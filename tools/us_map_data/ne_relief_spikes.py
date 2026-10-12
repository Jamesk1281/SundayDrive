"""What Terrarium's in-band corrupt pixels do to the deployed New England scores.

terrarium_survey.py's `local` run over data/raw/terrain lists the tiles whose
residue pixels (corrupt values inside elevation.py's -11,000..9,000 m band)
raise the relief component somewhere. For each such tile this reads the
deployed elevation.tif over the tile plus a margin, finds the residue with the
same detector (`residue_mask`), recomputes relief as elevation.py does (clamp
at 0 m, max - min over the window, checked against relief.tif) with and without
those pixels, and samples both at every scored chunk midpoint inside the tile,
as score.py's sample_relief does. A chunk's score moves by
10 x STRETCH x WEIGHTS["relief"] x its change in c_relief.

Reads data/processed-ne read-only.

Usage: python -I ne_relief_spikes.py <repo_pipeline_dir> <processed_dir>
                                     <terrarium_decode_new-england-cache.csv> <out.json>
"""

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import RELIEF_FULL, STRETCH, WEIGHTS  # noqa: E402
from terrarium_survey import ELEV_MAX_M, ELEV_MIN_M, residue_mask  # noqa: E402

R = 6378137.0
MARGIN = 20        # pixels around the tile, more than half the relief window


def tile_bounds_3857(x, y, z=11):
    n = 2 ** z
    size = 2 * math.pi * R / n
    left = -math.pi * R + x * size
    top = math.pi * R - y * size
    return left, top - size, left + size, top


def main():
    import geopandas as gpd
    import rasterio
    from scipy import ndimage
    proc, decode_csv, out = Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
    flagged = [(int(r["x"]), int(r["y"])) for r in csv.DictReader(open(decode_csv))
               if r.get("relief_component_raised_px") and int(r["relief_component_raised_px"]) > 0]
    chunks = gpd.read_parquet(proc / "scored_chunks.parquet",
                              columns=["geometry", "length_m", "c_relief", "score", "name",
                                       "highway"])
    mids = chunks.geometry.interpolate(0.5, normalized=True).to_crs(3857)
    mx, my = mids.x.values, mids.y.values
    report = []
    with rasterio.open(proc / "relief.tif") as rr, rasterio.open(proc / "elevation.tif") as er:
        res = rr.res[0]
        for x, y in flagged:
            l, b, r_, t = tile_bounds_3857(x, y)
            row0, col0 = rr.index(l + res / 2, t - res / 2)
            win = ((row0 - MARGIN, row0 + 256 + MARGIN), (col0 - MARGIN, col0 + 256 + MARGIN))
            e = er.read(1, window=win, boundless=True, fill_value=np.nan).astype(np.float64)
            dep = rr.read(1, window=win, boundless=True, fill_value=np.nan).astype(np.float64)
            e[(e > ELEV_MAX_M) | (e < ELEV_MIN_M)] = np.nan
            _, resid = residue_mask(e)
            land = np.clip(e, 0.0, None)
            found = None
            for w in (11, 13, 15, 17):          # elevation.py's window, read back
                lo = np.where(np.isnan(land), np.inf, land)
                hi = np.where(np.isnan(land), -np.inf, land)
                rel = ndimage.maximum_filter(hi, w) - ndimage.minimum_filter(lo, w)
                core = (slice(MARGIN, -MARGIN), slice(MARGIN, -MARGIN))
                same = np.isclose(np.where(np.isfinite(rel), rel, np.nan)[core], dep[core],
                                  atol=0.01, equal_nan=True)
                if same.mean() > 0.999:
                    found = w
                    break
            if found is None:
                report.append({"tile": [x, y], "error": "relief.tif not reproduced"})
                continue
            lo = np.where(np.isnan(land) | resid, np.inf, land)
            hi = np.where(np.isnan(land) | resid, -np.inf, land)
            clean = ndimage.maximum_filter(hi, found) - ndimage.minimum_filter(lo, found)
            sel = np.flatnonzero((mx >= l) & (mx < r_) & (my > b) & (my <= t))
            rows = np.floor((t - my[sel]) / res).astype(int) + MARGIN
            cols = np.floor((mx[sel] - l) / res).astype(int) + MARGIN
            old = np.clip(np.nan_to_num(dep[rows, cols]) / RELIEF_FULL, 0, 1)
            new = np.clip(np.nan_to_num(clean[rows, cols], posinf=0, neginf=0) / RELIEF_FULL, 0, 1)
            moved = old - new > 1e-6
            gain = 10 * STRETCH * WEIGHTS["relief"] * (old - new)
            km = chunks["length_m"].values[sel] / 1000.0
            report.append({
                "tile": [x, y], "window_px": found, "residue_px": int(resid[MARGIN:-MARGIN,
                                                                           MARGIN:-MARGIN].sum()),
                "chunks_in_tile": int(len(sel)), "chunks_inflated": int(moved.sum()),
                "km_inflated": round(float(km[moved].sum()), 2),
                "score_gain_max": round(float(gain.max()) if len(sel) else 0.0, 2),
                "score_gain_mean_inflated": round(float(gain[moved].mean()) if moved.any() else 0.0, 2),
                "roads": sorted({n for n in chunks["name"].values[sel][moved] if n})[:10],
            })
            print(report[-1], flush=True)
    tot = sum(r.get("km_inflated", 0) for r in report)
    print(f"{len(flagged)} flagged tiles; {tot:.1f} km of scored road inflated")
    out.write_text(json.dumps({"tiles": report, "km_inflated_total": round(tot, 2)}, indent=1))


if __name__ == "__main__":
    main()
