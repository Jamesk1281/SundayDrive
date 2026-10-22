# How much risk to take on roads that are sometimes closed

**Status:** the mechanism is diagnosed; nothing is measured, decided or
changed. Written 2026-10-21 by the master session against `usa` at `de43cb4`.
This is a **study that ends in a recommended policy**. It does not change
routing. The owner makes the final call from your verdict, and a separate
build follows. Your answer goes in **`docs/seasonal-road-risk-verdict.md`**,
never in this brief, which is deleted in the merge that brings the work back.

## The question, as the owner put it

> Is it worth just making them completely off limits? Or do we take the risk of
> routing someone, who may already be in the middle of nowhere, to a closed
> road, and cause that frustration?

"Them" means roads that are open some of the time: seasonal passes, gated
park and forest roads, and roads with part-time rules. The trade is
**scenery lost by avoiding them** against **the cost to a driver who reaches
one that is shut**. The answer is a policy and its parameters, chosen from
measured numbers on both sides.

## What the router does today (the mechanism)

1. **In window: closed absolutely. Out of window: open with no penalty.** There
   is nothing in between.
   - `seasonal_closures.parquet` gives each edge a dated window.
   - `_weights` adds `+inf` to an edge whose window contains today
     (`pipeline/router.py:2775-2779`; the rule is stated at `router.py:488-492`:
     "Closed means unusable").
   - Outside the window the edge costs what any road costs.
2. **"Today" comes from the clock, judged leniently toward closed.**
   `region_today()` (`router.py:510`) checks every date the contiguous US is on
   at that moment. `_today()` (`server/app.py:404`) is the hook the tests
   replace.
3. **The windows are a mix of precise and guessed:**
   - OSM `*:conditional` dates are used as tagged.
   - Undated `winter`/`snow`, `winter_service=no` and `seasonal=*` tags get
     the default `WINTER = (11, 1, 4, 30)` (`pipeline/closures.py:104`).
   - Seasonal roads with no readable dates get
     `UNKNOWN_SEASON = (10, 1, 6, 30)` (`pipeline/winter_closures.py:76`).
   - Hand-table roads (`pipeline/winter_windows.json`) use the **longest
     closure the operator published in ten seasons**
     (`docs/winter-closures-national.md`, decision 3). That rule closes Lassen
     until Jul 25, though it opened May 22 in 2026.
   - **There is no live status at all.** Snow events, washouts, construction
     and early or late openings are invisible.
4. **When the only way is closed**, the request fails with HTTP 404
   `CLOSED_FOR_SEASON`, "The only way there is closed for the season."
   (`server/app.py:149`, `:193`, returned at `:689`, `:736` and `:759`).
5. **Mid-drive, the router has no memory of a road the driver found shut.**
   There is no avoid-this-road parameter: the only `avoid` in `server/app.py`
   is `avoid_unpaved`. A driver who reaches a closed gate and turns round
   triggers a reroute from a fresh request. That request knows only the
   position, the heading and possibly `declined_uturn`
   (`server/app.py:448-457`, `docs/reroute-uturn.md`).
   - **Hypothesis:** the reroute keeps sending them back toward the same
     closed road until they are far enough away that another way is cheaper.
   - **Evidence:** nothing in the request can rule that road out.
   - **What would kill it:** a reroute from just past the turnaround that
     already avoids the road. That could happen if `declined_uturn` keep-ahead
     plus distance happens to make another way cheaper. Measure it (Q3).
6. **The app's only word on it** is the "Signs come first." item in
   `ios/Sources/BeforeYouDriveView.swift:95-97`. Nothing at planning time says
   that a route uses a road which closes, or recently opened, near today's
   date.

The size of what's at stake, from `docs/review-fixes-data.md`: nationally,
`seasonal_closures` is 1,765 rows, 1,290 edges and 1,902.5 km. In New
England (`docs/seasonal-closures.md`) the seasonal roads score 6.14 on
average, with 43.2% of km at 7 or more. That is far above the graph average.
These are the roads the app exists for: Beartooth, Going-to-the-Sun, Tioga,
Trail Ridge (opened by a parallel unit, see "Collisions"), VT-108 Smugglers'
Notch, Lincoln Gap and the Mount Washington Auto Road.

## What to measure

**Q1. What banning them costs.** For a fixed random trip sample, measured
in June, August and October:
- the share of served routes and loops that use any seasonal edge;
- the scenery they would lose (score and scenic km) if every seasonal edge
  were closed all year;
- the trips that fail outright;
- New England and national reported separately, with the ten best-known roads
  above named individually.

The sample should be the one `tools/national_audit` or
`tools/national_build/ne_trip_pairs.json` already uses, or a stated random
draw. Simulate a ban by handing the router an all-year copy of the table in
scratch, not by editing code.

**Q2. How often "open" is wrong, by window type.** For a sample of at least
15 roads across the four window sources (OSM dated, default `WINTER`,
`UNKNOWN_SEASON` and the hand table), find published actual opening and
closing dates for recent seasons:
- state DOT press releases, NPS road status archives, park pages;
- record each date with its source URL and read date.

Report how far our windows miss, in days, at each end. Split the misses into
**open when actually shut**, which is the dangerous one, and **shut when
actually open**. If a source can't be found for a road, say so; don't
estimate it.

**Q3. What a wrong "open" costs the driver.** For each road in Q2's sample
and for the top seasonal edges by route usage from Q1, put the driver at the
closed end:
- the gate node or the window's first edge, arriving the way the route
  arrived;
- turn them round and replay the reroutes the app would make, through the
  server's own `_route` with heading and `declined_uturn`, against the
  pack, at one or two points as they drive away.

Record:
- (a) whether each reroute sends them back into the closed road;
- (b) the extra minutes and km to the destination versus the planned route;
- (c) the distance from the closure to the nearest other road that reaches
  the destination: the "middle of nowhere" number.

This also settles the hypothesis in mechanism item 5.

**Q4. The policies, each measured on Q1–Q3:**
- **P0, today:** hard closed in window, free outside.
- **P1, ban:** closed all year.
- **P2, shoulder margin:** closed N days either side of the window. Try N =
  7, 14, 21 and 30, and also separately per window source, since the guessed
  windows deserve wider margins than published dates.
- **P3, risk price:** open outside the window, but with a cost that grows
  toward the window and with the detour from Q3(b). Describe it; the
  numbers can be computed offline without changing `router.py`.
- **P4, say it at planning:** P0 or P2 plus a notice on routes that use a
  road within M days of its window, with the faster alternative one tap away.
  This is app copy, measured only by how many routes would show it.
- **P5, remember the road mid-drive:** an avoid-edges parameter, or a
  "road closed" control, so the reroute rules out the road the driver turned
  away from. Measure it by re-running Q3 with that road closed for the
  reroute.

The policies combine. The likely answer is a combination.

## The decision rule to apply

Recommend the combination that minimises **expected stranded minutes per
1,000 trips**, computed as the sum over seasonal edges used of
P(shut while we say open, from Q2) × detour minutes (from Q3). It must keep
at least 90% of the scenery that P0 serves on the seasonal roads in their
open months (from Q1). If two combinations are within 20% of each other on
stranded minutes, prefer the one with no new app UI, because the app ships
soon and is small. Show the frontier as a table or chart so the owner can
move the 90% bar, and say which choice you'd make at 80% and at 95%.

## Traps

1. **Don't change routing code or the live data.** This is a study. A ban or
   margin is simulated with a modified copy of `seasonal_closures.parquet` in
   scratch, loaded by a router pointed at it, or with `_today()` shifted by N
   days (`server/app.py:404`, the tests' hook). Never write `data/processed-us`
   or `data/pack-us`: they are what the next deploy ships. The parallel unit
   (below) is editing `pipeline/closures.py`, `common.py` and
   `winter_closures.py`. Don't touch them either.
2. **Never evaluate on the real date.** Today is late October, so half the
   passes are already shut and Q1 comes out at the wrong scale. Every
   measurement names its date. Use June, August and October at minimum, and
   the shoulder dates of each sampled road for Q3.
3. **A ban looks cheap if you count routes.** Most trips touch no seasonal
   road, so "0.4% of routes change" hides that the app's best drives vanish
   all summer. Weight by scenery and name the roads (Q1).
4. **A "closed" gate in the data is not where the driver is stopped.** The
   gate may be at the far end of a long dead-end approach. Q3's turnaround
   point is where the closure physically sits: the gate node (`node_id` /
   `at_m` in the table) or the window's first edge. It is not the nearest
   junction.
5. **The hand table's ten-season rule is already biased toward closed.**
   Don't add a margin on top without measuring that bias (Q2). Applied
   uniformly, a margin double-counts it.
6. **The Mac is shared.** A parallel session is rebuilding the national
   sidecars and pack (about 3 GB+ resident). If memory is tight, run Q3's
   reroutes on `data/processed-ne` for New England roads, and on the national
   pack only for the western ones, one at a time. Kill only processes you
   started, by PID. Never run a broad `pkill`.

## Collisions

Chip `task_b97d53c1` (branch off `usa`, "Carry out six national data
decisions") is changing `pipeline/common.py`, `pipeline/closures.py`,
`pipeline/winter_closures.py` and `pipeline/federal_layers.py`, and building
`data/processed-us-next` / `data/pack-us-next`. That work:
- opens Trail Ridge Road outside its winter window (it is closed all year
  today by a permit rule): treat it as open in season here;
- closes about 4,849 mi of forest road that MVUM designates for no car.

Read only. Put your code in `tools/seasonal_risk/` and your doc in `docs/`.

## Done looks like

1. `docs/seasonal-road-risk-verdict.md` containing:
   - the Q1–Q4 numbers, with dates, samples and sources;
   - the Q2 table with a URL for every date;
   - the answer to mechanism item 5's hypothesis;
   - the frontier;
   - **a recommended policy** with its parameters: margins per window source,
     whether P4 and P5 are worth it, and what a build would touch.
2. `tools/seasonal_risk/` with the scripts and the result CSVs, rerunnable.
3. No change under `pipeline/`, `server/`, `ios/` or `data/`.
4. This brief committed with the work, with nothing appended to it.
5. An honest escape hatch: if Q2 can't find enough published dates to
   estimate the probability for a window source, say so. Recommend for that
   source on the stranding cost alone, and label it as such.
