"""V's prominence proxy against the true viewshed, on the icon and control pieces.

Usage: proxy_vs_viewshed.py <work_dir> <results_dir>
Writes proxy_vs_viewshed.csv: per road, mean prom10k and vis10k (m), and km >= 7 under
S0, V with the proxy, and V with the viewshed (same constants, vis10k for prom10k).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cands as K
from roads import ROADS

WORK, OUT = Path(sys.argv[1]), Path(sys.argv[2])
P = pd.read_parquet(WORK / "icons_pieces.parquet")
P["vis10k"] = pd.read_parquet(WORK / "icons_viewshed.parquet").vis10k.to_numpy()
E = P.groupby("edge", sort=True).first()
n = len(E); ed, pc = P.edge.to_numpy(), P.piece.to_numpy()


def edge_score(raw):
    r = np.bincount(ed, weights=raw * pc, minlength=n) / np.bincount(ed, weights=pc, minlength=n)
    return 10.0 * np.clip((r + K.S.RAW_BASE) * K.S.STRETCH + E.score_adj.to_numpy(), 0, 1)


s0 = edge_score(K.raw(P, {}))
sv = edge_score(K.raw(P, dict(vista={})))
Pv = P.copy(); Pv["prom10k"] = Pv["vis10k"]
sw = edge_score(K.raw(Pv, dict(vista={})))
km = E.length_m.to_numpy() / 1000
rows = []
for road in ROADS:
    m = (E.road == road["id"]).to_numpy(); pm = (P.road == road["id"]).to_numpy()
    k7 = lambda s: 100 * km[m & (s >= 7)].sum() / km[m].sum()
    rows.append(dict(road=road["id"], kind=road["kind"],
                     prom10k=np.average(P.prom10k.fillna(0)[pm], weights=pc[pm]),
                     vis10k=np.average(P.vis10k.fillna(0)[pm], weights=pc[pm]),
                     vis_share=np.average((P.vis10k.fillna(0) / P.prom10k.clip(lower=1)).clip(upper=1)[pm], weights=pc[pm]),
                     km7_s0=k7(s0), km7_v_proxy=k7(sv), km7_v_viewshed=k7(sw),
                     mean_v_proxy=np.average(sv[m], weights=km[m]), mean_v_viewshed=np.average(sw[m], weights=km[m])))
T = pd.DataFrame(rows)
r = np.corrcoef(P.prom10k.fillna(0), P.vis10k.fillna(0))[0, 1]
print(f"piece-level correlation prom10k vs vis10k: {r:.3f}")
for k in ("icon", "control"):
    m = (E.kind == k).to_numpy()
    print(k, {nm: round(100 * km[m & (s >= 7)].sum() / km[m].sum(), 2) for nm, s in (("S0", s0), ("V proxy", sv), ("V viewshed", sw))})
T.to_csv(OUT / "proxy_vs_viewshed.csv", index=False, float_format="%.3f")
pd.set_option("display.width", 200)
print(T.round(2).to_string())
