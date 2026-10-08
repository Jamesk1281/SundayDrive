# Route options: the in-between routes behind the dial

**Status:** merged into `main` 2026-10-07 and deployed to the Oracle box
**with options off**: the server computes them only with
`SUNDAYDRIVE_ROUTE_OPTIONS=1` (`server/app.py`, `ROUTE_OPTIONS`), which is not
set there. Code: `pipeline/options.py`, `server/app.py`, and
`ios/Sources/{Models,RouteService,RouteModel,DirectionsView,PlanningMap,
NavigationModel,DriveTrace}.swift`. Tests: `tests/test_options.py` (30) and
`ios/Tests/RouteOptionsTests.swift` (18). The study scripts and raw results
are in [route-options-study/](route-options-study/). "The brief" below is the
dispatch brief, `git show e26766a:docs/route-options-brief.md`.

## The problem, in one paragraph

The router's cost per edge is `d_minutes + strength · BETA · penalty`
(`Router._weights`), so a route's cost is a straight line in slider strength
and the slider can only return routes on the lower envelope of those lines.
The envelope's middle routes own slivers of the track. On the median sampled
trip the detour is past half its maximum by strength 0.17. Many in-between
routes are on no envelope at all ("VT-100, then I-89"). On Waitsfield VT →
Needham MA the dial gave +16 min or +112 min and nothing in between. Retuning
`BETA` or `PREF_CURVE`, remapping the handle, sending several of today's
routes, and a detour-limited ("slack mask") search were all measured, and all
lost to splicing (table below). None of them is built.

## What was built

### The server: `pipeline/options.py`

**`plan`**, for a new trip:

1. `S` is the route at pref 1 under the request's beauty weights, avoidance
   and date: one full Dijkstra, the same cost as today's scenic arm.
2. One forward and one reverse pref-0 Dijkstra are capped at `S`'s pref-0
   cost. The cap is exact, because every prefix and suffix of `S` is itself a
   path. The pref-0 matrix and its transpose are cached per (closure version,
   `avoid_unpaved`), two entries of ~80 MB each. Pref 0 ignores beauty
   weights, so one entry serves every user.
3. The fastest route comes from the forward tree, so no A* arm runs.
4. Switch points are placed along `S` every `max(0.5 km, len(S)/250)`. Every
   pair `i < j` is a candidate route: `fastest(start → S[i]) + S[i:j] +
   fastest(S[j] → destination)`. Minutes, km and beautiful km are O(1) per
   candidate from cumulative sums. Minutes are `d_minutes`, never tree
   distance: pref-0 weights carry the dirt-road avoidance (Trap 7, and a test
   that fails if it is broken).
5. The Pareto frontier is taken on (extra minutes, beautiful km gained). Only
   candidates that add time *and* beautiful road survive (the rule
   `_no_worse_than_fastest` enforces on the old response). Frontier points
   that drive a junction twice (`real_node`, not expanded indices) are
   dropped, and the frontier is recomputed until stable.
6. The frontier is thinned to a **menu**. The first option must add at least
   half a mile of beautiful road. Each later one must add `max(1 mi, 5% of the
   whole gain)` over the last option kept. The most scenic frontier point is
   always kept, and the fastest route is option 0.
7. The **default** is the most scenic option costing at most 25% of the
   fastest time (the owner's rule). The fastest route and the default go out
   in full detail. Every option goes out as figures, its two switch points,
   the roads of its scenic stretch and a line simplified to ~20 m.

**`spliced_route`** rebuilds one option from its switch points: fast roads
to `leave`, pref 1 to `rejoin`, fast roads to the destination. It is the same
code path for three callers: fetching an option in full, rerouting before the
stretch (both points), and rerouting on it (`rejoin` alone). A sub-path of a
cheapest path is itself a cheapest path, so the rebuild reproduces the priced
option exactly, ties aside. Across the re-run, **503 of 503 menu options
rebuilt to the same minutes, km and beautiful km, with no repeated junction**.

**Switch points** (Traps 5 and 6) are `{lat, lon, heading, road}`. Each sits
on the scenic road 15 m past the junction it names (or halfway along a
shorter road), never on the junction itself and never as a node id. The
heading says which way along the road the route drives. Rebuilding finds the
road within 2 m whose bearing is within 30° of that heading, so a rebuild on
another box or a rebuilt graph lands on the same road or raises
`SwitchPointNotFound`. In that case `/api/route` falls back to the plain pref
route instead of failing a driver mid-drive.

One defect was found and fixed by the re-run. A junction split for a turn
restriction stands at several graph indices. On trip 18 (Everett → Easton
area) the leave road could be entered from two copies of its junction. The
cheapest arrival at either one looped back through the junction, so the
rebuild drove it twice and came back 1.8 min shorter than the option priced.
`_legs` now searches to each copy separately and keeps the cheapest whole
route that drives no junction twice, which is the plan's own test.
`two_copies` in `tests/test_options.py` is that trip.

### The API

```
POST /api/route  from, to, pref, w_*, avoid_unpaved   + options=1
  -> {"fastest": ..., "scenic": <the default option in full, with "switch">,
      "options": {"default": i,
                  "menu": [{"extra_minutes", "minutes", "km", "beautiful_km",
                            "leave": {lat, lon, heading, road} | null,
                            "rejoin": ... | null,
                            "roads": ["VT 100", "US 4"],
                            "line": [[lon, lat], ...]}, ...]}}

POST /api/route  from, to, pref=1, w_*  + leave=LAT,LON,DEG [+ rejoin=LAT,LON,DEG]
  -> {"fastest": ..., "scenic": <that option in full, with "switch">}
```

It is backward compatible by construction. Options are computed only when the
request says `options=1` **and** the flag is on **and** no heading,
declined U-turn or switch point was sent **and** nothing else is computing.
Every other request gets today's reply, with today's two keys. A spliced
route's properties carry `"switch": {"leave", "rejoin"}`, which an old client
ignores. `null` at an end means the option is scenic from the start, or to
the destination.

### The busy guard (Trap 3, and review finding K-1)

`IN_FLIGHT` counts the `/api/route` and `/api/loop` requests computing. A plan
computes options only if it found nothing else running and `LOOP_LOCK` free,
and it gives up between phases the moment another request arrives
(`plan(..., abort=_not_alone)`). It then sends today's reply, so a waiting
driver pays at most the phase in progress, about one search's time. Options
never run under `LOOP_LOCK`. They never run for a reroute (heading, declined
U-turn or switch points) or for "switch to fastest" (pref 0 plus heading).
So in a burst, the queue drains at today's rate. The guard is what keeps K-1
where it was, rather than letting it get twice as easy to hit.

### The app

- **Detents.** When the plan has a menu, `PrefDial` shows `OptionDial`: one
  detent per option, evenly spaced by index. The handle opens on the
  default. The readout prints the price of the option under the handle
  *while dragging*, because every price came with the plan. Below the price,
  a caption says where the route leaves and rejoins the fast roads, for
  example "Fast roads to VT 100, scenic on VT 100 and US 4, back on fast roads
  after US 4." (`OptionCaption`).
- **On release** (`RouteModel.chooseOption`), the fastest route, the default
  and any option already fetched show at once. Any other option is drawn from
  its simplified line straight away (`previewLine`) and fetched in full by its
  switch points. "Start driving" is disabled until it lands.
- **Without a menu** (flag off, server busy, or an older backend) the dial is
  today's continuous `pref` slider, unchanged.
- **The fastest detent drives at exactly `pref == 0`**
  (`RouteModel.drivePref`). Every other option drives at pref 1 with its
  switch points (Trap 8).
- **The trace header** records `leave` and `rejoin` next to `pref`, as `[lat,
  lon, heading]` or null, only on drives from a menu.

### Rerouting a spliced plan

`NavigationModel` takes the plan's switch points from the route's
`properties.switch`. It latches `passedLeave` and `passedRejoin` once the
matched position (`travelled`, joined only) passes each point, and
re-measures both on every adopted line. A reroute then asks:

| where the driver is | request | arm taken |
| --- | --- | --- |
| before the scenic stretch | `fetchLegs` with `leave` and `rejoin` | `scenic` |
| on it | `fetchLegs` with `rejoin` only | `scenic` |
| on it, plan scenic to the end | plain `fetchRoute` at pref 1 | `scenic` |
| past it | plain `fetchRoute` at pref 0 | `fastest` |

The reroute goes through the same `reroute()`, so every guard of the
mid-drive recovery build (`docs/mid-drive-recovery.md`) applies unchanged:
backoff, failure classes, the wrong-way detector, the declined U-turn (sent
along with the legs) and the trace record. Past the stretch, `pref` and
`followingFastest` are left alone, because the driver gave nothing up.
"Switch to fastest" is untouched: it sets `pref = 0`, and with `pref == 0`
no legs are sent.

## The study, re-run through the endpoint

`route-options-study/endpoint_batch.py` drives `server/app.py` through Flask's
test client with gzip, on the brief's 60 trips (`route_census.sample_pairs`,
seed 20261007, five bands). `endpoint_analyze.py` scores them as
`compare_single.py` scored the study. Raw results:
`route-options-study/results/endpoint_60.jsonl`. 59 trips routed (one snaps
too far); 44 have a detour of at least 10 min and a gain of at least 1 mile,
the same count as the study.

| method | largest gap (median share of detour) | gap ≥ half | gap ≥ a third | scenery for ¼ the time | for ½ | menu size (median) |
|---|---|---|---|---|---|---|
| today's dial (study) | 0.55 | 27/44 | 37/44 | 0.02 | 0.15 | — |
| splicing, one base (study prototype) | 0.25 | 3/44 | 10/44 | 0.28 | 0.55 | — |
| **built, through the endpoint** | **0.25** | **2/44** | **11/44** | **0.28** | **0.55** | 13 |
| detour limit (study; not built) | 0.66 | 36/44 | 44/44 | 0.05 | 0.13 | — |

That reproduces the study's one-base row within noise. As in the study, the
full detour and gain are those of `S`, the route at pref 1, recorded per trip
as `base`. A first version of the scorer used the frontier's last point
instead. That point is shorter than `S` on 19 of the 44 trips, because a
spliced route can beat the full scenic route on both counts, and it inflated
the same menus' gaps to 4–6/44. Don't score against the frontier's end.

One rule differs from the prototype on purpose. **The first option must add
half a mile** of beautiful road. The prototype kept the first frontier point
however little it added, which on the 59 trips put 33 options at "+0 mi" on
the dial. Scored on the same frontiers:

| first-option rule | gap ≥ half | gap ≥ a third | "+0 mi" options |
|---|---|---|---|
| the prototype's (keep the first point) | 1/44 | 11/44 | 33 |
| **half a mile (built)** | **2/44** | **11/44** | **2** |
| the full step, from the fastest route | 3/44 | 11/44 | 2 |

The default option never cost more than 24.9% of the fastest time. Three
trips open on the fastest route because no option fits in 25%, and two have
a menu of one.

**Waitsfield → Needham** (2026-10-06 closures) opens on **+43.7 min**
(VT-100 to Killington, US-4 through Woodstock), option 3 of 12. The menu is
+3.5 (Brookside Road and Forest Street at the Needham end), **+16.4** (VT-100,
VT-107, I-89), **+43.7**, +63.3, +98.4, +106.4, +116.8, +135.2, +142.4,
+171.8 and +181.2 min (189.9 beautiful km). The brief's +16 and +44 are both
there, unmoved. Its +6.9 dropped out: under the menu rule it adds 6.6 km
over the +3.5, short of the 8.8 km step (5% of this trip's gain).

## Capacity

The figures are medians over the same 59 trips, in units of **one plain
pref-1 search timed in the same loop** (0.23 s here, median). That unit makes
the ratios immune to whatever else this machine was running (Trap 11).
"today" is `POST /api/route` at pref 0.5 and "options" adds `options=1`, both
end to end through the Flask app with gzip. "detail" is the fetch of the
default option by its switch points, which is also the cost of a reroute by
legs.

| band | today | options | **options / today** | p90 | detail | gzip KB today → options |
|---|---|---|---|---|---|---|
| 10–25 km | 1.20 | 1.19 | **0.97** | 1.08 | 1.27 | 10.3 → 11.3 |
| 25–50 km | 1.21 | 1.38 | **1.14** | 1.39 | 1.30 | 23.7 → 26.0 |
| 50–100 km | 1.30 | 2.59 | **1.90** | 2.20 | 1.47 | 46.0 → 51.5 |
| 100–200 km | 1.55 | 3.61 | **2.28** | 2.51 | 1.78 | 86.4 → 92.5 |
| 200–350 km | 1.76 | 3.64 | **2.12** | 2.38 | 2.05 | 123.7 → 130.4 |
| all | 1.31 | 2.42 | **1.66** | 2.35 | 1.48 | 43.5 → 50.9 |

An earlier run of the same batch gave 1.55 overall and the same shape by
band, so read the ratios as ±0.1. Inside a plan, the phases cost 1.02 units
for the scenic base, 1.11 for the two capped trees, 0.06 for the splice, 0.05
to build the menu and 0.01 for the default in full. Short trips cost nothing
extra: the capped trees are tiny, and the forward tree replaces the A* arm.

**On the box, by the brief's scaling** (box today, from
`server/DEPLOY-oracle.md` and the brief's §4, times the ratio above). These
are estimates for the owner to replace with a measurement there:

| band | today on the box | with options |
|---|---|---|
| 10–25 km | 0.38 s | ~0.37 s |
| 25–50 km | 0.38 s | ~0.43 s |
| 50–100 km | 0.42 s | ~0.80 s |
| 100–200 km | 0.48 s | ~1.09 s |
| 200–350 km | ~1.0 s | ~2.1 s (p90 ~2.4 s) |
| all | 0.42 s | ~0.70 s |

That is below the brief's 0.94 s because a plan with options *replaces*
today's two searches rather than adding to them. The pref-1 base is a scenic
arm, and the forward tree gives the fastest route without the A* arm. The
brief priced the trees on top of today's request.

- **Steady traffic** is not the problem. At ~0.70 s a plan, half the box's CPU
  is ~2,500 plans in a peak hour. Settling on an option costs one detail fetch
  (~1.5 units, about today's plan) unless it is the fastest, the default, or
  one already fetched. Today, every slider release is a full request.
- **Bursts** are the existing problem (K-1), and the busy guard keeps them
  there. Under load every plan is today's plan, so the 20 s client timeout is
  reached at the same queue depth as today.
- **Memory:** two cached pref-0 matrices of ~80 MB each, and a few n-sized
  arrays per request.
- **Payload:** the menu adds ~5–7 KB gzipped to a plan. Full geometry for
  every option would be ~2.5 MB (Trap 4). The default option is sent in full
  instead of the pref-0.5 route, which is why the totals barely move.

## For the owner

1. **To measure on the box,** with the flag still off, run the batch there:
   `python docs/route-options-study/endpoint_batch.py <checkout> <processed-ne>
   <out dir>`, then `endpoint_analyze.py <out dir>/results.jsonl`. It sets
   the flag in its own process only.
2. **To turn options on:** add `Environment=SUNDAYDRIVE_ROUTE_OPTIONS=1` to
   the unit (`server/DEPLOY-oracle.md`, the `[Service]` block), then
   `daemon-reload` and restart. To turn them off, remove the line and restart.
   No deploy is needed either way.
3. **The phone build** is needed for the detents, the caption and rerouting
   by legs. Against a server with the flag off, the app behaves exactly as
   today.
4. **On a drive,** check that a missed turn before the scenic stretch comes
   back via it, and one after it goes home on fast roads. Recording is on in
   Debug builds, so the trace header shows which option was driven.

## What is not done

- **Not driven.** Rerouting by legs is tested on the simulator against stub
  routes. The server side is tested on the real graph, including a reroute
  from halfway along the stretch.
- **The planning map does not reframe per detent.** The camera fits the plan's
  default when it arrives, and a much longer option may run off the card.
  Reframing on release is a small follow-up if it shows up on the phone.
- **Detents are not haptic.** SwiftUI's stepped `Slider` snaps but gives no
  tick. Not asked for.
- **Loops** are untouched. They have no menu, and their reroutes go `via` the
  far point as before.
