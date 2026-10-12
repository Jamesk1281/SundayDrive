"""Single-feature byway AUCs (within trunk-tertiary, length-weighted) and feature coverage, per region."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *
regions = sys.argv[1].split(",")
FEATS = ["score_nobyway"] + [c for c in COMP if c != "c_scenic_tag"] + [
    "relief750", "relief3k", "above3k", "below3k", "relief6k", "z",
    "tree_1k", "grass_1k", "shrub_1k", "bare_1k", "snow_1k", "crop_1k", "built_1k",
    "desert", "grassland", "grand", "prot_landmark", "prot_landmark_near", "prot_gap12", "prot_public"]
rows = []
for r in regions:
    C = load_chunks(r)
    C["score_nobyway"] = composite(raw_shipped(C, drop_byway=True), C.score_adj.to_numpy())
    C["desert"], C["grassland"], C["grand"] = c_desert(C), c_grassland(C), c_grand(C)
    m = C.highway.isin(MAIN).to_numpy(); w = C.length_m.to_numpy()
    for lab in ["byway_osm", "fhwa_sn", "fhwa_hc"]:
        y = C[lab].to_numpy().astype(bool)
        if (y & m).sum() < 20:
            continue
        for f in FEATS:
            if f not in C:
                continue
            x = C[f].fillna(0).to_numpy().astype(float)
            rows.append(dict(region=r, label=lab, feature=f, auc=wauc(x[m], y[m], w[m]),
                             auc_eco=wauc_strat(x[m], y[m], w[m], C.eco.to_numpy()[m]),
                             byway_mean=np.average(x[m & y], weights=w[m & y]),
                             other_mean=np.average(x[m & ~y], weights=w[m & ~y])))
    km = w / 1000
    cov = {f: 100 * km[C[f].fillna(0).to_numpy() >= 0.5].sum() / km.sum() for f in ["desert", "grassland", "grand", "c_relief", "c_forest"] if f in C}
    print(r, "km share with component >= 0.5:", {k: round(v, 1) for k, v in cov.items()},
          " relief3k p99 (all km):", round(wq(C.relief3k.fillna(0).to_numpy(), w, .99)), " p90:", round(wq(C.relief3k.fillna(0).to_numpy(), w, .9)))
D = pd.DataFrame(rows)
pd.set_option("display.width", 250)
for v in ("auc", "auc_eco"):
    print("\n", v, "(within trunk-tertiary%s)" % (" and within EPA L3 ecoregion" if v == "auc_eco" else ""))
    P = D.pivot_table(index="feature", columns=["region", "label"], values=v).reindex(FEATS)
    print(P.round(3).to_string())
D.to_csv(SP / "describe.csv", index=False)
