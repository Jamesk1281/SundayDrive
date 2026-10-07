"""Roads closed to cars all year: `motor_vehicle=no` roads, locked and private
gates, blocks, chains, bollards and fords stay off every route, loop and
reroute, and nothing starts a driver on the far side of one.

The access rule, the barrier rule and the join are pure and run anywhere. The
rest needs the built graph and `closed_to_cars.parquet` (pipeline/closures.py)
and skips without them, saying which. docs/closed-roads.md has the decisions,
the measurements and the cases these are named after.
"""

import math
import sys
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import shapely
from pyproj import Transformer

from closures import join_closed_to_cars
from common import (CAR_ACCESS_KEYS, CLOSED_TO_CARS, CRS_METERS, barrier_closes,
                    car_access, closed_to_cars)
from conftest import DATA, ROOT, ROUTER_DATA
from router import ClosedToCars, Router

_TO_M = Transformer.from_crs(4326, CRS_METERS, always_xy=True)
_TO_LL = Transformer.from_crs(CRS_METERS, 4326, always_xy=True)


# ------------------------------------------------------------- the access rule

class TestWhoMayDrive:
    """OSM's transport-mode hierarchy: the most specific key present wins
    (docs/closed-roads.md, decision 3)."""

    @pytest.mark.parametrize("value", sorted(CLOSED_TO_CARS))
    @pytest.mark.parametrize("key", CAR_ACCESS_KEYS)
    def test_every_closed_value_closes_under_every_car_key(self, key, value):
        assert closed_to_cars({key: value}) == f"{key}={value}"

    @pytest.mark.parametrize("value", ["yes", "permissive", "designated",
                                       "destination", "customers", "discouraged",
                                       "unknown", "residents", "hov"])
    def test_the_rest_is_open(self, value):
        """`destination` and `customers` are legal for a driver with business
        there, and an unrecognised value is not a reason to close a road."""
        assert closed_to_cars({"motor_vehicle": value}) is None

    def test_an_untagged_road_is_open(self):
        assert car_access({"highway": "residential"}) is None
        assert closed_to_cars({"highway": "residential"}) is None

    @pytest.mark.parametrize("tags", [
        {"access": "no", "motor_vehicle": "yes"},
        {"vehicle": "no", "motorcar": "yes"},
        {"motor_vehicle": "no", "motorcar": "yes"},
        {"access": "private", "vehicle": "no", "motor_vehicle": "destination"},
    ])
    def test_a_more_specific_key_opens_what_a_general_one_closes(self, tags):
        """Trap 9. A rule that closes on any restrictive tag shuts all of
        these, and the first is the one override the old filter knew."""
        assert closed_to_cars(tags) is None

    @pytest.mark.parametrize("tags,closer", [
        ({"access": "yes", "motor_vehicle": "no"}, "motor_vehicle=no"),
        ({"vehicle": "yes", "motor_vehicle": "private"}, "motor_vehicle=private"),
        ({"motor_vehicle": "yes", "motorcar": "no"}, "motorcar=no"),
        ({"access": "yes", "vehicle": "no"}, "vehicle=no"),
    ])
    def test_and_a_more_specific_key_closes_what_a_general_one_opens(self, tags, closer):
        assert closed_to_cars(tags) == closer

    def test_vehicle_binds_a_car(self):
        """Five ways on this extract are closed only by `vehicle=no`."""
        assert closed_to_cars({"vehicle": "no"}) == "vehicle=no"

    def test_subkeys_are_not_transport_modes(self):
        """Crane Road's gate also carries `access:delivery=no`, which says
        nothing about anyone else."""
        assert closed_to_cars({"access:delivery": "no"}) is None
        assert closed_to_cars({"motor_vehicle:conditional": "no @ (Nov-Apr)"}) is None

    def test_values_are_read_without_case_or_spaces(self):
        assert closed_to_cars({"motor_vehicle": " No "}) == "motor_vehicle=no"


# -------------------------------------------------------------- the barrier rule

class TestWhatStopsACar:
    """Decision 4: gates pass unless their own tags close them, everything else
    blocks unless its own tags open it; decision 5: fords block."""

    @pytest.mark.parametrize("barrier", ["gate", "lift_gate", "swing_gate",
                                         "cattle_grid", "toll_booth",
                                         "border_control", "entrance", "no"])
    def test_an_untagged_gate_is_open(self, barrier):
        """As in OSRM's car profile: most untagged gates are farm and park gates
        standing open, and 1,635 of them stand on this graph's roads."""
        assert barrier_closes({"barrier": barrier}) is None

    @pytest.mark.parametrize("tags,why", [
        ({"barrier": "gate", "access": "no", "access:delivery": "no"},
         "barrier=gate, access=no"),                       # Crane Road's
        ({"barrier": "gate", "access": "private"}, "barrier=gate, access=private"),
        ({"barrier": "lift_gate", "motor_vehicle": "private"},
         "barrier=lift_gate, motor_vehicle=private"),
        ({"barrier": "swing_gate", "motor_vehicle": "permit"},
         "barrier=swing_gate, motor_vehicle=permit"),
        ({"barrier": "gate", "locked": "yes"}, "barrier=gate, locked=yes"),
    ])
    def test_a_gate_its_own_tags_close_is_closed(self, tags, why):
        assert barrier_closes(tags) == why

    def test_a_gate_a_car_key_opens_stays_open(self):
        assert barrier_closes({"barrier": "gate", "access": "no",
                               "motor_vehicle": "yes"}) is None

    @pytest.mark.parametrize("barrier", ["block", "bollard", "chain",
                                         "jersey_barrier", "debris", "log", "rope",
                                         "fence", "yes", "planter"])
    def test_anything_else_blocks(self, barrier):
        assert barrier_closes({"barrier": barrier}) == f"barrier={barrier}"

    def test_its_own_tags_can_open_a_blocking_barrier(self):
        assert barrier_closes({"barrier": "bollard", "motor_vehicle": "yes"}) is None
        assert barrier_closes({"barrier": "chain", "access": "permissive"}) is None

    def test_the_named_barriers(self):
        """Holman Street's blocks and Stanley Street's chain, as tagged."""
        assert barrier_closes({"barrier": "block", "motor_vehicle": "no"}) \
            == "barrier=block, motor_vehicle=no"
        assert barrier_closes({"barrier": "chain", "bicycle": "yes", "foot": "yes",
                               "motor_vehicle": "no"}) \
            == "barrier=chain, motor_vehicle=no"

    def test_a_ford_blocks_whatever_else_it_says(self):
        assert barrier_closes({"ford": "yes"}) == "ford=yes"
        assert barrier_closes({"ford": "yes", "motor_vehicle": "yes"}) == "ford=yes"
        assert barrier_closes({"ford": "no"}) is None

    def test_a_crossing_kerb_on_the_centreline_does_not_close_the_road(self):
        """The one departure from decision 4 as written: every kerb on a
        drivable way here is a crossing's, Broadway in Cambridge among them
        (docs/closed-roads.md)."""
        assert barrier_closes({"barrier": "kerb", "highway": "crossing",
                               "kerb": "lowered"}) is None
        assert barrier_closes({"barrier": "kerb"}) is None
        assert barrier_closes({"barrier": "kerb", "access": "no"}) \
            == "barrier=kerb, access=no"

    def test_a_node_that_is_neither_closes_nothing(self):
        assert barrier_closes({"highway": "traffic_signals"}) is None


# -------------------------------------------------------------------- the join

# Junction 1 to junction 2 by two roads: one straight north through nodes 98
# (a quarter of the way) and 99 (halfway), one bowing about 80 m east, as a
# parallel road does. Junction 2 continues north to 3, and 4 branches off 2.
_N = {1: (-72.0, 44.0), 98: (-72.0, 44.0025), 99: (-72.0, 44.005),
      2: (-72.0, 44.01), 3: (-72.0, 44.02), 4: (-71.99, 44.01)}
_STRAIGHT = [_N[1], _N[98], _N[99], _N[2]]
_BOWED = [_N[1], (-71.999, 44.005), _N[2]]


def _edges(*spec):
    """A graph_edges frame from (u, v, coordinates) triples."""
    lines = [shapely.LineString(c) for _, _, c in spec]
    lengths = [shapely.length(shapely.LineString(
        np.column_stack(_TO_M.transform(*np.asarray(c).T)))) for _, _, c in spec]
    return gpd.GeoDataFrame({"u": [u for u, _, _ in spec], "v": [v for _, v, _ in spec],
                             "length_m": lengths,
                             "name": [f"road {i}" for i in range(len(spec))]},
                            geometry=lines, crs=4326)


def _way(way_id, refs, closes=""):
    return {"way_id": way_id, "name": "", "closes": closes,
            "kind": "way", "refs": refs, "coords": [_N[r] for r in refs]}


def _barrier(node, owners, why="barrier=gate, access=no"):
    return {node: (*_N[node], why, owners)}


class TestTheJoin:
    def test_a_barrier_closes_the_edge_it_stands_on_and_says_where(self):
        """Trap 3. Found by position: the barrier is a quarter of the way along,
        so a midpoint test would miss it."""
        edges = _edges((1, 2, _STRAIGHT), (1, 2, _BOWED))
        table, left = join_closed_to_cars([_way(7, [1, 98, 99, 2])],
                                          _barrier(98, [0]), edges)
        assert list(table["edge"]) == [0]
        row = table.iloc[0]
        assert (row["rule"], row["kind"], row["osm_type"], row["osm_id"]) == \
            ("edge", "barrier", "node", 98)
        assert row["at_m"] == pytest.approx(edges["length_m"].iat[0] / 4, abs=1.0)
        assert not any(left.values())

    def test_an_open_road_between_the_same_junctions_stays_open(self):
        """Both edges have both ends among the way's nodes, and `route` keeps
        only the cheaper of two parallel edges, so closing both would close the
        open road too."""
        edges = _edges((1, 2, _BOWED), (1, 2, _STRAIGHT))
        table, _ = join_closed_to_cars([_way(7, [1, 98, 99, 2])],
                                       _barrier(98, [0]), edges)
        assert list(table["edge"]) == [1]

    def test_a_barrier_between_two_edges_closes_neither(self):
        """Trap 1: each road is open up to it. One "through" row per edge."""
        edges = _edges((1, 2, _STRAIGHT), (2, 3, [_N[2], _N[3]]))
        table, _ = join_closed_to_cars([_way(7, [1, 98, 99, 2]), _way(8, [2, 3])],
                                       _barrier(2, [0, 1]), edges)
        assert set(table["rule"]) == {"through"}
        assert sorted(table["edge"]) == [0, 1]
        at = dict(zip(table["edge"], table["at_m"]))
        assert at[0] == pytest.approx(edges["length_m"].iat[0])
        assert at[1] == 0.0

    def test_a_barrier_at_a_dead_end_or_a_junction_closes_nothing(self):
        edges = _edges((1, 2, _STRAIGHT), (2, 3, [_N[2], _N[3]]),
                       (2, 4, [_N[2], _N[4]]))
        ways = [_way(7, [1, 98, 99, 2]), _way(8, [2, 3]), _way(9, [2, 4])]
        table, left = join_closed_to_cars(ways, {**_barrier(3, [1]),
                                                 **_barrier(2, [0, 1, 2])}, edges)
        assert table.empty
        assert left["dead end"] == [3]
        assert left["junction"] == [2]

    def test_a_barrier_on_no_edge_of_the_graph_is_counted(self):
        edges = _edges((1, 2, _BOWED))
        _, left = join_closed_to_cars([_way(7, [1, 98, 99, 2])],
                                      _barrier(98, [0]), edges)
        assert left["not in the graph"] == [98]

    def test_a_closed_way_closes_its_own_edges_only(self):
        edges = _edges((1, 2, _BOWED), (1, 2, _STRAIGHT), (2, 3, [_N[2], _N[3]]))
        table, _ = join_closed_to_cars(
            [_way(7, [1, 98, 99, 2], closes="motor_vehicle=no")], {}, edges)
        assert list(table["edge"]) == [1]
        assert table.iloc[0]["tag"] == "motor_vehicle=no"
        assert np.isnan(table.iloc[0]["at_m"])


# ------------------------------------------------------------------ the loader

def _row(edge, u, v, rule="edge", osm_type="way", osm_id=7, at_m=np.nan):
    return {"edge": edge, "u": u, "v": v, "rule": rule, "kind": "way",
            "osm_type": osm_type, "osm_id": osm_id, "tag": "motor_vehicle=no",
            "at_m": at_m, "name": "", "length_m": 100.0}


class TestTheTableIsRefusedWhenStale:
    def test_rows_that_name_other_edges_are_refused(self):
        table = pd.DataFrame([_row(0, 10, 11), _row(1, 11, 99)])
        with pytest.raises(RuntimeError, match="closures.py"):
            ClosedToCars(table, np.array([10, 11]), np.array([11, 12]))

    def test_a_row_past_the_end_of_the_graph_is_refused(self):
        with pytest.raises(RuntimeError, match="another graph"):
            ClosedToCars(pd.DataFrame([_row(5, 10, 11)]),
                         np.array([10]), np.array([11]))

    def test_a_barrier_between_edges_that_do_not_meet_there_is_refused(self):
        table = pd.DataFrame([_row(0, 10, 11, "through", "node", 12),
                              _row(1, 11, 12, "through", "node", 12)])
        with pytest.raises(RuntimeError, match="do not name two edges"):
            ClosedToCars(table, np.array([10, 11]), np.array([11, 12]))

    def test_a_current_table_loads(self):
        table = pd.DataFrame([_row(0, 10, 11),
                              _row(1, 11, 12, osm_type="node", osm_id=5, at_m=30.0),
                              _row(1, 11, 12, osm_type="node", osm_id=6, at_m=10.0)])
        c = ClosedToCars(table, np.array([10, 11]), np.array([11, 12]))
        assert c.edges.tolist() == [0, 1]
        assert c.whole.tolist() == [0]
        assert c.at[1].tolist() == [10.0, 30.0]
        assert (c.n_ways, c.n_barriers) == (1, 2)

    def test_the_router_says_when_it_has_no_table(self, tmp_path, capsys):
        """The box's journal is the only place a missing mask would show."""
        stub = SimpleNamespace(edges=pd.DataFrame({"u": [10], "v": [11]}))
        Router._read_closed_to_cars(stub, tmp_path)
        assert stub.closed_to_cars is None
        Router._close_to_cars(stub)
        assert "closed to cars: none" in capsys.readouterr().out
        assert stub._car_closed_slots is None


# ------------------------------------------------------------------- the table

@pytest.fixture(scope="module")
def table():
    path = DATA / "closed_to_cars.parquet"
    if not path.exists():
        pytest.skip("closed_to_cars.parquet missing — run pipeline/closures.py")
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def closed_router(router, table):
    """The session router, which must have loaded the table."""
    assert router.closed_to_cars is not None
    return router


# The brief's cases, each with the app's exact parameters: pref 0.5, every
# weight 1.00 except town (docs/closed-roads.md, "Result").
APP = {"town": 0.0}
BOSTON = (42.3601, -71.0589)
CRANE = ((42.1396268, -71.2613399), (42.1311784, -72.7617144))
CRANE_GATE = 6295163812                 # barrier=gate, access=no, 21 m into its edge
HOLMAN = ((42.200999, -71.691789), (44.9826946, -70.5827565))
HOLMAN_BLOCKS = (7554833357, 7317775708)
STANLEY = ((41.6274964, -72.9611079), (43.6324515, -72.3962464))
STANLEY_CHAIN = 6742373740
# A gate with access=no between Eagle Avenue and Arthur Paquin Way, each road
# open up to it; driving round is 0.93 km where driving through was 0.53 km.
EAGLE_GATE = 6410325983
# Up Watatic Mountain Road, past its locked gate, and up HMS Halsted Drive,
# past a gate standing between two of its edges: nothing a car may drive
# reaches either.
WATATIC = (42.7060860, -71.8884657)
WATATIC_GATE = 62477321
HALSTED = (42.2537317, -70.9126381)
HALSTED_GATE = 3256154895
# Where a 40 km loop started that went through Creeper Hill Road's private
# gate (barrier=gate, motor_vehicle=private).
CREEPER_HILL_START = (42.2970948, -71.7684485)
CREEPER_HILL_GATE = 61705730
# Turner Road's edge with two barriers 18 m apart, and Blunt Park Road, closed
# to motor vehicles through the park.
TURNER_BARRIERS = (62878724, 62903146)
BLUNT_PARK_WAY = 9321988


def _line_m(route):
    lon, lat = np.asarray(route.line.coords).T
    return shapely.LineString(np.column_stack(_TO_M.transform(lon, lat)))


def _feature_m(feature):
    lon, lat = np.asarray(feature["geometry"]["coordinates"]).T
    return shapely.LineString(np.column_stack(_TO_M.transform(lon, lat)))


def _crosses(line, point):
    """Whether a drive passes `point`: within a metre of its line, and not
    where it starts or ends, which is driving up to it."""
    ends = (shapely.Point(line.coords[0]), shapely.Point(line.coords[-1]))
    return point.distance(line) < 1.0 and min(e.distance(point) for e in ends) > 1.0


def _barrier_m(router, table, osm_id):
    row = table[table["osm_id"] == osm_id].iloc[0]
    if row["rule"] == "through":
        i = router.idx[osm_id]
        return shapely.Point(router._nx[i], router._ny[i])
    return router._edge_geom_m[int(row["edge"])].interpolate(row["at_m"])


def _ll(point):
    lon, lat = _TO_LL.transform(point.x, point.y)
    return lat, lon


def _toward_v(line, along):
    """The compass bearing of `line` at `along`, driving from u toward v."""
    a = line.interpolate(max(0.0, along - 1.0))
    b = line.interpolate(min(line.length, along + 1.0))
    return math.degrees(math.atan2(b.x - a.x, b.y - a.y)) % 360.0


def _gate_edge(router, table, osm_id):
    row = table[(table["osm_id"] == osm_id) & (table["rule"] == "edge")].iloc[0]
    e = int(row["edge"])
    return (e, router._edge_geom_m[e], float(row["at_m"]),
            int(router.edge_u_idx[e]), int(router.edge_v_idx[e]))


class TestTheTable:
    def test_the_named_elements_are_there(self, table):
        def rows(osm_id):
            return table[table["osm_id"] == osm_id]
        crane = rows(CRANE_GATE)
        assert list(crane["rule"]) == ["edge"]
        assert crane["tag"].iat[0] == "barrier=gate, access=no"
        assert crane["at_m"].iat[0] == pytest.approx(21.1, abs=0.5)
        for block in HOLMAN_BLOCKS:
            assert rows(block)["tag"].iat[0] == "barrier=block, motor_vehicle=no"
        assert rows(STANLEY_CHAIN)["tag"].iat[0] == "barrier=chain, motor_vehicle=no"
        assert sorted(rows(EAGLE_GATE)["rule"]) == ["through", "through"]
        assert (table["name"] == "Southeast Expressway HOV Lane").any()

    def test_crossing_kerbs_on_broadway_close_nothing(self, table):
        """The decision 4 departure: Broadway's signalled crossing in Cambridge
        is tagged barrier=kerb on the road's centreline."""
        assert not (table["osm_id"] == 1053454390).any()

    def test_the_router_loaded_all_of_it(self, closed_router, table):
        c = closed_router.closed_to_cars
        shut = set(table.loc[table["rule"] == "edge", "edge"])
        # The roads a state DOT closes arrive as rows of the same table
        # (docs/state-road-class.md), and must all be there too.
        if closed_router.state_roads is not None:
            shut |= set(closed_router.state_roads.edges["closed"].tolist())
        assert len(c.edges) == len(shut)
        assert len(c.through) == table.loc[table["rule"] == "through", "osm_id"].nunique()
        assert len(closed_router._through_split) == len(c.through)


# ------------------------------------------------------------------ the routes

def _cases():
    out = []
    for name, (a, b), barriers, crossed_before in (
            ("Crane Road", CRANE, (CRANE_GATE,), (0.0, 0.5)),
            # Before, only the scenic arm took Holman Street.
            ("Holman Street", HOLMAN, HOLMAN_BLOCKS, (0.5,)),
            ("Stanley Street", STANLEY, (STANLEY_CHAIN,), (0.0, 0.5))):
        for pref in (0.0, 0.5):
            out.append(pytest.param(a, b, barriers, pref, pref in crossed_before,
                                    id=f"{name}-{pref}"))
    return out


class TestTheBriefsCases:
    @pytest.mark.parametrize("a,b,barriers,pref,crossed_before", _cases())
    def test_the_route_no_longer_passes_the_barrier(self, closed_router, table, monkeypatch,
                                                    a, b, barriers, pref, crossed_before):
        r = closed_router
        s, _ = r.snap(*a)
        t, _ = r.snap_destination(*b)
        points = [_barrier_m(r, table, o) for o in barriers]
        route = r.route(s, t, pref, APP)
        assert route is not None
        assert not any(_crosses(_line_m(route), p) for p in points)
        # The control: with nothing closed to cars, the same request drives
        # through, as production did on 2026-10-05.
        monkeypatch.setattr(r, "_car_closed_slots", None)
        before = r.route(s, t, pref, APP)
        assert any(_crosses(_line_m(before), p) for p in points) == crossed_before


class TestTheCraneRoadReroute:
    """Case 5: a car stopped 57 m short of the gate, which stands 21 m from the
    edge's far end, so the car is on the near side, 78 m from the far end."""

    @pytest.mark.parametrize("facing", ["away", "toward", None])
    @pytest.mark.parametrize("pref", [0.0, 0.5])
    def test_the_reroute_does_not_go_back_through_the_gate(self, closed_router, table,
                                                           facing, pref):
        r = closed_router
        e, line, gate, u, v = _gate_edge(r, table, CRANE_GATE)
        along = gate + 57.0
        away = _toward_v(line, along)
        heading = {"away": away, "toward": (away + 180.0) % 360.0, None: None}[facing]
        s, _ = r.snap(*_ll(line.interpolate(along)), heading=heading)
        assert s == v, "the reroute starts on the far side of the gate"
        t, _ = r.snap_destination(*CRANE[1])
        route = r.route(s, t, pref, APP, heading=heading)
        assert route is not None
        assert not _crosses(_line_m(route), line.interpolate(gate))


class TestTheSnapStaysOnItsSide:
    """Trap 2: `snap` used to take the nearer end, or the end ahead, and either
    can be past the barrier."""

    def test_a_point_whose_nearer_end_is_past_the_gate(self, closed_router, table):
        r = closed_router
        e, line, gate, u, v = _gate_edge(r, table, CRANE_GATE)
        point = line.interpolate(gate + 19.0)
        to_u = math.hypot(r._nx[u] - point.x, r._ny[u] - point.y)
        to_v = math.hypot(r._nx[v] - point.x, r._ny[v] - point.y)
        assert to_u < to_v, "the nearer end is no longer past the gate; this tests nothing"
        assert r.snap(*_ll(point))[0] == v

    def test_a_heading_toward_the_gate_does_not_carry_the_start_through_it(
            self, closed_router, table):
        r = closed_router
        e, line, gate, u, v = _gate_edge(r, table, CRANE_GATE)
        along = gate - 11.0
        assert r.snap(*_ll(line.interpolate(along)), heading=_toward_v(line, along))[0] == u

    def test_a_point_between_two_barriers_takes_the_side_beyond_the_nearer(
            self, closed_router, table):
        """The decision for a point no end of its own edge is reachable from:
        the nearest part of a road a car can use, which on Turner Road is the
        stretch beyond the nearer of its two barriers."""
        r = closed_router
        rows = table[table["osm_id"].isin(TURNER_BARRIERS)]
        e = int(rows["edge"].iat[0])
        line, (first, last) = r._edge_geom_m[e], sorted(rows["at_m"])
        u, v = int(r.edge_u_idx[e]), int(r.edge_v_idx[e])
        assert r.snap(*_ll(line.interpolate(first + 4.0)))[0] == u
        assert r.snap(*_ll(line.interpolate(last - 4.0)))[0] == v

    def test_a_point_on_a_road_closed_to_cars_starts_on_the_nearest_open_one(
            self, closed_router, table):
        r = closed_router
        e = int(table.loc[table["osm_id"] == BLUNT_PARK_WAY, "edge"].iat[0])
        mid = r._edge_geom_m[e].interpolate(0.5, normalized=True)
        chosen = r._nearest_open(mid, e)
        nearby = [int(c) for c in r._edge_tree.query(mid.buffer(3000.0))]
        assert not r._snap_closed[chosen]
        assert r._open_distance(chosen, mid) == min(r._open_distance(c, mid) for c in nearby)
        s, _ = r.snap(*_ll(mid))
        assert s in (int(r.edge_u_idx[chosen]), int(r.edge_v_idx[chosen]))
        assert r.route(s, r.snap(*BOSTON)[0], 0.0) is not None


class TestABarrierBetweenTwoRoads:
    """Trap 1, degree 2: the movement through the junction is closed, and
    neither road is."""

    def _sides(self, r):
        e1, e2 = r.closed_to_cars.through[EAGLE_GATE]
        b = r.idx[EAGLE_GATE]
        far = [int(r.edge_v_idx[e]) if int(r.edge_u_idx[e]) == b else int(r.edge_u_idx[e])
               for e in (e1, e2)]
        return b, (e1, e2), far

    def test_nobody_drives_through_and_both_roads_stay_open(self, closed_router, monkeypatch):
        r = closed_router
        b, (e1, e2), far = self._sides(r)
        assert not set(r.closed_to_cars.edges) & {e1, e2}
        route = r.route(far[0], far[1], 0.0)
        assert route is not None and b not in route.nodes, "the route drove through the gate"
        boston, _ = r.snap(*BOSTON)
        for e in (e1, e2):
            assert r.route(boston, r.through_copy[(e, b)], 0.0) is not None, \
                "a road is no longer open up to the gate"
        monkeypatch.setattr(r, "_car_closed_slots",
                            np.setdiff1d(r._car_closed_slots, r._through_slots))
        assert b in r.route(far[0], far[1], 0.0).nodes

    def test_a_point_beside_it_starts_on_its_own_side(self, closed_router, table):
        r = closed_router
        b, (e1, e2), far = self._sides(r)
        line = r._edge_geom_m[e1]
        beside = line.interpolate(line.length - 5.0 if int(r.edge_v_idx[e1]) == b else 5.0)
        s, _ = r.snap(*_ll(beside))
        assert s == r.through_copy[(e1, b)]
        route = r.route(s, far[1], 0.0)
        assert route is not None
        assert route.edges.index[0] == e1, "the drive left by the far side of the gate"


class TestBehindAGate:
    """Trap 2's destination rule, and the same for a start: nothing past the
    gate is reachable, so the drive ends, or starts, at its near side."""

    @pytest.mark.parametrize("where,gate", [(WATATIC, WATATIC_GATE), (HALSTED, HALSTED_GATE)],
                             ids=["locked gate inside an edge", "gate between two edges"])
    def test_a_destination_past_a_gate_ends_at_it(self, closed_router, table, monkeypatch,
                                                  where, gate):
        r = closed_router
        s, _ = r.snap(*BOSTON)
        t, _ = r.snap_destination(*where)
        route = r.route(s, t, 0.0)
        assert route is not None, "no route to a destination past a gate"
        point = _barrier_m(r, table, gate)
        assert not _crosses(_line_m(route), point)
        assert shapely.Point(_line_m(route).coords[-1]).distance(point) < 1000.0
        monkeypatch.setattr(r, "_way_in", {})
        assert r.route(s, r.snap_destination(*where)[0], 0.0) is None

    def test_a_destination_past_a_gate_between_two_edges_ends_at_the_gate(self, closed_router):
        r = closed_router
        t, _ = r.snap_destination(*HALSTED)
        assert r.real_node[t] == r.idx[HALSTED_GATE]

    def test_a_start_past_a_locked_gate_leaves_by_it(self, closed_router, monkeypatch):
        r = closed_router
        boston, _ = r.snap(*BOSTON)
        s, _ = r.snap(*WATATIC)
        assert r.route(s, boston, 0.0) is not None
        monkeypatch.setattr(r, "_way_out", {})
        assert r.route(r.snap(*WATATIC)[0], boston, 0.0) is None


class TestEveryCaller:
    """Decision 6: closed for every caller, with or without a date."""

    def test_the_weights_need_no_date(self, closed_router):
        r = closed_router
        w = r._weights(0.5, r._edge_scores({}))
        assert np.isinf(w[r._car_closed_slots]).all()
        assert np.isfinite(np.delete(w, r._car_closed_slots)).all()

    def test_the_loop_planner_prices_them_too(self, closed_router):
        from looper import LoopPlanner
        cost = LoopPlanner(closed_router)._cost(1.0, (), 1.0, None)
        assert np.isinf(cost.w_slot[closed_router._car_closed_slots]).all()

    def test_the_creeper_hill_loop_no_longer_passes_the_private_gate(
            self, closed_router, table, monkeypatch):
        """Case 4: a 40 km loop at the server's defaults went through the
        private gate on Creeper Hill Road. It is loop059 of the 2026-10-05
        before-and-after sample, and now comes back 2.9 km longer."""
        from looper import LoopPlanner
        r = closed_router
        start, _ = r.snap(*CREEPER_HILL_START)
        gate = _barrier_m(r, table, CREEPER_HILL_GATE)
        loop = LoopPlanner(r).plan(start, 40.0, 1.0, {})
        assert loop is not None
        assert not _crosses(_line_m(loop.route), gate)
        monkeypatch.setattr(r, "_car_closed_slots", None)
        assert _crosses(_line_m(LoopPlanner(r).plan(start, 40.0, 1.0, {}).route), gate)


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
    assert server_app.ROUTER.closed_to_cars is not None
    return server_app


class TestThroughTheServer:
    def _post(self, server, monkeypatch, form):
        from datetime import date
        # July, so no seasonal closure is in force whenever the suite runs.
        monkeypatch.setattr(server, "_today", lambda: date(2027, 7, 15))
        return server.app.test_client().post("/api/route", data=form)

    def test_crane_road_through_the_api(self, server, table, monkeypatch):
        form = {"from": "42.1396268,-71.2613399", "to": "42.1311784,-72.7617144",
                "pref": "0.50", "w_town": "0"}
        resp = self._post(server, monkeypatch, form)
        assert resp.status_code == 200
        gate = _barrier_m(server.ROUTER, table, CRANE_GATE)
        for arm in ("fastest", "scenic"):
            feature = resp.get_json()[arm]
            steps = [s["instruction"] for s in feature["properties"]["steps"]]
            assert not any("Crane Road" in s for s in steps), steps
            assert not _crosses(_feature_m(feature), gate)

    @pytest.mark.parametrize("pref", ["0", "0.50"])
    def test_the_reroute_57_m_short_of_the_gate_through_the_api(
            self, server, table, monkeypatch, pref):
        r = server.ROUTER
        e, line, gate, u, v = _gate_edge(r, table, CRANE_GATE)
        along = gate + 57.0
        lat, lon = _ll(line.interpolate(along))
        form = {"from": f"{lat:.7f},{lon:.7f}", "to": "42.1311784,-72.7617144",
                "heading": f"{_toward_v(line, along):.1f}", "pref": pref, "w_town": "0"}
        resp = self._post(server, monkeypatch, form)
        assert resp.status_code == 200
        for arm in ("fastest", "scenic"):
            assert not _crosses(_feature_m(resp.get_json()[arm]), line.interpolate(gate))


def test_the_deploy_script_ships_the_table_and_reports_it():
    """Trap 6: the box would otherwise start, answer, and drive through every
    locked gate, with nothing in any log."""
    script = (ROOT / "server" / "deploy-oracle.sh").read_text()
    optional = next(line for line in script.splitlines()
                    if line.startswith("OPTIONAL="))
    assert "closed_to_cars" in optional.split("=", 1)[1].strip('"').split()
    assert "'closed to cars'" in script
