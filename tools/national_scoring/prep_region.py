"""Per-region scratch tables: chunk features + the exact chunk->edge averaging map graph.py uses.

Usage: prep_region.py <processed_dir> <out_dir>
Writes chunks.parquet (no geometry; lon/lat/x3857/y3857 midpoints + every column) and edgemap.npz.
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, shapely
from shapely.strtree import STRtree
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline"))
from common import CRS_METERS
from graph import sample_offsets, SAMPLE_STEP_M
d, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
t0 = time.time()
ch = gpd.read_parquet(d / "scored_chunks.parquet").to_crs(CRS_METERS)
mid = ch.geometry.interpolate(0.5, normalized=True)
ll = mid.to_crs(4326); wm = mid.to_crs(3857)
tab = pd.DataFrame(ch.drop(columns="geometry"))
tab["lon"], tab["lat"] = ll.x.values, ll.y.values
tab["x3857"], tab["y3857"] = wm.x.values, wm.y.values
tab.to_parquet(out / "chunks.parquet")
print("chunks", len(tab), f"{time.time()-t0:.0f}s", flush=True)
ed = gpd.read_parquet(d / "graph_edges.parquet")
geoms_m = np.asarray(ed.geometry.to_crs(CRS_METERS).values)
lengths = shapely.length(geoms_m)
row, along, piece = sample_offsets(lengths, SAMPLE_STEP_M)
pts = shapely.line_interpolate_point(geoms_m[row], along)
tree = STRtree(ch.geometry.values)
nearest = tree.query_nearest(pts, all_matches=False)
idx = nearest if nearest.ndim == 1 else nearest[1]
np.savez(out / "edgemap.npz", row=row.astype(np.int32), idx=idx.astype(np.int32), piece=piece.astype(np.float32), n=len(ed))
# self-check: re-averaging a shipped component reproduces graph_edges exactly
n = len(ed); total = np.bincount(row, weights=piece, minlength=n)
for c in ["c_relief", "c_forest", "c_water"]:
    v = np.bincount(row, weights=ch[c].to_numpy()[idx] * piece, minlength=n) / total
    print(c, "max abs diff vs graph_edges", float(np.abs(v - ed[c].to_numpy()).max()), flush=True)
print("edges", n, f"{time.time()-t0:.0f}s")
