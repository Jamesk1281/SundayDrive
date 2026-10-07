import CoreLocation
import XCTest
@testable import SundayDrive

/// Scratch only, for the 2026-10-07 revision of docs/mid-drive-recovery-plan.md
/// (§1.5, §11). Copy it into a scratch copy's `ios/Tests` as
/// `TimedReplayTests.swift`; it is not part of the app's suite, and its output
/// holds street names from the banners, so it stays in the scratch copy.
///
/// `DriveReplay.run` hands the recorded replacements out in order, whenever the
/// model asks. That is right for "did the latch hold", and wrong for "when did
/// the app ask and get nothing": a request the real drive never got an answer
/// to is handed the *next* recorded reply, from somewhere else entirely.
///
/// This one answers a request only with the recorded reply to that same
/// request: the reply whose `req_lat`/`req_lon` is a fix within 3 s of this
/// one. Replays drift by a fix or two from the drive (a real request is in
/// flight for a second, a stubbed one for none), and 3 s matched 28 of the 29
/// October replies. Any other request fails, as
/// `URLError(.notConnectedToInternet)`. Only the October traces are replayed:
/// the older ones have no `req_lat` to key on, and the fallback below for them
/// (the next reply landing within 8 s) matched too few to be worth reading.
/// Every request is logged, answered or not, and so is every banner change and
/// utterance. A "fastest" reply is replayed as the tap that asked for it.
@MainActor
final class TimedReplayTests: XCTestCase {

    private struct Reply {
        let ts: Double
        let reqTs: Double?
        let reason: String
        let feature: RouteFeature
    }

    private final class Tape {
        var replies: [Reply] = []
        var used = Set<Int>()
        var clock = Date()
        var log: [[String: Any]] = []
        var t0 = 0.0
    }

    private static func mirrorInt(_ model: NavigationModel, _ name: String) -> Int? {
        for child in Mirror(reflecting: model).children
        where child.label == name || child.label == "_" + name {
            return child.value as? Int
        }
        return nil
    }

    private static func mirrorString(_ model: NavigationModel, _ name: String) -> String? {
        for child in Mirror(reflecting: model).children
        where child.label == name || child.label == "_" + name {
            return String(describing: child.value)
        }
        return nil
    }

    func test_timed_replay() async throws {
        guard let dir = DriveReplay.directory() else { throw XCTSkip("no traces") }
        let out = ProcessInfo.processInfo.environment["SUNDAYDRIVE_REPLAY_OUT"]
            ?? NSTemporaryDirectory() + "timed-replay.ndjson"
        let names = try FileManager.default.contentsOfDirectory(atPath: dir.path)
            .filter { $0.hasSuffix(".ndjson") && $0.hasPrefix("drive-2026-10") }.sorted()
        var text = ""
        for name in names {
            let url = dir.appendingPathComponent(name)
            guard let drive = DriveReplay.RecordedDrive(contentsOf: url) else { continue }
            let row = await replay(drive, url: url)
            let data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
            text += String(decoding: data, as: UTF8.self) + "\n"
        }
        try text.write(toFile: out, atomically: true, encoding: .utf8)
    }

    private func replay(_ drive: DriveReplay.RecordedDrive, url: URL) async -> [String: Any] {
        // The route records again, for their timestamps and request origins,
        // zipped with the decoded features (same order, same filter).
        let raw = (try? String(contentsOf: url, encoding: .utf8)) ?? ""
        var routeRecs: [[String: Any]] = []
        var fixRecs: [(ts: Double, lat: Double, lon: Double)] = []
        for line in raw.split(separator: "\n") {
            guard let d = line.data(using: .utf8),
                  let r = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { continue }
            if r["t"] as? String == "route", r["coords"] != nil, r["steps"] != nil { routeRecs.append(r) }
            if r["t"] as? String == "fix", let ts = r["ts"] as? Double,
               let la = r["lat"] as? Double, let lo = r["lon"] as? Double {
                fixRecs.append((ts, la, lo))
            }
        }
        guard routeRecs.count == drive.routes.count else {
            return ["name": drive.name, "error": "route count mismatch"]
        }
        let tape = Tape()
        tape.t0 = drive.fixes[0].timestamp.timeIntervalSince1970
        for (i, r) in routeRecs.enumerated() where i > 0 {
            let ts = r["ts"] as? Double ?? 0
            var reqTs: Double?
            if let la = r["req_lat"] as? Double, let lo = r["req_lon"] as? Double {
                reqTs = fixRecs.last(where: { $0.ts <= ts && $0.lat == la && $0.lon == lo })?.ts
            }
            let reason = (r["reason"] as? String) ?? ""
            tape.replies.append(Reply(ts: ts, reqTs: reqTs, reason: reason, feature: drive.routes[i]))
        }

        let speaker = VoiceGuideTests.FakeSpeaker()
        let voice = VoiceGuide(speaker: speaker, muted: false)
        let model = NavigationModel(route: drive.routes[0], destination: drive.destination,
                                    pref: drive.pref, weights: drive.weights, voice: voice)
        tape.clock = drive.fixes[0].timestamp
        model.now = { tape.clock }
        let manager = LocationManager()
        manager.authorizationResolved(.authorizedWhenInUse)
        manager.accuracyResolved(.fullAccuracy)

        func answer() throws -> RouteResponse {
            let t = tape.clock.timeIntervalSince1970
            let match = tape.replies.indices.first { i in
                guard !tape.used.contains(i) else { return false }
                let r = tape.replies[i]
                if let q = r.reqTs { return abs(q - t) <= 3 }
                return r.ts >= t - 0.5 && r.ts <= t + 8
            }
            var entry: [String: Any] = ["t": t - tape.t0, "kind": "request"]
            if let m = match {
                tape.used.insert(m)
                entry["answered"] = true
                entry["reply"] = m + 1
                entry["reason"] = tape.replies[m].reason
                tape.log.append(entry)
                let f = tape.replies[m].feature
                return RouteResponse(fastest: f, scenic: f)
            }
            entry["answered"] = false
            tape.log.append(entry)
            throw URLError(.notConnectedToInternet)
        }
        model.fetchRoute = { _, _, _, _, _ in try await MainActor.run { try answer() } }
        model.fetchLoopResume = { _, _, _, _, _, _ in try await MainActor.run { try answer() } }

        let taps = tape.replies.filter { $0.reason.hasPrefix("fastest") }.compactMap(\.reqTs)
        var lastBanner = ""
        var heard = 0
        var wrongWay = 0
        var connectivity = "ok"
        var fed = 0
        for fix in drive.fixes {
            fed += 1
            tape.clock = fix.timestamp
            model.update(fix)
            var spins = 0
            repeat { await Task.yield(); spins += 1 } while model.isRerouting && spins < 500
            if taps.contains(where: { abs($0 - fix.timestamp.timeIntervalSince1970) < 0.01 }) {
                tape.log.append(["t": fix.timestamp.timeIntervalSince1970 - tape.t0, "kind": "tap-fastest"])
                await model.switchToFastest(from: fix)
            }
            let t = fix.timestamp.timeIntervalSince1970 - tape.t0
            let b = NavView.bannerText(nav: model, location: manager)
            let key = b.over + " | " + b.main
            if key != lastBanner {
                tape.log.append(["t": t, "kind": "banner", "over": b.over, "main": b.main, "alert": b.alert])
                lastBanner = key
            }
            if speaker.said.count != heard {
                for s in speaker.said[heard...] { tape.log.append(["t": t, "kind": "say", "text": s]) }
                heard = speaker.said.count
            }
            if let w = Self.mirrorInt(model, "wrongWayEvents"), w != wrongWay {
                tape.log.append(["t": t, "kind": "wrongway"]); wrongWay = w
            }
            if let c = Self.mirrorString(model, "connectivity"), c != connectivity {
                tape.log.append(["t": t, "kind": "connectivity", "to": c]); connectivity = c
            }
            if model.arrived || model.stalled { break }
        }
        let unrequested = tape.replies.indices.filter { !tape.used.contains($0) }.map { $0 + 1 }
        return ["name": drive.name, "fixes": drive.fixes.count, "fed": fed,
                "arrived": model.arrived, "stalled": model.stalled,
                "recordedReplies": tape.replies.count,
                "repliesNeverAskedFor": unrequested,
                "log": tape.log]
    }
}
