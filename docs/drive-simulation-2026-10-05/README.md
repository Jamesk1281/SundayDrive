# Pre-release drive simulation, 2026-10-05

This was tested against `191e15c` (400 km loops, compass), with a local server on `data/processed-ne`. Every harness change lives in scratch copies, and nothing in `ios/`, `server/` or `pipeline/` was edited. Earlier rounds replayed the real drives, used the overnight personas, and mutated constants. This round tried angles those never covered:

- GPS failure modes the 12 real drives never contained;
- loops up to the new 400 km cap;
- a race detector;
- a non-English locale;
- API fuzzing;
- production-vs-local diffing;
- concurrency;
- direction invariants on the compass.

## Findings, worst first

### 1. A loop's match can jump onto its own return leg and stay there

This existed before the 400 km change, which makes it much costlier. A loop leaves and returns near the same point. Once the first outbound fix has matched, nothing stops a later noisy fix matching the *return* pass if it is nearer by more than the 1 m tie. `travelled` then jumps to nearly the whole loop. Because it only ever grows, the drive either:

- **arrives on the spot**, when `remaining < 40 m`, or
- **is stuck for the rest of the day**. Here `remaining` is about 120 m, which is inside `noRerouteWithinMeters` (300 m), so it never reroutes. It is also outside `arrivalMeters`, so it never arrives.

The 400 km Needham loop (`longloop-001`, starting on Great Plain Avenue) shows the stuck case. Ten seconds in, one fix flipped the banner to "Arrive at your destination". Over 8 simulated hours and 253 maneuvers the driver heard **2 prompts**, and the banner stayed on the last step all day. With **mild noise matching the real traces** (σ 3 m, accuracy 3–10 m), the same thing happened: 28,626 skipped banners and 251 missed prompts.

| 28 loops (20 standard + 8 of 150–413 km) | current build | experimental gate |
|---|---|---|
| loopPerfect: early ends / skips | 0 / 0 | 0 / 0 |
| loopMild (real-trace noise): skips / missed prompts | 28,778 / 269 | 21 / 31 |
| loopColdStart (first 30 s at σ 15 m, acc 20–40, then mild): ended ≥ 500 m short | **4** (3 after 0 km, 1 after 1 km) | 0 |
| loopNoisy (existing noise model): skips / missed / early ends | 29,183 / 275 / 1 | 238 / 33 / 0 |
| loopCanyon: skips / early ends | 34,665 / 5 | 4,713 / 1 |

From Needham, the 20, 40, 80 and 150 km loops drive clean on the current build. The **250 km loop under mild noise ended at 133 of 256 km**, so the risk sits in the long loops this release unlocked.

**Experimental gate** (in a scratch copy only): reject a match more than `150 m + 50 m/s × seconds since the last accepted fix` ahead of `travelled`, unless 5 arrive in a row. Two runs were unchanged by it:

- **Genuine departures** (missedTurn, loopLate, loopEarly) and **perfect**: identical counts.
- **Dropout**: still 79/79 arrivals.

But it fails **50 unit tests**, because many fixtures jump kilometres along a line in one fix without advancing the clock (`test_a_whole_leg_skipped_between_fixes…`, `test_reaching_the_end_of_the_line_arrives`, …). Treat it as proof of where the fix goes, not as the fix. A narrower alternative is for loops to never arrive before `passedTurnaround`. That covers the driveway ends but not the stuck-for-hours case.

### 2. One bad fix reroutes the driver

`offRouteCertainMeters`: past 200 m, a single fix counts as the whole 3-fix streak. The spike persona throws one fix in 150 by 220–450 m, at a stated accuracy of 20–35 m. Every spike rerouted, 1.3 requests per spike: 1,468 over 79 routes. That led to 345 adoptions of road already driven, 145 missed prompts, and on `rural-010` a spoken "Make a U-turn on Beechnut Drive" for a road 2 km behind the car.

**Likelihood:** low on the roads we have data for. **0 of 29,736 real fixes** were a spike. The 99th-percentile accuracy was 15 m, and the worst jump beyond speed was 37 m. All of that is suburban Massachusetts, with no downtown, tunnel or multipath data.

**Requiring two consecutive fixes past 200 m** cut spike reroutes from 1,468 to **20**. missedTurn and wrongWayStart came out **byte-identical** (same reroute counts, same median latency of 2.0 s and 1 s), because a real wrong turn produces a second far fix a second later anyway. But **39 unit tests** reach a reroute through exactly one teleported fix, and would need a second fix added.

### 3. Sustained multipath ("canyon") reroutes drivers who never left the road

The canyon persona runs 40 s of every 4 min with σ 35 m sideways error (capped at 90 m) and accuracy 30–60 m. That gave 310 reroutes over 2,424 km, 63 of 79 drives rerouted, and 160 adoptions of road already driven. A fix 70 m off at a stated 55 m counts toward the streak, even though its own error bar covers the gap.

Counting a fix as off route only when `offRoute > 60 m + horizontalAccuracy`, combined with #2, gave **310 → 0** reroutes and 358 → 38 banner-behind. missedTurn was unchanged or better (banner-behind 160 → 123). wrongWayStart's median reroute delay rose from 1 s to 2 s. Noisy routes went from 3 to 2 reroutes.

### 4. The compass disables the direction you're heading (from the `bcf283c` compass commit)

`LoopPlanner.sectors()` drops directions with fewer than `MIN_SECTOR_CANDIDATES`, but `plan()` can pick its best loop from one of them. The response's own `meta.sector` is then missing from `alternatives`. In the app:

- the current point is `.disabled`, so it is drawn faded;
- VoiceOver gives it the hint "No loop this long that way";
- the caption miscounts. A SW loop whose list held only NW read "This is the only direction with a loop this long from here", while NW was tappable.

It reproduced in the real app via XCUITest at 43.8248, -71.2048, 5 km: "Heading northeast" next to "2 of 8 directions" (see `compass-thin-direction.png`).

**Frequency:** 14/29 starts at 5 km, 4/30 at 12 km, **2/30 at the 40 km default**, and 0 at 100 km or more.

**Fix options:** in the app, include `response.meta.sector` in `availableSectors` and `directionCount`, which is two lines in `LoopModel` and needs no redeploy. Or on the server, always add `loop.sector` to `available`.

### 5. Smaller ones

- **Islands contradict themselves.** The New England check deliberately counts Nantucket, Martha's Vineyard and Block Island as inside. Then the server's raw error is shown verbatim: "point is outside the covered road network (currently New England)". From the driver's side that reads as "you're outside New England" while standing in it. Islands aren't in the graph (largest-component pruning), so the refusal is right. The words are wrong.
- `/api/loop`'s 400 message still says `km=5..200` (`server/app.py`).
- `tools/e2e_od_pairs.json` `suburban-005` ("out of Boothbay Harbor") is `expect: route`, but its destination is Monhegan Island. The refusal is correct, so the label is wrong.
- 12 km loops in a compass-chosen direction run long: 25 of 155 are more than 25% over target, against 3 of 30 first loops. The card shows the real distance, so this is cosmetic.

## Checked and clean

- **Thread Sanitizer**, first ever run: 364 tests, 345 passed, 19 env-gated skips, **0 races**. The replay suites were skipped because they're single-threaded and about 10× slower under TSan.
- **Locale:** `-testLanguage de -testRegion DE`, where a probe confirmed `en_DE` with comma decimals (`1.5.formatted()` gives "1,5"), passed 349 tests with 3 expected failures and 0 failures. Requests still send `0.50` and `42.28,-71.24`. ar_SA gave the same result, but only the region changes, since the app has no localisations, so right-to-left layout went untested.
- **Production vs local** on the same commit: 15/15 responses (9 routes including via and Greylock, 6 loops up to 400 km) **byte-identical** after JSON decoding.
- **Concurrency:** 28 requests fired 16 at a time, twice, during a loop sweep, came back byte-identical to serial.
- **API fuzz** (NaN, ±inf, 1e309, malformed coordinates, bad sectors, via equal to an endpoint, out-of-range values): **no 500s**. NaN `km` and NaN weights clamp to the maximum, which is harmless.
- **Loop invariant sweep** over 1,212 requests (30 random towns, 5–400 km, every listed direction):
  - every loop closed, steps within 0.1 m of the line, every listed direction plannable, and the echoed sector always the one asked for;
  - median length within 1% of target at every length, and within 7% at 200 km and longer;
  - start-to-turnaround bearing within 7.5° of its octant even where it rounds to the neighbouring one.
- **400 km payload:** 119 KB gzipped, 15,865 coordinates, 255 steps.
- **Long loops with perfect GPS:** 8/8 (150–413 km, up to 28,754 fixes) arrived with 0 reroutes. 28 loops took 583 s wall in total, so per-fix matching doesn't degrade on a 20k-point line.
- **The 2–7.8 km straight hops** (40 edges, mostly the Maine Turnpike): genuine. Current OSM has the same 9 nodes, and the two separately mapped carriageways stay 17–21 m apart over 9 km.
- **Point-to-point perfect, dropout and noisy** match the 2026-10-01 table. The 7 "arrived on step N-1" flags are Finding 9.

## Reproducing

All of these live in the session scratchpad, not the repo:

- scratch copies `sim*` (`git archive HEAD ios tools`, plus personas `spike`, `canyon`, `loopNoisy`, `loopSpike`, `loopCanyon`, `loopMild`, `loopColdStart` in `SimulatedDrive.swift`);
- a trimmed O/D list: 80 routes at pref 0.5, the 20 loops, and 8 loops of 150–400 km;
- `loop_sweep.py`, `prod_diff.py`, `concurrency.py` and `cmp.py`.

The persona edits are small enough to re-add from this description.
