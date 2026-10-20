# Review fixes: the app (unit I)

**Status:** built 2026-10-20 on `claude/review-fixes-app`, cut from local `usa`
at 4f74951. Not merged, not pushed, not deployed. `ios/` only, plus this
document. The New England build on `main` is untouched.

What the 2026-10-20 outside review found in the app, what changed, and every
string a driver now reads differently. Code comments and tests cite this
document by item number.

## Done and left

| Item | State |
| --- | --- |
| 1. The cap's message, mid-drive refusals, a phone-side cap check | done, tested |
| 2. Spoken route numbers for every state and DC, plus SR, CR, FM, BIA | done, tested |
| 3. Start defaults to My Location; a filled field selects all on focus | done; checked on the simulator, not in a unit test (see §3) |
| 4. The loop slider takes the start's limit | done, tested with stubs and with bodies captured from unit R's server; seen on the simulator against R's uncommitted working tree (§7) |
| 5. Duplicate suggestions, refused Recents, Open Settings, 310 miles | done, tested |
| 6. "Before you drive" leads with what the app does | done, tested |
| Suite against a local national server | see §7 |

**Left:**

- R's call on `START_TOO_FAR` on an open approach to a closed edge (§1, "The
  I-10 lead-in");
- the owner's sign-off on the new copy (§6);
- the replay red that `usa` already had (§7), which belongs to another
  unit.

## 1. The cap's message is no longer thrown away

`RouteService.failure(status:body:)` decoded error bodies as
`[String: String]`. The trip cap's reply carries numbers:

```
{"code":"TRIP_TOO_LONG","error":"That trip is 849 miles in a straight line. Sunday Drive plans drives of up to 311 miles, so pick a stop along the way and plan it in two parts.","km":1365.6,"max_km":500.0}
```

That is the body the national server on `usa` sent for Boston to Chicago on
2026-10-20, kept byte for byte in `ReviewFixesAppTests`. The decode failed, so
the app showed "The routing service isn't reachable right now. Try again in a
moment. (HTTP 400)".

**Now:**

- A new `Refusal` (in `RouteService.swift`) reads `error`, `code`, `max_km`
  and `km` field by field with `JSONSerialization`. Unknown fields are
  ignored, numbers sent as strings are accepted, and a body with no string
  `error` is still `.unreachable(status)`. `ServiceError.server` carries a
  `Refusal`, not a `String`.
- It branches on `code` (`Refusal.Code` holds all seven of the contract's
  codes). `TRIP_TOO_LONG` with numbers gets the app's own sentence, in the
  app's miles. Every other refusal shows the server's sentence. An older
  server's lower-case fragment ("no route found between those points") is
  turned into a sentence ("No route found between those points.").
- **Phone-side check.** `RouteModel.computeRoute` measures the straight line
  between the two ends before asking. Over 500 km, it shows the cap's
  sentence and sends nothing. Planning only: a reroute has more room on the
  server (`REROUTE_MAX_TRIP_KM`), so it is never checked on the phone.
- **Mid-drive.** `NavigationModel.classify` used to turn every non-`.server`
  error into a lost connection, so the cap's 400 said "No connection. Head
  back to your route." It now books:
  - a `.server` refusal as the server's "no", with its sentence under the
    trip card and the backoff it already had;
  - any 4xx whose body cannot be read as a refusal too, with the app's own
    sentence. The exceptions are 408 and 429, which waiting fixes.

  The banner for both is "Off route", as for any refusal.
- The trace records a refusal's code with its message (`CODE: message`).

### The router's six extra codes

Unit R's branch (4db54fc) gives a code to the refusals that existed before
codes (`docs/review-fixes-router.md`, "Error bodies"). The app reads them all
(`Refusal.Code`):

| code | what the app does |
| --- | --- |
| `BUSY` | `.busy` at any status, the existing "Busy planning other drives" path: never the server's "no", so the loop page does not ask again at once and a drive does not climb the backoff |
| `CLOSED_FOR_SEASON` | the app's own sentence, "The only way there is closed for the season.", whatever the server's words |
| `SAME_ROAD`, `NO_LOOP`, `NOT_FOUND`, `SERVER_ERROR` | the server's sentence |
| any other code, or none | the server's sentence (a fragment from an older server is made one) |

Every one of them is an answer, so mid-drive none is "No connection". That
includes a 500 `SERVER_ERROR`: its sentence goes under the trip card, and the
reroute backs off as for any refusal. `NO_LOOP`'s `nearest_km` may be `null`,
and the body still decodes.

### Exit numbers and multi-values

The router now words a ramp that serves several exits "Take exit 7A or 7B",
with `exit_ref` "7A/7B" for a badge. The app draws no exit badge (`exit_ref`
is decoded, not shown), so the instruction is what a driver sees and hears,
and the router's wording is left exactly as sent.

For a server that still sends raw OSM values, `String.multiValuesTidied`
applies to both the banner (`NavigationModel.currentInstruction`) and the
voice (`spokenAloud`):

- "exit 7A;7B" and "exit 7A/7B" become "exit 7A or 7B";
- three numbers become "exit 12, 13 or 14";
- any other ";" becomes the sign's " / ". "Continue onto I 295;US 1;ME 26"
  shows as "I 295 / US 1 / ME 26" and is spoken "Interstate 295 and Route 1
  and Route 26";
- a slash that is not an exit's ("Soldiers Field Road West / Newton") is left
  alone.

### The I-10 lead-in

The review's blocker was this banner: "Off route · route 9.5 mi away / Head
back to your route", under the U-turn arrow, on I-10 westbound through edge
1470492. Unit R found the cause, and it was not a jump to another road. The
reroute's line began at the junction at the far end of the 16.3 km edge, so
the car was driving the new route's own road while the app called it off the
line.

- R's fix is a lead-in (d36a564): a reroute with a heading begins where the
  car is.
- **The app needed no change to take that line.** `awaitingJoin` settles on
  the first fix, which is 0 m from it.

**The test.** `LeadInRerouteTests` drives it against a live server:

- It plans a route to Blythe, CA from 1.1 km east of the edge on
  `data/pack-us`, where the ford still closes the edge.
- It then feeds `NavigationModel` fixes at 35 m/s, one a second, west down
  I-10 through the edge, with real reroutes on the test's clock.
- It asserts that every line adopted starts within 50 m of the car, and that
  once one is adopted the car is never called off it.
- It skips without `SUNDAYDRIVE_API`, and never uses the deployed server.
- `TEST_RUNNER_SUNDAYDRIVE_LEADIN_TRACE=1` prints every fix.

| server | lines adopted | where they began | called off the line after adopting |
| --- | --- | --- | --- |
| `usa` (no lead-in) | fix 11 | 16,987 m from the car | 438 fixes, "Off route · route 9.5 mi away / Head back to your route" |
| R, d36a564 | fix 38 | 0 m from the car | 0 |

The test reproduces the review's banner on `usa`, and it is gone with R's
lead-in.

**What is left: refusals on the approach (server).** Before the first
adoption the car is still called off the line, on the open 1.1 km of I-10 that
leads only into the closed edge. There R answers every reroute with
`START_TOO_FAR` (`m` 17,171 and 16,542 at two fixes): the only start it can
find is past the ford. The planned route left I-10 at the exit there, so "Off
route" is true, but on a freeway it is not useful.

- This is R's to decide. D's ford rule removes the case on I-10 itself
  (`pack-us-next`).
- It will recur before any other closed edge on a one-way road.

**The app's half (`RerouteFailure.refusedHere`).** Mid-drive,
`START_TOO_FAR` is said under the trip card like any refusal, but it no
longer climbs the reroute backoff. It depends only on where the car is, so
the next ask, at the base 8 s cooldown, is the one that can succeed. With
the backoff, two refusals at 16 s and 32 s kept that banner up for 50 fixes.
Without it, the window is 27 fixes, all of them on the approach. A unit test
in `MidDriveRecoveryTests` pins the gaps at 10 s or less.

## 2. Spoken road names

`String.spokenAloud` turned `MA|RI|NH|VT|ME|CT|US <n>` into "Route <n>". It
now covers:

- every state's postal code, DC and `US`, built from `Coverage.stateCodes`
  so the two lists cannot drift. Each becomes "Route <n>".
- `SR <n>` → "State Route <n>" ("SR" can be read as "senior").
- `CR <n>` → "County Road <n>".
- `FM <n>` → "Farm to Market Road <n>".
- `BIA <n>` → "BIA Route <n>".

A number must still follow, and matching is case-sensitive. "YMCA Drive",
"ORCA Road", "CR Smith Road" and "In 500 feet" are untouched, and there are
tests for each. "I-295 / US-1", the form unit R announces a split
multi-value in, reads "Interstate 295 and Route 1".

The new readings were chosen, not measured. `docs/voice-guidance-plan.md`
§4.2 compares synthesised durations to infer what the voice says, and that has
not been repeated for SR, CR, FM and BIA. "Route <n>" is what the sign says
for a state route, so that rewrite is harmless even if the premise is wrong.

## 3. Directions starts from here

- **An empty Start.** Choosing a destination with no Start did nothing,
  because only a Recents row filled it.
  - Now `RouteModel.resolve` fills Start from My Location when a destination
    is chosen, Start is empty and location is allowed, then routes.
  - Opening Directions with nothing set also fills Start
    (`defaultStartToHere`). It skips this when the phone is outside the
    covered area, and when a destination survives from the last drive
    (`endNavigation` keeps it). Otherwise that would route straight back to
    the place just arrived at.
- **Typing into a filled field.** It edited the old text: "Santa Cruz Beach
  Boardwalk" plus a typed letter became "Santa Cruz Beach R…". `PlaceField`
  now selects the whole field when it takes the keyboard. It listens for
  `UITextField.textDidBeginEditingNotification` and calls `selectAll` on the
  next turn of the run loop, after the focusing tap has placed its caret.
  It checks `focused` only after that hop. The notification arrives before
  `@FocusState` catches up, so the first build checked it too early and
  never selected anything. The simulator caught it ("ChicagoProv"). This
  works on iOS 17, where SwiftUI's `TextSelection` binding does not exist.

`CLLocationManager`'s authorisation cannot be set from a unit test, so the
defaulting was checked on the simulator (§7).

## 4. The loop slider takes the start's limit

- `RouteService.loopLimit(from:)` sends `POST /api/loop/limit` with `from`
  in the form body, never on the URL. It decodes
  `{"max_km": <float>, "max_mi": <int>}` into `LoopLimit`.
- `LoopModel` asks for it **once per start, beside the first loop, not
  before it.**
  - The driver is waiting for the loop, not the limit.
  - A loop over the limit is refused with the limit anyway.
  - A failure leaves the slider as it was, and is not retried until the start
    changes. An older server that answers 404 costs one request per start.
- `sliderMaxKm` is the limit floored to a whole kilometre, within 10–400 km.
  The slider's top, its right-hand time label and the clamp before each
  request all use it.
- **"Up to N mi from here"** appears under the dial once the limit is known.
  N is the server's `max_mi`, or the floored miles of `max_km` if `max_mi` is
  missing.
- **`LOOP_TOO_LONG`** with `max_km` is adopted as this start's limit, and the
  loop is asked for again at once, at the limit, in the same direction. That
  retry happens once. The compass fallback, which drops a remembered
  direction on a refusal, no longer fires for `LOOP_TOO_LONG`, because the
  length was the problem, not the direction.
- A length over the limit learnt for this start is pulled in before asking.
  That is the usual case: a long loop remembered from a sparser start.

## 5. Smaller ones

- **Duplicate suggestions.** Reproduced on the simulator: "Santa Cruz Beach
  Boardwalk" came back under three subtitles.
  - "Santa Cruz, CA, United States".
  - "400 Beach St, Santa Cruz, CA 95060, United States".
  - The same address with two spaces before the ZIP.

  `SearchCompleter.distinct` keeps the first row for each place. Two rows are
  one place when their titles match and one subtitle equals the other, or
  ends with it after a comma (the town is the tail of the address).
  Comparison ignores case, accents, ZIP codes and runs of spaces. Two Main
  Streets in two towns are both kept, and so are "Stowe, VT" and "North
  Stowe, VT". After the fix the same search shows the Boardwalk once.
- **Refused destinations in Recents.** A searched destination is held in
  `pendingRecent`.
  - It is filed when a route to it comes back.
  - It is dropped when the phone's cap check or the server refuses it.
  - A dead network is neither, so it waits for the next route.
- **Location off.** Directions and Loop show an **Open Settings** button
  under the location-off sentence (`OpenSettingsButton`, which opens
  `UIApplication.openSettingsURLString`).
- **310 miles everywhere.** `RouteService.capMiles` floors the cap
  (500 km = 310.7 mi), so an "up to" never promises a trip the server
  refuses. The first screen and the cap's sentence both read it. Whatever
  the server still says ("311"), the app shows 310 for `TRIP_TOO_LONG`.

## 6. Every string changed

| Where | Was | Now |
| --- | --- | --- |
| Directions, trip over the cap (phone or server) | "The routing service isn't reachable right now. Try again in a moment. (HTTP 400)" | "That trip is {N} miles in a straight line. Sunday Drive plans drives of up to 310 miles, so pick a stop along the way and plan it in two parts." |
| Any older server fragment | shown as sent, e.g. "no route found between those points" | first letter capitalised, full stop added: "No route found between those points." |
| Mid-drive, a refusal | "No connection. Head back to your route." (spoken) | the server's sentence under the trip card, banner "Off route" |
| Mid-drive, an unreadable 4xx | "No connection. Head back to your route." | "Couldn’t plan a new route from here. Keep to your route or head for a bigger road." |
| Mid-drive, `START_TOO_FAR` | "No connection. Head back to your route." (the body did not decode) | the server's sentence under the trip card, asked again at the base cooldown |
| Directions and Loop, location off | "Location access is off — allow it in Settings to start from here." | "Location access is off. Allow it in Settings to start from here." plus a button, **Open Settings** |
| Loop dial | (nothing) | "Up to {N} mi from here" |
| A road closed for the season (`CLOSED_FOR_SEASON`) | the server's words, e.g. "the only way there is closed for the season" | "The only way there is closed for the season." always |
| Banner and voice, a raw multi-value exit | "Take exit 7A;7B" | "Take exit 7A or 7B" |
| Banner, a raw multi-value ref | "Continue onto I 295;US 1;ME 26" | "Continue onto I 295 / US 1 / ME 26" (spoken "Interstate 295 and Route 1 and Route 26") |
| Spoken | "CA 1", "TX 71", "SR 20", "CR 12", "FM 1960", "BIA 15" read as letters | "Route 1", "Route 71", "State Route 20", "County Road 12", "Farm to Market Road 1960", "BIA Route 15" |
| Before you drive, first line | (none) | "Sunday Drive finds the beautiful way: a scenic route to where you’re going, or a loop back to where you started." |
| Before you drive, section heading | "What it does not do" | "Good to know" |
| Before you drive, limit 1 | "The 48 contiguous states and DC only. Directions go up to 500 km (310 miles) in a straight line. Loops have their own limits." | "Drives of up to 310 miles. Directions go up to 310 miles in a straight line, anywhere in the 48 contiguous states and DC. Loops reach farther in open country than in a city." |
| Before you drive, limit 2 | "Seasonal roads. Some mountain roads close for winter. The app avoids the closures OpenStreetMap records, but not every closure is recorded, so follow posted signs." | "Signs come first. Some roads close for the season, and the map doesn’t know every closure. Follow posted signs." |
| Before you drive, limit 3 | "No live traffic. Every time shown is a model, not a measurement." and "No lane guidance. In the states measured, the data covers between 4.6% and 23.8% of junction approaches, which is not enough to tell you which lane to be in." | "Times are estimates. There’s no live traffic and no lane guidance." |
| Before you drive, limit 4 | "Beauty is a model. One ruler for the whole country, checked against drivers’ ratings in New England only." | "Beauty is an estimate. Scenery scores come from map data, so a road you love may score lower than it deserves." |
| Before you drive, removed | "Driven in New England only. Everywhere else, routes come from the same map data and the same scoring, but nobody has driven them to check." | (gone) |

**Unchanged:**

- The route-guidance notice (`DataSources.routeGuidanceNotice`) is unchanged,
  character for character, and `AttributionTests` still pins it.
- So are the "Before you drive" and "Route guidance" labels, and "Got it" /
  "Done".

The new copy is the owner's to approve.

**Docs outside `ios/` that now quote old copy.** These are not edited here,
because this unit owns `ios/` only:

- `docs/app-store-listing.md:122` points at the "What it does not do" heading.
- `docs/app-goes-national.md:179` quotes the lane-guidance line.

## 7. Verification

### The suite

**Setup:**

- a simulator made for this unit (iPhone 17, iOS 26.4), deleted afterwards;
- `-destination id=`, with `TEST_RUNNER_SUNDAYDRIVE_API` pointed at a local
  national server;
- the server is `usa`'s `server/serve.py` on `data/pack-us` and
  `data/processed-us`.

**Result: 518 tests, 31 skipped, 2 failures.** The last recorded figure for `usa`
was 488 tests, 36 skipped, 0 failures.

- **Thirty tests are new.** All 30 are in `ReviewFixesAppTests`, and 488 + 30 is 518.
  The two new `MidDriveRecoveryTests` rows sit inside an existing test.
- **Five fewer skips.** The recorded drives in the main checkout's `traces/`
  are found from this worktree, so `DriveReplayTests` runs instead of
  skipping.
- **Both failures are one test, and `usa` already fails it.**
  `DriveReplayTests.test_no_recorded_drive_hears_the_same_maneuver_twice`
  fails on the 2026-10-06 12:25 trace: "Sharp right onto Old North Dana
  Road" is said twice running, and the drive has 149 utterances against a
  budget of 120.
  - The same test was run on an export of unchanged `usa` (4f74951), with
    `TEST_RUNNER_SUNDAYDRIVE_TRACES` at the same traces. It fails with the
    same two messages and the same numbers.
  - None of this change can reach it: the replay fails its requests as
    `.offline`, which `classify` treats as it always did.
  - That export also failed `test_the_search_for_traces_finds_them_and_gives_up_cleanly`.
    That test asserts that no `SUNDAYDRIVE_TRACES` is set, so the failure
    comes from the override needed to point the export at the traces, not
    from the code.

**Changed expectations.** Three existing expectations changed, because older
servers' fragments are now shown as sentences:

- `LoopModelTests`: "No loop there.";
- `LoopModelTests`: "Outside the covered network.";
- `MidDriveRecoveryTests`: "Closed for the season.".

The loop test helpers in `LoopModelTests` and `OutsideCoverageTests` now stub
`fetchLimit`. Without that, they would ask whatever server the run points at.

### On the simulator (`xcrun simctl location start` playback, never `set`)

**Against `usa`, from Boston:**

- **First launch.** "Before you drive" opens on the new first line, and the
  route-guidance notice is intact. The four limits read as in §6, with 310
  miles.
- **Directions, with location allowed.** Start filled itself: "My Location
  · Congress St, B…".
- **Chicago as the destination.** The cap's sentence appeared at once: "That
  trip is 851 miles in a straight line. Sunday Drive plans drives of up to
  310 miles…". There was no HTTP status.
  - This is the phone's own check. It measures from the fix rather than from
    the server's snapped ends, hence 851, not 849.
- **Select-all.** Tapping the filled Start field selected all of it, and
  typing "Santa Cruz Beach Boardwalk" replaced it. The first build appended
  to it instead (§3).
- **Suggestions.** "Santa Cruz Beach Boardwalk" appeared three times before
  the dedupe fix, and once after it.
- **Location off.** Loop showed "Location access is off. Allow it in
  Settings to start from here." over **Open Settings**, which opened
  Settings.

**Against unit R's working tree.** Unit R's branch had no commits yet, so the
server was started from its worktree as it stood, read-only. Its bodies
matched the contract:

- `/api/loop/limit` from New York: `{"max_km":288.3,"max_mi":179}`;
- from Boston and from Burlington: 400 km;
- a 400 km loop from New York: `LOOP_TOO_LONG` with `"max_km":288.3`.

On the simulator, New York's Loop page showed **"Up to 179 mi from here"**,
and the slider's top read 5 hr 46. That is 288 km at the seed's 1.2 min/km.
`ReviewFixesAppTests` keeps R's `LOOP_TOO_LONG` body verbatim.

### Against unit R's committed branch

**Setup.**

- The server was started from an export of `claude/review-fixes-router` at
  d36a564 (the lead-in), on `data/pack-us` and `data/processed-us`.
- It ran only after unit D's `data/pack-us-next.done` existed and no
  `pack.py` was running.
- One server at a time, stopped by its own PID. A fresh simulator, deleted
  afterwards.

**Suite: 525 tests, 31 skipped, 3 failures.** There are 7 new tests:

- five in `ReviewFixesAppTests`;
- the `START_TOO_FAR` backoff test;
- `LeadInRerouteTests`.

**The failures.**

- Two are the replay failures above, unchanged.
- The third was `SimulatedDriveRegressionTests.test_F6_instructions_carry_no_raw_ref_lists`,
  a strict expected failure ("semicolon ref lists in instructions"). R's
  branch fixes Finding 6 on the server, so the expected failure stopped
  happening.
  - It is now a plain assertion. Rerun against R's server, it passes.
  - Against a server older than R's it fails, which is right: those servers
    still send the lists. The app's `multiValuesTidied` covers the banner and
    the voice either way.

**On the simulator** (`simctl location start` playback at 35 m/s, through
the 99 waypoints of I-10 westbound through edge 1470492):

- The app planned Blythe from "My Location · I-10 W, Salome" around the
  ford, via Salome.
- The car kept to I-10.
- About a minute in, and again two minutes in, the banner read "67–69 mi /
  Keep right onto I 10 Truck", with the line under the car on the closed
  edge: no "Off route", no U-turn arrow.
- The approach window (§1, "The I-10 lead-in") was not caught on screen. The
  test measures it.

## 8. What the app needs from the server (unit R)

The app is built to the contract and reads today's bodies too. It relies on
these:

1. **`TRIP_TOO_LONG` keeps `km` and `max_km` as numbers.** With both, the
   app writes its own sentence in miles. Without them, it shows the server's
   sentence.
2. **`POST /api/loop/limit`** per the contract, with `max_mi` as an int.
   Please never return a `max_km` below 5. The app ignores such a limit and
   keeps the slider at 10 km or more.
3. **`LOOP_TOO_LONG` carries `max_km`.** The app retries once at
   `floor(max_km)`. It assumes a loop at exactly `floor(max_km)` is accepted,
   so compare with `km > max_km`, not `>=`.
4. **Sentences fit a moving driver** for `START_TOO_FAR`, `NO_ROUTE_NEARBY`
   and `LEG_TOO_LONG`. Mid-drive they are shown under the trip card as sent
   (not spoken), and the reroute backs off.
5. **Raw multi-value refs** ("I 295;US 1;ME 26") are split on the server. The
   app does not split them; it only reads " / " as "and".
6. The cap's own wording can say 310 (`_too_far`). The app no longer depends
   on it.
