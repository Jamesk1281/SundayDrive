# National scenery scoring: scripts and results

What [`docs/national-scenery-scoring-verdict.md`](../../docs/national-scenery-scoring-verdict.md)
measured, and how. Nothing here is imported by `pipeline/`, `server/` or the app,
and nothing writes to `data/`. The pipeline is run unmodified to build a region;
everything else reads its outputs and imports `score.py` only for its constants and
`composite`, and `router.py` only to monkeypatch `Router._edge_scores`.

## Locations

Three environment variables, so no path on the author's machine is in the repo:

- `NS_WORK` (required): a scratch directory **outside the repo**. Region builds,
  feature tables, the national downloads and two pickles live there.
  `marks.pkl` locates every mark the owner made, to the second. It must never be
  committed, and nothing in `results/` is derived from it except aggregate
  separations.
- `SUNDAYDRIVE_MAIN`: the main checkout, the only place `data/` and `traces/`
  exist. It defaults to this repo.
- `NS_CO_PROCESSED`: an existing Colorado build. It defaults to `$NS_WORK/co/processed`.

## Order

| step | script | what it writes | measured cost (one region) |
|---|---|---|---|
| inputs | `fetch_inputs.sh` | FHWA byways (8 states), EPA L3 ecoregions, PAD-US 4.1 | 1.55 GB down, 2.0 GB unpacked |
| WorldCover | `wc_grids.py <dl> <grid> <tile>...` | per-class pixel counts on a 12×12-pixel (~100 m) block grid, per 3° tile | ~70 s a tile; 22 tiles → 235 MB |
| region | `build_region.sh` | the unmodified pipeline, then the five feature steps below | Utah: ~15 min, 837 MB |
| | `prep_region.py` | chunk table, and graph.py's exact chunk→edge averaging map (checked: max difference 0.0) | ~30 s |
| | `terrain.py` | 3 km and 6 km range, height above the local minimum, depth below the local maximum | ~70 s, ~3 GB RAM |
| | `relief_raw.py` | the uncapped 750 m relief `c_relief` is cut from | seconds |
| | `wc_sample.py` | WorldCover class fractions at ~100 m and ~1 km | ~1 min |
| | `padus.py` | PAD-US landmark / GAP 1–2 / public-land flags | 3–4 min |
| | `attrs.py` | state, ecoregion, byway labels (OSM extract, a full state network, FHWA by intrinsic quality) | ~1 min |
| marks | `extract_marks.py $NS_WORK/marks.pkl` | **private**: analyze_trace's own attribution, every sampled edge kept | ~10 s |
| measure | `marks_features.py`, `describe.py` | single-feature checks on marks and byways | |
| | `eval_all.py results` | every candidate on marks, byway proxy, distributions, benchmarks | ~90 s |
| | `marks_ci.py`, `sensitivity.py`, `global_relief.py`, `seams.py`, `decisive_roads.py` | intervals, constant sweeps, trap 5, boundary seams, the drive list | |
| | `routes.py <region> <csv> <candidate>...` | the shipped Router on fixed town-centre trips | NE ~4 min |

`candidates.py` holds every candidate's definition. `core.py` holds loading and the
metrics.

## Traps hit while building this

- **The deployed New England graph predates 2026-08-29.** Its stored `score` still
  carries the old −0.25 unpaved penalty on 5.4% of edges. The Router strips it out
  at load (`Router._load_unpaved`), so the served score is different. `core.served()`
  applies the same recovery. Read the parquet column directly and New England's
  share of km at 7 or more is 11.0% instead of the served 13.1%, and its mean 4.57
  instead of 4.89.
- **Terrarium has in-band spikes in the West.** A ~700 m pixel sits in Moffat
  County, where Colorado's lowest point is 1,011 m. `terrain.py` drops pixels outside
  a physical band and any pixel more than 250 m from its 5×5 median: 13,704 px in
  Colorado, 225 in New England, 213 in Utah.
- **GDAL's FileGDB driver returns nothing unless the `where` field is also read.**
  It also drops rows on `AND`, and on a one-element `IN`. `padus.py` reads
  `State_Nm` and filters `FeatClass` in pandas.
- **ScienceBase's "manager" links are web pages, not files.** The catalog endpoint
  `catalog/file/get/<item>?name=<file>` serves the zip.
- **WorldCover calls most of Colorado's sagebrush "grassland".** Grass is 41% of
  Colorado's road surroundings and shrub 2%. So land cover cannot separate the
  Western Slope from the eastern plains.

## Results

Everything in `results/` is aggregate: separations, km shares, mean scores per named
public road, and route totals between town centres. No row locates a mark. The
figures derived from OpenStreetMap are © OpenStreetMap contributors, ODbL. The
other sources' terms:

- WorldCover: CC BY 4.0.
- PAD-US, EPA ecoregions and Terrarium's US sources: public domain.
- FHWA byways: no licence stated, used only as a check.
