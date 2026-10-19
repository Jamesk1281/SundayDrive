"""Scenic loops: one start point, a distance target, and a different loop each press.

The user gives a start and a length. There is no destination, so this module's
whole job is choosing the geography — which `docs/loop-routes-design.md` measures
as the term that decides whether a drive is good.

Why this is not `router.route(start, start)`
--------------------------------------------
That returns a zero-length route, and correctly so: the router minimises a sum
that accumulates with distance, so the cheapest way back to where you started is
not to leave. Hitting a distance *target* while collecting scenery is the
Orienteering Problem, which is NP-hard. What makes it tractable here is the
router's biggest inefficiency:

    `route()` runs a full-graph Dijkstra with no target early-exit.

For point-to-point that is pure waste. Here it is the entire architecture. One
pass from the start settles every node in the state, and — the measured result
this module is built on — the shortest-path *tree* it hands back can be walked to
recover the exact km and collected scenic-km to all 313,950 nodes, for about
80 ms of vectorised arithmetic. See `_accumulate`. So one pass yields 313,950
costed candidate turnarounds, and re-filtering all of them when the user moves
the distance slider takes 1.1 ms.

On New England the passes are no longer run over all of it. A loop of the
requested length cannot leave a disc of that radius around the start, so the
two passes search only the disc, prove that what they found there is what the
whole graph would give, and search the whole graph when they cannot
(§`_serves`, docs/loop-speed.md).

The shape of a loop
-------------------
1. Cache two fields per (start, pref, weights): the cost/km/scenic-km *out* to
   every node in the disc, and the same *back* from every node (§`_fields`).
2. Filter and rank candidate turnarounds — free, 1.1 ms (§`candidates`).
3. For a chosen turnaround, reuse the cached outbound path and run **one** more
   Dijkstra home with the roads just driven made three times more expensive
   (§`_build`), stopped at the cost of a way home already in hand.

All of it together costs about one search of the whole graph for a first 40 km
loop from a new start, where it cost 9.3 before the two caps
(docs/loop-speed.md).

Step 3 is the one that makes this a loop rather than an out-and-back. Measured
over three starts at a 40 km target, the share of loop km spent driving a road
already driven:

    plain out-and-back      Needham 26%   Petersham 50%   Boston 18%
    with the penalty        Needham  0%   Petersham  0%   Boston  0%

Petersham at 50% is the arithmetic maximum — a rural start where the way home is
the way out, reversed. One extra pass removes it entirely for about 0.15 points
of mean score.

Those three are one turnaround each, chosen for scenery. What `plan` actually
ships is chosen for *distance*, which is a different candidate: over three starts
and three targets it comes out at 1.1% repeated road on average and 3.4% at
worst. Not zero, and the difference is `SPAN_PICKS` — see there.

The penalty is soft (a multiplier) and never a ban, and that is not a
preference. 53,216 of 310,162 junctions — **17.2%** — are dead ends, and a house
on a cul-de-sac has *no* loop that avoids driving its own street twice. A hard
edge-disjointness constraint, which is the textbook way to get a non-retracing
circuit, returns "no loop" for every one of them. Sampled five at random: all
five failed hard and all five worked at x3.

What `pref` does here, and why the tab should not offer it
----------------------------------------------------------
Less than it does point-to-point, and not monotonically. Measured at 40 km
targets from two starts:

    pref      0.00   0.25   0.50   0.75   1.00
    Needham   4.76   5.41   5.67   5.73   5.74     score
              2.3    4.1    7.0    8.7    8.7      km >= 7
    Concord   5.86   5.86   4.99   6.15   6.19     score
              9.2    9.2    7.6   11.3    9.9      km >= 7

The endpoints behave — pref 1.0 is clearly better than pref 0.0, on both
measures, from both starts. The dip in the middle is real, and *which* pref
dips depends on the start: Concord loses 0.87 at pref 0.5, and Needham used to
lose 1.42 at pref 0.25 before the forest component was rebuilt on measured tree
cover (it read 5.00 / 3.58 / 5.43 / 5.84 under the old `c_green`). Do not read
the dip as living at a particular slider position. It has two causes, both
structural rather than a bug to chase: candidate turnarounds are ranked by
scenery whatever `pref` is, so a middling pref moves the choice of *where to go*
without buying the routing that would justify it; and the final choice among the
built loops is made on distance and repeated road with no scenery term (see
`_miss`), which is harmless at pref 1.0 where every candidate is pretty and is
not below it.

There is also a cache reason: `pref` is the one parameter that invalidates the
two cached passes, where the distance slider does not. So the loop tab should
pin pref at 1.0 and let the distance slider and the regenerate button be the
controls. Anyone who wants to expose it should sweep it first.

Nothing here changes the router or its objective. Every number above is at the
shipped `BETA` and `PREF_CURVE`. The distance target does quietly repair the
objective's known defect, though, and it is worth knowing why: at *fixed* total
km, minimising the router's `sum of km*(1 - score/10)` is exactly maximising
`sum of km*score`, because `sum of km` is a constant. The length-shrinking
pathology in `docs/scenery-cap-options.md` is a property of letting length float.
Here the slider pins it. Only at candidate selection, though, not inside the
search — which is why these loops reach far out and come back rather than
rambling in a circle.
"""

from dataclasses import dataclass, field as _dc_field
from datetime import date

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

# How much more expensive a road becomes on the way home once it has been driven
# on the way out. Measured at 3, 10 and infinity over three starts: all three
# gave 0% repeated road, so the retrace is bought at x3 and the rest is free.
# x3 is chosen because it stays closest to the requested distance (45.7 km
# against 50.4 km at a Petersham 40 km target) and because it degrades where a
# ban cannot: on the 17.2% of starts that are dead ends it still returns a loop.
PENALTY = 3.0

# Compass octants, from due north, clockwise. What the app's compass sets:
# eight loops built one per sector from a Needham start shared a median of 1% of
# their roads, so these really are different drives and not jitters of one.
SECTORS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")

# How far from the requested distance a candidate may sit and still be
# considered. Wider than the accuracy we ship, on purpose: the estimate below is
# exact for the *mirror* loop, but the penalised leg home is a different path and
# comes out anywhere from 13% short to 14% long, so the band has to be loose
# enough to contain the answer and the final choice is made on built lengths.
CANDIDATE_TOLERANCE = 0.10

# How many candidates spanning the band get built before one is kept. Each costs
# one Dijkstra home, capped (`_build`): about a quarter of a whole-graph search
# at 40 km. Measured error against the requested distance:
#
#     picks              1              3              5
#     worst error        +21%           -7%            +5%
#     worst repeated      --            5.0%           3.4%
#     mean repeated       --            1.7%           1.1%
#
# 5, and the second row is why. At 3 picks the slice holding the target can offer
# only a candidate that doubles back — at a Needham 40 km target it chose a
# 39.7 km loop repeating 2.0 km over a 43.2 km loop repeating none. Narrower
# slices fix that without touching the selection rule, which is the cheaper fix:
# weighting repeated road more heavily instead was measured and cost 14% of
# distance accuracy to save 0.4% of retrace.
#
# Do *not* try to converge by re-scaling the target from a built length instead —
# it jumps to a different candidate with a different stretch and oscillates
# (measured +5% to -19% on one Petersham target).
SPAN_PICKS = 5

# How many candidates a compass direction needs before it is worth offering.
#
# `SPAN_PICKS`, and not a round number, because that is the count `plan` needs to
# do its job: `_spread` takes one candidate from each of `SPAN_PICKS` slices
# across the band, so a direction holding fewer than that cannot fill the slices
# and silently degrades toward the picks=1 row of the table above — +21% on the
# requested distance — while the app advertises it like any other direction.
#
# At the extreme it is worse than inaccurate. Measured on the New England graph,
# a Boston start at 20 km has candidate counts of 1,422 north and **1**
# south-east: the harbour leaves exactly one loop that way, so the compass
# would offer a whole direction that returns the same drive every time. Massachusetts
# alone had zero there and the direction was correctly hidden; the wider graph
# turned "none" into "one", which reads as a real option and is not.
#
# `plan` applies the same cut to a requested sector, so a direction the app
# remembered from another length or start and that has since thinned out is
# refused like an empty one rather than served as one degraded drive.
MIN_SECTOR_CANDIDATES = SPAN_PICKS

# A turnaround closer than this makes a loop that leaves and returns along the
# same few metres of road, which no penalty can fix because there is nothing else
# there yet.
MIN_LEG_KM = 0.5

# The slider's ends. Not graph limits — the largest available loop is 516 km from
# Needham, 622 km from Petersham — but the range where the answer is a drive.
# The top was 200 km (about four hours) until 2026-10-05; 400 km is a full day.
# Measured from Needham, Petersham, Boston, Bar Harbor, Stowe and Provincetown
# at 300 and 400 km: built length within 4.3% of target, at most 3% doubled
# back, 8.2-9.0 h of driving at 400. The cost grows with length, because the
# searches are cut to what the length can reach: a median first loop costs
# about one whole-graph search at 40 km, five at 150 and eight at 300, where
# it was nine to ten at every length (docs/loop-speed.md). What does shrink is choice: at 400 km
# the same starts offer two to seven directions (Chatham 2, Provincetown 3,
# Boston and Needham 6, Gloucester 7).
MIN_TARGET_KM, MAX_TARGET_KM = 5.0, 400.0

# The two field passes run only over a disc around the start, not all of New
# England (docs/loop-speed.md). A candidate's way out and way home are each at
# most `target x (1 + CANDIDATE_TOLERANCE)` km of road, and a road is never
# shorter than the straight line between its ends, so both paths lie inside a
# disc of that radius. `DISC_SLACK` covers the gap between the graph's road
# lengths and this module's spherical distance: measured over every directed
# slot, a road is at most 0.09% shorter than the great circle between its ends.
DISC_SLACK = 0.01
EARTH_KM = 6371.0088

# A disc holding more than this share of the graph is not worth cutting out:
# with the extra search `_refine` may need, it costs more than the whole graph.
# Measured over twelve starts asking 150 km and then 300 km: the 300 km loop
# cost a median 4.8 searches with the cap at 0.6, 8.0 at 0.8 and 10.0 with no
# cap (docs/loop-speed.md).
DISC_MAX_SHARE = 0.6

# The field cache's ceiling in nodes searched, beside its count of entries. On
# a continent one 400 km loop's passes cover a few million nodes, a few hundred
# megabytes with their cost model, where New England's whole graph is 0.8M; four
# of those would be most of the box (docs/router-at-us-scale.md, "Memory").
FIELD_CACHE_NODES = 6_000_000

# A build's search home runs over the part of the disc between the turnaround
# and the start (`_home_near`) unless that part is more than this share of the
# disc, when the disc itself is searched.
HOME_REGION_SHARE = 0.5

# How many times `_fields` doubles a disc it cannot prove before keeping it.
# On New England the first doubling is nearly always the whole graph (see
# DISC_MAX_SHARE), so this only bites on a continent, where a whole-graph pass
# is 25 s and never an answer (docs/router-at-us-scale.md, "Loops").
DISC_WIDENINGS = 2

# The score at or above which a road counts as properly beautiful — see
# `router.BEAUTIFUL_SCORE`, which is where it now lives because point-to-point
# routes report the same number. Re-exported rather than moved outright, so
# `from looper import BEAUTIFUL_SCORE` keeps working for server/app.py.
from router import BEAUTIFUL_SCORE  # noqa: E402,F401
from router import (CORRIDOR_KM, CORRIDOR_SHARE, CORRIDOR_TOUCH,  # noqa: E402
                    CORRIDOR_WIDENINGS, SLOT_PRIVATE)
from compact import _ranges  # noqa: E402


@dataclass
class Loop:
    """One built loop: the route itself, plus what is loop-specific about it.

    `km`, `minutes` and `mean_score` are read off `route` rather than off the
    candidate estimate, so every number shown describes the line that is
    actually drawn. The estimate is a filter and is not reported.
    """

    route: object                       # router.RouteResult
    turnaround_idx: int
    turnaround: tuple                   # (lat, lon)
    sector: str
    target_km: float
    repeated_km: float
    beautiful_km: float

    @property
    def km(self):
        return self.route.km

    @property
    def minutes(self):
        return self.route.minutes

    @property
    def mean_score(self):
        return self.route.mean_score

    @property
    def repeated_fraction(self):
        """Share of the loop spent on a road it has already driven.

        Worth surfacing rather than hiding: it is the number that tells a user
        their 40 km drive is really a 20 km drive twice. Normally under 0.03. It
        goes high where the geography has no answer — a 5 km loop from a rural
        start comes back at 0.30, because within 2.5 km of the start there is
        only one road — and that is the cue to say so rather than to pretend.
        """
        return self.repeated_km / self.km if self.km else 0.0

    @property
    def error(self):
        """Signed fraction by which the built loop misses the request, or None
        when it was built directly rather than asked for (see `_build`)."""
        if not self.target_km:
            return None
        return (self.route.km - self.target_km) / self.target_km


@dataclass
class _CostModel:
    """Edge weights and per-node-pair lookups for one (pref, weights) setting.

    Over every pair of the graph (`pairs` None), which is what the whole-graph
    passes and the tests use, or over the pairs a disc touches (`pairs`, the
    graph's pair ids ascending, `at` maps into it). The whole graph's model is
    about 30 MB on the Massachusetts graph, 82 MB on New England's
    (docs/loop-lock-contention.md), and would be about 2 GB on the US, so a
    disc's passes are priced over the disc alone (docs/router-at-us-scale.md,
    "Loops").
    """

    metric: object              # router.Metric: the setting, priced on demand
    pair_w: np.ndarray          # per pair, the cheapest slot's Dijkstra weight
    pair_km: np.ndarray         # ...and that slot's road length, scenic-km, edge id
    pair_scen: np.ndarray
    pair_eidx: np.ndarray
    pairs: np.ndarray = None    # None: aligned to every pair of the graph
    # The whole graph's model only: per edge scores and per slot weights.
    scores: np.ndarray = None
    w_slot: np.ndarray = None

    def at(self, pairs):
        """Positions of graph pair ids in this model's arrays."""
        pairs = np.asarray(pairs, np.int64)
        return pairs if self.pairs is None else np.searchsorted(self.pairs, pairs)


@dataclass
class _Field:
    """One Dijkstra pass from (or to) the start, with km and scenic-km recovered.

    Held over the nodes it searched (`nodes`, ascending graph indices; every
    node for a pass over the whole graph), as `lcost`, `lkm`, `lscen` and
    `lpred`, the last in those local indices. `cost`, `km`, `scen`, `pred` and
    `exact` are the same spread over the whole graph's indices, built when
    asked for: they are what the tests compare against a whole-graph pass,
    and nothing that answers a request reads them.

    `km` and `scen` are meaningless where `cost` is infinite — an unreachable
    node self-loops in the predecessor tree and accumulates zero. Callers must
    mask on `np.isfinite(cost)`; `_Fields.reachable` does it once.
    """

    nodes: np.ndarray
    n: int
    lcost: np.ndarray
    lkm: np.ndarray
    lscen: np.ndarray
    lpred: np.ndarray
    # For a pass cut to a disc (`LoopPlanner._disc`), which nodes' cost and
    # path are provably the whole graph's; None for a pass over the whole
    # graph, where all are. `leave` is the cheapest way out of the disc, and
    # `refined` says `LoopPlanner._refine` has already run.
    lexact: np.ndarray = None
    leave: float = np.inf
    refined: bool = False

    @property
    def whole(self):
        return len(self.nodes) == self.n

    def local(self, idx):
        """Local indices of graph indices (all must be inside)."""
        idx = np.asarray(idx, np.int64)
        return idx if self.whole else np.searchsorted(self.nodes, idx)

    def _spread(self, values, fill):
        if self.whole:
            return values
        out = np.full(self.n, fill, dtype=values.dtype)
        out[self.nodes] = values
        return out

    @property
    def cost(self):
        return self._spread(self.lcost, np.inf)

    @property
    def km(self):
        return self._spread(self.lkm, 0.0)

    @property
    def scen(self):
        return self._spread(self.lscen, 0.0)

    @property
    def pred(self):
        if self.whole:
            return self.lpred
        out = np.full(self.n, -9999, dtype=self.lpred.dtype)
        seen = self.lpred >= 0
        out[self.nodes] = np.where(seen, self.nodes[np.maximum(self.lpred, 0)],
                                   self.lpred)
        return out

    @property
    def exact(self):
        return None if self.lexact is None else self._spread(self.lexact, False)


@dataclass
class _Disc:
    """The part of the graph near a start, as matrices for `_pass`.

    `nodes` are the whole graph's indices inside, ascending, and the disc's
    own index of a node is its position there. `fwd` and `rev` are (pair ids,
    column indices, row pointers) of the forward and transposed matrices over
    the pairs with both ends inside; `exit_fwd` and `exit_rev` are the pairs
    that leave the disc forward and enter it. `pairs` is every pair id any of
    those name, ascending: what a disc's cost model prices.

    Cut in time proportional to the disc, from the router's node grid and its
    forward and transposed pair rows, never by a pass over the graph.
    """

    nodes: np.ndarray
    fwd: tuple
    rev: tuple
    exit_fwd: np.ndarray
    exit_rev: np.ndarray
    pairs: np.ndarray
    # Where `fwd`'s, `rev`'s and the exits' pairs sit in `pairs`, found once.
    at: dict = None

    def position(self, cost, which):
        """Where the pairs of `which` ("fwd", "rev", "exit_fwd", "exit_rev")
        sit in `cost`'s arrays."""
        pairs = {"fwd": self.fwd[0], "rev": self.rev[0], "exit_fwd": self.exit_fwd,
                 "exit_rev": self.exit_rev}[which]
        if cost.pairs is None:
            return pairs
        if cost.pairs is self.pairs:
            return self.at[which]
        return cost.at(pairs)

    def arcs(self, tails, heads):
        """Positions in `fwd` of the arcs (tail, head), disc indices, all
        inside: read off the tail's own short row."""
        _, indices, indptr = self.fwd
        tails = np.asarray(tails, np.int64)
        heads = np.asarray(heads, np.int64)
        start = indptr[tails]
        count = indptr[tails + 1] - start
        out = np.full(len(tails), -1, np.int64)
        for k in range(int(count.max()) if len(count) else 0):
            live = np.flatnonzero((count > k) & (out < 0))
            if not len(live):
                break
            p = start[live] + k
            hit = indices[p] == heads[live]
            out[live[hit]] = p[hit]
        return out

    def local(self, idx):
        idx = np.atleast_1d(np.asarray(idx, np.int64))
        at = np.minimum(np.searchsorted(self.nodes, idx), len(self.nodes) - 1)
        return np.where(self.nodes[at] == idx, at, -1)

    def graph(self, pair_w, reverse: bool):
        """The matrix under `pair_w`, indexed by the graph's pair ids."""
        pairs, indices, indptr = self.rev if reverse else self.fwd
        m = len(self.nodes)
        return csr_matrix((pair_w[pairs], indices, indptr), shape=(m, m))

    def matrix(self, cost, reverse: bool, pair_w=None):
        """The matrix under a cost model, or under `pair_w` aligned with it."""
        w = cost.pair_w if pair_w is None else pair_w
        _, indices, indptr = self.rev if reverse else self.fwd
        m = len(self.nodes)
        at = self.position(cost, "rev" if reverse else "fwd")
        return csr_matrix((w[at], indices, indptr), shape=(m, m))


@dataclass
class _Fields:
    """The two cached passes for one (start, pref, weights). About 25 MB.

    Carries the `_CostModel` they were built from, so a loop built off these
    fields cannot be priced under different weights than the ones that chose the
    turnaround. Both passes run over the same nodes.
    """

    start: int
    cost: _CostModel
    out: _Field
    back: _Field
    # The loop length, in km of either leg, that the passes' disc was cut for;
    # infinite for passes over the whole graph. See `_serves`.
    reach_km: float = np.inf
    disc: _Disc = None
    lreachable: np.ndarray = _dc_field(default=None, repr=False)

    def __post_init__(self):
        self.lreachable = np.isfinite(self.out.lcost) & np.isfinite(self.back.lcost)

    @property
    def nodes(self):
        return self.out.nodes

    @property
    def lloop_km(self):
        """Estimated length of an out-and-back loop through each node.

        Exact for the mirror loop — verified against `route().km` to four
        decimals — and an estimate for the loop we actually build, because the
        penalised leg home is a different path. Good enough to filter on, not
        good enough to report.
        """
        return self.out.lkm + self.back.lkm

    @property
    def lloop_scen(self):
        return self.out.lscen + self.back.lscen

    # The same over the whole graph's indices, for the tests.
    @property
    def reachable(self):
        return self.out._spread(self.lreachable, False)

    @property
    def loop_km(self):
        return self.out._spread(self.lloop_km, 0.0)

    @property
    def loop_scen(self):
        return self.out._spread(self.lloop_scen, 0.0)


class LoopPlanner:
    """Builds scenic loops over an already-loaded `Router`.

    Holds no reference to the router's internals beyond what it reads, and
    changes nothing on it, so it is safe to construct alongside ordinary routing
    and to throw away.

    The two caches are sized for the serving box, not for a workstation: the
    process runs around 1 GB on a laptop behind a tunnel, and a field set is
    ~25 MB while a cost model is ~30 MB. Four starts and two settings is ~160 MB.
    Those are Massachusetts figures: on the New England graph a cost model is
    82 MB (docs/loop-lock-contention.md).
    Both are plain insertion-ordered dicts trimmed from the front, which is a
    true LRU only if callers touch entries by going through `plan`. They do.
    """

    def __init__(self, router, field_cache=4, cost_cache=2):
        self.router = router
        self._field_cache_size = field_cache
        self._cost_cache_size = cost_cache
        self._fields_by_key = {}
        self._costs_by_key = {}
        # How many field sets were cut to a disc, how many of those needed
        # `_refine`, how many still failed `_serves` and were redone over the
        # whole graph, and how many whole-graph field sets were built for any
        # reason (docs/loop-speed.md).
        self.disc_passes = 0
        self.disc_refines = 0
        self.disc_fallbacks = 0
        self.full_passes = 0
        # Every pair, ordered by head and then tail: the transpose's row
        # order, sorted once rather than per disc. 7 MB on New England.
        self._by_head = None

    # ------------------------------------------------------------------ public

    def sectors(self, start: int, target_km: float, pref: float = 1.0,
                weights: dict = None, avoid_unpaved: float = 1.0,
                on: date | None = None):
        """Which compass directions actually hold a loop of about this length.

        Returns `{sector: candidate count}` for the ones worth offering, which is
        what lets the app offer real directions instead of a blind shuffle. It
        must be asked rather than assumed: a Boston start has **zero** candidates
        due east at 20 km and zero north-east at 40 km — that is the harbour and
        the ocean — and a Petersham start has 9 south-west against 289
        north-west. Costs nothing beyond the cached passes.

        Thin directions are dropped, not just empty ones — see
        `MIN_SECTOR_CANDIDATES`. A direction holding one candidate is a button
        that returns the same drive on every press, and it cannot honour the
        distance slider either.
        """
        fields = self._fields(start, pref, weights, avoid_unpaved, on,
                              target_km=target_km)
        idx = self.candidates(fields, target_km)
        if not len(idx):
            return {}
        codes = self._sector_codes(fields.start, idx)
        counts = np.bincount(codes, minlength=len(SECTORS))
        return {SECTORS[i]: int(c) for i, c in enumerate(counts)
                if c >= MIN_SECTOR_CANDIDATES}

    def candidates(self, fields: _Fields, target_km: float,
                   tolerance: float = CANDIDATE_TOLERANCE,
                   sector: str = None, proven: bool = True):
        """Node indices that could be the turnaround of a loop of this length.

        The whole of step 2, and the reason the distance slider is free: this is
        array work over every node the passes searched, measured at 1.1 ms on
        a whole-graph field set.

        Only nodes both passes proved, on a disc (`_Field.lexact`), unless
        `proven` is False, which is how `_serves` asks whether any were not.
        A disc that `_fields` kept after it stopped widening can hold nodes it
        did not prove, and a turnaround among them could differ from the whole
        graph's.
        """
        km = fields.lloop_km
        # Never round on private road off the main public network
        # (`Router.private_inside`): the way there and back would be a
        # private road in the middle of the drive, which
        # `Router._weights` prices out of every route and a turnaround would
        # bring back in (docs/state-road-class.md, "Loops").
        ok = (fields.lreachable
              & ~self.router.private_inside[fields.nodes]
              & (np.abs(km - target_km) <= tolerance * target_km)
              & (fields.out.lkm >= MIN_LEG_KM))
        if proven and fields.out.lexact is not None:
            ok &= fields.out.lexact & fields.back.lexact
        idx = fields.nodes[np.where(ok)[0]]
        if sector is not None and len(idx):
            want = SECTORS.index(sector)
            idx = idx[self._sector_codes(fields.start, idx) == want]
        return idx

    def plan(self, start: int, target_km: float, pref: float = 1.0,
             weights: dict = None, sector: str = None,
             picks: int = SPAN_PICKS, penalty: float = PENALTY,
             avoid_unpaved: float = 1.0, on: date | None = None):
        """A scenic loop of about `target_km` from `start`, or None.

        None means the geography cannot answer — a rural start asked for a loop
        shorter than its road spacing allows. Callers should say so and offer the
        nearest length that works, rather than showing an error: at a Petersham
        start a 10 km request has only 21 candidates, and below about 15 km in
        open country there is genuinely nothing to return.

        `sector` is what the app's compass sets. Leave it None and the
        best-scoring direction wins. A sector holding fewer than
        `MIN_SECTOR_CANDIDATES` returns None, the same rule `sectors()` uses to
        decide what to offer.

        `on` is the request's date, and the roads closed for the season then
        are not driven (`Router._weights`). A loop needs no other handling: the
        candidates are whatever the open roads reach.

        Costs `picks` capped Dijkstras home, plus two passes over a disc the
        first time this start and setting are seen at this length or longer.
        About one whole-graph search in all at 40 km (docs/loop-speed.md).
        """
        target_km = float(np.clip(target_km, MIN_TARGET_KM, MAX_TARGET_KM))
        fields = self._fields(start, pref, weights, avoid_unpaved, on,
                              target_km=target_km)
        idx = self.candidates(fields, target_km, sector=sector)
        if not len(idx) or (sector is not None
                            and len(idx) < MIN_SECTOR_CANDIDATES):
            return None

        built = [loop for loop in
                 (self._build(fields, int(v), penalty)
                  for v in self._spread(fields, idx, target_km, picks))
                 if loop is not None]
        if not built:
            return None
        # Kept on built length and repeated road, not on estimated length and
        # never on score. Building more and keeping the *best-scoring* one was
        # measured and is worthless: 40 passes and six seconds buy 0.02 points
        # over one, because the top of the band is flat. Passes spent on getting
        # the distance right are the only ones that pay.
        best = min(built, key=lambda loop: _miss(loop, target_km))
        best.target_km = target_km
        return best

    def resume(self, src: int, via: int, dst: int, pref: float = 1.0,
               weights: dict = None, avoid_unpaved: float = 1.0,
               on: date | None = None):
        """A drive from `src` to `dst` that still goes round by way of `via`.

        What a loop's reroute needs, and it cannot be had from `route()`. A loop
        ends where it began, so a driver who misses a turn and asks for a route
        to their destination is asking for a route to the place they are trying
        to get away from — and gets the short way home, which deletes the rest of
        the drive. Measured on a 24 mi Needham loop, a missed turn two miles in
        would have replaced 22 remaining miles with about three.

        So until the driver has passed the far point of the loop, the replacement
        has to be pinned through it. Two Dijkstras rather than one, and no
        candidate filtering — the geography was already chosen when the loop was
        generated, and this is only the way back onto it.

        Returns a single `RouteResult`, so the caller cannot tell it was built
        from two searches and the turn-by-turn reads continuously across the
        waypoint.
        """
        metric = self.router.metric(round(float(pref), 4),
                                    dict(_weights_key(weights)),
                                    round(float(avoid_unpaved), 4), on)
        out = self._leg(metric, int(src), int(via))
        if out is None:
            return None
        # Threaded through whichever index of `via` the first leg actually
        # arrived at, not through the junction's original index. If `via` is a
        # junction split for turn restrictions, arriving on a restricted
        # approach lands on a copy whose exits are the legal ones — so
        # continuing from that copy is what keeps the second leg from taking a
        # turn the first leg's arrival forbids.
        for arrival in out:
            back = self._leg(metric, arrival[-1], int(dst))
            if back is not None:
                # The cheapest way home from here; unlike the waypoint, the end
                # of the route has nothing to continue into, so any arrival at
                # it will do and the first is the best.
                path = arrival + back[0][1:]
                return self.router._collect(path, metric, metric.scores)
        return None

    def _leg(self, metric, src: int, dst: int):
        """Node paths from `src` to `dst`, cheapest arrival first.

        A list rather than one path, because a split junction can be arrived at
        several ways and only the caller knows whether the cheapest one can be
        continued from. Searched in the leg's corridor, widened as
        `Router._cheapest` widens it (router.CORRIDOR_SHARE).
        """
        r = self.router
        ends = self._arrival_indices(dst)
        trip = r._trip(src, int(ends[0]))
        allowance = CORRIDOR_SHARE * trip.km + CORRIDOR_KM
        paths = None
        for attempt in range(CORRIDOR_WIDENINGS + 1):
            c = r.corridor(trip, trip.km + allowance)
            local_src = int(c.local(src)[0])
            dist, pred = dijkstra(c.matrix(c.price(metric)),
                                  directed=True, indices=local_src,
                                  return_predecessors=True)
            local = c.local(ends)
            local = local[local >= 0]
            local = local[np.isfinite(dist[local])]
            paths = []
            for end in local[np.argsort(dist[local])]:
                path = _tree_path(pred, local_src, int(end))
                if path is not None:
                    paths.append([int(v) for v in c.nodes[path]])
            if paths and trip.excess(paths[0]) <= CORRIDOR_TOUCH * allowance:
                return paths
            allowance *= 2.0
        return paths or None

    def nearest_length(self, start: int, target_km: float, pref: float = 1.0,
                       weights: dict = None, avoid_unpaved: float = 1.0,
                       on: date | None = None):
        """The closest loop length that has any candidate at all, or None.

        For the message shown when `plan` returns None. Needs passes over
        every node a loop up to MAX_TARGET_KM could use, because the nearest
        length that works can lie outside the disc `plan` searched: the whole
        graph when that disc would hold most of it, otherwise the disc for the
        longest loop, where only the nodes it proved count. Free when the
        cached passes already cover it, two searches when they do not
        (docs/loop-speed.md).
        """
        fields = self._fields(start, pref, weights, avoid_unpaved, on)
        ok = fields.lreachable & (fields.out.lkm >= MIN_LEG_KM)
        if fields.out.lexact is not None:
            ok &= fields.out.lexact & fields.back.lexact
        km = fields.lloop_km[ok]
        km = km[(km >= MIN_TARGET_KM) & (km <= MAX_TARGET_KM)]
        if not len(km):
            return None
        return float(km[np.argmin(np.abs(km - target_km))])

    # ----------------------------------------------------------------- picking

    def _spread(self, fields, idx, target_km, picks):
        """Best-ranked candidate from each of `picks` slices across the band.

        Spread across *length* rather than taking the top `picks` by score,
        because the band's job is distance accuracy — the scoring is flat across
        the top and the lengths are not. Ranking inside a slice is by estimated
        scenic-km per km, which is a good filter and a poor tie-breaker
        (Spearman +0.24 against built score at Needham, -0.21 at Petersham) —
        and it does not matter, because trusting rank 1 costs 0.01 points.
        """
        at = fields.out.local(idx)
        km = fields.lloop_km[at]
        rate = fields.lloop_scen[at] / np.maximum(km, 1e-9)
        lo = target_km * (1.0 - CANDIDATE_TOLERANCE)
        hi = target_km * (1.0 + CANDIDATE_TOLERANCE)
        out = []
        for a, b in zip(np.linspace(lo, hi, picks + 1)[:-1],
                        np.linspace(lo, hi, picks + 1)[1:]):
            inside = (km >= a) & (km < b)
            if inside.any():
                out.append(int(idx[np.where(inside)[0][np.argmax(rate[inside])]]))
        # A band narrower than one slice, or all candidates bunched at one
        # length, leaves nothing above. Fall back to the best-ranked candidate so
        # a legal request never returns empty for a bookkeeping reason.
        return out or [int(idx[np.argmax(rate)])]

    # ---------------------------------------------------------------- building

    def _build(self, fields, turnaround: int, penalty: float, widened: int = 0):
        """Out along the cached tree, home along a Dijkstra that avoids it.

        The penalty is applied to the *undirected* edge, not to the directed
        slot, which is the whole point: penalising one direction would leave the
        way home free to drive the same road backwards, which is the failure
        being fixed.
        """
        r = self.router
        cost = fields.cost
        out = fields.out
        local_out = _tree_path(out.lpred, int(out.local(fields.start)),
                               int(out.local(turnaround)))
        if local_out is None:
            return None
        out_path = [int(v) for v in out.nodes[local_out]]
        out_edges = self._path_edges(cost, out_path)

        # Re-collapse from slot level rather than scaling the per-pair weights
        # directly. Where two parallel roads join the same junctions and only one
        # was driven, only that one may be penalised, and the cheapest weight for
        # the pair may now belong to the other road.
        pair_w = self._retraced(cost, out_edges, penalty)

        # Capped at what the back field's own way home costs under these
        # penalised weights. That path is a legal drive home, so the cheapest
        # one costs no more and the cap cannot change the answer; it stops the
        # search settling the rest of New England (docs/loop-speed.md).
        limit = self._home_bound(fields, pair_w, turnaround)
        homes = self._arrival_indices(fields.start)
        if fields.disc is None:
            dist, pred = dijkstra(self._graph(pair_w), directed=True,
                                  indices=turnaround, return_predecessors=True,
                                  limit=limit)
            nodes = None
        else:
            # The part of the disc between the turnaround and the start first,
            # which is all a way home needs and a fraction of a long loop's
            # disc; the whole disc when that cannot prove its answer.
            found = self._home_near(fields, cost, pair_w, turnaround, homes, limit)
            if found is None or not found[3]:
                # Unproved, the way home it found is still a legal one, so
                # what it costs bounds the disc's search: exact, and it stops
                # the search about where the cheapest way home is.
                if found is not None and np.isfinite(found[4]):
                    limit = min(limit, found[4] * (1.0 + 1e-9) + 1e-9)
                found = self._home_in_disc(fields, cost, pair_w, turnaround,
                                           homes, limit)
            if found[3] is False and widened < DISC_WIDENINGS:
                # Not provably the whole graph's way home: the penalised way
                # home could leave the disc. Searched again wider, as the
                # passes are (`_wider`), and kept as found after that.
                return self._build(self._wider(fields), turnaround, penalty,
                                   widened + 1)
            dist, pred, nodes = found[:3]
            homes = homes[np.isin(homes, nodes)]

        # Closing the loop means *arriving* at the start, and a junction split for
        # turn restrictions stands at several indices — any of which is a legal
        # way to arrive, since a restriction forbids continuing through and a
        # route that ends here does not continue. Same rule `route()` applies to
        # a destination.
        at = homes if nodes is None else np.searchsorted(nodes, homes)
        reachable = at[np.isfinite(dist[at])]
        if not len(reachable):
            return None
        home = int(reachable[np.argmin(dist[reachable])])
        src = turnaround if nodes is None else int(np.searchsorted(nodes, turnaround))
        back = _tree_path(pred, src, home)
        if back is None:
            return None
        if nodes is not None:
            back = [int(v) for v in nodes[back]]

        path = out_path + back[1:]
        # The route is reported under the *real* weights, not the penalised ones:
        # the penalty shaped which roads were chosen and has no business in the
        # drawn geometry or the ETA. `_collect` uses them only to pick between
        # parallel roads on a hop, and `repeated_km` below would expose a
        # divergence as a road driven twice.
        if cost.w_slot is not None:
            route = r._collect(path, cost.w_slot, cost.scores)
        else:
            route = r._collect(path, cost.metric, cost.metric.scores)
        return Loop(
            route=route,
            turnaround_idx=turnaround,
            turnaround=self._latlon(turnaround),
            sector=SECTORS[int(self._sector_codes(fields.start,
                                                  np.array([turnaround]))[0])],
            target_km=0.0,          # set by `plan`, which knows what was asked
            repeated_km=_repeated_km(route),
            beautiful_km=route.beautiful_km,
        )

    def _retraced(self, cost, out_edges, penalty):
        """The cost model's pair weights with the roads already driven made
        `penalty` times dearer.

        Only the pairs those roads are on can change, so only they are
        re-collapsed from their slots: the same minimum over the same values
        as re-collapsing every slot of the graph, at the cost of the drive out
        rather than of the graph.
        """
        r = self.router
        pair_w = cost.pair_w.copy()
        edges = np.unique(np.asarray(out_edges, np.int64))
        if not len(edges):
            return pair_w
        slots = r._edge_order[_ranges(r._edge_start[edges],
                                      r._edge_start[edges + 1])].astype(np.int64)
        pairs = np.unique(r.slot_pair[slots]).astype(np.int64)
        if cost.pairs is not None:
            at = np.minimum(np.searchsorted(cost.pairs, pairs), len(cost.pairs) - 1)
            ok = cost.pairs[at] == pairs
            pairs, at = pairs[ok], at[ok]
        else:
            at = pairs
        start = r._pair_start[pairs].astype(np.int64)
        count = r._pair_start[pairs + 1] - start
        group = r._pair_slots[_ranges(start, start + count)].astype(np.int64)
        w = cost.metric(group)
        # Not on a private road, which a loop drives twice only when it starts
        # on one: scaling PRIVATE_ENTRY_MIN would make any other way back onto
        # it worth a detour of thousands of minutes (docs/state-road-class.md,
        # "Loops").
        hit = (np.isin(r.eidx[group], edges)
               & ((r._slot_flags[group] & SLOT_PRIVATE) == 0))
        w[hit] *= penalty
        pair_w[at] = np.minimum.reduceat(w, np.cumsum(count) - count)
        return pair_w

    def _home_near(self, fields, cost, pair_w, turnaround, homes, limit):
        """`_home_in_disc` over the part of the disc inside an ellipse about
        the turnaround and the start, the corridor a route between them would
        search (router.CORRIDOR_SHARE): (dist, pred, nodes, proved, best), or
        None when that is most of the disc anyway.

        Proved the same way: a way home that leaves this region must come
        back into it, at no less than an arc in plus the back field's bound on
        the rest. Measured on a 400 km loop from Philadelphia, the disc holds
        2.9M nodes and each build searched all of them.
        """
        r, disc, back = self.router, fields.disc, fields.back
        trip = r._trip(int(turnaround), int(fields.start))
        budget = trip.km + CORRIDOR_SHARE * trip.km + CORRIDOR_KM
        loc = disc.local(r._ellipse_nodes(trip, budget))
        loc = np.sort(loc[loc >= 0])
        if len(loc) > HOME_REGION_SHARE * len(disc.nodes):
            return None
        m = len(loc)
        mark = np.full(len(disc.nodes), -1, np.int64)
        mark[loc] = np.arange(m)
        _, f_indices, f_indptr = disc.fwd
        starts = f_indptr[loc]
        counts = f_indptr[loc + 1] - starts
        arcs = _ranges(starts, starts + counts)
        heads = mark[f_indices[arcs]]
        rows = np.repeat(np.arange(m), counts)
        inside = heads >= 0
        w_at = disc.position(cost, "fwd")[arcs]
        indptr = np.zeros(m + 1, np.int64)
        np.cumsum(np.bincount(rows[inside], minlength=m), out=indptr[1:])
        g = csr_matrix((pair_w[w_at[inside]], heads[inside].astype(np.int32), indptr),
                       shape=(m, m))
        src = int(mark[disc.local(turnaround)[0]])
        if src < 0:
            return None
        dist, pred = dijkstra(g, directed=True, indices=src,
                              return_predecessors=True, limit=limit)
        at = mark[disc.local(homes)]
        at = at[at >= 0]
        best = dist[at].min() if len(at) else np.inf
        # Leaving: to a disc node outside the region, or out of the disc.
        leave = (dist[rows[~inside]] + pair_w[w_at[~inside]]).min() if (~inside).any() \
            else np.inf
        ex = disc.exit_fwd
        if len(ex):
            tail = mark[disc.local(r.u_tail[ex])]
            ok = tail >= 0
            if ok.any():
                leave = min(leave, (dist[tail[ok]] + pair_w[
                    disc.position(cost, "exit_fwd")[ok]]).min())
        # Coming back in: from a disc node outside the region, or from
        # outside the disc, then the back field's bound to the start.
        to_start = np.minimum(back.lcost, back.leave)
        _, r_indices, r_indptr = disc.rev
        rstarts = r_indptr[loc]
        rarcs = _ranges(rstarts, r_indptr[loc + 1])
        rheads = np.repeat(loc, r_indptr[loc + 1] - rstarts)
        from_out = mark[r_indices[rarcs]] < 0
        come_back = ((cost.pair_w[disc.position(cost, "rev")[rarcs[from_out]]]
                      + to_start[rheads[from_out]]).min() if from_out.any() else np.inf)
        ex = disc.exit_rev
        if len(ex):
            head = disc.local(r.u_head[ex])
            ok = mark[head] >= 0
            if ok.any():
                come_back = min(come_back, (cost.pair_w[disc.position(cost, "exit_rev")[ok]]
                                            + to_start[head[ok]]).min())
        bound = leave + come_back
        proved = bool(best < bound or (not np.isfinite(best) and not bound <= limit))
        return dist, pred, disc.nodes[loc], proved, best

    def _home_in_disc(self, fields, cost, pair_w, turnaround, homes, limit):
        """`_build`'s search home over the fields' disc: (dist, pred, nodes,
        proved), `proved` False when the disc cannot show its way home is the
        whole graph's.

        A way home that leaves the disc must also come back into it. Leaving
        costs at least the cheapest arc out from a node the search reached;
        coming back costs at least the cheapest arc in plus the cheapest way
        from there to the start, which the back field already holds: exact
        where it proved the node, and never below its own `leave` where it did
        not. Weights here are the back field's times a penalty of at least 1,
        so neither bound can be too high. A way home cheaper than leaving plus
        coming back is the whole graph's.
        """
        disc, back = fields.disc, fields.back
        local = disc.local(turnaround)[0]
        dist, pred = dijkstra(disc.matrix(cost, False, pair_w), directed=True,
                              indices=int(local), return_predecessors=True,
                              limit=limit)
        at = disc.local(homes)
        at = at[at >= 0]
        best = dist[at].min() if len(at) else np.inf
        r = self.router
        out_ex, in_ex = disc.exit_fwd, disc.exit_rev
        leave = ((dist[disc.local(r.u_tail[out_ex])]
                  + pair_w[disc.position(cost, "exit_fwd")]).min()
                 if len(out_ex) else np.inf)
        if len(in_ex):
            heads = back.local(r.u_head[in_ex])
            to_start = np.minimum(back.lcost[heads], back.leave)
            come_back = (cost.pair_w[disc.position(cost, "exit_rev")] + to_start).min()
        else:
            come_back = np.inf
        bound = leave + come_back
        # Proved when the way home found is cheaper than any that leaves, or
        # when there is none and nothing that leaves is within the limit.
        proved = bool(best < bound or (not np.isfinite(best) and not bound <= limit))
        return dist, pred, disc.nodes, proved, best

    def _path_edges(self, cost, path):
        """Undirected edge ids for the hops of a node path."""
        hops = np.asarray(path, dtype=np.int64)
        pair = self.router._hop_pairs(hops[:-1], hops[1:])
        if (pair < 0).any():
            # Every hop came out of a Dijkstra over these same arrays, so this
            # cannot happen. Saying so loudly beats a silently short loop.
            raise RuntimeError("loop hop has no directed edge; graph index is "
                               "inconsistent")
        return cost.pair_eidx[cost.at(pair)]

    def _arrival_indices(self, node: int):
        copies = self.router.node_copies.get(node)
        if copies is None:
            return np.array([node], dtype=np.int64)
        return np.unique(np.asarray(copies, dtype=np.int64))

    def _graph(self, pair_w):
        """The forward graph under per-pair weights, without a COO sort.

        The pair arrays are already in CSR order (`Router._pair_indptr`), so
        this is the matrix `csr_matrix((pair_w, (u_tail, u_head)))` builds,
        neighbour order included, at a fifth of the cost: 0.013 of a search
        against 0.062 (docs/loop-speed.md). The whole graph's, so for a whole
        graph's cost model only.
        """
        r = self.router
        return csr_matrix((pair_w, r.u_head, r._pair_indptr), shape=(r.n, r.n))

    def _home_bound(self, fields, pair_w, turnaround: int):
        """What the back field's way home from `turnaround` costs under
        `pair_w`, a little rounded up; infinite if there is none.

        An upper bound on the cheapest way home under those weights, which is
        what makes it a safe `limit=` for `_build`'s search. Summed here in a
        different order from Dijkstra's running total, so it is padded by far
        more than the rounding either can carry.
        """
        r = self.router
        back = fields.back
        pred = back.lpred
        cur = int(back.local(turnaround))
        path = [cur]
        # On the transpose `pred[v]` is the next node after v on the way home,
        # and the back pass's roots are the start's arrival indices.
        while pred[cur] >= 0:
            cur = int(pred[cur])
            path.append(cur)
        path = back.nodes[np.asarray(path, np.int64)]
        if int(path[-1]) not in set(self._arrival_indices(fields.start).tolist()):
            return np.inf
        if len(path) < 2:
            return 0.0
        pair = r._hop_pairs(path[:-1], path[1:])
        if (pair < 0).any():
            return np.inf
        bound = float(pair_w[fields.cost.at(pair)].sum())
        return bound + 1e-9 * bound + 1e-9 if np.isfinite(bound) else np.inf

    # ------------------------------------------------------------------ fields

    def _fields(self, start: int, pref: float, weights: dict,
                avoid_unpaved: float = 1.0, on: date | None = None,
                target_km: float | None = None):
        """The two passes for this start and setting, cached.

        With `target_km`, the passes may be cut to a disc around the start
        that holds every candidate for that length (see `_serves`), which is
        what makes a loop cheap; without it, they cover every node a loop of
        MAX_TARGET_KM could use. Either way the candidates are exactly the
        ones a whole-graph pass gives (docs/loop-speed.md).
        """
        # `avoid_unpaved` is in the key for the same reason `pref` is: it moves
        # every edge weight, so a cached field set built under a different one
        # answers a question nobody asked. So is the closure version, or a
        # field set cached on Oct 14 would keep driving Lincoln Gap after it
        # closes on Oct 15. The version, not the date, so that the cache
        # survives every midnight that closes nothing new.
        #
        # The target is not in the key: a field set serves every target its
        # disc covers, so moving the distance slider down reuses it, and a
        # longer target replaces it with a wider one.
        key = (int(start), round(float(pref), 4), _weights_key(weights),
               round(float(avoid_unpaved), 4), self.router.closure_version(on))
        hit = self._fields_by_key.pop(key, None)
        if hit is not None:
            self._fields_by_key[key] = hit          # move to the warm end
            if self._serves(hit, target_km):
                return hit
        asked = MAX_TARGET_KM if target_km is None else target_km
        fields = None
        # A cached disc that already covers this length, and was refined, but
        # still cannot prove it would fail again cut the same; go straight to
        # a wider one.
        given_up = (hit is not None and np.isfinite(hit.reach_km)
                    and asked * (1.0 + CANDIDATE_TOLERANCE) <= hit.reach_km
                    and hit.out.refined)
        # Cut for exactly this target, with no headroom for the slider: a
        # wider disc costs every first loop more than it saves the next
        # distance up (docs/loop-speed.md).
        reach = float(asked) * (1.0 + CANDIDATE_TOLERANCE)
        scale = 2.0 if given_up else 1.0
        for attempt in range(DISC_WIDENINGS + 1):
            disc = self._disc(int(start), scale * reach * (1.0 + DISC_SLACK))
            if disc is None:
                fields = None
                break
            self.disc_passes += 1
            fields = self._disc_fields(key, int(start), disc, scale * reach, on)
            if not self._serves(fields, asked):
                # Both passes, even when one alone left a candidate
                # unproved: the disc is not kept, and a shorter target
                # reusing these passes may need the other.
                self.disc_refines += 1
                self._refine(fields.cost, fields.out, disc, reverse=False)
                self._refine(fields.cost, fields.back, disc, reverse=True)
            if self._serves(fields, asked):
                break
            # A disc twice as wide proves more, and is the whole graph once
            # it would hold most of it (DISC_MAX_SHARE), which on New England
            # it nearly always does. On a continent it never does, so after
            # DISC_WIDENINGS the last disc is kept and its unproved nodes are
            # left out of the candidates (`candidates`): a whole-graph pass is
            # never a request's fallback there.
            self.disc_fallbacks += 1
            scale *= 2.0
        if fields is None:
            self.full_passes += 1
            cost = self._cost(key[1], key[2], key[3], on)
            fields = _Fields(start=int(start), cost=cost,
                             out=self._pass(cost, int(start), reverse=False),
                             back=self._pass(cost, int(start), reverse=True))
        self._fields_by_key[key] = fields
        while len(self._fields_by_key) > self._field_cache_size or (
                len(self._fields_by_key) > 1
                and sum(len(f.nodes) for f in self._fields_by_key.values())
                > FIELD_CACHE_NODES):
            self._fields_by_key.pop(next(iter(self._fields_by_key)))
        return fields

    def _disc_fields(self, key, start, disc, reach, on):
        cost = self._disc_cost(disc, key[1], key[2], key[3], on)
        return _Fields(start=start, cost=cost,
                       out=self._pass(cost, start, False, disc),
                       back=self._pass(cost, start, True, disc),
                       reach_km=reach, disc=disc)

    def _wider(self, fields):
        """The same field set over a disc twice as wide, or the whole graph.

        For a loop build whose way home the disc could not prove: rare, and
        answered as `_fields` answers an unproved candidate."""
        if fields.disc is None:
            return fields
        reach = 2.0 * fields.reach_km
        disc = self._disc(int(fields.start), reach * (1.0 + DISC_SLACK))
        m = fields.cost.metric
        key = (int(fields.start), m.pref, _weights_key(m.weights),
               m.avoid_unpaved, None)
        if disc is None:
            cost = self._cost(key[1], key[2], key[3], m.on)
            return _Fields(start=fields.start, cost=cost,
                           out=self._pass(cost, fields.start, reverse=False),
                           back=self._pass(cost, fields.start, reverse=True))
        return self._disc_fields(key, int(fields.start), disc, reach, m.on)

    def _serves(self, fields, target_km):
        """Whether these passes give exactly the whole graph's candidates for
        `target_km` (None: for every length up to MAX_TARGET_KM).

        Always, for passes over the whole graph. For passes cut to a disc,
        two things must hold. The target must be one the disc was cut for:
        then every node that is a candidate on the whole graph has both legs
        inside the disc, so the disc finds it with the same cost and path.
        And every candidate the disc reports must be one both passes proved
        (`_Field.lexact`): no path through the rest of the graph could have
        been cheaper, so it is not a node whose whole-graph path leaves the
        disc and is longer than the band. A cost `limit=` alone could not
        promise either half, because candidates are chosen on km and the
        search runs on cost (docs/loop-speed.md).
        """
        if not np.isfinite(fields.reach_km):
            return True
        if target_km is None:
            return fields.reach_km >= MAX_TARGET_KM * (1.0 + CANDIDATE_TOLERANCE)
        if target_km * (1.0 + CANDIDATE_TOLERANCE) > fields.reach_km:
            return False
        idx = fields.out.local(self.candidates(fields, target_km, proven=False))
        return bool(fields.out.lexact[idx].all() and fields.back.lexact[idx].all())

    def _disc(self, start: int, radius_km: float):
        """The part of the graph within `radius_km` of the start, as a
        `_Disc`, or None when that is most of the graph anyway.

        Distance is the great circle between real junctions, so every copy of
        a split junction is in or out together with it. The candidates come
        off the router's node grid, so the cut costs what the disc holds.
        """
        r = self.router
        lat, lon = r.node_lat, r.node_lon
        origin = int(r.real_node[start])
        la0, lo0 = np.radians(lat[origin]), np.radians(lon[origin])
        theta = radius_km / EARTH_KM
        # A box that holds the spherical cap, to keep the trigonometry off
        # most of the graph.
        lat_edge = min(abs(la0) + theta, np.radians(89.0))
        half_lon = np.arcsin(min(1.0, np.sin(theta) / np.cos(lat_edge)))
        dlat, dlon = np.degrees(theta), np.degrees(half_lon)
        near = r.node_grid.box(lon[origin] - dlon - 1e-9, lat[origin] - dlat - 1e-9,
                               lon[origin] + dlon + 1e-9, lat[origin] + dlat + 1e-9,
                               unique=False)
        real = r.real_node[near]
        box = ((np.abs(lat[real] - lat[origin]) <= dlat)
               & (np.abs((lon[real] - lon[origin] + 180.0) % 360.0 - 180.0) <= dlon))
        near, real = near[box], real[box]
        la, lo = np.radians(lat[real]), np.radians(lon[real])
        h = (np.sin((la - la0) / 2.0) ** 2
             + np.cos(la0) * np.cos(la) * np.sin((lo - lo0) / 2.0) ** 2)
        nodes = np.sort(near[2.0 * np.arcsin(np.sqrt(np.minimum(h, 1.0))) <= theta])
        if len(nodes) > DISC_MAX_SHARE * r.n:
            return None
        m = len(nodes)
        scratch = r._scratch.take()
        try:
            scratch[nodes] = np.arange(m, dtype=np.int32)
            # Forward: each inside node's own row of the pair CSR, which is
            # the whole graph's neighbour order.
            starts = r._pair_indptr[nodes]
            counts = r._pair_indptr[nodes + 1] - starts
            fwd = _ranges(starts, starts + counts)
            head = scratch[r.u_head[fwd]]
            frow = np.repeat(np.arange(m), counts)
            # The pairs arriving from outside: each inside node's incoming
            # pairs whose tail is not inside.
            rstarts = r._rev_indptr[nodes]
            rcounts = r._rev_indptr[nodes + 1] - rstarts
            arriving = r._rev_pairs[_ranges(rstarts, rstarts + rcounts)].astype(np.int64)
            exit_rev = arriving[scratch[r.u_tail[arriving]] < 0]
        finally:
            scratch[nodes] = -1
            r._scratch.give(scratch)
        fin = head >= 0
        exit_fwd = fwd[~fin]
        fwd, frow, head = fwd[fin], frow[fin], head[fin]
        # Reverse: the inside pairs ordered by head and then by tail, which is
        # the stable sort on head scipy's transpose gives; on int32 numpy
        # sorts it by radix.
        order = np.argsort(head, kind="stable")
        rev, rrow, tail = fwd[order], head[order], frow[order]
        pairs, inverse = np.unique(np.concatenate([fwd, exit_fwd, exit_rev]),
                                   return_inverse=True)
        a, b = len(fwd), len(fwd) + len(exit_fwd)
        at = {"fwd": inverse[:a], "exit_fwd": inverse[a:b], "exit_rev": inverse[b:]}
        at["rev"] = at["fwd"][order]
        return _Disc(nodes=nodes,
                     fwd=_csr_parts(fwd, frow, head, m),
                     rev=_csr_parts(rev, rrow, tail, m),
                     exit_fwd=exit_fwd, exit_rev=exit_rev, pairs=pairs, at=at)

    def _pass(self, cost: _CostModel, start: int, reverse: bool, disc=None):
        """One Dijkstra, plus the km and scenic-km of every path it found.

        Reverse runs on the **transposed** graph, which gives the least-cost
        legal drive *to* the start rather than a mirror of the drive out. That
        distinction is not pedantic: the graph is directed and carries turn
        restrictions, and only 0.8% of nodes have a way home the same length as
        the way out (p5 of the difference is -6.4 km).

        It is also multi-sourced over the start's split copies, using scipy's
        `min_only` so that costs one pass and not one per copy.

        With a `disc`, the search and the accumulation run on the disc's nodes
        only, and `lexact` says which nodes it proved.
        """
        r = self.router
        sources = (self._arrival_indices(start) if reverse
                   else np.array([start], dtype=np.int64))
        if disc is None:
            if reverse:
                g = csr_matrix((cost.pair_w, (r.u_head, r.u_tail)),
                               shape=(r.n, r.n))
            else:
                g = self._graph(cost.pair_w)
            nodes = np.arange(r.n, dtype=np.int64)
        else:
            g = disc.matrix(cost, reverse)
            sources = disc.local(sources)
            nodes = disc.nodes
        if reverse:
            dist, pred, _ = dijkstra(g, directed=True, indices=sources,
                                     return_predecessors=True, min_only=True)
        else:
            dist, pred = dijkstra(g, directed=True, indices=int(sources[0]),
                                  return_predecessors=True)

        local = np.arange(len(dist), dtype=np.int64)
        seen = pred >= 0
        here, there = local[seen], pred[seen].astype(np.int64)
        # On the transpose, `pred[v]` is the next node *after* v on the way
        # home, so the arc that belongs to v is the original (v -> pred[v]).
        tails, heads = (here, there) if reverse else (there, here)
        if disc is None:
            pair = r._hop_pairs(tails, heads)
        else:
            pair = disc.arcs(tails, heads)
        if (pair < 0).any():
            raise RuntimeError("shortest-path tree holds an edge the pair index "
                               "does not; graph index is inconsistent")
        if disc is not None:
            pair = disc.position(cost, "fwd")[pair]

        # The root and every unreachable node point at themselves and carry zero,
        # so the accumulation below terminates and leaves them at zero.
        parent = np.where(seen, pred, local).astype(np.int64)
        edge_km = np.zeros(len(dist))
        edge_scen = np.zeros(len(dist))
        at = pair if disc is not None else cost.at(pair)
        edge_km[seen] = cost.pair_km[at]
        edge_scen[seen] = cost.pair_scen[at]
        km, scen = _accumulate(parent, edge_km, edge_scen)
        if disc is None:
            return _Field(nodes=nodes, n=r.n, lcost=dist, lkm=km, lscen=scen,
                          lpred=pred)
        # The cheapest way out of the disc: off a reached node inside, along
        # one arc to a node outside (on the transpose, along an arc arriving
        # from outside). Any path that leaves costs at least this, so a node
        # that costs less inside the disc costs the same on the whole graph,
        # by the same paths.
        if reverse:
            ex = disc.exit_rev
            leave = (dist[disc.local(r.u_head[ex])]
                     + cost.pair_w[disc.position(cost, "exit_rev")])
        else:
            ex = disc.exit_fwd
            leave = (dist[disc.local(r.u_tail[ex])]
                     + cost.pair_w[disc.position(cost, "exit_fwd")])
        leave = float(leave.min()) if len(leave) else np.inf
        return _Field(nodes=nodes, n=r.n, lcost=dist, lkm=km, lscen=scen,
                      lpred=pred, lexact=dist < leave, leave=leave)

    def _refine(self, cost: _CostModel, field: _Field, disc, reverse: bool):
        """Widen `field.lexact` to the nodes that leaving the disc and coming
        back could not undercut. One more search over the disc.

        `_pass` proves a node only when it costs less than leaving the disc
        at all. That fails on the few candidates whose cheapest way out turns
        onto a private road, which costs `router.PRIVATE_ENTRY_MIN` (10,000
        minutes) and outprices every way out of any disc. But a path that
        leaves and comes back must also re-enter: it costs at least the way
        out plus the cheapest way from an arc entering the disc to the node,
        inside it. That second term is one multi-source search, seeded at the
        entering arcs, and a node costing less than the sum is proved.

        On the transpose the same holds with the roles swapped: the way home
        from a node that leaves the disc costs at least the cheapest way,
        inside, from the node to an arc leaving it, plus the cheapest way
        back in to the start (`field.leave`).
        """
        r = self.router
        field.refined = True
        if not np.isfinite(field.leave):
            return
        ex = disc.exit_fwd if reverse else disc.exit_rev
        w = cost.pair_w[disc.position(cost, "exit_fwd" if reverse else "exit_rev")]
        at = disc.local(r.u_tail[ex] if reverse else r.u_head[ex])
        keep = np.isfinite(w)
        w, at = w[keep], at[keep]
        if not len(w):
            return
        # One arc from a virtual node to each seed, at the cheapest weight
        # entering it.
        order = np.lexsort((w, at))
        first = np.r_[True, at[order][1:] != at[order][:-1]]
        seeds, seed_w = at[order][first], w[order][first]
        pairs, indices, indptr = disc.rev if reverse else disc.fwd
        m = len(disc.nodes)
        at_pairs = disc.position(cost, "rev" if reverse else "fwd")
        g = csr_matrix((np.concatenate([cost.pair_w[at_pairs], seed_w]),
                        np.concatenate([indices, seeds.astype(indices.dtype)]),
                        np.append(indptr, indptr[-1] + len(seeds))),
                       shape=(m + 1, m + 1))
        back_in = dijkstra(g, directed=True, indices=m)[:m]
        field.lexact |= field.lcost < field.leave + back_in

    # -------------------------------------------------------------- cost model

    def _cost(self, pref: float, weights_key: tuple,
              avoid_unpaved: float = 1.0, on: date | None = None):
        """The whole graph's cost model for a setting, cached: for passes over
        the whole graph, which only a graph small enough for a disc to hold
        most of it ever runs."""
        r = self.router
        # The closure version is in the key for the reason given in `_fields`.
        key = weights_key + (pref, avoid_unpaved, r.closure_version(on))
        hit = self._costs_by_key.pop(key, None)
        if hit is not None:
            self._costs_by_key[key] = hit
            return hit
        scores = r._edge_scores(dict(weights_key))
        w_slot = r._weights(pref, scores, avoid_unpaved, on)
        pair_w = np.full(r.n_pairs, np.inf)
        np.minimum.at(pair_w, r.slot_pair, w_slot)
        # Which slot won each pair, so the km and score reported for a hop are
        # the road Dijkstra actually priced rather than an arbitrary parallel one.
        best = np.full(r.n_pairs, -1, dtype=np.int64)
        winners = np.where(w_slot == pair_w[r.slot_pair])[0]
        # Written descending so the *lowest* slot index survives, because
        # `Router._collect` settles the same tie with `argmin`, which also takes
        # the lowest. Two parallel ways between one pair of junctions can carry
        # bit-identical weights — `_apply_turn_restrictions` copies `d_minutes`
        # verbatim when it duplicates a slot — and when the two disagreed, this
        # module reported one road's km while `route()` drew the other's, and
        # the retrace penalty landed on the edge the return leg was not using.
        best[r.slot_pair[winners[::-1]]] = winners[::-1]
        edge = r.eidx[best]
        model = _CostModel(metric=r.metric(pref, dict(weights_key), avoid_unpaved,
                                           on),
                           pair_w=pair_w, pair_km=r.km[edge],
                           pair_scen=r.km[edge] * scores[edge], pair_eidx=edge,
                           scores=scores, w_slot=w_slot)
        self._costs_by_key[key] = model
        while len(self._costs_by_key) > self._cost_cache_size:
            self._costs_by_key.pop(next(iter(self._costs_by_key)))
        return model

    def _disc_cost(self, disc, pref, weights_key, avoid_unpaved, on):
        """`_cost` over the pairs a disc touches only: the same numbers for
        those pairs, priced in time proportional to the disc."""
        r = self.router
        metric = r.metric(pref, dict(weights_key), avoid_unpaved, on)
        pairs = disc.pairs
        start = r._pair_start[pairs].astype(np.int64)
        count = r._pair_start[pairs + 1] - start
        slots = r._pair_slots[_ranges(start, start + count)].astype(np.int64)
        slot_w = metric(slots)
        slot_start = np.cumsum(count) - count
        pair_w = np.minimum.reduceat(slot_w, slot_start)
        # The lowest slot reaching each pair's minimum, as `_cost` takes it:
        # a group's slots are in ascending order, so its first minimum.
        group = np.repeat(np.arange(len(pairs)), count)
        hit = np.flatnonzero(slot_w == pair_w[group])
        _, first = np.unique(group[hit], return_index=True)
        best = slots[hit[first]]
        edge = r.eidx[best].astype(np.int64)
        return _CostModel(metric=metric, pair_w=pair_w, pair_km=r.km[edge],
                          pair_scen=r.km[edge] * metric.scores(edge),
                          pair_eidx=edge, pairs=pairs)

    # ---------------------------------------------------------------- geometry

    def _latlon(self, node: int):
        real = int(self.router.real_node[node])
        return (float(self.router.node_lat[real]), float(self.router.node_lon[real]))

    def _sector_codes(self, start: int, nodes: np.ndarray):
        """Which compass octant each node sits in, seen from the start.

        A local flat-earth projection, which is ample: the answer is one of
        eight 45-degree buckets, and Massachusetts is 300 km across.
        """
        r = self.router
        lat, lon = r.node_lat, r.node_lon
        origin = int(r.real_node[start])
        real = r.real_node[np.asarray(nodes)]
        scale = np.cos(np.radians(lat[origin]))
        north = lat[real] - lat[origin]
        east = (lon[real] - lon[origin]) * scale
        bearing = (np.degrees(np.arctan2(east, north)) + 360.0) % 360.0
        # +22.5 so "N" spans -22.5..+22.5 rather than 0..45.
        return (((bearing + 22.5) % 360.0) / 45.0).astype(int)


# ------------------------------------------------------------- free functions

def _accumulate(parent, *edge_values):
    """Sum each edge value along every node's path to the root of a tree.

    The measured trick this module rests on. A shortest-path tree is handed back
    by `dijkstra` for free, and any quantity that sums along a path can be
    totalled up it by **pointer doubling**: repeatedly replace each node's parent
    by its grandparent while adding the two partial sums. After k rounds each
    node holds the sum over its nearest 2^k ancestors, so ~14 rounds of two
    gathers cover a road network's tree depth.

    Roots and unreachable nodes self-loop in `parent`, which makes them fixed
    points and lets the loop stop as soon as the parent array stops changing.
    Their edge value is forced to zero here rather than being required of the
    caller, because getting it wrong is silent and enormous: a root left holding
    a value of 1 comes back holding 2^32, and nothing about the number says
    where it came from.

    Exact, not approximate: it re-sums the same per-edge lengths `_collect`
    sums, and the km it produces matches `route().km` to four decimal places.
    That equality is the test worth writing first — see tests/test_loops.py.
    """
    A = parent.astype(np.int64).copy()
    totals = [np.asarray(v, dtype=np.float64).copy() for v in edge_values]
    rooted = A == np.arange(len(A))
    for t in totals:
        t[rooted] = 0.0
    for _ in range(32):
        nxt = A[A]
        for t in totals:
            t += t[A]
        if np.array_equal(nxt, A):
            break
        A = nxt
    return totals if len(totals) > 1 else totals[0]


def _csr_parts(pairs, rows, cols, m):
    """(pairs, column indices, row pointers) for arcs already sorted by row."""
    indptr = np.zeros(m + 1, dtype=np.int64)
    np.cumsum(np.bincount(rows, minlength=m), out=indptr[1:])
    return pairs, cols.astype(np.int32), indptr


def _tree_path(pred, start, node):
    """Node path start -> node, walking a forward predecessor tree."""
    out, cur = [], int(node)
    while cur != start:
        out.append(cur)
        cur = int(pred[cur])
        if cur < 0:
            return None
    out.append(start)
    out.reverse()
    return out


def _miss(loop, target_km):
    """How badly a built loop answers the request, in kilometres.

    Distance error and repeated road are added with equal weight because they
    are the same unit and the same complaint: a kilometre the driver did not ask
    for. That leaves no exchange rate to tune, and measurement says none is
    needed — at `SPAN_PICKS` slices the ranking barely moves between weighting
    repeated road at 1x and at 2x, and weighting it at 4x starts trading real
    distance accuracy away.
    """
    return abs(loop.route.km - target_km) + loop.repeated_km


def _repeated_km(route):
    """Kilometres of a loop spent on a road it has already driven.

    The loop-specific defect, and the number that tells a user their 40 km drive
    is really a 20 km drive twice. Taken off the built route's own edge rows, so
    it describes the line that gets drawn: `_collect` gathers those rows in
    travel order, so a road driven again appears twice and `duplicated()` marks
    every appearance after the first.
    """
    repeats = route.edges.index.duplicated()
    if not repeats.any():
        return 0.0
    return float(route.edges["length_m"].to_numpy()[repeats].sum() / 1000.0)


def _weights_key(weights):
    """A hashable, order-independent cache key for a beauty-weight dict."""
    return tuple(sorted((str(k), round(float(v), 4))
                        for k, v in (weights or {}).items()))
