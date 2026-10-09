"""The loop planner's capped searches give exactly the uncapped answer.

Two caps, both in `looper.py` and both measured in docs/loop-speed.md:

- `_build`'s search home is limited to what the back field's own way home
  costs under the penalised weights, which cannot cut off the cheapest way
  home because that path is one way home;
- `_fields` runs its two passes over a disc around the start, proves which
  nodes the disc got right (`_Field.exact`, `_refine`), and falls back to the
  whole graph when a candidate is left unproved.

Neither may change a loop. So every test here compares against the same
planner made to search the whole graph, node for node, rather than against a
tolerance. The stratified 39-start version of this is
docs/loop-speed-study/exactness.py.

These need the built graph and skip without it, like tests/test_loops.py.
"""

from datetime import date

import numpy as np
import pytest
from scipy.sparse import csr_matrix

import looper
from looper import (CANDIDATE_TOLERANCE, DISC_SLACK, EARTH_KM, LoopPlanner,
                    _Fields)

ON = date(2026, 10, 8)
NEEDHAM = (42.2809, -71.2378)
STOWE = (44.4654, -72.6874)
PETERSHAM = (42.4879, -72.1889)
BAR_HARBOR = (44.3876, -68.2039)
MILLINOCKET = (45.6573, -68.7098)


@pytest.fixture(scope="module")
def whole(router):
    """A planner that never cuts a disc: today's searches, for comparison."""
    p = LoopPlanner(router)
    p._disc = lambda start, radius_km: None
    p._home_bound = lambda fields, pair_w, turnaround: np.inf
    return p


@pytest.fixture
def capped(router):
    return LoopPlanner(router)


def _sig(loop):
    if loop is None:
        return None
    r = loop.route
    return (loop.turnaround_idx, tuple(r.nodes), tuple(r.edges.index), r.km,
            r.minutes, r.mean_score, loop.repeated_km, loop.beautiful_km,
            loop.sector, loop.target_km)


class TestTheMatricesAreTheSameMatrices:
    """Neighbour order decides which of two equal-cost paths Dijkstra keeps,
    so a matrix built a cheaper way must be the same matrix, not an equal
    one."""

    def test_the_forward_graph_matches_the_coo_build(self, router, capped):
        w = capped._cost(1.0, (), 1.0, ON).pair_w
        want = csr_matrix((w, (router.u_tail, router.u_head)),
                          shape=(router.n, router.n))
        got = capped._graph(w)
        assert np.array_equal(got.indptr, want.indptr)
        assert np.array_equal(got.indices, want.indices)
        assert np.array_equal(got.data, want.data)

    @pytest.mark.parametrize("reverse", [False, True])
    def test_a_disc_is_the_whole_matrix_cut_down(self, router, capped,
                                                 reverse):
        w = capped._cost(1.0, (), 1.0, ON).pair_w
        start = router.snap(*NEEDHAM)[0]
        disc = capped._disc(start, 20.0)
        rows, cols = ((router.u_head, router.u_tail) if reverse
                      else (router.u_tail, router.u_head))
        full = csr_matrix((w, (rows, cols)), shape=(router.n, router.n))
        want = full[disc.nodes][:, disc.nodes]
        got = disc.graph(w, reverse)
        assert np.array_equal(got.indptr, want.indptr)
        assert np.array_equal(got.indices, want.indices)
        assert np.array_equal(got.data, want.data)


class TestTheDiscHoldsEveryCandidate:
    def test_no_road_is_shorter_than_the_straight_line_by_the_slack(self, router):
        """The disc's whole case: a path of at most K km of road stays
        within K of the start. True only if no road is shorter than the
        great circle between its ends by more than `DISC_SLACK`. Measured
        0.09% at worst."""
        lat = np.radians(router.nodes["lat"].to_numpy())
        lon = np.radians(router.nodes["lon"].to_numpy())
        a, b = router.real_node[router.tail], router.real_node[router.head]
        h = (np.sin((lat[b] - lat[a]) / 2) ** 2 + np.cos(lat[a]) * np.cos(lat[b])
             * np.sin((lon[b] - lon[a]) / 2) ** 2)
        straight = 2 * EARTH_KM * np.arcsin(np.sqrt(h))
        road = router.km[router.eidx]
        assert (straight <= road * (1.0 + DISC_SLACK / 2)).all()

    def test_every_copy_of_a_junction_is_in_or_out_together(self, router,
                                                           capped):
        start = router.snap(*NEEDHAM)[0]
        disc = capped._disc(start, 30.0)
        inside = np.zeros(router.n, bool)
        inside[disc.nodes] = True
        for v, copies in list(router.node_copies.items())[:5000]:
            assert inside[copies].all() or not inside[copies].any()

    def test_a_disc_holding_most_of_the_graph_is_not_cut(self, router, capped):
        start = router.snap(*NEEDHAM)[0]
        assert capped._disc(start, 2000.0) is None


class TestTheCappedFieldsAreTheWholeGraphs:
    @pytest.mark.parametrize("place,km", [
        (NEEDHAM, 40.0), (NEEDHAM, 10.0), (STOWE, 25.0), (PETERSHAM, 80.0),
        (BAR_HARBOR, 40.0)])
    def test_the_candidates_and_their_paths_match(self, router, capped,
                                                  whole, place, km):
        start = router.snap(*place)[0]
        cut = capped._fields(start, 1.0, {}, 1.0, ON, target_km=km)
        full = whole._fields(start, 1.0, {}, 1.0, ON)
        idx = whole.candidates(full, km)
        assert np.array_equal(capped.candidates(cut, km), idx)
        for a, b in ((cut.out, full.out), (cut.back, full.back)):
            for name in ("cost", "km", "scen", "pred"):
                assert np.array_equal(getattr(a, name)[idx],
                                      getattr(b, name)[idx]), name
        assert capped.sectors(start, km, on=ON) == \
            whole.sectors(start, km, on=ON)

    @pytest.mark.parametrize("place,km", [
        (NEEDHAM, 40.0), (STOWE, 10.0), (PETERSHAM, 25.0), (BAR_HARBOR, 80.0)])
    def test_the_loops_match(self, router, capped, whole, place, km):
        start = router.snap(*place)[0]
        for sector in (None, "N", "E", "S"):
            assert _sig(capped.plan(start, km, sector=sector, on=ON)) == \
                _sig(whole.plan(start, km, sector=sector, on=ON))

    def test_nothing_outside_the_disc_looks_like_a_turnaround(self, router,
                                                             capped):
        """Unreached nodes come back at 0 km. They must not be reachable,
        or a 0 km 'loop' could fall in a band near zero."""
        start = router.snap(*NEEDHAM)[0]
        f = capped._fields(start, 1.0, {}, 1.0, ON, target_km=10.0)
        assert np.isfinite(f.reach_km)
        unreached = ~np.isfinite(f.out.cost)
        assert unreached.sum() > 0.9 * router.n
        assert not f.reachable[unreached].any()
        assert not np.isin(capped.candidates(f, 10.0),
                           np.flatnonzero(unreached)).any()


class TestTheProof:
    def _cut(self, router, planner, place, km):
        start = router.snap(*place)[0]
        cost = planner._cost(1.0, (), 1.0, ON)
        reach = km * (1.0 + CANDIDATE_TOLERANCE)
        disc = planner._disc(start, reach * (1.0 + DISC_SLACK))
        fields = _Fields(start=start, cost=cost,
                         out=planner._pass(cost, start, False, disc),
                         back=planner._pass(cost, start, True, disc),
                         reach_km=reach)
        return cost, disc, fields

    def test_refining_proves_what_leaving_alone_cannot(self, router, capped,
                                                       whole):
        """The candidates whose way out turns onto a private road cost
        10,000 minutes, more than any way out of the disc. Leaving and
        re-entering costs more again, and `_refine` proves them."""
        for place, km in ((STOWE, 10.0), (NEEDHAM, 80.0), (PETERSHAM, 80.0)):
            cost, disc, f = self._cut(router, capped, place, km)
            idx = capped.candidates(f, km)
            if not f.out.exact[idx].all() or not f.back.exact[idx].all():
                break
        else:
            pytest.skip("no start here needs the refinement on this build")
        capped._refine(cost, f.out, disc, reverse=False)
        capped._refine(cost, f.back, disc, reverse=True)
        assert f.out.exact[idx].all() and f.back.exact[idx].all()
        full = whole._fields(f.start, 1.0, {}, 1.0, ON)
        assert np.array_equal(whole.candidates(full, km), idx)

    def test_a_disc_it_cannot_prove_falls_back_to_the_whole_graph(
            self, router, capped, whole):
        capped._refine = lambda cost, field, disc, reverse: None
        start = router.snap(*STOWE)[0]
        f = capped._fields(start, 1.0, {}, 1.0, ON, target_km=10.0)
        if capped.disc_fallbacks == 0:
            pytest.skip("Stowe at 10 km no longer needs the refinement")
        assert not np.isfinite(f.reach_km)
        assert _sig(capped.plan(start, 10.0, on=ON)) == \
            _sig(whole.plan(start, 10.0, on=ON))

    def test_the_exit_cost_is_a_lower_bound_on_leaving(self, router, capped):
        """Every node outside the disc costs at least `leave` on the whole
        graph: the definition the proof uses, checked directly."""
        cost, disc, f = self._cut(router, capped, NEEDHAM, 25.0)
        full = capped._pass(cost, f.start, reverse=False)
        outside = np.ones(router.n, bool)
        outside[disc.nodes] = False
        assert full.cost[outside].min() >= f.out.leave


class TestTheCache:
    def test_a_shorter_distance_reuses_the_disc(self, router, capped):
        start = router.snap(*NEEDHAM)[0]
        first = capped._fields(start, 1.0, {}, 1.0, ON, target_km=40.0)
        assert capped._fields(start, 1.0, {}, 1.0, ON,
                              target_km=25.0) is first

    def test_a_longer_distance_cuts_a_wider_one(self, router, capped):
        start = router.snap(*NEEDHAM)[0]
        first = capped._fields(start, 1.0, {}, 1.0, ON, target_km=25.0)
        if not np.isfinite(first.reach_km):
            pytest.skip("Needham at 25 km fell back to the whole graph")
        wider = capped._fields(start, 1.0, {}, 1.0, ON, target_km=40.0)
        assert wider is not first
        assert wider.reach_km >= 40.0 * (1.0 + CANDIDATE_TOLERANCE)
        assert len(capped._fields_by_key) == 1

    def test_the_whole_graph_serves_any_distance(self, router, capped):
        start = router.snap(*NEEDHAM)[0]
        full = capped._fields(start, 1.0, {}, 1.0, ON)
        assert capped._fields(start, 1.0, {}, 1.0, ON,
                              target_km=300.0) is full

    def test_the_nearest_length_hint_searches_the_whole_graph(
            self, router, capped, whole):
        """It looks for any length that works, inside the disc or not, so a
        cut field set must not answer it. Asked, as the app asks it, after a
        refused request: a compass direction too thin to offer."""
        start = router.snap(*MILLINOCKET)[0]
        if capped.plan(start, 10.0, sector="N", on=ON) is not None:
            pytest.skip("Millinocket has a 10 km loop north on this build")
        assert np.isfinite(capped._fields(start, 1.0, {}, 1.0, ON,
                                          target_km=10.0).reach_km)
        assert capped.nearest_length(start, 10.0, on=ON) == \
            whole.nearest_length(start, 10.0, on=ON)


class TestTheHomeLegCap:
    def test_capped_builds_match_uncapped(self, router, whole):
        capped = LoopPlanner(router)
        for place in (NEEDHAM, PETERSHAM):
            start = router.snap(*place)[0]
            fields = whole._fields(start, 1.0, {}, 1.0, ON)
            for km in (25.0, 80.0):
                idx = whole.candidates(fields, km)
                for v in whole._spread(fields, idx, km, looper.SPAN_PICKS):
                    assert _sig(capped._build(fields, v, looper.PENALTY)) == \
                        _sig(whole._build(fields, v, looper.PENALTY))

    def test_the_bound_is_the_back_fields_cost_when_nothing_is_penalised(
            self, router, capped):
        start = router.snap(*NEEDHAM)[0]
        fields = capped._fields(start, 1.0, {}, 1.0, ON)
        v = int(capped.candidates(fields, 40.0)[0])
        bound = capped._home_bound(fields, fields.cost.pair_w, v)
        assert bound == pytest.approx(fields.back.cost[v], rel=1e-8)
        assert bound >= fields.back.cost[v]
