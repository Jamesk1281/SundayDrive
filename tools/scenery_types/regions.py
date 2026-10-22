"""Features for whole regions: the marks and the byway proxy.

Usage: regions.py <work_dir> ne|co|ut|fl
ne, co, ut: the chunk tables tools/national_scoring built ($NS_WORK/reg/<r>/chunks.parquet,
            with wc.parquet already there). Writes st_dem.parquet and st_coast.parquet beside them.
fl:         no chunk table survives the national build, so Florida's owned edges
            (data/national/build/fl/part_edges.parquet) are cut into pieces as icons.py does.
            Writes fl_edges.parquet (shipped components, ecoregion, FHWA labels) and
            fl_pieces.parquet (features). FHWA lines: $NS_WORK/fhwa/fl.geojson.
One region per run, so only one mosaic is ever in memory.
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, pyarrow.parquet as pq, shapely
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pin import BUILD
from cands import BASE
import feat_lib as FL

WORK, region = Path(sys.argv[1]), sys.argv[2]
t0 = time.time()


def log(*a):
    print(*a, f"{time.time() - t0:.0f}s", flush=True)


if region in ("ne", "co", "ut"):
    reg = WORK / "reg" / region
    ch = pd.read_parquet(reg / "chunks.parquet", columns=["lon", "lat"])
    bbox = (ch.lon.min(), ch.lat.min(), ch.lon.max(), ch.lat.max())
    dem, info = FL.dem_features(ch.lon.to_numpy(), ch.lat.to_numpy(), bbox)
    dem.drop(columns="z").to_parquet(reg / "st_dem.parquet")
    log(region, "dem", info)
    d = np.full(len(ch), np.inf)
    if region == "ne":
        c = gpd.read_parquet(FL.MAIN / "data" / "processed-ne" / "coastline.parquet").to_crs(4326)
        d = FL.coast_distance(ch.lon.to_numpy(), ch.lat.to_numpy(), c.geometry.to_numpy())
    pd.DataFrame({"d_coast": d}).to_parquet(reg / "st_coast.parquet")
    log(region, "coast: chunks within 350 m", int((d <= 350).sum()))
    sys.exit()

assert region == "fl"
cols = ["way_id", "owner", "ref", "name", "highway", "length_m", "geometry", "score_adj", "score"] + BASE
E = pq.read_table(BUILD / "fl" / "part_edges.parquet", columns=cols).to_pandas()
E = E[E.owner == "fl"].reset_index(drop=True)
g = shapely.from_wkb(E.pop("geometry").to_numpy())
mid = shapely.line_interpolate_point(g, 0.5, normalized=True)
E["mlon"], E["mlat"] = shapely.get_x(mid), shapely.get_y(mid)
log("edges", len(E))
# labels, as attrs.py: EPA L3 ecoregion at the midpoint; FHWA byway if the midpoint is within 40 m
eco = gpd.read_file(WORK / "eco_dl" / "x" / "us_eco_l3.shp").to_crs(4326)[["US_L3NAME", "geometry"]]
pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(E.mlon, E.mlat), crs=4326)
j = gpd.sjoin(pts, eco, how="left", predicate="within"); j = j[~j.index.duplicated()]
E["eco"] = j["US_L3NAME"].reindex(E.index).fillna("none").to_numpy()
fh = gpd.read_file(WORK / "fhwa" / "fl.geojson").to_crs(32617)
P17 = pts.to_crs(32617).geometry.to_numpy()
for lab, sel in [("fhwa_any", np.ones(len(fh), bool)), ("fhwa_sn", fh.IntrinsicQ.str.contains("S|N").to_numpy())]:
    tree = shapely.STRtree(fh[sel].geometry.to_numpy())
    hit = tree.query(P17, predicate="dwithin", distance=40.0)
    flag = np.zeros(len(E), bool); flag[np.unique(hit[0])] = True
    E[lab] = flag
E.to_parquet(WORK / "fl_edges.parquet")
log("labels: fhwa_sn km", round(E.length_m[E.fhwa_sn].sum() / 1000))

n = np.maximum(1, np.ceil(E.length_m.to_numpy() / 400.0)).astype(int)
row = np.repeat(np.arange(len(E)), n)
k = np.arange(len(row)) - np.repeat(np.cumsum(n) - n, n)
p = shapely.line_interpolate_point(g[row], (k + 0.5) / np.repeat(n, n), normalized=True)
del g
P = pd.DataFrame({"edge": row, "piece": (E.length_m.to_numpy() / n)[row], "lon": shapely.get_x(p), "lat": shapely.get_y(p)})
del p
log("pieces", len(P))
bbox = (P.lon.min(), P.lat.min(), P.lon.max(), P.lat.max())
dem, info = FL.dem_features(P.lon.to_numpy(), P.lat.to_numpy(), bbox)
log("dem", info)
wc, absent = FL.wc_features(P.lon.to_numpy(), P.lat.to_numpy())
log("wc absent (water)", absent)
lines = FL.coastline_lines("fl")
P["d_coast"] = FL.coast_distance(P.lon.to_numpy(), P.lat.to_numpy(), lines)
log("coast lines", len(lines))
pd.concat([P, dem.drop(columns="z"), wc[[c for c in wc.columns if c.endswith("_1k")]]], axis=1).to_parquet(WORK / "fl_pieces.parquet")
log("done")
