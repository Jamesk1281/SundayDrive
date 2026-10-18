# National build: the 48 states and DC as one processed directory

What [`docs/national-build.md`](../../docs/national-build.md) built and measured, and
how to run it again. The pipeline stages run unmodified, one region at a time, and
these scripts cut the regions, run the stages, and stitch the results into the
schema `data/processed-ne` has.

## Order

All paths below are under `data/national` in the main checkout. Nothing is written
into `data/processed-ne` or `data/processed`.

| step | script | writes |
|---|---|---|
| 1 | `curl` Geofabrik's `us-latest.osm.pbf`, check its `.md5` | `pbf/us-<date>.osm.pbf` |
| 2 | `padus_landmarks.py inputs/padus_landmarks.parquet` | PAD-US landmark polygons (the gdb needs a login since 2026-10-18) |
| 3 | `junctions.py pbf/us-<date>.osm.pbf junctions-us-<date>.npy` | every node two drivable-way references share, nationally |
| 4 | `cut.py pbf/us-<date>.osm.pbf boundaries/states48dc.parquet regions` | one ring PBF per region |
| 5 | `prefetch.py config.json` | every WorldCover tile, before regions run in parallel |
| 6 | `build.py config.json [region ...]` | `build/<region>/`: the pipeline's outputs, then `part_edges`, `part_restrictions`, `part_exits` |
| 7 | `stitch.py config.json <out>` | `graph_edges`, `graph_nodes`, `turn_restrictions`, `access_ways`, `access_entries`, `per_region.csv`, `stitch_report.json` |
| 8 | `sidecars.py config.json <out> ../raw/state-roads` | `closed_to_cars`, `seasonal_closures`, `osm_unpaved`, `state_road_class` |
| check | `compare.py`, `slice.py`, `joint.py` | the border proof and the New England check |

`boundaries/states48dc.parquet` is the Census TIGER/Line 2025 state layer
(`tl_2025_us_state.zip`) without the codes in `tools/us_map_data/scope.py`'s
`OUT_FIPS`.

`config.json`:

```json
{"pbf_dir": "regions", "work": "build", "junctions": "junctions-us-20261017.npy",
 "states": "boundaries/states48dc.parquet", "landmarks": "inputs/padus_landmarks.parquet",
 "jobs": 3, "mem_gb": 14, "keep": ["CT", "MA", "ME", "NH", "RI", "VT"]}
```

Every step skips what is already there, so a failed run is resumed by running it
again, and one region is rebuilt by deleting `build/<region>/part_edges.parquet`
(and whichever stage outputs should be redone) and re-running steps 6 to 8.

## Pieces

- `regions.py`: the regions (states; Texas and California in two), their 15 km
  rings, their projections, and `Owner`, which assigns an edge to the region
  holding its midpoint.
- `stage.py`: runs a pipeline stage with `common.CRS_METERS` (and `elevation.BBOX`)
  set to the region's, without editing either.
- `graph_part.py`: `graph.build_scored_edges` with the national junctions, before
  any component cut, with every edge's owner.
- `joint.py`: one PBF through the whole pipeline as one region, the way
  `processed-ne` was built: the reference the proof compares against.

## Traps hit building this

- **A region alone cannot know its junctions.** Counted from one extract, a node
  where its road meets a road only the neighbour's extract has is not a junction,
  so the same road is cut differently on the two sides. `junctions.py` counts once,
  nationally.
- **osmium extract's `smart` strategy completes only `type=multipolygon` by
  default.** Forests and parks mapped as `type=boundary` (`boundary=protected_area`,
  `national_park`) that cross a state line would come out incomplete in both states
  and fail to assemble. `cut.py` completes those too, limited to the tags
  extract.py reads, so county and state boundaries are not pulled in whole.
- **landcover.py's download is not safe to run twice at once.** Two regions fetching
  one tile write the same `.part` file. `prefetch.py` fills the cache first.
- **runpy re-executes a module.** Setting `elevation.BBOX` and then running
  elevation.py as `__main__` runs a fresh copy whose own `BBOX = ...` line undoes
  it, so `stage.py` calls `elevation.main` instead.
- **osmium extract config paths are relative to the config file**, not to the
  working directory.
