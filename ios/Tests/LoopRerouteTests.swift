import CoreLocation
import XCTest
@testable import SundayDrive

/// Rerouting a loop, which is the one thing about driving a loop that is not
/// simply driving a route.
///
/// A loop ends where it began, so its `destination` is the driver's own
/// driveway. Ask the server for a route there and it correctly returns the short
/// way home — which deletes the rest of the drive. Measured against a real 24 mi
/// Needham loop, a missed turn two miles in would have swapped 22 remaining miles
/// for about three. These tests are what stop that coming back.
///
/// In its own file rather than in RerouteTests, so the two can be read (and
/// merged) independently.
@MainActor
final class LoopRerouteTests: XCTestCase {

    /// A loop as a straight fixture line: out 5 km north and back down the same
    /// line, so the far point is the 5 km mark and the drive is 10 km.
    ///
    /// Straight rather than a ring because the reroute logic only cares about
    /// distance along the line and proximity to the far point, and a fixture
    /// whose geometry can be read off by eye is worth more here than a realistic
    /// one.
    private func loopRoute(lengthMeters: Double = 10_000) -> RouteFeature {
        Fixture.straightRoute(lengthMeters: lengthMeters,
                              steps: [(0, "Head north on Test Road"),
                                      (lengthMeters / 2, "Turn around"),
                                      (lengthMeters, "Arrive back where you started")],
                              minutes: 20)
    }

    private var origin: CLLocationCoordinate2D { Fixture.origin }
    private var turnaround: CLLocationCoordinate2D { Fixture.north(5_000) }

    /// Counts which fetcher a drive reached for.
    ///
    /// A counter rather than `XCTFail` inside the stub, deliberately. A reroute
    /// is asynchronous, so a stub can fire after the test method has returned —
    /// and an `XCTFail` that lands then is reported against whichever test is
    /// running at the time. That is exactly what happened while writing these:
    /// a failure from here surfaced inside `RerouteIdentityTests`, blaming a
    /// test that had nothing to do with it.
    private final class Asked {
        var plain = 0
        var resume = 0
        var via: CLLocationCoordinate2D?
        var to: CLLocationCoordinate2D?
    }

    /// A loop drive, off-route recovery already armed.
    private func loopDrive(_ asked: Asked,
                           expectation: XCTestExpectation? = nil) -> NavigationModel {
        let nav = NavigationModel(route: loopRoute(), destination: origin,
                                  pref: 1.0, weights: [:], trace: nil,
                                  turnaround: turnaround)
        nav.fetchLoopResume = { [self] _, via, to, _, _, _ in
            asked.resume += 1
            asked.via = via
            asked.to = to
            expectation?.fulfill()
            return Fixture.response(fastest: loopRoute(), scenic: loopRoute())
        }
        nav.fetchRoute = { [self] _, to, _, _, _ in
            asked.plain += 1
            asked.to = to
            expectation?.fulfill()
            return Fixture.response(fastest: loopRoute(), scenic: loopRoute())
        }
        // Join the line so off-route recovery is live, the way every reroute
        // test here has to.
        nav.update(Fixture.fixAt(100))
        return nav
    }

    /// Drag the driver a long way sideways and let the guards run.
    private func goOffRoute(_ nav: NavigationModel, at meters: Double) {
        let away = CLLocationCoordinate2D(
            latitude: Fixture.north(meters).latitude,
            longitude: Fixture.origin.longitude + 0.02)   // ~1.6 km east
        nav.update(Fixture.fix(away))
    }

    // MARK: - Before the far point

    func test_a_loop_reroutes_through_its_far_point_and_not_straight_home() async {
        let asked = Asked()
        let expectation = expectation(description: "a replacement was fetched")
        let nav = loopDrive(asked, expectation: expectation)
        goOffRoute(nav, at: 2_000)
        await fulfillment(of: [expectation], timeout: 2)

        XCTAssertEqual(asked.resume, 1)
        XCTAssertEqual(asked.plain, 0, "a loop before its far point must not "
                       + "reroute straight home")
        XCTAssertEqual(asked.via?.latitude ?? 0, turnaround.latitude, accuracy: 0.0001)
        // Still going home in the end — the waypoint is a detour, not a new
        // destination.
        XCTAssertEqual(asked.to?.latitude ?? 0, origin.latitude, accuracy: 0.0001)
    }

    func test_the_far_point_is_not_yet_passed_two_kilometres_in() {
        let nav = loopDrive(Asked())
        nav.update(Fixture.fixAt(2_000))
        XCTAssertFalse(nav.passedTurnaround)
    }

    // MARK: - After the far point

    func test_once_past_the_far_point_a_loop_reroutes_home_like_any_trip() async {
        let asked = Asked()
        let expectation = expectation(description: "a replacement was fetched")
        let nav = loopDrive(asked, expectation: expectation)
        // Drive out to the far point and past it.
        nav.update(Fixture.fixAt(5_000))
        XCTAssertTrue(nav.passedTurnaround)

        goOffRoute(nav, at: 6_000)
        await fulfillment(of: [expectation], timeout: 2)
        XCTAssertEqual(asked.plain, 1)
        XCTAssertEqual(asked.resume, 0, "past the far point there is nothing "
                       + "left to pin through")
        XCTAssertEqual(asked.to?.latitude ?? 0, origin.latitude, accuracy: 0.0001)
    }

    func test_driving_near_the_far_point_counts_as_passing_it() {
        let nav = loopDrive(Asked())
        // Beside the far point but matched short of it on the line — which is
        // what a coarse fix on a real loop looks like.
        nav.update(Fixture.fix(CLLocationCoordinate2D(
            latitude: turnaround.latitude, longitude: turnaround.longitude + 0.0002)))
        XCTAssertTrue(nav.passedTurnaround)
    }

    func test_passing_the_far_point_never_un_latches() {
        let nav = loopDrive(Asked())
        nav.update(Fixture.fixAt(5_000))
        XCTAssertTrue(nav.passedTurnaround)
        // A fix that matches earlier on the line — GPS jitter, or the return leg
        // of a real loop running back beside the outbound one — must not put the
        // far point back in front of the driver.
        nav.update(Fixture.fixAt(4_000))
        XCTAssertTrue(nav.passedTurnaround)
    }

    // MARK: - An ordinary route is untouched

    func test_a_route_with_no_far_point_reroutes_exactly_as_before() async {
        let expectation = expectation(description: "plain reroute asked")
        let destination = Fixture.north(5_000)
        let asked = Asked()
        let nav = NavigationModel(route: Fixture.straightRoute(),
                                  destination: destination,
                                  pref: 1.0, weights: [:])
        nav.fetchLoopResume = { _, _, _, _, _, _ in
            asked.resume += 1
            throw RouteService.ServiceError.badResponse
        }
        nav.fetchRoute = { _, to, _, _, _ in
            asked.plain += 1
            asked.to = to
            expectation.fulfill()
            return Fixture.response(fastest: Fixture.straightRoute(),
                                    scenic: Fixture.straightRoute())
        }
        nav.update(Fixture.fixAt(100))
        goOffRoute(nav, at: 2_000)
        await fulfillment(of: [expectation], timeout: 2)
        XCTAssertEqual(asked.resume, 0, "a point-to-point trip has no waypoint "
                       + "to pin through")
        XCTAssertEqual(asked.to?.latitude ?? 0, destination.latitude, accuracy: 0.0001)
        XCTAssertFalse(nav.passedTurnaround)
    }

    // MARK: - The escape hatch

    // "Switch to fastest" before the far point. The driver is giving up the
    // rest of the loop, so the far point goes with it: measured on six 60 km
    // loops from 8 km in, the request pinned through it came back 47–73 km
    // against a fastest way home of 7–8 km.

    func test_switching_to_fastest_before_the_far_point_heads_home() async {
        let asked = Asked()
        let nav = loopDrive(asked)
        nav.update(Fixture.fixAt(2_000))
        XCTAssertTrue(nav.isLoopBeforeFarPoint)

        await nav.switchToFastest(from: Fixture.fixAt(2_000))

        XCTAssertEqual(asked.plain, 1, "the fastest way home is a plain route home")
        XCTAssertEqual(asked.resume, 0, "a driver who gave up the loop was sent "
                       + "to its far point by fast roads")
        XCTAssertEqual(asked.to?.latitude ?? 0, origin.latitude, accuracy: 0.0001)
        XCTAssertTrue(nav.followingFastest)
        XCTAssertFalse(nav.isLoopBeforeFarPoint)
    }

    func test_after_heading_home_a_missed_turn_still_heads_home() async {
        // Why the decision lives in `passedTurnaround` rather than in the one
        // request: skipping the waypoint only for `reason: "fastest"` sends
        // the driver home, and then the first off-route reroute reads
        // `loopWaypoint` again and drags them back out to the far point.
        let asked = Asked()
        let fetched = expectation(description: "the switch, then the missed turn")
        fetched.expectedFulfillmentCount = 2
        let nav = loopDrive(asked, expectation: fetched)
        var clock = Date()
        nav.now = { clock }
        nav.update(Fixture.fixAt(2_000))
        await nav.switchToFastest(from: Fixture.fixAt(2_000))
        XCTAssertEqual(asked.plain, 1)

        // Past the 45 s join grace and the 8 s cooldown, and well clear of
        // where the switch was asked from, so only the waypoint decides.
        clock = clock.addingTimeInterval(60)
        goOffRoute(nav, at: 3_000)
        await fulfillment(of: [fetched], timeout: 2)

        XCTAssertEqual(asked.plain, 2, "the missed turn should be routed home too")
        XCTAssertEqual(asked.resume, 0, "a missed turn after heading home sent the "
                       + "driver back out to the far point")
    }

    func test_a_switch_that_never_lands_puts_the_far_point_back() async {
        // The other half. A switch that failed declined nothing, so the loop
        // has to carry on as a loop: left passed, every later reroute would be
        // the short way home — the bug at the top of this file.
        let asked = Asked()
        let fetched = expectation(description: "the missed turn was fetched")
        let nav = loopDrive(asked, expectation: fetched)
        var clock = Date()
        nav.now = { clock }
        nav.fetchRoute = { _, _, _, _, _ in
            asked.plain += 1
            throw URLError(.timedOut)
        }
        nav.update(Fixture.fixAt(2_000))
        await nav.switchToFastest(from: Fixture.fixAt(2_000))

        XCTAssertEqual(asked.plain, 1, "the switch should have asked for the way home")
        XCTAssertFalse(nav.passedTurnaround, "a switch that never landed passed the far point")
        XCTAssertTrue(nav.isLoopBeforeFarPoint)
        XCTAssertFalse(nav.followingFastest)

        clock = clock.addingTimeInterval(20)        // past the 8 s cooldown
        goOffRoute(nav, at: 3_000)
        await fulfillment(of: [fetched], timeout: 2)

        XCTAssertEqual(asked.resume, 1, "the next missed turn should go through the far point")
        XCTAssertEqual(asked.plain, 1, "a failed switch turned the loop into the way home")
        XCTAssertEqual(asked.via?.latitude ?? 0, turnaround.latitude, accuracy: 0.0001)
    }

    func test_the_escape_hatch_says_home_only_where_it_goes_home() {
        let loop = loopDrive(Asked())
        let home = NavView.FastestPrompt(loopBeforeFarPoint: loop.isLoopBeforeFarPoint)
        XCTAssertEqual(home.title, "Head home the fastest way?")
        XCTAssertEqual(home.confirm, "Head home")
        XCTAssertEqual(home.label, "Head home the fastest way")

        // Past the far point a loop is heading home whatever happens, and an
        // ordinary trip has no far point: both keep the words they had.
        let unchanged = NavView.FastestPrompt(loopBeforeFarPoint: false)
        XCTAssertEqual(unchanged.title, "Switch to the fastest route?")
        XCTAssertEqual(unchanged.message, "This gives up the scenic route for the rest of the drive.")
        XCTAssertEqual(unchanged.confirm, "Switch to fastest")
        XCTAssertEqual(unchanged.label, "Switch to the fastest route")

        loop.update(Fixture.fixAt(5_000))
        XCTAssertEqual(NavView.FastestPrompt(loopBeforeFarPoint: loop.isLoopBeforeFarPoint),
                       unchanged)
        let trip = NavigationModel(route: Fixture.straightRoute(),
                                   destination: Fixture.north(5_000),
                                   pref: 1.0, weights: [:])
        XCTAssertFalse(trip.isLoopBeforeFarPoint)
    }

    // MARK: - Arrival

    /// A drive around a loop whose line actually closes.
    ///
    /// `loopRoute()` above is a straight line and is right for the reroute
    /// tests, which only care about distance along it and proximity to the far
    /// point. It is the wrong fixture for arrival: its last point is 10 km from
    /// its first, so a fix at the start leaves the whole route remaining
    /// however the match lands, and the assertion cannot fail.
    private func closedLoopDrive() -> NavigationModel {
        NavigationModel(route: Fixture.closedLoopRoute(), destination: origin,
                        pref: 1.0, weights: [:], trace: nil,
                        turnaround: Fixture.closedLoopTurnaround())
    }

    func test_the_closed_loop_fixture_really_closes() {
        // Guarding the guard: everything below is vacuous if it does not.
        let line = Fixture.closedLoopRoute().coordinates
        XCTAssertEqual(line.first!.latitude, line.last!.latitude, accuracy: 1e-12)
        XCTAssertEqual(line.first!.longitude, line.last!.longitude, accuracy: 1e-12)
    }

    func test_a_loop_does_not_announce_arrival_while_sitting_at_the_start() {
        // The case that makes a loop different: the driver begins the drive
        // within a few metres of the destination, with the whole loop ahead.
        // These fixes sit on the *return* leg — nearer the closing segment than
        // the opening one — which is what a car parked at the kerb looks like
        // and what used to match at 7,991 m of an 8,000 m loop.
        let nav = closedLoopDrive()
        nav.update(Fixture.fix(Fixture.offset(east: 8, north: 0)))
        nav.update(Fixture.fix(Fixture.offset(east: 3, north: 0)))
        XCTAssertFalse(nav.arrived, "arrival must be having driven the line, "
                       + "not standing next to the pin")
        XCTAssertFalse(nav.passedTurnaround, "the far point is 2 km away and the "
                       + "car has not moved")
    }

    func test_a_loop_announces_arrival_once_it_is_actually_driven() {
        let nav = closedLoopDrive()
        nav.update(Fixture.fix(Fixture.offset(east: 0, north: 100)))
        nav.update(Fixture.fix(Fixture.offset(east: 0, north: 2_000)))
        nav.update(Fixture.fix(Fixture.offset(east: 2_000, north: 2_000)))
        XCTAssertTrue(nav.passedTurnaround, "the far point has been driven through")
        nav.update(Fixture.fix(Fixture.offset(east: 2_000, north: 0)))
        nav.update(Fixture.fix(Fixture.offset(east: 20, north: 0)))
        XCTAssertTrue(nav.arrived)
    }
}
