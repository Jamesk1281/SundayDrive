"""Q3: what a wrong "open" costs the driver, replayed through the server's own
`_route` (harness.route, POST /api/route).

For each case (a named road crossed gateway to gateway, both ways, or a
seasonal stretch a Q1 route used):

1. Plan the trip on a shoulder day the router calls open: the first open day
   of our effective window (spring), and the last (autumn). pref 0.5.
2. The driver reaches the closed road: the first edge of it on the planned
   scenic route, arriving the way the route arrived (the brief's trap 4: the
   window's first edge, not the nearest junction).
3. It is shut. They turn round, 30 m back from the closure, facing away.
   With the road closed for the reroute (harness.set_avoid, standing in for
   P5's avoid parameter) the server's reply is what the driver must actually
   drive: (b) the extra minutes and km to the destination over the plan,
   and (c) how far they backtrack before that way out leaves the road they
   came in by, the "middle of nowhere" number.
4. P0, today: the reroutes the app would get, asked along that way out at
   30 m and 1, 2, 5, 10, 20, 40 and 80 km from the closure, and just past
   the junction where it leaves the approach. Each is asked plain and, where
   it turns the driver round (`turns_around`), again with `declined_uturn`,
   as the app does once they keep going. Recorded: (a) whether the reply
   drives back into the closed road.

A dead-end case (an auto road to a summit) has no way on: its cost is the
drive to the gate and back to where it started.

  python q3_turnaround.py [--cases named|top|all] [--only beartooth,tioga]
  -> q3_reroutes.csv (one row per reroute asked), q3_cases.csv (one per case)
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
# Replay the real P5 parameter beside P0 (`--real-p5`): the build's
# measurement, docs/seasonal-road-policy.md.
REAL_P5 = False
ALONG_KM = (0.03, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0)
PREF = 0.5


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(a))


def bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def walk_back(coords: np.ndarray, back_m: float):
    """The point `back_m` before the end of `coords` ([lon, lat] in travel
    order), and the course of a car driving away from the end there."""
    pts = coords[::-1]
    run = 0.0
    for i in range(1, len(pts)):
        lon0, lat0 = pts[i - 1]
        lon1, lat1 = pts[i]
        seg = haversine_m(lat0, lon0, lat1, lon1)
        if seg > 0 and run + seg >= back_m:
            f = (back_m - run) / seg
            lat, lon = lat0 + f * (lat1 - lat0), lon0 + f * (lon1 - lon0)
            return (lat, lon), bearing(lat0, lon0, lat1, lon1), back_m
        run += seg
    lon0, lat0 = pts[-2]
    lon1, lat1 = pts[-1]
    return (lat1, lon1), bearing(lat0, lon0, lat1, lon1), run


def ask(h, pos, b, course, avoid=None):
    """One reroute as the app asks it: plain, then with `declined_uturn` if
    the reply turns the driver round. (scenic result or None, status, json,
    whether it was declined). `avoid` is P5's (avoid_edges, avoid_pack), sent
    with both, as the app sends it with every reroute."""
    st, js, res = h.route(pos, b, pref=PREF, heading=course, avoid=avoid)
    r = scenic(res) if st == 200 else None
    if r is not None and r.turns_around:
        st, js, res = h.route(pos, b, pref=PREF, heading=course, declined_uturn=True,
                              avoid=avoid)
        r = scenic(res) if st == 200 else None
        return r, st, js, True
    return r, st, js, False


def scenic(res):
    return res[1] if len(res) == 2 else None


def enters(result, closed: set) -> bool:
    return bool(set(int(x) for x in result.edges.index) & closed)


def backtrack_m(result, approach_edges: list) -> float:
    """Metres the route drives back over the approach before leaving it."""
    seen = set(approach_edges)
    m = 0.0
    for e, length in zip(result.edges.index, result.edges["length_m"]):
        if int(e) not in seen:
            break
        m += float(length)
    return m


# The app's rule (ios/Sources/NavigationModel.swift, `noteTurnedAway`): a
# stretch the car is on, or that starts within this far ahead, when the
# wrong-way episode opens.
TURNED_AWAY_AHEAD_M = 25_000


def turned_away(plan_json, along_m):
    """(avoid_edges, avoid_pack) for the stretches of the plan's scenic arm
    the app marks when the driver turns round `along_m` metres along it, or
    None when it marks none."""
    marked = [s for s in plan_json["scenic"]["properties"].get("seasonal", [])
              if s["from_m"] - TURNED_AWAY_AHEAD_M <= along_m <= s["to_m"]]
    if not marked:
        return None
    tokens = list(dict.fromkeys(("" if f else "-") + str(e) for s in marked[::-1]
                                for e, f in zip(s["edges"], s["forward"])))
    return ",".join(tokens), marked[0]["pack"]


def run_case(h, W, case, day, rows_out, replay=True):
    """One case on one shoulder day; returns the case row. `replay=False`
    skips the P0 reroutes and measures only the detour."""
    h.set_day(day)
    h.set_avoid(None)
    a, b = case["a"], case["b"]
    st, js, res = h.route(a, b, pref=PREF)
    base = dict(case=case["name"], road=case["road"], day=day.isoformat(), shoulder=case["shoulder"])
    if st != 200 or not res:
        return {**base, "status": f"plan {st} {(js or {}).get('code', '')}"}
    plan = scenic(res)
    plan_json = js
    edges = [int(x) for x in plan.edges.index]
    closed = set(case["closed_edges"])
    hit = [k for k, e in enumerate(edges) if e in closed]
    if not hit:
        return {**base, "status": "plan avoids the road", "plan_min": plan.minutes, "plan_km": plan.km}
    k = hit[0]
    approach = edges[:k]
    mins = np.asarray(plan.edge_minutes, float)
    km = plan.edges["length_m"].to_numpy() / 1000.0
    approach_min, approach_km = float(mins[:k].sum()), float(km[:k].sum())
    coords = np.vstack([plan.edge_coords[i] for i in range(k)] + [plan.edge_coords[k][:1]]) \
        if k else np.asarray(plan.edge_coords[0][:2])
    gate = coords[-1]
    row = {**base, "status": "ok", "plan_min": plan.minutes, "plan_km": plan.km,
           "gate_lat": float(gate[1]), "gate_lon": float(gate[0]), "gate_edge": edges[k],
           "approach_min": approach_min, "approach_km": approach_km,
           "closed_km_on_plan": float(km[hit].sum())}

    # The road shut for the reroute: P5, and what the driver must drive.
    h.set_avoid(sorted(closed))
    pos, course, _ = walk_back(coords, ALONG_KM[0] * 1000)
    r, st, js, declined = ask(h, pos, b, course)
    rows_out.append({**base, "policy": "P5", "along_km": ALONG_KM[0], "status": st,
                     "code": (js or {}).get("code", "") if st != 200 else "",
                     "declined_uturn": declined, "sends_back": bool(r is not None and enters(r, closed)),
                     "minutes": r.minutes if r is not None else None, "km": r.km if r is not None else None})
    h.set_avoid(None)
    if r is not None:
        way_out = np.asarray(r.line.coords)
        row.update(p5_min=r.minutes, p5_km=r.km,
                   detour_min=approach_min + r.minutes - plan.minutes,
                   detour_km=approach_km + r.km - plan.km,
                   backtrack_km=backtrack_m(r, approach[::-1]) / 1000.0)
    else:
        # No way on: a dead end, or the destination is up the closed road.
        # They drive back the way they came.
        way_out = coords[::-1]
        row.update(p5_status=f"{st} {(js or {}).get('code', '')}",
                   detour_min=2 * approach_min, detour_km=2 * approach_km,
                   backtrack_km=approach_km)
    if not replay:
        return row

    # P0: the reroutes the app gets today, asked along the way out the driver
    # actually has to take (P5's route, or the approach reversed), so they
    # cover the junction where the driver must leave the road they came in
    # by, and beyond it.
    out_km = float(np.sum([haversine_m(la0, lo0, la1, lo1) for (lo0, la0), (lo1, la1)
                           in zip(way_out[:-1], way_out[1:])])) / 1000.0
    points = sorted(set([x for x in ALONG_KM if x < out_km - 0.5]
                        + ([row["backtrack_km"] + 0.2] if row["backtrack_km"] + 0.2 < out_km - 0.5 else [])))
    first_clear, at_gate, sent_back, at_junction = None, None, 0, None
    # P5 as built: the stretches the app marks when the driver turns round
    # 30 m short of the closed road, sent with every reroute below.
    avoid = turned_away(plan_json, approach_km * 1000 - ALONG_KM[0] * 1000)
    row["p5_marked_edges"] = 0 if avoid is None else len(avoid[0].split(","))
    for along in points:
        # `walk_back` measures from the end of its line: hand it the way out
        # reversed, and it walks forward from the gate, facing on.
        pos, course, actual = walk_back(way_out[::-1], along * 1000)
        r, st, js, declined = ask(h, pos, b, course)
        back_in = r is not None and enters(r, closed)
        rows_out.append({**base, "policy": "P0", "along_km": round(actual / 1000, 3), "status": st,
                         "code": (js or {}).get("code", "") if st != 200 else "",
                         "declined_uturn": declined, "sends_back": back_in,
                         "minutes": r.minutes if r is not None else None,
                         "km": r.km if r is not None else None})
        if REAL_P5:
            r5, st5, js5, declined5 = ask(h, pos, b, course, avoid=avoid)
            rows_out.append({**base, "policy": "P5 built", "along_km": round(actual / 1000, 3),
                             "status": st5, "code": (js5 or {}).get("code", "") if st5 != 200 else "",
                             "declined_uturn": declined5,
                             "sends_back": r5 is not None and enters(r5, closed),
                             "minutes": r5.minutes if r5 is not None else None,
                             "km": r5.km if r5 is not None else None,
                             "marked": avoid is not None})
        if at_gate is None:
            at_gate = back_in
        if at_junction is None and along >= row["backtrack_km"]:
            at_junction = back_in
        sent_back += back_in
        if not back_in and first_clear is None and r is not None:
            first_clear = actual / 1000
    row.update(p0_sends_back_at_gate=at_gate, p0_sends_back_past_junction=at_junction,
               p0_reroutes_asked=len(points), p0_reroutes_sending_back=sent_back,
               p0_first_clear_km=first_clear)
    # What P0 adds and P5 removes. Up to the junction where the way out leaves
    # the approach, "turn round" from the app costs nothing extra: the driver
    # has to drive back there anyway. Past it, a driver who follows the app
    # misses that turn. They are charged the drive from the junction out to
    # where the app stops pointing back, and the drive back again, at the way
    # out's own speed. Where it never stops, the charge runs to the farthest
    # point asked.
    clear = first_clear if first_clear is not None else (max(points) if points else 0.0)
    over = max(0.0, clear - row["backtrack_km"]) if sent_back else 0.0
    km_, min_ = (row["p5_km"], row["p5_min"]) if "p5_km" in row else (approach_km, approach_min)
    # A trip that starts at the closure has no approach to take a speed
    # from: 1 km a minute, 60 km/h.
    speed = km_ / min_ if km_ > 0 and min_ > 0 else 1.0
    row["p0_extra_min"] = 2 * over / speed
    h.set_avoid(None)
    return row


def named_cases(h, W, R, table):
    cases = []
    for key, spec in R.ROADS.items():
        rows = R.edges_of(table, key, h.edge_lonlat)
        if not len(rows):
            continue
        closed = sorted(set(int(e) for e in rows["edge"]))
        m = np.logical_or.reduce(list(W.edge_masks(rows).values()))
        open_days = np.flatnonzero(~m)
        if not len(open_days):
            continue
        runs = np.split(open_days, np.flatnonzero(np.diff(open_days) > 1) + 1)
        season = max(runs, key=len)
        pairs = [("ab", spec["ends"][0], spec["ends"][1])]
        if not spec.get("dead_end"):
            pairs.append(("ba", spec["ends"][1], spec["ends"][0]))
        for tag, a, b in pairs:
            for shoulder, d in (("spring", season[0]), ("autumn", season[-1])):
                cases.append(dict(name=f"{key}:{tag}", road=key, a=list(a), b=list(b), shoulder=shoulder,
                                  day=W.day_of(d), closed_edges=closed))
    return cases


def top_cases(h, W, table, n=15):
    """The seasonal stretches the most Q1 routes used, open in August: each
    the run of consecutive seasonal edges on the route that used it."""
    q1 = pd.read_csv(HERE / "q1_routes.csv")
    q1 = q1[(q1.run == "open") & (q1.arm == "scenic") & q1.seasonal_edges.notna()]
    samples = {t["name"]: t for t in json.load(open(HERE / "samples.json"))}
    use = {}
    for _, r in q1.iterrows():
        for e in str(r.seasonal_edges).split():
            use.setdefault(int(e), []).append(r.trip)
    km = table.drop_duplicates("edge").set_index("edge")["length_m"] / 1000.0
    ranked = sorted(use, key=lambda e: -len(use[e]) * km.get(e, 0))
    masks = W.edge_masks(table)
    seen, cases = set(), []
    for e in ranked:
        if e in seen or len(cases) >= n:
            continue
        trip = samples[use[e][0]]
        m = masks[e]
        open_days = np.flatnonzero(~m)
        if not len(open_days):
            continue
        runs = np.split(open_days, np.flatnonzero(np.diff(open_days) > 1) + 1)
        season = max(runs, key=len)
        # The stretch: every seasonal edge this trip's route used.
        q = q1[q1.trip == trip["name"]].iloc[0]
        stretch = sorted(int(x) for x in str(q.seasonal_edges).split())
        seen.update(stretch)
        for shoulder, d in (("spring", season[0]), ("autumn", season[-1])):
            cases.append(dict(name=f"top:{e}", road=str(q.named) if isinstance(q.named, str) else "",
                              a=trip["a"], b=trip["b"], shoulder=shoulder, day=W.day_of(d),
                              closed_edges=stretch))
    return cases


def trip_cases(h, W):
    """Every Q1 trip whose all-open scenic route uses a seasonal edge, planned
    on the all-open graph, with every seasonal edge on it closed for the
    reroute: the driver meets the first one. Detour only, for Q4's D(i)."""
    q1 = pd.read_csv(HERE / "q1_routes.csv")
    q1 = q1[(q1.run == "open") & (q1.arm == "scenic") & q1.seasonal_edges.notna()]
    samples = {t["name"]: t for t in json.load(open(HERE / "samples.json"))}
    from datetime import date
    return [dict(name=f"trip:{r.trip}", road=str(r.named) if isinstance(r.named, str) else "",
                 a=samples[r.trip]["a"], b=samples[r.trip]["b"], shoulder="all-open",
                 day=date(2026, 8, 15), closed_edges=[int(x) for x in str(r.seasonal_edges).split()])
            for r in q1.itertuples()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="named")
    ap.add_argument("--only", default="")
    ap.add_argument("--real-p5", action="store_true",
                    help="also ask each P0 reroute with the app's avoid_edges")
    args = ap.parse_args()
    global REAL_P5
    REAL_P5 = args.real_p5
    sys.path.insert(0, str(HERE))
    import harness as h
    import roads as R
    import windows as W
    table = W.annotate(h.BASE_TABLE)
    h.open_to_cars(h.trail_ridge_permit_edges())
    cases = []
    if args.cases in ("named", "all"):
        cases += named_cases(h, W, R, table)
    if args.cases in ("top", "all"):
        cases += top_cases(h, W, table)
    if args.cases == "trips":
        h.set_table(table.iloc[:0])
        cases = trip_cases(h, W)
    if args.only:
        keep = set(args.only.split(","))
        cases = [c for c in cases if c["road"] in keep or c["name"] in keep]
    rows, out = [], []
    t0 = time.time()
    for c in cases:
        out.append(run_case(h, W, c, c["day"], rows, replay=args.cases != "trips"))
        print(f"{c['name']} {c['shoulder']} {out[-1].get('status')} "
              f"detour {out[-1].get('detour_min', float('nan')):.0f} min, {time.time() - t0:.0f}s", flush=True)
        suffix = "" if args.cases == "named" else f"_{args.cases}"
        pd.DataFrame(rows).to_csv(HERE / f"q3_reroutes{suffix}.csv", index=False)
        pd.DataFrame(out).to_csv(HERE / f"q3_cases{suffix}.csv", index=False)


if __name__ == "__main__":
    main()
