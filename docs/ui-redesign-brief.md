# UI and copy for Victory Lap — propose it, change no Swift

**Status: scoped 2026-09-20 against `main` at `897dbe7`, nothing changed and
nothing may be changed.** No Swift file, no asset, no string. **A rename is
running right now across the entire iOS target** (`claude/rename-to-victory-lap`)
— see Trap 1. The deliverable is one document.

**The finding that makes this worth a session: a UI copy redesign was already
written, and none of it shipped.** `docs/branding-brainstorm.md` §4–§6 specifies
the in-product naming, the copy and the visual identity. Measured on `main`
today:

| Recommendation (§4/§5) | In the code? |
| --- | --- |
| "good miles" instead of "mi beautiful" | **0 files** — `RouteResults.swift:103,106` still emit `"\(…) mi beautiful"` |
| Loop mode renamed **Nowhere** | **0 files** — it is still "Loop" |
| State the trade, not the setting | **not done** — `RoutePanel.swift:484` still reads `Text("scenery strength \(prefPosition…))` |
| Keep the green, rename the symbol (§6) | **already done** — `Theme.swift:10` is `static let brand`, see Trap 3 |

§4 calls the third of those "the single highest-value copy change in the app,"
and it is a one-line change that has been sitting unmade for three weeks.

---

## The actual intellectual work: §4–§6 were written for a different name

`branding-brainstorm.md` recommended **Longcut**. The owner chose **Victory Lap**
(2026-09-20, `docs/victory-lap-naming.md`). Some of §4–§6 is name-independent and
some is welded to the old name, and **nobody has separated the two**:

- **Name-independent, and still good.** "Good miles" instead of "mi beautiful".
  Stating the trade — `+38 min · 25 good miles` — instead of a 0–1 parameter.
  "The dial" as the internal name for the fastest↔scenic slider.
- **Welded to Longcut.** The tagline *"Take the long way."* The icon direction
  §6 picks — **"Two ways"**, a dashed straight line and a bold winding one
  between the same two dots — is chosen partly because "it pairs exactly with the
  name Longcut." Victory Lap is a different idea (the slow lap, after the race,
  driven for its own sake) and may want a different mark.
- **Superseded outright.** §5's App Store subtitle `Take the long way home.` The
  owner has chosen **`The scenic route, on purpose`**, verified at 28/30
  characters. That is decided; do not reopen it.
- **Open, and the most interesting question in this document.** Does **Nowhere**
  survive as the loop mode's name under Victory Lap, or does the new name suggest
  something better? §4's case for it is strong and independent of the app name —
  *"Nowhere in particular. Ninety minutes. We'll bring you home."* — but it was
  written to pair with a different brand.

## What the screens actually are

Measured on `main`, so a proposal can be specific rather than general:

```
RoutePanel.swift    544    the planning sheet — the dial, the route cards, Tune, About
NavView.swift       531    turn-by-turn, the two scenery-verdict buttons, the trip bar
LoopPanel.swift     275    loop mode ("Nowhere")
RouteResults.swift  255    the fastest-vs-scenic comparison copy
Models.swift        197    beautiful_km / beautiful_score reach the UI from here
ContentView.swift   183    the map and the sheet host
TuneView.swift       93    per-beauty-type weights
AboutView.swift     299    data sources + the required safety notice
Theme.swift           7    Color.brand only
```

The live copy worth reading before proposing anything: `RouteResults.swift:103`
and `:106` (`"… mi beautiful"`), `:186–193` (*"Scenic adds **49 min**…"*),
`LoopPanel.swift:182–183` and `:234–235` (*"19 of your 25 mi on beautiful road,
back where you started."*), and `RoutePanel.swift:484` (`scenery strength`).

---

## Traps

**1. Touch no file under `ios/`, and no asset.** The rename is *running* —
`claude/rename-to-victory-lap` exists and is rewriting `project.yml`,
`ScenicApp.swift`, the `SCENIC_*` prefix and every one of the 19 test files. A
redesign touches `RoutePanel`, `NavView`, `RouteResults`, `LoopPanel`,
`ContentView` — all of them in its path. **Write one markdown file.**

**2. Do not propose renaming anything `.scenic` in Swift.** All 34 occurrences
are the **routing-arm accessor** (`response.scenic`, `miles.scenic`) and they are
the client half of the API contract: `server/app.py:8` documents the response as
`{"fastest": …, "scenic": …}` and `Models.swift:12` decodes it **by property
name**, with no `CodingKeys`. Renaming them breaks decoding at runtime with no
compile error. The same rule governs the *visible* strings: `RoutePanel.swift:472`
and `RouteResults.swift:18` say "Scenic" because they name the **arm**, not the
app. `RoutePanel.swift:298` is the brand and is the rename's business, not yours.

**3. §6's colour recommendation is already done — do not propose it again.**
It says `Color.scenic = rgb(0.22, 0.83, 0.62)`, "rename the *symbol* with the
app; keep the *value*." `Theme.swift:10` already reads
`static let brand = Color(red: 0.22, green: 0.83, blue: 0.62)`, with a comment
saying it is named for the app rather than the arm on purpose. Keep the value —
§6 is right that it is the only brand equity the project has.

**4. One of §5's premises is now false, and it cuts in your favour.** §5 says not
to overclaim "because the scoring has never been validated against a human (the
README says so)." **It has been, since 2026-08-25.** 79 marks over 12 drives put
separation at **0.74 against a 0.63 noise floor** computed from those same sample
sizes. So "good miles" is better supported than §5 knew. **But it is one driver,
in one part of one state** — "measured" remains defensible, "validated" or
"beautiful, guaranteed" does not. Do not let the correction become licence to
overclaim; §5's rule survives its premise.

**5. The biggest UI change already has an owner and is not yours.**
`release-plan.md` §6c requires wrapping `MKMapView` in a `UIViewRepresentable`
and driving `layoutMargins.bottom` from the live sheet height, at
`ContentView.swift:40` **and** `NavView.swift:38` — because Apple's map
attribution is currently obscured at *every* detent, which Attachment 6 §4 names
as grounds to revoke MapKit access. It carries its own product decision (what
happens at `.large`). **Propose around it, note where a redesign would interact
with it, and do not design it.**

**6. Do not design the icon in a text file, and know the two hard constraints.**
**No SF Symbols** in an app icon, logo or trademark use — the Xcode/Apple SDKs
licence forbids glyphs "substantially or confusingly similar" there, which rules
out the obvious green-square-plus-`location.north.line.fill`. And **a human must
draw the final mark**: the current `icon-1024.png` is generated, so under the US
Copyright Office's position it may be owned by nobody. A direction and a brief
for an illustrator is the deliverable; a rendered PNG is not.

**7. The repo is public**, and this document describes an unreleased product's
identity.

---

## Done looks like

1. **One new document**, `docs/ui-redesign.md` — not this brief's filename —
   indexed in `docs/README.md`.
2. **§4–§6 triaged against the new name**, item by item: survives as written /
   survives with different wording / dead because it was Longcut-specific /
   already shipped. That separation is the core of the task.
3. **The copy layer specified concretely**, with the exact replacement strings
   and their `file:line` — at minimum `RouteResults.swift:103,106`,
   `RoutePanel.swift:484`, and `LoopPanel.swift:182,234`. Someone should be able
   to apply it after the rename lands without re-deciding anything.
4. **A verdict on "Nowhere"** for the loop mode under Victory Lap — keep,
   replace, or "this needs the owner", with the reasoning.
5. **An icon direction and an illustrator brief** — which of §6's four
   directions (or a new one) suits *Victory Lap*, what it must survive at 28px,
   and the two licence constraints stated for whoever draws it.
6. **A short list of anything else the screens need**, judged on whether a first
   user would notice. `roadmap.md`'s "the app still opens on Massachusetts"
   (`ios/Sources/Region.swift`) is a first-screen problem and is fair game;
   routing and instrument work is not.
7. **An honest-answer escape hatch.** "The existing §4 copy recommendations still
   stand and the name change affects only the tagline and the icon" is a complete
   answer — say it in a line rather than manufacturing a redesign. If a screen is
   genuinely fine, say it is fine.
