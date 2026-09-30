import AVFoundation
import CoreLocation
import XCTest
@testable import SundayDrive

// The pieces `SimulatedDriveTests` is built from, kept apart so the test file
// reads as the personas and the metrics rather than as plumbing.
//
// The one rule every piece here follows: **nothing measures the model with the
// model's own code.** Distances are great-circle (the app projects on a local
// flat frame), along-route positions come from this file's own projection, and
// the road the car is on comes from the rendered instruction text rather than
// the `name` field the screen shows. See the brief's trap 2.

// MARK: - Configuration

enum E2E {
    static let env = ProcessInfo.processInfo.environment

    /// The server, never the app's own default: that one is the deployed
    /// backend baked into Info.plist, and a harness that fell back to it would
    /// hammer production all night. 5057 when unset, as `LiveDriveTests` does —
    /// and 5057 is meant to be empty, so a missed override is a skip.
    static let baseURL = env["SUNDAYDRIVE_API"] ?? "http://127.0.0.1:5057"

    /// Off unless asked for. Hours of drives are not something a plain
    /// `xcodebuild test` with a dev server running should stumble into.
    static var enabled: Bool { env["SUNDAYDRIVE_E2E"] == "1" }

    /// Re-run a subset by id: `urban-007`, or `urban-007@0.5` for one pref.
    static let only: [String]? = env["SUNDAYDRIVE_E2E_ONLY"].map {
        $0.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
    }

    /// Where the NDJSON goes. Outside the repo; the simulator can write host
    /// paths.
    static let outDir = URL(fileURLWithPath: env["SUNDAYDRIVE_E2E_OUT"]
                            ?? NSTemporaryDirectory() + "sundaydrive-e2e")

    /// Write a per-fix trace of every drive run. Only sensible with `only`.
    static var tracing: Bool { env["SUNDAYDRIVE_E2E_TRACE"] == "1" }

    static func wants(_ key: String) -> Bool {
        guard let only else { return true }
        return only.contains { key == $0 || key.hasPrefix($0 + "@") }
    }
}

// MARK: - The committed O/D list

struct ODPair: Decodable {
    let id: String
    let category: String
    let state: String
    let note: String
    let expect: String
    let origin: [Double]
    let destination: [Double]?
    let loop_km: Double?

    var from: CLLocationCoordinate2D { .init(latitude: origin[0], longitude: origin[1]) }
    var to: CLLocationCoordinate2D? {
        destination.map { .init(latitude: $0[0], longitude: $0[1]) }
    }
}

struct ODFile: Decodable {
    let seed: Int
    let prefs: [Double]
    let pairs: [ODPair]

    /// `tools/e2e_od_pairs.json`, found by walking up from this file — the
    /// same trick `DriveReplay` uses for `traces/`, so it works from a worktree.
    static func load(from file: String = #filePath) throws -> ODFile {
        var dir = URL(fileURLWithPath: file).deletingLastPathComponent()
        for _ in 0..<6 {
            let candidate = dir.appendingPathComponent("tools/e2e_od_pairs.json")
            if FileManager.default.fileExists(atPath: candidate.path) {
                return try JSONDecoder().decode(ODFile.self,
                                                from: Data(contentsOf: candidate))
            }
            dir.deleteLastPathComponent()
        }
        throw XCTSkip("tools/e2e_od_pairs.json not found above \(file)")
    }
}

// MARK: - Server

/// The local backend, through the requests the app itself builds.
@MainActor
final class E2EServer {
    enum Failure: Error, CustomStringConvertible {
        case down(URLError)
        case refused(Int, String)
        var description: String {
            switch self {
            case .down(let e): return "down(\(e.code.rawValue))"
            case .refused(let code, let body): return "HTTP \(code): \(body.prefix(160))"
            }
        }
    }

    static let shared = E2EServer()

    private let session: URLSession = {
        let c = URLSessionConfiguration.ephemeral
        // The NE graph is big; a cold statewide pair can take several seconds.
        c.timeoutIntervalForRequest = 90
        return URLSession(configuration: c)
    }()

    private(set) var requests = 0

    /// Throws `Failure.down` for no server, `Failure.refused` for a non-200,
    /// and lets a decode error through untouched — that one means the two
    /// sides disagree about the shape, which must fail rather than skip.
    func send<T: Decodable>(_ request: URLRequest, as: T.Type) async throws -> T {
        requests += 1
        let data: Data, response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch let error as URLError {
            throw Failure.down(error)
        }
        let code = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard code == 200 else {
            throw Failure.refused(code, String(decoding: data, as: UTF8.self))
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    func route(from: CLLocationCoordinate2D, to: CLLocationCoordinate2D,
               via: CLLocationCoordinate2D? = nil, pref: Double,
               heading: CLLocationDirection? = nil) async throws -> RouteResponse {
        try await send(RouteService.routeRequest(from: from, to: to, via: via, pref: pref,
                                                 weights: [:], heading: heading,
                                                 base: E2E.baseURL),
                       as: RouteResponse.self)
    }

    func loop(from: CLLocationCoordinate2D, km: Double) async throws -> LoopResponse {
        try await send(RouteService.loopRequest(from: from, km: km, pref: 1.0,
                                                weights: [:], base: E2E.baseURL),
                       as: LoopResponse.self)
    }

    /// Skip — never fall back — when nothing answers.
    func requireUp() async throws {
        var request = URLRequest(url: URL(string: E2E.baseURL + "/api/health")!)
        request.timeoutInterval = 5
        do {
            _ = try await session.data(for: request)
        } catch let error as URLError {
            throw XCTSkip("no Sunday Drive API at \(E2E.baseURL) (\(error.code.rawValue))")
        }
    }
}

// MARK: - Independent geometry

enum Earth {
    static let radius = 6_371_008.8

    static func distance(_ a: CLLocationCoordinate2D, _ b: CLLocationCoordinate2D) -> Double {
        let la1 = a.latitude * .pi / 180, la2 = b.latitude * .pi / 180
        let dla = la2 - la1, dlo = (b.longitude - a.longitude) * .pi / 180
        let h = sin(dla / 2) * sin(dla / 2) + cos(la1) * cos(la2) * sin(dlo / 2) * sin(dlo / 2)
        return 2 * radius * asin(min(1, sqrt(h)))
    }

    static func bearing(_ a: CLLocationCoordinate2D, _ b: CLLocationCoordinate2D) -> Double {
        let la1 = a.latitude * .pi / 180, la2 = b.latitude * .pi / 180
        let dlo = (b.longitude - a.longitude) * .pi / 180
        let y = sin(dlo) * cos(la2)
        let x = cos(la1) * sin(la2) - sin(la1) * cos(la2) * cos(dlo)
        return (atan2(y, x) * 180 / .pi + 360).truncatingRemainder(dividingBy: 360)
    }

    static func offset(_ p: CLLocationCoordinate2D, bearing: Double,
                       meters: Double) -> CLLocationCoordinate2D {
        let d = meters / radius, t = bearing * .pi / 180
        let la1 = p.latitude * .pi / 180, lo1 = p.longitude * .pi / 180
        let la2 = asin(sin(la1) * cos(d) + cos(la1) * sin(d) * cos(t))
        let lo2 = lo1 + atan2(sin(t) * sin(d) * cos(la1), cos(d) - sin(la1) * sin(la2))
        return .init(latitude: la2 * 180 / .pi, longitude: lo2 * 180 / .pi)
    }

    static func angle(_ a: Double, _ b: Double) -> Double {
        let d = abs(a - b).truncatingRemainder(dividingBy: 360)
        return d > 180 ? 360 - d : d
    }
}

/// A line with great-circle cumulative lengths, and a projection that is not
/// `Geo.progress`.
struct Polyline {
    let coords: [CLLocationCoordinate2D]
    let cum: [Double]
    var length: Double { cum.last ?? 0 }

    init(_ coords: [CLLocationCoordinate2D]) {
        self.coords = coords
        var cum = [0.0]
        cum.reserveCapacity(coords.count)
        for (a, b) in zip(coords, coords.dropFirst()) {
            cum.append(cum.last! + Earth.distance(a, b))
        }
        self.cum = cum
    }

    /// The segment index containing `s`.
    private func segment(at s: Double) -> Int {
        var lo = 0, hi = cum.count - 1
        while hi - lo > 1 {
            let mid = (lo + hi) / 2
            if cum[mid] <= s { lo = mid } else { hi = mid }
        }
        return min(lo, max(0, coords.count - 2))
    }

    func point(at s: Double) -> CLLocationCoordinate2D {
        guard coords.count >= 2 else { return coords.first ?? .init() }
        let s = min(max(0, s), length)
        let i = segment(at: s)
        let seg = cum[i + 1] - cum[i]
        let t = seg > 0 ? (s - cum[i]) / seg : 0
        let a = coords[i], b = coords[i + 1]
        return .init(latitude: a.latitude + (b.latitude - a.latitude) * t,
                     longitude: a.longitude + (b.longitude - a.longitude) * t)
    }

    /// Direction of travel at `s`, from a chord either side so a short
    /// segment's noise does not swing it.
    func bearing(at s: Double) -> Double {
        let a = point(at: max(0, s - 10)), b = point(at: min(length, s + 10))
        return Earth.bearing(a, b)
    }

    /// Nearest point on the line within `[lo, hi]` of along-distance.
    func project(_ p: CLLocationCoordinate2D, lo: Double = 0,
                 hi: Double = .infinity) -> (s: Double, offset: Double) {
        guard coords.count >= 2 else { return (0, Earth.distance(p, coords.first ?? p)) }
        let first = segment(at: max(0, lo))
        let last = segment(at: min(hi, length))
        var best = (s: 0.0, offset: Double.infinity)
        let mPerLat = Earth.radius * .pi / 180
        for i in first...last {
            let a = coords[i], b = coords[i + 1]
            let mPerLon = mPerLat * cos(a.latitude * .pi / 180)
            let bx = (b.longitude - a.longitude) * mPerLon, by = (b.latitude - a.latitude) * mPerLat
            let px = (p.longitude - a.longitude) * mPerLon, py = (p.latitude - a.latitude) * mPerLat
            let len2 = bx * bx + by * by
            let t = len2 > 0 ? max(0, min(1, (px * bx + py * by) / len2)) : 0
            let dx = px - bx * t, dy = py - by * t
            let off = sqrt(dx * dx + dy * dy)
            if off < best.offset {
                best = (cum[i] + (cum[i + 1] - cum[i]) * t, off)
            }
        }
        return best
    }

    /// `project`, over only the segments running within `maxAngle` of
    /// `bearing` — so a car does not "join" a line on the leg coming back the
    /// other way past it.
    func projectAligned(_ p: CLLocationCoordinate2D, bearing: Double, maxAngle: Double,
                        lo: Double = 0, hi: Double = .infinity) -> (s: Double, offset: Double) {
        guard coords.count >= 2 else { return (0, .infinity) }
        let first = segment(at: max(0, lo)), last = segment(at: min(hi, length))
        var best = (s: 0.0, offset: Double.infinity)
        for i in first...last where cum[i + 1] > cum[i] {
            guard Earth.angle(Earth.bearing(coords[i], coords[i + 1]), bearing) <= maxAngle
            else { continue }
            let one = Polyline([coords[i], coords[i + 1]]).project(p)
            if one.offset < best.offset { best = (cum[i] + one.s, one.offset) }
        }
        return best
    }

    /// Where each maneuver sits along the line, walked forwards so a road
    /// driven twice places each on the right pass.
    ///
    /// Not a plain nearest-point walk, which is what the model does and
    /// exactly what this exists to check: on a closed loop the first and last
    /// vertex are the same point, a step's coordinate is rounded to 6 decimals
    /// (~5 cm), and a nearest-point search is then a coin flip between the
    /// opening segment and the closing one. Here, among everything within a
    /// metre of the best match, the *earliest* wins — a maneuver is placed on
    /// the first pass that reaches it.
    func alongPositions(of points: [CLLocationCoordinate2D]) -> [Double] {
        var floor = 0.0
        return points.map { p in
            let best = project(p, lo: floor).offset
            let hit = earliest(p, lo: floor, within: best + 1)
            floor = hit
            return hit
        }
    }

    private func earliest(_ p: CLLocationCoordinate2D, lo: Double, within: Double) -> Double {
        guard coords.count >= 2 else { return 0 }
        for i in segment(at: max(0, lo))..<(coords.count - 1) {
            let one = Polyline([coords[i], coords[i + 1]]).project(p)
            let along = cum[i] + one.s
            if one.offset <= within, along >= lo { return along }
        }
        return project(p, lo: lo).s
    }

    /// The stretch of line from `from` to `to`.
    func slice(_ from: Double, _ to: Double) -> [CLLocationCoordinate2D] {
        guard to > from else { return [point(at: from)] }
        var out = [point(at: from)]
        for (i, c) in cum.enumerated() where c > from && c < to { out.append(coords[i]) }
        out.append(point(at: to))
        return out
    }
}

/// "Turn left onto Bolton Road" -> "Bolton Road", as `LiveDriveTests` parses
/// it: the tail after the last " onto " or " on ", and nothing with a colon.
func roadNamed(inInstruction text: String) -> String? {
    for marker in [" onto ", " on "] {
        if let r = text.range(of: marker, options: .backwards) {
            let tail = String(text[r.upperBound...])
            return tail.isEmpty || tail.contains(":") ? nil : tail
        }
    }
    return nil
}

// MARK: - Randomness that is the same every night

/// SplitMix64, seeded from a stable hash of the drive's id. Swift's own
/// `hashValue` is randomised per process, which would make every noisy drive
/// irreproducible.
struct SeededRNG: RandomNumberGenerator {
    private var state: UInt64
    init(_ key: String) {
        var h: UInt64 = 0xcbf2_9ce4_8422_2325
        for b in key.utf8 { h = (h ^ UInt64(b)) &* 0x100_0000_01b3 }
        state = h
    }
    mutating func next() -> UInt64 {
        state &+= 0x9e37_79b9_7f4a_7c15
        var z = state
        z = (z ^ (z >> 30)) &* 0xbf58_476d_1ce4_e5b9
        z = (z ^ (z >> 27)) &* 0x94d0_49bb_1331_11eb
        return z ^ (z >> 31)
    }
    mutating func uniform(_ lo: Double, _ hi: Double) -> Double {
        Double.random(in: lo...hi, using: &self)
    }
    mutating func gaussian() -> Double {
        let u1 = max(1e-12, uniform(0, 1)), u2 = uniform(0, 1)
        return sqrt(-2 * log(u1)) * cos(2 * .pi * u2)
    }
}

// MARK: - Voice capture

/// What the guide hands to the audio hardware, captured instead of spoken.
/// `Speaker` is the guide's own seam, so no product code changes for this.
@MainActor
final class RecordingSpeaker: Speaker {
    var onFinished: (() -> Void)?
    var onInterrupted: (() -> Void)?
    var onProblem: ((String) -> Void)?
    var heard: ((String) -> Void)?

    @discardableResult func say(_ text: String) -> Bool {
        heard?(text)
        // Finished at once: nothing in the harness is speaking, and a guide
        // left believing an utterance is in flight forever behaves differently
        // from one on a phone.
        onFinished?()
        return true
    }
    func stop() {}
    func use(_ voice: AVSpeechSynthesisVoice?) {}
}

// MARK: - Percentiles, for the summary

func percentile(_ xs: [Double], _ p: Double) -> Double? {
    guard !xs.isEmpty else { return nil }
    let sorted = xs.sorted()
    let rank = p / 100 * Double(sorted.count - 1)
    let lo = Int(rank.rounded(.down)), hi = Int(rank.rounded(.up))
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (rank - Double(lo))
}
