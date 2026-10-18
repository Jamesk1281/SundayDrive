"""NLCD, LANDFIRE and RCMAP fractions in a ~1 km ground box at every chunk midpoint.

Usage: sample30.py <reg_dir> <nlcd.tif> <landfire_evt.tif> <LF2025_EVT.csv> <rcmap_dir>
Writes <reg_dir>/lc30.parquet, in chunk order:
  nlcd_desert, nlcd_grass, nlcd_pasture, nlcd_crop        share of the box in each NLCD group
  nlcd_desert_r, nlcd_grass_r                             the same, counting only RCMAP rangeland pixels
  lf_desert, lf_grass, lf_desert_r, lf_grass_r            LANDFIRE EVT groups, ungated and gated
  rc_sage, rc_shrub, rc_bare, rc_herb                     RCMAP mean cover over the box, 0-1
  rc_range                                                share of the box that is RCMAP rangeland
The groups are classmaps.py's, fixed before any of this ran. The box is 33 x 33 pixels
(990 m) on the products' shared 30 m Albers grid, the size of score's ~1 km desert box.
Pixels outside a product's extent count as neither group (as landcover.py counts ocean).
The three products share one grid, which is checked rather than assumed: a gate pixel is
read from exactly the same ground cell as the pixel it gates.
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd, rasterio
from rasterio.windows import Window
from pyproj import Transformer
sys.path.insert(0, str(Path(__file__).resolve().parent))
import classmaps as K

HALF = 16                      # 33 x 33 px
STRIP = 1500                   # point rows per read
reg, nlcd_p, lf_p, lf_csv, rc_dir = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], Path(sys.argv[5])
RC = {k: rc_dir / f"rcmap_{n}_2025.tif" for k, n in
      (("sage", "sagebrush"), ("shrub", "shrub"), ("bare", "bare_ground"), ("herb", "herbaceous"))}
t0 = time.time()
ch = pd.read_parquet(reg / "chunks.parquet", columns=["lon", "lat"])
n = len(ch)

lf_tab = pd.read_csv(lf_csv)
lf_group = K.landfire_groups(lf_tab)
lf_desert_vals = np.array(sorted(v for v, g in lf_group.items() if g == "desert"))
lf_grass_vals = np.array(sorted(v for v, g in lf_group.items() if g == "grass"))
print(f"LANDFIRE: {len(lf_desert_vals)} desert classes, {len(lf_grass_vals)} grass classes", flush=True)

srcs = {"nlcd": rasterio.open(nlcd_p), "lf": rasterio.open(lf_p), **{k: rasterio.open(p) for k, p in RC.items()}}
ref = srcs["nlcd"]
tr = Transformer.from_crs("EPSG:4326", ref.crs, always_xy=True)
x, y = tr.transform(ch.lon.to_numpy(), ch.lat.to_numpy())
# every product on one grid: same pixel size, origins a whole number of pixels apart, same CRS
off = {}
for k, s in srcs.items():
    a, e = s.transform.a, s.transform.e
    assert abs(a - 30) < 1e-6 and abs(e + 30) < 1e-6, (k, s.transform)
    dc, dr = (s.transform.c - ref.transform.c) / 30.0, (s.transform.f - ref.transform.f) / -30.0
    # NLCD is in a WGS84-datum Albers, LANDFIRE and RCMAP in NAD83 Conus Albers. LANDFIRE's origin is
    # a whole number of pixels from NLCD's; RCMAP's is 1.17 m east and 0.95 m south of a pixel edge
    # (0.04 px), the datum difference written into its origin. Nearest-pixel registration is then off
    # by at most ~1.5 m, which a 30 m pixel cannot see; anything over 0.1 px stops the run.
    assert abs(dc - round(dc)) < 0.1 and abs(dr - round(dr)) < 0.1, (k, dc, dr)
    if k != "nlcd":
        xx, yy = Transformer.from_crs(ref.crs, s.crs, always_xy=True).transform(x[:1000], y[:1000])
        assert np.abs(np.asarray(xx) - x[:1000]).max() < 3.0 and np.abs(np.asarray(yy) - y[:1000]).max() < 3.0, k
    off[k] = (int(round(dr)), int(round(dc)))   # this product's (row, col) of the reference's (0, 0)
col = np.floor((x - ref.transform.c) / 30.0).astype(np.int64)
row = np.floor((y - ref.transform.f) / -30.0).astype(np.int64)
print(f"{n:,} midpoints, grids checked, {time.time() - t0:.0f}s", flush=True)


def read(k, r0, r1, c0, c1):
    s = srcs[k]; dr, dc = off[k]
    w = Window(c0 - dc, r0 - dr, c1 - c0, r1 - r0)
    # outside a product's extent: its nodata, or for RCMAP a value above 100 (never cover, never rangeland)
    # RCMAP's nodata is its non-rangeland mask, 101, so outside its extent reads as masked too
    fill = s.nodata if s.nodata is not None else (255 if k in RC else 0)
    return s.read(1, window=w, boundless=True, fill_value=fill)


def boxsum(v, rr, cc):
    """Sum of v over the (2*HALF+1)^2 box centred on each (rr, cc), via a summed-area table."""
    S = np.zeros((v.shape[0] + 1, v.shape[1] + 1), np.float64 if v.dtype.kind == "f" else np.int64)
    np.cumsum(np.cumsum(v, axis=0, dtype=S.dtype), axis=1, out=S[1:, 1:])
    r0, r1, c0, c1 = rr - HALF, rr + HALF + 1, cc - HALF, cc + HALF + 1
    return S[r1, c1] - S[r0, c1] - S[r1, c0] + S[r0, c0]


COLS = ["nlcd_desert", "nlcd_grass", "nlcd_pasture", "nlcd_crop", "nlcd_desert_r", "nlcd_grass_r",
        "lf_desert", "lf_grass", "lf_desert_r", "lf_grass_r", "rc_sage", "rc_shrub", "rc_bare", "rc_herb", "rc_range"]
# Coverage, so a product that is nodata under the roads stops the run instead of reading as
# "no desert". LF2025's EVT, as published on 2026-06-05, carries values for the far West only;
# its eastern four fifths are nodata, which read here as zero desert until this check existed.
VALID = {"nlcd": lambda a: a != K.NLCD_NODATA, "lf": lambda a: ~np.isin(a, K.LF_NODATA)}
valid_centre = {k: np.zeros(n, bool) for k in VALID}
out = {c: np.zeros(n, np.float32) for c in COLS}
NPX = float((2 * HALF + 1) ** 2)
order = np.argsort(row, kind="mergesort")
i = 0
while i < n:
    # a strip of points whose rows span at most STRIP pixels
    j = np.searchsorted(row[order], row[order[i]] + STRIP, side="left")
    idx = order[i:j]; i = j
    r0, r1 = row[idx].min() - HALF, row[idx].max() + HALF + 1
    c0, c1 = col[idx].min() - HALF, col[idx].max() + HALF + 1
    rr, cc = row[idx] - r0, col[idx] - c0
    sage = read("sage", r0, r1, c0, c1)
    rng = sage <= K.RCMAP_MAX                       # RCMAP rangeland: a cover value, not 101 or nodata
    out["rc_range"][idx] = boxsum(rng.astype(np.uint8), rr, cc) / NPX
    out["rc_sage"][idx] = boxsum(np.where(rng, sage, 0).astype(np.uint16), rr, cc) / NPX / 100.0
    del sage
    for k in ("shrub", "bare", "herb"):
        a = read(k, r0, r1, c0, c1)
        ok = a <= K.RCMAP_MAX
        out[f"rc_{k}"][idx] = boxsum(np.where(ok, a, 0).astype(np.uint16), rr, cc) / NPX / 100.0
        del a, ok
    a = read("nlcd", r0, r1, c0, c1)
    valid_centre["nlcd"][idx] = VALID["nlcd"](a[rr, cc])
    for name, vals in (("desert", K.NLCD_DESERT), ("grass", K.NLCD_GRASS), ("pasture", K.NLCD_PASTURE), ("crop", K.NLCD_CROP)):
        m = np.isin(a, vals)
        out[f"nlcd_{name}"][idx] = boxsum(m.astype(np.uint8), rr, cc) / NPX
        if name in ("desert", "grass"):
            out[f"nlcd_{name}_r"][idx] = boxsum((m & rng).astype(np.uint8), rr, cc) / NPX
    del a
    a = read("lf", r0, r1, c0, c1)
    valid_centre["lf"][idx] = VALID["lf"](a[rr, cc])
    for name, vals in (("desert", lf_desert_vals), ("grass", lf_grass_vals)):
        m = np.isin(a, vals)
        out[f"lf_{name}"][idx] = boxsum(m.astype(np.uint8), rr, cc) / NPX
        out[f"lf_{name}_r"][idx] = boxsum((m & rng).astype(np.uint8), rr, cc) / NPX
    del a, rng
    print(f"  {i:,} / {n:,}  {time.time() - t0:.0f}s", flush=True)

for k, v in valid_centre.items():
    print(f"{k}: {100 * v.mean():.2f}% of midpoints on a valid pixel", flush=True)
    if v.mean() < 0.99:
        raise SystemExit(f"{k} is nodata under {100 * (1 - v.mean()):.1f}% of midpoints: wrong file or partial coverage")
df = pd.DataFrame(out)
df.to_parquet(reg / "lc30.parquet")
km = pd.read_parquet(reg / "chunks.parquet", columns=["length_m"]).length_m.to_numpy() / 1000
print(pd.DataFrame({"mean_kmw": (df.mul(km, axis=0).sum() / km.sum()),
                    "km_share_ge_0.5": df.ge(0.5).mul(km, axis=0).sum() / km.sum()}).round(3).to_string())
print(f"done {time.time() - t0:.0f}s")
