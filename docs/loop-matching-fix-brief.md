# Brief: loops match the wrong pass of a road they drive twice

**Status: fixed (2026-10-01), on `claude/loop-matching-fix`, not merged.**
See "What was fixed" at the end. The brief below is as written on 2026-09-30,
when no product code had been touched. The defects were found by the overnight simulated drives: Findings 1,
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

## What was fixed (2026-10-01)

### The change

All in `progress` (`ios/Sources/Geo.swift`), plus a `near:` anchor at two
call sites in `NavigationModel.swift`. There is no ceiling, no loop special
case, and nothing copied from the harness.

1. **Ties are decided by continuity.** Every segment within
   `progressTieMeters` (**1 m**) of the nearest is a candidate. The one with
   the lowest `offset + 0.05 × along-line gap to near` wins, and ground behind
   the anchor counts double.
   - `update` passes `near: travelled`. Passing the floor instead does not
     work: just past a U-turn, the floor still reaches the outbound leg.
   - `reseatIfPinned` passes `near: travelled` with `notBefore: 0`.
   - `remainingAtEachStep` and the far-point placements (`init`, `adopt`) keep
     the default, `near = notBefore`.
2. **A segment matched at its clamped end is dropped when its neighbour is at
   least as near.** That end is the same vertex, on the same pass.
3. **`reseatIfPinned`'s "never forwards" guarantee still holds.** The tie
   window (1 m) is under `offRouteMeters − joinConfirmMeters`. The doc comment
   says why.

### Why these numbers: four wrong turns, each measured

| attempt | what broke | where |
|---|---|---|
| tie 10 m, nearest along the line | U-turn legs are adjacent segments over the same ground; one was dropped by float noise | `loop-017` turnaround |
| + forward bias | a 10 m window admits other vertices of the *same* road through a tight corner, 7.8 m off | `loop-001`, Pleasant St |
| + offset weight | a match that had run 88 m ahead on the return carriageway held a car parked 1.9 m from the outbound one (8.9 m from the return) | real trace `08-25-202122`, Southwest Cutoff |
| tie 1 m, pure gap | (a) a fix 0.3 m past a maneuver's vertex tied with the previous segment's end; (b) at a bend, two adjacent interior minima 0.999 m apart | real traces `08-14-155019`, `08-14-192546` |

The lesson: the tie has to be a *genuine* tie. Identical passes agree to
nanometres. Anything wider than about a metre is a different road, and
strict-nearest was right about it. **No escape hatch was needed.** One setting
passes every check below, and nothing was traded off.

### Loops (20 loops, perfect GPS)

| | before | after |
|---|---|---|
| loopPerfect: loops rerouted | 11 | **0** |
| loopPerfect: ended before 95% driven | 13 (3 in the driveway) | **0** |
| loopPerfect: banner behind (fixes / loops) | 12,977 / 11 | **4 / 4** |
| loopPerfect: banner skipped | 170 | **0** |
| loopPerfect: clean on all three counts | 2 | **16** |
| loopLate: ended before 95% | 12 | **0** |
| loopLate: behind / skipped | 10,336 / 170 | 13 / 0 |
| loopEarly: ended before 95% | 17 | 5 |
| loopEarly: behind / skipped / same-road adoptions | 5,674 / 806 / 11 | 53 / 0 / 0 |

The loopLate and loopEarly drives reroute once each by design (a missed turn).

**The four remaining loopPerfect exceptions** are `loop-007`, `014`, `016`
and `017`. Each is a single fix, 3–4 m past the apex of a mid-loop "Make a
U-turn to stay on …". At the apex the two legs are the same point, so position
alone cannot say whether the car is 3.5 m before the turn or 3.5 m after it.
The next fix resolves it. Heading (the fix's `course` against the leg's
bearing) would separate the two legs. That is not built, and it would be a
second signal in `progress`.

**`loop-011`'s single "remaining rose 11 m"** comes from the pre-join quote
(`km × 1000`, rounded to 0.1 km) giving way to the line's true length. It is
not matching.

**loopEarly's five short drives:**

- **New finding, pre-existing: `002` (52%), `010` (72%), `014` (47%).** These
  are identical, or nearly, on the base build: 25.3 and 13.8 km both times.
  - Mechanism, traced on `014`: the via-far-point replacement is adopted
    while the car is off it (`awaitingJoin`). The new line passes beside the
    car again 18.9 km on, at about 0 m off, against about 50 m to the line's
    start. So the first fix matches there.
  - That is *not* a tie: the far pass really is nearer. `travelled` jumps,
    `passedTurnaround` latches, and the next reroute goes home.
  - Suggested fix, not attempted: don't advance `travelled` or
    `trackTurnaround` from a match taken while `awaitingJoin` and off the
    line.
- **`018` (94%) and `019` (89%)** reroute once, via the far point. Presumably
  the replacement is shorter than the rest of the loop. Not checked.

### Point-to-point (582 drives each; overnight table → now)

| persona | arrivals | reroutes | banner behind (drives) | skipped | missing prompts | hard-fail drives |
|---|---|---|---|---|---|---|
| perfect | 582 → 582 | 0 → 0 | 26 (4) → **3 (3)** | 23 → **0** | 3 → 0 | 43 → 37 |
| dropout | 582 → 582 | 0 → 0 | 19 (3) → **3 (3)** | 23 → **0** | 3 → 0 | 10 → 3 |
| stopAndGo | 582 → 582 | 0 → 0 | 99 (4) → 3 (3) | 729 → 332 | 4 → 0 | 31 → 18 |
| earlyStop | 582 → 582 | 0 → 0 | 26 (4) → 3 (3) | 23 → 0 | 3 → 0 | 11 → 5 |
| noisy | 582 → 582 | 0.001 → 0.001/km | 99 (11) → 86 (8) | 365 → 324 | 34 → 27 | 33 → 28 |
| missedTurn | 543 → 543 | 0.023 → 0.023/km | 1104 (169) → 1078 (171) | 282 → 230 | 49 → 44 | 213 → 208 |

- **Dropout**, the persona trap 2 was about, is the cleanest. A gap in the
  fixes does not bring an old pass within 1 m of where the car is now, so no
  ceiling is needed, and `lastFixAt`/`Date()` was left alone.
- **The three behind events** in each persona are the same U-turn-apex fix as
  on the loops: `urban-011@1.0`, `coastal-002@0.5`, `parking-014@0.0`.
- **perfect's remaining hard fails** are 32 × "arrived on step N of N"
  (Finding 9) and two 1 m rises at the start.
- **stopAndGo's remaining 332 skips** are sharp corners where the persona
  dwells 4–8 m before the vertex.
- **earlyStop's "3 never arrived while parked"** is `urban-009` at every pref.
  It is identical on the base build.

### Finding 4, as a side effect

- `test_F4` (`coastal-002@0.5`) went red as an unexpected pass, so it is now
  a plain assertion.
- Mid-route U-turn and interchange skips are gone on perfect and dropout
  (23 → 0), including `urban-011`, `suburban-023`, `coastal-002` and
  `suburban-013@0.0`.
- What is left of Finding 4 is the one-fix apex lag above, and stopAndGo's
  corner dwell.

### Tests

- **Regression class:** F1, F2, F2b and F4 are now plain assertions and pass.
  F3, F5 and F6 are unchanged and still expected failures.
- **Default suite, no server:** 300 run / 267 passed / 33 skipped / 0 failed.
  - The base build on this branch is 291 / 258 / 33; the brief's 290/32 was
    one off.
  - The difference is exactly the 9 new `GeoTests`: identical passes, the
    start of a closed line, U-turn legs, the 1 m tie, the other carriageway,
    a long jump, the segment behind, just past a vertex, and outside a corner.
- **With the server:** LiveDriveTests 7/7; SimulatedDriveRegressionTests 7/7.
- **Real-trace replay:** every one of the 12 traces in the main checkout's
  `traces/` is identical to the base build on arrival, fixes fed, replies,
  same-line replies, every utterance, and describable fixes.
  - Measured with a scratch per-trace dump, not committed. Two intermediate
    versions of this fix failed that check, which is how attempts 3 and 4 in
    the table were found.
