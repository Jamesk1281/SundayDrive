# Rename the app to Victory Lap — identifiers only, by reading every hit

**Status: scoped 2026-09-20 against `main` at `897dbe7`, nothing renamed.** No
identifier was touched, nothing filed, bought or submitted.

**The name is decided and the gate is open.** `docs/victory-lap-naming.md` §2
returns *"No knockout blocker found — proceed to professional clearance"*, and
records that **the owner declined paid clearance** (release-plan Decision 2),
on the reasoning that the realistic failure mode for a free app is an App Store
complaint rather than litigation, and the cost of being wrong is a rename at low
download counts. So `release-plan.md` §6b's "gated by clearance returning clean"
is **satisfied by that decision**, not still pending.

The strings, both decided and both verified against Apple's own field limits in
`docs/victory-lap-naming.md` §7:

| Field | Value | Count |
| --- | --- | --- |
| App name | **`Victory Lap`** | 11 / 30 |
| Subtitle | **`The scenic route, on purpose`** | 28 / 30 |

The subtitle deliberately keeps the word, chosen by the owner over the
document's own recommendation, with the evidence in front of the decision
(§6a). **It is metadata, not a build** — changing it later costs an App Store
Connect edit. Nothing in this task depends on it.

---

## The prerequisite: merge one branch first

**`claude/privacy-manifest-and-submission-docs` is unmerged and touches four
iOS files**, including the two this rename rewrites hardest:

```
ios/Sources/AboutView.swift          ios/Tests/AttributionTests.swift
ios/Sources/PrivacyInfo.xcprivacy    ios/Tests/PrivacyManifestTests.swift
```

A rename touches essentially every file under `ios/`. Running it against `main`
while that branch is out guarantees a conflict on `AttributionTests.swift` and
on the new manifest, in a change where "resolve by taking both" is exactly how a
brand string survives in a file nobody re-reads. **Merge it first.** It is a
clean merge today.

Three other branches are unmerged and are **docs-only** — `release-plan-sequence`,
`trademark-knockout-screen`, `hosting-recheck-2026-09`. They do not collide.

## The surface, measured on `main` today

```
case-insensitive "scenic", whole repo        3,168   across 118 files
  of which docs/route-census/ (DATA)         1,966   ← never touch, see Trap 3
  "scenic score|route|km|arm|byway|detour"     190   ← correct English, keep
brand identifiers
  SCENIC_* environment occurrences              88
  .scenic  (Swift colour token, ios/Sources)    34
  PRODUCT_BUNDLE_IDENTIFIER lines                2
  .scenic  (routing-arm accessor)               34   ← NOT brand. see correction below
```

**The ~121 figure in this brief counted those 34 as brand. It should not have.
The true brand-identifier count is closer to ~90**, almost all of it the
`SCENIC_*` prefix. Treat every count here as a measurement to re-take, not a
target to hit.

Reproduce with:

```sh
git grep -oi 'scenic' -- . | wc -l
git grep -oi 'scenic' -- docs/route-census/ | wc -l
git grep -oiE 'scenic (score|route|km|arm|byway|detour)' -- . | wc -l
git grep -o 'SCENIC_[A-Z]*' -- . | wc -l
git grep -o '\.scenic\b' -- 'ios/Sources/*.swift' | wc -l
```

### What is genuinely brand, verified on `main`

- `ios/project.yml:1` `name: Scenic`
- `ios/project.yml:3` `bundleIdPrefix: app.scenic`
- `ios/project.yml:16` `CFBundleDisplayName: Scenic`
- `ios/project.yml:66` `PRODUCT_BUNDLE_IDENTIFIER: app.scenic.demo`
- `ios/project.yml:101` `PRODUCT_BUNDLE_IDENTIFIER: app.scenic.demo.tests`
- `ios/Sources/ScenicApp.swift` — the struct **and** the filename
- ~~`Color.scenic` and the other `.scenic` tokens (34 in `ios/Sources/`)~~
  **CORRECTION, 2026-09-20 — this line was wrong and it is the dangerous kind of
  wrong.** There is no `Color.scenic`. `ios/Sources/Theme.swift:10` already reads
  `static let brand = Color(red: 0.22, green: 0.83, blue: 0.62)` — the colour was
  named for the app, not the arm, before this rename started. **All 34 `.scenic`
  hits are the routing-arm accessor** — `response.scenic`, `miles.scenic`,
  `model.response?.scenic.coordinates` — at `ContentView.swift:48,84,116,122`,
  `NavigationModel.swift:1266`, `RoutePanel.swift:542`, and
  `RouteResults.swift:10,106,134,180,191`.
  **They are the API contract and they must not be renamed.** `server/app.py:8`
  documents the response as `{"fastest": …, "scenic": <GeoJSON Feature>}` and
  `ios/Sources/Models.swift:12` is `let scenic: RouteFeature`, decoded from that
  key **by property name** — there are no `CodingKeys`. Renaming the Swift
  property silently breaks decoding against every deployed server. This is the
  same "it names the arm, not the brand" rule as Trap 2, and the identifier list
  above originally contradicted the trap that protects it.
- the `SCENIC_*` env prefix (88): `SCENIC_API`, `_DATA`, `_DEMO`, `_HOST`,
  `_PBF`, `_REGION`, `_TRACES`
- the `ScenicAPIBaseURL` Info.plist key, whose call sites outside
  `project.yml:63` are `RouteService.swift:13` and `:28`, `README.md`,
  `server/DEPLOY.md`, `docs/consumer-polish-brief.md`, and both hosting
  documents

---

## Traps

**1. Never find-and-replace, in any casing.** 3,168 hits, of which about 121 are
brand. The other ~3,047 are data and correct English. **Read every hit.** It is
an afternoon; the alternative is unreviewable.

**2. Capitalisation is not the discriminator, and `RoutePanel.swift` proves it
twice in one file.** Verified on `main` today:

```
RoutePanel.swift:298      Text("Scenic").font(.title2.bold())    ← the panel header. BRAND. changes
RoutePanel.swift:472      Text("Scenic").font(.caption2)         ← the Fastest↔Scenic slider label. ARM. keep
RouteResults.swift:18     card("Scenic", minutes: …)             ← the comparison card. ARM. keep
```

Two identical string literals 174 lines apart, opposite treatment. Anyone
reasoning "capital-S is the brand, lowercase is the feature" gets `:472` wrong
and renames the slider. `RouteResults.swift`'s user-visible copy has the same
shape — *"Scenic adds 49 min"* is a sentence about the scenic **arm**, and a
blind replace turns it into a sentence about the product that reads like a bug.

**3. Do not touch `docs/route-census/` at all.** Its 1,966 hits are an arm-name
**column value** in committed CSV. Changing them would corrupt a dataset that
`docs/route-distribution-study.md` quotes, and that directory now carries an
**ODbL notice and licence offer** (`docs/route-census/README.md`) — it is
published data with obligations attached, not prose.

**4. `SCENIC_DATA` appears in every documented command in this repo**, including
`server/DEPLOY.md`, `README.md`, the test invocations in several briefs, and the
project's own memory. Renaming the env prefix silently breaks all of them.
**Either rename and update every documented command in the same change, or keep
reading the old names as a fallback for one release.** Decide, state which, and
do it completely — a half-renamed env prefix is the worst of both.

**5. `xcodegen generate` is mandatory after `project.yml`, and its failure mode
lies.** `ios/Scenic.xcodeproj` and `ios/Generated/Info.plist` are gitignored
build outputs; Xcode keeps building the old config until regenerated, and the
symptom is "Cannot find type 'X' in scope" with the file plainly on disk. The
generated project directory is named after the target, so **the rename changes
what `xcodegen` emits** — expect to update `.gitignore` too, and confirm the old
`Scenic.xcodeproj` is not left behind shadowing the new one.

**6. Do not submit anything, and do not treat the bundle id as final.** It
becomes permanent **at first submission** and that has not happened.
`bundleIdPrefix: app.scenic` → `app.victorylap` with `app.victorylap` and
`app.victorylap.tests` is the obvious shape and drops the now-wrong `.demo` —
**propose it, use it, and flag it explicitly for the owner's confirmation before
any App Store Connect record exists.** Nothing else in this task is irreversible.

**7. Do not rewrite the historical record.** Most of the 118 files are briefs,
verdicts and findings that describe what was true when written; rewriting them
falsifies the project's own evidence trail, which is the thing this repository
is actually for. **Recommended policy — confirm it, then apply it uniformly:**
rename in code, config, and the *currently descriptive* documents
(`README.md`, `docs/README.md`, `docs/data-sources.md`, `server/DEPLOY.md`,
`docs/roadmap.md`); leave briefs, verdicts, studies and everything under
`docs/archive/` as written; add **one** dated line to `docs/README.md` recording
that the app was renamed and when, so a reader hitting the old name knows why.

**8. The repo is public**, and the rename is the most visible change it has had.
The README is the first thing anyone sees.

---

## Done looks like

1. **`claude/privacy-manifest-and-submission-docs` merged first**, then the
   rename on its own branch off the result.
2. **Every brand identifier renamed** — `project.yml` (name, prefix, display
   name, both bundle ids), `ScenicApp.swift` struct and filename, the `.scenic`
   colour tokens, the `SCENIC_*` prefix, and `ScenicAPIBaseURL` with all seven
   call sites.
3. **The 190 correct-English uses and the 1,966 census values untouched**, and
   `RoutePanel.swift:472` / `RouteResults.swift:18` verifiably still say
   "Scenic" because they name the routing arm. Say so explicitly in the commit —
   it is the thing a reviewer will check first.
4. **`xcodegen generate` run, the app built, and both suites green.** Backend:
   `SCENIC_DATA=…/data/processed-ne .venv/bin/python -m pytest tests/`, 348 at
   last count — under whatever the variable is called afterwards. iOS:
   `xcodebuild test -project <New>.xcodeproj -scheme <New> -destination 'id=<UDID>'`.
   **State both numbers.**
5. **The doc policy from Trap 7 applied uniformly**, with the one-line rename
   note in `docs/README.md`.
6. **The bundle identifier flagged** as the one value that becomes permanent
   later, with what was chosen and why.
7. **An honest-answer escape hatch.** If a hit genuinely cannot be classified as
   brand-or-vocabulary, leave it, list it, and say why — a short list of
   deliberate deferrals is a better outcome than a confident wrong call on a
   user-visible string. And if the count of true brand identifiers comes out
   materially different from ~121, say so: that number is a measurement, not a
   promise.
