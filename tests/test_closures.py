"""Seasonal closures: the roads OpenStreetMap marks closed for winter stay off
every route, loop and reroute on the days they are closed.

The parser and the calendar are pure and run anywhere. The rest needs the built
graph and `seasonal_closures.parquet` (pipeline/closures.py), and skips without
them, saying which.

**Every date here is injected, never today's.** On 2026-10-04, when this was
written, Lincoln Gap was open and VT-108 had four weeks to go, so a test of
"today" would have passed with no mask at all (docs/seasonal-closures-brief.md,
Trap 1).
"""

import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import shapely
from pyproj import Transformer

from closures import WINTER, conditional_windows, way_windows
from common import CRS_METERS
from conftest import DATA, ROOT, ROUTER_DATA
from looper import LoopPlanner
from router import Router, SeasonalClosures, _in_window

# The dates the brief's checks are written against. Lincoln Gap closes on
# Oct 15 and everything else in New England on Nov 1 or later, so Oct 20 has
# one road shut and Jan 15 has all of them.
JANUARY = date(2027, 1, 15)
JULY = date(2027, 7, 15)
GAP_CLOSED = date(2026, 10, 20)
GAP_OPEN = date(2026, 10, 10)

STOWE = (44.4654, -72.6874)
JEFFERSONVILLE = (44.6437, -72.8290)
WARREN = (44.1123, -72.8565)
BRISTOL = (44.1334, -73.0790)
LINCOLN = (44.1050, -72.9960)       # the village below the gap's west side
JACKSON = (44.1446, -71.1848)
JEFFERSON = (44.4192, -71.4748)
GORHAM = (44.3876, -71.1734)
# Where Lincoln Gap Road's closed section ends on the Warren side. A driver
# who meets the gate here and turns round faces east, and the reroute from
# this spot used to send them straight back over the gap.
GAP_EAST_END = (44.094617, -72.910377)
# On the Mt Washington Auto Road, a mile above its gate: no open road reaches it
# in winter.
AUTO_ROAD = (44.28112, -71.24602)

_TO_M = Transformer.from_crs(4326, CRS_METERS, always_xy=True)


# ------------------------------------------------------------------ the parser

class TestWhatCountsAsClosed:
    """Decision 2 of the brief, against the forms the New England extract
    actually holds."""

    @pytest.mark.parametrize("value,windows", [
        ("no @ (Nov-Apr)", [(11, 1, 4, 30)]),                 # VT-108
        ("no @ Nov-Apr", [(11, 1, 4, 30)]),
        ("no @ (Oct 15-May 15)", [(10, 15, 5, 15)]),          # Lincoln Gap Road
        ("no @ (Nov 1-Apr 30)", [(11, 1, 4, 30)]),
        ("no @ Nov-May", [(11, 1, 5, 31)]),                   # Hurricane Mountain Road
        ("no @ (December - May)", [(12, 1, 5, 31)]),
        ("no @ Dec 1-Apr 1", [(12, 1, 4, 1)]),
        ("no @ (Nov-Dec; Feb-Mar)", [(11, 1, 12, 31), (2, 1, 3, 31)]),
        ("No @ (Nov-Apr)", [(11, 1, 4, 30)]),
    ])
    def test_a_dated_closure_closes_inside_its_own_dates(self, value, windows):
        assert conditional_windows(value) == (windows, [])

    @pytest.mark.parametrize("value", ["no @ (winter)", "no @ winter",
                                       "no @ snow", "no @ (snow)"])
    def test_winter_or_snow_closes_the_default_window(self, value):
        assert conditional_windows(value) == ([WINTER], [])
        assert WINTER == (11, 1, 4, 30)

    @pytest.mark.parametrize("value", [
        "no @ (22:00-06:00)",             # the brief's own example
        "no @ 20:00-07:00",
        "no @ (dusk-dawn)",
        "no @ (Mo-Fr 07:00-09:00)",
        "no @ (07:00-09:00) (16:00-18:00)",
    ])
    def test_a_time_of_day_is_not_a_closure(self, value):
        assert conditional_windows(value) == ([], ["time of day"])
        assert way_windows({"highway": "residential",
                            "access:conditional": value}) == {}

    @pytest.mark.parametrize("value", [
        "no @ May-Sep Su 09:00-16:00",               # Baxter Boulevard, Portland
        "no @ (Sep 1-Jun 1 Mo-Fr 09:00-16:00)",      # Greenough Street, Brookline
    ])
    def test_months_with_a_weekday_or_time_are_not_a_closure_for_those_months(self, value):
        """Read as its months alone, the first would close Baxter Boulevard for
        the whole summer to protect its Sunday mornings."""
        assert conditional_windows(value) == ([], ["part-time"])

    def test_a_rule_that_is_part_time_does_not_drag_in_its_neighbours(self):
        value = ("no @ (Dec-Mar Mo-Fr; Dec-Mar Sa-Su dusk-dawn; PH dusk-dawn; "
                 "Apr-Nov Mo-Su dusk-dawn)")
        windows, reasons = conditional_windows(value)
        assert windows == []
        assert set(reasons) <= {"part-time", "time of day"}

    @pytest.mark.parametrize("value", [
        "no @ (2022 Apr 04-2022 Oct 28)",
        "no @ (2026 Mar 31 - 2026 Oct 31)",
        "no @ 2020 Feb 01-2021 Nov 01",
    ])
    def test_a_closure_with_a_year_is_a_one_off_not_a_season(self, value):
        """As an annual window the first would close four motorway ramps every
        summer, for a 2022 construction job."""
        assert conditional_windows(value) == ([], ["dated"])

    @pytest.mark.parametrize("value", ["no @ (weight>5)",
                                       "no @ (Nov-Apr AND weight > 5 st)"])
    def test_a_vehicle_condition_is_not_a_closure(self, value):
        assert conditional_windows(value) == ([], ["vehicle"])

    @pytest.mark.parametrize("value", [
        "yes @ (May 20-Oct 29, sunrise-sunset)",
        "destination @ (Apr 15 - Nov 30)",
        "yes @ snow",
        "private @ (Mo-Su 07:00-09:00,16:00-18:00)",
    ])
    def test_only_no_closes_anything(self, value):
        assert conditional_windows(value) == ([], [])

    def test_the_keys_that_bind_a_car_are_the_ones_read(self):
        for key in ("access", "vehicle", "motor_vehicle", "motorcar"):
            assert way_windows({f"{key}:conditional": "no @ (Nov-Apr)"}) == {
                (11, 1, 4, 30): [f"{key}:conditional=no @ (Nov-Apr)"]}
        assert way_windows({"hgv:conditional": "no @ (Nov-Apr)"}) == {}
        # Dated like a closure and containing "no", and a parking ban.
        assert way_windows({"parking:both:restriction:conditional":
                            "no_stopping @ (Nov 1-Apr 30)"}) == {}

    @pytest.mark.parametrize("tags", [
        {"winter_service": "no"},
        {"seasonal": "yes"}, {"seasonal": "summer"},
        {"seasonal": "spring;summer;autumn"}, {"seasonal": "no_snow"},
    ])
    def test_unmaintained_or_seasonal_roads_close_in_winter(self, tags):
        assert list(way_windows(tags)) == [WINTER]

    @pytest.mark.parametrize("tags", [{"winter_service": "yes"},
                                      {"seasonal": "winter"}, {"seasonal": "no"}])
    def test_the_other_seasonal_values_close_nothing(self, tags):
        assert way_windows(tags) == {}

    def test_every_tag_that_closes_a_way_is_kept_with_its_window(self):
        """Lincoln Gap Road carries both, and they disagree: the gate shuts on
        Oct 15, two weeks before the default window opens."""
        windows = way_windows({"motor_vehicle:conditional": "no @ (Oct 15-May 15)",
                               "winter_service": "no"})
        assert windows == {
            (10, 15, 5, 15): ["motor_vehicle:conditional=no @ (Oct 15-May 15)"],
            WINTER: ["winter_service=no"]}
        vt108 = way_windows({"motor_vehicle:conditional": "no @ (Nov-Apr)",
                             "winter_service": "no"})
        assert vt108 == {WINTER: ["motor_vehicle:conditional=no @ (Nov-Apr)",
                                  "winter_service=no"]}


# -------------------------------------------------------------------- the join

class TestTheJoin:
    """Closed ways to graph rows: candidates by node id, kept by geometry."""

    # Two roads from junction 1 to junction 2: one straight, one bowing about
    # 80 m east at its middle, as a parallel road does.
    CLOSED = [(-72.0, 44.0), (-72.0, 44.005), (-72.0, 44.01)]
    OPEN = [(-72.0, 44.0), (-71.999, 44.005), (-72.0, 44.01)]

    def _edges(self):
        import geopandas as gpd
        return gpd.GeoDataFrame(
            {"u": [1, 1], "v": [2, 2], "length_m": [1112.0, 1115.0]},
            geometry=[shapely.LineString(self.CLOSED),
                      shapely.LineString(self.OPEN)], crs=4326)

    def test_an_open_road_between_the_same_junctions_stays_open(self):
        """Trap 4. Both edges have both ends among the closed way's nodes, and
        `route` keeps only the cheaper of two parallel edges, so closing both
        would close the open road too."""
        from closures import join
        way = {"way_id": 7, "name": "Notch Road",
               "windows": {WINTER: ["winter_service=no"]},
               "refs": [1, 99, 2], "coords": self.CLOSED}
        table = join([way], self._edges())
        assert list(table["edge"]) == [0]
        assert table.loc[0, "tag"] == "winter_service=no"

    def test_an_edge_gets_a_row_for_each_window(self):
        from closures import join
        way = {"way_id": 7, "name": "Lincoln Gap Road",
               "windows": {(10, 15, 5, 15): ["motor_vehicle:conditional=no @ (Oct 15-May 15)"],
                           WINTER: ["winter_service=no"]},
               "refs": [1, 99, 2], "coords": self.CLOSED}
        table = join([way], self._edges())
        assert list(table["edge"]) == [0, 0]
        assert set(map(tuple, table[["start_month", "start_day", "end_month",
                                     "end_day"]].to_numpy())) == {(10, 15, 5, 15), WINTER}


# ---------------------------------------------------------------- the calendar

def _table(rows):
    return pd.DataFrame(rows, columns=["edge", "u", "v", "way_id", "start_month",
                                       "start_day", "end_month", "end_day",
                                       "length_m"])


class TestTheCalendar:
    @pytest.mark.parametrize("day,closed", [
        (date(2026, 10, 14), False), (date(2026, 10, 15), True),
        (date(2027, 1, 1), True), (date(2027, 5, 15), True),
        (date(2027, 5, 16), False), (date(2027, 7, 15), False),
    ])
    def test_a_window_across_new_year_includes_both_ends(self, day, closed):
        assert _in_window((10, 15, 5, 15), day) is closed

    @pytest.mark.parametrize("day,closed", [
        (date(2026, 10, 31), False), (date(2026, 11, 1), True),
        (date(2028, 2, 29), True), (date(2027, 4, 30), True),
        (date(2027, 5, 1), False),
    ])
    def test_the_default_winter_window(self, day, closed):
        assert _in_window(WINTER, day) is closed

    @pytest.mark.parametrize("day,closed", [
        (date(2027, 5, 31), False), (date(2027, 6, 1), True),
        (date(2027, 8, 31), True), (date(2027, 9, 1), False),
    ])
    def test_a_window_inside_one_year(self, day, closed):
        assert _in_window((6, 1, 8, 31), day) is closed

    def test_the_version_names_the_windows_in_force(self):
        c = SeasonalClosures(_table([[0, 10, 11, 1, 10, 15, 5, 15, 100.0],
                                     [1, 11, 12, 2, 11, 1, 4, 30, 200.0],
                                     [2, 12, 13, 2, 11, 1, 4, 30, 300.0]]),
                             np.array([10, 11, 12]), np.array([11, 12, 13]))
        assert c.version(GAP_OPEN) == ()
        assert c.version(GAP_CLOSED) == ((10, 15, 5, 15),)
        assert list(c.edges(c.version(GAP_CLOSED))) == [0]
        assert list(c.edges(c.version(JANUARY))) == [0, 1, 2]
        # Two days that close the same roads are one version, so a cache
        # filled on one serves the other; that is what lets it outlive a
        # midnight that closes nothing new.
        assert c.version(JANUARY) == c.version(date(2027, 2, 15))
        assert c.version(JULY) == c.version(GAP_OPEN) == ()
        assert (c.n_edges, c.n_ways, c.km) == (3, 2, 0.6)

    def test_a_table_built_against_another_graph_is_refused(self):
        """Its rows would close whichever roads now sit at those numbers."""
        table = _table([[1, 10, 11, 1, 11, 1, 4, 30, 100.0]])
        with pytest.raises(RuntimeError, match="another graph"):
            SeasonalClosures(table, np.array([10, 99]), np.array([11, 98]))
        with pytest.raises(RuntimeError, match="another graph"):
            SeasonalClosures(table, np.array([10]), np.array([11]))

    def test_today_is_new_englands_date_and_not_the_servers(self, monkeypatch):
        """The box keeps UTC. At 10 pm on Oct 14 in Vermont its clock already
        reads Oct 15, and judging the day by it would shut Lincoln Gap four
        hours before the gate does."""
        import router as router_module

        evening = datetime(2026, 10, 15, 2, 0, tzinfo=timezone.utc)

        class UtcBox:
            @staticmethod
            def now(tz=None):
                # A naive now() on a UTC box is UTC wall time.
                return evening.replace(tzinfo=None) if tz is None else evening.astimezone(tz)

        monkeypatch.setattr(router_module, "datetime", UtcBox)
        assert router_module.region_today() == date(2026, 10, 14)

    def test_the_router_says_what_it_loaded_either_way(self, tmp_path, capsys):
        """The box's journal is the only place a missing mask would show, so
        both outcomes print (and flush; see Router._read_closures)."""
        stub = SimpleNamespace(edges=pd.DataFrame({"u": [10, 11], "v": [11, 12]}))
        Router._read_closures(stub, tmp_path)
        assert stub.closures is None
        assert "seasonal closures: none" in capsys.readouterr().out

        _table([[1, 11, 12, 7, 11, 1, 4, 30, 1500.0]]).to_parquet(
            tmp_path / "seasonal_closures.parquet")
        Router._read_closures(stub, tmp_path)
        assert stub.closures.n_edges == 1
        assert ("seasonal closures: 1 edges (1.5 km, 1 ways) in 1 windows"
                in capsys.readouterr().out)


# ------------------------------------------------------------------- the table

@pytest.fixture(scope="module")
def table():
    path = DATA / "seasonal_closures.parquet"
    if not path.exists():
        pytest.skip("seasonal_closures.parquet missing — run pipeline/closures.py")
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def closed_router(router, table):
    """The session router, which must have loaded the table."""
    assert router.closures is not None
    return router


def _closed_rows(router, day):
    return set(router.closures.edges(router.closure_version(day)).tolist())


def _km_on(route, rows):
    edges = route.edges
    hit = np.isin(edges.index.to_numpy(), list(rows))
    return float(edges["length_m"].to_numpy()[hit].sum() / 1000.0)


class TestTheTable:
    def test_every_closure_is_a_winter_closure(self, table):
        """What a parser regression would break first: Baxter Boulevard's
        Sunday rule read as May-Sep, or a 2022 construction date read as
        every summer, would put a window over July."""
        windows = table[["start_month", "start_day", "end_month",
                         "end_day"]].drop_duplicates().to_numpy()
        for w in windows:
            assert _in_window(tuple(w), JANUARY), w
            assert not _in_window(tuple(w), JULY), w

    def test_the_named_roads_are_there(self, table):
        def windows(name):
            rows = table[table["name"] == name]
            return set(map(tuple, rows[["start_month", "start_day",
                                        "end_month", "end_day"]].to_numpy()))
        assert (10, 15, 5, 15) in windows("Lincoln Gap Road")
        assert WINTER in windows("Vermont Route 108 South")
        assert WINTER in windows("Mount Washington Auto Road")
        assert (11, 1, 5, 31) in windows("Hurricane Mountain Road")
        # Evans Notch carries a route number and no name.
        assert (table["ref"] == "ME 113").any()

    def test_the_router_loaded_all_of_it(self, closed_router, table):
        assert closed_router.closures.n_edges == table["edge"].nunique()
        assert len(_closed_rows(closed_router, JANUARY)) == table["edge"].nunique()


# ------------------------------------------------------------------ the routes

def _route(router, a, b, pref, day, heading=None):
    s, _ = router.snap(*a, heading=heading)
    t, _ = router.snap_destination(*b)
    return router.route(s, t, pref, {}, heading=heading, on=day)


class TestRoutes:
    @pytest.mark.parametrize("pref", [0.0, 0.5, 1.0])
    def test_stowe_to_jeffersonville_avoids_vt108_in_january(self, closed_router, pref):
        """Every arm, the fastest included, drove the Notch on the day the
        verdict measured it."""
        r = closed_router
        winter = _route(r, STOWE, JEFFERSONVILLE, pref, JANUARY)
        summer = _route(r, STOWE, JEFFERSONVILLE, pref, JULY)
        notch = _closed_rows(r, JANUARY)
        assert _km_on(summer, notch) > 3.0, "the July route no longer uses the Notch"
        assert _km_on(winter, notch) == 0.0, winter.edges["name"].unique()
        assert "Vermont Route 108 South" in set(summer.edges["name"])
        assert "Vermont Route 108 South" not in set(winter.edges["name"])

    @pytest.mark.parametrize("pref", [0.0, 0.5, 1.0])
    def test_warren_to_bristol_avoids_lincoln_gap_once_it_closes(self, closed_router, pref):
        r = closed_router
        gap = _closed_rows(r, GAP_CLOSED)
        before = _route(r, WARREN, BRISTOL, pref, GAP_OPEN)
        after = _route(r, WARREN, BRISTOL, pref, GAP_CLOSED)
        assert _km_on(before, gap) > 3.0, "the Oct 10 route no longer crosses the gap"
        assert _km_on(after, gap) == 0.0

    def test_a_day_with_nothing_closed_is_the_year_round_graph(self, closed_router):
        r = closed_router
        s, _ = r.snap(*STOWE)
        t, _ = r.snap_destination(*JEFFERSONVILLE)
        assert r.closure_version(JULY) == ()
        summer = r.route(s, t, 0.5, {}, on=JULY)
        plain = r.route(s, t, 0.5, {})
        assert list(summer.edges.index) == list(plain.edges.index)

    def test_the_fastest_arm_is_still_exact_with_roads_closed(self, closed_router):
        """The A* bound is built on the open graph. Closing roads only raises
        true costs, so it stays admissible, and the A* must still find what a
        whole-graph Dijkstra over the same masked weights does."""
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import dijkstra
        from router import _ASTAR_GAVE_UP

        r = closed_router
        s, _ = r.snap(*STOWE)
        t, _ = r.snap_destination(*JEFFERSONVILLE)
        targets = r.node_copies.get(t, np.array([t]))
        w = r._weights(0.0, r._edge_scores({}), 1.0, JANUARY)
        pair_w = np.full(r.n_pairs, np.inf)
        np.minimum.at(pair_w, r.slot_pair, w)
        path = r._astar(s, targets, pair_w)
        assert path is not None and path is not _ASTAR_GAVE_UP
        hops = np.asarray(path, dtype=np.int64)
        cost = pair_w[np.searchsorted(r._pair_key, hops[:-1] * r.n + hops[1:])].sum()
        g = csr_matrix((pair_w, (r.u_tail, r.u_head)), shape=(r.n, r.n))
        shortest = dijkstra(g, directed=True, indices=s)[targets].min()
        assert np.isfinite(cost)
        assert cost == pytest.approx(shortest, rel=1e-9)

    def test_closed_edges_cost_infinity_and_nothing_else_moves(self, closed_router):
        r = closed_router
        scores = r._edge_scores({})
        open_w = r._weights(0.5, scores, 1.0)
        shut_w = r._weights(0.5, scores, 1.0, JANUARY)
        closed = np.isin(r.eidx, list(_closed_rows(r, JANUARY)))
        assert np.isinf(shut_w[closed]).all()
        assert np.array_equal(shut_w[~closed], open_w[~closed])

    def test_a_rejoin_through_a_waypoint_avoids_the_gap_too(self, closed_router):
        """The mid-drive `via` reroute is priced by LoopPlanner.resume, not by
        `route`, so it has to be shown separately."""
        r = closed_router
        planner = LoopPlanner(r)
        s, _ = r.snap(*WARREN)
        w, _ = r.snap(*LINCOLN)
        t, _ = r.snap_destination(*BRISTOL)
        gap = _closed_rows(r, GAP_CLOSED)
        before = planner.resume(s, w, t, 0.0, {}, 1.0, on=GAP_OPEN)
        after = planner.resume(s, w, t, 0.0, {}, 1.0, on=GAP_CLOSED)
        assert _km_on(before, gap) > 3.0
        assert after is not None and _km_on(after, gap) == 0.0


# ------------------------------------------------------------------- the loops

@pytest.fixture(scope="module")
def loop_planner(closed_router):
    """Room for every start's fields under both versions, so the July and
    January sweeps do not evict each other."""
    return LoopPlanner(closed_router, field_cache=8)


class TestLoops:
    """Loops of 40 and 80 km from four towns among the closed roads, in every
    direction offered. In July 2027 the first loop offered from them carried
    winter-closed road in 5 of 8 cases, so the January check has something to
    catch."""

    STARTS = {"Stowe": STOWE, "Warren": WARREN,
              "Jackson": JACKSON, "Jefferson": JEFFERSON}

    @pytest.mark.parametrize("name", list(STARTS))
    @pytest.mark.parametrize("km", [40, 80])
    def test_no_loop_drives_a_closed_road_in_january(self, closed_router, loop_planner,
                                                      name, km):
        r, planner = closed_router, loop_planner
        start, _ = r.snap(*self.STARTS[name])
        closed = _closed_rows(r, JANUARY)
        sectors = planner.sectors(start, km, 1.0, {}, 1.0, on=JANUARY)
        assert sectors, f"no loop at all from {name} in January"
        loops = [planner.plan(start, km, 1.0, {}, on=JANUARY)]
        loops += [planner.plan(start, km, 1.0, {}, sector=s, on=JANUARY)
                  for s in sectors]
        for loop in loops:
            assert loop is not None
            # Zero, not the brief's 0.2 km. That allowance was for the
            # verdict's method, a 3 m buffer round each closed way, which
            # counts a few metres wherever a loop crosses one. Counted by edge
            # a closed road costs +inf, so any metre of it is a bug.
            assert _km_on(loop.route, closed) == 0.0, (name, km, loop.sector)

    def test_in_july_the_first_loops_still_use_them(self, closed_router, loop_planner):
        r, planner = closed_router, loop_planner
        winter_closed = _closed_rows(r, JANUARY)
        carrying = 0
        for point in self.STARTS.values():
            start, _ = r.snap(*point)
            for km in (40, 80):
                loop = planner.plan(start, km, 1.0, {}, on=JULY)
                carrying += _km_on(loop.route, winter_closed) > 0.2
        assert carrying >= 3, f"only {carrying} of 8 first loops use them in July"


# ------------------------------------------------------------------- the caches

class TestTheCachesKeyOnTheClosures:
    """All three caches key on everything else a request carries, so without
    the closure version they would go on serving a route cached on Oct 14
    after the gap shut on Oct 15 (Trap 2)."""

    def test_the_cost_model(self, closed_router):
        p = LoopPlanner(closed_router)
        july = p._cost(1.0, (), 1.0, on=JULY)
        assert p._cost(1.0, (), 1.0, on=JANUARY) is not july
        # The same closed set is the same entry, whatever the day.
        assert p._cost(1.0, (), 1.0, on=date(2027, 2, 15)) is \
               p._cost(1.0, (), 1.0, on=JANUARY)
        assert p._cost(1.0, (), 1.0) is july

    def test_the_field_sets(self, closed_router):
        p = LoopPlanner(closed_router, field_cache=4)
        start, _ = closed_router.snap(*STOWE)
        july = p._fields(start, 1.0, {}, 1.0, on=JULY)
        january = p._fields(start, 1.0, {}, 1.0, on=JANUARY)
        assert january is not july
        assert january.cost is not july.cost
        assert p._fields(start, 1.0, {}, 1.0, on=JULY) is july


# ------------------------------------------------------------------ the server

@pytest.fixture(scope="module")
def server(table):
    missing = [f for f in ROUTER_DATA if not (DATA / f).exists()]
    if missing:
        pytest.skip(f"built graph missing ({', '.join(missing)})")
    import os
    os.environ.setdefault("SUNDAYDRIVE_DATA", str(DATA))
    sys.path.insert(0, str(ROOT / "server"))
    import app as server_app
    server_app.app.config["TESTING"] = True
    assert server_app.ROUTER.closures is not None
    return server_app


def _on(monkeypatch, server, day):
    monkeypatch.setattr(server, "_today", lambda: day)
    return server.app.test_client()


def _steps(feature):
    return [s["instruction"] for s in feature["properties"]["steps"]]


def _line_m(feature):
    lon, lat = np.asarray(feature["geometry"]["coordinates"]).T
    return shapely.LineString(np.column_stack(_TO_M.transform(lon, lat)))


def _closed_midpoints_m(router, day):
    rows = sorted(_closed_rows(router, day))
    geoms = router._edge_geom_m[rows]
    return shapely.line_interpolate_point(geoms, 0.5, normalized=True)


class TestThroughTheServer:
    def _ll(self, point):
        return f"{point[0]},{point[1]}"

    def test_warren_to_bristol_through_the_api(self, server, monkeypatch):
        form = {"from": self._ll(WARREN), "to": self._ll(BRISTOL), "pref": "0.5"}
        before = _on(monkeypatch, server, GAP_OPEN).post("/api/route", data=form)
        after = _on(monkeypatch, server, GAP_CLOSED).post("/api/route", data=form)
        assert before.status_code == after.status_code == 200
        for arm in ("fastest", "scenic"):
            assert any("Lincoln Gap Road" in s for s in _steps(before.get_json()[arm]))
            assert not any("Lincoln Gap Road" in s for s in _steps(after.get_json()[arm]))

    @pytest.mark.parametrize("pref", ["0", "0.5"])
    def test_the_reroute_at_the_gate_does_not_go_back_over_the_gap(
            self, server, monkeypatch, pref):
        """The stranding case: at the gate, the off-route reroute and "switch
        to fastest" both sent the driver back up the closed road."""
        form = {"from": self._ll(GAP_EAST_END), "to": self._ll(BRISTOL),
                "heading": "90", "pref": pref}
        gap = _closed_midpoints_m(server.ROUTER, GAP_CLOSED)
        before = _on(monkeypatch, server, GAP_OPEN).post("/api/route", data=form)
        after = _on(monkeypatch, server, GAP_CLOSED).post("/api/route", data=form)
        assert before.status_code == after.status_code == 200
        for arm in ("fastest", "scenic"):
            assert min(p.distance(_line_m(before.get_json()[arm])) for p in gap) < 1.0
            assert min(p.distance(_line_m(after.get_json()[arm])) for p in gap) > 50.0

    def test_both_arms_of_a_rejoin_avoid_the_gap(self, server, monkeypatch):
        """The loop rejoin runs one `resume` per arm, and each has to be told
        the date: through Lincoln village, the way over the gap is the
        shortest, so an arm that is not told drives it."""
        form = {"from": self._ll(WARREN), "via": self._ll(LINCOLN),
                "to": self._ll(BRISTOL), "pref": "0.5"}
        gap = _closed_midpoints_m(server.ROUTER, GAP_CLOSED)
        before = _on(monkeypatch, server, GAP_OPEN).post("/api/route", data=form)
        after = _on(monkeypatch, server, GAP_CLOSED).post("/api/route", data=form)
        assert before.status_code == after.status_code == 200
        for arm in ("fastest", "scenic"):
            assert min(p.distance(_line_m(before.get_json()[arm])) for p in gap) < 1.0
            assert min(p.distance(_line_m(after.get_json()[arm])) for p in gap) > 50.0

    def test_a_destination_only_a_closed_road_reaches_says_so(self, server, monkeypatch):
        form = {"from": self._ll(GORHAM), "to": self._ll(AUTO_ROAD), "pref": "0.5"}
        winter = _on(monkeypatch, server, JANUARY).post("/api/route", data=form)
        assert winter.status_code == 404
        assert winter.get_json()["error"] == server.CLOSED_FOR_SEASON
        summer = _on(monkeypatch, server, JULY).post("/api/route", data=form)
        assert summer.status_code == 200

    def test_so_does_a_rejoin_through_one(self, server, monkeypatch):
        form = {"from": self._ll(JACKSON), "to": self._ll(GORHAM),
                "via": self._ll(AUTO_ROAD), "pref": "0.5"}
        winter = _on(monkeypatch, server, JANUARY).post("/api/route", data=form)
        assert winter.status_code == 404
        assert winter.get_json()["error"] == server.CLOSED_FOR_SEASON
        summer = _on(monkeypatch, server, JULY).post("/api/route", data=form)
        assert summer.status_code == 200

    def test_a_loop_cached_in_july_is_not_served_in_january(self, server, monkeypatch):
        form = {"from": self._ll(JEFFERSON), "km": "80"}
        closed = _closed_midpoints_m(server.ROUTER, JANUARY)
        july = _on(monkeypatch, server, JULY).post("/api/loop", data=form)
        january = _on(monkeypatch, server, JANUARY).post("/api/loop", data=form)
        assert july.status_code == january.status_code == 200

        def closed_hits(body):
            line = _line_m(body["loop"])
            return sum(p.distance(line) < 1.0 for p in closed)

        assert closed_hits(july.get_json()) > 0, "July's loop no longer uses them"
        assert closed_hits(january.get_json()) == 0
        versions = {key[-1] for key in server.LOOP_RESULTS}
        assert server.ROUTER.closure_version(JANUARY) in versions
        assert () in versions


# ------------------------------------------------------------------ the deploy

def test_the_deploy_script_ships_the_table():
    """The box would otherwise start, answer, and route over every closed road
    with nothing in any log (Trap 3)."""
    script = (ROOT / "server" / "deploy-oracle.sh").read_text()
    optional = next(line for line in script.splitlines()
                    if line.startswith("OPTIONAL="))
    assert "seasonal_closures" in optional.split("=", 1)[1].strip('"').split()
