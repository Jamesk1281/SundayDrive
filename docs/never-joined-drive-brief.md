# Brief: a drive that never joins its route can never end (release-plan §6d)

**Status: fixed 2026-09-29** on branch `claude/never-joined-stall`, as decided
below: `NavigationModel.stalled`, `StalledView`, and a replay assertion over all
twelve traces. What follows is the brief as written, against `main` at
`4ef3e11`. Line numbers are from that commit, and each comes with its anchor
text.

Answers `docs/roadmap.md` ("A drive that never joins its route can never
end") and the first half of `docs/release-plan.md` §6d. The second half of
§6d, the opening camera, shipped with the redesign.

---

## 1. The defect, as measured

`NavigationModel` ends a drive in exactly one automatic way: latching
`arrived` (`NavigationModel.swift:54`, `private(set) var arrived = false`).
That is what releases the hardware. `NavView.swift:105`,
`.onChange(of: nav.arrived)`, calls `locationManager.stop()` and clears
`isIdleTimerDisabled`. All three arrival tests require `hasJoinedRoute`
(`:857`, `:858`, `:865`):

```swift
let drivenTheLine = hasJoinedRoute && here.remaining < Self.arrivalMeters
let stoppedAtThePin = hasJoinedRoute && ...
let parkedAtTheEnd = hasJoinedRoute && here.remaining < Self.arrivalTailMeters && parkedLongEnough
```

`hasJoinedRoute` (`:78`) latches true only when a fix lands within
`offRouteMeters` (60 m) of the line (`:833-835`), or by hand when a reroute is
adopted (`:1301`). So a car that never comes within 60 m of the line, and never
reroutes, holds GPS at 1 Hz with background location on and the screen awake
until someone comes back to the phone.

**Measured over all twelve traces in `traces/` (main checkout, gitignored):**

| | drives |
| --- | --- |
| joined on the first fix | 9 |
| joined later, after 0.2 min / 0.6 min / 3.5 min | 3 |
| **never joined** | **1**: `drive-2026-08-25-222344` |

- **The longest legitimate pre-join stretch is 3.5 min**, in
  `2026-08-22-222623`. The car was *moving*: 1.3 km displacement, up to 593 m
  off the line. That is the pre-join abandon case `armedForReroute` (`:382`)
  now handles.
- **The never-joined drive**: 523 fixes over 8.7 min, with no `end` record
  (the app was killed). The car was **parked**: maximum displacement 40 m from
  the first fix, and 116–156 m off the line throughout. It is the phantom
  drive in `docs/archive/stale-plan-after-arrival.md`: a Harvard→Needham plan
  restarted by a stale button while the car sat at the Needham end, **176 m
  from the destination pin**, with `remaining: 0` on the first fix. The stale
  button is fixed. The gate that let it run forever is not. Any parked car
  more than 60 m from a line it has not reached reproduces this, for example
  from a driveway or car park set back from the road the route snapped to.

## 2. The fix, decided

**A second, non-arrival ending: the drive *stalls*.** Add a latch next to
`arrived` (name it; `stalled` is fine) that fires when all of these hold:

1. `!hasJoinedRoute`, and
2. the car has stayed within **50 m** of an anchor fix for **5 minutes**. When
   a fix lands more than 50 m from the anchor, re-anchor on it and restart the
   clock. **This is a displacement rule, not the speed rule.** See trap 1.

When it fires:

- **Release the hardware exactly as arrival does**: stop location and clear
  the idle-timer override. Mirror `NavView.swift:105`'s `onChange` for the new
  latch.
- **Show a card, not the arrival card.** Suggested wording, in the redesign's
  voice (`Theme.swift`, and `ArrivalView.swift` for shape): "Navigation paused.
  You haven't reached the route yet." Two actions: **Keep navigating**, which
  restarts location, clears the latch and resets the anchor, and **End
  drive**, which is the existing `onEnd` path. Keep it within the reserved
  bottom strip: `Metric.appleKeep` is load-bearing for Apple's logo.
- **Trace:** record the stall and any resume as records the analysis can see
  (`tools/analyze_trace.py:86` schemas `phase` as `{t, ts, phase}` and `:1005`
  filters it to `background`/`inactive`, so a new phase name looks safe. Confirm
  that before choosing between reusing `phase("stalled")`/`phase("resumed")` and adding a
  record type). An End after a stall ends with `finish(reason: "never-joined")`
  so the ending is distinguishable from "ended" and "arrived".
- **`recordingProblem` (`:674`) must go quiet while stalled.** It already does
  for `arrived` (`:678`, `guard !arrived else { return nil }`). Without that,
  the watchdog turns the paused screen into "No GPS fixes for 40 s — nothing is
  being recorded", which is false and alarming.

Why 5 minutes and 50 m: every real pre-join stretch is at most 3.5 min and
moving. The phantom stayed within 40 m for 8.7 min, and 30 m is too tight (its
longest still stretch at 30 m is 4.3 min). A false stall costs one tap on
*Keep navigating*. A missed one costs a battery.

## 3. Traps

1. **Building the timer on `parkedLongEnough`.** `trackStopping` (`:144`)
   resets whenever one fix reads ≥ 1.0 m/s. On the phantom, a car that did not
   move, GPS speed crossed 1.0 m/s **11 times in 8.7 minutes**, so the longest
   run that rule ever saw was **203 s**. A 5-minute timer on it **never fires on
   the one real case**, and every synthetic test with clean zero speeds would
   pass. That rule is fine for its own 90-second job near the end of a joined
   route. Use displacement here, and replay the real trace (Done item 3).
2. **Clearing `hasJoinedRoute`, or setting `arrived`, to get the drive to
   end.** `hasJoinedRoute` also gates the backtrack floor (`:809`) and
   off-route recovery (`armedForReroute`, `:382`). Three documents already warn
   off touching it. `arrived` is worse: it shows the arrival card, announces
   arrival by voice, and never un-latches (`:804`). A drive that never set off
   must not say "You've arrived".
3. **An "arrived near the pin, even if unjoined" rule.** It is the obvious
   reading of the roadmap's "an arrival path that does not depend on having
   joined", and it is **deliberately not in scope**. The one measured never-joined
   car was parked 176 m from its own destination pin. A "parked within 250 m
   of the pin" rule would have announced arrival on a drive that never
   happened, and a loop's destination is its own start, so every parked loop
   would arrive instantly. No trace contains a car that drove to its
   destination without ever joining. After a reroute `hasJoinedRoute` is set
   by hand (`:1301`), so that needs reroutes to fail for a whole drive. The
   stall path ends that case too, just with the wrong copy, which is acceptable
   for a case never observed.
4. **Applying the stall to joined drives.** A joined car parked mid-route at a
   scenic overlook for ten minutes is the product working. Whether a long
   *joined* stop should also pause is an owner decision, and it is not made.
   Gate strictly on `!hasJoinedRoute`.
5. **A test that sets the latch state by hand proves nothing.** Drive it
   through `update(_:)` with fixes and an injected clock. `now` is already a
   settable `var now: () -> Date` (`NavigationModel.swift:192`).

## 4. Done looks like

1. The stall latch, the card with *Keep navigating* / *End drive*, the hardware
   release, the silenced `recordingProblem` and the trace records, all as in §2.
2. **Unit tests in `NavigationModelTests.swift`**, driven through `update(_:)`:
   an unjoined car still for 5 min stalls, and one still for 4 min 50 s does
   not. An unjoined car whose GPS speed jitters above 1.0 m/s while staying
   within 50 m still stalls (trap 1, as a value). A car creeping 60 m every
   2 min does not. A **joined** car parked 10 min mid-route does not (trap 4).
   *Keep navigating* re-arms a fresh 5-minute clock.
3. **A replay assertion in `DriveReplayTests`** over the real traces:
   `drive-2026-08-25-222344` stalls, at about 5 min, and the other eleven end
   exactly as they do today, with no stall anywhere. Traces are gitignored, so
   the test must skip cleanly without them, as the existing replay tests do.
4. `docs/roadmap.md` and `docs/release-plan.md` §6d marked done, pointing at
   this brief. §3 trap 3 and trap 4 recorded there as deliberate exclusions,
   not oversights.
5. iOS suite green against the baseline, plus the new tests. The baseline is
   **261 tests, 254 passed, 7 skipped (LiveDriveTests), 0 failures** after the
   POST change. Re-measure on `main` before you start, rather than trusting this line.

Out of scope: unjoined *arrival* (trap 3), stalls on joined drives (trap 4),
and any change to `hasJoinedRoute`, `arrivalMeters`, `arrivalTailMeters` or
`parkedLongEnough`.
