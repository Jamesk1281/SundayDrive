# National scenery types: scripts and results

What [`docs/national-scenery-types-verdict.md`](../../docs/national-scenery-types-verdict.md)
measured, and how. Nothing here is imported by `pipeline/`, `server/` or the app,
and nothing writes to `data/`. `pipeline/` is imported read-only, for `score.py`'s
constants and for `elevation.decode_terrarium` and `terrain.despike`.
`tools/national_scoring/core.py` is reused for New England's chunk tables, the marks and
the metrics.

## Inputs, all read-only

- Region slices: `data/national/build/<region>/part_edges.parquet` (owned edges carry
  `way_id` and every shipped `c_*`). The national `graph_edges.parquet` and the pack are
  never read.
- The national build's caches: Terrarium z11 tiles and WorldCover tiles under
  `data/national/build/raw/`, the region rings `data/national/regions/<r>.osm.pbf`
  (for coastline), and `data/national/inputs/padus_landmarks.parquet`.
- `tools/national_scoring`'s scratch tables for New England, Colorado and Utah (chunks,
  WorldCover, terrain, PAD-US, attributes, marks), linked into `$NS_WORK/reg/` and
  `$NS_WORK/marks.pkl`. `marks.pkl` locates every mark and is never committed.
- FHWA's national byways for Florida (`$NS_WORK/fhwa/fl.geojson`, 8 byways), from the
  same feature service as `tools/national_scoring/fetch_inputs.sh`, with `STATE IN ('FL')`.

Set `NS_WORK` to a scratch directory outside the repo and `SUNDAYDRIVE_MAIN` to the
main checkout.

## Order

| step | script | writes | measured |
|---|---|---|---|
| pin | `roads.py`, `pin.py results` | `results/pins.csv`, `pins_summary.csv` (committed before any candidate) | 85 s |
| define | `cands.py` | every candidate and sweep (committed before any feature) | |
| icons | `icons.py $NS_WORK` | `icons_pieces.parquet`: 26,325 pieces of 12,090 pinned edges | 10 min |
| | `viewshed.py $NS_WORK` | `icons_viewshed.parquet`: a true 72-ray viewshed | 269 s, 10.2 ms a piece |
| regions | `regions.py $NS_WORK co\|ut\|ne\|fl` | DEM and coast features beside each chunk table; Florida's edges and 1.76 M pieces | CO 109 s / 3.2 GB, UT 87 s / 2.5 GB, NE 122 s / 4.4 GB, FL 322 s / 6.0 GB |
| | `landmarks.py $NS_WORK` | distance to the nearest PAD-US landmark, for candidate L | ~3 min |
| measure | `evaluate.py $NS_WORK results` | the three checks for every candidate and sweep | ~150 s, 1.9 GB |
| | `proxy_vs_viewshed.py`, `movers.py` | the proxy against the viewshed; which named roads move | |

## Results (aggregate only)

- `pins.csv`, `pins_summary.csv`: the pre-registered roads as OSM way ids, with km and pieces
- `icons_s0_breakdown.csv`: every pinned road under S0, weight times component, the new
  features, and the raw score its class needs for 7
- `icons.csv`: each road's mean and share of km at 7 or more, under every candidate and sweep
- `checks.csv`: the brief's three checks, one row per candidate and sweep
- `ne_marks_ci.csv`: paired drive-cluster bootstrap against S0 (4,000 resamples)
- `byway_proxy.csv`: FHWA scenic/natural within ecoregion, per region and pooled
- `distributions.csv`: share of km at 7 or more and mean, per region
- `proxy_vs_viewshed.csv`, `movers.csv`

Figures derived from OpenStreetMap are © OpenStreetMap contributors, ODbL. ESA WorldCover
2021 is CC BY 4.0. Terrarium elevation's licensors are listed in `docs/data-sources.md`.
PAD-US, the EPA ecoregions and the FHWA byways are US federal data.

## Traps hit

- **`pipeline/elevation.fetch_tile` deletes a cache file it cannot decode.** It is never
  called here: `feat_lib.dem_mosaic` reads the national cache itself and treats a missing
  tile as a hole.
- **The Tioga Road's ways inside Yosemite carry its name but not the `CA 120` ref.** By ref
  alone the pin found 2.9 km of 78. Fixed before anything was scored.
- **Pieces carry only the capped `c_relief`,** so P's rolling gate can only be swept at or
  below `RELIEF_FULL`.
- **New England's marks cannot see S, W or R.** None of the 151 moves by more than 0.25
  under any of them, so for those terms the New England check rests on km moved alone.
