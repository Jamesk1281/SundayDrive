"""How much of a planned drive has no mobile data coverage, by state.

    .venv/bin/python tools/coverage_on_routes.py --fcc <dir> --lines <lines.ndjson> \\
        [--api http://127.0.0.1:<port> --census 400]

Written for `docs/mid-drive-recovery-plan.md`, question 6.

**Routes.** `--lines` holds route and loop geometries, one JSON object per line
with `group` (`fastest`, `default`, `scenic` or `loop`) and `coords` (`[lon,
lat]`). With `--api` and `--census N` this writes that file first, by asking a
running Sunday Drive server exactly as the app does (a form POST to
`/api/route` and `/api/loop`): N of the seeded census pairs in
`docs/route-census/census-pairs.csv`, stratified by distance band, at pref 0.5
(giving the fastest and the default arm) and 1.0 (the most scenic arm); the 20
loops in `tools/e2e_od_pairs.json` at their own lengths; and 150, 250 and
400 km loops from four of those starts. Point it at a local server, never
production. `tools/corridor_study.py --census N` writes the same file from an
in-process router.

**Coverage.** `--fcc` is a folder holding the FCC National Broadband Map's
mobile broadband H3 downloads for the six states, data as of 31 Dec 2025
("Data Download → By State → Mobile Availability Data → 4G LTE → ESRI
Shapefile", and the same per provider from "By Provider"):

    bdc_<state FIPS>_4GLTE_mobile_broadband_h3_<as-of>_<revision>.zip
    bdc_<state FIPS>_<provider id>_4GLTE_mobile_broadband_h3_<as-of>_<revision>.shp.zip

The first is every provider at once, the second one provider: 130077 AT&T,
130403 T-Mobile, 131425 Verizon. Each row is an H3 resolution-9 cell (about
0.1 km²) where coverage was reported, with `environmnt` 1 for "in-vehicle
mobile and outdoor stationary" and 0 for "outdoor stationary only" (FCC,
*Data Specifications for Broadband Map Data Downloads* §3.1.2.1). 4G LTE in
these files means 5/1 Mbps at a 90% cell-edge probability with 50% cell
loading, the standard every provider has to model to (47 CFR §1.7004(c)).

A point along a route is **covered** if it lies in a cell with `environmnt` 1
— the case that matters to a phone in a moving car — **stationary only** if
its cell has 0, and **uncovered** if it lies in no reported cell.

**State.** Each point takes the state of the nearest reported cell in any
state's every-provider file. Inside a reported cell that is exact. In an
uncovered area it is the nearest covered state, which can be wrong within a
few hundred metres of a state line.

**What this cannot say.** These are provider-modelled maps, not measurements.
The FCC's own 2019 drive tests of the previous generation of maps found no 4G
LTE signal at all on 16% (Verizon) to 38% (US Cellular) of tests in areas
claimed as covered (Mobility Fund Phase II Coverage Maps Investigation Staff
Report, Dec 2019). So "uncovered" here is a floor on what a driver meets, not
an estimate of it.
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
from pyproj import Transformer
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from common import CRS_METERS  # noqa: E402

STEP_M = 50.0
STATES = {"09": "CT", "23": "ME", "25": "MA", "33": "NH", "44": "RI", "50": "VT"}
CARRIERS = {"130077": "AT&T", "130403": "T-Mobile", "131425": "Verizon"}
GROUPS = ("fastest", "default", "scenic", "loop")
LONG_LOOP_STARTS = ("loop-002", "loop-011", "loop-016", "loop-019")

_TO_M = Transformer.from_crs(4326, CRS_METERS, always_xy=True)
_TO_LL = Transformer.from_crs(CRS_METERS, 4326, always_xy=True)
_PAT = re.compile(r"bdc_(\d\d)_(?:(\d+)_)?4GLTE_mobile_broadband_h3_")


# ---------------------------------------------------------------- routes

def _post(api, path, fields):
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(api + path, data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def fetch_lines(api, n, out_path):
    pairs = [r for r in csv.DictReader(open(ROOT / "docs/route-census/census-pairs.csv"))
             if r["status"] == "ok"]
    rng = np.random.default_rng(20261005)
    by_band = defaultdict(list)
    for r in pairs:
        by_band[r["band"]].append(r)
    picked = []
    for band in sorted(by_band):
        rows = by_band[band]
        idx = rng.choice(len(rows), size=min(len(rows), n // len(by_band)), replace=False)
        picked += [rows[i] for i in sorted(idx)]
    od = json.load(open(ROOT / "tools/e2e_od_pairs.json"))
    loops = [p for p in od["pairs"] if p["category"] == "loop"]
    t0 = time.perf_counter()
    with open(out_path, "w") as fh:
        def write(group, key, feature):
            fh.write(json.dumps({"group": group, "key": key,
                                 "km": feature["properties"]["km"],
                                 "coords": feature["geometry"]["coordinates"]}) + "\n")
        for k, r in enumerate(picked):
            frm, to = f"{r['src_lat']},{r['src_lon']}", f"{r['dst_lat']},{r['dst_lon']}"
            try:
                a = _post(api, "/api/route", {"from": frm, "to": to, "pref": "0.50"})
                b = _post(api, "/api/route", {"from": frm, "to": to, "pref": "1.00"})
            except Exception as e:      # an island, a refusal: skip the pair
                print("skip", r["pair_id"], e, flush=True)
                continue
            write("fastest", r["pair_id"], a["fastest"])
            write("default", r["pair_id"], a["scenic"])
            write("scenic", r["pair_id"], b["scenic"])
            if k % 50 == 0:
                fh.flush()
                print(f"routes {k}/{len(picked)} in {time.perf_counter() - t0:.0f} s", flush=True)
        jobs = [(p, p.get("loop_km", 40)) for p in loops]
        jobs += [(p, km) for p in loops if p["id"] in LONG_LOOP_STARTS for km in (150, 250, 400)]
        for p, km in jobs:
            try:
                res = _post(api, "/api/loop", {"from": f"{p['origin'][0]},{p['origin'][1]}",
                                              "km": f"{km:.1f}", "pref": "1.00"})
            except Exception as e:
                print("skip loop", p["id"], km, e, flush=True)
                continue
            write("loop", f"{p['id']}:{km}", res["loop"])
        print(f"lines written in {time.perf_counter() - t0:.0f} s", flush=True)


def sample(coords):
    """Points every STEP_M along a [lon, lat] line, projected to metres."""
    xy = np.array(coords, float)
    x, y = _TO_M.transform(xy[:, 0], xy[:, 1])
    line = shapely.LineString(np.column_stack([x, y]))
    pts = shapely.line_interpolate_point(line, np.arange(0, line.length, STEP_M))
    return np.column_stack([shapely.get_x(pts), shapely.get_y(pts)])


# ---------------------------------------------------------------- cells

def files(folder):
    out = defaultdict(dict)
    for z in sorted(Path(folder).glob("bdc_*_4GLTE_mobile_broadband_h3_*.zip")):
        m = _PAT.match(z.name)
        if m and m.group(1) in STATES:
            out[STATES[m.group(1)]][m.group(2) or "all"] = z
    return out


def read_cells(path):
    cells = gpd.read_file(f"zip://{path}", columns=["environmnt"])
    return cells.geometry.to_crs(CRS_METERS).values, cells["environmnt"].to_numpy().astype(int)


def classify(points_xy, geoms, env):
    """Per point: 1 covered in-vehicle, 0 stationary only, -1 uncovered."""
    tree = shapely.STRtree(geoms)
    pts = shapely.points(points_xy)
    pi, ci = tree.query(pts, predicate="within")
    best = np.full(len(points_xy), -1)
    np.maximum.at(best, pi, env[ci])
    return best


def runs(flags, lengths):
    """Lengths, in km, of the runs of True in a boolean array."""
    out, n = [], 0
    for f in flags:
        if f:
            n += 1
        elif n:
            out.append(n * lengths); n = 0
    if n:
        out.append(n * lengths)
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fcc", required=True)
    ap.add_argument("--lines", required=True)
    ap.add_argument("--api")
    ap.add_argument("--census", type=int, default=400)
    a = ap.parse_args()
    if a.api:
        fetch_lines(a.api.rstrip("/"), a.census, a.lines)

    lines = [json.loads(l) for l in open(a.lines)]
    pts, owner = [], []
    for i, rec in enumerate(lines):
        p = sample(rec["coords"])
        pts.append(p); owner.append(np.full(len(p), i))
    pts = np.concatenate(pts); owner = np.concatenate(owner)
    group = np.array([lines[i]["group"] for i in owner])
    # Each line's points are one contiguous block.
    bounds = np.r_[0, np.cumsum(np.bincount(owner, minlength=len(lines)))]
    print(f"{len(lines)} lines, {len(pts)} points every {STEP_M:.0f} m", flush=True)

    fs = files(a.fcc)
    # Pass 1: state of every point, from the nearest reported cell anywhere.
    cx, cy, cs = [], [], []
    for st, by in sorted(fs.items()):
        geoms, _ = read_cells(by["all"])
        c = shapely.centroid(geoms)
        cx.append(shapely.get_x(c)); cy.append(shapely.get_y(c)); cs += [st] * len(c)
    tree = cKDTree(np.column_stack([np.concatenate(cx), np.concatenate(cy)]))
    _, nearest = tree.query(pts)
    state = np.array(cs)[nearest]

    # Pass 2, one state at a time: every-provider file, then each carrier.
    cls = {k: np.full(len(pts), -2) for k in ["all", *CARRIERS]}
    for st, by in sorted(fs.items()):
        m = state == st
        for prov, path in by.items():
            if prov not in cls:
                continue
            geoms, env = read_cells(path)
            cls[prov][m] = classify(pts[m], geoms, env)
            print(f"{st} {prov}: {len(geoms)} cells, {int(m.sum())} points", flush=True)

    step_km = STEP_M / 1000
    for g in GROUPS:
        gm = group == g
        if not gm.any():
            continue
        print(f"\n== {g} ({len(np.unique(owner[gm]))} lines, "
              f"{gm.sum() * step_km:.0f} km) ==")
        print(f"{'state':5} {'km':>7} {'no carrier':>11} {'no in-veh.':>11} "
              + " ".join(f"{n:>9}" for n in CARRIERS.values()) + "   (no in-vehicle coverage)")
        for st in [*sorted(set(state[gm])), "all"]:
            m = gm & (state == st) if st != "all" else gm
            km = m.sum() * step_km
            row = f"{st:5} {km:7.0f} {100 * (cls['all'][m] < 0).mean():10.2f}% " \
                  f"{100 * (cls['all'][m] < 1).mean():10.2f}% "
            row += " ".join(f"{100 * (cls[p][m] < 1).mean():8.2f}%" for p in CARRIERS)
            print(row)
        # How many drives meet a dead stretch at all: the share of lines with at
        # least one run of 1 km or more, with no carrier at all, and with no
        # in-vehicle coverage from any carrier and from each.
        ids = np.unique(owner[gm])
        def share_with(key, below):
            hit = 0
            for i in ids:
                if any(r >= 1.0 for r in runs(cls[key][bounds[i]:bounds[i + 1]] < below, step_km)):
                    hit += 1
            return 100 * hit / len(ids)
        print(f"  drives crossing 1 km or more with no 4G LTE from any carrier: "
              f"{share_with('all', 0):.0f}%; with no in-vehicle coverage from any carrier: "
              f"{share_with('all', 1):.0f}%; from " + ", ".join(
                  f"{n} {share_with(p, 1):.0f}%" for p, n in CARRIERS.items()))
        # Dead stretches, along each line, from no carrier at all and per carrier.
        for label, key in (("any carrier", "all"), *[(n, p) for p, n in CARRIERS.items()]):
            stretch = []
            for i in np.unique(owner[gm]):
                stretch += runs(cls[key][bounds[i]:bounds[i + 1]] < 1, step_km)
            s = np.array(stretch)
            if len(s):
                print(f"  stretches with no in-vehicle coverage, {label}: {len(s)}, "
                      f"p50 {np.median(s):.2f} km, p90 {np.percentile(s, 90):.2f} km, "
                      f"max {s.max():.1f} km; share of those km in stretches of 2 km or more "
                      f"{100 * s[s >= 2].sum() / s.sum():.0f}%")


if __name__ == "__main__":
    main()
