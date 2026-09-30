import CoreLocation
import SwiftUI
import XCTest
@testable import SundayDrive

/// Tier 2 of the overnight drives: the real app's screens, driven by the
/// simulator's own location playback, screenshotted from outside.
///
/// The unit tests are hosted in the app process, so a test can mount the
/// app's real `PlanningView` and `NavView` — the same two branches
/// `ContentView` switches between — on a `RouteModel` it has set up itself.
/// From there nothing is simulated in-process: the route comes from the local
/// server through `RouteService`, fixes come from CoreLocation fed by
/// `xcrun simctl location start`, and the voice, map and banner are the ones a
/// driver sees. The one thing no test can do from inside is run `simctl`, so
/// `tools/e2e_sim_watcher.py` does that on the host: this test writes a
/// command file, the watcher runs it and answers.
///
/// Off unless `SUNDAYDRIVE_E2E_SCREENS` names the watcher's directory. Runs
/// for tens of minutes of wall-clock time: playback is real time.
@MainActor
final class SimulatorScreenDriveTests: XCTestCase {

    private static let dir = E2E.env["SUNDAYDRIVE_E2E_SCREENS"].map { URL(fileURLWithPath: $0) }
    private var commandCount = 0

    override func setUp() async throws {
        guard Self.dir != nil else {
            throw XCTSkip("set SUNDAYDRIVE_E2E_SCREENS to the watcher's directory")
        }
        try await E2EServer.shared.requireUp()
        // Silent: tier 1 measures the voice, and this runs overnight on a Mac
        // with speakers.
        VoiceGuide.isMuted = true
        // Past the one-time "Before you drive" notice, which a test cannot tap
        // through; `test_0` photographs it once first.
        if !name.contains("test_0") {
            UserDefaults.standard.set(true, forKey: "hasSeenBeforeYouDrive")
        }
        continueAfterFailure = true
    }

    // MARK: Talking to the watcher

    @discardableResult
    private func command(_ body: [String: Any], timeout: TimeInterval = 60) async throws -> String {
        guard let dir = Self.dir else { return "" }
        commandCount += 1
        let id = String(format: "%@-%03d", name.split(separator: " ").last.map(String.init)?
                            .trimmingCharacters(in: CharacterSet(charactersIn: "]")) ?? "t",
                        commandCount)
        var body = body
        body["id"] = id
        let data = try JSONSerialization.data(withJSONObject: body)
        let pending = dir.appendingPathComponent("\(id).cmd")
        try data.write(to: pending.appendingPathExtension("tmp"))
        try FileManager.default.moveItem(at: pending.appendingPathExtension("tmp"), to: pending)
        let done = dir.appendingPathComponent("\(id).done")
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if let reply = try? String(contentsOf: done, encoding: .utf8) { return reply }
            try await Task.sleep(for: .milliseconds(100))
        }
        XCTFail("watcher never answered \(id) — is tools/e2e_sim_watcher.py running?")
        return ""
    }

    private func shot(_ label: String) async throws {
        try await command(["cmd": "shot", "label": label])
    }

    private func play(_ points: [CLLocationCoordinate2D], speed: Double) async throws {
        try await command(["cmd": "play", "speed": speed,
                           "points": points.map { [$0.latitude, $0.longitude] }])
    }

    private func place(_ point: CLLocationCoordinate2D) async throws {
        try await command(["cmd": "set", "point": [point.latitude, point.longitude]])
    }

    @discardableResult
    private func wait(_ timeout: TimeInterval, _ condition: () -> Bool) async -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if condition() { return true }
            try? await Task.sleep(for: .milliseconds(150))
        }
        return condition()
    }

    // MARK: Mounting the app's own screens

    private struct Screens: View {
        let model: RouteModel
        var body: some View {
            ZStack {
                if let nav = model.nav {
                    NavView(nav: nav, locationManager: model.locationManager,
                            destinationName: model.mode == .loops ? model.loops.startQuery
                                                                  : model.endQuery) {
                        model.endNavigation()
                    }
                } else {
                    PlanningView(model: model)
                }
            }
            .preferredColorScheme(.dark)
            .tint(Color.amberText)
        }
    }

    private func mount(_ model: RouteModel) {
        let window = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }.flatMap(\.windows).first
        window?.rootViewController = UIHostingController(rootView: Screens(model: model))
        window?.makeKeyAndVisible()
    }

    private func planned(_ pairID: String, pref: Double,
                         from: String, to: String) async throws -> RouteModel {
        let file = try ODFile.load()
        guard let pair = file.pairs.first(where: { $0.id == pairID }), let end = pair.to else {
            throw XCTSkip("no pair \(pairID)")
        }
        try await place(pair.from)
        let model = RouteModel()
        model.start = pair.from
        model.end = end
        model.startQuery = from
        model.endQuery = to
        model.pref = pref
        mount(model)
        await model.computeRoute()
        XCTAssertNotNil(model.response, "\(pairID): \(model.errorText ?? "no route")")
        return model
    }

    // MARK: Picking what to photograph

    private func turns(_ steps: [RouteStep], count: Int) -> [Int] {
        let ks = steps.indices.filter {
            $0 >= 1 && $0 < steps.count - 1
                && [.turn, .fork, .exit, .roundabout].contains(steps[$0].maneuver)
        }
        guard ks.count > count else { return ks }
        return (0..<count).map { ks[$0 * ks.count / count] }
    }

    private func photographManeuvers(_ nav: NavigationModel, _ ks: [Int], tag: String,
                                     timeout: TimeInterval) async throws {
        for k in ks {
            if await wait(timeout, { nav.currentStep == k && nav.distanceToNext < 90 || nav.currentStep > k || nav.arrived }),
               nav.currentStep == k {
                try await shot("\(tag)-step\(k)-before")
            }
            if await wait(timeout, { nav.currentStep > k || nav.arrived }), !nav.arrived {
                try await Task.sleep(for: .seconds(1))
                try await shot("\(tag)-step\(k)-after")
            }
        }
    }

    // MARK: Drives

    /// Plan, start, three maneuvers, arrive — no mistakes.
    private func straightDrive(_ pairID: String, pref: Double, from: String, to: String,
                               speed: Double) async throws {
        let model = try await planned(pairID, pref: pref, from: from, to: to)
        guard let response = model.response else { return }
        try await Task.sleep(for: .seconds(4))       // tiles
        try await shot("\(pairID)-results")
        model.startNavigation(response.scenic)
        guard let nav = model.nav else { return XCTFail("navigation did not start") }
        try await Task.sleep(for: .seconds(4))
        try await shot("\(pairID)-drive-start")
        let line = response.scenic.coordinates
        try await play(line, speed: speed)
        let budget = response.scenic.properties.km * 1000 / speed + 120
        try await photographManeuvers(nav, turns(nav.steps, count: 3), tag: pairID, timeout: budget)
        let arrived = await wait(budget) { nav.arrived }
        try await Task.sleep(for: .seconds(2))
        try await shot("\(pairID)-arrival")
        XCTAssertTrue(arrived, "\(pairID): played the whole line and never arrived")
        model.endNavigation()
    }

    /// Carry on past a turn down a road the server routes, watch the reroute
    /// happen, then follow the replacement to the end.
    private func deviatingDrive(_ pairID: String, pref: Double, from: String, to: String,
                                speed: Double, wrongWay: Bool) async throws {
        let model = try await planned(pairID, pref: pref, from: from, to: to)
        guard let response = model.response else { return }
        let line = Polyline(response.scenic.coordinates)
        let steps = response.scenic.properties.steps
        let stepS = line.alongPositions(of: steps.map(\.coordinate))

        var points: [CLLocationCoordinate2D] = []
        if wrongWay {
            let start = line.coords[0]
            let back = (line.bearing(at: 20) + 180).truncatingRemainder(dividingBy: 360)
            let away = try await E2EServer.shared.route(
                from: start, to: Earth.offset(start, bearing: back, meters: 500), pref: 0)
            points = [start] + away.fastest.coordinates
        } else {
            guard let k = steps.indices.first(where: {
                stepS[$0] > 600 && [.turn].contains(steps[$0].maneuver)
            }) else { throw XCTSkip("\(pairID): no turn to miss") }
            let js = stepS[k], junction = line.point(at: js)
            let approach = Earth.bearing(line.point(at: max(0, js - 40)), junction)
            let detour = try await E2EServer.shared.route(
                from: line.point(at: max(0, js - 25)),
                to: Earth.offset(junction, bearing: approach, meters: 700), pref: 0,
                heading: approach)
            let d = Polyline(detour.fastest.coordinates)
            let entry = d.project(junction, lo: 0, hi: min(d.length, 200))
            points = line.slice(0, js) + d.slice(entry.s, d.length)
        }

        try await Task.sleep(for: .seconds(4))
        try await shot("\(pairID)-results")
        model.startNavigation(response.scenic)
        guard let nav = model.nav else { return XCTFail("navigation did not start") }
        try await Task.sleep(for: .seconds(3))
        try await shot("\(pairID)-drive-start")
        let original = Self.signature(nav)
        try await play(points, speed: speed)
        let budget = Polyline(points).length / speed + 60
        let tag = wrongWay ? "\(pairID)-wrongway" : "\(pairID)-missed"
        if await wait(budget, { nav.isRerouting || Self.signature(nav) != original }) {
            try await shot("\(tag)-rerouting")
        }
        let adopted = await wait(30) { Self.signature(nav) != original }
        XCTAssertTrue(adopted, "\(pairID): left the route and was never rerouted")
        try await Task.sleep(for: .seconds(1))
        try await shot("\(tag)-rerouted")

        // Follow the replacement from where the car is. The first few metres
        // are straight to its start, which is a junction just ahead on the
        // road the car is on; this tier looks at screens, not directions.
        let here = model.locationManager.location?.coordinate ?? points.last!
        let next = nav.coordinates
        try await play([here] + next, speed: speed)
        for delay in [4.0, 8.0, 14.0] {
            try await Task.sleep(for: .seconds(delay == 4 ? 4 : delay - 4))
            try await shot("\(tag)-after-reroute-\(Int(delay))s")
        }
        let rest = Polyline(next).length / speed + 120
        try await photographManeuvers(nav, turns(nav.steps, count: 2), tag: tag, timeout: rest)
        let arrived = await wait(rest) { nav.arrived }
        try await Task.sleep(for: .seconds(2))
        try await shot("\(pairID)-arrival")
        XCTAssertTrue(arrived, "\(pairID): followed the reroute and never arrived")
        model.endNavigation()
    }

    private static func signature(_ nav: NavigationModel) -> String {
        SimulatedDrive.signature(nav.coordinates)
    }

    /// The notice itself, shown over the results the first time.
    func test_0_beforeYouDriveNotice() async throws {
        UserDefaults.standard.set(false, forKey: "hasSeenBeforeYouDrive")
        _ = try await planned("urban-001", pref: 0.5, from: "Burlington", to: "Winooski")
        try await Task.sleep(for: .seconds(4))
        try await shot("notice-before-you-drive")
    }

    func test_1_urbanDrive() async throws {
        try await straightDrive("urban-001", pref: 0.5, from: "Burlington", to: "Winooski",
                                speed: 15)
    }

    func test_2_coastalDrive() async throws {
        try await straightDrive("coastal-001", pref: 1.0, from: "Rockport", to: "Gloucester",
                                speed: 18)
    }

    func test_3_parkingLotPin() async throws {
        try await straightDrive("parking-002", pref: 0.5, from: "Start", to: "Parking lot",
                                speed: 15)
    }

    func test_4_missedTurn() async throws {
        try await deviatingDrive("urban-002", pref: 0.5, from: "Start", to: "Destination",
                                 speed: 14, wrongWay: false)
    }

    func test_5_wrongWayStart() async throws {
        try await deviatingDrive("urban-003", pref: 0.5, from: "Start", to: "Destination",
                                 speed: 14, wrongWay: true)
    }

    /// A loop, for the banner: see Finding "loop banner never advances".
    func test_6_loopBanner() async throws {
        let file = try ODFile.load()
        guard let pair = file.pairs.first(where: { $0.id == "loop-001" }) else { return }
        try await place(pair.from)
        let loop = try await E2EServer.shared.loop(from: pair.from, km: pair.loop_km ?? 30)
        let model = RouteModel()
        model.mode = .loops
        model.loops.start = pair.from
        model.loops.startQuery = "Boston"
        mount(model)
        model.startLoopDrive(loop)
        guard let nav = model.nav else { return XCTFail("loop did not start") }
        try await Task.sleep(for: .seconds(4))
        try await shot("loop-001-start")
        let line = Polyline(loop.loop.coordinates)
        try await play(line.slice(0, 4000), speed: 20)
        for (i, after) in [60.0, 60.0, 60.0].enumerated() {
            try await Task.sleep(for: .seconds(after))
            try await shot("loop-001-\((i + 1) * 60)s")
        }
        XCTAssertGreaterThan(nav.currentStep, 0, "a loop driven 3.6 km never left its first instruction")
        model.endNavigation()
    }

    /// Planned from somewhere the car is not, and the car never moves: the
    /// drive should pause itself after five minutes (`stallSeconds`).
    func test_7_stalledBeforeJoining() async throws {
        let model = try await planned("urban-002", pref: 0.5, from: "Start", to: "Destination")
        guard let response = model.response else { return }
        let start = response.scenic.coordinates[0]
        let away = Earth.offset(start, bearing: response.scenic.coordinates.count > 1
                                ? Earth.bearing(start, response.scenic.coordinates[1]) + 90 : 90,
                                meters: 400)
        // Moved off before the drive starts, so no cached fix from the route
        // start reaches it and joins.
        try await place(away)
        try await Task.sleep(for: .seconds(5))
        model.startNavigation(response.scenic)
        guard let nav = model.nav else { return XCTFail("navigation did not start") }
        try await Task.sleep(for: .seconds(5))
        try await shot("urban-002-stall-waiting")
        let stalled = await wait(330) { nav.stalled }
        try await Task.sleep(for: .seconds(2))
        try await shot("urban-002-stalled")
        XCTAssertTrue(stalled, "stood still 5.5 minutes off a route never joined, and never paused")
        model.endNavigation()
    }
}
