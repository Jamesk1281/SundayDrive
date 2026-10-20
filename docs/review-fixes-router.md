# Review fixes: router and server

**Status, 2026-10-20:** built and measured on branch `claude/review-fixes-router`
off `usa` (`4f74951`). Not merged, not deployed, not pushed. The pack format is
unchanged, so nothing needs rebuilding for this branch.

These are the router and server defects the outside review of `usa` found on
2026-10-20. Each was re-checked here on the national pack (`data/pack-us`) and
on New England (`data/processed-ne`).

| item | what changed | where |
|---|---|---|
| 1. A moving car on a closed road | a moving car's route begins at the car (the lead-in), which is what the I-10 symptom needed; a moving car on a closed road snaps onto it and leaves forward; a reroute starting off its road over 500 m away is refused (`START_TOO_FAR`) | `Router.snap_lead`, `lead_into`, `_road_under`; `app._route` |
| 2. `via` skipped the cap | each leg capped as a trip is (`LEG_TOO_LONG`) | `app._route` |
| 3. Non-finite inputs | refused before any work (`BAD_INPUT`); every error is JSON | `app._finite`, `_parse_ll`, error handlers |
| 4. False "no route found" | the corridor widens up to the longest trip's (`NO_ROUTE_NEARBY` after that) | `router.corridor_budgets` |
| 5. Loops capped at 400 km | capped by how many nodes the start's disc holds; `POST /api/loop/limit` | `LoopPlanner.max_km`, `LOOP_DISC_MAX_NODES` |
| 6. Instruction text | first value of multi-value tags; a direction on unsigned exits; nameless roads described | `RouteResult` steps |
| 7. Messages and health | sentences with codes, "310 miles", `region`/`commit`/`pack` | `app.py` |

- **The suite:** 1,059 passed, 13 skipped, 0 failed on `processed-ne`
  (`usa`: 987 and 13).
- **New England parity:**
  - Every request planned from rest draws the same line as `usa`, and so do all
    3,000 snaps; only step wording differs, each change put down to one of the
    instruction rules.
  - Every moving request draws `usa`'s line with a lead-in from the car in
    front of it.
- **The blocker in item 1 was not the snap.** On I-10 the route began 9 miles
  *ahead* of the car, on the road it was driving, because every reroute began
  at a junction. The master session decided on 2026-10-20 to build a lead-in
  on the server, and it is built. On New England, the share of reroutes
  starting more than 500 m from the car went from 27.6% to 0. A moving car on
  a one-way carriageway that a closure cuts off now drives on through it
  (section 1, "Committed to a carriageway").

## The contract with the app and the deploy

### Error bodies

Every JSON error is `{"error": <sentence>, "code": <string>, ...numbers}`. The
sentence has a capital first letter and a full stop, and the app may show it as
written. Numbers are JSON numbers, never strings; `nearest_km` may be `null`.

| code | status | when | numbers |
|---|---|---|---|
| `TRIP_TOO_LONG` | 400 | a trip over the cap: 500 km straight line, 650 km for a reroute | `km`, `max_km` |
| `LEG_TOO_LONG` | 400 | either leg of a `via` route over the same cap | `km`, `max_km`, `leg` (1 or 2) |
| `LOOP_TOO_LONG` | 400 | a loop over this start's limit | `km`, `max_km` |
| `NO_ROUTE_NEARBY` | 404 | the search widened as far as it goes and found no route | |
| `START_TOO_FAR` | 400 | a moving car's route would start more than 500 m from it | `m`, `max_m` |
| `OUTSIDE_COVERAGE` | 400 | a point more than 5 km from any covered road | |
| `BAD_INPUT` | 400 | a parameter missing, unreadable, non-finite or off the Earth | |

The seven codes above, agreed between the units, do not cover the refusals
that existed before them. Each has
a code now, so the app never has to read a sentence to know what happened:

| code | status | when | numbers |
|---|---|---|---|
| `CLOSED_FOR_SEASON` | 404 | only a road closed for the season connects the two points | |
| `SAME_ROAD` | 400 | both points snap to the same stretch of road | |
| `NO_LOOP` | 404 | no loop of that length from that start | `nearest_km` |
| `BUSY` | 503 | a loop build refused while another runs (unchanged behaviour) | |
| `NOT_FOUND` | 404 or 405 | no such endpoint, or the wrong method (`GET /api/loop/limit`) | |
| `SERVER_ERROR` | 500 | a bug; logged with its traceback | |

`server.CLOSED_FOR_SEASON` still names the sentence, as before, because
`tests/test_closures.py` (unit D's) compares against it. The code constant is
`SEASON_CLOSED`.

### The loop limit

`POST /api/loop/limit` with `from=lat,lon` in the form body returns
`{"max_km": <float, one decimal>, "max_mi": <int>}`. `max_mi` is `max_km` in
miles rounded down, so the slider's top turned back into km never exceeds the
limit. `GET` is refused with `NOT_FOUND` (405), so coordinates never sit in a
URL. A loop request over `max_km` + 0.5 km is refused with `LOOP_TOO_LONG`;
the 0.5 km absorbs a client converting `max_mi` back with a slightly different
factor. A request under 5 km is still raised to 5 km, as before.

### Health

`GET /api/health` keeps `status`, `nodes` and `routing_slots` and adds:

- `region`: `SUNDAYDRIVE_REGION` if set, else the pack manifest's `region`,
  else "New England".
- `commit`: `SUNDAYDRIVE_COMMIT`, else the first line of `DEPLOYED_COMMIT` in
  the checkout's root, else `null`. Unit P's deploy writes both (agreed by
  message on 2026-10-20).
- `pack`: the hex sha256 of the pack's `manifest.json`, or `null` when
  `SUNDAYDRIVE_PACK` is unset or empty. The manifest names every source
  parquet's hash, so a rebuild after any data change changes it.

On the US pack today: `region` "the contiguous United States", `pack`
`04e86dac…85b4`.

## 1. A moving car on a closed road

### What actually happened on I-10

The defect was put down to `_shut_at` → `_nearest_open` (`router.py`, the
snap). That rule does not run on the review's edge. Measured on the US pack:

- **The edge.** Edge 1470492 (I-10 westbound, 16.4 km) has **one** ford inside
  it, 3.4 km from its east end. A car beside a single barrier takes the end on
  its own side (`_barrier_end`), not the nearest open road.
- **Short of the ford.** The carriageway is one way, so from the edge's east
  end the only way on is west, through the ford. `_ways_round` therefore counts
  that node as cut off. Its way out is the nearest node beyond the ford: the
  edge's own west end, 16.2 km on.
- **What the `usa` code does.** A westbound car 10% along the edge was started
  at the west end. The route began **14.8 km ahead of the car**, on the road it
  was driving, with "Head west on Pearl Harbor Memorial Highway" and no
  turnaround. Past the ford, 25% along, it began 12.3 km ahead. Both were run
  on the `usa` checkout itself.

So the review's "Off route · route 9.5 mi away / Head back to your route" was
not a jump to another road, and the U-turn arrow was not a U-turn. It is the
app's off-the-line banner (`isOffTheLine`, `arrow.uturn.backward`) for a
route whose line begins 9 miles ahead along the car's own road. Every reroute
begins at a junction, and on a 16 km interstate edge that junction can be
16 km away. This is not specific to closed roads; it applies to any long edge:

- in the New England parity requests, 28% of reroutes with a heading begin
  more than 500 m from the car (p50 172 m, p90 1,137 m, worst 7.6 km);
- on the US graph, a point on a motorway is more than 500 m from the junction
  ahead on 56% of motorway length, and more than 2 km on 24%.

That is the blocker. The master session decided on 2026-10-20 to fix it on
the server with a lead-in, below ("The lead-in").

The snap rules below are a separate fix: they stop a moving car being sent
to some other road. On I-10 they leave the route as `usa` had it.

### The lead-in

For a moving request (a heading or `declined_uturn`), the line the server
returns begins at the car's position projected onto the edge it is snapped
to. It runs along that edge to the junction the route starts at, then follows
the route exactly as before.

`Router.snap_lead` returns the snap and a `Lead`:
- the edge;
- its [lon, lat] points from the car's place to the junction, ending on the
  junction's exact coordinates;
- its metres and minutes: the edge's length, and the travel time of its
  driven direction, prorated by the share of the edge left to drive.

There is no lead-in when the snap left the car's road (START_TOO_FAR decides
those), or when the car is within 1 m of its junction (`LEAD_MIN_M`).
`Router.lead_into` puts it in front of a `RouteResult`. `app._route` applies
it to both arms of every moving answer: plain reroutes, declined U-turns,
option reroutes and loop rejoins with a heading. A request from rest never
gets one.

The shape the app receives:

- **The line.** `geometry.coordinates[0]` is the car's projected position,
  within the snap's offset of the fix (at most 0.1 m in the parity replay).
  The coordinates up to the start junction are the car's own road. After it,
  the line is the route's, vertex for vertex.
- **The totals.** `km` and `minutes` include the lead-in. `mean_score`,
  `beautiful_km` and `scenery_km` count it as part of the car's road.
- **The first step covers the lead-in.**
  - It starts at the car (`lat`, `lon`), and its `distance_m` includes the
    lead-in's metres.
  - When the lead-in is 60 m or longer (`MIN_INSTRUCTION_GAP_M`) and the route
    turns at its junction, the lead-in is a step of its own ("Head south on
    Fellsway"), and the turn follows it ("Make a U-turn to stay on Fellsway").
    The U-turn used to be said as the first step, from a car 60 m or more
    short of the junction where it happens.
  - Shorter lead-ins fold into the first maneuver, which keeps its words and
    starts at the car. At Bedford, 2 m short of the junction, the first step
    is still "Make a U-turn on Bedford Street".
  - A first step on a nameless road says where it leads ("Head east toward
    I 495"). This applies only with a lead-in, so a trip from rest is worded as
    before.
- **`turns_around` and `turnaround_m`** are judged on the lead-in and then on
  the route after it, offset by the lead-in's length. A U-turn at a junction
  800 m ahead is still found, 1,600 m along the line. Judged on the whole line,
  the 1,000 m window would have missed it.
- **Not changed:** the pack, the snap, the search, and every request from
  rest, byte for byte.

**On New England** (the 123 reroutes with a heading in the parity set), the
distance from the car to where its line begins:

| | p50 | p90 | max | over 500 m |
|---|---:|---:|---:|---:|
| before | 172.5 m | 1,137 m | 7,633 m | 27.6% |
| with the lead-in | 0.0 m | 0.0 m | 0.1 m | **0** |

The parity reroutes start on route vertices, so their projections are exact.
A real fix lands up to its GPS error from the road, and the line begins at its
projection.

**On the US pack** (`data/pack-us`, where the ford on edge 1470492 is still
closed): run after unit D's `pack-us-next.done` appeared, with no pack build
running. The reroute was westbound on I-10, heading about 280, to Blythe at
pref 0.5. The fix was 15 m to either side of the road, at 10%, 25%, 50% and
90% along the edge, each with and without `declined_uturn`:

- In all 16 requests the line begins **14.9 m from the fix**, the car's
  projection onto the road; `usa` began it up to 14.8 km ahead.
- The first step is "Head west on Pearl Harbor Memorial Highway", from the
  same point, covering the lead-in and the road on to the exit.
- `km` includes the lead-in: 116.3 km at 10% against 101.6 km before. No
  request `turns_around`.

**Tests**, in `tests/test_api.py`:
- a moving car mid-way along a long New England edge: its line begins within
  30 m, its `km` and `minutes` grow by the lead-in's, its first step covers
  it, and the rest of the line is the plain route's, vertex for vertex;
- the same point from rest begins at the junction;
- Bedford's 2 m lead-in folds into the U-turn;
- a synthetic 800 m lead-in before a U-turn keeps `turns_around`. The control,
  judged the old way, misses it.

`TestAMovingCarOnAClosedRoad` checks that the closed-road reroute's line
begins at the car and leaves by the end ahead. Mutations: dropping the
lead-in fails 2 tests; not folding a short one fails 2.

One bug was found and fixed on the way. A car standing exactly on a vertex
gave a lead-in whose first segment was nanometres long. Its bearing was
rounding noise, and `turnaround_at` read it as driving back through the strip
behind the car (2 of 123 reroutes said `turns_around`). The lead-in now starts
at the vertex.

### Committed to a carriageway

Unit I found one case the lead-in left. On the open 1.1 km of I-10 westbound
before edge 1470492 (edge 1470493, and the on-ramp 1473085), every reroute
was refused with `START_TOO_FAR`. The car's junction ahead is cut off by the
ford, so its way out begins 17 km on, on another road. The app said "Off
route" until the car reached the closed edge.

The master session decided on 2026-10-20 that such a car is committed: it
cannot turn round, and the closure is almost certainly a mis-tag. So, only
when all of these hold:
- the request is moving, with a heading;
- the car is on a **one-way carriageway**: every directed copy of its edge runs
  the same way, or it is a motorway or a `_link`;
- the junction ahead is cut off by closures (`_ways_round`).

Then `Router._committed` follows the carriageway forward, edge by edge,
straightest first. It goes through the closed stretch and stops at the first
junction a route can start from. The route starts there, and the lead-in
covers the rest of the car's edge and every edge followed. It gives up, and
today's rule stands, when the walk passes no closed edge, or after 60 edges or
50 km (`COMMITTED_MAX_EDGES`, `COMMITTED_MAX_M`).

Two-way roads keep today's rule, because a car can turn round there; Crane
Road is unchanged. Planning from rest is unchanged. `START_TOO_FAR` still
answers every other case.

**Counted in the journal.** Each such answer prints one line, for example
`reroute through closed edges [1470492], 16.8 km of lead-in`. It names the
closed edges and never where the car is, so the journal shows how often it
happens and which closures are worth fixing. No response field changed.

**On the US pack** (`data/pack-us`, the ford still closed), the cases were:
- both edges arriving at the closed edge's east end: I-10 (1,101 m) and its
  on-ramp (610 m);
- the car 10%, 50% and 90% along each;
- on the road and 15 m to either side;
- with and without `declined_uturn`.

All 36 return 200 and start within 15 m of the fix. 34 run through edge 1470492
to its west end, each with the log line. Example: 118.4 km to Blythe, the first
step "Head west on Pearl Harbor Memorial Highway". The other two are a fix 15 m
south of the road 10% along, which is 3 m from a parallel road, so the car is
snapped to that road and routed from it, as any fix nearer another road is.
With the rule switched off, the same approach is refused with `START_TOO_FAR`
(m = 17,004). A parked request on the approach is unchanged: it starts at the
way out, as before.

**In New England**, ten one-way roads run into a closure with no open way off.
Among them:
- Kresge Way (7 edges to a start);
- Schoodic Loop Road (8);
- an airport's Inner Roadway Arrivals Level;
- Davisville Road (2 closed edges).

None appears in the parity requests: all 702 answers are identical to the
lead-in's run.

**Tests**, `TestCommittedToACarriageway` in `tests/test_closed_roads.py`:
- every New England one-way carriageway into a closure (at least 3) drives on
  through: it starts where `_committed` says, with the closed edges in its
  lead-in, and the parked control is unchanged;
- 40 two-way roads into a closure keep today's rule;
- through the API, the line begins at the car, passes the closed edge, and the
  log line is printed.

Mutations: switching the rule off fails the first test, and dropping the
one-way condition fails the second.

### The rules

A car is moving when the request carries a heading or `declined_uturn`. Only a
moving car's snap changes, and only where it has evidently driven past a
closure already:

1. **On a road closed by its tags, or between two barriers** (`_shut_at`), the
   car is on that road if it runs with the heading (within the same 40 degrees
   `_aligned_edge` uses). Failing that, the best-aligned road within 20 m of
   the nearest, open or closed, is its road. It starts from the end ahead
   (`_forward_end`), and the route leaves the road forward. With no road
   aligned, the car is not evidently on any, and the old rule (the nearest open
   road) stands. A declined U-turn with no heading takes the nearer end.
2. **Beside a barrier whose own side is cut off behind another closure**, the
   car starts from the end ahead, past the barrier. It could only have got
   there past a closure.

A car at rest keeps every rule `docs/closed-roads.md` ("Snapping") describes.
So does a moving car short of a barrier whose own side is open, such as Crane
Road's gate. Taken literally, "a moving car on a closed edge leaves forward"
would cover a car short of a barrier too. It would start a car 57 m short of
Crane Road's gate, facing it, beyond the gate. `docs/closed-roads.md` case 5
exists to prevent exactly that, and `TestTheCraneRoadReroute` sends a heading. At the approach, a real
gate and a mis-tagged ford look the same. Only a car that has already passed
one shows which it was.

### START_TOO_FAR

`Router.snap_start` returns the snap and the distance from the car to where its
route begins:

- **On the road the car was snapped to**, that distance is the distance to the
  road, however far the junction the route starts from. The car drives there
  along its own road, which is what the app's `awaitingJoin` exists for. A
  freshly adopted line "starts at the junction `snap` chose — a median 99 m
  ahead, p90 217 m" (`ios/Sources/NavigationModel.swift`), and on long rural
  edges far more.
- **When the snap left that road**, for the nearest open road or for a cut-off
  node's way out, it is the straight line to the junction the route starts at.

A reroute (moving) whose distance exceeds `START_MAX_M` = 500 m is refused
with `START_TOO_FAR`, `m` and `max_m`. A start from rest is never refused this
way.

Measuring it from the start junction instead would have refused ordinary
reroutes: every car more than 500 m from the end of a long edge.

### On the US pack

A westbound car on edge 1470492, heading 280, asking for Blythe at pref 0:

| along the edge | `usa` | this branch |
|---|---|---|
| 10% (short of the ford) | 200; route begins at the west end, 14.8 km ahead | the same route, with the lead-in from the car (below); `snap_start` puts the start on the car's own road |
| 25% to 90% (past it) | 200; begins at the west end, 12.3 km down to 1.6 km ahead | the same route, with the lead-in |

With rule 2 switched off, the 10% request is refused with `START_TOO_FAR`
(m = 14,803), because the start would come from the cut-off node's way out.
With it, the car is understood to be on its road, as it is. Each answer took
0.01–0.23 s CPU.

Eastbound on edge 1329618 (the other carriageway), short of its ford with an
open interchange behind, the car is routed back round from behind (227 km to
Phoenix). That is the Crane Road rule. Unit D's ford change opens both fords.
The remaining 71,617 national `closed_to_cars` rows are what these rules are
for.

**In the load probe's random reroutes** (random junctions, random headings,
about 330 requests), two were refused with `START_TOO_FAR`. Both were cars in
pockets the closures cut off:
- a residential street with no barrier on it, whose only way out passes a
  closure, 1.3 km away whatever the heading;
- Forest Service Road 9713A, closed by its tags, whose way out is 3.0 km away
  even with the car aligned to it.

### Tests

In `tests/test_closed_roads.py`, `TestAMovingCarOnAClosedRoad`, on the New
England build:

- Blunt Park Road (closed by its tags): a moving car starts at the end ahead
  in both directions, and its start distance is its distance to the road. The
  control: at rest it starts on the nearest open road.
- A declined U-turn with no heading still counts as moving.
- Turner Road, between two barriers: moving, it leaves by the end ahead in
  both directions. At rest, it takes the side beyond the nearer barrier, as
  before.
- A heading across the closed road is not evidence: the old rule stands.
- At rest, `snap_start` measures to the open road's junction.
- Through the API, the reroute's line begins at the end ahead.
- The cut-off side: every single-barrier edge in the build with one end cut
  off (up to 40) puts a moving car on the cut-off side at the end ahead. In
  at least one, the old rule sent it somewhere else.

`tests/test_api.py` checks the `START_TOO_FAR` wiring for a heading and for a
declined U-turn, and that a parked request is never refused that way.

Mutations, each run against the tests and then reverted:

| mutation | caught by |
|---|---|
| the moving rule never applies | 5 tests |
| the moving rule applies at rest too (trap 1) | 6 tests, among them the existing Turner Road and Blunt Park tests |
| the cut-off-side rule removed | the cut-off test |

## 2. `via` legs are capped

Both legs, from the car to the waypoint and from the waypoint to the end, are
measured in a straight line between their snapped ends before any search. Each
gets the same cap as a trip: 500 km at rest and 650 km for a moving car. On
the US pack, Boston via Los Angeles to Miami is refused in 165 ms with
`LEG_TOO_LONG`, `leg` 1, `km` 4169.5. The review measured 46.3 s and 5.8 GB
before.

No request's corridor can now become the national graph. A trip is capped
before its search; a leg is too. The widening below never goes past the
longest trip's own first corridor.

## 3. Input validation

Every number is read through `_finite`. `nan`, `inf` and anything unreadable
are refused with `BAD_INPUT` and a sentence naming the parameter, before any
snap or search:

- **Refused:** a point that is not two finite numbers, or is off the Earth
  (latitude outside ±90, longitude outside ±180), for `from`, `to`, `via`,
  `leave` and `rejoin`. Also a non-finite `pref`, `w_<type>`, `avoid_unpaved`,
  `heading` or loop `km`, and a switch point's heading outside 0–360.
- **Still clamped, as documented before:** finite `pref` outside 0–1, weights
  outside 0–4, `avoid_unpaved` outside 0–2, and a loop `km` under 5. Finite
  headings outside 0–360 are still dropped: CoreLocation sends -1 for "no
  course" (`_parse_heading`).
- **One behaviour changed:** `w_coast=1e999` (infinity) used to be clamped to
  4 and is now refused. `test_weights_are_clamped_not_rejected` was split
  accordingly.

Flask's own refusals and any unhandled exception now answer JSON with a code,
never the HTML page the app cannot read (`NOT_FOUND`, `SERVER_ERROR`).

## 4. No route nearby

`CORRIDOR_WIDENINGS` = 2 stopped two doublings in. A short trip whose road is
closed needs a detour far outside that. The schedule is now
`router.corridor_budgets`:

- The allowance doubles while fewer than two widenings have been tried, or
  while the corridor is smaller than `CORRIDOR_MAX_KM`.
- No corridor is bigger than `CORRIDOR_MAX_KM` = 770 km of |a v| + |v b|.
  That is the first corridor of a trip at the 500 km cap, unless the trip's own
  first corridor is bigger still.

| trip | corridors searched, km |
|---|---|
| 6 km | 29, 52, 98, 190, 374, 742, 770 |
| 300 km | 470, 640, 770 (was 470, 640, 980) |
| 500 km | 770 (was 770, 1040, 1580) |
| 600 km reroute | 920 (was 920, 1265, 1955) |

So a search that finds nothing costs at most what the longest permitted trip
costs anyway, and never widens toward the whole national graph. `_cheapest`,
the loop rejoin's `_leg` and the route options' scenic base share it. When it
is exhausted, the answer is 404 `NO_ROUTE_NEARBY`. Closed for the season is
still told apart (`CLOSED_FOR_SEASON`).

On the US pack, with today's data (the ford still closed): Andrew Molera to
Big Sur village, 4 miles on CA-1, now returns a 254.3 km route in 0.3 s wall
where it returned "no route found". Unit D's ford change will make it the
4-mile road.

## 5. Loops capped by density

The owner decided on 2026-10-20 that a loop's top length depends on how much
road its disc holds. The limit is `LoopPlanner.max_km(start)`: the longest
target, from 5 to 400 km, whose first disc holds at most
`LOOP_DISC_MAX_NODES` = **1,800,000** routing nodes.

The count is read off the router's node grid a cell at a time, each cell at
its centre's distance. That costs a few thousand distances and no search:
2–26 ms on the US pack through the endpoint. Against the nodes the passes
actually searched, it was within 1% on 155 of 160 runs, and within 0.8% on
every disc over 1M nodes, which is where the threshold sits (Philadelphia at
100 km: 523,501 counted, 521,198 searched). The worst miss was 5.5%, on a
194,533-node disc at Ely, NV.

### The measurement

`tools/us_scale_router/loop_limit.py` times a **first loop**: a cold planner,
then `plan` and `sectors` as the server calls them. It runs from 20 fixed
starts (12 dense metros, 4 middling, 4 sparse) and records CPU seconds, on the
US pack, with this Mac shared.

- **Replicate 1:** 100, 200, 300 and 400 km.
- **Replicate 2:** 150, 250, 350 and 400 km.
- The 400 km runs repeat across the two: median difference 10%, worst 43%.
  The worst was Philadelphia, 13.2 s then 20.4 s CPU, with a 31 s wall clock
  in the second run. That is paging: swap held 9–11 of 10–12 GB through both
  replicates, and unit D's national build ran beside them.

Cost is close to linear in the disc's nodes: CPU ≈ 2.45e-6 × nodes^1.03, with
the 90th-percentile run 1.23 times the fit.

| disc nodes | runs | p50 CPU s | p90 CPU s | max |
|---|---:|---:|---:|---:|
| under 0.5M | 54 | 0.74 | 1.64 | 1.98 |
| 0.5–1.0M | 42 | 2.76 | 3.76 | 4.32 |
| 1.0–1.5M | 19 | 4.95 | 5.85 | 6.87 |
| 1.5–2.0M | 18 | 6.52 | 7.98 | 9.30 |
| 2.0–2.5M | 17 | 8.71 | 11.02 | 15.43 |
| 2.5–3.0M | 10 | 10.88 | 14.94 | 20.40 |

The p90 reaches the target of 8.5 s Mac CPU at 1.83M nodes in replicate 1,
1.81M in replicate 2 and 1.81M pooled. The threshold is 1.8M, rounded down.
At the box's measured 1.4 times, that is about 12 s for the slowest tenth of
first loops at the limit. Later loops from the same start reuse the passes.

### What starts get

| start | limit | | start | limit |
|---|---:|---|---|---:|
| Philadelphia | 264 km, 163 mi | | Detroit | 354 km, 220 mi |
| New York | 269 km, 166 mi | | Boston | 398 km, 247 mi |
| Baltimore | 269 km, 167 mi | | Houston, Minneapolis, Miami | 400 km |
| Washington | 289 km, 179 mi | | Los Angeles, San Francisco, Seattle | 400 km |
| Hartford | 297 km, 184 mi | | Denver, Phoenix, Des Moines | 400 km |
| Asheville | 299 km, 185 mi | | Burlington VT, Acadia | 400 km |
| Pittsburgh | 317 km, 197 mi | | Ely NV, Billings MT, Moab UT, Amarillo TX | 400 km |
| Charlotte, Atlanta | 319–321 km | | | |
| Chicago | 329 km, 204 mi | | | |
| Dallas | 346 km, 214 mi | | | |

Of 2,000 random US junctions (so weighted toward where roads are dense), half
keep 400 km. The 10th percentile is 296 km and the lowest 243 km. New
England's whole graph holds 0.8M nodes, so every start on `processed-ne` keeps
400 km.

`nearest_length`, the "nearest loop from here" hint, now searches only up to
the start's limit. It used to build the passes of a 400 km loop whatever the
start, which from Philadelphia are most of that 13–20 s.

`tools/us_scale_router/load_probe.py` now asks `/api/loop/limit` before each
loop and keeps the loop's length under it, as the app will.

## 6. Instruction text

Three rules, all in `RouteResult`'s step generation, so nothing needs a
rebuild:

- **The first value of a multi-value tag.** `name` and `ref` are read through
  `_first_value`: "I 295;US 1;ME 26" is announced "I 295", and "Acquoni
  Road;ᎡᏆᏂ ᎦᏅᏅ" "Acquoni Road". The spelling stays OSM's ("I 295", not
  "I-295"), because the app's voice rewriting matches a network, a space and a
  number (`ios/Sources/VoiceGuide.swift`). Because two edges now share a label
  when only the tail of a multi-value differed, they merge into one leg. That
  drops a "Continue onto I 95;US 1" from the middle of I 95.
- **Exits.** A ramp with no exit number and no destination now names the road
  it joins as its sign does:
  - by route number when the joined road has one, even if OSM names the road
    ("Take the exit onto I 44 East", not "onto Will Rogers Expressway"); the
    step's `name` keeps the road's name, for the app's street readout;
  - with the direction that carriageway is signed in, read off its first 2 km.
    That is by parity for one- and two-digit Interstate and US routes, and
    otherwise the nearer compass point (three-digit routes such as US 220 run
    any way).

  A ramp serving several exits reads "Take exit 7A or 7B", with `exit_ref`
  "7A/7B".
- **Nameless roads.** A turn, fork, merge or U-turn onto a road with no name
  says where it leads, "toward" the first named road within 1 km. Failing
  that, it says what kind of road it is ("onto a service road", "onto the
  highway", "onto an unnamed road"). A bare "Continue" onto a nameless road is
  folded into the step before, since it neither names a road nor asks for
  anything. `name` stays empty for those steps, so the app's current-street
  readout still shows nothing for a nameless road.

`tools/us_scale_router/step_census.py` counts the defects in the same 40
random US trips (seeded, 20–400 km apart, at pref 0 and 0.5), on each
checkout:

| | `usa` | this branch |
|---|---:|---:|
| steps | 4,989 | 4,826 |
| a raw multi-value | 280 (5.6%) | 0 |
| an exit onto a road with no number, destination or direction | 113 (2.3%) | 12 (0.2%) |
| no road name at all | 134 (2.7%) | 0 |

The review counted 5.2%, 2.9% and 1.8% on its own forty trips. The 12 exits
left all join named streets with no route number ("Take the exit onto
Stetson Hills Boulevard"), which says where the ramp goes. One step in 4,826
is a bare "Take the exit": a ramp with no number, no destination and no named
road after it.

Tests: `TestInstructionText` in `tests/test_routing.py`. Each case uses a
literal expected sentence. Mutating `_first_value` to return the raw tag, the
direction to nothing, and the fold to off fails 9 of them.

## 7. Messages

- The 500 km cap reads **310 miles** (rounded down; it said 311). The reroute
  cap reads 403.
- Every refusal is a sentence with a code (tables above). "no route found
  between those points" became `NO_ROUTE_NEARBY`: "Sunday Drive couldn't find a
  drivable route between those points. One of them may be on a road cut off
  from the rest."
- `server/serve.py` no longer mentions Docker, which unit P removed.
- "no loop of that length from there" became `NO_LOOP`. Its hint is in miles,
  as the app shows distances, and `nearest_km` carries the number.

## New England parity

`tools/us_scale_router/parity_run.py` wrote the oracle's answers from the
`usa` checkout (`4f74951`) on `data/processed-ne`, and replayed the same 702
requests through this branch. `parity_diff.py` compared them.

| | requests |
|---|---:|
| identical JSON | 137 |
| refused by the 500 km cap on both, only the sentence changed ("311" → "310 miles") | 32 |
| the same lines, differing only in step text | 533 |
| a different line, status or anything else | **0** |

All 3,000 snaps (nearer end, with a heading, and as a destination) are
identical.

Every changed step was classified mechanically (counted per route feature, so
one route asked several ways counts several times):

| rule | steps |
|---|---:|
| a multi-value's tail merged away ("Continue onto I 95;US 1" after I 95) | 939 |
| a nameless road described ("Keep right" → "Keep right toward Centre Street") | 639 |
| a multi-value cut to its first value | 503 + 91 in `name` only |
| an exit by route number ("onto Maine Turnpike" → "onto I 95 North", "onto Post Road" → "onto US 1 South") | 423 |
| an exit's direction ("onto CT 8" → "onto CT 8 South") | 77, and 34 with a multi-value |
| a bare "Continue" folded | 71 |
| a multi-valued exit number ("7A;7B" → "7A or 7B") | 25 |
| the same road, now said so ("Keep left to stay on I 95") | 2 |

158 route features did not fit one rule step for step. Every one of them
contains a multi-value in the oracle's steps, and covers the same total
distance. When a multi-value's legs merge, the short-leg folding lands on
different steps. On Maine's I 295 the oracle had "Continue onto Tukey's
Bridge" covering 5,529 m, most of it I 295, because a 66 m "I 295;US 1;ME 26"
leg had folded into it. The branch says the bridge for 153 m, then I 295.

So no new difference is a route.

**With the lead-in**, the same replay against the run before it:
- **From rest:** all 579 requests are byte-identical.
- **Moving:** all 123 return 200.
  - **Lines:** 210 route features are the same line with a lead-in in front;
    36 are unchanged (the car was at its junction).
  - **First steps:** 140 keep their words, start at the car and cover the
    lead-in. 31 change only their compass word, because the departure is now
    measured over the lead-in. 39 gain a lead-in step before what used to be
    the first maneuver: 9 unchanged after it, 30 reworded after it, as in
    "Make a U-turn on Fellsway" → "Head south on Fellsway", "Make a U-turn to
    stay on Fellsway".
  - **The rest:** no total fell, and `turns_around` is unchanged in all 123.

## The suite

`SUNDAYDRIVE_DATA=…/data/processed-ne .venv/bin/python -m pytest tests/`:
**1,059 passed, 13 skipped, 0 failed**. On `usa` the count was 987 passed, 13
skipped.

New tests:
- `tests/test_closed_roads.py`: the moving-car snaps (section 1).
- `tests/test_routing.py`:
  - `TestNoRouteNearby`: the corridor schedule as literals, and a search that
    finds nothing widens exactly that far;
  - `TestInstructionText`.
- `tests/test_api.py`: the contract, and the lead-in (section 1).
  - Every refusal is checked for status, code, a sentence, and numbers that
    are numbers.
  - `BAD_INPUT` on 21 malformed requests, including every case the review
    found.
  - The 310-mile sentence, and `LEG_TOO_LONG` on either leg.
  - `START_TOO_FAR` wiring.
  - The loop limit: POST only; numbers; `LOOP_TOO_LONG` over it; the slider's
    top accepted; the limit as the longest disc under the threshold at three
    thresholds.
  - Health's fields, the commit's two sources, and the pack fingerprint.
  - `NO_ROUTE_NEARBY` and `CLOSED_FOR_SEASON` bodies.

Changed tests, each because the contract changed what it pinned:
- `test_weights_are_clamped_not_rejected` loses `w_coast=1e999`, which is now
  refused, in a test of its own.
- `test_the_distance_is_clamped_not_rejected` becomes "raised to the bottom
  and refused over the top": km=9999 is `LOOP_TOO_LONG`, with `max_km` 400.
- `tests/test_loop_lock.py`: the busy body now carries `"code": "BUSY"`.

`tests/test_closures.py` is unit D's and is untouched; it passes because
`server.CLOSED_FOR_SEASON` still names the sentence.

## Latency and memory under load

`tools/us_scale_router/load_probe.py` on `data/pack-us`: the real server, four
clients, a mixed workload drawn across the country. Each loop now first asks
`/api/loop/limit` and stays under it. Three replicates of 120 s, each a fresh
server, on this Mac with load about 4 and swap at 6.5 of 8 GB:

| | replicate 1 | 2 | 3 |
|---|---:|---:|---:|
| start to ready | 2.0 s | 2.0 s | 2.0 s |
| footprint after load | 3.16 GB | 3.15 GB | 3.15 GB |
| **peak footprint under load** | **3.95 GB** | **4.04 GB** | **4.70 GB** |
| peak RSS, pack pages included | 9.33 GB | 10.29 GB | 9.14 GB |
| requests answered | 273 | 275 | 224 |
| routes, plans with options, reroutes failed | 0 | 1 (`START_TOO_FAR`) | 0 |
| loops refused as busy (503, by design) | 11 | 13 | 11 |
| loop limit, p50 / p90 wall | 11 / 41 ms | 6 / 60 ms | 9 / 55 ms |
| routes, p50 / p90 wall | 1.5 / 4.0 s | 1.5 / 3.3 s | 1.8 / 4.2 s |
| loops, p50 / p90 wall | 2.9 / 7.7 s | 2.1 / 11.4 s | 3.6 / 13.8 s |

With four clients firing back to back every request queues for the GIL, so
these are saturation numbers, not a forecast. The peak footprint is within
the 4.1–4.8 GB `docs/router-at-us-scale.md` measured for `usa` (180 s runs,
a busier Mac). Nothing here needs more memory.

## What is left

1. **Unit I** verified the lead-in with no app change: on I-10 the line starts
   0 m from the car, with no off-line fixes. The committed-carriageway rule
   uses the same lead-in shape, longer.
2. **Merging with unit D.** The ford change removes the I-10 and CA-1 cases
   from the data. Nothing here depends on it. Andrew Molera to Big Sur should
   then be the 4-mile road, worth one check on `pack-us-next`.
3. **Unit I** also decodes the codes above, including the six beyond the agreed
   seven (`CLOSED_FOR_SEASON`, `SAME_ROAD`, `NO_LOOP`, `BUSY`, `NOT_FOUND`,
   `SERVER_ERROR`). It also takes `max_mi` for the slider and reads `exit_ref`
   as possibly "7A/7B".
4. **Unit P's** deploy reads `commit`, `pack` and `region` as agreed.
5. **On the box:** every latency here is this Mac's. The loop threshold
   assumes the box is 1.4 times slower, as measured for today's router; a
   first loop at the limit should be checked there after deploying.
6. **Not changed:** the pack format, `common.py`, `closures.py`, `ios/` and the
   deploy files.
