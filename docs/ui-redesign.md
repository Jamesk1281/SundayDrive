# The interface and its words, under the new name

**Status: written 2026-09-20 against `main` at `8e53ec9`, which is the tree with
the rename merged. Nothing was changed — `RoutePanel.swift:484` still reads
`scenery strength`, `RouteResults.swift:103,106` still emit `"… mi beautiful"`,
and `RouteModel.swift:19` is still `case loops = "Loop"`.** Every line number
below is `8e53ec9`; each citation carries its anchor text so it survives drift.
`branding-brainstorm.md` is cited **by section, never by line** — its header is
being appended to by more than one session, so its line numbers are not stable.

Answers [`ui-redesign-brief.md`](ui-redesign-brief.md). Triages
[`branding-brainstorm.md`](branding-brainstorm.md) §4–§6 against the name chosen
in [`victory-lap-naming.md`](victory-lap-naming.md).

---

## 1. The short answer

**§4's diagnosis is right and almost all of it survives the name change
unaltered. §5 is dead. §6's colour already shipped, and its icon ranking does
not survive.** Concretely:

- **Three of §4's four items survive as written** — "good miles", "the dial",
  and the demand that the interface stop printing a 0–1 parameter.
- **§4's fourth item, "Nowhere", does not survive**, and the thing that kills it
  is not the app name but the *subtitle the owner chose today*. §4.
- **§4's headline change is not a one-line change**, and the replacement string
  it specifies cannot render. This is the one place the existing document is
  wrong rather than merely out of date, and it is worth reading before anyone
  spends the afternoon §7 promised. §3.3.
- **§5 is Longcut's voice**, not pending work. Do not apply it.
- **§6's icon ranking was drawn for Longcut** and its top pick loses its main
  argument under Victory Lap. A different direction is recommended. §5.

The work below is an afternoon plus an illustrator, as
`branding-brainstorm.md` §7 item 7 estimated. Nothing here needs a routing
change, a new endpoint, or a decision from anyone but the owner on §4.

---

## 2. §4–§6, triaged

Four verdicts: **survives** as written · **reworded** · **dead** because it was
Longcut-specific or is superseded · **shipped** already.

| § | Item | Verdict | Where |
| --- | --- | --- | --- |
| §4 | "Good miles" instead of "mi beautiful" | **Survives** — name-independent, and better supported than §4 knew | [§3.1](#31-good-miles) |
| §4 | "The dial" as the internal name for the slider | **Survives** — internal vocabulary only, nothing to apply | — |
| §4 | State the trade, not the setting | **Reworded — and the cure changes.** The diagnosis holds; the specified string cannot render and would be the fourth statement of one fact | [§3.3](#33-the-dial-caption) |
| §4 | Loop mode renamed **Nowhere** | **Dead** — collides with the chosen subtitle, not with the name | [§4](#4-nowhere-the-verdict) |
| §5 | Tagline *"Take the long way."* | **Dead** — Longcut positioning, carried from §3's *"Recommendation: **Longcut**"* entry into §5's first bullet | — |
| §5 | Subtitle `Take the long way home.` | **Dead** — decided as `The scenic route, on purpose` (`victory-lap-naming.md` §6a) | — |
| §5 | One-liner, loop hook, credibility line, opening line | **Reworded** — survive as *listing* copy, already superseded by `victory-lap-naming.md` §7–§8, which is the live listing | — |
| §5 | "Measured" is defensible, "beautiful, guaranteed" is not | **Survives**, and its premise needs correcting in place | [§3.1](#31-good-miles) |
| §6 | Keep the green, rename the symbol | **Shipped** — by the rename itself | below |
| §6 | Icon: "Two ways" is the one to develop | **Reworded** — still viable, no longer the obvious pick | [§5](#5-the-icon) |
| §6 | Icon: Switchback / Contour / The dial | **Dead**, and one of them is *more* dead under this name | [§5.1](#51-6s-four-directions-re-ranked) |
| §6 | No SF Symbols; a human must draw it | **Survives**, and needs one thing added | [§5.3](#53-the-illustrator-brief) |

**On the colour, so it is not re-proposed.** §6 said `Color.scenic` should keep
its value and rename its symbol with the app. **The rename did exactly that** —
`897dbe7:ios/Sources/Theme.swift:6` was `static let scenic`, and
`ios/Sources/Theme.swift:10` is now
`static let brand = Color(red: 0.22, green: 0.83, blue: 0.62)`. The value is
unchanged and `#38D49E` remains the only brand equity the project has. There is
nothing left to do here, and the credit belongs to the rename.

**On why §4 is sitting there unshipped.** `branding-brainstorm.md` §7 item 7
asked for it to ship *with* the rename: *"Do the in-product copy from §4 at the
same time — it is an afternoon and it is most of what the brand actually feels
like."* It did not. The rename's scope was identifiers, and its follow-up
(`14efbf6`) was specifically about removing the *name* from where a driver reads
it. **This is a recorded gap, not an oversight** — worth stating so nobody
re-discovers it a third time.

---

## 3. The copy layer, ready to apply

Exact strings, in apply order. Nothing here needs a decision except §3.3.

### 3.1 Good miles

**`ios/Sources/RouteResults.swift:103,106`** — the detail line on each card.

```swift
// :103  beautifulMiles.map { "\($0.fastest) mi beautiful" } ?? "\(printedFastestScore)/10"
// :106  beautifulMiles.map { "\($0.scenic) mi beautiful" }  ?? "\(printedScenicScore)/10"
```

§4 asks for "good miles". Applied literally it produces **"1 good miles"**, and
one mile is reachable — `RouteComparisonTests.swift:188` strides
`0.0 → 20.0 by 0.1` and asserts on every step. The current wording has no plural
problem only because "mi" is an abbreviation, so the plural is a cost the change
introduces. Replacement:

```swift
/// "3 good miles", and "1 good mile" — the singular is reachable, and the
/// abbreviation that used to hide it is gone.
private static func goodMiles(_ n: Int) -> String {
    "\(n) good mile\(n == 1 ? "" : "s")"
}

var fastestDetail: String {
    beautifulMiles.map { Self.goodMiles($0.fastest) } ?? "\(printedFastestScore)/10"
}
var scenicDetail: String {
    beautifulMiles.map { Self.goodMiles($0.scenic) } ?? "\(printedScenicScore)/10"
}
```

The card reads `71 mi · 25 good miles`, which is **two characters shorter** than
`71 mi · 25 mi beautiful`, so it carries no new wrapping risk in a half-width
card at `.caption2`.

**The sentence has to move with it.** Leaving the cards saying "good miles" while
the sentence 20 points below says "beautiful road" splits the vocabulary on one
screen — which is the same "two rulers at once" objection `LoopPanel.swift:225`
already makes in its own words. Four sites, `beautiful road` → `good road`:

| Line | Current | Replacement |
| --- | --- | --- |
| `RouteResults.swift:186` | `…and leaves beautiful road at \(to)` | `…and leaves good road at \(to)` |
| `:187` | `…same \(to) of beautiful road, at no extra time` | `…same \(to) of good road, at no extra time` |
| `:192` | `turns \(from) of beautiful road into \(to)` | `turns \(from) of good road into \(to)` |
| `:193` | `**cuts** beautiful road from \(from) to \(to)` | `**cuts** good road from \(from) to \(to)` |

`from` and `to` at `:180` are untouched — they are `**0 mi**` / `**25 mi**`, and
the whole of `:150–198`'s four-shape logic stays exactly as it is. The sentence
becomes *"Scenic adds **38 min** and turns **0 mi** of good road into
**25 mi**"*.

**Loop mode, same vocabulary:**

| Line | Current | Replacement |
| --- | --- | --- |
| `LoopPanel.swift:181` | `card("Beautiful road", …)` | `card("Good road", …)` — renders uppercased at `:216`, and "GOOD ROAD" fits a half-width card better than "BEAUTIFUL ROAD" |
| `LoopPanel.swift:235` | `…mi** on beautiful road, ` | `…mi** on good road, ` |
| `LoopPanel.swift:225` | doc comment example | update to match |

**Keep `LoopPanel.swift:183`** — `"scoring \(Int(meta.beautiful_score))+ of 10"`.
It is the only place the threshold behind the word is shown, and it is *more*
necessary once the adjective is "good", which is vaguer than "beautiful". Do not
drop it as redundant.

**Why "good" is the right word, on the evidence we now have.** §5 argued against
overclaiming on the grounds that "the scoring has never been validated against a
human." **That premise is false and has been since 2026-08-25** —
`measuring-scenery.md:25–33` records 79 marks over 12 drives at separation
**0.74** against a **0.63** noise floor computed from those same sample sizes,
stable across the 200/400/800 m windows. §5's conclusion survives its premise
anyway: 79 marks are **one driver in one part of one state**
(`roadmap.md:85–88` says so and calls a second driver worth more than a second
drive). So "measured" is defensible, "good" is defensible, and "beautiful" is a
promise the data cannot underwrite for someone else's taste. The correction
strengthens the change; it is not licence to overclaim.

**Test cost: ten assertions in `ios/Tests/RouteComparisonTests.swift`** — `:177`,
`:178`, `:180`, `:196`, `:197`, `:214`, `:227`, `:238`, `:251`, `:265`. `:196–197`
interpolate the count, so they need the same pluralisation helper or they will
fail on the `1 mi` step of the stride rather than uniformly. Nothing else in the
suite reads these strings.

### 3.2 The loop mode's label

Covered in [§4](#4-nowhere-the-verdict). One string: `RouteModel.swift:19`.

### 3.3 The dial caption

**`ios/Sources/RoutePanel.swift:484`.** §4 calls this "the single highest-value
copy change in the app" and specifies the replacement as `+38 min · 25 good
miles`. **The diagnosis is right. The replacement cannot be applied, for three
independent reasons, and the third is fatal.**

```swift
// :480–485, current
// The position, not `model.pref` — after the mapping those are two
// different numbers and printing the one the handle is not at is
// how the caption would start lying. "Strength" because under the
// mapping the position *is* the router's `strength`.
Text("scenery strength \(prefPosition.wrappedValue, format: .number.precision(.fractionLength(2)))")
    .font(.caption2).foregroundStyle(.secondary)
```

**1 — It has nothing to print in the app's opening state.** `prefSlider` is
emitted at `RoutePanel.swift:280`, inside `directionsContent`, *before* the
`if let response = model.response` at `:288`. On a cold launch there is no route,
so there are no minutes and no miles. `+38 min · 25 good miles` is undefined in
the state every session starts in.

**2 — It would be the fourth statement of one fact.** Once a route exists the
screen already says the trade three times, in descending order down the sheet:
the header hint at `:304`/`:332` (*"Drag the slider to trade time for scenery"*),
the two cards, and `RouteResults`' sentence at `:174–198` — a sentence whose
entire type exists so that it "has to check out against what is on screen"
(`RouteResults.swift:98–101`). Adding a price tag above them adds no information.

**3 — Mid-drag it would be a lying price tag, and fixing that is refused on
measured grounds.** The route recomputes **only on release** —
`:475–476`, `if !editing { Task { await model.computeRoute() } }` — for the
reason `LoopPanel.swift:145–147` states outright: mid-drag is a request per tick
at ~0.65 s of server work each. So while the handle is moving, `extraMinutes` and
the mile count describe *the position the user just left*. A caption reading
`+38 min · 25 good miles` under a handle that is somewhere else is worse than the
number it replaces: `0.25` is merely opaque, a stale price is wrong. The existing
comment at `:480–483` is already alert to exactly this failure — it explains that
printing `model.pref` instead of the handle position "is how the caption would
start lying" — and §4's string reintroduces the fault it was written to avoid.

Making §4's string true requires live re-routing during the drag, which is a
server-cost decision the code has already taken the other way. **It is not a
one-line change; it is a routing change wearing a copy change's clothes.**

**Recommendation: delete the caption.** `:480–485`, six lines out, nothing in.

```swift
private var prefSlider: some View {
    HStack {
        Text("Fastest").font(.caption2)
        Slider(value: prefPosition, in: 0...1) { editing in
            if !editing { Task { await model.computeRoute() } }
        }
        Text("Scenic").font(.caption2)
    }
}
```

Nothing a driver can use is lost. The track is already labelled `Fastest` ↔
`Scenic` at `:474`/`:478`; the header says what the slider is for; the cards and
the sentence say what it cost. The number that goes is the router's `strength` —
a coordinate invented in `PrefSlider` that exists so the *handle* travels
usefully, and which has no meaning to the person holding it. That is precisely
§4's complaint, and deletion answers it more cheaply than the substitution does.

**The fallback, if the handle should keep a label.** Follow the precedent the app
already set: `TuneView.swift:89–91` prints `"more"` / `"less"` / `""` against
neutral rather than a weight. The same three-bucket treatment here — one
qualitative word off `prefPosition` alone — is honest at any moment of a drag
because it describes the handle and not the route. It needs three strings
invented, which is why it is the fallback and not the recommendation.

**The deletion has one follow-on, and it is not optional.** The compact detent's
height is a *fitted* model, not a live measurement:
`PlanningCompactDetent.fixedPoints = 147` and `textPoints = 164`
(`RoutePanel.swift:98–99`) were **solved** from the planning block measured on a
booted iPhone 15 Pro at 311 pt and 363 pt, and `:110–112` says that provenance is
"the only reason to trust them". The caption is a `.caption2` typed line *inside*
that block, so removing it leaves both constants describing a block that no
longer exists — the detent would reserve about a caption line of height nobody
uses. Nothing clips and nothing crashes; the numbers just stop being measurements,
which is the failure this codebase is most careful about.

Two further mentions have to be revisited in the same commit: `bottomInset = 34`
at `:101–104` is justified by the home indicator overlapping *"the slider
caption"*, and `:117–121` justifies counting the attribution footer by the same
caption being pushed under the sheet's edge. Neither is wrong once the caption
goes — the footer is still the bottom typed line — but both cite a thing that
will not be there.

**So the honest cost of §4's "single highest-value copy change" is: delete six
lines, re-measure the block on a device at the two text sizes, re-solve two
constants, and update three comments.** Still an afternoon. Not one line — and
that gap is the reason to read this section before starting rather than after.

**This is the one item that needs the owner**, because §4 called it the highest-
value change in the app and the answer here is "delete it instead". The
disagreement is about the cure, not the diagnosis.

---

## 4. "Nowhere": the verdict

**Replace it. The loop mode should be called `Lap`.**
One string: `RouteModel.swift:19`, `case loops = "Loop"` → `case loops = "Lap"`.

§4's case for "Nowhere" is good and it is genuinely name-independent, so the name
change alone does not kill it. **What kills it is the subtitle the owner chose on
2026-09-20:** `The scenic route, on purpose` (`victory-lap-naming.md` §6a, and
§7's options table records it as option 4). A mode called **Nowhere** says the
opposite of **on purpose**. They cannot share a product.

That tension is not new to this document — `branding-brainstorm.md` §3 rejected
*Aimless* as a name partly because *"'aimless' carries a negative valence
(pointless, lost), and some users will read it as the app not knowing where it is
going"* — and then recommended a mode name carrying the same valence two sections
later. Under Longcut, whose register is wry and neutral, the inconsistency was
survivable. Under a name and a subtitle both built on *purpose*, it is not.

**Why `Lap`, specifically:**

- **It is the namesake feature.** A victory lap *is* a closed loop driven slowly
  for its own sake. Under Longcut — a route between two points, made longer — the
  loop mode was the odd feature out and needed its own name to have an identity
  at all, which is most of why §4 proposed one. Under Victory Lap the loop is the
  thing the name is about, and giving it a different name now fights the brand
  instead of extending it.
- **It is parallel with the control's other option.** `Directions | Lap` — two
  nouns naming what you get. `Directions | Nowhere` is a noun and a negation.
- **It survives the control.** Three characters in a segmented control that must
  hold two labels at accessibility text sizes; "Nowhere" is seven.
- **It costs one string.** The `rawValue` is the display label and the
  `Identifiable` id (`RouteModel.swift:17–22`), and it is **not persisted** —
  `UserDefaults` is used only by `VoiceCatalogue.swift:118` and
  `VoiceGuide.swift:351`, neither for the mode — and no test reads it. So the
  change has no restore path and no test cost.

**Keep §4's sentence, and put it in the listing rather than the app.** *"Nowhere
in particular. Ninety minutes. We'll bring you home."* is excellent copy and the
objection above does not touch it: it describes *the destination*, which truly is
nowhere in particular, rather than labelling *the drive*, which has a point.
But it cannot go in the app as written — **loop mode has no minutes control.**
The slider is `LoopModel.minKm...maxKm` rendered as *"about 25 miles"*
(`LoopPanel.swift:151–166`), so "Ninety minutes" promises a control that does not
exist, and binding it to the live value would restate the caption directly above
it. It belongs in the App Store description, where an illustrative number is
what the form wants.

**The loop empty state is fine as it is.** `LoopPanel.swift:35–37` — *"Pick a
starting point and a distance. There's no destination to choose — that's the part
this does for you."* It instructs, it explains the feature's whole premise in one
clause, and it is already in the right voice. Leave it.

---

## 5. The icon

A direction and a brief. No rendered mark — see §5.3 for why that is a
requirement rather than a scoping choice.

### 5.1 §6's four directions, re-ranked

§6 tested four at 96px and 28px and picked **Two ways**. That ranking was drawn
for Longcut and does not survive intact.

| §6's pick | Under Victory Lap |
| --- | --- |
| **1. Two ways** — a dashed straight line and a bold winding one joining the same two dots | **Demoted, not dead.** §6 chose it partly because *"it pairs exactly with the name Longcut"*, and that argument is simply gone: Victory Lap is not about A-to-B-made-longer. It survives as a *product* mark — it is still the thesis in one image — but it is no longer the obvious pick. It also has a thumbnail problem §6 understates, below |
| **2. Switchback** — a single folded stroke | **Dead, and more dead than before.** §6 rejected it for reading as "twisty road, motorcycle register". The name now leans that way on its own, and `branding-brainstorm.md` §3 refuses Apex / Chicane / Hairpin for pulling *"toward fast and track, the opposite of the product's soul"*. The name has spent the product's entire motorsport budget; the icon must spend none |
| **3. Contour** — topo lines with a road across | **Dead as an icon, unchanged.** Muddies below 40px. Still good as a marketing motif or the Tune header |
| **4. The dial** — an arc with a handle | **Dead, and worse here.** It read as a gauge under any name; under Victory Lap a speedometer is an active misdirection about what the product is for |

**The thumbnail objection to "Two ways."** §6 argues it survives the thumbnail
"because the two strokes differ in weight *and* style." Weight survives
downsampling; **style does not.** A dash pattern is high-frequency detail, and at
29px — the Settings and Spotlight size, which the icon must ship at — a dashed
stroke either aliases into a broken smear or resolves to a solid line. When it
resolves, the mark becomes two roughly parallel strokes and its entire meaning
(*one of these is the boring way*) is gone. The direction needs the contrast
carried by weight or colour alone, not by the dash, and §6's brief should say so
whichever direction is drawn.

### 5.2 The recommendation: the closed loop

**A single closed, irregular, hand-drawn loop of road — the lap — in the brand
green on a dark ground.** Not a circle and not an oval; a road that comes back to
itself, with one or two switchback kinks and visibly uneven curvature.

- **It is the name, literally**, and it is the one mode no competitor has.
- **It is the most legible form available at 29px.** A closed shape reads as a
  silhouette — enclosed white space is the lowest-frequency signal there is, and
  the one thing downsampling preserves. It asks the viewer to resolve one stroke,
  not two, and nothing about it depends on telling two line styles apart.
- **It carries the product's soul rather than its category.** A loop is the shape
  of a drive taken for its own sake — there is nowhere it is trying to get.

**The risks, to hand to the illustrator rather than hide:** an irregular closed
curve can read as a blob, a leaf, or — worst — a racetrack. Mitigations: keep the
enclosed area large and open, keep the stroke weight constant as a road's would
be, make the asymmetry pronounced enough that no one sees an oval, and consider a
single dot marking start-and-finish, which is the one detail that says *drive*
rather than *shape* and is the first thing to drop if it does not survive 29px.

**Keep "Two ways" as the tested alternative.** It is a strong mark and the
argument against it is that it lost its pun, not that it stopped working. Draw
both; test both at 29px in greyscale before choosing.

### 5.3 The illustrator brief

Hand this over as written.

**What it is for.** The iOS app icon and the wordmark lockup for a navigation app
called Victory Lap that finds scenic driving routes. The voice is unhurried, dry,
quietly confident — "a well-made analogue object, a good map, a mechanical watch"
(`branding-brainstorm.md` §2). It is the only navigation app that asks you to
spend more time, not less.

**Direction.** §5.2 above, with §5.1's "Two ways" as the alternative to draw
alongside it.

**Colour.** `#38D49E` — `rgb(0.22, 0.83, 0.62)`, defined once at
`ios/Sources/Theme.swift:10` as `Color.brand`. **This value is fixed.** It is the
route line, the Tune highlight and the scenery bars, and it is the only brand
equity the project has. It was chosen to read against both the Apple basemap's
greens and its water blue, and to sit clear of Google Maps blue and Waze's
palette. A dark ground; the green is the mark, not the background.

**It must survive, in this order of importance:** 29pt (Settings, Spotlight),
40pt (Spotlight), 60pt (home screen), 1024pt (the App Store). **Test at 29px in
greyscale** — if it fails there it fails, whatever it looks like at full size.
This is the test that killed two of the four directions already explored.

**Deliverables.** Layered vector source (SVG or `.ai`/`.sketch`), plus a flat
1024×1024 PNG. **Opaque, square, no transparency and no rounded corners** — iOS
applies its own mask and rejects alpha. No text in the icon. No drop shadows or
gradients that will not survive the mask.

**Two hard constraints, both licence rather than taste:**

1. **No SF Symbols, and nothing close to one.** The Xcode and Apple SDKs licence
   forbids using SF Symbols *"or glyphs that are substantially or confusingly
   similar"* in app icons, logos, or any trademark-related use. This rules out
   the obvious shortcut — `location.north.line.fill` on a green square. (Inside
   the app, `systemImage:` is fine and the app uses it throughout; this constraint
   is about the mark only.)
2. **A human must draw it, and we need that in writing.** The current
   `ios/Sources/Assets.xcassets/AppIcon.appiconset/icon-1024.png` is generated by
   `ios/scripts/generate_icon.py`, and under the US Copyright Office's position
   AI-generated material without sufficient human authorship may not be
   copyrightable at all — meaning the current mark is plausibly owned by nobody,
   including us. Fine for a private build; useless for a brand you would defend.
   So: **the layered source file, a signed statement of human authorship, and a
   written assignment of copyright.** §6 asks for the first two by implication
   and none of the three explicitly; the assignment is the step that actually
   moves ownership, and commissioning a drawing does not do it on its own.

**Do not draw, under any circumstances:** a chequered flag, a trophy, a podium, a
speedometer, a stopwatch, speed lines or motion chevrons. "Victory Lap" invites
every one of them and every one of them is the opposite of the product — this is
an app that asks you to go slower and arrive later. The name is doing the wink
already; the mark should be the road.

**What the current icon gets wrong, for context.** It is a landscape — a winding
road through hills under a sky. That is a *picture* of the subject, and pictures
do not survive 29px or sit well beside iOS's flat system icons. What is wanted is
a *mark*: one idea, one stroke, no scene.

---

## 6. Everything else a first user would notice

Judged on that test alone. Two items, then three explicit "this is fine"s.

**1. The app opens on Massachusetts, and it serves six states.**
`ios/Sources/Region.swift:9`, `MKCoordinateRegion.massachusetts`, span 2.6° on
Oxford. It is the first thing on screen at every cold launch and it is the item
`roadmap.md:89–92` already flags.

One distinction worth making before anyone fixes it, because the constant is used
for **two different jobs** and only one of them is wrong:

| Use | Site | Verdict |
| --- | --- | --- |
| The opening map camera | `ContentView.swift:16` | **Wrong.** Should frame New England — this is the "where am I, and does this app cover me?" question, and the honest answer is all six states |
| The address-search bias | `RouteModel.swift:58`, `LoopModel.swift:94`, `SearchCompleter.swift:23` | **Leave tight.** `Region.swift:14–23` documents why: results rank by distance from the box's centre, so widening it to New England is how *"main street"* starts offering a main street four towns away. `around()` already re-biases to the user; only the pre-fix fallback is at issue |

So the fix is a second constant, not a wider one. Cheap, and worth doing before
anyone sees the app.

**2. `Text("You've arrived 🎉")` — `NavView.swift:121`.** §2 sets the voice as
*"unhurried, dry… never breathless, never exclamation marks."* A party popper is
an exclamation mark with extra steps, and it is the last thing the app says on
every drive. Lowest priority item in this document, but it is free: drop the
emoji.

**Three things that are fine, said plainly so nobody redesigns them:**

- **"Start scenic drive"** (`RoutePanel.swift:544`), **the "Scenic" card**
  (`RouteResults.swift:18`) and the **`Fastest` / `Scenic` track labels**
  (`:474`, `:478`). These name the **routing arm**, not the app, and "scenic" is
  the correct English word for it. They are also the visible half of a contract:
  `server/app.py:1–8` answers `{"fastest": …, "scenic": …}` and `Models.swift:12`
  is `let scenic: RouteFeature` on a plain `Decodable`, matching **by property
  name** — there is no `CodingKeys` anywhere in `ios/Sources`.

  **Leave all 13 surviving `.scenic` references — but for two different reasons,
  because only one group is dangerous.** Seven are the wire contract itself
  (`response.scenic`: `RouteResults.swift:10`, `RoutePanel.swift:542`,
  `NavigationModel.swift:1266`, `ContentView.swift:48`, `:84`, `:116`, `:122`),
  and renaming those yields a **nil route at runtime with no compile error**.
  The other six are derived or local — `comparison.scenicMinutes` and
  `scenicDetail` at `RouteResults.swift:18–19`, `miles.scenic` at `:134`, `:180`,
  `:191` — where a rename is merely pointless and fails loudly at build time.
  None of the 13 is a colour; the colour uses became `Color.brand` in the rename.
- **The scenery verdict buttons** — "Lovely road" / "Nothing to see"
  (`NavView.swift:355`, `:357`). Warm, concrete, and already in voice.
- **The Tune sheet** (`TuneView.swift`). *"Drag toward what you'd rather drive
  past. Centered means no preference."* is the clearest sentence in the app, and
  its `more`/`less` captions are the precedent §3.3's fallback borrows.

---

## 7. What this does not settle

- **The `MKMapView` attribution refactor** (`release-plan.md` §6c,
  `ContentView.swift:40`, `NavView.swift:38`) is the largest interface change
  pending and it is **not this document's**. It carries its own product decision —
  whether the attribution ornament rides above the sheet at `.large` or is allowed
  off-screen as Apple Maps' own does. Nothing proposed here touches the map or the
  sheet's geometry, so the two can land in either order. **One interaction, and it
  decides the order:** §3.3 shortens the planning block, which forces a re-solve of
  `PlanningCompactDetent`'s two fitted constants against a device measurement. §6c
  changes what the sheet's height has to clear. Doing them in either order means
  measuring that block twice — so **apply §3.3 first and take both measurements in
  §6c's pass**, or accept the duplicate.
- **§3.3 needs the owner's yes**, because it answers §4's highest-value item with
  a deletion rather than the substitution §4 asked for.
- **These items should graduate to `roadmap.md`** when the work is scheduled —
  `docs/README.md`'s rule 4 exists because a defect flagged in three finished-
  looking documents is a defect nobody owns. Not added there by this change,
  because nothing here is scheduled yet.
- **Nothing here is a visual design.** The icon section is a direction and a
  commissioning brief; the mark does not exist and cannot be made to exist by
  this project without the authorship problem in §5.3.
