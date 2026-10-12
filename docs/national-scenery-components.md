# National scenery components: built

**Status:** built on the `usa` branch 2026-10-12, not merged to `main`, not deployed. The code is `pipeline/terrain.py`, `pipeline/protected.py`, `landcover.py`'s ~1 km desert and built-up box, `score.py`'s `WEIGHTS["grand"]`, `WEIGHTS["protected"]`, `PROTECTED_BUILT_MAX` and forest-slot `max()`, and `router.py`'s `BASELINE`/`OPTIONAL_BASELINE`. Tests are in `tests/test_national_components.py` (45). The deployed New England graph is untouched and serves unchanged: it lacks the two columns, and the Router reads them as zero.

This builds candidate E1 from
[`national-scenery-scoring-verdict.md`](national-scenery-scoring-verdict.md),
the verdict's first recommendation. One change came from building it: landmark
credit stops in built-up land (§3). Building it does not settle whether E1 is
right in the West. That is still the verdict's §9 drive plan.

## 1. What was built

| piece | where | what it does |
|---|---|---|
| Terrain | `pipeline/terrain.py` (new stage, after `elevation.py`) | `range3k.tif`: the elevation range within 3 km. Despikes first (§2) |
| `c_grand` | `score.py` | clip((range − 300 m) / 600 m), weight 0.10, always on |
| Desert and rock | `landcover.py` | WorldCover shrub, bare, snow and moss within a ~1 km ground box, from the same tile read as tree cover. New `desert` column in `tree_cover.parquet`; the tree column is bit-identical to before |
| | `score.py` | `c_forest = max(0.5 green + 0.5 tree, desert)` |
| Built-up land | `landcover.py` | WorldCover built-up share of the same 1 km box, as a new `built` column. Not a scenery term |
| `c_protected` | `pipeline/protected.py` (new, optional stage) | 1 inside a PAD-US landmark (national or state park, monument, conservation/recreation/scenic area, lake- or seashore, wilderness or study area) **and** at most 30% built within 1 km. Weight 0.07, always on |
| Router | `router.py` | `c_grand` and `c_protected` join `BASELINE`; a graph without them reads zero |

**No slider and no app change.** `c_grand` and `c_protected` are always-on terms,
like curvature and the byway tag, so `BEAUTY_TYPES`, the API and `Models.swift`
are untouched. Desert rides the forest/park slider. One consequence is left open:
a desert road's breakdown row is labelled "forest/park" (§6).

**Missing inputs score as before.** Without `range3k.tif`, `protected.parquet`,
or `tree_cover.parquet`'s new columns, each term is zero. A landmark table
alongside an old `tree_cover.parquet` (one with no `built` column) also scores
zero, because nothing can then tell a city park from a national one.

## 2. Despiking, a defect the evaluation hid

A 3 km window spreads one bad elevation pixel across about 2,800 neighbours. A
5×5-median rule catches single pixels, but not Colorado's Moffat County blob.
That blob is 12 × 9 px, about 2,000 m deep, with ringing at its rim, and it left
County Road 23 with a 2,298 m "range". The evaluation had hidden this with a
Colorado-only elevation band, which a national build cannot use.

`terrain.py` adds a second rule. A pixel more than 1,200 m from the median of a
~1.1 km neighbourhood is a hole, and the hole is grown by 2 px. Measured:

| build | px flagged | County Road 23 | deep-canyon roads checked |
|---|---:|---|---|
| Colorado | 463 | 2,298 → 740 m | Black Canyon South Rim and North Rim, Million Dollar Highway, Maroon Lake Road, Rim Rock Drive: unchanged |
| Utah | 2 | — | Zion Canyon Scenic Drive, Zion–Mount Carmel, Big Cottonwood, Potash Road, Logan Canyon: unchanged |
| New England | 1,373 | — | Kancamagus, Mount Washington Auto Road: unchanged; no chunk moves more than 5 m |

The shipped `relief.tif` is not despiked. It carries in-band spikes too
(`us-map-data-findings.md`), but fixing it moves New England's scores, which is a
separate decision.

## 3. City parks are not landmarks, a defect the build found

The first New England build gave Storrow Drive, Memorial Drive and Soldiers Field
Road +0.84 each. PAD-US files Boston's Charles River, Mystic River and Old Harbor
reservations as state parks, and those roads run through them. Measured over the
whole landmark set:

- **New England:** state parks are 630 of its 932 landmark km.
- **Every one of the 108 km** whose 1 km box is more than 30% built is an urban
  park or reservation: the Charles River Reservation (57 km), the Mystic River
  Reservation, the Boston waterfront parks, Hampton Beach.
- **The West:** Utah has no such km, and Colorado has 11 (Denver's reservoir parks).

So landmark credit now needs the 1 km box to be at most 30% built. With the gate:

- Storrow Drive, Memorial Drive and Soldiers Field Road get no landmark credit.
- Rural parks keep theirs: Franconia Notch Parkway goes 3.66 → 5.00, and Acadia's
  Park Loop Road 8.51 → 9.17.
- New England's landmark chunks fall from 0.41% to 0.31%. Utah's are unchanged
  at 2.77%.

The evaluation's figures could not see this. Its trips avoided central Boston,
and no mark lies on those parkways.

## 4. Measured on real builds

### Utah: a full rebuild with the unmodified stage order

`terrain.py`, `landcover.py --stream`, `protected.py`, `score.py`, `graph.py`,
`closures.py`. The result matches the evaluation's prediction for E1 to its
printed precision, so the pipeline implements what was measured:

| | evaluation's E1 | built |
|---|---|---|
| share of km at 7 or more | 9.0% | 8.98% |
| mean score | 4.33 | 4.33 |
| byways (OSM), state-wide / within ecoregion | 0.596 / 0.496 | 0.596 / 0.496 |
| scenic-designated byways (FHWA) | 0.593 / 0.489 | 0.593 / 0.489 |
| SR 128 / Capitol Reef Scenic Drive / Zion–Mount Carmel | 7.5 / 7.8 / 8.9 | 7.5 / 7.8 / 8.9 |
| landmark chunks | 2.8% | 2.77% |

Costs: `landcover.py` took 526 s against 382 s before (the 1 km box), `terrain.py`
70 s, `protected.py` 33 s. The data and graph tests pass on the Utah build
(65 passed, 3 skipped) after the inland fix in §5.

### New England: a scratch copy of the deployed build

The deployed build is not touched. A copy was:

1. scored by the new code *without* the new inputs, which is the baseline;
2. then given `terrain.py`, `landcover.py --stream` and `protected.py`, and scored
   again.

Both chunk sets were re-attached to the deployed graph's own edges with
graph.py's `attach_scores`, so the PBF (newer than the deployed graph) plays no
part.

- **The baseline is the served score exactly.** Re-attached, it differs from what
  the Router serves today by 0.0 on every one of the 998,252 edges. So the new
  code with no new inputs changes nothing.
- **The tree half is bit-identical** to the deployed `tree_cover.parquet`, on
  every chunk, with the same midpoints.
- **E1 with the built-land gate:**

  | | served today | E1 built |
  |---|---|---|
  | km moved by more than 0.25 / 1 | — | 1.28% / 0.05% |
  | mean / share at 7 or more | 4.89 / 13.07% | 4.90 / 13.37% |
  | marks: all 151 / Oct holdout | 0.719 / 0.766 | 0.721 / 0.773 |
  | marks at 7 or more liked | 96.2% (52) | 96.2% (53) |
  | 3–7 band | 0.541 | 0.534 |
  | byways (OSM / FHWA scenic), state-wide | 0.611 / 0.618 | 0.614 / 0.629 |
  | Kancamagus / Mohawk Trail / Mass Pike | 8.6 / 5.4 / 0.6 | 8.8 / 5.5 / 0.6 |

  `c_grand` is nonzero on 4.6% of km. Desert lifts `c_forest` by more than 0.1 on
  0.03% of km.
- **Costs:** `landcover.py --stream` read all 8 tiles in about 9 minutes;
  `terrain.py` took 72 s and `protected.py` 31 s.

### Loops: what the routes and marks did not show

The loop planner was run from 16 New England town centres at 40 km, at pref 0,
0.5 and 1, on the baseline and on E1 (`LoopPlanner.plan`).

| | baseline | E1 (gated) |
|---|---|---|
| starts where pref 1's loop beats pref 0's (mean score) | 15 of 16 | **12 of 16** |
| mean of the 16 pref-1 loop scores | 6.41 | 6.41 |
| beautiful km over the 16 pref-1 loops | 253 | 264 |

Three starts lose their pref-1 advantage: Concord MA (6.11 → 5.60), Woodstock VT
(7.96 → 7.74) and Camden ME (5.58 → 5.49). Lincoln NH, Needham and North Conway
gain.

**The cause is the planner, not the scores.** In each of the three, the
baseline's pref-1 loop scores *higher* under E1's own scores than the loop E1's
planner chose:

| start | baseline's loop, under E1 | E1's choice |
|---|---|---|
| Concord MA | 6.11 | 5.60 |
| Woodstock VT | 8.05 | 7.74 |
| Camden ME | 5.59 | 5.49 |

So a small shift in scores, 1.28% of km, flips a discrete choice inside
`looper.py`. That is the wart `test_the_middle_of_the_pref_slider_is_not_monotone`
documents: the final pick among built loops has no scenery term. Against this
build that test now fails on its first assertion (Concord's pref 1 below pref 0),
and against the deployed data it still passes. The test is left as it is,
because its docstring asks for exactly this report rather than an edit. **Any
score change will move these loops; fixing the planner's choice is the remedy,
not tuning the score.**

## 5. Test-suite changes

- `test_calibration.py::test_score_matches_components` and
  `test_graph.py::test_the_blend_covers_every_component_the_graph_carries` read the
  graph's own component list instead of a hardcoded nine. A graph built before the
  national components may lack exactly `OPTIONAL_BASELINE`.
- `TestBreakdownThreshold` took `.min()` of a component's nonzero bands. Utah has
  no coast, so `c_coast` has none; it now skips a component that is never
  credited. Every inland state would have hit this.
- `TestLegacyGraphMigration::test_recovery_agrees_with_the_surface_tags` skips on
  a graph built since 2026-08-29. It compares against `LEGACY_UNPAVED`, and any
  New England rebuild fails it by the `compacted` gap (residential 0.140 against
  0.129). This is the first rebuild since the migration, so nothing had hit it
  before.

**Suite results:**

| data | result |
|---|---|
| deployed New England build | 847 passed, 2 skipped (802 passed before this work) |
| rebuilt New England E1 copy | 847 passed, 1 skipped, 1 failed: the loop wart, §4 |
| rebuilt Utah (calibration, graph and component tests) | 110 passed, 3 skipped |

## 6. Open

- **The breakdown label.** On a desert road, "forest/park" is wrong. It needs a
  rename or a new type in `BEAUTY_TYPES` and its mirror in `Models.swift`. That is
  an app change, so it waits for the decision to ship E1.
- **The loop planner's choice** (§4). It is the cheaper fix, and it is worth doing
  before any score change ships to New England.
- **Deploying it to New England** means running the three new stages and
  `score.py`/`graph.py` on the live build. That moves 1.28% of New England's km by
  more than 0.25. On point-to-point trips, the evaluation found one of 24 changing
  at pref 1 (Pittsfield–Manchester VT: +20.8 beautiful km for +29.8 min).
- **Colorado** was not rebuilt here. The evaluation's Colorado figures are the
  prediction, less its 11 km of urban landmark road.
- **The Western drives** (verdict §9) decide whether any of this is right.
- **PAD-US is a 1.52 GB national download** (`tools/national_scoring/fetch_inputs.sh`).
  `protected.py` is optional; without it `c_protected` is zero.
