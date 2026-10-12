"""Terrain derivatives at chunk midpoints from a build's elevation.tif.

Usage: terrain.py <processed_dir> <reg_dir> <lo_m> <hi_m>
Elevation outside [lo, hi] is treated as a hole (the Terrarium corrupt-pixel blobs).
For New England pass lo=-1e9 and the ocean is clipped to 0 as elevation.py does.
Writes <reg_dir>/terrain.parquet: z, relief3k, above3k, below3k, relief6k, above6k, below6k, (chunk order).
"""
import sys, math, time
from pathlib import Path
import numpy as np, pandas as pd, rasterio
from scipy.ndimage import maximum_filter, minimum_filter
d, reg = Path(sys.argv[1]), Path(sys.argv[2]); lo, hi = float(sys.argv[3]), float(sys.argv[4])
t0 = time.time()
with rasterio.open(d / "elevation.tif") as src:
    z = src.read(1).astype(np.float32); T = src.transform
bad = ~np.isnan(z) & ((z < lo) | (z > hi))
print("holes from physical band:", int(bad.sum()), "px", flush=True)
z[bad] = np.nan
# In-band spikes (Terrarium blobs inside the physical band): a pixel more than
# SPIKE_M from its 5x5 median is a hole. A planar slope's median is its centre
# value, so real cliffs at ~57 m pixels stay well under this.
from scipy.ndimage import median_filter
zf = np.where(np.isnan(z), np.nanmedian(z), z)
med = median_filter(zf, size=5); del zf
spike = ~np.isnan(z) & (np.abs(z - med) > 250.0); del med
print("holes from 5x5 median deviation > 250 m:", int(spike.sum()), "px", flush=True)
z[spike] = np.nan; del spike
if lo < -1e8:
    z = np.clip(z, 0, None)
gap = np.isnan(z)
px_ground = T.a * math.cos(math.radians(42.05))
ch = pd.read_parquet(reg / "chunks.parquet", columns=["x3857", "y3857"])
col = np.floor((ch.x3857.values - T.c) / T.a).astype(int)
row = np.floor((ch.y3857.values - T.f) / T.e).astype(int)
ok = (row >= 0) & (row < z.shape[0]) & (col >= 0) & (col < z.shape[1])
rr, cc = np.clip(row, 0, z.shape[0]-1), np.clip(col, 0, z.shape[1]-1)
out = pd.DataFrame({"z": np.where(ok, z[rr, cc], np.nan)})
for name, m in (("3k", 3000.0), ("6k", 6000.0)):
    win = max(3, int(round(m / px_ground)) | 1)
    a = z.copy(); a[gap] = -np.inf
    mx = maximum_filter(a, size=win)
    a[gap] = np.inf
    mn = minimum_filter(a, size=win); del a
    MX, MN = mx[rr, cc], mn[rr, cc]; del mx, mn
    zz = out.z.values
    good = ok & np.isfinite(MX) & np.isfinite(MN) & np.isfinite(zz)
    out[f"relief{name}"] = np.where(good, MX - MN, np.nan)
    out[f"above{name}"] = np.where(good, zz - MN, np.nan)
    out[f"below{name}"] = np.where(good, MX - zz, np.nan)
    print(name, "win px", win, f"{time.time()-t0:.0f}s", flush=True)
out.to_parquet(reg / "terrain.parquet")
print(out.describe().T.round(1).to_string())
