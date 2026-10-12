"""Time scipy's whole-graph Dijkstra (what the scenic arm runs) at US scale.

Builds K copies of the New England pref-1 graph (real weights, real topology),
links copy c to copy c+1 at 300 random node pairs, and times one Dijkstra from
copy 0. Usage: python bench_us_dijkstra.py <pipeline_dir> <processed_dir> K...
"""
import os
import sys
import time

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402
from scipy.sparse import csr_matrix  # noqa: E402
from scipy.sparse.csgraph import dijkstra  # noqa: E402

from router import Router  # noqa: E402


def rss_gb():
    return int(os.popen(f"ps -o rss= -p {os.getpid()}").read()) / 1e6


R = Router(sys.argv[2])
scores = R._edge_scores({})
w1 = R._weights(1.0, scores, 1.0, None)
pw = np.full(R.n_pairs, np.inf)
np.minimum.at(pw, R.slot_pair, w1)
ok = np.isfinite(pw)
u, v, w = R.u_tail[ok].astype(np.int64), R.u_head[ok].astype(np.int64), pw[ok]
n = R.n
del R
print(f"base graph: {n:,} nodes, {len(u):,} arcs; RSS {rss_gb():.2f} GB", flush=True)
rng = np.random.default_rng(1)

for K in (int(k) for k in sys.argv[3:]):
    uu = np.concatenate([u + c * n for c in range(K)])
    vv = np.concatenate([v + c * n for c in range(K)])
    ww = np.concatenate([w] * K)
    links_a = np.concatenate([rng.integers(0, n, 300) + c * n for c in range(K - 1)] or [np.zeros(0, np.int64)])
    links_b = np.concatenate([rng.integers(0, n, 300) + (c + 1) * n for c in range(K - 1)] or [np.zeros(0, np.int64)])
    uu = np.concatenate([uu, links_a, links_b]); vv = np.concatenate([vv, links_b, links_a])
    ww = np.concatenate([ww, np.full(2 * len(links_a), 30.0)])
    t = time.perf_counter()
    g = csr_matrix((ww, (uu, vv)), shape=(K * n, K * n))
    build = time.perf_counter() - t
    del uu, vv, ww
    times = []
    for src in (12345, 400000):
        t = time.perf_counter()
        dist, pred = dijkstra(g, directed=True, indices=src, return_predecessors=True)
        times.append(time.perf_counter() - t)
        reached = np.isfinite(dist).mean()
        del dist, pred
    print(f"K={K:2d}: {K*n/1e6:5.1f} M nodes, {g.nnz/1e6:5.1f} M arcs; csr build {build:.1f}s; "
          f"dijkstra {', '.join(f'{x:.2f}s' for x in times)} (reached {reached:.1%}); RSS {rss_gb():.2f} GB",
          flush=True)
    del g
