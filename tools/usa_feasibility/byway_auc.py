"""Does the scenery score (minus its own byway term) pick out designated byways?

Length-weighted AUC: the probability that a random km of designated byway scores
above a random km of other road, within the same road classes.
"""
import sys
sys.path.insert(0, sys.argv[1])
import numpy as np, pandas as pd
from score import WEIGHTS, composite
def auc(score, label, weight):
    o = np.argsort(score, kind="mergesort"); s, l, w = score[o], label[o], weight[o]
    pos_w = w * l; neg_w = w * (~l)
    # ties: average rank by grouping equal scores
    _, start = np.unique(s, return_index=True)
    cum_neg = np.cumsum(neg_w); neg_before = np.r_[0, cum_neg][start]
    grp = np.repeat(np.arange(len(start)), np.diff(np.r_[start, len(s)]))
    neg_in_grp = np.bincount(grp, weights=neg_w)
    pos_in_grp = np.bincount(grp, weights=pos_w)
    return float(((neg_before + 0.5 * neg_in_grp) * pos_in_grp).sum() / (pos_w.sum() * neg_w.sum()))
for label, path, ids in [("New England", sys.argv[2], None), ("Colorado", sys.argv[3], sys.argv[4])]:
    c = pd.read_parquet(path, columns=["way_id", "highway", "scenic", "length_m", "raw", "score_adj", "c_scenic_tag",
                                         "c_relief", "c_forest", "c_water", "c_curves", "score"])
    if ids:
        byw = set(int(x) for x in open(ids).read().split())
        lab = c["way_id"].isin(byw).to_numpy()
    else:
        lab = c["scenic"].to_numpy().astype(bool)
    s_wo = composite(c["raw"].to_numpy() - WEIGHTS["scenic_tag"] * c["c_scenic_tag"].to_numpy(), c["score_adj"].to_numpy())
    w = c["length_m"].to_numpy()
    cls = c["highway"].isin(["trunk", "primary", "secondary", "tertiary"]).to_numpy()
    km_b = w[lab].sum() / 1000
    print(f"{label}: {km_b:,.0f} km of byway chunks ({100*w[lab].sum()/w.sum():.1f}% of km)")
    print(f"   AUC all roads {auc(s_wo, lab, w):.3f};  within trunk/primary/secondary/tertiary {auc(s_wo[cls], lab[cls], w[cls]):.3f}")
    for comp in ("c_relief", "c_forest", "c_water", "c_curves"):
        print(f"      {comp}: AUC within classes {auc(c[comp].to_numpy()[cls], lab[cls], w[cls]):.3f}")
    print(f"   share of byway km scoring >= 7 (without byway term): {100*w[lab & (s_wo >= 7)].sum()/w[lab].sum():.1f}%;"
          f" of other km: {100*w[~lab & (s_wo >= 7)].sum()/w[~lab].sum():.1f}%")
    sat = c["c_relief"].to_numpy() >= 0.999
    print(f"   relief saturated (>= RELIEF_FULL): {100*w[sat].sum()/w.sum():.1f}% of all km, {100*w[lab & sat].sum()/w[lab].sum():.1f}% of byway km")
