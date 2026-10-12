"""Reduce WorldCover tiles to per-class pixel counts on a 12x12-pixel (~100 m) block grid.

Usage: wc_grids.py <dl_dir> <grid_dir> <tile> [<tile> ...]
Writes <grid_dir>/<tile>.npz with counts uint8 [len(CLASSES), 3000, 3000].
"""
import sys, subprocess, time
from pathlib import Path
import numpy as np, rasterio
CLASSES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]
URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
dl, gd = Path(sys.argv[1]), Path(sys.argv[2])
for t in sys.argv[3:]:
    out = gd / f"{t}.npz"
    if out.exists():
        continue
    tif = dl / f"{t}.tif"
    t0 = time.time()
    if not tif.exists():
        r = subprocess.run(["curl", "-sS", "-f", "-o", str(tif) + ".part", URL.format(t=t)])
        if r.returncode:
            print(t, "missing (ocean?)", flush=True); continue
        Path(str(tif) + ".part").rename(tif)
    with rasterio.open(tif) as src:
        assert src.width == 36000 and src.height == 36000
        a = src.read(1)
    b = a.reshape(3000, 12, 3000, 12)
    counts = np.stack([(b == k).sum(axis=(1, 3), dtype=np.uint16).astype(np.uint8) for k in CLASSES])
    np.savez_compressed(out, counts=counts)
    del a, b
    tif.unlink()
    print(t, f"{time.time() - t0:.0f}s", flush=True)
