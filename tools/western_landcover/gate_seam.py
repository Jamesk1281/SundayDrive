"""What the rangeland gate costs, nationally: where NLCD's desert classes are, and how much the gate keeps.

Usage: gate_seam.py <nlcd.tif> <rcmap_sagebrush_2025.tif> <out_csv>
Reads both on the shared 30 m grid, decimated 16x (~480 m; GDAL's overviews, nearest-sampled,
so shares are unbiased estimates, not counts). For each 1-degree longitude band of the 48 states:
  land_px            land pixels (NLCD, not water or nodata)
  desert_share       share of land that is NLCD Shrub/Scrub, Barren or Ice/Snow
  kept_by_gate       share of that desert the RCMAP gate keeps (pixel inside RCMAP rangeland)
  rangeland_share    share of land that is RCMAP rangeland
  footprint_share    share of land inside RCMAP's raster extent (it ends near 88-90 W)
The seam is where rangeland_share falls to zero: any NLCD desert east of it gets no credit
under the gate, however real. The band rows say how much desert that is.
"""
import sys
import numpy as np, pandas as pd, rasterio
from rasterio.windows import Window
from pyproj import Transformer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import classmaps as K

F = 16
nl, rc = rasterio.open(sys.argv[1]), rasterio.open(sys.argv[2])
H, Wd = nl.height // F, nl.width // F
a = nl.read(1, out_shape=(H, Wd))
dc = round((rc.transform.c - nl.transform.c) / 30.0); dr = round((rc.transform.f - nl.transform.f) / -30.0)
win = Window(-dc, -dr, nl.width, nl.height)
fill = rc.nodata if rc.nodata is not None else 255
g = rc.read(1, window=win, out_shape=(H, Wd), boundless=True, fill_value=fill)
land = (a != K.NLCD_NODATA) & (a != 11) & (a != 0)
desert = np.isin(a, K.NLCD_DESERT)
rng = g <= K.RCMAP_MAX
# RCMAP's nodata is 101 both for its mask and beyond its raster, so the footprint is the raster's extent
foot = np.zeros_like(rng)
c_east = int((rc.bounds.right - nl.transform.c) / (30.0 * F)); r_south = int((nl.transform.f - rc.bounds.bottom) / (30.0 * F))
c_west = max(0, int((rc.bounds.left - nl.transform.c) / (30.0 * F))); r_north = max(0, int((nl.transform.f - rc.bounds.top) / (30.0 * F)))
foot[r_north:r_south, c_west:c_east] = True
cols = np.arange(Wd)
xs = nl.transform.c + (cols + 0.5) * 30.0 * F
rows = np.arange(H)
ys = nl.transform.f - (rows + 0.5) * 30.0 * F
X, Y = np.meshgrid(xs, ys)
lon, _ = Transformer.from_crs(nl.crs, "EPSG:4326", always_xy=True).transform(X, Y)
band = np.floor(lon).astype(int)
out = []
for b in np.unique(band[land]):
    m = land & (band == b)
    d = desert & m
    out.append(dict(lon_band=int(b), land_px=int(m.sum()), desert_share=d.sum() / m.sum(),
                    kept_by_gate=(d & rng).sum() / max(d.sum(), 1),
                    rangeland_share=(rng & m).sum() / m.sum(), footprint_share=(foot & m).sum() / m.sum()))
T = pd.DataFrame(out)
T.to_csv(sys.argv[3], index=False)
pd.set_option("display.width", 200)
print(T.round(3).to_string(index=False))
tot = desert & land
print(f"\nnational: desert {tot.sum() / land.sum():.3f} of land; the gate keeps {(tot & rng).sum() / tot.sum():.3f} of it")
east = land & (lon > -95)
print(f"east of -95: desert {(tot & east).sum() / east.sum():.3f} of land; kept {(tot & east & rng).sum() / max((tot & east).sum(), 1):.3f}")
