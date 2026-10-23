# Brief: rewrite every customer-facing text for the national app

**Status: decided, not started.** Nothing has been changed. Branch off `usa`
(at or after `936dfcf`). This brief is temporary and is deleted in the merge
that brings the work back. **Your answer goes in `docs/national-copy.md`**:
every string changed (was → now), the measurements behind each number, and
what still needs the owner. Never append to this brief, and cite
`docs/national-copy.md` from code and tests.

## The goal

The binary on `usa` says "anywhere in the 48 contiguous states and DC". Every
text a customer, App Review or a repo visitor sees still describes a
six-state app. The 2026-10-23 outside review read them all against the app:

- `docs/app-store-listing.md` §1–3: "Every road in New England", "New England
  only. Routes and loops have to start and end in the six states". The
  keywords end `…new,england,vermont,maine,hampshire`, and four more terms
  are fall foliage.
- §6, the featuring nomination: "It launches for the last weekends of fall
  foliage, when New England is full of people…".
- `docs/app-store-submission.md` §5, the App Review notes: "Coverage is New
  England only", and a test trip of Concord, MA to Rockport, MA, measured on
  the New England server.
- All four captioned App Store screenshots are Concord / Boston. Screenshot
  1's caption reads "Every road in New England is scored for scenery".
- `site/index.html`, which is the Support URL: "in the six New England
  states", and a section headed "It says it only works in New England".
- `site/privacy/index.html` lines 64, 94 and 103 still describe "checking
  that you are in New England". Line 98 already quotes the new purpose string.
- The support page's data credits list OSM, WorldCover and Terrain Tiles. The
  app's Sources screen (`ios/Sources/AboutView.swift:208-246`) also credits
  PAD-US 4.1, USFS MVUM roads and NPS Public Roads, and INEGI for terrain in
  Mexico.

`docs/app-goes-national.md` §4 and §6 is the earlier inventory of the same
gap. Read it first: it lists the new in-app strings and what each outside
file needs.

Three small app fixes ride along, because the new screenshots would show
them:

- **The locate button sits under the status bar.** `MapUserLocationButton()`
  in `.mapControls` (`ios/Sources/PlanningMap.swift:77`) overlaps the battery
  and Wi-Fi icons on every planning screen, and in App Store screenshot 1.
- **The zero-gain trade headline reads like a gain.**
  `ios/Sources/RouteResults.swift:253`:
  `"Scenic adds **\(extraMinutes) min** and leaves beautiful road at \(to)"`.
  For Denver → Estes Park it said "Scenic adds 9 min and leaves beautiful road
  at 11 mi", which means nine minutes for nothing. Say that plainly, for
  example "Scenic adds 9 min for no more beautiful road". The wording is your
  call, in the app's voice: dry, no exclamation marks.
- **"What you'll pass" bars overlap without saying so.** Their miles summed
  to 108 on a 64 mi route, and 97 on 47 in screenshot 1. Label them as
  overlapping, or show shares.

One licence line rides along too:

- **ODbL §4.6.** `AboutView.swift:113-120` treats routes as a Produced Work,
  which is correct: no share-alike. But §4.6 still asks anyone who publicly
  uses a Produced Work from a Derivative Database to offer the database or
  "the method of making the alterations". The public repository is that
  method. Add one line and a link to it on the Sources screen, next to the
  OSM credit, and update the comment to say why.

## Decided

- **Positioning:** `docs/marketing-plan.md` §3.1 is decided. Use the subtitle
  *The scenic route, on purpose*, the one-liner "Every road in the contiguous
  US, scored for scenery on one scale", the loop hook and the honesty line.
  Every claim must pass §3.4's scope table.
- **Keywords:** start from §5.7's national candidate. **Drop the seasonal
  terms** (`foliage,fall,leaf,peeping`). The launch is in November, and
  seasonal terms belong on a custom product page later. Spend the bytes on
  non-seasonal national intent. No state names, nothing from the name or
  subtitle, no competitor names. It is **100 bytes**, not characters. Measure
  with `printf %s "<keywords>" | wc -c`, and record the count.
- **National mileage:** measured from the shipped build (`data/processed-us`),
  never estimated. Record how you measured it.
- **Review notes:** a reviewer in Cupertino is now *inside* coverage. Give a
  California directions trip and a California loop, measured on a local
  national server at this branch's HEAD, and the refusal someone outside the
  US sees. Name the production caveat in `docs/national-copy.md`, not in the
  notes: production serves the New England build until the owner deploys.
- **Screenshots:** retake the captioned set after the three app fixes are in.
  - At least two shots come from outside New England, in regions where the
    product is strong. Candidates the review measured: Big Sur (SF →
    Monterey, 0.9 → 119 km beautiful), Skyline Drive (Front Royal → Luray,
    6 → 55 km), Peak to Peak (Denver → Estes Park at full scenic, 11 → 65 mi),
    or a 2-hour Denver foothills loop (37 of 66 mi beautiful).
  - The hero trade should cost about 10–20 minutes, not the current +47 min
    on a 53-minute trip.
  - Lead the loop shot with a mostly beautiful loop.
  - No shot is half empty.
  - Captions use the app's own words (§3.2).
- **Marketing plan re-base** (`docs/marketing-plan.md` §7, §0 and §15):
  - The owner no longer sets target dates. Re-write the timeline relative to
    approval (S, then A, then L = the first Thursday after A plus the
    go/no-go), with no calendar dates except hard external ones: the domain's
    expiry, Thanksgiving, #30DayMapChallenge.
  - Add a **server gate before S**: the national server deployed on the box,
    routes answered from 10+ states, a latency monitor that plans a route,
    and the snap-cap fix deployed. App Review tests against production.
  - Add these to the go/no-go list: the server's region matches the app; the
    review notes; the privacy policy; the featuring text.
  - The featuring nomination's 22 October deadline has passed. Whether it was
    filed is unknown, so mark it for the owner.

## Traps

1. **Not every "New England" is wrong.** "Driven in New England only" in
   `BeforeYouDriveView` and the New England-scoped rating claims (§3.4: "96%
   liked at 7+" only as "on my own New England test drives") are true,
   deliberate and owner-approved. Scrub coverage claims. Keep scoped truths.
   Your "no New England" test therefore needs an explicit allow-list, with a
   reason per entry, not a blanket ban.
2. **Don't promise what the app doesn't do.**
   - Never write "beautiful wherever you are" or "scenic roads near you".
   - Never write "in flat country it tells you so". The low-scenery behaviour
     is an open owner decision and is not in the binary.
   - Never "best" or "most scenic". Compare only against the app's own
     fastest route, never against Apple's.
3. **The purpose string is pinned.** `tests/test_privacy_page.py` checks that
   the privacy page (`site/privacy/index.html`, `docs/privacy-policy.md`)
   quotes `NSLocationWhenInUseUsageDescription` in `ios/project.yml` exactly,
   and the prompt must not name the app (`LocationTextAndContactTests`).
   Change the page's surrounding text, not the quoted string. Add the launch
   camera as a use of location: on-device, nothing sent.
4. **The locate-button fix is a MapKit trap.** Inside
   `.ignoresSafeArea(edges: .top)`, SwiftUI reports a top inset of 0, so the
   map doesn't know the status bar covers it. Read the real inset from the
   parent, or from a view after the `ignoresSafeArea` modifier. Also, map
   content cannot cover Apple's logo or Legal link, which is a contract
   obligation. Check both in the simulator, on the small and the Max phone.
5. **Strings are pinned by iOS tests.** Grep `ios/Tests` for the trade
   headline and the bar labels before changing them, and update the tests to
   the new wording, not the other way round.
6. **Machine rules.**
   - Only one national server may run on this 24 GB Mac at a time. The
     snap-cap unit runs one too. Before starting yours, check
     `ps -axo pid,rss,command | grep '[s]erve.py'`. If a 2 GB+ one is
     running, wait for it to stop.
   - Stop yours by PID, never with `pkill`.
   - Make your own simulator, and delete it when you're done.
   - For drive screenshots, `simctl location set` fires once. Use
     `simctl location start` playback.
   - Point the app at your server with `SIMCTL_CHILD_` for `simctl launch`,
     or `TEST_RUNNER_` for `xcodebuild test`.
   - Never call Apple's or Google's directions services.

## Out of scope

- **Publishing anything.** Don't touch App Store Connect, the live site or
  the featuring form. The site goes live when `usa` reaches `main` and is
  pushed, and that is the owner's job.
- **The low-scenery fallback.** It is an owner decision. If it lands later,
  the trade-card screenshot may need retaking, so say so in the answer doc.
- The brand marks, Dynamic Type, and the name.

## Done looks like

1. The listing §1–3 and §6, the review notes, `site/index.html`, the privacy
   page and `docs/privacy-policy.md` describe the national app. Every number
   is measured and traced in `docs/national-copy.md`.
2. The keywords are 100 bytes or fewer, measured, and non-seasonal.
3. The support page's credits match the Sources screen.
4. A Python test fails on any New England coverage claim in the
   customer-facing files, except for allow-listed scoped truths.
5. The locate button clears the status bar, the zero-gain headline says
   "no more", and the bars say they overlap. The iOS tests that pin them are
   updated and pass.
6. The ODbL §4.6 line and link are on the Sources screen.
7. A new captioned screenshot set, with at least two shots outside New
   England, built with `app-store-screenshots/build.py`.
8. Marketing plan §7 is re-based with no target dates, the server gate is
   before S, and the go/no-go additions are in.
9. `docs/national-copy.md` lists everything the owner must sign off on: new
   claims, keyword choice, captions, and the featuring status.
