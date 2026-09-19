# Legal and IP audit: everything Scenic could be sued or rejected over

**Audited 2026-09-01, against `main` + `claude/data-attribution`.** This goes
wider than `licensing-and-attribution-brief.md`, which covered only the three
open geodata sets. Everything below was read from a primary source — a contract,
a licence, a registry, or the repo — and the source is cited so it can be
re-checked rather than re-believed.

**I am not a lawyer and this is not legal advice.** Two items below (the name,
and the privacy-policy obligations) turn on facts a professional has to clear.
Everything else is a documented term of an agreement already signed by anyone
holding an Apple developer account, checked against what the code does.

**The headline: the data attribution that shipped on 2026-08-31 was the smaller
half of the problem.** The larger half is Apple's, and the largest single item is
the *name*.

---

## Risk register, worst first

| # | Item | Status | Source | Cost to fix |
| --- | --- | --- | --- | --- |
| 1 | **"Scenic" is taken by a senior direct competitor**, and is descriptive | **Rename before spending anything on brand** | App Store; TM doctrine | Rename |
| 2 | Apple's map attribution is **obscured** by the planning sheet | **Confirmed breach, unfixed** | ADPLA Att. 6 §2.1 | ~150 lines (UIKit wrapper) |
| 3 | **No EULA** carrying the required route-guidance notice | **Confirmed gap** | ADPLA §3.3.15 | ~1 hour |
| 4 | **No privacy policy URL** — a hard App Store submission gate | Confirmed missing | App Store Connect | ~2 hours |
| 5 | Drive traces **persist Apple-derived coordinates** | Technically engaged, low enforcement risk | ADPLA Att. 6 §2.5 | ~20 lines |
| 6 | No `PrivacyInfo.xcprivacy` | Known, already recorded | Apple submission rule | ~1 hour |
| 7 | Geofabrik asks for its own credit line | Cheap courtesy/insurance | download.geofabrik.de | 1 line |
| 8 | App icon is generated — may not be **ownable** | Branding, not infringement | US Copyright Office | Redraw |
| 9 | Third-party code licences | **Clean — nothing owed** | venv metadata | none |
| 10 | OSM / WorldCover / Terrain Tiles attribution | **Done 2026-08-31** | 41cbae7 | done |

---

## 1. The distributed artifact carries no third-party code obligations

Worth stating first because it is the one place with genuinely nothing to do.

- `ios/project.yml` declares **no Swift Package, no CocoaPods, no Carthage**, and
  there is no `Package.swift` or `.xcworkspace`. The app imports only
  `SwiftUI`, `MapKit`, `CoreLocation`, `AVFoundation`, `UIKit`, `Foundation`,
  `Observation` — all Apple frameworks.
- **So the thing that ships to users contains no third-party code at all.** No
  NOTICES file, no bundled licence list, no copyleft exposure in the binary.

The Python side (`pipeline/`, `server/`) never ships to a user. Scanned all 56
installed distributions in `.venv` for copyleft:

- Everything is permissive: BSD-2/3, MIT, Apache-2.0, PSF, ZPL-2.1.
- **One MPL-2.0**: `certifi`. MPL-2.0 is file-level copyleft — it obliges sharing
  modifications *to the MPL'd files*, and nothing here modifies certifi. It is
  also server-side only. **Nothing owed.**
- **No GPL, no AGPL, no LGPL anywhere.** AGPL is the one that would have bitten,
  because it reaches network services and `server/app.py` is exactly that.

**How to keep it true:** an AGPL dependency added to `server/` later would oblige
offering the whole service's source. Check the licence before adding to
`pipeline/requirements.txt` — it is a one-line check now and an unpickable knot
later.

## 2. Apple — the Developer Program License Agreement, Attachment 6

This is the agreement in force for anyone shipping a MapKit app. Quotes below are
verbatim from the executed ADPLA text filed with the SEC by a licensee
([Glu Mobile exhibit 10.23a](https://www.sec.gov/Archives/edgar/data/1366246/000155837021002009/gluu-20201231xex10d23a.htm)),
cross-checked for current numbering against Apple's own
[Program agreements page](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/).
**Verify exact wording against the current PDF before relying on it** — the
clause *numbering* (Attachment 6, §2.1–2.7, §3.3.15) is stable across both, but
the text I quote is from the 2020/21 execution.

The definition that makes several of these bite:

> "**Map Data**" means any content, data or information provided through the
> Apple Maps Service including, but not limited to, imagery, terrain data,
> **latitude and longitude coordinates**, transit data, points of interest and
> traffic data.

### 2a. The good news: Scenic's core architecture is expressly permitted

§3.3.15 opens by contemplating exactly what this app does:

> If You choose to provide Your own location-based service, data and/or
> information in conjunction with the Apple maps provided through the Apple Maps
> Service (**e.g., overlaying a map or route You have created on top of an Apple
> map**), You are solely responsible for ensuring that Your service, data and/or
> information correctly aligns with any Apple maps used.

So drawing an OSM-derived route over an Apple basemap is not a grey area, it is
the named example. There is **no** clause prohibiting third-party routing, and no
clause requiring you to use `MKDirections`. The fleet/asset/insurance
prohibitions in §1.2 are scoped to *MapKit JS on non-Apple hardware* and do not
touch a native iPhone app. **Scenic's fundamental design is fine.**

### 2b. §2.1 — the obscured Apple attribution is a breach (item 2)

> 2.1 Neither You nor Your Application, website or web application may remove,
> **obscure** or alter Apple's or its licensors' copyright notices, trademarks,
> logos, or any other proprietary rights or legal notices, documents or
> hyperlinks that may appear in or be provided through the Apple Maps Service.

**Measured: it is obscured.** The Apple logo + "Maps" wordmark sits at the map's
bottom-left; `RoutePanel` clips it so only the logo and "Ma" are legible. This
does **not** vary by detent, because a sheet's bottom edge is pinned to the
bottom of the screen at every detent — the detent moves only its top edge, and
MapKit pins its ornament to the map's bottom-left. Verified by screenshot at
`.planningCompact`, at `.medium`, and at the 0.85-of-screen height the compact
detent takes at the AX5 text size.

This was previously written up as an App Review risk. **It is more than that: it
is a term of the agreement**, and "obscure" is the exact verb.

**Two fixes tried and measured NOT to work**, both reverted:

| Attempt | Result |
| --- | --- |
| `.safeAreaPadding(.bottom, 380)` after `.ignoresSafeArea()` | Ornament unmoved (pixel-identical crop). Also leaked into the presented sheet's safe area and pushed `RoutePanel`'s own footer off the bottom at `.medium`. |
| `.safeAreaInset(edge: .bottom) { Color.clear.frame(height: 380) }` | Ornament unmoved. Footer survived. |

The second is the pattern `NavView.swift:53-55` already uses, so it is not that
the codebase is doing something unusual — **SwiftUI's `Map` simply exposes no way
to move the Apple ornament.**

**The fix that should work**, not attempted because it is a refactor rather than
a cleanup: UIKit's `MKMapView` positions the legal label inside its
`layoutMargins`. Wrapping `MKMapView` in a `UIViewRepresentable` and setting
`layoutMargins.bottom` to the live sheet height is the documented lever. Cost:
re-implementing the polyline/marker/user-location content that `Map`'s result
builder currently gives for free, in both `ContentView` and `NavView`.

**Design decision that has to be made with it:** what happens at `.large`, where
the sheet covers ~92% of the screen. Apple Maps itself lets its attribution go
off-screen with the map at full sheet height, which is the strongest precedent to
follow — but it means the honest answer is "visible whenever the map is
meaningfully visible", not "always".

### 2c. §3.3.15 — the missing EULA notice (item 3)

The same clause continues:

> For Applications that use location-based APIs for real-time navigation
> (including, but not limited to, **turn-by-turn route guidance** and other
> routing that is enabled through the use of a sensor), You must have an
> end-user license agreement that includes the following notice: **YOUR USE OF
> THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK. LOCATION DATA
> MAY NOT BE ACCURATE.**

Scenic is squarely inside this: `NavigationModel` drives turn-by-turn guidance
from `CoreLocation` fixes, and `VoiceGuide` speaks them. **There is no EULA in
the repo at all** — no hits for `end-user licen`, `EULA`, or `terms of use`
anywhere.

This is the cheapest item on the list with the clearest text. Two routes:

1. Rely on Apple's **standard EULA** (the "Licensed Application End User License
   Agreement"), which App Store apps get by default — but that standard document
   does **not** contain this notice, so it does not discharge §3.3.15 on its own.
2. Supply a **custom EULA** in App Store Connect containing the notice verbatim,
   and — because a driver should actually see it — surface the sentence in-app.
   The "Data sources" sheet added in 41cbae7 is the natural home; it is already
   one tap from the main screen and already the app's legal surface.

**Note the notice is a fixed string with fixed capitalisation.** It is quoted
above exactly; do not paraphrase it, and do not soften "AT YOUR SOLE RISK".

There is a real safety dimension here too, independent of Apple: this app
deliberately routes drivers onto small rural roads, and its own README lists
`via`-way turn restrictions and lane guidance as unimplemented. A prominent
"don't drive off a cliff following this" notice is warranted on the merits.

### 2d. §2.5 — drive traces store Apple-derived coordinates (item 5)

> 2.5 Unless otherwise expressly permitted in the MapKit Documentation or MapKit
> JS Documentation, Map Data may not be cached, pre-fetched, or **stored** by You
> or Your Application, website, or web application other than on a temporary and
> limited basis solely to improve the performance of the Apple Maps Service with
> Your Application.

`DriveTrace` writes a permanent header containing:

- `"dest": [destination.latitude, destination.longitude]` (`DriveTrace.swift:121`)
- `header["from"] = [origin.latitude, origin.longitude]` (`:126`)
- `record["req_lat"] / ["req_lon"]` (`:226-227`)

When the user searched an address, those coordinates came from `MKLocalSearch` or
`CLGeocoder` — and "latitude and longitude coordinates" is *named* in the Map
Data definition. They are written to `Documents/traces/*.ndjson`, which
`UIFileSharingEnabled` deliberately exposes for copying off over a cable.
Permanent, and not for Apple's performance. **The clause is engaged.**

Calibration, honestly: Apple enforces §2.2/§2.5 against scraping and database
building, and a single-user research log of a dozen drives is nowhere near that.
The realistic exposure is **low**. But it is also **cheap to remove entirely**,
and the removal is better engineering anyway:

**The fix:** record the *snapped* coordinate the router actually used — a node in
Scenic's own OSM-derived graph, returned in the API response — instead of the raw
geocoder output. The trace becomes strictly more truthful (it records the point
the route was actually computed from, not the point requested, and
`docs/` already documents that these differ by a median 99 m), and no Apple Map
Data is persisted. Fixes item 5 and improves the instrument in one change.

Two things that are currently **fine and should stay that way**:

- **`server/` logs nothing.** Grepped: only startup `print`s, no access log, no
  request logging, no persistence of coordinates. If request logging is ever
  added to the hosted API, it would put Apple-derived coordinates in a server-side
  log — the same clause, at much larger scale, on a machine that is not the
  user's. Log the *snapped graph node*, never the raw request, if it is added.
- CoreLocation *fixes* (`"lat"/"lon"` from `location.coordinate`) are the device's
  own sensor output, not Apple Maps Service output. Storing those is unrestricted.

### 2e. §2.2 and §2.3 — two bright lines never to cross

> 2.2 ... For example, neither You nor Your Application may use or make available
> the Map Data, or any portion thereof, **as part of any secondary or derived
> database**.

> 2.3 ... you **may not use or compare the data provided by the Apple Maps
> Service for the purpose of improving or creating another mapping service**. You
> agree not to create or attempt to create a substitute or similar service
> through use of or access to the Apple Maps Service.

Currently **compliant**, and it matters that it stays that way, because both
lines run very close to how this project naturally works:

- The `.parquet` graph is built purely from OSM by `pipeline/extract.py` and
  `pipeline/graph.py`. **No Apple data enters it.** Keep it that way — pooling
  drive traces (which today carry Apple-geocoded endpoints, see §2.5) into an
  analysis dataset is the most likely accidental route to a "derived database".
- The app **does not call `MKDirections`** — grepped, zero hits. This is
  load-bearing. The single most tempting experiment in this repo is "how does my
  ETA/route compare to Apple's?", and §2.3 prohibits exactly that comparison
  when done to improve your own routing. **Benchmark against recorded drives and
  the clock, which is what `docs/directions-accuracy.md` and the trace
  instrument already do — never against Apple's answer.**

### 2f. §2.4 — surfacing place names without the map

> 2.4 ... when displaying it on a map, You agree that it will be displayed only
> on an Apple map provided through the Apple Maps Service. Further, You may not
> surface Map Data within Your Application ... without displaying the
> corresponding Apple map (e.g., if You surface an address result through the
> Apple Maps Service, You must display the corresponding map with the address
> result).

Scenic surfaces Apple address results in the autocomplete dropdown
(`SearchCompleter`) and Apple reverse-geocoded labels via `PlaceNaming`. The map
is present behind the sheet in both cases, and `NavView` shows an Apple `Map`
too (`NavView.swift:38`), so this is **substantially satisfied**.

The soft spot is the `.large` detent, where the sheet covers ~92% of the screen
while the suggestion list — full of Apple address results — is on show. Fixing
item 2 with a live-sheet-height inset would resolve this at the same time. Note
also that the *street names spoken and shown during navigation come from OSM*,
not Apple, so nav is not surfacing Map Data at all.

### 2g. §2.6 — monetisation constraint, for later

> 2.6 You may not charge any fees to end-users **solely for access to or use of
> the Apple Maps Service** ... and You agree not to sell access to the Apple Maps
> Service in any other way.

A paid app or subscription is fine — the fee buys Scenic's routing and scoring,
which is Scenic's own work. What is prohibited is charging for map access as
such. No action now; do not build a pricing page that says "includes maps".

## 3. Open geodata — status after 41cbae7, plus one addition

`OpenStreetMap` (ODbL 1.0), `ESA WorldCover v200` (CC BY 4.0), and the four
`Terrain Tiles` upstreams (USGS, NOAA, and CDEM under the **Open Government
Licence – Canada**) are credited in `ios/Sources/AboutView.swift` in each
licensor's own wording, test-asserted, and reachable in one tap. See
`licensing-and-attribution-brief.md` for the derivation and for the ODbL
Derivative-Database constraint on any future offline-download feature.

**One thing to add (item 7).** `download.geofabrik.de` states its own provenance
line: *"Data processed by Geofabrik GmbH and created by OpenStreetMap
Contributors"*, under ODbL 1.0. Geofabrik's extract is arguably itself a
Derivative Database, which would make Geofabrik a database author owed
attribution under ODbL §4.3. Cheap insurance and simply accurate: add
"Extracts by Geofabrik GmbH" to the OpenStreetMap entry's credit lines. Geofabrik
imposes no terms of its own beyond ODbL and publishes no rate limit, but the
extracts are a free service — don't hammer it from CI.

## 4. Privacy and the App Store submission gates

Not copyright, but these are the things that actually block a release, and one is
a legal obligation in its own right.

- **A privacy policy URL is mandatory** in App Store Connect for every app, with
  no exception for free or single-user apps. Scenic has none, and nothing in the
  repo drafts one. **This is a hard gate (item 4)**, and it has to be a real
  hosted URL.
- **Precise location is treated as sensitive** under both GDPR (EU) and CCPA/CPRA
  (California, where it is expressly "sensitive personal information"). Scenic
  collects continuous precise location *and writes it to disk* — a drive trace is
  a detailed record of where someone drove and when. The saving grace is the
  architecture: traces stay on the device, and `server/` stores nothing. **That
  is a genuinely strong privacy position and it is worth writing down as a
  deliberate design property rather than an accident**, because it is most of what
  a privacy policy would need to say.
- **`PrivacyInfo.xcprivacy` is still missing (item 6)** — required now that
  `VoiceCatalogue.swift` persists to `UserDefaults`
  (`NSPrivacyAccessedAPICategoryUserDefaults`, reason code `CA92.1`). Already
  recorded in `licensing-and-attribution-brief.md`; unchanged.
- **Privacy Nutrition Label**: must declare Location. Because it is not linked to
  identity and not used for tracking, the honest answer is the mild one — but it
  must be answered.
- **Export compliance**: HTTPS only, so the standard exemption applies; it still
  has to be declared at submission.

## 5. The app icon (item 8)

`ios/Sources/Assets.xcassets/AppIcon.appiconset/icon-1024.png`, added in 8e76c80
as a "generated scenic-road mark". Checked for embedded provenance metadata
(Adobe/Getty/Shutterstock/Icons8/Flaticon/Noun Project strings): **none**, so
there is no evidence of an unlicensed third-party asset. **No infringement
concern.**

The concern runs the other way: the US Copyright Office's position is that
material generated by AI without sufficient human authorship is **not
copyrightable**. A generated icon may therefore be something nobody owns —
fine for a private app, weak for a brand you intend to defend. If the app gets a
real identity, have the mark drawn (or substantially reworked by hand) so there
is human authorship to own.

**Also, for whoever designs the next one:** SF Symbols are licensed under the
Xcode and Apple SDKs agreement, which states you *"may not use SF Symbols — or
glyphs that are substantially or confusingly similar — in your app icons, logos,
or any other trademark-related use."* The app's in-app use of `systemImage:` is
exactly what they are for and is fine. **Do not build the icon or wordmark out of
one** — `location.north.line.fill`, `slider.horizontal.3` and friends are off
limits for that purpose.

## 6. The name — see `branding-brainstorm.md`

Summarised here because it outranks everything above: **"Scenic" is both legally
weak and already occupied by a senior, established, direct competitor.** The
README already calls it a working title. Details, evidence and alternatives are
in `branding-brainstorm.md`.

---

## What to do, in order

1. **Stop using "Scenic" in anything public-facing** until the name is settled.
   Costs nothing today; costs a rename of bundle ID, domain, App Store listing
   and any built audience later. → `branding-brainstorm.md`
2. **Write the EULA notice** (§3.3.15). One paragraph, verbatim string, into App
   Store Connect and the "Data sources" sheet. Cheapest item, clearest text, and
   defensible on safety grounds alone.
3. **Draft the privacy policy** and host it. Most of its content is already true
   and good: on-device traces, no server-side storage, no tracking, no ads.
4. **Fix the Apple attribution** (§2.1) via `MKMapView` + `layoutMargins`, and
   decide the `.large` behaviour while doing it.
5. **Record snapped coordinates, not geocoder output**, in `DriveTrace` (§2.5).
   Improves the instrument regardless.
6. Add `PrivacyInfo.xcprivacy`; add the Geofabrik credit line.
7. Have the icon drawn by a human if the brand is going to matter.

**Two standing rules** worth pinning somewhere that gets read:

- **Never compare Scenic's routes or ETAs against Apple's** to evaluate or improve
  Scenic (§2.3). Compare against recorded drives and a clock.
- **Never let Apple-derived coordinates into `data/processed` or any pooled
  dataset** (§2.2).
