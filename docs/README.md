# What is in here

Scenic scores every road in New England for beauty and routes across that score.
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
| [unpaved-and-urban-brief.md](unpaved-and-urban-brief.md) → [unpaved-and-urban-verdict.md](unpaved-and-urban-verdict.md) | Vermont has the prettiest roads and the worst scores. Surface measured mapping diligence, not beauty — it left the score and became a priced preference |
| [scenery-cap-options.md](scenery-cap-options.md) | **Standing negative result.** Five ways to raise the scenery cap, measured. `BETA` is a dead lever: the Dijkstra-valid region *is* the region where no extra km is worth adding |
| [scenery-grading-review-brief.md](scenery-grading-review-brief.md) → [scenery-grading-verdict.md](scenery-grading-verdict.md) | Twenty proposals for the grading model, with verdicts. Nothing built from either yet |
| [byway-relations-brief.md](byway-relations-brief.md) | Scenic byways from OSM route relations instead of three hardcoded names. Built — and three of the brief's own inferences failed, recorded at the end |
| [driver-preferences-study.md](driver-preferences-study.md) | What else should be a driver preference. Road class is orthogonal to scenery but loses to the pref slider, so it stays off. Carries one claim a later verdict overturned — flagged at the top |
| [new-england-terrain-findings.md](new-england-terrain-findings.md) | The relief raster at regional scale, the corrupt-pixel defect in the Terrarium source, and why `RELIEF_FULL` has no range left north of Massachusetts |

## Routing and travel time

| doc | |
| --- | --- |
| [junction-timing-plan.md](junction-timing-plan.md) | How travel times came to account for stopping: 22% error → 5.7%. **Cited by section from `graph.py` and `router.py`** — do not renumber its sections |
| [traffic-schedule-plan.md](traffic-schedule-plan.md) | **Standing negative result.** Time-of-day travel times: do not build this, not on borrowed data. The filename says "plan"; the verdict says no |
| [route-distribution-study.md](route-distribution-study.md) | 983 town-to-town trips, 5,192 routes. What the router actually offers, and the source of most numbers quoted elsewhere |
| [loop-routes-design.md](loop-routes-design.md) | The loop feature: three architectures measured, one built. §12 records where building it proved the design wrong |
| [astar-fastest-arm-brief.md](astar-fastest-arm-brief.md) | A\* on the fastest arm. Nothing built |
| [component-rebuild-cache-brief.md](component-rebuild-cache-brief.md) → [component-rebuild-cache-findings.md](component-rebuild-cache-findings.md) | A per-column cache so retuning a constant is not a full rebuild |

## The app

| doc | |
| --- | --- |
| [voice-guidance-plan.md](voice-guidance-plan.md) | Spoken guidance: the schedule is time-based because half of all maneuver legs are shorter than half a mile. **Cited by section from five files including `ios/project.yml`** — do not renumber |
| [current-street-display.md](current-street-display.md) | The road under the car, the three-state off-route readout — and why the street name **cannot** fix the snap start-point problem |
| [reroute-audit.md](reroute-audit.md) | Five findings on the reroute path, four fixed. Three items still open, listed at the end |
| [reroute-step-offset.md](reroute-step-offset.md) | The banner skipping the first turn of every reroute. Fixed; two items still open |
| [consumer-polish-brief.md](consumer-polish-brief.md) | Eight defects found by driving the app. Four since fixed — the table at the top says which |

## Region and build

| doc | |
| --- | --- |
| [new-england-rollout.md](new-england-rollout.md) | The six-state rollout, executed. One decision in it was overruled by what shipped — flagged at the top |
| [new-england-expansion.md](new-england-expansion.md) | Staging the other five extracts, with two predictions that turned out wrong |

## Hosting, legal and product

| doc | |
| --- | --- |
| [hosting-options-brief.md](hosting-options-brief.md) → [hosting-options-findings.md](hosting-options-findings.md) | Where the API should live, and whether it can be free. Three figures in the brief were refuted by the findings and are marked there |
| [legal-and-ip-audit.md](legal-and-ip-audit.md) | What the app owes, and to whom |
| [licensing-and-attribution-brief.md](licensing-and-attribution-brief.md) | The credit strings and where they came from |
| [licensing-open-questions-brief.md](licensing-open-questions-brief.md) → [licensing-open-questions.md](licensing-open-questions.md) | The three questions the audit did not answer, and now **resolved** — §1a chose Apache-2.0 (`LICENSE`, `NOTICE`), §1b's ODbL claim on `route-census/` is discharged. The commit email and the Gap 2 Apple clauses are still open |
| [odbl-repository-compliance-brief.md](odbl-repository-compliance-brief.md) | What §1b's finding took to close: the notice on `census-pairs.csv`, the heatmap credited, and the two things in the same blast radius. Its "no `LICENSE` file" instruction was overtaken by the §1a decision |
| [branding-brainstorm.md](branding-brainstorm.md) | The name has to change; candidates and how to check them |
| [victory-lap-naming-brief.md](victory-lap-naming-brief.md) → [victory-lap-naming.md](victory-lap-naming.md) | "Victory Lap" put through the knockout screen, and the App Store listing it justifies. Survives the screen. The brief's "six Navigation/Travel apps named Scenic" is corrected to 25, and the subtitle recommendation follows from that. Companion to the four-name screen in `trademark-knockout-findings.md` |
| [driving-app-features-brief.md](driving-app-features-brief.md) → [driving-app-features-cost.md](driving-app-features-cost.md) | Seven candidate features, costed. Neither document chooses what ships |
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
to these except their own answers.

| doc | where its content lives now |
| --- | --- |
| [stale-plan-after-arrival.md](archive/stale-plan-after-arrival.md) | `ios/Sources/RouteModel.swift:279-300` + four tests in `RouteModelTests.swift` |
| [beautiful-miles-and-the-slider-brief.md](archive/beautiful-miles-and-the-slider-brief.md) | `ios/Sources/RoutePanel.swift:24-51` — the sweep table and all three traps, verbatim |
| [new-england-terrain-brief.md](archive/new-england-terrain-brief.md) | `pipeline/elevation.py:50-58`, and `new-england-terrain-findings.md` |
| [landcover-implementation-brief.md](archive/landcover-implementation-brief.md) | `geodata-sources-findings.md` and `geodata-peer-review-verdict.md`; its reading order became this file |
| [voice-guidance-plan-brief.md](archive/voice-guidance-plan-brief.md) | `VoiceGuide.swift:12-20`, and re-measured on a second sample in `voice-guidance-plan.md` §3 |
| [geodata-peer-review-brief.md](archive/geodata-peer-review-brief.md) | `geodata-peer-review-verdict.md`, which is the review it commissioned |
| [documentation-structure-brief.md](archive/documentation-structure-brief.md) | `documentation-structure-proposal.md` |

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
   answer refuted. `hosting-options-brief.md` is the model. This is the rule that
   stops the next person reading a stale question and re-doing settled work —
   which has cost this project a day once already.

3. **A document that corrects another edits the corrected one's header.** A
   correction is worthless where nobody reading the error will find it. Two such
   corrections existed here for weeks with neither target saying so.

4. **Open items graduate to [roadmap.md](roadmap.md) before the document is
   archived.** A defect flagged "out of scope" in three documents that all read
   as finished is a defect nobody owns — which is exactly what happened to the
   arrival gate.

5. **Name it `<topic>-brief.md` for the question and `-verdict.md` / `-findings.md`
   for the answer, never the same stem for both.** Committed data goes under
   `tools/`, not here.

**Archive rather than delete**, and only when the document has no inbound
reference and holds no measurement that does not survive elsewhere — check both,
don't assume. The check for the first:

```sh
grep -rn "$(basename "$doc")" README.md docs pipeline server ios tools tests
```

Note that **eight references from source cite a document by section number**
(`ios/project.yml`, `VoiceGuide.swift`, `graph.py`, `router.py` and four others).
Renumbering the sections of `voice-guidance-plan.md` or `junction-timing-plan.md`
silently breaks them — nothing fails, the pointers just aim at the wrong place.
