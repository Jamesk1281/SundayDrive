# Brief: ask for an App Store rating after a good drive

**Status: decided, not built.** Written 2026-10-08 against `main` at `8ad257f`.
Nothing has been touched. **This brief is temporary, and the merge that brings
the work back deletes it** (`docs/briefs.md`).

The answer goes in a new `docs/rating-prompt.md`, plus the code and tests.
Never append results to this file, and never cite it from code or tests.

## 1. The goal, and why

The app never asks for a rating. `git grep -i 'requestReview\|StoreKit' -- ios`
is empty at `8ad257f`. The 2026-10-04 store-readiness pass listed this as a
gap.

`docs/marketing-plan.md` (around line 105–127) counted the 2026 scenic-drive
apps. Six of eight have **zero ratings**, and fifteen ratings would make this
the most-used of them. Ratings feed App Store search rank and whether a
browser installs. The system prompt is the only way to ask inside the app:
App Review Guideline 5.6.1 forbids custom review prompts.

**How the system prompt works.** SwiftUI's `@Environment(\.requestReview)`
(iOS 16+, StoreKit) *asks* the system to show the five-star sheet.
- The system decides whether it actually appears, at most 3 times in 365 days
  per user per app.
- Its words cannot be changed, and nothing may be offered for a rating.
- In a **Debug** build it shows **every** time it is asked.
- In **TestFlight** it **never** shows.
- In production it is rate-limited by Apple, invisibly.

## 2. What is decided

The owner agreed this on 2026-10-08:

- **When:** after the driver taps **Done** on the arrival card, once the
  planning screen is back. Never while driving, and never on the arrival card
  itself.
  - The card appears when the car is near the destination and may still be
    rolling (`ios/Sources/NavView.swift:94-98`).
  - Apple's guidance is not to call `requestReview` *as the direct response
    to* a button tap. So Done sets a pending flag, and the planning screen
    asks a moment after it appears (about 1 s).
- **Which drives count:** a drive that **arrived** (`nav.arrived`, the
  arrival card's Done, `ArrivalView.swift` → `onDone`) and lasted at least
  **10 minutes** (`nav.elapsedMinutes`, `NavigationModel.swift:1145`). Loops
  count; their arrival card says "Back where you started".
  - Ending a drive early does not count. That covers the furniture's End
    button (`NavView.swift:~501`) and `StalledView`'s "End drive".
  - The owner ends most test drives himself, so most of his won't count.
    That is intended.
- **Whose:** from the **second** qualifying drive on, at most **once per app
  version** (`CFBundleShortVersionString`). Apple's own cap sits on top.
  - Not on the first drive: a first-timer hasn't yet had the good drive the
    prompt should follow.
  - Once per version is Apple's sample-code pattern. It keeps the app from
    spending its three yearly showings on one release.

## 3. What to build

1. **A small type for the policy**, for example `RatingPrompt` in a new
   `ios/Sources/RatingPrompt.swift`. It has:
   - `noteArrival(elapsedMinutes:)`, which counts qualifying drives in
     `UserDefaults`;
   - `shouldAsk(version:)`;
   - `didAsk(version:)`.

   Use an injected `UserDefaults` and pass the version in, so it is
   unit-testable with no UI.
2. **Wire it with the fewest edits to busy files.**
   - Count the drive and set the pending flag on the arrival card's Done
     (`ArrivalView.swift`, wrapping `onDone`).
   - Ask from the planning side (`ContentView.swift`, where
     `model.nav == nil` brings `PlanningView` back, or `PlanningView` itself),
     with `@Environment(\.requestReview)`.
   - **Don't edit `NavView.swift` or `NavigationModel.swift`** (§5).
3. **A test seam.** Never request a review while running under XCTest (§4
   trap 2). Check `ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"]`
   or the project's existing convention, if it has one. Grep for how other
   code detects tests before inventing one.
4. **Privacy: add the counter to both copies of the policy** (§4 trap 1):
   - `docs/privacy-policy.md` §1's "What is stored on your phone" table, with
     its `file:line`;
   - `site/privacy/index.html`, which says to change the two together.

   It is a count and a version string, nothing about where or when. The
   nutrition label does not change. `PrivacyInfo.xcprivacy` already declares
   `UserDefaults` (CA92.1).
5. **Tests**, in a new `ios/Tests/RatingPromptTests.swift`:
   - the first qualifying drive doesn't ask, and the second does;
   - a 9-minute drive doesn't count;
   - once asked, the same version doesn't ask again, and a new version may;
   - nothing asks under XCTest.

   If the ask can be put behind a closure, test that Done followed by the
   planning screen appearing calls it exactly once.
6. **Verify by eye in a Debug simulator build**, where the sheet always
   shows. Fake two qualifying arrivals through the policy type, or a debug
   launch argument, rather than driving 20 minutes. Take a screenshot of the
   sheet over the planning screen for `docs/rating-prompt.md`. The owner
   cannot check it in TestFlight (§1).

## 4. Traps

1. **The privacy policy enumerates every value stored on the phone.**
   `docs/privacy-policy.md` §1 has a table of every `UserDefaults` item, with
   `file:line`. `site/privacy/index.html` (live on GitHub Pages) is its
   user-facing copy, and says to change the two together. A new counter that
   isn't listed makes a published policy false. That is the kind of thing an
   App Review or a reader can catch, and it is cheap to get right.
2. **A Debug build shows the sheet every time, and that breaks UI tests.**
   The iOS suite runs in a hosted Debug app. `SimulatorScreenDriveTests`
   drives to arrival and screenshots it. An XCUITest that taps Done on a
   simulator with two counted drives would get a system sheet over the next
   screen. Gate on XCTest, and don't count drives the tests make. The
   screenshot session also uses fresh simulators, which start at zero, so it
   is safe either way.
3. **Don't ask on the arrival card, or on "End drive".** The card shows when
   the car is near the destination, possibly moving. A sheet over a driving
   screen is the one place this must never appear. An ended-early drive is
   often the bad one.
4. **Don't build a "Rate us" button or a pre-prompt** ("Enjoying Sunday
   Drive?" → Yes → system sheet). Guideline 5.6.1 forbids custom review
   prompts, and filtering for happy users first is the pattern App Review
   rejects.

## 5. Build and test

- Work on a branch off current `main` (`8ad257f` or later), never on `main`.
  This brief may be untracked in the master worktree
  (`release-readiness-check-a285aa`). Copy it into yours and commit it with
  the work.
- **Parallel sessions:**
  - The wrong-way time-out is editing `NavView.swift` and
    `NavigationModel.swift`.
  - K-1 is editing `RouteService.swift`, `server/app.py`, and
    `NavigationModel`'s `classify`/`traceDetail`.

  This change should touch none of those. If it must, keep the edit tiny and
  say so.
- `cd ios && xcodegen generate` (a new source file needs it), then
  `xcodebuild test -project SundayDrive.xcodeproj -scheme SundayDrive -destination 'id=<a simulator you created>'`.
  Use `id=`, not `name=`, and never pipe it through `tail`. About 33 tests
  skip with no server, which is normal.
- No server change and no deploy.

## 6. Done looks like

1. §3 items 1–5 built. The iOS suite is green apart from the usual skips.
2. A Debug-simulator screenshot of the sheet over the planning screen, in
   `docs/rating-prompt.md`, which also records the rule (§2) and where it
   lives in code.
3. Both privacy-policy copies list the new stored value.
4. Or, if a part of §2 turns out wrong once built, say why in
   `docs/rating-prompt.md`. One example: the planning screen can't host the
   ask cleanly.
