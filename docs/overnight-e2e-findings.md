# Overnight end-to-end drives: the findings

**Status:** shipped — merged to `main` by `a2ddddc`. This is the part of the dispatch brief that outlived the work: its measurements, decisions and results. The brief itself, with its traps and done-list, was deleted on merge — `git show a2ddddc:docs/overnight-e2e-drives-brief.md` prints it. Section numbers and "below" refer to that brief's layout.

## The goal

Several full end-to-end drives of Sunday Drive, run unattended overnight, with
the emphasis on two things:

1. **Correct directions.** At every point of a simulated drive the banner, the
   distance-to-maneuver, the current-street readout and the spoken prompt are
   right for where the car actually is, and the route itself is legal and
   unambiguous.
2. **User experience across a whole trip.** Plan → start → drive → (go wrong,
   reroute) → arrive, as a driver sees it: no stuck banners, no reroute storms,
   no arrival 800 ft short, no prompts too late to act on, no screens that look
   broken.

"Several" means at minimum: **≥ 200 routes** through the Swift harness (tier 1)
across all six New England states and both arms, **≥ 6 driver personas** over
each, and **≥ 5 full simulator drives** with screenshots (tier 2).

## Findings

Run 2026-09-30, 00:40–03:10 EDT, on `claude/overnight-e2e-drives` off `6f26edf`.
**No product code was changed.** The voice is captured through `VoiceGuide`'s
existing `Speaker` protocol, and the clock and route fetcher through
`NavigationModel.now` / `fetchRoute` / `fetchLoopResume`, so no test-only seam
was needed either.

### Baselines, before any new number

| suite | brief said | measured |
|---|---|---|
| iOS, no server (`VoiceCatalogueTests` skipped) | 261 / 254 passed / 7 skipped | **265 / 258 passed / 7 skipped / 0 failed**. Four tests merged since the brief was written. |
| `LiveDriveTests` against 5173 | 7/7 except `test_the_reported_scenery_reflects_the_weights_that_were_sent` | **7/7, including that one.** It is not failing today. |
| backend `pytest tests`, `SUNDAYDRIVE_DATA=processed-ne` | — | **388 passed** |
| iOS after this branch, no server | — | 290 run / 258 passed / 32 skipped / 0 failed. The 25 new tests all skip without a server or `SUNDAYDRIVE_E2E=1`. |

The server was the worktree's `server/serve.py` app behind a scratchpad wrapper
that writes one access-log line per request, on 127.0.0.1:5173 with 5057 empty.
It logged 4,598 requests during the tier-1 run. All of them were local; nothing went to production.
Correction found at cleanup: my first plain `serve.py` launch (same worktree,
same `processed-ne`) was never stopped and also held `*:5173` beside the
wrapper's `127.0.0.1:5173`. Both served identical code and data, so no result
changes, but the access-log count is a lower bound on requests served.

### What was built

- `tools/e2e_od_pairs.py` → `tools/e2e_od_pairs.json`: **225 seeded pairs**,
  byte-reproducible. They are 40 urban (< 10 km), 40 suburban, 30 rural long hauls
  (42–217 km), 25 coastal, 30 cross-state, 30 parking-lot pins (the centre of a
  service-way cluster), 10 island/ferry pins and 20 loops. Every point-to-point
  pair runs at pref 0 / 0.5 / 1.0, so there are 582 routes, all six states.
- `ios/Tests/SimulatedDrive.swift`, `SimulatedDriveSupport.swift`,
  `SimulatedDriveTests.swift`: ten personas. They are perfect, noisy (AR(1)
  10 m σ, ±15 m cap, 50 m jump 1 in 150, accuracy 10–30 m), dropout (20–90 s
  gaps every 3–6 km), stop-and-go (20–60 s dwells at ~40% of turns), missed
  turn, wrong-way start, early stop (park 150 m short for 120 s, then walk),
  and three loop personas (perfect, deviate after the far point, deviate before it).
  - Every off-route stretch is a **server route**, never an extrapolated line.
    A missed turn is a route from 25 m before the junction, heading as
    approached, to 500–700 m beyond. It is kept only if it truly leaves the
    route (> 50 m apart 250 m on).
  - Truth is measured by an independent instrument: great-circle polyline
    lengths, this harness's own maneuver placement, road names parsed from the
    rendered instruction, and a synthetic 1 Hz clock injected as `model.now`.
  - One NDJSON line per drive, plus `tools/e2e_summarize.py` for the tables below.
- `SimulatedDriveRegressionTests.swift`: seven strict `XCTExpectFailure`
  cases, one per defect below. They are green while the defect exists and go
  red when it is fixed. All seven reproduce today.
- `SimulatorScreenDriveTests.swift` + `tools/e2e_sim_watcher.py`, for tier 2.
  The unit tests are hosted in the app, so the test mounts the app's own
  `PlanningView`/`NavView` on a `RouteModel` it configured. A host-side
  watcher runs `simctl location start` and `simctl io screenshot` on request.
  The simulator panel could not be used: it needs a human to grant access.
- `tools/audit_directions.py --pairs`: audits the committed list the way
  `/api/route` routes it (`snap_destination`, both arms,
  `_no_worse_than_fastest`). **Trap found on the way:** `_find_pbf()` takes
  the alphabetically first extract in `data/raw`, which is
  `connecticut-latest.osm.pbf`. Run on `processed-ne` without
  `SUNDAYDRIVE_PBF`, it would silently audit New England against Connecticut's
  restrictions and cache the result. I set it to `new-england-latest.osm.pbf`.
  The cache is now `data/processed-ne/forbidden_movements.parquet` in the main checkout.

Reproduce the whole night:

```
SUNDAYDRIVE_DATA=<main>/data/processed-ne PORT=5173 <main>/.venv/bin/python server/serve.py
cd ios && xcodegen generate
TEST_RUNNER_SUNDAYDRIVE_E2E=1 TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:5173 \
TEST_RUNNER_SUNDAYDRIVE_E2E_OUT=/tmp/e2e xcodebuild test -scheme SundayDrive \
  -destination 'id=<your sim>' -only-testing:SundayDriveTests/SimulatedDriveTests
python3 tools/e2e_summarize.py /tmp/e2e
```

To replay one drive, add `TEST_RUNNER_SUNDAYDRIVE_E2E_ONLY=<id>@<pref>`, add
`TEST_RUNNER_SUNDAYDRIVE_E2E_TRACE=1` for a per-fix trace, and select the
persona's method, e.g. `-only-testing:SundayDriveTests/SimulatedDriveTests/test_07_wrongWayStart`.
Loops take the bare id, e.g. `loop-013`.

### Tier 1: drives actually run

**4,024 drives run, over 602 distinct routes and 182,351 simulated km.**
164 persona×route combinations could not be staged and are counted apart
(reasons below), never as passes.

| persona | drives run | unstaged | arrived | driven km | reroutes/km | same-road adoptions | banner behind (drives) | banner skipped | dist err p50/p95 m (≤1 km) | prompt lead p5/p50 s | missing prompts | reroute openings unspoken | street mismatches / checked | hard-fail drives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| perfect | 582 | 0 | 582 | 26,316 | 0.000 | 0 | 26 (4) | 23 | 0.4/1.0 | 4.8/5.5 | 3 of 11573 | 0 of 0 | 498 / 1,575,785 | 43 |
| noisy | 582 | 0 | 582 | 26,304 | 0.001 | 18 | 99 (11) | 365 | 2.1/6.0 | 4.6/5.5 | 34 of 11541 | 11 of 20 | 745 / 1,573,479 | 33 |
| dropout | 582 | 0 | 582 | 26,318 | 0.000 | 0 | 19 (3) | 23 | 0.4/1.0 | 4.0/5.5 | 3 of 9475 | 0 of 0 | 272 / 1,261,770 | 10 |
| stopAndGo | 582 | 0 | 582 | 26,316 | 0.000 | 0 | 99 (4) | 729 | 0.5/1.4 | 4.7/5.5 | 4 of 11573 | 0 of 0 | 498 / 1,575,785 | 31 |
| missedTurn | 543 | 39 | 543 | 25,247 | 0.023 | 18 | 1104 (169) | 282 | 0.4/1.0 | 4.5/5.5 | 49 of 11126 | 309 of 557 | 490 / 1,507,276 | 213 |
| wrongWayStart | 515 | 67 | 515 | 24,163 | 0.021 | 2 | 757 (136) | 21 | 0.4/1.0 | 5.0/5.5 | 33 of 10475 | 262 of 511 | 437 / 1,434,218 | 193 |
| earlyStop | 582 | 0 | 582 | 26,258 | 0.000 | 0 | 26 (4) | 23 | 0.4/1.0 | 4.9/5.5 | 3 of 11446 | 0 of 0 | 498 / 1,571,930 | 11 |
| loopPerfect | 20 | 0 | 20 | 556 | 0.020 | 0 | 12977 (11) | 170 | 0.4/1.1 | 5.0/5.5 | 124 of 394 | 6 of 11 | 11752 / 42,201 | 15 |
| loopLate | 19 | 1 | 19 | 526 | 0.030 | 0 | 10336 (12) | 170 | 0.4/1.1 | 5.0/5.5 | 93 of 367 | 9 of 16 | 9255 / 39,849 | 17 |
| loopEarly | 17 | 3 | 17 | 347 | 0.089 | 11 | 5674 (9) | 806 | 0.4/1.0 | 4.9/5.5 | 46 of 251 | 18 of 27 | 4557 / 24,834 | 15 |

Columns:

- **Banner behind**: fixes where the maneuver on the banner lies more than
  3 m behind the true position (25 m for noisy; +30 m for step 0, per
  `passedMargin`).
- **Banner skipped**: fixes where the banner shows a later maneuver while an
  earlier one is still > 3 m ahead.
- **Distance error**: `distanceToNext` against the true along-route distance,
  within 1 km of the maneuver. Beyond that, the app's 111,320 m/° and a great
  circle's 111,195 m/° differ by 0.1–0.2%, which is not a finding.
- **Prompt lead**: seconds of travel between the last spoken final for a
  maneuver and reaching it.
- **Reroute openings unspoken**: adopted replacement routes whose first
  maneuver the car reached and the voice never said.

Unstaged: 67 wrong-way starts and 23 missed turns found no real road leaving
the junction away from the route. 16 missed turns had no turn, fork or exit in
the window; 4 loop deviations had no room before or after the far point.

What is **right**, and worth saying first:

- Over ~105,000 km of perfect, dropout, stop-and-go and early-stop driving on
  point-to-point routes: **0 reroutes, 582/582 arrivals per persona**.
- The distance to the next maneuver within 1 km: **p50 0.4 m, p95 1.0 m**.
- The street readout agrees with the independently rendered instruction on
  99.97% of 1.58 M checks.
- 3 missing prompts in 11,573 maneuvers.
- A deviation is rerouted **2 s** after the car crosses 60 m (p50 and p95).
- Parking 150 m short arrives after **91 s** (`parkedAtTheEnd`, as designed).
- Standing still off a never-joined route pauses the drive at 5 minutes
  (tier 2 screenshot).

The defects are concentrated in three places: **loops**, **reroutes that open
with a U-turn**, and **lines that pass near themselves**.

### Tier 1b: the directions audit on the same routes

582 routes audited (30 refused, the 10 island pairs × 3). The audit's
route matches the server's on km for all 582, so it audited the routes that were driven.

| failure | `directions-accuracy.md` (120 random MA routes) | this run (582 NE routes, fixed list) |
|---|---|---|
| route makes a turn OSM forbids | 1% | **0.2%**: 1 route, `parking-003@0.0`, at OSM node 5853462645 |
| misleading fork (straight is wrong, nothing said) | **0%** | **10%**: 65 forks on 56 routes, in every category (urban 7, suburban 8, rural 11, coastal 10, cross 10, parking 10) |
| ambiguous fork | 98% | 87% |
| start offset median / p90 | 135 / 589 m (random points) | 24 / 89 m (town and place pins) |
| end offset median / p90 | 195 / 496 m | 36 / 219 m |

The misleading-fork jump is the headline, **Finding 7**. The per-route list is
in the audit NDJSON; each record carries `misleading_at` router node ids.

### The defects

Severity is my judgement. Every `file:line` is a **guess at the mechanism**,
made from the traces and the code; none of them has been confirmed by a fix.

### Finding 1: on a loop, the banner never leaves its first instruction (critical)

- **Where:** 7 of 20 loops (`loop-001, 004, 007, 009, 010, 011, 012`),
  persona `loopPerfect`.
- **Observed:** on perfect GPS the banner shows "Head north on Cambridge
  Street" for the whole loop, and `distanceToNext` equals the whole remaining
  loop. Tier 2 shows it on the real screen: `docs/overnight-e2e/loop-001-180s.png`
  has the car mid-river on the Longfellow Bridge under "Head north on Cambridge
  Street · 18 mi".
- **Consequence:** no maneuver advances, so the voice has nothing to announce.
  A loop has no turn-by-turn at all.
- **Expected:** the banner advances like it does on a point-to-point route.
- **Mechanism (guess):** `remainingAtEachStep` (`NavigationModel.swift:866`)
  places each step with `progress(notBefore: previous)`.
  1. A loop's first and last vertex are the same point.
  2. Step coordinates are rounded to 6 decimals (measured 0.026–0.056 m off
     the vertex on four loops).
  3. So `distance < best` (`Geo.swift:109`) is a coin flip between the
     opening segment and the closing one.
  4. When the closing segment wins, `stepRemaining[0] ≈ 0`, and every later
     step is floored there too.
- **Replay:** `SimulatedDriveRegressionTests.test_F1_a_loop_banner_advances_past_its_first_maneuver`.
  It builds the model directly, drives 3 km, and needs no persona.

### Finding 2: loops are cut short, or end in the driveway, on a road they drive twice (critical)

On perfect GPS:

- **11 of 20 loops rerouted** on a drive that never left the line.
- **7 were cut short.** `loop-006` drove 1.6 km of 31 and `loop-016` 1.4 km
  of 59.5 before "You have arrived" at home.
- **3 (`loop-013, 015, 017`) latched `arrived` 20 m from the driveway**, with
  the whole 34–45 km loop still ahead.

Only `loop-018` and `loop-019` drove cleanly.

Trace of `loop-013`:

- Fix 1 (11 m out) matches correctly, with 45,152 m remaining.
- Fix 2 (20 m out) matches the **closing** leg, which comes home along the
  same street. Remaining reads 0, so `drivenTheLine` fires.

Trace of `loop-001`, at 9.2 km:

1. The match jumps 10.2 km ahead onto the retraced return pass.
2. `trackTurnaround` latches `passedTurnaround` (`NavigationModel.swift:324`,
   `here.travelled >= loop.along`).
3. The car then drives away from that pass, so the floor pins the match and
   `offRoute` climbs.
4. `reseatIfPinned` refuses, because the jump was 10 km and its window is 500 m.
5. The reroute therefore asks for the short way home and **20 km of loop
   becomes 10.8 km home.** This is exactly the failure `loopWaypoint` was
   written to prevent.

- **Expected:** a perfect loop drive is never rerouted and never ends before
  it is driven.
- **Mechanism (guess):** the match floor is `travelled - 100`
  (`NavigationModel.swift:896`), with no ceiling. `progress` takes the nearest
  segment anywhere ahead, so on a road driven twice a tie goes to either pass.
  The loop guard (`:911`) only protects fixes before `seenBeforeTurnaround`,
  which the first good fix sets.
- **Replay:** `test_F2_a_loop_driven_perfectly_is_never_rerouted` (`loop-001`)
  and `test_F2b_a_loop_does_not_arrive_in_its_own_driveway` (`loop-013`).
- **A harness gap to note:** the three driveway arrivals passed my own
  hard-fail rules. The loop's pin is its start, so "arrived 45 km short, 20 m
  from the pin" looked like a legitimate pin arrival. They were found by
  reading `drivenKm`.

### Finding 3: a reroute that opens with a U-turn never says it, then lags (high)

- **Where:** all missed-turn and wrong-way reroutes.
  - Missed turn: **309 of 557** adopted routes had their opening maneuver
    driven through and never spoken.
  - Wrong-way start: **262 of 511**.
- **Where it is worst:** when the replacement begins "Make a U-turn". The
  server snaps ahead with the heading, so the line starts at the next junction
  and comes back past the car. Wrong-way `rural-003@0.5`, from the trace:
  - t=7: reroute adopted.
  - t=8–16: banner "Make a U-turn on North Main Street", countdown correct,
    **never spoken**.
  - t=17: the car makes the U-turn at the junction.
  - t=17–23: the banner still says "Make a U-turn", the distance counts **up**
    13 → 113 m, and the readout says **"Off your route"** on the route.
  - t=24: it advances to step 1.
- **On screen:** `urban-003-wrongway-after-reroute-4s.png` shows "Off your
  route" in red under a car sitting on the orange line.
- **Scale:** banner-behind occurs in 169 missed-turn drives and 136 wrong-way drives.
- **Expected:** the U-turn is spoken, and once made, the banner moves to the
  next maneuver and the readout names the road.
- **Mechanism (guess):**
  - `matchAtAdoption` (`NavigationModel.swift:945`) is taken from the car's
    position on the line's *return* pass. After the U-turn, the car's true
    progress is below that anchor, so `runningBackwards` (`:1167`) holds the
    banner and `stepsDescribeWhereWeAre` (`:839`) stays false until the car is
    back level with where it was rerouted.
  - The voice is gated on that predicate (`:986-989`). During the approach
    `runningBackwards` is also true, so step 0 is never said.
- **Replay:** `test_F3_a_reroute_that_opens_with_a_u_turn_says_it_and_moves_on`.

### Finding 4: a line that passes near itself skips maneuvers (medium)

- **Where, clean GPS:** the banner advances past a maneuver still 3–43 m ahead,
  and remaining jumps up, on:
  - mid-route U-turns: "Make a U-turn to stay on North Washington Street"
    (`urban-011`, all prefs, every persona), "…on Main Street"
    (`suburban-023`), "…on Congress Street" (`coastal-002@0.5`);
  - interchanges whose ramps pass close to the approach: `suburban-013@0.0`
    goes from step 4 straight to step 6 at the Mid Cape Highway merge.
- **Scale:** 23 skip events on perfect, 729 on stop-and-go (it dwells 12 m
  before exactly these maneuvers).
- **Expected:** a maneuver is passed only by reaching it.
- **Mechanism (guess):** the same unbounded-forward match as Finding 2. The
  out-and-back leg is within metres of the car, so it wins the nearest-segment
  test before the car reaches the U-turn.
- **Separate question for the router:** whether "U-turn to stay on X" in the
  middle of a planned route is intended, or an artefact of a restriction.
- **Replay:** `test_F4_a_mid_route_u_turn_is_not_skipped` (`coastal-002@0.5`).

### Finding 5: ferry-only islands (medium)

- **Peaks Island from Portland** (`island-005`) is routed to the Portland
  waterfront. It returns 6.7 km and ends **2,488 m from the pin**, across Casco
  Bay, with no warning. It would "arrive" at the dock.
- **Mechanism (guess):** `SNAP_MAX_M = 5000` (`server/app.py:89`) lets
  `snap_destination` snap across open water.
- The other eight islands, and an island-internal Martha's Vineyard trip, are
  refused with "point is outside the covered road network (currently New
  England)". Clean, but misleading: they are in New England, and the graph
  simply has no roads there.
- **Replay:** `test_F5_a_ferry_only_island_is_refused`.

### Finding 6: raw OSM ref lists in instructions and in the voice (low)

- "Take the exit onto I 295;US 1", "…onto I 395;ME 9;ME 15",
  "…onto US 5;CT 15". These are shown, and handed to the synthesiser.
- This is also most of the street-readout disagreement. At an exit the screen
  shows the ramp's single ref ("US 1A") while the instruction names the list.
  That is 347 of the ~2,300 sampled mismatches for `I 295;US 1` alone. Other
  exits disagree name-against-ref: "MA 1A" vs "Lee Burbank Highway".
- **Mechanism (guess):** `_describe_turn` (`pipeline/router.py:2343`) uses the
  raw `ref` column (`:1974`) unsplit.
- **Replay:** `test_F6_instructions_carry_no_raw_ref_lists` (`suburban-002@0.0`).

### Finding 7: misleading forks are back, on New England (medium)

- 10% of the 582 routes pass a junction where carrying straight leaves the
  route and nothing is said. `docs/directions-accuracy.md` measured 0% on
  Massachusetts.
- Spread across every category and state, so not one bad region.
- Not investigated further: the fix history in `directions-accuracy.md` §2
  was measured on `data/processed`, and whether this is NE data, new junction
  types, or a regression is open.
- **Replay:** `SUNDAYDRIVE_PBF=<main>/data/raw/new-england-latest.osm.pbf
  .venv/bin/python tools/audit_directions.py data/processed-ne --pairs
  tools/e2e_od_pairs.json --out audit.ndjson`, then read `misleading_at`.

### Finding 8: noisy GPS (low)

Over 582 noisy drives (26,304 km):

- **0.001 reroutes/km.** 18 of them adopted the road already being driven,
  which restarts the banner.
- The banner skipped a maneuver still > 25 m ahead in 90 drives, at right-angle
  corners, where a lateral error projects onto the next leg.
- `currentStep` went backwards in 16 drives. The guess is `reseatIfPinned`
  re-deriving the step from zero after a 50 m jump.
- "Off your route" was shown while on the route in 422 drives.
- The noise model is mine (AR(1) with rare 50 m jumps), not fitted to the
  recorded traces, so treat the rates as indicative.

### Finding 9: arrival pre-empts a final maneuver within 40 m of the end (low)

- 32 perfect drives arrive (`drivenTheLine`, < 40 m) while the banner is still
  on the maneuver before "Arrive". The car is at the pin, so this is cosmetic.
- It is the assertion `LiveDriveTests` makes, and it would fail there on these
  routes (e.g. `urban-002@0.0`, `urban-017@0.0`).

### Note: prompt timing against the brief's 8 s

Final prompts land **p5 4.8 s, p50 5.5 s** before the maneuver on perfect
GPS. 89.7% are under 8 s and 147 of 11,570 are under 3 s. Prepares land at a
median 24.3 s.

This is the design, not a defect. `VoiceGuide.referenceFinalAt` is 6 s,
derived from utterance length. The brief's 8 s bar disagrees with that
derivation, and which is right is a product judgement I have not made.

### Tier 2: real app in the simulator

Seven drives on a dedicated simulator, with location from `simctl location
start`. Screenshots are in `docs/overnight-e2e/`: 16 kept, 700 px, from 60 taken.

| drive | route | what it showed |
|---|---|---|
| 1 urban | `urban-001@0.5` Burlington | Correct banner, distance and street through 3 maneuvers (`urban-001-step4-*`); arrival card. |
| 2 coastal | `coastal-001@1.0` Rockport→Gloucester | Clean (`coastal-001-step3-before`). |
| 3 parking-lot pin | `parking-002@0.5` | Arrives with the pin across from the route's end (`parking-002-arrival`). |
| 4 missed turn | `urban-002@0.5` Hartford | Reroute opens "Make a U-turn on Pleasant Street · 50 ft" (`urban-002-missed-rerouted`), then advances. |
| 5 wrong-way start | `urban-003@0.5` Bangor | **Finding 3 on screen:** "Off your route" while on the line, 4 s after the U-turn (`urban-003-wrongway-after-reroute-4s`). |
| 6 loop | `loop-001` Boston | **Finding 1 on screen:** first instruction after 3.6 km (`loop-001-180s`). |
| 7 stall | `urban-002`, car 400 m off the start | "Navigation paused · You haven't reached the route yet" after 5 min (`urban-002-stalled`). |

Screen judgements:

- The Apple Maps logo and "Legal" are visible and unclipped on every nav screen.
- No clipped or overlapping banner text was seen.
- Distances and street names matched the map in every screenshot I checked.
- The first-launch "Before you drive" notice (`notice-before-you-drive`)
  renders cleanly.

Two tier-2 harness artefacts, both corrected, not app defects:

- **Stall.** The first stall run never paused. The app's own trace showed 2
  fixes in 5.5 minutes: `simctl location set` reports once, and the stall is
  decided on fixes. A slow 3 m circle fixed it; a parked phone reports ~1 Hz.
- **Results sheet.** Every "results" shot showed the notice or the home
  screen, not the route results. Which sheet is open is view state that only
  a tap reaches, and the simulator panel needs a human to grant access. **The
  results sheet was not screenshotted.**

### What was not determined

- **Voice.** Never audible: muted in tier 2, captured as text in tier 1. That
  an utterance was *heard* in time is inferred from when it was handed over.
- **Reroutes land in zero simulated seconds.** Tier 1 awaits the server
  before the next fix. A phone keeps moving for the ~1 s round trip, so
  latencies are optimistic and races between an in-flight reroute and new
  fixes are not exercised.
- **Speed.** It is the route's average speed (clamped 8–30 m/s), slowing to
  6 m/s near turns. It is not posted speeds, and prompt lead-times depend on it.
- **Joining a replacement line** is my rule: aligned within 90°, within
  15 m, or at the line's start for a U-turn. 794 U-turn joins used the
  last case. A real driver's path to the new line was not modelled beyond
  continuing on the road they were on. There were **0 straight-line bridges**
  in the whole run, so no drive needed invented geometry.
- **Unstaged personas.** 67 wrong-way and 39 missed-turn combinations (of 582
  each) could not be staged on real roads. Those routes are untested for that
  persona.
- **Flicker.** The flicker counter keys on instruction *text*. A route that
  says "Continue onto Main Street" twice counts, so its 3,435 is not a finding
  and is omitted.
- **Timings.** Other sessions shared the Mac all night. No timing here is a
  performance number.
- **Loops, point-to-point, and cause.** Loop pairs are not in the tier-1b
  audit (the audit uses the router, not the loop planner). Whether the
  loop defects share one fix is untested.

The tier-1 results (`drives.ndjson`, `routes.ndjson`, `summary-*.json`) and
audit NDJSON are in the session scratchpad, not the repo, by the brief's rule.
The run can be regenerated with the commands above.
