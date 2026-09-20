# "Victory Lap" — pressure-test the name, then build the listing

**Status: scoped 2026-09-19, nothing changed.** No file renamed, no identifier
touched, nothing filed or bought. This is naming and copy work — **not** the
rename implementation, which is a separate job with its own traps
(`docs/release-plan.md` §6b). See Trap 5.

**The owner has chosen "Victory Lap."** That decision is not being reopened. What
this task does is (a) put it through the checks the previous candidates got,
(b) settle the App Store title and subtitle, and (c) write the description.

**Nobody here is a lawyer and none of this is legal advice.**

---

## What is already measured

### "Victory Lap" passes the cheap check that killed the last front-runner

Queried against the US App Store search API on 2026-09-19 — the same method
`docs/branding-brainstorm.md` §3 used, and the one that demoted its own first
recommendation when *Amble: Walk Route Planner* surfaced:

```
itunes.apple.com/search?term=Victory%20Lap&entity=software&country=us&limit=200
  →  144 results, 0 with "victory lap" in the app NAME
```

**Zero collisions**, matching the cleanest previous results (Longcut, Aimless,
Detourist all returned 0). The bare word "Victory" returns 108 name-matches, but
none in Navigation or Travel — they are Lifestyle, Sports, Games, Education.

### The proposed subtitle is the problem, and it is measurable

The owner's suggestion is **"Victory Lap - The Scenic Route"**. Same query, for
the word it contains:

```
itunes.apple.com/search?term=Scenic&entity=software&country=us&limit=200
  →  157 results, 43 with "scenic" in the app NAME — SIX in Navigation/Travel
```

| App | Category |
| --- | --- |
| **Scenic Motorcycle Navigation** | **Navigation** — the senior competitor |
| Scenic Way | Navigation |
| Detour - Scenic Navigation | Navigation |
| RevRoutes Find Scenic Drives | Navigation |
| Scenra: Scenic Road Trips | Travel |
| Sedona GPS: Scenic Audio Guide | Travel |

**Why this matters more than it looks.** The entire reason for the rename is that
`docs/branding-brainstorm.md` §1 found the working title occupied by a *senior,
established, directly-competing* scenic-route navigation app whose whole mark is
that word. **Putting "Scenic" back into the App Store title, in the Navigation
category, hands back the distance the rename is being done to buy** — and an App
Store title is use in commerce, not a description.

*Flagged as a hypothesis, because it turns on a distinction a professional should
confirm:* "the scenic route" used descriptively in a subtitle is different in
kind from "Scenic" used as a mark, and descriptive fair use is a real defence.
**What would settle it:** whether the senior user's mark is registered, in which
class, and how the phrase reads next to six existing Nav/Travel apps using the
same word. That is a question for the clearance engagement, not for a subtitle
draft. **What is not in doubt is that it is the riskiest available subtitle**,
and that alternatives exist which cost nothing.

`branding-brainstorm.md` §3 already rules out, on exactly this reasoning,
"anything with **Scenic, Route, Drive, Map, Road** as the whole mark."

### The positioning question, stated fairly

That document's §3 also warns against the motorsport register — "**Apex,
Chicane, Hairpin, Esses** — pulls toward fast and track, the opposite of the
product's soul." "Victory Lap" sits in that register on its face.

**But the obvious objection does not survive a second's thought, and the brief
records that rather than hiding it.** A victory lap is the *slow* lap. It happens
after the race is over, at no speed, for no reason but enjoyment — which is
exactly this product: the drive you take when arriving fast has stopped being the
point. It is arguably a better fit than the document's own recommendation, and it
carries a warmth ("you've earned this") that "Longcut" does not.

The real questions are whether it reads as *sports* rather than *driving* to
someone who has not been told, and whether "lap" implies returning to where you
started — which is true of the loop mode and false of point-to-point routing.
**Both are answerable with the five-person test `branding-brainstorm.md` §7
already prescribes**, and that test is free.

### One known association to check rather than assume

**Nipsey Hussle's *Victory Lap*** is a Grammy-nominated 2018 album, which means
there is plausibly a live mark in recorded-music goods. Different class from
navigation software, most likely — but `branding-brainstorm.md` made exactly this
kind of class-based inference about "Skoal Long Cut" and this project's record is
that briefs are right on measurements and wrong on inferences. **Check it, do not
reason from it.**

---

## Traps

**1. Do not put "Scenic" in the App Store title or subtitle without confronting
the measurement above.** Six Navigation/Travel apps already carry the word, one
of them the senior competitor the rename exists to escape. If the recommendation
is still to use it, that recommendation has to argue against this evidence
explicitly rather than around it. **Offer at least two subtitles that do not use
the word**, so the owner is choosing rather than defaulting.

**2. A knockout search is not a clearance search.** Same boundary as
`docs/trademark-knockout-brief.md`: screen the public register for obvious
blockers, never write "clear" or "available", and use the permitted verdicts —
*no knockout blocker found, proceed to professional clearance* / *blocked* /
*cannot be determined from public sources*. `release-plan.md` §5.2 still calls
for a professional engagement and this does not replace it.

**3. A parallel session is already knockout-searching different names.**
`docs/trademark-knockout-brief.md` was dispatched before this decision and is
screening **Longcut, Aimless, Detourist, Camber** into
`docs/trademark-knockout-findings.md`. **Do not write that file and do not
re-screen those four** — they are fallbacks now, and its results still matter if
"Victory Lap" hits a blocker. Use your own filename (below) and say in your
document that the two are companion pieces.

**4. "Victory Lap" is a common English phrase, so the register will be noisy.**
Expect many live marks across unrelated classes — sports, media, food, apparel.
The screen is worth nothing unless it filters to the classes that matter for
downloadable navigation software and adjacent services, and unless it covers
similar marks rather than the exact string. "Many hits, all irrelevant" is a
conclusion that has to be shown, not asserted.

**5. Do not rename anything in the code.** No `PRODUCT_BUNDLE_IDENTIFIER`, no
`Color.scenic`, no `SCENIC_*`, no `ScenicApp.swift`. That work is
`release-plan.md` §6b, it is gated on clearance returning, and it carries its own
severe trap: of 3,046 case-insensitive occurrences of "scenic" in the repo,
**1,967 are census CSV data and 158 are correct English** ("scenic route",
"scenic km") that must survive. `RoutePanel.swift:298` and `:472` are identical
string literals with opposite treatment. **Write copy; change no identifiers.**

**6. Verify the App Store Connect field limits rather than assuming them.** The
name and subtitle fields are short and the proposed string is close to the
ceiling — "Victory Lap - The Scenic Route" is **exactly 30 characters**, which is
either at or over the limit depending on the field. Confirm the current limits
for name, subtitle, promotional text, keywords and description, cite where, and
design within them. A title that cannot be entered is not a recommendation.

**7. The repo is public.** A document naming a chosen brand, before any
application is filed, is readable by anyone. State facts and sources; do not
speculate in writing about third parties' enforcement posture.

---

## Done looks like

1. **One new document**, `docs/victory-lap-naming.md` — not this brief's
   filename — added to `docs/README.md`'s index.
2. **A knockout screen on VICTORY LAP** in the classes that matter, covering
   similar marks and not just the exact string, with mark / owner / serial /
   class / goods / status for each relevant hit, and the search system and date
   named so it can be re-run. Include the Nipsey Hussle check explicitly.
3. **The positive control, as in the companion brief**: run "Scenic" through the
   same method and confirm it surfaces the known senior competitor. If it does
   not, the method is broken and the rest of the document is worthless.
4. **A recommended App Store name and subtitle**, within the verified character
   limits, **with at least two subtitle options that avoid the word "Scenic"**
   and an explicit argument for whichever is recommended — engaging the six-app
   measurement above rather than stepping around it.
5. **A full App Store description**, plus promotional text and a keywords-field
   suggestion. It should say what is true and provable about this app: routes
   scored from open geodata only, a preference dial that trades minutes for
   beauty, turn-by-turn navigation, and a loop mode. **Do not claim uniform
   six-state scenery quality** — `release-plan.md` §9 records that `RELIEF_FULL`
   saturates for 13.4% of chunks north of Massachusetts, so the model is weakest
   in exactly the terrain the screenshots would most want.
6. **An honest-answer escape hatch.** "Victory Lap survives the knockout screen"
   is a complete answer in one line. So is "the subtitle should not contain
   Scenic, and here is what it should contain instead" — and if the evidence
   genuinely supports keeping it, say that with the argument. "This cannot be
   determined from public sources" remains better than a guess on any individual
   point.
