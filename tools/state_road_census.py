"""Route the same trips on two data directories and say what the state road
classes changed (docs/state-road-class.md, "Route census").

    .venv/bin/python tools/state_road_census.py route --processed DIR --out before.pkl
    .venv/bin/python tools/state_road_census.py route --processed DIR2 --out after.pkl
    .venv/bin/python tools/state_road_census.py compare before.pkl after.pkl \
        --table DIR2/state_road_class.parquet

`route` drives the trips: every pair in tools/e2e_od_pairs.json at pref 0 and
0.5, its loops, a stratified sample of town-to-town pairs drawn as
tools/route_census.py draws them, and the Class VI case that started this,
replayed between two public test points (never a drive trace's own
coordinates, which are private). Each is snapped as server/app.py snaps it,
with the app's weights (town 0) and on a July day, so no seasonal closure is
in force.
Run it once per directory, in separate processes: each Router holds about 5 GB.

`compare` reads both, and for every trip says whether its edges changed, what
that cost in km and minutes, and how much of it drove what the table closes,
drove a private road in the middle, or drove what it calls unpaved. A private
road at the start or the end of a trip is what decision 2 allows, so only a
private run with something public on both sides of it counts.
"""

import argparse
import json
import pickle
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tools"))

APP_WEIGHTS = {"town": 0.0}
JULY = date(2027, 7, 15)
# Warren village (tests/test_closures.py) to NEEDHAM_KERB (tests/test_routing.py),
# which drives the Class VI edge 497893 without the table.
CASE = {"from": (44.1123, -72.8565), "dest": (42.27725230013152, -71.2417737300463),
        "pref": 0.5, "weights": APP_WEIGHTS}


def trips(processed: Path, per_band: int, seed: int):
    """(id, kind, origin, destination or loop km, pref, weights), in a fixed
    order."""
    out = [("class-vi-case", "case", CASE["from"], CASE["dest"], CASE["pref"],
            CASE["weights"])]
    pairs = json.loads((ROOT / "tools" / "e2e_od_pairs.json").read_text())["pairs"]
    for p in pairs:
        if p["category"] == "loop":
            out.append((p["id"], "loop", tuple(p["origin"]), float(p["loop_km"]),
                        0.5, APP_WEIGHTS))
            continue
        for pref in (0.0, 0.5):
            out.append((f"{p['id']}@{pref:g}", "e2e", tuple(p["origin"]),
                        tuple(p["destination"]), pref, APP_WEIGHTS))
    import geopandas as gpd
    from route_census import sample_pairs
    places = gpd.read_parquet(processed / "place_points.parquet")
    lat, lon = places.geometry.y.to_numpy(), places.geometry.x.to_numpy()
    picked, _ = sample_pairs(lat, lon, per_band, seed)
    for band, chosen in picked.items():
        for n, (i, j, _) in enumerate(chosen):
            for pref in (0.0, 0.5):
                out.append((f"{band[0]:g}-{band[1]:g}:{n:03d}@{pref:g}", "census",
                            (float(lat[i]), float(lon[i])),
                            (float(lat[j]), float(lon[j])), pref, APP_WEIGHTS))
    return out


def route(args):
    from looper import LoopPlanner
    from router import Router
    processed = Path(args.processed)
    plan = trips(processed, args.per_band, args.seed)
    t0 = time.perf_counter()
    r = Router(str(processed))
    print(f"loaded in {time.perf_counter() - t0:.0f}s; {len(plan)} trips", flush=True)
    loops = LoopPlanner(r)
    rows = []
    t0 = time.perf_counter()
    for k, (tid, kind, a, b, pref, weights) in enumerate(plan):
        src, _ = r.snap(*a)
        if kind == "loop":
            loop = loops.plan(src, b, pref, weights, on=JULY)
            res = loop.route if loop is not None else None
        else:
            dst, _ = r.snap_destination(*b)
            res = None if src == dst else r.route(src, dst, pref, weights, on=JULY)
        rows.append({"id": tid, "kind": kind, "pref": pref,
                     "ok": res is not None,
                     "km": res.km if res else np.nan,
                     "minutes": res.minutes if res else np.nan,
                     "edges": res.edges.index.to_numpy() if res else np.empty(0, int)})
        if k % 100 == 0:
            print(f"  {k} of {len(plan)}, {time.perf_counter() - t0:.0f}s", flush=True)
    with open(args.out, "wb") as f:
        pickle.dump(rows, f)
    print(f"wrote {args.out}", flush=True)


def _exposure(edges, km_of, rule_of):
    """km of `edges` (one route, in travel order) on closed, on private in the
    middle, and on unpaved roads."""
    rules = rule_of.reindex(edges).fillna("").to_numpy()
    km = km_of[edges]
    closed = km[rules == "closed"].sum()
    unpaved = km[rules == "unpaved"].sum()
    private = rules == "private"
    # Private in the middle: a private edge after the first public edge and
    # before the last one.
    public = np.flatnonzero(~private)
    middle = 0.0
    if len(public):
        inside = np.zeros(len(edges), bool)
        inside[public[0]:public[-1] + 1] = True
        middle = km[private & inside].sum()
    return closed, middle, unpaved


def compare(args):
    with open(args.before, "rb") as f:
        before = pd.DataFrame(pickle.load(f)).set_index("id")
    with open(args.after, "rb") as f:
        after = pd.DataFrame(pickle.load(f)).set_index("id")
    table = pd.read_parquet(args.table)
    rule_of = table.set_index("edge")["rule"]
    lengths = pd.read_parquet(Path(args.table).parent / "graph_edges.parquet",
                              columns=["length_m"])["length_m"].to_numpy() / 1000.0
    rows = []
    for tid in before.index:
        b, a = before.loc[tid], after.loc[tid]
        row = {"id": tid, "kind": b["kind"], "pref": b["pref"],
               "ok_before": b["ok"], "ok_after": a["ok"]}
        if b["ok"] and a["ok"]:
            row["changed"] = not np.array_equal(b["edges"], a["edges"])
            row["d_km"] = a["km"] - b["km"]
            row["d_min"] = a["minutes"] - b["minutes"]
            for when, rec in (("before", b), ("after", a)):
                c, m, u = _exposure(rec["edges"], lengths, rule_of)
                row[f"closed_km_{when}"], row[f"private_mid_km_{when}"] = c, m
                row[f"unpaved_km_{when}"] = u
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(args.csv, index=False) if args.csv else None
    ok = out[out["ok_before"] & out["ok_after"]]
    print(f"{len(out)} trips; routed both times {len(ok)}; lost "
          f"{int((out['ok_before'] & ~out['ok_after']).sum())}, gained "
          f"{int((~out['ok_before'] & out['ok_after']).sum())}")
    for kind, g in [("all", ok), *ok.groupby("kind")]:
        ch = g[g["changed"]]
        print(f"{kind:7} {len(g):4} trips, {len(ch):3} changed ({len(ch) / max(len(g), 1):.1%})"
              + (f"; of those, median +{ch['d_km'].median():.2f} km "
                 f"+{ch['d_min'].median():.2f} min, max +{ch['d_km'].max():.1f} km "
                 f"+{ch['d_min'].max():.1f} min" if len(ch) else ""))
    for col in ("closed_km", "private_mid_km", "unpaved_km"):
        for when in ("before", "after"):
            v = ok[f"{col}_{when}"]
            print(f"  {col:15} {when:6}: {int((v > 0).sum()):4} trips, {v.sum():8.2f} km")
    for _, r in ok[ok["private_mid_km_after"] > 0].iterrows():
        print(f"  still private in the middle: {r['id']} {r['private_mid_km_after']:.2f} km")
    for _, r in ok[ok["closed_km_after"] > 0].iterrows():
        print(f"  still closed: {r['id']} {r['closed_km_after']:.2f} km")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("route")
    a.add_argument("--processed", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--per-band", type=int, default=50)
    a.add_argument("--seed", type=int, default=20261007)
    c = sub.add_parser("compare")
    c.add_argument("before")
    c.add_argument("after")
    c.add_argument("--table", required=True)
    c.add_argument("--csv")
    args = ap.parse_args()
    route(args) if args.cmd == "route" else compare(args)


if __name__ == "__main__":
    main()
