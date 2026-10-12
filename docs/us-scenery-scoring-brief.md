# Scenery scoring for the whole country: brief

**Status: scoped, not started.** Written 2026-10-12 against `main` at
`0fca74f`. Nothing in the tree has been touched. The answer goes to a new
`docs/national-scenery-scoring-verdict.md`, and its scripts to a new
`tools/national_scoring/`. This is an evaluation: it recommends and builds
nothing. The choice of system stays with the owner. This brief is deleted in
the merge that brings the verdict back (`docs/README.md`, rule 5).

## The goal

The US is now in scope: the 48 contiguous states and DC
(`docs/us-map-data-findings.md`). The scenic score was hand-set and calibrated
in New England. Decide, with measurements, whether to keep it, recalibrate it
per region, extend it with new components, or replace it with a different
system.

For each candidate, report:

- how it does on the only real ground truth (New England ratings);
- how it does on the only national proxy (designated byways);
- what it does to routes;
- what it would cost to build;
- which Western drives would be needed to trust it.

## What is already measured

**The ratings (New England only, one driver).**

- There are 151 marks over 18 traces in `traces/` in the main checkout. The
  analysis is `docs/scenic-rating-analysis.md`, untracked in another worktree;
  the task prompt gives its path.
- The shipped score separates liked from disliked roads at **0.719** over all
  151 (drive-cluster CI 0.626-0.826).
- On the Oct 6 marks, the first true holdout (72 marks, graph built
  2026-08-29), it scores **0.766** against a null of 0.628.
- **Score 7 or more is 96% liked (50/52).** Between 3 and 7 separation is
  0.541, below the 0.613 null, so the middle band is flat. Yet the router pays
  linearly for it.
- Every model fitted to the August marks failed the October holdout:
  - road class: 0.754, then 0.441;
  - `c_curves`: 0.678, then 0.562;
  - logistic fits: 0.44-0.69, all below the hand-set weights.
- Out of sample the load-bearing components are water (dropping it costs 0.12)
  and relief. Forest flipped from 0.786 to 0.481. Coast has zero marks.
- `docs/measuring-scenery.md` describes the instrument (`tools/analyze_trace.py`
  marks, the separation metric, the noise floor).

**Colorado, a full build in the USA feasibility review** (2026-10-10). The
prompt gives the build and its scripts.

- Mean score 3.69 against New England's 4.57. Km scoring 7 or more: 6.3%
  against 11.0%.
- Median WorldCover tree fraction on roads: 0.00 (57.8% of km at 0).
- `RELIEF_FULL` = 100 m pins 16.4% of all km and **46.6% of byway km** at the
  cap. New England: 5.7% and 20.6%.
- Iconic drives land mid-scale:
  - US 550 (Million Dollar Highway) 5.0;
  - CO 141 (Unaweep-Tabeguache) 5.1;
  - Rim Rock Drive 6.6;
  - Trail Ridge Rd 7.5, partly on byway credit.
- Byway proxy AUC, with the score's own byway term removed, within
  trunk-tertiary: New England 0.619 (38 routes), Colorado 0.661 (26 state
  byways). Script: `byway_auc.py` in the review's `tools/usa_feasibility/`.

**National data** (`docs/us-map-data-findings.md`):

- byway networks: 310 state relations, of which extract.py admits 48;
- FHWA America's Byways: 222 records;
- WorldCover's other classes (shrub, grass, bare, snow) cover the 48 states in
  131 cells, already streamed by landcover.py;
- PAD-US 4.1: 1.52 GB;
- 3DEP 1″ agrees with Terrarium to a median 1.9 m.

## The mechanism: where the score is defined and spent

- **`pipeline/score.py`:**
  - `:55` `WEIGHTS`: water .22, coast .13, forest .18, curves .13, relief .16,
    farm .06, views .05, scenic_tag .07, urban .14.
  - `:68-69` `RAW_BASE = 0.143`, `STRETCH = 1.20`, fitted so New England's p50 is
    about 4.5.
  - `:84` `RELIEF_FULL = 100.0`.
  - `:420` `blend` and `:431` `composite` are the single definitions the router
    reuses:

    ```python
    return 10.0 * np.clip((raw + RAW_BASE) * STRETCH + score_adj, 0.0, 1.0)
    ```

- **`pipeline/router.py`:**
  - `:1802` `_edge_scores` re-blends live from the user's six beauty weights
    (`:259` `BEAUTY_TYPES`, `:276` `BASELINE`).
  - `:1862` prices the score into the route:

    ```python
    penalty = self.km * (1.0 - scores / 10.0)           # km of "unscenic" road
    ```

  - It is scaled by `BETA = 8.0` (`:86`) and `PREF_CURVE = 2.0` (`:247`), which
    are one calibration. `:330` is `BEAUTIFUL_SCORE = 7.0`.
- **`pipeline/options.py:343`** builds the menu, and the app's "beautiful km",
  from `scores >= BEAUTIFUL_SCORE`.
- **`pipeline/landcover.py:58`** `TREE_CLASS = 10` is the only WorldCover class
  read.
- **`tests/test_calibration.py`** holds the distribution guards a change must
  keep or consciously move.

## Candidates to evaluate

Add more if the evidence suggests them.

- **A. Keep the system; recalibrate per region.** `RAW_BASE`, `STRETCH` and
  `RELIEF_FULL` per state or ecoregion.
- **B. Extend the components:**
  - open land and desert (WorldCover shrub, grass, bare);
  - snow and alpine;
  - protected designation (PAD-US, NPS);
  - canyon and vista terrain from elevation derivatives (slope variance,
    viewshed or prominence);
  - optionally, relief measured relative to its region.
- **C. Change the scale's meaning:** a percentile within a region or ecoregion,
  instead of an absolute 0-10.
- **D. A different system:** learned from external labels (byway designation,
  and whatever else the national data supports), with the marks as the check.
- **E. Hybrids:** for example A plus B, keeping New England's numbers exactly.

## Method

Score each candidate on:

1. **New England ratings.** Separation over all 151 marks and over the Oct 6
   holdout; precision of score ≥ 7; separation of the 3-7 band. Reuse
   analyze_trace.py's mark attribution, as `scenic-rating-analysis.md` did.
2. **The byway proxy** in New England, Colorado and at least one contrasting
   landscape: desert (Utah), or plains (Kansas or South Dakota). Remove the
   score's own byway term first.
3. **The score distribution per region**, and the share of km at 7 or more.
4. **Route effect:**
   - New England routes must not regress: beautiful km and extra minutes on a
     fixed set of trips, at pref 1 and 0.5.
   - Western routes: what changes on Colorado trips.
5. **Build cost** and data needs.
6. **The drives needed** to trust it in the West: how many marks, where, which
   score band.

A new region needs a build. Colorado's `processed` directory is in the review's
scratchpad (the path is in the prompt) and may have been cleaned up. Rebuilding
takes about 36 minutes with the review's `run_elevation.py` (bbox
`-109.4,36.75,-101.6,41.55`), `landcover.py --stream`, then
`score.py --no-cache`, `graph.py` and `closures.py`. One more region at most,
and keep 10 GB of disk free.

## Traps

1. **Don't fit weights to the marks.** Every August-fitted model collapsed on
   the October holdout, and class went from 0.754 to 0.441. With 151 marks from
   one driver the noise floor is high: five marks a side reach 0.82 by chance.
   The marks are a check, never a target. A candidate that only wins on marks it
   was tuned on has failed.
2. **There is no ground truth in the West.** Every mark is in New England. The
   byway proxy is only moderate (about 0.62-0.66) and partly circular: remove
   `c_scenic_tag`, and remember extract.py misses 168 of 310 network relations.
   Byways are also designated for history as well as views. No candidate can be
   shown right for the West from this data. Say what it predicts, and what drives
   would test it.
3. **The scale is spent by the router.** `km * (1 - score/10)`, `BETA` with
   `PREF_CURVE`, and the fixed 7.0 threshold in the options menu and the app
   all read the absolute number. Moving the scale moves every route and every
   menu. Report route effects, not chunk AUC alone.
4. **A regional percentile is a product decision, not a fix.** It makes the best
   road in Kansas an 8 and puts a seam at every region boundary. Price it, and
   leave the choice to the owner.
5. **Raising `RELIEF_FULL` globally changes New England.** Relief is one of the
   two components that hold up there. Any relief change has to keep New
   England's holdout separation.
6. **Forest is regional even inside New England.** It flipped between batches
   because everything up north is wooded. Expect every land-cover component to
   behave that way across the country.
7. **The marks are private.** `traces/` is gitignored and records where someone
   drove, to the second. Never commit traces, mark coordinates or anything that
   locates them. The repo is public.
8. **Don't fan out broad research sub-agents.** They recurse out of sight and
   cost the owner's session limit. Work directly.

## Done looks like

1. `docs/national-scenery-scoring-verdict.md`, with a bold `**Status:**` line on
   line 3, containing:
   - every candidate measured on the six criteria above;
   - New England non-regression shown;
   - a ranked recommendation;
   - the decisions reserved for the owner, at least absolute against regional
     scale and which landscapes count as scenery;
   - a drive plan for the West.

   Or a plain statement that the choice cannot be made without Western marks,
   with the smallest drive plan that would make it.
2. Scripts and small, non-locating results in `tools/national_scoring/`.
   Nothing changed in `pipeline/`, `server/`, `ios/`, `tests/` or `data/`.
3. This brief committed unchanged beside the verdict, on a branch off `main`,
   not merged.
