"""The trips docs/low-scenery-fallback.md measures: a seeded random national
sample, the outside review's named trips, and its three fewer-km starts.

Both ends of a random trip are points on the road graph, drawn by length (a
km of road anywhere in the 48 states is as likely as any other), 40-160 km
apart in a straight line. The review did not record where its three fewer-km
trips went, so each of those starts gets seeded random destinations the same
way.

    python tools/low_scenery_fallback/sample.py data/pack-us > trips.json
"""

import json
import math
import sys

import numpy as np

SEED = 20261025
RANDOM_TRIPS = 120
PER_START = 3
MIN_KM, MAX_KM = 40.0, 160.0

NAMED = [
    ("Wichita -> Salina", (37.6872, -97.3301), (38.8403, -97.6114)),
    ("New Orleans -> Baton Rouge", (29.9511, -90.0715), (30.4515, -91.1871)),
    ("Chicago -> Milwaukee", (41.8781, -87.6298), (43.0389, -87.9065)),
    ("Atlanta -> Chattanooga", (33.7490, -84.3880), (35.0456, -85.3097)),
    ("Denver -> Estes Park", (39.7392, -104.9903), (40.3772, -105.5217)),
]
FEWER_KM_STARTS = [("NV", (40.58, -119.30)), ("WA", (45.87, -121.56)),
                   ("ID", (43.21, -115.36))]


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


def main(pack):
    km = np.load(f"{pack}/km.npy", mmap_mode="r")
    eidx = np.load(f"{pack}/eidx.npy", mmap_mode="r")
    tail = np.load(f"{pack}/tail.npy", mmap_mode="r")
    real = np.load(f"{pack}/real_node.npy", mmap_mode="r")
    lat = np.load(f"{pack}/node_lat.npy", mmap_mode="r")
    lon = np.load(f"{pack}/node_lon.npy", mmap_mode="r")
    # Drawn by routing slot, one per direction a road can be driven, so a
    # two-way road counts once each way.
    cum = np.cumsum(np.asarray(km)[np.asarray(eidx)])
    rng = np.random.default_rng(SEED)

    def points(n):
        slots = np.searchsorted(cum, rng.random(n) * cum[-1])
        nodes = np.asarray(real)[np.asarray(tail)[slots]]
        return np.asarray(lat)[nodes], np.asarray(lon)[nodes]

    def destination(a_lat, a_lon):
        while True:
            b_lat, b_lon = points(200_000)
            d = haversine_km(a_lat, a_lon, b_lat, b_lon)
            ok = np.flatnonzero((d >= MIN_KM) & (d <= MAX_KM))
            if len(ok):
                i = ok[0]
                return float(b_lat[i]), float(b_lon[i]), float(d[i])

    trips = []
    for k in range(RANDOM_TRIPS):
        a_lat, a_lon = points(1)
        b_lat, b_lon, d = destination(a_lat[0], a_lon[0])
        trips.append({"id": f"r{k:03d}", "kind": "random",
                      "from": [round(float(a_lat[0]), 6), round(float(a_lon[0]), 6)],
                      "to": [round(b_lat, 6), round(b_lon, 6)], "crow_km": round(d, 1)})
    for name, a, b in NAMED:
        trips.append({"id": name, "kind": "named", "from": list(a), "to": list(b),
                      "crow_km": round(float(haversine_km(*a, *b)), 1)})
    for state, a in FEWER_KM_STARTS:
        for j in range(PER_START):
            b_lat, b_lon, d = destination(*a)
            trips.append({"id": f"{state}-{j}", "kind": "fewer-km start",
                          "from": list(a), "to": [round(b_lat, 6), round(b_lon, 6)],
                          "crow_km": round(d, 1)})
    json.dump({"seed": SEED, "trips": trips}, sys.stdout, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
