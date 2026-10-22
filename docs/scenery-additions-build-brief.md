# Build V + S2 + L: three scenery additions for the national score

**Status:** decided, not built. Written 2026-10-22 by the master session
against `usa` at `37bc5c1`. The owner approved building the three terms that
`docs/national-scenery-types-verdict.md` recommends. **Nothing has been
touched:** no code, and no data. The study measured them offline, in
`tools/scenery_types/`. This brief turns them into pipeline stages and
rebuilds the national data. Your answer goes in
**`docs/national-scenery-additions.md`**, plus the code and tests. Don't
append to this brief: it is deleted in the merge that brings the work back.

## What to build (exactly what was measured; don't re-tune)

All three change **existing** columns, `c_grand`, `c_water` and
`c_protected`, by `max()`. No column is added, so `graph_edges.parquet`'s
schema, `BEAUTY_TYPES` and the pack format stay as they are. The reference
implementation is `tools/scenery_types/cands.py:55-101`. The pipeline must
reproduce it.

### V: distant relief over open land, into the `c_grand` slot

```python
# tools/scenery_types/cands.py:65-71
def open_land(F):
    return np.clip(1 - f(F, "tree_1k") - f(F, "built_1k") - f(F, "mangrove_1k"), 0, 1)

def vista(F, R=V_R, v0=V0, v1=V1):
    p = np.nan_to_num(f(F, f"prom{R}k"), nan=0.0)
    return open_land(F) * np.clip((p - v0) / (v1 - v0), 0, 1)
```

- **`prom10k`** is the highest *despiked* elevation within a 10 km half-side
  square, minus the elevation at the road's own point. The windows are sized at
  `RELIEF_REF_LAT`, as every pipeline window is (verdict §3, §10).
- **`V0`, `V1`** are `GRAND_START = 300.0` and `GRAND_FULL = 900.0`
  (`pipeline/score.py:107-108`). `R = 10`.
- **Open land** is WorldCover within about 1 km that is not tree, built or
  mangrove. Each `<class>_1k` in the study is that class's share of a 9 × 11
  pixel box on WorldCover's ~100 m aggregate (`tools/scenery_types/feat_lib.py:95-130`,
  `uniform_filter(a, size=(9, 11))`). That is the same box `landcover.py`
  already uses for its desert and built shares (`landcover.py:74-82`).
  **`tree_1k` is that box's tree share. It is not the per-chunk `tree`
  fraction in `tree_cover.parquet`,** which is an ~83 × 62 m window
  (`landcover.py:101`). Mixing the two up changes open land everywhere.
- **The result:** `c_grand = max(c_grand, vista)`.
- **Where:** `pipeline/terrain.py` already despikes the mosaic
  (`despike`, `terrain.py:72`) and writes `range3k.tif` (`:122-146`). Add a
  10 km maximum filter and write `prom10k.tif` beside it, minus the elevation
  at sampling time, or as a raster. `pipeline/landcover.py` must also emit
  `mangrove` (WorldCover class 95) in its ~1 km box, beside the tree and built
  shares it already writes. `pipeline/score.py` combines them where it sets
  `c_grand` (`score.py:661`).

### S2: the sea as water, only where the road is on it, into `c_water`

```python
# tools/scenery_types/cands.py:74-79
def sea(F, near=S.DIST["water"], mid=S.DIST["water_mid"], on_sea=False, share=ON_SEA_WATER_SHARE):
    d = f(F, "d_coast")
    s = np.where(d <= near, 1.0, np.where(d <= mid, WET_MID, 0.0))
    if on_sea:
        s = s * (f(F, "water_1k") >= share)
```

- `d_coast` is the distance to the coastline. The study capped it at 1,000 m
  (`feat_lib.py:157`, `coast_distance`). Use the coastline tree
  `score.py` already builds (`score.py:625`). `near` = 120 m, `mid` = 350 m,
  `WET_MID = 0.45`. `share = 0.5` of the ~1 km box is WorldCover permanent
  water (class 80). `landcover.py` must emit that `water` share.
- **The result:** `c_water = max(c_water, sea)`.

### L: landmark credit within 80 m, into `c_protected`

```python
# tools/scenery_types/cands.py:97-98
def landmark(F, dist=S.DIST["green"]):
    return ((f(F, "d_landmark") <= dist) & (f(F, "built_1k") <= S.PROTECTED_BUILT_MAX)).astype(float)
```

- **Where:** `pipeline/protected.py:landmark_flags` (`:65-77`) uses
  `predicate="intersects"` on points. Use a within-80 m test instead, by
  `dwithin` or a buffer in a metric CRS. Keep the 30% built gate exactly as
  `sample_protected` applies it (`score.py:482-495`).
- **Why:** PAD-US's fee polygons cut the road right-of-way out. The Tamiami
  Trail is 9% inside Big Cypress but 98% within 80 m (verdict §5).

## What the study measured (the numbers your build must reproduce)

From `tools/scenery_types/results/checks.csv`, row `V+S2+L`, against shipped
E1:

| check | shipped E1 | V+S2+L |
|---|---:|---:|
| New England marks, all 151 | 0.721 | 0.721 |
| New England marks, Oct holdout | 0.773 | 0.780 (90% interval −0.003 to +0.017) |
| New England km moved > 0.25 | — | 2.52% |
| New England marks scored ≥ 7 | 53 | 56 |
| icon km ≥ 7 (pinned list) | 37.6% | 42.4% |
| control km ≥ 7 | 0.04% | 0.04% |
| worst control mean | 3.52 (Bell Road) | 3.66 (US 6 Delta–Eureka) |

Named roads: Death Valley's CA 190 goes from 34% to 96% of km at 7 or more,
the Overseas Highway from 16% to 32%, and Valley of Fire from 22% to 36%
(verdict, "The verdict").

## The order, and the gate

1. **Now, light work only:**
   - the code and the unit tests;
   - one small Western region (Utah, about 15 minutes as E1's build) to
     compare against the study's piece-level figures;
   - **a scratch copy** of New England, built as
     `docs/national-scenery-components.md` §4 did. Never write
     `data/processed-ne`.
   - The seasonal-risk session (chip `task_6008122e`) is holding the national
     pack for its last runs, at about 8 GB. Run nothing whose peak is above
     about 4 GB until the master session says the slot is free. Check
     `memory_pressure` first.
2. **Then message the master session and wait for its go-ahead** before the
   national rebuild. Before it gives one, the master session must:
   - wait for the seasonal study to finish;
   - swap the pending `-next` data from the six data decisions
     (`docs/national-data-decisions.md`, "The rebuilt data"), including
     `data/raw/federal-next` → `data/raw/federal`. The rebuild's closures
     stage reads `data/raw/federal/mvum_roads.parquet`. Without the refetched
     fields, D5's rule misreads it.
3. **The national rebuild, alone, at `--jobs 2`:**
   - all region stages (about 10.7 process-hours; verdict §7), then the
     stitch, the sidecars and the pack, into `data/processed-us-next` and
     `data/pack-us-next`, with `data/pack-us-next.done` when the pair is
     complete;
   - follow `tools/national_build/README.md` and `docs/national-build.md`;
   - the swap is the master session's.

## Traps

1. **One national-scale job on this Mac at a time.** On 2026-10-21 at 23:29,
   three sessions on national data (a three-job sidecar rebuild, the pack, and
   a 4.2 GB parquet read) hung the 24 GB Mac into a kernel watchdog panic.
   Rebuild at `--jobs 2` and only after the go-ahead. In `terrain.py`, compute
   the 3 km range and the 10 km prominence **in turn**, never as two
   mosaic-sized arrays at once. Montana's adds about 3.6 GB (verdict §7).
2. **Reproduce, don't improve.** The constants were swept and passed as
   they are:
   - V0/V1 = 300/900;
   - R = 10 km;
   - the on-sea share = 0.5;
   - L at 80 m with the 0.3 built gate.

   Changing any of them invalidates the New England check. If the pipeline's
   New England scratch copy doesn't reproduce 0.721 / 0.780 / 2.52%, find
   the implementation difference. Don't move a constant. Small differences
   on the icons are expected, because the study used 400 m pieces with
   edge-averaged components there (verdict §10). New England used chunk
   tables, so it should match to about three decimals.
3. **Despike before the 10 km maximum filter.** Western Terrarium has in-band
   spikes (`docs/national-scenery-components.md` §2). A 10 km maximum finds
   every one, so use `terrain.despike`, as `range3k` does.
4. **Never write `data/processed-us`, `data/pack-us` or `data/processed-ne`.**
   Build into `-next` and a scratch New England copy.
5. **Distances in a metric CRS per region.** Use whatever `score.py`'s
   existing `near_flags` and coastline queries use. The router's
   `CRS_METERS` (EPSG:26986) is wrong at national scale, about 4.5% long at
   Key West (`docs/national-build.md` §8).
6. **The default `data/processed` is an August MA-only build.** Always set
   `SUNDAYDRIVE_DATA` explicitly.
7. **The repo is public.** Commit aggregate results only, never per-mark
   coordinates.

## Done looks like

1. Code in `pipeline/terrain.py`, `landcover.py`, `protected.py` and
   `score.py`. Unit tests for each term in `tests/`, including one per term
   that mutates its constant and watches a test fail.
2. Reproduction, recorded in `docs/national-scenery-additions.md`: the New
   England scratch copy against the table above, and Utah against the study's
   Utah pieces.
3. After the go-ahead:
   - `data/processed-us-next` + `data/pack-us-next` + `.done`;
   - the continuity check (`tools/national_audit/continuity.py`) at 11,414
     of 11,414 legs;
   - `tests/test_national_routes.py` with `SUNDAYDRIVE_PACK` set to the
     -next pack;
   - the suite on `processed-ne` green;
   - the pinned icons and controls re-measured on the real build
     (`tools/scenery_types/icons.py`).
4. The answer doc has the national numbers: share of km at 7 or more
   nationally and per state, before and after.
5. This brief committed with the work, with nothing appended to it.
6. **The escape hatch:** if the pipeline can't reproduce the New England
   check without changing a constant, stop before the national rebuild and
   report the difference.
