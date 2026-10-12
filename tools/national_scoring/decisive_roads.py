"""Named, paved Western roads where the candidates disagree across the 7 line: where marks would decide.

Usage: decisive_roads.py <out_csv>
"""
import sys, pickle
import numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *  # noqa
from candidates import build, SPEC
REGIONS = ["ne", "co", "ut"]
chunks = {r: load_chunks(r) for r in REGIONS}
edges = {r: load_edges(r, chunks[r]) for r in REGIONS}
keep = {k: SPEC[k] for k in ["S0 shipped", "E1 terrain+desert+protected", "E1g E1 with grass", "C1 percentile per state",
                             "C2 percentile per ecoregion", "A2 relief cap + recal per state"]}
out, _ = build(REGIONS, chunks, edges, keep)
GROUPS = {"High Plains": "plains", "Southwestern Tablelands": "plains", "Southern Rockies": "mountains",
          "Wasatch and Uinta Mountains": "mountains", "Colorado Plateaus": "plateau/canyon",
          "Arizona/New Mexico Plateau": "plateau/canyon", "Wyoming Basin": "basin", "Central Basin and Range": "basin",
          "Mojave Basin and Range": "basin", "Northern Basin and Range": "basin"}
rows = []
for r in ["co", "ut"]:
    C = chunks[r].copy()
    surf = pd.read_parquet(REG / r / "chunks.parquet", columns=["surface"])["surface"]
    C = C[~surf.isin(S.UNPAVED).to_numpy() & C.highway.isin(MAIN + ["unclassified"]).to_numpy()]
    for k in keep:
        C[k] = out[k][r]["chunk"][C.index.to_numpy()]
    C["road"] = np.where(C.name.fillna("") != "", C.name.fillna(""), C.ref.fillna(""))
    C = C[C.road != ""]
    C["grp"] = C.eco.map(GROUPS).fillna("other")
    g = C.groupby("road").apply(lambda d: pd.Series(
        {"km": d.length_m.sum() / 1000, "group": d.grp.mode().iat[0], "ref": d.ref.dropna().mode().iat[0] if d.ref.notna().any() else "",
         **{k: np.average(d[k], weights=d.length_m) for k in keep}}), include_groups=False)
    g = g[g.km >= 10].reset_index()
    g["region"] = r
    s0, e1, c1, c2 = g["S0 shipped"], g["E1 terrain+desert+protected"], g["C1 percentile per state"], g["C2 percentile per ecoregion"]
    g["test"] = np.select(
        [(s0 < 7) & (e1 >= 7), (s0 >= 7) & (e1 >= 7), (e1 < 7) & (c1 >= 7), (c1 < 7) & (c2 >= 7), (s0 < 4) & (e1 < 4) & (c2 < 4)],
        ["E1 promotes to 7+", "agreed 7+", "scale-only (percentile per state) promotes", "ecoregion percentile promotes", "agreed dull"], "middle")
    rows.append(g)
G = pd.concat(rows)
G.to_csv(sys.argv[1], index=False)
pd.set_option("display.width", 220)
print(G.groupby(["region", "test", "group"]).agg(roads=("road", "size"), km=("km", "sum")).round(0).to_string())
for t in ["E1 promotes to 7+", "scale-only (percentile per state) promotes", "ecoregion percentile promotes"]:
    print("\n", t)
    print(G[G.test == t].sort_values("km", ascending=False).head(14)[["region", "group", "road", "ref", "km", "S0 shipped",
          "E1 terrain+desert+protected", "C1 percentile per state", "C2 percentile per ecoregion"]].round(1).to_string(index=False))
