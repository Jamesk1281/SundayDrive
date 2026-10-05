# Eight consumer-facing defects found by driving the app

**Status:** four of eight open as of the 2026-09-19 re-check — #3, #4, #5 and #6 (table below). Re-check against the tree before acting on one. This is the part of the dispatch brief that outlived the work: its measurements, decisions and results. The brief itself, with its traps and done-list, was deleted on merge — `git show a2ddddc:docs/consumer-polish-brief.md` prints it. Section numbers and "below" refer to that brief's layout.

Diagnosed 2026-08-29; four of the eight fixed by 2026-09-19.
Re-checked against the tree 2026-09-19 — **#1, #2, #7 and #8 are closed**, and
each item below now opens with its own state:

| | defect | state |
| --- | --- | --- |
| 1 | "HTTP 530" reaches the driver raw | **fixed** — `RouteService.swift:62-64` returns `.unreachable(status)` with a sentence around it |
| 2 | the comparison contradicts itself by a minute | **fixed** — `RouteComparison` owns both minute figures, so the cards and the sentence share one rounding |
| 3 | the compact sheet is shorter than its content | open |
| 4 | the start pin is centred behind the sheet | open |
| 5 | the verdict buttons are the least visible control | open — but the lines cited below, `NavView.swift:287-296`, are now `currentRoadLabel`; re-locate before acting |
| 6 | two overlapping location requests strand a task | open |
| 7 | "Switch to fastest" can do nothing at all | **fixed** — `NavView.swift:106-108` no longer no-ops on a nil fix |
| 8 | the loop tab never names the place | **fixed** — `LoopModel.swift:137,148` |

## 1. A backend outage reaches the driver as the text "HTTP 530"

**Observed.** `https://api.jameskouvlis.com` returns HTTP 530 (Cloudflare 1033,
tunnel down). Launched the app with the baked `ScenicAPIBaseURL`, tapped My
Location on the Loop tab, and the entire feedback was small red text reading
`HTTP 530` at the bottom of the sheet. Same for every `/api/route`.

**Mechanism.** `ios/Sources/RouteService.swift:126-131`:

```swift
if let http = response as? HTTPURLResponse, http.statusCode != 200 {
    let body = try? JSONDecoder().decode([String: String].self, from: data)
    throw ServiceError.server(body?["error"] ?? "HTTP \(http.statusCode)")
}
```

The comment above it already knows a tunnel answers in HTML rather than the
app's JSON shape. The fallback chosen is the raw status code. `RouteModel.computeRoute`
(`ios/Sources/RouteModel.swift:312`) and `LoopModel.fetch`
(`ios/Sources/LoopModel.swift:199`) both surface `error.localizedDescription`
verbatim.

**The fix.** Map the failure to something a driver can act on, in
`ServiceError`. Three cases, distinguished:

- The server answered with its own `{"error": ...}` — **keep passing it through
  unchanged.** These are good messages ("point is outside the covered road
  network", "no route found between those points", "those points are too close
  together") and losing them is a regression.
- The server answered with a status but no usable JSON (502/503/530, HTML from a
  tunnel or a proxy) — "The routing service isn't reachable right now. Try again
  in a moment." Keep the status code in the string only as a parenthetical, or
  drop it.
- The request never reached a server at all (`URLError`, thrown from
  `session.data(from:)` before the status check) — that is a *different* thing to
  tell someone: "No connection to the routing service. Check your network."
  Currently this path produces Foundation's own text, which is passable but
  inconsistent with the above.

Both `route(...)` and `loop(...)` duplicate the status-check block verbatim;
factor it into one private helper they both call.

## 2. The route comparison contradicts itself by a minute

**Observed on screen**, Needham → Rockport at the default preference: the cards
read `58 min` and `106 min`; the sentence directly beneath read
**"Scenic adds 49 min"**. 106 − 58 = 48.

**Mechanism.** `ios/Sources/RouteResults.swift:11` computes the delta from the
unrounded values:

```swift
let extra = Int((scenic.minutes - fastest.minutes).rounded())
```

while `card(...)` at line 31 rounds each one independently
(`Int(p.minutes.rounded())`). The API returned 57.6 and 106.4, so all three
roundings are individually correct and cannot all be true together.

**The fix.** Round once, up front, and derive everything from the rounded
values, so the sentence is arithmetic the reader can check:

```swift
let fastestMin = Int(fastest.minutes.rounded())
let scenicMin  = Int(scenic.minutes.rounded())
let extra      = scenicMin - fastestMin
```

Pass the rounded ints into `card(...)` too rather than letting it round again.
Also handle `extra <= 0` — at `pref` 0 the server returns the same route for
both, and "Scenic adds 0 min and raises scenery 4.4 → 4.4" is a sentence worth
replacing with something like "Same as the fastest route at this setting."

## 3. The compact sheet is shorter than its own content, on every launch

**Observed** on the first screen of every cold launch: `scenery preference 0.50`
is bisected by the sheet's bottom edge and overlapped by the home indicator. On
the Loop tab the placeholder paragraph is cut mid-sentence the same way.

**Mechanism.** `ios/Sources/RoutePanel.swift:7`:

```swift
static let planningCompact = PresentationDetent.height(260)
```

Measured content at default Dynamic Type is ~276 pt (padding 20 + header ~40 +
14 + segmented picker ~32 + 14 + field 44 + 14 + field 44 + 14 + slider ~40).
It clips before the user changes any accessibility setting, and worsens with
text size.

**The fix.** Make the resting height follow its content rather than a literal.
Either a `@ScaledMetric` height that grows with Dynamic Type, or
`PresentationDetent.custom` with a `ContainerValues`-derived height, or measure
the compact block once and drive the detent from it. Verify at the largest
accessibility text size, not just the default.

## 4. The start pin is centred behind the bottom sheet

**Observed** after choosing "Needham" as the start: the green pin sat clipped
against the sheet's top edge, and at the `.medium` detent it is fully covered.

**Mechanism.** `ios/Sources/ContentView.swift:93-96` (and the loop twin at
99-102):

```swift
.onChange(of: model.start?.latitude) {
    guard model.response == nil, let start = model.start else { return }
    withAnimation { camera = .region(.around(start, meters: 1_200)) }
}
```

`.around()` centres the point in the *whole* map rect while the sheet covers the
bottom ~44% at `.medium` — the detent the panel rests at once the user has
engaged with it. The comment two lines above says the camera moves precisely so
that "seeing the pin land on the right street is how you catch a bad fix before
pulling away", which a hidden pin defeats.

**The fix.** Lift the pin the way `frame()` already lifts routes — see the
`bottomLift` in `ContentView.swift:143`. Offset the region's centre north by
roughly 30–40% of its latitude span, or build a rect and reuse the existing
padding logic. Both `onChange` blocks need it; factor out one helper.

## 5. The scenery verdict buttons are the least visible control on the nav screen

**Observed** mid-drive over light map tiles: the thumbs-up/down glyphs sit in
near-transparent panels with map POI labels ("Beth Israel", "Needham Coin
and…") legible straight through them. Neither button carries any text.

**Mechanism.** `ios/Sources/NavView.swift:287-296` — an SF Symbol on
`.background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))`
directly over `Map`. "Lovely road" / "Nothing to see" exist only as
`accessibilityLabel`s.

**The fix.** Raise the contrast and say what they are: an opaque or
`.regularMaterial` background with a thin stroke, the glyph *and* its short
label side by side, and the accent tint carried on the "nice" side as it is
today.

**Do not move them.** The placement is deliberate and documented at
`NavView.swift:248-264`: hard against the screen edges because `tripStats` owns
the middle where a resting thumb lands, and above the row holding `End` so the
destructive control never sits beside the frequent one. Contrast and labelling
are in scope; layout is not.

## 6. Two overlapping location requests strand a task forever

**Mechanism.** `ios/Sources/LocationManager.swift:206-212`:

```swift
private func requestAuthorization() async -> CLAuthorizationStatus {
    await withCheckedContinuation { continuation in
        pendingAuth = continuation
        manager.requestWhenInUseAuthorization()
    }
}
```

`pendingAuth` is overwritten with no attempt to resume whatever was already
there. Two `currentLocation()` calls can overlap while the status is
`.notDetermined`: `RouteModel.useMyLocation` is invoked from
`Task { await model.useMyLocation() }` at both `RoutePanel.swift:211` and
`RoutePanel.swift:240`, and `isLocatingUser` — which drives the button's
`.disabled` — is set *inside* the Task body, not at tap time, so two quick taps
both get through. The first continuation is never resumed and that task hangs
for the life of the process (Swift logs `SWIFT TASK CONTINUATION MISUSE`).

`pendingFix`, 20 lines above at `LocationManager.swift:187-189`, already carries
the fix for exactly this bug, with a comment describing the same symptom
("Replacing `pendingFix` while its continuation was unresumed left that caller
suspended forever"). `pendingAuth` never got it.

**The fix — and the trap.** The obvious move, resuming the superseded
continuation immediately the way `PendingFix.finish` does, is **wrong here**.
At that instant the status is still `.notDetermined`, so the first caller
resumes, fails the `guard` at `LocationManager.swift:173-174`, and returns nil —
`useMyLocation` then shows "Couldn't get a location fix. Try again in a moment."
while the system prompt is still on screen. Instead hold *all* waiters (an
array of continuations) and resume every one of them from
`locationManagerDidChangeAuthorization`, which already has the
non-`.notDetermined` guard right.

`ios/Tests/LocationManagerTests.swift` exists — add the two-concurrent-callers
case there.

## 7. Confirming "Switch to fastest" can do nothing at all

**Mechanism.** `ios/Sources/NavView.swift:99-103`:

```swift
Button("Switch to fastest", role: .destructive) {
    if let here = locationManager.location {
        Task { await nav.switchToFastest(from: here) }
    }
}
```

No `else`. `locationManager.location` is nil until a fix passes `isUsable`
(accuracy ≤ 65 m, age ≤ 15 s) — a cold start in a garage, an urban canyon, or
location denied. The driver taps the bolt, reads "This gives up the scenic route
for the rest of the drive", confirms, and nothing changes: line still green,
button still there, no message. This is the control someone reaches for when the
scenic route has gone wrong, so a silent no-op is the worst outcome available.

**The fix.** Surface a message on the nav screen when there is no usable fix —
`NavigationModel` already owns a user-visible diagnostic channel in
`recordingProblem`, but that one means something else, so add a separate
transient string rather than overloading it.

**Trap: do not fall back to `nav.lastFix` or to a stale `CLLocation`.**
`switchToFastest` reroutes *from* the location it is handed, and the entire
reason `isUsable` exists (`LocationManager.swift:10-15`) is that a cached
Wi-Fi-derived fix puts the driver a street or two from where they are. Rerouting
from a bad fix is worse than refusing.

## 8. The loop tab never names the place it put you, and duplicates the code that would

**Observed**: the loop start field reads `My Location` and stays that way, where
the directions tab becomes `My Location · Highland Ave, Needham`.

**Mechanism.** `ios/Sources/LoopModel.swift:130-134` sets
`startQuery = "My Location"` and stops. `RouteModel` does the extra work in
`nameCurrentLocation` (`RouteModel.swift:185-195`) and `displayName`
(`RouteModel.swift:324-331`), both file-private, so `LoopModel` cannot reach
them. `LoopModel.resolve` at line 104 also uses a bare `match.name ?? label`
where `RouteModel` uses `displayName`, so the loop tab shows "Main Street" where
directions shows "Main Street, Needham".

The justification for the extra geocode is in `RouteModel.swift:183-184` —
"'My Location' on its own gives the driver no way to notice we've placed them on
the wrong road" — and it applies harder to a loop, whose entire shape is derived
from that one point with no destination to sanity-check it against.

**The fix.** Move `displayName(for:fallback:)` and the reverse-geocode into a
new `ios/Sources/PlaceNaming.swift` as internal (not private) helpers, and call
them from both models. Touch `RouteModel.swift` only to delete the two private
functions and call the shared ones — that keeps the diff away from the
`weights` dictionary, which the driver-preferences session owns.

**Trap:** `nameCurrentLocation` guards `startQuery == "My Location"` *and*
`start?.matches(fix.coordinate) == true` before applying the result, because the
user can change the start while the geocode is in flight. The shared version
must keep both checks, and `LoopModel` — which has no such guard today — needs
them too.

**Second, smaller reuse item.** `RoutePanel.myLocationButton` +
`suggestionList` (`RoutePanel.swift:207-283`) and
`LoopPanel.myLocationButton` + `suggestionList` (`LoopPanel.swift:81-143`) are
~60 near-identical lines each, already drifted (the loop version has no `role`
parameter and a slightly different accessibility label). Extract one
`PlaceSearchField` view used by both. This is optional if it makes the diff
unreviewable; say so rather than doing it badly.

---
