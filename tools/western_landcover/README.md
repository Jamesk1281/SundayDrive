# Western land cover: scripts and results

What [`docs/western-landcover-verdict.md`](../../docs/western-landcover-verdict.md) measured, and how.
It builds on `tools/national_scoring/` (its regions, feature tables, marks and candidates) and,
like it, imports nothing into `pipeline/` and writes nothing to `data/`. Set `NS_WORK` (outside
the repo) and `SUNDAYDRIVE_MAIN` as that README says.

| script | what it does |
|---|---|
| `classmaps.py` | the class groupings and the nine candidates, committed before any measurement (0cec4f8) |
| `sample30.py` | NLCD, LANDFIRE and RCMAP fractions in a 33 × 33 px (~1 km) box at every chunk midpoint → `$NS_WORK/reg/<r>/lc30.parquet`. It stops if a product is nodata under more than 1% of midpoints |
| `evaluate_lib.py` | loads the three regions and the marks, and scores E1 with each desert source in the forest slot |
| `evaluate.py results [--ne-only]` | New England movement and marks first, then coverage, byway checks, shares at 7+, named roads and the prairie question |
| `breakdowns.py results` | byway separation per ecoregion, what WorldCover's grass is in New England, open-land classes on the marks, and Western movement by landscape |
| `gate_seam.py` | the rangeland gate's national cost, by longitude band, from the rasters |

`results/` holds aggregates only: separations, km shares, mean scores per named public road,
and per-band raster shares. No row locates a mark.

Sources: Annual NLCD 2025, LANDFIRE EVT LF2024 and RCMAP V8 2025 (all US government works,
public domain), and ESA WorldCover 2021 (CC BY 4.0). The exact URLs, and why LF2024 rather than
LF2025, are in the verdict §2.
