# What is in here

Sunday Drive scores every road in New England for beauty and routes across that
score.
Almost none of the numbers it uses are guesses — `BETA`, `CONTROL_SECONDS`,
`SPEED_FACTOR`, `RELIEF_FULL`, `PREF_CURVE` and the scoring weights were each
fitted against measured data, and **this directory is where those measurements
live**. That is why it is large: the studies are the evidence for the constants,
and deleting one turns a fitted number into a magic number.

**Start with [the README](../README.md).** It is 117 lines and links the six
documents most people want. This file is the full index, for when the answer you
need is in a study rather than in the overview.

Everything here opens with a bold **Status:** line saying what state the tree was
in when it was written. Where a question has since been answered, the question
document carries a blockquote at the top pointing at the answer. Read the pointer
first — the body below it is a historical record, not a description of today.

**The app was renamed from Scenic to Victory Lap on 2026-09-20**
([`victory-lap-naming.md`](victory-lap-naming.md)) **and from Victory Lap to
Sunday Drive on 2026-09-21** ([`sunday-drive-naming.md`](sunday-drive-naming.md)),
each time applied to code, configuration and the currently-descriptive documents
only. Everything here written before those dates says "Scenic" or "Victory Lap"
and is left as written, for the reason in the paragraph above. The word "scenic"
also survives on purpose wherever it is the right English one — the *scenic
route*, the *scenic score*, the *scenic arm* — and in `route-census/`, where it
is a column value in published data.

---

## How it works — read these first

| doc | |
| --- | --- |
| [roadmap.md](roadmap.md) | **What is built, and what is open.** The only list of open work — everything else here is a record, not a backlog |
| [scoring.md](scoring.md) | The components, the weights, and the three failure modes the calibration report catches |
| [measuring-travel-times.md](measuring-travel-times.md) | The speed and junction model, how to take a drive worth analysing, how to read the report |
| [measuring-scenery.md](measuring-scenery.md) | The two buttons, the separation statistic, and the noise floor printed beside it |
| [directions-accuracy.md](directions-accuracy.md) | Forbidden turns and missing instructions, audited over 120 random routes |
| [extending.md](extending.md) | Where a new scenery component, a retune, or another region plugs in |
| [data-sources.md](data-sources.md) | What the app is built from, and what each source is owed |

## Scenery and scoring

| doc | |
| --- | --- |
| [geodata-sources-review.md](geodata-sources-review.md) → [geodata-sources-findings.md](geodata-sources-findings.md) | Are we using the right geographic data? OSM's polygons are 3.3× more complete in Rhode Island than Maine; the fix was WorldCover tree cover **alongside** `c_green`, not instead of it |
| [geodata-peer-review-verdict.md](geodata-peer-review-verdict.md) | Adversarial review of the above. Four attacks on the uniformity argument, all failed; four real defects found. Cited from `landcover.py` |
| [unpaved-and-urban-verdict.md](unpaved-and-urban-verdict.md) | Vermont has the prettiest roads and the worst scores. Surface measured mapping diligence, not beauty — it left the score and became a priced preference |
| [scenery-cap-options.md](scenery-cap-options.md) | **Standing negative result.** Five ways to raise the scenery cap, measured. `BETA` is a dead lever: the Dijkstra-valid region *is* the region where no extra km is worth adding |
| [scenery-grading-verdict.md](scenery-grading-verdict.md) | Twenty proposals for the grading model, with verdicts. Nothing built from either yet |
| [byway-relations.md](byway-relations.md) | Scenic byways from OSM route relations instead of three hardcoded names. Built — and three of the brief's own inferences failed, recorded under "What the build found" |
| [driver-preferences-study.md](driver-preferences-study.md) | What else should be a driver preference. Road class is orthogonal to scenery but loses to the pref slider, so it stays off. Carries one claim a later verdict overturned — flagged at the top |
| [new-england-terrain-findings.md](new-england-terrain-findings.md) | The relief raster at regional scale, the corrupt-pixel defect in the Terrarium source, and why `RELIEF_FULL` has no range left north of Massachusetts |

## Routing and travel time

| doc | |
| --- | --- |
| [junction-timing-plan.md](junction-timing-plan.md) | How travel times came to account for stopping: 22% error → 5.7%. **Cited by section from `graph.py` and `router.py`** — do not renumber its sections |
| [traffic-schedule-plan.md](traffic-schedule-plan.md) | **Standing negative result.** Time-of-day travel times: do not build this, not on borrowed data. The filename says "plan"; the verdict says no |
| [route-distribution-study.md](route-distribution-study.md) | 983 town-to-town trips, 5,192 routes. What the router actually offers, and the source of most numbers quoted elsewhere |
| [loop-routes-design.md](loop-routes-design.md) | The loop feature: three architectures measured, one built. §12 records where building it proved the design wrong |
| [astar-fastest-arm.md](astar-fastest-arm.md) | A\* on the fastest arm. Built 2026-09-19; the record ends on the four things the plan got wrong |
| [component-rebuild-cache-findings.md](component-rebuild-cache-findings.md) | A per-column cache so retuning a constant is not a full rebuild |

## The app

| doc | |
| --- | --- |
| [voice-guidance-plan.md](voice-guidance-plan.md) | Spoken guidance: the schedule is time-based because half of all maneuver legs are shorter than half a mile. **Cited by section from five files including `ios/project.yml`** — do not renumber |
| [current-street-display.md](current-street-display.md) | The road under the car, the three-state off-route readout — and why the street name **cannot** fix the snap start-point problem |
| [reroute-audit.md](reroute-audit.md) | Five findings on the reroute path, four fixed. Three items still open, listed at the end |
| [reroute-step-offset.md](reroute-step-offset.md) | The banner skipping the first turn of every reroute. Fixed; two items still open |
| [overnight-e2e-findings.md](overnight-e2e-findings.md) | 4,024 simulated drives, a directions audit and 7 real-app drives, 2026-09-30: nine findings. The harness tests in `ios/Tests/SimulatedDrive*.swift` cite them by number |
| [loop-matching-fix.md](loop-matching-fix.md) | Findings 1, 2, 2b and 4: loops matched the wrong pass of a road they drive twice. Fixed 2026-10-01 by `progress`'s continuity rule |
| [brand-ui-alignment.md](brand-ui-alignment.md) | What was decided when the interface was brought into line with the new logo, 2026-09-29 |
| [consumer-polish-defects.md](consumer-polish-defects.md) | Eight defects found by driving the app. Four still open — the table at the top says which |
| [interface-design.md](interface-design.md) | **The interface, designed again from nothing.** The planning sheet obscures Apple’s logo at *every* detent, which Attachment 6 §4 makes grounds for revoking MapKit access — so the planning surface becomes a page with a map card, and the bottom-left of every map is a keep-out. The dial prints what a setting costs and buys instead of `scenery strength 0.25`; the loop is one tap from a cold launch; the fixed safety notice gets a screen of its own. §13 reviews the two documents this replaced — their citations were re-resolved against a later tree and every one holds, so the defect is elsewhere: their brief ruled the attribution refactor out of scope, which is the constraint that shapes the whole interface. **Built the same day** — §2.3 and §4.3 carry corrections the implementation forced: MapKit does *not* lift its logo above a `safeAreaInset`, so the reserved strip is the only thing protecting it, and the dial’s staleness has to come from `responsePref`, not from `onEditingChanged` |
| [interface-design-mockups.html](interface-design-mockups.html) | Those screens, rendered. Twenty-one phone-framed states, dark and light, self-contained and offline — open it in a browser |

## Region and build

| doc | |
| --- | --- |
| [new-england-rollout.md](new-england-rollout.md) | The six-state rollout, executed. One decision in it was overruled by what shipped — flagged at the top |
| [new-england-expansion.md](new-england-expansion.md) | Staging the other five extracts, with two predictions that turned out wrong |

## Hosting, legal and product

| doc | |
| --- | --- |
| [release-plan.md](release-plan.md) | **Start here for anything about shipping.** The sequence the rest of this section does not contain: the membership gate, the three owner decisions priced by what deferring them costs, and why the order is set by external lead times rather than by irreversibility. Records two items believed open that are already done |
| [marketing-plan.md](marketing-plan.md) | **How people find the app, on a $0 budget.** The companion to the release plan: the 2026 App Store census (six of eight new scenic-driving apps have zero ratings), channels ranked for a free, New England-only app, the one-drive-a-week content system, and a launch timeline relative to release day with a worked example (L = 2026-10-22) and a go/no-go fallback |
| [hosting-options-findings.md](hosting-options-findings.md) | Where the API should live, and whether it can be free. Three figures in the brief were refuted by the findings and are marked there |
| [hosting-status-2026-09.md](hosting-status-2026-09.md) | The 2026-09-19 re-check of the four dated provider facts and the sizing measurement A\* invalidated. **Verdict unchanged**; the findings' 3.53 GB is superseded by a measured 4.4 GB |
| [hosting-independent-review.md](hosting-independent-review.md) | The 2026-09-28 review from outside that chain. **Oracle stays, but as a second connector beside a hardened laptop rather than a replacement.** Also finds the API's domain expiring 2026-10-28, and that a US Contabo box costs $6.58–7.90/mo, not €5.50. Lists edits it proposes to the three rows above |
| [../server/DEPLOY-oracle.md](../server/DEPLOY-oracle.md) | **How to actually build the Oracle box**, sign-up to cutover to rollback. Not a study — a tutorial, and the only document here you follow rather than read |
| [legal-and-ip-audit.md](legal-and-ip-audit.md) | What the app owes, and to whom |
| [licensing-and-attribution.md](licensing-and-attribution.md) | The credit strings and where they came from |
| [licensing-open-questions.md](licensing-open-questions.md) | The three questions the audit did not answer, and now **resolved** — §1a chose Apache-2.0 (`LICENSE`, `NOTICE`), §1b's ODbL claim on `route-census/` is discharged. The commit email and the Gap 2 Apple clauses are still open |
| [branding-brainstorm.md](branding-brainstorm.md) | The name has to change; candidates and how to check them. **Three of its four survivors are since knocked out** — corrected at the top |
| [trademark-knockout-findings.md](trademark-knockout-findings.md) | The free knockout screen, run against the live federal register and the open web. **Eight names screened to the same depth, four blocked and four clear** — Camber by a registration, Aimless, Detourist and Sunday Drive by common-law use; **Victory Lap (§15) is the one that shipped**. Carries the positive control that shows the register alone cannot clear a name, and what the paid clearance costs |
| [victory-lap-naming.md](victory-lap-naming.md) | "Victory Lap" put through the knockout screen, and the App Store listing it justifies. Survives the screen. The brief's "six Navigation/Travel apps named Scenic" is corrected to 25 — and the subtitle recommendation that followed from it was **overruled by the owner**, whose choice §6a records alongside the evidence against it. Companion to the four-name screen in `trademark-knockout-findings.md` |
| [scenic-name-viability-findings.md](scenic-name-viability-findings.md) | Was "Scenic" really unusable, and is any variation of it? **No, and no.** The bare word is blocked on both bars — a USPTO examiner has twice refused it as *merely descriptive* for travel software, 82 marks disclaim it, and at least 29 Navigation/Travel apps carry it. Thirteen variations screened: nine blocked, and the four survivors survive only by no longer reading as "scenic". Corrects the 25-app count to **≥29** and shows the store leg missing a live class 9 registration, the mirror of this section's positive control. Prices the reversal while the bundle identifier is still free |
| [sunday-drive-naming.md](sunday-drive-naming.md) | **The name as it stands.** "Sunday Drive" screened and adopted 2026-09-21, bundle id `app.sundaydrive`. Overrules `trademark-knockout-findings.md` §14, which invited it: the 2009 class 9 application died procedurally, and the class 42 mapping registration it was refused over has been cancelled since 2014. Zero live marks in 9/39/42, zero apps in Navigation/Travel, no descriptiveness refusal ever — the opposite of Scenic. Records the worst domain position of any candidate, and the three-layer env fallback |
| [sunday-drive-rename-audit.md](sunday-drive-rename-audit.md) | The 2026-09-21 rename audited across the whole tree: **3,843 name occurrences counted in code and classified, 16 defects, all in `docs/`, all fixed** — nothing compiled or executed was wrong. Also the census method, why `Color.brand` and the three env layers stay, and what a later merge of the redesign must resolve, including three added files that carry the old name and will *not* conflict |
| [app-store-submission.md](app-store-submission.md) | **Everything typed into App Store Connect, with the code that justifies it:** the custom EULA (paste-ready, minimum terms mapped), the nutrition label, the policy URL, export compliance, the App Review notes, and the submission checklist (§8). **Read §1 before touching the route-guidance notice — it already shipped** |
| [app-store-listing.md](app-store-listing.md) | **The listing copy, paste-ready and measured:** three seasonal promotional texts, the description with a source for every claim, and the 98-byte keyword list. Assumes C-3 merges first (§4) |
| [privacy-policy.md](privacy-policy.md) | **The developer's source copy of the published policy** (live at `jamesk1281.github.io/SundayDrive/privacy/` from `site/privacy/index.html`). Every factual claim cites the file that makes it true. §7 records how each open question was settled without a lawyer (owner decision, 2026-09-19), and §8 lists what would make the document wrong |
| `site/index.html` | The Support URL App Store Connect requires (guideline 1.5): a self-contained page with the contact address, the out-of-region and Precise Location answers, and the data credits. Dispatched 2026-10-04; it waits on the owner confirming `support@jameskouvlis.com` routes |
| [pre-submission-review-verdict.md](pre-submission-review-verdict.md) | **The pre-submission review**, 2026-09-30: verdict SUBMIT AFTER, and the C-items dispatched from it. Round 1's fixes merged as `f9f1937`. C-3, merged 2026-10-05: the dial's headline printed the scenic route's total beautiful miles beside a *difference* in minutes. It now prints the gain (`+47 min · +11 mi`), with the fall and no-gain cases falling back to the existing sentence. **Merged 2026-10-05**; App Store screenshot 1 still shows the old headline |
| [seasonal-closures.md](seasonal-closures.md) | Verdict C-1, dispatched 2026-10-04: 190 OSM winter-closed ways (165.5 km) are routed over, and the score prefers them. A per-request, date-aware mask in `Router._weights` from a PBF side table, with the cache-key and deploy-list traps. **Merged 2026-10-05, not yet deployed**: 197 ways and 182.2 km masked, Mt Greylock included; Acadia's park roads are untagged in OSM and slip through |
| [closed-roads.md](closed-roads.md) | Routes, loops and reroutes drove through what OSM closes to cars **all year**: locked and private gates, blocks, chains, bollards, fords and `motor_vehicle=no` roads. In a 320-request sample that was 5.6% of loops and 8.1% of scenic routes, with the fastest arm and the Crane Road reroute included. The fix is a side table from the seasonal scan, masked in `Router._weights` for every caller. Barriers are placed by where they stand on the graph, and the snap keeps a driver on their own side. **Built 2026-10-05, not merged:** 1,093 edges and 105 junction barriers closed, and exposure in the same sample falls to 0. The one departure from the brief is that crossing kerbs pass |
| [loop-lock-contention.md](loop-lock-contention.md) | Review finding K-1: loop planning queued drivers' rejoins and starved every route. Merged 2026-10-08, not deployed: the rejoin's own lock, a 503 for a loop build that would have queued, `.busy` and `.timedOut` in the app. With 4 loop clients a rejoin went from ×7–8 to ×1.2–1.3 |
| [new-england-only.md](new-england-only.md) | Make the app impossible to use without knowing it only works in New England: an on-device test against the six Census states, a search that only offers and accepts New England places, a dismissible "This won't work from here" at launch, and an opening camera that shows all six states. **Merged 2026-10-05.** Three of its assumptions failed on the simulator: the completer ignores `regionPriority`, a city's state is in the title, and Stowe's default loop is the Smugglers' Notch out-and-back (`NewEngland.swift`, `app-store-submission.md` §5) |
| [never-joined-drive.md](never-joined-drive.md) | A drive that never joined its route could never end (release-plan §6d). Fixed 2026-09-29: `NavigationModel.stalled` and `StalledView` |
| [coordinates-out-of-the-url.md](coordinates-out-of-the-url.md) | The route request moved from GET to POST, so coordinates no longer ride in the query string through Cloudflare (release-plan §6e) |
| [location-text-and-contact.md](location-text-and-contact.md) | The location purpose string and the privacy policy name all three uses, the New England check included, and Sources gains "Help and support" and "Email the developer" for guideline 1.5. **Merged 2026-10-05**, with the check it describes |
| [driving-app-features-cost.md](driving-app-features-cost.md) | Seven candidate features, costed. Neither document chooses what ships |
| [documentation-structure-proposal.md](documentation-structure-proposal.md) | Why this directory is shaped the way it is, and what was done to it on 2026-09-19 |

## Not documentation

- **`route-census/`** — 6,267 lines of committed CSV, the output of
  `tools/route_census.py`, plus the [ODbL notice](route-census/README.md) that
  `census-pairs.csv` needs. It is data, and it would sit better under `tools/`.
  **The move is now unblocked** — the notice that was the condition on it is
  written — but it was deliberately kept out of that change, because
  `licensing-open-questions.md` cites two live `raw.githubusercontent.com` URLs
  into this path. Update those citations in the same commit that moves the
  directory, and update `tools/route_census.py`'s `--out-dir` default.
- **`scenic_heatmap.png`** — the README's hero image. `out/` is gitignored, so
  it cannot be referenced from there.
- **`archive/`** — below.

## Archive

Shipped, superseded, and holding no measurement that does not survive somewhere
else. Kept rather than deleted because they are cheap to keep and this project
has been bitten once by a question that looked spent and was not. Nothing links
to these except their own answers. The six briefs that used to sit here were
deleted with the rest; [briefs.md](briefs.md) lists them.

| doc | where its content lives now |
| --- | --- |
| [stale-plan-after-arrival.md](archive/stale-plan-after-arrival.md) | `ios/Sources/RouteModel.swift:279-300` + four tests in `RouteModelTests.swift` |
| [roadmap-draft-2026-09-16.md](archive/roadmap-draft-2026-09-16.md) | Never adopted. `roadmap.md` replaced it, and `release-plan.md` sequences the release |

---

## Adding a document

Five rules. All five describe what this corpus already does when it is at its
best — they are written down because it grew by 29 documents in 17 days, and
whatever is tidy today will not be in a fortnight without them.

1. **Line 3 is a bold `**Status:**` line, and it states the tree — not the
   work.** "Built 2026-08-30" is not enough on its own: name the file, constant
   or commit that proves it. Four status lines here went stale precisely because
   they recorded a moment rather than a checkable fact, and the one that named a
   constant (`UNPAVED_ADJ is still -0.25`) is the one whose staleness was
   detectable.

2. **A question document gets a forward pointer the day its answer lands.** One
   blockquote at the top: what answered it, when, and which of its claims the
   answer refuted. `geodata-sources-review.md` is the model. This is the rule that
   stops the next person reading a stale question and re-doing settled work —
   which has cost this project a day once already.

3. **A document that corrects another edits the corrected one's header.** A
   correction is worthless where nobody reading the error will find it. Two such
   corrections existed here for weeks with neither target saying so.

4. **Open items graduate to [roadmap.md](roadmap.md) before the document is
   archived.** A defect flagged "out of scope" in three documents that all read
   as finished is a defect nobody owns — which is exactly what happened to the
   arrival gate.

5. **A dispatch brief is deleted in the merge that brings its work back.** It
   is named `<topic>-brief.md` while the work is out. When the work comes back,
   anything in it that nothing else records goes into the answer first: a
   measurement, a decision, a result. That answer is `<topic>-findings.md` /
   `-verdict.md`, or a plain `<topic>.md` record. Give the answer a different
   stem from the question. Then delete the brief, add its row to
   [briefs.md](briefs.md) with the commit that last had it, and repoint every
   citation (the grep below). Traps and done-lists are not worth keeping;
   `git show` has them. Committed data goes under `tools/`, not here.

**Archive rather than delete** anything that is not a brief, and only when the document has no inbound
reference and holds no measurement that does not survive elsewhere — check both,
don't assume. The check for the first:

```sh
grep -rn "$(basename "$doc")" README.md docs pipeline server ios tools tests
```

Note that **eight references from source cite a document by section number**
(`ios/project.yml`, `VoiceGuide.swift`, `graph.py`, `router.py` and four others).
Renumbering the sections of `voice-guidance-plan.md` or `junction-timing-plan.md`
silently breaks them — nothing fails, the pointers just aim at the wrong place.
