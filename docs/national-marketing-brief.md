# Marketing for a national first launch (brief)

**Status:** decided, not written. Written 2026-10-18 in the master session. Nothing
in `docs/marketing-plan.md`, `docs/release-plan.md` or any other doc has been
touched for this. The answer is a **revision of `docs/marketing-plan.md` in
place**, with a status line naming the commit that last held the New England
plan, plus the small status notes listed under "Done". This brief is deleted in
the merge that brings that back, so nothing permanent may cite it.

## What changed, decided by the owner

1. **The New England-only app will never be public.** Decided 2026-10-18. The
   first App Store release is the national app (the contiguous 48 states and DC;
   Alaska, Hawaii and territories are out of scope and are not mentioned at all).
   A private TestFlight for invited friends, as today, is not "public". Whether a
   *public* TestFlight link (anyone with the URL, up to 10,000 testers) counts is
   not decided. List it as an owner decision.
2. **Scenery is scored on one national scale.** Decided 2026-10-18. A 7 means the
   same in Kansas as in Vermont. So the plains get almost no 7+ road (0.6% of
   eastern Colorado's km), and the mountains get plenty (29% of Colorado's
   mountain km under the scoring being built). Source:
   `docs/national-scenery-scoring-verdict.md` §7, on the `usa` branch.

Unchanged constraints (`docs/marketing-plan.md`, opening section): $0 marketing,
completely free app (no price, IAP, subscription or ads), no account, no
tracking, open source, iPhone only, one person who is also a student. The owner
is **new to marketing**. Define terms, give a verdict per section, and end on
this week's actions.

## The goal

`docs/marketing-plan.md` (907 lines, written 2026-09-29, committed 2026-10-04) is
a New England launch plan: L = Thursday 22 October 2026, or a quiet release with
the seasonal one-shots held for Memorial Day 2027 and foliage 2027 (§0 item 6,
§7, §12 item 1). Almost every section assumes New England: the audiences (§4),
the channels (state subreddits, New England Facebook groups, local press §5.3–5.5),
the seasons (§1, "foliage is the peak"), the flagship data post ("the ten
best-scoring drives in Vermont", §6.3) and the timeline (§7). The goal is to
rewrite it for one national first launch, with a timeline tied to when the US
app can be ready.

## Inputs the plan has to sit on

**When national can ship, as estimated (judgment, not measured):**
- Search and memory: path C in `docs/usa-extension-feasibility.md` §8 (on
  `usa`), a compact graph plus corridor search, "roughly 4–6 weeks of engineering
  plus validation".
- Data safety fixes: the quick ones are in progress (closure dates, gates, 4WD).
  The Forest Service, Park Service and TIGER joins are "a week each"
  (`docs/us-map-data-findings.md` §7).
- **The scenery model sets the calendar.** About 160 marks from four Western
  landscapes are needed before Western scores can be trusted
  (`national-scenery-scoring-verdict.md` §9): canyon country, the San Juans, the
  eastern plains, the Great Basin. The San Juans' passes open late May to July.
- So **national-ready (call it N) is most likely summer 2027**. Treat that as a
  hypothesis with ranges, and plan relative to N, the way the current plan plans
  relative to L.

**What's true of the market** (competitor sweep 2026-10-08; not in the repo, so
re-check before relying on it):
- **WanderWay** (launched 2026-09-16) calls its feature "Sunday Drive loops": time
  budget, CarPlay, no account, $4.99 after a trial. It is the closest concept and
  a name collision.
- **ROADS by Porsche** is free with round trips, but needs sign-up and tracks
  usage.
- **Detour – Scenic Navigation** has a national scenery heatmap and is paid.
- **DriveLoop** is free with loops and hands off to Google Maps.
- **Google Ask Maps** answers "scenic drive" conversationally in the US.
- **Not novel:** loops, the compass and the slider. **Defensible:** published,
  measured validation; open source; scenery rather than curvature, for cars; free
  with no account and built-in navigation.
- The current plan's §2 found about 60 scenic apps in the 2026 field, most with
  zero ratings. Distribution, not features, separates them.

**Engineering facts that constrain claims:**
- **The "96% liked at 7+" figure is New England only**: 52 marks, one rater, the
  author. Nothing validates it in the West until those drives happen.
- Drive recording is compiled out of App Store builds (the `RECORD_DRIVES` flag;
  see `docs/privacy-policy.md`). There is no in-app analytics, so measurement
  stays as §9 of the current plan describes.
- A rating prompt is built (2nd arrived drive of 10+ minutes, once per version).
- `jameskouvlis.com` (the API host and `privacy@`) **expires 2026-10-28** and was
  unrenewed on 2026-10-18. The plan must say what it costs to keep it through N.
  It is a release dependency, not a marketing one, but the current plan lists it
  at §0 item 7.

## Traps

1. **Don't carry the 96% claim, or any measured scenery claim, nationwide.** The
   whole validation is one rater in New England. Under the national scale, a
   plains user sees few 7+ roads. Copy that promises "beautiful roads wherever you
   are" is false in Kansas and gets the one-star reviews the plan exists to avoid.
   Say what is true nationally (free, no account, a scenery score for every road,
   open method) and keep measured claims scoped to where they were measured until
   Western marks exist. Check §3.4 ("What not to claim") against this.
2. **One person can't run 48 states of local channels.** The current plan's
   engine (location-tagged short video, state subreddits, local press) works
   because it is regional. Copying it ×48 is a plan nobody can execute. Pick where
   the marketing *focuses*: a sequence of landscapes or regions, chosen by where
   footage, drives and the score's strength coincide. The product is national from
   day one either way. Price the choice in the owner's hours per week.
3. **Seasons invert nationally.** Winter is New England's trough but the desert
   Southwest's high season. Spring and summer open the mountain passes. Foliage
   moves south through October. A national calendar has no single "peak", and the
   one-shot channels (press, Show HN, each subreddit's launch post, Apple's
   featuring nomination) are still spent only once. Tie each one-shot to a dated
   season *and* to N, not to a New England date.
4. **Don't write marketing as if N were fixed.** N rests on drives that haven't
   happened and engineering that hasn't started. Give the plan a go/no-go check at
   N−something like the current §7.3, and a fallback window if N slips past the
   launch season it targets.
5. **Section numbers are cited.** `docs/README.md`, `docs/app-store-listing.md`,
   `docs/load-test-oracle.md` and `docs/mid-drive-recovery-plan.md` cite the
   marketing plan, some by section (e.g. §5.10.2). Grep for `marketing-plan.md`
   before renumbering, and repoint or keep the anchors.
6. **Don't publish anything.** No posts, accounts, handles, waitlist or listing
   changes. A waitlist would add an email data flow the privacy policy doesn't
   cover. If you recommend one, price that and leave it as an owner decision.
7. **Keep New England work that still pays.** Footage filmed this October and
   the per-state top-10 method (§6.3) carry over. "The ten best drives in
   Vermont" becomes a series across states. Don't throw away what transfers.

## Done looks like

1. `docs/marketing-plan.md` revised in place for a national first launch:
   - a status line naming the commit that last held the New England plan;
   - one-page summary, audiences, positioning and claims (trap 1), channel
     playbooks with a regional focus sequence (trap 2), a national seasonal
     calendar (trap 3), and a timeline relative to N with milestones, a go/no-go
     check and a fallback (trap 4);
   - a pre-launch phase: what to build and film between now and N;
   - risks, costs, a refreshed owner-decisions list (the public TestFlight
     question among them), and this week's actions.
2. Every section citation in the four docs in trap 5 still resolves.
3. One-paragraph status notes at the top of `docs/release-plan.md`,
   `docs/app-store-submission.md` and `docs/app-store-listing.md`: the New
   England build will not be submitted (2026-10-18), and the national app is the
   first release. Don't rewrite those documents beyond that note. Their national
   versions are later work.
4. Facts re-checked on the web are dated and listed, as the current §14 does.
   Anything not re-checked is marked *(re-check)*.
