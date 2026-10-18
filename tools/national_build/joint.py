"""The reference a national build is checked against: one PBF built as one region.

Usage: joint.py <input.osm.pbf> <processed_dir> <landmarks.parquet>

The unmodified pipeline in build_region.sh's order, in EPSG:26986 and over
elevation.py's own New England box, ending with graph.py's main() and
closures.py, exactly as data/processed-ne was built, plus E1's terrain.py and
protected.py. Run on the 2026-08-25 New England extract it is what processed-ne
would be if rebuilt with E1, and the six-state stitch is compared with it
(docs/national-build.md §3, §4).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import PY, run_stage  # noqa: E402

PIPELINE = HERE.parents[1] / "pipeline"


def main(pbf: str, out: str, landmarks: str):
    d = Path(out).resolve()
    (d / "logs").mkdir(parents=True, exist_ok=True)
    record = json.loads((d / "stages.json").read_text()) if (d / "stages.json").exists() else {}
    stage = [PY, str(HERE / "stage.py"), "26986", "-"]
    for name, cmd, done in [
        ("extract", [*stage, "extract", pbf, str(d)], "roads.parquet"),
        ("elevation", [*stage, "elevation", str(d), "11"], "relief.tif"),
        ("terrain", [*stage, "terrain", str(d)], "range3k.tif"),
        ("landcover", [*stage, "landcover", str(d)], "tree_cover.parquet"),
        ("protected", [*stage, "protected", str(d), landmarks], "protected.parquet"),
        ("score", [*stage, "score", str(d), "--no-cache"], "scored_chunks.parquet"),
        ("graph", [*stage, "graph", pbf, str(d)], "graph_edges.parquet"),
        ("closures", [PY, str(PIPELINE / "closures.py"), pbf, str(d)], "osm_unpaved.parquet"),
    ]:
        run_stage(d, name, cmd, d / done, record)


if __name__ == "__main__":
    main(*sys.argv[1:4])
