"""The Forest Service Motor Vehicle Use Map roads layer, nationally, by statistics.

No feature is downloaded here. The layer's own JSON gives its schema, and
grouped `outStatistics` queries give miles and segment counts by MVUM symbol,
by the SEASONAL flag, by what a passenger car and a high-clearance vehicle are
allowed, by maintenance level and surface, and by forest. That is enough to say
which fields carry season dates and vehicle class nationally, and how many
forests publish at all (the brief's Trap 7: the layer is published forest by
forest). mvum_osm_match.py does the one-forest comparison against OSM.

Also HEADs the Clearinghouse's national downloads for their sizes.

Usage: python -I mvum_survey.py <out_dir>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import get_json, head  # noqa: E402

LAYER = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MVUM_01/MapServer/1"
DOWNLOADS = [
    "https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.Road_MVUM.zip",
    "https://data.fs.usda.gov/geodata/edw/edw_resources/fc/S_USA.Road_MVUM.gdb.zip",
    "https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.RoadCore_FS.zip",
    "https://data.fs.usda.gov/geodata/edw/edw_resources/fc/S_USA.RoadCore_FS.gdb.zip",
    "https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.Road_MVUM_bogus.zip",
]
GROUPS = ["symbol,mvum_symbol_name", "seasonal", "passengervehicle", "highclearancevehicle",
          "operationalmaintlevel", "surfacetype", "jurisdiction", "forestname"]


def stats(group):
    out_stats = json.dumps([
        {"statisticType": "count", "onStatisticField": "objectid", "outStatisticFieldName": "n"},
        {"statisticType": "sum", "onStatisticField": "gis_miles", "outStatisticFieldName": "mi"},
    ])
    status, data, body = get_json(LAYER + "/query", {
        "where": "1=1", "outStatistics": out_stats, "groupByFieldsForStatistics": group,
        "f": "json"}, timeout=180)
    if status != 200 or not data or "features" not in data:
        return {"error": f"HTTP {status}: {body[:300]!r}"}
    rows = [f["attributes"] for f in data["features"]]
    return sorted(rows, key=lambda r: -(r.get("mi") or 0))


def sample_dates(field, n=40):
    """The distinct date strings in a *_datesopen field, with miles."""
    out_stats = json.dumps([{"statisticType": "sum", "onStatisticField": "gis_miles",
                             "outStatisticFieldName": "mi"}])
    status, data, body = get_json(LAYER + "/query", {
        "where": f"{field} IS NOT NULL", "outStatistics": out_stats,
        "groupByFieldsForStatistics": field, "f": "json"}, timeout=180)
    if status != 200 or not data or "features" not in data:
        return {"error": f"HTTP {status}: {body[:300]!r}"}
    rows = sorted((f["attributes"] for f in data["features"]), key=lambda r: -(r["mi"] or 0))
    return {"distinct": len(rows), "top": rows[:n]}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    res = {"layer": LAYER}
    status, meta, _ = get_json(LAYER, {"f": "json"})
    res["fields"] = [f["name"] for f in meta.get("fields", [])]
    res["description"] = meta.get("description", "")
    status, cnt, _ = get_json(LAYER + "/query", {"where": "1=1", "returnCountOnly": "true",
                                                 "f": "json"})
    res["count"] = cnt.get("count") if cnt else None
    for g in GROUPS:
        res[f"by_{g.split(',')[0]}"] = stats(g)
        print(g, "done", flush=True)
    for f in ("passengervehicle_datesopen", "highclearancevehicle_datesopen"):
        res[f] = sample_dates(f)
    res["downloads"] = []
    for u in DOWNLOADS:
        status, size, hdrs = head(u)
        res["downloads"].append({"url": u, "status": status, "bytes": size,
                                 "last_modified": hdrs.get("Last-Modified", "")})
        print(u, status, size, flush=True)
    (out / "mvum_national.json").write_text(json.dumps(res, indent=1))
