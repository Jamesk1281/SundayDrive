import CoreLocation
import XCTest
@testable import SundayDrive

/// What the drive does when a reroute fails, when the car drives its own route
/// backwards, and when a loop's match could jump past its far point
/// (docs/mid-drive-recovery.md; the design is docs/mid-drive-recovery-plan.md,
/// sections 2–4).
///
/// Driven through the seams — `now`, the three fetchers and
/// `networkReachable` — on the straight fixture road north, so every clock in
/// the retry policy can be stepped rather than waited for.
@MainActor
final class MidDriveRecoveryTests: XCTestCase {

    // MARK: - Harness

    /// The backend: each request takes the next scripted answer, or the
    /// fallback once they run out, and is noted with which seam asked.
    @MainActor
    final class Backend {
        enum Answer {
            case route(RouteFeature)
            case fail(Error)
        }
        var answers: [Answer] = []
        var fallback: Answer = .fail(RouteService.ServiceError.offline)
        private(set) var asked: [(kind: String, heading: CLLocationDirection?,
                                  via: CLLocationCoordinate2D?, at: Date)] = []
        var clock: () -> Date = Date.init

        var plain: RouteFetcher {
            { [self] _, _, _, _, heading in try answer("plain", heading, nil) }
        }
        var keepingAhead: RouteFetcher {
            { [self] _, _, _, _, heading in try answer("ahead", heading, nil) }
        }
        var loopResume: LoopResumeFetcher {
            { [self] _, via, _, _, _, heading in try answer("via", heading, via) }
        }

        private func answer(_ kind: String, _ heading: CLLocationDirection?,
                            _ via: CLLocationCoordinate2D?) throws -> RouteResponse {
            asked.append((kind, heading, via, clock()))
            let next = answers.isEmpty ? fallback : answers.removeFirst()
            switch next {
            case .route(let feature): return Fixture.response(fastest: feature, scenic: feature)
            case .fail(let error): throw error
            }
        }
    }

    private var clock = Date(timeIntervalSince1970: 1_790_000_000)
    private var path = true
    private var speaker: VoiceGuideTests.FakeSpeaker!

    private func model(route: RouteFeature = Fixture.straightRoute(),
                       destination: CLLocationCoordinate2D = Fixture.north(5000),
                       turnaround: CLLocationCoordinate2D? = nil,
                       trace: DriveTrace? = nil,
                       _ backend: Backend) -> NavigationModel {
        speaker = VoiceGuideTests.FakeSpeaker()
        let model = NavigationModel(route: route, destination: destination,
                                    pref: 0.8, weights: [:], trace: trace,
                                    turnaround: turnaround,
                                    voice: VoiceGuide(speaker: speaker, muted: false))
        model.now = { [unowned self] in self.clock }
        backend.clock = { [unowned self] in self.clock }
        model.fetchRoute = backend.plain
        model.fetchRouteKeepingAhead = backend.keepingAhead
        model.fetchLoopResume = backend.loopResume
        model.networkReachable = { [unowned self] in self.path }
        return model
    }

    private func at(_ coordinate: CLLocationCoordinate2D, course: CLLocationDirection,
                    speed: CLLocationSpeed = 15, accuracy: Double = 5) -> CLLocation {
        CLLocation(coordinate: coordinate, altitude: 0, horizontalAccuracy: accuracy,
                   verticalAccuracy: 5, course: course, speed: speed, timestamp: clock)
    }

    /// One fix, a second after the last, and any reroute it starts allowed to
    /// land. The stubs never suspend, so a few yields settle it.
    private func feed(_ model: NavigationModel, _ fix: CLLocation) async {
        clock = clock.addingTimeInterval(1)
        model.update(fix)
        for _ in 0..<5 { await Task.yield() }
        var spins = 0
        while model.isRerouting && spins < 500 { await Task.yield(); spins += 1 }
    }

    /// Along the fixture road, 15 m a second, the way it runs or against it.
    private func drive(_ model: NavigationModel, from: Double, to: Double,
                       speed: CLLocationSpeed = 15, accuracy: Double = 5) async {
        let step = to >= from ? 15.0 : -15.0
        for m in stride(from: from, through: to, by: step) {
            await feed(model, at(Fixture.north(m), course: step > 0 ? 0 : 180,
                                 speed: speed, accuracy: accuracy))
        }
    }

    /// 400 m east of the road, heading north: off any line here, at a
    /// distance that prints as 0.2 mi.
    private func offRoad(_ northing: Double) -> CLLocation {
        at(Fixture.offset(east: 400, north: northing), course: 0)
    }

    /// Joined at the start, driven to 900 m, then two fixes off the road —
    /// the two a reroute past 200 m now needs.
    private func leaveTheRoute(_ model: NavigationModel) async {
        await drive(model, from: 0, to: 900)
        await feed(model, offRoad(915))
        await feed(model, offRoad(930))
    }

    /// Keep driving north off the road for `seconds`, one fix a second.
    private func stayOff(_ model: NavigationModel, from northing: Double,
                         seconds: Int) async -> Double {
        var n = northing
        for _ in 0..<seconds {
            n += 15
            await feed(model, offRoad(n))
        }
        return n
    }

    private func banner(_ model: NavigationModel) -> NavView.BannerText {
        NavView.bannerText(nav: model, location: LocationManager())
    }

    private var noConnectionSaid: Int {
        speaker.said.filter { $0 == "No connection. Head back to your route." }.count
    }

    private var turnAroundSaid: Int {
        speaker.said.filter { $0 == "Turn around when possible." }.count
    }

    // MARK: - A failed reroute, classified (plan, section 2)

    func test_each_failure_lands_in_its_banner_row() async {
        let noSignal = NavView.BannerText(symbol: "antenna.radiowaves.left.and.right.slash",
                                          alert: true, over: "No signal · route\u{00A0}0.2\u{00A0}mi\u{00A0}away",
                                          main: "Head back to your route")
        let noConnection = NavView.BannerText(symbol: "exclamationmark.icloud", alert: true,
                                              over: "No connection · route\u{00A0}0.2\u{00A0}mi\u{00A0}away",
                                              main: "Head back to your route")
        let offRoute = NavView.BannerText(symbol: "arrow.uturn.backward", alert: true,
                                          over: "Off route · route\u{00A0}0.2\u{00A0}mi\u{00A0}away",
                                          main: "Head back to your route")
        let cases: [(Error, Bool, NavView.BannerText, String)] = [
            (RouteService.ServiceError.offline, false, noSignal, "no path"),
            (RouteService.ServiceError.offline, true, noConnection, "a path that carried nothing"),
            (RouteService.ServiceError.unreachable(530), true, noConnection, "Cloudflare's 530"),
            (RouteService.ServiceError.unreachable(502), true, noConnection, "a 5xx"),
            (RouteService.ServiceError.badResponse, true, noConnection, "an undecodable reply"),
            (URLError(.timedOut), true, noConnection, "anything unforeseen"),
            (RouteService.ServiceError.server("no route found"), true, offRoute, "the server's no"),
        ]
        for (error, hasPath, expected, label) in cases {
            path = hasPath
            let backend = Backend()
            backend.fallback = .fail(error)
            let nav = model(backend)
            await leaveTheRoute(nav)
            XCTAssertEqual(backend.asked.count, 1, label)
            XCTAssertEqual(banner(nav), expected, label)
        }
    }

    func test_the_servers_no_is_shown_under_the_trip_card() async {
        let backend = Backend()
        backend.fallback = .fail(RouteService.ServiceError.server("closed for the season"))
        let nav = model(backend)
        await leaveTheRoute(nav)
        XCTAssertEqual(nav.actionProblem, "closed for the season")
        XCTAssertNil(nav.lostConnection, "the server answered, so the connection works")
        XCTAssertEqual(noConnectionSaid, 0, "nothing new is said for the server's no")
    }

    // MARK: - Two counters (plan, section 3.1)

    func test_network_failures_never_climb_the_backoff() async {
        // Four failed requests used to put the backoff at its 120 s cap, so the
        // reroute after the server came back waited up to two minutes more.
        // They are counted apart now: once a request lands, the next is due at
        // the 16 s of one unhelpful reply, not 120.
        let backend = Backend()
        backend.answers = Array(repeating: .fail(RouteService.ServiceError.unreachable(530)),
                                count: 4)
        let nav = model(backend)
        await leaveTheRoute(nav)
        var north = await stayOff(nav, from: 930, seconds: 110)
        XCTAssertEqual(backend.asked.count, 4, "15, 30 and 60 s after each failure")

        // The server is back, with a route the car never reaches.
        backend.answers = [.route(Fixture.straightRoute(start: 4500, lengthMeters: 3000))]
        backend.fallback = .route(Fixture.straightRoute(start: 6000, lengthMeters: 2000))
        north = await stayOff(nav, from: north, seconds: 70)
        XCTAssertEqual(backend.asked.count, 5)
        let landed = backend.asked[4].at
        north = await stayOff(nav, from: north, seconds: 60)
        XCTAssertGreaterThanOrEqual(backend.asked.count, 6)
        let next = backend.asked[5].at.timeIntervalSince(landed)
        // 45 s for the car to reach the replacement, which it never does, then
        // three fixes off it; well inside the old two minutes.
        XCTAssertLessThan(next, 60, "the failures climbed the backoff: next request after \(next) s")
        _ = north
    }

    func test_the_servers_no_climbs_the_backoff_and_is_not_held_for_a_path() async {
        // An unhelpful success: the server is up and asking again from a few
        // metres on gets the same answer. It backs off — 16 s after one — and
        // it is not a network failure, so a path monitor reporting no path
        // (which it would not, with a reply in hand) cannot hold it.
        path = false
        let backend = Backend()
        backend.fallback = .fail(RouteService.ServiceError.server("no route found"))
        let nav = model(backend)
        await leaveTheRoute(nav)
        let first = backend.asked[0].at
        _ = await stayOff(nav, from: 930, seconds: 20)
        XCTAssertEqual(backend.asked.count, 2)
        let gap = backend.asked[1].at.timeIntervalSince(first)
        XCTAssertGreaterThan(gap, 16)
        XCTAssertLessThanOrEqual(gap, 18)
    }

    // MARK: - When to try again (plan, section 3.1)

    func test_no_timer_retries_without_a_path_and_one_when_it_returns() async {
        path = false
        let backend = Backend()
        let nav = model(backend)
        await leaveTheRoute(nav)
        XCTAssertEqual(backend.asked.count, 1, "a request is always allowed to try")
        var north = await stayOff(nav, from: 930, seconds: 180)
        XCTAssertEqual(backend.asked.count, 1, "retried on a timer with no path")

        path = true
        nav.connectivityRestored()
        backend.answers = [.route(Fixture.straightRoute(start: north + 100, lengthMeters: 2000))]
        north += 15
        await feed(nav, offRoad(north))
        XCTAssertEqual(backend.asked.count, 2, "the first fix after the path returned asks")
        XCTAssertEqual(backend.asked[1].at, clock)
    }

    func test_a_car_that_waited_out_the_dead_zone_still_asks_when_the_path_returns() async {
        path = false
        let backend = Backend()
        let nav = model(backend)
        await leaveTheRoute(nav)
        for _ in 0..<60 { await feed(nav, offRoad(930)) }     // parked off the road
        path = true
        nav.connectivityRestored()
        await feed(nav, offRoad(930))
        XCTAssertEqual(backend.asked.count, 2,
                       "the movement guard held a retry the returning path asked for")
    }

    func test_with_a_path_retries_come_at_15_30_then_60_s() async {
        let backend = Backend()
        backend.fallback = .fail(RouteService.ServiceError.unreachable(530))
        let nav = model(backend)
        await leaveTheRoute(nav)
        _ = await stayOff(nav, from: 930, seconds: 200)
        let times = backend.asked.map { $0.at.timeIntervalSince(backend.asked[0].at) }
        XCTAssertEqual(times.count, 5, "\(times)")
        XCTAssertEqual(zip(times.dropFirst(), times).map { $0 - $1 }, [15, 30, 60, 60])
    }

    func test_a_restored_path_with_nothing_on_it_falls_back_to_the_timer() async {
        // "Satisfied" is not "working": a weak signal, a captive portal, our
        // server down. The path-restored retry is made once, and when it fails
        // too, the timer takes over.
        path = false
        let backend = Backend()
        let nav = model(backend)
        await leaveTheRoute(nav)
        path = true
        nav.connectivityRestored()
        var north = await stayOff(nav, from: 930, seconds: 1)
        XCTAssertEqual(backend.asked.count, 2)
        north = await stayOff(nav, from: north, seconds: 10)
        XCTAssertEqual(backend.asked.count, 2, "the restored path retried more than once")
        _ = await stayOff(nav, from: north, seconds: 60)
        XCTAssertEqual(backend.asked.count, 3)
    }

    // MARK: - Said once per episode (plan, section 2, rows 3–4)

    func test_no_connection_is_said_once_per_episode() async {
        let backend = Backend()
        backend.fallback = .fail(RouteService.ServiceError.unreachable(530))
        let nav = model(backend)
        await leaveTheRoute(nav)
        _ = await stayOff(nav, from: 930, seconds: 120)
        XCTAssertGreaterThan(backend.asked.count, 2)
        XCTAssertEqual(noConnectionSaid, 1)

        // Back on the road, which ends the episode, and the banner with it.
        await drive(nav, from: 2745, to: 3000)
        XCTAssertNil(nav.lostConnection)
        XCTAssertFalse(banner(nav).alert)

        // A new departure is a new episode.
        clock = clock.addingTimeInterval(10)
        await feed(nav, offRoad(3015))
        await feed(nav, offRoad(3030))
        XCTAssertEqual(noConnectionSaid, 2)
    }

    // MARK: - "Switch to fastest" with no connection (plan, section 2, row 10)

    func test_a_fastest_switch_with_no_connection_says_so_and_changes_nothing_else() async {
        path = false
        let backend = Backend()
        let nav = model(backend)
        await drive(nav, from: 0, to: 600)
        await nav.switchToFastest(from: at(Fixture.north(600), course: 0))
        XCTAssertEqual(nav.actionProblem, "Can't switch — no connection.")
        XCTAssertNil(nav.lostConnection, "a failed tap is not an off-route state")
        XCTAssertFalse(nav.followingFastest)
        XCTAssertEqual(noConnectionSaid, 0)
        XCTAssertEqual(banner(nav).main, "Turn right onto Elm Street")
    }

    // MARK: - Every attempt in the trace

    private var folder: URL!

    override func tearDownWithError() throws {
        if let folder { try? FileManager.default.removeItem(at: folder) }
        try super.tearDownWithError()
    }

    private func newTrace() -> DriveTrace? {
        folder = FileManager.default.temporaryDirectory
            .appendingPathComponent("recovery-trace-\(UUID().uuidString)")
        return DriveTrace(origin: Fixture.origin, destination: Fixture.north(5000),
                          pref: 0.8, weights: [:], directory: folder)
    }

    private func reroutes(in trace: DriveTrace) -> [[String: Any]] {
        let text = (try? String(contentsOf: trace.url, encoding: .utf8)) ?? ""
        return text.split(separator: "\n").compactMap {
            try? JSONSerialization.jsonObject(with: Data($0.utf8)) as? [String: Any]
        }.filter { $0["t"] as? String == "reroute" }
    }

    func test_every_reroute_attempt_is_recorded_failures_included() async throws {
        let trace = try XCTUnwrap(newTrace())
        path = false
        let backend = Backend()
        backend.answers = [
            .fail(RouteService.ServiceError.offline),
            .fail(RouteService.ServiceError.unreachable(530)),
            .fail(RouteService.ServiceError.server("no route found")),
            .route(Fixture.straightRoute()),                                  // the same line
            .route(Fixture.straightRoute(start: 5000, lengthMeters: 3000)),   // a new one
        ]
        let nav = model(trace: trace, backend)
        await leaveTheRoute(nav)
        var north = await stayOff(nav, from: 930, seconds: 5)     // no path: no timer
        path = true
        nav.connectivityRestored()
        north = await stayOff(nav, from: north, seconds: 1)       // the 530
        north = await stayOff(nav, from: north, seconds: 30)      // the server's no, 30 s on
        north = await stayOff(nav, from: north, seconds: 17)      // merged, past its 16 s
        north = await stayOff(nav, from: north, seconds: 50)      // adopted, after the merge's grace
        nav.finish()

        let records = reroutes(in: trace)
        XCTAssertEqual(records.map { $0["outcome"] as? String },
                       ["failed", "failed", "failed", "merged", "adopted"])
        XCTAssertEqual(records.map { $0["error_class"] as? String },
                       ["offline", "unreachable", "server", nil, nil])
        XCTAssertEqual(records.map { $0["path"] as? Bool }, [false, true, true, nil, nil])
        XCTAssertEqual(records[1]["status"] as? Int, 530)
        XCTAssertEqual(records[2]["message"] as? String, "no route found")
        for record in records {
            XCTAssertEqual(record["reason"] as? String, "offroute")
            XCTAssertNotNil(record["ts"] as? Double)
            XCTAssertNotNil(record["req_lat"] as? Double)
            XCTAssertNotNil(record["req_lon"] as? Double)
            XCTAssertEqual(record["req_heading"] as? Double, 0)
            XCTAssertNotNil(record["elapsed_s"] as? Double)
        }
        _ = north
    }

    func test_a_superseded_attempt_is_recorded_and_nothing_follows_the_end() async throws {
        let trace = try XCTUnwrap(newTrace())
        let backend = RerouteTests.Backend()
        let nav = NavigationModel(route: Fixture.straightRoute(), destination: Fixture.north(5000),
                                  pref: 0.8, weights: [:], trace: trace)
        nav.now = { [unowned self] in self.clock }
        nav.fetchRoute = backend.fetch
        await drive(nav, from: 0, to: 900)
        nav.update(offRoad(915))
        nav.update(offRoad(930))                                // request 0, held
        try await Task.sleep(for: .milliseconds(20))
        Task { await nav.switchToFastest(from: offRoad(930)) }  // request 1 supersedes it
        try await Task.sleep(for: .milliseconds(20))
        let line = Fixture.straightRoute(start: 1000, lengthMeters: 4000)
        backend.reply(0, with: Fixture.response(fastest: line, scenic: line))
        try await Task.sleep(for: .milliseconds(20))
        // The car reaches the end while request 1 is in the air.
        nav.update(Fixture.fixAt(4990))
        XCTAssertTrue(nav.arrived)
        backend.reply(1, with: Fixture.response(fastest: line, scenic: line))
        try await Task.sleep(for: .milliseconds(20))

        // The arrival closed the file, so the attempt it ended is not
        // written: `end` is the terminator.
        let records = reroutes(in: trace)
        XCTAssertEqual(records.map { $0["outcome"] as? String }, ["superseded"])
        XCTAssertEqual(records.map { $0["reason"] as? String }, ["offroute"])
        let text = try String(contentsOf: trace.url, encoding: .utf8)
        let last = text.split(separator: "\n").last.map(String.init) ?? ""
        XCTAssertTrue(last.contains("\"t\":\"end\""), "something was written after the end")
    }

    // MARK: - Two consecutive fixes past 200 m (drive simulation, Finding 2)

    func test_one_spike_past_200_m_does_not_reroute_and_two_in_a_row_do() async {
        let backend = Backend()
        backend.fallback = .route(Fixture.straightRoute(start: 1500, lengthMeters: 3500))
        let nav = model(backend)
        await drive(nav, from: 0, to: 900)
        await feed(nav, offRoad(915))                       // a spike
        await drive(nav, from: 930, to: 990)
        XCTAssertTrue(backend.asked.isEmpty, "one spike rerouted the driver")

        await feed(nav, offRoad(1005))
        XCTAssertTrue(backend.asked.isEmpty)
        await feed(nav, offRoad(1020))
        XCTAssertEqual(backend.asked.count, 1, "a real departure waits one fix, not three")
    }

    // MARK: - A fix's own error bar (drive simulation, Finding 3)

    func test_a_fix_whose_error_covers_the_gap_is_not_evidence_of_leaving() async {
        let backend = Backend()
        backend.fallback = .route(Fixture.straightRoute(start: 1500, lengthMeters: 3500))
        let nav = model(backend)
        await drive(nav, from: 0, to: 900)
        // 75 m out at a stated 20 m: within 60 + 20 of the road.
        for n in stride(from: 915.0, through: 1035, by: 15) {
            await feed(nav, at(Fixture.offset(east: 75, north: n), course: 0, accuracy: 20))
        }
        XCTAssertTrue(backend.asked.isEmpty, "multipath rerouted a car on its road")
        XCTAssertFalse(nav.isOffTheLine, "and told it to head back to a road it was on")

        // The same offset at a stated 10 m is past 60 + 10: three of those.
        for n in stride(from: 1050.0, through: 1080, by: 15) {
            await feed(nav, at(Fixture.offset(east: 75, north: n), course: 0, accuracy: 10))
        }
        XCTAssertEqual(backend.asked.count, 1)
    }

    // MARK: - The wrong-way detector (plan, section 4.2)

    func test_reversed_after_driving_forward_it_fires_on_the_fifth_fix_and_asks_at_once() async {
        let backend = Backend()
        let nav = model(backend)
        await drive(nav, from: 0, to: 1500)
        await drive(nav, from: 1485, to: 1440)                 // four fixes back
        XCTAssertFalse(nav.wrongWay)
        XCTAssertTrue(backend.asked.isEmpty)
        await feed(nav, at(Fixture.north(1425), course: 180))    // the fifth, 60 m of line
        XCTAssertTrue(nav.wrongWay)
        XCTAssertEqual(backend.asked.count, 1, "asked on the fix that detected it")
        XCTAssertEqual(backend.asked.first?.heading, 180, "with the heading")
        XCTAssertEqual(turnAroundSaid, 1)
    }

    func test_the_wrong_way_banner_and_its_failures() async {
        for (hasPath, over) in [(true, "Wrong way · No connection"), (false, "Wrong way · No signal")] {
            path = hasPath
            let backend = Backend()
            let nav = model(backend)
            await drive(nav, from: 0, to: 1500)
            await drive(nav, from: 1485, to: 1410)
            XCTAssertEqual(banner(nav), NavView.BannerText(
                symbol: "arrow.uturn.down", alert: true, over: over,
                main: "Turn around when possible"))
            // Further back, still failing: said once, decision D3, and nothing
            // added for the failure (row 2).
            await drive(nav, from: 1395, to: 900)
            XCTAssertEqual(turnAroundSaid, 1)
            XCTAssertEqual(noConnectionSaid, 0)
            XCTAssertTrue(nav.wrongWay)
        }
    }

    func test_the_replacement_landing_ends_the_wrong_way() async {
        let backend = Backend()
        backend.answers = [.route(Fixture.straightRoute(
            start: 1350, lengthMeters: 3650,
            steps: [(0, "Make a U-turn on Test Road"), (3650, "Arrive at your destination")]))]
        let nav = model(backend)
        await drive(nav, from: 0, to: 1500)
        await drive(nav, from: 1485, to: 1425)
        XCTAssertEqual(backend.asked.count, 1)
        XCTAssertFalse(nav.wrongWay)
        XCTAssertEqual(banner(nav).main, "Make a U-turn on Test Road")
    }

    func test_not_before_100_m_of_driving_the_right_way() async {
        let backend = Backend()
        let nav = model(backend)
        await drive(nav, from: 0, to: 75)                      // 75 m aligned
        await drive(nav, from: 60, to: 0)
        XCTAssertFalse(nav.wrongWay, "armed on 75 m")

        let control = model(Backend())
        await drive(control, from: 0, to: 120)
        await drive(control, from: 105, to: 30)
        XCTAssertTrue(control.wrongWay, "the control should fire")
    }

    func test_a_fix_that_cannot_say_which_way_the_car_points_does_not_vote() async {
        for (speed, accuracy, label) in [(2.5, 5.0, "below 3 m/s"), (15.0, 35.0, "worse than 30 m")] {
            let nav = model(Backend())
            await drive(nav, from: 0, to: 1500)
            await drive(nav, from: 1485, to: 1200, speed: speed, accuracy: accuracy)
            XCTAssertFalse(nav.wrongWay, label)
        }
    }

    func test_a_single_spike_off_the_line_resets_the_count() async {
        let backend = Backend()
        let nav = model(backend)
        await drive(nav, from: 0, to: 1500)
        await drive(nav, from: 1485, to: 1440)                 // four votes
        await feed(nav, at(Fixture.offset(east: 220, north: 1425), course: 180))
        await drive(nav, from: 1410, to: 1365)                 // four more
        XCTAssertFalse(nav.wrongWay, "four and four made five")
        XCTAssertTrue(backend.asked.isEmpty, "and the spike rerouted on its own")
        await feed(nav, at(Fixture.north(1350), course: 180))
        XCTAssertTrue(nav.wrongWay)
    }

    func test_a_replacement_that_opens_with_a_u_turn_does_not_fire_it() async {
        // The replacement starts at a junction ahead and runs back over the
        // road the car is on, so the car drives against it until it turns
        // (plan, section 4.1, case 2). Here the driver declines the U-turn and
        // carries on north past the junction: that is the declined-U-turn
        // rule's business (docs/reroute-uturn.md), not a wrong way.
        let backend = Backend()
        backend.answers = [
            .route(Fixture.uTurnRoute(start: 1130, lengthMeters: 1530,
                                      steps: [(0, "Make a U-turn on Test Road"),
                                              (600, "Turn right onto Cliff Street"),
                                              (1530, "Arrive at your destination")],
                                      turnaroundM: 230)),
            .route(Fixture.straightRoute(start: 1500, lengthMeters: 3000)),
        ]
        let nav = model(backend)
        await leaveTheRoute(nav)
        XCTAssertEqual(nav.currentInstruction, "Make a U-turn on Test Road")
        await drive(nav, from: 900, to: 1500)
        XCTAssertEqual(turnAroundSaid, 0, "the U-turn route fired the detector")
        XCTAssertEqual(backend.asked.map(\.kind), ["plain", "ahead"],
                       "the declined U-turn went out as an ordinary off-route reroute")
    }

    func test_the_wrong_way_reroute_sends_declined_uturn_when_set() async {
        // A route that leads on ahead and turns the driver around 2 km in,
        // turned back on long before: leaving it without having taken its
        // turn is declining it, whatever the reason (docs/reroute-uturn.md),
        // and the wrong-way reroute goes through the same `reroute`.
        let backend = Backend()
        let nav = model(route: Fixture.uTurnAheadRoute(start: 0, aheadMeters: 2000,
                                                       besideMeters: 15, backMeters: 2500),
                        destination: Fixture.offset(east: 15, north: -500), backend)
        await drive(nav, from: 0, to: 600)
        // To the fix it fires on, and no further: past the 100 m backtrack
        // floor the match moves to the return carriageway 15 m away, which is
        // a different question (docs/mid-drive-recovery.md).
        await drive(nav, from: 585, to: 525)
        XCTAssertTrue(nav.wrongWay, "the detector did not fire")
        XCTAssertEqual(backend.asked.map(\.kind), ["ahead"])
        XCTAssertTrue(nav.declinedUTurn, "the U-turn was not declined")
    }

    // MARK: - Loops (plan, sections 4.2 rule 6 and 4.4; decision D2)

    /// An out-and-back loop: 3 km north to its far point and back down the
    /// same road, the shape of a loop that drives a road twice. Driving the
    /// first pass backwards is driving the second pass forwards.
    private func outAndBackLoop() -> RouteFeature {
        var points: [[Double]] = []
        for m in stride(from: 0.0, through: 3000, by: 100) {
            let c = Fixture.north(m); points.append([c.longitude, c.latitude])
        }
        for m in stride(from: 2900.0, through: 0, by: -100) {
            let c = Fixture.north(m); points.append([c.longitude, c.latitude])
        }
        return Fixture.decode(Fixture.feature(
            coordinates: points, km: 6, minutes: 12,
            steps: [(Fixture.north(0), "Head north on Test Road", "Test Road"),
                    (Fixture.north(3000), "Make a U-turn to stay on Test Road", "Test Road"),
                    (Fixture.north(0), "Arrive back where you started", "")]))
    }

    private func loopModel(_ backend: Backend) -> NavigationModel {
        model(route: outAndBackLoop(), destination: Fixture.north(0),
              turnaround: Fixture.north(3000), backend)
    }

    func test_on_a_loop_turned_back_before_the_far_point_it_fires_and_keeps_the_loop() async {
        let backend = Backend()
        let nav = loopModel(backend)
        await drive(nav, from: 0, to: 1500)
        await drive(nav, from: 1485, to: 1410)
        XCTAssertTrue(nav.wrongWay, "the return pass beyond the far point counted as aligned")
        XCTAssertTrue(nav.isLoopBeforeFarPoint, "the far point was lost")
        XCTAssertEqual(backend.asked.map(\.kind), ["via"], "the reroute must go via the far point")
        XCTAssertEqual(backend.asked.first?.via?.latitude ?? 0, Fixture.north(3000).latitude,
                       accuracy: 1e-9)
    }

    func test_on_a_loop_the_return_pass_after_the_far_point_is_silent() async {
        let nav = loopModel(Backend())
        await drive(nav, from: 0, to: 3000)
        XCTAssertFalse(nav.isLoopBeforeFarPoint)
        await drive(nav, from: 2985, to: 1500)
        XCTAssertFalse(nav.wrongWay)
        XCTAssertEqual(turnAroundSaid, 0)
        XCTAssertEqual(nav.remainingMeters, 1500, accuracy: 30)
    }

    func test_the_cap_keeps_a_loops_match_short_of_its_far_point_until_it_is_reached() async {
        // Back down the outbound pass too slowly for the detector to read: the
        // match used to jump to the return pass, kilometres on, and latch the
        // far point as passed.
        let nav = loopModel(Backend())
        await drive(nav, from: 0, to: 1500)
        await drive(nav, from: 1485, to: 1200, speed: 2)
        XCTAssertTrue(nav.isLoopBeforeFarPoint, "the match jumped past the far point")
        XCTAssertGreaterThan(nav.remainingMeters, 4000)
    }

    // MARK: - The voice

    func test_a_recovery_line_is_not_cut_off_by_the_route_it_announced() {
        let speaker = VoiceGuideTests.FakeSpeaker()
        let voice = VoiceGuide(speaker: speaker, muted: false)
        voice.announceRecovery("Turn around when possible.")
        voice.routeAdopted()
        XCTAssertEqual(speaker.stops, 0)
        XCTAssertEqual(speaker.said, ["Turn around when possible."])
    }
}
