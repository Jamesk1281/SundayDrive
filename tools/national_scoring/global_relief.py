"""Trap 5 measured: raise RELIEF_FULL for everyone (no per-region constants) and watch New England."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *  # noqa
from candidates import build
REGIONS = ["ne", "co", "ut"]
chunks = {r: load_chunks(r) for r in REGIONS}
edges = {r: load_edges(r, chunks[r]) for r in REGIONS}
spec = {f"RELIEF_FULL={v:.0f}": (dict(relief_full=float(v)), None) for v in (100, 150, 175, 250)}
out, _ = build(REGIONS, chunks, edges, spec)
D = load_marks(); rows = []
for name in spec:
    rep = mark_report(D, mark_values(D, out[name]["ne"]["edge"]))
    rec = dict(name=name, ne_all=rep["all"], ne_oct=rep["oct"], ne_prec7=rep["prec7"], ne_n7=rep["n7"])
    for r in REGIONS:
        C = chunks[r]; m = C.highway.isin(MAIN).to_numpy(); w = C.length_m.to_numpy(); s = out[name][r]["chunk_nb"]
        yb = C.fhwa_sn.to_numpy().astype(bool)
        rec[f"{r}_fhwa_sn"] = wauc(s[m], yb[m], w[m]); rec[f"{r}_fhwa_sn_eco"] = wauc_strat(s[m], yb[m], w[m], C.eco.to_numpy()[m])
        rec[f"{r}_share7"] = 100 * w[out[name][r]["chunk"] >= 7].sum() / w.sum()
    rows.append(rec)
T = pd.DataFrame(rows); pd.set_option("display.width", 250)
print(T.round(3).to_string(index=False)); T.to_csv(sys.argv[1], index=False)
