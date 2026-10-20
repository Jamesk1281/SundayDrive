import CoreLocation
import XCTest
@testable import SundayDrive

/// A reroute from a long closed edge, against a real national server.
///
/// The outside review drove I-10 westbound at 35 m/s, west of Tonopah, AZ,
/// through edge 1470492: 16.3 km, closed by a ford node in `data/pack-us`. The
/// reroute's line began at the junction at the far end of the edge, so the app
/// showed "Off route · route 9.5 mi away / Head back to your route" under the
/// U-turn arrow while the car drove the road the new route was on. The fix is
/// the router's lead-in: a reroute with a heading starts at the car
/// (docs/review-fixes-router.md; docs/review-fixes-app.md, "The I-10 lead-in").
///
/// Skips unless `SUNDAYDRIVE_API` names a server, and never falls back to the
/// deployed one. Meaningful only on a pack where that ford still closes the
/// edge (`data/pack-us`, not `pack-us-next`): the test says which it saw.
@MainActor
final class LeadInRerouteTests: XCTestCase {

    private static let env = ProcessInfo.processInfo.environment

    /// I-10 westbound: the last 1.1 km before the closed edge, the edge, and
    /// the 51 m after it. OSM geometry, thinned to about 800 m.
    private static let i10West: [CLLocationCoordinate2D] = [
        (33.568352, -113.346956), (33.568894, -113.350590), (33.569656, -113.355632),
        (33.570482, -113.361052), (33.571157, -113.365492), (33.572045, -113.371250),
        (33.572947, -113.377482), (33.574205, -113.385718), (33.575497, -113.394304),
        (33.576683, -113.402190), (33.578048, -113.411173), (33.579563, -113.421284),
        (33.580397, -113.426671), (33.581687, -113.435328), (33.583141, -113.444903),
        (33.584504, -113.453972), (33.585867, -113.463041), (33.587220, -113.472044),
        (33.588543, -113.480850), (33.589866, -113.489657), (33.591191, -113.498474),
        (33.592517, -113.507303), (33.593844, -113.516131), (33.594913, -113.523362),
        (33.595722, -113.528799), (33.596173, -113.531671),
    ].map { CLLocationCoordinate2D(latitude: $0.0, longitude: $0.1) }

    private static let blythe = CLLocationCoordinate2D(latitude: 33.6103, longitude: -114.5964)

    private var clock = Date(timeIntervalSince1970: 1_790_000_000)

    private func base() throws -> String {
        guard let api = Self.env["SUNDAYDRIVE_API"], !api.isEmpty else {
            throw XCTSkip("set TEST_RUNNER_SUNDAYDRIVE_API to a local national server")
        }
        return api
    }

    /// A route as the app asks for one, from `base` and nowhere else, with
    /// failures read the way `RouteService` reads them.
    private func route(_ base: String, from: CLLocationCoordinate2D, to: CLLocationCoordinate2D,
                       pref: Double, heading: CLLocationDirection?,
                       declinedUTurn: Bool = false) async throws -> RouteResponse {
        let request = RouteService.routeRequest(from: from, to: to, pref: pref, heading: heading,
                                                declinedUTurn: declinedUTurn, base: base)
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 30
        let (data, response) = try await URLSession(configuration: configuration).data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw RouteService.failure(status: http.statusCode, body: data)
        }
        return try JSONDecoder().decode(RouteResponse.self, from: data)
    }

    /// Fixes every `metres` along `line`, each carrying its course, at `speed`.
    private func fixes(along line: [CLLocationCoordinate2D], metres: Double,
                       speed: CLLocationSpeed) -> [CLLocation] {
        var out: [CLLocation] = []
        var carried = 0.0
        for (a, b) in zip(line, line.dropFirst()) {
            let start = CLLocation(latitude: a.latitude, longitude: a.longitude)
            let segment = start.distance(from: CLLocation(latitude: b.latitude,
                                                          longitude: b.longitude))
            let course = Self.bearing(a, b)
            var travelled = carried
            while travelled < segment {
                let t = travelled / segment
                out.append(CLLocation(
                    coordinate: CLLocationCoordinate2D(
                        latitude: a.latitude + (b.latitude - a.latitude) * t,
                        longitude: a.longitude + (b.longitude - a.longitude) * t),
                    altitude: 0, horizontalAccuracy: 5, verticalAccuracy: 5,
                    course: course, speed: speed, timestamp: Date()))
                travelled += metres
            }
            carried = travelled - segment
        }
        return out
    }

    private static func bearing(_ a: CLLocationCoordinate2D, _ b: CLLocationCoordinate2D) -> Double {
        let φ1 = a.latitude * .pi / 180, φ2 = b.latitude * .pi / 180
        let Δλ = (b.longitude - a.longitude) * .pi / 180
        let y = sin(Δλ) * cos(φ2)
        let x = cos(φ1) * sin(φ2) - sin(φ1) * cos(φ2) * cos(Δλ)
        return (atan2(y, x) * 180 / .pi + 360).truncatingRemainder(dividingBy: 360)
    }

    func test_a_reroute_on_a_long_closed_edge_starts_at_the_car() async throws {
        let api = try base()
        let start = Self.i10West[0]
        let planned: RouteResponse
        do {
            planned = try await route(api, from: start, to: Self.blythe, pref: 0.5, heading: nil)
        } catch let error as URLError {
            throw XCTSkip("no Sunday Drive API at \(api) (\(error.code))")
        }

        let nav = NavigationModel(route: planned.scenic, destination: Self.blythe,
                                  pref: 0.5, weights: [:])
        nav.now = { [unowned self] in self.clock }
        nav.networkReachable = { true }
        var asked = 0
        nav.fetchRoute = { [unowned self] from, to, pref, _, heading in
            asked += 1
            return try await self.route(api, from: from, to: to, pref: pref, heading: heading)
        }
        nav.fetchRouteKeepingAhead = { [unowned self] from, to, pref, _, heading in
            asked += 1
            return try await self.route(api, from: from, to: to, pref: pref, heading: heading,
                                        declinedUTurn: true)
        }

        // Does the planned route drive this edge? On a pack where the ford
        // still closes it, it cannot, and the car leaving it is the review's
        // case. Where the ford is open the route may simply follow I-10.
        let plannedOnEdge = planned.scenic.coordinates.contains {
            $0.longitude < -113.40 && $0.longitude > -113.50 && abs($0.latitude - 33.58) < 0.01
        }

        // Each line the drive adopts, by the fix it arrived on, and how far
        // from the car it began. The lead-in's promise is the second number:
        // a reroute with a heading starts where the car is.
        var adopted: [(fix: Int, startOffset: Double)] = []
        var offTheLine: [(Int, NavView.BannerText)] = []
        var bannerBeforeAdoption = 0
        var lineStart = nav.coordinates.first
        for (i, fix) in fixes(along: Self.i10West, metres: 35, speed: 35).enumerated() {
            clock = clock.addingTimeInterval(1)
            nav.update(fix)
            for _ in 0..<5 { await Task.yield() }
            var waited = 0
            while nav.isRerouting && waited < 600 {
                try await Task.sleep(for: .milliseconds(50))
                waited += 1
            }
            if let first = nav.coordinates.first, lineStart.map({ !$0.matches(first) }) ?? true {
                lineStart = first
                adopted.append((i, CLLocation(latitude: first.latitude, longitude: first.longitude)
                    .distance(from: fix)))
            }
            let text = NavView.bannerText(nav: nav, location: LocationManager())
            let calledOff = nav.isOffTheLine || text.symbol == "arrow.uturn.backward"
            if calledOff, adopted.isEmpty { bannerBeforeAdoption += 1 }
            if calledOff, !adopted.isEmpty { offTheLine.append((i, text)) }
            if Self.env["SUNDAYDRIVE_LEADIN_TRACE"] != nil {
                print(String(format: "lead-in trace %03d lon %.5f asked %d off %.0f m | %@ / %@ [%@]",
                             i, fix.coordinate.longitude, asked,
                             progress(of: fix.coordinate, along: nav.coordinates).offRoute,
                             text.over, text.main, text.symbol))
            }
        }

        print("lead-in: planned route on the edge: \(plannedOnEdge); reroutes asked: \(asked); "
              + "lines adopted at fixes \(adopted.map(\.fix)), starting "
              + "\(adopted.map { Int($0.startOffset) }) m from the car; "
              + "called off the line on \(bannerBeforeAdoption) fixes before the first")
        if plannedOnEdge && asked == 0 {
            throw XCTSkip("the planned route drives the edge, so this pack has the ford open "
                          + "and there is nothing to reroute from")
        }
        XCTAssertGreaterThan(asked, 0, "the car never left the planned route")
        XCTAssertFalse(adopted.isEmpty, "no reroute was adopted")
        for line in adopted {
            XCTAssertLessThan(line.startOffset, 50,
                              "the line adopted at fix \(line.fix) began "
                              + "\(Int(line.startOffset)) m from the car")
        }
        XCTAssertEqual(offTheLine.count, 0,
                       "after a reroute was adopted the car was called off its own line "
                       + "\(offTheLine.count) times, first: "
                       + "\(offTheLine.first.map { "\($0.1.over) / \($0.1.main)" } ?? "")")
    }
}
