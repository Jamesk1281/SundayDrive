# Pre-submission review: grill the whole project, then give a verdict

**Status: brief only. Nothing has been reviewed and nothing has been changed.**
Written 2026-09-30 against `main` at `6f26edf` ("Merge the brand UI alignment",
2026-09-29 23:15). The answer goes in `docs/pre-submission-review-verdict.md`,
which does not exist yet. No source file, test or other document was touched to
write this brief.

This file holds the map, the list of what earlier reviews already concluded, and
the rules. **It is not a list of findings.** Nothing below says what is wrong
with the project. Where it states a fact about the tree, treat that as a claim to
check (§6, trap 2), not as evidence.

---

## 1. The job

The owner is about to submit Sunday Drive to App Review and wants the whole
project attacked first, "shelled and grilled beyond belief". There are four
questions, and all four answers go in one document:

1. **What doesn't work conceptually?** This is about the idea, not the code. The
   product is a beauty score for every road in New England, a dial that trades
   minutes for scenery, loops that bring you home the pretty way, and
   turn-by-turn guidance from a custom router drawn over Apple's map. Does each
   of these do what the product claims, for the person it claims to serve?
   Where does the code's model of the world stop matching the real world?
2. **What doesn't work in theory or in the market?** Who is it for? Why would
   they choose it over what is already on their phone, and why would they open
   it a second time? What happens if it succeeds, and what happens if nobody
   notices it? The app ships free, with $0 for marketing, one person, one
   2-OCPU server, New England only and iPhone only. Can it survive those
   constraints?
3. **Where are the big code problems?** Look at correctness on the paths a
   driver depends on, crashes and hangs, gaps in the state machines, the public
   server's attack surface and capacity, whether the data build can be
   reproduced, the deploy, and tests that cannot fail.
4. **Will App Review pass it?** This decides the verdict more than anything
   else.

**It has to reach different conclusions from every earlier review, and copy none
of them.** §4 lists what they concluded. This is not a request to disagree for
the sake of it. See trap 1.

**End with a verdict: submit, or don't.** §8 says what the verdict must contain.

---

## 2. The tree today, measured for this brief (2026-09-30, 00:30–00:45 EDT)

| | |
|---|---|
| `main` | `6f26edf`. It moves several times an hour, so pin your own SHA at the start (trap 2) |
| Backend suite | **388 passed, 0 failed, 0 skipped, 264 s** on the served build: `SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python -m pytest -q tests`, run from a worktree at `6f26edf`. The docs quote 379, 378/1 and 341/6, which come from older trees or other machines |
| iOS suite | **Not re-run for this brief.** Last recorded on 2026-09-29, after the POST change: 261 tests, 254 passed, 7 skipped (`LiveDriveTests`, because no server was running). Two merges since then (`80b9abf` never-joined pause, `6f26edf` brand UI) add tests |
| Live API | `https://api.jameskouvlis.com/api/health` returned HTTP 200 in 0.15 s. Since 2026-09-29 it has been served from an Oracle Always Free A1 box (2 OCPU / 8 GB) through a Cloudflare tunnel (`server/DEPLOY-oracle.md`) |
| Domain | RDAP gives the `jameskouvlis.com` expiration as **2026-10-28T18:52:52Z**, and it has not been renewed. This is already known (§4), so it is a status item, not a finding |
| Pages | `https://jamesk1281.github.io/SundayDrive/` and `/privacy/` both returned 200 |
| Shipping identity | `ios/project.yml`: bundle id `app.sundaydrive` (:73), `MARKETING_VERSION "1.0"` (:81), build `"1"` (:82), `SundayDriveAPIBaseURL: https://api.jameskouvlis.com` (:70), `UIBackgroundModes` (:50) |
| API surface | `server/app.py`: `/api/route` GET+POST (:238), `/api/loop` GET+POST (:316), `/api/health` (:414), `/` (:420). `server/serve.py` serves it through waitress |
| Size | Python is about 14.6k lines (`pipeline/router.py` 2,414; `tools/analyze_trace.py` 1,588; `tests/test_routing.py` 1,507). Swift is about 13.9k lines across `ios/Sources` and `ios/Tests` (`NavigationModel.swift` 1,509; `VoiceGuide.swift` 627). The iOS app has no third-party dependencies |
| Dates that bound the verdict | The first **TestFlight upload** locks the bundle id permanently (`docs/app-store-submission.md` §6). In the marketing plan, launch day **L is Thu 2026-10-22**, with a go/no-go check at L-7. The plan uses one-shot channels on launch: press, one launch post per subreddit, Show HN and a featuring nomination. None of them can be run a second time |
| Not on `main` | Five local branches hold *parked* work, not shipped work: `claude/app-branding-brainstorm-045351` (a 2026-09-01 UI change from before the redesign), `claude/project-context-gathering-d0c730` (a 2026-08-29 change to `looper.py`), `claude/project-timeline-draft-96d9b6` (a 2026-09-16 roadmap draft), `claude/hosting-setup-guidebook-11cf46` (a brief) and `claude/brand-ui-alignment` (screenshots only). **`docs/marketing-plan.md` exists only as an uncommitted file**, at `<main>/.claude/worktrees/marketing-deployment-strategy-18f044/docs/marketing-plan.md` |

Throughout this brief, `<main>` means the main checkout, which is the first line
that `git worktree list` prints.

---

## 3. Where nobody has looked

Everything in this section can be checked with `git log` and `grep`. That is why
it is the only coverage map worth handing over. It is not complete, and it is not
a list of findings. If a gap turns out to be fine, it becomes an "attacked and
held" entry (§8).

1. **None of the code merged in the last month has had a code review.** The last
   whole-project review is `9163cf6` (2026-08-29 00:24). Since then `main` has
   taken 170 commits (119 of them non-merge). That is **+6,337 / −1,306 lines of
   code across 60 files** under `ios/Sources`, `server/` and `pipeline/` (markdown
   excluded), plus 3,744 lines of tests. It covers:
   - all of voice guidance (`VoiceGuide.swift`, `VoiceCatalogue.swift`)
   - the whole clean-sheet interface, merged as `f54e24f` on 2026-09-29
     (`HomeView`, `PlanningView`, `PlanningMap`, `PlaceField`,
     `DirectionsView`, `LoopView`, `PrefSlider`, `Recents`, `StalledView` and
     `Theme`, with `RoutePanel.swift` and `LoopPanel.swift` deleted)
   - `NavigationModel.swift`, +265 lines
   - `router.py`, +531 lines, including the A\* fastest arm
   - `score.py`, +352 lines
   - `landcover.py`, which is new
   - `server/app.py`, +162 lines, including the POST change (`b5cd47e`, merged
     as `4ef3e11`)
   - `server/deploy-oracle.sh`, which is new (`ca9e724`)

   Several of these had a design document or a targeted check. None of them had
   a code review.
2. **The public server has never had a security review.** No committed document
   contains "security review", "threat model" or "attack surface". Rate limiting
   comes up only as capacity sizing (`hosting-options-findings.md:820`;
   `server/DEPLOY-oracle.md` Part 11, at :635). The repo cannot tell you whether
   that rule is actually live.
3. **App Review has only been looked at piece by piece.** Guidelines 2.1 (a
   backend that is down, which `release-plan.md` §7 calls the most likely
   rejection), 2.3.7 (the subtitle), 5.1.1 (the in-app privacy link) and 5.2.1
   (names) are each cited somewhere. So are the route-guidance notice,
   attribution and the background modes (`app-store-submission.md` §5). No
   committed document mentions guideline 4.2, and none reads the current
   guidelines from start to finish against this app. None considers what
   happens when the review itself takes place outside New England. The
   marketing plan counts out-of-region installs as a *ratings* risk (§10),
   which is a different question.
4. **The premise has been measured, positioned and planned around, but nobody
   has attacked it.** `measuring-scenery.md` validates the score as a
   measurement: separation 0.74 on 79 marks, all from one driver.
   `branding-brainstorm.md` positions it, and the marketing plan distributes it.
   Nobody has asked as a question in its own right whether the product built on
   that score does a job people want done, or whether a driver would notice any
   difference from the roads they already take.
5. **Accessibility was designed but never audited.** `interface-design.md` §7.7
   specifies Dynamic Type and VoiceOver support. Nothing records a check of the
   built app.

---

## 4. What earlier reviews concluded (the ledger)

Each entry is one line and works as a pointer. **Read the source before you rely
on any line here.** Prior art also includes anything in `docs/`, any commit
message on `main`, the uncommitted marketing plan, and your auto-memory
(`MEMORY.md`).

**Whole-project and max-effort code reviews (all fixed; do not re-report)**

- **2026-08-14, `40cabfd`.** The commit message is the write-up. It lists
  fifteen findings in four areas:
  - The drive-trace instrument: a wrong denominator in the optimism headline;
    clamped deltas that turned GPS noise into drift and deleted stops; an
    arithmetic mean where a harmonic one belongs; stops merged across dropouts;
    every step counted as a turn; and `off` never used as a filter.
  - The graph: `largest_component` ran undirected. There were 572
    strongly-connected components, and now there is one.
  - The app: a crash from a stale generated `Info.plist`; switch-to-fastest not
    restored after a failure; a parked car rerouting every 8 s forever; location
    left running after arrival; a recording indicator that could not see
    missing fixes; and a leaked trace descriptor.
  - The server: waitress's four threads give a 1.08× speedup, so the rate limit
    had been sized for ~20 req/s when the real ceiling is ~5.
- **2026-08-20, `83f498c`.** Twelve of fifteen findings were fixed. The other
  three were deliberately left alone, and the commit message lists them. Mutation
  testing found four tests that still passed with the constant they guard set to
  zero (`CONTROL_SECONDS`, `PREF_CURVE`, `node_copies`). The review also found
  that step-folding had no tests, that arriving mid-request left
  switch-to-fastest stranded, that a due-north heading was sent as 360.0, that
  traces logged "unknown" maneuvers, that the reachability check failed
  silently, that bearings were recomputed on every request, and that the
  operator numbers were stale.
- **2026-08-29, `9163cf6`.** Thirteen defects:
  - a loop latched `arrived` on its first fix
  - `snap` picked the road in plan view at grade separations
  - one noisy fix could discard a route
  - an invalid fix could plan a trip from (0, 0)
  - the curvature floor was applied to chunks
  - `relief.tif` had no nodata value
  - `attach_scores` joined at any distance
  - a via-way restriction banned both approaches
  - the loop planner and the router broke ties in opposite directions
  - the off-route filter was asymmetric
  - denominators did not match
  - `dropped_*` counts were doubled
  - a loop fixture was not actually closed
  - `LiveDriveTests` swallowed every error into `XCTSkip`
- **2026-08-26, `docs/reroute-audit.md`.** Five findings on the reroute path,
  four of them fixed, and three items left open at the end. The first open item
  (a drive that never joins its route can never end) was answered by the
  never-joined pause, merged as `80b9abf` on 2026-09-29. That makes it
  post-review code (§3.1).
- **2026-08-29, `docs/consumer-polish-brief.md`.** Eight defects found by driving
  the app in the simulator. Its table says four are fixed. Two of the four open
  ones describe the *old* planning sheet, so check each against the redesign
  before you cite it either way.
- **2026-08-15/16, `docs/directions-accuracy.md` and `18b8600`.** An audit of 120
  random routes. Illegal turns fell from 18% to 1%, misleading forks from 78% to
  0%, and wrong-side turns from 5 per 150 to 0.

**Scoring and the scenic premise**

- `measuring-scenery.md`: separation of 0.74, from 79 marks over 12 drives by one
  driver, with a noise floor. It already states the one-driver limit, so that is
  not a new finding.
- `scenery-grading-verdict.md` (2026-09-16): verdicts on twenty grading
  proposals. None of them has been built.
- `scenery-cap-options.md`: `BETA` is a lever that does nothing, and the cap on
  how much scenery a route can buy is structural.
- `geodata-sources-findings.md` and `geodata-peer-review-verdict.md`: OSM's green
  areas are 3.3× more complete in Rhode Island than in Maine, so WorldCover tree
  cover was blended in.
- `unpaved-and-urban-verdict.md`: road surface was measuring how carefully an
  area had been mapped, not how beautiful it is. It was taken out of the score
  and made a priced preference instead.
- `driver-preferences-study.md`: road class is independent of scenery but loses
  to the pref slider, so it is off by default.
- `new-england-terrain-findings.md`: `RELIEF_FULL` has no range left north of
  Massachusetts, and Terrarium's corrupt pixels are dropped.
- `route-distribution-study.md`: 983 trips and 5,192 routes, showing what the
  router actually offers, plus the guard that stops it offering a scenic route
  that scores below the fastest one.

**Travel time**

- `junction-timing-plan.md`: ETA error fell from 22% to 5.7% once traffic
  controls were priced in.
- `traffic-schedule-plan.md`: don't build time-of-day travel times on borrowed
  data.

**The app's features**

- `voice-guidance-plan.md`: the schedule is time-based. The simulator fails open
  on background audio, so this was measured on the phone.
- `loop-routes-design.md`: three loop architectures were measured and one was
  built. §12 covers where building it proved the design wrong.
- `current-street-display.md`: the readout of the road under the car, and why it
  cannot fix the start-point snap.
- `driving-app-features-cost.md`: seven candidate features costed. One of them is
  lane guidance, which `turn:lanes` coverage cannot support anywhere in New
  England.
- `never-joined-drive-brief.md`: GPS speed does not tell you a parked phone is
  still.
- `interface-design.md` (built 2026-09-20, merged 2026-09-29): the old sheet
  covered Apple's logo at every detent. Planning became a page with a bounded
  map card and a 48 pt keep-out zone. §13 reviews the documents it replaced.

**Release, legal, hosting and market**

- `legal-and-ip-audit.md` (2026-09-01) covers Attachment 6 of the Apple developer
  agreement:
  - Covering Apple's logo is a breach.
  - Turn-by-turn guidance needs a fixed notice, which has shipped in
    `AboutView.swift`.
  - `DriveTrace` stores Apple-geocoded coordinates (§2.5, which now carries a
    duty to delete them).
  - There are two bright lines, described in trap 6.
- `licensing-open-questions.md`: Apache-2.0 for the repo, ODbL for
  `route-census/`, and the clause renumbered to §3.3.3(F)(iii).
  `data-sources.md`: what each dataset is owed.
- `app-store-submission.md` (2026-09-19): the custom EULA text, the
  nutrition-label answers, the policy URL, export compliance, which fields lock
  and when, and the questions App Review is expected to ask (§5).
- `privacy-policy.md`: a developer draft. The owner decided on no lawyer and a
  US-only launch (`release-plan.md` Decision 3).
- `release-plan.md` (2026-09-19, with header notes up to 2026-09-29): the release
  sequence. §10 lists the submission artifacts still open: the EULA field,
  export compliance, screenshots, description, category and the name
  reservation.
- `sunday-drive-naming.md` and the trademark documents: the name was settled on a
  free knockout screen (paid clearance was declined), and it has the worst domain
  position of any candidate. `sunday-drive-rename-audit.md`: 3,843 occurrences
  classified and 16 defects found, all of them in docs.
- `hosting-independent-review.md` (2026-09-28) is the last of the hosting
  documents. Keep Oracle, as a second health-gated connector beside the laptop.
  The domain expires on 2026-10-28, and a US Contabo box costs $6.58–7.90/mo.
- The marketing plan (uncommitted):
  - At least eight scenic-driving apps launched in 2026, and six of them have
    zero ratings.
  - Short video is the main channel.
  - A risks table (§10): the domain lapsing, a load spike, one-star reviews
    from out-of-region installs, Android users, a home address showing in a
    video, confusion with Google Drive and a dealership, and burnout.
  - Seven engineering asks (§5.10): a rating prompt, a friendlier out-of-region
    message, sharing, Siri, a reminder, a web preview and CarPlay.

---

## 5. Methods that have found real defects here

These are the methods that found everything in the ledger above. Reuse the
methods. The conclusions are used up.

1. **Mutate the constant, then run the suite.** Four tests once passed with the
   value they guard set to zero. A test that imports the constant it asserts
   against cannot fail.
2. **Run two instruments on one input and compare the results.** A fitter and a
   report once disagreed, seven stops against four. The difference turned out to
   be a lunch break being fitted as traffic-signal cost.
3. **Replay the recorded drives.** Twelve traces sit in `<main>/traces/`
   (gitignored), and `ios/Tests/DriveReplay.swift` exists to replay them. Every
   fix records what the phone computed at the time. Real drives show whether
   things hold up over time, but they won't pin down a specific bug. So also
   break the code on purpose and check that the replay notices.
4. **Neutralise one parameter and treat the change in output as that parameter's
   error.** A 168 m off-route reading came out as 11.8 m once its floor was
   removed.
5. **Choose a query shape that can show the defect.** One penalty had no visible
   effect on sixty-kilometre A→B routes, yet it cut dirt roads from 23.7% of loop
   distance to 8.2%. `/api/loop` has its own cost surface.
6. **Check that the fixture has the property the test's name promises**, whether
   that is closed, doubling back, or carrying a field. A loop test once used a
   straight line, and the fixture builder once dropped a field that the server
   sent.
7. **Compare any change against the precision of the wire format.** The server
   rounds `mean_score` to two decimals (`server/app.py:387`), so a real change of
   0.003 shows up as no change at all.
8. **Drive the app in the simulator along a real route** (`xcrun simctl location
   start`). That is how eight consumer-facing defects were found in one sitting.
9. **Run against both builds.** `data/processed` (Massachusetts) and
   `data/processed-ne` (New England, which is what gets served) give different
   answers, and a defect can exist in only one of them.
10. **Check a cached artifact's bounds against the region it claims to cover.** A
    "New England" traffic-control cache once had Connecticut's bounding box.

---

## 6. Traps

**The two traps that lead to a wrong verdict**

1. **Novelty by restating old findings, or by disagreeing for effect.** The owner
   asked for conclusions that differ from earlier reviews. You can fail in either
   direction:
   - One failure is re-reporting a §4 finding in new words.
   - The other is inventing disagreement with a correct earlier conclusion to
     look original. This repo's own history calls that "worse than useless".

   The rule: **before a finding goes in, grep for its key nouns** in `docs/`,
   in `git log main --grep`, in the marketing plan and in your auto-memory. If
   there is prior art, the finding belongs in §8's "prior conclusions
   revisited", and only if you have *new evidence*: a fix that never landed, a
   fix that regressed, or a premise the tree no longer supports. If a prior
   conclusion simply still stands, say so in one line and move on. Three real,
   new findings from the night are worth more than thirty restated ones.
2. **Believing what documents say about the code, or about what shipped. That
   includes this brief.** Documents in this repo have been shown to be wrong
   about the code in seven different ways. Examples include correct line
   numbers with the wrong control flow, a "default" that was really a test
   fixture, and a peer's "correction" that was a misreading of the corrected
   session's own merged work.

   The documents also disagree with each other about the current state:
   - `release-plan.md`'s header says the redesign uncovered Apple's logo on
     2026-09-29.
   - `app-store-submission.md` §7.2 and §8 row 9 still say "Blocked". They also
     cite `project.yml:66` for a bundle id that is now at :73.

   At most one of those is current, so check on the tree. **Pin a SHA at the
   start and read the tree at that SHA.** Use `git show <sha>:<file>`, never
   `git show main:<file>`. `main` moves several times an hour, and nothing in
   the output tells you it moved. Cite `file:line` at your pinned SHA.

   A ticked item may also mean something was *declined* rather than *passed*.
   Paid trademark clearance and privacy counsel were both declined, not
   cleared.

**The traps that waste the night or cause damage**

3. **Do not spawn sub-agents.** Do not use the Agent tool or fan work out to
   other agents, not even `Explore`. Read and search directly. Sub-agents use up
   the owner's hard session cap. On this project, two research agents once
   turned into six and used up the cap mid-task. A brief asking for an
   "overnight comprehensive review" is exactly the kind that sets off that
   fan-out.
4. **A green suite is not evidence.** `LiveDriveTests` skips all seven of its
   tests without saying so when nothing answers. `VoiceCatalogueTests` can hang
   for 13+ minutes when a voice asset is listed but not downloaded. Tests in this
   repo have imported the constant they assert against. Mutate before you trust a
   result, and say which run your numbers come from.
5. **The simulator lets background execution through when the phone would not.**
   A build without the audio background mode spoke from the background 18 times
   out of 18 on the simulator, and 0 times out of 19 on the phone. The phone is
   not available tonight, so any claim about what happens when the phone is
   locked or the app is in the background is **undetermined**. Put it in §8's
   undetermined list and say which way it would move the verdict.
6. **Never compare this app's routes or ETAs with Apple's.** That means no
   `MKDirections` and no Apple Maps side by side. Attachment 6 §2.3 of the
   developer agreement forbids using Apple's map service to evaluate or improve
   your own. It is the most tempting experiment in any review of route quality.
   Benchmark against the fastest arm, the recorded drives and a clock instead.
   Also never let Apple-derived coordinates into `data/` (§2.2).
7. **The live API is production.** It runs on one 2-OCPU box with four waitress
   threads, and a default loop took 3.9 s on its first call there. A few
   requests to observe behaviour are fine. Run load tests, fuzzing and security
   probing against a **local** server (§7). Do not touch the Oracle box,
   Cloudflare, GitHub settings or App Store Connect.
8. **Another session's job will distort your timings.** Other Claude sessions
   share this 8-core Mac and compete for memory bandwidth, which is exactly what
   this router's full-array numpy passes need. The same unmodified code has
   measured 254, 277 and 352 ms on different runs. Before timing anything:
   - check `ps -eo pid,rss,pcpu,args | grep "[P]ython /private"`
   - run each measurement twice
   - interleave A/B pairs in one process
   - quote ratios rather than absolute times
9. **Settled owner decisions are not findings.** These include:
   - the name and the bundle id
   - the subtitle *The scenic route, on purpose*, chosen despite a
     recommendation against it
   - a free knockout screen instead of paid trademark clearance
   - no privacy counsel
   - a US-only launch
   - Oracle hosting
   - a free app with a $0 marketing budget
   - Apache-2.0

   You can challenge a decision only with evidence that the document which made
   it did not have, and you must name that document.
10. **Fix nothing. Report findings only.** The owner's planning session sends
    fixes out later, and it can only do that if the tree you describe is the
    tree you reviewed. Make no edits outside the verdict document, leave no
    scaffolding in the tree, and do not push or merge.
11. **The repo is public**, and the verdict will be committed to a branch of it.
    Don't include:
    - absolute local paths (write `<main>/…` instead)
    - credentials or tokens
    - coordinates, addresses or start points from the drive traces, which record
      where the owner drives

---

## 7. Environment

- **`.venv` and `data/` exist only in `<main>`**, not in your worktree.
  - Run Python as `<main>/.venv/bin/python -m pytest …`, because the venv's
    console scripts have hard-coded shebangs.
  - Set `SUNDAYDRIVE_DATA=<main>/data/processed-ne` to test the served build.
    `data/processed` is the older Massachusetts build, and
    `data/processed_backup` does not load.
  - Environment variable names are read in three layers: `SUNDAYDRIVE_*`, then
    `VICTORYLAP_*`, then `SCENIC_*`. This is deliberate, left over from two
    renames.
- **Running a local server.** Use:
  `PORT=<free port> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python server/serve.py`.
  Wait until `/api/health` answers before sending requests. **Don't use port
  5057.** `server/app.py` and `<main>/.claude/launch.json` default to it, and
  other sessions fight over it. Flask runs without a reloader, so restart the
  server after any change.
- **iOS setup.**
  - Run `cd ios && xcodegen generate` first, because the `.xcodeproj` is
    gitignored.
  - Create your own simulator. This machine may have none, and any shared one
    belongs to another session: run
    `xcrun simctl create "<name>" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-4`,
    then `xcrun simctl boot <udid>`, then `xcrun simctl bootstatus <udid> -b`.
    `Status=4294967295` together with `Finished` means success.
  - Pass `-destination 'id=<udid>'`, because xcodebuild rejects a device name.
    Delete the device when you are done.
- **Running the tests against your server.** Use
  `TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:<port> xcodebuild test -project SundayDrive.xcodeproj -scheme SundayDrive -destination 'id=<udid>' > <log> 2>&1`
  with nothing on 5057. That way a missed override shows up as seven skips
  instead of a silent pass. For `simctl launch` the prefix is `SIMCTL_CHILD_`
  instead. If `VoiceCatalogueTests` stalls, add
  `-skip-testing:SundayDriveTests/VoiceCatalogueTests` and report the voice tests
  as unverified.
- **Never pipe `xcodebuild` through `tail` or `grep`.** A hung build and a slow
  one look identical that way. Redirect the output to a log instead. Real compile
  errors match `^/.*\.swift:[0-9]+:[0-9]+: error:`, while a bare `error:` also
  matches routine simulator noise. In the same way, `pytest | tail` reports
  tail's exit code, not pytest's.
- **What you can do in the simulator without the owner:**
  - launch the app with environment variables
  - place the device: `xcrun simctl location <udid> set …`
  - play a real drive: `xcrun simctl location <udid> start --speed=22 <lat,lon> …`
    (one malformed pair rejects the whole list)
  - grant permissions: `xcrun simctl privacy <udid> grant location-always app.sundaydrive`
  - take screenshots: `xcrun simctl io <udid> screenshot <path>`

  You **cannot tap**. The simulator control tool needs the owner's permission,
  and that is not available overnight. `simctl` cannot send touches either.
  `RouteModel.init` reads a `SUNDAYDRIVE_DEMO` hook (`RouteModel.swift:128-133`)
  that loads a route without any taps. Keep any scaffolding you add to use it
  out of the commit.
- **Do your own web research** with WebFetch and WebSearch. Read the App Review
  guidelines from `developer.apple.com`, not from memory, because they change.
  `itunes.apple.com/search` ranks by relevance, so report any App Store count as
  "at least N". Python's SSL certificate store is not configured on this
  machine, so fetch with `curl`.
- `gh` is not installed. The disk had 34 GB free on 2026-09-30, and DerivedData
  will grow.

---

## 8. What "done" looks like

1. **`docs/pre-submission-review-verdict.md`, committed together with this
   brief** on the branch your worktree gives you, never on `main`. Don't push or
   merge it. Leave `docs/README.md` alone: its index row gets added at merge
   time, and another worktree has uncommitted edits to it.
2. **Line 3 is a bold Status line** that gives the SHA you reviewed and the
   verdict in one word.
3. **Baselines come first:**
   - the SHA
   - both test suites as you ran them: backend on `processed-ne` at least, and
     iOS with `LiveDriveTests` actually reaching your server, plus how you know
     it did
   - the live API
   - RDAP
   - Pages
   - what else was running on the machine
4. **Findings go under four headings:** conceptual, market, code and App Review.
   Each finding has:
   - an ID
   - a severity:
     - **Blocker**: a likely App Review rejection; a driver put in danger,
       stranded or misled; or a live contract breach
     - **Major**: passes review but damages the launch, or the first session,
       for a real group of users
     - **Minor**: anything else
   - evidence at your pinned SHA: the `file:line`, the command, and its output
     or the measurement
   - how to reproduce it
   - a confidence level:
     - **Verified**: reproduced
     - **Plausible**: the mechanism was read in the code but not reproduced
     - **Hypothesis**: stated together with what would disprove it
   - its closest prior art from §4, or "none", and how it differs
   - the cheapest fix direction, in a sentence or two, not implemented
5. **"Attacked and held"**: what you tried to break and couldn't, with the
   attempt described, so nobody repeats it.
6. **"Prior conclusions revisited"**: only the ones where you have new evidence.
   That means a fix that never landed, a fix that regressed, or a premise that
   has moved.
7. **"Undetermined"**: whatever tonight cannot settle (the phone, a paid account,
   a real drive, App Review itself), what would settle each item, and which way
   each would move the verdict.
8. **The verdict comes last.** It must be one of these:
   - **SUBMIT**
   - **SUBMIT AFTER**: numbered blockers, each with its cheapest fix and how big
     that fix is
   - **DO NOT SUBMIT**: what would have to change, and whether that can happen
     before L

   State the bar you used. The default bar has four parts:
   - App Review is likely to pass it the first time.
   - No defect puts a driver in danger, strands them or misleads them on the
     main paths: plan, drive, reroute, arrive and end, for both a route and a
     loop.
   - There is no live breach of any term the app or its listing is bound by.
   - Nothing makes the planned launch undercut itself.

   Keep **the build** separate from **the package**. The App Store Connect items
   in `release-plan.md` §10 are not code.
9. **Commit as you go.** Commit after finishing each heading. Include the verdict
   section from the first commit and mark it provisional. That way a session that
   runs out partway through the night still ends with a verdict and says which
   parts it finished.
10. **Be honest about limits.** If an area turns out clean, say so, because
    "attacked, nothing found" is a result. If the verdict needs something that
    tonight doesn't have, say so and make the verdict conditional on it.

Keep scratch scripts outside the repository. End the document with a
**Reproducing this** section that lists the commands in order.
