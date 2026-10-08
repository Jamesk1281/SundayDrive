# Mid-drive recovery: what was built

**Status: built and simulated; not yet driven.** This is the record of
building the before-submission items of `docs/mid-drive-recovery-plan.md`
(sections 2, 3, 4 and 8.1–8.3) on one branch off `main` at `7ce5ef4`. The
plan holds the design and the measurements behind it. This file records what
was built, what this branch measured where it differs from the plan, and what
only a drive on the phone can show.

The server and `pipeline/` are unchanged. In `tools/`, one comment changed in
`analyze_trace.py`.

## What was built

Six changes, in one branch, because they all touch the same lines of
`NavigationModel.update` and `reroute`:

| # | change | where |
|---|---|---|
| 1 | **P-04, a failed reroute.** A failure is classified: the server's own "no" (`.server`) against a request that never landed (no connection, a refused one, a timeout, a 5xx, Cloudflare's 530, an undecodable reply). Network failures get their own counter, `consecutiveFailures`, which never touches the reroute backoff; a `.server` reply moves `consecutiveReroutes` as before. A failed request is retried when the network path comes back (`connectivityRestored`), otherwise at 15 s, 30 s, then every 60 s, and never on a timer while there is no path. The honest banners of plan section 2 (rows 2–6 and 10), and one spoken line per episode | `NavigationModel` (the "When a reroute fails" section, `reroute`, `noteFailure`, `switchToFastest`), `Connectivity.swift` (new: `NWPathMonitor`), `RouteModel.watchConnectivity`, `NavView.bannerText`, `VoiceGuide.announceRecovery` |
| 2 | **A trace record for every reroute attempt**, failures included (below) | `DriveTrace.reroute`, written from `NavigationModel.reroute` |
| 3 | **P-05, the wrong-way detector** of plan section 4.2: the car's course against the line's direction, armed only after 100 m of course-aligned progress, five votes and 40 m. When it fires, it reroutes at once with the heading, through the same `reroute` as any other, so the request carries `declined_uturn` when that is set and goes via the far point on a loop | `NavigationModel` ("Wrong way along the route", `trackWrongWay`), `Geo.passes`, `Geo.lineBearing`, `Geo.cumulativeLengths` |
| 4 | **The loop far-point cap** of plan section 4.4: `progress` takes a `notAfter` bound, the far point plus 25 m, until the far point has been passed | `Geo.progress(notAfter:)`, `NavigationModel.farPointCap`, passed in `update`, `reseatIfPinned`, the detector and the banner's distance |
| 5 | **Drive simulation Finding 2:** past 200 m it takes two far fixes in a row, not one | `NavigationModel.countOffRouteEvidence` |
| 6 | **Drive simulation Finding 3:** a fix counts toward the off-route streak only when `offRoute > 60 m + horizontalAccuracy`. A fix inside its own error bar neither builds the streak nor clears it | `NavigationModel.countOffRouteEvidence` |

### The owner's decisions, as built (plan section 8.3)

- **D2.** A loop turned back early on a road it drives twice is a wrong way
  ("Turn around when possible"), and the reroute goes via the far point. It
  is the cap that makes this so: the return pass lies beyond the far point,
  so the detector cannot read it as an aligned pass and the match cannot jump
  onto it, and `loopWaypoint` stays set.
- **D3.** "Turn around when possible." is said once per episode, on the fix
  that opens it. An episode ends when the replacement lands, the car turns
  round, or it leaves the line.
- **D4.** The distance is shown: "No signal · route 0.3 mi away". It says
  *away*, never *ahead*.
- **D5.** Not decided, so the camera is unchanged.

### The banner, row by row

In the plan's order, first match wins, after the two location-permission
states. Every row was rendered from the real `NavView`, with the mute button
showing, at 375 pt and 402 pt wide and at the largest Dynamic Type size.

| plan row | when | symbol | over | main |
|---|---|---|---|---|
| 1 | the detector has fired | `arrow.uturn.down` | Wrong way | Turn around when possible |
| 2 | …and the reroute failed | `arrow.uturn.down` | Wrong way · No signal / Wrong way · No connection | Turn around when possible |
| 3 | a reroute failed, no path | `antenna.radiowaves.left.and.right.slash` | No signal · route 0.3 mi away | Head back to your route |
| 4 | a reroute failed, with a path | `exclamationmark.icloud` | No connection · route 0.3 mi away | Head back to your route |
| 7 | a request in flight (unchanged) | `arrow.triangle.2.circlepath` | Off route | Finding a way back… |
| 5, 6 | off the line with no reroute in hand: in the backoff, handed the same line back, or the server said no (its message goes under the trip card for 6 s, row 5) | `arrow.uturn.backward` | Off route · route 0.3 mi away | Head back to your route |
| 10 | "Switch to fastest" failed with no connection | (no banner change) | | under the trip card: Can't switch — no connection. |

Four choices the plan left open, and what was built:

- **Rows 3 and 4 come before row 7.** A retry in flight after a failure keeps
  "No signal" or "No connection" on screen until a request lands. Otherwise
  the banner would flick to "Finding a way back…" for a fraction of a second
  on every retry with no path, or for up to 15 s on a weak signal, while the
  last thing known is still that the connection failed.
- **Row 6 needs the evidence a reroute needs.** It shows only when the
  off-route streak is full, the same `offRoute > 60 m + accuracy` evidence
  that makes a reroute due. Plain `offRoute > 60 m` would tell a car in canyon
  multipath, on its own road, to "Head back to your route". Rows 3–6 all
  share the plan's "more than 300 m from the end" rule (`noRerouteWithinMeters`).
- **"route 0.3 mi away" is held together with no-break spaces.** With the mute
  button beside it, "No connection · route 0.3 mi away" is too long for one
  line at 402 pt as well as at 375 pt, and it broke as "route 0.3 / mi away",
  the misreading the plan warned about. Now it breaks at the "·", so it reads
  "No connection ·" and then "route 0.3 mi away". The plan's render had no
  mute button, which is why it found only row 4 too long.
- **Dynamic Type does not reach the banner's words.** `Font.figure` is a fixed
  `.system(size:)`, so the largest size changes nothing but the mute button's
  glyph, which grows and narrows the text column. The words fit at the largest
  size too. Whether they should scale is a separate question.

### The voice

Two recovery lines, through `VoiceGuide.announceRecovery`. They are latched
like any announcement, so a muted voice stays silent and nothing is queued for
later:

- "Turn around when possible." Once, when the detector fires (D3).
- "No connection. Head back to your route." Once per episode, on the first
  failed request. An episode ends when a request lands or the car gets back
  within 30 m of the line. Nothing more is said while the car is going the
  wrong way (row 2): the turn-around line is still the instruction.

`routeAdopted` no longer cuts a recovery line short. That line is usually
what announced the reroute that is now landing. The replacement's own opening
still pre-empts it, as any new utterance does.

### The trace record

One `reroute` record per attempt, written when the attempt ends, after the
`route` record of a reply that was taken:

    {"t":"reroute","ts":…,"reason":"offroute"|"wrongway"|"fastest",
     "req_lat":…,"req_lon":…,"req_heading":…,"req_pref":…,
     "req_declined_uturn":true,"req_via":true,
     "outcome":"adopted"|"merged"|"failed"|"superseded"|"ended",
     "error_class":"server"|"busy"|"unreachable"|"timed_out"|"offline"|"bad_response"|"other",
     "status":530,"message":"…","path":true|false,"elapsed_s":0.021}

`req_heading`, `req_declined_uturn`, `req_via` and the failure fields appear
only when they apply. `elapsed_s` is what tells a failure with no path
(milliseconds) from a timeout (15 s); since K-1's fix a timeout is also its own
class, `timed_out`, where it used to be written as `offline`. `busy` (status
503) is the server refusing a loop build, which no reroute should ever see
(docs/loop-lock-contention.md). The detector firing is also marked
with `{"t":"phase","phase":"wrongway"}`.

An attempt the arrival ended is not written: `end` is the file's terminator,
and nothing is appended after it, as with `phase`.

`tools/analyze_trace.py` does not read the new type. Every reader there, and
`tools/trace_excursions.py`, `tools/replay_uturn.py` and
`ios/Tests/DriveReplay.swift`, selects records by type, so an unknown type is
skipped. `test_a_record_type_the_analysis_does_not_read_changes_nothing`
(`tests/test_trace.py`) holds that, and
`test_the_recorded_fields_are_the_ones_the_analysis_reads`
(`ios/Tests/DriveTraceTests.swift`) now writes a `reroute` record too and
lists the type as written but not read.

## What it measured

Everything below compares a scratch copy of `7ce5ef4` with the personas patch
applied (the baseline) against this branch, on the same simulator runtime
against the same local server on `data/processed-ne`. The routes are a
60-route sample at pref 0.5 (see Reproducing). It is not the plan's sample,
so the baseline counts differ from the plan's tables while showing the same
pattern. The loops are the 20 committed ones. The six 150–400 km loops were
not run.

### Routes

| persona | drives | reroute requests | wrong-way alarms off a reversal | banner behind the car | missed prompts |
|---|---|---|---|---|---|
| `perfect` | 60 | 0 → 0 | 0 | 1 → 1 | 0 → 0 |
| `noisy` | 60 | 0 → 0 | 0 | 0 → 0 | 2 → 2 |
| `missedTurn` | 57 | 58 → 58 | 2, both real (below) | 127 → 132 | 4 → 5 |
| `wrongWayStart` | 51 | 51 → 51 | 0 | 71 → 67 | 2 → 2 |
| `spike` | 60 | **887 → 25** | 0 | **975 → 8** | **67 → 8** |
| `canyon` | 60 | **364 → 1** | 0 | **211 → 38** | **17 → 3** |

Spikes and canyon multipath land where the drive simulation's Findings 2 and
3 said they would (1,468 → 20 and 310 → 0 in that report's sample). Their
adoptions went from 735 to 12 and from 265 to 1.

**Driving the wrong way along the route** (`wrongWayAlong`, 59 reversals):

| | baseline | branch |
|---|---|---|
| a reroute requested while driving back | 1 of 59, after 46 s and 552 m | **59 of 59**, on the detecting fix |
| detected after | — | a median **4 s and 48 m** |
| "Turn around when possible." | never | exactly once on every drive |

The plan measured 4–5 s and 48–60 m. The replacement's own opening was then
driven through unspoken on 50 of 58 routes (the plan: 48 of 56). That is
overnight Finding 3, still open, as the plan says.

The two alarms off a reversal, both traced fix by fix:

- `rural-013` is the plan's known case: a missed right turn onto the stretch
  the route had just come up. A wrong way by any definition.
- `rural-007` is new to this sample, and real too. The harness staged its
  missed turn with a detour that opens by turning round at the junction and
  driving back down the route itself: the fixes sit 0 m off the line while
  the position along it falls from 920 m to 824 m. The detector fired five
  fixes in. The same staging put `cross-025` into `serverDown` and
  `deadZone` (its remaining distance grows while the car stays on the line),
  so each of those has one detection as well.

**A failed reroute**, a 180 s outage starting at a missed turn onto a 1.5–3 km
road:

| | baseline | branch |
|---|---|---|
| `serverDown` (HTTP 530, a path present), 57 drives: recovery after the server returns | median **64 s**, max 80 s (53 recovered by a request) | median **53 s**, max 57 s (53) |
| `deadZone` (no path, then the path returns), 57 drives | the same as `serverDown`: the baseline cannot tell them apart | **the first fix after the path returned**, on 55; the other 2 were back on their line first |
| requests during the outage | median 4 | 5 (`serverDown`, about 11, 26, 56, 116 and 176 s in); 1 (`deadZone`) |
| banner during the outage | the abandoned line's next maneuver | "No connection · route … away" or "No signal · route … away", "Head back to your route" |
| spoken during the outage | nothing | "No connection. Head back to your route." once, on every drive but `cross-025`, which was going the wrong way at the time (row 2: nothing more said) |

The plan's prototype measured a median 58 s on `serverDown`. Both are the
cadence's own phase: after a 180 s outage the sixth try falls about a minute
after the fifth, 236 s in here, and the rest is this sample. For an outage of
any length the wait is at most 60 s.

On `serverDown` the banner-behind count went from 86 to 1,281, all but 29 of
them on one drive, `parking-005`. Traced, the model is right there: every
step advances, every maneuver is spoken in time, and the remaining distance
matches the truth to within 20 m. That drive's replacement route passes the
same junction twice, and the harness places those steps on the earlier pass,
so it counts the car as past them. Without that drive it is 29 against 86, on
9 drives against 13.

### Loops

| persona | loops (km planned) | baseline: km driven | baseline: under half way | branch: km driven | branch: under half way |
|---|---|---|---|---|---|
| `loopPerfect` | 20 (886) | 884 | 0 | 884 | 0 |
| `loopEarly` | 17 (774) | 721 (93.1%) | 1 | **771 (99.5%)** | 0 |
| `loopMild`, real-trace noise | 20 (886) | 768 (86.7%) | 3 | **884 (99.8%)** | 0 |
| `loopSpike` | 20 (886) | 305 (34.5%) | 14 | **882 (99.5%)** | 0 |
| `loopCanyon` | 20 (886) | 456 (51.5%) | 9 | **884 (99.8%)** | 0 |

The plan's spike figure with the cap was 101%, because its one-fix rule still
added a detour per spike. With two fixes, spike requests on loops went from
98 to 10, and canyon requests from 60 to 0.

| | baseline | branch |
|---|---|---|
| `loopWrongWay` (20): a reroute while driving back | 2 of 20 | **20 of 20**, a median 5 s and 60 m, via the far point |
| `loopWrongWay`: came home more than 3 km short | 2 (`loop-001` 19.1 of 30.1 km, `loop-004` 34.0 of 56.7 km: the plan's two) | 1: `loop-019`, 76.3 of 84.6 km, whose replacement through the far point takes a shorter way home (the plan's footnote) |
| `loopServerDown` (15): recovery | median 64 s, max 80 s | median 53 s, max 58 s |
| `loopServerDown`: more than 3 km short | 6 | 1 (`loop-009`, 45.9 of 49 km) |
| `loopDeadZone` (15): recovery | — | the first fix after the path returned, on all 15 |

Missed prompts rose on the loop personas that now reroute where they did not
before: `loopWrongWay` 19 → 63, `loopServerDown` 24 → 50. About a third are
replacement openings driven through unspoken (`loopWrongWay` 0 → 14), which
is overnight Finding 3. Traced on `loop-004` (0 → 10), every maneuver of the
replacement was spoken before the car reached it. So the rest of the count
is the harness's bookkeeping for a replacement line, not what the voice
said. It was not traced further.

### The recorded drives, replayed

All 18 traces, before and after (`ReplayDumpTests`, the recorded replacement
routes handed out in order). **11 replay identically. The other 7 differ, all
explained.** 584 utterances before, 587 after.

| trace | what changed | why |
|---|---|---|
| `2026-08-14-192546` | two requests 1 s later (of 12); one prepare said one fix later, so "In 900 feet" became "In 800 feet" | Finding 3: the fixes before them were 60 m to 60 m + accuracy off |
| `2026-08-22-183419`, `2026-08-22-202700`, `2026-10-06-185940` | one request 1 s later | Finding 3, the same |
| `2026-10-06-161415` | its one request 2 s later | Finding 3: by the recorded offsets, two fixes 61 m and 65 m off at a stated 5 m no longer count |
| `2026-10-06-164801` | its one request 1 s later, and two more utterances: the replacement's opening and its U-turn prepare, which the reply now lands in time to say | Finding 3, and then overnight Finding 3 in the drive's favour |
| `2026-10-06-122558` | requests shifted by 1 s (and one by 5 s), and one new line, "Turn around when possible.", 9204 s in, 7 s before the baseline's off-route request there | Finding 3. For the 5 s, the car ran 60–65 m off its line at a stated 4 m for 8 s before really leaving it. The wrong-way line is real: the car turned about 200 degrees on its line and drove back along it for about 100 m before leaving it |

`2026-10-06-192759`, the P-05 drive, replays identically in order, and that
was a finding about the replay, not the detector. The car leaves its line just
before the wrong-way run. The replay answers that request with the next
recorded route, one the drive was given 40 minutes later somewhere else, and
then follows the wrong line. On the road nothing landed until then, so those
requests failed: P-04. `DriveReplay.Mode.asRecorded` replays that: a request
gets the next recorded route only from 30 s before it really landed, and fails
before that. Replayed that way, the drive says "No connection. Head back to
your route." when the first request fails, at 9218 s. It says "Turn around
when possible." at 9288 s, 14 s after the first fix of the run against the
line, whose first few fixes were at a crawl the detector does not read. It
says "No connection" again, a new episode, when the car leaves the line at
9494 s. `RecordedWrongWayTests` holds that, within 20 s of the run's start.

In that mode across all 18 traces, the detector fires on two drives:
`122558` (above) and `192759`, both real. "No connection" is said on
`192759` and `2026-08-22-222623`, whose recorded requests did not all land
either.

**The known replay failure.**
`DriveReplayTests.test_no_recorded_drive_hears_the_same_maneuver_twice` fails
on `drive-2026-10-06-122558` as it does on `main`. The same maneuver is still
said twice running, and the utterance count moves from 148 to 149 (over a
limit of 120). The extra one is the wrong-way line above. The limit was not
touched.

### The suites

- **iOS**, the full `xcodebuild test` with no server, on a simulator made for
  this: **424 executed, 378 passed, 45 skipped, 1 failed** (the replay test
  above). Baseline on `7ce5ef4`: 385, 351, 33, 1. The difference is 26 tests in
  `MidDriveRecoveryTests`, one in `RecordedWrongWayTests` (both passing), and 12
  skips: the 11 new persona tests and `ReplayDumpTests`, which run only when
  asked.
- **Backend**, `pytest tests/` on `data/processed-ne`: **653 passed** (652 on
  `7ce5ef4`, plus the new trace-reader test).

### Tests that moved with the rules

Forty-seven existing tests failed on the first run of the branch, as the plan
expected. They reached a reroute through one teleported fix, or (the
declined-U-turn tests) left a route by driving past its end in one fix. Each now
sends the second fix, through a commented helper where the file has one
(`RerouteTests.offRoute`, `LoopRerouteTests.goOffRoute`,
`DeclinedUTurnTests.leave` and `declineAUTurn`). One insertion was taken back:
in `test_a_driver_who_keeps_ignoring_the_route_is_asked_less_often` the streak
was already full, so an extra fix started a second request before the first
one's task had run, which back-to-back `update` calls allow and 1 Hz fixes
do not. Two failure-path tests describe the old rule and still pass; their
wording now says what the rule is:
`RerouteTests.test_a_failed_reroute_is_not_retried_on_every_fix`, and
`RerouteIdentityTests.test_a_reroute_that_never_lands_is_not_asked_straight_back`
(renamed from `…still_costs_an_interval`).

New tests (`MidDriveRecoveryTests`, `RecordedWrongWayTests`): each failure
lands in its banner row; the server's no under the trip card; network
failures never climb the backoff and a server's no does, even with the path
monitor saying no path; no timer retry without a path, and one on the first
fix after it returns, even from a parked car; 15, 30, 60, 60 s with a path;
a returned path that carries nothing falls back to the timer; "No
connection" once per episode; a failed "fastest" says so and changes nothing
else; a trace record for every outcome, failures included, and nothing after
`end`; two fixes past 200 m; a fix inside its error bar; the detector firing
on the fifth fix and asking at once with the heading; its banner with and
without a failure, said once; the replacement ending it; not before 100 m;
not below 3 m/s or above 30 m; a spike resetting it; a U-turn replacement
not firing it, with the decline going out as an ordinary off-route reroute;
the wrong-way reroute sending `declined_uturn`; on a loop, firing before the
far point and rerouting via it, silent on the return pass, and the cap
keeping the match short of the far point; a recovery line not cut short by
the route it announced; the real P-05 run.

### Two things noticed, not changed

- **A parallel return carriageway can take the match.** On a route that leads
  ahead and turns round onto a carriageway 15 m beside the outbound one, a car
  reversing more than 100 m past the backtrack floor is matched onto the return
  carriageway, which reads as having driven the route and clears
  `declinedUTurn`. It predates this work. The detector fires before that
  point, which is why its test stops there.
- **Back-to-back `update` calls can start two reroutes.** `isRerouting` is set
  inside the reroute's task, so two fixes delivered before that task runs both
  pass the guard. At 1 Hz from CoreLocation it does not happen; in a test it
  can.

## On the phone: the owner's test-drive checklist

The simulator reaches the network through the Mac and fails open on
background policy, so none of the following has been exercised (plan,
section 10). Nothing here claims them. With a Debug build, which records,
each check leaves `reroute` records in the trace to read afterwards.

1. **Airplane Mode, off the route.** Leave the route on purpose, then switch
   Airplane Mode on. Expect "No signal · route … away / Head back to your
   route", and "No connection. Head back to your route." said once. Switch it
   off: a reroute should land on the next fix. In the trace, the failures
   show `error_class: offline`, `path: false`, and an `elapsed_s` of
   milliseconds.
2. **Network Link Conditioner, 100% loss** (a path that exists and carries
   nothing). Expect "No connection · route … away", retries about 15 s, 30 s,
   then 60 s apart, and each failure ending in the 15 s timeout
   (`elapsed_s` about 15). This is the case where "Finding a way back…" never
   shows: rows 3 and 4 are held through a retry.
3. **The same, locked, in a pocket.** Does the `NWPathMonitor` callback arrive
   in the background on location, and is the recovery line spoken? Method:
   `docs/voice-guidance-plan.md` section 1.
4. **The wrong way, on purpose,** on a quiet road the route follows: drive it
   for a few hundred metres, turn round safely and drive back along it.
   Expect "Turn around when possible." within about 5 s and 60 m, said once,
   the banner "Wrong way", and a reroute requested on the same fix
   (`reason: wrongway`). Then do it in a dead zone, which should give "Wrong
   way · No signal" with nothing more said.
5. **On a loop,** turn back before the far point on a road the loop drives
   twice. Expect the same, with the reroute going via the far point
   (`req_via: true`) and the loop kept.
6. **"Switch to fastest" in a dead zone.** Expect "Can't switch — no
   connection." under the trip card, and nothing else changed.
7. **Largest text.** Settings › Accessibility › Display & Text Size › Larger
   Text at its maximum, then look at an off-route banner on the phone itself.

## Reproducing

`<main>` is the main checkout, which holds `data/`, `traces/` and `.venv`.

    # the iOS suite, with no server, on a simulator you made yourself
    cd ios && xcodegen generate
    xcodebuild test -project SundayDrive.xcodeproj -scheme SundayDrive \
      -destination 'id=<your simulator>'

    # the backend suite
    SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python -m pytest tests/

    # a local server, for the personas; stop that PID only
    PORT=<free port> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<main>/data/processed-ne \
      <main>/.venv/bin/python server/serve.py &

    # the personas (after build-for-testing)
    TEST_RUNNER_SUNDAYDRIVE_E2E=1 TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:<port> \
    TEST_RUNNER_SUNDAYDRIVE_E2E_OUT=<out> TEST_RUNNER_SUNDAYDRIVE_E2E_ONLY=<keys> \
      xcodebuild test-without-building … \
      -only-testing:SundayDriveTests/SimulatedDriveTests/test_12_wrongWayAlong

    # the replay dump, in order or as recorded
    TEST_RUNNER_SUNDAYDRIVE_REPLAY_OUT=<file> [TEST_RUNNER_SUNDAYDRIVE_REPLAY_MODE=asRecorded] \
      xcodebuild test-without-building … -only-testing:SundayDriveTests/ReplayDumpTests

The persona tests are `test_12_wrongWayAlong` to `test_22_loopDeadZone`. The
key lists: a 60-route sample at pref 0.5, ten per category (urban, suburban,
rural, cross, parking, coastal), drawn with
`random.Random(20261005).sample` from each category's sorted ids, leaving out
`suburban-005`, which the server refuses; and the 20 committed loops. The
baseline is a scratch copy of `7ce5ef4` with `tools/mid_drive_personas.patch`
applied, its `serverDown` changed to fail with HTTP 530 as here.

