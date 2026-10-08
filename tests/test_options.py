"""Route options: the spliced in-between routes behind the slider's detents.

What docs/route-options.md promises, held against the built graph: the
owner's Waitsfield -> Needham trip gets its in-between routes, the menu only
ever buys scenery with time, the route shown first follows the owner's rule,
every option can be rebuilt anywhere from its switch points alone, closures
hold, and the server never computes options for a request that should not wait
for them.
"""

import sys
from datetime import date

import numpy as np
import pytest
import shapely

from conftest import DATA, ROOT, ROUTER_DATA

ON = date(2026, 10, 6)
GAP_OPEN = date(2026, 10, 10)
GAP_CLOSED = date(2026, 10, 20)

WAITSFIELD = (44.1901, -72.8244)
NEEDHAM = (42.2809, -71.2378)
WORCESTER = (42.2626, -71.8023)
BOSTON = (42.3551, -71.0657)
WARREN = (44.1123, -72.8565)
BRISTOL = (44.1334, -73.0790)


@pytest.fixture(scope="module")
def server():
    missing = [f for f in ROUTER_DATA if not (DATA / f).exists()]
    if missing:
        pytest.skip(f"built graph missing ({', '.join(missing)})")
    import os
    os.environ.setdefault("SUNDAYDRIVE_DATA", str(DATA))
    sys.path.insert(0, str(ROOT / "server"))
    import app as server_app
    server_app.app.config["TESTING"] = True
    return server_app


@pytest.fixture(scope="module")
def R(server):
    return server.ROUTER


@pytest.fixture(scope="module")
def O(server):
    return server.route_options


def _ends(R, a, b):
    s, _ = R.snap(*a)
    t, _ = R.snap_destination(*b)
    return s, t


def _point(sp):
    return None if sp is None else (sp["lat"], sp["lon"], sp["heading"])


@pytest.fixture(scope="module")
def waitsfield(R, O):
    s, t = _ends(R, WAITSFIELD, NEEDHAM)
    return s, t, O.plan(R, s, t, {}, 1.0, on=ON)


@pytest.fixture(scope="module")
def two_copies(R, O):
    """Trip 18 of the re-run (docs/route-options.md): its +24 and +32 min
    options leave the fast roads onto Enneking Parkway at a junction split
    for a turn restriction. The cheapest arrival at either copy looped back
    through the junction, so the rebuild drove it twice and came back 1.8 min
    shorter than the option priced."""
    s, t = _ends(R, (42.4042634, -71.0661628), (42.0245442, -71.1286594))
    return s, t, O.plan(R, s, t, {}, 1.0, on=ON)


@pytest.fixture(scope="module")
def worcester(R, O):
    s, t = _ends(R, WORCESTER, BOSTON)
    return s, t, O.plan(R, s, t, {}, 1.0, on=ON)


def _closed_rows(R, day):
    return set(R.closures.edges(R.closure_version(day)).tolist())


def _uses(route, rows):
    return bool(np.isin(route.edges.index.to_numpy(), list(rows)).any())


# ----------------------------------------------------------------- the menu

class TestTheMenu:
    def test_waitsfield_to_needham_has_the_routes_in_between(self, waitsfield):
        """The owner's trip: today's slider gives +16 or +112 and nothing
        between. Spliced, the +16 (VT-100, VT-107, I-89) and the +44 (VT-100
        to Killington, US-4 through Woodstock) are both on the menu."""
        _, _, plan = waitsfield
        extras = [o["extra_minutes"] for o in plan.menu]
        assert any(12 <= x <= 22 for x in extras), extras
        assert any(38 <= x <= 50 for x in extras), extras
        assert any(60 <= x <= 120 for x in extras), extras
        assert len(plan.menu) >= 8

    def test_it_opens_on_the_plus_44(self, waitsfield):
        _, _, plan = waitsfield
        assert 38 <= plan.menu[plan.default]["extra_minutes"] <= 50

    @pytest.mark.parametrize("trip", ["waitsfield", "worcester"])
    def test_every_option_buys_scenery_with_time(self, trip, request):
        """Strictly more minutes and strictly more beautiful road, option on
        option: an option that adds time without adding beautiful road must
        not survive (the rule `_no_worse_than_fastest` keeps for the old
        response)."""
        _, _, plan = request.getfixturevalue(trip)
        extras = [o["extra_minutes"] for o in plan.menu]
        gains = [o["beautiful_km"] for o in plan.menu]
        assert extras[0] == 0.0
        assert all(b > a for a, b in zip(extras, extras[1:])), extras
        assert all(b > a for a, b in zip(gains, gains[1:])), gains

    @pytest.mark.parametrize("trip", ["waitsfield", "worcester"])
    def test_the_route_shown_first_is_the_owners_rule(self, trip, request, O):
        """The most scenic option costing at most 25% of the fastest time."""
        _, _, plan = request.getfixturevalue(trip)
        budget = O.DEFAULT_MAX_EXTRA_SHARE * plan.fastest.minutes
        within = [i for i, o in enumerate(plan.menu) if o["extra_minutes"] <= budget]
        assert plan.default == max(within)
        assert plan.scenic.minutes == pytest.approx(
            plan.menu[plan.default]["minutes"], abs=0.06)

    def test_the_fastest_option_is_the_fastest_route(self, R, waitsfield):
        """Taken from the forward tree, not the A* arm; same cost either way."""
        s, t, plan = waitsfield
        assert plan.menu[0]["leave"] is None and plan.menu[0]["rejoin"] is None
        alone = R.route(s, t, 0.0, {}, on=ON)
        assert plan.fastest.minutes == pytest.approx(alone.minutes, abs=0.01)

    def test_a_drawn_line_is_simplified_and_stays_on_the_route(self, R, O, waitsfield):
        s, t, plan = waitsfield
        option = plan.menu[plan.default]
        full = shapely.get_coordinates(plan.scenic.line)
        assert len(option["line"]) < len(full) / 4
        # Every simplified vertex is a vertex of the full line.
        line = shapely.LineString(full)
        assert max(line.distance(shapely.Point(p)) for p in option["line"]) < 1e-4


# ----------------------------------------------------------- the switch points

class TestRebuildingAnOption:
    @pytest.mark.parametrize("trip", ["waitsfield", "worcester", "two_copies"])
    def test_every_option_rebuilds_from_its_switch_points(self, trip, request, R, O):
        """Trap 5 and 6: the follow-up request can land on the other box, so
        two lat/lon/headings must be enough to rebuild exactly the option
        that was priced. And none of them drives a junction twice."""
        s, t, plan = request.getfixturevalue(trip)
        for option in plan.menu[1:]:
            route = O.spliced_route(R, s, t, _point(option["leave"]),
                                    _point(option["rejoin"]), {}, 1.0, on=ON)
            assert route.minutes == pytest.approx(option["minutes"], abs=0.06)
            assert route.km == pytest.approx(option["km"], abs=0.06)
            assert route.beautiful_km == pytest.approx(option["beautiful_km"], abs=0.06)
            assert len(set(route.nodes)) == len(route.nodes)
            assert route.switch["leave"] == option["leave"]
            assert route.switch["rejoin"] == option["rejoin"]

    def test_a_switch_point_is_on_its_road_not_at_a_junction(self, R, O, waitsfield):
        _, _, plan = waitsfield
        for option in plan.menu[1:]:
            for sp in (option["leave"], option["rejoin"]):
                if sp is None:
                    continue
                slots = O.switch_slots(R, sp["lat"], sp["lon"], sp["heading"])
                assert len(set(R.eidx[slots].tolist())) == 1
                x, y = O._TO_M.transform(sp["lon"], sp["lat"])
                nodes = R.edge_u_idx[R.eidx[slots[0]]], R.edge_v_idx[R.eidx[slots[0]]]
                assert min(np.hypot(R._nx[n] - x, R._ny[n] - y) for n in nodes) > 1.0

    def test_the_wrong_heading_names_the_other_direction(self, R, O, waitsfield):
        _, _, plan = waitsfield
        sp = plan.menu[plan.default]["leave"]
        ahead = O.switch_slots(R, sp["lat"], sp["lon"], sp["heading"])
        back = O.switch_slots(R, sp["lat"], sp["lon"], (sp["heading"] + 180) % 360)
        assert not set(ahead.tolist()) & set(back.tolist())

    def test_a_point_off_every_road_is_refused(self, R, O):
        with pytest.raises(O.SwitchPointNotFound):
            O.switch_slots(R, 42.2550, -70.6500, 0.0)     # Massachusetts Bay


# ---------------------------------------------------------------- closures

class TestDirtRoads:
    def test_minutes_are_driving_time_not_tree_distance(self, R, O):
        """Trap 7: pref-0 weights carry the dirt-road avoidance, so a tree's
        distance overstates time on dirt. Pushed to its maximum, on Vermont
        roads, the priced minutes must still be the minutes the rebuilt
        route reports, which are `d_minutes`."""
        s, t = _ends(R, WAITSFIELD, (43.9250, -72.6650))      # Randolph VT
        plan = O.plan(R, s, t, {}, 2.0, on=ON)
        assert len(plan.menu) >= 3
        assert plan.menu[0]["minutes"] == pytest.approx(plan.fastest.minutes, abs=0.06)
        for option in plan.menu[1:]:
            route = O.spliced_route(R, s, t, _point(option["leave"]),
                                    _point(option["rejoin"]), {}, 2.0, on=ON)
            assert route.minutes == pytest.approx(option["minutes"], abs=0.06)


class TestClosures:
    def test_no_option_drives_lincoln_gap_once_it_closes(self, R, O):
        """Every weight comes from `Router._weights(..., on=day)`, so a
        closure is infinite in the trees, the base and every rebuilt leg."""
        if R.closures is None:
            pytest.skip("seasonal_closures.parquet missing")
        s, t = _ends(R, WARREN, BRISTOL)
        gap = _closed_rows(R, GAP_CLOSED)
        opened = O.plan(R, s, t, {}, 1.0, on=GAP_OPEN)
        assert _uses(opened.fastest, gap), "the open-gap fastest no longer uses it"
        closed = O.plan(R, s, t, {}, 1.0, on=GAP_CLOSED)
        assert not _uses(closed.fastest, gap) and not _uses(closed.scenic, gap)
        for option in closed.menu[1:]:
            route = O.spliced_route(R, s, t, _point(option["leave"]),
                                    _point(option["rejoin"]), {}, 1.0, on=GAP_CLOSED)
            assert not _uses(route, gap)


# ------------------------------------------------------------------ the server

def _ll(p):
    return f"{p[0]},{p[1]}"


def _sp(sp):
    return f"{sp['lat']},{sp['lon']},{sp['heading']}"


@pytest.fixture
def client(server, monkeypatch):
    monkeypatch.setattr(server, "_today", lambda: ON)
    monkeypatch.setattr(server, "ROUTE_OPTIONS", True)
    return server.app.test_client()


PLAN = {"from": _ll(WORCESTER), "to": _ll(BOSTON), "pref": "0.5"}


class TestThroughTheServer:
    def test_the_reply_is_todays_unless_options_are_asked_for(self, client):
        body = client.post("/api/route", data=PLAN).get_json()
        assert set(body) == {"fastest", "scenic"}
        assert "switch" not in body["scenic"]["properties"]

    def test_the_flag_is_off_by_default(self, server, monkeypatch):
        monkeypatch.setattr(server, "_today", lambda: ON)
        assert server.ROUTE_OPTIONS is False
        body = server.app.test_client().post(
            "/api/route", data={**PLAN, "options": "1"}).get_json()
        assert set(body) == {"fastest", "scenic"}

    def test_a_plan_with_options(self, client):
        body = client.post("/api/route", data={**PLAN, "options": "1"}).get_json()
        assert set(body) == {"fastest", "scenic", "options"}
        menu, default = body["options"]["menu"], body["options"]["default"]
        assert len(menu) >= 3 and 0 <= default < len(menu)
        for option in menu:
            assert {"extra_minutes", "minutes", "km", "beautiful_km", "leave",
                    "rejoin", "roads", "line"} <= set(option)
            assert all(len(p) == 2 for p in option["line"])
        chosen = menu[default]
        scenic = body["scenic"]["properties"]
        assert scenic["minutes"] == pytest.approx(chosen["minutes"], abs=0.06)
        assert scenic["switch"] == {"leave": chosen["leave"], "rejoin": chosen["rejoin"]}
        assert body["fastest"]["properties"]["minutes"] == menu[0]["minutes"]
        # The full-detail features keep every field an old client decodes.
        for arm in ("fastest", "scenic"):
            assert body[arm]["properties"]["steps"][-1]["instruction"] == \
                "Arrive at your destination"

    def test_no_options_while_anything_else_is_computing(self, server, client, monkeypatch):
        """Trap 3: skipped, and today's reply sent, when another plan or a
        loop is already running."""
        monkeypatch.setattr(server, "IN_FLIGHT", 1)
        body = client.post("/api/route", data={**PLAN, "options": "1"}).get_json()
        assert set(body) == {"fastest", "scenic"}
        assert server.IN_FLIGHT == 1

    def test_no_options_under_the_loop_lock(self, server, client):
        with server.LOOP_LOCK:
            body = client.post("/api/route", data={**PLAN, "options": "1"}).get_json()
        assert set(body) == {"fastest", "scenic"}

    def test_a_plan_gives_up_when_a_request_arrives(self, R, O):
        """Between phases, not after: the abort is checked as soon as the
        scenic base is found."""
        s, t = _ends(R, WORCESTER, BOSTON)
        assert O.plan(R, s, t, {}, 1.0, on=ON, abort=lambda: True) is None

    def test_no_options_for_a_reroute(self, client):
        """A heading or a declined U-turn means a driver is waiting."""
        for extra in ({"heading": "90"}, {"declined_uturn": "1", "heading": "90"}):
            body = client.post("/api/route", data={**PLAN, "options": "1",
                                                   **extra}).get_json()
            assert set(body) == {"fastest", "scenic"}

    def test_the_counter_comes_back_down(self, server, client):
        client.post("/api/route", data={**PLAN, "options": "1"})
        client.post("/api/route", data={"from": "nonsense"})
        assert server.IN_FLIGHT == 0

    def test_a_malformed_switch_point_is_a_bad_request(self, client):
        for bad in ("42.3,-71.1", "42.3,-71.1,400", "a,b,c"):
            assert client.post("/api/route",
                               data={**PLAN, "leave": bad}).status_code == 400


@pytest.fixture(scope="module")
def option(server):
    """A middle option of Worcester -> Boston with both switch points."""
    server_app = server
    old = server_app.ROUTE_OPTIONS
    server_app.ROUTE_OPTIONS = True
    today = server_app._today
    server_app._today = lambda: ON
    try:
        body = server_app.app.test_client().post(
            "/api/route", data={**PLAN, "options": "1"}).get_json()
    finally:
        server_app.ROUTE_OPTIONS = old
        server_app._today = today
    options = [o for o in body["options"]["menu"]
               if o["leave"] is not None and o["rejoin"] is not None]
    assert options, "no option with both switch points on Worcester -> Boston"
    return options[len(options) // 2]


class TestReroutingByLegs:
    """The app reroutes a spliced plan by legs (docs/route-options.md,
    "Rerouting"): both switch points before the leave point, the rejoin point
    alone on the scenic stretch, and plain fastest after it."""


    @staticmethod
    def _passes(feature, sp, within_m=5.0):
        from router import _TO_M
        lon, lat = np.asarray(feature["geometry"]["coordinates"]).T
        line = shapely.LineString(np.column_stack(_TO_M.transform(lon, lat)))
        return line.distance(shapely.Point(*_TO_M.transform(sp["lon"], sp["lat"]))) < within_m

    def test_fetching_an_option_in_full(self, client, option):
        body = client.post("/api/route", data={
            **PLAN, "pref": "1", "leave": _sp(option["leave"]),
            "rejoin": _sp(option["rejoin"])}).get_json()
        props = body["scenic"]["properties"]
        assert props["minutes"] == pytest.approx(option["minutes"], abs=0.06)
        assert props["switch"] == {"leave": option["leave"], "rejoin": option["rejoin"]}

    def test_before_the_leave_point(self, client, option):
        """A missed turn on the fast roads into the stretch: fastest back to
        the leave point, then the stretch, then home."""
        here = (WORCESTER[0] + 0.004, WORCESTER[1] + 0.004)
        body = client.post("/api/route", data={
            "from": _ll(here), "to": _ll(BOSTON), "pref": "1", "heading": "45",
            "leave": _sp(option["leave"]), "rejoin": _sp(option["rejoin"])}).get_json()
        scenic = body["scenic"]
        assert self._passes(scenic, option["leave"])
        assert self._passes(scenic, option["rejoin"])
        assert scenic["properties"]["switch"]["leave"] == option["leave"]

    def test_on_the_scenic_stretch(self, client, option):
        """Halfway along the stretch, asked with the rejoin point alone: the
        stretch to its end, then fastest; nothing sends the driver back to
        where it began."""
        from options import _FROM_M
        from router import _TO_M, _tangent_at
        full = client.post("/api/route", data={
            **PLAN, "pref": "1", "leave": _sp(option["leave"]),
            "rejoin": _sp(option["rejoin"])}).get_json()["scenic"]
        lon, lat = np.asarray(full["geometry"]["coordinates"]).T
        line = shapely.LineString(np.column_stack(_TO_M.transform(lon, lat)))
        at = [line.project(shapely.Point(*_TO_M.transform(sp["lon"], sp["lat"])))
              for sp in (option["leave"], option["rejoin"])]
        middle = line.interpolate(sum(at) / 2)
        here_lon, here_lat = _FROM_M.transform(middle.x, middle.y)
        body = client.post("/api/route", data={
            "from": f"{here_lat},{here_lon}", "to": _ll(BOSTON), "pref": "1",
            "heading": f"{_tangent_at(line, middle):.1f}",
            "rejoin": _sp(option["rejoin"])}).get_json()
        scenic = body["scenic"]
        assert self._passes(scenic, option["rejoin"])
        assert not self._passes(scenic, option["leave"], within_m=50.0)
        assert scenic["properties"]["switch"] == {"leave": None,
                                                  "rejoin": option["rejoin"]}
        assert not scenic["properties"]["turns_around"]

    def test_after_the_rejoin_point_is_plain_fastest(self, client, option):
        """Nothing new on the server: the app sends pref 0, the reply's
        `scenic` is the fastest route, exactly as for "switch to fastest"."""
        body = client.post("/api/route", data={**PLAN, "pref": "0"}).get_json()
        assert body["scenic"] == body["fastest"]

    def test_a_switch_point_on_no_road_falls_back_to_the_scenic_route(self, client):
        """A graph rebuilt under a plan: the driver gets a route, not an error."""
        body = client.post("/api/route", data={
            **PLAN, "pref": "1", "leave": "42.255,-70.65,0"})
        assert body.status_code == 200
        assert "switch" not in body.get_json()["scenic"]["properties"]
