"""PAD-US 4.1 Fee and Designation polygons inside one bbox, from USGS's public ArcGIS layer.

Usage: padus_rest.py <out.parquet> <west,south,east,north>

The ScienceBase geodatabase that fetch_inputs.sh fetched on 2026-10-12 has since moved behind
ScienceBase's new file manager, whose download link needs a signed-in session (checked
2026-10-18: the old catalog endpoint 404s for the real name and a bogus one alike, and the
manager's API answers UNAUTHENTICATED). USGS also serves the same combined layer
(PADUS4_1ProtMechCat: 656,986 features, the gdb layer's schema) as a public feature service,
and padus.py reads this file in place of the gdb when given it. Same filter as padus.py:
FeatClass Fee or Designation, so the flags are computed from the same rows.
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path
import certifi, ssl
import geopandas as gpd, pandas as pd

URL = ("https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
       "Protection_Mechanism_Category_PADUS/FeatureServer/0/query")
FIELDS = "OBJECTID,FeatClass,Des_Tp,GAP_Sts,Mang_Type,Unit_Nm,State_Nm"
CTX = ssl.create_default_context(cafile=certifi.where())
out, bbox = Path(sys.argv[1]), sys.argv[2]


def get(params):
    q = urllib.parse.urlencode(params).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=q, headers={"User-Agent": "sundaydrive-national-scoring"})
            with urllib.request.urlopen(req, timeout=300, context=CTX) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 -- a retry on anything transient, raised on the last
            if attempt == 4:
                raise
            print("  retry", type(e).__name__, flush=True); time.sleep(5 * 2 ** attempt)


base = dict(where="FeatClass IN ('Fee','Designation')", geometry=bbox, geometryType="esriGeometryEnvelope",
            inSR=4326, spatialRel="esriSpatialRelIntersects")
ids = sorted(get(dict(base, returnIdsOnly="true", f="json"))["objectIds"])
print(len(ids), "polygons in", bbox, flush=True)
parts, t0 = [], time.time()
for i in range(0, len(ids), 500):
    chunk = ids[i:i + 500]
    d = get(dict(objectIds=",".join(map(str, chunk)), outFields=FIELDS, outSR=4326, f="geojson"))
    if not d.get("features"):
        raise SystemExit(f"empty page at {i}: {str(d)[:300]}")
    parts.append(gpd.GeoDataFrame.from_features(d["features"], crs=4326))
    if (i // 500) % 20 == 0:
        print(f"  {i + len(chunk):,} / {len(ids):,}  {time.time() - t0:.0f}s", flush=True)
g = pd.concat(parts, ignore_index=True)
assert len(g) == len(ids) and g.OBJECTID.nunique() == len(ids), "a page came back short"
g.to_parquet(out)
print("wrote", out, len(g), f"{time.time() - t0:.0f}s")
