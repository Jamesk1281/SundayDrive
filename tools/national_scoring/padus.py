"""PAD-US 4.1 designation flags at chunk midpoints.

Usage: padus.py <reg_dir> <state,state,...> [padus_rest.parquet]
With a third argument, the polygons come from padus_rest.py's file (the same layer from USGS's
feature service) instead of the ScienceBase geodatabase, and the state list is not used.
prot_landmark: inside a national park, monument, conservation/recreation/scenic area, lake- or seashore,
               wilderness or wilderness study area, or state park/wilderness (Des_Tp).
prot_landmark_near: within 500 m of one.  prot_gap12: inside GAP status 1-2 land.
prot_public: inside federal or state fee land of any kind.  prot_core = prot_landmark (what c_protected reads).
"""
import os, sys, time
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, pyogrio, shapely
SP = Path(os.environ["NS_WORK"])
G = SP / "padus_x/PADUS4_1Geodatabase.gdb"
LANDMARK = {"NP", "NM", "NCA", "NRA", "NSBV", "NLS", "WA", "WSA", "SP", "SW"}
reg, states = Path(sys.argv[1]), sys.argv[2].split(",")
t0 = time.time()
ch = pd.read_parquet(reg / "chunks.parquet", columns=["lon", "lat"])
where = "State_Nm IN (" + ",".join(f"'{s}'" for s in states) + ")"  # OpenFileGDB returns nothing unless the where-field is also read, and drops rows on AND; filter below
if len(sys.argv) > 3:
    P = gpd.read_parquet(sys.argv[3])
else:
    P = pyogrio.read_dataframe(G, layer="PADUS4_1Combined_Proclamation_Marine_Fee_Designation_Easement",
                               columns=["FeatClass", "Des_Tp", "GAP_Sts", "Mang_Type", "Unit_Nm", "State_Nm"], where=where)
P = P[P.FeatClass.isin(["Fee", "Designation"])].to_crs(5070)
P["geometry"] = shapely.make_valid(P.geometry.values)
pts = gpd.GeoSeries(gpd.points_from_xy(ch.lon, ch.lat), crs=4326).to_crs(5070).values
print(len(P), "polygons", f"{time.time()-t0:.0f}s", flush=True)
out = pd.DataFrame(index=ch.index)
def flag(sel, dist=None):
    g = P.geometry.values[sel]
    tree = shapely.STRtree(g)
    if dist is None:
        hit = tree.query(pts, predicate="intersects")
    else:
        hit = tree.query(pts, predicate="dwithin", distance=dist)
    f = np.zeros(len(pts), bool); f[np.unique(hit[0])] = True
    return f
lm = P.Des_Tp.isin(LANDMARK).values
out["prot_landmark"] = flag(lm)
out["prot_landmark_near"] = flag(lm, 500.0)
out["prot_gap12"] = flag(P.GAP_Sts.isin(["1", "2"]).values)
out["prot_public"] = flag((P.FeatClass == "Fee").values & P.Mang_Type.isin(["FED", "STAT"]).values)
out["prot_core"] = out["prot_landmark"]
out.to_parquet(reg / "padus.parquet")
print(out.mean().round(4).to_dict(), f"{time.time()-t0:.0f}s")
