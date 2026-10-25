"""When the scenic route isn't worth it, the server says so on every path.

A plan's scenic arm gains at least the menu's half mile of beautiful road
(`options.MENU_FIRST_MIN_KM`) or is the fastest route, with `"no_gain": true`
on the scenic Feature saying why. No path ever hands back a scenic route with
fewer beautiful km than the fastest. A moving car is never held to the
minimum. docs/low-scenery-fallback.md.
"""

import sys
from datetime import date

import pytest

from conftest import DATA, ROOT, ROUTER_DATA

ON = date(2027, 7, 15)

HANCOCK = "42.4443,-73.0787"
SHUTESBURY = "42.4945,-72.4684"
WORCESTER = "42.2626,-71.8023"
BOSTON = "42.3551,-71.0657"
ATTLEBORO_A = "41.9019,-71.0931"
ATTLEBORO_B = "41.9166,-71.1141"

# Hancock -> Shutesbury at pref 0.25 on processed-ne: the scenic search finds a
# different route, no slower, for 21.4 -> 21.9 beautiful km. Under the minimum.
SMALL_GAIN = {"from": HANCOCK, "to": SHUTESBURY, "pref": "0.25"}
# Worcester -> Boston at pref 0.5 gains far more than the minimum on any path.
REAL_GAIN = {"from": WORCESTER, "to": BOSTON, "pref": "0.5"}


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


@pytest.fixture
def busy(server, monkeypatch):
    """A client whose plans take the plain path, as one overlapping another
    request does: `options=1` is sent, the menu does not run."""
    monkeypatch.setattr(server, "_today", lambda: ON)
    monkeypatch.setattr(server, "ROUTE_OPTIONS", False)
    return server.app.test_client()


@pytest.fixture
def alone(server, monkeypatch):
    """A client whose plans get the menu."""
    monkeypatch.setattr(server, "_today", lambda: ON)
    monkeypatch.setattr(server, "ROUTE_OPTIONS", True)
    return server.app.test_client()


def _arms(body):
    return body["fastest"], body["scenic"]


def _same(body):
    fastest, scenic = _arms(body)
    return fastest["geometry"] == scenic["geometry"]


# --------------------------------------------------------------- the decision

class Arm:
    def __init__(self, score, km):
        self.mean_score = score
        self.beautiful_km = km


class TestTheDecision:
    """`_worth_the_detour`, on stand-ins: each branch in one place."""

    def test_fewer_beautiful_km_falls_back_on_every_path(self, server):
        # The Nevada case: the mean rose and the good road went 10 -> 1 km.
        fastest = Arm(4.0, 10.0)
        for planning in (True, False):
            route, no_gain = server._worth_the_detour(fastest, Arm(4.2, 1.0),
                                                      planning)
            assert route is fastest and no_gain

    def test_a_lower_mean_still_falls_back(self, server):
        fastest = Arm(5.794, 3.0)
        route, no_gain = server._worth_the_detour(fastest, Arm(5.210, 3.0), False)
        assert route is fastest and no_gain
        # ...and when that route did gain the minimum, it is not "no gain".
        route, no_gain = server._worth_the_detour(fastest, Arm(5.5, 9.0), True)
        assert route is fastest and not no_gain

    def test_a_plan_needs_the_minimum(self, server):
        fastest = Arm(4.0, 2.0)
        small = Arm(4.1, 2.0 + server.route_options.MENU_FIRST_MIN_KM - 0.01)
        assert server._worth_the_detour(fastest, small, True) == (fastest, True)
        enough = Arm(4.1, 2.0 + server.route_options.MENU_FIRST_MIN_KM)
        assert server._worth_the_detour(fastest, enough, True) == (enough, False)

    def test_a_moving_car_is_never_held_to_the_minimum(self, server):
        """Trap 2: the gain left near the end of a scenic drive is naturally
        under half a mile."""
        fastest = Arm(4.0, 2.0)
        small = Arm(4.1, 2.3)
        assert server._worth_the_detour(fastest, small, False) == (small, False)

    def test_pref_zero_is_not_no_gain(self, server):
        fastest = Arm(4.0, 0.0)
        assert server._worth_the_detour(fastest, fastest, True) == (fastest, False)


# ------------------------------------------------------- the plain path, a plan

class TestTheBusyFallback:
    def test_a_plan_that_gains_under_the_minimum_gets_the_fastest(self, busy):
        body = busy.post("/api/route", data={**SMALL_GAIN, "options": "1"}).get_json()
        assert set(body) == {"fastest", "scenic"}, "the menu ran"
        assert _same(body)
        fastest, scenic = _arms(body)
        assert scenic["properties"]["no_gain"] is True
        assert "no_gain" not in fastest["properties"]
        for k in ("minutes", "km", "mean_score", "beautiful_km"):
            assert scenic["properties"][k] == fastest["properties"][k]

    def test_a_plan_that_gains_the_minimum_keeps_its_scenic_route(self, server, busy):
        body = busy.post("/api/route", data={**REAL_GAIN, "options": "1"}).get_json()
        fastest, scenic = _arms(body)
        assert not _same(body)
        assert "no_gain" not in scenic["properties"]
        gain = scenic["properties"]["beautiful_km"] - fastest["properties"]["beautiful_km"]
        assert gain >= server.route_options.MENU_FIRST_MIN_KM

    def test_pref_zero_carries_no_reason(self, busy):
        body = busy.post("/api/route", data={**SMALL_GAIN, "pref": "0",
                                             "options": "1"}).get_json()
        assert _same(body)
        assert "no_gain" not in body["scenic"]["properties"]

    @pytest.mark.parametrize("pref", ["0.25", "0.5", "1.0"])
    @pytest.mark.parametrize("pair", [
        (HANCOCK, SHUTESBURY), (WORCESTER, BOSTON), (ATTLEBORO_A, ATTLEBORO_B),
        ("42.1821,-71.2290", "42.0692,-71.3397"),
        ("41.9627,-71.6950", "42.0043,-71.7460"),
        ("42.2267,-71.5381", "42.0949,-71.4575"),
    ])
    def test_no_plan_offers_a_scenic_route_under_the_minimum(self, server, busy,
                                                             pair, pref):
        """Done-looks-like 1, on the real graph: the scenic arm of a plan is
        the fastest, with the reason, or gains at least half a mile."""
        body = busy.post("/api/route", data={"from": pair[0], "to": pair[1],
                                             "pref": pref, "options": "1"}).get_json()
        fastest, scenic = (a["properties"] for a in _arms(body))
        if _same(body):
            assert scenic.get("no_gain") is True
        else:
            assert "no_gain" not in scenic
            assert (scenic["beautiful_km"] - fastest["beautiful_km"]
                    >= server.route_options.MENU_FIRST_MIN_KM)


# -------------------------------------------------- the plain path, not a plan

class TestAMovingCar:
    """Reroutes never send `options=1`, so the minimum never reaches them."""

    def test_a_reroute_keeps_a_small_gain(self, busy):
        """The request a reroute without a heading sends: a car below 2 m/s
        or on a fix with no course (`NavigationModel.usableHeading`). The
        brief's "no heading" alone would have held it to the minimum."""
        body = busy.post("/api/route", data=SMALL_GAIN).get_json()
        fastest, scenic = (a["properties"] for a in _arms(body))
        assert not _same(body), "the scenic search no longer finds a small gain here"
        assert 0 <= scenic["beautiful_km"] - fastest["beautiful_km"] < 0.805
        assert "no_gain" not in scenic

    def test_a_heading_is_never_a_plan(self, busy):
        """Belt and braces: `options=1` with a heading is not something the
        app sends, and still gets no minimum."""
        planned = busy.post("/api/route", data={**SMALL_GAIN, "options": "1",
                                                "heading": "90"}).get_json()
        plain = busy.post("/api/route", data={**SMALL_GAIN,
                                              "heading": "90"}).get_json()
        assert planned == plain

    @pytest.mark.parametrize("pref", ["0.25", "0.5", "1.0"])
    @pytest.mark.parametrize("pair", [
        (HANCOCK, SHUTESBURY), (WORCESTER, BOSTON),
        ("42.1821,-71.2290", "42.0692,-71.3397"),
        ("41.9627,-71.6950", "42.0043,-71.7460"),
    ])
    def test_no_route_has_fewer_beautiful_km_than_the_fastest(self, busy, pair, pref):
        for extra in ({}, {"heading": "90"}):
            body = busy.post("/api/route", data={"from": pair[0], "to": pair[1],
                                                 "pref": pref, **extra}).get_json()
            fastest, scenic = (a["properties"] for a in _arms(body))
            assert scenic["beautiful_km"] >= fastest["beautiful_km"]


# ------------------------------------------------------------------ the menu

class TestTheMenu:
    def test_a_menu_with_gain_carries_no_reason(self, alone):
        body = alone.post("/api/route", data={**REAL_GAIN, "options": "1"}).get_json()
        assert "options" in body
        assert "no_gain" not in body["scenic"]["properties"]

    def test_over_budget_is_not_no_gain(self, server, alone, monkeypatch):
        """Trap 3: every option over the budget puts the default on the
        fastest, but the options are still on the dial."""
        monkeypatch.setattr(server.route_options, "DEFAULT_MAX_EXTRA_SHARE", 0.0)
        body = alone.post("/api/route", data={**REAL_GAIN, "options": "1"}).get_json()
        assert body["options"]["default"] == 0
        assert len(body["options"]["menu"]) > 1
        assert _same(body)
        assert "no_gain" not in body["scenic"]["properties"]

    def test_nothing_reaching_the_minimum_is_no_gain(self, server, alone, monkeypatch):
        """A frontier whose best gain is under the minimum, made so by raising
        the minimum rather than by finding such a trip."""
        monkeypatch.setattr(server.route_options, "DEFAULT_MAX_EXTRA_SHARE", 0.0)
        monkeypatch.setattr(server.route_options, "MENU_FIRST_MIN_KM", 1e6)
        body = alone.post("/api/route", data={**REAL_GAIN, "options": "1"}).get_json()
        assert body["options"]["default"] == 0
        assert body["scenic"]["properties"]["no_gain"] is True
        assert "no_gain" not in body["fastest"]["properties"]

    def test_a_point_under_the_minimum_is_not_offered(self, server, alone, monkeypatch):
        """The menu's hole: with the budget left alone, a frontier under the
        minimum used to keep its most scenic point and default to it."""
        monkeypatch.setattr(server.route_options, "MENU_FIRST_MIN_KM", 1e6)
        body = alone.post("/api/route", data={**REAL_GAIN, "options": "1"}).get_json()
        assert len(body["options"]["menu"]) == 1
        assert body["options"]["default"] == 0
        assert _same(body)
        assert body["scenic"]["properties"]["no_gain"] is True

    def test_a_trip_with_no_scenic_alternative_is_no_gain(self, alone):
        """A short hop whose scenic base is no slower than the fastest:
        `t_max <= 0` or an empty front, the menu's own no-gain cases."""
        body = alone.post("/api/route", data={"from": ATTLEBORO_A,
                                              "to": ATTLEBORO_B, "pref": "0.5",
                                              "options": "1"}).get_json()
        assert "options" in body
        if len(body["options"]["menu"]) > 1:
            pytest.skip("the graph now finds an option on this hop")
        assert body["scenic"]["properties"]["no_gain"] is True

    def test_a_chosen_option_is_held_to_the_guard_only(self, server, alone):
        """Switch points mean the driver chose the option, or is driving it."""
        body = alone.post("/api/route", data={**REAL_GAIN, "options": "1"}).get_json()
        chosen = [o for o in body["options"]["menu"][1:]
                  if o["leave"] is not None and o["rejoin"] is not None][0]
        sp = lambda p: f"{p['lat']},{p['lon']},{p['heading']}"  # noqa: E731
        got = alone.post("/api/route", data={**REAL_GAIN, "pref": "1",
                                             "leave": sp(chosen["leave"]),
                                             "rejoin": sp(chosen["rejoin"])}).get_json()
        fastest, scenic = (a["properties"] for a in _arms(got))
        assert scenic["beautiful_km"] >= fastest["beautiful_km"]
        assert "switch" in scenic
