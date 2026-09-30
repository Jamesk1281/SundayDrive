import CoreLocation
import XCTest
@testable import SundayDrive

/// One simulated drive: a persona's timed fix stream through the real
/// `NavigationModel`, against the real local server, measured by an instrument
/// that is not the model's own. See docs/overnight-e2e-drives-brief.md.
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

    var isLoop: Bool { [.loopPerfect, .loopLate, .loopEarly].contains(self) }
    /// Personas that never leave the road; any reroute they cause is the
    /// model's doing.
    var staysOnRoute: Bool { [.perfect, .noisy, .dropout, .stopAndGo, .earlyStop, .loopPerfect].contains(self) }
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
    var detour: String?
    var violations: [String] = []
    var samples: [String] = []
}

/// Behaviour a persona adds on top of driving the line.
struct Script {
    var noisy = false
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
        do {
            return try await server.route(from: from, to: to, via: via, pref: pref,
                                          heading: heading)
        } catch {
            record.failedReroutes += 1
            if record.samples.count < 8 { record.samples.append("reroute failed: \(error)") }
            throw error
        }
    }

    // MARK: Voice

    private func heard(_ text: String) {
        if E2E.tracing { traceLines.append("{\"said\": \"\(text)\", \"t\": \(t.timeIntervalSince(t0))}") }
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
                path = line; s = at; onModelLine = true; walking = false
                joinWindow = nil; joinS = s
                lastExp = expectedStep(at: s)
                lastStep = model.currentStep
                lastRemaining = model.remainingMeters
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
