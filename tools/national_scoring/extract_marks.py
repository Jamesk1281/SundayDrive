"""PRIVATE OUTPUT: the pickle this writes locates every mark. Write it under NS_WORK, never into the repo.

Resolve every mark in traces/ to the graph edges under its window, keep per-sample edge ids.

Uses analyze_trace's own load/segments/marks so attribution is identical to the
shipped instrument; only the snapping is re-done here so per-sample edge indices
(and therefore every component, not just `score`) are kept.
"""
import sys, glob, json
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from shapely import STRtree
from shapely.geometry import LineString

import os
REPO = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("SUNDAYDRIVE_MAIN", REPO))   # data/ and traces/ live only in the main checkout
sys.path.insert(0, str(REPO / "tools")); sys.path.insert(0, str(REPO / "pipeline"))
import analyze_trace as at
from common import CRS_METERS

OUT = Path(sys.argv[1])
edges = gpd.read_parquet(ROOT / "data/processed-ne/graph_edges.parquet")
edges = edges.to_crs(CRS_METERS).reset_index(drop=True)
geom = edges.geometry.values
tree = STRtree(geom)
print("edges", len(edges), flush=True)

rows = []
for path in sorted(glob.glob(str(ROOT / "traces/*.ndjson"))):
    recs = at.load(path)
    header = next((r for r in recs if r["t"] == "drive"), {})
    parts = at.segments(recs)
    lines = {}
    for route, _ in parts:
        c = route.get("coords") or []
        if len(c) >= 2:
            lines[int(route["seq"])] = LineString(
                gpd.points_from_xy([p[0] for p in c], [p[1] for p in c], crs=4326).to_crs(CRS_METERS))
    for window in (200.0, 400.0, 800.0):
        for reaction in ((0.0, 3.0, 6.0) if window == 400.0 else (3.0,)):
            m = at.marks(recs, window_m=window, reaction_s=reaction)
            for r in m.itertuples():
                line = lines.get(r.seq)
                ids = []
                if line is not None:
                    lo = min(max(0.0, r.lo_m), line.length); hi = min(max(lo, r.hi_m), line.length)
                    n = max(2, int(np.ceil((hi - lo) / at.MARK_SAMPLE_M)) + 1)
                    pts = [line.interpolate(d) for d in np.linspace(lo, hi, n)]
                    near = tree.nearest(pts)
                    dist = np.array([geom[i].distance(p) for i, p in zip(near, pts)])
                    ids = [int(i) for i in near[dist <= at.MAX_SNAP_M]]
                rows.append(dict(drive=Path(path).stem, pref=header.get("pref"),
                                 weights=json.dumps(header.get("weights")),
                                 window=window, reaction=reaction, ts=r.ts, verdict=r.verdict,
                                 lat=r.lat, lon=r.lon, speed=r.speed_ms, edge_ids=ids))
    print(Path(path).name, "done", flush=True)

df = pd.DataFrame(rows)
df.to_pickle(OUT)
print(df.groupby(["window", "reaction"]).verdict.value_counts().unstack())
