# Winter closures for park and forest roads, national

**Status:** built 2026-10-18 on `claude/winter-closures`, off `usa` at `6fdf137`.
Not merged, deployed or pushed. The router, the build files and `ios/` are
untouched.

## Earliest honest date

**Day one (2026-10-18), committed before any code:** Wednesday 2026-10-21 for
the branch to be ready to merge into `usa`.

**End of day one: ready to merge now.** The code, the tests, the sourced
window table, the §4 re-run and the New England diff are all below. The date
it depends on is unit A's: the national `seasonal_closures` is only as good as
the run of `closures.py` that writes it, and that run needs
`data/raw/federal/` (step 1 under "For unit A").

## Result

`docs/us-map-data-findings.md` §4 checked 23 roads against their operators.
**Every road now closes on its operator's closed dates and opens on its open
dates**, apart from the two the brief leaves alone: Trail Ridge Road (the
permit rule) and Hurricane Ridge (part-time). Measured on a graph of the §4
roads built from 2026-10-17 Geofabrik extracts ("How it was checked"), in km
of each road closed. "OSM" is closures.py on `usa`; "now" is this branch.

| road | km in graph | date (role) | OSM | now |
|---|---:|---|---:|---:|
| Teton Park Rd | 33.8 | Nov 5, Jan 15, Apr 25 (closed) | 0.0 | **23.0** |
| | | Aug 15 (open) | 0.0 | 0.0 |
| Yellowstone Grand Loop | 225.9 | Nov 5, Jan 15, Apr 10 (closed) | 0.0 | **197.2** |
| | | Aug 15 (open) | 0.0 | 0.0 |
| Glacier Point Rd | 25.1 | Nov 20, Jan 15, May 20 (closed) | 0.0 | **17.3** |
| Kuwohi Rd | 11.1 | Dec 15, Jan 15, Mar 15 (closed) | 0.0 | **11.1** |
| | | **Nov 5** and Aug 15 (open) | 0.0 | **0.0** |
| Crater Lake Rim Drive | 51.3 | Nov 5, Jan 15, Jun 1 (closed) | 0.0 | **46.7** |
| Old Fall River Rd | 14.3 | Nov 5, Jan 15, Jun 20 (closed) | 0.0 | **14.3** |
| Beartooth Hwy (MT and WY boxes) | 107.5 | Jan 15 (closed) | 13.8 | **85.6** |
| | | May 15, Oct 20 (closed) | 0.0 | **84.6** |
| Lassen Park Hwy | 56.4 | May 15 (closed) | 0.0 | **41.4** |
| Sonora Pass | 55.6 | Jan 15 (closed) | 37.6 | **55.6** |
| | | May 10 (closed) | 0.0 | **55.6** |
| Ebbetts Pass | 32.4 | May 1 (closed) | 0.0 | **32.4** |
| Mount Blue Sky Rd | 23.4 | May 20, Sep 15 (closed) | 0.0 | **23.4** |
| Independence Pass | 61.2 | Nov 20, Jan 15, May 15 (closed) | 36.8 | **39.3** |
| North Cascades Hwy | 79.7 | Dec 15, Jan 15, Apr 15 (closed) | 55.1 | **59.0** |
| Chinook Pass | 30.5 | Nov 20, Jan 15, May 15 (closed) | 18.6 | **27.5** |
| Going-to-the-Sun Rd | 80.0 | Nov 5, Jun 15 (closed) | 63.5 | 63.5 |
| Tioga Rd | 88.5 | Nov 20, May 20 (closed) | 88.4 | 88.5 |
| Mirror Lake Hwy | 69.3 | Dec 15, May 15 (closed) | 54.6 | 54.6 |
| Needles Hwy | 48.3 | Jan 15 (closed) | 31.5 | 31.5 |
| Trail Ridge Rd | 70.2 | every date | 66.6 (and 66.8 all year by the permit rule) | unchanged |
| Hurricane Ridge Rd | 21.5 | Jan 15 | 0.0 | 0.0 (part-time, left open on purpose) |
| Mt Washington Auto Rd | 12.4 | **May 12** (closed) | 0.0 | **12.2** |
| | | Nov 5, Jan 15 (closed) | 12.2 | 12.4 |
| Kancamagus Hwy (control) | 59.4 | Nov 5, Jan 15, May 15, Aug 15 | 0.0 | **0.0** |

Every road above is open on its "open" date (Aug 15, or Jul 15 for Mount Blue
Sky); the CSVs in `tools/winter_closures/results/` have every row. Where "now"
is less than the km in the graph, the rest is road beyond the closure: Teton
Park Road's 23.0 km is Taggart Lake to Signal Mountain, and Yellowstone keeps
Mammoth to Tower open (28.7 km). The road-name match picks up approaches in
each road's box.

**The brief's forest:** in Grand Mesa, Uncompahgre and Gunnison NFs, MVUM now
closes **813.2 km** of graph road for part of the year (§6.4 counted 821 km of
seasonal road in that forest's graph). OSM's own tags close 4.0 km of it
(§6.4: 1.6 km, on the review's older Colorado build).

## What was built

- **`pipeline/federal_layers.py`, the new input stage.** It fetches MVUM roads
  (149,950 features) and NPS Public Roads (30,374) for the contiguous 48 into
  `data/raw/federal/`. It writes nothing if it receives fewer features than
  the server reports. It was run on 2026-10-18, and both counts matched.
- **`pipeline/winter_closures.py`** turns each source into `seasonal_closures`
  rows:
  - **MVUM:** a road is closed to a car outside its passenger-vehicle dates.
  - **NPS:** a segment marked seasonal is closed in the window its
    description gives, or else in its park's window.
  - **`pipeline/winter_windows.json`:** a window for each high pass, park road
    and park, each with its operator source, its access date and its basis.
- **`pipeline/closures.py`** calls it from `main` (`join_federal`). It reads
  the layers from the fourth argument, then `$SUNDAYDRIVE_FEDERAL`, then
  `federal/` beside the PBF, then `data/raw/federal`. If a file is missing it
  prints a `WARNING`; it never fails silently.
- **The table format is unchanged.** Agency rows are `rule` "edge",
  `node_id` -1 and `way_id` -1, and `tag` starts with `mvum `, `nps ` or
  `table `. `Router`'s `SeasonalClosures` loads both new tables (New England
  and the West).

### The join (trap 1)

**By geometry, never by name** (`match_lines`):
- Each graph edge is sampled every 25 m. Each sample takes the nearest agency
  line within 15 m, as in `tools/us_map_data/mvum_osm_match.py`.
- A sample counts only where the two run within 30° of each other, so a road
  crossing a closed one, or ending at it, picks up nothing.
- An edge closes when seasonal lines cover at least half its samples. It then
  takes every window of those lines.

In GMUG, changing that half moves the result by under 5%: a quarter would
close 851.4 km and three quarters 759.5 km, against 813.2 km.

Kuwohi Road is still "Kuwohi Access Road" in OSM, and NPS's layer carries its
own name. Neither name is read. A table road is the graph's shortest path
through waypoints taken from OSM's own seasonal tags and gates. Each one was
checked to run 100% on its road, and its length was checked against the
operator's. For example, North Cascades is 59.0 km in the graph against
WSDOT's MP 134–171, which is 59.5 km.

### Uncertain resolves toward closed (trap 2)

- **MVUM with no readable dates:** a road marked `seasonal` gets
  UNKNOWN_SEASON, Oct 1 – Jun 30. That is 1,442 mi nationally.
- **NPS seasonal with no dates, in a park the table doesn't know:** also
  UNKNOWN_SEASON.
- **Prose dates are read at their longer end.** Columbus Day becomes Oct 8,
  "mid-October" Oct 10, and "the Wed. before Memorial Day weekend" May 26.
  Every one of the 61 descriptions seen in the 48 states is mapped by hand,
  and a description not in the table resolves toward closed.
- **Table windows** are the longest the operator published in its last ten
  seasons (Lassen, North Cascades, Chinook, Independence Pass). Where there is
  no record, the window is the longer ends of the operator's stated range
  ("late May or early June" becomes Jun 10).

**Unknown seasons.** Oct 1 – Jun 30 contains every dated NPS winter
description in the 48 states. It also contains 95.7% of the closed days of
MVUM's dated seasonal roads, weighted by miles; 86.6% of those miles fall
wholly inside it.

**The generic winter is not widened.** Nov 1 – Apr 30 still applies to every
OSM tag, and only a sourced road, park or MVUM date adds days to it.
(Superseded by docs/seasonal-road-policy.md: an undated tag now closes to
Jun 14, unknown seasons and agency dates 7 days longer at each end, and the
undated winter gives way to a dated winter on its own edge.) The
Kancamagus has no row before or after.

## The window table

Accessed 2026-10-18. The full basis for each is in `winter_windows.json`.

| road or park | window | source |
|---|---|---|
| Beartooth Hwy (3 rows, split at 45°N) | Oct 12 – May 27 | nps.gov/yell parkroads; MDT seasonally closed roads; WYDOT |
| Dunraven Pass | Oct 12 – May 21 | nps.gov/yell parkroads |
| Sonora Pass | Nov 1 – Jun 12 | Caltrans D9/D10 releases (via press, see below) |
| Ebbetts Pass | Nov 1 – Jun 29 | Caltrans D10; Record-Courier; AP (Jun 30, 2017) |
| Mount Blue Sky Rd | Sep 2 – May 27 | CDOT byway page |
| Independence Pass | Oct 25 – May 27 | CDOT, 2015–2025 closing dates |
| North Cascades Hwy | Nov 3 – May 15 | WSDOT opening and closing table |
| Chinook Pass | Oct 24 – Jun 10 | WSDOT opening and closing table |
| Kuwohi Rd | Nov 30 – Mar 31 | nps.gov/grsm seasonal roads |
| Mt Washington Auto Rd | Oct 19 – May 22 | mt-washington.com 2026 calendar |
| Yellowstone (Yes and Unknown) | Oct 31 – May 21, except North to Northeast Entrance | nps.gov/yell parkroads |
| Grand Teton | Nov 1 – May 20 | nps.gov/grte roads |
| Yosemite | Nov 1 – Jun 10 | nps.gov/yose winter roads |
| Great Smoky Mountains | Nov 1 – May 14 | nps.gov/grsm seasonal roads |
| Lassen Volcanic | Oct 21 – Jul 25 | nps.gov/lavo, 2016–2026 table |
| Crater Lake | Oct 15 – Jul 31 | nps.gov/crla conditions |
| Rocky Mountain | Oct 1 – Jul 10 | nps.gov/romo road status |
| Acadia | Nov 16 – May 14 | nps.gov/acad hours |
| Katahdin Woods and Waters | Oct 20 – May 31 | nps.gov/kaww hours |
| Golden Gate | closes nothing | see decision 6 |

**Caltrans was unreachable.** `dot.ca.gov` reset every connection from this
Mac on 2026-10-18, in curl, WebFetch and the browser pane. A bogus path on the
same host failed the same way. The Sonora and Ebbetts dates are Caltrans
releases as quoted in search results and the local press. The URLs are in the
table, and they should be re-read from another network.

## New England

New England changes only where a source says so. Measured against
`data/processed-ne`'s graph with the 2026-08-25 extract; the run wrote into
scratch.
- `closed_to_cars` and `osm_unpaved` are byte-identical to `usa`'s.
- All 248 of `usa`'s seasonal rows are kept.
- 363 rows are added. **325 edges (349.6 km) newly close for part of the
  year**, and 32 already-closed edges get a second window.

| source | edges | km | what |
|---|---:|---:|---|
| MVUM, White Mountain NF | 107 | 126.8 | Kilkenny Loop, Tripoli, Wild River, Gale River, Cherry Mountain, Zealand, Sawyer River, Haystack and other gated forest roads |
| MVUM, Green Mountain NF | 87 | 102.9 | Airport Road (FS 71), Steam Mill, Brooks, Natural Turnpike, Mad Tom Notch and others; mostly Dec 16 – Apr 30 |
| NPS, Acadia | 107 | 64.8 | Park Loop Road and Cadillac Summit Road Dec 1 – Apr 15; the west-side roads to May 15 |
| NPS and table, Katahdin Woods and Waters | 41 | 79.8 | Katahdin Loop, American Thread, Swift Brook and Seboeis Roads, Oct 20 – May 31 |
| Table, Mt Washington Auto Road | 15 | 12.2 | Oct 19 – May 22 |

On the router's calendar:
- New England goes from 9 windows to 29.
- The closed set changes on 30 days a year, instead of 11.
- On Nov 5, 274 edges are closed, against 222.

## The decisions made here (each can be overruled)

1. **MVUM's passenger dates decide.** 4,101 mi marked `seasonal` with
   passenger dates `01/01-12/31` stay open: their season belongs to another
   vehicle class.
2. **No passenger designation: high-clearance dates, else open.** 1,221 mi
   with no passenger designation are read by their high-clearance dates.
   Another 4,849 mi have neither designation, and are left as they were. Is a
   car legal there? That is a closed-to-cars question (gaps S2/S5), not a
   seasonal one.
3. **The ten-season rule closes some roads in good years.** Lassen is closed
   until Jul 25, because it opened Jul 26 in 2017. In 2026 it opened May 22.
   Sonora runs to Jun 12 and Ebbetts to Jun 29. A live feed would end this
   over-closure; that is the next step, not this one.
4. **A table road replaces its park's window on its own edges.** Kuwohi's own
   season beats the Smokies' longest. Agency and dated rows always stay
   alongside it.
5. **Yellowstone's Unknown counts as seasonal,** since 1,979 of its 2,007
   segments say Unknown. The North-to-Northeast road is kept open by its
   waypoints, through Gardiner on the Temporary North Entrance Road, which is
   the only one in the graph.
6. **Golden Gate's flag closes nothing.** It marks 57 km seasonal with no
   dates, among them Lincoln Blvd and Washington Blvd in the Presidio. No
   seasonal closure of these roads is published, and the unknown season is a
   winter rule. Every other park that falls to UNKNOWN_SEASON does close for
   winter: Mount Rainier, Delaware Water Gap, Valles Caldera, Craters of the
   Moon, North Cascades and Lake Chelan.
7. **Beartooth: all of US 212 from WY 296 to Cooke City is closed.** Pilot
   Creek's position is not published, so this is the longer reading. The road
   is split at the state line so that a per-state run places each part.
8. **Mount Blue Sky: Echo Lake to Summit Lake takes the summit's window.** The
   Auto Road's weekend-only weeks are closed.

## For the other units

**Unit A (the national build):**
1. The layers are already in the main checkout's `data/raw/federal/`,
   fetched 2026-10-18 (308 MB). `python pipeline/federal_layers.py` refreshes
   them. Then run `closures.py` as before. It finds them beside a PBF in
   `data/raw/`; for a merged PBF kept elsewhere, pass the directory as the
   fourth argument or set `SUNDAYDRIVE_FEDERAL`.
2. Check the run's log for these lines:
   - `MVUM closes ...` and `NPS closes ...` in the output;
   - `table roads: 12 of 12` on a national run, or the roads it couldn't place
     on a per-state run;
   - no `WARNING ... is missing`.
3. The join's cost: 143 s on New England's 1.0M edges, and 280 s on the West
   test graph. Both were measured with the Mac at a load average of about
   300, so they are upper bounds. Peak RSS was 2.2 GB for the whole
   `closures.py` run. The cost scales with the edges near agency lines, not
   with the whole graph: candidates are found by one STRtree query in degrees.
4. Each table road lies in one state, apart from edges at a border, so a
   per-state run places it. Kuwohi Road is in North Carolina's extract.

**Unit B (the router):**
- Nationally, MVUM alone has **710 distinct windows**. They change the closed
  set on **223 days a year**: every cache keyed on `closure_version` will
  rebuild about every 1.6 days. That is correct, but it is a cost to measure.
  On the West test graph it was 106 windows and 72 days. The other fix would
  be to round MVUM windows outward to the 1st and 16th of a month (at most 24
  change days). That would over-close forest roads by up to 15 days at each
  end. Not done here.
- Agency rows have `way_id` -1, which `SeasonalClosures.n_ways` counts as one
  way on the startup line.
- `REGION_TZ` still dates every closure in New York time.

## What is still open

- **No live status.** Openings vary by weeks a year. Caltrans CWWP2, WSDOT's
  pass API (free registration) and NPS alerts (API key) are the sources
  (`docs/us-map-data-findings.md` §6.7).
- **Parks the table does not cover** fall to UNKNOWN_SEASON where NPS marks a
  road seasonal. Mount Rainier's Sunrise Road (open about July to September)
  is closed Oct 1 – Jun 30 by it, which is too short at both ends.
- **The 4,849 mi of MVUM road with no passenger or high-clearance
  designation** (decision 2).
- Unchanged and not touched: **the permit rule** (Trail Ridge is closed all
  year), **Hurricane Ridge's part-time winter**, and **the position-aware
  seasonal snap**.
- **The Beartooth's Pilot Creek** (decision 7).
- **MVUM's licence, and the app's credit line.** The survey recorded CC BY
  4.0, but the service states none (`docs/data-sources.md`). If it is
  CC BY 4.0, `ios/Sources/AboutView.swift` needs a Forest Service credit.
  That is unit C's file and the master session's call.
- **Caltrans' pages, re-read from another network** ("The window table").

## How it was checked

- **A test graph of the §4 roads.** `tools/winter_closures/test_graph.py`
  clips each road's box, widened by 0.2°, plus Yellowstone, Grand Teton, RMNP,
  Lassen, Crater Lake, GMUG and the Smokies' North Carolina side. The clips
  come from ten Geofabrik extracts of 2026-10-17, each md5-checked. It splits
  the ways with `graph.py`'s own handler. There is no scoring and no
  component cut; `closures.py` reads neither.
- **The §4 table re-run.** `tools/winter_closures/acceptance.py` selects each
  §4 road as `seasonal_check.py` does, and reports the km closed on the dates
  in `acceptance.json`. Results are in `tools/winter_closures/results/`.
- **New England.** `closures.py` from `usa` and from this branch, on the same
  PBF and graph, each writing into scratch.

**Tests:** 42 new ones in `tests/test_closures.py`.
- MVUM dates, NPS descriptions and the table's sourcing;
- the geometry join on synthetic roads (a crossing road, a road 30 m away, a
  renamed road, two seasons on one edge);
- the waypoint paths;
- four New England checks against the real graph and layers. These skip
  without `data/raw/federal`: the Kancamagus stays open, Tripoli Road and
  Park Loop Road close, and the Auto Road is closed on May 15.


## Suite

Run with `SUNDAYDRIVE_DATA=.../data/processed-ne`, on 2026-10-18:
- **979 passed, 12 skipped, 0 failed** across the whole suite (`usa`: 938 and
  12). It ran before the 42nd new test was added.
- `tests/test_closures.py` then ran again with it: 186 passed, 5 skipped.

## Reproduction

```bash
.venv/bin/python pipeline/federal_layers.py
.venv/bin/python -I tools/winter_closures/test_graph.py $PWD/pipeline <pbf_dir> <graph_dir>
.venv/bin/python pipeline/closures.py <graph_dir>/clips.osm.pbf <graph_dir> <out_dir>
.venv/bin/python -I tools/winter_closures/acceptance.py $PWD/pipeline <graph_dir> <out_dir> <out.csv>
```
