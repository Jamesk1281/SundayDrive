# The router at US scale

**Status:** day one, 2026-10-18, on branch `claude/us-scale-router` off `usa`.
Nothing has been built yet. This section is the dated plan. Measurements
replace the estimates below as they land, and each section says which it is.

The design is path C of [usa-extension-feasibility.md](usa-extension-feasibility.md)
§8: one compact graph in memory, and each route searched only inside an ellipse
around the trip. Point-to-point trips are capped at 500 km straight line.

## The earliest honest date

**The router, options, loops and reroutes on the compact graph and corridor
search, with New England parity proven and US-scale numbers from a synthetic
graph: Friday 23 October.** Thursday 22 is possible if parity turns up nothing
that needs explaining. It probably will turn something up, so plan on the 23rd.

**Measured on `data/processed-us`: one day after it exists.** Most of that day
is building the compact pack from it (the pack is described below), plus one
measurement pass.

For a submission on Thursday 29 October, the server has to be on the box with
the US data by about Monday 26 October, so the app can be tested against it.
That works only if the US data arrives by about Saturday 24 October, and if the
box has been resized (next section).

### A correction to the premise: the box has 8 GB, and the ceiling is 12 GB

The feasibility review and the launch plan both size the US against a **24 GB**
box. The box in the repo's own measured records is smaller:

- `server/DEPLOY-oracle.md` (executed 2026-09-28/29): `VM.Standard.A1.Flex`,
  **2 OCPU, 8 GB**, chosen "deliberately not 12".
- `docs/hosting-status-2026-09.md` and `docs/hosting-independent-review.md`
  (C19), both checked against Oracle's page on 2026-09-28: the Always Free A1
  allowance is **2 OCPU / 12 GB**.
- `docs/load-test-oracle.md`: resizing to 12 GB "costs a stop/start, and
  Ashburn's A1 capacity is not guaranteed at the moment of the resize".

24 GB was Oracle's older A1 allowance. So the hard ceiling at $0 is 12 GB of
RAM and two A1 cores, each about three quarters the speed of the Mac's M2
cores (`DEPLOY-oracle.md`, Part 13).

What this changes:

- **The design still holds, but the margin is gone.** The review put a compact
  US graph at 4.4–5.5 GB. Add the access layer (parking lots, used to place
  destinations), each request's working set, the loop and options caches and
  Python itself, and an all-in-RAM US router would sit at or over 12 GB.
- **So the bulk of the graph will be memory-mapped from disk, not loaded.** A
  one-time *pack* step turns a processed directory into flat arrays. The server
  maps them read-only, so geometry, names and the search arrays are
  file-backed pages. The kernel can drop those pages under pressure; they do
  not count against the box the way built Python objects do. What stays truly
  in RAM is small: each request's corridor, the caches, a few dicts. The
  target is **peak anonymous memory (what the kernel cannot drop) under 6 GB
  under concurrent load**, reported beside total RSS. That works on today's
  8 GB box. The 12 GB resize then becomes headroom rather than a
  requirement. That target is a goal, not a measurement yet.
- **Someone has to decide about the resize.** It isn't mine to do, since
  deploying is the master session's job. If the 6 GB target holds, the resize
  is optional.

### What could move the date

1. **New England parity takes longer than a day to explain.** The corridor is
   empirical (the review found it exact on 80 of 80 trips, not on all trips).
   Snapping without shapely's tree may break ties differently. Every difference
   gets explained, and each one costs time.
2. **Long loops in dense places.** Loops keep their 400 km limit. A 400 km
   loop searches a disc 440 km in radius. In New England that disc already is
   the whole graph, about eight whole-graph searches, 3–4 s on the box. Around
   New York the same disc holds several times more road. If the synthetic
   measurement puts it past the app's 20 s limit, I'll report it with a
   proposed fix. The limit is not mine to change.
3. **The trip's time zone.** Seasonal closures are dated in New York time
   (`router.py:484`). Nationally the date has to come from where the trip is.
   `timezonefinder` isn't installed, and adding a dependency to the box is a
   deploy decision. The fallback is to close a road if it is closed on any US
   date at that moment. That is never more than three hours early, and it errs
   toward closed.
4. **The US data's date.** That date belongs to unit A.

## Plan, by day

| Day | Work | Done when |
|---|---|---|
| Sun 18 Oct | The fixed New England trip set and its oracle answers from today's router. A synthetic US graph builder. This document. | Oracle answers saved; the synthetic graph loads |
| Mon 19 Oct | The pack (flat arrays, memory-mapped) and a `Router` that loads it. Snapping through a grid index, without a shapely tree over every road. | Same snaps and same whole-graph routes as the oracle on the trip set |
| Tue 20 Oct | Corridor search for routes, both arms, and reroutes. Weights priced per corridor, never per graph. Corridor nodes from a spatial grid, so the cost is O(corridor). Widen the corridor when a route touches its edge. The 500 km cap. | Route parity on the trip set; US-scale latency by trip length |
| Wed 21 Oct | Options (`plan`, `spliced_route`) and loops on corridors and discs. Cost models and loop fields cut to the disc, not the graph. | Options and loop parity |
| Thu 22 Oct | Server: dates from the trip's location, national messages, the cap's error. RSS under concurrent load on the synthetic graph, with replicates. | Numbers in this document |
| Fri 23 Oct | Buffer, and explaining every parity difference. | Suite green; this document final for New England and synthetic |
| A's date + 1 | Pack `processed-us` and measure on it. | The US table filled in |

## Constraints this work keeps

- Today's router on `data/processed-ne` is the oracle. New England must route
  the same, with every difference explained, because it holds the only ground
  truth.
- No whole-graph pass per request. Corridor extraction, weights and search are
  all O(corridor).
- scipy first. numba isn't in the venv; it gets added only if measurement shows
  scipy is not enough, and it would have to install from a wheel on aarch64
  Linux under the box's Python 3.12.
- No changes to the pipeline build files, `closures.py` or `ios/`.

## What was built

### The pack

`Router(processed_dir)` used to read the graph into geopandas frames, a shapely
object per road twice over (lon/lat and projected), an STRtree over them, and a
Python dict from OSM node id to index. Today it reads the parquets into flat
arrays (`pipeline/compact.py`):

- **text** columns (name, ref, highway, junction, destinations, exit numbers)
  as int32 codes into one UTF-8 blob of distinct values;
- **geometry** as int32 lon/lat in 1e-7 degrees, OSM's own precision, so the
  round trip is exact (checked on all 9,390,733 New England vertices);
- **grids** in degrees: nodes by 0.1-degree cell, for corridors and loop discs;
  road bounding boxes by 0.01-degree cell, for snapping. New England's roads
  sit in 1.37 cells each on average.

Snapping keeps its code. `_edge_tree` and `_edge_geom_m` are now objects that
answer the same two questions STRtree answered (nearest line, lines whose box
meets a box) and build a projected shapely line only for the roads asked
about, through the same transformer geopandas used, so the metres are the same
to the bit. `idx` is a binary search over the sorted node ids.

`tools/us_scale_router/pack.py` writes those arrays to a directory, and
`SUNDAYDRIVE_PACK` makes the server map them instead of building. The arrays
every search reads are loaded into memory. The rest (geometry, names, the
access layer) is paged from disk as requests touch it. Paging the search arrays
too would gain nothing: OSM node ids are not spatially ordered, so a long
corridor touches nearly every page of them. A pack records a fingerprint of
each file it was built from, and the server refuses a pack that no longer
matches the parquets beside it, as it refuses a stale closures table. It also
names its region, which is where the server's coverage messages get it from.

| New England | today's router (`usa`) | this branch, built | this branch, pack |
|---|---:|---:|---:|
| load | 35 s on 2026-10-18, 53 s in the review | 27–44 s | **1.6–1.8 s** |
| peak memory while loading | 4.4 GB (`docs/hosting-status-2026-09.md`) | 2.1–2.3 GB | pack mapped |
| on disk | 382 MB of parquets | — | 0.58 GB |

### Corridor search

Every route, every arm, reroutes, option legs and loop rejoins search an
ellipse around the trip: nodes v with |s v| + |v t| <= d + 0.5 d + 20 km in
great-circle km between junctions (feasibility §3). The cost of a request now
follows the trip, not the map:

- **The corridor's nodes** come off the node grid: whole cells inside the
  ellipse are taken, whole cells outside are skipped, and only cells the edge
  crosses are tested node by node.
- **Its matrix** is each corridor node's own row of the pair CSR, kept where
  the head is inside. It is the whole graph's matrix cut down, neighbour order
  included (tested), so scipy breaks ties the same way.
- **Its prices** come from a `Metric`, which applies `_edge_scores` and
  `_weights` to the corridor's slots only, in the same arithmetic. A subset's
  prices equal the whole graph's to the bit (tested). Private, closed and
  seasonal slots are read from one flag byte per slot.
- **The check.** A route whose worst point comes within 90% of the allowance
  is searched again with twice the room, up to twice. This is what the review
  asked for. It is evidence and not proof: squeezed to a few km, the Mass Pike
  fits without touching, so a corridor that narrow keeps it where the scenic
  route strays further. The allowance is what makes the answer exact; the
  check catches the routes it bends.
- **The fastest arm's A\*** is gone. Its landmark tables would be about 2.5 GB
  for the US, sixteen landmarks bound a continent much worse than a region,
  and the corridor already makes the fastest arm local.

### Options

`plan` runs its three searches (S at pref 1, the forward and backward fastest
trees) in one corridor, chosen and widened for S. `spliced_route` searches each
leg in that leg's own corridor. The whole-graph pref-0 matrices that
`_fastest_graphs` cached, about 80 MB each on New England and 2 GB each on the
US, are gone.

### Loops

A loop's two passes already ran over a disc around the start, with a proof
that each candidate's paths are the whole graph's (`docs/loop-speed.md`). What
was still whole-graph was everything around the disc: the cost model (82 MB on
New England, about 2 GB each on the US, two per planner and two planners), the
fields spread to the whole graph's size, the mask that cut the disc, and every
build's search home. Now:

- the disc is cut from the node grid and the graph's forward and transposed
  rows;
- its cost model prices only the pairs it touches;
- the fields keep disc-local arrays, with whole-graph views built only when a
  test asks for them;
- a build re-prices only the pairs the drive out used. It searches home inside
  the disc and proves the answer: any way home that leaves the disc must come
  back in, and the back field already bounds that. A disc that cannot prove a
  build is searched twice as wide.
- A disc that cannot prove its candidates is cut again twice as wide instead of
  being replaced by the whole graph. On New England the doubled disc is nearly
  always most of the graph, so it becomes the whole graph as before. On the US
  it never is, so after two doublings the last disc is kept and its unproved
  candidates are left out.
- The field cache is capped at 6M nodes searched as well as at four entries.

The loop rejoin (`via`) searches each leg in its corridor, and the K-1
rejoiner's whole-graph cost models are gone with the rest.

### Closure dates

Seasonal closures were dated in New York time. A road is now closed if it is
closed on any date the contiguous US is on at that moment (`region_today`).
That is one date except in the three hours after midnight Eastern. A window
can therefore start up to three hours early in the West and end up to three
hours late in the East, always overnight and always toward closed. No time-zone
lookup and no new dependency.

### The cap and the messages

`/api/route` refuses a point-to-point trip longer than 500 km in a straight
line between the snapped ends, before any search. The reply is a 400 with
`code: "TRIP_TOO_LONG"`, `km` and `max_km`, and an `error` the app shows as
written:

> That trip is 412 miles in a straight line. Sunday Drive plans drives of up
> to 311 miles, so pick a stop along the way and plan it in two parts.

A reroute (it carries a heading or a declined U-turn) gets 650 km instead. A
driver who has wandered past the cap mid-drive is better served slowly than
refused. A loop's rejoin is bounded by the loop.

The coverage refusals are sentences now ("Sunday Drive covers the contiguous
United States, and that point is outside it."), with the region taken from
`SUNDAYDRIVE_REGION`, else the pack's own region, else "New England". Unit C's
app passes `error` through verbatim (`RouteService.failure`).
