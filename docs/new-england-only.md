# Making it impossible to miss that the app only works in New England

**Status:** shipped — merged to `main` by `a2ddddc`. This is the part of the dispatch brief that outlived the work: its measurements, decisions and results. The brief itself, with its traps and done-list, was deleted on merge — `git show a2ddddc:docs/new-england-only-brief.md` prints it. Section numbers and "below" refer to that brief's layout.

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
