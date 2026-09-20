# "Victory Lap": the screen, and the listing it justifies

**Status: screened and drafted 2026-09-20, against `main` at `2d6fbc0`. Nothing
was filed, bought, reserved or renamed.** No identifier in the codebase was
touched — that is [`release-plan.md`](release-plan.md) §6b and it is a separate
job. This document is copy and evidence.

**Nobody here is a lawyer and nothing below is legal advice.**

Answers [`victory-lap-naming-brief.md`](victory-lap-naming-brief.md). Companion
piece to [`trademark-knockout-findings.md`](trademark-knockout-findings.md),
which screens the four fallback names (Longcut, Aimless, Detourist, Camber) and
which — after this brief was written — added its own §15 on Victory Lap. **That
overlap turned out to be worth having**: §3 below is an independent re-run, and
it reproduces §15's register numbers exactly while correcting one of its
domain facts. Where the two documents disagree, §11 says so.

**Two links in here are forward references.** Neither
`docs/release-plan.md` (branch `claude/release-plan-sequence`) nor
`docs/trademark-knockout-findings.md` (branch `trademark-knockout-screen`) is on
`main` as of `2d6fbc0`, so those links dangle until those branches merge. They
are cited rather than quoted at length because both are substantial documents
that should land on their own merits; this one does not depend on either being
merged first.

---

## The short answers

1. **Victory Lap survives the knockout screen.** No knockout blocker found —
   proceed to professional clearance.
2. **The owner has chosen `The scenic route, on purpose` as the subtitle**
   (2026-09-20), against this document's recommendation. **That is the
   decision and it is not being reopened here.** The evidence that argued the
   other way is left standing in §5 and §6, unedited, because it is what a
   re-read would need — not because the question is open. §6a records the
   decision and the one thing worth knowing if it is ever challenged.
3. **The recommendation it overrode**, for the record: keep "Scenic" out of
   the name and subtitle, keep it in the keywords and the description. The
   analysis is graduated by field rather than a ban — §6.
4. **"Victory Lap - The Scenic Route" is exactly 30 characters and therefore
   fits** either field. Fitting is not the objection; §6 is.

---

## 1. The positive control, reported first

The method was run on **"Scenic"** first, because the answer is known: there is
a senior, established, directly-competing navigation app of exactly that name.
If the method cannot find it, nothing else here is worth reading.

Both legs were run, and **they disagree in the same way
[`trademark-knockout-findings.md`](trademark-knockout-findings.md) §1 found**:

| Leg | Result for "Scenic" | Control |
| --- | --- | --- |
| **App Store search API** | *Scenic Motorcycle Navigation*, Applified Life Ltd., bundle `com.pinguido.scenic`, released 2016-07-21, category **Navigation**, free | ✅ **found it, first result** |
| **Federal register** (`tmsearch.uspto.gov`) | 417 marks contain the string. Owner search `Applified` → 2 records, neither the competitor; `Pinguido` → **0** | ❌ **missed it entirely** |

The competitor holds no US federal trademark record. **A register search alone
cannot clear a name in this field, and this is the measurement that proves it.**
Read every "register: nothing found" in §3 against that.

**The register leg did independently knock "Scenic" out, by a different party**
— and the detail matters for §6. `SCENIC`, **Scenic Tours Europe AG**
(Switzerland), serial **79431580**, a live §66(a) Madrid designation filed
2025-05-13, status **NON-FINAL ACTION – MAILED** as of 2026-09-20, covering
IC 009, 012, 016, 025, 035, 039, 041, 042 and 043. **Classes 9, 39 and 42 are
this product's classes.** The same owner has eight further live `SCENIC *`
marks; `SCENIC VANS` (reg. 8162022, IC 012/039) and `FLORIDA SCENIC HIGHWAY`
(reg. 3217061, IC 039, *"providing information in the field of automotive
travel via the Internet"*) are live to third parties in the travel classes.

**The control passes as a whole and fails one leg, and the failure is the
finding.**

---

## 2. Verdict on VICTORY LAP

> **No knockout blocker found — proceed to professional clearance.**

The words *clear* and *available* are not used in this document, and should not
be used in any document that cites it. The permitted verdicts are the three in
[`trademark-knockout-findings.md`](trademark-knockout-findings.md) §"This is a
knockout search, not a clearance search": *no knockout blocker found* /
*blocked* / *cannot be determined from public sources*.

A note on what "proceed to professional clearance" means here, because
[`release-plan.md`](release-plan.md) and the brief read it differently. The
brief says §5.2 "still calls for a professional engagement." It does not:
**Decision 2 declined paid clearance** and replaced it with the free search,
on the reasoning that the realistic failure mode for a free app is an App Store
complaint rather than litigation, and that the cost of being wrong is a rename
at low download counts. That decision is the owner's and this document does not
reopen it. The verdict wording is the honest ceiling of *this* screen, not a
demand that the engagement be booked.

---

## 3. The register screen

**System:** `tmsearch.uspto.gov`, the Elasticsearch endpoint
`POST https://tmsearch.uspto.gov/prod-stage-v1-0-0/tmsearch`, `query_string`
syntax, run 2026-09-20. TESS was retired 2023-11-30 and is not an option.
Re-run instructions are in §10.

### Controls first — a zero is only believable if the machinery works

| Control query | Hits |
| --- | --- |
| `wordmark:*scenic*` | **417** |
| `wordmark:*lap*` | **7,886** |
| `wordmark:*victory*` | **2,915** |
| `internationalClass:("IC 009") AND alive:true` | **621,725** |

All non-zero, all matching the companion document's controls. The zeros below
are real zeros.

### Counts

| Query | Hits |
| --- | --- |
| `wordmark:*victorylap*` — one word, substring, every class and status | 1 |
| `wordmark:VICTORYLAP` | 1 |
| `wordmark:"VICTORY LAP"` — all classes, all statuses | **30** |
| `wordmark:"VICTORY LAP" AND alive:true` | **7** |
| `wordmark:"VICTORY LAPS"` | 0 |
| `wordmarkPseudoText:"VICTORY LAP"` — USPTO's own alternate-spelling field | 3 |
| `wordmark:VICTORYLAP~1` — one character's difference | 3, all dead |
| `wordmark:VICTORYLAP~2` | 7 |
| `wordmark:(VICTORY AND LAP) AND internationalClass:("IC 009")` | 2, **both abandoned** |
| `wordmark:(VICTORY AND LAP) AND internationalClass:("IC 039")` | 1, **abandoned** |
| `wordmark:(VICTORY AND LAP) AND internationalClass:("IC 042")` | **0** |
| **`wordmark:(VICTORY AND LAP)` live in 9 / 39 / 42** | **0** |

### The seven live marks, in full

| Mark | Owner | Serial / Reg. | Class | Goods and services | Status |
| --- | --- | --- | --- | --- | --- |
| `VICTORY LAP` | Clean Plus, Inc. (MN) | 74205924 / **1769701** | 012, 007 | Starter repair kits for land vehicles; alternator repair kits | REGISTERED AND RENEWED |
| `VICTORY LAP` | Victory Lap LLC (IL) | 87501440 / **5511282** | 035, 041 | Employment recruiting, counseling, job placement; sales training | SECTION 8 – ACCEPTED |
| `VICTORY LAP` | Victory Lap Clothing Co LLC (NY) | 88676458 / **6064185** | 025 | Clothing: bandanas, beachwear, belts, blazers, caps … | SECTION 8 & 15 – ACCEPTED |
| `VICTORY LAP` | Lincoln Ventures, LLC (TX) | 98693923 / **7778175** | 043 | Restaurant and bar services | REGISTERED |
| `VICTORY LAP` | VICTORY LAP INC. (DE) | 98906306 | 005 | Dietary supplements | STATEMENT OF USE – TO EXAMINER |
| `VICTORY LAP SPORTS CARDS & COLLECTIBLES` | Edgar Alminar | 99153376 / **8249563** | 016 | Collectible printed trading cards | REGISTERED |
| `VICTORY LAP POOLS` | Paradise Pools & Landscapes, Inc. (CA) | 99556221 | 037 | Swimming pool cleaning, maintenance, construction | NOTICE OF ALLOWANCE – ISSUED |

**Nothing in software, navigation, mapping, travel or transport.**

### Every attempt in this product's classes is dead

| Mark | Owner | Serial | Class | Goods | Status |
| --- | --- | --- | --- | --- | --- |
| `VICTORY LAP` | Video Gaming Technologies, Inc. | 78622026 | 009 | Software and firmware for games of chance | ABANDONED – failure to respond |
| `VICTORY LAP` | Bandai Namco Entertainment | 90710268 | 009, 028, 041 | Recorded computer game software and programs | ABANDONED – failure to respond |
| `VICTORY LAP` | Victory Airlines Corporation | 78550035 | 039 | Airline customer loyalty and frequent flyer programs | ABANDONED – no statement of use |
| `VICTORY LAP` | Kellogg Company | 75652704 / 2348414 | 041 | Sponsoring and participating in automobile races | CANCELLED – §8 |
| `VICTORY LAP` | Kellogg Company | 75184075 | 041 | Sponsoring professional auto races | ABANDONED – no statement of use |
| `THE VICTORY LAP` | Race Rock International, Inc. | 75471881 / 2521483 | 029, 030 | Desserts | CANCELLED – §8 |
| `VICTORY LAP HOBBIES` | Three Wards, LLC | 86601103 | 028 | Toy model cars and kit cars | ABANDONED – failure to respond |
| `VICTORY LAP MEDIA` | Victory Lap Media, LLC | 86807449 | 041 | Film and television production | ABANDONED – no statement of use |
| `VICTORY LAP BAR & GRILL` | Autobahn Indoor Speedway, LLC | 87425790 / 5429856 | 043 | Restaurant and bar services | CANCELLED – §8 |

Two games companies and an airline reached for classes 9 and 39 and let them
go. **Per the brief's Trap 4 that removes the registrations, not whatever rights
their use created** — but these are well-resourced companies abandoning
applications, not small users quietly trading on, and none of them appears on
the App Store under the name (§4).

### Similar marks, not just the exact string

The brief is right that a phrase screen that only looks for the phrase is
worthless. Three additional cuts, all in this product's classes:

| Query | Hits | What they are |
| --- | --- | --- |
| `wordmark:VICTORY` live in IC 009 | 76 | crowded, and none is navigation or mapping |
| `wordmark:VICTORY` live in IC 039 | 8 | — |
| `wordmark:VICTORY` live in IC 042 | 34 | — |
| `wordmark:VICTORY` live in 9/39/42 **with navigation/mapping/GPS/route goods** | **1** | `THE GREATEST VICTORY REQUIRES NO WAR`, Shield AI, Inc., serial 97652936 — **tactical robots** |
| `wordmark:LAP` live in IC 009 | 18 | see below |
| `wordmark:LAP` live in IC 039 | **1** | `RUN A LAP RENTALS`, reg. 6808168 — motor coach and vehicle rental |
| `wordmark:LAP` live in 9/39/42 **with navigation/mapping/GPS goods** | **1** | `AUTO LAP`, **Garmin Ltd.**, reg. 2950644, IC 009 — *"electronic exercise monitors featuring a GPS receiver"* |

**`AUTO LAP` is the nearest live technology neighbour and is worth naming for
the attorney** — a GPS company holding a LAP-formative class 9 registration.
The goods are exercise monitors, not navigation software, so this screen does
not treat it as a blocker. The other 17 live `LAP` marks in class 9 are radar
systems, laser alignment, laptop bags, eyewear, and racing video games
(`FINAL LAP`, `HOT LAP LEAGUE`, `PHAR LAP`, `DEATH LAP`) — the racing-games
cluster is a tone signal, not a legal one.

**`VICTORY LAP` reg. 1769701 (Clean Plus, Inc.) is the only live mark in a
vehicle-related class** — IC 012, registered 1991 and renewed since. Automotive
*parts*, not software or services. Named because a professional searcher would
look at it.

### The Nipsey Hussle check, done by owner rather than by inference

*Victory Lap* (2018) is a Grammy-nominated album and the phrase carries that
association for a great many people. The brief says check it rather than reason
from the class. Checked two ways:

- `ownerFullText:Asghedom` → **44 records, 24 distinct marks**: `NIPSEY HUSSLE`,
  `NIPSEY BLUE`, `ALL MONEY IN`, `CRENSHAW`, `TMC`, `PROUD 2 PAY`, `PROLIFIC`,
  the `MARATHON` family, `BLACCSAM`, `ADELIA`, `SOUTH CENTRAL STATE OF MIND`,
  `RUN A LAP`, and the personal names. **`VICTORY LAP` is not among them.**
- `wordmark:(VICTORY AND LAP) AND goodsAndServices:(music OR "sound recordings"
  OR musical)` → **0**.

**There is no `VICTORY LAP` mark on the US federal register in recorded-music
goods, held by that estate or by anyone else.** Recorded as a fact about the
register, not as a claim about any party. Note in passing that the estate does
hold a lap-metaphor mark — `RUN A LAP`, reg. 6964791, IC 025 clothing — so the
absence of a `VICTORY LAP` filing is not for want of filing activity.

---

## 4. The common-law leg

Run separately, because §1 shows the register is the leg that misses things.

- **App Store, US, 2026-09-20.** `term=Victory Lap` → 144 results, **0 with the
  phrase in the app name**, 0 in Navigation or Travel. `term=victorylap` → 2
  results, both games, neither named for the phrase. `term=Victory` → 193
  results, 108 with the word in the name, **0 of those in Navigation or
  Travel**. The three brief-cited figures reproduce exactly.
- **What actually ranks** for "victory lap" in the US store is a motorsport
  cluster — *Victory Race Engineer*, *dragy·Lap*, *MYLAPS Speedhive*,
  *LapTrophy*, *Golden Lap*, *Asphalt 8*. Nothing in Navigation. This is a
  positioning signal, not a conflict: the store currently reads the phrase as
  *racing*, which is the objection the brief raises and §8 addresses.
- **No navigation, mapping, travel or road-trip business under the name was
  found** on the open web.
- **The largest user of the phrase is `victorylap.io`** — a Chicago sales
  recruiting and training company, "since 2016 … over 400 leading
  organizations." This is the owner of reg. 5511282 (IC 035/041). The site is
  live and substantial. **Unrelated field.** *(This corrects
  [`trademark-knockout-findings.md`](trademark-knockout-findings.md) §15, which
  identified the company but not its domain.)*

### Domains, measured 2026-09-20

| Domain | State |
| --- | --- |
| `victorylap.io` | **Registered and serving the sales-training company above** (42.9 kB page) |
| `victorylap.com` | Registered 1997-03-07, GoDaddy. Resolves, serves a **114-byte** parking response |
| `victorylap.app` | Resolves to a parking IP; **no HTTPS response** |
| `getvictorylap.com` | Registered 2025-01-28, Namecheap. Resolves; no HTTPS response |
| **`victorylapapp.com`** | **Unregistered** — whois "No match" |
| **`takethevictorylap.com`** | **Unregistered** — whois "No match" |
| `victorylap.co` | **Cannot be determined from public sources.** The command-line whois chain gave a 2019 creation date on one pass and only the IANA `.co` record on a direct re-query; there is no A record either way. *(This contradicts [`trademark-knockout-findings.md`](trademark-knockout-findings.md) §15, which lists it as free. Neither reading is confirmed — check it at the registrar before relying on it.)* |

`takethevictorylap.com` being free is the exact parallel of `takethelongcut.com`
in the companion document, and it fits the tagline better than any
`*app.com` does.

---

## 5. The subtitle measurement, re-run — and it is worse than the brief says

The brief reports six Navigation/Travel apps with "scenic" in the name. **Same
query, same method, 2026-09-20: it is 25.**

```
itunes.apple.com/search?term=Scenic&entity=software&country=us&limit=200
  → 157 results, 43 with "scenic" in the app NAME
     14 in Navigation, 11 in Travel  ... 25 in the two categories that matter
```

| App | Category | Publisher | Released |
| --- | --- | --- | --- |
| **Scenic Motorcycle Navigation** | **Navigation** | Applified Life Ltd. | 2016-07-21 |
| Scenic Way | Navigation | Turnkey I.T Solutions Ltd (bundle `uk.co.turnkeyit.ScenicRoute`) | 2026-07-18 |
| Detour - Scenic Navigation | Navigation | Kozlo LLC | 2024-05-02 |
| RevRoutes Find Scenic Drives | Navigation | Tengy LLc | 2026-05-14 |
| Trailblaze: Scenic Routes | Navigation | Andrey Takhtamirov | 2024-01-30 |
| Scenic Routes: Walk & Transit | Navigation | Feng Xinyuan (bundle `uk.co.scenicroutes`) | 2026-06-17 |
| `Scenic Map` ×8 — Western/Central/Eastern USA, Western/Central/Eastern Canada, Alaska, and the base app | Navigation | Mark Granger, 2010–2015, free to $4.99 | |
| Scenra: Scenic Road Trips, Sedona GPS, Scenic Spots (Hawaii, New York), Scenic Lookouts Australia, GoodView, Lume, Covered Bridges Scenic Byway, Mt. Rainier Scenic Railroad, Kuranda Scenic Railway, Scenic Luxury Cruises | Travel | various | |

**Two of these are not in the brief and matter more than the ones that are.**
*Scenic Way*'s bundle identifier is literally `uk.co.turnkeyit.ScenicRoute`, and
*Scenic Routes: Walk & Transit* is `uk.co.scenicroutes`. **The exact phrase the
proposed subtitle uses is already a shipping product's identifier in the
Navigation category, twice.** In the visible name, two Navigation apps carry
"Scenic Routes" (a third, *Scenic Route's Generations*, is a game) — and a
separate query, `term=scenic route`, returns **157 results and zero apps with
"the scenic route" in the name**. The definite article is the only part of the
proposed subtitle that nobody has taken.

The brief's undercount is not a sloppiness — it is the same failure mode
`branding-brainstorm.md` §3 had, which is that eyeballing a ranked list stops
early. Four times as many is a different argument.

---

## 6. Should "Scenic" be in the listing? A graduated answer

The brief asks for the argument, not a predetermined result. Here it is, and it
is **not** a ban: the four metadata fields carry different exposure and deserve
different answers.

### The argument against the visible fields is Apple's, not a lawyer's

**App Review Guideline 2.3.7**, quoted exactly:

> "Choose a unique app name … don't try to pack any of your metadata with
> trademarked terms, popular app names, pricing information, or other
> irrelevant phrases just to game the system. … **App subtitles … should not
> include inappropriate content, reference other apps, or make unverifiable
> product claims.**"

And **5.2.1**: "don't include misleading, false, or copycat representations,
names, or metadata."

A subtitle reading *The Scenic Route*, on a Navigation app, in a store where the
senior Navigation incumbent is an app called **Scenic**, is a subtitle that a
complainant can characterise as referencing another app in one sentence. The
relevant fact is not whether that characterisation would ultimately win. It is
that **[`release-plan.md`](release-plan.md) Decision 2 already identified the
realistic failure mode as an App Store complaint — cheap to file, and capable of
pulling an app pending resolution** — and this is the single cheapest way to
hand someone the form to fill in.

**The register adds a second, independent reason the brief did not have.**
`SCENIC`, serial 79431580, Scenic Tours Europe AG, is a **live application under
examination covering IC 009, 039 and 042** (§1). If it registers, the exact word
is a live US registration in this product's own classes, held by a travel
company. **That is a register-side argument, and it stands even if every one
of the 25 App Store uses in §5 is purely descriptive.**

### The honest counter-argument, stated properly

"The scenic route" is ordinary English and has been since long before any of
these apps. Descriptive fair use is a real defence, and using a common adjective
to describe what a product does is not the same act as adopting it as a source
identifier. The brief is right that this distinction is real, and it is right
that it is a question for a professional rather than for a copywriter.

**What settles it for the recommendation is not who would win. It is that the
alternatives cost nothing.** §7 has two subtitles that are at least as good as
*The Scenic Route* on their own merits and carry none of this. When one side of
a trade is free, you do not need to resolve the other side.

### The graduated position

| Field | Visible? | Recommendation | Why |
| --- | --- | --- | --- |
| **Name** (30) | Yes, everywhere | **No.** `Victory Lap` alone | Use in commerce as a mark, in the incumbent's category. The strongest form of the objection |
| **Subtitle** (30) | Yes, under the name | **No** — ***overruled by the owner, see §6a*** | Guideline 2.3.7 names subtitles specifically |
| **Keywords** (100 bytes) | **No** — never shown to a user | **Yes, include `scenic`** | Not displayed, so not a source identifier to any consumer. Purely functional and descriptive. It is the single highest-value search term this app has, and losing it costs real installs. The rule in Apple's reference — *"Names of other apps or companies aren't allowed"* — is aimed at packing a competitor's brand, not at an English adjective describing your own feature. **Risk is not zero:** the worst case is a metadata rejection, which costs one review cycle and is fixed by deleting a word |
| **Description** (4000) | Yes | **Yes, sparingly — twice** | Running prose, plainly descriptive, and Apple's own reference says the description "will be used for web engine search results," so it is where the term earns its SEO. Not a title, not a claim of source |

**One boundary worth stating, because the rename job will hit it.** The word
also appears in the app's own UI, as the right-hand label of the Fastest↔Scenic
slider (`RoutePanel.swift:472`). That is the *arm name* — correct English for
the feature — and [`release-plan.md`](release-plan.md) §6b is explicit that it
must not change. **In-app feature vocabulary and App Store metadata are
different questions and this document only answers the second.**

### 6a. The decision taken, 2026-09-20

**The owner chose `The scenic route, on purpose`.** The recommendation above
was to avoid the word in that field; it was overruled with the evidence in
front of the decision, which is the owner's call to make. The listing in §7 is
written to that decision.

Three things worth recording rather than re-arguing:

1. **The requested wording was `Take the scenic route on purpose`, which is 32
   characters and cannot be entered.** The chosen string is the repair that
   keeps the phrase and "on purpose" inside the 30-character field.
2. **Nothing in §5 or §6 changes.** Twenty-five Navigation/Travel apps carry
   the word, the senior incumbent among them is named for it, and Scenic Tours
   Europe AG's IC 009/039/042 application is live and under examination. The
   decision accepts that exposure; it does not dissolve it.
3. **If it is ever challenged, the subtitle is metadata, not a binary.**
   Changing it costs an App Store Connect edit rather than a new build — which
   is materially cheaper than a rename, and is the reason this is a reversible
   decision rather than a permanent one. The bundle identifier, which is
   permanent, is untouched and carries no form of the word that is at issue
   here.

---

## 7. The listing, inside verified limits

### The limits, verified rather than assumed

All from Apple's own App Store Connect Help, read 2026-09-20:

| Field | Limit | Source |
| --- | --- | --- |
| **Name** | 2–30 characters | [App information](https://developer.apple.com/help/app-store-connect/reference/app-information/) — "at least two characters and no more than 30 characters" |
| **Subtitle** | ≤ 30 characters | *ibid.* — "can't be longer than 30 characters" |
| **Promotional Text** | ≤ 170 characters | [Platform version information](https://developer.apple.com/help/app-store-connect/reference/platform-version-information/) |
| **Description** | ≤ 4000 characters, **plain text, HTML not supported** | *ibid.* |
| **Keywords** | **≤ 100 *bytes***, each term > 2 characters | *ibid.* — "up to 100 bytes"; and "Names of other apps or companies aren't allowed" |
| What's New | ≤ 4000 characters | *ibid.* — not required for a first version |
| App Review Notes | ≤ 4000 bytes | *ibid.* |

Note the keyword limit is **bytes, not characters** — an em-dash or accented
character costs more than one. Every string below is pure ASCII, so for these
drafts bytes and characters are equal.

**Trap 6, resolved.** `Victory Lap - The Scenic Route` is **exactly 30
characters**, so it fits the Name field and it fits the Subtitle field. It is
not rejected on length in either. §6 is the objection, not the ruler.

### Recommended

| Field | Value | Count |
| --- | --- | --- |
| **Name** | `Victory Lap` | 11 / 30 |
| **Subtitle** | `The scenic route, on purpose` | 28 / 30 |

**Chosen by the owner 2026-09-20 (§6a)**, over this document's recommendation
of `Take the long way on purpose`. The options table below is left as written
so the choice is legible; option 4 is the one that was taken.

Using only 11 of 30 name characters is deliberate. The name field is what
appears under the icon on the home screen, where it is truncated hard; a short
name survives that, and a descriptor bolted into the name field burns the
subtitle's separate 30 characters for nothing.

### Subtitle options, in order

| # | Subtitle | Chars | Contains "Scenic"? | Note |
| --- | --- | --- | --- | --- |
| **1** | `Take the long way on purpose` | 28 | No | **Recommended.** Carries `branding-brainstorm.md` §5's tagline, answers the "is this a racing app?" problem in six words, and "on purpose" is the whole thesis. Invitation architecture |
| **2** | `Every road, scored for beauty` | 29 | No | **Recommended alternative.** Instrument architecture — the one claim no competitor can make, and it is verifiable, which matters because 2.3.7 forbids "unverifiable product claims" |
| 3 | `Drive the long way home` | 23 | No | Warmer, loop-mode flavoured, slightly vaguer |
| **4** | `The scenic route, on purpose` | 28 | **Yes** | **CHOSEN — §6a.** The owner's phrasing, repaired to fit: the requested `Take the scenic route on purpose` is 32 characters. Not this document's recommendation, and §5–§6 say why |
| 4a | `The Scenic Route` | 16 | **Yes** | The bare phrase, as first proposed. Superseded by 4, which at no extra cost buys back the "this is not a racing app" work that options 1–3 were doing |

Options 1 and 2 discharge the brief's requirement for at least two Scenic-free
subtitles. They were not taken, and they are recorded here rather than deleted
because a subtitle is an App Store Connect edit rather than a build (§6a), so
this table is the shortlist if the decision is ever revisited. Option 2's
claim still reaches the listing either way — it is the description's first
section heading.

### Keywords — 97 / 100 bytes

**Instructed by the owner 2026-09-20: the scenic terms go in.** They do, and
§6's analysis already recommended `scenic` here — the keyword field is the one
place the word was never in question, because nothing in it is displayed to a
user.

```
scenic,route,backroad,byway,countryside,road trip,loop,curvy,touring,twisty,coastal,weekend,drive
```

**`scenic` and `route` are two terms rather than the phrase `scenic route`, and
that is deliberate.** `scenic,route` and `scenic route` are **the same twelve
bytes** — the comma and the space cost the same. Apple's search combines
individual keyword terms into phrases, so the two-term form still covers the
"scenic route" query, and it additionally covers "scenic drive", "scenic
byway", "route planner" and "coastal route", which the literal phrase does
not. **Same price, strictly more coverage.** If the literal string is wanted
anyway, this is the same 97 bytes:

```
scenic route,backroad,byway,countryside,road trip,loop,curvy,touring,twisty,coastal,weekend,drive
```

Every term > 2 characters. No app or company name. The app's own name is
excluded deliberately — Apple's reference says an app "is searchable by app name
and company name, so you shouldn't duplicate these values in the keyword list."
That rule names the app name and the developer name; **it does not name the
subtitle**, so carrying `scenic` and `route` in both the subtitle and the
keyword field is not a documented duplication.

Words considered and dropped: **`detour`** and **`revroutes`** — both are
names of shipping Navigation apps (*Detour - Scenic Navigation*, *RevRoutes*),
and unlike `scenic` **neither describes anything this app actually does**,
which is the whole of the distinction the table above rests on. Also dropped:
`navigation` and `gps` (the category assignment already covers them and they
are the most contested terms in the store), `joyride` (cut to make room for
`route`, which the subtitle decision made worth more), and
`vermont`/`maine`/state names (six to fourteen bytes each, for terms the
description already carries into web search).

### Promotional text — 159 / 170 characters

```
Pick a distance instead of a destination and it plans the loop. Every road in New England scored for beauty from open data. Move one slider and spend the time.
```

Promotional text can be changed without submitting a build, so it is the right
place for the loop hook, which is the feature most likely to need re-pitching
after the first week of reviews.

---

## 8. The description — 3,199 / 4,000 characters

Plain text, no HTML, US spelling, ASCII only. Every factual claim in it is
traced in §9.

```text
Every other maps app is trying to save you time. This one helps you spend it.

Pick a destination, then move one slider. Watch the trade as it happens: a few
more minutes of driving, a few more miles of road worth looking at. Slide it
back and you have the fastest route again. No account, no ads, no subscription.

EVERY ROAD, MEASURED

Over 145,000 miles of road across Connecticut, Maine, Massachusetts, New
Hampshire, Rhode Island and Vermont, scored one segment at a time: coastline,
forest and parkland, lakes and rivers, hills and valleys, curvature, farmland,
viewpoints, and the byways the map data marks as scenic. Nobody had to drive a
road and upload it first, so the empty ones count too.

It runs entirely on open data - OpenStreetMap, ESA WorldCover land cover, and
public elevation tiles. No Google or Apple road data is used anywhere in the
scoring.

The scoring is not uniform across the region, and that is worth saying out
loud. It was calibrated in Massachusetts, and its terrain measure runs out of
range in the White Mountains and the Maine highlands, where a deep ravine can
score much like a modest rise. Expect it to be sharpest in southern New
England and blunter as you go north.

ONE SLIDER, AND THE PRICE IN FRONT OF YOU

Fastest at one end, scenic at the other - those are the slider's own labels -
and the cost is printed before you commit: how many extra minutes, and how
many miles of good road you get for them. Six kinds of beauty can be dialed up
or down on their own - coast, forest and parks, lakes and rivers, hills,
farmland, town centers.

NO DESTINATION? PICK A DISTANCE

Loop mode answers a question the other navigation apps do not ask: I have
ninety minutes and nowhere to be. Give it a starting point and a distance, and
it returns a round trip that ends where it began, tells you which way it
heads, and tells you honestly how much of it doubles back on itself.

TURN BY TURN

Spoken turn-by-turn navigation, arrival time and distance remaining, automatic
rerouting when you leave the route, and a switch-to-fastest button for when
the drive has stopped being the point. Two buttons on the navigation screen
let you tell it what you thought of the road you are on.

HOW WELL DOES IT WORK

Both of its claims are measured rather than asserted.

Arrival times: 5.7% error, pooled over recorded drives, after pricing roads at
the speed each class is really driven plus the traffic signals and stop signs
facing you.

Beauty: over 79 marks recorded from the driver's seat, the score ranked a road
the driver liked above one they did not 74% of the time, against a 63% noise
floor for samples that size. Better than chance, measured on real drives, and
not magic.

Directions: audited over 120 random routes. Turns the map data forbids fell
from 18% of routes to 1%; junctions where holding the wheel takes you off
route with no instruction fell from 78% to 0%.

WHAT IT DOES NOT DO

No live traffic. No lane guidance. No offline maps. No CarPlay. Six New
England states only, and it needs a connection to plan a route.

Map data from OpenStreetMap, available under the Open Database License. Full
credits for every data source are in the app, under About.
```

**Why the third paragraph of "EVERY ROAD, MEASURED" is in a marketing
document.** [`release-plan.md`](release-plan.md) §9 records that `RELIEF_FULL`
saturates for **13.4% of chunks north of Massachusetts**, so the terrain
component has no range left in exactly the landscape a scenic-driving app's
screenshots would most want. The brief forbids claiming uniform six-state
quality. Rather than quietly omitting the region, the paragraph says it — which
also converts the project's biggest known weakness into the listing's most
credible sentence, and pre-empts the one-star review from Franconia Notch.

---

## 9. Every claim in the description, traced

| Claim | Source | Verified |
| --- | --- | --- |
| "Over 145,000 miles" | `README.md`: 236,000 km → 146,644 mi | ✅ |
| Six states, named | `README.md` build step; six Geofabrik extracts | ✅ |
| Component list | `roadmap.md` line 1; `BeautyType.all` | ✅ |
| "open data … no Google or Apple road data" | `docs/data-sources.md`; `README.md` | ✅ |
| Terrain caveat | `release-plan.md` §9; `new-england-terrain-findings.md` Finding 3 | ✅ |
| One slider, cost shown | `RoutePanel.swift`; `/api/route?…&pref=0..1` | ✅ |
| Six tunable types incl. town centers | `ios/Sources/BeautyType.swift:30-56` — and `town` ships **off by default**, which is why the description lists it last and claims nothing for it | ✅ |
| Loop mode: start + distance, no destination | `server/app.py:287` `/api/loop`; `LoopPanel.swift`, presented from `RoutePanel.swift:204` | ✅ |
| Loop reports heading and doubling-back | `LoopPanel.swift:175-196` — "heading {sector}", "{n} mi doubles back" | ✅ |
| **Spoken** guidance | `VoiceGuide(speaker: SystemSpeaker())`, `RouteModel.swift:241,266` | ✅ |
| Arrival time, distance remaining, switch-to-fastest | `roadmap.md`, iOS app entry | ✅ |
| Two feedback buttons | `roadmap.md`, "An instrument for route quality" | ✅ |
| ETA 5.7% pooled | `roadmap.md`; `measuring-travel-times.md` | ✅ |
| 74% vs 63% noise floor over 79 marks | `roadmap.md`; `measuring-scenery.md` | ✅ |
| Directions 18%→1%, 78%→0% over 120 routes | `roadmap.md`; `directions-accuracy.md` | ✅ |
| **No CarPlay** | No CarPlay file or symbol anywhere in `ios/` — checked, not assumed | ✅ |
| **No offline** | The app calls a hosted API for every route | ✅ |
| **No traffic, no lane guidance** | `roadmap.md`, both open; lane guidance is blocked upstream at 4.6–23.8% `turn:lanes` coverage | ✅ |

**Deliberately not claimed**, though tempting: "best route", "guaranteed
beautiful", any comparison against Apple Maps or Google Maps (also a MapKit
contract issue — see [`legal-and-ip-audit.md`](legal-and-ip-audit.md)), unpaved
avoidance (the API supports `avoid_unpaved`; **the iOS app does not expose it**,
verified by grep), and per-state quality parity.

**One limitation the description does not mention and arguably should not.** The
map opens on Massachusetts and biases address search there
(`ios/Sources/Region.swift`), so a Vermont trip is harder to search for than it
should be — `roadmap.md` has it open. It is a one-line fix and it will likely be
gone before submission; if it is not, the honest place for it is the release
notes, not the description.

---

## 10. Method, so it can be re-run

**App Store leg.** `curl -s 'https://itunes.apple.com/search?term=TERM&entity=software&country=us&limit=200'`, then count results whose `trackName` contains the term case-insensitively, and bucket those by `primaryGenreName`. **Count them in code.** The brief's six-versus-twenty-five gap (§5) is what reading a ranked list by eye produces.

**Register leg.** TESS was retired 2023-11-30. `tmsearch.uspto.gov`'s `?q=`
URL parameter is ignored and Return does not submit the form. Query the
Elasticsearch endpoint from inside a loaded `tmsearch.uspto.gov` browser tab —
AWS WAF blocks bare `curl`:

```js
await fetch("https://tmsearch.uspto.gov/prod-stage-v1-0-0/tmsearch", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({
    query: {bool: {must: [{query_string: {query: 'wordmark:"VICTORY LAP"',
                                          default_operator: "AND"}}]}},
    size: 40, from: 0, track_total_hits: true
  })
}).then(r => r.json());
```

Counts are `hits.totalValue`; records are `hits.hits[].source`. Useful fields:
`wordmark`, `wordmarkPseudoText`, `id` (serial), `registrationId`,
`internationalClass`, `alive`, `statusDescription`, `ownerName`,
`ownerFullText`, `goodsAndServices`, `disclaimer`.

**Always run a wildcard control before believing a zero** — `wordmark:*scenic*`
should return 417 and `wordmark:*lap*` should return 7,886. If they do not, the
query machinery has changed and every zero below is meaningless.

**Always run both legs.** §1 is the standing proof that one of them misses the
thing that matters most.

---

## 11. Where this disagrees with the companion document

[`trademark-knockout-findings.md`](trademark-knockout-findings.md) §15 screened
Victory Lap independently, before this document, and the two were run
separately. That is a replication, and it is worth what a replication is worth.

**Agreement, exactly:** every register count (`*victorylap*` 1, `"VICTORY LAP"`
30, `"VICTORY LAPS"` 0, pseudo-text 3, `~1` fuzzy 3 all dead, **0 live in
9/39/42**), both controls (417, 7,886), the App Store zero, the Chicago
recruiter as the largest user, and the Nipsey Hussle conclusion.

**Two corrections and one addition:**

1. **`victorylap.co` is not confirmed free.** §15 lists it as free; the whois
   chain here would not confirm that either way (§4). Do not rely on it.
2. **The recruiter's live site is `victorylap.io`**, not an unidentified
   domain — and it is substantial, which slightly strengthens §15's own
   "crowded field" reading.
3. **`AUTO LAP` (Garmin, reg. 2950644, IC 009) and `RUN A LAP RENTALS`
   (reg. 6808168, IC 039)** are the nearest live marks in this product's
   classes by the similar-mark cut, and neither appears in §15. Neither is a
   blocker. Both belong in an attorney's packet.

The verdict is the same in both documents, reached twice.

---

## 12. What this does not settle

- **It is not clearance.** No state registers, no phonetic or foreign
  equivalents, no commercial common-law database, no opinion from anyone whose
  liability stands behind it. See §2 on how that squares with
  [`release-plan.md`](release-plan.md) Decision 2.
- **Whether the name *works*.** Every check here tests availability. The store's
  own ranking for "victory lap" is a wall of racing apps (§4), which is exactly
  the risk `branding-brainstorm.md` §3 flags about the motorsport register. The
  counter-argument is good — a victory lap is the *slow* lap, driven for no
  reason but the driving — but it is an argument, and
  [`release-plan.md`](release-plan.md) §5.3 already prescribes the test that
  settles it: **five strangers, one question, "what does this sound like it
  does?"** It is free and it has not been run. **The chosen subtitle (§6a) does
  more of this work than any of the alternatives** — "the scenic route" tells a
  stranger what the app is for before the name can mislead them, which is a
  real argument in its favour that §6 does not make. If five people still say
  "racing," the fallbacks in the companion document are there.
- **Whether `Scenic Tours Europe AG`'s serial 79431580 registers.** It is under
  examination. If it registers, §6 gets stronger; if it is abandoned, §6's
  register argument goes away and the App Store argument stands alone.
- **The icon, the screenshots, and the privacy policy URL.** Listing work, not
  naming work — [`release-plan.md`](release-plan.md) §10.
- **Nothing in the code was renamed.** `PRODUCT_BUNDLE_IDENTIFIER`,
  `Color.scenic`, `SCENIC_*` and `ScenicApp.swift` are untouched, and the 158
  correct-English uses of the word are untouched with them.

---

**Nothing was filed, purchased, reserved or renamed in the course of this work.**
