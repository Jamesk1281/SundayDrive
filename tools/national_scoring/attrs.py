"""Per-chunk region attributes: NE state, EPA L3 ecoregion, byway labels (OSM state network ids, FHWA by intrinsic quality).

Usage: attrs.py <reg_dir> <region: ne|co|ut> <processed_dir> [byway_way_ids.txt]
Writes <reg_dir>/attrs.parquet.
"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, shapely
SP = Path(os.environ["NS_WORK"])
ROOT = Path(os.environ.get("SUNDAYDRIVE_MAIN", Path(__file__).resolve().parents[2]))
reg, region, proc = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
ch = pd.read_parquet(reg / "chunks.parquet", columns=["lon", "lat", "way_id", "length_m"])
pts = gpd.GeoSeries(gpd.points_from_xy(ch.lon, ch.lat), crs=4326)
out = pd.DataFrame(index=ch.index)
# state
if region == "ne":
    st = np.full(len(ch), None, object)
    for s in ["ma", "me", "nh", "vt"]:
        f = sorted((ROOT / "data/raw/state-roads").glob(f"{s}-tigerweb-state-*.geojson"))[-1]
        poly = gpd.read_file(f).to_crs(4326).union_all()
        inside = shapely.within(pts.values, poly) & pd.isna(st)
        st[inside] = s.upper()
    rest = pd.isna(st)
    st[rest & (ch.lat.values < 42.06) & (ch.lon.values < -71.80)] = "CT"
    st[pd.isna(st) & (ch.lat.values < 42.06)] = "RI"
    out["state"] = pd.Series(st).fillna("other").values
else:
    out["state"] = region.upper()
# ecoregion L3
eco = gpd.read_file(SP / "eco_dl/x/us_eco_l3.shp").to_crs(4326)[["US_L3NAME", "geometry"]]
j = gpd.sjoin(gpd.GeoDataFrame(geometry=pts), eco, how="left", predicate="within")
j = j[~j.index.duplicated()]
out["eco"] = j["US_L3NAME"].reindex(out.index).fillna("none").values
# OSM byway label: full state network (CO) or extract's own flag
sc = pd.read_parquet(reg / "chunks.parquet", columns=["scenic"])["scenic"].astype(bool).values
out["byway_osm_extract"] = sc
if len(sys.argv) > 4:
    ids = set(int(x) for x in open(sys.argv[4]).read().split())
    out["byway_osm"] = ch.way_id.isin(ids).values
else:
    out["byway_osm"] = sc
# FHWA byways, midpoint within 40 m of the national line, split by intrinsic quality
fh = gpd.read_file(SP / "fhwa/byways.geojson").to_crs(32613 if region != "ne" else 32619)
P = pts.to_crs(fh.crs)
for lab, sel in [("fhwa_any", np.ones(len(fh), bool)),
                 ("fhwa_sn", fh.IntrinsicQ.str.contains("S|N").values),
                 ("fhwa_hc", ~fh.IntrinsicQ.str.contains("S|N").values)]:
    g = fh[sel]
    if len(g) == 0:
        out[lab] = False; continue
    tree = shapely.STRtree(g.geometry.values)
    hit = tree.query(P.values, predicate="dwithin", distance=40.0)
    flag = np.zeros(len(ch), bool); flag[np.unique(hit[0])] = True
    out[lab] = flag
    # which byway (first hit) for byway-level stats
    if lab == "fhwa_any":
        first = pd.Series(hit[1], index=hit[0]); first = first[~first.index.duplicated()]
        nm = np.full(len(ch), "", object); nm[first.index.values] = g.NAME.values[first.values]
        out["fhwa_name"] = nm
out.to_parquet(reg / "attrs.parquet")
km = ch.length_m / 1000
print(region, "km by state", km.groupby(out.state).sum().round(0).to_dict())
for c in ["byway_osm_extract", "byway_osm", "fhwa_any", "fhwa_sn", "fhwa_hc"]:
    print(f"  {c}: {km[out[c]].sum():,.0f} km")
print("  top ecoregions by km:", km.groupby(out.eco).sum().sort_values(ascending=False).head(8).round(0).to_dict())
