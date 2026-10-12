"""The ESA WorldCover v200 (2021) tiles covering the contiguous 48 + DC, by HEAD.

WorldCover is a grid of 3-degree cells named for their SOUTH-WEST corner
(landcover.py: the floor, never the ceil). A cell that is all ocean is left out
of the grid, so a 404 there is expected; a 404 on a cell whose interior holds
land would be a real hole. Each cell is therefore classed by how much of the
Census outline (1:500k) falls inside it.

Usage: python -I worldcover_cells.py <states.zip> <out.csv>
"""

import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import head  # noqa: E402
from scope import OUT_FIPS  # noqa: E402

TILE_URL = ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
            "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif")


def name(lat0, lon0):
    return (f"{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}"
            f"{'E' if lon0 >= 0 else 'W'}{abs(lon0):03d}")


if __name__ == "__main__":
    import geopandas as gpd
    import shapely
    st = gpd.read_file(f"zip://{sys.argv[1]}")
    st = st[~st["STATEFP"].isin(OUT_FIPS)]
    cells = {}
    for _, r in st.iterrows():
        for p in getattr(r.geometry, "geoms", [r.geometry]):
            w, s, e, n = p.bounds
            for lat0 in range(int(math.floor(s / 3)) * 3, int(math.floor(n / 3)) * 3 + 1, 3):
                for lon0 in range(int(math.floor(w / 3)) * 3, int(math.floor(e / 3)) * 3 + 1, 3):
                    box = shapely.box(lon0, lat0, lon0 + 3, lat0 + 3)
                    if p.intersects(box):
                        c = cells.setdefault((lat0, lon0), {"states": set(), "land_deg2": 0.0})
                        c["states"].add(r["STUSPS"])
                        c["land_deg2"] += p.intersection(box).area
    rows = []
    for (lat0, lon0), c in sorted(cells.items()):
        tile = name(lat0, lon0)
        status, size, _ = head(TILE_URL.format(tile=tile))
        rows.append({"tile": tile, "states": ";".join(sorted(c["states"])),
                     "land_deg2": round(c["land_deg2"], 4), "status": status,
                     "bytes": size or ""})
        print(tile, status, size, flush=True)
    with open(sys.argv[2], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    ok = [r for r in rows if r["status"] == 200]
    print(f"{len(rows)} cells touch the outlines: {len(ok)} exist, "
          f"{sum(int(r['bytes']) for r in ok) / 1e9:.2f} GB; "
          f"{len(rows) - len(ok)} absent")
