"""Rerun closures.py over every region into a new processed directory, without
touching the one being served.

Usage: sidecars_next.py <config.json> <processed-us> <processed-us-next> [--jobs N] [region ...]

tools/national_build/sidecars.py writes each region's slice of the national graph
into <out_dir>/sidecars/<region> and then runs closures.py on it. The slices
depend only on graph_edges.parquet, which a closures change leaves alone, so
this reads the slices already in <processed-us>/sidecars (3.9 GB) instead of
writing them again, and has closures.py write its three tables into
<processed-us-next>/sidecars/<region> (closures.py's own `out_dir`). The rows
are then mapped to national edge ids and deduplicated exactly as sidecars.py
does, with its `remap`.

Everything else in <processed-us> is linked into <processed-us-next> by
absolute symlink, state_road_class.parquet included: state_roads.py reads no
ford or barrier rule. Nothing is written under <processed-us>.

SUNDAYDRIVE_FEDERAL must point at data/raw/federal, because the region PBFs
are in data/national/regions, which has no federal/ beside it.
"""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "national_build"
sys.path.insert(0, str(HERE.parents[1] / "pipeline"))
sys.path.insert(0, str(BUILD))
import regions  # noqa: E402
from build import load_config  # noqa: E402
from sidecars import TABLES, remap  # noqa: E402

DEDUPE = {"seasonal_closures": ["edge", "rule", "node_id", "start_month", "start_day",
                                "end_month", "end_day"],
          "closed_to_cars": ["edge", "rule", "osm_type", "osm_id"],
          "osm_unpaved": ["edge"]}
REGENERATED = {f"{t}.parquet" for t in TABLES} | {"sidecars", "sidecars_report.json"}


def link_the_rest(src: Path, out: Path):
    for p in sorted(src.iterdir()):
        if p.name in REGENERATED or p.name.startswith("."):
            continue
        target = out / p.name
        if target.is_symlink() or target.exists():
            if not target.is_symlink() or os.readlink(target) != str(p.resolve()):
                raise SystemExit(f"{target} exists and is not a link to {p}")
            continue
        target.symlink_to(p.resolve())


def run_region(name: str, pbf: Path, src: Path, out: Path) -> float:
    d = out / "sidecars" / name
    if all((d / f"{t}.parquet").exists() for t in TABLES):
        return 0.0
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(d / "closures.log", "w") as f:
        res = subprocess.run(["/usr/bin/time", "-l", sys.executable,
                              str(BUILD / "closures_run.py"), str(pbf),
                              str(src / "sidecars" / name), str(d)],
                             stdout=f, stderr=subprocess.STDOUT)
    if res.returncode:
        raise SystemExit(f"{name} failed, see {d / 'closures.log'}")
    print(f"  {name}: closures {time.time() - t0:.0f}s", flush=True)
    return time.time() - t0


def main(argv):
    jobs = 1
    if "--jobs" in argv:
        i = argv.index("--jobs")
        jobs = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    config, src, out, only = argv[0], Path(argv[1]), Path(argv[2]), argv[3:]
    if not os.environ.get("SUNDAYDRIVE_FEDERAL"):
        raise SystemExit("set SUNDAYDRIVE_FEDERAL to data/raw/federal")
    if out.resolve() == src.resolve():
        raise SystemExit("the output must not be the served directory")
    c = load_config(config)
    regs = regions.load(c["states"], only or None)
    out.mkdir(parents=True, exist_ok=True)
    link_the_rest(src, out)
    t0 = time.time()
    with ThreadPoolExecutor(jobs) as pool:
        timing = dict(zip([r.name for r in regs], pool.map(
            lambda r: run_region(r.name, Path(c["pbf_dir"]) / f"{r.name}.osm.pbf", src, out),
            regs)))
    if only:
        return
    collected = {t: [] for t in TABLES}
    for r in regs:
        s = src / "sidecars" / r.name
        rows, owned = np.load(s / "national_rows.npy"), np.load(s / "owned.npy")
        for t in TABLES:
            collected[t].append(remap(pd.read_parquet(out / "sidecars" / r.name / f"{t}.parquet"),
                                      rows, owned))
    report = {}
    for t in TABLES:
        table = pd.concat(collected[t], ignore_index=True)
        table = table.drop_duplicates(DEDUPE[t]).sort_values(DEDUPE[t]).reset_index(drop=True)
        table.to_parquet(out / f"{t}.parquet", index=False)
        report[t] = len(table)
    report["seconds"] = timing
    (out / "sidecars_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report), f"in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1:])
