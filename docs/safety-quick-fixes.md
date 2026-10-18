# Routing safety: the quick fixes, as built

**Status:** built 2026-10-18 on `claude/safety-quick-fixes`, off `main` at
`0fca74f`, and merged into `main` the same day. Not yet deployed. The rough-road
and TIGER rules were decided by the dispatching session before the build. The
brief that recorded them was deleted in the merge:
`git show 93cf704:docs/safety-quick-fixes-brief.md`. This document is what
outlives it. Code comments and tests cite
this file, and its section names.

The US map-data inventory (docs/us-map-data-findings.md, §4, §6.4–6.5, gaps
S1–S2) found that the router plans roads that are closed, or not passable in a
car. Four causes could be fixed in days from tags already in the OSM extract.
All four are fixed here:

1. **Dates** that `closures.py` could not read are read now: ordinal days, day
   first, and the German `Mai`.
2. **Gates** closed for the season by tags on the gate node now close in their
   window.
3. **Rough roads**, `4wd_only=yes` and `smoothness` of `very_bad` or worse, are
   closed to cars all year.
4. **TIGER's 4WD class**, `tiger:cfcc` A5x, counts as unpaved unless OSM's own
   surface says it is sealed.

The permit rule is untouched.

## Result, New England

Measured on 2026-10-18. `closures.py` ran on `data/raw/new-england-latest.osm.pbf`
against the deployed graph (`data/processed-ne`, 998,252 edges, 232,720 km). It
wrote into a scratch copy, never into `processed-ne`. "Before" is `main`'s
`closures.py` on the same inputs, and its two tables are byte-identical to the
deployed ones.

| rule | what it does in New England |
|---|---|
| dates | 0 km of way changes. **One gate** changes: Natural Turnpike's swing gate in Ripton, VT, `motor_vehicle:conditional=no @ (15 Dec-30 Apr)`, now closes its 318 m edge from Dec 15 to Apr 30 |
| gates | **9 gates** close for the season: 5 inside an edge, 4 between two edges. 5 of them change routing: they close 5.1 km of road and one through-movement in winter |
| rough roads | **49 ways, 59 edges, 30.8 km** closed all year. 57 edges and 29.1 km of that were open before |
| TIGER 4WD | **721 ways, 951 edges, 575.2 km** now count as unpaved. 102.3 km of public road and 52.6 km of private road were paved to the router before |

The router's startup lines, before and after:

```
before:
seasonal closures: 223 edges (182.2 km, 197 ways) in 7 windows; 0 gates, no driving through 0 of them in season
closed to cars: 3,271 edges (1693.9 km, 530 ways, 522 barriers and fords, 2,186 by state road class), and no driving through 108 more barriers; 3,101 junctions cut off behind them
unpaved by TIGER's 4WD class: none, osm_unpaved.parquet is missing, ...

after:
unpaved by TIGER's 4WD class: 951 edges (575.2 km, 721 ways)
seasonal closures: 227 edges (187.3 km, 197 ways) in 9 windows; 9 gates, no driving through 4 of them in season
closed to cars: 3,328 edges (1723.0 km, 579 ways, 522 barriers and fords, 2,186 by state road class), and no driving through 108 more barriers; 3,157 junctions cut off behind them
```

(The "before" lines are printed by this branch's router reading the old tables.
`main`'s router prints the same numbers without the new clause.)

**Exposure, on the closed-roads sample.** This replays docs/closed-roads.md's
design:
- 160 random origin-destination pairs and 160 random loop starts, seed
  20261005, drawn from `graph_nodes.parquet`;
- the server's defaults: a route at pref 0.5 and the fastest arm, a loop at
  40 km and pref 1.0, every weight 1.0, `avoid_unpaved` 1.0;
- each request snapped as `server/app.py` snaps it, and run in-process, on
  July 15 and on January 15, 2027.

| | before | after |
|---|---|---|
| requests answered | 960 of 960 | 960 of 960: **none now fails** |
| scenic routes on a newly closed rough road | one pair of 160, on both days (0.05 km) | **0** |
| loops and fastest routes on one | 0 | 0 |
| January requests on a newly gate-closed edge, or through New River Road's gate | 0 | 0 |
| responses that changed | | 2 of 960: that pair's scenic route, on both days, −0.1 min and −0.3 km |

The random sample barely meets these roads, because they are 0.0125% of the
graph's km. So each element was also driven directly ("Targeted exposure",
below).

**Targeted exposure.** Each trip below is planned where one of the new closures
or unpaved roads is: between the two ends of the element, both ways, on both
arms, plus a 40 km loop from its first end. Each end is snapped as the app
snaps it. Rough roads and A51 ran in July, gates in January.

| elements | before | after |
|---|---|---|
| 57 newly closed rough edges: 114 routes per arm | 100 drove the closed edge | **0**. 52 still route, none of them on it. The 46 of those that changed are a median +0.6 min and +0.4 km. In the other 62, both ends snap to the same open junction, which the app answers "too close together" (`s == t`). None is a "no route" |
| the same, 57 loops from their first end | 25 drove one; 39.9 km over the routes, 31.8 km over the loops | **0 km**. 57 of 57 loops still built, 35 changed, median −0.2 min |
| 5 gates that change routing, in January | all 5 driven through or along | none. Seboeis Road, +16 min round. Swift Brook Road, +93 min round. Katahdin Loop Road, Natural Turnpike and New River Road: no route, which the app answers "the only way there is closed for the season" |
| 80 random newly unpaved A51 edges | 156 of 160 routes drive them | 154. The trip is along that very road, and unpaved is a cost, not a closure. 2 of 80 loops changed |

**Snap keeps drivers off the newly closed roads.** At the midpoint of each of
the 57 newly closed rough edges, a start and a destination were snapped and
routed to and from Boston:
- before: 21 of 57 routes each way drove the closed edge they stood on;
- after: **0**, and 57 of 57 route each way;
- the snap moves the point a median 89 m, at most 1,883 m. The longest is the
  middle of Stuart Lane in Maine, a 6 km `smoothness=horrible` edge.

## Dates

`_dates` (pipeline/closures.py) rewrites three spellings into the month-first
form `_RANGE` reads, each as narrowly as it was seen:
- an ordinal suffix directly after a 1–2 digit day (`Oct 14th`);
- the German `Mai`, as a whole word only;
- a range written day first at both ends (`8 Dec - 1 May`).

Both the `no @` and `yes @` paths go through it.

| string (docs/us-map-data-findings.md §4) | window |
|---|---|
| `no @ Oct 14th - May 31st` (Trail Ridge Road, CO) | Oct 14 – May 31 |
| `no @ Nov 19th - May 30th` (CO) | Nov 19 – May 30 |
| `no@(Dec 1 - Mai 1)` | Dec 1 – May 1 |
| `no @ (8 Dec - 1 May)` (WA) | Dec 8 – May 1 |
| `no @ (15 Dec-30 Apr)` (Natural Turnpike's gate, VT) | Dec 15 – Apr 30 |

**The refusals are unchanged.** The year, weekday, time and vehicle checks run
on the raw rule before any rewriting. So `no @ (2024 Oct 14th-2025 May 31st)`
is still "dated", `no @ (Oct 14th-May 31st Mo-Fr)` is still "part-time", and
`Th` standing alone is still Thursday. A day that does not exist (`Oct 32nd`),
a word that merely begins "mai" (`maintenance`), and day-first at one end only
(`8 Dec - May 1`) are all still "unrecognized".

**New England:** 0 km of drivable way carries one of these spellings, as the
brief's scan found. The gate above is the only element in New England that the
date fix moves.

**Colorado: not measured.** No Colorado PBF is on this machine, and none was
downloaded. Trail Ridge Road's exact string is unit-tested to parse as
Oct 14 – May 31 (`TestDatesWrittenOtherWays`). Its window in a Colorado
`seasonal_closures.parquet` is still to be checked when a US build runs.

## Gates

`gate_windows` (pipeline/closures.py) reads a barrier node's car conditionals
through `conditional_windows`, with every refusal it makes. There is no second
parser. Three more rules:
- `yes @` closes outside its dates, as on a way.
- `customers @`, `permissive @` and the like close nothing.
- **A conditional never opens a barrier.** A node that `barrier_closes`
  already closes all year gets no seasonal row; its closed_to_cars row stands.

**Placement.** A seasonal gate is placed exactly as a barrier closed all year
is, by `_place_barriers`. That function is factored out of
`join_closed_to_cars`, which now uses it too.
- **Inside an edge:** the edge is closed in the window (`rule` "edge"). The
  `at_m` position is recorded, but nothing reads it yet. See "What is still
  open".
- **Where two edges meet:** neither edge closes. Driving *through* the gate
  closes in the window (`rule` "through", two rows). This is how VT-108 is
  gated below Smugglers' Notch: closing both edges would close the open road
  below the gate too.
- **At a dead end or a junction of three or more:** closes nothing, as for
  all-year barriers. New England has none.

**The router** splits a seasonal through-gate's junction all year, the way
`_split_through_barriers` splits an all-year one. Each approach gets a copy of
the junction, and each copy keeps every exit. The exits onto the far side are
priced +inf by `_closed_slots`, and only in the gate's window. On other days
they cost what driving on costs, so the split changes no route then. The closure
version, and every cache that keys on it, already covers the new windows,
because they are windows of the same table.

**New England's barrier conditionals.** 57 barrier nodes in the extract carry
some `:conditional` key, which is the brief's 57. 45 of them carry one for a
car key. **21 stand on drivable ways**, and `closures.py` reports what each came
to:

| outcome | gates |
|---|---|
| closed for the season | 9 |
| closes nothing: time of day (`no @ 20:00-07:00`, `no @ (Mo-Fr 17:00-07:00; Sa-Su)`, `no @ (sunset-sunrise)`) | 4 |
| closes nothing: part-time (`no @ (Dec-Mar Mo-Fr; ... dusk-dawn)`) | 1 |
| closes nothing: not `no @`/`yes @` with dates (`customers @ ...`, `yes @ (sunrise-sunset)`, ...) | 4 |
| already closed all year, left closed | 3 |

The 9 seasonal gates:

| gate | where it stands | window | effect |
|---|---|---|---|
| Katahdin Loop Road (ME), 2975174442 | inside a 2.9 km edge, 27 m from one end | Nov 1 – Apr 30 | **new**: closes 2.9 km |
| Seboeis Road (ME), 102017895 | inside a 1.4 km edge | Nov 1 – Apr 30 | **new**: closes 1.4 km |
| Swift Brook Road (ME), 9645841853 | inside a 0.5 km edge | Nov 1 – Apr 30 | **new**: closes 0.5 km |
| Natural Turnpike (VT), 7660919426 | inside a 0.3 km edge | Dec 15 – Apr 30 | **new**, via the date fix: closes 0.3 km |
| New River Road (ME), 10297054235 | between two edges | Nov 1 – Apr 30 | **new**: no driving through |
| VT-108 at Smugglers' Notch, 204656317 and 592642546 | between two edges | Nov 1 – Apr 30 | redundant: the way beyond is closed by its own tag |
| Cardigan Mountain Road (NH), 4586272784 | inside an edge | Nov 1 – Mar 31 | redundant: the way's own tag closes it Nov 1 – Apr 30 |
| Ossipee Park Road (NH), 194429974 | between two edges | `no @ winter` | redundant: both edges are NH Class VI, closed all year by state_road_class |

Three more gates would close for the season but stand on no drivable way, so
they add nothing:
- two tagged `yes @ (Jun-Aug)`;
- one tagged `no @ (December 16 - April 30)`.

## Rough roads

`too_rough` (pipeline/closures.py) closes a way tagged `4wd_only=yes` or
`smoothness` of `very_bad`, `horrible`, `very_horrible` or `impassable`. Such
a way gets a closed_to_cars row like a ford's, with `kind` "rough". From there
everything that handles closed ways handles it:
- the +inf mask;
- `snap` onto the nearest open road;
- the way round a closure.

`smoothness=bad` stays open. It covers 265.6 km of New England.

| tag | ways in the graph | edges | km |
|---|---|---|---|
| `smoothness=very_bad` | 32 | 37 | 17.0 |
| `smoothness=horrible` | 10 | 11 | 11.2 |
| `smoothness=very_horrible` | 5 | 7 | 1.2 |
| `4wd_only=yes` (McMurphy Road, NH) | 1 | 3 | 1.2 |
| `smoothness=impassable` | 1 | 1 | 0.2 |
| total | 49 | 59 | 30.8 |

These match the brief's scan: 17.1, 11.1, 1.2, 0.2 and 1.2 km. Of the
59 edges, 2 were already closed by other rules, so **57 edges and 29.1 km are
newly closed**. The largest are:
- Stuart Lane (ME), 6.0 km;
- Blodgett Road (VT), 2.4 km;
- Beartown State Forest Road (MA), 2.2 km;
- Messier Road (VT), 1.5 km;
- Depot Street (ME), 1.5 km.

## Unpaved

`tiger_unpaved` (pipeline/closures.py) counts a way as unpaved when every one of
its `tiger:cfcc` codes is A5x and its OSM `surface` is not sealed. `SEALED`
moved from `state_roads.py` to `common.py`, so one list serves both rules.

`closures.py` writes the result to its own table, `osm_unpaved.parquet`, never
to `state_road_class.parquet`: `state_roads.py` regenerates that file from DOT
data. The router reads it as `OsmUnpaved`, which refuses a table built against
another graph by the same u/v check the other tables have. `_state_unpaved`
sets those edges to all dirt, after the scenery score is settled, exactly as
it does Vermont Class 4. Nothing is closed for the class.

**New England:** 736 ways in the PBF; 721 in the graph, as 951 edges and
575.2 km. What that changes:

| of those 575.2 km | edges | km |
|---|---|---|
| already closed (OSM or state) | 133 | 83.6 |
| already unpaved by OSM `surface`, wholly or partly (119 edges only partly, now wholly) | 454 | 318.0 |
| already unpaved by state_road_class (VT Class 4) | 35 | 18.7 |
| **newly unpaved, public** | 250 | **102.3** |
| **newly unpaved, private** (start or end only) | 79 | 52.6 |

**Overlap with state_road_class**, as the brief asked, by edge: 211.1 km of
the 575.2 km carries a state row.
- closed: 72.4 km. NH Class VI 53.8, VT Class 4 impassable 11.5, VT trails 6.5,
  VT discontinued 0.5.
- private: 119.6 km. ME Local 48.5, ME Private 25.9, NH Class 0 23.6,
  VT private 21.6.
- unpaved: 19.1 km, VT Class 4.

**Left paved:** 210 drivable ways mention A5x and are not counted.
- 98 have a sealed surface: 90 `asphalt` and 8 `paved`.
- 112 mix A5x with another class (`A41;A51`, `A51;A41`, `A41:A51`,
  `A51;A74`, ...). These are ways joined from a 4WD trail and a road of
  another class, so which part is which is unknown. They are left to their
  surface (decision 3 below).

The brief's 711.6 km counted every drivable way carrying A51, mixed ones
included, and some outside the graph.

## The decisions made here

The brief settled what closes and what is unpaved. These are the calls made
while building it. Each can be overruled.

1. **A seasonal gate between two edges closes only driving through it**, in
   its window. This mirrors the all-year rule (docs/closed-roads.md, Trap 1),
   and it adds a dated through-movement to the router. Closing both edges
   would have closed each road up to the gate as well. At New River Road that
   is 340 m. At VT-108 it is the stretches below the two gates that the
   road's own tag leaves open, 121 m and 903 m.
2. **A seasonal gate inside an edge closes the whole edge** in its window.
   The seasonal table has no position-aware snap, so the road between the
   gate and the edge's near end is closed too. At Katahdin Loop Road the gate
   stands 27 m from one end of a 2.9 km edge, which closes up to 2.9 km of
   approach in winter. A destination there gets "closed for the season"
   rather than a route to the gate. This is the same behaviour as a way's own
   seasonal tag.
3. **A way whose `tiger:cfcc` mixes A5x with another class stays as its
   surface says.** That is 112 ways in New England. Counting them would mark
   paved stretches of other classes unpaved.
4. **`seasonal_closures.parquet` gains three columns**, `rule`, `node_id` and
   `at_m`, rather than a fourth table. A table without them still loads, as
   all "edge" rows.
5. **The rough rule's `kind` is "rough"**, beside "way", "ford", "barrier" and
   "state_class".

## What is still open

- **Colorado was not measured** ("Dates").
- **A position-aware seasonal snap.** With one, a destination between the
  near end of an edge and a seasonal gate inside it would route to the gate in
  winter instead of failing. It concerns 5.1 km in New England.
- **The permit rule**, which waits on the owner and is untouched here. Trail
  Ridge Road stays closed every day under it, so its new window shows in
  `seasonal_closures`, not in routing.
- **TIGER's other classes and `tracktype`** are still not read. Neither was in
  scope.

## The brief's traps, as handled

| trap | how |
|---|---|
| 1. Gate conditionals through the existing grammar, refusals kept; `yes @` closes outside; never open an all-year barrier | `gate_windows` calls `conditional_windows` via `_car_windows`, the same loop `way_windows` uses. Nothing is added for a node `barrier_closes` already closes. Tested for each refusal, for `yes @`, and for the chain, the `motor_vehicle=no` gate with `yes @ (May-Oct ...)`, and the logging checkpoints |
| 2. A51 is unreviewed: unpaved not closed, own sidecar, u/v check, nothing into state_road_class | `osm_unpaved.parquet`, `OsmUnpaved`, `_state_unpaved`. Sealed surfaces win |
| 3. Strip ordinals narrowly; day-first and `Mai` explicit; refusals not loosened | `_ORDINAL`, `_RANGE_DAY_FIRST`, `_MAI`, all applied after the refusal checks. Each brief string has a test |
| 4. No New England win for the date fix | 0 km of way. The one gate it moves is reported under "Gates" |
| 5. Exposure before and after, and the snap | "Result" and "Targeted exposure" |
| 6. Never write into `data/processed-ne` | All runs wrote into a scratch copy. Large inputs were symlinked; every file `closures.py` writes was a real file in scratch |

## Tests

**The suite**, against the New England build: **802 passed on `main`**
(`0fca74f`, deployed tables) and **903 passed on this branch** (new tables),
with none failing. That is 101 new tests in `tests/test_closures.py` and
`tests/test_closed_roads.py`: 91 that run anywhere and 10 that need the
build. Without the build, those two files run 260 tests and skip 73, saying
which file is missing; on `main` the figures are 169 and 63.

New tests:
- **Dates:** each brief string, plus New England's gate, plus ordinals in `yes @`. Every refusal still holds with ordinals present.
- **Gates:** `gate_windows`:
  - each New England seasonal form;
  - eleven refused forms;
  - five barriers closed all year that a conditional must not open;
  - non-car keys;
  - way and gate agreeing on the rule.
- **The gate join:** inside an edge, between two, dead end and junction, a row per window. A way and a gate on one edge keep both rows.
- **The loader:** through rows load, a gate whose rows don't meet at it is refused, and a pre-gate table still loads.
- **Rough roads:** each closing value, each open one (`bad` included), and the join's `kind`.
- **TIGER:** A51–A53 unpaved; every `SEALED` surface wins, in any case; mixed and other classes don't count; `OsmUnpaved` refuses a stale table; the router prints its line and applies the edges by row label.
- **On the build:**
  - New River Road: July drives through the gate, January doesn't, and the road up to the gate stays reachable;
  - Natural Turnpike: driven on Dec 14, closed on Dec 15, closed on Apr 30, open on May 1;
  - Beartown State Forest Road and McMurphy Road: no route drives them, with a control that does when their slots are reopened;
  - a point on Beartown snaps off it, both ways;
  - every `osm_unpaved` edge is dirt to the router, and closures.py closes nothing for TIGER.
- **The deploy script** ships `osm_unpaved` and echoes its line.

**Tests changed**, each because a gate between two edges is a row that closes
no edge, not because a claim changed:
- `test_closures.py::TestTheTable::test_the_router_loaded_all_of_it` counts only
  closing rows;
- `TestRoutes::test_closed_edges_cost_infinity_and_nothing_else_moves` counts a
  closed gate's exits as closed;
- `test_closed_roads.py::TestTheTable::test_the_router_loaded_all_of_it` compares
  all-year through-barriers with `_through_all_year`, since `_through_split`
  now holds the seasonal gates too;
- `TestTheCalendar::test_the_router_says_what_it_loaded_either_way` matches the
  longer startup line.

**Breakages.** Each rule was broken once, and each breakage made at least one
test fail:

| breakage | tests that failed |
|---|---|
| ordinals not stripped | 5 |
| `Mai` not read | 1 |
| `Mai` read as a prefix | 1 |
| day-first not read | 3 |
| a conditional may add to a barrier closed all year | 1 |
| gate conditionals read by month alone, without the refusals | 15 |
| a gate between two edges closes both | 2 |
| `smoothness=bad` closes | 1 |
| `4wd_only` ignored | 3 |
| sealed surface ignored for A5x | 9 |
| mixed TIGER codes counted | 3 |
| router ignores `osm_unpaved` | 1 |
| seasonal through rows close their edges | 1 |
| deploy script drops `osm_unpaved` | 1 |
| gate exits never closed by date (on the build) | 3 |
| seasonal gates not split (on the build) | 3 |
| seasonal gate exits closed all year (on the build) | 3 |
| rough closures reopened in the router (on the build) | 3 |

Loosening the ordinal regex's word boundaries failed nothing. That change is
equivalent in practice: the weekday and year refusals run before any
rewriting, and `_RANGE` allows at most two digits for a day.

## Deploy steps

Nothing here has been deployed. The return leg is the master session's:

1. **Merge to `main`** (done 2026-10-18; the brief was deleted in the
   merge). Push with `git -c http.version=HTTP/1.1 push origin main`. Then merge
   `main` into `usa`.
2. **Rebuild the tables in the main checkout**, against the graph the box
   serves:

   ```bash
   .venv/bin/python pipeline/closures.py data/raw/new-england-latest.osm.pbf data/processed-ne
   ```

   It took 51 s and 2.3 GB peak here. Expect these lines:
   - `control: roads.parquet has 565,410 ways, which matches the scan`
   - `in the graph: 197 ways, 223 edges, 182.2 km; ...` (unchanged)
   - `gates closed for the season: 9 on drivable ways, ...`, with `5 inside an edge, which closes 5 edges (6.0 km) in season` and `4 where two edges meet`
   - `wrote seasonal_closures.parquet (248 rows)` (was 235)
   - `closed to cars all year: 579 ways in the graph (724 edges, 232.3 km) of 598 in the PBF` (was 530, 665, 201.6, 549)
   - `wrote closed_to_cars.parquet (1,462 rows)` (was 1,403)
   - `unpaved by TIGER's 4WD class: 721 ways in the graph (951 edges, 575.2 km) of 736 in the PBF`
   - `wrote osm_unpaved.parquet (951 rows)`, a new file of about 43 KB

3. **Ship it.** Run `server/deploy-oracle.sh --dry-run`, then
   `server/deploy-oracle.sh`. It ships the code and three parquets
   (`osm_unpaved` is now on its `OPTIONAL` list), then restarts once. Code and
   tables must land together. Old code would read a gate's "through" rows as
   closing both edges.
4. **After the restart** it echoes the router's lines from the journal. Expect:

   ```
   seasonal closures: 227 edges (187.3 km, 197 ways) in 9 windows; 9 gates, no driving through 4 of them in season
   closed to cars: 3,328 edges (1723.0 km, 579 ways, 522 barriers and fords, 2,186 by state road class), and no driving through 108 more barriers; 3,157 junctions cut off behind them
   state road classes: 31,638 private edges (13324.3 km), start or end only; 2,186 closed (1237.7 km); 15,977 unpaved (4404.8 km)
   unpaved by TIGER's 4WD class: 951 edges (575.2 km, 721 ways)
   ```

   `/api/health` keeps `"nodes": 794685`. Its `routing_slots` goes from
   801,933 to **801,941**: two copies for each of the 4 gates between two
   edges.
5. **The box's test count** rises by the 101 new tests once the tables are on
   it.
