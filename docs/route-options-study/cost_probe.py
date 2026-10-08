"""Per-request cost of the spliced-options endpoint, against today's /api/route.

Read-only; no server. Times, per sampled trip:
  today    : ROUTER.route(fastest) + ROUTER.route(pref 1) + both .geojson()
             (what /api/route does at pref 1; pref 0.5 costs the same search)
  trees    : forward + reverse pref-0 full Dijkstra (what splicing adds)
  trees_lim: the same with limit = the scenic path's pref-0 cost, which cannot
             change any spliced option (every prefix/suffix of the scenic path
             is a path no cheaper than the tree's answer, so df,db <= limit on it)
  option   : _collect + geojson for one extra spliced route (the scenic one, as
             a stand-in of the same length class)
"""
import json, sys, time
from datetime import date
from pathlib import Path
import numpy as np
import geopandas as gpd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

WT = Path(sys.argv[1]); DATA = Path(sys.argv[2]); OUT = Path(sys.argv[3])
sys.path.insert(0, str(WT / "pipeline")); sys.path.insert(0, str(WT / "tools"))
import router as RT  # noqa
import route_census as RC  # noqa

ON = date(2026, 10, 6)
RC.BANDS = [(10.0, 25.0), (25.0, 50.0), (50.0, 100.0), (100.0, 200.0), (200.0, 350.0)]
places = gpd.read_parquet(DATA / "place_points.parquet")
lat = places.geometry.y.to_numpy(); lon = places.geometry.x.to_numpy()
picked, _ = RC.sample_pairs(lat, lon, 12, seed=20261007)
R = RT.Router(str(DATA))
scores = R._edge_scores({})
w0 = R._weights(0.0, scores, 1.0, ON)
pw0 = np.full(R.n_pairs, np.inf); np.minimum.at(pw0, R.slot_pair, w0)
fin = np.isfinite(pw0)
g0 = csr_matrix((pw0[fin], (R.u_tail[fin], R.u_head[fin])), shape=(R.n, R.n))
g0T = g0.T.tocsr()


def T(f):
    t = time.perf_counter(); out = f(); return time.perf_counter() - t, out


rows = []
for band, plist in picked.items():
    for a, b, gc in plist:
        s, so = R.snap(lat[a], lon[a]); t, to = R.snap_destination(lat[b], lon[b])
        if max(so, to) > 5000 or s == t:
            continue
        targets = R.node_copies.get(t, np.array([t]))
        d_fast, fast = T(lambda: R.route(s, t, 0.0, {}, avoid_unpaved=1.0, on=ON))
        d_scen, scen = T(lambda: R.route(s, t, 1.0, {}, avoid_unpaved=1.0, on=ON))
        if fast is None or scen is None:
            continue
        d_json, _ = T(lambda: (fast.geojson(), scen.geojson()))
        # Upper bound on the scenic path's pref-0 cost (every km charged as dirt),
        # so the cap can only be looser than exact, never tighter.
        w1 = R._weights(1.0, scores, 1.0, ON)
        pw1 = np.full(R.n_pairs, np.inf); np.minimum.at(pw1, R.slot_pair, w1)
        PS = np.asarray(R._dijkstra_path(s, targets, pw1), dtype=np.int64)
        pairs = np.searchsorted(R._pair_key, PS[:-1] * R.n + PS[1:])
        L = float(pw0[pairs].sum()) + 1e-6   # a real path's pref-0 cost: an exact cap
        d_trees, _ = T(lambda: (dijkstra(g0, indices=s),
                                dijkstra(g0T, indices=targets, min_only=True)))
        d_lim, (df, db) = T(lambda: (dijkstra(g0, indices=s, limit=L),
                                     dijkstra(g0T, indices=targets, min_only=True, limit=L)))
        settled = float((np.isfinite(df).mean() + np.isfinite(db).mean()) / 2)
        P = R._dijkstra_path(s, targets, pw0)
        d_opt, _ = T(lambda: R._collect(P, w0, scores).geojson())
        rows.append(dict(band=f"{band[0]:g}-{band[1]:g}", today=d_fast + d_scen + d_json,
                         fast=d_fast, scen=d_scen, json=d_json, trees=d_trees,
                         trees_lim=d_lim, settled=settled, option=d_opt, L=L))
        print(rows[-1]["band"], {k: round(v, 3) for k, v in rows[-1].items() if k != "band"}, flush=True)
(OUT / "cost.json").write_text(json.dumps(rows))
