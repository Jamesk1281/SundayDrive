# Roads closed to cars all year: brief

**Status: diagnosed, not fixed.** Nothing in the tree has been touched. Written
2026-10-05 against `main` at `191e15c`. The measurements come from an outside
review run that day. One production case was re-run by the master session the
same day, and every code claim below was re-read against the source. The answer
goes in `docs/closed-roads.md` and in the code and tests. This brief is deleted
when the work merges, so nothing may cite it.

## The symptom, as measured

Routes, loops and reroutes drive through things OpenStreetMap marks closed to
cars all year: locked or no-access gates, concrete blocks, chains, bollards, and
whole roads tagged `motor_vehicle=no`. Seasonal closures are already masked (see
`docs/seasonal-closures.md`), but these all-year ones are not.

**How often** (outside review, 2026-10-05). The sample was 149 loops and 150
point-to-point routes from random graph nodes, at the server's defaults, on a
local server whose output was byte-identical to production. It counted a route
when its line runs along an OSM way through a gate or chain tagged `no`/`private`,
a block or bollard, or a `motor_vehicle=no|private|permit` way:

| | share crossing a closed element |
| --- | --- |
| loops | 5.4% |
| scenic routes | 6.0% |
| fastest routes | 1.3% |

The scenic preference raises exposure about 4.5×. It looks for small roads, and
small roads are where these restrictions are.

**What is in the graph.** The review scanned the raw extract for ways the
pipeline keeps:

| tag | ways |
| --- | --- |
| `motor_vehicle=no` | 260 |
| `motor_vehicle=private` | 194 |
| `access=permit` | 43 |
| `motor_vehicle=permit` | 15 |
| `access=forestry` | 6 |
| `access=military` | 5 |
| `vehicle=no` | 5 |
| `ford=yes` | 13 |

It also found 2,816 barrier nodes on those ways:
- 1,974 gates, of which 242 are `access=no` and 164 `access=private`;
- 206 blocks, 80 bollards, 66 chains and 58 jersey barriers;
- and separately, 90 ford nodes.

An earlier count, taken for the seasonal-closure work, agrees on the overlap
(`docs/seasonal-closures.md`, "Recorded, not acted on"):
- `motor_vehicle`/`motorcar`/`vehicle` = `no`/`private`: 460 ways, 452 with
  graph edges, 151.5 km. (The review's 260 + 194 + 5 is 459.)
- Ways passing a blocking barrier (block, jersey barrier, bollard, chain,
  debris, log, rope) that no access tag opens: 418 ways, 404 with edges,
  134.7 km. **Gates were not in that set.**

**Cases.** Each uses the app's exact parameters (`pref=0.50`, every weight 1.00
except `w_town=0`), sent as a POST form body.

1. **Crane Road gate, on production, re-run 2026-10-05.**
   `from=42.1396268,-71.2613399&to=42.1311784,-72.7617144&pref=0.50&w_town=0`
   comes back with "Turn left onto Crane Road" on both arms. Its line runs
   through OSM node 6295163812 at 42.1375651,-71.2680315, which is tagged
   `barrier=gate, access=no, access:delivery=no`. The node is at version 3,
   unchanged since 2021-12-20.
2. **Holman Street blocks.** `from=42.200999,-71.691789&to=44.9826946,-70.5827565`
   says "Turn right onto Holman Street (2,505 m)". It passes through nodes
   7554833357 and 7317775708, both `barrier=block, motor_vehicle=no`.
3. **Stanley Street chain.** `from=41.6274964,-72.9611079&to=43.6324515,-72.3962464`
   says "Turn left onto Stanley Street". It passes through node 6742373740,
   `barrier=chain, motor_vehicle=no`.
4. **Loops at the server's defaults** crossed:
   - a private gate on Creeper Hill Road;
   - an `access=no` gate on Quail Hollow, near Hanover, NH;
   - `motor_vehicle=no` stretches of Crosby Street, Castle Lane, Cottage Street
     and Blunt Park Road.

   Loops change with their parameters, and the Quail Hollow one did not recur
   with `w_town=0`.
5. **The reroute.** A car is stopped 57 m short of the Crane Road gate, facing
   back the way it came. The reroute the app would send (`heading` pointing away
   from the gate) opens with "Sharp left onto Crane Road" on **both** the scenic
   and the fastest arm, and goes through the gate again. So "Switch to fastest"
   does not get the driver out.

The 497 Python tests pass, and none of them asserts anything about access tags
or barriers.

## The mechanism

**Ways.** One filter is copied in three places: `pipeline/extract.py:176`,
`pipeline/graph.py:202` and `pipeline/closures.py:297`.

```python
if tags.get("access") in PRIVATE_ACCESS and tags.get("motor_vehicle") != "yes":
    return
```

`PRIVATE_ACCESS = {"private", "no"}` is at `pipeline/common.py:20`. Nothing reads:
- `motor_vehicle`, `motorcar` or `vehicle` as a ban;
- any restrictive `access` value other than `no` and `private`;
- `ford`.

**Nodes.** No stage reads `barrier`. A grep of `pipeline/`, `server/`, `tools/`,
`tests/` and `ios/` finds nothing.
- `graph.py`'s node handler (`pipeline/graph.py:152-196`) reads only exit
  numbers and traffic controls.
- `extract.py`'s (`pipeline/extract.py:163-167`) reads only viewpoints and
  place names.

**Graph shape.** `graph.py` splits each way at its junctions, so an edge is a
run of one way between two graph nodes. The way id is "dropped before the
parquet is written" (`pipeline/graph.py:228`), and so are interior node ids.
That leaves two places a barrier can be:
- an interior vertex of exactly one edge;
- a graph node: a junction, a dead end, or the joint where two ways meet end
  to end.

**The template already exists.**
- `pipeline/closures.py` scans the same PBF with the same filter. It checks its
  drivable count against `roads.parquet` as a control, and joins closed ways to
  `graph_edges.parquet` rows (`join`, `:328`). The join has two tests:
  - both ends of the edge are among the way's nodes;
  - the edge's midpoint lies within `MATCH_M = 1.0` m of the way's line, in
    EPSG:26986.

  It writes `seasonal_closures.parquet`.
- `Router._read_closures` (`pipeline/router.py:493`) loads it. `SeasonalClosures`
  refuses a table whose `u`/`v` do not match the graph (`:426-438`).
- `Router._weights` (`:1308-1348`) prices the closed slots at +inf:

  ```python
  closed = self._closed_slots(on)
  if closed is not None:
      w[closed] += np.inf
  ```

  Everything goes through it:
  - `Router.route` (`:1483`);
  - `LoopPlanner._cost` (`pipeline/looper.py:679`);
  - the mid-drive `via` rejoin and "switch to fastest", which use those two.

  So a mask there reaches every path.

**Snapping knows nothing about closures.** `Router.snap` (`:1350-1398`) takes
the nearest edge from an STRtree over every edge, and returns one of its **end
nodes**. With no heading it picks the nearer end; with a heading, the end more
nearly ahead. `snap_destination` (`:616-637`) calls it.

The server's snaps all go through these two:
- the route start, with heading (`server/app.py:281`);
- `via` (`:308`);
- the loop start (`:386`).

**Why the reroute goes back.** The reroute is an ordinary route from the snapped
node. Once the closed element is masked, no route can use it. So the mask fixes
case 5 by itself, as long as the snap does not put the start on the far side of
the barrier (Trap 2).

## Decisions already made

Do not reopen these. The owner can overrule items 4 and 5 at review.

1. **A side table and a router mask, not a rebuild.** This is the
   seasonal-closures reasoning (`docs/seasonal-closures.md`, decision 1).
   Carrying tags through `extract.py` and `graph.py` means a rebuild, and a
   rebuild moves every published number. The rebuild-time version is one
   car-access rule in `common.py`, applied in `extract.py` and `graph.py`.
   Record it in the answer document for the next full rebuild; don't do it
   here.
2. **Server-side only.** No iOS change. It ships with a server deploy and needs
   no new app build or review.
3. **The car-access rule is OSM's transport-mode hierarchy.** The most specific
   key present wins: `motorcar`, then `motor_vehicle`, then `vehicle`, then
   `access`.
   - **Closed to a car:** `no`, `private`, `permit`, `agricultural`,
     `forestry`, `military`, `emergency`, `delivery`, `psv`, `bus`.
   - **Open:** `yes`, `permissive`, `designated`, `destination`, `customers`,
     `discouraged`, `unknown` and anything unrecognised. `destination` and
     `customers` are legal for local access; count them and leave them alone.
   - The same rule decides a barrier node's own tags.
   - Subkeys such as `access:delivery` are not transport modes. Ignore them.
4. **Barrier nodes on a drivable way.**
   - **Passable unless their own tags close them:** `gate`, `lift_gate`,
     `swing_gate`, `cattle_grid`, `toll_booth`, `border_control`, `entrance`,
     `height_restrictor`, `sally_port`, `arch`, `no`. "Close them" means
     closed to a car by the hierarchy, or `locked=yes`. **Untagged gates
     stay passable**, as in OSRM's car profile. Many are open farm and park
     gates. Count how often routes still cross them, and report it.
   - **Every other `barrier=` value blocks** unless the node's own tags open it
     to a car: block, bollard, chain, jersey_barrier, debris, log, rope, fence
     and the rest.
5. **Fords are closed:** a `ford=yes` way, or a `ford=yes` node on a drivable
   way. There are few of them (13 ways and 90 nodes), and a consumer car app
   should not plan one.
6. **It applies to every caller, `on=None` included.** A gate closed all year is
   closed for every purpose. Load the table at startup. Because it is constant
   for the life of the process, the route and loop caches need no new key.

**Out of scope.**
- An in-drive "road closed" control. It is new UI and an API change, and the
  owner has not decided on it.
- Through-traffic handling for `destination`/`customers`.
- Re-admitting legally open ways that the current filter drops (for example
  `access=private` with `motorcar=yes`). That needs a rebuild. Count them.
- Time-of-day access on gates. Count it.
- Closures OSM does not record.
- Any edit to iOS, and deploying.

## Traps

1. **A barrier on a graph node is not on any one edge.** Closing every edge at
   that node closes the public road through it, which is a false closure.
   Closing the edge "it's on" picks an arbitrary one. Measure first: how many
   blocking barriers are interior vertices, and how many are graph nodes of
   degree 1, 2 and 3 or more. Then treat each case:
   - **Degree 1 (a dead end):** closing its one edge is harmless.
   - **Degree 2 (two ways meeting end to end):** the barrier forbids the
     *movement* through the node, not either edge. Both sides stay reachable
     up to it. Use the turn-restriction machinery, `_apply_turn_restrictions`
     (`pipeline/router.py:701`). Restrictions are read at `:473` and applied
     inside `_build_directed` (`:489`, which calls it at `:1099`). Synthetic
     ones must join `self.restrictions` before that call, because
     `_build_alt_tables` and the pair collapse index into the split graph
     (`:1161-1170`).
   - **Degree 3 or more:** this is usually a mapping error. Do not close it.
     List the cases in the answer document with counts and examples.

   If the degree-2 count is tiny, recording those cases instead of modelling
   them is acceptable. Say which you did, and why.
2. **Snapping can start the drive on the far side of the barrier.** `snap`
   returns an end node, chosen by distance or heading, and is blind to closures.
   Take an edge `a`→`c` 300 m long with a gate 250 m from `a`. A car stopped
   57 m short of the gate is 193 m from `a` and 107 m from `c`, so the nearer
   end is `c`, which is past the gate. With a heading toward the gate, `c` is
   also "ahead".
   The route then starts beyond the gate, and the app leads the driver through
   it to reach the start. The same happens if the start is the barrier node
   itself (Trap 1, degree 2): a route that starts at a node can leave by either
   side. The rules:
   - A start, reroute or `via` on a barrier edge snaps to the end on **the
     point's own side** of the barrier, whatever distance or heading say. Store
     each barrier's position along its edge in the table, so `snap` can compare
     it with the point's projection.
   - A point between two barriers on one edge has no reachable end of its own
     edge. Decide what it gets, and test it.
   - A destination beyond a barrier ends the route on the reachable side. It
     must not produce "no route", and must not end beyond the gate.
   - A point on a wholly closed way (`motor_vehicle=no`) may snap to an end that
     only the closed edge reaches. Decide (the nearest open edge is the obvious
     answer), and test it.
3. **Join barriers by position, not by midpoint.** `closures.py`'s midpoint test
   exists because parallel edges join the same two junctions, and `route()`
   keeps only the cheapest of them. Closing an open parallel edge closes an open
   road. A barrier can sit anywhere along its edge. The test is that the
   barrier's point lies on the edge's line (within `MATCH_M`), **and** that the
   edge's ends are among that way's nodes.
4. **Put the mask in `_weights`, not in `d_minutes`.**
   - `d_minutes` feeds the ALT landmark tables (`_build_alt_tables`, `:1161`,
     with the `inf - inf` hazard handled by `ALT_UNREACHABLE_MIN`, `:342-352`)
     and the reported ETA. Writing +inf into it changes both, untested.
   - Build the mask over edge rows and index it through `self.eidx`, as
     `_closed_slots` does (`:529-544`). Slots exist only after the restriction
     split.
5. **The filter is in three places, and the scan must match `graph.py` exactly.**
   The control is that the scan's drivable count equals `roads.parquet`'s
   565,410 rows. Do **not** "fix" the filter in `extract.py` or `graph.py` in
   this change. That forces a rebuild, and a data directory built by the old
   code would then disagree with the new code.
6. **The deploy list, and refusing a stale table.**
   - `server/deploy-oracle.sh` ships optional parquets by name
     (`OPTIONAL="access_ways access_entries seasonal_closures"`, `:21`), and
     greps the router's `seasonal closures` startup line (`:173-176`). Add the
     new table and its own startup line there. Otherwise the box routes without
     it, and nothing says so.
   - Refuse a table built against another graph, as `SeasonalClosures` does.
   - Add the step to the README build list, after `graph.py` (README `:76-81`).
7. **A test that now fails may have been encoding the bug.** The mask applies to
   `on=None` callers, so year-round routes through closed elements change. For
   each newly failing test, check by hand which element it crossed, and whether
   OSM really closes it, before changing the expectation. Never bulk-update. A
   failure in `tests/test_api.py` gets reported, not edited (see "Files you must
   not touch").
8. **A green suite proved nothing last time.** 497 tests passed with this bug.
   After adding the tests, break each rule once and confirm that some test
   fails:
   - drop `vehicle` from the hierarchy;
   - make gates always passable, then always blocking;
   - skip the snap side rule;
   - join barriers by midpoint.

   The seasonal work caught 12 of 12 such breakages only after it added one test
   it had been missing.
9. **The overrides must stay open.** These all mean open to a car:
   - `access=no` with `motor_vehicle=yes` (the current filter's one override);
   - `vehicle=no` with `motorcar=yes`;
   - `motor_vehicle=no` with `motorcar=yes`.

   A naive "any restrictive tag closes it" rule shuts all three. Unit-test
   each one.

## Done looks like

1. A single car-access function, unit-tested on the hierarchy cases (Trap 9 and
   decision 3). A scan of the PBF the graph was built from writes a new side
   table of edges closed to cars. A suggested name is `closed_to_cars.parquet`.
   Each row gives:
   - the edge row, `u` and `v`;
   - the OSM way or node id;
   - the kind (way, barrier or ford), and the tag that closed it;
   - for a barrier, its position along the edge;
   - `length_m`.

   Degree-2 barriers are rows of their own, or a separate table. One PBF scan
   for both closure tables is preferred.
2. `Router` loads the table at startup, refuses a stale one, and logs a line
   such as `closed to cars: N edges (X km, W ways, B barriers)`. `_weights`
   masks them for every caller. `snap` and `snap_destination` obey Trap 2.
3. Tests cover:
   - cases 1–3, which no longer cross their elements;
   - the Crane Road reroute from 57 m short of the gate, heading away and
     heading toward it;
   - a snap where the nearer end is past the barrier;
   - the overrides;
   - the degree-2 rule, if it was built.

   Every rule fails a test when broken (Trap 8).
4. Before and after, on the **same** random sample of at least 150 loops and 150
   routes on a local server, report:
   - exposure to the closed set (expected near zero after);
   - the share of routes that changed;
   - the median extra minutes and km, and the change in scenic km, on the
     changed ones;
   - every request that now fails and did not before, with the reason;
   - how many untagged gates routes still cross.
5. `docs/closed-roads.md` records:
   - the decisions as built;
   - the counts: ways, edges and km by tag; barrier nodes by type and by where
     they sit (interior, degree 1, 2, 3 or more); the dropped-but-open ways;
     the gates with time-of-day access;
   - what is still open: unrecorded closures, `destination`, the rebuild-time
     rule, and the "road closed" control;
   - the exact deploy steps.

   Code comments and tests cite `docs/closed-roads.md`. Add its row to
   `docs/README.md`, and point the "Recorded, not acted on" paragraph of
   `docs/seasonal-closures.md` at it.
6. The Python suite is green against the New England build, with the count
   before and after.
7. Nothing is deployed or pushed. The table is in your scratch data directory
   (see below), not in the main checkout's.

If the snap rule (Trap 2) cannot be done cleanly inside `pipeline/router.py`,
stop at the mask and the measurements. Write down what the snap rule would take.
A mask that leaves Trap 2 open must say so at the top of `docs/closed-roads.md`.

## Build and test

`<main>` means the main checkout, the first line of `git worktree list`.

- **Branch.** Work in your own worktree off `main`, on your branch. This brief is
  untracked in the master session's worktree. Copy it into your `docs/` and
  commit it with the change. Results go in `docs/closed-roads.md`, never
  appended here.
- **Files you must not touch.** Another session has uncommitted edits in
  `server/app.py`, `pipeline/looper.py` and `tests/test_api.py`. Both server
  call sites already go through `Router.snap` and `Router._weights`, so the fix
  should not need any of the three. If it truly does, stop and say why.
- **Data** is gitignored and exists only in `<main>/data`, read-only to you.
  - The New England build is `<main>/data/processed-ne`. Production's
    `/api/health` reports the same 794,685 nodes. `data/processed` is an older
    single-state build.
  - The PBF it was built from is `<main>/data/raw/new-england-latest.osm.pbf`
    (782 MB, 2026-08-25).
  - Write your table into a **scratch data directory**: a real directory whose
    entries are symlinks to `<main>/data/processed-ne/*`, plus your new file.
    Point `SUNDAYDRIVE_DATA` at it. The main checkout's data stays untouched
    until merge.
- **Python** is `<main>/.venv/bin/python -m pytest tests/ -q`, with
  `SUNDAYDRIVE_DATA` set. The venv's script shebangs are stale, so always use
  `-m`. `tests/conftest.py` puts your worktree's code on `sys.path`.
- **Memory.** The router takes roughly 4–5 GB, and the PBF scan takes minutes
  and RAM too. The Mac has 24 GB and other sessions are running, so run the
  scan, the suite and a server one at a time.
- **Local server:**
  `PORT=<free port, never 5057> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<scratch dir> <main>/.venv/bin/python server/serve.py`.
  Record `$!` and stop only that PID. A broad `pkill -f serve.py` killed
  another session's server on 2026-10-05.
- **Production** gets a handful of requests at most, to confirm the before
  state. Never send it a sample.
