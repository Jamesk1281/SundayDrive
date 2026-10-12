"""Export the Router's directed search graph for bench_device_search.swift.

Writes the pair CSR, the per-slot and per-edge inputs of `Router._weights` at
pref 1 with default beauty weights (so Swift recomputes every weight itself, the
way a phone would per request), node positions in km, and test trips with the
whole-graph optimum from scipy to check the Swift answers against.

Usage: python export_search_graph.py <pipeline_dir> <processed_dir> <out.bin> <n_tests>
"""
import struct
import sys

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402
from scipy.sparse import csr_matrix  # noqa: E402
from scipy.sparse.csgraph import dijkstra  # noqa: E402
from router import BETA, UNPAVED_AVOID_MIN_PER_KM, Router  # noqa: E402

R = Router(sys.argv[2])
out, n_tests = sys.argv[3], int(sys.argv[4])
scores = R._edge_scores({})
w = R._weights(1.0, scores, 1.0, None)
# What _weights adds beyond the closed-form part (private-road and closed-road
# costs), carried per slot so Swift reproduces w exactly.
base = R.d_minutes + BETA * (R.km * (1.0 - scores / 10.0))[R.eidx] \
    + UNPAVED_AVOID_MIN_PER_KM * (R.km * R.unpaved_frac)[R.eidx]
extra = np.where(np.isinf(w), np.inf, w - base)
pw = np.full(R.n_pairs, np.inf)
np.minimum.at(pw, R.slot_pair, w)
indptr = R._pair_indptr.astype(np.int64)
G = csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n))
real = R.real_node.astype(np.int64)
x = (np.asarray(R._nx)[real] / 1000).astype(np.float32)
y = (np.asarray(R._ny)[real] / 1000).astype(np.float32)
rng = np.random.default_rng(31)
S, T, D, C = [], [], [], []
while len(S) < n_tests:
    s, t = (int(v) for v in rng.integers(0, len(R.nodes), 2))
    if t in R.node_copies:
        continue
    d = float(np.hypot(x[s] - x[t], y[s] - y[t]))
    if not 15 <= d <= 300:
        continue
    c = float(dijkstra(G, directed=True, indices=s)[t])
    if np.isfinite(c):
        S.append(s); T.append(t); D.append(d); C.append(c)
with open(out, "wb") as f:
    f.write(struct.pack("<5q", R.n, R.n_pairs, len(R.eidx), len(R.km), len(S)))
    for arr, dt in ((indptr, np.int64), (R.u_head, np.int32), (R.slot_pair, np.int32),
                    (R.eidx, np.int32), (R.d_minutes, np.float32), (extra, np.float32),
                    (R.km, np.float32), (R.unpaved_frac, np.float32), (R.base_score, np.float32),
                    (R.score_adj, np.float32), (R.pref_matrix, np.float32), (x, np.float32),
                    (y, np.float32), (np.array(S), np.int32), (np.array(T), np.int32),
                    (np.array(D), np.float32), (np.array(C), np.float64)):
        f.write(np.ascontiguousarray(arr, dtype=dt).tobytes())
print(f"wrote {out}: {R.n:,} nodes, {R.n_pairs:,} pairs, {len(R.eidx):,} slots, "
      f"{R.pref_matrix.shape[1]} beauty columns, {len(S)} trips")
