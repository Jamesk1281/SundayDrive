"""Seasonal closures: the roads OpenStreetMap marks closed for winter stay off
every route, loop and reroute on the days they are closed.

The parser and the calendar are pure and run anywhere. The rest needs the built
graph and `seasonal_closures.parquet` (pipeline/closures.py), and skips without
them, saying which.

**Every date here is injected, never today's.** On 2026-10-04, when this was
written, Lincoln Gap was open and VT-108 had four weeks to go, so a test of
"today" would have passed with no mask at all (Trap 1 of the brief,
`git show a2ddddc:docs/seasonal-closures-brief.md`).
"""

import re
import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import shapely
from pyproj import Transformer

from closures import WINTER, conditional_windows, gate_windows, way_windows
from common import CRS_METERS, in_window
from conftest import DATA, ROOT, ROUTER_DATA
from looper import LoopPlanner
from router import Router, SeasonalClosures

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
# On the Mt Washington Auto Road, a mile above its gate, and on Mt Greylock's
# Notch Road below the summit: no open road reaches either in winter.
AUTO_ROAD = (44.28112, -71.24602)
GREYLOCK = (42.65410, -73.16278)

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

    @pytest.mark.parametrize("value,windows", [
        # Mt Greylock's Rockwell and Notch Roads. Read by strict grammar the
        # comma adds a daylight rule for every day of the year; the mapper
        # meant a season with daylight hours.
        ("yes @ (May 20-Oct 29, sunrise-sunset)", [(10, 30, 5, 19)]),
        ("yes @ (May-Oct)", [WINTER]),
        ("yes @ (May-Oct Sa,Su 10:00-16:00)", [WINTER]),
        ("yes @ (Jun 1-Sep 30; Dec 15-Jan 15)", [(1, 16, 5, 31), (10, 1, 12, 14)]),
    ])
    def test_open_only_in_season_closes_the_rest_of_the_year(self, value, windows):
        assert conditional_windows(value) == (windows, [])

    @pytest.mark.parametrize("value", [
        "yes @ (Mo-Fr 05:00-10:00)",          # the I-93 lanes: open every week
        "yes @ snow",
        "yes @ (2026 May-2026 Oct)",
        "destination @ (Apr 15 - Nov 30)",
        "private @ (Mo-Su 07:00-09:00,16:00-18:00)",
    ])
    def test_the_other_values_close_nothing(self, value):
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


class TestDatesWrittenOtherWays:
    """The spellings `_RANGE` alone rejected as "unrecognized", leaving the
    road open all year (docs/safety-quick-fixes.md, "Dates"). Each string is
    the one the US survey found (docs/us-map-data-findings.md, section 4),
    plus New England's one gate written day first."""

    @pytest.mark.parametrize("value,windows", [
        ("no @ Oct 14th - May 31st", [(10, 14, 5, 31)]),      # Trail Ridge Road, CO
        ("no @ Nov 19th - May 30th", [(11, 19, 5, 30)]),      # CO
        ("no@(Dec 1 - Mai 1)", [(12, 1, 5, 1)]),              # German month
        ("no @ (8 Dec - 1 May)", [(12, 8, 5, 1)]),            # WA, day first
        ("no @ (15 Dec-30 Apr)", [(12, 15, 4, 30)]),          # Natural Turnpike's gate, VT
        ("no @ (Nov 1st-Apr 30th)", [WINTER]),
        ("no @ (Oct 22nd - May 3rd)", [(10, 22, 5, 3)]),
    ])
    def test_each_spelling_closes_its_own_dates(self, value, windows):
        assert conditional_windows(value) == (windows, [])

    def test_an_ordinal_in_an_open_only_window(self):
        assert conditional_windows("yes @ (May 31st - Oct 14th)") == (
            [(10, 15, 5, 30)], [])

    @pytest.mark.parametrize("value,reason", [
        # The refusals stay, each added to keep a New England road from being
        # closed for good: a year, a weekday or time, a vehicle condition.
        ("no @ (2024 Oct 14th-2025 May 31st)", "dated"),
        ("no @ (Oct 14th-May 31st Mo-Fr)", "part-time"),
        ("no @ (Oct 14th-May 31st 18:00-06:00)", "part-time"),
        ("no @ (Oct 14th - May 31st AND weight>5)", "vehicle"),
        # `th` standing alone is Thursday, not an ordinal.
        ("no @ (Th 10:00-12:00)", "time of day"),
        ("no @ Th", "time of day"),
        # A day that does not exist, and a word that only begins like "Mai".
        ("no @ (Oct 32nd - May 1)", "unrecognized"),
        ("no @ maintenance", "unrecognized"),
        ("no @ (1st)", "unrecognized"),
        # Day first at one end only is not a form anyone was seen writing.
        ("no @ (8 Dec - May 1)", "unrecognized"),
    ])
    def test_the_refusals_still_hold(self, value, reason):
        assert conditional_windows(value) == ([], [reason])


class TestGatesClosedForTheSeason:
    """A barrier node's own car conditionals, through the grammar a way's go
    through (docs/safety-quick-fixes.md, "Gates")."""

    @pytest.mark.parametrize("tags,windows", [
        ({"barrier": "gate", "motor_vehicle:conditional": "no @ (Nov-Apr)"}, [WINTER]),
        ({"barrier": "gate", "motor_vehicle:conditional": "no @ winter"}, [WINTER]),
        ({"barrier": "gate", "motor_vehicle:conditional": "no @ (Nov-Mar)"},
         [(11, 1, 3, 31)]),
        ({"barrier": "swing_gate", "access": "yes",
          "motor_vehicle:conditional": "no @ (15 Dec-30 Apr)"}, [(12, 15, 4, 30)]),
        # Open only in summer, so closed the rest of the year, as on a way.
        ({"barrier": "gate", "access:conditional": "yes@(Jun-Aug)"}, [(9, 1, 5, 31)]),
        ({"barrier": "swing_gate", "motor_vehicle": "permissive",
          "motor_vehicle:conditional": "yes @ (Jun-Aug 08:00-20:00)"}, [(9, 1, 5, 31)]),
    ])
    def test_a_seasonal_gate_closes_in_its_window(self, tags, windows):
        found = gate_windows(tags)
        assert list(found) == windows
        key = next(k for k in tags if k.endswith(":conditional"))
        assert found[windows[0]] == [f"barrier={tags['barrier']}, {key}={tags[key]}"]

    @pytest.mark.parametrize("value", [
        # Times of day. Read by their months, or by nothing, these would shut
        # a park gate all summer, or all year, for its evenings.
        "no @ (Mo-Fr 17:00-07:00; Sa-Su)",
        "no @ 20:00-07:00",
        "no @ (sunset-sunrise)",
        "no @ (Dec-Mar Mo-Fr; Dec-Mar Sa-Su dusk-dawn; PH dusk-dawn; "
        "Apr-Nov Mo-Su dusk-dawn)",
        "no @ (2022 Apr 04-2022 Oct 28)",
        "no @ (weight>5)",
        "no @ crossing", "no @ flooding",
        "yes @ (sunrise-sunset)",
        "customers @ Mo-Fr 08:00-16:30",
        "permissive @ (winter)",
    ])
    def test_the_refusals_close_nothing_on_a_gate_either(self, value):
        assert gate_windows({"barrier": "gate", "access:conditional": value}) == {}

    def test_a_conditional_never_opens_a_barrier_closed_all_year(self):
        """The chain is private all year and `permissive` in winter; the
        conditional must not open it, and nothing seasonal is added either,
        because closed_to_cars already closes it every day."""
        from common import barrier_closes
        for tags in (
                {"barrier": "chain", "access": "private",
                 "access:conditional": "permissive @ (winter)"},
                {"barrier": "gate", "motor_vehicle": "no",
                 "motor_vehicle:conditional": "yes @ (May-Oct: Mo-Su,PH 10:00-17:30)"},
                {"barrier": "gate", "motor_vehicle": "no",
                 "access:conditional": "yes @ (sunrise-sunset)"},
                {"barrier": "gate", "locked": "yes",
                 "motor_vehicle:conditional": "yes @ (Jun-Aug)"},
                {"barrier": "toll_booth", "operator": "North Maine Woods",
                 "motor_vehicle:conditional": "no @ (Dec-Apr)"}):
            assert barrier_closes(tags)
            assert gate_windows(tags) == {}

    def test_only_a_car_key_on_a_barrier_counts(self):
        assert gate_windows({"barrier": "gate", "hgv:conditional": "no @ (Nov-Apr)"}) == {}
        assert gate_windows({"barrier": "gate", "winter_service": "no"}) == {}
        assert gate_windows({"highway": "residential",
                             "motor_vehicle:conditional": "no @ (Nov-Apr)"}) == {}

    def test_a_gate_and_its_way_agree_on_the_rule(self):
        for value in ("no @ (Nov-Apr)", "yes @ (May 20-Oct 29, sunrise-sunset)",
                      "no @ (Mo-Fr 17:00-07:00; Sa-Su)"):
            gate = gate_windows({"barrier": "gate", "motor_vehicle:conditional": value})
            way = way_windows({"motor_vehicle:conditional": value})
            assert list(gate) == list(way)


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


class TestTheGateJoin:
    """Seasonal gates are placed as barriers closed all year are
    (`_place_barriers`), and each placement gets a row per window."""

    #   1 ---- 98 ---- 2 ---- 3      a straight road, 98 a quarter of the way
    #                  |             to 2; 2 continues north to 3, and 4
    #                  4             branches off 2.
    N = {1: (-72.0, 44.0), 98: (-72.0, 44.0025), 2: (-72.0, 44.01),
         3: (-72.0, 44.02), 4: (-71.99, 44.01)}

    def _edges(self, *spec):
        import geopandas as gpd
        return gpd.GeoDataFrame(
            {"u": [u for u, _ in spec], "v": [v for _, v in spec],
             "length_m": [1112.0] * len(spec),
             "name": [f"road {i}" for i in range(len(spec))]},
            geometry=[shapely.LineString([self.N[n] for n in (
                (u, 98, v) if (u, v) == (1, 2) else (u, v))]) for u, v in spec],
            crs=4326)

    def _way(self, way_id, refs):
        return {"way_id": way_id, "name": "", "closes": "", "kind": "",
                "refs": refs, "coords": [self.N[r] for r in refs]}

    def _gate(self, node, owners, windows=None):
        windows = windows or {WINTER: ["barrier=gate, motor_vehicle:conditional=no @ (Nov-Apr)"]}
        return {node: (*self.N[node], windows, owners)}

    def test_a_gate_inside_an_edge_closes_it_for_the_season(self):
        from closures import join_gates
        edges = self._edges((1, 2))
        table, left = join_gates([self._way(7, [1, 98, 2])], self._gate(98, [0]), edges)
        assert list(table["edge"]) == [0]
        row = table.iloc[0]
        assert (row["rule"], row["node_id"], row["way_id"]) == ("edge", 98, 7)
        assert tuple(row[["start_month", "start_day", "end_month", "end_day"]]) == WINTER
        assert row["at_m"] == pytest.approx(1112.0 / 4, rel=0.01)
        assert not any(left.values())

    def test_a_gate_between_two_edges_closes_neither(self):
        """VT-108's gate at Smugglers' Notch stands where two edges meet:
        closing both would close the open road below it too."""
        from closures import join_gates
        edges = self._edges((1, 2), (2, 3))
        table, _ = join_gates([self._way(7, [1, 98, 2]), self._way(8, [2, 3])],
                              self._gate(2, [0, 1]), edges)
        assert set(table["rule"]) == {"through"}
        assert sorted(table["edge"]) == [0, 1]
        assert set(table["node_id"]) == {2}

    def test_a_gate_at_a_dead_end_or_a_junction_closes_nothing(self):
        from closures import join_gates
        edges = self._edges((1, 2), (2, 3), (2, 4))
        ways = [self._way(7, [1, 98, 2]), self._way(8, [2, 3]), self._way(9, [2, 4])]
        table, left = join_gates(ways, {**self._gate(3, [1]), **self._gate(2, [0, 1, 2])},
                                 edges)
        assert table.empty
        assert (left["dead end"], left["junction"]) == ([3], [2])

    def test_a_row_for_each_window(self):
        from closures import join_gates
        edges = self._edges((1, 2))
        windows = {(9, 1, 5, 31): ["barrier=gate, access:conditional=yes@(Jun-Aug)"],
                   WINTER: ["barrier=gate, motor_vehicle:conditional=no @ winter"]}
        table, _ = join_gates([self._way(7, [1, 98, 2])],
                              self._gate(98, [0], windows), edges)
        assert len(table) == 2 and set(table["edge"]) == {0}

    def test_a_way_and_a_gate_on_one_edge_keep_both_rows(self):
        """A gate between two edges keeps its "through" row even where its
        way closes the edge in the same window, or the router would find one
        side of the gate missing."""
        from closures import _seasonal_table, join, join_gates
        edges = self._edges((1, 2), (2, 3))
        ways = [self._way(7, [1, 98, 2]), self._way(8, [2, 3])]
        closed = [{**ways[0], "windows": {WINTER: ["winter_service=no"]}}]
        gates, _ = join_gates(ways, self._gate(2, [0, 1]), edges)
        table = _seasonal_table(pd.concat([join(closed, edges), gates], ignore_index=True))
        assert sorted(zip(table["edge"], table["rule"])) == [
            (0, "edge"), (0, "through"), (1, "through")]


# ---------------------------------------------------------------- the calendar

def _table(rows):
    return pd.DataFrame(rows, columns=["edge", "u", "v", "way_id", "start_month",
                                       "start_day", "end_month", "end_day",
                                       "length_m"])


def _closed_on(window, day):
    return in_window(window, (day.month, day.day))


class TestTheCalendar:
    @pytest.mark.parametrize("day,closed", [
        (date(2026, 10, 14), False), (date(2026, 10, 15), True),
        (date(2027, 1, 1), True), (date(2027, 5, 15), True),
        (date(2027, 5, 16), False), (date(2027, 7, 15), False),
    ])
    def test_a_window_across_new_year_includes_both_ends(self, day, closed):
        assert _closed_on((10, 15, 5, 15), day) is closed

    @pytest.mark.parametrize("day,closed", [
        (date(2026, 10, 31), False), (date(2026, 11, 1), True),
        (date(2028, 2, 29), True), (date(2027, 4, 30), True),
        (date(2027, 5, 1), False),
    ])
    def test_the_default_winter_window(self, day, closed):
        assert _closed_on(WINTER, day) is closed

    @pytest.mark.parametrize("day,closed", [
        (date(2027, 5, 31), False), (date(2027, 6, 1), True),
        (date(2027, 8, 31), True), (date(2027, 9, 1), False),
    ])
    def test_a_window_inside_one_year(self, day, closed):
        assert _closed_on((6, 1, 8, 31), day) is closed

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

    def test_a_gate_between_two_edges_closes_no_edge(self):
        """Its rows name the two edges it stands between, and close neither:
        `through_nodes` says when driving through it is closed instead."""
        table = _table([[0, 10, 11, 1, 10, 15, 5, 15, 100.0],
                        [1, 11, 12, 1, 11, 1, 4, 30, 200.0],
                        [2, 12, 13, 2, 11, 1, 4, 30, 300.0]])
        table["rule"] = ["edge", "through", "through"]
        table["node_id"] = [-1, 12, 12]
        c = SeasonalClosures(table, np.array([10, 11, 12]), np.array([11, 12, 13]))
        assert c.through == {12: (1, 2)}
        assert list(c.edges(c.version(JANUARY))) == [0]
        assert c.through_nodes(c.version(JANUARY)) == {12}
        assert c.through_nodes(c.version(GAP_CLOSED)) == set()
        assert c.through_nodes(c.version(JULY)) == set()
        assert (c.n_edges, c.n_ways, c.n_gates, c.km) == (1, 1, 1, 0.1)

    def test_a_gate_whose_rows_do_not_meet_at_it_is_refused(self):
        table = _table([[1, 11, 12, 1, 11, 1, 4, 30, 200.0],
                        [2, 12, 13, 2, 11, 1, 4, 30, 300.0]])
        table["rule"] = "through"
        table["node_id"] = 11
        with pytest.raises(RuntimeError, match="closures.py"):
            SeasonalClosures(table, np.array([10, 11, 12]), np.array([11, 12, 13]))

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
        assert ("seasonal closures: 1 edges (1.5 km, 1 ways) in 1 windows; "
                "0 gates, no driving through 0 of them in season"
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
            assert _closed_on(w, JANUARY), w
            assert not _closed_on(w, JULY), w

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
        # Tagged the other way round: open May 20 - Oct 29.
        assert windows("Rockwell Road") == windows("Notch Road") == {(10, 30, 5, 19)}

    def test_the_router_loaded_all_of_it(self, closed_router, table):
        # A gate between two edges closes neither (docs/safety-quick-fixes.md).
        shut = table[table["rule"] == "edge"] if "rule" in table.columns else table
        assert closed_router.closures.n_edges == shut["edge"].nunique()
        assert len(_closed_rows(closed_router, JANUARY)) == shut["edge"].nunique()


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
        """Nothing but the closed edges, and driving through the gates closed
        between two edges (docs/safety-quick-fixes.md, "Gates")."""
        r = closed_router
        scores = r._edge_scores({})
        open_w = r._weights(0.5, scores, 1.0)
        shut_w = r._weights(0.5, scores, 1.0, JANUARY)
        closed = np.isin(r.eidx, list(_closed_rows(r, JANUARY)))
        for node in r.closures.through_nodes(r.closure_version(JANUARY)):
            closed[r._through_exits.get(node, [])] = True
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


# ------------------------------------------------------------------- the gates

# Two of New England's gates closed for the season on the gate and nowhere
# else (docs/safety-quick-fixes.md, "Gates"): New River Road's, `no @ (Nov-Apr)`,
# stands where two edges meet; Natural Turnpike's, `no @ (15 Dec-30 Apr)`,
# written day first, stands inside one.
NEW_RIVER_GATE = 10297054235
NATURAL_TURNPIKE_GATE = 7660919426


def _node_ll(router, i):
    return float(router.nodes["lat"].iat[i]), float(router.nodes["lon"].iat[i])


def _drives_through(route, pair):
    rows = list(route.edges.index)
    return any({a, b} == set(pair) for a, b in zip(rows, rows[1:]))


class TestGates:
    def test_the_gates_are_in_the_table(self, table):
        if "node_id" not in table.columns:
            pytest.skip("seasonal_closures.parquet predates gate rows; rerun closures.py")
        new_river = table[table["node_id"] == NEW_RIVER_GATE]
        assert sorted(new_river["rule"]) == ["through", "through"]
        assert {tuple(w) for w in new_river[["start_month", "start_day", "end_month",
                                             "end_day"]].to_numpy()} == {WINTER}
        turnpike = table[table["node_id"] == NATURAL_TURNPIKE_GATE]
        assert list(turnpike["rule"]) == ["edge"]
        assert tuple(turnpike[["start_month", "start_day", "end_month",
                               "end_day"]].iloc[0]) == (12, 15, 4, 30)

    def test_the_router_split_every_gate_between_two_edges(self, closed_router, table):
        c = closed_router.closures
        if "node_id" not in table.columns:
            pytest.skip("seasonal_closures.parquet predates gate rows; rerun closures.py")
        assert set(c.through) == set(table.loc[table["rule"] == "through", "node_id"])
        assert set(closed_router._through_exits) == set(c.through)

    def _new_river(self, r):
        a, b = r.closures.through[NEW_RIVER_GATE]
        gate = r.idx[NEW_RIVER_GATE]
        far = [int(r.edge_v_idx[e]) if int(r.edge_u_idx[e]) == gate
               else int(r.edge_u_idx[e]) for e in (a, b)]
        return (a, b), [_node_ll(r, i) for i in far]

    @pytest.mark.parametrize("pref", [0.0, 0.5])
    def test_nobody_drives_through_new_river_roads_gate_in_winter(self, closed_router, pref):
        r = closed_router
        if NEW_RIVER_GATE not in getattr(r.closures, "through", {}):
            pytest.skip("no gate rows in seasonal_closures.parquet; rerun closures.py")
        pair, (a, b) = self._new_river(r)
        s, t = r.snap(*a)[0], r.snap_destination(*b)[0]
        summer = r.route(s, t, pref, {}, on=JULY)
        assert summer is not None and _drives_through(summer, pair), \
            "the July route no longer drives through the gate"
        winter = r.route(s, t, pref, {}, on=JANUARY)
        assert winter is None or not _drives_through(winter, pair)
        # Both roads stay open up to the gate: only driving through it closes.
        assert r.route(s, r.snap_destination(*_node_ll(r, r.idx[NEW_RIVER_GATE]))[0],
                       pref, {}, on=JANUARY) is not None

    def test_natural_turnpikes_gate_shuts_on_december_15(self, closed_router, table):
        """Written day first, `15 Dec-30 Apr`, which `_RANGE` alone rejected,
        leaving the road open all winter."""
        r = closed_router
        if "node_id" not in table.columns:
            pytest.skip("seasonal_closures.parquet predates gate rows; rerun closures.py")
        e = int(table.loc[table["node_id"] == NATURAL_TURNPIKE_GATE, "edge"].iat[0])
        a, b = _node_ll(r, int(r.edge_u_idx[e])), _node_ll(r, int(r.edge_v_idx[e]))
        s, t = r.snap(*a)[0], r.snap_destination(*b)[0]
        before = r.route(s, t, 0.0, {}, on=date(2026, 12, 14))
        assert before is not None and e in set(before.edges.index)
        after = r.route(s, t, 0.0, {}, on=date(2026, 12, 15))
        assert after is None or e not in set(after.edges.index)
        assert e in _closed_rows(r, date(2027, 4, 30))
        assert e not in _closed_rows(r, date(2027, 5, 1))


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

    @pytest.mark.parametrize("start,end", [(GORHAM, AUTO_ROAD),
                                           ((42.6973, -73.1084), GREYLOCK)])
    def test_a_destination_only_a_closed_road_reaches_says_so(
            self, server, monkeypatch, start, end):
        form = {"from": self._ll(start), "to": self._ll(end), "pref": "0.5"}
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
        # 60 km, which crosses Jefferson Notch and Cherry Mountain Roads in
        # July. The 80 km loop crossed Jefferson Notch and Mount Clinton Roads
        # until loops stopped turning round on private road: that changed
        # which turnarounds the planner samples, and the one it builds now
        # misses them (docs/state-road-class.md, "Route census").
        form = {"from": self._ll(JEFFERSON), "km": "60"}
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


# ------------------------------------------- the agencies' winter closures
#
# pipeline/winter_closures.py: MVUM and NPS Public Roads joined by geometry,
# and the window table for the high passes and parks
# (docs/winter-closures-national.md).

def _line(*points):
    return shapely.LineString(points)


def _frame(geoms, **cols):
    import geopandas as gpd
    return gpd.GeoDataFrame(cols, geometry=list(geoms), crs=4326)


# A kilometre of road running north near Gunnison, CO, as two graph edges
# meeting at node 2, and a road crossing it at the junction.
_SOUTH = _line((-107.0, 38.5), (-107.0, 38.5045))
_NORTH = _line((-107.0, 38.5045), (-107.0, 38.509))
_ACROSS = _line((-107.006, 38.5045), (-106.994, 38.5045))


def _graph():
    return _frame([_SOUTH, _NORTH, _ACROSS], u=[1, 2, 3], v=[2, 4, 5],
                  length_m=[500.0, 500.0, 1046.0], name=["", "", ""])


@pytest.fixture(scope="module")
def windows_table():
    """winter_windows.json, indexed as `federal_rows` indexes it."""
    from winter_closures import _norm, load_table
    t = load_table()
    t["_parks"] = {p["unit"]: p for p in t["parks"]}
    t["_descriptions"] = {_norm(d["text"]): d for d in t["nps_descriptions"]}
    return t


class TestMvumDates:
    """MVUM's `*_datesopen` are the days a vehicle class may drive the road;
    a car is closed out on every other day."""

    def test_one_range_closes_outside_it(self):
        from winter_closures import mvum_windows
        windows, how = mvum_windows({"passengervehicle": "open",
                                     "passengervehicle_datesopen": "04/01-11/30"})
        assert windows == [(12, 1, 3, 31)]
        assert how == "passengervehicle_datesopen"

    def test_a_hunting_gap_is_its_own_window(self):
        from winter_closures import mvum_windows
        windows, _ = mvum_windows({"passengervehicle": "open",
                                   "passengervehicle_datesopen": "01/01-10/11    10/22-12/31"})
        assert windows == [(10, 12, 10, 21)]

    def test_a_range_across_new_year_closes_in_spring(self):
        from winter_closures import mvum_windows
        windows, _ = mvum_windows({"passengervehicle": "open",
                                   "passengervehicle_datesopen": "05/16-03/14"})
        assert windows == [(3, 15, 5, 15)]

    def test_all_year_passenger_dates_win_over_the_seasonal_flag(self):
        """4,101 mi are `seasonal` with passenger dates 01/01-12/31: the
        season is another vehicle class's."""
        from winter_closures import mvum_windows
        windows, _ = mvum_windows({"seasonal": "seasonal", "passengervehicle": "open",
                                   "passengervehicle_datesopen": "01/01-12/31"})
        assert windows == []

    def test_no_passenger_designation_falls_back_to_high_clearance(self):
        from winter_closures import mvum_windows
        windows, how = mvum_windows({"seasonal": "seasonal", "passengervehicle": None,
                                     "highclearancevehicle": "open",
                                     "highclearancevehicle_datesopen": "05/16-11/30"})
        assert windows == [(12, 1, 5, 15)]
        assert how == "highclearancevehicle_datesopen"

    @pytest.mark.parametrize("dates", ["", "open", "02/30-11/30", "13/01-11/30",
                                       "04/01-11/30 and more"])
    def test_seasonal_with_no_readable_dates_closes_for_the_long_season(self, dates):
        """Trap 2: unreadable resolves toward closed."""
        from winter_closures import UNKNOWN_SEASON, mvum_windows
        windows, _ = mvum_windows({"seasonal": "Seasonal ", "passengervehicle": "open",
                                   "passengervehicle_datesopen": dates})
        assert windows == [UNKNOWN_SEASON]

    def test_yearlong_with_no_dates_stays_open(self):
        from winter_closures import mvum_windows
        assert mvum_windows({"seasonal": "yearlong", "passengervehicle": "open",
                             "passengervehicle_datesopen": None})[0] == []

    def test_feb_29_is_a_day(self):
        from winter_closures import mvum_open_ranges
        assert mvum_open_ranges("09/01-02/29") == [(9, 1, 2, 29)]


class TestNpsDescriptions:
    """NPS Public Roads: dated prose read at its longer end, a park's window
    where there are no dates, and the long season where there is no park."""

    def test_teton_park_road(self, windows_table):
        from winter_closures import nps_windows
        windows, how = nps_windows({"UNITCODE": "GRTE", "SEASONAL": "Yes",
                                    "SEASDESC": "Seasonal Closure Nov1 to May1.  "}, windows_table)
        assert windows == [(11, 1, 5, 1)] and how == "description"

    def test_a_holiday_is_read_at_its_earliest(self, windows_table):
        from winter_closures import nps_windows
        windows, _ = nps_windows({"UNITCODE": "ACAD", "SEASONAL": "Yes",
                                  "SEASDESC": "winter closure Columbus Day to May 1"}, windows_table)
        assert windows == [(10, 8, 5, 1)]

    def test_no_dates_takes_the_parks_window(self, windows_table):
        from winter_closures import nps_windows
        park = windows_table["_parks"]["YOSE"]["window"]
        assert nps_windows({"UNITCODE": "YOSE", "SEASONAL": "Yes",
                            "SEASDESC": "Winter"}, windows_table)[0] == [park]

    def test_yellowstone_unknown_is_seasonal(self, windows_table):
        """1,979 of Yellowstone's 2,007 segments say Unknown."""
        from winter_closures import nps_windows
        park = windows_table["_parks"]["YELL"]["window"]
        assert nps_windows({"UNITCODE": "YELL", "SEASONAL": "Unknown"}, windows_table)[0] == [park]

    def test_unknown_elsewhere_closes_nothing(self, windows_table):
        from winter_closures import nps_windows
        assert nps_windows({"UNITCODE": "GOGA", "SEASONAL": "Unknown"}, windows_table)[0] == []

    def test_seasonal_in_a_park_without_a_window_gets_the_long_season(self, windows_table):
        from winter_closures import UNKNOWN_SEASON, nps_windows
        assert nps_windows({"UNITCODE": "MORA", "SEASONAL": "Yes",
                            "SEASDESC": None}, windows_table)[0] == [UNKNOWN_SEASON]

    def test_a_park_without_winter_closes_nothing(self, windows_table):
        """Golden Gate flags Lincoln Blvd seasonal with no dates."""
        from winter_closures import nps_windows
        assert nps_windows({"UNITCODE": "GOGA", "SEASONAL": "Yes",
                            "SEASDESC": None}, windows_table)[0] == []

    def test_an_unseen_description_resolves_toward_closed(self, windows_table):
        from winter_closures import nps_windows
        windows, _ = nps_windows({"UNITCODE": "GRTE", "SEASONAL": "Yes",
                                  "SEASDESC": "Closed until the snow melts"}, windows_table)
        assert windows == [windows_table["_parks"]["GRTE"]["window"]]

    def test_the_permit_rule_is_left_alone(self, windows_table):
        """The permit rule is the owner's open decision."""
        from winter_closures import nps_windows
        assert nps_windows({"UNITCODE": "REDW", "SEASONAL": "Yes",
                            "SEASDESC": "Permit Required"}, windows_table)[0] == []


class TestTheWindowTable:
    """Trap 2: every window carries its operator source and access date."""

    def test_every_road_and_park_is_sourced(self, windows_table):
        for entry in windows_table["roads"] + windows_table["parks"]:
            assert entry["source"].startswith("https://"), entry
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["accessed"]), entry
            assert entry["basis"], entry

    def test_every_window_is_real_days(self, windows_table):
        from closures import _LAST_DAY
        windows = [e["window"] for e in windows_table["roads"] + windows_table["parks"]
                   if e["window"]]
        windows += [w for d in windows_table["nps_descriptions"] for w in d["windows"]]
        for sm, sd, em, ed in windows:
            assert 1 <= sm <= 12 and 1 <= em <= 12
            assert 1 <= sd <= _LAST_DAY[sm - 1] and 1 <= ed <= _LAST_DAY[em - 1]

    def test_every_description_says_what_it_does(self, windows_table):
        from winter_closures import _norm
        texts = [_norm(d["text"]) for d in windows_table["nps_descriptions"]]
        assert len(texts) == len(set(texts))
        for d in windows_table["nps_descriptions"]:
            assert d["closes"] in ("dates", "park", "no")
            assert bool(d["windows"]) == (d["closes"] == "dates"), d["text"]

    def test_road_waypoints_are_inside_the_lower_48(self, windows_table):
        kept = [k for p in windows_table["parks"] for k in p.get("except", [])]
        for entry in windows_table["roads"] + kept:
            assert len(entry["waypoints"]) >= 2
            for lon, lat in entry["waypoints"]:
                assert -125 < lon < -66.9 and 24.4 < lat < 49.5

    def test_the_kancamagus_is_in_no_window(self, windows_table):
        """The year-round control (docs/us-map-data-findings.md §4)."""
        for entry in windows_table["roads"]:
            assert "kancamagus" not in entry["id"].lower()


class TestTheGeometryJoin:
    """Trap 1: joined by where the roads are, never by what they are called."""

    def test_a_line_along_an_edge_matches_it_whole(self):
        from winter_closures import match_lines
        m = match_lines(_graph().geometry, _frame([_line((-107.00005, 38.4995),
                                                         (-107.00005, 38.5050))]).geometry)
        assert m.loc[m["edge"] == 0, "share"].item() == pytest.approx(1.0)
        assert (m["edge"] == 2).sum() == 0

    def test_a_crossing_road_picks_up_nothing(self):
        """The crossing edge passes within 15 m of the seasonal road for 30 m
        either side of the junction, at right angles."""
        from winter_closures import closed_by_lines, match_lines
        m = match_lines(_graph().geometry, _frame([_line((-107.0, 38.4995),
                                                         (-107.0, 38.509))]).geometry)
        assert set(closed_by_lines(m, [[(12, 1, 3, 31)]])) == {0, 1}

    def test_a_road_30_m_away_does_not_match(self):
        from winter_closures import match_lines
        m = match_lines(_graph().geometry, _frame([_line((-107.00035, 38.5),
                                                         (-107.00035, 38.509))]).geometry)
        assert m.empty

    def test_a_renamed_road_still_matches(self):
        """Clingmans Dome Road became Kuwohi Road in 2024. The edge's name
        and the line's play no part."""
        from winter_closures import match_lines
        g = _graph()
        g["name"] = ["Kuwohi Road", "Kuwohi Road", "Other"]
        lines = _frame([_SOUTH], RDNAME=["Clingmans Dome Road"])
        assert 0 in set(match_lines(g.geometry, lines.geometry)["edge"])

    def test_an_edge_mostly_off_the_closed_road_stays_open(self):
        from winter_closures import closed_by_lines, match_lines
        # 40% of the south edge.
        m = match_lines(_graph().geometry, _frame([_line((-107.0, 38.5027),
                                                         (-107.0, 38.5045))]).geometry)
        assert closed_by_lines(m, [[(12, 1, 3, 31)]]) == {}

    def test_two_seasons_on_one_edge_close_it_for_both(self):
        from winter_closures import closed_by_lines, match_lines
        lines = _frame([_line((-107.0, 38.5), (-107.0, 38.50225)),
                        _line((-107.0, 38.50225), (-107.0, 38.5045))])
        m = match_lines(_graph().geometry, lines.geometry)
        closed = closed_by_lines(m, [[(12, 1, 3, 31)], [(11, 1, 4, 30)]])
        assert set(closed[0]) == {(12, 1, 3, 31), (11, 1, 4, 30)}

    def test_no_match_at_all_closes_nothing(self):
        from winter_closures import closed_by_lines, match_lines
        far = _frame([_line((-100.0, 30.0), (-100.0, 30.01))])
        assert closed_by_lines(match_lines(_graph().geometry, far.geometry), [[]]) == {}

    def test_an_open_line_closes_nothing(self):
        from winter_closures import closed_by_lines, match_lines
        m = match_lines(_graph().geometry, _frame([_SOUTH]).geometry)
        assert closed_by_lines(m, [[]]) == {}


class TestTheTableRoads:
    """A table road is the graph's path through its waypoints."""

    def test_the_path_through_the_waypoints(self):
        from winter_closures import path_edges
        rows, why = path_edges(_graph(), [(-107.0, 38.5), (-107.0, 38.509)])
        assert why is None and sorted(rows) == [0, 1]

    def test_a_waypoint_off_the_graph_places_nothing(self):
        from winter_closures import path_edges
        rows, why = path_edges(_graph(), [(-107.0, 38.5), (-107.1, 38.6)])
        assert rows == [] and why.startswith("waypoint 2 is")

    def test_a_road_replaces_its_parks_window_and_not_the_agencies(self):
        """A table road's window beats its park's on the edges they share; an
        MVUM or dated NPS window still stands beside it."""
        from winter_closures import federal_rows, load_table
        table = load_table()
        # A window unlike ROMO's own, so the test can tell which one won.
        table["parks"] = [dict(p, window=(11, 15, 4, 15)) if p["unit"] == "ROMO" else p
                          for p in table["parks"]]
        table["roads"] = [{"id": "test_road", "window": (10, 1, 7, 10),
                           "source": "https://example.org", "accessed": "2026-10-18",
                           "basis": "test", "waypoints": [(-107.0, 38.5), (-107.0, 38.5045)]}]
        nps = _frame([_SOUTH, _NORTH], UNITCODE=["ROMO", "ROMO"], SEASONAL=["Yes", "Yes"],
                     SEASDESC=["Closed in Winter", "Seasonal Closure Nov1 to May1"])
        rows, _ = federal_rows(_graph(), None, nps, table)
        by_edge = {}
        for r in rows:
            by_edge.setdefault(r["edge"], set()).add(
                (r["start_month"], r["start_day"], r["end_month"], r["end_day"]))
        assert by_edge[0] == {(10, 1, 7, 10)}           # the road's, not the park's
        assert by_edge[1] == {(11, 1, 5, 1)}            # dated, untouched

    def test_rows_are_in_the_seasonal_format(self):
        from closures import SEASONAL_COLUMNS
        from winter_closures import federal_rows
        mvum = _frame([_SOUTH], passengervehicle=["open"],
                      passengervehicle_datesopen=["04/01-11/30"], forestname=["GMUG"], id=["1"])
        rows, report = federal_rows(_graph(), mvum, None)
        assert [r["edge"] for r in rows] == [0]
        assert list(rows[0]) == SEASONAL_COLUMNS
        assert rows[0]["rule"] == "edge" and rows[0]["node_id"] == -1
        assert report["mvum"] == (1, pytest.approx(0.5))


# The New England graph against the agencies' layers. New England changes only
# where a source says so (docs/winter-closures-national.md, "New England").
_NE_BOXES = {
    "kancamagus": (-71.70, 43.95, -71.15, 44.10),
    "auto_road": (-71.32, 44.24, -71.20, 44.30),
    "park_loop": (-68.30, 44.30, -68.17, 44.40),
}


@pytest.fixture(scope="module")
def ne_winter():
    """(edges, rows) for the graph's edges in _NE_BOXES, joined as
    closures.py joins them."""
    import geopandas as gpd
    from winter_closures import federal_rows
    federal = DATA.parent / "raw" / "federal"
    missing = [str(p) for p in (DATA / "graph_edges.parquet", federal / "mvum_roads.parquet",
                                federal / "nps_roads.parquet") if not p.exists()]
    if missing:
        pytest.skip(f"missing {', '.join(missing)}: build the graph and run "
                    "pipeline/federal_layers.py")
    edges = gpd.read_parquet(DATA / "graph_edges.parquet",
                             columns=["u", "v", "length_m", "name", "ref", "geometry"])
    keep = np.zeros(len(edges), bool)
    for w, s, e, n in _NE_BOXES.values():
        b = edges.geometry.bounds
        keep |= ((b["minx"] >= w) & (b["maxx"] <= e) & (b["miny"] >= s)
                 & (b["maxy"] <= n)).to_numpy()
    edges = edges[keep].reset_index(drop=True)
    w, s, e, n = (-71.8, 43.9, -68.1, 44.45)
    mvum = gpd.read_parquet(federal / "mvum_roads.parquet").cx[w:e, s:n].reset_index(drop=True)
    nps = gpd.read_parquet(federal / "nps_roads.parquet").cx[w:e, s:n].reset_index(drop=True)
    rows, _ = federal_rows(edges, mvum, nps)
    return edges, pd.DataFrame(rows)


def _km_closed(ne_winter, pattern, box, day):
    edges, rows = ne_winter
    w, s, e, n = _NE_BOXES[box]
    b = edges.geometry.bounds
    road = edges[(b["minx"] >= w) & (b["maxx"] <= e) & (b["miny"] >= s) & (b["maxy"] <= n)
                 & (edges["name"].fillna("").str.contains(pattern)
                    | edges["ref"].fillna("").str.contains(pattern))]
    assert len(road), f"no {pattern} in the graph"
    on = rows[rows["edge"].isin(road.index)]
    shut = {r.edge for r in on.itertuples()
            if in_window((r.start_month, r.start_day, r.end_month, r.end_day),
                         (day.month, day.day))}
    return road.loc[sorted(shut), "length_m"].sum() / 1000.0, road["length_m"].sum() / 1000.0


class TestNewEnglandWinter:
    def test_the_kancamagus_stays_open(self, ne_winter):
        """The year-round control (docs/us-map-data-findings.md §4)."""
        for day in (JANUARY, JULY, date(2026, 11, 5)):
            assert _km_closed(ne_winter, "Kancamagus|NH 112", "kancamagus", day)[0] == 0

    def test_tripoli_road_closes_for_winter_by_mvum(self, ne_winter):
        """White Mountain NF, untagged in OSM. 14.7 of the 16.7 km close on
        the graph of 2026-08-25; the rest is road MVUM does not mark."""
        closed, total = _km_closed(ne_winter, "Tripoli", "kancamagus", JANUARY)
        assert closed > 0.8 * total
        assert _km_closed(ne_winter, "Tripoli", "kancamagus", JULY)[0] == 0

    def test_the_auto_road_closes_until_daily_driving_begins(self, ne_winter):
        """Weekends only until May 22 in 2026; OSM's own tag ends Apr 30."""
        closed, total = _km_closed(ne_winter, "Auto Road", "auto_road", date(2027, 5, 15))
        assert closed > 0.9 * total
        assert _km_closed(ne_winter, "Auto Road", "auto_road", JULY)[0] == 0

    def test_acadias_park_loop_road_closes_by_nps(self, ne_winter):
        """Paved roads open Apr 15 - Dec 1; OSM leaves Acadia untagged."""
        closed, total = _km_closed(ne_winter, "Park Loop", "park_loop", JANUARY)
        assert closed > 0.5 * total
        assert _km_closed(ne_winter, "Park Loop", "park_loop", JULY)[0] == 0
