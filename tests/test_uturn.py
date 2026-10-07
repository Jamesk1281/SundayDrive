"""At most one U-turn per departure: what "turns you around" means, and the
reroute that goes on ahead once a driver has declined one.

docs/reroute-uturn.md has the design and the replay of the recorded drives.
The geometry tests run anywhere; the rest need a built graph.
"""

from datetime import date

import numpy as np
import pytest
from pyproj import Transformer

import router as R
from router import CRS_METERS, turnaround_at

# A driver somewhere in Massachusetts, heading due north. Every shape below is
# laid out in metres east and north of them, so the geometry under test is the
# point of each case and not an accident of a real street.
DRIVER = (42.30, -71.50)
NORTH = 0.0
_TO_M = Transformer.from_crs(4326, CRS_METERS, always_xy=True)
_TO_LL = Transformer.from_crs(CRS_METERS, 4326, always_xy=True)
_X0, _Y0 = _TO_M.transform(DRIVER[1], DRIVER[0])


def route(*points_m):
    """A route as [lon, lat] points, from (east, north) metres off the driver."""
    lon, lat = _TO_LL.transform([_X0 + e for e, _ in points_m],
                                [_Y0 + n for _, n in points_m])
    return np.column_stack([lon, lat])


def turns(*points_m, heading=NORTH):
    return turnaround_at(route(*points_m), DRIVER, heading) is not None


class TestWhatTurnsYouAround:
    """The definition is geometric because the wording is not: the recorded
    drives say the same thing three ways (docs/reroute-uturn.md)."""

    def test_a_route_that_goes_on_ahead_does_not(self):
        assert not turns((0, 60), (0, 2000))

    def test_turning_round_at_the_junction_ahead_does(self):
        """"Make a U-turn on X": the route starts at the junction ahead, 60 m
        on, and comes straight back down the road past the car."""
        assert turns((0, 60), (0, -300), (400, -300))

    def test_turning_round_one_junction_on_does(self):
        """"Head north on X ... Make a U-turn to stay on X": 300 m ahead, then
        back down the other carriageway of a divided road, 15 m over. A rule
        reading only the first step, or only the words "U-turn", misses this;
        the recorded ones came back 304 to 632 m along."""
        assert turns((0, 60), (0, 360), (15, 360), (15, -200), (400, -200))

    def test_going_round_the_block_and_back_down_the_road_does(self):
        """Three rights and a left lands the driver heading back down the road
        they were on: the same instruction in different words."""
        assert turns((0, 40), (0, 100), (100, 100), (100, -150), (0, -150),
                     (0, -400))

    def test_a_road_that_bends_back_beside_the_car_does_not(self):
        """Heading back is not enough. A road curving through 180 degrees ahead
        heads back too; measured on a real one, it came back 95 m to the side
        of a driver who had done nothing but drive on."""
        assert not turns((0, 20), (0, 200), (50, 250), (95, 200), (95, -500))

    def test_crossing_behind_the_car_at_a_right_angle_does_not(self):
        """Through the strip, but across it: a different direction, not back."""
        assert not turns((0, 40), (0, 100), (60, 100), (60, -50), (-300, -50))

    def test_coming_back_past_the_car_only_after_the_window_does_not(self):
        """Back past the car, but 1,155 m along: by then the route has gone on
        ahead. TURN_BACK_WITHIN_M is the window, and it is cut at that
        distance exactly, not at the nearest vertex."""
        assert R.TURN_BACK_WITHIN_M < 1155
        assert not turns((0, 60), (0, 600), (15, 600), (15, -400))
        assert turns((0, 60), (0, 400), (15, 400), (15, -400))

    def test_it_is_measured_from_the_course_and_not_from_north(self):
        """The same U-turn, driven eastward."""
        assert turns((60, 0), (-300, 0), (-300, 400), heading=90.0)
        assert not turns((60, 0), (2000, 0), heading=90.0)

    def test_a_route_with_no_length_does_not(self):
        assert turnaround_at(route((0, 60)), DRIVER, NORTH) is None

    def test_it_says_where_the_route_starts_to_turn_back(self):
        """Where it enters the strip behind the driver, along the route: the
        app counts a U-turn as followed only once the driver is past it."""
        at_start = turnaround_at(route((0, 60), (0, -300)), DRIVER, NORTH)
        assert at_start == pytest.approx(60, abs=1)
        one_on = turnaround_at(route((0, 60), (0, 360), (15, 360), (15, -200)),
                               DRIVER, NORTH)
        assert one_on == pytest.approx(300 + 15 + 360, abs=1)


# --- On the graph -------------------------------------------------------------

# The drive of 2026-08-22 that `test_routing.py`'s "a reroute that must double
# back says so" pins: a car on Bedford Street doing 70 km/h north-west, with the
# destination behind it. The cheapest route turns it around.
BEDFORD_HERE, BEDFORD_COURSE = (42.479463, -71.255401), 322.0
BEDFORD_LOT = (42.484894, -71.264336)


def _ask(router, here, course, dest, pref=0.0, keep_ahead=False, **kw):
    s, _ = router.snap(*here, heading=course)
    t, _ = router.snap(*dest)
    return router.route(s, t, pref, heading=course, origin=here,
                        keep_ahead=keep_ahead, **kw)


class TestKeepingAhead:

    def test_the_cheapest_route_turns_the_driver_around(self, router):
        free = _ask(router, BEDFORD_HERE, BEDFORD_COURSE, BEDFORD_LOT)
        assert free.turns_around
        assert free.steps()[0]["modifier"] == "uturn"

    @pytest.mark.parametrize("pref", [0.0, 0.7])
    def test_after_a_declined_u_turn_the_route_goes_on_ahead(self, router, pref):
        """Both arms: the fastest goes through A*, the scenic one through the
        full Dijkstra, and a driver who taps "fastest" after declining a U-turn
        must not be handed it again on the fast roads."""
        free = _ask(router, BEDFORD_HERE, BEDFORD_COURSE, BEDFORD_LOT, pref=pref)
        ahead = _ask(router, BEDFORD_HERE, BEDFORD_COURSE, BEDFORD_LOT, pref=pref,
                     keep_ahead=True)
        assert not ahead.turns_around
        assert ahead.steps()[0]["modifier"] != "uturn"
        assert not any("U-turn" in s["instruction"] for s in ahead.steps()[:3])
        assert 0 <= ahead.minutes - free.minutes <= R.TURN_BACK_CAP_MIN

    def test_a_route_that_already_goes_on_ahead_is_left_alone(self, router):
        """`keep_ahead` only ever replaces a turnaround. Turned the other way,
        the same car's cheapest route is already ahead, and asking to keep
        ahead must hand back exactly that route."""
        course = (BEDFORD_COURSE + 180.0) % 360.0
        free = _ask(router, BEDFORD_HERE, course, BEDFORD_LOT)
        ahead = _ask(router, BEDFORD_HERE, course, BEDFORD_LOT, keep_ahead=True)
        assert not free.turns_around
        assert free.line.equals_exact(ahead.line, 0.0)

    def test_without_a_heading_nothing_is_judged_and_nothing_changes(self, router):
        """A parked car has no "behind". Planned from a standstill, a route
        never turns anyone around, and keeping ahead is a no-op."""
        s, _ = router.snap(*BEDFORD_HERE)
        t, _ = router.snap(*BEDFORD_LOT)
        free = router.route(s, t, 0.0, origin=BEDFORD_HERE)
        ahead = router.route(s, t, 0.0, origin=BEDFORD_HERE, keep_ahead=True)
        assert not free.turns_around
        assert free.line.equals_exact(ahead.line, 0.0)

    def test_going_on_past_the_cap_offers_the_u_turn_again(self, router, monkeypatch):
        """The cap is the escape from an absurd "ahead": on a divided highway
        it can be the next exit 15 km on. Past it the turnaround comes back,
        and still says it turns around, so the app keeps the driver's refusal."""
        monkeypatch.setattr(R, "TURN_BACK_CAP_MIN", 0.0)
        got = _ask(router, BEDFORD_HERE, BEDFORD_COURSE, BEDFORD_LOT,
                   keep_ahead=True)
        assert got.turns_around
        assert got.steps()[0]["modifier"] == "uturn"

    def test_the_answer_says_whether_it_turns_around(self, router):
        free = _ask(router, BEDFORD_HERE, BEDFORD_COURSE, BEDFORD_LOT)
        ahead = _ask(router, BEDFORD_HERE, BEDFORD_COURSE, BEDFORD_LOT,
                     keep_ahead=True)
        free_props = free.geojson()["properties"]
        ahead_props = ahead.geojson()["properties"]
        assert free_props["turns_around"] is True
        assert isinstance(free_props["turnaround_m"], int)
        assert 0 <= free_props["turnaround_m"] <= R.TURN_BACK_WITHIN_M
        assert ahead_props["turns_around"] is False
        assert ahead_props["turnaround_m"] is None
