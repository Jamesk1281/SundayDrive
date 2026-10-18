# The national road graph build

**Status:** in progress, started 2026-10-18 on `claude/national-build` (off `usa`).
Output: `data/processed-us` in the main checkout, in `data/processed-ne`'s schema.

## 1. The earliest honest date

**`data/processed-us` complete and checked: Wednesday 21 October 2026, end of day.
Committed date: Thursday 22 October**, which leaves room for one full rebuild of
the country if the first one turns up a defect.

What that rests on, measured on this Mac on 2026-10-18:

| step | measured | basis for the national figure |
|---|---|---|
| download `us-latest.osm.pbf` (Geofabrik, 2026-10-17) | 12.2 GB at ~5 MB/s, ~40 min | in progress at the time of writing |
| the pipeline on one region (extract, elevation, landcover, score, graph, closures) | Colorado, 385 MB of PBF: **26 min** (extract.py alone 808 s) | its own logs of 2026-10-18 |
| the same, the whole country | about 13.5 GB of region PBFs (11.8 GB of states plus a 15 km overlap ring) at Colorado's rate: **~15 h single-stream**, ~8 h at two or three regions at once | memory, not cores, bounds the parallelism (6.7 GB of RAM per GB of PBF in extract.py; elevation.py's mosaic, Texas 13.3 GB) |
| Terrarium tiles, WorldCover tiles, PAD-US landmarks | 4.1 GB, 9.1 GB, a few hundred MB | sizes from `docs/us-map-data-findings.md` §2, §6 |

The plan by day:

- **Sun 18 Oct:** download; the global junction pass; the build driver; cut the six
  New England states out of the 2026-08-25 New England extract.
- **Mon 19 Oct:** the border proof and the New England check on 2026-08-25 data
  (§3, §4), against a joint New England build from the same extract. Then cut the
  country into regions and start the national build overnight.
- **Tue 20 Oct:** finish the regions; stitch; run `closures.py` and
  `state_roads.py` per region and remap their tables onto national edge ids.
- **Wed 21 Oct:** the New England trip sample on the national graph, per-state
  counts, and delivery.

What would move the date: a defect found by the border proof that needs a
redesign (a day), a second full national run (a day), or memory pressure from
other sessions on this Mac forcing the regions to run one at a time (half a day).
Disk is the other limit. 84 GB was free on 2026-10-18, not the 116 GB
expected, so region intermediates are deleted as each region is harvested.

## 2. Method

To be written as it is built.
