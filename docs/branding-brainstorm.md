# Branding: why "Scenic" has to go, and what the product is actually called

**Written 2026-09-01.** The README has always called Scenic a working title. This
says why that instinct was right, what the app is actually *for* in words a
stranger would understand, and what to call it. Companion to
`legal-and-ip-audit.md`, where the name is risk item #1.

**Not legal advice.** Nothing here substitutes for a professional trademark
clearance search before money goes into a brand. But the two facts that decide it
are checkable, and I checked them.

---

## 1. The name is the biggest single risk in the project

Two independent problems, either of which alone would be enough.

### It is already taken, by a senior direct competitor

| What | Where | Why it matters |
| --- | --- | --- |
| **Scenic — Motorcycle Navigation** | `scenic.app`, App Store | ~30M hours ridden, 200k+ user routes, 4.7★, paid Premium tier. A scenic-route *navigation app*. Same name, same category, years of priority. |
| **Scenic Way** | `scenicway.co.uk` | "Scenic route planner for iPhone & CarPlay" — turn-by-turn, waypoints. |
| **Scenic Map** | App Store | iOS navigation app, GPX routes. |
| **Scenic Landscapes** | App Store | Photo/video app. |
| **Scenic Group / Scenic Luxury Cruises** | scenic.com | Large travel brand with marks in travel classes. |
| **Scenic** (Elixir UI framework) | hex.pm | Not a legal conflict; pure search-result noise. |

The first row is the one that matters. It is not a distant sound-alike in another
industry — it is **the same word, for a scenic-route navigation app, already
established**. In a likelihood-of-confusion analysis the marks are identical and
the goods are identical, which is the worst possible pairing. They have priority.

### It is legally the weakest kind of name

Trademark distinctiveness runs: **generic → descriptive → suggestive → arbitrary
→ fanciful.** A mark is "merely descriptive" and refusable under Lanham Act
§2(e)(1) if it *immediately conveys* a quality, feature, function or purpose of
the goods. "Scenic" for an app whose entire function is finding scenic routes is
about as squarely descriptive as it gets — it names the feature.

Consequences, in order of how much they'd hurt:

1. Likely **refused on the Principal Register** absent acquired distinctiveness
   (which takes years of use and money to prove). Supplemental Register at best.
2. A descriptive mark is **weak even if registered** — you can't stop competitors
   from using the word, because they need it to describe their own product.
3. **App Store discoverability is bad**: searching "scenic" returns the
   established competitor and a photo app before it returns you.

### So: rename now, while it costs nothing

There are no users, no listing, no audience, and the bundle ID is still
`app.scenic.demo`. The cost of renaming today is a few hours. The cost after a
launch is a bundle ID that can never change, a domain, a listing, reviews, and
whatever audience exists.

**And the code cost is far lower than it looks.** Grepping suggests thousands of
hits, but almost all of them are either the gitignored `Scenic.xcodeproj` build
output or *prose*. What actually has to change:

- `PRODUCT_BUNDLE_IDENTIFIER` (`app.scenic.demo`) and the target/scheme names
- `Color.scenic` (13 uses)
- the `SCENIC_*` env var prefix (~40 uses: `SCENIC_API`, `SCENIC_DATA`,
  `SCENIC_DEMO`, `SCENIC_HOST`, `SCENIC_PBF`, `SCENIC_TRACES`, `SCENIC_REGION`)
- `CFBundleDisplayName`, the README title

**What does *not* change — and this is the point:** the ~47 uses of "scenic
score", "scenic route", "scenic km", "the scenic arm". Those are correct English
describing a real quantity, and they stay. The word is a fine *adjective* for the
feature; it is a bad *proper noun* for the product. Losing it as a brand costs
you nothing in the domain vocabulary, precisely because it is descriptive.

## 2. What the product actually is

Worth getting straight before naming it, because the current name describes the
category rather than the product, and that's the underlying mistake.

Everyone in this space sells **curvy roads to motorcyclists, from
community-submitted routes**: Scenic Motorcycle, calimoto, Kurviger, Rever.
Roadtrippers sells POI-stitched road trips. Two things here are genuinely not on
that list:

**(a) Every road is measured, not submitted.** There is a beauty vector for every
road segment in the region — water, coastline, forest and parks, curvature,
terrain relief, farmland, viewpoints, scenic tags, urban penalty — computed from
open geodata. Nobody had to have driven it and uploaded it. That is a real,
defensible, *statable* claim: **"we scored every road in New England."**

**(b) The dial, and the loop.** You don't pick a route from a list; you move one
slider and *spend minutes to buy beauty*, continuously, and watch the trade
happen (89 min / 0 mi beautiful → 193 min / 25 mi beautiful). And the loops mode
answers a question no navigation app answers: **"I have ninety minutes and
nowhere to be — where should I drive?"** No destination required.

That second one is probably the product. "Directions, but prettier" is a feature.
"Give me a beautiful hour and bring me home" is a reason to open an app on a
Sunday morning.

**The positioning line I'd build the brand on: *take the long way, on purpose.***

## 3. Names

Every single-word `.app` domain I checked is registered — `amble`, `switchback`,
`meander`, `wend`, `overlook`, `byway`, `hairpin`, `longway`, all gone. That is
normal for dictionary words and **not** a reason to reject a name: an exact-match
single-word domain is a nice-to-have, not a requirement. Compounds are available.

*(Domain notes below are from `dig`/`whois` on 2026-09-01 — indicative only,
confirm at a registrar. A registered domain may be parked and for sale.)*

### The candidates I'd actually put forward

| Name | Evokes | Class | Collision risk | Notes |
| --- | --- | --- | --- | --- |
| **Amble** | To travel at an unhurried pace | Suggestive | Low-ish in class 9 | Warm, short, says *unhurried* without saying *scenic*. My favourite. `driveamble.com` taken; `amblerouting.com` free. |
| **Switchback** | A hairpin climbing a hillside | Suggestive | Moderate — used by other software cos | Vivid and specific to great driving roads. Strong, adventurous. `switchbackdrive.com` free. |
| **Byroad** | A minor side road | Suggestive | Low — uncommon word | Quietly perfect meaning. `byroadapp.com` free. Careful: near "byway", which is the *US National Scenic Byways* program and leans descriptive. |
| **Meander** | What a river and a good road both do | Suggestive | Low-moderate | Doubles as the curvature signal. Slightly soft. |
| **Overlook** | The payoff at the top of the climb | Suggestive | Moderate | Nice noun; competes with "overlook" = to miss something. |
| **Wend** | To make one's way, unhurried | Arbitrary-ish | Low | Short, distinctive, uncrowded. Slightly archaic — may need the tagline to carry it. |

### Ones I'd avoid, and why

- **Anything containing "Scenic", "Route", "Drive", "Map", "Road"** as the whole
  mark — same descriptiveness trap, and "Scenic *anything*" walks straight into
  the senior competitor.
- **Verge** — "The Verge" is a major media trademark with class 9/41 coverage.
- **Backroads** — `backroads.com` is a large established travel-tour operator.
- **Detour** — conceptually ideal, but heavily used, including a well-known
  location-audio app.
- **The Long Way / Long Way Round** — the best *phrase* here, but Ewan McGregor's
  "Long Way Round" is a strong travel/media brand. **Use it as the tagline, not
  the name.** `thelongwayapp.com` is free if you want it defensively.
- **Apex, Chicane, Hairpin** — motorsport register. Pulls the brand toward
  fast/track driving, which is the opposite of the product's soul.

### My recommendation

**Amble**, with *"Take the long way."* as the tagline.

It says unhurried without saying scenic, it's short and pronounceable, it's
suggestive rather than descriptive (a consumer needs one mental step to get from
"amble" to "driving routes" — which is exactly the test that separates
registrable from refused), and it doesn't sit in the motorcycle/curvy-road
register that the competition owns. **Switchback** is the runner-up and the better
choice if the brand should feel more adventurous than gentle.

## 4. Copy to build the listing on

- **Tagline:** Take the long way.
- **App Store subtitle** (30 chars): `Take the long way home.` (23)
- **The one-liner:** Every road in New England, scored for beauty. Move one
  slider to trade minutes for the view.
- **The loop hook:** Ninety minutes, no destination. We'll bring you home the
  pretty way.
- **The credibility line:** Built on open data — every road measured, not
  crowdsourced.
- **What not to claim:** avoid "best route", "fastest scenic route", or anything
  implying verified ground truth. The README is honest that the scoring has never
  been validated against a human driving the roads; the marketing should not get
  ahead of that. "Measured" is defensible; "beautiful, guaranteed" is not.

## 5. Visual identity

**Keep the green.** `Color.scenic` is `rgb(0.22, 0.83, 0.62)` — a mint/emerald
that reads clearly against both the Apple basemap's greens and its water blue,
and is meaningfully distinct from Google Maps blue and Waze's palette. It is
already the route line, the Tune highlight and the scenery bars. That consistency
is the one piece of brand equity the project has. Rename the *symbol* with the
app, keep the *value*.

**Icon direction.** The soul of the product is the dial and the curve, so:

- a single switchback/hairpin curve, cresting — one confident stroke, mint on
  dark; or
- contour lines with one road threading across them (nods to `c_relief`, and
  reads at 60px); or
- the trade itself: a curve with a notch on it, like a slider on a road.

**Two hard constraints for whoever draws it:**

1. **No SF Symbols.** The Xcode and Apple SDKs licence states you *"may not use
   SF Symbols — or glyphs that are substantially or confusingly similar — in your
   app icons, logos, or any other trademark-related use."* In-app `systemImage:`
   use is fine and expected; the icon and wordmark must be original. That rules
   out the obvious shortcut of dropping `location.north.line.fill` on a green
   square.
2. **Have a human draw it.** The current icon (`icon-1024.png`, commit 8e76c80)
   is a generated mark. The US Copyright Office's position is that AI-generated
   material without sufficient human authorship isn't copyrightable — so the
   current icon may be something *nobody owns*, including you. Fine for a private
   build; weak for a brand you'd want to defend.

## 6. Rename checklist, when the name is picked

1. **Clear it first**: professional trademark search in classes 9 (downloadable
   software) and 42 (SaaS), plus a US and EU knock-out search, plus an App Store
   name search. Do this *before* buying anything.
2. Register the domain and the App Store name (App Store names can be reserved
   ahead of submission).
3. `PRODUCT_BUNDLE_IDENTIFIER` — **this one is permanent after first submission.**
   Get it right. Drop `.demo` while you're there.
4. Target/scheme names in `ios/project.yml`, `CFBundleDisplayName`,
   `MARKETING_VERSION` off `0.1`.
5. `Color.scenic` → new name; `SCENIC_*` env vars → new prefix (update
   `server/DEPLOY.md`, `README.md`, and the simulator invocations in
   `docs/` that pass `SCENIC_API`/`SCENIC_DEMO`).
6. Leave "scenic score / scenic route / scenic km" alone — still the right words.
7. `docs/` prose can be updated lazily; it is internal.
