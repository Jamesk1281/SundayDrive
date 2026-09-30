import CoreLocation
import XCTest
@testable import SundayDrive

/// The defects the overnight drives found, each kept as a replayable case.
///
/// Every assertion is wrapped in a strict `XCTExpectFailure`: the suite is green
/// while the defect is present and goes red the day it is fixed, so whoever
/// fixes it has to come here and turn the expectation into a plain assertion.
/// Each names its finding in docs/overnight-e2e-drives-brief.md.
///
/// Needs the local server, like `LiveDriveTests`, and skips without one:
///     TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:5173 xcodebuild test ...
///       -only-testing:SundayDriveTests/SimulatedDriveRegressionTests
@MainActor
final class SimulatedDriveRegressionTests: XCTestCase {

    private func planned(_ id: String, pref: Double) async throws -> PlannedRoute {
        try await E2EServer.shared.requireUp()
        let file = try ODFile.load()
        guard let pair = file.pairs.first(where: { $0.id == id }) else {
            throw XCTSkip("no pair \(id) in tools/e2e_od_pairs.json")
        }
        if pair.category == "loop" {
            let loop = try await E2EServer.shared.loop(from: pair.from, km: pair.loop_km ?? 40)
            return PlannedRoute(key: id, pair: pair, pref: 1.0, feature: loop.loop,
                                destination: pair.from,
                                turnaround: loop.meta.turnaroundCoordinate)
        }
        let response = try await E2EServer.shared.route(from: pair.from, to: pair.to!, pref: pref)
        return PlannedRoute(key: "\(id)@\(String(format: "%.1f", pref))", pair: pair, pref: pref,
                            feature: response.scenic, destination: pair.to!, turnaround: nil)
    }

    private func drive(_ id: String, pref: Double, _ persona: Persona) async throws -> DriveRecord {
        let route = try await planned(id, pref: pref)
        guard case .script(let script, _) = try await Staging.stage(persona, route) else {
            throw XCTSkip("\(id) could not be staged for \(persona.rawValue)")
        }
        return await SimulatedDrive(route, persona: persona).run(script)
    }

    /// Finding 1. A loop's first maneuver is placed on its closing segment, so
    /// the banner never leaves "Head north on Cambridge Street".
    func test_F1_a_loop_banner_advances_past_its_first_maneuver() async throws {
        let route = try await planned("loop-001", pref: 1.0)
        let model = NavigationModel(route: route.feature, destination: route.destination,
                                    pref: 1.0, weights: [:], turnaround: route.turnaround)
        model.fetchRoute = { _, _, _, _, _ in throw URLError(.notConnectedToInternet) }
        model.fetchLoopResume = { _, _, _, _, _, _ in throw URLError(.notConnectedToInternet) }
        let line = Polyline(route.feature.coordinates)
        var t = Date(timeIntervalSince1970: 1_790_000_000)
        model.now = { t }
        var s = 0.0
        while s < 3000 {
            let p = line.point(at: s)
            model.update(CLLocation(coordinate: p, altitude: 0, horizontalAccuracy: 5,
                                    verticalAccuracy: 5, course: line.bearing(at: s),
                                    speed: 12, timestamp: t))
            s += 12
            t = t.addingTimeInterval(1)
        }
        XCTExpectFailure("Finding 1: stepRemaining[0] lands on the loop's closing segment",
                         strict: true) {
            XCTAssertGreaterThan(model.currentStep, 0,
                                 "3 km into the loop and still on \"\(model.currentInstruction)\"")
        }
    }

    /// Finding 2. On a stretch the loop drives twice, the match jumps to the
    /// later pass, latches the far point as passed, and the reroute that
    /// follows goes home — on a drive that never left the line.
    func test_F2_a_loop_driven_perfectly_is_never_rerouted() async throws {
        let record = try await drive("loop-001", pref: 1.0, .loopPerfect)
        XCTExpectFailure("Finding 2: forward jump onto the retraced pass", strict: true) {
            XCTAssertEqual(record.rerouteRequests, 0)
        }
    }

    /// Finding 2b. The same tie at the driveway: a loop whose closing leg
    /// comes home along the street it left by matches that leg on the second
    /// fix and latches `arrived` 20 m from the start, with 45 km to go.
    func test_F2b_a_loop_does_not_arrive_in_its_own_driveway() async throws {
        let record = try await drive("loop-013", pref: 1.0, .loopPerfect)
        XCTExpectFailure("Finding 2b: arrival latched on the closing leg at the start", strict: true) {
            XCTAssertGreaterThan(record.drivenKm, 40, "arrived after \(record.drivenKm) km of a 45 km loop")
        }
    }

    /// Finding 3. A reroute that opens with a U-turn never says so, and once
    /// it is made the banner holds it, reading "off route", for ~100 m.
    func test_F3_a_reroute_that_opens_with_a_u_turn_says_it_and_moves_on() async throws {
        let record = try await drive("rural-003", pref: 0.5, .wrongWayStart)
        XCTExpectFailure("Finding 3: opening U-turn unspoken, banner lags after it", strict: true) {
            XCTAssertEqual(record.openingsUnspoken, 0)
            XCTAssertEqual(record.bannerBehind, 0)
        }
    }

    /// Finding 4. A U-turn in the middle of a route is skipped by the banner
    /// before the car reaches it.
    func test_F4_a_mid_route_u_turn_is_not_skipped() async throws {
        let record = try await drive("coastal-002", pref: 0.5, .perfect)
        XCTExpectFailure("Finding 4: out-and-back match jumps past the U-turn", strict: true) {
            XCTAssertEqual(record.bannerSkipped, 0)
        }
    }

    /// Finding 5. A ferry-only island is "routed" to the mainland shore 2.5 km
    /// away, because the destination snap accepts 5 km across water.
    func test_F5_a_ferry_only_island_is_refused() async throws {
        try await E2EServer.shared.requireUp()
        let pair = try ODFile.load().pairs.first { $0.id == "island-005" }!
        var routed = false
        do {
            _ = try await E2EServer.shared.route(from: pair.from, to: pair.to!, pref: 0.5)
            routed = true
        } catch E2EServer.Failure.refused {}
        XCTExpectFailure("Finding 5: SNAP_MAX_M lets the pin snap across Casco Bay", strict: true) {
            XCTAssertFalse(routed, "Peaks Island came back with a route")
        }
    }

    /// Finding 6. OSM's raw `ref` list reaches the instruction text, and so
    /// the voice: "Take the exit onto I 395;ME 9;ME 15".
    func test_F6_instructions_carry_no_raw_ref_lists() async throws {
        let route = try await planned("suburban-002", pref: 0.0)
        let raw = route.feature.properties.steps.map(\.instruction).filter { $0.contains(";") }
        XCTExpectFailure("Finding 6: semicolon ref lists in instructions", strict: true) {
            XCTAssertEqual(raw, [])
        }
    }
}
