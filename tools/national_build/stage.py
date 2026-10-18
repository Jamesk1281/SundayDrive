"""Run one pipeline stage as its own __main__, in a region's metric projection.

Usage: stage.py <crs> <bbox or -> <module> [module args...]

The pipeline measures every length in common.CRS_METERS, which is EPSG:26986
(Massachusetts Mainland) and reads 4.5% long at Key West (regions.py). Each stage
imports it with `from common import CRS_METERS`, so setting common's attribute
before the stage is imported moves the whole stage into the region's projection
without editing it. `<crs>` is an EPSG code or a proj string.

`<bbox>` is west,south,east,north and sets elevation.BBOX, which is New England's
otherwise; build_region.sh in tools/national_scoring does the same.
"""
import runpy
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[2] / "pipeline"


def main():
    crs, bbox, module, *args = sys.argv[1:]
    sys.path.insert(0, str(PIPELINE))
    import common
    common.CRS_METERS = int(crs) if crs.isdigit() else crs
    if bbox != "-":
        # Called rather than run as __main__: runpy would execute a fresh copy of
        # the module, whose own `BBOX = ...` line would undo this.
        import elevation
        elevation.BBOX = tuple(float(x) for x in bbox.split(","))
        if module == "elevation":
            elevation.main(args[0], int(args[1]) if len(args) > 1 else 11)
            return
    sys.argv = [str(PIPELINE / f"{module}.py"), *args]
    runpy.run_module(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
