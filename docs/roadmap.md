# Roadmap: what happens next, in what order, and what each step is waiting on

**Status: drafted 2026-09-16.** Nothing here is built. This document orders the
work that is already diagnosed somewhere in `docs/`, the README's unchecked
items, and the consequences of decisions already taken — and it says what each
step is blocked on, because on this project the blockers are more informative
than the estimates.

Every size below is in **active days**, not calendar days, for the reason in
*Velocity* immediately below. The calendar dates are that size divided by an
assumed two active days a week; rescale them by changing that one number rather
than by re-reading the list.

## At a glance

| # | horizon | dates | size | the one thing it is waiting on |
|---|---|---|---|---|
| 1 | Land what is already built | now → 2026-09-23 | ≈2 active days | nothing — all of it exists already |
| 2 | The irreversible decisions | 09-23 → 10-07 | ≈4 active days | a name, and cloud credentials |
| 3 | Evidence | October 2026 | calendar-bound | a second driver, and a drive in Maine |
| 4 | Decide the product, then make it good | Nov–Dec 2026 | ≈8 active days | the dial-or-loop decision |
| 5 | Distribution, properly | Q1 2027 | ≈5 active days + queues | App Review, and a privacy policy |
| 6 | Region expansion | 2027 | ≈15 active days | two walls that must fall before the build |
| 7 | The fork | 2028+ | a rewrite of one component | scale nobody has yet |

The dependency that breaks the tidy order: a second driver needs the app on a
second phone, so **TestFlight is a prerequisite for evidence** (Horizon 3), which
makes the rename and the privacy manifest (Horizon 2) prerequisites too, because
the first upload fixes the bundle id forever. That single arrow is why Horizon 2
sits in front of the interesting engineering rather than behind it.

## Velocity — the measurement that makes the dates honest

`git log --all --date=short` over this repository:

| period | active days | commits | commits/active day |
|---|---|---|---|
| 2026-06-20 → 2026-09-16 (all of it) | 22 | 138 | 6.3 |
| 2026-08-11 → 2026-09-16 | 17 | 112 | 6.6 |
| 2026-08-26 → 2026-08-31 (the burst) | 6 | 81 | 13.5 |
| 2026-09-02 → 2026-09-15 | **0** | 0 | — |

Two things follow, and they matter more than any estimate in this document.

**The work happens in bursts and the bursts are short.** Six days at the end of
August produced 81 of the 112 commits of the last five weeks — 72% — and 59% of
everything in the repository's history. A phase sized at "three active days" is a
long weekend, not three weeks — *if* the weekend happens.

**A fortnight of silence just ended.** There are no commits between 2026-09-01
and today. So the risk to every date below is not that a phase takes longer than
sized; it is that no phase runs at all for two weeks. That is also the argument
for the ordering chosen here: the first horizon is entirely made of work that is
already finished and merely unlanded, so a single active day converts a fortnight
of drift into a clean state.

## The three tracks, and which one is the rate limiter

The project has three workstreams that proceed at genuinely different speeds, and
sequencing them as one list is what makes a plan wrong.

**Evidence** — drives, marks, drivers. Measured rate: **79 marks over 12 drives
= 6.6 marks per drive**. It cannot be hurried by working harder, it gates every
scoring change, and it is the only track where a second *person* is worth more
than a second day. Schedule it first and let it run underneath everything else.

**Distribution** — name, licence, attribution, privacy manifest, hosting, store.
Mostly admin, nearly no routing content, but it carries the only external
dependencies in the project (an App Review queue, a cloud account, a filed EULA)
and two of its items get **permanently** more expensive after the first store
submission. Cheap now, irreversible later.

**Engine** — router, scoring, region. The only effort-bound track, the one that
has real measurements behind its estimates, and the one with a hard
architectural fork in it (see *Horizon 7*).

The rate limiter is **evidence**. Everything the score does past today is gated
on marks that only exist after someone drives, and the repo's own conclusion is
that the marks it has are one person in one corner of one state.

## Where the project is today, for the record

- **Region:** six-state New England build serving by default — `server/app.py:74`
  defaults `SCENIC_REGION` to `New England`; 998,252 edges / 794,685 nodes.
- **Measured serving cost:** 3.53 GB peak RSS cold (3.85 GB with the access
  layers touched), 42.6 s load, **~835 ms** for a full two-arm request
  (Boston → Augusta, 262 km). Required parquets 214 MB; 382 MB with the access
  layers.
- **Scoring validated once, against a human:** separation **0.74** over 79 marks
  / 12 drives against a **0.63** noise floor, stable at 200/400/800 m windows.
- **Travel time measured:** pooled error 5.7%, down from 22% free-flow.
- **Directions audited:** illegal turns 18% of routes → 1%; misleading forks 78%
  → 0%, over 120 random routes.
- **Two branches carry finished work that is not on `main`** — see Horizon 1.
- **The backend suite is not green on the region it serves:** 347 pass, 1 fails
  against `data/processed-ne` and passes against `data/processed` (measured
  2026-09-16 — see 1e; it is a region-pinned assertion, not a router defect).
- **No `LICENSE`, no attribution in the README, no `PrivacyInfo.xcprivacy`,**
  bundle id still `app.scenic.demo`, `MARKETING_VERSION` `0.1`.

---

## Horizon 1 — now → 2026-09-23. Land what is already built. (≈2 active days)

Nothing in this horizon is new engineering. All of it is work that exists and is
not where it should be, which is the cheapest kind of progress available and the
failure mode this repo has already paid for once. It is also the horizon that
changes character the moment the repository becomes public: 1b and 1c go from
correct to urgent, because a public repo publishes a rendered map made from other
people's data under licences that ask to be named.

**1a. Merge the two unmerged branches, or delete their briefs.** `git branch
--no-merged main` returns exactly two, and both hold answers whose *questions*
are already on `main` — the trap where a session reads the working tree, finds
the question, and redoes the work:

| branch | carries | conflicts to expect |
|---|---|---|
| `claude/data-attribution` (+3) | `ios/Sources/AboutView.swift`, `ios/Tests/AttributionTests.swift`, `docs/legal-and-ip-audit.md`, `docs/branding-brainstorm.md` | `README.md`; add/add on `docs/licensing-and-attribution-brief.md` (`main` has its own copy from `ad5fc0b`) |
| `claude/admiring-torvalds-64b1d0` (+3) | `docs/hosting-options-findings.md`, `server/DEPLOY.md` hardening, a `pipeline/render.py` change | add/add on `docs/hosting-options-brief.md` (`main`'s copy came from `9a1bf45`) |

Both branches also rename `docs/scenic_heatmap.png` to
`docs/ma_scenic_heatmap.png` while `main` replaced that file with the New England
render. Resolve that deliberately: the README's image is the New England one now.

The attribution branch is the one that matters. `AboutView.swift` is the only
place the app credits OpenStreetMap, and the OSMF rule it was written against
asks for a credit that does not require interacting with the work to see. On
`main`, today, the app credits nothing.

**1b. Give the README an attribution block.** The README renders
`docs/scenic_heatmap.png`, a produced work derived from OSM, ESA WorldCover and
Terrarium, and `grep -niE "openstreetmap|odbl|contributors"` over it returns
nothing. Once the repository is public the README *is* the attribution surface
for that image. The strings already exist with their source URLs and check dates
beside them in `AboutView.swift` — copy, do not re-derive. Terrarium resolves to
four licensors at z11 over `elevation.py`'s bbox, one of which (NRCAN CDEM under
OGL-Canada) is not US public domain.

**1c. Decide the `LICENSE`.** There is no licence file at all, which for a public
repository means all rights reserved by default — the opposite of what a project
built entirely on open data should say. Two separable questions:

- *The code.* MIT or Apache-2.0. Apache-2.0 if the patent grant and the NOTICE
  file are wanted; MIT if brevity is. Either is compatible with everything in
  the tree — 56 Python packages, all permissive, one MPL-2.0 (`certifi`,
  unmodified, server-side), no GPL/AGPL, and zero third-party iOS dependencies.
- *The data that ships in the repo.* `data/` and `traces/` are gitignored, so no
  derived database ships — but `docs/route-census/census-routes.csv` (619 KB of
  route geometry statistics) and the heatmap PNG are derived from OSM and travel
  under ODbL's terms. Say so in one paragraph rather than leaving it implied.

**1d. Fix the README's stale ETA paragraph.** Its open `CONTROL_SECONDS` item
still says the router charges "9.5 s per signal, 9.3 s per stop sign".
`pipeline/router.py:199` has `{signal: 11.5, stop: 8.1, giveway: 4.7}` — re-fitted
2026-08-24. The item itself stands (the target is 11.9 / 8.5); only the
parenthetical is wrong, and it is wrong in the direction of understating the
work already done.

**1e. Run both suites once, as the gate — and fix the one test that is pinned to
the wrong region.** Run 2026-09-16 against `data/processed-ne`, the build the API
actually serves: **347 passed, 1 failed** in 4 minutes. The README's count of 348
is right; "green" is not.

The failure is `tests/test_api.py::test_the_route_that_found_this_defect_no_longer_returns_it`,
and it is a test defect rather than a router defect. Its docstring says the case
was caught "in Massachusetts", and the same test **passes against
`data/processed`**. Line 170 asserts the property the guard exists to hold —
scenic ≥ fastest — and that holds on both builds. Lines 172–173 then assert the
two arms are *identical*, which encoded the Massachusetts outcome, where the
guard had to fall back to the fastest route. On New England that pair
(Hancock → Shutesbury, pref 0.5) has a genuinely better scenic route available:
**6.79 against the fastest arm's 6.28**. The test fails because the product got
better.

So the fix is a decision about what the test is for. The general property is
already covered for the same pair at four prefs by
`test_the_scenic_arm_never_scores_below_the_fastest_arm`, which passes — so lines
172–173 should either move into a Massachusetts-only test or be dropped. ≈15
minutes, and worth doing before anything else runs the suite and learns to
ignore a red line.

Then the iOS suite **with `server/serve.py` warm**, because `LiveDriveTests`
skips silently without it and those six are the only tests that drive real route
geometry end to end. A green iOS run with skips is not a green run.

**Done looks like:** `git branch --no-merged main` is empty, the app and the
README both credit their data, `LICENSE` exists, both suites are green with zero
skips.

## Horizon 2 — 2026-09-23 → 2026-10-07. Make the irreversible decisions while they are still cheap. (≈4 active days)

Every item here gets permanently more expensive after the first App Store
submission, which is the argument for doing them before any of the interesting
engineering.

**2a. The rename.** `Scenic` is both taken by a senior direct competitor in the
same category and merely descriptive, which is the weakest thing a mark can be.
The code footprint is small and enumerated: `PRODUCT_BUNDLE_IDENTIFIER`,
target/scheme names, `Color.scenic` (13 uses), the `SCENIC_*` environment prefix
(~40), `CFBundleDisplayName`. The ~47 uses of "scenic route / scenic score /
scenic km" stay — that is correct English for the feature and costs nothing.
Recommended `Longcut`, tagline *"Take the long way."*; check any alternative
against the App Store search API rather than against taste. **Blocked on: one
decision from the owner.** ≈1 active day once decided.

**2b. `PrivacyInfo.xcprivacy`.** Now a submission requirement rather than a
future one: merging voice guidance put three persisted settings on `main` — the
chosen voice and a duration cache (`VoiceCatalogue.swift:118,148`) and the mute
flag (`VoiceGuide.swift:351`) — all of them `UserDefaults`, which is
`NSPrivacyAccessedAPICategoryUserDefaults`, a required-reason API. Half a day, including the
`project.yml` wiring and a test that the manifest ships in the bundle.

**2c. Re-fit `CONTROL_SECONDS` to the ten-drive numbers** (signal 11.9, stop
8.5). This is a deliberate step, not a drive-by: it moves every ETA the app
shows. Run `tools/fit_junction_cost.py` against the current build, confirm the
extract the analyser cached is the New England one, then change the constants —
no graph rebuild needed, which is why this is cheap. ≈0.5 active day.

**2d. Hosting.** The laptop is not broken; it was switched off, and the 530s were
the correct response to an absent origin. The reason to move is that a machine
someone turns off is not an always-on host. Recommended: Oracle Always Free A1
in `us-chicago-1` (+12 ms from Boston vs Ashburn, against +81 ms for Frankfurt),
deliberately provisioned at **≤8 GB** so the 3.85 GB footprint stays above the
20% idle-reclaim floor. Transfer 382 MB of parquet as a resumable copy. The
hostname is a Cloudflare tunnel, so re-migrating needs no DNS change and no App
Review — which is what bounds the downside if Oracle changes its allowance
again, as it did twice in 2026. Exit is Contabo at ~€5.50/mo. **Blocked on:
account credentials only the owner has.** ≈1 active day.

**2e. Unclip Apple's own map credit.** Attachment 6 §2.1 forbids obscuring it,
so this is a contract term rather than a review note, and the planning sheet
clips it at every detent because a sheet's bottom edge and MapKit's bottom-left
ornament are pinned to the same place. `.safeAreaPadding` does not move it —
measured, pixel-identical. The real fix plumbs the live detent height into the
map and needs a decision about `.large`, where the sheet covers ~92% of the
screen. **Blocked on: a product call.** ≈1 active day.

## Horizon 3 — October. Evidence. (calendar-bound, not effort-bound)

This is the horizon that decides whether the scenic score is a measurement or one
person's taste, and the only one that cannot be compressed by working harder.

**3a. A second driver — the highest-value item in the project.** 79 marks, one
person, one part of one state. A second driver tests the one claim the score
makes that no amount of self-consistency can defend. Target ≥20 marks each way,
then re-run the separation per driver and pooled; a score that separates for one
person and not the other has told you something important either way.

**There is a dependency here that is easy to miss:** a second driver needs the
app on a second phone, and free-tier signing caps the device at three apps and
will not launch on a locked phone. So **TestFlight becomes a prerequisite for
evidence**, not a distribution nicety — which pulls it out of Horizon 5 and into
this one, and which in turn makes Horizon 2's rename and privacy manifest
prerequisites too, since the first upload fixes the bundle id forever.

**3b. Twenty marks each way in Maine.** At the measured 6.6 marks a drive that is
several drives' worth of tapping, or one long drive taken with the buttons in
mind — and it tests two claims at once: that
OSM's green mapping is 3.3× thinner there than in Rhode Island (measured, and it
survived four attacks including a negative control on water, which spread only
1.52×), and that WorldCover tree cover corrects it. Until those marks exist the
region-wide re-fit in 3d cannot distinguish calibrating from averaging a bias.

**3c. Two cheap additions to any drive.** Drive one route twice at different
hours — the two drives behind the travel-time fit met 26 and 27 signals and
stopped at 4 and 12 of them, and that variance, not the model, is what now caps per-drive accuracy.
And deliberately route over a `giveway`: eight drives have met none, so 4.7 s is
still the only unmeasured number in `CONTROL_SECONDS`.

**3d. Then, and only then, rollout Phase 4 — the region-wide scoring re-fit.**
`RELIEF_FULL` (the 0.97 Spearman against 3DEP says it wants to be 110, not that
there is new information), `RAW_BASE`/`STRETCH` region-wide, and the
**`BETA`/`PREF_CURVE` re-sweep that re-fitting the composite forces** — that
re-sweep is a gate, not a nicety, because `minutes` is the Dijkstra weight and
changing the composite silently changes the router's detour appetite. Then a
score + graph rebuild, and **all three parquets copied to the serving box from
the same commit as the code**, or the API returns subtly wrong routes with no
error. ≈2 active days plus build time. **Blocked on: 3a and 3b.**

## Horizon 4 — November–December 2026. Decide what the product is, then make that one good. (≈8 active days)

**4a. The product decision: the dial or the loop.** Point-to-point with a
beauty/time dial is what the app opens on; the loop — "ninety minutes, nowhere to
be, bring me home the pretty way" — already ships (`pipeline/looper.py`,
`/api/loop`, `LoopPanel`) and is probably the actual product, because it is the
thing none of the competitors do and the one case where "fastest" has no meaning
to compete with at all — there is no destination. This is a decision, not work,
and everything else in this horizon is cheaper once it is made.

**4b. Longer routes, if they are wanted: the detour budget.** The pref slider
buys 1.61× travel time but never distance (0.86×), and that is structural, not a
constant — the region where `scipy`'s Dijkstra is valid is exactly the region
where no kilometre is worth adding for its own sake, so `BETA` is a dead lever
and Bellman-Ford is not a fallback (it did not finish in 900 s against a 112 ms
Dijkstra). The detour budget is the only measured option that produces longer
routes, and it is nearly the cheapest: two Dijkstras plus two O(V)
predecessor-tree passes price every via-node in the state at once, ~250–400 ms.
Its cost is retracing — under 5% of route km at a 2× budget on long trips, ~30%
at 4×. ≈2 active days.

**4c. Lane guidance.** Nothing reads `turn:lanes`, so nothing says "use the right
two lanes", and at a multi-lane exit the wrong lane is a missed exit however good
the maneuver text is. This is the largest remaining correctness gap in
directions. ≈2 active days.

**4d. `via`-way turn restrictions.** 604 of them, counted and skipped at build
time; honouring them needs the search to remember more than one junction back,
which is a real change to the router's state and not a constant. ≈2 active days.

**4e. Trace hygiene: record the router's snapped node, not the geocoder's
coordinates.** Better engineering (it is what the route was actually computed
from) and it retires the one clause of Apple's agreement that `DriveTrace`
currently engages. It changes the trace format the analysis tools read, so it is
the owner's call and it should land between drive batches, never mid-batch.
≈0.5 active day.

**4f. Start from the exact point.** `snap()` routes from the nearer end of the
snapped road — right street, median 99 m up it, p90 217 m. Splitting the snapped
edge into two virtual nodes per request takes that to zero. Scheduled late
deliberately, and for a measured reason: those README numbers come from random
bbox points that can land far from any road, and re-measured over 400 trips from
a point actually *on* a local road — a parked car — the offset is median 30 m
and its **net progress cost is median +1.2 m** (p90 +45 m), because both ends of
the snapped segment lie on the road the driver is already on. Large in metres,
nearly free in driving. Polish with a good story rather than a defect. ≈1 active
day.

## Horizon 5 — Q1 2027. Distribution, properly. (≈5 active days + queues)

TestFlight will already exist from Horizon 3. What is left is everything a store
listing needs that a research instrument never did:

- a **privacy policy** and a written **policy for drive traces** — they record
  where someone drove, timestamped to the second, and "they stay on the phone"
  is a fine answer for one user and not an answer for a listing;
- a **custom EULA filed in App Store Connect** carrying §3.3.15's fixed
  turn-by-turn notice verbatim (Apple's default Licensed Application EULA does
  **not** contain it; the string and two tests pinning it already exist in
  `AboutView.swift`);
- App Review itself — a queue, not a task, and the first submission is when the
  bundle id stops being changeable;
- the opening-region change from rollout Phase 7: initial camera and search bias
  from the last known location, falling back to a regional box. Do **not** widen
  the box to all six states — search ranks by distance from the region's centre,
  and a box centred in New Hampshire is worse for everyone than the
  Massachusetts fallback is today.

Deliberately **not** scheduled: a paid tier. The obvious competitor sells one, so
the question is real, but it is a business decision with no engineering
dependency in this document.

## Horizon 6 — 2027. Region expansion, and the two walls in front of it. (≈15 active days)

The order here is forced by measurement rather than preference. Both walls must
fall **before** a bigger extract is built, not after.

**6a. Make `elevation.py` tileable.** It holds one in-RAM float64 mosaic of the
whole bbox and then runs maximum/minimum filters over it, so peak ≈ 5× the
array: New England 5.6 GB, +NY 10.9 GB, Northeast 14.1 GB, East Coast 51.5 GB.
Relief is a local ~750 m operator, so this is trivially tileable with an overlap
halo — the wall is self-inflicted, which is the good kind. ≈3 active days.

**6b. Give the router a target early-exit.** Latency scales as **E^1.28** on real
topology (validated on the New England build, not on tiles), and
`router.route()` runs a full-graph Dijkstra with no early exit, so a 15 km trip
and a 190 km trip cost the same. New England's two-arm request is 835 ms;
doubling the edge count for New York puts it near 2 s. `dijkstra(..., limit=cost)`
took a Boston→Cambridge case from 79 ms to 4 ms — but the settled set is a cost
*ball*, 62% of Massachusetts by Boston→Worcester, so early-exit only pays once
the region is much larger than the trip. That is precisely the expansion case,
and it is why this lands here rather than in Horizon 4. ≈4 active days.

**6c. Then New York, then the Census Northeast (9 states).** Road miles scale
about 3× faster than PBF bytes, so size the graph by road miles and only the
download and the import by bytes: +NY is 6.35× Massachusetts, the Northeast 9 is
10.69×. Geofabrik ships `us-northeast-latest.osm.pbf` (1.79 GB) as exactly those
nine states. Build RAM runs 6.70 GB per GB of PBF.

**6d. Replace `CRS_METERS` before going south of roughly Pennsylvania.** The
current conformal conic is ≤0.31% anywhere in New England/NY/PA, 1.0% at
Atlanta, 3.9% at Miami. Fine northward; a defect southward. ≈1 active day, and
it must precede any southern extract.

**6e. The scoring components that are still wrong, in cost order.** `c_urban` is
confirmed backwards and WorldCover built-up measures it better (0.728 inverted
against 0.644); `c_farm` has the worst regional spread of any component at 5.9×.
Each is one `c_` column plus a `WEIGHTS` entry plus a re-fit plus a rebuild — the
pipeline is deliberately open-ended this way — but each is also gated on marks
in more than one state, and on changing **one weight at a time** so
`score.py`'s calibration report can still catch a component pinned at its
ceiling.

**The honest ceiling of the current architecture is the Census Northeast**, and
only after 6a and 6b.

## Horizon 7 — 2028 and beyond. The fork, and the options each gate opens.

**7a. The fork: past the East Coast, keep the scoring and change the router.**
East-of-Mississippi is 52.7× Massachusetts' road miles and the USA 114×. At that
size the right move is to put the scenic scoring into Valhalla or OSRM custom
costing rather than grow this Dijkstra. That is a rewrite of one component, not
of the project — and it is worth saying plainly that this was designed for:
`score.py` writes every `c_` column it computes, `graph.py` auto-detects them,
and `router.py` re-blends them per request, so the asset is the scoring pipeline
and the router is the replaceable part. Scoring CONUS is *already* affordable on
the WorldCover cost shape (153 tiles, ~6.4 GB, no mosaic, peak RSS is one tile
and does not grow with region). The router is the only thing that cannot come.

**7b. Options, each stated with the gate that would justify it.** None of these
is scheduled; each is here so that a future decision starts from a condition
rather than from enthusiasm.

| option | the gate that would justify it |
|---|---|
| CarPlay | the app is used on more than a handful of drives a week by someone other than its author |
| Android | a second platform's users exist, i.e. after a listing, not before |
| A public scenic-score tile or API service | someone asks for the score without the navigation — the scoring pipeline is the part that is genuinely novel |
| Marks as a data flywheel across many drivers | ≥3 drivers whose marks agree with each other more than with chance; and a hard line — marks calibrate the **model**, they never become the **routes**, because "every road is measured, not submitted" is the entire differentiator |
| Seasonal or time-of-day scenery (foliage, golden hour) | a measurement of it exists that this project made itself — the same bar the traffic verdict set |

## What this timeline deliberately does not schedule, and why

Keeping these visible is the point: each was investigated, decided against, and
is likely to be proposed again.

- **Time-of-day travel times on borrowed traffic data.** It would be the only
  unmeasured constant in `router.py`. If it is ever built, the measured route is
  to integrate the ETA along the *chosen* route rather than make the graph
  time-dependent — that cost 4.42× in a measurement, 3.61× of which was merely
  leaving `scipy`'s C loop.
- **Raising `BETA` to get longer routes.** Structurally dead: swept 8→512, it
  makes the router *more* determined to be short.
- **3DEP elevation.** Closed with a number: ρ=0.97 against the shipped relief.
  The uniform +10% is `RELIEF_FULL` wanting to be 110, not new information.
- **Benchmarking routes or ETAs against Apple.** The single most tempting
  experiment in the repo and a bright line in the developer agreement. Benchmark
  against recorded drives and a clock.
- **Re-surveying WorldCover's 2021 vintage** for tree cover. One epoch plus a
  full algorithm revision perturbs the score ~40× less than the change it was
  being compared against.
- **A five-point scenery scale** in place of the two buttons. It is answered at
  45 mph; a scale needs aiming and aiming needs looking at the phone.

## Gates, not dates

If only one section of this document survives, it should be this one. These are
the numbers that decide whether a phase is done, and they are all already
instrumented:

| gate | current | threshold |
|---|---|---|
| scenery separation vs its own printed noise floor | 0.74 vs 0.63 | above floor, at every window width, **per driver** |
| marks behind any regional or weight re-fit | 79, one driver, one state | ≥20 each way per new driver and per new region |
| pooled ETA error against recorded drives | 5.7% | ≤6%, and no single drive above ~10% without an explanation |
| illegal turns / misleading forks, over 120 random routes | 1% / 0% | no regression |
| two-arm request latency | 835 ms | ≤1.3 s |
| serving RSS | 3.53–3.85 GB | leaves headroom on the box it is on |
| suites | 347 passed / 1 failed on `data/processed-ne`, measured 2026-09-16; iOS last counted at 105 on 2026-08-25, before the voice and loop suites | green on the region actually served, **zero skips**, with a local server warm |

And one rule that is not a number: **when a dispatched session returns, merge its
branch or delete its brief, the same day.** Horizon 1 exists because that rule was
broken twice, and it is the single cheapest thing on this list.
