"""Route options: the in-between scenic routes the slider cannot reach.

The router's cost is linear in slider strength (`Router._weights`), so the
slider only ever returns routes on the lower envelope of those lines, and the
envelope's middle routes own slivers of the track. Many good in-between routes
("VT-100, then I-89") are on no envelope at all. This module builds them by
**splicing off one scenic base**:

    fastest(start -> S[i])  +  S[i:j]  +  fastest(S[j] -> destination)

where S is the route at pref 1. One forward and one reverse pref-0 Dijkstra,
both capped at the pref-0 cost of S, price every pair (i, j) of switch points
along S in O(1). A Pareto frontier on (extra minutes, beautiful km), thinned to
a menu, is what the app turns into slider detents.

Two entry points, and they are deliberately symmetric:

  - `plan` prices the menu for a new trip and returns it with the fastest
    route and the default option in full detail.
  - `spliced_route` rebuilds one option from its two **switch points**, which
    are lat/lon/heading on a road, never node ids, so the follow-up request
    can land on a different box or a rebuilt graph. It is also how a reroute
    keeps a spliced plan: from wherever the driver is, fastest to the leave
    point, the scenic stretch to the rejoin point, then fastest home.

A sub-path of a cheapest path is a cheapest path, so the three legs that
`spliced_route` searches reproduce the planned option exactly, ties aside. The
tests hold every menu option to that.

Measurements, the decisions and the traps: docs/route-options.md.
"""

import threading
import time

import numpy as np
import shapely
from pyproj import Transformer
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from common import CRS_METERS
from router import (_TO_M, BEAUTIFUL_SCORE, TURN_BACK_CAP_MIN, _behind_strip,
                    _tangent_at, _turn_delta)

# Switch points along S: every this many km, or len(S)/SWITCH_POINTS, whichever
# is coarser. The study's spacing; finer buys nothing visible on the menu.
SWITCH_STEP_MIN_KM = 0.5
SWITCH_POINTS = 250

# A menu option must add this much beautiful road over the one before it:
# max(1 mile, 5% of the whole gain). Fewer, more different detents.
MENU_STEP_MIN_KM = 1.609
MENU_STEP_SHARE = 0.05

# ...except the first option after the fastest, which needs only half a mile:
# enough that the dial never prints "+0 mi" (the study's rule, keeping the
# first frontier point whatever it adds, put 33 such options on the 59 re-run
# trips), and small enough to keep the cheap option that closes the gap at the
# bottom of the track (a gap of half the detour on 2 of 44 trips, against 3
# at the full step). docs/route-options.md.
MENU_FIRST_MIN_KM = 0.805

# The option shown first: the most scenic one costing at most this share of
# the fastest time. The owner's rule of 2026-10-07; Waitsfield -> Needham opens
# on its +44 min option.
DEFAULT_MAX_EXTRA_SHARE = 0.25

# Where a switch point sits: this far along the scenic road from the junction
# it names (or half the road, if the road is shorter). Off the junction itself,
# so the point names one road and not every road meeting there.
SWITCH_INSET_M = 15.0

# How far from a road a switch point may lie and still name it, and how far
# its heading may be from the road's. The points are written to 1e-6 degrees
# (~0.1 m), so the distance only has to absorb rounding.
SWITCH_MATCH_M = 2.0
SWITCH_MATCH_DEG = 30.0

# The simplified line each option is drawn with: ~15-20 m. One full route is
# 145-280 KB; twelve of them would be ~2.5 MB a plan.
LINE_TOLERANCE_DEG = 0.00015
LINE_DECIMALS = 5

_FROM_M = Transformer.from_crs(CRS_METERS, 4326, always_xy=True)


class SwitchPointNotFound(ValueError):
    """A switch point that names no road on this graph."""


# --- The pref-0 graph, cached ---------------------------------------------

# The fastest weights do not depend on beauty weights (pref 0 zeroes the
# scenery term), only on the day's closures and the dirt-road avoidance, so
# the matrix and its transpose are kept per (closure version, avoid_unpaved).
# ~80 MB each; two cover the default avoidance across a closure change.
_GRAPHS = {}
_GRAPHS_MAX = 2
_GRAPHS_LOCK = threading.Lock()


def _pair_min(router, w):
    pw = np.full(router.n_pairs, np.inf)
    np.minimum.at(pw, router.slot_pair, w)
    return pw


def _fastest_graphs(router, avoid_unpaved, on):
    key = (id(router), router.closure_version(on), round(float(avoid_unpaved), 4))
    with _GRAPHS_LOCK:
        hit = _GRAPHS.pop(key, None)
        if hit is None:
            w0 = router._weights(0.0, np.zeros(len(router.km)), avoid_unpaved, on)
            pw0 = _pair_min(router, w0)
            g0 = csr_matrix((pw0, (router.u_tail, router.u_head)),
                            shape=(router.n, router.n))
            hit = (w0, pw0, g0, g0.T.tocsr())
        _GRAPHS[key] = hit
        while len(_GRAPHS) > _GRAPHS_MAX:
            _GRAPHS.pop(next(iter(_GRAPHS)))
        return hit


# --- Small helpers over the directed graph -----------------------------------

def _pairs(router, path):
    path = np.asarray(path, dtype=np.int64)
    return np.searchsorted(router._pair_key, path[:-1] * router.n + path[1:])


def _best_slots(router, pairs, w):
    """The directed slot each hop takes under `w`: the cheapest of any
    parallel roads, which is the one the search priced."""
    start = router._pair_start[pairs]
    count = router._pair_start[pairs + 1] - start
    out = router._pair_slots[start].copy()
    for k in np.flatnonzero(count > 1):
        sl = router._pair_slots[start[k]:start[k] + count[k]]
        out[k] = sl[np.argmin(w[sl])]
    return out


def _hop_stats(router, slots, beautiful):
    """Minutes, km and beautiful km per slot. Minutes are `d_minutes`, never
    the search's weights: pref-0 weights carry the dirt-road avoidance, which
    is not time."""
    e = router.eidx[slots]
    km = router.km[e]
    return np.column_stack([router.d_minutes[slots], km, km * beautiful[e]])


def _tree_path(pred, v, roots):
    """The nodes from `v` back along the tree to whichever of `roots` it
    grew from: reversed, a forward tree's path; as is, a reverse tree's."""
    out = [int(v)]
    while out[-1] not in roots:
        p = int(pred[out[-1]])
        if p < 0:
            return None
        out.append(p)
    return out


def _tree_stats(router, pred, nodes, roots, w, beautiful, forward):
    """Cumulative (minutes, km, beautiful km) from the tree's root to each of
    `nodes`, sharing work through a memo: the paths to consecutive switch
    points share almost everything."""
    memo = {int(r): np.zeros(3) for r in roots}
    out = np.full((len(nodes), 3), np.inf)
    for k, v in enumerate(nodes):
        chain, cur = [], int(v)
        while cur not in memo:
            chain.append(cur)
            cur = int(pred[cur])
            if cur < 0:
                break
        if cur < 0:
            continue
        if chain:
            seq = np.array([cur] + chain[::-1], dtype=np.int64)
            hops = (_pairs(router, seq) if forward
                    else _pairs(router, seq[::-1])[::-1])
            stats = np.cumsum(_hop_stats(router, _best_slots(router, hops, w),
                                         beautiful), axis=0) + memo[cur]
            for node, row in zip(seq[1:], stats):
                memo[int(node)] = row
        out[k] = memo[int(v)]
    return out


def _line(router, slots):
    """The drawn line of a run of slots, in travel order, as one array."""
    e = router.eidx[slots]
    coords, idx = shapely.get_coordinates(router._geom[e], return_index=True)
    starts = np.searchsorted(idx, np.arange(len(e)))
    pos = np.arange(len(idx)) - starts[idx]
    flip = router.flip[slots][idx]
    order = np.lexsort((np.where(flip, -pos, pos), idx))
    coords = coords[order]
    keep = np.ones(len(coords), bool)
    keep[1:] = np.any(coords[1:] != coords[:-1], axis=1)
    return coords[keep]


def _simplified(router, slots):
    line = shapely.simplify(shapely.LineString(_line(router, slots)),
                            LINE_TOLERANCE_DEG, preserve_topology=False)
    return np.round(shapely.get_coordinates(line), LINE_DECIMALS).tolist()


def _label(router, e):
    """A road's name for a caption: its ref where it has one ("VT 100"),
    which is what the signs say on the roads this is about, else its name."""
    for col in ("ref", "name"):
        if col in router.edges.columns:
            v = router.edges[col].iat[int(e)]
            if isinstance(v, str) and v.strip():
                return v.split(";")[0].strip()
    return ""


def _roads(router, slots, most=3):
    """The few roads carrying most of a stretch, in the order driven."""
    km, first = {}, {}
    for k, e in enumerate(router.eidx[slots]):
        name = _label(router, e)
        if name:
            km[name] = km.get(name, 0.0) + float(router.km[e])
            first.setdefault(name, k)
    top = sorted(km, key=km.get, reverse=True)[:most]
    return sorted(top, key=first.get)


def _collect(router, path, slots, scores, heading, origin):
    """`Router._collect` over a path whose hops were chosen under different
    weights per leg: a selector that makes each chosen slot the cheapest."""
    pick = np.ones(len(router.eidx))
    pick[slots] = 0.0
    aiming = (heading if heading is not None and 0.0 <= heading < 360.0
              else None)
    return router._collect(path, pick, scores, aiming,
                           origin if aiming is not None else None)


# --- Switch points -------------------------------------------------------------

def switch_point(router, slot, at_end):
    """Where a spliced route leaves (`at_end=False`, on the scenic road's
    first hop, just past the junction) or rejoins (`at_end=True`, on its last
    hop, just short of the junction) the fast roads.

    On the road and not at the junction: a junction is several roads, and a
    lat/lon snapped back onto one can land on the wrong one. The heading says
    which way along the road the route drives it. docs/route-options.md.
    """
    e = int(router.eidx[slot])
    flip = bool(router.flip[slot])
    line = router._edge_geom_m[e]
    length = line.length
    inset = min(SWITCH_INSET_M, 0.5 * length)
    travel = length - inset if at_end else inset
    point = line.interpolate(length - travel if flip else travel)
    tangent = _tangent_at(line, point) or 0.0
    heading = (tangent + 180.0) % 360.0 if flip else tangent
    lon, lat = _FROM_M.transform(point.x, point.y)
    return {"lat": round(lat, 6), "lon": round(lon, 6),
            "heading": round(heading, 1), "road": _label(router, e)}


def switch_slots(router, lat, lon, heading):
    """The directed slots a switch point names: the road under it, driven the
    way its heading says. Several when parallel roads share the geometry."""
    x, y = _TO_M.transform(lon, lat)
    point = shapely.Point(x, y)
    found = []
    for e in router._edge_tree.query(point.buffer(SWITCH_MATCH_M)):
        e = int(e)
        d = router._edge_geom_m[e].distance(point)
        tangent = _tangent_at(router._edge_geom_m[e], point)
        if d > SWITCH_MATCH_M or tangent is None:
            continue
        delta = abs(_turn_delta(heading, tangent))
        if min(delta, 180.0 - delta) > SWITCH_MATCH_DEG:
            continue
        found.append((d, e, delta > 90.0))
    if not found:
        raise SwitchPointNotFound(f"no road at {lat},{lon} heading {heading}")
    nearest = min(d for d, _, _ in found)
    keep = np.zeros(len(router.eidx), bool)
    for d, e, flip in found:
        if d <= nearest + 0.25:
            keep |= (router.eidx == e) & (router.flip == flip)
    slots = np.flatnonzero(keep)
    if not len(slots):
        raise SwitchPointNotFound(f"no way along the road at {lat},{lon}")
    return slots


# --- Planning the menu ------------------------------------------------------

class Plan:
    """What `plan` found: the fastest route, the menu, and which is shown first."""

    def __init__(self, fastest, default, menu, scenic, frontier=(), base=None):
        self.fastest = fastest        # RouteResult
        self.default = default        # index into menu
        self.menu = menu              # list of dicts, menu[0] is the fastest
        self.scenic = scenic          # RouteResult of menu[default]
        # (extra minutes, beautiful km gained) of every frontier point the
        # menu was thinned from; the study scores against it.
        self.frontier = list(frontier)
        # (extra minutes, beautiful km gained) of S itself, the full scenic
        # route: the study's denominator for "a share of the detour".
        self.base = base

    def options_json(self):
        return {"default": self.default,
                "menu": [{k: v for k, v in o.items() if not k.startswith("_")}
                         for o in self.menu]}


def plan(router, s, t, weights=None, avoid_unpaved=1.0, on=None,
         heading=None, origin=None, abort=lambda: False, timings=None):
    """The menu of spliced routes from `s` to `t`, or None.

    None when there is no route, or when `abort()` turns true between phases:
    the server's guard against a plan making somebody else's request wait. The
    caller then sends today's response. `timings`, when given, is filled with
    each phase's seconds for the capacity study.
    """
    clock = time.perf_counter
    tick = clock()

    def lap(name):
        nonlocal tick
        if timings is not None:
            now = clock()
            timings[name] = now - tick
            tick = now

    scores = router._edge_scores(weights or {})
    beautiful = scores >= BEAUTIFUL_SCORE
    w0, pw0, g0, g0T = _fastest_graphs(router, avoid_unpaved, on)
    w1 = router._weights(1.0, scores, avoid_unpaved, on)
    targets = router.node_copies.get(t)
    if targets is None:
        targets = np.array([t])
    roots_t = {int(x) for x in targets}

    # S, the scenic base: the route at pref 1, as an expanded node path.
    g1 = csr_matrix((_pair_min(router, w1), (router.u_tail, router.u_head)),
                    shape=(router.n, router.n))
    d1, p1 = dijkstra(g1, directed=True, indices=s, return_predecessors=True)
    dst = int(targets[np.argmin(d1[targets])])
    if not np.isfinite(d1[dst]):
        return None
    S = _tree_path(p1, dst, {int(s)})
    if S is None:
        return None
    S = np.array(S[::-1], dtype=np.int64)
    lap("scenic")
    if abort():
        return None

    # The two trees, capped at S's pref-0 cost. Exact: every prefix and suffix
    # of S is a path, so no tree distance a candidate uses can exceed it.
    pairs_s = _pairs(router, S)
    limit = float(pw0[pairs_s].sum()) * (1 + 1e-9) + 1e-6
    df, pf = dijkstra(g0, directed=True, indices=s, limit=limit,
                      return_predecessors=True)
    if abort():
        return None
    db, pb, _ = dijkstra(g0T, directed=True, indices=targets, min_only=True,
                         limit=limit, return_predecessors=True)
    lap("trees")
    if abort():
        return None

    # The fastest route falls out of the forward tree; no A* arm needed.
    fdst = int(targets[np.argmin(df[targets])])
    F = np.array(_tree_path(pf, fdst, {int(s)})[::-1], dtype=np.int64)
    slots_f = (_best_slots(router, _pairs(router, F), w0) if len(F) > 1
               else np.array([], dtype=np.int64))
    fastest = _collect(router, F, slots_f, scores, heading, origin)
    f_min, f_km, f_bkm = _hop_stats(router, slots_f, beautiful).sum(axis=0)

    slots_s = _best_slots(router, pairs_s, w1)
    cum = np.vstack([np.zeros(3),
                     np.cumsum(_hop_stats(router, slots_s, beautiful), axis=0)])
    t_max = cum[-1, 0] - f_min

    fastest_option = {"extra_minutes": 0.0, "minutes": round(float(f_min), 1),
                      "km": round(float(f_km), 1),
                      "beautiful_km": round(float(f_bkm), 1),
                      "leave": None, "rejoin": None, "roads": [],
                      "line": _simplified(router, slots_f) if len(slots_f) else [],
                      "_gain": 0.0}
    menu = [fastest_option]
    if t_max <= 0 or len(S) < 2:
        lap("splice")
        return Plan(fastest, 0, menu, fastest)

    # Switch points along S.
    step = max(SWITCH_STEP_MIN_KM, cum[-1, 1] / SWITCH_POINTS)
    keep = [0]
    for q in range(1, len(S)):
        if cum[q, 1] - cum[keep[-1], 1] >= step:
            keep.append(q)
    if keep[-1] != len(S) - 1:
        keep.append(len(S) - 1)
    keep = np.array(keep)
    FP = _tree_stats(router, pf, S[keep], {int(s)}, w0, beautiful, True)
    FS = _tree_stats(router, pb, S[keep], roots_t, w0, beautiful, False)

    I, J = np.triu_indices(len(keep), k=1)
    qi, qj = keep[I], keep[J]
    total = FP[I] + cum[qj] - cum[qi] + FS[J]
    extra = total[:, 0] - f_min
    gain = total[:, 2] - f_bkm
    # Trap 9: an option that adds time must add beautiful road.
    ok = np.isfinite(extra) & (extra > 0) & (extra <= t_max + 1e-6) & (gain > 1e-9)
    idx = np.flatnonzero(ok)
    idx = idx[np.lexsort((-gain[idx], extra[idx]))]

    pre_memo, suf_memo = {}, {}

    def pre(q):
        if q not in pre_memo:
            pre_memo[q] = np.array(_tree_path(pf, S[q], {int(s)})[::-1], dtype=np.int64)
        return pre_memo[q]

    def suf(q):
        if q not in suf_memo:
            suf_memo[q] = np.array(_tree_path(pb, S[q], roots_t), dtype=np.int64)
        return suf_memo[q]

    def full_path(k):
        a, b = int(qi[k]), int(qj[k])
        return np.concatenate([pre(a)[:-1], S[a:b], suf(b)])

    def simple(k):
        # On junctions, not on expanded indices: two copies of one junction
        # are one place, and a path through both is a U-turn loop (Trap 10).
        real = router.real_node[full_path(k)]
        return len(np.unique(real)) == len(real)

    bad = np.zeros(len(idx), bool)
    checked = set()
    while True:
        b = np.where(bad, -np.inf, gain[idx])
        prev = np.concatenate([[0.0], np.maximum.accumulate(b)[:-1]])
        prev = np.maximum(prev, 0.0)
        front = np.flatnonzero(b > prev + 1e-9)
        todo = [f for f in front if f not in checked]
        if not todo:
            break
        if abort():
            return None
        for f in todo:
            checked.add(f)
            if not simple(idx[f]):
                bad[f] = True
    front = idx[front]
    lap("splice")
    if not len(front):
        return Plan(fastest, 0, menu, fastest)

    # The menu: the first option adds half a mile, each after it at least
    # max(1 mi, 5% of the whole gain) over the last one kept; the most scenic
    # frontier point always stays.
    whole = float(gain[front[-1]])
    step_km = max(MENU_STEP_MIN_KM, MENU_STEP_SHARE * whole)
    chosen = []
    for k in front:
        if (gain[k] >= MENU_FIRST_MIN_KM if not chosen
                else gain[k] - gain[chosen[-1]] >= step_km):
            chosen.append(int(k))
    if not chosen or chosen[-1] != front[-1]:
        chosen.append(int(front[-1]))

    built = {}
    for k in chosen:
        path = full_path(k)
        a, b = int(qi[k]), int(qj[k])
        n_pre = len(pre(a)) - 1
        slots_pre = (_best_slots(router, _pairs(router, pre(a)), w0)
                     if n_pre else np.array([], dtype=np.int64))
        slots_suf = (_best_slots(router, _pairs(router, suf(b)), w0)
                     if len(suf(b)) > 1 else np.array([], dtype=np.int64))
        slots = np.concatenate([slots_pre, slots_s[a:b], slots_suf]).astype(np.int64)
        built[k] = (path, slots)
        menu.append({
            "extra_minutes": round(float(extra[k]), 1),
            "minutes": round(float(total[k, 0]), 1),
            "km": round(float(total[k, 1]), 1),
            "beautiful_km": round(float(total[k, 2]), 1),
            # None at an end of S: the option leaves from the start, or
            # stays scenic to the destination.
            "leave": switch_point(router, slots_s[a], False) if a > 0 else None,
            "rejoin": (switch_point(router, slots_s[b - 1], True)
                       if b < len(S) - 1 else None),
            "roads": _roads(router, slots_s[a:b]),
            "line": _simplified(router, slots),
            "_gain": float(gain[k]),
            "_k": k,
        })
    lap("menu")

    budget = DEFAULT_MAX_EXTRA_SHARE * f_min
    default = max(i for i, o in enumerate(menu) if o["extra_minutes"] <= budget)
    if default == 0:
        scenic = fastest
    else:
        path, slots = built[menu[default]["_k"]]
        scenic = _collect(router, path, slots, scores, heading, origin)
        scenic.switch = {"leave": menu[default]["leave"],
                         "rejoin": menu[default]["rejoin"]}
    lap("default")
    return Plan(fastest, default, menu, scenic,
                [(float(extra[k]), float(gain[k])) for k in front],
                (float(t_max), float(cum[-1, 2] - f_bkm)))


# --- Rebuilding one option from its switch points ---------------------------

def spliced_route(router, s, t, leave=None, rejoin=None, weights=None,
                  avoid_unpaved=1.0, on=None, heading=None, origin=None,
                  keep_ahead=False):
    """The route from `s` that drives the scenic stretch between two switch
    points: fastest to `leave`, pref 1 to `rejoin`, fastest to `t`.

    `leave` and `rejoin` are (lat, lon, heading) or None. No `leave` means the
    stretch starts here, which is also how a driver already on it is
    rerouted; no `rejoin` means it runs to the destination. Raises
    `SwitchPointNotFound` for a point naming no road on this graph (a rebuild
    since the plan), returns None when there is no route.

    `keep_ahead` is `Router.route`'s: for a driver who has declined a U-turn,
    the route that goes on ahead unless that costs more than
    TURN_BACK_CAP_MIN. docs/reroute-uturn.md.
    """
    scores = router._edge_scores(weights or {})
    w0 = _fastest_graphs(router, avoid_unpaved, on)[0]
    w1 = router._weights(1.0, scores, avoid_unpaved, on)
    leave_slots = None if leave is None else switch_slots(router, *leave)
    rejoin_slots = None if rejoin is None else switch_slots(router, *rejoin)

    result = _legs(router, s, t, leave_slots, rejoin_slots, w0, w1, scores,
                   heading, origin)
    if result is None or not (keep_ahead and result.turns_around):
        return result
    x, y = _TO_M.transform(origin[1], origin[0])
    blocked = router._turn_back_slots(_behind_strip(x, y, heading), heading)
    w0b, w1b = w0.copy(), w1.copy()
    w0b[blocked] = np.inf
    w1b[blocked] = np.inf
    ahead = _legs(router, s, t, leave_slots, rejoin_slots, w0b, w1b, scores,
                  heading, origin)
    if ahead is None or ahead.minutes - result.minutes > TURN_BACK_CAP_MIN:
        return result
    return ahead


def _legs(router, s, t, leave_slots, rejoin_slots, w0, w1, scores,
          heading, origin):
    """The three legs, searched one after another, keeping every way of
    arriving at a switch point's junction until the end.

    A junction with a turn restriction stands at several indices, one per
    restricted approach, and a switch point's road can leave from more than
    one of them. The cheapest arrival at *any* of them can loop back through
    the junction it is about to cross — measured on the 60-trip re-run, the
    rebuild then came back 1.8 min shorter than the option priced and drove
    one junction twice. So each copy is searched for separately, and the
    cheapest whole route that drives no junction twice wins: the same test
    the plan applied (Trap 10, docs/route-options.md).
    """
    targets = router.node_copies.get(t)
    if targets is None:
        targets = np.array([t])
    trees = {}

    def searched(src, to, pref, w, each):
        """(cost, path, slots) from `src`: to each of `to` if `each`, else to
        the cheapest of them."""
        if not each:
            found = [router._cheapest(src, np.unique(to), pref, w)]
        elif pref == 0.0:
            found = [router._cheapest(src, np.array([x]), 0.0, w) for x in np.unique(to)]
        else:
            key = (src, id(w))
            if key not in trees:
                g = csr_matrix((_pair_min(router, w), (router.u_tail, router.u_head)),
                               shape=(router.n, router.n))
                trees[key] = dijkstra(g, directed=True, indices=src,
                                      return_predecessors=True)
            dist, pred = trees[key]
            found = [_tree_path(pred, x, {src})[::-1] for x in np.unique(to)
                     if np.isfinite(dist[x])]
        out = []
        for p in found:
            if p is None:
                continue
            p = [int(v) for v in p]
            sl = (_best_slots(router, _pairs(router, p), w).tolist() if len(p) > 1
                  else [])
            out.append((float(w[sl].sum()) if sl else 0.0, p, sl))
        return out

    def extend(ways, to, pref, w, each=False):
        return [dict(way, cost=way["cost"] + c, path=way["path"] + p[1:],
                     slots=way["slots"] + sl)
                for way in ways for c, p, sl in searched(way["path"][-1], to, pref, w, each)]

    def cross(ways, candidates):
        # Over the switch point's own road, from whichever copy of its
        # junction this way arrived at.
        out = []
        for way in ways:
            here = [int(k) for k in candidates if router.tail[k] == way["path"][-1]]
            if here:
                k = min(here, key=lambda k: w1[k])
                out.append(dict(way, cost=way["cost"] + float(w1[k]),
                                path=way["path"] + [int(router.head[k])],
                                slots=way["slots"] + [k]))
        return out

    ways = [dict(cost=0.0, path=[int(s)], slots=[], leave=None, rejoin=None)]
    if leave_slots is not None and int(s) not in set(router.head[leave_slots].tolist()):
        ways = cross(extend(ways, router.tail[leave_slots], 0.0, w0, each=True),
                     leave_slots)
        for way in ways:
            way["leave"] = switch_point(router, way["slots"][-1], False)
    if rejoin_slots is None:
        ways = extend(ways, targets, 1.0, w1)
    else:
        heads = set(router.head[rejoin_slots].tolist())
        done = [w for w in ways if w["path"][-1] in heads]
        todo = [w for w in ways if w["path"][-1] not in heads]
        ways = done + cross(extend(todo, router.tail[rejoin_slots], 1.0, w1, each=True),
                            rejoin_slots)
        rejoin_set = set(rejoin_slots.tolist())
        for way in ways:
            # Unless the driver is already past it, or the stretch is one road
            # and crossing the leave point crossed this one too.
            if way["slots"] and way["slots"][-1] in rejoin_set:
                way["rejoin"] = switch_point(router, way["slots"][-1], True)
        ways = extend(ways, targets, 0.0, w0)
    ways = [w for w in ways if len(w["path"]) >= 2]
    if not ways:
        return None
    simple = [w for w in ways
              if len(set(router.real_node[w["path"]].tolist())) == len(w["path"])]
    best = min(simple or ways, key=lambda w: w["cost"])
    result = _collect(router, np.array(best["path"], dtype=np.int64),
                      np.array(best["slots"], dtype=np.int64), scores, heading, origin)
    result.switch = {"leave": best["leave"], "rejoin": best["rejoin"]}
    return result


def feature(result):
    """`RouteResult.geojson`, carrying the switch points of a spliced route so
    the app can reroute it by legs."""
    out = result.geojson()
    switch = getattr(result, "switch", None)
    if switch is not None:
        out["properties"]["switch"] = switch
    return out
