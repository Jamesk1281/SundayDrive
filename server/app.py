"""Sunday Drive routing API (backend for the iOS app).

Loads the routing graph once at startup and serves:
  GET  /api/route?from=LAT,LON&to=LAT,LON&pref=0.5[&heading=DEG][&via=LAT,LON]
                                            [&avoid_unpaved=0..2]
                 [&w_<type>=...][&options=1]
                 [&leave=LAT,LON,DEG][&rejoin=LAT,LON,DEG]
                              -> {"fastest": <GeoJSON Feature>,
                                  "scenic":  <GeoJSON Feature>,
                                  ["options": {"default": i, "menu": [...]}]}
  GET  /api/loop?from=LAT,LON&km=40[&pref=1.0][&sector=NE][&w_<type>=...]
                              -> {"loop": <GeoJSON Feature>, "meta": {...},
                                  "alternatives": [...], "note": null|str}
  GET  /api/health

`pref` (0..1) is the overall scenery strength. Each beauty type can also be
weighted with w_<type> (e.g. w_coast=2&w_town=3&w_farm=0); each defaults to 1.0
(neutral) and is clamped to a sane range. The tunable types are listed by
BEAUTY_TYPES in router.py.

`via` pins a route through a waypoint. It exists for one caller: a driver who
has gone off a *loop* and needs to rejoin it. A loop ends where it began, so
asking for a route to its destination hands back the short way home and deletes
the rest of the drive — the waypoint is the loop's far point, and pinning through
it is what makes the replacement a continuation rather than an abandonment.

`/api/loop` takes one endpoint and a length instead of two endpoints, and
returns a closed scenic drive of about that length. `sector` (a compass octant)
is what the app's compass sets; the populated ones come back in
`alternatives`, and asking is the point — a coastal start has fewer than eight.
The loop-specific numbers live in `meta` rather than in the Feature's
properties, so the same client type decodes a loop and a route. A loop that
has to be built while another build is running is refused with a 503 and a
JSON `error`, rather than queued (docs/loop-lock-contention.md); one already
built for the same request is always served. Nothing on `/api/route` is ever
refused this way.

`heading` (0..360, 0=N, clockwise) is the driver's course over ground, and
applies to `from` only — a destination has no travel direction. With it, the
start snaps to the end of its road that lies ahead rather than the nearer one,
so a mid-drive reroute doesn't open by turning the driver around. Send it only
while moving; omit it when planning from a parked car.

`options=1` asks for the menu of in-between scenic routes the app turns into
slider detents (pipeline/options.py, docs/route-options.md). It is honoured
only when the server runs with SUNDAYDRIVE_ROUTE_OPTIONS=1, and only when no
other plan or loop is computing; otherwise the reply is today's, with no
`options`. With options, `scenic` is the menu's default option in full detail.
`leave` and `rejoin` are an option's switch points: the scenic stretch between
them at pref 1, fastest roads either side. They are how the app fetches an
option in full and how it reroutes one mid-drive.

Every route and loop avoids the roads OpenStreetMap marks closed for the season
on the day of the request, in New England's time zone (pipeline/closures.py).
When the only way to a destination is one of them, /api/route says so: a 404
whose error is CLOSED_FOR_SEASON.

Run:  python server/app.py [processed_dir]   (default: data/processed)
"""

import os
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

from flask import Flask, jsonify, request
from flask_compress import Compress
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from looper import (BEAUTIFUL_SCORE, MAX_TARGET_KM, MIN_TARGET_KM, SECTORS,
                    LoopPlanner)  # noqa: E402
from router import (BEAUTY_TYPES, MAX_AVOID_UNPAVED, Router,  # noqa: E402
                    region_today)
import options as route_options  # noqa: E402

# How far a user may push a single beauty type. 0 ignores it; the upper bound
# keeps one cranked slider from completely swamping the others.
WEIGHT_MIN, WEIGHT_MAX = 0.0, 4.0

# Above this share of a loop spent re-driving a road already driven, the answer
# stops being a loop and the response says so instead of pretending. Normal is
# under 0.06; the cases that trip this are short loops from rural starts, where
# within a couple of km there is genuinely one road (a 8 km loop from Petersham
# comes back at 0.35). See looper.Loop.repeated_fraction.
LOOP_RETRACE_NOTE = 0.15

# What the built graph actually covers, named in one place because it appears in
# three error messages and in the index response. It must be changed with the
# parquets, not with the code: a server telling a driver in Vermont that the
# region is Massachusetts is wrong in the one direction that costs a bug report,
# and it was wrong that way from the moment the New England graph was copied
# over. Read from the environment so a rollback to a different region's parquets
# does not need a code change to stay honest.
#
# `VICTORYLAP_*` and `SCENIC_*` are the two pre-rename spellings, still read
# after the `SUNDAYDRIVE_*` ones for one release. They are set by hand on the
# deployed box and in every command written before the renames, and dropping
# them outright fails silently in the worst way available: the server would
# come up serving the default region and the default data directory, and
# answer every request as though that were correct. Delete both legacy names
# at the first release, not before.
REGION = (os.environ.get("SUNDAYDRIVE_REGION")
          or os.environ.get("VICTORYLAP_REGION")
          or os.environ.get("SCENIC_REGION", "New England"))

# The 404 for a trip that only a road closed for the season connects. Kept
# apart from "no route found", which reads as a wrong pin or a broken app: this
# place is real, and the road to it opens again in spring.
CLOSED_FOR_SEASON = "the only way there is closed for the season"

# Reject a request whose endpoint lies farther than this from any road — it's
# outside the covered region (see REGION), and the "nearest" road would be in an
# arbitrary border town, yielding a nonsense route.
SNAP_MAX_M = 5000.0

# Where the prebuilt graph lives. An env var (not a CLI arg) so it works
# identically whether run directly (python server/app.py) or via the waitress
# entrypoint (server/serve.py). Defaults to the repo's data/processed.
PROCESSED = (os.environ.get("SUNDAYDRIVE_DATA")
             or os.environ.get("VICTORYLAP_DATA")
             or os.environ.get("SCENIC_DATA", str(ROOT / "data" / "processed")))

# Route options (pipeline/options.py) are off unless this is set. They cost
# about twice today's plan on the box (docs/route-options.md, "Capacity"), so
# the owner turns them on after measuring there, and can turn them off again
# with a restart and no deploy.
ROUTE_OPTIONS = os.environ.get("SUNDAYDRIVE_ROUTE_OPTIONS", "") in ("1", "true")

app = Flask(__name__, static_folder=None)
CORS(app)
# Gzip responses. Route GeoJSON is large and very repetitive (coordinate
# digits), so it compresses ~5x — which directly eases the home-upload
# bottleneck when the server runs on a laptop behind a tunnel.
Compress(app)

print(f"loading graph from {PROCESSED} ...")
ROUTER = Router(PROCESSED)
# len(ROUTER.nodes), not ROUTER.n: the router overwrites `n` with the
# turn-restriction-expanded index count (~+1.2%), so reporting it here made
# /api/health disagree with graph_nodes.parquet after a code-only deploy on
# identical data — a false alarm in the one number a smoke check compares.
# Loops are served from the same graph. The planner is cheap to construct — it
# holds a reference and nothing else — but it caches two ~25 MB Dijkstra passes
# per (start, pref, weights) so that tapping another direction does not repeat them.
#
# One lock around every build, because waitress is threaded and those caches
# are plain dicts. Serialising is also the right answer on merit: a loop is
# ~0.7 s of CPU-bound numpy, so two at once would contend for the same cores and
# finish no sooner, and the second request is almost always the same user
# tapping the compass again.
LOOPER = LoopPlanner(ROUTER)
LOOP_LOCK = threading.Lock()

# The mid-drive loop rejoin (`via`) has a planner and a lock of its own, so a
# driver who missed a turn waits only for another driver's rejoin, never behind
# everyone's "Try another direction" (review finding K-1). The price is a second
# pair of cost models, 82 MB each on the New England graph, and a first rejoin
# per weight set that builds its own (~40 ms) instead of finding the loop
# build's. docs/loop-lock-contention.md.
REJOINER = LoopPlanner(ROUTER)
REJOIN_LOCK = threading.Lock()

# A loop build that finds another running may wait for it, but only one at a
# time and only this long; any other is refused with a 503 at once.
#
# The wait is for one person releasing the distance slider twice, whose second
# request should follow their first rather than be told the server is busy. A
# cold build took a median 3.1 s (p90 3.6 s) on the New England graph, so a
# shorter wait refused that second request every time it was tried.
# One waiter, not several, because each holds one of waitress's four threads:
# a build and a waiter leave two for drivers, however many people tap Loop.
# docs/loop-lock-contention.md, "The wait".
LOOP_BUSY_WAIT_S = 5.0
LOOP_WAIT_SLOT = threading.Lock()
LOOP_BUSY = "Busy planning other drives. Try again in a moment."

# Built loops, keyed by the whole request. The planner's caches make a *new* loop
# cost ~0.65 s; this makes an *identical* request cost nothing, which is the
# common interaction and not an edge case — trying another direction on the
# compass and then going back to the one you liked is how it gets used.
# The graph is loaded once for the life of the process, but the roads closed
# for the season change on fixed dates while it runs, so the key carries the
# closure version too. Without it a loop cached on Oct 14 would go on being
# served over Lincoln Gap after Oct 15.
#
# Under its own lock, not the build's: a cached loop is answered while another
# build runs, and is never refused as busy.
LOOP_RESULTS = {}
LOOP_RESULTS_MAX = 16
LOOP_RESULTS_LOCK = threading.Lock()

# How many /api/route and /api/loop requests are computing right now.
#
# The guard that keeps route options from ever making a driver wait. Routing
# holds the GIL, so requests run one at a time in effect, and a plan with
# options costs about twice one without. A burst is where that hurts: the app
# gives up at 20 s and a queue twice as slow to drain fills twice as fast
# (review finding K-1). So options are computed only by a request that found
# nothing else running, and they give up between phases the moment anything
# else arrives — the reply is then today's, without `options`, which every
# client handles. docs/route-options.md, "The busy guard".
IN_FLIGHT = 0
IN_FLIGHT_LOCK = threading.Lock()


@contextmanager
def _computing():
    """Count this request as computing; yields whether it is the only one."""
    global IN_FLIGHT
    with IN_FLIGHT_LOCK:
        IN_FLIGHT += 1
        alone = IN_FLIGHT == 1
    try:
        yield alone
    finally:
        with IN_FLIGHT_LOCK:
            IN_FLIGHT -= 1


def _not_alone():
    # A rejoin is counted through IN_FLIGHT, because it runs inside
    # `api_route`'s `_computing()`; the locks are belt and braces.
    return IN_FLIGHT > 1 or LOOP_LOCK.locked() or REJOIN_LOCK.locked()

print(f"ready: {len(ROUTER.nodes):,} nodes "
      f"({ROUTER.n:,} routing slots after turn-restriction splits)")


def _parse_ll(s: str):
    lat, lon = (float(x) for x in s.split(","))
    return lat, lon


def _today():
    """The day this request's seasonal closures are judged on.

    Called once per request and handed to every search the request makes, so a
    request that straddles midnight cannot price its two arms on different
    days. And the one place the tests replace the clock: on 2026-10-04 Lincoln
    Gap is open, so a test that read the real date would prove nothing.
    """
    return region_today()


def _parse_heading(args):
    """Read the driver's course over ground, or None if they didn't send a
    usable one.

    Anything outside 0..360 is dropped rather than rejected. CoreLocation
    reports -1 for "no opinion", and a client that forwards it verbatim is
    asking for the default behaviour, not making a bad request — failing the
    whole route over it would turn a missing heading into a failed reroute.

    Dropped, specifically, and never wrapped: `-1 % 360` is 359, so normalising
    a *negative* would turn "I don't know which way I'm facing" into a confident
    due-north, and point the reroute at the wrong end of the road.

    Exactly 360.0 is the one value folded rather than dropped, because it is not
    a client error — it is what rounding a legal course to one decimal produces.
    A driver headed due north reports 359.97, which any `%.1f` formatter sends as
    "360.0"; dropping that fell back to nearer-end snapping precisely when the
    heading was most worth having. Folding is safe here and not above because
    the sign check has already run.
    """
    raw = args.get("heading")
    if raw is None or raw == "":
        return None
    value = float(raw)          # a non-numeric heading is a real bad request
    if value < 0.0 or value > 360.0:
        return None
    # The same 0..360 window `Router.snap` accepts, so both layers agree on
    # what "usable" means rather than each having its own idea.
    return value % 360.0


def _parse_declined_uturn(args):
    """Whether the driver has just declined a route that turned them around.

    Sent by the app, on a reroute, when the route it is leaving opened by
    turning the driver back (`turns_around` on that route) and they kept going
    instead. The reply then goes on ahead if there is a reasonable way to:
    at most one U-turn per departure. Absent means today's behaviour, which is
    what every client built before this sends. docs/reroute-uturn.md.
    """
    return args.get("declined_uturn", "") in ("1", "true")


def _parse_avoid_unpaved(args):
    """How hard to steer around dirt roads, as a multiple of the calibrated
    default (`router.UNPAVED_AVOID_MIN_PER_KM`). 0 accepts them freely, 1.0 is
    the default, `MAX_AVOID_UNPAVED` is as hard as the old fixed penalty ever
    pushed.

    Separate from `w_<type>` on purpose. Those six compete for a fixed pot of
    scenery weight and are renormalised against each other, so an avoidance
    jammed in among them would quietly turn every attraction down. This one is
    priced in minutes and does not touch the beauty blend at all.
    """
    value = float(args.get("avoid_unpaved", 1.0))
    return max(0.0, min(MAX_AVOID_UNPAVED, value))


def _parse_weights(args):
    """Read the per-beauty-type weights (w_<type>) from the request. Each
    defaults to 1.0 (neutral) and is clamped to [WEIGHT_MIN, WEIGHT_MAX]."""
    weights = {}
    for name, *_ in BEAUTY_TYPES:
        value = float(args.get(f"w_{name}", 1.0))
        weights[name] = max(WEIGHT_MIN, min(WEIGHT_MAX, value))
    return weights


def _parse_switch(args, name):
    """One of an option's switch points, `lat,lon,heading`, or None.

    A point on the scenic road and the way along it the route drives, never
    a node id: ids change with every rebuild, and the request that fetches an
    option can land on the other box (docs/route-options.md, "Switch points").
    """
    raw = args.get(name)
    if not raw:
        return None
    lat, lon, heading = (float(x) for x in raw.split(","))
    if not 0.0 <= heading <= 360.0:
        raise ValueError(name)
    return lat, lon, heading % 360.0


def _no_worse_than_fastest(fastest, scenic):
    """The scenic route, or the fastest one when "scenic" came back scoring lower.

    The detour cost is `km * (1 - score/10)` (`Router._weights`) — proportional
    to *length* — so at any pref above 0 the router is also, quietly, a
    shortest-distance router, and a shorter route can carry less total penalty
    while being uglier per kilometre. Dijkstra then returns it, correctly by its
    own objective and wrongly by the driver's.

    Measured over 983 sampled trips at the shipped defaults, that happens on 6
    of them (0.6%; 9 with `town` off). One came back 4.8 km shorter, 0.3 minutes
    slower, and scoring 5.21 against the fastest route's 5.79 — and the app
    dutifully rendered it as "adds 1 min and raises scenery 5.8 -> 5.2".
    Handing back the fastest route instead is better on both numbers the app
    prints, costs nothing because it is already computed, and makes the screen
    say "Same as the fastest route at this setting", which is true.

    Deliberately *not* a fix to the cost function. Making the penalty
    proportional to minutes rather than km would remove the cause, and would
    also invalidate the BETA/PREF_CURVE calibration those two constants share —
    a sweep, not a bug fix. See docs/route-distribution-study.md.
    """
    return fastest if scenic.mean_score < fastest.mean_score else scenic


def _request_params():
    """The request's parameters: the form body on a POST, the query string on
    a GET.

    The app sends POST, so the driver's coordinates travel in the body and not
    in the URL, which is what a TLS-terminating proxy's access log records by
    default (docs/coordinates-out-of-the-url.md). GET stays accepted for
    builds already installed and for curl.

    Deliberately not `request.values`, which merges the two. That would make a
    POST whose parameters were left on the URL work perfectly, and the one
    client mistake this change exists to rule out could never show up here.
    """
    return request.form if request.method == "POST" else request.args


@app.route("/api/route", methods=["GET", "POST"])
def api_route():
    args = _request_params()
    try:
        a = _parse_ll(args["from"])
        b = _parse_ll(args["to"])
        pref = float(args.get("pref", 0.5))
        avoid_unpaved = _parse_avoid_unpaved(args)
        heading = _parse_heading(args)
        declined_uturn = _parse_declined_uturn(args)
        weights = _parse_weights(args)
        raw_via = args.get("via")
        via = _parse_ll(raw_via) if raw_via else None
        leave = _parse_switch(args, "leave")
        rejoin = _parse_switch(args, "rejoin")
        want_options = args.get("options", "") in ("1", "true")
    except (KeyError, ValueError):
        return jsonify(error="need from=lat,lon&to=lat,lon[&pref=0..1]"
                             "[&heading=0..360][&declined_uturn=1]"
                             "[&via=lat,lon][&w_<type>=...][&options=1]"
                             "[&leave=lat,lon,deg][&rejoin=lat,lon,deg]"), 400
    with _computing() as alone:
        return _route(a, b, pref, avoid_unpaved, heading, declined_uturn,
                      weights, via, leave, rejoin,
                      want_options and ROUTE_OPTIONS and alone)


def _route(a, b, pref, avoid_unpaved, heading, declined_uturn, weights, via,
           leave, rejoin, with_options):
    day = _today()

    # Heading applies to the start only: it says which way the driver is
    # travelling, and a destination isn't travelling anywhere.
    s, s_off = ROUTER.snap(*a, heading=heading)
    # The destination goes through the access layer: a pin on a building inside
    # a car park has to become the road you can get in from, not the nearest
    # road as the crow flies, which is routinely the wrong side of the building.
    t, t_off = ROUTER.snap_destination(*b)
    if max(s_off, t_off) > SNAP_MAX_M:
        return jsonify(error="point is outside the covered road network "
                             f"(currently {REGION})"), 400
    if s == t:
        return jsonify(error="those points are too close together — "
                             "they sit on the same stretch of road"), 400

    # Both routes are scored with the user's beauty weights so the two numbers
    # the app puts side by side ("scenery 4.1 -> 6.3") are on one scale. The
    # weights do not change the *fastest* route itself: pref 0 zeroes the
    # scenery term, so its path is time-only either way.
    # At pref 0 the scenic route collapses to the fastest one, so reuse that
    # result instead of running Dijkstra twice — this halves the latency of
    # mid-drive "switch to fastest" reroutes.
    # `heading` reaches the route as well as the snap. It picks which end of the
    # road to start from (above) and, in RouteResult._describe_start, whether
    # the opening instruction is a compass heading or a turn — a route that has
    # to begin by sending a moving car back the way it came must say so.
    pref = max(0.0, min(1.0, pref))
    if via is not None:
        # A waypoint is a point on a road, so it snaps like a start and not like
        # a destination — there is no building to find the car park entrance for.
        w, w_off = ROUTER.snap(*via)
        if w_off > SNAP_MAX_M:
            return jsonify(error="that waypoint is outside the covered road "
                                 f"network (currently {REGION})"), 400
        # The rejoin's own planner and lock, never the loop builds': a driver
        # is not queued behind anyone's "Try another direction", and is never
        # refused as busy (docs/loop-lock-contention.md). Still inside
        # `api_route`'s `_computing()`, which is how the route options' busy
        # guard sees a driver and gives way.
        with REJOIN_LOCK:
            fastest = REJOINER.resume(s, w, t, 0.0, weights, avoid_unpaved,
                                      on=day)
            scenic = (fastest if pref == 0.0
                      else REJOINER.resume(s, w, t, pref, weights,
                                           avoid_unpaved, on=day))
            # Asked again with nothing closed only when it failed, so the
            # common case pays nothing for the better message.
            closed = ((fastest is None or scenic is None)
                      and REJOINER.resume(s, w, t, 0.0, weights,
                                          avoid_unpaved) is not None)
        # `heading` is deliberately dropped here. It picks which end of the
        # driver's road to leave from, and this caller is mid-drive, so it
        # matters — but honouring it would mean starting the search from a
        # different node than the one `snap` returned above, which `resume` has
        # no way to express. A rejoin that opens by turning the car around is
        # worth fixing; see docs/loop-routes-design.md.
        #
        # `declined_uturn` is ignored here for the same reason, and accepted
        # rather than refused so a client that sends it on every reroute still
        # gets its rejoin. Without a heading there is no "behind" to keep the
        # route out of, and the app never sends it on this path anyway: these
        # routes carry no `turns_around`, so nothing here can be declined.
        # docs/reroute-uturn.md.
        if closed:
            return jsonify(error=CLOSED_FOR_SEASON), 404
        if fastest is None or scenic is None:
            return jsonify(error="no route found through that waypoint"), 404
        scenic = _no_worse_than_fastest(fastest, scenic)
        return jsonify(fastest=fastest.geojson(), scenic=scenic.geojson())

    # The menu of in-between routes, for a plan. Never for a reroute, which
    # carries a heading or a declined U-turn or switch points, and never when
    # anything else is computing: `plan` returns None the moment another
    # request arrives, and the reply below is today's.
    if (with_options and heading is None and not declined_uturn
            and leave is None and rejoin is None):
        plan = route_options.plan(ROUTER, s, t, weights, avoid_unpaved,
                                  on=day, abort=_not_alone)
        if plan is not None:
            return jsonify(fastest=plan.fastest.geojson(),
                           scenic=route_options.feature(plan.scenic),
                           options=plan.options_json())

    # One option of a menu, in full: fetched when the driver settles on it,
    # and asked again by legs when they leave it mid-drive.
    if leave is not None or rejoin is not None:
        fastest = ROUTER.route(s, t, 0.0, weights, heading=heading,
                               avoid_unpaved=avoid_unpaved, on=day, origin=a,
                               keep_ahead=declined_uturn)
        try:
            scenic = route_options.spliced_route(
                ROUTER, s, t, leave, rejoin, weights, avoid_unpaved, on=day,
                heading=heading, origin=a, keep_ahead=declined_uturn)
        except route_options.SwitchPointNotFound:
            # A graph rebuilt under a plan. The stretch's road has gone, so
            # the nearest thing to the driver's choice is the scenic route;
            # an error here would leave a driver mid-drive with nothing.
            scenic = ROUTER.route(s, t, pref, weights, heading=heading,
                                  avoid_unpaved=avoid_unpaved, on=day,
                                  origin=a, keep_ahead=declined_uturn)
        if fastest is not None and scenic is not None:
            scenic = _no_worse_than_fastest(fastest, scenic)
            return jsonify(fastest=fastest.geojson(),
                           scenic=route_options.feature(scenic))
        if ROUTER.route(s, t, 0.0, weights, avoid_unpaved=avoid_unpaved) is not None:
            return jsonify(error=CLOSED_FOR_SEASON), 404
        return jsonify(error="no route found between those points"), 404

    # `origin` lets each route say whether it turns the driver around, and
    # `keep_ahead` asks for one that doesn't once they have declined one.
    # Both arms, so a driver who declined a U-turn and then tapped "fastest"
    # is not handed the same U-turn on the fast roads. docs/reroute-uturn.md.
    fastest = ROUTER.route(s, t, 0.0, weights, heading=heading,
                           avoid_unpaved=avoid_unpaved, on=day, origin=a,
                           keep_ahead=declined_uturn)
    scenic = (fastest if pref == 0.0
              else ROUTER.route(s, t, pref, weights, heading=heading,
                                avoid_unpaved=avoid_unpaved, on=day, origin=a,
                                keep_ahead=declined_uturn))
    if fastest is None or scenic is None:
        # A route on the graph with nothing closed means the closures are what
        # cut it off: the destination is up a road shut for the season, or
        # the driver is already on one.
        if ROUTER.route(s, t, 0.0, weights, avoid_unpaved=avoid_unpaved) is not None:
            return jsonify(error=CLOSED_FOR_SEASON), 404
        return jsonify(error="no route found between those points"), 404
    scenic = _no_worse_than_fastest(fastest, scenic)
    return jsonify(fastest=fastest.geojson(), scenic=scenic.geojson())


@app.route("/api/loop", methods=["GET", "POST"])
def api_loop():
    """A closed scenic drive of about `km` from one point, and the directions
    that hold another one.

    There is no destination to take, which is the whole feature: choosing where
    to go is the term that decides whether a drive is good, and here the server
    owns it. See docs/loop-routes-design.md.
    """
    args = _request_params()
    try:
        start_ll = _parse_ll(args["from"])
        target_km = float(args.get("km", 40.0))
        # Loops default to full scenery where routes default to 0.5. With the
        # length already pinned by the slider, pref has little left to trade,
        # and the middle of its travel is not monotone for loops — see the
        # docstring in pipeline/looper.py. Clients should leave this alone.
        pref = max(0.0, min(1.0, float(args.get("pref", 1.0))))
        weights = _parse_weights(args)
        avoid_unpaved = _parse_avoid_unpaved(args)
    except (KeyError, ValueError):
        return jsonify(error=f"need from=lat,lon[&km={MIN_TARGET_KM:.0f}.."
                             f"{MAX_TARGET_KM:.0f}][&pref=0..1]"
                             f"[&sector={'|'.join(SECTORS)}][&w_<type>=...]"), 400

    sector = args.get("sector") or None
    if sector is not None and sector not in SECTORS:
        return jsonify(error=f"sector must be one of {', '.join(SECTORS)}"), 400
    day = _today()

    # A loop is planned from a standstill by definition — the driver is choosing
    # a drive, not already on one — so no heading, and `snap` takes the nearer
    # end of the road they are on. No `snap_destination` either: there is no
    # destination pin to pull out of a car park.
    start, offset = ROUTER.snap(*start_ll)
    if offset > SNAP_MAX_M:
        return jsonify(error="point is outside the covered road network "
                             f"(currently {REGION})"), 400

    with _computing():
        return _loop(start, target_km, pref, weights, sector, avoid_unpaved, day)


def _loop(start, target_km, pref, weights, sector, avoid_unpaved, day):
    target_km = max(MIN_TARGET_KM, min(MAX_TARGET_KM, target_km))
    key = (start, round(target_km, 1), round(pref, 4), sector,
           tuple(sorted(weights.items())), round(avoid_unpaved, 4),
           ROUTER.closure_version(day))
    cached = _cached_loop(key)
    if cached is not None:
        return jsonify(cached)
    # Refused rather than queued: a build waiting on the lock holds a waitress
    # thread, and four of them starved every driver's reroute (K-1). Loop
    # builds only — nothing a driver sends mid-drive comes through here.
    if not _acquire_loop_lock():
        return jsonify(error=LOOP_BUSY), 503
    try:
        # The build just waited for may have been this same request, sent
        # twice.
        cached = _cached_loop(key)
        if cached is not None:
            return jsonify(cached)
        loop = LOOPER.plan(start, target_km, pref, weights, sector=sector,
                           avoid_unpaved=avoid_unpaved, on=day)
        if loop is None:
            # Only reachable when the geography has nothing at all in that
            # direction at that length, since `plan` returns the best available
            # rather than holding out for a good one.
            nearest = LOOPER.nearest_length(start, target_km, pref, weights,
                                            avoid_unpaved, on=day)
            hint = (f" The nearest loop from here is about {nearest:.0f} km."
                    if nearest else "")
            return jsonify(error="no loop of that length from there." + hint), 404
        available = LOOPER.sectors(start, loop.target_km, pref, weights,
                                   avoid_unpaved, on=day)
    finally:
        LOOP_LOCK.release()

    note = None
    if loop.repeated_fraction > LOOP_RETRACE_NOTE:
        share = round(100 * loop.repeated_fraction)
        note = (f"The roads here don't really make a loop this short — "
                f"{share}% of this one doubles back. Try a longer distance.")

    body = dict(
        loop=loop.route.geojson(),
        meta={
            "target_km": round(float(loop.target_km), 1),
            "km": round(float(loop.km), 1),
            "minutes": round(float(loop.minutes), 1),
            "mean_score": round(float(loop.mean_score), 2),
            # The legible number: "16 of your 40 km". Measured to separate a
            # scenic loop from a fast one of the same length 5-fold, where the
            # means only manage 5.8 against 5.0.
            "beautiful_km": round(float(loop.beautiful_km), 1),
            "beautiful_score": BEAUTIFUL_SCORE,
            # The loop-specific defect, always reported. It is what tells a
            # driver their 40 km drive is really a 20 km drive twice.
            "repeated_km": round(float(loop.repeated_km), 1),
            "turnaround": [round(loop.turnaround[0], 6),
                           round(loop.turnaround[1], 6)],
            "sector": loop.sector,
        },
        # Which way else the user could be sent, so the app can offer real
        # directions instead of a blind shuffle. Free — it falls out of the same
        # cached passes.
        alternatives=[{"sector": name, "candidates": count}
                      for name, count in available.items()],
        note=note,
    )
    with LOOP_RESULTS_LOCK:
        LOOP_RESULTS[key] = body
        while len(LOOP_RESULTS) > LOOP_RESULTS_MAX:
            LOOP_RESULTS.pop(next(iter(LOOP_RESULTS)))
    return jsonify(body)


def _acquire_loop_lock():
    """Take the build lock: at once if it is free, else by waiting in the one
    waiting slot for up to `LOOP_BUSY_WAIT_S`. False means refuse."""
    if LOOP_LOCK.acquire(blocking=False):
        return True
    if not LOOP_WAIT_SLOT.acquire(blocking=False):
        return False
    try:
        return LOOP_LOCK.acquire(timeout=LOOP_BUSY_WAIT_S)
    finally:
        LOOP_WAIT_SLOT.release()


def _cached_loop(key):
    """A loop already built for exactly this request, or None."""
    with LOOP_RESULTS_LOCK:
        cached = LOOP_RESULTS.pop(key, None)
        if cached is not None:
            LOOP_RESULTS[key] = cached          # move to the warm end
        return cached


@app.get("/api/health")
def health():
    return jsonify(status="ok", nodes=len(ROUTER.nodes),
                   routing_slots=ROUTER.n)


@app.get("/")
def index():
    """Say what this service is, rather than 404ing.

    Flask's default 404 on `/` renders as a page headed "Not Found", which reads
    as a broken deployment when you open the bare hostname in a browser to check
    a tunnel — even though the server is answering perfectly. Returning a small
    description makes a bare visit a useful liveness check and documents the
    query shape for anyone poking at the API by hand.
    """
    return jsonify(
        service="sundaydrive-api",
        status="ok",
        nodes=len(ROUTER.nodes),
        routing_slots=ROUTER.n,
        endpoints={
            "/api/route": ("from=LAT,LON&to=LAT,LON[&pref=0..1][&via=LAT,LON]"
                           "[&avoid_unpaved=0..2]"
                           "[&w_<type>=0..4][&options=1]"
                           "[&leave=LAT,LON,DEG][&rejoin=LAT,LON,DEG]"),
            "/api/loop": (f"from=LAT,LON&km={MIN_TARGET_KM:.0f}..{MAX_TARGET_KM:.0f}"
                          "[&sector=NE][&pref=0..1][&w_<type>=0..4]"
                          "[&avoid_unpaved=0..2]"),
            "/api/health": "liveness check",
        },
        # How the two routing endpoints take those parameters. The app posts
        # them, so a driver's coordinates stay out of every URL.
        parameters=("POST as an application/x-www-form-urlencoded body, "
                    "or GET as a query string"),
        loop_sectors=list(SECTORS),
        beauty_types=[name for name, *_ in BEAUTY_TYPES],
        region=REGION,
    )


if __name__ == "__main__":
    # 0.0.0.0 listens on all interfaces so a phone on the same Wi-Fi can reach
    # this dev server. (127.0.0.1 would only be reachable from this Mac.)
    app.run(host="0.0.0.0", port=5057, debug=False)
