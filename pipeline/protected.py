"""Flag every road chunk that runs through a landmark protected area (PAD-US 4.1).

A landmark is a national park, monument, conservation area, recreation area,
scenic/botanical/volcanic area, lake- or seashore, wilderness or wilderness study
area, or a state park or state wilderness (PAD-US `Des_Tp` codes below). It is a
designation, like the scenic-byway tag, not a measurement of what the land looks
like -- which is why its weight in score.py is the byway tag's, and why it is a
small term: 0.4% of New England's road chunks, 0.7% of Colorado's and 2.8% of
Utah's fall inside one (docs/national-scenery-scoring-verdict.md §8).

This stage flags every chunk inside a landmark, city parks included. score.py
then drops the ones whose surroundings are built up (PROTECTED_BUILT_MAX): PAD-US
files Boston's river reservations as state parks, and Storrow Drive runs through
one. That takes New England from 0.41% to 0.31% of chunks and leaves Utah at 2.77%
(docs/national-scenery-components.md §3).

National forests, BLM land and other multiple-use public land are deliberately not
landmarks. OSM's `boundary=protected_area` polygons already put national forests
into c_forest's green half, and in the West most public land is range.

Reads the PAD-US 4.1 national geodatabase (public domain, USGS; 1.52 GB zip from
ScienceBase item 652d4fc5d34e44db0e2ee45e, whose `catalog/file/get/<item>?name=`
endpoint serves the file -- the item's "manager" links are web pages) and writes:

  data/processed/protected.parquet   lon, lat, landmark (0/1) per chunk

Joined by position, like tree_cover.parquet: this stage chunks the roads with
score.py's own chunk_roads() and stores the midpoint it tested, and score.py
refuses a file whose midpoints do not match.

The layer is read by bounding box in its own CRS. A `where` clause is the obvious
filter and the wrong one: GDAL's FileGDB driver returns no rows unless the
filtered field is also among the columns read, and drops rows on `AND`.

ScienceBase has put the geodatabase behind a sign-in since 2026-10-18. The same
layer is a public USGS feature service, and tools/national_build/padus_landmarks.py
fetches its landmark rows for the 48 states and DC into a GeoParquet, which this
stage reads in place of the geodatabase (docs/national-build.md).

Usage: python protected.py <processed_dir> <PADUS4_1Geodatabase.gdb | landmarks.parquet>
"""

import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from score import chunk_roads, load_layer

LAYER = "PADUS4_1Combined_Proclamation_Marine_Fee_Designation_Easement"
# Designation types that name a place people go to look at. Codes from the
# geodatabase's own Designation_Type table.
LANDMARK = {"NP", "NM", "NCA", "NRA", "NSBV", "NLS", "WA", "WSA", "SP", "SW"}
# Fee (ownership) and Designation (overlay) polygons. Proclamation boundaries
# include private inholdings; easements are not public places; marine areas are
# not driven.
FEATURE_CLASSES = {"Fee", "Designation"}


def landmark_flags(lon: np.ndarray, lat: np.ndarray, polygons: gpd.GeoDataFrame) -> np.ndarray:
    """1.0 where a point falls in any landmark polygon, else 0.0."""
    keep = (polygons["FeatClass"].isin(FEATURE_CLASSES).to_numpy()
            & polygons["Des_Tp"].isin(LANDMARK).to_numpy())
    geoms = shapely.make_valid(polygons.geometry.values[keep])
    flags = np.zeros(len(lon), dtype=np.float32)
    if len(geoms) == 0:
        return flags
    pts = gpd.GeoSeries(gpd.points_from_xy(lon, lat), crs=4326).to_crs(polygons.crs).values
    hit = shapely.STRtree(geoms).query(pts, predicate="intersects")
    flags[np.unique(hit[0])] = 1.0
    return flags


def main(processed_dir: str, gdb: str):
    d = Path(processed_dir)
    t0 = time.time()
    chunks = chunk_roads(load_layer(d, "roads"))
    mids = chunks.geometry.interpolate(0.5, normalized=True).to_crs(4326)
    lon, lat = mids.x.to_numpy(), mids.y.to_numpy()
    print(f"{len(chunks):,} chunks in {time.time() - t0:.0f}s")

    if str(gdb).endswith(".parquet"):
        # Already in lon/lat, and small (9,048 polygons nationally), so read whole and cut.
        polygons = gpd.read_parquet(gdb, columns=["FeatClass", "Des_Tp", "geometry"])
        polygons = polygons.cx[lon.min():lon.max(), lat.min():lat.max()]
    else:
        crs = pyogrio.read_info(gdb, layer=LAYER)["crs"]
        corners = gpd.GeoSeries(gpd.points_from_xy([lon.min(), lon.max()], [lat.min(), lat.max()]),
                                crs=4326).to_crs(crs)
        # Albers bends lines of longitude, so pad the box rather than trust two corners.
        pad = 50_000.0
        bbox = (corners.x.min() - pad, corners.y.min() - pad, corners.x.max() + pad, corners.y.max() + pad)
        polygons = pyogrio.read_dataframe(gdb, layer=LAYER, columns=["FeatClass", "Des_Tp"], bbox=bbox)
    print(f"{len(polygons):,} PAD-US polygons in the region's box in {time.time() - t0:.0f}s")

    flags = landmark_flags(lon, lat, polygons)
    out = d / "protected.parquet"
    pd.DataFrame({"lon": lon, "lat": lat, "landmark": flags}).to_parquet(out)
    km = chunks.geometry.length.to_numpy() / 1000
    print(f"landmark: {100 * flags.mean():.2f}% of chunks, "
          f"{100 * km[flags > 0].sum() / km.sum():.2f}% of km; wrote {out} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
