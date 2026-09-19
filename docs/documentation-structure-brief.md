# Propose a structure for `docs/` — read everything, change nothing

**Status: measured 2026-09-19, nothing changed and nothing may be changed.**
No file was edited, moved or deleted, and **this task must not edit, move or
delete one either.** The deliverable is a single new document containing a
proposal. See Trap 1 — it is the reason this is scoped the way it is.

The owner's framing, in his words: *"read all docs and consider what is still
necessary. Old stuff that has been implemented for a while has no reason to be
here anymore... propose a more organized structure."* He is right about the
direction. This brief supplies the measurements, the one mechanical triage key
the corpus already carries, and the exception to his rule that a first pass will
otherwise miss.

---

## The goal, as measured

`docs/` on `main` at `378aaee`: **30 markdown files, 11,466 lines**, against
24,707 lines of Python and Swift. Plus 3.3 MB on disk, of which 2.0 MB is the
README's hero image (`scenic_heatmap.png`, load-bearing — it is the first thing
a visitor sees) and 0.7 MB is `docs/route-census/` (6,267 lines of committed CSV,
see Question 4).

**Only 4 of the 30 are linked from the README** — `junction-timing-plan.md`,
`unpaved-and-urban-verdict.md`, `geodata-sources-findings.md`,
`directions-accuracy.md`. **Five have zero inbound references** from the README,
from any source file, or from any other doc.

Inbound reference counts, measured (README / source tree / other docs):

| doc | lines | R | C | D |
| --- | ---: | ---: | ---: | ---: |
| `voice-guidance-plan.md` | 813 | 0 | 5 | 1 |
| `driver-preferences-study.md` | 804 | 0 | 0 | 3 |
| `geodata-sources-findings.md` | 761 | 1 | 2 | 5 |
| `loop-routes-design.md` | 662 | 0 | 4 | 1 |
| `reroute-audit.md` | 652 | 0 | 0 | 1 |
| `scenery-cap-options.md` | 602 | 0 | 2 | 3 |
| `route-distribution-study.md` | 571 | 0 | 4 | 1 |
| `junction-timing-plan.md` | 571 | 1 | 5 | 0 |
| `unpaved-and-urban-verdict.md` | 549 | 1 | 4 | 0 |
| `geodata-peer-review-verdict.md` | 538 | 0 | 1 | 4 |
| `new-england-rollout.md` | 440 | 0 | 0 | 8 |
| `new-england-expansion.md` | 393 | 0 | 0 | 2 |
| `consumer-polish-brief.md` | 358 | 0 | 0 | 2 |
| `traffic-schedule-plan.md` | 326 | 0 | 0 | 2 |
| `byway-relations-brief.md` | 313 | 0 | 1 | 1 |
| `new-england-terrain-findings.md` | 277 | 0 | 0 | 0 |
| `current-street-display.md` | 268 | 0 | 0 | 0 |
| `landcover-implementation-brief.md` | 256 | 0 | 0 | 0 |
| `beautiful-miles-and-the-slider-brief.md` | 239 | 0 | 0 | 0 |
| `reroute-step-offset.md` | 231 | 0 | 0 | 1 |
| `voice-guidance-plan-brief.md` | 220 | 0 | 0 | 1 |
| `licensing-and-attribution-brief.md` | 212 | 0 | 0 | 1 |
| `geodata-sources-review.md` | 206 | 0 | 0 | 3 |
| `hosting-options-brief.md` | 195 | 0 | 0 | 1 |
| `geodata-peer-review-brief.md` | 176 | 0 | 0 | 1 |
| `unpaved-and-urban-brief.md` | 175 | 0 | 0 | 2 |
| `directions-accuracy.md` | 162 | 1 | 0 | 0 |
| `stale-plan-after-arrival.md` | 145 | 0 | 0 | 1 |
| `new-england-terrain-brief.md` | 134 | 0 | 0 | 1 |

(`licensing-open-questions-brief.md`, 217 lines, is new today and has a task
already in flight against it — leave it alone.)

Reproduce the table with:

```sh
for f in docs/*.md; do b=$(basename "$f"); \
  printf "%-44s %5s %2s %2s %2s\n" "$b" "$(wc -l < "$f")" \
  "$(grep -c "$b" README.md)" \
  "$(grep -rl "$b" pipeline server ios tools tests | wc -l)" \
  "$(grep -l "$b" docs/*.md | grep -v "docs/$b$" | wc -l)"; done
```

## The mechanism: the corpus already carries its own triage key

**Nearly every document opens with a bold self-declared status line**, and this
is the single most useful fact about the corpus. Measured:

```
docs/landcover-implementation-brief.md:3:**Status: implemented 2026-08-29.**
docs/voice-guidance-plan-brief.md:3:    **Status: built 2026-08-30.**
docs/stale-plan-after-arrival.md:3:     **Status: fixed** — `endNavigation()` in ...
docs/consumer-polish-brief.md:3:        **Status: diagnosed 2026-08-29, nothing changed.**
docs/hosting-options-brief.md:3:        **Status: requirements measured 2026-08-31, nothing changed.**
```

So the corpus is not rotting — it is a well-labelled archive with no index on the
front of it. Seven documents (~1,575 lines) declare their own answer has shipped:
`beautiful-miles-and-the-slider-brief` (239), `byway-relations-brief` (313),
`landcover-implementation-brief` (256), `new-england-terrain-brief` (134),
`voice-guidance-plan-brief` (220), `current-street-display` (268),
`stale-plan-after-arrival` (145).

**Two carry no status line at all** and need one either way:
`reroute-step-offset.md` (231) and `traffic-schedule-plan.md` (326).

**Six topics exist as a question document plus an answer document.** Four pairs
are both on `main`; two have the answer on an unmerged branch:

| question | answer | where |
| --- | --- | --- |
| `unpaved-and-urban-brief` 175 | `unpaved-and-urban-verdict` 549 | both on main |
| `geodata-peer-review-brief` 176 | `geodata-peer-review-verdict` 538 | both on main |
| `new-england-terrain-brief` 134 | `new-england-terrain-findings` 277 | both on main |
| `geodata-sources-review` 206 | `geodata-sources-findings` 761 | both on main |
| `hosting-options-brief` 195 | `hosting-options-findings` 1028 | answer on `claude/admiring-torvalds-64b1d0` |
| `scenery-grading-review-brief` 406 | `scenery-grading-verdict` 1085 | **both** on `claude/funny-elbakyan-93c75f` |

## Why it matters, and the exception to "implemented means deletable"

The owner's rule — implemented work does not need its planning document — is
right in the main. But it has a systematic exception, and the proposal has to
handle it explicitly rather than by instinct.

**An implemented brief's *plan* is dead. Three things inside one may not be:**

1. **The rejected alternative, and the measurement that rejected it.**
   `landcover-implementation-brief.md:111` says *"It must be continuous, not a
   flag"* and carries the threshold table that proves it (≥10% tree → 3.21×,
   ≥25% → 3.47×, ≥50% → 4.11×, ≥75% → 5.11×, continuous → 3.93×). The code
   records only the conclusion — `pipeline/landcover.py:287` mentions "a flag
   rather than a signal" in a comment with no numbers. Delete the evidence and
   the next person re-proposes the flag.
2. **Hub sections.** That same file's first eight lines are a *reading order* for
   four other documents ("read them in this order and do not re-derive them").
   It is the closest thing `docs/` currently has to an index. Its content is
   redundant; its navigation is not.
3. **Falsified predictions.** The project's standing practice is to attack plan
   documents rather than implement them, and that practice is built entirely on
   the record of which briefs turned out wrong. That record lives only in the
   briefs.

**The rule to propose instead**, and to apply per-claim rather than per-file: an
implemented document is deletable when its content is either (a) restated in the
code and its tests, or (b) superseded by a later document. **Shipping is not by
itself sufficient.** Verified on the hardest case: the landcover brief's
threshold numbers *do* survive in `geodata-sources-findings.md` and
`geodata-peer-review-verdict.md`, so that one really is redundant on content —
which is evidence for the owner's rule, arrived at by a test that could have
falsified it.

---

## Traps

**1. Propose. Do not change anything.** No deletions, no moves, no renames, no
edits to existing docs, no `git mv`. This is not caution for its own sake:
**`docs/` is the most contended directory in the repo right now.** Six separate
pieces of work are in flight in it —

- `claude/github-description-trim-9bce8b` — rewrites `README.md` 513 → 113 lines
  and adds 5 docs (`roadmap`, `measuring-travel-times`, `measuring-scenery`,
  `scoring`, `extending`). Merges clean today.
- `claude/funny-elbakyan-93c75f` — adds 2 docs, 1,491 lines.
- `claude/code-review-max-317af8` — rewrites `hosting-options-brief.md` and
  `new-england-rollout.md`.
- `claude/admiring-torvalds-64b1d0` — adds `hosting-options-findings.md`;
  **already conflicts** with main.
- `claude/data-attribution` — adds `legal-and-ip-audit.md` and
  `branding-brainstorm.md`; **already conflicts** with main.
- A task in flight writing `docs/licensing-open-questions.md`.

Any restructure applied to `main` today would collide with four unmerged branches
and strand two that already conflict. The proposal must therefore be a *plan a
human can apply after those land*, not a change.

**2. Assume the README restructure as the baseline, and do not redo it.**
`claude/github-description-trim-9bce8b` already cuts the README to 113 lines and
ends it with a six-item index into five new topic docs. It is good and it merges
clean. **Read it before proposing anything about the README:**
`git show claude/github-description-trim-9bce8b:README.md`. A proposal that
re-derives a README trim has wasted its budget. Propose how `docs/` should be
organised *given* that branch lands — including what its five new docs make
redundant, which is a real question nobody has asked yet.

**3. A grep for a bare number is not a uniqueness test.** Checking whether a
measurement survives elsewhere by grepping the digits produces nonsense: `"3.3"`
matches 27 files including `pipeline/graph.py` and two CSVs; `"3.21"` matches
`docs/route-census/census-pairs.csv` as coincidental digits inside a coordinate.
Test a *claim* — the sentence and its surrounding context — not a token. Where
uniqueness matters, quote the claim and name the file that restates it.

**4. Do not propose deleting a document whose answer is on an unmerged branch.**
`hosting-options-brief.md` and the scenery-grading pair look like dead questions
from `main`'s working tree and are not: their answers exist but have not landed.
This exact failure has already cost this project a day — a 170-line question sat
on disk under the same filename as its 602-line answer, and a session read the
question and re-did the work. **Check `git branch --no-merged main` before
calling any document spent.**

**5. Do not propose deleting the heatmap.** `docs/scenic_heatmap.png` is 2.0 MB
and 61% of the directory's bytes, and it is the README's hero image. The comment
next to it in the README explains that `out/` is gitignored, so pointing there
would render broken on GitHub.

**6. The repo is public.** `github.com/Jamesk1281/Scenic` answers HTTP 200
anonymously. Anything proposed — and this proposal itself — is readable by
anyone. Structure for a stranger arriving at the repository, not for someone who
already knows the project.

---

## Open questions the proposal should answer

1. **What is the top-level shape?** Flat with an index, or subdirectories
   (`docs/how-it-works/`, `docs/studies/`, `docs/archive/`)? Subdirectories break
   every existing inbound link — the table above says how many that is per file.
2. **Should brief/answer pairs be merged into one document each?** Six pairs,
   ~2,100 lines of question against ~4,200 of answer. Merging keeps every fact
   and would take 30 files to 24.
3. **What happens to the two status-less docs** (`reroute-step-offset.md`,
   `traffic-schedule-plan.md`)? At minimum they need a status line; decide which.
4. **Does `docs/route-census/` belong in `docs/` at all?** 6,267 lines of CSV and
   a JSON summary — the committed output of `tools/route_census.py`, 0.7 MB. It
   is data, not documentation. Check what references it before proposing a move.
5. **Is there a convention worth writing down** so the next fifteen documents
   arrive already organised — a required status line, a naming rule for
   question-vs-answer, a stated home for studies?

## Done looks like

1. **One new document**, `docs/documentation-structure-proposal.md` — note this
   is deliberately *not* the filename of this brief. Keeping question and answer
   under distinct names is a rule this project learned the hard way (Trap 4).
2. **Every one of the 30 documents accounted for individually**, with a proposed
   disposition — keep / merge into X / archive / delete — and a one-line reason
   citing its status line, its inbound references, or the document that
   supersedes it.
3. **A proposed structure**, with the answers to the five open questions above,
   and an explicit statement of what breaks (how many inbound links, in which
   files) if it involves moving anything.
4. **A ranked, sequenced application plan** a human can follow after the four
   unmerged doc branches land — cheapest and most reversible first.
5. **The exception applied, not just acknowledged**: for every document proposed
   for deletion, a line saying which measurements it uniquely holds and where
   they survive — or that it holds none.
6. **An honest-answer escape hatch.** "This document could not be triaged without
   a decision from the owner" is a legitimate disposition — say which ones, and
   what the decision is. So is "the corpus is in better shape than it looks and
   the right change is small"; if reading all 11,466 lines supports that, say so
   rather than manufacturing a reorganisation to justify the task.
