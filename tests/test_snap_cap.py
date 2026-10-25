"""The snap cap: a point far from every road is refused after a bounded
search, on every endpoint, and a point near one snaps as it always did
(docs/snap-cap.md).

The work is asserted, never the wall time: lines measured by
`LineIndex.nearest` and the squares it searched, counted where both versions
of it ask the grid for candidates. Wall clocks on this shared Mac are noise.
"""

import math
import threading
import time

import numpy as np
import pytest
import shapely

from router import SNAP_MAX_M, OutOfReach, _FROM_M, _TO_M
from test_api import _refusal, _server, client  # noqa: F401  (client is a fixture)

# Hostile points, as (name, lat, lon). Each lies more than SNAP_MAX_M from
# every road of the New England graph, most of them inside its bounding box
# or near it, where a bounding-box check would have let them through.
FUZZ = [
    ("10 km off Cape Ann", 42.62, -70.47),
    ("10 km off Nantucket", 41.15, -69.85),
    ("mid Gulf of Maine", 43.0, -68.5),
    ("400 km off the Atlantic coast", 36.46994, -70.93004),
    ("10 km into the Gulf of Mexico", 29.10, -90.20),
    ("400 km into the Gulf of Mexico", 25.5, -90.0),
    ("10 km off Oregon", 44.6, -124.2),
    ("400 km into the Pacific", 37.0, -127.5),
    ("mid Lake Michigan", 43.6, -87.1),
    ("the Nevada desert", 39.30, -116.80),
    ("Hudson Bay", 60.0, -86.0),
    ("central Mexico", 23.0, -102.0),
    ("null island", 0.0, 0.0),
    ("the north pole", 90.0, 0.0),
    ("the south pole", -90.0, 0.0),
    ("near the north pole", 89.9, -71.0),
    ("the antimeridian", 0.0, 180.0),
    ("the antimeridian, west", 45.0, -180.0),
]
# Refused as unreadable before any search.
UNREADABLE = ["91,0", "-91,0", "0,181", "0,-181", "nan,nan", "inf,0", "0,-inf"]

# The most lines a refused request may measure. A refusal searches squares up
# to SNAP_MAX_M across, at most three times (a destination's road, its
# service ways and its road again, never more). The densest such square of
# New England, 10 km across around Cambridge, holds 24,595 roads and 13,697
# service ways (measured 2026-10-24), and a refused point's square holds no
# road within reach at all, so far fewer. Before the cap, the 400 km
# offshore point measured 1.3 million on this graph and tens of millions on
# the national one.
MAX_LINES = 100_000
# The most squares one bounded `nearest` searches: 250 m, 1 km, 4 km, then
# SNAP_MAX_M itself.
MAX_SQUARES = 4
# The most `nearest` calls one request makes: a start, a destination's three
# (and the entrance it snaps to), and a waypoint.
MAX_NEAREST = 6


class Work:
    """Lines measured and squares searched by every `nearest`, counted at the
    grid lookup both versions of it make once per square."""

    def __init__(self, monkeypatch, router):
        self.lines = self.squares = 0
        for tree in (router._edge_tree, router._access_tree):
            if tree is None:
                continue
            inner = tree._candidates

            def counted(*box, _inner=inner):
                found = _inner(*box)
                self.lines += len(found)
                self.squares += 1
                return found
            monkeypatch.setattr(tree, "_candidates", counted)


@pytest.fixture
def work(client, monkeypatch):
    return Work(monkeypatch, _server().ROUTER)


def _far(router, lat, lon):
    """Skip a point this graph does reach (a fixture build may differ)."""
    x, y = _TO_M.transform(lon, lat)
    if math.isfinite(x) and math.isfinite(y):
        point = shapely.Point(x, y)
        for e in router._edge_tree.query(point.buffer(SNAP_MAX_M)):
            if router._edge_geom_m[int(e)].distance(point) <= SNAP_MAX_M:
                pytest.skip(f"{lat},{lon} has a road within {SNAP_MAX_M:.0f} m here")


NEEDHAM = "42.2809,-71.2378"
BOSTON = "42.3551,-71.0657"


def _requests(ll):
    """The point in every place a request takes one: (label, method, path, body)."""
    return [
        ("route from", "post", "/api/route", {"from": ll, "to": BOSTON}),
        ("route to", "post", "/api/route", {"from": BOSTON, "to": ll}),
        ("route via", "post", "/api/route", {"from": NEEDHAM, "to": BOSTON, "via": ll}),
        ("reroute from", "post", "/api/route",
         {"from": ll, "to": BOSTON, "heading": "90"}),
        ("loop", "post", "/api/loop", {"from": ll, "km": "40"}),
        ("loop limit", "post", "/api/loop/limit", {"from": ll}),
    ]


@pytest.mark.parametrize("name,lat,lon", FUZZ, ids=[f[0] for f in FUZZ])
def test_a_point_far_from_every_road_is_refused_after_a_bounded_search(
        client, work, name, lat, lon):
    """Each endpoint, each place a point goes: OUTSIDE_COVERAGE, with the work
    of a few squares and never a continent's."""
    _far(_server().ROUTER, lat, lon)
    for label, method, path, body in _requests(f"{lat},{lon}"):
        work.lines = work.squares = 0
        response = getattr(client, method)(path, data=body)
        _refusal(response, 400, "OUTSIDE_COVERAGE")
        assert work.lines <= MAX_LINES, (label, work.lines)
        assert work.squares <= MAX_NEAREST * MAX_SQUARES, (label, work.squares)


@pytest.mark.parametrize("ll", UNREADABLE)
def test_a_point_off_the_earth_is_refused_before_any_search(client, work, ll):
    for label, method, path, body in _requests(ll):
        work.lines = work.squares = 0
        _refusal(getattr(client, method)(path, data=body), 400, "BAD_INPUT")
        assert work.squares == 0, label


def test_one_nearest_searches_at_most_four_squares(client, work):
    """The cut-off itself, on the 400 km point that took 94-618 s nationally."""
    r = _server().ROUTER
    x, y = _TO_M.transform(-70.93004, 36.46994)
    assert r._edge_tree.nearest(shapely.Point(x, y), SNAP_MAX_M) is None
    assert work.squares == MAX_SQUARES
    work.lines = work.squares = 0
    with pytest.raises(OutOfReach):
        r.snap_destination(36.46994, -70.93004, limit=SNAP_MAX_M)
    # `_snap` refuses before the access layer is ever searched.
    assert work.squares == MAX_SQUARES


def test_a_square_across_the_antimeridian_measures_no_roads(client, work):
    """In degrees such a square is two boxes at the map's edges. Read as one
    band round the earth at Boston's latitude, it measured every road of
    Massachusetts in that band (docs/snap-cap.md, "The antimeridian")."""
    r = _server().ROUTER
    for lon in (-180.0, 180.0):
        x, y = _TO_M.transform(lon, 42.36)
        assert r._edge_tree.nearest(shapely.Point(x, y), SNAP_MAX_M) is None
    assert work.squares == 2 * MAX_SQUARES
    assert work.lines == 0


def test_without_a_limit_snap_still_answers_an_index(client):
    """Tools, studies and the loop builder call `snap` with no limit and take
    an int back whatever the distance (docs/snap-cap.md, "Other callers")."""
    r = _server().ROUTER
    node, off = r.snap(42.62, -70.47)
    assert isinstance(node, int) and off > SNAP_MAX_M


def _sample(r, n, rng):
    """Points on, beside and kilometres off random roads, and in car parks."""
    pts = []
    for lo, hi in ((0.0, 8.0), (30.0, 300.0), (1000.0, 4900.0)):
        for row in rng.integers(0, len(r._edge_geom_m), n):
            p = r._edge_geom_m[int(row)].interpolate(rng.random(), normalized=True)
            a, d = rng.random() * 2 * math.pi, rng.uniform(lo, hi)
            pts.append((p.x + d * math.cos(a), p.y + d * math.sin(a)))
    if r._access_tree is not None:
        for row in rng.integers(0, len(r._access_geom_m), n):
            p = r._access_geom_m[int(row)].interpolate(rng.random(), normalized=True)
            pts.append((p.x, p.y))
    return pts


def test_within_reach_every_snap_is_unchanged(client):
    """Bounded against unbounded on the same graph: the same line (so the
    same tie rule), the same node and the same offset, at rest, moving and
    as a destination. tools/snap_cap/parity.py runs this against the code
    before the cap, on many more points."""
    r = _server().ROUTER
    rng = np.random.default_rng(20261023)
    within = 0
    for x, y in _sample(r, 60, rng):
        point = shapely.Point(x, y)
        lon, lat = _FROM_M.transform(x, y)
        e = r._edge_tree.nearest(point)
        if r._edge_geom_m[e].distance(point) > SNAP_MAX_M:
            assert r._edge_tree.nearest(point, SNAP_MAX_M) is None
            with pytest.raises(OutOfReach):
                r.snap(lat, lon, limit=SNAP_MAX_M)
            continue
        within += 1
        assert r._edge_tree.nearest(point, SNAP_MAX_M) == e
        if r._access_tree is not None:
            a = r._access_tree.nearest(point)
            near = r._access_geom_m[a].distance(point) <= SNAP_MAX_M
            assert r._access_tree.nearest(point, SNAP_MAX_M) == (a if near else None)
        h = float(rng.uniform(0, 360))
        assert r.snap(lat, lon, limit=SNAP_MAX_M) == r.snap(lat, lon)
        assert (r.snap(lat, lon, h, True, limit=SNAP_MAX_M)
                == r.snap(lat, lon, h, True))
        assert (r.snap_start(lat, lon, None, True, limit=SNAP_MAX_M)
                == r.snap_start(lat, lon, None, True))
        assert (r.snap_destination(lat, lon, limit=SNAP_MAX_M)
                == r.snap_destination(lat, lon))
    assert within > 150


def test_an_island_car_park_entrance_beyond_the_limit_still_snaps(client):
    """A pin within reach whose car park's entrance is not: on Mount Desert
    Island the entrance lies 6.7 km from the nearest road the snap knows, and
    bounding that third search by SNAP_MAX_M refused a pin 4.9 km off. Found
    by the parity run, 21 of 20,865 points (docs/snap-cap.md)."""
    r = _server().ROUTER
    lat, lon = 44.146414079353356, -68.55470821363215
    entry = r.access_point(lat, lon)
    if entry is None:
        pytest.skip("this build has no car park entrance here")
    ex, ey = _TO_M.transform(entry[1], entry[0])
    at_entry = shapely.Point(ex, ey)
    if r._edge_geom_m[r._edge_tree.nearest(at_entry)].distance(at_entry) <= SNAP_MAX_M:
        pytest.skip("this build has a road within reach of the entrance")
    assert r.snap(lat, lon)[1] <= SNAP_MAX_M
    assert (r.snap_destination(lat, lon, limit=SNAP_MAX_M)
            == r.snap_destination(lat, lon))


def test_an_ordinary_route_is_untouched(client):
    response = client.post("/api/route", data={"from": NEEDHAM, "to": BOSTON})
    assert response.status_code == 200


# --- The health route -------------------------------------------------------

@pytest.fixture
def fresh_health(client, monkeypatch):
    """The health route with no plan cached, and its plans counted."""
    server = _server()
    monkeypatch.setattr(server, "_health_route", None)
    monkeypatch.setattr(server, "_health_route_began", None)
    plans = []
    inner = server._plan_health_route

    def counted():
        plans.append(1)
        return inner()
    monkeypatch.setattr(server, "_plan_health_route", counted)
    return server, plans


def test_the_health_route_plans_and_says_route_ok(client, fresh_health):
    server, plans = fresh_health
    response = client.get("/api/health/route")
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["status"] == "route_ok"
    assert body["seconds"] < server.HEALTH_ROUTE_SLOW_S and body["km"] > 5
    assert plans == [1]


def test_the_health_route_plans_at_most_once_a_minute(client, fresh_health,
                                                      monkeypatch):
    server, plans = fresh_health
    for _ in range(5):
        assert client.get("/api/health/route").status_code == 200
    assert len(plans) == 1
    # Past the minute, the next call plans again.
    planned, body, status = server._health_route
    monkeypatch.setattr(server, "_health_route",
                        (planned - server.HEALTH_ROUTE_TTL_S, body, status))
    client.get("/api/health/route")
    assert len(plans) == 2


def test_a_failed_plan_is_a_503_without_the_keyword(client, fresh_health,
                                                    monkeypatch):
    server, _ = fresh_health
    monkeypatch.setattr(server.ROUTER, "route", lambda *a, **k: None)
    response = client.get("/api/health/route")
    assert response.status_code == 503
    text = response.get_data(as_text=True)
    assert "route_ok" not in text and response.get_json()["reason"] == "no route"


def test_a_slow_plan_is_a_503_without_the_keyword(client, fresh_health,
                                                  monkeypatch):
    server, _ = fresh_health
    monkeypatch.setattr(server, "HEALTH_ROUTE_SLOW_S", 0.0)
    response = client.get("/api/health/route")
    assert response.status_code == 503
    assert "route_ok" not in response.get_data(as_text=True)
    assert response.get_json()["reason"].startswith("slow")


def test_a_plan_raising_is_a_503_not_a_500(client, fresh_health, monkeypatch):
    server, _ = fresh_health

    def broken(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(server.ROUTER, "route", broken)
    response = client.get("/api/health/route")
    assert response.status_code == 503
    assert response.get_json()["reason"] == "error: RuntimeError"


def test_the_health_route_never_plans_twice_at_once(client, fresh_health,
                                                    monkeypatch):
    """Callers during a plan are answered without planning; with nothing
    cached they wait for it, and a plan running past the limit is reported
    as the stall it is. Never the loop or rejoin lock."""
    server, _ = fresh_health
    release = threading.Event()
    inner = server._plan_health_route
    loop_free = []

    def held():
        loop_free.append(not server.LOOP_LOCK.locked()
                         and not server.REJOIN_LOCK.locked())
        release.wait(10)
        return inner()
    monkeypatch.setattr(server, "_plan_health_route", held)
    monkeypatch.setattr(server, "HEALTH_ROUTE_SLOW_S", 0.3)
    first = []
    t = threading.Thread(target=lambda: first.append(
        client.get("/api/health/route")))
    t.start()
    while server._health_route_began is None:
        time.sleep(0.01)
    # Nothing cached and a plan under way: waits for it up to the limit,
    # then reports the plan still running as a failure.
    waiting = client.get("/api/health/route")
    assert waiting.status_code == 503
    assert waiting.get_json()["reason"].startswith("slow")
    release.set()
    t.join(10)
    # One plan, the first caller's, taken under neither loop lock.
    assert loop_free == [True]
    assert server._health_route is not None and first
