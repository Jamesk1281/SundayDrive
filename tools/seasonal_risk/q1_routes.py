"""Q1: what banning seasonal roads costs, on a fixed trip sample.

Every trip is asked of the server in process (harness.route, POST /api/route,
pref 0.5, the app's default) under:

  open      nothing closed for the season: what each road would be asked for
  P0@06-15, P0@08-15, P0@10-15   today's table on three dates
  P1        every seasonal row closed all year (a copy of the table, in memory)

Trail Ridge Road's all-year permit closure is lifted in every run, as the
brief directs (the parallel unit opens it in season).

Samples (samples.json, written once by `--make-samples`, seed 20261021):

  ne      tools/national_build/ne_trip_pairs.json, the 100 NE pairs the
          national proof used
  us      300 pairs: origin uniform over road km of the national graph,
          destination at a random bearing and a great-circle 20-150 km
  near    300 pairs in seasonal-road country: a seasonal edge drawn by
          length, an origin 5-60 km from it, and a destination on the far
          side (the origin reflected through the edge, scaled 0.5-1.5x and
          turned up to 30 degrees). Biased toward seasonal roads on purpose.
  named   each road in roads.py, gateway to gateway, both ways

Output: q1_routes.csv, one row per (trip, run, arm).

  python q1_routes.py --make-samples
  python q1_routes.py [--only ne,us] [--limit N]
"""

import argparse
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "samples.json"
OUT = HERE / "q1_routes.csv"
DATES = {"P0@06-15": date(2026, 6, 15), "P0@08-15": date(2026, 8, 15),
         "P0@10-15": date(2026, 10, 15)}
PREF = 0.5


def offset(lat, lon, km, bearing_deg):
    b = math.radians(bearing_deg)
    dlat = km * math.cos(b) / 111.2
    dlon = km * math.sin(b) / (111.2 * math.cos(math.radians(lat)))
    return round(lat + dlat, 6), round(lon + dlon, 6)


def make_samples(h, W, R):
    rng = np.random.default_rng(20261021)
    out = []
    ne = json.load(open(HERE.parents[1] / "tools/national_build/ne_trip_pairs.json"))
    for p in ne:
        out.append(dict(sample="ne", name=p["name"], a=p["from"], b=p["to"]))
    L = np.asarray(h.ROUTER.length_m, float)
    cum = np.cumsum(L) / L.sum()
    for i in range(300):
        e = int(np.searchsorted(cum, rng.random()))
        lon, lat = h.edge_lonlat(e)
        b = offset(lat, lon, rng.uniform(20, 150), rng.uniform(0, 360))
        out.append(dict(sample="us", name=f"us:{i:03d}", a=[round(lat, 6), round(lon, 6)], b=list(b)))
    t = h.BASE_TABLE.drop_duplicates("edge")
    w = t["length_m"].to_numpy() / t["length_m"].sum()
    picks = rng.choice(len(t), size=300, p=w)
    for i, k in enumerate(picks):
        e = int(t["edge"].iloc[k])
        lon, lat = h.edge_lonlat(e)
        dist, bear = rng.uniform(5, 60), rng.uniform(0, 360)
        a = offset(lat, lon, dist, bear)
        b = offset(lat, lon, dist * rng.uniform(0.5, 1.5), bear + 180 + rng.uniform(-30, 30))
        out.append(dict(sample="near", name=f"near:{i:03d}", a=list(a), b=list(b),
                        seed_edge=e))
    for key, spec in R.ROADS.items():
        a, b = spec["ends"]
        out.append(dict(sample="named", name=f"{key}:ab", road=key, a=list(a), b=list(b)))
        out.append(dict(sample="named", name=f"{key}:ba", road=key, a=list(b), b=list(a)))
    json.dump(out, open(SAMPLES, "w"), indent=0)
    print(f"wrote {len(out)} trips to {SAMPLES.name}")


def describe(h, res, seasonal, road_of, beautiful=7.0):
    """The numbers Q1 needs off one RouteResult."""
    e = res.edges.index.to_numpy()
    km = res.edges["length_m"].to_numpy() / 1000.0
    sc = np.asarray(res.scores, float)
    on = np.isin(e, seasonal)
    roads = sorted({road_of[x] for x in e[on] if x in road_of})
    return dict(km=float(km.sum()), minutes=float(res.minutes),
                mean_score=float(res.mean_score), beautiful_km=float(km[sc >= beautiful].sum()),
                cost=float(h.cost(res, PREF)),
                seasonal_km=float(km[on].sum()),
                seasonal_beautiful_km=float(km[on & (sc >= beautiful)].sum()),
                seasonal_edges=" ".join(str(int(x)) for x in np.unique(e[on])),
                named=" ".join(roads))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-samples", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    sys.path.insert(0, str(HERE))
    import harness as h
    import roads as R
    import windows as W
    if args.make_samples:
        make_samples(h, W, R)
        return

    table = W.annotate(h.BASE_TABLE)
    seasonal = np.unique(table["edge"].to_numpy())
    road_of = {}
    for key in R.ROADS:
        for x in R.edges_of(table, key, h.edge_lonlat)["edge"]:
            road_of[int(x)] = key
    h.open_to_cars(h.trail_ridge_permit_edges())

    trips = json.load(open(SAMPLES))
    if args.only:
        trips = [t for t in trips if t["sample"] in args.only.split(",")]
    if args.limit:
        trips = trips[: args.limit]

    runs = [("open", date(2026, 8, 15), table.iloc[:0]),
            *[(k, d, None) for k, d in DATES.items()],
            ("P1", date(2026, 8, 15), W.policy_table(table, ban=True))]
    rows = []
    t0 = time.time()
    for run, day, tab in runs:
        h.set_table(tab)
        h.set_day(day)
        for i, trip in enumerate(trips):
            st, js, res = h.route(trip["a"], trip["b"], pref=PREF)
            base = dict(sample=trip["sample"], trip=trip["name"], run=run, day=day.isoformat(),
                        status=st, code=(js or {}).get("code", "") if st != 200 else "")
            if st == 200 and len(res) == 2:
                for arm, r in zip(("fastest", "scenic"), res):
                    rows.append({**base, "arm": arm, **describe(h, r, seasonal, road_of)})
            else:
                rows.append({**base, "arm": ""})
            if (i + 1) % 50 == 0:
                print(f"{run} {i + 1}/{len(trips)} {time.time() - t0:.0f}s", flush=True)
        pd.DataFrame(rows).to_csv(OUT, index=False)
    h.set_table(None)
    print(f"wrote {len(rows)} rows to {OUT.name} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
