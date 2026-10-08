"""State road classes: NH Class VI, VT trails and discontinued roads are closed
to cars, private roads are only ever the start or the end of a route, and VT
Class 4 counts as dirt (docs/state-road-class.md).

The rules, the name check, the edge labelling and the router's handling all run
on synthetic data anywhere. The last section needs the built graph and
`state_road_class.parquet` (pipeline/state_roads.py), and skips without them.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
import shapely
from pyproj import Transformer

import state_roads
from common import CRS_METERS, barrier_closes, logging_checkpoint
from conftest import DATA, ROOT, ROUTER_DATA
from router import PRIVATE_ENTRY_MIN, ClosedToCars, Router, StateRoadClass
from state_roads import SOURCES, apply_overrides, label, same_name

_TO_M = Transformer.from_crs(4326, CRS_METERS, always_xy=True)
_TO_LL = Transformer.from_crs(CRS_METERS, 4326, always_xy=True)
# A point in southwest New Hampshire: every synthetic place below is metres east
# and north of here.
X0, Y0 = _TO_M.transform(-72.35, 43.07)


def _ll(x, y):
    return _TO_LL.transform(X0 + x, Y0 + y)


def _line_ll(*points):
    return shapely.LineString([_ll(x, y) for x, y in points])


def _classify(state, **attrs):
    found = [layer.classify(attrs) for layer in SOURCES[state]]
    return found[0]


# ------------------------------------------------------------------- the rules

class TestTheRules:
    """The decisions, one class at a time (docs/state-road-class.md)."""

    @pytest.mark.parametrize("state, attrs, rule", [
        ("NH", {"LEGIS_CLASS": "VI"}, "closed"),
        ("NH", {"LEGIS_CLASS": "0"}, "private"),
        ("NH", {"LEGIS_CLASS": "V"}, None),
        # Federal roads and Class V dirt were not decided, so are left alone.
        ("NH", {"LEGIS_CLASS": "VII"}, None),
        ("NH", {"LEGIS_CLASS": "V", "SURF_TYPE": "Unpaved"}, None),
        ("VT", {"AOTCLASS": 4, "SURFACETYPE": 6}, "closed"),
        ("VT", {"AOTCLASS": 4, "SURFACETYPE": 2}, "unpaved"),
        ("VT", {"AOTCLASS": 7}, "closed"),
        ("VT", {"AOTCLASS": 70}, "closed"),
        ("VT", {"AOTCLASS": 71}, "closed"),
        ("VT", {"AOTCLASS": 96}, "closed"),
        ("VT", {"AOTCLASS": 97}, "closed"),
        ("VT", {"AOTCLASS": 8}, "private"),
        ("VT", {"AOTCLASS": 9}, "private"),
        ("VT", {"AOTCLASS": 89}, "private"),
        ("VT", {"AOTCLASS": 3, "SURFACETYPE": 2}, None),
        ("MA", {"JURISDICTN": "H"}, "private"),
        ("MA", {"JURISDICTN": "2", "FACILITY": 14}, "private"),
        ("MA", {"JURISDICTN": "2", "SURFACE_TP": 1}, "unpaved"),
        ("MA", {"JURISDICTN": "2", "SURFACE_TP": 2}, "unpaved"),
        ("MA", {"JURISDICTN": "2", "SURFACE_TP": 6}, None),
    ])
    def test_each_class(self, state, attrs, rule):
        found = _classify(state, **attrs)
        assert (found[0] if found else None) == rule

    def test_unaccepted_massachusetts_streets_are_not_private(self):
        """JURISDICTN '0' is 15.7% of the MA graph and mostly ordinary
        subdivision streets: not a private proxy."""
        assert _classify("MA", JURISDICTN="0", SURFACE_TP=6) is None

    def test_every_maine_private_road_class_is_private_and_limited_to_the_north(self):
        private, public = SOURCES["ME"]
        for cls in ("Private", "Local", "Gated", "Vehicular Trail", "Paper Street"):
            assert private.classify({"RDCLASS": cls})[0] == "private"
        assert private.min_lat == 45.0
        assert public.classify({}) is None and public.min_lat is None


class TestTheNames:
    @pytest.mark.parametrize("osm, state", [
        ("Brook Road", "BROOK RD"), ("Brook Road", "Brook Rd"),
        ("North Main Street", "N MAIN ST"), ("NH 12A", "NH ROUTE 12A"),
        ("Mount Washington Auto Road", "MT WASHINGTON AUTO RD"),
        ("Realty Road", "American Realty Rd"), ("Saint Aurelie Road", "Ste Aurelie Rd"),
        ("South Road Extension", "SOUTH ROAD EXTENSION"), ("Interstate Drive", "Interstate Dr"),
    ])
    def test_spelled_alike(self, osm, state):
        assert same_name([osm], [state])

    @pytest.mark.parametrize("osm, state", [
        ("Vermont Route 12", "Vermont"), ("", "MA Turn Around"),
        ("South River Road", "Ramp"), ("Plaistow Road", "Cushing Ave Mass."),
        ("Daniel Webster Highway", "TURN LANE B755"), ("Gateway Boulevard", "No Name"),
        ("Neponset Valley Parkway", "WESTINGHOUSE PLAZA"),
        ("Grant Street", "NORTH STREET"), ("No Name", "No Name"),
        ("I 93", "Hooksett Rest Area Interstate 93 N"),
    ])
    def test_not_the_same_road(self, osm, state):
        """Pairs the state private lines actually made on major, secondary and
        tertiary roads."""
        assert not same_name([osm], [state])


# ------------------------------------------------------------- the labelling

def _lines(*spec):
    """read_lines' frame from (rule, cls, names, points[, min_lat]) tuples, in
    metres around the origin."""
    rows, geoms = [], []
    for i, s in enumerate(spec):
        rule, cls, names, points = s[:4]
        rows.append({"state": "NH", "layer": "test", "rule": rule, "cls": cls,
                     "tag": cls, "names": tuple(names), "objectid": i,
                     "min_lat": s[4] if len(s) > 4 else np.nan})
        geoms.append(shapely.LineString([(X0 + x, Y0 + y) for x, y in points]))
    return gpd.GeoDataFrame(rows, geometry=geoms, crs=CRS_METERS)


def _graph(*spec):
    """graph_edges-like rows from (highway, name, points) tuples."""
    rows = [{"u": 2 * i, "v": 2 * i + 1, "length_m": shapely.LineString(p).length,
             "name": name, "ref": "", "highway": hw, "score": 5.0}
            for i, (hw, name, p) in enumerate(spec)]
    return gpd.GeoDataFrame(rows, geometry=[_line_ll(*p) for _, _, p in spec],
                            crs=4326)


class TestTheLabelling:
    def test_a_motorway_beside_a_private_drive_is_not_labelled(self):
        """Trap 1. The drive runs 8 m off the motorway for its whole length; the
        motorway's own public line is nearer, so it keeps every sample."""
        edges = _graph(("motorway", "", [(0, 0), (1000, 0)]))
        lines = _lines((None, "NH I", ["I-93"], [(0, 2), (1000, 2)]),
                       ("private", "NH 0", ["Frontage Dr"], [(0, 8), (1000, 8)]))
        assert label(edges, lines).table.empty

    def test_a_major_road_needs_the_names_to_agree(self):
        """With no public line to win the samples, only the names stand
        between a stub the state calls private and I-95."""
        edges = _graph(("motorway", "", [(0, 0), (1000, 0)]),
                       ("primary", "South River Road", [(0, 500), (1000, 500)]))
        lines = _lines(("private", "NH 0", ["MA Turn Around"], [(0, 3), (1000, 3)]),
                       ("private", "NH 0", ["South River Rd"], [(0, 503), (1000, 503)]))
        found = label(edges, lines)
        assert found.table["edge"].tolist() == [1]
        assert found.refused["edge"].tolist() == [0]

    def test_a_run_of_samples_never_labels_a_motorway(self):
        """Edge 800720, I-93 at the Hooksett rest area: 76 m of a private
        ramp line, named with the interstate's number, on a 1 km edge that
        meets public roads at both ends. Neither run rule applies to a major
        road, and its names must agree exactly."""
        edges = _graph(("motorway", "Everett Turnpike", [(-500, 0), (0, 0)]),
                       ("motorway", "Everett Turnpike", [(0, 0), (1000, 0)]),
                       ("motorway", "Everett Turnpike", [(1000, 0), (1500, 0)]))
        edges["ref"] = "I 93"
        edges.loc[1, "u"], edges.loc[1, "v"] = 1, 4
        lines = _lines((None, "NH I", ["I-93"], [(-500, 1), (450, 1)]),
                       ("private", "NH 0", ["Hooksett Rest Area Interstate 93 N"],
                        [(450, 1), (650, 1)]),
                       (None, "NH I", ["I-93"], [(650, 1), (1500, 1)]))
        found = label(edges, lines)
        assert found.table.empty and found.refused.empty

    def test_a_major_road_needs_its_names_to_agree_exactly(self):
        """Elsewhere "Realty Road" may be "American Realty Rd"; on a major
        road a state line's extra words mean another road."""
        assert same_name(["Everett Turnpike"], ["Everett Turnpike Rest Area"])
        assert not same_name(["Everett Turnpike"], ["Everett Turnpike Rest Area"],
                             exact=True)
        edges = _graph(("motorway", "Everett Turnpike", [(0, 0), (1000, 0)]))
        lines = _lines(("private", "NH 0", ["Everett Turnpike Rest Area"],
                        [(0, 3), (1000, 3)]))
        found = label(edges, lines)
        assert found.table.empty and found.refused["edge"].tolist() == [0]

    def test_a_road_crossing_is_not_a_road_running_along(self):
        """A private drive meeting the road at right angles is within 12 m of
        it near the junction, and runs the wrong way there."""
        edges = _graph(("residential", "Valley Road", [(0, 0), (60, 0)]))
        lines = _lines(("private", "NH 0", ["Drive"], [(30, -200), (30, 200)]))
        assert label(edges, lines).table.empty

    def test_a_closed_stretch_closes_its_edge_and_says_where(self):
        """The case that started this: a Class VI section 481 m long in a 912 m
        OSM edge, under half, still closes it; the rest of the edge is open,
        so the span is recorded for `Router.snap`."""
        edges = _graph(("residential", "Brook Road", [(0, 0), (900, 0)]))
        lines = _lines((None, "NH V", ["Brook Rd"], [(0, 1), (420, 1)]),
                       ("closed", "NH VI", ["Hill Rd"], [(420, 1), (900, 1)]))
        row = label(edges, lines).table.iloc[0]
        assert row["rule"] == "closed" and row["coverage"] < 0.6
        assert 400 <= row["from_m"] <= 440 and row["to_m"] == pytest.approx(900, abs=1)

    def test_a_short_private_stretch_in_a_long_edge_labels_nothing(self):
        """Under MIN_RUN_M and under half the edge: reported, not labelled."""
        edges = _graph(("residential", "Long Road", [(0, 0), (1000, 0)]))
        lines = _lines((None, "NH V", ["Long Rd"], [(0, 1), (450, 1)]),
                       ("private", "NH 0", ["Long Rd"], [(450, 1), (500, 1)]),
                       (None, "NH V", ["Long Rd"], [(500, 1), (1000, 1)]))
        found = label(edges, lines)
        assert found.table.empty
        assert found.short["rule"].tolist() == ["private"]
        assert (found.short[["before", "after"]].to_numpy() == 0).all()

    def test_a_short_private_stretch_on_a_connector_labels_it(self):
        """The same 50 m stretch on an edge that meets a public road at both
        ends is a shortcut between them, and is labelled (the master
        session's review, docs/state-road-class.md, "Short runs")."""
        edges = _graph(("residential", "West Road", [(-500, 0), (0, 0)]),
                       ("residential", "Long Road", [(0, 0), (1000, 0)]),
                       ("residential", "East Road", [(1000, 0), (1500, 0)]))
        edges.loc[1, "u"], edges.loc[1, "v"] = 1, 4      # meets both neighbours
        lines = _lines((None, "NH V", ["Long Rd"], [(0, 1), (450, 1)]),
                       ("private", "NH 0", ["Long Rd"], [(450, 1), (500, 1)]),
                       (None, "NH V", ["Long Rd"], [(500, 1), (1000, 1)]))
        assert label(edges, lines).table["edge"].tolist() == [1]

    def test_one_sample_on_a_connector_is_not_enough(self):
        edges = _graph(("residential", "West Road", [(-500, 0), (0, 0)]),
                       ("residential", "Long Road", [(0, 0), (1000, 0)]),
                       ("residential", "East Road", [(1000, 0), (1500, 0)]))
        edges.loc[1, "u"], edges.loc[1, "v"] = 1, 4
        lines = _lines((None, "NH V", ["Long Rd"], [(0, 1), (480, 1)]),
                       ("private", "NH 0", ["Long Rd"], [(480, 1), (505, 1)]),
                       (None, "NH V", ["Long Rd"], [(505, 1), (1000, 1)]))
        assert label(edges, lines).table.empty

    def test_a_short_private_edge_is_labelled_by_its_share(self):
        """A 90 m private connector that is its own edge is wholly private."""
        edges = _graph(("residential", "", [(0, 0), (90, 0)]))
        lines = _lines(("private", "NH 0", ["Cut Through"], [(-50, 1), (140, 1)]))
        assert label(edges, lines).table["rule"].tolist() == ["private"]

    def test_a_layer_limited_to_the_north_labels_nothing_south_of_it(self):
        """Maine's private layer applies north of 45 N only; the origin is at
        43.07 N. South of the line its samples still belong to it, as public."""
        edges = _graph(("residential", "", [(0, 0), (500, 0)]))
        north = _lines(("private", "ME Private", [""], [(0, 1), (500, 1)], 43.0))
        south = _lines(("private", "ME Private", [""], [(0, 1), (500, 1)], 45.0))
        assert label(edges, north).table["rule"].tolist() == ["private"]
        assert label(edges, south).table.empty


# ------------------------------------------------------------- the overrides

def _override_case(spec, roads=()):
    """(table, edges, roads) for apply_overrides, from (state, rule, cls,
    name, lon, lat) rows, each a 100 m east-west edge centred there, and
    (surface, lon, lat) OSM ways lying on them."""
    rows, geoms = [], []
    for i, (state, rule, cls, name, lon, lat) in enumerate(spec):
        rows.append({**_state_row(i, 2 * i, 2 * i + 1, rule), "state": state,
                     "cls": cls, "name": name})
        geoms.append(shapely.LineString([(lon - 0.0006, lat), (lon + 0.0006, lat)]))
    edges = gpd.GeoDataFrame({"name": [r["name"] for r in rows]}, geometry=geoms,
                             crs=4326)
    ways = gpd.GeoDataFrame({"surface": [r[0] for r in roads]},
                            geometry=[shapely.LineString([(lon - 0.001, lat),
                                                          (lon + 0.001, lat)])
                                      for _, lon, lat in roads], crs=4326)
    return pd.DataFrame(rows), edges, ways


class TestTheOverrides:
    def test_the_auto_road_is_open_to_all(self):
        """NHDOT codes the Mount Washington Auto Road private; it is a toll
        road anyone may drive in season."""
        table, edges, roads = _override_case([
            ("NH", "private", "NH 0", "Mount Washington Auto Road", -71.25, 44.27),
            ("NH", "private", "NH 0", "Mount Washington Auto Road", -71.50, 43.20),
            ("VT", "private", "VT 8 private", "Skyline Drive", -73.12, 43.15),
            ("VT", "private", "VT 8 private", "Skyline Drive", -72.60, 44.40)])
        kept, over = apply_overrides(table, edges, roads)
        assert over["edge"].tolist() == [0, 2]
        assert kept["edge"].tolist() == [1, 3]       # same names, other places

    def test_a_sealed_osm_surface_beats_a_state_surface_code(self):
        """Rockwell Road: MassDOT gravel, OSM asphalt. VT Class 4 is a legal
        class and keeps its label whatever OSM says."""
        table, edges, roads = _override_case(
            [("MA", "unpaved", "MA gravel", "Rockwell Road", -73.18, 42.63),
             ("MA", "unpaved", "MA gravel", "Gravel Road", -73.10, 42.63),
             ("VT", "unpaved", "VT 4", "Class Four Road", -72.80, 44.10)],
            roads=[("asphalt", -73.18, 42.63), ("gravel", -73.10, 42.63),
                   ("asphalt", -72.80, 44.10)])
        kept, over = apply_overrides(table, edges, roads)
        assert over["edge"].tolist() == [0]
        assert over["why"].tolist() == ["OSM surface is sealed"]
        assert kept["edge"].tolist() == [1, 2]


# ---------------------------------------------------------------- the loader

def _state_row(edge, u, v, rule, from_m=np.nan, to_m=np.nan, length_m=100.0):
    return {"edge": edge, "u": u, "v": v, "state": "NH", "rule": rule,
            "cls": "NH VI", "tag": "LEGIS_CLASS=VI", "name": "", "state_name": "",
            "highway": "residential", "coverage": 1.0, "run_m": length_m,
            "from_m": from_m, "to_m": to_m, "length_m": length_m}


class TestTheTableIsRefusedWhenStale:
    def test_rows_that_name_other_edges_are_refused(self):
        table = pd.DataFrame([_state_row(0, 10, 11, "closed"),
                              _state_row(1, 11, 99, "private")])
        with pytest.raises(RuntimeError, match="state_roads.py"):
            StateRoadClass(table, np.array([10, 11]), np.array([11, 12]))

    def test_an_unknown_rule_is_refused(self):
        table = pd.DataFrame([_state_row(0, 10, 11, "toll")])
        with pytest.raises(RuntimeError, match="rules"):
            StateRoadClass(table, np.array([10]), np.array([11]))

    def test_closed_rows_are_whole_or_two_barriers(self):
        table = pd.DataFrame([_state_row(0, 10, 11, "closed", 0.0, 100.0),
                              _state_row(1, 11, 12, "closed", 40.0, 100.0)])
        s = StateRoadClass(table, np.array([10, 11]), np.array([11, 12]))
        c = ClosedToCars(s.closed_rows(), np.array([10, 11]), np.array([11, 12]))
        assert c.edges.tolist() == [0, 1]
        assert c.whole.tolist() == [0]
        assert c.at[1].tolist() == [40.0, 100.0]
        assert (c.n_ways, c.n_barriers, c.n_state) == (0, 0, 2)


# ------------------------------------------------- the router, on a toy graph
#
#   N12 (-2000,1000) ---------- Back Drive (private, 3 km) ---------- N7
#    |                                                                 | Long Drive
#  Far Road                                       Camp Road (public)  N11
#    |                                            between private     | Camp Road
#    |                                                                N10
#    |                                                                 | Long Drive
#   N4 (0,300) ---- North Road ---- N3 (1000,300) -- Long Drive ----- N6
#    |                               | Private Lane, 300 m
#  West Road, 12 km                  |
#   N1 (0,0) ------ South Road ---- N2 (1000,0) -- East Road -- N8 (2000,0)
#                                                                |
#                                    N9 (2000,300) - Class VI ---+  (closed)
#                                    N9 -- Back Road -- N3
#
# Through Private Lane, N1 to N4 is 2.3 km; round by West Road it is 12 km,
# which costs more than the per-km charge alone, so only PRIVATE_ENTRY_MIN
# keeps a route off the lane. Camp Road is a public pocket inside the private
# Long Drive, reachable only through it, as the North Maine Woods are full of.

NODES = {1: (0, 0), 2: (1000, 0), 3: (1000, 300), 4: (0, 300), 5: (-6000, 150),
         6: (1000, 800), 7: (1000, 1000), 8: (2000, 0), 9: (2000, 300),
         10: (1000, 900), 11: (1000, 950), 12: (-2000, 1000)}
EDGES = [  # u, v, name, highway, rule
    (1, 2, "South Road", "tertiary", None),
    (2, 3, "Private Lane", "residential", "private"),
    (3, 4, "North Road", "tertiary", None),
    (1, 5, "West Road", "tertiary", None),
    (5, 4, "West Road", "tertiary", None),
    (3, 6, "Long Drive", "residential", "private"),
    (6, 10, "Long Drive", "residential", "private"),
    (2, 8, "East Road", "tertiary", None),
    (8, 9, "Class Six Road", "residential", "closed"),
    (9, 3, "Back Road", "residential", "unpaved"),
    (10, 11, "Camp Road", "residential", None),
    (11, 7, "Long Drive", "residential", "private"),
    (4, 12, "Far Road", "tertiary", None),
    (12, 7, "Back Drive", "residential", "private"),
]
PRIVATE_LANE, LONG_DRIVE, CLASS_SIX, BACK_ROAD = 1, 5, 8, 9


def _toy(d, rules=True):
    """A Router's three parquets for the toy graph, plus the side table when
    `rules`, written to `d`."""
    d.mkdir(parents=True, exist_ok=True)
    nodes = pd.DataFrame([{"node_id": n, "lon": _ll(*p)[0], "lat": _ll(*p)[1],
                           "exit_ref": ""} for n, p in NODES.items()])
    nodes.to_parquet(d / "graph_nodes.parquet")
    rows = []
    for u, v, name, hw, _ in EDGES:
        length = float(np.hypot(*np.subtract(NODES[v], NODES[u])))
        rows.append({"u": u, "v": v, "length_m": length,
                     "minutes": length / 1000.0 / 50.0 * 60.0, "oneway": "no",
                     "name": name, "ref": "", "highway": hw, "junction": "",
                     "dest_ref": "", "dest_name": "",
                     **{f"n_{k}_{s}": 0 for k in ("signal", "stop", "giveway")
                        for s in ("fwd", "rev")},
                     **{c: 0.0 for c in ("c_curves", "c_water", "c_coast", "c_forest",
                                         "c_farm", "c_views", "c_scenic_tag",
                                         "c_relief", "c_urban")},
                     "unpaved_frac": 0.0, "score_adj": 0.0, "score": 5.0})
    geoms = [_line_ll(NODES[u], NODES[v]) for u, v, *_ in EDGES]
    gpd.GeoDataFrame(rows, geometry=geoms, crs=4326).to_parquet(d / "graph_edges.parquet")
    pd.DataFrame({"via_node": pd.Series([], dtype="int64"), "from_edge": pd.Series([], dtype="int64"),
                  "to_edge": pd.Series([], dtype="int64"), "kind": pd.Series([], dtype="object")}
                 ).to_parquet(d / "turn_restrictions.parquet")
    if rules:
        table = pd.DataFrame([_state_row(i, u, v, rule, 0.0, 1e9, 100.0)
                              for i, (u, v, _, _, rule) in enumerate(EDGES) if rule])
        table.to_parquet(d / "state_road_class.parquet")
    return d


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return Router(str(_toy(tmp_path_factory.mktemp("toy"))))


@pytest.fixture(scope="module")
def bare(tmp_path_factory):
    return Router(str(_toy(tmp_path_factory.mktemp("bare"), rules=False)))


def _names(route):
    return route.edges["name"].tolist()


def _route(r, a, b, pref=0.0):
    return r.route(r.idx[a], r.idx[b], pref)


class TestTheToyGraph:
    @pytest.mark.parametrize("pref", [0.0, 0.5, 1.0])
    def test_a_route_that_could_go_round_never_passes_through(self, toy, bare, pref):
        assert "Private Lane" in _names(_route(bare, 1, 4, pref))
        route = _route(toy, 1, 4, pref)
        assert "Private Lane" not in _names(route)
        assert "West Road" in _names(route)

    def test_a_trip_ending_on_a_private_road_still_routes(self, toy):
        """And comes in the public way, not through Private Lane."""
        names = _names(_route(toy, 1, 7))
        assert names[-1] == "Long Drive"
        assert "Private Lane" not in names

    def test_a_public_pocket_inside_private_land_is_not_a_second_entry(self, toy):
        """Camp Road is public but reached only through Long Drive, so driving
        on past it to N7 is still the one entry, and the route does not go
        3.4 km further round by Far Road and Back Drive to save a second."""
        names = _names(_route(toy, 1, 7))
        assert names[-4:] == ["Long Drive", "Long Drive", "Camp Road", "Long Drive"]
        assert "Far Road" not in names

    def test_a_trip_starting_on_a_private_road_drives_out_of_it(self, toy):
        names = _names(_route(toy, 7, 1))
        assert names[0] == "Long Drive"
        assert "Private Lane" not in names

    def test_a_trip_inside_the_private_road_routes(self, toy):
        assert _names(_route(toy, 7, 3)) == ["Long Drive", "Camp Road",
                                             "Long Drive", "Long Drive"]

    def test_the_eta_is_real_minutes(self, toy):
        """The penalty chooses the route and is never reported in it."""
        from router import SURFACE_SPEED_FACTOR
        route = _route(toy, 1, 7)
        assert route.minutes < 60.0
        assert route.minutes == pytest.approx(
            route.edges["minutes"].sum() / SURFACE_SPEED_FACTOR, rel=1e-9)

    def test_the_penalty_is_per_entry_not_per_edge(self, toy):
        """Long Drive is two edges; turning onto it costs PRIVATE_ENTRY_MIN
        once, and its second edge per km alone."""
        w = toy._weights(0.0, toy._edge_scores({}), 0.0)
        extra = w - toy.d_minutes
        entering = extra[(toy.eidx == LONG_DRIVE)
                         & (toy.real_node[toy.tail] == toy.idx[3])]
        onward = extra[(toy.eidx == LONG_DRIVE + 1)
                       & (toy.real_node[toy.tail] == toy.idx[6])]
        assert entering.min() >= PRIVATE_ENTRY_MIN
        assert onward.max() < 10.0

    def test_a_closed_road_is_never_routed(self, toy, bare):
        assert "Class Six Road" in _names(_route(bare, 8, 9))
        assert "Class Six Road" not in _names(_route(toy, 8, 9))
        w = toy._weights(0.5, toy._edge_scores({}))
        assert np.isinf(w[toy.eidx == CLASS_SIX]).all()

    def test_vermont_class_4_counts_as_dirt(self, toy, bare):
        assert toy.unpaved_frac[BACK_ROAD] == 1.0
        assert bare.unpaved_frac[BACK_ROAD] == 0.0
        assert toy.unpaved_frac[PRIVATE_LANE] == 0.0

    def test_a_loop_never_turns_round_inside_a_private_road(self, toy):
        """Nor on the public pocket inside it."""
        inside = [toy.idx[n] for n in (6, 7, 10, 11)]
        assert toy.private_inside[inside].all()
        assert not toy.private_inside[[toy.idx[n] for n in (2, 3, 4, 12)]].any()

    def test_without_the_table_nothing_changes(self, bare):
        """An old graph without the side table prices exactly the travel time,
        scenery and dirt it always did, and nothing else."""
        from router import BETA, PREF_CURVE, UNPAVED_AVOID_MIN_PER_KM
        assert bare.state_roads is None and bare._private_slots is None
        assert bare.closed_to_cars is None
        scores = bare._edge_scores({})
        for pref, avoid in ((0.0, 0.0), (0.5, 1.0), (1.0, 2.0)):
            expected = (bare.d_minutes
                        + pref ** PREF_CURVE * BETA
                        * (bare.km * (1 - scores / 10.0))[bare.eidx]
                        + avoid * UNPAVED_AVOID_MIN_PER_KM
                        * (bare.km * bare.unpaved_frac)[bare.eidx])
            assert np.allclose(bare._weights(pref, scores, avoid), expected,
                               rtol=0, atol=1e-12)
        assert (bare.unpaved_frac == 0).all()


def test_the_router_says_when_it_has_no_table(tmp_path, capsys):
    """The box's journal is the only place a missing table would show."""
    Router(str(_toy(tmp_path, rules=False)))
    assert "state road classes: none" in capsys.readouterr().out


# --------------------------------------------------------------- checkpoints

class TestTheMaineCheckpoints:
    @pytest.mark.parametrize("tags", [
        {"barrier": "toll_booth", "name": "Telos Checkpoint",
         "operator": "North Maine Woods"},
        {"barrier": "toll_booth", "name": "Northeast Carry Electronic Gate"},
        {"barrier": "toll_booth", "name": "Kelly Dam Elecrtronic Gate",
         "operator": "North Maine Woods"},
        {"barrier": "toll_booth", "name": "Little Black Checkpoint",
         "operator": "North Maine woods"},
    ])
    def test_a_checkpoint_closes_the_road(self, tags):
        assert logging_checkpoint(tags)
        assert barrier_closes(tags) == "barrier=toll_booth, logging checkpoint"

    @pytest.mark.parametrize("tags", [
        {"barrier": "toll_booth", "name": "Hampton Toll Plaza"},
        {"barrier": "gate", "name": "Checkpoint"},
        {"amenity": "bar", "name": "Checkpoint Charlie's"},
    ])
    def test_nothing_else_does(self, tags):
        """An ordinary toll booth stays open, and a gate keeps the gate rules."""
        assert not logging_checkpoint(tags)
        assert barrier_closes(tags) is None


# ------------------------------------------------------------ the real graph

@pytest.fixture(scope="module")
def table():
    path = DATA / "state_road_class.parquet"
    if not path.exists():
        pytest.skip("state_road_class.parquet missing — run pipeline/state_roads.py")
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def state_router(router, table):
    assert router.state_roads is not None
    return router


# The case that started this (docs/state-road-class.md): the graph edge holding
# a Class VI section, and a trip that drove it until the table existed, between
# two points the suite already uses (Warren village in tests/test_closures.py,
# NEEDHAM_KERB in tests/test_routing.py) at the app's settings. Never a drive
# trace's own coordinates: the traces are private and this repository is not.
CLASS_VI_EDGE = 497893
CASE = {"from": (44.1123, -72.8565), "dest": (42.27725230013152, -71.2417737300463),
        "pref": 0.5, "weights": {"town": 0.0}}


class TestTheRealGraph:
    def test_no_named_class_is_labelled_without_a_name_match(self, state_router, table):
        """Trap 1, checked on the table that ships: no label on a tertiary
        road or above unless the names agree."""
        refs = state_router.edges["ref"].fillna("").to_numpy()
        named = table[table["highway"].isin(state_roads.NAMED)]
        assert len(named)
        for _, row in named.iterrows():
            osm = [row["name"], *refs[row["edge"]].split(";")]
            assert same_name(osm, row["state_name"].split("; ")), row

    def test_the_class_vi_section_is_closed(self, state_router, table):
        row = table[table["edge"] == CLASS_VI_EDGE]
        assert row["rule"].tolist() == ["closed"]
        assert CLASS_VI_EDGE in state_router.closed_to_cars.edges

    def test_the_case_no_longer_drives_the_class_vi_road(self, state_router, table):
        """Measured without the table, this trip drives edge 497893."""
        r = state_router
        src, _ = r.snap(*CASE["from"])
        dst, _ = r.snap_destination(*CASE["dest"])
        route = r.route(src, dst, CASE["pref"], CASE["weights"])
        rows = set(route.edges.index.tolist())
        assert CLASS_VI_EDGE not in rows
        banned = set(table.loc[table["rule"].isin(["closed", "private"]), "edge"])
        assert not rows & banned

    def test_the_deploy_script_ships_the_table_and_reports_it(self):
        script = (ROOT / "server" / "deploy-oracle.sh").read_text()
        optional = next(line for line in script.splitlines()
                        if line.startswith("OPTIONAL="))
        assert "state_road_class" in optional.split("=", 1)[1].strip('"').split()
        assert "'state road classes'" in script
