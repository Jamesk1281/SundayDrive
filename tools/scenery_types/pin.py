"""Pin roads.py's icons and controls to OSM way ids, from region slices only.

Usage: pin.py <out_dir>
Reads each region's data/national/build/<r>/part_edges.parquet (owned edges only; never
the national graph_edges or the pack) and writes:
  pins.csv          road, kind, region, way_id
  pins_summary.csv  road, kind, ways, edges, km, the pinned edges' extent
It reads no score or component column, so the pins are fixed before anything is scored.
"""
import os, re, sys
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.parquet as pq, shapely
sys.path.insert(0, str(Path(__file__).resolve().parent))
from roads import ROADS

MAIN = Path(os.environ.get("SUNDAYDRIVE_MAIN", Path(__file__).resolve().parents[2]))
BUILD = MAIN / "data" / "national" / "build"
COLS = ["u", "v", "way_id", "owner", "ref", "name", "highway", "length_m", "geometry"]


def region_edges(r, _cache={}):
    if r not in _cache:
        t = pq.read_table(BUILD / r / "part_edges.parquet", columns=COLS).to_pandas()
        t = t[t.owner == r].reset_index(drop=True)
        g = shapely.from_wkb(t.pop("geometry").to_numpy())
        mid = shapely.line_interpolate_point(g, 0.5, normalized=True)
        t["mlon"], t["mlat"] = shapely.get_x(mid), shapely.get_y(mid)
        _cache.clear(); _cache[r] = t   # one region in memory at a time
    return _cache[r]


def inside(df, box):
    return (df.mlon >= box[0]) & (df.mlon <= box[2]) & (df.mlat >= box[1]) & (df.mlat <= box[3])


def select(df, road):
    """Edges of this road inside its stretch: the pin is their way ids plus the bbox."""
    toks = df.ref.fillna("").str.split(";").map(lambda v: {t.strip() for t in v})
    ok = ~df.highway.fillna("").str.endswith("_link") & inside(df, road["bbox"])
    by_ref = pd.Series(False, index=df.index)
    for ref in road.get("refs", []):
        hit = toks.map(lambda s: ref in s)
        if ref in road.get("per_ref", {}):
            hit &= inside(df, road["per_ref"][ref])
        by_ref |= hit
    if "name" in road:
        by_name = df.name.fillna("").str.fullmatch(road["name"])
        m = (by_ref & by_name) if road.get("both") else (by_ref | by_name)
    else:
        m = by_ref
    return df[ok & m]


def edges_for(road, pins_df):
    """Used by every later script: the pinned edges of one road, from its regions' slices."""
    out = []
    ways = pins_df[pins_df.road == road["id"]]
    for r in road["regions"]:
        df = region_edges(r)
        w = set(ways[ways.region == r].way_id)
        e = df[df.way_id.isin(w) & inside(df, road["bbox"]) & ~df.highway.fillna("").str.endswith("_link")]
        out.append(e.assign(region=r))
    return pd.concat(out)


if __name__ == "__main__":
    OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
    order = sorted({r for road in ROADS for r in road["regions"]})
    pins, summ = [], {}
    for r in order:                      # region-major, so each slice is read once
        df = region_edges(r)
        for road in ROADS:
            if r not in road["regions"]:
                continue
            e = select(df, road)
            pins += [dict(road=road["id"], kind=road["kind"], region=r, way_id=int(w)) for w in sorted(set(e.way_id))]
            s = summ.setdefault(road["id"], dict(road=road["id"], kind=road["kind"], label=road["label"],
                                                 ways=0, edges=0, km=0.0, lon0=180, lat0=90, lon1=-180, lat1=-90))
            s["ways"] += e.way_id.nunique(); s["edges"] += len(e); s["km"] += e.length_m.sum() / 1000
            s.setdefault("_uv", []).append(e[["u", "v"]])
            if len(e):
                s["lon0"] = min(s["lon0"], e.mlon.min()); s["lat0"] = min(s["lat0"], e.mlat.min())
                s["lon1"] = max(s["lon1"], e.mlon.max()); s["lat1"] = max(s["lat1"], e.mlat.max())
        print(r, "done", flush=True)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    for s in summ.values():   # pieces: connected runs of pinned edges (a gap in the pin shows as >1)
        uv = pd.concat(s.pop("_uv")); ids, inv = np.unique(uv.to_numpy().ravel(), return_inverse=True)
        a = coo_matrix((np.ones(len(uv)), (inv[0::2], inv[1::2])), shape=(len(ids), len(ids)))
        s["pieces"] = connected_components(a, directed=False)[0] if len(ids) else 0
    P = pd.DataFrame(pins); P.to_csv(OUT / "pins.csv", index=False)
    S = pd.DataFrame([summ[r["id"]] for r in ROADS]).round({"km": 1, "lon0": 3, "lat0": 3, "lon1": 3, "lat1": 3})
    S.to_csv(OUT / "pins_summary.csv", index=False)
    pd.set_option("display.width", 220)
    print(S.drop(columns="label").to_string())
