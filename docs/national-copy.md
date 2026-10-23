# The national copy: every customer-facing text, rewritten for the 48 states

**Status: built 2026-10-23 on `claude/national-copy-7a6577`, cut from `usa` at
`936dfcf`. Not merged, not pushed, nothing published.** The brief is
[`national-copy-brief.md`](national-copy-brief.md), committed unchanged; it is
deleted in the merge that brings this back. Nothing was entered in App Store
Connect, nothing went to the live site, no form was filled.

The binary on `usa` covers the 48 contiguous states and DC. Every text a
customer, App Review or a repo visitor reads described a six-state New England
app; the 2026-10-23 outside review flagged it as a metadata-rejection blocker.
This unit rewrote all of them, with every number measured on the national
build, fixed three things the new screenshots would show, added the ODbL §4.6
line, put a test on New England coverage claims, retook the screenshots and
re-based the marketing timeline on approval.

**What the owner must sign off** is §8. **The production caveat** is §3.1:
production still serves the New England build, so nothing here is true of
production until the national server is deployed.

## 1. What changed, by file

| file | what |
| --- | --- |
| `docs/app-store-listing.md` | Rewritten: promotional text, description, keywords (§1–3), featuring nomination (§6) |
| `docs/app-store-submission.md` | §5's region note replaced by the national review notes, ready to paste; banner and checklist rows 13 and 16 |
| `site/index.html` | Support page: coverage, the outside-coverage FAQ, two new FAQs (the 310-mile cap, uneven beauty), credits now the Sources screen's word for word |
| `site/privacy/index.html`, `docs/privacy-policy.md` | The area check is national; the launch camera added as a fourth use of location; effective date 23 October 2026 |
| `README.md` | Opening paragraph only: national coverage and graph size, with the New England scope of the test drives |
| `app-store-screenshots/build.py` | National captions, a place line under each phone, national store and banner copy |
| `app-store-screenshots/*.jpg`, `captioned/`, `captioned-6.3/`, promo PNGs | Retaken and rebuilt (§6) |
| `ios/Sources/PlanningMap.swift`, `PlanningView.swift` | The locate button below the status bar (§4.1) |
| `ios/Sources/RouteResults.swift`, `DirectionsView.swift`, `LoopView.swift` | The zero-gain sentence (§4.2); the breakdown as shares of the route, captioned (§4.3) |
| `ios/Sources/AboutView.swift` | The ODbL §4.6 line and repository link on the OpenStreetMap entry (§4.4) |
| `ios/Tests/RouteComparisonTests.swift`, `AttributionTests.swift` | The pinned strings updated to the new wording; two new tests |
| `tests/test_no_new_england_claims.py` | New: fails on a New England coverage claim, with an allow-list (§7) |
| `tests/test_support_page.py` | New tests: every Sources-screen credit line is on the support page |
| `docs/marketing-plan.md` | §7 re-based on approval, with the server gate before S and four go/no-go additions; §0, §5.5, §5.7, §10, §12 and §15 de-dated (§9) |

## 2. Measurements

Everything here was measured on 2026-10-23 on this Mac, on the national build:
`data/processed-us` and `data/pack-us` (pack fingerprint `b0ba664c…7b45`, the
one `api/health` reports), served by `server/serve.py` at this branch's head on
`127.0.0.1:55621`. `server/` and `pipeline/` are unchanged on this branch, so
the server is `usa`'s. No other national job ran (`ps -axo pid,rss,command |
grep '[s]erve.py'` was empty before the server started).

**Requests were sent the way the app sends them** (`RouteService`): POST,
form body, `pref` 0.50 for directions (`RouteModel.pref`'s default), the
loop endpoint's own default `pref`, and the app's default scenery weights,
every type 1.00 and town centers 0.00 (`BeautyType.all`). The weights matter:
a first pass without them got 39 beautiful miles on the Moab loop where the
app shows 48, and 18 on Denver → Idaho Springs where it shows 16. Every
figure below is the weighted one, and the screenshots agree with it to the
mile. The probe script is not committed; each figure is one request, and the
router is deterministic on a fixed pack.

### 2.1 National mileage

| | edges | km | miles | share of km at 7+ |
| --- | --- | --- | --- | --- |
| `data/processed-us/graph_edges.parquet` | 25,849,861 | 7,796,106 | 4,844,276 | 5.28% |
| `data/processed-ne/graph_edges.parquet` (for comparison) | 998,252 | 232,720 | 144,606 | 10.00% |

Method: the sum of `length_m` over every row of `graph_edges.parquet`, read
with pyarrow. Each row is one road segment, drawn once whatever its one-way
flag, so it is road length, not lane length. The national figure matches
`national-build.md`'s 7,796,108 km to rounding. The edges are owned by the 48
state cores and DC (TIGER/Line boundaries, `national-build.md` §2), so the
15 km read rings over the borders are not counted.

**In copy: "about 4.8 million miles".** Rounded down from 4.84.

The New England row shows why the old figures cannot be reused even for New
England: the rebuilt `processed-ne` is 232,720 km, not the 236,000 km the
README said, because closures and private roads have since been taken out of
the graph.

### 2.2 The trips the copy and the screenshots use

"Beautiful" is km on edges scored 7 or more, as the server's `beautiful_km`
counts them. Miles and minutes are rounded the way the cards print them
(`Double.wholeMilesFromKm`; the added minutes are the difference of the two
whole-minute figures).

| trip | fastest | scenic | on the card | used for |
| --- | --- | --- | --- | --- |
| Apple Park → Boulder Creek, CA | 44.7 km, 42.2 min, 23.9 km beautiful | 45.0 km, 48.4 min, 36.6 km | +6 min, 15 → 23 mi | review notes |
| Denver → Idaho Springs, CO | 53.0 km, 33.7 min, 0.4 km | 54.1 km, 48.9 min, 26.1 km | **+15 min · +16 mi of beautiful road**; 34 vs 49 min, 0 vs 16 mi | screenshot 1 |
| Asheville → Blowing Rock, NC | 145.5 km, 98.3 min, 8.8 km | 130.3 km, 117.9 min, 55.1 km | +20 min · +29 mi; with Forest set to "more", +20 min · +26 mi | screenshot 4 |
| Denver → Estes Park, CO | 106.2 km, 82.3 min, 17.2 km | 102.9 km, 92.2 min, 17.8 km | Scenic adds 10 min for no more beautiful road: 11 mi either way | §4.2, §4.3 |
| Rocky Creek → Big Sur, CA (Highway 1) | 17 min, 11 mi, 11 mi beautiful | the same | Same as the fastest route | screenshot 3 |
| San Francisco → Los Angeles | refused, `TRIP_TOO_LONG`, 559.6 km | | "That trip is 348 miles in a straight line. …" | review notes |
| Toronto → Buffalo | refused, `OUTSIDE_COVERAGE` | | "Sunday Drive covers the contiguous United States, and that point is outside it." | review notes |

None of these crosses a seasonal stretch (`seasonal` empty on every arm).
Denver → Idaho Springs is the hero because it is the brief's 10–20 minutes,
goes from nothing to something, and is short enough to read at a glance; its
scenic arm is Clear Creek Canyon (US 6). The screenshot's destination is
Apple's "Idaho Springs, CO" search result, and its card matches the probe
exactly.

Candidates measured and not used (unweighted first pass, `pref` 0.5 unless
noted): SF → Monterey +53 min for 1 → 58 mi (+140 min for 1 → 74 mi at
`pref` 1); Front Royal → Luray, the same route; Asheville → Brevard +34 min
for 0 → 35 mi; Portland → Multnomah Falls +24 min for 4 → 13 mi; Seattle →
Snoqualmie +20 min for 0 → 6 mi; Salt Lake → Park City +47 min for 0 → 21 mi;
SF → Stinson Beach +2 min for 11 → 13 mi; Apple Park → Pescadero +24 min for
21 → 31 mi; Apple Park → Santa Cruz +8 min for no more.

### 2.3 The loops

All 80 km asked unless noted, with the app's weights.

| start | got | beautiful | driven twice | directions | used for |
| --- | --- | --- | --- | --- | --- |
| Apple Park, CA, 40 km (the default) | 41.6 km, 68.6 min | 5.9 km (14%) | 1.4 km | 7 of 8 | review notes |
| Apple Park, CA, 80 km | 72.5 km, 98.4 min | 48.7 km (67%) | 0.4 km | 8 of 8 | review notes |
| **Moab, UT** | 58 mi, 111 min | 48 mi (83%) | 0 | 4 of 8 | **screenshot 2** |
| Boulder, CO | 54 mi, 111 min | 47 mi (87%) | 0 | 7 | not used: Colorado has shot 1 |
| Golden, CO, 106 km (the review's foothills loop) | 66 mi, 123 min | 57 mi (86%) | 21.9 mi | 8 | not used: a third of it twice |
| Estes Park, CO | 50 mi, 86 min | 43 mi (85%) | 9.1 mi | 4 | — |
| Tahoe City, CA | 50 mi, 81 min | 46 mi (92%) | 19.2 mi | 6 | — |
| Brevard, NC | 49 mi, 89 min | 42 mi (86%) | 19.0 mi | 8 | — |
| Asheville, NC, 100 km | 63 mi, 122 min | 47 mi (74%) | 9.5 mi | 8 | — (2 seasonal stretches) |
| Carmel, CA | 55 mi, 115 min | 41 mi (74%) | 10.9 mi | 4 | — |
| Sedona, AZ | 50 mi, 95 min | 37 mi (73%) | 16.7 mi | 5 | — |
| Gatlinburg, TN | 48 mi, 104 min | 34 mi (71%) | 2.5 mi | 6 | — |
| Luray, VA | 59 mi, 120 min | 21 mi (36%) | 0.4 mi | 8 | — |
| Taos, NM | 65 mi, 109 min | 23 mi (35%) | 0.2 mi | 6 | — |
| Charlottesville, VA | 49 mi, 97 min | 9 mi (18%) | 0 | 8 | — |
| Bend, OR | 52 mi, 93 min | 5 mi (9%) | 0 | 7 | — |

Every response carried `beautiful_score` 7.0: the line is the same number in
every state, which is what the description's "ONE SCALE" paragraph says. The
loop limit (`POST /api/loop/limit`) was 400 km at Apple Park and Boulder. The
last rows are the risk the marketing plan names (§3.4): a loop from Bend,
5 of 52 miles beautiful, is what "beautiful wherever you are" would have
promised. And the reviewer's own default loop from Apple Park is 4 of 26
miles, which is why the notes also give the 50-mile one.

## 3. The App Review notes

`docs/app-store-submission.md` §5 now has a "Where does it work?" answer and
a block to paste, 1,477 bytes. A reviewer in Cupertino is inside coverage, so
the notes give a trip and a loop that start where they sit, the notice and
refusal someone outside the US sees, and the 310-mile cap with its sentence.
Figures are §2.2 and §2.3.

### 3.1 The production caveat

**Production serves the New England build** (outside review #4: "prod still
NE"). Until the owner deploys the national server, every Cupertino request a
reviewer makes is refused with production's old sentence, and the notes are
wrong. That is why the marketing plan now has a server gate before
submission (§9). The notes say only that the figures should be checked
against production on the day; the caveat itself is here and in the plan,
not in text a reviewer reads.

## 4. The app changes

### 4.1 The locate button

**Was:** `.mapControls { MapUserLocationButton() }` inside a map that runs
under the status bar (`.ignoresSafeArea(edges: .top)` on `PlanningView`).
Inside that modifier the map sees a top inset of 0, so MapKit put the button
at the very top, over the battery and Wi-Fi icons, on every planning screen
and in App Store screenshot 1.

**Now:** the map has no MapKit controls (`.mapControls {}`). The same
`MapUserLocationButton` and a `MapCompass`, tied to the map by a
`@Namespace` scope (`Map(scope:)`, `.mapScope`), are drawn in an overlay at
the top right, padded by `topInset + 8`. `topInset` is the one `PlanningView`
already reads outside its `ignoresSafeArea` for route framing, now passed to
`PlanningMap`. Outside `.mapControls` the button is a bare glyph, so it gets a
44 pt material platter.

**Checked in the simulator** (§6.1): on the iPhone 17 Pro Max and the iPhone
SE (3rd generation), iOS 26.4, the button sits below the status bar, and
Apple's logo and Legal link, bottom-left of the map card, are clear: the
overlay is top-right and cannot reach them.

### 4.2 The zero-gain headline

`RouteComparison.summary`, when the scenic route costs minutes and the whole
beautiful miles do not move:

| | sentence |
| --- | --- |
| was | Scenic adds **9 min** and leaves beautiful road at **11 mi** |
| now | Scenic adds **9 min** for no more beautiful road: **11 mi** either way |

And its fallback for a backend without `beautiful_km`, for the same reason:

| | sentence |
| --- | --- |
| was | Scenic adds **1 min** and leaves scenery at **5.3** |
| now | Scenic adds **1 min** for no more scenery: **5.3** either way |

"No more" leads, so the sentence cannot be read as a gain. The pinned tests
(`RouteComparisonTests`: `test_time_spent_for_no_more_beautiful_road_says_exactly_that`,
`test_minutes_that_buy_no_more_beautiful_road_never_read_plus_zero`, and the
score fallback's) were updated to the new wording. On today's national server
Denver → Estes Park at `pref` 0.5 is this case: +10 min, 11 mi either way
(§2.2; the brief measured +9 min).

### 4.3 What you'll pass

**Was:** each bar's width was its km over the *longest* row's km, with no
caption, so the bars read as slices of one drive. They overlap: a road through
woods beside a lake counts under forest and under water. On Denver → Estes
Park's scenic arm today the rows sum to 102 mi on a 64 mi route (forest 23,
hills 34, water 22, town 17, farmland 6); on Asheville → Blowing Rock, 183 on
81. The brief measured 108 on 64 and 97 on 47.

**Now:** each bar is drawn as a share of the whole route (`SceneryBreakdown`,
`RouteResults.swift`), so a full bar is the whole drive, and one caption
under the rows says what they are:

> Out of 64 mi. A mile beside water and forest counts in both.

One view for both pages: `DirectionsView` and `LoopView` had the same
`breakdown` body, and both now use `SceneryBreakdown`.
`RouteComparisonTests.test_the_breakdown_says_its_rows_overlap` pins the
caption.

### 4.4 ODbL §4.6

The routes are a Produced Work (§4.3: attribution, no share-alike), which the
comment already said. But they are produced from a Derivative Database (the
graph in `data/processed-*`), and §4.6 asks anyone who publicly uses such a
Produced Work to offer recipients the database or "the method of making the
alterations". The public repository is that method.

The OpenStreetMap entry on the Sources screen now carries, under its credit
and licence:

> Routes are planned on a modified copy of this data. How it is modified is
> public, in the app’s source code:
> github.com/Jamesk1281/SundayDrive

`DataSource` gained an optional `notice` and `noticeURL`, set only on
OpenStreetMap (`DataSources.odblMethod`, `DataSources.sourceCodeURL`); the
comment says why. `AttributionTests.test_the_osm_entry_offers_the_method_of_making_the_alterations`
pins it. The support page carries the same line and link (§5.1).

## 5. The pages

### 5.1 The support page's credits

**Was:** OSM, WorldCover and Terrain Tiles by name, with "the full credits for
OpenStreetMap and Terrain Tiles are on the app's Sources screen".

**Now:** all seven sources of `DataSources.all`, each with its name, every
credit line verbatim, its licence where it has one, and its link: OSM (with
Geofabrik and the §4.6 line), WorldCover, Terrain Tiles (all four upstream
lines, INEGI included), PAD-US 4.1, MVUM roads, NPS Public Roads, Apple Maps.
`tests/test_support_page.py` parses the `DataSource(...)` literals in
`AboutView.swift` and fails if any name, line or licence is missing from the
page, so a source added to the app and not to the page is caught. A mutation
check (deleting the INEGI line from the page) failed the Terrain Tiles case,
as it should.

### 5.2 Every support-page string

| was | now |
| --- | --- |
| "…or a loop from where you are, in the six New England states: Connecticut, Maine, Massachusetts, New Hampshire, Rhode Island and Vermont. Every road is scored for scenery from open data." | "…or a loop from where you are, anywhere in the 48 contiguous states and Washington, DC. Every road is scored for scenery from open data, on one scale." |
| **It says it only works in New England.** "Sunday Drive covers the six New England states only… type a New England town as the start… Only My Location needs you to be in New England." | **It says it won't work from here.** "Sunday Drive covers the 48 contiguous states and Washington, DC… type a town in those states as the start… Only My Location needs you to be inside them." |
| (none) | **It won't plan a long trip.** "Directions go up to 310 miles in a straight line. For a longer trip, pick a stop along the way and plan it in two parts. Loops have their own limit, which is lower in a dense city than in open country, and the loop slider shows it." |
| (none) | **Why do some places have so much more beautiful road?** "Every road is scored on one scale, so a road counts as beautiful at the same score in every state. Some places have far more of it than others. The route card shows how many miles of beautiful road each route has, so you can see what the scenic way buys before you take it." |

The third answer describes what the card does today. It does not say the app
warns about flat country, which is the open owner decision.

### 5.3 The privacy page and policy

`tests/test_privacy_page.py` pins the purpose string to `ios/project.yml`, and
it already quoted the national string, so the quoted text did not change.

| where | was | now |
| --- | --- | --- |
| page, effective date | 8 October 2026 | 23 October 2026 (the day this was written; set it to the day it goes live) |
| page, summary | "…to check that you are in New England… The New England check happens on your phone." | "…to show the map where you are, to plan drives from there, to check that you are in the area the app covers, and to guide you turn by turn. Moving the map and the area check happen on your phone." |
| page, Location | "three things"; "Checking that you are in New England. The app only has roads for the six New England states…" | "four things"; new first item **Showing the map where you are**: on the phone, the app sends nothing, Apple's map loads the area on screen; "Checking that you are in the area the app covers. The app only has roads for the 48 contiguous states and Washington, DC…" |
| page, Where your location goes | "Checking that you are in New England sends it to neither." | "Moving the map to where you are, and checking that you are in the area the app covers, send it to neither." |
| policy §2 | three uses; item 2 cites `NewEngland.contains` and `tools/build_new_england_boundary.py` | four uses; item 1 is the launch camera (`RouteModel.launchFix`, `PlanningView.swift:128`, `Region.swift:57`); item 3 cites `Coverage.contains` (`Coverage.swift:34`) and `ios/scripts/build_coverage_boundary.py`; three stale line numbers fixed |
| policy §2.1, §8 | "The New England check adds none"; "Any network call in the New England check" | the launch camera and the area check |
| policy status | | a dated line for the national build |

"Apple's map then loads the area on screen" is new and deliberate: moving the
camera sends the app's fix nowhere, but MapKit fetches the map for whatever is
on screen, as it does when anyone scrolls. Saying "nothing is sent" without it
would be the one untrue sentence on the page.

### 5.4 The listing, the review notes, the README and the captions

| where | was | now |
| --- | --- | --- |
| promotional text | "Peak color is moving south…" (launch), "Every road in New England, scored for scenery…" (evergreen), a spring line | "Every road in the contiguous US, scored for scenery on one scale. Move one slider to trade minutes for the view, or pick how long you have and loop home." (153); a Thanksgiving line (138) |
| description, coverage | "Every road in Connecticut, Maine, Massachusetts, New Hampshire, Rhode Island and Vermont, about 146,000 miles of it…" | "Every road in the 48 contiguous states and Washington, DC, about 4.8 million miles of it, has been scored for scenery from open map and satellite data, on one scale." |
| description, slider | "Drag from Fastest to Most scenic… how many more miles of beautiful road those minutes buy" | "Drag from Fastest to Scenic" (the slider's real labels)… "Sometimes the minutes buy no more beautiful road at all, and the card says that too." |
| description, new | | ONE SCALE: "A road counts as beautiful at the same score everywhere, so some places have far more of it than others. The numbers on the card are the same measurement wherever you are." |
| description, loops | "…over the best-scoring roads nearby…", "a whole day" | "…over roads it scores well…", "a long day out" |
| description, types | "coast, forest and parks…" | "coast, forest, parks and desert…" (the slider's own label) |
| description, score | water, coastline, woods, parks, farmland, viewpoints, hills, bends | adds desert and protected land, "hills and mountains" |
| description, limits | "New England only. Routes and loops have to start and end in the six states."; "Travel times are modeled" | "The 48 contiguous states and Washington, DC only."; the 310-mile line; "Travel times are estimates."; "Some roads close for the season, and the map doesn't know every closure."; "Scenery scores come from map data, so a road you love may score lower than it deserves." (all `BeforeYouDriveView`'s) |
| description, credits | OSM, WorldCover, Apple | adds Terrain Tiles, PAD-US, the Forest Service and the Park Service |
| keywords | `foliage,fall,leaf,peeping,loop,backroads,byway,curvy,road,trip,new,england,vermont,maine,hampshire` (98) | `backroads,loop,byway,curvy,road,trip,canyon,mountain,pass,country,park,coastal,winding,parkway,views` (100) |
| featuring, description | "Every road in the six New England states, about 146,000 miles… It launches for the last weekends of fall foliage, when New England is full of people…" | the national coverage, "forest and desert, parks… mountains", "roads it scores well", "The method and the code are public." (800 characters) |
| featuring, details | "Over 79 ratings made during test drives…"; "Coverage is New England only, by design… type a New England town… Concord, MA to Rockport, MA" | "Over 79 ratings the developer made on test drives in New England… Elsewhere the same scale is applied to the same kinds of open data, unchecked by a driver."; "Coverage is the 48 contiguous states and Washington, DC, so in Cupertino My Location and Loop work where you are. Apple Park to Boulder Creek, CA is a good first route." |
| featuring, name and date | `Sunday Drive launch, fall 2026`; 22 October 2026 | `Sunday Drive launch`; the planned release date |
| review notes | "Why does it only work in New England?"… Concord, MA → Rockport, MA (production, 2026-10-04); Kent, CT loop | "Where does it work?"; the pasteable block of §3: Apple Park → Boulder Creek, the default loop and the 50-mile one, the outside-US notice, the 310-mile refusal |
| README, opening | "Every road in the six New England states is scored… 236,000 km of road on a 998k-edge graph" | "Every road in the 48 contiguous states and Washington, DC is scored for beauty, on one scale… 7.8 million km of road on a 25.8M-edge graph… The test drives that checked the score were all in New England (below)." |
| shot 1 caption | "Every road in New England is scored for scenery. One slider sets what the view is worth to you." | "Every road in the contiguous US, scored for scenery on one scale. One slider sets what the view is worth." |
| shot 2 caption | "…over the best-scoring roads nearby…" | "…over roads it scores well…" |
| shot 4 | "Somewhere, or nowhere at all" (the home screen) | "More of what you like" (the tuning sheet) |
| store and banner copy | "Every road in New England, scored for scenery." | "Every road in the contiguous US, scored for scenery." |

## 6. Screenshots

Four raw 6.9" captures (1320 × 2868) in `app-store-screenshots/`, built into
`captioned/` with `app-store-screenshots/build.py`, and the 6.3" copies
(1206 × 2622) in `captioned-6.3/` resized from them with `sips -z`, as
`6848ba7` made the first set. The header banner, the two App Store creative
assets and the search-result mock-ups were rebuilt from the same captures.
**All four shots are outside New England**, in four states.

| # | file | place | what it shows | headline | line under it |
| --- | --- | --- | --- | --- | --- |
| 1 | `1-route-comparison.jpg` | Denver → Idaho Springs, Colorado | Directions at the default slider: "+15 min · +16 mi of beautiful road", 49 vs 34 min, 16 vs 0 mi; the bars with their new caption | Trade minutes for *the view* | Every road in the contiguous US, scored for scenery on one scale. One slider sets what the view is worth. |
| 2 | `2-loop.jpg` | Moab, Utah | An 80 km loop from My Location: "1 hr 51 · 58 mi", "48 miles of it beautiful", "no road driven twice", heading east, 4 of 8 directions | Nowhere to be? *Take a loop.* | Pick how long you have. It plans a round trip over roads it scores well, and brings you home. |
| 3 | `3-driving.jpg` | Highway 1, Big Sur, California | Driving, on the route: "0.4 mi · Continue onto Bixby Creek Bridge", Cabrillo Highway, 17 min · 11 mi | Every turn, *out loud* | Spoken directions, the next turn always on screen, and a new route if you miss one. |
| 4 | `4-tune.jpg` (new; `4-home.jpg` removed) | Asheville → Blowing Rock, North Carolina | *What you like* over the route, Forest, parks & desert set to "more", the route behind it now "+20 min · +26 mi of beautiful road" | More of what *you like* | Drag toward what you'd rather drive past. Routes update in the background as you drag. |

**Against the brief's rules:**
- *At least two outside New England:* four.
- *The hero trade costs about 10–20 minutes:* +15 min, on a 34-minute trip,
  for 0 → 16 mi of beautiful road. Shot 4's is +20 min.
- *The loop shot leads with a mostly beautiful loop:* 48 of 58 mi, 83%, no
  road twice.
- *No shot is half empty:* the old home shot was: two rows under the map and
  half a screen of nothing. It is replaced by the tuning sheet, which is also
  the one feature the old set did not show. Shot 1 has about a sixth of the
  screen empty above "Start driving"; the others are full.
- *Captions use the app's own words:* "Trade minutes for the view" and the
  loop headline are the old set's; "the view", "round trip", "Spoken
  directions", "Drag toward what you'd rather drive past" and "Routes update
  in the background as you drag" are the app's strings (`TuneView`). Nothing
  says best, most scenic, near you or wherever you are.
- *A place line under each phone* is new in `build.py`, so a caption never
  implies a place it does not show (§5.7 of the plan: "caption the place").
  The two backdrop photos, behind shots 1 and 3, are the owner's New England
  roads; they are decoration, and the place line says where the capture is.
  The owner may prefer national photos or none (§8).

**How they were taken.** On a simulator made for this unit (iPhone 17 Pro
Max, iOS 26.4), erased first so no test leftovers were in the app (checklist
16, verdict K-3), with a **Release** build (`-configuration Release`, so
`DriveTrace.isEnabled` is false and no recording dot shows), pointed at the
local national server with `SIMCTL_CHILD_SUNDAYDRIVE_API`. Location was
granted with `simctl privacy grant`, and the first-launch "Before you drive"
sheet was dismissed with Got it. The start was My Location each time
(`simctl location set` to Denver, Moab, Asheville and Rocky Creek), the
destination typed into the app's own search (Apple's results). The loop length
is the 80 km a driver would have picked last time (`lastLoopTargetKm`, set
with `defaults write`). Shot 3 is real playback (`simctl location start`, 14
m/s along the route's own geometry), taken once the app had matched the car
to the route. Its status-bar clock is the real time (3:05), so it agrees with
the 3:21 PM arrival; the others keep 9:41.

**Checked on the screen, not assumed:** each card's figures match §2.2 and
§2.3 to the mile and minute.

### 6.1 The locate button on two phones

| phone | locate button | status bar | Apple logo and Legal |
| --- | --- | --- | --- |
| iPhone 17 Pro Max | top right, below the status bar, on a material platter | clear | bottom left of the map card, clear |
| iPhone SE (3rd generation) | top right, 8 pt below the 20 pt status bar, on the home map and on the 132 pt map card while searching | clear | clear |

The overlay is top-right and the logo bottom-left, so no content of the
app's can reach the logo on any phone. On shot 4, MapKit's own label for
Great Smoky Mountains National Park is drawn over its own logo; that is
MapKit's rendering of its own map, not the app's content, and the logo is
not covered by anything of ours.

## 7. The New England claims test

`tests/test_no_new_england_claims.py` reads what reaches a reader and fails on
a New England coverage claim: "new england", "six states", "six New England
states", "six-state", and New England's network figures (146,811, 146,000,
236,000, 942,448, 998k).

**What it reads:** the fenced `text` blocks of `app-store-listing.md` and
`app-store-submission.md` (the pasted copy, not the maintainers' notes), the
visible text of `site/index.html` and `site/privacy/index.html` (comments and
styles dropped), §§0–6 of `docs/privacy-policy.md`, the README's opening
paragraph, every non-docstring string in `app-store-screenshots/build.py`,
and every string literal in `ios/Sources/*.swift` (comments dropped). A guard
test fails if any of them comes back nearly empty, so a renamed heading cannot
turn the check into a pass.

**The allow-list**, each entry with its reason, and a test that fails if an
entry no longer matches anything:

| where | allowed text | why |
| --- | --- | --- |
| `app-store-listing.md` | "Over 79 ratings the developer made on test drives in New England" | The featuring notes, read by Apple's editors only; §3.4 allows the 79-rating separation there and only there, scoped to New England and one rater |
| `privacy-policy.md` | "incomplete before the New England check existed" | History: what the policy said before 2026-10-04 |
| `README.md` | "The test drives that checked the score were all in New England" | A scoped truth that the README's measured claims rest on |

**The brief's first trap has moved.** "Driven in New England only" is no
longer in `BeforeYouDriveView`: review-fixes unit I removed it on 2026-10-20
(`review-fixes-app.md` §6), and no Swift string literal says New England
today. So the allow-list has no app entry. If the owner wants that line back,
it needs an entry.

54 tests, all passing. Three of them feed old sentences through the pattern
to show it catches them.

## 8. For the owner to sign off

1. **The new claims.** "about 4.8 million miles" (§2.1); "on one scale" and
   the "ONE SCALE" paragraph; "A road counts as beautiful at the same score
   everywhere"; the support page's "Why do some places have so much more
   beautiful road?". None says what the app does in flat country.
2. **The keywords** (`app-store-listing.md` §3, 100 bytes): the seasonal four
   out, `coastal,winding,parkway,views` in. At 100 bytes there is no slack; if
   any term is swapped, re-measure.
3. **The captions and places** (§6), and that the two backdrop photos are New
   England roads behind non-New-England captures.
4. **The featuring nomination: was it filed?** Its deadline for the old
   5 November date was 22 October, now past. Unknown here. If filed, its
   publish date and description need the national text; if not, the plan
   says file it at S.
5. **The App Review notes** (§3): the Cupertino trip and loop, and checking
   them on production on the day.
6. **The privacy page's new sentence** about Apple's map loading the area on
   screen (§5.3), and its effective date.
7. **The zero-gain sentence and the breakdown caption** (§4.2, §4.3): the
   wording is the app's voice, not the owner's yet.
8. **The ODbL line** (§4.4).
9. **The marketing plan's server gate and go/no-go additions** (§9).

## 9. The marketing plan, re-based

`docs/marketing-plan.md` §7 is now "relative to approval". No target dates;
the only calendar dates left are hard external ones: the domain's expiry
(28 October 2026), #30DayMapChallenge (November), Thanksgiving (26–29
November), and the 2027 seasons.

- **Milestones** (§7.1): M (done), D (the domain), **G, the server gate**, S,
  A, and L = the first Thursday after A and a passing go/no-go.
- **The server gate before S:** the national server deployed on the box, with
  `api/health` reporting the national region and pack; routes answered from
  10+ states through the public hostname, the review notes' trip and loop
  among them; a latency monitor that plans a route, not only `api/health`;
  and the snap-cap fix deployed. App Review tests against production.
- **Go/no-go** (§7.3), run at A: the six old items, adjusted, plus **7** the
  server's region matches the app, **8** the review notes still hold on
  production, **9** the privacy policy is the national one, **10** the
  featuring text is the national one.
- **The featuring nomination** is marked for the owner in §5.7, §7.4 and §12.
- **Phases** renumbered around G: now to G, G, S to A, A to L, launch week,
  the month after, winter. The Thanksgiving pitch and #30DayMapChallenge are
  spent only if L comes before them.
- §0, §5.5, §5.7, §10, §12 and §15 lost their target dates; §15 is now "Next,
  before submission". The 2026-10-18 decisions block is kept as history.

## 10. What is not done

- **Production.** §3.1. The server gate is the owner's.
- **The low-scenery fallback** is an open owner decision and is claimed
  nowhere. If it ships, screenshot 1 may need retaking (it is a strong trade,
  so it probably does not), and the "ONE SCALE" paragraph and the support
  FAQ can then say what the app says.
- **A screen recording for App Review** (submission checklist 13) is not made.
- **`docs/app-goes-national.md` §6** still lists the listing, notes and
  screenshots as "not done"; this document supersedes that list. Not edited,
  because it is that unit's record.
- **The README's build instructions** still build New England. They are
  developer instructions for the graph the test suite needs, not a coverage
  claim, and were left alone.
- **The replay red** in §11 is not this unit's and is not fixed.

## 11. Tests run

- Python: `SUNDAYDRIVE_DATA=data/processed-ne .venv/bin/python -m pytest`
  `tests`: **1,372 passed, 14 skipped**, 8 min 26 s. The three page tests
  alone (`test_no_new_england_claims`, `test_support_page`,
  `test_privacy_page`): 77 passed.
- iOS, on a simulator made for this unit (iPhone 17 Pro Max, iOS 26.4),
  `TEST_RUNNER_SUNDAYDRIVE_API` at the national server: `RouteComparisonTests`
  (28), `AttributionTests` (17) and `LocationTextAndContactTests` (5), 50 of 50
  passed, on the first build.
- iOS, the full suite on the same simulator after the last app change (the
  button's platter), against the national server: **537 tests, 502 passed,
  32 skipped, 1 failed**, 19.5 min. The failure is
  `DriveReplayTests.test_no_recorded_drive_hears_the_same_maneuver_twice` on
  the `drive-2026-10-06-122558` trace ("Sharp right onto Old North Dana
  Road" spoken twice, two assertions). It is the red recorded on `main` on
  2026-10-08 and again by units C and I (`app-goes-national.md` §5.1,
  `review-fixes-app.md`); nothing on the replay path changed here. The 32
  skips are the opt-in harnesses.
