"""The regions a national build is cut into, and which region owns each edge.

A region is a *core*, which owns every edge whose midpoint falls inside it, and a
*ring* BUFFER_M wide around it. The ring is read but never owned. Every scenery
term reads at most a few km around a road (score.py's DIST tops out at 900 m,
landcover.py's desert box is 1 km, terrain.py's range window 3 km), so with the ring
an owned edge is scored from the same surroundings a single national build would
give it. docs/national-build.md §2 sets out the method.

Cores are the 48 states and DC (Census TIGER/Line 2025 state polygons, which run
out over their waters), except where one state is too big for one pass: Texas and
California are cut in two, because elevation.py holds its whole mosaic in RAM and
Texas's takes 13.3 GB (docs/us-map-data-findings.md §2).

Ownership is decided on the edge's midpoint, measured in EPSG:5070 from the edge's
lon/lat geometry, so every region computes the same point for the same edge. A
midpoint inside no core is outside the 48 states and DC: Canada or Mexico, in the
slivers the US extract carries. It is owned by the nearest core when that core is
within FOREIGN_TOL_M (a road traced along the border itself), and dropped
otherwise.

Each region is built in its own metric projection. New England's six states keep
common.CRS_METERS (EPSG:26986, Massachusetts Mainland), which is what the deployed
graph was built in and is within 0.1% of true length across New England; it is 2.2%
long at Houston and 4.5% at Key West, so every other region gets a Lambert conformal
conic fitted to its own latitude range, within 0.1% everywhere in it.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely

BUFFER_M = 15_000.0
FOREIGN_TOL_M = 100.0
EQUAL_AREA = 5070
NEW_ENGLAND = ("CT", "MA", "ME", "NH", "RI", "VT")
# (state, name, west, south, east, north): a state cut into parts by a box each.
SPLITS = {
    "TX": [("tx-west", -180, -90, -100.0, 90), ("tx-east", -100.0, -90, 180, 90)],
    "CA": [("ca-south", -180, -90, 180, 36.0), ("ca-north", -180, 36.0, 180, 90)],
}


@dataclass
class Region:
    name: str
    state: str
    core: shapely.Geometry      # lon/lat
    ring: shapely.Geometry      # lon/lat, core + BUFFER_M, simplified

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return tuple(float(x) for x in self.ring.bounds)

    @property
    def crs(self):
        if self.state in NEW_ENGLAND:
            return 26986
        w, s, e, n = self.bbox
        third = (n - s) / 6
        return (f"+proj=lcc +lat_1={s + third:.4f} +lat_2={n - third:.4f} "
                f"+lat_0={(s + n) / 2:.4f} +lon_0={(w + e) / 2:.4f} "
                "+x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs")


def load(states_path: str | Path, only: list[str] | None = None) -> list[Region]:
    """Every region, in a fixed order (by name), or just those named in `only`
    (region names or state abbreviations)."""
    states = gpd.read_parquet(states_path).to_crs(4326)
    regions = []
    for _, row in states.sort_values("STUSPS").iterrows():
        st = row["STUSPS"]
        parts = SPLITS.get(st, [(st.lower(), -180, -90, 180, 90)])
        for name, w, s, e, n in parts:
            core = shapely.intersection(row.geometry, shapely.box(w, s, e, n))
            core_m = gpd.GeoSeries([core], crs=4326).to_crs(EQUAL_AREA)
            ring = core_m.buffer(BUFFER_M).simplify(500.0).to_crs(4326).iloc[0]
            regions.append(Region(name, st, core, ring))
    regions.sort(key=lambda r: r.name)
    if only:
        wanted = {x.lower() for x in only}
        regions = [r for r in regions if r.name in wanted or r.state.lower() in wanted]
    return regions


def write_polygon(region: Region, path: Path):
    """The ring as GeoJSON, for osmium extract."""
    path.write_text(json.dumps({"type": "Feature", "properties": {"name": region.name},
                                "geometry": shapely.geometry.mapping(region.ring)}))


class Owner:
    """Which region owns a point: the core containing it, else the nearest core
    within FOREIGN_TOL_M, else none (-1). Indices are into the list given."""

    def __init__(self, regions: list[Region]):
        self.regions = regions
        cores = gpd.GeoSeries([r.core for r in regions], crs=4326)
        self.cores_m = np.asarray(cores.to_crs(EQUAL_AREA).values)
        for g in self.cores_m:
            shapely.prepare(g)
        self.tree = shapely.STRtree(self.cores_m)

    def of_xy(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Owner index per point, x/y in EPSG:5070."""
        pts = shapely.points(x, y)
        owner = np.full(len(pts), -1, dtype=np.int64)
        hit_pt, hit_core = self.tree.query(pts, predicate="intersects")
        # A point on a shared boundary hits both cores: the lower index wins,
        # which is the same answer in every region that asks.
        order = np.lexsort((hit_core, hit_pt))
        hit_pt, hit_core = hit_pt[order], hit_core[order]
        first = np.r_[True, hit_pt[1:] != hit_pt[:-1]]
        owner[hit_pt[first]] = hit_core[first]
        lost = np.flatnonzero(owner < 0)
        if len(lost):
            near_pt, near_core = self.tree.query_nearest(pts[lost], max_distance=FOREIGN_TOL_M,
                                                         all_matches=False)
            owner[lost[near_pt]] = near_core
        return owner

    def of_lines(self, geoms_lonlat: np.ndarray) -> np.ndarray:
        """Owner index per line, by its midpoint in EPSG:5070."""
        g = gpd.GeoSeries(geoms_lonlat, crs=4326).to_crs(EQUAL_AREA).values
        mid = shapely.line_interpolate_point(g, 0.5, normalized=True)
        return self.of_xy(shapely.get_x(mid), shapely.get_y(mid))

    def of_lonlat(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        g = gpd.GeoSeries(gpd.points_from_xy(lon, lat), crs=4326).to_crs(EQUAL_AREA)
        return self.of_xy(g.x.to_numpy(), g.y.to_numpy())
