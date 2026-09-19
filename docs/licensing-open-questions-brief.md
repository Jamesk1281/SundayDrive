# Licensing and copyright: the three questions the IP audit did not answer

**Status: researched 2026-09-19, nothing changed.** No file under `ios/`,
`server/`, `pipeline/` or `tests/` was touched, and this task must not touch one
either — see Trap 2. This brief is *not* the legal audit. The audit exists, it is
good, and it is 369 lines long:

```sh
git show claude/data-attribution:docs/legal-and-ip-audit.md
```

**Read that first. Do not re-derive it.** It registers ten items against primary
sources — the Apple Developer Program License Agreement, ODbL 1.0, CC BY 4.0, the
US Copyright Office, the App Store Connect gates — and it is right about every
claim I re-checked today (verifications listed below). This brief covers only the
**residue**: what that audit scoped itself out of, what it self-flagged as
unverified, and one thing that became true after it was written.

**I am not a lawyer and neither is the session picking this up. The output is a
documented set of options with their consequences, not legal advice, and not a
decision.** The repo's own precedent for this shape is
`docs/hosting-options-findings.md`: research, recommend, hand the choice back.

---

## What is already answered, so nobody spends a budget re-answering it

From `docs/legal-and-ip-audit.md`, re-verified against `main` at `378aaee` today:

| audit claim | re-checked 2026-09-19 | verdict |
| --- | --- | --- |
| No third-party code ships in the app | `ios/project.yml` declares no SPM/CocoaPods/Carthage; no `Package.swift`, no `.xcworkspace` | **holds** — but see Trap 3 |
| `MKDirections` is never called | `git grep MKDirections main -- ios/` → **zero hits** | **holds** |
| `DriveTrace` persists geocoder coordinates | `DriveTrace.swift:121` `"dest"`, `:126` `header["from"]`, `:226-227` `req_lat`/`req_lon` — all still at those exact lines | **holds** |
| No EULA anywhere | `git grep -riI 'end-user licen|EULA|terms of use'` over `main` → one hit, in an unrelated planning doc | **holds** |
| `PrivacyInfo.xcprivacy` missing, now required | absent from `main`; `UserDefaults` is live on `main` at `VoiceCatalogue.swift:118,119,148,149` and `VoiceGuide.swift:351,352` | **holds, and has escalated** — the older note called this a *voice-branch* problem; voice merged in `0b1f240` on 2026-08-30, so the requirement is live on `main` today |
| Traces are a record of where someone drove | `.gitignore` excludes `traces/` and `*.ndjson`, with a comment saying exactly why; **zero** `.ndjson` committed | **holds** — this one is already done right |

Six of the audit's claims, independently reproduced. Its measurements are
reliable. Attack its *inferences* if you attack anything — that is where this
repo's briefs have historically been wrong, and the audit's inferences about
Apple's agreement all rest on the second-hand text in Gap 2 below.

---

## Gap 1 — the repository is public and carries no licence

**This is new since the audit, and it is the largest open item.**

Measured today:

```
curl -s -o /dev/null -w '%{http_code}' https://github.com/Jamesk1281/Scenic   →  200   (anonymous, no auth)
git ls-tree -r main --name-only | grep -iE '^(LICENSE|COPYING|NOTICE)'        →  (nothing)
```

The repo is readable by anyone and contains no licence file of any kind. Under
the Berne Convention and US copyright law the default for a published work with
no licence grant is **all rights reserved**: readers may view it, and GitHub's
Terms of Service §D.5 grant forking *within GitHub*, but nobody acquires any
right to copy, modify, or redistribute it outside that.

That default may be exactly what the owner wants, or exactly wrong. Right now it
has not been chosen — it has been inherited by not acting. **The audit never
covers this, because the audit scoped itself to the artifact that ships to end
users, and the repo is not that artifact.**

Four questions sit under it, and none is answered anywhere in the repo:

1. **What is the intent?** "Readable so people can see the work" and "reusable by
   others" are different goals with different licences. Source-available /
   all-rights-reserved satisfies the first. MIT or Apache-2.0 satisfies both.
   Apache-2.0 additionally carries an express patent grant and a
   trademark-reservation clause, which interacts with the naming problem in the
   audit's item 1.
2. **Does ODbL 1.0 reach the code?** *Hypothesis, flagged as one:* it does not.
   ODbL's copyleft attaches to the Database and to Derivative Databases, and its
   attribution duty to Produced Works. `pipeline/*.py` is independently authored
   software that *processes* OSM; it is not a database and not a produced work.
   **What would kill this hypothesis:** any committed artifact that is itself
   substantially derived from OSM content. Check for one — the `data/` tree is
   gitignored, but check the whole tree, including fixtures under `tests/` and
   anything embedded in a doc. If such an artifact is committed, the ODbL
   share-alike question is live and the answer changes.
3. **Do the fitted constants carry anything?** `score.py`'s `WEIGHTS`,
   `router.py`'s `SPEED_KMH` / `SPEED_FACTOR` / `CONTROL_SECONDS` were *fitted to*
   OSM-derived data. Facts and measurements are not copyrightable subject matter
   in the US (*Feist*), and a handful of fitted scalars is not a database. State
   the reasoning and move on — this is a two-paragraph answer, not a project.
4. **Does a licence choice constrain a later App Store release?** Publishing the
   source under a permissive licence and shipping a paid binary are compatible
   (many apps do both), but it is worth one explicit sentence rather than an
   assumption.

**Recommend one, with the consequences of each. Do not choose.**

## Gap 2 — the Apple agreement is quoted from a five-year-old third-party filing

The audit is transparent about this and says so in its own words:

> **Verify exact wording against the current PDF before relying on it** — the
> clause *numbering* (Attachment 6, §2.1–2.7, §3.3.15) is stable across both, but
> the text I quote is from the 2020/21 execution.

Its source is the executed ADPLA filed with the SEC as
[Glu Mobile exhibit 10.23a](https://www.sec.gov/Archives/edgar/data/1366246/000155837021002009/gluu-20201231xex10d23a.htm),
cross-checked for numbering against Apple's
[Program agreements page](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/).

**Four of the ten register items rest entirely on that second-hand text**: §2.1
(the obscured Apple logo — a confirmed breach), §2.3 (never benchmark against
Apple's routes — a standing rule in two memory files and in `README`-adjacent
practice), §2.5 (stored coordinates), and §3.3.15 (the missing EULA notice).

§3.3.15 is the one that actually bites, because the obligation is to reproduce a
**verbatim string with fixed capitalisation**:

> YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK.
> LOCATION DATA MAY NOT BE ACCURATE.

If the current agreement words that differently, the string the app eventually
ships is the wrong string, and the item that the audit calls "the cheapest item
on the list with the clearest text" silently fails to discharge the clause.

**What to do:** retrieve the *current* ADPLA, confirm or correct the four quoted
clauses, and say plainly which ones you could not retrieve. Apple's terms pages
are sometimes served as PDFs that refuse automated fetches — if that happens,
**report it as unretrieved rather than falling back to the 2021 text and calling
it current.** An honest "could not be verified from this machine, here is the
2021 text and here is what changed in the numbering" is a complete answer.

## Gap 3 — what the public repo puts on display

Minor, and mostly benign, but nobody has looked since it went public. Measured:

- `api.jameskouvlis.com` appears **8 times across 5 files** — `ios/project.yml:63`,
  `server/DEPLOY.md:9,366,367`, `server/start-windows.bat:23`,
  `docs/hosting-options-brief.md:18,191`, `docs/consumer-polish-brief.md:33`.
  This is the owner's own domain and `DEPLOY.md:366` deliberately proposes a
  public demo on it, so it is published on purpose. Worth one line on whether a
  home-hosted origin behind a tunnel should be advertised by hostname in a public
  repo, and nothing more.
- `DEVELOPMENT_TEAM` / `28ZU5P5GC3` in 2 files. A Team ID is not a credential and
  appears in every app's receipt; confirm that and move on.
- **No traces committed, and `.gitignore` says why.** Correct already.
- No API keys, tokens or passwords found. Confirm independently rather than
  taking this line's word for it.

---

## Traps

**1. Do not re-derive the audit.** It is 369 lines against primary sources and
six of its claims reproduced exactly today. A session that starts from a blank
page will spend its whole budget rebuilding it and never reach the three gaps.
Open it first: `git show claude/data-attribution:docs/legal-and-ip-audit.md`.
The same goes for `docs/branding-brainstorm.md` (the name) and
`docs/licensing-and-attribution-brief.md` (the geodata licences) on that branch —
both already done, neither needs redoing.

**2. The audit's own fixes cannot be implemented on `main`, and this task must
not try.** Its items 2, 6 and 7 all edit `ios/Sources/AboutView.swift` — the
"Data sources" sheet. **That file does not exist on `main`.** It exists only on
`claude/data-attribution`, which is unmerged and currently conflicts with `main`
on `README.md` and `docs/licensing-and-attribution-brief.md`. A session that
tries to "add the EULA notice to the Data sources sheet" will either find no such
file or create a second one that collides with the branch when it lands.
**This task is documentation-only: write one markdown file, touch nothing under
`ios/`, `server/`, `pipeline/` or `tests/`.** Landing the branch is separate
work, deliberately not dispatched with this.

**3. `ios/project.yml:97` has a `dependencies:` line and it is not a package.**
It reads `dependencies: [- target: Scenic]` — the *test* target depending on the
*app* target. I tripped on this myself today before reading the context. The
audit's "no third-party code ships" conclusion is correct; do not "fix" it.

**4. Do not choose the licence.** Gap 1 ends in a decision the owner makes.
Lay out the options with their consequences and recommend one, the way
`docs/hosting-options-findings.md` does. A session that commits a `LICENSE` file
has made a permanent, publicly-recorded choice on someone else's behalf — and
un-licensing a public repo is not possible for copies already taken.

**5. This document will itself be public.** It is going into a repo that is
already readable by anyone. Write it as something a stranger reading the project
should see. Nothing about the owner beyond what the repo already publishes, and
no speculation about anyone's legal exposure phrased as fact.

**6. Report what you could not retrieve.** Several sources in this area block
automated fetches — `oracle.com` did during the hosting research, and Apple's
terms PDFs may. "Could not be verified from this machine" is an acceptable and
expected answer for any individual item. Guessing, or silently substituting an
older source for a current one, is the one failure mode that makes the whole
document untrustworthy.

---

## Done looks like

1. **One new doc**, `docs/licensing-open-questions.md` (note: *not* this
   filename — this is the question, that is the answer; keeping them distinct is
   deliberate, because this repo has previously overwritten an answer with its own
   question and lost the work).
2. **Gap 1 answered**: the licensing options for a public repo, each with its
   consequences, one recommended; the ODbL-reach hypothesis settled one way or the
   other with the check that settled it; the fitted-constants question answered in
   a short paragraph.
3. **Gap 2 answered**: the four ADPLA clauses confirmed against the current
   agreement, corrected if they have moved, **or** explicitly listed as
   unretrievable with the reason.
4. **Gap 3 answered**: a short section on what the public repo exposes, with an
   independent check for credentials rather than a restatement of this brief.
5. **The audit's register carried forward, not rebuilt** — a short table saying
   which of its ten items this pass confirmed, changed, or could not reach.
6. **An honest-answer escape hatch is available for every item**: "this cannot be
   determined without a lawyer" and "this could not be retrieved from this
   machine" are both complete answers, and are better than a confident one that is
   wrong. Say which items they apply to.
