# Western land cover: can a US source tell sagebrush from prairie? Verdict

**Status:** measured 2026-10-18 on the `usa` branch at 5219744 (which contains `main` to 0fca74f), on
fresh builds of Colorado and Utah and the deployed New England build, read-only. Nothing in
`pipeline/`, `server/`, `ios/`, `tests/` or `data/` changed. Every figure comes from a script in
`tools/western_landcover/` or `tools/national_scoring/`, with its output in
`tools/western_landcover/results/`, unless the text says otherwise. National scale is E1,
absolute, as decided; this does not revisit it.

## The verdict

**No source passes the pre-registered rule, so WorldCover stays the desert source and nothing
in `pipeline/` changes.**

All three US sources do separate sagebrush and shrub-steppe from prairie at road scale. None of
them helps rank roads *within* a Western landscape, and that is the test the rule sets:

| E1 with this desert source | NE km moved > 0.25 | NE marks, all / Oct | CO S/N within ecoregion (needs > 0.605) | UT S/N within ecoregion (needs ≥ 0.479) | named roads | passes |
|---|---:|---|---:|---:|---|---|
| **W0** WorldCover (E1, the baseline) | — | 0.721 / 0.773 | 0.595 | 0.489 | all four ≥ 7, both dull ≤ 4 | — |
| W0m3 WorldCover at ~30 m (control) | 0.000% | 0.721 / 0.773 | 0.595 | 0.489 | ok | no |
| W0r WorldCover, rangeland only | 0.019% | 0.721 / 0.773 | 0.596 | 0.484 | ok | no |
| N1 NLCD, ungated | 0.191% | 0.721 / 0.773 | 0.598 | 0.486 | ok | no |
| N1r NLCD, rangeland only | 0.019% | 0.721 / 0.773 | **0.599** | 0.488 | ok | no |
| L1 LANDFIRE | 0.032% | 0.721 / 0.773 | 0.590 | 0.491 | ok | no |
| L1r LANDFIRE, rangeland only | 0.019% | 0.721 / 0.773 | 0.590 | 0.492 | ok | no |
| R1 RCMAP shrub + bare | 0.019% | 0.721 / 0.773 | 0.593 | 0.488 | ok | no |
| R2 RCMAP shrub | 0.019% | 0.721 / 0.773 | 0.595 | 0.499 | **SR 128 6.26** | no |

- **New England is safe for every source.** Trap 1 is real but small. Ungated NLCD moves 0.19% of
  New England's km (Maine 0.43%), and a 1 km box dilutes the clearcuts. The marks don't move at
  the third decimal for any candidate, and every paired interval is [0.000, 0.000].
- **The hypothesis is dead.** It was that separating sagebrush lifts Colorado within ecoregion.
  The best source adds +0.004, a third of the +0.01 the rule asks and inside the ±0.01 noise
  between candidates.
- **What the sources do change is the level between landscapes, not the order within one.**
  - FHWA scenic/natural, state-wide: Colorado 0.743 → 0.766 and Utah 0.593 → 0.615 (both N1r).
  - Share of km at 7 or more: Colorado 8.7% → 9.7% and Utah 9.0% → 11.1%.
  - Colorado's Wyoming Basin km rise a mean 1.30 points.

  That is a calibration question for Western marks. The rule does not reward it.

**Prairie, once separated** (§5). In Colorado it still points the wrong way state-wide on both
byway labels: 0.40–0.49 on the rangeland-only grass layers. Within an ecoregion it is at chance:
0.51–0.54. So "grass points the wrong way" is the plains having few byways, not grass ranking
roads badly within the plains. The New England marks can't read real prairie, because none
exists under them.

## 1. What was measured

**Builds.** These are fresh, under a scratch `NS_WORK` outside the repo. Order and scripts
follow `tools/national_scoring/README.md`:

| region | build | road km | WorldCover tiles |
|---|---|---:|---|
| New England | deployed `data/processed-ne`, read-only | 236,477 | 8 (N39W069 is ocean, a 404 on the tile) |
| Utah | `build_region.sh ut ...` (header command), Geofabrik 2026-10-17 | 77,720 | 9 |
| Colorado | the command below, Geofabrik 2026-10-17, 385 MB PBF, pipeline 1,648 s | 172,619 | 8 |

Colorado's command is now recorded, here and in `build_region.sh`'s header:

```
byway_ways.py $NS_WORK/co/pbf/region.osm.pbf US:CO:Scenic $NS_WORK/co_byway_ways.txt
BYWAY_WAYS=$NS_WORK/co_byway_ways.txt PADUS_FILE=$NS_WORK/padus_rest/co.parquet \
  build_region.sh co https://download.geofabrik.de/north-america/us/colorado-latest.osm.pbf \
  -109.1,36.95,-102.0,41.05 1000 4420 CO,UT,WY,NE,KS,OK,NM,AZ
```

On `usa`, `landcover.py` already writes the desert and built columns. `build_region.sh` now
drops them before `score.py`, keeping a copy as `tree_cover_national.parquet`. So S0 stays the
score without national terms, and `candidates.py` adds E1's terms once, not twice.

**The baseline reproduces.** E1 on these builds against the national verdict's tables:

| | verdict | this rebuild |
|---|---|---|
| NE marks S0 / E1, all | 0.719 / 0.721 | 0.719 / 0.721 |
| NE marks S0 / E1, Oct | 0.766 / 0.773 | 0.766 / 0.773 |
| NE marks at 7 or more liked, S0 / E1 | 52 / 53 | 52 / 53 |
| NE 3–7 band, S0 / E1 | 0.541 / 0.534 | 0.541 / 0.534 |
| NE km moved by E1, > 0.25 / > 1 | 1.3% / 0.05% | 1.33% / 0.05% |
| E1 byways, state-wide / within ecoregion: NE OSM | 0.614 / 0.576 | 0.614 / 0.576 |
| NE FHWA S/N | 0.629 / 0.574 | 0.629 / 0.574 |
| CO OSM | 0.681 / 0.535 | 0.681 / 0.535 |
| CO FHWA S/N | 0.744 / 0.596 | 0.743 / 0.595 |
| UT OSM | 0.596 / 0.496 | 0.596 / 0.496 |
| UT FHWA S/N | 0.593 / 0.489 | 0.593 / 0.489 |
| S0 CO FHWA S/N | 0.718 / 0.564 | 0.717 / 0.563 |
| E1 share at 7 or more, CO / UT | 8.7% / 9.0% | 8.7% / 9.0% |
| desert ≥ 0.5, NE / CO / UT | 0.0 / 2.4 / 24.0% | 0.0 / 2.4 / 24.0% |
| grassland ≥ 0.5, NE / CO / UT | 0.3 / 38.5 / 25.5% | 0.3 / 38.5 / 25.6% |
| SR 128 / Capitol Reef Scenic Drive | 7.5 / 7.8 | 7.47 / 7.75 |

The only differences are Colorado's last-digit 0.001s. They come from a newer extract and from
PAD-US read through a different route (§2). Every comparison below is against this rebuild's E1
(W0), never against the verdict's tables.

**Method.** Each source supplies a desert fraction in a ~1 km box, 33 × 33 px at 30 m, around
every chunk midpoint. It goes into E1's forest slot as `max(c_forest, desert)`, exactly where
WorldCover's does today, and nothing else in E1 changes. Byway checks are within trunk–tertiary
with the byway term removed. They are computed state-wide and within EPA Level III ecoregion,
as in the national verdict. The marks use `analyze_trace.py`'s attribution (400 m window, 3 s
reaction), with a paired drive-cluster bootstrap against E1 (4,000 resamples, 90%).

**Order.** New England's movement and marks for all nine candidates were computed and
committed first, before any Western table existed (`evaluate.py --ne-only`, commit 1ffa9c7,
`results/report_ne_first.txt`). That is trap 1.

## 2. The sources: retrievability

All are US government works in the public domain.

| source | file | size | notes |
|---|---|---:|---|
| **Annual NLCD 2025** (C1V2), Land Cover | `https://www.mrlc.gov/downloads/sciweb1/shared/mrlc/data-bundles/Annual_NLCD_LndCov_2025_CU_C1V2.zip` | 1.46 GB (last modified 2026-04-20) | 30 m, WGS84-datum Albers. The control URL beside it 404s, so the host is reachable. MRLC's WCS (`dmsdata.cr.usgs.gov/geoserver/mrlc_Land-Cover-Native_conus_year_data/wcs`) fails server-side on every GetCoverage ("startTime is null"), with or without a time subset, and speaks only 2.0.1. The bundle is the only working route. |
| **LANDFIRE EVT, LF2024** | `https://landfire.gov/data-downloads/CONUS_LF2024/LF2024_EVT_CONUS.zip` | 3.83 GB | 30 m, NAD83 Conus Albers, on NLCD's grid. LF2025 (`CONUS_LF2025/LF2025_EVT_CONUS.zip`, 1.31 GB, 2026-06-05) carries values for the far West only. The rest of CONUS is nodata, Colorado included, so it can't be used yet. That was found by a coverage check in `sample30.py` before any result was read. The class tables of LF2024 and LF2025 give identical groups under the rules below. |
| **RCMAP V8**, 2025 | `https://www.mrlc.gov/downloads/sciweb1/shared/mrlc/data-bundles/{Sagebrush,Shrub,Bare_Ground,Herbaceous}_2015_2025.zip` | 14 / 36 / 41 / 47 GB bundles; the 2025 members are 1.41 / 3.44 / 3.91 / 4.43 GB | The server allows range requests, so only `rcmap_<component>_2025.tif` is pulled from each zip. Percent cover, Western rangeland only; 101 is the non-rangeland mask *and* nodata. Its origin is ~1 m off NLCD's grid (the datum), which is 0.04 px. |
| PAD-US 4.1 (for E1's landmark term) | `services.arcgis.com/v01gqwM5QqNysAAi/.../Protection_Mechanism_Category_PADUS/FeatureServer/0` | 8.3k / 9.8k / 61k polygons for UT / CO / NE | The ScienceBase zip `fetch_inputs.sh` used now 404s, and so does a bogus name. Its new file manager needs a signed-in session (its API answers UNAUTHENTICATED, and its old catalog route shows a captcha). The same combined layer is public as a feature service, with the gdb layer's schema. `padus_rest.py` fetches it by bbox; Utah's landmark share comes out at 2.77%, as before. |

Sampling costs 32–58 s a region (`sample30.py`). The national WorldCover grids now also write a
3×3-majority (~30 m) version, which is the resolution control (`wc_grids.py`, `wc_sample.py --m3`).

## 3. The class groupings

These were written from each product's legend and committed before anything was sampled, in
commit 0cec4f8, `tools/western_landcover/classmaps.py`. That file is the definition. In short:

- **WorldCover (W0):** desert is shrubland 20, bare/sparse 60, snow 70, moss/lichen 100, as
  shipped. Grass is 30.
- **NLCD (N1):** desert is Shrub/Scrub 52, Barren 31, Ice/Snow 12, the class-for-class analog.
  CONUS has no moss class. Grass is Grassland/Herbaceous 71. Pasture/Hay 81 and Crops 82 are
  kept separate.
- **LANDFIRE (L1):**
  - Desert is `EVT_PHYS` Shrubland, Sparsely Vegetated or Snow-Ice, plus any Grassland class
    whose name says *Alpine* (fell-field, turf, tundra meadow).
  - The *transitional* classes are left out: "Recently Logged / Burned / Disturbed – Shrub
    Cover" (`EVT_GP_N` Transitional Shrub Vegetation). These are disturbance states of forest,
    and they are where LANDFIRE files Maine's clearcuts.
  - Exotic/ruderal vegetation is in neither group.
  - Grass is natural Grassland, minus transitional and alpine.
- **RCMAP:** R1 is (shrub + bare ground) cover / 100. R2 is shrub cover / 100, without bare
  ground, because the bare soil between shortgrass bunches is prairie. Grass is herbaceous
  cover / 100.
- **The gate (…r):** an NLCD, LANDFIRE or WorldCover desert pixel counts only where RCMAP 2025
  has a cover value, not its mask and not outside its extent. W0r is approximate: WorldCover's
  box share times the box's rangeland share, because the two grids differ.

Only these nine candidates were tried. No grouping was revised after a result was read. The
LANDFIRE version change (LF2025 → LF2024) changed the file, not the rules.

## 4. New England first

| | km moved > 0.25 / > 1 | share ≥ 7 | marks all / Oct | marks ≥ 7 liked | paired Δ vs E1, all and Oct |
|---|---|---:|---|---|---|
| E1 (W0) | — | 13.38% | 0.721 / 0.773 | 96.2% (53) | — |
| N1 NLCD, ungated | 0.191% / 0.007% | 13.39% | 0.721 / 0.773 | 96.2% (53) | 0.000 [0.000, 0.000] |
| L1 LANDFIRE | 0.032% / 0 | 13.38% | 0.721 / 0.773 | 96.2% (53) | 0.000 [0.000, 0.000] |
| every gated source, R1, R2 | 0.019% / 0 | 13.38% | 0.721 / 0.773 | 96.2% (53) | 0.000 [0.000, 0.000] |

- **NLCD's Shrub/Scrub does what the brief feared.** It averages 1.2% of New England's 1 km
  boxes, and its movers sit in Maine (0.43% of the state's km), New Hampshire (0.23%) and
  Massachusetts (0.13%). But almost no 1 km box is half clearcut: its share of km at 0.5 or more
  rounds to 0.0%, and it moves 0.19% of km. That is far inside the rule's 1.5%.
- **LANDFIRE's split works.** It moves 0.03%, because clearcuts are its transitional classes.
- **The gate zeroes New England by construction.** RCMAP's footprint ends at 88–90° W. The
  0.019% that every gated source moves is WorldCover's own desert credit there, quarries and
  gravel pits mostly, going away.

**The gate's seam, priced nationally** (`gate_seam.py`, NLCD against RCMAP at ~480 m, by
longitude band, `results/gate_seam.txt`):

- Nationally the gate keeps **94.0%** of NLCD's desert pixels. West of 104° W it keeps 93–99%
  in every band.
- East of 95° W, NLCD desert is 2.1% of land, and the gate keeps 5.1% of it. NLCD's own
  definition of Shrub/Scrub includes early-successional trees, so most of that is probably
  regenerating forest. That was not checked class by class.
- It has no sharp edge. RCMAP rangeland is 64% of land at 100° W, 47% at 98°, 40% at 95°, 16%
  at 94° and 0 by 90°. NLCD's desert share falls with it, from 28% at 100° W to 0.6–3.5% from
  97° W east.
- So the seam runs through the eastern Plains, where little desert is lost. What it would cost
  is any genuine Eastern open land, such as the Atlantic heathlands or the Appalachian balds.
  At 2% of land, and mostly not that, it is small.

## 5. The West

### What WorldCover's "grassland" is

Colorado km with WorldCover grass ≥ 0.5, by landscape, and what the other sources say is there
(`results/what_worldcover_grass_is.csv`, mean fractions):

| landscape | km | LANDFIRE desert / grass | NLCD desert / grass | RCMAP sage / shrub / bare / herb |
|---|---:|---|---|---|
| plains | 43,561 (61%) | 0.07 / 0.57 | 0.04 / 0.69 | 0.01 / 0.03 / 0.16 / 0.38 |
| mountains | 15,901 | 0.33 / 0.22 | 0.49 / 0.19 | 0.05 / 0.14 / 0.13 / 0.39 |
| plateau and canyon | 9,248 | 0.47 / 0.02 | 0.65 / 0.01 | 0.04 / 0.11 / 0.23 / 0.26 |
| Wyoming Basin | 2,250 | 0.67 / 0.04 | 0.83 / 0.03 | 0.11 / 0.15 / 0.20 / 0.37 |

The brief's premise is half right:

- **By km, most of Colorado's WorldCover grass is prairie.** 61% is on the plains, where both
  class products call it grassland.
- **The 39% off the plains is mostly shrubland** by both class products.

So the sources do separate the two at road scale. Colorado's desert share at ≥ 0.5 goes from
2.4% under WorldCover to 8.9% (LANDFIRE) or 14.8% (NLCD). Utah's goes from 24.0% to 32.5% or
45.9%. RCMAP's sagebrush layer is thin at this scale: a 1 km mean of 0.11 even in the Wyoming
Basin.

### The byway checks

Trunk–tertiary, byway term removed (`results/byway_proxy.csv`; FHWA H/C in the CSV):

| | CO OSM | CO FHWA S/N | UT OSM | UT FHWA S/N |
|---|---|---|---|---|
| S0 | 0.661 / 0.517 | 0.717 / 0.563 | 0.555 / 0.483 | 0.560 / 0.491 |
| **E1 (W0)** | **0.681 / 0.535** | **0.743 / 0.595** | **0.596 / 0.496** | **0.593 / 0.489** |
| W0m3 | 0.681 / 0.535 | 0.743 / 0.595 | 0.596 / 0.496 | 0.593 / 0.489 |
| W0r | 0.681 / 0.536 | 0.743 / 0.596 | 0.599 / 0.493 | 0.593 / 0.484 |
| N1 | 0.702 / 0.539 | 0.765 / 0.598 | 0.621 / 0.492 | 0.613 / 0.486 |
| N1r | 0.700 / 0.538 | 0.766 / 0.599 | 0.624 / 0.495 | 0.615 / 0.488 |
| L1 | 0.689 / 0.532 | 0.746 / 0.590 | 0.622 / 0.498 | 0.614 / 0.491 |
| L1r | 0.689 / 0.532 | 0.746 / 0.590 | 0.624 / 0.499 | 0.616 / 0.492 |
| R1 | 0.692 / 0.544 | 0.746 / 0.593 | 0.610 / 0.492 | 0.605 / 0.488 |
| R2 | 0.675 / 0.532 | 0.738 / 0.595 | 0.579 / 0.492 | 0.581 / 0.499 |

Cells are state-wide / within ecoregion.

- **State-wide gains are real.** NLCD adds about +0.02 everywhere in the West.
- **The gains vanish within an ecoregion.** NLCD's desert fraction alone separates Colorado's
  S/N byways at 0.744 state-wide and 0.493 within ecoregion. WorldCover's own desert keeps more
  within-landscape signal (0.591), because it is rare and lands on real rock. NLCD's says which
  landscape a road is in, and the byway proxy already knows that.
- **Per ecoregion, small wins and losses cancel** (`results/byway_by_ecoregion.csv`, FHWA S/N):
  - Colorado Plateaus 0.406 → 0.435 (N1r);
  - Southwestern Tablelands 0.531 → 0.623 on 89 byway km;
  - Southern Rockies, the bulk of the byways, 0.632 → 0.624.

  The pair-weighted net is +0.004.
- **Resolution is not the finding (trap 4).** The ~30 m majority WorldCover matches the 10 m
  one to 0.001 on every check and moves no New England km.

### Shares at 7 or more, and where km move

| share ≥ 7 | CO all | CO mountains | CO plateau | CO basin | CO plains | UT all | UT mountains | UT plateau | UT basin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E1 (W0) | 8.7 | 29.1 | 6.7 | 1.3 | 0.6 | 9.0 | 24.0 | 12.0 | 2.8 |
| N1 | 9.8 | 31.7 | 8.9 | 4.5 | 0.7 | 11.3 | 28.4 | 15.4 | 3.9 |
| N1r | 9.7 | 31.5 | 8.6 | 4.2 | 0.6 | 11.1 | 28.1 | 15.0 | 3.8 |
| L1 | 9.1 | 30.4 | 7.1 | 2.5 | 0.6 | 9.5 | 25.9 | 12.0 | 3.1 |
| R1 | 9.0 | 29.8 | 6.8 | 1.6 | 0.7 | 8.5 | 24.8 | 10.3 | 2.5 |
| R2 | 8.6 | 29.4 | 5.2 | 1.1 | 0.6 | 7.0 | 24.0 | 6.2 | 2.1 |

How far each source moves km against E1 (`results/western_movement.csv`):

- **N1r:** 17% of Colorado's km rise by more than 0.25 and 4% fall, but 89% of the Wyoming
  Basin's km rise (mean +1.30). The plains move under 4% either way, so the sources leave
  prairie where WorldCover had it.
- **R1:** lifts 27% of the plains' km by more than 0.25. That is the bare-soil-in-shortgrass
  problem R2 was written for.
- **R2:** fixes that, but drops 70% of Utah's plateau km, because slickrock has no shrubs.

### Named roads

Mean score, E1 → N1r / L1 / R1 / R2 (`results/named_roads.csv`):

- **Rule ≥ 7:**
  - Trail Ridge 8.93 → 8.87 / 8.97 / 8.86 / 8.86;
  - Rim Rock Drive 7.96 → 8.07 / 7.89 / 7.84 / 7.81;
  - SR 128 7.47 → 7.81 / 7.62 / 7.48 / **6.26**;
  - Capitol Reef Scenic Drive 7.75 → 8.00 / 7.71 / 7.53 / 7.11.
- **Rule ≤ 4:**
  - I 70 east of Denver: 0.1 under every source;
  - US 287 on the plains: 1.51 → 1.50 / 1.63 / 1.85 / 1.54.
- **Others:**
  - CO 141 Unaweep–Tabeguache 6.02 → 6.41 (N1r);
  - US 50 Gunnison–Montrose 4.85 → 5.38;
  - Highway of Legends 6.25 → 6.64;
  - US 6 Delta–Eureka 3.27 → 3.61.

  No dull road crosses 4.

## 6. Once sagebrush is separated, does real grassland still point the wrong way?

Numbers only. Whether prairie should count is the owner's call. Single-feature AUC, within
trunk–tertiary, state-wide / within ecoregion (`results/single_features.csv`):

| grass layer | CO OSM byways | CO FHWA S/N | UT OSM | UT FHWA S/N |
|---|---|---|---|---|
| WorldCover grassland (30), sagebrush mixed in | 0.461 / 0.472 | 0.401 / 0.400 | 0.523 / 0.513 | 0.532 / 0.546 |
| NLCD Grassland/Herbaceous (71) | 0.395 / 0.517 | 0.374 / 0.508 | 0.474 / 0.501 | 0.466 / 0.498 |
| NLCD 71, rangeland only | 0.418 / 0.517 | 0.404 / 0.507 | 0.480 / 0.501 | 0.472 / 0.499 |
| LANDFIRE natural grassland | 0.468 / 0.538 | 0.436 / 0.508 | 0.654 / 0.537 | 0.629 / 0.527 |
| LANDFIRE natural grassland, rangeland only | 0.491 / 0.537 | 0.471 / 0.513 | 0.661 / 0.534 | 0.635 / 0.524 |
| RCMAP herbaceous cover | 0.576 / 0.473 | 0.586 / 0.448 | 0.607 / 0.499 | 0.600 / 0.519 |

- **State-wide in Colorado, separated prairie still points the wrong way:** 0.37–0.49 on both
  labels for NLCD and LANDFIRE. It is no better than the mixed class.
- **Within an ecoregion it is at chance:** 0.507–0.538. Mixing sagebrush in had not been hiding
  a within-landscape signal. The state-wide sign is the plains having few byways.
- **Utah's natural grassland is mountain meadow,** 0.7% of road surroundings. It points the
  right way state-wide (0.63–0.66) and is near chance within ecoregion (0.52–0.54).
- **RCMAP's herbaceous cover goes the other way** (0.59 state-wide, 0.45 within ecoregion). It
  is herb cover *within* rangeland, the understory of shrub-steppe too, so it isn't a prairie
  layer.

**Prairie in the forest slot** (E1 + each source's grass net of built land, the national
verdict's E1g form), Colorado OSM / FHWA S/N within ecoregion:

| | Colorado OSM, within ecoregion | Colorado FHWA S/N, within ecoregion |
|---|---|---|
| WorldCover's grass (E1g) | 0.535 → 0.548 | 0.595 → 0.573 |
| NLCD rangeland grass | 0.538 → 0.554 | 0.599 → 0.588 |
| LANDFIRE grass | 0.532 → 0.555 | 0.590 → 0.585 |

Utah's within-ecoregion and New England's numbers are unchanged, except under WorldCover's own
grass.

**The marks** (151, all / Oct; `results/breakdowns.txt`):

- **Real prairie is absent from New England.** LANDFIRE's natural grassland and every
  rangeland-gated grass layer are zero under all 151 marks, so they read 0.500 by construction.
- **WorldCover's grassland reads 0.394 / 0.330.** In New England it is pasture, hay and road
  edge: where it is ≥ 0.5, NLCD calls the box 0.33 pasture/hay, 0.29 tree, 0.07 grass.
- **NLCD's own open classes point the other way on the same marks:** Grassland 71 0.575 / 0.515,
  Pasture/Hay 81 0.571 / 0.523. So "grass points the wrong way on the marks" is a property of
  WorldCover's grass class in New England. It is not a finding about open land.

## 7. What this can't tell you

- **The rule is a proxy rule.** The byway labels can't say whether a 7 on a Wyoming Basin
  highway is right. NLCD would put 4.2% of that landscape's km over 7, where WorldCover puts
  1.3%. Whether that is better is the national verdict's §9: Western marks.
- **Only Colorado and Utah were rebuilt.** The gate's national behaviour is priced from the
  rasters (§4), not from road scores outside these three regions.
- **RCMAP's fractional groupings are one reading of a product without classes.** R1 and R2 were
  both written down. A dominance rule (shrub > herb) was not, and it was not tried.

## Tests

Nothing in `pipeline/` changed, so there is no new test. The suite with the main checkout's
`data/` linked in: 774 passed, 71 skipped, 4 failed. The same 4 fail on `usa` itself at
5219744: `test_loop_speed.py::TestTheProof::test_refining_proves_what_leaving_alone_cannot`
and three in `test_options.py`. So they predate this work. On 2026-10-12, `usa` was 847 passed.

## Reproducing this

1. Set up the regions. With `NS_WORK` outside the repo and `SUNDAYDRIVE_MAIN` at the main
   checkout:
   - run `fetch_inputs.sh` (FHWA and ecoregions; PAD-US is its last step and now 404s);
   - run `padus_rest.py` per region bbox;
   - run `wc_grids.py` over the 24 tiles (23 exist);
   - build each region with `build_region.sh` and the commands above, run `PART=features`
     after the grids exist, then `wc_sample.py <grid> <reg> --m3`;
   - run `extract_marks.py`.
2. Fetch the three products into their own directories:
   - the NLCD and LF2024 zips, unzipped;
   - the RCMAP 2025 members, pulled out of the 2015–2025 bundles by range reads.
3. Measure from `tools/western_landcover/`:
   - `sample30.py <reg> <nlcd.tif> <LF2024_EVT_CONUS.tif> <LF2024_EVT.csv> <rcmap_dir>` per
     region;
   - `evaluate.py results --ne-only`, then `evaluate.py results`;
   - `breakdowns.py results`;
   - `gate_seam.py`.
