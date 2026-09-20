# The privacy manifest, the privacy policy, and the App Store paperwork

> **Acted on 2026-09-19.** The manifest is
> `ios/Sources/PrivacyInfo.xcprivacy`, verified at the root of the built
> `Scenic.app` and guarded by `ios/Tests/PrivacyManifestTests.swift`; the policy
> draft is [`privacy-policy.md`](privacy-policy.md); the console answers are
> [`app-store-submission.md`](app-store-submission.md); the `§3.3.15` citations
> are corrected. **One of this brief's inferences was wrong and the correction
> matters:** precise location is declared collected because route *requests*
> carry coordinates through a Cloudflare edge, **not** because `DriveTrace`
> writes to disk — on-device storage is not collection under Apple's definition.
> Right answer, wrong reason, and the reason is what a later change would turn
> on. See `app-store-submission.md` §3.

**Status: diagnosed 2026-09-19 against `main` at `3fb75d6`, nothing changed.**
No source file, no test, no config was touched.

**Read this before assuming any of it is still undone.** Two documents already on
`main` cover the legal ground and must not be re-derived:

```sh
docs/legal-and-ip-audit.md        # 369 lines, ten-item register, primary sources
docs/licensing-open-questions.md  # 640 lines, the current-agreement verification
```

**The EULA half of this task has already shipped, and this brief exists partly to
stop it being done twice.** See "What is already done" below — verified today,
not taken on trust.

---

## What is already done, verified against `main` today

The 2026-09-19 attribution merge (`3fb75d6`) landed more than the licensing
research knew about — that research ran against `378aaee`, *before* the merge, so
its register still lists item 3 as open. It is not.

**Apple's route-guidance notice is in the app, verbatim, and test-asserted.**

- `ios/Sources/AboutView.swift:96-98` defines it:

  ```swift
  static let routeGuidanceNotice =
      "YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE "
      + "RISK. LOCATION DATA MAY NOT BE ACCURATE."
  ```

- `AboutView.swift:229` renders it under a `SAFETY` heading, deliberately set
  apart from the credits (`:221-223` says why: "The credits say who owns the
  data; this says what the app does not promise about it").
- `RoutePanel.swift:250` presents the sheet, so it is one tap from the main
  screen.
- `ios/Tests/AttributionTests.swift:149` asserts it character for character, and
  `:158` separately asserts it equals its own `.uppercased()` — a guard against
  "fixing the shouting".

Checked programmatically after joining the split string literal: the required
text is present **verbatim**. `docs/licensing-open-questions.md` confirmed the
same string byte-for-byte against the current agreement dated 2026-08-18.

**So the in-app half of audit item 3 is closed.** What remains of "EULA" is not a
repo artifact at all — it is a field in App Store Connect. See Task 3.

---

## What is actually missing

### 1. `PrivacyInfo.xcprivacy` does not exist, and is required today

```sh
git ls-tree -r main --name-only | grep -i privacyinfo   →  (nothing)
```

Six live `UserDefaults` call sites on `main`:

```
ios/Sources/VoiceCatalogue.swift:118,119   # chosen voice
ios/Sources/VoiceCatalogue.swift:148,149   # speech-length cache
ios/Sources/VoiceGuide.swift:351,352       # mute flag
```

That is `NSPrivacyAccessedAPICategoryUserDefaults`, reason code **`CA92.1`**
("access info from same app, per documentation") — correct here, because every
one of those keys is the app reading back its own settings.

**This escalated and the older notes are stale on it.** It used to be recorded as
something the *voice branch would create*. Voice merged in `0b1f240` on
2026-08-30. The requirement is live on `main` now.

The manifest must also declare **collected data types**. The app collects precise
location; `DriveTrace` writes it to disk. It is not linked to identity and not
used for tracking, so the honest answers are the mild ones — but they have to be
answered, not omitted.

`ios/project.yml:11-12` declares `sources: [- Sources]`, so a manifest placed in
`ios/Sources/` should be picked up as a resource. **Verify that it lands in the
built bundle rather than assuming it** — see Trap 2.

### 2. No privacy policy exists, in any form

```sh
git grep -riIl 'privacy polic' main   →  only the three legal docs, discussing its absence
```

A privacy policy URL is a hard App Store submission gate with no exception for
free or single-user apps, and precise location is "sensitive personal
information" under CPRA and special-category-adjacent under GDPR.

**The facts a policy needs are already established and verifiable in this repo**,
which is what makes drafting it dispatchable:

- Drive traces are written to the app's own `Documents/traces` and stay there;
  the documented way off the device is a cable.
- `server/` persists nothing — the audit grepped it: startup prints only, no
  access log, no request logging, no coordinate storage.
- No analytics SDK, no ad SDK, no third-party code at all in the shipped binary
  (`ios/project.yml` declares no package manager; the `dependencies:` line at
  `:97` is the test target depending on the app target — see Trap 3).
- `UserDefaults` holds a voice name, a speech-length cache and a mute flag.

That is an unusually strong privacy position, and most of what the policy has to
say is simply true already.

### 3. The App Store Connect paperwork has no home in the repo

Four things are answered in a web console, not in code, and nothing in the repo
records what the answers should be: the **custom EULA** (Apple's standard EULA
does *not* contain the route-guidance notice, so it cannot discharge the clause
on its own), the **Privacy Nutrition Label**, the **privacy policy URL**, and
**export compliance** (HTTPS only, so the standard exemption applies — but it
still has to be declared).

### 4. One stale citation, now cheap to fix

`ios/Tests/AttributionTests.swift:161` reads:

```swift
"§3.3.15's notice is upper-case in the agreement: \(notice)"
```

**`3.3.15` no longer exists in the agreement.** `docs/licensing-open-questions.md`
established that §3.3 was restructured into eleven thematic subsections and the
route-guidance obligation now sits at **§3.3.3(F)(iii)**. The string is
unchanged; only the citation moved. Grep the whole repo — the old number appears
in more than one place.

---

## Traps

**1. Do not re-derive the legal research, and do not re-ship the EULA notice.**
Both documents named at the top are on `main` and total over 1,000 lines against
primary sources. The notice is already in `AboutView.swift`, rendered, and
asserted twice. A session that "adds the EULA" will duplicate a shipped string
and break a test that asserts there is exactly one.

**2. `xcodegen generate` is mandatory after touching `project.yml`, and its
failure mode lies to you.** `ios/Scenic.xcodeproj` and `ios/Generated/Info.plist`
are gitignored build outputs. Xcode keeps building the *old* config until they
are regenerated, and the symptom is "Cannot find type 'X' in scope" with the file
plainly on disk. Run `cd ios && xcodegen generate` after any `project.yml` change
**and after any pull that adds a file**. Then confirm the manifest is actually in
the built product — a `PrivacyInfo.xcprivacy` that is not in the bundle's
resources is worth nothing, and nothing warns you.

**3. `ios/project.yml:97` has a `dependencies:` line that is not a package
dependency.** It is `- target: Scenic`, the test target depending on the app
target. Both legal documents conclude no third-party code ships; that is correct.
Do not "discover" a dependency here and write it into the privacy policy.

**4. Do not publish anything, and do not commit a `LICENSE`.** The privacy policy
deliverable is a **draft in the repo for review**, clearly marked as not
published. `docs/licensing-open-questions.md` says plainly that any policy that
will actually be published needs a lawyer, because "being wrong in a published
policy is worse than not having one". The repository licence is a separate open
decision belonging to the owner — that document lays out three options and
deliberately commits no file. Leave it that way.

**5. Do not touch `DriveTrace.swift`.** Audit item 5 — recording the router's
snapped node instead of the geocoder's coordinates — is real, and
`docs/licensing-open-questions.md` made it *stronger* by finding that the current
Attachment 6 §2.5 adds an express duty to delete. It is deliberately **out of
scope here**, because it changes the on-disk schema of the instrument that twelve
recorded drives and `tools/analyze_trace.py` depend on. That is a different
blast radius from writing documents, and it deserves its own dispatch.

**6. Another session on this machine will fight you for the simulator and for
port 5057.** `xcrun simctl install booted` targets *their* device. Boot your own
and use `-destination 'id=<UDID>'` — `name=` is rejected here even for a listed
device. Nothing in this task needs the API, which is currently down anyway.

---

## Done looks like

1. **`ios/Sources/PrivacyInfo.xcprivacy`**, declaring
   `NSPrivacyAccessedAPICategoryUserDefaults` with reason `CA92.1` and the
   collected-data entry for precise location (not linked to identity, not used
   for tracking) — **verified present in the built app bundle**, not merely
   present on disk.
2. **`docs/privacy-policy.md`** — a draft, marked as a draft, every factual claim
   traceable to a file in this repo, with a short note naming which claims a
   lawyer has to clear before it is published anywhere.
3. **`docs/app-store-submission.md`** (or similar) — the console answers that
   live nowhere today: the custom EULA text to paste, including the verbatim
   notice; the Privacy Nutrition Label answers with the code evidence for each;
   the export-compliance answer; and a line saying the privacy policy URL is the
   owner's to host.
4. **The stale `§3.3.15` citation corrected to `§3.3.3(F)(iii)`** everywhere it
   appears, including `ios/Tests/AttributionTests.swift:161`.
5. **The iOS suite green.** Run it; say the number. If a pre-existing failure is
   unrelated to this change, say that too rather than fixing it here.
6. **An honest-answer escape hatch.** "This needs a lawyer" and "this cannot be
   determined without the owner deciding X" are both complete answers for any
   individual item — say which ones, and what the decision is. If the privacy
   manifest turns out not to be required on the evidence, say so with the
   evidence rather than shipping one to be safe.
