import MapKit
import SwiftUI

/// Small chevrons along a route line, pointing the way it is driven.
///
/// A line on a map says where, not which way, and a loop is the case where
/// that matters: the same ring driven the other way round is a different
/// drive, with every turn on the other side. On the driving screen they also
/// answer "am I going the right way" on the stretch behind the car as well as
/// the one ahead, so they run the whole length of the line.
///
/// **Drawn as map geometry, not annotations.** An annotation stays upright on
/// screen, so on a heading-up map every arrow would need counter-rotating by
/// the camera's heading, once per frame, and would lag the map while it turns.
/// A chevron made of coordinates turns and tilts with the road for free. The
/// cost is that its size is in map units, so it is recomputed for the zoom
/// whenever the camera settles (`Frame`); in between, a pinch scales the
/// chevrons with the line they sit in, which is what it does to the line too.
///
/// Everything is in `MKMapPoint` space. Mercator is conformal, so a chevron
/// built square there is square on screen, and a spacing measured there is a
/// spacing in screen points at any latitude.
enum RouteArrows {

    /// What the camera is showing, as much as the chevrons need of it.
    struct Frame {
        /// Map points per screen point at the centre of the view.
        var scale: Double
        /// What is on screen, in map points. Chevrons outside it are not drawn.
        var visible: MKMapRect

        /// Measure the camera through the map's own projection, rather than
        /// from `context.rect`: on a map turned to the car's heading that rect
        /// is the bounding box of a rotated screen, and up to 1.4 times too
        /// big, so the chevrons would grow and shrink as the car turned.
        @MainActor
        init?(proxy: MapProxy, context: MapCameraUpdateContext) {
            let step: CGFloat = 100
            guard let mid = proxy.convert(context.camera.centerCoordinate, to: .local),
                  let aside = proxy.convert(CGPoint(x: mid.x + step, y: mid.y), from: .local)
            else { return nil }
            let a = MKMapPoint(context.camera.centerCoordinate), b = MKMapPoint(aside)
            let scale = hypot(b.x - a.x, b.y - a.y) / Double(step)
            guard scale > 0, scale.isFinite else { return nil }
            self.init(scale: scale, visible: context.rect)
        }

        init(scale: Double, visible: MKMapRect) {
            self.scale = scale
            self.visible = visible
        }
    }

    /// How a chevron is drawn, in screen points.
    struct Style {
        /// Between one chevron and the next.
        var spacing: Double = 72
        /// From the chevron's centre to its tip, and to each end of its arms.
        /// With the stroke this keeps the whole mark inside the line it sits on.
        var reach: Double
        var lineWidth: CGFloat

        /// The 8 pt line on the driving screen.
        static let driving = Style(reach: 2.6, lineWidth: 2.4)
        /// The 6 pt lines on the planning card.
        static let planning = Style(reach: 1.9, lineWidth: 1.9)
    }

    /// One chevron: arm, tip, arm. `id` is its place along the line, so the
    /// same chevron keeps its identity while the map pans.
    struct Chevron: Identifiable {
        let id: Int
        let points: [MKMapPoint]
        var coordinates: [CLLocationCoordinate2D] { points.map(\.coordinate) }
    }

    /// Never more than this many on screen at once, whatever the zoom.
    static let maxChevrons = 160

    /// The chevrons for `line` in `frame`.
    ///
    /// They sit at `spacing * (k + ½)` along the line, so none lands on either
    /// end, where the start and destination pins are. The spacing is rounded
    /// down to a power of two in map points: following the car, the zoom
    /// drifts by small amounts, and an exact spacing would slide every chevron
    /// along the line each time it did. Rounded, they hold still until the
    /// zoom has changed by half or double.
    static func chevrons(along line: [CLLocationCoordinate2D],
                         in frame: Frame,
                         style: Style) -> [Chevron] {
        guard line.count >= 2, frame.scale > 0, frame.scale.isFinite else { return [] }
        let points = line.map(MKMapPoint.init)
        let spacing = exp2((log2(style.spacing * frame.scale)).rounded(.down))
        let reach = style.reach * frame.scale

        // A chevron half on screen is still drawn, and so is one a little
        // beyond the edge, so they don't pop in at the edge while panning.
        let margin = style.spacing * frame.scale
        let window = frame.visible.insetBy(dx: -margin, dy: -margin)

        var result: [Chevron] = []
        var along = 0.0                 // map points of line before `points[i]`
        var k = 0                       // the next chevron to place
        for i in 1..<points.count {
            let a = points[i - 1], b = points[i]
            let dx = b.x - a.x, dy = b.y - a.y
            let length = hypot(dx, dy)
            guard length > 0 else { continue }
            let segment = MKMapRect(x: min(a.x, b.x), y: min(a.y, b.y),
                                    width: abs(dx), height: abs(dy))
            let end = along + length
            if !window.intersects(segment.insetBy(dx: -reach, dy: -reach)) {
                // Skip the segment, but keep the count, so the chevrons on the
                // next one land where they would have anyway.
                k = max(k, Int((end / spacing - 0.5).rounded(.up)))
                along = end
                continue
            }
            let ux = dx / length, uy = dy / length
            while spacing * (Double(k) + 0.5) < end {
                let at = spacing * (Double(k) + 0.5) - along
                let centre = MKMapPoint(x: a.x + ux * at, y: a.y + uy * at)
                if window.contains(centre) {
                    // Tip forward along the segment, arms back and out to
                    // either side.
                    let tip = MKMapPoint(x: centre.x + ux * reach, y: centre.y + uy * reach)
                    let left = MKMapPoint(x: centre.x - ux * reach - uy * reach,
                                          y: centre.y - uy * reach + ux * reach)
                    let right = MKMapPoint(x: centre.x - ux * reach + uy * reach,
                                           y: centre.y - uy * reach - ux * reach)
                    result.append(Chevron(id: k, points: [left, tip, right]))
                    if result.count >= maxChevrons { return result }
                }
                k += 1
            }
            along = end
        }
        // Too close to the end to clear the destination pin and the line's
        // round cap.
        if let last = result.last, spacing * (Double(last.id) + 0.5) + reach * 2 > along {
            result.removeLast()
        }
        return result
    }
}

/// `RouteArrows` as map content: put it after the line it belongs to.
struct RouteArrowsContent: MapContent {
    let line: [CLLocationCoordinate2D]
    let frame: RouteArrows.Frame?
    let style: RouteArrows.Style

    var body: some MapContent {
        ForEach(frame.map { RouteArrows.chevrons(along: line, in: $0, style: style) } ?? []) { chevron in
            MapPolyline(coordinates: chevron.coordinates)
                .stroke(.white.opacity(0.92),
                        style: StrokeStyle(lineWidth: style.lineWidth,
                                           lineCap: .round, lineJoin: .round))
        }
    }
}
