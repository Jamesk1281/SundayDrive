"""The pieces of the national build that decide topology at region borders.

docs/national-build.md §3 proves the method on real data (New Hampshire and Vermont
stitched against the joint New England build). These pin the three rules it rests
on, on graphs small enough to read: junctions counted over every region's ways, the
component cut on bare arrays, and each edge owned by exactly one region.
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import shapely

pytest.importorskip("osmium", reason="graph build tests need the pipeline deps")

from graph import build_edges, global_junctions, largest_component, largest_component_mask  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "national_build"))
import regions  # noqa: E402


def way(wid, ids, lon0=-72.0):
    meta = {"way_id": wid, "highway": "residential", "name": "", "ref": "", "junction": "",
            "dest_ref": "", "dest_name": "", "oneway": "", "speed": 40.0}
    return meta, ids, [(lon0 + 0.001 * i, 43.0 + 0.0001 * (n % 7)) for n, i in enumerate(ids)]


def to_m(lons, lats):
    return np.asarray(lons) * 81_000.0, np.asarray(lats) * 111_000.0


def counted(ways):
    count = {}
    for _, ids, _ in ways:
        for n in ids:
            count[n] = count.get(n, 0) + 1
    return count


class TestGlobalJunctions:
    """A road crossing the border is whole in both regions; a side road meeting it
    at node 3 is in region B only. Counted per region, A does not split at 3."""
    main = way(1, [1, 2, 3, 4, 5])
    side = way(2, [3, 30, 31], lon0=-71.998)

    def splits(self, ways, junctions=None):
        count = counted(ways)
        if junctions is not None:
            global_junctions(count, junctions)
        return sorted((r["u"], r["v"]) for r in build_edges([self.main], count, to_m))

    def test_a_region_alone_misses_the_neighbours_junction(self):
        assert self.splits([self.main]) == [(1, 5)]
        assert self.splits([self.main, self.side]) == [(1, 3), (3, 5)]

    def test_national_junctions_split_both_sides_alike(self):
        everywhere = np.array(sorted(n for n, c in counted([self.main, self.side]).items() if c >= 2))
        assert self.splits([self.main], everywhere) == self.splits([self.main, self.side], everywhere) \
            == [(1, 3), (3, 5)]

    def test_it_only_promotes(self):
        count = {1: 1, 3: 1, 9: 3}
        assert global_junctions(count, np.array([3, 9, 100])) == 1
        assert count == {1: 1, 3: 2, 9: 3}


class TestComponentMask:
    def test_matches_largest_component(self):
        # A two-way loop of four nodes, a one-way spur out of it with no way back,
        # and a separate two-way pair.
        u = np.array([1, 2, 3, 4, 4, 10])
        v = np.array([2, 3, 4, 1, 5, 11])
        oneway = ["", "", "", "", "yes", ""]
        edges = gpd.GeoDataFrame({"u": u, "v": v, "oneway": oneway},
                                 geometry=[shapely.LineString([(0, 0), (1, 1)])] * 6, crs=4326)
        mask = largest_component_mask(u, v, pd.Series(oneway))
        assert mask.tolist() == [True, True, True, True, False, False]
        kept = largest_component(edges)
        assert list(zip(kept["u"], kept["v"])) == list(zip(u[mask], v[mask]))


@pytest.fixture(scope="module")
def owner():
    west = regions.Region("w", "XX", shapely.box(-73, 42, -72, 43), None)
    east = regions.Region("e", "XX", shapely.box(-72, 42, -71, 43), None)
    return regions.Owner([west, east])


class TestOwner:
    def test_one_owner_each_and_the_border_goes_to_the_first(self, owner):
        got = owner.of_lonlat(np.array([-72.5, -71.5, -72.0]), np.array([42.5, 42.5, 42.5]))
        assert got.tolist() == [0, 1, 0]

    def test_foreign_points_are_dropped_unless_on_the_line(self, owner):
        # ~50 m north of the boundary is kept, ~5 km north is dropped.
        got = owner.of_lonlat(np.array([-72.5, -72.5]), np.array([43.00045, 43.045]))
        assert got.tolist() == [0, -1]
