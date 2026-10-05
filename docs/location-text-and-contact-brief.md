# Brief: a complete location permission text, and a way to contact the developer from inside the app

**Status: diagnosed and decided, not fixed.** Written 2026-10-04 against `main`
at `8e4e5c7`. No source file has been touched for this brief. Every `file:line`
below is at that SHA. A parallel session is working from
`new-england-only-brief.md`. Read its "Files" section so the two of you never
edit the same file.

## The two gaps, against the App Review Guidelines (June 8, 2026 text)

### 1. The permission text describes one use of location, and the app has more

Guideline 5.1.1(ii): *"Ensure your purpose strings clearly and **completely**
describe your use of the data."*

The string is at `ios/project.yml:36`:

> Your location is used to follow the route, turn by turn, while you drive.

The system prompt usually appears first while **planning**, not driving:
- Home's Loop row calls `LoopModel.useMyLocation` (`HomeView.swift:40`), which
  calls `locationManager.currentLocation()` (`LoopModel.swift:153`).
- My Location in Directions does the same through `RouteModel.swift:207`.
- Both reach `requestWhenInUseAuthorization` when permission is undetermined
  (`LocationManager.swift:225-226`, then `:287`).
- Starting a drive asks too (`NavView.swift:100` and `:129` call
  `LocationManager.start()`, which reaches `:182`).
- **After the parallel brief lands, there is a fourth trigger:** the app asks
  once at first launch, right after the "Before you drive" notice, so that it
  can warn someone outside New England.

What location is actually used for:

| Use | Where it goes | Evidence |
|---|---|---|
| Planning a drive or loop from where you are | To the routing server, in a POST body | `RouteService.swift`; privacy page "Where your location goes", item 1 |
| Checking whether you are in New England | **Nowhere.** The parallel brief requires the check to run on the phone with no network call | `new-england-only-brief.md` §A and its trap 4 |
| Turn-by-turn guidance, including in the background with the blue indicator | Stays on the phone, apart from reroutes, which go to the server as above | `LocationManager.swift:195-196`; privacy page "Location" |
| Naming the start ("My Location" becomes a street) | To Apple, by reverse geocoding | `PlaceNaming.swift:45-46` (`CLGeocoder`); privacy page "Where your location goes", item 2 |

### 2. There is no way to contact the developer from inside the app

Guideline 1.5: *"Make sure your app **and** its Support URL include an easy way
to contact you."*

The Support URL page does this already. `site/index.html` lists
`support@jameskouvlis.com`, and `tests/test_support_page.py:41-42` asserts the
`mailto:` link.

The app does not. Its only outward link is the privacy policy
(`AboutView.swift:302-319`, URL constant at `:217-219`). The Sources screen is
reached from the pinned "Sources ›" credit line on every planning stage
(`PlanningView.swift:160-186`).

## The published privacy policy repeats the incomplete claim

The privacy policy repeats the claim, in three places:
- `site/privacy/index.html:90` says *"The app uses your location for one thing:
  following the route you asked for."*
- `:91` quotes the string above, verbatim, in a `<blockquote>`.
- The summary bullet at the top says *"Your location is used to follow your
  route."*

`docs/privacy-policy.md` §2 (`:84-90`) says the same, and cites
`ios/project.yml:21` for the string. That citation is stale: the string is at
`:36`.

**This is incomplete today, before any new feature.** Planning from where you
are is already a second use. Guideline 5.1.1(i) asks the policy to identify
"all uses of that data".

## What was decided (master session, 2026-10-04)

### A. The new permission text

> **Your location is used to plan drives from where you are, to check that
> you're in New England, and to guide you turn by turn.**

The owner may reword it. Whatever the wording, it must:
- name all three uses;
- **not name the app.** iOS already titles the alert *Allow "Sunday Drive" to
  use your location?*, and naming it in the body says it twice. That was
  decided on 2026-09-20 and is recorded in `docs/privacy-policy.md` §2;
- stay a single sentence that a driver reads in two seconds.

**Change only `NSLocationWhenInUseUsageDescription`.** Leave
`NSLocationTemporaryUsageDescriptionDictionary` (`ios/project.yml:42-43`, the
Precise Location prompt) exactly as it is.

### B. The privacy policy, in step

In `site/privacy/index.html` and `docs/privacy-policy.md` §2:
- Replace "for one thing: following the route you asked for" with the three
  uses.
- Say plainly that the New England check happens on the phone and sends the
  location nowhere.
- Update the blockquote to the new string, character for character.
- Update the summary bullet at the top of the page.
- Fix the stale `:21` citation.
- Move the page's "Effective date" to the day this merges.

"Where your location goes" stays at two places. The check adds no destination.

### C. The contact route

In `AboutView.swift`, add two rows right after the "Privacy policy" row, in the
same style: a 50 pt row on `Color.sunk`, with an `arrow.up.right` glyph.
- **"Help and support"** opens the support page,
  `https://jamesk1281.github.io/SundayDrive/`.
- **"Email the developer"** opens `mailto:support@jameskouvlis.com`.

Put both URLs in a small enum next to `PrivacyPolicy` (`AboutView.swift:217-219`).
Copy its warning: Pages does **not** redirect after a repo rename, so renaming
the repo breaks these links.

### D. Guards against drift

- **A Python test** in `tests/test_privacy_page.py` that reads
  `NSLocationWhenInUseUsageDescription` out of `ios/project.yml` and asserts
  that the privacy page's blockquote is exactly that string. This is the
  failure that just happened: the string and the policy describe the app
  differently, and nothing noticed.
- **An iOS unit test** that reads the string from the built bundle
  (`Bundle.main.object(forInfoDictionaryKey:)`, the pattern at
  `LocationManagerTests.swift:186-192`). It asserts the string is non-empty and
  does not contain "Sunday Drive". It also asserts the two new URL constants:
  the scheme, the host, and the address in the `mailto:`.

## Files

**You may edit:**
- `ios/project.yml` (that one key only);
- `ios/Sources/AboutView.swift`;
- a new test file under `ios/Tests/`, or `AttributionTests.swift`;
- `site/privacy/index.html`, `docs/privacy-policy.md` and
  `tests/test_privacy_page.py`.

**Do not edit:**
- the parallel session's files: `Region.swift`, `SearchCompleter.swift`,
  `RouteModel.swift`, `LoopModel.swift`, `LocationManager.swift`,
  `ContentView.swift`, `HomeView.swift`, `LoopView.swift`, `Recents.swift`,
  `site/index.html` and `docs/app-store-submission.md`;
- the files the three finished-but-unmerged branches touch:
  - `PlanningView.swift` and `PlanningMap.swift` (map framing);
  - `DirectionsView.swift` and `RouteResults.swift` (C-3);
  - `BeforeYouDriveView.swift` and `server/app.py` (C-1, seasonal closures);
- `docs/README.md`.

## Traps

1. **The policy quotes the string verbatim.** Change `ios/project.yml` without
   `site/privacy/index.html` and the published policy misquotes the app. The
   test in D exists so this cannot happen twice.
2. **Editing `ios/Generated/Info.plist` does nothing.** `xcodegen generate`
   rewrites it from `ios/project.yml`. Regenerate before building, or the
   simulator still shows the old prompt.
3. **Leave the precise-location purpose alone.** Its dictionary key
   `Navigation` must match `LocationManager.precisePurposeKey`
   (`LocationManager.swift:66`). A purpose that CoreLocation cannot find shows
   no prompt and gives no error.
4. **Do not put the contact link in the planning page's credit line.**
   `PlanningView.swift` is being rewritten on the framing branch. The credit
   line also carries the OpenStreetMap attribution, under its own placement
   rules (`PlanningView.swift:139-159`).
5. **Use `Link` with a `mailto:` URL, not `MFMailComposeViewController`.** On a
   phone with no Mail account, iOS offers to restore Mail, which is why the
   support-page row exists too. The composer needs MessageUI and fails the same
   way with no account configured.
6. **"Check that you're in New England" describes the parallel branch's
   feature.** If this branch merged alone, the policy's "on the phone, sent
   nowhere" sentence would describe a check that does not exist yet. The master
   session will merge the two together, or this one second. Do not add a code
   dependency on the other branch.
7. **Both addresses live on `jameskouvlis.com`, which expires 2026-10-28 unless
   the owner renews it.** That is the owner's action, not code. Do not add a
   fallback address on another domain without asking him.
8. **The repo is public.** No absolute home-directory paths in anything you
   commit.

## Done looks like

1. On a fresh simulator install, the system location prompt shows the new text.
   A screenshot goes in the report.
2. Sources shows "Help and support" and "Email the developer" after "Privacy
   policy". The first opens the support page. The second's URL is asserted by a
   unit test, since the simulator has no Mail.
3. `site/privacy/index.html` and `docs/privacy-policy.md` describe all three
   uses, quote the new string exactly, and carry the new effective date.
4. `tests/test_privacy_page.py`, including the new drift test, and
   `tests/test_support_page.py` pass. So does the iOS suite.
5. Committed on your own branch off `main`, with this brief, and not merged.

**Out of scope:**
- **Renaming "Sources ›" to something like "About ›"**, so that people looking
  for help find it: the label lives in `PlanningView.swift`, which the framing
  branch owns. It is a follow-up.
- **App Store Connect fields:** the nutrition label is unchanged, because
  location was already declared collected for App Functionality.
- **The support page's own content:** the parallel brief corrects its Loop line.

## Build and test

- Work on your own branch off `main`. Commit this brief with the change.
- `.venv` lives only in the main checkout, written `<main>` here.
- Run the site tests with `<main>/.venv/bin/python -m pytest -q
  tests/test_privacy_page.py tests/test_support_page.py > out.txt 2>&1; echo $?`.
  Never pipe pytest or `xcodebuild` through `tail`, because the exit code is
  lost.
- Run `xcodegen generate` in `ios/` after editing `project.yml` or adding a
  Swift file.
- Create your own simulator:
  - `xcrun simctl create <name> com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-4`
  - then pass `-destination id=<udid>` to `xcodebuild`.
- For the live tests, point `TEST_RUNNER_SUNDAYDRIVE_API` at a local server on
  a free port, never 5057. Start the server with
  `PORT=<port> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python server/serve.py`.
- To see the permission prompt again, erase the simulator or uninstall the
  app. A fresh install opens on the "Before you drive" notice.
