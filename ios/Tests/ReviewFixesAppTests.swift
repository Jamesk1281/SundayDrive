import CoreLocation
import XCTest
@testable import SundayDrive

/// The app's half of the fixes in docs/review-fixes-app.md, one section per
/// item there. Everything here runs without a server: the bodies are the
/// contract's, written out by hand, and the old server's, so the app is shown
/// to read both.
@MainActor
final class ReviewFixesAppTests: XCTestCase {

    private func body(_ object: [String: Any]) -> Data {
        try! JSONSerialization.data(withJSONObject: object)
    }

    private static let boston = CLLocationCoordinate2D(latitude: 42.3601, longitude: -71.0589)
    private static let chicago = CLLocationCoordinate2D(latitude: 41.8781, longitude: -87.6298)
    private static let newYork = CLLocationCoordinate2D(latitude: 40.7128, longitude: -74.0060)

    /// The body the national server on `usa` sent for Boston to Chicago on
    /// 2026-10-20, byte for byte: numbers beside the sentence, which a
    /// `[String: String]` decode refused.
    private var tripTooLongBody: Data {
        Data(#"{"code":"TRIP_TOO_LONG","error":"That trip is 849 miles in a straight line. Sunday Drive plans drives of up to 311 miles, so pick a stop along the way and plan it in two parts.","km":1365.6,"max_km":500.0}"#.utf8)
    }

    // MARK: - 1. The cap's message

    func test_the_trip_caps_reply_is_the_servers_no_not_unreachable() {
        let error = RouteService.failure(status: 400, body: tripTooLongBody)
        guard case .server(let refusal) = error else {
            return XCTFail("expected .server, got \(error)")
        }
        XCTAssertEqual(refusal.kind, .tripTooLong)
        XCTAssertEqual(refusal.maxKm, 500)
        XCTAssertEqual(refusal.km, 1365.6)
        XCTAssertEqual(error.errorDescription,
                       "That trip is 849 miles in a straight line. Sunday Drive plans drives "
                       + "of up to 310 miles, so pick a stop along the way and plan it in two parts.")
        XCTAssertFalse(error.errorDescription!.contains("HTTP"))
    }

    func test_every_contract_code_decodes_with_its_numbers() {
        for code in ["TRIP_TOO_LONG", "LEG_TOO_LONG", "LOOP_TOO_LONG", "NO_ROUTE_NEARBY",
                     "START_TOO_FAR", "OUTSIDE_COVERAGE", "BAD_INPUT", "CLOSED_FOR_SEASON",
                     "SAME_ROAD", "NO_LOOP", "NOT_FOUND", "SERVER_ERROR"] {
            let error = RouteService.failure(
                status: 400, body: body(["error": "A sentence.", "code": code,
                                         "max_km": 120.5, "km": 300, "extra": [1, 2]]))
            guard case .server(let refusal) = error else { return XCTFail(code) }
            XCTAssertEqual(refusal.kind?.rawValue, code)
            XCTAssertEqual(refusal.maxKm, 120.5, code)
        }
    }

    func test_the_routers_loop_refusal_reads_with_its_limit() {
        // As unit R's server sent it for a 400 km loop from New York on
        // 2026-10-20, before that branch was committed.
        let data = Data(#"{"code":"LOOP_TOO_LONG","error":"Loops from here go up to 179 miles, because the roads around this start are dense enough to make a longer one slow to plan. Pick a shorter loop.","km":400.0,"max_km":288.3}"#.utf8)
        guard case .server(let refusal) = RouteService.failure(status: 400, body: data) else {
            return XCTFail("not read as the server's no")
        }
        XCTAssertEqual(refusal.kind, .loopTooLong)
        XCTAssertEqual(refusal.maxKm, 288.3)
        XCTAssertEqual(refusal.sentence, refusal.message)
    }

    func test_an_unknown_code_is_still_the_servers_sentence() {
        let error = RouteService.failure(status: 400, body: body(["error": "Something new.",
                                                                  "code": "NEW_CODE"]))
        guard case .server(let refusal) = error else { return XCTFail("\(error)") }
        XCTAssertNil(refusal.kind)
        XCTAssertEqual(refusal.rawCode, "NEW_CODE")
        XCTAssertEqual(error.errorDescription, "Something new.")
    }

    func test_the_old_servers_bodies_still_read_and_become_sentences() {
        let error = RouteService.failure(status: 404,
                                         body: body(["error": "no route found between those points"]))
        guard case .server(let refusal) = error else { return XCTFail("\(error)") }
        XCTAssertNil(refusal.kind)
        XCTAssertEqual(error.errorDescription, "No route found between those points.")
        // A sentence already is one.
        XCTAssertEqual(Refusal.asSentence("Sunday Drive covers the contiguous United States, "
                                          + "and that point is outside it."),
                       "Sunday Drive covers the contiguous United States, and that point is outside it.")
        XCTAssertEqual(Refusal.asSentence("no loop of that length from there. The nearest "
                                          + "loop from here is about 30 km."),
                       "No loop of that length from there. The nearest loop from here is about 30 km.")
    }

    func test_numbers_sent_as_strings_are_tolerated() {
        let error = RouteService.failure(status: 400, body: body([
            "error": "x", "code": "TRIP_TOO_LONG", "max_km": "500", "km": "851.6"]))
        guard case .server(let refusal) = error else { return XCTFail("\(error)") }
        XCTAssertEqual(refusal.maxKm, 500)
        XCTAssertTrue(error.errorDescription!.contains("up to 310 miles"))
    }

    func test_a_body_that_is_not_our_json_is_still_unreachable() {
        for data in [Data("<html>Bad Request</html>".utf8), body(["message": "nope"]),
                     body(["error": 12])] {
            guard case .unreachable(400) = RouteService.failure(status: 400, body: data) else {
                return XCTFail("expected .unreachable(400)")
            }
        }
    }

    func test_the_cap_reads_310_miles_never_311() {
        XCTAssertEqual(RouteService.capMiles(500), 310)
        XCTAssertEqual(RouteService.capMiles(RouteService.maxTripKm), 310)
        XCTAssertTrue(RouteService.tripTooLong(km: 851.6).contains("up to 310 miles"))
    }

    func test_a_trip_over_the_cap_is_refused_on_the_phone_before_asking() {
        let refusal = RouteService.refusalBeforeAsking(from: Self.boston, to: Self.chicago)
        XCTAssertNotNil(refusal)
        XCTAssertTrue(refusal!.contains("up to 310 miles"), refusal!)
        XCTAssertNil(RouteService.refusalBeforeAsking(from: Self.boston, to: Self.newYork),
                     "Boston to New York, 306 km, is asked for")
    }

    func test_planning_over_the_cap_sends_nothing() async {
        let model = RouteModel()
        var asked = 0
        model.fetchRoute = { _, _, _, _, _ in
            asked += 1
            throw URLError(.cancelled)
        }
        model.start = Self.boston
        model.end = Self.chicago
        await model.computeRoute()
        XCTAssertEqual(asked, 0)
        XCTAssertNil(model.response)
        XCTAssertTrue(model.errorText?.contains("up to 310 miles") == true, "\(model.errorText ?? "nil")")
        XCTAssertFalse(model.isLoading)
    }

    func test_mid_drive_a_refusal_is_never_no_connection() {
        let cap = RouteService.failure(status: 400, body: tripTooLongBody)
        guard case .server(let words) = NavigationModel.classify(cap, hasPath: true) else {
            return XCTFail("the trip cap's reply was booked as a lost connection")
        }
        XCTAssertTrue(words.contains("310 miles"))

        // A 4xx whose body cannot be read is still an answer.
        XCTAssertEqual(NavigationModel.classify(RouteService.ServiceError.unreachable(400),
                                                hasPath: true),
                       .server(NavigationModel.refusedReroute))
        // Waiting fixes a timeout, a rate limit and a 5xx, so they stay lost.
        for status in [408, 429, 502, 530] {
            XCTAssertEqual(NavigationModel.classify(RouteService.ServiceError.unreachable(status),
                                                    hasPath: true),
                           .lost(.serverUnreachable), "\(status)")
        }
    }

    // MARK: - The router's other codes

    private func refusal(_ code: String, status: Int = 404,
                         error: String = "A sentence from the server.") -> RouteService.ServiceError {
        RouteService.failure(status: status, body: body(["error": error, "code": code]))
    }

    func test_busy_is_the_busy_path_at_any_status() {
        for status in [503, 429, 400] {
            guard case .busy(let words) = refusal("BUSY", status: status,
                                                  error: "Busy planning other drives. Try again in a moment.")
            else { return XCTFail("BUSY at \(status) was not .busy") }
            XCTAssertEqual(words, "Busy planning other drives. Try again in a moment.")
        }
    }

    func test_closed_for_season_has_the_seasonal_wording_whatever_the_server_says() {
        let error = refusal("CLOSED_FOR_SEASON", error: "Some other wording.")
        XCTAssertEqual(error.errorDescription, "The only way there is closed for the season.")
        guard case .server(let refusal) = error else { return XCTFail("\(error)") }
        XCTAssertEqual(refusal.kind, .closedForSeason)
        // Mid-drive it is the server's no, under the trip card.
        XCTAssertEqual(NavigationModel.classify(error, hasPath: true),
                       .server("The only way there is closed for the season."))
    }

    func test_the_other_router_codes_show_the_servers_sentence() {
        for (code, status) in [("SAME_ROAD", 400), ("NO_LOOP", 404), ("NOT_FOUND", 405),
                               ("SERVER_ERROR", 500), ("SOMETHING_NEW", 400)] {
            let error = refusal(code, status: status, error: "The server's own sentence.")
            guard case .server(let refusal) = error else { return XCTFail(code) }
            XCTAssertEqual(refusal.rawCode, code)
            XCTAssertEqual(error.errorDescription, "The server's own sentence.", code)
            // An answer, so never "No connection" mid-drive.
            XCTAssertEqual(NavigationModel.classify(error, hasPath: true),
                           .server("The server's own sentence."), code)
        }
        // NO_LOOP's nearest_km may be null, which must not stop it decoding.
        let noLoop = RouteService.failure(status: 404, body: body([
            "error": "There's no loop of that length from there.", "code": "NO_LOOP",
            "nearest_km": NSNull()]))
        guard case .server(let refusal) = noLoop else { return XCTFail("\(noLoop)") }
        XCTAssertEqual(refusal.kind, .noLoop)
    }

    // MARK: - Exit numbers and multi-values

    func test_a_ramp_serving_two_exits_reads_as_either() {
        // The router's own wording is left as it is.
        XCTAssertEqual("Take exit 7A or 7B toward Boston".multiValuesTidied,
                       "Take exit 7A or 7B toward Boston")
        XCTAssertEqual("Take exit 7A or 7B toward Boston".spokenAloud,
                       "Take exit 7A or 7B toward Boston")
        // A server that sends the raw values gets the same words.
        XCTAssertEqual("Take exit 7A;7B toward Boston".multiValuesTidied,
                       "Take exit 7A or 7B toward Boston")
        XCTAssertEqual("Take exit 7A/7B".multiValuesTidied, "Take exit 7A or 7B")
        XCTAssertEqual("Take exit 12;13;14".multiValuesTidied, "Take exit 12, 13 or 14")
        XCTAssertEqual("Exit 7A/7B".multiValuesTidied, "Exit 7A or 7B")
    }

    func test_raw_multi_value_refs_are_shown_and_spoken_as_a_sign_shows_them() {
        XCTAssertEqual("Continue onto I 295;US 1;ME 26".multiValuesTidied,
                       "Continue onto I 295 / US 1 / ME 26")
        XCTAssertEqual("Continue onto I 295;US 1;ME 26".spokenAloud,
                       "Continue onto Interstate 295 and Route 1 and Route 26")
        // A slash that is not an exit's is left alone.
        XCTAssertEqual("Take the exit toward Soldiers Field Road West / Newton".multiValuesTidied,
                       "Take the exit toward Soldiers Field Road West / Newton")
    }

    // MARK: - 2. Spoken road names

    func test_every_states_routes_are_spoken_as_routes() {
        XCTAssertEqual("Continue onto CA 1".spokenAloud, "Continue onto Route 1")
        XCTAssertEqual("Turn left onto TX 71".spokenAloud, "Turn left onto Route 71")
        XCTAssertEqual("Keep right onto OR-99E".spokenAloud, "Keep right onto Route 99E")
        XCTAssertEqual("Take the exit toward DC 295".spokenAloud, "Take the exit toward Route 295")
        for code in Coverage.stateCodes {
            XCTAssertEqual("Turn right onto \(code) 12".spokenAloud, "Turn right onto Route 12", code)
        }
    }

    func test_the_other_prefixes_are_spoken_as_their_kind_of_road() {
        XCTAssertEqual("Turn left onto SR 20".spokenAloud, "Turn left onto State Route 20")
        XCTAssertEqual("Turn left onto CR 12".spokenAloud, "Turn left onto County Road 12")
        XCTAssertEqual("Turn right onto FM 1960".spokenAloud,
                       "Turn right onto Farm to Market Road 1960")
        XCTAssertEqual("Continue onto BIA 15".spokenAloud, "Continue onto BIA Route 15")
    }

    func test_a_prefix_without_a_number_or_in_lower_case_is_left_alone() {
        for text in ["Turn left onto YMCA Drive", "Turn left onto ORCA Road",
                     "Turn right onto Main Street", "In 500 feet, turn left",
                     "Continue onto Pennsylvania Avenue", "Turn left onto CR Smith Road"] {
            XCTAssertEqual(text.spokenAloud, text)
            XCTAssertFalse(text.spokenAloud.contains("Route"), text)
        }
    }

    func test_a_split_multi_value_reads_as_two_routes() {
        // How the server announces "I-295 / US-1" (docs/review-fixes-router.md).
        XCTAssertEqual("Continue onto I-295 / US-1".spokenAloud,
                       "Continue onto Interstate 295 and Route 1")
    }

    // MARK: - 4. The loop slider takes the start's limit

    private static let loopStart = CLLocationCoordinate2D(latitude: 40.7128, longitude: -74.0060)

    private func loopResponse(km: Double) -> LoopResponse {
        let ring: [[Double]] = [[-74.00, 40.71], [-74.00, 40.81], [-73.90, 40.81],
                                [-73.90, 40.71], [-74.00, 40.71]]
        let object: [String: Any] = [
            "loop": ["type": "Feature",
                     "geometry": ["type": "LineString", "coordinates": ring],
                     "properties": ["km": km, "minutes": km * 1.4, "mean_score": 5.0,
                                    "scenery_km": [:] as [String: Double], "steps": []]],
            "meta": ["target_km": km, "km": km, "minutes": km * 1.4, "mean_score": 5.0,
                     "beautiful_km": 1.0, "beautiful_score": 7.0, "repeated_km": 0.0,
                     "turnaround": [40.81, -73.95], "sector": "N"],
            "alternatives": [["sector": "N", "candidates": 10]],
            "note": NSNull(),
        ]
        return try! JSONDecoder().decode(LoopResponse.self,
                                         from: try! JSONSerialization.data(withJSONObject: object))
    }

    func test_the_limit_reply_decodes() throws {
        let limit = try JSONDecoder().decode(LoopLimit.self,
                                             from: body(["max_km": 182.4, "max_mi": 113]))
        XCTAssertEqual(limit.max_km, 182.4)
        XCTAssertEqual(limit.miles, 113)
        XCTAssertEqual(LoopView.limitCaption(limit), "Up to 113 mi from here")
        // Without max_mi the miles are floored, as the cap's are.
        let bare = try JSONDecoder().decode(LoopLimit.self, from: body(["max_km": 400.0]))
        XCTAssertEqual(bare.miles, 248)
    }

    func test_the_limit_request_carries_its_start_in_the_body() {
        let request = RouteService.loopLimitRequest(from: Self.loopStart, base: "https://api.example")
        XCTAssertEqual(request.url?.absoluteString, "https://api.example/api/loop/limit")
        XCTAssertNil(request.url?.query)
        XCTAssertEqual(request.httpMethod, "POST")
        let form = String(data: request.httpBody ?? Data(), encoding: .utf8)
        XCTAssertEqual(form, "from=40.7128,-74.006")
    }

    func test_the_slider_tops_out_at_this_starts_limit() async {
        let model = LoopModel(locationManager: LocationManager())
        model.start = Self.loopStart
        model.targetKm = 40
        model.fetchLimit = { _ in LoopLimit(max_km: 182.4, max_mi: 113) }
        model.fetchLoop = { _, km, _, _ in self.loopResponse(km: km) }
        XCTAssertEqual(model.sliderMaxKm, 400, "the server's clamp until the limit is known")
        await model.generate()
        for _ in 0..<50 where model.limit == nil { await Task.yield() }
        XCTAssertEqual(model.limit?.max_km, 182.4)
        XCTAssertEqual(model.sliderMaxKm, 182)
        XCTAssertEqual(model.targetKm, 40, "a length inside the limit is left alone")
    }

    func test_a_remembered_length_over_the_limit_is_pulled_in_before_asking() async {
        let model = LoopModel(locationManager: LocationManager())
        model.start = Self.loopStart
        model.targetKm = 300
        model.fetchLimit = { _ in LoopLimit(max_km: 182.4, max_mi: 113) }
        var asked: [Double] = []
        model.fetchLoop = { _, km, _, _ in asked.append(km); return self.loopResponse(km: km) }
        await model.generate()
        for _ in 0..<50 where model.limit == nil { await Task.yield() }
        // The second loop is asked for inside the limit learnt beside the first.
        model.targetKm = 300
        await model.generate()
        XCTAssertEqual(asked.last, 182)
    }

    func test_a_loop_over_the_limit_is_asked_again_at_it() async {
        let model = LoopModel(locationManager: LocationManager())
        model.start = Self.loopStart
        model.targetKm = 400
        model.fetchLimit = { _ in throw URLError(.cancelled) }   // an older server
        var asked: [Double] = []
        model.fetchLoop = { _, km, _, _ in
            asked.append(km)
            if km > 150 {
                throw RouteService.failure(status: 400, body: self.body([
                    "error": "That loop is longer than roads here allow.",
                    "code": "LOOP_TOO_LONG", "max_km": 150.7, "km": km]))
            }
            return self.loopResponse(km: km)
        }
        await model.generate()
        XCTAssertEqual(asked, [400, 150])
        XCTAssertNil(model.errorText)
        XCTAssertNotNil(model.response)
        XCTAssertEqual(model.limit?.max_km, 150.7)
        XCTAssertEqual(model.sliderMaxKm, 150)
    }

    func test_a_loop_over_the_limit_with_a_chosen_direction_keeps_it() async {
        // The sector fallback must not answer LOOP_TOO_LONG by dropping the
        // driver's direction: the length is what was wrong.
        let model = LoopModel(locationManager: LocationManager())
        model.start = Self.loopStart
        model.targetKm = 40
        model.fetchLimit = { _ in throw URLError(.cancelled) }
        model.fetchLoop = { _, km, _, _ in self.loopResponse(km: km) }
        await model.generate()
        await model.head("N")
        var asked: [(Double, String?)] = []
        model.targetKm = 300
        model.fetchLoop = { _, km, sector, _ in
            asked.append((km, sector))
            if km > 150 {
                throw RouteService.failure(status: 400, body: self.body([
                    "error": "Too long.", "code": "LOOP_TOO_LONG", "max_km": 150.0, "km": km]))
            }
            return self.loopResponse(km: km)
        }
        await model.generate()
        XCTAssertEqual(asked.map(\.0), [300, 150])
        XCTAssertEqual(asked.map(\.1), ["N", "N"])
    }

    func test_without_a_limit_the_slider_is_what_it_always_was() async {
        let model = LoopModel(locationManager: LocationManager())
        model.start = Self.loopStart
        model.fetchLimit = { _ in throw RouteService.ServiceError.unreachable(404) }
        model.fetchLoop = { _, km, _, _ in self.loopResponse(km: km) }
        await model.generate()
        for _ in 0..<20 { await Task.yield() }
        XCTAssertNil(model.limit)
        XCTAssertEqual(model.sliderMaxKm, LoopModel.maxKm)
    }

    func test_a_new_start_forgets_the_old_limit() async {
        let model = LoopModel(locationManager: LocationManager())
        model.start = Self.loopStart
        var limits = [LoopLimit(max_km: 120, max_mi: 74), LoopLimit(max_km: 400, max_mi: 248)]
        var limitCalls = 0
        model.fetchLimit = { _ in limitCalls += 1; return limits.removeFirst() }
        model.fetchLoop = { _, km, _, _ in self.loopResponse(km: km) }
        await model.generate()
        for _ in 0..<50 where model.limit == nil { await Task.yield() }
        await model.generate()   // same start: not asked again
        XCTAssertEqual(limitCalls, 1)
        model.start = CLLocationCoordinate2D(latitude: 44.0, longitude: -72.7)
        await model.generate()
        for _ in 0..<50 where model.limit?.max_km != 400 { await Task.yield() }
        XCTAssertEqual(limitCalls, 2)
        XCTAssertEqual(model.sliderMaxKm, 400)
    }

    // MARK: - 5. Smaller ones

    func test_one_place_answered_three_times_is_one_suggestion() {
        // The five rows the completer gave on the simulator on 2026-10-20,
        // as shown: three are one place.
        let rows: [(title: String, subtitle: String)] = [
            ("Santa Cruz Beach Boardwalk", "Santa Cruz, CA, United States"),
            ("Santa Cruz Beach Boardwalk", "400 Beach St, Santa Cruz, CA 95060, United States"),
            ("Santa Cruz Beach Boardwalk", "400 Beach St, Santa Cruz, CA  95060, United States"),
            ("Fright Walk At Santa Cruz Beach Boardwalk",
             "400 Beach St, Santa Cruz, CA  95060, United States"),
            ("Boardwalk Stairs 2", "Santa Cruz, CA, United States"),
        ]
        XCTAssertEqual(SearchCompleter.distinct(rows), [0, 3, 4])
        // Case, accents, spacing and a missing subtitle are the same place too.
        XCTAssertEqual(SearchCompleter.distinct([
            ("Café Boulud", "New York, NY"), ("cafe boulud ", "New  York, NY"), ("Café Boulud", ""),
        ]), [0])
    }

    func test_two_places_of_one_name_in_two_towns_are_both_offered() {
        let rows: [(title: String, subtitle: String)] = [
            ("Main Street", "Stowe, VT"), ("Main Street", "Bar Harbor, ME"),
            ("Main Street", "North Stowe, VT"),
        ]
        XCTAssertEqual(SearchCompleter.distinct(rows), [0, 1, 2])
    }

    private func withRecents(_ body: () async throws -> Void) async rethrows {
        let key = "recentDestinations"
        let saved = UserDefaults.standard.data(forKey: key)
        defer {
            // The test host is the real app, so put its list back as found.
            if let saved { UserDefaults.standard.set(saved, forKey: key) }
            else { UserDefaults.standard.removeObject(forKey: key) }
        }
        Recents.clear()
        try await body()
    }

    private func routeModel(to end: CLLocationCoordinate2D, name: String) -> RouteModel {
        let model = RouteModel()
        model.start = Self.boston
        model.end = end
        model.endQuery = name
        model.pendingRecent = Recent(name: name, subtitle: "", latitude: end.latitude,
                                     longitude: end.longitude)
        return model
    }

    func test_a_destination_the_server_refuses_is_not_saved() async {
        await withRecents {
            let model = routeModel(to: Self.newYork, name: "Somewhere refused")
            model.fetchRoute = { _, _, _, _, _ in
                throw RouteService.ServiceError.server("No route found between those points.")
            }
            await model.computeRoute()
            XCTAssertEqual(Recents.load(), [])
            XCTAssertNil(model.pendingRecent)
        }
    }

    func test_a_destination_over_the_cap_is_not_saved() async {
        await withRecents {
            let model = routeModel(to: Self.chicago, name: "Chicago")
            await model.computeRoute()
            XCTAssertEqual(Recents.load(), [])
        }
    }

    func test_a_destination_waits_out_a_dead_network_and_is_saved_with_its_route() async {
        await withRecents {
            let model = routeModel(to: Self.newYork, name: "New York")
            model.fetchRoute = { _, _, _, _, _ in throw RouteService.ServiceError.offline }
            await model.computeRoute()
            XCTAssertEqual(Recents.load(), [], "not routed yet")
            XCTAssertNotNil(model.pendingRecent, "and not refused either")

            model.fetchRoute = { _, _, _, _, _ in
                Fixture.response(fastest: Fixture.straightRoute(),
                                 scenic: Fixture.straightRoute())
            }
            await model.computeRoute()
            XCTAssertEqual(Recents.load().map(\.name), ["New York"])
        }
    }

    func test_location_off_is_a_sentence_with_a_way_to_settings() {
        XCTAssertEqual(LocationManager.locationOffText,
                       "Location access is off. Allow it in Settings to start from here.")
        XCTAssertNotNil(URL(string: UIApplication.openSettingsURLString))
    }

    // MARK: - 6. The first screen

    func test_the_first_screen_leads_with_what_the_app_does() {
        XCTAssertTrue(BeforeYouDriveView.whatItDoes.hasPrefix("Sunday Drive finds"))
        let limits = BeforeYouDriveView.limits.map { "\($0.head) \($0.body)" }
        XCTAssertEqual(limits.count, 4)
        XCTAssertTrue(limits[0].contains("310 miles"))
        for text in limits + [BeforeYouDriveView.whatItDoes] {
            XCTAssertFalse(text.contains("311"), text)
            XCTAssertFalse(text.contains("New England"), text)
            XCTAssertFalse(text.contains("%"), "the junction-approach statistic is gone: \(text)")
            XCTAssertFalse(text.contains("Alaska") || text.contains("Hawaii"), text)
        }
    }
}
