"""What a road corridor shipped with each route would weigh, and what it covers.

    SUNDAYDRIVE_DATA=data/processed-ne \\
      .venv/bin/python tools/corridor_study.py [--routes N] [--export] [--out DIR]
    # and, for T2's whole-region search time, the whole graph alone:
    SUNDAYDRIVE_DATA=data/processed-ne \\
      .venv/bin/python tools/corridor_study.py --export-full --out DIR

Written for `docs/mid-drive-recovery-plan.md`, tier T1: the road network within
W metres of the route travels with it, so the phone can reroute when the server
cannot be reached. Three questions, each answered by measurement on the real
New England graph rather than by estimate:

1. **Payload.** How many nodes, edges and bytes a corridor holds at each width,
   in a compact binary encoding and gzipped, beside the route JSON the app
   already downloads. On routes and loops, including the 400 km loops `191e15c`
   allows.
2. **Coverage.** Whether a car that has missed a turn can be routed back from
   inside the corridor. For each turn on the route, every road leaving the
   junction that the route does not take is followed for D metres, straightest
   continuation first, the way a driver who missed the turn carries on. From
   that node: the best way back onto the route *ahead* (then following it) on
   the whole graph, the same inside the corridor, and the best new route to the
   destination on the whole graph, which is what the server would answer.
3. **Cost.** Server milliseconds to cut and encode a corridor, the share of an
   ordinary request that is.
4. **T1b, the server's own answer.** One more full-graph search per drive,
   backwards from the destination (and, for a loop, from its far point), gives
   every node its next hop and its cost to go. Timed here, and the bytes it
   adds to a corridor measured by encoding the next hop and the cost for every
   corridor node.
5. **How far "back to the route" really is.** For the same missed-turn points,
   the shortest drive (in km, any route node, ignoring scenery) against the
   straight-line distance a tier-0 banner could print. The ratio is how much a
   straight line under-states the way back — a river, a railway or a limited-
   access highway between the car and its route is what makes it large.
6. **What T3b would precompute.** Every turn on the route, and every road
   leaving it that the route does not take: one contingency search each.

For a loop, a rejoin before the far point is counted only up to the far point,
as the app's own reroutes go via it.

Every cost is the router's own: `Router._weights` at the route's pref, the
default weights, `avoid_unpaved` 1.0 and today's seasonal closures, over the
turn-restriction-split graph Dijkstra actually runs on. So "the corridor finds
the same route" means the same route the server would draw.

It loads one `Router` (about 4 GB) and a `LoopPlanner`. Run it with nothing
else heavy on the machine, and never beside a serving process.

The encoding is a design sketch, not a format: varints and zigzag deltas, a
string table, intermediate vertices at 1e-6 degrees. A real format would land
near it. The bytes it reports are what the data costs to carry, which is the
question; JSON is reported too, as the upper bound a quick implementation
would ship.
"""

import argparse
import gzip
import io
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import router as R  # noqa: E402
from looper import LoopPlanner  # noqa: E402

WIDTHS = [100, 250, 500, 1000, 2000]
# How far a driver who missed a turn has carried on when the reroute is asked
# for. 150 m is about where today's trigger fires (60 m off plus a three-fix
# streak at town speed); 400 and 1000 m are a driver who did not take the first
# replacement, or a reroute that waited out the backoff.
DEVIATIONS = [150, 400, 1000]
MAX_TURNS_PER_ROUTE = 5


# ---------------------------------------------------------------- encoding

def _varint(out: bytearray, v: int):
    v = int(v)
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return


def _zz(v: int) -> int:
    v = int(v)
    return (v << 1) ^ (v >> 63)


class StringTable:
    def __init__(self):
        self.index = {"": 0}
        self.strings = [""]

    def id(self, s):
        if s is None or (isinstance(s, float) and math.isnan(s)):
            s = ""
        s = str(s)
        if s not in self.index:
            self.index[s] = len(self.strings)
            self.strings.append(s)
        return self.index[s]

    def blob(self):
        return "\0".join(self.strings).encode("utf-8")


_CLASS = {}


def _class_code(h):
    if h not in _CLASS:
        _CLASS[h] = len(_CLASS)
    return _CLASS[h]


def _columns(router):
    """The whole-table columns the encoder reads, converted once per router.

    Read per call, they cost about a third of a second of whole-table work on
    every corridor, which is not what a corridor costs to cut."""
    c = getattr(router, "_encode_columns", None)
    if c is None:
        e, n = router.edges, router.nodes
        c = router._encode_columns = {
            "lat": n["lat"].to_numpy(), "lon": n["lon"].to_numpy(),
            "exit_ref": n["exit_ref"].to_numpy(),
            "name": e["name"].to_numpy(), "ref": e["ref"].to_numpy(),
            "highway": e["highway"].to_numpy(), "junction": e["junction"].to_numpy(),
            "dest_ref": e["dest_ref"].to_numpy(), "dest_name": e["dest_name"].to_numpy(),
            "oneway": e["oneway"].astype(str).str.lower().to_numpy(),
            "length": e["length_m"].to_numpy(), "score": e["score"].to_numpy(),
        }
    return c


def encode(router, edge_rows, node_set, *, per_request=True, slot_cost=None,
           restrictions=None, stubs=None):
    """Bytes for a set of undirected edge rows and their nodes.

    `per_request`: costs are the request's blended weights, one per direction
    (what T1 needs). Otherwise the raw ingredients a phone would re-blend for
    any pref (T2): minutes each way, the 0-10 score, the unpaved share.
    """
    col = _columns(router)
    nodes = np.array(sorted(node_set), dtype=np.int64)
    local = {int(n): i for i, n in enumerate(nodes)}
    st = StringTable()
    out = bytearray()

    # Nodes: zigzag deltas of microdegrees, in a coarse spatial order.
    lat = col["lat"][nodes]
    lon = col["lon"][nodes]
    order = np.lexsort((np.round(lon, 2), np.round(lat, 2)))
    remap = np.empty(len(nodes), np.int64)
    remap[order] = np.arange(len(nodes))
    _varint(out, len(nodes))
    plat = plon = 0
    for k in order:
        a, b = int(round(lat[k] * 1e6)), int(round(lon[k] * 1e6))
        _varint(out, _zz(a - plat)); _varint(out, _zz(b - plon))
        plat, plon = a, b
    exit_ref = col["exit_ref"][nodes]
    has_exit = [i for i in range(len(nodes)) if isinstance(exit_ref[i], str) and exit_ref[i]]
    _varint(out, len(has_exit))
    for i in has_exit:
        _varint(out, remap[i]); _varint(out, st.id(exit_ref[i]))

    # Edges.
    names, refs = col["name"], col["ref"]
    hw, junc = col["highway"], col["junction"]
    dref, dname = col["dest_ref"], col["dest_name"]
    ow, length, score = col["oneway"], col["length"], col["score"]
    _varint(out, len(edge_rows))
    prev_u = 0
    for r in edge_rows:
        u = remap[local[int(router.edge_u_idx[r])]]
        v = remap[local[int(router.edge_v_idx[r])]]
        _varint(out, _zz(u - prev_u)); _varint(out, _zz(v - u)); prev_u = u
        fwd = ow[r] not in R.ONEWAY_REV
        rev = ow[r] not in R.ONEWAY_FWD
        flags = (fwd << 0) | (rev << 1) | ((str(junc[r]) in ("roundabout", "circular")) << 2)
        out.append(flags)
        out.append(_class_code(hw[r]))
        _varint(out, st.id(names[r])); _varint(out, st.id(refs[r]))
        _varint(out, st.id(dref[r])); _varint(out, st.id(dname[r]))
        _varint(out, int(round(length[r] * 10)))
        if per_request:
            for c in slot_cost(r):
                _varint(out, 0 if not np.isfinite(c) else int(round(c * 600)) + 1)
        else:
            mf, mr = slot_cost(r)
            _varint(out, int(round(mf * 600)) if np.isfinite(mf) else 0)
            _varint(out, int(round(mr * 600)) if np.isfinite(mr) else 0)
            out.append(int(round(score[r] * 25)) & 0xFF)
            out.append(int(round(router.unpaved_frac[r] * 255)) & 0xFF)
        g = shapely.get_coordinates(router._geom[r])
        mid = g[1:-1]
        _varint(out, len(mid))
        pa, pb = int(round(g[0][1] * 1e6)), int(round(g[0][0] * 1e6))
        for x, y in mid:
            a, b = int(round(y * 1e6)), int(round(x * 1e6))
            _varint(out, _zz(a - pa)); _varint(out, _zz(b - pb))
            pa, pb = a, b

    # Departure stubs: the bearing of every road leaving a corridor node to the
    # outside, which `fork_side` needs to see.
    stubs = stubs or []
    _varint(out, len(stubs))
    for node, bearing in stubs:
        _varint(out, remap[local[node]]); out.append(int(bearing / 360 * 256) & 0xFF)

    restrictions = restrictions or []
    _varint(out, len(restrictions))
    for a, b in restrictions:
        _varint(out, a); _varint(out, b)

    blob = bytes(out) + st.blob()
    return blob, len(st.strings)


def gz(b: bytes) -> int:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0) as fh:
        fh.write(b)
    return len(buf.getvalue())


# ---------------------------------------------------------------- the graph

class Graph:
    """The router's search graph at one (pref, weights) setting."""

    def __init__(self, router, pref, day):
        self.r = router
        self.pref = pref
        self.scores = router._edge_scores({})
        self.w = router._weights(pref, self.scores, 1.0, day)       # per slot
        pair_w = np.full(router.n_pairs, np.inf)
        np.minimum.at(pair_w, router.slot_pair, self.w)
        self.pair_w = pair_w
        self.full = csr_matrix((pair_w, (router.u_tail, router.u_head)),
                               shape=(router.n, router.n))
        # Pure length, for "how far is the route by road".
        pair_km = np.full(router.n_pairs, np.inf)
        slot_km = router.km[router.eidx]
        closed = ~np.isfinite(self.w)
        np.minimum.at(pair_km, router.slot_pair, np.where(closed, np.inf, slot_km))
        self.full_km = csr_matrix((pair_km, (router.u_tail, router.u_head)),
                                  shape=(router.n, router.n))
        self.full_T = self.full.T.tocsr()
        real = router.real_node
        self.real = real
        # Per undirected edge, the cheapest slot each way, for encoding.
        self.cost_fwd = np.full(len(router.edges), np.inf)
        self.cost_rev = np.full(len(router.edges), np.inf)
        f = router.flip
        np.minimum.at(self.cost_fwd, router.eidx[~f], self.w[~f])
        np.minimum.at(self.cost_rev, router.eidx[f], self.w[f])
        mins = router.d_minutes
        self.min_fwd = np.full(len(router.edges), np.inf)
        self.min_rev = np.full(len(router.edges), np.inf)
        np.minimum.at(self.min_fwd, router.eidx[~f], mins[~f])
        np.minimum.at(self.min_rev, router.eidx[f], mins[f])

    def slot_cost(self, r):
        return self.cost_fwd[r], self.cost_rev[r]

    def raw_cost(self, r):
        return self.min_fwd[r], self.min_rev[r]


def route_togo(router, graph, result):
    """Cost still to drive from each node of a route to its end, by the weights
    the route was chosen with — the terminal cost of rejoining it there."""
    rows = result.edges.index.to_numpy()
    strength = max(0.0, min(1.0, graph.pref)) ** R.PREF_CURVE
    km = router.km[rows]
    per_edge = (np.asarray(result.edge_minutes)
                + strength * R.BETA * km * (1.0 - np.asarray(result.scores) / 10.0)
                + R.UNPAVED_AVOID_MIN_PER_KM * km * router.unpaved_frac[rows])
    togo = np.r_[np.cumsum(per_edge[::-1])[::-1], 0.0]
    return np.asarray(result.nodes, dtype=np.int64), togo


def corridor_nodes(router, line_m, width):
    """Node indices (search graph, copies included) within `width` of a line.

    The index over every junction is built once per router: built per call, it
    is most of what a corridor appears to cost to cut."""
    if not hasattr(router, "_node_tree"):
        router._node_tree = shapely.STRtree(
            shapely.points(np.column_stack([router._nx, router._ny])))
    hit = router._node_tree.query(line_m, predicate="dwithin", distance=width)
    inside = np.zeros(router.n, bool)
    real_in = np.zeros(len(router._nx), bool)
    real_in[hit] = True
    inside[:] = real_in[router.real_node]
    return inside


def subgraph(graph, inside):
    r = graph.r
    keep = inside[r.u_tail] & inside[r.u_head] & np.isfinite(graph.pair_w)
    idx = np.where(inside)[0]
    local = np.full(r.n, -1, np.int64)
    local[idx] = np.arange(len(idx))
    g = csr_matrix((graph.pair_w[keep], (local[r.u_tail[keep]], local[r.u_head[keep]])),
                   shape=(len(idx), len(idx)))
    return g, idx, local


def best_rejoin(dist_real, route_nodes, togo, start_pos, end_pos=None):
    """Cheapest total: reach a route node in [start_pos, end_pos], then follow.

    `end_pos` is a loop's far point while the car has not reached it. Without
    it the cheapest "rejoin" before the far point is usually a hop onto the
    return leg, which is skipping the loop, not getting back onto it — the
    same reason the app's own reroutes go via the far point."""
    end = len(route_nodes) - 1 if end_pos is None else end_pos
    ahead = np.arange(start_pos, end + 1)
    total = dist_real[route_nodes[ahead]] + togo[ahead]
    k = int(np.argmin(total))
    return float(total[k]), int(ahead[k])


def to_real(router, dist):
    """Per real node, the cheapest of it and its turn-restriction copies."""
    n_real = len(router._nx)
    out = np.full(n_real, np.inf)
    np.minimum.at(out, router.real_node, dist)
    return out


# ---------------------------------------------------------------- deviations

def straight_walk(router, start_real, first_slot, metres):
    """Follow the road a driver kept to after missing a turn: from `first_slot`,
    at each junction the outgoing road nearest straight on."""
    slot, walked, node = first_slot, 0.0, start_real
    seen = set()
    lengths = router._lengths
    for _ in range(200):
        r = router.eidx[slot]
        walked += lengths[r]
        node = int(router.real_node[router.head[slot]])
        if walked >= metres or node in seen:
            break
        seen.add(node)
        arrive = R._bearing_in(router.slot_coords(slot).tolist())
        best, best_turn = None, 1e9
        for s2 in router.outgoing_slots(node):
            if router.eidx[s2] == r:
                continue
            c = router.slot_coords(s2)
            if len(c) < 2:
                continue
            turn = abs(R._turn_delta(arrive, R._bearing_out(c.tolist())))
            if turn < best_turn:
                best, best_turn = s2, turn
        if best is None or best_turn > 100:
            break
        slot = best
    return node, walked


def _turn_junctions(router, result, route_nodes):
    """Route positions of the turn-like maneuvers: the junctions a driver can miss."""
    turn_like = {"turn", "fork", "exit", "roundabout", "merge"}
    nx, ny = router._nx, router._ny
    out = []
    for st in result.steps()[1:-1]:
        if st.get("type") not in turn_like:
            continue
        x, y = R._TO_M.transform(st["lon"], st["lat"])
        d = np.hypot(nx[route_nodes] - x, ny[route_nodes] - y)
        i = int(np.argmin(d))
        if d[i] <= 30:
            out.append(i)
    return out


def _side_slots(router, route_nodes, route_set, i):
    """Roads leaving the junction at route position `i` that the route does not take."""
    junction = int(route_nodes[i])
    nxt = int(route_nodes[i + 1]) if i + 1 < len(route_nodes) else -1
    return [s for s in router.outgoing_slots(junction)
            if int(router.real_node[router.head[s]]) != nxt
            and int(router.real_node[router.head[s]]) not in route_set]


def contingency_points(router, result, route_nodes):
    """(turns, roads not taken at them): what T3b would have to precompute."""
    route_set = set(int(x) for x in route_nodes)
    turns = _turn_junctions(router, result, route_nodes)
    return len(turns), sum(len(_side_slots(router, route_nodes, route_set, i)) for i in turns)


def deviations(router, result, route_nodes, line_m, rng):
    """Missed-turn start points: (route position, node off the route, metres)."""
    route_set = set(int(x) for x in route_nodes)
    nx, ny = router._nx, router._ny
    cand = _turn_junctions(router, result, route_nodes)
    rng.shuffle(cand)
    out = []
    for i in cand[:MAX_TURNS_PER_ROUTE]:
        junction = int(route_nodes[i])
        for s in _side_slots(router, route_nodes, route_set, i):
            for D in DEVIATIONS:
                node, walked = straight_walk(router, junction, s, D)
                off = shapely.distance(shapely.Point(nx[node], ny[node]), line_m)
                if off < 60:
                    continue      # the road came back to the route
                out.append((i, node, D, walked, float(off)))
    return out


# ---------------------------------------------------------------- main

def load_pairs(n_routes, rng):
    od = json.load(open(ROOT / "tools/e2e_od_pairs.json"))
    routes = [p for p in od["pairs"] if p["category"] not in ("loop", "island")
              and p["expect"] == "route"]
    loops = [p for p in od["pairs"] if p["category"] == "loop"]
    by_cat = {}
    for p in routes:
        by_cat.setdefault(p["category"], []).append(p)
    picked = []
    while len(picked) < n_routes and any(by_cat.values()):
        for cat in sorted(by_cat):
            if by_cat[cat] and len(picked) < n_routes:
                picked.append(by_cat[cat].pop(int(rng.integers(len(by_cat[cat])))))
    return picked, loops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--routes", type=int, default=20)
    ap.add_argument("--loops", type=int, default=8)
    ap.add_argument("--long-loops", default="loop-002,loop-011,loop-015,loop-019")
    ap.add_argument("--out", default="corridor-out")
    ap.add_argument("--export", action="store_true",
                    help="write two corridor graphs for the Swift benchmark")
    ap.add_argument("--census", type=int, default=0,
                    help="also write lines.ndjson: this many census pairs at pref "
                         "0, 0.5 and 1.0, for tools/coverage_on_routes.py")
    ap.add_argument("--skip-corridors", action="store_true")
    ap.add_argument("--export-full", action="store_true",
                    help="only write bench-full.bin, the whole search graph, for "
                         "timing a whole-region search (T2) with tools/bench")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    data = os.environ.get("SUNDAYDRIVE_DATA", str(ROOT / "data/processed-ne"))

    t0 = time.perf_counter()
    router = R.Router(data)
    router._lengths = router.edges["length_m"].to_numpy()
    assert (router.edges.index.to_numpy() == np.arange(len(router.edges))).all()
    planner = LoopPlanner(router)
    # Turn restrictions, as the banned (edge in, edge out) pairs the router
    # splits junctions for; a corridor carries the ones wholly inside it.
    r_from = router.restrictions["from_edge"].to_numpy()
    r_to = router.restrictions["to_edge"].to_numpy()
    day = R.region_today()
    print(f"router loaded in {time.perf_counter() - t0:.1f} s, n={router.n}", flush=True)
    rng = np.random.default_rng(20261005)
    pairs, loops = load_pairs(a.routes, rng)

    graphs = {}

    def graph(pref):
        if pref not in graphs:
            graphs[pref] = Graph(router, pref, day)
        return graphs[pref]

    if a.export_full:
        # T2's search is the whole graph. The bench runs every search to
        # exhaustion, so the target is immaterial; one route's end stands in.
        t, _ = router.snap_destination(*pairs[0]["destination"])
        export(out / "bench-full.bin", graph(1.0), np.ones(router.n, bool),
               np.array([t]), np.array([0.0]), router, "the whole graph")
        return

    jobs = []
    for p in pairs:
        for pref in (0.5, 1.0):
            jobs.append(("route", p, pref, None))
    for p in loops[:a.loops]:
        jobs.append(("loop", p, 1.0, p.get("loop_km", 40)))
    by_id = {p["id"]: p for p in loops}
    for lid in a.long_loops.split(","):
        if lid in by_id:
            for km in (150, 400):
                jobs.append(("loop", by_id[lid], 1.0, km))

    lines_f = open(out / "lines.ndjson", "w")
    if a.census:
        census_lines(router, day, a.census, rng, lines_f)
    if a.skip_corridors:
        jobs = [j for j in jobs if j[0] == "loop"]

    rec_path = out / "corridors.ndjson"
    dev_path = out / "deviations.ndjson"
    rec_f, dev_f = open(rec_path, "w"), open(dev_path, "w")
    exported = set()
    for kind, p, pref, km in jobs:
        g = graph(pref)
        t_req = time.perf_counter()
        if kind == "route":
            s, _ = router.snap(*p["origin"])
            t, _ = router.snap_destination(*p["destination"])
            if s == t:
                continue
            result = router.route(s, t, pref, {}, avoid_unpaved=1.0, on=day)
            dst = t
            label = f"{p['id']}@{pref}"
        else:
            s, _ = router.snap(*p["origin"])
            loop = planner.plan(s, km, pref, {}, avoid_unpaved=1.0, on=day)
            if loop is None:
                print("no loop", p["id"], km, flush=True)
                continue
            result = loop.route
            dst = s
            label = f"{p['id']}:{km}km"
        if result is None:
            continue
        route_ms = (time.perf_counter() - t_req) * 1000
        gj = result.geojson()
        if kind == "loop":
            lines_f.write(json.dumps({"group": "loop", "key": label, "km": result.km,
                                      "coords": gj["geometry"]["coordinates"]}) + "\n")
            lines_f.flush()
            if a.skip_corridors:
                continue
        route_json = json.dumps(gj, separators=(",", ":")).encode()
        line = shapely.LineString(np.column_stack(
            R._TO_M.transform(*np.asarray(gj["geometry"]["coordinates"]).T)))
        route_nodes, togo = route_togo(router, g, result)
        turns, side_roads = contingency_points(router, result, route_nodes)
        rec = {"key": label, "kind": kind, "state": p["state"], "category": p["category"],
               "pref": pref, "km": round(result.km, 1), "steps": len(gj["properties"]["steps"]),
               "turns": turns, "side_roads": side_roads,
               "coords": len(gj["geometry"]["coordinates"]), "route_ms": round(route_ms),
               "route_json": len(route_json), "route_json_gz": gz(route_json),
               "widths": {}}

        # T1b: the reverse search a drive start would cost, from the end (and
        # from the far point of a loop), and its tree.
        t5 = time.perf_counter()
        targets = [dst] + ([loop.turnaround_idx] if kind == "loop" else [])
        trees = [dijkstra(g.full_T, directed=True, indices=x, return_predecessors=True)
                 for x in targets]
        rec["reverse_ms"] = round((time.perf_counter() - t5) * 1000)
        insides = {}
        for W in WIDTHS:
            t1 = time.perf_counter()
            inside = corridor_nodes(router, line, W)
            real_in = np.zeros(len(router._nx), bool)
            real_in[router.real_node[inside]] = True
            eu, ev = router.edge_u_idx, router.edge_v_idx
            both = np.where(real_in[eu] & real_in[ev])[0]
            one = np.where(real_in[eu] ^ real_in[ev])[0]
            stubs = []
            for r in one:
                u_in = real_in[eu[r]]
                node = int(eu[r] if u_in else ev[r])
                c = shapely.get_coordinates(router._geom[r])
                c = c if u_in else c[::-1]
                if len(c) >= 2:
                    stubs.append((node, R._bearing_out(c.tolist()) % 360))
            nodes = set(int(x) for x in np.where(real_in)[0])
            local_edge = np.full(len(router.edges), -1, np.int64)
            local_edge[both] = np.arange(len(both))
            keep = (local_edge[r_from] >= 0) & (local_edge[r_to] >= 0)
            restr = list(zip(local_edge[r_from[keep]].tolist(), local_edge[r_to[keep]].tolist()))
            blob, nstr = encode(router, both, nodes, per_request=True,
                                slot_cost=g.slot_cost, stubs=stubs, restrictions=restr)
            ms = (time.perf_counter() - t1) * 1000
            vertices = int(sum(len(shapely.get_coordinates(router._geom[r])) for r in both))
            # The tree's share of the corridor: next hop and cost for every
            # corridor node, per target.
            tree_bytes = bytearray()
            inside_idx = np.where(inside)[0]
            for dist_t, pred_t in trees:
                prev = 0
                for v in inside_idx:
                    p = int(pred_t[v])
                    _varint(tree_bytes, _zz(p - prev) if p >= 0 else 0); prev = max(p, 0)
                    c = dist_t[v]
                    _varint(tree_bytes, int(round(c * 600)) + 1 if np.isfinite(c) else 0)
            rec.setdefault("tree", {})[W] = {"bytes": len(tree_bytes), "gz": gz(bytes(tree_bytes))}
            rec["widths"][W] = {"nodes": len(nodes), "edges": int(len(both)),
                                "stubs": len(stubs), "strings": nstr,
                                "restrictions": len(restr),
                                "road_km": round(float(router.km[both].sum()), 1),
                                "vertices": vertices,
                                "bytes": len(blob), "gz": gz(blob), "ms": round(ms)}
            insides[W] = inside
            # One long route and one 400 km loop, the largest corridors a
            # phone would search.
            tag = ("route" if kind == "route" and result.km > 100
                   else "loop400" if kind == "loop" and km == 400 else None)
            if a.export and W == 500 and tag and tag not in exported:
                export(out / f"bench-{tag}.bin", g, inside, route_nodes, togo,
                       router, label)
                exported.add(tag)
        rec_f.write(json.dumps(rec) + "\n"); rec_f.flush()
        print(label, f"{result.km:.0f} km",
              {W: (v["edges"], v["gz"] // 1024) for W, v in rec["widths"].items()},
              f"route {rec['route_json_gz'] // 1024} KB gz", flush=True)

        # Coverage of missed turns, by corridor width.
        devs = deviations(router, result, route_nodes, line, rng)
        far = None
        if kind == "loop":
            at = np.where(route_nodes == int(router.real_node[loop.turnaround_idx]))[0]
            far = int(at[0]) if len(at) else None
        for pos, node, D, walked, off in devs:
            end = far if far is not None and pos < far else None
            t2 = time.perf_counter()
            dist = dijkstra(g.full, directed=True, indices=node)
            full_ms = (time.perf_counter() - t2) * 1000
            dreal = to_real(router, dist)
            full_rejoin, _ = best_rejoin(dreal, route_nodes, togo, pos, end)
            to_dst = float(dreal[dst]) if kind == "route" else float("nan")
            dkm = to_real(router, dijkstra(g.full_km, directed=True, indices=node))
            ahead = route_nodes[pos:(end + 1 if end is not None else None)]
            road_km = float(dkm[ahead].min())
            row = {"key": label, "kind": kind, "D": D, "walked": round(walked),
                   "off_m": round(off), "full_rejoin": full_rejoin, "to_dst": to_dst,
                   "road_km_to_route": road_km, "full_ms": round(full_ms), "by_width": {}}
            for W in WIDTHS:
                inside = insides[W]
                if not inside[node]:
                    row["by_width"][W] = {"inside": False}
                    continue
                sub, idx, local = subgraph(g, inside)
                t3 = time.perf_counter()
                d2 = dijkstra(sub, directed=True, indices=int(local[node]))
                sub_ms = (time.perf_counter() - t3) * 1000
                full_d = np.full(router.n, np.inf)
                full_d[idx] = d2
                cr, _ = best_rejoin(to_real(router, full_d), route_nodes, togo, pos, end)
                row["by_width"][W] = {"inside": True, "rejoin": cr,
                                      "nodes": len(idx), "ms": round(sub_ms, 1)}
            dev_f.write(json.dumps(row) + "\n"); dev_f.flush()
    rec_f.close(); dev_f.close()

    # T2: the whole graph, encoded for any pref.
    g = graph(0.5)
    t4 = time.perf_counter()
    all_rows = np.arange(len(router.edges))
    blob, nstr = encode(router, all_rows, set(range(len(router._nx))),
                        per_request=False, slot_cost=g.raw_cost,
                        restrictions=list(zip(r_from.tolist(), r_to.tolist())))
    t2 = {"edges": len(all_rows), "nodes": len(router._nx), "strings": nstr,
          "bytes": len(blob), "gz": gz(blob), "ms": round((time.perf_counter() - t4) * 1000),
          "road_km": round(float(router.km.sum()), 1)}
    (out / "t2.json").write_text(json.dumps(t2))
    print("T2 whole graph:", t2, flush=True)


def census_lines(router, day, n, rng, fh):
    """Route geometries for `n` census pairs, stratified by distance band."""
    import pandas as pd
    pairs = pd.read_csv(ROOT / "docs/route-census/census-pairs.csv")
    pairs = pairs[pairs["status"] == "ok"]
    per_band = max(1, n // pairs["band"].nunique())
    picked = pairs.groupby("band", group_keys=False).apply(
        lambda g: g.sample(min(per_band, len(g)), random_state=20261005))
    t0 = time.perf_counter()
    for k, row in enumerate(picked.itertuples()):
        s, _ = router.snap(row.src_lat, row.src_lon)
        t, _ = router.snap_destination(row.dst_lat, row.dst_lon)
        if s == t:
            continue
        for group, pref in (("fastest", 0.0), ("default", 0.5), ("scenic", 1.0)):
            res = router.route(s, t, pref, {}, avoid_unpaved=1.0, on=day)
            if res is None:
                continue
            fh.write(json.dumps({"group": group, "key": row.pair_id, "band": row.band,
                                 "km": res.km,
                                 "coords": res.geojson()["geometry"]["coordinates"]}) + "\n")
        if k % 50 == 0:
            fh.flush()
            print(f"census {k}/{len(picked)} in {time.perf_counter() - t0:.0f} s", flush=True)
    fh.flush()


def export(path, graph, inside, route_nodes, togo, router, label):
    """A corridor's search graph in a flat binary, for tools/bench."""
    sub, idx, local = subgraph(graph, inside)
    sub = sub.tocsr()
    ahead = [int(local[n]) for n in route_nodes if inside[n]]
    tg = [float(togo[i]) for i, n in enumerate(route_nodes) if inside[n]]
    srcs = np.linspace(0, len(idx) - 1, 32).astype(np.int64)
    with open(path, "wb") as fh:
        np.array([len(idx), sub.nnz, len(ahead), len(srcs)], np.int64).tofile(fh)
        sub.indptr.astype(np.int64).tofile(fh)
        sub.indices.astype(np.int32).tofile(fh)
        sub.data.astype(np.float32).tofile(fh)
        np.array(ahead, np.int32).tofile(fh)
        np.array(tg, np.float32).tofile(fh)
        srcs.astype(np.int32).tofile(fh)
    print("exported", path, label, len(idx), "nodes", sub.nnz, "arcs", flush=True)


if __name__ == "__main__":
    main()
