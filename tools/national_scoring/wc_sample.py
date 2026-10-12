"""WorldCover class fractions at chunk midpoints, from wc_grids.py block counts.

Usage: wc_sample.py <grid_dir> <reg_dir>
Writes <reg_dir>/wc.parquet: <class>_100 (one ~100 m block) and <class>_1k (9x11 blocks, ~1 km).
Missing tiles (all-ocean cells WorldCover omits) count as water.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.ndimage import uniform_filter
NAMES = ["tree", "shrub", "grass", "crop", "built", "bare", "snow", "water", "wetland", "mangrove", "moss"]
gd, reg = Path(sys.argv[1]), Path(sys.argv[2])
ch = pd.read_parquet(reg / "chunks.parquet", columns=["lon", "lat"])
bc = np.floor((ch.lon.values + 180) * 1000).astype(np.int64)
br = np.floor((90 - ch.lat.values) * 1000).astype(np.int64)
PAD = 10
tr0, tr1 = (br.min() - PAD) // 3000, (br.max() + PAD) // 3000
tc0, tc1 = (bc.min() - PAD) // 3000, (bc.max() + PAD) // 3000
H, W = (tr1 - tr0 + 1) * 3000, (tc1 - tc0 + 1) * 3000
def name(r, c):
    lat0 = 90 - (r + 1) * 3; lon0 = c * 3 - 180
    return f"{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}{'E' if lon0 >= 0 else 'W'}{abs(lon0):03d}"
mos = np.zeros((len(NAMES), H, W), np.uint8)
for r in range(tr0, tr1 + 1):
    for c in range(tc0, tc1 + 1):
        p = gd / f"{name(r, c)}.npz"
        sl = (slice((r - tr0) * 3000, (r - tr0 + 1) * 3000), slice((c - tc0) * 3000, (c - tc0 + 1) * 3000))
        if p.exists():
            mos[(slice(None),) + sl] = np.load(p)["counts"]
        else:
            print("missing", name(r, c), "-> water"); mos[(NAMES.index("water"),) + sl] = 144
rr, cc = br - tr0 * 3000, bc - tc0 * 3000
out = {}
for k, nm in enumerate(NAMES):
    a = mos[k].astype(np.float32) / 144.0
    out[f"{nm}_100"] = a[rr, cc]
    out[f"{nm}_1k"] = uniform_filter(a, size=(9, 11), mode="nearest")[rr, cc]
    del a
df = pd.DataFrame(out)
df.to_parquet(reg / "wc.parquet")
print(df.describe().T[["mean", "50%"]].round(3).to_string())
