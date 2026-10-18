"""Shared loading, candidate scores and metrics for the national scoring evaluation.

Nothing here touches pipeline/; score.py is imported only for WEIGHTS, RAW_BASE,
STRETCH, RELIEF_FULL and composite, so every candidate is measured against the
shipped definitions.
"""
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Locations. Nothing is written inside the repo: NS_WORK is a scratch directory outside it
# (the region builds, feature tables, PAD-US and the marks pickle live there, and the marks
# pickle locates the owner's drives, so it must never be committed). SUNDAYDRIVE_MAIN is the
# main checkout, the only place data/ and traces/ exist.
REPO = Path(__file__).resolve().parents[2]
MAIN = Path(os.environ.get("SUNDAYDRIVE_MAIN", REPO))
if "NS_WORK" not in os.environ:
    raise SystemExit("set NS_WORK to a scratch directory outside the repo (see tools/national_scoring/README.md)")
SP = Path(os.environ["NS_WORK"])
sys.path.insert(0, str(REPO / "pipeline"))
import score as S  # noqa: E402

PROC = {
    "ne": MAIN / "data" / "processed-ne",
    "co": Path(os.environ.get("NS_CO_PROCESSED", SP / "co" / "processed")),
    "ut": SP / "ut" / "processed",
}
REG = SP / "reg"
COMP = ["c_curves", "c_water", "c_coast", "c_forest", "c_farm", "c_views", "c_scenic_tag", "c_relief", "c_urban"]
W = {c: S.WEIGHTS[c[2:]] for c in COMP}
MAIN = ["trunk", "primary", "secondary", "tertiary"]
EXTRA = ["terrain", "wc", "relief750", "attrs", "padus",
         "wc_m3", "lc30"]   # the last two: docs/western-landcover-verdict.md (tools/western_landcover)


def _extras(region):
    parts = []
    for name in EXTRA:
        p = REG / region / f"{name}.parquet"
        if p.exists():
            parts.append(pd.read_parquet(p))
    return parts


def served(F):
    """The score the Router serves. A graph built before 2026-08-29 (the deployed New England one)
    folded LEGACY_UNPAVED_ADJ into score_adj and its stored `score`; Router._load_unpaved strips it
    back out at load. Same recovery here, so every New England number is on the served scale."""
    cls = F["highway"].map(S.CLASS_ADJ).fillna(0.0).to_numpy()
    frac = np.clip((F["score_adj"].to_numpy() - cls) / S.LEGACY_UNPAVED_ADJ, 0.0, 1.0)
    F["score_adj"] = F["score_adj"].to_numpy() - S.LEGACY_UNPAVED_ADJ * frac
    F["score"] = composite(raw_shipped(F), F["score_adj"].to_numpy())
    return F


def load_chunks(region):
    cols = ["way_id", "highway", "name", "ref", "length_m", "lon", "lat", "score_adj", "raw", "score"] + COMP
    ch = pd.read_parquet(REG / region / "chunks.parquet", columns=cols)
    if region == "ne":
        ch = served(ch)
    df = pd.concat([ch] + _extras(region), axis=1)
    df["region"] = region
    return df


def load_edges(region, chunks=None):
    """graph_edges' own columns, plus every extra chunk feature averaged exactly as graph.py does."""
    cols = ["name", "ref", "highway", "length_m", "score_adj", "score"] + COMP
    E = pd.read_parquet(PROC[region] / "graph_edges.parquet", columns=cols)
    if region == "ne":
        E = served(E)
    ch = load_chunks(region) if chunks is None else chunks
    m = np.load(REG / region / "edgemap.npz")
    row, idx, piece, n = m["row"], m["idx"], m["piece"].astype(float), int(m["n"])
    assert n == len(E)
    total = np.bincount(row, weights=piece, minlength=n)
    for c in ch.columns:
        if c in E.columns or c in ("way_id", "lon", "lat", "raw", "region"):
            continue
        v = ch[c].to_numpy()
        if v.dtype.kind in "fiub":
            E[c] = np.bincount(row, weights=v.astype(float)[idx] * piece, minlength=n) / total
        else:  # categorical: the chunk under the edge's middle sample
            start = np.r_[0, np.cumsum(np.bincount(row, minlength=n))[:-1]]
            cnt = np.bincount(row, minlength=n)
            E[c] = v[idx[start + cnt // 2]]
    for c in ("lon", "lat"):
        E[c] = np.bincount(row, weights=ch[c].to_numpy()[idx] * piece, minlength=n) / total
    E["region"] = region
    return E


# ---------------------------------------------------------------- weighted stats
def wq(x, w, q):
    o = np.argsort(x, kind="mergesort")
    cw = np.cumsum(w[o]) / w.sum()
    return np.interp(q, cw, x[o])


def wauc(score, label, weight):
    """Length-weighted AUC with ties at half, as byway_auc.py computes it."""
    score = np.asarray(score, float); label = np.asarray(label, bool); weight = np.asarray(weight, float)
    o = np.argsort(score, kind="mergesort"); s, l, w = score[o], label[o], weight[o]
    pos_w = w * l; neg_w = w * (~l)
    _, start = np.unique(s, return_index=True)
    cum_neg = np.cumsum(neg_w); neg_before = np.r_[0, cum_neg][start]
    grp = np.repeat(np.arange(len(start)), np.diff(np.r_[start, len(s)]))
    neg_in = np.bincount(grp, weights=neg_w); pos_in = np.bincount(grp, weights=pos_w)
    return float(((neg_before + 0.5 * neg_in) * pos_in).sum() / (pos_w.sum() * neg_w.sum()))


def auc(y, s):
    y = np.asarray(y, bool); s = np.asarray(s, float)
    a, b = s[y], s[~y]
    if len(a) == 0 or len(b) == 0:
        return np.nan
    return ((a[:, None] > b[None]).sum() + 0.5 * (a[:, None] == b[None]).sum()) / (len(a) * len(b))


def ceiling(n1, n0, z=1.645):
    return 0.5 + z * np.sqrt((n1 + n0 + 1) / (12 * n1 * n0))


# ---------------------------------------------------------------- new components
def c_desert(F):
    """Arid open land, rock and alpine: WorldCover shrub + bare + moss/lichen + snow within ~1 km.
    ~0 everywhere in New England (shrub, bare, moss, snow all round to 0.000 there)."""
    return np.clip(F["shrub_1k"] + F["bare_1k"] + F["moss_1k"] + F["snow_1k"], 0, 1)


def c_grassland(F):
    """Open grassland within ~1 km, net of anything built. Prairie in the plains; hay, pasture and lawn in New England."""
    return np.clip(F["grass_1k"] * (1 - F["built_1k"]), 0, 1)


# Mountain- and canyon-scale terrain, from the 3 km range. Starts where New England
# runs out of hills and is full at the scale of a Colorado valley wall. Constants are
# set from the terrain, not from the marks: G0 is just above New England's 95th
# percentile road (293 m), G1 a hand choice near Colorado's deepest byway valleys
# (its byway km reach 979 m at p99). The verdict's section 5 sweeps both.
G0, G1 = 300.0, 900.0


def c_grand(F):
    return np.clip((F["relief3k"].fillna(0) - G0) / (G1 - G0), 0, 1)


def c_protected(F):
    return F["prot_core"].to_numpy().astype(float) if "prot_core" in F else np.zeros(len(F))


# ---------------------------------------------------------------- candidate scores
def raw_shipped(F, drop_byway=False):
    r = sum(W[c] * F[c].to_numpy() for c in COMP)
    if drop_byway:
        r = r - W["c_scenic_tag"] * F["c_scenic_tag"].to_numpy()
    return r


def composite(raw, adj, base=S.RAW_BASE, stretch=S.STRETCH):
    return 10.0 * np.clip((raw + base) * stretch + adj, 0.0, 1.0)


def fit_affine(raw, adj, w, target_p50, target_p99):
    """RAW_BASE, STRETCH for one region so its length-weighted p50 and p99 land on New England's."""
    from scipy.optimize import least_squares
    def f(p):
        s = composite(raw, adj, p[0], p[1])
        a = wq(s, w, np.array([.5, .99]))
        return [a[0] - target_p50, a[1] - target_p99]
    r = least_squares(f, [S.RAW_BASE, S.STRETCH], bounds=([-0.5, 0.3], [1.0, 5.0]))
    return float(r.x[0]), float(r.x[1])


def quantile_map(src_scores, src_w, ref_scores, ref_w):
    """Monotone map sending a region's length-weighted score distribution onto the reference's."""
    qs = np.linspace(0, 1, 2001)
    sq = wq(np.asarray(src_scores, float), np.asarray(src_w, float), qs)
    rq = wq(np.asarray(ref_scores, float), np.asarray(ref_w, float), qs)
    sq, keep = np.unique(sq, return_index=True)
    return lambda x: np.interp(x, sq, rq[keep])


def wauc_strat(score, label, weight, strata):
    """Length-weighted AUC over pairs drawn within the same stratum only."""
    score = np.asarray(score, float); label = np.asarray(label, bool)
    weight = np.asarray(weight, float); strata = np.asarray(strata)
    num = den = 0.0
    for k in np.unique(strata):
        m = strata == k
        if label[m].sum() == 0 or (~label[m]).sum() == 0:
            continue
        a = wauc(score[m], label[m], weight[m])
        d = weight[m & label].sum() * weight[m & ~label].sum()
        num += a * d; den += d
    return num / den if den else np.nan


# ---------------------------------------------------------------- marks
def load_marks():
    D = pd.read_pickle(SP / "marks.pkl")
    D = D[(D.window == 400) & (D.reaction == 3)].reset_index(drop=True)
    D["batch"] = np.where(D.drive.str.contains("2026-08"), "Aug", "Oct")
    D["y"] = D.verdict == "nice"
    return D


def mark_values(D, edge_values):
    """Per-mark mean of an edge-level array over the mark's sampled edges (distance-weighted, as before)."""
    v = np.asarray(edge_values, float)
    return np.array([v[ids].mean() for ids in D.edge_ids])


def mark_report(D, s):
    """The four numbers the brief asks for, from per-mark scores s."""
    y = D.y.to_numpy(); o = (D.batch == "Oct").to_numpy()
    hi = s >= 7; band = (s >= 3) & (s < 7)
    return dict(all=auc(y, s), oct=auc(y[o], s[o]), aug=auc(y[~o], s[~o]),
                prec7=y[hi].mean() if hi.any() else np.nan, n7=int(hi.sum()),
                band37=auc(y[band], s[band]), nband=int(band.sum()))
