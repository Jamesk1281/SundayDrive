import CoreLocation
import XCTest
@testable import SundayDrive

/// `progress` is what every number on the drive screen is built from — how far
/// off the line the driver is, and how much road is left.
final class GeoTests: XCTestCase {

    private let line = (0...20).map { Fixture.north(Double($0) * 250) }   // 5 km north

    func test_a_point_on_the_line_is_not_off_route() {
        let here = progress(of: Fixture.north(1200), along: line)
        XCTAssertEqual(here.offRoute, 0, accuracy: 1)
        XCTAssertEqual(here.remaining, 3800, accuracy: 5)
    }

    func test_a_point_between_two_vertices_is_still_on_route() {
        // Vertices are 250 m apart here and can be kilometres apart on a real
        // road; measuring to the nearest *vertex* rather than the nearest
        // segment would call a driver on a straight highway "off route".
        let here = progress(of: Fixture.north(1125), along: line)
        XCTAssertEqual(here.offRoute, 0, accuracy: 1)
    }

    func test_offset_from_the_line_is_the_perpendicular_distance() {
        let east = CLLocationCoordinate2D(
            latitude: Fixture.north(1200).latitude,
            longitude: -71.0 + 100 / (111_320 * cos(42.0 * .pi / 180)))
        let here = progress(of: east, along: line)
        XCTAssertEqual(here.offRoute, 100, accuracy: 5)
        XCTAssertEqual(here.remaining, 3800, accuracy: 10)
    }

    func test_before_the_start_the_whole_route_is_left() {
        let here = progress(of: Fixture.north(-500), along: line)
        XCTAssertEqual(here.remaining, 5000, accuracy: 5)
        XCTAssertEqual(here.offRoute, 500, accuracy: 5)
    }

    func test_past_the_end_nothing_is_left() {
        let here = progress(of: Fixture.north(5400), along: line)
        XCTAssertEqual(here.remaining, 0, accuracy: 5)
    }

    func test_remaining_never_goes_negative() {
        for metres in stride(from: -1000.0, through: 6000.0, by: 137) {
            XCTAssertGreaterThanOrEqual(
                progress(of: Fixture.north(metres), along: line).remaining, 0)
        }
    }

    func test_remaining_decreases_as_the_driver_advances() {
        var last = Double.greatestFiniteMagnitude
        for metres in stride(from: 0.0, through: 5000.0, by: 250) {
            let remaining = progress(of: Fixture.north(metres), along: line).remaining
            XCTAssertLessThan(remaining, last + 1)
            last = remaining
        }
    }

    // MARK: - A road driven twice

    /// `metres` north of the origin and `east` metres east of it.
    private func at(_ metres: Double, east: Double = 0) -> CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: Fixture.north(metres).latitude,
                               longitude: -71.0 + east / (111_320 * cos(42.0 * .pi / 180)))
    }

    /// 2 km north and back down the same coordinates: a 4 km out-and-back,
    /// whose two passes are identical, as a loop's start and end are.
    private var outAndBack: [CLLocationCoordinate2D] {
        let out = (0...8).map { Fixture.north(Double($0) * 250) }
        return out + out.reversed().dropFirst()
    }

    func test_on_identical_passes_the_match_stays_on_the_one_being_driven() {
        // 500 m out is equally 3,500 m along. Which one is float noise unless
        // something says where the driver already is.
        let outbound = progress(of: Fixture.north(500), along: outAndBack, notBefore: 0)
        XCTAssertEqual(outbound.travelled, 500, accuracy: 1)
        let inbound = progress(of: Fixture.north(500), along: outAndBack,
                               notBefore: 3300, near: 3400)
        XCTAssertEqual(inbound.travelled, 3500, accuracy: 1)
    }

    func test_the_start_of_a_closed_line_is_not_its_end() {
        // The driveway fix of a loop, and the maneuver placed there.
        let here = progress(of: Fixture.north(20), along: outAndBack)
        XCTAssertEqual(here.remaining, 3980, accuracy: 1)
    }

    func test_just_past_a_u_turn_the_match_is_on_the_return_leg() {
        // 30 m back down from the turn at 2 km, last matched 10 m short of it:
        // the floor still reaches the outbound leg, which is as close.
        let here = progress(of: Fixture.north(1970), along: outAndBack,
                            notBefore: 1890, near: 2020)
        XCTAssertEqual(here.travelled, 2030, accuracy: 1)
        // And with the last match exactly at the turn, which is where a
        // running maximum waits while the car drives away from it: the two
        // legs are then equally far either side.
        let away = progress(of: Fixture.north(1950), along: outAndBack,
                            notBefore: 1900, near: 2000)
        XCTAssertEqual(away.travelled, 2050, accuracy: 1)
    }

    func test_passes_within_a_metre_are_a_tie_and_continuity_decides() {
        // A return pass 0.5 m east and the car 0.4 m east of the outbound one:
        // strictly nearer the return, but that is not a different road.
        let out = (0...8).map { at(Double($0) * 250) }
        let back = (0...8).reversed().map { at(Double($0) * 250, east: 0.5) }
        let here = progress(of: at(500, east: 0.4), along: out + back,
                            notBefore: 400, near: 490)
        XCTAssertEqual(here.travelled, 500, accuracy: 1)
    }

    func test_the_other_carriageway_is_a_different_road_whatever_continuity_says() {
        // The 2026-08-25 Southwest Cutoff case: the match had run ahead onto
        // the return carriageway, and the car sat 1.9 m from the outbound one
        // and 8 m from the return. The nearer road is where the car is.
        let out = (0...8).map { at(Double($0) * 250) }
        let back = (0...8).reversed().map { at(Double($0) * 250, east: 10) }
        let here = progress(of: at(500, east: 1.9), along: out + back,
                            notBefore: 0, near: 3600)
        XCTAssertEqual(here.travelled, 500, accuracy: 1)
        XCTAssertEqual(here.offRoute, 1.9, accuracy: 0.2)
    }

    func test_a_pass_clearly_nearer_still_wins_however_far_on() {
        // After a long gap in the fixes the driver really is kilometres on,
        // and nothing near where they were is close to where they are.
        let jumped = progress(of: Fixture.north(4200), along: line, notBefore: 1400, near: 1500)
        XCTAssertEqual(jumped.travelled, 4200, accuracy: 1)
        // And a return carriageway well outside the tolerance is a different road.
        let out = (0...8).map { at(Double($0) * 250) }
        let back = (0...8).reversed().map { at(Double($0) * 250, east: 40) }
        let here = progress(of: at(500, east: 40), along: out + back, notBefore: 400, near: 500)
        XCTAssertEqual(here.offRoute, 0, accuracy: 0.5)
        XCTAssertGreaterThan(here.travelled, 3000)
    }

    func test_the_segment_just_behind_on_the_same_road_is_not_a_second_pass() {
        // 5 m past a vertex the previous segment is 5 m off at its end; taking
        // it because it is nearer `near` would lag the match and inflate offRoute.
        let here = progress(of: Fixture.north(1005), along: line, notBefore: 900, near: 993)
        XCTAssertEqual(here.travelled, 1005, accuracy: 0.5)
        XCTAssertEqual(here.offRoute, 0, accuracy: 0.5)
    }

    func test_just_past_a_vertex_the_match_is_past_it() {
        // Maneuvers sit on vertices. A fix 0.3 m past one is 0.3 m from the
        // end of the segment behind, which ties with the 0 m of the segment
        // ahead; matched at the vertex, the maneuver reads as not yet passed.
        let here = progress(of: Fixture.north(1000.3), along: line, notBefore: 900, near: 990)
        XCTAssertGreaterThan(here.travelled, 1000.1)
    }

    func test_outside_a_corner_the_vertex_is_still_matched() {
        // Both segments meet the point at their shared vertex: neither is
        // dominated, and something must be matched.
        let corner = [Fixture.origin, Fixture.north(500), at(500, east: 500)]
        let here = progress(of: at(520, east: -20), along: corner, notBefore: 0, near: 400)
        XCTAssertEqual(here.travelled, 500, accuracy: 0.5)
        XCTAssertEqual(here.offRoute, 28.3, accuracy: 0.5)
    }

    func test_a_degenerate_line_does_not_crash() {
        XCTAssertEqual(progress(of: Fixture.origin, along: []).offRoute, .infinity)
        let single = progress(of: Fixture.north(100), along: [Fixture.origin])
        XCTAssertEqual(single.offRoute, 100, accuracy: 5)
        XCTAssertEqual(single.remaining, 0)
    }

    func test_kilometres_convert_to_miles() {
        XCTAssertEqual(1.0.milesFromKm, 0.621371, accuracy: 1e-6)
        XCTAssertEqual(160.9344.milesFromKm, 100, accuracy: 0.01)
    }

    func test_whole_miles_round_rather_than_truncate() {
        // 24.9 km is 15.47 mi. Truncated that reads 15, which is the rounding
        // the scenery breakdown used to do on its way to showing "0 mi".
        XCTAssertEqual(24.9.wholeMilesFromKm, 15)
        XCTAssertEqual(25.5.wholeMilesFromKm, 16)
        // Anything below half a mile has no whole mile in it, which is what the
        // breakdown filter keys off.
        XCTAssertEqual(0.3.wholeMilesFromKm, 0)
        XCTAssertEqual(0.8.wholeMilesFromKm, 0)
        XCTAssertEqual(0.9.wholeMilesFromKm, 1)
    }

    func test_coordinates_compare_by_value() {
        XCTAssertTrue(Fixture.origin.matches(Fixture.origin))
        XCTAssertFalse(Fixture.origin.matches(Fixture.north(1)))
    }
}
