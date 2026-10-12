"""How big is a region's routing graph as a phone download?

Packs what an on-device router would need — topology, travel time inputs, the
scenery vector, names/refs/signs for turn-by-turn, drawable geometry and the
side tables (restrictions, closures, closed roads, state classes) — into plain
little-endian arrays the way a Swift loader would mmap them, then compresses
each part with zlib -9 and xz -9 (both available on iOS via Compression).
Optional: the parking-lot access layer used for destination snapping.

Usage: python package_size.py <processed_dir> <label>
"""
import lzma
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapely

d = Path(sys.argv[1])
label = sys.argv[2]
parts = {}

nodes = pd.read_parquet(d / "graph_nodes.parquet")
idx = pd.Series(np.arange(len(nodes)), index=nodes["node_id"].to_numpy())
lon_i = np.round(nodes["lon"].to_numpy() * 1e6).astype(np.int32)
lat_i = np.round(nodes["lat"].to_numpy() * 1e6).astype(np.int32)
parts["nodes (lat/lon int32)"] = lon_i.tobytes() + lat_i.tobytes()

cols = [c for c in pq.ParquetFile(d / "graph_edges.parquet").schema_arrow.names]
e = pd.read_parquet(d / "graph_edges.parquet")
geoms = shapely.from_wkb(e["geometry"]) if e["geometry"].dtype == object else e["geometry"]
u = idx[e["u"].to_numpy()].to_numpy().astype(np.int32)
v = idx[e["v"].to_numpy()].to_numpy().astype(np.int32)

# Strings: one table, edges carry int32 ids.
str_cols = [c for c in ("name", "ref", "dest_ref", "dest_name") if c in e.columns]
table = pd.unique(pd.concat([e[c].fillna("").astype(str) for c in str_cols]))
code = {s: i for i, s in enumerate(table)}
ids = np.column_stack([e[c].fillna("").astype(str).map(code).to_numpy() for c in str_cols]).astype(np.int32)
parts["string table"] = "\0".join(table).encode()
parts["edge string ids"] = ids.tobytes()

enum = lambda s: pd.factorize(s.fillna("").astype(str))[0].astype(np.uint8)
comp_cols = [c for c in e.columns if c.startswith("c_")]
q = lambda a: np.clip(np.round(np.asarray(a, dtype=float) * 255), 0, 255).astype(np.uint8)
ctrl = [c for c in e.columns if c.startswith("n_")]
edge_attr = [u.tobytes(), v.tobytes(),
             np.asarray(e["length_m"], dtype=np.float32).tobytes(),
             np.asarray(e["minutes"], dtype=np.float32).tobytes(),
             enum(e["highway"]).tobytes(), enum(e["oneway"]).tobytes(), enum(e["junction"]).tobytes(),
             e[ctrl].to_numpy().astype(np.uint8).tobytes(),
             np.column_stack([q(e[c]) for c in comp_cols]).tobytes(),
             np.round(np.asarray(e["score_adj"]) * 100).astype(np.int8).tobytes(),
             q(e["unpaved_frac"] if "unpaved_frac" in e.columns else np.zeros(len(e))).tobytes()]
parts["edge attributes"] = b"".join(edge_attr)

# Geometry: interior points only (the ends are the nodes), delta-coded in
# 1e-6 degrees from the previous point, zigzag + varint.
coords, owner = shapely.get_coordinates(np.asarray(geoms), return_index=True)
counts = np.bincount(owner, minlength=len(e))
first = np.r_[0, np.cumsum(counts)[:-1]]
last = first + counts - 1
interior = np.ones(len(coords), bool)
interior[first] = False
interior[last] = False
ci = np.round(coords * 1e6).astype(np.int64)
delta = np.diff(ci, axis=0, prepend=ci[:1])
delta[first] = 0                      # each edge's run starts from its own first node
z = ((delta << 1) ^ (delta >> 63))[interior].ravel()
out = bytearray()
for val in z.tolist():
    while val >= 0x80:
        out.append((val & 0x7F) | 0x80)
        val >>= 7
    out.append(val)
parts["geometry (interior points, varint deltas)"] = bytes(out)
parts["geometry offsets (uint32 per edge)"] = np.cumsum(counts - 2).astype(np.uint32).tobytes()

for name in ("turn_restrictions", "forbidden_movements", "seasonal_closures", "closed_to_cars",
             "state_road_class", "neighbourhood_streets"):
    p = d / f"{name}.parquet"
    if p.exists():
        t = pd.read_parquet(p)
        num = t.select_dtypes(include=[np.number])
        parts[f"side table: {name} ({len(t):,} rows)"] = num.to_numpy().astype(np.float32).tobytes()

opt = {}
if (d / "access_entries.parquet").exists():
    a = pd.read_parquet(d / "access_entries.parquet", columns=["component", "lon", "lat"])
    opt["access entries"] = (a["component"].to_numpy().astype(np.int32).tobytes()
                             + np.round(a[["lon", "lat"]].to_numpy() * 1e6).astype(np.int32).tobytes())
    aw = pd.read_parquet(d / "access_ways.parquet")
    ag = shapely.from_wkb(aw["geometry"]) if aw["geometry"].dtype == object else aw.geometry.values
    ac = np.round(shapely.get_coordinates(np.asarray(ag)) * 1e6).astype(np.int32)
    opt["access way geometry (raw int32)"] = ac.tobytes()


def report(title, items):
    raw = zl = xz = 0
    print(title)
    for k, b in items.items():
        zb, xb = len(zlib.compress(b, 9)), len(lzma.compress(b, preset=9))
        raw, zl, xz = raw + len(b), zl + zb, xz + xb
        print(f"  {k:48s} raw {len(b) / 1e6:7.1f} MB   zlib {zb / 1e6:6.1f}   xz {xb / 1e6:6.1f}")
    print(f"  {'TOTAL':48s} raw {raw / 1e6:7.1f} MB   zlib {zl / 1e6:6.1f}   xz {xz / 1e6:6.1f}")
    return raw, xz


print(f"[{label}] {len(nodes):,} nodes, {len(e):,} edges, {len(coords):,} coordinates")
r1, x1 = report("routing + turn-by-turn + drawing:", parts)
if opt:
    r2, x2 = report("optional: parking-lot access layer (destination snapping):", opt)
print(f"per graph node: raw {r1 / len(nodes):.0f} B, xz {x1 / len(nodes):.0f} B")
