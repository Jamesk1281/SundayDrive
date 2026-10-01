# Brief: loops match the wrong pass of a road they drive twice

**Status: diagnosed, not fixed (2026-09-30).** No product code has been
touched. The defects were found by the overnight simulated drives: Findings 1,
2 and 2b in `docs/overnight-e2e-drives-brief.md`. Each is pinned by a strict
`XCTExpectFailure` in `ios/Tests/SimulatedDriveRegressionTests.swift`. The
harness, the regression tests and this brief all live on
`claude/overnight-e2e-drives`, which is **not merged to main**.

## The symptom, as measured

The harness drove all 20 committed loops (`tools/e2e_od_pairs.json`,
`loop-001`…`loop-020`) through the real `NavigationModel` with perfect GPS:
fixes exactly on the line, 1 Hz, and a synthetic clock. Results:

| outcome | loops |
|---|---|
| banner never leaves step 0 ("Head north on Cambridge Street · 18 mi" for the whole loop) | `001 004 007 009 010 011 012` (7) |
| `arrived` latched on the **second fix**, 20 m from the driveway, with 34–45 km to go | `013 015 017` (3) |
| rerouted although the car never left the line | 11 of 20 |
| loop cut short by that reroute ("the short way home") | 7, e.g. `loop-006` drove 1.6 of 31 km and `loop-016` 1.4 of 59.5 km |
| drove cleanly | only `018`, `019` |

The real app shows the same thing. The tier-2 screenshot
`docs/overnight-e2e/loop-001-180s.png` has the car mid-river on the Longfellow
Bridge under the first instruction.

## The mechanism: one defect, three symptoms

`progress(of:along:notBefore:)` (`ios/Sources/Geo.swift:73`) returns the
nearest segment at or after `notBefore`. It has **no upper bound**, and ties go
to whichever segment is strictly closer:

```swift
// Geo.swift:109
if distance < best, travelled + length >= notBefore {
```

A loop drives some roads twice: out and back on the same OSM way, and always
the start/end stretch. On such a stretch the two passes are the *same
coordinates*, so the car is equidistant from both. I measured this with a
line-for-line Python port of `progress`:

- `loop-013`, car 20 m out: near pass offset `5.686017158e-10` m, closing pass
  (45,143 m along) `5.686017412e-10` m.
- `loop-001`, car 9,186 m along: near pass `6.7779103e-11` m, later pass
  (19,430 m along) `6.7779165e-11` m.

So which pass wins is floating-point noise. With real GPS, metres off both
passes, it is a coin flip on every fix. Every one of the 20 loops lies within
3 m of itself somewhere; the shared stretch runs from 25 m (`loop-010`) to
38 km (`loop-015`). The server's `repeated_km` undercounts it.

The three symptoms:

1. **Banner stuck (Finding 1).** `remainingAtEachStep`
   (`NavigationModel.swift:866-874`) places each maneuver with the same
   function:

   ```swift
   let match = progress(of: step.coordinate, along: line, notBefore: floor)
   floor = match.travelled
   ```

   Step coordinates are rounded to 6 dp, which puts them 0.026–0.056 m off the
   vertex. Step 0 sits at the start, which is also the end. On **9 of 20 loops**
   (`001 007 009 010 011 012 013 015 017`) it lands on the closing segment:
   `stepRemaining[0] ≈ 0`, every later step is floored behind it, and
   `advanceSteps` can never pass step 0.

   The tier-1 count was 7 only because `013 015 017` "arrived" before they
   could show it. `004` is stuck by symptom 2 instead.

2. **Match jumps ahead (Finding 2).** `update` floors the match at
   `travelled - 100` (`NavigationModel.swift:896`) with no ceiling, so on a
   shared stretch it can land on the later pass. Then:
   1. `trackTurnaround` latches `passedTurnaround` (`:322-326`,
      `here.travelled >= loop.along`).
   2. The car drives on, away from that pass, so the floor pins the match and
      `offRoute` climbs.
   3. `reseatIfPinned` (`:1078`) refuses: its window is 500 m and the jump was
      10 km.
   4. The reroute goes "home", not via the far point.

3. **Driveway arrival (Finding 2b).** The loop guard at
   `NavigationModel.swift:911` only discards beyond-the-far-point matches until
   `seenBeforeTurnaround` is set, and the **first** good fix sets it. Fix 2
   then matches the closing pass with `remaining ≈ 0`, and `drivenTheLine`
   (`:957`) latches `arrived`, which never un-latches.

The loop's own far point is placed the same way, through
`progress(of: turnaround, …)` at `:598` (init) and `:1487` (`adopt`). On the 20
loops it landed correctly, but it is exposed to the same tie.

## Why it matters

Loops are a headline feature, and on this measurement they work on 2 in 20.
The failure modes are the worst ones on offer:

- no turn-by-turn at all;
- a drive that silently becomes the short way home, the exact Needham case
  `loopWaypoint` was written to prevent;
- an `arrived` that cannot be undone, 20 m from the driveway.

## Traps

1. **`<` → `<=`, or any deterministic tie-break, is not a fix.** The tie is
   float noise on identical geometry (above), and with real GPS the two
   offsets differ by millimetres in either direction. "Exactly equal"
   essentially never happens; "equal to within the GPS error" happens on every
   fix of a shared stretch.
   - The rule has to prefer **continuity**: among candidates within a
     tolerance of the best offset, take the one nearest the current progress
     (earliest at/after the floor).
   - The harness's independent instrument does this for maneuver placement
     (`Polyline.alongPositions`, `ios/Tests/SimulatedDriveSupport.swift`,
     earliest within 1 m). **Do not copy that code into the app.** The two must
     stay independent, or the harness ends up measuring the model against itself.
2. **A fixed forward ceiling breaks tunnels.** The dropout persona has 20–90 s
   gaps; at highway speed the car really is 2.7 km further on when fixes
   resume, and the match must follow. Any ceiling must scale with the time
   since the last fix, measured on `now()`.
   - `lastFixAt` is written with `Date()`, not `now()`
     (`NavigationModel.swift:882`), so it is invisible to the injected clock
     and to the harness. Use the injected clock.
   - A ceiling alone also does not separate passes that are both within it
     (a short out-and-back), so it is a complement to trap 1's rule, not a
     substitute for it.
3. **Do not special-case loops.** The same tie skips mid-route U-turns
   ("Make a U-turn to stay on North Washington Street", `urban-011`) and some
   interchanges (`suburban-013@0.0`) on point-to-point routes: Finding 4 in
   the overnight brief.
   - A fix inside `progress` or its callers will move those numbers too, and
     that is expected.
   - Finding 4 is out of scope: report what happens to it, but don't chase it.
4. **`progress` has five callers** (`NavigationModel.swift:598, 870, 897,
   1078, 1487`) and `GeoTests.swift` pins its behaviour.
   - `reseatIfPinned` (`:1078`) *deliberately* asks the unconstrained question
     (`notBefore: 0`). Read its doc comment, and `docs/reroute-audit.md`
     Finding 3, before touching it.
   - Changing the shared function's semantics for one caller changes all five.
5. **The strict `XCTExpectFailure`s will go red when the fix works.** That is
   the signal, not a regression. Convert F1/F2/F2b into plain assertions;
   F3–F6 should stay as they are.
6. **Don't judge it on the regression tests alone.** They pin three loops.
   The harness covers all 20, and covers what the change might break elsewhere.

## Done looks like

1. `test_F1`, `test_F2` and `test_F2b` in `SimulatedDriveRegressionTests`
   fail as unexpected passes, then are converted to plain passing assertions.
2. **All 20 loops** under `loopPerfect`:
   - 0 reroutes;
   - 0 arrivals before `drivenKm` ≥ 95% of the loop;
   - `bannerBehind` 0;
   - or each remaining exception named, with its trace.

   Run with `TEST_RUNNER_SUNDAYDRIVE_E2E=1` and
   `-only-testing:SundayDriveTests/SimulatedDriveTests/test_09_loopPerfect`,
   then `test_10_loopLate` and `test_11_loopEarly`. Summarise with
   `python3 tools/e2e_summarize.py <out>`.
3. **No regression on point-to-point.** Re-run `test_02_perfect`,
   `test_04_dropout`, `test_05_stopAndGo` and `test_08_earlyStop`, and compare
   with the overnight table in `docs/overnight-e2e-drives-brief.md`:
   - still 0 reroutes;
   - 582/582 arrivals;
   - banner-behind / banner-skipped no higher than perfect 26/23 and dropout
     19/23.

   Dropout matters most (trap 2).
4. The default suite still passes: 290 run / 258 passed / 32 skipped with no
   server. With the server, `LiveDriveTests` (7/7) and the regression class
   pass. `DriveReplayTests` replays 12 real phone traces from the main
   checkout's `traces/`: unchanged, or every change explained.
5. A short "What was fixed" section appended to this file, with before/after
   numbers. Include what happened to Finding 4's numbers as a side effect.
6. **Escape hatch:** if no single tolerance separates a genuine tie from a
   legitimate jump without breaking (3), stop. Write up the trade-off with the
   numbers, and leave the decision to the owner, rather than shipping a
   compromise silently.
