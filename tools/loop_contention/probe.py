"""K-1 capacity probe: driving requests timed idle and under loop-planning load.

    python probe.py BASE NODES_PARQUET --clients 0 1 0 4 --duration 45 --label before-opt0-1

Local only, or a second process on a localhost port: never the live service.
docs/loop-lock-contention.md has what it measured.

Rows: the loop rejoin (`via`), a default-pref route (with options=1, which is
what the app sends for a plan), and a fastest-only route. Each loaded run starts
N threads posting cold 40 km loops from seeded random graph nodes, back to back;
after a 503 a planner waits 1 s before tapping again, as a person would. Each
loaded run's ratios are to the idle (0-client) run just before it.
"""
import argparse
import json
import statistics
import threading
import time

import numpy as np
import pandas as pd
import requests

REJOIN = {"from": "42.2900,-71.2200", "to": "42.2810,-71.2370",
          "via": "42.2457,-71.2828", "pref": "1.0"}
ROUTE_DEFAULT = {"from": "42.3601,-71.0589", "to": "42.2626,-71.8023",
                 "pref": "0.5", "options": "1"}
ROUTE_FASTEST = {"from": "42.3601,-71.0589", "to": "42.2626,-71.8023",
                 "pref": "0"}
ROWS = [("rejoin", "/api/route", REJOIN),
        ("route_default", "/api/route", ROUTE_DEFAULT),
        ("route_fastest", "/api/route", ROUTE_FASTEST)]
SEEDS = [7, 11, 13, 17, 19, 23]
CLIENT_TIMEOUT = 20.0          # RouteService.timeoutIntervalForResource


def timed(base, path, params, timeout=90):
    t0 = time.perf_counter()
    try:
        r = requests.post(base + path, data=params, timeout=timeout)
        status = r.status_code
    except requests.RequestException as e:
        status = type(e).__name__
    return time.perf_counter() - t0, status


def planner(base, starts, stop, outcomes, lock):
    for lat, lon in starts:
        if stop.is_set():
            return
        t0 = time.perf_counter()
        try:
            r = requests.post(base + "/api/loop",
                              data={"from": f"{lat:.6f},{lon:.6f}", "km": "40"},
                              timeout=CLIENT_TIMEOUT)
            kind = {200: "built", 503: "busy", 404: "no_loop"}.get(
                r.status_code, f"http_{r.status_code}")
            if kind == "busy":
                if "error" not in r.json():
                    kind = "busy_without_json"
        except requests.Timeout:
            kind = "timed_out"
        except requests.RequestException as e:
            kind = type(e).__name__
        with lock:
            outcomes.setdefault(kind, []).append(time.perf_counter() - t0)
        if kind == "busy":
            stop.wait(1.0)


def measure(base, reps):
    out = {name: [] for name, *_ in ROWS}
    for _ in range(reps):
        for name, path, params in ROWS:
            dt, status = timed(base, path, params)
            if status != 200:
                print("non-200", name, status, round(dt, 1), flush=True)
            out[name].append(dt)
    return out


def run(base, nodes, clients, duration, reps):
    if clients == 0:
        return measure(base, reps), {}
    stop = threading.Event()
    outcomes, lock = {}, threading.Lock()
    threads = []
    for i in range(clients):
        rng = np.random.default_rng(SEEDS[i])
        pick = rng.choice(len(nodes), 4000, replace=False)
        starts = list(zip(nodes.lat.values[pick], nodes.lon.values[pick]))
        t = threading.Thread(target=planner,
                             args=(base, starts, stop, outcomes, lock))
        t.start()
        threads.append(t)
    time.sleep(3.0)
    out = {name: [] for name, *_ in ROWS}
    t_end = time.perf_counter() + duration
    while time.perf_counter() < t_end:
        for name, path, params in ROWS:
            dt, status = timed(base, path, params)
            if status != 200:
                print("non-200", name, status, round(dt, 1), flush=True)
            out[name].append(dt)
    stop.set()
    for t in threads:
        t.join()
    return out, {k: len(v) for k, v in outcomes.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("nodes")
    ap.add_argument("--clients", type=int, nargs="+", default=[0, 1, 4])
    ap.add_argument("--duration", type=float, default=50)
    ap.add_argument("--reps", type=int, default=6)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    nodes = pd.read_parquet(a.nodes, columns=["lat", "lon"])
    # Warm the server's own route caches the same way for every run.
    measure(a.base, 1)
    # Each loaded run is compared with the idle run just before it, because
    # this Mac's background load drifts by the minute.
    result = {"label": a.label, "runs": []}
    idle = None
    for c in a.clients:
        times, outcomes = run(a.base, nodes, c, a.duration, a.reps)
        row = {name: {"median": statistics.median(v), "max": max(v), "n": len(v),
                      "over_20s": sum(x > CLIENT_TIMEOUT for x in v)}
               for name, v in times.items()}
        entry = {"clients": c, "rows": row, "planners": outcomes}
        if c == 0:
            idle = row
        elif idle:
            entry["ratios"] = {n: round(r["median"] / idle[n]["median"], 2)
                               for n, r in row.items()}
        result["runs"].append(entry)
        print(a.label, json.dumps(entry), flush=True)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(result, f, indent=1)


if __name__ == "__main__":
    main()
