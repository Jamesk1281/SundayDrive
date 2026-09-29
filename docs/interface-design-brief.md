# Design the interface again, from nothing

> **Answered 2026-09-20 by [`interface-design.md`](interface-design.md) and
> [`interface-design-mockups.html`](interface-design-mockups.html).** Both superseded
> documents are deleted as §6.1 instructs. One finding goes against this brief’s
> framing: §6.2 asked whether `ui-redesign.md` was inaccurate, and it was not — every
> citation re-resolved against a *later* tree. The answer locates the defect in that
> document’s own brief instead, which had ruled the Apple attribution refactor out of
> scope. See §13.2 there.

**Status: commissioned 2026-09-20 against `main` at `0c967e2`. Nothing in
`ios/` has been touched and this task must not touch it either** — the
deliverable is a design, drawn and argued, not Swift. `docs/ui-redesign.md` and
`docs/ui-redesign-brief.md` are on `main` as of `1ed7d97` and this task
**deletes both**.

The owner's instruction, in his words: a redesign *"independent of any
documentation suggestions or plans in this app so far. only with knowledge of
what the app does and its name"*, presenting *"visualized design ideas and a
complete ui/ux overhaul that it sees fit"*.

That independence is the point of this brief, and it is the one thing here that
is easy to violate by accident. Everything below is either **a fact about the
product**, **a fact about the current screens**, or **a constraint that is
legal or contractual rather than aesthetic**. There are no design opinions in
this document, and you should not go looking for any elsewhere.

---

## 1. The firewall — read this before opening anything

**Do not read these. They are the opinions you are replacing:**

- `docs/ui-redesign.md` and `docs/ui-redesign-brief.md` — delete them (§6.1).
  Read only as much as §6.2's review requires, and do that **after** your own
  design exists, so it cannot anchor you.
- `docs/branding-brainstorm.md` §4–§6 — copy, tagline and icon proposals.
- `docs/victory-lap-naming.md` §6–§8 — App Store listing copy. The subtitle in
  §6a is a decided fact and is quoted for you in §2; do not mine the rest.
- Any other document in `docs/` that proposes, critiques or plans the
  interface.

**Do read the source.** Reading `ios/Sources/*.swift` is reading *the app*, not
the commentary on it, and you cannot overhaul an interface you have not seen.
§4 describes it, but read it yourself.

**Why the firewall is worth honouring even though it is unusual.** The document
you are deleting is not wrong on its facts — all three of the status claims in
its header were re-checked today against `main` and every one holds exactly.
What it is, is *derivative*: it triages an older brainstorm section by section
rather than designing anything, and the brainstorm it triages was written when
a different name was winning. The owner's judgement is that the result reads as
though it were assembled rather than designed. Starting from it would reproduce
that. So: no inheritance, including from its good parts.

---

## 2. What the app is

**Sunday Drive.** Subtitle, decided and final: *The scenic route, on purpose.*

*(The app was renamed Victory Lap → **Sunday Drive** on 2026-09-21, after this
brief was written — `docs/sunday-drive-naming.md`. The subtitle is
name-independent and is unchanged.)*

It is a **driving navigation app for people who do not want the fastest route.**
Pick a destination; it returns two routes — the fastest one, and a scenic one —
and a single control trades travel time for beauty between them. It then drives
you there turn by turn, out loud.

What makes it different from every other navigation app, and the thing worth
designing around:

- **Every road is measured, not submitted.** Each of 236,000 km of road in the
  six New England states carries a nine-component "beauty vector" — water,
  coastline, forest, curvature, terrain relief, farmland, viewpoints, scenic
  byway designation, townscape — computed from open geodata. Competitors curate
  routes from community submissions. This one scores the whole network.
- **The trade is a dial, not a toggle.** One control from *fastest* to *most
  scenic*. It buys up to **1.61x travel time** at the top.
- **Loop mode.** "Ninety minutes, nowhere to be, bring me home the pretty way" —
  give it a time or a distance and a starting point and it returns a round trip.
  There is no destination. This is arguably the actual product.
- **Per-scenery-type weighting.** The driver can say they care about water more
  than farmland, live per request.
- **It measures itself.** Two buttons on the driving screen record what the
  driver thinks of the road they are on.

Honest limits, because a design should not promise what the data cannot pay:
**New England only**; the terrain component saturates north of Massachusetts,
so scenery quality is *not* uniform across the six states; there is **no lane
guidance** and cannot be (the data covers 4.6%–23.8% of junction approaches);
and there is no live traffic.

---

## 3. Who is holding it, and when

Design for this and nothing else:

- **iPhone, one hand, in a car.** Often in a windscreen mount, often in
  sunlight, sometimes moving. The planning half is used parked; the driving half
  is used at 50 mph and must be readable in the half-second a driver can spare.
- **No CarPlay.** No iPad, no Watch, no widgets. Portrait iPhone is the whole
  surface.
- **Two distinct modes** with different rules: **planning** (leisurely, dense,
  exploratory — the user is choosing) and **driving** (glanceable, sparse,
  loud — the user is not looking). They currently share a map.

---

## 4. The interface as it stands today

Factual, so you know what you are replacing. All of it is on the table.

**Built with SwiftUI and MapKit, with zero third-party dependencies** — every
import is an Apple framework. That is a real constraint: whatever you draw has
to be buildable from SwiftUI, MapKit and the system SDKs alone. No Lottie, no
custom rendering library, no web view.

- **`ContentView.swift`** — a full-screen `Map`, with a planning sheet
  presented over it permanently (`.sheet(isPresented: .constant(true))`) at
  three detents: a custom `.planningCompact`, `.medium`, `.large`. Every cold
  launch opens at `.planningCompact`.
- **`RoutePanel.swift`** (550 lines, the main surface) — destination search,
  the fastest-vs-scenic slider, the two route result cards, the loop controls,
  and a pinned data-credit row. Entry points to two further sheets: Tune and
  About.
- **`TuneView.swift`** — the per-scenery-type weights, in its own sheet at
  `.medium`/`.large`.
- **`LoopPanel.swift`** — loop planning, a second mode inside the same panel.
- **`RouteResults.swift`** — the two comparison cards, fastest against scenic.
- **`NavView.swift`** — the driving screen: maneuver banner, distance and ETA,
  the two scenery-marking buttons, a switch-to-fastest escape hatch.
- **`AboutView.swift`** — credits, data sources, and the safety notice in §5.
- **`Theme.swift:10`** — `Color.brand` is `rgb(0.22, 0.83, 0.62)`, a mid green.
  It is the only visual equity the project has, which is an argument for keeping
  it and not an instruction. **Changing it is in scope.**

Three strings, quoted because they are what the interface literally says today
and you should know its register before choosing a new one:

- `RoutePanel.swift:484` — `"scenery strength 0.25"`, printing a raw 0–1
  parameter to the driver.
- `RouteResults.swift:103,106` — `"25 mi beautiful"`.
- `RouteModel.swift:19` — the loop mode is labelled `"Loop"`.

---

## 5. Constraints that are not negotiable

These are contractual, legal or test-asserted. A design that breaks one cannot
ship, however good it is. They are also genuinely *shaping* constraints, so
read them as material rather than as a fence.

1. **Apple's map attribution and logo must never be obscured** — Apple
   Developer Program Licence Agreement, Attachment 6 §2.1, and §4 names
   obscuring the logo as grounds for revoking MapKit access outright. **The
   current design breaches this**: the planning sheet covers the logo at
   *every* detent, not just the tall one. This is the single largest open
   defect in the app and the one your layout most directly controls. A design
   that keeps an opaque panel pinned across the bottom of the map reproduces
   the breach. Treat it as a brief: *the bottom-left of the map belongs to
   Apple.*
2. **The OpenStreetMap credit must be visible without interaction.** The ODbL
   and the OSM Foundation's guideline both require the credit be presented
   where a reader sees it — *"should not require individuals to interact with
   the map or produced work to see"* it. A credits screen one tap away is a
   supplement, **not** a substitute. So "move the credits into About" is not
   available to you. It must survive on a visible surface, legibly.
3. **The route-guidance safety notice is fixed text and must appear exactly
   once**, character for character, capitals included:
   `YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE RISK.
   LOCATION DATA MAY NOT BE ACCURATE.` It is at `AboutView.swift:101` under a
   `SAFETY` heading, and two tests pin it. **Do not reword it, do not translate
   it, do not add a second copy.** You may move it and restyle around it.
4. **Do not put the app's name back into the interface.** The owner removed it
   from the panel header, the About screen and the location purpose string on
   2026-09-20, deliberately, because the name is *"not as descriptive or
   mood-adjacent to the rest of it"*. The only place a user should read
   "Sunday Drive" is the home-screen icon label. Designing a splash screen or a
   branded header would undo a decision taken two days ago. **The instruction
   survived the 2026-09-21 rename unchanged** — the removal was of *a* product
   name, not of that one, and `ios/project.yml:21`'s purpose string still names
   no app at all.
5. **If you propose an icon: SF Symbols may not be used in app icons, logos or
   trademarks** under the Xcode and Apple SDK licence. Inside the app,
   `systemImage:` is fine. Also worth knowing: the current `icon-1024.png` is
   machine-generated, and under the US Copyright Office's position a generated
   mark may not be copyrightable by anyone — so an icon direction should assume
   a human illustrator draws the final artwork.
6. **The word "scenic" stays in the vocabulary.** It is correct English for the
   feature — the scenic route, the scenic score, the scenic arm — and it is the
   *brand* use that was renamed away, not the descriptive one.
   `RoutePanel.swift:472` labels the slider's scenic end and must keep doing so
   in substance.

---

## 6. What to deliver

### 6.1 Delete the superseded design documents

`git rm docs/ui-redesign.md docs/ui-redesign-brief.md`, and **remove their row
from the `docs/README.md` index in the same commit** or the index will point at
a dead file. Git history retains both (`1ed7d97`), so nothing is lost.

Note this cuts against `docs/README.md`'s own "archive rather than delete"
convention. It is a deliberate owner instruction, not an oversight — say so in
the commit message.

### 6.2 A short, honest review of what you deleted

One section, **written after your own design is drafted**, two or three
paragraphs. The owner's stated reason for binning it is that it reads as though
it were produced in *"a hallucinated state"*. Test that claim rather than
repeating it: its factual citations were re-checked today and hold, so if you
find the same, say so, and locate the real defect somewhere other than
accuracy. If you find genuine fabrication, quote it. **A finding of "it was
substantially correct and simply not what was wanted" is an acceptable and
useful answer** — do not manufacture fault to justify the deletion.

### 6.3 The design — `docs/interface-design.md`

A complete interface and experience proposal, yours, argued. Cover at least:
the information architecture and how planning and driving relate; the planning
flow end to end; the driving screen; how the time-for-beauty trade is presented
(it is the product's central idea and today it prints a decimal); how loop mode
is reached and framed; the scenery-type weighting; typography, colour and dark
mode; the compliance surfaces from §5 as *designed elements* rather than
obligations bolted on; and motion, if it earns its place.

State your reasoning. Where you reject an obvious alternative, say why.

### 6.4 Show it — this is the part he actually asked for

Words about a design are not a design. Produce **rendered, viewable mockups**:

- A **self-contained HTML file**, `docs/interface-design-mockups.html`, that
  opens in a browser with no server and no network — inline SVG or CSS, no CDN
  links, no external fonts. Phone-framed screens at realistic proportions, light
  and dark, covering every screen in §6.3.
- **Render the key screens inline in the session too**, so he can see them
  without opening a file, and send him the HTML file when it is ready.

Make them look like the product, not like wireframes — real map colour, real
type, real copy, real data. Use plausible New England place names and real
numbers from §2 rather than lorem ipsum.

---

## 7. Traps

1. **Do not write any Swift, and do not touch `ios/`.** The overhaul is being
   *presented* for a decision, and implementing it before he has chosen is the
   expensive order to do this in. If you find yourself opening an editor on a
   `.swift` file to "check feasibility", read it instead.
2. **Do not design the bottom sheet back over Apple's logo.** §5.1. This is the
   easiest constraint in the document to violate, because a bottom sheet over a
   map is the obvious iOS pattern and it is exactly what is already broken.
3. **Do not quietly relocate the OSM credit into a sub-screen.** §5.2. It reads
   like clutter and it is load-bearing.
4. **Do not read the deleted documents for inspiration first.** §1. Draft your
   design, then open them only for §6.2.
5. **`.planningCompact` is a custom detent, not a system one** — if you keep a
   sheet, know that the compact height is bespoke and that every cold launch
   lands there, so it is the height that has to work hardest.
6. **Your mockups must render offline.** A mockup that silently fails to load a
   web font shows him broken boxes. Inline everything.

---

## 8. Done looks like

1. `docs/ui-redesign.md` and `docs/ui-redesign-brief.md` are deleted and the
   `docs/README.md` index no longer references them.
2. `docs/interface-design.md` exists, opens with a `**Status:**` line naming the
   commit it was written against, and contains a complete argued design plus the
   §6.2 review.
3. `docs/interface-design-mockups.html` exists, is self-contained, and renders
   every screen the document describes in both light and dark.
4. The key screens have been rendered inline in the session, and the HTML file
   sent to the owner.
5. Every §5 constraint is either visibly satisfied in the mockups or explicitly
   argued about in the document. Silence on one is a failure.
6. No file under `ios/` has changed. `git status` proves it.
7. **Or**, if some part of this cannot be done as specified, a plain statement
   of which part and why — that is a better outcome than a design that quietly
   drops a constraint.

---

## 9. Working notes

- **Branch off `main`, not on it.** Name the branch for the work.
- **This brief is committed to `main`** (unusually — a task chip opens a fresh
  worktree, which would not see an untracked file). Do not delete it; it is the
  question, and `docs/README.md`'s rule 2 wants it pointed at its answer.
- **Add both new documents to the `docs/README.md` index**, under "The app".
- **No build or test run is needed** — nothing you touch is compiled. The
  backend suite is **379 passed** as of `0c967e2` and you should leave it there.
  If you somehow need it: `SUNDAYDRIVE_DATA=<main checkout>/data/processed-ne
  .venv/bin/python -m pytest tests/ -q`, from the *main* checkout, where the
  data and the venv live. The project path contains spaces, so always
  `.venv/bin/python -m <tool>`, never the console script.
- **The return leg is this repo's documented failure mode** — thirteen finished
  branches piled up unmerged once, and a decision recorded only in an unmerged
  commit message caused a later planning document to re-open settled work. When
  you are done, say plainly that the branch is ready and what it touches.
