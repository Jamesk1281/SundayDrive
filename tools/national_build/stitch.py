"""Stitch built regions into one processed directory, in processed-ne's schema.

Usage: stitch.py <config.json> <out_dir> [region ...]

Reads each region's graph part (graph_part.py) and access tables (extract.py) and
writes graph_edges, graph_nodes, turn_restrictions, access_ways and access_entries
into <out_dir>, plus stitch_report.json and per_state.csv. sidecars.py adds
closures.py's and state_roads.py's tables afterwards, because they name edges by
the rows written here.

What it does, in order:

1. **Checks that every way two regions both built was split identically.** A way
   near a border is whole in both regions' extracts (cut.py). With junctions
   counted nationally (junctions.py) both must cut it at the same nodes. Each
   region's edges of a way are hashed as a multiset of (u, v), and a way whose hash
   differs between two regions is a border defect: it would leave overlapping or
   missing edges. The scores of the two copies are compared too; within New England
   both are built in EPSG:26986 and agree exactly, elsewhere each region's own
   projection moves chunk boundaries by a few metres.
2. Keeps each edge from the region that owns its midpoint (regions.Owner), so every
   edge appears once.
3. Cuts graph.py's strongly connected component over the whole country
   (`graph.largest_component_mask`), on bare arrays.
4. Writes the edges region by region, in region-name order, as one GeoParquet. Row
   numbers are national from here on.
5. Builds the node table (graph.node_table, with every region's exit numbers) and
   resolves the turn restrictions (graph.resolve_restrictions) against the national
   rows, on just the edges that meet a restriction's via node.
6. Keeps each parking-lot component (access_ways) from the region owning the first
   vertex of its south-westernmost way, so a lot is kept whole and once, and
   renumbers components to be unique nationally.
"""
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pipeline"))
sys.path.insert(0, str(HERE))
import graph  # noqa: E402
import regions  # noqa: E402
from build import load_config  # noqa: E402

LIGHT = ["way_id", "u", "v", "oneway", "owner", "length_m", "score"]


def geo_metadata(path: Path) -> bytes:
    """The GeoParquet metadata geopandas wrote on a part, minus its bbox, which
    describes the part and not the stitched file."""
    md = json.loads(pq.read_schema(path).metadata[b"geo"])
    for col in md["columns"].values():
        col.pop("bbox", None)
    return json.dumps(md).encode()


class GeoWriter:
    """Append GeoDataFrames to one GeoParquet file, each cast to the schema of the
    file geopandas wrote for the first part (minus `drop`). Taken from the file,
    not from the first frame, because an empty or all-null column in one frame
    would otherwise fix that column's type as null for every frame after it."""

    def __init__(self, path: Path, like: Path, drop: tuple = ()):
        self.path, self.rows = path, 0
        schema = pq.read_schema(like)
        keep = [f for f in schema if f.name not in drop and not f.name.startswith("__")]
        self.schema = pa.schema(keep).with_metadata({b"geo": geo_metadata(like)})
        self.writer = pq.ParquetWriter(path, self.schema)

    def write(self, gdf: gpd.GeoDataFrame):
        df = pd.DataFrame(gdf.drop(columns="geometry"))
        df["geometry"] = shapely.to_wkb(gdf.geometry.values)
        table = pa.Table.from_pandas(df[self.schema.names], preserve_index=False)
        self.writer.write_table(table.cast(self.schema))
        self.rows += len(df)

    def close(self):
        if self.writer is not None:
            self.writer.close()


def check_borders(light: pd.DataFrame) -> dict:
    """Step 1: ways split differently by two regions, and score differences
    between the two copies of the same edge."""
    key = (light["u"].to_numpy().astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15)
           ^ light["v"].to_numpy().astype(np.uint64) * np.uint64(0xC2B2AE3D27D4EB4F))
    way = light["way_id"].to_numpy()
    region = light["region"].cat.codes.to_numpy()
    order = np.lexsort((region, way))
    way, region, key = way[order], region[order], key[order]
    start = np.flatnonzero(np.r_[True, (way[1:] != way[:-1]) | (region[1:] != region[:-1])])
    groups = pd.DataFrame({"way_id": way[start], "hsum": np.bitwise_xor.reduceat(key, start),
                           "n": np.diff(np.r_[start, len(key)])})
    per_way = groups.groupby("way_id").agg(regions=("n", "size"), hsums=("hsum", "nunique"),
                                           ns=("n", "nunique"))
    multi = per_way[per_way["regions"] > 1]
    split_differently = multi.index.to_numpy()[((multi["hsums"] > 1) | (multi["ns"] > 1)).to_numpy()]

    # Score of the owner's copy against every other region's copy of the same edge.
    owned = light[light["mine"]]
    other = light[~light["mine"] & (light["owner"] != "")]
    both = other.merge(owned[["way_id", "u", "v", "score", "length_m"]],
                       on=["way_id", "u", "v"], suffixes=("", "_owner"))
    both = both.drop_duplicates(["way_id", "u", "v", "region"])
    d_score = (both["score"] - both["score_owner"]).abs().to_numpy()
    d_len = (both["length_m"] / both["length_m_owner"] - 1).abs().to_numpy()
    q = lambda a, p: float(np.percentile(a, p)) if len(a) else 0.0
    return {
        "ways_in_two_or_more_regions": int(len(multi)),
        "of_them_split_differently": int(len(split_differently)),
        "split_differently_examples": split_differently[:20].tolist(),
        "edges_built_by_a_region_that_does_not_own_them": int(len(other)),
        "of_them_matched_to_the_owners_copy": int(len(both)),
        "score_abs_diff": {"p50": q(d_score, 50), "p99": q(d_score, 99),
                           "max": float(d_score.max()) if len(d_score) else 0.0,
                           "share_over_0.25": float((d_score > 0.25).mean()) if len(d_score) else 0.0},
        "length_rel_diff": {"p99": q(d_len, 99), "max": float(d_len.max()) if len(d_len) else 0.0},
    }


def access_tables(c: dict, regs: list, owner: regions.Owner, out: Path, report: dict):
    """Step 6."""
    # Owner indexes every region, not just the ones being stitched.
    names = [r.name for r in owner.regions]
    work = Path(c["work"])
    ways_w = entries_w = None
    offset, kept_c, total_c, kept_e = 0, 0, 0, 0
    rows = []
    for r in regs:
        ways = gpd.read_parquet(work / r.name / "access_ways.parquet")
        entries = gpd.read_parquet(work / r.name / "access_entries.parquet")
        if ways_w is None:
            ways_w = GeoWriter(out / "access_ways.parquet", work / r.name / "access_ways.parquet")
            entries_w = GeoWriter(out / "access_entries.parquet", work / r.name / "access_entries.parquet")
        first = shapely.get_point(ways.geometry.values, 0)
        rep = (pd.DataFrame({"component": ways["component"].to_numpy(),
                             "x": shapely.get_x(first), "y": shapely.get_y(first)})
               .sort_values(["component", "x", "y"]).drop_duplicates("component"))
        own = owner.of_lonlat(rep["x"].to_numpy(), rep["y"].to_numpy())
        mine = set(rep["component"].to_numpy()[own == names.index(r.name)].tolist())
        total_c += len(rep)
        kept_c += len(mine)
        w = ways[ways["component"].isin(mine)].copy()
        e = entries[entries["component"].isin(mine)].copy()
        w["component"] += offset
        e["component"] += offset
        ways_w.write(w)
        entries_w.write(e)
        kept_e += len(e)
        rows.append({"region": r.name, "ways": len(w), "entries": len(e)})
        offset += int(ways["component"].max()) + 1 if len(ways) else 0
    ways_w.close()
    entries_w.close()
    # Each region's rows are contiguous, in this order, so a reader can take one
    # region's lots without reading the country's (slice.py).
    pd.DataFrame(rows).to_csv(out / "access_per_region.csv", index=False)
    report["access"] = {"components_built": total_c, "components_kept": kept_c,
                        "ways": ways_w.rows, "entries": kept_e}


def main(config: str, out_dir: str, only: list[str]):
    if only[:1] == ["--access-only"]:
        c = load_config(config)
        regs = regions.load(c["states"], only[1:] or None)
        out = Path(out_dir)
        report = json.loads((out / "stitch_report.json").read_text())
        access_tables(c, regs, regions.Owner(regions.load(c["states"])), out, report)
        (out / "stitch_report.json").write_text(json.dumps(report, indent=1))
        print(json.dumps(report["access"]))
        return
    c = load_config(config)
    regs = regions.load(c["states"], only or None)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(c["work"])
    t0 = time.time()
    report = {"regions": [r.name for r in regs]}
    owner = regions.Owner(regions.load(c["states"]))

    light = []
    for r in regs:
        t = pd.read_parquet(work / r.name / "part_edges.parquet", columns=LIGHT)
        t["region"] = r.name
        light.append(t)
    light = pd.concat(light, ignore_index=True)
    light["mine"] = light["owner"].to_numpy() == light["region"].to_numpy()
    for col in ("oneway", "owner", "region"):
        light[col] = light[col].astype("category")
    print(f"read {len(light):,} region edges in {time.time() - t0:.0f}s", flush=True)

    report["borders"] = check_borders(light)
    print(json.dumps(report["borders"], indent=1), flush=True)

    in_scope = light["owner"].isin(report["regions"]).to_numpy()
    owned = light["mine"].to_numpy()
    report["outside_the_48_states_and_dc"] = {
        "edges": int((light["owner"] == "").sum()),
        "km": float(light.loc[light["owner"] == "", "length_m"].sum() / 1000)}
    if not in_scope[owned].all():
        raise SystemExit("an owned edge's owner is not among the regions being stitched")
    nat = light[owned].reset_index(drop=True)
    del light
    keep = graph.largest_component_mask(nat["u"].to_numpy(), nat["v"].to_numpy(), nat["oneway"])
    report["component"] = {"edges_owned": int(len(nat)), "edges_kept": int(keep.sum()),
                           "km_owned": float(nat["length_m"].sum() / 1000),
                           "km_kept": float(nat.loc[keep, "length_m"].sum() / 1000)}
    print(f"component: {keep.sum():,} of {len(nat):,} owned edges in {time.time() - t0:.0f}s", flush=True)

    # Step 4 and the per-region pieces of step 5.
    edges_w, nodes, exits, written = None, [], {}, []
    per_region = []
    start = 0
    for r in regs:
        part = gpd.read_parquet(work / r.name / "part_edges.parquet")
        mine = (part["owner"] == r.name).to_numpy()
        n_mine = int(mine.sum())
        k = keep[start:start + n_mine]
        start += n_mine
        e = part[mine][k].reset_index(drop=True)
        ex = pd.read_parquet(work / r.name / "part_exits.parquet")
        exits.update(zip(ex["node_id"].tolist(), ex["exit_ref"].tolist()))
        written.append(e[["way_id", "u", "v"]])
        if len(e):
            nodes.append(graph.node_table(e))
        per_region.append({"region": r.name, "state": r.state, "edges": len(e),
                           "km": float(e["length_m"].sum() / 1000),
                           "nodes": int(len(np.unique(np.r_[e["u"].to_numpy(), e["v"].to_numpy()])))})
        e = e.drop(columns=["way_id", "owner"])
        if edges_w is None:
            edges_w = GeoWriter(out / "graph_edges.parquet", work / r.name / "part_edges.parquet",
                                drop=("way_id", "owner"))
        edges_w.write(e)
        print(f"  {r.name}: {len(e):,} edges", flush=True)
    edges_w.close()
    if start != len(nat):
        raise SystemExit("the parts changed while stitching")

    nodes = pd.concat(nodes, ignore_index=True).drop_duplicates("node_id").sort_values("node_id")
    nodes["exit_ref"] = nodes["node_id"].map(exits).fillna("")
    nodes.reset_index(drop=True).to_parquet(out / "graph_nodes.parquet")

    rows = pd.concat(written, ignore_index=True)
    restrictions = pd.concat([pd.read_parquet(work / r.name / "part_restrictions.parquet") for r in regs],
                             ignore_index=True).drop_duplicates()
    via = restrictions["via_node"].unique()
    at_via = np.flatnonzero(np.isin(rows["u"].to_numpy(), via) | np.isin(rows["v"].to_numpy(), via))
    sub = rows.iloc[at_via].reset_index(drop=True)
    banned, unresolved = graph.resolve_restrictions(
        sub, list(restrictions[["kind", "from_way", "via_node", "to_way"]].itertuples(index=False, name=None)))
    banned["from_edge"] = at_via[banned["from_edge"].to_numpy()]
    banned["to_edge"] = at_via[banned["to_edge"].to_numpy()]
    banned.to_parquet(out / "turn_restrictions.parquet")
    report["graph"] = {"edges": edges_w.rows, "nodes": len(nodes),
                       "exit_numbers": int((nodes["exit_ref"] != "").sum()),
                       "restrictions_read": len(restrictions), "unresolved": unresolved,
                       "forbidden_turns": len(banned)}
    print(json.dumps(report["graph"]), flush=True)

    access_tables(c, regs, owner, out, report)
    pr = pd.DataFrame(per_region)
    pr.to_csv(out / "per_region.csv", index=False)
    report["seconds"] = round(time.time() - t0)
    (out / "stitch_report.json").write_text(json.dumps(report, indent=1))
    print(f"stitched in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
