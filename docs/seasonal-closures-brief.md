# Brief: stop routing over roads that are closed for the season

**Status: built 2026-10-04 on `claude/inspiring-cannon-89c90c`, not merged or
deployed.** The result comes first, below. The brief follows it unchanged.

## Result

**The table.** `pipeline/closures.py` scanned the PBF with extract.py's filter:
565,410 drivable ways, equal to `roads.parquet`. It flags **197 ways, 223
edges, 182.2 km**, every one of them in the served graph. Length-weighted score
6.14, 43.2% of km at 7 or more. That is 179 ways under decision 2 as written,
plus Mt Greylock's 18 (below). By window, where the 6 ways with two windows
count in both:

| window | ways | km | what |
|---|---|---|---|
| Oct 15 - May 15 | 4 | 3.3 | Lincoln Gap Road |
| Oct 30 - May 19 | 18 | 20.5 | Mt Greylock: Rockwell Road and Notch Road |
| Nov 1 - Apr 30 | 176 | 157.2 | VT-108, the Auto Road, ME 113 and the rest |
| Nov 1 - May 31 | 1 | 7.9 | Hurricane Mountain Road |
| Dec 1 - Mar 31, Dec 1 - Apr 1, Dec 1 - May 31 | 4 | 5.1 | Mount Agamenticus's Mountain Road and Forest Roads 59 and 59B in Maine, Ayer Road in Vermont |

**Mt Greylock, added on the builder's call** (the owner left it open on
2026-10-04). Its roads are tagged the other way round:
`motor_vehicle:conditional=yes @ (May 20-Oct 29, sunrise-sunset)`, with no
base `no`. Decision 2 reads only `no @`, so it missed them, and so did the
verdict. Read as "closed outside those dates", they close Oct 30 - May 19.
`_open_only_windows` reads `yes @ <dates>` on a car key that way. On this
extract it flags these 18 ways and nothing else: the I-93 lanes tagged
`yes @ (Mo-Fr 05:00-10:00)` have no dates, so they stay open.

**Why 179 and not 190 under decision 2.** Read literally, the verdict's rule
("a `*:conditional` containing `no` and a month, `winter` or `snow`") flags 195
ways here. The 16 between 179 and 195 are what decision 2 excludes, applied
one rule at a time:
- **8 dated one-off closures.** Read as annual windows, they would recur
  forever: four Manchester, NH ramps (2022), Lyman Street (2020-21), Crosby
  Street (to 2026-10-03) and Burnham Road (2026-03-31 to 10-31, the only one
  still running).
- **8 part-time rules** that name months and also a weekday or a time:
  - Baxter Boulevard's summer Sundays (4 ways); read by its months alone, this
    rule would close the road all summer;
  - Greenough Street in Brookline (1 way), closed on weekdays 9-4 from
    September to June;
  - Farnam Drive and two other roads in New Haven's East Rock Park (3 ways),
    shut on winter weekdays and every night.

The verdict's script is not committed, so I cannot name its exact 11 extra
ways. Every way it could have counted beyond these 179 is among the 16.

**Trap 4 occurs on this graph.** Four candidate edges had both ends among a
closed way's nodes without lying on it. All four belong to parallel *closed*
carriageways (two on the Auto Road) and are closed through their own ways. So
here the 1 m test changed which way each edge is attributed to, and not the
closed set.

**Before and after.** "Before" is `main` at `8e4e5c7` on a local server. "After"
is this branch, with the request date injected through a scratch wrapper. On
2026-10-04, 10-10 and 2027-07-15, every response (4 routes, 8 loop requests
with every sector) is byte-identical to `main`'s. Closed km is measured the
verdict's way, inside a 3 m buffer. These ran before Greylock was added, and
Greylock is too far away to touch any of them:

| request | `main` | this branch |
|---|---|---|
| Stowe → Jeffersonville, pref 0.5 | Both arms: "Head north on Mountain Road", "Continue onto Vermont Route 108 South". 27.9 km, 28 min, 4.8 km closed | On 2027-01-15: Pucker Street, Cadys Falls Road, "Turn left onto Vermont Route 15 West". 39.6 km / 44 min fastest, 38.6 km / 45 min scenic, none closed |
| Warren → Bristol, pref 0.5 | Both arms: "Turn right onto Lincoln Gap Road". 22.6 km, 27 min | On 2026-10-20: "Turn left onto Vermont Route 17", over the Appalachian Gap. 39.2 km, 36 min |
| Reroute at the gap's east end, heading 90 | Both arms: "Turn right onto Lincoln Gap Road", back over the gap. 17.4 km, 21 min | On 2026-10-20: "Turn left onto Lincoln Gap Road" (the open stretch, east), "Turn left onto Vermont Route 100", then VT-17. 44.2 km, 42 min |
| Loops of 40 and 80 km from Stowe, Warren, Jackson, Jefferson, every sector | 19 of 53 carry more than 0.2 km of closed road. The first loop offered does in 5 of 8, and Jefferson's 80 km one has 25.0 km on it | On 2027-01-15: 0 of 48, and 0 of 8. Five directions drop out: Stowe 40 NW; Warren 40 SW, W and NW; Jackson 80 NE |
| Jackson → Chatham (verdict's third row) | "Turn left onto Hurricane Mountain Road", 7.9 km closed | On 2027-01-15: through North Conway and East Conway Road. 49.7 km, 50 min |

**What the mask costs.** Measured on the router with the final table:
- **When.** Nothing is closed from Jun 1 to Oct 14. From Oct 15 only Lincoln
  Gap (3.3 km) is closed, Greylock joins on Oct 30, and the full 178-182 km is
  closed Nov 1 - Apr 30. 34.5 km is still closed in early May.
- **How much road.** 182 km is 0.08% of the network, but 105 km of it scores 7
  or more: 0.38% of the region's 27,378 beautiful km.
- **Ordinary trips.** In January, 0 of 300 random trips (15-150 km) change.
- **Mountain trips.** 4 of 200 random trips with both ends within 15 km of a
  closed road change: +3 min median, +10 min at worst, and no scenery lost.
- **Mountain loops.** 2 of 16 random 60 km loops change, and the directions
  offered go from 125 to 124.
- **Where it does bite.** Loops from the four notch towns: 23 of 53 change, by
  -0.19 score and -4.8 beautiful km at the median.
  - Overall they lose 75 of 977 beautiful km.
  - Worst: Stowe's first 40 km loop loses 31 of its 40 beautiful km.
  - Warren's 80 km loops gain, over the Appalachian Gap.
  - The point-to-point notch crossings add 9-17 min.
- **The conservative part.** 59.6 km is closed by a dated or winter access
  rule, which means a gate. The other 122.6 km is closed only for
  `winter_service=no` or `seasonal=*`, which means unplowed. Those are avoided
  from Nov 1 even in a dry autumn, as decision 2 says.

**How often the new 404 fires.** "The only way there is closed for the season"
is answered only when the start or the destination is on a closed road or
beyond one. These counts are measured as reachability from Boston, with
junction copies included:

| date | junctions cut off | road | road-side viewpoints cut off |
|---|---|---|---|
| Oct 20 | 3 | 2.3 km | 1 of 2,195 (Lincoln Gap) |
| Oct 30 | 24 | 21.6 km | 13 (mostly Greylock) |
| Nov 1 - Apr 30 | 209-212 | 142-144 km (0.06%) | 24 (Greylock, Wachusett, the Notch, Mt Everett and more) |
| May 1 | 40 | 31.4 km | 13 |

- None of 500 sampled trips hit the 404.
- The largest cut-off stretches are ME 113, the Auto Road, Rockwell Road,
  Jefferson Notch Road and Kelley Stand Road.
- These are true answers: none of those places can be reached by car that day.

**What still slips through: closures OSM does not record.**
- **Certain:** Acadia's Park Loop Road (29.9 km, score 8.59) and Cadillac
  Summit Road (5.4 km, 7.68). The park closes both Dec 1 - Apr 14, and OSM
  tags neither. Park Loop Road is #5 on the flagship list. The lasting fix is
  an OSM edit, a `motor_vehicle:conditional` on those ways. It reaches the app
  only with the next full rebuild, because `closures.py` reads the PBF the
  graph was built from. Closing them this winter would take a hand-kept
  override.
- **Possible, unverified:** Mt Equinox's Skyline Drive (8.6 km) and Skinner
  State Park Road (4.2 km) are summit roads in the graph with no closure tag.
  I could not find the toll roads on Mt Mansfield and Burke Mountain, or Pack
  Monadnock's road, by name near their summits. They may be mapped as tracks,
  which the graph leaves out.
- **Not modeled:** Farnam Drive's winter-weekday closure, and Howeville Road's
  `seasonal=winter`, which is probably a mistag.

**Recorded, not acted on (Trap 5).** The counts reproduce the verdict's; the
kilometres differ because its join is not committed:

| set | ways in the PBF | with graph edges | km |
|---|---|---|---|
| `motor_vehicle`/`motorcar`/`vehicle` = `no`/`private` | 460 | 452 | 151.5 |
| behind a blocking barrier no access tag opens | 418 | 404 | 134.7 |

**Decided while building, beyond the brief:**
- **Greylock's inverse tag counts** (above).
- **A stale table stops the server.** A table whose rows do not match
  `graph_edges.parquet`'s `u`/`v` raises at startup, so `closures.py` reruns
  after every `graph.py` (README).
- **`on=None` closes nothing.** Only the server passes a date, which keeps
  tools and the existing tests on the year-round graph.
- **`test_api.py` pins the date** to 2027-07-15, so its results no longer depend
  on the date the suite runs.
- **The deploy script echoes the closure line.** After a restart, it prints the
  router's `seasonal closures: ...` line from the journal. That line is
  untested against the box.

**Tests.** `tests/test_closures.py` holds 99 tests. The suite: **495
passed, 0 failed** (396 before), exit 0. 12 deliberate breakages were all
caught once one test was added. That test covers the breakage that had
survived: dropping the date from one arm of the `via` rejoin. Once the table is
on the box, the box's count in `server/DEPLOY-oracle.md` rises by 99, and its
journal should read `seasonal closures: 223 edges (182.2 km, 197 ways) in 7
windows`.

## The symptom, measured (verdict C-1, 2026-09-30, New England build)

- **190 drivable ways (165.5 km) in the served graph** are ones OpenStreetMap
  marks closed or unmaintained in winter. Concretely: a `*:conditional` with
  `no` and a date, `winter` or `snow`; or `winter_service=no`; or `seasonal=*`.
- **The scenery score prefers them.**
  - Their length-weighted mean is 5.93, against 4.56 for the network.
  - 37.2% of their km score 7 or more, against 10.0% overall.
  - Examples: VT‑108 through Smugglers' Notch (8.51), the Mt Washington Auto
    Road (7.86), Lincoln Gap Road (7.33), Hurricane Mountain Road, Jefferson
    Notch Road, Evans Notch (ME 113), Hazens Notch, Kelley Stand Road.
- **Every main path uses them**, the fastest arm included:

  | Request | What comes back |
  | --- | --- |
  | Stowe → Jeffersonville, VT (`from=44.4654,-72.6874&to=44.6437,-72.8290`) | Every arm drives VT‑108 |
  | Warren → Bristol, VT (`from=44.1123,-72.8565&to=44.1334,-73.0790`) | Every arm drives Lincoln Gap Road |
  | Loops from Stowe, Warren, Jackson and Jefferson, NH | 19 of 53 loops carry more than 0.2 km of these roads, and the first loop offered does in 5 of 8 cases |
  | Reroute from the east end of the closed Lincoln Gap section, heading 90° | Sends the driver back over the gap |

- **Why it matters:** a driver at a winter gate has no way out. The reroute,
  "switch to fastest" and the loop all send them back up the same road.

## The mechanism

- `pipeline/extract.py:176-177` keeps a drivable way unless `access` is
  private/no without `motor_vehicle=yes`. Nothing in `pipeline/` reads
  `*:conditional`, `seasonal` or `winter_service`.
- The graph has one state all year.
- **Every route and every loop is priced by one function**,
  `Router._weights(pref, scores, avoid_unpaved)` at `pipeline/router.py:1179`.
  - `Router.route` calls it (`:1339`).
  - `LoopPlanner._cost` calls it (`pipeline/looper.py:661`).
  - The mid-drive `via` rejoin and "switch to fastest" go through those two.

  So a mask applied inside `_weights` reaches every path:

  ```python
  w = self.d_minutes + strength * BETA * penalty[self.eidx]   # router.py:1200
  ```

- Per-edge arrays are indexed by **undirected edge row** (`self.km`, `:957`).
  They reach directed slots through `self.eidx` (`:955`), which
  `_apply_turn_restrictions` extends (`:664`). A mask built over the rows of
  `graph_edges.parquet` and applied as `closed[self.eidx]` is therefore correct
  by construction.
- **Edges carry OSM node ids.** `graph_edges.u`/`v` and `graph_nodes.node_id`
  are OSM node ids (21,321,186 … 14,123,593,723). A flagged way's node refs
  from the PBF therefore identify its edges directly; see Trap 4 for the
  catch.
- The PBF behind the served graph is
  `<main>/data/raw/new-england-latest.osm.pbf` (782 MB, 2026-08-25). It exists
  only in the main checkout. `pyosmium` is installed in `<main>/.venv`.
  `pipeline/common.py:11-20` has the `DRIVABLE` set extract.py uses.

## The decisions (made, do not reopen)

1. **A side table, not a graph rebuild.**
   - A new script, `pipeline/closures.py`, scans the PBF with extract.py's
     own filter. That scan should see 565,410 drivable ways, matching
     `roads.parquet`, which is the control.
   - It writes `data/processed-ne/seasonal_closures.parquet`: one row per
     graph edge, with `u`, `v`, the edge's row identity, the way id and name,
     the raw tag, and the closed window as month/day start and end.
   - `Router.__init__` loads it if present, the way it already treats
     `access_ways`/`access_entries` as optional (`router.py:428-440`).
   - Carrying the tags through `extract.py`/`graph.py` is for the next full
     rebuild. A rebuild moves every published number, so it is not for now.
2. **What counts as closed, and when** (dates are in America/New_York):
   - A `*:conditional` whose condition carries month or date ranges, such as
     `no @ (Nov-Apr)`, `no @ (Oct 15-May 15)` or `no @ (Nov 1-Apr 30)`, is
     closed inside **its own** ranges, including ones that wrap the year end.
   - A `*:conditional` whose condition is `winter` or `snow`, `winter_service=no`,
     and `seasonal` ∈ {`yes`, `summer`, `spring;summer;autumn`, `no_snow`}
     are closed **Nov 1 – Apr 30**, the default winter window.
   - Conditions that are only times of day (`no @ (22:00-06:00)`) or vehicle
     classes are **not** closures. Ignore them.
3. **Closed means unusable.**
   - Closed edges get `+inf` added in `_weights`. That is safe in both
     searches: scipy's Dijkstra never relaxes an infinite edge, and
     `_astar`'s `nd < dist.get(v, inf)` is never true for one.
   - The ALT bound stays admissible, because closing edges only raises true
     costs.
4. **"Today" is evaluated per request**, with an injectable date for tests.
   The active set changes on fixed dates while the server runs for weeks.
5. **When the only way is closed:** if masked routing finds no route but the
   unmasked graph would have one, return HTTP 404 with
   `error="the only way there is closed for the season"`. Otherwise keep the
   existing errors (`server/app.py:301`, `:311`). Loops simply route around.
6. **In the app,** add a fifth item to `BeforeYouDriveView`'s "What it does not
   do" list:

   > **Seasonal roads.** Some mountain roads close for winter. The app avoids
   > the closures OpenStreetMap records, but not every closure is recorded,
   > so follow posted signs.

   It is a separate commit, because it needs a new build while the server part
   does not.

## Traps

1. **Computing the mask once at startup is wrong.** The box runs for weeks.
   Lincoln Gap closes on Oct 15, but VT‑108 and Hurricane Mountain Road close
   on Nov 1. A mask fixed when the server started would miss every date after
   it.
   - Compute the active set from the current date, and cache it by date at
     most.
   - Tests must inject the date and never read the real clock. On 2026-10-04
     Lincoln Gap is *open*, so a test of "today" proves nothing.
2. **The caches will serve pre-closure routes after the date flips unless
   the closure state is in their keys.** All three caches key on everything
   except that state:
   - `LOOP_RESULTS` in `server/app.py:354-355`;
   - `LoopPlanner._fields_by_key` in `pipeline/looper.py:589-590`;
   - `LoopPlanner._costs_by_key`, the `_cost` key.

   Add a closure version, for example a hash of the active set, to all three
   keys.
3. **The deploy script will not ship the new file.**
   - `server/deploy-oracle.sh:18-19` copies a fixed list,
     `REQUIRED="graph_edges graph_nodes turn_restrictions"` and
     `OPTIONAL="access_ways access_entries"`.
   - Add `seasonal_closures` to `OPTIONAL`, or the box silently runs with no
     mask.
   - The router must log at startup how many closure edges it loaded, so the
     box's journal shows it.
4. **A node-id join alone over-marks parallel roads.** When a closed way and
   an open way both run between the same two junctions, both rows share
   `(u, v)`. `route()` collapses parallel edges to the cheapest
   (`router.py:1342-1343`), so closing both would also close the open road.
   - Take candidate rows by `u`/`v` in the way's node refs.
   - Then confirm each by its geometry: midpoint within 1 m of the way, in
     EPSG:26986. That is the verdict's method, and it reproduced the 190.
5. **Don't widen the scope to the year-round sets in this pass.** The verdict
   also counted:
   - 460 ways / 152.8 km tagged `motor_vehicle`/`motorcar`/`vehicle` =
     `no`/`private` all year;
   - 418 ways / 141.9 km behind blocking barriers.

   Both are real, but they carry false-positive risk (a destination on a
   private drive becomes unreachable). They are a separate decision. Record
   their counts in the report and leave them.

## Done looks like

1. **The side table builds.** `pipeline/closures.py` writes
   `seasonal_closures.parquet`, and its control count is 565,410 drivable
   ways. Around 190 ways should be flagged on this PBF. If the number moves,
   say why.
2. **The router applies it.** It loads the table optionally, applies the mask
   per request date inside `_weights`, adds the closure version to the three
   cache keys, and logs the loaded count.
3. **Tests**, with injected dates, in a new `tests/test_closures.py`:
   - Stowe → Jeffersonville avoids VT‑108 on 2027-01-15 and uses it on
     2027-07-15.
   - Warren → Bristol avoids Lincoln Gap Road on 2026-10-20 and uses it on
     2026-10-10.
   - The Lincoln Gap reroute (heading 90°) does not go back over the gap on
     2026-10-20.
   - Loops of 40 and 80 km from Stowe, Warren, Jackson and Jefferson, NH,
     every sector offered, carry ≤ 0.2 km of closed road on 2027-01-15.
   - A conditional with only a time of day is not a closure.
4. **The full suite stays green.** The baseline was 388 passed at `6f26edf`,
   run with `SUNDAYDRIVE_DATA=<main>/data/processed-ne`.
5. **The deploy script** lists `seasonal_closures`. **Do not deploy.** The
   master session deploys after the merge.
6. **The app** gets the `BeforeYouDriveView` line, in its own commit.
7. **The report** gives:
   - the flagged count;
   - before/after step names for the four requests;
   - the year-round counts, recorded and not acted on (Trap 5).

## Build and test

- Work on your own branch off `main`. Commit this brief with the change if it
  is not already committed.
- `data/` and `.venv` live only in the main checkout, written `<main>` here,
  not in a worktree.
  - Build the table into `<main>/data/processed-ne/`.
  - Run the suite with `SUNDAYDRIVE_DATA=<main>/data/processed-ne
    <main>/.venv/bin/python -m pytest -q tests > out.txt 2>&1; echo $?`.
  - Never pipe pytest through `tail`; the exit code is lost.
- For the request checks, start a local server on a free port
  (`PORT=<port> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=… server/serve.py`).
  Don't use 5057, which another session may own.
- If you touch the app, run `xcodegen generate` in `ios/` first; the project
  is gitignored.
