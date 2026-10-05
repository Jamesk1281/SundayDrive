# App Store listing: promotional text, description, keywords

**Status, 2026-10-04: drafted, not entered in App Store Connect.** Written
against `main` `8e4e5c7` plus the four unmerged branches listed in §5, whose
user-facing changes the copy already allows for. The name (*Sunday Drive*) and
subtitle (*The scenic route, on purpose*, 28/30) are decided elsewhere
(`sunday-drive-naming.md`, `marketing-plan.md` §3.1) and are not reopened here.

Every number below was measured with a script, not counted by eye. Re-measure
after any edit: the limits are hard and App Store Connect truncates silently in
some places and refuses in others.

| Field | Limit | This draft | Needs review to change? |
| --- | --- | --- | --- |
| Promotional text | 170 characters | 160 | **No**, edit any time |
| Description | 4,000 characters, plain text | 2,731 | Yes, ships with a version |
| Keywords | **100 bytes**, comma-separated | 98 | Yes, ships with a version |

---

## 1. Promotional text

Sits above the description and is the only field that changes without App
Review, so it is the seasonal one (`marketing-plan.md` §5.7). Paste the one that
matches the calendar.

**For launch (foliage, October 2026), 160 characters:**

```text
Peak color is moving south. Tell Sunday Drive how long you have and it plans a loop from where you are, over the best-scoring roads nearby, and brings you home.
```

**Evergreen (winter, or any time a season isn't running), 156 characters:**

```text
Every road in New England, scored for scenery. Move one slider to trade minutes for the view, or pick how long you have and take a loop home the pretty way.
```

**Spring opener (Memorial Day 2027), 156 characters:**

```text
The back roads are open again. Pick how long you have and Sunday Drive plans a loop over the best-scoring roads nearby, then brings you home the pretty way.
```

"Best-scoring" rather than "most beautiful" on purpose: the score is ours, and
`marketing-plan.md` §3.4 rules out claims that imply ground truth.

---

## 2. Description

Plain text: App Store Connect strips HTML, so the section heads are capitals
and the lists are hyphens. The first three lines are all most people read
before "more", so they carry the thesis, the coverage and the trade.

```text
Every navigation app tries to save you time. Sunday Drive asks you to spend a little of it, on purpose.

Every road in Connecticut, Maine, Massachusetts, New Hampshire, Rhode Island and Vermont, about 146,000 miles of it, has been scored for scenery from open map and satellite data. Then you decide how many minutes the view is worth.

ONE SLIDER
Drag from Fastest to Most scenic and the route redraws as you go. Sunday Drive always shows you the trade against its own fastest route, in plain numbers: how many minutes the scenic way adds, and how many more miles of beautiful road those minutes buy. Some drives cost nothing extra. Some cost an hour. That's your call.

LOOPS, FOR WHEN YOU HAVE NOWHERE TO BE
No destination? Pick a starting point and how long you have, from a short spin to most of an afternoon. Sunday Drive plans a round trip over the best-scoring roads nearby and brings you back where you started. Don't like the direction it chose? Try another. Every loop tells you how many of its miles are beautiful and whether any of it doubles back.

ROADS THAT SUIT YOU
Tell it what you'd rather drive past: coast, forest and parks, lakes and rivers, hills, farmland or town centers. Routes reshape in the background as you adjust.

WHAT GOES INTO THE SCORE
Each stretch of road is rated for what's beside it and what it's like to drive: water and coastline, woods and parks, open farmland, viewpoints, the hills around it, and how much the road bends. Highways score low. It's a measurement, not a crowd vote, so the quiet road nobody has posted about gets the same look as the famous one.

TURN BY TURN
Spoken directions, the next turn always on screen, the name of the road you're on, and a new route if you miss a turn. Changed your mind mid-drive? Switch to the fastest route, or end a loop and head home the quick way.

WHAT IT DOESN'T DO
- New England only. Routes and loops have to start and end in the six states.
- No live traffic. Travel times are modeled, not measured live.
- No lane guidance.
- Needs a data connection. No CarPlay.
- Some roads close for part of the year, and the app may not know about every one. Follow posted signs.

FREE, WITH NOTHING ATTACHED
No account, no ads, no tracking and no in-app purchases. Your location goes to the routing server to plan your route, and the server doesn't store it. The app doesn't record your drives. The source code is public under the Apache License 2.0.

Please don't handle your phone while you drive. Mount it, plan before you go, and let the voice do the rest.

Map data from OpenStreetMap, available under the Open Database License. Tree cover from ESA WorldCover. Base map and place search by Apple. Full credits are on the app's Sources screen.
```

### Every claim, and where it is true

The description makes promises a reviewer and a driver can check, so each one
is pinned to the code or document that makes it true. If any of these changes,
change the description in the same commit.

| Claim | Source |
| --- | --- |
| Six states, "about 146,000 miles" | 236,000 km in `BeforeYouDriveView.swift` and the README; 146,811 mi in `marketing-plan.md` §0 |
| Scored from open map and satellite data | OSM, ESA WorldCover, Terrain Tiles: `AboutView.swift` `DataSources`, `docs/data-sources.md` |
| Fastest ↔ Most scenic slider, redraws as you drag | `PrefSlider.swift:71-75` labels; `DirectionsView.swift:172` |
| The trade, against **its own** fastest route | `RouteResults.swift` ("Scenic adds … min"); the "+N mi of beautiful road" gain is C-3 (`ce25d1f`, unmerged). The wording "how many more miles" is true of `main` only once C-3 merges; on `main` alone the readout prints the scenic total |
| "Some drives cost nothing extra" | `RouteResults.swift:237` "at no extra time" |
| Loop from a starting point, "short spin to most of an afternoon" | `LoopView.swift:173` typed start; `LoopModel.minKm`/`maxKm` = 5–200 km, about 3 h 50 at the top end (`LoopView.swift:248`) |
| Try another direction | `LoopView.swift:212-215` |
| Beautiful miles, doubles back | `LoopView.swift:291-307` |
| Six scenery types, reshape in the background | `BeautyType.all`; `TuneView.swift:30` |
| Score components, highways score low | `docs/scoring.md` opening paragraph (water, coast, forest/parks, farmland, viewpoints, curvature, relief, highway penalty) |
| Spoken directions, current road, reroute | `VoiceGuide.swift`; `NavView.swift:548-560`; `NavView.swift:255` "Off route / Finding a way back" |
| Switch to fastest / head home | `NavView.swift:180-188` |
| No live traffic, no lane guidance | `BeforeYouDriveView.swift` "What it does not do" |
| Needs data, no CarPlay | `site/index.html` support page |
| Seasonal closures | EULA §3; true whether or not C-1 (`claude/inspiring-cannon-89c90c`) merges, since C-1 covers only roads OSM tags as seasonal |
| No account, ads, tracking or IAP; server doesn't store location; no recording | `site/privacy/index.html` summary; `app-store-submission.md` §3; `DriveTrace.isEnabled = false` |
| Apache 2.0 | `LICENSE` |

### What it deliberately leaves out

- **Other apps' names**, including the ones the loop mode resembles. Guideline
  2.3.7 and Apple's keyword rule both forbid it.
- **Comparisons with Apple Maps' routes.** ADPLA Attachment 6 §2.3
  (`legal-and-ip-audit.md`). The only comparison is with the app's own fastest
  arm.
- **"Best", "most beautiful" as fact.** "Most scenic" appears only as the
  slider's own label.
- **The 5.7% ETA error and the 74% scenery separation.** Both are real
  (`README.md`), but they come from two drives and 79 marks. In a listing they
  read as product claims Apple can call unverifiable (2.3.7), and
  "Travel times are modeled" is the honest version.
- **Locked-screen guidance.** The background audio mode was measured working on
  2026-08-30, but there is no recorded locked-screen drive since the 2026-09-29
  redesign. Add "keeps talking with the screen off" after one.
- **"Free" in the keywords.** The listing shows the price already, and
  `marketing-plan.md` §3.3 says not to spend bytes on it. The description says
  it because "what's the catch" is the first question a free app gets.
- **Unpaved-road avoidance.** The server supports `avoid_unpaved`, but the app
  exposes no control for it.

---

## 3. Keywords

**98 bytes, 15 terms:**

```text
foliage,fall,leaf,peeping,loop,backroads,byway,curvy,road,trip,new,england,vermont,maine,hampshire
```

Rules it follows (`app-store-listing-limits` reference, Apple's own help page):

- **Bytes, not characters.** All ASCII, so 98 characters is 98 bytes.
- **Nothing from the name or subtitle.** "sunday", "drive", "scenic", "route",
  "purpose" are already indexed, and repeating them wastes bytes. Apple combines
  keywords with name and subtitle words, so "curvy" plus the name's "drive"
  reaches "curvy drive", and "scenic" from the subtitle plus "byway" reaches
  "scenic byway".
- **Single words, no spaces.** Apple builds phrases from separate terms, so
  "leaf,peeping" reaches "leaf peeping", "road,trip" reaches "road trip", and
  "new,england" / "new,hampshire" reach both states.
- **No competitor or company names.** None appear.

**The one change from `marketing-plan.md` §5.7's 95-byte candidate:** `autumn`
out, `hampshire` in. US searchers say "fall", which is already there, and
"autumn" mostly duplicates it. "hampshire" completes **New Hampshire** with the
"new" already paid for, so the White Mountains state gets a search term for 9
bytes. That leaves Massachusetts, Connecticut and Rhode Island without one;
together they cost 34 bytes, which nothing in the list could free up.

**If a custom product page takes keywords later** (`marketing-plan.md` §5.7, up
to 70 pages since July 2025), those bytes come out of the same 100. Move
`foliage,fall,leaf,peeping` to a foliage page then, and spend the main page's
freed bytes on `massachusetts` and `coastal`.

---

## 4. Before pasting

- [ ] Re-measure all three fields with a script after any edit. Promotional
      text and description in characters, keywords in bytes.
- [ ] Merge C-3 (`claude/jolly-easley-2a7ea1`) before submitting, or change
      "how many more miles of beautiful road those minutes buy" to "how many
      miles of beautiful road you get".
- [ ] Take the screenshots after the merges too (store-readiness note,
      2026-10-04), so the slider readout in them matches the description.
- [ ] Ask one person who has never seen the app to read the first three lines
      and say what it does. If they can't, rewrite the first three lines.

---

## 5. Branches this was checked against

| Branch | Commit | Effect on the listing |
| --- | --- | --- |
| `claude/jolly-easley-2a7ea1` | `ce25d1f` | C-3: the readout prints the gain ("+11 mi of beautiful road"). The description's "how many more miles" assumes it |
| `claude/inspiring-cannon-89c90c` | `1e3e985` | C-1 seasonal closures. "May not know about every one" stays true either way |
| `claude/distracted-dijkstra-c31f91` | `a1b65c6` | In-app contact and the fuller location purpose string. No copy change needed |
| `claude/strange-dewdney-4a01fd` | `8212831` | Map framing only. No copy change needed |

---

## 6. Featuring nomination

App Store Connect → Featuring → **Nominations** → *App Launch*. Apple wants it
at least two weeks before the publish date, so for 22 October file it by
**8 October**. Apple's help page (read 2026-10-05) gives no character limits for
the text fields. The description below is kept under 1,000 characters anyway,
because the people reading it see hundreds of these.

| Field | Entry |
| --- | --- |
| Nomination name (internal only) | `Sunday Drive launch, fall 2026` |
| Type | App Launch |
| Publish date | 22 October 2026, or the real release date if it moves |
| Platforms | iOS |
| Countries or regions | United States (filled in from availability) |
| Related apps | None |
| In-app events | None |
| Supplemental materials | `https://jamesk1281.github.io/SundayDrive/` and `https://github.com/Jamesk1281/SundayDrive`; add a drive video link once one exists |

**Description:**

```text
Every navigation app tries to save you time. Sunday Drive asks you to spend a little of it, and shows you exactly what those minutes buy.

Every road in the six New England states, about 146,000 miles of them, is scored for scenery from open map and satellite data: water and coastline, forest, farmland, hills, and how much the road bends. One slider trades travel time for the view, and the app states the trade in plain numbers against its own fastest route.

With nowhere in particular to be, Loop takes how long you have and plans a round trip over the best-scoring roads nearby, then brings you home. Spoken turn-by-turn directions handle the rest, so the phone stays mounted.

It launches for the last weekends of fall foliage, when New England is full of people looking for exactly this drive. No account, no ads, no tracking.
```

**Helpful details:**

```text
Sunday Drive was designed and built by one person, a Northeastern University student in Massachusetts, as an independent project.

The scenery score was checked against real drives rather than assumed. Over 79 ratings made during test drives, it ranked a road the driver liked above one they did not 74% of the time, against 63% expected by chance. Travel times were fitted to recorded drives the same way.

Coverage is New England only, by design, because every road is measured from regional data. If you review the app outside the region, type a New England town as the start; Concord, MA to Rockport, MA is a good first route.

The source code is public under the Apache License 2.0, and every data source is credited in the app.
```

The two measured figures belong here and not in the listing (§2): this text is
read by Apple's editors, not shown to customers, and it cites how they were
measured (`README.md`, `docs/measuring-scenery.md`).
