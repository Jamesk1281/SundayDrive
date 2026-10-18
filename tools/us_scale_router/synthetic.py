"""A synthetic US-sized pack: New England tiled across the map.

    python synthetic.py <new_england_pack> <out_pack> [--cols 6 --rows 4]

What the router at US scale is measured on before data/processed-us exists
(docs/router-at-us-scale.md, "Measured at US scale"). The feasibility review did
the same with linked copies of the New England graph
(docs/usa-extension-feasibility.md §2). Each copy is the real graph, weights,
names, geometry and access layer, shifted in longitude and latitude so the
copies tile a box the size of the contiguous US. 6 by 4 copies are 19.07M
nodes, against the 19.1M the US was counted at (docs/us-map-data-findings.md).

Neighbouring copies are joined by straight two-way links between junctions
near their facing edges, so the graph is one graph. The links are made up, and
so is everything about routes that cross them; what the pack is for is size
(memory, load time) and the cost of a corridor, which depends on the road
density inside it. New England's density is about twice the US mean, so
corridor costs measured here err high.

Closures are New England's and apply to the first copy only.
"""

import argparse
import json
import pickle
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from compact import SCALE, Lines  # noqa: E402
from router import Router, haversine_km  # noqa: E402

ID_STEP = 10 ** 11          # past the largest OSM node id
LINKS = 300                 # links between two neighbouring copies
LINK_KMH = 60.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ne_pack")
    p.add_argument("out_pack")
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("--rows", type=int, default=4)
    args = p.parse_args()
    src, out = Path(args.ne_pack), Path(args.out_pack)
    out.mkdir(parents=True, exist_ok=True)
    a = {f.stem: np.load(f, mmap_mode="r") for f in src.glob("*.npy")}
    obj = pickle.load(open(src / "objects.pickle", "rb"))
    # Columns west to east and rows north to south, New England shifted by
    # whole steps so the tiles span about 108-67 W and 24-50 N.
    shifts = [(-7.0 * (args.cols - 1 - c), 3.0 - 6.5 * r)
              for r in range(args.rows) for c in range(args.cols)]
    K = len(shifts)
    nr, n, m = obj["n_real"], obj["n"], obj["m"]
    c0, S = n - nr, len(a["tail"])

    def rmap(idx, k):
        """A copy's routing index: real nodes of all copies first, then the
        split junctions' copies."""
        idx = np.asarray(idx, np.int64)
        return np.where(idx < nr, k * nr + idx, K * nr + k * c0 + (idx - nr))

    def tile(name, f=lambda v, k: v):
        return np.concatenate([f(np.asarray(a[name]), k) for k in range(K)])

    lat0, lon0 = np.asarray(a["node_lat"]), np.asarray(a["node_lon"])
    links = _links(lat0, lon0, shifts, args.cols, args.rows, nr)
    L = len(links)
    print(f"{K} copies, {K * nr:,} nodes, {L:,} links", flush=True)

    table = [bytes(a["text.highway.blob"][a["text.highway.offsets"][i]:
                                          a["text.highway.offsets"][i + 1]]).decode()
             for i in range(len(a["text.highway.offsets"]) - 1)]
    primary = table.index("primary")

    # Per node, real nodes then copies, in the layout `rmap` defines.
    arrays = {}
    arrays["node_id"] = tile("node_id", lambda v, k: v + k * ID_STEP)
    arrays["node_lat"] = tile("node_lat", lambda v, k: v + shifts[k][1])
    arrays["node_lon"] = tile("node_lon", lambda v, k: v + shifts[k][0])
    real0 = np.asarray(a["real_node"], np.int64)

    def per_routing(name):
        v = np.asarray(a[name])
        return np.concatenate([v[:nr]] * K + [v[nr:]] * K)

    arrays["real_node"] = np.concatenate(
        [np.arange(K * nr)] + [k * nr + real0[nr:] for k in range(K)]).astype(np.int32)
    arrays["exits_at_node"] = per_routing("exits_at_node")
    arrays["private_inside"] = per_routing("private_inside")

    # Per edge, then the links.
    u = np.array([e[0] for e in links], np.int64)
    v = np.array([e[1] for e in links], np.int64)
    lat, lon = arrays["node_lat"], arrays["node_lon"]
    link_km = haversine_km(lat[u], lon[u], lat[v], lon[v])
    for name, extra in (("km", link_km), ("length_m", link_km * 1000.0),
                        ("unpaved_frac", np.zeros(L)), ("score_adj", np.zeros(L)),
                        ("base_score", np.zeros(L)), ("_score", np.zeros(L)),
                        ("free_minutes", link_km / LINK_KMH * 60.0),
                        ("_roundabout", np.zeros(L, bool)),
                        ("_snap_closed", np.zeros(L, bool))):
        arrays[name] = np.concatenate([tile(name), extra])
    arrays["pref_matrix"] = np.concatenate([tile("pref_matrix"), np.zeros((L, 6))])
    arrays["_breakdown"] = np.concatenate([tile("_breakdown"), np.zeros((L, 6))])
    arrays["edge_u_idx"] = np.concatenate([tile("edge_u_idx", lambda x, k: x + k * nr), u])
    arrays["edge_v_idx"] = np.concatenate([tile("edge_v_idx", lambda x, k: x + k * nr), v])
    for col in ("name", "ref", "highway", "junction", "dest_ref", "dest_name"):
        fill = primary if col == "highway" else -1
        arrays[f"text.{col}.codes"] = np.concatenate(
            [tile(f"text.{col}.codes"), np.full(L, fill, np.int32)])
        arrays[f"text.{col}.blob"] = a[f"text.{col}.blob"]
        arrays[f"text.{col}.offsets"] = a[f"text.{col}.offsets"]
    for part in ("codes", "blob", "offsets"):
        arrays[f"exit_ref.{part}"] = (tile("exit_ref.codes") if part == "codes"
                                      else a[f"exit_ref.{part}"])

    # Geometry and the access layer, shifted.
    def shifted_lines(prefix):
        xy, start = np.asarray(a[f"{prefix}.xy"]), np.asarray(a[f"{prefix}.start"])
        parts = [xy + np.array([round(dx * SCALE), round(dy * SCALE)], np.int32)
                 for dx, dy in shifts]
        starts = [start[:-1] + k * len(xy) for k in range(K)]
        return parts, starts, K * len(xy)

    parts, starts, total = shifted_lines("lines")
    ends = np.column_stack([lon[u], lat[u], lon[v], lat[v]]).reshape(-1, 2)
    parts.append(np.round(ends * SCALE).astype(np.int32))
    starts.append(total + 2 * np.arange(L))
    arrays["lines.xy"] = np.concatenate(parts)
    arrays["lines.start"] = np.append(np.concatenate(starts), len(arrays["lines.xy"]))
    del parts
    access = obj["_has_access"]
    if access:
        parts, starts, total = shifted_lines("access")
        arrays["access.xy"] = np.concatenate(parts)
        arrays["access.start"] = np.append(np.concatenate(starts), total)
        top = int(np.max(a["access.component"])) + 1
        arrays["access.component"] = tile("access.component", lambda x, k: x + k * top)
        arrays["access.entry_comp"] = tile("access.entry_comp", lambda x, k: x + k * top)
        arrays["access.entry_lat"] = tile("access.entry_lat", lambda x, k: x + shifts[k][1])
        arrays["access.entry_lon"] = tile("access.entry_lon", lambda x, k: x + shifts[k][0])
        del parts

    # Slots, then the links both ways.
    tail = np.concatenate([rmap(a["tail"], k) for k in range(K)] + [u, v])
    head = np.concatenate([rmap(a["head"], k) for k in range(K)] + [v, u])
    eidx = np.concatenate([np.asarray(a["eidx"], np.int64) + k * m for k in range(K)]
                          + [K * m + np.arange(L)] * 2)
    flip = np.concatenate([tile("flip"), np.zeros(L, bool), np.ones(L, bool)])
    minutes = link_km / LINK_KMH * 60.0
    d_minutes = np.concatenate([tile("d_minutes"), minutes, minutes])

    r = Router.__new__(Router)
    r.n, r.n_real, r.m = K * n, K * nr, K * m + L
    r.tail, r.head, r.eidx, r.flip, r.d_minutes = tail, head, eidx, flip, d_minutes
    r.real_node = arrays["real_node"].astype(np.int64)
    r.node_lat, r.node_lon = arrays["node_lat"], arrays["node_lon"]
    r.lines = Lines(arrays["lines.xy"], arrays["lines.start"])
    r.edge_u_idx = arrays["edge_u_idx"]
    r.edge_v_idx = arrays["edge_v_idx"]
    r._private_slots = np.concatenate([np.asarray(a["_private_slots"]) + k * S
                                       for k in range(K)])
    r._private_cost = tile("_private_cost")
    r._car_closed_slots = np.concatenate([np.asarray(a["_car_closed_slots"]) + k * S
                                          for k in range(K)])
    r._through_slots = np.concatenate([np.asarray(a["_through_slots"]) + k * S
                                       for k in range(K)])
    r.closures = obj["closures"]
    r._through_exits = obj["_through_exits"]
    r._pair_up()
    r._build_indexes()
    print(f"paired: {r.n_pairs:,} pairs over {len(r.tail):,} slots", flush=True)
    for name in ("tail", "head", "eidx", "flip", "d_minutes", "u_tail", "u_head",
                 "slot_pair", "_pair_indptr", "_pair_slots", "_pair_start",
                 "_rev_pairs", "_rev_indptr", "_tail_order", "_tail_start",
                 "_edge_order", "_edge_start", "_slot_flags", "_private_slots",
                 "_private_cost", "_car_closed_slots", "_through_slots",
                 "edge_u_idx", "edge_v_idx", "real_node"):
        arrays[name] = getattr(r, name)
    arrays.update(r.node_grid.arrays("node_grid"))
    arrays.update(r.edge_grid.arrays("edge_grid"))
    if access:
        from compact import Grid
        arrays.update(Grid.build(Lines(arrays["access.xy"], arrays["access.start"])
                                 .bounds(), 0.01).arrays("access_grid"))
    for name, arr in arrays.items():
        np.save(out / f"{name}.npy", np.ascontiguousarray(arr))

    def mapped(d, f):
        return {f(k_): v_ for k_, v_ in d.items()}

    objects = dict(obj)
    objects.update(n=r.n, n_real=r.n_real, m=r.m, n_pairs=r.n_pairs)
    objects["node_copies"] = {int(rmap(key, k)): rmap(val, k)
                              for k in range(K) for key, val in obj["node_copies"].items()}
    objects["through_copy"] = {(e + k * m, int(rmap(j, k))): int(rmap(c, k))
                               for k in range(K)
                               for (e, j), c in obj["through_copy"].items()}
    for name in ("_through_split", "_through_all_year"):
        objects[name] = {int(rmap(x, k)) for k in range(K) for x in obj[name]}
    for name in ("_way_out", "_way_in"):
        objects[name] = {int(rmap(x, k)): int(rmap(y, k))
                         for k in range(K) for x, y in obj[name].items()}
    with open(out / "objects.pickle", "wb") as f:
        pickle.dump(objects, f, protocol=pickle.HIGHEST_PROTOCOL)
    (out / "manifest.json").write_text(json.dumps({
        "version": Router.PACK_VERSION, "sources": {}, "arrays": sorted(arrays),
        "nodes": int(r.n_real), "edges": int(r.m), "routing_nodes": int(r.n),
        "region": "a synthetic US of New England copies",
        "built": datetime.now().isoformat(timespec="seconds")}, indent=1))
    size = sum(f.stat().st_size for f in out.iterdir())
    print(f"wrote {out}: {size / 1e9:.2f} GB", flush=True)


def _links(lat0, lon0, shifts, cols, rows, nr):
    """Two-way links between facing edges of neighbouring copies: east edge
    to the next copy's west edge, south edge to the next row's north edge.
    Each pairs a sample of junctions on one side with the nearest on the
    other, as (node, node) in the tiled graph's real indices."""
    rng = np.random.default_rng(20261018)
    east = np.flatnonzero(lon0 > np.quantile(lon0, 0.97))
    west = np.flatnonzero(lon0 < np.quantile(lon0, 0.03))
    south = np.flatnonzero(lat0 < np.quantile(lat0, 0.03))
    north = np.flatnonzero(lat0 > np.quantile(lat0, 0.97))
    out = []
    for r in range(rows):
        for c in range(cols):
            k = r * cols + c
            for here, there, other in ((east, west, k + 1 if c + 1 < cols else None),
                                       (south, north, k + cols if r + 1 < rows else None)):
                if other is None:
                    continue
                pick = rng.choice(here, size=min(LINKS, len(here)), replace=False)
                (ax, ay), (bx, by) = shifts[k], shifts[other]
                tlat, tlon = lat0[there] + by, lon0[there] + bx
                for i in pick:
                    d = haversine_km(lat0[i] + ay, lon0[i] + ax, tlat, tlon)
                    out.append((k * nr + int(i), other * nr + int(there[np.argmin(d)])))
    return out


if __name__ == "__main__":
    main()
