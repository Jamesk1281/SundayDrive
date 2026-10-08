"""Batch: today's slider (exact envelope) vs spliced routes, over sampled trips.

Read-only against the graph; no server; output only to argv[3]. One JSON line
per pair in results.jsonl.

Today's slider: strength s = handle position (PrefSlider: pref = sqrt(pos)).
Route cost is c0 + s*c1, so the set of routes the slider can return is the
lower envelope, found exactly by the usual recursive line-intersection search.

Spliced: fastest(src->P[i]) + P[i:j] + fastest(P[j]->dst) for every envelope
route P, over switch points every ~0.5 km. Pareto frontier on (extra minutes,
beautiful km); frontier points that revisit a junction are dropped and the
frontier recomputed.
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

places = gpd.read_parquet(DATA / "place_points.parquet")
lat = places.geometry.y.to_numpy(); lon = places.geometry.x.to_numpy()
picked, _ = RC.sample_pairs(lat, lon, PER_BAND, seed=20261007)

t0 = time.time()
R = RT.Router(str(DATA))
print(f"loaded {time.time()-t0:.0f}s", flush=True)
scores = R._edge_scores({})
W = {}
TIMES = {}


def weights(s):
    key = round(s, 12)
    if key not in W:
        if len(W) > 6:
            W.pop(next(iter(W)))
        w = R._weights(float(np.sqrt(s)), scores, 1.0, ON)
        pw = np.full(R.n_pairs, np.inf); np.minimum.at(pw, R.slot_pair, w)
        W[key] = (w, csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n)))
    return W[key]


w0, g0 = weights(0.0)
w0 = w0.copy(); g0T = g0.T.tocsr()
w1 = weights(1.0)[0].copy()


def slot(a, b, w):
    key = np.int64(int(a) * R.n + int(b))
    p = np.searchsorted(R._pair_key, key)
    sl = R._pair_slots[R._pair_start[p]:R._pair_start[p + 1]]
    return int(sl[np.argmin(w[sl])])


def hop(a, b, w):
    k = slot(a, b, w); e = R.eidx[k]; km = R.km[e]
    return R.d_minutes[k], km, (km if scores[e] >= BK else 0.0), w0[k], w1[k]


def from_pred(pred, src, dst):
    out, cur = [], dst
    while cur != src and cur >= 0:
        out.append(int(cur)); cur = pred[cur]
    if cur < 0:
        return None
    out.append(int(src)); return out[::-1]


def solve(src, targets, s):
    w, g = weights(s)
    t = time.perf_counter()
    dist, pred = dijkstra(g, directed=True, indices=src, return_predecessors=True)
    TIMES["search"] = time.perf_counter() - t
    dst = int(targets[np.argmin(dist[targets])])
    if not np.isfinite(dist[dst]):
        return None
    P = from_pred(pred, src, dst)
    hs = np.array([hop(P[q], P[q + 1], w) for q in range(len(P) - 1)]).reshape(-1, 5)
    c = np.vstack([np.zeros(5), np.cumsum(hs, axis=0)])
    return dict(P=P, cum=c, minutes=c[-1, 0], km=c[-1, 1], bkm=c[-1, 2],
                c0=c[-1, 3], c1=c[-1, 4] - c[-1, 3])


def envelope(src, targets):
    A, B = solve(src, targets, 0.0), solve(src, targets, 1.0)
    if A is None:
        return None
    verts = {tuple(A["P"]): A, tuple(B["P"]): B}
    stack, solves = [(A, B)], 2
    while stack:
        a, b = stack.pop()
        if a["P"] == b["P"] or a["c0"] >= b["c0"] - 1e-9 or b["c1"] >= a["c1"] - 1e-9:
            continue
        s = (b["c0"] - a["c0"]) / (a["c1"] - b["c1"])
        if not (0 < s < 1):
            continue
        C = solve(src, targets, s); solves += 1
        if C["c0"] + s * C["c1"] >= a["c0"] + s * a["c1"] - 1e-6:
            continue
        verts[tuple(C["P"])] = C
        stack += [(a, C), (C, b)]
    vs = sorted(verts.values(), key=lambda v: -v["c1"])
    # The slider interval each route owns.
    for k, v in enumerate(vs):
        lo = 0.0 if k == 0 else (v["c0"] - vs[k-1]["c0"]) / (vs[k-1]["c1"] - v["c1"])
        hi = 1.0 if k == len(vs) - 1 else (vs[k+1]["c0"] - v["c0"]) / (v["c1"] - vs[k+1]["c1"])
        v["lo"], v["hi"] = lo, hi
    return vs, solves


def run_pair(a, b):
    src, so = R.snap(lat[a], lon[a]); dst, do = R.snap_destination(lat[b], lon[b])
    if max(so, do) > SNAP_MAX_M:
        return dict(status="snap_far")
    if src == dst:
        return dict(status="same_node")
    targets = R.node_copies.get(dst, np.array([dst]))
    F = solve(src, targets, 0.0)
    if F is None:
        return dict(status="no_path")
    Q = solve(src, targets, 0.25)
    S = solve(src, targets, 1.0); t_scenic = TIMES["search"]
    vs = [F, Q, S]
    T_MAX = S["minutes"] - F["minutes"]
    if T_MAX < 1:
        return dict(status="ok", trivial=True)
    tt = time.perf_counter()
    # Fastest trees.
    _, pred_f = dijkstra(g0, directed=True, indices=src, return_predecessors=True)
    _, pred_r, _x = dijkstra(g0T, directed=True, indices=targets,
                             return_predecessors=True, min_only=True)
    tset = set(int(x) for x in targets)
    memo_f = {int(src): (0.0, 0.0, 0.0)}; memo_r = {x: (0.0, 0.0, 0.0) for x in tset}

    def walk(v, pred, memo, forward):
        stack, cur = [], v
        while cur not in memo:
            stack.append(cur); cur = int(pred[cur])
            if cur < 0:
                return (np.inf, np.inf, 0.0)
        while stack:
            x = stack.pop(); p = int(pred[x])
            h = hop(p, x, w0) if forward else hop(x, p, w0)
            M = memo[p]; memo[x] = (M[0] + h[0], M[1] + h[1], M[2] + h[2])
        return memo[v]

    t_trees = time.perf_counter() - tt

    def splice(bases):
        # Fresh memos, so each config pays its own tree walks.
        memo_f.clear(); memo_f[int(src)] = (0.0, 0.0, 0.0)
        memo_r.clear(); memo_r.update({x: (0.0, 0.0, 0.0) for x in tset})
        ext, bkm, meta = [], [], []
        for bi in bases:
            v = vs[bi]
            P, c = v["P"], v["cum"]
            step = max(0.5, c[-1, 1] / 250.0)
            keep = [0]
            for q in range(1, len(P)):
                if c[q, 1] - c[keep[-1], 1] >= step:
                    keep.append(q)
            if keep[-1] != len(P) - 1:
                keep.append(len(P) - 1)
            keep = np.array(keep)
            FP = np.array([walk(P[q], pred_f, memo_f, True) for q in keep])
            FS = np.array([walk(P[q], pred_r, memo_r, False) for q in keep])
            I, J = np.triu_indices(len(keep), k=1)
            ext.append(FP[I, 0] + c[keep[J], 0] - c[keep[I], 0] + FS[J, 0] - F["minutes"])
            bkm.append(FP[I, 2] + c[keep[J], 2] - c[keep[I], 2] + FS[J, 2] - F["bkm"])
            meta.append(np.column_stack([np.full(len(I), bi), keep[I], keep[J]]))
        ext = np.concatenate(ext); bkm = np.concatenate(bkm); meta = np.concatenate(meta)
        ok = np.isfinite(ext) & (ext <= T_MAX + 1e-6)
        ext, bkm, meta = ext[ok], bkm[ok], meta[ok]
        order = np.lexsort((-bkm, ext))
        ext, bkm, meta = ext[order], bkm[order], meta[order]

        def simple(m):
            bi, i, j = (int(x) for x in m); P = vs[bi]["P"]
            pre = from_pred(pred_f, src, P[i]); suf = [P[j]]
            while suf[-1] not in tset:
                suf.append(int(pred_r[suf[-1]]))
            full = pre[:-1] + P[i:j] + suf
            real = R.real_node[np.array(full)]
            return len(np.unique(real)) == len(real)

        bad = np.zeros(len(ext), bool)
        checked = set()

        def frontier():
            b = np.where(bad, -np.inf, bkm)
            prev = np.concatenate([[-np.inf], np.maximum.accumulate(b)[:-1]])
            return np.nonzero(b > prev + 1e-9)[0]

        while True:
            front = frontier()
            todo = [int(k) for k in front if int(k) not in checked]
            if not todo:
                break
            for k in todo:
                checked.add(k)
                if not simple(meta[k]):
                    bad[k] = True
        spliced = [dict(extra=round(float(ext[k]), 1), gain_km=round(float(bkm[k]), 1))
                   for k in front]
        return spliced, int(bad.sum())

    out_cfg = {}
    for name, bases in (("full", [2]), ("full+quarter", [1, 2])):
        t = time.perf_counter()
        sp, rej = splice(bases)
        out_cfg[name] = dict(spliced=sp, rejected=rej, t_splice=round(time.perf_counter() - t, 3))
    return dict(status="ok", trivial=False, t_max=round(T_MAX, 1),
                full_gain_km=round(S["bkm"] - F["bkm"], 1),
                t_scenic_search=round(t_scenic, 3), t_trees=round(t_trees, 3),
                configs=out_cfg)


out = open(OUT / "results.jsonl", "w")
n = 0
for band, plist in picked.items():
    for a, b, gc in plist:
        n += 1; t1 = time.time()
        try:
            r = run_pair(a, b)
        except Exception:
            r = dict(status="error", err=traceback.format_exc()[-400:])
        r.update(pair=n, band=f"{band[0]:g}-{band[1]:g}", gc_km=round(gc, 1),
                 src=(round(float(lat[a]), 4), round(float(lon[a]), 4)),
                 dst=(round(float(lat[b]), 4), round(float(lon[b]), 4)),
                 secs=round(time.time() - t1, 1))
        out.write(json.dumps(r) + "\n"); out.flush()
        print(n, r["band"], r["status"], r.get("t_max"), r["secs"], flush=True)
print(f"done {time.time()-t0:.0f}s")
