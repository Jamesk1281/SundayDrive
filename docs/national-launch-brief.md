# Closing the national launch gap (brief)

**Status:** diagnosed, not fixed. Written 2026-10-18 in the master session.
Nothing has been touched for this. It is one brief for **four parallel units**,
A to D. Each unit reads "Common" plus its own section, works on its own branch
off **`usa`** (never `main`), and writes its own answer document, named in its
section. This brief is deleted in the merge that brings back the last of the
four. Until then it is untracked, and each unit commits an unchanged copy with
its work. **Never edit it, never append results to it, and never cite it.**

## Common

### The goal and the date

The owner decided on 2026-10-18:
- The New England-only app is **never public**. The first App Store release is
  the national app: the contiguous 48 states and DC. Alaska, Hawaii and the
  territories are out of scope and are not mentioned anywhere.
- **No Western test drives will happen.** No unit may gate anything on them.
- `docs/marketing-plan.md` (on `main` and `usa`) targets **App Store submission by
  Thursday 29 October 2026** (the go/no-go at L−7) and **launch on Thursday
  5 November**. A slip moves launch a week at a time (§7.3).

**Today none of the national code exists.** The server, the data and the app are
New England-only. Each unit's first job is an **honest earliest date for its part,
committed to its answer document within its first day of work**. Measure; don't
promise. If 29 October can't be met, the master session needs to know early, not
on the 28th.

### Decided in the master session (don't reopen)

- **The route search design is "path C"** from `docs/usa-extension-feasibility.md`
  §8 (on `usa`): one compact national graph in memory, and each route searched
  only inside an ellipse around the trip.
- **Point-to-point trips are capped at 500 km straight-line distance.** A longer
  request gets a clear error, not a slow search. The owner proposed a directions
  cap like the loop cap himself. 500 km is the range over which corridor search
  was measured to stay near today's latency (feasibility §3). Loops keep their
  existing limits.
- **Scenery scoring is national and absolute**: candidate E1, already built on
  `usa` (`docs/national-scenery-components.md`). The Western land-cover study
  (`docs/western-landcover-verdict.md`) kept WorldCover as the desert source.
- **The server stays on the existing Oracle box**: 24 GB RAM, ARM (aarch64),
  Ubuntu, $0 Always Free. No paid hosting.
- **The permit rule** (`permit` closes a road all year, `pipeline/common.py`
  `CLOSED_TO_CARS`) is the owner's open decision. Nobody changes it.

### The contract between units A and B

Unit A delivers a **processed directory for the whole country**, at
`data/processed-us` in the main checkout. It has **exactly the files and columns
`data/processed-ne` has today** that the server reads:

`graph_edges.parquet`, `graph_nodes.parquet`, `turn_restrictions.parquet`,
`access_entries.parquet`, `access_ways.parquet`, `closed_to_cars.parquet`,
`seasonal_closures.parquet`, `osm_unpaved.parquet`, `state_road_class.parquet`
(that one is New Hampshire, Vermont, Massachusetts and Maine only; the other
states get an empty table with the same columns).

Grep `pipeline/router.py`, `pipeline/options.py`, `pipeline/looper.py` and
`server/app.py` for `.parquet` to confirm the list. Unit B builds whatever compact
form it needs *from* that directory, so neither unit blocks the other. B develops
on `data/processed-ne` and a synthetic large graph until A delivers.

### Where things are

- `data/` and `traces/` exist only in the main checkout,
  `/Users/james./Desktop/myapps/SundayDrive`. The `usa` worktree's `data` is a
  symlink to it. **Never write into `data/processed-ne` or `data/processed`:**
  `processed-ne` is what the box serves today. Write new data into new
  directories.
- Run the suite with `SUNDAYDRIVE_DATA=/Users/james./Desktop/myapps/SundayDrive/data/processed-ne`
  set. Without it the tests silently use the August Massachusetts-only graph.
  `usa` was 938 passed, 12 skipped, 0 failed on 2026-10-18 like that.
  Interpreter: `/Users/james./Desktop/myapps/SundayDrive/.venv/bin/python`.
- The Mac has about 116 GB free disk (2026-10-18) and 24 GB RAM. Other sessions
  run servers on it, so kill only your own server, by PID. **Never
  `pkill serve.py`.**
- Deploying to the box is the master session's job (`server/deploy-oracle.sh`).
  No unit deploys or pushes.
- The repo is public. No home location, drive traces or marks in commits.

---

## A. The national road graph build

**Answer:** `docs/national-build.md`, plus the code. **Branch:**
`claude/national-build` off `usa`. **Owns:** `pipeline/graph.py`, `extract.py`,
`elevation.py`, `landcover.py`, `score.py`, `terrain.py`, `protected.py` (only
where scale forces a change), and a new `tools/national_build/`. **Doesn't touch:**
`closures.py` (unit D), `router.py` (unit B), `ios/` (unit C).

**Goal:** `data/processed-us` per the contract, for the 48 states and DC, scored
with E1, built on this Mac.

**What is known:**
- **Size:** about 19.1M graph nodes, ±20%. 11.8 GB of OSM extracts, 4.1 GB of
  Terrarium tiles, 9.1 GB of WorldCover streamed. Peak 9 GB of working space
  keeping only packs, 40–47 GB keeping every processed directory. Elevation
  mosaic RAM per state peaks at 13.3 GB (Texas), which fits. Source:
  `docs/us-map-data-findings.md` §2, measured per state in
  `tools/us_map_data/results/`.
- **The pipeline builds one region from one PBF.** `pipeline/graph.py:428-433`:
  ```python
  def main(pbf_path: str, processed_dir: str):
      ...
      h.apply_file(pbf_path, locations=True, idx="flex_mem")
  ```
  Graph nodes are OSM node IDs (`graph.py:10`, `node_id`), and ways are split
  into edges at junctions counted from the ways *in that extract*
  (`graph.py:100-101`, `node_count`).
- Building the whole country from one PBF in one process is ruled out at today's
  memory cost: about 6.7 GB of RAM per GB of PBF, so about 79 GB for 11.8 GB.

**Traps:**
1. **Stitching per-state graphs by concatenation is wrong at every border.** A
   Geofabrik state extract keeps a way that crosses the border whole, so it shows
   up in both states. A junction whose other road is in only one extract gets
   counted differently on each side, so the same road is split into different
   edges in the two builds. Concatenating and deduplicating on `(u, v)` leaves
   duplicate or overlapping edges and missed junctions. Choose a method that gets
   junctions right globally. Possibilities: merge the state PBFs and run the
   junction pass on all of them (`osmium merge`, with an on-disk location index
   such as `dense_file_array`); or build overlapping regions and keep each edge
   only from the region that owns its midpoint, with junctions computed from the
   union. Then **prove it at a real border.** Build NH+VT as two states, stitch
   them, and compare with the existing joint New England build: edge counts and
   routes across the Connecticut River must match.
2. **New England must not move.** The national graph's New England part should
   score and route like `processed-ne` built with E1. Check a sample of trips
   (`tools/route_census.py` style) and report the differences. New England has
   the only ground truth (the marks) and the only real users so far.
3. **Region-specific constants are hiding in the pipeline.** New England bounds,
   the Terrarium spike band (`elevation.py`'s `ELEV_MAX_M`/`ELEV_MIN_M` and the
   in-band coastal spikes in `docs/us-map-data-findings.md` §6.1), the byway
   allowlist, `RAW_BASE`/`STRETCH` fitted on New England. The absolute scale
   keeps the score constants. Grep for New England bounds and state lists, and
   report each one you find.
4. **Sidecars have to be built too.** Run `closures.py` per state, or over the
   merged PBF, without editing it (unit D owns it). Merge its tables onto the
   national edge ids. `state_road_class` stays New England's four states.

**Done:**
1. The earliest honest date for `processed-us`, in `docs/national-build.md` on
   day one.
2. A build driver in `tools/national_build/`, re-runnable state by state, with
   the measured time, disk and RAM.
3. The border proof (trap 1) and the New England non-regression (trap 2).
4. `data/processed-us` delivered per the contract, with node, edge and km counts
   per state. Or a statement of what blocked it.

---

## B. The router at US scale

**Answer:** `docs/router-at-us-scale.md`, plus the code. **Branch:**
`claude/us-scale-router` off `usa`. **Owns:** `pipeline/router.py`,
`options.py`, `looper.py`, `server/app.py`, `server/serve.py`, and the
server-side region messages. **Doesn't touch:** the pipeline build files (A),
`closures.py` (D), `ios/` (C).

**Goal:** the server answers routes, route options, loops and reroutes for the
whole country on the 24 GB box. Point-to-point is capped at 500 km. Latency
stays near today's New England figures for trips up to about 300 km, and under
the app's 20 s give-up for everything allowed.

**What is known (feasibility review §2–§4, §9, measured on the Mac):**
- **Today's router on a US graph:** about 88 GB RSS, about 25 min to load, and
  24–26 s per scenic search. That last figure was measured on 29 linked copies
  of New England, 23.3M nodes.
- **Where the memory goes** (New England, 3.7 GB): edge geometry as shapely
  objects 1.1 GB, a projected copy 0.56 GB, string columns 0.42 GB, routing
  arrays 0.40 GB, and a Python dict from node ID to index (2–3 GB at US size).
  The dict is at `router.py:762`:
  ```python
  self.idx = {nid: i for i, nid in enumerate(ids)}
  ```
  The geometry and its spatial index are built at `router.py:769-770`
  (`self._edge_geom_m = ...to_crs(CRS_METERS)`, `STRtree`).
- **Compact layout measured:** the arrays a search needs are 113 B per node, and
  everything for turn-by-turn and drawing is 122 B per node. That's about
  230 B per node, roughly 4.4–5.5 GB for the US.
- **Per-request work over the whole graph:** each request re-blends every edge
  score (`router.py:1930-1958`, `_edge_scores`: `raw = self.base_score +
  self.pref_matrix @ w`), builds weights for every edge (`_weights`,
  `router.py:1960`) and builds the CSR. That's 53 ms on New England and about
  1.6 s at US scale. It all has to become O(corridor).
- **Corridor search is exact on 80/80 trips.** The ellipse is a detour
  allowance of half the trip distance plus 20 km. It held all 300 sampled scenic
  routes, at 30–39% of the full search time. Its cost depends on trip length,
  not map size: about 0.2–0.3 s at 300 km and 0.5–1.4 s at 500 km with scipy.
  It is empirical, so production code must widen the corridor when a route
  touches its edge.
- `REGION_TZ = ZoneInfo("America/New_York")` (`router.py:484`) dates the seasonal
  closures. Nationally the date has to come from where the trip is.
- The K-1 cost models are 82 MB each on New England (`server/app.py:160`). That
  is roughly 2 GB each at US scale, so check them against the box's memory.

**Traps:**
1. **Parity before speed.** Today's router on `processed-ne` is the oracle. The
   rewritten router must return the same routes there: run a fixed set of
   point-to-point trips, options and loops, and explain every difference. A
   faster router that routes differently in New England breaks the one region
   with ground truth. The features to keep are listed in feasibility §9:
   weights, splits, closures, the private rule, snapping, turn-by-turn, options,
   loops, the K-1 rejoin.
2. **Don't extract the corridor with a whole-graph mask.** The review's
   prototype did, and that costs O(E), about 1–1.5 s per request at US scale.
   Index nodes spatially (a grid over projected coordinates) so the corridor
   costs O(corridor). Prefer numpy and scipy on the corridor's sub-CSR. Add a
   compiled kernel (numba must work on aarch64 Linux, and the box's Python
   version matters) only if measurement shows scipy isn't enough, and say so.
3. **Measure memory as the box will see it,** with every cache and cost model
   loaded and several concurrent requests, not an RSS figure taken after load.
   Peak RSS needs replicates (load-probe traps: the Mac swaps graph servers out).
   Test at US scale on a synthetic graph (linked New England copies, as the
   review did) before `processed-us` exists.
4. **The 500 km cap is straight-line between the snapped endpoints.** It must be
   enforced before any search starts, with a message the app can show. Options
   and splicing (`options.py`, `plan` at `options.py:323`) need the corridor too.
   An unmodified options plan was estimated at 30–40 s at US scale.

**Done:**
1. The earliest honest date, in `docs/router-at-us-scale.md` on day one.
2. New England parity: a fixed trip set, identical routes or every difference
   explained, and the suite green.
3. US-scale measurements on the synthetic graph, then on `processed-us` when A
   delivers: load time, RSS under load, and p50/p90 latency by trip length for
   route, options, loop and reroute.
4. The 500 km cap, and the server's out-of-coverage messages made national.

---

## C. The app goes national

**Answer:** `docs/app-goes-national.md`, plus the code. **Branch:**
`claude/app-goes-national` off `usa`. **Owns:** `ios/` only. **Doesn't touch:**
`server/` (B owns the server's messages; list anything the server must change in
your answer document for B).

**Goal:** an iPhone build in which the whole of the 48 states and DC works:
search, start points, the map camera, loops and copy. New England-only gating is
removed rather than widened to a bigger box.

**What is known.** New England gating lives in:
- `ios/Sources/NewEnglandBoundary.swift` (the "is this in New England?" polygon);
- `ios/Sources/Region.swift` (the camera box and search fallback, "taller than
  New England, and centred north of it, on purpose");
- `ios/Sources/SearchCompleter.swift` (results limited to New England places,
  `NewEngland.allowsSuggestion`, and a region outside New England swapped for the
  New England envelope);
- `HomeView.swift`, `BeforeYouDriveView.swift`, `LoopView.swift` and
  `LoopModel.swift` (copy and checks);
- the tests `ios/Tests/NewEnglandTests.swift` and `OutsideNewEnglandTests.swift`.

The completer ignores `.required` and puts a city's state in the title
(`docs/new-england-only.md` on `main`).

**Traps:**
1. **Don't replace the New England polygon with a US polygon and call it done.**
   The 48 states plus DC still has edges: Canada, Mexico, the oceans, Alaska and
   Hawaii. Out-of-coverage handling has to stay honest at those edges. And the
   NE build on `main`, which TestFlight friends use, must keep its New England
   gating. Make this change on `usa` only.
2. **The simulator lies about location and keyboards.**
   - Use `simctl location start` playback for drive screenshots, not `set`.
   - `xcodebuild test` takes `TEST_RUNNER_` environment variables, not
     `SIMCTL_CHILD_`.
   - Use `-destination id=`, never `name=`, and never pipe `xcodebuild` through
     `tail`.
   - Create your own simulator device: other sessions use theirs.
   - Run your local server on a free port, never 5057.
3. **Copy says New England in many places,** the App Store attribution among
   them. Grep `ios/` for "New England" and list every string you change. The
   App Store listing and screenshots are not code and are out of scope; list what
   they will need.

**Done:**
1. The earliest honest date, in `docs/app-goes-national.md` on day one.
2. A build with New England gating removed and coverage edges handled, and the
   tests rewritten. The suite passes against a local server on `processed-ne`
   (and on `processed-us` once it exists).
3. A list of the server message changes B must make, and of the listing and
   screenshot changes the release needs.

---

## D. Winter closures for park and forest roads

**Answer:** `docs/winter-closures-national.md`, plus the code. **Branch:**
`claude/winter-closures` off `usa`. **Owns:** `pipeline/closures.py`, plus a new
input stage if needed. **Doesn't touch:** `router.py` (B). If the router needs a
new column, write it in the existing `seasonal_closures` format.

**Goal:** a November launch must not route drivers onto park and forest roads
that are shut for winter. Today they are routed, because OSM doesn't tag them.

**What is known** (`docs/us-map-data-findings.md` §4, §6.4, §6.6):
- **Untagged, routed open all winter:** Teton Park Road (closed Nov 1–Apr 30),
  Glacier Point Road, Yellowstone's Grand Loop (225.5 km; most park roads close
  in early November), Kuwohi Road, and Crater Lake's Rim Drive and Old Fall River
  Road (free text only). The Beartooth is 17 of 130 km closed.
- **The NPS public roads layer** marks Glacier Point, Teton Park Road, Tioga,
  both Crater Lake rim drives and Old Fall River as seasonal. Its dates are
  prose, and it says "Unknown" for 1,979 of Yellowstone's 2,007 segments.
- **MVUM has machine-readable dates** per vehicle class
  (`passengervehicle_datesopen`, e.g. `04/01-11/30`, 727 distinct strings). In
  one forest (GMUG, Colorado) MVUM marks 821 km of graph road seasonal, and
  closures.py closes 1.6 km of it.
- **The generic winter window is too short for high passes:** Nov 1–Apr 30,
  against openings in late May to July. Lassen, Ebbetts, Sonora, Mount Blue Sky
  and the Mount Washington Auto Road are open in closures.py for 2–10 weeks of
  real closure.

**Traps:**
1. **Join external layers by geometry, never by name.** Clingmans Dome Road
   became Kuwohi Road in 2024. Use the matcher in
   `tools/us_map_data/mvum_osm_match.py` (25 m steps, 15 m radius) as the
   pattern.
2. **When the source is uncertain, close for the longer window.** An "Unknown"
   segment or a prose date resolves toward the closure, never toward open. The
   failure that matters is routing someone onto a gated road in a snowstorm. Every
   per-road window in a curated table needs its operator source and access date
   written beside it.
3. **Don't change the permit rule,** and don't widen the generic winter window
   for every road. That would close low-elevation roads that stay open all year
   (the Kancamagus control in §4 must stay open).

**Done:**
1. The earliest honest date, in `docs/winter-closures-national.md` on day one.
2. MVUM passenger-vehicle dates and NPS seasonal segments joined into
   `seasonal_closures`, plus a sourced window table for the high passes and park
   roads in §4.
3. The §4 table re-run: every road in it, closed or open on the right dates.
   Plus New England unchanged except roads with a sourced reason (the Auto Road).
4. Tests in `tests/test_closures.py`. The suite green.
