# Brief: make it impossible to use the app without knowing it only works in New England

**Status: diagnosed and decided, not fixed.** Written 2026-10-04 against `main`
at `8e4e5c7`. No source file has been touched for this brief. Every `file:line`
below is at that SHA. Do not re-derive the diagnosis; do check the arithmetic
before you build on it.

## The goal, in the owner's words

> "ensure there are no mistakes when using the app that it only functions for
> new england. start the map zoomed in on new england. maybe even request the
> users location upon start and just give them a big warning if they are
> outside of NE that THIS WONT WORK. definitely make sure the only streets that
> can come up in the search are in new england."

Three parts, in the order he weighted them:
1. **Search returns only New England places.** He said "definitely".
2. **A big, unmissable warning when the phone is outside New England**, with a
   location request at launch to make that possible.
3. **The map opens on New England.**

## What is already true

**The map already opens on New England.** `PlanningView.swift:38` is
`@State private var camera: MapCameraPosition = .region(.newEngland)`, and
`Region.swift:14-27` defines that box: centre 43.6, -71.3, span 6.4° by 6.4°,
documented as "the opening map camera, and nothing else".

The box probably does not show all six states, though. This is arithmetic, not
a measurement, so check it on a simulator:
- Latitude runs 40.4 to 46.8. Fort Kent, ME (47.25) and the top of Aroostook
  County are north of it.
- Longitude runs -74.5 to -68.1. Lubec, ME (-66.98) is east of it. The card is
  wider than it is tall, so MapKit will probably widen the longitude and show
  Lubec anyway. Latitude has no such slack.
- The card runs under the status bar (`PlanningView.swift:78`), so the top of
  the box sits under the clock.

## The diagnosis: where out-of-region use gets through today

**Measured on production, 2026-10-04.** A loop requested from Cupertino
(37.3349, -122.0090) returns HTTP 400 in 0.13 s, with the body
`{"error":"point is outside the covered road network (currently New England)"}`.
The app shows that string verbatim (`RouteService.swift:71`). It is what a
reviewer outside New England sees on tapping Loop.

There are five ways through:

1. **Search is ranked, never filtered.** `SearchCompleter.swift:23` and `:39`
   set `completer.region`, which on iOS 17 is a ranking bias only. Results from
   anywhere in the world come back and are all shown:
   `completerDidUpdateResults` at `:51-53` copies `completer.results` with no
   filter, and `PlaceField.swift:98` shows the first five.
2. **The bias follows the user out of the region.** `PlanningMap.swift:71-74`
   sets `searchRegion` to whatever the map is showing. `RouteModel.swift:219`
   and `LoopModel.swift:162` set it to a 30 km box around the phone after
   My Location. Someone in Cupertino who taps the map's locate button, or
   My Location, gets suggestions ranked around Cupertino.
3. **Resolving takes the first hit, wherever it is.** `RouteModel.swift:169`
   and `LoopModel.swift:129` use `result.mapItems.first`. A typed name that
   exists in several states becomes whichever one Apple ranks first. Portland,
   Concord, Manchester, Salem, Springfield and Burlington are where to look.
   *That is a hypothesis: confirm it with real queries from a Cupertino
   location before writing the test.*
4. **My Location and Loop send an out-of-region fix straight to the server.**
   `RouteModel.useMyLocation` (`:203`) and `LoopModel.useMyLocation` (`:149`)
   set the start to the fix and plan. Home's Loop row calls the second one with
   no form in between (`HomeView.swift:31-42`), as does tapping a recent
   destination (`HomeView.swift:116-117`).
5. **The support page is wrong about Loop.** `site/index.html:81` says
   "**Loop** and **My Location** only work when you are in New England". But
   Loop takes a typed start: `LoopView.swift:30` is a `PlaceField` labelled
   "Start and finish here", wired to `LoopModel.search`/`choose`. A typed
   New England town works from anywhere, in both Directions and Loop.

## What was decided (master session, 2026-10-04)

Build all of this. The owner said "maybe" about the launch request. It was
taken as a yes, sequenced so it is safe in App Review.

### A. One on-device test: "is this point in New England?"

- **The data source is US Census cartographic boundaries**, which are public
  domain:
  `https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip`
  (3.2 MB, checked reachable on 2026-10-04).
- Take the union of CT, ME, MA, NH, RI and VT. Simplify it to about 0.002–0.005°
  and buffer it outward by about 500 m, so piers, causeways and coastal fixes
  count as inside.
- Keep the islands that have roads:
  - Nantucket, Martha's Vineyard and Block Island;
  - Aquidneck and Conanicut;
  - Mount Desert, Deer Isle and Vinalhaven;
  - Peaks Island;
  - the Lake Champlain islands.
- Generate a Swift source file with a header naming the source, the vintage,
  the tolerance, the buffer and the script.
- Commit the script under `tools/` so the file can be rebuilt. `geopandas`,
  `shapely` and `pyogrio` are in `<main>/.venv`.
- Keep the generated file reasonably small: under about 100 KB. Point-in-polygon
  over a few thousand vertices takes microseconds.
- **No network.** The check runs on the phone and sends the coordinate nowhere.
  The parallel privacy-text brief (`location-text-and-contact-brief.md`)
  describes it that way in the published privacy policy.

### B. Search: show and accept only New England places

Defence in depth, because no single MapKit setting covers it on iOS 17:

1. **Clamp the bias region.** In `SearchCompleter.update` and in both models'
   `search()`, if the bias region's centre is outside New England, or its span
   is wider than New England, use the New England *envelope* (C below).
   Otherwise keep the existing tight bias. Ranking near the user is
   deliberate, for the reason given at `Region.swift:29-34`.
2. **Restrict on iOS 18 and later, only when the bias is outside.**
   `regionPriority` exists from iOS 18.0 only (checked in the iOS 26.4 SDK:
   `MKLocalSearchCompleter.h:40` and `MKLocalSearchRequest.h:32`, both
   `API_AVAILABLE(ios(18.0))`). The deployment target is iOS 17.0, so gate it
   with `if #available(iOS 18, *)`. When the bias was clamped to the envelope,
   set `.required`. Otherwise leave `.default`.
3. **Filter suggestions by the state they name, on every iOS version.** A
   completion has no coordinate, only `title` and `subtitle`. Drop a suggestion
   whose subtitle names a US state outside the six, or a Canadian province. Keep
   one that names one of the six, or names no state at all; step 4 catches what
   gets through. Filter **before** `prefix(5)`, or out-of-region rows push good
   ones off the list.
4. **Gate at resolve time, on every iOS version. This is the hard guarantee.**
   In both `resolve()` functions, take the first map item that is inside the
   polygon. When `placemark.administrativeArea` is present, also require it to
   be one of `CT ME MA NH RI VT`. If no item passes, set:
   `"<label>" isn't in New England. Sunday Drive only covers the six New England states.`
   Never take an out-of-region item.
5. **Filter Recents on load** (`Recents.swift`) to points inside the polygon,
   so an old entry cannot route somewhere the server will refuse.

`placemark` is deprecated in the iOS 26 SDK (`MKMapItem.h:28`) but still
works. The code already reads it at `RouteModel.swift:173`, `:184` and
`LoopModel.swift:133`. Follow the existing code rather than migrating in this
change.

### C. A separate envelope region for search

Add `MKCoordinateRegion.newEnglandEnvelope`, built from the six-state bounds
plus a small margin. The pipeline's envelope is `pipeline/elevation.py:34`,
`BBOX = (-73.76, 40.93, -66.87, 47.47)`. Leave `.newEngland` as the camera box,
as its doc comment insists. Adjust `.newEngland` itself only for the camera fix
in E.

### D. The warning: big, honest, and never a blocker

**When it appears:**
- **First launch only:** after "Before you drive" is acknowledged
  (`hasSeenBeforeYouDrive` becomes true), request when-in-use authorisation once.
- **Every cold launch, if location is already granted:** take a fix quietly.
- If the fix is outside the polygon, show the warning once for that launch,
  not again on returning from the background.
- If permission is denied or not yet determined after the first launch, do
  nothing at launch. The existing My Location paths still ask.

**Suggested copy, which is the owner's to edit.** It keeps his words in the
headline:

> **This won't work from here**
>
> Sunday Drive only covers the six New England states: Connecticut, Maine,
> Massachusetts, New Hampshire, Rhode Island and Vermont. You're outside them,
> so Loop and My Location can't plan a drive from where you are.
>
> You can still plan a drive there: type a New England town, like Stowe, VT,
> as your start.
>
> **[Got it]**

It must be big and unmissable: a sheet or a full-screen cover, with a large
bold headline. All-caps body text hurts readability and VoiceOver, so put the
caps feeling in the headline's weight and size, not in capital letters. **It
must be dismissible, and planning from a typed start must keep working.**
Guideline 3.2.2(v) treats "arbitrarily restricting who may use the app, such as
by location" as unacceptable. And a person planning a trip to New England is
part of the audience.

**Everywhere else a fix arrives outside:**
- `RouteModel.useMyLocation` and `LoopModel.useMyLocation` check the fix before
  setting the start. Outside, they set a short inline `errorText` (e.g. "You're
  outside New England, so this can't start from your location. Type a New
  England town as your start.") and **make no server request**.
- Home's Loop row: while the last known fix is outside, the subtitle reads
  "Type a New England town to start" instead of "From here, about …". Tapping
  the row opens the loop stage with the start field focused, instead of
  calling `useMyLocation`.

Keep the result in one place, such as an inside/outside/unknown status on
`RouteModel`. Every fix updates it: the launch check, both My Location paths,
and the Loop row.

### E. The opening camera

Measure the opening map on the smallest supported simulator (iPhone SE, 3rd
generation) and on an iPhone 17 Pro Max. If any of the six states is cut off,
or sits under the status bar, adjust **only the `.newEngland` constant** in
`Region.swift`, by shifting its centre north and/or growing its span. Fort Kent,
Lubec, Greenwich CT and Nantucket are the corners to check. Do not edit
`PlanningView.swift`; see "Files" below.

### F. The words around it

- Fix `site/index.html:81`: Loop and Directions both take a typed New England
  start from anywhere, and only My Location needs you to be there.
  `tests/test_support_page.py` must stay green.
- Update `docs/app-store-submission.md` §5, the "Why does it only work in
  New England?" notes at `:344-356`. Describe the launch warning. Give the
  reviewer both entry points: Directions **Concord, MA → Rockport, MA**, and
  Loop with **Stowe, VT** typed into "Start and finish here".

## Files

**Three finished branches sit unmerged and touch files near this work.**
Editing the same files here would conflict on merge:

| Branch | Touches |
|---|---|
| `claude/strange-dewdney-4a01fd` (map framing) | `PlanningView.swift`, `PlanningMap.swift` (rewrites `refit` and the camera state) |
| `claude/jolly-easley-2a7ea1` (C-3) | `DirectionsView.swift`, `RouteResults.swift` |
| `claude/inspiring-cannon-89c90c` (C-1, closures) | `BeforeYouDriveView.swift` (adds a "Seasonal roads." line after `:62`), `server/app.py` (hunks around the out-of-region error strings at `:262`, `:285`, `:350`) |

A parallel session (`location-text-and-contact-brief.md`) owns `ios/project.yml`,
`AboutView.swift`, `site/privacy/index.html` and `docs/privacy-policy.md`.

**You may edit:**
- `Region.swift`, `SearchCompleter.swift`, `RouteModel.swift`, `LoopModel.swift`,
  `LocationManager.swift`, `ContentView.swift`, `HomeView.swift`, `LoopView.swift`
  and `Recents.swift`;
- new Swift files and new test files;
- `site/index.html`, `docs/app-store-submission.md` §5, and `tools/`.

**Do not edit:**
- the files in the table;
- the other session's files;
- `docs/README.md`. The master session indexes briefs at merge.

## Traps

1. **`regionPriority = .required` on the existing bias region is a 30 km hard
   limit.** `.around` (`Region.swift:35-38`) is 30 km across. Restricted to it,
   "Stowe, VT" typed in Boston returns nothing. Restricting to the envelope
   *everywhere* brings back the ranking bug that `Region.swift:29-34` and
   `RouteModel.swift:53-58` were written to kill. Hence the hybrid: restrict
   only when the bias is outside New England.
2. **A rectangle is not New England.** The `.newEngland` camera box leaves out
   Lubec and Fort Kent, so using it as the search restriction would hide parts
   of Maine. The envelope covers all of Maine but takes in Montauk NY, Sherbrooke
   QC and Edmundston NB. The polygon is the only containment test. Rectangles
   are for bias and restriction only.
3. **Do not reuse `currentLocation()` for the launch check.** It holds out for
   a fix of ≤65 m (`LocationManager.swift:76`, `:164-166`, `:242`). Worse, with
   Precise Location off it raises the temporary full-accuracy prompt
   (`:237-238`), "Turn-by-turn guidance needs your precise location", at launch
   with no drive in sight. A region check needs a fix to within kilometres. Add
   a separate method that accepts any recent fix and never asks for precision.
4. **Do not geocode for the region check.** `CLGeocoder` is a network call to
   Apple. It fails offline and is deprecated in iOS 26. The privacy text being
   written in parallel says the check stays on the phone.
5. **One sheet at a time.** On first launch `PlanningView.swift:82-85` presents
   the notice as a sheet with interactive dismiss disabled. Present the warning
   from `ContentView` only after the notice has been acknowledged *and has
   finished dismissing*. Otherwise SwiftUI drops one of the two presentations.
6. **Build the subtitle parser from captured strings, not imagined ones.** In
   the iOS 26.4 simulator, log `title` and `subtitle` for about ten queries from
   Boston and from Cupertino: Portland, Concord, Main Street, Times Square,
   Sherbrooke, Stowe, Albany, Montauk, plus a business and an address. Use those
   strings as the test fixtures. Match state codes as tokens. ", ME" is Maine;
   the letters "ME" inside a word are not. Country names are localised, so do
   not depend on "United States".
7. **Never block a typed start.** The warning informs. Typed New England starts
   must work from anywhere, for the reviewer and for trip planners alike.
8. **Do not embed Geofabrik's `.poly` files.** They are the server's real cut
   lines: the graph is built from six merged Geofabrik state extracts
   (`pipeline/elevation.py:31-34`), and the server accepts points within 5 km of
   a road (`server/app.py:89`, `SNAP_MAX_M = 5000.0`). But they are derived from
   OpenStreetMap, which would put ODbL data inside an Apache-2.0 source file.
   Census boundaries are public domain.
9. **Leave `server/app.py` alone.** Its out-of-region wording should improve,
   but C-1 rewrites the hunks around those lines. Once your client check exists,
   a reviewer never reaches that message: Loop and My Location stop before any
   request, and typed starts are inside by construction. The server wording is a
   follow-up after C-1 merges.
10. **The repo is public.** No absolute home-directory paths in anything
    committed, the generated file's header and the script included.

## Done looks like

1. A pure, unit-tested `contains(_:)` (or similar). Named points cover:
   - **inside:** Boston, Stowe VT, Fort Kent ME, Lubec ME, Bar Harbor ME,
     Greenwich CT, Nantucket, Block Island, Grand Isle VT, Pittsburg NH,
     Provincetown;
   - **outside:** Cupertino, Albany NY, Montauk NY, Sherbrooke QC, Plattsburgh NY,
     Edmundston NB;
   - plus a few points you confirm are within 1 km of a border, labelled as
     such.

   Choose "clearly outside" points at least 3 km from any border, and check
   their distances rather than trusting this list.
2. The suggestion filter and the resolve gate are pure functions with tests
   built from the captured strings (trap 6). On the iOS 26.4 simulator at
   Cupertino:
   - "Portland" suggests only Portland, ME;
   - "Times Square" and "Sherbrooke" suggest nothing;
   - a typed "Portland" submit resolves to Maine.

   At Boston, the top five for "Main Street" are unchanged from `main`.
3. The fresh-install flow at Cupertino (`xcrun simctl location <udid> set
   37.3349,-122.0090`) runs: notice → permission prompt → **This won't work from
   here** → Got it → Home's Loop row reads "Type a New England town to start".
   Loop, with Stowe, VT typed, draws a loop. Screenshots go in the report.
4. At Cupertino, My Location in both Directions and Loop shows the inline
   message, and **no request reaches the server**. Show it with a local server's
   log, or with a request count.
5. A fresh install at Boston shows no warning, and the Loop row behaves as on
   `main`.
6. The opening-camera measurement for both device sizes is in the report, with
   any `.newEngland` change.
7. `site/index.html` and `docs/app-store-submission.md` §5 are updated, and
   `tests/test_support_page.py` passes.
8. The iOS suite is green, with no live-test failures.
9. Committed on your own branch off `main`, with this brief, and not merged.

**Out of scope, and why:**
- **The server's out-of-region wording:** trap 9.
- **A warning on "Start driving" when the route starts thousands of miles
  away:** it belongs in `DirectionsView`, and C-3 owns that file. The driving
  screen already says "Head to the start of your route", and the review notes
  cover it. It is a follow-up.
- **Locking the map camera to New England** (`.mapCameraBounds`): it would mean
  editing `PlanningMap.swift`, and it makes the locate button look broken for
  someone outside. The bias clamp makes it unnecessary for search.
- **Raising the deployment target to iOS 18:** it would mean editing
  `ios/project.yml`, which the other session owns, and the `#available` branch
  costs one `if`.

## Build and test

- **Branch and data:**
  - Work on your own branch off `main`. Commit this brief with the change.
  - `data/` and `.venv` live only in the main checkout, written `<main>` here,
    not in a worktree.
- **Project setup:**
  - Run `xcodegen generate` in `ios/` after adding a Swift file. The
    `.xcodeproj` is gitignored, and a new file is otherwise "Cannot find type in
    scope".
  - Create your own simulator: `xcrun simctl create <name>
    com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro
    com.apple.CoreSimulator.SimRuntime.iOS-26-4`.
  - Use `-destination id=<udid>`, never `name=`.
- **Running the suites:**
  - Run `xcodebuild test` with `TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:<port>`
    pointing at a local server on a free port. Not 5057: another session may own
    it.
  - Never pipe `xcodebuild` or `pytest` through `tail`. Redirect to a file and
    `echo $?`.
- **Running a local server:** `PORT=<port> SUNDAYDRIVE_HOST=127.0.0.1
  SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python
  server/serve.py`. To point a simulator launch at it, use
  `SIMCTL_CHILD_SUNDAYDRIVE_API=…` with `simctl launch`.
- **Site tests:** `<main>/.venv/bin/python -m pytest -q tests/test_support_page.py
  tests/test_privacy_page.py`.
- **First launch:** a fresh install opens on the "Before you drive" notice.
  Erase the simulator, or uninstall, between first-launch runs.
