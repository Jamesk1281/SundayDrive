# Voice guidance: establish what is actually verified — documentation only

**Status: scoped 2026-09-20 against `main` at `897dbe7`, nothing changed.** No
Swift file, no test, no config was touched — **and this task must not touch one
either.** A rename is in flight across the whole iOS target; see Trap 1. The
deliverable is one document.

Voice guidance is **built and shipped**. `docs/voice-guidance-plan.md` (813
lines) designed it and `docs/archive/voice-guidance-plan-brief.md` scoped it;
both carry "built 2026-08-30". `ios/Sources/VoiceGuide.swift` (627 lines) speaks
the maneuvers, `VoiceCatalogue.swift` (235) lets the driver pick a voice, and
`UIBackgroundModes: audio` is in `ios/project.yml` because §1 of the plan
measured that it is required — on a real phone, 23 of 23 utterances spoken with
it against 0 of 19 without.

So this is not "is it built". It is **"what about it is actually verified"**, and
the answer measured below is: less than the repository implies.

---

## The two findings that make this worth a session

### 1. The voice tests do not run, and a green suite says otherwise

`VoiceCatalogueTests.swift:27` calls `VoiceCatalogue.duration(of: samantha)`,
which renders real speech through `AVSpeechSynthesizer`. On this machine the
simulator's voice-asset fetch times out and **the whole run stops** — last log
line `nw_read_request_report [C8] Receive failed with error "Operation timed
out"`, then nothing, for **13 minutes, observed twice**. Every other suite had
already passed.

The standing workaround is to skip it:

```sh
xcodebuild test -project Scenic.xcodeproj -scheme Scenic -destination 'id=<UDID>' \
  -skip-testing:ScenicTests/LiveDriveTests \
  -skip-testing:ScenicTests/VoiceCatalogueTests
```

That returns `** TEST SUCCEEDED **` over 19 suites. **It also means the voice
catalogue's 143 lines of tests are unverified on every run, and a clean result
reports them as if they had passed.** `VoiceGuideTests.swift` is 506 lines and is
*not* in the skip list — but whether it currently passes has not been stated
anywhere, only assumed. **Establishing that is part of this task.**

*The fix is not in scope* — it lands in `ios/Tests/`, which the rename is
rewriting. Diagnose it precisely and hand it on.

### 2. Voice has never spoken on a recorded drive

Measured today:

```
last trace in traces/     drive-2026-08-25-222344.ndjson
voice merged (0b1f240)    2026-08-30
```

**Every one of the twelve recorded drives predates the feature by at least five
days.** This project's whole discipline is that a test drive produces
measurements rather than impressions — the ETA model, the junction costs and the
scenic score were each validated that way. Voice is the one shipped feature that
has never been through it.

That matters concretely, because the plan's central design decisions are all
about *timing under real driving*, and none of them has met a real drive:

- the schedule is **time-based, not distance-based** — the brief's central
  settled question;
- **about a fifth of maneuvers have to share an utterance** (§11 argues against
  ever speaking about scenery on that basis — "there is no spare airtime");
- the audio session, the mute control, and the reroute behaviour.

*Flagged as a hypothesis, because it is one:* a simulator cannot falsify any of
that. **What would settle it: one drive with voice on, which the owner has to
take.** It is not dispatchable and it is not in this task's scope — but naming
what that drive should test *is*.

---

## Traps

**1. Touch no file under `ios/`. A rename is in flight across the entire
target.** `claude/…rename…` is rewriting `PRODUCT_BUNDLE_IDENTIFIER`,
`ScenicApp.swift`, the `.scenic` tokens and the `SCENIC_*` prefix — and **all 19
test files carry `import Scenic`**, so every one of them changes. The voice files
are directly in its path: `VoiceGuide.swift` has 3 occurrences of the old name,
`VoiceGuideTests.swift` 2, `VoiceCatalogueTests.swift` 1. Editing any of them now
produces a conflict in a change whose entire risk is that a brand string survives
a merge nobody re-reads. **Write one markdown file.**

**2. Do not renumber `docs/voice-guidance-plan.md`, and do not edit its design
sections.** Its own status line says the numbering is **load-bearing**: the
document "is cited by section from five files — `ios/project.yml`,
`VoiceGuide.swift`, `VoiceCatalogue.swift`, `LocationManagerTests.swift` and
`VoiceGuideTests.swift`". Verifying those five citations still point at the
sections they claim is worth doing; changing them is not.

**3. Never report a green iOS run as evidence about voice.** With both skips in
place the voice catalogue is untested and `** TEST SUCCEEDED **` is actively
misleading about it. If you run the suite, **state which suites were skipped and
say the voice catalogue went unverified** rather than passing.

**4. Never pipe `xcodebuild` through `tail` or `grep | tail`.** `tail` writes
nothing until its input closes, so a hung run and a slow one look identical — an
empty file for 15 minutes either way. Redirect to a log and read that. This is
exactly how the 13-minute hang stayed invisible. Also: `error:` is a bad grep
here — the simulator emits `CLLocationManager … did fail with error:` and
`[AXTTSCommon] … error:` on healthy runs.

**5. The plan's route measurements predate two rebuilds.** Its leg distribution
(455 legs, re-measured on a second sample of 194, median 507 m) was taken before
the land-cover merge changed `c_forest` and before A\* changed the fastest arm.
**Re-measure before repeating any of those numbers as current** — and if you
re-measure, note that `data/` lives only in the main checkout. Quoting a stale
distribution as though it were today's is the specific failure this project keeps
hitting.

**6. Do not drive, and do not simulate a drive as a substitute.** The
`SCENIC_DEMO` hook and a simulator location can exercise the code path; they
cannot test whether an instruction arrives in time to act on. Say which is which.

---

## Done looks like

1. **One new document**, `docs/voice-status.md` — not this brief's filename —
   added to `docs/README.md`'s index.
2. **Shipped-versus-designed, section by section.** For each numbered section of
   `voice-guidance-plan.md` that specifies behaviour: is it in
   `VoiceGuide.swift` / `VoiceCatalogue.swift` as designed, changed, or absent —
   with `file:line`. This is the `verify-plan-docs-before-building` discipline
   applied after the fact, and the plan is explicit that five files cite it by
   section, so the citations are checkable.
3. **A verified/unverified split.** What `VoiceGuideTests.swift`'s 506 lines
   actually cover, whether that suite currently passes, and what the permanently
   skipped `VoiceCatalogueTests` would have covered. Name the gap plainly.
4. **The `VoiceCatalogueTests` hang diagnosed to a fix, not fixed.** What
   `duration(of:)` needs in order to be testable without a live voice-asset
   fetch, which file the change lands in, and why it is deferred until the
   rename lands.
5. **A drive protocol for the first voice drive** — a short, specific list of
   what to listen for, tied to the plan's own decisions: whether the time-based
   schedule leaves enough warning, what the shared-utterance cases sound like in
   the car, whether mute and reroute behave, and whether anything arrives too
   late to act on. This is the deliverable the owner can actually use.
6. **An honest-answer escape hatch.** "Everything designed is present and the
   only real gap is that no drive has tested it" is a complete answer — say it
   in a line rather than padding it. Equally, if a design decision turns out
   *not* to have shipped as written, say so plainly with the `file:line`; that is
   the most valuable thing this task could find.
