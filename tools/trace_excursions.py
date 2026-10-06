"""How far real drives strayed from their route, in aggregate only.

    .venv/bin/python tools/trace_excursions.py <main>/traces/*.ndjson

Written for `docs/mid-drive-recovery-plan.md` (question 6). A road corridor
shipped with each route only helps a driver who is still inside it, so its
width has to come from how far real drives actually went from the line, not
from a guess. The traces record that directly: every `fix` names the route it
was matched against (`route`, the `seq` of the last `route` record), so the
distance from each fix to that line is a measurement, not an inference.

Two distances per fix, because a corridor can be shipped two ways:

- **from the line being followed** — the route the app held at that moment,
  replacements included. This is what a corridor shipped with *each* route
  (the original and every reroute) has to contain.
- **from the original line** — the route the drive started with. This is what
  a corridor shipped once, at the start, has to contain, which is the only
  corridor a drive that has lost its server still holds.

`off` in the trace is not used. It is the *constrained* match, measured from a
floor that can pin it behind the car (`NavigationModel.reseatIfPinned`), so it
reads high on exactly the fixes this is counting. The distance here is to the
whole line, unconstrained.

An excursion is a run of consecutive joined fixes more than `OFF_M` from the
line being followed. It ends when a fix comes back inside, when a new line is
adopted, or when the trace ends. One that *begins* on the first fixes after a
new line was adopted is not a departure at all: a replacement starts at the
junction `snap` chose, a median 99 m ahead (`NavigationModel.awaitingJoin`), so
the car is legitimately off it until it gets there. Those are counted apart as
join gaps, and only the rest — the car leaving a line it was on — are
departures.

**The traces are private.** They record where someone drove, to the second
(`.gitignore`, "Drive traces"). This prints counts, distances and durations
only — never a coordinate, a street, a town or a timestamp — and nothing it
prints may be committed alongside anything that would let a reader place it.
"""

import json
import sys
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from common import CRS_METERS  # noqa: E402

# The same 60 m `NavigationModel.offRouteMeters` reroutes at.
OFF_M = 60.0
# Corridor half-widths to report the containment of, metres.
WIDTHS = [60, 100, 150, 250, 500, 1000, 2000]
# A fix gap longer than this is reported as a hole in the stream, the
# 10 s `NavigationModel.fixSilenceSeconds` uses.
GAP_S = 10.0

_TO_M = Transformer.from_crs(4326, CRS_METERS, always_xy=True)


def _line(coords):
    xy = np.array(coords, float)
    x, y = _TO_M.transform(xy[:, 0], xy[:, 1])
    return shapely.LineString(np.column_stack([x, y]))


def read(path):
    """Fixes (projected), and the route lines by seq."""
    lines, fixes = {}, []
    with open(path) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue          # a torn last line on a killed app
            kind = rec.get("t")
            if kind == "route" and rec.get("coords"):
                lines[rec["seq"]] = (rec.get("reason", ""), _line(rec["coords"]))
            elif kind == "fix":
                fixes.append(rec)
    return lines, fixes


def analyse(path):
    lines, fixes = read(path)
    if not fixes or not lines:
        return None
    first = min(lines)
    lon = np.array([f["lon"] for f in fixes])
    lat = np.array([f["lat"] for f in fixes])
    x, y = _TO_M.transform(lon, lat)
    pts = shapely.points(np.column_stack([x, y]))
    ts = np.array([f["ts"] for f in fixes], float)
    seq = np.array([f.get("route", first) for f in fixes])
    joined = np.array([bool(f.get("joined")) for f in fixes])
    acc = np.array([f.get("acc", 0.0) for f in fixes], float)

    d_follow = np.full(len(fixes), np.nan)
    for s in np.unique(seq):
        if s in lines:
            m = seq == s
            d_follow[m] = shapely.distance(pts[m], lines[s][1])
    d_orig = shapely.distance(pts, lines[first][1])

    step = np.r_[0.0, np.hypot(np.diff(x), np.diff(y))]
    dt = np.r_[0.0, np.diff(ts)]
    # Driven distance only while joined, and not across a hole in the stream
    # (a hole's straight line is not road).
    drive_m = np.where(joined & (dt <= GAP_S) & (dt > 0), step, 0.0)

    excursions = []
    i, n = 0, len(fixes)
    while i < n:
        if not (joined[i] and d_follow[i] > OFF_M):
            i += 1
            continue
        j, s0 = i, seq[i]
        # Did the car get onto this line before leaving it? If no fix of this
        # seq so far was within OFF_M, this run is the gap before joining it.
        same = np.where(seq[:i] == s0)[0]
        departed = bool(len(same)) and bool((d_follow[same] <= OFF_M).any())
        while j + 1 < n and joined[j + 1] and seq[j + 1] == s0 and d_follow[j + 1] > OFF_M:
            j += 1
        if j + 1 >= n:
            end = "trace ended"
        elif seq[j + 1] != s0:
            end = "new line adopted"
        else:
            end = "came back to the line"
        excursions.append({
            "fixes": j - i + 1,
            "seconds": float(ts[j] - ts[i]),
            "metres": float(drive_m[i + 1:j + 1].sum()),
            "max_from_followed": float(np.nanmax(d_follow[i:j + 1])),
            "max_from_original": float(d_orig[i:j + 1].max()),
            "end": end,
            "kind": "departure" if departed else "join gap",
        })
        i = j + 1

    gaps = dt[1:][dt[1:] > GAP_S]
    return {
        "km": float(drive_m.sum() / 1000),
        "fixes": n,
        "joined_fixes": int(joined.sum()),
        "routes": len(lines),
        "excursions": excursions,
        "d_follow": d_follow[joined],
        "d_orig": d_orig[joined],
        "drive_m": drive_m[joined],
        "gaps": gaps,
        "acc": acc,
    }


def main(paths):
    results = [r for r in (analyse(p) for p in paths) if r]
    km = sum(r["km"] for r in results)
    allexc = [e for r in results for e in r["excursions"]]
    print(f"drives: {len(results)}   joined km: {km:.1f}   "
          f"fixes: {sum(r['fixes'] for r in results)}   "
          f"route records: {sum(r['routes'] for r in results)}")
    for kind in ("departure", "join gap"):
        exc = [e for e in allexc if e["kind"] == kind]
        print(f"{kind}s past {OFF_M:.0f} m: {len(exc)}  "
              f"= {100 * len(exc) / km:.2f} per 100 km")
        report(exc)


def report(exc):
    if exc:
        def q(key, p):
            return float(np.percentile([e[key] for e in exc], p))
        for key in ("max_from_followed", "max_from_original", "seconds", "metres"):
            print(f"  {key:>18}: p50 {q(key, 50):7.0f}  p90 {q(key, 90):7.0f}  "
                  f"max {max(e[key] for e in exc):7.0f}")
        ends = {}
        for e in exc:
            ends[e["end"]] = ends.get(e["end"], 0) + 1
        print("  ended:", ", ".join(f"{k} {v}" for k, v in sorted(ends.items())))
        print("  excursions, sorted by how far they went from the line followed (m):")
        print("   ", sorted(round(e["max_from_followed"]) for e in exc))
        print("  ... and from the original line (m):")
        print("   ", sorted(round(e["max_from_original"]) for e in exc))



def coverage(results):
    dm = np.concatenate([r["drive_m"] for r in results])
    for label, key in (("followed", "d_follow"), ("original", "d_orig")):
        d = np.concatenate([r[key] for r in results])
        ok = np.isfinite(d)
        print(f"share of joined km within W of the {label} line:")
        print("   " + "  ".join(
            f"{w} m {100 * dm[ok & (d <= w)].sum() / dm[ok].sum():5.1f}%" for w in WIDTHS))

    gaps = np.concatenate([r["gaps"] for r in results])
    print(f"fix holes longer than {GAP_S:.0f} s: {len(gaps)}"
          + (f", p50 {np.median(gaps):.0f} s, max {gaps.max():.0f} s" if len(gaps) else ""))
    acc = np.concatenate([r["acc"] for r in results])
    acc = acc[acc > 0]
    print(f"stated accuracy p50 {np.median(acc):.1f} m  p99 {np.percentile(acc, 99):.1f} m  "
          f"max {acc.max():.1f} m")


def course_agreement(paths):
    """How often a moving car's reported course points against the line it is on.

    The input a wrong-way detector reads. For every joined fix within 15 m of
    the line being followed, moving at 3 m/s or more with a course reported,
    the angle between that course and the line's direction at the nearest
    point. A fix reading 120 degrees or more is one false vote for "wrong way";
    the detector's persistence rule is sized against how often those come, and
    how many arrive in a row.
    """
    angles, runs_, run = [], [], 0
    for p in paths:
        lines, fixes = read(p)
        for f in fixes:
            seq = f.get("route")
            if seq not in lines or not f.get("joined"):
                continue
            spd, crs = f.get("spd", -1), f.get("crs", -1)
            if spd is None or crs is None or spd < 3 or crs < 0:
                run = 0
                continue
            x, y = _TO_M.transform(f["lon"], f["lat"])
            line = lines[seq][1]
            pt = shapely.Point(x, y)
            if line.distance(pt) > 15:
                run = 0
                continue
            d = line.project(pt)
            a = line.interpolate(max(0, d - 10)); b = line.interpolate(min(line.length, d + 10))
            bearing = np.degrees(np.arctan2(b.x - a.x, b.y - a.y)) % 360
            # Grid bearing, near enough: CRS_METERS convergence is under 1.5 degrees.
            diff = abs((crs - bearing + 180) % 360 - 180)
            angles.append(diff)
            if diff >= 120:
                run += 1
            else:
                if run:
                    runs_.append(run)
                run = 0
    a = np.array(angles)
    print(f"moving on-line fixes with a course: {len(a)}")
    print(f"  angle to the line: p50 {np.median(a):.1f}  p99 {np.percentile(a, 99):.1f}  "
          f"max {a.max():.1f} degrees")
    print(f"  at 120 degrees or more: {(a >= 120).sum()} fixes "
          f"({100 * (a >= 120).mean():.3f}%); longest run {max(runs_) if runs_ else 0}")
    print(f"  at 60 degrees or more: {(a >= 60).sum()} fixes ({100 * (a >= 60).mean():.3f}%)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
    coverage([r for r in (analyse(p) for p in sys.argv[1:]) if r])
    course_agreement(sys.argv[1:])
