"""The national build before and after the scenery additions: share of km at 7 or more,
and mean score, nationally and per state; then the pinned icons and controls.

Usage: national.py <processed_before> <processed_after> <build_before> <build_after> <results_dir>

The two processed directories are stitched national builds (tools/national_build/stitch.py);
each one's per_region.csv gives the row range each region wrote, in region-name order,
which is how an edge is given its state. The two build directories hold the region parts
(<build>/<region>/part_edges.parquet). The icons and controls are the study's pinned roads
(tools/scenery_types/results/pins.csv, roads.py), selected exactly as icons.py selects
them, but scored by the score each build stored rather than recomputed.
Writes <results_dir>/national_states.csv and <results_dir>/national_icons.csv.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapely

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scenery_types"))
from roads import ROADS     # noqa: E402
from pin import inside      # noqa: E402

BEFORE, AFTER, B_BEFORE, B_AFTER, OUT = (Path(a) for a in sys.argv[1:6])
OUT.mkdir(parents=True, exist_ok=True)


def by_state(d):
    t = pq.read_table(d / "graph_edges.parquet", columns=["length_m", "score"]).to_pandas()
    pr = pd.read_csv(d / "per_region.csv")
    pr = pr[pr.region != "total"] if "total" in set(pr.region) else pr
    assert pr.edges.sum() == len(t), "per_region.csv does not cover graph_edges"
    t["state"] = np.repeat(pr.state.to_numpy(), pr.edges.to_numpy())
    return t


rows = []
for label, d in (("before", BEFORE), ("after", AFTER)):
    t = by_state(d)
    km = t.length_m.to_numpy() / 1000
    s = t.score.to_numpy()
    rows.append(dict(build=label, state="US", km=km.sum(), km7=100 * km[s >= 7].sum() / km.sum(),
                     mean=np.average(s, weights=km)))
    for st, g in t.groupby("state"):
        k = g.length_m.to_numpy() / 1000; sc = g.score.to_numpy()
        rows.append(dict(build=label, state=st, km=k.sum(), km7=100 * k[sc >= 7].sum() / k.sum(),
                         mean=np.average(sc, weights=k)))
    del t
R = pd.DataFrame(rows)
W = R.pivot(index="state", columns="build", values=["km7", "mean"])
W.columns = [f"{a}_{b}" for a, b in W.columns]
W["km7_change"] = W.km7_after - W.km7_before
W = W.reset_index()
W.to_csv(OUT / "national_states.csv", index=False, float_format="%.3f")
pd.set_option("display.width", 200)
print(W.sort_values("km7_change", ascending=False).round(2).to_string(index=False))

PINS = pd.read_csv(HERE.parent / "scenery_types" / "results" / "pins.csv")
COLS = ["way_id", "owner", "highway", "length_m", "geometry", "score"]
irows = []
for label, build in (("before", B_BEFORE), ("after", B_AFTER)):
    for r in sorted({r for road in ROADS for r in road["regions"]}):
        t = pq.read_table(build / r / "part_edges.parquet", columns=COLS).to_pandas()
        t = t[(t.owner == r) & t.way_id.isin(set(PINS[PINS.region == r].way_id))].reset_index(drop=True)
        mid = shapely.line_interpolate_point(shapely.from_wkb(t.pop("geometry").to_numpy()), 0.5, normalized=True)
        t["mlon"], t["mlat"] = shapely.get_x(mid), shapely.get_y(mid)
        for road in ROADS:
            if r not in road["regions"]:
                continue
            w = set(PINS[(PINS.road == road["id"]) & (PINS.region == r)].way_id)
            e = t[t.way_id.isin(w) & inside(t, road["bbox"]) & ~t.highway.fillna("").str.endswith("_link")]
            irows.append(e.assign(road=road["id"], kind=road["kind"], build=label)[["road", "kind", "build", "length_m", "score"]])
I = pd.concat(irows, ignore_index=True)
I["km"] = I.length_m / 1000
I["km7"] = I.km * (I.score >= 7)
I["ks"] = I.km * I.score
g = I.groupby(["road", "kind", "build"])[["km", "km7", "ks"]].sum()
g["share7"] = 100 * g.km7 / g.km
g["mean"] = g.ks / g.km
P = g[["km", "share7", "mean"]].unstack("build")
P.columns = [f"{a}_{b}" for a, b in P.columns]
P = P.reset_index()
P.to_csv(OUT / "national_icons.csv", index=False, float_format="%.3f")
print(P.round(2).to_string(index=False))
for kind in ("icon", "control"):
    for label in ("before", "after"):
        m = (I.kind == kind) & (I.build == label)
        print(f"{kind}s {label}: km >= 7 {100 * I.km7[m].sum() / I.km[m].sum():.2f}%")
