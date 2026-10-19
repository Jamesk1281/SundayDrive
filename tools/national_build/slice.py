"""Cut some regions' edges out of a stitched directory into one the Router can load.

Usage: slice.py <stitched_dir> <states.parquet> <out_dir> <region> [region ...]

Reads only the row groups that hold the regions' rows: the country's edges and
parking lots do not fit in memory at once.

Today's Router holds its whole graph in memory and cannot load the country's, so
the New England check (docs/national-build.md §4) routes on the national graph's
New England part. That is every edge the six states' regions own, in the national
rows' order, cut again to the strongly connected component (a few roads that
reach the rest of New England only through New York drop out), with every table
that names an edge renumbered to match: turn restrictions, closures, unpaved,
state road classes. Nodes are those the edges end at; parking lots are the ones
stitch.py kept from these regions.
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pipeline"))
sys.path.insert(0, str(HERE))
import graph  # noqa: E402

EDGE_TABLES = ["closed_to_cars", "seasonal_closures", "osm_unpaved", "state_road_class"]


def rows_of(path: Path, rows: np.ndarray) -> gpd.GeoDataFrame:
    """Just these rows of a GeoParquet, reading only the row groups that hold them."""
    pf = pq.ParquetFile(path)
    sizes = [pf.metadata.row_group(i).num_rows for i in range(pf.num_row_groups)]
    start = np.r_[0, np.cumsum(sizes)]
    groups = np.unique(np.searchsorted(start, rows, side="right") - 1)
    table = pa.concat_tables([pf.read_row_group(int(g)) for g in groups])
    base = np.concatenate([np.arange(start[g], start[g + 1]) for g in groups])
    df = table.take(np.searchsorted(base, rows)).to_pandas()
    order = list(df.columns)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkb(df.pop("geometry"), crs=4326))
    return gdf[order]


def ranges(table: pd.DataFrame, column: str, names: list[str]) -> np.ndarray:
    starts = np.r_[0, np.cumsum(table[column].to_numpy())]
    at = {n: (a, b) for n, a, b in zip(table["region"], starts[:-1], starts[1:])}
    return np.concatenate([np.arange(*at[n]) for n in sorted(names)])


def main(src: str, states: str, out_dir: str, names: list[str]):
    s, out = Path(src), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = ranges(pd.read_csv(s / "per_region.csv"), "edges", names)
    edges = rows_of(s / "graph_edges.parquet", rows)
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

    # Parking lots: the regions' own rows, which stitch.py wrote contiguously.
    access = pd.read_csv(s / "access_per_region.csv")
    for table, column in (("access_ways", "ways"), ("access_entries", "entries")):
        rows_of(s / f"{table}.parquet", ranges(access, column, names)).to_parquet(out / f"{table}.parquet")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
