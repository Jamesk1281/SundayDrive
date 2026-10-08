import CoreLocation
import XCTest
@testable import SundayDrive

/// The route menu (docs/route-options.md): the dial's detents, fetching an
/// option in full on release, and keeping a spliced plan through a reroute.
///
/// The server end of all of this is in tests/test_options.py. These hold the
/// app to its half: the shape decoded, the request sent, the detent shown, and
/// which legs a reroute asks for from where on the plan the driver is.
@MainActor
final class RouteOptionsTests: XCTestCase {

    // MARK: - A plan with a menu

    private static let start = CLLocationCoordinate2D(latitude: 44.1901, longitude: -72.8244)
    private static let end = CLLocationCoordinate2D(latitude: 42.2809, longitude: -71.2378)

    private static func option(_ extra: Double, _ beautifulKm: Double,
                               leave: SwitchPoint? = nil, rejoin: SwitchPoint? = nil,
                               roads: [String] = []) -> [String: Any] {
        ["extra_minutes": extra, "minutes": 181 + extra, "km": 330, "beautiful_km": beautifulKm,
         "leave": Fixture.json(leave), "rejoin": Fixture.json(rejoin), "roads": roads,
         "line": [[-72.82, 44.19], [-72.0, 43.5], [-71.24, 42.28]]]
    }

    private static let vt100 = SwitchPoint(lat: 44.0818, lon: -72.859, heading: 182.5, road: "VT 100")
    private static let us4 = SwitchPoint(lat: 43.6075, lon: -72.7512, heading: 101.0, road: "US 4")

    /// Waitsfield -> Needham, as the server sends it: four detents, opening on
    /// the +44 min one.
    private static func planned() -> RouteResponse {
        let fastest = Fixture.feature(
            coordinates: [[-72.82, 44.19], [-71.24, 42.28]], km: 330, minutes: 181,
            steps: [(start, "Head south", nil), (end, "Arrive at your destination", nil)],
            beautifulKm: 14.6)
        let scenic = Fixture.feature(
            coordinates: [[-72.82, 44.19], [-72.75, 43.6], [-71.24, 42.28]], km: 342,
            minutes: 225, steps: [(start, "Head south on VT 100", nil),
                                  (end, "Arrive at your destination", nil)],
            beautifulKm: 96.0, switchPoints: SwitchPoints(leave: vt100, rejoin: us4))
        let body: [String: Any] = [
            "fastest": fastest, "scenic": scenic,
            "options": ["default": 2, "menu": [
                option(0, 14.6),
                option(16.4, 63.5, leave: vt100, rejoin: vt100, roads: ["VT 100"]),
                option(43.7, 96.0, leave: vt100, rejoin: us4, roads: ["VT 100", "US 4"]),
                option(181.2, 189.9, roads: ["VT 100", "VT 103", "NH 119"]),
            ]],
        ]
        let data = try! JSONSerialization.data(withJSONObject: body)
        return try! JSONDecoder().decode(RouteResponse.self, from: data)
    }

    private func plannedModel() async -> RouteModel {
        let model = RouteModel()
        model.start = Self.start
        model.end = Self.end
        model.fetchRoute = { _, _, _, _, _ in Self.planned() }
        await model.computeRoute()
        return model
    }

    func test_the_menu_decodes_and_an_old_reply_has_none() throws {
        let plan = Self.planned()
        XCTAssertEqual(plan.options?.defaultIndex, 2)
        XCTAssertEqual(plan.options?.menu.count, 4)
        XCTAssertEqual(plan.options?.menu[2].leave, Self.vt100)
        XCTAssertNil(plan.options?.menu[3].rejoin)
        XCTAssertEqual(plan.scenic.properties.switch?.rejoin, Self.us4)

        let leg = Fixture.straightRoute()
        let old = Fixture.response(fastest: leg, scenic: leg)
        XCTAssertNil(old.options)
        XCTAssertNil(old.scenic.properties.switch)
    }

    func test_a_plan_opens_on_its_default_detent() async {
        let model = await plannedModel()
        XCTAssertEqual(model.optionIndex, 2)
        XCTAssertFalse(model.routeIsStale)
        XCTAssertEqual(model.drivePref, 1)
        XCTAssertEqual(model.response?.scenic.properties.minutes, 225)
    }

    func test_a_plan_without_a_menu_is_the_dial_it_always_was() async {
        let model = RouteModel()
        model.start = Self.start
        model.end = Self.end
        model.pref = 0.35
        let leg = Fixture.straightRoute()
        model.fetchRoute = { _, _, _, _, _ in Fixture.response(fastest: leg, scenic: leg) }
        await model.computeRoute()
        XCTAssertNil(model.options)
        XCTAssertEqual(model.drivePref, 0.35)
        XCTAssertFalse(model.routeIsStale)
        model.pref = 0.6
        XCTAssertTrue(model.routeIsStale, "the continuous dial's staleness is unchanged")
    }

    func test_the_fastest_detent_drives_at_exactly_zero() async {
        let model = await plannedModel()
        var fetches = 0
        model.fetchOption = { _, _, _, _, _ in fetches += 1; return Self.planned() }
        model.optionIndex = 0
        await model.chooseOption()
        XCTAssertEqual(fetches, 0, "the fastest route came with the plan")
        XCTAssertEqual(model.drivePref, 0)
        XCTAssertEqual(model.response?.scenic.properties.minutes, 181)
    }

    func test_releasing_on_an_option_fetches_it_once_by_its_switch_points() async {
        let model = await plannedModel()
        var asked: [(SwitchPoint?, SwitchPoint?)] = []
        let detail = Fixture.splicedRoute(leave: 1000, rejoin: 3000)
        model.fetchOption = { _, _, _, leave, rejoin in
            asked.append((leave, rejoin))
            return Fixture.response(fastest: detail, scenic: detail)
        }
        model.optionIndex = 1
        XCTAssertTrue(model.routeIsStale, "the handle has left the option on screen")
        await model.chooseOption()
        XCTAssertEqual(asked.count, 1)
        XCTAssertEqual(asked.first?.0, Self.vt100)
        XCTAssertEqual(asked.first?.1, Self.vt100)
        XCTAssertFalse(model.routeIsStale)
        XCTAssertNotNil(model.response?.scenic.properties.switch)
        XCTAssertEqual(model.response?.fastest.properties.minutes, 181,
                       "the plan's fastest route stays the reference price")
        XCTAssertNotNil(model.options, "the menu survives choosing from it")

        // Back to the default and out again: nothing more is fetched.
        model.optionIndex = 2
        await model.chooseOption()
        model.optionIndex = 1
        await model.chooseOption()
        XCTAssertEqual(asked.count, 1)
        XCTAssertEqual(model.response?.scenic.properties.km, 5)
    }

    func test_the_map_draws_the_simplified_line_while_the_option_is_on_its_way() async {
        let model = await plannedModel()
        var answer: CheckedContinuation<RouteResponse, Error>?
        model.fetchOption = { _, _, _, _, _ in
            try await withCheckedThrowingContinuation { answer = $0 }
        }
        model.optionIndex = 3
        let choosing = Task { await model.chooseOption() }
        let deadline = Date().addingTimeInterval(2)
        while answer == nil, Date() < deadline { try? await Task.sleep(for: .milliseconds(2)) }
        XCTAssertEqual(model.pendingOption, 3)
        XCTAssertEqual(model.previewLine?.count, 3)
        let detail = Fixture.straightRoute()
        answer?.resume(returning: Fixture.response(fastest: detail, scenic: detail))
        await choosing.value
        XCTAssertNil(model.previewLine)
        XCTAssertNil(model.pendingOption)
    }

    func test_a_new_plan_forgets_the_old_menu() async {
        let model = await plannedModel()
        let leg = Fixture.straightRoute()
        model.fetchRoute = { _, _, _, _, _ in Fixture.response(fastest: leg, scenic: leg) }
        await model.computeRoute()
        XCTAssertNil(model.options)
        XCTAssertNil(model.previewLine)
    }

    // MARK: - The words

    func test_the_caption_says_where_the_route_leaves_and_rejoins() throws {
        let menu = try XCTUnwrap(Self.planned().options?.menu)
        XCTAssertNil(OptionCaption.route(menu[0]))
        XCTAssertEqual(OptionCaption.route(menu[2]),
                       "Fast roads to VT 100, scenic on VT 100 and US 4, "
                       + "back on fast roads after US 4.")
        XCTAssertEqual(OptionCaption.route(menu[3]),
                       "Scenic all the way on VT 100, VT 103 and NH 119.")
        XCTAssertEqual(OptionCaption.gainMiles(menu[2], fastest: menu[0]),
                       96.0.wholeMilesFromKm - 14.6.wholeMilesFromKm)
        XCTAssertEqual(OptionCaption.spoken(menu[0], fastest: menu[0]), "Fastest route")
    }

    // MARK: - The trace

    func test_the_trace_header_records_the_switch_points_beside_pref() throws {
        let folder = FileManager.default.temporaryDirectory
            .appendingPathComponent("route-options-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: folder) }
        let trace = try XCTUnwrap(DriveTrace(
            origin: Self.start, destination: Self.end, pref: 1, weights: [:],
            switchPoints: SwitchPoints(leave: Self.vt100, rejoin: nil), directory: folder))
        // The writer is asynchronous; ending the drive is what waits for it.
        trace.end(reason: "ended")
        let first = try XCTUnwrap(try String(contentsOf: trace.url, encoding: .utf8)
            .split(separator: "\n").first)
        let header = try XCTUnwrap(try JSONSerialization.jsonObject(with: Data(first.utf8))
            as? [String: Any])
        XCTAssertEqual(header["pref"] as? Double, 1)
        XCTAssertEqual(header["leave"] as? [Double], [44.0818, -72.859, 182.5])
        XCTAssertTrue(header["rejoin"] is NSNull)

        let plain = try XCTUnwrap(DriveTrace(origin: Self.start, destination: Self.end,
                                             pref: 0.5, weights: [:], directory: folder))
        plain.end(reason: "ended")
        let line = try XCTUnwrap(try String(contentsOf: plain.url, encoding: .utf8)
            .split(separator: "\n").first)
        let old = try XCTUnwrap(try JSONSerialization.jsonObject(with: Data(line.utf8))
            as? [String: Any])
        XCTAssertNil(old["leave"], "a drive off no menu writes the header it always did")
    }

    // MARK: - The request

    func test_a_plan_asks_for_options_and_an_option_sends_its_switch_points() throws {
        let base = "https://api.example.test"
        let plan = RouteService.routeRequest(from: Self.start, to: Self.end, pref: 0.5,
                                             options: true, base: base)
        let body = String(data: try XCTUnwrap(plan.httpBody), encoding: .utf8) ?? ""
        XCTAssertTrue(body.contains("options=1"))
        XCTAssertFalse(body.contains("leave"))

        let detail = RouteService.routeRequest(from: Self.start, to: Self.end, pref: 1,
                                               leave: Self.vt100, rejoin: Self.us4, base: base)
        let text = String(data: try XCTUnwrap(detail.httpBody), encoding: .utf8) ?? ""
        XCTAssertTrue(text.contains("leave=44.081800,-72.859000,182.5"), text)
        XCTAssertTrue(text.contains("rejoin=43.607500,-72.751200,101.0"), text)
        XCTAssertFalse(text.contains("options"))
        XCTAssertEqual(detail.url?.absoluteString, "\(base)/api/route")

        let reroute = RouteService.routeRequest(from: Self.start, to: Self.end, pref: 1,
                                                heading: 90, base: base)
        let plain = String(data: try XCTUnwrap(reroute.httpBody), encoding: .utf8) ?? ""
        XCTAssertFalse(plain.contains("options") || plain.contains("leave"))
    }
}

// MARK: - Rerouting a spliced plan

/// A drive on a spliced option, rerouted from before, on and after its scenic
/// stretch. The plan below leaves the fast roads 1.5 km in and rejoins them
/// at 3.5 km of a 5 km straight route.
@MainActor
final class SplicedRerouteTests: XCTestCase {

    @MainActor
    final class Backend {
        var legs: [(leave: SwitchPoint?, rejoin: SwitchPoint?, declined: Bool)] = []
        var prefs: [Double] = []
        var legsReply: RouteResponse
        var plainReply: RouteResponse

        init(legsReply: RouteResponse, plainReply: RouteResponse) {
            self.legsReply = legsReply
            self.plainReply = plainReply
        }
    }

    private func waitFor(_ condition: @MainActor () -> Bool,
                         _ message: String = "condition never held",
                         file: StaticString = #filePath, line: UInt = #line) async {
        let deadline = Date().addingTimeInterval(2)
        while !condition() {
            if Date() > deadline { return XCTFail(message, file: file, line: line) }
            try? await Task.sleep(for: .milliseconds(2))
        }
    }

    private static func response(_ instruction: String, switchPoints: SwitchPoints?) -> RouteResponse {
        let steps: [(Double, String)] = [(0, instruction), (5000, "Arrive at your destination")]
        let scenic = switchPoints.map { points in
            Fixture.splicedRoute(start: 150,
                                 leave: points.leave.map { _ in 1500 },
                                 rejoin: points.rejoin.map { _ in 3500 },
                                 steps: steps)
        } ?? Fixture.straightRoute(start: 150, steps: steps)
        let fastest = Fixture.straightRoute(start: 150, steps: [(0, "Fastest home"),
                                                                (5000, "Arrive at your destination")])
        return Fixture.response(fastest: fastest, scenic: scenic)
    }

    /// A drive on the plan, joined 500 m in, with every fetch recorded.
    private func driving(leave: Double? = 1500, rejoin: Double? = 3500,
                         pref: Double = 1) -> (NavigationModel, Backend) {
        let backend = Backend(
            legsReply: Self.response("Back to the scenic road",
                                     switchPoints: SwitchPoints(leave: Fixture.switchPoint(1500),
                                                                rejoin: Fixture.switchPoint(3500))),
            plainReply: Self.response("Plain reply", switchPoints: nil))
        let model = NavigationModel(route: Fixture.splicedRoute(leave: leave, rejoin: rejoin),
                                    destination: Fixture.north(5000),
                                    pref: pref, weights: [:])
        model.fetchLegs = { _, _, _, _, leave, rejoin, declined in
            backend.legs.append((leave, rejoin, declined))
            return backend.legsReply
        }
        model.fetchRoute = { _, _, pref, _, _ in
            backend.prefs.append(pref)
            return backend.plainReply
        }
        model.update(Fixture.fixAt(500))
        XCTAssertTrue(model.hasJoinedRoute)
        return (model, backend)
    }

    /// Drive the line to `meters`, a fix every 250 m.
    private func drive(_ model: NavigationModel, from: Double = 500, to meters: Double) {
        for m in stride(from: from + 250, through: meters, by: 250) {
            model.update(Fixture.fixAt(m))
        }
    }

    /// Leave the line 300 m east, two fixes a second apart.
    private func goOffRoute(_ model: NavigationModel, at metres: Double) {
        for m in [metres, metres + 15] {
            model.update(Fixture.fix(CLLocationCoordinate2D(
                latitude: Fixture.north(m).latitude, longitude: -71.0 + 300 / 82_600)))
        }
    }

    func test_before_the_scenic_stretch_it_asks_for_both_switch_points() async {
        let (model, backend) = driving()
        XCTAssertNotNil(model.plan)
        XCTAssertFalse(model.passedLeave)
        goOffRoute(model, at: 800)
        await waitFor { backend.legs.count == 1 && !model.isRerouting }
        XCTAssertEqual(backend.legs.first?.leave, Fixture.switchPoint(1500))
        XCTAssertEqual(backend.legs.first?.rejoin, Fixture.switchPoint(3500))
        XCTAssertEqual(backend.prefs, [], "a spliced plan is never asked for by pref alone")
        XCTAssertEqual(model.currentInstruction, "Back to the scenic road")
    }

    func test_on_the_scenic_stretch_it_asks_for_the_rejoin_point_alone() async {
        let (model, backend) = driving()
        drive(model, to: 2000)
        XCTAssertTrue(model.passedLeave)
        XCTAssertFalse(model.passedRejoin)
        goOffRoute(model, at: 2200)
        await waitFor { backend.legs.count == 1 && !model.isRerouting }
        XCTAssertNil(backend.legs.first?.leave)
        XCTAssertEqual(backend.legs.first?.rejoin, Fixture.switchPoint(3500))
    }

    func test_after_the_scenic_stretch_it_asks_for_the_fastest_way_home() async {
        let (model, backend) = driving()
        drive(model, to: 4000)
        XCTAssertTrue(model.passedRejoin)
        goOffRoute(model, at: 4100)
        await waitFor { backend.prefs.count == 1 && !model.isRerouting }
        XCTAssertEqual(backend.prefs, [0])
        XCTAssertTrue(backend.legs.isEmpty)
        XCTAssertEqual(model.currentInstruction, "Fastest home", "it takes the fastest arm")
        XCTAssertEqual(model.pref, 1, "the plan was not given up, so `pref` is untouched")
        XCTAssertFalse(model.followingFastest)
    }

    func test_a_plan_scenic_from_the_start_asks_for_its_rejoin_point() async {
        let (model, backend) = driving(leave: nil, rejoin: 3500)
        XCTAssertTrue(model.passedLeave)
        goOffRoute(model, at: 800)
        await waitFor { backend.legs.count == 1 && !model.isRerouting }
        XCTAssertNil(backend.legs.first?.leave)
        XCTAssertEqual(backend.legs.first?.rejoin, Fixture.switchPoint(3500))
    }

    func test_a_plan_scenic_to_the_end_is_a_plain_scenic_reroute_once_on_it() async {
        let (model, backend) = driving(leave: 1500, rejoin: nil)
        drive(model, to: 2000)
        goOffRoute(model, at: 2200)
        await waitFor { backend.prefs.count == 1 && !model.isRerouting }
        XCTAssertEqual(backend.prefs, [1])
        XCTAssertTrue(backend.legs.isEmpty)
    }

    func test_a_reply_that_leaves_the_leave_point_out_has_the_driver_past_it() async {
        let (model, backend) = driving()
        backend.legsReply = Self.response(
            "Already on it", switchPoints: SwitchPoints(leave: nil, rejoin: Fixture.switchPoint(3500)))
        goOffRoute(model, at: 800)
        await waitFor { backend.legs.count == 1 && !model.isRerouting }
        XCTAssertTrue(model.passedLeave)
        XCTAssertFalse(model.passedRejoin)
    }

    func test_switching_to_fastest_is_unchanged() async {
        let (model, backend) = driving()
        await model.switchToFastest(from: Fixture.fixAt(800))
        XCTAssertEqual(backend.prefs, [0])
        XCTAssertTrue(backend.legs.isEmpty)
        XCTAssertTrue(model.followingFastest)
        XCTAssertEqual(model.currentInstruction, "Fastest home")
    }

    func test_a_drive_that_is_not_spliced_never_asks_by_legs() async {
        let backend = Backend(legsReply: Self.response("x", switchPoints: nil),
                              plainReply: Self.response("Plain reply", switchPoints: nil))
        let model = NavigationModel(route: Fixture.straightRoute(),
                                    destination: Fixture.north(5000), pref: 0.8, weights: [:])
        model.fetchLegs = { _, _, _, _, _, _, _ in backend.legs.append((nil, nil, false)); return backend.legsReply }
        model.fetchRoute = { _, _, pref, _, _ in backend.prefs.append(pref); return backend.plainReply }
        model.update(Fixture.fixAt(500))
        XCTAssertNil(model.plan)
        goOffRoute(model, at: 800)
        await waitFor { backend.prefs.count == 1 && !model.isRerouting }
        XCTAssertEqual(backend.prefs, [0.8])
        XCTAssertTrue(backend.legs.isEmpty)
    }
}
