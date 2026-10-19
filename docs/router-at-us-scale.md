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

## New England parity

`tools/us_scale_router/parity_run.py` replays one fixed request set through a
checkout's own server (Flask's test client), and `parity_diff.py` compares two
runs answer by answer. The oracle is the `usa` code at `6fdf137`, on
`data/processed-ne`.

**The set: 726 requests.** Forty-six trips, random junctions moved up to 30 m
off the road, in bands of 2–20, 20–60, 60–150, 150–300, 300–500 and 500–650 km.
Each one is asked:

- at pref 0, 0.5 and 1, with other beauty weights, with dirt roads avoided and
  ignored, and in winter;
- as an options plan, and each option's fetch by its switch points;
- as a reroute with a heading and as a declined U-turn, both 30% along the
  route, and as a reroute along an option.

Fifteen starts each ask for loops of 15, 40 and 120 km, a winter loop, a loop by
compass sector and a loop rejoin; two ask for 300 km. Separately, 3,000 snaps
are compared: nearer end, with a heading, and as a destination.

| | requests |
|---|---:|
| identical, every byte of the JSON | **677** |
| over 500 km, answered by the oracle, refused with `TRIP_TOO_LONG` | 44 |
| a different route | 5 |

Every loop, loop rejoin, options plan and option fetch is identical. The five
that differ are all reroutes with a heading:

- **Three (#37, #603, #604) come from the heading correction.** The driver's
  heading is now turned from true north to the projection's grid before it is
  compared with a road, and in New England that turn is 0.3–2.3 degrees. With
  the correction switched off, all three are identical to the oracle's.
- **Two (#519, #520, one trip) are a tie.** The reroute's origin lies exactly
  on a vertex three roads share, at distance 0 from all of them. STRtree's
  choice among equidistant geometries is undefined; the new index takes the
  lowest edge. Both edges pass the same alignment test.

Of the 3,000 snaps, 2,973 are identical. All 27 differences are in the snap
with a heading. 24 are the heading correction (identical with it switched off),
and 3 are the same kind of tie, a point equidistant to several roads at a
junction vertex.

**Latency against the oracle**, CPU seconds per request, same requests, same
machine, load about 3 (this Mac is shared; `cpu` beside wall in every answer):

| kind | oracle p50 / p90 | this branch p50 / p90 |
|---|---:|---:|
| route, pref 0 | 0.15 / 0.47 | 0.21 / 0.62 |
| route, pref 0.5 | 0.62 / 0.90 | 0.31 / 1.00 |
| route, pref 1 | 0.63 / 0.90 | 0.35 / 1.01 |
| options plan | 1.35 / 1.60 | 0.66 / 1.86 |
| option fetch | 0.71 / 1.31 | 0.31 / 1.10 |
| reroute | 0.58 / 0.85 | 0.23 / 0.94 |
| declined U-turn | 1.06 / 1.72 | 0.59 / 1.61 |
| loop | 0.41 / 2.23 | 0.31 / 2.51 |
| loop by sector | 0.78 / 1.28 | 0.88 / 1.41 |
| loop rejoin | 1.73 / 1.95 | 0.14 / 0.36 |

- **Medians halve.** A typical New England trip's corridor is a fraction of the
  region.
- **The p90s are within 15%.** The longest trips' ellipses hold most of New
  England, so they are searched as the whole graph, as before.
- **The fastest arm alone is a little slower** (0.15 to 0.21 s): it lost its A*.
  A plan now searches its scenic arm first and bounds the fastest arm's search
  by the scenic route's pref-0 cost, which is exact and wins most of that back.
- **Rejoins are 12 times faster.** They searched the whole graph twice.

## Measured on the US

`data/processed-us` (unit A, delivered 2026-10-19): 20,023,955 nodes,
25,849,861 edges, 20,186,995 routing nodes after the splits.

**Packing it** (`tools/us_scale_router/pack.py`, on this Mac) took 326 s to
build and 26 s to write, at a peak RSS of 14.4 GB. The pack is **13.5 GB** on
disk. It has to be built on a machine with more than 16 GB, not on the box.

**Fixed while packing: turn restrictions were about to be switched off for the
whole country.** `_keep_network_reachable` thins the turn-restriction splits
that would leave a junction unreachable, and blames a split only when its
removed exit points straight at the stranded junction. On the US graph, 33
junctions were stranded two or more roads out, so nothing was blamed, and the
old fallback enforced none of the 159,431 splits. Every route in the country
could then have taken turns OSM forbids, with nothing but a warning in the
log. Now the splits at junctions near the stranded ones go instead, nearest
first (`_near_strandings`). On the US it gives up **20 of 159,431**.

| | US pack |
|---|---:|
| load, start to ready | **2.7–2.9 s** |
| resident after load | 4.7 GB RSS, 4.6 GB footprint |
| one request at a time, end of a run | 5.1–5.2 GB footprint; 10.8–11.3 GB peak RSS, most of it pages of the pack read from disk |

**Latency by straight-line trip length**, CPU seconds on this Mac, one request
at a time, eight trips per band drawn from the whole country. The box's cores
are about 1.4 times slower (`server/DEPLOY-oracle.md`, Part 13):

| trip | route p50 / p90 | options p50 / p90 | reroute p50 / p90 |
|---|---:|---:|---:|
| ≤ 25 km | 0.12 / 0.24 | 0.14 / 0.24 | 0.06 / 0.11 |
| ≤ 50 km | 0.23 / 0.36 | 0.38 / 0.64 | 0.14 / 0.23 |
| ≤ 100 km | 0.23 / 0.67 | 0.39 / 1.39 | 0.12 / 0.49 |
| ≤ 200 km | 0.54 / 0.71 | 0.91 / 1.29 | 0.27 / 0.48 |
| ≤ 300 km | 1.07 / 1.40 | 2.08 / 2.61 | 0.67 / 0.99 |
| ≤ 400 km | 1.60 / 2.13 | 3.06 / 3.96 | 0.95 / 1.61 |
| ≤ 500 km | 2.14 / 3.44 | 3.83 / 6.48 | 1.12 / 2.06 |

Trips up to 300 km stay near New England's latency, and everything the cap
allows stays well under the app's 20 s, at about 9 s on the box at worst for an
options plan. The first request after a load paid 7 s for a one-off table of
exit numbers. That table is now built from the distinct values (0.07 s).

### Loops: 400 km does not fit in the densest metros

| loop | p50 | p90 | worst seen |
|---|---:|---:|---:|
| 40 km | 0.22 | 0.46 | |
| 150 km | 1.61 | 3.23 | |
| 300 km | 3.09 | 7.74 | |
| 400 km | 8.79 | 11.22 | 17.7 (Philadelphia) |

CPU seconds, a first loop from a new start, ten random starts per length. A
400 km loop searches a disc 444 km in radius, which from Philadelphia holds
2.9M nodes. Its two passes and five builds then take 18 s on this Mac, about
25 s on the box, past the app's 20 s. New York measured 14.0 s (about 20 s on
the box), Chicago 11.8, Los Angeles 6.1 and Minneapolis 4.8. A second sector
from the same start reuses the passes and costs half or less.

Two things were done and did not close it:

- each build first searches home in the ellipse between the turnaround and the
  start (`_home_near`);
- each build is bounded by what that way home costs.

The proof that lets the small ellipse stand alone usually fails at 400 km,
because the retrace penalty makes the real way home dearer than the
unpenalised back field it is bounded by.

The brief says loops keep their limits, so the limit is unchanged. The ways to
close the gap, in the order I would take them:

1. **Cap loops at 300 km.** p90 7.7 s on the Mac, about 11 s on the box,
   everywhere. One constant (`looper.MAX_TARGET_KM`) and the app's slider.
2. **Cap the loop by what its disc holds** (for example 2M nodes), so the top
   of the slider is 400 km in Montana and less around New York. More honest
   about distance, harder to explain on a slider.
3. **Three builds instead of five above 300 km** (`SPAN_PICKS`). From the
   loop-speed table, that trades +5% against -7% worst distance error, and it
   saves about 40% of a long loop's time. It does not close New York alone.
4. **A compiled kernel** (numba). It would speed the searches by a constant,
   not change their size, and it adds a dependency to the box. Not enough on
   its own either.
