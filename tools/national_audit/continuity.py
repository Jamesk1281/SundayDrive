"""A national route-correctness check that needs no travel: numbered highways
route along themselves (docs/review-fixes-data.md, "The continuity check").

    continuity.py legs    <processed_dir> <legs.json>
    continuity.py check   <processed_dir> <pack_dir> <legs.json> <result.json>
    continuity.py explain <processed_dir> <result.json> <explained.json>

`legs` takes points about LEG_KM apart along every interstate and US route of
a national build, end to end and both ways (`make_legs`). A leg's `along_km`
is the distance driving the ref's own edges from one to the other.
graph_edges.parquet alone decides the legs, so a closures change leaves them
as they were and one file serves before and after.

`check` routes each leg on the fastest arm, on a summer day so that a pass
shut for the winter is not counted (seasonal closures are a separate table),
and passes it when the route stays on the ref (at least ON_REF of its km
carry it), is no longer than STRETCH times `along_km`, or costs no more,
under the router's own prices for that request, than driving the ref's own
path does (`along_cost`: an interstate beside a US route through a run of
signals is longer and faster, and is the right answer). A closed edge on the
ref's path prices it at infinity. So a leg fails only when the router leaves
a highway it could have driven, for a longer road, and the highway would
have been cheaper had it been open: which is how a wrong closure on a major
road shows (I-10 at Tonopah, closed by two ford nodes), or a turn
restriction or barrier between two edges that the plain path ignores.

`explain` lists, for each failed leg, the closed_to_cars rows on the ref's own
driven path between its ends, which tells a closure from everything else.

tests/test_national_routes.py runs `check` on the legs in legs.json against
the pack in SUNDAYDRIVE_PACK.
"""
import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from common import ONEWAY_FWD, ONEWAY_REV  # noqa: E402

LEG_KM = 50.0
# The window a leg's far end must fall in.
LEG_MIN_KM, LEG_MAX_KM = 40.0, 60.0
# How far, in km, the other carriageway's nodes may lie from a walk that has
# found nothing ahead (`make_legs`).
SWITCH_KM = 0.3
STRETCH = 1.2
ON_REF = 0.9
# A day with every pass open, so a failure is a closure all year.
SUMMER = date(2027, 7, 15)
# An interstate or US route, by the ref OSM puts on its ways: "I 10", "I 35E",
# "US 95", "US 1A". Business, spur and alternate routes carry a suffix word
# and are not taken.
NUMBERED = re.compile(r"^(I|US) \d{1,3}[A-Z]?$")
HERE = Path(__file__).resolve().parent
LEGS = HERE / "legs.json"

# The legs allowed to fail, with why, keyed by `key`. Empty: the seven that
# failed once fords on paved major roads were open (Trail Ridge four times,
# US 12 at White Pass twice, US 322 in Cleveland once;
# docs/review-fixes-data.md) all pass since Trail Ridge's park-entry permit
# and the smoothness rule on paved roads were settled
# (docs/national-data-decisions.md, D1 and D2): 11,414 of 11,414 on
# data/pack-us-next.
KNOWN: dict[str, str] = {}


def refs_of(value) -> list[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return [r.strip() for r in str(value).split(";") if r.strip()]


def key(leg: dict) -> str:
    return f"{leg['ref']} {leg['from'][0]:.6f},{leg['from'][1]:.6f}"


class Refs:
    """Each numbered ref's own edges, as graphs: `both` undirected, `drive`
    directed by `oneway` as the router reads it (common.ONEWAY_FWD/REV)."""

    def __init__(self, processed: Path):
        t = pq.read_table(processed / "graph_edges.parquet",
                          columns=["u", "v", "length_m", "ref", "oneway"])
        codes, uniques = pd.factorize(t["ref"].to_pandas())
        self.u, self.v = t["u"].to_numpy(), t["v"].to_numpy()
        self.length = t["length_m"].to_numpy() / 1000.0
        oneway = t["oneway"].to_pandas().astype(str).str.lower()
        self.fwd_ok = ~oneway.isin(ONEWAY_REV).to_numpy()
        self.rev_ok = ~oneway.isin(ONEWAY_FWD).to_numpy()
        self.by_code = {}
        for code, value in enumerate(uniques):
            for r in refs_of(value):
                if NUMBERED.match(r):
                    self.by_code.setdefault(r, []).append(code)
        self.order_c = np.argsort(codes, kind="stable")
        self.sorted_c = codes[self.order_c]
        nodes = pq.read_table(processed / "graph_nodes.parquet",
                              columns=["node_id", "lon", "lat"])
        self.node_id = nodes["node_id"].to_numpy()
        self.order = np.argsort(self.node_id)
        self.lon, self.lat = nodes["lon"].to_numpy(), nodes["lat"].to_numpy()
        pr = pd.read_csv(processed / "per_region.csv")
        self.starts = np.r_[0, np.cumsum(pr["edges"].to_numpy())]
        self.names = pr["region"].to_numpy()

    def at(self, osm):
        return self.order[np.searchsorted(self.node_id, osm, sorter=self.order)]

    def ll(self, osm):
        i = self.at(osm)
        return [round(float(self.lat[i]), 6), round(float(self.lon[i]), 6)]

    def graph(self, r: str) -> dict:
        rows = np.sort(np.concatenate([
            self.order_c[np.searchsorted(self.sorted_c, c):
                         np.searchsorted(self.sorted_c, c, side="right")]
            for c in self.by_code[r]]))
        ids, inv = np.unique(np.r_[self.u[rows], self.v[rows]], return_inverse=True)
        k, n = len(rows), len(ids)
        a, b, w = inv[:k], inv[k:], self.length[rows]
        f, rv = self.fwd_ok[rows], self.rev_ok[rows]
        local = np.arange(k)
        both, _ = _arcs(np.r_[a, b], np.r_[b, a], np.r_[w, w], np.r_[local, local], n)
        drive, arc_row = _arcs(np.r_[a[f], b[rv]], np.r_[b[f], a[rv]], np.r_[w[f], w[rv]],
                               np.r_[local[f], local[rv]], n)
        region_at = np.empty(n, dtype=object)
        region = self.names[np.searchsorted(self.starts, rows, side="right") - 1]
        region_at[b] = region
        region_at[a] = region
        here = self.at(ids)
        xy = np.column_stack([self.lon[here] * 111.32 * np.cos(np.radians(self.lat[here])),
                              self.lat[here] * 110.57])
        return {"rows": rows, "ids": ids, "a": a, "b": b, "both": both, "drive": drive,
                "arc_row": arc_row, "region_at": region_at, "xy": xy, "tree": cKDTree(xy)}

    def path_arcs(self, g: dict, pred: np.ndarray, s: int, t: int) -> list[tuple]:
        """(national edge row, whether driven from its `u` to its `v`) along
        the driven path from `s` to `t` that `pred` (dijkstra's predecessors
        from `s`) holds, in order."""
        path = [t]
        while path[-1] != s:
            path.append(int(pred[path[-1]]))
        path.reverse()
        out = []
        for x, y in zip(path, path[1:]):
            row = int(g["rows"][g["arc_row"][(x, y)]])
            out.append((row, int(g["ids"][x]) == int(self.u[row])))
        return out

    def leg_arcs(self, g: dict, leg: dict) -> list[tuple]:
        """A leg's own driven path, as `path_arcs`, or [] if there is none."""
        ids = g["ids"]
        s = int(np.searchsorted(ids, leg["from_node"]))
        t = int(np.searchsorted(ids, leg["to_node"]))
        dist, pred = dijkstra(g["drive"], indices=s, limit=LEG_MAX_KM,
                              return_predecessors=True)
        return self.path_arcs(g, pred, s, t) if np.isfinite(dist[t]) else []


def _arcs(src, dst, w, row, n):
    """A CSR graph of arcs src -> dst weighted `w`, keeping the lightest of
    parallel arcs (a coo matrix would add them), and {(src, dst): its `row`}."""
    keep = np.lexsort((w, dst, src))
    src, dst, w, row = src[keep], dst[keep], w[keep], row[keep]
    first = np.r_[True, (src[1:] != src[:-1]) | (dst[1:] != dst[:-1])]
    src, dst, w, row = src[first], dst[first], w[first], row[first]
    graph = coo_matrix((w, (src, dst)), shape=(n, n)).tocsr()
    return graph, {(int(x), int(y)): int(r) for x, y, r in zip(src, dst, row)}


def make_legs(processed: Path) -> list[dict]:
    """Every interstate and US route, end to end, both ways, in consecutive legs.

    Each connected piece of a ref's own edges is walked from one end (the far
    end of a double sweep) to the other, and then back. A step goes from the
    current node to the node about LEG_KM on that the ref's edges reach
    *driving*, and that is farther from the end walked from. So a leg on a
    divided highway starts and ends on the carriageway it drives, and both
    carriageways are walked. A walk that finds nothing ahead to drive to is on
    the carriageway pointing back, and starts again from the nearest of the
    ref's nodes within SWITCH_KM that has. Where none has (a gap in the ref's
    tagging), it steps over without a leg; `gaps` in the printout counts
    those. A piece shorter than LEG_MIN_KM has no leg. A leg's region is the
    one that owns an edge of the ref at its start.
    """
    refs = Refs(processed)
    legs, gaps = [], 0
    for r in sorted(refs.by_code):
        g = refs.graph(r)
        ids, both, drive, xy, tree = g["ids"], g["both"], g["drive"], g["xy"], g["tree"]
        n = len(ids)

        def step(cur, ahead):
            """The next leg's (start, end, km) from `cur`, or None."""
            near = sorted(tree.query_ball_point(xy[cur], SWITCH_KM),
                          key=lambda j: np.hypot(*(xy[j] - xy[cur])))
            for start in [cur] + [j for j in near if j != cur][:8]:
                dc = dijkstra(drive, indices=start, limit=LEG_MAX_KM)
                ok = np.flatnonzero((dc >= LEG_MIN_KM) & (dc <= LEG_MAX_KM) & ahead)
                if len(ok):
                    nxt = int(ok[np.argmin(np.abs(dc[ok] - LEG_KM))])
                    return start, nxt, float(dc[nxt])
            return None

        _, label = connected_components(both, directed=False)
        sizes = np.bincount(label, weights=np.bincount(
            g["a"], weights=refs.length[g["rows"]], minlength=n))
        for comp in np.flatnonzero(sizes >= LEG_MIN_KM):
            members = np.flatnonzero(label == comp)
            d0 = dijkstra(both, indices=int(members[0]))
            end_a = int(members[np.argmax(d0[members])])
            from_a = dijkstra(both, indices=end_a)
            end_b = int(members[np.argmax(from_a[members])])
            for end in (end_a, end_b):
                from_end = from_a if end == end_a else dijkstra(both, indices=end)
                cur = end
                while True:
                    ahead = from_end > from_end[cur] + LEG_MIN_KM * 0.75
                    found = step(cur, ahead)
                    if found:
                        start, nxt, km = found
                        legs.append({"region": g["region_at"][start], "ref": r,
                                     "from": refs.ll(int(ids[start])),
                                     "to": refs.ll(int(ids[nxt])),
                                     "from_node": int(ids[start]),
                                     "to_node": int(ids[nxt]),
                                     "along_km": round(km, 3)})
                        cur = nxt
                        continue
                    du = dijkstra(both, indices=cur, limit=LEG_MAX_KM)
                    ok = np.flatnonzero((du >= LEG_MIN_KM) & (du <= LEG_MAX_KM) & ahead)
                    if not len(ok):
                        break
                    gaps += 1
                    cur = int(ok[np.argmin(np.abs(du[ok] - LEG_KM))])
    print(f"  {len(legs)} legs on {len(refs.by_code)} refs; stepped over {gaps} gaps",
          flush=True)
    return legs


def load_router(processed: Path, pack: Path):
    from router import Router
    return Router(str(processed), pack=str(pack))


def along_cost(router, metric, arcs) -> float:
    """What driving `arcs` (`Refs.path_arcs`) costs under `metric`: each edge
    at its cheapest directed slot that way, infinite if it has none open."""
    if not arcs:
        return np.inf
    total = 0.0
    for row, forward in arcs:
        slots = router._members((router._edge_order, router._edge_start), row)
        slots = [k for k in slots if bool(router.flip[k]) != forward]
        if not slots:
            return np.inf
        total += float(np.min(metric(slots)))
    return total


def route_leg(router, metric, leg: dict, arcs) -> dict:
    """The fastest route for one leg; how much of it is on the leg's ref; and
    what it and the ref's own path cost under `metric`."""
    s, s_off = router.snap(*leg["from"])
    t, t_off = router.snap(*leg["to"])
    res = router.route(s, t, 0.0, None, on=SUMMER)
    along = along_cost(router, metric, arcs)
    out = {"snap_m": [round(s_off, 1), round(t_off, 1)],
           "along_cost": round(along, 3) if np.isfinite(along) else None}
    if res is None:
        return {**out, "route_km": None, "route_cost": None, "on_ref": 0.0,
                "stretch": None, "passed": False}
    km = float(res.edges["length_m"].sum()) / 1000.0
    cost = float(metric(res.slots).sum())
    on = sum(float(m) for m, r in zip(res.edges["length_m"], res.edges["ref"])
             if leg["ref"] in refs_of(r)) / 1000.0
    frac = on / km if km else 1.0
    return {**out, "route_km": round(km, 3), "route_cost": round(cost, 3),
            "on_ref": round(frac, 4), "stretch": round(km / leg["along_km"], 4),
            "passed": bool(frac >= ON_REF or km <= STRETCH * leg["along_km"]
                           or (np.isfinite(along) and cost <= along + 1e-6))}


def check(router, legs: list[dict], processed: Path) -> list[dict]:
    """`route_leg` for every leg, on the fastest arm's prices on SUMMER."""
    refs = Refs(processed)
    metric = router.metric(0.0, None, 1.0, SUMMER)
    out = []
    for r in sorted({leg["ref"] for leg in legs}):
        g = refs.graph(r)
        for i, leg in enumerate(legs):
            if leg["ref"] == r:
                out.append((i, {**leg, **route_leg(router, metric, leg,
                                                   refs.leg_arcs(g, leg))}))
    return [result for _, result in sorted(out, key=lambda x: x[0])]


def explain(processed: Path, results: list[dict]) -> list[dict]:
    """Each failed leg, with the closed_to_cars rows on the ref's own driven
    path between its ends: an "edge" row on one of the path's edges, or a
    "through" row at one of its inner nodes."""
    refs = Refs(processed)
    closed = pd.read_parquet(processed / "closed_to_cars.parquet")
    by_edge = {e: g for e, g in closed[closed["rule"] == "edge"].groupby("edge")}
    through = closed[closed["rule"] == "through"]
    through_at = {n: g for n, g in through.groupby("osm_id")}
    out = []
    failed = [r for r in results if not r["passed"]]
    for r in sorted({f["ref"] for f in failed}):
        g = refs.graph(r)
        for leg in (f for f in failed if f["ref"] == r):
            path = [row for row, _ in refs.leg_arcs(g, leg)]
            found = []
            for e in path:
                if e in by_edge:
                    found += [{"edge": e, **_row(c)} for _, c in by_edge[e].iterrows()]
            inner = ((set(refs.u[path]) | set(refs.v[path]))
                     - {leg["from_node"], leg["to_node"]})
            for osm in sorted(int(x) for x in inner):
                if osm in through_at:
                    found += [{"edge": int(c["edge"]), **_row(c)}
                              for _, c in through_at[osm].iterrows()]
            out.append({**leg, "closed": found})
    return out


def _row(c) -> dict:
    return {"rule": c["rule"], "kind": c["kind"], "osm_type": c["osm_type"],
            "osm_id": int(c["osm_id"]), "tag": c["tag"],
            "length_m": round(float(c["length_m"]), 1)}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("legs")
    a.add_argument("processed")
    a.add_argument("out")
    c = sub.add_parser("check")
    c.add_argument("processed")
    c.add_argument("pack")
    c.add_argument("legs")
    c.add_argument("out")
    e = sub.add_parser("explain")
    e.add_argument("processed")
    e.add_argument("results")
    e.add_argument("out")
    args = p.parse_args()
    t0 = time.time()
    if args.cmd == "legs":
        legs = make_legs(Path(args.processed))
        # One leg a line, so a rebuilt graph's changes read as a diff.
        Path(args.out).write_text("[\n" + ",\n".join(
            json.dumps(leg, separators=(",", ":")) for leg in legs) + "\n]\n")
        print(f"{len(legs)} legs in {time.time() - t0:.0f}s")
        return
    if args.cmd == "explain":
        found = explain(Path(args.processed), json.loads(Path(args.results).read_text()))
        Path(args.out).write_text(json.dumps(found, indent=1) + "\n")
        n = sum(1 for f in found if f["closed"])
        print(f"{len(found)} failed legs; {n} have a closure on the ref's own path")
        return
    router = load_router(Path(args.processed), Path(args.pack))
    print(f"router loaded in {time.time() - t0:.0f}s", flush=True)
    legs = json.loads(Path(args.legs).read_text())
    results = check(router, legs, Path(args.processed))
    Path(args.out).write_text(json.dumps(results, indent=0) + "\n")
    failed = [r for r in results if not r["passed"]]
    print(f"{len(results) - len(failed)} of {len(results)} legs pass in {time.time() - t0:.0f}s")
    for r in failed:
        print(f"  FAIL {r['region']:9s} {r['ref']:7s} along {r['along_km']:.1f} km "
              f"(cost {r['along_cost']}), route {r['route_km']} km (cost {r['route_cost']}), "
              f"on ref {r['on_ref']:.0%}  {r['from']} -> {r['to']}")


if __name__ == "__main__":
    main()
