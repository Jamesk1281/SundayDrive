# The Sunday Drive rename, audited across the whole tree

**Status: audited and fixed 2026-09-21, against `claude/rename-to-sunday-drive`
at `c75ce1d` with `main` merged in — the audited tree is `5aff398`.** Answers
[`sunday-drive-rename-audit-brief.md`](briefs.md).
Every `git show` in this document is pinned to a SHA, never to `main`, because
`main` moves several times an hour on this repo.

**The rename is sound.** 3,843 occurrences of the three names were counted in
code and classified; **18 were defects, on 16 lines in 5 documents, and all 18
are fixed here.** No defect was found in any compiled or executed file — not one
Swift file, Python module, `project.yml`, Dockerfile or deploy script. The
2026-09-21 rename reached everything that runs.

What a passing suite could not see was documents, and that is where all eighteen
were. **Two of the five files are outside the brief's list** — `release-plan.md`
(§3.5) and `voice-status-refresh-brief.md` (§3.6), both operational, both missed
by *both* renames. Four of the brief's own factual claims did not survive
re-checking — §7.

---

## 1. The census

Counted by script, not by eye: every tracked file read as bytes, scanned with
one regex alternation, longest-match-first, so each occurrence is counted
**exactly once** and lands in exactly one name family. 175 tracked files, 0
unreadable, 138 with at least one hit.

| class | occurrences |
| --- | --- |
| **domain vocabulary** | 2,975 |
| **historical record** | 656 |
| **brand identifier** | 194 |
| **defect** | **18** |
| **total** | **3,843** |

Zero occurrences were left unclassified; that is asserted by the classifier
itself, which prints any residue.

By family:

| family | total | brand id | vocabulary | historical | defect |
| --- | --- | --- | --- | --- | --- |
| `scenic` (any case, incl. compounds) | 3,278 | 1 | 2,975 | 298 | 4 |
| `Sunday Drive` / `SundayDrive` | 183 | 93 | — | 90 | — |
| `Victory Lap` / `VictoryLap` | 165 | 2 | — | 155 | 8 |
| `SCENIC_*` | 81 | 20 | — | 61 | — |
| `SUNDAYDRIVE_*` | 44 | 42 | — | 2 | — |
| `VICTORYLAP_*` | 22 | 20 | — | 1 | 1 |
| `app.*` bundle ids | 55 | 16 | — | 35 | 4 |
| lone `Sunday` / `Victory` | 15 | — | — | 14 | 1 |

**`scenic` appears in the defect column**, which looks wrong and is not: four of
the eighteen are `Scenic.xcodeproj`, `-scheme Scenic` and `ScenicTests/…` in a
runnable command (§3.6). Capitalisation is not the discriminator in either
direction.

### What "domain vocabulary" is, and why it is 77% of the tree

- **1,966** are in `docs/route-census/census-routes.csv`, where `scenic` is an
  arm-name **column value** in published ODbL data. Never touchable.
- The rest is correct English and the API wire contract: *scenic route*,
  *scenic score*, *scenic km*, *scenic arm*, *scenic byway*, plus OSM tag values
  (`US:MA:Scenic`, `US:NY:Scenic` in `pipeline/extract.py:108-111`) and a road
  name in a test fixture (`RerouteTests.swift:522`, "Continue on Scenic Road").
- **Capital `Scenic` is not a reliable brand marker**, which is the trap
  `release-plan.md:194-209` warned about. All 319 bare capitalised `Scenic`
  occurrences were read: in code they are the **routing arm's UI label** —
  nine quoted `"Scenic"` strings in `RouteResults.swift` alone, the comparison
  card at `:18` (`card("Scenic", …)`) and six user-visible sentences at
  `:186-214` (*"Scenic adds **49 min**"*) — or sentence-initial prose, or the
  `~/Scenic` / `C:\Scenic` deployment paths and the GitHub URL, all deliberate.

### The `drive` denominator, which is why nothing was replaced mechanically

The new name collides with the codebase's own vocabulary. A single pass counted
**2,356** occurrences of `drive`/`driving`/`driven`/`Drive*` as domain words —
`DriveTrace`, `DriveReplay`, `DriveReplayTests`, `LiveDriveTests`,
`DriveTraceTests`, `_driving_minutes`, and "a drive" meaning a recorded journey
throughout. Every one of the 3,843 name hits was read in context and decided
individually. Nothing in this branch was produced by a find-and-replace.

### Reproducing it

The three scripts are in the session scratchpad, not committed — they are
throwaway instruments, and the numbers above are the deliverable. To re-derive
the headline figures from the shell:

```bash
git grep -oih scenic -- docs/route-census/ | wc -l   # 1966
git grep -c VICTORYLAP_ -- '*.py' '*.swift'          # the legacy env layer, by file
```

---

## 2. Brand identifiers: the 194, all correct

These are the occurrences that genuinely name the product. Each was checked.

**Current and right (141):** `ios/project.yml` (14 — `name: SundayDrive`,
`CFBundleDisplayName: Sunday Drive`, `SundayDriveAPIBaseURL`, both bundle ids),
`SundayDriveApp.swift`, 19 × `@testable import SundayDrive` (every test file), the
`SUNDAYDRIVE_*` reads, the two dispatch-queue labels
(`DriveTrace.swift:408` `app.sundaydrive.drive-trace`, `VoiceGuide.swift:75`
`app.sundaydrive.audio-session`), the systemd unit and Docker tag
`sundaydrive-api`, `PrivacyInfo.xcprivacy`, `NOTICE`, and the `/health`
service id asserted by `tests/test_api.py:46`.

**Deliberately old (43):** the `VICTORYLAP_*` and `SCENIC_*` fallback layers in
code, and the three `ios/*.xcodeproj/` lines in `.gitignore`. Left exactly as
found — §5.

**The spike (10):** `spike/voice-audio/` keeps `app.scenic.spike.*` on its four
targets and in two measurement files. **Deliberately left.** It is a finished, separate measurement project;
its recorded results (`measurements/*.jsonl`) carry those bundle ids as *data*
in the `"bundle"` field, so renaming the targets would break the correspondence
between the spike and its own evidence. It shares no identifier with the app,
whose prefix is now `app.sundaydrive`, so there is no collision to resolve.

### Bundle identifiers, everywhere one appears

Verified at `5aff398` and in the generated project:

| where | value |
| --- | --- |
| `ios/project.yml:3` | `bundleIdPrefix: app.sundaydrive` |
| `ios/project.yml:66` | `PRODUCT_BUNDLE_IDENTIFIER: app.sundaydrive` |
| `ios/project.yml:101` | `PRODUCT_BUNDLE_IDENTIFIER: app.sundaydrive.tests` |
| `SundayDrive.xcodeproj/project.pbxproj` | `app.sundaydrive`, `app.sundaydrive.tests` — and nothing else |
| `docs/privacy-policy.md:5`, `:36` | `app.sundaydrive` — **fixed here** |
| `docs/app-store-submission.md` §6 | `app.sundaydrive` — **fixed here** |
| `server/Dockerfile`, `server/DEPLOY*.md`, `start-windows.bat` | no bundle id; tag and service id are `sundaydrive-api` |

The generated `Info.plist` was read rather than inferred:
`CFBundleDisplayName => "Sunday Drive"`,
`SundayDriveAPIBaseURL => "https://api.jameskouvlis.com"`.

---

## 3. The eighteen defects, and the fixes

### 3.1 `docs/privacy-policy.md` — the document that gets published

A privacy policy naming the wrong application is wrong the moment it is hosted,
and the policy URL is a hard submission gate. Six defective tokens on six lines
— the last two are one sentence.

| line | was | now |
| --- | --- | --- |
| `:5` | `PRODUCT_BUNDLE_IDENTIFIER: app.victorylap` | `app.sundaydrive`, with both renames dated |
| `:29` | *"Victory Lap plans and narrates driving routes…"* | *"Sunday Drive plans and narrates…"* |
| `:36` | `app.victorylap` | `app.sundaydrive` |
| `:76` | a quotation of a string that exists nowhere — §3.2 | the string `ios/project.yml:21` actually holds |
| `:237-238` | "Resolved 2026-09-20. The app is **Victory Lap**" | records both renames, points at `sunday-drive-naming.md` |

The citations themselves were re-verified, not assumed: `ios/project.yml:66` and
`:74` still are the bundle-identifier and marketing-version lines at `5aff398`,
and `:43-44` is still `UIBackgroundModes`. The rename moved values, not line
numbers.

### 3.2 The quoted string that no longer existed in any form

`docs/privacy-policy.md:76` quoted the location purpose string as *"Victory Lap
uses your location to follow your route, turn by turn, while you drive."*

`ios/project.yml:21` at `5aff398` reads:

    NSLocationWhenInUseUsageDescription: "Your location is used to follow the route, turn by turn, while you drive."

**Fixed by re-reading the source, not by substituting the name.** The app's name
was deliberately removed from that string on 2026-09-20, because iOS already
titles the alert *Allow "Sunday Drive" to use your location?*. A
name-substitution pass would have written *"Sunday Drive uses your location…"* —
a string that appears nowhere in the project and never has.

Confirmed a third way, at the only level that matters to a user: the **built**
`Generated/Info.plist` after `xcodegen generate` reads
`NSLocationWhenInUseUsageDescription => "Your location is used to follow the
route, turn by turn, while you drive."`

The fix adds a standing note at that line telling the next reader not to restore
a product name to it, and names both wrong forms, so the defect cannot recur by
good intentions.

### 3.3 `docs/app-store-submission.md` — the console checklist

| line | was | now |
| --- | --- | --- |
| `:255` | bundle identifier `app.victorylap` | `app.sundaydrive`, both renames dated |
| `:289` | "the app is **Victory Lap**" | **Sunday Drive**, citing `sunday-drive-naming.md` |
| `:308` | manifest "verified at the root of the built `VictoryLap.app`" | `SundayDrive.app` |
| `:315` | checklist row 8: "Name settled — **Blocked**, §7.1" | **Done** — §7.1 had said *Resolved* since 2026-09-20 |

`:315` is **not in the brief**. The checklist contradicted its own §7.1 for a
day: §7.1 read "Resolved 2026-09-20" while the row summarising it read
"Blocked". Row 8 is the line someone scanning the checklist reads.

Two measured facts were added to §7.1 while it was open, because the name field
is a console answer and this is the document that holds console answers:

- The App Store **`Name`** answer is `Sunday Drive` — **12 characters of 30**.
- The combined form does **not** carry over. `Victory Lap - The Scenic Route`
  was exactly 30 characters, which `victory-lap-naming.md` §6 records as its
  "Trap 6, resolved". **`Sunday Drive - The Scenic Route` is 31** — one over the
  limit. Anyone reusing that listing shape will be rejected by the field.

The subtitle *The scenic route, on purpose* is name-independent and stands.

### 3.4 `docs/interface-design-brief.md` — the live brief

This brief is commissioning `interface-redesign-from-nothing` right now.

| line | was | now |
| --- | --- | --- |
| `:52` | "**Victory Lap.** Subtitle, decided and final…" | **Sunday Drive**, with a dated parenthesis that the subtitle is unchanged |
| `:169` | 'The only place a user should read "Victory Lap"…' | "Sunday Drive", plus a note that the *instruction* survived the rename |
| `:287` | `VICTORYLAP_DATA=<main checkout>/data/processed-ne` | `SUNDAYDRIVE_DATA=…` |

`:287` is the **same defect class as the one the previous rename left in
`server/DEPLOY-oracle.md`**: a runnable command that still works, silently,
through a fallback layer the project elsewhere calls temporary. It would have
kept working until the layer is deleted at first release, and then stopped —
which is exactly the failure mode the three-layer chain exists to prevent
being silent.

`:30` was **not** changed. It cites `docs/victory-lap-naming.md` §6–§8 for the
listing copy, which is a real file and the right pointer; the only thing the
brief takes from it is the name-independent subtitle, and it says "do not mine
the rest".

### 3.5 `docs/release-plan.md` — not in the brief, and both renames missed it

**Status: current.** It is the document that sequences the release, and its
header's "Checkable facts this rests on" asserts, in the present tense:

> `ios/project.yml:66` still reads `PRODUCT_BUNDLE_IDENTIFIER: app.scenic.demo`

That was true when written on 2026-09-19 and is now two renames stale. §6b —
*The rename* — is the plan the rename was executed from, and it still describes
`ScenicApp.swift` and `ScenicAPIBaseURL` as things to change.

**Fixed with a forward-pointer blockquote at the top, and no body edit**, per
`docs/README.md` rule 2 and the brief's Trap 2. The body is the record of *how*
the rename was done by reading every hit, and its traps are still the traps;
rewriting its identifiers would destroy that record. The pointer states what the
identifiers are now, at a pinned SHA, and explicitly claims nothing about §6a or
§6c–§6f, which were not audited here.

This is the `server/DEPLOY-oracle.md` shape repeating: the file the breadth
check skips is a *currently-descriptive operational document that nobody edits
because it reads like history*.

### 3.6 `docs/voice-status-refresh-brief.md` — not in the brief, and stale since the *first* rename

Four occurrences on three lines, in a **runnable command**, and this is the file
that turns out to explain the 241 baseline (§6).

`:32-38` presents "the standing workaround" for a `LiveDriveTests` hang:

```sh
xcodebuild test -project Scenic.xcodeproj -scheme Scenic -destination 'id=<UDID>' \
  -skip-testing:ScenicTests/LiveDriveTests \
  -skip-testing:ScenicTests/VoiceCatalogueTests
```

Every identifier in it is wrong: there is no `Scenic.xcodeproj`, no scheme
`Scenic`, and no `ScenicTests`. It has been unrunnable since **2026-09-20**, one
rename before the one being audited.

**Why this one is fixed and its neighbours are not:** its deliverable,
`docs/voice-status.md`, **does not exist**, and it has no row in the
`docs/README.md` index. It is an **open brief**, not a record — someone will run
that block. The same file's Trap 1, which *describes* the then-in-flight rename
and its `ScenicApp.swift`, is left as written with a dated "spent" note in front
of it, because rewriting it would destroy the record and make the trap
incoherent. `:119`'s `SCENIC_DEMO` is left too: it still works, through the
third fallback layer, and it is describing a code path rather than instructing.

A second, larger correction was added there rather than silently: **the hang the
workaround exists for did not reproduce.** See §6.

---

## 4. The protected set is untouched — proved by diff, not by counting

The brief offered occurrence counts for the six historical records so they could
be diffed. **The counts do not reproduce**, so they cannot do that job:

| file | brief | matching lines, any spelling | occurrences, any spelling |
| --- | --- | --- | --- |
| `victory-lap-naming.md` | 58 | 59 | 65 |
| `trademark-knockout-findings.md` | 28 | 28 | 33 |
| `victory-lap-naming-brief.md` | 13 | 14 | 14 |
| `sunday-drive-naming.md` | 9 | 9 | 9 |
| `rename-to-victory-lap-brief.md` | 5 | 7 | 8 |
| `branding-brainstorm.md` | 2 | 3 | 4 |

Eight counting methods were tried (occurrences vs matching lines, case-sensitive
vs not, `Victory Lap` alone vs all three spellings including the hyphenated
filename form). The closest matches two of six exactly. No method reproduces all
six, and the brief does not state which it used.

**A count is the wrong instrument anyway** — it cannot distinguish "untouched"
from "edited and coincidentally the same count". `git diff` can:

```
$ git diff --stat 5aff398 -- <the six protected files> <both ui-redesign files>
(no output)
```

All six protected records, **and both `ui-redesign*.md` files a running task is
deleting**, are byte-identical to the audited base. Nothing in §5's protected
list was touched.

---

## 5. Deliberately left, and why

- **The three-layer env chain** (`SUNDAYDRIVE_*` → `VICTORYLAP_*` → `SCENIC_*`),
  untouched at every read site. Dropping a layer fails silently, with the server
  coming up on the default region and data directory and answering every request
  as though that were right.
  *Count correction:* the brief and `sunday-drive-naming.md:220` both say **ten**
  read sites. There are **eleven**, across ten files — `server/app.py` has two
  (`REGION` at `:83`, `DATA` at `:95`). The chain itself is complete; only the
  tally is off by one.
- **`Color.brand`** — named `.brand` rather than `.victoryLap` by the previous
  rename precisely so the next one would not have to touch it. It did not.
- **`Models.swift`'s `scenic` property** — decoded by property name with no
  `CodingKeys`, so renaming it would break every deployed client as a nil route
  at run time, not a compile error.
- **The six historical records**, the GitHub repo, the Cloudflare tunnel named
  `scenic`, the `~/Scenic` and `C:\Scenic` deployment paths, and the whole
  routing-arm vocabulary.
- **`docs/ui-redesign.md` and `docs/ui-redesign-brief.md`** — a running task
  deletes both. Editing them would buy a conflict over files that are about to
  disappear. Verified untouched above.
- **`docs/scenic-name-viability-brief.md`** (4 old-name hits). Left as written.
  It is a dated commissioning brief whose every "Victory Lap" correctly records
  the state on 2026-09-20, and its answer — the 860-line screen on
  `claude/scenic-name-viability-screen` — **is not on `main` yet**, so the
  forward pointer `docs/README.md` rule 2 wants belongs to whoever merges that
  branch. It is also absent from the `docs/README.md` index, which the same
  merge should fix.
- **The other Scenic-era briefs and findings** — `consumer-polish-brief.md:49`,
  `hosting-options-brief.md:331`, `hosting-options-findings.md:683`,
  `hosting-refresh-brief.md:97`, `hosting-status-2026-09.md:160`,
  `archive/*`, `release-plan-brief.md:38`/`:59` — keep `ScenicAPIBaseURL`,
  `app.scenic.demo` and `SCENIC_*` in dated records of what was true when they
  were written, per `docs/README.md`'s stated convention.
  The line that decided each case: **is the document currently descriptive, or a
  record?** Three tests, applied in order — does its own Status line claim the
  present tense; is its deliverable on `main`; would a reader following it today
  run something. `release-plan.md` failed the first (§3.5) and
  `voice-status-refresh-brief.md` failed all three (§3.6). Everything in the
  list above passed all three, and a brief pinned to a SHA whose answer has
  landed is a record whatever it says about identifiers.
- **`spike/voice-audio/`** — §2.

---

## 6. Build, and both suites

### One `.xcodeproj`, and the three-project trap is not currently live

`xcodegen generate` in this worktree produced **exactly one** project,
`ios/SundayDrive.xcodeproj`. No `Scenic.xcodeproj` or `VictoryLap.xcodeproj`
was left beside it.

All **29 checkouts** on this machine were inventoried — the main one plus 28
worktrees. **None has two `.xcodeproj` directories**, so the "Xcode opens the
wrong one" hazard does not exist anywhere today. Ten have a project at all: two
`SundayDrive.xcodeproj` (the rename's own worktree and this one), six
`Scenic.xcodeproj` and two `VictoryLap.xcodeproj`. Every one of the eight
old-named ones is the *correct* output of its own checkout's `project.yml` —
those branches were cut before the rename, so their project is not stale for
them. The main checkout has none.

**Nothing was deleted in another worktree.** These are gitignored build outputs
regenerable in one command, several belong to live sessions, and deleting a
project mid-build is a worse failure than the one it would prevent. The hazard
materialises only when such a checkout *pulls* the rename without regenerating —
so the standing instruction is the one already in `project.yml:67-72`: run
`xcodegen generate` after any pull, and delete the old project if a second one
appears.

### Backend: the env var is read, not merely present

The brief's skip-behaviour trick, run with all three layers explicitly unset:

```
$ env -u SUNDAYDRIVE_DATA -u VICTORYLAP_DATA -u SCENIC_DATA .venv/bin/python -m pytest tests/test_api.py -q
69 skipped in 0.86s
```

All 69 skip. The suite can only reach a graph through the variable, so a green
run proves `SUNDAYDRIVE_DATA` is genuinely read rather than shadowed by a
default.

Full suite, `SUNDAYDRIVE_DATA` pointed at the main checkout's `data/processed-ne`
(neither `data/` nor `.venv` exists in a worktree):

```
379 passed, 155 warnings in 371.14s (0:06:11)
```

**379 passed, 0 failed** — the baseline exactly. The 6m11s against the brief's
~4.5 min is concurrent load on this Mac, not a regression; the iOS suite was
building for part of it. The 155 warnings are pre-existing `FutureWarning`s from
pandas and pyproj, untouched by this branch.

### iOS: 249 passed, and why that is not 241

```
Executed 256 tests, with 7 tests skipped and 0 failures (0 unexpected)
```

**249 passed, 7 skipped, 0 failures**, `xcodebuild` exit 0, on a simulator
created for this run (`iPhone 17 Pro`, iOS 26.4 — this machine had **no**
simulator devices at all, so one had to be created; `-destination id=<UDID>` to
avoid colliding with a parallel session).

The documented baseline is 241, and the difference is worth having in writing:

| | |
| --- | --- |
| executed | 256 |
| `LiveDriveTests` skipped — nothing listening on 5057, confirmed by `lsof` and a refused `curl` | −7 |
| **passed, this run** | **249** |
| `VoiceCatalogueTests` | −8 |
| = the documented baseline | **241** |

**The brief's account of where 241 comes from is wrong.** It says
`LiveDriveTests` *and* `VoiceCatalogueTests` "skip without a server on
127.0.0.1:5057". Only `LiveDriveTests` does. `VoiceCatalogueTests` has no server
dependency at all — its single `XCTSkip` at `:25` fires when *the Samantha voice
is not installed on the runtime*. On iOS 26.4 Samantha is present, so all 8 ran,
in 2.8 seconds, and passed.

**Where 241 actually comes from** turned up later in the audit, in the file
§3.6 fixes. `voice-status-refresh-brief.md:32-38` records the "standing
workaround" as an explicit `-skip-testing` pair for *both* suites — so 241 is
`256 − 7 − 8` with `VoiceCatalogueTests` deliberately excluded on the command
line, not skipping itself. This run is strictly more coverage than the baseline
with nothing red. Nobody should "fix" a 249 back down to 241.

**The hang that workaround exists for did not occur, and is not fixed — it is
runtime-dependent.** Its cause is narrower than "the suite hangs", and worth
having right, because the suite that hangs is **not** the one that needs a
server:

- `VoiceCatalogueTests.swift:27` calls `VoiceCatalogue.duration(of: samantha)`,
  which renders real speech through `AVSpeechSynthesizer`. On 2026-09-01 the
  simulator's **voice-asset fetch** timed out and the whole run stopped —
  `nw_read_request_report … Operation timed out`, then nothing, for **13
  minutes, observed twice**. Nothing to do with port 5057.
- The guard at `:23-26` cannot prevent it. It skips when Samantha is not in
  `AVSpeechSynthesisVoice.speechVoices()`, and it has been there since
  `0b1f240`, 2026-08-30 — *before* the hang. The failing condition is Samantha
  **listed but not downloaded**, which that call cannot distinguish; the test's
  own comment at `:28-30` names it.
- On iOS 26.4 here the asset was present: all 8 ran in **2.843 s** and the
  1.0–2.5 s assertion band held. The device was created fresh for this run,
  which is mild evidence the asset ships inside the iOS 26.4 runtime image
  rather than being fetched on demand.

**So: unresolved, and recorded as such** in that brief — "re-measure before
reinstating", not "fixed". A machine whose runtime lacks the asset can still
stall. What can be said is narrower and still useful: on this runtime neither
skip was needed, `LiveDriveTests` skipped instantly (its 7 tests in 0.053 s,
connection refused rather than timed out), and the full suite ran clean.

One incidental confirmation the rename reached a string only a failing run
prints: the skip message is *"no **Sunday Drive** API at
http://127.0.0.1:5057"* (`LiveDriveTests.swift:39`).

`PrivacyManifestTests` (6) and `AttributionTests` (15) — the two suites that
catch a broken product rename, one asserting the manifest out of `Bundle.main`
and one pinning the route-guidance EULA character-for-character and asserting
there is exactly **one** copy — both passed. No second copy of that notice was
added.

---

## 7. Four claims in the brief that did not survive re-checking

Recorded because this project's documents are expected to be re-checkable, and
because three of the four are the kind of number that gets inherited.

1. **"1,967 in `docs/route-census/`"** is now **1,966**, by three independent
   methods. Traced, rather than guessed at: at `4cf43b8`, where
   `release-plan.md:186` measured it, `census-summary.json` held one occurrence
   — in the field `"processed_dir": "/Users/…/Scenic/data/processed-ne"`, the
   **repository directory name leaking into a JSON path**. That path was later
   replaced with the relative `"processed-ne"`, and the count fell by one. The
   claim was right when written; the one it lost was never a brand identifier in
   data.
2. **"The overlap with the redesign is exactly four files."** Four is right for
   the rename alone. This audit makes it **five** by fixing
   `docs/interface-design-brief.md`, which the redesign also edits — §8.
3. **"The redesign's new files carry no brand identifier at all."** Three of them
   do — §8. This is the check the brief says it ran specifically because the trap
   has bitten before.
4. **"`LiveDriveTests`/`VoiceCatalogueTests` skip without a server"** — §6. Only
   the first does, and it turns out the 241 baseline comes from an explicit
   `-skip-testing` pair recorded in `voice-status-refresh-brief.md:32-38`, not
   from either suite skipping itself.

And one gap rather than an error: §4's list of documents carrying the old name
is not exhaustive. `release-plan.md` (§3.5) and `voice-status-refresh-brief.md`
(§3.6) were both missed, and both are operational. The brief's own §4 heading
—  "Two operational documents still name the app Victory Lap" — was four.

Also off by one, in a document rather than the brief: the **ten** env read sites
are eleven (§5).

---

## 8. What a later merge of `interface-redesign-from-nothing` must resolve

Reported, not acted on. That branch was not edited, rebased or merged, and
neither was `claude/scenic-name-viability-screen`.

It is 4 commits ahead of `main` at `e86152c` and touches 33 files. Against this
branch:

**Will conflict, visibly — resolve to Sunday Drive:**

| file | the redesign's side |
| --- | --- |
| `ios/Sources/AboutView.swift:5` | `/// Victory Lap draws OpenStreetMap-derived road geometry…` |
| `ios/Sources/RouteModel.swift:128-132` | two-layer env chain: `VICTORYLAP_DEMO` → `SCENIC_DEMO`. This branch has the three-layer one. **Take the three-layer side** |
| `README.md`, `docs/README.md` | both sides edited; `docs/README.md` is a pure add/add append to the index table — **keep both rows, take no side** |

**Will merge clean, and must still be fixed — this is the dangerous set.** Three
files the redesign *adds* carry the old name, so there is no conflict to notice:

| file | line | what it says |
| --- | --- | --- |
| `tools/fake_api.py` | `:250` | `server_version = "VictoryLapFakeAPI/1"` — a brand identifier **in code**, the one class the rename was meant to catch |
| `docs/interface-design-mockups.html` | `:183` | `<h1>Victory Lap — the interface, drawn</h1>` — the title of the deliverable the owner opens |
| `docs/interface-design.md` | `:728` | prose, and **not a substitution** — see below |

`docs/interface-design.md` §10 argues *"for this particular name, the right
aesthetic call… 'Victory Lap' is a wry name — it is about the feeling at the end
of the drive, not the drive. …the name gets paid off once, at the only moment it
is true"*, and builds the arrival-card decision on it. **That argument does not
transfer.** "Sunday Drive" is about the drive, not the feeling at the end of it,
so swapping the name in produces a sentence that is false about the new one.
This needs the designer's judgement, not a rename pass. §10's *conclusion* — the
name appears nowhere but the icon label — survives intact, and agrees with the
instruction at `interface-design-brief.md:169`.

**Merges clean and is fine:** `docs/interface-design-brief.md`. The redesign's
change is a forward-pointer blockquote inserted between the title and the Status
line; this audit's three fixes are at `:52`, `:169` and `:287`. Different hunks,
no overlap. **Confirm after merging that all three fixes survived** — a clean
merge is exactly how a stale line gets through.

**Not a rename issue, but a later review will hit it:**
`docs/interface-design.md:736` cites `RoutePanel.swift:474`/`:478` for the
dial's labels, and the same branch **deletes** `RoutePanel.swift`.

The brief's other cleared check holds: `RoutePanel.swift`, which the redesign
deletes, carries no brand identifier — its 8 `scenic` hits are the arm label and
prose — so its deletion loses no rename work.

---

## 9. What could not be settled

- **`app.sundaydrive` is not confirmed as available or as the owner's final
  choice.** It is right *in the tree*; it becomes permanent at the first build
  upload, TestFlight included, and nothing has been uploaded. That confirmation
  is an owner decision and outside an audit.
- **The brief's six count figures cannot be reproduced** by any of eight
  methods, so they are recorded as unreproducible rather than as wrong (§4).
  The diff settles the underlying question regardless.
- **The 379 backend figure was re-run rather than inherited**, but it cannot be
  timed meaningfully: other Claude sessions run heavy jobs on this Mac
  concurrently, and one was running during part of this audit.

---

## 10. Files this branch changes

| file | change |
| --- | --- |
| `docs/privacy-policy.md` | §3.1, §3.2 — name, bundle id ×2, the quoted purpose string, the resolved open question |
| `docs/app-store-submission.md` | §3.3 — bundle id, the console name answer, `SundayDrive.app`, checklist row 8, the two measured listing facts |
| `docs/interface-design-brief.md` | §3.4 — the app's name ×2, `SUNDAYDRIVE_DATA` |
| `docs/release-plan.md` | §3.5 — one forward-pointer blockquote, no body edit |
| `docs/voice-status-refresh-brief.md` | §3.6 — the three identifiers in the runnable command, plus a dated note on the spent trap and on the hang that did not reproduce |
| `docs/sunday-drive-rename-audit.md` | this document |
| `docs/README.md` | one index row |

Nothing in `ios/`, `server/`, `pipeline/`, `tests/`, `tools/` or `spike/` was
changed by the audit — because nothing there was wrong.
