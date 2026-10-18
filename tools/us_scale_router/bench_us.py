"""Latency by trip length on a US-sized pack, through the server's own code.

    SUNDAYDRIVE_PACK=<pack> python bench_us.py --out results.json [--trips 8]

Loads server/app.py over the pack (SUNDAYDRIVE_DATA may point anywhere: a pack
built by synthetic.py has no processed directory), then times, in one process
and one request at a time:

  route      a plan, both arms (pref 0.5), by straight-line distance band
  options    the same with options=1 (the menu, which costs most)
  reroute    from 30% along the route, with a heading
  loop       a first loop from a new start, by length

On the synthetic pack the trips are drawn inside one copy of New England in
the middle of the map, so the corridor of a long trip spills into the copies
around it as a real one would into neighbouring states. Load time and RSS after
load are reported beside the latencies. Memory under concurrent load is
`load_probe.py`'s.
"""

import argparse
import json
import math
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BANDS_KM = (25, 50, 100, 200, 300, 400, 500)
LOOP_KM = (40.0, 150.0, 300.0, 400.0)


def rss_gb(pid=None):
    pid = pid or os.getpid()
    return int(os.popen(f"ps -o rss= -p {pid}").read()) / 1e6


def footprint_gb(pid=None):
    """macOS's phys_footprint: memory the process holds that the kernel cannot
    simply drop, which leaves out clean pages mapped from a file."""
    out = os.popen(f"footprint -p {pid or os.getpid()} 2>/dev/null").read()
    for line in out.splitlines():
        if "phys_footprint:" in line:
            v, unit = line.split("phys_footprint:")[1].split()[:2]
            return float(v) * {"KB": 1e-6, "MB": 1e-3, "GB": 1.0}[unit]
    return float("nan")


def bearing(p, q):
    lon1, lat1, lon2, lat2 = map(math.radians, (p[0], p[1], q[0], q[1]))
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = (math.cos(lat1) * math.sin(lat2)
         - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--trips", type=int, default=8)
    p.add_argument("--copy", type=int, default=8,
                   help="which New England copy to draw trips in (synthetic)")
    args = p.parse_args()
    os.environ["SUNDAYDRIVE_ROUTE_OPTIONS"] = "1"
    sys.path.insert(0, str(ROOT / "server"))
    sys.path.insert(0, str(ROOT / "pipeline"))
    t = time.perf_counter()
    import app as server
    load_s = time.perf_counter() - t
    r = server.ROUTER
    loaded = {"load_s": load_s, "rss_gb": rss_gb(), "footprint_gb": footprint_gb(),
              "nodes": int(r.n_real), "edges": int(r.m)}
    print(f"loaded {r.n_real:,} nodes in {load_s:.1f} s; RSS {loaded['rss_gb']:.2f} GB, "
          f"footprint {loaded['footprint_gb']:.2f} GB", flush=True)
    client = server.app.test_client()
    rng = np.random.default_rng(7)
    per = r.n_real
    if "synthetic" in (r.region or ""):
        copies = r.n_real // 794_685
        per = r.n_real // copies
        lo, hi = args.copy * per, (args.copy + 1) * per
    else:
        lo, hi = 0, r.n_real
    lat, lon = np.asarray(r.node_lat), np.asarray(r.node_lon)
    rows = []

    def ask(kind, km, params, path="/api/route"):
        t, c = time.perf_counter(), time.process_time()
        resp = client.post(path, data=params)
        dt, cpu = time.perf_counter() - t, time.process_time() - c
        rows.append({"kind": kind, "km": km, "seconds": dt, "cpu": cpu,
                     "status": resp.status_code})
        print(f"  {kind:8s} {km:5.0f} km  {dt:6.2f} s wall  {cpu:6.2f} s cpu  "
              f"{resp.status_code}", flush=True)
        return resp.get_json()

    for band in BANDS_KM:
        got = 0
        while got < args.trips:
            i, j = rng.integers(lo, hi, 2)
            d = float(r._trip(int(i), int(j)).km)
            if not 0.85 * band <= d <= band:
                continue
            got += 1
            base = {"from": f"{lat[i]:.6f},{lon[i]:.6f}",
                    "to": f"{lat[j]:.6f},{lon[j]:.6f}", "pref": "0.5"}
            body = ask("route", d, base)
            ask("options", d, {**base, "options": "1"})
            if body and "scenic" in body:
                c = body["scenic"]["geometry"]["coordinates"]
                k = max(0, int(0.3 * len(c)) - 1)
                h = bearing(c[k], c[min(k + 5, len(c) - 1)])
                ask("reroute", d, {**base, "from": f"{c[k][1]:.6f},{c[k][0]:.6f}",
                                   "heading": f"{h:.1f}"})
    for km in LOOP_KM:
        for _ in range(max(2, args.trips // 2)):
            i = int(rng.integers(lo, hi))
            ask("loop", km, {"from": f"{lat[i]:.6f},{lon[i]:.6f}", "km": f"{km:g}"},
                path="/api/loop")
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    loaded["peak_rss_gb"] = peak / 1e9 if sys.platform == "darwin" else peak / 1e6
    loaded["end_footprint_gb"] = footprint_gb()
    Path(args.out).write_text(json.dumps({"loaded": loaded, "rows": rows}, indent=1))
    print(f"peak RSS {loaded['peak_rss_gb']:.2f} GB; footprint at end "
          f"{loaded['end_footprint_gb']:.2f} GB", flush=True)
    for kind in ("route", "options", "reroute"):
        for band in BANDS_KM:
            s = [x["cpu"] for x in rows if x["kind"] == kind
                 and 0.85 * band <= x["km"] <= band]
            if s:
                print(f"{kind:8s} <= {band:3d} km: p50 {np.median(s):5.2f} s cpu, "
                      f"p90 {np.percentile(s, 90):5.2f} s  (n={len(s)})")
    for km in LOOP_KM:
        s = [x["cpu"] for x in rows if x["kind"] == "loop" and x["km"] == km]
        if s:
            print(f"loop     {km:5.0f} km: p50 {np.median(s):5.2f} s, "
                  f"p90 {np.percentile(s, 90):5.2f} s  (n={len(s)})")


if __name__ == "__main__":
    main()
