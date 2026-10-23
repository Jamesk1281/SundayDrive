"""The server, in process, with its clock and its closure table under our control.

Imports server/app.py exactly as serve.py does, so every route measured here is
the one `_route` would answer, and changes nothing on disk:

  set_day(d)        replaces `app._today`, the hook the tests use;
  set_table(df)     swaps ROUTER.closures for a SeasonalClosures built from a
                    modified copy of seasonal_closures.parquet (a ban, a margin);
  set_avoid(edges)  closes extra undirected edges for every search, standing in
                    for a P5 "avoid this road" parameter the server lacks;
  route(...)        POST /api/route through Flask's test client, returning the
                    JSON and the RouteResults `_route` built (captured at `_led`).

Set SUNDAYDRIVE_DATA (and SUNDAYDRIVE_PACK for the national graph) before
importing. Nothing here writes under data/.
"""

import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "pipeline"))

for var in ("SUNDAYDRIVE_DATA",):
    if not os.environ.get(var):
        raise SystemExit(f"set {var}: the default data/processed is the old MA-only build")

import app as server                         # noqa: E402
from router import SeasonalClosures, _osm_ends  # noqa: E402

ROUTER = server.ROUTER
DATA = Path(server.PROCESSED)
BASE_TABLE = pd.read_parquet(DATA / "seasonal_closures.parquet")
if "rule" not in BASE_TABLE.columns:
    BASE_TABLE["rule"] = "edge"
    BASE_TABLE["node_id"] = -1
    BASE_TABLE["at_m"] = np.nan
_ORIGINAL_CLOSURES = ROUTER.closures
_ORIGINAL_CLOSED_SLOTS = ROUTER._closed_slots
CLIENT = server.app.test_client()
_DAY = [date(2026, 8, 15)]
_AVOID = [None]          # sorted directed slots, or None
_CAPTURED = []


def set_day(d: date):
    _DAY[0] = d
    server._today = lambda: _DAY[0]


set_day(_DAY[0])


def set_table(table: pd.DataFrame | None):
    """Close by `table` instead of the deployed one; None restores it."""
    if table is None:
        ROUTER.closures = _ORIGINAL_CLOSURES
    else:
        ROUTER.closures = SeasonalClosures(table.reset_index(drop=True), *_osm_ends(ROUTER))
    ROUTER._closed_slots_by_version = {}
    # The route caches key on the closure version, and a swapped table reuses
    # version tuples with other meanings: empty every cache we can find.
    _clear_caches()


def _clear_caches():
    # The loop planners' field and cost caches, and the server's built loops,
    # are the caches keyed on the closure version (looper.py `_fields`,
    # `_costs`; app.py LOOP_RESULTS).
    for planner in (server.LOOPER, server.REJOINER):
        planner._fields_by_key.clear()
        planner._costs_by_key.clear()
    server.LOOP_RESULTS.clear()


def set_avoid(edges):
    """Close these undirected edge rows in every search (P5), or None."""
    if edges is None or not len(edges):
        _AVOID[0] = None
    else:
        mask = np.zeros(ROUTER.m, bool)
        mask[np.asarray(list(edges), np.int64)] = True
        _AVOID[0] = np.flatnonzero(mask[ROUTER.eidx])
    _clear_caches()


def _closed_slots_with_avoid(on):
    base = _ORIGINAL_CLOSED_SLOTS(on) if ROUTER.closures is _ORIGINAL_CLOSURES \
        else type(ROUTER)._closed_slots(ROUTER, on)
    extra = _AVOID[0]
    if extra is None:
        return base
    return extra if base is None else np.union1d(base, extra)


ROUTER._closed_slots = _closed_slots_with_avoid
# A swapped table or an avoid list changes membership the slot flags were built
# from; `_slot_weights` then checks every slot exactly (its `fresh` test) as
# long as closures differs by identity. For the avoid list it does not, so
# force exact membership whenever one is set.
_orig_flag_sources = ROUTER._flag_sources
ROUTER._flag_sources = lambda: (_orig_flag_sources() if _AVOID[0] is None
                                else ("avoid", id(_AVOID[0])))

_orig_led = server._led


def _capture_led(lead, weights, *results):
    out = _orig_led(lead, weights, *results)
    _CAPTURED[:] = out
    return out


server._led = _capture_led


def route(a, b, pref=0.5, heading=None, declined_uturn=False, avoid=None):
    """(status, json, [fastest RouteResult, scenic RouteResult] or []).
    `avoid` is (avoid_edges, avoid_pack) as the app sends them: P5 for real
    (docs/seasonal-road-policy.md)."""
    form = {"from": f"{a[0]},{a[1]}", "to": f"{b[0]},{b[1]}", "pref": str(pref)}
    if heading is not None:
        form["heading"] = f"{heading:.1f}"
    if declined_uturn:
        form["declined_uturn"] = "1"
    if avoid is not None:
        form["avoid_edges"], form["avoid_pack"] = avoid
    _CAPTURED.clear()
    r = CLIENT.post("/api/route", data=form)
    return r.status_code, r.get_json(), list(_CAPTURED)


def loop(start, km, pref=1.0):
    form = {"from": f"{start[0]},{start[1]}", "km": str(km), "pref": str(pref)}
    r = CLIENT.post("/api/loop", data=form)
    return r.status_code, r.get_json()


def window_table(table, window):
    """A copy of `table` with every row's window replaced by `window`."""
    t = table.copy()
    t[["start_month", "start_day", "end_month", "end_day"]] = window
    return t


_ORIGINAL_CAR_CLOSED = ROUTER._car_closed_slots


def open_to_cars(edges):
    """Open these undirected edges that closed_to_cars closes all year, or
    restore the deployed set with None.

    For Trail Ridge Road: today a `vehicle=permit` rule closes it all year,
    and the parallel unit (chip task_b97d53c1) opens it outside its winter
    window, so the brief says to treat it as open in season here."""
    if edges is None:
        ROUTER._car_closed_slots = _ORIGINAL_CAR_CLOSED
    else:
        mask = np.zeros(ROUTER.m, bool)
        mask[np.asarray(list(edges), np.int64)] = True
        drop = np.flatnonzero(mask[ROUTER.eidx])
        ROUTER._car_closed_slots = np.setdiff1d(_ORIGINAL_CAR_CLOSED, drop)
    _clear_caches()


def trail_ridge_permit_edges():
    c = pd.read_parquet(DATA / "closed_to_cars.parquet")
    hit = c[(c["name"].fillna("") == "Trail Ridge Road") & (c["tag"] == "vehicle=permit")]
    return hit["edge"].to_numpy()


def edge_lonlat(e):
    return tuple(ROUTER.lines.coords(int(e)).mean(axis=0))


def cost(result, pref=0.5):
    """The router's own price of a route with nothing seasonal closed
    (`Router.cost_of`, on=None), for P3's offline arithmetic."""
    return ROUTER.cost_of(result, pref, None, 1.0, None)
