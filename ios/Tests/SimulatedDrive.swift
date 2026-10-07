import CoreLocation
import XCTest
@testable import SundayDrive

/// One simulated drive: a persona's timed fix stream through the real
/// `NavigationModel`, against the real local server, measured by an instrument
/// that is not the model's own. See docs/overnight-e2e-findings.md.
///
/// The car has a *true* position — always a point on real road geometry the
/// server returned (the route, a detour the server routed, or the replacement
/// route the model adopted) — and the model is handed that position through
/// the persona's GPS. Everything checked is checked against the truth:
///
/// - where each maneuver sits is this file's own projection of the step's
///   coordinate onto the line (`Polyline.alongPositions`), so "the banner's
///   maneuver is behind the car" and "the distance shown is wrong" are
///   measured, not read back;
/// - the road the car is on is parsed from the *instruction* of the maneuver
///   the truth last drove through, which the server renders from the leg
///   label independently of the `name` field the screen shows;
/// - the clock is synthetic and injected (`model.now`), one second per fix, so
///   every cooldown, grace period and stall timer runs on the persona's time.
///
/// The one place this is kinder than a phone: a reroute's server round trip
/// is awaited before the next fix, so it lands in zero simulated seconds.
enum Persona: String, CaseIterable, Codable {
    case perfect, noisy, dropout, stopAndGo, missedTurn, wrongWayStart, earlyStop
    case loopPerfect, loopLate, loopEarly
    case wrongWayAlong, loopWrongWay, serverDown, loopServerDown, deadZone, loopDeadZone
    case spike, canyon, loopMild, loopSpike, loopCanyon

    var isLoop: Bool { [.loopPerfect, .loopLate, .loopEarly, .loopWrongWay, .loopServerDown, .loopDeadZone,
                        .loopMild, .loopSpike, .loopCanyon].contains(self) }
    /// Personas that never leave the road; any reroute they cause is the
    /// model's doing.
    var staysOnRoute: Bool { [.perfect, .noisy, .dropout, .stopAndGo, .earlyStop, .loopPerfect,
                              .spike, .canyon, .loopMild, .loopSpike, .loopCanyon].contains(self) }
}

/// A route ready to drive, fetched once per process.
struct PlannedRoute {
    let key: String
    let pair: ODPair
    let pref: Double
    let feature: RouteFeature
    let destination: CLLocationCoordinate2D
    let turnaround: CLLocationCoordinate2D?
}

/// Everything recorded about one drive, one NDJSON line.
struct DriveRecord: Encodable {
    var key = "", id = "", category = "", state = "", persona = ""
    var pref = 0.0
    var routeKm = 0.0, routeMinutes = 0.0, steps = 0
    var setup: String?            // why a persona could not be staged, if it couldn't
    var ran = false
    var fixes = 0, simSeconds = 0.0, drivenKm = 0.0
    var arrived = false
    var arrivalPinM: Double?, arrivalShortM: Double?, arrivalAfterParkS: Double?
    var endedOnLastStep: Bool?
    var rerouteRequests = 0, adoptions = 0, merges = 0, failedReroutes = 0
    var suffixAdoptions = 0
    var rerouteLatencyS: [Double] = []
    var bridges = 0, uTurnJoins = 0
    var bannerBehind = 0, maxBehindM = 0.0, bannerSkipped = 0
    var distChecked = 0, distOver30 = 0
    var distErrP50: Double?, distErrP95: Double?, distErrMax: Double?
    var remainingErrP95: Double?
    var streetChecked = 0, streetMismatch = 0, falseOffRoute = 0
    var namedWhileOff = 0, offTicks = 0
    var remainingRises = 0, maxRiseM = 0.0, stepBackwards = 0
    var bannerChanges = 0, maneuversPassed = 0, flicker = 0
    var finalLeadM: [Double] = [], finalLeadS: [Double] = [], prepareLeadS: [Double] = []
    var missingPrompts = 0, missingNearStart = 0, latePrompts = 0
    /// Reroutes whose opening maneuver was driven through and never spoken.
    var openingsDriven = 0, openingsUnspoken = 0, passedInGap = 0
    var stalls = 0
    // Wrong way along the route (mid-drive recovery study).
    var revDone = false, revBackM = 0.0
    var revFirstRequestS: Double?, revFirstRequestM: Double?
    var revRequests = 0, revUtterances = 0
    var revSaid: [String] = []
    var revRoadOff = 0, revRoadNamed = 0, revRoadUnknown = 0
    var revBanner: [String] = []
    var revJoinedNew = false
    // Server down mid-drive.
    var outageS = 0.0
    var outageAttempts: [Double] = []
    var recoveryAfterS: Double?
    var outageBanner: [String] = []
    var outageUtterances = 0
    var outageFixes = 0, outageRerouting = 0
    // The wrong-way detector: when it fired during the reversal (seconds and
    // metres after the U-turn), and how often it fired anywhere else.
    var wrongWayFirstS: Double?, wrongWayFirstM: Double?
    var wrongWayFalse = 0, wrongWayEvents = 0
    /// The recovery lines heard, and when.
    var recoverySaid: [String] = []
    var detour: String?
    var violations: [String] = []
    var samples: [String] = []
}

/// Behaviour a persona adds on top of driving the line.
enum Noise { case none, mild, spike, canyon }

struct Script {
    var noisy = false
    var noise: Noise = .none
    var reverse: (at: Double, back: Double)?
    var outageSeconds: Double?
    var gaps: [(s: Double, seconds: Double)] = []
    var dwells: [(s: Double, seconds: Double)] = []
    var deviation: (s: Double, path: Polyline, into: Double)?
    var startPath: Polyline?
    var earlyStop = false
}

@MainActor
final class SimulatedDrive {
    struct Utterance {
        let text: String, kind: String, gen: Int
        let sTruth: Double?, v: Double
        let target: Double?, chainedTarget: Double?
    }
    struct Passed { let gen: Int; let s: Double; let joinS: Double }
    /// The opening maneuver of each adopted line, by generation.
    private var openings: [Int: (s: Double, text: String)] = [:]
    private var joinedOpenings: [Int] = []
    private var lastFixT: Date?

    let planned: PlannedRoute
    let persona: Persona
    let model: NavigationModel
    private let speaker = RecordingSpeaker()
    private let server = E2EServer.shared
    private var rng: SeededRNG
    var record = DriveRecord()

    // The clock.
    private var t: Date
    private let t0: Date

    // The truth.
    private var path: Polyline
    private var s = 0.0
    private var onModelLine = true
    private var walking = false
    /// After an adoption: the new line, waiting for the car to reach it.
    private var joinWindow: ClosedRange<Double>?
    private var joinS = 0.0
    private var lastModelS = 0.0
    private var truthSpeed = 0.0

    // What the model is following, as measured here.
    private var line: Polyline
    private var lineSig: String
    private var stepS: [Double]
    private var stepsSig: String
    private var gen = 0
    private let cruise: Double

    // Metric state.
    private var lastStep = 0, lastRemaining = Double.infinity, lastExp = 0
    private var lastBanner = ""
    private var bannersSeen: Set<String> = []
    private var distErrs: [Double] = [], remErrs: [Double] = []
    /// Every distance-to-maneuver error measured, for the pooled percentiles.
    var distErrSamples: [Double] { distErrs }
    private var utterances: [Utterance] = []
    private var passed: [Passed] = []
    private var deviationStart: Date?
    // Mid-drive recovery study.
    private var reversing = false
    private var revStart: Date?
    private var revAt = 0.0, revBack = 0.0
    private var outageStart: Date?, outageEnd: Date?
    private var noise: Noise = .none
    private var canyonOffset = 0.0
    private let bannerLocation = LocationManager()
    private var outageActive: Bool {
        guard let a = outageStart, let b = outageEnd else { return false }
        return t >= a && t < b
    }
    private var bannerNow: String {
        let b = NavView.bannerText(nav: model, location: bannerLocation)
        let road: String
        switch model.currentRoad {
        case .named(let r): road = "named(\(r))"
        case .offRoute: road = "Off your route"
        case .unknown: road = "-"
        }
        return "[\(b.over)] \(b.main) | road: \(road) | rem \(Int(model.remainingMeters)) m"
            + (model.isLoopBeforeFarPoint ? " | before far point" : "")
    }
    private var parkedAt: Date?
    private var traceLines: [String] = []

    init(_ planned: PlannedRoute, persona: Persona) {
        self.planned = planned
        self.persona = persona
        let key = "\(planned.key):\(persona.rawValue)"
        rng = SeededRNG(key)
        // A fixed epoch per drive, so a replay sees the same clock.
        t0 = Date(timeIntervalSince1970: 1_790_000_000)
        t = t0
        let coords = planned.feature.coordinates
        line = Polyline(coords)
        path = line
        lineSig = Self.signature(coords)
        let steps = planned.feature.properties.steps
        stepS = line.alongPositions(of: steps.map(\.coordinate))
        stepsSig = Self.signature(steps)
        let km = planned.feature.properties.km, minutes = planned.feature.properties.minutes
        cruise = minutes > 0 ? min(30, max(8, km * 1000 / (minutes * 60))) : 13

        let voice = VoiceGuide(speaker: speaker, muted: false)
        model = NavigationModel(route: planned.feature, destination: planned.destination,
                                pref: planned.pref, weights: [:],
                                turnaround: planned.turnaround, voice: voice)
        model.now = { [unowned self] in self.t }
        model.fetchRoute = { [unowned self] from, to, pref, _, heading in
            try await self.reroute(from: from, to: to, via: nil, pref: pref, heading: heading)
        }
        model.fetchLoopResume = { [unowned self] from, via, to, pref, _, heading in
            try await self.reroute(from: from, to: to, via: via, pref: pref, heading: heading)
        }
        speaker.heard = { [unowned self] text in self.heard(text) }

        record.key = planned.key
        record.id = planned.pair.id
        record.category = planned.pair.category
        record.state = planned.pair.state
        record.pref = planned.pref
        record.persona = persona.rawValue
        record.routeKm = km
        record.routeMinutes = minutes
        record.steps = steps.count
    }

    static func signature(_ c: [CLLocationCoordinate2D]) -> String {
        guard let f = c.first, let l = c.last else { return "0" }
        let m = c[c.count / 2]
        return "\(c.count)|\(f.latitude),\(f.longitude)|\(m.latitude),\(m.longitude)|\(l.latitude),\(l.longitude)"
    }
    static func signature(_ steps: [RouteStep]) -> String {
        "\(steps.count)|" + steps.map(\.instruction).joined(separator: "|")
    }

    // MARK: Server, as the model sees it

    private func reroute(from: CLLocationCoordinate2D, to: CLLocationCoordinate2D,
                         via: CLLocationCoordinate2D?, pref: Double,
                         heading: CLLocationDirection?) async throws -> RouteResponse {
        record.rerouteRequests += 1
        if reversing {
            record.revRequests += 1
            if record.revFirstRequestS == nil, let rs = revStart {
                record.revFirstRequestS = t.timeIntervalSince(rs)
                record.revFirstRequestM = s
            }
        }
        if outageActive, let a = outageStart {
            record.outageAttempts.append(t.timeIntervalSince(a))
            record.failedReroutes += 1
            // The production outage is Cloudflare answering 530 for an absent
            // origin; a dead zone is no connection at all.
            if persona == .serverDown || persona == .loopServerDown {
                throw RouteService.ServiceError.unreachable(530)
            }
            throw RouteService.ServiceError.offline
        }
        do {
            let reply = try await server.route(from: from, to: to, via: via, pref: pref,
                                               heading: heading)
            if let b = outageEnd, t >= b, record.recoveryAfterS == nil {
                record.recoveryAfterS = t.timeIntervalSince(b)
            }
            return reply
        } catch {
            record.failedReroutes += 1
            if record.samples.count < 8 { record.samples.append("reroute failed: \(error)") }
            throw error
        }
    }

    // MARK: Voice

    private func heard(_ text: String) {
        if E2E.tracing { traceLines.append("{\"said\": \"\(text)\", \"t\": \(t.timeIntervalSince(t0))}") }
        if reversing {
            record.revUtterances += 1
            if record.revSaid.count < 6 {
                record.revSaid.append("t+\(Int(t.timeIntervalSince(revStart ?? t)))s: \(text)")
            }
        }
        if outageActive { record.outageUtterances += 1 }
        // The detector firing, read off the voice: it says this once per
        // detection, and a reply landing within the same fix clears
        // `wrongWay` before the per-fix measurement could see it.
        if text == "Turn around when possible." {
            record.wrongWayEvents += 1
            if reversing, record.wrongWayFirstS == nil, let rs = revStart {
                record.wrongWayFirstS = t.timeIntervalSince(rs)
                record.wrongWayFirstM = s
            } else if !reversing {
                record.wrongWayFalse += 1
                if record.samples.count < 8 {
                    record.samples.append("t=\(Int(record.simSeconds))s wrong-way fired off the reversal: \(bannerNow)")
                }
            }
        }
        if text.hasPrefix("Turn around") || text.hasPrefix("No connection") {
            if record.recoverySaid.count < 6 {
                record.recoverySaid.append("t=\(Int(t.timeIntervalSince(t0)))s\(reversing ? " (reversing)" : ""): \(text)")
            }
        }
        let kind = text == "You have arrived." ? "arrival"
            : text.hasPrefix("In ") ? "prepare" : "final"
        let cur = model.currentStep
        utterances.append(Utterance(
            text: text, kind: kind, gen: gen,
            sTruth: onModelLine ? s : nil, v: truthSpeed,
            target: cur < stepS.count ? stepS[cur] : nil,
            chainedTarget: text.contains(", then ") && cur + 1 < stepS.count
                ? stepS[cur + 1] : nil))
    }

    // MARK: Driving

    private func isTurnLike(_ step: RouteStep) -> Bool {
        switch step.maneuver {
        case .turn, .fork, .exit, .roundabout, .arrive, .merge: return true
        default: return false
        }
    }

    private func expectedStep(at s: Double) -> Int {
        // First maneuver strictly ahead; stepS is non-decreasing.
        var lo = 0, hi = stepS.count - 1
        guard hi >= 0 else { return 0 }
        if stepS[hi] <= s + 0.5 { return hi }
        while lo < hi {
            let mid = (lo + hi) / 2
            if stepS[mid] > s + 0.5 { hi = mid } else { lo = mid + 1 }
        }
        return lo
    }

    private func speedHere() -> Double {
        if walking { return 1.4 }
        guard onModelLine else { return 12 }
        let exp = expectedStep(at: s)
        let steps = model.steps
        guard exp < steps.count, isTurnLike(steps[exp]) else { return cruise }
        let ahead = stepS[exp] - s
        return ahead < 80 ? max(6, min(cruise, 6 + ahead * 0.15)) : cruise
    }

    func run(_ script: Script) async -> DriveRecord {
        record.ran = true
        var gaps = script.gaps, dwells = script.dwells
        var deviation = script.deviation
        var gapUntil = t0, dwellUntil = t0, parkUntil = t0
        noise = script.noise
        canyonOffset = rng.uniform(0, 240)
        // A dead zone has no network path while it lasts, and the path coming
        // back is what `Connectivity` reports in a real drive.
        if persona == .deadZone || persona == .loopDeadZone {
            model.networkReachable = { [unowned self] in !self.outageActive }
        }
        var restored = false
        var endSince: Date?
        var parkedDone = false
        var lateral = 0.0
        if let start = script.startPath {
            path = start
            onModelLine = false
        }
        let limit = t0.addingTimeInterval(max(1800, planned.feature.properties.minutes * 180 + 1800))

        // First fix: at the start of the route, stationary — a driver tapping
        // "Start" before pulling away.
        await emit(stationary: true, noisy: script.noisy, lateral: &lateral)

        while !model.arrived && t < limit {
            t = t.addingTimeInterval(1)
            var stationary = t < dwellUntil || t < parkUntil
            if !stationary {
                let v = speedHere()
                truthSpeed = v
                let before = s
                s = min(path.length, s + v)
                record.drivenKm += (s - before) / 1000

                if onModelLine && gen == 0 {
                    if let i = gaps.firstIndex(where: { before < $0.s && s >= $0.s }) {
                        gapUntil = t.addingTimeInterval(gaps[i].seconds); gaps.remove(at: i)
                    }
                    if let i = dwells.firstIndex(where: { before < $0.s && s >= $0.s }) {
                        dwellUntil = t.addingTimeInterval(dwells[i].seconds); dwells.remove(at: i)
                    }
                    if let d = deviation, before < d.s, s >= d.s {
                        path = d.path; s = d.into; onModelLine = false; deviation = nil
                        if let o = script.outageSeconds {
                            outageStart = t; outageEnd = t.addingTimeInterval(o); record.outageS = o
                        }
                    }
                    if let r = script.reverse, !reversing, !record.revDone, before < r.at, s >= r.at {
                        // A U-turn on the route itself, then back along it.
                        let back = Array(line.slice(r.at - r.back, r.at).reversed())
                        let fwd = Array(line.slice(r.at - r.back, line.length).dropFirst())
                        path = Polyline(back + fwd)
                        s = 0; onModelLine = false; reversing = true; revStart = t
                        revAt = r.at; revBack = r.back
                        record.revDone = true
                    }
                }
                if reversing, s >= revBack {
                    // Turned round again, having driven `revBack` the wrong way.
                    reversing = false
                    record.revBackM = revBack
                    if gen == 0 {
                        path = line; s = revAt - revBack; onModelLine = true
                        lastExp = expectedStep(at: s); lastStep = model.currentStep
                        lastRemaining = model.remainingMeters
                    }
                }
                if script.earlyStop, onModelLine, !parkedDone, line.length - s <= 150 {
                    parkedDone = true
                    parkUntil = t.addingTimeInterval(120)
                    parkedAt = t
                    // Then walk: the rest of the line, then to the pin. A
                    // pedestrian's path; nothing directional is read off it.
                    path = Polyline(line.slice(s, line.length) + [planned.destination])
                    s = 0; onModelLine = false; walking = true
                }
                if s >= path.length {
                    if onModelLine || walking {
                        endSince = endSince ?? t
                        stationary = true
                        if t.timeIntervalSince(endSince!) > 150 { break }
                    } else {
                        bridge()
                    }
                }
            }
            if stationary { truthSpeed = 0 }
            if !restored, let b = outageEnd, t >= b, persona == .deadZone || persona == .loopDeadZone {
                restored = true
                model.connectivityRestored()
            }
            if t < gapUntil { continue }
            await emit(stationary: stationary, noisy: script.noisy, lateral: &lateral)
        }
        finish()
        return record
    }

    /// The detour ran out before the car reached a line to follow. Straight
    /// to the nearest point of the one the model is following — invented
    /// geometry, so it is counted and reported.
    private func bridge() {
        let here = path.point(at: s)
        let target: (s: Double, offset: Double)
        if joinWindow != nil {
            target = line.project(here, lo: 0, hi: min(line.length, 3000))
        } else {
            target = line.project(here, lo: max(0, lastModelS - 200), hi: lastModelS + 5000)
        }
        record.bridges += 1
        path = Polyline([here] + line.slice(target.s, line.length))
        s = 0
        joinWindow = max(0, target.s - 60)...(target.s + 60)
    }

    private func emit(stationary: Bool, noisy: Bool, lateral: inout Double) async {
        let truth = path.point(at: s)
        var shown = truth
        var accuracy = 5.0, course = path.bearing(at: s), speed = truthSpeed
        if stationary {
            shown = Earth.offset(truth, bearing: rng.uniform(0, 360), meters: rng.uniform(0, 3))
            accuracy = 8; course = -1; speed = 0
        } else if noise == .mild {
            shown = Earth.offset(truth, bearing: course + 90, meters: 3 * rng.gaussian())
            shown = Earth.offset(shown, bearing: course, meters: 2 * rng.gaussian())
            accuracy = rng.uniform(3, 10)
            course = (course + 2 * rng.gaussian() + 360).truncatingRemainder(dividingBy: 360)
        } else if noise == .spike {
            if rng.uniform(0, 1) < 1.0 / 150 {
                shown = Earth.offset(truth, bearing: rng.uniform(0, 360), meters: rng.uniform(220, 450))
                accuracy = rng.uniform(20, 35)
            }
        } else if noise == .canyon {
            let phase = (t.timeIntervalSince(t0) + canyonOffset).truncatingRemainder(dividingBy: 240)
            if phase < 40 {
                lateral = 0.8 * lateral + 0.6 * 35 * rng.gaussian()
                shown = Earth.offset(truth, bearing: course + 90, meters: max(-90, min(90, lateral)))
                accuracy = rng.uniform(30, 60)
            } else {
                lateral = 0
            }
        } else if noisy {
            // AR(1) lateral error with a 10 m standard deviation, capped at
            // 15 m, and a 50 m jump one fix in 150.
            lateral = max(-15, min(15, 0.9 * lateral + 4.36 * rng.gaussian()))
            var off = lateral
            if rng.uniform(0, 1) < 1.0 / 150 { off += (rng.uniform(0, 1) < 0.5 ? -50 : 50) }
            shown = Earth.offset(truth, bearing: course + 90, meters: off)
            shown = Earth.offset(shown, bearing: course, meters: 3 * rng.gaussian())
            accuracy = rng.uniform(10, 30)
            course = (course + 5 * rng.gaussian() + 360).truncatingRemainder(dividingBy: 360)
            speed = max(0, speed + 0.5 * rng.gaussian())
        }
        let fix = CLLocation(coordinate: shown, altitude: 0, horizontalAccuracy: accuracy,
                             verticalAccuracy: 5, course: course, speed: speed, timestamp: t)
        let requestsBefore = record.rerouteRequests
        model.update(fix)
        record.fixes += 1
        // Let a reroute the update spawned run to completion before the next
        // fix: it starts on the main actor, so a yield lets it reach the
        // network call and raise `isRerouting`.
        for _ in 0..<3 { await Task.yield() }
        while model.isRerouting { try? await Task.sleep(for: .milliseconds(1)) }
        observe(truth: truth, rerouted: record.rerouteRequests != requestsBefore)
        if E2E.tracing { traceFix(truth: truth, fix: fix) }
    }

    private func traceFix(truth: CLLocationCoordinate2D, fix: CLLocation) {
        let road: String
        switch model.currentRoad {
        case .named(let r): road = r
        case .offRoute: road = "<off route>"
        case .unknown: road = ""
        }
        let row: [String: Any] = [
            "t": t.timeIntervalSince(t0), "gen": gen, "onLine": onModelLine, "s": s.rounded(),
            "truth": [truth.latitude, truth.longitude],
            "fix": [fix.coordinate.latitude, fix.coordinate.longitude],
            "acc": fix.horizontalAccuracy.rounded(), "speed": fix.speed,
            "step": model.currentStep, "banner": model.currentInstruction,
            "toNext": model.distanceToNext.rounded(), "remaining": model.remainingMeters.rounded(),
            "truthRemaining": onModelLine ? (line.length - s).rounded() : -1,
            "road": road, "arrived": model.arrived, "stalled": model.stalled,
            "requests": record.rerouteRequests,
        ]
        if let data = try? JSONSerialization.data(withJSONObject: row, options: [.sortedKeys]) {
            traceLines.append(String(decoding: data, as: UTF8.self))
        }
    }

    /// The per-fix trace, if one was kept.
    var trace: String { traceLines.joined(separator: "\n") + "\n" }

    // MARK: Measuring

    private func observe(truth: CLLocationCoordinate2D, rerouted: Bool) {
        record.simSeconds = t.timeIntervalSince(t0)
        var adopted = false, merged = false
        if rerouted {
            let coords = model.coordinates
            let sig = Self.signature(coords)
            if sig != lineSig {
                adopted = true
                adopt(coords)
            } else {
                let stepsNow = Self.signature(model.steps)
                if stepsNow != stepsSig {
                    stepsSig = stepsNow
                    stepS = line.alongPositions(of: model.steps.map(\.coordinate))
                }
                merged = true
                record.merges += 1
            }
        }
        if model.stalled {
            record.stalls += 1
            if record.samples.count < 8 { record.samples.append("stalled at t=\(Int(record.simSeconds))s") }
            model.resumeAfterStall()
        }
        if model.arrived {
            record.arrived = true
            record.arrivalPinM = Earth.distance(truth, planned.destination)
            record.arrivalShortM = onModelLine ? line.length - s
                : walking ? path.length - s : nil
            if let p = parkedAt { record.arrivalAfterParkS = t.timeIntervalSince(p) }
            record.endedOnLastStep = model.currentStep == model.steps.count - 1
            return
        }

        // Has the car reached the line the model adopted? Only on a leg
        // running its way, or at the line's own start — a replacement that
        // opens with a U-turn begins at a junction ahead, and the car has to
        // drive there first.
        if let window = joinWindow, !onModelLine {
            let heading = path.bearing(at: s)
            let hi = min(line.length, window.upperBound)
            let aligned = line.projectAligned(truth, bearing: heading, maxAngle: 90,
                                              lo: window.lowerBound, hi: hi)
            var at: Double?
            if aligned.offset <= 15 {
                at = aligned.s
            } else if window.lowerBound == 0, Earth.distance(truth, line.coords[0]) <= 15 {
                at = 0
                record.uTurnJoins += 1
            }
            if let at {
                if gen >= 1, let opening = openings[gen], at <= opening.s + 30 {
                    joinedOpenings.append(gen)
                }
                if reversing { record.revJoinedNew = true; record.revBackM = s; reversing = false }
                path = line; s = at; onModelLine = true; walking = false
                joinWindow = nil; joinS = s
                lastExp = expectedStep(at: s)
                lastStep = model.currentStep
                lastRemaining = model.remainingMeters
            }
        }

        if reversing, let rs = revStart {
            switch model.currentRoad {
            case .offRoute: record.revRoadOff += 1
            case .named: record.revRoadNamed += 1
            case .unknown: record.revRoadUnknown += 1
            }
            let since = Int(t.timeIntervalSince(rs))
            if since % 10 == 0, record.revBanner.count < 30 {
                record.revBanner.append("t+\(since)s back \(Int(s)) m req=\(record.revRequests): \(bannerNow)")
            }
        }
        if outageActive, let a = outageStart {
            record.outageFixes += 1
            if model.isRerouting { record.outageRerouting += 1 }
            let since = Int(t.timeIntervalSince(a))
            if since % 15 == 0, record.outageBanner.count < 20 {
                record.outageBanner.append("t+\(since)s: \(bannerNow)")
            }
        }
        if onModelLine && !adopted {
            measureOnLine(merged: merged)
        } else if !onModelLine && !walking {
            let hit = line.project(truth, lo: max(0, lastModelS - 300), hi: lastModelS + 3000)
            if joinWindow == nil, hit.offset > 60 {
                record.offTicks += 1
                deviationStart = deviationStart ?? t
                if hit.offset > 80, case .named(let road) = model.currentRoad {
                    record.namedWhileOff += 1
                    if record.samples.count < 8 {
                        record.samples.append("t=\(Int(record.simSeconds))s \(Int(hit.offset)) m off the line, screen names \(road)")
                    }
                }
            }
        }
    }

    private func adopt(_ coords: [CLLocationCoordinate2D]) {
        let old = line
        let oldS = onModelLine ? s : lastModelS
        gen += 1
        record.adoptions += 1
        line = Polyline(coords)
        lineSig = Self.signature(coords)
        stepS = line.alongPositions(of: model.steps.map(\.coordinate))
        stepsSig = Self.signature(model.steps)
        if let first = model.steps.first, let s0 = stepS.first {
            openings[gen] = (s0, first.instruction)
        }
        if let start = deviationStart {
            record.rerouteLatencyS.append(t.timeIntervalSince(start))
            deviationStart = nil
        }
        // Is the "new" line the road already being driven? Every 50 m of it
        // within 5 m of the old line, ahead of the car.
        var same = line.length > 0
        var k = 0.0
        while same && k <= line.length {
            if old.project(line.point(at: k), lo: max(0, oldS - 300)).offset > 5 { same = false }
            k += 50
        }
        if same {
            record.suffixAdoptions += 1
            if record.samples.count < 8 {
                record.samples.append("t=\(Int(record.simSeconds))s adopted a line that is the one being driven (\(Int(line.length)) m)")
            }
        }
        onModelLine = false
        joinWindow = 0...min(line.length, 3000)
        lastModelS = 0
        lastBanner = ""
        bannersSeen = []
    }

    private func measureOnLine(merged: Bool) {
        defer { lastFixT = t }
        lastModelS = s
        let noisy = persona == .noisy
        let tol = noisy ? 25.0 : 3.0
        let cur = model.currentStep
        let n = stepS.count
        let exp = expectedStep(at: s)
        let steps = model.steps

        if cur < n {
            let behind = s - stepS[cur]
            if behind > (cur == 0 ? tol + 30 : tol) {
                record.bannerBehind += 1
                record.maxBehindM = max(record.maxBehindM, behind)
                if record.samples.count < 8 {
                    record.samples.append("t=\(Int(record.simSeconds))s banner \"\(steps[cur].instruction)\" is \(Int(behind)) m behind the car")
                }
            }
            if cur > exp, stepS[exp] > s + tol {
                record.bannerSkipped += 1
                if record.samples.count < 8 {
                    record.samples.append("t=\(Int(record.simSeconds))s banner skipped \"\(steps[exp].instruction)\" \(Int(stepS[exp] - s)) m ahead")
                }
            }
            // Within a kilometre of the maneuver, where the number is acted
            // on. Further out the two instruments' metres-per-degree differ by
            // ~0.1-0.2% (the app's 111,320 against a great circle's 111,195;
            // neither is the ellipsoid), which is tens of metres at 15 km and
            // not a finding.
            let truthAhead = stepS[cur] - s
            if cur == exp, truthAhead <= 1000 {
                let err = abs(model.distanceToNext - truthAhead)
                distErrs.append(err)
                record.distChecked += 1
                if err > 30 {
                    record.distOver30 += 1
                    if record.samples.count < 8 {
                        record.samples.append("t=\(Int(record.simSeconds))s shows \(Int(model.distanceToNext)) m to \"\(steps[cur].instruction)\", truth \(Int(truthAhead)) m")
                    }
                }
            }
        }
        remErrs.append(abs(model.remainingMeters - (line.length - s)))

        // The road readout, against the instruction the truth last drove
        // through — away from the maneuvers, where "which leg" is a matter of
        // metres.
        if exp >= 1, exp - 1 < steps.count, s - stepS[exp - 1] > 20,
           exp >= n - 1 || stepS[exp] - s > 20 {
            switch model.currentRoad {
            case .named(let shown):
                if let expected = roadNamed(inInstruction: steps[exp - 1].instruction) {
                    record.streetChecked += 1
                    if shown != expected {
                        record.streetMismatch += 1
                        if record.samples.count < 8 {
                            record.samples.append("t=\(Int(record.simSeconds))s street shows \(shown), driven through \"\(steps[exp - 1].instruction)\"")
                        }
                    }
                }
            case .offRoute:
                if s - joinS > 60 { record.falseOffRoute += 1 }
            case .unknown:
                break
            }
        }

        // Monotonicity, except where the model was handed a new step list.
        if !merged {
            if cur < lastStep {
                record.stepBackwards += 1
                if record.samples.count < 8 {
                    record.samples.append("t=\(Int(record.simSeconds))s step went back \(lastStep) -> \(cur)")
                }
            }
            let rise = model.remainingMeters - lastRemaining
            if rise > (noisy ? 50 : persona == .stopAndGo ? 10 : 1) {
                record.remainingRises += 1
                record.maxRiseM = max(record.maxRiseM, rise)
            }
        }
        lastStep = cur
        lastRemaining = model.remainingMeters

        let banner = model.currentInstruction
        if banner != lastBanner {
            record.bannerChanges += 1
            if bannersSeen.contains(banner) { record.flicker += 1 }
            bannersSeen.insert(banner)
            lastBanner = banner
        }

        if exp > lastExp {
            // A maneuver crossed while no fixes were arriving (a tunnel) was
            // never the voice's to announce; counted apart.
            let gap = lastFixT.map { t.timeIntervalSince($0) > 5 } ?? false
            for k in lastExp..<exp where k >= 1 && k < n - 1 {
                if gap { record.passedInGap += 1 } else {
                    passed.append(Passed(gen: gen, s: stepS[k], joinS: joinS))
                }
            }
            lastExp = exp
        }
    }

    private func finish() {
        record.maneuversPassed = passed.count
        for g in joinedOpenings {
            guard let opening = openings[g] else { continue }
            record.openingsDriven += 1
            let spoken = utterances.contains { u in
                u.gen == g && u.kind == "final" && (u.target.map { abs($0 - opening.s) < 5 } ?? false)
            }
            if !spoken {
                record.openingsUnspoken += 1
                if record.samples.count < 8 {
                    record.samples.append("gen \(g) opened with \"\(opening.text)\", never spoken")
                }
            }
        }
        record.distErrP50 = percentile(distErrs, 50)
        record.distErrP95 = percentile(distErrs, 95)
        record.distErrMax = distErrs.max()
        record.remainingErrP95 = percentile(remErrs, 95)

        for p in passed {
            let matching = utterances.filter { u in
                u.gen == p.gen && u.kind == "final" && u.sTruth != nil
                    && ((u.target.map { abs($0 - p.s) < 5 } ?? false)
                        || (u.chainedTarget.map { abs($0 - p.s) < 5 } ?? false))
            }
            guard let last = matching.max(by: { $0.sTruth! < $1.sTruth! }) else {
                record.missingPrompts += 1
                if p.s - p.joinS < 150 { record.missingNearStart += 1 }
                continue
            }
            let lead = p.s - last.sTruth!
            if lead < 0 { record.latePrompts += 1 }
            record.finalLeadM.append((lead * 10).rounded() / 10)
            record.finalLeadS.append((lead / (last.v >= 1 ? last.v : cruise) * 10).rounded() / 10)
            if let prep = utterances.first(where: { u in
                u.gen == p.gen && u.kind == "prepare" && u.sTruth != nil
                    && (u.target.map { abs($0 - p.s) < 5 } ?? false)
            }) {
                let lead = p.s - prep.sTruth!
                record.prepareLeadS.append((lead / (prep.v >= 1 ? prep.v : cruise) * 10).rounded() / 10)
            }
        }

        // The hard failures.
        var v: [String] = []
        if !record.arrived { v.append("never arrived") }
        if record.stepBackwards > 0 { v.append("step went backwards \(record.stepBackwards)x") }
        if record.remainingRises > 0 && persona != .noisy {
            v.append("remaining rose \(record.remainingRises)x (max \(Int(record.maxRiseM)) m)")
        }
        if record.suffixAdoptions > 0 { v.append("adopted the line already driven \(record.suffixAdoptions)x") }
        if persona.staysOnRoute && persona != .noisy && record.rerouteRequests > 0 {
            v.append("\(record.rerouteRequests) reroute(s) on a drive that never left the road")
        }
        if persona == .noisy && record.drivenKm > 0
            && Double(record.rerouteRequests) / record.drivenKm > 0.1 {
            v.append("noisy GPS rerouted \(record.rerouteRequests)x over \(Int(record.drivenKm)) km")
        }
        if record.bannerBehind > 0, persona != .noisy { v.append("banner behind the car \(record.bannerBehind)x (max \(Int(record.maxBehindM)) m)") }
        if record.bannerSkipped > 0, persona != .noisy { v.append("banner skipped a maneuver \(record.bannerSkipped)x") }
        // Only when the whole line was driven: arriving beside the pin, with
        // the last maneuver still ahead, is arriving.
        if persona == .perfect, record.arrived, record.endedOnLastStep == false,
           (record.arrivalShortM ?? .infinity) <= 40 {
            v.append("arrived on step \(model.currentStep) of \(model.steps.count - 1)")
        }
        if let short = record.arrivalShortM, short > 100, persona != .earlyStop,
           (record.arrivalPinM ?? 0) > 60 {
            v.append("arrived \(Int(short)) m short along the route")
        }
        record.violations = v
    }
}

/// Putting a persona on a route: the script, and for the personas that
/// leave the road, the real road geometry they leave it by.
@MainActor
enum Staging {

    enum Staged {
        case script(Script, String?)
        case unstageable(String)
    }

    static func stage(_ persona: Persona, _ route: PlannedRoute) async throws -> Staged {
        var rng = SeededRNG(route.key + ":" + persona.rawValue + ":stage")
        let line = Polyline(route.feature.coordinates)
        let steps = route.feature.properties.steps
        let stepS = line.alongPositions(of: steps.map(\.coordinate))
        var script = Script()

        switch persona {
        case .perfect, .loopPerfect:
            break
        case .noisy:
            script.noisy = true
        case .dropout:
            var at = 1500.0
            while at < line.length - 500 {
                script.gaps.append((at, rng.uniform(20, 90)))
                at += rng.uniform(3000, 6000)
            }
            if script.gaps.isEmpty { return .unstageable("route under 2 km: no room for a gap") }
        case .stopAndGo:
            for k in steps.indices where k >= 1 && k < steps.count - 1 && stepS[k] > 50 {
                guard [.turn, .fork, .exit, .roundabout].contains(steps[k].maneuver) else { continue }
                if rng.uniform(0, 1) < 0.4, script.dwells.count < 15 {
                    script.dwells.append((stepS[k] - 12, rng.uniform(20, 60)))
                }
            }
            if script.dwells.isEmpty,
               let k = steps.indices.first(where: { $0 >= 1 && $0 < steps.count - 1 && stepS[$0] > 50 }) {
                script.dwells.append((stepS[k] - 12, rng.uniform(20, 60)))
            }
            if script.dwells.isEmpty { return .unstageable("no maneuver to stop at") }
        case .earlyStop:
            script.earlyStop = true
            if line.length < 600 { return .unstageable("route under 600 m") }
        case .missedTurn:
            return try await missedTurn(route, line, steps, stepS,
                                        window: 400...(line.length - 700), prefer: 0.4)
        case .loopLate, .loopEarly:
            guard let turn = route.turnaround else { return .unstageable("not a loop") }
            let turnS = line.project(turn).s
            let window = persona == .loopLate
                ? (turnS + 300)...(line.length - 700)
                : (0.1 * line.length)...(turnS - 700)
            guard window.lowerBound < window.upperBound else {
                return .unstageable("no room \(persona == .loopLate ? "after" : "before") the far point")
            }
            return try await missedTurn(route, line, steps, stepS, window: window,
                                        prefer: persona == .loopLate ? 0.75 : 0.25)
        case .wrongWayStart:
            return try await wrongWay(route, line)
        case .wrongWayAlong, .loopWrongWay:
            let at: Double
            if persona == .loopWrongWay {
                guard let turn = route.turnaround else { return .unstageable("not a loop") }
                let turnS = line.project(turn).s
                at = max(2500, min(0.3 * line.length, turnS - 1000))
            } else {
                at = max(2000, 0.4 * line.length)
            }
            let back = min(2000, at - 300)
            guard at < line.length - 1500, back >= 800 else {
                return .unstageable("route too short to drive back along")
            }
            script.reverse = (at, back)
            return .script(script, "U-turn on the route at \(Int(at)) m, \(Int(back)) m back along it")
        case .serverDown, .loopServerDown, .deadZone, .loopDeadZone:
            let staged: Staged
            if persona == .serverDown || persona == .deadZone {
                staged = try await missedTurn(route, line, steps, stepS,
                                              window: 400...(line.length - 700), prefer: 0.4, far: true)
            } else {
                guard let turn = route.turnaround else { return .unstageable("not a loop") }
                let turnS = line.project(turn).s
                staged = try await missedTurn(route, line, steps, stepS,
                                              window: (0.1 * line.length)...(turnS - 700), prefer: 0.25, far: true)
            }
            guard case .script(var s2, let note) = staged else { return staged }
            s2.outageSeconds = 180
            return .script(s2, (note ?? "") + "; server down for 180 s from the deviation")
        case .spike, .loopSpike:
            script.noise = .spike
        case .canyon, .loopCanyon:
            script.noise = .canyon
        case .loopMild:
            script.noise = .mild
        }
        return .script(script, nil)
    }

    /// Carry on past maneuver k along a road the server routes, not a line
    /// extrapolated off the route: a route from just before the junction,
    /// heading as the car approaches it, to a point 500-700 m on past it. The
    /// server picks the road; this only keeps the ones that actually leave the
    /// route.
    static func missedTurn(_ route: PlannedRoute, _ line: Polyline, _ steps: [RouteStep],
                            _ stepS: [Double], window: ClosedRange<Double>,
                            prefer: Double, far: Bool = false) async throws -> Staged {
        guard window.lowerBound < window.upperBound else {
            return .unstageable("route too short to miss a turn and still be rerouted")
        }
        let candidates = steps.indices.filter { k in
            k >= 1 && k < steps.count - 1 && window.contains(stepS[k])
                && [.turn, .fork, .exit].contains(steps[k].maneuver)
                && steps[k].modifier.map { $0 != "straight" } ?? false
        }.sorted { abs(stepS[$0] - prefer * line.length) < abs(stepS[$1] - prefer * line.length) }
        guard !candidates.isEmpty else {
            return .unstageable("no turn, fork or exit in \(Int(window.lowerBound))...\(Int(window.upperBound)) m "
                                + "of \(Int(line.length)); maneuvers at "
                                + stepS.map { String(Int($0)) }.joined(separator: ","))
        }

        var rejects: [String] = []
        for k in candidates.prefix(3) {
            let js = stepS[k]
            let junction = line.point(at: js)
            let approach = Earth.bearing(line.point(at: max(0, js - 40)), junction)
            let from = line.point(at: max(0, js - 25))
            let reach: [(Double, Double)] = far ? [(3000.0, 0.0), (2500, -35), (2500, 35), (1500, 0)]
                                                : [(700.0, 0.0), (500, -35), (500, 35)]
            for (d, off) in reach {
                let target = Earth.offset(junction, bearing: approach + off, meters: d)
                let response: RouteResponse
                do {
                    response = try await E2EServer.shared.route(from: from, to: target, pref: 0,
                                                                heading: approach)
                } catch E2EServer.Failure.down(let e) {
                    throw XCTSkip("server went away: \(e.code.rawValue)")
                } catch E2EServer.Failure.refused {
                    continue
                }
                let detour = Polyline(response.fastest.coordinates)
                guard detour.length > 300 else { rejects.append("k\(k) short"); continue }
                let entry = detour.project(junction, lo: 0, hi: min(detour.length, 200))
                guard entry.offset <= 20, detour.length - entry.s > (far ? 1200 : 250) else {
                    rejects.append("k\(k) misses junction by \(Int(entry.offset)) m"); continue
                }
                let probe = detour.point(at: entry.s + 250)
                let apart = line.project(probe, lo: max(0, js - 300), hi: js + 3000).offset
                guard apart > 50 else { rejects.append("k\(k) rejoins (\(Int(apart)) m)"); continue }
                var script = Script()
                script.deviation = (js, detour, entry.s)
                return .script(script, "missed step \(k) \"\(steps[k].instruction)\" at "
                               + "\(Int(js)) m; took a real road \(Int(off))° off straight, "
                               + "\(Int(detour.length - entry.s)) m of it")
            }
        }
        return .unstageable("no real road leaves the candidate junctions away from the route: "
                            + rejects.joined(separator: "; "))
    }

    /// Set off the wrong way: a server route from the start, heading opposite
    /// to the route's first leg, to a point 400-500 m behind.
    static func wrongWay(_ route: PlannedRoute, _ line: Polyline) async throws -> Staged {
        guard line.length > 1200 else { return .unstageable("route under 1.2 km") }
        let start = line.coords[0]
        let ahead = line.bearing(at: 20)
        let back = (ahead + 180).truncatingRemainder(dividingBy: 360)
        var rejects: [String] = []
        // With the reversed heading first; the server then snaps to the far end
        // of the road the car is on, which can be hundreds of metres off, so
        // the same targets again with no heading, which starts at the route's
        // own first node.
        let tries: [(Double, Double, Double?)] = [(500, 0, back), (400, -35, back), (400, 35, back),
                                                  (500, 0, nil), (400, -35, nil), (400, 35, nil)]
        for (d, off, heading) in tries {
            let target = Earth.offset(start, bearing: back + off, meters: d)
            let response: RouteResponse
            do {
                response = try await E2EServer.shared.route(from: start, to: target, pref: 0,
                                                            heading: heading)
            } catch E2EServer.Failure.down(let e) {
                throw XCTSkip("server went away: \(e.code.rawValue)")
            } catch E2EServer.Failure.refused {
                continue
            }
            var coords = response.fastest.coordinates
            guard let first = coords.first else { continue }
            let gap = Earth.distance(start, first)
            guard gap <= 60 else { rejects.append("starts \(Int(gap)) m away"); continue }
            if gap > 1 { coords.insert(start, at: 0) }
            let path = Polyline(coords)
            let apart = line.project(path.point(at: 200), lo: 0, hi: 2000).offset
            guard path.length > 250, apart > 40 else {
                rejects.append("\(Int(path.length)) m, \(Int(apart)) m from the route at 200 m"); continue
            }
            var script = Script()
            script.startPath = path
            return .script(script, "set off \(Int(path.length)) m the wrong way"
                           + (gap > 1 ? " (joined to its start by \(Int(gap)) m of straight line)" : ""))
        }
        return .unstageable("no real road leaves the start away from the route: "
                            + rejects.joined(separator: "; "))
    }

}
