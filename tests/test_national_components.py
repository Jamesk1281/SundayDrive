"""The national scenery components: mountain-scale terrain, desert and rock, landmarks.

docs/national-scenery-scoring-verdict.md chose them (candidate E1) for one property
above all: they are ~0 in New England, so a build made before them, and the
deployed graph, must score and route exactly as before. Most of what is tested
here is that property, and the two ways the new inputs can be quietly wrong --
a corrupt elevation pixel spread across a 3 km window, and a WorldCover cell the
1 km desert box reaches that WorldCover never made.

Everything runs on synthetic data; nothing here needs a built region.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
import rasterio.errors
import shapely
from rasterio.transform import from_origin

import landcover
import protected
import score
import terrain
from router import BASELINE, OPTIONAL_BASELINE, Router
from test_cache import rebuild, region, write_tree_cover
from test_state_roads import _toy


# --- terrain.py ------------------------------------------------------------

def slope(h=60, w=60, per_px=10.0, base=1500.0):
    """A plane rising `per_px` metres per pixel to the east."""
    return (base + per_px * np.arange(w)[None, :] * np.ones((h, 1))).astype(np.float32)


class TestDespike:
    def test_a_steep_real_slope_survives(self):
        """100 m per 57 m pixel is a 60-degree face, steeper than any road sees."""
        z, n = terrain.despike(slope(per_px=100.0))
        assert n == 0 and not np.isnan(z).any()

    def test_a_cliff_survives(self):
        """A 600 m wall (the Black Canyon's is 690 m) is terrain, not a spike."""
        z = slope(per_px=0.0)
        z[:, 30:] += 600.0
        out, n = terrain.despike(z)
        assert n == 0

    def test_a_single_spike_is_removed_alone(self):
        z = slope()
        z[30, 30] += 500.0
        out, n = terrain.despike(z)
        assert n == 1 and np.isnan(out[30, 30])

    def test_a_huge_spike_takes_only_its_rim_with_it(self):
        """Past BLOB_M the coarse rule fires too and grows by BLOB_GROW, so a
        2,500 m spike costs its diamond of 13 px -- invisible to a 53 px window."""
        z = slope()
        z[30, 30] = 4000.0
        out, n = terrain.despike(z)
        assert np.isnan(out[30, 30]) and n == 13
        assert np.isnan(out).sum() == 13

    def test_a_pit_too_wide_for_the_median_is_removed_with_its_rim(self):
        """Colorado's Moffat County blob: 12 x 9 px, about 2,000 m deep, with
        ringing at its edge. Its own 5x5 median is corrupt too, so only the
        coarse rule can see it, and the ringing has to go with it."""
        z = np.full((80, 80), 2100.0, dtype=np.float32)
        z[34:46, 34:43] = 0.0
        z[33, 34:43] = 900.0                       # ringing at the rim
        out, n = terrain.despike(z)
        assert np.isnan(out[34:46, 34:43]).all()
        assert np.isnan(out[33, 34:43]).all()
        assert not np.isnan(out[:20, :20]).any(), "far terrain untouched"

    def test_holes_stay_holes_and_never_become_data(self):
        z = slope()
        z[10:12, 10:12] = np.nan
        out, _ = terrain.despike(z)
        assert np.isnan(out[10:12, 10:12]).all()
        assert np.isnan(out).sum() == 4

    def test_the_physical_band_still_applies(self):
        z = slope()
        z[5, 5] = -32768.0
        out, _ = terrain.despike(z)
        assert np.isnan(out[5, 5])


class TestRange:
    def test_range_of_a_plane_is_its_rise_across_the_window(self):
        out = terrain.range_within(slope(per_px=10.0), 5)
        assert out[30, 30] == pytest.approx(40.0)

    def test_a_hole_is_invisible_not_flat(self):
        """A gap must not set the minimum for its neighbours: elevation.py's
        convention, for the same reason."""
        z = slope(per_px=0.0)
        z[30, 30] = np.nan
        out = terrain.range_within(z, 5)
        assert np.isnan(out[30, 30])
        assert out[30, 31] == pytest.approx(0.0)

    def test_window_is_three_km_of_ground_at_the_reference_latitude(self):
        tr = from_origin(0, 0, 76.4, 76.4)        # zoom-11 Terrarium pixels
        win = terrain.window_px(tr)
        assert win % 2 == 1
        ground = win * 76.4 * np.cos(np.radians(terrain.RELIEF_REF_LAT))
        assert abs(ground - terrain.RANGE_WINDOW_M) < 76.4


# --- landcover.py: one read, two boxes --------------------------------------

class FakeTile:
    """A WorldCover tile defined by a function of global pixel (row, col)."""

    def __init__(self, tr, tc, cls):
        self.tr, self.tc, self.cls = tr, tc, cls
        self.width = self.height = landcover.TILE_PX

    def read(self, band, window):
        r0 = self.tr * landcover.TILE_PX + int(window.row_off)
        c0 = self.tc * landcover.TILE_PX + int(window.col_off)
        rr, cc = np.mgrid[r0:r0 + int(window.height), c0:c0 + int(window.width)]
        return self.cls(rr, cc).astype(np.uint8)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_worldcover(monkeypatch, cls, absent=()):
    def open_tile(tile, cache, stream):
        if tile in absent:
            raise rasterio.errors.RasterioIOError(f"{tile}: HTTP 404")
        lat0 = int(tile[1:3]) * (1 if tile[0] == "N" else -1)
        lon0 = int(tile[4:7]) * (-1 if tile[3] == "W" else 1)
        tr = (90 - lat0) // landcover.TILE_DEG - 1
        tc = (lon0 + 180) // landcover.TILE_DEG
        return FakeTile(tr, tc, cls)
    monkeypatch.setattr(landcover, "open_tile", open_tile)
    monkeypatch.setattr(landcover, "check_georeferencing", lambda *a: None)
    monkeypatch.setattr(landcover, "tile_absent", lambda tile: tile in absent)


def gcol(lon):
    return np.floor((lon + 180.0) * landcover.PX_PER_DEG)


class TestCover:
    def test_trees_and_desert_are_counted_in_their_own_boxes(self, monkeypatch):
        """Desert east of a meridian, trees west of it. A point 300 m west of the
        line has a tree box all tree and a desert box that reaches the desert."""
        line = gcol(-110.5)
        fake_worldcover(monkeypatch, lambda r, c: np.where(c >= line, 60, 10))
        lon = np.array([-110.6, -110.5 - 300 / (111_320 * np.cos(np.radians(38.5))), -110.4])
        lat = np.full(3, 38.5)
        tree, desert, _ = landcover.sample_cover(lon, lat, None, stream=True)
        assert tree[0] == 1.0 and desert[0] == 0.0
        assert tree[1] == 1.0 and 0.1 < desert[1] < 0.4
        assert tree[2] == 0.0 and desert[2] == 1.0

    def test_built_land_is_counted_in_the_one_km_box(self, monkeypatch):
        line = gcol(-110.5)
        fake_worldcover(monkeypatch, lambda r, c: np.where(c >= line, 50, 10))
        lon = np.array([-110.5 - 300 / (111_320 * np.cos(np.radians(38.5)))])
        tree, desert, built = landcover.sample_cover(lon, np.array([38.5]), None, True)
        assert tree[0] == 1.0 and desert[0] == 0.0 and 0.1 < built[0] < 0.4

    def test_grass_is_not_desert(self, monkeypatch):
        """The owner's decision, encoded: grassland (30) does not count."""
        fake_worldcover(monkeypatch, lambda r, c: np.full(r.shape, 30))
        _, desert, _ = landcover.sample_cover(np.array([-105.0]), np.array([39.5]), None, True)
        assert desert[0] == 0.0

    def test_tree_fraction_is_what_it_was(self, monkeypatch):
        """The tree half must not move: it is New England's c_forest."""
        fake_worldcover(monkeypatch, lambda r, c: np.where((r + c) % 3 == 0, 10, 20))
        lon, lat = np.array([-72.31, -71.0]), np.array([42.0001, 44.2])
        tree = landcover.sample_tree_fraction(lon, lat, None, True)
        rows, cols = landcover.window_px(lat)
        for i in range(2):
            gr = np.floor((90 - lat[i]) * landcover.PX_PER_DEG)
            gc = gcol(lon[i])
            rr, cc = np.mgrid[gr - rows[i] // 2:gr + rows[i] // 2 + 1, gc - cols[i] // 2:gc + cols[i] // 2 + 1]
            assert tree[i] == pytest.approx(((rr + cc) % 3 == 0).mean(), abs=1e-6)

    def test_a_box_across_a_tile_seam_is_counted_from_both(self, monkeypatch):
        """Lat 42 is a tile line, and Massachusetts' southern border is on it."""
        fake_worldcover(monkeypatch, lambda r, c: np.full(r.shape, 70))
        tree, desert, _ = landcover.sample_cover(np.array([-72.0]), np.array([42.0001]), None, True)
        assert desert[0] == 1.0 and tree[0] == 0.0

    def test_a_desert_box_reaching_an_ocean_cell_counts_it_as_water(self, monkeypatch):
        """WorldCover omits all-ocean cells. A 1 km box near the coast can reach
        one where a 100 m box never has: that is water, not a reason to stop."""
        fake_worldcover(monkeypatch, lambda r, c: np.full(r.shape, 60), absent={"N42W069"})
        lon = np.array([-69.0 - 200 / (111_320 * np.cos(np.radians(43.0)))])
        tree, desert, _ = landcover.sample_cover(lon, np.array([43.0]), None, True)
        assert 0.6 < desert[0] < 0.8

    def test_a_tree_box_reaching_a_missing_cell_still_stops_the_run(self, monkeypatch):
        fake_worldcover(monkeypatch, lambda r, c: np.full(r.shape, 10), absent={"N42W069"})
        with pytest.raises(rasterio.errors.RasterioIOError):
            landcover.sample_cover(np.array([-68.99]), np.array([43.0]), None, True)


# --- protected.py -----------------------------------------------------------

class TestLandmarks:
    def polygons(self, des_tp, featclass="Fee"):
        box = shapely.box(-111.0, 38.0, -110.0, 39.0)
        g = gpd.GeoDataFrame({"FeatClass": [featclass], "Des_Tp": [des_tp]}, geometry=[box], crs=4326)
        return g.to_crs(5070)

    @pytest.mark.parametrize("code", sorted(protected.LANDMARK))
    def test_each_landmark_designation_counts(self, code):
        f = protected.landmark_flags(np.array([-110.5, -109.5]), np.array([38.5, 38.5]), self.polygons(code))
        assert f.tolist() == [1.0, 0.0]

    @pytest.mark.parametrize("code", ["NF", "PUB", "CONE", "LP", "MIL"])
    def test_multiple_use_and_local_land_does_not(self, code):
        f = protected.landmark_flags(np.array([-110.5]), np.array([38.5]), self.polygons(code))
        assert f.tolist() == [0.0]

    @pytest.mark.parametrize("featclass", ["Proclamation", "Easement", "Marine"])
    def test_only_fee_and_designation_polygons_count(self, featclass):
        f = protected.landmark_flags(np.array([-110.5]), np.array([38.5]), self.polygons("NP", featclass))
        assert f.tolist() == [0.0]


# --- score.py ---------------------------------------------------------------

def write_cover(d, tree, desert, built=0.0):
    roads = score.load_layer(d, "roads")
    mids = score.chunk_roads(roads).geometry.interpolate(0.5, normalized=True).to_crs(4326)
    pd.DataFrame({"lon": mids.x.to_numpy(), "lat": mids.y.to_numpy(),
                  "tree": np.full(len(mids), tree), "desert": np.full(len(mids), desert),
                  "built": np.full(len(mids), built)}).to_parquet(d / "tree_cover.parquet")
    return mids


def write_landmarks(d, mids):
    pd.DataFrame({"lon": mids.x.to_numpy(), "lat": mids.y.to_numpy(),
                  "landmark": np.ones(len(mids), dtype=np.float32)}).to_parquet(d / "protected.parquet")


@pytest.fixture
def legacy(tmp_path):
    """A region exactly as it was built before the national components."""
    d = region(tmp_path / "processed")
    write_tree_cover(d, 0.4)
    chunks, _ = rebuild(d, cache=False)
    return d, chunks


class TestScore:
    def test_a_build_without_the_new_inputs_scores_as_before(self, legacy):
        """The deployed region's contract: no range3k.tif, no protected.parquet,
        a tree_cover.parquet with no desert column -> the old score, exactly."""
        d, chunks = legacy
        assert (chunks["c_grand"] == 0).all() and (chunks["c_protected"] == 0).all()
        old = {k: v for k, v in score.WEIGHTS.items() if k not in ("grand", "protected")}
        raw = sum(old[c[2:]] * chunks[c] for c in chunks.columns
                  if c.startswith("c_") and c[2:] in old)
        assert np.allclose(chunks["score"], score.composite(raw, chunks["score_adj"]), atol=1e-12)

    def test_desert_takes_forest_s_slot_by_max(self, legacy):
        d, before = legacy
        write_cover(d, 0.4, 0.9)
        after, _ = rebuild(d, cache=False)
        assert np.allclose(after["c_forest"], np.maximum(before["c_forest"], 0.9))
        write_cover(d, 0.4, 0.05)
        low, _ = rebuild(d, cache=False)
        assert np.allclose(low["c_forest"], before["c_forest"]), \
            "a little bare ground (a quarry) must not move a wooded road"

    def test_grand_starts_above_new_england_hills_and_saturates(self, legacy):
        d, _ = legacy
        roads = score.load_layer(d, "roads")
        bounds = roads.to_crs(3857).total_bounds
        h, w = 40, 40
        tr = from_origin(bounds[0] - 500, bounds[3] + 500, (bounds[2] - bounds[0] + 1000) / w,
                         (bounds[3] - bounds[1] + 1000) / h)
        for value, want in ((250.0, 0.0), (600.0, 0.5), (2000.0, 1.0)):
            with rasterio.open(d / "range3k.tif", "w", driver="GTiff", height=h, width=w, count=1,
                               dtype="float32", crs="EPSG:3857", transform=tr, nodata=float("nan")) as dst:
                dst.write(np.full((1, h, w), value, dtype=np.float32))
            chunks, _ = rebuild(d, cache=False)
            assert np.allclose(chunks["c_grand"], want), value

    def test_a_misaligned_landmark_table_is_refused(self, legacy):
        d, chunks = legacy
        pd.DataFrame({"lon": np.zeros(3), "lat": np.zeros(3), "landmark": np.ones(3)}
                     ).to_parquet(d / "protected.parquet")
        with pytest.raises(SystemExit, match="do not line up"):
            rebuild(d, cache=False)

    def test_new_components_carry_their_weights(self, legacy):
        d, _ = legacy
        write_landmarks(d, write_cover(d, 0.4, 0.0))
        chunks, _ = rebuild(d, cache=False)
        assert (chunks["c_protected"] == 1.0).all()
        assert np.allclose(chunks["raw"], score.blend(chunks))

    def test_a_city_park_is_not_a_landmark(self, legacy):
        """PAD-US calls Boston's Charles River Reservation a state park, and
        Storrow Drive runs through it. Built-up surroundings switch the credit off."""
        d, _ = legacy
        write_landmarks(d, write_cover(d, 0.4, 0.0, built=0.45))
        chunks, _ = rebuild(d, cache=False)
        assert (chunks["c_protected"] == 0.0).all()
        write_landmarks(d, write_cover(d, 0.4, 0.0, built=score.PROTECTED_BUILT_MAX))
        chunks, _ = rebuild(d, cache=False)
        assert (chunks["c_protected"] == 1.0).all()

    def test_landmarks_need_the_built_column_to_count(self, legacy):
        """An old tree_cover.parquet cannot tell a city park from a national
        one, so landmarks score nothing rather than everything."""
        d, _ = legacy
        roads = score.load_layer(d, "roads")
        mids = score.chunk_roads(roads).geometry.interpolate(0.5, normalized=True).to_crs(4326)
        write_landmarks(d, mids)                          # tree_cover has no built column
        chunks, _ = rebuild(d, cache=False)
        assert (chunks["c_protected"] == 0.0).all()


# --- router.py --------------------------------------------------------------

class TestRouterCompatibility:
    def test_the_new_components_are_always_on(self):
        cols = {c for c, _ in BASELINE}
        assert OPTIONAL_BASELINE <= cols

    def test_a_graph_built_before_them_loads_and_scores_as_stored(self, tmp_path):
        """The deployed New England graph has no c_grand or c_protected."""
        r = Router(str(_toy(tmp_path / "old", rules=False)))
        assert "c_grand" not in r.edges.columns
        assert np.allclose(r._edge_scores({}), score.composite(
            score.blend(r.edges[score.components(r.edges)]).to_numpy(), r.score_adj))

    def test_a_graph_carrying_them_reblends_to_its_stored_score(self, tmp_path):
        d = _toy(tmp_path / "new", rules=False)
        e = gpd.read_parquet(d / "graph_edges.parquet")
        e["c_grand"] = np.linspace(0, 1, len(e))
        e["c_protected"] = (np.arange(len(e)) % 2).astype(float)
        e["score"] = score.composite(score.blend(e[score.components(e)]).to_numpy(), e["score_adj"].to_numpy())
        e.to_parquet(d / "graph_edges.parquet")
        r = Router(str(d))
        assert np.allclose(r._edge_scores({}), e["score"].to_numpy(), atol=1e-9)
        # and no slider reaches them: zeroing every tunable type leaves their share
        weights = {name: 0.0 for name in ("water", "coast", "forest", "hills", "farm", "town")}
        assert np.all(r._edge_scores(weights) >= score.composite(
            np.zeros(len(e)) + 0.10 * e["c_grand"].to_numpy(), e["score_adj"].to_numpy()) - 1e-9)
