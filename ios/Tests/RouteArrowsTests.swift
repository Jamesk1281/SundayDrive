import CoreLocation
import MapKit
import XCTest
@testable import SundayDrive

/// The chevrons that say which way a route line is driven.
final class RouteArrowsTests: XCTestCase {

    /// A straight line due east, about 5 km long, in Massachusetts.
    private let east = [CLLocationCoordinate2D(latitude: 42.4, longitude: -71.40),
                        CLLocationCoordinate2D(latitude: 42.4, longitude: -71.34)]

    /// A frame that sees everything, at `scale` map points per screen point.
    private func everything(_ scale: Double) -> RouteArrows.Frame {
        RouteArrows.Frame(scale: scale, visible: .world)
    }

    func testEveryChevronPointsTheWayTheLineIsDriven() {
        for line in [east, Array(east.reversed())] {
            let chevrons = RouteArrows.chevrons(along: line, in: everything(10), style: .driving)
            XCTAssertFalse(chevrons.isEmpty)
            let forward = MKMapPoint(line[1]).x - MKMapPoint(line[0]).x
            for chevron in chevrons {
                let (left, tip, right) = (chevron.points[0], chevron.points[1], chevron.points[2])
                // The tip is ahead of both arms, and the arms sit either side
                // of the line, the same distance out.
                XCTAssertGreaterThan((tip.x - left.x) * forward, 0)
                XCTAssertGreaterThan((tip.x - right.x) * forward, 0)
                XCTAssertEqual(left.y - tip.y, tip.y - right.y, accuracy: 1e-6)
                XCTAssertNotEqual(left.y, right.y)
            }
        }
    }

    func testChevronsAreEvenlySpacedAndClearOfBothEnds() {
        let scale = 10.0
        let chevrons = RouteArrows.chevrons(along: east, in: everything(scale), style: .driving)
        let tips = chevrons.map { $0.points[1].x }
        let gaps = zip(tips.dropFirst(), tips).map { $0 - $1 }
        // 72 pt rounded down to a power of two in map points: 720 -> 512.
        for gap in gaps { XCTAssertEqual(gap, 512, accuracy: 1e-6) }

        let start = MKMapPoint(east[0]).x, end = MKMapPoint(east[1]).x
        XCTAssertGreaterThanOrEqual(tips.first! - start, 256)
        XCTAssertGreaterThan(end - tips.last!, 0)
        XCTAssertEqual(chevrons.map(\.id), Array(0..<chevrons.count))
    }

    /// Following the car, the zoom drifts a little; the chevrons must not slide
    /// along the line each time it does.
    func testASmallZoomChangeLeavesTheChevronsWhereTheyWere() {
        let a = RouteArrows.chevrons(along: east, in: everything(10), style: .driving)
        let b = RouteArrows.chevrons(along: east, in: everything(10.5), style: .driving)
        XCTAssertEqual(a.map(\.id), b.map(\.id))
        // The chevron's centre, halfway between an arm and the tip on a line
        // heading due east; its size follows the zoom, its place does not.
        func centre(_ c: RouteArrows.Chevron) -> Double { (c.points[0].x + c.points[1].x) / 2 }
        for (x, y) in zip(a, b) {
            XCTAssertEqual(centre(x), centre(y), accuracy: 1e-6)
        }
    }

    /// Off screen is not drawn, and what is drawn keeps the id it would have
    /// had with the whole line in view, so panning does not reshuffle them.
    func testOnlyVisibleChevronsAreDrawnUnderTheirOwnIds() {
        let all = RouteArrows.chevrons(along: east, in: everything(10), style: .driving)
        let start = MKMapPoint(east[0]), end = MKMapPoint(east[1])
        let middle = MKMapRect(x: start.x + (end.x - start.x) * 0.4, y: start.y - 1_000,
                               width: (end.x - start.x) * 0.2, height: 2_000)
        let some = RouteArrows.chevrons(along: east,
                                        in: RouteArrows.Frame(scale: 10, visible: middle),
                                        style: .driving)
        XCTAssertFalse(some.isEmpty)
        XCTAssertLessThan(some.count, all.count / 2)
        let byId = Dictionary(uniqueKeysWithValues: all.map { ($0.id, $0.points[1]) })
        for chevron in some {
            XCTAssertEqual(byId[chevron.id]?.x ?? .nan, chevron.points[1].x, accuracy: 1e-6)
        }
    }

    /// A line split into many short segments draws the same chevrons as the
    /// straight line it traces.
    func testSegmentBoundariesDoNotMoveTheChevrons() {
        let steps = 37
        let split = (0...steps).map { i in
            CLLocationCoordinate2D(latitude: 42.4,
                                   longitude: -71.40 + 0.06 * Double(i) / Double(steps))
        }
        let a = RouteArrows.chevrons(along: east, in: everything(10), style: .driving)
        let b = RouteArrows.chevrons(along: split, in: everything(10), style: .driving)
        XCTAssertEqual(a.map(\.id), b.map(\.id))
        for (x, y) in zip(a, b) {
            XCTAssertEqual(x.points[1].x, y.points[1].x, accuracy: 0.01)
        }
    }

    func testZoomedFarOutTheCountIsCapped() {
        let chevrons = RouteArrows.chevrons(along: east, in: everything(0.001), style: .driving)
        XCTAssertEqual(chevrons.count, RouteArrows.maxChevrons)
    }

    func testNothingToDrawWithoutALine() {
        XCTAssertTrue(RouteArrows.chevrons(along: [east[0]], in: everything(10), style: .driving).isEmpty)
        XCTAssertTrue(RouteArrows.chevrons(along: [], in: everything(10), style: .driving).isEmpty)
    }
}
