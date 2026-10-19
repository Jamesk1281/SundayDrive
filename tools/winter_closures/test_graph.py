"""A small road graph around each seasonal road in docs/us-map-data-findings.md
§4, for checking closures.py where no national build exists yet.

Clips each road's box (tools/us_map_data/seasonal_roads.json), widened by
MARGIN_DEG, and the extra areas in AREAS, out of the state extracts with
`osmium extract`, merges the clips, and splits the drivable ways into edges
with graph.py's own handler and `build_edges`. Two things differ from a real
build, and neither touches what closures.py reads: there is no scoring chain,
so `score` is 0, and no largest-component cut, since the clips are separate
islands. Junctions near a clip's edge can split differently from a full
build; the roads checked sit well inside their clips.

Writes graph_edges.parquet and graph_nodes.parquet into <out_dir>, and the
merged extract as <out_dir>/clips.osm.pbf for closures.py to scan.

Usage: python test_graph.py <repo_pipeline_dir> <pbf_dir> <out_dir>
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import geopandas as gpd  # noqa: E402
from pyproj import Transformer  # noqa: E402

from common import CRS_METERS  # noqa: E402
from graph import GraphHandler, build_edges, node_table  # noqa: E402

MARGIN_DEG = 0.2
ROADS = Path(__file__).resolve().parent.parent / "us_map_data/seasonal_roads.json"
# Areas beyond the roads' own boxes: whole parks whose every road the window
# table speaks for, and the one forest docs/us-map-data-findings.md §6.4
# measured MVUM against (Grand Mesa, Uncompahgre and Gunnison NFs).
AREAS = {
    "yellowstone": ("wyoming", (-111.20, 44.10, -109.80, 45.12)),
    "yellowstone_mt": ("montana", (-111.20, 44.90, -109.80, 45.12)),
    "gmug": ("colorado", (-108.90, 37.75, -106.30, 39.30)),
    "kuwohi_nc": ("north-carolina", (-83.70, 35.45, -83.20, 35.75)),
    "lassen_park": ("california", (-121.65, 40.35, -121.20, 40.60)),
    "crater_lake_park": ("oregon", (-122.30, 42.80, -121.95, 43.10)),
    "rmnp": ("colorado", (-105.95, 40.15, -105.45, 40.55)),
    "grand_teton": ("wyoming", (-110.95, 43.45, -110.40, 44.15)),
}


def regions():
    out = dict(AREAS)
    for r in json.loads(ROADS.read_text()):
        w, s, e, n = r["bbox"]
        out[r["id"]] = (r["state"], (w - MARGIN_DEG, s - MARGIN_DEG,
                                     e + MARGIN_DEG, n + MARGIN_DEG))
    return out


def main(pbf_dir: str, out_dir: str):
    out = Path(out_dir)
    clips = out / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    parts = []
    for name, (state, box) in sorted(regions().items()):
        pbf = Path(pbf_dir) / f"{state}-latest.osm.pbf"
        if state == "new-hampshire":
            continue        # New England is checked against its own build
        part = clips / f"{name}.osm.pbf"
        subprocess.run(["osmium", "extract", "-b", ",".join(map(str, box)), str(pbf),
                        "-o", str(part), "--overwrite", "-s", "complete_ways"], check=True)
        parts.append(str(part))
    merged = out / "clips.osm.pbf"
    subprocess.run(["osmium", "merge", *parts, "-o", str(merged), "--overwrite"], check=True)

    h = GraphHandler()
    h.apply_file(str(merged), locations=True, idx="flex_mem")
    fwd = Transformer.from_crs(4326, CRS_METERS, always_xy=True)
    edges = gpd.GeoDataFrame(build_edges(h.ways, h.node_count, fwd.transform, h.controls),
                             geometry="geometry", crs=4326)
    edges["score"] = 0.0
    edges = edges.drop(columns=["way_id"]).reset_index(drop=True)
    edges.to_parquet(out / "graph_edges.parquet")
    node_table(edges).to_parquet(out / "graph_nodes.parquet")
    print(f"{len(edges):,} edges, {edges['length_m'].sum() / 1000:,.0f} km, from "
          f"{len(parts)} clips")


if __name__ == "__main__":
    main(sys.argv[2], sys.argv[3])
