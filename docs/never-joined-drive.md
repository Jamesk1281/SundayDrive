# A drive that never joined its route could never end

**Status:** shipped — merged to `main` by `a2ddddc`. This is the part of the dispatch brief that outlived the work: its measurements, decisions and results. The brief itself, with its traps and done-list, was deleted on merge — `git show a2ddddc:docs/never-joined-drive-brief.md` prints it. Section numbers and "below" refer to that brief's layout.

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
