"""The junctions of the whole PBF, counted once, so every region splits its roads alike.

Usage: junctions.py <input.osm.pbf> <out.npy>

graph.py splits a way into edges at every node that two or more drivable-way
references share (`GraphHandler.node_count`), counted from the ways in the PBF it
reads. Built region by region, a node where a road in this region meets a road only
the next region's extract carries is counted once on this side, so the same road is
cut into different edges on each side of the border (docs/national-build.md §3).
This counts the references over every drivable way in the national PBF, each way
once, with graph.py's own filter, and writes the sorted ids whose count is 2 or more.
`graph.build_scored_edges(..., junctions=)` then treats each as a junction.

A way's references are counted the way graph.py counts them: every reference, so a
closed way's first node, listed twice, is a junction, and a way with fewer than two
nodes is skipped. graph.py also drops a reference whose location is invalid. A
reference-complete extract has none, which the region build checks (the count of
nodes promoted to junctions that its own extract does not already count is printed).
"""
import sys
import time
from array import array
from pathlib import Path

import numpy as np
import osmium

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline"))
from common import DRIVABLE, PRIVATE_ACCESS  # noqa: E402


def drivable_refs(pbf: str) -> tuple[np.ndarray, int]:
    """Every node reference of every way graph.py would keep, and the way count."""
    refs = array("q")
    ways = 0
    fp = (osmium.FileProcessor(pbf, osmium.osm.WAY)
          .with_filter(osmium.filter.TagFilter(*(("highway", hw) for hw in sorted(DRIVABLE)))))
    for w in fp:
        tags = w.tags
        if tags.get("access") in PRIVATE_ACCESS and tags.get("motor_vehicle") != "yes":
            continue
        if len(w.nodes) < 2:
            continue
        refs.extend(n.ref for n in w.nodes)
        ways += 1
    return np.frombuffer(refs, dtype=np.int64), ways


def main(pbf: str, out: str):
    t0 = time.time()
    refs, ways = drivable_refs(pbf)
    print(f"{ways:,} drivable ways, {len(refs):,} node references in {time.time() - t0:.0f}s")
    ids, counts = np.unique(refs, return_counts=True)
    junctions = ids[counts >= 2]
    np.save(out, junctions)
    print(f"{len(ids):,} distinct nodes, {len(junctions):,} junctions; wrote {out} "
          f"in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
