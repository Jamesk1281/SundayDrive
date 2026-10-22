# The scenery additions V, S2 and L, built into the pipeline

**Status:** built, reproduced and rebuilt nationally on 2026-10-22, on
`claude/scenery-additions` (off `usa` at `37bc5c1`). The national data is in
`data/processed-us-next` and `data/pack-us-next`, and `data/pack-us-next.done` is written.
The swap into `processed-us` and `pack-us` is the master session's. Nothing under
`data/processed-us`, `data/pack-us` or `data/processed-ne` was written.

[`docs/national-scenery-types-verdict.md`](national-scenery-types-verdict.md) measured three
terms offline in `tools/scenery_types/` and recommended shipping them together, and the
owner approved that. This document records how they were built and whether the build
reproduces what was measured. It does.

## The verdict

**The pipeline reproduces the study. No constant moved.**

- **New England** (scratch copy of the deployed build, §3):
  - marks: all 151 at 0.720 (study 0.721) and the Oct holdout at 0.780 (study 0.780). The
    paired 90% interval is −0.003 to +0.017, as in the study;
  - 2.49% of km move by more than 0.25 (study 2.52%; the limit is 3%);
  - 56 marks score 7 or more, as in the study.
- **Utah** (scratch copy of the study's own Utah build, §4): 12.26% of km at 7 or more
  (study 12.28%), mean 4.761 (4.763), and the byway proxy within ecoregion 0.4980 (0.4973).
- **Nationally** (§6): the share of km at 7 or more goes from 4.89% to 5.28%. Utah,
  Nevada and Arizona gain the most (+3.4, +3.3 and +2.5 points); the plains do not move.
  Icon km at 7 or more go from 37.6% to 41.6%, and control km stay at 0.04%. The graph, the
  closures and the routes are unchanged: 11,414 of 11,414 continuity legs pass, and
  `tests/test_national_routes.py` passes 11 of 11.
- **Death Valley's CA 190 reaches 77.6% of km at 7 or more, not the study's 96%.** The
  study's 96% was an artefact of its piece method, and the build is right (§6).
- **The one residual is V's open-land box.** The 10 km prominence is identical to the
  study's on every chunk. The pipeline counts open land in `landcover.py`'s own ~1 km
  ground box, which the brief named. The study counted it in 9 × 11 aligned blocks of
  ~100 m. The two differ by more than 0.05 in V on 0.034% of New England's km. That is the
  whole of the 0.0003 on all marks, the 0.001 on the holdout and the 0.03 points of km
  moved.

## 1. What was built

The three terms each change an existing column by `max()`:

- V goes into `c_grand`;
- S2 goes into `c_water`;
- L goes into `c_protected`.

So no column is added, and `graph_edges.parquet`'s schema, `BEAUTY_TYPES`, the sliders and
the pack format are unchanged. The definitions are the study's
(`tools/scenery_types/cands.py:55-101`), and the tests hold the pipeline to them (§2).

| term | stage | what changed |
|---|---|---|
| V | `terrain.py` | writes `prom10k.tif`: the highest despiked elevation within a 10 km half-side square (`PROM_HALF_SIDE_M`, windows sized at `RELIEF_REF_LAT`), minus the pixel's own. It is computed on the same despiked, sea-clipped mosaic as `range3k.tif`, before it, and freed first, so the two are never held at once. `range3k.tif` is written last, so its presence, which `tools/national_build/build.py` checks, means both are done. |
| V, S2 | `landcover.py` | the ~1 km box (`DESERT_BOX_M`) also writes `tree_1k`, `water_1k` (class 80) and `mangrove_1k` (class 95), beside `desert` and `built`. A box reaching a cell WorldCover omits counts those pixels as water. `tree`, the 100 m share, is unchanged. |
| L | `protected.py` | also writes `landmark_near`: within `DIST["green"]` (80 m) of a landmark polygon, by `dwithin` in `common.CRS_METERS`, which `stage.py` sets per region. `landmark`, the inside flag, is kept. |
| all | `score.py` | V: `c_grand = max(c_grand, open × clip((prom10k − GRAND_START) / (GRAND_FULL − GRAND_START)))`, with open = 1 − tree_1k − built − mangrove_1k, clipped. S2: `c_water = max(c_water, sea)`, where sea is 1 within `DIST["water"]` (120 m) of the coastline, `WATER_MID` (0.45) within `DIST["water_mid"]` (350 m), from the chunk midpoint, and only where `water_1k ≥ ON_SEA_WATER_SHARE` (0.5). L: `c_protected` credits `max(landmark, landmark_near)` behind the same `PROTECTED_BUILT_MAX` gate. |

**Old files score as E1.** Each input degrades as the national components did: no
`prom10k.tif`, no ~1 km shares in `tree_cover.parquet`, or no `landmark_near` column, and
that term scores nothing and prints a NOTE. The E1 copies in §3 and §4 are built that way,
and they reproduce E1 exactly.

**Choices the brief left open:**

- **S2 is measured from the chunk midpoint,** with two more queries on the coastline tree
  `score.py` already builds. The study measured from the midpoint, and the ~1 km box is
  sampled there too. `c_water`'s own queries use the whole chunk.
- **The constant 0.45** was a literal in `c_water`. It is now `WATER_MID`, which S2
  shares, so S2 uses water's curve by construction. The value is unchanged.

### `landcover.py`'s memory went down, not up

Before this change, the ~1 km box counted desert with `np.isin` and built-up land with
`==`. Measured on numpy 2.2, `np.isin` holds about 10.5 times the window (an int64
temporary). On a tile read corner to corner (1.3 GB) that is about 14 GB. It is why E1's
Utah landcover stage peaked at 10.03 GB in the national build.

The box now maps each pixel to one small code with a 256-entry lookup (`BOX_CODES`) and
bincounts each box. That is one uint8 copy of the window, however many shares are written.
Measured on a 36 MB window, the old way peaked at 381 MB and the new one at 36 MB. `tree`,
`desert` and `built` are unchanged: `tests/test_scenery_additions.py` checks every share
against a direct count, and New England's `tree` is bit-identical to the deployed file.

## 2. Tests

The tests are in `tests/test_scenery_additions.py` (30 tests, synthetic data only):

- **Each term against the study's code on the same inputs:** `score.vista` against
  `cands.vista` and `score.sea_as_water` against `cands.sea(on_sea=True)`, on 2,000 random
  rows each. The prominence window must equal `feat_lib.dem_features`'s.
- **Behaviour:**
  - the 10 km window sees a mountain 8 km off;
  - the prominence is despiked first, and the sea floor is clipped;
  - trees, built land and mangrove hide the view;
  - a shore road is dry, and a road on the sea is wet;
  - a road 50 m outside a park is next to it, and one 150 m outside is not;
  - multiple-use land is still not a landmark;
  - the ~1 km shares partition the box.
- **In a build:**
  - each term takes its slot by `max()`;
  - L keeps the 30% built gate;
  - no column is added;
  - a build without the new inputs is E1, column for column.
- **Each constant pinned, with a test that moves it and watches a behaviour break.** As a
  check on the checks, each constant was also changed in the source and the file run:

  | constant | moved to | tests failing |
  |---|---|---:|
  | `ON_SEA_WATER_SHARE` | 0.5 → 0.65 | 3 |
  | `GRAND_START` | 300 → 450 | 3 |
  | `PROM_HALF_SIDE_M` | 10 → 15 km | 2 |
  | `DIST["green"]` | 80 → 200 m | 2 |
  | `WATER_MID` | 0.45 → 1.0 | 2 |

The full suite on `processed-ne`: 1,248 passed, 24 skipped (2026-10-22).

## 3. New England: a scratch copy of the deployed build

This is the method of [`docs/national-scenery-components.md`](national-scenery-components.md)
§4.

1. **The copy.** `data/processed-ne`'s layers, `elevation.tif` and `relief.tif` were cloned
   (APFS copy-on-write) into a scratch directory outside the repo. The national
   WorldCover cache was linked in.
2. **The new stages.** `terrain.py`, `landcover.py` and `protected.py` (with
   `data/national/inputs/padus_landmarks.parquet`) were run on it.
3. **Two scorings.** `score.py` scored it twice:
   - once with the three new inputs removed, which is E1;
   - once with them, which is V+S2+L.
4. **The comparison.** `tools/scenery_additions/check.py` compares both against the
   study's New England chunk table, chunk by chunk, after asserting that they hold the
   same 942,448 chunks. Edge scores come from the study's own chunk → edge map (graph.py's
   averaging), the marks from `tools/national_scoring`'s marks table, and the interval from
   the study's paired drive-cluster bootstrap (4,000 resamples, the same seed).

The single-term rows are E1's raw score plus that term's column change. That is exact,
because each term touches one column only.

| | E1 pipeline | E1 study | V | S2 | L | **V+S2+L pipeline** | **V+S2+L study** |
|---|---:|---:|---:|---:|---:|---:|---:|
| marks, all 151 | 0.7211 | 0.7211 | 0.7202 | 0.7211 | 0.7211 | **0.7204** | 0.7207 |
| marks, Oct holdout | 0.7726 | 0.7726 | 0.7736 | 0.7726 | 0.7776 | **0.7795** | 0.7805 |
| Oct paired 90% interval vs E1 | — | — | −0.003 to +0.005 | 0 | +0.000 to +0.011 | **−0.003 to +0.017** | −0.003 to +0.017 |
| marks at 7 or more (liked) | 53 (96.2%) | 53 | 54 | 53 | 55 | **56 (94.6%)** | 56 |
| marks moved by more than 0.25 | — | — | 3 | 0 | 5 | **8** | 8 |
| km moved by more than 0.25 | — | — | 1.81% | 0.24% | 0.45% | **2.49%** | 2.52% |
| km at 7 or more | 13.37% | 13.37% | 13.66% | 13.53% | 13.46% | **13.90%** | 13.89% |
| mean | 4.897 | 4.897 | 4.916 | 4.902 | 4.901 | **4.925** | 4.925 |

The verdict's single-term rows are V 1.85% / S2 0.23% / L 0.45% of km moved, with Oct
0.775 / 0.773 / 0.778. They match to the third decimal, except V's km moved (1.81% against
1.85%), which is the box difference below.

**The components, pipeline against study, on the V+S2+L build:**

| column | km differing by more than 0.05 | mean | nonzero km |
|---|---:|---|---|
| `c_grand` | 0.033% | 0.0221 / 0.0222 | 26.97% / 26.96% |
| `c_water` | 0.051% | 0.2345 / 0.2345 | 32.81% / 32.80% |
| `c_protected` | 0.007% | 0.0082 / 0.0082 | 0.82% / 0.82% |

On the E1 build, every other component differs on 0.000% of km by more than 0.05
(`c_forest` at most 0.047, the desert box).

**Where the residual comes from.** The pipeline's and the study's inputs were swapped one
at a time:

- the prominence alone differs from the study's on no chunk: the same 4 holes, and a
  p99 difference of 0 m;
- with the pipeline's prominence and the study's open-land box, V equals the study's on
  every chunk;
- with the study's prominence and the pipeline's box, V differs by more than 0.05 on 0.034%
  of km, and at most by 0.09. That is the whole residual.

The two boxes differ in shape and alignment:

- **the pipeline's** (`landcover.window_px` at 1,000 m) is 109 × 145 pixels at 42°N, about
  1,010 × 1,000 m, centred on the point's pixel;
- **the study's** (`feat_lib.wc_features`) is 9 × 11 blocks of 12 × 12 pixels, about
  1,000 × 910 m at 42°N, centred on the point's block.

Their shares agree to a p99 difference of 0.05 for tree, water and built. S2's cut at 0.5
water gives the same answer on 99.8% of chunks. S2's own residual (0.051% of km) is that
cut plus the coastline distance (the region's `CRS_METERS` against the study's EPSG:5070).
L's residual (0.007%) is the same CRS difference at 80 m.

The brief names `landcover.py`'s box ("the same box `landcover.py` already uses for its
desert and built shares"). That box is also where E1's built-land gate comes from, so the
study's box was not added beside it. The residual moves no mark across 7 and is a tenth of
the holdout interval's width.

## 4. Utah: the study's own Utah build, rescored

The study's Utah chunk table came from a pipeline build of Utah
(`tools/national_scoring/build_region.sh`, 2026-10-18), run without `stage.py`, so in the
default `CRS_METERS`. That build's layers were cloned and run through the same stages, also
in the default CRS, so its 283,587 chunks match the study's one for one. The two scorings
and `check.py` are as in §3. Here the byway proxy replaces the marks: FHWA scenic or
natural on trunk to tertiary, within EPA level-3 ecoregion, with the byway term removed.

| | E1 pipeline | E1 study | V | L | **V+S2+L pipeline** | **V+S2+L study** |
|---|---:|---:|---:|---:|---:|---:|
| km at 7 or more | 8.98% | 8.98% | 11.98% | 9.24% | **12.26%** | 12.28% |
| mean | 4.326 | 4.326 | 4.751 | 4.337 | **4.761** | 4.763 |
| km moved by more than 0.25 | — | — | 53.4% | 1.29% | **53.9%** | 54.0% |
| byway proxy within ecoregion | 0.4886 | 0.4887 | 0.4982 | 0.4885 | **0.4980** | 0.4973 |

The study's figures are its `results/distributions.csv` (ut, V+S2+L: 12.282%, 4.763) and
`results/byway_proxy.csv` (0.4973). S2 does nothing in Utah, which has no coastline.

`c_grand` differs from the study's by more than 0.05 on 0.43% of Utah's km. That is the
same box difference: V is nonzero on 89% of Utah's km, against 27% of New England's. Landmark
credit covers 2.77% of chunks inside a polygon and 3.81% within 80 m.

V moves more than half of Utah's km by more than 0.25. That is what V is for: open land
under distant relief is most of Utah. It is not a New England risk, and New England is the
check that has marks.

## 5. Cost

Measured stage by stage on the two scratch copies (`/usr/bin/time -l`):

| stage | New England wall / peak | Utah wall / peak | E1 in the national build (Utah) |
|---|---|---|---|
| terrain | 145 s / 4.59 GB | 60 s / 2.33 GB | 52 s / 2.44 GB |
| landcover (cached tiles) | 172 s / 5.96 GB | 39 s / 4.59 GB | 75 s / 10.03 GB |
| protected | 538 s / 2.97 GB | 29 s / 2.85 GB | 31 s / 3.03 GB |
| score, V+S2+L | 98 s / 3.29 GB | 35 s / 1.17 GB | 53 s / 1.42 GB |

The national build ran New England as six states, so its New England figures are not
comparable. Notes on the measurements:

- **New England's terrain peak is the existing despike,** about eight copies of a 555 MB
  mosaic. The prominence holds three, and added about 40 s.
- **New England's landcover peak is the 942,448-chunk frame** and its per-tile box tables,
  not the raster.
- **New England's `protected.py` wall time was the machine stalling,** during chunking:
  72 s of CPU in 538 s. The 80 m query itself took 8 s.

### The national rebuild

The run was the master session's go-ahead, at 02:27–08:40 on 2026-10-22, alone on the
Mac. It took these steps:

1. The 51 regions into a fresh `data/national/build-next` (its `raw/` a link to
   `data/national/build/raw`, so no tile was fetched), at `--jobs 2`.
2. `stitch.py`, then `sidecars.py` with `SUNDAYDRIVE_FEDERAL=data/raw/federal`.
3. `tools/national_audit/pack_next.py` against `data/pack-us`, which writes as clones the
   arrays that did not change.

| step | wall | peak |
|---|---|---|
| regions, 51 | 4 h 50 min; 9.54 process-hours (E1: 10.71) | 11.46 GB (east Texas, graph) |
| stitch | 1,718 s | 11.76 GB |
| sidecars | 2,951 s | 7.59 GB |
| pack | 245 s | 14.15 GB |
| continuity check | 283 s | 11.65 GB |

Per stage over all regions, against E1's build:

- landcover: 1.00 process-hours (E1 1.52), peak 8.58 GB (E1 10.82 GB, South Dakota);
- terrain: 0.92 process-hours (E1 0.77), peak 5.83 GB (E1 5.25). Montana's terrain stage
  went from 3.82 GB to 5.83 GB, which is the prominence array the verdict predicted.

Disk used: `build-next` 10 GB, `processed-us-next` 11 GB, and the pack's 5 new arrays. The
volume went from 53 GB free to 27 GB.

## 6. The national data

**Only the scores changed:**

- **The graph:** `processed-us-next` has the same 25,849,861 edges and 20,023,955 nodes as
  `processed-us`. `per_region.csv` is byte-identical.
- **The border proof holds.** 0 of 2,159,473 ways that two regions both built are split
  differently. Copies of an edge built on both sides of a border differ by more than 0.25
  on 1.34% of edges, up from 1.29%: the same projection and ring-edge noise, now on three
  more columns.
- **The sidecars** are row for row the six decisions' (`closed_to_cars` 70,830,
  `seasonal_closures` 13,588, `osm_unpaved` 19,237, `state_road_class` 49,697).
- **The pack** has 20,186,991 routing nodes, as `pack-us`. It wrote 5 arrays new, all
  scores: `_score`, `base_score`, `_breakdown`, and `comp.0` (water's slider column;
  `c_grand` and `c_protected` are baseline terms with no slider). The other 87 were
  cloned from `pack-us`.
- **The routes:**
  - `continuity.py check data/processed-us-next data/pack-us-next`: 11,414 of 11,414
    legs pass;
  - `SUNDAYDRIVE_PACK=data/pack-us-next pytest tests/test_national_routes.py`: 11 passed.

**Share of km at 7 or more, per state,** before (`processed-us`, E1) and after
(`processed-us-next`). From `tools/scenery_additions/national.py`; the full table is
`results/national_states.csv`.

| state | km ≥ 7 before | after | change | mean before | after |
|---|---:|---:|---:|---:|---:|
| **US** | 4.89% | 5.28% | +0.39 | 3.63 | 3.68 |
| UT | 8.43% | 11.83% | +3.40 | 4.34 | 4.78 |
| NV | 2.83% | 6.17% | +3.33 | 3.95 | 4.59 |
| AZ | 3.56% | 6.08% | +2.52 | 3.92 | 4.23 |
| CO | 8.32% | 9.98% | +1.66 | 3.85 | 4.02 |
| ID | 15.55% | 16.92% | +1.36 | 4.40 | 4.66 |
| VT | 20.04% | 21.32% | +1.29 | 5.53 | 5.62 |
| CA | 9.90% | 11.18% | +1.27 | 4.05 | 4.23 |
| OR | 19.98% | 21.21% | +1.23 | 5.01 | 5.17 |
| WY | 3.29% | 4.42% | +1.14 | 3.42 | 3.59 |
| WA | 16.88% | 18.01% | +1.14 | 4.71 | 4.82 |
| MT | 9.07% | 10.06% | +0.98 | 3.58 | 3.77 |
| NM | 3.14% | 3.94% | +0.80 | 3.53 | 3.71 |
| NH | 15.52% | 16.28% | +0.76 | 5.25 | 5.30 |
| WV | 34.43% | 34.96% | +0.53 | 6.47 | 6.50 |
| VA | 8.07% | 8.56% | +0.49 | 4.41 | 4.46 |
| ME | 8.66% | 9.15% | +0.49 | 4.61 | 4.63 |
| RI | 15.13% | 15.50% | +0.37 | 5.16 | 5.17 |
| MA | 10.51% | 10.88% | +0.37 | 4.72 | 4.73 |
| TN | 5.73% | 6.00% | +0.27 | 4.20 | 4.23 |
| NY | 7.70% | 7.94% | +0.25 | 4.22 | 4.24 |
| NC | 5.16% | 5.39% | +0.23 | 3.87 | 3.89 |
| DE | 5.92% | 6.15% | +0.23 | 4.12 | 4.13 |
| FL | 3.94% | 4.16% | +0.22 | 4.09 | 4.10 |
| NJ | 9.16% | 9.37% | +0.21 | 4.53 | 4.54 |
| CT | 10.89% | 11.09% | +0.20 | 4.78 | 4.79 |
| PA | 9.53% | 9.71% | +0.18 | 4.69 | 4.71 |
| MD | 9.84% | 10.00% | +0.17 | 4.61 | 4.62 |
| AR | 2.07% | 2.16% | +0.09 | 3.55 | 3.56 |
| TX | 0.98% | 1.06% | +0.08 | 3.01 | 3.02 |
| GA | 2.34% | 2.40% | +0.07 | 3.72 | 3.73 |
| KY | 6.03% | 6.08% | +0.05 | 4.12 | 4.12 |
| WI | 3.63% | 3.67% | +0.05 | 3.69 | 3.69 |
| OH | 4.13% | 4.17% | +0.04 | 3.69 | 3.69 |
| SC | 2.45% | 2.49% | +0.04 | 3.73 | 3.74 |
| SD | 0.56% | 0.59% | +0.03 | 2.39 | 2.40 |
| AL | 2.82% | 2.85% | +0.03 | 3.96 | 3.96 |
| MO | 2.42% | 2.45% | +0.03 | 3.46 | 3.47 |
| MN | 1.89% | 1.91% | +0.02 | 3.03 | 3.03 |
| MI | 2.21% | 2.23% | +0.02 | 3.31 | 3.32 |
| IA | 0.72% | 0.74% | +0.01 | 2.49 | 2.49 |
| IL | 1.06% | 1.07% | +0.01 | 2.84 | 2.84 |
| OK | 0.57% | 0.58% | +0.01 | 2.62 | 2.63 |
| IN | 1.69% | 1.70% | +0.01 | 3.02 | 3.02 |
| LA | 0.72% | 0.72% | +0.01 | 3.21 | 3.21 |
| MS | 0.65% | 0.65% | +0.01 | 3.37 | 3.37 |
| KS | 0.39% | 0.39% | +0.00 | 2.39 | 2.39 |
| ND | 0.15% | 0.15% | +0.00 | 2.30 | 2.30 |
| NE | 0.32% | 0.32% | +0.00 | 2.64 | 2.64 |
| DC | 4.10% | 4.10% | +0.00 | 3.59 | 3.59 |

The West gains where V has open land under mountains. The coasts gain a little from S2 and
L. The plains and the Midwest move by hundredths. New England moves by +0.2 to +1.3 points:
Vermont gains most, from V on its valley roads, which is the verdict's §4 mover list.

**The pinned icons and controls on the real build** (`results/national_icons.csv`),
against the study's V+S2+L prediction (`tools/scenery_types/results/icons.csv`):

| | E1 | built | study |
|---|---:|---:|---:|
| icon km at 7 or more | 37.59% | **41.64%** | 42.4% |
| control km at 7 or more | 0.04% | **0.04%** | 0.04% |
| worst control mean | 3.52 (Bell Road) | **3.67 (US 6 Delta–Eureka)** | 3.66 (US 6) |

Of the 38 pinned roads, 33 come out exactly as the study predicted, to 0.01 points. The
largest differences:

| road | E1 | built | study | why |
|---|---:|---:|---:|---|
| CA 190 Death Valley | 33.6% | **77.6%** | 96.3% | below |
| Overseas Highway | 15.6% | **38.5%** | 40.0% | the same artefact, smaller |
| NC 12 Outer Banks | 52.8% | **59.0%** | 58.4% | S2's box and coast distance |
| UT 12 | 37.2% | **47.4%** | 47.2% | V's box |
| Valley of Fire | 21.8% | **36.4%** | 36.4% | |
| US 163 Monument Valley | 4.6% | **9.4%** | 9.4% | |
| Tamiami Trail, Big Cypress | 4.3% (mean 3.92) | **6.1% (mean 4.69)** | 6.1% (4.68) | |

**CA 190 is the study's error, not the build's.** One 29.2 km edge east of Furnace Creek
holds 18.6% of the road's pinned km. It scores 6.935 in the build and 7.006 in the study.
The study cut pinned edges into 400 m pieces but knew the shipped components only as edge
averages, and applied each candidate's `max()` piece by piece (verdict §10). The edge's
averaged `c_protected` is 0.092, and 12.3% of its pieces are within 80 m of the park. So
the study gave every piece max(0.092, its own flag), counting the inside stretches twice.
The pipeline takes the `max()` chunk by chunk, before the edge average, which is the
definition. The road's mean is the same (7.65 built, 7.66 study): 30 km of it sits between
6.9 and 7.0.

## 7. Open

- **The swap is the master session's:** `processed-us-next` → `processed-us` and
  `pack-us-next` → `pack-us`.
- `data/national/build-next` (10 GB) holds the new region parts. It is the input for any
  re-stitch of this build, and `data/national/build` holds E1's. Which to keep after the
  swap is the master session's call.
- `tools/scenery_types` and `tools/scenery_additions/check.py` read the study's chunk tables
  and marks under `SundayDrive-scratch/western-landcover`. They still resolve; deleting
  `reg/`, `ut/`, `co/` or `marks.pkl` there would stop either check from being re-run.

Figures derived from OpenStreetMap are © OpenStreetMap contributors, ODbL. ESA WorldCover
2021 is CC BY 4.0. PAD-US is US federal data. The marks are the owner's, and only
aggregates appear here.
