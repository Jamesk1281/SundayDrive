"""Measurement harness for docs/side-loops-verdict.md. Nothing here is wired
into the router.

The question: should a scenic route ever leave the main road for a minor road
that rejoins it further on (a "side loop"), trading minutes for scenery? The
user's example is Washburn Road, Barre, MA. Each part is a subcommand:

  washburn  The example's own geometry: the roads at each of its junctions, and
            what the main roads between its two ends cost and score. (It ends
            on Pleasant Street, not West Street, and between its own ends it is
            a shortcut. As a side loop off a real route it is found by `census`
            on drive 122558, which prints it.)

  census    Every side loop along a sample of real scenic routes. A side loop
            is the cheapest path from route node A to a later route node B
            whose interior touches neither a route node nor a route edge, so it
            is edge-disjoint from the route and simple by construction, and B
            is always downstream of A. Reports count per 100 km, extra minutes,
            km on roads scoring >= 7 gained, and the share on unreviewed TIGER
            or untagged-surface ways.

  marks     Whether the score undervalues minor roads, from the driver's
            nice/dull marks (all 151: 79 from August, 72 from 2026-10-06),
            split by road class, with bootstrap error bars.

  plan      The settling drive: named minor roads near Washburn Road that the
            score calls dull and good, on reviewed ways.

  summary   Reprints the census tables from the CSVs `census` wrote.

The scenery measure throughout is **km on edges scoring >= 7** (`km7`), never
mean_score: mean_score is length-weighted, so a longer loop moves it either way
regardless of what was gained (docs/scenery-cap-options.md). `scen` (sum of
km * score/10) is carried alongside for comparison with that document.

Usage:
    .venv/bin/python pipeline/side_loop_experiment.py <processed_dir> <part>...
        [--traces DIR] [--pbf FILE] [--cache DIR] [--pairs N]

`<processed_dir>` is data/processed-ne, and `--traces` the gitignored traces/
directory; both live only in the main checkout. `--cache` is where the way-tag
scan of the PBF is kept (under a minute to build, seconds to reread).
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

SCENIC = 7.0                     # the "scenic" bar, as in scenery-cap-options.md
ON = date(2026, 10, 6)           # the drives' day, for seasonal closures
APP_WEIGHTS = {"town": 0.0}      # what the app sends unless the driver changes it

# Road classes, for the minor-road hypothesis. "Major" is the state network a
# driver would call the main road; the rest is what the user means by a side
# street.
MAJOR = {"motorway", "motorway_link", "trunk", "trunk_link", "primary",
         "primary_link", "secondary", "secondary_link"}

# Census limits. A loop longer than this, or costing more extra time, is a
# different route rather than a side loop off this one.
CORRIDOR_M = 5000.0              # nodes this close to the route are searched
MAX_LOOP_KM = 20.0
MAX_EXTRA_MIN = 20.0
MIN_SPAN_KM = 0.3                # shorter than this is a junction triangle
OVERLAP = 0.5                    # a loop sharing more km than this with a kept
                                 # one is the same loop with different ends
BATCH = 16
CLEAR = (6.5, 7.5)               # bars for the noise-proof gain, see candidates()


# --- way tags from the PBF ----------------------------------------------------

def way_tags(pbf, cache):
    """way_id -> highway, tiger:reviewed, surface, access, name. Cached."""
    path = Path(cache) / "side_loop_way_tags.parquet"
    if path.exists():
        return pd.read_parquet(path)
    import osmium
    from common import DRIVABLE

    rows = []

    class H(osmium.SimpleHandler):
        def way(self, w):
            hw = w.tags.get("highway")
            if hw in DRIVABLE:
                rows.append((w.id, hw, w.tags.get("tiger:reviewed", ""),
                             w.tags.get("surface", ""), w.tags.get("access", ""),
                             w.tags.get("name", "")))

    t0 = time.time()
    H().apply_file(str(pbf))
    out = pd.DataFrame(rows, columns=["way_id", "highway", "tiger_reviewed",
                                      "surface", "access", "name"])
    Path(cache).mkdir(parents=True, exist_ok=True)
    out.to_parquet(path)
    print(f"# scanned {len(out):,} drivable ways in {time.time()-t0:.0f}s -> {path}")
    return out


class EdgeTags:
    """Per graph edge: is the way it came from unreviewed TIGER, untagged surface.

    The graph keeps no way id, so each edge is matched to the nearest way in
    roads.parquet at the edge's midpoint, preferring a way of the same name.
    Only the edges asked about are matched, lazily.
    """

    def __init__(self, processed_dir, tags, edges):
        import geopandas as gpd
        from shapely import STRtree
        from common import CRS_METERS

        roads = gpd.read_parquet(Path(processed_dir) / "roads.parquet",
                                 columns=["way_id", "name", "geometry"])
        roads = roads.merge(tags[["way_id", "tiger_reviewed", "surface"]],
                            on="way_id", how="left")
        self.roads = roads.to_crs(CRS_METERS).reset_index(drop=True)
        self.tree = STRtree(self.roads.geometry.values)
        self.edges = edges
        self.mid = edges.geometry.to_crs(CRS_METERS).values
        self.memo = {}

    def __call__(self, e):
        if e in self.memo:
            return self.memo[e]
        import shapely
        p = shapely.line_interpolate_point(self.mid[e], 0.5, normalized=True)
        near = self.tree.query(p.buffer(15.0))
        if len(near) == 0:
            near = [self.tree.nearest(p)]
        name = self.edges["name"].iat[e] or ""
        cand = self.roads.iloc[list(near)]
        same = cand[cand["name"].fillna("") == name]
        cand = same if len(same) else cand
        d = cand.geometry.distance(p)
        r = cand.loc[d.idxmin()]
        out = (r["tiger_reviewed"] == "no",
               not isinstance(r["surface"], str) or r["surface"] == "",
               int(r["way_id"]))
        self.memo[e] = out
        return out


# --- shared measures ----------------------------------------------------------

def measure_edges(rt, edge_ids, minutes, scores):
    L = rt.km[edge_ids]
    s = scores[edge_ids]
    return dict(km=float(L.sum()), minutes=float(np.sum(minutes)),
                km7=float(L[s >= SCENIC].sum()), scen=float((L * s / 10).sum()),
                mean=float((L * s).sum() / max(L.sum(), 1e-9)))


def strength(pref):
    import router as R
    return max(0.0, min(1.0, pref)) ** R.PREF_CURVE * R.BETA


# --- part 1: Washburn Road ----------------------------------------------------

WASHBURN = [183219, 183216, 183217]     # west to east, from the brief


def washburn(rt, args):
    import router as R
    e = rt.edges
    print("=" * 96 + "\nWASHBURN ROAD, BARRE MA\n" + "=" * 96)
    for name, w in (("neutral", {}), ("app (town=0)", APP_WEIGHTS)):
        sc = rt._edge_scores(w)
        print(f"  scores, {name}: " + ", ".join(
            f"{i}: {e['length_m'].iat[i]:.0f} m {sc[i]:.2f}" for i in WASHBURN))

    print("\n  every junction along it (osm node: roads meeting there):")
    chain = [e["u"].iat[WASHBURN[0]], e["v"].iat[WASHBURN[0]],
             e["v"].iat[WASHBURN[1]], e["v"].iat[WASHBURN[2]]]
    for n in chain:
        inc = e[(e["u"] == n) | (e["v"] == n)]
        print(f"    {n}: " + "; ".join(f"[{i}] {r['name'] or '(unnamed)'} "
                                       f"{r['highway']} {r['length_m']:.0f} m"
                                       for i, r in inc.iterrows()))
    west, east = rt.idx[chain[0]], rt.idx[chain[-1]]

    loop_set = set(WASHBURN)
    for pref in (0.5, 0.773, 1.0):
        sc = rt._edge_scores(APP_WEIGHTS)
        k = strength(pref)
        loop = measure_edges(rt, np.array(WASHBURN),
                             [e["minutes"].iat[i] for i in WASHBURN], sc)
        # the router's own minutes for the loop, either direction
        fwd = _directed_minutes(rt, chain)
        loop["minutes"] = fwd
        loop_cost = fwd + k * sum(rt.km[i] * (1 - sc[i] / 10) for i in WASHBURN)
        # the main road between the same two junctions: route with Washburn shut
        w = rt._weights(pref, sc, on=ON).copy()
        shut = np.isin(rt.eidx, list(loop_set))
        w[shut] = np.inf
        res = _route_with(rt, west, east, w, sc)
        alt = measure_edges(rt, res.edges.index.to_numpy(), res.edge_minutes, sc)
        alt_cost = float(np.sum(w[_slots_of(rt, res)]))
        names = pd.Series(res.edges["name"].fillna("")).loc[lambda s: s != ""]
        print(f"\n  pref={pref}:  (k = {k:.2f} min per unscenic km)")
        print(f"    Washburn Rd      {loop['km']:5.2f} km {loop['minutes']:5.2f} min "
              f"mean {loop['mean']:.2f} km7 {loop['km7']:.2f} scen {loop['scen']:.2f}"
              f"  cost {loop_cost:6.2f}")
        print(f"    main-road alt    {alt['km']:5.2f} km {alt['minutes']:5.2f} min "
              f"mean {alt['mean']:.2f} km7 {alt['km7']:.2f} scen {alt['scen']:.2f}"
              f"  cost {alt_cost:6.2f}   via {' / '.join(dict.fromkeys(names))}")
        # The uniform score Washburn would need to cost no more than the main
        # road: fwd + k*km*(1 - s/10) <= alt_cost.
        need = 10 * (1 - (alt_cost - fwd) / (k * loop["km"])) if k > 0 else np.inf
        print(f"    extra {loop['minutes']-alt['minutes']:+.2f} min for "
              f"{loop['km7']-alt['km7']:+.2f} km7; to be chosen Washburn Rd would "
              f"need to score {need:.1f} everywhere (today {loop['mean']:.2f}; max 10)")


def _directed_minutes(rt, chain):
    tot = 0.0
    for a, b in zip(chain, chain[1:]):
        ai, bi = rt.idx[a], rt.idx[b]
        m = (rt.real_node[rt.tail] == ai) & (rt.real_node[rt.head] == bi)
        tot += float(rt.d_minutes[m].min())
    return tot


def _route_with(rt, src, dst, w, scores):
    pair_w = np.full(rt.n_pairs, np.inf)
    np.minimum.at(pair_w, rt.slot_pair, w)
    targets = rt.node_copies.get(dst, np.array([dst]))
    path = rt._dijkstra_path(src, targets, pair_w)
    return rt._collect(path, w, scores)


def _slots_of(rt, res):
    """The directed slots a RouteResult drove, recovered from its node path."""
    out = []
    nodes = res.nodes
    for (a, b), e in zip(zip(nodes, nodes[1:]), res.edges.index):
        m = np.flatnonzero((rt.eidx == e) & (rt.real_node[rt.tail] == a)
                           & (rt.real_node[rt.head] == b))
        out.append(int(m[0]))
    return np.array(out)


def chosen_slots(rt, path, w):
    """The directed slot each hop of a router node path used (as `_collect`)."""
    hops = np.asarray(path, dtype=np.int64)
    pairs = np.searchsorted(rt._pair_key, hops[:-1] * rt.n + hops[1:])
    return np.array([int(rt._pair_slots[rt._pair_start[p]:rt._pair_start[p + 1]]
                         [np.argmin(w[rt._pair_slots[rt._pair_start[p]:
                                                     rt._pair_start[p + 1]]])])
                     for p in pairs])


def plan(rt, src, dst, pref, weights):
    """Route src -> dst as the server would on the drives' day, as slots."""
    sc = rt._edge_scores(weights)
    w = rt._weights(pref, sc, on=ON)
    pair_w = np.full(rt.n_pairs, np.inf)
    np.minimum.at(pair_w, rt.slot_pair, w)
    targets = rt.node_copies.get(dst, np.array([dst]))
    path = rt._dijkstra_path(src, targets, pair_w)
    if path is None:
        return None
    slots = chosen_slots(rt, path, w)
    return dict(slots=slots, nodes=rt.real_node[np.asarray(path)], w=w, sc=sc,
                pref=pref)


def totals(rt, r, deltas=()):
    """Route measures, plus km7 with minor roads' scores raised by each delta."""
    e = rt.eidx[r["slots"]]
    m = measure_edges(rt, e, rt.d_minutes[r["slots"]], r["sc"])
    m["cost"] = float(r["w"][r["slots"]].sum())
    minor = ~rt.edges["highway"].isin(MAJOR).to_numpy()
    for d in deltas:
        s = r["sc"][e] + d * minor[e]
        m[f"km7+{d}"] = float(rt.km[e][s >= SCENIC].sum())
    return m


# --- part 2: census -----------------------------------------------------------

class Loops:
    """Every side loop off one planned route.

    Real-node space: turn-restriction and barrier copies are folded back onto
    their junction and closed slots dropped, so a loop's entry or exit turn can
    in rare cases be one the router would forbid. The route itself is the
    router's own, restrictions and all.
    """

    def __init__(self, rt, r, deltas):
        self.rt, self.r = rt, r
        sc, w = r["sc"], r["w"]
        n0 = len(rt.nodes)
        nodes = r["nodes"]
        route_e = set(rt.eidx[r["slots"]].tolist())
        # cumulative route measures at each node position
        e = rt.eidx[r["slots"]]
        L = rt.km[e]
        minor = ~rt.edges["highway"].isin(MAJOR).to_numpy()
        self.minor = minor
        self.deltas = deltas
        cum = lambda v: np.concatenate([[0.0], np.cumsum(v)])
        self.rc = dict(km=cum(L), minutes=cum(rt.d_minutes[r["slots"]]),
                       cost=cum(w[r["slots"]]), scen=cum(L * sc[e] / 10))
        for d in (0,) + tuple(deltas):
            self.rc[f"km7+{d}"] = cum(L * ((sc[e] + d * minor[e]) >= SCENIC))
        for b in CLEAR:
            self.rc[f"km{b}"] = cum(L * (sc[e] >= b))
        self.route_km = float(L.sum())

        # corridor
        from scipy.spatial import cKDTree
        rx, ry = rt._nx[nodes], rt._ny[nodes]
        tree = cKDTree(np.column_stack([rx, ry]))
        dd, _ = tree.query(np.column_stack([rt._nx[:n0], rt._ny[:n0]]),
                           distance_upper_bound=CORRIDOR_M)
        corr = np.flatnonzero(np.isfinite(dd))
        local = np.full(n0, -1, np.int64)
        local[corr] = np.arange(len(corr))
        R = np.unique(nodes)
        out_id = np.full(n0, -1, np.int64)
        out_id[R] = len(corr) + np.arange(len(R))
        N = len(corr) + len(R)

        T, H = rt.real_node[rt.tail], rt.real_node[rt.head]
        keep = (np.isfinite(w) & (local[T] >= 0) & (local[H] >= 0)
                & ~np.isin(rt.eidx, list(route_e)) & (T != H))
        s_idx = np.flatnonzero(keep)
        tl = np.where(out_id[T[s_idx]] >= 0, out_id[T[s_idx]], local[T[s_idx]])
        hl = local[H[s_idx]]
        # collapse parallels to the cheapest slot
        order = np.lexsort((w[s_idx], hl, tl))
        tl, hl, s_idx = tl[order], hl[order], s_idx[order]
        first = np.ones(len(tl), bool)
        first[1:] = (tl[1:] != tl[:-1]) | (hl[1:] != hl[:-1])
        tl, hl, s_idx = tl[first], hl[first], s_idx[first]
        self.key = tl * N + hl                      # sorted by construction
        self.slot = s_idx
        self.G = csr_matrix((w[s_idx], (tl, hl)), shape=(N, N))
        self.N, self.corr, self.local, self.out_id = N, corr, local, out_id
        ee = rt.eidx[s_idx]
        Le = rt.km[ee]
        self.val = dict(km=Le, minutes=rt.d_minutes[s_idx], scen=Le * sc[ee] / 10)
        for d in (0,) + tuple(deltas):
            self.val[f"km7+{d}"] = Le * ((sc[ee] + d * minor[ee]) >= SCENIC)
        for b in CLEAR:
            self.val[f"km{b}"] = Le * (sc[ee] >= b)
        # route positions of each route node, in-copy local id
        self.pos = {}
        for i, nd in enumerate(nodes):
            self.pos.setdefault(int(nd), []).append(i)
        self.R = R

    def candidates(self, limit):
        """All (A, B) side loops passing the census limits, as a DataFrame."""
        rt, nodes = self.rt, self.r["nodes"]
        srcs = [nd for nd in self.R if self.G.indptr[self.out_id[nd] + 1]
                > self.G.indptr[self.out_id[nd]]]
        Rin = self.local[self.R]
        rows = []
        for b0 in range(0, len(srcs), BATCH):
            batch = srcs[b0:b0 + BATCH]
            ids = self.out_id[batch]
            dist, pred = dijkstra(self.G, directed=True, indices=ids, limit=limit,
                                  return_predecessors=True)
            acc, first = self._accumulate(dist, pred, ids)
            for k, A in enumerate(batch):
                i = self.pos[int(A)][0]
                dB = dist[k, Rin]
                ok = np.flatnonzero(np.isfinite(dB))
                for q in ok:
                    B = int(self.R[q])
                    js = [j for j in self.pos[B] if j > i]
                    if not js:
                        continue
                    j = js[0]
                    v = Rin[q]
                    row = dict(A=int(A), B=B, i=i, j=j, first=int(first[k, v]),
                               last=int(pred[k, v]), cost=float(dB[q]))
                    for name, a in acc.items():
                        row["loop_" + name] = float(a[k, v])
                    for name, c in self.rc.items():
                        row["seg_" + name] = float(c[j] - c[i])
                    rows.append(row)
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df["extra_min"] = df.loop_minutes - df.seg_minutes
        for d in (0,) + tuple(self.deltas):
            df[f"gain7+{d}"] = df[f"loop_km7+{d}"] - df[f"seg_km7+{d}"]
        # A gain that survives a half-point of score noise either way: loop km
        # at >= 7.5 against segment km at >= 6.5. Kills 6.9 -> 7.1 flicker.
        df["clear"] = df[f"loop_km{CLEAR[1]}"] - df[f"seg_km{CLEAR[0]}"]
        df["gain_scen"] = df.loop_scen - df.seg_scen
        df = df[(df.seg_km >= MIN_SPAN_KM) & (df.loop_km <= MAX_LOOP_KM)
                & (df.extra_min > 0) & (df.extra_min <= MAX_EXTRA_MIN)]
        return df.reset_index(drop=True)

    def _accumulate(self, dist, pred, ids):
        """Sum each per-edge measure from the source down the predecessor tree.

        Pointer jumping: log2(depth) numpy passes instead of a Python walk.
        Also returns, per node, the first node after the source on its path.
        """
        b, N = dist.shape
        S = N                                     # sentinel column, value 0
        p = np.where(pred < 0, S, pred).astype(np.int64)
        reached = np.isfinite(dist) & (pred >= 0)
        tail = np.where(reached, pred, 0).astype(np.int64)
        head = np.broadcast_to(np.arange(N), (b, N))
        k = np.searchsorted(self.key, tail * self.N + head)
        k = np.minimum(k, len(self.key) - 1)
        hit = reached & (self.key[k] == tail * self.N + head)
        assert (hit == reached).all(), "predecessor hop missing from the graph"
        acc = {}
        for name, v in self.val.items():
            a = np.zeros((b, N + 1))
            a[:, :N] = np.where(reached, v[k], 0.0)
            acc[name] = a
        anc = np.concatenate([p, np.full((b, 1), S)], axis=1)
        rows = np.arange(b)[:, None]
        # first-hop ancestor: parent, except children of the source map to self
        src = np.asarray(ids)[:, None]
        fp = np.where(p == src, np.arange(N), p)
        fp = np.concatenate([fp, np.full((b, 1), S)], axis=1)
        while True:
            done = (anc == S).all()
            if done:
                break
            for name in acc:
                acc[name] = acc[name] + np.where(anc == S, 0.0,
                                                 acc[name][rows, anc])
            anc = anc[rows, anc]
        for _ in range(64):
            nxt = fp[rows, fp]
            if (nxt == fp).all():
                break
            fp = nxt
        return {n: a[:, :N] for n, a in acc.items()}, fp[:, :N]

    def path(self, A, B):
        """Undirected edge ids of the loop from route node A to route node B."""
        rt = self.rt
        src, dst = self.out_id[A], self.local[B]
        _, pred = dijkstra(self.G, directed=True, indices=src,
                           return_predecessors=True, limit=np.inf)
        hops, cur = [], dst
        while cur != src and cur >= 0:
            hops.append((pred[cur], cur))
            cur = pred[cur]
        hops.reverse()
        k = np.searchsorted(self.key, [t * self.N + h for t, h in hops])
        return rt.eidx[self.slot[k]]


DELTAS = (1, 2)                 # minor-road score offsets tried, from the marks
CATEGORIES = ("rural", "suburban", "coastal", "cross")


def od_pairs(rt, args):
    """(label, src, dst, pref, weights): the drives' scenic trips, then e2e pairs."""
    out = []
    seen = set()
    for f in sorted(Path(args.traces).glob("drive-2026-10-06-*.ndjson")):
        head = json.loads(Path(f).read_text().splitlines()[0])
        if head.get("t") != "drive" or not head.get("pref"):
            continue
        # One trip per destination and pref band: 192759 (pref 0.50) replans
        # 185940's trip (0.51); 104931 (0.50) and 122558 (0.77) share a
        # destination but not a setting, so both stay.
        key = (tuple(np.round(head["dest"], 2)), round(float(head["pref"]) * 10))
        if key in seen:
            continue
        seen.add(key)
        out.append((f"drive {f.stem[-6:]}", rt.snap(*head["from"])[0],
                    rt.snap_destination(*head["dest"])[0], float(head["pref"]),
                    head.get("weights") or APP_WEIGHTS))
    pairs = json.load(open(Path(__file__).resolve().parent.parent
                           / "tools" / "e2e_od_pairs.json"))["pairs"]
    per = {c: 0 for c in CATEGORIES}
    for p in pairs:
        c = p["category"]
        if c in per and per[c] < args.pairs and p.get("expect") == "route":
            per[c] += 1
            out.append((p["id"], rt.snap(*p["origin"])[0],
                        rt.snap_destination(*p["destination"])[0], 0.5, APP_WEIGHTS))
    return out


def census(rt, args):
    tags = way_tags(args.pbf, args.cache)
    et = EdgeTags(args.processed, tags, rt.edges)
    print("=" * 96 + "\nCENSUS OF SIDE LOOPS\n" + "=" * 96)
    allrows, routes = [], []
    for label, s, d, pref, weights in od_pairs(rt, args):
        t0 = time.time()
        r = plan(rt, s, d, pref, weights)
        if r is None or len(r["slots"]) < 3:
            print(f"  {label}: no route")
            continue
        base = totals(rt, r, DELTAS)
        fast = totals(rt, plan(rt, s, d, 0.0, weights), DELTAS)
        top = totals(rt, plan(rt, s, d, 1.0, weights), DELTAS)
        lp = Loops(rt, r, DELTAS)
        k = strength(pref)
        cand = lp.candidates(limit=30.0 + k * 15.0)
        # tags on the route itself, the baseline the loops are compared with
        re_ = rt.eidx[r["slots"]]
        rkm = rt.km[re_]
        rtag = np.array([et(int(e))[:2] for e in re_], bool)
        routes.append(dict(label=label, pref=pref, **{f"r_{k_}": v for k_, v in base.items()},
                           f_minutes=fast["minutes"], f_km7=fast["km7"],
                           t_minutes=top["minutes"], t_km7=top["km7"],
                           r_unrev=float(rkm[rtag[:, 0]].sum() / rkm.sum()),
                           r_nosurf=float(rkm[rtag[:, 1]].sum() / rkm.sum()),
                           r_both=float(rkm[rtag.all(1)].sum() / rkm.sum()),
                           r_minor=float(rkm[lp.minor[re_]].sum() / rkm.sum()),
                           n_cand=len(cand)))
        if cand.empty:
            print(f"  {label}: {base['km']:.0f} km, no side loops")
            continue
        # One loop per offshoot: the cheapest rejoin from each (A, first node),
        # then drop any loop sharing more than OVERLAP of its km with a kept one.
        per = cand.loc[cand.groupby(["A", "first"]).extra_min.idxmin()]
        per = per.sort_values("extra_min")
        kept, used = [], {}
        for _, row in per.iterrows():
            body = lp.path(int(row.A), int(row.B))
            km = rt.km[body]
            shared = sum(km[n] for n, e in enumerate(body) if e in used)
            if shared > OVERLAP * km.sum():
                continue
            for e in body:
                used[int(e)] = True
            tg = np.array([et(int(e))[:2] for e in body], bool)
            hw = rt.edges["highway"].to_numpy()[body]
            names = [n for n in rt.edges["name"].to_numpy()[body] if n]
            kept.append(dict(row.to_dict(), label=label, pref=pref,
                             unrev=float(km[tg[:, 0]].sum() / km.sum()),
                             nosurf=float(km[tg[:, 1]].sum() / km.sum()),
                             both=float(km[tg.all(1)].sum() / km.sum()),
                             minor=float(km[lp.minor[body]].sum() / km.sum()),
                             cls=pd.Series(hw).groupby(hw).size().idxmax(),
                             name=" / ".join(dict.fromkeys(names))[:60],
                             has_washburn=bool(set(body) & set(WASHBURN))))
        kd = pd.DataFrame(kept)
        allrows.append(kd)
        west = rt.idx[69504916]
        if west in set(r["nodes"].tolist()):
            hit = [i for i, x in enumerate(kd.has_washburn) if x]
            print(f"      route passes Washburn Rd's west junction; kept loops using it: "
                  + ("; ".join(f"+{kd.extra_min.iat[i]:.1f} min {kd.loop_km.iat[i]:.1f} km "
                               f"vs {kd.seg_km.iat[i]:.1f}, gain7 {kd['gain7+0'].iat[i]:+.2f}, "
                               f"{kd.name.iat[i]}" for i in hit) or "none"))
        print(f"  {label:14s} pref {pref:.2f} {base['km']:6.1f} km  "
              f"{len(cand):6d} candidates -> {len(kd):4d} loops "
              f"({100*len(kd)/base['km']:.0f}/100 km)  "
              f"best gain7/min {(cand['gain7+0']/cand.extra_min).max():.2f}  "
              f"[{time.time()-t0:.0f}s]")
        best = cand.assign(rate=cand["gain7+0"] / cand.extra_min.clip(lower=0.5))
        best = best.sort_values("rate", ascending=False).head(3)
        for _, b in best.iterrows():
            body = lp.path(int(b.A), int(b.B))
            names = [n for n in rt.edges["name"].to_numpy()[body] if n]
            print(f"      best: +{b.extra_min:4.1f} min  {b.loop_km:4.1f} km vs "
                  f"{b.seg_km:4.1f}  gain7 {b['gain7+0']:+.2f} km  "
                  f"{' / '.join(dict.fromkeys(names))[:70]}")
    loops = pd.concat(allrows, ignore_index=True) if allrows else pd.DataFrame()
    rts = pd.DataFrame(routes)
    out = Path(args.cache)
    loops.to_csv(out / "side_loops.csv", index=False)
    rts.to_csv(out / "side_loop_routes.csv", index=False)
    summarise(loops, rts)


def summarise(loops, rts):
    """The census tables. Rerunnable from the CSVs: `summary` subcommand."""
    print("\n" + "-" * 96)
    km = rts.r_km.sum()
    print(f"{len(rts)} routes, {km:.0f} km; {len(loops)} side loops = "
          f"{100*len(loops)/km:.1f} per 100 km")
    # What the slider already pays per extra minute, per route: the bar a loop
    # has to clear to be a better use of the driver's time than more slider.
    rts = rts.assign(rate=(rts.r_km7 - rts.f_km7) / (rts.r_minutes - rts.f_minutes),
                     rate_top=(rts.t_km7 - rts.r_km7) / (rts.t_minutes - rts.r_minutes))
    ok = rts.rate.replace([np.inf, -np.inf], np.nan)
    top = rts.rate_top.replace([np.inf, -np.inf], np.nan)
    print(f"slider exchange rate, fastest -> chosen pref: median {ok.median():.2f} "
          f"km7/min (p25 {ok.quantile(.25):.2f}, p75 {ok.quantile(.75):.2f}); "
          f"chosen pref -> 1: median {top.median():.2f}")
    print(f"route baseline: unreviewed TIGER {100*np.average(rts.r_unrev, weights=rts.r_km):.1f}% "
          f"of km, untagged surface {100*np.average(rts.r_nosurf, weights=rts.r_km):.1f}%, "
          f"both {100*np.average(rts.r_both, weights=rts.r_km):.1f}%, minor class "
          f"{100*np.average(rts.r_minor, weights=rts.r_km):.0f}%")
    if loops.empty:
        return
    bar = loops.label.map(rts.set_index("label").rate.clip(lower=0.1))
    loops = loops.assign(bar=bar, r7=loops["gain7+0"] / loops.extra_min,
                         rclear=loops.clear / loops.extra_min)
    for title, L in (("ALL LOOPS", loops), ("MINOR-ROAD LOOPS (>= 50% of km below "
                                            "secondary)", loops[loops.minor >= .5]),
                     ("OTHER LOOPS", loops[loops.minor < .5])):
        if L.empty:
            continue
        w = L.loop_km
        print(f"\n{title}: {len(L)} = {100*len(L)/km:.1f} per 100 km")
        print(f"  extra min p25/50/75 {L.extra_min.quantile(.25):.1f}/"
              f"{L.extra_min.median():.1f}/{L.extra_min.quantile(.75):.1f}; loop km median "
              f"{L.loop_km.median():.1f}; any km7 gain {100*(L['gain7+0'] > 0).mean():.0f}%, "
              f"clear gain {100*(L.clear > 0).mean():.0f}%")
        print(f"  loop km on unreviewed TIGER {100*np.average(L.unrev, weights=w):.0f}%, "
              f"untagged surface {100*np.average(L.nosurf, weights=w):.0f}%, both "
              f"{100*np.average(L.both, weights=w):.0f}%; loops mostly (>50%) unreviewed "
              f"{100*(L.unrev > .5).mean():.0f}%, mostly untagged "
              f"{100*(L.nosurf > .5).mean():.0f}%, mostly both {100*(L.both > .5).mean():.0f}%")
        print(f"  {'extra':>8} {'per100km':>9} {'gain7':>7} {'clear':>7} {'scen':>7}"
              f"  n(gain7>0) n(clear>0)  n(beats slider: km7 / clear)")
        for lo, hi in [(0, 2), (2, 5), (5, 10), (10, 20)]:
            b = L[(L.extra_min > lo) & (L.extra_min <= hi)]
            if b.empty:
                continue
            print(f"  {lo:>3}-{hi:<3}min {100*len(b)/km:9.1f} {b['gain7+0'].sum():7.1f} "
                  f"{b.clear.sum():7.1f} {b.gain_scen.sum():7.1f}  "
                  f"{(b['gain7+0'] > 0).sum():10d} {(b.clear > 0).sum():10d}  "
                  f"{(b.r7 >= b.bar).sum():5d} / {(b.rclear >= b.bar).sum():d}")
        for d in (0,) + DELTAS:
            r = L[f"gain7+{d}"] / L.extra_min
            print(f"  minor roads +{d} points: beat their route's slider rate "
                  f"{(r >= L.bar).sum():4d} ({100*(r >= L.bar).sum()/km:.1f}/100 km); "
                  f"gain7/min >= 0.5: {(r >= .5).sum():4d}; net gain7 if all taken "
                  f"{L[f'gain7+{d}'].sum():6.1f} km for {L.extra_min.sum():.0f} min")
        win = L[L.rclear >= L.bar]
        if len(win):
            ww = win.loop_km
            print(f"  the {len(win)} that clearly beat the slider: unreviewed TIGER "
                  f"{100*np.average(win.unrev, weights=ww):.0f}%, untagged surface "
                  f"{100*np.average(win.nosurf, weights=ww):.0f}%, minor "
                  f"{100*np.average(win.minor, weights=ww):.0f}%; extra min median "
                  f"{win.extra_min.median():.1f}")


def summary(rt, args):
    out = Path(args.cache)
    summarise(pd.read_csv(out / "side_loops.csv"), pd.read_csv(out / "side_loop_routes.csv"))


# --- part 3: marks by road class ----------------------------------------------

def mark_frame(rt, args):
    """Every usable nice/dull mark, scored as analyze_trace.py scores it.

    Scored twice: neutral weights (what analyze_trace.py and the brief use) and
    the app's town=0, which is what the drives were routed under.
    """
    import analyze_trace as A
    edges = rt.edges[["highway", "length_m", "minutes", "name", "geometry"]].copy()
    out = []
    for name, w in (("neutral", {}), ("app", APP_WEIGHTS)):
        edges["score"] = rt._edge_scores(w)
        index = A.road_index(edges)
        for f in sorted(Path(args.traces).glob("drive-*.ndjson")):
            recs = A.load(f)
            m = A.marks(recs)
            if m.empty:
                continue
            m = A.attach_scenery(m, A.segments(recs), edges, index)
            m["drive"] = f.stem[6:]
            m["weights"] = name
            out.append(m)
    df = pd.concat(out, ignore_index=True)
    return df[df.model_score.notna()]


def auc(nice, dull):
    import analyze_trace as A
    return A.separation(nice, dull)


def boot(df, stat, n=4000, seed=0, by="verdict"):
    """Percentile 95% interval, resampling marks within each verdict."""
    rng = np.random.default_rng(seed)
    groups = [g.index.to_numpy() for _, g in df.groupby(by)]
    vals = []
    for _ in range(n):
        idx = np.concatenate([rng.choice(g, len(g)) for g in groups])
        v = stat(df.loc[idx])
        if np.isfinite(v):
            vals.append(v)
    return np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan)


def boot_cluster(df, stat, n=4000, seed=1):
    """Percentile 95% interval, resampling whole roads (marks on one road on one
    day are not independent verdicts)."""
    rng = np.random.default_rng(seed)
    groups = {k: g.index.to_numpy() for k, g in df.groupby("cluster")}
    keys = list(groups)
    vals = []
    for _ in range(n):
        idx = np.concatenate([groups[keys[i]] for i in rng.integers(0, len(keys), len(keys))])
        sub = df.loc[idx]
        if sub.verdict.nunique() < 2 or sub.minor.nunique() < 2:
            continue
        v = stat(sub)
        if np.isfinite(v):
            vals.append(v)
    return np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan)


def logit(X, y, iters=50):
    """Plain IRLS logistic regression; returns coefficients."""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b))
        W = p * (1 - p) + 1e-9
        step = np.linalg.solve(X.T @ (X * W[:, None]) + 1e-6 * np.eye(len(b)),
                               X.T @ (y - p))
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


def offset(df):
    """Score points a minor road is worth over a major one at equal odds of nice."""
    X = np.column_stack([np.ones(len(df)), df.model_score, df.minor.astype(float)])
    b = logit(X, (df.verdict == "nice").astype(float).to_numpy())
    return b[2] / b[1] if b[1] > 0 else np.nan


def marks(rt, args):
    df = mark_frame(rt, args)
    df["minor"] = ~df.highway.isin(MAJOR)
    df["day"] = np.where(df.drive.str.startswith("2026-08"), "Aug", "Oct")
    df["cluster"] = df.drive.str[:10] + ":" + df.road.fillna("?")
    df.to_csv(Path(args.cache) / "side_loop_marks.csv", index=False)
    print("=" * 96 + "\nMARKS BY ROAD CLASS\n" + "=" * 96)
    m = df[(df.weights == "neutral") & df.minor].sort_values(["verdict", "model_score"])
    print("every minor-road mark (neutral score):")
    for r in m.itertuples():
        print(f"  {r.drive[:10]} {r.verdict:4s} {r.model_score:4.1f} {r.highway:12s} {r.road}")
    for wname in ("neutral", "app"):
        d0 = df[df.weights == wname].reset_index(drop=True)
        print(f"\n--- scores under {wname} weights ---")
        print(pd.crosstab(d0.highway, d0.verdict).to_string())
        for label, sub in (("all", d0), ("no motorway", d0[~d0.highway.isin(
                {"motorway", "motorway_link"})])):
            sub = sub.reset_index(drop=True)
            print(f"\n  [{label}]")
            for g, gd in (("pooled", sub), ("major", sub[~sub.minor]),
                          ("minor", sub[sub.minor]),
                          ("Aug", sub[sub.day == "Aug"]), ("Oct", sub[sub.day == "Oct"])):
                gd = gd.reset_index(drop=True)
                nn, nd = (gd.verdict == "nice").sum(), (gd.verdict == "dull").sum()
                a = auc(gd[gd.verdict == "nice"].model_score,
                        gd[gd.verdict == "dull"].model_score)
                lo, hi = boot(gd, lambda x: auc(x[x.verdict == "nice"].model_score,
                                                x[x.verdict == "dull"].model_score))
                import analyze_trace as A
                print(f"    {g:7s} n={nn:3d} nice/{nd:3d} dull  separation {a:.2f} "
                      f"[{lo:.2f}, {hi:.2f}]  chance bar {A.null_ceiling(nn, nd):.2f}  "
                      f"nice mean {gd[gd.verdict=='nice'].model_score.mean():.2f}  "
                      f"dull mean {gd[gd.verdict=='dull'].model_score.mean():.2f}")
            nice = sub[sub.verdict == "nice"].reset_index(drop=True)
            diff = lambda x: (x[x.minor].model_score.mean() - x[~x.minor].model_score.mean())
            lo, hi = boot(nice, diff, by="minor")
            print(f"    nice marks: minor minus major mean score {diff(nice):+.2f} "
                  f"[{lo:+.2f}, {hi:+.2f}]")
            dull = sub[sub.verdict == "dull"].reset_index(drop=True)
            if dull.minor.nunique() == 2:
                lo, hi = boot(dull, diff, by="minor")
                print(f"    dull marks: minor minus major mean score {diff(dull):+.2f} "
                      f"[{lo:+.2f}, {hi:+.2f}]")
            o = offset(sub)
            lo, hi = boot(sub, offset)
            clo, chi = boot_cluster(sub, offset)
            print(f"    logistic nice ~ score + minor: minor worth {o:+.2f} score points "
                  f"[{lo:+.2f}, {hi:+.2f}] by mark, [{clo:+.2f}, {chi:+.2f}] by road "
                  f"({sub.cluster.nunique()} roads)")
            # rate of nice by class at matched score bands
            sub = sub.assign(band=pd.cut(sub.model_score, [0, 3, 4, 5, 6, 10]))
            t = sub.groupby(["band", "minor"], observed=True).verdict.agg(
                lambda v: f"{(v == 'nice').mean():.2f} (n={len(v)})").unstack()
            print("    share nice by score band (columns: minor?)\n" +
                  "\n".join("      " + l for l in t.to_string().splitlines()))


# --- part 4: the drive that would settle it -----------------------------------

PLAN_RADIUS_M = 15000.0
PLAN_MIN_KM = 1.0


def plan_drive(rt, args):
    """Minor roads near Washburn Road to mark, split by what the score says.

    The marks cannot say whether the score ranks minor roads against each other,
    because only two minor roads were ever called dull. This lists named minor
    roads within PLAN_RADIUS_M of Washburn Road, at least PLAN_MIN_KM long and
    mostly on reviewed (not tiger:reviewed=no) ways, in two groups: what the
    score calls dull (<= 4.5) and what it calls good (>= 6.0).
    """
    import shapely
    from common import CRS_METERS
    tags = way_tags(args.pbf, args.cache)
    et = EdgeTags(args.processed, tags, rt.edges)
    sc = rt._edge_scores({})
    geo = rt.edges.geometry.to_crs(CRS_METERS)
    centre = shapely.line_interpolate_point(geo.iat[WASHBURN[1]], 0.5, normalized=True)
    hw = rt.edges["highway"].to_numpy()
    near = np.flatnonzero((geo.distance(centre).to_numpy() <= PLAN_RADIUS_M)
                          & ~np.isin(hw, list(MAJOR)) & rt.edges["name"].notna().to_numpy()
                          & (rt.edges["name"].to_numpy() != ""))
    rows = []
    for e in near:
        u, n, _ = et(int(e))
        rows.append((rt.edges["name"].iat[e], hw[e], rt.km[e], sc[e], u, n))
    df = pd.DataFrame(rows, columns=["road", "highway", "km", "score", "unrev", "nosurf"])
    g = df.groupby("road").apply(lambda x: pd.Series(dict(
        km=x.km.sum(), score=np.average(x.score, weights=x.km),
        unrev=np.average(x.unrev, weights=x.km), nosurf=np.average(x.nosurf, weights=x.km),
        cls=x.groupby("highway").km.sum().idxmax())), include_groups=False)
    g = g[(g.km >= PLAN_MIN_KM) & (g.unrev < 0.5)]
    print("=" * 96 + f"\nMINOR ROADS WITHIN {PLAN_RADIUS_M/1000:.0f} KM OF WASHBURN ROAD, "
          f">= {PLAN_MIN_KM:.0f} km, mostly reviewed\n" + "=" * 96)
    print(f"{len(g)} roads; score p25/50/75 {g.score.quantile(.25):.1f}/"
          f"{g.score.median():.1f}/{g.score.quantile(.75):.1f}")
    for title, sub in (("score calls dull (<= 4.5)", g[g.score <= 4.5]),
                       ("score calls good (>= 6.0)", g[g.score >= 6.0])):
        print(f"\n{title}: {len(sub)}")
        print(sub.sort_values("km", ascending=False).head(15).round(2).to_string())


PARTS = {"washburn": washburn, "census": census, "marks": marks, "summary": summary, "plan": plan_drive}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("processed")
    ap.add_argument("parts", nargs="*", default=list(PARTS))
    ap.add_argument("--traces", default="traces")
    ap.add_argument("--pbf", default="data/raw/new-england-latest.osm.pbf")
    ap.add_argument("--cache", default=".")
    ap.add_argument("--pairs", type=int, default=10,
                    help="e2e pairs per category (rural, suburban, coastal, cross)")
    args = ap.parse_args(argv)
    rt = None
    if set(args.parts) - {"summary"}:
        import router as R
        t0 = time.time()
        rt = R.Router(args.processed)
        print(f"# router loaded in {time.time()-t0:.0f}s ({rt.n:,} nodes)")
    for p in args.parts:
        PARTS[p](rt, args)


if __name__ == "__main__":
    main(sys.argv[1:])
