"""Breakdowns behind docs/western-landcover-verdict.md: per-ecoregion byway separation, what
WorldCover's grassland is in New England, and the open-land classes on the marks. Aggregates only.

Usage: breakdowns.py <out_dir>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "national_scoring")); sys.path.insert(0, str(HERE))
from core import *  # noqa
import evaluate_lib as EV

OUT = Path(sys.argv[1])
chunks, edges, D, S = EV.chunks, EV.edges, EV.D, EV.S
pd.set_option("display.width", 250)
lines = []


def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); lines.append(s)


# 1. FHWA scenic/natural within each ecoregion, per candidate (the within-ecoregion figure is the
#    pair-weighted mean of these)
rows = []
for r in ("co", "ut"):
    C = chunks[r]; m = C.highway.isin(MAIN).to_numpy(); w = C.length_m.to_numpy(); eco = C.eco.to_numpy()
    for lab in ("fhwa_sn", "byway_osm"):
        yb = C[lab].to_numpy().astype(bool)
        for g in np.unique(eco[m]):
            k = m & (eco == g)
            if (yb & k).sum() < 20 or w[yb & k].sum() < 20e3:
                continue
            row = dict(region=r, label=lab, eco=g, byway_km=w[yb & k].sum() / 1000, other_km=w[~yb & k].sum() / 1000)
            for name in ("W0", "N1r", "L1", "R1", "R2"):
                row[name] = wauc(S[name][r]["chunk_nb"][k], yb[k], w[k])
            rows.append(row)
T = pd.DataFrame(rows)
T.to_csv(OUT / "byway_by_ecoregion.csv", index=False)
say("1. BYWAY AUC WITHIN EACH ECOREGION (trunk-tertiary, byway term removed; ecoregions with >= 20 byway km)")
say(T.round(3).to_string(index=False))

# 2. What WorldCover's grassland is in New England: other sources' content where grass_1k >= 0.5
C = chunks["ne"]; w = C.length_m.to_numpy(); g = C.grass_1k.to_numpy() >= .5
say(f"\n2. NEW ENGLAND km with WorldCover grass_1k >= 0.5: {w[g].sum() / 1000:,.0f} km")
say(pd.Series({k: np.average(C[k].to_numpy()[g], weights=w[g]) for k in
               ("nlcd_grass", "nlcd_pasture", "nlcd_crop", "nlcd_desert", "lf_grass", "lf_desert", "built_1k", "tree_1k")}).round(3).to_string())

# 3. The open-land classes on the 151 marks (per-mark mean over the mark's edges)
y = D.y.to_numpy(); o = (D.batch == "Oct").to_numpy(); E = edges["ne"]
rows = {}
for k in ("grass_1k", "crop_1k", "nlcd_grass", "nlcd_pasture", "nlcd_crop", "nlcd_desert", "lf_desert", "lf_grass"):
    v = mark_values(D, E[k].to_numpy())
    rows[k] = dict(all=auc(y, v), oct=auc(y[o], v[o]), aug=auc(y[~o], v[~o]),
                   marks_nonzero=int((v > 0.001).sum()))
say("\n3. OPEN-LAND FRACTIONS ON THE 151 NEW ENGLAND MARKS (AUC; marks_nonzero = marks where it is > 0.001)")
say(pd.DataFrame(rows).T.round(3).to_string())

# 4. Where the candidates move Colorado and Utah: km moved > 0.25 against E1, by landscape
rows = []
for r in ("co", "ut"):
    C = chunks[r]; w = C.length_m.to_numpy(); grp = C.eco.map(EV.GROUPS).fillna("other").to_numpy()
    for name in ("N1", "N1r", "L1", "R1", "R2"):
        d = S[name][r]["chunk"] - S["W0"][r]["chunk"]
        for G in ["ALL"] + sorted(set(grp)):
            m = np.ones(len(C), bool) if G == "ALL" else grp == G
            if w[m].sum() < 1000e3:
                continue
            rows.append(dict(region=r, name=name, group=G, up_025=100 * w[m & (d > .25)].sum() / w[m].sum(),
                             down_025=100 * w[m & (d < -.25)].sum() / w[m].sum(), mean_shift=np.average(d[m], weights=w[m])))
T4 = pd.DataFrame(rows)
T4.to_csv(OUT / "western_movement.csv", index=False)
say("\n4. WESTERN km MOVED > 0.25 AGAINST E1 (% of the landscape's km), and mean shift")
say(T4.round(2).to_string(index=False))
(OUT / "breakdowns.txt").write_text("\n".join(lines) + "\n")
