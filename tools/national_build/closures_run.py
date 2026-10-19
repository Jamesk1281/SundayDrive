"""Run closures.py unmodified, except that its report survives a region with nothing closed.

Usage: closures_run.py <input.osm.pbf> <processed_dir>

closures.py's report prints the length-weighted score of the seasonally closed
edges with np.average, which raises ZeroDivisionError when the graph holds none of
them (Rhode Island's ring, 2026-08-25). It raises after seasonal_closures.parquet is
written and before closed_to_cars.parquet and osm_unpaved.parquet are, so a region
with no seasonal road gets neither. closures.py belongs to another unit, so it is
not edited: this makes that one call return NaN on empty weights, which changes a
printed number and nothing written.
"""
import runpy
import sys
from pathlib import Path

import numpy as np

PIPELINE = Path(__file__).resolve().parents[2] / "pipeline"
_average = np.average


def average(a, *args, weights=None, **kwargs):
    if weights is not None and np.size(weights) == 0:
        return float("nan")
    return _average(a, *args, weights=weights, **kwargs)


if __name__ == "__main__":
    np.average = average
    sys.path.insert(0, str(PIPELINE))
    sys.argv = [str(PIPELINE / "closures.py"), *sys.argv[1:]]
    runpy.run_path(str(PIPELINE / "closures.py"), run_name="__main__")
