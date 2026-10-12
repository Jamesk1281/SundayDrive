"""Tag quality of a state extract, by kilometre of the graph a route can drive.

Rebuilds graph.py's graph without building it, the same way the feasibility
review's count_graph.py does: DRIVABLE plus the access rule, oneway inference,
splits at nodes two ways share, segments under 1 m dropped, then the largest
strongly connected component. Every metric is then weighted by the length of
the edges in that component, so a tag counts for the kilometres a route drives
on it rather than for the objects that carry it (docs/us-map-data-findings.md,
"Tier 2"). The node and edge counts are printed so the reconstruction can be
checked against count_graph.py; they must match it exactly.

What it measures, per state:
  - km by class, and `maxspeed` coverage by class with the length-weighted
    harmonic mean of the tagged speeds against graph.py's SPEED_KMH;
  - `surface` coverage and the share in score.py's UNPAVED set;
  - `smoothness`, `4wd_only` and `tracktype`, which nothing in pipeline/ reads;
  - `tiger:reviewed=no`, and the TIGER 2005 import's own 4WD class
    (`tiger:cfcc` A5x, "vehicular trail");
  - signals, stops and give-ways per 100 km, as graph.py counts them (a node
    of a drivable way);
  - turn restrictions per 1,000 junctions, via-node and via-way apart;
  - seasonal tagging: what closures.py's `way_windows` closes, and every
    seasonal or car-key conditional it does not, on ways and on gate nodes;
  - road-route relations naming a scenic or byway network, with the drivable
    km of their members and whether extract.py's rule admits them.

The same totals are also given over every accepted way (no component, no
1 m drop), which is what the review's rough_tags.py and maxspeed.py weight
by, so its Colorado figures can be reproduced as a check.

Usage: python -I osm_metrics.py <repo_pipeline_dir> <file.osm.pbf> <label> <out.json>
"""

import json
import math
import re
import resource
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, sys.argv[1])
import osmium  # noqa: E402
from common import (DRIVABLE, ONEWAY_FWD, ONEWAY_REV, PRIVATE_ACCESS,  # noqa: E402
                    CONTROL_KINDS, closed_to_cars)
from graph import SPEED_KMH, parse_maxspeed  # noqa: E402
from closures import CAR_KEYS, SEASONAL, conditional_windows, way_windows  # noqa: E402
from extract import BYWAY_NETWORKS  # noqa: E402
from score import UNPAVED  # noqa: E402

pbf, label, out_path = sys.argv[2], sys.argv[3], sys.argv[4]
t0 = time.time()

HW = sorted(DRIVABLE)
HW_IX = {h: i for i, h in enumerate(HW)}
MAIN = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
        "residential")
SMOOTH_BAD = {"bad"}
SMOOTH_VBAD = {"very_bad", "horrible", "very_horrible", "impassable"}
SMOOTH_OK = {"excellent", "good", "intermediate"}
GATES = {"gate", "lift_gate", "swing_gate"}
SCENIC_WORD = re.compile(r"scenic|byway|parkway|backway|skyway", re.IGNORECASE)
ORDINAL = re.compile(r"(\d)(st|nd|rd|th)\b", re.IGNORECASE)

# --- relations: turn restrictions and road routes ---------------------------
restrictions = []            # (kind, from_way, via_kind, via_ref, to_way)
routes = {}                  # rel id -> {tags, ways}
for r in osmium.FileProcessor(pbf, osmium.osm.RELATION):
    t = r.tags
    typ = t.get("type")
    if typ in ("restriction", "restriction:motorcar"):
        kind = (t.get("restriction") or t.get("restriction:motorcar") or "")
        kind = kind.split("@")[0].strip()
        frm = to = None
        via = []
        for m in r.members:
            if m.role == "from" and m.type == "w":
                frm = m.ref
            elif m.role == "to" and m.type == "w":
                to = m.ref
            elif m.role == "via":
                via.append((m.type, m.ref))
        vk = via[0][0] if via else ""
        restrictions.append((kind, frm, vk, via[0][1] if via else None, to))
    elif t.get("route") == "road":
        routes[r.id] = {
            "tags": {k: t.get(k, "") for k in ("network", "name", "ref", "scenic",
                                                 "official_name", "operator")},
            "ways": [m.ref for m in r.members if m.type == "w"],
        }
t_rel = time.time() - t0

# --- nodes and ways ---------------------------------------------------------
controls = {}                # node id -> kind
gate_nodes = {}              # node id -> tags, for seasonal / timed gates
refs_chunks, lon_chunks, lat_chunks = [], [], []
cols = defaultdict(list)     # per-way attributes
skipped_private = 0

fp = (osmium.FileProcessor(pbf, osmium.osm.NODE | osmium.osm.WAY)
      .with_locations()
      .with_filter(osmium.filter.KeyFilter("highway", "barrier")))
for o in fp:
    tags = o.tags
    if o.is_node():
        kind = CONTROL_KINDS.get(tags.get("highway"))
        if kind:
            controls[o.id] = kind
        b = tags.get("barrier")
        if b:
            timed = {k: tags.get(k) for k in [f"{c}:conditional" for c in CAR_KEYS]
                     + ["seasonal", "opening_hours", "winter_service"] if tags.get(k)}
            if timed:
                gate_nodes[o.id] = {"barrier": b, **timed,
                                    **({"access": tags.get("access")} if tags.get("access") else {}),
                                    **({"name": tags.get("name")} if tags.get("name") else {})}
        continue
    hw = tags.get("highway")
    if hw not in DRIVABLE:
        continue
    if tags.get("access") in PRIVATE_ACCESS and tags.get("motor_vehicle") != "yes":
        skipped_private += 1
        continue
    ids, lons, lats = [], [], []
    for n in o.nodes:
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
    c = cols
    c["way_id"].append(o.id)
    c["ow"].append(1 if ow in ONEWAY_FWD else (-1 if ow in ONEWAY_REV else 0))
    c["hw"].append(HW_IX[hw])
    v = parse_maxspeed(tags.get("maxspeed", ""))
    c["maxspeed"].append(v if (v and v > 5) else np.nan)
    c["maxspeed_any"].append(bool(tags.get("maxspeed")))
    s = tags.get("surface", "")
    c["surf"].append(0 if not s else (2 if s in UNPAVED else 1))
    sm = tags.get("smoothness", "")
    c["smooth"].append(0 if not sm else 3 if sm in SMOOTH_VBAD else 2 if sm in SMOOTH_BAD
                       else 1)
    c["fourwd"].append(tags.get("4wd_only") == "yes")
    tt = tags.get("tracktype", "")
    c["track"].append(0 if not tt else (2 if tt in ("grade3", "grade4", "grade5") else 1))
    c["tiger_no"].append(tags.get("tiger:reviewed") == "no")
    cfcc = tags.get("tiger:cfcc", "")
    c["tiger_any"].append(bool(cfcc) or tags.get("tiger:reviewed") is not None)
    c["cfcc_a5"].append(any(p.strip().startswith("A5") for p in cfcc.split(";")))
    seas = (tags.get("seasonal") or "").strip().lower()
    c["seasonal_any"].append(bool(seas) and seas != "no")
    c["seasonal_read"].append(bool(way_windows(tags)))
    c["cond_car"].append(any(tags.get(f"{k}:conditional") for k in CAR_KEYS))
    c["winter_no"].append((tags.get("winter_service") or "").strip().lower() == "no")
    ctag = closed_to_cars(tags)
    c["closed"].append(bool(ctag) or (tags.get("ford") or "").strip().lower() == "yes")
    c["closed_tag"].append(ctag or ("ford=yes" if c["closed"][-1] else ""))
    # How closures.py's grammar reads this way's car conditionals: "closes",
    # its first reason for closing nothing, or "" when there are none. An
    # ordinal date ("Oct 14th") is unrecognised; `cond_fix` says whether
    # dropping the suffix alone would have let it close the road.
    verdict, fix, raw = "", False, ""
    for k in CAR_KEYS:
        v = tags.get(f"{k}:conditional")
        if not v:
            continue
        raw = raw or f"{k}:conditional={v}"
        wins, why = conditional_windows(v)
        if wins:
            verdict = "closes"
            break
        verdict = verdict or (why[0] if why else "no closing rule")
        if conditional_windows(ORDINAL.sub(r"\1", v))[0]:
            fix = True
    c["cond_verdict"].append(verdict)
    c["cond_fix"].append(fix and verdict != "closes")
    c["cond_raw"].append(raw if verdict and verdict != "closes" else "")
    c["seasonal_val"].append(seas if seas and seas != "no" and seas not in SEASONAL else "")
t_parse = time.time() - t0

n_ways = len(refs_chunks)
lens = np.array([len(r) for r in refs_chunks], dtype=np.int64)
allrefs = np.concatenate(refs_chunks)
alllon = np.concatenate(lon_chunks)
alllat = np.concatenate(lat_chunks)
del refs_chunks, lon_chunks, lat_chunks
A = {k: np.array(v) for k, v in cols.items()}
del cols

uniq, inv, counts = np.unique(allrefs, return_inverse=True, return_counts=True)
deg = counts[inv]
starts = np.r_[0, np.cumsum(lens)[:-1]]
ends = np.cumsum(lens) - 1
is_break = deg >= 2
is_break[starts] = True
is_break[ends] = True

R = 6371008.8
lat1, lat2 = np.radians(alllat[:-1]), np.radians(alllat[1:])
dlat = lat2 - lat1
dlon = np.radians(alllon[1:] - alllon[:-1])
a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
seg = 2 * R * np.arcsin(np.sqrt(np.minimum(a, 1.0)))
seg[ends[:-1]] = 0.0
cum = np.r_[0.0, np.cumsum(seg)]
way_len_all = (cum[ends] - cum[starts]) / 1000.0          # km per accepted way

way_of = np.repeat(np.arange(n_ways), lens)
bpos = np.flatnonzero(is_break)
same = way_of[bpos[:-1]] == way_of[bpos[1:]]
ea, eb = bpos[:-1][same], bpos[1:][same]
elen = cum[eb] - cum[ea]
keep = elen >= 1.0
ea, eb, elen = ea[keep], eb[keep], elen[keep]
ew = way_of[ea]
eu, ev = inv[ea], inv[eb]
eow = A["ow"].astype(np.int8)[ew]

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

# Per-way km inside the component: what every metric below is weighted by.
way_km = np.bincount(ew[emask], weights=elen[emask] / 1000.0, minlength=n_ways)
total_km = float(way_km.sum())


def km(mask, w=way_km):
    return float(w[mask].sum())


def pct(mask, base=None, w=way_km):
    base = np.ones(n_ways, bool) if base is None else base
    d = km(base, w)
    return round(100 * km(mask & base, w) / d, 2) if d else None


hw = A["hw"]
cls = {h: hw == HW_IX[h] for h in HW}
out = {
    "label": label,
    "graph_nodes": int(len(nodes_in)),
    "graph_edges": int(emask.sum()),
    "graph_km": round(total_km, 1),
    "accepted_ways": int(n_ways),
    "accepted_km": round(float(way_len_all.sum()), 1),
    "skipped_private_ways": skipped_private,
    "km_by_class": {h: round(km(cls[h]), 1) for h in HW},
}

# maxspeed by class: coverage and length-weighted harmonic mean
ms = A["maxspeed"]
tagged = ~np.isnan(ms)
speed = {}
for h in HW:
    m = cls[h]
    tk = km(m & tagged)
    inv_sum = float((way_km[m & tagged] / ms[m & tagged]).sum())
    speed[h] = {"km": round(km(m), 1), "tagged_pct": pct(tagged, m),
                "tagged_hm_kmh": round(tk / inv_sum, 1) if inv_sum else None,
                "default_kmh": SPEED_KMH[h]}
out["maxspeed"] = speed
out["maxspeed_any_tag_pct"] = pct(A["maxspeed_any"])

surf, smooth, track = A["surf"], A["smooth"], A["track"]
out["surface"] = {
    "tagged_pct": pct(surf > 0), "unpaved_pct": pct(surf == 2),
    "untagged_pct": pct(surf == 0),
    "unpaved_pct_by_class": {h: pct(surf == 2, cls[h]) for h in MAIN},
    "untagged_pct_by_class": {h: pct(surf == 0, cls[h]) for h in MAIN},
}
out["roughness"] = {
    "smoothness_tagged_pct": pct(smooth > 0),
    "smoothness_bad_or_worse_km": round(km(smooth >= 2), 1),
    "smoothness_very_bad_or_worse_km": round(km(smooth == 3), 1),
    "4wd_only_km": round(km(A["fourwd"]), 1),
    "4wd_or_very_bad_km": round(km(A["fourwd"] | (smooth == 3)), 1),
    "tracktype_tagged_km": round(km(track > 0), 1),
    "tracktype_grade3plus_km": round(km(track == 2), 1),
    "tiger_cfcc_a5_km": round(km(A["cfcc_a5"]), 1),
    "tiger_cfcc_a5_untagged_rough_km": round(km(A["cfcc_a5"] & ~A["fourwd"] & (smooth < 2)
                                                & (track < 2)), 1),
    "4wd_or_very_bad_km_by_class": {h: round(km((A["fourwd"] | (smooth == 3)) & cls[h]), 1)
                                     for h in MAIN},
}
out["tiger"] = {
    "reviewed_no_pct": pct(A["tiger_no"]),
    "tiger_origin_pct": pct(A["tiger_any"]),
    "reviewed_no_pct_by_class": {h: pct(A["tiger_no"], cls[h]) for h in MAIN},
}
out["seasonal"] = {
    "closures_py_closes_km": round(km(A["seasonal_read"]), 1),
    "closures_py_closes_ways": int((A["seasonal_read"] & (way_km > 0)).sum()),
    "seasonal_any_km": round(km(A["seasonal_any"]), 1),
    "car_conditional_km": round(km(A["cond_car"]), 1),
    "winter_service_no_km": round(km(A["winter_no"]), 1),
    "seasonal_values_not_read": dict(Counter(v for v, k in zip(A["seasonal_val"], way_km)
                                             if v and k > 0).most_common(12)),
    "closed_to_cars_or_ford_km": round(km(A["closed"]), 1),
    "closed_km_by_tag": dict(sorted(
        ((t, round(float(way_km[A["closed_tag"] == t].sum()), 1))
         for t in set(A["closed_tag"].tolist()) if t), key=lambda x: -x[1])[:15]),
    "permit_km": round(float(way_km[np.char.endswith(A["closed_tag"].astype(str),
                                                      "=permit")].sum()), 1),
    "car_conditional_km_by_verdict": {v: round(km(A["cond_verdict"] == v), 1)
                                      for v in sorted(set(A["cond_verdict"].tolist())) if v},
    "car_conditional_ordinal_fixable_km": round(km(A["cond_fix"]), 1),
    "car_conditional_unread_top": dict(sorted(
        ((r, round(float(way_km[A["cond_raw"] == r].sum()), 1))
         for r in set(A["cond_raw"].tolist()) if r), key=lambda x: -x[1])[:15]),
}

# Positions covered by an edge of the component, for the node counts.
cover = np.zeros(len(allrefs) + 1, dtype=np.int32)
np.add.at(cover, ea[emask], 1)
np.add.at(cover, eb[emask] + 1, -1)
covered = np.cumsum(cover)[:-1] > 0
on_graph = np.unique(allrefs[covered])
# Terrarium z11 tiles that hold a vertex of the graph: the tiles a build that
# fetched only where roads are would need, against the state's whole outline.
zn = 2 ** 11
cl, ct = alllon[covered], np.radians(alllat[covered])
tx = np.floor((cl + 180.0) / 360.0 * zn).astype(np.int64)
ty = np.floor((1.0 - np.arcsinh(np.tan(ct)) / math.pi) / 2.0 * zn).astype(np.int64)
out["terrarium_z11_tiles_with_graph"] = int(len(np.unique(tx * zn + ty)))
del cl, ct, tx, ty

ctrl_ids = np.fromiter(controls.keys(), dtype=np.int64, count=len(controls))
ctrl_on = ctrl_ids[np.isin(ctrl_ids, on_graph)]
ctrl_kinds = Counter(controls[int(i)] for i in ctrl_on)
out["controls"] = {
    "on_graph": {k: int(v) for k, v in ctrl_kinds.items()},
    "in_file": dict(Counter(controls.values())),
    "per_100km": {k: round(100 * v / total_km, 2) for k, v in ctrl_kinds.items()},
    "all_per_100km": round(100 * len(ctrl_on) / total_km, 2),
}
gate_ids = np.fromiter(gate_nodes.keys(), dtype=np.int64, count=len(gate_nodes))
gates_on = [int(i) for i in gate_ids[np.isin(gate_ids, on_graph)]]
out["timed_barriers_on_graph"] = {
    "count": len(gates_on),
    "by_key": dict(Counter(k for i in gates_on for k in gate_nodes[i]
                           if k not in ("barrier", "access", "name"))),
    "list": [{"id": i, **gate_nodes[i]} for i in gates_on[:200]],
}

# Junctions: component nodes where three or more edge ends meet.
end_deg = np.bincount(np.concatenate([eu[emask], ev[emask]]), minlength=nn)
junction = (end_deg >= 3) & inbig
graph_way_ids = set(A["way_id"][way_km > 0].tolist())
id_of = dict(zip(uniq.tolist(), range(nn))) if len(restrictions) else {}
rc = Counter()
for kind, frm, vk, vref, to in restrictions:
    if frm not in graph_way_ids or to not in graph_way_ids:
        rc["from/to not both in graph"] += 1
        continue
    if vk == "n":
        j = id_of.get(vref)
        rc["via node, at a junction" if j is not None and junction[j] else "via node, elsewhere"] += 1
    elif vk == "w":
        rc["via way"] += 1
    else:
        rc["no via"] += 1
n_junc = int(junction.sum())
out["turn_restrictions"] = {
    "relations_in_file": len(restrictions),
    "by_where": dict(rc),
    "junctions": n_junc,
    "via_node_per_1000_junctions": round(1000 * rc["via node, at a junction"] / n_junc, 2)
    if n_junc else None,
    "via_way_per_1000_junctions": round(1000 * rc["via way"] / n_junc, 2) if n_junc else None,
}

# Road routes naming scenery, with their drivable km.
km_of_way = dict(zip(A["way_id"].tolist(), way_km.tolist()))
nets = defaultdict(lambda: {"relations": 0, "scenic_yes": 0, "admitted": 0, "km": 0.0,
                            "admitted_km": 0.0})
byway_rels = []
for rid, r in routes.items():
    t = r["tags"]
    net = t["network"]
    rkm = sum(km_of_way.get(w, 0.0) for w in set(r["ways"]))
    admitted = net in BYWAY_NETWORKS or t["scenic"] == "yes"
    named = bool(SCENIC_WORD.search(net)) or bool(SCENIC_WORD.search(t["name"]))
    if not (named or t["scenic"] == "yes"):
        continue
    n = nets[net or "(none)"]
    n["relations"] += 1
    n["scenic_yes"] += t["scenic"] == "yes"
    n["admitted"] += admitted
    n["km"] += rkm
    n["admitted_km"] += rkm if admitted else 0.0
    byway_rels.append({"id": rid, **t, "admitted": admitted, "drivable_km": round(rkm, 1)})
out["byways"] = {
    "road_route_relations": len(routes),
    "networks": {k: {**v, "km": round(v["km"], 1), "admitted_km": round(v["admitted_km"], 1)}
                 for k, v in sorted(nets.items())},
    "relations": sorted(byway_rels, key=lambda r: (r["network"], r["name"])),
}

# The review's weighting (every accepted way), for reproducing its numbers.
W = way_len_all
out["accepted_way_basis"] = {
    "km": round(float(W.sum()), 1),
    "unpaved_pct": pct(surf == 2, w=W), "untagged_surface_pct": pct(surf == 0, w=W),
    "smoothness_bad_or_worse_km": round(km(smooth >= 2, W), 1),
    "4wd_only_km": round(km(A["fourwd"], W), 1),
    "4wd_or_very_bad_km": round(km(A["fourwd"] | (smooth == 3), W), 1),
    "maxspeed_tagged_pct": {h: pct(tagged, cls[h], W) for h in MAIN},
}
out["timing_s"] = {"relations": round(t_rel, 1), "parse": round(t_parse, 1),
                   "total": round(time.time() - t0, 1)}
out["peak_rss_gb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2)
with open(out_path, "w") as f:
    json.dump(out, f, indent=1)
print(json.dumps({k: out[k] for k in ("label", "graph_nodes", "graph_edges", "graph_km",
                                      "timing_s", "peak_rss_gb")}))
