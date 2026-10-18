"""PAD-US 4.1 landmark polygons for the 48 states and DC, from USGS's public feature service.

Usage: padus_landmarks.py <out.parquet>

protected.py reads the PAD-US geodatabase, and ScienceBase has put that behind a
sign-in since 2026-10-18. tools/national_scoring/padus_rest.py reads the same layer
from USGS's public feature service one region's bbox at a time; this asks it once for
the whole country, and only for the rows protected.py keeps (FeatClass Fee or
Designation, Des_Tp in protected.LANDMARK), so it fetches the landmarks rather than
every polygon. protected.py reads the file in place of the geodatabase.
"""
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import certifi
import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline"))
from protected import FEATURE_CLASSES, LANDMARK  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "us_map_data"))
from scope import LOWER48_BBOX, OUT_ABBR  # noqa: E402

URL = ("https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
       "Protection_Mechanism_Category_PADUS/FeatureServer/0/query")
FIELDS = "OBJECTID,FeatClass,Des_Tp,GAP_Sts,Mang_Type,Unit_Nm,State_Nm"
CTX = ssl.create_default_context(cafile=certifi.where())
PAGE = 200


def get(params):
    q = urllib.parse.urlencode(params).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(URL, data=q, headers={"User-Agent": "sundaydrive-national-build"})
            with urllib.request.urlopen(req, timeout=300, context=CTX) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 -- retried, raised on the last attempt
            if attempt == 5:
                raise
            print("  retry", type(e).__name__, flush=True)
            time.sleep(5 * 2 ** attempt)


def main(out: Path):
    quote = lambda xs: ",".join(f"'{x}'" for x in sorted(xs))
    where = f"FeatClass IN ({quote(FEATURE_CLASSES)}) AND Des_Tp IN ({quote(LANDMARK)})"
    base = dict(where=where, geometry=",".join(map(str, LOWER48_BBOX)),
                geometryType="esriGeometryEnvelope", inSR=4326,
                spatialRel="esriSpatialRelIntersects")
    ids = sorted(get(dict(base, returnIdsOnly="true", f="json"))["objectIds"])
    print(f"{len(ids):,} landmark polygons in {LOWER48_BBOX}", flush=True)
    parts, t0 = [], time.time()
    for i in range(0, len(ids), PAGE):
        chunk = ids[i:i + PAGE]
        d = get(dict(objectIds=",".join(map(str, chunk)), outFields=FIELDS, outSR=4326, f="geojson"))
        if not d.get("features"):
            raise SystemExit(f"empty page at {i}: {str(d)[:300]}")
        parts.append(gpd.GeoDataFrame.from_features(d["features"], crs=4326))
        if (i // PAGE) % 20 == 0:
            print(f"  {i + len(chunk):,} / {len(ids):,}  {time.time() - t0:.0f}s", flush=True)
    g = pd.concat(parts, ignore_index=True)
    if len(g) != len(ids) or g.OBJECTID.nunique() != len(ids):
        raise SystemExit("a page came back short")
    out_of_scope = g["State_Nm"].isin(OUT_ABBR)
    g = g[~out_of_scope].reset_index(drop=True)
    g.to_parquet(out)
    print(f"wrote {out}: {len(g):,} polygons ({int(out_of_scope.sum())} outside the 48 states "
          f"and DC dropped) in {time.time() - t0:.0f}s")
    print(g.groupby("Des_Tp").size().to_string())


if __name__ == "__main__":
    main(Path(sys.argv[1]))
