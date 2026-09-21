# The interface, designed again

**Status: built.** Drawn 2026-09-20 against `main` at `d11344d`
(`docs/interface-design-brief.md` is the commission) and **implemented the same
day** at the owner's instruction. `PlanningView.swift`, `HomeView.swift`,
`DirectionsView.swift`, `LoopView.swift`, `NavView.swift`, `ArrivalView.swift`,
`BeforeYouDriveView.swift`, `PlanningMap.swift`, `PlaceField.swift`,
`Recents.swift` and `Theme.swift` are this document; `RoutePanel.swift` and
`LoopPanel.swift` are gone. 241 iOS tests pass and every screen below has been
run on a booted iPhone 17 Pro. **Two claims here were falsified by building
them** and are corrected in place, marked **Measured** — §2.3 and §4.3. The drawn
version is in [interface-design-mockups.html](interface-design-mockups.html),
which opens offline in any browser; where it and the code differ, the code is
right.

---

## 1. The idea

**The trade is the interface.**

Every other navigation app answers one question — *how do I get there* — and
treats the answer as a fact. This app answers a different one, and the answer is
a *choice the driver makes*: how much of my afternoon am I willing to spend on
a better road. That choice is the product. It is currently rendered as a stock
`Slider` with the caption `scenery strength 0.25`, which is the number the
router uses, printed at the person paying for it.

So the whole planning side is built around making that trade visible, priced,
and reversible, and the whole driving side is built around one promise: *you
chose this, and here is the road you chose.*

And for the layout: **a page, not a drawer.**

---

## 2. Why the drawer has to go, and what replaces it

### 2.1 The defect

`ContentView.swift:103` presents `RoutePanel` with `.sheet(isPresented:
.constant(true))` over a full-bleed `Map`, at three detents, permanently,
starting at `.planningCompact` on every cold launch. Apple's map logo and legal
link are drawn in the bottom-left of the map view. The sheet is opaque and
spans the bottom of the screen at every detent. The logo is therefore covered
at every detent. ADPLA Attachment 6 §2.1 requires it visible; §4 makes
obscuring it grounds for revoking MapKit access.

This is not a margin problem. A `.sheet` is a separate presentation layer: the
map underneath has no idea it is there, so MapKit cannot lay its attribution out
around it. That is the mechanical reason the breach exists, and it is why
"raise the detent a bit" is not a fix — every detent is above zero.

### 2.2 The rule I am designing to

> **The bottom-left of every map belongs to Apple.**
> On whatever view MapKit is rendering into, the bottom-left **≈150 × 44 pt** is
> a keep-out: nothing opaque, nothing tappable, nothing that scrolls over it.

It appears as a hatched zone in every mockup that contains a map. I have drawn
Apple's attribution as a grey placeholder pill reading `Maps  Legal` rather than
reproducing Apple's logo mark in a document — the shape and the reserved space
are the point, and the real thing is drawn by MapKit.

### 2.3 Two applications of one rule

**Planning: the map is a card, not a canvas.** The planning screen is a
scrolling page whose first element is an inset, rounded map. Apple's attribution
sits inside that card's bottom-left, on the map, with nothing over it — by
construction, at every scroll position, at every text size. The page below the
card is the app's own surface and can hold whatever it likes.

**Driving: the furniture floats, and the tail of the map is clear.** The map is
full-bleed. Every control sits in a floating card with a margin all round, and
the bottom **48 pt above the safe-area inset** is empty. On a heading-up
navigation map, the bottom of the screen is the road *already driven* — the
least valuable pixels on the display, so reserving them costs nothing.

I expected a second, independent protection here: that because the furniture is
composed with `.safeAreaInset` on the `Map` rather than presented as a `.sheet`,
MapKit would lay its attribution out inside the reduced safe area and lift the
logo above the furniture by itself.

**Measured, on a booted iPhone 17 Pro: it does not.** With `.ignoresSafeArea()`
on the `Map` and the controls added back through `.safeAreaInset(edge: .bottom)`,
MapKit draws the logo and the legal link at the bottom-left of the *full-bleed*
view — about 42 pt up from the screen's bottom edge, inside the reserved strip,
underneath the trip card rather than above it. The belt did not hold. **The
reserved strip is the only thing protecting the logo on the driving screen**,
which makes `Metric.appleKeep` load-bearing rather than belt-and-braces and its
48 pt a number not to trim. Screenshot and read the logo after any change to the
driving screen's furniture.

The planning side is unaffected either way: there the map is a bounded card and
the page starts underneath it, so the corner is protected by geometry and not by
a framework behaviour that has now been observed to differ from the obvious
reading of it.

### 2.4 What rejecting the drawer buys, beyond compliance

- `PlanningCompactDetent` (`RoutePanel.swift:84–170`) goes away. It is 87 lines
  of custom detent solved from two measured screen heights, because the compact
  block outgrows any constant as Dynamic Type scales, and at AX5 it measures
  884 pt on an 852 pt screen — *no detent can show it*. A scrolling page has no
  such failure mode; it simply gets longer.
- The `onChange(of: focused)` dance at `RoutePanel.swift:238` — nudge the detent
  rather than assign it, or UIKit keeps a stale hit-test frame and the top half
  of the sheet silently stops taking taps — has nothing to be about.
- The bug that produced it ("the panel closes itself the instant an address is
  set") cannot recur.
- The map stops being something the sheet has to be framed *around*:
  `ContentView.frame(_:)` pads the route's bounding rect downward by
  `max(h*1.4, w*0.9)` to lift it clear of the drawer. With a map card, the route
  is fitted to the card, and the multipliers are 1.0.

### 2.5 The alternatives I rejected

**Keep the sheet, inset the map's layout margins.** Possible in UIKit
(`MKMapView.layoutMargins` moves the legal label), not available through
SwiftUI's `Map`, and it would mean bridging to `UIViewRepresentable` — which
spends the project's zero-dependency discipline on a workaround rather than on
the product.

**Keep the sheet, move the logo to the top.** MapKit does not offer this.

**A tab bar.** Two tabs for planning and driving is wrong: driving is not a
place you navigate to, it is a state the app enters. A tab bar also permanently
occupies the bottom of the screen, which is the corner in dispute.

**A full-screen planning view with no map at all.** Tempting — the search is
textual and the numbers are the decision. But the shape of the line on the
ground is the single most persuasive thing this app can show, and "does that go
where I think it goes" is a real question. The card keeps the map at the size
its job actually needs.

---

## 3. Information architecture

```
                      ┌──────────────────────────┐
     cold launch ───▶ │  THE PAGE   (parked)     │
                      │                          │
                      │  ▸ Directions  ──────────┼──▶  set the ends  ──▶  THE TRADE
                      │  ▸ Loop        ──────────┼──▶  THE LOOP
                      │                          │
                      │  what you like  (sheet)  │
                      │  sources        (sheet)  │
                      │    └ before you drive    │
                      └───────────┬──────────────┘
                                  │  Start driving
                                  ▼
                      ┌──────────────────────────┐
                      │  THE DRIVE  (moving)     │
                      │   full-bleed, floating   │
                      │   furniture, glanceable  │
                      └───────────┬──────────────┘
                                  │  arrive / end
                                  ▼
                            THE ARRIVAL CARD  ──▶ back to the page
```

Two surfaces with different physics. **The page** scrolls, is dense, is read at
rest, and uses the full type scale. **The drive** does not scroll, holds five
things, and uses three type sizes. They share a map and nothing else — not a
layout, not a density, not a set of controls. Today they share a sheet as well,
and the sheet is the thing that makes planning cramped and driving crowded.

One modal idiom throughout: a sheet with a navigation bar and a Done button,
which is the idiom the app already has (`TuneView`, `AboutView`). Sheets are
used only for the two things that are genuinely aside from the flow — *what you
like* and *sources* — never for the flow itself.

---

## 4. The page, screen by screen

### 4.1 Cold launch — directions or a loop

Every navigation app opens with a destination field. This one should not, because
one of its two products has no destination. Loop mode today sits behind a
segmented control (`RouteModel.swift:19`), inside a sheet, below a destination
field it does not use.

So the first screen offers both, as two rows:

> **Directions** — "Search for a destination"
> **Loop** — "From here, about 1 hr 30 →"

**The second is a single tap to a finished drive.** It uses the current
location and the last duration and returns a loop. No form. That is the true
shape of the feature and it is currently four interactions away.

Above them, the map card, framed on where you are. Below them, recent
destinations if there are any — a new, small persistence (five entries in
`UserDefaults`, the same mechanism `VoiceCatalogue.swift:118` already uses for
the chosen voice); nothing is stored today, and a nav app that forgets where you
went last Sunday is making you retype it.

No headline above them. The two rows say what they are, and a greeting line
would be the most prominent thing on a screen whose job is to get out of the way.

### 4.2 Setting the ends

Two fields, a coloured dot each, live autocomplete beneath the focused one, and
a `My Location` row on top of the start's list. That much the app already gets
right (`RoutePanel.swift:343–458`), including the `contentShape(Rectangle())`
lesson that a suggestion row's empty half has to be tappable.

What changes:

- **The map card shrinks while you type** and grows back when a route lands.
  The keyboard takes the bottom half of the screen; a page can give it that
  space by scrolling, and the card animates down to a 120 pt strip rather than
  being covered.
- **Swap and clear move to the field rows**, where their objects are, instead of
  living in a header with the hint text (`RoutePanel.swift:302–325`).
- **The hint text goes.** Four states of instructional prose in the most
  prominent line of the screen is a caption for a UI that needs one. The
  redesigned screens name themselves.

### 4.3 The trade — the screen the app is for

This is the one that matters. In order down the page:

**1. The trip**, small: `Needham → Rockport`, tap to edit.

**2. The dial.** A track from *Fastest* to *Scenic*, and directly beneath it,
large, the only number that matters:

> **+18 min · 19 mi of beautiful road**

That is the price and the prize in one line, in the driver's units. It replaces
`scenery strength 0.25` (`RoutePanel.swift:484`), which is the router's internal
parameter shown to a person who has no way to know what it buys.

The handle's *position* still maps to the router's `strength`, exactly as
`PrefSlider` (`RoutePanel.swift:52–65`) already does — `pref = sqrt(position)`,
so every quarter of the travel does comparable work and `0` and `1` survive the
round trip bit-for-bit. **That mathematics is not up for redesign; it is
measured, and it is right.** What changes is only what the caption says.

**While the figures are stale the readout shows a name, not a number**, because
the route has not been recomputed and any number would be a lie for as long as it
is on screen. It shows the name of the region of the track the handle is in —
*Direct · A little scenic · Scenic · Most scenic* — and resolves to the real
figures when the response lands.

**Measured.** The first implementation keyed this on the slider's own
`onEditingChanged`, which is the obvious way and is wrong twice. It latched: on a
drag whose end-of-edit callback did not arrive, the caption stayed on the name
with the correct figures sitting in the ledger directly beneath it. And even
working, it covered only the gesture and not the request in flight *after* the
finger lifts — so for the second the route takes to come back, the old figures
were shown as though they described the new setting.

What shipped asks the question of the data instead: `RouteModel.responsePref`
records the `pref` the response on screen was computed at, and `routeIsStale` is
`isLoading || responsePref != pref`. That is exactly *is what is drawn the answer
to what is being asked*, it depends on no callback, and it closes the in-flight
gap the gesture version could not see.

**3. The ledger.** Three columns; the big figure is this drive, the small grey
figure beneath it is the fastest route.

```
   76 min          51 mi          19 mi beautiful
   58 fastest      44             4
```

The comparison becomes a subscript rather than a second card. Today it is two
equal-weight cards plus a sentence (`RouteResults.swift:14–26`), and the two
cards imply a choice between two products — but the fastest route is not a
product here. **You cannot start it.** It is the reference price, and it should
be typeset like one. (If a driver wants it, the dial's left end *is* it, exactly:
`server/app.py` short-circuits at `pref == 0`.)

The sentence under the cards goes. `RouteComparison.summary` is careful, correct
prose covering five cases — including the 3.1% of trips where the scenic arm is
slower *and* has less beautiful road — and all five are visible in the ledger
without prose, because both numbers are on screen with their comparison
underneath. The one case that still needs words is the degenerate one, and it
replaces the ledger rather than annotating it: **"Same as the fastest route at
this setting."**

**4. What you'll pass.** The scenery breakdown, one row per type, each with its
own colour (§7.3) — and those colours are a legend, because the same six hues
tint the route line on the map card. Today the bars are all one green
(`RouteResults.swift:226`), which makes them a bar chart of unrelated
quantities rather than a key to the drawing above.

*Dependency:* colouring the line by dominant scenery type needs a per-vertex
score from the API, which it does not return. §12. The bars are coloured either
way; without the field the line is plain amber and the colours are decorative.

**5. What you like** — one chip, which states its own value: `No preference`, or
`Coast & water · no towns`. Today this is a `Tune` button (`RoutePanel.swift:310`)
tinted when active, which tells you that *something* is set but not what.

**6. Start driving** — pinned to the bottom of the page above the credit line,
full width, amber. One primary action. `Start scenic drive` is three words
longer and one of them is redundant at the bottom of a screen about scenic
routes.

**7. The credit line** — always visible, never scrolls. §8.

### 4.4 The loop

One field (where from), one dial (how long), and the loop.

**The dial reads in time, not distance.** Today it is 5–200 km with the caption
"about 25 miles" (`LoopPanel.swift:151–166`). The request is a distance; what a
driver has is a span of time. The request still goes to the API in kilometres, because
that is what `/api/loop` takes; the label converts, and — the part that keeps it
honest — **the conversion factor is the km/minutes ratio of the last loop the
server actually returned**, not a constant. The app calibrates its own estimate
from its own results, with no backend change. The estimate is marked as one
("about 1 hr 30 · 48 mi") and is replaced by the truth the moment the loop
arrives.

The result is one card, and it leads with the thing loops are for:

> **1 hr 34 · 51 mi**
> **33 miles of it beautiful**
> heading northwest · no road driven twice

`repeated_km` stays always-visible as it is today, and rightly: it is the one
number that tells a driver their loop is really an out-and-back. It just stops
being orange, which in this palette means an alert (§7.2) — it becomes a plain
line with a symbol, and only turns red past `repeatedFraction > 0.15`.

Then **Try another direction (5)**, which already names how many there really
are rather than implying endless variety, and **Start driving**.

### 4.5 What you like

The six-type sheet, largely as it is — this screen is already good. Three
changes:

- It is titled **What you like**, and its one instruction stays: *"Drag toward
  what you'd rather drive past."*
- Each slider carries **its type's colour** (§7.3), so the sheet, the breakdown
  bars and the map all speak one language.
- The **Town centers** note stays visible and stays honest ("Off by default —
  drivers rated built-up stretches worse than the score predicted"). It is the
  best single sentence in the current interface: a product admitting to a
  measurement that went against it. It should be the model for the app's voice,
  not an exception to it.

### 4.6 Sources, and Before you drive

Two screens, one sheet. §8 and §9.

---

## 5. The drive

Five things, in priority order: **the next maneuver**, **am I nearly there**,
**this road is lovely / this road is dull**, **where am I now**, and **get me
out of this**. Everything else is a diagnostic and belongs below the fold of
attention.

### 5.1 The banner

Top of the screen, floating, **opaque**. A glyph, the distance, the instruction,
and the mute control.

Opaque is a change and it is the important one. The banner is
`.ultraThinMaterial` today (`NavView.swift:164`). The codebase has already
learned this lesson once, one screen down: the verdict buttons were moved to
`.regularMaterial` because *"`.ultraThinMaterial` over a `Map` is not a
background, it is a tint: mid-drive over light tiles the POI labels underneath
('Beth Israel', 'Needham Coin and…') read straight through"*
(`NavView.swift:387–393`). The same is true of the maneuver banner, and the
maneuver banner is the one element on this screen that a driver reads at 50 mph
in direct sunlight. It gets ink, not glass.

Type: **SF Pro Rounded**, 28 pt bold for the instruction, 20 pt for the
distance. Rounded because it is measurably easier at a glance and because it is
free.

`pointsOfInterest: .excludingAll` on the map while driving, so the basemap stops
competing with the route line for the brightest thing on screen.

### 5.2 The two buttons

They stay, they stay big, they stay paired, and they keep their words — a
thumbs-down alone on a map reads as "hide this" as easily as "dull road", which
the current code already says. They move to a floating pair above the trip card
with a margin, not hard against the screen edges, so the keep-out below them is
unbroken.

The haptic difference (`success` for nice, `warning` for dull) is the
confirmation and it stays. The small count beside the ETA stays too, for drivers
with haptics off — it is a receipt, and receipts are worth their pixels.

**An honest tension, named:** in a US car with a centre windscreen mount, the
driver's right hand approaches the phone from the lower left. The most reachable
corner of this screen is the one the licence reserves. I have put the two
buttons low and wide rather than in that corner, and accepted a slightly longer
reach, because the alternative is a contract breach. It is the only place in
this design where the compliance constraint costs the driver something real, and
it is worth about 15 mm of reach.

### 5.3 The trip card

One floating card, below the buttons, above the keep:

```
  ✕        ● 4:52 PM  3        ⚡
        22 min · 11.4 mi
           Essex Ave
```

ETA centred and largest, because it is the number a passenger asks for. Time and
distance remaining beneath it. The current road as a caption — the opposite
question from the banner's, and rightly quieter. End at the left, the
fastest-route escape at the right, both small, both in corners, both away from
where a resting thumb lands. That geometry is already right in `NavView`
(`controlRow`, and the `Color.clear` spacer that stops the stats shifting when
`Fastest` disappears) and I am keeping it.

The recording dot stays. A drive is unrepeatable and silence looks exactly like
working.

**End gets an undo, not a confirmation.** Tapping it ends the drive and shows
`Drive ended · Resume` for five seconds. A modal confirmation on a moving
vehicle is worse than a reversible mistake.

### 5.4 The arrival card

The app is called what it is called. When a drive finishes, it should say what
the drive was:

> **Rockport**
> 51 miles · 1 hr 14
> **19 of them beautiful**
> HOW WAS THE ROAD?  ·  Lovely · Not really

New, and it earns its place three ways: it closes the promise the trade screen
made; it gives a driver who marked nothing a single chance to mark the whole
drive, which is free calibration data; and it is the moment the product's name
is about — without the name appearing anywhere (§10).

`"You've arrived 🎉"` in the banner (`NavView.swift:121`) is replaced by this.

---

## 6. Motion

Four places, and nowhere else. All respect Reduce Motion.

1. **Numbers roll, they do not cut.** `contentTransition(.numericText())` on the
   ledger, the dial readout and the ETA. The trade screen's whole job is showing
   a number change in response to a gesture; a cut hides the change.
2. **The map card grows and shrinks** between stages of the flow, with the route
   fitted to its new size in the same animation. `withAnimation { camera = .rect(…) }`,
   which the app already does.
3. **The page-to-drive transition** is the one big move: the card unfolds to
   full bleed, the page falls away downward, the banner drops in. It is the only
   modal change of state in the app and deserves to feel like one. 0.4 s.
4. **Haptics on the two marks**, differentiated, as today.

No launch animation, no splash, no confetti at arrival. An app you open in a car
park should be usable in the first 300 ms.

---

## 7. Colour, type and dark mode

### 7.1 The idea

The app is about a trade between two quantities. **Give each quantity a colour
and never let them swap.**

- **Time** is slate — cool, quiet, unglamorous. Choosing fast is not celebrated.
- **Beauty** is amber — warm, low, late-afternoon.

Route lines, ledger columns, dial ends, bars, the arrival card: the same two
colours mean the same two things everywhere, so the trade is legible before a
single word is read.

### 7.2 The palette

|  | light | dark | used for |
| --- | --- | --- | --- |
| Paper | `#FBF8F3` | `#121110` | page background |
| Card | `#FFFFFF` | `#1C1A17` | raised surfaces |
| Hairline | `#E6DFD4` | `#2E2A25` | rules, borders |
| Ink | `#1A1713` | `#F3EFE8` | primary text |
| Ink-2 | `#6B6459` | `#A8A096` | secondary text |
| Ink-3 | `#7C7568` | `#857D72` | captions, the credit line |
| **Amber** line | `#E07B2E` | `#F09A4B` | the scenic route, fills |
| **Amber** text | `#A5541A` | `#F0A462` | beauty figures, primary button |
| **Slate** | `#5C6771` | `#9AA3AB` | the fastest route, time figures |
| Alert | `#B3352C` | `#E5675C` | off-route, destructive, real trouble |

Every text pairing above clears 4.5:1 against its background.

### 7.3 The six scenery hues

Mid-chroma, distinguishable, used in the breakdown, the *what you like* sliders
and (given §12's field) the route line.

`coast #2F7E8C` · `forest & parks #2F8A63` · `lakes & rivers #3D6BA8` ·
`hills #7A6A9E` · `farmland #A8903C` · `town centers #8A7F74`

### 7.4 On replacing the green

`Color.brand` is `rgb(0.22, 0.83, 0.62)` = `#38D49E` (`Theme.swift:10`), and the
brief is right that it is the only visual equity the project has. I am proposing
to move it anyway, for one reason that is about the map rather than about taste:

**a mint-green line has to survive on a basemap whose parks, forests and golf
courses are green.** That is the exact surface this app routes across, and the
scenic line is the single most important mark it draws. Amber sits opposite the
basemap's greens and blues on the wheel, holds up in direct sun at mid
luminance, and is not Apple's directions blue — so the line reads as *ours* and
reads as *a route*.

The green is not thrown away. It is **demoted to the thing it literally names**:
`forest & parks` in the six scenery hues, deepened to `#2F8A63` so it works as
text. The equity survives where it is descriptive instead of decorative, which
is the same move the project already made with the word *scenic* (§10).

**The cost, stated:** amber in a car is near the caution family. I have answered
that by going burnt and marigold rather than safety-yellow, by reserving a
distinct red for every genuine alert, and by a rule with no exceptions —
**amber never means warning anywhere in this app.** That rule has a consequence
worth naming: today `.orange` carries three unrelated meanings — the off-route
readout, the "doubles back" figure, the recording fault. Under this palette the
first and third become red and the second becomes plain ink. That is an
improvement regardless of the brand colour; three meanings on one hue was
already one too many.

### 7.5 Type

Two system faces, no dependency.

| role | face | size |
| --- | --- | --- |
| Hero number (arrival, ledger) | **SF Pro Rounded** Semibold | 28–40 |
| Driving instruction | **SF Pro Rounded** Bold | 28/32 |
| Title | SF Pro Semibold | 20 |
| Body | SF Pro | 17 |
| Caption | SF Pro | 13 |
| Label (small caps, tracked) | SF Pro Semibold | 11 |

**SF Pro Rounded is for figures and for the driving instruction, nowhere else.**
Everything a user reads as prose is SF Pro. Two faces with one rule between them
is enough; an earlier draft added New York for a few editorial lines, and the
lines it invited were the problem rather than the face.

Every figure that changes is `monospacedDigit()`. Metrics: 20 pt page margin
(the app's existing value), 12 pt gutter, radii 18 (card) / 14 (control) /
999 (pill).

### 7.6 Dark is the default

**The app ships dark**, whatever the system setting is —
`.preferredColorScheme(.dark)` at the root, with one switch in Sources,
*Match system appearance*, for anyone who wants otherwise. Three reasons:

- A phone in a windscreen mount is a light source pointed at the driver. Dark is
  the correct default for the half of the product used in a moving car, and the
  planning half is used minutes before it, in the same car.
- MapKit's dark basemap is where amber separates best: against `#23262A` ground
  and `#16394F` water, `#F09A4B` is the brightest thing on screen by a wide
  margin, which is what a route line should be.
- Most driving happens at the two ends of the day. Following the system means the
  app is light at 4 p.m. and dark at 6 p.m. on the same drive; picking one and
  holding it is steadier than being right half the time.

**The honest cost:** in direct midday sun, light-on-dark is harder to read than
dark-on-light, so the default is wrong for the brightest hour. That is what the
switch is for, and it is why the driving furniture is opaque rather than glass,
why its type is Rounded and large, and why nothing on that screen is lighter than
Medium.

Light mode is fully designed, not a fallback: paper is a warm off-white, amber
darkens to `#A5541A` for text, slate drops to `#5C6771`. Dark is not an inversion
of it — amber *brightens* to `#F09A4B` because a dark surround makes mid-amber
muddy, and slate lifts to `#9AA3AB`. The map follows the app rather than the
system, so the two never disagree on one screen.

### 7.7 Dynamic Type and VoiceOver

The page scrolls, so large text lengthens it and nothing is cut — which is the
whole class of defect `PlanningCompactDetent` exists to fight. On the drive,
sizes are `@ScaledMetric`, the banner wraps to three lines before it truncates,
and the two marks keep `minimumScaleFactor(0.7)`.

The dial is an `.adjustable` accessibility element whose value is spoken as the
outcome, not the position: *"plus eighteen minutes, nineteen miles of beautiful
road"*. The ledger is one element per column, read as "seventy-six minutes,
fastest is fifty-eight". The scenery bars keep their existing combined label.

---

## 8. The credit line, designed

The ODbL and the OSMF guideline require that attribution be *"presented to
anyone who uses, views, accesses, interacts with"* the work, in a format that
*"should not require individuals to interact with the map or produced work to
see"* it. A credits screen one tap away is the supplement the guideline names,
not a substitute for the visible line.

So the line is not moving anywhere. What I am proposing is that it stop looking
like a disclaimer and start looking like a **colophon** — because on this
product it is one.

> ```
> ─────────────────────────────────────────────
> MAP DATA FROM OPENSTREETMAP              Sources ›
> ```

Pinned to the bottom of the page, outside the scroll view, present at every
state and every scroll position. Set in the small-caps label style (SF Pro
Semibold 11, tracked, Ink-3) above a hairline — the same treatment the design
uses for every section label, so it reads as part of the typographic system
rather than as fine print someone was made to add.

`DataSources.shortCredit` is unchanged: **"Map data from OpenStreetMap"**,
including the qualification, which the guideline explicitly invites and which is
not decoration here — the basemap under the route lines is Apple's, and an
unqualified "© OpenStreetMap contributors" over an Apple basemap would credit
OSM for Apple's work. The existing implementation note at
`RoutePanel.swift:489–509` makes this argument already and makes it correctly.

Two details carried forward from that implementation, because they were learned
the hard way and a redesign that dropped them would be a regression:

- **One concatenated `Text`, not two side by side.** At accessibility sizes, a
  credit and a link in separate columns each wrap inside their own column —
  four lines to say one thing. Joined, it reflows as one paragraph.
- **The row is allowed to grow.** It is a licence credit; the guideline asks
  that it stay legible. Truncating it is not an option available to us.

**On the driving screen there is no credit,** and that is deliberate and
defensible: a route must be planned on the page before a drive can start, so the
credit has necessarily been on screen first, and the guideline is explicit that
attribution shown at startup *"does not need to be presented to the user every
time the user looks at or interacts with the application"*. The existing code
reaches the same conclusion for the same reason, and I am not disturbing it.

Where the redesign *adds* something: the **Sources** screen becomes a screen
worth reaching. It currently lists four datasets, their verbatim credits, their
licences and their links, which is exactly right and I am changing none of the
strings. What it gains is the design's own section labels, the six scenery hues
against the sources that produce them, and — most usefully — the sentence that
tells a reader why they are looking at this at all: *the roads on this map, and
the scores they are rated with, come from open data.* That sentence exists today
(`AboutView.swift:216`). It should be the largest thing on the screen, not the
smallest.

---

## 9. The safety notice, designed

The string is fixed by contract (ADPLA §3.3.3(F)(iii)), it is pinned character
for character by two tests (`AttributionTests.swift:149` and `:158`), and it must
appear exactly once:

```
YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK.
LOCATION DATA MAY NOT BE ACCURATE.
```

Today it lives under a `SAFETY` heading at the bottom of the credits sheet
(`AboutView.swift:231–236`), which is correct, compliant, and read by nobody. A
clause that protects a driver and is filed where drivers never look protects
nobody — the code comment says as much itself.

**The proposal: give it its own screen, called `Before you drive`, shown once on
first launch and reachable for ever after from Sources.** One view, one copy of
the string, two ways in.

That screen holds the notice, and then what the app does not do:

> **BEFORE YOU DRIVE**
>
> *YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK.*
> *LOCATION DATA MAY NOT BE ACCURATE.*
>
> **What it does not do**
>
> — New England only. Six states, 236,000 km of road.
> — No lane guidance. The data covers between 4.6% and 23.8% of junction
>   approaches, depending on the state, which is not enough to tell you which
>   lane to be in.
> — No live traffic. Every time shown is a model, not a measurement.
> — Scenery scores are not uniform across the six states: the terrain component
>   saturates north of Massachusetts.
>
> **Got it**
>
> *Also in Sources, any time.*

The obligation is not bolted on: the notice is a reasonable host for the app's
limits, and stating them once, up front, is cheaper than a driver discovering
them on a back road in Maine.

Three points of compliance hygiene:

1. **Exactly one copy.** The first-run card and the Sources entry are two routes
   into the same view. Nothing anywhere else in the interface restates,
   paraphrases or summarises the notice. The bullets below it are the app's own
   words about the app's own limits and are not a second copy of anything.
2. **Both tests keep passing unchanged.** They assert the constant, not its
   location — one that it is character-exact, one that it is not quietly
   sentence-cased. Moving the view that renders it touches neither.
3. **This does not discharge §3.3.3(F)(iii) by itself.** That clause asks for an
   end-user licence agreement carrying the notice, filed in App Store Connect.
   That is a submission task, not an interface one, and
   `docs/app-store-submission.md` already owns it. The screen is in the app
   because the person it protects is driving.

---

## 10. The name, and the word *scenic*

**The app's name appears nowhere in this design** except the home-screen icon
label. Not a splash, not a header, not a watermark, not the Sources screen, not
the location purpose string. That decision was taken on 2026-09-20 and it is a
good one: a driver who has opened the app knows which app it is, and the most
prominent line on any screen is worth more spent on what to do next.

It is also, for this particular name, the right *aesthetic* call. "Victory Lap"
is a wry name — it is about the feeling at the end of the drive, not the drive.
Putting it in a header would make the app announce a joke every time it opened.
Letting the **arrival card** (§5.4) be the place that feeling lands means the
name gets paid off once, at the only moment it is true, without ever being
printed.

**The word *scenic* stays** and stays descriptive. It labels the dial's far end
(`RoutePanel.swift:474`/`:478`), it names the scenic route in the
ledger, and it is the right English word in both places. What the redesign does
*not* do is let it drift back into being a brand: there is no "Scenic Mode", no
"Scenic Score™", no capital S anywhere it is not starting a sentence.

**On an icon.** Out of scope to draw here, but three constraints for whoever
does: SF Symbols may not be used in app icons, logos or trademarks under the
Xcode and SDK licence; the current `icon-1024.png` is machine-generated and
under the US Copyright Office's position a generated mark may not be
copyrightable by *anyone*, so the shipping artwork wants a human illustrator;
and the icon is the only surface in the whole product that carries the name, so
it is doing more work than an icon usually does. The palette gives it a
starting point — amber on a warm dark ground, a road, low sun — and that is as
far as a document should go without a pencil.

---

## 11. What I am keeping, and why that matters

Most of the current app's small decisions are right. These are load-bearing and
they survive:

| kept | why |
| --- | --- |
| `PrefSlider`'s `sqrt` mapping (`RoutePanel.swift:52`) | Measured over 252 pairs. Handle-linear-in-`strength` is the honest transform, and `0`/`1` survive bit-for-bit — which three call sites depend on |
| Two marks, not a five-point scale | Aiming needs looking. The calibration wants a rank statistic over many marks, so precision on any one buys nothing |
| Differentiated haptics on those marks | The whole confirmation, felt not read |
| `repeated_km` always shown | The one number that says a loop is really an out-and-back |
| The `Town centers` note | A product admitting a measurement went against it. Model for the voice |
| `beautiful_km` over `mean_score` on screen | Nobody has a feel for 4.2 against 5.1, and the mean rose on 27 of the 30 trips where the good road went *down* |
| `Try another direction (5)` | Names how many there really are rather than implying endless variety |
| Untappable numbers under the resting thumb | A hand on the phone mid-drive cannot fire anything |
| `contentShape(Rectangle())` on every full-width row | Half of every suggestion row was dead space without it |
| Verbatim credit strings, and their capitalisation | Somebody else's text |

The interface this replaces is not badly reasoned. Almost every small decision in
`RoutePanel` and `NavView` has a paragraph behind it and most of those paragraphs
are right. What it lacks is a shape. The container was wrong, so good local
decisions could not add up to a good screen.

---

## 12. What this design wants that the API does not have

One field, and it unlocks two features:

**`score_profile: [Double]`** — the scenic score at each vertex of the returned
LineString, same length as `geometry.coordinates`. `RouteProps` already carries
`scenery_km` as aggregate totals and `beautiful_km` as a single figure; this is
the same information, positioned.

With it:

1. **The route line is coloured by what it is passing** — the six scenery hues
   along the line, so the breakdown bars become a legend for the drawing rather
   than a chart beside it.
2. **The score ribbon on the driving screen** — a thin strip showing the beauty
   of the next few miles, so a driver knows the good bit is in three miles. This
   is the app's unique asset put to work in the moment it matters most, and
   today the scoring system is invisible from behind the wheel.

Both are drawn in the mockups, marked. **Both degrade cleanly:** without the
field, the line is plain amber and the ribbon simply is not there. Nothing else
in this design depends on a backend change.

Two smaller asks, neither blocking:

- **`/api/loop` accepting `target_minutes`** would make §4.4's dial exact
  instead of self-calibrated. The self-calibration works and needs nothing.
- Five recent destinations in `UserDefaults`. Not an API change; just a thing
  the app does not do.

---

## 13. A review of the two documents this deletes

Written after the design above was drafted and drawn, so it is not anchored by
them.

### 13.1 The accuracy charge does not stand

The stated reason for binning `ui-redesign.md` is that it reads as though it were
produced in "a hallucinated state". I tested that rather than repeating it, by
resolving its citations against `main` at `d11344d` — a later tree than the
`8e53ec9` it was written against, and one where `RoutePanel.swift` has grown by
six lines.

Every one of the ten I checked still lands on exactly the text it claims:
`RoutePanel.swift:484` is the `scenery strength` caption, `:544` is
`"Start scenic drive"`; `RouteResults.swift:103` and `:106` are the two
`"… mi beautiful"` branches; `RouteModel.swift:19` is `case loops = "Loop"`;
`Theme.swift:10` is the brand green; `Region.swift:9` is
`static let massachusetts`; `NavView.swift:121` is the party popper; `:355` is
`"Lovely road"`; `LoopPanel.swift:181` is `card("Beautiful road", …)`. Its
structural claims check out too: `prefSlider` really is emitted at `:280` before
`if let response` at `:288`, the route really does recompute only on release at
`:475`, and there really is no `CodingKeys` anywhere in `ios/Sources` — I grepped,
it is zero, which is what makes its warning about renaming `response.scenic`
correct and worth keeping.

The only wobble I found is arithmetic and trivial: it says "13 surviving
`.scenic` references" where a word-boundary grep returns 11, the difference being
whether `scenicMinutes` and `scenicDetail` count as `.scenic` references. It
names which ones it means, so nothing turns on it.

**So: substantially correct, and not what was wanted.** There is no accuracy
fault here to report.

### 13.2 Where the real defect is, and it is not in that document

The owner asked for an interface. What `ui-redesign.md` delivers is a
**changelist**: a triage table with four verdict words, exact replacement strings
with `file:line`, a per-test cost tally, an apply order. Its unit of thought is
the string literal. There is no screen in it — no layout, no hierarchy, no
drawing, no claim about what the thing should feel like in the hand. **You could
apply every word of it and the app would look identical.** That is a difference
of category, not of quality, and it is what the complaint was about.

Why it reads as assembled: its agenda is inherited wholesale. Every section
answers a section of `branding-brainstorm.md` §4–§6; its structure *is* that
document's structure; even where it disagrees it is arguing inside a frame
somebody else set, about words somebody else picked, under a name that had since
changed. That is editing, and the editing is good; it is not design.

**And the fault for that belongs to the brief, not the document.**
`ui-redesign-brief.md` Trap 5 rules the largest interface change out of scope in
so many words: *"Propose around it, note where a redesign would interact with it,
and do not design it."* The change it is ruling out is the Apple attribution
refactor. That is not one item among many — it is the fact that **a bottom sheet
over a map is illegal in this app**, which is the single constraint that
determines the shape of every planning screen. A redesign forbidden from touching
it was structurally prevented from being a redesign. The brief also fixed the
deliverable as "one markdown file" (Trap 1) and set `Done looks like` as six
triage-and-specify items, none of which asks for a screen.

Given that commission, `ui-redesign.md` did the right work. It answered the
question it was asked, and the question was the wrong one. The honest verdict is
that **the brief is the weaker of the two documents**, and its mistake is the one
worth remembering: a brief that rules out the load-bearing problem caps the
answer, however well the answer is written.

### 13.3 Its best paragraph, and where it went

§3.3 is the best analysis in either document, and it is a refusal. `branding-
brainstorm.md` §4 called "state the trade, not the setting" the single
highest-value copy change in the app and specified the replacement as
`+38 min · 25 good miles`. §3.3 shows it cannot be applied as a one-line change,
for three independent reasons: the caption renders before any route exists, so
on every cold launch it has nothing to print; once a route does exist it is the
fourth statement of one fact; and because the route recomputes only on release, a
price tag under a moving handle describes the position the user just left. *"`0.25`
is merely opaque, a stale price is wrong."* It then traces the follow-on nobody
else had — deleting the caption invalidates two *fitted* constants in
`PlanningCompactDetent` that were solved from a device measurement — and prices
the change honestly at a re-measure rather than a line.

**My design agrees with all three findings and answers them differently.** The
caption is gone, as §3.3 recommends. But the diagnosis it inherited was right:
`0.25` should not be on screen. So the readout shows the *outcome* — `+18 min ·
19 mi of beautiful road` — and it solves the three objections by construction
rather than by deletion. There is no cold-launch state to fail in, because the
dial does not exist until a route does; it is not a fourth statement, because the
ledger and the sentence it would be duplicating are both gone; and mid-drag it
prints no number at all, only the name of the region of the track, resolving to
figures when the finger lifts.

That is the one idea in my design I did not have on my own, and §3.3 is where it
came from. Deleting the document does not delete the argument — this section is
where it now lives.

---

## 14. What the deletion must not lose

`docs/README.md`'s own convention is *archive rather than delete*. The owner has
instructed deletion, which is his call to make; the commit message says so. These
are the things worth carrying, checked so that nothing is orphaned:

| From the deleted documents | Where it lives now |
| --- | --- |
| §3.3's three arguments against a live price tag | §13.3 above, and designed around in §4.3 |
| Renaming `response.scenic` breaks decoding at runtime with no compile error (no `CodingKeys` in `ios/Sources` — verified, zero) | §13.1, and §10 keeps *scenic* as the arm's name anyway |
| "1 good miles" — the plural trap any adjective swap introduces | Here. It applies to **any** replacement for `mi beautiful`, including keeping it |
| No SF Symbols in an app icon; a human must draw the mark; a signed authorship statement **and a written assignment** | §10 |
| Never draw a chequered flag, a trophy, a podium, a speedometer, a stopwatch, or speed lines | §10, and it is right: the name already carries the motorsport reference, so the mark should not repeat it |
| `Text("You've arrived 🎉")` is an exclamation mark with extra steps | §5.4 replaces the whole banner state with the arrival card |
| The opening region serves one state of six | Already owned by `roadmap.md:89`, independently of this |
| The camera and the search bias want *different* constants — widening the search box is how "main street" starts offering one four towns away | Here, because it is a real distinction and the roadmap item does not draw it |
| The attribution refactor | Already owned by `release-plan.md` §6c |

**Two of its conclusions I am overturning, with reasons rather than silence.**

**"Lap" for the loop mode.** Its argument against "Nowhere" is sound — a mode
called *Nowhere* fights a subtitle that says *on purpose*, and
`branding-brainstorm.md` had already refused *Aimless* as a product name for
carrying that valence. It then proposed *Lap*. I am keeping what the app already
says: **Loop**.

It is the accurate word, it is what the feature is called everywhere else in the
project (`LoopModel`, `LoopPanel`, `/api/loop`), and it needs no explaining. *Lap*
is a wink at the app's name, and the first screen is the last place to spend one:
a driver reading **Directions** and **Loop** knows immediately which is which.
`RouteModel.swift:19` does not change.

**"Good miles" for "beautiful".** Its case is that 79 marks from one driver in
one part of one state support *measured* but not *beautiful*. The force of that
is real. I am keeping **beautiful** anyway, for three reasons: it is the API's own
name for the quantity (`beautiful_km`, `beautiful_score`), so the app and the
backend would otherwise call one number two things; *good* is vaguer, and
vagueness is not the same as honesty; and my design answers the overclaim where
it should be answered — §9's **Before you drive** says in the app's own words that
the times are a model and that the scores are *not* uniform across the six
states. A screen that states its limits buys more honesty than a weaker adjective
does. If the owner disagrees, it is a one-line change either way and the plural
trap above is the only thing to watch.
