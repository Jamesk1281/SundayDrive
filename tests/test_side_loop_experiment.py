"""The side-loop census's tree accumulation, against a brute-force walk.

Every number in docs/side-loops-verdict.md's census -- a loop's minutes, km,
and km on roads scoring >= 7 -- is summed down a Dijkstra predecessor tree by
pointer jumping in `Loops._accumulate`, a few numpy passes instead of a Python
walk per node. A wrong jump would mis-sum every loop silently, so it is checked
here against walking each node's path back to the source, on random graphs.
"""

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

import side_loop_experiment as sl


def _graph(seed, n=40, m=160):
    rng = np.random.default_rng(seed)
    t, h = rng.integers(0, n, m), rng.integers(0, n, m)
    keep = t != h
    t, h = t[keep], h[keep]
    pairs = np.unique(np.stack([t, h], 1), axis=0)
    t, h = pairs[:, 0], pairs[:, 1]
    w = rng.uniform(0.1, 5.0, len(t))
    return n, t, h, w, rng


def _loops(n, t, h, w, rng):
    lp = sl.Loops.__new__(sl.Loops)
    lp.N = n
    lp.key = t.astype(np.int64) * n + h          # np.unique left it sorted
    lp.val = {"km": rng.uniform(0, 3, len(t)), "minutes": w.copy()}
    lp.G = csr_matrix((w, (t, h)), shape=(n, n))
    return lp


def _walk(lp, pred, src, v, name):
    total, cur, first = 0.0, v, None
    while cur != src:
        p = pred[cur]
        k = np.searchsorted(lp.key, p * lp.N + cur)
        total += lp.val[name][k]
        first, cur = cur, p
    return total, first


def test_accumulated_sums_match_a_walk_back_to_the_source():
    for seed in range(5):
        n, t, h, w, rng = _graph(seed)
        lp = _loops(n, t, h, w, rng)
        ids = np.array([0, 3, 7])
        dist, pred = dijkstra(lp.G, directed=True, indices=ids,
                              return_predecessors=True)
        acc, first = lp._accumulate(dist, pred, ids)
        for r, src in enumerate(ids):
            for v in range(n):
                if v == src or not np.isfinite(dist[r, v]):
                    continue
                for name in lp.val:
                    want, f = _walk(lp, pred[r], src, v, name)
                    assert np.isclose(acc[name][r, v], want), (seed, src, v, name)
                assert first[r, v] == f, (seed, src, v)
        # minutes are the weights here, so the sum is the Dijkstra distance
        reached = np.isfinite(dist) & (pred >= 0)
        assert np.allclose(acc["minutes"][reached], dist[reached])


def test_offset_reads_a_planted_class_effect():
    # nice if score + 2*minor + noise > 5: a minor road is worth two points
    rng = np.random.default_rng(0)
    import pandas as pd
    score = rng.uniform(0, 10, 4000)
    minor = rng.random(4000) < 0.5
    nice = score + 2.0 * minor + rng.logistic(0, 1, 4000) > 5.0
    df = pd.DataFrame(dict(model_score=score, minor=minor,
                           verdict=np.where(nice, "nice", "dull")))
    assert abs(sl.offset(df) - 2.0) < 0.3
