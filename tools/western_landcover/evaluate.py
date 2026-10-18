"""Every desert source in E1's forest slot, measured on the same rebuild. Aggregates only.

Usage: evaluate.py <out_dir> [--ne-only]
Needs $NS_WORK/reg/{ne,co,ut} with the national_scoring feature tables plus wc_m3.parquet and
lc30.parquet (sample30.py), and $NS_WORK/marks.pkl. Writes CSVs and a text report to <out_dir>.

Order, as the brief's trap 1 asks: New England movement for every candidate is computed and
printed first; the Western tables come after it. Nothing here is fitted to anything.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_lib import *  # noqa: the loaded regions, marks and candidate scores
from evaluate_lib import t0

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
REPORT = open(OUT / ("report_ne_first.txt" if "--ne-only" in sys.argv else "report.txt"), "w")


def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); REPORT.write(s + "\n")


# ------------------------------------------------------------ 0. New England first (trap 1)
y = D.y.to_numpy(); o = (D.batch == "Oct").to_numpy(); drives = D.drive.to_numpy(); u = np.unique(drives)
rng = np.random.default_rng(20261018)
picks = [np.concatenate([np.flatnonzero(drives == d) for d in rng.choice(u, len(u))]) for _ in range(4000)]
km_ne = chunks["ne"].length_m.to_numpy() / 1000
e1_ne = S["W0"]["ne"]["chunk"]
e1_marks = mark_values(D, S["W0"]["ne"]["edge"])


def paired(s, base, m):
    d = []
    for ix in picks:
        ix = ix[m[ix]]
        if y[ix].all() or (~y[ix]).all():
            continue
        d.append(auc(y[ix], s[ix]) - auc(y[ix], base[ix]))
    return np.percentile(d, 5), np.percentile(d, 95)


rows = []
for name, by in [("S0 (no national terms)", S0)] + list(S.items()) + [(f"{k} + its grass", v) for k, v in SG.items()]:
    s = mark_values(D, by["ne"]["edge"])
    rep = mark_report(D, s)
    d = by["ne"]["chunk"] - e1_ne
    lo_a, hi_a = paired(s, e1_marks, np.ones(len(D), bool))
    lo_o, hi_o = paired(s, e1_marks, o)
    rows.append(dict(name=name, km_moved_025=100 * km_ne[np.abs(d) > .25].sum() / km_ne.sum(),
                     km_moved_1=100 * km_ne[np.abs(d) > 1].sum() / km_ne.sum(),
                     share7=100 * km_ne[by["ne"]["chunk"] >= 7].sum() / km_ne.sum(),
                     mean=np.average(by["ne"]["chunk"], weights=km_ne),
                     **rep, d_all=rep["all"] - auc(y, e1_marks), d_all_lo=lo_a, d_all_hi=hi_a,
                     d_oct=rep["oct"] - auc(y[o], e1_marks[o]), d_oct_lo=lo_o, d_oct_hi=hi_o))
T0 = pd.DataFrame(rows).set_index("name")
T0.to_csv(OUT / "ne_movement_and_marks.csv")
say("0. NEW ENGLAND, relative to E1 (W0). km moved in %, marks AUC, differences with a paired drive-cluster 90% interval")
say(T0[["km_moved_025", "km_moved_1", "share7", "mean", "all", "oct", "prec7", "n7", "band37",
        "d_all", "d_all_lo", "d_all_hi", "d_oct", "d_oct_lo", "d_oct_hi"]].round(3).to_string())

# NE: where do the movers sit? (state and road class, km)
rows = []
for name in DESERT:
    d = S[name]["ne"]["chunk"] - e1_ne; m = np.abs(d) > .25
    C = chunks["ne"]
    for st, g in pd.Series(km_ne[m]).groupby(C.state.to_numpy()[m]):
        rows.append(dict(name=name, state=st, km=g.sum(), share_of_state=100 * g.sum() / km_ne[C.state.to_numpy() == st].sum()))
say("\n   km moved > 0.25 by state (% of the state's km)")
if rows:
    say(pd.DataFrame(rows).pivot_table(index="name", columns="state", values="share_of_state", sort=False).round(2).to_string())

if "--ne-only" in sys.argv:
    say("stopped after New England (--ne-only)"); raise SystemExit(0)

# ------------------------------------------------------------ 1. coverage: what each source calls desert and grass
rows = []
for r in REGIONS:
    C = chunks[r]; w = C.length_m.to_numpy()
    feats = {f"desert {k}": f(C) for k, f in DESERT.items()} | {f"grass {k}": f(C) for k, f in GRASS.items()}
    feats["grassland (E1g form, WorldCover)"] = c_grassland(C).to_numpy()
    for k, v in feats.items():
        rows.append(dict(region=r, feature=k, mean=np.average(v, weights=w), share_ge_05=100 * w[v >= .5].sum() / w.sum()))
T1 = pd.DataFrame(rows)
T1.to_csv(OUT / "coverage.csv", index=False)
say("\n1. COVERAGE: km share with the fraction >= 0.5 (%)")
say(T1.pivot_table(index="feature", columns="region", values="share_ge_05", sort=False).round(1).to_string())

# What WorldCover's grass is, in the West: content of km where WorldCover grass_1k >= 0.5, by landscape
rows = []
for r in ("co", "ut"):
    C = chunks[r]; w = C.length_m.to_numpy(); grp = C.eco.map(GROUPS).fillna("other").to_numpy()
    g = C.grass_1k.to_numpy() >= .5
    for G in ["ALL"] + sorted(set(grp)):
        m = g & ((grp == G) if G != "ALL" else True)
        if w[m].sum() < 200e3:
            continue
        rows.append(dict(region=r, group=G, km=w[m].sum() / 1000,
                         **{k: np.average(C[k].to_numpy()[m], weights=w[m]) for k in
                            ("lf_desert", "lf_grass", "nlcd_desert", "nlcd_grass", "nlcd_pasture", "nlcd_crop",
                             "rc_sage", "rc_shrub", "rc_bare", "rc_herb", "rc_range")}))
T1b = pd.DataFrame(rows)
T1b.to_csv(OUT / "what_worldcover_grass_is.csv", index=False)
say("\n   What WorldCover calls grassland (km with grass_1k >= 0.5): mean content by the other sources")
say(T1b.round(3).to_string(index=False))

# ------------------------------------------------------------ 2. byway proxy
LAB = ["byway_osm", "fhwa_sn", "fhwa_hc"]
rows = []
for name, by in [("S0", S0)] + list(S.items()) + [(f"{k} + its grass", v) for k, v in SG.items()]:
    for r in REGIONS:
        C = chunks[r]; m = C.highway.isin(MAIN).to_numpy(); w = C.length_m.to_numpy(); s = by[r]["chunk_nb"]
        for lab in LAB:
            yb = C[lab].to_numpy().astype(bool)
            if (yb & m).sum() < 20:
                continue
            rows.append(dict(name=name, region=r, label=lab, auc=wauc(s[m], yb[m], w[m]),
                             auc_eco=wauc_strat(s[m], yb[m], w[m], C.eco.to_numpy()[m])))
T2 = pd.DataFrame(rows)
T2.to_csv(OUT / "byway_proxy.csv", index=False)
for v in ("auc", "auc_eco"):
    say(f"\n2. BYWAY PROXY {v} (trunk-tertiary, byway term removed)")
    say(T2.pivot_table(index="name", columns=["region", "label"], values=v, sort=False).round(3).to_string())

# ------------------------------------------------------------ 3. distributions
rows = []
for name, by in [("S0", S0)] + list(S.items()):
    for r in REGIONS:
        C = chunks[r]; s = by[r]["chunk"]; w = C.length_m.to_numpy()
        grp = C.eco.map(GROUPS).fillna("all-NE" if r == "ne" else "other").to_numpy()
        for G in ["ALL"] + sorted(set(grp)):
            m = np.ones(len(C), bool) if G == "ALL" else grp == G
            if w[m].sum() < 1000e3:
                continue
            rows.append(dict(name=name, region=r, group=G, km=w[m].sum() / 1000, mean=np.average(s[m], weights=w[m]),
                             share7=100 * w[m & (s >= 7)].sum() / w[m].sum()))
T3 = pd.DataFrame(rows)
T3.to_csv(OUT / "distributions.csv", index=False)
say("\n3. SHARE OF KM >= 7 (%) by landscape")
say(T3.pivot_table(index="name", columns=["region", "group"], values="share7", sort=False).round(1).to_string())
say("\n   mean score")
say(T3.pivot_table(index="name", columns=["region", "group"], values="mean", sort=False).round(2).to_string())


# ------------------------------------------------------------ 4. named roads (eval_all.py's list, plus the brief's)
def bm(r):
    C = chunks[r]; nm = C.name.fillna("").str.lower(); ref = C.ref.fillna(""); lon, lat = C.lon, C.lat
    if r == "co":
        return [("rule >= 7", "Trail Ridge Road", nm.str.contains("trail ridge road")),
                ("rule >= 7", "Rim Rock Drive", nm.str.fullmatch("rim rock drive")),
                ("scenic", "US 550, all of it in CO", ref.str.contains("US 550")),
                ("scenic", "Million Dollar Hwy (named section)", nm.str.contains("million dollar")),
                ("scenic", "CO 141 Unaweep-Tabeguache", ref.str.fullmatch("CO 141")),
                ("scenic", "Highway of Legends (CO 12)", ref.str.fullmatch("CO 12")),
                ("scenic", "Kebler Pass Road", nm.str.contains("kebler pass road")),
                ("scenic", "US 50 Gunnison-Montrose", ref.str.contains("US 50") & (lon < -107.0) & (lon > -107.9)),
                ("rule <= 4", "I 70 east of Denver", ref.str.contains("I 70") & (lon > -104.6)),
                ("rule <= 4", "US 287 on the plains", ref.str.contains("US 287") & (lon > -103.5)),
                ("dull", "I 76", ref.str.contains("I 76")),
                ("dull", "US 385", ref.str.contains("US 385"))]
    if r == "ut":
        return [("rule >= 7", "SR 128 (Colorado River)", ref.str.fullmatch("SR 128")),
                ("rule >= 7", "Capitol Reef Scenic Drive", nm.str.contains("capitol reef scenic")),
                ("scenic", "SR 12 (Scenic Byway 12)", ref.str.fullmatch("SR 12")),
                ("scenic", "Zion-Mount Carmel Hwy", nm.str.contains("zion.mount carmel")),
                ("scenic", "Potash Road (SR 279)", ref.str.fullmatch("SR 279")),
                ("scenic", "Bryce Canyon Scenic Drive", nm.str.contains("bryce canyon scenic")),
                ("scenic", "Logan Canyon Scenic Byway", nm.str.contains("logan canyon scenic")),
                ("dull", "I 80 west of Salt Lake", ref.str.contains("I 80") & (lon < -112.3)),
                ("dull", "I 15 through Millard/Juab", ref.str.contains("I 15") & (lat > 38.5) & (lat < 39.8)),
                ("dull", "US 6 Delta-Eureka", ref.str.contains("US 6") & (lon < -112.0) & (lon > -113.0))]
    return [("scenic", "Kancamagus Hwy", nm.str.contains("kancamagus")),
            ("scenic", "Mohawk Trail", nm.str.contains("mohawk trail")),
            ("scenic", "VT 100", ref.str.contains(r"\bVT 100\b")),
            ("dull", "I 90 (Mass Pike)", ref.str.fullmatch("I 90")),
            ("dull", "I 95", ref.str.contains("I 95"))]


rows = []
for r in REGIONS:
    C = chunks[r]; w = C.length_m.to_numpy()
    for kind, lab, mask in bm(r):
        m = mask.to_numpy()
        row = dict(region=r, kind=kind, road=lab, km=w[m].sum() / 1000)
        for name, by in [("S0", S0)] + list(S.items()):
            row[name] = np.average(by[r]["chunk"][m], weights=w[m]) if m.any() else np.nan
        rows.append(row)
T4 = pd.DataFrame(rows)
T4.to_csv(OUT / "named_roads.csv", index=False)
say("\n4. NAMED ROADS (length-weighted mean score)")
say(T4.round(2).to_string(index=False))

# ------------------------------------------------------------ 5. the prairie question, single features
rows = []
mk = {}
for k, f in GRASS.items():
    v = mark_values(D, f(edges["ne"]))
    mk[k] = dict(marks_all=auc(y, v), marks_oct=auc(y[o], v[o]), marks_aug=auc(y[~o], v[~o]))
for r in REGIONS:
    C = chunks[r]; m = C.highway.isin(MAIN).to_numpy(); w = C.length_m.to_numpy()
    for k, f in list(GRASS.items()) + [("NLCD Pasture/Hay (81)", lambda F: F["nlcd_pasture"].to_numpy()),
                                       ("NLCD Cultivated Crops (82)", lambda F: F["nlcd_crop"].to_numpy()),
                                       ("RCMAP sagebrush cover", lambda F: F["rc_sage"].to_numpy())] + \
                                      [(f"desert {k2}", f2) for k2, f2 in DESERT.items()]:
        x = f(C)
        for lab in ("byway_osm", "fhwa_sn"):
            yb = C[lab].to_numpy().astype(bool)
            if (yb & m).sum() < 20:
                continue
            rows.append(dict(feature=k, region=r, label=lab, auc=wauc(x[m], yb[m], w[m]),
                             auc_eco=wauc_strat(x[m], yb[m], w[m], C.eco.to_numpy()[m]),
                             byway_mean=np.average(x[m & yb], weights=w[m & yb]),
                             other_mean=np.average(x[m & ~yb], weights=w[m & ~yb]), **mk.get(k, {})))
T5 = pd.DataFrame(rows)
T5.to_csv(OUT / "single_features.csv", index=False)
for v in ("auc", "auc_eco"):
    say(f"\n5. SINGLE FEATURES {v} (trunk-tertiary)")
    say(T5.pivot_table(index="feature", columns=["region", "label"], values=v, sort=False).round(3).to_string())
say("\n   on the 151 New England marks")
say(pd.DataFrame(mk).T.round(3).to_string())
say("done", f"{time.time() - t0:.0f}s")
