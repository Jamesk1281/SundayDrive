"""Prove the snap cap changes no snap within reach (docs/snap-cap.md).

The old snapping code, read verbatim from git at the commit before the cap,
is bound onto the same loaded router as the new code, so both answer from
one graph in one process. Every sampled point is snapped both ways:

  - the nearest road (`LineIndex.nearest` on the edge index) and the nearest
    service way (the access index), old unbounded against new at SNAP_MAX_M;
  - `snap` at rest, `snap_lead` at rest, moving with a heading and moving
    without one (a declined U-turn), and `snap_destination`.

Within reach every answer must be identical: the same line, so the same tie
rule, and the same node, offset, gap and lead-in. The service-way search is
bounded on its own, so it must give the same way where the old one was
within SNAP_MAX_M, and None where it was not.

Beyond reach the new code must refuse (OutOfReach, or None from `nearest`),
and that is checked without the old code: no line of `query(point.buffer
(SNAP_MAX_M))` lies within SNAP_MAX_M. Running the old code there is the
stall itself, minutes a point on the national graph, so it runs only with
--old-beyond (fine on New England), where the old offsets must be beyond
SNAP_MAX_M too, so the server answered OUTSIDE_COVERAGE either way.

    SUNDAYDRIVE_DATA=data/processed-ne python tools/snap_cap/parity.py --n 4000
    SUNDAYDRIVE_PACK=data/pack-us SUNDAYDRIVE_DATA=data/processed-us \\
        python tools/snap_cap/parity.py --n 4000

Points, per kind, --n each: on the road (a few metres off a random edge),
mid-block (30-300 m off one), far (1-4.9 km from the nearest road, drawn by
rejection), in car parks (on and beside random service ways), and random
over the graph's bounding box; and --n/4 at the limit (4.9-5.1 km). Prints counts per kind and the work
(lines measured) each version did; --out writes them as JSON.
"""

import argparse
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import types
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import shapely

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
import router as new  # noqa: E402

BASE = "936dfcf"   # usa before the cap
SEED = 20261023
SNAPPERS = ("snap", "snap_start", "snap_lead", "_snap", "snap_destination",
            "access_point")


def load_old(scratch: Path):
    """router.py at BASE, as a module of its own."""
    src = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE}:pipeline/router.py"],
                         check=True, capture_output=True, text=True).stdout
    path = scratch / "router_before_snap_cap.py"
    path.write_text(src)
    spec = importlib.util.spec_from_file_location("router_before_snap_cap", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Counter:
    """Lines measured by `nearest`, counted at `_candidates`, which both
    versions call once per square and measure everything it returns."""

    def __init__(self, *trees):
        self.n = 0
        for tree in trees:
            if tree is None:
                continue
            inner = tree._candidates

            def counted(*box, _inner=inner):
                found = _inner(*box)
                self.n += len(found)
                return found
            tree._candidates = counted


@contextmanager
def old_code(r, old):
    """The router answering with BASE's snapping code."""
    for name in SNAPPERS:
        setattr(r, name, types.MethodType(getattr(old.Router, name), r))
    trees = [t for t in (r._edge_tree, r._access_tree) if t is not None]
    for t in trees:
        t.nearest = types.MethodType(old.LineIndex.nearest, t)
    try:
        yield
    finally:
        for name in SNAPPERS:
            delattr(r, name)
        for t in trees:
            del t.nearest


def lead_key(lead):
    if lead is None:
        return None
    return (tuple((p.edge, p.coords.tobytes(), p.length_m, p.minutes, p.node)
                  for p in lead.parts), tuple(lead.through_closed))


def answers(r, lat, lon, heading, limit):
    """Every snap of one point, as comparable values; "OUT" for OutOfReach."""
    x, y = new._TO_M.transform(lon, lat)
    point = shapely.Point(x, y)
    out = {}

    def call(name, f):
        try:
            out[name] = f()
        except new.OutOfReach:
            out[name] = "OUT"

    kw = {} if limit is None else {"limit": limit}
    call("edge", lambda: r._edge_tree.nearest(point, **kw))
    if r._access_tree is not None:
        call("access", lambda: r._access_tree.nearest(point, **kw))
    call("snap", lambda: r.snap(lat, lon, **kw))
    for tag, h, moving in (("rest", None, False), ("heading", heading, True),
                           ("declined", None, True)):
        def lead(h=h, moving=moving):
            node, off, gap, ld = r.snap_lead(lat, lon, h, moving, **kw)
            return (node, off, gap, lead_key(ld))
        call(f"lead_{tag}", lead)
    call("destination", lambda: r.snap_destination(lat, lon, **kw))
    return out


def sample(r, n, rng, max_tries):
    """(kind, lat, lon, heading) points, in CRS_METERS then back to lon/lat."""
    pts = []
    n_edges = len(r._edge_geom_m)

    def along(geoms, rows, off_lo, off_hi, kind):
        for row in rows:
            line = geoms[int(row)]
            p = line.interpolate(rng.random(), normalized=True)
            ang = rng.random() * 2 * math.pi
            d = rng.uniform(off_lo, off_hi)
            pts.append((kind, p.x + d * math.cos(ang), p.y + d * math.sin(ang)))

    along(r._edge_geom_m, rng.integers(0, n_edges, n), 0.0, 8.0, "on_road")
    along(r._edge_geom_m, rng.integers(0, n_edges, n), 30.0, 300.0, "mid_block")
    # Far points by rejection: most points kilometres off one road are near
    # another, so offsets are drawn until each band has its share, sorted by
    # the bounded search's own distance (the comparison is made afterwards).
    want = {"far": n, "at_limit": n // 4}
    lo_hi = {"far": (1000.0, 4900.0), "at_limit": (4900.0, 5100.0)}
    tries = 0
    while any(want.values()) and tries < max_tries:
        tries += 1
        line = r._edge_geom_m[int(rng.integers(0, n_edges))]
        p = line.interpolate(rng.random(), normalized=True)
        ang, d = rng.random() * 2 * math.pi, rng.uniform(1000.0, 8000.0)
        q = shapely.Point(p.x + d * math.cos(ang), p.y + d * math.sin(ang))
        e = r._edge_tree.nearest(q, 5200.0)
        dist = math.inf if e is None else r._edge_geom_m[int(e)].distance(q)
        for kind, (lo, hi) in lo_hi.items():
            if want[kind] and lo <= dist <= hi:
                want[kind] -= 1
                pts.append((kind, q.x, q.y))
    if r._access_tree is not None:
        rows = rng.integers(0, len(r._access_geom_m), n)
        along(r._access_geom_m, rows, 0.0, 25.0, "car_park")
    lat, lon = np.asarray(r.node_lat), np.asarray(r.node_lon)
    b = (float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max()))
    for _ in range(n):
        bx, by = new._TO_M.transform(rng.uniform(b[0], b[2]), rng.uniform(b[1], b[3]))
        pts.append(("bbox", bx, by))
    out = []
    for kind, x, y in pts:
        lo, la = new._FROM_M.transform(x, y)
        out.append((kind, float(la), float(lo), float(rng.uniform(0.0, 360.0))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--out")
    ap.add_argument("--scratch", default=os.environ.get("TMPDIR", "/tmp"))
    ap.add_argument("--max-tries", type=int,
                    help="offsets drawn for the far bands (default 400 per --n)")
    ap.add_argument("--old-beyond", action="store_true",
                    help="also run the old code on points it refuses")
    args = ap.parse_args()

    old = load_old(Path(args.scratch))
    data = os.environ.get("SUNDAYDRIVE_DATA", str(ROOT / "data" / "processed"))
    pack = os.environ.get("SUNDAYDRIVE_PACK") or None
    t0 = time.time()
    r = new.Router(data, pack=pack)
    print(f"loaded {pack or data} in {time.time() - t0:.0f} s, "
          f"{len(r._edge_geom_m):,} edges", flush=True)
    counter = Counter(r._edge_tree, r._access_tree)
    rng = np.random.default_rng(SEED)
    points = sample(r, args.n, rng, args.max_tries or 400 * args.n)
    limit = new.SNAP_MAX_M

    tally, bad = {}, []
    t0 = time.time()
    for i, (kind, lat, lon, heading) in enumerate(points):
        x, y = new._TO_M.transform(lon, lat)
        point = shapely.Point(x, y)
        counter.n = 0
        after = answers(r, lat, lon, heading, limit)
        work_new = counter.n
        reach = "out" if after["edge"] is None else "in"
        before, work_old = None, 0
        if reach == "in" or args.old_beyond:
            counter.n = 0
            with old_code(r, old):
                before = answers(r, lat, lon, heading, None)
            work_old = counter.n
        if before is not None:
            d = float(r._edge_geom_m[before["edge"]].distance(point))
        else:
            d = min((float(r._edge_geom_m[int(e)].distance(point)) for e in
                     r._edge_tree.query(point.buffer(limit))), default=math.inf)
        t = tally.setdefault(f"{kind} / {reach}",
                             dict(n=0, ok=0, work_old=0, work_new=0, old_run=0))
        t["n"] += 1
        t["work_old"] += work_old
        t["work_new"] += work_new
        t["old_run"] += before is not None
        if reach == "in":
            ok = d <= limit and all(before[k] == after[k] for k in after if k != "access")
            if "access" in after:
                a = before["access"]
                a_d = float(r._access_geom_m[a].distance(point))
                ok = ok and after["access"] == (a if a_d <= limit else None)
        else:
            # Refused, with nothing in reach, and (when the old code ran) the
            # old offsets beyond it, so the server refused it too.
            ok = (d > limit
                  and all(after[k] == "OUT" for k in after if k not in ("edge", "access"))
                  and (before is None or (before["snap"][1] > limit
                                          and before["destination"][1] > limit)))
        t["ok"] += ok
        if not ok and len(bad) < 20:
            differs = [k for k in after if before is not None
                       and k in before and before[k] != after[k]]
            bad.append(dict(kind=kind, lat=lat, lon=lon, heading=heading, d=d,
                            differs=differs, before=repr(before)[:400],
                            after=repr(after)[:400]))
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1:,}/{len(points):,} in {time.time() - t0:.0f} s", flush=True)

    total = sum(t["n"] for t in tally.values())
    good = sum(t["ok"] for t in tally.values())
    print(f"\n{'kind / reach':32} {'points':>7} {'same':>7} {'old ran':>8} "
          f"{'lines/pt old':>13} {'lines/pt new':>13}")
    for k in sorted(tally):
        t = tally[k]
        old_pt = t["work_old"] / t["old_run"] if t["old_run"] else float("nan")
        print(f"{k:32} {t['n']:7,} {t['ok']:7,} {t['old_run']:8,} {old_pt:13,.0f} "
              f"{t['work_new'] / t['n']:13,.0f}")
    print(f"\n{good:,} of {total:,} points identical (or refused where the old "
          f"code was beyond {limit:.0f} m)")
    for b in bad:
        print(json.dumps(b))
    if args.out:
        Path(args.out).write_text(json.dumps(dict(
            data=pack or data, base=BASE, seed=SEED, n=args.n, total=total,
            identical=good, tally=tally, bad=bad), indent=1))
    sys.exit(0 if good == total else 1)


if __name__ == "__main__":
    main()
