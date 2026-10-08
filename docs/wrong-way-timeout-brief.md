# Brief: item 3b (the wrong-way time-out) and decision D9

**Status: diagnosed and decided, not built.** Written 2026-10-08 against
`main` at `cdc090f`. Nothing in `ios/`, `server/` or `pipeline/` has been
touched. **This brief is temporary. The merge that brings the work back
deletes it** (see `docs/briefs.md`). Results go into
`docs/mid-drive-recovery.md`, in a new section, and into the code and tests.
They never go into this file, and no comment or test may cite it.

## 1. The goal

This is item 3b of `docs/mid-drive-recovery-plan.md` §8.1 (designed in
§4.6, points 1 and 2), plus the owner's answer to D9. It is the last
before-submission item of the mid-drive recovery work. Items 1–4, 6 and 7
are built and merged (`c97b126`, recorded in `docs/mid-drive-recovery.md`).

**D9 is decided: (a). The wording does not change.** The banner stays
**Wrong way · Turn around when possible**, and the spoken
"Turn around when possible." is still said once (D3). The owner chose this
on 2026-10-08. For D9 the build only records the decision:
- In the plan's §8.3 D9 row, append **Decided 2026-10-08: (a)**.
- In the plan's status line, "D5 and the new D9 are open" becomes "D5 is open".
- Cite D9 at the announcement in `trackWrongWay`.

**3b has two halves:**

1. **The time-out.** A wrong-way episode that has gone on for **30 s, or
   300 m of further reversal along the line, whichever comes first** (both
   counted from the detecting fix) stops showing "Wrong way · Turn around when
   possible". It gives way to the off-route state:
   - "Off route · route 0.3 mi away / Head back to your route", or
   - its No signal / No connection row when the last request failed (plan
     §2, rows 3–6).

   Meanwhile the reroute keeps retrying as §3 says. Both thresholds are a
   judgement from two real drives, not a measurement, and the code comment
   must say so.
2. **One line, not two.** If the wrong-way request is going to fail on the
   fix that detected the reversal, the spoken line is the failure version,
   **"No connection. Turn around when possible."**, instead of
   "Turn around when possible." It must not be said in addition (plan §4.3,
   the prototype's fault).

### The measured case it exists for

There are two real reversals on record (plan §4.6).

- **`drive-2026-10-06-192759` (§1.5).** The driver turned back from a road
  that could not be driven, drove **1,932 m back along the line over
  196 s**, then took a detour. Every request in that stretch failed.
  - Today's build detects the reversal at 9 s and 45 m. It then holds
    **Wrong way · Turn around when possible** for the whole 196 s,
    instructing a driver who has decided not to turn round.
  - With 3b, it switches after about 30 s.
- **`drive-2026-10-06-122558`, a deliberate U-turn.** The car left the line
  85 m after turning, so it never reaches either threshold. **3b must change
  nothing on this drive.**

## 2. The mechanism, and why "just clear `wrongWay` after 30 s" is wrong

All references are to `cdc090f`.

- **`wrongWay` is one flag doing three jobs.** It is set in
  `trackWrongWay` (`ios/Sources/NavigationModel.swift:779`) and cleared by
  `resetWrongWay` (`:788`), which runs when:
  - the car turns round (an aligned pass, `:762-765`),
  - the car leaves the line (`:760`), or
  - a replacement is adopted (`:2058`).

  It is read by three things:
  - **the banner:** `NavView.bannerText` (`ios/Sources/NavView.swift:278-289`),
    first match after the permission rows;
  - **the reroute trigger** in `update`
    (`NavigationModel.swift:1418-1427`), where `offRouteDue || wrongWay`
    is what makes a request due at all;
  - **the failure voice:** `noteFailure`'s `guard !wrongWay,
    !announcedLostConnection` (`:1957`), which keeps the failure line from
    following the turn-around line. `trackLostConnection` (`:622`) also
    refuses to end a failure episode while `wrongWay`.
- **The car is *on* its line the whole time it reverses.** `reseatIfPinned`
  (`:1503-1517`, window `reseatWindowMeters = 500` at `:251`) walks
  `travelled` back with the car. So `here.offRoute` stays near 0,
  `countOffRouteEvidence` (`:1442`) never builds a streak, `offRouteDue` is
  false, and `isOffTheLine` (`:627-631`) is false. That is the whole reason
  P-05 needed a detector.
- **`distanceToLine` is measured from `travelled`.** It is refreshed in
  `update` (`:1394-1398`) to the line no more than 300 m behind `travelled`.
  Because `travelled` follows the reversing car, this is **about 0 m**.
- **The detector keeps voting after it fires.** `wrongWayVotes` and
  `wrongWayBackMeters` keep accumulating (`:772-776`). The `guard !wrongWay`
  at `:777` only stops it re-firing. So "300 m further back" is available as
  `wrongWayBackMeters` minus its value at detection. Check that its ±60 m
  per-fix clamp is acceptable, or keep a separate odometer.

## 3. What to build

The shape is yours. These are the behaviours:

1. **Split "the episode is open" from "the wrong-way banner shows".** Keep an
   episode flag that holds through the time-out. It must still:
   - make the reroute due (the trigger at `:1418-1427`),
   - keep `trackLostConnection` from ending a failure episode while the
     car is still reversing on the line, and
   - stop the detector re-firing and re-speaking.

   A second, derived state says whether the 30 s / 300 m has passed. The
   banner shows the wrong-way row only before that. The episode still ends
   exactly as today: the car turns round, leaves the line, or a replacement
   is adopted. Keep `nav.wrongWay` meaning "the wrong-way banner applies" if
   that keeps the existing tests readable, or rename it and update them;
   either is fine.
2. **After the time-out, show the off-route row with an honest distance.**
   - "route X away" must be measured to the part of the route **still to
     drive**: the line at or after where the reversal began (for example
     `progress(of:along:notBefore: <turn-back along>, notAfter: farPointCap,
     near:)`), not to the line under the car.
   - Record the turn-back point when the run starts. That is the match of
     its first vote, or `travelled` at detection plus the back metres
     accumulated so far.
   - It still says *away*, never *ahead* (D4).
   - With a failure in hand, show rows 3/4 ("No signal ·" / "No connection ·").
   - Without one, show "Off route · … / Head back to your route" (the
     `isOffTheLine` row, `arrow.uturn.backward`). Whichever way you do it,
     the banner must not fall through to the abandoned route's next maneuver.
     That fallthrough was P-05 itself.
3. **The give-way is silent.** D3 still holds: one "Turn around" per
   episode. A failure that happens *after* the give-way and has not yet been
   announced in this episode may be announced with the ordinary
   "No connection. Head back to your route." This is the build's judgement,
   not the plan's. Say so in `docs/mid-drive-recovery.md` so the owner can
   veto it.
4. **"One line, not two."** If `networkReachable()` is false on the
   detecting fix, the request will fail offline in milliseconds. In that
   case:
   - speak "No connection. Turn around when possible." instead of the plain
     line;
   - set `announcedLostConnection`, so the episode's failure has been said;
   - do this whether or not the reroute actually fires on that fix (it may
     be held by `rerouteDue`).

   With a path, keep today's behaviour: the plain line now, and a later
   failure stays silent while the wrong-way banner shows.
5. **The reroute after the time-out keeps `reason: "wrongway"`.** It goes
   through the unchanged `reroute`. **Do not** set or send `declined_uturn`
   on account of the time-out (§4 trap 3).
6. **Tests**, in `ios/Tests/MidDriveRecoveryTests.swift`, with the existing
   fixtures (`drive(nav, from:to:)`, `Backend`, `path`, the `now()` seam):
   - Gives way at 300 m, with no failure and with each failure class.
   - Gives way at 30 s, crawling so that 300 m is not reached first.
   - Does not give way at 85 m / 7 s (the real U-turn's shape).
   - After the give-way, retries continue at 15/30/60 s, the detector does
     not re-fire or re-speak, and turning round ends the episode.
   - The distance after give-way grows as the car keeps reversing, and is
     not ~0.
   - The no-path detection says exactly one line, the failure version.
   - The with-path detection says exactly "Turn around when possible." once.
   - A replacement landing after the give-way ends the episode.
   - The loop case (detector before the far point, D2) gives way the same
     way, and the reroute still goes via the far point.
7. **Replays.**
   - Run `RecordedWrongWayTests` and `ReplayDumpTests`, in order and
     `asRecorded`, against `main` and against the branch.
   - The twelve August drives and the four October drives with no reversal
     must stay identical, utterance for utterance.
   - On `192759`, report when the give-way happens and what the banner says
     after it.
   - On `122558`, nothing may change.
8. **Docs.**
   - Add a section to `docs/mid-drive-recovery.md`: what was built, what was
     measured, and the item-3 judgement above.
   - In the plan's §8.1, mark item 3b built.
   - Record D9 in the plan (§1 above).
   - Update the phone checklist in `docs/mid-drive-recovery.md` (items 4 and
     5): expect the banner to change to the off-route row after 30 s if you
     keep going.

## 4. Traps

1. **Clearing `wrongWay` at the time-out silently stops the reroute.** The
   trigger is `offRouteDue || wrongWay`, and `offRouteDue` is false on the
   line (§2). Clear the flag and nothing asks again until the car leaves the
   line. On `192759` that was 196 s. The detector would also re-arm and fire
   "Turn around" a second time a few fixes later, breaking D3. Keep the
   episode; change only what the banner shows.
2. **The obvious distance is ~0 and reads as nonsense.** `distanceToLine`
   follows `travelled`, which `reseatIfPinned` walks back with the car. So
   the obvious rendering is "No signal · route 0 ft away / Head back to your
   route" to a car sitting on its route. Measure to the route still ahead of
   the turn-back point (§3 item 2), and test that the number grows.
3. **Don't send `declined_uturn` because of the time-out.** The plan (§4.6
   point 3) says the wrong-way reroute composes with the existing rule
   (`docs/reroute-uturn.md`) without new code. The first reply turns the
   driver round; a driver who keeps going leaves it, and the next request
   keeps ahead. That composition is already tested
   (`test_the_wrong_way_reroute_sends_declined_uturn_when_set`). Changing it
   is a product decision that has not been made.
4. **Don't hold the turn-around line until the request resolves.** Waiting
   for the reply to choose between the plain and the failure line looks
   neater. But when the reply *succeeds*, the replacement's opening
   instruction is usually not spoken (overnight Finding 3: 50 of 58 routes,
   `docs/mid-drive-recovery.md`). The driver would then hear nothing at all.
   Decide on the detecting fix from `networkReachable()`.
5. **The test instruments count the wrong-way line by exact string.** These
   are `DriveReplay.wrongWayLine` / `wrongWayAt` (`ios/Tests/DriveReplay.swift:215-224`),
   `SimulatedDrive.swift:301`, and `turnAroundSaid` in
   `MidDriveRecoveryTests.swift:136`. With the failure version, a detection
   in a dead zone vanishes from all three, and the assertions on counts
   still pass by accident. Make them count both strings, or count the trace's
   `{"t":"phase","phase":"wrongway"}` record.
6. **An existing test encodes the old behaviour, and it should change.**
   `test_the_wrong_way_banner_and_its_failures` (`MidDriveRecoveryTests.swift:479`)
   drives 495 m further back and asserts the wrong-way banner is still up,
   with `noConnectionSaid == 0` in the no-path case. Both change on purpose.
   Update the test and say why in the commit. Don't weaken it to pass.
7. **Don't trust a conflict-free merge.** A parallel session (spliced route
   options, `claude/keen-yonath-de1e89`) will rewrite
   `NavigationModel.reroute` to reroute by legs. Stay out of `reroute`,
   `switchToFastest` and `noteFailure`'s `.server` branch. Whichever branch
   merges second must rerun `MidDriveRecoveryTests` and
   `RecordedWrongWayTests` after the merge, not just before it.

## 5. Build and test

- Work on a branch off `main`, never on `main`. This brief may be untracked
  in the master worktree; copy it into yours and commit it with the work.
  The merge deletes it.
- Traces live in the **main checkout's** `traces/`, which is gitignored and
  not in your worktree. The replays skip when a trace is not on disk, so a
  green run with skips proves nothing. Point them at
  `/Users/james./Desktop/myapps/SundayDrive/traces`, as the existing
  replays do, and report the skip count.
- iOS suite: `cd ios && xcodegen generate`, then
  `xcodebuild test -project SundayDrive.xcodeproj -scheme SundayDrive -destination 'id=<a simulator you created>'`.
  - Use `id=`, not `name=`.
  - Never pipe `xcodebuild` through `tail`.
  - With no server, about 33 tests skip. That is normal.
  - The personas need a local server on a free port, passed as
    `TEST_RUNNER_SUNDAYDRIVE_API`. Reproducing commands are at the end of
    `docs/mid-drive-recovery.md`.
  - Kill only your own server, by PID.
- No server or pipeline change, and no deploy.

## 6. Done looks like

1. The behaviours in §3, items 1–5, with the tests in item 6, and the
   whole iOS suite green except the usual skips.
2. Replays: the sixteen non-reversal drives are unchanged, `122558` is
   unchanged, and `192759`'s give-way is reported with its time and banner.
3. D9 is recorded as decided in the plan. 3b is marked built, and
   `docs/mid-drive-recovery.md` has the new section and the updated phone
   checklist.
4. If a behaviour in §3 turns out wrong once built, say why in
   `docs/mid-drive-recovery.md`, with the measurement. For example, the
   time-out might fire on a persona that never reverses deliberately.
   Don't quietly build something else.
