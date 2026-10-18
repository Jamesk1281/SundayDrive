"""Shared test setup: put pipeline/ and tools/ on the path, locate the built data.

The pure-function tests run anywhere. The calibration and routing tests need a
built graph, which is large and gitignored, so they skip cleanly when it's
absent (a fresh clone, or CI) instead of failing.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tools"))

# `VICTORYLAP_DATA` and `SCENIC_DATA` are the two pre-rename names, read for
# one release (see `server/app.py`) so commands written before the renames
# still point the suite at a built graph instead of silently skipping every
# test that needs one.
DATA = Path(os.environ.get("SUNDAYDRIVE_DATA")
            or os.environ.get("VICTORYLAP_DATA")
            or os.environ.get("SCENIC_DATA", ROOT / "data" / "processed"))

# Everything `Router.__init__` reads. It raises on any one of them being
# absent, so anything that builds a Router has to require the whole set or the
# skip below turns into an error.
ROUTER_DATA = ("graph_edges.parquet", "graph_nodes.parquet",
               "turn_restrictions.parquet")


def _require(*files):
    missing = [f for f in files if not (DATA / f).exists()]
    if missing:
        pytest.skip(f"built data missing ({', '.join(missing)}) — run the pipeline first")
    return DATA


@pytest.fixture(scope="session")
def chunks():
    """The scored road chunks (output of score.py)."""
    import geopandas as gpd
    return gpd.read_parquet(_require("scored_chunks.parquet") / "scored_chunks.parquet")


@pytest.fixture(scope="session")
def edges():
    """The routable graph edges (output of graph.py)."""
    import geopandas as gpd
    return gpd.read_parquet(_require("graph_edges.parquet") / "graph_edges.parquet")


@pytest.fixture(scope="session")
def router():
    """A loaded Router. Slow to build, so it is shared across the session.

    All three parquets, because `Router` refuses to load without the
    restriction table — so naming only the first two here turns "the data
    isn't built" from a clean skip into an error in fixture setup, on exactly
    the box `server/DEPLOY.md` tells the operator to read this run on.
    """
    _require(*ROUTER_DATA)
    from router import Router
    return Router(str(DATA))


# How far a test's named place may snap before the graph is taken not to cover
# it. A real place snaps within a few hundred metres; a place outside the built
# region snaps to the region's edge, tens of kilometres away.
COVERAGE_M = 5_000.0


def require_places(router, **places):
    """Skip unless the graph reaches every named (lat, lon).

    `data/processed` in the main checkout is still the August Massachusetts
    build; the New England one is `data/processed-ne`. Pointed at the first,
    a test about Waitsfield or Stowe would quietly plan from the Massachusetts
    line and fail on numbers that were never about its trip, which is how four
    tests on `usa` read as regressions on 2026-10-18.
    """
    far = {}
    for name, (lat, lon) in places.items():
        metres = router.snap(lat, lon)[1]
        if metres > COVERAGE_M:
            far[name] = metres
    if far:
        where = ", ".join(f"{n} {m / 1000:.0f} km" for n, m in far.items())
        pytest.skip(f"the graph at {DATA} does not reach {where} from the "
                    f"nearest road; point SUNDAYDRIVE_DATA at the New England "
                    f"build")
