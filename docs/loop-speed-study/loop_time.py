"""Time /api/loop at whatever checkout this runs from, in units of one plain
pref-1 search timed in the same process. argv: <checkout> <data>"""
import os, sys, time
from datetime import date
WT, DATA = sys.argv[1], sys.argv[2]
os.environ["SUNDAYDRIVE_DATA"] = DATA
sys.path.insert(0, WT + "/pipeline"); sys.path.insert(0, WT + "/server")
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
import app as A
A._today = lambda: date(2026, 10, 8)
R = A.ROUTER; c = A.app.test_client()
def unit():
    w = R._weights(1.0, R._edge_scores({}), 1.0, date(2026, 10, 8))
    pw = np.full(R.n_pairs, np.inf); np.minimum.at(pw, R.slot_pair, w)
    t = time.perf_counter(); dijkstra(csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n)), indices=0); return time.perf_counter() - t
rows = []
for s in ["42.2809,-71.2378", "44.4654,-72.6874", "43.6235,-72.5185"]:
    u = np.median([unit() for _ in range(3)])
    for km in (40, 60):
        t = time.perf_counter(); r = c.post("/api/loop", data={"from": s, "km": str(km)}); d = time.perf_counter() - t
        rows.append((s, km, r.status_code, d, d / u))
for s, km, st, d, x in rows:
    print(f"{s} km={km} {st} {d:.2f}s  {x:.1f} searches")
print("first-from-start median x:", round(float(np.median([x for _, km, _, _, x in rows if km == 40])), 1),
      " new-distance median x:", round(float(np.median([x for _, km, _, _, x in rows if km == 60])), 1))
