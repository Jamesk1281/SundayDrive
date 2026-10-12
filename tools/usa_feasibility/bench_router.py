"""Load the shipped Router on a processed dir and time its searches.

Usage: python bench_router.py <pipeline_dir> <processed_dir> <label> [n_pairs]
Prints a JSON summary line at the end.
"""
import json
import os
import resource
import sys
import time

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402

proc, label = sys.argv[2], sys.argv[3]
n_pairs = int(sys.argv[4]) if len(sys.argv) > 4 else 20


def rss_gb():
    # current RSS via ps (ru_maxrss is the peak)
    return int(os.popen(f"ps -o rss= -p {os.getpid()}").read()) / 1e6


t0 = time.time()
from router import Router  # noqa: E402
import options  # noqa: E402
from looper import LoopPlanner  # noqa: E402
R = Router(proc)
load_s = time.time() - t0
rss_after_load = rss_gb()
peak_load = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9
print(f"[{label}] loaded {len(R.nodes):,} nodes / {R.n:,} slots-indices in {load_s:.1f}s, "
      f"RSS {rss_after_load:.2f} GB, peak {peak_load:.2f} GB", flush=True)

rng = np.random.default_rng(7)
lon = R.nodes["lon"].to_numpy(); lat = R.nodes["lat"].to_numpy()
n = len(lon)


def km_between(i, j):
    p1, p2 = np.radians(lat[i]), np.radians(lat[j])
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon[j] - lon[i]) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


pairs = []
while len(pairs) < n_pairs:
    i, j = rng.integers(0, n, 2)
    d = km_between(i, j)
    if 20 <= d <= 200:
        pairs.append((int(i), int(j), float(d)))

res = {"fast": [], "scenic": [], "plan": [], "plan_phases": [], "loop": []}
for k, (i, j, d) in enumerate(pairs):
    t = time.perf_counter(); f = R.route(i, j, 0.0); res["fast"].append(time.perf_counter() - t)
    t = time.perf_counter(); s = R.route(i, j, 1.0); res["scenic"].append(time.perf_counter() - t)
    timings = {}
    t = time.perf_counter(); p = options.plan(R, i, j, timings=timings); res["plan"].append(time.perf_counter() - t)
    res["plan_phases"].append(timings)
    print(f"  pair {k}: {d:5.0f} km  fast {res['fast'][-1]*1e3:6.0f} ms  scenic {res['scenic'][-1]*1e3:6.0f} ms  "
          f"plan {res['plan'][-1]*1e3:6.0f} ms  ({', '.join(f'{a} {b*1e3:.0f}' for a, b in timings.items())})"
          + (f"  fastest {f.minutes:.0f} min / scenic {s.minutes:.0f} min" if f is not None and s is not None else ""),
          flush=True)

LP = LoopPlanner(R)
for k in range(min(6, n_pairs)):
    start = pairs[k][0]
    t = time.perf_counter(); lp = LP.plan(start, 60.0); res["loop"].append(time.perf_counter() - t)
    print(f"  loop {k}: 60 km from node {start}: {res['loop'][-1]*1e3:.0f} ms"
          + (f" -> {lp.km:.0f} km" if lp is not None else " -> None"), flush=True)

summ = {"label": label, "nodes": len(R.nodes), "indices": int(R.n), "pairs": int(R.n_pairs),
        "load_s": round(load_s, 1), "rss_gb": round(rss_after_load, 2),
        "peak_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2)}
for key in ("fast", "scenic", "plan", "loop"):
    v = np.array(res[key]) * 1e3
    summ[key + "_ms"] = {"median": round(float(np.median(v))), "p90": round(float(np.percentile(v, 90))),
                         "max": round(float(v.max()))}
print(json.dumps(summ))
