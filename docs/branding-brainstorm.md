# Branding: what this app is actually called

**Written 2026-09-01, expanded the same day** after actually checking candidate
names against the App Store instead of just liking the sound of them. That check
changed the recommendation, which is the main reason this document is worth
re-reading if you saw the first version.

Companion to `legal-and-ip-audit.md`, where the name is risk item #1.

**Not legal advice.** Nothing here substitutes for a professional trademark
clearance search before money goes into a brand. The facts below are checkable
and I checked them; the conclusions about registrability are doctrine, not
counsel.

---

## 1. Why "Scenic" cannot stay

Two independent problems, either sufficient on its own.

### It is taken, by a senior direct competitor

| What | Where | Why it matters |
| --- | --- | --- |
| **Scenic — Motorcycle Navigation** | `scenic.app`, App Store | ~30M hours ridden, 200k+ user routes, 4.7★, paid Premium tier. A scenic-route *navigation app*. Same word, same goods, years of priority. |
| **Scenic Way** | `scenicway.co.uk` | "Scenic route planner for iPhone & CarPlay" — waypoints, turn-by-turn. |
| **Scenic Map** | App Store | iOS navigation app, GPX routes. |
| **Scenic Landscapes** | App Store | Photo/video app. |
| **Scenic Group / Scenic Luxury Cruises** | `scenic.com` | Large travel brand, marks in travel classes. |
| **Scenic** (Elixir UI framework) | `hex.pm` | Not legal — pure search-result noise. |

Row one is decisive. Identical mark, identical goods is the worst pairing in a
likelihood-of-confusion analysis, and they have priority.

### It is descriptive, so it would be weak even unopposed

Distinctiveness runs **generic → descriptive → suggestive → arbitrary →
fanciful**. A mark is "merely descriptive" and refusable under Lanham §2(e)(1) if
it *immediately conveys* a feature, quality, function or purpose of the goods.
"Scenic", for an app that finds scenic routes, names the feature outright.

1. Likely **refused on the Principal Register** absent acquired distinctiveness
   (years of use and money to prove). Supplemental Register at best.
2. **Weak even if registered** — competitors need the word to describe their own
   products, so you cannot stop them using it.
3. **Bad App Store discovery** — the established competitor and a photo app rank
   above you for your own name.

### Renaming is nearly free right now

No users, no listing, no audience, and the bundle ID is still `app.scenic.demo`
— which becomes **permanent after first submission**.

The code footprint is much smaller than a grep implies; almost every hit is the
gitignored `Scenic.xcodeproj` build output or prose. What actually changes:

- `PRODUCT_BUNDLE_IDENTIFIER`, target and scheme names, `CFBundleDisplayName`
- `Color.scenic` (13 uses)
- the `SCENIC_*` env prefix (~40 uses: `API`, `DATA`, `DEMO`, `HOST`, `PBF`,
  `TRACES`, `REGION`)

**What does not change, and this is the point:** the ~47 uses of "scenic score",
"scenic route", "scenic km", "the scenic arm". Those are accurate English for a
real quantity and they stay. The word is a fine *adjective* for the feature and a
bad *proper noun* for the product — so giving it up as a brand costs nothing in
the domain vocabulary, precisely *because* it is descriptive.

## 2. The positioning the name has to serve

Getting this straight first, because naming the category instead of the product
is the underlying mistake in "Scenic".

**The competitive field sells curvy roads to motorcyclists, from
community-submitted routes** — Scenic Motorcycle, calimoto, Kurviger, Rever.
Roadtrippers sells POI-stitched itineraries. Two things here are on nobody's
list:

**(a) Every road is measured, not submitted.** A beauty vector for every segment
in the region — water, coastline, forest and parks, curvature, terrain relief,
farmland, viewpoints, scenic tags, urban penalty — computed from open geodata.
Nobody had to drive it and upload it first. That supports a claim no competitor
can make: **"we scored every road in New England."**

**(b) The dial, and the loop.** You don't pick from a list of routes; you move
one slider and *spend minutes to buy beauty*, watching the trade as it happens
(89 min / 0 mi beautiful → 193 min / 25 mi beautiful). And the loop mode answers
a question no navigation app answers: **"I have ninety minutes and nowhere to be
— where should I drive?"**

**The strategic thesis, and it is a good one:** every navigation app ever built
optimises for *less* — less time, less distance, less traffic. This is the only
one that asks you to spend more. That is a genuinely contrarian position and a
culturally live one. **The brand should be proudly anti-efficiency.** Not
"optimise your leisure" — the opposite of optimisation.

Which means the voice is: unhurried, dry, quietly confident. Never breathless,
never "supercharge", never exclamation marks. It should feel like a well-made
analogue object — a good map, a mechanical watch.

Two brand architectures fit, and the best name serves both:

- **Instrument** — "we scored every road." Precise, technical, for map nerds.
- **Invitation** — "go get lost on purpose." Warm, for Sunday drivers.

## 3. Names, checked

I queried the US App Store search API for every candidate and counted apps whose
*name* contains the word, flagging those in Navigation or Travel. This is the
check that separates a wordlist from a shortlist, and it demoted my own first
recommendation.

| Candidate | Apps with the name | In Nav/Travel | Verdict |
| --- | --- | --- | --- |
| **Longcut** | **0** | **0** | **Clean** |
| **Aimless** | **0** | **0** | **Clean** |
| **Detourist** | **0** | **0** | **Clean** (coined) |
| Dawdle | 1 | 0 | Usable |
| Vireo | 2 | 0 | Usable |
| Camber | 5 | 0 | Usable |
| Overlook | 7 | 0 | Usable |
| ~~Amble~~ | 6+ | **yes** — *Amble: Walk Route Planner*, *Amble App* (Travel) | **Avoid** |
| ~~Mosey~~ | 6+ | **yes** — *Mosey – Commute Alerts* (Navigation) | **Avoid** |
| ~~Switchback~~ | 6+ | **yes** — *Switchback Moto* (Navigation) | **Avoid** |
| ~~Saunter~~ | 4 | **yes** — *Saunter Map* | **Avoid** |
| ~~Meander~~ | 9 | **yes** — *MeanderEV* | **Avoid** |
| ~~Byroad~~ | 1 | **yes** — *ByRoad* (Travel) | Avoid |
| ~~Wynd~~ | 4 | yes — *Wyndham* | Avoid (big mark) |

**Correction to the first version of this document: it recommended Amble.** That
was wrong, and only checking revealed it — there is already an *Amble: Walk Route
Planner* on the App Store. Same idea, adjacent category. Switchback, which was
the runner-up, collides with *Switchback Moto* in Navigation, which is worse
still given the motorcycle field is exactly what we want distance from.

### Domains

Every single-word `.app` I checked is registered — `amble`, `switchback`,
`meander`, `wend`, `overlook`, `byway`, `hairpin`, `longway`, `camber`, `saunter`,
`dawdle`, `mosey`. That is normal for dictionary words and **not** a reason to
reject a name; an exact-match single word is a nice-to-have.

For Longcut: `longcut.com` is registered; `longcut.co` and
`takethelongcut.com` appear free; `longcut.app` returned no A record with
inconclusive whois — **possibly free, must be confirmed at a registrar** (my
RDAP query failed to connect, so treat this as unverified).

### Recommendation: **Longcut**

*Tagline: "Take the long way."*

- **It is the product, in one word.** The opposite of a shortcut is a route you
  chose to make longer on purpose. Nobody needs it explained.
- **Legally much stronger than Scenic.** It does not describe a feature of a
  navigation app; it takes a mental step to connect (which is the actual
  suggestive-vs-descriptive test). Not a term of art in this field.
- **Zero App Store collisions** — the cleanest result of anything tested.
- **It serves both architectures.** Wry enough for the invitation, concrete
  enough for the instrument.
- **The voice falls out of it.** "Longcut found you 25 good miles for 38
  minutes." That sentence writes itself and no competitor can write it.

**Honest risks, to test on real people before committing:**

- **"Skoal Long Cut"** is chewing tobacco, and for some Americans "long cut" cues
  that first. Different trademark class (34 vs 9), so conflict risk is low, but
  the *association* is a real branding question. Ask five people what "longcut"
  makes them think of before you buy anything.
- Slight risk of being heard as two words, or as a hair/sewing term.
- It is a compound of common words, so it is suggestive rather than fanciful —
  strong, but not the strongest possible class.

**The bold alternative: Aimless.** Also zero collisions, and it captures the loop
mode perfectly — "ninety minutes, nowhere to be". A navigation app called Aimless
is a confident joke, and confident jokes make memorable indie brands. The risk is
real though: "aimless" carries a negative valence (pointless, lost), and some
users will read it as the app not knowing where it is going. High reward, higher
variance.

**The understated alternative: Camber** — the curve of a road surface. Zero
Nav/Travel collisions, designerly, quiet. Needs the tagline to carry all the
meaning, because most people do not know the word.

### Avoid regardless of availability

- Anything with **Scenic, Route, Drive, Map, Road** as the whole mark — same
  descriptiveness trap, and "Scenic *anything*" walks into the senior competitor.
- **Verge** — "The Verge" is a major media mark with class 9/41 coverage.
- **Backroads** — `backroads.com` is a large established tour operator.
- **Detour** — conceptually ideal, heavily used, including a well-known
  location-audio app.
- **The Long Way / Long Way Round** — best *phrase* in the space, but Ewan
  McGregor's is a strong travel/media brand. **Use it as the tagline, not the
  name.** `thelongwayapp.com` is free if you want it defensively.
- **Apex, Chicane, Hairpin, Esses** — motorsport register. Pulls toward fast and
  track, the opposite of the product's soul.

## 4. Naming things *inside* the product

Cheaper than a rebrand and most of the felt personality. Currently the UI says
"scenery strength 0.25" and "25 mi beautiful", which is instrumentation talking.

- **The loop mode deserves a name.** It is the most distinctive thing here and it
  is currently called "Loop". Call it **Nowhere**. The UI string becomes
  *"Nowhere · 90 minutes"*, and the empty state becomes *"Nowhere in particular.
  Ninety minutes. We'll bring you home."* That is a feature people tell friends
  about.
- **"Good miles" instead of "mi beautiful".** `25 good miles` is warmer, shorter,
  and does not overclaim — which matters, because the scoring has never been
  validated against a human (the README says so).
- **State the trade, not the setting.** Replace `scenery strength 0.25` with the
  thing the user is actually buying: **`+38 min · 25 good miles`**. The slider
  stops being a parameter and becomes a price tag. This is the single highest-
  value copy change in the app.
- **The dial** as the internal name for the fastest↔scenic slider — it is what
  everyone will call it anyway.

## 5. Copy

- **Tagline:** Take the long way.
- **App Store subtitle** (30 char limit): `Take the long way home.` — 23 chars.
- **One-liner:** Every road in New England, scored for beauty. Move one slider to
  trade minutes for the view.
- **The loop hook:** Ninety minutes, nowhere to be. We'll bring you home the
  pretty way.
- **Credibility line:** Built on open data — every road measured, not
  crowdsourced.
- **Opening line of the listing:** *Every other maps app is trying to save you
  time. This one helps you spend it.*

**What not to claim.** No "best route", no "fastest scenic route", nothing
implying validated ground truth. The README is honest that scoring has never been
checked against a human driving the roads. **"Measured" is defensible.
"Beautiful, guaranteed" is not** — and an overclaim here is also the kind of
thing that turns a bad review into a refund request.

## 6. Visual identity

**Keep the green.** `Color.scenic` = `rgb(0.22, 0.83, 0.62)` ≈ `#38D49E`. It
reads clearly against both the Apple basemap's greens and its water blue, and is
meaningfully distinct from Google Maps blue and Waze's palette. It is already the
route line, the Tune highlight and the scenery bars — the only brand equity the
project has. Rename the *symbol* with the app; keep the *value*.

**Icon.** Four directions were drawn and tested at 96px and 28px:

1. **Two ways** — a dashed straight line and a bold winding one joining the same
   two dots. **The strongest**: it is the entire product in one mark, it pairs
   exactly with the name Longcut, and it survives the thumbnail because the two
   strokes differ in weight *and* style. This is the one to develop.
2. **Switchback** — a single folded stroke. Boldest at small sizes and the most
   confident mark, but it says "twisty road" (the motorcycle register) rather
   than "the long way".
3. **Contour** — topo lines with a road threading across. Beautiful at full size,
   **muddies below 40px** — the contour lines merge. Better as a marketing motif,
   a loading state, or the "Tune scenery" header than as the icon.
4. **The dial** — an arc with a handle. Reads as a gauge or a speedometer, not a
   road. Clean, but says "settings" more than "driving".

**Two hard constraints for whoever draws the final mark:**

1. **No SF Symbols.** The Xcode and Apple SDKs licence: you *"may not use SF
   Symbols — or glyphs that are substantially or confusingly similar — in your
   app icons, logos, or any other trademark-related use."* In-app `systemImage:`
   is fine and expected. This rules out the obvious shortcut of putting
   `location.north.line.fill` on a green square.
2. **Have a human draw it.** The current `icon-1024.png` (commit 8e76c80) is a
   generated mark, and the US Copyright Office's position is that AI-generated
   material without sufficient human authorship is not copyrightable — so it may
   be something **nobody owns, including you**. Fine for a private build, weak
   for a brand you would defend.

## 7. Order of operations

1. **Test the name on people first.** Five strangers, one question: "what does
   Longcut sound like it does?" If they say "the long way round", you are done.
   If they say "chewing tobacco", pick Aimless or Camber.
2. **Professional clearance search** — classes 9 (downloadable software) and 42
   (SaaS), US and EU knock-out, plus App Store name search. Before spending.
3. Register the domain; reserve the App Store name (can be done ahead of
   submission).
4. `PRODUCT_BUNDLE_IDENTIFIER` — **permanent after first submission.** Drop
   `.demo` while you are there.
5. Target/scheme names, `CFBundleDisplayName`, `MARKETING_VERSION` off `0.1`.
6. `Color.scenic` → new name; `SCENIC_*` → new prefix (also `server/DEPLOY.md`,
   `README.md`, and the `SCENIC_API`/`SCENIC_DEMO` invocations in `docs/`).
7. **Do the in-product copy from §4 at the same time** — it is an afternoon and
   it is most of what the brand actually feels like.
8. Leave "scenic score / scenic route / scenic km" alone. Still the right words.
9. `docs/` prose can be updated lazily; it is internal.
