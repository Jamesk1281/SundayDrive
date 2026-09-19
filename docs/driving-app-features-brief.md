# Seven driving-app features: what exists today, and what each would cost

> **Costed in `docs/driving-app-features-cost.md` (2026-09-19).** Neither
> document chooses what ships; both are inventory awaiting a decision.

**Status: surveyed 2026-09-19, nothing changed.** No source file, no constant
and no test was touched. Every claim below is a `file:line` read off
`main` at `378aaee`. This document is a **brief for a costing study**, not a
licence to build: the deliverable is a second document that prices seven
candidate features and recommends an order. **It must not choose what ships,
and it must not implement any of them.** The model for its shape and its
contract is `docs/scenery-cap-options.md` — "this document exists to be chosen
from; it does not choose".

## Why these seven, and why now

They came out of a feature brainstorm that split the project's options into
scoring ideas, search-primitive ideas, and app ideas. The scoring half is
already being worked elsewhere (`docs/scenery-grading-verdict.md` on
`claude/funny-elbakyan-93c75f` measures twenty scenery proposals). These seven
are the app half, and none of them has ever been costed.

The common thread is that the engine has gone a long way past the app. The API
serves 236,000 km over six states with turn-by-turn guidance, voice, loops and
drive recording — and the app cannot export a route, cannot show you where the
good parts of one are, throws every drive away when you close it, and opens on
Massachusetts.

---

## 1. GPX export

**What exists.** Nothing. `grep -rn "gpx\|GPX\|ShareLink\|UIActivity" ios/ server/ pipeline/`
returns a single unrelated comment in `pipeline/router.py:738`.

The data is already there and already in the right shape. `Route.geojson`
(`pipeline/router.py:2047-2064`) returns the route as a GeoJSON `Feature` whose
geometry is the full LineString, with `steps()` (`pipeline/router.py:1782`)
alongside it as structured maneuvers. A GPX `<trk>` is that LineString with
different tag names.

**What to cost.** Server-side (`/api/route.gpx`, or a `format=gpx` parameter)
against client-side generation plus a `ShareLink`. Which arm gets exported when
the response carries two. Whether maneuvers become `<wpt>` elements or are
dropped.

**Traps.**
- The route response is *two* routes, fastest and scenic. A GPX file is one
  track. Exporting "the route" without saying which is a silent wrong answer.
- Do not put the export button in `ios/Sources/RoutePanel.swift` without
  reading the collision note at the end of this brief.

---

## 2. A strip showing where the good parts are

**What exists.** Aggregates only. `Route.geojson`'s properties are `km`,
`minutes`, `mean_score`, `beautiful_km`, `beautiful_score`, `scenery_km` and
`steps` (`pipeline/router.py:2051-2063`). `scenery_km` is a *total* per beauty
type. Nothing in the payload says **where** along the route the score is high,
so the app cannot draw a profile and the driver cannot see whether their
"31 beautiful miles" are one long stretch or forty scattered fragments.

The server already has the per-edge numbers: `_edge_scores`
(`pipeline/router.py:982`) computes the 0–10 score per undirected edge and
`_collect` walks the chosen path's edges to build those aggregates. A
per-segment series is a new field on an existing walk, not a new computation.

**What to cost.** The wire format (a coarse fixed-bucket series against a
per-edge array — an 80 km scenic route can carry several hundred edges, and the
payload already carries full geometry), and the iOS rendering. Also whether the
same series answers elevation, since the app displays no terrain profile either
and `c_relief` is already on the edge.

**Traps.**
- How the scenery breakdown should be presented is listed in
  `docs/consumer-polish-brief.md` as one of seven **product decisions
  deliberately held out of scope** and decided separately. Cost the mechanism;
  do not redesign the breakdown UI.
- Do not compute a second score client-side. `_edge_scores` exists precisely to
  stop two instruments disagreeing (`pipeline/router.py:976`).

---

## 3. Saved routes and history

**What exists.** No route persistence of any kind. `UserDefaults` is used for
exactly three things, all voice: the selected voice and its duration cache
(`ios/Sources/VoiceCatalogue.swift:118-119,148-149`) and the mute flag
(`ios/Sources/VoiceGuide.swift:351-352`). There is no favourites list, no
recents, no "drive it again".

**But half of it is already on disk.** Every drive writes an NDJSON trace to
`Documents/traces` (`ios/Sources/DriveTrace.swift:107,131-133`), exposed to
Files.app by `UIFileSharingEnabled` (`ios/project.yml:46-47`). The app records
a complete history and shows the driver none of it.

**What to cost.** A saved-route store (what identifies a route: endpoints plus
`pref` plus weights plus `avoid_unpaved`, or the returned geometry), against
simply surfacing the traces that already exist as a drive history. These are
different features with different costs and the study should not merge them.

**Traps.**
- Re-running a saved request does not reproduce a saved route. The graph is
  rebuilt periodically and the constants are re-fitted deliberately
  (`SPEED_FACTOR` and `CONTROL_SECONDS` are "constants and a restart" by
  design). Storing the parameters and storing the polyline answer different
  promises.
- The drive-trace privacy story is another of the held-out product decisions in
  `docs/consumer-polish-brief.md`. Surfacing traces in-app touches it. Cost it,
  flag it, do not decide it.

---

## 4. Offline fallback

**What exists — and this is the item most likely to be misread.** Navigation
does *not* collapse when the network drops. `ServiceError.offline` is a
distinct, well-worded case (`ios/Sources/RouteService.swift:55,65,207`), and
`NavigationModel`'s reroute cooldown was written for exactly this: the comment
at `ios/Sources/NavigationModel.swift:260-264` says the cooldown exists so that
"a failed reroute (server briefly down…)" does not fire on every 1 Hz fix. The
route already in memory keeps guiding, and voice keeps speaking.

So the gaps are narrower and more specific than "the app needs offline mode":

1. the driver is never told they are now navigating without a safety net —
   a declined reroute and an unreachable server look the same from the seat;
2. a cold start with no network has no route at all, and no cached last route
   to open;
3. MapKit tiles are Apple's and go blank regardless of anything this project does.

**Traps.**
- **Offline *routing* is not on the table and the study must say so in one
  line.** The graph is 998k edges served from a remote process; shipping a
  routable subset to the phone is a different project by an order of magnitude.
  The feature is offline *continuation*, not offline routing. A session that
  misses this will cost a week.
- Do not "fix" the reroute behaviour on the way past. The cooldown, the
  movement guard and the `awaitingJoin` latch
  (`ios/Sources/NavigationModel.swift:280-310,402-417`) are each the
  measured answer to a specific defect from the 2026-08-22 drives, where one
  drive rerouted ten times in 160 seconds.

---

## 5. Lane guidance

**What exists.** Nothing, anywhere in the stack.
`grep -rn "turn:lanes\|lanes" pipeline/*.py ios/Sources/*.swift` returns **zero
matches** — the tag is not extracted, not carried onto edges, and not in
`steps()`. The README already lists this as an open item: at a multi-lane exit
the wrong lane is a missed exit however good the maneuver is.

**What to cost — and the first step is a measurement, not a design.**

**Trap, and it is the expensive one.** This project has twice been burned by
assuming an OSM tag is evenly mapped. Road `surface` runs from Vermont's 90%
down to Maine's 36%, which is why the unpaved penalty was measuring mapping
diligence rather than road quality (`docs/unpaved-and-urban-verdict.md`), and
green polygons are 3.3× thinner in Maine than Rhode Island
(`docs/geodata-sources-findings.md` §1). `turn:lanes` is a *more* laborious tag
than either. **So the study's first act is a per-state coverage census of
`turn:lanes` over the six-state extract**, and if it lands where `surface` did,
the honest finding is that lane guidance is a feature that works in some states
and silently does not in others — which is a product decision, not an
engineering one. Report the number before costing the build.

---

## 6. CarPlay

**What exists.** Nothing. `ios/project.yml` declares `UIBackgroundModes:
location, audio` (`:43-45`) and no entitlements beyond that; deployment target
is iOS 17 (`:4-5`).

**Cost the gate, not the implementation.** CarPlay navigation requires an
Apple-granted entitlement that is requested and approved rather than simply
enabled, and it lands the app in a category with its own review expectations.
Against that:

- the app has no privacy manifest and no LICENSE
  (`docs/legal-and-ip-audit.md` on `claude/data-attribution` is the live record);
- the name is unresolved and has to change — "Scenic" is taken by an
  established scenic-route nav app;
- MapKit's attribution obligations already have a known open defect (the Apple
  logo is clipped), and a second screen is a second place to get that wrong.

**So the study's job here is to establish the ordering, with evidence: what
must be true before the entitlement can even be requested.** An engineering
estimate for the CarPlay scene itself is the least useful thing it could
produce. If the honest answer is "blocked until release readiness is done",
that is a finding and it should be written as one.

---

## 7. The app opens on Massachusetts

**What exists.** `MKCoordinateRegion.massachusetts`
(`ios/Sources/Region.swift:9-12`) — a 2.6° box centred on 42.15, −71.8 — is
both the initial map camera and the address-search bias. Its own doc comment
says "When the app expands beyond MA, this is the single place to widen."

The app expanded beyond MA on 2026-08-29 and this did not move. The API serves
all six states (`docs/new-england-rollout.md`), so a Vermont trip is harder to
search for than a Needham one, and the app quietly hides five states of a build
that cost a 998k-edge rebuild to produce.

**Traps.**
- **This one needs the owner's judgement and the study must not settle it.**
  The `SCENIC_REGION` default is explicitly one of the seven held-out product
  decisions in `docs/consumer-polish-brief.md`. There are at least three
  defensible answers — open on the user's location, open on the six-state box,
  remember the last region used — and they differ in behaviour before location
  permission is granted, which is the case that decides it.
- Widening the *search bias* is not free in the way widening the *camera* is.
  `MKCoordinateRegion.around` (`ios/Sources/Region.swift:20-23`) exists because
  ranking by distance from a statewide box's centre offers "main street" four
  towns away. A six-state box makes that worse, not better. Cost the two
  separately.

---

## Done looks like

A single document in `docs/`, written to the standard of
`docs/scenery-cap-options.md`, containing:

1. A per-feature section for all seven: what exists today (with `file:line`),
   what would have to change, an honest cost, and what would kill it.
2. The `turn:lanes` per-state coverage census from §5, as a real number per
   state over the six-state extract — or a statement of why it could not be
   measured.
3. An explicit ordering recommendation with its reasoning, **and no choice
   made**: the document is chosen from, it does not choose.
4. For every item that touches one of the held-out product decisions in
   `docs/consumer-polish-brief.md` (§2, §3, §7), the decision named as the
   owner's to make, not answered.
5. Where an item is blocked rather than merely expensive (§6 is the candidate),
   the blocker stated as the finding, with what must be true first.
6. Honest-answer escape hatch: "this cannot be costed from the code alone, and
   here is the measurement that would settle it" is an acceptable answer for
   any section, and a better one than a guessed number.

## Out of scope

- **Building any of the seven.** No source file in `pipeline/`, `server/` or
  `ios/Sources/` should change. The `turn:lanes` census is a scratch script
  outside the repo, as the geodata studies were.
- The scoring ideas from the same brainstorm (negative landscape components,
  visibility, foliage, sun angle) — `claude/funny-elbakyan-93c75f` owns that
  ground.
- The detour-budget router work, which is a separate and much larger piece.

## Collisions — read before touching a file

Eleven worktrees are live. Two hold changes that overlap this ground:

- `claude/data-attribution` edits **`ios/Sources/RoutePanel.swift`** and adds
  `AboutView.swift`. §1 and §2 would both naturally reach for `RoutePanel`.
  Since this task writes no Swift, that is only a warning for whoever
  implements later — but do not "just add the button while you are here".
- `claude/github-description-trim-9bce8b` is **rewriting `README.md`** and
  moving its workings into `docs/extending.md`, `docs/roadmap.md`,
  `docs/scoring.md` and others. Two of the seven items (lane guidance, the
  Massachusetts camera) are README checklist entries that are moving.
  **Do not edit `README.md` in this task**, and cite it by content rather than
  by line number.
