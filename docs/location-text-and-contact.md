# A complete location permission text, and contact from inside the app

**Status:** shipped — merged to `main` by `a2ddddc`. This is the part of the dispatch brief that outlived the work: its measurements, decisions and results. The brief itself, with its traps and done-list, was deleted on merge — `git show a2ddddc:docs/location-text-and-contact-brief.md` prints it. Section numbers and "below" refer to that brief's layout.

## The two gaps, against the App Review Guidelines (June 8, 2026 text)

### 1. The permission text describes one use of location, and the app has more

Guideline 5.1.1(ii): *"Ensure your purpose strings clearly and **completely**
describe your use of the data."*

The string is at `ios/project.yml:36`:

> Your location is used to follow the route, turn by turn, while you drive.

The system prompt usually appears first while **planning**, not driving:
- Home's Loop row calls `LoopModel.useMyLocation` (`HomeView.swift:40`), which
  calls `locationManager.currentLocation()` (`LoopModel.swift:153`).
- My Location in Directions does the same through `RouteModel.swift:207`.
- Both reach `requestWhenInUseAuthorization` when permission is undetermined
  (`LocationManager.swift:225-226`, then `:287`).
- Starting a drive asks too (`NavView.swift:100` and `:129` call
  `LocationManager.start()`, which reaches `:182`).
- **After the parallel brief lands, there is a fourth trigger:** the app asks
  once at first launch, right after the "Before you drive" notice, so that it
  can warn someone outside New England.

What location is actually used for:

| Use | Where it goes | Evidence |
|---|---|---|
| Planning a drive or loop from where you are | To the routing server, in a POST body | `RouteService.swift`; privacy page "Where your location goes", item 1 |
| Checking whether you are in New England | **Nowhere.** The parallel brief requires the check to run on the phone with no network call | `new-england-only-brief.md` §A and its trap 4 |
| Turn-by-turn guidance, including in the background with the blue indicator | Stays on the phone, apart from reroutes, which go to the server as above | `LocationManager.swift:195-196`; privacy page "Location" |
| Naming the start ("My Location" becomes a street) | To Apple, by reverse geocoding | `PlaceNaming.swift:45-46` (`CLGeocoder`); privacy page "Where your location goes", item 2 |

### 2. There is no way to contact the developer from inside the app

Guideline 1.5: *"Make sure your app **and** its Support URL include an easy way
to contact you."*

The Support URL page does this already. `site/index.html` lists
`support@jameskouvlis.com`, and `tests/test_support_page.py:41-42` asserts the
`mailto:` link.

The app does not. Its only outward link is the privacy policy
(`AboutView.swift:302-319`, URL constant at `:217-219`). The Sources screen is
reached from the pinned "Sources ›" credit line on every planning stage
(`PlanningView.swift:160-186`).

## The published privacy policy repeats the incomplete claim

The privacy policy repeats the claim, in three places:
- `site/privacy/index.html:90` says *"The app uses your location for one thing:
  following the route you asked for."*
- `:91` quotes the string above, verbatim, in a `<blockquote>`.
- The summary bullet at the top says *"Your location is used to follow your
  route."*

`docs/privacy-policy.md` §2 (`:84-90`) says the same, and cites
`ios/project.yml:21` for the string. That citation is stale: the string is at
`:36`.

**This is incomplete today, before any new feature.** Planning from where you
are is already a second use. Guideline 5.1.1(i) asks the policy to identify
"all uses of that data".

## What was decided (master session, 2026-10-04)

### A. The new permission text

> **Your location is used to plan drives from where you are, to check that
> you're in New England, and to guide you turn by turn.**

The owner may reword it. Whatever the wording, it must:
- name all three uses;
- **not name the app.** iOS already titles the alert *Allow "Sunday Drive" to
  use your location?*, and naming it in the body says it twice. That was
  decided on 2026-09-20 and is recorded in `docs/privacy-policy.md` §2;
- stay a single sentence that a driver reads in two seconds.

**Change only `NSLocationWhenInUseUsageDescription`.** Leave
`NSLocationTemporaryUsageDescriptionDictionary` (`ios/project.yml:42-43`, the
Precise Location prompt) exactly as it is.

### B. The privacy policy, in step

In `site/privacy/index.html` and `docs/privacy-policy.md` §2:
- Replace "for one thing: following the route you asked for" with the three
  uses.
- Say plainly that the New England check happens on the phone and sends the
  location nowhere.
- Update the blockquote to the new string, character for character.
- Update the summary bullet at the top of the page.
- Fix the stale `:21` citation.
- Move the page's "Effective date" to the day this merges.

"Where your location goes" stays at two places. The check adds no destination.

### C. The contact route

In `AboutView.swift`, add two rows right after the "Privacy policy" row, in the
same style: a 50 pt row on `Color.sunk`, with an `arrow.up.right` glyph.
- **"Help and support"** opens the support page,
  `https://jamesk1281.github.io/SundayDrive/`.
- **"Email the developer"** opens `mailto:support@jameskouvlis.com`.

Put both URLs in a small enum next to `PrivacyPolicy` (`AboutView.swift:217-219`).
Copy its warning: Pages does **not** redirect after a repo rename, so renaming
the repo breaks these links.

### D. Guards against drift

- **A Python test** in `tests/test_privacy_page.py` that reads
  `NSLocationWhenInUseUsageDescription` out of `ios/project.yml` and asserts
  that the privacy page's blockquote is exactly that string. This is the
  failure that just happened: the string and the policy describe the app
  differently, and nothing noticed.
- **An iOS unit test** that reads the string from the built bundle
  (`Bundle.main.object(forInfoDictionaryKey:)`, the pattern at
  `LocationManagerTests.swift:186-192`). It asserts the string is non-empty and
  does not contain "Sunday Drive". It also asserts the two new URL constants:
  the scheme, the host, and the address in the `mailto:`.
