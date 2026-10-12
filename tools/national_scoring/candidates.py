"""Every candidate score, on chunks and edges, for every region.

build(regions) -> {cand: {region: {"chunk": s, "chunk_nb": s_without_byway_term, "edge": s}}}

No constant below is fitted to the marks. Region-level calibrations (A, C) are fitted to
each region's own score distribution, the way the shipped RAW_BASE/STRETCH were. The
learned candidate (D) is fitted to byway labels only; the marks never enter.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *  # noqa

W_GRAND = 0.10      # mountain/canyon-scale terrain, added on top of relief's 0.16
W_PROT = 0.07       # landmark designation: the same weight as the byway tag, the other designation term
NE_RELIEF_CAP_SHARE = None  # filled from New England: share of km at relief >= RELIEF_FULL


def _cols(F, *, relief_full=None, land=None, grand=False, prot=False, drop_byway=False):
    """Weighted component sum with optional substitutions. Returns raw (pre-composite)."""
    c = {k: F[k].to_numpy().astype(float) for k in COMP}
    if relief_full is not None:
        c["c_relief"] = np.clip(F["relief750"].to_numpy() / relief_full, 0, 1)
    if land == "desert":
        c["c_forest"] = np.maximum(c["c_forest"], c_desert(F).to_numpy())
    elif land == "open":
        c["c_forest"] = np.maximum(c["c_forest"], np.maximum(c_desert(F).to_numpy(), c_grassland(F).to_numpy()))
    raw = sum(W[k] * c[k] for k in COMP)
    if grand:
        raw = raw + W_GRAND * c_grand(F).to_numpy()
    if prot:
        raw = raw + W_PROT * c_protected(F).astype(float)
    if drop_byway:
        raw = raw - W["c_scenic_tag"] * c["c_scenic_tag"]
    return raw


SPEC = {
    # name: (component options, calibration)
    "S0 shipped": (dict(), None),
    "A1 recal per state": (dict(), "affine"),
    "A2 relief cap + recal per state": (dict(relief_full="region"), "affine"),
    "B1 +terrain": (dict(grand=True), None),
    "B2 +desert": (dict(land="desert"), None),
    "B3 +desert+grass": (dict(land="open"), None),
    "B4 +protected": (dict(prot=True), None),
    "E1 terrain+desert+protected": (dict(grand=True, land="desert", prot=True), None),
    "E1g E1 with grass": (dict(grand=True, land="open", prot=True), None),
    "C1 percentile per state": (dict(), "qmap_state"),
    "C2 percentile per ecoregion": (dict(), "qmap_eco"),
    "E2 E1 + percentile per state": (dict(grand=True, land="desert", prot=True), "qmap_state"),
    "E3 A2 + desert + protected": (dict(relief_full="region", land="desert", prot=True), "affine"),
}


def relief_cap_share(F, full=S.RELIEF_FULL):
    w = F.length_m.to_numpy()
    return w[F.relief750.to_numpy() >= full].sum() / w.sum()


def relief_full_for(F, share):
    """RELIEF_FULL that pins the same share of this region's km as New England's 100 m does there."""
    return float(wq(F.relief750.to_numpy(), F.length_m.to_numpy(), 1 - share))


def build(regions, chunks, edges, specs=SPEC):
    ne_share = relief_cap_share(chunks["ne"])
    ne_s = chunks["ne"].score.to_numpy(); ne_w = chunks["ne"].length_m.to_numpy()
    ne_p50, ne_p99 = wq(ne_s, ne_w, np.array([.5, .99]))
    out, info = {}, {}
    for name, (opt, cal) in specs.items():
        out[name] = {}
        for r in regions:
            C, E = chunks[r], edges[r]
            o = dict(opt)
            if o.get("relief_full") == "region":
                o["relief_full"] = S.RELIEF_FULL if r == "ne" else relief_full_for(C, ne_share)
                info[(name, r, "RELIEF_FULL")] = o["relief_full"]
            rc, rcnb, re = _cols(C, **o), _cols(C, **o, drop_byway=True), _cols(E, **o)
            ac, ae = C.score_adj.to_numpy(), E.score_adj.to_numpy()
            if cal == "affine" and r != "ne":
                base, st = fit_affine(rc, ac, C.length_m.to_numpy(), ne_p50, ne_p99)
                info[(name, r, "RAW_BASE,STRETCH")] = (round(base, 4), round(st, 4))
            else:
                base, st = S.RAW_BASE, S.STRETCH
            sc, scnb, se = composite(rc, ac, base, st), composite(rcnb, ac, base, st), composite(re, ae, base, st)
            if cal in ("qmap_state", "qmap_eco"):
                key = "state" if cal == "qmap_state" else "eco"
                # New England counts as one state here: it already shares one calibration.
                gc = np.full(len(C), r) if (key == "state") else C[key].to_numpy()
                ge = np.full(len(E), r) if (key == "state") else E[key].to_numpy()
                sc2, scnb2, se2 = sc.copy(), scnb.copy(), se.copy()
                w = C.length_m.to_numpy()
                for g in np.unique(gc):
                    m = gc == g
                    if w[m].sum() < 2000e3:   # ecoregion slivers under 2,000 km keep the absolute score
                        continue
                    f = quantile_map(sc[m], w[m], ne_s, ne_w)
                    fnb = quantile_map(scnb[m], w[m], ne_s, ne_w)
                    sc2[m], scnb2[m] = f(sc[m]), fnb(scnb[m])
                    me = ge == g
                    se2[me] = f(se[me])
                sc, scnb, se = sc2, scnb2, se2
            out[name][r] = dict(chunk=sc, chunk_nb=scnb, edge=se)
    return out, info
