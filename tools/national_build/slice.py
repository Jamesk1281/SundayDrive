"""Cut some regions' edges out of a stitched directory into one the Router can load.

Usage: slice.py <stitched_dir> <states.parquet> <out_dir> <region> [region ...]

Today's Router holds its whole graph in memory and cannot load the country's, so
the New England check (docs/national-build.md §4) routes on the national graph's
New England part. That is every edge the six states' regions own, in the national
rows' order, cut again to the strongly connected component (a few roads that
reach the rest of New England only through New York drop out), with every table
that names an edge renumbered to match: turn restrictions, closures, unpaved,
state road classes. Nodes are those the edges end at; parking-lot components are
those whose first vertex lies in the regions.
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pipeline"))
sys.path.insert(0, str(HERE))
import graph  # noqa: E402
import regions  # noqa: E402

EDGE_TABLES = ["closed_to_cars", "seasonal_closures", "osm_unpaved", "state_road_class"]


def main(src: str, states: str, out_dir: str, names: list[str]):
    s, out = Path(src), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pr = pd.read_csv(s / "per_region.csv")
    starts = np.r_[0, np.cumsum(pr["edges"].to_numpy())]
    ranges = {n: (a, b) for n, a, b in zip(pr["region"], starts[:-1], starts[1:])}
    rows = np.concatenate([np.arange(*ranges[n]) for n in sorted(names)])
    edges = gpd.read_parquet(s / "graph_edges.parquet").iloc[rows].reset_index(drop=True)
    keep = graph.largest_component_mask(edges["u"].to_numpy(), edges["v"].to_numpy(), edges["oneway"])
    rows, edges = rows[keep], edges[keep].reset_index(drop=True)
    new = pd.Series(np.arange(len(rows)), index=rows)
    print(f"{len(edges):,} edges ({(~keep).sum():,} outside the slice's component)")
    edges.to_parquet(out / "graph_edges.parquet")
    ends = np.unique(np.r_[edges["u"].to_numpy(), edges["v"].to_numpy()])
    nodes = pd.read_parquet(s / "graph_nodes.parquet")
    nodes[nodes["node_id"].isin(ends)].reset_index(drop=True).to_parquet(out / "graph_nodes.parquet")

    tr = pd.read_parquet(s / "turn_restrictions.parquet")
    tr = tr[tr["from_edge"].isin(rows) & tr["to_edge"].isin(rows)].copy()
    tr["from_edge"] = new[tr["from_edge"].to_numpy()].to_numpy()
    tr["to_edge"] = new[tr["to_edge"].to_numpy()].to_numpy()
    tr.reset_index(drop=True).to_parquet(out / "turn_restrictions.parquet")
    for t in EDGE_TABLES:
        if (s / f"{t}.parquet").exists():
            tab = pd.read_parquet(s / f"{t}.parquet")
            tab = tab[tab["edge"].isin(rows)].copy()
            tab["edge"] = new[tab["edge"].to_numpy()].to_numpy()
            tab.reset_index(drop=True).to_parquet(out / f"{t}.parquet", index=False)

    all_regions = regions.load(states)
    owner = regions.Owner(all_regions)
    wanted = [i for i, r in enumerate(all_regions) if r.name in names]
    ways = gpd.read_parquet(s / "access_ways.parquet")
    first = shapely.get_point(ways.geometry.values, 0)
    inside = np.isin(owner.of_lonlat(shapely.get_x(first), shapely.get_y(first)), wanted)
    comps = set(ways["component"].to_numpy()[inside].tolist())
    ways[ways["component"].isin(comps)].reset_index(drop=True).to_parquet(out / "access_ways.parquet")
    entries = gpd.read_parquet(s / "access_entries.parquet")
    entries[entries["component"].isin(comps)].reset_index(drop=True).to_parquet(out / "access_entries.parquet")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
