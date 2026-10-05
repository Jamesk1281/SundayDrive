"""Write the committed O/D list the overnight end-to-end drives run over.

    .venv/bin/python tools/e2e_od_pairs.py data/processed-ne > tools/e2e_od_pairs.json

Seeded and committed on purpose: a drive that fails at 3 a.m. has to be
re-runnable by its id the next morning, so the list is data in the repo and not
a sampler run per night. Re-running this with the same seed and the same
processed data reproduces the file byte for byte; changing either is a new list
and should be committed as one. See docs/overnight-e2e-findings.md.

Pins come from three places, and the category says which:

  * hand-placed town anchors (below), for the named categories — coastal,
    cross-state, rural long hauls, loops, islands;
  * `place_points.parquet` (OSM place nodes: villages, neighbourhoods) within a
    distance band of an anchor, for urban and suburban trips — real settlements,
    so the pin is somewhere a person would actually ask for;
  * the centroid of a service-way component from `access_ways.parquet`, for the
    parking-lot category. A component is one connected cluster of service ways
    (car-park aisles, a plaza's loop road), so its bbox centre is a pin dropped
    in the middle of a lot — the case `scenic-destination-snaps-to-wrong-road`
    measured going wrong.

The state on a pair is the state of the anchor it was drawn around, not a
point-in-polygon test: a pin sampled near a border can sit across it. Cross-state
pairs are anchored on both ends, so their states are right.
"""

import json
import math
import random
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np

SEED = 20260930

# (name, state, lat, lon, tags). Town centres, hand-placed; the server snaps
# them, so a few hundred metres of error only moves which junction is used.
ANCHORS = [
    ("Boston", "MA", 42.3601, -71.0589, "city"),
    ("Worcester", "MA", 42.2626, -71.8023, "city"),
    ("Springfield", "MA", 42.1015, -72.5898, "city"),
    ("Lowell", "MA", 42.6334, -71.3162, "city"),
    ("Pittsfield", "MA", 42.4501, -73.2454, "rural"),
    ("Northampton", "MA", 42.3251, -72.6412, "rural"),
    ("Greenfield", "MA", 42.5876, -72.5995, "rural"),
    ("Plymouth", "MA", 41.9584, -70.6673, "coast"),
    ("Rockport", "MA", 42.6559, -70.6206, "coast"),
    ("Gloucester", "MA", 42.6159, -70.6620, "coast"),
    ("Chatham", "MA", 41.6821, -69.9597, "coast"),
    ("Provincetown", "MA", 42.0526, -70.1860, "coast"),
    ("New Bedford", "MA", 41.6362, -70.9342, "coast"),
    ("Providence", "RI", 41.8240, -71.4128, "city"),
    ("Warwick", "RI", 41.7001, -71.4162, "city"),
    ("Woonsocket", "RI", 42.0029, -71.5148, "city"),
    ("Newport", "RI", 41.4901, -71.3128, "coast"),
    ("Narragansett", "RI", 41.4501, -71.4495, "coast"),
    ("Westerly", "RI", 41.3776, -71.8273, "coast"),
    ("Bristol", "RI", 41.6771, -71.2662, "coast"),
    ("Hartford", "CT", 41.7658, -72.6734, "city"),
    ("New Haven", "CT", 41.3083, -72.9279, "city"),
    ("Stamford", "CT", 41.0534, -73.5387, "city"),
    ("Danbury", "CT", 41.3948, -73.4540, "city"),
    ("Litchfield", "CT", 41.7473, -73.1887, "rural"),
    ("Putnam", "CT", 41.9151, -71.9090, "rural"),
    ("Norwich", "CT", 41.5243, -72.0759, "rural"),
    ("Mystic", "CT", 41.3543, -71.9665, "coast"),
    ("Old Saybrook", "CT", 41.2918, -72.3762, "coast"),
    ("Manchester", "NH", 42.9956, -71.4548, "city"),
    ("Nashua", "NH", 42.7654, -71.4676, "city"),
    ("Concord", "NH", 43.2081, -71.5376, "city"),
    ("Keene", "NH", 42.9337, -72.2781, "rural"),
    ("North Conway", "NH", 44.0537, -71.1284, "rural"),
    ("Lincoln", "NH", 44.0456, -71.6703, "rural"),
    ("Hanover", "NH", 43.7022, -72.2896, "rural"),
    ("Berlin", "NH", 44.4687, -71.1851, "rural"),
    ("Laconia", "NH", 43.5279, -71.4704, "rural"),
    ("Portsmouth", "NH", 43.0718, -70.7626, "coast"),
    ("Burlington", "VT", 44.4759, -73.2121, "city"),
    ("Montpelier", "VT", 44.2601, -72.5754, "rural"),
    ("Brattleboro", "VT", 42.8509, -72.5579, "rural"),
    ("Rutland", "VT", 43.6106, -72.9726, "rural"),
    ("Stowe", "VT", 44.4654, -72.6874, "rural"),
    ("Woodstock", "VT", 43.6243, -72.5185, "rural"),
    ("Bennington", "VT", 42.8781, -73.1968, "rural"),
    ("St. Johnsbury", "VT", 44.4192, -72.0151, "rural"),
    ("Manchester Center", "VT", 43.1637, -73.0723, "rural"),
    ("Portland", "ME", 43.6591, -70.2568, "city"),
    ("Bangor", "ME", 44.8016, -68.7712, "city"),
    ("Lewiston", "ME", 44.1004, -70.2148, "city"),
    ("Augusta", "ME", 44.3106, -69.7795, "rural"),
    ("Bethel", "ME", 44.4040, -70.7909, "rural"),
    ("Rangeley", "ME", 44.9659, -70.6428, "rural"),
    ("Presque Isle", "ME", 46.6812, -68.0159, "rural"),
    ("Kennebunkport", "ME", 43.3615, -70.4767, "coast"),
    ("Brunswick", "ME", 43.9145, -69.9653, "coast"),
    ("Boothbay Harbor", "ME", 43.8523, -69.6281, "coast"),
    ("Camden", "ME", 44.2098, -69.0648, "coast"),
    ("Rockland", "ME", 44.1037, -69.1089, "coast"),
    ("Bar Harbor", "ME", 44.3876, -68.2039, "coast"),
    ("Ellsworth", "ME", 44.5434, -68.4195, "coast"),
]

# Coastal runs, in order along the shore: each is driven as one pair.
COASTAL = [
    ("Rockport", "Gloucester"), ("Gloucester", "Boston"), ("Plymouth", "New Bedford"),
    ("Chatham", "Provincetown"), ("Provincetown", "Plymouth"), ("New Bedford", "Newport"),
    ("Bristol", "Newport"), ("Newport", "Narragansett"), ("Narragansett", "Westerly"),
    ("Westerly", "Mystic"), ("Mystic", "Old Saybrook"), ("Old Saybrook", "New Haven"),
    ("New Haven", "Stamford"), ("Portsmouth", "Kennebunkport"), ("Kennebunkport", "Portland"),
    ("Portland", "Brunswick"), ("Brunswick", "Boothbay Harbor"), ("Boothbay Harbor", "Rockland"),
    ("Rockland", "Camden"), ("Camden", "Ellsworth"), ("Ellsworth", "Bar Harbor"),
    ("Bar Harbor", "Camden"), ("Rockport", "Portsmouth"), ("Chatham", "Plymouth"),
    ("Westerly", "Narragansett"),
]

CROSS_STATE = [
    ("Boston", "Manchester"), ("Lowell", "Nashua"), ("Worcester", "Keene"),
    ("Springfield", "Hartford"), ("Worcester", "Providence"), ("Boston", "Providence"),
    ("Hartford", "Providence"), ("Norwich", "Westerly"), ("Putnam", "Woonsocket"),
    ("Brattleboro", "Keene"), ("Greenfield", "Brattleboro"), ("Pittsfield", "Bennington"),
    ("Hanover", "Woodstock"), ("St. Johnsbury", "Lincoln"), ("Montpelier", "Hanover"),
    ("Portsmouth", "Portland"), ("North Conway", "Bethel"), ("Berlin", "Rangeley"),
    ("Danbury", "Pittsfield"), ("Stamford", "Springfield"), ("Mystic", "Newport"),
    ("Concord", "Portland"), ("Nashua", "Worcester"), ("Keene", "Northampton"),
    ("Rutland", "Hanover"), ("Burlington", "Hanover"), ("Bennington", "Northampton"),
    ("Woonsocket", "Worcester"), ("Litchfield", "Springfield"), ("Kennebunkport", "Manchester"),
]

RURAL_LONG = [
    ("Pittsfield", "Northampton"), ("Brattleboro", "Rutland"), ("Rutland", "Montpelier"),
    ("Burlington", "Stowe"), ("Stowe", "St. Johnsbury"), ("Woodstock", "Manchester Center"),
    ("Bennington", "Rutland"), ("Keene", "Concord"), ("Concord", "North Conway"),
    ("Lincoln", "Berlin"), ("Laconia", "Lincoln"), ("Hanover", "Lincoln"),
    ("Augusta", "Bethel"), ("Bethel", "Rangeley"), ("Lewiston", "Rangeley"),
    ("Bangor", "Bar Harbor"), ("Augusta", "Camden"), ("Bangor", "Presque Isle"),
    ("Litchfield", "Danbury"), ("Putnam", "Norwich"), ("Hartford", "Litchfield"),
    ("Greenfield", "Pittsfield"), ("Worcester", "Greenfield"), ("Springfield", "Pittsfield"),
    ("Montpelier", "Brattleboro"), ("North Conway", "Laconia"), ("Portland", "Bethel"),
    ("Augusta", "Bangor"), ("Keene", "Hanover"), ("Stowe", "Burlington"),
]

# Pins that cannot be reached by car, or not from the mainland. The right
# answer is a clean 400/404 the app can say something about — not a hang, a
# 500, or a route across the water. The first is island-internal and should
# route.
ISLANDS = [
    ("island-internal Edgartown->Oak Bluffs", (41.3890, -70.5134), (41.4543, -70.5620), "route"),
    ("Nantucket from Hyannis", (41.6526, -70.2881), (41.2835, -70.0995), "fail"),
    ("Edgartown from Falmouth", (41.5515, -70.6148), (41.3890, -70.5134), "fail"),
    ("Block Island from Narragansett", (41.4501, -71.4495), (41.1720, -71.5578), "fail"),
    ("Peaks Island from Portland", (43.6591, -70.2568), (43.6554, -70.1970), "fail"),
    ("Vinalhaven from Rockland", (44.1037, -69.1089), (44.0484, -68.8317), "fail"),
    ("Monhegan from Boothbay", (43.8523, -69.6281), (43.7648, -69.3161), "fail"),
    ("Cuttyhunk from New Bedford", (41.6362, -70.9342), (41.4254, -70.9267), "fail"),
    ("Isle au Haut from Camden", (44.2098, -69.0648), (44.0712, -68.6314), "fail"),
    ("open ocean off Cape Ann", (42.6559, -70.6206), (42.60, -70.20), "fail"),
]

LOOPS = [
    ("Boston", 30), ("Worcester", 50), ("Northampton", 40), ("Pittsfield", 60),
    ("Plymouth", 35), ("Providence", 30), ("Newport", 25), ("Hartford", 45),
    ("Litchfield", 50), ("Mystic", 40), ("Concord", 60), ("North Conway", 50),
    ("Hanover", 45), ("Portsmouth", 30), ("Stowe", 40), ("Woodstock", 60),
    ("Brattleboro", 35), ("Camden", 50), ("Bethel", 80), ("Kennebunkport", 30),
]


def km_between(a, b):
    """Great-circle distance in km, (lat, lon) pairs."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def r6(p):
    return [round(float(p[0]), 6), round(float(p[1]), 6)]


def main(argv):
    data = Path(argv[1])
    rng = random.Random(SEED)
    anchors = {a[0]: a for a in ANCHORS}

    places = gpd.read_parquet(data / "place_points.parquet")
    place_ll = np.column_stack([places.geometry.y.to_numpy(), places.geometry.x.to_numpy()])

    ways = gpd.read_parquet(data / "access_ways.parquet")
    b = ways.geometry.bounds
    b["component"] = ways["component"].to_numpy()
    box = b.groupby("component").agg(minx=("minx", "min"), miny=("miny", "min"),
                                      maxx=("maxx", "max"), maxy=("maxy", "max"))
    midlat = np.radians((box.miny + box.maxy) / 2)
    diag = np.hypot((box.maxx - box.minx) * 111.32 * np.cos(midlat),
                    (box.maxy - box.miny) * 110.54) * 1000
    lots = box[(diag > 120) & (diag < 400)]
    lot_ll = np.column_stack([((lots.miny + lots.maxy) / 2).to_numpy(),
                              ((lots.minx + lots.maxx) / 2).to_numpy()])

    def near(pool, centre, lo_km, hi_km):
        """A seeded pick from `pool` between lo and hi km of `centre`."""
        d = np.array([km_between(centre, p) for p in pool]) if len(pool) < 20000 else None
        if d is None:
            # Pre-filter by a bbox so the big pools stay cheap.
            dlat = hi_km / 110.5
            dlon = hi_km / (111.3 * math.cos(math.radians(centre[0])))
            m = ((np.abs(pool[:, 0] - centre[0]) < dlat)
                 & (np.abs(pool[:, 1] - centre[1]) < dlon))
            sub = pool[m]
            d = np.array([km_between(centre, p) for p in sub])
            pool = sub
        idx = np.flatnonzero((d >= lo_km) & (d <= hi_km))
        if len(idx) == 0:
            return None
        return pool[idx[rng.randrange(len(idx))]]

    pairs = []

    def add(cat, state, origin, dest, note, expect="route", km=None):
        pid = f"{cat}-{sum(1 for p in pairs if p['category'] == cat) + 1:03d}"
        entry = dict(id=pid, category=cat, state=state, origin=r6(origin),
                     note=note, expect=expect)
        if dest is not None:
            entry["destination"] = r6(dest)
            entry["crow_km"] = round(km_between(origin, dest), 1)
        if km is not None:
            entry["loop_km"] = km
        pairs.append(entry)

    cities = [a for a in ANCHORS if a[4] == "city"]
    # Urban: both ends inside the city, under 10 km apart.
    while sum(p["category"] == "urban" for p in pairs) < 40:
        name, st, lat, lon, _ = cities[rng.randrange(len(cities))]
        o = near(place_ll, (lat, lon), 0.0, 4.0)
        d = o is not None and near(place_ll, tuple(o), 2.0, 8.0)
        if o is None or d is None or d is False:
            continue
        add("urban", st, o, d, f"within {name}")

    # Suburban: out of a town to a place 10-30 km away.
    everywhere = ANCHORS
    while sum(p["category"] == "suburban" for p in pairs) < 40:
        name, st, lat, lon, _ = everywhere[rng.randrange(len(everywhere))]
        o = near(place_ll, (lat, lon), 0.0, 3.0)
        d = o is not None and near(place_ll, (lat, lon), 10.0, 30.0)
        if o is None or d is None or d is False:
            continue
        add("suburban", st, o, d, f"out of {name}")

    for a, b_ in RURAL_LONG:
        A, B = anchors[a], anchors[b_]
        add("rural", A[1], (A[2], A[3]), (B[2], B[3]), f"{a} -> {b_}")
    for a, b_ in COASTAL:
        A, B = anchors[a], anchors[b_]
        add("coastal", A[1], (A[2], A[3]), (B[2], B[3]), f"{a} -> {b_}")
    for a, b_ in CROSS_STATE:
        A, B = anchors[a], anchors[b_]
        add("cross", f"{A[1]}->{B[1]}", (A[2], A[3]), (B[2], B[3]), f"{a} -> {b_}")

    # Parking-lot pins: the destination is the middle of a service-way cluster
    # 3-15 km from a town.
    while sum(p["category"] == "parking" for p in pairs) < 30:
        name, st, lat, lon, _ = everywhere[rng.randrange(len(everywhere))]
        o = near(place_ll, (lat, lon), 0.0, 3.0)
        d = o is not None and near(lot_ll, (lat, lon), 3.0, 15.0)
        if o is None or d is None or d is False:
            continue
        add("parking", st, o, d, f"lot near {name}")

    for note, o, d, expect in ISLANDS:
        add("island", "MA/RI/ME", o, d, note, expect=expect)

    for name, km in LOOPS:
        A = anchors[name]
        add("loop", A[1], (A[2], A[3]), None, f"{km} km loop from {name}", km=km)

    json.dump(dict(seed=SEED, generator="tools/e2e_od_pairs.py",
                   prefs=[0.0, 0.5, 1.0], pairs=pairs), sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
