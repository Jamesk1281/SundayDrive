"""Replay a fixed New England request set through one checkout's server.

The parity harness of docs/router-at-us-scale.md. Today's router on
data/processed-ne is the oracle, so a run against a snapshot of the `usa`
code writes the reference answers, and a run against this branch replays the
oracle's own requests and writes its answers beside them. `parity_diff.py`
compares the two.

    python parity_run.py --root <checkout> --out answers.json             # oracle
    python parity_run.py --root <checkout> --out new.json --replay answers.json

`--root` is a directory holding `pipeline/` and `server/`; the data directory
is SUNDAYDRIVE_DATA, as for the server. Each request goes through Flask's test
client, so everything the app sees is compared: snapping, both arms, options,
switch points, reroutes with a heading, declined U-turns, loops and loop
rejoins, at a fixed date in summer and one in winter.

The trips are random junctions of graph_nodes.parquet, moved up to 30 m off
the road so snapping does real work, drawn in straight-line distance bands up
to 650 km. Trips over 500 km are the cap's: the oracle answers them, and a
capped server must refuse them. Reroutes start 30% of the way along the
oracle's own route, heading the way it drives there, so both runs ask exactly
the same questions.
"""

import argparse
import importlib
import json
import math
import os
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261018
BANDS_KM = [(2, 20, 6), (20, 60, 8), (60, 150, 10), (150, 300, 10),
            (300, 500, 8), (500, 650, 4)]
SUMMER, WINTER = date(2026, 7, 1), date(2026, 1, 15)
LOOP_KM = (15.0, 40.0, 120.0)
SNAP_POINTS = 3000


def haversine_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def bearing(p, q):
    lon1, lat1, lon2, lat2 = map(math.radians, (p[0], p[1], q[0], q[1]))
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = (math.cos(lat1) * math.sin(lat2)
         - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def jitter(rng, lat, lon, metres=30.0):
    r, a = metres * math.sqrt(rng.random()), 2 * math.pi * rng.random()
    return (lat + r * math.cos(a) / 111_320.0,
            lon + r * math.sin(a) / (111_320.0 * math.cos(math.radians(lat))))


def ll(p):
    return f"{p[0]:.6f},{p[1]:.6f}"


def along(coords, share):
    """The point `share` of the way along a [lon, lat] line, and the bearing
    the line drives there."""
    c = np.asarray(coords, float)
    if len(c) < 2:
        return None
    step = np.array([haversine_km((a[1], a[0]), (b[1], b[0]))
                     for a, b in zip(c[:-1], c[1:])])
    cum = np.concatenate([[0.0], np.cumsum(step)])
    k = int(np.searchsorted(cum, share * cum[-1], side="right")) - 1
    k = min(max(k, 0), len(c) - 2)
    # A heading over the next 50 m or so, the way a phone reports course.
    j = k + 1
    while j < len(c) - 1 and cum[j] - cum[k] < 0.05:
        j += 1
    lon, lat = c[k]
    return (float(lat), float(lon)), bearing(c[k], c[j])


def make_requests(data_dir):
    """The oracle's request list, minus the ones derived from its answers."""
    rng = np.random.default_rng(SEED)
    nodes = pd.read_parquet(Path(data_dir) / "graph_nodes.parquet",
                            columns=["lat", "lon"])
    lat, lon = nodes["lat"].to_numpy(), nodes["lon"].to_numpy()
    trips = []
    for lo_km, hi_km, count in BANDS_KM:
        got = 0
        while got < count:
            i, j = rng.integers(0, len(lat), 2)
            d = haversine_km((lat[i], lon[i]), (lat[j], lon[j]))
            if lo_km <= d < hi_km:
                trips.append((jitter(rng, lat[i], lon[i]),
                              jitter(rng, lat[j], lon[j]), d))
                got += 1
    starts = [jitter(rng, lat[i], lon[i]) for i in rng.integers(0, len(lat), 15)]
    snaps = [(*jitter(rng, lat[i], lon[i], 150.0), float(rng.uniform(0, 360)))
             for i in rng.integers(0, len(lat), SNAP_POINTS)]
    return trips, starts, snaps


class Server:
    """One checkout's app, imported from its own `server/` and `pipeline/`."""

    def __init__(self, root):
        root = Path(root).resolve()
        os.environ["SUNDAYDRIVE_ROUTE_OPTIONS"] = "1"
        sys.path.insert(0, str(root / "server"))
        sys.path.insert(0, str(root / "pipeline"))
        t = time.perf_counter()
        self.app = importlib.import_module("app")
        self.load_s = time.perf_counter() - t
        self.client = self.app.app.test_client()
        self.day = SUMMER
        self.app._today = lambda: self.day

    def ask(self, path, params, day=SUMMER):
        self.day = day
        t, c = time.perf_counter(), time.process_time()
        r = self.client.post(path, data=params)
        # CPU seconds beside wall seconds: the Mac this runs on is shared, and
        # contention inflates the wall clock far more than the CPU time.
        return {"status": r.status_code, "body": r.get_json(),
                "seconds": round(time.perf_counter() - t, 4),
                "cpu": round(time.process_time() - c, 4)}


def oracle_requests(server, trips, starts):
    """Ask the oracle, deriving the reroutes and option fetches from its own
    answers. Returns [(path, params, day, answer)]."""
    out = []

    def ask(path, params, day=SUMMER):
        a = server.ask(path, params, day)
        out.append({"path": path, "params": params, "day": day.isoformat(),
                    "answer": a})
        return a

    weighted = {"w_coast": "2", "w_farm": "0", "w_town": "3"}
    for n, (a, b, d) in enumerate(trips):
        base = {"from": ll(a), "to": ll(b)}
        print(f"trip {n}: {d:.0f} km", flush=True)
        ask("/api/route", {**base, "pref": "0"})
        mid = ask("/api/route", {**base, "pref": "0.5"})
        ask("/api/route", {**base, "pref": "1"})
        ask("/api/route", {**base, "pref": "1", **weighted})
        ask("/api/route", {**base, "pref": "0.5", "avoid_unpaved": "0"})
        ask("/api/route", {**base, "pref": "0.5", "avoid_unpaved": "2"})
        ask("/api/route", {**base, "pref": "0.5"}, WINTER)
        plan = ask("/api/route", {**base, "pref": "0.5", "options": "1"})
        menu = ((plan["body"] or {}).get("options") or {}).get("menu", [])
        for opt in menu[1:4]:
            sw = {k: f"{opt[k]['lat']},{opt[k]['lon']},{opt[k]['heading']}"
                  for k in ("leave", "rejoin") if opt.get(k)}
            if sw:
                ask("/api/route", {**base, "pref": "0.5", **sw})
        if mid["status"] != 200:
            continue
        coords = mid["body"]["scenic"]["geometry"]["coordinates"]
        point = along(coords, 0.3)
        if point is None:
            continue
        (plat, plon), h = point
        here = {"from": f"{plat:.6f},{plon:.6f}", "to": base["to"], "pref": "0.5"}
        ask("/api/route", {**here, "heading": f"{h:.1f}"})
        ask("/api/route", {**here, "heading": f"{(h + 180.0) % 360.0:.1f}",
                           "declined_uturn": "1"})
        scenic = (plan["body"] or {}).get("scenic") or {}
        switch = (scenic.get("properties") or {}).get("switch")
        if switch:
            p = along(scenic["geometry"]["coordinates"], 0.15)
            if p is not None:
                (qlat, qlon), qh = p
                sw = {k: f"{v['lat']},{v['lon']},{v['heading']}"
                      for k, v in switch.items() if v}
                ask("/api/route", {"from": f"{qlat:.6f},{qlon:.6f}",
                                   "to": base["to"], "pref": "0.5",
                                   "heading": f"{qh:.1f}", **sw})

    for n, s in enumerate(starts):
        print(f"loop start {n}", flush=True)
        for km in LOOP_KM:
            loop = ask("/api/loop", {"from": ll(s), "km": f"{km:g}"})
        ask("/api/loop", {"from": ll(s), "km": "40"}, WINTER)
        if loop["status"] == 200:
            alts = loop["body"].get("alternatives") or []
            if alts:
                ask("/api/loop", {"from": ll(s), "km": "120",
                                  "sector": alts[-1]["sector"]})
            coords = loop["body"]["loop"]["geometry"]["coordinates"]
            p = along(coords, 0.2)
            turn = loop["body"]["meta"]["turnaround"]
            if p is not None:
                (qlat, qlon), _ = p
                ask("/api/route", {"from": f"{qlat:.6f},{qlon:.6f}",
                                   "to": ll(s), "via": f"{turn[0]},{turn[1]}",
                                   "pref": "1"})
    for s in starts[:2]:
        ask("/api/loop", {"from": ll(s), "km": "300"})
    return out


def snap_answers(router, snaps):
    ids = router.nodes["node_id"].to_numpy() if hasattr(router, "nodes") else None
    real = router.real_node

    def name(i):
        return [int(ids[real[i]]), int(i - len(ids)) if i >= len(ids) else -1]

    out = []
    for lat, lon, h in snaps:
        a, a_off = router.snap(lat, lon)
        b, b_off = router.snap(lat, lon, heading=h)
        c, c_off = router.snap_destination(lat, lon)
        out.append([name(a), round(a_off, 6), name(b), round(b_off, 6),
                    name(c), round(c_off, 6)])
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--replay")
    args = p.parse_args()
    server = Server(args.root)
    trips, starts, snaps = make_requests(os.environ["SUNDAYDRIVE_DATA"])
    t = time.perf_counter()
    if args.replay:
        reference = json.loads(Path(args.replay).read_text())["requests"]
        requests = []
        for n, r in enumerate(reference):
            if n % 50 == 0:
                print(f"request {n}/{len(reference)}", flush=True)
            day = date.fromisoformat(r["day"])
            requests.append({**r, "answer": server.ask(r["path"], r["params"], day)})
    else:
        requests = oracle_requests(server, trips, starts)
    serve_s = time.perf_counter() - t
    t = time.perf_counter()
    snapped = snap_answers(server.app.ROUTER, snaps)
    Path(args.out).write_text(json.dumps({
        "root": str(args.root), "load_s": server.load_s, "serve_s": serve_s,
        "snap_s": time.perf_counter() - t, "requests": requests,
        "snaps": snapped}))
    print(f"wrote {args.out}: {len(requests)} requests in {serve_s:.0f} s, "
          f"load {server.load_s:.0f} s", flush=True)


if __name__ == "__main__":
    main()
