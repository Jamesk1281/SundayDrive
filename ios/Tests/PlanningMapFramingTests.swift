import CoreLocation
import MapKit
import SwiftUI
import XCTest
@testable import SundayDrive

/// The planning map card runs under the status bar, and the camera has to frame
/// routes into the part of it below that strip.
///
/// These tests play MapKit's half of the contract, as measured on iOS 26.4:
/// `.rect` is fitted to the map by aspect ratio and centred, with no padding of
/// its own. Then they check where every point and pin lands on the card. What
/// they cannot check is the timing: the camera has to be applied once the card
/// has its final height, which `PlanningView.refit` waits for, and which was
/// verified in the simulator rather than here.
final class PlanningMapFramingTests: XCTestCase {

    /// The loop and route cards on an iPhone 17 Pro Max, and the strip its
    /// status bar and Dynamic Island cover. All three measured in the simulator.
    private let loopCard = CGSize(width: 440, height: 200)
    private let routeCard = CGSize(width: 440, height: 218)
    private let strip: CGFloat = 62

    // MARK: - Shapes

    /// A loop heading southeast from a start at its northern tip, taller than
    /// it is wide, like the Concord loops that went under the clock.
    private let southLoop = metres([
        (0, 0), (4_000, -2_000), (7_000, -9_000), (6_000, -11_000),
        (2_000, -8_000), (1_000, -3_000), (0, 0),
    ])

    /// The same loop heading north: its turnaround is now its top.
    private var northLoop: [CLLocationCoordinate2D] {
        southLoop.map { Fixture.offset(east: east(of: $0), north: -north(of: $0)) }
    }

    /// A long, low route ending to the northeast, like Concord to Rockport,
    /// whose destination balloon sat under the Wi-Fi icon.
    private let eastRoute = metres([
        (0, 0), (12_000, 3_000), (25_000, 6_000), (40_000, 12_000),
        (52_000, 17_000), (60_000, 22_000),
    ])

    /// Long and nearly flat, so the card's width is what limits it: the one
    /// shape where the side padding is exactly 12% rather than slack.
    private let flatRoute = metres([
        (0, 0), (15_000, 1_500), (30_000, 2_500), (45_000, 3_500), (60_000, 4_000),
    ])

    // MARK: - Clear of the strip

    func test_a_south_loop_starts_below_the_status_bar() throws {
        let rect = try fitted(southLoop, pins: [.dot(southLoop[0]), .marker(southLoop[3])],
                              card: loopCard)
        let start = project(southLoop[0], rect, loopCard)
        XCTAssertGreaterThanOrEqual(start.y - 10, strip - 0.01, "the start dot is under the status bar")
        for point in southLoop {
            XCTAssertGreaterThanOrEqual(project(point, rect, loopCard).y - 3, strip - 0.01)
        }
    }

    /// The test above can fail: ignore the strip and the start dot lands where
    /// it did on the device, 31 pt down a card whose top 62 pt are covered.
    func test_ignoring_the_strip_puts_the_start_under_it() throws {
        let rect = try fitted(southLoop, card: loopCard, topInset: 0)
        XCTAssertEqual(project(southLoop[0], rect, loopCard).y, 200 * 0.22 / 1.44, accuracy: 0.01)
    }

    /// A `Marker` stands 35 pt tall on its coordinate, and 22% of a loop's
    /// height on this card is about 21 pt. Proportional headroom alone left the
    /// top of the balloon under the strip.
    func test_a_turnaround_at_the_top_keeps_its_whole_balloon_clear() throws {
        let turnaround = northLoop[3]
        let rect = try fitted(northLoop, pins: [.dot(northLoop[0]), .marker(turnaround)],
                              card: loopCard)
        XCTAssertGreaterThanOrEqual(project(turnaround, rect, loopCard).y - 35, strip - 0.01)

        let withoutPins = try fitted(northLoop, card: loopCard)
        XCTAssertLessThan(project(turnaround, withoutPins, loopCard).y - 35, strip,
                          "this shape does not exercise the balloon")
    }

    func test_a_destination_to_the_northeast_keeps_its_balloon_clear() throws {
        let end = eastRoute[eastRoute.count - 1]
        let rect = try fitted(eastRoute, pins: [.dot(eastRoute[0]), .marker(end)], card: routeCard)
        XCTAssertGreaterThanOrEqual(project(end, rect, routeCard).y - 35, strip - 0.01)
        for point in eastRoute {
            let p = project(point, rect, routeCard)
            XCTAssertGreaterThanOrEqual(p.y - 3, strip - 0.01)
            XCTAssertLessThanOrEqual(p.y, routeCard.height)
            XCTAssertGreaterThanOrEqual(p.x, 0)
            XCTAssertLessThanOrEqual(p.x, routeCard.width)
        }
    }

    // MARK: - Still filling the card

    /// The fix must not come out of the other three sides: the line keeps 12%
    /// of its width either side and 22% of its height below.
    func test_the_sides_and_the_bottom_keep_their_padding() throws {
        let flat = try fitted(flatRoute, pins: cases[3].1, card: routeCard)
        let xs = flatRoute.map { project($0, flat, routeCard).x }
        XCTAssertEqual((xs.max()! - xs.min()!) * 1.24, routeCard.width, accuracy: 0.01,
                       "the flat route should be limited by the card's width")
        for (line, pins, card) in cases {
            let rect = try fitted(line, pins: pins, card: card)
            let points = line.map { project($0, rect, card) }
            let xs = points.map(\.x), ys = points.map(\.y)
            let width = xs.max()! - xs.min()!, height = ys.max()! - ys.min()!
            XCTAssertGreaterThanOrEqual(xs.min()!, width * 0.12 - 0.01)
            XCTAssertGreaterThanOrEqual(card.width - xs.max()!, width * 0.12 - 0.01)
            XCTAssertGreaterThanOrEqual(card.height - ys.max()!, height * 0.22 - 0.01)
        }
    }

    /// As close as those rules allow, and no further: the padded line spans
    /// the card's width, or the height below the strip, or a pin's artwork
    /// touches the strip. Anything else is a route drawn smaller than it had
    /// to be.
    func test_the_route_is_as_large_as_the_rules_allow() throws {
        for (line, pins, card) in cases {
            let rect = try fitted(line, pins: pins, card: card)
            let points = line.map { project($0, rect, card) }
            let xs = points.map(\.x), ys = points.map(\.y)
            let paddedWidth = (xs.max()! - xs.min()!) * 1.24
            let paddedHeight = (ys.max()! - ys.min()!) * 1.44
            let pinTops = pins.map { project($0.coordinate, rect, card).y - $0.reach }
            let spansWidth = abs(paddedWidth - card.width) < 0.5
            let spansHeight = abs(paddedHeight - (card.height - strip)) < 0.5
            let pinTouches = pinTops.contains { abs($0 - strip) < 0.5 }
            XCTAssertTrue(spansWidth || spansHeight || pinTouches,
                          "width \(paddedWidth), height \(paddedHeight), pin tops \(pinTops)")
        }
    }

    /// When the width is what limits a route, the height to spare is shared
    /// above and below it rather than all left at the bottom.
    func test_spare_height_is_shared_above_and_below() throws {
        let rect = try fitted(flatRoute, card: routeCard)
        let ys = flatRoute.map { project($0, rect, routeCard).y }
        let lineHeight = ys.max()! - ys.min()!
        let above = ys.min()! - lineHeight * 0.22 - strip
        let below = routeCard.height - (ys.max()! + lineHeight * 0.22)
        XCTAssertGreaterThan(above, 10, "this shape has no height to spare")
        XCTAssertEqual(above, below, accuracy: 0.01)
    }

    // MARK: - What MapKit is handed

    /// The rect is the whole card in map points, so MapKit has nothing to
    /// adjust: fitting it by aspect and centring it leaves it exactly as given.
    func test_the_rect_has_the_cards_shape() throws {
        for (line, pins, card) in cases {
            let rect = try fitted(line, pins: pins, card: card)
            XCTAssertEqual(rect.width / rect.height, Double(card.width / card.height),
                           accuracy: 1e-9)
        }
    }

    // MARK: - Unchanged where there is nothing to dodge

    /// With no strip and no pins this is the fit it always was: the padded
    /// line handed over as a rect, fitted by aspect and centred.
    func test_with_no_strip_the_framing_is_what_it_was() throws {
        for (line, _, card) in cases {
            let rect = try fitted(line, card: card, topInset: 0)
            let old = paddedRect(line)
            for point in line {
                let new = project(point, rect, card), was = project(point, old, card)
                XCTAssertEqual(new.x, was.x, accuracy: 0.01)
                XCTAssertEqual(new.y, was.y, accuracy: 0.01)
            }
        }
    }

    func test_before_the_card_has_a_size_it_fits_the_whole_card() throws {
        let rect = try fitted(southLoop, card: .zero)
        let old = paddedRect(southLoop)
        XCTAssertEqual(rect.origin.x, old.origin.x, accuracy: 1e-6)
        XCTAssertEqual(rect.origin.y, old.origin.y, accuracy: 1e-6)
        XCTAssertEqual(rect.size.width, old.size.width, accuracy: 1e-6)
        XCTAssertEqual(rect.size.height, old.size.height, accuracy: 1e-6)
    }

    func test_nothing_to_fit_leaves_the_camera_alone() {
        XCTAssertNil(MapCameraPosition.fitting(nil, card: loopCard, topInset: strip))
        XCTAssertNil(MapCameraPosition.fitting([], card: loopCard, topInset: strip))
    }

    // MARK: - Helpers

    private var cases: [([CLLocationCoordinate2D], [PlanningMap.Pin], CGSize)] {
        [
            (southLoop, [.dot(southLoop[0]), .marker(southLoop[3])], loopCard),
            (northLoop, [.dot(northLoop[0]), .marker(northLoop[3])], loopCard),
            (eastRoute, [.dot(eastRoute[0]), .marker(eastRoute[eastRoute.count - 1])], routeCard),
            (flatRoute, [.dot(flatRoute[0]), .marker(flatRoute[flatRoute.count - 1])], routeCard),
        ]
    }

    private func fitted(_ line: [CLLocationCoordinate2D], pins: [PlanningMap.Pin] = [],
                        card: CGSize, topInset: CGFloat? = nil) throws -> MKMapRect {
        let position = MapCameraPosition.fitting(line, pins: pins, card: card,
                                                 topInset: topInset ?? strip)
        return try XCTUnwrap(position?.rect)
    }

    /// Where MapKit draws `coordinate` when handed `rect` for a map of `size`:
    /// the rect fitted by aspect ratio and centred.
    private func project(_ coordinate: CLLocationCoordinate2D, _ rect: MKMapRect,
                         _ size: CGSize) -> CGPoint {
        let width = Double(size.width), height = Double(size.height)
        let scale = max(rect.width / width, rect.height / height)
        let point = MKMapPoint(coordinate)
        return CGPoint(x: (point.x - rect.midX) / scale + width / 2,
                       y: (point.y - rect.midY) / scale + height / 2)
    }

    /// What `fitting` handed MapKit before it knew about the strip.
    private func paddedRect(_ line: [CLLocationCoordinate2D]) -> MKMapRect {
        var rect = MKMapRect.null
        for coordinate in line {
            let p = MKMapPoint(coordinate)
            rect = rect.union(MKMapRect(x: p.x, y: p.y, width: 0, height: 0))
        }
        return MKMapRect(x: rect.origin.x - rect.size.width * 0.12,
                         y: rect.origin.y - rect.size.height * 0.22,
                         width: rect.size.width * 1.24,
                         height: rect.size.height * 1.44)
    }

    private func east(of c: CLLocationCoordinate2D) -> Double {
        (c.longitude - Fixture.origin.longitude)
            * Fixture.metersPerDegLat * cos(Fixture.origin.latitude * .pi / 180)
    }

    private func north(of c: CLLocationCoordinate2D) -> Double {
        (c.latitude - Fixture.origin.latitude) * Fixture.metersPerDegLat
    }
}

/// A line from offsets in metres east and north of the fixture origin.
private func metres(_ offsets: [(east: Double, north: Double)]) -> [CLLocationCoordinate2D] {
    offsets.map { Fixture.offset(east: $0.east, north: $0.north) }
}
