"""Generate the outline the app uses to answer "is this point somewhere we cover?".

    .venv/bin/python ios/scripts/build_coverage_boundary.py
    .venv/bin/python ios/scripts/build_coverage_boundary.py --zip cb_2024_us_state_500k.zip

Writes `ios/Sources/CoverageBoundary.swift`, which `Coverage.contains` reads. The
check runs on the phone and sends the coordinate nowhere, so the outline has to
ship inside the app. See `docs/app-goes-national.md`.

The national counterpart of `tools/build_new_england_boundary.py`, which stays
with the New England build on `main`. Same source, same steps, same margins, so
the edge behaves the same way it did around New England:

1. **The 48 contiguous states and DC are unioned** into one shape: every state
   in the Census file except the ones listed in `LEFT_OUT`.
2. **Projected to EPSG:5070** (NAD83 / Conus Albers, metres).
3. **Buffered 500 m outward**, so a fix on a pier, a causeway or a beach counts.
4. **Holes filled.**
5. **Simplified with a 200 m tolerance**, after the buffer. Every island is kept.
6. **Rounded to four decimal places**, about 10 m.

The source is the US Census Bureau's 2024 cartographic boundary file for the
states, at 1:500,000. It is public domain, which matters: an outline derived
from OpenStreetMap would put ODbL data inside an Apache-2.0 source file.

The script measures what it built and writes the measurements into the
generated file's header. It refuses to write if the outline does not contain
the whole Census outline, or if any of the named points below comes out on the
wrong side.
"""

import argparse
import hashlib
import sys
import tempfile
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union

SOURCE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip"
# Everything in the file that is not one of the 48 contiguous states or DC.
LEFT_OUT = ["AK", "HI", "PR", "VI", "GU", "AS", "MP"]
EXPECTED_COUNT = 49       # 48 states and DC
PROJECTED = 5070          # NAD83 / Conus Albers, metres
BUFFER_M = 500
TOLERANCE_M = 200
DECIMALS = 4

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "Sources" / "CoverageBoundary.swift"

# Points the outline must get right, as (latitude, longitude). The Swift tests
# repeat these; they are here too so a rebuild fails before it reaches Xcode.
MUST_BE_INSIDE = {
    "Boston MA": (42.3601, -71.0589),
    "Washington DC": (38.8977, -77.0365),
    "Fort Kent ME": (47.2587, -68.5895),
    "Lubec ME": (44.8606, -66.9842),
    "Estcourt Station ME, the northern tip": (47.4597, -69.2240),
    "Key West FL": (24.5551, -81.7800),
    "Friday Harbor WA, San Juan Island": (48.5343, -123.0171),
    "Cape Flattery WA, the north-western tip": (48.3833, -124.7144),
    "Avalon CA, Catalina Island": (33.3428, -118.3268),
    "Ocracoke NC": (35.1146, -75.9810),
    "Point Roberts WA": (48.9860, -123.0680),
    "Northwest Angle MN": (49.3450, -95.0650),
    "San Ysidro CA, at the Mexican border": (32.5430, -117.0300),
    "Brownsville TX": (25.9017, -97.4975),
    "Detroit MI": (42.3314, -83.0458),
    "Montauk NY": (41.0359, -71.9545),
}
MUST_BE_OUTSIDE = {
    "Edmundston NB": (47.3730, -68.3251),
    "Windsor ON": (42.3000, -83.0200),
    "Victoria BC": (48.4284, -123.3656),
    "Vancouver BC": (49.2827, -123.1207),
    "Toronto ON": (43.6532, -79.3832),
    "Montreal QC": (45.5017, -73.5673),
    "Tijuana BC": (32.5149, -117.0382),
    "Ciudad Juarez CHIH": (31.7200, -106.4500),
    "Nogales SON": (31.3000, -110.9400),
    "Matamoros TAMPS": (25.8690, -97.5027),
    "Nassau, Bahamas": (25.0443, -77.3504),
    "Havana, Cuba": (23.1136, -82.3666),
    "Hamilton, Bermuda": (32.2949, -64.7814),
    "Anchorage": (61.2181, -149.9003),
    "Honolulu": (21.3069, -157.8583),
    "San Juan": (18.4655, -66.1057),
    "The Gulf of Mexico": (26.0, -90.0),
    "The Atlantic, off Cape Hatteras": (35.0, -74.0),
    "The Pacific, off San Francisco": (37.7, -123.5),
    "Lake Superior, mid-lake": (47.6, -87.5),
}


def fetch(zip_path: Path | None) -> Path:
    if zip_path is not None:
        return zip_path
    target = Path(tempfile.mkdtemp()) / SOURCE_URL.rsplit("/", 1)[1]
    print(f"downloading {SOURCE_URL}")
    urllib.request.urlretrieve(SOURCE_URL, target)
    return target


def polygons(geometry) -> list[Polygon]:
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return [geometry]


def without_holes(geometry):
    return unary_union([Polygon(p.exterior) for p in polygons(geometry)])


def build(zip_path: Path):
    states = gpd.read_file(f"zip://{zip_path}")
    kept = states[~states.STUSPS.isin(LEFT_OUT)]
    if len(kept) != EXPECTED_COUNT or "DC" not in set(kept.STUSPS):
        sys.exit(f"expected the 48 states and DC, got {sorted(kept.STUSPS)}")

    census = unary_union(kept.to_crs(PROJECTED).geometry.values)
    outline = without_holes(census.buffer(BUFFER_M, quad_segs=8))
    outline = without_holes(outline.simplify(TOLERANCE_M, preserve_topology=True))
    if not outline.contains(census):
        sys.exit("the simplified outline no longer contains the Census outline; "
                 "lower the tolerance or raise the buffer")
    return census, outline


def measure(census, outline) -> tuple[float, float]:
    """The margin the outline keeps around the Census land, both ways, in metres.

    Inner: how close the Census outline's edge comes to this one's, sampled every
    200 m along it. Outer: how far this outline's edge strays from any Census
    land, sampled every 200 m along it. Coarser steps than the New England
    script's 50 m and 100 m, because the edge is about forty times as long.
    """
    edge = unary_union([p.exterior for p in polygons(outline)])
    census_edge = census.boundary
    inner = edge.distance(unary_union(
        [census_edge.interpolate(d) for d in np.arange(0, census_edge.length, 200)]))
    outer = max(census.distance(edge.interpolate(d))
                for d in np.arange(0, edge.length, 200))
    return inner, outer


def rings_in_degrees(outline) -> list[list[tuple[float, float]]]:
    """Exterior rings as (latitude, longitude), rounded, closing vertex dropped."""
    geographic = gpd.GeoSeries([outline], crs=PROJECTED).to_crs(4326).iloc[0]
    rings = []
    for polygon in sorted(polygons(geographic), key=lambda p: -p.area):
        coords = [(round(lat, DECIMALS), round(lon, DECIMALS))
                  for lon, lat in polygon.exterior.coords[:-1]]
        deduped = [c for i, c in enumerate(coords) if c != coords[i - 1]]
        rings.append(deduped)
    return rings


def check(rings) -> None:
    """Re-test the named points against the rounded rings, as the app will."""
    shape = unary_union([Polygon([(lon, lat) for lat, lon in ring]) for ring in rings])
    if not shape.is_valid:
        sys.exit("rounding made the outline invalid")
    wrong = [f"{name} should be inside" for name, (lat, lon) in MUST_BE_INSIDE.items()
             if not shape.contains(Point(lon, lat))]
    wrong += [f"{name} should be outside" for name, (lat, lon) in MUST_BE_OUTSIDE.items()
              if shape.contains(Point(lon, lat))]
    if wrong:
        sys.exit("; ".join(wrong))


def swift(rings, digest: str, inner: float, outer: float) -> str:
    vertices = sum(len(r) for r in rings)
    lats = [lat for ring in rings for lat, _ in ring]
    lons = [lon for ring in rings for _, lon in ring]

    def number(x: float) -> str:
        return f"{x:.{DECIMALS}f}"

    lines = [
        "// GENERATED by ios/scripts/build_coverage_boundary.py. Do not edit by",
        "// hand; rerun the script instead.",
        "//",
        "// The 48 contiguous states and DC as one outline, for the on-device test",
        "// `Coverage.contains`. Nothing here leaves the phone.",
        "//",
        "// Source:     US Census Bureau, 2024 cartographic boundary file, states,",
        "//             1:500,000 (cb_2024_us_state_500k). Public domain.",
        f"//             {SOURCE_URL}",
        f"//             SHA-256 {digest}",
        "// States:     the 48 contiguous states and DC, unioned.",
        f"// Buffer:     {BUFFER_M} m outward, in EPSG:{PROJECTED}, so piers, causeways and",
        "//             coastal fixes count as inside.",
        "// Holes:      filled.",
        f"// Tolerance:  {TOLERANCE_M} m (Douglas-Peucker, topology-preserving), after the",
        "//             buffer. Every island is kept.",
        f"// Rounding:   {DECIMALS} decimal places, about 10 m.",
        f"// Measured:   the Census outline is at least {inner:.0f} m inside this one",
        f"//             everywhere, and this one strays at most {outer:.0f} m from",
        "//             Census land.",
        f"// Size:       {len(rings)} rings, {vertices} vertices.",
        "",
        "/// The outline behind `Coverage.contains`. Generated; see the header.",
        "enum CoverageBoundary {",
        "    /// The bounding box of `rings`, in degrees.",
        f"    static let south = {number(min(lats))}",
        f"    static let north = {number(max(lats))}",
        f"    static let west = {number(min(lons))}",
        f"    static let east = {number(max(lons))}",
        "",
        "    /// Closed rings, largest first, each a flat list of latitude, longitude",
        "    /// pairs. The first vertex is not repeated at the end. The rings do not",
        "    /// overlap, and none is a hole.",
        "    static let rings: [[Double]] = [",
    ]
    per_line = 6
    for ring in rings:
        lines.append("        [")
        for i in range(0, len(ring), per_line):
            chunk = ring[i:i + per_line]
            lines.append("            " + " ".join(
                f"{number(lat)}, {number(lon)}," for lat, lon in chunk))
        lines.append("        ],")
    lines += ["    ]", "}", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--zip", type=Path, help="a local copy of the Census zip")
    args = parser.parse_args()

    zip_path = fetch(args.zip)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    census, outline = build(zip_path)
    inner, outer = measure(census, outline)
    rings = rings_in_degrees(outline)
    check(rings)

    OUTPUT.write_text(swift(rings, digest, inner, outer), encoding="utf-8")
    vertices = sum(len(r) for r in rings)
    print(f"{len(rings)} rings, {vertices} vertices, inner margin {inner:.0f} m, "
          f"outer reach {outer:.0f} m, {OUTPUT.stat().st_size / 1024:.0f} KB "
          f"-> {OUTPUT}")


if __name__ == "__main__":
    main()
