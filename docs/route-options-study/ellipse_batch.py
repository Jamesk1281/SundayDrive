"""Detour-limit ("ellipse") options over the same 60 sampled trips as batch60.

Read-only against the graph; no server; output only to argv[3].

Per trip: forward fastest tree df from src, reverse fastest tree db into dst,
slack(v) = df[v] + db[v] - F. For each budget B (fraction of the full scenic
detour T), the pref-1 scenic search runs on the subgraph of nodes with
slack <= B'. B' starts at B and is tightened (twice at most) when the route
comes back more than 10% over B. Every result is kept as a candidate.

Timing is reported against a plain full-graph scenic search timed in the same
loop, because other sessions are loading this machine.
"""
import json, sys, time, traceback
from datetime import date
from pathlib import Path

import numpy as np
import geopandas as gpd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

WT = Path(sys.argv[1]); DATA = Path(sys.argv[2]); OUT = Path(sys.argv[3])
PER_BAND = int(sys.argv[4]) if len(sys.argv) > 4 else 12
sys.path.insert(0, str(WT / "pipeline")); sys.path.insert(0, str(WT / "tools"))
import router as RT  # noqa
import route_census as RC  # noqa

ON = date(2026, 10, 6)
SNAP_MAX_M = 5000.0
RC.BANDS = [(10.0, 25.0), (25.0, 50.0), (50.0, 100.0), (100.0, 200.0), (200.0, 350.0)]
BK = RT.BEAUTIFUL_SCORE
FRACS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

places = gpd.read_parquet(DATA / "place_points.parquet")
lat = places.geometry.y.to_numpy(); lon = places.geometry.x.to_numpy()
picked, _ = RC.sample_pairs(lat, lon, PER_BAND, seed=20261007)

R = RT.Router(str(DATA))
scores = R._edge_scores({})


def pairw(w):
    pw = np.full(R.n_pairs, np.inf); np.minimum.at(pw, R.slot_pair, w)
    return pw


w0 = R._weights(0.0, scores, 1.0, ON); pw0 = pairw(w0)
w1 = R._weights(1.0, scores, 1.0, ON); pw1 = pairw(w1)
fin0 = np.isfinite(pw0); fin1 = np.isfinite(pw1)
g0 = csr_matrix((pw0[fin0], (R.u_tail[fin0], R.u_head[fin0])), shape=(R.n, R.n))
g0T = g0.T.tocsr()
g1 = csr_matrix((pw1[fin1], (R.u_tail[fin1], R.u_head[fin1])), shape=(R.n, R.n))
U1, V1, P1 = R.u_tail[fin1], R.u_head[fin1], pw1[fin1]


def slot(a, b, w):
    key = np.int64(int(a) * R.n + int(b))
    p = np.searchsorted(R._pair_key, key)
    sl = R._pair_slots[R._pair_start[p]:R._pair_start[p + 1]]
    return int(sl[np.argmin(w[sl])])


def stats(P, w):
    m = k = b = 0.0
    for q in range(len(P) - 1):
        s = slot(P[q], P[q + 1], w); e = R.eidx[s]; km = R.km[e]
        m += R.d_minutes[s]; k += km; b += km if scores[e] >= BK else 0.0
    return m, k, b


def path(pred, src, dst):
    out, cur = [], dst
    while cur != src and cur >= 0:
        out.append(int(cur)); cur = pred[cur]
    if cur < 0:
        return None
    out.append(int(src)); return out[::-1]


def search(g, src, targets):
    dist, pred = dijkstra(g, directed=True, indices=src, return_predecessors=True)
    dst = int(targets[np.argmin(dist[targets])])
    if not np.isfinite(dist[dst]):
        return None
    return path(pred, src, dst)


def run_pair(a, b):
    src, so = R.snap(lat[a], lon[a]); dst, do = R.snap_destination(lat[b], lon[b])
    if max(so, do) > SNAP_MAX_M:
        return dict(status="snap_far")
    if src == dst:
        return dict(status="same_node")
    targets = R.node_copies.get(dst, np.array([dst]))

    t = time.perf_counter()
    Pf = search(g0, src, targets)
    if Pf is None:
        return dict(status="no_path")
    t_fast_search = time.perf_counter() - t
    Fm, Fk, Fb = stats(Pf, w0)

    t = time.perf_counter()
    Ps = search(g1, src, targets)
    t_scenic_search = time.perf_counter() - t
    Sm, Sk, Sb = stats(Ps, w1)
    T, G = Sm - Fm, Sb - Fb

    t = time.perf_counter()
    df = dijkstra(g0, directed=True, indices=src)
    db = dijkstra(g0T, directed=True, indices=targets, min_only=True)
    F = df[targets].min()
    slack = df + db - F
    t_trees = time.perf_counter() - t

    opts, t_opts, n_search = [], 0.0, 0
    if T >= 1:
        for frac in FRACS:
            B = frac * T; lim = B; res = None
            for attempt in range(3):
                t = time.perf_counter()
                ok = slack <= lim
                sel = ok[U1] & ok[V1]
                g = csr_matrix((P1[sel], (U1[sel], V1[sel])), shape=(R.n, R.n))
                P = search(g, src, targets)
                t_opts += time.perf_counter() - t; n_search += 1
                if P is None:
                    break
                m, k, bk = stats(P, w1)
                res = dict(frac=frac, attempt=attempt, extra=round(m - Fm, 1),
                           gain_km=round(bk - Fb, 1), allowed_share=round(float(ok.mean()), 4))
                if m - Fm <= 1.1 * B:
                    break
                lim *= B / max(m - Fm, 1e-9)
            if res is not None:
                res["over"] = bool(res["extra"] > 1.1 * B)
                opts.append(res)
    return dict(status="ok", t_max=round(T, 1), full_gain_km=round(G, 1),
                fast_min=round(Fm, 1), options=opts, n_search=n_search,
                t_fast_search=round(t_fast_search, 3), t_scenic_search=round(t_scenic_search, 3),
                t_trees=round(t_trees, 3), t_opts=round(t_opts, 3))


out = open(OUT / "results.jsonl", "w"); n = 0; t0 = time.time()
for band, plist in picked.items():
    for a, b, gc in plist:
        n += 1; t1 = time.time()
        try:
            r = run_pair(a, b)
        except Exception:
            r = dict(status="error", err=traceback.format_exc()[-400:])
        r.update(pair=n, band=f"{band[0]:g}-{band[1]:g}", gc_km=round(gc, 1),
                 secs=round(time.time() - t1, 1))
        out.write(json.dumps(r) + "\n"); out.flush()
        print(n, r["band"], r["status"], r.get("t_max"), len(r.get("options", [])), r["secs"], flush=True)
print(f"done {time.time()-t0:.0f}s")
