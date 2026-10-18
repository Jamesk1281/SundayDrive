"""Cut a PBF into the regions' rings, several regions per pass.

Usage: cut.py <input.osm.pbf> <states.parquet> <out_dir> [region ...]

`osmium extract --strategy smart` keeps every way whole (all its nodes, inside the
ring or not) and completes the relations extract.py turns into areas, so a forest
that straddles a state line is assembled whole in both regions rather than lost
from both. Completion is limited to the relation tags extract.py reads (its
GREEN_*, WATER_*, FARM_ and URBAN_ sets), because "-S types=...,boundary" alone
would also pull every county and state boundary in whole.

osmium's memory grows with the number of extracts in one pass (six New England rings
from the 2026-08-25 New England extract: 41 s, 7.9 GB peak), so regions are cut
BATCH at a time; the measured cost is in docs/national-build.md.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regions  # noqa: E402

BATCH = 5
COMPLETE = ["types=multipolygon,boundary",
            "tags=natural,landuse,leisure,boundary=national_park,boundary=protected_area"]


def main(pbf: str, states: str, out_dir: str, only: list[str]):
    out = Path(out_dir).resolve()
    (out / "poly").mkdir(parents=True, exist_ok=True)
    todo = [r for r in regions.load(states, only or None)
            if not (out / f"{r.name}.osm.pbf").exists()]
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        extracts = []
        for r in batch:
            poly = out / "poly" / f"{r.name}.geojson"
            regions.write_polygon(r, poly)
            extracts.append({"output": f"{r.name}.osm.pbf.tmp", "output_format": "pbf",
                             "polygon": {"file_name": str(poly), "file_type": "geojson"}})
        config = out / "poly" / f"batch{i // BATCH}.json"
        config.write_text(json.dumps({"directory": str(out), "extracts": extracts}))
        cmd = ["/usr/bin/time", "-l", "osmium", "extract", "-c", str(config), "--strategy", "smart",
               *[a for o in COMPLETE for a in ("-S", o)], "--overwrite", pbf]
        t0 = time.time()
        print(f"cutting {', '.join(r.name for r in batch)}", flush=True)
        res = subprocess.run(cmd, capture_output=True, text=True)
        rss = [ln for ln in res.stderr.splitlines() if "maximum resident" in ln]
        if res.returncode:
            raise SystemExit(res.stderr[-3000:])
        for r in batch:
            (out / f"{r.name}.osm.pbf.tmp").rename(out / f"{r.name}.osm.pbf")
        sizes = {r.name: (out / f"{r.name}.osm.pbf").stat().st_size / 1e6 for r in batch}
        print(f"  {time.time() - t0:.0f}s, {rss[0].split()[0] if rss else '?'} B peak; "
              + ", ".join(f"{k} {v:.0f} MB" for k, v in sizes.items()), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
