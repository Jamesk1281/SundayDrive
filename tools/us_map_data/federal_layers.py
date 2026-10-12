"""Four federal road layers, counted for the contiguous 48 + DC by statistics queries.

No feature is downloaded. Each layer is asked for grouped counts (and miles
where it has them), restricted to the contiguous US: by state field where the
layer has one, by the scope.py envelope where it does not.

  tigerweb   Census TIGERweb local roads, segments by MTFCC (S1500 4WD trail,
             S1740 private service road, S1400 local road, ...)
  nps        NPS Public Roads: segments by SEASONAL and RDHICLEAR
  blm        BLM GTLF roads for public and limited public motorized use: miles by
             route-use class and seasonal-restriction code
  byways     FHWA America's Byways: records by designation

Usage: python -I federal_layers.py <out.json>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import get_json  # noqa: E402
from scope import LOWER48_BBOX, OUT_ABBR  # noqa: E402

TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Transportation/MapServer/8"
NPS = "https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/NPS_Public_Roads/MapServer/0"
BLM = "https://gis.blm.gov/arcgis/rest/services/transportation/BLM_Natl_GTLF_Public_Display/MapServer"
BYWAYS = ("https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/"
          "FHWA_ScenicByways_08042026_gdb/FeatureServer/0")
ENVELOPE = {"geometry": ",".join(str(v) for v in LOWER48_BBOX),
            "geometryType": "esriGeometryEnvelope", "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects"}
OUT_LIST = ",".join(f"'{a}'" for a in sorted(OUT_ABBR))


def grouped(url, group, stats, where="1=1", spatial=None, timeout=300):
    params = {"where": where, "outStatistics": json.dumps(stats),
              "groupByFieldsForStatistics": group, "f": "json", **(spatial or {})}
    status, data, body = get_json(url + "/query", params, timeout=timeout, tries=2)
    if status != 200 or not data or "features" not in data:
        return {"error": f"HTTP {status}: {body[:200]!r}"}
    return sorted((f["attributes"] for f in data["features"]),
                  key=lambda a: -max(v for v in a.values() if isinstance(v, (int, float))))


def count(field="OBJECTID"):
    return {"statisticType": "count", "onStatisticField": field, "outStatisticFieldName": "n"}


def miles(field):
    return {"statisticType": "sum", "onStatisticField": field, "outStatisticFieldName": "mi"}


if __name__ == "__main__":
    out = {"scope": "contiguous 48 + DC", "envelope": LOWER48_BBOX}
    out["tigerweb_by_mtfcc"] = grouped(TIGERWEB, "MTFCC", [count()], spatial=ENVELOPE)
    print("tigerweb done", flush=True)
    out["nps_by_seasonal"] = grouped(NPS, "SEASONAL", [count()], spatial=ENVELOPE)
    out["nps_by_highclearance"] = grouped(NPS, "RDHICLEAR", [count()], spatial=ENVELOPE)
    print("nps done", flush=True)
    for layer, name in ((0, "public"), (1, "limited")):
        for g in ("OBSRVE_ROUTE_USE_CLASS", "PLAN_SEASON_RSTRCT_CODE"):
            out[f"blm_{name}_by_{g.lower()}"] = grouped(
                f"{BLM}/{layer}", g, [count(), miles("GIS_MILES")],
                where=f"ADMIN_ST NOT IN ({OUT_LIST})")
    print("blm done", flush=True)
    out["byways_by_designation"] = grouped(BYWAYS, "Current_Desig", [count()],
                                           where=f"STATE NOT IN ({OUT_LIST})")
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:3000])
