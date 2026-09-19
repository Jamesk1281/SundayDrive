# Measuring travel times

**Status:** current. Split out of the README 2026-09-16. The model itself is
worked through in [`docs/junction-timing-plan.md`](junction-timing-plan.md);
this is how the measurement is taken and read.

Travel time was `length_m / speed_kmh`, summed over the route's edges — free
flow, with nothing charged for traffic lights, stop signs, turns or traffic,
though New England has 25,213 mapped signals and 49,669 stop signs. Measured against two
recorded drives it ran 22% short of the clock.

It is now two terms, both applied in `router.py` when the graph loads:

    time = distance ÷ (speed limit × how fast that class is really driven)
           + the controls on that road, in the direction they face

`SPEED_FACTOR` holds the first (0.95 on surface roads; motorway 1.16, because
drivers exceed the limit), `CONTROL_SECONDS` the second (9.5 s per signal met,
9.3 s per stop sign — P(stop) and the wait folded together). `graph.py` counts
the controls per edge per direction; both tables are fitted from traces by
`tools/fit_junction_cost.py`. Full workings in
[`docs/junction-timing-plan.md`](junction-timing-plan.md).

The third defect was underneath both: `SPEED_KMH`, the assumed limit where OSM
has no `maxspeed` tag — 77% of the network's kilometres — was a table of
guesses. Read off the tagged roads of the same class instead, `residential` goes
from 30 km/h to 40 (25 mph, Massachusetts' statutory default; 30 is not a limit
posted anywhere in the state) across 36,871 km of road, and `trunk` from 85 to
64. That table was doing most of the damage: with it fixed, the per-class speed
factors collapse from 0.86/0.89/0.93 to 0.94/0.94/0.95 — one number, not three,
which is why one number can now cover the classes with no measurement at all.

Guessing a correction would be calibrating against Apple Maps' model — traffic
included — rather than against the road. So the app measures instead. Every
drive writes an NDJSON trace to its `Documents/traces` folder
(`ios/Sources/DriveTrace.swift`): one record per GPS fix, carrying both the raw
position and the fix's match onto the route line. That match is the measurement
— `travelled` is metres along a known route, so its slope against the timestamp
is real speed at a known place on a known road.

Getting a drive worth analysing:

- **Start where the route starts.** Fixes taken before the driver reaches the
  line are dropped — the match lands wherever the route happens to pass nearest,
  which is not where they are. Driving two miles to the route start measures
  nothing.
- **Watch the indicator.** The nav screen shows whether it is recording, next to
  the arrival time. If it says otherwise, the drive is not worth taking.
- **Expect the blue bar.** Background location is on during a drive, so a locked
  phone or a phone call doesn't end the recording. It stops when the drive does.
- **Plug in.** A 1 Hz GPS with the screen awake is not gentle on a battery, and a
  phone that dies at minute 50 takes the last of the drive with it.
- **Drive the same route twice at different hours** if you want to separate
  traffic from the road. Nothing else can: one drive cannot tell a busy junction
  from a slow one.

- **Follow the reroutes, or expect fewer of them.** A reroute now opens with the
  maneuver you have to make — "Make a U-turn on Bedford Street" — rather than a
  compass heading, because the destination is often behind you and "Head
  southeast" reads as "carry on". If you decline several in a row the app waits
  longer each time before asking again, and it stops re-planning inside the last
  300 m. All three landed after 2026-08-22, where one drive rerouted ten times
  in 160 seconds and the banner reset to its first instruction each time.

- **Start on the road, not in the driveway.** The origin snapped 165 m from the
  car on one 2026-08-22 drive, which put the route's first coordinates on a
  different street: 3.5 minutes and 1.5 km of that drive are unmeasurable, and
  nothing could re-route out of it. The app now gives up on a route you are
  driving *away* from, but the cheap fix is to pull onto the street first. Only
  the *origin* still has this problem — destinations go through the access layer
  below.

- **A destination in a car park is routed to the car park's entrance.**
  `highway=service` is not in the routing graph and never will be (433,969 of
  them against 227,251 drivable ways), but it *is* extracted into
  `access_ways.parquet` / `access_entries.parquet` purely so
  `Router.snap_destination` can turn a pin inside a lot into the road you can
  get in from. Without it, three of the five 2026-08-22 destinations snapped to
  the wrong side of the building and two to a road with no connection to the lot
  at all. The layer is optional: absent, the router silently reverts to nearest.

- **Tap the two buttons.** They are the only record of whether the route was any
  good — see [Measuring whether the roads are
  nice](measuring-scenery.md). A drive that measures the clock
  perfectly and says nothing about the scenery has tested the part that was
  already working.

Then pull the traces off through Files.app (On My iPhone → Scenic) or Finder
over a cable — do it before deleting the app, since that takes them with it:

```sh
.venv/bin/python tools/analyze_trace.py data/processed-ne traces/*.ndjson
```

which reports, per drive and pooled across drives:

- **the headline** — actual vs. predicted minutes for the ground actually
  covered, priced per snapped edge rather than by scaling the route's total, so
  a drive that rerouted or was abandoned halfway still counts;
- **a speed factor per road class** — measured moving speed against the speed the
  graph assumed. This is what `SPEED_KMH` should be multiplied by. Classes with
  too little road behind them are marked, not quietly averaged in;
- **stops, split by what caused them** — at a mapped traffic signal, a stop sign,
  a turn, or nothing identifiable. This is the split the whole exercise turns on:
  a signal is on that road *every* time you drive it, so it belongs in `graph.py`
  and needs no traffic feed, while an unexplained stop is congestion that no
  static data will ever predict. Summing them would bake one afternoon's traffic
  into the graph permanently;
- **speed by grade band** — whether the back roads are slow because of the
  corners or because of the climb.

Four things worth knowing before reading a report.

*Parking is not junction cost.* A stationary run longer than `PARKED_S` (5 min)
is held out of both the junction cost and the clock the router is judged
against, and listed at the end of the report with its time and place so the
threshold can be overruled. This is not fussiness: on the drives of 2026-08-22
two runs, of 7 and 13 minutes, carried 57% of all measured stopped time, landed
in the "unexplained" bucket, and moved one drive's headline error from +23% to
+59%. Fitted, they would have become a permanent per-junction penalty on every
road in the state. If one of the listed runs was really the road stopping you —
a freight crossing, a drawbridge — raise the constant and re-run.

*Every exclusion is reported.* The analyzer drops fixes it can't trust, and the
dangerous failure is the silent one: a phone that stops reporting while the car
is stationary turns every stop into a gap, the junction cost reads zero, and that
looks like good news. So wall-clock time is printed next to measured time, and
unaccounted minutes next to both — with the drive's own `phase` records saying
which gaps were the app being backgrounded rather than a tunnel.

*The app is set up so a drive can't be half-lost.* `LocationManager` runs with no
distance filter (a filter can't make fixes arrive faster — GPS is ~1 Hz — it only
suppresses ones that moved too little, so the 5 m filter this used to carry
deleted the record of every car sitting still), and with `UIBackgroundModes:
location`, so a locked phone or an incoming call doesn't silently end the drive.
The nav screen shows whether it is recording, because a screen that looks normal
while recording nothing costs a whole drive.

*Grade is measured over a 200 m baseline*, on smoothed altitude, and reported
only in coarse bands. Rise over a single 20 m step is almost entirely phone-GPS
noise, and read that way a dead-flat drive splits neatly into confident-looking
uphill and downhill — the curvature mistake exactly. There is a test for it.

Applying the correction was a bigger change than it looks, and this warning
turned out to be the right one: `minutes` is the Dijkstra weight, not a display
field, so making time more expensive divides through as a *smaller effective*
`BETA`. Measured after the fact, the pref slider's bottom half had gone soft —
a pref-0.25 route found scenery of 3.39 where it used to find 4.62 — and `BETA`
had to rise from 7.0 to mean the same thing to a driver. It and `PREF_CURVE`
trade against each other, so they are swept as a pair; they now sit at 8.0 and
2.0, re-swept 2026-08-29 when road surface left the score. The top half was
untouched either way, because the scenery penalty saturates up there: past
pref ~0.5 the router has already taken every detour worth taking, and the
scenery ceiling is 5.6 on the 0–10 scale whatever these two are set to.

The re-ranking prediction was half right. Per-class factors do re-rank, but not
toward arterials: arterials carry 123 traffic signals per 100 km against a
motorway's 0.9, so the correction makes *them* the expensive option. What it
rewards is motorway. Across 40–90 km trips the fastest route got 4% faster while
the max-scenic one got 15% slower, so the honest gap between them widened from
44% to 71% rather than narrowing.
