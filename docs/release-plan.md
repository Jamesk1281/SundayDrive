# Release plan: what shipping needs, in what order

> **§6b — the rename — has since been executed, twice.** Scenic → **Victory
> Lap** on 2026-09-20 (`098ff8f`, `14efbf6`) and Victory Lap → **Sunday Drive**
> on 2026-09-21 (`c75ce1d`, `docs/sunday-drive-naming.md`). So the header's
> checkable fact below — that `ios/project.yml:66` reads
> `PRODUCT_BUNDLE_IDENTIFIER: app.scenic.demo` — was true when written and is
> not true now: at `5aff398` that line reads **`app.sundaydrive`**, with
> `app.sundaydrive.tests` at `:101`. `ScenicApp.swift` is now
> `SundayDriveApp.swift` and the Info.plist key is `SundayDriveAPIBaseURL`.
> **§6b's method is what stands, not its identifiers** — it is the record of
> how the rename was done by reading every hit, and the traps it names are
> still the traps. Everything below is left as written; only this pointer is
> new. Nothing is claimed here about §6a, §6c–§6f or §7.

> **2026-09-29: §6c, Decision 4, half of §6d and §7 are overtaken.** The
> owner adopted the clean-sheet redesign (`interface-redesign-from-nothing`,
> `4b3171d`) and it is merged to `main`. Planning is now a page with a bounded
> map card instead of a permanent sheet over a full-bleed map, so nothing can
> reach the corner where MapKit draws Apple's logo. NavView keeps a reserved
> 48 pt strip for it (`Metric.appleKeep`, load-bearing). **So the §6c
> `MKMapView` refactor is no longer needed**, and Decision 4 (where the ornament
> goes at `.large`) is moot, because that detent no longer exists on the
> planning screen. The opening camera now shows all six states
> (`Region.newEngland`), which is the second half of §6d. The first half of §6d
> (a drive that never joins its route can never end) was done later the same
> day; see §6d. §7 is
> done too: the API has served from Oracle since 2026-09-29, per
> `server/DEPLOY-oracle.md`. **§6e (coordinates in the query string) is
> merged and deployed** (checked against the live box 2026-09-29, §6e).
> `MARKETING_VERSION` is `"1.0"` as of 2026-09-29. Still open: the §10
> artifacts. §10's states were brought up to date and §11's
> table given a state column, both 2026-09-29.

> **2026-10-04: the membership is in hand (accepted 2026-10-03), and what is
> left is tracked in two places rather than here.** These are
> [`app-store-submission.md`](app-store-submission.md) §8 (the console
> checklist, with the custom EULA now paste-ready in §1) and the open items at
> the top of [`pre-submission-review-verdict.md`](pre-submission-review-verdict.md).
>
> **Three notes on the text below:**
> - **§3 holds as written: the team did not change.** The individual
>   enrolment kept Team ID `28ZU5P5GC3`, the free team's own ID, so
>   `ios/project.yml` and the existing `app.sundaydrive` registration are
>   already right. Only Xcode's cached account needs refreshing
>   (`app-store-submission.md` §6).
> - **§11's "the total cost is $99/year" is short.** Add the domain,
>   `jameskouvlis.com`, at about $23/year. It expires 2026-10-28 and is
>   unrenewed as of 2026-10-04. Also add the PO box that the custom EULA's
>   minimum terms now require (`app-store-submission.md` §1).
> - **The Windows laptop is retired** (owner, 2026-10-04). §7's "keep the
>   laptop up" option, and its role as a second connector or a rollback, are
>   gone. Oracle is the only origin.

**Status:** current. Sequenced 2026-09-19 against `main` at `4cf43b8`, plus the
two unmerged branches named in §2, and **revised the same day** with three owner
decisions recorded in §8. **Nothing was executed** — no rename, no `LICENSE`, no
Oracle account, no `project.yml` edit. Checkable facts this rests on:
`ios/project.yml:66` still reads `PRODUCT_BUNDLE_IDENTIFIER: app.scenic.demo`,
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

**About a week of engineering, $99, and one external wait that is measured in
hours.** That is the whole release.

An earlier draft of this section put the calendar at one to two months, because
it assumed three external clocks: Apple's enrolment, a paid trademark clearance
search, and a lawyer reading the privacy policy. **Two of those three were
removed by owner decision on 2026-09-19** (§8, decisions 2 and 3), and what
replaced them is free and takes an afternoon. The calendar collapsed to roughly
the engineering time.

So this is not a programme, and it is not really a plan either. It is **one
purchase, one afternoon of free checks, and about a week of work**, of which the
single largest item is one UIKit refactor.

Read §8 first if you read nothing else — the decisions are what make the rest
small.

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

> **Resolved 2026-09-19: the owner will buy it.** The question below is settled
> and the section is kept for its evidence, which still matters — it says what
> the project is running on *today*, and therefore what changes on the day the
> membership starts (§8, decision 1).

**The evidence says the project is on free provisioning**, and the owner can
confirm it in thirty seconds.

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

**$99/year is the gate in front of:** reserving the App Store name, creating the
App Store Connect record, TestFlight, and submission. It is *not* a gate in front
of the rename, the licence, the attribution fix, hosting, or the privacy policy —
all of that proceeds on free provisioning, which is why nothing below stalls
waiting for enrolment to clear.

**Two things change on the day membership starts**, and both are worth having
ready rather than discovering:

- **The three-app device cap lifts.** The spike apps currently competing for
  slots on the phone stop being a constraint on device testing.
- **The App Store name can be reserved.** Do it the same day the name is chosen
  (§6b) — an App Store Connect record holds the name, and holding it is the only
  protection available short of a registered mark.

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
  it today, before the §5.2 search comes back, is how you buy a permanent
  identifier for a name the search then tells you not to use.
- **The Oracle home region** is irreversible and **gates nothing whatsoever**.
  [`hosting-options-findings.md`](hosting-options-findings.md) heads its own
  Phase 1 *"no deadline, no pressure"*, because the laptop serves throughout.
  Choosing it early buys nothing; choosing it carelessly costs a new account.
  It is a decision to make **carefully at the moment of account creation**,
  wherever that lands.

The one item with an **external clock** is enrolment (§5.1), and the one thing
that **App Review will actually test** is the backend (§7). Those two set the
order. Nothing else does.

---

## 5. Day one: one purchase and one afternoon

**There is only one external wait, and it is short.**

1. **Enrol in the Developer Program.** Approval is usually same-day, though
   individual enrolments sometimes need identity verification, so start it first
   and stop thinking about it. Cost: **$99/year**. This is the only thing here
   that anyone else has to act on.
2. **Run the free trademark knock-out search yourself** — see §8, decision 2 for
   what it does and does not buy. Twenty minutes: the candidate name in
   **USPTO classes 9 and 42** at `tmsearch.uspto.gov`, plus a plain web and
   domain search. [`branding-brainstorm.md`](branding-brainstorm.md) §3 has
   already done the App Store half, which is the half that catches the realistic
   risk.
3. **Test the name on five strangers.** One question — "what does this sound
   like it does?" — straight from `branding-brainstorm.md` §7 step 1. Free, and
   it is the only check here that tests whether the name *works* rather than
   whether it is available.

Item 1 blocks §10. Items 2 and 3 block the rename (§6b). Everything else in §6
can start immediately and in parallel, including the largest item.

---

## 6. The engineering, in dependency order

### 6a. Merge the two finished branches (§2) — minutes

### 6b. The rename — half a day, plus the copy pass

**Gated by:** the knock-out search coming back clean (§5.2), which is an
afternoon rather than a wait.
**Gates:** the bundle identifier, and therefore the App Store Connect record.

[`branding-brainstorm.md`](branding-brainstorm.md) §7 already has the internal
order of operations, and it is sound. Two amendments:

- **Its counts are stale.** Written 2026-09-01, it says 13 `Color.scenic` uses
  and ~40 `SCENIC_*`. Measured on `4cf43b8`: **36** `.scenic` uses, **83**
  `SCENIC_*` occurrences, **2** `PRODUCT_BUNDLE_IDENTIFIER` — about **121**
  brand identifiers.
- **Its step 1 — test the name on five strangers — is worth keeping**, and it
  matters more now than it did. Listed as §5.3: every other check on the name
  tests whether it is *available*, and this is the only one that tests whether it
  **works**.

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

**Gated by:** nothing. **Start it now**, in parallel with §5. It is
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

- **Done 2026-09-29**, per
  [`never-joined-drive-brief.md`](never-joined-drive-brief.md). An unjoined car
  that stays within 50 m of one fix for 5 minutes now *pauses* the drive
  (`NavigationModel.stalled`). That stops location, releases the screen lock,
  and shows *Keep navigating* / *End drive*. It is not an arrival and it does
  not touch `hasJoinedRoute`. Over the twelve real traces, only
  `drive-2026-08-25-222344` pauses (at 300 s), and the other eleven end as they
  did. **Deliberately excluded, not overlooked:** an "arrived near the pin even
  if unjoined" rule (the real phantom sat 176 m from its pin, and a loop's
  destination is its start), and pausing *joined* drives (an overlook stop is
  the product working, and that is an owner decision not yet made). The
  original entry follows.
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

### 6e. Move the coordinates out of the query string — an hour, and now required

**Done in code 2026-09-29** (branch `claude/coordinates-out-of-url`, per
[`coordinates-out-of-the-url-brief.md`](coordinates-out-of-the-url-brief.md)),
with the privacy policy's §2.1(a), §7 item 1 and §8 rewritten in the same
commit. **Deployed, checked 2026-09-29:** an empty-bodied POST to
`https://api.jameskouvlis.com/api/route` gets the handler's own 400
(`need from=lat,lon&to=…`), not a 405, so the box serves POST.

**Promoted from "nice to have" by §8 decision 3.** Route requests put start and
destination in the **URL query string**, and the Cloudflare tunnel terminates
TLS — so *"the server stores nothing"* is true of `server/app.py`, which has no
logger, no database and no file writes, and false of the system as deployed.

While that is true, the honest privacy policy has to either disclose an edge
that may retain coordinates in access logs, or argue that it does not. **With no
lawyer in the loop, do not argue it — remove it.** Moving the coordinates into a
POST body keeps them out of URLs, which is what access logs record by default.

Two things this does *not* do, stated so the policy does not overclaim:

- It does **not** remove Cloudflare from the path. The tunnel still terminates
  TLS and can still see the body. The policy names Cloudflare as a processor
  either way — that is a one-sentence disclosure, not a legal judgment.
- It does **not** change the privacy manifest. Precise location stays declared
  as collected, which is the conservative answer and the one to keep (§8,
  decision 3).

Touches `ios/Sources/RouteService.swift` and `server/app.py`. Note
`privacy-policy.md` §8 lists this change as one that invalidates the draft — so
make the edit and the policy wording in the same pass.

### 6f. A backend a reviewer can reach — see §7

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

## 8. The decisions — three taken 2026-09-19, one still open

Four decisions were outstanding when this document was written. **Three were
taken on 2026-09-19** and are recorded here with their reasoning, because a
decision recorded nowhere but a conversation is the failure mode §2 documents.
One remains open, and it sits inside the largest code item.

### Decision 1 — Developer Program membership: **buy it** ✅

**$99/year, day one (§5.1).** Settled. The evidence in §3 says the project is on
free provisioning today, so this is a real change rather than a formality: the
three-app device cap lifts, and the App Store name becomes reservable.

*Recorded because the alternative was live and reasonable:* not buying leaves a
private instrument on free provisioning, and deletes §5.2, §6b and all of §10.
That was a materially cheaper project and it is the one this repository was
optimised for. It was declined deliberately.

### Decision 2 — Trademark clearance: **do the free search, not the paid one** ✅

**Twenty minutes, day one (§5.2).** Paid clearance was declined. What replaces it:
USPTO classes 9 and 42, a web and domain search, and the App Store search
`branding-brainstorm.md` §3 has already run.

**Why this is proportionate, stated honestly.** The realistic failure mode for a
free app with no revenue is **not** litigation — that costs a complainant more
than it recovers. It is an **App Store trademark complaint**, which is cheap to
file and can pull an app pending resolution. The App Store name search is exactly
the check that catches that, and it returned zero collisions and zero in
Navigation/Travel for the recommended candidate.

**What the free version does not buy**, so nobody later believes it did: no
search of unregistered common-law rights, no coverage of close-but-not-identical
marks, and **no opinion** — a knock-out search tells you what is obviously taken,
not what is safe.

**Why deferring the paid search is cheap and deferring the rename is not.** If
the free search misses something, the cost is renaming at low download counts —
which is the cheap state the project is in now and will stay in for a while.
Clearance becomes worth paying for when there is brand equity to defend, and that
is not a launch-day condition. **Revisit it before spending money on the brand**,
which is what `branding-brainstorm.md` §7 step 2 actually says.

**This does not make the rename optional.** Keeping "Scenic" is the single
highest-risk naming option available — identical mark, identical goods, senior
user, already shipping in the same App Store category. A free search substitutes
for clearance, not for renaming.

### Decision 3 — Privacy: **no lawyer; US-only at launch** ✅

**Not legal advice**, and the same caveat `branding-brainstorm.md` opens with
applies here: the engineering facts below are checkable and were checked; the
conclusion that they do not need a lawyer is a proportionality judgment the owner
made, not counsel's opinion. It is recorded with its reasoning so that it can be
re-opened on its merits rather than re-litigated from scratch.

`privacy-policy.md` §7 lists eight items "a lawyer has to clear." A ninth was
added on 2026-09-29, when the server moved to Oracle. Its row at the bottom of
the table was added then too.
None of them needs one, given four conditions — three of which are decisions or
tests rather than legal work:

| §7 item | What resolves it instead |
| --- | --- |
| 1. Cloudflare sees the coordinates | **§6e** — move them to a POST body, then name Cloudflare as a processor in one sentence |
| 2. Is precise location "collected"? | Already answered **yes**, the conservative side. **Keep it.** Over-declaring is free; under-declaring is what bites |
| 3. CPRA | A threshold test, not a judgment: >$25M revenue, 100k+ consumers, or revenue from selling data. None is met, and no data is sold |
| 4. GDPR | **Removed by shipping US-only.** Territory is a checkbox in App Store Connect |
| 5. Children / age rating | App Store Connect's own questionnaire decides this. Answer it honestly |
| 6. Reduced-accuracy behaviour | The draft says outright this is not a legal question. It is an **untested code path** — test what the app does under approximate location, then write what it does |
| 7. Contact address | Owner's pick. Use a monitored alias, not a personal address — it is published |
| 8. The name | Decision 2 and §6b |
| 9. Oracle hosts the server (added 2026-09-29) | Same shape as item 1: **name Oracle as the host** in the sentence that names Cloudflare. The region is `us-ashburn-1`, so shipping US-only still removes GDPR. **An EU host, or Contabo GmbH anywhere, would reopen item 4.** Optionally switch off the three in-VM agent plugins the free tier does not need |

**Why no lawyer is defensible here, specifically.** What makes a privacy policy
dangerous is asserting something untrue. This one was written against the code,
and the code is unusually easy to describe: **zero third-party dependencies**
(every import in `ios/Sources/` is an Apple framework — no analytics, no ads, no
crash reporting), no accounts, no advertising identifier, and a server with no
logger, no database and no file writes. One declared data type, not linked, not
used for tracking.

**US-only at launch, and why it is the right shape rather than a dodge.** It
removes GDPR from scope rather than answering it, leaving CPRA as the only regime
in play — and CPRA fails on thresholds. It is **reversible**: territories can be
added later, and the honest sequence is to add the EU when someone has reason to
want it, with the policy revisited then. What it costs is EU availability at
launch, which is worth approximately nothing for a New England driving app.

**When this decision expires.** Revisit the moment any of these becomes true:
money changes hands (paid app, IAP, subscription), an account system appears, a
third-party SDK is added, or EU/UK territories are switched on. `privacy-policy.md`
§8 already lists the engineering changes that invalidate the draft; this is the
commercial half of the same list.

### Decision 4 — Attribution at the `.large` detent ⬜ **still open**

**Position:** inside the MapKit refactor (§6c) — a parameter of the fix, not a
separate task. **Deferral cost: it blocks the refactor from being finished**, and
that refactor is the largest code item, so deferring it idles the long pole.

At `.large` the sheet covers ~92% of the screen. Does the ornament ride above the
sheet at every detent, or is it allowed off-screen at full height? Apple Maps
itself lets its attribution go off-screen at full sheet height, which is the
strongest available precedent — but choosing it makes the honest claim *"visible
whenever the map is meaningfully visible"*, not *"always"*. The audit recommends
following Apple's own behaviour; the owner should confirm, because it is the
difference between a defensible reading of Attachment 6 §2.1 and a literal one.

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
| `PrivacyInfo.xcprivacy` | **On `main`** (`ios/Sources/PrivacyInfo.xcprivacy`). Keep precise location declared as collected — §8, decision 3 |
| Privacy policy **draft** | **On `main`**, `docs/privacy-policy.md`. No longer needs a lawyer (§8, decision 3). Of the four things it needed, two are done: §6e landed and deployed, and Cloudflare and Oracle are both named (§2.1(a)). **Still open: the approximate-location path tested (§7 item 6), and a monitored contact alias (§6).** It is also still a developer document, with file citations and a §7 addressed to a lawyer; the published page has to be a user-facing rewrite of §§0–6 |
| Privacy policy **URL** | **Built; contact address in and Pages set to GitHub Actions (2026-09-29). Live once merged.** A **hard submission gate**. `site/privacy/index.html`, deployed by `.github/workflows/pages.yml` (uploads `site/` only — never serve Pages from `/docs`) to `https://jamesk1281.github.io/SundayDrive/privacy/`, and linked from the Sources screen (`PrivacyPolicy.url`, `AboutView.swift`). Owner steps are `privacy-policy-page-brief.md` §5; `tests/test_privacy_page.py` fails if the contact placeholder comes back |
| **Territories: United States only** | Decided (§8, decision 3). Set at the listing. Reversible later |
| App Store **name reservation** | Open. Do it the day membership clears and the name is chosen — §3 |
| The four App Store Connect answers | **On `main`**, `app-store-submission.md` |
| In-app route-guidance notice | **Shipped, and on `main`** — `AboutView.swift:97-98`, asserted character-for-character in `AttributionTests.swift`. **Do not add it again** — a test asserts there is exactly one. (The audit cites `:100-102`, which is where the §2 merge moves it) |
| EULA field in App Store Connect | Open. Paste-ready text is in `app-store-submission.md` §1 |
| Export-compliance declaration | Open, trivial |
| Screenshots, description, category | Open, not started |
| `MARKETING_VERSION` off `0.1` | **Done 2026-09-29**: `"1.0"` at `ios/project.yml:74` |

---

## 11. What this costs, and what is left

**The two unpriced items are gone.** An earlier draft of this section said the
total was "$99 plus two unknowns, and the unknowns are plausibly the larger
half" — the unknowns being professional trademark clearance and counsel. §8
declined both, and replaced them with free checks.

**The total cost of this release is $99/year.** There is nothing else to buy.
Hosting is $0/mo on the Oracle free tier, or free on the laptop that already
serves; the exit, if it is ever outgrown, is ~€5.50/mo (§7).

**The time is about a week of engineering**, and it is no longer gated by anyone
else:

| Item | Estimate | State, 2026-09-29 |
| --- | --- | --- |
| Merge the two finished branches (§6a) | minutes | **Done** |
| The rename (§6b), including the in-product copy pass | half a day | **Done**, twice (header note) |
| **MapKit attribution refactor (§6c)** | **one to two days** | **Not needed**: the redesign keeps the logo clear by construction |
| The two roadmap defects (§6d) | about a day | **Done**: opening camera, and the never-joined pause (§6d) |
| Coordinates to a POST body (§6e) | an hour | **Done and deployed** |
| Hosting: keep the laptop up, or migrate (§7) | an evening, or a weekend | **Done**: Oracle, since 2026-09-29 |
| Submission artifacts, screenshots, listing (§10) | a day | Open. `MARKETING_VERSION` done; the policy URL, approximate-location test and contact alias are the gates |

Plus the day-one afternoon in §5, and however long Apple takes to approve
enrolment — usually same-day.

**The estimate is only wrong in one direction that matters.** §6c is the item
that can grow: if re-implementing the polyline, marker and user-location content
on `MKMapView` turns out to need more than the audit's ~150-line estimate, that
is where the week becomes two. Nothing else here has that shape — everything else
is either already written, a checkbox, or an afternoon.

**What genuinely cannot be estimated:** how long App Review takes, and whether it
passes first time. §7 names the most likely rejection — a reviewer opening the app
against a backend that is down — and that one is preventable. The rest is not
forecastable and should not be planned around.
