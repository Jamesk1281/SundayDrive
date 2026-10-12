"""E1's hand-set constants swept (not fitted), and the pinned-relief test.

Pinned-relief test: among trunk-tertiary chunks whose c_relief is at the cap, does the score
(byway term removed) still separate byways? This is the "relief can't rank mountain roads" claim.
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import core
from core import *  # noqa
import candidates as K
REGIONS = ["ne", "co", "ut"]
chunks = {r: load_chunks(r) for r in REGIONS}
edges = {r: load_edges(r, chunks[r]) for r in REGIONS}
D = load_marks()
rows = []
def run(tag, G0, G1, WG, WP, land="desert"):
    core.G0, core.G1 = G0, G1; K.W_GRAND, K.W_PROT = WG, WP
    spec = {"S0": (dict(), None), tag: (dict(grand=WG > 0, land=land, prot=WP > 0), None)}
    out, _ = K.build(REGIONS, chunks, edges, spec)
    for name in spec:
        rec = dict(name=name if name != "S0" else "S0 shipped", G0=G0, G1=G1, W_GRAND=WG, W_PROT=WP, land=land)
        rec.update({f"ne_{k}": v for k, v in mark_report(D, mark_values(D, out[name]["ne"]["edge"])).items() if k in ("all", "oct", "prec7", "n7")})
        ne_d = out[name]["ne"]["chunk"] - chunks["ne"].score.to_numpy(); kmne = chunks["ne"].length_m.to_numpy()
        rec["ne_km_moved_025_pct"] = 100 * kmne[np.abs(ne_d) > .25].sum() / kmne.sum()
        for r in REGIONS:
            C = chunks[r]; m = C.highway.isin(MAIN).to_numpy(); w = C.length_m.to_numpy(); s = out[name][r]["chunk_nb"]
            pin = m & (C.c_relief.to_numpy() >= 0.999)
            for lab in ("byway_osm", "fhwa_sn"):
                yb = C[lab].to_numpy().astype(bool)
                rec[f"{r}_{lab}_eco"] = wauc_strat(s[m], yb[m], w[m], C.eco.to_numpy()[m])
                rec[f"{r}_{lab}_pinned"] = wauc(s[pin], yb[pin], w[pin]) if (yb & pin).sum() > 20 else np.nan
            rec[f"{r}_share7"] = 100 * w[out[name][r]["chunk"] >= 7].sum() / w.sum()
            rec[f"{r}_pinned_byway_km_pct"] = 100 * w[pin & C.byway_osm.to_numpy()].sum() / max(w[m & C.byway_osm.to_numpy()].sum(), 1)
        rows.append(rec)
run("E1 as specified", 300, 900, .10, .07)
for G0 in (200, 400):
    run(f"G0={G0}", G0, 900, .10, .07)
for G1 in (600, 1200):
    run(f"G1={G1}", 300, G1, .10, .07)
for WG in (.05, .20):
    run(f"W_GRAND={WG}", 300, 900, WG, .07)
for WP in (0.0, .14):
    run(f"W_PROT={WP}", 300, 900, .10, WP)
run("no desert", 300, 900, .10, .07, land=None)
T = pd.DataFrame(rows).drop_duplicates(subset=[c for c in pd.DataFrame(rows).columns if c not in ("G0", "G1", "W_GRAND", "W_PROT", "land")] )
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)
cols = ["name", "ne_all", "ne_oct", "ne_prec7", "ne_km_moved_025_pct", "co_byway_osm_eco", "co_fhwa_sn_eco", "ut_byway_osm_eco", "ut_fhwa_sn_eco",
        "co_byway_osm_pinned", "co_fhwa_sn_pinned", "ut_byway_osm_pinned", "ut_fhwa_sn_pinned", "ne_share7", "co_share7", "ut_share7"]
print(T[cols].round(3).to_string())
print("pinned byway km %:", {r: round(T.iloc[0][f"{r}_pinned_byway_km_pct"], 1) for r in REGIONS})
T.to_csv(sys.argv[1], index=False)
