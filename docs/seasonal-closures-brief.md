# Brief: stop routing over roads that are closed for the season

**Status: diagnosed and decided, not fixed.** Written 2026-10-04 against `main`
at `454e2cc`. No source file has been touched for this brief. This is
`pre-submission-review-verdict.md` C-1, the last code blocker before the app is
public. Read that section for the evidence. This brief adds the code facts and
the decisions, and does not repeat the derivation.

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
- `data/` and `.venv` live only in the main checkout (`<main>` =
  `/Users/james./Desktop/myapps/SundayDrive`).
  - Build the table into `<main>/data/processed-ne/`.
  - Run the suite with `SUNDAYDRIVE_DATA=<main>/data/processed-ne
    <main>/.venv/bin/python -m pytest -q tests > out.txt 2>&1; echo $?`.
  - Never pipe pytest through `tail`; the exit code is lost.
- For the request checks, start a local server on a free port
  (`PORT=<port> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=… server/serve.py`).
  Don't use 5057, which another session may own.
- If you touch the app, run `xcodegen generate` in `ios/` first; the project
  is gitignored.
