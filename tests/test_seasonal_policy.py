"""P5: a reroute rules out the seasonal stretch the driver turned away from
(docs/seasonal-road-policy.md; docs/seasonal-road-risk-verdict.md, Q3).

Each route lists the seasonal stretches it drives; the app sends back the ones
the driver turned from as `avoid_edges`, with the fingerprint they came with,
and every later reroute closes them through the same `blocked` path keep-ahead
uses. Measured on Lincoln Gap, whose window says open on Oct 10: the case of a
road our window calls open that the driver finds shut.

Needs the New England graph (SUNDAYDRIVE_DATA=data/processed-ne); skips
without it. Every date is injected.
"""

import os
import sys
from datetime import date

import numpy as np
import pytest
import shapely
from pyproj import Transformer

from common import CRS_METERS
from conftest import DATA, ROOT, ROUTER_DATA

GAP_OPEN = date(2026, 10, 10)
WARREN = (44.1123, -72.8565)
BRISTOL = (44.1334, -73.0790)
LINCOLN = (44.1050, -72.9960)
# Where Lincoln Gap Road's closed section ends on the Warren side: a driver
# who meets the gate here and turns round faces east.
GAP_EAST_END = (44.094617, -72.910377)
LINCOLN_GAP_DATES = (10, 15, 5, 15)

_TO_M = Transformer.from_crs(4326, CRS_METERS, always_xy=True)


@pytest.fixture(scope="module")
def server():
    missing = [f for f in ROUTER_DATA + ("seasonal_closures.parquet",)
               if not (DATA / f).exists()]
    if missing:
        pytest.skip(f"built graph missing ({', '.join(missing)})")
    os.environ.setdefault("SUNDAYDRIVE_DATA", str(DATA))
    sys.path.insert(0, str(ROOT / "server"))
    import app as server_app
    server_app.app.config["TESTING"] = True
    assert server_app.ROUTER.closures is not None
    return server_app


@pytest.fixture
def client(server, monkeypatch):
    monkeypatch.setattr(server, "_today", lambda: GAP_OPEN)
    return server.app.test_client()


def _ll(point):
    return f"{point[0]},{point[1]}"


def _gap_edges(server):
    """Lincoln Gap Road's own rows: the edges its dated window closes."""
    import pandas as pd
    t = pd.read_parquet(DATA / "seasonal_closures.parquet")
    w = t[["start_month", "start_day", "end_month", "end_day"]].apply(tuple, axis=1)
    return set(t.loc[(t["name"] == "Lincoln Gap Road") & (w == LINCOLN_GAP_DATES),
                     "edge"].astype(int))


def _drives(feature, server, edges):
    """Whether the feature's line runs along any of `edges` (to 1 m)."""
    lon, lat = np.asarray(feature["geometry"]["coordinates"]).T
    line = shapely.LineString(np.column_stack(_TO_M.transform(lon, lat)))
    mids = shapely.line_interpolate_point(
        server.ROUTER._edge_geom_m[sorted(edges)], 0.5, normalized=True)
    return min(p.distance(line) for p in mids) < 1.0


def _gap_stretch(client, server):
    """The plan Warren -> Bristol over the gap, and its stretch on the gap."""
    body = client.post("/api/route", data={"from": _ll(WARREN), "to": _ll(BRISTOL),
                                           "pref": "0.5"}).get_json()
    gap = _gap_edges(server)
    stretches = [s for s in body["scenic"]["properties"]["seasonal"]
                 if gap & set(s["edges"])]
    assert stretches, "the plan no longer crosses Lincoln Gap"
    return body, stretches[0]


def _avoid(stretch, flip=False):
    return ",".join(("" if f != flip else "-") + str(e)
                    for e, f in zip(stretch["edges"], stretch["forward"]))


def _reroute(client, stretch, **extra):
    form = {"from": _ll(GAP_EAST_END), "to": _ll(BRISTOL), "heading": "90",
            "pref": "0.5", **extra}
    if stretch is not None:
        form.setdefault("avoid_edges", _avoid(stretch))
        form.setdefault("avoid_pack", stretch["pack"])
    return client.post("/api/route", data=form)


class TestTheStretches:
    def test_a_route_lists_its_seasonal_stretches(self, client, server):
        body, stretch = _gap_stretch(client, server)
        assert stretch["pack"] == server.EDGES_FINGERPRINT
        assert len(stretch["forward"]) == len(stretch["edges"])
        assert 0 <= stretch["from_m"] < stretch["to_m"] <= body["scenic"]["properties"]["km"] * 1000 + 1
        assert _gap_edges(server) <= set(stretch["edges"])
        # And none of a stretch's edges is free of rows.
        seasonal = set(server.ROUTER.closures.seasonal_edges.tolist())
        for s in body["scenic"]["properties"]["seasonal"] + body["fastest"]["properties"]["seasonal"]:
            assert set(s["edges"]) <= seasonal

    def test_its_directions_are_the_ones_the_route_drove(self, server):
        """`avoid_slots` of a stretch, as listed, are the route's own slots
        on it: so the avoid closes the way the driver was going."""
        r = server.ROUTER
        s, _ = r.snap(*WARREN)
        t, _ = r.snap_destination(*BRISTOL)
        route = r.route(s, t, 0.5, on=GAP_OPEN)
        for stretch in r.seasonal_stretches(route):
            avoid = set(r.avoid_slots(zip(stretch["edges"], stretch["forward"])).tolist())
            driven = {int(k) for k, e in zip(route.slots, r.eidx[route.slots])
                      if int(e) in set(stretch["edges"])}
            assert driven and driven <= avoid
            reverse = set(r.avoid_slots(zip(stretch["edges"],
                                            [not f for f in stretch["forward"]])).tolist())
            assert not driven & reverse

    def test_a_loop_lists_them_too(self, client, server):
        body = client.post("/api/loop", data={"from": _ll(WARREN), "km": "40"}).get_json()
        assert "seasonal" in body["loop"]["properties"]


class TestTheAvoidSet:
    def test_today_the_reroute_sends_the_driver_back_over_the_gap(self, client, server):
        """What P5 fixes (verdict Q3): with the window open, the reroute from
        the gate goes straight back over it."""
        r = _reroute(client, None)
        assert r.status_code == 200
        assert _drives(r.get_json()["scenic"], server, _gap_edges(server))

    @pytest.mark.parametrize("extra", [{}, {"pref": "0"}, {"declined_uturn": "1"}])
    def test_the_ids_are_honoured_in_both_arms(self, client, server, extra):
        _, stretch = _gap_stretch(client, server)
        r = _reroute(client, stretch, **extra)
        assert r.status_code == 200
        for arm in ("fastest", "scenic"):
            assert not _drives(r.get_json()[arm], server, _gap_edges(server)), arm

    def test_a_stale_fingerprint_is_ignored_not_refused(self, client, server):
        _, stretch = _gap_stretch(client, server)
        r = _reroute(client, stretch, avoid_pack="a-pack-from-before-the-redeploy")
        assert r.status_code == 200
        assert _drives(r.get_json()["scenic"], server, _gap_edges(server))
        r = _reroute(client, stretch, avoid_pack="")
        assert r.status_code == 200

    @pytest.mark.parametrize("raw", ["x", ",,", "-", "12a,b", "99999999999", "-0"])
    def test_a_token_that_is_not_a_row_is_dropped(self, client, server, raw):
        _, stretch = _gap_stretch(client, server)
        assert _reroute(client, stretch, avoid_edges=raw).status_code == 200

    def test_the_cap(self, client, server):
        """At most MAX_AVOID_EDGES, the first ones sent: the app sends its
        newest stretch first."""
        _, stretch = _gap_stretch(client, server)
        cap = server.MAX_AVOID_EDGES
        filler = ",".join(["0"] * cap)
        late = _reroute(client, stretch, avoid_edges=filler + "," + _avoid(stretch))
        early = _reroute(client, stretch, avoid_edges=_avoid(stretch) + "," + filler)
        assert late.status_code == early.status_code == 200
        assert _drives(late.get_json()["scenic"], server, _gap_edges(server))
        assert not _drives(early.get_json()["scenic"], server, _gap_edges(server))

    def test_only_the_direction_turned_from_is_closed(self, client, server):
        """A car on the stretch facing back must still be able to drive off
        it (the verdict's "Limits": `Router.snap` routes a moving car forward
        off the road under it). Closing the stretch the other way round sends
        the driver back over the gap again."""
        _, stretch = _gap_stretch(client, server)
        r = _reroute(client, stretch, avoid_edges=_avoid(stretch, flip=True))
        assert r.status_code == 200
        assert _drives(r.get_json()["scenic"], server, _gap_edges(server))


class TestLoops:
    def test_a_loop_rejoin_honours_it(self, client, server):
        """A loop's reroute is /api/route with `via`, answered by
        `LoopPlanner.resume`: both arms close the stretch."""
        _, stretch = _gap_stretch(client, server)
        form = {"from": _ll(WARREN), "via": _ll(LINCOLN), "to": _ll(BRISTOL), "pref": "0.5"}
        plain = client.post("/api/route", data=form)
        avoided = client.post("/api/route", data={**form, "avoid_edges": _avoid(stretch),
                                                   "avoid_pack": stretch["pack"]})
        again = client.post("/api/route", data=form)
        assert plain.status_code == avoided.status_code == again.status_code == 200
        gap = _gap_edges(server)
        assert _drives(plain.get_json()["scenic"], server, gap)
        for arm in ("fastest", "scenic"):
            assert not _drives(avoided.get_json()[arm], server, gap), arm
        # No cache answered one request with the other's route.
        assert _drives(again.get_json()["scenic"], server, gap)

    def test_no_cache_a_reroute_reaches_keys_without_it(self, server):
        """The built-loop cache (LOOP_RESULTS) is /api/loop's, which no
        reroute calls and which takes no avoid set; the rejoin's planner
        caches nothing per request. If either changes, this has to."""
        import inspect
        assert "avoid" not in inspect.signature(server._loop).parameters
        src = inspect.getsource(server.LoopPlanner.resume)
        assert "_fields(" not in src and "_costs(" not in src

    def test_a_spliced_reroute_honours_it(self, server):
        import options
        r = server.ROUTER
        s, _ = r.snap(*WARREN)
        t, _ = r.snap_destination(*BRISTOL)
        route = r.route(s, t, 1.0, on=GAP_OPEN)
        gap = _gap_edges(server)
        assert gap & set(route.edges.index.tolist())
        stretch = next(x for x in r.seasonal_stretches(route) if gap & set(x["edges"]))
        avoid = r.avoid_slots(zip(stretch["edges"], stretch["forward"]))
        spliced = options.spliced_route(r, s, t, on=GAP_OPEN, avoid=avoid)
        assert spliced is not None
        assert not gap & set(spliced.edges.index.tolist())
