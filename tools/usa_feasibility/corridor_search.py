"""Scenic (pref 1) search on an ellipse subgraph vs the whole graph.

Ellipse: |s v| + |v t| <= d + X with X = a*d + b km (straight-line, projected).
Checks the corridor answer's cost equals the whole-graph optimum and times both
(subgraph extraction included). Usage:
  python corridor_search.py <pipeline_dir> <processed_dir> <n_pairs> <a> <b>
"""
import sys
import time

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402
from scipy.sparse import csr_matrix  # noqa: E402
from scipy.sparse.csgraph import dijkstra  # noqa: E402
from router import Router  # noqa: E402

R = Router(sys.argv[2])
N, A, B = int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
real = R.real_node.astype(np.int64)
X = np.asarray(R._nx)[real] / 1000.0
Y = np.asarray(R._ny)[real] / 1000.0
scores = R._edge_scores({})
w = R._weights(1.0, scores, 1.0, None)
pw = np.full(R.n_pairs, np.inf)
np.minimum.at(pw, R.slot_pair, w)
G = csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n))
rng = np.random.default_rng(23)
rows = []
while len(rows) < N:
    s, t = (int(v) for v in rng.integers(0, len(R.nodes), 2))
    d = float(np.hypot(X[s] - X[t], Y[s] - Y[t]))
    if not 20 <= d <= 350:
        continue
    targets = R.node_copies.get(t)
    targets = np.array([t]) if targets is None else targets
    c = time.perf_counter
    t0 = c()
    full = dijkstra(G, directed=True, indices=s)
    t1 = c()
    Cfull = float(full[targets].min())
    if not np.isfinite(Cfull):
        continue
    t2 = c()
    lim = d + A * d + B
    m = np.hypot(X - X[s], Y - Y[s]) + np.hypot(X - X[t], Y - Y[t]) <= lim
    sel = np.flatnonzero(m)
    new = np.full(R.n, -1, np.int64)
    new[sel] = np.arange(len(sel))
    pm = m[R.u_tail] & m[R.u_head]
    g = csr_matrix((pw[pm], (new[R.u_tail[pm]], new[R.u_head[pm]])), shape=(len(sel), len(sel)))
    t3 = c()
    sub = dijkstra(g, directed=True, indices=int(new[s]))
    t4 = c()
    tt = new[targets]
    Csub = float(sub[tt[tt >= 0]].min()) if (tt >= 0).any() else np.inf
    rows.append((d, len(sel) / R.n, Csub / Cfull, t1 - t0, t3 - t2, t4 - t3))
    print(f"  {d:5.0f} km: corridor {len(sel)/R.n:6.1%} of graph ({len(sel):,} nodes); cost ratio {Csub/Cfull:.6f}; "
          f"full {1e3*(t1-t0):.0f} ms vs extract {1e3*(t3-t2):.0f} + search {1e3*(t4-t3):.0f} ms", flush=True)
r = np.array(rows)
print(f"exact (ratio 1.000000) on {int((np.abs(r[:, 2] - 1) < 1e-9).sum())} of {len(r)}; worst ratio {r[:, 2].max():.6f}")
print(f"median corridor share {np.median(r[:, 1]):.1%}; median full {1e3*np.median(r[:, 3]):.0f} ms, "
      f"corridor search {1e3*np.median(r[:, 5]):.0f} ms (+ extract {1e3*np.median(r[:, 4]):.0f} ms, O(E) here)")
