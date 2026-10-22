# New kinds of scenery for a national score

**Status:** diagnosed, not fixed. Written 2026-10-21 by the master session
against `usa` at `de43cb4`. Nothing under `pipeline/`, `server/`, `ios/` or
`data/` has been touched. This is a **study that ends in a priced
recommendation**, like `docs/national-scenery-scoring-verdict.md`. What ships
is the owner's call, and the build is separate. Your answer goes in
**`docs/national-scenery-types-verdict.md`**, never in this brief, which is
deleted in the merge that brings the work back.

## The goal

The score was built in New England, where scenery is mostly forest, water,
hills and curves. The national app covers deserts, canyons, mountains seen
across open ground, the sea, swamps, prairie and farm country. Find which
kinds of scenery the score misses, test candidate components for them, and
recommend which to add. Also propose the set of scenery **types** the app
shows in a route's breakdown.

## Already settled: don't reopen

- **The scale is absolute** (decided 2026-10-18): one meaning of 7 everywhere.
  Per-state and per-ecoregion percentiles are out.
- **E1 is built on `usa`**, as `docs/national-scenery-components.md` describes:
  - `c_grand`, the 3 km elevation range above 300 m;
  - desert, rock and alpine land cover, entering the forest slot through
    `max()`;
  - `c_protected`, PAD-US landmarks.
- **Learned systems fail.** Systems learned from byway labels (verdict
  D1–D3) won the proxy and failed the marks: D1 scored the Mass Pike 9.2.
- **Grassland, as WorldCover measures it, points the wrong way** (verdict §8).
  WorldCover calls most of Colorado's sagebrush "grass".
- **Western land cover:** no better source than WorldCover passed
  (`docs/western-landcover-verdict.md`).

## As measured: where the score falls short (2026-10-21, `data/processed-us`)

Each figure is the length-weighted mean of `weight × c_*` from
`graph_edges.parquet`'s stored components, using `pipeline/score.py:60-72`'s
`WEIGHTS`. **These are crude.** Roads were matched by a substring of `name`
or `ref`, so "SR 128" sweeps in other states' SR 128s and the Tamiami Trail
includes urban US 41. Re-pin every road to way IDs before you rely on it
(trap 3).

| road | km | score | km ≥ 7 | main contributions (of each weight) |
|---|---:|---:|---:|---|
| US 163, Monument Valley | 104 | 5.24 | 4% | forest/desert 0.176, relief 0.065 (of 0.16), curves 0.014, **grand 0.000**, protected 0.005 |
| Valley of Fire | 38 | 5.90 | 21% | forest/desert 0.176, relief 0.085, curves 0.041, protected 0.033, grand 0.007 |
| Overseas Highway (US 1, Keys) | 212 | 5.60 | 17% | coast 0.129 (full), **water 0.059 (of 0.22)**, forest 0.081, adj −0.097 |
| Tamiami Trail (substring) | 579 | 4.92 | 9% | water 0.079, forest 0.051, urban 0.090 |
| Going-to-the-Sun | 82 | 9.58 | 97% | everything, including grand 0.070 and protected 0.069 |
| Kancamagus (New England control) | 57 | 8.84 | 97% | water 0.152, forest 0.167, relief 0.117 |
| Big Bend, Ross Maxwell Drive | 50 | 8.06 | 86% | forest/desert 0.163, relief 0.106, water 0.082, protected 0.070 |

Outside review #3 (2026-10-20, M-02) found the same pattern: Monument Valley's
US 163 has 3% of km at 7 or more, Valley of Fire 9%, and Big Bend 0.4 of 68 mi
on its approach roads.

## The mechanism

1. **Every term looks within 3 km of the road. Most look within 1 km.**
   - `DIST` (`score.py:50-58`): water 120 m, coast 800 m, green 80 m, views
     400 m.
   - Relief is the elevation range in a 750 m window
     (`pipeline/elevation.py:46`, `RELIEF_WINDOW_M = 750.0`), saturating at
     100 m (`score.py:99`, `RELIEF_FULL`).
   - `c_grand` is the 3 km range, counted from 300 m and full at 900 m
     (`score.py:107-108`).

   Monument Valley's buttes stand about 300 m above a flat floor, mostly
   more than 1–3 km from the road. The road sees them and the score does not:
   `grand` is 0.000. **Hypothesis:** the West's signature scenery is what is
   visible at a distance across open ground. That is invisible in forested
   New England, so nothing was built for it. **Evidence:** US 163's zero
   `grand`, and its relief at 40% of the weight. **What would kill it:** an
   open-land "visible prominence within 5–15 km" term that doesn't lift US 163
   above the dull desert controls (below).
2. **A straight, dry road can barely reach 7.**
   - The formula is `score = 10 * ((raw + RAW_BASE) * STRETCH + score_adj)`
     with `RAW_BASE = 0.143` and `STRETCH = 1.20` (`score.py:73-83`). So 7
     needs `raw ≥ 0.44`.
   - With no water and no curves, the most available is forest/desert 0.18 +
     relief 0.16 + grand 0.10 + protected 0.07 + scenic_tag 0.07 + views 0.05
     = 0.63. That means collecting almost everything at once.
   - In New England, water (0.22) and curves (0.13) are what carry roads over
     the line.
3. **The open sea counts as coast, not water.** `c_water` is proximity to
   OSM water polygons (`score.py:633`). `c_coast` is proximity to the
   coastline line (`score.py:634`), full at 800 m. The Keys get full coast and
   only 27% of the water weight, though the road runs on the sea.
   **Hypothesis:** the ocean isn't a water polygon. Check whether the 0.059 is
   from lakes and bays only.
4. **Wetland and mangrove are unread.** WorldCover has herbaceous wetland
   (class 90) and mangroves (95). The desert term reads shrub, bare, moss and
   snow (`score.py:650-656`), and the forest term reads tree cover.
5. **The breakdown types are New England's.** `BEAUTY_TYPES`
   (`pipeline/router.py:266-273`) is water, coast, "forest/park", hills,
   farmland and town. Their mirror is `ios/Sources/Models.swift`. On a desert
   road the desert credit shows as "forest/park"
   (`national-scenery-components.md` §6). `grand` and `protected` are not user
   types at all.

## The candidates to test (hand-set, never fitted)

Test each alone and in sensible combinations, on the same footing as
`tools/national_scoring/` (reuse `core.py`, `candidates.py`, `eval_all.py`,
`marks_ci.py` and `prep_region.py`):

- **V. Distant visible relief:** prominence above the road within about 5, 10
  and 15 km, credited only where the land cover around the road is open
  (shrub, bare, grass, crop or water within ~1 km), so a forest road gets no
  credit for mountains it can't see. A true viewshed if it's affordable, or a
  prominence proxy if not. State which, and what it costs on the national
  raster.
- **S. The sea as water:** ocean within water distance counts toward
  `c_water`, or coast's weight is reconsidered for roads *on* the sea, such
  as bridges and causeways.
- **W. Wetland and mangrove:** WorldCover 90 and 95 in the forest slot via
  `max()`, like desert. Or into water. Test both.
- **R. Rock texture:** small-scale relief (about a 250 m window) where the
  land is bare. This is for Valley of Fire, the Badlands and slickrock.
- **P. Prairie and pastoral, priced only:** rolling open grass and crop with
  relief, for the Flint Hills, the Sandhills and the Palouse. The verdict says
  this data can't find good prairie. Confirm or refute it on the icon list;
  don't recommend it on taste.
- **C. The composite:** whether the West's ceiling (mechanism 2) is better
  fixed by letting the landscape families (forest, desert/rock, wetland,
  distant relief) combine by `max()` into one slot. The alternative is adding
  more terms. Price both.

One candidate of your own is allowed if the icon breakdown shows a gap that
none of these covers. Justify it before measuring it.

## How a candidate passes

All three must hold:

1. **New England is unharmed.**
   - The marks are measured with `analyze_trace.py`'s attribution, as the
     verdict did: 0.719 over 151, and 0.766 on the Oct holdout.
   - The paired 90% interval on the holdout must not fall below −0.005.
   - No more than 3% of New England's km may move by more than 0.25.
2. **The pre-registered icons rise and the dull controls don't.**
   - **The lists below were written before any candidate was measured. Don't
     edit them after you see a score.** Pin each road to way IDs or an OSM
     relation, bounded to the named stretch, and commit that pinning
     *before* computing a candidate.
   - Report the km ≥ 7 for icons and for controls under S0 (shipped E1) and
     under each candidate.
   - A candidate passes if it raises the icons' share of km at 7 or more and
     leaves every dull control's mean below 4, with no more than 2% of
     control km at 7 or more.
3. **The national byway proxy within ecoregion is not worse** (verdict §1,
   FHWA scenic/natural).

**Icons** (named stretch):
- US 163 through Monument Valley (UT/AZ)
- Valley of Fire Highway (NV)
- the Overseas Highway, US 1, Key Largo to Key West (FL)
- US 41 Tamiami Trail through Big Cypress (FL)
- Badlands Loop Road, SD 240 (SD)
- Needles Highway, SD 87 (SD)
- Million Dollar Highway, US 550 Ouray–Silverton (CO)
- UT 12 (UT)
- UT 128 along the Colorado River (UT)
- Zion–Mount Carmel Highway, UT 9 (UT)
- CA 190 through Death Valley (CA)
- CA 1 through Big Sur (CA)
- Tioga Road, CA 120 (CA)
- Historic Columbia River Highway (OR)
- Chuckanut Drive (WA)
- Beartooth Highway, US 212 (MT/WY)
- Blue Ridge Parkway (NC/VA)
- Skyline Drive (VA)
- Cherohala Skyway (NC/TN)
- Natchez Trace Parkway (MS/TN)
- NC 12 on the Outer Banks (NC)
- the Texas Hill Country's RR 335, 336 and 337 (TX)
- the Flint Hills Scenic Byway, K-177 (KS), for prairie
- the Sandhills Journey, NE 2 (NE), for prairie
- the Palouse Scenic Byway (WA), for pastoral

**Dull controls:**
- I-15 from Barstow to Primm (CA/NV)
- I-10 from Tonopah to Quartzsite (AZ)
- US 6 from Delta to Eureka (UT)
- I-40 through Amarillo (TX)
- I-80 from Grand Island to North Platte (NE)
- I-70 east of Denver (CO)
- US 287 on the Colorado plains
- I-75 from Ocala to Tampa (FL)
- I-4 through Orlando (FL)
- Bell Road in Phoenix (AZ)
- Westheimer Road in Houston (TX)
- I-95 on the New Jersey Turnpike
- I-635 LBJ Freeway in Dallas (TX)

The desert interstates are there on purpose: a desert or distant-relief term
that makes I-15 beautiful has failed.

## Also deliver: the app's scenery types

Propose the breakdown set that replaces `BEAUTY_TYPES`'s six. For example:
forest, desert and rock, mountains, water, coast, wetland, farmland and town.
Give each one's mapping to components, which ones stay user-tunable, and what
the change touches: `router.py` `BEAUTY_TYPES` and `DEFAULT_WEIGHTS`,
`Models.swift`, the slider renormalisation in `Router._edge_scores`, and the
API's breakdown field. Propose it only; don't build it.

## Traps

1. **Never fit a constant**, whether to marks, icons or byways. Hand-set each
   weight by analogy with an existing one, then sweep it to show it isn't a
   knife-edge (verdict §5 did this for `grand` and `protected`). A system
   tuned to win the icon list is D1 again.
2. **Don't touch `pipeline/` or the live data.** Chip `task_b97d53c1` is
   editing `pipeline/common.py`, `closures.py`, `winter_closures.py` and
   `federal_layers.py`, and building `data/processed-us-next` /
   `data/pack-us-next`. Chip `task_6008122e` is reading the pack. Compute
   candidates offline, on region slices, in `tools/scenery_types/`, as
   `tools/national_scoring/` did. Never write `data/processed-us` or
   `data/pack-us`.
3. **Pin the roads; don't match names.** The table above used substrings and
   is contaminated. A wrong stretch (urban US 41, another state's SR 128)
   moves the result more than any candidate does.
4. **New England's bare land is quarries and gravel pits** (marks AUC 0.271,
   verdict §8). Its wetlands are roadside marsh and swamp. A rock or wetland
   term has to stay harmless there. That's why desert enters through `max()`
   with forest. Check it on the marks, not by inspection.
5. **Western Terrarium has in-band spikes** (`national-scenery-components.md`
   §2). A distant-prominence term over a 10 km window will find every spike.
   Despike first, with the same method.
6. **Raising `RELIEF_FULL` is not the fix.** It was measured and rejected
   because it costs New England (`score.py:102-106`).
7. **Absolute scale.** Don't propose a regional rescaling as a candidate.
8. **The default `data/processed` is an August MA-only build.** Set
   `SUNDAYDRIVE_DATA` explicitly.
9. **The marks are the owner's drives.** Commit aggregates only. Never commit
   new per-mark coordinates or trace-derived points: the repo is public.

## Done looks like

1. `docs/national-scenery-types-verdict.md` containing:
   - the pinned icon and control table under S0, with per-component
     breakdowns;
   - each candidate's three pass checks;
   - the sweeps;
   - the build cost, in national rebuild time and raster size;
   - **a ranked recommendation**;
   - the proposed app types;
   - what the Western marks would need to test, if the owner ever got them.
2. `tools/scenery_types/` with the scripts and result CSVs, rerunnable, and
   the pinned road list committed before the candidate results.
3. No change under `pipeline/`, `server/`, `ios/` or `data/`.
4. This brief committed with the work, with nothing appended to it.
5. An honest escape hatch: if no candidate passes all three checks, say so,
   and say which check failed and on which roads. "Ship nothing new" is an
   acceptable answer.
