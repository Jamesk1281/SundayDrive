# The national road graph build

**Status:** in progress, started 2026-10-18 on `claude/national-build` (off `usa`).
Output: `data/processed-us` in the main checkout, in `data/processed-ne`'s schema.

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
