# The scenery additions V, S2 and L, built into the pipeline

**Status:** built and reproduced 2026-10-22 on `claude/scenery-additions`, off `usa` at
`37bc5c1`. The code, its tests and the two scratch reproductions are done. The national
rebuild into `data/processed-us-next` and `data/pack-us-next` is **not** done: it waits on
the master session's go-ahead (§5). No file under `data/` was written.

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

## 5. Cost, and what the national rebuild needs

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

**The national rebuild is not run.** It is the national build's region stages for every
region, about 10.7 process-hours (verdict §7). Then come the stitch, the sidecars and the
pack, into `data/processed-us-next` and `data/pack-us-next`, at `--jobs 2`. Before it
starts:

- **The master session's go-ahead.** The seasonal-risk study must have released the
  national pack. The six data decisions' pending `-next` data, including
  `data/raw/federal-next` → `data/raw/federal`, must be swapped in, because `closures.py`
  reads `data/raw/federal/mvum_roads.parquet`. That swap also frees the `-next` names this
  rebuild writes to.
- **Disk.** On 2026-10-22 the volume had 29 GB free. A rebuild needs about 32 GB:
  - a fresh region work directory, about 10 GB, like `data/national/build` without `raw/`.
    It has to be a new directory, because `build.py` skips every region whose
    `part_edges.parquet` exists. Its `raw/` can be linked to the existing caches;
  - `processed-us-next`, about 11 GB;
  - `pack-us-next`, about 11 GB.

  Something has to be freed first.

## 6. Open

- The national rebuild and everything after it in the brief's "Done looks like", item 3:
  - the -next pair and `.done`;
  - the continuity check at 11,414 of 11,414 legs;
  - `tests/test_national_routes.py` on the -next pack;
  - the icons and controls re-measured on the real build;
  - the national and per-state share of km at 7 or more, before and after.
- Nothing else: the suite on `processed-ne` is green (§2).

Figures derived from OpenStreetMap are © OpenStreetMap contributors, ODbL. ESA WorldCover
2021 is CC BY 4.0. PAD-US is US federal data. The marks are the owner's, and only
aggregates appear here.
