"""One national forest's MVUM roads against OSM: coverage, roughness, seasons.

Fetches the forest's Motor Vehicle Use Map roads from the national layer (one
forest, paged, WGS84), reads every `highway=*` way inside its box from the
state PBF, and matches the two by osm_match.py's sampling rule. That gives, by
km of MVUM road:

  - what OSM has there: a road graph.py keeps, one closures.py closes all
    year, a `highway=track` the graph leaves out, something else, or nothing;
  - for the roads the graph keeps, MVUM's maintenance level (2 = "high
    clearance vehicles", 3+ = passenger cars) against whatever OSM says about
    roughness (`4wd_only`, `smoothness`, `tracktype`, an unpaved `surface`);
  - for MVUM's seasonal roads, whether closures.py closes the OSM way, whether
    OSM carries any seasonal or conditional tag it does not read, or nothing.

Usage: python -I mvum_osm_match.py <repo_pipeline_dir> <state.osm.pbf> <forest name>
                                   <cache.geojson> <out.json>
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import get_json  # noqa: E402
from osm_match import SAMPLE_M, TOLERANCE_M, matcher, osm_ways  # noqa: E402

LAYER = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MVUM_01/MapServer/1"
FIELDS = ("id,name,symbol,mvum_symbol_name,seasonal,passengervehicle,"
          "passengervehicle_datesopen,highclearancevehicle_datesopen,"
          "operationalmaintlevel,surfacetype,jurisdiction,gis_miles")


def fetch(forest, cache):
    if Path(cache).exists():
        return json.loads(Path(cache).read_text())
    feats, offset = [], 0
    while True:
        status, data, body = get_json(LAYER + "/query", {
            "where": f"forestname = '{forest}'", "outFields": FIELDS, "outSR": 4326,
            "f": "geojson", "resultOffset": offset, "resultRecordCount": 500,
            "orderByFields": "objectid"}, timeout=180)
        if status != 200 or not data:
            raise SystemExit(f"MVUM query failed: HTTP {status} {body[:300]!r}")
        feats += data.get("features", [])
        print(f"  {len(feats)} MVUM features", flush=True)
        if len(data.get("features", [])) < 500:
            break
        offset += 500
    fc = {"type": "FeatureCollection", "features": feats}
    Path(cache).write_text(json.dumps(fc))
    return fc


def main():
    pbf, forest, cache, out = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
    fc = fetch(forest, cache)
    lines, attrs = [], []
    for f in fc["features"]:
        g = f.get("geometry")
        if not g:
            continue
        parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for p in parts:
            if len(p) >= 2:
                lines.append(p)
                attrs.append(f["properties"])
    allx = [x for p in lines for x, _ in p]
    ally = [y for p in lines for _, y in p]
    bbox = (min(allx) - 0.02, min(ally) - 0.02, max(allx) + 0.02, max(ally) + 0.02)
    print(f"{len(lines)} MVUM lines, bbox {tuple(round(v, 3) for v in bbox)}", flush=True)
    ways = osm_ways(pbf, bbox)
    print(f"{len(ways)} OSM highway ways in the box", flush=True)
    match = matcher(ways)
    tab = defaultdict(float)
    total = 0.0
    for p, a in zip(lines, attrs):
        km_each, hit = match(p)
        ml = (a.get("operationalmaintlevel") or "").strip()[:1] or "?"
        ml = "ML2 (high clearance)" if ml == "2" else (
            f"ML{ml} (passenger car)" if ml in "345" else f"ML{ml}")
        dates = (a.get("passengervehicle_datesopen") or "").strip()
        seasonal = (a.get("symbol") in ("2", "4", "12")) or bool(dates and dates != "01/01-12/31")
        for h in hit:
            total += km_each
            w = ways[h] if h >= 0 else None
            kind = w["kind"] if w else f"no OSM way within {TOLERANCE_M:.0f} m"
            tab[("coverage", kind)] += km_each
            if kind.startswith("in graph ("):
                tab[("graph roughness", ml, w["rough"])] += km_each
                if w["cfcc"].startswith("A5"):
                    tab[("graph, TIGER cfcc A5x", ml)] += km_each
                if seasonal:
                    tab[("graph seasonal", w["seasonal"])] += km_each
            if seasonal:
                tab[("seasonal coverage", kind)] += km_each
    res = {"forest": forest, "mvum_lines": len(lines), "mvum_km_sampled": round(total, 1),
           "sample_m": SAMPLE_M, "tolerance_m": TOLERANCE_M, "tables": {}}
    for k, v in sorted(tab.items()):
        res["tables"].setdefault(k[0], {})[" | ".join(k[1:])] = round(v, 1)
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
