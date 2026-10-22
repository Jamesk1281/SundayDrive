"""Which named roads a candidate moves: New England chunks and Florida edges.

Usage: movers.py <work_dir> <results_dir> <candidate> [<candidate> ...]
Writes movers.csv: per candidate and region, the 15 named roads (OSM name, else ref)
with the most km moved by more than 0.25 against S0, their mean change, and the share
of all moved km that is motorway or in built-up land (WorldCover built > 30% of ~1 km).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "national_scoring"))
import cands as K
import core as NS

WORK, OUT, names = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
spec = {**K.CANDIDATES, **K.SWEEPS}


def comp(raw, adj):
    return 10.0 * np.clip((raw + K.S.RAW_BASE) * K.S.STRETCH + adj, 0.0, 1.0)


C = NS.load_chunks("ne")
for f in ("st_dem", "st_coast", "st_landmark"):
    C = pd.concat([C, pd.read_parquet(NS.REG / "ne" / f"{f}.parquet")], axis=1)
C["c_forest"] = np.maximum(C.c_forest.to_numpy(), NS.c_desert(C).to_numpy())
C["c_grand"] = NS.c_grand(C).to_numpy()
C["c_protected"] = NS.c_protected(C) * (C.built_1k.to_numpy() <= K.S.PROTECTED_BUILT_MAX)
FE = pd.read_parquet(WORK / "fl_edges.parquet"); FP = pd.read_parquet(WORK / "fl_pieces.parquet")
FP["d_landmark"] = pd.read_parquet(WORK / "fl_landmark.parquet").d_landmark.to_numpy()
for c in K.BASE + ["score_adj"]:
    FP[c] = FE[c].to_numpy()[FP.edge.to_numpy()]
ed, pc, n = FP.edge.to_numpy(), FP.piece.to_numpy(), len(FE)
FE["built_1k"] = np.bincount(ed, weights=FP.built_1k.to_numpy() * pc, minlength=n) / np.bincount(ed, weights=pc, minlength=n)


def fl_score(sp):
    r = np.bincount(ed, weights=K.raw(FP, sp) * pc, minlength=n) / np.bincount(ed, weights=pc, minlength=n)
    return comp(r, FE.score_adj.to_numpy())


rows = []
for reg, T, s0, f in (("ne", C, comp(K.raw(C, {}), C.score_adj.to_numpy()), lambda sp: comp(K.raw(C, sp), C.score_adj.to_numpy())),
                      ("fl", FE, FE.score.to_numpy(), fl_score)):
    label = T["name"].fillna(T["ref"]).fillna("(unnamed)").to_numpy()
    km = T.length_m.to_numpy() / 1000
    for nm in names:
        d = f(spec[nm]) - s0
        mv = np.abs(d) > 0.25
        urb = mv & ((T.built_1k.to_numpy() > 0.3) | T.highway.isin(["motorway", "motorway_link"]).to_numpy())
        G = pd.DataFrame({"road": label[mv], "km": km[mv], "d": d[mv]})
        top = G.groupby("road").apply(lambda g: pd.Series({"km": g.km.sum(), "mean_change": np.average(g.d, weights=g.km)}),
                                      include_groups=False).sort_values("km", ascending=False).head(15)
        for road, r in top.iterrows():
            rows.append(dict(candidate=nm, region=reg, road=road, km_moved=r.km, mean_change=r.mean_change,
                             region_km_moved=km[mv].sum(), share_urban_or_motorway=km[urb].sum() / max(km[mv].sum(), 1e-9)))
M = pd.DataFrame(rows); M.to_csv(OUT / "movers.csv", index=False, float_format="%.3f")
pd.set_option("display.width", 220)
for (nm, reg), g in M.groupby(["candidate", "region"], sort=False):
    print(f"\n{nm} [{reg}] moved {g.region_km_moved.iloc[0]:.0f} km, urban or motorway {g.share_urban_or_motorway.iloc[0]:.0%}")
    print(g[["road", "km_moved", "mean_change"]].head(10).round(2).to_string(index=False))
