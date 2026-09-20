# Release plan: what shipping needs, in what order

**Status:** current. Sequenced 2026-09-19 against `main` at `4cf43b8`, plus the
two unmerged branches named in §2. **Nothing was executed** — no rename, no
`LICENSE`, no Oracle account, no `project.yml` edit. Checkable facts this rests
on: `ios/project.yml:66` still reads `PRODUCT_BUNDLE_IDENTIFIER: app.scenic.demo`,
`grep -rE 'MKMapView|UIViewRepresentable' ios/Sources/` returns zero, and
`https://api.jameskouvlis.com/api/health` answered **HTTP 530** while this was
written.

This document orders the six documents that hold the pieces. It does not repeat
them — [`branding-brainstorm.md`](branding-brainstorm.md),
[`hosting-options-findings.md`](hosting-options-findings.md),
[`legal-and-ip-audit.md`](legal-and-ip-audit.md),
[`licensing-open-questions.md`](licensing-open-questions.md),
`app-store-submission.md` (unmerged, §2) and
[`roadmap.md`](roadmap.md) are each correct and each cited below. The thing none
of them contains is the sequence, and that is all this adds.

---

## 1. The honest headline

**The engineering left is about a week. The calendar is one to two months, and
almost none of that is code.**

Three external clocks dominate everything: Apple's enrolment approval, a
professional trademark clearance search, and a lawyer reading the privacy policy
draft. Each is measured in days-to-weeks, each costs money, and **none of them
can be started by writing software**. The whole engineering backlog — the
rename, one UIKit refactor, two defect fixes and a hosting migration that already
has a runbook — fits comfortably inside the time those three take to return.

So this is not a programme. It is **three purchases, three decisions and about a
week of work**, and the only reason it is not a weekend is that two of the
purchases have strangers attached to them.

The one thing that would genuinely change this estimate is §3.

---

## 2. Two things believed open are already done

Both were written, committed, and then not merged. Anyone planning from `main`
alone will re-specify them.

| Believed open | Actually | Where |
| --- | --- | --- |
| **The `LICENSE` decision** | **Made.** Apache-2.0, chosen by the owner, with `LICENSE`, `NOTICE`, and the ODbL notice for the census CSV | `claude/apache-licence-and-odbl-notice` (`165679d`), unmerged |
| **Privacy manifest and submission paperwork** | **Written.** `PrivacyInfo.xcprivacy`, `docs/privacy-policy.md` (draft), `docs/app-store-submission.md` (the four console answers), plus `PrivacyManifestTests.swift` asserting the manifest out of `Bundle.main` | `claude/privacy-manifest-and-submission-docs` (`2053609`), unmerged |

**So the owner has three decisions left, not four.** The licence is not one of
them. [`licensing-open-questions.md`](licensing-open-questions.md) already
carries the resolved banner on that branch.

**Action: merge both branches.** It costs nothing, decides nothing, and it stops
the next reader re-opening settled work. Do this before anything else in this
document — not because it is urgent, but because it is free and it makes the
tree tell the truth.

---

## 3. The gate: is there a paid Developer Program membership?

**The evidence says no, and the owner can settle it in thirty seconds.**

What is checkable on the build Mac, without asking anyone:

| Evidence | Reading |
| --- | --- |
| Four `Apple Development` signing certificates on the team in `project.yml:73`, spanning 2024→2027, one currently valid. **Zero `Apple Distribution` certificates.** | Suggestive, not proof — Xcode creates the distribution certificate on demand at first archive, so someone who has never archived would also have none |
| **Both provisioning-profile directories are empty** (`~/Library/MobileDevice/…` and `~/Library/Developer/Xcode/UserData/…`) | Consistent with simulator-only work; not decisive |
| `PRODUCT_BUNDLE_IDENTIFIER: app.scenic.demo`, `MARKETING_VERSION: "0.1"` | Nobody has ever prepared a submission |
| **The three-app device cap has been hit in practice**, with `MIInstallerErrorDomain error 13` naming the three incumbents | **This is the decisive one.** A three-app limit exists *only* under free provisioning. Paid membership has no such cap |

**Conclusion: free provisioning, no paid membership.** The last row is the one
that carries it — it is an observed limit, not an absence of evidence, and the
limit it observed does not exist on a paid account.

**Confirm it anyway**, because everything in §6 is downstream: open
`developer.apple.com/account` and look at the membership panel. That is faster
than reading this paragraph.

**If unpaid, then $99/year is a gate in front of:** reserving the App Store
name, creating the App Store Connect record, TestFlight, and submission. It is
*not* a gate in front of the rename, the licence, the attribution fix, hosting,
or the privacy policy — all of that proceeds unpaid, which is why the sequence
below does not stall waiting for it.

---

## 4. Why the order is not "irreversible things first"

The brief that commissioned this document identified two irreversible decisions
— the bundle identifier and the Oracle home region — and inferred that they come
first. **That inference does not hold, and following it would waste the cheapest
weeks available.**

Irreversibility tells you **how much care** a decision needs. It does not tell
you **when** to make it. What sets timing is dependency and lead time.

- **The bundle identifier** is irreversible *at first submission* and it encodes
  the name, so the rename must precede the App Store Connect record. That is a
  real ordering constraint — but its deadline is submission, not today. Making
  it today, before clearance comes back, is how you buy a permanent identifier
  for a name a lawyer then tells you not to use.
- **The Oracle home region** is irreversible and **gates nothing whatsoever**.
  [`hosting-options-findings.md`](hosting-options-findings.md) heads its own
  Phase 1 *"no deadline, no pressure"*, because the laptop serves throughout.
  Choosing it early buys nothing; choosing it carelessly costs a new account.
  It is a decision to make **carefully at the moment of account creation**,
  wherever that lands.

The items that genuinely force the order are the ones with **external clocks**
(§5) and the one that **App Review will actually test** (§7).

---

## 5. Start the three clocks (day one, no code, parallel)

These are first because they are slow and outside the project's control. Nothing
else in this document is on the critical path while these are running.

1. **Settle membership (§3), and buy it if buying.** Enrolment approval is
   typically fast but can take a day or two, and individual enrolments sometimes
   require identity verification. Cost: **$99/year**.
2. **Commission the trademark clearance search** on the candidate recommended in
   [`branding-brainstorm.md`](branding-brainstorm.md) §3 — the one with zero App
   Store collisions. That document is explicit that the search comes **before
   money goes into a brand**, and it is right: its own first recommendation was
   withdrawn after a check. Cost: unpriced anywhere in this repo — see §11.
3. **Send the privacy policy draft to a lawyer** — `docs/privacy-policy.md`,
   which arrives with the §2 merge. It is a marked draft, and it is the gating
   input to a hard submission requirement (audit item 4: a privacy policy URL).
   Cost: unpriced — see §11.

Everything from §6 onward can proceed while these three are out.

---

## 6. The engineering, in dependency order

### 6a. Merge the two finished branches (§2) — minutes

### 6b. The rename — half a day, plus the copy pass

**Gated by:** clearance returning clean (§5.2).
**Gates:** the bundle identifier, and therefore the App Store Connect record.

[`branding-brainstorm.md`](branding-brainstorm.md) §7 already has the internal
order of operations, and it is sound. Two amendments:

- **Its counts are stale.** Written 2026-09-01, it says 13 `Color.scenic` uses
  and ~40 `SCENIC_*`. Measured on `4cf43b8`: **36** `.scenic` uses, **83**
  `SCENIC_*` occurrences, **2** `PRODUCT_BUNDLE_IDENTIFIER` — about **121**
  brand identifiers.
- **Its step 1 — test the name on five strangers — is worth keeping**, and it is
  free, and it can run during the clearance wait.

#### The trap, stated explicitly

**Never find-and-replace "scenic", in any casing.** The repository holds **3,046**
case-insensitive occurrences. Of those:

| What | Count | Treatment |
| --- | --- | --- |
| Census output under `docs/route-census/` | **1,967** | **Data.** `scenic` is an arm-name column value. Never touch |
| Brand identifiers (`.scenic`, `SCENIC_*`, bundle ids) | ~121 | **Rename** |
| "scenic score / route / km / arm / byway" | 158 | **Correct English. Keep** |
| Everything else — prose, tests, comments | remainder | Read it and decide |

The word is descriptive, which is exactly why it fails as a trademark and
exactly why it stays in the vocabulary.

**The specific way this goes wrong** is subtler than lowercase prose, and it is
worth knowing before anyone starts. Someone renaming an app will reason that
lowercase `scenic` is the feature and capital-`Scenic` is the brand, and replace
the capitalised form. That reasoning is wrong, and `RoutePanel.swift` proves it
twice in one file:

- **`RoutePanel.swift:298`** — `Text("Scenic").font(.title2.bold())`, the panel
  header, above a hint line. **This is the brand. It changes.**
- **`RoutePanel.swift:472`** — `Text("Scenic").font(.caption2)`, the right-hand
  label of the Fastest↔Scenic slider. **This is the arm. It must not change.**

Two identical string literals, 174 lines apart, opposite treatment. The same
applies to `RouteResults.swift:18` (`card("Scenic", …)`, the comparison card) and
its user-visible copy at `:186–214` — *"Scenic adds **49 min**"* is a sentence
about the scenic arm, and a blind replace turns it into a sentence about the
product that reads like a bug.

**Do the rename by reading every hit.** 121 is an afternoon. The alternative
destroys 158 correct usages and is very hard to review.

Genuinely brand, and easy to miss: `ios/project.yml:1` (`name:`), `:16`
(`CFBundleDisplayName`), `ios/Sources/ScenicApp.swift` (struct *and* filename),
and the `ScenicAPIBaseURL` Info.plist key. That key has seven call sites outside
`project.yml:63`: `RouteService.swift:13` and `:28`, `README.md:85`,
`server/DEPLOY.md:394`, `consumer-polish-brief.md:49`, and both hosting documents
(`-brief.md:331`, `-findings.md:670`).

### 6c. The Apple attribution fix — the one real refactor, one to two days

**Gated by:** nothing. **Start it now**, in parallel with the §5 clocks. It is
the only item here that could surprise, and it is the largest.

Audit item 2 is a **confirmed breach of ADPLA Attachment 6 §2.1**, and
[`licensing-open-questions.md`](licensing-open-questions.md) found that §4 names
obscuring the logo, by example, as grounds for Apple to **revoke MapKit access**.
For an app that is a map, that is not a fine — it is the product.

The audit already measured the two cheap fixes failing
(`.safeAreaPadding`, `.safeAreaInset` — ornament pixel-identical both times) and
concluded SwiftUI's `Map` exposes no lever. Confirmed still true: zero
`MKMapView`/`UIViewRepresentable` in `ios/Sources/`. The fix is a
`UIViewRepresentable` around `MKMapView`, driving `layoutMargins.bottom` from the
live sheet height, at **both** `ContentView.swift:40` and `NavView.swift:38` —
re-implementing the polyline, marker and user-location content that `Map`'s
result builder currently gives for free.

**Correcting one thing that is easy to misread:** the obscuring does **not** vary
by detent. A sheet's bottom edge is pinned at every detent, so this is broken at
`.planningCompact` and `.medium` too, not only at `.large`. The `.large` question
(§8, decision 3) is about where the ornament goes *once you can move it*, not
about when the breach occurs.

### 6d. Two roadmap items that ship with the release — about a day

Judged on release relevance, not on backlog rank. See §9 for the ten that do not
qualify.

- **A drive that never joins its route can never end**
  (`NavigationModel.swift:849-857`). Holds GPS at 1 Hz with the screen awake,
  indefinitely, when the car is snapped to the wrong road or parked beside a line
  it never reached. This is a battery-drain defect reachable on a first drive; it
  is the kind of thing that produces one-star reviews and, if a reviewer hits it,
  a rejection. The fix is **not** clearing `hasJoinedRoute` — it also gates the
  backtrack floor and off-route recovery — so it needs an arrival path that does
  not depend on having joined.
- **The app still opens on Massachusetts** (`ios/Sources/Region.swift`). The API
  serves six states; the starting camera and the search bias serve one. Not a
  gate — nobody rejects for it — but it is the first screen, and it makes five
  of six states harder to search than they should be.

**One cheap privacy win worth taking here:** route requests put coordinates in the
**query string**, and the tunnel terminates TLS, so "the server logs nothing" is
true of `server/app.py` and false of the system. Moving them to a POST body is
small, and it reduces what the submission has to declare as collected.

### 6e. A backend a reviewer can reach — see §7

---

## 7. Hosting is on the release path, but not for the reason you would guess

**It is not the baked URL.** `ScenicAPIBaseURL` points at a *hostname*, and both
hosting documents are explicit that the hostname does not change — the Cloudflare
tunnel is the switch. Migrating the backend therefore needs **no new build and no
App Review**. Hosting is fully decoupled from the submission sequence.

**It is that the API is down right now.** `HTTP 530` — the tunnel answering with
nothing behind it, because the laptop is off. **An App Review reviewer opens the
app, searches for a route, and gets an error.** That is a rejection under
guideline 2.1, and it is the single most likely way a first submission fails.

So the requirement is **reliability during review**, not migration. Two ways to
meet it:

- **Keep the laptop up.** Free, available today, and it is what `530` says is not
  currently happening. The weakness is not capacity, it is that nothing restarts
  it — which is exactly the gap `hosting-options-findings.md` names when it
  recommends systemd over a batch file.
- **Do the Oracle migration.** The runbook is written end to end, rollback is
  "start `cloudflared` on the laptop again", and it costs **$0/mo**. The home
  region is decided here, carefully, and only here (§4).

**Either is acceptable for launch.** The honest ceiling, already measured in
`hosting-options-findings.md` and worth carrying into any launch expectation:
routing **does not parallelise** — `scipy.sparse.csgraph.dijkstra` holds the GIL
— so the constraint is *simultaneous* reroutes, not daily volume, and the second
OCPU buys nothing. More throughput means more processes at ~3.53 GB of graph
each, so the 8 GB free box tops out around two workers. The doc's verdict —
comfortable at 1,000+ drives/day — is the right one for a first release. The exit,
if it is ever outgrown, is ~**€5.50/mo** at Contabo, with no DNS change and no
App Review.

---

## 8. The three decisions, positioned and priced by deferral

Each sits at the point in the sequence where it must be made. The price is **what
deferring it costs**, which is the thing no single document can show.

### Decision 1 — Buy Developer Program membership? ($99/year)

**Position:** day one (§5.1). **Deferral cost: everything downstream stops, and
the exposure compounds.** Without it there is no App Store Connect record, and
without that the chosen name **cannot be reserved** — so every week of deferral
is a week the name sits unclaimed after a clearance search has been paid for.
Deferring also defers nothing useful: the rename, the MapKit fix and hosting all
proceed unpaid, so the $99 buys time rather than work.

*If the answer is no*, that is a legitimate outcome and it should be said out
loud rather than discovered — the product stays a private instrument on free
provisioning with a three-app cap, and §5.2, §5.3, §6b and the whole of §10
become unnecessary. **That is a materially cheaper project**, and it is the
version this repository has actually been optimised for.

### Decision 2 — The name

**Position:** after clearance returns, before the App Store Connect record (§6b).
**Deferral cost: low now, permanent later.** Today the rename is an afternoon of
reading 121 identifiers. After the first submission the bundle identifier is
permanent, and changing the name means a new identifier, a new listing, and no
continuity of ratings or installs. There are no users and no listing, so this is
the cheapest this decision will ever be — and the competing mark in the same
category on the App Store is the reason it cannot simply be skipped.

### Decision 3 — Attribution at the `.large` detent

**Position:** inside the MapKit refactor (§6c) — it is a parameter of the fix,
not a separate task. **Deferral cost: it blocks the refactor from being
finished**, and the refactor is the largest code item, so deferring it idles the
long pole.

The question: at `.large` the sheet covers ~92% of the screen. Does the ornament
ride above the sheet at every detent, or is it allowed off-screen at full height?
Apple Maps itself lets its attribution go off-screen at full sheet height, which
is the strongest available precedent — but choosing it makes the honest claim
*"visible whenever the map is meaningfully visible"*, not *"always"*. The audit
recommends following Apple's own behaviour; the owner should confirm, because it
is the difference between a defensible reading of §2.1 and a literal one.

### Already decided, recorded here so it is not re-opened

**The licence is Apache-2.0** (§2). Chosen over MIT because §6 grants no rights
in names or marks — which matters precisely while the name is still changing —
and because its patent grant is express.

---

## 9. What is *not* on the release path

Ten of the twelve open items in [`roadmap.md`](roadmap.md) are instrument and
routing work, and importing them would turn a week into a quarter. Named so the
exclusion is deliberate rather than an oversight: re-fitting `CONTROL_SECONDS`,
time-of-day costs, lane guidance, `via`-way turn restrictions, the snap
start-point offset, more drivers, the remaining-distance odometer, the 500 m
reroute re-seat window, and `RELIEF_FULL` saturation.

**Two of those deserve a sentence rather than silence:**

- **`RELIEF_FULL` has no range left north of Massachusetts** — 13.4% of chunks
  north of MA saturate it, so a White Mountains ravine scores like a rise outside
  Worcester. Not a gate, and re-fitting changes every score so it is not a
  pre-launch move. But it is a **truthfulness constraint on the listing**: the
  scenery model is weakest in the terrain a scenic-driving app's screenshots
  would most want to show. Do not claim uniform six-state quality.
- **Lane guidance** is the most-requested-looking gap on the list and it is
  unbuildable on this data — `turn:lanes` covers 4.6%–23.8% of primary+ junction
  approaches across New England. It is not deferred; it is blocked upstream.

The icon (audit item 8) is not roadmap work but is on the path: it is generated,
so it **may not be ownable**, which matters for a brand but not for submission.
Redrawing it is a design task that can happen any time before the listing.

---

## 10. Submission artifacts

All of these are downstream of Decision 1, and most are already written.

| Item | State |
| --- | --- |
| `PrivacyInfo.xcprivacy` | **Written**, unmerged (§2) |
| Privacy policy **draft** | **Written**, unmerged — needs a lawyer (§5.3) and a public URL |
| The four App Store Connect answers | **Written**, unmerged — `app-store-submission.md` (§2) |
| In-app route-guidance notice | **Shipped, and on `main`** — `AboutView.swift:97-98`, asserted character-for-character in `AttributionTests.swift`. **Do not add it again** — a test asserts there is exactly one. (The audit cites `:100-102`, which is where the §2 merge moves it) |
| EULA field in App Store Connect | Open. Paste-ready text is in `app-store-submission.md` §1, which arrives with the §2 merge |
| Export-compliance declaration | Open, trivial |
| Screenshots, description, category | Open, not started |
| `MARKETING_VERSION` off `0.1` | Open, one line |

---

## 11. What cannot be estimated, and why

Two numbers are missing and neither can be found inside this repository:

1. **The cost of professional trademark clearance**, and of filing if the owner
   chooses to file. `branding-brainstorm.md` correctly says "not legal advice"
   and stops there. This is the largest unpriced item in the plan.
2. **The cost of counsel reviewing the privacy policy.** Same shape.

Both are quotes, not research, and both are obtainable in a day of phone calls.
Until they exist, the dollar total for this release is **$99 plus two unknowns**,
and the unknowns are plausibly the larger half.

The **time** estimate does survive: roughly a week of engineering (rename half a
day, MapKit refactor one to two days, the two defects about a day, hosting a
weekend if migrating, submission artifacts a day), inside one to two months of
calendar set by clearance and counsel.

**The estimate is only wrong in one direction that matters:** if the MapKit
refactor turns out to need the polyline and marker rendering rebuilt more
thoroughly than the audit's ~150-line estimate assumes, §6c is the item that
grows. Nothing else here has that shape.
