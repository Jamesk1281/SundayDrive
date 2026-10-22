"""A true viewshed for the icon and control pieces, to check V's prominence proxy against it.

Usage: viewshed.py <work_dir>
For each piece, 72 rays (every 5 degrees) are walked one pixel at a time out to the same
half-side the proxy's prom10k uses, from an eye 1.5 m above the despiked DEM. A cell is
visible when its elevation angle is at least the steepest angle met before it on that
ray. vis10k is the highest visible cell above the road (m), the viewshed version of
prom10k. Earth curvature is ignored (about 8 m at 10 km). Times the run, which prices a
national viewshed. Writes <work_dir>/icons_viewshed.parquet (piece order).
"""
import math, sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import feat_lib as FL
from roads import ROADS

WORK = Path(sys.argv[1])
P = pd.read_parquet(WORK / "icons_pieces.parquet", columns=["road", "lon", "lat"])
EYE, N_RAY, KM = 1.5, 72, 10
t0 = time.time(); out = np.full(len(P), np.nan); cells = 0
az = np.radians(np.arange(N_RAY) * 360 / N_RAY)
for road in ROADS:
    m = np.flatnonzero((P.road == road["id"]).to_numpy())
    Q = P.iloc[m]
    z, (left, top, px), _ = FL.dem_mosaic((Q.lon.min(), Q.lat.min(), Q.lon.max(), Q.lat.max()))
    px_ground_ref = px * math.cos(math.radians(FL.RELIEF_REF_LAT))
    n_step = int(round(KM * 1000 / px_ground_ref))           # the proxy's half-side, in pixels
    mx, my = FL.merc(Q.lon.to_numpy(), Q.lat.to_numpy())
    c0 = (mx - left) / px; r0 = (top - my) / px
    steps = np.arange(1, n_step + 1)
    for s in range(0, len(m), 400):
        cc, rr = c0[s:s + 400], r0[s:s + 400]
        lat = Q.lat.to_numpy()[s:s + 400]
        # ray samples: (point, ray, step), nearest pixel
        C = np.rint(cc[:, None, None] + np.cos(az)[None, :, None] * steps[None, None, :]).astype(int)
        R = np.rint(rr[:, None, None] - np.sin(az)[None, :, None] * steps[None, None, :]).astype(int)
        ok = (R >= 0) & (R < z.shape[0]) & (C >= 0) & (C < z.shape[1])
        zz = np.where(ok, z[np.clip(R, 0, z.shape[0] - 1), np.clip(C, 0, z.shape[1] - 1)], np.nan)
        z0 = z[np.clip(np.rint(rr).astype(int), 0, z.shape[0] - 1), np.clip(np.rint(cc).astype(int), 0, z.shape[1] - 1)]
        dist = steps[None, None, :] * (px * np.cos(np.radians(lat)))[:, None, None]
        tan = (zz - (z0 + EYE)[:, None, None]) / dist
        tan = np.where(np.isnan(tan), -np.inf, tan)
        prev = np.maximum.accumulate(np.concatenate([np.full(tan.shape[:2] + (1,), -np.inf), tan[:, :, :-1]], axis=2), axis=2)
        vis = tan >= prev
        above = np.where(vis & ~np.isnan(zz), zz - z0[:, None, None], -np.inf)
        out[m[s:s + 400]] = np.maximum(above.max(axis=(1, 2)), 0.0)
        cells += zz.size
    print(road["id"], f"{time.time() - t0:.0f}s", flush=True)
pd.DataFrame({"vis10k": out}).to_parquet(WORK / "icons_viewshed.parquet")
dt = time.time() - t0
print(f"{len(P)} pieces, {cells:.3g} ray cells, {dt:.0f}s: {dt / len(P) * 1000:.1f} ms a piece")
