import CoreLocation
import XCTest
@testable import SundayDrive

/// P5: once the driver turns away from a seasonal stretch, no later reroute
/// sends them back onto it (docs/seasonal-road-policy.md;
/// docs/seasonal-road-risk-verdict.md, Q3).
///
/// A simulated drive on the straight fixture road north, with the stretch
/// from 2 km to 3 km and its gate shut at 2.3 km. The backend behaves as the
/// server does: asked without the stretch's `avoid_edges`, it sends the
/// driver back up the stretch, as 93% of the study's reroutes did; asked with
/// them, it routes round by a road 2 km east.
@MainActor
final class SeasonalStretchTests: XCTestCase {

    static let stretch = SeasonalStretch(edges: [11, 12, 13], forward: [true, false, true],
                                         from_m: 2000, to_m: 3000, pack: "pack-1")

    /// The backend, noting what each reroute was asked with: its seam, and
    /// the avoid set `RouteService.avoiding` carried into it.
    @MainActor
    final class Server {
        private(set) var asked: [(kind: String, avoid: RouteService.SeasonalAvoid?)] = []
        private(set) var answered: [RouteFeature] = []
        var plain: RouteFetcher { { [self] from, _, _, _, _ in answer("plain", from) } }
        var keepingAhead: RouteFetcher { { [self] from, _, _, _, _ in answer("ahead", from) } }
        var loopResume: LoopResumeFetcher {
            { [self] from, _, _, _, _, _ in answer("via", from) }
        }
        var legs: LegsFetcher { { [self] from, _, _, _, _, _, _ in answer("legs", from) } }

        private func answer(_ kind: String, _ from: CLLocationCoordinate2D) -> RouteResponse {
            let avoid = RouteService.avoiding
            asked.append((kind, avoid))
            let closed = avoid.map { Set($0.tokens).isSuperset(of: stretch.tokens) } ?? false
            let route = closed ? SeasonalStretchTests.roundTheEast(from: from)
                               : SeasonalStretchTests.backUpTheStretch(from: from)
            answered.append(route)
            return Fixture.response(fastest: route, scenic: route)
        }
    }

    /// The plan: north up the test road, over the stretch, to 5 km.
    static func plan() -> RouteFeature {
        let coordinates = (0...20).map { i -> [Double] in
            let c = Fixture.north(Double(i) * 250)
            return [c.longitude, c.latitude]
        }
        return Fixture.decode(Fixture.feature(
            coordinates: coordinates, km: 5, minutes: 10,
            steps: [(Fixture.north(0), "Head north on Test Road", "Test Road"),
                    (Fixture.north(5000), "Arrive at your destination", "")],
            seasonal: [stretch]))
    }

    /// What the server answers without the avoid set: turn round and drive
    /// back up the stretch.
    static func backUpTheStretch(from: CLLocationCoordinate2D) -> RouteFeature {
        let start = (from.latitude - Fixture.origin.latitude) * Fixture.metersPerDegLat
        let coordinates = [[from.longitude, from.latitude]] + stride(from: 2000.0, through: 5000, by: 250)
            .filter { $0 > start }.map { [Fixture.north($0).longitude, Fixture.north($0).latitude] }
        return Fixture.decode(Fixture.feature(
            coordinates: coordinates, km: (5000 - start) / 1000, minutes: 8,
            steps: [(from, "Make a U-turn on Test Road", "Test Road"),
                    (Fixture.north(5000), "Arrive at your destination", "")],
            seasonal: [SeasonalStretch(edges: stretch.edges, forward: stretch.forward,
                                       from_m: max(0, 2000 - start), to_m: 3000 - start,
                                       pack: stretch.pack)]))
    }

    /// What it answers with it: south to 1.5 km, east 2 km, north, and back
    /// west to the destination. No seasonal road.
    static func roundTheEast(from: CLLocationCoordinate2D) -> RouteFeature {
        let points = [from, Fixture.north(1500), Fixture.offset(east: 2000, north: 1500),
                      Fixture.offset(east: 2000, north: 5000), Fixture.north(5000)]
        return Fixture.decode(Fixture.feature(
            coordinates: points.map { [$0.longitude, $0.latitude] }, km: 9, minutes: 14,
            steps: [(points[0], "Head south on Test Road", "Test Road"),
                    (points[1], "Turn left onto East Road", "East Road"),
                    (points[2], "Turn left onto North Road", "North Road"),
                    (points[3], "Turn left onto Top Road", "Top Road"),
                    (points[4], "Arrive at your destination", "")],
            seasonal: []))
    }

    private var clock = Date(timeIntervalSince1970: 1_790_000_000)

    private func model(_ server: Server, route: RouteFeature? = nil) -> NavigationModel {
        let model = NavigationModel(route: route ?? Self.plan(), destination: Fixture.north(5000),
                                    pref: 0.8, weights: [:])
        model.now = { [unowned self] in self.clock }
        model.fetchRoute = server.plain
        model.fetchRouteKeepingAhead = server.keepingAhead
        model.fetchLoopResume = server.loopResume
        model.fetchLegs = server.legs
        model.networkReachable = { true }
        return model
    }

    private func at(_ coordinate: CLLocationCoordinate2D, course: CLLocationDirection) -> CLLocation {
        CLLocation(coordinate: coordinate, altitude: 0, horizontalAccuracy: 5,
                   verticalAccuracy: 5, course: course, speed: 15, timestamp: clock)
    }

    private func feed(_ model: NavigationModel, _ fix: CLLocation) async {
        clock = clock.addingTimeInterval(1)
        model.update(fix)
        for _ in 0..<5 { await Task.yield() }
        var spins = 0
        while model.isRerouting && spins < 500 { await Task.yield(); spins += 1 }
    }

    private func drive(_ model: NavigationModel, from: Double, to: Double, east: Double = 0) async {
        let step = to >= from ? 15.0 : -15.0
        for m in stride(from: from, through: to, by: step) {
            await feed(model, at(Fixture.offset(east: east, north: m), course: step > 0 ? 0 : 180))
        }
    }

    /// Drive the plan onto the stretch to the gate at 2.3 km, and turn back.
    private func turnBackAtTheGate(_ nav: NavigationModel) async {
        await drive(nav, from: 0, to: 2300)
        await drive(nav, from: 2285, to: 2210)
    }

    // MARK: - The simulated drive

    func test_turned_back_at_the_gate_no_later_reroute_reenters_the_stretch() async {
        let server = Server()
        let nav = model(server)
        await turnBackAtTheGate(nav)
        XCTAssertTrue(nav.turnedAway.contains { $0.sameRoad(as: Self.stretch) })
        XCTAssertFalse(server.asked.isEmpty, "the wrong-way episode asked nothing")

        // Off the replacement, twice, down the road and then at the turn east.
        await drive(nav, from: 2195, to: 1800)
        await drive(nav, from: 1500, to: 1200, east: 400)
        await nav.switchToFastest(from: at(Fixture.offset(east: 400, north: 1185), course: 180))

        XCTAssertGreaterThanOrEqual(server.asked.count, 2)
        for (k, ask) in server.asked.enumerated() {
            XCTAssertEqual(ask.avoid?.pack, "pack-1", "reroute \(k) (\(ask.kind))")
            XCTAssertEqual(ask.avoid?.tokens, ["11", "-12", "13"], "reroute \(k) (\(ask.kind))")
        }
        for (k, route) in server.answered.enumerated() {
            XCTAssertFalse((route.properties.seasonal ?? []).contains { $0.sameRoad(as: Self.stretch) },
                           "reroute \(k) went back up the stretch")
        }
        XCTAssertNil(nav.route.properties.seasonal?.first)
    }

    func test_without_the_rule_the_same_drive_goes_back_up_the_stretch() async {
        // The control: a plan whose stretch the server never named, so there
        // is nothing to remember, is sent straight back to the gate.
        let server = Server()
        let unlisted = Fixture.straightRoute()
        let nav = model(server, route: unlisted)
        await turnBackAtTheGate(nav)
        XCTAssertTrue(nav.turnedAway.isEmpty)
        XCTAssertNil(server.asked.first?.avoid)
        XCTAssertTrue(server.answered.first.map {
            ($0.properties.seasonal ?? []).contains { $0.sameRoad(as: Self.stretch) } } ?? false)
    }

    // MARK: - The 25 km rule

    private func turnBack(at gate: Double, stretch: SeasonalStretch) async -> NavigationModel {
        let server = Server()
        let route = Fixture.decode(Fixture.feature(
            coordinates: (0...20).map { i -> [Double] in
                let c = Fixture.north(Double(i) * 250); return [c.longitude, c.latitude]
            },
            km: 5, minutes: 10,
            steps: [(Fixture.north(0), "Head north on Test Road", "Test Road"),
                    (Fixture.north(5000), "Arrive at your destination", "")],
            seasonal: [stretch]))
        let nav = model(server, route: route)
        await drive(nav, from: 0, to: gate)
        await drive(nav, from: gate - 15, to: gate - 90)
        return nav
    }

    private func stretch(from: Double, to: Double) -> SeasonalStretch {
        SeasonalStretch(edges: [7], forward: [true], from_m: from, to_m: to, pack: "pack-1")
    }

    func test_a_stretch_starting_within_25_km_ahead_is_turned_from() async {
        let nav = await turnBack(at: 1500, stretch: stretch(from: 1500 + 24_000, to: 30_000))
        XCTAssertEqual(nav.turnedAway.count, 1)
        XCTAssertEqual(nav.seasonalAvoid?.tokens, ["7"])
    }

    func test_one_starting_further_ahead_is_not() async {
        let nav = await turnBack(at: 1500, stretch: stretch(from: 1500 + 26_000, to: 30_000))
        XCTAssertTrue(nav.turnedAway.isEmpty)
        XCTAssertNil(nav.seasonalAvoid)
    }

    func test_one_already_driven_is_not() async {
        let nav = await turnBack(at: 1500, stretch: stretch(from: 200, to: 900))
        XCTAssertTrue(nav.turnedAway.isEmpty)
    }

    func test_the_rule_is_25_km() {
        XCTAssertEqual(NavigationModel.turnedAwayAheadMeters, 25_000)
    }

    // MARK: - The request

    func test_the_request_carries_the_avoid_set_only_when_given() throws {
        let start = Fixture.north(0), end = Fixture.north(5000)
        func body(_ request: URLRequest) -> [String: String] {
            let text = String(data: request.httpBody ?? Data(), encoding: .utf8) ?? ""
            var out: [String: String] = [:]
            for pair in text.split(separator: "&") {
                let kv = pair.split(separator: "=", maxSplits: 1).map(String.init)
                out[kv[0]] = kv.count > 1 ? kv[1].removingPercentEncoding : ""
            }
            return out
        }
        let plain = body(RouteService.routeRequest(from: start, to: end, pref: 0.5))
        XCTAssertNil(plain["avoid_edges"])
        let avoided = body(RouteService.routeRequest(
            from: start, to: end, pref: 0.5,
            avoid: RouteService.SeasonalAvoid(pack: "pack-1", tokens: Self.stretch.tokens)))
        XCTAssertEqual(avoided["avoid_edges"], "11,-12,13")
        XCTAssertEqual(avoided["avoid_pack"], "pack-1")
        XCTAssertNil(URLComponents(url: RouteService.routeRequest(
            from: start, to: end, pref: 0.5,
            avoid: RouteService.SeasonalAvoid(pack: "p", tokens: ["1"])).url!,
                                   resolvingAgainstBaseURL: false)?.queryItems)
    }

    func test_a_route_from_an_older_backend_decodes_with_none() throws {
        let route = Fixture.straightRoute()
        XCTAssertNil(route.properties.seasonal)
        XCTAssertEqual(Self.stretch.tokens, ["11", "-12", "13"])
    }
}
