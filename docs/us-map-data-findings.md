# US map data: what exists, how big, how good

**Status:** measured 2026-10-11 against `main` at `2ed3f47` on branch `claude/us-map-data`. Nothing in `pipeline/`, `server/`, `ios/` or `data/` changed. Every figure comes from a script in `tools/us_map_data/`, and its output is in `tools/us_map_data/results/`, unless the text says otherwise. This answers `docs/us-data-evaluation-brief.md`, which is deleted in the merge that brings it back.

This is the data half of the US question. The routing half (graph size, search, the
serving box) is the feasibility review, `docs/usa-extension-feasibility.md`. It is cited
here, and corrected in four places (§9). The scope is every dataset the pipeline reads
today or would need, for the 50 states and DC: how much disk each takes to fetch, build
and serve, and how good it is for what `pipeline/` reads from it. Gaps are ranked and
split into routing safety and scenery.

## Verdict

**Space is not the obstacle. The routing-safety gaps in the data are, and nearly all
of them close with data that is public, plus changes to code that reads OSM.**

1. **A full-US build fits this Mac if it keeps compact packs rather than processed
   directories.**
   - Built one state at a time, the peak working space is about **9 GB**: the largest
     state in flight (California or Texas, 4.8 GB) plus 4.4 GB of finished packs.
   - Keeping every processed directory and its rasters needs 46-56 GB.
   - Serving takes about 4.4 GB compact, 1.0 GB compressed. The US graph is about
     **19.2M nodes**, not the review's 23.4M: its fit overestimated every rural state
     counted since, South Dakota by 178% (§2).
   - Memory binds one stage. elevation.py's in-RAM mosaic is 13.3 GB for Texas and
     56 GB for Alaska, so those two need a tiled elevation stage.
2. **Seasonal closures are the largest safety gap, and most of it is in closures.py,
   not in OSM.**
   - Of 18 passes and park roads checked against their operators, closures.py closes 11,
     and six of those it opens a week to two months early.
   - Of the 7 it leaves open, Trail Ridge Road *is* tagged in OSM
     (`no @ Oct 14th - May 31st`). The grammar rejects the ordinal "14th".
   - Glacier Point, Teton Park Road, Yellowstone's Grand Loop and Kuwohi Road carry no
     tag at all. NPS's own roads layer flags most park roads, but not Yellowstone's.
   - The Forest Service's MVUM fills the gap on national-forest roads: in one Colorado
     forest it lists 820 km of seasonal roads in the graph, and closures.py closes
     1.6 km of them.
3. **4WD tracks, wrong speeds and permit roads are the rest of the safety gap.**
   - OSM's own TIGER-import class for a 4WD trail (`tiger:cfcc` A5x) sits on 3,296 km of
     South Dakota's graph, 1,499 km of Montana's and 927 km of Colorado's. Nothing reads
     it, and almost none of those km carries a roughness tag.
   - Tagged rural speeds run 42-66% above graph.py's Massachusetts-fitted defaults on
     primary roads in Kansas, Montana, Wyoming, South Dakota and Utah.
   - The all-year rule closes `permit`. That shuts Trail Ridge Road on every day of the
     year (it carries Rocky Mountain National Park's timed-entry permit), and takes out
     272 km in Washington.
4. **Byways: extract.py's network allowlist admits 48 of the 310 relations filed in
   state byway networks.**
   - `scenic=yes` admits 213 relations nationally, and 168 are missed outright: Ohio 26,
     Oregon 23, California 22, Iowa 21, Colorado and Kentucky 15 each.
   - Two whole numbered highways would become byways: US 34 (451 km) and NY 30 (485 km).
5. **Terrarium is good enough to keep, with a patch from 3DEP.**
   - About 0.3% of lower-48 tiles (111 ± 33) hold corrupt pixels *inside* elevation.py's
     validity band that raise the relief score.
   - Nearly all are on coasts: 12% of coastal tiles against 0.2% inland. In the
     mountains, relief is already at its cap, so most cannot raise it.
   - Alaska's sample also turns up source seams, so Alaska needs its own pass.
   - The deployed New England raster has 31 such tiles and inflates 25.5 km of road by
     up to 1.7 points. Its maximum relief of 1,453 m is one of them, on the Maine coast,
     not the White Mountains (§9).
   - Elsewhere 3DEP 1″ agrees with Terrarium to a median 1.9 m, and it is clean where
     Terrarium is not.
6. **Taginfo is a fair first look at some tags and a misleading one at others.**
   - By object count Colorado is 11.6% unpaved; by kilometre it is 40.8%. Across 16
     states the count proxy halves the unpaved share and misses unclassified-road speed
     limits entirely (r = 0.32).
   - It does predict signal density (r = 0.99) and `tiger:reviewed` (r = 0.98) well, and
     a straight-line calibration recovers most of the rest (§3.3).

Every finding is ranked in §7, each with the dataset or code change that closes it, and
§8 lists what cannot be determined from what is available.

## 1. The datasets

"Fetch" is bytes off the wire for the 50 states and DC. "Build" is what the pipeline
writes from it. "Serve" is what a request needs in memory. Sizes come from HEAD
`Content-Length`, index pages, bucket listings and ArcGIS layer JSON. The only things
downloaded whole were the nine sampled state extracts (1,436 MB, each deleted after use;
§3), TIGER files for six Colorado counties (6 MB), one forest's MVUM roads, the Census
state outlines (3 MB), and 1,997 Terrarium tiles for the corruption sample (§6.1).

| dataset | what the pipeline reads, or would | licence | format, access | cadence | US fetch | build | serve |
|---|---|---|---|---|---:|---:|---:|
| OSM extracts (Geofabrik) | everything in extract, graph, closures | ODbL 1.0 | PBF per state, HTTPS, no key; 1.1-1.7 MB/s on 2026-10-11 | daily | **12.00 GB** (51 extracts; the US file is 12.20 GB) | processed 25-26 GB | in the pack |
| Terrarium z11 (AWS open data) | elevation.py → relief | per source, see `docs/data-sources.md` | 256 px PNG tiles on S3, no key | static: tiles last modified Nov 2017 | **6.56 ± 0.06 GB**, 58,947 tiles | rasters 16-25 GB | none (scores are baked in) |
| ESA WorldCover v200 2021 | landcover.py tree cover | CC BY 4.0 | 3° COGs, S3 eu-central-1, range requests | static (Oct 2022) | **11.58 GB**, 205 cells, streamed rather than stored | in processed | none |
| USFS MVUM roads | *new*: season dates, vehicle class, maintenance level on Forest Service roads | CC BY 4.0 (data.gov) | ArcGIS MapServer (150,789 features, 2,000 a page); national shapefile 236 MB, GDB 129 MB | refreshed forest by forest; GDB May 2025 | **0.13 GB** (GDB) | small | small |
| Census TIGER/Line 2026 roads | *new*: MTFCC S1500 (4WD), S1740 (private service) | public domain | shapefile per county, www2.census.gov | annual (2026-10-06) | **3.88 GB** (3,144 county zips) | small | — |
| NPS Public Roads | *new*: SEASONAL, SEASDESC, RDHICLEAR, RDSURFACE | not stated on the layer | ArcGIS MapServer, 31,313 features | maintained by parks | tens of MB *(not measured)* | small | small |
| BLM GTLF public roads | *new*: route-use class (4WD), seasonal restriction | US public domain | ArcGIS MapServer, 110,437 + limited-use layer; also shapefile, GDB on data.gov | Aug 2026 | small *(not measured)* | small | — |
| FHWA America's Byways | *new*: designated byway geometry | none stated | ArcGIS FeatureServer, 227 per-state records | layer dated 2026-08-04 | < 50 MB *(est.)* | small | — |
| PAD-US 4.1 | *new*: protected areas, park designation | public domain | national GDB zip on ScienceBase | about yearly (4.1: 2025-03-31) | **1.52 GB** | | |
| USGS 3DEP 1″ / 1/3″ | *alternative* elevation, or Terrarium's patch | public domain | COG per 1° cell on S3; windows read in place | rolling | 130.3 GB (3,812 cells) / 493.5 GB (1,449) if fetched whole | | |
| FHWA HPMS 2024 | *new*: posted speed limit, ownership | CC0 (data.gov lists it "non-public" all the same) | per-state geodatabases via BTS | yearly (2026-04-30) | *not determined* | | |
| NHDPlus HR | *alternative* water | public domain | national GDB | frozen (Release 1, Jul 2022) | 28.1 GB | | |
| State DOT road layers | state_roads.py (4 states today) | 7 of 38 open, 2 restrictive (§6.8) | ArcGIS REST, one per state | varies | per state; New England's raw GeoJSON is 53-290 MB each | | |
| Census 2020 Urban Areas | the residential-streets change in flight | public domain | TIGER UAC20 zip | decennial | **74.1 MB** national; the file in `data/raw/census` is New England only (102 areas) | | |

OSM grows: the US file went from 7.55 GB in January 2021 to 11.60 GB in January 2026,
**9.0% a year** (`osm_us_history.csv`). Every size here is 2026-10 and grows with it.

## 2. Disk and memory for a full-US build

`budget.py` prices every state from measured sizes (`budget_by_state.csv`). The inputs
are:
- the extract (HEAD) and its Terrarium tiles (each state's outline tiles times its own
  HEAD-sample mean, 75 KB in Rhode Island and Florida up to 143 KB in West Virginia);
- graph nodes, counted for 17 states and fitted for the rest;
- the processed directory at 1.31-1.36 KB per node, measured on Colorado and New
  England with elevation.py's two rasters left out;
- the rasters at 184-278 KB per bounding-box tile, measured on the same two builds;
- the compact pack at the review's 230 B per node.

**The US graph is about 19.2M nodes.** The review fitted 23.4M on 8 counted states: the
six New England states, Colorado and California. The 9 states counted here were all
more rural, and its fit overestimated every one of them: South Dakota by 178%, Montana 111%, Kansas 84%,
Wyoming 73%, Oregon 46%, Utah 37%, Mississippi 27% and Tennessee 17%. Washington came
within 1%. The same model refitted on all 17 gives 7.03 nodes per urban km and 0.98 per
rural km of FHWA public road. That is 19.2M nodes and 24.5M edges, 5.1M of the nodes
counted. Leave-one-out error is 19% mean and 53% worst (South Dakota), so the range is
roughly ±20%. The rural coefficient fell from 2.46 to 0.98: rural states have fewer
graph nodes per km of public road than New England, most likely because long unbroken
ways need few of them.

| | total | largest single state |
|---|---:|---|
| fetch: OSM extracts | 12.0 GB | California 1.33 GB |
| fetch: Terrarium tiles | 6.6 GB | Alaska 2.4 GB; lower 48 4.5 GB in all |
| fetch: WorldCover, streamed | 11.6 GB | lower 48 9.09 GB, Alaska 2.46 GB |
| build: processed directories | 25-26 GB | Texas 2.2 GB *(fit)*, California 2.1 GB |
| build: relief and elevation rasters | 16-25 GB | Texas 1.5 GB |
| serve: compact pack | **4.4 GB** | Texas 374 MB, California 351 MB |
| serve: xz download | **≤ 1.0 GB** | |
| RAM: elevation.py mosaic, 37 B per pixel over the box | — | Texas 13.3 GB, California 9.9 GB, Alaska 56 GB |

**Peak working space, one state at a time:**
- **9.2 GB** keeping only compact packs. The largest transient is California or Texas
  at 4.8 GB (extract, tile cache, rasters, processed directory), plus 4.4 GB of packs.
- **46-56 GB** keeping every processed directory and its rasters.
- The Mac's 20 GB free is enough for the first and not the second.

Two states need work before they can be built at all:
- **Alaska:** its outline crosses the antimeridian, so elevation.py's single box would
  span the globe. Even its 23,056 outline tiles would be a 56 GB mosaic.
- **Hawaii:** its box stretches to Kure Atoll and holds 8,100 tiles, against 113 for the
  islands themselves.
- Both need per-island or tiled elevation. That is the stage the review already
  flagged, at 146 GB for the contiguous US in one mosaic.

| state | extract (GB) | graph nodes (M) | Terrarium (GB) | box mosaic RAM (GB) | processed + rasters (GB) | compact pack (MB) |
|---|---:|---:|---:|---:|---:|---:|
| TX *(fit)* | 0.72 | 1.63 | 0.29 | 13.3 | 3.7 | 374 |
| CA | 1.33 | 1.53 | 0.22 | 9.9 | 3.2 | 351 |
| FL *(fit)* | 0.66 | 1.05 | 0.05 | 4.6 | 2.0 | 242 |
| IL *(fit)* | 0.36 | 0.71 | 0.08 | 2.4 | 1.3 | 164 |
| GA *(fit)* | 0.36 | 0.70 | 0.07 | 2.2 | 1.2 | 160 |
| NY *(fit)* | 0.50 | 0.67 | 0.08 | 4.0 | 1.4 | 154 |
| PA *(fit)* | 0.35 | 0.66 | 0.08 | 1.7 | 1.1 | 153 |
| OH *(fit)* | 0.33 | 0.66 | 0.06 | 1.7 | 1.1 | 152 |

## 3. OSM quality

Two tiers, as the brief set them:
- **Tier 2, measured:** length-weighted over the graph graph.py would build, in 16
  states.
- **Tier 1, the proxy:** object counts from Geofabrik's per-state taginfo, for all 51.

The sample is:
- the six New England extracts in `data/raw/` (2026-08-25);
- the review's Colorado extract (2026-10-10);
- nine more, fetched one at a time from Geofabrik on 2026-10-11 and deleted after
  measuring: South Dakota, Utah, Wyoming, Montana, Washington, Kansas, Tennessee,
  Oregon and Mississippi. That is 1,436 MB of downloads, spread across the West,
  Plains, South and Northwest.

`osm_metrics.py` rebuilds graph.py's graph without writing it: DRIVABLE plus the access
rule, oneway inference, splits at shared nodes, the 1 m drop, the largest strongly
connected component. Every metric is then weighted by the km of edges in that component.
**It reproduces count_graph.py's node and edge counts exactly on every state where both
were run:** the six New England states and Colorado. California, the review's eighth,
was not fetched. On Colorado it also reproduces every figure the review published:
- 40.7% unpaved and 27.3% untagged;
- 3,593 km `smoothness` bad or worse, and 938 km `4wd_only`;
- maxspeed tagged 97/82/66/53/20/3.5/6.4% from motorway down to residential.

### 3.1 Measured, by km, in 16 states

Speed limits, and tagged speed against graph.py's `SPEED_KMH`. That table is fitted on
Massachusetts, so New England sits near 0; positive means the posted limit is higher
than the default.

| state | graph nodes | graph km | maxspeed tagged, % of km: primary / secondary / tertiary / unclassified / residential | tagged vs default, %: primary / secondary / tertiary / unclassified |
|---|---:|---:|---|---|
| CO | 398,656 | 169,977 | 66 / 53 / 20 / 4 / 6 | +30 / +26 / +23 / +35 |
| CT | 148,215 | 39,571 | 32 / 27 / 20 / 26 / 10 | +1 / +10 / +1 / −18 |
| KS | 338,569 | 241,554 | 58 / 43 / 16 / 5 / 2 | +57 / +51 / +50 / +99 |
| ME | 129,083 | 58,209 | 31 / 26 / 18 / 7 / 4 | +12 / +24 / +26 / +17 |
| MA | 310,627 | 66,125 | 56 / 39 / 25 / 12 / 11 | −3 / 0 / +1 / 0 |
| MS | 299,351 | 150,157 | 24 / 13 / 6 / 1 / 1 | +37 / +36 / +28 / +6 |
| MT | 151,399 | 141,702 | 34 / 24 / 5 / 1 / 1 | +66 / +59 / +49 / +42 |
| NH | 93,542 | 31,622 | 77 / 75 / 63 / 26 / 18 | +11 / +12 / +10 / +30 |
| OR | 268,778 | 117,990 | 55 / 35 / 11 / 1 / 12 | +26 / +26 / +13 / +2 |
| RI | 53,823 | 10,680 | 27 / 21 / 11 / 10 / 5 | −11 / −8 / −13 / −17 |
| SD | 122,678 | 130,063 | 28 / 21 / 6 / 1 / 1 | +48 / +49 / +49 / +92 |
| TN | 469,411 | 180,988 | 28 / 14 / 8 / 2 / 2 | +28 / +24 / +26 / +19 |
| UT | 191,246 | 75,981 | 78 / 57 / 23 / 2 / 19 | +42 / +31 / +8 / +11 |
| VT | 62,508 | 28,102 | 43 / 39 / 22 / 6 / 6 | +14 / +22 / +19 / +33 |
| WA | 449,861 | 149,062 | 91 / 67 / 38 / 6 / 22 | +22 / +22 / +21 / +42 |
| WY | 77,030 | 69,387 | 52 / 32 / 15 / 5 / 2 | +66 / +48 / +56 / +75 |

Surface and roughness:
- "4WD or very bad" is `4wd_only=yes` or `smoothness` very_bad or worse.
- "TIGER A5x unflagged" is graph km whose `tiger:cfcc` is the 2005 import's 4WD
  vehicular-trail class, with no `4wd_only`, rough `smoothness` or grade 3-5
  `tracktype` beside it.

| state | surface tagged % | unpaved % | `smoothness` tagged % | `4wd_only` km | 4WD or very bad km | TIGER A5x km, unflagged | `tiger:reviewed=no` % |
|---|---:|---:|---:|---:|---:|---:|---:|
| CO | 73 | 40.8 | 4.2 | 901 | 1,852 | 927 | 33 |
| CT | 38 | 2.1 | 1.5 | 0 | 1 | 38 | 71 |
| KS | 38 | 26.7 | 0.1 | 12 | 38 | 914 | 68 |
| ME | 36 | 14.3 | 1.0 | 0 | 10 | 224 | 51 |
| MA | 47 | 5.9 | 0.3 | 0 | 4 | 0 | 1 |
| MS | 16 | 3.5 | 0.7 | 0 | 1 | 33 | 76 |
| MT | 33 | 26.6 | 0.1 | 16 | 61 | 1,499 | 57 |
| NH | 74 | 16.9 | 0.3 | 1 | 2 | 282 | 64 |
| OR | 55 | 26.1 | 1.3 | 2 | 248 | 145 | 30 |
| RI | 45 | 1.4 | 0.2 | 0 | 0 | 4 | 66 |
| SD | 62 | 47.8 | 0.0 | 0 | 1 | 3,296 | 58 |
| TN | 14 | 1.5 | 0.5 | 13 | 44 | 139 | 62 |
| UT | 76 | 35.8 | 16.1 | 567 | 1,458 | 303 | 10 |
| VT | 90 | 46.5 | 0.6 | 0 | 13 | 164 | 52 |
| WA | 46 | 19.3 | 1.1 | 6 | 165 | 555 | 40 |
| WY | 55 | 39.0 | 2.4 | 18 | 762 | 772 | 42 |

Controls, restrictions and closures, by km:
- **seasonal:** what closures.py closes for part of the year;
- **unread:** car conditionals its grammar rejects as unrecognised;
- **all year:** what its all-year rule closes, with the `permit` share after the comma.

| state | signals / stops / give-ways per 100 km | via-node / via-way restrictions per 1,000 junctions | seasonal km | unread km | all-year km, of which permit |
|---|---|---|---:|---:|---|
| CO | 7.4 / 14.4 / 0.8 | 22.3 / 4.6 | 188.8 | 97.8 | 280, 153 |
| CT | 18.9 / 39.8 / 0.7 | 18.1 / 1.5 | 2.3 | 0 | 14, 0 |
| KS | 1.7 / 3.3 / 0.3 | 7.6 / 2.5 | 0.8 | 0 | 6, 3 |
| ME | 2.8 / 3.6 / 0.4 | 9.0 / 0.8 | 43.7 | 0 | 48, 24 |
| MA | 16.4 / 23.1 / 1.2 | 26.7 / 2.8 | 28.6 | 0 | 83, 5 |
| MS | 2.0 / 3.2 / 0.8 | 4.6 / 0.1 | 0 | 0 | 8, 5 |
| MT | 0.7 / 0.6 / 0.1 | 4.1 / 0.1 | 85.9 | 0 | 90, 4 |
| NH | 6.4 / 16.4 / 1.1 | 18.8 / 1.7 | 60.0 | 0 | 32, 1 |
| OR | 4.3 / 10.2 / 0.4 | 39.0 / 1.5 | 165.4 | 0 | 175, 40 |
| RI | 15.4 / 7.3 / 1.8 | 15.4 / 1.7 | 0 | 0 | 3, 0 |
| SD | 0.9 / 1.1 / 0.1 | 8.9 / 0.3 | 31.9 | 0 | 7, 1 |
| TN | 4.2 / 2.3 / 0.2 | 7.6 / 0.7 | 0 | 0 | 11, 2 |
| UT | 6.1 / 19.1 / 1.8 | 16.8 / 2.3 | 326.9 | 0.5 | 238, 138 |
| VT | 1.7 / 7.7 / 0.3 | 23.4 / 0.5 | 45.9 | 0 | 22, 7 |
| WA | 5.8 / 13.0 / 0.8 | 36.0 / 1.8 | 249.5 | 7.5 | 3,795, 272 |
| WY | 0.7 / 2.3 / 0.1 | 3.9 / 0.6 | 53.8 | 0 | 10, 3 |

What the tables say:
- **Speeds are the most uniform defect.** Every state outside southern New England posts
  higher limits than the Massachusetts-fitted defaults, and the ones that matter most
  are where tagging is thinnest. Kansas tags 16% of its tertiary km at +50% over the
  default, and 5% of its unclassified km at +99%. graph.py's own method, a
  length-weighted harmonic mean over tagged roads, can be rerun per state as it
  stands. Whether untagged roads are driven like tagged ones is the open question
  (§8).
- **4WD is several signals, and the pipeline reads none of them.** Utah and Colorado tag
  `4wd_only` and `smoothness` heavily (1,458 and 1,852 km very bad or 4WD). The Plains
  states carry the TIGER A5x class instead, with no roughness tag at all on it.
- **`tracktype` grade 3-5 on drivable roads** is a minor signal: 975 km in Colorado, 934
  in Utah, 558 in Montana, 362 in Maine, under 300 everywhere else. `highway=track`
  carries it, and the graph leaves those out.
- **Washington's 3,795 km closed all year is `access=forestry`, 3,345 km of it.** These
  are state and timber-company logging roads. They are in the graph because graph.py's
  access rule only drops `private` and `no`; closures.py's mask removes them at
  routing time. So the behaviour is right and the graph carries dead weight.
- **Turn restrictions** run from 3.9 per 1,000 junctions (Wyoming) to 39.0 (Oregon).
  Via-way restrictions, which graph.py skips, are 0.1-4.6 per 1,000: a constant small
  loss, not a regional one.
- **`tiger:reviewed=no`** is 1% of Massachusetts' km (its roads came from a MassGIS
  import, not TIGER) and 76% of Mississippi's. It measures how much of the TIGER 2005
  geometry nobody has touched, which is where the A5x tracks sit.

### 3.2 The proxy, for all 51

`taginfo_proxy.py` reads each state's taginfo at about 27 calls a state, all cached.
Two proxies:
- **class proxy:** per DRIVABLE class, the share of its ways with the tag, from one
  `tag/combinations` call per class.
- **naive proxy:** the share of every `highway=*` way, footways and service roads
  included.

**These are object counts and a proxy only.** Taginfo cannot apply the access rule or
the connected component, and a 20 km pass counts the same as a 30 m stub. Three things
taginfo cannot do:
- **Rare tags.** It only pairs tags above a usage floor. `seasonal=summer` on Colorado's
  35 ways has no combinations at all, so seasonal and conditional tags can only be
  counted at key level, on any `highway=`.
- **Texas.** Geofabrik's Texas instance has **no combination statistics** (every class
  returned total 0 on 2026-10-08), so its class proxies are missing, not zero.
- **Small classes.** Link roads and `living_street` are below the floor nearly
  everywhere.

The km estimates below apply the straight-line calibration fitted on the 16 sampled
states, which are starred (§3.3; `osm_quality_all_states.csv`).

| state | drivable ways | unpaved %: proxy → km est. | tertiary maxspeed %: proxy → km est. | `tiger:reviewed=no` % (km est.) | `4wd_only` % of ways | signals per 100 km (proxy) | ways with `seasonal` / car `*:conditional` |
|---|---:|---|---|---:|---:|---:|---|
| AL | 302,229 | 1.9 → 10 | 19 → 13 | 82 | 0.00 | 4.5 | 0 / 4 |
| AK | 41,621 | 15.5 → 30 | 32 → 24 | 54 | 0.00 | 3.5 | 93 / 2 |
| AZ | 375,804 | 6.1 → 16 | 31 → 24 | 27 | 0.00 | 9.5 | 4 / 124 |
| AR | 207,025 | 5.5 → 15 | 14 → 10 | 57 | 0.00 | 1.9 | 2 / 14 |
| CA | 1,243,279 | 1.6 → 10 | 34 → 25 | 43 | 0.00 | 31.2 | 413 / 798 |
| CO* | 301,963 | 11.6 → 41 | 34 → 20 | 33 | 0.13 | 8.9 | 181 / 233 |
| CT* | 108,899 | 1.4 → 2 | 19 → 20 | 71 | 0.00 | 22.8 | 6 / 23 |
| DE | 44,539 | 0.3 → 8 | 25 → 18 | 37 | 0.00 | 20.0 | 0 / 1 |
| DC | 15,553 | 0.0 → 7 | 41 → 31 | 14 | 0.00 | 113.9 | 0 / 70 |
| FL | 884,731 | 1.1 → 9 | 34 → 26 | 46 | 0.00 | 19.4 | 0 / 234 |
| GA | 488,181 | 4.5 → 14 | 31 → 23 | 63 | 0.00 | 6.8 | 20 / 22 |
| HI | 34,742 | 1.6 → 10 | 25 → 18 | 17 | 0.00 | 22.5 | 0 / 15 |
| ID | 125,967 | 7.9 → 19 | 24 → 17 | 58 | 0.00 | 1.6 | 10 / 26 |
| IL | 485,394 | 0.7 → 8 | 28 → 20 | 66 | 0.00 | 8.7 | 70 / 195 |
| IN | 309,651 | 1.7 → 10 | 26 → 19 | 68 | 0.00 | 6.5 | 4 / 59 |
| IA | 190,477 | 14.7 → 29 | 16 → 11 | 74 | 0.00 | 2.5 | 2 / 2 |
| KS* | 207,653 | 8.9 → 27 | 24 → 16 | 68 | 0.00 | 1.8 | 1 / 36 |
| KY | 232,575 | 0.8 → 8 | 17 → 12 | 81 | 0.00 | 4.0 | 0 / 29 |
| LA | 223,135 | 0.9 → 8 | 35 → 27 | 66 | 0.00 | 4.8 | 0 / 15 |
| ME* | 90,641 | 6.2 → 14 | 28 → 18 | 51 | 0.00 | 4.6 | 30 / 41 |
| MD | 211,134 | 0.4 → 8 | 38 → 29 | 38 | 0.00 | 20.3 | 5 / 91 |
| MA* | 231,645 | 5.3 → 6 | 27 → 25 | 1 | 0.00 | 19.4 | 204 / 213 |
| MI | 386,561 | 9.3 → 21 | 52 → 41 | 63 | 0.00 | 6.0 | 63 / 71 |
| MN | 284,525 | 19.7 → 36 | 29 → 22 | 60 | 0.00 | 3.7 | 137 / 55 |
| MS* | 187,057 | 1.7 → 4 | 13 → 6 | 76 | 0.00 | 2.4 | 0 / 0 |
| MO | 389,135 | 3.5 → 12 | 31 → 24 | 74 | 0.00 | 3.8 | 16 / 37 |
| MT* | 99,332 | 14.7 → 27 | 8 → 5 | 57 | 0.00 | 0.8 | 40 / 77 |
| NE | 130,114 | 25.9 → 45 | 71 → 56 | 59 | 0.00 | 3.0 | 0 / 8 |
| NV | 138,269 | 6.0 → 16 | 30 → 22 | 42 | 0.00 | 9.2 | 3 / 55 |
| NH* | 69,788 | 11.4 → 17 | 56 → 62 | 64 | 0.00 | 8.4 | 33 / 108 |
| NJ | 254,370 | 0.2 → 8 | 27 → 20 | 80 | 0.00 | 20.9 | 13 / 120 |
| NM | 155,721 | 13.3 → 27 | 25 → 19 | 70 | 0.21 | 3.0 | 915 / 3 |
| NY | 457,943 | 1.5 → 9 | 36 → 27 | 62 | 0.00 | 20.3 | 144 / 743 |
| NC | 515,352 | 3.1 → 12 | 46 → 36 | 54 | 0.00 | 9.7 | 5 / 39 |
| ND | 60,413 | 45.9 → 74 | 11 → 6 | 78 | 0.00 | 0.6 | 4 / 0 |
| OH | 431,397 | 0.6 → 8 | 33 → 25 | 57 | 0.00 | 8.6 | 13 / 39 |
| OK | 331,660 | 2.8 → 11 | 63 → 49 | 57 | 0.00 | 4.6 | 0 / 125 |
| OR* | 202,496 | 6.1 → 26 | 37 → 10 | 30 | 0.00 | 4.1 | 26 / 151 |
| PA | 503,153 | 2.4 → 11 | 30 → 22 | 60 | 0.00 | 10.8 | 40 / 678 |
| RI* | 36,731 | 0.7 → 1 | 16 → 11 | 66 | 0.00 | 16.4 | 0 / 3 |
| SC | 265,874 | 7.9 → 19 | 19 → 13 | 46 | 0.00 | 4.8 | 0 / 3 |
| SD* | 76,083 | 24.5 → 48 | 11 → 6 | 58 | 0.00 | 0.9 | 24 / 3 |
| TN* | 311,490 | 0.7 → 2 | 10 → 8 | 62 | 0.00 | 5.0 | 0 / 123 |
| TX | 1,295,807 | – → – | – → – | – | – | 9.5 | 1 / 1103 |
| UT* | 143,791 | 7.1 → 36 | 43 → 23 | 10 | 0.08 | 6.1 | 655 / 163 |
| VT* | 45,753 | 33.9 → 46 | 27 → 22 | 52 | 0.00 | 2.1 | 22 / 62 |
| VA | 366,814 | 2.5 → 11 | 31 → 23 | 57 | 0.00 | 15.8 | 4 / 121 |
| WA* | 336,945 | 6.5 → 19 | 52 → 38 | 40 | 0.00 | 6.9 | 95 / 331 |
| WV | 124,403 | 3.7 → 13 | 9 → 5 | 61 | 0.00 | 3.4 | 0 / 14 |
| WI | 310,290 | 2.6 → 11 | 33 → 25 | 66 | 0.00 | 5.5 | 50 / 172 |
| WY* | 52,816 | 22.4 → 39 | 13 → 15 | 42 | 0.00 | 1.1 | 1 / 35 |

### 3.3 How well the proxy predicts the km

Across the 16 sampled states: each proxy against the km value it stands for
(`proxy_accuracy.csv`). Errors are in percentage points, or in the metric's own unit
where it is a rate. "Calibrated" fits a straight line on 15 states and predicts the
16th, which is what using the proxy for an unsampled state would cost.

| metric (proxy → km value) | r | km mean | proxy mean | raw error | calibrated error | worst raw error |
|---|---:|---:|---:|---:|---:|---:|
| maxspeed tagged, motorway | 0.95 | 94.0 | 93.0 | 1.9 | 2.0 | 6.9 |
| maxspeed tagged, trunk | 0.94 | 68.9 | 71.6 | 5.7 | 6.1 | 11.7 |
| maxspeed tagged, primary | 0.90 | 48.8 | 56.9 | 9.6 | 9.1 | 25.5 |
| maxspeed tagged, secondary | 0.89 | 36.6 | 46.1 | 10.2 | 7.4 | 34.6 |
| maxspeed tagged, tertiary | 0.84 | 19.2 | 26.1 | 8.1 | 6.3 | 26.7 |
| maxspeed tagged, unclassified | **0.32** | 7.2 | 7.8 | 4.8 | 6.1 | 26.4 |
| maxspeed tagged, residential | 0.91 | 7.6 | 8.6 | 2.5 | 2.4 | 7.4 |
| `surface` tagged | 0.97 | 49.9 | 40.3 | 9.6 | 4.6 | 17.3 |
| unpaved share | 0.84 | **22.1** | **10.2** | 11.9 | 8.6 | 29.1 |
| `smoothness` tagged | 0.99 | 1.9 | 1.6 | 0.4 | 1.1 | 2.3 |
| `tiger:reviewed=no` | 0.98 | 48.7 | 43.4 | 5.6 | 3.6 | 11.4 |
| `4wd_only` share | 0.92 | 0.08 | 0.01 | 0.07 | 0.07 | 0.66 |
| naive maxspeed (all highway ways) → any maxspeed on drivable km | 0.68 | 16.3 | 4.6 | 11.7 | 5.0 | 30.3 |
| naive surface (all highway ways) → surface tagged on drivable km | 0.91 | 49.9 | 26.7 | 23.2 | 8.0 | 51.1 |
| signal nodes / FHWA public-road km → signals per 100 graph km | 0.99 | 6.0 | 7.0 | 1.1 | 0.5 | 3.8 |
| restriction relations / drivable ways → via-node restrictions per 1,000 junctions | 0.91 | 16.4 | 23.5 | 7.1 | 3.3 | 21.6 |

- **Direction matters as much as size.** Counting objects *understates* the unpaved
  share by half, because unpaved roads are long rural ways and paved streets are short.
  It *overstates* tagged speed limits on primary to tertiary roads by 7-10 points,
  because the tagged ways are the short urban ones. The naive proxy, footways
  included, is the worst of all: it puts surface tagging at half its km value.
- **Usable as is:** `tiger:reviewed`, `smoothness`, signals, and motorway, trunk and
  residential speed limits.
- **Usable after calibration:** surface and unpaved share (±5-9 points), the
  primary-to-tertiary speed limits (±6-9), restrictions (±3 per 1,000).
- **Not usable:** unclassified speed limits (r = 0.32, partly because taginfo drops the
  class's combinations below its floor in some states), every seasonal or conditional
  tag, and anything in Texas. For those, sample the state.

## 4. Seasonal closures: 23 roads against their operators

Each road's actual closure came from its operator first: NPS, CDOT, MDT, WYDOT, Caltrans,
WSDOT, UDOT, SD Game Fish and Parks, the Auto Road's operator. Only then was OSM
checked. `seasonal_check.py` finds the road's ways inside its box by name or ref and
reads every closure-type tag on them and on their barrier nodes. It then runs
closures.py's own `way_windows`. California came from one small Overpass query, because
its extract (1.3 GB) was not sampled. The brief's 18 roads plus the Kancamagus control
are joined by three extras: Yellowstone's Grand Loop, Kuwohi Road and the Needles
Highway. The Beartooth is split at the state line, which makes 23 rows. Sources and
notes are in `seasonal_truth.json`; the joined table is `seasonal_ground_truth.csv`. The
window shown is the one covering the most km of the road.

| road | official closure | in graph (km) | closures.py closes (km, window) | verdict |
|---|---|---:|---|---|
| Trail Ridge Rd (US 34, RMNP) (CO) | Normally opens the last week in May; closes to through travel around Oct 23 on average (mid-October to early November), gated at Rainbow Curve and the Colorado River Trailhead | 70.2 | 0.0 | **tagged, not read** |
| Old Fall River Rd (RMNP) (CO) | Open to vehicles from about July 4 to early October, one way uphill | 14.2 | 0.0 | **free text only** |
| Independence Pass (CO 82) (CO) | Closed Aspen to Twin Lakes from late October or November (Oct 25 to Nov 17, 2011-2025) until the week before Memorial Day | 65.8 | 36.7, 11/15-5/15 | **closed, window loose** |
| Mount Blue Sky Rd (CO 5) (CO) | Summit open from the Friday before Memorial Day to Labor Day, Echo Lake to Summit Lake to about Sep 30 (and closed 2024-2026 for construction) | 29.3 | 23.1, 11/1-4/30 | **closed, window loose** |
| Going-to-the-Sun Rd (Glacier NP) (MT) | Alpine section (Avalanche Creek to Jackson Glacier Overlook) closes on or before the third Monday of October; fully open from about late June (Jun 22 in 2026) | 79.3 | 63.0, 10/1-6/30 | **closed** |
| Beartooth Hwy (US 212), Montana part (MT) | Open from the Friday of Memorial Day weekend to about Oct 15 (May 22 - Oct 12 in 2026); MDT's seasonal closure is US 212 mileposts 45-56 | 70.3 | 8.7, 11/1-4/30 | **mostly untagged** |
| Beartooth Hwy (US 212), Wyoming part (WY) | WYDOT closes US 212 between WY 296 and Beartooth Pass for the season (closed as of Oct 11, 2026) | 60.1 | 8.4, 12/1-3/31 | **mostly untagged** |
| Teton Park Rd (Grand Teton NP) (WY) | Closed to motor vehicles Nov 1 - Apr 30 between Taggart Lake Trailhead and Signal Mountain Lodge | 33.8 | 0.0 | **untagged** |
| Grand Loop Rd (Yellowstone NP), bonus (WY) | Most park roads close to wheeled vehicles at the end of October or early November until late April; only North to Northeast Entrance stays open | 225.5 | 0.0 | **untagged** |
| Tioga Rd (CA 120, Yosemite) (CA) | Typically open from late May or June until sometime in November (May 15 in 2026) | 88.2 | 88.1, 11/1-5/31 | **closed** |
| Sonora Pass (CA 108) (CA) | Closed from the Sno-Park east of Strawberry to US 395 (Dec 26, 2025 - Apr 30, 2026, the earliest reopening in five years) | 64.6 | 37.5, 12/1-4/30 | **closed, window loose** |
| Ebbetts Pass (CA 4) (CA) | Closed from Lake Alpine to the Raymond Meadows gate (Dec 26, 2025 - May 6, 2026; the goal is Memorial Day) | 32.3 | 32.3, 11/1-4/30 | **closed, window loose** |
| Glacier Point Rd (Yosemite) (CA) | Closed beyond Badger Pass from sometime in November through late May or early June | 25.0 | 0.0 | **untagged** |
| Lassen Park Hwy (CA 89, Lassen Volcanic NP) (CA) | Closes for the season in mid to late November; reopens late May to early July depending on snowpack | 51.8 | 41.1, 11/1-4/30 | **closed, window loose** |
| North Cascades Hwy (WA 20) (WA) | Closed between Ross Dam Trailhead (MP 134) and Silver Star gate (MP 171); closure date varies (Oct 17 to Jan 3), reopening usually late April or May (Jun 14 in 2026 after storm damage) | 81.0 | 54.7, 11/1-4/30 | **closed** |
| Chinook Pass (WA 410) (WA) | Closes in mid-November; reopens around Memorial Day (May 22 in 2026) | 30.4 | 18.6, 11/1-5/31 | **closed** |
| Hurricane Ridge Rd (Olympic NP) (WA) | Winter (late November to end of March): open Friday to Sunday and some holidays, 9 am - 4 pm, weather permitting | 21.4 | 0.0 | **untagged (part-time)** |
| Rim Drive (Crater Lake NP) (OR) | Rim Drive closes to cars with the first big storm or Nov 1; West Rim reopens mid-May to late June, East Rim mid-June to late July | 51.2 | 0.0 | **free text only** |
| Mirror Lake Hwy (UT 150) (UT) | SR-150 closed east of Kamas through the winter, typically November through May or June (reopened May 22, 2026) | 69.3 | 54.6, 11/1-5/31 | **closed** |
| Mt Washington Auto Rd (NH) | Closed to private vehicles in winter (SnowCoach December - March); summer season from about mid-May to late October | 12.4 | 12.2, 11/1-4/30 | **closed, window loose** |
| Kancamagus Hwy (NH 112), year-round control (NH) | Open all year: NH 112 is a state highway, which NHDOT maintains year-round | 59.9 | 0.0 | **correctly open** |
| Kuwohi Rd, formerly Clingmans Dome Rd (Great Smoky Mountains NP), bonus (TN) | Kuwohi Road (formerly Clingmans Dome Road): 2026 season Apr 1 - Nov 29 | 11.0 | 0.0 | **untagged** |
| Needles Hwy (SD 87, Custer SP), bonus (SD) | Closes to vehicles with the first snow; reopens no earlier than April 1 | 58.4 | 31.5, 11/1-4/30 | **closed** |

**Of the brief's 18 seasonal roads, closures.py closes 11 and leaves 7 open**:
- **Trail Ridge Road:** tagged, but not read.
- **Old Fall River and Crater Lake's Rim Drive:** free text only.
- **Glacier Point Road and Teton Park Road:** untagged.
- **Hurricane Ridge:** a part-time closure, which closures.py deliberately ignores.
- **The Beartooth Highway:** mostly untagged, 17 of 130 km closed.

Of the 11 it closes, six leave the road open for a week or more while it is officially
closed. Five things cause it:
1. **Ordinal dates.** `no @ Oct 14th - May 31st` (Trail Ridge, 66 km) and
   `no @ Nov 19th - May 30th` (18 km) fail `_RANGE`, which expects `Oct 14`. Dropping
   the suffix alone would close **84.7 km in Colorado**, Trail Ridge among them. One
   more, `no@(Dec 1 - Mai 1)` (13 km), spells May in German, and Washington has
   `no @ (8 Dec - 1 May)` with the day first (7.5 km).
2. **The generic winter.** `seasonal=yes|summer|no_snow` and `winter_service=no` read as
   Nov 1-Apr 30. High passes open in late May to July, so Lassen, Ebbetts, Sonora, the
   Auto Road and Mount Blue Sky are routed open for two to ten weeks of real closure.
   Mount Blue Sky's summit closes the day after Labor Day, so it is open in closures.py
   through most of September and October as well.
3. **The permit rule.** Trail Ridge carries `access=permit` and `vehicle=permit`
   (RMNP's timed-entry reservation, 9 am-2 pm in season). The all-year rule closes
   permit, so in the review's Colorado build Trail Ridge was shut **every day of the
   year**, 39 edges and 66.8 km. That is a closed road routed around in July, the
   opposite failure to the one the review reported. Utah has 138 km of permit roads
   and Washington 272 km. docs/closed-roads.md already lists this as decision 3's cost
   in Maine; in the West it closes park roads.
4. **Gates are counted, not read.** Mirror Lake's two "Winter Closure" gates and the
   North Cascades' Ross Dam and Silver Star gates carry `*:conditional` on the node.
   closures.py reads way conditionals only; for gates it counts the timed ones and
   moves on. These four are redundant with tags on their ways. Elsewhere a gate can be
   the only tag a closure has.
5. **Untagged roads need another source, and one exists for most of them.** NPS's public
   roads layer marks Glacier Point (`Winter`), Teton Park Road (`Seasonal Closure Nov1
   to May1`), Tioga, both Crater Lake rim drives and Old Fall River as seasonal. It says
   **Unknown for 1,979 of Yellowstone's 2,007 segments**, though, and its dates are
   prose. On Forest Service roads, MVUM has machine-readable dates (§6.4).

Two more things the table shows:
- **Names drift.** Clingmans Dome Road became **Kuwohi Road** in 2024, and a name match
  for the old one finds nothing. Matching by geometry, not name, is the safe join for
  any external closure source.
- **The control holds.** The Kancamagus has no closure tag and none is read.

## 5. Byways: the census

`byway_census.py` combines two sources. Per-state taginfo gives every relation `network`
naming a scenic system (51 calls). One Overpass query gives every road route tagged
`scenic=yes`. The 86 of those with no network were placed by their member geometry's
centre, inside the Census outlines. The network-regex query was tried twice and timed
out both times (504), so taginfo stands in for it. extract.py admits a relation when its
network is in `BYWAY_NETWORKS` or it carries `scenic=yes`.

| state | scenic-system networks (relations) | admitted by network | `scenic=yes` relations | missed | numbered highways carrying `scenic=yes` |
|---|---|---:|---:|---:|---|
| AL | — | 0 | 2 | 0 | US:AL 281 |
| AK | — | 0 | 2 | 0 |  |
| AZ | US:AZ:Scenic (24) | 0 | 27 | 2 |  |
| CA | US:CA:CR:Scenic (2); US:CA:San_Francisco:49_Mile_Scenic_Drive (1); US:CA:Scenic (21) | 0 | 10 | 22 | US:CA 160 |
| CO | US:CO:Scenic (26) | 0 | 11 | 15 |  |
| CT | — | 0 | 1 | 0 |  |
| FL | US:FL:Scenic (27) | 0 | 28 | 0 |  |
| GA | US:GA:Scenic (2) | 0 | 2 | 1 |  |
| HI | — | 0 | 1 | 0 |  |
| ID | — | 0 | 6 | 0 |  |
| IL | — | 0 | 1 | 0 |  |
| IA | US:IA:Scenic (21) | 0 | 0 | 21 |  |
| KS | US:KS:Scenic (1); US:KS:Scenic Byway (1) | 0 | 1 | 1 |  |
| KY | US:KY:Scenic (15) | 0 | 3 | 15 |  |
| LA | — | 0 | 1 | 0 |  |
| ME | — | 0 | 3 | 0 |  |
| MD | US:MD:Scenic (1) | 0 | 3 | 1 | US:MD 25 |
| MA | US:MA:Scenic (14) | 14 | 0 | 0 |  |
| MI | — | 0 | 1 | 0 |  |
| MN | — | 0 | 5 | 0 |  |
| MS | US:MS:Scenic (4) | 0 | 0 | 4 |  |
| MT | — | 0 | 2 | 0 |  |
| NE | US:NE:Scenic (9) | 0 | 0 | 9 |  |
| NV | US:NV:NSB (1); US:NV:Scenic (7) | 0 | 3 | 8 | US:NV 158 |
| NH | — | 0 | 5 | 0 |  |
| NJ | US:NJ:Scenic (12); US:NJ:Scenic:Alt (1); US:NJ:Scenic:Connector (2); US:NJ:Scenic:Loop (2); US:NJ:Scenic:Spur (2) | 0 | 12 | 7 |  |
| NM | US:NM:Scenic (1) | 0 | 6 | 1 | US:NM 503 |
| NY | US:NY:Scenic (25); US:NY:Scenic:Alternate (5) | 25 | 5 | 3 | US:NY 30 |
| NC | US:NC:Scenic_Byway (2) | 0 | 4 | 0 |  |
| ND | — | 0 | 1 | 0 |  |
| OH | US:OH:Byway (26); US:OH:Scenic (1) | 0 | 1 | 26 |  |
| OK | — | 0 | 1 | 0 |  |
| OR | US:OR:Scenic (19); US:OR:Tour (10) | 0 | 6 | 23 |  |
| PA | US:PA:Scenic (6) | 0 | 1 | 6 |  |
| SC | US:SC:Scenic (1) | 0 | 4 | 1 | US:SC Cherokee Foothills National Scenic Byway |
| SD | US:SD:Scenic (2) | 0 | 1 | 1 |  |
| TN | US:TN:secondary:Scenic (1) | 0 | 6 | 1 |  |
| UT | — | 0 | 12 | 0 | US:UT 128; US:UT 211; US:UT 279; US:UT 313 |
| VT | US:VT:byway (9) | 9 | 9 | 0 |  |
| VA | — | 0 | 2 | 0 |  |
| WA | — | 0 | 7 | 0 | US:WA Mount Baker Scenic Byway |
| WV | — | 0 | 2 | 0 |  |
| WI | US:WI:Scenic (6) | 0 | 14 | 0 |  |
| WY | — | 0 | 1 | 0 |  |

National networks with no state prefix: `US:AB:NSB` (2), `US:AB:NSB:Connecticut River`
(3, allowlisted), `US:AAR` (1), `US:Byway` (1), `US:US:Scenic` (1), `US:USFS:byway`
(1). Among the `scenic=yes` relations, the Great River Road (`US:GRR`, 16) and BLM Back
Country Byways (`US:BLM:BCB`, 13) are the largest network-wide sets. Parkway networks
(New York's, Kentucky's, Connecticut's) and the historic auto trails are road classes or
heritage routes. They are left out of "missed".

**Totals:**
- 310 relations in 25 states' byway networks. The allowlist admits 48 (Massachusetts 14,
  Vermont 9, New York 25).
- 213 relations nationally carry `scenic=yes`.
- **168 are missed.** Ohio's 26, Oregon's 23, California's 22, Iowa's 21, Colorado's and
  Kentucky's 15 each, Nebraska's 9, Nevada's 8 and New Jersey's 7 carry the byway
  network and no `scenic=yes`.

**Whole numbered highways:** 13 numbered-highway relations carry `scenic=yes`. Eleven
are short state routes, or byway relations filed under a state network, where the whole
route *is* the byway: Utah's 128, 211, 279 and 313, Alabama 281, Nevada 158, the
Cherokee Foothills, Mount Baker and others. **Two are not:**
- **US 34 in Colorado, 451 km** (Overpass length of the member ways), of which Trail
  Ridge is about 70 km.
- **NY 30, 485 km.**

extract.py would make every km of both a byway. A rule admitting a state's own byway
network by pattern (`US:XX:Scenic`, `US:XX:Byway`, `US:XX:Scenic_Byway`) would recover
the 168. It would also have to keep refusing the numbered-highway networks, which is
the trap byway-relations.md describes.

In the sampled states, by drivable km in relations named or tagged scenic:

| state | relations | drivable km | admitted km | share |
|---|---:|---:|---:|---:|
| CO | 32 | 4,801 | 1,749 | 36% |
| CT | 5 | 266 | 54 | 20% |
| KS | 4 | 246 | 96 | 39% |
| ME | 7 | 957 | 302 | 32% |
| MA | 19 | 737 | 737 | 100% |
| MS | 11 | 1,466 | 1,341 | 92% |
| MT | 4 | 158 | 158 | 100% |
| NH | 10 | 758 | 757 | 100% |
| OR | 24 | 4,260 | 1,360 | 32% |
| SD | 5 | 1,063 | 112 | 10% |
| TN | 22 | 1,239 | 1,236 | 100% |
| UT | 21 | 2,061 | 1,569 | 76% |
| VT | 13 | 1,631 | 1,631 | 100% |
| WA | 16 | 1,028 | 982 | 96% |
| WY | 5 | 224 | 213 | 95% |

The FHWA's national layer (§6.6) is an independent check, but a partial one. It holds
the 184 National Scenic Byways and All-American Roads as 227 per-state records:
Colorado has 13 of its 26 state byways in it.

## 6. The other layers

### 6.1 Terrarium

**Size.** The outlines of the 50 states and DC touch **58,947 z11 tiles**:
- 35,778 in the lower 48 and DC;
- 23,056 in Alaska;
- 113 in Hawaii.

The review's "about 60,400" for the contiguous US was its bounding box, which holds
60,060 by this count. A stratified HEAD sample of 4,839 tiles, up to 100 per state, puts
the total at **6.56 ± 0.06 GB** (one standard error). The mean per tile runs from 75 KB
(Rhode Island, Florida) to 143 KB (West Virginia), median 115 KB. Bytes follow terrain,
as the brief warned. Every sampled HEAD returned 200. The tiles were last modified in
November 2017, so corruption in them is permanent.

**Corruption.** `terrarium_survey.py`'s detector has two parts:
- **Out of band:** pixels outside elevation.py's −11,000..9,000 m band. elevation.py
  already masks these.
- **Residue:** what the band misses. A pixel counts if it sits more than 500 m from the
  median of its valid 7×7 neighbours, or more than 150 m and more than ten times their
  robust spread.
- Both tests run on the ocean-clamped elevation, which is what elevation.py's relief
  filter reads. So garbage bathymetry the clamp makes harmless does not count, and
  neither does a 30 m sea stack beside deep water. An unclamped first version flagged one
  on Maui.

The first test finds Colorado's fringe pixels: −639 m and exact-0 m pixels in 2,500 m
terrain, around blocks the band already masks. The second finds New England's coastal
spikes, 150-1,453 m beside 0 m. It raises **nothing on 21 control tiles**: Yosemite
Valley, Half Dome, El Capitan, the Grand Canyon twice, Zion, Hells Canyon, the Whitney
escarpment, Rainier, Denali, Kings Canyon, Logan Pass, Waimea Canyon, Na Pali, the
Columbia Gorge, the Tetons, Crater Lake, Lake Tahoe, Lake Chelan, Death Valley and New
Orleans. The one control it flags is the Salton Sea, where a 2×2 block of 304-479 m
sits in the middle of the water. That was checked pixel by pixel. Every residue is
priced two ways:
- the relief it adds;
- the pixels where it raises the relief *component* (relief / `RELIEF_FULL`, clipped)
  by 0.1 or more. That is the only harm a mountain tile already at the 100 m cap can
  show.

| tiles | decoded | out of band | residue | residue raises the relief component | largest relief added |
|---|---:|---:|---:|---:|---:|
| the review's Colorado cache (every tile in the state's box) | 1,656 | 2 | 3 | 1 | 3,941 m |
| `data/raw/terrain`, New England (every tile in the deployed box) | 2,120 | 9 | 31 | 31 | 1,453 m |
| national sample: 40 random tiles per state | 1,975 | 2 | 26 | 24 | 1,158 m |
| control tiles (steep, deep lakes, below sea level, coasts) | 22 | 0 | 1 | 1 | 479 m |

What the national sample says (`terrarium_corruption_rates.csv`). Each state is weighted
by its share of the outline tiles, with stratified binomial standard errors.
- **Lower 48 and DC:** 16 of 1,895 sampled tiles have residue that raises the relief
  component, about **111 ± 33 tiles of 35,778 (0.3%)**.
- **It is a coastal defect.** 19 of the 158 sampled coastal tiles (12%) carry it, against
  4 of 1,805 inland (0.2%). The 160 desert-state tiles (Arizona, Nevada, Utah, New
  Mexico) had none, and 1 of the 80 mountain tiles did. The hits sit on the Potomac,
  Patuxent and Chesapeake tidewater, the Delaware shore, Florida's Atlantic coast from
  Miami Beach to near Jacksonville, Cape Romain in South Carolina, Long Island Sound,
  Nantucket and the Maine coast.
- **Hawaii:** 5 of its 40, about 14 of 113 tiles. These are isolated 166-504 m pixels
  beside sea-level ground.
- **Alaska:** 3 of its 40, which weights to about 1,700 ± 1,000 tiles. That is too few
  hits to pin down. Two of them are not spikes but source seams: a straight 340 m step
  across many columns, and a two-column strip at a tile edge. Alaska needs its own pass
  before it is built.

In the mountains the harm is smaller than the metres suggest. Two of Colorado's three
bad tiles add 2,800-3,900 m of relief and change `c_relief` nowhere, because the
mountains around them are already at the 100 m cap. On a sea-level shore, a single
400 m pixel lifts every chunk within 375 m from flat to maximal relief.

**The deployed New England raster carries these.** `ne_relief_spikes.py` rebuilds
relief over each flagged New England tile from the deployed `elevation.tif`, with and
without the residue pixels. It checks the rebuild against the deployed `relief.tif`
first, then samples both at every scored chunk's midpoint, as score.py does.
That reproduces `relief.tif` exactly on all 31 tiles (13 px window), and finds **25.5 km
of scored road on 108 chunks inflated, by up to 1.72 score points**
(`ne_relief_spikes.json`). The largest patches:
- around Portland's Eastern Promenade: 46 chunks, 9.4 km, up to +1.63;
- Harpswell: 2.9 and 1.8 km, up to +1.45;
- Falmouth Foreside: 2.3 km;
- smaller ones at Provincetown (+1.46), Nantucket's Madequecham Valley Road (+1.72) and
  Baptist Hill Road inland in New Hampshire (+1.03), where a one-pixel-wide trench reads
  127-198 m through 430-470 m ground.

That is 0.01% of New England's 232,000 km. It is a real defect in what is deployed,
small in extent, and invisible to elevation.py's band.

**3DEP as the patch.** `dem3dep_vs_terrarium.py` looks up every pixel centre of 43
Colorado tiles in 3DEP's 1 arc-second DEM, read as windows of the COGs over HTTP:
- **On 40 random tiles**, Terrarium agrees with 3DEP to a median 1.9 m, p95 8.5 m, with
  a 0.1 m bias. Relief, the quantity score.py reads, agrees to a median 0.1 m and p95
  8.8 m.
- **On the three corrupt tiles**, 3DEP's minimum is 1,849, 2,409 and 2,726 m, where
  Terrarium's is −371, 0 and −639 m.

Terrarium's US source is 3DEP, and it shows: resampled 3DEP with a few hundred broken
pixels. Patching it from 3DEP needs only the flagged pixels' windows, a few MB, not
3DEP's 130 GB.

### 6.2 WorldCover

The outlines touch 211 3° cells, and 205 exist (`worldcover_cells.csv`):
- 131 cover the lower 48 and DC, 9.09 GB;
- 70 cover Alaska, 2.46 GB;
- 4 cover Hawaii, 0.02 GB.

The six absent cells are all Northwestern Hawaiian Islands water, with at most
0.0005 square degrees of outline land among them and no roads. The bucket passes the
control: a bogus tile name returns 404.

Quality for what landcover.py reads is the review's: median Colorado tree fraction 0.00,
57.8% of km at 0. That is a scenery problem, not a data defect. WorldCover's other
classes (shrub, grass, bare, snow) are what Western scenery would need, and the same
tiles carry them.

### 6.3 3DEP

The bucket listing (`dem3dep_sizes.json`, S3 ListObjects) gives exact current sizes:
- 1″: 3,812 cells, **130.3 GB**, including Alaska and the border cells;
- 1/3″: 1,449 cells, **493.5 GB**;
- Alaska's 2″: 521 cells, 5.3 GB.

The National Map's product API disagrees with its own bucket. It lists superseded
versions beside current ones and its paging repeats items, so its `sizeInBytes` sums
are not usable. Quality against Terrarium is in §6.1.

### 6.4 USFS Motor Vehicle Use Map

**The national schema** (`mvum_survey.py`; `mvum_national.json`) is one layer of 150,789
segments and 197,625 miles. Fields:
- `seasonal` (yearlong/seasonal);
- open or closed and **dates open per vehicle class**: `passengervehicle_datesopen`,
  `highclearancevehicle_datesopen` and twelve more, written `04/01-11/30`, 728 distinct
  strings;
- `operationalmaintlevel`, `surfacetype`, `symbol`.

Nationally:
- **73% of MVUM road miles are maintenance level 2, "high clearance vehicles"**
  (144,084 mi).
- Level 3 and up, suitable for passenger cars, is 52,596 mi.
- 47,105 mi are seasonal (symbols 2, 4 and 12).
- `passengervehicle=open` covers 191,555 mi. That is *legal*, not *suitable*: the
  maintenance level is the physical signal.

**Published forest by forest, as Trap 7 warned:**
- 450 of 503 ranger districts are marked as having MVUM data.
- Ten forests have none, or a handful of stray segments: Okanogan-Wenatchee (6.9 mi:
  the forest east of the North Cascades Highway and Chinook Pass), Modoc, Tonto,
  Apache-Sitgreaves, Malheur, Wallowa-Whitman, Angeles, Six Rivers, the National
  Forests in Alabama, and El Yunque (Puerto Rico).
- The Gallatin half of Custer Gallatin, around Bozeman and West Yellowstone, has 6 mi.

**Against OSM in one forest:** Grand Mesa, Uncompahgre and Gunnison NFs (Colorado), the
home of the review's top-ranked 4WD roads. `mvum_osm_match.py` walks every MVUM road at
25 m steps and gives each step the nearest OSM `highway=*` way within 15 m
(`mvum_osm_gmug.json`). That covers 4,428 km of MVUM road:
- 2,563 km (58%) are `highway=track` in OSM, outside the graph.
- 1,503 km (34%) are in the graph: unclassified 1,028, tertiary 342, residential 131.
- 283 km (6.4%) have no OSM way within 15 m.

Of the 307 km of maintenance-level-2 road in the graph:
- OSM flags 78% as `4wd_only` or rough `smoothness`;
- 11% has only an unpaved `surface`;
- 12% has nothing.

So on this forest OSM's 4WD tagging is good where mappers worked, and MVUM confirms
rather than corrects it.

**Seasons are where MVUM corrects OSM.** MVUM marks 1,419 km of this forest's roads
seasonal, 821 km of them in the graph. **closures.py closes 1.6 km of those 821.**
The other 819 km carry no seasonal tag in OSM at all.

### 6.5 TIGER/Line

**Size:** 3,144 county road files for the 50 states and DC, **3.88 GB** zipped (2026
vintage, released 2026-10-06; `tiger_2026_sizes.csv`, from the directory listing's
rounded sizes). The primary-and-secondary files are 0.28 GB.

TIGERweb counts segments nationally by MTFCC:
- S1400 local roads 13,903,067;
- **S1740 private service roads 1,221,450**;
- **S1500 4WD trails 302,858**.

**Against OSM in six counties of one sample state, Colorado** (Ouray, San Juan, Hinsdale,
San Miguel, Weld, Moffat: the San Juan 4WD country, an oil-and-ranch plains county and a
ranching county; `tiger_osm_colorado.json`), by the same matcher:
- **S1500, 2,912 km:** 56% is `highway=track` in OSM, 28% has no OSM way, and **13%
  (370 km) is in the graph**. Of those 370 km, 7% carries a 4WD or rough tag, 73% only
  an unpaved surface, and 21% nothing. TIGER's own 4WD class survives in OSM as
  `tiger:cfcc` A5x on 46 of them.
- **S1740, 819 km:** 8% (69 km) is in the graph, 66 km of it with no access tag.

So in Colorado, TIGER adds a 4WD flag to about 345 km of graph road per six counties
that OSM leaves unflagged, and a private flag to 69 km. The Plains states' A5x figures
(§3.1) say the 4WD share is larger there.

### 6.6 NPS roads and closures; FHWA byways

**NPS Public Roads** (`mapservices.nps.gov`, 31,313 segments):
- Fields: `SEASONAL` (Yes 2,313 / No 17,077 / **Unknown 11,912, 38%**), free-text
  `SEASDESC`, `RDHICLEAR` (275 Yes), `RDSURFACE`, `OPENTOPUBLIC`.
- It flags four of §4's untagged or free-text roads as seasonal (Glacier Point, Teton
  Park Road, Crater Lake, Old Fall River), and Kuwohi Road and Lassen too. Only Teton
  Park Road's flag comes with dates ("Seasonal Closure Nov1 to May1"); the rest say
  "Winter" or nothing.
- It does not cover Yellowstone: 1,979 of its 2,007 segments are Unknown.
- NPS closure *status* (the developer API's alerts) needs an API key and is free text.
  It was not read.

**FHWA America's Byways** (an ArcGIS layer published by a USDOT account,
`FHWA_ScenicByways_08042026`):
- 227 per-state polyline records, 57 All-American Roads and 170 National Scenic Byways.
- Fields: name, state, designation, intrinsic qualities.
- No licence is stated.
- An older copy on ArcGIS Online (`NTIR_TRANS_NationalScenicByways_NSBP_ln`, owned by
  a private account) no longer answers at its URL. Its notes say its geometry was taken
  from 2005 Census streets or traced from Google, so it should not be used anyway.

### 6.7 PAD-US, BLM, HPMS, NHD, pass feeds

- **PAD-US 4.1:** national geodatabase 1,523,434,496 bytes, public domain, released
  2025-03-31 (ScienceBase item JSON). It was not compared against OSM's protected areas
  here (§8).
- **BLM GTLF:**
  - "Roads managed for public motorized use", 110,437 segments, about 47,000 mi. Its
    route-use class is Unknown or blank on 53%; "4WD high clearance / specialized" is
    about 9,000 mi, "4WD low" 8,900 and "2WD low" 4,100. A seasonal restriction is
    marked on 970 mi.
  - The "limited public motorized use" layer, about 36,000 mi, is 77% high-clearance.
  - Class values come in three spellings each ("4WD Low", "4wd Low", "4WD LOW").
  - US public domain; updated 2026-08-14.
- **HPMS 2024:**
  - Per-state geodatabases of ARNOLD geometry with section data, `SPEED_LIMIT`
    included.
  - CC0 according to data.gov, which also lists it as "non-public"; its own
    contradiction, recorded as found. Size not determined.
  - The host, `www.fhwa.dot.gov`, now passes a control URL (200 real, 404 bogus);
    `highways.dot.gov` still returns 403.
- **NHDPlus HR:** national Release 1 geodatabase 28.1 GB (July 2022). Release 2 (February
  2025) appears in the bucket as metadata only. The plain-NHD national prefix
  (`Hydrography/NHD/National/HighResolution/`) is empty.
- **Pass status in three Western states:**
  - **Caltrans CWWP2** serves public JSON with no key: chain controls, and lane and
    full closures per district (553 records in District 10 on 2026-10-11, all
    construction and maintenance). Whether seasonal pass closures appear in it in
    winter could not be seen in October.
  - **WSDOT's mountain-pass API** answers 401 without an access code (free
    registration). Its `devapps` host fails TLS name checks.
  - **CDOT's COtrip** developer page redirects to the map, so the feed's terms and
    format were not determined.

### 6.8 State DOT road-class layers: the 50-state survey

`state_dot_survey.py` searched ArcGIS Online's catalogue twice per state, skipping city
and county servers. It probed each candidate's line layers for fields and
`returnCountOnly`. `state_dot_table.py` holds the hand choice: a statewide layer
published by the state (its DOT, GIS office or 911 board), not one county's. A miss is
"not found by catalogue search". A DOT that hosts only on its own server and never
registers it would be missed, so a miss is not evidence the layer is private.

| state | layer (features) | scope | fields for class / maintenance / surface / ownership / season |
|---|---|---|---|
| AL | 2016 Highway Functional Classification (150,799) | functional class only, 2016 | class `Functional` |
| AK | — | not found by catalogue search (a borough's layer, and the continental NTAD North American Roads) | — |
| AZ | ADOT HPMS PavementCondition2022 (143,793) | HPMS pavement layer, statewide | surface `TravelSurfaceType_REF`; ownership `Owner_REF` |
| AR | ROADS_ACF (458,050) | statewide all roads (state GIS office) | class `rd_class`; surface `rd_surftyp` |
| CA | CRS Functional Classification (779,834) | statewide public roads, class only | class `F_System` |
| CO | Highways: Functional Class (406) | state highways only | class `FUNCCLASS` |
| CT | State Route Network Historical (32,833) | state routes and local roads, historical | status `PRI_SEC_STATUS` |
| DE | ROAD INVENTORY (112,276) | statewide | class `FNCTNL_CLASS_CODE`, `SYSTEM_CLASS_CODE`; maintenance `MAINT_RSP_CODE`, `RDWAY_STATUS`, acceptance dates |
| DC | Roadway Functional Classification (13,833) | district-wide | class `FHWAFUNCTIONALCLASS`; surface `SURFACE_TYPE`; ownership `OWNERSHIP` |
| FL | — | not found by catalogue search | — |
| GA | — | not found by catalogue search (city layers only) | — |
| HI | — | not found by catalogue search | — |
| ID | Local Road Inventory (22,358) | local roads | status `RoadStatus`; surface `SurfaceType`; jurisdiction `LRI_Jurisdiction_Primary` |
| IL | ROADS2017 (563,163) | statewide, 2017 | maintenance `MAINT_TYPE`; surface `SURF_TYP` |
| IN | Road Centerlines of Indiana Current (569,734) | statewide | class `roadclass` |
| IA | Road Network (359,528) | statewide | class `FED_FUNCTIONAL_CLASS`; status `ROAD_STATUS`; surface `SURFACE_TYPE`; ownership `OWNER_CODE` |
| KS | RoadCenterline_NG911_GCS (392,663) | statewide NG911 | class `RDCLASS`; status `STATUS`; surface `SURFACE` |
| KY | Locals (2,883) | functional class, one layer per class | class `FUNCT`; status `STATUS` |
| LA | Louisiana Roadways (685,620) | statewide | class `FeatureClassCode`, `RouteClassCode`; ownership `Ownership` |
| ME | MEDOT.ALLPUBRDS (77,651) | all public roads, beside layer 915's private roads (what state_roads.py reads) | presence in the layer is the signal |
| MD | Roadway Functional Classification (98,740) | class only | class `FUNCTIONAL_CLASS` |
| MA | Road Inventory 2024 (595,790) | statewide (state_roads.py reads the MassGIS copy) | class `F_F_Class`; maintenance `City_Maint`; surface `Surface_Tp`; jurisdiction `Jurisdictn` |
| MI | MDOT RH 2026 (708,231) | statewide LRS | surface `MIRESurfaceType`; ownership `Ownership` |
| MN | FUNCTIONAL_CLASS (365,338) | statewide, class only | class `FUNCTIONAL_CLASS` |
| MS | — | not found by catalogue search | — |
| MO | — | not found by catalogue search | — |
| MT | — | a functional-class layer was found, but its server returned HTTP 503 | — |
| NE | StreetCenterline (299,925) | statewide | class `RoadClass` |
| NV | NDOT Unimproved Roads (104,460) | NDOT's roads mirrored by the state water office, in three layers | surface `SURFACE_TYPE` |
| NH | NH DOT Roads (112,827) | statewide (GRANIT) | class `funct_system`, `legis_class`; surface `surf_type`; ownership `hpms_ownership`; season `winter_maint` |
| NJ | Tran_road (489,277) | statewide (state GIS office) | class `ROADCLASS`; status `STATUSTYP`; surface `SURFACETYP`; jurisdiction `JURISDICTN` |
| NM | — | only per-class E911 extracts; NMDOT's centerline layer did not answer a count | — |
| NY | NYSDOT Roadway Inventory (475,937) | statewide | class `Functional_Class`; jurisdiction `Owning_Jurisdiction`; surface `Pavement_Type` |
| NC | State Maintained Roads (370,437) | state-maintained roads, most of NC's network | class `RouteClass`; maintenance `RouteMaintCode`; ownership `OwnerType` |
| ND | — | a state and federal roads layer that did not answer a count | — |
| OH | — | not found by catalogue search (county layers only) | — |
| OK | Local Roads (269,260) | local roads; state roads in a second layer | class `FUNCTIONALCLASS`; maintenance `MAINTENANCERESPONSIBILITY`; surface `SURFACETYPE` |
| OR | All Public Roads (758,494) | statewide public roads, ownership only | ownership `ROADOWNER` |
| PA | — | not found by catalogue search (county layers only) | — |
| RI | RIDOT Roads (2016) (71,384) | statewide, 2016 | class `F_SYSTEM`; surface `SURFACE`; jurisdiction `JURIS` |
| SC | — | only a regional council's statewide copy, with no class field | — |
| SD | Non-State Trunk Roads (150,365) | local roads | class `FUNC_CLASS`; surface `SURFACE_TYPE` |
| TN | Tennessee NG911 Road Centerlines (571,907) | statewide NG911 | status `STATUS` |
| TX | TxDOT Roadway Inventory (960,621) | statewide | class `F_SYSTEM`; maintenance `RDWAY_MAINT_AGCY`; surface `SURF_TREAT_CODE` |
| UT | Roads (414,082) | statewide (state GIS office) | class `DOT_FCLASS`; status `STATUS` |
| VT | ALL ROADS (78,946) | statewide (state_roads.py reads s1111_rds) | class `AOTCLASS`, `FUNCL`; surface `SURFACETYPE` |
| VA | VDOT Route Master LRS (196,896) | statewide routes | route type; status `RTE_STATUS_CD`; jurisdiction |
| WA | Local Public Road Labels (141,755) | statewide local public roads | class `FederalFunctionalClassDesc`; jurisdiction `Jurisdiction` |
| WV | Federal Functional Classification Routes (51,287) | class only | class `NAT_FUNCTIONAL_CLASS` |
| WI | Local Road Network snapshot (1,011,803) | local roads | surface `SURF_TYCD` |
| WY | — | not found by catalogue search (a TIGER copy only) | — |

**37 states and DC have a public layer; 13 were not found**: AK, FL, GA, HI, MS, MO,
MT (server 503), NM, ND, OH, PA, SC, WY.

Of the 38 layers:
- **26 cover the public road network statewide**, some only its local roads and some
  with a single useful field: AR, CA, DE, IA, IL, IN, KS, LA, MA, ME, MI, NC, NE, NH,
  NJ, NY, OK, OR, RI, SD, TN, TX, UT, VT, WA and WI.
- **12 are state highways, functional class or a partial network.**
- **One carries a seasonal field:** New Hampshire's GRANIT copy has `winter_maint`.
- No two share a schema.

Licences:
- **Open terms on 7:** CO and IL CC BY-SA; DC and IA CC BY 4.0; KY CC0; MA public
  domain; LA "no use limitations".
- **Restrictive on 2:** TxDOT says its data is its property and "produced for internal
  use"; Oklahoma requires an Open Records Request for official use.
- **Conditions on 2:** Minnesota's disclaimer must travel with the data; Rhode Island
  uses the RIGIS licence agreement.
- **The rest:** disclaimers, with no licence.

state_roads.py's bespoke integration does not scale to 50 schemas. **HPMS/ARNOLD is the
same information in one schema**, and its absence of private roads is itself a signal:
a road in OSM but not in ARNOLD is the private-road test Maine's layer already gives
state_roads.py.

## 7. Gaps, ranked

Ranked by what a driver meets first: a closed or impassable road over a slow one, and
anything over a dull one.

### Routing safety

| # | gap | evidence | closes it | cost |
|---|---|---|---|---|
| S1 | **Seasonal closures leave open roads that are closed:** 7 of 18 checked, and six more open early | §4; 819 of 821 km of MVUM-seasonal graph road in one forest has no OSM tag | closures.py: read ordinal and day-first dates and gate-node conditionals. **MVUM** dates for Forest Service roads, joined by geometry. **NPS public roads** for park roads, with dates from NPS pages where `SEASDESC` is prose. A per-road window table for the dozen high passes the generic Nov 1-Apr 30 gets wrong | code: days; MVUM join: a week; NPS dates: per park |
| S2 | **4WD and high-clearance roads in the graph unflagged** | A5x unflagged on 3,296 km (SD), 1,499 (MT), 927 (CO), 914 (KS); 370 km of TIGER S1500 in the graph per six Colorado counties | read `4wd_only`, `smoothness`, `tracktype` and `tiger:cfcc` A5x (OSM, free); **MVUM** maintenance level 2 and **BLM** route-use class on federal land; **TIGER** S1500 elsewhere | OSM tags: a day; federal layers: a week each |
| S3 | **The permit rule closes park roads all year** | Trail Ridge 66.8 km shut every day; 272 km (WA), 138 km (UT), 153 km (CO) | treat `permit` as open (with a notice) where the road is a park road or carries `*:conditional`, rather than closed; decision 3 in closed-roads.md is the owner's | a decision, then hours |
| S4 | **Default speeds for untagged roads run 20-99% below what each state's tagged roads post** | §3.1 | refit `SPEED_KMH` per state by graph.py's own harmonic-mean method; **HPMS** `SPEED_LIMIT` where OSM is untagged | a day per region; HPMS: a week |
| S5 | **Private roads routable** | 69 km of TIGER S1740 in the graph per six Colorado counties; Maine's 35% (state-road-class.md) | **TIGER** S1740; absence from **HPMS/ARNOLD**; state layers where open | a week |
| S6 | **Unpaved roads invisible to the avoid-unpaved preference** | no `surface` tag on 62% of Kansas' km and 84% of Mississippi's; 78% of Kansas' unclassified km is tagged unpaved, so untagged dirt is likely common | **MVUM** `surfacetype` on forest roads; the surface fields in the state layers that have them (§6.8: KS, IA, NJ, OK, SD and others) | a week per source |

### Scenery

| # | gap | evidence | closes it | cost |
|---|---|---|---|---|
| Sc1 | **Byways missed, and two highways wrongly made byways** | 168 of 310 network relations missed; US 34 and NY 30 | admit state byway networks by pattern; refuse numbered-highway networks unless the relation is short or names a byway; **FHWA byways** as a check | days |
| Sc2 | **Western scenery invisible** | review §6: tree cover 0 on most Western km, relief capped | **WorldCover** shrub, bare and snow classes, already fetched; **PAD-US** designation; relief derivatives | the scenery track: months of drives, not data |
| Sc3 | **Overstated rural minutes overprice scenic detours** | the slider trades minutes for scenery, and rural untagged minutes run long by the S4 margin | the S4 refit | with S4 |
| Sc4 | **Terrarium spikes inflate relief on flat coasts** | §6.1: 12% of coastal tiles; 25.5 km of deployed New England road | mask the residue with this detector before elevation.py's filters, and patch it from **3DEP** windows | a day |

## 8. What cannot be determined from the data available

- **Untagged speeds.** Whether untagged rural roads are driven like tagged ones. The
  harmonic means are of *posted* limits on the roads that carry a tag. Only drives
  measure the rest; `SPEED_FACTOR` is the existing instrument.
- **Bulk-only metrics.** OSM quality in the 35 unsampled states by km. Taginfo's proxy
  is the best available, and §3.3 says how far to trust each column. A km figure for
  any of them needs its extract (Texas 0.72 GB, California 1.33 GB).
- **Texas by proxy.** Geofabrik's Texas taginfo has no combination statistics.
- **Seasonal closures nationally.** No national list of closed-for-winter roads exists
  to count against. The 23 here are a judgment sample of famous roads, and MVUM covers
  Forest Service roads only. NPS's layer is 38% Unknown.
- **Winter feeds.** Whether Caltrans' feed carries seasonal pass closures in winter;
  CDOT's feed terms.
- **Sizes not determined:** HPMS 2024 (per-state, behind BTS), NPS public roads, BLM
  GTLF and FHWA byways as files. All were counted by feature instead.
- **The private-road share outside Colorado's six counties.** TIGER S1740 is counted
  nationally by segment (1.22M), not by km against OSM.
- **PAD-US against OSM's protected areas,** and how much it would add to `c_forest` or a
  designation component. Not measured.
- **State DOT layers missed by catalogue search.** The 13 states without one may still
  publish one on their own servers. Licences on the 38 found are what their item pages
  say, not legal readings.
- **Terrarium nationally beyond the sample.** The rates come from 1,975 random tiles,
  plus the Colorado and New England censuses (3,776 tiles). Alaska's estimate rests on 3
  hits. Finding every corrupt tile means decoding all 58,947, a 6.6 GB fetch. It is
  cheap, but it is the bulk download the brief excluded.

## 9. Corrections to earlier documents

- **The feasibility review, §5 defect 1, "Trail Ridge Road … 0 km are marked":** false.
  OSM tags 66.4 km of it `access:conditional = no @ Oct 14th - May 31st`, and
  closures.py's grammar rejects the ordinals. In the review's own build the road was
  not open in January. closures.py's all-year rule closed it every day of the year,
  for `vehicle=permit`. Its "a January plan would cross the Continental Divide" does not
  hold for its own build; a July plan could not cross it either.
- **The review, §1, "~23.4M nodes (19-28M)":** about 19.2M (±20%) on 17 counted states.
  Its fit overestimated every rural state counted since, South Dakota by 178%. Its
  compact US pack is therefore about 4.4 GB, not 5.5.
- **The review, §5, "the contiguous US at zoom 11 is about 60,400 tiles":** that is the
  bounding box (60,060 by this count). The outlines need 35,778, or 58,947 with Alaska
  and Hawaii.
- **The review, §5 defect 5, Colorado's 2,300-4,536 m of fake relief:** true in metres,
  but the relief score is capped at `RELIEF_FULL` = 100 m. Only one of the three tiles
  changes `c_relief` at all, because the surrounding mountains are already at the cap.
  The harm concentrates on flat and coastal ground (§6.1).
- **`docs/new-england-terrain-findings.md`, "relief max 1,453 m (White Mountains,
  plausible)":** false. The deployed raster's four largest relief values are in-band
  spikes on the Maine coast: 1,453 m near Boothbay, 870 m near Portland, 726 m and
  620 m. The real maximum is about 680 m, at Katahdin. That document's header now says
  so.

The review is untracked in another worktree, so its header is not edited here; the
merge that commits it should carry these.

## 10. Method and reproduction

Everything ran on the dev Mac on 2026-10-11 with the project venv (pyosmium 4.3.1)
under `python -I`. Downloads went to a session scratchpad, one at a time, each in its
own directory.

| script | what it does | output in `results/` |
|---|---|---|
| `geofabrik_sizes.py` | HEAD of every state extract; US file history | `osm_extract_sizes.csv`, `osm_us_history.csv` |
| `sample_states.sh` | download, measure, delete, one state at a time | — |
| `osm_metrics.py` | tier 2: km-weighted tag quality over graph.py's graph | `metrics/<state>.json`, summarised in `osm_quality_measured.csv` |
| `taginfo_proxy.py` | tier 1: taginfo proxies for 51 states, cached | `taginfo_proxy.csv` |
| `summarize.py` | measured, proxy and calibrated tables | `osm_quality_measured.csv`, `proxy_vs_measured.csv`, `proxy_accuracy.csv`, `osm_quality_all_states.csv` |
| `seasonal_roads.json`, `seasonal_check.py`, `seasonal_truth.json`, `seasonal_table.py` | the 23-road ground truth | `seasonal/<state>.json` (every matched way and gate, with its tags), `seasonal_ground_truth.csv` |
| `overpass_queries.py` | the small Overpass queries: five answered, and the network regex timed out twice | — |
| `byway_census.py`, `byway_state_table.py` | byway networks and `scenic=yes` relations | `byway_networks.csv`, `byway_scenic_yes.csv`, `byway_census_by_state.csv`, `byway_sampled_states.csv` |
| `terrarium_survey.py` | tile counts, HEAD sample, decode and detector | `terrarium_tiles_by_state.csv`, `terrarium_head_sample.csv`, `terrarium_decode_*.csv` |
| `ne_relief_spikes.py` | the deployed New England raster's residue, priced in chunks | `ne_relief_spikes.json` |
| `worldcover_cells.py` | WorldCover cells by HEAD | `worldcover_cells.csv` |
| `dem3dep_survey.py`, `dem3dep_vs_terrarium.py` | 3DEP sizes; Terrarium against 3DEP 1″ | `dem3dep_sizes.json`, `dem3dep_vs_terrarium_colorado.csv` |
| `mvum_survey.py`, `mvum_osm_match.py`, `osm_match.py` | MVUM nationally; one forest against OSM | `mvum_national.json`, `mvum_osm_gmug.json` |
| `tiger_sizes.py`, `tiger_osm_match.py` | TIGER sizes; six counties against OSM | `tiger_2026_sizes.csv`, `tiger_osm_colorado.json` |
| `state_dot_survey.py`, `state_dot_table.py` | the 50-state DOT survey | `state_dot_layers.csv` |
| `budget.py` | the per-state disk and memory budget | `budget_by_state.csv` |

Figures derived from OpenStreetMap are © OpenStreetMap contributors, under the ODbL
(`results/README.md`).
