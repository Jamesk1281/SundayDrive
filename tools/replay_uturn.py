"""Replay recorded reroutes with and without the declined-U-turn rule.

    .venv/bin/python tools/replay_uturn.py <processed-ne> <main>/traces/*.ndjson
    .venv/bin/python tools/replay_uturn.py <processed-ne> --sample 400

Written for `docs/reroute-uturn.md`. A reroute record carries the request it
answered (`req_lat`, `req_lon`, `req_heading`, `req_pref`) and the drive record
its destination and weights, so every reroute can be asked again of a local
router. This asks each one twice: as it was sent, and with `declined_uturn`
wherever the app's rule would have set it, and prints whether each answer
turns the driver around (`router.turnaround_at`) and what it costs
against the route the drive was actually sent.

Which requests carry the flag is decided the way `NavigationModel` decides it:
a reroute away from a route that turned the driver around, made before they
had driven `PROGRESS_M` past the point where it starts to (`turnaround_m`),
declines it, and the flag stays set until they drive `PROGRESS_M` past that
point, or past where they joined a route that goes on ahead. Progress is read off the recorded
fixes, so it is the progress the driver really made on the routes they were
really sent. A replay cannot know where they would have driven had they been
sent something else, and this does not pretend to: every request is asked from
where it was really made.

Traces recorded before `req_*` existed are rebuilt from the last fix before
the route record — its position, and its course if the car was moving — and
marked `~`. The server they were sent to may not have had the heading at all,
so treat those rows as indicative.

`--sample` instead plants random mid-drive departures on the road network,
heading along the road, each with a random destination 3-60 km away, and
reports what keeping ahead costs where the cheapest route turns around.

**The traces are private.** They record where someone drove, to the second
(`.gitignore`, "Drive traces"). This prints trace names, sequence numbers,
distances and durations only — never a coordinate, a street or a clock time.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import router as R  # noqa: E402

# NavigationModel.declinedUTurnProgressMeters and joinConfirmMeters.
PROGRESS_M = 100.0
ON_LINE_M = 30.0
# NavigationModel.minSpeedForHeading, for the rebuilt requests.
MIN_SPEED_FOR_HEADING = 2.0


def requests(path: Path):
    """Each reroute in one trace: the request, and the route that answered."""
    recs = [json.loads(line) for line in path.open()]
    drive = recs[0]
    fixes = [r for r in recs if r.get("t") == "fix"]
    day = dt.date.fromisoformat(drive["started"][:10])
    pref = drive.get("pref", 0.5)
    for rec in recs:
        if rec.get("t") != "route":
            continue
        if rec["reason"].startswith("fastest"):
            pref = 0.0
        if rec["seq"] == 0:
            req = None
        elif "req_lat" in rec:
            req = dict(lat=rec["req_lat"], lon=rec["req_lon"],
                       heading=rec.get("req_heading"),
                       pref=rec.get("req_pref", pref), rebuilt=False)
        else:
            before = [f for f in fixes if f["ts"] <= rec["ts"] - 0.5]
            if not before:
                continue
            f = before[-1]
            moving = f.get("crs", -1) >= 0 and f.get("spd", 0) >= MIN_SPEED_FOR_HEADING
            req = dict(lat=f["lat"], lon=f["lon"],
                       heading=f["crs"] if moving else None, pref=pref,
                       rebuilt=True)
        turn_at = None
        if req is not None and req["heading"] is not None:
            turn_at = R.turnaround_at(np.asarray(rec["coords"]),
                                      (req["lat"], req["lon"]), req["heading"])
        on_it = [f for f in fixes if f.get("route") == rec["seq"]]
        yield dict(seq=rec["seq"], reason=rec["reason"], req=req, rec=rec,
                   dest=drive["dest"], weights=drive.get("weights", {}),
                   day=day, turns=turn_at is not None,
                   progressed=progressed(on_it, turn_at))


def progressed(fixes, turn_at) -> bool:
    """Whether the driver drove PROGRESS_M past where a route turned them
    around, or past where they joined it if it didn't, while on it."""
    mark = None
    for f in fixes:
        if not f.get("joined"):
            continue
        if mark is None:
            mark = max(turn_at or 0.0, f["travelled"]) + PROGRESS_M
        if f.get("off", 1e9) <= ON_LINE_M and f["travelled"] >= mark:
            return True
    return False


def ask(router, q, declined: bool):
    """What /api/route answers for this request, as server/app.py builds it."""
    req = q["req"]
    heading = req["heading"]
    origin = (req["lat"], req["lon"])
    s, _ = router.snap(req["lat"], req["lon"], heading=heading)
    t, _ = router.snap_destination(*q["dest"])
    pref = max(0.0, min(1.0, req["pref"] if req["pref"] is not None else 0.5))
    kw = dict(heading=heading, on=q["day"], origin=origin, keep_ahead=declined)
    fastest = router.route(s, t, 0.0, q["weights"], **kw)
    if pref == 0.0 or fastest is None:
        return fastest
    scenic = router.route(s, t, pref, q["weights"], **kw)
    if scenic is None:
        return None
    return fastest if scenic.mean_score < fastest.mean_score else scenic


def why_still(router, q) -> str:
    """For a flagged request still answered by a turnaround: no way on, or
    the cap. Asked again with the cap lifted."""
    cap = R.TURN_BACK_CAP_MIN
    R.TURN_BACK_CAP_MIN = float("inf")
    try:
        uncapped = ask(router, q, True)
    finally:
        R.TURN_BACK_CAP_MIN = cap
    if uncapped is None or uncapped.turns_around:
        return "no way ahead"
    return f"capped: ahead was +{uncapped.minutes - ask(router, q, False).minutes:.1f} min"


def replay(router, paths):
    print(f"{'trace':24s} {'seq':>3s} {'reason':10s} {'sent':4s} {'flag':4s} "
          f"{'now':4s} {'d km':>6s} {'d min':>6s}  note")
    for path in paths:
        declined = False
        previous = None
        for q in requests(path):
            if q["req"] is not None and previous is not None:
                if previous["turns"] and not previous["progressed"]:
                    declined = True
                q_turns = q["turns"]
                if q["req"]["heading"] is not None:
                    flag = declined
                    got = ask(router, q, flag)
                    rec = q["rec"]
                    note = "~ rebuilt request" if q["req"]["rebuilt"] else ""
                    if flag and got is not None and got.turns_around:
                        note = (note + "; " if note else "") + why_still(router, q)
                    print(f"{path.stem[6:]:24s} {q['seq']:3d} {q['reason'][:10]:10s} "
                          f"{'U' if q_turns else '-':4s} {'set' if flag else '':4s} "
                          f"{'U' if got is not None and got.turns_around else '-':4s} "
                          f"{(got.km - rec['km']) if got else float('nan'):+6.1f} "
                          f"{(got.minutes - rec['minutes']) if got else float('nan'):+6.1f}  {note}")
            if q["progressed"]:
                declined = False
            previous = q


def sample(router, n: int, seed: int):
    """Random mid-drive departures: what keeping ahead costs where the
    cheapest route turns around. Fastest arm only, for speed."""
    to_ll = Transformer.from_crs(R.CRS_METERS, 4326, always_xy=True)
    rng = np.random.default_rng(seed)
    km = router.km[router.eidx]
    hw = router.edges["highway"].astype(str).to_numpy()
    drivable = np.isin(hw[router.eidx], [
        "motorway", "motorway_link", "trunk", "trunk_link", "primary",
        "primary_link", "secondary", "secondary_link", "tertiary",
        "tertiary_link", "unclassified", "residential"])
    slots = np.flatnonzero(drivable & (km > 0.05))
    p = km[slots] / km[slots].sum()

    def point(k, at):
        line = router._edge_geom_m[int(router.eidx[k])]
        return line, line.interpolate(at * line.length)

    asked = turned = no_way = capped = 0
    extra_min, extra_km = [], []
    while asked < n:
        k = int(rng.choice(slots, p=p))
        line, here = point(k, rng.uniform(0.2, 0.8))
        tangent = R._tangent_at(line, here)
        if tangent is None:
            continue
        heading = (tangent + 180.0) % 360.0 if router.flip[k] else tangent
        _, there = point(int(rng.choice(slots, p=p)), 0.5)
        if not 3000.0 < here.distance(there) < 60000.0:
            continue
        lon, lat = to_ll.transform(here.x, here.y)
        dlon, dlat = to_ll.transform(there.x, there.y)
        s, _ = router.snap(lat, lon, heading=heading)
        t, _ = router.snap_destination(dlat, dlon)
        if s == t:
            continue
        kw = dict(heading=heading, origin=(lat, lon))
        base = router.route(s, t, 0.0, {}, **kw)
        if base is None:
            continue
        asked += 1
        if not base.turns_around:
            continue
        turned += 1
        cap = R.TURN_BACK_CAP_MIN
        R.TURN_BACK_CAP_MIN = float("inf")
        try:
            ahead = router.route(s, t, 0.0, {}, keep_ahead=True, **kw)
        finally:
            R.TURN_BACK_CAP_MIN = cap
        if ahead.turns_around:
            no_way += 1
            continue
        extra_min.append(ahead.minutes - base.minutes)
        extra_km.append(ahead.km - base.km)
        capped += extra_min[-1] > cap
    m, k_ = np.array(extra_min), np.array(extra_km)
    print(f"{asked} departures; the cheapest route turned around on {turned}")
    print(f"  no way ahead: {no_way}; a way ahead: {len(m)}, "
          f"of which over the {R.TURN_BACK_CAP_MIN:.0f} min cap: {capped}")
    pct = [50, 75, 90, 95, 99, 100]
    print("  extra minutes, p50/75/90/95/99/max:", np.percentile(m, pct).round(1))
    print("  extra km,      p50/75/90/95/99/max:", np.percentile(k_, pct).round(1))
    for thr in (5, 10, 15, 20, 30):
        print(f"  over {thr:2d} min: {int((m > thr).sum())}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("processed")
    ap.add_argument("traces", nargs="*", type=Path)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20261006)
    args = ap.parse_args()
    router = R.Router(args.processed)
    if args.traces:
        replay(router, sorted(args.traces))
    if args.sample:
        sample(router, args.sample, args.seed)


if __name__ == "__main__":
    main()
