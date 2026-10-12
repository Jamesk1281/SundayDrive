"""Terrarium z11 against USGS 3DEP 1 arc-second, tile by tile, in Colorado.

For each Terrarium tile asked for, every pixel centre is looked up in 3DEP's
1 arc-second DEM (nearest pixel), read as a window of the cloud-optimised
GeoTIFF over HTTP: nothing is downloaded whole. Reported per tile:

  - elevation: median and p95 of |Terrarium - 3DEP|, the bias, and the share
    of pixels more than 100 m apart;
  - relief, the quantity score.py reads: max - min over the 13 px window
    elevation.py uses, from each DEM on the same grid, after elevation.py's
    own masking (its -11,000..9,000 m band and the clamp at 0 m). Median and
    p95 of the difference, and the largest.

The corrupt tiles found by terrarium_survey.py are included by name, which is
the test of whether 3DEP is a clean substitute where Terrarium is not.

Usage: python -I dem3dep_vs_terrarium.py <terrarium_tile_dir> <n_random> <out.csv>
                                         [x,y ...]
"""

import csv
import math
import os
import random
import sys
from pathlib import Path

import numpy as np

try:  # GDAL's curl needs a CA bundle; certifi's is the one this venv has.
    import certifi
    os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
except ImportError:
    pass
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")

import rasterio  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402

URL = ("/vsicurl/https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/current/"
       "{cell}/USGS_1_{cell}.tif")
N = 2 ** 11
WIN = 13
SEED = 20261011


def pixel_lonlat(x, y):
    """Centre lon/lat of every pixel of z11 tile (x, y), as 256x256 arrays."""
    i = np.arange(256) + 0.5
    lon = (x + i / 256.0) / N * 360.0 - 180.0
    yy = y + i / 256.0
    lat = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * yy / N))))
    return np.meshgrid(lon, lat)


def dem_at(lon, lat, opened):
    """3DEP elevation at each lon/lat (nearest pixel), NaN where no cell."""
    out = np.full(lon.shape, np.nan)
    # 1x1 degree cells are named for their NORTH-west corner: n40w106 spans
    # lat 39..40 and lon -106..-105.
    north = np.floor(lat).astype(int) + 1
    west = -np.floor(lon).astype(int)
    for n, w in set(zip(north.ravel().tolist(), west.ravel().tolist())):
        cell = f"n{n:02d}w{w:03d}"
        if cell not in opened:
            try:
                opened[cell] = rasterio.open(URL.format(cell=cell))
            except rasterio.errors.RasterioIOError:
                opened[cell] = None
        ds = opened[cell]
        if ds is None:
            continue
        m = (north == n) & (west == w)
        rows, cols = rasterio.transform.rowcol(ds.transform, lon[m], lat[m])
        rows, cols = np.asarray(rows), np.asarray(cols)
        r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()
        win = ds.read(1, window=((r0, r1 + 1), (c0, c1 + 1))).astype(np.float64)
        vals = win[rows - r0, cols - c0]
        if ds.nodata is not None:
            vals[vals == ds.nodata] = np.nan
        out[m] = vals
    return out


def relief(e):
    land = np.clip(e, 0.0, None)
    lo = np.where(np.isnan(land), np.inf, land)
    hi = np.where(np.isnan(land), -np.inf, land)
    r = ndimage.maximum_filter(hi, WIN) - ndimage.minimum_filter(lo, WIN)
    return np.where(np.isfinite(r), r, np.nan)


def main():
    tile_dir, n_random, out = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    named = [tuple(int(v) for v in a.split(",")) for a in sys.argv[4:]]
    allt = sorted(tuple(int(v) for v in p.stem.split("_")[1:]) for p in tile_dir.glob("11_*.png"))
    pick = named + [t for t in random.Random(SEED).sample(allt, n_random) if t not in named]
    opened, rows = {}, []
    for x, y in pick:
        a = np.asarray(Image.open(tile_dir / f"11_{x}_{y}.png").convert("RGB")).astype(np.float64)
        t = a[..., 0] * 256.0 + a[..., 1] + a[..., 2] / 256.0 - 32768.0
        t[(t > 9000) | (t < -11000)] = np.nan                     # elevation.py's band
        lon, lat = pixel_lonlat(x, y)
        d = dem_at(lon, lat, opened)
        ok = ~np.isnan(t) & ~np.isnan(d)
        diff = (t - d)[ok]
        rt, rd = relief(t), relief(d)
        rok = ~np.isnan(rt) & ~np.isnan(rd)
        rdiff = (rt - rd)[rok]
        rows.append({
            "x": x, "y": y, "named": (x, y) in named, "pixels_compared": int(ok.sum()),
            "abs_diff_median_m": round(float(np.median(np.abs(diff))), 1),
            "abs_diff_p95_m": round(float(np.percentile(np.abs(diff), 95)), 1),
            "bias_m": round(float(np.mean(diff)), 2),
            "share_over_100m": round(float(np.mean(np.abs(diff) > 100)), 5),
            "relief_diff_median_m": round(float(np.median(rdiff)), 1),
            "relief_abs_diff_p95_m": round(float(np.percentile(np.abs(rdiff), 95)), 1),
            "relief_diff_max_m": round(float(rdiff.max()), 1),
            "relief_3dep_p50_m": round(float(np.median(rd[rok])), 1),
            "terrarium_min_m": round(float(np.nanmin(t)), 1),
            "dem3dep_min_m": round(float(np.nanmin(d)), 1),
        })
        print(rows[-1], flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
