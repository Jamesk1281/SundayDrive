# The seasonal-road policy, built

**Status:** built 2026-10-22/23 on `claude/seasonal-road-policy`, off `usa` at
`2b31f28`. Not merged, pushed or deployed. The rebuilt tables and pack are
`data/processed-us-next` and `data/pack-us-next` with `data/pack-us-next.done`;
the swap is the master session's. Source comments and tests cite this file.

This builds what `docs/seasonal-road-risk-verdict.md` recommends ("Recommended
policy"):
1. per-source margins on the windows;
2. P5, a reroute that remembers the seasonal road the driver turned away from;
3. three window fixes.

There is one addition the master session decided during the build, after the
first rebuild showed what the margins did: **the undated default gives way
to a dated winter on its own edge.**

## The result

- **Margins.** Nationally, 10,868 edges' windows moved. 10,720 gained closed
  days and 582 lost some; the two sets overlap where one end moved each way.
  Against today's table the built windows keep **92–101% of the seasonal
  scenery** in every sample, on the same trips (us 92.6%, near 92.4%, ne
  100%, named 101.1%). That clears the verdict's 90% bar.
- **New England.** On `processed-ne`, 458 edges (404 km) moved: 456 gained
  closed days and 16 lost some. VT 108, Lincoln Gap and the Auto Road keep
  their own dates. Jefferson Notch, Kelley Stand and Evans Notch, which have
  only the default, open Jun 15.
- **P5, measured** on the rebuilt pair with the real parameter
  (`tools/seasonal_risk/q3_turnaround.py --real-p5`):
  - On the named roads, reroutes that drive back into the closed road fall
    from **82.3% to 8.3%** (666 asked). On the most-used stretches, from
    **73.6% to 18.9%** (106 asked).
  - **None** goes back onto the stretch the driver turned from in the
    direction they were driving it.
  - 68 of the 72 reach a *different* part of the same shut road, 5–293 km
    later (median 78 km), by edges the plan never drove. The other 4 drive
    the marked stretch the other way, away from its gate. Two of those are
    the verdict's 2-in-99, a trip that starts on the stretch. All are
    explained below.
- **The three fixes** hold on the edges the routes drive:

  | road | before | built |
  |---|---|---|
  | North Cascades | Jul 1 – Sep 30 | **May 16 – Nov 2** |
  | Crater Lake, West Rim | Aug 1 – Oct 14 | **Jun 30 – Oct 13** |
  | Crater Lake, East Rim | Aug 1 – Oct 14 | **Jul 21 – Oct 12** |
  | Going-to-the-Sun | Jul 1 – Sep 30 | **Jul 13 – Sep 24** (the record, not OSM's guess) |

- **The -next pair:**
  - the continuity check passes **11,414 of 11,414** legs;
  - `tests/test_national_routes.py` has **11 passed**;
  - the suite on `processed-ne` and the iOS suite: see "How the data was
    built".

## 1. Margins, by source, where the rows are written

| source | where | margin | written as |
|---|---|---|---|
| OSM undated winter (`osm_default`) | `pipeline/closures.py`, `WINTER_SPRING_MARGIN_DAYS = 45` | spring end +45 days | `WINTER` = Nov 1 – **Jun 14** (was Apr 30) |
| `UNKNOWN_SEASON` | `pipeline/winter_closures.py`, `UNKNOWN_MARGIN_DAYS = (7, 7)` | ±7 days | Sep 24 – Jul 7 (was Oct 1 – Jun 30) |
| MVUM dates, NPS-description dates (`agency_dated`) | `pipeline/winter_closures.py`, `AGENCY_MARGIN_DAYS = (7, 7)` | ±7 days | each window 7 days longer at both ends |
| hand table (roads and park windows), OSM-dated conditionals | | none | as before |

**The router is untouched.** `in_window`, `_weights` and `SeasonalClosures`
are as they were, so the windows are still the closure version every cache
keys on (the brief's trap 2).

**`WINTER`'s readers.** The brief named three: `closures.py:219`, `:340` and
`:343`. Every one is the undated source:
- `_rule_windows` returns it for `no @ winter` and `no @ snow`. That covers
  ways and gates, since `gate_windows` reads conditionals through
  `_car_windows`.
- `way_windows` uses it for `winter_service=no` and for `seasonal` in
  `SEASONAL`.

No dated rule reads the constant. A dated `no @ (Nov-Apr)` builds its own
`(11, 1, 4, 30)` in `_window`, and `yes @ (May-Oct)` builds the same by
`_complement`. Both keep Apr 30. So the constant carries the margin
(`WINTER = widen([WINTER_TAGGED], after=45)`), and `WINTER_TAGGED` keeps what
the tag means. `tools/seasonal_risk/windows.py` classes rows the same way, and
now reads either value as the default.

**The ±7.** It is applied in `federal_rows` to each agency line's windows
before they are matched to edges (`_with_margin`). That means
`UNKNOWN_SEASON` from MVUM ("seasonal, no readable dates") or NPS ("seasonal,
no dates"), and every other MVUM or NPS-description window. A park's window
(`nps park …`) is the table's and takes none. `widen` merges windows that meet,
and a margin that would close every day closes the whole year.

**Each margin mutated** (`tests/test_closures.py`, `TestMarginsBySource`):

| change | tests that fail |
|---|---:|
| `WINTER_SPRING_MARGIN_DAYS` 45 → 44 | 6 |
| `UNKNOWN_MARGIN_DAYS` (7, 7) → (7, 6) | 3 |
| `AGENCY_MARGIN_DAYS` (7, 7) → (6, 7) | 2 |

## 2. The default gives way to a dated winter on its own edge

**Why it was added.** The first rebuild (v1) applied the margins row by row,
as the verdict's Q4 did. An edge closes when any row closes it, so the
default's new Jun 14 outlasted every dated window it sat beside. On
`processed-ne`:
- Lincoln Gap would have opened Jun 15 instead of May 16;
- VT 108 Jun 15 instead of May 1;
- the Mt Washington Auto Road Jun 15 instead of its table date, May 23.

Before the margin this never mattered: the default ended Apr 30, ahead of
every dated window. But the decided policy gives the hand table and OSM's
own dates no margin, and v1 had handed them one through the back door. The
master session decided the rule below. It is the same specific-beats-general
precedence as decision 4 of `docs/winter-closures-national.md`, where a table
road replaces its park's window on its own edges.

**The rule** (`closures.seasonal_rows`, used by `closures.main`):
- On an edge with a **dated window that covers Jan 15**
  (`WINTER_EVIDENCE_DAY`), the edge's `osm_default` rows are dropped. Dated
  means an OSM conditional with dates, a table row, a park window, or MVUM
  or NPS dates.
- A dated window for another season says nothing about winter, and the
  default beside it stays. Carson NF's MVUM `07/26-04/30` is open to cars all
  winter and shut May to July; another case is `no @ (Apr 1-Oct 31)` beside
  `seasonal=yes`. Dropping the default there would open the road all winter,
  the unsafe side. That was the master session's second call.
- A gate between two edges (`rule` "through") gives way as a whole when
  either of its edges has such a window. Its two rows go together, because
  the router reads a gate as the two edges it joins and refuses a table that
  names one. This is what opens the North Cascades Highway on May 16. The
  Ross Dam lift gate, `access:conditional=no @ winter`, stands between the
  table's last edge and the next, and as a gate it would otherwise hold the
  crossing to Jun 14.
- An edge with only guesses, the default and `UNKNOWN_SEASON`, keeps every row.

Tests (`TestTheDefaultGivesWay`), each on synthetic rows:
- Lincoln Gap's dates and the Auto Road's table row win over the default;
- an MVUM date, an NPS description and a park window each count as dated;
- Carson's MVUM window and an Apr–Oct OSM window keep their winter, and so
  does a window that starts Jan 16;
- guesses alone all stand;
- the Ross Dam gate gives way whole, and a gate between guesses stands.

Without the rule five of them fail, and without the Jan 15 condition three.

**What it gave back.** Each count is against the previous run of the same data:

| | rows given way | edges with fewer closed days than v1 | km |
|---|---:|---:|---:|
| `processed-ne` | 49 | 49 | 51.9 |
| national, its 51 regions | 826 (on 824 edges) | 699 | 1,239.2 |

The Jan 15 condition keeps the winter closure on **11 edges, 23.0 km**,
nationally. That is the share of the 827 edges with both a default and a
dated window whose dated windows all miss Jan 15. In New England it keeps
none.

**Named roads in New England** (`processed-ne`, the road's own rows; open days):

| road | before the build | v1 (margins only) | built |
|---|---|---|---|
| VT 108 (Smugglers' Notch) | May 1 – Oct 31 | Jun 15 | **May 1 – Oct 31** |
| Lincoln Gap Road | May 16 – Oct 14 | Jun 15 | **May 16 – Oct 14** |
| Mt Washington Auto Road | May 23 – Oct 18 | Jun 15 | **May 23 – Oct 18** |
| Hurricane Mountain Road | Jun 1 – Oct 31 | Jun 15 | **Jun 1 – Oct 31** |
| Jefferson Notch Road | May 1 – Oct 31 | Jun 15 | **Jun 15 – Oct 31** |
| Kelley Stand Road | May 1 – Oct 31 | Jun 15 | **Jun 15 – Oct 31** |
| Evans Notch (ME 113) | May 1 – Oct 31 | Jun 15 | **Jun 15 – Oct 31** |
| Rockwell Road (Greylock) | May 20 – Oct 29 | May 20 | **May 20 – Oct 29** |

**VT 108 is dated.** Its ways carry `motor_vehicle:conditional=no @
(Nov-Apr)` beside `winter_service=no`, and its gates carry the same dates. So
under the rule it opens May 1, not Jun 15. The master session's first
expectation had it at Jun 15, as if it carried only the default.

**Jefferson Notch, Kelley Stand and Evans Notch** carry only
`winter_service=no`. They open Jun 15 because the policy is working as
decided, not by accident. The verdict picked +45 over the pooled curve's +14
for the smaller worst case, and these low gravel roads are where the pooled
curve fits better ("Sensitivities"). That trade was already made.

**Some edges now open earlier than before the build.** These are edges whose
own winter is shorter than the old Nov 1 – Apr 30 default that sat beside
them. That default no longer applies there, by the rule above. In New
England, 16 edges:
- most are MVUM roads whose dates, less 7 days, start a week or two after
  Nov 1: Cherry Mountain, Zealand, Wild River and Red Mill Campground Roads;
- Ayer Road is now closed Dec 1 – Apr 1 by its own `no @ Dec 1-Apr 1`;
- Cardigan Mountain Road is now closed Nov 1 – Mar 31 by its gate's dates.

Nationally there are 582 such edges, 24 of them the fixes'. Most are MVUM roads
whose dates, ±7, are a few weeks shorter than Nov 1 – Apr 30, a median 54
days. Another 57 are OSM-dated, Kings Canyon (CA 180) among them, 14
days fewer. 45 are table edges: Crater Lake's rims, North Cascades, and the
North Cascades Highway's own edges, which now close Nov 3 by the table
instead of Nov 1 by the default.

**The Auto Road's one-way pair.** Near its base the Auto Road is two one-way
edges 9 m apart (726813 up, 726814 down, on `processed-ne`). The table's path
through its waypoints took only one of them. The other kept only
`seasonal=no_snow`, so one direction still opened Jun 15. Two waypoints, one
on each half, fix it; the window is unchanged. This is the same fix as
Crater Lake's North Entrance split (fix 2).

## 3. The three window fixes

**1. North Cascades (WA 20).** The `north_cascades` row's last waypoint now
lies on the 30 m "Highway 20" edge past the Silver Star Gate (24800421
nationally). That is the edge whose NPS `USFS SEASONAL=Yes` row had put it
under `UNKNOWN_SEASON`. The table's window replaces the unknown season there,
as on any table road (level 2 in `federal_rows`). The edge now closes 47 fewer
days.

A report line was added, which closes nothing: every unknown season on an
edge that meets a table road's path (`winter_closures.unknown_beside`, printed
by `closures.py`). It has **4 hits, all in Washington, left as they are**:

| beside | edge | road | length | row |
|---|---:|---|---:|---|
| north_cascades | 113702 (WA region) | National Forest Development Road 400 | 1,614 m | NPS `USFS SEASONAL=Yes`, no dates |
| north_cascades | 362317 (WA region) | (no name) | 40 m | NPS `USFS SEASONAL=Yes`, no dates |
| chinook_pass | 480564 (WA region) | (no name) | 86 m | NPS `MORA SEASONAL=Yes`, no dates |
| chinook_pass | 480567 (WA region) | Sunrise Park Road | 26 m | NPS `MORA SEASONAL=Yes`, no dates |

The edge ids are the WA region's own, as `closures.py` printed them in its
sidecar. They are side roads leaving the passes, not the passes. Sunrise
Park Road is Rainier's Sunrise Road, which has its own unknown season.

**2. Crater Lake.** The park's one window (Oct 15 – Jul 31) is split into two
table rows, both from `tools/seasonal_risk/q2_published_dates.csv`
(nps.gov/crla/planyourvisit/hours.htm), under the table's own rule: the
longest the operator published in its last ten seasons.
- **West Rim**, the North Entrance Road and West Rim Drive, both
  carriageways of the North Entrance split. Openings 2014–2023, the latest
  Jun 30 (2023). Closings 2012–2021, the earliest Oct 14 (2016). Closed
  **Oct 14 – Jun 29**.
- **East Rim**, from the headquarters junction round the east rim to North
  Junction. Openings 2013–2022, the latest Jul 21 (2017). Closings: the ten
  latest seasonal ones, 2011–2012 and 2014–2021, the earliest Oct 13 (2017).
  Closed **Oct 13 – Jul 20**. Left out: **2013's Oct 1**, the first day of the
  federal government shutdown, when every national park closed. It is not a
  closing for the season, and with it the window would close on Oct 1.
- The park's window stays on its other seasonal roads: Pinnacles, Grayback,
  the Mazama Village entrance road and NFD 2304.

**3. Going-to-the-Sun.** A new table row from NPS's Logan Pass record
(nps.gov/glac/learn/news/logan-pass-opening-and-closing-dates.htm, read
2026-10-22), Avalanche Creek to Rising Sun. Its last ten seasons are
2013–2022, since 2023 is blank.
- Latest opening Jul 13, in both 2020 and 2022. 2020's was delayed by the
  pandemic; 2022's, by avalanches, sets the same date.
- Closings NPS footnotes as something other than the season are left out:
  - 2014 (Sep 22), 2015 (Oct 5) and 2022 (Oct 16): road rehabilitation;
  - 2017 (Sep 3): the Sprague Fire, then construction;
  - 2013 (Sep 23): the government shutdown. The brief named fire and
    construction; the shutdown is left out on the same ground, that it isn't
    seasonal. With it, the window would close Sep 23 instead of Sep 25.
- The earliest of the rest (2016, 2018–2021) is Sep 25 (2019).
- Closed **Sep 25 – Jul 12**. That holds OSM's `Oct-Jun` on every day, so on
  the edges the row covers, the measurement is what closes the road.
- Outside it, between Lake McDonald Lodge and Avalanche, and Rising Sun and
  St. Mary, OSM's `Oct-Jun` and NPS's descriptions still apply.

## 4. P5: the reroute remembers

**Server** (`server/app.py`, `pipeline/router.py`):
- Every route Feature, and the loop's, has `properties.seasonal`: one entry
  per maximal run of consecutive route edges with any row in
  `seasonal_closures`. Each entry gives `edges` (row ids), `forward` (driven
  u → v), `from_m` and `to_m` along the route, and `pack`, the fingerprint the
  ids belong to. The fingerprint is the pack's (`/api/health`'s `pack`), or
  for a graph built from parquets the same hash over its source files.
- `/api/route` takes `avoid_edges=ROW,-ROW,…&avoid_pack=FINGERPRINT`, a
  leading minus meaning v → u. The edges become directed slots
  (`Router.avoid_slots`) and are closed through the `blocked` path keep-ahead
  uses (`Metric.blocking`). That covers both arms, plain and keep-ahead, the
  spliced legs (`options.spliced_route`) and a loop's rejoin
  (`LoopPlanner.resume`).
- A fingerprint that isn't this graph's is ignored and logged, never refused,
  and so is a token that isn't a row.
- **The cap is 2,000 edges** (`MAX_AVOID_EDGES`): the first 2,000 sent count,
  and the app sends its newest stretch first.

**Per direction, not per edge.** The avoid closes each edge only the way the
route drove it. A car that turns back on the stretch itself is snapped
forward off the road under it (`Router.snap`; the verdict's "Limits"). Closing
both directions would leave it no way off and the reroute would 404. One
direction lets it drive back out, and a reroute can never re-enter the way it
was going. The test: closing the stretch the other way round sends the
driver back over Lincoln Gap again
(`tests/test_seasonal_policy.py::test_only_the_direction_turned_from_is_closed`).

**No cache a reroute can hit keys without it.** A loop's reroute is
`/api/route` with `via`, answered by `LoopPlanner.resume`, which builds its
own metric per request and reads none of the planner's caches. `LOOP_RESULTS`
is `/api/loop`'s, which no reroute calls and which takes no avoid set.
`test_no_cache_a_reroute_reaches_keys_without_it` fails if either changes,
and `test_a_loop_rejoin_honours_it` asks plain, avoided and plain again.

**App** (`ios/Sources/NavigationModel.swift`, `RouteService.swift`,
`Models.swift`):
- A stretch is turned away from when a wrong-way episode opens while the car
  is on it, or while it starts within 25 km ahead (`turnedAwayAheadMeters`).
  The distance along is the turn-back point, `wrongWayTurnBackAlong`.
- Every reroute after that, until arrival, sends it: plain, keeping ahead,
  by legs, round a loop or "fastest". It travels in
  `RouteService.avoiding`, a task-local `reroute` sets around whichever
  fetcher it calls, so no seam or stub changed.
- Only the newest stretch's graph's stretches are sent, each edge once.
- No button and no notice.

**Tests:**
- `tests/test_seasonal_policy.py`, 19, on `processed-ne`: the listing, both
  arms, keep-ahead, a stale fingerprint, bad tokens, the cap, direction, the
  loop rejoin, the spliced route. Disabling the avoid in `Router.route` fails 4.
- `ios/Tests/SeasonalStretchTests.swift`, 8: a simulated drive that turns
  back at a gate on a stretch, against a backend that sends it back up the
  stretch unless asked with the avoid set, as the server does today. No
  later reroute re-enters, through the off-route, wrong-way and "fastest"
  reroutes. Also the 25 km edge both ways, and the request body. Sending the
  avoid set as nil fails the drive test.

### The escape hatch: does the 25 km rule fire on ordinary wrong-way episodes?

- **Real-trace replays.** The 18 recorded drives' routes predate the field,
  so nothing can be marked in a replay. Their own wrong-way episodes were
  checked instead (`ReplayDumpTests`): one in 18 drives, the deliberate
  U-turn of drive-2026-10-06-122558. The nearest seasonal edge to the 25 km
  ahead of it on its route is 9.1 km away (Reservation Road). It would not
  fire.
- **Simulated drives.** The two personas that reverse on purpose are
  `wrongWayAlong`, at 40% of the route, and `loopWrongWay`. Over
  `tools/e2e_od_pairs.json` at every pref, asked of the server in process on
  Aug 15 and Oct 22, that is 1,198 staged episodes. **The rule fires on
  one**: loop-019, the 80 km Bethel loop. Its scripted U-turn is 3.8 km into
  Evans Notch (ME 113, `winter_service=no`). The driver did turn round on the
  stretch, so the rule does what it says. But the persona wasn't turned away
  by a gate, so Evans Notch drops out of that loop's later reroutes. This is
  the one case to report, and the 25 km stays.

### P5 against the study

The study's Q3 harness was adapted rather than rewritten. `--real-p5` asks
every replayed P0 reroute a second time with the `avoid_edges` the app would
send. Those are the stretches of the plan's scenic arm that start within
25 km ahead of the turn, or that the driver is on, at the point 30 m short of
the closed road. Each reroute is asked plain, then with `declined_uturn` if it
turns the driver round, as the app asks it. Each `P5 built` row says which
closed edges it entered, and whether the avoid set named them, named them in
the other direction, or didn't name them.

On v3, `named` (88 cases) and `top` (16):

| | P0, sends back | built P5, sends back | the study's P5 (whole road closed) | built P5, no way on |
|---|---:|---:|---:|---:|
| named | 548 of 666 (82.3%) | 52 of 628 (8.3%) | 0 of 72 | 38 (`CLOSED_FOR_SEASON`) |
| top | 78 of 106 (73.6%) | 20 of 106 (18.9%) | 2 of 12 | 0 |

By distance from the closed road, P0 sends back 93% within 7 km and 57% at
60–100 km. Built P5 sends back 10% and 4%.

**Every built-P5 send-back, explained:**
- **50 of 52 named and 18 of 20 top: another part of the same shut road.**
  These cases are Dunraven, Sonora, Crater Lake and Kelley Stand, each driven
  b → a, and the most-used stretch 2246084. The reroute goes round and
  reaches the road again from its far end, 5–293 km later (median 78 km),
  by edges the plan never drove and the avoid set never named. The study's
  P5 closed the whole named road; the app can only name what the driver was
  routed onto. If that far gate is shut too, the driver meets it, turns, and
  the rule marks that stretch in turn. P5 can't see a road before it is on a
  route, and closing a whole road would be a ban by another name.
- **2 named (Stevens Canyon a → b, at 2 km, asked with `declined_uturn`) and
  2 top (3852782): the marked stretch, driven the other way.**
  - 3852782 is the verdict's 2-in-99: the trip starts on the closed stretch
    itself, and the reroute drives off it the way it came, the only way off.
    The avoid closes only the way the driver was going (see "Per direction"),
    so that is allowed, and it re-enters nothing.
  - Stevens Canyon's keep-ahead reply drives 5 km on and comes back down the
    stretch's lower end the other way, toward the driver's destination.

  None of the four drives the stretch toward the gate.

**Stranding, re-run** (`tools/seasonal_risk/built/`, all four Q scripts, both
curves). In this run the built windows are Q4's P0, so its P0 rows are the
build:

| per 1,000 trips | us | near | ne | named |
|---|---:|---:|---:|---:|
| the build, high-pass curve | 9.9 | 189.3 | 3.5 | 580.9 |
| the build + P5 | 5.9 | 121.7 | 1.6 | 412.2 |
| the build + P5, pooled curve | 5.9 | 161.3 | 1.6 | 503.4 |
| verdict, recommended + P5 (pre-decisions data) | 6.5 | 489 | 3.4 | 1,582 |
| verdict, P0 today (pre-decisions data) | 37.6 | 1,474 | 7.3 | 3,842 |

These do not compare one for one with the verdict's:
- Q2's miss curves are now measured against the built windows, so
  "dangerous" is counted from the new ends;
- the data under them moved: the six decisions (D5 closes MVUM roads with no
  car designation) and the scenery additions;
- P5 is Q4's model of it, which drops the pointed-back minutes entirely.
  Measured, it leaves 8.3% and 18.9% of reroutes going back, almost all of
  them to another part of the road.

The direction matches the verdict's on every sample. The size is smaller,
mostly because the windows the risk is now measured from already carry the
margins. Q4's frontier on top of this build (`q4_choice.csv`) stacks a second
round of margins, so it is not a recommendation.

## How the data was built

- **Rebuilt three times.**
  - **v1**, margins only. It showed the default outvoting dated windows, and
    the master session stopped it before any swap.
  - **v2**, with the precedence. It showed the Ross Dam gate and the
    other-season windows.
  - **v3**, with the gate rule and the Jan 15 condition, is the pair now in
    `data/`.

  Each was rebuilt from scratch after the one before was deleted. Every run
  was alone on the Mac and was checked with `memory_pressure` first.
- **`data/processed-us-next/`.** Built by `tools/national_audit/sidecars_next.py`
  at `--jobs 2` with `SUNDAYDRIVE_FEDERAL=data/raw/federal`, the refetched
  MVUM. It took 1,511 s for 51 regions; v1's run took 22,699 s, but only
  because the Mac slept with its lid closed.
  - `seasonal_closures` goes from 13,588 rows to 12,839.
  - `closed_to_cars` (70,830) and `osm_unpaved` (19,237) are unchanged.
  - Everything else is an absolute symlink into `data/processed-us`.
- **`data/pack-us-next/`.** Built by `tools/national_audit/pack_next.py`
  against `data/pack-us` in 240 s (pack.py's peak 11.99 GB).
  - 25 arrays were written new and 67 cloned.
  - The three gates' default rows that gave way changed the through-barrier
    set, so the turn expansion moved: 20,186,985 routing nodes against
    `pack-us`'s 20,186,991.
  - The pack's `manifest.json` is new, so its fingerprint, and with it every
    route's `seasonal[].pack`, changes at the swap. That is expected: the
    app's held stretches are ignored, not refused.
- **Checks on the pair.** The continuity check passes 11,414 of 11,414 legs
  in 288 s. `SUNDAYDRIVE_PACK=data/pack-us-next pytest
  tests/test_national_routes.py` has 11 passed. Only then was
  `data/pack-us-next.done` written.
- **New England.** `closures.py` was run on
  `data/raw/new-england-latest.osm.pbf` over `data/processed-ne` into
  scratch, once with `usa`'s pipeline (`git archive usa pipeline`) and once
  with this branch's. `closed_to_cars` and `osm_unpaved` come out
  byte-identical. Nothing under `data/processed-ne` was written, so it needs
  `closures.py` rerun at merge.
- **The suite.** `SUNDAYDRIVE_DATA=data/processed-ne pytest tests/`:
  **1,299 passed, 24 skipped, 0 failed** at `008420e`. iOS on the branch: 535 tests, 47 skipped, one failing test,
  `DriveReplayTests.test_no_recorded_drive_hears_the_same_maneuver_twice`.
  That is `usa`'s own replay red: `usa` built from `git archive` runs 527
  tests with the same one failing. The 8 extra are `SeasonalStretchTests`.

## Not done

- **Defect 4** of the verdict, narrowing Lassen's and the table's spring
  ends: not approved, not done.
- **The 4 adjacency hits** are listed, not fixed.
- **The verdict's CSVs** under `tools/seasonal_risk/` are untouched. This
  build's re-run is in `tools/seasonal_risk/built/`.
