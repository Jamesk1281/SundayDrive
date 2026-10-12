"""Measure every candidate: NE marks, byway proxy, distributions, benchmarks. Writes CSVs to <out_dir>.

Usage: eval_all.py <out_dir>
"""
import sys, time, pickle
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *  # noqa
from candidates import build, SPEC

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
REGIONS = ["ne", "co", "ut"]
t0 = time.time()
chunks = {r: load_chunks(r) for r in REGIONS}
edges = {r: load_edges(r, chunks[r]) for r in REGIONS}
print("loaded", f"{time.time() - t0:.0f}s", flush=True)
cands, info = build(REGIONS, chunks, edges)
print("built", f"{time.time() - t0:.0f}s", flush=True)
for k, v in info.items():
    print("  calibration", k, v)

# ------------------------------------------------------------ D: learned from byway labels
FEATS = [c for c in COMP if c != "c_scenic_tag"] + ["score_adj", "relief3k", "above3k", "below3k", "z",
         "tree_1k", "grass_1k", "shrub_1k", "bare_1k", "crop_1k", "built_1k", "prot_landmark", "prot_public"]


def feats(F):
    X = np.column_stack([F[f].fillna(0).to_numpy().astype(float) for f in FEATS])
    return X


def fit_logit(X, y, w, l2=1.0):
    from scipy.optimize import minimize
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    Z = np.column_stack([np.ones(len(X)), (X - mu) / sd])
    w = w / w.mean()
    def f(b):
        z = Z @ b
        return np.sum(w * (np.logaddexp(0, z) - y * z)) + l2 * np.sum(b[1:] ** 2)
    def g(b):
        p = 1 / (1 + np.exp(-(Z @ b)))
        gr = Z.T @ (w * (p - y)); gr[1:] += 2 * l2 * b[1:]; return gr
    b = minimize(f, np.zeros(Z.shape[1]), jac=g, method="L-BFGS-B").x
    return lambda X2: np.column_stack([np.ones(len(X2)), (X2 - mu) / sd]) @ b, b


rng = np.random.default_rng(20261012)


def train(regions, label):
    Xs, ys, ws = [], [], []
    for r in regions:
        C = chunks[r]; m = C.highway.isin(MAIN).to_numpy()
        y = C[label].to_numpy().astype(bool) & m
        idx_pos = np.flatnonzero(y); idx_neg = np.flatnonzero(m & ~y)
        idx_neg = rng.choice(idx_neg, min(len(idx_neg), 20 * len(idx_pos), 150_000), replace=False)
        idx = np.r_[idx_pos, idx_neg]
        L = C.length_m.to_numpy()[idx]
        # each region's positives and negatives carry equal total weight, so no region dominates
        wy = np.where(y[idx], L / L[y[idx]].sum(), L / L[~y[idx]].sum())
        Xs.append(feats(C.iloc[idx])); ys.append(y[idx].astype(float)); ws.append(wy)
    return fit_logit(np.vstack(Xs), np.concatenate(ys), np.concatenate(ws))


ne_s, ne_w = chunks["ne"].score.to_numpy(), chunks["ne"].length_m.to_numpy()
for label, tag in [("byway_osm", "D1 learned from OSM byways"), ("fhwa_sn", "D2 learned from FHWA scenic/natural")]:
    model, coef = train(REGIONS, label)
    print(tag, "coefficients:", dict(zip(["intercept"] + FEATS, np.round(coef, 3))))
    lc = {r: model(feats(chunks[r])) for r in REGIONS}
    anchor = quantile_map(lc["ne"], ne_w, ne_s, ne_w)   # NE's own distribution, so the scale stays absolute
    cands[tag] = {r: dict(chunk=anchor(lc[r]), chunk_nb=anchor(lc[r]), edge=anchor(model(feats(edges[r]))))
                  for r in REGIONS}
    # leave-one-region-out version, for the byway proxy only
    loro = {}
    for r in REGIONS:
        m2, _ = train([q for q in REGIONS if q != r], label)
        loro[r] = m2(feats(chunks[r]))
    cands[tag + " (LORO)"] = {r: dict(chunk=loro[r], chunk_nb=loro[r], edge=None) for r in REGIONS}
# D3: the fair version. Road class is kept out of the learned part (it is what made D1/D2 rate
# interstates 9/10: within trunk-tertiary, bigger roads are likelier byways, and the coefficient
# extrapolates to motorways). The learned logit replaces the blend only; the shipped CLASS_ADJ
# is re-applied through the shipped composite.
FEATS_ALL = FEATS
FEATS = [f for f in FEATS_ALL if f != "score_adj"]
model, coef = train(REGIONS, "byway_osm")
print("D3 coefficients:", dict(zip(["intercept"] + FEATS, np.round(coef, 3))))
ne_raw = chunks["ne"].raw.to_numpy()
lc = {r: model(feats(chunks[r])) for r in REGIONS}
to_raw = quantile_map(lc["ne"], ne_w, ne_raw, ne_w)
def d3(F, logit):
    return composite(to_raw(logit), F.score_adj.to_numpy())
cands["D3 learned blend, shipped class adj"] = {r: dict(chunk=d3(chunks[r], lc[r]), chunk_nb=d3(chunks[r], lc[r]),
                                                     edge=d3(edges[r], model(feats(edges[r])))) for r in REGIONS}
loro = {}
for r in REGIONS:
    m2, _ = train([q for q in REGIONS if q != r], "byway_osm")
    loro[r] = composite(to_raw(m2(feats(chunks[r]))), chunks[r].score_adj.to_numpy())
cands["D3 learned blend, shipped class adj (LORO)"] = {r: dict(chunk=loro[r], chunk_nb=loro[r], edge=None) for r in REGIONS}
FEATS = FEATS_ALL
print("learned", f"{time.time() - t0:.0f}s", flush=True)

# ------------------------------------------------------------ 1. New England marks
D = load_marks()
rows = []
ship_ne = chunks["ne"].score.to_numpy()
km_ne = chunks["ne"].length_m.to_numpy() / 1000
for name, by in cands.items():
    if by["ne"]["edge"] is None:
        continue
    s = mark_values(D, by["ne"]["edge"])
    rep = mark_report(D, s)
    d = by["ne"]["chunk"] - ship_ne
    rep.update(name=name, ne_km_changed_025=100 * km_ne[np.abs(d) > 0.25].sum() / km_ne.sum(),
               ne_km_changed_1=100 * km_ne[np.abs(d) > 1.0].sum() / km_ne.sum(),
               ne_share7=100 * km_ne[by["ne"]["chunk"] >= 7].sum() / km_ne.sum())
    rows.append(rep)
T1 = pd.DataFrame(rows).set_index("name")
y = D.y.to_numpy(); o = (D.batch == "Oct").to_numpy()
print("\n1. NEW ENGLAND MARKS (nulls: all %.3f, Oct %.3f)" % (ceiling(y.sum(), (~y).sum()), ceiling(y[o].sum(), (~y[o]).sum())))
print(T1.round(3).to_string())
T1.to_csv(OUT / "ne_marks.csv")

# ------------------------------------------------------------ 2. byway proxy
rows = []
for name, by in cands.items():
    for r in REGIONS:
        C = chunks[r]; m = C.highway.isin(MAIN).to_numpy(); w = C.length_m.to_numpy()
        s = by[r]["chunk_nb"]
        for lab in ["byway_osm", "fhwa_sn", "fhwa_hc"]:
            yb = C[lab].to_numpy().astype(bool)
            if (yb & m).sum() < 20:
                continue
            rows.append(dict(name=name, region=r, label=lab, auc=wauc(s[m], yb[m], w[m]),
                             auc_eco=wauc_strat(s[m], yb[m], w[m], C.eco.to_numpy()[m]),
                             byway_share7=100 * w[yb & (s >= 7)].sum() / w[yb].sum(),
                             other_share7=100 * w[~yb & (s >= 7)].sum() / w[~yb].sum()))
T2 = pd.DataFrame(rows)
T2.to_csv(OUT / "byway_proxy.csv", index=False)
pd.set_option("display.width", 250)
for v in ["auc", "auc_eco"]:
    print(f"\n2. BYWAY PROXY {v} (trunk-tertiary, byway term removed)")
    print(T2.pivot_table(index="name", columns=["region", "label"], values=v, sort=False).round(3).to_string())

# national pool: does a byway km anywhere outrank a non-byway km anywhere?
rows = []
for name, by in cands.items():
    if "LORO" in name:
        continue
    for lab in ["byway_osm", "fhwa_sn"]:
        S_, Y_, W_ = [], [], []
        for r in REGIONS:
            C = chunks[r]; m = C.highway.isin(MAIN).to_numpy()
            S_.append(by[r]["chunk_nb"][m]); Y_.append(C[lab].to_numpy().astype(bool)[m])
            # each region weighted to equal total km, so New England's size does not decide the pool
            L = C.length_m.to_numpy()[m]; W_.append(L / L.sum())
        rows.append(dict(name=name, label=lab, pooled_auc=wauc(np.concatenate(S_), np.concatenate(Y_), np.concatenate(W_))))
T2b = pd.DataFrame(rows).pivot_table(index="name", columns="label", values="pooled_auc", sort=False)
print("\n2b. NATIONAL POOL (three regions, equal weight, byway term removed)")
print(T2b.round(3).to_string())
T2b.to_csv(OUT / "byway_pooled.csv")

# ------------------------------------------------------------ 3. distributions
GROUPS = {"High Plains": "plains", "Southwestern Tablelands": "plains", "Southern Rockies": "mountains",
          "Wasatch and Uinta Mountains": "mountains", "Colorado Plateaus": "plateau/canyon",
          "Arizona/New Mexico Plateau": "plateau/canyon", "Wyoming Basin": "basin", "Central Basin and Range": "basin",
          "Mojave Basin and Range": "basin", "Northern Basin and Range": "basin"}
rows = []
for name, by in cands.items():
    if "LORO" in name:
        continue
    for r in REGIONS:
        C = chunks[r]; s = by[r]["chunk"]; w = C.length_m.to_numpy()
        grp = C.eco.map(GROUPS).fillna("all-NE" if r == "ne" else "other").to_numpy()
        for g in ["ALL"] + sorted(set(grp)):
            m = np.ones(len(C), bool) if g == "ALL" else grp == g
            if w[m].sum() < 1000e3:
                continue
            rows.append(dict(name=name, region=r, group=g, km=w[m].sum() / 1000,
                             mean=np.average(s[m], weights=w[m]), p50=wq(s[m], w[m], .5),
                             share7=100 * w[m & (s >= 7)].sum() / w[m].sum(),
                             share_le3=100 * w[m & (s < 3)].sum() / w[m].sum()))
T3 = pd.DataFrame(rows)
T3.to_csv(OUT / "distributions.csv", index=False)
print("\n3. DISTRIBUTIONS: share of km >= 7 (%)")
print(T3.pivot_table(index="name", columns=["region", "group"], values="share7", sort=False).round(1).to_string())
print("\n   mean score")
print(T3.pivot_table(index="name", columns=["region", "group"], values="mean", sort=False).round(2).to_string())

# ------------------------------------------------------------ 4. benchmarks
def bm(r):
    C = chunks[r]; nm = C.name.fillna("").str.lower(); ref = C.ref.fillna(""); lon, lat = C.lon, C.lat
    if r == "co":
        return [("scenic", "US 550, all of it in CO", ref.str.contains("US 550")),
                ("scenic", "Million Dollar Hwy (named section)", nm.str.contains("million dollar")),
                ("scenic", "CO 141 Unaweep-Tabeguache", ref.str.fullmatch("CO 141")),
                ("scenic", "Rim Rock Drive", nm.str.fullmatch("rim rock drive")),
                ("scenic", "Trail Ridge Road", nm.str.contains("trail ridge road")),
                ("scenic", "Highway of Legends (CO 12)", ref.str.fullmatch("CO 12")),
                ("scenic", "Kebler Pass Road", nm.str.contains("kebler pass road")),
                ("dull", "I 70 east of Denver", ref.str.contains("I 70") & (lon > -104.6)),
                ("dull", "I 76", ref.str.contains("I 76")),
                ("dull", "US 287 on the plains", ref.str.contains("US 287") & (lon > -103.5)),
                ("dull", "US 385", ref.str.contains("US 385"))]
    if r == "ut":
        return [("scenic", "SR 12 (Scenic Byway 12)", ref.str.fullmatch("SR 12")),
                ("scenic", "Zion-Mount Carmel Hwy", nm.str.contains("zion.mount carmel")),
                ("scenic", "Zion Canyon Scenic Drive", nm.str.contains("zion canyon scenic")),
                ("scenic", "SR 128 (Colorado River)", ref.str.fullmatch("SR 128")),
                ("scenic", "Potash Road (SR 279)", ref.str.fullmatch("SR 279")),
                ("scenic", "Capitol Reef Scenic Drive", nm.str.contains("capitol reef scenic")),
                ("scenic", "Bryce Canyon Scenic Drive", nm.str.contains("bryce canyon scenic")),
                ("scenic", "Logan Canyon Scenic Byway", nm.str.contains("logan canyon scenic")),
                ("scenic", "Mirror Lake Hwy", nm.str.contains("mirror lake highway")),
                ("scenic", "Big Cottonwood Canyon Rd", nm.str.contains("big cottonwood canyon road")),
                ("dull", "I 80 west of Salt Lake", ref.str.contains("I 80") & (lon < -112.3)),
                ("dull", "I 15 through Millard/Juab", ref.str.contains("I 15") & (lat > 38.5) & (lat < 39.8)),
                ("dull", "US 6 Delta-Eureka", ref.str.contains("US 6") & (lon < -112.0) & (lon > -113.0))]
    return [("scenic", "Kancamagus Hwy", nm.str.contains("kancamagus")),
            ("scenic", "Mohawk Trail", nm.str.contains("mohawk trail")),
            ("scenic", "VT 100", ref.str.contains(r"\bVT 100\b")),
            ("scenic", "Route 6A", ref.str.contains("6A")),
            ("dull", "I 90 (Mass Pike)", ref.str.fullmatch("I 90")),
            ("dull", "I 95", ref.str.contains("I 95"))]


rows = []
for r in REGIONS:
    C = chunks[r]; w = C.length_m.to_numpy()
    for kind, lab, mask in bm(r):
        m = mask.to_numpy()
        row = dict(region=r, kind=kind, road=lab, km=w[m].sum() / 1000)
        for name, by in cands.items():
            if "LORO" in name:
                continue
            row[name] = np.average(by[r]["chunk"][m], weights=w[m]) if m.any() else np.nan
        rows.append(row)
T4 = pd.DataFrame(rows)
T4.to_csv(OUT / "benchmarks.csv", index=False)
print("\n4. BENCHMARKS (length-weighted mean score)")
show = ["S0 shipped", "A2 relief cap + recal per state", "B1 +terrain", "E1 terrain+desert+protected", "E1g E1 with grass",
        "C1 percentile per state", "E2 E1 + percentile per state", "D1 learned from OSM byways", "D3 learned blend, shipped class adj"]
print(T4[["region", "kind", "road", "km"] + show].round(1).to_string())

with open(SP / "cands.pkl", "wb") as f:
    pickle.dump({n: {r: by[r]["edge"] for r in REGIONS} for n, by in cands.items() if by["ne"]["edge"] is not None}, f)
print("done", f"{time.time() - t0:.0f}s")
