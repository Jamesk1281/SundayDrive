"""Feature extraction for the scenery-type candidates: DEM, WorldCover and coastline.

All inputs are read-only caches the national build left behind:
  data/national/build/raw/terrain/11_<x>_<y>.png   Terrarium, zoom 11
  data/national/build/raw/worldcover/<tile>.tif    ESA WorldCover v200 2021
  data/national/regions/<r>.osm.pbf                the region rings (coastline)
Nothing is fetched and nothing in data/ is written. A Terrarium tile absent from the
cache is a hole (NaN), never sea level; a WorldCover tile absent from the cache counts
as water, as wc_sample.py does (WorldCover omits all-ocean cells), and is logged.

Every window follows the pipeline's conventions: pixel ground size measured at
elevation.RELIEF_REF_LAT, the DEM despiked with terrain.despike, ocean clipped to 0 m,
and the ~1 km land-cover box is wc_sample.py's 9 x 11 blocks of 12 x 12 pixels.
"""
import json, math, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd, shapely
from PIL import Image
from scipy.ndimage import maximum_filter, uniform_filter

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "pipeline"))
from elevation import ELEV_MAX_M, ELEV_MIN_M, RELIEF_REF_LAT, decode_terrarium, lonlat_to_tile  # noqa: E402
from terrain import despike, range_within  # noqa: E402

MAIN = Path(os.environ.get("SUNDAYDRIVE_MAIN", REPO))
RAW = MAIN / "data" / "national" / "build" / "raw"
PBF = MAIN / "data" / "national" / "regions"
Z, TILE = 11, 256
R_EARTH = 6378137.0
PROM_KM = (5, 10, 15)
ROCK_WIN_M = 250.0
WC_NAMES = ["tree", "shrub", "grass", "crop", "built", "bare", "snow", "water", "wetland", "mangrove", "moss"]
WC_CODES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]


def merc(lon, lat):
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    return R_EARTH * np.radians(lon), R_EARTH * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


# ------------------------------------------------------------------ DEM
def dem_mosaic(bbox, margin_km=17.0):
    """Despiked elevation over bbox plus a margin, with its mercator origin and pixel size."""
    lon0, lat0, lon1, lat1 = bbox
    dlat = margin_km / 111.0
    dlon = margin_km / (111.0 * math.cos(math.radians(max(abs(lat0), abs(lat1)))))
    x0f, y0f = lonlat_to_tile(lon0 - dlon, lat1 + dlat, Z)
    x1f, y1f = lonlat_to_tile(lon1 + dlon, lat0 - dlat, Z)
    tx = range(int(x0f), int(x1f) + 1); ty = range(int(y0f), int(y1f) + 1)
    elev = np.full((len(ty) * TILE, len(tx) * TILE), np.nan, np.float32)
    missing = 0
    for j, y in enumerate(ty):
        for i, x in enumerate(tx):
            p = RAW / "terrain" / f"{Z}_{x}_{y}.png"
            if not p.exists():
                missing += 1; continue
            elev[j * TILE:(j + 1) * TILE, i * TILE:(i + 1) * TILE] = decode_terrarium(np.asarray(Image.open(p).convert("RGB")))
    elev[~np.isnan(elev) & ((elev > ELEV_MAX_M) | (elev < ELEV_MIN_M))] = np.nan
    z, n_spike = despike(elev); del elev
    np.clip(z, 0.0, None, out=z)
    n = 2 ** Z
    px = 2 * math.pi * R_EARTH / (n * TILE)                     # mercator metres per pixel
    left = tx[0] * TILE * px - math.pi * R_EARTH
    top = math.pi * R_EARTH - ty[0] * TILE * px
    return z, (left, top, px), dict(tiles=len(tx) * len(ty), missing=missing, spikes=n_spike)


def dem_features(lon, lat, bbox):
    """z, relief250 and prom{5,10,15}k at each point (see cands.py)."""
    z, (left, top, px), info = dem_mosaic(bbox)
    mx, my = merc(lon, lat)
    col = np.floor((mx - left) / px).astype(int); row = np.floor((top - my) / px).astype(int)
    ok = (row >= 0) & (row < z.shape[0]) & (col >= 0) & (col < z.shape[1])
    rr, cc = np.clip(row, 0, z.shape[0] - 1), np.clip(col, 0, z.shape[1] - 1)
    px_ground = px * math.cos(math.radians(RELIEF_REF_LAT))
    out = {"z": np.where(ok, z[rr, cc], np.nan)}
    win = max(3, int(round(ROCK_WIN_M / px_ground)) | 1)
    out["relief250"] = np.where(ok, range_within(z, win)[rr, cc], np.nan)
    a = np.where(np.isnan(z), -np.inf, z)
    for km in PROM_KM:
        w = int(round(2 * km * 1000 / px_ground)) | 1
        mx_ = maximum_filter(a, size=w)[rr, cc]
        out[f"prom{km}k"] = np.where(ok & np.isfinite(mx_), mx_ - out["z"], np.nan)
    info.update(rock_win_px=win, rock_win_m=round(win * px_ground))
    return pd.DataFrame(out), info


# ------------------------------------------------------------------ WorldCover
def _tile_name(r, c):
    lat0 = 90 - (r + 1) * 3; lon0 = c * 3 - 180
    return f"{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}{'E' if lon0 >= 0 else 'W'}{abs(lon0):03d}"


def wc_features(lon, lat, pad=10):
    """<class>_1k (and _100) at each point, wc_sample.py's geometry, from the cached tifs."""
    import rasterio
    from rasterio.windows import Window
    bc = np.floor((np.asarray(lon) + 180) * 1000).astype(np.int64)   # global 100 m block index
    br = np.floor((90 - np.asarray(lat)) * 1000).astype(np.int64)
    b0r, b1r = br.min() - pad, br.max() + pad + 1
    b0c, b1c = bc.min() - pad, bc.max() + pad + 1
    H, Wd = b1r - b0r, b1c - b0c
    mos = np.zeros((len(WC_NAMES), H, Wd), np.uint8)
    absent = []
    for tr in range(b0r // 3000, (b1r - 1) // 3000 + 1):
        for tc in range(b0c // 3000, (b1c - 1) // 3000 + 1):
            r0, r1 = max(b0r, tr * 3000), min(b1r, (tr + 1) * 3000)
            c0, c1 = max(b0c, tc * 3000), min(b1c, (tc + 1) * 3000)
            dst = (slice(r0 - b0r, r1 - b0r), slice(c0 - b0c, c1 - b0c))
            p = RAW / "worldcover" / f"{_tile_name(tr, tc)}.tif"
            if not p.exists():
                absent.append(_tile_name(tr, tc))
                mos[(WC_NAMES.index("water"),) + dst] = 144
                continue
            with rasterio.open(p) as src:
                for s0 in range(r0, r1, 200):               # strips of 200 blocks bound the memory
                    s1 = min(r1, s0 + 200)
                    a = src.read(1, window=Window((c0 - tc * 3000) * 12, (s0 - tr * 3000) * 12,
                                                  (c1 - c0) * 12, (s1 - s0) * 12))
                    b = a.reshape(s1 - s0, 12, c1 - c0, 12)
                    for k, code in enumerate(WC_CODES):
                        mos[k, s0 - b0r:s1 - b0r, c0 - b0c:c1 - b0c] = (b == code).sum(axis=(1, 3), dtype=np.uint16)
                    del a, b
    rr, cc = br - b0r, bc - b0c
    out = {}
    for k, nm in enumerate(WC_NAMES):
        a = mos[k].astype(np.float32) / 144
        out[f"{nm}_100"] = a[rr, cc]
        out[f"{nm}_1k"] = uniform_filter(a, size=(9, 11), mode="nearest")[rr, cc]
        del a
    return pd.DataFrame(out), sorted(set(absent))


# ------------------------------------------------------------------ coastline
def coastline_lines(region, bbox=None):
    """natural=coastline ways from a region ring, as lon/lat LineStrings (osmium, temp files only)."""
    with tempfile.TemporaryDirectory() as td:
        src = PBF / f"{region}.osm.pbf"
        if bbox is not None:
            clip = Path(td) / "clip.osm.pbf"
            subprocess.run(["osmium", "extract", "-b", ",".join(map(str, bbox)), str(src), "-o", str(clip), "-O"],
                           check=True, capture_output=True)
            src = clip
        f = Path(td) / "c.osm.pbf"; g = Path(td) / "c.geojsonseq"
        subprocess.run(["osmium", "tags-filter", str(src), "w/natural=coastline", "-o", str(f), "-O"], check=True, capture_output=True)
        subprocess.run(["osmium", "export", str(f), "-o", str(g), "-O", "-f", "geojsonseq", "--geometry-types=linestring"],
                       check=True, capture_output=True)
        lines = []
        for ln in open(g):
            ln = ln.strip().lstrip("\x1e")
            if ln:
                lines.append(shapely.geometry.shape(json.loads(ln)["geometry"]))
    return np.array(lines, dtype=object)


def coast_distance(lon, lat, lines, cap=1000.0):
    """Metres (EPSG:5070) from each point to the nearest coastline line; inf beyond cap or with none."""
    import pyproj
    d = np.full(len(lon), np.inf)
    if len(lines) == 0:
        return d
    tf = pyproj.Transformer.from_crs(4326, 5070, always_xy=True)
    L = shapely.segmentize(shapely.transform(lines, lambda xy: np.column_stack(tf.transform(xy[:, 0], xy[:, 1]))), 2000.0)
    # Long coastline ways are cut into short pieces so the tree's boxes stay tight.
    parts = []
    for g in L:
        c = shapely.get_coordinates(g)
        for k in range(0, len(c) - 1, 50):
            parts.append(shapely.linestrings(c[k:k + 51]))
    parts = np.array(parts, dtype=object)
    tree = shapely.STRtree(parts)
    x, y = tf.transform(np.asarray(lon), np.asarray(lat))
    pts = shapely.points(x, y)
    (i, _), dist = tree.query_nearest(pts, max_distance=cap, return_distance=True, all_matches=False)
    d[i] = dist
    return d
