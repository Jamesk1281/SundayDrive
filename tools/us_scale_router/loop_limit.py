"""Measure a first loop's CPU time against its disc's node count, on the US.

The measurement behind looper.LOOP_DISC_MAX_NODES (docs/review-fixes-router.md,
"Loops capped by density"). Each run is a cold planner asked what the server
asks for a first loop, `plan` and then `sectors`, from one start at one length,
timed in CPU seconds (this Mac is shared, and contention inflates the wall
clock far more than the CPU time). Beside it, the disc's node count as
`LoopPlanner.max_km` estimates it from the node grid, and as the passes
actually searched.

    SUNDAYDRIVE_PACK=data/pack-us python loop_limit.py data/processed-us \
        --out runs.json [--reps 2] [--km 100 200 300 400]
    python loop_limit.py --report runs.json [--target 8.5]

Starts are fixed places, dense metros and sparse country, so two runs ask
the same questions.
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

STARTS = {
    # Dense: where the old 400 km top was slow.
    "Philadelphia": (39.9526, -75.1652),
    "New York": (40.7484, -73.9857),
    "Washington": (38.9072, -77.0369),
    "Boston": (42.3601, -71.0589),
    "Chicago": (41.8781, -87.6298),
    "Atlanta": (33.7490, -84.3880),
    "Los Angeles": (34.0522, -118.2437),
    "San Francisco": (37.7749, -122.4194),
    "Dallas": (32.7767, -96.7970),
    "Houston": (29.7604, -95.3698),
    "Detroit": (42.3314, -83.0458),
    "Charlotte": (35.2271, -80.8431),
    # Middling.
    "Denver": (39.7392, -104.9903),
    "Des Moines": (41.5868, -93.6250),
    "Asheville": (35.5951, -82.5515),
    "Burlington VT": (44.4759, -73.2121),
    # Sparse.
    "Ely NV": (39.2474, -114.8886),
    "Billings MT": (45.7833, -108.5007),
    "Moab UT": (38.5733, -109.5498),
    "Amarillo TX": (35.2220, -101.8313),
}
SUMMER = date(2026, 7, 1)


def measure(processed, pack, kms, reps, out):
    from looper import LoopPlanner
    from router import Router
    t = time.perf_counter()
    router = Router(processed, pack=pack)
    print(f"loaded in {time.perf_counter() - t:.0f} s", flush=True)
    runs = []
    # Warm the router's own caches (closures by date) once, off the clock.
    LoopPlanner(router).plan(router.snap(*STARTS["Moab UT"])[0], 20.0, on=SUMMER)
    for rep in range(reps):
        for name, (lat, lon) in STARTS.items():
            start, off = router.snap(lat, lon)
            probe = LoopPlanner(router)
            for km in kms:
                planner = LoopPlanner(router)     # cold: a first loop
                c, w = time.process_time(), time.perf_counter()
                loop = planner.plan(start, km, on=SUMMER)
                if loop is not None:
                    planner.sectors(start, loop.target_km, on=SUMMER)
                cpu, wall = time.process_time() - c, time.perf_counter() - w
                fields = next(iter(planner._fields_by_key.values()), None)
                searched = None if fields is None else int(len(fields.nodes))
                est = probe.disc_nodes(start, km)
                runs.append({"rep": rep, "start": name, "km": km, "cpu": cpu,
                             "wall": wall, "nodes_est": est,
                             "nodes_searched": searched,
                             "built": loop is not None,
                             "max_km": probe.max_km(start)})
                print(f"{rep} {name:14s} {km:5.0f} km  cpu {cpu:6.2f} s  wall "
                      f"{wall:6.2f} s  est {est:>9,}  searched {searched or 0:>9,}",
                      flush=True)
                Path(out).write_text(json.dumps(runs))
    return runs


def report(runs, target):
    cpu = np.array([r["cpu"] for r in runs])
    est = np.array([r["nodes_est"] for r in runs], float)
    ok = est > 0
    b, a = np.polyfit(np.log(est[ok]), np.log(cpu[ok]), 1)
    resid = np.log(cpu[ok]) - (a + b * np.log(est[ok]))
    q90 = float(np.quantile(resid, 0.9))
    n_star = math.exp((math.log(target) - a - q90) / b)
    print(f"{len(runs)} runs; cpu ~ {math.exp(a):.3g} * nodes^{b:.2f}; "
          f"p90 residual x{math.exp(q90):.2f}")
    print(f"nodes at which p90 reaches {target} s CPU: {n_star:,.0f}")
    for lo, hi in ((0, 5e5), (5e5, 1e6), (1e6, 1.5e6), (1.5e6, 2e6), (2e6, 2.5e6),
                   (2.5e6, 3e6), (3e6, 4e6), (4e6, 1e9)):
        sel = (est > lo) & (est <= hi)
        if sel.any():
            print(f"  {lo/1e6:4.1f}-{hi/1e6:4.1f} M nodes: n={sel.sum():3d}  "
                  f"p50 {np.median(cpu[sel]):5.2f}  p90 {np.quantile(cpu[sel], 0.9):5.2f}"
                  f"  max {cpu[sel].max():5.2f} s")
    return n_star


def main():
    p = argparse.ArgumentParser()
    p.add_argument("processed", nargs="?")
    p.add_argument("--out")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--km", type=float, nargs="+", default=[100, 200, 300, 400])
    p.add_argument("--report")
    p.add_argument("--target", type=float, default=8.5)
    args = p.parse_args()
    if args.report:
        report(json.loads(Path(args.report).read_text()), args.target)
        return
    runs = measure(args.processed, os.environ.get("SUNDAYDRIVE_PACK"), args.km,
                   args.reps, args.out)
    report(runs, args.target)


if __name__ == "__main__":
    main()
