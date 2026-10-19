"""Compare a stitched graph with a reference build of the same ground.

Usage:
  compare.py graph  <reference_dir> <stitched_dir> <states.parquet> <out.json> [region ...]
  compare.py naive  <reference_dir> <states.parquet> <out.json> <a.osm.pbf> <b.osm.pbf> [region ...]
  compare.py routes <dir_a> <dir_b> <pairs.json> <out.csv>
  compare.py sample <place_points.parquet> <out.json> <per_band> <seed>

`graph` matches edges on (u, v, geometry), a multiset, restricted on the reference
side to the edges whose midpoint the named regions own (regions.Owner), since the
reference may run past them (the New England extract carries strips of New York,
Quebec and New Brunswick). Every column of the matched edges is compared; the
unmatched ones are classed by whether the stitch built them at all.

`naive` is the method the brief rules out, built for the record: graph.py's own
edge splitting run on two state extracts separately, each counting its junctions
from its own ways, the two concatenated and de-duplicated on (u, v). Unscored,
since the defect is in the topology.

`sample` draws town-to-town pairs with tools/route_census.py's own stratified
sampler (OSM place nodes, four great-circle bands from 10 to 200 km).

`routes` routes each pair on both graphs with the shipped Router, fastest and at
pref 0.5 and 1.0, and writes the km, minutes, mean score and whether the edge
sequence is the same.
"""
import hashlib
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pipeline"))
sys.path.insert(0, str(HERE))
import regions  # noqa: E402

NUMERIC_EXACT = ["length_m", "minutes", "n_signal_fwd", "n_signal_rev", "n_stop_fwd", "n_stop_rev",
                 "n_giveway_fwd", "n_giveway_rev"]
TEXT_EXACT = ["oneway", "name", "ref", "highway", "junction", "dest_ref", "dest_name"]


def keyed(edges: gpd.GeoDataFrame) -> pd.DataFrame:
    wkb = shapely.to_wkb(edges.geometry.values)
    g = np.array([hashlib.blake2b(b, digest_size=8).hexdigest() for b in wkb])
    k = pd.DataFrame({"u": edges["u"].to_numpy(), "v": edges["v"].to_numpy(), "g": g})
    k["dup"] = k.groupby(["u", "v", "g"]).cumcount()
    return k


def owned_by(edges: gpd.GeoDataFrame, states: str, names: list[str]) -> np.ndarray:
    all_regions = regions.load(states)
    idx = regions.Owner(all_regions).of_lines(np.asarray(edges.geometry.values))
    region_names = np.array([r.name for r in all_regions] + [""])
    return np.isin(region_names[idx], names)


def graph_cmd(ref_dir, st_dir, states, out, names):
    ref = gpd.read_parquet(Path(ref_dir) / "graph_edges.parquet")
    st = gpd.read_parquet(Path(st_dir) / "graph_edges.parquet")
    ref = ref[owned_by(ref, states, names)].reset_index(drop=True)
    kr, ks = keyed(ref), keyed(st)
    kr["r"], ks["s"] = np.arange(len(kr)), np.arange(len(ks))
    m = kr.merge(ks, on=["u", "v", "g", "dup"], how="outer", indicator=True)
    both = m[m["_merge"] == "both"]
    r_rows, s_rows = both["r"].to_numpy().astype(int), both["s"].to_numpy().astype(int)
    km = ref["length_m"].to_numpy()[r_rows] / 1000
    res = {"reference_edges_in_regions": len(ref), "stitched_edges": len(st),
           "matched": len(both), "reference_only": int((m["_merge"] == "left_only").sum()),
           "stitched_only": int((m["_merge"] == "right_only").sum()),
           "reference_only_km": float(ref["length_m"].to_numpy()[
               m.loc[m["_merge"] == "left_only", "r"].to_numpy().astype(int)].sum() / 1000),
           "stitched_only_km": float(st["length_m"].to_numpy()[
               m.loc[m["_merge"] == "right_only", "s"].to_numpy().astype(int)].sum() / 1000),
           "columns": {}}
    for col in NUMERIC_EXACT + TEXT_EXACT:
        if col in ref and col in st:
            a, b = ref[col].to_numpy()[r_rows], st[col].to_numpy()[s_rows]
            same = (a == b) if col in TEXT_EXACT else np.isclose(a.astype(float), b.astype(float),
                                                                 rtol=0, atol=1e-9)
            res["columns"][col] = {"differ": int((~same).sum())}
    for col in [c for c in st.columns if c.startswith("c_")] + ["score_adj", "unpaved_frac", "score"]:
        if col in ref and col in st:
            d = np.abs(ref[col].to_numpy()[r_rows] - st[col].to_numpy()[s_rows])
            res["columns"][col] = {"differ": int((d > 1e-9).sum()), "max": float(d.max()),
                                   "km_over_0.25": float(km[d > 0.25].sum()),
                                   "km_share_over_0.25": float(km[d > 0.25].sum() / km.sum())}
    # The stitched-only and reference-only edges, by whether a region built them
    # before the component cut and by how far they sit from a region border.
    for side, frame, rows in (("reference_only", ref, m.loc[m["_merge"] == "left_only", "r"]),
                              ("stitched_only", st, m.loc[m["_merge"] == "right_only", "s"])):
        sample = frame.iloc[rows.to_numpy().astype(int)]
        res[side + "_by_highway_km"] = (sample.groupby("highway")["length_m"].sum() / 1000).round(2).to_dict()
        res[side + "_examples"] = [
            {"u": int(r.u), "v": int(r.v), "name": r["name"], "highway": r.highway,
             "length_m": round(float(r.length_m), 1),
             "lonlat": [round(c, 5) for c in shapely.get_coordinates(r.geometry)[0]]}
            for _, r in sample.head(15).iterrows()]
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if not k.endswith("examples")}, indent=1))


def naive_cmd(ref_dir, states, out, pbf_a, pbf_b, names):
    import common
    import graph
    from pyproj import Transformer
    fwd = Transformer.from_crs(4326, common.CRS_METERS, always_xy=True)
    frames = []
    for pbf in (pbf_a, pbf_b):
        h = graph.GraphHandler()
        h.apply_file(pbf, locations=True, idx="flex_mem")
        rows = graph.build_edges(h.ways, h.node_count, lambda x, y: fwd.transform(x, y), h.controls)
        frames.append(gpd.GeoDataFrame(rows, geometry="geometry", crs=4326))
    naive = pd.concat(frames, ignore_index=True).drop_duplicates(["u", "v"]).reset_index(drop=True)
    naive = naive[owned_by(naive, states, names)].reset_index(drop=True)
    ref = gpd.read_parquet(Path(ref_dir) / "graph_edges.parquet")
    ref = ref[owned_by(ref, states, names)].reset_index(drop=True)
    # The reference has had its component cut; compare only what both could hold.
    in_ref_nodes = set(ref["u"]) | set(ref["v"])
    naive = naive[naive["u"].isin(in_ref_nodes) & naive["v"].isin(in_ref_nodes)].reset_index(drop=True)
    kr, kn = keyed(ref), keyed(naive)
    m = kr.merge(kn, on=["u", "v", "g", "dup"], how="outer", indicator=True)
    left, right = m["_merge"] == "left_only", m["_merge"] == "right_only"
    res = {"reference_edges": len(ref), "naive_edges": len(naive),
           "matched": int((m["_merge"] == "both").sum()),
           "reference_edges_naive_lacks": int(left.sum()),
           "naive_edges_reference_lacks": int(right.sum())}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def routes_cmd(dir_a, dir_b, pairs_path, out):
    """One Router at a time: two New England graphs at once is ~8 GB."""
    import gc
    from router import Router
    pairs = json.loads(Path(pairs_path).read_text())
    found = {}
    for side, d in (("a", dir_a), ("b", dir_b)):
        r = Router(d)
        for p in pairs:
            src, so = r.snap(*p["from"])
            dst, do = r.snap_destination(*p["to"])
            for pref in (0.0, 0.5, 1.0):
                res = r.route(src, dst, pref) if src != dst else None
                found[(side, p["name"], pref)] = {
                    "snap_m": round(max(so, do), 1),
                    "km": round(res.km, 3) if res else None,
                    "min": round(res.minutes, 2) if res else None,
                    "score": round(res.mean_score, 3) if res else None,
                    "path": list(zip(res.edges["u"].tolist(), res.edges["v"].tolist())) if res else None}
        del r
        gc.collect()
    rows = []
    for p in pairs:
        for pref in (0.0, 0.5, 1.0):
            a, b = found[("a", p["name"], pref)], found[("b", p["name"], pref)]
            row = {"pair": p["name"], "pref": pref}
            for side, x in (("a", a), ("b", b)):
                row.update({f"{side}_{k}": v for k, v in x.items() if k != "path"})
            row["same_path"] = a["path"] is not None and a["path"] == b["path"]
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    print(df.to_string())


def sample_cmd(places_path, out, per_band, seed):
    sys.path.insert(0, str(HERE.parent))
    from route_census import sample_pairs
    places = gpd.read_parquet(places_path)
    lat, lon = places.geometry.y.to_numpy(), places.geometry.x.to_numpy()
    picked, _ = sample_pairs(lat, lon, int(per_band), int(seed))
    pairs = [{"name": f"{a:g}-{b:g}:{n:03d}", "gc_km": round(gc, 1),
              "from": [round(float(lat[i]), 6), round(float(lon[i]), 6)],
              "to": [round(float(lat[j]), 6), round(float(lon[j]), 6)]}
             for (a, b), group in picked.items() for n, (i, j, gc) in enumerate(group)]
    Path(out).write_text("[\n" + ",\n".join(json.dumps(p) for p in pairs) + "\n]\n")
    print(f"{len(pairs)} pairs")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "graph":
        graph_cmd(*args[:4], args[4:])
    elif cmd == "naive":
        naive_cmd(*args[:5], args[5:])
    elif cmd == "routes":
        routes_cmd(*args)
    elif cmd == "sample":
        sample_cmd(*args)
