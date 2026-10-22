"""Does the pipeline reproduce what tools/scenery_types measured offline?

Usage: check.py ne|ut <e1_processed> <full_processed> <results_dir>

Both directories are scratch copies scored by pipeline/score.py: <e1_processed> without
the scenery additions' inputs (no prom10k.tif, no ~1 km tree/water/mangrove shares, no
landmark_near), which is E1 exactly; <full_processed> with them, which is V+S2+L. The
two share their chunks, and the study's chunk table for the region ($NS_WORK/reg/<r>)
must hold the same chunks in the same order: that is checked, midpoint by midpoint.

Each term changes one column only (V c_grand, S2 c_water, L c_protected), so a single
term's score is E1's raw plus that column's weighted change, and is printed beside the
study's single-term rows.

Writes <results_dir>/<r>_check.csv (aggregate only, no row locates a mark) and prints:
  ne  the marks (all, Oct, >= 7, paired drive-cluster 90% interval on Oct), km moved
      by more than 0.25, share of km at 7 or more, and the component differences
      between the pipeline and the study's features
  ut  share of km at 7 or more, mean, and the byway proxy within ecoregion
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scenery_types")); sys.path.insert(0, str(HERE.parent / "national_scoring"))
import cands as K          # noqa: E402  (imports pipeline/score.py as K.S)
import core as NS          # noqa: E402  (needs NS_WORK)

S = K.S
region, E1_DIR, FULL_DIR, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
COLS = ["highway", "length_m", "score_adj", "raw", "score"] + K.BASE
TERMS = {"V": "c_grand", "S2": "c_water", "L": "c_protected"}


def chunks(d):
    import geopandas as gpd
    c = gpd.read_parquet(d / "scored_chunks.parquet", columns=COLS + ["geometry"])
    m = c.geometry.interpolate(0.5, normalized=True).to_crs(4326)
    df = pd.DataFrame(c.drop(columns="geometry"))
    df["lon"], df["lat"] = m.x.to_numpy(), m.y.to_numpy()
    return df


A, B = chunks(E1_DIR), chunks(FULL_DIR)
assert len(A) == len(B) and np.array_equal(A.lon, B.lon) and np.array_equal(A.lat, B.lat)
# Only the three columns may differ between the two builds.
for c in K.BASE:
    if c not in TERMS.values():
        assert np.array_equal(A[c].to_numpy(), B[c].to_numpy()), c
assert np.array_equal(A.score_adj.to_numpy(), B.score_adj.to_numpy())

# The study's chunk table for the region, as evaluate.py builds it.
C = NS.load_chunks(region)
for f in ("st_dem", "st_coast", "st_landmark"):
    C = pd.concat([C, pd.read_parquet(NS.REG / region / f"{f}.parquet")], axis=1)
assert len(C) == len(A) and np.allclose(C.lon, A.lon, atol=1e-9) and np.allclose(C.lat, A.lat, atol=1e-9), \
    "the study's chunks are not the pipeline's"
C["c_forest"] = np.maximum(C.c_forest.to_numpy(), NS.c_desert(C).to_numpy())
C["c_grand"] = NS.c_grand(C).to_numpy()
C["c_protected"] = NS.c_protected(C) * (C.built_1k.to_numpy() <= S.PROTECTED_BUILT_MAX)

km = A.length_m.to_numpy() / 1000
adj = A.score_adj.to_numpy()
W = K.WT
raw_e1 = A.raw.to_numpy()
assert np.allclose(raw_e1, sum(W[c] * A[c].to_numpy() for c in K.BASE), atol=1e-9)


def term_raw(names):
    r = raw_e1.copy()
    for t in names:
        c = TERMS[t]
        r += W[c] * (B[c].to_numpy() - A[c].to_numpy())
    return r


PIPE = {"E1": raw_e1, "V": term_raw(["V"]), "S2": term_raw(["S2"]), "L": term_raw(["L"]),
        "V+S2": term_raw(["V", "S2"]), "V+S2+L": B.raw.to_numpy()}
assert np.allclose(PIPE["V+S2+L"], term_raw(["V", "S2", "L"]), atol=1e-9)
STUDY = {"E1": "S0 shipped E1", "V": "V slot (R10, 300-900 m)", "S2": "S2 sea as water, on the sea only",
         "L": "L landmark within 80 m", "V+S2": "V+S2", "V+S2+L": "V+S2+L"}
STUDY_RAW = {k: K.raw(C, K.CANDIDATES[v]) for k, v in STUDY.items()}

rows = []
print(f"{region}: {len(A):,} chunks, {km.sum():,.0f} km; score_adj max |pipeline - study| "
      f"{np.abs(C.score_adj.to_numpy() - adj).max():.2e}")
# The E1 build against the study's S0, every component: the baseline both sides start from.
for c in K.BASE:
    if c in TERMS.values():
        continue
    d = np.abs(A[c].to_numpy() - C[c].to_numpy())
    print(f"  {c:12s} E1      km differing >0.05: {100 * km[d > 0.05].sum() / km.sum():.3f}%   max {d.max():.3f}")
# Component by component: the pipeline against the study's features, on the full build.
study_full = {"c_grand": np.maximum(C.c_grand.to_numpy(), K.vista(C)),
              "c_water": np.maximum(C.c_water.to_numpy(), K.sea(C, on_sea=True)),
              "c_protected": np.maximum(C.c_protected.to_numpy(), K.landmark(C))}
for c, sv in study_full.items():
    for lab, pv, ref in (("E1", A[c].to_numpy(), C[c].to_numpy()), ("V+S2+L", B[c].to_numpy(), sv)):
        d = np.abs(pv - ref)
        r = dict(region=region, row=f"component {c} {lab}", km_diff_gt_0_05=100 * km[d > 0.05].sum() / km.sum(),
                 mean_pipeline=np.average(pv, weights=km), mean_study=np.average(ref, weights=km),
                 nonzero_pipeline=100 * km[pv > 0].sum() / km.sum(), nonzero_study=100 * km[ref > 0].sum() / km.sum())
        rows.append(r)
        print(f"  {c:12s} {lab:7s} km differing >0.05: {r['km_diff_gt_0_05']:.3f}%   mean {r['mean_pipeline']:.4f} vs "
              f"{r['mean_study']:.4f}   nonzero {r['nonzero_pipeline']:.2f}% vs {r['nonzero_study']:.2f}%")

s_e1 = S.composite(raw_e1, adj)
st_e1 = S.composite(STUDY_RAW["E1"], adj)
for name in PIPE:
    sp = S.composite(PIPE[name], adj)
    ss = S.composite(STUDY_RAW[name], adj)
    r = dict(region=region, row=name,
             km7=100 * km[sp >= 7].sum() / km.sum(), km7_study=100 * km[ss >= 7].sum() / km.sum(),
             mean=np.average(sp, weights=km), mean_study=np.average(ss, weights=km),
             km_moved_025=100 * km[np.abs(sp - s_e1) > 0.25].sum() / km.sum(),
             km_moved_025_study=100 * km[np.abs(ss - st_e1) > 0.25].sum() / km.sum(),
             km_vs_study_025=100 * km[np.abs(sp - ss) > 0.25].sum() / km.sum())
    rows.append(r)

if region == "ne":
    m = np.load(NS.REG / "ne" / "edgemap.npz")
    row, idx, piece, n_e = m["row"], m["idx"], m["piece"].astype(float), int(m["n"])
    tot = np.bincount(row, weights=piece, minlength=n_e)
    e_adj = np.bincount(row, weights=adj[idx] * piece, minlength=n_e) / tot
    D = NS.load_marks(); y = D.y.to_numpy(); octb = (D.batch == "Oct").to_numpy(); drives = D.drive.to_numpy()
    u = np.unique(drives); rng = np.random.default_rng(20261021)
    boots = [np.concatenate([np.flatnonzero(drives == d) for d in rng.choice(u, len(u))]) for _ in range(4000)]

    def marks(raw):
        return NS.mark_values(D, S.composite(np.bincount(row, weights=raw[idx] * piece, minlength=n_e) / tot, e_adj))

    MV = {k: marks(v) for k, v in PIPE.items()}
    MS = {k: marks(v) for k, v in STUDY_RAW.items()}
    base = MV["E1"]
    for r in rows:
        if r["row"] not in MV:
            continue
        s = MV[r["row"]]; rep = NS.mark_report(D, s); rs = NS.mark_report(D, MS[r["row"]])
        diffs = []
        for ix in boots:
            ix = ix[octb[ix]]
            if y[ix].all() or (~y[ix]).all():
                continue
            diffs.append(NS.auc(y[ix], s[ix]) - NS.auc(y[ix], base[ix]))
        r.update(marks_all=rep["all"], marks_oct=rep["oct"], n7=rep["n7"], prec7=rep["prec7"],
                 oct_diff=rep["oct"] - NS.mark_report(D, base)["oct"],
                 oct_lo=np.percentile(diffs, 5), oct_hi=np.percentile(diffs, 95),
                 marks_moved_025=int((np.abs(s - base) > 0.25).sum()),
                 marks_all_study=rs["all"], marks_oct_study=rs["oct"], n7_study=rs["n7"],
                 marks_vs_study_max=float(np.abs(s - MS[r["row"]]).max()))
else:
    import geopandas as gpd  # noqa: F401
    main = A.highway.isin(NS.MAIN).to_numpy(); lab = C.fhwa_sn.to_numpy().astype(bool); eco = C.eco.to_numpy()
    w = A.length_m.to_numpy()
    for r in rows:
        if r["row"] not in PIPE:
            continue
        nb = PIPE[r["row"]] - W["c_scenic_tag"] * A.c_scenic_tag.to_numpy()
        nbs = STUDY_RAW[r["row"]] - W["c_scenic_tag"] * C.c_scenic_tag.to_numpy()
        r.update(proxy_eco=NS.wauc_strat(S.composite(nb, adj)[main], lab[main], w[main], eco[main]),
                 proxy_eco_study=NS.wauc_strat(S.composite(nbs, adj)[main], lab[main], w[main], eco[main]))

R = pd.DataFrame(rows)
R.to_csv(OUT / f"{region}_check.csv", index=False, float_format="%.4f")
pd.set_option("display.width", 250)
show = [c for c in ["row", "km7", "km7_study", "mean", "mean_study", "km_moved_025", "km_moved_025_study", "km_vs_study_025",
                    "marks_all", "marks_all_study", "marks_oct", "marks_oct_study", "oct_diff", "oct_lo", "oct_hi", "n7", "n7_study",
                    "marks_moved_025", "marks_vs_study_max", "proxy_eco", "proxy_eco_study"] if c in R]
print(R[R.row.isin(PIPE)][show].round(4).to_string(index=False))
