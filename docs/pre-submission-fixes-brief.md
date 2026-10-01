# Pre-submission fixes, round 1: the loop escape hatch, approximate location, and three cheap ones

**Status: diagnosed, not fixed.** Written 2026-10-01 against `main` at
`d4265d2`, from the pre-submission review's verdict. That verdict is
`docs/pre-submission-review-verdict.md` on branch
`claude/suspicious-mirzakhani-349da5`, reviewed at `6f26edf`. Every `file:line`
below has been re-checked at `d4265d2`. Since `6f26edf`, `main` has taken the
loop-matching fix (`45b1685`), which touched only `NavigationModel.update` and
`Geo.swift` and changes none of the mechanisms here. No source file has been
touched for this brief.

## Scope

**In scope**, in priority order:
1. **Loop escape hatch** (verdict K-7, blocker 1). On a loop, "Switch to
   fastest" routes through the far point instead of going home.
2. **Approximate location** (verdict §6.2, blocker 2). With Precise Location
   off, navigation never receives a fix, and the screen claims "50 ft away".
3. **The version and build number** (verdict K-2). `MARKETING_VERSION` and
   `CURRENT_PROJECT_VERSION` never reach the bundle.
4. **The Loop row's icon** (verdict K-6). It is an iOS 18-only SF Symbol in an
   app that targets iOS 17.
5. **"1 miles"** (verdict K-10).
6. **The published privacy page's "three small settings" list**, which is
   false (verdict AR-3, text only). It is in scope only because item 2 has to
   edit the same page.

**Out of scope, deliberately.** Each of these needs an owner decision or is
larger work, and is being handled elsewhere:
- App Review notes and the out-of-region server copy (AR-1).
- The winter road-closure mask (C-1).
- Recording consent (AR-2).
- Hiding the in-drive rating buttons (AR-4).
- The dial headline's wording (C-3).
- A "Clear recent destinations" control.
- The capacity and lock changes (K-1).
- Dynamic Type (K-5).

Do not start any of them here.

---

## 1. On a loop, "Switch to fastest" goes to the far point, not home

**Measured** on a local server with the New England build, on six 60 km
loops (Stowe VT, Concord MA and four seeded random starts). From a point 8 km
into the loop:
- **What the app asks for** (`via` the turnaround, `pref=0`) comes back as
  **47–73 km / 47–59 min**.
- **The fastest way home** from the same point is **7.3–8.2 km / 8–14 min**.

So the app's route is **4.4–6.3 times longer** than the fastest way home. The
driver taps the bolt button and confirms *"Switch to the fastest route? … This
gives up the scenic route for the rest of the drive."* (`NavView.swift:149-158`),
then gets sent to the far point by fast roads.

**Mechanism** (`ios/Sources/NavigationModel.swift` at `d4265d2`):
- `switchToFastest` (`:1279-1320`) sets `followingFastest = true`, sets
  `pref = 0`, and calls `reroute(from: location, reason: "fastest")`. It
  restores `followingFastest`, `pref`, `consecutiveReroutes` and
  `onRouteSince` on `.failed` or `.ended`.
- `reroute` (`:1331`) pins every request through the far point while a
  waypoint exists:
  ```swift
  if let via = loopWaypoint {                       // :1355
      reply = try? await fetchLoopResume(origin.coordinate, via, destination, …)
  ```
- `loopWaypoint` (`:310-313`) is non-nil until the far point is passed:
  ```swift
  guard let loop = loopTurnaround, !passedTurnaround else { return nil }
  ```
  `passedTurnaround` is declared at `:289`.

**The fix, which is decided.**
1. In `switchToFastest`, before the `reroute` call, save `passedTurnaround`
   and set it to `true`. That clears `loopWaypoint`, so the switch, *and every
   later off-route reroute*, goes home.
2. Restore the saved value in the existing `.failed, .ended` branch, next to
   the four values already restored there.
3. For a loop that has not reached its far point, change the confirmation to
   "Head home the fastest way?". Use a message such as "This ends the loop and
   takes the fastest route back to where you started." and a button
   "Head home".
4. Give the bolt button's accessibility label (`NavView.swift:370-373`) the
   same wording.
5. Expose what NavView needs as a read-only computed property on
   `NavigationModel`, for example `var isLoopBeforeFarPoint: Bool { loopWaypoint != nil }`.
   Leave the non-loop copy unchanged.

**Tests** go in `ios/Tests/LoopRerouteTests.swift`. Use its `Asked` counters
and `loopDrive(_:)` helper (`:45-75`). The counters exist because a stub's
`XCTFail` can land in another test.
- **The switch goes home.** Before the far point, `await nav.switchToFastest(from:)`
  reaches `fetchRoute` (plain = 1) and not `fetchLoopResume` (resume = 0).
- **It stays home.** After a successful switch, a later off-route reroute
  (`goOffRoute`) also reaches `fetchRoute`. Advance past the cooldown with the
  injectable `nav.now`.
- **A failure is undone.** Make `fetchRoute` throw. Then `passedTurnaround` is
  back to `false`, and the next off-route reroute reaches `fetchLoopResume`
  again.
- **Mutation check.** Remove the restore. The failure test must go red.

**Traps.**
- **Do not bypass `loopWaypoint` only when `reason == "fastest"`.** That looks
  like the minimal change and is wrong. The very next off-route reroute
  (`reason: "offroute"`) would see `loopWaypoint` again and drag the driver back
  to the far point they just declined. The decision has to live in state.
- **Do not set `passedTurnaround` permanently, even on failure.** A switch that
  never landed would turn every later loop rejoin into "the short way home",
  deleting the rest of the drive. That is the original loop-reroute bug
  (`LoopRerouteTests.swift:1-12`).
- `.superseded` deliberately leaves state alone (comment at `:1300`, case at
  `:1316`). Keep that.

---

## 2. Approximate location: zero fixes accepted, "50 ft away" forever

**Reproduced** in the simulator: iPhone 17 Pro, iOS 26.4. A scratch XCUITest
drove Settings and the app. The drive was Northampton → Amherst, with the
simulator moving along it at 15 m/s
(`xcrun simctl location <udid> start --speed=15 42.3190,-72.6310 42.3375,-72.5880 42.3490,-72.5480 42.3700,-72.5200`).
- **Precise Location on (the control):** the banner gave turn instructions,
  and the footer said "Recording this drive".
- **Precise Location off** (Settings → Privacy & Security → Location Services
  → Sunday Drive, value 1 → 0): after 25 s of moving, the screen still said
  **"50 ft away · Head to the start of your route"** and **"No GPS fixes yet —
  nothing is being recorded."**

`docs/privacy-policy.md` §2.2 (`:193-198`) and §7 item 6 (`:305-308`), and
`docs/release-plan.md` §10, list this path as an open gate: "untested". It is
now tested, and it fails.

**Mechanism.**
- `LocationManager.isUsable` rejects any fix worse than 65 m
  (`ios/Sources/LocationManager.swift:40`, `:127-131`):
  ```swift
  location.horizontalAccuracy > 0
      && location.horizontalAccuracy <= usableAccuracy      // 65 m
  ```
- An approximate grant reports kilometres, so `didUpdateLocations`
  (`:283-289`) never calls `onFix`, and `NavigationModel.update` never runs.
- `distanceToRouteStart` keeps its initial `0` (`NavigationModel.swift:120`).
  The banner prints it through `distanceText`, which floors at 50 ft
  (`NavView.swift:186`, `:512-518`), hence a confident "50 ft away" with no
  position at all.
- `lastFixAt` (`NavigationModel.swift:687`) stays `nil`. That is the clean
  signal for "no accepted fix yet".
- Nothing in `ios/` reads `accuracyAuthorization`, calls
  `requestTemporaryFullAccuracyAuthorization`, or declares
  `NSLocationTemporaryUsageDescriptionDictionary` (`git grep` is empty).
- **Planning has the same hole.** `currentLocation()`'s timeout returns the
  best coarse fix it saw (`LocationManager.swift:204-210`), so "My Location"
  can plan a loop from kilometres away.

**The fix, which is decided.**
1. **`ios/project.yml` `info.properties`.** Add
   `NSLocationTemporaryUsageDescriptionDictionary` with one key, `Navigation`.
   Suggested text: *"Turn-by-turn guidance needs your precise location to
   follow the route."*
2. **`LocationManager`.**
   - Publish `accuracyAuthorization`, read in `init` and in
     `locationManagerDidChangeAuthorization` (`:292-297`).
   - In `start()` (`:143-154`) and in `currentLocation()` (`:179-213`), when
     it is `.reducedAccuracy`, call
     `manager.requestTemporaryFullAccuracyAuthorization(withPurposeKey: "Navigation")`.
3. **The NavView banner** (`:167-192`).
   - Add a branch after the "Location is off" one: if accuracy is still
     reduced, show `over: "Precise Location is off"` and
     `main: "Turn it on in Settings to navigate"`, styled like the existing
     denied-location banner. Text only. Do not add a tap target to a
     driving banner.
   - In the `!nav.hasJoinedRoute` branch, when `nav.lastFixAt == nil`, show
     "Waiting for GPS" instead of a distance.
4. **Docs.** Update `docs/privacy-policy.md` §2.2 and §7 item 6 to say what
   the app now does. Add one factual sentence to `site/privacy/index.html` near
   `:89`: if Precise Location is off, the app asks to use precise location for
   the drive, and cannot navigate without it. `tests/test_privacy_page.py` must
   stay green.

**Tests.** `CLLocationManager` cannot be driven in a unit test, so test what
can be:
- **The no-fix banner.** With a `NavigationModel` that has received no
  `update`, the view's choice is "Waiting for GPS". Factor the over-text into
  something testable, such as a small pure function in NavView or a computed
  property on the model.
- **Accuracy reaches the banner.** The published accuracy state drives the
  banner choice, through the same kind of seam `authorizationResolved`
  (`LocationManager.swift:305-314`) uses for status.
- **One manual check in the simulator**, the way the repro above did it:
  Precise off, then start a drive. Expect the system prompt for temporary
  precise location. Allow it, and fixes flow. Decline it, and the banner reads
  "Precise Location is off".

**Traps.**
- **Do not loosen `usableAccuracy` (65 m) to let coarse fixes in.** It is
  load-bearing. A kilometre-wide fix sits far past `offRouteCertainMeters`
  (200 m), so every fix would read as off-route and reroute. Arrival and step
  advance would act on noise. The 65 m gate is what ended the reroute storms
  in `docs/reroute-audit.md`. The fix is "get precise, or say so", never
  "accept coarse".
- **Edit `ios/project.yml`, not `ios/Generated/Info.plist`.** The plist is a
  gitignored output that `xcodegen generate` overwrites. A purpose key added
  there vanishes on the next generate, and
  `requestTemporaryFullAccuracyAuthorization` with an unknown purpose key fails
  silently.
- `distanceToRouteStart == 0` is not a "no fix" test. A driver who really is
  at the start also reads near 0. Use `lastFixAt == nil`.

---

## 3. `MARKETING_VERSION` and `CURRENT_PROJECT_VERSION` do nothing

**Verified.**
- `ios/Generated/Info.plist` (from `xcodegen generate`) carries the literals
  `CFBundleShortVersionString = 1.0` and `CFBundleVersion = 1`. Those are
  XcodeGen's defaults, written because `info.properties` does not set them.
- `xcodebuild build … MARKETING_VERSION=9.9 CURRENT_PROJECT_VERSION=42`
  produces an app whose `Info.plist` still reads `1.0` / `1`.
- All twelve August drive traces record `"app": "1.0"`, while `project.yml`
  said `"0.1"` until `fbffba2`.

Consequence: the *second* App Store Connect upload (a fixed build after a
rejection, or a launch-week hotfix) carries `1.0 (1)` again.

**Fix.** Under `info.properties` in `ios/project.yml` (`:15-70`), add:
```yaml
CFBundleShortVersionString: $(MARKETING_VERSION)
CFBundleVersion: $(CURRENT_PROJECT_VERSION)
```
Then regenerate. **Verify** by building with the two overrides and reading the
built app's plist: `/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" -c "Print :CFBundleVersion" <DerivedData>/…/SundayDrive.app/Info.plist`.
Expect `9.9` / `42`, then `1.0` / `1` without the overrides.

**Trap.** Do not "fix" this by editing the generated plist. It is gitignored
and regenerated.

---

## 4. The Loop row's icon does not exist on iOS 17

`HomeView.swift:33` uses `"arrow.trianglehead.clockwise"`. Apple's own table,
`/System/Library/CoreServices/CoreGlyphs.bundle/Contents/Resources/name_availability.plist`,
dates it to iOS 18.0. The app targets iOS 17.0 (`ios/project.yml:5`). On iOS 17
`Image(systemName:)` renders nothing, so the first screen's Loop row shows an
empty amber square. All 31 other symbol literals in `ios/Sources` exist on
iOS 17.

**Fix.** Keep the designed symbol on iOS 18 and later, and fall back on
iOS 17:
```swift
if #available(iOS 18, *) { "arrow.trianglehead.clockwise" } else { "arrow.clockwise" }
```
Use it in a small computed property feeding `intentRow`. One line of
behaviour, with no visible change on iOS 18 and later.

---

## 5. "1 miles of it beautiful"

- `LoopView.swift:148`: `Text("\(meta.beautiful_km.wholeMilesFromKm) miles of it beautiful")`.
  A short loop reads "1 miles" (seen on screen).
- `DirectionsView.swift:249` (the dial's VoiceOver value) has the same
  `"\(miles.scenic) miles of beautiful road"`.

**Fix.** Pluralise both, either with a two-line helper or with SwiftUI's
`^[\(n) mile](inflect: true)`. Do not touch the `"… mi"` abbreviations, which
have no plural.

---

## 6. The privacy page's "three small settings" is false

`site/privacy/index.html:78-83` says: *"Besides drive recordings (below), the
app keeps three small settings for itself"*, then lists the voice, voice
durations and mute. At `d4265d2` the app also keeps:
- **The last five searched destinations, with names and coordinates.** These
  are `recentDestinations`, at `Recents.swift:13-50`, written by
  `RouteModel.swift:182-189`.
- `lastLoopTargetKm` (`LoopModel.swift:52`).
- `hasSeenBeforeYouDrive` (`PlanningView.swift:47`).
- `matchSystemAppearance` (`ContentView.swift:23`).

`docs/privacy-policy.md:76-84` has the same three-row table.

**Fix, text only.** Make both lists say what is stored, in plain words. For
example: "your five most recent destinations, so the home screen can offer them
again". Also change "Reset the three stored settings" in both §5 lists
(`privacy-policy.md:253`, `index.html:121`) to "Reset these".

**Trap.** Do **not** add a "Clear recent destinations" control here. Where it
lives is an owner decision and is out of scope. Describe what the app does
today.

---

## Building and testing

- **Work on your own branch, off `main`, never on `main`.** Do not push or
  merge. The master session reviews and merges. This brief is untracked where it
  was written: copy it into your worktree at `docs/pre-submission-fixes-brief.md`
  and commit it with the change. Do not edit `docs/README.md`, because another
  worktree has uncommitted edits to it.
- **`.venv` and `data/` exist only in the main checkout** (`<main>` is the
  first line of `git worktree list`). Use `<main>/.venv/bin/python`.
- **Backend suite** (items 2 and 6 touch `site/` and `docs/`, and
  `tests/test_privacy_page.py` reads the page):
  `SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python -m pytest -q tests > log 2>&1`.
  It gave 388 passed on `6f26edf`; `main` has added no backend tests since.
- **iOS.**
  1. `cd ios && xcodegen generate`. The xcodeproj is gitignored, and you must
     regenerate after editing `project.yml`.
  2. Create your own simulator:
     `xcrun simctl create "<name>" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-4`,
     then `xcrun simctl boot <udid>`. Pass `-destination 'id=<udid>'`, because
     a device name is rejected. Delete the simulator when done.
  3. Start a local server on a free port, **not 5057**:
     `PORT=<port> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python server/serve.py`.
  4. Run `TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:<port> xcodebuild test -project SundayDrive.xcodeproj -scheme SundayDrive -destination 'id=<udid>' > log 2>&1`.
     Put `TEST_RUNNER_` in the environment, not as a build-setting argument.
     With 5057 empty, a missed override shows up as 7 `LiveDriveTests` skips.
  - **Never pipe `xcodebuild` through `tail` or `grep`.**
  - If `VoiceCatalogueTests` hangs, add
    `-skip-testing:SundayDriveTests/VoiceCatalogueTests` and say so.
  - `main` now includes `SimulatedDrive*` and `SimulatorScreenDriveTests`
    (`2c49e5c`, `1e25472`). Run the whole suite, and record the new count.
- **Running the unit tests writes into the real app's container**
  (`lastLoopTargetKm = 5` and fake traces). Uninstall the app before any
  manual check or screenshot.
- **XCUITest can tap in the simulator** if you want the manual check of item 2
  automated. Use a scratch copy of `ios/` with an added `bundle.ui-testing`
  target, kept out of the repo. For Settings
  (`XCUIApplication(bundleIdentifier: "com.apple.Preferences")`):
  - search does not index the app on iOS 26, so go Privacy & Security →
    Location Services → Sunday Drive
  - a plain `.tap()` on the Precise switch does not flip it, so tap
    `coordinate(withNormalizedOffset: CGVector(dx: 0.93, dy: 0.5))`

## Done looks like

1. **Item 1.** The three new `LoopRerouteTests` pass, and the failure one goes
   red with the restore removed. The loop confirmation reads "Head home the
   fastest way", and the non-loop copy is unchanged.
2. **Item 2.** With Precise Location off, starting a drive shows the system
   prompt.
   - Allowing it delivers fixes.
   - Declining it shows "Precise Location is off · Turn it on in Settings to
     navigate".
   - A drive with no accepted fix never shows a distance.

   `privacy-policy.md` §2.2 and §7 item 6 describe this. `usableAccuracy` is
   still 65 m.
3. **Item 3.** A build with `MARKETING_VERSION=9.9 CURRENT_PROJECT_VERSION=42`
   ships `9.9 (42)`, and the default build ships `1.0 (1)`.
4. **Items 4 and 5.** The Loop row uses the fallback symbol below iOS 18, and
   "1 mile" reads correctly in both places.
5. **Item 6.** Both privacy lists match what `ios/Sources` stores, and
   `tests/test_privacy_page.py` passes.
6. **The suites.** Backend green. iOS green, with `LiveDriveTests` passing
   against your server. Report the new iOS test count.
7. **The commits.** One commit per item, each naming the verdict ID (K-7,
   §6.2, K-2, K-6, K-10, AR-3), on your branch, unmerged.

If an item turns out not to be as described here, stop that item and write
down what you found instead of improvising. For example, XcodeGen might not let
`info.properties` override `CFBundleVersion`.
