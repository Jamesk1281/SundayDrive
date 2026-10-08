import CoreLocation
import MapKit
import XCTest
@testable import SundayDrive

/// What a phone outside New England can and cannot do.
///
/// Production answered a loop requested from Cupertino with HTTP 400 and
/// "point is outside the covered road network (currently New England)", which
/// the app printed verbatim. That is what a reviewer outside the region saw on
/// tapping Loop. These pin the replacement: the fix is judged on the phone, the
/// message says what to do instead, and **no request is made**. Both fetch
/// seams count their calls, so "nothing reached the server" is a number here.
@MainActor
final class OutsideNewEnglandTests: XCTestCase {

    private static let cupertino = CLLocationCoordinate2D(latitude: 37.3349, longitude: -122.0090)
    private static let boston = CLLocationCoordinate2D(latitude: 42.3601, longitude: -71.0589)
    private static let rockport = CLLocationCoordinate2D(latitude: 42.6557, longitude: -70.6203)

    private func fix(_ coordinate: CLLocationCoordinate2D) -> CLLocation {
        CLLocation(coordinate: coordinate, altitude: 0, horizontalAccuracy: 5,
                   verticalAccuracy: 5, timestamp: Date())
    }

    // MARK: - Directions

    /// A model whose fix is `here` and whose route requests are counted.
    private func directions(at here: CLLocationCoordinate2D) -> (RouteModel, () -> Int) {
        let model = RouteModel()
        let fix = fix(here)
        model.locate = { fix }
        var requests = 0
        model.fetchRoute = { from, to, _, _, _ in
            requests += 1
            let leg = Fixture.decode(Fixture.feature(
                coordinates: [[from.longitude, from.latitude], [to.longitude, to.latitude]],
                km: 60, minutes: 70,
                steps: [(from, "Head out", nil), (to, "Arrive", nil)]))
            return Fixture.response(fastest: leg, scenic: leg)
        }
        return (model, { requests })
    }

    func test_my_location_outside_new_england_says_so_and_sends_nothing() async {
        let (model, requests) = directions(at: Self.cupertino)
        model.end = Self.rockport
        model.endQuery = "Rockport, MA"
        let biasBefore = model.searchRegion.center

        await model.useMyLocation()

        XCTAssertEqual(model.errorText, NewEngland.outsideHere)
        XCTAssertEqual(requests(), 0, "no route request reaches the server")
        XCTAssertNil(model.start, "Cupertino never becomes the start")
        XCTAssertNil(model.response)
        XCTAssertEqual(model.locationManager.regionStatus, .outside)
        XCTAssertEqual(model.searchRegion.center.latitude, biasBefore.latitude,
                       "search is not re-ranked around Cupertino")
        XCTAssertFalse(model.isLocatingUser, "the spinner stops")
    }

    func test_a_start_already_typed_survives_an_outside_my_location() async {
        let (model, requests) = directions(at: Self.cupertino)
        model.start = Self.boston
        model.startQuery = "Boston, MA"

        await model.useMyLocation()

        XCTAssertEqual(model.start?.latitude, Self.boston.latitude, "the typed start is left alone")
        XCTAssertEqual(model.startQuery, "Boston, MA")
        XCTAssertEqual(requests(), 0)
    }

    func test_my_location_inside_new_england_still_plans() async {
        let (model, requests) = directions(at: Self.boston)
        model.end = Self.rockport

        await model.useMyLocation()

        XCTAssertEqual(model.start?.latitude, Self.boston.latitude)
        XCTAssertEqual(requests(), 1, "the route is requested as before")
        XCTAssertNil(model.errorText)
        XCTAssertNotNil(model.response)
        XCTAssertEqual(model.locationManager.regionStatus, .inside)
    }

    // MARK: - Loop

    private func loop(at here: CLLocationCoordinate2D) -> (LoopModel, LocationManager, () -> Int) {
        let manager = LocationManager()
        let model = LoopModel(locationManager: manager)
        let fix = fix(here)
        model.locate = { fix }
        var requests = 0
        model.fetchLoop = { start, km, sector, _ in
            requests += 1
            return Self.loopResponse(around: start, km: km, sector: sector ?? "N")
        }
        return (model, manager, { requests })
    }

    func test_a_loop_from_outside_new_england_says_so_and_sends_nothing() async {
        // The Loop row on Home used to call this with no form in between, so
        // this was the reviewer's one tap to the server's raw error.
        let (model, manager, requests) = loop(at: Self.cupertino)

        await model.useMyLocation()

        XCTAssertEqual(model.errorText, NewEngland.outsideHere)
        XCTAssertEqual(requests(), 0, "no loop request reaches the server")
        XCTAssertNil(model.start)
        XCTAssertNil(model.response)
        XCTAssertEqual(manager.regionStatus, .outside)
    }

    func test_a_loop_from_inside_new_england_still_plans() async {
        let (model, manager, requests) = loop(at: Self.boston)

        await model.useMyLocation()

        XCTAssertEqual(requests(), 1)
        XCTAssertEqual(model.start?.latitude, Self.boston.latitude)
        XCTAssertNotNil(model.response)
        XCTAssertEqual(manager.regionStatus, .inside)
    }

    func test_one_status_is_shared_by_both_planning_stages() async {
        // Directions' My Location and the Loop row write the same answer, so
        // Home cannot say "from here" after Directions has learnt otherwise.
        let (model, _) = directions(at: Self.cupertino)
        let fix = fix(Self.cupertino)
        model.loops.locate = { fix }
        model.loops.fetchLoop = { _, _, _, _ in
            XCTFail("no request from outside")
            throw URLError(.cancelled)
        }
        XCTAssertEqual(model.locationManager.regionStatus, .unknown, "nothing known before a fix")

        await model.loops.useMyLocation()
        XCTAssertEqual(model.locationManager.regionStatus, .outside)

        let inBoston = self.fix(Self.boston)
        model.locate = { inBoston }
        model.fetchRoute = { _, _, _, _, _ in throw URLError(.cancelled) }
        await model.useMyLocation()
        XCTAssertEqual(model.locationManager.regionStatus, .inside, "the latest fix wins")
    }

    // MARK: - Recents

    func test_a_saved_destination_outside_new_england_is_not_offered() {
        let key = "recentDestinations"
        let saved = UserDefaults.standard.data(forKey: key)
        defer {
            // The test host is the real app, so put its list back as found.
            if let saved { UserDefaults.standard.set(saved, forKey: key) }
            else { UserDefaults.standard.removeObject(forKey: key) }
        }
        let rows = [
            Recent(name: "Rockport", subtitle: "MA", latitude: 42.6557, longitude: -70.6203),
            Recent(name: "Portland", subtitle: "OR", latitude: 45.5151, longitude: -122.6795),
        ]
        UserDefaults.standard.set(try! JSONEncoder().encode(rows), forKey: key)

        XCTAssertEqual(Recents.load().map(\.name), ["Rockport"])
    }

    func test_clearing_recents_empties_the_list() {
        let key = "recentDestinations"
        let saved = UserDefaults.standard.data(forKey: key)
        defer {
            if let saved { UserDefaults.standard.set(saved, forKey: key) }
            else { UserDefaults.standard.removeObject(forKey: key) }
        }
        Recents.remember(Recent(name: "Rockport", subtitle: "MA",
                                latitude: 42.6557, longitude: -70.6203))
        XCTAssertFalse(Recents.load().isEmpty)

        Recents.clear()
        XCTAssertEqual(Recents.load(), [])
    }

    // MARK: - Fixture

    private static func loopResponse(around start: CLLocationCoordinate2D, km: Double,
                                     sector: String) -> LoopResponse {
        let (lat, lon) = (start.latitude, start.longitude)
        let ring: [[Double]] = [[lon, lat], [lon, lat + 0.1], [lon + 0.1, lat + 0.1],
                                [lon + 0.1, lat], [lon, lat]]
        let object: [String: Any] = [
            "loop": [
                "type": "Feature",
                "geometry": ["type": "LineString", "coordinates": ring],
                "properties": [
                    "km": km, "minutes": km * 1.6, "mean_score": 5.8,
                    "scenery_km": ["water": 4.0],
                    "steps": [
                        ["instruction": "Head north", "lat": lat, "lon": lon,
                         "distance_m": 1000, "type": "depart"],
                        ["instruction": "Arrive back where you started", "lat": lat,
                         "lon": lon, "distance_m": 0, "type": "arrive"],
                    ],
                ],
            ],
            "meta": [
                "target_km": km, "km": km, "minutes": km * 1.6, "mean_score": 5.8,
                "beautiful_km": km * 0.4, "beautiful_score": 7.0, "repeated_km": 0.0,
                "turnaround": [lat + 0.1, lon + 0.05], "sector": sector,
            ],
            "alternatives": [["sector": sector, "candidates": 500]],
            "note": NSNull(),
        ]
        let data = try! JSONSerialization.data(withJSONObject: object)
        return try! JSONDecoder().decode(LoopResponse.self, from: data)
    }
}
