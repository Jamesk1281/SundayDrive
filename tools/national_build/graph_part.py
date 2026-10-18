"""One region's share of the national graph: its edges, scored, before any component cut.

Usage: graph_part.py <crs> <region.osm.pbf> <processed_dir> <junctions.npy> <states.parquet> <region>

Runs graph.py's own edge building and scoring (`build_scored_edges`) on the region's
extract, with the junctions counted over the whole national PBF, and writes beside
the region's other outputs:

  part_edges.parquet         every edge the extract yields, `way_id` kept, plus
                             `owner`: the region owning its midpoint (regions.py),
                             "" for one outside the 48 states and DC. The ring's
                             edges are kept so that the stitch can check every
                             edge two regions both built against itself.
  part_restrictions.parquet  graph.py's via-node turn restrictions, unresolved
  part_exits.parquet         motorway exit numbers by node

The strongly connected component, the node table and the restrictions are made
once, nationally, by stitch.py: each depends on roads outside any one region.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pipeline"))
sys.path.insert(0, str(HERE))


def main(crs, pbf, processed_dir, junctions_path, states_path, region_name):
    import common
    common.CRS_METERS = int(crs) if crs.isdigit() else crs
    import graph
    import regions

    d = Path(processed_dir)
    t0 = time.time()
    junctions = np.load(junctions_path)
    edges, h = graph.build_scored_edges(pbf, processed_dir, junctions)

    all_regions = regions.load(states_path)
    names = np.array([r.name for r in all_regions] + [""])
    owner = regions.Owner(all_regions).of_lines(np.asarray(edges.geometry.values))
    edges["owner"] = names[owner]
    mine = edges["owner"] == region_name
    foreign = edges["owner"] == ""
    km = edges["length_m"] / 1000
    print(f"owned: {mine.sum():,} of {len(edges):,} edges, {km[mine].sum():,.0f} of "
          f"{km.sum():,.0f} km; outside the 48 states and DC: {foreign.sum():,} edges, "
          f"{km[foreign].sum():,.0f} km; in {time.time() - t0:.0f}s")
    edges.to_parquet(d / "part_edges.parquet")
    pd.DataFrame(h.restrictions, columns=["kind", "from_way", "via_node", "to_way"]) \
        .to_parquet(d / "part_restrictions.parquet")
    pd.DataFrame({"node_id": np.fromiter(h.exit_refs.keys(), dtype=np.int64, count=len(h.exit_refs)),
                  "exit_ref": list(h.exit_refs.values())}).to_parquet(d / "part_exits.parquet")
    skipped = pd.Series(h.skipped_restrictions, dtype="int64")
    print(f"{len(h.restrictions):,} via-node restrictions read, skipped {skipped.to_dict()}")
    print(f"wrote part_edges, part_restrictions, part_exits in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(*sys.argv[1:7])
