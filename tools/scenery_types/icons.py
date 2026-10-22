"""Features for the pinned icon and control roads: one row per sample piece.

Usage: icons.py <work_dir>
Each pinned edge is cut into n = ceil(length / 400 m) equal pieces (score.py's chunk
length), sampled at each piece's middle. Writes <work_dir>/icons_pieces.parquet: the
edge's shipped components broadcast to its pieces, plus every cands.py feature.
Region slices only (data/national/build/<r>/part_edges.parquet).
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.parquet as pq, shapely
sys.path.insert(0, str(Path(__file__).resolve().parent))
from roads import ROADS
from pin import BUILD, inside
from cands import BASE
import feat_lib as FL

WORK = Path(sys.argv[1]); WORK.mkdir(parents=True, exist_ok=True)
PINS = pd.read_csv(Path(__file__).resolve().parent / "results" / "pins.csv")
COLS = ["way_id", "owner", "ref", "name", "highway", "length_m", "geometry", "score_adj", "score"] + BASE
t0 = time.time()

edges = []
for r in sorted({r for road in ROADS for r in road["regions"]}):
    t = pq.read_table(BUILD / r / "part_edges.parquet", columns=COLS).to_pandas()
    t = t[(t.owner == r) & t.way_id.isin(set(PINS[PINS.region == r].way_id))].reset_index(drop=True)
    g = shapely.from_wkb(t.pop("geometry").to_numpy())
    mid = shapely.line_interpolate_point(g, 0.5, normalized=True)
    t["mlon"], t["mlat"] = shapely.get_x(mid), shapely.get_y(mid)
    t["geom"] = g
    for road in ROADS:
        if r not in road["regions"]:
            continue
        w = set(PINS[(PINS.road == road["id"]) & (PINS.region == r)].way_id)
        e = t[t.way_id.isin(w) & inside(t, road["bbox"]) & ~t.highway.fillna("").str.endswith("_link")]
        edges.append(e.assign(road=road["id"], kind=road["kind"], region=r))
E = pd.concat(edges, ignore_index=True)
E["edge"] = np.arange(len(E))
print("edges", len(E), f"{time.time() - t0:.0f}s", flush=True)

n = np.maximum(1, np.ceil(E.length_m.to_numpy() / 400.0)).astype(int)
row = np.repeat(np.arange(len(E)), n)
k = np.arange(len(row)) - np.repeat(np.cumsum(n) - n, n)
frac = (k + 0.5) / np.repeat(n, n)
pts = shapely.line_interpolate_point(E.geom.to_numpy()[row], frac, normalized=True)
P = E.drop(columns=["geom"]).iloc[row].reset_index(drop=True)
P["piece"] = (E.length_m.to_numpy() / n)[row]
P["lon"], P["lat"] = shapely.get_x(pts), shapely.get_y(pts)
print("pieces", len(P), flush=True)

parts = []
for road in ROADS:
    m = (P.road == road["id"]).to_numpy()
    Q = P[m]
    bbox = (Q.lon.min(), Q.lat.min(), Q.lon.max(), Q.lat.max())
    dem, info = FL.dem_features(Q.lon.to_numpy(), Q.lat.to_numpy(), bbox)
    wc, absent = FL.wc_features(Q.lon.to_numpy(), Q.lat.to_numpy())
    d = np.full(len(Q), np.inf)
    for r in road["regions"]:
        lines = FL.coastline_lines(r, (bbox[0] - 0.05, bbox[1] - 0.05, bbox[2] + 0.05, bbox[3] + 0.05))
        d = np.minimum(d, FL.coast_distance(Q.lon.to_numpy(), Q.lat.to_numpy(), lines))
    out = pd.concat([Q.reset_index(drop=True), dem, wc], axis=1)
    out["d_coast"] = d
    parts.append(out)
    print(road["id"], len(Q), info, "wc absent:", absent, "coast pieces <=350 m:", int((d <= 350).sum()),
          f"{time.time() - t0:.0f}s", flush=True)
pd.concat(parts, ignore_index=True).to_parquet(WORK / "icons_pieces.parquet")
print("done", f"{time.time() - t0:.0f}s")
