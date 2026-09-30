import CoreLocation
import XCTest
@testable import SundayDrive

/// The overnight end-to-end drives: every route in `tools/e2e_od_pairs.json`,
/// at every pref, driven by every persona through the real `NavigationModel`
/// against a real local server. See docs/overnight-e2e-drives-brief.md and the
/// findings appended to it.
///
/// Off by default twice over: it skips unless `SUNDAYDRIVE_E2E=1`, and it
/// skips when no server answers (a decode error still fails). Run it as
///
///     SUNDAYDRIVE_DATA=<main>/data/processed-ne PORT=5173 python server/serve.py
///     TEST_RUNNER_SUNDAYDRIVE_E2E=1 \
///     TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:5173 \
///     TEST_RUNNER_SUNDAYDRIVE_E2E_OUT=/some/dir \
///     xcodebuild test ... -only-testing:SundayDriveTests/SimulatedDriveTests
///
/// and replay one drive with `TEST_RUNNER_SUNDAYDRIVE_E2E_ONLY=urban-007@0.5`
/// plus `-only-testing:SundayDriveTests/SimulatedDriveTests/test_05_missedTurn`.
///
/// What it reports is drives *run*. A persona that could not be staged on a
/// route (no real road leaves the junction, say) is written down with the
/// reason and counted apart, never as a pass.
@MainActor
final class SimulatedDriveTests: XCTestCase {

    // MARK: Routes, fetched once per process

    private static var planned: [PlannedRoute]?

    static func routes() async throws -> [PlannedRoute] {
        if let planned { return planned }
        let file = try ODFile.load()
        let server = E2EServer.shared
        var out: [PlannedRoute] = []
        var log: [[String: Any]] = []

        for pair in file.pairs where E2E.wants(pair.id) {
            if pair.category == "loop" {
                var entry: [String: Any] = ["key": pair.id, "id": pair.id,
                                            "category": pair.category, "state": pair.state,
                                            "pref": 1.0, "expect": pair.expect]
                do {
                    let loop = try await server.loop(from: pair.from, km: pair.loop_km ?? 40)
                    out.append(PlannedRoute(key: pair.id, pair: pair, pref: 1.0,
                                            feature: loop.loop, destination: pair.from,
                                            turnaround: loop.meta.turnaroundCoordinate))
                    entry["status"] = "ok"
                    entry["km"] = loop.meta.km
                    entry["target_km"] = loop.meta.target_km
                    entry["repeated_km"] = loop.meta.repeated_km
                    entry["steps"] = loop.loop.properties.steps.count
                } catch E2EServer.Failure.down(let e) {
                    throw XCTSkip("server went away: \(e.code.rawValue)")
                } catch E2EServer.Failure.refused(let code, let body) {
                    entry["status"] = "refused"; entry["code"] = code; entry["message"] = body
                }
                log.append(entry)
                continue
            }
            guard let to = pair.to else { continue }
            for pref in file.prefs {
                let key = "\(pair.id)@\(String(format: "%.1f", pref))"
                guard E2E.wants(key) else { continue }
                var entry: [String: Any] = ["key": key, "id": pair.id,
                                            "category": pair.category, "state": pair.state,
                                            "pref": pref, "expect": pair.expect]
                do {
                    let response = try await server.route(from: pair.from, to: to, pref: pref)
                    let f = response.scenic
                    let line = Polyline(f.coordinates)
                    entry["status"] = "ok"
                    entry["km"] = f.properties.km
                    entry["minutes"] = f.properties.minutes
                    entry["steps"] = f.properties.steps.count
                    entry["startOffsetM"] = Earth.distance(pair.from, f.coordinates.first!).rounded()
                    entry["endOffsetM"] = Earth.distance(to, f.coordinates.last!).rounded()
                    entry["pinToLineM"] = line.project(to).offset.rounded()
                    entry["sameAsFastest"] = Self.sameLine(f, response.fastest)
                    if pair.expect == "route" {
                        out.append(PlannedRoute(key: key, pair: pair, pref: pref, feature: f,
                                                destination: to, turnaround: nil))
                    }
                } catch E2EServer.Failure.down(let e) {
                    throw XCTSkip("server went away: \(e.code.rawValue)")
                } catch E2EServer.Failure.refused(let code, let body) {
                    entry["status"] = "refused"; entry["code"] = code; entry["message"] = body
                }
                log.append(entry)
            }
        }
        write(log, to: "routes.ndjson", append: false)
        planned = out
        return out
    }

    private static func sameLine(_ a: RouteFeature, _ b: RouteFeature) -> Bool {
        a.geometry.coordinates == b.geometry.coordinates
    }

    // MARK: Output

    private static func write(_ rows: [[String: Any]], to name: String, append: Bool) {
        try? FileManager.default.createDirectory(at: E2E.outDir, withIntermediateDirectories: true)
        let url = E2E.outDir.appendingPathComponent(name)
        var text = ""
        for row in rows {
            if let data = try? JSONSerialization.data(withJSONObject: row, options: [.sortedKeys]) {
                text += String(decoding: data, as: UTF8.self) + "\n"
            }
        }
        writeText(text, to: url, append: append)
    }

    private static func writeText(_ text: String, to url: URL, append: Bool) {
        if append, let handle = try? FileHandle(forWritingTo: url) {
            handle.seekToEndOfFile()
            handle.write(Data(text.utf8))
            try? handle.close()
        } else {
            try? Data(text.utf8).write(to: url)
        }
    }

    private static func appendRecord(_ record: DriveRecord) {
        try? FileManager.default.createDirectory(at: E2E.outDir, withIntermediateDirectories: true)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        guard let data = try? encoder.encode(record) else { return }
        writeText(String(decoding: data, as: UTF8.self) + "\n",
               to: E2E.outDir.appendingPathComponent("drives.ndjson"), append: true)
    }

    // MARK: Driving a persona over every route

    private func drive(_ persona: Persona) async throws {
        guard E2E.enabled else {
            throw XCTSkip("set SUNDAYDRIVE_E2E=1 (TEST_RUNNER_SUNDAYDRIVE_E2E=1) to run the overnight drives")
        }
        try await E2EServer.shared.requireUp()
        let routes = try await Self.routes()
        let pool = routes.filter { ($0.turnaround != nil) == persona.isLoop }
        var records: [DriveRecord] = []
        var pooledDistErr: [Double] = []
        let started = Date()

        for route in pool where E2E.wants(route.key) {
            let staged = try await Staging.stage(persona, route)
            let drive = SimulatedDrive(route, persona: persona)
            var record: DriveRecord
            switch staged {
            case .script(let script, let note):
                drive.record.detour = note
                record = await drive.run(script)
                pooledDistErr += drive.distErrSamples
                if E2E.tracing {
                    Self.writeText(drive.trace, to: E2E.outDir.appendingPathComponent(
                        "trace-\(route.key)-\(persona.rawValue).ndjson"), append: false)
                }
            case .unstageable(let why):
                record = drive.record
                record.setup = why
            }
            Self.appendRecord(record)
            records.append(record)
        }
        summarize(persona, records, pooledDistErr, wall: Date().timeIntervalSince(started))
    }

    private func summarize(_ persona: Persona, _ records: [DriveRecord],
                           _ distErr: [Double], wall: TimeInterval) {
        let ran = records.filter { $0.ran }
        let km = ran.reduce(0) { $0 + $1.drivenKm }
        let reroutes = ran.reduce(0) { $0 + $1.rerouteRequests }
        let leads = ran.flatMap(\.finalLeadS)
        func sum(_ k: KeyPath<DriveRecord, Int>) -> Int { ran.reduce(0) { $0 + $1[keyPath: k] } }
        let summary: [String: Any] = [
            "persona": persona.rawValue,
            "routes": records.count,
            "drivesRun": ran.count,
            "unstaged": records.count - ran.count,
            "arrivals": ran.filter(\.arrived).count,
            "drivenKm": km.rounded(),
            "rerouteRequests": reroutes,
            "reroutesPerKm": km > 0 ? Double(reroutes) / km : 0,
            "adoptions": sum(\.adoptions),
            "suffixAdoptions": sum(\.suffixAdoptions),
            "bannerBehind": sum(\.bannerBehind),
            "drivesWithBannerBehind": ran.filter { $0.bannerBehind > 0 }.count,
            "bannerSkipped": sum(\.bannerSkipped),
            "distErrP50": percentile(distErr, 50) ?? -1,
            "distErrP95": percentile(distErr, 95) ?? -1,
            "distOver30": sum(\.distOver30),
            "distChecked": sum(\.distChecked),
            "promptLeadP5": percentile(leads, 5) ?? -1,
            "promptLeadP50": percentile(leads, 50) ?? -1,
            "missingPrompts": sum(\.missingPrompts),
            "openingsDriven": sum(\.openingsDriven),
            "openingsUnspoken": sum(\.openingsUnspoken),
            "passedInGap": sum(\.passedInGap),
            "missingNearStart": sum(\.missingNearStart),
            "latePrompts": sum(\.latePrompts),
            "maneuversPassed": sum(\.maneuversPassed),
            "streetChecked": sum(\.streetChecked),
            "streetMismatch": sum(\.streetMismatch),
            "falseOffRoute": sum(\.falseOffRoute),
            "namedWhileOff": sum(\.namedWhileOff),
            "flicker": sum(\.flicker),
            "stalls": sum(\.stalls),
            "bridges": sum(\.bridges),
            "uTurnJoins": sum(\.uTurnJoins),
            "rerouteLatencyP50": percentile(ran.flatMap(\.rerouteLatencyS), 50) ?? -1,
            "drivesWithViolations": ran.filter { !$0.violations.isEmpty }.count,
            "wallSeconds": wall.rounded(),
        ]
        Self.write([summary], to: "summary-\(persona.rawValue).json", append: false)
        print("E2E SUMMARY \(summary)")

        XCTAssertGreaterThan(ran.count, 0, "\(persona.rawValue): no drive was run")
        var reported = 0
        for r in ran where !r.violations.isEmpty {
            reported += 1
            guard reported <= 25 else { break }
            XCTFail("\(r.key) \(persona.rawValue): " + r.violations.joined(separator: "; "))
        }
        if reported > 0 {
            XCTFail("\(persona.rawValue): \(ran.filter { !$0.violations.isEmpty }.count) of "
                    + "\(ran.count) drives had a hard failure — see drives.ndjson")
        }
    }

    // MARK: The personas, in the order they should run

    func test_01_routesFetchAndIslandsFailCleanly() async throws {
        guard E2E.enabled else { throw XCTSkip("set SUNDAYDRIVE_E2E=1") }
        try await E2EServer.shared.requireUp()
        let routes = try await Self.routes()
        XCTAssertGreaterThan(routes.count, 0)
        // Read back what was logged, so the checks are on the same record the
        // report is built from.
        let url = E2E.outDir.appendingPathComponent("routes.ndjson")
        let rows = (try? String(contentsOf: url, encoding: .utf8))?
            .split(separator: "\n")
            .compactMap { try? JSONSerialization.jsonObject(with: Data($0.utf8)) as? [String: Any] }
            ?? []
        for row in rows {
            let key = row["key"] as? String ?? "?"
            let code = row["code"] as? Int ?? 200
            XCTAssertLessThan(code, 500, "\(key): the server errored — \(row["message"] ?? "")")
            if row["expect"] as? String == "fail" {
                XCTAssertNotEqual(row["status"] as? String, "ok",
                                  "\(key): an unreachable pin came back with a route "
                                  + "(\(row["km"] ?? "?") km)")
            }
        }
    }

    func test_02_perfect() async throws { try await drive(.perfect) }
    func test_03_noisy() async throws { try await drive(.noisy) }
    func test_04_dropout() async throws { try await drive(.dropout) }
    func test_05_stopAndGo() async throws { try await drive(.stopAndGo) }
    func test_06_missedTurn() async throws { try await drive(.missedTurn) }
    func test_07_wrongWayStart() async throws { try await drive(.wrongWayStart) }
    func test_08_earlyStop() async throws { try await drive(.earlyStop) }
    func test_09_loopPerfect() async throws { try await drive(.loopPerfect) }
    func test_10_loopLate() async throws { try await drive(.loopLate) }
    func test_11_loopEarly() async throws { try await drive(.loopEarly) }
}
