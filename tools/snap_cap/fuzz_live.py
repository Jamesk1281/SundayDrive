"""Fuzz a running server with hostile points and time each answer
(docs/snap-cap.md).

Every point goes everywhere a request takes one: `/api/route` from, to, via
and a reroute's from (with a heading), `/api/loop` and `/api/loop/limit`.
Then four requests from 400 km offshore at once, beside an ordinary Denver
to Estes Park route, which must answer in about its normal time.

    python tools/snap_cap/fuzz_live.py --base http://127.0.0.1:55611
    python tools/snap_cap/fuzz_live.py --base ... --only "10 km off New Jersey" \\
        --skip-concurrent        # the old-code baseline: never the 400 km points

Standard library only, so it runs against any checkout's server. Writes
every answer as JSON with --out.
"""

import argparse
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

DENVER, ESTES_PARK = "39.7392,-104.9903", "40.3772,-105.5217"
OFFSHORE_400 = "36.46994,-70.93004"     # the outside review's point

# (name, "lat,lon", the code expected). Water and desert points lie inside
# or beside the contiguous US's bounding box, where a box check passes them.
POINTS = [
    ("10 km off New Jersey", "39.75,-73.93", "OUTSIDE_COVERAGE"),
    # Past the old code's 16 km square, so it widened to 64 km; still cheap
    # there with the pack in memory (docs/snap-cap.md, "Timings").
    ("30 km off New Jersey", "39.75,-73.65", "OUTSIDE_COVERAGE"),
    # Far enough that the old code widened past 64 km: the stall, smaller.
    ("100 km off New Jersey", "39.4,-73.2", "OUTSIDE_COVERAGE"),
    ("400 km off the Atlantic coast", OFFSHORE_400, "OUTSIDE_COVERAGE"),
    ("10 km into the Gulf, off Florida", "30.08,-85.85", "OUTSIDE_COVERAGE"),
    ("400 km into the Gulf", "25.5,-90.0", "OUTSIDE_COVERAGE"),
    ("10 km off Oregon", "44.6,-124.2", "OUTSIDE_COVERAGE"),
    ("400 km into the Pacific", "37.0,-127.5", "OUTSIDE_COVERAGE"),
    ("mid Lake Michigan", "43.6,-87.1", "OUTSIDE_COVERAGE"),
    ("Great Salt Lake", "41.1,-112.6", "OUTSIDE_COVERAGE"),
    ("Nevada desert, Black Rock playa", "40.85,-119.10", "OUTSIDE_COVERAGE"),
    ("Hudson Bay", "60.0,-86.0", "OUTSIDE_COVERAGE"),
    ("central Mexico", "23.0,-102.0", "OUTSIDE_COVERAGE"),
    ("null island", "0,0", "OUTSIDE_COVERAGE"),
    ("the north pole", "90,0", "OUTSIDE_COVERAGE"),
    ("the south pole", "-90,0", "OUTSIDE_COVERAGE"),
    ("near the north pole", "89.9,-100", "OUTSIDE_COVERAGE"),
    ("the antimeridian", "0,180", "OUTSIDE_COVERAGE"),
    ("the antimeridian, west", "45,-180", "OUTSIDE_COVERAGE"),
    ("latitude 91", "91,0", "BAD_INPUT"),
    ("longitude -181", "0,-181", "BAD_INPUT"),
    ("nan", "nan,nan", "BAD_INPUT"),
    ("inf", "inf,-100", "BAD_INPUT"),
]


def placements(ll):
    return [
        ("route from", "/api/route", {"from": ll, "to": DENVER}),
        ("route to", "/api/route", {"from": DENVER, "to": ll}),
        ("route via", "/api/route", {"from": DENVER, "to": ESTES_PARK, "via": ll}),
        ("reroute from", "/api/route", {"from": ll, "to": DENVER, "heading": "90"}),
        ("loop", "/api/loop", {"from": ll, "km": "40"}),
        ("loop limit", "/api/loop/limit", {"from": ll}),
    ]


def post(base, path, body, timeout=900.0):
    data = urllib.parse.urlencode(body).encode()
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(base + path, data=data, timeout=timeout) as r:
            status, text = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read()
    seconds = time.perf_counter() - t0
    try:
        code = json.loads(text).get("code")
    except ValueError:
        code = None
    return status, code, seconds


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--only", action="append", help="point names to send")
    ap.add_argument("--places", help="comma-separated placements to use")
    ap.add_argument("--skip-concurrent", action="store_true")
    ap.add_argument("--timeout", type=float, default=900.0,
                    help="seconds a request may take before it counts as failed")
    ap.add_argument("--out")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    out = dict(base=base, points=[], concurrent=None)

    t, code, s = post(base, "/api/route", {"from": DENVER, "to": ESTES_PARK})
    print(f"Denver -> Estes Park alone: {t} in {s:.2f} s", flush=True)
    out["route_alone_s"] = s
    want = set(args.places.split(",")) if args.places else None
    worst = 0.0
    for name, ll, expect in POINTS:
        if args.only and name not in args.only:
            continue
        for place, path, body in placements(ll):
            if want and place not in want:
                continue
            try:
                status, got, s = post(base, path, body, args.timeout)
            except OSError:              # timed out: the stall itself
                status, got, s = None, "TIMEOUT", args.timeout
            ok = got == expect
            worst = max(worst, s)
            out["points"].append(dict(name=name, ll=ll, place=place, status=status,
                                      code=got, expect=expect, ok=ok, seconds=s))
            print(f"{'ok ' if ok else 'BAD'} {s:7.3f} s  {status} {str(got):18}  "
                  f"{place:13} {name}", flush=True)
    print(f"slowest answer {worst:.3f} s; "
          f"{sum(p['ok'] for p in out['points'])} of {len(out['points'])} as expected")

    if not args.skip_concurrent:
        results = {}

        def offshore(i):
            results[i] = post(base, "/api/route",
                              {"from": OFFSHORE_400, "to": "36.48985,-70.08488"})
        threads = [threading.Thread(target=offshore, args=(i,)) for i in range(4)]
        for th in threads:
            th.start()
        time.sleep(0.05)
        status, code, s = post(base, "/api/route", {"from": DENVER, "to": ESTES_PARK})
        for th in threads:
            th.join()
        print(f"Denver -> Estes Park beside four offshore requests: {status} in "
              f"{s:.2f} s; offshore answers "
              f"{[(r[1], round(r[2], 3)) for r in results.values()]}")
        out["concurrent"] = dict(route_status=status, route_s=s,
                                 offshore=[dict(code=r[1], seconds=r[2])
                                           for r in results.values()])
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
