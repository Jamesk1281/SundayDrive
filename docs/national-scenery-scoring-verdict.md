# Scenery scoring for the 48 states: verdict

**Status:** measured 2026-10-12 against `main` at `0fca74f`. Nothing in `pipeline/`, `server/`, `ios/`, `tests/` or `data/` changed. Every figure comes from a script in `tools/national_scoring/`, and its output is in `tools/national_scoring/results/`, unless the text says otherwise. It answers the national scenery scoring brief, `docs/us-scenery-scoring-brief.md` until this merges and [briefs.md](briefs.md) after; "the brief" below means that one. The choice of system is the owner's. This recommends and builds nothing.

## The verdict

**The structural choice can be made now. Whether it is right in the West cannot.
That takes about 160 marks from four Western landscapes (§9).**

Ranked:

1. **Keep the absolute scale and New England's numbers, and add three
   components (candidate E1): mountain- and canyon-scale terrain, desert and
   rock land cover, and landmark designation.** It is the only family that does
   all three of these:
   - It leaves New England intact. 1.3% of its km move by more than 0.25. The
     marks are unchanged within noise (Oct holdout 0.766 → 0.773, paired 90%
     interval +0.000 to +0.009). Of 24 test trips, one changes route at each
     pref.
   - It improves the Western proxy everywhere except Utah within ecoregion,
     which stays flat. The national byway pool rises from 0.569 to 0.624.
   - It lifts the iconic Western drives over 7 without promoting suburbs or
     plains:
     - Trail Ridge Road 7.6 → 8.9;
     - Rim Rock Drive 6.6 → 8.0;
     - SR 128 6.0 → 7.5;
     - Capitol Reef Scenic Drive 6.2 → 7.8;
     - I 70 east of Denver stays at 0.1, US 287 on the plains at 1.5.

   **Its limit:** it barely ranks roads *within* a Western landscape. Within an
   ecoregion, Utah's scenic-designated byways separate at 0.489 under E1 and 0.491
   shipped, which is chance. No hand-built candidate fixes that (§4).
2. **Ship nothing (S0).** This is still defensible. The shipped score is not
   broken in the West, but it is blind within a landscape (Colorado 0.564, Utah
   0.491). E1 is better, not cured.
3. **E1 with a per-state percentile on top (E2), only if the owner chooses a
   regional meaning for 7** (§7). It keeps E1's ranking and gives every state the
   same 13.1% "beautiful" share. Its seams between states are small, a shipped 6.0
   becomes 6.9 in Colorado and 7.1 in Utah. The price is minutes on the plains.
4. **Recalibrating per state alone (A1, A2, C1)** changes what 7 means and nothing
   about which road is better. Within a region it ranks exactly as shipped (§4).
5. **Not recommended: a percentile per ecoregion (C2).** It makes the best roads
   on the High Plains suburban Denver arterials rated 7 to 8 (Briargate Parkway,
   West 80th Avenue, Simms Street). It puts a 3.5-point seam at the Front Range. It
   moves 75% of New England's km. It drags the national byway pool to chance
   (0.495).
6. **Not recommended: any system learned from byway labels (D1–D3).** It wins the
   proxy and fails the ground truth:
   - D1 scores the Mass Pike 9.2 and drops the 151-mark separation to 0.589.
   - The fairest version, D3, keeps the shipped class penalty and still:
     - rewrites 59% of New England's km by more than a point;
     - cuts shipped-beautiful km on New England trips by 18%;
     - would call 58% of Colorado's mountain km beautiful.

   It learned what a byway is: a rural main road away from development,
   often through a town. That is not what the driver rates (§6).

**Two decisions are the owner's and are priced, not made:** absolute against
regional scale (§7), and which landscapes count as scenery (§8).

**Two findings change numbers quoted elsewhere:**

- **New England's served share of km at 7 or more is 13.1%, not 11.0%, and its
  mean is 4.89, not 4.57.** The brief and the feasibility review read the deployed
  build's stored scores. Those predate the 2026-08-29 surface change, and the
  Router strips their unpaved penalty out at load (`Router._load_unpaved`).
  - The marks are unaffected: every mark figure is identical to three decimals on
    either column.
  - New England's byway proxy moves from the brief's 0.619 to 0.611.
  - The West-versus-New England gap is wider than the brief states: Colorado's
    6.3% at 7 or more is against 13.1%, not 11.0%.

  `docs/unpaved-and-urban-verdict.md` already records the 4.570 → 4.888 shift.
- **On the plains the shipped router already spends minutes for nothing it can
  show.** On six eastern-Colorado trips at pref 1 it adds a mean 41 minutes for
  2.8 beautiful km in total. That is the flat 3–7 band (rating analysis §3) being
  paid for linearly, in a landscape with almost nothing above 7. Every regional
  scale makes it worse: the mean detour rises to 55 minutes under C1 and 69 under
  C2. This is a reason to run the
  convex-cost experiment before a national launch, whatever the scoring choice.

---

## 1. What was measured, and on what

**Three regions, built with the unmodified pipeline:**

| region | road km | landscapes (EPA Level III ecoregions, by km) | build |
|---|---:|---|---|
| New England | 236,477 | coastal zone 49%, highlands 29%, Acadian plains 16% | deployed `data/processed-ne`, read only |
| Colorado | 172,624 | High Plains 39%, Southern Rockies 25%, Southwestern Tablelands 19%, Colorado Plateaus 11% | the feasibility review's build |
| Utah | 77,658 | Central Basin and Range 49%, Colorado Plateaus 27%, Wasatch and Uinta 17% | new, this evaluation, 15.5 min |

Utah is the desert contrast. Colorado's eastern 58% is High Plains and Tablelands,
so it doubles as the plains region, and Kansas was not built.

**New inputs, all national:**

- **WorldCover's other classes** (shrub, grass, crop, built, bare, snow, moss) at
  about 100 m and 1 km. These are the same tiles `landcover.py` already reads.
- **Terrain derivatives from `elevation.tif`:**
  - the elevation range within 3 km and 6 km;
  - height above the local minimum ("above", vista);
  - depth below the local maximum ("below", canyon or valley wall).

  Western Terrarium has in-band spikes, so the derivatives are despiked (README).
- **PAD-US 4.1 designations:**
  - "landmark": national park, monument, conservation, recreation or scenic area,
    lake- or seashore, wilderness or wilderness study area, state park or
    wilderness;
  - GAP status 1–2;
  - any federal or state land.
- **Byway labels, three independent kinds:**
  - **OSM, extract.py's own:** New England's 38 routes (3,034 km within
    trunk–tertiary) and the 15 Utah relations it admits (1,405 km).
  - **OSM, a full state network:** Colorado's 26 `US:CO:Scenic` byways (4,040 km),
    from the feasibility review's way list.
  - **FHWA America's Byways, split by intrinsic quality.** "Scenic or natural"
    (S/N) covers New England 427 km, Colorado 1,164 km and Utah 1,109 km.
    Byways designated only for history, culture or archaeology (H/C) are the
    contrast. This split answers the brief's point that byways are designated
    for history as well as views.

**The metrics:**

- New England marks: `analyze_trace.py`'s own attribution, 400 m window, 3 s
  reaction. The shipped score reproduces the rating analysis exactly: 0.719 over
  151, 0.766 on the Oct holdout, 50 of 52 liked at 7 or more, 0.541 in the 3–7
  band.
- The byway proxy: length-weighted AUC within trunk–tertiary, with the score's
  byway term removed, as `byway_auc.py` does. It is computed two ways:
  - **state-wide**, which is mostly mountains against plains in the West;
  - **within ecoregion**, pairs drawn only inside one landscape. This is the harder
    test, and the one the relief cap is about.
- Routes: the shipped Router with `_edge_scores` monkeypatched. The trips are
  24 New England, 24 Colorado (6 of them plains-only) and 14 Utah, between town
  centres, never trace points. Each runs at pref 0, 0.5 and 1.

## 2. The candidates

None of these constants is fitted to the marks. The region-level calibrations are
fitted to each region's own score distribution, the way `RAW_BASE` and `STRETCH`
were. The learned candidates are fitted to byway labels only.

| | what | New England |
|---|---|---|
| **S0** | shipped | — |
| **A1** | `RAW_BASE`, `STRETCH` per state, fitted so p50 and p99 match New England's (CO 0.396/0.946, UT 0.274/1.142) | identical |
| **A2** | A1, plus `RELIEF_FULL` per state, set to pin the same 5.7% of km New England's 100 m does (CO 174 m, UT 182 m) | identical |
| **B1** | + `c_grand` = clip((3 km range − 300) / 600), weight 0.10. Nonzero on 4.6% of New England's km, 18.5% of Colorado's, 25.7% of Utah's | 1.0% of km move > 0.25 |
| **B2** | desert: forest slot becomes max(`c_forest`, shrub + bare + moss + snow within 1 km) | 0.02% |
| **B3** | B2 plus grassland net of built land | 5.0% |
| **B4** | + 0.07 × inside a PAD-US landmark | 0.4% |
| **E1** | B1 + B2 + B4 | **1.3%** |
| **E1g** | E1 with grassland (B3) | 6.4% |
| **C1** | shipped score quantile-mapped per state onto New England's distribution | identical |
| **C2** | the same per EPA Level III ecoregion (slivers under 2,000 km keep the absolute score) | 75% |
| **E2** | E1, then C1 | 1.2% |
| **E3** | A2 plus desert plus landmark | 0.4% |
| **D1 / D2** | logistic regression on 21 features, trained on OSM / FHWA-S/N byways in all three regions; quantile-anchored to New England's distribution | 89% |
| **D3** | D1 without the road-class feature; the learned logit replaces the blend only, and the shipped `CLASS_ADJ` is re-applied through `composite` | 89% |

**How the hand-set constants were chosen:**

- `G0` = 300 m sits just above New England's 95th-percentile road (293 m within
  3 km), so the term is zero on 95% of New England's km.
- `G1` = 900 m is a hand choice: full credit at the scale of Colorado's deepest
  byway valleys. The 99th percentile of Colorado byway km is 979 m and Utah's
  857 m.
- The weights borrow existing roles: relief-scale terrain at 0.10 (relief is 0.16),
  designation at 0.07 (the byway tag's weight).
- Desert takes the forest slot via `max()`, so it adds no weight mass and leaves
  the forest/park slider whole.

§5 sweeps every one of these constants.

## 3. New England: the ground truth

All 151 marks, nulls one-sided at 5% (all 0.589, Oct 0.628):

| | all 151 | Oct 72 (holdout) | ≥ 7 liked | 3–7 band | km moved > 0.25 / > 1 |
|---|---|---|---|---|---|
| **S0 shipped** | **0.719** | **0.766** | **96.2% (52)** | 0.541 (79) | — |
| A1, A2, C1, E3 | 0.719 | 0.766–0.767 | 96.2% (52) | 0.540–0.541 | 0–0.4% / 0 |
| B1 +terrain | 0.721 | 0.773 | 96.2% (53) | 0.534 | 1.0% / 0.01% |
| B3 +desert+grass | 0.720 | 0.769 | 96.2% (52) | 0.558 | 5.0% / 0.2% |
| **E1** | **0.721** | **0.773** | **96.2% (53)** | 0.534 | **1.3% / 0.05%** |
| E1g | 0.722 | 0.776 | 96.2% (53) | 0.551 | 6.4% / 0.3% |
| E2 | 0.721 | 0.774 | 96.2% (52) | 0.543 | 1.2% / 0.05% |
| C2 per ecoregion | 0.735 | 0.753 | 94.2% (52) | 0.666 | 75% / 1.0% |
| D1 byway-learned | 0.589 | 0.692 | 76.6% (47) | 0.672 | 89% / 61% |
| D2 FHWA-learned | 0.537 | 0.637 | 76.1% (46) | 0.520 | 90% / 63% |
| D3 learned blend | 0.682 | 0.794 | 95.6% (45) | 0.496 | 89% / 59% |

Each candidate's difference from shipped, under a paired drive-cluster bootstrap
(4,000 resamples, 90% interval, `marks_ci.csv`):

| | all | Oct |
|---|---|---|
| E1 | +0.002 [0.000, +0.004] | +0.007 [0.000, +0.009] |
| C2 | +0.016 [−0.010, +0.040] | −0.013 [−0.041, 0.000] |
| D3 | −0.037 [−0.095, +0.050] | +0.029 [−0.010, +0.119] |
| D1 | −0.131 [−0.240, −0.001] | −0.073 [−0.284, +0.120] |

What it says:

- **E1 is New England-neutral by construction, and the marks confirm it.** Its
  new terms are nearly zero there:
  - shrub, bare, moss and snow all round to 0.000 of New England's road
    surroundings;
  - `c_grand` touches 11% of marks;
  - landmark designation touches none.
- **D3 is the case trap 1 describes.** It is up on one batch and down on the
  other, and it rewrites the map underneath both. Its Oct gain is the largest
  of any candidate, and its interval includes zero.
- **C2's 3–7 band of 0.666 is the one interesting mark result here. It is a
  between-landscape shift, not a ranking fix.**
  - Within an ecoregion, C2 ranks exactly as shipped, by construction. All of
    its effect is a level shift between landscapes.
  - It lowers the Northeastern Highlands and raises the coastal zone: a shipped
    6.0 becomes 5.4 in one and 6.3 in the other (`seams.csv`).
  - Among October's 35 middle-band marks, highland roads were liked 45% of the
    time (20 marks) and coastal-zone roads 67% (15 marks). So October's band rises
    from 0.549 to 0.750, while August's, all in the coastal zone, falls from 0.625
    to 0.588.
  - At the top it goes the other way. Highland marks overall were liked more
    (77% against 67%), so C2's Oct holdout falls to 0.753.

  The lean, "the absolute scale overrates middling highland roads", rests on 35
  marks and is worth one targeted drive. It is not a reason to adopt a scale
  that moves 75% of New England's km. It is also the forest flip (trap 6) in
  another form.

**Routes** (24 trips; beautiful km counted on the shipped score, which is the
validated claim):

| pref | | extra min, mean | beautiful km (shipped scale) | km shared with shipped |
|---|---|---|---|---|
| 0.5 | S0 | 19.6 | 536 | — |
| 0.5 | E1 | 20.0 | 556 | 98% |
| 1 | S0 | 30.2 | 711 | — |
| 1 | E1 | 31.4 | 732 | 99% |
| 1 | E1g | 31.0 | 730 | 97% |
| 1 | C2 | 32.2 | 718 | 81% |
| 1 | D3 | 26.4 | **584** | 60% |

Exactly one E1 trip changes at each pref. At pref 1, Pittsfield–Manchester VT gains 20.8
beautiful km for 29.8 more minutes, inside the router's existing exchange rate
of 1.48 minutes per beautiful km. **New England does not regress under E1.** D3
fails non-regression outright.

## 4. The byway proxy, and where the West goes blind

Trunk–tertiary, with the byway term removed. Each cell is state-wide AUC, then
within-ecoregion AUC:

| | NE OSM | NE FHWA S/N | CO OSM (26) | CO FHWA S/N | UT OSM | UT FHWA S/N |
|---|---|---|---|---|---|---|
| **S0 shipped** | 0.611 / 0.574 | 0.618 / 0.566 | 0.661 / **0.518** | 0.718 / **0.564** | 0.555 / **0.483** | 0.560 / **0.491** |
| A1 | 0.611 / 0.574 | 0.618 / 0.566 | 0.654 / 0.510 | 0.707 / 0.551 | 0.554 / 0.482 | 0.558 / 0.489 |
| A2 | 0.611 / 0.574 | 0.618 / 0.566 | 0.647 / 0.516 | 0.696 / 0.559 | 0.543 / 0.481 | 0.549 / 0.489 |
| B1 +terrain | 0.614 / 0.576 | 0.624 / 0.572 | 0.669 / 0.530 | 0.731 / 0.588 | 0.561 / 0.487 | 0.567 / 0.497 |
| B2 +desert | 0.611 / 0.574 | 0.618 / 0.565 | 0.673 / 0.521 | 0.730 / 0.566 | 0.579 / 0.485 | 0.575 / 0.477 |
| B4 +landmark | 0.612 / 0.574 | 0.624 / 0.568 | 0.663 / 0.520 | 0.720 / 0.571 | 0.565 / 0.489 | 0.569 / 0.495 |
| **E1** | 0.614 / 0.576 | 0.629 / 0.574 | **0.681 / 0.535** | **0.744 / 0.596** | **0.596 / 0.496** | **0.593 / 0.489** |
| E1g | 0.620 / 0.578 | 0.629 / 0.573 | 0.685 / 0.548 | 0.725 / 0.573 | 0.585 / 0.467 | 0.577 / 0.463 |
| C1 (= S0 within a state) | 0.611 / 0.574 | 0.618 / 0.566 | 0.661 / 0.518 | 0.718 / 0.564 | 0.555 / 0.483 | 0.560 / 0.491 |
| C2 | 0.552 / 0.574 | 0.585 / 0.566 | 0.514 / 0.518 | 0.536 / 0.564 | 0.455 / 0.483 | 0.476 / 0.491 |
| D1, leave-one-region-out | 0.798 / 0.742 | 0.852 / 0.810 | 0.812 / 0.723 | 0.879 / 0.793 | 0.798 / 0.711 | 0.819 / 0.733 |
| D3, leave-one-region-out | 0.682 / 0.580 | 0.714 / 0.660 | 0.733 / 0.630 | 0.788 / 0.660 | 0.672 / 0.539 | 0.666 / 0.521 |

National pool: the three regions at equal weight, so a Utah byway km competes
with a New England road (`byway_pooled.csv`):

| | OSM | FHWA S/N |
|---|---|---|
| S0 | 0.599 | 0.569 |
| A1 | 0.614 | 0.603 |
| C1 | 0.613 | 0.608 |
| **E1** | 0.624 | 0.624 |
| E2 | 0.635 | 0.637 |
| C2 | 0.504 | 0.495 |
| D3 | 0.740 | 0.767 |

What it says:

1. **The feasibility review's "the score doesn't collapse in Colorado" (0.661) is
   mostly mountains beating plains.** Inside one landscape, the shipped score is
   at 0.518 on Colorado's 26 byways and below chance in Utah (0.483). New England
   keeps 0.574 there.
2. **A and C cannot fix ranking, by construction.** A monotone map within a
   region leaves within-region AUC unchanged, and C1's rows equal S0's. What they
   change is the meaning of 7, the national pool (S0 0.569 → C1 0.608) and the
   routes. Raising `RELIEF_FULL` per state (A2) *lowers* the proxy slightly.
   Moderate hills lose credit to components that are noise in the West.
3. **E1 is the best hand-built candidate everywhere, and its gains are small
   where they are needed.** It takes Colorado within ecoregion from 0.564 to
   0.596 on scenic byways, and leaves Utah within ecoregion at 0.489. The relief
   cap bites hardest where relief is pinned: 46.9% of Colorado's and 45.3% of
   Utah's byway km, against New England's 19.4%. Among pinned chunks:
   - Colorado's scenic byways move from 0.496 to 0.537;
   - Utah's don't move (0.489 → 0.487, `sensitivity.csv`).
4. **The best Western features, alone and within ecoregion** (`describe.txt`,
   Colorado then Utah, FHWA S/N):
   - the 3 km range, 0.673 / 0.554;
   - depth below the local maximum, 0.678 / 0.580;
   - uncapped 750 m relief, 0.654 / 0.590;
   - shipped `c_relief`, 0.623 / 0.582.

   Pointing the wrong way:
   - curvature, 0.453 / 0.462;
   - grass in Colorado, 0.399;
   - cropland.

   Byways being the main roads through a landscape is the likely reason for
   curvature, as the rating analysis found in New England.
5. **The history-only byways are a useful control.** The shipped score does *not*
   find them: Colorado H/C 0.521, Utah 0.440. So its moderate S/N result is
   about scenery, not designation habits. The learned models find both kinds
   (D1, leave-one-region-out, Colorado H/C 0.764), which is the tell that they
   learned byway-ness.

## 5. E1's constants, swept rather than fitted

Same metrics, one constant changed at a time (`sensitivity.csv`):

| variant | NE Oct | NE km moved > 0.25 | CO S/N within eco | UT S/N within eco | CO share ≥ 7 | UT share ≥ 7 |
|---|---|---|---|---|---|---|
| S0 | 0.766 | — | 0.564 | 0.491 | 6.3% | 4.7% |
| **E1 as specified** | 0.773 | 1.3% | 0.596 | 0.489 | 8.7% | 9.0% |
| G0 = 200 m | 0.785 | 2.8% | 0.594 | 0.491 | 9.4% | 9.7% |
| G0 = 400 m | 0.766 | 0.7% | 0.596 | 0.487 | 8.1% | 8.4% |
| G1 = 600 m | 0.774 | 2.4% | 0.599 | 0.493 | 10.0% | 10.6% |
| G1 = 1,200 m | 0.766 | 0.8% | 0.590 | 0.487 | 8.2% | 8.3% |
| W_GRAND 0.05 | 0.766 | 0.6% | 0.585 | 0.485 | 7.8% | 7.9% |
| W_GRAND 0.20 | 0.774 | 2.4% | 0.612 | 0.494 | 10.3% | 11.2% |
| W_PROT 0 | 0.773 | 1.0% | 0.590 | 0.484 | 8.6% | 8.2% |
| W_PROT 0.14 | 0.773 | 1.3% | 0.600 | 0.504 | 8.9% | 9.8% |
| no desert | 0.773 | 1.3% | 0.594 | 0.500 | 8.4% | 6.8% |

- **No variant is a knife-edge.** Every one keeps New England's ≥7 precision at
  96.2% and leaves Utah within ecoregion between 0.484 and 0.504.
- **The constants mostly decide how much of the West clears 7**, from 7.8% to
  10.3% of Colorado. That is a calibration question for Western marks, not for
  this data.
- **Trap 5, measured** (`global_relief.csv`). Raising `RELIEF_FULL` for everyone
  costs New England and buys the West nothing:

  | `RELIEF_FULL` | NE Oct | marks at ≥ 7 | NE share ≥ 7 | CO S/N within eco |
  |---|---|---|---|---|
  | 100 m (shipped) | 0.766 | 52 | 13.1% | 0.564 |
  | 150 m | 0.764 | 45 | 10.5% | 0.569 |
  | 175 m | 0.759 | 41 | 9.8% | 0.570 |
  | 250 m | 0.750 | 34 | 8.5% | 0.568 |

  The cap is not the binding problem. What is missing in the West is a signal for
  what makes one mountain road better than the next. Adding a term above the
  cap, as `c_grand` does, is the cheaper lever.

## 6. Why the learned system fails

D1's coefficients (`eval_all.txt`), standardised:

- **Strongest:** built land within 1 km −1.62, road-class adjustment −0.78,
  tree cover −0.68, grass −0.60.
- **Positive:** relief +0.40, town credit +0.26, water +0.19.
- **Negative:** curvature −0.12.

So a byway is a rural main road away from development, through a town now and
then. Two consequences:

- **Inside trunk–tertiary, bigger roads are likelier byways.** Applied to
  motorways, the class coefficient puts the Mass Pike at 9.2, I-95 at 8.9 and
  I-80 west of Salt Lake at 9.1.
- **Removing class (D3) fixes the motorways and leaves the rest.** Town credit
  stays positive, the term the marks never endorsed. Curvature stays negative.
  D3 rewrites 59% of New England's km by more than a point and calls 58% of
  Colorado's mountain km and 40% of Utah's canyon country beautiful.

This is the August-marks failure again with a different label. A model fitted to
a proxy learns the proxy. The byway labels are a check, like the marks, not a
target.

## 7. Absolute or regional: the owner's decision, priced

The question is whether a 7 in Kansas should mean "as good as a 7 in Vermont" or
"among the best Kansas has".

**Share of km at 7 or more, and mean score** (`distributions.csv`):

| | NE | CO all | CO mountains | CO plains | CO plateau/canyon | UT all | UT mountains | UT plateau/canyon | UT basin |
|---|---|---|---|---|---|---|---|---|---|
| **absolute: S0** | 13.1% (4.89) | 6.3% (3.69) | 21.6% | 0.6% | 3.5% | 4.7% (3.70) | 16.1% | 3.7% | 1.5% |
| **absolute: E1** | 13.4% | 8.7% (3.85) | 29.1% | 0.6% | 6.8% | 9.0% (4.33) | 24.1% | 12.0% | 2.8% |
| per state: A1 | 13.1% | 14.7% (5.20) | 45.9% | 2.5% | 10.6% | 13.4% | 40.0% | 11.5% | 6.0% |
| per state: C1 | 13.1% | 13.1% (4.89) | 41.9% | 2.0% | 8.8% | 13.1% | 39.2% | 11.1% | 5.8% |
| per state: E2 | 13.1% | 13.1% | 41.2% | 1.4% | 12.1% | 13.1% | 32.3% | 17.9% | 4.6% |
| per ecoregion: C2 | 13.1% | 13.1% | 13.1% | 13.1% | 13.1% | 12.8% | 13.2% | 13.1% | 12.6% |

**What each one costs:**

- **Absolute (S0, E1)**
  - **Product:** "beautiful miles" means one thing everywhere, which is what the
    96% claim was validated as. A plains driver sees nearly none: 0.6% of
    eastern Colorado's km.
  - **Routes:** at pref 1, plains trips still detour a mean 41 min (S0) or 39 min
    (E1) for nothing visible: 2.7–2.8 beautiful km over six trips.
  - **Seams:** none.
- **Per state (C1, E2)**
  - **Product:** every state gets 13.1%. The ≥7 claim becomes "among the best
    13% of this state", a different claim from the one the marks back. Colorado's
    beautiful km on the 24 trips at pref 1 go from 514 shipped to 757.
  - **Routes:** plains detours grow from 41 to 55 min a trip with no gain on the
    shipped scale (2.9 km). The mountain trips are about the same.
  - **Seams:** small between similar states. A shipped 6.0 is 6.9 in Colorado
    and 7.1 in Utah. Wherever a state's landscape mix differs from its
    neighbour's, a road changes score at the line.
- **Per ecoregion (C2)**
  - **Product:** every landscape gets 13%, including the suburbs. Denver's
    Briargate Parkway, West 80th Avenue and Simms Street, Colorado Springs' US 24
    (7.9), and Salt Lake's Wasatch Boulevard all clear 7.
  - **Routes:** plains detours reach 69 min a trip. Colorado's trips lose
    shipped-beautiful km (514 → 421) while chasing local "beauty".
  - **Seams:** 3.5 points at the Front Range (a shipped 5.0 is 7.7 on the High
    Plains, 4.2 in the Southern Rockies). It moves 75% of New England's km.

The middle option, per state on top of E1 (E2), is the cheapest regional scale.
It keeps E1's ranking and the national pool's best figure (0.637). One fact
should weigh heavily either way: **regional scales spend minutes on the plains**,
and only the absolute scale leaves them where they are. If the owner wants
"regional", it should come with the convex cost that stops paying for 4 → 5
(rating analysis §9.4; `docs/scenery-cap-options.md` prices it).

## 8. Which landscapes count: the owner's decision, priced

| landscape | how it would enter | what it moves | what the checks say |
|---|---|---|---|
| **Canyon and mountain terrain** (`c_grand`, 3 km range above 300 m) | additive, 0.10 | CO ≥7 6.3% → 8.3%; UT 4.7% → 6.3%; NE 1.0% of km | best Western feature within landscape; NE Oct +0.007. "Depth below" and "height above" flip between the two New England batches (below: Aug 0.543, Oct 0.759; above: 0.658, 0.370), so the combined range is used, not either alone |
| **Desert, rock and alpine** (WorldCover shrub + bare + moss + snow within 1 km) | forest slot via `max()` | UT ≥7 4.7% → 6.2%, its plateau 3.7% → 8.2%; CO 6.3% → 6.5%; NE 0.02% of km | modestly positive on Western byways (CO S/N 0.637 state-wide). In New England these classes are quarries and gravel pits (marks AUC 0.271), and `max()` with forest is what keeps them harmless there |
| **Grassland and prairie** (WorldCover grass net of built) | forest slot via `max()` | CO plains ≥7 0.6% → 1.3%, Colorado's basin 0.9% → 4.5%; US 287 on the plains 1.5 → 3.0; NE 5% of km | points the wrong way on every check that sees it: CO S/N within eco 0.399; NE marks Oct 0.330. WorldCover also calls most of Colorado's sagebrush "grass" (41% grass against 2% shrub), so it can't separate prairie from the Western Slope. **If prairie counts, this data can't find the good prairie** |
| **Snow** | — | WorldCover snow on roads is 0.000 in all three regions | nothing to build; alpine arrives through terrain and elevation instead |
| **Protected landmarks** (PAD-US) | additive, 0.07 | 0.4% of NE chunks, 0.7% of CO, 2.8% of UT | small but positive (UT S/N within eco 0.484 → 0.504 across weight 0 → 0.14). A designation term like the byway tag, so partly circular against byways: park roads are often byways |
| **Town** (unchanged) | — | — | not re-tested here. The rating analysis's §9.3 test still stands, and it matters more in the West: D1 leaned on town credit (+0.26) |

The recommended E1 counts terrain, desert and rock, and landmarks. It does not
count grassland. That is a recommendation from the checks, and the owner may
overrule it on taste. The price of overruling is in the table.

## 9. The drives needed to trust any of it in the West

No candidate can be shown right in the West from this data. Every mark is in New
England, and the proxy is moderate and partly a measure of byway-ness. What
follows is the smallest plan that would decide **between S0, E1 and the scale
choice**, built from `decisive_roads.csv`.

That file lists named Western roads of 10 km or more, not tagged unpaved, grouped by where
the candidates disagree across the 7 line:

| | Colorado roads / km | Utah roads / km |
|---|---|---|
| E1 promotes to 7+ (S0 below 7) | 27 / 908 | 21 / 451 |
| both 7+ | 40 / 1,204 | 19 / 530 |
| percentile per state promotes, E1 doesn't | 39 / 863 | 25 / 672 |
| percentile per ecoregion promotes, nothing else does | 13 / 188 | 4 / 75 |
| agreed dull (all below 4) | 114 / 6,067 | 88 / 2,947 |

**Four landscapes, about 40 marks each, about 160 in all.** That is the same size
as New England's whole set. It needs **at least 10 dull marks in each
landscape**. New England's 38 dull marks were the binding constraint; with 30
nice and 10 dull, chance reaches 0.68.

1. **Canyon country** (Moab, Island in the Sky, Capitol Reef; two days). Drive the
   roads E1 promotes: SR 128 (S0 6.0, E1 7.5), Grand View Point Road, Capitol Reef
   Scenic Drive, Natural Bridges' park road. Add agreed-7+ roads as the precision
   control (Potash Road, SR 279, which both score 7+), and SR 12, which both put in the middle. Add
   agreed-dull desert highways for the dull side.
2. **The San Juans** (two days). This is where relief is pinned and only
   `c_grand` ranks. CO 145 and CO 133 (E1 promotes), the Million Dollar section
   (both 7+), CO 62 and Tarryall-type roads (only per-state percentile promotes),
   and the valley highways for dull.
3. **The eastern plains and the Front Range edge** (one day). This decides the
   owner's own view of the absolute-versus-regional question. Drive the plains'
   best roads, which only a regional scale calls beautiful, and the suburban
   arterials C2 promotes. US 287 and US 385 are agreed dull.
4. **The Great Basin** (west Utah, one day). Does desert count? Gunlock Road
   (E1 promotes), US 6 between Delta and Eureka (2.4 shipped, 3.3 under E1), SR 21.

**Pre-registered predictions,** to be written into the drive's brief *before*
the drive. The tables above are the predictions:

- **E1 is right** if its promoted roads are liked at about New England's
  precision.
  - Detecting 0.92 against a middle-band 0.68, one-sided at 5% with 80% power,
    takes about 18 marks: 17 of 20 liked or better.
  - The agreed-dull roads should be liked well below the base rate.
- **S0 is right** if E1's promotions are liked no more than the middle band is.
- **The per-state percentile is safe** if its promotions (roads E1 leaves at 6.5)
  pass the same 17-of-20 bar. If they fail, regional "beautiful miles" overclaims.
- **Prairie counts for this driver** if the plains' best roads are liked at the
  ≥7 rate. One driver cannot settle that for the product.

**Two cautions:**

- **This is one rater, and he built the app.** A second driver on even one
  Western landscape is the cheapest way to tell "E1 is right" from "E1 agrees
  with its author". It matters more here than in New England, because the
  absolute-versus-regional question is about other people's taste.
- **Don't fit the constants to these marks either.** If E1's promotions pass, keep
  E1's constants. If they fail, the next candidate is tested on the next drive,
  not tuned on this one.

## 10. Build cost

| | code | data | compute (measured on one region) | app | New England |
|---|---|---|---|---|---|
| **A1 / A2** | Per-region `RAW_BASE`, `STRETCH`, `RELIEF_FULL` in score.py, keyed by a region id on every chunk (a state-polygon join, as `attrs.py` does). `composite` and `_edge_scores` take per-edge arrays. `test_calibration.py` goes per region. **1–2 days** | none | seconds | none | untouched |
| **E1** | `landcover.py` counts four more classes in the windows it already reads. A 3 km max/min pass from `elevation.tif`. A PAD-US stage writing one flag per chunk. Two `WEIGHTS` entries and the forest-slot `max()`. The breakdown label "forest/park" becomes wrong for desert, so `BEAUTY_TYPES` and its `Models.swift` mirror need a rename or a new type. Tests. **3–5 days** | PAD-US 4.1, 1.52 GB (2.0 GB unpacked, public domain); WorldCover adds no bytes | terrain ~70 s, ~3 GB; PAD-US 3–4 min; WorldCover nothing extra. Nationally, terrain rides on the tiled elevation stage the feasibility review already requires | a label | a rebuild and deploy; 1.3% of km move by more than 0.25 |
| **C1 / E2** | A quantile table per region (2,001 points each), applied after the live blend in `_edge_scores`. This breaks the `score = composite(blend)` identity `test_score_matches_components` checks, and a user's slider re-weighting is mapped through the default-weight table. Region id per edge, seams at state lines. **2–3 days** | none | seconds | none | untouched |
| **C2** | as C1, per ecoregion | EPA Level III ecoregions, 28 MB, public domain | seconds | none | 75% of km move |
| **D** | Label pipeline (state byway networks, FHWA), training, model artefact, retraining on every data refresh. The six sliders no longer map onto weights. **1–2 weeks**, and it fails the marks | FHWA layer, no licence stated | minutes | sliders | 59–63% of km move by more than a point |

**Nationally,** WorldCover's other classes need no extra fetch: they are the
131 cells and 9.1 GB `landcover.py` already streams. Block-count grids like
`wc_grids.py`'s would be about 1.4 GB for the 48 states (235 MB for 22 tiles).

## 11. What this can't tell you

- **Whether E1 is right in the West.** §9 is the test.
- **Anything about the middle band in the West.** New England's 3–7 band is flat
  (0.541), and no candidate here fixes it except C2. C2's figure is probably
  regional confounding, and it costs 75% of New England's km.
- **Loops.** Only point-to-point routes were measured. In Utah, routes barely
  move under any candidate (95–100% shared), because the network offers few
  alternatives. There, the score mostly changes what the card says rather than
  where the car goes: Utah's 14 trips at pref 1 carry 125 beautiful km shipped,
  219 under E1 and 680 under D3. Loops choose among more roads and may differ.
- **Speeds.** The route minutes use New England's speed model, which the
  feasibility review found 19–28% slow in Colorado. That inflates every
  Western "extra minutes" figure about equally across candidates.
- **One region per landscape.** Kansas or South Dakota prairie, Southern
  Appalachia and the Pacific coast were not built. Colorado's plains stand in
  for prairie, and the coast component is still untested anywhere (rating
  analysis §8).

## Reproducing this

`tools/national_scoring/README.md` gives the order, the environment variables
and the measured cost of each step. In short, `fetch_inputs.sh`, then
`wc_grids.py` for the tiles, `build_region.sh` per region, `extract_marks.py`,
then the measurement scripts. The marks pickle and every region build stay
outside the repo. Nothing in `results/` locates a mark.
