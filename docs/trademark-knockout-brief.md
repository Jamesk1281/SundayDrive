# Knockout search the name candidates — before the attorney, not instead of them

**Status: scoped 2026-09-19 against `main` at `2d6fbc0`, nothing changed.** No
file was edited, no application filed, no domain bought — and this task must not
do any of those either.

**Read this first, because the scope boundary is the whole point.**
`docs/release-plan.md` §5.2 calls for **commissioning a professional trademark
clearance search** — an engagement with a trademark attorney or search firm, on
an external clock measured in days-to-weeks, and one of only two unpriced items
in the entire release plan (§11).

**This task is not that, and must not be presented as that.** It is the
**knockout search** that goes *before* it: a preliminary screen of the public
registers that kills obviously-blocked candidates cheaply, so the paid engagement
starts on a shortlist that has already survived the free checks. A knockout
search finds blockers. It cannot establish that a name is clear. See Trap 1 —
that distinction is the single most important thing in this document.

**Nobody here is a lawyer and the output is not legal advice.**

---

## The goal, as measured

`docs/branding-brainstorm.md` §1 establishes why the working title cannot stay,
and it is not a close call: **"Scenic — Motorcycle Navigation" (`scenic.app`) is
an established scenic-route navigation app** — ~30M hours ridden, 200k+ user
routes, 4.7★, paid tier, years of priority. Identical mark, identical goods.
Separately, "scenic" for an app that finds scenic routes is **merely descriptive**
under Lanham §2(e)(1), so it is the weakest registrable class even unopposed.

§3 of that document then did the one check that turns a wordlist into a
shortlist — querying the US App Store search API for every candidate and counting
apps whose *name* contains the word:

| Candidate | Apps with the name | In Nav/Travel | Verdict |
| --- | ---: | --- | --- |
| **Longcut** | 0 | 0 | Clean — **recommended**, tagline *"Take the long way."* |
| **Aimless** | 0 | 0 | Clean — the bold alternative |
| **Detourist** | 0 | 0 | Clean (coined) |
| Camber | 5 | 0 | Usable — the understated alternative |

That check has real force — **it demoted the document's own first
recommendation**, Amble, on discovering *Amble: Walk Route Planner* already
exists. A method that overturns its author's preference is working.

**But an App Store name search is not a trademark search.** It sees app titles
in one storefront. It does not see the USPTO register, pending applications,
state registrations, or unregistered common-law users — any of which can block a
mark, and the last of which never appears in any register at all. **That gap is
this task.**

## What is already known and must not be re-derived

- **The candidate list and its reasoning** — `branding-brainstorm.md` §3, above.
- **The App Store counts** — done, sourced, and correct. Do not redo them.
- **The names to avoid regardless of availability** — §3's final block rules out
  anything built on *Scenic / Route / Drive / Map / Road* (same descriptiveness
  trap), plus **Verge** (major media mark), **Backroads** (large tour operator),
  **Detour** (heavily used, incl. a well-known location-audio app), **The Long
  Way** (Ewan McGregor's travel/media brand — *use it as the tagline, not the
  name*), and the motorsport register (Apex, Chicane, Hairpin, Esses).
- **One known risk on the front-runner**, already recorded: **"Skoal Long Cut"**
  is chewing tobacco. `branding-brainstorm.md` reasons that the class differs
  (34 vs 9) so conflict risk is low, but flags the *association* as a real
  branding question. **Verify the class-34 reasoning rather than inheriting it**
  — that is exactly the kind of inference this project has found wrong before.
- **Domains, partially checked and explicitly unverified**: `longcut.com` is
  registered; `longcut.co` and `takethelongcut.com` appeared free; **`longcut.app`
  returned no A record with inconclusive whois and the RDAP query failed to
  connect — the document marks it unverified and it still is.**

---

## Traps

**1. A knockout search is not a clearance search, and the difference is the
whole deliverable.** A knockout screen looks for obvious blockers in the public
registers; a clearance search is a professional product covering common-law use,
state registers, phonetic and foreign-equivalent variants, with an attorney's
written opinion you can actually rely on. **Never write "clear to use" or
"available".** The honest verdicts are *"no knockout blocker found — proceed to
professional clearance"* and *"blocked, drop it"*. Presenting a free screen as
clearance is the one outcome here that could cost real money, because it is the
one that would let someone skip §5.2 and put a brand behind an unsearched name.

**2. Searching for identical marks is the wrong search and will return a false
all-clear.** The test is **likelihood of confusion**, which reaches similar marks
for related goods — not identical marks for identical goods. "Longcut" has to be
screened against `LONG CUT`, `LONGKUT`, `LONG-CUT`, `LONGCUTT` and similar, and
against marks in adjacent classes, not just an exact string in class 9. A report
saying "no exact match, therefore clear" has done nothing and would be worse than
no report, because it reads like reassurance.

**3. Run "Scenic" through the same method as a positive control, and report the
result.** The answer is known in advance — there is a senior, established,
directly-competing navigation app under that exact name. **If your method does
not surface it, your method is broken and every other result in the report is
worthless.** Do this first and say plainly whether it passed. This project's
habit is to print the noise floor next to the measurement; this is that.

**4. "Dead" does not mean free.** An abandoned application or cancelled
registration removes a *federal registration*, not the underlying rights — a
senior common-law user who never registered can still block, and never appears in
the register. Report status codes honestly and do not treat DEAD as a green
light.

**5. Do not file, buy, or reserve anything.** No USPTO application, no domain
purchase, no App Store name reservation. The name is **Decision 2** in
`release-plan.md` §8 and belongs to the owner; it is positioned *after* clearance
returns and *before* the App Store Connect record, for the specific reason that
the bundle identifier becomes permanent at first submission.

**6. Verify the search tool before trusting it.** The USPTO retired TESS and
replaced it; confirm what the current public search system is and say which one
you used, with the date. A report citing a retired system is a report nobody can
reproduce.

**7. The repository is public.** This document and your findings are readable by
anyone, including parties with an interest in these marks. State facts and
sources; do not speculate in writing about anyone's enforcement posture.

---

## Done looks like

1. **One new document**, `docs/trademark-knockout-findings.md` — deliberately not
   this brief's filename — added to `docs/README.md`'s index.
2. **The positive control reported first** (Trap 3): what the method returns for
   "Scenic", and whether that matches the known senior competitor.
3. **Each of the four candidates screened** — Longcut, Aimless, Detourist,
   Camber — against the live federal register in the relevant classes, including
   similar marks and not only identical ones. For each hit: the mark, owner,
   serial/registration number, class, goods description, and status, with the
   search system and date named so it can be re-run.
4. **Common-law signals per candidate**, separate from and clearly labelled
   against the register results: existing companies, products, and the domain
   position — including a definitive answer on `longcut.app`, which
   `branding-brainstorm.md` could not resolve.
5. **A verdict per candidate in the permitted vocabulary** — *no knockout blocker
   found, proceed to professional clearance* / *blocked, drop it* / *cannot be
   determined from public sources*. **Never "clear" or "available".**
6. **A price range for the professional engagement**, with what to ask for — this
   is one of exactly two unpriced items in `release-plan.md` (§11), it is called
   "plausibly the larger half" of the release's cost, and it is obtainable from
   public rate information. If it cannot be pinned down, say so and say what a
   quote request should specify.
7. **An honest-answer escape hatch.** "All four survive the knockout screen and
   the real question is the attorney's" is a complete answer — say it in a line
   rather than padding it. So is "this could not be determined from public
   sources" for any individual candidate, and it is much better than a guess.
