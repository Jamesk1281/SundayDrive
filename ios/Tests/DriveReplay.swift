import CoreLocation
import Foundation
@testable import SundayDrive

/// Replays a drive recorded by `DriveTrace` back through `NavigationModel`.
///
/// The fixture routes in `RouteFixtures` are straight lines with four
/// maneuvers, which is the right shape for testing one rule at a time and the
/// wrong shape for testing anything about a *drive*. These are the real thing:
/// 1,400 to 6,700 point polylines, GPS that wanders, cars that stop at lights,
/// and — the reason this exists — 53 real reroutes, 8 of which handed back the
/// line already being driven.
///
/// The traces are gitignored on purpose: they are a record of where someone
/// drove. So this finds them wherever they are and the tests skip when they are
/// not there, rather than a copy being committed.
enum DriveReplay {

    // MARK: - Finding the recordings

    /// The `traces/` directory, searched for by walking up from this file.
    ///
    /// Walking up rather than a fixed path because `data/`, `.venv` and the
    /// traces live in the **main checkout** and never in a worktree — from
    /// `<repo>/.claude/worktrees/<name>/ios/Tests` the walk climbs out of the
    /// worktree and finds the real one.
    ///
    /// `SUNDAYDRIVE_TRACES` overrides it for a copy kept elsewhere (the
    /// pre-rename `VICTORYLAP_TRACES` and `SCENIC_TRACES` still work for one
    /// release), but note it
    /// cannot be set on the `xcodebuild` command line: these are app-hosted
    /// unit tests, so neither a bare variable nor the `TEST_RUNNER_` prefix
    /// reaches the process that reads `ProcessInfo`. It has to go in the
    /// scheme's test action in `ios/project.yml`.
    static func directory(from file: String = #filePath) -> URL? {
        let env = ProcessInfo.processInfo.environment
        if let override = env["SUNDAYDRIVE_TRACES"] ?? env["VICTORYLAP_TRACES"]
                            ?? env["SCENIC_TRACES"] {
            return URL(fileURLWithPath: override)
        }
        var directory = URL(fileURLWithPath: file).deletingLastPathComponent()
        while directory.path != "/" {
            let candidate = directory.appendingPathComponent("traces")
            if let names = try? FileManager.default.contentsOfDirectory(atPath: candidate.path),
               names.contains(where: { $0.hasSuffix(".ndjson") }) {
                return candidate
            }
            directory = directory.deletingLastPathComponent()
        }
        return nil
    }

    static func recordings() -> [RecordedDrive] {
        guard let directory = directory(),
              let names = try? FileManager.default.contentsOfDirectory(atPath: directory.path)
        else { return [] }
        return names.filter { $0.hasSuffix(".ndjson") }.sorted().compactMap {
            RecordedDrive(contentsOf: directory.appendingPathComponent($0))
        }
    }

    // MARK: - One recorded drive

    struct RecordedDrive {
        let name: String
        let destination: CLLocationCoordinate2D
        let pref: Double
        let weights: [String: Double]
        /// Every route the drive was handed, in the order it was handed them —
        /// the first is the one it set off on.
        let routes: [RouteFeature]
        /// When each of those was recorded — see `Tape.Mode.asRecorded`.
        let routeTimes: [Date]
        let fixes: [CLLocation]

        init?(contentsOf url: URL) {
            guard let text = try? String(contentsOf: url, encoding: .utf8) else { return nil }
            var header: [String: Any]?
            var routes: [RouteFeature] = []
            var routeTimes: [Date] = []
            var fixes: [CLLocation] = []

            for line in text.split(separator: "\n", omittingEmptySubsequences: true) {
                guard let data = line.data(using: .utf8),
                      let record = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                else { continue }
                switch record["t"] as? String {
                case "drive": header = record
                case "route":
                    if let feature = DriveReplay.feature(from: record) {
                        routes.append(feature)
                        routeTimes.append(Date(timeIntervalSince1970: record["ts"] as? Double ?? 0))
                    }
                case "fix":
                    if let fix = DriveReplay.location(from: record) { fixes.append(fix) }
                default: break
                }
            }

            guard let header, !routes.isEmpty, fixes.count > 1,
                  let dest = header["dest"] as? [Double], dest.count == 2 else { return nil }
            self.name = url.lastPathComponent
            self.destination = CLLocationCoordinate2D(latitude: dest[0], longitude: dest[1])
            self.pref = header["pref"] as? Double ?? 0.5
            self.weights = header["weights"] as? [String: Double] ?? [:]
            self.routes = routes
            self.routeTimes = routeTimes
            self.fixes = fixes
        }

        /// How many of the replacement routes repeated the line before them.
        /// The case the announcement latch exists for.
        var sameLineReplies: Int {
            zip(routes, routes.dropFirst()).count { previous, next in
                previous.coordinates.count == next.coordinates.count
                    && zip(previous.coordinates, next.coordinates).allSatisfy { $0.matches($1) }
            }
        }
    }

    // MARK: - Decoding

    /// A `route` record back into the `RouteFeature` the app decoded from the
    /// server, via the same `Decodable` path so a field renamed on either side
    /// shows up here.
    ///
    /// `scenery_km` is supplied empty because the trace does not record it —
    /// nothing in navigation reads it, and `RouteProps` requires it.
    private static func feature(from record: [String: Any]) -> RouteFeature? {
        guard let coords = record["coords"] as? [[Double]],
              let steps = record["steps"] as? [[String: Any]] else { return nil }
        let object: [String: Any] = [
            "geometry": ["coordinates": coords],
            "properties": [
                "km": record["km"] as? Double ?? 0,
                "minutes": record["minutes"] as? Double ?? 0,
                "mean_score": record["mean_score"] as? Double ?? 0,
                "scenery_km": [String: Double](),
                // Dropping empty `type` and `modifier` rather than passing them
                // through: the writer stores "" for "the server sent none", and
                // the app's own decoder would read that as an unrecognised
                // maneuver rather than an absent one. The 2026-08-14 traces
                // predate both fields entirely and simply have no key.
                "steps": steps.map { step -> [String: Any] in
                    var out = step
                    for key in ["type", "modifier"] where (step[key] as? String)?.isEmpty ?? false {
                        out.removeValue(forKey: key)
                    }
                    return out
                },
            ],
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: object) else { return nil }
        return try? JSONDecoder().decode(RouteFeature.self, from: data)
    }

    /// A `fix` record back into the `CLLocation` the delegate handed over.
    ///
    /// Speed and course are logged raw, negatives and all, which is the point:
    /// CoreLocation's "no opinion" is a case the schedule has to survive and
    /// there is no better source of real ones than a real drive.
    private static func location(from record: [String: Any]) -> CLLocation? {
        guard let lat = record["lat"] as? Double, let lon = record["lon"] as? Double,
              let ts = record["ts"] as? Double else { return nil }
        return CLLocation(
            coordinate: CLLocationCoordinate2D(latitude: lat, longitude: lon),
            altitude: record["alt"] as? Double ?? 0,
            horizontalAccuracy: record["acc"] as? Double ?? 5,
            verticalAccuracy: record["valt"] as? Double ?? 5,
            course: record["crs"] as? Double ?? -1,
            speed: record["spd"] as? Double ?? -1,
            timestamp: Date(timeIntervalSince1970: ts))
    }

    // MARK: - Running one

    /// What a replay heard, and enough about the drive to know the run was not
    /// vacuous.
    struct Outcome {
        var name = ""
        var said: [String] = []
        /// Maneuvers the drive actually approached — the ceiling on how much
        /// there was to say.
        var maneuversApproached = 0
        /// Replacement routes handed over during *this* replay. Not necessarily
        /// the recording's count: the code deciding when to ask has changed.
        var repliesGiven = 0
        /// Of those, the ones that repeated the line already being followed.
        var sameLineReplies = 0
        /// Any maneuver announced twice with no genuinely different route in
        /// between. Must stay empty; it is the whole point of the latch.
        ///
        /// Keyed on the maneuver's *place* as well as its words, for the same
        /// reason the latch is. Keyed on words alone this reported a repeat on
        /// the 2026-08-14 evening drive that was nothing of the kind: its route
        /// turns left onto Washington Street at two junctions 11 km apart, and
        /// both deserve saying.
        var repeatsWithoutARouteChange: [String] = []
        /// Fixes on which the step list described the road the car was on —
        /// the only ones anything can be said from. A drive that is quiet
        /// because it spent the whole time off-route is behaving correctly; one
        /// that is quiet with this high is not.
        var describableFixes = 0
        var arrived = false
        /// Seconds from the first fix to the one that paused the drive, or nil
        /// if it never paused. See `NavigationModel.stalled`.
        var stalledAfter: TimeInterval?
        /// How many fixes were fed before the drive ended or paused itself, or
        /// all of them if it did neither.
        var fixesFed = 0
        /// When each reroute was asked for, in seconds from the first fix.
        var requestsAt: [Double] = []
        /// When each utterance was heard, in seconds from the first fix.
        var saidAt: [Double] = []
        /// When "Turn around when possible." was said — the wrong-way
        /// detector firing — in seconds from the first fix, in either of its
        /// two wordings. Read off the voice rather than `wrongWay`, which a
        /// reply landing within the same fix clears before anything outside
        /// the model can see it.
        var wrongWayAt: [Double] {
            zip(said, saidAt).filter { DriveReplay.isWrongWayLine($0.0) }.map(\.1)
        }
        /// Requests the tape failed — see `Tape.Mode.asRecorded`.
        var failedRequests = 0
        /// When the wrong-way banner timed out and gave way to the off-route
        /// one, in seconds from the first fix (docs/mid-drive-recovery.md,
        /// the time-out).
        var wrongWayTimeoutsAt: [Double] = []
        /// The banner each time it changed: seconds from the first fix, then
        /// what it said. Rendered by the real `NavView.bannerText`.
        var banners: [(at: Double, banner: NavView.BannerText)] = []
    }

    static let wrongWayLine = "Turn around when possible."

    /// The detector's line, plain or with no network path on the detecting
    /// fix, when it is "No connection. Turn around when possible."
    /// (docs/mid-drive-recovery.md, the time-out). Matching the plain line
    /// exactly would lose a detection in a dead zone and leave every count
    /// that asserts on it passing by accident.
    static func isWrongWayLine(_ text: String) -> Bool { text.hasSuffix(wrongWayLine) }

    /// How the tape answers a reroute request.
    enum Mode {
        /// The next recorded route, whenever asked: what the drive was given,
        /// in order. A replay that asks at a moment the drive did not gets a
        /// route recorded somewhere else.
        case inOrder
        /// The next recorded route only once the drive is within 30 s of when
        /// it really landed; every request before that fails, as the drive's
        /// own must have, since nothing landed (P-04,
        /// docs/mid-drive-recovery.md). What lets a replay reach a stretch the
        /// drive spent on a line it could not replace.
        case asRecorded
    }

    /// Mutable replay state, in a class because `fetchRoute` is called from a
    /// `Task` and captured `var`s would be a race.
    private final class Tape {
        var nextRoute = 1
        var repliesHandedOut = 0
        /// Replies that handed back the line already being followed — decided
        /// here, where both the reply and the route in force are in hand.
        var sameLineReplies = 0
        var requestsAt: [Double] = []
        var failed = 0
    }

    /// Feed a recorded drive through a real `NavigationModel` with a real
    /// `VoiceGuide` and a fake speaker.
    ///
    /// Time comes from the fixes, not the wall clock. Without that the reroute
    /// cooldown — eight seconds, backing off to two minutes — never elapses
    /// during a replay that takes half a second, and a drive that really
    /// re-routed thirteen times would exercise one.
    @MainActor
    static func run(_ drive: RecordedDrive, speaker: VoiceGuideTests.FakeSpeaker,
                    mode: Mode = .inOrder) async -> Outcome {
        var outcome = Outcome()
        outcome.name = drive.name
        let voice = VoiceGuide(speaker: speaker, muted: false)
        let model = NavigationModel(route: drive.routes[0], destination: drive.destination,
                                    pref: drive.pref, weights: drive.weights, voice: voice)

        var clock = drive.fixes[0].timestamp
        model.now = { clock }

        let tape = Tape()
        model.fetchRoute = { [weak model] _, _, _, _, _ in
            tape.repliesHandedOut += 1
            tape.requestsAt.append((clock.timeIntervalSince(drive.fixes[0].timestamp) * 10).rounded() / 10)
            let inForce = await model?.route.coordinates ?? []
            let feature: RouteFeature
            if mode == .asRecorded, tape.nextRoute < drive.routes.count,
               clock < drive.routeTimes[tape.nextRoute].addingTimeInterval(-30) {
                tape.failed += 1
                throw RouteService.ServiceError.offline
            }
            if tape.nextRoute < drive.routes.count {
                feature = drive.routes[tape.nextRoute]
                tape.nextRoute += 1
            } else if let current = await model?.route {
                // Out of recorded replacements. Handing back the line already
                // being followed is what the server really does when the driver
                // has strayed and this is still the best way there — and it
                // keeps the same-line path under test for the rest of the drive.
                feature = current
            } else {
                feature = drive.routes[0]
            }
            let coords = feature.coordinates
            if coords.count == inForce.count,
               zip(coords, inForce).allSatisfy({ $0.matches($1) }) {
                tape.sameLineReplies += 1
            }
            return RouteResponse(fastest: feature, scenic: feature)
        }

        // Everything said since the route last genuinely changed. A maneuver
        // appearing in here twice is the defect: the same line handed back must
        // not restart the commentary.
        var saidSinceRouteChange: Set<String> = []
        var heard = 0
        var deepestStep = 0
        var describable = 0
        var timedOut = false
        let location = LocationManager()

        for fix in drive.fixes {
            outcome.fixesFed += 1
            clock = fix.timestamp
            let before = model.route.coordinates
            model.update(fix)

            // Let a reroute Task started by this fix finish. The stub above
            // never suspends, so this settles in a yield or two; the bound is
            // there so a hang fails this test rather than the whole suite.
            var spins = 0
            repeat {
                await Task.yield()
                spins += 1
            } while model.isRerouting && spins < 500

            let after = model.route.coordinates
            let sameLine = after.count == before.count
                && zip(before, after).allSatisfy { $0.matches($1) }
            if !sameLine {
                // A genuinely different line. Everything already said belongs
                // to a route the driver is no longer on, so saying it again is
                // correct rather than a repeat.
                saidSinceRouteChange = []
            }

            if model.stepsDescribeWhereWeAre { describable += 1 }

            let at = fix.timestamp.timeIntervalSince(drive.fixes[0].timestamp)
            if model.wrongWayTimedOut, !timedOut { outcome.wrongWayTimeoutsAt.append(at) }
            timedOut = model.wrongWayTimedOut
            let banner = NavView.bannerText(nav: model, location: location)
            if outcome.banners.last?.banner != banner { outcome.banners.append((at, banner)) }

            if speaker.said.count != heard {
                // Anchored to the maneuver being approached, which cannot have
                // moved since: the utterance was produced inside this same
                // `update`.
                let place = model.steps.indices.contains(model.currentStep)
                    ? model.steps[model.currentStep].coordinate
                    : model.destination
                for text in speaker.said[heard...] {
                    let key = String(format: "%.5f,%.5f|", place.latitude, place.longitude) + text
                    if saidSinceRouteChange.contains(key) {
                        outcome.repeatsWithoutARouteChange.append(key)
                    }
                    saidSinceRouteChange.insert(key)
                }
                outcome.saidAt += Array(repeating: at, count: speaker.said.count - heard)
                heard = speaker.said.count
            }

            deepestStep = max(deepestStep, model.currentStep)
            if model.arrived { break }
            // The app stops location when a drive pauses, so no fix after this
            // one would ever have reached the model.
            if model.stalled {
                outcome.stalledAfter = fix.timestamp.timeIntervalSince(drive.fixes[0].timestamp)
                break
            }
        }

        outcome.said = speaker.said
        outcome.arrived = model.arrived
        outcome.maneuversApproached = deepestStep + 1
        outcome.repliesGiven = tape.repliesHandedOut
        outcome.sameLineReplies = tape.sameLineReplies
        outcome.describableFixes = describable
        outcome.requestsAt = tape.requestsAt
        outcome.failedRequests = tape.failed
        return outcome
    }
}
