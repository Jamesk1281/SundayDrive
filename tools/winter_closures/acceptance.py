"""docs/us-map-data-findings.md §4's seasonal roads, re-run against a built
seasonal_closures.parquet: is each road closed on the days its operator closes
it, and open on the days it is open?

A road's graph edges are found as tools/us_map_data/seasonal_check.py finds
its ways, by name or ref inside its box. That picks out the road to check
and nothing else; closures.py itself never joins by name. For each date in
acceptance.json it reports the km of the road closed, by OSM's tags alone
(rows whose `tag` is not an agency's or the table's) and by every row, and
the km closed all year by closed_to_cars.parquet, which is where the permit
rule puts Trail Ridge Road.

Usage: python acceptance.py <repo_pipeline_dir> <graph_dir> <tables_dir> <out.csv>
"""

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import CLOSURE_WINDOW, in_window  # noqa: E402

HERE = Path(__file__).resolve().parent
ROADS = HERE.parent / "us_map_data/seasonal_roads.json"
AGENCY = re.compile(r"^(mvum|nps|table) ")


def select(edges, road):
    w, s, e, n = road["bbox"]
    b = edges.geometry.bounds
    inside = (b["maxx"] >= w) & (b["minx"] <= e) & (b["maxy"] >= s) & (b["miny"] <= n)
    hit = np.zeros(len(edges), bool)
    if road.get("name"):
        hit |= edges["name"].fillna("").str.contains(road["name"], case=False, regex=True)
    if road.get("ref"):
        rx = re.compile(road["ref"], re.IGNORECASE)
        hit |= edges["ref"].fillna("").map(
            lambda v: any(rx.search(p.strip()) for p in v.split(";")))
    return np.flatnonzero(inside.to_numpy() & hit.to_numpy())


def closed_km(table, rows, length, day):
    md = (int(day[:2]), int(day[3:]))
    shut = table[(table["rule"] == "edge") & table["edge"].isin(rows)]
    on = shut[np.array([in_window(tuple(w), md)
                        for w in shut[list(CLOSURE_WINDOW)].to_numpy()], bool)]
    return length[np.unique(on["edge"].to_numpy())].sum() / 1000.0


def main(graph_dir, tables_dir, out):
    edges = gpd.read_parquet(Path(graph_dir) / "graph_edges.parquet",
                             columns=["u", "v", "length_m", "name", "ref", "geometry"])
    length = edges["length_m"].to_numpy()
    table = pd.read_parquet(Path(tables_dir) / "seasonal_closures.parquet")
    osm = table[~table["tag"].str.match(AGENCY)]
    cars_path = Path(tables_dir) / "closed_to_cars.parquet"
    cars = pd.read_parquet(cars_path) if cars_path.exists() else None
    checks = json.loads((HERE / "acceptance.json").read_text())
    roads = {r["id"]: r for r in json.loads(ROADS.read_text())}
    rows_out = []
    for rid, check in checks.items():
        rows = select(edges, roads[rid])
        km = length[rows].sum() / 1000.0
        if not len(rows):
            print(f"{rid:24s} not in this graph")
            continue
        year = (length[np.unique(cars.loc[cars["edge"].isin(rows) & (cars["rule"] == "edge"),
                                          "edge"])].sum() / 1000.0 if cars is not None else 0.0)
        for want in ("closed", "open"):
            for day in check[want]:
                before = closed_km(osm, rows, length, day)
                after = closed_km(table, rows, length, day)
                rows_out.append({"road": rid, "km_in_graph": round(km, 1), "date": day,
                                 "operator": want, "km_closed_osm_only": round(before, 1),
                                 "km_closed_now": round(after, 1),
                                 "km_closed_all_year": round(year, 1),
                                 "expected_closed_km": check.get("closed_km", "")})
        line = "  ".join(f"{r['date']} {r['operator'][0]} {r['km_closed_osm_only']:5.1f}->"
                         f"{r['km_closed_now']:5.1f}" for r in rows_out if r["road"] == rid)
        print(f"{rid:24s} {km:6.1f} km  all-year {year:5.1f}  {line}")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0]))
        w.writeheader()
        w.writerows(rows_out)


if __name__ == "__main__":
    main(*sys.argv[2:5])
