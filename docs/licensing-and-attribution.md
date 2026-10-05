# Licensing and data attribution: what the app owes, and to whom

**Status:** shipped — merged to `main` by `a2ddddc`. This is the part of the dispatch brief that outlived the work: its measurements, decisions and results. The brief itself, with its traps and done-list, was deleted on merge — `git show a2ddddc:docs/licensing-and-attribution-brief.md` prints it. Section numbers and "below" refer to that brief's layout.

## The three sources, and what each actually requires

### 1. OpenStreetMap — ODbL 1.0

**Where it enters:** the Geofabrik extract (`README.md:104`), consumed by
`pipeline/extract.py` and `pipeline/graph.py`. Every road, every street name,
every turn restriction.

**Where it reaches the user:** the app draws OSM-derived polylines onto the map
— `ios/Sources/ContentView.swift:45`, `:49`, `:62` — and names OSM streets in
its maneuvers and (since the voice merge) speaks them aloud.

**What that makes it:** a **Produced Work** under ODbL §4.3. Attribution is
required. Share-alike is **not** triggered.

**Required, per the OSMF's attribution guidance:** the credit
`© OpenStreetMap contributors`, and a statement that the data is available under
the Open Database License. Confirm the current exact wording and the required
link at <https://www.openstreetmap.org/copyright> and the OSMF attribution
guideline before writing it — reproduce what those say, do not paraphrase this
brief.

**The separate obligation, which is not triggered today but constrains the
future.** `data/processed/{scored_chunks,graph_edges,graph_nodes,turn_restrictions}.parquet`
are a **Derivative Database**, and distributing *those files* does trigger
share-alike (ODbL §4.4). Today they move only from the author's Mac to the
author's own serving box, which is not distribution. **Any future "download this
region for offline use" feature changes that**, and would oblige offering the
derived database under ODbL. Record this; do not act on it.

### 2. ESA WorldCover v200 (2021) — CC-BY 4.0

**Where it enters:** `pipeline/landcover.py:52` —
`esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/`.

**How much it matters:** it is half of `c_forest` at `pipeline/score.py:324`
(`chunks["c_forest"] = 0.5 * green + 0.5 * tree`), and forest carries weight
0.18 of 1.14. It is in every score the app displays. Not incidental.

**Required:** CC-BY 4.0 attribution. ESA's own prescribed credit is of the form
`© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data
(2021) processed by ESA WorldCover consortium`. **Verify the exact string
against ESA's current terms** — the consortium has published slightly different
wording per version, and v200/2021 is the one this repo fetches.

### 3. AWS Terrain Tiles (Terrarium) — an aggregate, not a dataset

**Where it enters:** `pipeline/elevation.py:35` —
`elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png`. Feeds
`c_relief`.

**The trap, and the reason this item is listed third but is the one most likely
to be got wrong:** this endpoint is the AWS Open Data terrain tile set (the
former Mapzen service). It is **not one dataset under one licence** — it is a
mosaic of many national elevation products, each with its own attribution, and
the required credit depends on which sources cover your footprint. Over New
England the contributing sources are believed to be USGS 3DEP/NED and SRTM, both
US-government public domain, which would make the burden light.

**Do not ship that belief.** Read the current source-and-attribution list on the
AWS Open Data registry entry for Terrain Tiles and reproduce the lines that
apply, or — if the list cannot be resolved to a confident answer — say so and
credit the aggregate by name. An honest "attributed the aggregate because the
per-source list could not be pinned down" is a fine outcome; an invented
public-domain claim is not.

### 4. Apple MapKit — already handled, but possibly obscured

The basemap is Apple's (`Map(position:)`, `ios/Sources/ContentView.swift:40`).
MapKit renders Apple's own attribution and legal link itself, bottom-left, and
Apple's guidelines require it not be covered.

**This is a real, checkable defect and not a theoretical one.** The app presents
a permanently-open bottom sheet — `ContentView.swift:103`,
`.sheet(isPresented: .constant(true))` with `.interactiveDismissDisabled()` —
across detents `[.planningCompact, .medium, .large]`. A sheet occupying the
bottom of the screen is exactly where MapKit puts that attribution. **Check it
at all three detents.** If it is covered, that is an App Review rejection item
as well as a licence one.

---

## Where it goes in the app

**There is no settings screen, no about screen, and no tab bar.** The entire UI
is a map plus one persistent sheet (`RoutePanel`, presented at
`ContentView.swift:103`) holding a mode picker, two address fields, the
preference slider, and a button that opens the "Tune scenery" sub-sheet
(`RoutePanel.swift:165`).

**The design that matches the existing idiom:** an unobtrusive row at the bottom
of `RoutePanel`'s `ScrollView` — "Data sources" or "About" — presenting a sheet
exactly the way "Tune scenery" already does. New file, e.g.
`ios/Sources/AboutView.swift`; wire it from `RoutePanel.swift`.

Files you will touch: `ios/Sources/RoutePanel.swift`, a new
`ios/Sources/AboutView.swift`, possibly `ios/Sources/ContentView.swift` for the
MapKit-attribution fix. Nothing else is in flight in `ios/` — all outstanding
branches were merged on 2026-08-31 — so there is nothing to collide with.

---

## Outcome, 2026-08-31 — implemented, with four corrections to the above

Shipped: `ios/Sources/AboutView.swift` (the credit strings and the "Data
sources" sheet), a credit line pinned in `RoutePanel` at every sheet height,
`ios/Tests/AttributionTests.swift` (12 cases), and the
[Data sources and licences](data-sources.md) page.

### The ODbL Derivative-Database constraint (brief item 5)

**Recorded, not acted on, exactly as instructed.** The routes the app draws are
a Produced Work under ODbL §4.3 — attribution only, no share-alike, and adding
the credit screen discharges it.

`data/processed/{scored_chunks,graph_edges,graph_nodes,turn_restrictions}.parquet`
are a **Derivative Database** under §4.4. They are built from the Geofabrik
extract by `pipeline/extract.py` and `pipeline/graph.py`, and they carry OSM's
substance — geometry, names, turn restrictions — not merely a rendering of it.
Today they move only from the author's Mac to the author's own serving box,
which is not distribution, so nothing is triggered.

**What would trigger it:** any feature that puts those files, or anything
derived from them with comparable substance, onto a user's device — the
"download this region for offline use" idea most obviously, but equally a
seeded on-device cache, a bundled starter region, or a P2P/side-load
distribution. At that point the recipient must be offered the derived database
under ODbL, with the licence text or a link to it, per the guideline's
*Databases* section ("in a location ... where users would be likely to look for
it, such as a readme file, or within the data or metadata").

The cheap design-time move, if offline download is ever built: ship the region
file with an adjacent `LICENSE`/`README` naming ODbL 1.0 and crediting
OpenStreetMap, and treat that pair as inseparable from the download. Retrofitting
it after the fact means re-issuing every file already shipped.

### Correction 1 — "one tap from the main view" is not sufficient on its own

The brief's Trap 3 says the accepted small-screen pattern is one tap from the
main view. The OSMF guideline is stricter than that. Its base requirement:

> Attribution must be presented to anyone who uses, views, accesses, interacts
> with, or is otherwise exposed to the map or produced work. The attribution
> format should not require individuals to interact with the map or produced
> work to see the attribution.

The one-tap case the brief is thinking of is the guideline's *collapsed*
attribution — an `(i)` button or an "About" menu is what a credit that **was
already shown** may shrink to. It is not a safe harbour for never showing one.

So the credit line is pinned **outside** `RoutePanel`'s `ScrollView`, not as a
row at the bottom of it as the brief specified. Inside the scroll view it sits
below the fold at the compact detent — the height every cold launch opens at —
so seeing it would require a scroll, i.e. an interaction. `PlanningCompactDetent`
gained `attributionTextPoints`/`attributionFixedPoints` to reserve its height,
for the same reason the custom detent exists at all.

### Correction 2 — the Terrarium source list *was* resolvable

The brief allowed "credited the aggregate because the per-source list could not
be pinned down" as an acceptable outcome. It did not come to that. The AWS
registry entry names
<https://github.com/tilezen/joerd/blob/master/docs/attribution.md> as the
dataset's licence, and that document carries a verbatim "Required attribution"
block, one line per upstream. `joerd`'s per-zoom source table then says which
upstreams apply at **zoom 11**, the zoom `pipeline/elevation.py` fetches.

Three lines apply to this app's footprint, and all three are reproduced verbatim
in `AboutView.swift`:

- `United States 3DEP (formerly NED) and global GMTED2010 and SRTM terrain data courtesy of the U.S. Geological Survey.`
- `Global ETOPO1 terrain data U.S. National Oceanic and Atmospheric Administration` — ocean at every zoom, and `BBOX` covers the Gulf of Maine.
- `Canada terrain data contains information licensed under the Open Government Licence – Canada;`

**The brief's guess was too narrow.** It expected "USGS 3DEP/NED and SRTM, both
US-government public domain, which would make the burden light". Two of the
three are not that: ETOPO1 is NOAA, and `BBOX`'s northern edge of 47.47 reaches
into Quebec and New Brunswick, where zoom 11 is sourced from NRCAN's CDEM under
the **Open Government Licence – Canada** — a real attribution licence, not
public domain. `AttributionTests` has a case asserting no entry ever claims
public domain, so the shortcut cannot come back.

*Not* reproduced, because they are outside the footprint: ArcticDEM and GMTED
(above 60° only at this zoom), and the Australian, Austrian, European, Mexican,
New Zealand, Norwegian and UK lines. **Widening `BBOX` can pull in another
upstream with another licence** — re-read that per-zoom table when it changes.

### Correction 3 — the two "known-failing" backend tests do not fail on `main`

The brief says to expect `2 failed, 345 passed, 1 skipped` and not to chase
them. On `main` (8ab5110) that is not the state:

    SCENIC_DATA=<abs>/data/processed pytest tests/   →   317 passed

`test_loops.py::TestLoopsAreLoops::test_the_penalty_is_what_removes_the_retrace`
exists and **passes**.
`test_routing.py::TestSurfaceAvoidanceIsNotAScenerySetting::test_surface_is_absent_from_the_reported_score`
**does not exist at all**. The `claude/unpaved-and-urban-verdict` merge the brief
attributes them to (dc7380a) is not an ancestor of `main` — it went into
`claude/project-context-next-steps-88cd34`. The brief was written in a tree that
had that work; `main` does not.

So the bar was tighter than stated, and is met: **317 passed, 0 failed, 0
skipped**, unchanged, and this branch touches no Python.

### Correction 4 — MapKit's attribution is covered, and the one-line fix does not work

**It is covered, at every detent** (brief item 2). Apple's attribution — the
Apple logo followed by the word "Maps" — sits at the map's bottom-left and the
planning sheet clips it: the logo and the first two letters are legible, the
rest is behind the sheet's rounded bottom-left corner.

The brief expected this to vary across `[.planningCompact, .medium, .large]`. It
does not, and the reason is worth writing down: a sheet's **bottom edge is
pinned to the bottom of the screen at every detent** — the detent moves only its
*top* edge. MapKit pins its ornament to the bottom-left of the map. The two never
stop overlapping, so the occlusion is detent-independent. Verified by screenshot
at the compact detent, at `.medium` (route loaded via `SCENIC_DEMO`), and at the
0.85-of-screen height the compact detent takes at the AX5 text size.

**The obvious fix was tried and measured not to work.**
`.safeAreaPadding(.bottom, 380)` on the `Map`, after its `.ignoresSafeArea()`,
does not move the ornament at all — the corner crop is pixel-identical. Worse, it
leaked into the presented sheet's safe area and pushed `RoutePanel`'s own pinned
footer off the bottom at `.medium`. Reverted; `ContentView.swift` is untouched.

This is **not fixed** and is left as separate work, because the honest fix is a
design change rather than a modifier: the map's ornaments have to be inset by
the *live* sheet height, which means plumbing the current detent's point height
into the map, and deciding what should happen at `.large`, where the sheet
covers ~92% of the screen and there is no honest place to put an attribution
that belongs to a map nobody can see. (Apple Maps itself lets its attribution go
with the map at full sheet height.) That is a product call, not a cleanup.

Note it is **Apple's** basemap attribution, not the data attribution this brief
commissioned — that is delivered and verified. Apple is additionally credited by
name on the "Data sources" screen.
