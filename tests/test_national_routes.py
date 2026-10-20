"""Numbered highways route along themselves on the national pack: the check
that finds a wrong closure on a major road without anyone driving it
(docs/review-fixes-data.md, "The continuity check").

Skipped unless SUNDAYDRIVE_PACK names a national pack. The processed directory
it was built from is SUNDAYDRIVE_PACK_DATA, or the pack's sibling named with
"processed" for "pack" (data/pack-us -> data/processed-us, data/pack-us-next ->
data/processed-us-next). The full set of legs takes about 8 minutes.
"""

import json
import os
from pathlib import Path

import pytest

from conftest import ROOT

PACK = os.environ.get("SUNDAYDRIVE_PACK")
pytestmark = pytest.mark.skipif(not PACK, reason="SUNDAYDRIVE_PACK is not set")

import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools" / "national_audit"))
import continuity  # noqa: E402

MILES = 1.609344

# The trips the 2026-10-20 review planned through a ford on a paved major road,
# as (from, to, the most the trip may be in miles): about a tenth over each
# drive along the highway. Measured on data/pack-us and data/pack-us-next
# (docs/review-fixes-data.md, "The trips"): 308.7 -> 152.1, 132.3 -> 97.2,
# 80.8 -> 58.2, 137.1 -> 26.1, and no route -> 3.9.
REVIEW_TRIPS = {
    "El Paso to Carlsbad Caverns, US-62/180": ((31.7587, -106.4869), (32.1753, -104.4440), 165),
    "Needles to Blythe, US-95": ((34.8480, -114.6141), (33.6103, -114.5964), 105),
    "Fort Stockton to Marathon, US-385": ((30.8940, -102.8793), (30.2071, -103.2427), 64),
    "Carmel to Big Sur village, CA-1": ((36.5553, -121.9233), (36.2704, -121.8077), 29),
    "Andrew Molera to Big Sur village, CA-1": ((36.2878, -121.8443), (36.2704, -121.8077), 5),
}


def _processed():
    given = os.environ.get("SUNDAYDRIVE_PACK_DATA")
    if given:
        return Path(given)
    pack = Path(PACK)
    return pack.with_name(pack.name.replace("pack", "processed", 1))


@pytest.fixture(scope="module")
def national():
    processed = _processed()
    if not (processed / "graph_edges.parquet").exists():
        pytest.skip(f"no processed directory for the pack at {processed}; "
                    "set SUNDAYDRIVE_PACK_DATA")
    return continuity.load_router(processed, Path(PACK))


@pytest.mark.parametrize("trip", sorted(REVIEW_TRIPS))
def test_the_review_trips_drive_the_highway(national, trip):
    a, b, most_mi = REVIEW_TRIPS[trip]
    s, _ = national.snap(*a)
    t, _ = national.snap(*b)
    res = national.route(s, t, 0.0, None, on=continuity.SUMMER)
    assert res is not None
    assert res.km / MILES <= most_mi, f"{trip}: {res.km / MILES:.1f} mi"


def test_the_legs_are_the_graphs():
    """legs.json is what `make_legs` takes from this graph, so a rebuilt graph
    with different ids or roads says so here rather than in a failed leg."""
    processed = _processed()
    if not (processed / "graph_edges.parquet").exists():
        pytest.skip(f"no processed directory at {processed}")
    assert continuity.make_legs(processed) == json.loads(continuity.LEGS.read_text())


def test_numbered_highways_route_along_themselves(national):
    """Every leg passes, or is one of the failures docs/review-fixes-data.md
    explains (continuity.KNOWN)."""
    legs = json.loads(continuity.LEGS.read_text())
    results = continuity.check(national, legs, _processed())
    failed = {continuity.key(r): r for r in results if not r["passed"]}
    unexplained = sorted(set(failed) - set(continuity.KNOWN))
    assert not unexplained, "\n".join(
        f"{k}: route {failed[k]['route_km']} km for {failed[k]['along_km']} km along, "
        f"{failed[k]['on_ref']:.0%} on the ref" for k in unexplained)
