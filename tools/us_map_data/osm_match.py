"""Match another agency's road lines to OSM ways, by sampling along them.

Shared by mvum_osm_match.py and tiger_osm_match.py so both comparisons use one
rule: walk each line in SAMPLE_M steps, give each sample the nearest OSM
`highway=*` way within TOLERANCE_M, and let it carry its share of the line's
length. state_roads.py matches the same way (25 m samples, 12 m tolerance); the
tolerance is 15 m here because forest and ranch roads are digitised more
loosely than state highways.

Each OSM way is classed once, by what the pipeline would do with it:
  kind      in the graph (by class), in it but closed all year by closures.py,
            dropped by the access rule, or a highway= the graph leaves out;
  rough     the strongest roughness signal OSM carries;
  seasonal  whether closures.py closes it, or OSM has a seasonal or
            conditional tag it does not read, or neither;
  access    the car-access tag that decides it (common.car_access), if any.
"""

import numpy as np

from closures import CAR_KEYS, way_windows
from common import DRIVABLE, PRIVATE_ACCESS, car_access, closed_to_cars
from score import UNPAVED

SAMPLE_M = 25.0
TOLERANCE_M = 15.0
CRS_M = 5070           # NAD83 / Conus Albers: metres anywhere in the lower 48
ROUGH = {"bad", "very_bad", "horrible", "very_horrible", "impassable"}


def classify(t):
    hw = t.get("highway")
    if hw in DRIVABLE:
        if t.get("access") in PRIVATE_ACCESS and t.get("motor_vehicle") != "yes":
            kind = "dropped by the access rule"
        elif closed_to_cars(t) or (t.get("ford") or "").lower() == "yes":
            kind = "in graph, closed all year by closures.py"
        else:
            kind = f"in graph ({hw})"
    elif hw == "track":
        kind = "highway=track (not in graph)"
    elif hw == "service":
        kind = "highway=service (not in graph)"
    else:
        kind = f"other highway={hw} (not in graph)"
    rough = ("4wd_only" if t.get("4wd_only") == "yes" else
             "smoothness bad or worse" if t.get("smoothness") in ROUGH else
             "tracktype grade3-5" if t.get("tracktype") in ("grade3", "grade4", "grade5")
             else "unpaved surface only" if t.get("surface") in UNPAVED
             else "no roughness or surface signal")
    tagged = any(t.get(f"{k}:conditional") for k in CAR_KEYS) or \
        t.get("seasonal") or t.get("winter_service")
    seasonal = ("closures.py closes it" if way_windows(t) else
                "seasonal/conditional tag closures.py does not close" if tagged else
                "no seasonal tag")
    found = car_access(t)
    access = f"{found[0]}={found[1]}" if found else "no access tag"
    return {"kind": kind, "rough": rough, "seasonal": seasonal, "access": access,
            "cfcc": t.get("tiger:cfcc", ""), "tiger_reviewed": t.get("tiger:reviewed", "")}


def osm_ways(pbf, bbox):
    """Every highway= way with a vertex inside bbox (lon/lat), classified."""
    import osmium
    w0, s0, e0, n0 = bbox
    rows = []
    fp = (osmium.FileProcessor(pbf, osmium.osm.NODE | osmium.osm.WAY).with_locations()
          .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
          .with_filter(osmium.filter.KeyFilter("highway")))
    for o in fp:
        pts = [(n.location.lon, n.location.lat) for n in o.nodes if n.location.valid()]
        if len(pts) < 2 or not any(w0 <= x <= e0 and s0 <= y <= n0 for x, y in pts):
            continue
        rows.append({"pts": pts, **classify({k.k: k.v for k in o.tags})})
    return rows


def matcher(ways):
    """A function from a lon/lat line to (km per sample, nearest-way index per
    sample, -1 where no way is within TOLERANCE_M)."""
    import shapely
    from pyproj import Transformer
    from shapely.strtree import STRtree
    to_m = Transformer.from_crs(4326, CRS_M, always_xy=True).transform

    def proj(pts):
        xs, ys = to_m([p[0] for p in pts], [p[1] for p in pts])
        return shapely.LineString(list(zip(xs, ys)))

    tree = STRtree([proj(w["pts"]) for w in ways])

    def match(pts):
        line = proj(pts)
        L = line.length
        if L <= 0:
            return 0.0, np.zeros(0, dtype=int)
        n = max(1, int(L // SAMPLE_M))
        at = shapely.line_interpolate_point(line, (np.arange(n) + 0.5) * (L / n))
        idx = tree.query_nearest(at, max_distance=TOLERANCE_M, return_distance=False,
                                 all_matches=False)
        hit = np.full(n, -1)
        hit[idx[0]] = idx[1]
        return L / n / 1000.0, hit

    return match
