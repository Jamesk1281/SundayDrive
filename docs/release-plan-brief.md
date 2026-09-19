# Sequence the release workstream — plan it, do not execute it

**Status: scoped 2026-09-19 against `main` at `4cf43b8`, nothing changed.** No
source file, no config, no doc was edited. **The deliverable is a plan.** Nothing
in this task ships, renames, migrates, or commits a licence — see Trap 1.

**The owner chose the goal on 2026-09-19**, from three framings put to him:
*a releasable product*, over *a sharper instrument* and *better routes*. That
answer is the input this whole task rests on. It does not mean the other two stop
mattering; it means the ordering question is now "what does shipping need, in
what order", and that is a question nobody has answered.

## Why this is not already answered

Every *piece* is researched, and researched well. What does not exist anywhere is
the **sequence**, with its dependencies and its decision points. Six documents
hold the pieces and none of them orders the others:

| document | holds |
| --- | --- |
| `docs/branding-brainstorm.md` | the rename: why "Scenic" fails, candidates checked against the App Store API, Longcut recommended |
| `docs/hosting-options-findings.md` | 1,028 lines: Oracle Always Free recommended, with a runbook and an 8 GB sizing argument |
| `docs/legal-and-ip-audit.md` | ten-item register incl. the obscured Apple logo and the generated icon |
| `docs/licensing-open-questions.md` | the `LICENSE` options (§1a), the current Apple clauses (Gap 2) |
| `docs/privacy-and-submission-brief.md` | the privacy manifest, policy draft and console answers |
| `docs/roadmap.md` | twelve open engineering items — **mostly not on this path** |

`roadmap.md` is the closest thing to a next-steps list and it is the wrong shape
for this: it is engineering-only, so it contains neither the rename, nor the
licence, nor hosting, nor any submission gate.

---

## The structure the plan has to respect

### One gate sits before everything, and it may not be open

`ios/project.yml` carries `PRODUCT_BUNDLE_IDENTIFIER: app.scenic.demo`,
`MARKETING_VERSION: "0.1"`, and `DEVELOPMENT_TEAM: 28ZU5P5GC3`. The project has
been running on **free-tier signing**, whose signature is the three-app device
cap the project has already hit.

**App Store submission requires paid Apple Developer Program membership
($99/year); free provisioning cannot submit anything.** A personal team also has
a team ID, so the presence of `DEVELOPMENT_TEAM` does not settle which one this
is. **Establish it first** — `xcrun altool`/`notarytool` behaviour, the
membership page, or simply asking the owner. *Flagged as a hypothesis:* the
evidence (free-tier signing, the device cap, `.demo` bundle id, version 0.1)
points to unpaid, but it has not been confirmed, and if it is unpaid then every
submission gate below is downstream of a purchase decision that nobody has
recorded.

### Two decisions are irreversible, and they set the order

Everything else can be done in any order. These cannot be undone, so they come
first or they cost permanently:

1. **The bundle identifier is permanent after the first submission.** It is
   `app.scenic.demo` today. Renaming the app after submitting means a new bundle
   id, which means a new App Store listing with no continuity.
2. **An Oracle account's home region is permanent, and A1 capacity is scarce in
   exactly the US regions.** `hosting-options-findings.md` calls this "an
   irreversible bet" and recommends `us-chicago-1` on a measured +12 ms RTT from
   Boston against +81 ms for Frankfurt. Choosing wrong means a new account.

### One item got more expensive since it was written

The audit rated the obscured Apple logo a breach of Attachment 6 §2.1.
`licensing-open-questions.md` then found **Attachment 6 §4**, which names
obscuring the logo — by example — as grounds for Apple to revoke MapKit access
outright. No `MKMapView`/`UIViewRepresentable` wrapper exists in `ios/Sources/`
(grepped: zero hits), so the fix is unstarted, and it carries a product decision
with it: what happens at the `.large` detent, where the sheet covers ~92% of the
screen. Apple Maps itself lets its attribution go off-screen at full sheet
height, which is the strongest precedent — but it makes the honest claim
"visible whenever the map is meaningfully visible", not "always".

### Three chips are in flight and their output is assumed, not re-specified

- **Privacy manifest + submission paperwork** (running): will produce
  `PrivacyInfo.xcprivacy`, a marked-draft `docs/privacy-policy.md`, and a
  document holding the App Store Connect answers.
- **ODbL repository compliance** (pending): the `route-census` notice, the
  heatmap credit, the `data-sources.md` correction.
- The licensing research and the docs restructure have **already landed** on
  `main`.

Treat all of that as done. The plan's job is to say what has to happen *around*
it, and in what order.

---

## Traps

**1. Plan. Do not execute.** No rename, no `LICENSE`, no Oracle account, no
`MKMapView` refactor, no `project.yml` edit. Several items here are irreversible
and at least three are decisions belonging to the owner. **Write one document.**
A session that "gets a head start" on the rename is the worst outcome available,
because it is the one change that is expensive to undo.

**2. Never find-and-replace "scenic".** Measured on `main`: brand identifiers
number about 121 — `PRODUCT_BUNDLE_IDENTIFIER` (2), `Color.scenic` and friends
(34 `.scenic` uses in `ios/Sources/`), and the `SCENIC_*` environment prefix (85
occurrences across `SCENIC_API`, `_DATA`, `_DEMO`, `_HOST`, `_PBF`, `_REGION`,
`_TRACES`). Against that sit **158 occurrences of "scenic score", "scenic route",
"scenic km", "scenic arm", "scenic byway", "scenic detour"** — correct English
for the feature, which must survive the rename untouched. The word is descriptive,
which is exactly why it fails as a mark and exactly why it stays in the
vocabulary. A blind replace destroys 158 correct usages and is very hard to
review. **The plan should say this explicitly**, because it is the single most
likely way the rename goes wrong.

**3. Do not re-derive the six documents.** They total well over 3,000 lines
against primary sources. Read them, cite them, order them. A plan that restates
why Oracle beat Hetzner has spent its budget reproducing a conclusion that is
already on `main` and unchallenged.

**4. Do not make the owner's decisions.** At least four are his: the name, the
`LICENSE`, the `.large` detent behaviour, and whether to buy Developer Program
membership at all. **Surface each as a decision point, in the position in the
sequence where it must be made, with what it costs to defer.** That is more
useful than an answer, because the cost-of-deferral is the thing he cannot see
from inside any one document.

**5. `roadmap.md` is not the input.** Twelve open engineering items sit there and
**most are not on the release path**. Two arguably are — the drive that can never
end (`NavigationModel.swift:849-857`, holds GPS at 1 Hz with the screen awake
indefinitely) reads like something review or a user would hit, and the app still
opening on Massachusetts is a first-run impression. Judge them on release
relevance and say so; do not import the list wholesale, and do not re-rank the
engineering backlog as if that were the task.

**6. A new document must be added to `docs/README.md`.** That index landed on
2026-09-19 and it is what stops docs becoming orphans — five were orphaned before
it existed. Adding a file without indexing it reintroduces the exact problem that
restructure fixed.

**7. The repo is public.** A release plan naming dates, costs and a candidate
product name is readable by anyone, including whoever owns the competing mark.
Write accordingly.

---

## Done looks like

1. **One new document**, `docs/release-plan.md`, added to `docs/README.md`'s
   index in the right section.
2. **The membership gate settled or explicitly flagged** — paid or free, with the
   evidence, or a clear statement that it needs the owner to confirm, because
   everything downstream depends on it.
3. **A sequenced plan ordered by irreversibility and dependency, not by effort**,
   covering: the rename and bundle id, the `LICENSE` decision, hosting migration
   and its permanent region choice, the Apple attribution fix and its `.large`
   decision, the privacy and submission artifacts (assumed from the in-flight
   work), the icon, and whichever roadmap items genuinely gate a release.
4. **Every decision point named, positioned, and priced by what deferring it
   costs** — particularly the two irreversibles.
5. **An honest estimate of what is actually left**, in whatever unit survives
   scrutiny — sessions, decisions, or dollars. "This cannot be estimated without
   knowing X" is a legitimate answer; name X.
6. **An honest-answer escape hatch.** If the sequence turns out to be shorter or
   duller than expected — if most of this is four decisions and a weekend — say
   that plainly rather than padding it into a programme. And if any item turns
   out to be already done, say so: two items thought open in this session had
   already shipped, and that is the failure mode this project keeps hitting.
