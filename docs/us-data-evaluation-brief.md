# US map data: what exists, how big, how good (brief)

**Status: scoped, not started.** Written 2026-10-11 against `main` at
`2ed3f47`. Nothing in the tree has been touched. The answer goes to a new
`docs/us-map-data-findings.md`, and its scripts and small result files go to a
new `tools/us_map_data/`. This brief is deleted in the merge that brings the
answer back (`docs/README.md`, rule 5).

## The question

A USA feasibility review (2026-10-10/11; the task prompt gives its path) found
that the serving hardware is enough for the whole US once the router changes.
It did not settle the data side at national scale. For the 50 states and DC:

1. **Space.** For every dataset the pipeline reads today, or would need to read
   in the US: how much disk it takes to fetch, how much to build from, and how
   much to serve. Then the peak working space to build the whole US one region
   at a time.
2. **Quality.** How good each dataset is for what the router and scorer read
   from it, measured outside New England. Split the gaps into routing-safety
   problems (closed, 4WD, private or wrong-speed roads) and scenery-quality
   problems.

## Already measured: do not re-measure, cite these

From the feasibility review (Mac, 2026-10-10/11):

- **OSM extracts.**
  - The whole US is `us-260701.osm.pbf`, 11,997,871,559 bytes.
  - Per-state sizes are on Geofabrik's `north-america/us.html`. On 2026-10-10:
    CA 1.2 GB, TX 690 MB, FL 627 MB, NY 474 MB, CO 366 MB, down to VT 43.9 MB
    and SD 47.2 MB.
- **Routing graph.**
  - `count_graph.py` (the review's) reproduces graph.py exactly: New England
    794,685 nodes / 998,252 edges, Colorado 398,656 / 515,191.
  - Measured: CA 1,527,476 nodes (378,139 km), CO 169,977 km, and the six New
    England states.
  - US estimate: about 23.4M nodes (19-28M), fitted on FHWA HM-20 2023 public
    road length (US 4,199,211 mi).
- **Colorado OSM quality**, length-weighted over drivable roads (172,295 km):
  - Surface: unpaved tag 40.7%, no `surface` 27.3%.
  - Roughness: `smoothness` bad or worse 3,593 km (2.1%); `4wd_only=yes`
    938 km.
  - `maxspeed` tagged: motorway 97%, trunk 82%, primary 66%, secondary 53%,
    tertiary 20%, unclassified 3.5%, residential 6.4%.
  - Tagged speeds run 19-28% above graph.py's New England defaults.
- **Colorado seasonal closures.**
  - Detected: 77 ways, 189 km, including Independence Pass, Mount Blue Sky,
    Kebler and Cottonwood.
  - Not tagged: Trail Ridge Road (81 km in the graph), Old Fall River, and the
    Engineer, Cinnamon and Boreas passes.
- **Colorado byways.**
  - 26 relations use `network=US:CO:Scenic`; extract.py admits only the 11 that
    also carry `scenic=yes`.
  - The US 34 route relation carries `scenic=yes`, which flags 425 km, mostly
    plains.
- **Terrarium elevation.**
  - New England: 2,120 z11 tiles, 160 MB (75 KB per tile).
  - Colorado: 1,656 tiles, 197 MB (119 KB per tile).
  - The contiguous US is about 60,400 z11 tiles.
  - Colorado decode found three inland blobs (161 px below 500 m, minimum
    -639 m) creating 2,300-4,536 m of fake relief, plus 1,152 out-of-band
    pixels in two tiles.
- **WorldCover.** New England's eight tiles are 343 MB (landcover.py
  docstring). Colorado's eight took 967 s to stream from eu-central-1. Median
  Colorado tree fraction is 0.00.
- **State DOT road classes, raw GeoJSON** (`data/raw/state-roads/`): MA 290 MB,
  NH 99 MB, VT 82 MB, ME 53 + 81 MB.
- **Build outputs.** `processed` comes to 948 MB for Colorado (0.40M nodes) and
  1.4 GB for New England (0.79M).
- **Compact serving pack** (the review's `package_size.py`): New England 97 MB
  raw / 42 MB xz, Colorado 43 / 17 MB. Search arrays add about 113 B per node.

## Where the pipeline reads each dataset

The New England assumptions to test live in these constants:

- `pipeline/common.py:13` `DRIVABLE`, `:28` `PRIVATE_ACCESS`, `:42`
  `CLOSED_TO_CARS`, `:57` `PASSABLE_BARRIERS`. This is what counts as a road and
  as closed. `:182` `CRS_METERS = 26986` (MA state plane) is the projection
  used for every length.
- `pipeline/extract.py:107`: the byway networks, New England's only:

  ```python
  BYWAY_NETWORKS = {
      "US:MA:Scenic",                 # 14 relations, every one a designated byway
      "US:VT:byway",                  # 9
  ```

  `:34-49` holds the green, water, farm and urban tag sets that score.py reads.
- `pipeline/graph.py:64`: `SPEED_KMH`, fitted on Massachusetts tagged roads.
  `:83` is `parse_maxspeed`. Via-way restrictions are skipped (`:149`).
- `pipeline/score.py:55` is `WEIGHTS` and `:99` the `UNPAVED` surface set
  (there's no `smoothness` or `4wd_only` anywhere). `:84` is the relief cap:

  ```python
  RELIEF_FULL = 100.0
  ```

- `pipeline/elevation.py:34` `BBOX` (New England), `:35` the Terrarium
  `TILE_URL`, `:87-88` the -11,000..9,000 m validity band, `:165` the in-RAM
  float64 mosaic.
- `pipeline/landcover.py:52`: WorldCover v200 2021 `TILE_URL`. `:58` is
  `TREE_CLASS`.
- `pipeline/closures.py:83` `CAR_KEYS`, `:87` `WINTER`. `:91` is the only set of
  `seasonal=` values it reads:

  ```python
  SEASONAL = {"yes", "summer", "spring;summer;autumn", "no_snow"}
  ```

- `pipeline/state_roads.py:148`: `SOURCES`, one bespoke ArcGIS layer per state
  (NH, VT, MA, ME). `:200` is the TIGERweb state boundaries.
- `pipeline/router.py:470`: `REGION_TZ = America/New_York`.
- **In flight elsewhere, not on main:** a residential-streets change reads 2020
  Census Urban Areas (`data/raw/census/urban-areas-2020-20261008.geojson`,
  28 MB; check whether it is national).

## Scope, in priority order

**P1, needed for any US build:**

- **OSM: sizes per state** (index page or HEAD). **Quality per state** with the
  metrics below.
- **Terrarium:** the national tile count and bytes. Sample HEAD
  `Content-Length` across terrain types rather than extrapolating from New
  England. Then measure the corrupt-pixel rate by decoding a sample of tiles in
  mountains, deserts, coasts and plains.
- **WorldCover:** the tiles covering the US (count and bytes by HEAD), and
  which cells are absent.
- **USFS Motor Vehicle Use Map roads** (national, CC-BY, on data.gov). Size,
  which fields carry season dates and vehicle class nationally, and coverage
  against OSM in one sample forest. The review flagged it as the national source
  for seasonal and high-clearance roads.
- **TIGER/Line roads:** national size. Coverage of MTFCC S1500 (4WD vehicular
  trail) and S1740 (private service road) against OSM in a sample state.

**P2:**

- PAD-US (protected areas, for scenery and park designation).
- USGS 3DEP (elevation alternative): size, plus one quality comparison against
  Terrarium in Colorado.
- NPS road and closure data: availability and form.
- National Scenic Byways geometry: availability.
- **State DOT road-class layers for all 50 states:** an availability survey
  only. Public ArcGIS endpoint or not, licence, which field carries class,
  maintenance or surface, and a count via `returnCountOnly=true`.

**P3, availability only:** NHD/NHDPlus HR (water), FHWA HPMS/ARNOLD (speed
limits), BLM GTLF roads, and state 511 or pass-status feeds in three Western
states (CO, CA, WA).

## Method

- **Sizes come from metadata, never from bulk downloads:** HEAD
  `Content-Length`, index pages, data.gov and ArcGIS layer JSON, and
  `returnCountOnly`.
- **OSM quality runs on two tiers:**
  1. **All 50 states + DC through Geofabrik's per-state taginfo.** These are
     object counts, a proxy only. Reachability was checked on 2026-10-11:
     `https://taginfo.geofabrik.de/north-america:us:colorado/api/4/key/stats?key=maxspeed`
     returned 200.
  2. **Length-weighted over the drivable graph for a stratified sample.** Use
     the six New England extracts in `data/raw/`, Colorado (if the review's copy
     still exists, else re-download) and about five more states, chosen for
     spread: West, Plains, South, Northwest. Download one at a time, keep the
     total at or under ~1.5 GB, and delete each when done. Use the review's
     drivable filter (`count_graph.py`, which matches graph.py exactly). Report
     how well tier 1 predicts tier 2 in the sample states.
- **Metrics:**
  - `maxspeed` coverage by class, and tagged speed against `SPEED_KMH`.
  - `surface` coverage and unpaved share.
  - `smoothness`, `4wd_only` and `tracktype` on drivable roads.
  - The `tiger:reviewed=no` share.
  - Signal, stop and give-way density per km.
  - Turn restrictions per 1,000 junctions.
  - Seasonal and conditional tagging against ground truth (below).
  - Byway relation networks per state.
- **Seasonal ground truth.** Verify each road's actual closure from an official
  source (NPS, state DOT) before scoring it, then check how OSM tags it: ways
  and gate nodes, `*:conditional`, `seasonal`, `winter_service`. Start from:
  Trail Ridge Rd, Old Fall River Rd, Independence Pass, Mount Blue Sky Rd (CO);
  Going-to-the-Sun Rd, Beartooth Hwy (MT/WY); Tioga Rd (CA 120), Sonora Pass
  (CA 108), Ebbetts Pass (CA 4), Glacier Point Rd, Lassen Park Hwy (CA); North
  Cascades Hwy (WA 20), Chinook Pass (WA 410), Hurricane Ridge Rd (WA); Rim Drive
  at Crater Lake (OR); Mirror Lake Hwy (UT 150); Teton Park Rd (WY); Mt
  Washington Auto Road (NH). Add Kancamagus Hwy as a year-round control.
- **Byway census.** For every state, list `route=road` networks naming
  scenic or byway, with relation counts. Mark which extract.py's rule (network
  allowlist, or `scenic=yes`) admits or misses, and any whole numbered-highway
  relation carrying `scenic=yes`. A few small Overpass relation queries, or the
  sampled PBFs, will do.

## Traps

1. **Bulk downloads.** The Mac has about 20 GB free and the build data already
   fills most of the rest. Geofabrik ran at 0.05-1.9 MB/s here on 2026-10-10.
   Do not fetch the 12 GB US file, every state, all Terrarium tiles or all
   WorldCover tiles. Metadata gives sizes; samples give quality. If a size
   cannot be known without a bulk download, say so and stop there.
2. **Counting objects instead of km on the drivable graph.** Taginfo counts
   every element under every `highway=*`, footways and service roads included.
   A tag can look 60% covered by count and be 20% covered on the kilometres a
   route drives. Length-weight over `DRIVABLE` plus the access rule (the
   review's counter), and label taginfo figures as a proxy.
3. **An absent tag is not an open road.** Some closures are mapped on gate
   nodes rather than ways, and closures.py only reads certain values
   (`:83-91`). Check both before calling a road untagged, and verify the real
   closure first.
4. **Terrarium bytes per tile depend on terrain** (75 KB New England, 119 KB
   Colorado). The corruption the validity band misses is negative values
   inland. A coastal sample will not find it.
5. **WorldCover is in eu-central-1 and slow from here.** Use HEAD. A 404 near a
   coast is an all-ocean cell left out of the grid, not an error.
6. **State DOT layers are a survey, not an integration.** Schemas and meanings
   differ per state; `state_roads.py:148` shows how much interpretation each one
   needed. Use counts and field lists only, and record "not public" or "not
   found" plainly.
7. **MVUM is published forest by forest.** Check the national schema before
   assuming one forest's fields exist everywhere.
8. **`data/` in the main checkout is production input** (`processed-ne` is what
   is deployed). Read only. Downloads go to the session scratchpad.
9. **Don't fan out broad research sub-agents.** They recurse out of sight and
   cost the owner's session limit. Search directly.
10. **Some government hosts block scripted requests.** Make one request at a
    time and record a block as an access finding. Don't work around it
    aggressively.

## Done looks like

1. `docs/us-map-data-findings.md`, with a bold `**Status:**` line on line 3,
   containing:
   - a dataset table: source, licence, format, access and its constraints,
     update cadence, and US size to fetch, build and serve;
   - the disk budget for a full-US build, the peak working space region by
     region, and the serving size;
   - OSM quality per state (the proxy for all of them, measured for the sample)
     and how well the proxy predicts the measurement;
   - the seasonal-roads table and the byway-network census;
   - the quality of the non-OSM layers;
   - a ranked list of gaps, split safety from scenery, naming the dataset that
     closes each one;
   - an explicit list of what cannot be determined from the data available.
2. Scripts and small result files in `tools/us_map_data/`. Nothing changed in
   `pipeline/`, `server/`, `ios/` or `data/`.
3. This brief committed unchanged beside the findings, on a branch off `main`,
   not merged. Results go in the findings, never appended here.
