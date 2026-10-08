"""Prototype: spliced scenic/fastest routes for a time-budget slider.

Read-only against the graph. No server, no port, writes only to the scratchpad.

Families, all built on the pure scenic path P (s -> t at pref p):
  A  scenic P[:k]  + fastest(P[k] -> t)
  B  fastest(s -> P[k]) + scenic P[k:]
  C  fastest(s -> P[i]) + scenic P[i:j] + fastest(P[j] -> t)   (A and B are edge cases)
Sub-paths of a shortest path are shortest, so P[i:j] is the scenic optimum
between its ends; the fastest legs come from one forward and one reverse
pref-0 tree.
"""
import json, sys, time
from datetime import date
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

WT = Path(sys.argv[1])
DATA = sys.argv[2]
OUT = Path(sys.argv[3])
sys.path.insert(0, str(WT / "pipeline"))
import router as RT  # noqa: E402

A_LL = (44.1897, -72.8243)   # Waitsfield village, VT-100
B_LL = (42.2809, -71.2378)   # Needham centre
ON = date(2026, 10, 6)
PREFS = [0.5, 0.75, 1.0]     # slider positions 0.25, 0.56, 1.0
BUDGETS = [5, 10, 15, 20, 30, 45, 60, 75, 90, 120, 150]

t0 = time.time()
R = RT.Router(DATA)
print(f"loaded in {time.time()-t0:.0f}s, n={R.n}", flush=True)

s, s_off = R.snap(*A_LL)
t, t_off = R.snap_destination(*B_LL)
print("snap offsets m:", round(s_off), round(t_off))
targets = R.node_copies.get(t, np.array([t]))
scores = R._edge_scores({})


def pair_weights(w):
    pw = np.full(R.n_pairs, np.inf)
    np.minimum.at(pw, R.slot_pair, w)
    return pw


def hop_slot(a, b, w):
    key = np.int64(int(a) * R.n + int(b))
    p = np.searchsorted(R._pair_key, key)
    assert R._pair_key[p] == key
    slots = R._pair_slots[R._pair_start[p]:R._pair_start[p + 1]]
    return int(slots[np.argmin(w[slots])])


def hop_stats(a, b, w):
    k = hop_slot(a, b, w)
    e = R.eidx[k]
    km = R.km[e]
    return R.d_minutes[k], km, (km if scores[e] >= RT.BEAUTIFUL_SCORE else 0.0)


def path_from_pred(pred, src, dst):
    out, cur = [], dst
    while cur != src and cur >= 0:
        out.append(cur)
        cur = pred[cur]
    if cur < 0:
        return None
    out.append(src)
    return out[::-1]


w0 = R._weights(0.0, scores, 1.0, ON)
pw0 = pair_weights(w0)
g0 = csr_matrix((pw0, (R.u_tail, R.u_head)), shape=(R.n, R.n))
# Forward fastest tree from s, reverse fastest tree into t.
_, pred_f = dijkstra(g0, directed=True, indices=s, return_predecessors=True)
_, pred_r, _src = dijkstra(g0.T.tocsr(), directed=True, indices=targets,
                           return_predecessors=True, min_only=True)

memo_f = {s: (0.0, 0.0, 0.0)}           # node -> (min, km, beautiful km) from s
memo_r = {int(x): (0.0, 0.0, 0.0) for x in targets}   # node -> ... to t


def fast_prefix(v):
    stack, cur = [], v
    while cur not in memo_f:
        stack.append(cur); cur = pred_f[cur]
        if cur < 0:
            return None
    while stack:
        x = stack.pop(); p = pred_f[x]
        m, k, b = hop_stats(p, x, w0); M, K, B = memo_f[p]
        memo_f[x] = (M + m, K + k, B + b)
    return memo_f[v]


def fast_suffix(v):
    stack, cur = [], v
    while cur not in memo_r:
        stack.append(cur); cur = pred_r[cur]
        if cur < 0:
            return None
    while stack:
        x = stack.pop(); nx = pred_r[x]
        m, k, b = hop_stats(x, nx, w0); M, K, B = memo_r[nx]
        memo_r[x] = (M + m, K + k, B + b)
    return memo_r[v]


def fast_suffix_path(v):
    out = [v]
    while out[-1] not in set(targets.tolist()):
        out.append(int(pred_r[out[-1]]))
    return out


def road_at(path, i, w):
    """Name/ref of the edge leaving path[i]."""
    if i >= len(path) - 1:
        return "(arrive)"
    e = R.eidx[hop_slot(path[i], path[i + 1], w)]
    row = R.edges.iloc[e]
    ref = row.get("ref") or ""
    name = row.get("name") or ""
    return " / ".join(x for x in (str(ref), str(name)) if x and x != "None" and x != "nan") or row["highway"]


fastest = R.route(s, t, 0.0, {}, avoid_unpaved=1.0, on=ON)
F_MIN, F_BKM = fastest.minutes, fastest.beautiful_km
print(f"fastest: {F_MIN:.0f} min, {fastest.km:.0f} km, {F_BKM:.1f} beautiful km")

# Today's slider, for comparison: pure routes at 20 handle positions.
sweep = []
for pos in np.linspace(0.05, 1.0, 20):
    r = R.route(s, t, float(np.sqrt(pos)), {}, avoid_unpaved=1.0, on=ON)
    sweep.append((round(pos, 2), round(r.minutes - F_MIN, 1), round((r.beautiful_km - F_BKM) / 1.609, 1)))
    print("today's slider position", sweep[-1], flush=True)

cands = []   # (extra_min, beautiful_km, km, family, pref, i, j)
pure = {}
for pref in PREFS:
    w = R._weights(pref, scores, 1.0, ON)
    pw = pair_weights(w)
    g = csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n))
    dist, pred = dijkstra(g, directed=True, indices=s, return_predecessors=True)
    dst = int(targets[np.argmin(dist[targets])])
    P = path_from_pred(pred, s, dst)
    hs = np.array([hop_stats(P[q], P[q + 1], w) for q in range(len(P) - 1)])
    cm = np.concatenate([[0], np.cumsum(hs[:, 0])])
    ck = np.concatenate([[0], np.cumsum(hs[:, 1])])
    cb = np.concatenate([[0], np.cumsum(hs[:, 2])])
    ref = R.route(s, t, pref, {}, avoid_unpaved=1.0, on=ON)
    pure[pref] = dict(P=P, w=w, minutes=cm[-1], bkm=cb[-1])
    print(f"pref {pref}: scenic {cm[-1]:.0f} min (router says {ref.minutes:.0f}), "
          f"{ck[-1]:.0f} km, {cb[-1]:.1f} beautiful km (router says {ref.beautiful_km:.1f})",
          flush=True)
    # Thin the switch points to every ~0.5 km so C stays tractable.
    keep = [0]
    for q in range(1, len(P)):
        if ck[q] - ck[keep[-1]] >= 0.5:
            keep.append(q)
    if keep[-1] != len(P) - 1:
        keep.append(len(P) - 1)
    keep = np.array(keep)
    FP = np.array([fast_prefix(P[q]) or (np.inf,) * 3 for q in keep])
    FS = np.array([fast_suffix(P[q]) or (np.inf,) * 3 for q in keep])
    I, J = np.triu_indices(len(keep), k=1)
    mins = FP[I, 0] + (cm[keep[J]] - cm[keep[I]]) + FS[J, 0]
    kms = FP[I, 1] + (ck[keep[J]] - ck[keep[I]]) + FS[J, 1]
    bk = FP[I, 2] + (cb[keep[J]] - cb[keep[I]]) + FS[J, 2]
    fam = np.where(I == 0, "A", np.where(J == len(keep) - 1, "B", "C"))
    for a in range(len(I)):
        cands.append((mins[a] - F_MIN, bk[a], kms[a], fam[a], pref, int(keep[I[a]]), int(keep[J[a]])))
    print(f"  {len(keep)} switch points, {len(I)} candidates", flush=True)

cands.sort(key=lambda c: (-c[1], c[0]))


def assemble(c):
    _, _, _, fam, pref, i, j = c
    P = pure[pref]["P"]
    pre = path_from_pred(pred_f, s, P[i])
    suf = fast_suffix_path(P[j])
    full = pre[:-1] + P[i:j] + suf
    real = R.real_node[np.array(full)]
    return full, len(set(real.tolist())) == len(real)


rows = []
for B in BUDGETS:
    best = None
    for c in cands:
        if c[0] > B:
            continue
        full, simple = assemble(c)
        if simple:
            best = (c, full); break
    if best is None:
        continue
    c, full = best
    _, _, _, fam, pref, i, j = c
    P, w = pure[pref]["P"], pure[pref]["w"]
    # Verify by rebuilding a RouteResult from the stitched node path.
    res = R._collect(full, w0, scores)  # w only picks among parallel edges
    leave_on = road_at(P, i, w)
    rejoin = road_at(full, len(path_from_pred(pred_f, s, P[i])) - 1 + (j - i), w0)
    lat_i, lon_i = R.nodes.iloc[R.real_node[P[i]]][["lat", "lon"]]
    lat_j, lon_j = R.nodes.iloc[R.real_node[P[j]]][["lat", "lon"]]
    rows.append(dict(budget=B, extra_min=round(res.minutes - F_MIN, 1),
                     beautiful_km=round(res.beautiful_km, 1),
                     gain_mi=round((res.beautiful_km - F_BKM) / 1.609, 1),
                     km=round(res.km, 0), family=fam, pref=pref,
                     scenic_from=(round(lat_i, 4), round(lon_i, 4)), scenic_on=leave_on,
                     scenic_to=(round(lat_j, 4), round(lon_j, 4)), then=rejoin))
    (OUT / f"budget_{B}.geojson").write_text(json.dumps(res.geojson()))
    print(rows[-1], flush=True)

(OUT / "summary.json").write_text(json.dumps(dict(
    fastest=dict(minutes=F_MIN, km=fastest.km, beautiful_km=F_BKM),
    pure={p: dict(extra=v["minutes"] - F_MIN, bkm=v["bkm"]) for p, v in pure.items()},
    sweep=sweep, options=rows), indent=1, default=str))
print(f"done in {time.time()-t0:.0f}s")
