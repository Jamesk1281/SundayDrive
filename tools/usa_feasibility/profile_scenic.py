"""Where a scenic request's time goes, and what an exact early-exit search would settle.

Per request the shipped scenic arm does, over the WHOLE graph:
  _edge_scores (matrix-vector over every edge), _weights (every slot),
  np.minimum.at to pairs, csr_matrix build, scipy dijkstra (no early exit).
This times each phase on the loaded graph, then measures the exact alternative:

  UB = scenic cost of the fastest route (any feasible path bounds the optimum)
  dijkstra(..., limit=UB) settles only nodes with d(s, v) <= UB, and since every
  node on the optimal path has d <= C* <= UB, it returns the same route.

Reports the settled share for limit=UB and for limit=C* (the floor for any
unidirectional early-exit search), and a bidirectional estimate.

Usage: python profile_scenic.py <pipeline_dir> <processed_dir> <n_pairs>
"""
import sys
import time

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402
from scipy.sparse import csr_matrix  # noqa: E402
from scipy.sparse.csgraph import dijkstra  # noqa: E402
from router import Router  # noqa: E402

R = Router(sys.argv[2])
N = int(sys.argv[3])
rng = np.random.default_rng(5)
xn, yn = np.asarray(R._nx) / 1000, np.asarray(R._ny) / 1000
ph = {k: [] for k in ("scores", "weights", "pairmin", "csr", "dijkstra_full", "dijkstra_ub", "fast")}
rows = []
while len(rows) < N:
    s, t = (int(v) for v in rng.integers(0, len(R.nodes), 2))
    d = float(np.hypot(xn[s] - xn[t], yn[s] - yn[t]))
    if not 15 <= d <= 300:
        continue
    c = time.perf_counter
    t0 = c(); scores = R._edge_scores({}); t1 = c()
    w = R._weights(1.0, scores, 1.0, None); t2 = c()
    pw = np.full(R.n_pairs, np.inf); np.minimum.at(pw, R.slot_pair, w); t3 = c()
    g = csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n)); t4 = c()
    dist, pred = dijkstra(g, directed=True, indices=s, return_predecessors=True); t5 = c()
    Cstar = float(dist[t])
    if not np.isfinite(Cstar):
        continue
    # UB: scenic cost of the fastest path
    w0 = R._weights(0.0, scores, 1.0, None)
    targets = R.node_copies.get(t)
    targets = np.array([t]) if targets is None else targets
    t6 = c(); fpath = R._cheapest(s, targets, 0.0, w0); t7 = c()
    if fpath is None or len(fpath) < 2:
        continue
    path = np.asarray(fpath, dtype=np.int64)
    Cstar = float(np.min(dist[targets]))
    key = path[:-1] * R.n + path[1:]
    pairs = np.searchsorted(R._pair_key, key)
    UB = float(pw[pairs].sum())
    t8 = c(); dl, pl = dijkstra(g, directed=True, indices=s, limit=UB * (1 + 1e-9), return_predecessors=True); t9 = c()
    same = np.isclose(float(np.min(dl[targets])), Cstar)
    # reverse search from t for a bidirectional estimate
    dr = dijkstra(g.T.tocsr(), directed=True, indices=t)
    fin = np.isfinite(dist)
    rows.append(dict(d=d, Cstar=Cstar, UB=UB, same=bool(same),
                     settled_ub=float((dist <= UB).sum() / fin.sum()),
                     settled_c=float((dist <= Cstar).sum() / fin.sum()),
                     settled_bi=float(((dist <= Cstar / 2).sum() + (dr <= Cstar / 2).sum()) / fin.sum())))
    for k, v in zip(("scores", "weights", "pairmin", "csr", "dijkstra_full", "fast", "dijkstra_ub"),
                    (t1 - t0, t2 - t1, t3 - t2, t4 - t3, t5 - t4, t7 - t6, t9 - t8)):
        ph[k].append(v)
    print(f"  {d:5.0f} km: C*/UB {Cstar / UB:.2f}; settled full-limit-UB {rows[-1]['settled_ub']:.1%}, "
          f"limit-C* {rows[-1]['settled_c']:.1%}, bidir {rows[-1]['settled_bi']:.1%}; "
          f"dijkstra full {1e3*(t5 - t4):.0f} ms vs limit-UB {1e3*(t9 - t8):.0f} ms; same={same}", flush=True)

print("phase medians (ms):", {k: round(1e3 * float(np.median(v)), 1) for k, v in ph.items()})
for k in ("settled_ub", "settled_c", "settled_bi"):
    v = np.array([r[k] for r in rows])
    print(f"{k}: median {np.median(v):.1%}  p90 {np.percentile(v, 90):.1%}  max {v.max():.1%}")
print("all limit-UB routes identical to full:", all(r["same"] for r in rows))
d = np.array([r["d"] for r in rows]); su = np.array([r["settled_ub"] for r in rows])
for lo, hi in ((15, 60), (60, 120), (120, 200), (200, 300)):
    m = (d >= lo) & (d < hi)
    if m.any():
        print(f"  d {lo}-{hi} km (n={m.sum()}): settled with limit=UB median {np.median(su[m]):.1%}  "
              f"≈ {np.median(su[m]) * len(R.nodes):,.0f} nodes")
