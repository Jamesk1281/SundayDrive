"""RSS growth of the Router's main components, step by step, plus array totals."""
import os, sys, gc
sys.path.insert(0, sys.argv[1])
proc = sys.argv[2]
def rss(): return int(os.popen(f"ps -o rss= -p {os.getpid()}").read()) / 1e6
import numpy as np, pandas as pd, geopandas as gpd, shapely
from shapely.strtree import STRtree
import router
from common import CRS_METERS
r0 = rss(); print(f"libs imported: {r0:.2f} GB")
e = gpd.read_parquet(f"{proc}/graph_edges.parquet"); r1 = rss()
print(f"graph_edges GeoDataFrame ({len(e):,} rows, {shapely.get_num_coordinates(e.geometry.values).sum():,} coords): +{r1-r0:.2f} GB")
strcols = [c for c in e.columns if e[c].dtype == object and c != 'geometry']
print(f"   of which string columns {strcols}: {e[strcols].memory_usage(deep=True).sum()/1e9:.2f} GB")
gm = e.geometry.to_crs(CRS_METERS).values; r2 = rss(); print(f"projected copy of geometry: +{r2-r1:.2f} GB")
tree = STRtree(gm); r3 = rss(); print(f"STRtree over edges: +{r3-r2:.2f} GB")
del e, gm, tree; gc.collect()
R = router.Router(proc); r4 = rss(); print(f"full Router: {r4:.2f} GB total")
arrs = 0; big = []
for k, v in R.__dict__.items():
    if isinstance(v, np.ndarray):
        arrs += v.nbytes; big.append((v.nbytes, k))
print(f"numpy arrays on the Router: {arrs/1e9:.2f} GB; largest: " + ", ".join(f"{k} {b/1e6:.0f} MB" for b, k in sorted(big, reverse=True)[:10]))
print("dict/list attributes:", ", ".join(f"{k}({len(v):,})" for k, v in R.__dict__.items() if isinstance(v, (dict, list)) and len(v) > 10000))
print("other big attributes:", ", ".join(f"{k}:{type(v).__name__}" for k, v in R.__dict__.items() if isinstance(v, (pd.DataFrame, gpd.GeoDataFrame, STRtree))))
