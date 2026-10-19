# The national road graph build

**Status:** delivered at 02:00 on Monday 19 October 2026, three days ahead of the
committed Thursday 22. `data/processed-us` is in the main checkout, in
`data/processed-ne`'s schema: 25,849,861 edges, 20,023,955 nodes and 7,796,108 km
for the 48 states and DC, built from Geofabrik's US extract of 2026-10-17 and scored
with E1. Built on `claude/national-build` (off `usa`), not deployed, not pushed.

- **Border proof (§3):** stitched state by state, New England matches its joint
  build edge for edge, sidecar row for row, and on 54 of 54 Connecticut River routes.
  Nationally, 2,159,473 ways cross a region border and every one is split alike.
- **New England (§4):** on the same data the method changes 2 of 300 trips, by
  0.17 km at most. Against `processed-ne` built with E1, the national build's New
  England keeps 97.9% of edges unchanged, and 245 of 300 trips are the same on the
  ground. The rest is seven weeks of OSM edits.
- **For units B, C and D (§8):** the Router's own `CRS_METERS` is still Massachusetts
  State Plane; `closures.py` crashes on a region with no seasonal road; the files'
  sizes.

## 1. The earliest honest date

**`data/processed-us` complete and checked: Wednesday 21 October 2026, end of day.
Committed date: Thursday 22 October**, which leaves room for one full rebuild of
the country if the first one turns up a defect.

What that rests on, measured on this Mac on 2026-10-18:

| step | measured | basis for the national figure |
|---|---|---|
| download `us-latest.osm.pbf` (Geofabrik, 2026-10-17) | 12.2 GB at ~5 MB/s, ~40 min | in progress at the time of writing |
| the pipeline on one region (extract, elevation, landcover, score, graph, closures) | Colorado, 385 MB of PBF: **26 min** (extract.py alone 808 s) | its own logs of 2026-10-18 |
| the same, the whole country | about 13.5 GB of region PBFs (11.8 GB of states plus a 15 km overlap ring) at Colorado's rate: **~15 h single-stream**, ~8 h at two or three regions at once | memory, not cores, bounds the parallelism (6.7 GB of RAM per GB of PBF in extract.py; elevation.py's mosaic, Texas 13.3 GB) |
| Terrarium tiles, WorldCover tiles, PAD-US landmarks | 4.1 GB, 9.1 GB, a few hundred MB | sizes from `docs/us-map-data-findings.md` §2, §6 |

The plan by day:

- **Sun 18 Oct:** download; the global junction pass; the build driver; cut the six
  New England states out of the 2026-08-25 New England extract.
- **Mon 19 Oct:** the border proof and the New England check on 2026-08-25 data
  (§3, §4), against a joint New England build from the same extract. Then cut the
  country into regions and start the national build overnight.
- **Tue 20 Oct:** finish the regions; stitch; run `closures.py` and
  `state_roads.py` per region and remap their tables onto national edge ids.
- **Wed 21 Oct:** the New England trip sample on the national graph, per-state
  counts, and delivery.

What would move the date: a defect found by the border proof that needs a
redesign (a day), a second full national run (a day), or memory pressure from
other sessions on this Mac forcing the regions to run one at a time (half a day).
Disk is the other limit. 84 GB was free on 2026-10-18, not the 116 GB
expected, so region intermediates are deleted as each region is harvested.

**Update, end of 2026-10-18.** The proof is done (§3, §4.1). All 51 regions are cut,
and the national regions are building. Measured today, on a Mac shared with three
other units' jobs (an iOS simulator, unit B's parity runs, unit D's closures):

| step | measured |
|---|---|
| download, `us-latest.osm.pbf` of 2026-10-17 | 12,212,909,513 B, md5 `bab88d207efbcba7aa2998e2076045a3` (Geofabrik's own); stalled once at 10.0 GB and resumed |
| `junctions.py`, national | 13,891,641 drivable ways, 176,221,570 references, **16,371,824 junctions**; 1,494 s, 3.7 GB peak |
| `cut.py`, 51 rings | 13 GB of region PBFs. 5 rings per pass, 133-2,611 s and 3.9-10.0 GB a pass: the slow passes ran while the Mac was swapping |
| the six New England rings (0.99 GB), every stage | 2.7 process-hours, two at a time, so ~2.7 h per GB of PBF under that load, against Colorado's ~1.1 h alone |

At those rates the 13 GB of rings take roughly 15-35 process-hours. That is about
half a day to a day and a half of wall time at two regions at once, which is what
the 14 GB memory budget allows with the other units' jobs running. **Thursday 22
October stands as the committed date. Wednesday is now unlikely.**

Disk ran short. 30 GB was free with all 51 rings cut. The US PBF is deleted, since
the junctions and rings are made from it and the md5 above identifies it.
Geofabrik will not serve that exact snapshot again, so a different cut needs a new
download, and new junctions to match.

## 2. Method

The code is `tools/national_build/` (its README has the order and how to re-run
one state). Pipeline stages run unmodified; `graph.py` gained two seams, and
`protected.py` a second input format.

**Regions.** A region is a core plus a 15 km ring around it. Cores are the 48
states and DC (Census TIGER/Line 2025, which runs out over each state's water), but
Texas and California are each cut in two because `elevation.py` holds its whole
mosaic in RAM. After the cut the largest mosaic is Montana's, at 7.2 GB. The ring is
read but never owned. Every scenery term looks at most a few km from the road
(`score.py`'s distances top out at 900 m, the desert box is 1 km, the range window
3 km), so an owned edge is scored from the same surroundings a single national
build would see.

**One read of the country, then one region at a time.**
1. `junctions.py` reads `us-latest.osm.pbf` once. It counts every node reference
   of every drivable way, each way once, with `graph.py`'s own filter, and keeps
   the nodes counted twice or more. These are the country's junctions.
2. `cut.py` cuts each ring out of the US PBF with `osmium extract --strategy
   smart`. Ways are kept whole, and the multipolygon and boundary relations
   `extract.py` reads are completed, so a national forest across a state line
   assembles in both regions.
3. `build.py` runs `extract.py`, `elevation.py` (over the ring's box), `terrain.py`,
   `landcover.py`, `protected.py` and `score.py` on each ring. Then
   `graph.build_scored_edges` builds its edges with the national junctions, so a
   road is cut at the same nodes in every region that reads it.
4. `stitch.py` keeps each edge from the region that owns its midpoint, measured in
   EPSG:5070 from the edge's lon/lat geometry, so every region computes the same
   point. It then cuts the strongly connected component, builds the node table and
   resolves turn restrictions over the whole country, and writes the edges region
   by region without ever holding them all.
5. `sidecars.py` runs `closures.py` per region, unmodified. It runs on that
   region's PBF and on a slice of the national graph: the edges the region owns,
   plus every edge meeting one of their end nodes, because `closures.py` decides
   what a barrier on a node closes from how many edges meet there. Each row's
   edge is mapped back to its national row and kept only from the owning region.
   `state_roads.py` runs once, the same way, on New England's slice.

**Projection.** The pipeline measures every length in `common.CRS_METERS`,
EPSG:26986, Massachusetts Mainland. That is 0.1% long in central Maine and 0.45%
at the top of its ring, but 2.2% long at Houston, 3.9% at Miami and 4.5% at Key
West, and grid north is 30-35 degrees off true north in the West. `stage.py` sets
`common.CRS_METERS` to a Lambert conformal conic fitted to each region's latitudes
before the stage is imported, without editing `common.py`. Measured at the corners
and mid-edges of every region's box, the conics are within 0.25% of true length;
the halves of Texas are the worst, at 0.21% and 0.17%, because each spans nine
degrees of latitude. New England's six states keep EPSG:26986, which is what
`processed-ne` was built in.

**Why not one national PBF in one process.** `graph.py` and `extract.py` read
with `flex_mem` and hold every way in Python. At the measured 6.7 GB of RAM per GB
of PBF, the 12.2 GB US file needs about 82 GB. `closures.py` has the same shape,
which is why it runs per region too.

## 3. The border proof (trap 1)

**Set-up.** Everything here is built from Geofabrik's New England extract of
2026-08-25, the file `processed-ne` was built from, so OSM edits play no part.

- **The reference** (`joint.py`) is that extract built as one region, in the order
  and projection `processed-ne` was built in, plus E1's `terrain.py` and
  `protected.py`. Its graph is **998,252 edges and 794,685 nodes: exactly
  `processed-ne`'s**, so today's code reproduces the deployed topology.
- **The stitch** cuts the six states' rings out of the same file (`cut.py`),
  counts junctions over the whole file (`junctions.py`: 645,920), builds each
  state alone (`build.py`) and stitches them (`stitch.py`).

**Every way two states both read is split identically.** 144,458 ways are in two
or more states' rings. The multiset of (u, v) each state cut them into is the
same in every state for all 144,458 (`stitch_report.json`, `borders`). Massachusetts
alone shows why the national junctions are needed: its extract by itself misses
1,152 junctions whose other road lies outside its ring.

**Edge for edge against the reference:**

| | edges | km |
|---|---:|---:|
| reference, owned by the six states | 997,253 | |
| stitch | 997,095 | |
| matched on (u, v, geometry) | **997,095** | |
| in the stitch only | **0** | 0 |
| in the reference only | 158 | 25.4 |

- **Every matched edge** has the same length, minutes, traffic-control counts,
  one-way flag, name, ref, class, junction and destination tags: 0 differ in each.
- **The 158 reference-only edges** were all built and owned by a state. The
  proof's component cut, made over New England alone, then dropped them because
  they connect only through New York, Quebec or New Brunswick: 99 in Connecticut
  (Greenwich's streets off Port Chester, at -73.67, 41.03), 36 Vermont, 16 Maine,
  5 Massachusetts (Egremont, on the New York line), 2 New Hampshire. In the
  national build New York is in the component and its share comes back; roads
  reachable only through Canada stay out, which is right for a US graph.
- **Scores:** 3,377 of 997,095 edges (0.34%) differ, and 272 km (0.12% of km)
  differ by more than 0.25 (max 2.16). **Every one of them is a tie.**
  `graph.attach_scores` reads, at each sample point along an edge, the nearest
  scored chunk (`query_nearest(..., all_matches=False)`). Where two ways overlap,
  several chunks are equally near, and the tree returns whichever its build order
  puts first. That order depends on which chunks are in the tree, which differs
  between one region and six. In a sample of 300 differing edges, all 300 have a
  sample point with a tied nearest chunk. In 300 unchanged edges, 6 do (2%). The
  choice is just as arbitrary in the reference, so neither copy is wrong. No
  difference traces to a ring missing its surroundings. The tie test separates the
  two populations completely, and `score_adj` and `unpaved_frac` differ on 0 edges.
  The component differences (`c_curves` up to 0.88, `c_water` 0.55, `c_forest` 0.24)
  are what the other overlapping way's chunk carries.

**The method the brief rules out, built for the record** (`compare.py naive`):
Geofabrik's own New Hampshire and Vermont extracts of the same day, each built
alone with `graph.py`'s splitting, concatenated and de-duplicated on (u, v). Over
the two states' 187,955 reference edges:

| | reference edges missing | edges the reference lacks |
|---|---:|---:|
| naive concatenation | **832** | **182** |
| this build's stitch | 38 (the component edges above) | 0 |

The 182 are roads that run straight through a junction one side never counted,
overlapping the reference's two shorter edges, and they are among the 832 missing.

**The sidecars match too.** Run per state on the stitched graph (`sidecars.py`) and
compared with `closures.py` and `state_roads.py` run once on the reference, matched
through each edge's (u, v):

| table | reference rows | stitched rows | rows matched | `at_m` difference |
|---|---:|---:|---:|---:|
| `closed_to_cars` | 1,462 | 1,462 | all | 0 |
| `seasonal_closures` | 248 | 248 | all | 0 |
| `osm_unpaved` | 951 | 951 | all | — |
| `state_road_class` | 49,801 | 49,798 | 49,798 | — |

The three missing state-road rows are on edges the New England-only component
dropped (Egremont, MA). `processed-ne` has 49,801 rows too.

Running it found a defect in `closures.py`. A region with no seasonally closed
road in its graph (Rhode Island) raises `ZeroDivisionError` in the report's
`np.average`, after `seasonal_closures.parquet` is written and before the other two
tables are. `closures.py` is unit D's, so it is not edited here.
`tools/national_build/closures_run.py` runs it with that one call returning NaN on
empty weights, which changes a printed number and nothing written.

**Routes across the Connecticut River** (`compare.py routes`,
`tools/national_build/cross_river_pairs.json`). There are 18 New Hampshire to Vermont
trips, from bridge towns a few km apart (Hanover-Norwich, Woodsville-Wells River)
to Portsmouth-Burlington, plus two near the Canadian line (Colebrook-Canaan,
Pittsburg-Island Pond). Each is routed by the shipped Router at pref 0, 0.5 and 1
on the reference and on the stitch, with every sidecar table present:

- **54 of 54 take the identical edge sequence**, with identical km and minutes.
- Mean scores differ by at most 0.005, on 14 of the 54, from the tied chunks above.

**Parking-lot entrances.** `access_ways` and `access_entries` are kept per
component, from the region that owns the component's south-westernmost first
vertex. On the reference's components, with that same rule applied, the stitch
holds the same 703,359 components and the same 1,190,420 distinct way
geometries, with none missing on either side. The reference's other 729
components are lots in its New York, Quebec and New Brunswick strips.

The proof's files are in `tools/national_build/results/proof_*`.

## 4. New England must not move (trap 2)

Two questions with different answers, kept apart:

1. **Does the method move New England?** Answered on the 2026-08-25 data, where the
   only difference between the two builds is the method.
2. **How far does the national build's New England sit from `processed-ne` built
   with E1?** That adds seven weeks of OSM edits (2026-08-25 to 2026-10-17) and the
   loss of the Canadian strips, which the method has nothing to do with.

### 4.1 The method, on the same data

The reference and the stitch of §3, compared on 100 town-to-town trips across New
England. They are drawn by `tools/route_census.py`'s own sampler (OSM place nodes,
25 in each of the 10-25, 25-50, 50-100 and 100-200 km bands, seed 20261019,
`tools/national_build/ne_trip_pairs.json`), and routed at pref 0, 0.5 and 1 with the
shipped Router and every sidecar table:

- **All 300 routes succeed on both. 298 take the identical path**, with identical
  km and minutes.
- The other 2 are pref-1 routes (one 50-100 km trip, one 100-200 km) that differ
  by 0.17 and 0.16 km and 0.5 and 0.1 min. Their mean scores agree to 0.003. A tied
  chunk moved a score by enough to change a near-equal scenic choice.
- The largest mean-score difference on any of the 300 is 0.012.

So stitching moves New England's routing only through the nearest-chunk ties of §3,
which are arbitrary in any build.

### 4.2 The national build against `processed-ne` with E1

`slice.py` cuts the six states' regions out of `data/processed-us` (997,415 edges;
193 more drop out because they reach the rest of New England only through New York
or Canada). That slice is compared with the reference of §3, which is the
2026-08-25 extract built as one region with E1: what `processed-ne` becomes when
rebuilt with E1.

**Graph** (`compare.py graph`, `results/ne_national_vs_reference_graph.json`):

| | |
|---|---:|
| reference edges in the six states | 997,253 |
| national edges in the six states | 997,415 |
| matched on (u, v, geometry) | 975,979 (97.9%) |
| reference only / national only | 21,274 (7,431 km) / 21,436 (7,381 km) |

The unmatched edges are roads re-split between 2026-08-25 and 2026-10-17: a new
junction, a moved node or a re-drawn way. 4,479 and 4,455 km of each side are
residential, and the two sides are nearly the same size by class. On the matched
edges, length differs on 0. The score differs by more than 0.25 on 1.07% of km.
That combines the 0.12% from ties (§3) with seven weeks of edits around the roads:
`c_forest` (565 km over 0.25), `c_urban` (375 km), `c_water` (308 km). Tags differ
where they were edited: `highway` on 2,405 edges, `name` on 518, `oneway` on 170.

**Routes** (`compare.py routes` on §4.1's 100 trips, at pref 0, 0.5 and 1,
`results/ne_national_vs_reference_routes.csv`):

| pref | same on the ground (within 50 m and 6 s) | length changed by over 1% | largest change |
|---|---:|---:|---|
| 0 | 93 of 100 | 2 | 12.2 km on a 266 km trip, +0.1 min |
| 0.5 | 76 of 100 | 6 | 4.1 km on a 76 km trip, +1.8 min |
| 1 | 76 of 100 | 4 | 14.0 km shorter and 19.6 min faster on a 243 km trip |

All 300 route on both. The mean score of the route moves by +0.008, +0.019 and
+0.005 on average at the three prefs, and by at most 0.36.

**So, measured:** the method moves New England by the ties alone, 2 trips in 300 on
the same data (§4.1). Everything else in this table is OSM between August and
October, which any rebuild of `processed-ne` would pick up too.

## 5. What scale forced in the pipeline

The contract is the server's file list, in `processed-ne`'s schema: `graph_edges`,
`graph_nodes`, `turn_restrictions`, `access_ways`, `access_entries`,
`closed_to_cars`, `seasonal_closures`, `osm_unpaved` and `state_road_class` (New
Hampshire, Vermont, Massachusetts and Maine rows only; every other state has none,
and the table keeps its columns). `graph_edges` also carries `unpaved_frac`,
`c_grand` and `c_protected`, which a post-2026-08-29 E1 build writes and the Router
reads as optional.

Four changes to owned pipeline files, each forced by the national scale, and none
moving a New England number:

| file | change | why | checked |
|---|---|---|---|
| `graph.py` | `build_scored_edges` split out of `main`, with an optional national junction set (`global_junctions`) | a region must split its roads at junctions it cannot see (§3) | `main` unchanged in behaviour: the joint build reproduces `processed-ne`'s 998,252 edges and 794,685 nodes |
| `graph.py` | `largest_component_mask` on bare arrays, `largest_component` now calls it | the national component is cut over ~24M edges without their geometry | `tests/test_national_build.py`; the joint build above |
| `score.py` | `split_large`: polygons over 2,000 vertices cut into 5 km squares before any `dwithin` tree | Casco Bay's water polygon cost 54 s per 20,000 nearby chunks, its pieces 0.22 s; the Great Lakes are larger | **bit-identical**: re-scoring all 942,448 New England chunks gives 0 differences in every component, `raw` and `score`. New England's water queries went 582 s to 19 s and 616 s to 13 s |
| `protected.py` | reads PAD-US landmarks from a GeoParquet as well as the geodatabase | ScienceBase put the geodatabase behind a sign-in on 2026-10-18 | same filter (`FEATURE_CLASSES`, `LANDMARK`) on the same PAD-US 4.1 layer, from USGS's public feature service (`tools/national_build/padus_landmarks.py`, 9,048 polygons) |

`common.CRS_METERS` and `elevation.BBOX` are set per region from outside, by
`tools/national_build/stage.py`, without editing either file. `closures.py`,
`state_roads.py` and `router.py` are run or read unmodified.

## 6. Region-specific constants in the pipeline (trap 3)

Grepped in `pipeline/` for New England bounds, state lists and fitted constants on
2026-10-18. `server/app.py`, `router.py`, `looper.py` and `options.py` hold no
bounds; the graph's own extent decides what is in region.

| constant | where | what it assumes | what the national build does |
|---|---|---|---|
| `CRS_METERS = 26986` | `common.py`, used by every stage and by `router.py`, `options.py`, `closures.py`, `state_roads.py` | Massachusetts Mainland: 4.5% long at Key West, grid north 30-35 degrees off in the West | **changed, per region**, for the stages (§2). Not changed in `router.py` or `options.py`: unit B's. Their snap distances and bearings are in 26986 at runtime, and `closures.py` (run unmodified) measures a barrier's `at_m` in 26986 too, which is consistent with the router's own snap until B changes it |
| `BBOX = (-73.76, 40.93, -66.87, 47.47)` | `elevation.py` | New England | **set per region** to the ring's box (`stage.py`) |
| `RELIEF_REF_LAT = 42.05` | `elevation.py`, `terrain.py` | windows sized in ground metres at Massachusetts' latitude; on Web Mercator pixels the 13-pixel relief window is 738 m of ground there, 860 m at 30 N and 652 m at 49 N | **kept**. E1 was measured with it in Utah and Colorado (`docs/national-scenery-components.md`), and the absolute scale keeps the score constants. A latitude-true window is a score change for its own decision |
| `ELEV_MAX_M`, `ELEV_MIN_M` | `elevation.py` | a physical band, global | kept. The in-band coastal spikes (`docs/us-map-data-findings.md` §6.1) stay in `relief.tif`: `terrain.py` despikes only `range3k.tif`, and despiking relief moves New England's scores, which is a separate decision |
| `BYWAY_NETWORKS` | `extract.py` | five networks, three of them New England's | **kept**. It admits 48 of the 310 relations filed in state byway networks, and `scenic=yes` admits 210 more; 168 are missed (Ohio 26, Oregon 23, California 22: `docs/us-map-data-findings.md` §5). Widening it raises `c_scenic_tag` outside New England only, but it is a scoring change the E1 measurements did not include |
| `SPEED_KMH` | `graph.py` | posted-limit defaults fitted on Massachusetts' tagged roads | **kept**. Tagged rural primary speeds run 42-66% above it in Kansas, Montana, Wyoming, South Dakota and Utah (findings §3.1), so untagged Western roads get Massachusetts' limits. That is an ETA defect, not a topology one, and refitting it per region moves New England's times |
| `RAW_BASE`, `STRETCH`, `RELIEF_FULL`, `WEIGHTS`, `CLASS_ADJ` | `score.py` | calibrated on New England | kept: the decided absolute scale (E1) |
| `SOURCES` (NH, VT, MA, ME) | `state_roads.py` | four states' DOT layers | run on New England only; every other state gets an empty table (the contract) |
| calibration benchmarks (Greylock, Mohawk Trail, I-90) | `score.py`'s report | Massachusetts names | cosmetic: the report prints "no match" outside Massachusetts |

## 7. Delivered

`data/processed-us`, 7.3 GB:

| file | rows | size |
|---|---:|---:|
| `graph_edges.parquet` | 25,849,861 | 4.2 GB |
| `graph_nodes.parquet` | 20,023,955 | 420 MB |
| `turn_restrictions.parquet` | 192,179 | 4 MB |
| `access_ways.parquet` | 23,780,477 | 2.6 GB |
| `access_entries.parquet` | 16,693,454 | 642 MB |
| `closed_to_cars.parquet` | 71,617 | 3 MB |
| `seasonal_closures.parquet` | 3,850 | 0.2 MB |
| `osm_unpaved.parquet` | 19,237 | 0.7 MB |
| `state_road_class.parquet` | 49,697 (NH, VT, MA, ME) | 2.7 MB |

Beside them are `per_region.csv` and `access_per_region.csv`, the row ranges each
region wrote (`slice.py` reads them), plus `stitch_report.json` and
`sidecars_report.json`.

Checked against `processed-ne`'s schema: no column is missing from any file and no
type differs. The extras are what today's code writes: `c_grand`, `c_protected` and
`unpaved_frac` on the edges, and `rule`, `node_id` and `at_m` on
`seasonal_closures`. `osm_unpaved` is new since `processed-ne` was built.

The 192,179 forbidden turns come from 407,138 via-node restrictions; 113,750 name
a road the graph does not carry. The component keeps 25,849,861 of 26,041,120 owned
edges (99.3%). Edges whose midpoint lies outside the 48 states and DC are dropped:
Canada and Mexico, in the strips the US extract carries.

**Per state** (`results/per_state.csv`; Texas's and California's halves added
together; a node where two states' edges meet counts in both, so the states sum to
20,034,769 nodes against 20,023,955):

| state | nodes | edges | km |
|---|---:|---:|---:|
| TX | 1,886,996 | 2,505,407 | 720,118 |
| CA | 1,526,366 | 1,940,853 | 376,922 |
| FL | 1,147,548 | 1,530,865 | 262,615 |
| IL | 699,922 | 941,114 | 255,162 |
| MO | 581,761 | 748,094 | 252,418 |
| GA | 678,810 | 847,382 | 238,062 |
| KS | 336,237 | 465,810 | 237,787 |
| PA | 692,979 | 901,483 | 231,683 |
| NC | 756,220 | 916,728 | 231,111 |
| MN | 396,961 | 532,973 | 231,017 |
| MI | 555,908 | 737,717 | 221,650 |
| OK | 460,582 | 591,769 | 216,597 |
| OH | 609,223 | 791,834 | 215,656 |
| NY | 621,967 | 818,680 | 209,974 |
| WI | 440,078 | 580,764 | 202,354 |
| IA | 296,424 | 409,829 | 193,798 |
| AL | 477,227 | 597,088 | 182,141 |
| TN | 468,635 | 582,659 | 179,098 |
| IN | 458,541 | 606,255 | 176,425 |
| CO | 398,522 | 514,959 | 168,196 |
| VA | 514,656 | 631,734 | 164,689 |
| NM | 239,111 | 308,715 | 163,428 |
| AR | 321,071 | 403,048 | 161,141 |
| NE | 200,356 | 285,963 | 160,863 |
| MS | 298,582 | 375,204 | 149,037 |
| WA | 449,380 | 551,667 | 148,694 |
| KY | 355,708 | 428,979 | 146,411 |
| MT | 151,301 | 188,835 | 140,854 |
| SC | 402,603 | 510,410 | 140,743 |
| LA | 363,256 | 468,073 | 139,005 |
| AZ | 474,743 | 602,729 | 138,755 |
| SD | 122,277 | 166,307 | 127,915 |
| OR | 268,473 | 333,652 | 117,254 |
| ND | 90,425 | 128,223 | 113,952 |
| ID | 187,151 | 235,766 | 110,593 |
| WV | 177,653 | 207,455 | 78,153 |
| UT | 191,294 | 242,541 | 75,094 |
| NJ | 351,545 | 467,800 | 73,334 |
| WY | 77,145 | 96,874 | 68,767 |
| MA | 309,730 | 400,257 | 65,562 |
| MD | 279,955 | 352,958 | 65,449 |
| NV | 158,374 | 203,678 | 60,837 |
| ME | 128,817 | 150,991 | 58,008 |
| CT | 147,758 | 188,001 | 39,232 |
| NH | 93,057 | 115,906 | 31,241 |
| VT | 61,760 | 71,898 | 27,589 |
| DE | 59,499 | 78,458 | 14,146 |
| RI | 53,619 | 70,555 | 10,592 |
| DC | 14,563 | 20,921 | 1,986 |
| **total** | 20,034,769 | 25,849,861 | 7,796,108 |

The findings estimated 19.1M nodes ±20% (`docs/us-map-data-findings.md` §2); the
build has 20.0M.

**Cost, measured on this Mac** (`results/per_region_cost.csv`):

| | |
|---|---|
| region builds, 51 regions | 10.7 process-hours, 13.9 GB of ring PBFs; about 4 h of wall time at two, then three, regions at once, 20:50 to 00:55 |
| slowest region | east Texas, 36 min |
| peak RSS, any stage | 10.8 GB (South Dakota's `landcover.py`); `landcover.py` is the peak stage in 48 of 51 regions, at 8-11 GB. It reads a WorldCover tile window at a time, and a rural state's sample boxes cover whole tiles |
| a region's processed directory before clean-up | at most 1.96 GB (east Texas) |
| stitch | 1,729 s, 9.0 GB peak |
| sidecars | 1,302 s, 7.0 GB peak (`closures.py` 3-54 s a region; `state_roads.py` 104 s) |
| disk kept | `processed-us` 7.3 GB; `data/national` 40 GB (the parts 10 GB, WorldCover 8.8 GB, Terrarium 4.1 GB, ring PBFs 13 GB, the proof 3.2 GB) |

**Re-running one state** (`tools/national_build/README.md`): delete
`data/national/build/<region>/part_edges.parquet` and the stage outputs to redo, run
`build.py config.json <region>`, then `stitch.py` and `sidecars.py` for the whole
country, about 50 minutes for the two. National row numbers change on every stitch,
so the sidecars are always rerun with it.

## 8. For the other units, and what is still open

- **Unit B, the router.** `router.py` and `options.py` still measure in
  `common.CRS_METERS`, EPSG:26986. Snap distances are 4.5% long at Key West, and
  grid bearings in the West are 30-35 degrees off true north (§2). The graph's own
  `length_m` is right: each region measured it in its own conic. `closures.py`'s
  `at_m`, written in 26986, agrees with today's snap. If B moves the router off
  26986, `at_m` must move with it (re-run `sidecars.py`). The files are large to
  load whole: 25.8M edges in 4.2 GB, 23.8M parking-lot ways in 2.6 GB. Today's
  `Router` cannot load them on this Mac, which is why §4.2 routes on a slice.
- **Unit D, closures.** `closures.py` raises `ZeroDivisionError` in its report on a
  region whose graph holds no seasonally closed road (Rhode Island), after
  `seasonal_closures.parquet` and before `closed_to_cars.parquet` and
  `osm_unpaved.parquet`. Its `np.average` over an empty selection is at
  `closures.py:927`. The national build runs it through
  `tools/national_build/closures_run.py` until D fixes it. After any change to
  `closures.py`, re-run `sidecars.py` (about 22 minutes).
- **Ties in `attach_scores`.** Where ways overlap, the nearest chunk is a tie and
  the choice is arbitrary (§3). It moves 0.12% of New England's km by more than
  0.25 between any two builds. A deterministic tie-break would end that, at the
  cost of moving the same km once against the deployed graph. Not done: it is a
  scoring change.
- **The constants in §6.** `SPEED_KMH`, `BYWAY_NETWORKS`, `RELIEF_REF_LAT` and the
  unpatched relief spikes are national-scale defects that this build carries
  unchanged. Each is a decision for the master session, not a build problem.
- **Not done here:** the test suite against `processed-us` itself. The Router
  cannot load it, so the data tests ran on `processed-ne`: 944 passed, 12 skipped,
  on this branch. The six new tests are `tests/test_national_build.py`.
