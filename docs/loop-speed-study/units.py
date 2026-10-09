"""LoopPlanner cost per request kind, in units of one plain pref-1 full-graph
Dijkstra timed in the same process (so machine load cancels).

argv: <checkout> <data>. Run once at the base commit (a `git archive` of
pipeline/ is enough) and once at the change.

One planner for the whole run, warmed once, the way the server holds one:
one-time costs (the cost model, the pair order `_disc` sorts once) are paid
before timing. Per start, with the field cache cleared first:
  first   plan + sectors at 40 km, the first loop from a new start
  longer  60 km after 40, a new distance up the slider
  shorter 25 km after 60, a new distance down it
  compass the same 25 km in another offered sector
  rejoin  `resume` from a tenth of the way round, through the turnaround, home
and first loops at 10, 80, 150 and 300 km, each from a cleared cache.
"""
import sys, time
from datetime import date
import numpy as np

WT, DATA = sys.argv[1], sys.argv[2]
sys.path.insert(0, WT + "/pipeline")
from scipy.sparse import csr_matrix                                 # noqa: E402
from scipy.sparse.csgraph import dijkstra                           # noqa: E402
import router as RT, looper as LP                                   # noqa: E402

ON = date(2026, 10, 8)
R = RT.Router(DATA)
w = R._weights(1.0, R._edge_scores({}), 1.0, ON)
pw = np.full(R.n_pairs, np.inf); np.minimum.at(pw, R.slot_pair, w)
G = csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n))


def unit():
    ts = []
    for _ in range(3):
        t = time.perf_counter(); dijkstra(G, indices=0)
        ts.append(time.perf_counter() - t)
    return float(np.median(ts))


STARTS = {"Needham": (42.2809, -71.2378), "Boston": (42.3601, -71.0589),
          "Stowe": (44.4654, -72.6874), "Woodstock": (43.6235, -72.5185),
          "Petersham": (42.4890, -72.1890), "Bar Harbor": (44.3876, -68.2039),
          "Greenville": (45.4595, -69.5906), "Hartford": (41.7658, -72.6734),
          "Chatham": (41.6821, -69.9598), "Jackson": (44.1464, -71.1856),
          "Providence": (41.8240, -71.4128), "Portland": (43.6591, -70.2568)}

P = LP.LoopPlanner(R)
P.plan(R.snap(44.4654, -72.6874)[0], 40.0, on=ON)        # one-time costs


def timed(f):
    u = unit()
    t = time.perf_counter(); out = f(); d = time.perf_counter() - t
    return out, d / u


def clear():
    P._fields_by_key.clear()


kinds = ["first", "longer", "shorter", "compass", "rejoin",
         "first@10", "first@80", "first@150", "first@300"]
table = {k: [] for k in kinds}
for name, ll in STARTS.items():
    s = R.snap(*ll)[0]
    clear()
    loop, x = timed(lambda: (P.plan(s, 40.0, on=ON), P.sectors(s, 40.0, on=ON))[0])
    table["first"].append(x)
    _, x = timed(lambda: (P.plan(s, 60.0, on=ON), P.sectors(s, 60.0, on=ON)))
    table["longer"].append(x)
    _, x = timed(lambda: (P.plan(s, 25.0, on=ON), P.sectors(s, 25.0, on=ON)))
    table["shorter"].append(x)
    offered = sorted(P.sectors(s, 25.0, on=ON).items(), key=lambda kv: -kv[1])
    sector = offered[-1][0] if offered else None
    _, x = timed(lambda: P.plan(s, 25.0, sector=sector, on=ON))
    table["compass"].append(x)
    nodes = loop.route.nodes
    src = int(nodes[len(nodes) // 10])
    _, x = timed(lambda: P.resume(src, loop.turnaround_idx, s, on=ON))
    table["rejoin"].append(x)
    for km in (10.0, 80.0, 150.0, 300.0):
        clear()
        _, x = timed(lambda: (P.plan(s, km, on=ON), P.sectors(s, km, on=ON)))
        table[f"first@{km:.0f}"].append(x)
    print(f"{name:11s}", " ".join(f"{k}={table[k][-1]:.2f}" for k in kinds),
          flush=True)

print("\nmedian " + " ".join(f"{k}={np.median(v):.2f}" for k, v in table.items()))
print("mean   " + " ".join(f"{k}={np.mean(v):.2f}" for k, v in table.items()))
print("max    " + " ".join(f"{k}={np.max(v):.2f}" for k, v in table.items()))
for attr in ("disc_passes", "disc_refines", "disc_fallbacks", "full_passes"):
    if hasattr(P, attr):
        print(attr, getattr(P, attr))
