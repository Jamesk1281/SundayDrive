"""The 60-trip study, re-run through the real endpoint (server/app.py).

Same trips as splice_batch.py / splice_single.py (route_census.sample_pairs,
seed 20261007, five bands, 12 a band). Per trip, timed in one loop so that
other load on the machine moves all of them together:

  scenic : one plain pref-1 Dijkstra over the whole graph, the unit
  today  : POST /api/route pref=0.5, gzip, as the deployed app sends it
  options: POST /api/route pref=0.5&options=1 with SUNDAYDRIVE_ROUTE_OPTIONS on
  detail : POST /api/route with the default option's leave/rejoin (the fetch
           on selection, and the cost of a reroute by legs)

and the menu's quality, scored as compare_single.py scores it: the largest
gap in extra time over the menu, and the share of the full gain bought with a
quarter and a half of the full extra time, over the frontier. Every menu
option is also rebuilt from its switch points and compared with what was
priced (Trap 6 of the brief, docs/route-options.md).

Usage: endpoint_batch.py <worktree> <processed dir> <out dir> [per band]
Read-only against the graph; no server process, Flask's test client.
"""
import json, os, sys, time, traceback
from datetime import date
from pathlib import Path

import numpy as np
import geopandas as gpd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

WT = Path(sys.argv[1]); DATA = Path(sys.argv[2]); OUT = Path(sys.argv[3])
PER_BAND = int(sys.argv[4]) if len(sys.argv) > 4 else 12
os.environ["SUNDAYDRIVE_DATA"] = str(DATA)
os.environ["SUNDAYDRIVE_ROUTE_OPTIONS"] = "1"
sys.path.insert(0, str(WT / "pipeline")); sys.path.insert(0, str(WT / "tools"))
sys.path.insert(0, str(WT / "server"))
import route_census as RC  # noqa
t0 = time.time()
import app as A  # noqa  (loads the graph)
print(f"loaded {time.time() - t0:.0f}s", flush=True)

ON = date(2026, 10, 6)
A._today = lambda: ON
R = A.ROUTER
RC.BANDS = [(10.0, 25.0), (25.0, 50.0), (50.0, 100.0), (100.0, 200.0), (200.0, 350.0)]
places = gpd.read_parquet(DATA / "place_points.parquet")
lat = places.geometry.y.to_numpy(); lon = places.geometry.x.to_numpy()
picked, _ = RC.sample_pairs(lat, lon, PER_BAND, seed=20261007)
client = A.app.test_client()
GZ = {"Accept-Encoding": "gzip"}
scores = R._edge_scores({})


def timed(f):
    t = time.perf_counter(); out = f(); return time.perf_counter() - t, out


def scenic_search(s):
    w = R._weights(1.0, scores, 1.0, ON)
    pw = np.full(R.n_pairs, np.inf); np.minimum.at(pw, R.slot_pair, w)
    g = csr_matrix((pw, (R.u_tail, R.u_head)), shape=(R.n, R.n))
    return dijkstra(g, directed=True, indices=s)


def post(form):
    r = client.post("/api/route", data=form, headers=GZ)
    return r, len(r.get_data())


def run_pair(a, b):
    s, so = R.snap(lat[a], lon[a]); t, to = R.snap_destination(lat[b], lon[b])
    if max(so, to) > 5000:
        return dict(status="snap_far")
    if s == t:
        return dict(status="same_node")
    base = {"from": f"{lat[a]},{lon[a]}", "to": f"{lat[b]},{lon[b]}", "pref": "0.5"}
    t_scen, _ = timed(lambda: scenic_search(s))
    t_today, (r_today, b_today) = timed(lambda: post(base))
    if r_today.status_code != 200:
        return dict(status=f"http{r_today.status_code}")
    t_opt, (r_opt, b_opt) = timed(lambda: post({**base, "options": "1"}))
    body = json.loads(r_opt.get_data() if not r_opt.headers.get("Content-Encoding")
                      else __import__("gzip").decompress(r_opt.get_data()))
    if "options" not in body:
        return dict(status="no_options")
    menu, default = body["options"]["menu"], body["options"]["default"]
    f_bkm = menu[0]["beautiful_km"]
    out = dict(status="ok", t_scenic=t_scen, t_today=t_today, t_options=t_opt,
               bytes_today=b_today, bytes_options=b_opt,
               fastest_min=menu[0]["minutes"], default=default,
               menu=[(o["extra_minutes"], round(o["beautiful_km"] - f_bkm, 1)) for o in menu])
    # The frontier, and the phase timings, straight from the planner.
    tm = {}
    plan = A.route_options.plan(R, s, t, {}, 1.0, on=ON, timings=tm)
    out["frontier"] = [(round(x, 2), round(g, 2)) for x, g in plan.frontier]
    out["phases"] = tm
    out["base"] = plan.base
    if default > 0:
        o = menu[default]
        form = {**base, "pref": "1"}
        for k in ("leave", "rejoin"):
            if o[k] is not None:
                form[k] = f"{o[k]['lat']},{o[k]['lon']},{o[k]['heading']}"
        out["t_detail"], (r_d, _) = timed(lambda: post(form))
    # Every option rebuilt from its switch points.
    bad = []
    for i, o in enumerate(plan.menu[1:], 1):
        pt = lambda sp: None if sp is None else (sp["lat"], sp["lon"], sp["heading"])
        r = A.route_options.spliced_route(R, s, t, pt(o["leave"]), pt(o["rejoin"]),
                                          {}, 1.0, on=ON)
        if (r is None or abs(r.minutes - o["minutes"]) > 0.06
                or abs(r.beautiful_km - o["beautiful_km"]) > 0.06
                or len(set(r.nodes)) != len(r.nodes)):
            bad.append(i)
    out["rebuild_mismatch"] = bad
    return out


rows = open(OUT / "results.jsonl", "w")
n = 0
for band, plist in picked.items():
    for a, b, gc in plist:
        n += 1; t1 = time.time()
        try:
            r = run_pair(a, b)
        except Exception:
            r = dict(status="error", err=traceback.format_exc()[-600:])
        r.update(pair=n, band=f"{band[0]:g}-{band[1]:g}", gc_km=round(gc, 1),
                 secs=round(time.time() - t1, 1))
        rows.write(json.dumps(r) + "\n"); rows.flush()
        print(n, r["band"], r["status"], r.get("t_options"), r.get("rebuild_mismatch"),
              r["secs"], flush=True)
print(f"done {time.time() - t0:.0f}s")
