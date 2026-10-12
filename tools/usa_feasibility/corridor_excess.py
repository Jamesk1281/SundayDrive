"""How far outside the straight line do the shipped scenic routes go?

For random OD pairs, runs the shipped Router at pref 1 (the options base S)
and pref 0.5, and records the route's ellipse excess:

    excess = max over route nodes v of (|s v| + |v t|) - |s t|      (km, straight-line)

A search restricted to the ellipse {v : |s v| + |v t| <= |s t| + X} returns
exactly the full-graph route whenever X >= excess (the route is feasible in
the restriction, and the restriction can only remove alternatives). So the
distribution of `excess` IS the corridor-size requirement, measured.

Also reports how many graph nodes such an ellipse holds, as a share of the
graph, for X = the p95 / p99 / max excess.

Usage: python corridor_excess.py <pipeline_dir> <processed_dir> <label> <n_pairs> [dmin dmax]
"""
import json
import sys
import time

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402
from router import Router  # noqa: E402

proc, label, N = sys.argv[2], sys.argv[3], int(sys.argv[4])
dmin = float(sys.argv[5]) if len(sys.argv) > 5 else 10.0
dmax = float(sys.argv[6]) if len(sys.argv) > 6 else 300.0
R = Router(proc)
real = R.real_node.astype(np.int64)
x = np.asarray(R._nx)[real] / 1000.0   # km, projected
y = np.asarray(R._ny)[real] / 1000.0
xn, yn = np.asarray(R._nx) / 1000.0, np.asarray(R._ny) / 1000.0
n_real = len(xn)
rng = np.random.default_rng(11)
rows = []
t0 = time.time()
while len(rows) < N:
    i, j = (int(v) for v in rng.integers(0, len(R.nodes), 2))
    d = float(np.hypot(xn[i] - xn[j], yn[i] - yn[j]))
    if not dmin <= d <= dmax:
        continue
    rec = {"d_km": round(d, 1)}
    for pref in (1.0, 0.5, 0.0):
        r = R.route(i, j, pref)
        if r is None:
            rec = None
            break
        coords = np.asarray(r.line.coords) if hasattr(r, "line") else None
        # use the route's own geometry (every vertex), projected
        from router import _TO_M
        lon, lat = np.asarray(r.line.coords).T
        px, py = _TO_M.transform(lon, lat)
        px, py = np.asarray(px) / 1000, np.asarray(py) / 1000
        e = np.hypot(px - xn[i], py - yn[i]) + np.hypot(px - xn[j], py - yn[j]) - d
        rec[f"excess_{pref}"] = round(float(e.max()), 2)
        rec[f"km_{pref}"] = round(float(r.km), 1)
        rec[f"min_{pref}"] = round(float(r.minutes), 1)
    if rec is None:
        continue
    rows.append(rec)
print(f"{len(rows)} pairs in {time.time() - t0:.0f}s", flush=True)

d = np.array([r["d_km"] for r in rows])
for pref in (1.0, 0.5, 0.0):
    ex = np.array([r[f"excess_{pref}"] for r in rows])
    rel = ex / d
    print(f"pref {pref}: excess km p50 {np.median(ex):.1f}  p90 {np.percentile(ex, 90):.1f}  "
          f"p95 {np.percentile(ex, 95):.1f}  p99 {np.percentile(ex, 99):.1f}  max {ex.max():.1f}  | "
          f"excess/d p50 {np.median(rel):.2f} p90 {np.percentile(rel, 90):.2f} p99 {np.percentile(rel, 99):.2f} max {rel.max():.2f}")
# by distance band, pref 1
for lo, hi in ((10, 50), (50, 100), (100, 200), (200, 400)):
    m = (d >= lo) & (d < hi)
    if m.sum() == 0:
        continue
    ex = np.array([r["excess_1.0"] for r in rows])[m]
    print(f"  d {lo:3d}-{hi:3d} km (n={m.sum():3d}): pref-1 excess p50 {np.median(ex):5.1f}  p90 {np.percentile(ex, 90):5.1f}  "
          f"max {ex.max():5.1f} km;  ratio scenic/fastest km p50 "
          f"{np.median(np.array([r['km_1.0'] / r['km_0.0'] for r in rows])[m]):.2f}")
json.dump(rows, open(f"corridor_{label}.json", "w"))
