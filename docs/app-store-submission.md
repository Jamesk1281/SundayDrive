# App Store Connect answers

**Status: written 2026-09-19; nothing submitted, and three of the ten items in
§8 are blocked on decisions only the owner can make.** Checkable: the one
deliverable here that is code, `ios/Sources/PrivacyInfo.xcprivacy`, is asserted
present in the built bundle by `ios/Tests/PrivacyManifestTests.swift`.

**What this document is for.** Four things that gate an App Store submission are
answered in a web console and recorded nowhere else: the licence agreement, the
privacy nutrition label, the privacy policy URL, and export compliance. A web
form is a bad place for an answer that has to be defended later, so the answers
live here, each with the code that justifies it.

**Written 2026-09-19 against `main` at `3fb75d6`. Nothing here has been
submitted.** The app is not currently submittable — see §7 for the two blockers
that are not paperwork.

**Keep this in step with `ios/Sources/PrivacyInfo.xcprivacy`.** The manifest and
the nutrition label answer overlapping questions, and Apple compares them. If
one changes, change the other, and `ios/Tests/PrivacyManifestTests.swift` will
tell you if the manifest drifts from what §3 says here.

---

## 1. The custom EULA (ADPLA §3.3.3(F)(iii))

### The obligation

Apple's Developer Program License Agreement, **§3.3.3 "Data and Privacy" → F.
"Location and Maps; User Consents" → (iii)**, requires that an app doing
real-time navigation "must have an end user license agreement that includes the
following notice":

> YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK.
> LOCATION DATA MAY NOT BE ACCURATE.

The clause and the string were verified against the current agreement in
`docs/licensing-open-questions.md` §"Clause by clause" — byte-for-byte
identical, pure ASCII, no smart quotes. **The citation `§3.3.15` that appears in
older documents is the pre-restructure number and no longer exists.**

### What is already done — do not do it again

**The notice is in the app, verbatim, rendered, and test-asserted.** It is
defined at `ios/Sources/AboutView.swift:100-102`, shown under a `SAFETY`
heading at `:233`, reachable in one tap from the main screen via
`RoutePanel.swift:250`, and asserted character-for-character — plus an
uppercase guard against "fixing the shouting" — in
`ios/Tests/AttributionTests.swift:149-154` and `:158-163`.

**A session that "adds the EULA notice" will duplicate a shipped string and
break a test that asserts there is exactly one.** What is left to do is not in
this repository.

### What is left to do: the console field

App Store Connect offers a choice between Apple's **standard Licensed
Application EULA** and a **custom EULA**. Apple's standard EULA does not contain
this notice and cannot be edited, so **it cannot discharge the clause on its
own**. A custom EULA is therefore required, and Apple requires any custom EULA
to meet its published "Minimum Terms of Developer's EULA".

**Paste-ready clause.** This is the part that carries the obligation; it goes
into whichever custom EULA is filed, as its own numbered section:

```text
ROUTE GUIDANCE AND LOCATION DATA

YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK.
LOCATION DATA MAY NOT BE ACCURATE.

You are responsible at all times for the safe operation of your vehicle and for
obeying all traffic laws and road signs. Routes, road classifications, turn
restrictions and estimated times are derived from third-party data that may be
incomplete, out of date, or wrong, and are offered as suggestions only.
```

The **first paragraph is fixed by contract**: it must appear exactly as above,
capitals included. The second paragraph is drafting, not obligation, and is a
lawyer's to revise or delete.

> **This needs a lawyer, and the rest of the EULA is not drafted here.** A EULA
> is a contract with every user, and Apple's minimum terms have to be satisfied
> in full. Writing the surrounding document is outside what this repository can
> verify. The verbatim notice above is the only part where the correct text is
> known with certainty and has been checked against the source.

**Owner decision:** whether to file a custom EULA at all, which presupposes
deciding the app is going to be submitted. Until then the in-app notice is the
half that protects an actual driver, and it has shipped.

---

## 2. Privacy policy URL

**Required. No exception for free apps, single-user apps, or apps with no
account.** The field will not accept "none", and the URL must resolve to a
publicly readable page at submission time and stay up afterwards.

**Status: there is no URL, because there is nowhere to host it and nothing
published to host.** `docs/privacy-policy.md` is a draft, marked as one, with
every factual claim traceable to a file in this repo.

**Owner decisions, in order:**

1. **Have a lawyer clear the draft.** `docs/privacy-policy.md` §7 lists the
   eight items that need clearing and says which are legal and which are
   factual gaps.
2. **Decide where it is hosted.** It must outlive any one machine; the laptop
   behind the Cloudflare tunnel (`server/DEPLOY.md`) is the wrong place for a
   document that has to be up when the app is reviewed. A static page is
   enough.
3. **Decide the contact address** it will publish (`docs/privacy-policy.md`
   §6).

---

## 3. App Privacy — the nutrition label

Apple asks, per data type: is it **collected**, is it **linked to the user**, is
it used for **tracking**, and for what **purposes**. "Collect" means
transmitting data off the device in a way that lets you or your partners access
it for longer than is needed to service the request in real time.

### The one judgement call: is precise location "collected"?

**On the app and server code alone, no.** Coordinates go to `/api/route` and
`/api/loop` to compute a route (`RouteService.swift:135-146`, `:185-192`) and
`server/app.py` keeps nothing — no database, no log file, no request logging
(startup prints only, at `:93` and `:120`), served by `waitress`, which writes
no access log by default.

**With the deployment in the path, arguably yes.** The backend is reached
through a Cloudflare tunnel that terminates TLS (`server/DEPLOY.md:9`,
`:113-120`), and the coordinates are in the **query string**, so they appear in
the request URL that Cloudflare's edge sees and may retain.

**Answer: declare it collected.** Under-declaring is a rejection and a
credibility problem; over-declaring costs an honest line on the label. This is
the conservative reading and it is what `PrivacyInfo.xcprivacy` says.

**What would change the answer:** moving the coordinates out of the query string
into a POST body would not by itself remove Cloudflare from the path, but it
would stop them appearing in URLs. Dropping the tunnel for a host the owner
controls end to end would remove the third party. Either is a real engineering
change and neither has been made.

**Note what is *not* the reason.** Drive traces are not why location is declared
collected. They never leave the device (`docs/privacy-policy.md` §3), and
on-device storage is not collection under Apple's definition. A brief that says
"the app collects precise location; `DriveTrace` writes it to disk" has the
right conclusion for the wrong reason, and the reason matters — if the routing
request changed, the answer would change, and the traces would not save it.

### The answers

| Data type | Collected | Linked | Tracking | Purpose | Evidence |
| --- | --- | --- | --- | --- | --- |
| **Precise Location** | **Yes** | No | No | App Functionality | `RouteService.swift:135-146`, `:185-192`; see above |
| Coarse Location | No | — | — | — | Only precise coordinates are ever sent; the app never derives or sends a coarse value |
| Contact Info | No | — | — | — | No name, email, phone or address field exists anywhere in `ios/Sources` |
| Health & Fitness | No | — | — | — | No HealthKit, no motion APIs |
| Financial Info | No | — | — | — | No purchases, no payment code |
| Contacts | No | — | — | — | No Contacts framework import |
| User Content | No | — | — | — | Drive traces and scenery verdicts stay in the app's own `Documents/traces` (`DriveTrace.swift:131-134`); there is no upload path in the app |
| Search History | No | — | — | — | Typed addresses go to **Apple's** `MKLocalSearchCompleter`/`MKLocalSearch` (`SearchCompleter.swift:17`, `RouteModel.swift:125`, `LoopModel.swift:78`), never to the routing server, which only ever receives resolved coordinates |
| Browsing History | No | — | — | — | No web view, no browser |
| Identifiers | No | — | — | — | No IDFA, no IDFV, no account, no device name read |
| Purchases | No | — | — | — | No StoreKit |
| Usage Data | No | — | — | — | No analytics SDK; the binary contains no third-party code at all (`docs/legal-and-ip-audit.md` §1) |
| Diagnostics | No | — | — | — | No crash reporter, no telemetry |
| Sensitive Info | No | — | — | — | — |
| Other Data | No | — | — | — | — |

**"Used for tracking": No, for every type.** There is no ad SDK, no analytics
SDK, no IDFA and no App Tracking Transparency prompt — `ios/project.yml`
declares no Swift Package, no CocoaPods and no Carthage, and every `import` in
`ios/Sources` is an Apple framework. (The `dependencies:` line at
`ios/project.yml:97` is **not** a package: it is the test target depending on
the app target.) `NSPrivacyTrackingDomains` is correspondingly empty.

---

## 4. Export compliance

**The question:** "Does your app use encryption?" and then "Does your app
qualify for any of the exemptions provided in Category 5, Part 2 of the U.S.
Export Administration Regulations?"

**The facts.** The app's only network traffic is HTTPS to
`https://api.jameskouvlis.com` (`ios/project.yml:63`, read by
`RouteService.swift:23-32`), using the system's own TLS through `URLSession`.
There is no bundled crypto library, no custom cipher, and no key management
code anywhere in `ios/Sources`. The one App Transport Security exception is
`NSAllowsLocalNetworking` (`ios/project.yml:55-56`) — for `http` to a Flask dev
server on the same machine — **not** `NSAllowsArbitraryLoads`, which is the one
that draws questions.

**The answer that follows:** the app uses encryption, but only Apple's, only for
HTTPS, which is the standard exemption. In App Store Connect that resolves to
answering **"No"** to *non-exempt* encryption.

**To stop being asked on every build,** add to the Info.plist properties in
`ios/project.yml`:

```yaml
        # HTTPS via URLSession only — no bundled or custom crypto anywhere in
        # ios/Sources. Standard Category 5 Part 2 exemption.
        ITSAppUsesNonExemptEncryption: false
```

**Deliberately not added here.** That key is a declaration to a US export
authority, made in the owner's name, and it is the owner's to make. The
engineering facts supporting it are above and are checkable; the declaration is
not a code change to be slipped in by a session writing documents.

---

## 5. Things App Review will ask about, with the answers

Not console fields, but the questions this app's configuration reliably
provokes. Each answer is already written down in the codebase; this is where to
find it.

**Why does it need background location?** `UIBackgroundModes: [location,
audio]` (`ios/project.yml:43-45`). It is a turn-by-turn navigation app: with
when-in-use authorization, background location is permitted for navigation so
long as the blue status-bar indicator shows, which the app opts into
(`LocationManager.swift:150-151`) and switches off when navigation ends
(`:163`). Without it, a locked phone or an incoming call silently ends the
drive. **It never requests "always" authorization** — only
`requestWhenInUseAuthorization` (`LocationManager.swift:145`, `:218`).

**Why does it need the `audio` background mode?** Spoken guidance, and it is
not optional: measured on a physical phone on 2026-08-30, a build declaring only
`location` failed to speak on all 19 attempts made from the background —
`AVAudioSession.setActive(true)` throwing `'!pla'` — while the same binary with
`audio` added spoke 23 of 23, 16 with the screen off. The measurement is
recorded at `ios/project.yml:26-40`.

**Why is the Documents folder exposed?** `UIFileSharingEnabled` and
`LSSupportsOpeningDocumentsInPlace` (`ios/project.yml:51-52`) are the *entire*
export and deletion story for drive recordings: the user copies them off over a
cable or deletes them in the Files app. There is no upload and no in-app share.

**Age rating.** No user-generated content visible to others, no web view, no
advertising, no in-app purchases. *(The exact rating is an owner input, not a
code fact.)*

---

## 6. Version and identity fields

These are still development values and are wrong for a submission
(`ios/project.yml:66`, `:74-76`, `:5`): bundle identifier `app.victorylap`
(renamed 2026-09-20, **still provisional** until first submission),
marketing version `0.1`, build `1`, iPhone only (`TARGETED_DEVICE_FAMILY: "1"`),
deployment target iOS 17.0. **Each is an owner decision**, and the bundle
identifier in particular cannot be changed after first submission.

Note that publishing the app publishes `api.jameskouvlis.com` — the backend URL
is baked into the bundle and readable by anyone who unpacks it. That is already
true of this public repository, but it is worth deciding deliberately rather
than by default.

---

## 7. The two blockers that are not paperwork

Both from `docs/legal-and-ip-audit.md`; neither is fixed, and neither is fixed
by this document.

1. ~~**The name.**~~ **Resolved 2026-09-20.** Item 1 — "Scenic" taken by a
   senior direct competitor in the same category *and* merely descriptive — is
   answered: the app is **Victory Lap** (`victory-lap-naming.md`), and the
   identifiers were renamed to match. Nothing public-facing has gone out under
   either name.
2. **Apple's map attribution is obscured** by the planning sheet. Item 2, ADPLA
   Attachment 6 §2.1, confirmed breach, unfixed. Submitting with a clipped Apple
   logo is submitting a known contract breach.

A third item is open but not a submission gate: drive traces persist
Apple-derived coordinates (item 5, Attachment 6 §2.5, which the licensing review
found now carries an express duty to delete). Fixing it changes the on-disk
trace schema that twelve recorded drives and `tools/analyze_trace.py` depend on,
so it is its own piece of work.

---

## 8. Checklist

| # | Item | State |
| --- | --- | --- |
| 1 | `PrivacyInfo.xcprivacy` in the app bundle | **Done** — `ios/Sources/PrivacyInfo.xcprivacy`, verified at the root of the built `VictoryLap.app` and guarded by `ios/Tests/PrivacyManifestTests.swift` |
| 2 | Route-guidance notice in the app | **Done** — `AboutView.swift:100-102`, shipped 2026-09-19 |
| 3 | Custom EULA filed in App Store Connect | **Open** — §1; needs a lawyer and an owner decision |
| 4 | Privacy policy drafted | **Done, as a draft** — `docs/privacy-policy.md` |
| 5 | Privacy policy cleared and published, URL entered | **Open** — §2; needs a lawyer, a host, and a contact address |
| 6 | Nutrition label answers decided | **Done** — §3; enter them when submitting |
| 7 | Export compliance answer decided | **Done** — §4; the declaration itself is the owner's to make |
| 8 | Name settled | **Blocked** — §7.1 |
| 9 | Apple attribution unobscured | **Blocked** — §7.2 |
| 10 | Bundle ID, version, territories | **Open** — §6, owner input |
