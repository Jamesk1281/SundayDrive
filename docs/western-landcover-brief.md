# Western land cover: can a US source tell sagebrush from prairie? (brief)

**Status:** diagnosed, not fixed. Written 2026-10-18 in the master session. Nothing in
`pipeline/`, `server/`, `ios/`, `tests/` or `data/` has been touched for this. Work on
a branch off **`usa`**, never `main`, and never merge into `main`. The answer goes in
`docs/western-landcover-verdict.md`. This brief is deleted in the merge that brings
that verdict back into `usa`, so nothing permanent may cite it.

**Decided before this brief, so don't reopen it:** the national scale stays absolute
(candidate E1, as built on `usa` at 5219744). A 7 means the same thing in Colorado as
in Vermont. Per-state and per-ecoregion percentiles are out. That makes land cover
matter more, because it has to be right in absolute terms, not just within a region.

## The goal, as measured

The scenery score's desert term reads ESA WorldCover 2021 (10 m, global). In the
West, WorldCover can't tell the landscapes apart that the score most needs to
separate:

- **Colorado's road surroundings are 41% "grassland" and 2% "shrubland"**
  (`tools/national_scoring/README.md:61`). Most of that "grass" is Western Slope
  sagebrush, so the eastern plains and the Western Slope look the same to land cover.
- km share with the component at ≥ 0.5 (`tools/national_scoring/results/describe.txt:1-3`):

  | | desert (shrub+bare+moss+snow, 1 km) | grassland |
  |---|---:|---:|
  | New England | 0.0% | 0.3% |
  | Colorado | 2.4% | 38.5% |
  | Utah | 24.0% | 25.5% |

- Grass points the wrong way on every check that sees it. On Colorado's FHWA
  scenic/natural byways, `grass_1k` scores AUC 0.401, and `grassland` 0.434
  (`describe.txt:25,32`). On the New England October marks it scores 0.330
  (verdict §8). That is partly *because* sagebrush and prairie are mixed in one
  class: the good sagebrush country and the dull wheat-and-pasture plains cancel
  out.
- The verdict's within-landscape blind spot: Utah's scenic byways separate at
  0.489 within an ecoregion under E1, which is chance
  (`docs/national-scenery-scoring-verdict.md` §4). Better land cover is one
  candidate fix. Nobody has shown it would help.

**The question:** does a US land-cover source separate sagebrush and other
shrub-steppe from prairie and cropland well enough to (a) fix the desert term in
the West, and (b) say whether *real* grassland, once separated, still points the
wrong way? If it does, does that move the Western checks without moving New
England?

## The mechanism

The desert classes are a fixed WorldCover set. Grassland (30) is left out on purpose:

`pipeline/landcover.py:74`
```python
DESERT_CLASSES = (20, 60, 70, 100)
```

The comment above it (`landcover.py:67-73`) records why grass is excluded:
WorldCover "files most of Colorado's sagebrush under it, so it cannot tell prairie
from the Western Slope."

Desert is the fraction of those classes in a ~1 km ground box (`DESERT_BOX_M = 1000.0`,
`landcover.py:113`), counted at `landcover.py:312-317`. It enters the score through
forest's slot, so it adds no weight:

`pipeline/score.py:621`
```python
chunks["c_forest"] = np.maximum(0.5 * green_flag + 0.5 * tree, desert)
```

So the score can only see Western open land through four WorldCover classes. The
biggest of them in reality, sagebrush steppe, is mostly filed under the one class
the score ignores.

## Candidates to measure (none chosen)

All three are US public-domain products. Check each host with the control-URL
trick before believing a 404: request a deliberately bogus path beside the real
one. `www.mrlc.gov` and `landfire.gov` both currently return 404 for a bogus
path, so they are reachable. My guessed file URLs were wrong, so find the real
ones on their pages.

1. **NLCD.** Annual NLCD land cover, the newest year, 30 m, all 48 states. It has
   separate Shrub/Scrub (52) and Grassland/Herbaceous (71) classes, plus
   Cultivated Crops (82) and Pasture/Hay (81). Use the `www.mrlc.gov/downloads/...`
   path. The `s3-us-west-2.amazonaws.com/mrlc` bucket 403s on everything.
2. **LANDFIRE EVT** (Existing Vegetation Type), 30 m. Its ecological-system
   classes name sagebrush directly. Group them by `EVT_PHYS` / `EVT_NAME` and
   write the grouping down in the verdict.
3. **RCMAP** (MRLC Rangeland Condition Monitoring), fractional cover: sagebrush,
   shrub, herbaceous and bare ground, as percentages per 30 m pixel. It covers
   Western rangelands only. In New England it is zero by construction.

WorldCover, as shipped, is the baseline every candidate is compared against.

## Regions and data: everything has to be rebuilt

**The 2026-10-12 scratch is gone.** The Colorado and Utah builds, `marks.pkl`, the
WorldCover block grids and the PAD-US download lived in session scratchpads under
`/private/tmp`. Only empty directories are left (checked 2026-10-18). Rebuild them
under your own `NS_WORK`, outside the repo:

- **Order:** follow `tools/national_scoring/README.md` (`fetch_inputs.sh`,
  `wc_grids.py`, `build_region.sh` per region, `extract_marks.py`, then the
  measurement scripts).
- **Utah:** use the command in the header of `build_region.sh`. It takes about
  15 minutes.
- **Colorado:** its parameters were never recorded, because it was the
  feasibility review's build. Use Geofabrik's `colorado-latest.osm.pbf`, a bbox
  of about `-109.1,36.95,-102.0,41.05`, and an elevation band of about 1000–4420
  (the lowest point is 1,011 m, the highest 4,401 m). For PAD-US read CO and its
  neighbours. Write the exact command into the verdict and into the header of
  `build_region.sh`.
- **New England:** read the deployed `data/processed-ne` read-only.
- **Where the data is:** `data/` and `traces/` exist only in the main checkout,
  `/Users/james./Desktop/myapps/SundayDrive`. Set `SUNDAYDRIVE_MAIN` to it. The
  `usa` worktree's `data` is a symlink there. **Never write into it.**

## Why it matters

- Under an absolute scale, the West's 7+ share is carried by terrain (`c_grand`,
  relief) and desert. If desert is mis-measured, Colorado's sagebrush country gets
  no land-cover credit while Utah's slickrock does. That is a data defect, not a
  taste call.
- **Whether prairie counts is still undecided, and data has to come before
  taste.** With WorldCover, "grass points the wrong way" can't be read: the class
  is half sagebrush. With a source that separates them, it can.
- **Hypothesis, not finding:** separating sagebrush will lift Colorado's
  within-ecoregion byway AUC and leave Utah's roughly where it is. Utah's open land
  is already mostly in WorldCover's shrub and bare classes (24% desert ≥ 0.5). What
  would kill it: Colorado within-ecoregion S/N not rising above E1's 0.596 by more
  than the noise between candidates (about ±0.01 in the verdict's §5 sweep).

## Traps

1. **NLCD's Shrub/Scrub in New England is cut-over and regenerating forest, not
   desert.** Maine's commercial forest is full of clearcuts. Fed through the
   `max()` in forest's slot, a 1 km box of clearcut would earn desert credit and
   lift timber-haul roads. WorldCover's shrub rounds to 0.000 in New England.
   NLCD's will not. Measure New England movement (km moved > 0.25, marks) for
   every candidate *before* reading the Western numbers. Gating on region
   (rangeland only, via RCMAP's footprint or an ecoregion/state mask) is a
   legitimate fix. Say which one you used, and price its seam.
2. **Don't fit anything to the byway labels.** The verdict's learned candidates
   (D1–D3) won the byway proxy at 0.8+ and failed the marks: D1 put the Mass Pike
   at 9.2. Pick the class grouping from what the classes *are* (sagebrush,
   shrub-steppe, slickrock, alpine), write it down, then measure. If a grouping
   only wins after you try five, report all five.
3. **Compare candidates on the same rebuild, never against the verdict's tables.**
   Today's Geofabrik extract and the `usa` pipeline (E1 is built in) are not what
   the verdict measured on `main` at 0fca74f. First reproduce the WorldCover
   baseline on your builds: the desert and grass shares above, and E1's byway row
   in §4. Report the differences, then compare candidates against *that*.
4. **30 m vs 10 m is not the finding.** NLCD, LANDFIRE and RCMAP are coarser
   than WorldCover. In a ~1 km box (≈ 1,100 pixels at 30 m) that barely matters.
   Don't use the resolution change to explain a difference without measuring it
   (a 3×3-aggregated WorldCover is the control).
5. **Don't change the score's weights or add a grassland term to the pipeline.**
   This unit measures sources and, if one wins by the rule below, swaps the
   desert *input*. The score's structure stays as built. If separated prairie
   turns out to point the right way, that is a finding for the master session
   to take to the owner, not a code change.
6. **The marks file locates the owner's drives to the second.** `marks.pkl` and
   any per-mark table stay in `NS_WORK`, outside the repo. `results/` gets
   aggregates only, as `tools/national_scoring/README.md` already requires.
7. **WorldCover tile indexing:** if you touch `wc_grids.py` or `landcover.py`,
   tiles are named for their *south-west* corner. Use the global-pixel-index
   arithmetic already in `landcover.py`, never `ceil`.

## The decision rule (pre-registered)

A candidate replaces WorldCover as the desert source in `pipeline/landcover.py` on
your branch **only if all of these hold** on your rebuilds:

- New England: ≤ 1.5% of km move by more than 0.25 relative to E1, and the marks'
  October holdout separation within the verdict's paired interval of E1 (no lower
  than E1 − 0.005 on all 151).
- Colorado within-ecoregion FHWA S/N rises by more than 0.01 over the E1
  WorldCover baseline. Utah within-ecoregion doesn't fall by more than 0.01.
- The iconic and agreed-dull roads behave: Trail Ridge, Rim Rock Drive, SR 128 and
  Capitol Reef Scenic Drive don't fall below 7. I-70 east of Denver and US 287 on
  the plains don't rise above 4.
- The class grouping was written down before the measurement.

If none passes, nothing in `pipeline/` changes, and the verdict says so.

## Done looks like

1. `docs/western-landcover-verdict.md` on a branch off `usa`. For each source:
   retrievability (exact URLs, size, licence), the class grouping, the New England
   movement, the byway checks state-wide and within ecoregion, the shares at 7+
   per landscape, and the named roads.
2. A direct answer to: **once sagebrush is separated from prairie, does real
   grassland still point the wrong way?** Give it as numbers on both byway checks
   and the marks, with no recommendation about whether prairie should count.
3. Either the winning source wired into `landcover.py` (with the class map as a
   named constant, the fetch documented, `tests/` covering the class map and the
   New England zero, the suite green), or a statement that no source passed and
   why.
4. Scripts in `tools/national_scoring/` (or a sibling `tools/western_landcover/`),
   results as aggregates in their `results/`, and the Colorado build command
   recorded.
5. Or, honestly: a statement that the available sources can't separate sagebrush
   from prairie at road scale, with the evidence.
