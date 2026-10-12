"""Mountain- and canyon-scale terrain: the elevation range within ~3 km of each pixel.

`relief.tif` (elevation.py) measures relief over ~750 m and score.py caps it at
RELIEF_FULL = 100 m. That scale was fitted to New England, and in the West it
runs out: 46.9% of Colorado's byway km and 45.3% of Utah's sit at the cap, against
New England's 19.4%, so relief cannot tell one mountain road from the next. Raising
the cap costs New England its holdout (0.766 -> 0.750 at 250 m) and buys the West
nothing. What it needs is a second, larger scale *above* the cap.
docs/national-scenery-scoring-verdict.md §4-5 measures both.

Reads data/processed/elevation.tif and writes:

  data/processed/range3k.tif   max - min elevation within ~3 km (m), EPSG:3857,
                               same grid as elevation.tif, NaN = no data

score.py samples it into `c_grand`. A separate stage rather than a second filter
pass inside elevation.py, for two reasons: it runs on any existing build without
re-fetching a tile, and elevation.py's in-RAM mosaic is already the memory wall a
national build has to tile around.

**Despiking.** Terrarium has corrupt pixels that decode to plausible heights. In New
England they sit on sea-level shores (docs/us-map-data-findings.md: in-band spikes
in the deployed relief.tif). In Colorado's Moffat County there is a 12 x 9 px pit
about 2,000 m deep, where the state's lowest point is 1,011 m; it put a 2,300 m
"range" under County Road 23. A 3 km window spreads one bad pixel across 2,800
neighbours, so this stage removes what elevation.py's physical band
(ELEV_MIN_M..ELEV_MAX_M) cannot, with two rules:

- a pixel more than SPIKE_M from the median of its 5x5 neighbourhood. A planar
  slope's median is its centre value, so a real cliff, even a 60-degree one at
  about 100 m per 57 m pixel, stays well under 250 m;
- a pixel more than BLOB_M from a ~1.1 km coarse median, grown by BLOB_GROW px,
  for patches too wide for the first rule.

Measured on the three builds of 2026-10-12, the rules flag 1,373 px in New England,
2 in Utah and 463 in Colorado. They take County Road 23 back to 740 m and leave
every deep-canyon road the evaluation checked unchanged (the Black Canyon's rims,
Zion Canyon, Big Cottonwood Canyon, the Mount Washington Auto Road).

Usage: python terrain.py <processed_dir>
"""

import math
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, maximum_filter, median_filter, minimum_filter

from elevation import ELEV_MAX_M, ELEV_MIN_M, RELIEF_REF_LAT

# Ground size of the window, measured the way elevation.py measures RELIEF_WINDOW_M:
# at RELIEF_REF_LAT, so one constant means one distance in every region.
RANGE_WINDOW_M = 3000.0
# How far a pixel may sit from its 5x5 median before it is treated as corrupt.
SPIKE_M = 250.0
SPIKE_WINDOW = 5
# Blobs: a corrupt patch wider than the 5x5 window survives the rule above (its
# own median is corrupt too). Colorado's Moffat County one is 12 x 9 px, a pit
# about 2,000 m deep with ringing at its rim. So a second test runs at ~1.1 km:
# the median of 4x4-pixel block medians over a 5x5-block neighbourhood. No real
# road-scale terrain sits BLOB_M below or above that: the Black Canyon's Painted
# Wall is 690 m, Zion's walls under 1,000 m. The flagged patch is grown by
# BLOB_GROW px to take the ringing with it.
BLOB_BLOCK = 4
BLOB_M = 1200.0
BLOB_GROW = 2


def despike(elev: np.ndarray) -> tuple[np.ndarray, int]:
    """Copy of `elev` with corrupt pixels set to NaN, and how many were.

    Holes are filled with the global median only so the median filter can run;
    a hole never becomes data.
    """
    z = elev.astype(np.float32, copy=True)
    z[~np.isnan(z) & ((z > ELEV_MAX_M) | (z < ELEV_MIN_M))] = np.nan
    gap = np.isnan(z)
    filled = np.where(gap, np.nanmedian(z) if (~gap).any() else 0.0, z)
    med = median_filter(filled, size=SPIKE_WINDOW)
    spike = ~gap & (np.abs(filled - med) > SPIKE_M)
    del med
    spike |= ~gap & blob_mask(filled)
    z[spike] = np.nan
    return z, int(spike.sum())


def blob_mask(filled: np.ndarray) -> np.ndarray:
    """Pixels more than BLOB_M from the ~1.1 km coarse median, grown by BLOB_GROW."""
    b = BLOB_BLOCK
    H, W = filled.shape
    Hp, Wp = -(-H // b) * b, -(-W // b) * b
    pad = np.pad(filled, ((0, Hp - H), (0, Wp - W)), mode="edge")
    blocks = np.median(pad.reshape(Hp // b, b, Wp // b, b).transpose(0, 2, 1, 3)
                       .reshape(Hp // b, Wp // b, b * b), axis=2)
    del pad
    coarse = median_filter(blocks, size=5)
    up = np.repeat(np.repeat(coarse, b, axis=0), b, axis=1)[:H, :W]
    far = np.abs(filled - up) > BLOB_M
    return binary_dilation(far, iterations=BLOB_GROW) if far.any() else far


def range_within(z: np.ndarray, win: int) -> np.ndarray:
    """max - min within a win x win window, holes invisible (NaN only where the
    pixel itself, or its whole window, is a hole) -- elevation.py's convention."""
    gap = np.isnan(z)
    a = np.where(gap, -np.inf, z)
    out = maximum_filter(a, size=win)
    np.copyto(a, np.inf, where=gap)
    out -= minimum_filter(a, size=win)
    del a
    return np.where(gap | ~np.isfinite(out), np.nan, out).astype(np.float32)


def window_px(transform) -> int:
    px_ground = transform.a * math.cos(math.radians(RELIEF_REF_LAT))
    return max(3, int(round(RANGE_WINDOW_M / px_ground)) | 1)


def main(processed_dir: str):
    d = Path(processed_dir)
    t0 = time.time()
    with rasterio.open(d / "elevation.tif") as src:
        elev = src.read(1)
        prof = src.profile
        transform = src.transform
    z, n_spike = despike(elev)
    del elev
    print(f"despiked: {n_spike:,} px (more than {SPIKE_M:.0f} m from their "
          f"{SPIKE_WINDOW}x{SPIKE_WINDOW} median, or in a patch more than "
          f"{BLOB_M:.0f} m from the ~1.1 km median)")
    # Ocean bathymetry to sea level, as elevation.py does, so a coastal road is
    # not credited with the sea floor.
    np.clip(z, 0.0, None, out=z)
    win = window_px(transform)
    rng = range_within(z, win)
    del z
    prof.update(dtype="float32", nodata=float("nan"), compress="deflate", predictor=2)
    with rasterio.open(d / "range3k.tif", "w", **prof) as dst:
        dst.write(rng, 1)
    valid = ~np.isnan(rng)
    print(f"range within {RANGE_WINDOW_M:.0f} m ({win} px): median "
          f"{np.median(rng[valid]):.0f} m, p95 {np.percentile(rng[valid], 95):.0f} m; "
          f"wrote {d / 'range3k.tif'} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1])
