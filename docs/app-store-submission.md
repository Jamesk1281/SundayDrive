# App Store Connect answers

**Status, 2026-10-04: nothing has been submitted or uploaded.** The Developer
Program membership was accepted on 2026-10-03. The owner decided on 2026-09-19
that the privacy policy and the EULA go out **without a lawyer**
(`release-plan.md` §8, decision 3), so none of the answers here wait on one.
§8 is the checklist. Checkable: the one deliverable here that is code,
`ios/Sources/PrivacyInfo.xcprivacy`, is asserted present in the built bundle by
`ios/Tests/PrivacyManifestTests.swift`.

**What this document is for.** Several things that gate an App Store
submission are answered in a web console and recorded nowhere else. Among them
are the licence agreement, the privacy nutrition label, the privacy policy URL
and export compliance. A web form is a bad place for an answer that has to be
defended later, so the answers live here, each with the code that justifies it.

**Keep this in step with `ios/Sources/PrivacyInfo.xcprivacy`.** The manifest and
the nutrition label answer overlapping questions, and Apple compares them. If
one changes, change the other, and `ios/Tests/PrivacyManifestTests.swift` will
tell you if the manifest drifts from what §3 says here.

---

## 1. The custom EULA (ADPLA §3.3.3(F)(iii))

### The obligation

Apple's Developer Program License Agreement, **§3.3.3 "Data and Privacy" → F.
"Location and Maps; User Consents" → (iii)**, applies to any app doing
real-time navigation. Such an app "must have an end user license agreement
that includes the following notice":

> YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK.
> LOCATION DATA MAY NOT BE ACCURATE.

The clause and the string were checked against the current agreement in
`docs/licensing-open-questions.md` §"Clause by clause". They match byte for
byte: pure ASCII, no smart quotes. **The citation `§3.3.15` that appears in
older documents is the pre-restructure number and no longer exists.**

Apple's standard Licensed Application EULA does not contain this notice and
cannot be edited, so **a custom EULA is required.**

### What is already done — do not do it again

**The notice is in the app, verbatim, rendered, and test-asserted.**
- It is defined at `ios/Sources/AboutView.swift:107-108`.
- It is rendered in exactly one place, `BeforeYouDriveView.swift:35`. That
  view is shown at first launch and can be reached at any time from the
  Sources screen, which is one tap from planning (`PlanningView.swift:81`).
- `ios/Tests/AttributionTests.swift:152-153` asserts it character for
  character, and an uppercase guard stops anyone "fixing the shouting".

**A session that "adds the EULA notice" will duplicate a shipped string and
break a test that asserts there is exactly one.** What is left is the console
field below.

### Apple's minimum terms, and the address they require

A custom EULA must meet Apple's *Minimum Terms of Developer's End-User License
Agreement*
(`apple.com/legal/internet-services/itunes/appstore/dev/minterms/`, read
2026-10-04). It sets ten terms:
1. Acknowledgement that the EULA is between you and the user, not Apple.
2. Scope of the licence.
3. Maintenance and support.
4. Warranty.
5. Product claims.
6. Intellectual property.
7. Export legal compliance.
8. **Developer name and address.**
9. Third-party terms.
10. Apple as third-party beneficiary.

**Item 8 is the one with a cost.** The EULA must state *"Your name and
address, and the contact information (telephone number; E-mail address) to
which any End-User questions, complaints or claims with respect to the
Licensed Application should be directed."* The owner chose a PO box on
2026-10-04, so no home address is published.

### The text to paste

App Store Connect → the app → **App Information** → License Agreement →
**Edit** → custom. Paste the text below and apply it to **United States**,
the only territory (§6). The field is plain text: HTML is stripped and only
line breaks survive.

**Filled in 2026-10-04 by the owner:**
- the address is the PO box in Needham, MA 02492;
- the phone is the account's number;
- `support@jameskouvlis.com` is created.

Paste it as it stands.

The name must match the seller name App Store Connect shows for the account. It
does: Xcode lists the team as "James Kouvlis", Individual, as of 2026-10-04.

```text
SUNDAY DRIVE END USER LICENSE AGREEMENT

Last updated: October 2026

This End User License Agreement ("Agreement") is between you and James Kouvlis ("the Developer"), the developer of the Sunday Drive app ("the App"). By downloading or using the App, you agree to this Agreement.

1. ACKNOWLEDGEMENT
This Agreement is concluded between you and the Developer only, and not with Apple Inc. ("Apple"). The Developer, not Apple, is solely responsible for the App and its content. This Agreement does not provide for usage rules for the App that conflict with the Apple Media Services Terms and Conditions as of the date you accept it.

2. SCOPE OF LICENSE
The Developer grants you a non-transferable license to use the App on any Apple-branded products that you own or control, as permitted by the Usage Rules in the Apple Media Services Terms and Conditions, except that the App may also be accessed and used by other accounts associated with you through Family Sharing or volume purchasing. This Agreement governs the copy of the App you obtain from the App Store. The App's source code is published separately under the Apache License, Version 2.0, and nothing in this Agreement restricts the rights that license gives you in that source code.

3. ROUTE GUIDANCE AND LOCATION DATA
YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK. LOCATION DATA MAY NOT BE ACCURATE.
You are responsible at all times for the safe operation of your vehicle and for obeying all traffic laws and road signs. Do not handle your device while driving. Routes, road classifications, turn restrictions, road closures and estimated times are derived from third-party data that may be incomplete, out of date or wrong, and are offered as suggestions only. Some roads close for part of the year, and the App may not know that a road is closed.

4. MAINTENANCE AND SUPPORT
The Developer is solely responsible for providing any maintenance and support services for the App, as specified in this Agreement or as required under applicable law. You and the Developer acknowledge that Apple has no obligation whatsoever to furnish any maintenance and support services with respect to the App. The App is free, and the Developer may change, suspend or discontinue it, including the routing service it depends on, at any time.

5. WARRANTY
To the maximum extent permitted by applicable law, the App is provided "as is" and "as available", without warranty of any kind, and the Developer disclaims all warranties, express or implied. To the extent any warranty cannot be disclaimed under applicable law, the Developer, not Apple, is solely responsible for it. In the event of any failure of the App to conform to any applicable warranty, you may notify Apple, and Apple will refund the purchase price, if any, for the App to you. To the maximum extent permitted by applicable law, Apple will have no other warranty obligation whatsoever with respect to the App, and any other claims, losses, liabilities, damages, costs or expenses attributable to any failure to conform to any warranty will be the Developer's sole responsibility.

6. PRODUCT CLAIMS
You and the Developer acknowledge that the Developer, not Apple, is responsible for addressing any claims by you or any third party relating to the App or your possession and use of the App, including, but not limited to: (i) product liability claims; (ii) any claim that the App fails to conform to any applicable legal or regulatory requirement; and (iii) claims arising under consumer protection, privacy or similar legislation. This Agreement does not limit the Developer's liability to you beyond what is permitted by applicable law.

7. INTELLECTUAL PROPERTY RIGHTS
In the event of any third-party claim that the App or your possession and use of the App infringes that third party's intellectual property rights, the Developer, not Apple, will be solely responsible for the investigation, defense, settlement and discharge of any such intellectual property infringement claim.

8. LEGAL COMPLIANCE
You represent and warrant that (i) you are not located in a country that is subject to a U.S. Government embargo, or that has been designated by the U.S. Government as a "terrorist supporting" country; and (ii) you are not listed on any U.S. Government list of prohibited or restricted parties.

9. THIRD-PARTY TERMS
You must comply with applicable third-party terms of agreement when using the App, such as your wireless data service agreement. The base map is provided by Apple. Road and scenery data come from OpenStreetMap contributors and other open datasets, credited with their licenses on the App's Sources screen.

10. THIRD-PARTY BENEFICIARY
You and the Developer acknowledge and agree that Apple, and Apple's subsidiaries, are third-party beneficiaries of this Agreement, and that, upon your acceptance of the terms and conditions of this Agreement, Apple will have the right (and will be deemed to have accepted the right) to enforce this Agreement against you as a third-party beneficiary thereof.

11. LIMITATION OF LIABILITY
To the extent not prohibited by applicable law, in no event will the Developer be liable for personal injury, or for any incidental, special, indirect or consequential damages whatsoever, arising out of or related to your use of or inability to use the App, however caused, regardless of the theory of liability, even if the Developer has been advised of the possibility of such damages.

12. PRIVACY
The App's privacy policy is at https://jamesk1281.github.io/SundayDrive/privacy/

13. TERMINATION
This Agreement is effective until terminated. Your rights under it end automatically if you fail to comply with any of its terms. When it ends, you must stop using the App and delete it.

14. CONTACT
Questions, complaints or claims about the App:
James Kouvlis
PO Box 920857
Needham, MA 02492
Phone: (781) 300-8440
Email: support@jameskouvlis.com
```

**Where each minimum term is met:**

| Minimum term | Section |
| --- | --- |
| 1 Acknowledgement | 1 |
| 2 Scope of licence | 2 |
| 3 Maintenance and support | 4 |
| 4 Warranty | 5 |
| 5 Product claims | 6 |
| 6 Intellectual property | 7 |
| 7 Legal compliance | 8 |
| 8 Name and address | 14 |
| 9 Third-party terms | 9 |
| 10 Third-party beneficiary | 10 |

**Things in it that are deliberate:**
- §3 carries the DPLA notice exactly as written, capitals included, on a line
  of its own.
- §3's "roads close for part of the year" is there because the router has no
  seasons yet (`pre-submission-review-verdict.md` C-1).
- §2's Apache sentence stops the EULA from appearing to take back what
  `LICENSE` grants.
- There is no governing-law clause. Add one only if a state is chosen on
  purpose.

---

## 2. Privacy policy URL

**Required, with no exception for free apps or apps without accounts.** The
URL must resolve to a public page at submission time and stay up afterwards.

**Done.** The URL is **`https://jamesk1281.github.io/SundayDrive/privacy/`**.
- It is published from `site/privacy/index.html` by
  `.github/workflows/pages.yml`. That workflow uploads `site/` only; never
  serve Pages from `/docs`.
- It is linked inside the app at `AboutView.swift:302` (`PrivacyPolicy.url`),
  as guideline 5.1.1(i) asks.
- Its contact address is `privacy@jameskouvlis.com`, and
  `tests/test_privacy_page.py` fails if the placeholder returns.
- `docs/privacy-policy.md` is the developer-facing source, with a file
  citation for every claim. A change to its §§0–6 must also change the
  published page.

**The same site also has to serve the Support URL**, which App Store Connect
requires as well. Today `site/index.html` only redirects to the privacy page.
It is being replaced: see `support-page-brief.md`.

---

## 3. App Privacy — the nutrition label

Apple asks four questions about each data type:
- Is it **collected**?
- Is it **linked to the user**?
- Is it used for **tracking**?
- For what **purposes**?

"Collect" means sending data off the device in a way that lets you or your
partners access it for longer than it takes to service the request in real
time.

### The one judgement call: is precise location "collected"?

**On the app and server code alone, no.** Coordinates are sent to `/api/route`
and `/api/loop` to compute a route (`RouteService.swift:150-160` and
`:211-219`, both POST). `server/app.py` keeps nothing: no database, no log
file, no request logging. It is served by `waitress`, which writes no access
log by default.

**With the deployment in the path, arguably yes.** The backend is reached
through a Cloudflare tunnel that terminates TLS, and since 2026-09-29 it runs
on an Oracle Cloud VM. Since that date the coordinates travel in a **POST
body** rather than the URL, so they are no longer in the URLs that access logs
record by default. Cloudflare still terminates TLS and can technically read
the body.

**Answer: declare it collected.** Under-declaring is a rejection and a
credibility problem; over-declaring costs an honest line on the label. This is
the conservative reading, it is what `PrivacyInfo.xcprivacy` says, and
`release-plan.md` decision 3 keeps it.

**Note what is *not* the reason.** Drive traces are not why location is
declared collected:
- The release build does not write them at all (`DriveTrace.isEnabled` is
  `false` since 2026-10-04), and when it did they never left the device
  (`docs/privacy-policy.md` §3).
- On-device storage is not collection under Apple's definition.
- The same goes for the five recent destinations (`Recents.swift`).

A brief that says "the app collects precise location because `DriveTrace`
writes it to disk" has the right conclusion for the wrong reason.

### The answers

| Data type | Collected | Linked | Tracking | Purpose | Evidence |
| --- | --- | --- | --- | --- | --- |
| **Precise Location** | **Yes** | No | No | App Functionality | `RouteService.swift:150-160`, `:211-219`; see above |
| Coarse Location | No | — | — | — | Only precise coordinates are ever sent; the app never derives or sends a coarse value |
| Contact Info | No | — | — | — | No name, email, phone or address field exists anywhere in `ios/Sources` |
| Health & Fitness | No | — | — | — | No HealthKit, no motion APIs |
| Financial Info | No | — | — | — | No purchases, no payment code |
| Contacts | No | — | — | — | No Contacts framework import |
| User Content | No | — | — | — | Drive recording and scenery verdicts are switched off (`DriveTrace.isEnabled = false`); when on, they stayed in the app's own `Documents/traces` with no upload path |
| Search History | No | — | — | — | Typed addresses go to **Apple's** `MKLocalSearchCompleter`/`MKLocalSearch` (`SearchCompleter.swift`, `RouteModel.swift:149-160`, `LoopModel.swift:108-128`), never to the routing server, which only ever receives resolved coordinates. Recent destinations stay on the phone |
| Browsing History | No | — | — | — | No web view, no browser |
| Identifiers | No | — | — | — | No IDFA, no IDFV, no account, no device name read |
| Purchases | No | — | — | — | No StoreKit |
| Usage Data | No | — | — | — | No analytics SDK; the binary contains no third-party code at all (`docs/legal-and-ip-audit.md` §1) |
| Diagnostics | No | — | — | — | No crash reporter, no telemetry |
| Sensitive Info | No | — | — | — | — |
| Other Data | No | — | — | — | — |

**"Used for tracking": No, for every type.** There is no ad SDK, no analytics
SDK, no IDFA and no App Tracking Transparency prompt. `ios/project.yml`
declares no Swift Package, no CocoaPods and no Carthage, and every `import` in
`ios/Sources` is an Apple framework. The test target's `dependencies:` entry in
`ios/project.yml` is **not** a package: it is the test target depending on the
app target. `NSPrivacyTrackingDomains` is empty to match.

---

## 4. Export compliance

**The question:** "Does your app use encryption?" and then "Does your app
qualify for any of the exemptions provided in Category 5, Part 2 of the U.S.
Export Administration Regulations?"

**The facts.**
- The app's only network traffic is HTTPS to `https://api.jameskouvlis.com`
  (`SundayDriveAPIBaseURL` in `ios/project.yml`), using the system's own TLS
  through `URLSession`.
- There is no bundled crypto library, no custom cipher, and no key management
  code anywhere in `ios/Sources`.
- The one App Transport Security exception is `NSAllowsLocalNetworking`, which
  allows `http` to a dev server on the same machine. It is **not**
  `NSAllowsArbitraryLoads`, the one that draws questions.

**The answer that follows:** the app uses encryption, but only Apple's and
only for HTTPS, which is the standard exemption. In App Store Connect that
means answering **"No"** to *non-exempt* encryption.

**To stop being asked on every build,** add to the Info.plist properties in
`ios/project.yml`:

```yaml
        # HTTPS via URLSession only — no bundled or custom crypto anywhere in
        # ios/Sources. Standard Category 5 Part 2 exemption.
        ITSAppUsesNonExemptEncryption: false
```

**Deliberately not added yet.** The key is a declaration to a US export
authority, made in the owner's name, so it is the owner's to make. The facts
that support it are above and can be checked.

---

## 5. Things App Review will ask about, with the answers

These are not console fields. They are the questions this app's configuration
reliably provokes, and each answer is already in the codebase. **Paste the
short versions into the App Review notes** (≤ 4,000 bytes), together with the
region note at the end of this section.

**Why does it need background location?** It is a turn-by-turn navigation app,
and it declares `UIBackgroundModes: [location, audio]` in `ios/project.yml`.
- With when-in-use authorization, background location is permitted for
  navigation as long as the blue status-bar indicator shows. The app opts
  into it (`LocationManager.swift:196`) and switches it off when navigation
  ends.
- Without it, a locked phone or an incoming call silently ends the drive.
- **It never requests "always" authorization**, only
  `requestWhenInUseAuthorization` (`LocationManager.swift:182`, `:287`).

**Why does it need the `audio` background mode?** For spoken guidance, and it
is not optional. On a physical phone on 2026-08-30:
- A build declaring only `location` failed to speak on all 19 attempts made
  from the background. `AVAudioSession.setActive(true)` threw `'!pla'`.
- The same binary with `audio` added spoke 23 of 23, 16 of them with the
  screen off.

The measurement is recorded in the comment above `UIBackgroundModes` in
`ios/project.yml`.

**Why is the Documents folder exposed?** `UIFileSharingEnabled` and
`LSSupportsOpeningDocumentsInPlace` were the *entire* export and deletion story
for drive recordings. Recording is switched off for launch (2026-10-04,
`DriveTrace.isEnabled`), so the folder stays empty; the keys are left in so
turning recording back on needs no plist change.

**Why does it only work in New England?** (`pre-submission-review-verdict.md`
AR-1.) Each road's scenery score is computed from regional open data, so
coverage is the six New England states. A reviewer is almost certainly
outside them, and the app now says so itself (`docs/new-england-only-brief.md`):
- **At launch**, after "Before you drive" and the location prompt, a phone
  outside New England gets a full-screen notice, **This won't work from
  here**. "Got it" dismisses it, and nothing is blocked. The check runs on the
  phone; the location is not sent anywhere for it.
- **My Location**, in Directions and Loop, says "You're outside New England,
  so this can't start from your location. Type a New England town as your
  start." It sends nothing to the server.
- **Home's Loop row** reads "Type a New England town to start", and opens the
  loop page with the start field ready.
- **Search** only offers and accepts New England places.

So give the reviewer the two ways in that work from anywhere:
- **Directions:** type **Concord, MA** as the start and **Rockport, MA** as
  the destination. On 2026-10-04 production returned both arms in 0.8 s:
  fastest 77 km in 53 min, scenic 75 km in 100 min with 24 km of beautiful
  road.
- **Loop:** type **Kent, CT** into "Start and finish here". On 2026-10-04 the
  default 40 km loop came back as 38 km in 52 min, 27 km of it beautiful and
  1.4 km driven twice, with five directions to try.
  - Not Stowe, VT. Its default loop climbs VT 108 to Smugglers' Notch and
    comes back the same way, 19 of 41 km twice, and that road is closed from
    November to April (verdict C-1). Kent's nearest seasonal road is 32 km
    away.
- Attach a short screen recording of a real drive.

**Age rating.** No user-generated content visible to others, no web view, no
advertising, no in-app purchases. Answer the age-rating questionnaire
honestly; the result is Apple's to compute.

---

## 6. Version and identity fields

| Field | Value | State |
| --- | --- | --- |
| Name | `Sunday Drive` (12 of 30) | Decided. Editable until submission, and changeable with any later version |
| Subtitle | `The scenic route, on purpose` (28 of 30) | Decided |
| Bundle ID | `app.sundaydrive` | Decided. **Locks at the first build upload, TestFlight included** |
| SKU | not yet chosen | Permanent once the record is created; never shown to users |
| Version / build | `MARKETING_VERSION` 1.0, `CURRENT_PROJECT_VERSION` 1 | Wired into the bundle since K-2 (`261b3c0`); raise the build number for every upload |
| Devices | iPhone only (`TARGETED_DEVICE_FAMILY: "1"`), iOS 17.0+ | Decided |
| Territories | **United States only** | Decided (`release-plan.md` decision 3) |
| Price | Free | Decided |

**The membership kept the team.** Membership details (2026-10-04) shows Team
ID **`28ZU5P5GC3`**, enrolled as an Individual. That is the same ID the free
Personal Team had: the enrolment upgraded the existing team rather than
creating a new one. So:
- `DEVELOPMENT_TEAM: 28ZU5P5GC3` in `ios/project.yml` is already right.
- `app.sundaydrive` is already registered to this team. Xcode registered it on
  2026-09-29.
- Builds on the phone upgrade in place and keep their data.

**The one thing to do is refresh Xcode.** On 2026-10-04 its cached account
still read `isFreeProvisioningTeam = 1`, "James . (Personal Team)". Until
Settings → Accounts is refreshed, Xcode treats the team as free: 7-day
profiles, the three-app cap, and no App Store upload.

*An earlier version of this section, written the same morning, predicted that
the paid team would get a new Team ID and fight the free one for the bundle
ID. That prediction was wrong and is retracted.*

Note that publishing the app publishes `api.jameskouvlis.com`. The backend URL
is baked into the bundle and readable by anyone who unpacks it. That is
already true of this public repository.

---

## 7. The two blockers that were not paperwork — both resolved

1. **The name.** Resolved 2026-09-20 and re-decided 2026-09-21. "Scenic" was
   taken by a senior direct competitor in the same category, and it is merely
   descriptive. The app is **Sunday Drive** (`sunday-drive-naming.md`).
2. **Apple's map attribution was obscured** by the planning sheet (ADPLA
   Attachment 6 §2.1). It was resolved by the clean-sheet redesign, merged
   2026-09-29 (`f54e24f`). Planning is a page with a bounded map card, and
   the driving screen keeps a reserved strip for the logo
   (`Metric.appleKeep`). Runtime screenshots of every planning stage and the
   driving screen confirm the logo is clear (`pre-submission-review-verdict.md`
   §5). Re-check it if the map card's corner radius or inset changes.

One related item is open but is not a submission gate. Recent destinations,
and drive traces when recording is switched on (it is off since 2026-10-04),
persist Apple-geocoded coordinates (Attachment 6 §2.5,
which now carries an express duty to delete). The fix is to store the
server's snapped endpoint instead. It changes the trace format that
`tools/analyze_trace.py` reads, so it is its own piece of work.

---

## 8. Checklist

| # | Item | State |
| --- | --- | --- |
| 1 | `PrivacyInfo.xcprivacy` in the app bundle | **Done.** Guarded by `PrivacyManifestTests.swift` |
| 2 | Route-guidance notice in the app | **Done.** `AboutView.swift:107-108` |
| 3 | Custom EULA filed in App Store Connect | **Text final (§1).** Paste it once the app record exists |
| 4 | Privacy policy written | **Done.** `docs/privacy-policy.md` |
| 5 | Privacy policy published, URL entered | **Published** (§2). Enter the URL in App Store Connect |
| 6 | Nutrition label answers | **Decided** (§3). Enter them in App Store Connect |
| 7 | Export compliance | **Decided** (§4). The plist key is the owner's to approve |
| 8 | Name | **Done.** `Sunday Drive` |
| 9 | Apple attribution unobscured | **Done** (§7.2) |
| 10 | Bundle ID, version, territories | **Decided** (§6) |
| 11 | Team and bundle ID | **Done** (§6). The membership kept Team ID `28ZU5P5GC3`, and `app.sundaydrive` is registered to it. Refresh Xcode's account so it stops treating the team as free |
| 12 | Support URL | **Built** (`site/index.html`, merged 2026-10-04): `https://jamesk1281.github.io/SundayDrive/`, live once `main` is pushed |
| 13 | App Review notes and screen recording | **Open** (§5). Must exist before the first submission *and* before external TestFlight, whose beta review has the same problem |
| 14 | Mac and Vision Pro availability | **Untick both.** iPhone apps are offered on Apple Silicon Macs and Apple Vision Pro by default. Pricing and Availability → "iPhone and iPad Apps on Apple Silicon Macs", and the Apple Vision Pro section |
| 15 | Accessibility Nutrition Label | Optional. **Do not claim Larger Text.** No text in the app follows Dynamic Type yet (verdict K-5) |
| 16 | Screenshots | **Open.** 6.9" (1320 × 2868), from a **freshly created** simulator, because the unit tests leave fake settings and drive traces in the app (verdict K-3). Take them after the dial headline fix (verdict C-3) |
| 17 | Category, age rating, copyright, release option | **Open.** Navigation / Travel; the age-rating questionnaire; `2026 <legal name>`; **Manually release this version** |
