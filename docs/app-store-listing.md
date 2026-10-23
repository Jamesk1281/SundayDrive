# App Store listing: promotional text, description, keywords

**Status, 2026-10-23: the national listing, drafted, not entered in App Store
Connect.** Written against `usa` at `936dfcf` for the binary that covers the
48 contiguous states and Washington, DC. It replaces the New England listing
of 2026-10-04, which was never entered and is in git history
(`git show 936dfcf:docs/app-store-listing.md`). What changed, line by line,
and the measurement behind every number, is
[`national-copy.md`](national-copy.md). The name (*Sunday Drive*) and subtitle
(*The scenic route, on purpose*, 28/30) are decided elsewhere and are not
reopened here.

Every claim below has to pass [`marketing-plan.md`](marketing-plan.md) §3.4,
which scopes each measured claim to where it was measured. In short: say only
what is true in every covered state. No "best", no "most scenic", no
"beautiful wherever you are", nothing about what the app does in flat country,
and compare only against the app's own fastest route.
`tests/test_no_new_england_claims.py` fails if a New England coverage claim
comes back into any pasted text below.

Every number below was measured with a script, not counted by eye. Re-measure
after any edit: the limits are hard and App Store Connect truncates silently in
some places and refuses in others.

| Field | Limit | This draft | Needs review to change? |
| --- | --- | --- | --- |
| Promotional text | 170 characters | 153 (launch), 138 (Thanksgiving) | **No**, edit any time |
| Description | 4,000 characters, plain text | 3,271 | Yes, ships with a version |
| Keywords | **100 bytes**, comma-separated | 100 | Yes, ships with a version |

---

## 1. Promotional text

Sits above the description and is the only field that changes without App
Review, so it is the seasonal one (`marketing-plan.md` §5.7). Paste the one that
matches the calendar.

**For launch, and any time no season is running, 153 characters:**

```text
Every road in the contiguous US, scored for scenery on one scale. Move one slider to trade minutes for the view, or pick how long you have and loop home.
```

**Thanksgiving week, 138 characters:**

```text
Driving somewhere for Thanksgiving? Move one slider and see what the scenic way costs, in minutes, against the fastest route. Then decide.
```

Spring and fall versions are written when those seasons come round, against
§3.4 again: seasonal lines belong here and on custom product pages, never in
the keywords.

---

## 2. Description

Plain text: App Store Connect strips HTML, so the section heads are capitals
and the lists are hyphens. The first three lines are all most people read
before "more", so they carry the thesis, the coverage and the trade.

```text
Every navigation app tries to save you time. Sunday Drive asks you to spend a little of it, on purpose.

Every road in the 48 contiguous states and Washington, DC, about 4.8 million miles of it, has been scored for scenery from open map and satellite data, on one scale. Then you decide how many minutes the view is worth.

ONE SLIDER
Drag from Fastest to Scenic and the route redraws. Sunday Drive always shows you the trade against its own fastest route, in plain numbers: how many minutes the scenic way adds, and how many miles of beautiful road come with them. Some drives cost nothing extra. Some cost an hour. Sometimes the minutes buy no more beautiful road at all, and the card says that too. Your call.

ONE SCALE
A road counts as beautiful at the same score everywhere, so some places have far more of it than others. The numbers on the card are the same measurement wherever you are.

LOOPS, FOR WHEN YOU HAVE NOWHERE TO BE
No destination? Pick a starting point and how long you have, from a short spin to a long day out. Sunday Drive plans a round trip over roads it scores well and brings you back where you started. Don't like the direction it chose? Pick another on the compass. Every loop tells you how many of its miles are beautiful and whether any of it doubles back.

ROADS THAT SUIT YOU
Tell it what you'd rather drive past: coast, forest, parks and desert, lakes and rivers, hills, farmland or town centers. Routes reshape in the background as you adjust.

WHAT GOES INTO THE SCORE
Each stretch of road is rated for what's beside it and what it's like to drive: water and coastline, woods, desert, parks and protected land, open farmland, viewpoints, the hills and mountains around it, and how much the road bends. Highways score low. It's a measurement, not a crowd vote, so the quiet road nobody has posted about gets the same look as the famous one.

TURN BY TURN
Spoken directions, the next turn always on screen, the name of the road you're on, and a new route if you miss a turn. Changed your mind mid-drive? Switch to the fastest route, or end a loop and head home the quick way.

WHAT IT DOESN'T DO
- The 48 contiguous states and Washington, DC only.
- Directions go up to 310 miles in a straight line. For a longer trip, plan it in parts.
- No live traffic. Travel times are estimates.
- No lane guidance.
- Needs a data connection. No CarPlay.
- Some roads close for the season, and the map doesn't know every closure. Follow posted signs.
- Scenery scores come from map data, so a road you love may score lower than it deserves.

FREE, WITH NOTHING ATTACHED
No account, no ads, no tracking and no in-app purchases. Your location goes to the routing server to plan your route, and the server doesn't store it. The app doesn't record your drives. The source code is public under the Apache License 2.0.

Please don't handle your phone while you drive. Mount it, plan before you go, and let the voice do the rest.

Map data from OpenStreetMap, available under the Open Database License. Tree cover from ESA WorldCover. Terrain from Terrain Tiles. Protected areas from USGS PAD-US. Seasonal closures from the USDA Forest Service and the National Park Service. Base map and place search by Apple. Full credits are on the app's Sources screen.
```

### Every claim, and where it is true

The description makes promises a reviewer and a driver can check, so each one
is pinned to the code or document that makes it true. If any of these changes,
change the description in the same commit.

| Claim | Source |
| --- | --- |
| 48 contiguous states and DC | `Coverage.areaName`, `Coverage.contains` (`ios/Sources/Coverage.swift`); the server's `/api/health` `region` reads "the contiguous United States" |
| "about 4.8 million miles" | 7,796,106 km = 4,844,276 mi, the sum of `length_m` over all 25,849,861 edges of `data/processed-us/graph_edges.parquet` (`national-copy.md` §2.1). Rounded down |
| Scored from open map and satellite data, on one scale | `DataSources.all` (`AboutView.swift`); one national scale, `national-scenery-scoring-verdict.md` (E1) |
| Fastest ↔ Scenic slider, redraws | `PrefSlider.swift` labels "Fastest" / "Scenic"; `PrefDial` in `DirectionsView.swift` recomputes on release |
| The trade, against **its own** fastest route | `RouteComparison.summary` (`RouteResults.swift`): "Scenic adds … min and turns … mi of beautiful road into … mi" |
| "Some drives cost nothing extra" | `summary`: "… at no extra time" |
| "the minutes buy no more beautiful road, and the card says that too" | `summary`: "Scenic adds 9 min for no more beautiful road: 11 mi either way" (`national-copy.md` §4.2) |
| "A road counts as beautiful at the same score everywhere" | `beautiful_score` is 7.0 in every response the server sent in `national-copy.md` §2; the one national scale |
| Loop from a starting point, "a short spin to a long day out" | typed start in `LoopView`; `LoopModel.minKm`/`maxKm` = 5–400 km; a dense metro tops out lower (`POST /api/loop/limit`) |
| Pick another direction on the compass | `LoopCompass.swift` |
| Beautiful miles, doubles back | `LoopView.swift`, "… mi doubles back" / "no road driven twice" |
| Scenery types, reshape in the background | `BeautyType.all`, "Forest, parks & desert" among them; `TuneView.swift` |
| Score components | `pipeline/score.py`: water, coast, forest (WorldCover, OSM), desert (E1), protected land (PAD-US), farmland, viewpoints, relief and vista, curvature, highway penalty |
| Spoken directions, current road, reroute | `VoiceGuide.swift`; `NavView.swift` |
| Switch to fastest / head home | `NavView.swift`, "Head home the fastest way?" |
| 310 miles | `RouteService.capMiles(RouteService.maxTripKm)`, the floor of 500 km; the server's `TRIP_TOO_LONG` sentence |
| No live traffic, no lane guidance, seasonal closures, scores from map data | `BeforeYouDriveView.limits` |
| Needs data, no CarPlay | `site/index.html` support page |
| No account, ads, tracking or IAP; server doesn't store location; no recording | `site/privacy/index.html` summary; `app-store-submission.md` §3; `DriveTrace.isEnabled` false in App Store builds |
| Apache 2.0 | `LICENSE` |
| The credits | `DataSources.all`, the Sources screen |

### What it deliberately leaves out

- **Other apps' names**, including the ones the loop mode resembles. Guideline
  2.3.7 and Apple's keyword rule both forbid it.
- **Comparisons with Apple Maps' routes.** ADPLA Attachment 6 §2.3
  (`legal-and-ip-audit.md`). The only comparison is with the app's own fastest
  arm.
- **"Best", "most scenic", "most beautiful".** The score is ours. Even
  "best-scoring", which the New England draft used, is gone: §3.4 rules out
  claims that read as ground truth.
- **What happens in flat country.** Whether the app should say so when a
  region has little high-scoring road is an open owner decision, and nothing
  in the binary does it yet. "ONE SCALE" says only what the card already
  shows.
- **Any rating figure.** The "96% liked" and 74%-against-63% figures are one
  rater's New England marks (§3.4). They stay in builder posts and the
  featuring notes (§6).
- **Locked-screen guidance.** No locked-screen drive has been recorded since
  the 2026-09-29 redesign.
- **"Free" in the keywords.** The listing shows the price already.
- **Unpaved-road avoidance.** The server supports `avoid_unpaved`, but the app
  exposes no control for it.

---

## 3. Keywords

**100 bytes, 15 terms:**

```text
backroads,loop,byway,curvy,road,trip,canyon,mountain,pass,country,park,coastal,winding,parkway,views
```

Measured with `printf %s "<keywords>" | wc -c`: **100**.

Built from `marketing-plan.md` §5.7's national candidate (96 bytes), with the
four seasonal terms (`foliage,fall,leaf,peeping`, 26 bytes) taken out, because
the launch is in November and seasonal terms belong on a custom product page
later. The 30 bytes that freed went to non-seasonal national intent:

| added | bytes with its comma | what it reaches, with words already indexed |
| --- | --- | --- |
| `coastal` | 8 | "coastal drive", "coastal road", "coastal route" |
| `winding` | 8 | "winding roads", "winding drive" |
| `parkway` | 8 | "scenic parkway", parkway drives anywhere |
| `views` | 6 | "scenic views", "drive with views" |

Rules it follows (Apple's own help page, the `app-store-listing-limits`
reference):

- **Bytes, not characters.** All ASCII, so 100 characters is 100 bytes.
- **Nothing from the name or subtitle.** "sunday", "drive", "scenic", "route",
  "purpose" are already indexed. Apple combines keywords with name and
  subtitle words, so "curvy" plus the name's "drive" reaches "curvy drive",
  and "scenic" from the subtitle plus "byway" reaches "scenic byway".
- **Single words, no spaces.** "road,trip" reaches "road trip", "mountain,pass"
  reaches "mountain pass", and "country,road" reaches "country road".
- **No state names.** National search, and one state's name would say the app
  is regional.
- **No competitor or company names.** None appear.
- **Nothing seasonal.**

**If a custom product page takes keywords later** (`marketing-plan.md` §5.7),
those bytes come out of the same 100. The foliage terms go on a foliage page
then.

---

## 4. Before pasting

- [ ] Re-measure all three fields with a script after any edit. Promotional
      text and description in characters, keywords in bytes.
- [ ] The production server answers for the whole country
      (`marketing-plan.md` §7.1, the server gate). Until then the listing
      describes an app that production cannot serve.
- [ ] The screenshots are the national set (`app-store-screenshots/captioned`,
      `national-copy.md` §6).
- [ ] Ask one person who has never seen the app to read the first three lines
      and say what it does. If they can't, rewrite the first three lines.

---

## 5. What this was checked against

`usa` at `936dfcf`, plus this unit's own app changes (the zero-gain sentence,
the breakdown caption, the locate button, the §4.6 line), which are on
`claude/national-copy-7a6577` until it merges.

---

## 6. Featuring nomination

App Store Connect → Featuring → **Nominations** → *App Launch*. Apple wants it
at least two weeks before the publish date. **Whether it was filed for the
original 5 November date is not known** (`national-copy.md` §8): the 22 October
deadline for that date has passed. If it was not filed, file it at least two
weeks before the release date, whenever that is, and set the publish date to
match. Apple's help page (read 2026-10-05) gives no character limits for the
text fields. The description below is kept under 1,000 characters anyway.

| Field | Entry |
| --- | --- |
| Nomination name (internal only) | `Sunday Drive launch` |
| Type | App Launch |
| Publish date | the planned release date (L, `marketing-plan.md` §7.1) |
| Platforms | iOS |
| Countries or regions | United States (filled in from availability) |
| Related apps | None |
| In-app events | None |
| Supplemental materials | `https://jamesk1281.github.io/SundayDrive/` and `https://github.com/Jamesk1281/SundayDrive`; add a drive video link once one exists |

**Description, 800 characters:**

```text
Every navigation app tries to save you time. Sunday Drive asks you to spend a little of it, and shows you exactly what those minutes buy.

Every road in the 48 contiguous states and Washington, DC, about 4.8 million miles of them, is scored for scenery on one scale, from open map and satellite data: water and coastline, forest and desert, parks, farmland, mountains, and how much the road bends. One slider trades travel time for the view, and the app states the trade in plain numbers against its own fastest route.

With nowhere in particular to be, Loop takes how long you have and plans a round trip over roads it scores well, then brings you home. Spoken turn-by-turn directions handle the rest, so the phone stays mounted.

No account, no ads, no tracking. The method and the code are public.
```

**Helpful details:**

```text
Sunday Drive was designed and built by one person, a Northeastern University student in Massachusetts, as an independent project.

The scenery score was checked against real drives rather than assumed. Over 79 ratings the developer made on test drives in New England, it ranked a road the driver liked above one they did not 74% of the time, against 63% expected by chance. Travel times were fitted to recorded drives the same way. Elsewhere the same scale is applied to the same kinds of open data, unchecked by a driver.

Coverage is the 48 contiguous states and Washington, DC, so in Cupertino My Location and Loop work where you are. Apple Park to Boulder Creek, CA is a good first route.

The source code is public under the Apache License 2.0, and every data source is credited in the app.
```

The measured rating figure belongs here and not in the listing (§2): this text
is read by Apple's editors, not shown to customers, and it says where and by
whom it was measured (`marketing-plan.md` §3.4).
