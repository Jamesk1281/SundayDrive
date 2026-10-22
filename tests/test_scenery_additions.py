"""The scenery additions V, S2 and L (docs/national-scenery-additions.md).

docs/national-scenery-types-verdict.md measured three terms offline, in
tools/scenery_types, and every constant was swept and passed as it stands. The
pipeline has to compute exactly what was measured, so three kinds of test are here:

- each term against the study's own definition (tools/scenery_types/cands.py), on
  the same inputs;
- each term's constant pinned, with a test that moves it and watches a behaviour the
  verdict depends on break (`*_moved` below): moving a constant invalidates the New
  England check, so it has to be loud;
- the old-file contract: a build without the new inputs scores exactly as E1 did.

Everything runs on synthetic data; nothing here needs a built region.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
import shapely
from rasterio.transform import from_origin

import landcover
import protected
import score
import terrain
from scenery_types import cands
from test_cache import rebuild, region
from test_national_components import fake_worldcover, gcol

PX = 76.437  # a zoom-11 Terrarium pixel in mercator metres


# --- V: distant relief ------------------------------------------------------

def plain(h=401, w=401, base=1000.0):
    return np.full((h, w), base, dtype=np.float32)


class TestProminence:
    def test_a_mountain_inside_the_window_counts(self):
        z = plain()
        z[200, 300] = 1600.0                      # 100 px (~5.6 km of ground) east
        win = terrain.prom_window_px(from_origin(0, 0, PX, PX))
        p = terrain.prominence_within(z, win)
        assert p[200, 200] == pytest.approx(600.0)

    def test_the_window_is_twenty_km_of_ground_at_the_reference_latitude(self):
        win = terrain.prom_window_px(from_origin(0, 0, PX, PX))
        assert win % 2 == 1
        ground = win * PX * np.cos(np.radians(terrain.RELIEF_REF_LAT))
        assert abs(ground - 2 * terrain.PROM_HALF_SIDE_M) < PX
        assert terrain.PROM_HALF_SIDE_M == 10_000.0

    def test_a_hole_is_invisible_and_stays_a_hole(self):
        z = plain()
        z[200, 210] = np.nan
        p = terrain.prominence_within(z, 51)
        assert np.isnan(p[200, 210]) and p[200, 200] == pytest.approx(0.0)

    def test_the_study_s_window_is_the_pipeline_s(self):
        """feat_lib.dem_features sizes the window from the same pixel at RELIEF_REF_LAT."""
        px_ground = PX * np.cos(np.radians(terrain.RELIEF_REF_LAT))
        assert terrain.prom_window_px(from_origin(0, 0, PX, PX)) == int(round(2 * 10 * 1000 / px_ground)) | 1

    @staticmethod
    def mountain_8km_away_counts():
        z = plain()
        px_ground = PX * np.cos(np.radians(terrain.RELIEF_REF_LAT))
        z[200, 200 + int(8000 / px_ground)] = 1700.0
        return terrain.prominence_within(z, terrain.prom_window_px(from_origin(0, 0, PX, PX)))[200, 200] > 0

    def test_a_mountain_8_km_off_is_seen(self):
        assert self.mountain_8km_away_counts()

    def test_the_half_side_moved_loses_it(self, monkeypatch):
        """R = 5 km was swept and passes New England, but it is not what ships."""
        monkeypatch.setattr(terrain, "PROM_HALF_SIDE_M", 5_000.0)
        assert not self.mountain_8km_away_counts()


def write_elevation(d, z):
    d.mkdir(parents=True, exist_ok=True)
    with rasterio.open(d / "elevation.tif", "w", driver="GTiff", height=z.shape[0], width=z.shape[1],
                       count=1, dtype="float32", crs="EPSG:3857", transform=from_origin(-8e6, 5.2e6, PX, PX),
                       nodata=float("nan")) as dst:
        dst.write(z, 1)


class TestTerrainStage:
    def test_prominence_is_despiked_first(self, tmp_path):
        """A 10 km maximum finds every corrupt pixel there is (verdict, trap 3)."""
        z = plain(120, 120)
        z[60, 60] = 1600.0                        # one in-band spike
        write_elevation(tmp_path, z)
        terrain.main(str(tmp_path))
        with rasterio.open(tmp_path / "prom10k.tif") as src:
            p = src.read(1)
        assert np.nanmax(p) == pytest.approx(0.0)
        assert (tmp_path / "range3k.tif").exists()

    def test_the_sea_floor_is_not_a_view(self, tmp_path):
        """Ocean is clipped to sea level before the maximum, as before the range."""
        z = plain(120, 120, base=-200.0)
        z[:, :60] = 0.0
        write_elevation(tmp_path, z)
        terrain.main(str(tmp_path))
        with rasterio.open(tmp_path / "prom10k.tif") as src:
            assert np.nanmax(src.read(1)) == pytest.approx(0.0)


class TestVista:
    def frame(self, prom, tree=0.0, built=0.0, mangrove=0.0):
        n = len(prom)
        return pd.DataFrame({"prom10k": prom, "tree_1k": np.full(n, tree), "built_1k": np.full(n, built),
                             "mangrove_1k": np.full(n, mangrove)})

    def test_matches_the_study(self):
        rng = np.random.default_rng(1)
        n = 2000
        F = pd.DataFrame({"prom10k": np.where(rng.random(n) < 0.1, np.nan, rng.uniform(0, 1500, n)),
                          "tree_1k": rng.uniform(0, 1, n), "built_1k": rng.uniform(0, 0.5, n),
                          "mangrove_1k": rng.uniform(0, 0.2, n)})
        got = score.vista(F.prom10k.to_numpy(), F.tree_1k.to_numpy(), F.built_1k.to_numpy(), F.mangrove_1k.to_numpy())
        assert np.allclose(got, cands.vista(F), atol=1e-12)

    def test_open_land_under_mountains(self):
        F = self.frame(np.array([250.0, 600.0, 900.0, 2000.0, np.nan]))
        assert np.allclose(score.vista(F.prom10k, F.tree_1k, F.built_1k, F.mangrove_1k), [0, 0.5, 1, 1, 0])

    def test_trees_built_land_and_mangrove_hide_the_view(self):
        for kw in ({"tree": 1.0}, {"built": 1.0}, {"mangrove": 1.0}):
            F = self.frame(np.array([2000.0]), **kw)
            assert score.vista(F.prom10k, F.tree_1k, F.built_1k, F.mangrove_1k)[0] == 0.0
        F = self.frame(np.array([2000.0]), tree=0.4, built=0.1)
        assert score.vista(F.prom10k, F.tree_1k, F.built_1k, F.mangrove_1k)[0] == pytest.approx(0.5)

    @staticmethod
    def a_300m_view_is_worth_nothing():
        return score.vista(np.array([300.0]), np.zeros(1), np.zeros(1), np.zeros(1))[0] == 0.0

    def test_it_starts_at_c_grand_s_own_start(self):
        assert self.a_300m_view_is_worth_nothing()
        assert (score.GRAND_START, score.GRAND_FULL) == (300.0, 900.0)

    def test_the_start_moved_credits_new_england_s_hills(self, monkeypatch):
        """At 150-450 m V moves 7.6% of New England's km and fails its check (verdict §4)."""
        monkeypatch.setattr(score, "GRAND_START", 150.0)
        assert not self.a_300m_view_is_worth_nothing()


# --- S2: the sea, where the road is on it ------------------------------------

class TestSea:
    def test_matches_the_study(self):
        rng = np.random.default_rng(2)
        n = 2000
        d = np.where(rng.random(n) < 0.3, np.inf, rng.uniform(0, 1000, n))
        F = pd.DataFrame({"d_coast": d, "water_1k": rng.uniform(0, 1, n)})
        got = score.sea_as_water(d <= score.DIST["water"], d <= score.DIST["water_mid"], F.water_1k.to_numpy())
        assert np.allclose(got, cands.sea(F, on_sea=True))

    def test_water_s_own_curve(self):
        near, mid = np.array([True, False, False]), np.array([True, True, False])
        assert score.sea_as_water(near, mid, np.ones(3)).tolist() == [1.0, score.WATER_MID, 0.0]
        assert score.WATER_MID == 0.45

    @staticmethod
    def a_shore_road_is_dry():
        """A road along the shore has about half its box water at most."""
        return score.sea_as_water(np.array([True]), np.array([True]), np.array([0.45]))[0] == 0.0

    def test_only_on_the_sea(self):
        assert self.a_shore_road_is_dry()
        assert score.sea_as_water(np.array([True]), np.array([True]), np.array([0.5]))[0] == 1.0
        assert score.ON_SEA_WATER_SHARE == 0.5

    def test_the_share_moved_credits_shore_roads(self, monkeypatch):
        monkeypatch.setattr(score, "ON_SEA_WATER_SHARE", 0.35)
        assert not self.a_shore_road_is_dry()


class TestWaterShare:
    def test_water_and_mangrove_are_counted_in_the_one_km_box(self, monkeypatch):
        line = gcol(-81.0)
        fake_worldcover(monkeypatch, lambda r, c: np.where(c >= line, 80, 95))
        lon = np.array([-81.0 - 300 / (111_320 * np.cos(np.radians(25.0)))])
        s = landcover.sample_shares(lon, np.array([25.0]), None, True)
        assert 0.1 < s["water_1k"][0] < 0.4
        assert s["water_1k"][0] + s["mangrove_1k"][0] == pytest.approx(1.0)
        assert s["tree"][0] == 0.0 and s["tree_1k"][0] == 0.0

    def test_tree_1k_is_the_one_km_box_not_the_100_m_one(self, monkeypatch):
        """The trap the brief names: the study's tree_1k is not tree_cover's `tree`."""
        line = gcol(-110.5)
        fake_worldcover(monkeypatch, lambda r, c: np.where(c >= line, 30, 10))
        lon = np.array([-110.5 - 300 / (111_320 * np.cos(np.radians(38.5)))])
        s = landcover.sample_shares(lon, np.array([38.5]), None, True)
        assert s["tree"][0] == 1.0 and 0.6 < s["tree_1k"][0] < 0.9

    def test_an_ocean_cell_counts_as_water(self, monkeypatch):
        fake_worldcover(monkeypatch, lambda r, c: np.full(r.shape, 60), absent={"N42W069"})
        lon = np.array([-69.0 - 200 / (111_320 * np.cos(np.radians(43.0)))])
        s = landcover.sample_shares(lon, np.array([43.0]), None, True)
        assert s["desert"][0] + s["water_1k"][0] == pytest.approx(1.0)
        assert 0.2 < s["water_1k"][0] < 0.4

    def test_the_shares_partition_the_box(self, monkeypatch):
        """Every class lands in exactly one code: desert, built, tree, water and
        mangrove plus the rest is the whole box, and the old three are unchanged."""
        classes = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100])
        fake_worldcover(monkeypatch, lambda r, c: classes[(r * 7 + c * 3) % len(classes)])
        lon, lat = np.array([-105.3, -72.2]), np.array([39.6, 44.1])
        s = landcover.sample_shares(lon, lat, None, True)
        tree, desert, built = landcover.sample_cover(lon, lat, None, True)
        assert np.array_equal(tree, s["tree"]) and np.array_equal(desert, s["desert"])
        assert np.array_equal(built, s["built"])
        rows, cols = landcover.window_px(lat, landcover.DESERT_BOX_M)
        for i in range(2):
            gr, gc = np.floor((90 - lat[i]) * landcover.PX_PER_DEG), gcol(lon[i])
            rr, cc = np.mgrid[gr - rows[i] // 2:gr + rows[i] // 2 + 1, gc - cols[i] // 2:gc + cols[i] // 2 + 1]
            box = classes[((rr * 7 + cc * 3) % len(classes)).astype(int)]
            for name, cls in (("desert", landcover.DESERT_CLASSES), ("built", [50]), ("tree_1k", [10]),
                              ("water_1k", [80]), ("mangrove_1k", [95])):
                assert s[name][i] == pytest.approx(np.isin(box, cls).mean(), abs=1e-6), name


# --- L: landmark credit within 80 m -----------------------------------------

class TestLandmarkNear:
    def polygons(self):
        box = shapely.box(0, 0, 1000, 1000)                       # metres, in CRS_METERS
        g = gpd.GeoDataFrame({"FeatClass": ["Fee"], "Des_Tp": ["NP"]}, geometry=[box], crs=score.CRS_METERS)
        return g.to_crs(4326)                                       # as padus_landmarks.parquet stores it

    def flags(self, xs, within):
        pts = gpd.GeoSeries(gpd.points_from_xy(xs, np.full(len(xs), 500.0)), crs=score.CRS_METERS).to_crs(4326)
        return protected.landmark_flags(pts.x.to_numpy(), pts.y.to_numpy(), self.polygons(), within_m=within)

    def test_a_road_cut_out_of_the_park_is_next_to_it(self):
        xs = np.array([500.0, 1050.0, 1150.0])                      # inside, 50 m out, 150 m out
        assert self.flags(xs, 0.0).tolist() == [1.0, 0.0, 0.0]
        assert self.flags(xs, protected.DIST["green"]).tolist() == [1.0, 1.0, 0.0]

    def test_the_reach_is_score_s_own_green_reach(self):
        assert protected.DIST is score.DIST and score.DIST["green"] == 80

    def test_the_reach_moved_loses_the_road(self, monkeypatch):
        monkeypatch.setitem(score.DIST, "green", 40)
        assert self.flags(np.array([1050.0]), protected.DIST["green"]).tolist() == [0.0]

    def test_multiple_use_land_is_still_not_a_landmark(self):
        g = self.polygons().assign(Des_Tp="NF")
        pts = gpd.GeoSeries(gpd.points_from_xy([1050.0], [500.0]), crs=score.CRS_METERS).to_crs(4326)
        assert protected.landmark_flags(pts.x.to_numpy(), pts.y.to_numpy(), g, within_m=80).tolist() == [0.0]


# --- score.py: the three terms in a build ------------------------------------

def mids(d):
    return score.chunk_roads(score.load_layer(d, "roads")).geometry.interpolate(0.5, normalized=True)


def write_cover(d, built=0.0, tree_1k=0.0, water_1k=0.0, mangrove_1k=0.0, shares=True):
    m = mids(d).to_crs(4326)
    n = len(m)
    df = pd.DataFrame({"lon": m.x.to_numpy(), "lat": m.y.to_numpy(), "tree": np.full(n, 0.4),
                       "desert": np.zeros(n), "built": np.full(n, built)})
    if shares:
        df["tree_1k"], df["water_1k"], df["mangrove_1k"] = tree_1k, water_1k, mangrove_1k
    df.to_parquet(d / "tree_cover.parquet")


def write_raster(d, name, value):
    b = score.load_layer(d, "roads").to_crs(3857).total_bounds
    h = w = 40
    tr = from_origin(b[0] - 500, b[3] + 500, (b[2] - b[0] + 1000) / w, (b[3] - b[1] + 1000) / h)
    with rasterio.open(d / name, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
                       crs="EPSG:3857", transform=tr, nodata=float("nan")) as dst:
        dst.write(np.full((1, h, w), value, dtype=np.float32))


@pytest.fixture
def e1(tmp_path):
    """A region with every E1 input: range3k.tif, the built share, landmarks inside only."""
    d = region(tmp_path / "processed")
    write_cover(d, shares=False)
    write_raster(d, "range3k.tif", 450.0)                          # c_grand 0.25
    m = mids(d).to_crs(4326)
    pd.DataFrame({"lon": m.x.to_numpy(), "lat": m.y.to_numpy(),
                  "landmark": np.zeros(len(m), dtype=np.float32)}).to_parquet(d / "protected.parquet")
    chunks, _ = rebuild(d, cache=False)
    return d, chunks


class TestScoreStage:
    def test_without_the_new_inputs_it_is_e1(self, e1):
        """No prom10k.tif, no ~1 km shares, no landmark_near: E1's columns exactly."""
        d, before = e1
        write_raster(d, "prom10k.tif", 2000.0)                     # V alone needs the shares too
        after, _ = rebuild(d, cache=False)
        for c in score.components(before):
            assert np.array_equal(after[c], before[c]), c
        assert np.allclose(before["c_grand"], 0.25)

    def test_v_takes_c_grand_s_slot_by_max(self, e1):
        d, before = e1
        write_cover(d, tree_1k=0.2)
        write_raster(d, "prom10k.tif", 900.0)                      # full, times open land 0.8
        after, _ = rebuild(d, cache=False)
        assert np.allclose(after["c_grand"], 0.8)
        write_raster(d, "prom10k.tif", 400.0)                      # 0.167 * 0.8 < 0.25
        low, _ = rebuild(d, cache=False)
        assert np.allclose(low["c_grand"], before["c_grand"])

    def test_s2_takes_c_water_s_slot_by_max_on_the_sea_only(self, e1):
        d, before = e1
        # Bog Lane (y = 1500) and Main Street (y = 2000) have no water within 350 m.
        # The coast runs 100 m off the first and 200 m off the second.
        gpd.GeoDataFrame(geometry=[shapely.LineString([(0, 1400), (900, 1400)]),
                                   shapely.LineString([(0, 1800), (900, 1800)])],
                         crs=score.CRS_METERS).to_parquet(d / "coastline.parquet")
        y = mids(d).y.round().to_numpy()
        assert (before["c_water"][(y == 1500) | (y == 2000)] == 0).all()
        write_cover(d, water_1k=0.6)
        on, _ = rebuild(d, cache=False)
        assert np.allclose(on["c_water"][y == 1500], 1.0)
        assert np.allclose(on["c_water"][y == 2000], score.WATER_MID)
        rest = (y != 1500) & (y != 2000)
        assert np.array_equal(on["c_water"][rest], before["c_water"][rest])
        write_cover(d, water_1k=0.4)
        shore, _ = rebuild(d, cache=False)
        assert np.array_equal(shore["c_water"], before["c_water"])

    def test_l_credits_landmark_near_with_the_built_gate(self, e1):
        d, _ = e1
        write_cover(d)
        m = mids(d).to_crs(4326)
        pd.DataFrame({"lon": m.x.to_numpy(), "lat": m.y.to_numpy(), "landmark": np.zeros(len(m), np.float32),
                      "landmark_near": np.ones(len(m), np.float32)}).to_parquet(d / "protected.parquet")
        chunks, _ = rebuild(d, cache=False)
        assert (chunks["c_protected"] == 1.0).all()
        write_cover(d, built=0.31)
        chunks, _ = rebuild(d, cache=False)
        assert (chunks["c_protected"] == 0.0).all()

    def test_no_column_is_added(self, e1):
        d, before = e1
        write_cover(d, tree_1k=0.1, water_1k=0.6)
        write_raster(d, "prom10k.tif", 900.0)
        after, _ = rebuild(d, cache=False)
        assert score.components(after) == score.components(before)
        assert np.allclose(after["raw"], score.blend(after))
