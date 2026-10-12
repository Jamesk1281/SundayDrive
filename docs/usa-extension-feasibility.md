# A full-USA Sunday Drive: independent feasibility review

**Status:** measured against `main` at `2ed3f47`, committed on the `usa`
branch 2026-10-12. Nothing in `pipeline/`, `server/` or `ios/` has been changed.
Scripts and logs are in `tools/usa_feasibility/`. The data half is
[us-map-data-findings.md](us-map-data-findings.md), and the US means the 48
contiguous states and DC.

> **Corrected by [us-map-data-findings.md](us-map-data-findings.md) §9
> (2026-10-11):**
> 1. **US graph size.** It is about **19.1M nodes** (±20%, 17 states counted),
>    not 23.4M. The fit below overestimated every rural state measured since.
>    The compact US pack is therefore about **4.4 GB**, not 5.5.
> 2. **Trail Ridge Road.** It *is* tagged seasonal in OSM
>    (`no @ Oct 14th - May 31st`), but closures.py rejects the ordinal "14th".
>    The all-year `permit` rule then closed it every day of the year. The real
>    bug is a road closed in July, not one open in January.
> 3. **Terrarium tile count.** "60,400 tiles" is the bounding box. The 48 states'
>    outlines need 35,778, and state-by-state builds fit elevation.py's
>    existing in-RAM stage (Texas peaks at 13.3 GB). No tiled stage is needed.
> 4. **Colorado's fake relief.** It is real in metres, but the relief score caps
>    at 100 m and the surrounding mountains are already there, so only one of
>    the three tiles changes the score. The harm is on flat and coastal ground.
>
> Alaska and Hawaii are out of scope; ignore them below.

2026-10-10. Built from the code and from measurements made for this review.
No project memory and no earlier docs were read, and nothing here has been
reconciled with them. Every number is measured unless marked *est.*; the
scripts and raw results are in `tools/usa_feasibility/`.

## Verdict

**Feasible, but not by pointing today's pipeline at a bigger extract.** Three
things stand in the way. In order of difficulty:

1. **Search and memory: solvable, an engineering job.** A US graph is about
   23M nodes, 29.5x New England. Today's router would need roughly 90 GB and
   24-26 s per scenic search, and the app gives up at 20 s. Searching only a
   corridor around the trip returned the whole-graph optimum on 80 of 80 trips.
   Its cost grows with the trip, not the map. Pair it with a compact in-memory
   layout (about 5.5 GB for the US; section 9) and the US fits today's 24 GB box
   at roughly today's latency, for trips up to about 500 km.
2. **Data outside New England: solvable, weeks plus per-region checking.** A
   full Colorado build ran unchanged, and it shows the West breaking assumptions
   New England never tested:
   - Trail Ridge Road is closed all year by the `permit` rule, and its
     seasonal tag goes unread (corrected; see the header).
   - The best-scoring roads in the state are 4WD jeep tracks.
   - Default speeds are 19-28% low.
   - 15 of 26 state byways are missed, and one whole US highway is flagged as a
     byway.
3. **The scenery model: the long pole.** On the one independent label available
   everywhere (official byways) it does as well in Colorado as at home. It
   cannot see Western scenery, though: the Million Dollar Highway scores 5.0/10,
   and relief sits at its cap on 47% of Colorado byway km. Fixing that needs new
   components and real drives in each kind of landscape.

**Today's hardware is enough; today's code isn't.** As written, the code
stretches to three or four more New England-sized regions. The 24 GB box can
hold and serve the whole US once three things change: the map is stored
compactly (about 5.5 GB, measured per node in section 9), the search is
compiled, local and stops at the destination, and directions are capped. An
earlier draft of this review put a compact US graph at 15-20 GB, needing a
bigger machine. That was an estimate, and measuring it showed it was about 3x
too high.

## 1. How big is the US graph?

`count_graph.py` replays graph.py's rules without building anything:

- the drivable filter and the access rule;
- oneway inference;
- splits at shared nodes, and the drop of segments under 1 m;
- the largest strongly connected component.

**On the New England extract it reproduces the shipped graph exactly:
794,685 nodes and 998,252 edges.**

| Measured | Graph nodes | Edges | OSM km |
|---|---:|---:|---:|
| New England (6 states) | 794,685 | 998,252 | 232,453 |
| Colorado | 398,656 | 515,191 | 169,977 |
| California | 1,527,476 | 1,942,632 | 378,139 |

California alone is 1.9x New England.

Counting all 12.0 GB of state extracts wasn't practical: Geofabrik ran at
0.05-1.9 MB/s. So the other states come from a fit on FHWA Highway Statistics
2023 (HM-20) public road length: 5.70 nodes per urban km and 2.46 per rural km
(`fit_us.py`, leave-one-out error 13% per state, worst 23%).

**US, 50 states + DC: ~23.4M nodes and ~29M edges, 29.5x New England.** The
plausible range is roughly 19-28M. The largest states are Texas (~1.9M,
fitted), California (1.53M, measured), Florida (~0.95M) and Illinois (~0.84M).

## 2. What today's router costs at that size

Measured on the dev Mac (Apple M2), single-threaded scipy, exactly as shipped.
The serving box's cores are slower, so read these as relative numbers.

| | New England | Colorado | US as one graph |
|---|---:|---:|---:|
| nodes | 0.79M | 0.40M | ~23.4M |
| load time | 53 s | 19 s | ~25 min *est.* |
| RSS after load | 3.7 GB | 2.2 GB | ~88 GB *est.*, plus caches |
| scenic search (pref 1) | 417 ms | 167 ms | **24-26 s** |
| route-options plan, median | 1.14 s | 0.46 s | 30-40 s *est.* |
| fastest arm (A*), median | 100 ms | 44 ms | depends on landmarks |
| 60 km loop, median | 0.84 s | 0.41 s | about the same (searches a disc) |

- **Scenic search at US scale was measured, not extrapolated.** It ran on 29
  linked copies of the New England pref-1 graph (23.3M nodes, real weights and
  topology). Results: 0.38 s at 0.8M nodes, 3.6 s at 3.2M, 12.5 s at 9.6M and
  24-26 s at 23.3M.
- **RSS fit.** 0.73 GB plus 3.7 KB per node, fitted from the two loads.
- **Per-request work outside the search.** Each request also re-blends scores,
  computes weights, takes pair minima and builds the CSR over the whole graph:
  53 ms on New England, about 1.6 s at US scale.
- **Where the memory goes (New England, `mem_breakdown.py`).**
  - Edge geometry as shapely objects: 1.1 GB for 9.4M coordinates, about 115 B
    each against 8 B as float32 pairs.
  - A projected copy of that geometry: 0.56 GB.
  - String columns: 0.42 GB.
  - The routing arrays themselves: 0.40 GB.
  - A Python dict from node id to index (2-3 GB at US size).
  - So the routing data is a small share of the total. Measured since
    (section 9): the arrays a compiled search needs are 90 MB for New England
    (113 B per node). Everything else for turn-by-turn and drawing packs into
    97 MB raw (122 B per node). That's about 230 B per node, roughly 5.5 GB for
    the US, against today's 4.6 KB per node.
- **Regional shards don't rescue today's code.** Census divisions are 2-5x New
  England: East North Central is 3.4M nodes and South Atlantic 3.7M. Under
  today's code each needs 13-15 GB and 3.7-4.3 s per scenic search. Shards
  would have to be New England-sized, which means 25-30 of them and about
  120 GB of RAM in total.

## 3. Search: what scales and what doesn't

**Stopping the search early, exactly, is not enough** (`profile_scenic.py`).

- scipy's `dijkstra` takes a `limit`. Using the scenic cost of the fastest route
  as that limit is exact: the routes were identical on 24/24 trips.
- It still settles 23% of New England for trips under 60 km, and 76-93% beyond
  that.
- The reason: under the scenic cost, the search reaches far along cheap, pretty
  roads before it can stop. Even the ideal limit (the optimum's own cost)
  settles 51% at the median.

**Restricting the search to a corridor is what works** (`corridor_excess.py`,
`corridor_search.py`).

How far routes stray: for each route, take the worst-case point v and measure
|s v| + |v t| - |s t|, its detour beyond the straight line.

| Route | New England, 150 trips | Colorado, 150 trips |
|---|---|---|
| Scenic (pref 1) | p50 4.3 km, p99 34 km, max 50 km (at most 0.49 of the trip distance) | p50 9 km, p99 73 km, max 85 km (at most 0.35 of the distance) |
| Fastest | at most 0.50 of the distance | at most 0.50 of the distance |

The scenic routes are about the same length as the fastest ones (median km
ratio 0.95-1.08). That's because the scenery penalty is charged per km.

An ellipse around the trip with a detour allowance of half the trip distance
plus 20 km held all 300 sampled scenic routes and all the fastest ones.
Searching only that subgraph returned the whole-graph optimum on 80/80 trips:
the cost ratio was exactly 1.000000. It took 30% (New England) and 39%
(Colorado) of the full search time.

That corridor's size depends on trip length and local road density. It does not
depend on the size of the map:

| Trip (straight line) | Corridor area | Nodes at NE density (4.9/km²) | Nodes at US mean (2.6/km²) | scipy search *est.* |
|---|---:|---:|---:|---:|
| 100 km | 18,000 km² | 90k | 47k | ~30-50 ms |
| 300 km | 134,000 km² | 650k | 340k | ~0.2-0.3 s |
| 500 km | 354,000 km² | 1.7M | 0.9M | ~0.5-1.4 s |
| 1,000 km | 1.37M km² | 6.7M | 3.5M | ~4-8 s |

So trips up to about 500 km stay near today's latency, and cross-country trips
don't (section 4 covers those).

Caveats:

- **It's empirical, not proven.** A strong scenic attractor next to a dull
  plain could pull a route further out. Production code should check its own
  answer, for example by widening the corridor when the route touches the
  boundary.
- **Corridor extraction has to be O(corridor).** My prototype masks the whole
  graph, which costs O(E): about 1-1.5 s at US scale. The clean version is a
  compiled (numba/Cython/Rust) Dijkstra over the global arrays. It would test
  each node against the ellipse and price each arc lazily from
  `pref_matrix`, so no whole-graph pass is left per request, and every other
  module keeps its global indices.

## 4. Splicing at US scale

**What already scales:**

- **The switch-point protocol.** An option's leave/rejoin points are
  lat/lon/heading, never node ids. So any leg can be answered by whichever
  process or box covers it, which is exactly what sharding needs.
- **The splice arithmetic.** Up to 250 switch points priced in O(K²) costs the
  same whatever the graph size.

**What doesn't:** the plan's three searches. Those are S at pref 1, plus two
fastest-route trees capped at S's travel time. On New England the trees alone
take 0.6-0.7 s for trips over 100 km. Inside the corridor they shrink with the
trip.

**New method for long trips: windowed splicing.**

1. Compute the fastest route (A* or CH).
2. Cut it into windows of about 150 km.
3. Find one local scenic alternative per window, inside that window's own
   corridor. Each is about as big as a 150 km New England search.
4. Choose a set of non-overlapping detours under the extra-time budget. The
   detours are independent, so this is a knapsack, and greedy by beautiful km
   per extra minute is fine.

Cost grows linearly with trip length and parallelises across cores. It reuses
options.py's leave/rejoin model as it stands. It gives up global optimality,
which doesn't matter for a road trip.

**Further out: a scenic-stretch catalogue.**

- Precompute, per region, the maximal high-scoring stretches, with km per
  scenery component, so a user's beauty weights re-score them live.
- Build options as fastest(s -> a) + stretch + fastest(b -> t).
- Each request then needs only fixed-metric fastest queries, which a CH engine
  answers in about 1 ms. That's the route to engine-class scale.
- It's a redesign, not a port.

## 5. The pipeline outside New England: Colorado, end to end

Only the elevation bounding box needed changing (it is hard-coded to New
England; see `run_elevation.py`).

| Stage | Time | Peak RSS |
|---|---:|---:|
| extract | 232 s | 3.5 GB |
| elevation (1,656 Terrarium tiles) | 299 s | 4.0 GB |
| landcover (8 WorldCover tiles, streamed from eu-central-1) | 967 s | 4.4 GB |
| score | 416 s | 3.2 GB |
| graph | 205 s | 4.1 GB |
| closures | 31 s | 1.5 GB |

That's 36 minutes and 1.1 GB on disk, so region-sized builds are routine.
**Full-US builds** need two things this Mac doesn't have:

- About 100 GB of disk. This Mac has 19 GB free.
- ~~A tiled elevation stage~~ (corrected: only a whole-country mosaic needs
  one, and state-by-state builds never make one). The contiguous US's bounding
  box at zoom 11 is about 60,400 tiles; the state outlines need 35,778.

**Defects that New England never exercised:**

1. **Seasonal closures are missing for famous passes.**
   - Caught from OSM tags: Independence Pass (36.8 km), Mount Blue Sky, Kebler
     and Cottonwood.
   - Missed: Trail Ridge Road has 81 km in the graph, closes every winter and
     scores 7.47, but 0 km are in the seasonal table. Old Fall River Road and
     the Engineer, Cinnamon and Boreas passes are also unmarked.
   - **Corrected:** Trail Ridge *is* tagged, and the parser rejects "Oct 14th".
     Its `vehicle=permit` puts 66.8 km in the all-year closed table, so it is
     shut every day of the year. In July, Estes Park to Grand Lake takes 219 min
     instead of 93.
   - National sources exist: the Forest Service's Motor Vehicle Use Map roads
     layer (national, CC-BY, with seasonal designations) and NPS road status.
2. **The best-ranked roads are 4WD tracks.**
   - Colorado's top-scoring named roads are Yankee Boy Basin (9.82), Camp Bird
     (9.78), Nellie Creek (9.68) and Engineer Pass (9.42). These are
     high-clearance or 4WD roads, tagged `smoothness=bad`/`very_bad`, and
     Engineer Pass is even `highway=tertiary`. The pipeline reads neither
     `smoothness` nor `4wd_only`.
   - 40.7% of Colorado's drivable km is tagged unpaved. The 1 min/km dirt
     penalty is all that keeps a sedan off a jeep road.
   - 1,971 km carry `4wd_only=yes` or `smoothness` of very_bad or worse.
3. **The byway allowlist misses most of Colorado's byways, and one rule adds
   a highway.**
   - Colorado tags all 26 state byways `network=US:CO:Scenic`. The allowlist
     knows only New England's networks, so 15 of 26 are missed, the San Juan
     Skyway (Million Dollar Highway) among them.
   - Meanwhile the `scenic=yes` clause admits the whole US 34 route relation:
     425 km flagged as byway, most of it eastern plains.
4. **Speeds are low.**
   - Tagged posted speeds run 19-28% above the New England-fitted defaults in
     every rural class: trunk 89 vs 64 km/h, primary 77 vs 59, secondary 67 vs
     53, tertiary 58 vs 47, unclassified 50 vs 37.
   - 80-97% of tertiary and unclassified km is untagged, so ETAs there likely
     run 20-35% long. That assumes the untagged roads resemble the tagged ones,
     and gravel is driven below its limit, so a drive would have to confirm it.
   - graph.py's own method, a length-weighted harmonic mean over tagged
     roads, can be rerun per state automatically.
5. **Elevation has inland spikes.** Three blobs of corrupt Terrarium pixels
   inside Colorado, down to -639 m, create 2,300-4,536 m of fake relief
   (corrected: the 100 m relief cap absorbs most of it here). The
   filter only rejects values below -11,000 m, because in New England a
   negative value is just ocean.
6. **Distances use the Massachusetts state-plane projection.** The length
   error is under 0.5% across most of the contiguous US, but 2.1% in Austin,
   3.9% in Miami, 4.5% in Key West and 6.3-6.6% in Hawaii and Alaska.
7. **Other things that are New England-bound:**
   - Closure dates are judged in America/New_York.
   - The NH/VT/MA/ME state road classes are bespoke ArcGIS integrations, one
     per state. National substitutes: TIGER/Line MTFCC S1500 (4WD trails),
     Forest Service roads, BLM roads.
   - ALT's 16 landmarks were placed for one region.

## 6. Does the scenery model transfer?

- **Proxy test (`byway_auc.py`).** The only independent label available
  everywhere is official byway designation. I measured the length-weighted AUC
  of the score, with its own byway term removed: the chance that a random km of
  designated byway outscores a random km of other road of the same classes
  (trunk to tertiary).
  - New England (38 routes): 0.619. Colorado (all 26 state byways): 0.661.
  - Share scoring 7 or more: New England byways 29% against 11% of other
    roads; Colorado 23% against 6%.
  - So the score doesn't collapse in Colorado, but it was only moderate to
    begin with.
- **The absolute scale shifts.** Colorado's mean is 3.69 against New England's
  4.57, and the share of km at 7 or more is 6.3% against 11.0%. Fixed
  thresholds such as `BEAUTIFUL_SCORE = 7` mean different things in each
  region.
- **Scenery types it can't see:**
  - Forest: half of `c_forest` is WorldCover tree cover, which is about zero on
    most Western roads (median tree fraction 0.00; 57.8% of km at 0).
  - Relief: `RELIEF_FULL = 100 m` pins 16.4% of all Colorado km and 46.6% of
    its byway km at the maximum (New England: 5.7% and 20.6%), so relief can't
    rank mountain roads.
  - The result: iconic Western drives land mid-scale. US 550 (Million Dollar
    Highway) scores 5.0, CO 141 (Unaweep-Tabeguache) 5.1 and Rim Rock Drive
    6.6. Only Trail Ridge Road (7.5) clears 7, partly on byway credit.
- **What it needs:**
  - Components for open vistas or viewshed, rock and desert (WorldCover
    bare/sparse and shrub), protected-area designation (PAD-US, NPS) and
    canyons (relief derivatives).
  - Per-landscape calibration against real drives.
  - That's months of drives, not code.

## 7. App and operations

- **App gating is concentrated in a few files:**
  - `NewEngland.swift`, plus the generated boundary, which comes from Census
    state outlines and can be regenerated for any set of states;
  - the `Region.swift` camera;
  - `OutsideNewEnglandView` and the strings;
  - one baked API base URL, with 15/20 s timeouts.

  That's a few days' work. Having the server publish its coverage polygon would
  be better than hard-coding it.
- **There's no on-device routing.** Every reroute needs the server. Much of the
  rural West has no signal, so failed reroutes will be far more common than in
  New England.
- **Hosting:**
  - Today's code on a 24 GB box (the Oracle Always Free ceiling) holds about
    4-5 New England-sized processes, each 3.7 GB plus its loop and options
    caches. That's about 3-4M nodes, roughly 15% of the US. The box's slower
    cores make every latency above worse.
  - A compact US graph (~5.5-6 GB *est.*, section 9) fits today's 24 GB box.
  - A 128 GB Hetzner AX102 lists at about EUR 104-133/month in 2026
    third-party listings (memory prices are moving, so check Hetzner directly).
  - Region-by-region builds peaked at 4.4 GB for Colorado. Building the whole
    country needs about 100-150 GB of disk, plus 32-64 GB of RAM to run regions
    in parallel, for a few hours.

## 8. Paths

| Path | What | Gets you | Effort *(judgment)* | Running cost |
|---|---|---|---|---|
| A. Regional add-ons | Today's code; extra New England-sized regions as their own processes | 3-4 more regions on the free box | 1-2 weeks for the first region including the section-5 fixes, then days each | $0 |
| B. Sharded US | 25-30 New England-sized shards with overlapping halos, plus a dispatcher | The whole US; trip length capped by the halo | A, plus a dispatcher and ops | ~120-150 GB of RAM, about EUR 200-270/month |
| C. One lean graph + corridor | Flat arrays, compiled corridor Dijkstra, grid index, windowed splicing for long trips | The whole US at today's latency for trips up to ~500 km | Roughly 4-6 weeks of engineering plus validation | Today's 24 GB box (~6 GB used) |
| D. Engine rebuild | Scenic-stretch catalogue over a CH engine (OSRM/GraphHopper) | Any trip length | Months | Small |

**Recommendation:**

- Take path C if the goal is "anywhere in the US".
- The section-5 data fixes are a prerequisite on every path.
- Run the scenery model as its own track, since it sets the calendar.
- Prove all of it on one Western region first. Colorado is a good test: it has
  plains, mountains, desert and seasonal passes. Drive it, then widen.

## 9. Moving the work: the phone, one-time costs, a distance cap

Added 2026-10-11. All three measured with `package_size.py`,
`export_search_graph.py` and `bench_device_search.swift`.

**What the work actually is.** Each request does three things:

1. Re-colours every road with the user's sliders.
2. Searches outward from the start.
3. Reads off the best route to the destination.

Today step 2 covers the entire map whatever the trip, and the map is held as
Python objects at 4.6 KB per node. Those are two separate problems: how much
of the map each request touches, and how the map is stored.

**A directions cap, like loops: yes, but only together with a local search.**

- A cap alone changes nothing today. A 20 km route on a US map would still
  search the whole country.
- What buys the speed is a compiled search that stops at the destination and
  ignores roads outside the trip's corridor.
  - New England, 40 trips, two runs: whole graph 115-163 ms, stop at
    destination 55-69 ms, plus corridor **37-43 ms median, 69-81 ms p90**.
  - Colorado: 45 / 15 / **9.5 ms**.
  - The answer was identical to scipy's whole-graph optimum on every trip.
  - Recomputing every weight for new slider settings takes 12 ms (New England)
    and 6.6 ms (Colorado).
- The cap then bounds the worst case however big the country is. At 300 km
  straight line the largest corridor is ~134,000 km², at most ~1M nodes even in
  dense metros, so roughly 0.1-0.25 s.
- Pair the cap with a route-length rule (a route may not exceed the corridor's
  length budget) and the shortcut becomes provably exact, the same argument
  loops use for their disc.

**One-time precomputation: partly.**

- Already one-time: every road's scenery score.
- Worth adding:
  - **A compact map file built by the pipeline.** About 230 B per node, so
    ~5.5 GB for the US. It loads in seconds by mmap, instead of today's 53 s
    and 4.6 KB per node.
  - **Cache the default-slider weights and graph.** Today they're rebuilt per
    request, which costs 53 ms on New England and about 1.6 s at US scale.
  - **Contraction hierarchies for metrics that never change**: the fastest
    route, and pref 1 at default beauty weights, which is the base S of every
    options plan. Those queries become about 1 ms. Building them needs a
    compiled library.
- Can't be precomputed: arbitrary slider combinations, which are infinite.
  Those keep the per-request search, which is cheap once it's local.

**The phone doing the routing: feasible on the numbers. The cost is a port.**

| Region pack | Raw (mmap'd on the phone) | Compressed download |
|---|---:|---:|
| New England (measured) | 97 MB | **42 MB** |
| Colorado (measured) | 43 MB | **17 MB** |
| California (est., 1.53M nodes) | ~180 MB | ~75 MB |
| Whole US (est., 23.4M nodes) | ~2.7 GB | ~1.1 GB |

- What a pack holds: graph, travel-time inputs, the scenery vector, names,
  refs and signs for turn-by-turn, drawable geometry, restrictions, closures,
  closed roads, state classes and neighbourhood flags.
- The parking-lot access layer, used for destination snapping, adds another
  76%. It could be simplified or left on the server.
- Search arrays come to about 90 MB for New England, so a region sits at
  roughly 100-200 MB in memory. Searches take tens of milliseconds on an
  M2-class core; a recent iPhone is in that class, older phones somewhat
  slower.
- Wins:
  - no per-user server cost;
  - planning and rerouting work with no signal, which matters for the rural
    West;
  - coordinates never leave the phone.
- Cost:
  - the router rebuilt in Swift: weights, splits, closures, the private rule,
    snapping, turn-by-turn, options, loops, about 5,000 lines of Python
    behaviour;
  - pack building, hosting, versioning and updates;
  - two implementations to keep in sync unless the server goes away.
- That's roughly 2-3 months (*judgment*). The Python server is a ready-made
  oracle for parity tests.
- **A small first step: drive packs.** At plan time, ship the graph within
  ±10 km of the planned route, about 1-2 MB, so reroutes work offline.

**None of these fix the data.** Trail Ridge Road, the 4WD tracks, the byways,
speeds and Western scenery (sections 5-6) are the same problem wherever the
search runs.

**Order this suggests:**

1. A compact map file plus a compiled local search with stop-at-destination
   and the corridor, and a directions cap (e.g. 300 km) beside the existing
   400 km loop cap. That makes the current box US-capable with bounded cost
   per request.
2. Regions one at a time, with the section-5 data fixes, starting with a
   Western state.
3. Optionally, on-device routing: drive packs first, then full region packs.
   Write the compiled core once (Swift or C) so the server and the phone share
   it.

## Method notes

- `count_graph.py` is checked against the shipped New England graph (exact),
  and against graph.py on Colorado (exact: 398,656 / 515,191).
- State counts: the six New England extracts of 2026-08-25, Colorado and
  California from Geofabrik on 2026-10-10, and FHWA HM-20 2023 for the rest
  (`fhwa_hm20.py`).
- Router timings: dev Mac (M2, 24 GB), one process; a download and other
  benchmarks ran alongside part of the time.
- Not measured:
  - a full options plan on a corridor subgraph (only the scenic search was
    tested);
  - the serving box's CPU;
  - Plains and Southern road density (fitted, not counted);
  - anything in the iOS app beyond reading its code.
- Colorado build: `run_elevation.py` with bbox `-109.4,36.75,-101.6,41.55`,
  `landcover.py --stream`, `score.py --no-cache`. The processed directory was
  kept in the session scratchpad, not in the repo.
