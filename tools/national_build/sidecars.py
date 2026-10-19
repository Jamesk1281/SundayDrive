"""closures.py's and state_roads.py's tables for a stitched graph, on national edge ids.

Usage: sidecars.py <config.json> <out_dir> <raw_dir> [region ...]   (raw_dir holds state-roads/)

Both stages name edges by their row in graph_edges.parquet, and both are run
unmodified. closures.py reads its PBF with an in-memory location index, which a
national PBF does not fit, so it runs once per region, on that region's PBF and
on a slice of the national graph written to <out_dir>/sidecars/<region>:

- every edge the region owns, which are the only rows kept from its output;
- every other edge that meets one of their end nodes. closures.py decides what a
  barrier on a node closes from how many edges meet there (`_place_barriers`), so
  the slice must hold all of them for every node an owned edge ends at.

Each output row's `edge` is mapped from the slice's row back to the national row,
and a row is kept only from the region that owns its edge. A barrier where two
regions' edges meet is placed by both, from the same national edges, and each keeps
its own edge's row.

state_roads.py runs once on New England's slice, built the same way, with the six
states' roads.parquet stacked for its surface override. Its rules cover NH, VT, MA
and ME. Every other state gets an empty table with its columns (the contract in
docs/national-build.md §5).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
PIPELINE = HERE.parents[1] / "pipeline"
sys.path.insert(0, str(PIPELINE))
sys.path.insert(0, str(HERE))
import regions  # noqa: E402
from build import PY, load_config  # noqa: E402

COLUMNS = ["u", "v", "length_m", "score", "name", "unpaved_frac", "highway", "ref", "geometry"]
TABLES = ["seasonal_closures", "closed_to_cars", "osm_unpaved"]
NEW_ENGLAND_STATE_ROADS = ("ct", "ma", "me", "nh", "ri", "vt")


class National:
    def __init__(self, out: Path):
        self.path = out / "graph_edges.parquet"
        self.pf = pq.ParquetFile(self.path)
        t = self.pf.read(columns=["u", "v"])
        self.u = t["u"].to_numpy()
        self.v = t["v"].to_numpy()
        sizes = [self.pf.metadata.row_group(i).num_rows for i in range(self.pf.num_row_groups)]
        self.group_start = np.r_[0, np.cumsum(sizes)]
        pr = pd.read_csv(out / "per_region.csv")
        starts = np.r_[0, np.cumsum(pr["edges"].to_numpy())]
        self.rows = {name: (int(a), int(b)) for name, a, b in zip(pr["region"], starts[:-1], starts[1:])}

    def slice_rows(self, names: list[str]) -> tuple[np.ndarray, np.ndarray]:
        """(rows of the slice, which of them are owned by `names`), sorted."""
        owned = np.concatenate([np.arange(*self.rows[n]) for n in names])
        ends = np.unique(np.r_[self.u[owned], self.v[owned]])
        touch = np.flatnonzero(np.isin(self.u, ends) | np.isin(self.v, ends))
        rows = np.union1d(owned, touch)
        return rows, np.isin(rows, owned)

    def read(self, rows: np.ndarray) -> gpd.GeoDataFrame:
        groups = np.unique(np.searchsorted(self.group_start, rows, side="right") - 1)
        cols = [c for c in COLUMNS if c in self.pf.schema_arrow.names]
        parts, offsets = [], []
        for g in groups:
            parts.append(self.pf.read_row_group(int(g), columns=cols))
            offsets.append(self.group_start[g])
        import pyarrow as pa
        table = pa.concat_tables(parts)
        base = np.concatenate([np.arange(o, o + p.num_rows) for o, p in zip(offsets, parts)])
        take = np.searchsorted(base, rows)
        if not (base[take] == rows).all():
            raise SystemExit("a slice row was not found in the row groups read")
        df = table.take(take).to_pandas()
        return gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkb(df.pop("geometry"), crs=4326))


def write_slice(nat: National, names: list[str], d: Path) -> tuple[np.ndarray, np.ndarray]:
    d.mkdir(parents=True, exist_ok=True)
    rows, owned = nat.slice_rows(names)
    nat.read(rows).to_parquet(d / "graph_edges.parquet")
    np.save(d / "national_rows.npy", rows)
    np.save(d / "owned.npy", owned)
    return rows, owned


def remap(table: pd.DataFrame, rows: np.ndarray, owned: np.ndarray) -> pd.DataFrame:
    local = table["edge"].to_numpy()
    table = table[owned[local]].copy()
    table["edge"] = rows[table["edge"].to_numpy()]
    return table


def run(cmd: list[str], log: Path) -> float:
    t0 = time.time()
    with open(log, "w") as f:
        res = subprocess.run(["/usr/bin/time", "-l", *cmd], stdout=f, stderr=subprocess.STDOUT)
    if res.returncode:
        raise SystemExit(f"{cmd[1]} failed, see {log}:\n" + log.read_text()[-2000:])
    return time.time() - t0


def main(config: str, out_dir: str, state_raw: str, only: list[str]):
    c = load_config(config)
    regs = regions.load(c["states"], only or None)
    out = Path(out_dir)
    nat = National(out)
    t0 = time.time()
    collected = {t: [] for t in TABLES}
    timing = {}
    for r in regs:
        d = out / "sidecars" / r.name
        if all((d / f"{t}.parquet").exists() for t in TABLES):
            rows, owned = np.load(d / "national_rows.npy"), np.load(d / "owned.npy")
            for t in TABLES:
                collected[t].append(remap(pd.read_parquet(d / f"{t}.parquet"), rows, owned))
            continue
        rows, owned = write_slice(nat, [r.name], d)
        timing[r.name] = run([PY, str(HERE / "closures_run.py"), str(Path(c["pbf_dir"]) / f"{r.name}.osm.pbf"),
                              str(d)], d / "closures.log")
        for t in TABLES:
            collected[t].append(remap(pd.read_parquet(d / f"{t}.parquet"), rows, owned))
        print(f"  {r.name}: slice {len(rows):,} rows ({owned.sum():,} owned), closures "
              f"{timing[r.name]:.0f}s", flush=True)

    report = {}
    for t in TABLES:
        table = pd.concat(collected[t], ignore_index=True)
        dedupe = {"seasonal_closures": ["edge", "rule", "node_id", "start_month", "start_day",
                                        "end_month", "end_day"],
                  "closed_to_cars": ["edge", "rule", "osm_type", "osm_id"],
                  "osm_unpaved": ["edge"]}[t]
        table = table.drop_duplicates(dedupe).sort_values(dedupe).reset_index(drop=True)
        table.to_parquet(out / f"{t}.parquet", index=False)
        report[t] = len(table)

    ne = [r.name for r in regs if r.name in NEW_ENGLAND_STATE_ROADS]
    d = out / "sidecars" / "state_roads"
    if ne:
        rows, owned = write_slice(nat, ne, d)
        roads = pd.concat([gpd.read_parquet(Path(c["work"]) / n / "roads.parquet",
                                            columns=["way_id", "surface", "geometry"]) for n in ne])
        roads.drop_duplicates("way_id").drop(columns="way_id").to_parquet(d / "roads.parquet")
        timing["state_roads"] = run([PY, str(PIPELINE / "state_roads.py"), "build", state_raw, str(d)],
                                    d / "state_roads.log")
        table = remap(pd.read_parquet(d / "state_road_class.parquet"), rows, owned)
    else:
        table = pd.read_parquet(Path(c["state_road_columns_from"])).iloc[:0]
    table.sort_values("edge").reset_index(drop=True).to_parquet(out / "state_road_class.parquet", index=False)
    report["state_road_class"] = len(table)
    report["seconds"] = timing
    (out / "sidecars_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report), f"in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
