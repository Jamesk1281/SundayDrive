# The snap cap: a far point is refused in a few squares, not a continent

**Status:** built 2026-10-24 on `claude/snap-cap-d6e859`, off `usa` at
`936dfcf`. Not merged, not deployed. The dispatch brief,
`docs/snap-cap-brief.md`, is committed with this work and deleted when it
merges. This document is what outlives it. Code comments and tests cite it,
and they cite its section names.

## Result

The defect, from outside review #4: one unauthenticated request from 400 km
off the Atlantic coast held a waitress thread for 94-618 s on the national
server, and four of them delayed an ordinary route by about three minutes.
The cause was `LineIndex.nearest`, which widened its square fourfold until it
found a road, before the server ever asked whether the road was within 5 km.

Now every request's point is searched only out to 5 km, and refused there:

- **Parity:** 20,865 of 20,865 sampled points snap identically on New
  England (old code run on every one), 5,014 of 5,014 nationally.
- **Fuzz:** all 138 requests (23 points, each as a route's from, to and
  via, a reroute's from, `/api/loop` and `/api/loop/limit`) gave their correct answer on the
  national server, the slowest in 14 ms. The old code took 5-14 s on a point
  100 km off New Jersey, and up to 1.8 s on the antimeridian.
- **Under load:** with four offshore requests in flight, Denver to Estes
  Park planned in 0.26 s (0.34 s alone); each offshore request took 4 ms.
- **Health:** `/api/health/route` plans Concord to Lexington, MA in 0.33 s
  and answers from its 60 s cache in under 1 ms.
- **Suites:** `tests/` on `data/processed-ne` 1,346 passed, 14 skipped;
  `tests/test_national_routes.py` on the national pack 11 passed;
  `tests/test_snap_cap.py` 37 passed, none skipped.

## What changed

**One constant**: `SNAP_MAX_M = 5000.0` now lives in `pipeline/router.py`.
`server/app.py` imports it. The local copy in app.py is gone.

**`LineIndex.nearest(point, limit=None)`.** The acceptance rule is untouched:
a line is accepted once it lies no further than the square's half-width
(`d[k] <= reach`), which is what makes the answer exact. Two things are new,
and both happen only when a limit is given:

- **A cut-off.** Once the half-width has reached the limit and nothing lies
  within it, return None instead of widening.
- **A clamp.** The half-width never grows past the limit, so the last square
  is exactly 5 km: 250 m, 1 km, 4 km, 5 km, at most four squares.
  - The clamp cannot change an answer. Any line the search accepts is the
    nearest in the whole index, because it lies inside a square that holds
    every line that close.
  - The old code went from 4 km to 16 km, measuring 16 times the area to
    find the same line. Within reach the new code measures fewer lines for
    the same answer: see the parity table.
- **A point off the projection** (the south pole projects to infinity) is
  None at once. Before, it raised inside `Grid.box`, which made a 500.

**`LineIndex._candidates`** now reads a square across the antimeridian as two
boxes, not one band round the earth. See "The antimeridian".

**`OutOfReach(ValueError)`.** `_snap` raises it when the edge search comes back
None. "Outside" is an exception, not a return value, because every caller of
`snap` takes an `int` back (the brief's Trap 4). Only callers that pass a
`limit` can see it, and only `server/app.py` passes one.

**The limit is threaded through** `snap`, `snap_start`, `snap_lead`, `_snap`,
`snap_destination` and `access_point`. That bounds all three of a
destination's searches (Trap 3):

1. The pin's road, through `_snap`.
2. The nearest service way and the nearest road again, inside
   `access_point`. Either one beyond the limit makes `access_point` None.
   A service way beyond the limit is never nearer than a road within it, so
   the answer is otherwise unchanged.
3. The entrance's road, which is `_snap` again, from the car park's entrance.
   This search is not bounded by the limit itself. See "The entrance trap".

**`server/app.py`.** Every snap that a request reaches passes
`limit=SNAP_MAX_M` and turns `OutOfReach` into the same `OUTSIDE_COVERAGE`
refusal it already gave:

- `from`, through `snap_lead`;
- `to`, through `snap_destination`;
- `via`, through `snap`;
- `/api/loop` and `/api/loop/limit`, through `snap`.

The existing `> SNAP_MAX_M` checks on the offsets stay. A line inside the
first square is accepted whatever the limit, so the check is still the rule
for what counts as outside. The cap only makes reaching that decision cheap.

No bounding box or coverage polygon was added (Trap 1). The fuzz set includes
points inside the contiguous US's box (the Gulf, Lake Michigan, Great Salt
Lake, the Black Rock playa), and the cap alone refuses them in milliseconds.

## The entrance trap

The first full parity run found **21 of 20,865** New England points where the
bounded code refused a pin the old code had snapped. In every one, the pin was
3.1-4.99 km from a road and inside a mapped car park. The park's entrance,
which the destination snaps from, was 5.2-9.2 km from the nearest road the
snap index holds. These are island parks: Martha's Vineyard, Mount Desert,
Casco Bay and the Rangeley lakes. With the entrance's own search bounded at
5 km, `snap_destination` raised `OutOfReach` for a pin that was in reach.

The entrance is a mapped node, not the request's point, so the attacker
cannot choose where it lies. That search is now bounded by the limit plus
the pin's distance to the entrance, plus 1 m for rounding. By the triangle
inequality, that distance always contains the road the pin found, so the
same road is found.
`tests/test_snap_cap.py::test_an_island_car_park_entrance_beyond_the_limit_still_snaps`
pins it, on a Mount Desert pin 4.93 km off whose entrance is 6.7 km from a
road. With the bound put back to `limit`, the test fails.

## Parity: in-reach snaps are unchanged

`tools/snap_cap/parity.py` loads `pipeline/router.py` as it was at `936dfcf`
(read from git) and binds the old snapping methods onto the same loaded
router. Old and new then answer from one graph in one process. Each sampled
point is snapped every way:

- the nearest road and the nearest service way;
- `snap`;
- `snap_lead` at rest, moving with a heading, and moving with none (a
  declined U-turn);
- `snap_destination`.

Within reach every answer must be identical: the same line (so the same tie
rule), node, offset, gap and lead-in. The bounded service-way search must give
the old way wherever that way was within 5 km, and None otherwise.

Beyond reach, the new code must refuse. That is checked without the old code:
no line of `query(point.buffer(5000))` may lie within 5 km. On New England
the old code also runs there (`--old-beyond`), and its offsets must be beyond
5 km too, so the server refused those points before as well.

Run 2026-10-24/25 on this Mac. "old ran" counts the points the old code was
run on; "lines/pt" is lines measured per point, mean over the point's
snaps.

**New England** (`data/processed-ne`, `--n 4000 --old-beyond`, 2.6 h):
**20,865 of 20,865 points identical.**

| kind / reach | points | same | old ran | lines/pt old | lines/pt new |
| --- | ---: | ---: | ---: | ---: | ---: |
| at_limit / in | 448 | 448 | 448 | 89,259 | 3,520 |
| at_limit / out | 417 | 417 | 417 | 85,196 | 2,327 |
| bbox / in | 1,867 | 1,867 | 1,867 | 1,186 | 509 |
| bbox / out | 2,133 | 2,133 | 2,133 | 1,329,229 | 9 |
| car_park / in | 3,982 | 3,982 | 3,982 | 1,017 | 1,009 |
| car_park / out | 18 | 18 | 18 | 483,717 | 86 |
| far / in | 4,000 | 4,000 | 4,000 | 10,099 | 5,479 |
| mid_block / in | 4,000 | 4,000 | 4,000 | 1,191 | 1,191 |
| on_road / in | 4,000 | 4,000 | 4,000 | 1,133 | 1,133 |

The first run of this, before the entrance fix, gave 20,844 of 20,865: all
21 misses were `snap_destination` on island car parks, the entrance trap
above. The 20 it logged were rechecked after the fix and matched, and the
re-run above is the whole sample again.

**National** (`data/pack-us` + `data/processed-us`, `--n 1000 --max-tries
60000`; the old code is not run beyond reach, see above):
**5,014 of 5,014 points identical.**

| kind / reach | points | same | old ran | lines/pt old | lines/pt new |
| --- | ---: | ---: | ---: | ---: | ---: |
| at_limit / in | 6 | 6 | 6 | 475,055 | 27,145 |
| at_limit / out | 8 | 8 | 0 | - | 12,055 |
| bbox / in | 559 | 559 | 559 | 1,450 | 451 |
| bbox / out | 441 | 441 | 0 | - | 12 |
| car_park / in | 998 | 998 | 998 | 1,477 | 1,477 |
| car_park / out | 2 | 2 | 0 | - | 26 |
| far / in | 1,000 | 1,000 | 1,000 | 11,161 | 7,612 |
| mid_block / in | 1,000 | 1,000 | 1,000 | 1,509 | 1,509 |
| on_road / in | 1,000 | 1,000 | 1,000 | 1,357 | 1,352 |

Both runs predate the antimeridian change to `_candidates`, which can only
take effect for a square whose corners lie both sides of 180 degrees, so for
no point within 5 km of a US or New England road. The tests covering it ran
on the final code.

## Timings: old code against new, national server

Measured 2026-10-24 on this Mac, one national server at a time on port 55611
(`data/pack-us` + `data/processed-us`, 20,023,955 nodes), with
`tools/snap_cap/fuzz_live.py`. The old code is `pipeline/` and `server/` at
`936dfcf`, run from a scratch copy. The NE parity run was going in another
process throughout, on one core.

**The old-code baseline.** The 400 km point was not re-run on the old code,
as the brief's Trap 5 requires. The review's own figures for it stand:
100.2 s and 94.2 s, and 618 s from a cold page cache.

The review did not record its "about 10 km offshore" coordinates. The ones
used here were cheap on the old code too, because what costs is not the
distance offshore. The old search widened from a 4 km square straight to a
16 km one, then to 64 km. A point is cheap whenever that widening finds a
road before the square grows past a few tens of kilometres. It stalls only
when it has to reach a whole region. The 100 km point is the smallest case
of the stall measured here:

| point | placement | old code | new code |
| --- | --- | --- | --- |
| 10 km off New Jersey, 39.75,-73.93 | route from | 0.032 s | 0.011 s |
| | route to | 0.015 s | 0.012 s |
| | loop | 0.002 s | 0.001 s |
| 30 km off New Jersey, 39.75,-73.65 | route from | 0.273 s | 0.001 s |
| 10 km into the Gulf, 30.08,-85.85 | route from | 0.073 s | 0.001 s |
| 10 km off Oregon, 44.6,-124.2 | route from | 0.041 s | 0.001 s |
| Great Salt Lake, 41.1,-112.6 | route from | 0.413 s | 0.001 s |
| Black Rock playa, 40.85,-119.10 | route from | 0.010 s | 0.002 s |
| **100 km off New Jersey, 39.4,-73.2** | route from | **5.06 s** | 0.001 s |
| | route to (three searches) | **13.57 s** | 0.003 s |
| | loop | **4.36 s** | 0.001 s |
| 400 km off the Atlantic, 36.46994,-70.93004 | route from | 94-618 s (review) | 0.001 s |

On the old code, RSS went from 3.78 GB to 4.34 GB over the two 100 km
requests.

**The new code, the whole fuzz set.**

- **The points:** 23 of them.
  - 10 km, 30 km, 100 km and 400 km off the Atlantic coast;
  - 10 km and 400 km into the Gulf and the Pacific;
  - mid Lake Michigan, Great Salt Lake, the Black Rock playa, Hudson Bay
    and central Mexico;
  - 0,0, both poles, 89.9,-100, and 0,180 and 45,-180;
  - lat 91, lon -181, nan and inf.
- **The placements:** each point in each of six places a request takes one:
  route from, to, via, a reroute's from with a heading, `/api/loop` and
  `/api/loop/limit`. That is 138 requests.
- **The result: 138 of 138 gave the right code, the slowest in 0.014 s.**
  Points in range of nothing answer `400 OUTSIDE_COVERAGE`. Unreadable ones
  answer `400 BAD_INPUT`.

**Four at once.** Four 400 km offshore requests went in together, beside
Denver → Estes Park. The route answered in **0.26 s** (0.34 s alone), and
each offshore request in 0.004 s. In the review it took 176.8 s.

## The antimeridian

The first fuzz run on the new code passed every point, but 45,-180 took
0.36-0.87 s where every other point took a few milliseconds. Timed at denser
latitudes, it was **1.69 s** from 40.75,-180 and **1.83 s** from 34.05,-180:
bounded, but not "well under 1 s".

The cause is the step that turns a square in metres into a box in degrees.
A square across ±180° has corners at both -180 and +180, so `min` and `max`
made it one band round the whole earth, a tenth of a degree tall. Every road
at that latitude in the country was then measured, four squares a search.

`LineIndex._candidates` now reads such a square as two boxes, one at each
edge of the map. That happens only when the corners span more than 180° and
all lie more than 90° from the prime meridian. No square around a point in
the contiguous US meets that test, so in-range answers cannot change. A
square around a pole fails the second test and keeps the single band, which
is correct there and has no roads in it.

After the fix, 40.75,-180, 34.05,-180 and 40.75,180 each answer in
0.001-0.004 s.
`tests/test_snap_cap.py::test_a_square_across_the_antimeridian_measures_no_roads`
measures zero lines at Boston's latitude. With the fix disabled, the test
fails.

## The health route

`GET /api/health/route` plans one fixed route the way `/api/route` does at the
app's defaults: Concord, MA to Lexington, MA, both arms, scenic bounding
fastest. The pair exists in both the New England and the national builds.
On the national build the plan took **0.33 s** (10.7 km). Cached answers
took under 1 ms.

| answer | status | body |
| --- | --- | --- |
| planned, within 5 s | 200 | `{"status": "route_ok", "route", "seconds", "limit_s": 5.0, "km", "age_s"}` |
| no route found | 503 | `{"status": "route_failed", "reason": "no route", ...}` |
| planned, but took over 5 s | 503 | `"reason": "slow: over 5 s"` |
| the plan raised | 503 | `"reason": "error: <ExceptionType>"`, logged with its traceback |
| a plan under way has run over 5 s | 503 | `"reason": "slow: a plan has run N s"` |
| no plan has finished yet | 503 | `"reason": "no plan finished yet"` |

The contract:

- **The keyword is `route_ok`.** No failure body contains it. It does not
  change with the region served.
- **At most one plan a minute** (`HEALTH_ROUTE_TTL_S = 60`). Calls inside the
  minute are answered from the cache, and `age_s` says how old the answer
  is. A scraper can make the server plan at most once a minute (Trap 6).
- **One plan at a time**, under its own lock (`HEALTH_ROUTE_LOCK`), and never
  the loop or rejoin lock. A caller that finds a plan under way is answered
  from the last plan. If there is no last plan yet, it waits for the one
  under way, but never more than 5 s after that plan began.
- **A stall shows.** The plan's caller waits for its own plan, so a stalled
  server makes that check time out. Every other caller gets a 503 once the
  plan has run 5 s. `/api/health`'s node count stays green through a stall,
  which is what outside review #4 measured.

The UptimeRobot steps are in `server/DEPLOY-oracle.md`, under "A second
monitor that plans a route". Setting up the monitor is the owner's job.

Tests (`tests/test_snap_cap.py`):

- the plan says `route_ok`;
- five calls make one plan, and an expired cache plans again;
- no route, slow, and raising each give a 503 without the keyword;
- two concurrent callers make one plan, which runs with neither the loop
  lock nor the rejoin lock held.

## Tests

`tests/test_snap_cap.py` runs on `processed-ne`. It asserts the work done,
never wall time: lines measured and squares searched, counted at
`LineIndex._candidates`.

- **Each fuzz point in each place a request takes one**
  - The places: route from, to, via, a reroute's from with a heading,
    `/api/loop` and `/api/loop/limit`.
  - Each must give `OUTSIDE_COVERAGE` within 100,000 lines and 24 squares.
  - A point that has a road within 5 km on the loaded build is skipped, not
    failed.
  - For scale: the densest square of New England, 10 km across around
    Cambridge, holds 24,595 roads and 13,697 service ways. Before the cap,
    the 400 km offshore point measured 1.3 million lines on this graph.
- **Unreadable input** (lat ±91, lon ±181, nan, inf) gives `BAD_INPUT` before
  any search: zero squares.
- **One bounded `nearest`** from 400 km offshore searches exactly four
  squares, and so does a refused `snap_destination`.
- **`snap` without a limit** still returns an int, however far off the point.
- **Bounded against unbounded** on about 200 in-reach points: the line, the
  service way, `snap`, a heading snap, a declined `snap_start` and
  `snap_destination`.
- **The entrance trap** and **the antimeridian**, above. Each test fails
  with its fix taken out.

**Suites, 2026-10-24, with the final code:**

- `SUNDAYDRIVE_DATA=data/processed-ne python -m pytest tests/`: **1,346
  passed, 14 skipped, 0 failed** in 5 min 23 s. The 37 tests in
  `tests/test_snap_cap.py` all ran; none was skipped.
- `SUNDAYDRIVE_PACK=data/pack-us python -m pytest
  tests/test_national_routes.py`: **11 passed** in 8 min 58 s.

Collecting from the repo root instead of `tests/` stops with a module-name
clash: `tools/winter_closures/test_graph.py` against `tests/test_graph.py`.
That clash is older than this work, and the README runs `pytest tests/`.

## Known failures and what is left

- **No other slow path turned up.** Apart from the antimeridian, now fixed,
  every one of the 138 fuzz requests answered in 14 ms or less on the
  national server. No per-request CPU deadline was added; it was out of scope.
- **The entrance search can reach past 5 km.** It is bounded by the
  pin's distance to its car park's entrance plus 5 km. That is a fact of the
  map, not of the request: the entrance is the nearest node the service
  network shares with the roads, so a caller cannot move it. The farthest
  seen in New England was 9.2 km.
- **The national at-limit band is thin.** Points 4.9-5.1 km from a road are
  rare on the national graph. The national run's capped sampling found 14
  (6 in reach, 8 beyond), against 865 in New England. The bounds are the
  same code on both graphs.
- **Those island car-park pins were not looked into.** They snap where they
  always did, to a road 5-9 km from their own entrance, and why the entrance
  is that far from any snappable road was not investigated. Island and ferry
  destinations were out of scope.
- **`OUTSIDE_COVERAGE` for the south pole** used to be a 500: the old code
  raised inside `Grid.box` on an infinite projection. It is now the same
  400 as every other point off the map.
- **The tools' own copies of 5 km** are listed below. They do not reach the
  server.
- **Deploying is the owner's job**, and so is the second UptimeRobot monitor
  (`server/DEPLOY-oracle.md`).

## Other callers keep the unbounded search

Tools, studies and the loop builder call `snap` with no limit, and keep the
old behaviour exactly: an int back however far off. That is safe because
their points come from the graph or the operator, never a request. Some
tools keep a copy of the 5 km constant:

- `tools/route_census.py`
- `tools/audit_directions.py`
- the scripts under `docs/route-options-study/`

They never reach the server, so they were left as they are. Pointing them at
`router.SNAP_MAX_M` is tidying, not a fix.
