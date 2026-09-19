"""The component cache, and the invalidation table it exists to implement.

score.py spends almost all of its feature time in two `dwithin` queries —
water at 202.8 s and green at 142.0 s on the New England build, against 7.5 s
for the other five layers put together. Caching those two is what makes
re-tuning a constant a minutes-long operation instead of a 17-minute one.

Two things can go wrong and only one of them is loud. The loud one is a stale
answer for a constant that changed. The quiet one is a cached array joined to
the wrong chunks: it would credit one road with another's water and still
produce a plausible score, which is the hazard `sample_tree_cover` already
raises SystemExit over. Both are tested here; the quiet one is tested harder.

These run against a synthetic six-road region built in a tmp_path, so they need
no built data. Every invalidation case asserts on *which layer files were
opened*, because a cache hit is precisely the case where the expensive layer is
never read — that makes the assertion about the thing the cache is for rather
than about a log line.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import shapely

import score


# --- A tiny region, in metres, so the distances below read literally --------

def region(d):
    """Six roads and the layers score.main() reads, written to `d`.

    Written already in CRS_METERS, so `load_layer`'s reprojection is a no-op
    and a "50 m from the river" below really is 50 m.
    """
    d.mkdir(parents=True, exist_ok=True)
    roads = gpd.GeoDataFrame(
        {"highway": ["residential", "tertiary", "secondary", "unclassified",
                     "primary", "residential"],
         "name": ["Mill Road", "Lake Street", "Ridge Road", "Bog Lane",
                  "Main Street", "Elm Street"],
         "ref": ["", "", "", "", "US 1", ""],
         "scenic": [False, True, False, False, False, False],
         "surface": ["asphalt", "gravel", "", "dirt", "asphalt", ""]},
        geometry=[shapely.LineString([(0, i * 500), (900, i * 500)])
                  for i in range(6)],
        crs=score.CRS_METERS)
    roads.to_parquet(d / "roads.parquet")

    def layer(name, geoms):
        gpd.GeoDataFrame(geometry=geoms, crs=score.CRS_METERS).to_parquet(
            d / f"{name}.parquet")

    # A pond beside road 0 and another 250 m off road 1 — inside the 350 m
    # mid-water band but outside the 120 m near band, so both water distances
    # have something to say.
    layer("water_areas", [shapely.box(100, 50, 400, 300),
                          shapely.box(100, 750, 400, 900)])
    layer("water_lines", [shapely.LineString([(0, 2400), (900, 2400)])])
    layer("green_areas", [shapely.box(0, 950, 900, 1450)])
    layer("coastline", [shapely.LineString([(0, -700), (900, -700)])])
    layer("farm_areas", [shapely.box(0, 1550, 900, 1900)])
    layer("viewpoints", [shapely.Point(450, 2100)])
    layer("urban_areas", [shapely.box(0, 2450, 900, 2600)])
    layer("place_points", [shapely.Point(450, 100)])
    return d


def write_tree_cover(d, value):
    """landcover.py's output, aligned to these chunks the way it must be."""
    roads = score.load_layer(d, "roads")
    mids = score.chunk_roads(roads).geometry.interpolate(0.5, normalized=True).to_crs(4326)
    pd.DataFrame({"lon": mids.x.to_numpy(), "lat": mids.y.to_numpy(),
                  "tree": np.full(len(mids), value)}).to_parquet(
        d / "tree_cover.parquet")


def rebuild(d, cache=True):
    """Run score.main() and report which layers it actually opened.

    A warm cache is exactly the case where the expensive layer is never read —
    `CachedQuery` takes a callable rather than a tree so a hit does not pay to
    load and reproject it — so `opened` is the direct test of a cache hit.

    Swaps `load_layer` by hand rather than through `monkeypatch`, because the
    callers patch a constant *before* calling this and `monkeypatch.undo()`
    would take theirs down with it.
    """
    opened = []
    real = score.load_layer

    def spy(directory, name):
        opened.append(name)
        return real(directory, name)

    score.load_layer = spy
    try:
        score.main(str(d), cache=cache)
    finally:
        score.load_layer = real
    return gpd.read_parquet(d / "scored_chunks.parquet"), opened


EXPENSIVE = ("water_areas", "water_lines", "green_areas")


@pytest.fixture
def built(tmp_path):
    """A cold build, so every test below starts from a populated cache."""
    d = region(tmp_path / "processed")
    cold, opened = rebuild(d)
    assert set(EXPENSIVE) <= set(opened), "a cold build must read both layers"
    return d, cold


class TestChunkIdentity:
    """Trap 1: a cached array joined to the wrong chunks has no symptom."""

    def line(self, *points):
        return np.array([shapely.LineString(points)])

    def test_the_same_chunks_hash_the_same(self):
        a = self.line((0, 0), (10, 0), (10, 10))
        b = self.line((0, 0), (10, 0), (10, 10))
        assert score.chunk_digest(a) == score.chunk_digest(b)

    def test_a_millimetre_of_movement_changes_it(self):
        a = self.line((0, 0), (10, 0))
        b = self.line((0, 0), (10.000001, 0))
        assert score.chunk_digest(a) != score.chunk_digest(b)

    def test_reordering_the_chunks_changes_it(self):
        """The misalignment itself: same geometries, different rows, and a
        cached column carried across would credit each road with the other's."""
        a = shapely.LineString([(0, 0), (10, 0)])
        b = shapely.LineString([(0, 5), (10, 5)])
        assert score.chunk_digest(np.array([a, b])) != score.chunk_digest(np.array([b, a]))

    def test_regrouping_the_same_coordinates_changes_it(self):
        """Hashing the coordinate stream alone would miss this: identical
        points, cut into chunks at a different place. That is precisely what a
        CHUNK_LEN change or a shapely `substring` change does, so the per-chunk
        vertex counts have to be in the hash too."""
        pts = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]
        split_at_2 = np.array([shapely.LineString(pts[:2]), shapely.LineString(pts[2:])])
        split_at_3 = np.array([shapely.LineString(pts[:3]), shapely.LineString(pts[3:])])
        assert score.chunk_digest(split_at_2) != score.chunk_digest(split_at_3)

    def test_two_roads_can_share_a_midpoint_and_not_a_geometry(self):
        """Why this hashes the whole chunk and not, as the brief allows, its
        midpoint. `dwithin` reads the entire line, so two chunks that agree on
        their midpoint to the tolerance `sample_tree_cover` uses can still give
        different answers — the second of these dips 4 m towards the water."""
        flat = np.array([shapely.LineString([(0, 0), (5, 0), (10, 0)])])
        vee = np.array([shapely.LineString([(0, -4), (5, 0), (10, -4)])])
        mids = [shapely.get_coordinates(
            shapely.line_interpolate_point(g, 0.5, normalized=True)) for g in (flat, vee)]
        assert np.allclose(*mids, atol=1e-9), "the midpoint check would pass these"
        assert score.chunk_digest(flat) != score.chunk_digest(vee)

    def test_a_tampered_entry_stops_the_build(self, built):
        """Trap 1's response, not a silent recompute. The filename is the
        digest of the key, so an entry whose recorded key disagrees is a
        collision or a hand-edit — and proceeding would be the misaligned join
        that has no symptom."""
        d, _ = built
        entries = sorted(score.cache_dir(d).glob("water-*.npz"))
        assert entries, "the cold build should have written water entries"
        held = dict(np.load(entries[0], allow_pickle=False))
        held["flags"] = held["flags"][:-1]
        np.savez_compressed(entries[0], **held)
        with pytest.raises(SystemExit, match="does not hold what its name says"):
            rebuild(d)


class TestInvalidationTable:
    """docs/component-rebuild-cache-brief.md's table, executed row by row.

    `opened` is the assertion in every case: a layer that is not reopened is a
    query that was not re-run.
    """

    def test_an_unchanged_rebuild_reads_neither_expensive_layer(self, built):
        d, cold = built
        warm, opened = rebuild(d)
        assert not set(EXPENSIVE) & set(opened)
        pd.testing.assert_frame_equal(cold, warm)

    def test_weights_invalidates_no_component_column(self, built, monkeypatch):
        """The top row, and the whole point of the change: re-blending is a
        cache-hit rebuild. `WEIGHTS` moves `raw` and `score` and nothing else,
        so a retune that has to be re-validated against the drive marks costs
        the cheap half of the build rather than all of it."""
        d, cold = built
        monkeypatch.setitem(score.WEIGHTS, "water", score.WEIGHTS["water"] * 2)
        warm, opened = rebuild(d)

        assert not set(EXPENSIVE) & set(opened)
        for c in score.components(cold):
            np.testing.assert_array_equal(cold[c].to_numpy(), warm[c].to_numpy(), c)
        assert not np.allclose(cold["raw"], warm["raw"]), "WEIGHTS must move `raw`"

    @pytest.mark.parametrize("constant, key, reopened", [
        ("DIST", "water", ("water_areas", "water_lines")),
        ("DIST", "water_mid", ("water_areas", "water_lines")),
        ("DIST", "green", ("green_areas",)),
        ("MIN_AREA", "water", ("water_areas", "water_lines")),
        ("MIN_AREA", "green", ("green_areas",)),
    ])
    def test_a_distance_or_area_invalidates_exactly_its_own_query(
            self, built, monkeypatch, constant, key, reopened):
        d, _ = built
        monkeypatch.setitem(getattr(score, constant), key,
                            getattr(score, constant)[key] * 1.5)
        _, opened = rebuild(d)
        assert set(EXPENSIVE) & set(opened) == set(reopened)

    def test_a_cheap_layers_distance_invalidates_nothing_cached(self, built, monkeypatch):
        """`DIST["farm"]` and `DIST["green"]` are both 80 m. They must not
        share a cache entry — the key carries the query name, not just the
        distance."""
        d, _ = built
        monkeypatch.setitem(score.DIST, "farm", 200)
        _, opened = rebuild(d)
        assert not set(EXPENSIVE) & set(opened)

    @pytest.mark.parametrize("layer, geom, reopened, untouched", [
        ("green_areas", shapely.box(0, 950, 900, 1460),
         ("green_areas",), "c_water"),
        # Both water files feed one tree, so either one moving has to take
        # both queries with it — and neither may touch the green answer.
        ("water_areas", shapely.box(100, 50, 400, 310),
         ("water_areas", "water_lines"), "c_forest"),
        ("water_lines", shapely.LineString([(0, 2410), (900, 2410)]),
         ("water_areas", "water_lines"), "c_forest"),
    ])
    def test_rewriting_a_layer_invalidates_only_its_query(
            self, built, layer, geom, reopened, untouched):
        d, cold = built
        gpd.GeoDataFrame(geometry=[geom], crs=score.CRS_METERS).to_parquet(
            d / f"{layer}.parquet")
        warm, opened = rebuild(d)
        assert set(EXPENSIVE) & set(opened) == set(reopened)
        np.testing.assert_array_equal(cold[untouched].to_numpy(),
                                      warm[untouched].to_numpy())

    def test_touching_a_layer_without_changing_it_invalidates_nothing(self, built):
        """Trap 3. A git checkout, a re-copy or a re-run of an upstream stage
        moves mtime without moving a byte, and an mtime key would evict exactly
        the two entries worth keeping."""
        d, _ = built
        for name in EXPENSIVE:
            p = d / f"{name}.parquet"
            p.write_bytes(p.read_bytes())
        _, opened = rebuild(d)
        assert not set(EXPENSIVE) & set(opened)

    def test_tree_cover_moves_c_forest_without_re_running_the_green_query(
            self, tmp_path):
        """Why this caches the query and not the `c_forest` column. Only half
        of c_forest is the 142 s green query; the other half is landcover.py's
        output, which the proposals this cache exists for want to rewrite
        repeatedly. Keying on the column would throw the query away each time."""
        d = region(tmp_path / "processed")
        write_tree_cover(d, 0.25)
        cold, _ = rebuild(d)
        write_tree_cover(d, 0.75)
        warm, opened = rebuild(d)

        assert not set(EXPENSIVE) & set(opened)
        assert np.allclose(warm["c_forest"] - cold["c_forest"], 0.25)

    def test_chunk_len_invalidates_everything(self, built, monkeypatch):
        """The chunk geometry itself changes, so no cached answer lines up."""
        d, _ = built
        monkeypatch.setattr(score, "CHUNK_LEN", 200.0)
        _, opened = rebuild(d)
        assert set(EXPENSIVE) <= set(opened)

    def test_rewriting_the_roads_invalidates_everything(self, built):
        d, _ = built
        roads = gpd.read_parquet(d / "roads.parquet")
        roads.loc[0, "geometry"] = shapely.LineString([(0, 1), (900, 1)])
        roads.to_parquet(d / "roads.parquet")
        _, opened = rebuild(d)
        assert set(EXPENSIVE) <= set(opened)


class TestTheOutputDoesNotMove:
    """Trap 6. This is a build-speed change to the file every other artifact is
    derived from, so the bar is an identical output, not a close one."""

    def test_cached_and_uncached_builds_agree_exactly(self, tmp_path):
        d = region(tmp_path / "processed")
        write_tree_cover(d, 0.4)
        uncached, opened = rebuild(d, cache=False)
        assert set(EXPENSIVE) <= set(opened)
        assert not score.cache_dir(d).exists(), "--no-cache must write nothing"

        cold, _ = rebuild(d)
        warm, opened = rebuild(d)
        assert not set(EXPENSIVE) & set(opened)
        pd.testing.assert_frame_equal(uncached, cold)
        pd.testing.assert_frame_equal(uncached, warm)

    def test_the_cache_lives_outside_the_deploy_source(self, tmp_path):
        """Trap 5: `data/processed-ne` is what gets rsynced to the serving box.
        Same placement landcover.py uses for its WorldCover tiles."""
        d = tmp_path / "data" / "processed-ne"
        assert score.cache_dir(d) == tmp_path / "data" / "raw" / "component-cache"
