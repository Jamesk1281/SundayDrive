import sys, time, cProfile, pstats, io
sys.path.insert(0, "pipeline")
from datetime import date
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
import router as RT, looper as LP
R = RT.Router("data/processed-ne"); ON = date(2026, 10, 8)
P = LP.LoopPlanner(R)
s, _ = R.snap(42.2809, -71.2378)
P.plan(R.snap(44.4654, -72.6874)[0], 40.0, 1.0, {}, on=ON)   # warm the cost model
w = R._weights(1.0, R._edge_scores({}), 1.0, ON); pw = np.full(R.n_pairs, np.inf); np.minimum.at(pw, R.slot_pair, w)
g = csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n))
t = time.perf_counter(); dijkstra(g, indices=s); unit = time.perf_counter() - t
pr = cProfile.Profile(); pr.enable()
t0 = time.perf_counter(); loop = P.plan(s, 40.0, 1.0, {}, on=ON); t_first = time.perf_counter() - t0
t0 = time.perf_counter(); P.plan(s, 60.0, 1.0, {}, on=ON); t_new = time.perf_counter() - t0
pr.disable()
print(f"unit (one full search) {unit:.3f}s; first loop {t_first:.2f}s = {t_first/unit:.1f} units; new distance {t_new:.2f}s = {t_new/unit:.1f} units")
st = pstats.Stats(pr); st.sort_stats("cumulative")
out = io.StringIO(); st.stream = out; st.print_stats("looper.py|dijkstra|_collect|minimum|isin|csr_matrix|_accumulate", 25); print(out.getvalue()[-4000:])
