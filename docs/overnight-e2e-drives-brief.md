# Overnight end-to-end drives: mock routes, simulated drivers

**Status: not started (2026-09-30).** This brief is the only thing written so far.
No harness code exists yet and no app or server code has been changed for it.
It is a **test-and-report** job: build the harness, run it overnight, write up what
broke. Do **not** fix product bugs on this branch; record each one as a failing,
replayable case and describe it in the findings (see "Done looks like").

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

## What already exists — build on it, do not rebuild it

| Piece | Where | What it gives you |
|---|---|---|
| Live end-to-end drive | `ios/Tests/LiveDriveTests.swift:18` | Fetch a real route from a local server via `RouteService.routeRequest` (the POST the app sends), walk its geometry at N m/fix (`fixes(along:metresPerFix:)` `:55`), feed `NavigationModel.update` (`drive(...)` `:81`), assert step monotonic, remaining non-increasing, arrival. Only **3 fixed O/D pairs** (Worcester, Boston, Buzzards Bay, Rockport) and one driver: perfect GPS on the line. |
| Recorded-drive replay | `ios/Tests/DriveReplay.swift`, `DriveReplayTests.swift` | 12 real phone traces in the **main checkout's** `traces/` (gitignored; the file walks up out of the worktree to find them). Real GPS wander, stops, 53 real reroutes. |
| Test seams on the model | `ios/Sources/NavigationModel.swift:263` `var now`, `:265` `var fetchRoute`, `:271` `var fetchLoopResume` | Inject a clock (so 45 s grace periods and 8 s cooldowns run instantly) and a route fetcher (so reroutes hit the local server, or a stub). |
| Route-level directions audit | `tools/audit_directions.py` | Illegal turns vs raw OSM relations, silent forks (< 45°), start/end offset. Python, server-side. `docs/directions-accuracy.md` has the last numbers (illegal 18% → 1%, silent forks 78% → 0%). |
| Fake backend | `tools/fake_api.py` | Straight-line invented routes. **For looking at screens only — never for directions** (see Traps). |
| Demo launch hook | `ios/Sources/RouteModel.swift:128` `SUNDAYDRIVE_DEMO` | Preloads a route at launch, so a simulator run can reach the results/drive screen without synthesized taps. |
| Known defects already fixed | `docs/reroute-audit.md` (Findings 1-5 + "What was fixed"), `docs/reroute-step-offset.md`, `docs/never-joined-drive-brief.md` | Read these so you recognise a regression of a fixed bug versus a new one. |

## What to build

### Tier 1 — Swift simulated-driver harness (the bulk of the night)

A new test class, e.g. `ios/Tests/SimulatedDriveTests.swift` (plus a helper file
if it grows), gated exactly like `LiveDriveTests` — skips on `URLError` when no
server answers, **fails** on a decode error. Keep it out of the default fast run
(own class, so `-skip-testing:SundayDriveTests/SimulatedDriveTests` drops it).

**Mock routes.** A committed, seeded O/D list (not random per run — every
failure must be re-runnable by id). Mix: short urban (< 10 km), suburban,
long rural (60-150 km), coastal, cross-state (e.g. MA→NH, CT→RI), ferry-adjacent
/ island-adjacent pins that should fail cleanly, and **loop routes** (the loop
endpoint, `LoopModel`). Include pins deliberately placed in parking lots and
behind buildings (`scenic-destination-snaps-to-wrong-road` in project memory:
parking-lot pins snap to the road behind the building; this was the root cause of
both the arrival bug and the reroute storms). Request each at pref 0, 0.5, 1.0.

**Simulated drivers (personas).** Each takes a route and emits a timed
`CLLocation` stream with speed, course and horizontalAccuracy set — not just
coordinates — through `model.update`, with `model.now` advanced to match the
fix timestamps:

1. **Perfect** — on the line, 1 Hz, posted-ish speed.
2. **Noisy GPS** — 5-15 m lateral jitter, accuracy 10-30 m, occasional 50 m jump.
3. **Tunnel / dropout** — 20-90 s gaps, then resume further along.
4. **Stop-and-go** — dwells 20-60 s at a subset of maneuvers (lights), speed 0,
   jittering in place. (Parked time was once charged as junction cost and caused
   reroutes — memory `scenic-preliminary-drive-defects`.)
5. **Missed turn** — at a chosen maneuver, carries straight on for 300-800 m
   along the *actual road network* (take the geometry from a second server
   route, never an invented straight line), then follows whatever reroute
   `fetchRoute` returns (wired to the real local server).
6. **Wrong way at start** — sets off in the opposite direction for 200 m.
7. **Early stop** — parks 150 m before the destination, then walks the last bit.
8. **Loop driver** — drives a loop and deviates once past the far point.

**Assertions / metrics per drive** (record all, fail on the hard ones):

- Hard: arrives; `currentStep` never goes backwards; ends on the last step;
  remaining distance never rises by more than a small tolerance except across an
  adopted reroute; no more than N reroutes per km for personas 1-4 (target 0 for
  1, 3, 4); no reroute adopted that is the same line already being driven
  (`sameLine`, reroute-audit Finding 1).
- Directions: the banner step's maneuver lies ahead of the car along the route
  whenever displayed; distance-to-maneuver within 30 m of the true
  along-route distance; current-street readout matches the leg the car is on
  (the method at `LiveDriveTests.swift:135` — compare against the independently
  rendered instruction text); every maneuver gets a spoken prompt, and the last
  prompt before a maneuver lands at ≥ ~8 s of travel before it at the persona's
  speed (log the distribution; the threshold is a judgement — report, don't fail).
  Capture spoken prompts through whatever `NavigationModel` hands to its voice
  guide (find the seam; add a test-only one if needed, keeping it minimal).
- UX: time from deviation to reroute adopted; count of banner changes per
  maneuver (flicker); arrival fired within X m of the pin; any stretch where the
  model shows a "stalled"/"no GPS" state while fixes were arriving.

Write one NDJSON line per drive to a results file outside the repo (scratchpad),
and a summary table at the end.

### Tier 1b — route-level audit at the same O/D list

Run `tools/audit_directions.py` against `data/processed-ne` on the same O/D pairs
(extend it to accept a pair list if it only samples randomly) so every route in
tier 1 also has illegal-turn / silent-fork / offset numbers. This is the
"is the route itself right" half; tier 1 is "does the app guide it right".

### Tier 2 — real app in the simulator (≥ 5 drives, for UX)

Build the app, launch against the local server, preload a route through
`SUNDAYDRIVE_DEMO`, and play the route's geometry with
`xcrun simctl location <udid> start --speed=<m/s> <lat,lon> ...`. Screenshot
with `xcrun simctl io <udid> screenshot` at: results sheet, drive start, just
before and just after 3 maneuvers, during a reroute (feed a deviating point
list), stalled state, arrival. Judge each screenshot: wrong street, clipped
text, overlapping banner, stale distance, missing Apple logo/attribution. Save
screenshots under `docs/overnight-e2e/` (small PNGs only).

## Environment — the gotchas that cost hours

- **Data, venv and traces live only in the main checkout**
  (`/Users/james./Desktop/myapps/SundayDrive/`), not the worktree. Run the server
  with the main checkout's `.venv/bin/python` but the **worktree's**
  `server/serve.py`, with `SUNDAYDRIVE_DATA=<main>/data/processed-ne` and
  `PORT=<free port, e.g. 5173>`. Use New England, not `data/processed` (that is
  an older Massachusetts build); production serves NE. NE router loads in
  ~10-30 s and needs ~4 GB.
- **Do not use port 5057** and make sure nothing is on it: another session may
  own it, and with 5057 empty a missed override shows up as a skip instead of a
  silent pass against someone else's server. Confirm hits in the server's own
  access log.
- **`xcodebuild test` gets env via `TEST_RUNNER_SUNDAYDRIVE_API=...`**;
  `simctl launch` gets it via `SIMCTL_CHILD_SUNDAYDRIVE_API=...`. Swapping them
  fails silently.
- **Create and boot your own simulator** (`xcrun simctl create ... iPhone-17-Pro
  ... iOS-26-4`) and pass `-destination 'id=<UDID>'` everywhere; names are
  rejected, and `booted` may target another session's device. Delete it at the end.
- **`cd ios && xcodegen generate`** before building — the `.xcodeproj` is
  gitignored, and a new Swift file is invisible until you regenerate.
- **Never pipe `xcodebuild` through `tail`/`grep`.** Redirect to a log file.
  `VoiceCatalogueTests` can hang 13+ minutes on a missing voice asset; skip it
  (`-skip-testing:SundayDriveTests/VoiceCatalogueTests`) and say it was skipped.
- `simctl location start` rejects the whole list if one pair is malformed; get
  route points from a file the app writes, not truncated console stdout.
- Baselines to confirm first, so a red is yours: iOS **261 tests / 254 passed /
  7 skipped** (LiveDriveTests skip with no server); with a server, LiveDriveTests
  7/7, except the known server-side `test_the_reported_scenery_reflects_the_weights_that_were_sent`
  (pre-existing, don't chase). Backend: `.venv/bin/python -m pytest tests` with
  `SUNDAYDRIVE_DATA` set.
- Other sessions share this Mac; don't quote timings as performance findings.

## Traps

1. **Driving invented geometry.** A persona that "misses a turn" by
   extrapolating a straight line off the route drives through buildings and
   fields; the model will reroute correctly and you will have tested nothing, or
   flag a storm that no road could cause. Every off-route stretch must be real
   road geometry from the server (e.g. a route from the missed junction to a
   point 800 m straight ahead). Likewise, **never use `tools/fake_api.py` for any
   directions finding** — its routes are straight lines with invented steps; it is
   for screenshots of screens that need *a* route, nothing more.
2. **Measuring the model against itself.** Checking the banner against
   `properties.steps` indices, or the street readout against the same `name`
   field it displays, only proves consistency. Use an independent instrument:
   along-route distance computed from the polyline yourself, the rendered
   instruction text (as `LiveDriveTests:135` does), or the raw-OSM checks in
   `audit_directions.py`.
3. **Not advancing `model.now`.** Without injecting the clock, every guard
   (reroute cooldown, 45 s grace, stall timer) sees all fixes arrive in the same
   instant — reroute storms become impossible and stall detection never fires,
   so the run is green for the wrong reason. Stamp fixes with synthetic
   timestamps and set `model.now` to them.
4. **Hitting production.** The app's default base URL is the deployed backend
   (Info.plist → api.jameskouvlis.com). A harness that falls back to it hammers
   the live box overnight. Build requests with an explicit local base, as
   `LiveDriveTests.liveRoute` does, and skip — don't fall back — when it's down.
5. **Fixing what you find.** It will be tempting, and it will collide with other
   sessions' work on `NavigationModel.swift` and turn the night's numbers into a
   moving target. Record, don't fix. A test-only seam is the one allowed change
   to app source, and should be called out in the findings.
6. **Random O/D per run.** An unseeded sampler makes a 3 a.m. failure
   irreproducible. Commit the list; tag every result with its route id and
   persona.
7. **Treating a skip as a pass.** `XCTSkip` on no server makes the whole tier
   green. The summary must report drives *run*, not tests passed.

## Out of scope

- Fixing any navigation, routing or UI bug (record them).
- Scoring/scenery quality — whether a route is *pretty* is not this job.
- Real-phone runs and CarPlay.
- Traffic/ETA accuracy beyond noting gross outliers.

## Done looks like

1. A branch off `main` (e.g. `claude/overnight-e2e-drives`) with the harness
   (Swift test class + helpers, committed O/D list, any `audit_directions.py`
   extension) and this brief committed.
2. Baselines confirmed and quoted before any new numbers.
3. Tier 1 run: ≥ 200 routes × ≥ 6 personas actually driven (not skipped), with a
   summary table — per persona: drives run, arrivals, reroutes/km, sameLine
   adoptions, banner-behind-car events, distance-error p50/p95, prompt lead-time
   p5/p50, street-readout mismatches.
4. Tier 1b audit numbers on the same routes, compared to
   `docs/directions-accuracy.md`.
5. Tier 2: ≥ 5 simulator drives with annotated screenshots in `docs/overnight-e2e/`.
6. Findings appended to this file under `# Findings`: each defect with route id,
   persona, reproduction command, the observed vs expected, a `file:line` guess at
   the mechanism flagged as a guess, and a severity. Failing cases kept as
   (skipped-by-default or `XCTExpectFailure`) tests so they can be replayed.
7. An honest list of what was **not** determined — e.g. prompt-timing
   threshold is a judgement, voice not audible in simulator, personas that could
   not be made realistic — rather than a clean-looking report.
8. A PR opened against `main`; not merged.
