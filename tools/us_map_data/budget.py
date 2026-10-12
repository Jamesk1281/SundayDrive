"""Disk and memory budget for a full-US build, state by state, from measured sizes.

Per state (the region unit Geofabrik publishes):
  fetch    the OSM extract (HEAD), its Terrarium tiles (outline tiles x the
           state's HEAD-sample mean), and the WorldCover cells it touches
           (HEAD; landcover.py --stream reads them over HTTP, so this is
           network, not disk);
  build    graph nodes, measured for the 17 counted states and otherwise fitted
           as the feasibility review did (nodes ~ a x urban km + b x rural km of
           FHWA HM-20 public road, least squares on relative error) but over all
           17; then the processed directory, less elevation.py's two rasters,
           at the per-node size measured for Colorado (1.31 KB, 522 MB /
           0.40M) and New England (1.36 KB, 1,082 MB / 0.79M), and the two
           rasters at 184-278 KB per bounding-box tile (New England 389 MB /
           2,120, Colorado 461 MB / 1,656);
  serve    the review's compact pack, 230 B per node, and its xz download,
           43-53 B per node (Colorado 17 MB / 0.40M, New England 42 MB / 0.79M);
  memory   elevation.py's mosaic peak, 37 B per pixel over the bounding box
           (the review's Colorado measurement, which matched its 4.0 GB RSS).

The peak working space of a region-by-region build is the largest single
state's transient (extract + tile cache + rasters + processed directory) plus
whatever earlier states' outputs are kept: every processed directory, or only
their compact packs.

Usage: python -I budget.py <results_dir> <fhwa_hm20_states.csv> <review_graph_counts.jsonl>
                           <metrics_dir> <out.csv>
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

KM_PER_MI = 1.609344
PROC_KB = (1.31, 1.36)
RASTER_KB = (184, 278)
PACK_B, XZ_B = 230, (43, 53)
NAME_TO_AB = {}


def main():
    res, fhwa_csv, review_counts, mdir, out = (Path(sys.argv[1]), sys.argv[2], sys.argv[3],
                                               Path(sys.argv[4]), sys.argv[5])
    sizes = {r["slug"]: r for r in csv.DictReader(open(res / "osm_extract_sizes.csv"))
             if r["scope"] == "in"}
    tiles = {r["name"].lower().replace(" ", "-"): r
             for r in csv.DictReader(open(res / "terrarium_tiles_by_state.csv"))}
    ab_of = {k: v["state"] for k, v in tiles.items()}
    head = defaultdict(list)
    for r in csv.DictReader(open(res / "terrarium_head_sample.csv")):
        if r["bytes"]:
            head[r["state"]].append(int(r["bytes"]))
    wc_bytes = defaultdict(int)
    for r in csv.DictReader(open(res / "worldcover_cells.csv")):
        if r["status"] == "200":
            for st in r["states"].split(";"):
                wc_bytes[st] += int(r["bytes"])
    fhwa = {r["state"].lower().replace(" ", "-"): r for r in csv.DictReader(open(fhwa_csv))}
    meas = {}
    for line in open(review_counts):
        d = json.loads(line)
        if "graph_nodes" in d:
            meas[d["label"]] = d["graph_nodes"]
    for p in mdir.glob("*.json"):
        d = json.load(open(p))
        meas[d["label"]] = d["graph_nodes"]
    X = {k: np.array([int(v["urban_mi"]) * KM_PER_MI, int(v["rural_mi"]) * KM_PER_MI])
         for k, v in fhwa.items()}
    names = sorted(meas)
    A = np.array([X[k] / meas[k] for k in names])
    coef = np.linalg.lstsq(A, np.ones(len(names)), rcond=None)[0]
    rows = []
    for slug, s in sorted(sizes.items()):
        t = tiles[slug]
        ab = ab_of[slug]
        nodes = meas.get(slug, float(X[slug] @ coef))
        mean_tile = float(np.mean(head[ab])) if head[ab] else float("nan")
        bbox = int(t["bbox_tiles"]) if t["bbox_tiles"] else int(t["outline_tiles"])
        rows.append({
            "state": ab, "slug": slug, "pbf_gb": int(s["bytes"]) / 1e9,
            "nodes": nodes, "nodes_measured": slug in meas,
            "terrarium_tiles": int(t["outline_tiles"]),
            "terrarium_gb": int(t["outline_tiles"]) * mean_tile / 1e9,
            "bbox_tiles": bbox, "mosaic_ram_gb": bbox * 65536 * 37 / 1e9,
            "worldcover_gb_touched": wc_bytes[ab] / 1e9,
            "processed_gb_lo": nodes * PROC_KB[0] * 1e3 / 1e9,
            "processed_gb_hi": nodes * PROC_KB[1] * 1e3 / 1e9,
            "rasters_gb_lo": bbox * RASTER_KB[0] * 1e3 / 1e9,
            "rasters_gb_hi": bbox * RASTER_KB[1] * 1e3 / 1e9,
            "pack_gb": nodes * PACK_B / 1e9,
            "pack_xz_gb_hi": nodes * XZ_B[1] / 1e9,
        })
    for r in rows:
        r["transient_gb_hi"] = (r["pbf_gb"] + r["terrarium_gb"] + r["rasters_gb_hi"]
                                + r["processed_gb_hi"])
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    tot = lambda k: sum(r[k] for r in rows)
    # Alaska's outline crosses the antimeridian and Hawaii's box spans the
    # whole island chain to Kure Atoll, so neither has a meaningful single box:
    # both need per-island or tiled elevation. The peaks are the lower 48's.
    lower = [r for r in rows if r["state"] not in ("AK", "HI")]
    big = max(lower, key=lambda r: r["transient_gb_hi"])
    ram = max(lower, key=lambda r: r["mosaic_ram_gb"])
    print(f"fit: {coef[0]:.2f} nodes per urban km, {coef[1]:.2f} per rural km, "
          f"{len(names)} states measured")
    print(f"US nodes {tot('nodes') / 1e6:.1f} M ({sum(r['nodes'] for r in rows if r['nodes_measured']) / 1e6:.1f} M measured)")
    print(f"fetch: OSM {tot('pbf_gb'):.2f} GB, Terrarium {tot('terrarium_gb'):.2f} GB (outline tiles, per state, "
          f"border tiles counted in each)")
    print(f"build: processed {tot('processed_gb_lo'):.0f}-{tot('processed_gb_hi'):.0f} GB, rasters "
          f"{tot('rasters_gb_lo'):.0f}-{tot('rasters_gb_hi'):.0f} GB")
    print(f"serve: compact {tot('pack_gb'):.2f} GB, xz {tot('pack_xz_gb_hi'):.2f} GB at most")
    print(f"largest lower-48 transient: {big['state']} {big['transient_gb_hi']:.1f} GB "
          f"(pbf {big['pbf_gb']:.2f}, tiles {big['terrarium_gb']:.2f}, rasters "
          f"{big['rasters_gb_hi']:.2f}, processed {big['processed_gb_hi']:.2f})")
    print(f"largest lower-48 mosaic: {ram['state']} {ram['mosaic_ram_gb']:.1f} GB at "
          f"{ram['bbox_tiles']} box tiles")
    keep_all = tot("processed_gb_hi") + tot("rasters_gb_hi") + big["transient_gb_hi"]
    keep_lo = tot("processed_gb_lo") + tot("rasters_gb_lo") + big["transient_gb_hi"]
    keep_packs = tot("pack_gb") + big["transient_gb_hi"]
    print(f"peak disk, keeping every processed directory and its rasters: {keep_lo:.0f}"
          f"-{keep_all:.0f} GB; keeping only compact packs: {keep_packs:.1f} GB")
    for r in sorted(rows, key=lambda r: -r["transient_gb_hi"])[:6]:
        print(f"  {r['state']} transient {r['transient_gb_hi']:.1f} GB, mosaic {r['mosaic_ram_gb']:.1f} GB, "
              f"nodes {r['nodes'] / 1e6:.2f} M{'' if r['nodes_measured'] else ' (fit)'}")


if __name__ == "__main__":
    main()
