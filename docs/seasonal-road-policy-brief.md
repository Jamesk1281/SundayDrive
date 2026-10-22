# Build the seasonal-road policy: margins on guessed windows, and a reroute that remembers

**Status:** decided, not built. Written 2026-10-22 by the master session
against `usa` at `2b31f28`. The owner approved building what
`docs/seasonal-road-risk-verdict.md` recommends ("Recommended policy"), plus
three of its data fixes. **Nothing has been touched.** The study simulated
everything in memory. Your answer goes in **`docs/seasonal-road-policy.md`**,
plus the code and tests. Don't append to this brief: it is deleted in the
merge that brings the work back.

## What was measured (the verdict, in short)

- **Banning seasonal roads costs far more than it saves.** On random US trips,
  a ban saves 37.6 expected stranded minutes per 1,000 trips and costs 108.5
  certain ones. Nine of 24 named roads can then no longer be crossed.
- **The risk sits in the guessed windows.** OSM's undated default,
  `WINTER = (11, 1, 4, 30)` (`pipeline/closures.py:110`), says "open" while high
  passes are still shut in 83% of springs, a median 24 days early. Hand-table
  windows are almost never dangerously open: 1.3 days a season.
- **The reroute has no memory.** 93% of reroutes from a closed gate send the
  driver back to it. 39% still do after 80 km of driving the right way, and
  `declined_uturn` doesn't rescue them (89%).
- **Recommended policy + P5 cuts expected stranding by 53–83%** across the
  four samples and keeps 91–100% of the seasonal scenery.

## What to build (decided; don't re-tune)

### 1. Margins, by window source, where windows are written

The margins go **where rows are written**, as a per-source margin, never in
the router. The router stays as it is (`pipeline/router.py:2775-2779`), and
the closure version keeps keying every cache.

| source (verdict's name) | where it's written | margin |
|---|---|---|
| OSM undated default (`osm_default`: `winter`/`snow` conditionals, `winter_service=no`, `seasonal=*`) | `pipeline/closures.py`, `WINTER` (`:110`; read at `:219`, `:340`, `:343`) | **spring end +45 days**, so Apr 30 → Jun 14. Autumn unchanged. |
| `UNKNOWN_SEASON = (10, 1, 6, 30)` | `pipeline/winter_closures.py:76` | **±7 days**: closed 7 days earlier and 7 days later |
| MVUM dates and NPS-description dates (`agency_dated`) | `pipeline/winter_closures.py` (`mvum_windows`, the NPS rows) | **±7 days** |
| hand table (`pipeline/winter_windows.json`) and OSM-dated conditionals | — | **none** |

The +45 rests on the verdict's high-pass curve. The milder pooled curve would
give +14, but the verdict picked +45 for the smaller worst case
("Sensitivities"). **Use +45.**

### 2. P5: the reroute rules out the seasonal stretch the driver turned away from

The server side, following the verdict's "What a build would touch":
- **Each route response lists its seasonal stretches.** These are maximal runs
  of consecutive route edges that have any row in `seasonal_closures`. For
  each one, give its edge row ids, `from_m` and `to_m` along the route, and
  the pack fingerprint the ids belong to.
- **A new `/api/route` parameter carries the edge row ids to close for this
  request,** together with the fingerprint they came from, e.g.
  `avoid_edges=…&avoid_pack=…`.
  - Parse it beside `_parse_declined_uturn` (`server/app.py:448-457`).
  - Close those edges through the `blocked` path that keep-ahead already uses
    (`router.py:2720-2791`, `:3696-3700`).
  - Ignore the parameter, never fail on it, when the fingerprint doesn't match
    the loaded pack: a redeploy mid-drive must not 400 a driver.
  - Cap the number of ids, and say what the cap is.
- **Loops:** a loop's reroute must honour it too, whichever endpoint loops use
  mid-drive. Any cached-result key that a reroute can hit must include the
  avoid set (`server/app.py:278-287`, the loop cache).

The app side:
- **The rule:** a stretch counts as turned away from when a wrong-way episode
  opens (`wrongWayEpisode`, `ios/Sources/NavigationModel.swift:797`) while the
  car is on a seasonal stretch, or while one starts **within 25 km ahead**
  along the active route.
  - The 25 km is the 90th percentile of the gate approaches in the study's
    `tools/seasonal_risk/q3_cases.csv` (`approach_km`, p90 25.2).
  - A false positive only costs one stretch's scenery for the rest of the
    trip, so the rule leans generous.
- **Send that stretch's ids with every later reroute until arrival,**
  including reroutes asked with `declined_uturn`
  (`RouteService.swift:212`, `NavigationModel.swift:2020`).
- **No button, no notice.** P4 isn't being built, and neither is a "Road
  closed" button.

### 3. Three data fixes (the verdict's "Defects found", items 1–3)

1. **North Cascades (WA 20) is shut Oct 1 – Jun 30** by one 30 m "Highway 20"
   edge carrying an NPS `USFS SEASONAL=Yes` row, so `UNKNOWN_SEASON` applies
   there. The `north_cascades` row in `winter_windows.json` doesn't cover it.
   **Fix:** extend that row's waypoints so its path covers the edge, and the
   table's window replaces the unknown row on it, as for other table roads
   (decision 4 in `docs/winter-closures-national.md`). Then add a report
   line, which closes nothing: every `UNKNOWN_SEASON` row on an edge adjacent
   to a table road's path. List the hits in the answer doc and don't fix them
   blind.
2. **Crater Lake.** One park window (Oct 15 – Jul 31) shuts the West Rim to
   August 1, though it opened a median 53 days earlier. **Fix:** split it into
   West Rim and East Rim table rows. Build each from the published dates in
   `tools/seasonal_risk/q2_published_dates.csv` under the table's existing
   rule (the longest the operator published in its last ten seasons), and
   cite the sources in `basis`.
3. **Going-to-the-Sun.** OSM's `Oct-Jun` replaces measurement with a guess.
   **Fix:** add a table row from NPS's Logan Pass record. The URL and years
   are in `q2_published_dates.csv`; the page is
   `nps.gov/glac/learn/news/logan-pass-opening-and-closing-dates.htm`.
   **Exclude the closings the NPS footnotes as fire or construction.** They
   aren't seasonal. 2017's Sep 3 is fire, and keeping it would shut every
   September. Apply the ten-season rule to the rest, and record which years
   were excluded and why.

**Not in scope:** the verdict's defect 4 (narrowing Lassen's and the hand
table's spring ends). The verdict calls it a judgement for the owner, and it
was not approved.

## The rebuild

Closure changes need the closure tables and the pack rebuilt, not the
regions. Use `tools/national_audit/sidecars_next.py` and then `pack_next.py`,
as `docs/national-data-decisions.md` ("The rebuilt data") did, into
`data/processed-us-next` and `data/pack-us-next`, with
`data/pack-us-next.done` when the pair is complete. The swap is the master
session's. Base this on the data now in `data/processed-us` and
`data/pack-us`. As of 2026-10-22 it carries the six data decisions and the
scenery additions (V + S2 + L). `data/raw/federal` has the refetched MVUM.

## Traps

1. **One national-scale job on this Mac at a time.** On 2026-10-21, three
   concurrent national jobs hung the 24 GB Mac into a kernel panic. Run the
   sidecars at `--jobs 2`, alone, with nothing else heavy. Check
   `memory_pressure` first, and message the master session before starting
   if any other session's python holds national data.
2. **Margins at the source, not in the router.** Don't add a margin to
   `in_window` or `_weights`. The closure version keys the loop cache and the
   router's caches. A margin inside the router would change behaviour without
   changing the version, so cached loops would go stale. Apply the margins
   per source, and only to the ends the table above names:
   - only spring for `WINTER`;
   - nothing for the hand table, which is already biased toward closed by its
     ten-season rule (verdict trap 5);
   - nothing for OSM-dated rows.

   `WINTER` may be read by more than one rule, such as gate windows. Change
   what the `osm_default` source writes, not a constant something else
   shares, unless every reader is that source.
3. **Judge a window by the edges actually on the route,** not by "most of the
   road's km". The study missed the North Cascades edge this way first.
4. **An unknown fingerprint must be ignored, not rejected.** The app keeps a
   route's stretch ids for hours, and the box may be redeployed in between.
5. **A stretch that starts under the car can't be avoided** (verdict
   "Limits": 2 of 99). `Router.snap` routes a moving car forward off the road
   it's on. Don't fight that. The test is that the reroute leaves the stretch
   at its next exit and never re-enters it.
6. **Don't write `data/processed-us`, `data/pack-us` or `data/processed-ne`.**
   For New England, run `closures.py` into a scratch copy, as the
   six-decisions unit did (`docs/national-data-decisions.md`, "New England").
7. **The default `data/processed` is an August MA-only build.** Always set
   `SUNDAYDRIVE_DATA`.

## Done looks like

1. **Code and tests:**
   - the margins in `pipeline/closures.py` and `pipeline/winter_closures.py`,
     with tests that mutate each margin and watch a test fail;
   - the three table rows in `pipeline/winter_windows.json`, plus the
     adjacency report;
   - P5 in `server/app.py` and `pipeline/router.py`, with tests: ids honoured,
     a stale fingerprint ignored, the cap, the loop cache key;
   - P5 in `ios/Sources/` (`NavigationModel.swift`, `RouteService.swift`,
     `Models.swift`), with a simulated-drive test of a car reversing at a gate
     on a seasonal stretch, where no later reroute re-enters the stretch.
2. **The real implementation measured against the study,** using
   `tools/seasonal_risk/q3_turnaround.py`, adapted to call the real parameter,
   on the `named` and `top` cases. Sends-back should fall from 93% to about the
   study's P5 figure, with the 2-in-99 snap cases explained. Then re-run
   `q4_policies.py` on the rebuilt data and report stranding against the
   verdict's table.
3. **`data/processed-us-next` + `data/pack-us-next` + `.done`:**
   - the continuity check at 11,414 of 11,414;
   - `tests/test_national_routes.py` against the -next pack;
   - the suite on `processed-ne` green;
   - the iOS suite, with failures compared against `usa`'s own (`usa` already
     has one replay red).
4. **`docs/seasonal-road-policy.md`:** what changed per source, the km and
   edges whose windows moved (nationally and in New England), the three fixes
   with their sources and excluded years, the adjacency report's hits, and
   the measured P5 numbers.
5. This brief committed with the work, with nothing appended to it.
6. **The escape hatch:** if P5's 25 km rule fires on an ordinary
   wrong-way episode in the existing simulated drives or real-trace replays
   (`ios/Tests/DriveReplay*`, `SimulatedDrive*`) in a way that drops a stretch
   the driver never turned from, report the cases. Don't move the 25 km.
