"""Check, not fit: single-feature separation of the NE marks for the candidate features."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *
E = load_edges("ne")
D = load_marks()
s = mark_values(D, E.score)
print("reproduction:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in mark_report(D, s).items()})
y = D.y.to_numpy(); o = (D.batch == "Oct").to_numpy()
print(f"nulls: all {ceiling(y.sum(), (~y).sum()):.3f}  Oct {ceiling(y[o].sum(), (~y[o]).sum()):.3f}  Aug {ceiling(y[~o].sum(), (~y[~o]).sum()):.3f}")
E["grand"] = c_grand(E); E["grassland"] = c_grassland(E); E["desert"] = c_desert(E)
for f in ["c_relief", "relief750", "relief3k", "above3k", "below3k", "relief6k", "z", "tree_1k", "grass_1k", "grassland",
          "crop_1k", "built_1k", "desert", "grand", "prot_landmark", "prot_landmark_near", "prot_gap12", "prot_public"]:
    if f not in E:
        continue
    v = mark_values(D, E[f].fillna(0))
    print(f"  {f:<20} all {auc(y, v):.3f}  Aug {auc(y[~o], v[~o]):.3f}  Oct {auc(y[o], v[o]):.3f}   share of marks > 0: {(v > 0).mean():.2f}")
