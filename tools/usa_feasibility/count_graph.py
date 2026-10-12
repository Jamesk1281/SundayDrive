"""Count the routing graph graph.py would build from a PBF, without building it.

Mirrors GraphHandler.way (DRIVABLE + the access rule + oneway inference),
build_edges (split at nodes referenced >= 2 times, drop segments < 1 m) and
largest_component (strongly connected, oneway-aware). Prints one JSON line.

Usage: python -I count_graph.py <repo_pipeline_dir> <file.osm.pbf> <label>
"""
import json
import math
import resource
import sys
import time

import numpy as np

sys.path.insert(0, sys.argv[1])
import osmium  # noqa: E402
from common import DRIVABLE, ONEWAY_FWD, ONEWAY_REV, PRIVATE_ACCESS  # noqa: E402

pbf, label = sys.argv[2], sys.argv[3]
t0 = time.time()

refs_chunks, lon_chunks, lat_chunks = [], [], []
way_len, way_ow, way_hw = [], [], []
HW = sorted(DRIVABLE)
HW_IX = {h: i for i, h in enumerate(HW)}

fp = (osmium.FileProcessor(pbf, osmium.osm.NODE | osmium.osm.WAY)
      .with_locations()
      .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
      .with_filter(osmium.filter.KeyFilter("highway")))
for w in fp:
    tags = w.tags
    hw = tags.get("highway")
    if hw not in DRIVABLE:
        continue
    if tags.get("access") in PRIVATE_ACCESS and tags.get("motor_vehicle") != "yes":
        continue
    ids, lons, lats = [], [], []
    for n in w.nodes:
        loc = n.location
        if not loc.valid():
            continue
        ids.append(n.ref)
        lons.append(loc.lon)
        lats.append(loc.lat)
    if len(ids) < 2:
        continue
    oneway = tags.get("oneway", "")
    if not oneway and (tags.get("junction") in ("roundabout", "circular") or hw == "motorway"):
        oneway = "yes"
    ow = oneway.strip().lower()
    refs_chunks.append(np.array(ids, dtype=np.int64))
    lon_chunks.append(np.array(lons))
    lat_chunks.append(np.array(lats))
    way_ow.append(1 if ow in ONEWAY_FWD else (-1 if ow in ONEWAY_REV else 0))
    way_hw.append(HW_IX[hw])
t_parse = time.time() - t0

n_ways = len(refs_chunks)
lens = np.array([len(r) for r in refs_chunks], dtype=np.int64)
allrefs = np.concatenate(refs_chunks)
alllon = np.concatenate(lon_chunks)
alllat = np.concatenate(lat_chunks)
del refs_chunks, lon_chunks, lat_chunks
uniq, inv, counts = np.unique(allrefs, return_inverse=True, return_counts=True)
deg = counts[inv]                               # node_count per position

starts = np.r_[0, np.cumsum(lens)[:-1]]
ends = np.cumsum(lens) - 1
is_break = deg >= 2
is_break[starts] = True
is_break[ends] = True

# haversine length of each consecutive pair within a way
R = 6371008.8
lat1, lat2 = np.radians(alllat[:-1]), np.radians(alllat[1:])
dlat = lat2 - lat1
dlon = np.radians(alllon[1:] - alllon[:-1])
a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
seg = 2 * R * np.arcsin(np.sqrt(np.minimum(a, 1.0)))
# zero the pairs that straddle two ways
seg[ends[:-1]] = 0.0
cum = np.r_[0.0, np.cumsum(seg)]

way_of = np.repeat(np.arange(n_ways), lens)
bpos = np.flatnonzero(is_break)
# consecutive breaks inside the same way form an edge
same = way_of[bpos[:-1]] == way_of[bpos[1:]]
ea, eb = bpos[:-1][same], bpos[1:][same]
elen = cum[eb] - cum[ea]
keep = elen >= 1.0
ea, eb, elen = ea[keep], eb[keep], elen[keep]
ew = way_of[ea]
eu, ev = inv[ea], inv[eb]                      # dense node ids
eow = np.array(way_ow, dtype=np.int8)[ew]
ehw = np.array(way_hw, dtype=np.int8)[ew]

from scipy.sparse import csr_matrix  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402

nn = len(uniq)
fwd_ok = eow != -1
rev_ok = eow != 1
tails = np.concatenate([eu[fwd_ok], ev[rev_ok]])
heads = np.concatenate([ev[fwd_ok], eu[rev_ok]])
g = csr_matrix((np.ones(len(tails), dtype=np.int8), (tails, heads)), shape=(nn, nn))
ncomp, labels = connected_components(g, directed=True, connection="strong")
big = np.bincount(labels).argmax()
inbig = labels == big
emask = inbig[eu] & inbig[ev]
nodes_in = np.unique(np.concatenate([eu[emask], ev[emask]]))

km_by_hw = {HW[i]: round(float(elen[emask & (ehw == i)].sum() / 1000), 1)
            for i in range(len(HW))}
out = {
    "label": label,
    "pbf_mb": round(__import__("os").path.getsize(pbf) / 1e6, 1),
    "drivable_ways": int(n_ways),
    "node_refs": int(len(allrefs)),
    "graph_nodes": int(len(nodes_in)),
    "graph_edges": int(emask.sum()),
    "directed_slots": int((fwd_ok & emask).sum() + (rev_ok & emask).sum()),
    "graph_km": round(float(elen[emask].sum() / 1000), 1),
    "dropped_nodes_not_scc": int(len(np.unique(np.concatenate([eu, ev]))) - len(nodes_in)),
    "km_by_highway": km_by_hw,
    "bbox": [round(float(alllon.min()), 3), round(float(alllat.min()), 3),
             round(float(alllon.max()), 3), round(float(alllat.max()), 3)],
    "parse_s": round(t_parse, 1),
    "total_s": round(time.time() - t0, 1),
    "peak_rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2),
}
print(json.dumps(out))
