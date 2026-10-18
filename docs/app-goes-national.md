# The app goes national (unit C)

**Status:** built 2026-10-18 on `claude/app-goes-national`, cut from local
`usa` at 6fdf137. Not merged, not pushed, not deployed. `ios/` only. The New
England build on `main`, which TestFlight friends use, keeps its gating and is
not touched.

## 1. Earliest honest date

| What | Earliest | Depends on |
|---|---|---|
| iPhone build with the New England gate removed, the national edge handled, tests rewritten, suite run against a local server on `processed-ne` | **done 2026-10-18** (§5 has the result) | nothing outside `ios/` |
| Same suite against `processed-us` | **the day unit A delivers `data/processed-us`**, if a server can load it on this Mac | A, and B's router if today's cannot load the national graph |
| Release screenshots of drives outside New England | **the day a server answers for the whole country** | A and B |
| Owner sign-off on the new copy (§4) | his call; the copy is in the build | the owner |

The app is not on the critical path for Thursday 29 October. A and B are.

Until a national server exists, a national build pointed at today's New
England server is still honest. A start in Colorado gets the server's own
refusal ("point is outside the covered road network (currently New
England)"), which the app shows as written (`RouteService.failure(status:body:)`).

## 2. What changed

The gate was not widened to a bigger box. It was replaced by an outline of the
48 contiguous states and DC, and every check that used the New England outline
now uses that one.

| Was (on `main`) | Now (this branch) |
|---|---|
| `NewEngland.swift`, `NewEnglandBoundary.swift` (75 rings, 3,473 vertices) | `Coverage.swift`, `CoverageBoundary.swift` (346 rings, 20,169 vertices, 428 KB of source) |
| `tools/build_new_england_boundary.py` | `ios/scripts/build_coverage_boundary.py` (same source, same steps, same margins) |
| `OutsideNewEnglandView` | `OutsideCoverageView` |
| `MKCoordinateRegion.massachusetts`, `.newEngland`, `.newEnglandEnvelope` | `.coverageEnvelope` (search), `.coverage` (opening camera), `.home(around:)` (camera after the launch fix) |
| `NewEnglandTests`, `OutsideNewEnglandTests` | `CoverageTests` (31), `OutsideCoverageTests` (12) |

### 2.1 The outline

The Census Bureau's 2024 1:500,000 state boundaries are the same file and hash
as the New England outline (SHA-256 `3e81cbb6…71447bc`), public domain. The 48
states and DC are unioned, buffered 500 m, holes filled, simplified at 200 m
and rounded to 10 m. The generator refuses to write if the outline does not
contain the Census outline, or if any of 16 named inside points or 20 named
outside points lands on the wrong side. It took 3 min 25 s on this Mac, most
of it measuring.

Measured, and written into the generated header:
- The Census outline is at least **199 m** inside this one everywhere. That is
  less than New England's 292 m. The tightest spots are in the Florida Keys
  (25.03, −80.68) and on the Elizabeth Islands (41.42, −70.94), where
  topology-preserving simplification of neighbouring islands eats into the
  buffer.
- This outline strays at most **793 m** from Census land, against New
  England's 697 m.

**Cost of the test.** `contains` now indexes each ring's edges by band of
latitude, because the mainland ring has 15,779 vertices against New England's
~3,000. Measured in a Debug build on the iPhone 17 Pro simulator: 2,000 calls
at the busiest latitudes in 0.154 s. That includes building the index on first
use, so it is at most 77 µs a call. `CoverageTests.test_the_test_is_cheap`
fails above 500 µs. The build with the 428 KB literal took 73 s from clean.

### 2.2 The edges, and what each one does now

| Edge | How it is handled | Pinned by |
|---|---|---|
| **Canada**, by land and over water | Outside the outline. Search results over the line but inside the 500 m buffer (Stanstead QC at 370 m, Fort Frances ON at 80 m) are refused by their state. Suggestions with a province code are dropped. | `test_border_towns_on_the_far_side_are_outside`, `test_a_place_over_the_line_is_refused_by_its_state`, `test_a_place_in_canada_is_dropped`, the captured strings |
| **Mexico** | Outside the outline; Tijuana is 3.0 km over, Matamoros 1.3 km. Suggestions end "…, Mexico" or carry "BC" and are dropped. | as above, plus `test_national_captures_are_judged_right` |
| **Oceans, the Gulf, the Great Lakes, big bays** | Outside. The Census file clips the Great Lakes, Chesapeake Bay and Puget Sound out, and the buffer does not close them, so a phone on a Lake Michigan ferry is told it is outside. That is true of the roads too. | `test_open_water_is_outside` |
| **US places outside the 48** | Outside the outline. Suggestions with their codes are dropped, and so is a subtitle ending in their state's name with no code. | `test_a_us_place_outside_the_48_is_dropped`, captured strings |
| **Exclaves reached only through Canada** (Point Roberts WA, the Northwest Angle MN) | Inside: they are in a state. Whether a route can reach them is the server's to say (§3). | `test_the_places_only_reached_through_canada_are_inside` |
| **A phone just over a border** (Fort Frances, 80 m from the Census line) | Counts as inside for My Location, as Stanstead did around New England. The server decides what it snaps to (§3). | `test_a_place_over_the_line_is_refused_by_its_state` (precondition) |
| **A bare street address with no state** | Shown, and refused at resolve by coordinate and state, as before. Captured: an airport outside the 48 over "5000 W International Airport Rd", and "Windsor Detroit Tunnel" over "555 Goyeau St". | `test_a_bare_street_address_is_left_to_the_resolve_gate` |

**Two leaks found by capturing real strings**, which the New England rules
would have let through. On 2026-10-18 the iOS 26.4 simulator's completer was
ranked around San Diego and Detroit for 12 border and off-coverage queries,
and returned 272 rows. Both leaks are fixed and pinned:
- A city outside the 48 whose subtitle ended in its state's *name*, with no
  code.
- "San Juan, Argentina" over an empty subtitle. The country is in the title.

### 2.3 Search ranking

New England replaced any bias whose **centre** was outside with the envelope.
Nationally that would rank a search made over the Florida Keys, or over
Windsor with Detroit on screen, from the middle of Kansas. Now a bias is kept
if its centre or any point of a 5 × 5 grid across it is covered
(`Coverage.showsSomeOf`). Only a region that shows no covered land at all, such
as Toronto or the open Gulf, becomes the envelope. The envelope is still the
only region a typed search is restricted to.

### 2.4 The opening camera

Before a fix, the home map shows the whole of the 48 states. The fit is
width-limited on every phone, so the centre's latitude is what places it.
Centred on the states' own middle (37.6), the first try put Mexico City in
the bottom of the card and the 49th parallel under the 17 Pro Max's status
bar. At 40.95, measured on 2026-10-18:
- On the **iPhone 17 Pro Max**, the 49th parallel is at y = 69 pt, below the
  62 pt status bar, and Key West is at about 296 pt of the 305 pt card, right
  of Apple's logo.
- On the **iPhone SE (3rd generation)**, the 49th parallel is at y = 80 pt.

The 60.4° width leaves Cape Flattery and Lubec just inside the card's edges.

**New: the map moves to the phone at launch.** Around New England, a camera on
the whole region was close enough to rank searches from. Nationally it is not,
because the search bias follows the camera, and with the whole country on
screen "Main St" would rank from Kansas. So when the launch check's rough fix
is inside the covered area, the home map moves to a 300 km box around the
phone (`RouteModel.launchFix`, `PlanningView`). It does not move if the user
has already set a start. Nothing new is sent: the fix is the same one the
launch check already took, and it stays on the phone. This is a new *use* of
location, so the purpose string names it (§4).

### 2.5 Not changed

- Loops keep their limits (`LoopModel.minKm` 5, `maxKm` 400).
- The app has **no client-side 500 km check**. The cap is measured between
  *snapped* endpoints, which only the server knows, and a client check on raw
  coordinates would disagree with it near 500 km. The app shows the server's
  message as written. If B wants an instant refusal, a client check at more
  than 510 km (500 plus 5 km of snap at each end) could never contradict the
  server. That is a follow-up once B's message is final.
- The `main` branch's New England gate, and `tools/build_new_england_boundary.py`,
  which writes a file that no longer exists on this branch. At the `usa` merge
  that script should go, or be pointed somewhere harmless. If it is run, its
  output is an unused `enum`, which is harmless but confusing.

## 3. What the server must change (for unit B)

The app passes every server `{"error": ...}` through verbatim, so these
strings are what drivers read.

1. **"point is outside the covered road network (currently New England)"**
   (`server/app.py`, three places, `REGION`). Nationally, set `REGION`, or
   reword the message so it does not name a region the app no longer has.
   Suggested: "that point is outside the area Sunday Drive covers: the 48
   contiguous states and Washington, DC". The app's own copy uses the same
   phrase (`Coverage.areaName`).
2. **Inside the 48 but more than `SNAP_MAX_M` (5 km) from any road.** Remote
   desert and wilderness have such points. The same message would tell a
   driver in Nevada that Nevada is not covered. They need their own message,
   for example "there's no road within 5 km of that point".
3. **The 500 km cap**, enforced before any search starts, as the decision
   says. It needs a message the app can show as written: what the limit is,
   in miles too, and what to do instead, for example "Directions go up to 500
   km (310 miles) in a straight line. Try a stop on the way as your
   destination." The app's "Before you drive" screen already states the cap in
   those units, so if B changes the number, `BeforeYouDriveView.swift` changes
   with it. A distinct status or error key would let a later app version react
   to it without matching text.
4. **Snapping must not cross a border or a strait.** A start the app counts as
   inside (Fort Frances, 80 m over the line; anything in the 500 m buffer) can
   snap to a US road across the river, and the result is a route starting on
   the wrong side of a border crossing. The national graph's edges are where
   this has to be decided. Around New England it was the same in principle
   (Stanstead), but nationally there are many more such towns.
5. **Point Roberts and the Northwest Angle** are covered but reachable by road
   only through Canada. With no Canadian roads in the graph, a route there
   fails. Its message should say why, rather than "no route found".
6. **Seasonal-closure dates** come from the trip's own time zone, in the brief
   for B already (`REGION_TZ`). The app needs no change for it.

## 4. Every string changed in `ios/`

| Where | Was | Now |
|---|---|---|
| `project.yml`, `NSLocationWhenInUseUsageDescription` | "Your location is used to plan drives from where you are, to check that you’re in New England, and to guide you turn by turn." | "Your location is used to show the map where you are, to plan drives from there, to check that you’re in the area the app covers, and to guide you turn by turn." (it must not name the app: `LocationTextAndContactTests`) |
| `Coverage.notCovered` (search found only uncovered places) | "“X” isn’t in New England. Sunday Drive only covers the six New England states." | "“X” is outside the area Sunday Drive covers: the 48 contiguous states and Washington, DC." |
| `Coverage.outsideHere` (My Location or Loop outside) | "You’re outside New England, so this can’t start from your location. Type a New England town as your start." | "You’re outside the area Sunday Drive covers, so this can’t start from your location. Type a town in the 48 contiguous states as your start." |
| `OutsideCoverageView` body | "Sunday Drive only covers the six New England states: Connecticut, Maine, …" | "Sunday Drive only covers the 48 contiguous states and Washington, DC. You’re outside them, so Loop and My Location can’t plan a drive from where you are." |
| `OutsideCoverageView` second line | "…type a New England town, like Stowe, VT, as your start." | "…type a town in the 48 states, like Stowe, VT, as your start." |
| `HomeView`, Loop row when outside | "Type a New England town to start" | "Type a town to start from" |
| `BeforeYouDriveView` | "New England only. Six states, 236,000 km of road, all of it measured." | "The 48 contiguous states and DC only. Directions go up to 500 km (310 miles) in a straight line. Loops have their own limits." |
| `BeforeYouDriveView` (new line) | | "Driven in New England only. Everywhere else, routes come from the same map data and the same scoring, but nobody has driven them to check." |
| `BeforeYouDriveView` | "No lane guidance. The data covers between 4.6% and 23.8% of junction approaches depending on the state…" | "…In the states measured, the data covers between 4.6% and 23.8%…" (the figures are New England's) |
| `BeforeYouDriveView` | "Beauty is not measured evenly. The terrain component saturates north of Massachusetts…" | "Beauty is a model. One ruler for the whole country, checked against drivers’ ratings in New England only." |
| `BeautyType` tune-sheet label | "Forest & parks" | "Forest, parks & desert" (desert rides this slider under E1, `docs/national-scenery-components.md` §6) |
| `AboutView`, Terrain Tiles credit | three upstream lines | adds "Mexico terrain data source: INEGI, Continental relief, 2016;", verbatim from joerd's required block, because the border states' boxes reach into Mexico at zoom 11 |
| `AboutView`, new source | | PAD-US 4.1 (`c_protected`), with USGS's citation verbatim from ScienceBase item 652d4fc5d34e44db0e2ee45e |

**For the owner to confirm:** "Driven in New England only" and "Beauty is a
model" state limits the New England build did not have to. They are true, and
they are the kind of thing a driver in Utah would want to know. They are still
his words to approve. The 500 km figure in "Before you drive" assumes B ships
the cap as decided.

**Outside `ios/`, needed before submission, not done here** (I own `ios/`
only):
- `site/privacy/index.html` and `docs/privacy-policy.md` quote the location
  purpose string word for word, and `tests/test_privacy_page.py` pins them to
  `ios/project.yml`. **So the two quoting tests fail on this branch until the
  page quotes the new string.** The page also describes "the New England check"
  in three more places, and needs the launch camera added as a use of
  location (on-device, nothing sent).
- `site/index.html`, the support page App Review reaches, says "six New
  England states" twice and has a section "It says it only works in New
  England".

## 5. Tests

- `CoverageTests` (31 tests), `OutsideCoverageTests` (12) and
  `AttributionTests` (15) all pass on the iPhone 17 Pro simulator (iOS 26.4).
- Full suite against a local server on `processed-ne`: see §5.1.

### 5.1 Full-suite run

Run on 2026-10-18 on a simulator made for this work (iPhone 17 Pro, iOS 26.4),
with `TEST_RUNNER_SUNDAYDRIVE_API` pointed at a local server on port 5191
serving `processed-ne`. Took 36 min.

**488 tests: 454 passed, 31 skipped, 3 failures.**
- **1 was mine and is fixed.** `LocationTextAndContactTests.test_the_location_prompt_does_not_name_the_app`.
  The first national purpose string said "the area Sunday Drive covers". It
  now says "the area the app covers", and that class and
  `PrivacyPolicyLinkTests` pass (7 of 7). The full suite was not run again
  after this one-string change.
- **2 are not from this change.** They are two assertions in
  `DriveReplayTests.test_no_recorded_drive_hears_the_same_maneuver_twice`, on
  the `drive-2026-10-06-122558` trace: "Sharp right onto Old North Dana Road"
  spoken twice, and 149 utterances over 20 maneuvers. This red was recorded on
  `main` on 2026-10-08. The test, `DriveReplay.swift`, `NavigationModel.swift`
  and `VoiceGuide.swift` are identical to `usa` on this branch, and nothing on
  the replay path calls `Coverage`. I did not re-run it on `usa` itself.
- The 31 skips are opt-in harnesses: 22 `SimulatedDriveTests` (the e2e
  drives, off without `SUNDAYDRIVE_E2E`), 8 `SimulatorScreenDriveTests` and 1
  `ReplayDumpTests` (off without `SUNDAYDRIVE_REPLAY_OUT`).

Python side: `tests/test_privacy_page.py` fails 2 of 6 on this branch, as
predicted in §4, until `site/privacy` quotes the new purpose string.

## 6. App Store listing and screenshots the release needs

None of this is code, and none of it is done.

- **Promotional text, description, keywords** (`docs/app-store-listing.md`).
  Every coverage claim is New England's: "Every road in New England", "six
  states, about 146,000 miles", "New England only. Routes and loops have to
  start and end in the six states". The national mileage comes from unit A's
  per-state counts. The 500 km directions cap belongs in the description's
  limits list. Keywords were chosen for a New England audience and need
  re-cutting for national search, within the 100-byte limit.
- **Subtitle**: "The scenic route, on purpose" has no region in it and can
  stay.
- **Review notes** (`docs/app-store-submission.md`, "Why does it only work in
  New England?"). Rewrite them. A reviewer in Cupertino is now **inside**
  coverage, so My Location and Loop work where they sit. The notes should give
  a California trip and loop measured on the national server, plus the
  Toronto-style refusal for anyone reviewing from abroad. The Concord→Rockport
  and Kent, CT figures were measured on the New England server.
- **Screenshots**: every current one shows New England. They need at least
  one drive outside New England, so the listing does not imply a regional
  app. Real-drive screenshots need `simctl location start` playback, not
  `set`. The opening map now shows the whole country, and then the user's
  region, so a "home" screenshot should be taken after the launch fix.
- **Featuring nomination** text ("It launches for the last weekends of fall
  foliage, when New England is full…").
- **App Privacy answers**: unchanged in kind. Location is still used on the
  phone and sent only to plan a route. The camera move adds no collection.
- **Availability**: coverage is the 48 states and DC. Whether the app is
  offered in other storefronts, such as Canada, for people planning US trips,
  is the owner's decision. The app already tells anyone outside what works.
- **Age rating, EULA, route-guidance notice**: unchanged.
