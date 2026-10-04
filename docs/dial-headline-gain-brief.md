# Brief: the dial's headline should print what the extra minutes buy

**Status: diagnosed and decided, not fixed.** Written 2026-10-04 against `main`
at `454e2cc`. No source file has been touched for this brief. This is
`pre-submission-review-verdict.md` C-3. Do not re-derive it.

## The symptom, measured

The planning screen's headline under the Fastest ↔ Scenic dial reads, for
Concord, MA → Rockport, MA at the default setting (production API,
2026-10-04):

> **+47 min · 13 mi of beautiful road**

The two cards just below it read **13 mi** (scenic) and **2 mi** (fastest). So
the minutes are a *difference* (scenic minus fastest), and the miles are the
scenic route's *total*. The extra 47 minutes buy **11** miles of beautiful
road, not 13.

Over the 983 shipped-default trips in `docs/route-census/census-routes.csv`
(verdict C-3, replayed with `isSameDrive` and the server's
`_no_worse_than_fastest` guard):
- 846 trips charge minutes;
- **61 (7.2%)** of those buy no extra beautiful road at all, and 15 have
  *less* beautiful road than the fastest route;
- **163 (19.3%)** print at least twice the real gain;
- on the typical 25–50 km trip, the median printed figure is 6 mi against a
  median gain of 3.

The worst real readouts were "+43 min · 10 mi of beautiful road" (the fastest
route has 11) and "+16 min · 0 mi".

## Why it matters

`interface-design.md` §4.3 calls this line "the only number that matters", the
price and the prize in one line. It is the headline of App Store screenshot 1.
The archived `beautiful-miles-and-the-slider-brief.md` had already settled the
principle, "turns 1 mi of beautiful road into 12", because only a phrasing like
that states the gain. The redesign reintroduced the total.

## The mechanism

`ios/Sources/DirectionsView.swift`, in `PrefDial.readout` (`:218-232`):

```swift
} else if let miles = c.beautifulMiles {
    (cost(c.extraMinutes)
     + Text(" · ").foregroundColor(.ink3)
     + Text("\(miles.scenic) mi of beautiful road").foregroundColor(.amberText))
```

The VoiceOver value has the same fault, in `PrefDial.spokenValue` (`:245-251`):
`"\(cost), \(CountText.of(miles.scenic, "mile")) of beautiful road"`.

Everything needed already exists in `RouteComparison`
(`ios/Sources/RouteResults.swift`, from `:100`):
- `beautifulMiles` is `(fastest, scenic)`, each rounded to whole miles
  separately.
- `beautifulMilesMove` and `isSameDrive` (`:190`) exist.
- `summary` (`:216`) already words every non-gain case honestly: "Scenic adds
  **N min** and leaves beautiful road at X mi", "A different route with the
  same…", "**cuts** beautiful road from A to B", and "… at no extra time".

## The decision (already made, do not reopen)

Past `isSameDrive`, with `beautifulMiles` present:

| Case | Headline |
| --- | --- |
| `miles.scenic > miles.fastest`, minutes > 0 | **`+47 min · +11 mi of beautiful road`** |
| `miles.scenic > miles.fastest`, minutes ≤ 0 | **`No extra time · +11 mi of beautiful road`** (`cost()` already prints "No extra time") |
| `miles.scenic ≤ miles.fastest` | the existing `RouteComparison.attributedSummary` sentence, in the readout's place |

- The gain is **`miles.scenic − miles.fastest`**, the difference of the two
  whole-mile figures the cards print (Trap 1).
- Keep the existing colours: the price in slate, the prize in amberText.
- The `isSameDrive` branch, the stale-state name branch and the older-backend
  branch are unchanged.
- **VoiceOver says the same thing:** "plus 47 minutes, 11 more miles of
  beautiful road". When there is no gain, it says the plain text of the
  summary sentence (Trap 3).

## Traps

1. **Compute the gain from the printed whole miles, not by rounding the km
   difference.** Concord → Rockport is 24.1 km against 2.0 km of beautiful
   road. Rounding the difference gives 13.7 mi → **14**, while the cards
   directly below print **13** and **2**. A headline that disagrees with the
   arithmetic of the two numbers under it is a new bug. Subtract the printed
   values.
2. **Never print "+0 mi", and never clamp a fall to zero.** On 3.1% of trips
   the scenic route has *less* beautiful road, and the code comments in
   `RouteComparison.summary` explain why that is stated plainly rather than
   hidden. Past `isSameDrive`, a gain ≤ 0 goes to the existing sentence.
3. **VoiceOver must change in the same pass, and must not read markdown.**
   - `spokenValue` today returns `c.summary` raw in its fallback, which
     contains `**` markers.
   - Use `String(c.attributedSummary.characters)` for the plain text.
4. **Do not touch `isSameDrive` or `beautifulMiles`.** Their definitions rest
   on a census; the comment at `RouteResults.swift:185-189` says redefining
   them needs a new one.

## Done looks like

1. The headline and the VoiceOver value follow the table above.
2. The choice is a small pure function or property, for example
   `RouteComparison.headlineGain: Int?` or a headline enum, so it can be unit
   tested without SwiftUI. Tests in `ios/Tests/RouteComparisonTests.swift`
   cover:
   - 13 vs 2 → `+11`;
   - a gain at no extra time;
   - equal miles with minutes added;
   - a cut;
   - the same drive;
   - a backend without `beautiful_km`.
3. The iOS suite is green, with no live-test failures (see the build note).
4. A simulator screenshot of Concord, MA → Rockport, MA against the production
   API, showing `+47 min · +11 mi of beautiful road`, or whatever the live
   numbers are that day. Put it in the session's report.
5. Committed on the session's own branch off `main`, not merged. App Store
   screenshot 1 gets retaken after the merge.

**Out of scope:** the loop card, which has no fastest route to compare against;
the slider itself; and any wording outside the readout and its VoiceOver
value.
