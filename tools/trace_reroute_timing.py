"""How reroutes went on real drives: reply times, silences, runs the wrong way.

    .venv/bin/python tools/trace_reroute_timing.py <main>/traces/*.ndjson

Written for the 2026-10-07 revision of `docs/mid-drive-recovery-plan.md`,
beside `tools/trace_excursions.py`, which measures how far drives strayed.
This one reads what that one does not:

- **Reply time.** A `route` record carries `req_lat`/`req_lon`, the fix the
  request was made from (`DriveTrace.route`, since the 2026-08-26 audit), so
  the fix with exactly those coordinates is when the request left, and the
  record's own `ts` is when the reply was adopted. Traces older than those
  fields are skipped for this part.
- **Silences.** A failed request leaves nothing in a trace: `reroute` drops it
  in a `try?` before anything is written. So the trace cannot count failures.
  What it can show is a stretch the car spent more than `OFF_M` off the line it
  had reached and was following, joined and moving, for at least
  `SILENCE_S`, with no reply landing. `NavigationModel` asks within seconds of 60 m and at most every
  120 s after that, so a silence that long is either failed requests or a
  guard holding them back. Which it was needs a replay (the plan's §1.5).
- **Runs the wrong way.** Runs of `RUN_FIXES` or more moving on-line fixes
  whose course points 120 degrees or more against the line, each with how long
  after its line was adopted it began and how far back along the line it went.
  A run starting seconds after an adoption is a replacement opening behind the
  car (the plan's §4.1, case 2). One starting long after is a car on a line it
  had been following, now driving it backwards: P-05.

**The traces are private** (`.gitignore`, "Drive traces"). Like
`trace_excursions.py`, this prints counts, durations and distances only, never
a coordinate, a street, a town or a timestamp.
"""

import json
import sys
from pathlib import Path

import numpy as np
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trace_excursions import GAP_S, OFF_M, _TO_M, read  # noqa: E402

# A silence must last this long to be reported. Twice the 8 s first cooldown
# plus the 15 s request timeout: past it, a working reroute would have landed.
SILENCE_S = 30.0
# The wrong-way detector's own vote count (plan §4.2, rule 5).
RUN_FIXES = 5
# A run beginning within this long of its line's adoption is a replacement
# opening behind the car, not a reversal.
ADOPTION_S = 20.0


def records(path):
    out = []
    with open(path) as fh:
        for raw in fh:
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return out


def reply_times(recs):
    fixes = [r for r in recs if r.get("t") == "fix"]
    out = []
    for r in recs:
        if r.get("t") != "route" or "req_lat" not in r:
            continue
        sent = [f["ts"] for f in fixes if f["ts"] <= r["ts"]
                and f["lat"] == r["req_lat"] and f["lon"] == r["req_lon"]]
        if sent:
            out.append(r["ts"] - sent[-1])
    return out


def silences(path, recs):
    lines, fixes = read(path)
    if not fixes or not lines:
        return []
    first = min(lines)
    x, y = _TO_M.transform(np.array([f["lon"] for f in fixes]),
                           np.array([f["lat"] for f in fixes]))
    pts = shapely.points(np.column_stack([x, y]))
    ts = np.array([f["ts"] for f in fixes], float)
    seq = np.array([f.get("route", first) for f in fixes])
    joined = np.array([bool(f.get("joined")) for f in fixes])
    spd = np.array([f.get("spd") if f.get("spd") is not None else -1 for f in fixes], float)
    d = np.full(len(fixes), np.nan)
    for s in np.unique(seq):
        if s in lines:
            m = seq == s
            d[m] = shapely.distance(pts[m], lines[s][1])
    step = np.r_[0.0, np.hypot(np.diff(x), np.diff(y))]
    dt = np.r_[0.0, np.diff(ts)]
    replies = np.array(sorted(r["ts"] for r in recs if r.get("t") == "route"
                              and r.get("seq", 0) > 0), float)

    out, i, n = [], 0, len(fixes)
    while i < n:
        if not (joined[i] and d[i] > OFF_M):
            i += 1
            continue
        j = i
        while j + 1 < n and joined[j + 1] and d[j + 1] > OFF_M:
            j += 1
        # Only a car that had reached this line and left it. Before it gets
        # there it is on its way to a replacement's first junction, and
        # `awaitingJoin` holds reroutes off on purpose (trace_excursions'
        # "join gaps").
        same = np.where(seq[:i] == seq[i])[0]
        if not (len(same) and (d[same] <= OFF_M).any()):
            i = j + 1
            continue
        # Split at each reply: the silence is the stretch no reply landed in.
        cuts = [ts[i]] + [t for t in replies if ts[i] < t <= ts[j]] + [ts[j]]
        for a, b in zip(cuts, cuts[1:]):
            m = (ts >= a) & (ts <= b)
            moving = (spd[m] >= 3).mean() if m.any() else 0
            if b - a >= SILENCE_S and moving >= 0.5:
                mm = m & (dt <= GAP_S)
                out.append({"seconds": float(b - a),
                            "metres": float(step[mm].sum()),
                            "max_off": float(np.nanmax(d[m]))})
        i = j + 1
    return out


def wrong_way_runs(path, recs):
    lines, fixes = read(path)
    adopted = {r["seq"]: r["ts"] for r in recs if r.get("t") == "route"}
    runs, run = [], []

    def close():
        if len(run) >= RUN_FIXES:
            s = run[0][1]
            runs.append({"fixes": len(run),
                         "after_adoption_s": float(run[0][0] - adopted.get(s, run[0][0])),
                         "back_m": float(run[0][2] - run[-1][2])})

    for f in fixes:
        s = f.get("route")
        spd, crs = f.get("spd"), f.get("crs")
        ok = (s in lines and f.get("joined") and spd is not None and spd >= 3
              and crs is not None and crs >= 0)
        if ok:
            x, y = _TO_M.transform(f["lon"], f["lat"])
            line, pt = lines[s][1], shapely.Point(x, y)
            ok = line.distance(pt) <= 15
        if not ok:
            close(); run = []
            continue
        a = line.project(pt)
        p, q = line.interpolate(max(0, a - 10)), line.interpolate(min(line.length, a + 10))
        bearing = np.degrees(np.arctan2(q.x - p.x, q.y - p.y)) % 360
        if abs((crs - bearing + 180) % 360 - 180) >= 120:
            run.append((f["ts"], s, a))
        else:
            close(); run = []
    close()
    return runs


def main(paths):
    rtt, quiet, runs = [], [], []
    for p in paths:
        recs = records(p)
        rtt += reply_times(recs)
        quiet += silences(p, recs)
        runs += wrong_way_runs(p, recs)

    print(f"drives: {len(paths)}")
    if rtt:
        r = np.array(rtt)
        print(f"replies with a request origin: {len(r)}   seconds from request to adoption: "
              f"p50 {np.median(r):.2f}  p90 {np.percentile(r, 90):.2f}  max {r.max():.2f}  "
              f"over 3 s: {(r > 3).sum()}")
    else:
        print("replies with a request origin: 0 (traces predate req_lat)")
    print(f"silences: off the line past {OFF_M:.0f} m, moving, {SILENCE_S:.0f} s or more "
          f"with no reply landing: {len(quiet)}")
    for q in sorted(quiet, key=lambda q: -q["seconds"]):
        print(f"   {q['seconds']:5.0f} s  {q['metres']:6.0f} m driven  up to {q['max_off']:5.0f} m off")
    print(f"runs of {RUN_FIXES}+ fixes 120 degrees or more against the line: {len(runs)}")
    early = [r for r in runs if r["after_adoption_s"] <= ADOPTION_S]
    late = [r for r in runs if r["after_adoption_s"] > ADOPTION_S]
    print(f"   beginning within {ADOPTION_S:.0f} s of their line's adoption: {len(early)}"
          + (f", longest {max(r['fixes'] for r in early)} fixes" if early else ""))
    print(f"   beginning later, on a line already being followed: {len(late)}")
    for r in sorted(late, key=lambda r: -r["fixes"]):
        print(f"   {r['fixes']:4d} fixes  {r['back_m']:6.0f} m back along the line  "
              f"{r['after_adoption_s'] / 60:6.0f} min after adoption")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
