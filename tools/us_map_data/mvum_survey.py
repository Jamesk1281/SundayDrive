"""The Forest Service Motor Vehicle Use Map roads layer, nationally, by statistics.

No feature is downloaded here. The layer's own JSON gives its schema, and
grouped `outStatistics` queries give miles and segment counts by MVUM symbol,
by the SEASONAL flag, by what a passenger car and a high-clearance vehicle are
allowed, by maintenance level and surface, and by forest. That is enough to say
which fields carry season dates and vehicle class nationally, and how many
forests publish at all (the brief's Trap 7: the layer is published forest by
forest). mvum_osm_match.py does the one-forest comparison against OSM.

Also HEADs the Clearinghouse's national downloads for their sizes, and counts
the ranger districts the layer's own status layer marks as having MVUM data
against all districts.

Everything is restricted to the 48 states (scope.py): the forests outside them,
OUT_FORESTS and Region 10, are left out of every query.

Usage: python -I mvum_survey.py <out_dir>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import get_json, head  # noqa: E402

LAYER = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MVUM_01/MapServer/1"
STATUS = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MVUM_01/MapServer/12"
DISTRICTS = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_RangerDistricts_01/MapServer/0"
OUT_FORESTS = ("Chugach National Forest", "Tongass National Forest", "El Yunque National Forest")
IN_SCOPE = "forestname NOT IN ({})".format(",".join(f"'{f}'" for f in OUT_FORESTS))
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
        "where": IN_SCOPE, "outStatistics": out_stats, "groupByFieldsForStatistics": group,
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
        "where": f"{field} IS NOT NULL AND {IN_SCOPE}", "outStatistics": out_stats,
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
    status, cnt, _ = get_json(LAYER + "/query", {"where": IN_SCOPE, "returnCountOnly": "true",
                                                 "f": "json"})
    res["count"] = cnt.get("count") if cnt else None
    for g in GROUPS:
        res[f"by_{g.split(',')[0]}"] = stats(g)
        print(g, "done", flush=True)
    for f in ("passengervehicle_datesopen", "highclearancevehicle_datesopen"):
        res[f] = sample_dates(f)
    # Districts with MVUM data, from the layer's own status layer, against all.
    pre = "edw.s_usa.BdyAdm_LSRS_RangerDistrict_Gen."
    _, allrd, _ = get_json(DISTRICTS + "/query", {
        "where": "region <> '10'", "outFields": "forestname,districtname",
        "returnGeometry": "false", "resultRecordCount": 2000, "f": "json"}, timeout=120)
    _, avail, _ = get_json(STATUS + "/query", {
        "where": "1=1", "outFields": pre + "forestname," + pre + "districtname",
        "returnGeometry": "false", "resultRecordCount": 2000, "f": "json"}, timeout=120)
    every = {(f["attributes"]["forestname"], f["attributes"]["districtname"])
             for f in (allrd or {}).get("features", [])
             if f["attributes"]["forestname"] not in OUT_FORESTS}
    have = {(f["attributes"][pre + "forestname"], f["attributes"][pre + "districtname"])
            for f in (avail or {}).get("features", [])}
    missing = sorted(every - have)
    forests = {}
    for fo, _ in every:
        forests.setdefault(fo, [0, 0])[0] += 1
    for fo, _ in missing:
        forests[fo][1] += 1
    res["districts"] = {"all": len(every), "with_data": len(every & have),
                        "forests_with_no_district": sorted(f for f, (a, m) in forests.items()
                                                           if a == m),
                        "forests_partly_missing": {f: f"{m} of {a}" for f, (a, m) in
                                                   sorted(forests.items()) if 0 < m < a}}
    res["downloads"] = []
    for u in DOWNLOADS:
        status, size, hdrs = head(u)
        res["downloads"].append({"url": u, "status": status, "bytes": size,
                                 "last_modified": hdrs.get("Last-Modified", "")})
        print(u, status, size, flush=True)
    (out / "mvum_national.json").write_text(json.dumps(res, indent=1))
