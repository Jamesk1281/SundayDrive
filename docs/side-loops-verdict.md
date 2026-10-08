# Side loops: should a scenic route take the side street that rejoins further on?

**Status: measured 2026-10-06, nothing changed.** No routing, server or app code
was touched. The harness is `pipeline/side_loop_experiment.py`; its tree
arithmetic is checked by `tests/test_side_loop_experiment.py`. All numbers are
from the New England build (`data/processed-ne`) on the drives' date, so this
year's seasonal closures and the closed-to-cars mask are applied.

## The answer

**Can't tell from the data we have, for the kind of loop the question is
about. Shipping it would also depend on fixing state road classes first.**

1. **The router can't pick a side loop today, and the census confirms it
   empirically.** All 2,957 side loops found along 43 real routes cost more than
   the route segment they would replace, under the router's own cost. The
   median margin is 2.3 cost-minutes (§2). That's the length tax described in
   `docs/scenery-cap-options.md`, Part 1, playing out loop by loop.
2. **On today's score the answer is mostly no.** There are about 75 minor-road
   loops per 100 km. Taking all of them buys 0.10 km of road scoring 7 or more
   (call it km≥7) per extra minute, about an eighth of the 0.77 km≥7/min the
   pref slider already buys. Only **2.4 per 100 km** clearly beat the slider, and
   those are lake and pond roads that the score already rates well. Washburn Road
   isn't one of them: it gains 0 km≥7 for +2.9 min.
3. **The user's kind of loop (woods, farms, a quiet lane) can't count as
   scenic under the score's 7 bar, by construction.** 95% of New England's
   km≥7 has water or coast nearby. Roads with neither and no byway tag reach 7
   on 0.8% of their km. So "should we take Washburn Road?" really asks whether
   the score undervalues roads like it.
4. **The marks say minor roads are probably under-scored, but they can't say
   which minor roads.** At equal score, a minor road is more likely to be
   called nice. The estimated offset is +2.1 score points, but resampled by road
   the interval is [+0.15, +27]: positive, size unknown. Within minor roads
   there are 31 nice marks and **4 dull marks, on 2 roads**. So whether the score
   tells a good minor road from a bad one is unmeasured, and that is the one
   thing a side-loop rule needs.
5. **Side roads are where the map is worst.** Minor-road loop km is **40% on
   `tiger:reviewed=no` ways**, against 12% of the routes they leave. On the
   drives' own routes it's 23% against 2.4%. A rule that rewards these loops
   would multiply the 2026-10-06 blockaded-road outcome. Anything that ships has to
   wait for the separate state road-class fix.

If the settling drive in §5 comes back yes, the cheapest mechanism isn't a
side-loop feature. It's the road-size term that `docs/driver-preferences-study.md`
§6 (A′) already designed: one extra non-negative term in `_weights`, so Dijkstra
stays valid with no extra search. Side loops then fall out of the ordinary route
wherever a small road beats a big one (§4).

---

## 1. Washburn Road, worked end to end

Washburn Road, Barre MA, is three graph edges (183219, 183216, 183217) with a
total length of 3.25 km. Its scores:

| edge | length | score, neutral weights | score, app weights (`town=0`) |
|---|---|---|---|
| 183219 | 535 m | 4.71 | 5.22 |
| 183216 | 1,656 m | 4.20 | 4.55 |
| 183217 | 1,055 m | 4.87 | 5.05 |
| **length-weighted** | 3.25 km | **4.50** | **4.82** |

The app sends `w_town=0` unless the driver changes it, and all six 2026-10-06
drives did. So the routing numbers below use the app weights. The brief's
4.2–4.9 are the neutral column.

**It doesn't rejoin West Street.** The west end (OSM node 69504916) is on West
Street, a primary. The east end (69466804) is on **Pleasant Street**, a
tertiary, and the middle junction meets Allen Hill Road. Between its own two
ends, Washburn Road is a **shortcut**: 3.25 km and 5.13 min, against 4.82 km
and 4.74 min by West Street and Pleasant Street. It's also already cheaper under
the router's cost at every pref (8.5 against 10.3 at pref 0.5). Any trip from
West Street to Pleasant Street already uses it.

**As a side loop off the actual route.** Drive 122558 (pref 0.773) re-planned on
today's graph passes the west junction. The census finds Washburn Road plus
Pleasant Street rejoining that route further on:

| | km | minutes | km≥7 | router cost |
|---|---|---|---|---|
| route segment, West Street onward | 3.90 | 3.50 | 0.00 | 13.86 |
| loop via Washburn Rd + Pleasant St | 4.17 | 6.37 | 0.00 | 17.26 |
| **difference** | +0.27 | **+2.87** | **0.00** | +3.40 |

The loop costs 2.9 minutes and buys nothing on the score's own terms.

- **What score would make the router take it?** The cost gap is 3.40, and at
  pref 0.773 each unscenic km costs `k = 0.773² × 8 = 4.78`. Closing the gap on
  Washburn Road's 3.25 km needs +2.19 points. Washburn Road would have to score
  **7.0 instead of 4.8**. That's possible on a 0–10 scale, but it would put the
  road in the network's top 10%.
- **Would the minor-road offset the marks suggest be enough?** At +2 points,
  two of its three edges cross 7, giving 1.59 km≥7 for 2.87 min = 0.55 km≥7/min.
  The slider buys 0.93 on this same trip (fastest to pref 0.773). So the loop
  still loses to the slider.
- **Map quality.** Every edge of the loop is on a reviewed way (not
  `tiger:reviewed=no`). None has a surface tag.

**The verdict on the example:** under today's score the intuition is wrong.
Under any minor-road offset the marks can support, it's closer, but still
loses on this trip. What would make it right is the score being wrong about
this particular road, and nothing on hand can say whether it is.

---

## 2. Census of side loops

### Definition

A side loop is the router-cost-cheapest path from route node A to a later route
node B (B strictly after A along the route) whose interior touches no route node
and no route edge. Four properties follow from that:

- it is edge-disjoint from the route;
- it is a simple path, because it's a shortest path, so nothing is driven twice
  and retracing is 0 km by construction;
- it can't rejoin behind where it left;
- a dead-end spur can't appear, because it would have to come back through its
  own entry.

Loops are found inside a 5 km corridor of the route. The limits are:

- loop length ≤ 20 km;
- extra time from 0 to 20 min;
- route span ≥ 0.3 km, so junction triangles are excluded.

Dedupe works in two steps. First, keep one loop per offshoot (the cheapest
rejoin from each first off-route edge). Then drop any loop that shares more than
half its km with a loop already kept. That turns 80,863 raw (A, B) candidates
(about 2,700 per 100 km) into 2,957 loops. **Minor-road loop** means at least
half the loop's km is below `secondary`.

The search runs in real-junction space, so a loop's own entry or exit turn may
occasionally be one the router forbids. The route itself is the router's own,
restrictions included.

### Sample

43 routes, 2,971 km:

- the three distinct scenic trips from 2026-10-06, re-planned at their own
  pref and weights: 104931 at 0.50, 122558 at 0.77, and 185940 at 0.51.
  192759 re-plans 185940's trip, so it's dropped as a duplicate.
- 40 pairs from `tools/e2e_od_pairs.json` (the first 10 each of `rural`,
  `suburban`, `coastal` and `cross`) at pref 0.5 with the app's weights.

### Scenery measure, and the bar a loop must clear

**km≥7** is km on edges scoring 7 or more, the top **10.0%** of New England
road-km. It's the bar `docs/scenery-cap-options.md` uses, and the brief asks
for it. A threshold metric flickers, though: a 6.9 → 7.1 swap counts as a full
km gained. So every table also carries **clear gain**, which is loop km at ≥ 7.5
minus segment km at ≥ 6.5. A loop only shows a clear gain if it survives half a
point of score noise either way.

**The bar is what the slider already pays.** For each route, the slider's
exchange rate is (km≥7 at the chosen pref − km≥7 on the fastest route) ÷ (extra
minutes). The median is **0.77 km≥7/min** (p25 0.40, p75 1.81). Going from the
chosen pref up to 1 pays a median of only 0.58. A loop worth adding has to buy
more scenery per minute than the slider does on the same trip. Otherwise the
driver gets more by moving the slider, which they already have.

### Results

| | all loops | minor-road loops | other loops |
|---|---|---|---|
| per 100 km of route | **99.5** | **74.5** | 25.0 |
| extra minutes, p25 / median / p75 | 0.6 / 1.3 / 3.5 | 0.6 / 1.4 / 3.8 | 0.4 / 1.1 / 2.8 |
| loop length, median | 2.0 km | 1.7 km | 3.6 km |
| any km≥7 gain | 37% | 40% | 30% |
| clear gain | 23% | 25% | 17% |
| **beat their route's slider rate, km≥7** | 8.3 / 100 km | 5.9 / 100 km | 2.5 / 100 km |
| **beat it, clear gain** | **3.4 / 100 km** | **2.4 / 100 km** | 1.0 / 100 km |
| take every loop: km≥7 per extra minute | 0.06 | **0.10** | −0.07 |

Minor-road loops by extra time, totals over the 2,971 km:

| extra | per 100 km | km≥7 gained | clear gain | beat slider (km≥7 / clear) |
|---|---|---|---|---|
| 0–2 min | 44.6 | +30.9 | −162.3 | 101 / 31 |
| 2–5 min | 15.9 | +132.3 | −96.3 | 52 / 30 |
| 5–10 min | 10.0 | +225.8 | −29.0 | 17 / 10 |
| 10–20 min | 4.0 | +220.3 | +61.4 | 4 / 0 |

How to read it:

- **Loops are everywhere**, about one minor-road loop per 1.3 km of route, and
  most cost under two minutes. The density runs from 53 per 100 km (suburban)
  to 106 (coastal).
- **Taken wholesale, they're a bad trade.** 0.10 km≥7/min is an eighth of the
  slider's rate. By clear gain the net is negative, because more loops step
  down off a good road than step up from a bad one.
- **Taken selectively, a few win.** 71 minor-road loops (2.4 per 100 km) clearly
  beat their own route's slider rate, at a median of +2.1 min. The biggest are
  all water roads: Lily Road and Lakeview Avenue, Slough Pond and Black Pond
  Roads on Cape Cod, River Road. That matches point 3 of the answer above. The
  loops the score endorses are loops to a lake.

### Map quality on the loops (trap 1)

TIGER review status comes from a tag scan of `new-england-latest.osm.pbf`
(579,413 drivable ways, 36% `tiger:reviewed=no`, 57% with no `surface`). Each
graph edge is matched to its way at the edge's midpoint.

| share of km that is… | on the routes | all loops | minor-road loops | the 71 winners |
|---|---|---|---|---|
| `tiger:reviewed=no` | 11.7% | 32% | **40%** | 30% |
| untagged surface | 16.8% | 30% | 33% | 31% |
| both (the blockaded-road profile) | 3.5% | 9% | 11% | — |

On the drives' own routes the contrast is sharper: 2.4% unreviewed TIGER on the
route, against 23% on its minor-road loops. 38% of minor-road loops are *mostly*
(over 50%) unreviewed TIGER, and 12% are mostly both unreviewed and untagged.
In rural, suburban and cross-state trips, the minor-road loop km is 47–56%
unreviewed. This is the population that put the driver behind a blockade and
into a private driveway on a New Hampshire road that state data lists as
private and Class VI.

---

## 3. Does the score undervalue minor roads?

All 151 usable marks are used: 79 from August (mostly 2026-08-25) and 72 from
2026-10-06. Each is scored the way `tools/analyze_trace.py` scores it (a 400 m
window ending 3 s of driving before the tap). There's **one driver, on three
days**, and 113 nice against 38 dull.

"Separation" is the rank statistic analyze_trace.py reports: the probability
that a nice stretch outscores a dull one. The chance bar is the level a score
that knows nothing reaches one time in twenty, at that sample size. Intervals
are bootstrap 95%, resampling marks within verdict.

| neutral weights | nice / dull | separation | chance bar |
|---|---|---|---|
| pooled | 113 / 38 | 0.72 [0.63, 0.80] | 0.59 |
| major roads (secondary and up) | 82 / 34 | 0.75 [0.65, 0.83] | 0.60 |
| major, excluding motorways | 71 / 29 | 0.83 [0.74, 0.91] | 0.61 |
| **minor roads** | **31 / 4** | **0.48 [0.28, 0.67]** | **0.76** |
| 2026-10-06 alone | 53 / 19 | 0.77 [0.65, 0.87] | 0.63 |

Under app weights the minor-road separation is 0.64 [0.45, 0.81], against the
same 0.76 bar. The 2026-10-06 row reproduces the brief's 0.77, which is a
check that these marks are attributed exactly as analyze_trace.py does it.

**What would have killed the hypothesis** (from the brief): minor-road marks
separating as well as major ones, and nice minor marks not scoring lower than
nice major ones. The second condition fails:

- **Nice marks on minor roads score lower** than nice marks on major roads:
  **−1.04 points [−1.65, −0.37]**, excluding motorways.
- **Dull marks on minor roads score higher**: +1.15 [+0.07, +2.09].
- **At equal score, minor roads are called nice more often.** In the 4–5 score
  band, 10 of 11 minor-road marks are nice, against 5 of 13 on major roads.
- **A logistic fit**, nice ~ score + minor, says being a minor road is worth
  **+2.09 score points** (motorways excluded). The interval is [+0.51, +4.56]
  resampling marks, but **[+0.15, +26.6] resampling roads**: 77 distinct roads,
  since several marks on one road on one day are not independent verdicts. The
  sign is real and the size is unidentified. With app weights it's +2.44
  [+0.23, +35.9].

The first condition can't be tested. **The 4 dull minor-road marks are on two
roads**, two marks each. A separation off
31/4 has a chance bar of 0.76, so whether the score ranks minor roads against
each other is simply unmeasured.

This **replicates** `docs/driver-preferences-study.md` §1–3 on twice the marks.
That study found the scenery model blind to road size (raw beauty flat to 0.19
points across classes) while the driver's verdicts track it. It's the same
finding, from the marks rather than the network.

**Three reasons not to turn the offset into a correction:**

1. **Selection.** Every mark is on a road the router chose, and the driver taps
   *nice* three times as readily as *dull*. A dull minor road may simply go
   unmarked. A forced-choice protocol (§5) removes that.
2. **One of the nice-but-low minor marks is the blockaded road (4.5)**, the road that
   turned out private and Class VI. That's the hypothesis and trap 1 in a
   single mark.
3. **19 dull marks per day, 4 of them on minor roads.** Fitting a per-class
   correction to that and calling it calibrated is what the brief's trap 5
   warns against.

---

## 4. Verdict and mechanism

**Can't tell.** Here's the reasoning:

- On today's score, side loops are a measured no as a class. They're a narrow
  yes for about 2.4 per 100 km, and those are lake roads.
- The user's loops (Washburn Road and the like) can't count as scenic under the
  7 bar. They only win if minor roads are worth about +2 points or more.
- The marks say the offset is positive but can't size it. More importantly,
  they can't say the score *ranks* minor roads, and any loop rule needs that
  ranking to pick the good loop over the blockaded one.

**If the drive in §5 comes back yes, the order is:**

1. **Fix road class first** (the separate NHDOT and state road-class work).
   Shipping anything that leans toward minor roads before that would aim 40% of
   its gains at unreviewed TIGER ways.
2. **Then the road-size term A′** from `docs/driver-preferences-study.md` §6:
   `+ k_road · BETA_ROAD · km · (1 − rank)`. It charges big-road km and not
   small-road km. Every weight stays non-negative, so it's still one Dijkstra
   with no added latency and no validity wall. A Washburn-type loop then wins
   wherever its small-road km saves more road-tax than its extra minutes cost.
   No loop search exists at request time; loops simply appear in the route. That
   study measured A′ losing to the slider on km≥7 and recommended default
   **off**, as a preference. This study agrees, and reaches it from the other
   end.
3. **Not a loop splicer.** A post-pass that scans candidate loops and splices
   in those beating the slider rate would work. As built here, though, the
   search takes tens of seconds per route in Python, and it would need the
   corridor search compiled. These timings were taken while other sessions were
   running, so they show the order of magnitude only, not latency.
4. **Not BETA or PREF_CURVE.** Raising either taxes the extra km harder
   (`docs/scenery-cap-options.md`, Part 1), and 0 of 2,957 loops win at today's
   values.
5. **Not the detour budget** (option 5 there) for this question. It inserts
   one via-node for the whole trip, so it buys a long scenic excursion rather
   than local side streets. It's the right tool for "I have two hours", not for
   "take Washburn Road".

**The rule, if it's yes:** take a loop when the clear gain per extra minute is
at least that trip's slider exchange rate (median 0.77 km≥7/min). Restrict it to
loops whose km is mostly reviewed, or tagged with a surface, until the road-class
fix lands.

---

## 5. The drive that would settle it

What's missing is dull marks on minor roads, from roads the score rates both
low and high. Requirements:

- **Marks needed:** at least **15 nice and 15 dull on minor roads, from at
  least 15 distinct roads.** At 15/15 the chance bar is 0.68, so a real
  separation of about 0.80 would show. At today's 31/4 nothing can.
- **Protocol: forced choice.** Mark *every* minor road on the drive once, nice
  or dull, a few hundred metres in. Don't mark only the ones that stand out.
  That removes the 3:1 nice bias that §3's first reason depends on.
- **Where:** around Barre, MA, starting from Washburn Road. `side_loop_experiment.py
  plan` lists 205 named minor roads within 15 km that are at least 1 km long
  and mostly on reviewed ways (the score's median is 5.2). Drive a mix from both
  ends:
  - **The score says dull (≤ 4.5):** Oakham Road 4.4, North Road 4.2, Old
    Petersham Road 4.4, Sheldon Road 3.9, Old Stage Road 3.9, Hale Road 3.7,
    Root Road 3.8, Scott Road 3.3, Walnut Hill Road 4.2, Ridge Road 3.9.
  - **The score says good (≥ 6.0):** Coldbrook Road 6.6, Patrill Hollow Road
    6.1, Pine Plain Road 6.8, Glen Valley Road 8.7, Brigham Road 7.0, Charnock
    Hill Road 6.5, Intervale Road 7.2, Prison Camp Road 6.8, Carter Pond Road
    6.5, Brooks Village Road 6.4.
  - **Washburn Road itself (4.8)**, both directions.

  `plan` groups by name within the radius, so a common name (Pleasant Street,
  Main Street) can merge two roads; check before driving. All of these are
  reviewed TIGER, but many have no surface tag, so expect gravel.
- **What settles it:**
  - **No:** the dull-scored roads are called dull about as often as the
    good-scored ones are called nice (minor-road separation ≥ 0.70, above its
    bar). The score ranks minor roads, it's merely shifted, and §4's A′ is the
    honest fix as a preference.
  - **Yes, the score is blind there:** both groups come back mostly nice. Minor
    roads are liked regardless of score, which is a road-size preference and
    again A′. A loop rule keyed on score would pick at random among them.
  - **Can't tell, still:** fewer than about 10 dull marks come back. Then the
    driver doesn't dislike minor roads, and the question becomes product rather
    than measurement.

Pool with the existing 151 marks using `tools/analyze_trace.py`, then rerun
`side_loop_experiment.py marks`.

---

## 6. What this does not measure

- **Turn restrictions inside loops.** The loop search folds turn-restriction and
  barrier copies back onto their junction, so a few loop entry or exit turns
  may be illegal. The routes themselves aren't affected.
- **Edge-to-way matching.** It's by midpoint, preferring the same name, so a
  short edge at a junction can take its neighbour's tags. That affects the
  shares by a little, not their 3–10× gap from the route baseline.
- **Interaction between loops.** Each loop is scored independently against the
  route. Taking two overlapping loops isn't additive, and the per-100-km counts
  depend on the dedupe rule (raw candidates are 27× more numerous).
- **The e2e sample** is one pref (0.5) and the first 10 pairs per category, not
  a random draw. The three drive trips are the real case.
- **Latency.** Not measured; other sessions were running.
- **Graph vintage.** The NE graph predates the `unpaved_frac` column, so the
  router recovers it from `score_adj` (`Router._load_unpaved`). All scores here
  are the router's in-memory ones, which differ from the stored `score` column
  only on unpaved edges.

## Reproducing this

The data, PBF and traces live only in the main checkout.

```bash
.venv/bin/python pipeline/side_loop_experiment.py data/processed-ne washburn marks census plan \
    --traces traces --pbf data/raw/new-england-latest.osm.pbf --cache <scratch> --pairs 10
.venv/bin/python pipeline/side_loop_experiment.py - summary --cache <scratch>
```

`census` writes `side_loops.csv` and `side_loop_routes.csv` into `--cache`;
`summary` reprints the tables from them. The census trip list skips 192759 as a
re-plan of 185940; the tables above were made from one run with that duplicate
filtered out, which matches what the committed dedupe produces.
