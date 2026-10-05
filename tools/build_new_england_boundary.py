"""Generate the outline the app uses to answer "is this point in New England?".

    .venv/bin/python tools/build_new_england_boundary.py
    .venv/bin/python tools/build_new_england_boundary.py --zip cb_2024_us_state_500k.zip

Writes `ios/Sources/NewEnglandBoundary.swift`, which `NewEngland.contains` reads.
The check runs on the phone and sends the coordinate nowhere, so the outline has
to ship inside the app. See `docs/new-england-only-brief.md`.

**The source is the US Census Bureau's 2024 cartographic boundary file for the
states, at 1:500,000.** It is public domain. Geofabrik's `.poly` files are the
server's real cut lines, but they are derived from OpenStreetMap, which would put
ODbL data inside an Apache-2.0 source file (brief, trap 8).

What happens to it, in order, and why:

1. **The six states are unioned** into one shape: CT, ME, MA, NH, RI, VT.
2. **Projected to EPSG:5070** (NAD83 / Conus Albers), so the buffer and the
   tolerance below are in metres rather than in degrees, which shrink eastward.
3. **Buffered 500 m outward.** The cartographic file is clipped to a generalised
   shoreline, so a fix on a pier, a causeway or a beach can fall just outside it.
   Northeast Harbor's town dock is 10 m outside the raw outline, for example.
4. **Holes filled.** Buffering closes island chains around the water behind
   them: Casco Bay, Mount Hope Bay and Boston Harbor become holes of 36, 12 and
   10 km². A holed outline would tell someone on the Peaks Island ferry that
   they are not in New England.
5. **Simplified with a 200 m tolerance**, after the buffer so the 500 m margin
   absorbs it. Every island is kept, however small: Little Brewster, with Boston
   Light, is a destination the server can route to.
6. **Rounded to four decimal places**, about 10 m.

The script measures what it built, instead of assuming it, and writes the
measurements into the generated file's header. It refuses to write if the
outline does not contain the whole Census outline.
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
STATES = ["CT", "ME", "MA", "NH", "RI", "VT"]
PROJECTED = 5070          # NAD83 / Conus Albers, metres
BUFFER_M = 500
TOLERANCE_M = 200
DECIMALS = 4

REPO = Path(__file__).resolve().parent.parent
OUTPUT = REPO / "ios" / "Sources" / "NewEnglandBoundary.swift"

# Points the outline must get right, as (latitude, longitude). The Swift tests
# repeat these; they are here too so a rebuild fails before it reaches Xcode.
MUST_BE_INSIDE = {
    "Boston": (42.3601, -71.0589),
    "Fort Kent ME": (47.2587, -68.5895),
    "Lubec ME": (44.8606, -66.9842),
    "Northeast Harbor ME, the town dock": (44.2959, -68.2856),
    "Estcourt Station ME, the northern tip": (47.4597, -69.2240),
    "Peaks Island ME": (43.6556, -70.1990),
    "Block Island RI": (41.1720, -71.5578),
}
MUST_BE_OUTSIDE = {
    "Edmundston NB, Saint-Jacques": (47.4426, -68.3829),
    "Plattsburgh NY": (44.6995, -73.4529),
    "Montauk NY": (41.0359, -71.9545),
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
    six = states[states.STUSPS.isin(STATES)]
    missing = set(STATES) - set(six.STUSPS)
    if missing:
        sys.exit(f"the source has no {sorted(missing)}")

    census = unary_union(six.to_crs(PROJECTED).geometry.values)
    outline = without_holes(census.buffer(BUFFER_M, quad_segs=8))
    outline = without_holes(outline.simplify(TOLERANCE_M, preserve_topology=True))
    if not outline.contains(census):
        sys.exit("the simplified outline no longer contains the Census outline; "
                 "lower the tolerance or raise the buffer")
    return census, outline


def measure(census, outline) -> tuple[float, float]:
    """The margin the outline keeps around the Census land, both ways, in metres.

    Inner: how close the Census outline's edge comes to this one's, sampled every
    50 m along it. Outer: how far this outline's edge strays from any Census
    land, sampled every 100 m along it.
    """
    edge = unary_union([p.exterior for p in polygons(outline)])
    census_edge = census.boundary
    inner = min(edge.distance(census_edge.interpolate(d))
                for d in np.arange(0, census_edge.length, 50))
    outer = max(census.distance(edge.interpolate(d))
                for d in np.arange(0, edge.length, 100))
    return inner, outer


def rings_in_degrees(outline) -> list[list[tuple[float, float]]]:
    """Exterior rings as (latitude, longitude), rounded, closing vertex dropped."""
    geographic = gpd.GeoSeries([outline], crs=PROJECTED).to_crs(4326).iloc[0]
    rings = []
    for polygon in sorted(polygons(geographic), key=lambda p: -p.area):
        coords = [(round(lat, DECIMALS), round(lon, DECIMALS))
                  for lon, lat in polygon.exterior.coords[:-1]]
        # Rounding can make neighbours equal; a repeated vertex is a zero-length
        # edge, harmless to the crossing test but noise in the file.
        deduped = [c for i, c in enumerate(coords) if c != coords[i - 1]]
        rings.append(deduped)
    return rings


def check(rings) -> None:
    """Re-test the named points against the rounded rings, as the app will."""
    shape = unary_union([Polygon([(lon, lat) for lat, lon in ring]) for ring in rings])
    if not shape.is_valid:
        sys.exit("rounding made the outline invalid")
    for name, (lat, lon) in MUST_BE_INSIDE.items():
        if not shape.contains(Point(lon, lat)):
            sys.exit(f"{name} should be inside")
    for name, (lat, lon) in MUST_BE_OUTSIDE.items():
        if shape.contains(Point(lon, lat)):
            sys.exit(f"{name} should be outside")


def swift(rings, digest: str, inner: float, outer: float) -> str:
    vertices = sum(len(r) for r in rings)
    lats = [lat for ring in rings for lat, _ in ring]
    lons = [lon for ring in rings for _, lon in ring]

    def number(x: float) -> str:
        return f"{x:.{DECIMALS}f}"

    lines = [
        "// GENERATED by tools/build_new_england_boundary.py. Do not edit by hand;",
        "// rerun the script instead.",
        "//",
        "// The six New England states as one outline, for the on-device test",
        "// `NewEngland.contains`. Nothing here leaves the phone.",
        "//",
        "// Source:     US Census Bureau, 2024 cartographic boundary file, states,",
        "//             1:500,000 (cb_2024_us_state_500k). Public domain.",
        f"//             {SOURCE_URL}",
        f"//             SHA-256 {digest}",
        f"// States:     {', '.join(STATES)}, unioned.",
        f"// Buffer:     {BUFFER_M} m outward, in EPSG:{PROJECTED}, so piers, causeways and",
        "//             coastal fixes count as inside.",
        "// Holes:      filled. Water enclosed by New England (Casco Bay, Boston",
        "//             Harbor) is New England.",
        f"// Tolerance:  {TOLERANCE_M} m (Douglas-Peucker, topology-preserving), after the",
        "//             buffer. Every island is kept.",
        f"// Rounding:   {DECIMALS} decimal places, about 10 m.",
        f"// Measured:   the Census outline is at least {inner:.0f} m inside this one",
        f"//             everywhere, and this one strays at most {outer:.0f} m from",
        "//             Census land.",
        f"// Size:       {len(rings)} rings, {vertices} vertices.",
        "",
        "/// The outline behind `NewEngland.contains`. Generated; see the header.",
        "enum NewEnglandBoundary {",
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
          f"-> {OUTPUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
