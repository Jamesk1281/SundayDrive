"""The brief's three pass checks, for every candidate and sweep in cands.py.

Usage: evaluate.py <work_dir> <results_dir> [icons]
Writes to <results_dir> (aggregate only: no row locates a mark):
  icons_s0_breakdown.csv   each pinned road under S0: km, mean, km >= 7, weight x component
  icons.csv                each road's mean and share of km >= 7 under every candidate
  checks.csv               one row per candidate: the three checks and pass/fail
  ne_marks_ci.csv          paired drive-cluster bootstrap against S0
  byway_proxy.csv          FHWA scenic/natural, within ecoregion, per region and pooled
  distributions.csv        share of km >= 7 and mean, per region
With `icons`, only the first two (the region features are not needed).

Pieces (icons, Florida) and chunks (New England, Colorado, Utah) are scored the way
graph.py builds an edge: each piece's raw score, averaged along the edge by length, then
the composite with the edge's score_adj.
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "national_scoring"))
import cands as K
from roads import ROADS

WORK, OUT = Path(sys.argv[1]), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
ONLY_ICONS = "icons" in sys.argv[3:]
ALL = {**K.CANDIDATES, **K.SWEEPS}
S = K.S
t0 = time.time()


def log(*a):
    print(*a, f"{time.time() - t0:.0f}s", flush=True)


def composite(raw, adj):
    return 10.0 * np.clip((raw + S.RAW_BASE) * S.STRETCH + adj, 0.0, 1.0)


def edge_raw(raw_piece, edge, piece, n):
    return np.bincount(edge, weights=raw_piece * piece, minlength=n) / np.bincount(edge, weights=piece, minlength=n)


# ------------------------------------------------------------------ icons and controls
P = pd.read_parquet(WORK / "icons_pieces.parquet")
P["d_landmark"] = pd.read_parquet(WORK / "icons_landmark.parquet").d_landmark.to_numpy()
E = P.groupby("edge", sort=True).first()[["road", "kind", "region", "length_m", "score", "score_adj"] + K.BASE]
ne_ = len(E); assert (E.index == np.arange(ne_)).all()
ed, pc = P.edge.to_numpy(), P.piece.to_numpy()
ICON = {}
for name, spec in ALL.items():
    ICON[name] = composite(edge_raw(K.raw(P, spec), ed, pc, ne_), E.score_adj.to_numpy())
assert np.abs(ICON["S0 shipped E1"] - E.score.to_numpy()).max() < 1e-9, "S0 must reproduce the stored score"
km = E.length_m.to_numpy() / 1000
kind = E.kind.to_numpy()


def share7(s, m):
    return 100 * km[m & (s >= 7)].sum() / km[m].sum()


# S0 breakdown: weight x component, and the new features, length-weighted per road
Pk = P.piece.to_numpy()
feat = dict(prom10k=P.prom10k.fillna(0), open=K.open_land(P), vista=K.vista(P), sea=K.sea(P), wet=K.wet(P),
            rock=K.rock(P), pastoral=K.pastoral(P), landmark80=K.landmark(P), bare_1k=P.bare_1k, water_1k=P.water_1k)
rows = []
for road in ROADS:
    m = (E.road == road["id"]).to_numpy(); s0 = ICON["S0 shipped E1"]
    r = dict(road=road["id"], kind=road["kind"], km=km[m].sum(), mean=np.average(s0[m], weights=km[m]), km7=share7(s0, m))
    for c in K.BASE:
        r[c[2:]] = np.average(K.WT[c] * E[c].to_numpy()[m], weights=km[m])
    r["adj"] = np.average(E.score_adj.to_numpy()[m], weights=km[m])
    # the ceiling (brief, mechanism 2): raw the road has, and raw its own class needs for 7
    r["raw"] = np.average(sum(K.WT[c] * E[c].to_numpy()[m] for c in K.BASE), weights=km[m])
    r["raw_needed_7"] = 0.7 / S.STRETCH - S.RAW_BASE - r["adj"] / S.STRETCH
    pm = (P.road == road["id"]).to_numpy()
    for k, v in feat.items():
        r["f_" + k] = np.average(np.asarray(v, float)[pm], weights=Pk[pm])
    rows.append(r)
B = pd.DataFrame(rows)
B.to_csv(OUT / "icons_s0_breakdown.csv", index=False, float_format="%.3f")

rows = []
for road in ROADS:
    m = (E.road == road["id"]).to_numpy()
    for name, s in ICON.items():
        rows.append(dict(road=road["id"], kind=road["kind"], candidate=name, mean=np.average(s[m], weights=km[m]), km7=share7(s, m)))
I = pd.DataFrame(rows)
I.to_csv(OUT / "icons.csv", index=False, float_format="%.3f")
icon_rows = {}
for name, s in ICON.items():
    ctrl = I[(I.candidate == name) & (I.kind == "control")]
    icon_rows[name] = dict(icons_km7=share7(s, kind == "icon"), controls_km7=share7(s, kind == "control"),
                           worst_control_mean=ctrl["mean"].max(), worst_control=ctrl.loc[ctrl["mean"].idxmax(), "road"],
                           icons_mean=np.average(s[kind == "icon"], weights=km[kind == "icon"]))
log("icons scored")
pd.set_option("display.width", 250)
if ONLY_ICONS:
    print(pd.DataFrame(icon_rows).T.round(2).to_string())
    sys.exit()

# ------------------------------------------------------------------ chunk regions
import core as NS  # noqa: E402  (tools/national_scoring; needs NS_WORK)


def chunk_table(r):
    C = NS.load_chunks(r)
    for f in ("st_dem", "st_coast", "st_landmark"):
        C = pd.concat([C, pd.read_parquet(NS.REG / r / f"{f}.parquet")], axis=1)
    # S0 as built on usa: desert in forest's slot, c_grand, landmark credit gated on built land
    C["c_forest"] = np.maximum(C.c_forest.to_numpy(), NS.c_desert(C).to_numpy())
    C["c_grand"] = NS.c_grand(C).to_numpy()
    C["c_protected"] = NS.c_protected(C) * (C.built_1k.to_numpy() <= S.PROTECTED_BUILT_MAX)
    return C


def edgemap(r):
    m = np.load(NS.REG / r / "edgemap.npz")
    return m["row"], m["idx"], m["piece"].astype(float), int(m["n"])


# New England: marks and movement
C = chunk_table("ne")
row, idx, piece, n_e = edgemap("ne")
Eadj = np.bincount(row, weights=C.score_adj.to_numpy()[idx] * piece, minlength=n_e) / np.bincount(row, weights=piece, minlength=n_e)
D = NS.load_marks(); y = D.y.to_numpy(); octb = (D.batch == "Oct").to_numpy(); drives = D.drive.to_numpy()
u = np.unique(drives); rng = np.random.default_rng(20261021)
boots = [np.concatenate([np.flatnonzero(drives == d) for d in rng.choice(u, len(u))]) for _ in range(4000)]
km_c = C.length_m.to_numpy() / 1000
ne_rows, ci_rows, MV = {}, [], {}
for name, spec in ALL.items():
    rc = K.raw(C, spec)
    sc = composite(rc, C.score_adj.to_numpy())
    se = composite(np.bincount(row, weights=rc[idx] * piece, minlength=n_e) / np.bincount(row, weights=piece, minlength=n_e), Eadj)
    MV[name] = NS.mark_values(D, se)
    if name == "S0 shipped E1":
        s0c = sc
    rep = NS.mark_report(D, MV[name])
    d = sc - s0c
    ne_rows[name] = dict(ne_all=rep["all"], ne_oct=rep["oct"], ne_prec7=rep["prec7"], ne_n7=rep["n7"],
                         ne_km_moved_025=100 * km_c[np.abs(d) > 0.25].sum() / km_c.sum(),
                         ne_km7=100 * km_c[sc >= 7].sum() / km_c.sum())
base = MV["S0 shipped E1"]
for name in ALL:
    s = MV[name]
    # how many marks the candidate moves at all: the evidence the marks check can carry
    ne_rows[name]["ne_marks_moved_025"] = int((np.abs(s - base) > 0.25).sum())
    for sub, m in (("all", np.ones(len(D), bool)), ("Oct", octb)):
        diffs = []
        for ix in boots:
            ix = ix[m[ix]]
            if y[ix].all() or (~y[ix]).all():
                continue
            diffs.append(NS.auc(y[ix], s[ix]) - NS.auc(y[ix], base[ix]))
        diffs = np.array(diffs)
        ci_rows.append(dict(candidate=name, subset=sub, auc=NS.auc(y[m], s[m]), diff=NS.auc(y[m], s[m]) - NS.auc(y[m], base[m]),
                            lo=np.percentile(diffs, 5), hi=np.percentile(diffs, 95)))
CI = pd.DataFrame(ci_rows); CI.to_csv(OUT / "ne_marks_ci.csv", index=False, float_format="%.4f")
for name in ALL:
    o = CI[(CI.candidate == name) & (CI.subset == "Oct")].iloc[0]
    ne_rows[name].update(oct_diff=o["diff"], oct_lo=o["lo"])
log("New England marks")

# ------------------------------------------------------------------ byway proxy and distributions
PROXY = {}       # name -> region -> (score, label, weight, strata)
DIST = []


def proxy_add(region, name, s_nb, s, lab, w, eco, main):
    PROXY.setdefault(name, {})[region] = (s_nb[main], lab[main], w[main], eco[main])
    DIST.append(dict(candidate=name, region=region, mean=np.average(s, weights=w), km7=100 * w[s >= 7].sum() / w.sum()))


for r in ("ne", "co", "ut"):
    Cr = C if r == "ne" else chunk_table(r)
    w = Cr.length_m.to_numpy(); main = Cr.highway.isin(NS.MAIN).to_numpy()
    lab = Cr.fhwa_sn.to_numpy().astype(bool); eco = Cr.eco.to_numpy()
    for name, spec in ALL.items():
        adj = Cr.score_adj.to_numpy()
        proxy_add(r, name, composite(K.raw(Cr, dict(spec, drop_byway=True)), adj), composite(K.raw(Cr, spec), adj), lab, w, eco, main)
    del Cr
    log("proxy", r)

FE = pd.read_parquet(WORK / "fl_edges.parquet")
FP = pd.read_parquet(WORK / "fl_pieces.parquet")
FP["d_landmark"] = pd.read_parquet(WORK / "fl_landmark.parquet").d_landmark.to_numpy()
for c in K.BASE + ["score_adj"]:
    FP[c] = FE[c].to_numpy()[FP.edge.to_numpy()]
nf = len(FE); fed, fpc = FP.edge.to_numpy(), FP.piece.to_numpy()
w = FE.length_m.to_numpy(); main = FE.highway.isin(NS.MAIN).to_numpy()
for name, spec in ALL.items():
    s = composite(edge_raw(K.raw(FP, spec), fed, fpc, nf), FE.score_adj.to_numpy())
    if name == "S0 shipped E1":
        assert np.abs(s - FE.score.to_numpy()).max() < 1e-9
    snb = composite(edge_raw(K.raw(FP, dict(spec, drop_byway=True)), fed, fpc, nf), FE.score_adj.to_numpy())
    proxy_add("fl", name, snb, s, FE.fhwa_sn.to_numpy(), w, FE.eco.to_numpy(), main)
log("proxy fl")
pd.DataFrame(DIST).to_csv(OUT / "distributions.csv", index=False, float_format="%.3f")

rows = []
for name, by in PROXY.items():
    for r, (s, l, wt, e) in by.items():
        rows.append(dict(candidate=name, region=r, auc_eco=NS.wauc_strat(s, l, wt, e), auc=NS.wauc(s, l, wt)))
    # pooled: each region weighted to equal total km, pairs only within one region's ecoregion
    S_, L_, W_, E_ = [], [], [], []
    for r, (s, l, wt, e) in by.items():
        S_.append(s); L_.append(l); W_.append(wt / wt.sum()); E_.append(np.char.add(r + "|", e.astype(str)))
    rows.append(dict(candidate=name, region="pooled", auc_eco=NS.wauc_strat(np.concatenate(S_), np.concatenate(L_),
                     np.concatenate(W_), np.concatenate(E_))))
BP = pd.DataFrame(rows); BP.to_csv(OUT / "byway_proxy.csv", index=False, float_format="%.4f")
log("proxy done")

# ------------------------------------------------------------------ the three checks
s0 = BP[BP.candidate == "S0 shipped E1"].set_index("region").auc_eco
chk = []
for name in ALL:
    r = dict(candidate=name, **ne_rows[name], **icon_rows[name])
    b = BP[BP.candidate == name].set_index("region").auc_eco
    for reg in ("ne", "co", "ut", "fl", "pooled"):
        r[f"proxy_{reg}_diff"] = b[reg] - s0[reg]
    r["pass_ne"] = (r["oct_lo"] >= -0.005) and (r["ne_km_moved_025"] <= 3.0)
    r["pass_icons"] = (r["icons_km7"] > icon_rows["S0 shipped E1"]["icons_km7"]) and (r["worst_control_mean"] < 4) and (r["controls_km7"] <= 2.0)
    r["pass_proxy"] = r["proxy_pooled_diff"] >= -0.005
    r["pass_all"] = r["pass_ne"] and r["pass_icons"] and r["pass_proxy"]
    chk.append(r)
CH = pd.DataFrame(chk); CH.to_csv(OUT / "checks.csv", index=False, float_format="%.4f")
show = ["candidate", "ne_marks_moved_025", "ne_oct", "oct_diff", "oct_lo", "ne_km_moved_025", "icons_km7", "controls_km7", "worst_control_mean",
        "proxy_pooled_diff", "proxy_fl_diff", "proxy_ut_diff", "pass_ne", "pass_icons", "pass_proxy", "pass_all"]
print(CH[show].round(3).to_string())
log("done")
