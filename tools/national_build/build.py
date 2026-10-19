"""Build regions with the unmodified pipeline, re-runnably, a few at a time.

Usage:
  build.py <config.json> [region ...]          those named, or every region not yet
                                               built, each as soon as cut.py writes its PBF
  build.py <config.json> --one <region>        one region, in this process

config.json names the inputs and outputs (paths absolute or relative to the file):
  {"pbf_dir": region PBFs from cut.py, "work": where each region's processed
   directory goes, "junctions": junctions.py's output, "states": the state polygons,
   "landmarks": padus_landmarks.py's output, "jobs": regions at once,
   "mem_gb": the memory they may use together, "keep": [regions whose
   intermediates are kept]}

Each region runs, in its own projection (regions.py) and in the order
tools/national_scoring/build_region.sh uses: extract.py, elevation.py (over the
ring's box), terrain.py, landcover.py, protected.py, score.py, then graph_part.py.
A stage whose output exists is skipped, so a failed run resumes where it stopped.
Every stage's wall time and peak RSS go to <work>/<region>/stages.json.

The Terrarium and WorldCover tiles are cached once for every region, in
<work>/raw (elevation.py and landcover.py put their caches beside the processed
directory). Once a region's graph part is written its rasters and layers are
deleted unless the region is in "keep" (New England's six, whose roads.parquet
state_roads.py reads); the access tables and the parts stay.
"""
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regions  # noqa: E402

PY = sys.executable
# Peak RSS per GB of region PBF, and per mosaic pixel. extract.py: Colorado's
# 385 MB took ~2.6 GB (docs/us-map-data-findings.md §2 has 6.7 GB per GB for the
# whole pipeline). elevation.py's mosaic: 37 B per pixel (the same section).
GB_PER_PBF_GB = 7.0
MOSAIC_B_PER_PX = 37
KEEP_ALWAYS = {"access_ways.parquet", "access_entries.parquet",
               "part_edges.parquet", "part_restrictions.parquet", "part_exits.parquet",
               "stages.json"}


def load_config(path: str) -> dict:
    p = Path(path).resolve()
    c = json.loads(p.read_text())
    for k in ("pbf_dir", "work", "junctions", "states", "landmarks"):
        c[k] = str((p.parent / c[k]).resolve())
    c.setdefault("jobs", 2)
    c.setdefault("mem_gb", 14)
    c.setdefault("keep", [])
    return c


def mosaic_gb(region: regions.Region, zoom: int = 11) -> float:
    w, s, e, n = region.bbox
    tx = lambda lon: (lon + 180) / 360 * 2 ** zoom
    ty = lambda lat: (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 2 ** zoom
    tiles = (math.floor(tx(e)) - math.floor(tx(w)) + 1) * (math.floor(ty(s)) - math.floor(ty(n)) + 1)
    return tiles * 256 * 256 * MOSAIC_B_PER_PX / 1e9


def need_gb(region: regions.Region, pbf: Path) -> float:
    return max(GB_PER_PBF_GB * pbf.stat().st_size / 1e9, mosaic_gb(region)) + 1.0


def run_stage(d: Path, name: str, cmd: list[str], done: Path, record: dict):
    if done.exists():
        return
    log = d / "logs" / f"{name}.log"
    t0 = time.time()
    with open(log, "w") as f:
        res = subprocess.run(["/usr/bin/time", "-l", *cmd], stdout=f, stderr=subprocess.STDOUT)
    wall = time.time() - t0
    text = log.read_text()
    rss = [int(ln.split()[0]) for ln in text.splitlines() if "maximum resident set size" in ln]
    record[name] = {"wall_s": round(wall, 1), "peak_rss_gb": round(rss[-1] / 1e9, 2) if rss else None,
                    "returncode": res.returncode}
    (d / "stages.json").write_text(json.dumps(record, indent=1))
    if res.returncode or not done.exists():
        raise SystemExit(f"{d.name}: {name} failed (see {log}):\n" + text[-2000:])
    print(f"  {d.name}: {name} {wall:.0f}s, {record[name]['peak_rss_gb']} GB", flush=True)


def building(d: Path) -> bool:
    """Whether a live process holds this region's lock."""
    lock = d / ".building"
    if not lock.exists():
        return False
    try:
        os.kill(int(lock.read_text()), 0)
        return True
    except (ValueError, ProcessLookupError):
        return False


def build_one(c: dict, region: regions.Region):
    d = Path(c["work"]) / region.name
    (d / "logs").mkdir(parents=True, exist_ok=True)
    if building(d):
        raise SystemExit(f"{region.name} is already being built")
    (d / ".building").write_text(str(os.getpid()))
    try:
        _build_one(c, region, d)
    finally:
        (d / ".building").unlink(missing_ok=True)


def _build_one(c: dict, region: regions.Region, d: Path):
    pbf = Path(c["pbf_dir"]) / f"{region.name}.osm.pbf"
    record = json.loads((d / "stages.json").read_text()) if (d / "stages.json").exists() else {}
    crs = str(region.crs)
    stage = [PY, str(HERE / "stage.py"), crs]
    bbox = ",".join(f"{x:.4f}" for x in region.bbox)
    steps = [
        ("extract", [*stage, "-", "extract", str(pbf), str(d)], "roads.parquet"),
        ("elevation", [*stage, bbox, "elevation", str(d), "11"], "relief.tif"),
        ("terrain", [*stage, "-", "terrain", str(d)], "range3k.tif"),
        ("landcover", [*stage, "-", "landcover", str(d)], "tree_cover.parquet"),
        ("protected", [*stage, "-", "protected", str(d), c["landmarks"]], "protected.parquet"),
        ("score", [*stage, "-", "score", str(d), "--no-cache"], "scored_chunks.parquet"),
        ("graph_part", [PY, str(HERE / "graph_part.py"), crs, str(pbf), str(d), c["junctions"],
                        c["states"], region.name], "part_edges.parquet"),
    ]
    for name, cmd, out in steps:
        if (d / "part_edges.parquet").exists() and name != "graph_part":
            continue
        run_stage(d, name, cmd, d / out, record)
    if "disk_gb" not in record:
        record["disk_gb"] = round(sum(f.stat().st_size for f in d.iterdir() if f.is_file()) / 1e9, 2)
        record["pbf_gb"] = round(pbf.stat().st_size / 1e9, 3)
        (d / "stages.json").write_text(json.dumps(record, indent=1))
    if region.name not in c["keep"] and region.state not in c["keep"]:
        for f in d.iterdir():
            if f.is_file() and f.name not in KEEP_ALWAYS:
                f.unlink()


def main():
    c = load_config(sys.argv[1])
    if sys.argv[2:3] == ["--one"]:
        build_one(c, regions.load(c["states"], [sys.argv[3]])[0])
        return
    named = sys.argv[2:]
    pbf_dir, work = Path(c["pbf_dir"]), Path(c["work"])
    all_regions = regions.load(c["states"])
    pending = [r for r in regions.load(c["states"], named or None)
               if not (work / r.name / "part_edges.parquet").exists()]
    todo, need = [], {}

    def admit():
        """Queue each pending region once its PBF exists. With no regions named,
        that is every region, picked up as cut.py writes them."""
        for r in list(pending):
            pbf = pbf_dir / f"{r.name}.osm.pbf"
            if (work / r.name / "part_edges.parquet").exists():
                pending.remove(r)
            elif pbf.exists() and not building(work / r.name):
                pending.remove(r)
                need[r.name] = need_gb(r, pbf)
                todo.append(r)
        todo.sort(key=lambda r: -need[r.name])

    admit()
    if named and pending:
        raise SystemExit(f"no PBF for {', '.join(r.name for r in pending)}")
    running, failed = {}, []
    t0 = time.time()
    while todo or running or pending:
        admit()
        for name, (p, _) in list(running.items()):
            if p.poll() is not None:
                del running[name]
                if p.returncode:
                    failed.append(name)
                print(f"[{time.time() - t0:6.0f}s] {name} {'FAILED' if p.returncode else 'done'}; "
                      f"{len(todo)} waiting", flush=True)
        # Builds this scheduler did not start (another scheduler, or one stopped
        # and restarted) count against the same budget while their lock is live.
        others = [r for r in all_regions if r.name not in running and building(work / r.name)]
        used = (sum(g for _, g in running.values())
                + sum(need_gb(r, pbf_dir / f"{r.name}.osm.pbf") for r in others))
        busy = len(running) + len(others)
        for r in list(todo):
            if busy >= c["jobs"]:
                break
            if busy and used + need[r.name] > c["mem_gb"]:
                continue
            todo.remove(r)
            print(f"[{time.time() - t0:6.0f}s] start {r.name} (~{need[r.name]:.1f} GB)", flush=True)
            running[r.name] = (subprocess.Popen([PY, __file__, sys.argv[1], "--one", r.name]),
                               need[r.name])
            used += need[r.name]
            busy += 1
        time.sleep(5)
    if failed:
        raise SystemExit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    main()
