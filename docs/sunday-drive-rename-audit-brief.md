# Audit the Sunday Drive rename across the whole project

**Status: commissioned 2026-09-21 against `main` at `3c35b4f`. The rename
itself is done and tested — it is commit `c75ce1d` on
`claude/rename-to-sunday-drive`, one commit ahead of `main`, 47 files, both
suites green (backend 379, iOS 241).** Nothing in this brief has been changed.
This is an audit of that branch plus everything it did not reach, and the owner
wants the result *perfect*.

**Read §3 before §4.** Most of the rename is right, and the fastest way to make
this worse is to "fix" something that was a deliberate decision.

---

## 1. What the rename did

Victory Lap → **Sunday Drive**, on 2026-09-21. Target, scheme, module and
product are `SundayDrive`; `CFBundleDisplayName` is `Sunday Drive`; the bundle
identifier is **`app.sundaydrive`** (tests `.tests`). `ios/Sources/VictoryLapApp.swift`
became `SundayDriveApp.swift`. Env vars read `SUNDAYDRIVE_*`, then
`VICTORYLAP_*`, then `SCENIC_*`, at all ten read sites. The Info.plist key is
`SundayDriveAPIBaseURL`.

This is the project's **second** rename in two days (Scenic → Victory Lap on
2026-09-20, `098ff8f`/`14efbf6`). That matters for §3: there are now three
generations of name in the tree, and two of them are supposed to still be there.

**The name was screened before it was taken, and it overruled a prior block.**
`trademark-knockout-findings.md` §14 had said "blocked, drop it";
`docs/sunday-drive-naming.md` re-checked it and three of the four facts behind
that verdict did not survive — the 2009 class-9 application died *procedurally*
("abandoned due to incomplete response"), the class-42 mark it was refused over
has been cancelled since 2014-11-14, and "App Store: zero" was two apps, both
outside Navigation and Travel. **Do not re-open the naming question.** It is
settled, with better evidence than the block had, and a separate 860-line screen
(`claude/scenic-name-viability-screen`) independently blocks "Scenic" and every
variation of it. This task is about *execution*, not about the choice.

---

## 2. Why an audit, when the branch is green

Because a green suite does not prove a rename. Three things a passing test run
cannot see, all of which have bitten this project before:

- **Documents are not compiled.** The rename touched exactly **four** files in
  `docs/` (`README.md`, `sunday-drive-naming.md`, `trademark-knockout-findings.md`,
  `victory-lap-naming.md`). Everything else in `docs/` was left, correctly for
  the historical records and **incorrectly for at least two operational ones** —
  §4.1.
- **A quoted string can go stale without the name changing.** §4.2 is a live
  example, and it predates this rename by a day.
- **The previous rename missed a whole file and nobody noticed for a day.**
  `server/DEPLOY-oracle.md` was untouched by the Victory Lap rename — it still
  set `SCENIC_HOST`/`SCENIC_DATA` and named the Info.plist key
  `ScenicAPIBaseURL`. `c75ce1d` fixed it in passing. The lesson is that the
  breadth check is the part that gets skipped, which is exactly what is being
  commissioned here.

---

## 3. Already verified correct — do not change any of this

I checked each of these on `claude/rename-to-sunday-drive` while writing this
brief. Changing them is a regression, and several look like bugs at a glance.

**The three-layer env chain is deliberate.** `server/app.py:75-96` reads
`SUNDAYDRIVE_*` then `VICTORYLAP_*` then `SCENIC_*`, with the reason in a
comment: dropping a legacy layer **fails silently in the worst way available** —
the server comes up on the default region and the default data directory and
answers every request as though that were right. The same pattern is in
`RouteService.swift:33-34` for `*_API`. Three layers is ugly and it is correct
until the first release. **Do not tidy it.**

**Also verified and deliberate:**

- **`Color.brand` is untouched**, and should be. The previous rename chose
  `.brand` over `.victoryLap` precisely so the next rename would not have to
  touch it. One day later it paid off.
- **`.gitignore` keeps all three** `ios/*.xcodeproj/` entries (`SundayDrive`,
  `VictoryLap`, `Scenic`). Deliberate — see Trap 4.
- **`docs/README.md:20-26` is already correct**, and now narrates both renames.
- **`README.md:144`** keeps one "Victory Lap" — it is the sentence recording
  both namings, and it is right.
- **The GitHub repo, the Cloudflare tunnel named `scenic`, and the `~/Scenic`
  deployment paths are unchanged on purpose.** Renaming the tunnel means
  recreating credentials and re-pointing `api.jameskouvlis.com`.
- **The routing-arm vocabulary is unchanged on purpose** — *scenic route*,
  *scenic score*, *scenic km*, *scenic arm*, *scenic byway*. Correct English,
  and the API wire contract: `Models.swift` decodes `scenic` **by property name
  with no `CodingKeys`**, so renaming that property breaks decoding against
  every deployed server as a *nil route at run time*, not a compile error.
- **Both suites pass, and the backend result is verified rather than assumed:**
  `data/` does not exist in that worktree, so the suite could only reach a graph
  via `SUNDAYDRIVE_DATA`; without it, `test_api.py` skips all 69. That is what
  proves the new variable is read, not merely that the suite is green. Copy this
  trick when you re-verify.

**These documents are historical records and must NOT be rewritten**, per
`docs/README.md`'s own convention that documents written before a rename are
left as written. Occurrence counts of the old name, so you can confirm you have
not touched them:

| file | "Victory Lap" hits | why it stays |
| --- | --- | --- |
| `victory-lap-naming.md` | 58 | the record of the 2026-09-20 decision |
| `trademark-knockout-findings.md` | 28 | the 2026-09-19 screen, §15 is the Victory Lap leg |
| `victory-lap-naming-brief.md` | 13 | the question that produced it |
| `sunday-drive-naming.md` | 9 | legitimately discusses the name it replaced |
| `rename-to-victory-lap-brief.md` | 5 | the previous rename's brief |
| `branding-brainstorm.md` | 2 | the 2026-09-01 record |

---

## 4. What is actually wrong

Three findings, verified on `claude/rename-to-sunday-drive`. §4.1 and §4.2 are
the ones with consequences outside the repo.

### 4.1 Two operational documents still name the app Victory Lap

Both have a `**Status:**` line saying they are current, and both exist to be
*used externally*. Neither is a historical record.

**`docs/privacy-policy.md`** — the draft intended to be **published** at the
App Store privacy-policy URL, which is a hard submission gate. Four hits:

- `:5` and `:36` state the app is `PRODUCT_BUNDLE_IDENTIFIER: app.victorylap`.
  It is `app.sundaydrive`.
- `:29` — *"Victory Lap plans and narrates driving routes that prefer scenic
  roads over fast ones"*. This is the policy's own opening description of the
  app, and it is the first sentence a reader or a regulator gets.
- `:76` — see §4.2, this one is worse than a stale name.

A privacy policy that names the wrong application is wrong the moment it is
hosted, and this document's entire design principle is that every factual claim
cites the file that makes it true.

**`docs/app-store-submission.md`** — the checklist someone works through in
App Store Connect. Three hits:

- `:255` — bundle identifier given as `app.victorylap`.
- `:289` — *"the app is **Victory Lap**"*, as one of the four console answers.
- `:308` — the manifest "verified at the root of the built `VictoryLap.app`".

### 4.2 A quoted string that no longer exists in any form

`docs/privacy-policy.md:76` quotes the location purpose string as:

> `ios/project.yml:21`: "Victory Lap uses your location to follow your…"

`ios/project.yml:21` actually reads:

    NSLocationWhenInUseUsageDescription: "Your location is used to follow the
    route, turn by turn, while you drive."

**The app's name was deliberately removed from that string on 2026-09-20** —
iOS already titles the alert *Allow "Sunday Drive" to use your location?*, so
naming the app in the body said it twice. The policy quotes the pre-removal
wording and was never updated. **This is a Victory Lap-era defect, not a Sunday
Drive one**, and a name-substitution pass would "fix" it to *"Sunday Drive uses
your location…"* — a string that appears nowhere in the project. See Trap 3.

### 4.3 Live briefs carrying the old name

Lower stakes, but one of them is feeding a session that is running right now.

- `docs/interface-design-brief.md` (3 hits) — commissions the interface
  redesign, and §5.4 tells the designer the app is called Victory Lap and that
  the name belongs only on the icon label. The instruction is still right; the
  name in it is not.
- `docs/scenic-name-viability-brief.md` (4 hits) — that task has since
  delivered, so this is now a historical brief. Judge it as such, and if you
  leave it, say why.
- `docs/ui-redesign.md` (8) and `docs/ui-redesign-brief.md` (6) — **do not
  touch these.** A running task is deleting both. Editing them buys a conflict
  over files that are about to disappear.

---

## 5. Three branches are live and two of them collide with this

`git branch --no-merged main` currently lists three. Read this before merging
anything.

| branch | ahead | what it is |
| --- | --- | --- |
| `claude/rename-to-sunday-drive` | 1 | the rename. Your base |
| `interface-redesign-from-nothing` | 4 | the UI overhaul — deletes `RoutePanel.swift` (550 lines), adds `PlanningView`/`PlanningMap`/`PrefSlider`/`Recents`/`tools/fake_api.py` |
| `claude/scenic-name-viability-screen` | 1 | the 860-line Scenic screen |

**The overlap between the rename and the redesign is exactly four files:**
`README.md`, `docs/README.md`, `ios/Sources/AboutView.swift`,
`ios/Sources/RouteModel.swift`.

**The redesign's side of those two Swift files still says `VictoryLap`** — 1 hit
in `AboutView.swift`, 2 in `RouteModel.swift`, because it was branched before
the rename. A merge **will** conflict there, and that is the good case: the
conflict is visible. Resolve to Sunday Drive.

**Checked and cleared, so you need not worry about it:** the redesign's new
files carry no brand identifier at all. Their `scenic` occurrences are the arm
accessor (`model.response?.scenic`) and descriptive English ("A little scenic",
"Most scenic") — all correct and all must survive. And `RoutePanel.swift`, which
the redesign deletes, carried **no** brand identifier, so its deletion loses no
rename work. The "new file copied from an old one" trap does not bite here; I
checked specifically because it has bitten this repo before.

**Scope:** branch off `claude/rename-to-sunday-drive`. Do not edit, rebase or
merge the other two branches — merging the redesign is a separate decision with
a UI review attached. Do report, in one short section, exactly what a later
merge of it will have to resolve.

---

## 6. Traps

1. **Never find-and-replace, and this rename has a new direction of danger.**
   The old name was safe to replace mechanically because "Victory Lap" has no
   domain meaning here. **"Sunday Drive" does not have that property, because
   the codebase is saturated with "drive" as vocabulary:** `DriveTrace`,
   `DriveReplay`, `DriveReplayTests`, `LiveDriveTests`, `DriveTraceTests`,
   `_driving_minutes`, `docs/driving-app-features-brief.md`, and "a drive"
   meaning a recorded journey throughout. A replace on `Drive` is catastrophic.
   Likewise **158 correct-English uses of "scenic"** and **1,967 in
   `docs/route-census/`, where it is a data column value in published ODbL
   data**. Read every hit; decide per hit.
2. **Do not rewrite history.** §3's table is the protected set. A correction
   belongs in a forward-pointer blockquote at the top, per `docs/README.md`
   rule 2 — not in the body.
3. **Verify quoted strings against their cited source, not against the name.**
   §4.2 is the worked example, and a name-grep makes it worse rather than
   better. When a document quotes a file, open the file at a **pinned SHA** —
   `git show <sha>:<file>`, never `git show main:<file>`, because `main` moves
   several times an hour on this repo and nothing in the output tells you which
   tree you read.
4. **`xcodegen` leaves the old project behind, and there could now be three.**
   The Victory Lap rename left a stale `ios/Scenic.xcodeproj` sitting beside the
   new one in a fresh worktree; two projects in `ios/` is how Xcode opens the
   wrong one. Check for `Scenic.xcodeproj`, `VictoryLap.xcodeproj` and
   `SundayDrive.xcodeproj` and delete the stale ones. **`ios/*.xcodeproj` and
   `ios/Generated/Info.plist` are gitignored build outputs of `project.yml`**,
   so a merge or pull updates the yml and never them — run `xcodegen generate`
   in `ios/` before building, or Xcode reports "Cannot find type 'X' in scope"
   with the file plainly on disk.
5. **Do not drop an env-var layer.** §3. It fails silently.
6. **Two tests are the ones that catch a broken product rename.**
   `PrivacyManifestTests` asserts `PrivacyInfo.xcprivacy` out of `Bundle.main`
   (not off disk), and `AttributionTests` pins the route-guidance EULA notice
   character-for-character **and asserts there is exactly one copy**. A rename
   changes the bundle; these are what notice. Never add a second copy of that
   notice.
7. **`docs/README.md` will conflict** with both other live branches. It is a
   pure add/add append to the index table — keep both rows, take no side. This
   has already happened three times on this repo.
8. **Do not spawn research sub-agents.** Broad agents here have silently fanned
   out — two became six, over a million tokens — and exhausted the owner's
   session limit mid-task. Do the searching yourself.

---

## 7. Done looks like

1. **A census, in the findings document**: every occurrence of `Scenic`,
   `Victory Lap` and `Sunday Drive` (and their `SCENIC_`/`VICTORYLAP_`/
   `SUNDAYDRIVE_`, `app.*`, camel-case and lower-case forms) across the whole
   tree, each classified as **brand identifier**, **domain vocabulary**,
   **historical record**, or **defect**. Counted in code, not by eye — an
   eyeballed count has undercounted on this project twice.
2. §4.1 fixed: `privacy-policy.md` and `app-store-submission.md` name Sunday
   Drive and `app.sundaydrive` throughout.
3. §4.2 fixed by **re-reading `project.yml` and quoting what it says**, not by
   substituting the name.
4. §4.3 resolved, with `ui-redesign*.md` left alone and that stated.
5. Every file in §3's protected table verified **unchanged**, by diff.
6. Both suites green and re-run, not inherited: **backend 379, iOS 241**. Use
   §3's skip-behaviour check to prove the env var is actually read.
7. `xcodegen generate` produces exactly one `.xcodeproj` in `ios/`, and any
   stale ones are gone from every worktree that has one.
8. `app.sundaydrive` / `app.sundaydrive.tests` confirmed everywhere a bundle
   identifier appears, including `project.yml`, the docs in §4.1, and the
   Dockerfile/deploy scripts.
9. A short section saying what a later merge of
   `interface-redesign-from-nothing` will have to resolve (§5).
10. A plain statement of what was deliberately left and why.
11. **Or**, for anything that cannot be settled, a statement of which check
    failed and how — the existing findings documents do exactly this for sources
    they could not reach, and that is the standard here.

---

## 8. Working notes

- **Branch off `claude/rename-to-sunday-drive`, not `main`, and not on either.**
  Name the branch for the work.
- **This brief is committed to `main`** — a task chip opens a fresh worktree,
  which would not see an untracked file. It will not be on your base branch
  until you merge `main` in, which you should do first.
- **The data and the `.venv` live only in the MAIN checkout**, not in a
  worktree. Backend suite:
  `SUNDAYDRIVE_DATA="<main checkout>/data/processed-ne" .venv/bin/python -m pytest tests/ -q`,
  about 4.5 minutes. The project path contains spaces, so venv console scripts
  are broken — always `.venv/bin/python -m <tool>`.
- **iOS:** `cd ios && xcodegen generate && xcodebuild test -project
  SundayDrive.xcodeproj -scheme SundayDrive -destination 'platform=iOS
  Simulator,name=iPhone 17 Pro'`. `LiveDriveTests` and `VoiceCatalogueTests`
  skip unless a server answers on `127.0.0.1:5057`; skipping is normal and is
  how the 241 baseline was taken. Never pipe `xcodebuild` through `tail`.
- **Do not trust a single timing** — other Claude sessions run heavy jobs on
  this Mac concurrently. Irrelevant to a rename audit, but relevant if you
  quote a number.
- **The return leg is this repo's documented failure mode** — thirteen finished
  branches piled up unmerged once, and a decision recorded only in an unmerged
  commit message caused a later planning document to re-open settled work. When
  you finish, say plainly that the branch is ready, what it touches, and whether
  the rename is now safe to merge to `main`.
