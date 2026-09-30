import XCTest
@testable import Scenic

/// The sentence that replaced the six scenery bars at the top of the results,
/// and the road names under it.
///
/// Both are prose assembled from numbers, which is the shape of thing that
/// drifts away from the numbers it came from. Every case here is either a claim
/// the sentence must not make, or a rounding it must share with the bars still
/// sitting under the disclosure.
@MainActor
final class RouteDescriptionTests: XCTestCase {

    /// A route of a stated length whose scenery mileage is dictated outright,
    /// decoded from JSON the way the app really receives it.
    private func props(km: Double, scenery: [String: Double]) -> RouteProps {
        Fixture.decode(Fixture.feature(
            coordinates: [[-71.0, 42.0], [-71.0, 42.1]],
            km: km, minutes: 30,
            steps: [(Fixture.origin, "Head north", nil)],
            sceneryKm: scenery)).properties
    }

    // MARK: - What the drive is

    func test_a_drive_that_really_is_mostly_one_thing_says_so() {
        let described = RouteDescription(
            props(km: 10, scenery: ["forest/park": 8.0, "water": 2.0]))

        XCTAssertEqual(described.character,
                       "Mostly forest, with 1 mile along the water.")
    }

    func test_mostly_is_not_claimed_when_nothing_covers_half_the_drive() {
        // "Mostly forest" over 3 km of forest on a 10 km route is a sentence
        // the breakdown underneath would immediately contradict.
        let described = RouteDescription(
            props(km: 10, scenery: ["forest/park": 3.0, "water": 2.0]))

        XCTAssertEqual(described.character,
                       "2 miles through forest, with 1 mile along the water.")
        XCTAssertFalse(described.character!.contains("Mostly"))
    }

    func test_overlapping_features_cannot_add_up_to_a_false_majority() {
        // The reason the lead clause is a *share of the route* and not a share
        // of the scenery total: a lakeside road through woods is counted under
        // both `water` and `forest/park`, so these three sum to 12 km on a
        // 10 km route. Ranked against each other, forest would be "most" of a
        // drive that is 40% forest.
        let described = RouteDescription(
            props(km: 10, scenery: ["forest/park": 4.0, "water": 4.0, "hills": 4.0]))

        XCTAssertNotNil(described.character)
        XCTAssertFalse(described.character!.contains("Mostly"), described.character!)
    }

    func test_features_tied_on_mileage_are_ordered_the_same_way_every_time() {
        // Rounding to whole miles makes ties ordinary, and `sorted(by:)` is not
        // documented as stable — so this is the same route described twice.
        let scenery = ["forest/park": 4.0, "water": 4.0, "hills": 4.0]
        let first = RouteDescription(props(km: 10, scenery: scenery)).character

        for _ in 0..<50 {
            XCTAssertEqual(RouteDescription(props(km: 10, scenery: scenery)).character,
                           first)
        }
        // The server's display order breaks the tie, so forest leads water.
        XCTAssertEqual(first, "2 miles through forest, with 2 miles along the water.")
    }

    func test_a_feature_under_a_mile_is_not_mentioned_at_all() {
        // The same one-mile floor `sceneryBreakdown` filters the bars by, so
        // the sentence cannot name a feature the bars below it do not show.
        let described = RouteDescription(
            props(km: 10, scenery: ["forest/park": 8.0, "coast": 0.5]))

        XCTAssertEqual(described.character, "Mostly forest.")
        XCTAssertFalse(described.character!.contains("coast"))
    }

    func test_a_single_mile_is_not_plural() {
        let described = RouteDescription(
            props(km: 100, scenery: ["forest/park": 1.7]))

        XCTAssertEqual(described.character, "1 mile through forest.")
    }

    func test_a_route_that_passes_nothing_has_nothing_to_say() {
        let described = RouteDescription(props(km: 10, scenery: [:]))

        XCTAssertNil(described.character)
    }

    // MARK: - Which roads it goes down

    func test_the_roads_named_are_the_ones_the_drive_spends_itself_on() {
        // The default fixture: 1 km on Test Road, 2 km each on Elm and Oak.
        //
        // Membership rather than the whole string, because Elm and Oak are not
        // quite tied. `Fixture` places each maneuver by offsetting latitude and
        // then measures the gap geodesically, and a degree of latitude is
        // longer the further north you go — so Oak, sitting 2 km up the road
        // from Elm, measures about 9 mm more for the same nominal 2 km. Which
        // of the two leads is therefore a fact about WGS84, not about this
        // code, and asserting it would be a test of Core Location.
        let via = RouteDescription(Fixture.routeWithRoadNames().properties).via

        XCTAssertNotNil(via)
        XCTAssertTrue(via!.hasPrefix("via "), via!)
        XCTAssertTrue(via!.contains("Elm Street"), via!)
        XCTAssertTrue(via!.contains("Oak Street"), via!)
        XCTAssertFalse(via!.contains("Test Road"), "only the two longest are named")
    }

    func test_the_roads_are_named_in_the_same_order_every_time() {
        // The property that actually matters, and the one a dictionary breaks:
        // `metersByRoad` has no order of its own, so without the sort the same
        // route would name its roads differently between launches.
        let first = RouteDescription(Fixture.routeWithRoadNames().properties).via

        for _ in 0..<50 {
            XCTAssertEqual(RouteDescription(Fixture.routeWithRoadNames().properties).via,
                           first)
        }
    }

    func test_a_road_the_route_rejoins_counts_both_passes() {
        // River Road twice for 1.5 km each, Bridge Street once for 2 km. Taken
        // a leg at a time Bridge Street is the longest thing on the route;
        // summed under its name, River Road is.
        let route = Fixture.routeWithRoadNames(steps: [
            (0, "Head north on River Road", "River Road"),
            (1500, "Turn onto Bridge Street", "Bridge Street"),
            (3500, "Turn back onto River Road", "River Road"),
            (5000, "Arrive at your destination", ""),
        ])

        XCTAssertEqual(RouteDescription(route.properties).via,
                       "via River Road and Bridge Street")
    }

    func test_a_short_connector_at_the_end_of_a_drive_is_not_named() {
        // 200 m of "Connector" is a road the route touches and nobody would
        // mention. Without the floor it is half of what this line says.
        let route = Fixture.routeWithRoadNames(steps: [
            (0, "Head north on Connector", "Connector"),
            (200, "Turn onto Main Street", "Main Street"),
            (5000, "Arrive at your destination", ""),
        ])

        XCTAssertEqual(RouteDescription(route.properties).via, "via Main Street")
    }

    func test_a_response_without_road_names_says_nothing_about_roads() {
        // What a route cached before the `name` field existed looks like, and
        // what the 4% of legs carrying neither a name nor a ref look like.
        let described = RouteDescription(Fixture.straightRoute().properties)

        XCTAssertNil(described.via)
        XCTAssertNotNil(described.character, "the scenery half still works")
        XCTAssertFalse(described.isEmpty)
    }

    func test_a_route_with_neither_half_is_empty_rather_than_blank() {
        // `RouteResults` hides the whole block on this, instead of leaving a
        // gap where a sentence should be.
        let route = Fixture.decode(Fixture.feature(
            coordinates: [[-71.0, 42.0], [-71.0, 42.1]],
            km: 10, minutes: 30,
            steps: [(Fixture.origin, "Head north", nil)],
            sceneryKm: [:]))

        XCTAssertTrue(RouteDescription(route.properties).isEmpty)
    }
}
