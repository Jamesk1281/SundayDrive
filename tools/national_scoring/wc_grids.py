"""Reduce WorldCover tiles to per-class pixel counts on a 12x12-pixel (~100 m) block grid.

Usage: wc_grids.py <dl_dir> <grid_dir> <tile> [<tile> ...]
Writes <grid_dir>/<tile>.npz with counts uint8 [len(CLASSES), 3000, 3000].
Also writes <grid_dir>/<tile>_m3.npz: the same block grid counted on WorldCover first reduced to
~30 m by the majority class of each 3x3 pixels (ties to the lower class code), counts 0-16 per
block. That is the resolution control for 30 m sources (docs/western-landcover-verdict.md).
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
        for attempt in range(4):
            r = subprocess.run(["curl", "-sS", "-f", "-o", str(tif) + ".part", URL.format(t=t)])
            if r.returncode == 0:
                break
            # Only a 404 on the tile itself means WorldCover omits the cell (all ocean). On
            # 2026-10-18 a land tile (N42W114) failed mid-transfer and was logged as ocean.
            head = subprocess.run(["curl", "-s", "-I", "-o", "/dev/null", "-w", "%{http_code}", URL.format(t=t)],
                                  capture_output=True, text=True).stdout
            if head == "404":
                break
            time.sleep(10 * (attempt + 1))
        if r.returncode:
            if head != "404":
                raise SystemExit(f"{t}: download failed (HTTP {head}), not an absent cell")
            print(t, "absent from WorldCover (404, all ocean)", flush=True); continue
        Path(str(tif) + ".part").rename(tif)
    with rasterio.open(tif) as src:
        assert src.width == 36000 and src.height == 36000
        a = src.read(1)
    b = a.reshape(3000, 12, 3000, 12)
    counts = np.stack([(b == k).sum(axis=(1, 3), dtype=np.uint16).astype(np.uint8) for k in CLASSES])
    np.savez_compressed(out, counts=counts)
    del b
    b3 = a.reshape(12000, 3, 12000, 3)
    best = np.zeros((12000, 12000), np.uint8); mode = np.zeros((12000, 12000), np.uint8)
    for k in CLASSES:
        c = (b3 == k).sum(axis=(1, 3), dtype=np.uint8)
        win = c > best
        best[win] = c[win]; mode[win] = k
        del c, win
    del a, b3, best
    m4 = mode.reshape(3000, 4, 3000, 4)
    np.savez_compressed(gd / f"{t}_m3.npz", counts=np.stack([(m4 == k).sum(axis=(1, 3), dtype=np.uint8) for k in CLASSES]))
    del mode, m4
    tif.unlink()
    print(t, f"{time.time() - t0:.0f}s", flush=True)
