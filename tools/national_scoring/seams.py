"""The seam a regional percentile puts at a boundary: what one shipped score becomes on each side.

Usage: seams.py <out_csv>
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *  # noqa
REGIONS = ["ne", "co", "ut"]
C = {r: load_chunks(r) for r in REGIONS}
ref_s, ref_w = C["ne"].score.to_numpy(), C["ne"].length_m.to_numpy()
rows = []
maps = {r: quantile_map(C[r].score.to_numpy(), C[r].length_m.to_numpy(), ref_s, ref_w) for r in ("co", "ut")}
eco = {}
for r in ("ne", "co", "ut"):
    for g in C[r].eco.unique():
        m = (C[r].eco == g).to_numpy()
        if C[r].length_m.to_numpy()[m].sum() >= 2000e3:
            eco[(r, g)] = quantile_map(C[r].score.to_numpy()[m], C[r].length_m.to_numpy()[m], ref_s, ref_w)
for s in (3.0, 4.0, 5.0, 6.0, 6.5, 7.0, 8.0):
    row = {"shipped": s, "percentile per state, CO": float(maps["co"](s)), "percentile per state, UT": float(maps["ut"](s))}
    for (r, g), f in eco.items():
        row[f"ecoregion {r.upper()}: {g}"] = float(f(s))
    rows.append(row)
T = pd.DataFrame(rows).set_index("shipped")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(T.T.round(1).to_string())
T.to_csv(sys.argv[1])
