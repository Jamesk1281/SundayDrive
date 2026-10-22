"""Distance to the nearest PAD-US landmark polygon, for candidate L.

Usage: landmarks.py <work_dir>
Reads data/national/inputs/padus_landmarks.parquet (the national build's own landmark
polygons, read-only) and writes d_landmark (m, EPSG:5070, capped at 1,000 m; 0 inside):
  <work_dir>/icons_landmark.parquet        icon and control pieces, piece order
  <work_dir>/fl_landmark.parquet           Florida pieces
  <work_dir>/reg/<r>/st_landmark.parquet   New England, Colorado, Utah chunks
"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, shapely

WORK = Path(sys.argv[1])
MAIN = Path(os.environ.get("SUNDAYDRIVE_MAIN", Path(__file__).resolve().parents[2]))
CAP = 1000.0
L = gpd.read_parquet(MAIN / "data" / "national" / "inputs" / "padus_landmarks.parquet").to_crs(5070)
polys = shapely.get_parts(L.geometry.to_numpy())
tree = shapely.STRtree(polys)


def dist(lon, lat):
    pts = gpd.GeoSeries(gpd.points_from_xy(lon, lat), crs=4326).to_crs(5070).to_numpy()
    d = np.full(len(pts), np.inf)
    for s in range(0, len(pts), 200_000):
        p = pts[s:s + 200_000]
        (i, _), dd = tree.query_nearest(p, max_distance=CAP, return_distance=True, all_matches=False)
        d[s + i] = dd
    return d


P = pd.read_parquet(WORK / "icons_pieces.parquet", columns=["lon", "lat"])
pd.DataFrame({"d_landmark": dist(P.lon, P.lat)}).to_parquet(WORK / "icons_landmark.parquet")
P = pd.read_parquet(WORK / "fl_pieces.parquet", columns=["lon", "lat"])
pd.DataFrame({"d_landmark": dist(P.lon, P.lat)}).to_parquet(WORK / "fl_landmark.parquet")
for r in ("ne", "co", "ut"):
    C = pd.read_parquet(WORK / "reg" / r / "chunks.parquet", columns=["lon", "lat"])
    d = dist(C.lon, C.lat)
    pd.DataFrame({"d_landmark": d}).to_parquet(WORK / "reg" / r / "st_landmark.parquet")
    print(r, "chunks inside / within 80 m:", int((d == 0).sum()), int((d <= 80).sum()), flush=True)
print("done")
