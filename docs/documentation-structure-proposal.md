# A structure for `docs/` — what to keep, what to archive, and the rule that stops it recurring

**Status: proposed 2026-09-19, and applied the same day.** The plan in §7 has
been carried out, with two departures recorded at the end of §7. The corpus it
was measured against (`378aaee`, 30 documents) has since grown to 47 as nine
branches merged; every disposition below was re-verified against the merged tree
before it was acted on, and all six archive candidates still qualified unchanged.

Originally: *"nothing changed. No file was edited, moved, renamed or deleted."*
That was true when it was written and is the reason it was scoped that way. This document and `docs/archive/documentation-structure-brief.md`
(the question it answers) are the only two files this work added. Everything
below was measured against `main` at `378aaee` and against the nine unmerged
branches listed in §2; every disposition cites the line that justifies it.

Answers `docs/archive/documentation-structure-brief.md`. Reading order: that file first
— it holds the measurement table this one does not repeat.

---

## The answer in five sentences

**The corpus is in better shape than it looks, and the right change is small.**
It is not 11,466 lines of dead planning: 104 inbound references across 42 files
point into it, 22 of those files are source code, and eight of those cite a
document *by section number*. What is actually wrong with it is four things,
none of which is volume — **four status lines that misdescribe the working
tree**, **no index**, **no back-pointer from a corrected document to its
correction**, and **at least one real open defect stranded inside a document
that reads as finished**. Fixing those costs about a dozen one-line edits and
three file moves, against the 42-file, 104-reference edit that a subdirectory
reorganisation would cost. **The single highest-value output is not a
reorganisation at all — it is a written convention**, because `docs/` grew by
29 documents in 17 days and has 15 more inbound on unmerged branches right now.

---

## 1. What I checked, and what the brief got right

The brief's measurement table **reproduces exactly**. I re-ran its one-liner and
matched every row. Its central mechanism — the corpus carries its own triage key
in a bold self-declared status line — is real and is the right place to start.

Its hardest claim also holds, and I extended the test. The brief verified that
`landcover-implementation-brief.md`'s threshold table survives in two later
documents. I tested the stronger version of the same rule on three more
documents and found something better than redundancy:

> **This project moves a document's argument into the code comment when the work
> lands.** That is *why* implemented briefs are safely disposable here — not
> because they shipped, but because the evidence was carried forward.

Verified, with the numbers intact on the other side:

| document | where its argument now lives | what survived |
| --- | --- | --- |
| `stale-plan-after-arrival.md` | `ios/Sources/RouteModel.swift:279-300` | the 2026-08-25 date, the 86 seconds, Harvard, the **38 km**, the nine-minute parked trace, *and* the `end`/`endQuery` decision — plus a loop-tab extension the document never covered |
| `beautiful-miles-and-the-slider-brief.md` | `ios/Sources/RoutePanel.swift:24-51` | the whole pref-sweep table (`0.75 / 0.56 / 24.5 / 7.01 / 22%`), "the first quarter buys 2% of what the whole slider buys", the sqrt rationale, the 55%/59% figures, and all three traps |
| `new-england-terrain-brief.md` | `pipeline/elevation.py:50-58` | 13 px → 15 px, 738 m → 851 m, the 15% widening, and why `42.05` is the fitted latitude |

Four tests hold the first one (`ios/Tests/RouteModelTests.swift:53-94`),
including `test_a_finished_drive_keeps_the_destination`, which pins the
*decision* rather than the defect. That is the cleanest disposable document in
the corpus, and it is disposable for a reason that can be checked rather than
assumed.

## 2. Four things the brief's picture is missing

These change the plan, so they are stated before the dispositions.

### 2.1 Nine unmerged branches, not six — and `docs/` is about to grow 52%

`git branch --no-merged main` returns nine. The brief lists six. The three it
misses are `claude/licensing-open-questions` (the task it said was "in flight"
has since committed: 857 lines in two files), `claude/project-feature-brainstorm-a09a8d`
(265 lines), and `claude/scenery-grading-brainstorm-30d14e` — which adds
`docs/scenery-grading-review-brief.md`, **the same filename `claude/funny-elbakyan-93c75f`
adds**. Those two branches will conflict with each other, not just with `main`.

Counted per branch against its own merge base (`git diff $(git merge-base main $b)..$b`,
which is the only honest way to read these — a plain `main..branch` diff reports
six deletions on `claude/data-attribution` that are an artifact of a stale base,
and the heatmap rename on three branches is the same artifact in reverse):

| branch | new docs | new lines |
| --- | ---: | ---: |
| `claude/github-description-trim-9bce8b` | 5 | 423 |
| `claude/funny-elbakyan-93c75f` | 4 | 1,945 |
| `claude/admiring-torvalds-64b1d0` | 1 | 1,028 |
| `claude/licensing-open-questions` | 2 | 857 |
| `claude/data-attribution` | 2 | 658 |
| `claude/project-feature-brainstorm-a09a8d` | 1 | 265 |
| `claude/scenery-grading-brainstorm-30d14e` | (duplicate filename) | — |
| **total** | **15** | **5,176** |

**`docs/` goes from 29 files / 11,249 lines to 44 files / 16,425 lines** when
these land — +52% in files, +46% in lines. No branch deletes a document. **A
structure proposed for 30 files that has no rule for the 15 arriving is already
out of date.** This is the single strongest argument for §6 over §4.

### 2.2 The code cites documents *by section number*

The brief counts inbound references. It does not say what kind they are. Eight
are pointers into a specific section of a specific document, from source and
test files:

```
ios/project.yml                        -> docs/voice-guidance-plan.md §1
ios/Tests/LocationManagerTests.swift   -> docs/voice-guidance-plan.md §1
ios/Tests/VoiceGuideTests.swift        -> docs/voice-guidance-plan.md §1, §10
ios/Sources/VoiceCatalogue.swift       -> docs/voice-guidance-plan.md §2
ios/Sources/VoiceGuide.swift           -> docs/voice-guidance-plan.md §1
pipeline/graph.py                      -> docs/junction-timing-plan.md §13
pipeline/router.py                     -> docs/junction-timing-plan.md §5, §10
```

This matters twice over. **Renaming or moving these files breaks the build's own
documentation**, including `ios/project.yml`. And **merging a brief into its
answer renumbers the sections**, silently invalidating every one of these
pointers — which is most of the case against Question 2.

The full cost of a blanket move, measured: **104 inbound reference occurrences
across 42 files, 22 of them source or config** — all eight `pipeline/` modules,
`server/app.py`, five `ios/Sources/` files, three `ios/Tests/` files,
`ios/project.yml`, two `tools/` scripts and four `tests/` modules.

### 2.3 Four status lines misdescribe the working tree

The triage key works, but it records **state at the time of writing, not fact**.
For a question document that state is obsolete the moment its answer lands. Four
are wrong against the tree today, and I verified each against code:

| document | says | is |
| --- | --- | --- |
| `voice-guidance-plan.md:9` | "**Nothing here is built.** No Swift file under `ios/Sources/` was touched" | Built. `VoiceGuide.swift` (29 KB), `VoiceCatalogue.swift` (11 KB), two test files, commits `67ffc46` and `0b1f240`. `throwaway/voice-audio-spike` merged in `4a02da0`. |
| `consumer-polish-brief.md:3` | "diagnosed 2026-08-29, **nothing changed**" | At least four of its eight defects are fixed: #1 (`RouteService.swift:62-64` now returns a friendly `.unreachable(status)`), #2 (`RouteComparison` now owns both minute figures, so the cards and the sentence share one rounding), #7 (`NavView.swift:106-108` no longer silently no-ops on a nil fix), #8 (`LoopModel.swift:137,148` names the place). |
| `unpaved-and-urban-brief.md:3` | "`UNPAVED_ADJ` is still -0.25" | It is `LEGACY_UNPAVED_ADJ` (`pipeline/router.py:45`) and the penalty moved out of the score into `pref`. |
| `new-england-rollout.md:82` | "Decided 2026-08-26: band the filter by latitude", with three reasons banding beats pinning | The **pinned** latitude shipped (`6cd0620`). Recorded already, in `new-england-terrain-findings.md:199` — where nobody reading the rollout doc will see it. |

**This is the corpus's actual defect, and it is the opposite of the one the task
assumed.** The archive is not too big; it is unverified. The largest document in
`docs/` is also the most-cited from code (7 references, 5 files) and is the one
that lies about its own status.

### 2.4 A real open defect is stranded in documents that read as finished

Three documents flag the same bug as out of scope and still open —
`stale-plan-after-arrival.md:53`, `reroute-step-offset.md:211`,
`reroute-audit.md:641`. It is still live: **all three arrival tests are gated on
`hasJoinedRoute`** (`ios/Sources/NavigationModel.swift:849-857`), so a car that
never joins its route can never register arrival.

`docs/roadmap.md` — the document on `claude/github-description-trim-9bce8b`
that is about to become the canonical open-items list — **does not carry it.**
Nor does it carry `new-england-terrain-findings.md:218`'s finding that
`RELIEF_FULL = 100` saturates 13.4% of northern New England, where a 1,453 m
White Mountains ravine scores identically to a 100 m rise outside Worcester.

**So deletion is not yet safe.** Harvesting open items into `roadmap.md` is a
precondition for archiving anything, and it is step 2 of §7.

---

## 3. Every document, with a disposition

Dispositions are **keep** (stays where it is), **archive** (moves to
`docs/archive/`, still in git and still readable), **pointer** (a one-line
forward reference added at the top, nothing else), **status** (its status line
is corrected), and **hold** (blocked on an unmerged branch or an owner
decision). Nothing is proposed for outright deletion; §5 says why.

### 3.1 Load-bearing — cited from source code, cannot move or rename

Moving any of these means editing source. All **keep**.

| doc | lines | refs | why it stays |
| --- | ---: | ---: | --- |
| `voice-guidance-plan.md` | 813 | 6 | 7 occurrences in 5 files incl. `ios/project.yml`, cited by section. **+ status** — see §2.3 |
| `junction-timing-plan.md` | 571 | 6 | `graph.py §13`, `router.py §5 §10`, `common.py`, `analyze_trace.py`, `test_routing.py`; inherits the README link via `measuring-travel-times.md` |
| `loop-routes-design.md` | 662 | 5 | `looper.py`, `app.py` ×2, `RouteService.swift`, `test_loops.py` |
| `unpaved-and-urban-verdict.md` | 549 | 5 | `router.py` ×2, `score.py`, `test_scoring.py`, `test_routing.py`; inherits the README link via `scoring.md` |
| `route-distribution-study.md` | 571 | 5 | `app.py`, `RoutePanel.swift`, `test_api.py`, `route_census.py`. Also the source of every measurement in two other docs |
| `scenery-cap-options.md` | 602 | 5 | `scenery_cap_experiment.py`, `looper.py`. Records that `BETA` is a dead lever — a standing negative result |
| `geodata-sources-findings.md` | 761 | 8 | `score.py`; most-linked doc in the corpus after the rollout; inherits the README link via `scoring.md` |
| `geodata-peer-review-verdict.md` | 538 | 5 | `landcover.py` |
| `byway-relations-brief.md` | 313 | 2 | `extract.py`. Status says built — but §§1–8 are the *findings* appended below the brief, and three of the brief's inferences failed there |
| `directions-accuracy.md` | 162 | 1 | The only doc the trimmed README still links directly |

### 3.2 Holds live open work — keep, and harvest into `roadmap.md` first

| doc | lines | disposition | what is open |
| --- | ---: | --- | --- |
| `reroute-audit.md` | 652 | keep + **status** | Three open items at `:641` — the arrival gate, the un-backfillable request record, the unfitted 500 m re-seat window |
| `reroute-step-offset.md` | 231 | keep + **status** | Two at `:203` — remaining/ETA still credit undriven route; the arrival gate. Its status ("**Fixed 2026-08-25**") is in ¶2, not the conventional slot — it needs *moving*, not inventing |
| `consumer-polish-brief.md` | 358 | keep + **status** | Four of eight now fixed (§2.3); the other four need re-checking before anyone trusts the list |
| `new-england-terrain-findings.md` | 277 | keep | Finding 3 (`RELIEF_FULL` saturates north of MA) and Finding 4 (filter headroom) are unacted-on and in no roadmap |

### 3.3 Standing answers to questions that will be asked again — keep

These have low or zero inbound references and are still the most expensive
documents to lose, because each one is a *negative* result. A negative result
that is not written down gets re-proposed.

| doc | lines | refs | the standing answer |
| --- | ---: | ---: | --- |
| `traffic-schedule-plan.md` | 326 | 2 | "Do not build this — not on borrowed data." Leads with the verdict as an H2 at line 3, so it does declare a status, just not in the bold form |
| `current-street-display.md` | 268 | **0** | Part two: the street name **cannot** fix the reroute start-point problem, because `snap` chooses geometrically and the name is an output of the lookup, not an input. With it, the 23%→0% wrong-road measurement over 400 blocks and the 3,857-sample direction check |
| `driver-preferences-study.md` | 804 | 3 | Road class is orthogonal to scenery. **+ pointer** — it carries a claim `unpaved-and-urban-verdict.md:289` measured wrong ("`surface` is NOT on the edges"), and nothing at the top of it says so |
| `new-england-expansion.md` | 393 | 2 | "Results, 2026-08-25" holds two predictions that turned out wrong — the kind of record the project's attack-the-plan practice runs on |

### 3.4 Question halves of landed pairs — pointer, do not merge

Each already has its answer on `main`. Each needs one line at the top naming it.
See Question 2 for why merging is the wrong move.

| question | lines | its answer | note |
| --- | ---: | --- | --- |
| `unpaved-and-urban-brief.md` | 175 | `unpaved-and-urban-verdict.md` | **+ status**: `UNPAVED_ADJ` no longer exists under that name |
| `geodata-peer-review-brief.md` | 176 | `geodata-peer-review-verdict.md` | |
| `geodata-sources-review.md` | 206 | `geodata-sources-findings.md` | |
| `new-england-rollout.md` | 440 | (executed) | **+ correction**: §0a's banding decision is contradicted by shipped code. 8 inbound doc references — the most-linked document in `docs/`, and it contains a decision the code overruled |

### 3.5 Archive — shipped, superseded on content, and moving them breaks almost nothing

Each of these has **at most one inbound link**, and in every case that link is
from its own answer document. Archiving all six costs **three one-line link
edits**. That is not a coincidence — having no inbound references is what
qualifies them.

| doc | lines | refs | the measurement it uniquely holds |
| --- | ---: | ---: | --- |
| `stale-plan-after-arrival.md` | 145 | 1 (`reroute-audit.md`) | **None.** Fully restated at `RouteModel.swift:279-300` with four tests. The strongest case in the corpus |
| `beautiful-miles-and-the-slider-brief.md` | 239 | **0** | **None.** Every number in it is quoted from `route-distribution-study.md`; the design rationale is in `RoutePanel.swift:24-51` verbatim, traps included |
| `landcover-implementation-brief.md` | 256 | **0** | **None on content** — the brief verified its own threshold table survives in `geodata-sources-findings.md` and `geodata-peer-review-verdict.md`. **But lift its first eight lines first**: they are a four-document reading order, the closest thing `docs/` has to an index, and they belong in `docs/README.md` (§4) |
| `new-england-terrain-brief.md` | 134 | 1 (its findings) | **None.** The 13 px/15 px table is in `pipeline/elevation.py:50-58`; the prediction table is answered in `new-england-terrain-findings.md` |
| `voice-guidance-plan-brief.md` | 220 | 1 (its plan) | **None that is still load-bearing.** The 455-leg distribution is compressed into `VoiceGuide.swift:12-20` and *independently replicated on a different sample* at `voice-guidance-plan.md:156-160` (194 legs, median 507 m vs 746 m, 14.4% vs 12.1% under 100 m) |
| `geodata-peer-review-brief.md` | 176 | 1 (its verdict) | **None.** It is a task brief whose verdict is on `main` and is itself cited from `landcover.py` |

### 3.6 Hold — blocked on an unmerged branch or an owner decision

| doc | lines | why it cannot be triaged here |
| --- | ---: | --- |
| `hosting-options-brief.md` | 195 | **Trap 4, exactly.** Zero inbound on `main`, status "nothing changed", looks spent — and its 1,028-line answer is on `claude/admiring-torvalds-64b1d0`, which already conflicts. Worse, `claude/code-review-max-317af8` rewrites *the brief itself* (+223/−59). **Two branches change this one file in different directions.** Touch nothing until both land |
| `licensing-and-attribution-brief.md` | 212 | Its "nothing changed" is still **true** — `grep -l OpenStreetMap ios/Sources server` returns nothing, and there is no `LICENSE` file. But `claude/data-attribution` rewrites it (+350) and `claude/licensing-open-questions` adds 857 lines beside it. Three-way; needs the owner |
| `licensing-open-questions-brief.md` | 217 | Not on `main`; task in flight. Leave alone, as the brief says |

### 3.7 Not markdown

| entry | size | disposition |
| --- | ---: | --- |
| `scenic_heatmap.png` | 2.0 MB | **Keep, in place.** README hero image; `out/` is gitignored so it cannot be referenced from there. Note that three unmerged branches still carry it under the older name `ma_scenic_heatmap.png` — `main` renamed it, and those branches will conflict on it |
| `route-census/` | 0.7 MB, 6,267 lines | **Move to `tools/route-census/`** — see Question 4 |

---

## 4. The proposed structure

**Flat, with an index, plus one archive subdirectory that only ever receives
zero-inbound documents.** Concretely, after the in-flight branches land:

```
README.md                    113 lines, six-item index   (already done — do not redo)
docs/
  README.md                  NEW: the index. One line per document, grouped.
  roadmap.md                 the only list of open work            } the five
  scoring.md                 how the score works                   } topic docs
  measuring-travel-times.md  the clock, and how to take a drive    } from the
  measuring-scenery.md       the two buttons and the noise floor   } README trim
  extending.md               where the next feature plugs in       }
  directions-accuracy.md     linked directly from the README
  <the studies and verdicts, flat, ~30 files>
  archive/                   shipped, zero-inbound, restated in code
  scenic_heatmap.png
tools/route-census/          moved out of docs/ — it is data
```

Three reasons this is the shape, rather than `how-it-works/` + `studies/` +
`archive/`:

1. **The README trim already built the hierarchy, and it is link-preserving.**
   Read it before proposing anything else. Main's README links four documents
   directly; the trimmed one links `directions-accuracy.md` and hands the other
   three down a level — `scoring.md` links `geodata-sources-findings.md` and
   `unpaved-and-urban-verdict.md`, `measuring-travel-times.md` links
   `junction-timing-plan.md` twice. **No document loses its inbound link; each
   gains a better-placed one.** That is already README → topic → study. A
   directory tree would be a third, competing hierarchy over the same 44 files.

2. **Subdirectories cost 104 reference edits across 42 files** (§2.2), 22 of them
   source and config, and eight of those cite section numbers that a move
   invites someone to renumber. `docs/archive/` avoids all of it by construction:
   only documents with no inbound references go in, so moving them is free.

3. **A stranger arriving cold needs one file to read, not a directory to
   explore.** The repo is public. `docs/README.md` with 44 annotated lines is
   navigable in thirty seconds; four directories are four guesses.

The index is not a new idea in this project — `landcover-implementation-brief.md:1-8`
already is one, for four documents, and says "read them in this order and do not
re-derive them". §3.5 lifts it rather than losing it.

---

## 5. The five open questions, answered

### Q1 — Flat with an index, or subdirectories?

**Flat with an index, plus `docs/archive/` for zero-inbound documents only.**
Measured cost of the alternative: 104 inbound occurrences in 42 files, including
`ios/project.yml`, all eight `pipeline/` modules and four test modules. Measured
cost of the recommendation: **three one-line link edits** (from `reroute-audit.md`,
`new-england-terrain-findings.md` and `voice-guidance-plan.md`, each pointing at
the one archived document it references) plus one new file.

### Q2 — Should brief/answer pairs be merged?

**No.** Four reasons, in order of weight.

1. **It breaks the section-number citations.** `ios/project.yml`,
   `VoiceGuide.swift`, `VoiceCatalogue.swift`, two test files, `graph.py` and
   `router.py` cite `§1`, `§2`, `§5`, `§10`, `§13`. Merging renumbers them, and
   nothing fails — the pointers just quietly aim at the wrong section.
2. **It destroys the record the project runs on.** The standing practice is to
   attack plan documents rather than implement them, and that practice is built
   on which briefs turned out wrong. `byway-relations-brief.md` records that
   three of its own inferences failed. `new-england-expansion.md` records two
   wrong predictions. `junction-timing-plan.md:3` keeps a superseded design
   explicitly "because the wrong version is instructive". Merging a question
   into its answer edits the question to match — which is exactly the evidence
   you need to keep.
3. **It is six document rewrites against six one-line edits.** A forward pointer
   at the top of each question document — `**Answered by [X]. Read that first;
   the state described below is as of <date>.**` — closes the whole hazard
   Trap 4 describes, at 1/100th of the cost.
4. **The pattern is already the codebase's own.** `reroute-audit.md` and
   `reroute-step-offset.md` are briefs with their findings appended below,
   under duplicated `## Finding N` headings. That is a merge, done twice, and
   it reads worse than the separated pairs do.

### Q3 — The two status-less documents

Neither is actually status-less; both declare an outcome, just not in the bold
line-3 slot. **The fix is positional, not editorial.**

- **`reroute-step-offset.md`** — "**Fixed 2026-08-25**" is in paragraph 2. It
  belongs on line 3, *and it must carry the open items*, because `## Still open`
  at `:203` lists two. Proposed:
  `**Status: fixed 2026-08-25, two items still open** — see [Still open](#still-open).`
- **`traffic-schedule-plan.md`** — leads with `## Verdict: do not build this —
  not on borrowed data` at line 3, which is louder than a status line and should
  stay. Add above it:
  `**Status: decided 2026-08-31 — not built, and deliberately so.**` The risk
  this guards is a reader skimming the filename, seeing "plan", and building it.

### Q4 — Does `docs/route-census/` belong in `docs/`?

**No — move it to `tools/route-census/`, next to the script that writes it.** It
is 6,267 lines of CSV and a JSON summary: the committed *output* of
`tools/route_census.py`, not documentation.

What that costs, checked rather than assumed: **one line of code and five
references in one document.** `tools/route_census.py:773` hardcodes
`p.add_argument("--out-dir", default="docs/route-census")`, and
`route-distribution-study.md` names the path at lines 30, 121, 566, 568 and 570.
Nothing else in the repo references it. This is the only move in the proposal
that touches source, and it is one default string.

Worth doing because the alternative is worse as the corpus grows: every future
study that commits its output lands more data in `docs/`, and there is currently
no rule saying it shouldn't.

### Q5 — Is there a convention worth writing down?

**Yes, and it is the most valuable thing in this proposal.** `docs/` gained 29
documents between 2026-08-15 and 2026-08-31 — seven on one day — and 15 more are
on unmerged branches now. Whatever is tidied today is re-untidied inside a
fortnight without a rule. Five rules, each one a description of what the corpus
already does well, so adoption costs nothing:

1. **Line 3 is a bold status line, always, and it states the tree — not the
   work.** `**Status: built 2026-08-30.**` is not enough on its own; four of
   them have gone stale because they recorded a moment. Name the file or
   constant that proves it, as `unpaved-and-urban-brief.md` did — that is what
   made its staleness detectable.
2. **A question document gets a forward pointer the day its answer lands.** One
   line, at the top. This is the rule that would have saved the day the brief's
   Trap 4 describes.
3. **A document that corrects another edits the corrected one's header.** Two
   corrections exist today — `new-england-terrain-findings.md:199` against the
   rollout doc, `unpaved-and-urban-verdict.md:289` against the preferences study
   — and neither target says so. The correction is worthless where nobody
   reading the error will find it.
4. **Open items graduate to `roadmap.md` before the document is archived.** §2.4
   is what happens otherwise.
5. **`question-brief.md` / `question-verdict.md` or `-findings.md`, and never
   the same stem for both.** The corpus already does this five times out of six.
   Committed data goes to `tools/`, not `docs/`.

Worth adding to `docs/README.md` as a short "adding a document" section, not as
a separate file — a convention in its own document is a document nobody reads.

---

## 6. What I could not settle, and what the owner has to decide

Three, stated plainly rather than guessed.

1. **`licensing-and-attribution-brief.md` is a three-way collision.** Its
   "nothing changed" is still literally true — no attribution string exists in
   `ios/Sources/` or `server/`, and the repo has no `LICENSE` file at all, which
   matters more than the doc question given the repo is public. But
   `claude/data-attribution` rewrites it (+350) and `claude/licensing-open-questions`
   adds 857 lines beside it. **Decision needed: which of the three is the
   document of record?** Nothing else can be sequenced around it until that is
   answered.

2. **`hosting-options-brief.md` is edited in two directions at once.**
   `claude/code-review-max-317af8` rewrites the brief; `claude/admiring-torvalds-64b1d0`
   adds the 1,028-line answer and already conflicts with `main`. **Decision
   needed: which lands first.** Merging them in the wrong order either strands
   the answer or reverts the rewrite.

3. **`docs/scenery-grading-review-brief.md` is added by two branches.**
   `claude/funny-elbakyan-93c75f` (with its 1,094-line verdict) and
   `claude/scenery-grading-brainstorm-30d14e` (alone). They will conflict with
   each other. **Decision needed: is the brainstorm branch superseded?** If it
   is, deleting the branch is cheaper than resolving the conflict.

Two things I deliberately did **not** conclude. I did not propose deleting any
document outright — archiving keeps everything in git and in the tree, costs
nothing extra, and this corpus has already paid once for a document that looked
spent and was not. And I did not re-triage the four unverified defects in
`consumer-polish-brief.md`; I verified four of the eight are fixed and stopped
there, because the remaining four need the app run, not grep.

---

## 7. The application plan, cheapest and most reversible first

Steps 1–4 are safe **today** — they add lines and change no paths, so they
cannot conflict with the nine unmerged branches beyond ordinary text merges.
Steps 5 onward must wait for those branches to land.

| # | step | cost | reversible? | blocked by |
| ---: | --- | --- | --- | --- |
| 1 | **Correct the four stale status lines** (§2.3) — `voice-guidance-plan.md`, `consumer-polish-brief.md`, `unpaved-and-urban-brief.md`, `new-england-rollout.md` §0a | 4 edits, ~8 lines | trivially | nothing |
| 2 | **Harvest open items into `roadmap.md`** — the arrival gate (`NavigationModel.swift:849-857`), `RELIEF_FULL` north of MA, the two reroute items | 1 edit, ~4 lines | trivially | `github-description-trim` landing (or stage it on that branch) |
| 3 | **Add the two missing status lines** (Q3) and the four forward pointers (§3.4) | 6 edits, 6 lines | trivially | nothing |
| 4 | **Add the two correction pointers** — `driver-preferences-study.md` → the verdict that overturned its cost claim; `new-england-rollout.md` → `new-england-terrain-findings.md:199` | 2 edits, 2 lines | trivially | nothing |
| 5 | **Land the four doc branches**, resolving the three collisions in §6 | — | — | owner decisions |
| 6 | **Write `docs/README.md`**, lifting the reading order from `landcover-implementation-brief.md:1-8`, with one annotated line per document | 1 new file | trivially | step 5 |
| 7 | **Create `docs/archive/` and move the six of §3.5**, updating three inbound links | 6 moves, 3 edits | `git mv` back | steps 1–6 |
| 8 | **Move `route-census/` to `tools/`**, updating `route_census.py:773` and five references in `route-distribution-study.md` | 1 move, 6 edits | `git mv` back | step 7 |
| 9 | **Add the convention** (Q5) as a section of `docs/README.md` | ~15 lines | trivially | step 6 |

Steps 1–4 are **20 lines of edits across 12 files** and deliver most of the
value: after them, no document misdescribes the tree, no question document
strands a reader on a stale answer, and no open defect is invisible. Steps 5–9
are the tidying, and they are genuinely optional — worth doing, not worth
blocking on.

**The sanity check before and after any move**, from the brief:

```sh
for f in docs/*.md; do b=$(basename "$f"); \
  printf "%-44s %5s %2s %2s %2s\n" "$b" "$(wc -l < "$f")" \
  "$(grep -c "$b" README.md)" \
  "$(grep -rl "$b" pipeline server ios tools tests | wc -l)" \
  "$(grep -l "$b" docs/*.md | grep -v "docs/$b$" | wc -l)"; done
```

A document whose count falls after a move has a link that was not updated.

---

## 8. Reproducing this

Every claim above came from the working tree at `378aaee` plus the nine unmerged
branches. The commands, in the order they were run:

```sh
git branch --no-merged main                       # nine, not six
for b in $(git branch --format='%(refname:short)'); do        # real per-branch work
  git diff --stat "$(git merge-base main $b)..$b" -- docs README.md; done
git show claude/github-description-trim-9bce8b:README.md      # the baseline (Trap 2)

grep -rn 'docs/[a-z-]*\.md' pipeline server ios tools tests   # the 22 source citations
grep -rl -E 'docs/[a-z0-9-]+\.md' README.md docs/*.md pipeline server ios tools tests | wc -l
```

Claims were tested with their context, never as bare tokens (Trap 3): the
"restated in code" findings in §1 were checked by reading the cited comment
block — `RouteModel.swift:279-300`, `elevation.py:50-58`,
`RoutePanel.swift:24-51` — not by grepping for the digits.

**What was not verified.** Four of the eight `consumer-polish-brief.md` defects
(#3 sheet height, #4 pin placement, #5 verdict-button contrast, #6 the stranded
continuation) — these are visual or concurrency defects that need the app run on
a simulator, and I read code only. #5's code has moved regardless: the lines the
brief cites, `NavView.swift:287-296`, are now the `currentRoadLabel` added by the
`current-street-display.md` work.
