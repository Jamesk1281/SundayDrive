"""How OSM tags each seasonal ground-truth road, and what closures.py does with it.

For every road in seasonal_roads.json belonging to the state given, finds the
highway ways inside the road's bounding box whose name, ref or alternative
names match it, and reports for each:
  - whether graph.py would keep it (DRIVABLE and the access rule) or drop it;
  - its km and the tags that bear on a closure: `*:conditional` for any key,
    `seasonal`, `winter_service`, `access` and the car keys, `opening_hours`;
  - the windows closures.py's `way_windows` closes it in, if any;
  - every barrier node on it, with its own tags, since a gate can carry the
    closure where the way carries nothing (closures.py does not read timed
    gates; it only counts them).

The input is a state PBF or an Overpass JSON answer (`out tags geom` for the
ways, `out tags` for their barrier nodes), for the states whose extracts were
too large to sample (docs/us-map-data-findings.md, "Seasonal roads").

Usage: python -I seasonal_check.py <repo_pipeline_dir> <file.osm.pbf|answer.json>
                                   <state> <seasonal_roads.json> <out.json>
"""

import json
import math
import re
import sys

sys.path.insert(0, sys.argv[1])
from common import DRIVABLE, PRIVATE_ACCESS  # noqa: E402
from closures import way_windows  # noqa: E402

src, state, roads_path, out_path = sys.argv[2:6]
roads = [r for r in json.load(open(roads_path)) if r["state"] == state]
NAME_KEYS = ("name", "ref", "official_name", "alt_name", "old_name", "name_1", "loc_name")
KEEP = re.compile(r"conditional|^seasonal$|^winter_service|^access$|^motor_vehicle$|"
                  r"^motorcar$|^vehicle$|^opening_hours|^highway$|^surface$|^smoothness$|"
                  r"^4wd_only$|^barrier$|^locked$|^note|^description$")


def length_km(coords):
    total = 0.0
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        la1, la2 = math.radians(y1), math.radians(y2)
        a = (math.sin((la2 - la1) / 2) ** 2
             + math.cos(la1) * math.cos(la2) * math.sin(math.radians(x2 - x1) / 2) ** 2)
        total += 2 * 6371.0088 * math.asin(math.sqrt(min(1.0, a)))
    return total


def matches(road, tags):
    rx_name = re.compile(road["name"], re.IGNORECASE) if road.get("name") else None
    rx_ref = re.compile(road["ref"], re.IGNORECASE) if road.get("ref") else None
    for k in NAME_KEYS:
        v = tags.get(k)
        if not v:
            continue
        if rx_name and k != "ref" and rx_name.search(v):
            return True
        if rx_ref and k == "ref" and any(rx_ref.search(p.strip()) for p in v.split(";")):
            return True
    return False


def in_bbox(road, coords):
    w, s, e, n = road["bbox"]
    return any(w <= x <= e and s <= y <= n for x, y in coords)


ways, barriers = [], {}
if src.endswith(".json"):
    data = json.load(open(src))
    for el in data["elements"]:
        if el["type"] == "node" and "barrier" in el.get("tags", {}):
            barriers[el["id"]] = el["tags"]
    for el in data["elements"]:
        if el["type"] == "way" and "highway" in el.get("tags", {}):
            coords = [(p["lon"], p["lat"]) for p in el.get("geometry", []) if p]
            ways.append((el["id"], el["tags"], el.get("nodes", []), coords))
else:
    import osmium
    fp = (osmium.FileProcessor(src, osmium.osm.NODE | osmium.osm.WAY)
          .with_locations()
          .with_filter(osmium.filter.KeyFilter("highway", "barrier")))
    for o in fp:
        if o.is_node():
            if o.tags.get("barrier"):
                barriers[o.id] = {t.k: t.v for t in o.tags}
            continue
        tags = {t.k: t.v for t in o.tags}
        if not any(matches(r, tags) for r in roads):
            continue
        coords = [(n.location.lon, n.location.lat) for n in o.nodes if n.location.valid()]
        ways.append((o.id, tags, [n.ref for n in o.nodes], coords))

report = []
for road in roads:
    found = []
    for wid, tags, nodes, coords in ways:
        if not (matches(road, tags) and in_bbox(road, coords)):
            continue
        hw = tags.get("highway")
        if hw not in DRIVABLE:
            status = f"not drivable (highway={hw})"
        elif tags.get("access") in PRIVATE_ACCESS and tags.get("motor_vehicle") != "yes":
            status = f"dropped by the access rule (access={tags.get('access')})"
        else:
            status = "in graph"
        win = way_windows(tags)
        found.append({
            "way_id": wid, "status": status, "km": round(length_km(coords), 2),
            "tags": {k: v for k, v in tags.items() if KEEP.search(k)},
            "closures_py_windows": [list(w) for w in win],
            "barriers": [{"node": n, **barriers[n]} for n in nodes if n in barriers],
        })
    graph = [f for f in found if f["status"] == "in graph"]
    km_graph = sum(f["km"] for f in graph)
    km_closed = sum(f["km"] for f in graph if f["closures_py_windows"])
    km_tagged = sum(f["km"] for f in graph if any(
        k.endswith(":conditional") or k in ("seasonal", "winter_service")
        for k in f["tags"]))
    timed_gates = [b for f in found for b in f["barriers"]
                   if any(k.endswith(":conditional") or k in ("seasonal", "opening_hours")
                          for k in b)]
    report.append({
        "id": road["id"], "road": road["road"], "state": state,
        "ways_matched": len(found), "km_in_graph": round(km_graph, 1),
        "km_closures_py_closes": round(km_closed, 1),
        "km_with_any_seasonal_or_conditional_tag": round(km_tagged, 1),
        "km_dropped_or_not_drivable": round(sum(f["km"] for f in found) - km_graph, 1),
        "barriers_on_road": sum(len(f["barriers"]) for f in found),
        "timed_barriers": timed_gates,
        "ways": found,
    })
    print(f"{road['id']:24s} ways {len(found):3d}  graph {km_graph:6.1f} km  "
          f"closed by closures.py {km_closed:6.1f} km  any tag {km_tagged:6.1f} km  "
          f"barriers {sum(len(f['barriers']) for f in found)} (timed {len(timed_gates)})")
json.dump(report, open(out_path, "w"), indent=1)
