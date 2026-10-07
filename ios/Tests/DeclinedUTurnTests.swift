import CoreLocation
import XCTest
@testable import SundayDrive

/// At most one U-turn per departure (docs/reroute-uturn.md).
///
/// The server answers each reroute from where the car is now, so a driver who
/// ignores "Make a U-turn" and keeps going is asked the same question from a
/// few hundred metres on, and usually told to turn around again: five times in
/// 103 seconds on one drive of 2026-10-06, one of them the driver's own
/// "switch to fastest". The app is the only party that knows a U-turn was
/// declined, so it has to say so. These drive that state — set, kept across
/// "fastest", cleared once the driver has taken a route — through the two
/// fetcher seams, and check which one each reroute used.
@MainActor
final class DeclinedUTurnTests: XCTestCase {

    /// The backend, answering at once from a queue, and noting whether each
    /// reroute was a plain request or one saying a U-turn had been declined.
    @MainActor
    final class Backend {
        private(set) var asked: [String] = []
        var replies: [RouteFeature] = []

        var plain: RouteFetcher { { [self] _, _, _, _, _ in try answer("plain") } }
        var keepingAhead: RouteFetcher { { [self] _, _, _, _, _ in try answer("ahead") } }

        private func answer(_ kind: String) throws -> RouteResponse {
            asked.append(kind)
            guard !replies.isEmpty else { throw URLError(.timedOut) }
            let next = replies.removeFirst()
            return Fixture.response(fastest: next, scenic: next)
        }
    }

    private var clock = Date()
    private func advance(_ seconds: TimeInterval) { clock = clock.addingTimeInterval(seconds) }

    /// A model on the straight fixture route north, joined at 500 m.
    private func driving(_ backend: Backend) -> NavigationModel {
        let model = NavigationModel(route: Fixture.straightRoute(),
                                    destination: Fixture.north(5000),
                                    pref: 0.8, weights: [:])
        model.now = { [unowned self] in self.clock }
        model.fetchRoute = backend.plain
        model.fetchRouteKeepingAhead = backend.keepingAhead
        model.update(Fixture.fixAt(500))
        XCTAssertTrue(model.hasJoinedRoute)
        return model
    }

    /// 300 m east of the road at `northing`: certainly off any line here.
    private func offRoad(_ northing: Double) -> CLLocation {
        Fixture.fix(Fixture.offset(east: 300, north: northing))
    }

    /// Leave the road at `northing`: two fixes off it in a row, a second's
    /// driving apart, since past 200 m one is a spike rather than a departure
    /// (drive simulation, Finding 2; docs/mid-drive-recovery.md).
    private func leave(_ model: NavigationModel, _ backend: Backend,
                       at northing: Double) async {
        await drive(model, backend, to: offRoad(northing - 15))
        await drive(model, backend, to: offRoad(northing))
    }

    private func waitFor(_ condition: @MainActor () -> Bool,
                         _ message: String = "condition never held",
                         file: StaticString = #filePath, line: UInt = #line) async {
        let deadline = Date().addingTimeInterval(2)
        while !condition() {
            if Date() > deadline { return XCTFail(message, file: file, line: line) }
            try? await Task.sleep(for: .milliseconds(2))
        }
    }

    /// Feed one fix and let any reroute it starts land.
    private func drive(_ model: NavigationModel, _ backend: Backend,
                       to fix: CLLocation) async {
        let before = backend.asked.count
        model.update(fix)
        try? await Task.sleep(for: .milliseconds(20))
        if backend.asked.count > before { await waitFor { !model.isRerouting } }
    }

    /// A replacement that turns the driver around, the way the server sends
    /// one: it begins at the junction 1,130 m up the road and runs back south
    /// over the road the car is on. `turnaroundM` nil is a backend that
    /// predates the field.
    private func uTurn(turnaroundM: Double? = 230) -> RouteFeature {
        Fixture.uTurnRoute(start: 1130, lengthMeters: 1530,
                           steps: [(0, "Make a U-turn on Test Road"),
                                   (600, "Turn right onto Cliff Street"),
                                   (1530, "Arrive at your destination")],
                           turnaroundM: turnaroundM)
    }

    /// A replacement that goes on ahead, starting at `start`.
    private func ahead(from start: Double) -> RouteFeature {
        Fixture.straightRoute(start: start, lengthMeters: 3000,
                              steps: [(0, "Head north on Test Road"),
                                      (3000, "Arrive at your destination")])
    }

    /// Off the road at 900 m, rerouted onto `turnaround`, back on the road
    /// under its return leg — and then on north, past the junction it turned
    /// around at, until the off-route check asks again from 1,400 m: the
    /// second fix in a row past 200 m beyond the end of that line.
    private func declineAUTurn(_ model: NavigationModel, _ backend: Backend,
                               _ turnaround: RouteFeature? = nil,
                               then reply: RouteFeature) async {
        backend.replies = [turnaround ?? uTurn()]
        await leave(model, backend, at: 900)
        XCTAssertEqual(backend.asked, ["plain"])
        XCTAssertEqual(model.currentInstruction, "Make a U-turn on Test Road")
        for northing in stride(from: 900.0, through: 1100.0, by: 50) {
            await drive(model, backend, to: Fixture.fixAt(northing))
        }
        advance(30)
        backend.replies = [reply]
        await drive(model, backend, to: Fixture.fixAt(1385))
        await drive(model, backend, to: Fixture.fixAt(1400))
    }

    // MARK: - Set

    func test_a_u_turn_left_untaken_makes_the_next_reroute_go_on_ahead() async {
        let backend = Backend()
        let model = driving(backend)
        XCTAssertFalse(model.declinedUTurn)
        await declineAUTurn(model, backend, then: ahead(from: 1500))
        XCTAssertEqual(backend.asked, ["plain", "ahead"],
                       "the reroute after a declined U-turn did not say so")
        XCTAssertTrue(model.declinedUTurn)
        XCTAssertEqual(model.currentInstruction, "Head north on Test Road")
    }

    func test_the_first_u_turn_of_a_departure_is_still_offered() async {
        // The rule is about the *second*: a driver who missed a turn 30 m back
        // is best told to turn around, and nothing has been declined yet.
        let backend = Backend()
        let model = driving(backend)
        backend.replies = [uTurn()]
        await leave(model, backend, at: 900)
        XCTAssertEqual(backend.asked, ["plain"])
        XCTAssertFalse(model.declinedUTurn)
    }

    func test_being_led_ahead_to_the_turnaround_is_not_taking_it() async {
        // The "Head north on X ... Make a U-turn to stay on X" form: the route
        // runs on ahead 300 m before turning the driver around, so a driver
        // who follows those 300 m and then carries on past has made plenty of
        // progress along it and taken none of the U-turn. Counting progress
        // from where they joined would have forgiven them.
        let backend = Backend()
        let model = driving(backend)
        backend.replies = [Fixture.uTurnAheadRoute(start: 1000, backMeters: 1200)]
        await leave(model, backend, at: 900)
        for northing in stride(from: 1000.0, through: 1250.0, by: 50) {
            await drive(model, backend, to: Fixture.fixAt(northing))
        }
        XCTAssertEqual(model.currentInstruction, "Make a U-turn to stay on Test Road")
        advance(30)
        backend.replies = [ahead(from: 1600)]
        for northing in stride(from: 1300.0, through: 1500.0, by: 50) {
            await drive(model, backend, to: Fixture.fixAt(northing))
        }
        XCTAssertEqual(backend.asked, ["plain", "ahead"])
        XCTAssertTrue(model.declinedUTurn)
    }

    func test_a_backend_that_never_says_a_route_turns_around_changes_nothing() async {
        // The deployed server predates `turnaround_m`. Its U-turns look like
        // any other route, so nothing is ever declined and every request is
        // the one the app always sent.
        let backend = Backend()
        let model = driving(backend)
        await declineAUTurn(model, backend, uTurn(turnaroundM: nil),
                            then: ahead(from: 1500))
        XCTAssertEqual(backend.asked, ["plain", "plain"])
        XCTAssertFalse(model.declinedUTurn)
    }

    // MARK: - Kept across "switch to fastest"

    func test_switching_to_fastest_instead_of_taking_the_u_turn_declines_it() async {
        // Seq 16 to 17 of `drive-2026-10-06-122558`: a U-turn, and the driver's
        // answer to it was to tap "fastest". That request U-turned too.
        let backend = Backend()
        let model = driving(backend)
        backend.replies = [uTurn()]
        await leave(model, backend, at: 900)
        for northing in stride(from: 900.0, through: 1050.0, by: 50) {
            await drive(model, backend, to: Fixture.fixAt(northing))
        }
        backend.replies = [ahead(from: 1200)]
        await model.switchToFastest(from: Fixture.fixAt(1100))
        XCTAssertEqual(backend.asked, ["plain", "ahead"])
        XCTAssertTrue(model.declinedUTurn)
        XCTAssertTrue(model.followingFastest)
    }

    func test_a_declined_u_turn_survives_switching_to_fastest() async {
        // `switchToFastest` resets the backoff — the driver has changed their
        // mind about how to get there — but not this. Where the car is going
        // has not changed, and the fast roads turn it around just the same.
        let backend = Backend()
        let model = driving(backend)
        await declineAUTurn(model, backend, then: ahead(from: 1500))
        backend.replies = [ahead(from: 1520)]
        await model.switchToFastest(from: Fixture.fixAt(1450))
        XCTAssertEqual(backend.asked, ["plain", "ahead", "ahead"])
        XCTAssertTrue(model.declinedUTurn)
    }

    func test_a_switch_to_fastest_that_fails_keeps_it_too() async {
        // A failed switch unwinds what it staked on the request. The driver
        // declining the U-turn was not staked on anything.
        let backend = Backend()
        let model = driving(backend)
        await declineAUTurn(model, backend, then: ahead(from: 1500))
        backend.replies = []
        await model.switchToFastest(from: Fixture.fixAt(1450))
        XCTAssertEqual(backend.asked, ["plain", "ahead", "ahead"])
        XCTAssertFalse(model.followingFastest)
        XCTAssertTrue(model.declinedUTurn)
    }

    // MARK: - Cleared

    func test_driving_the_route_ahead_ends_the_departure() async {
        let backend = Backend()
        let model = driving(backend)
        await declineAUTurn(model, backend, then: ahead(from: 1500))
        // Reaching the new line is not enough...
        await drive(model, backend, to: Fixture.fixAt(1500))
        await drive(model, backend, to: Fixture.fixAt(1550))
        XCTAssertTrue(model.declinedUTurn, "forgiven before the driver had taken the route")
        // ...driving 100 m along it is.
        await drive(model, backend, to: Fixture.fixAt(1610))
        XCTAssertFalse(model.declinedUTurn)

        // So the next departure is a fresh one, and its first U-turn is offered.
        advance(200)
        backend.replies = [ahead(from: 2400)]
        await leave(model, backend, at: 2300)
        XCTAssertEqual(backend.asked, ["plain", "ahead", "plain"])
    }

    func test_a_u_turn_the_driver_takes_is_not_declined() async {
        let backend = Backend()
        let model = driving(backend)
        backend.replies = [uTurn()]
        await leave(model, backend, at: 900)
        await drive(model, backend, to: Fixture.fixAt(900))
        // Turned round, and 120 m back down the road the route sent them.
        for northing in stride(from: 880.0, through: 780.0, by: -20) {
            await drive(model, backend, to: Fixture.fixAt(northing))
        }
        XCTAssertEqual(model.currentInstruction, "Turn right onto Cliff Street")
        advance(60)
        backend.replies = [ahead(from: 800)]
        await leave(model, backend, at: 700)
        XCTAssertEqual(backend.asked, ["plain", "plain"])
        XCTAssertFalse(model.declinedUTurn)
    }
}
