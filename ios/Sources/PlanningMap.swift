import MapKit
import SwiftUI

/// The planning map — **a card, not a canvas.**
///
/// This is the load-bearing piece of the redesign and the reason the planning
/// sheet is gone. Apple's map logo and legal link are drawn in the bottom-left
/// of whatever view MapKit renders into. The old screen presented `RoutePanel`
/// with `.sheet(isPresented: .constant(true))` over a full-bleed map, and a
/// `.sheet` is a separate presentation layer — the map beneath it cannot lay
/// its attribution out around something it does not know is there. So the logo
/// was covered at *every* detent, which ADPLA Attachment 6 §2.1 forbids and §4
/// makes grounds for revoking MapKit access.
///
/// Bounding the map and starting the page underneath it fixes that by
/// construction: there is no scroll position, no text size and no amount of
/// content that can reach the corner. See `docs/interface-design.md` §2.
struct PlanningMap: View {
    @Bindable var model: RouteModel
    let stage: PlanStage
    @Binding var camera: MapCameraPosition

    var body: some View {
        Map(position: $camera) {
            switch stage {
            case .home:
                // Nothing drawn: the home screen's map answers "where am I",
                // and `UserAnnotation` below is the whole answer.
                MapCircle(center: .init(latitude: 0, longitude: 0), radius: 0)
                    .foregroundStyle(.clear)
            case .directions:
                // The fastest arm under the scenic one, quiet and dashed: it is
                // the reference price, not a route you can choose here.
                if let fastest = model.response?.fastest {
                    MapPolyline(coordinates: fastest.coordinates)
                        .stroke(Color.slate.opacity(0.65),
                                style: StrokeStyle(lineWidth: 3, dash: [6, 6]))
                }
                // A menu option on its way in full is drawn from its
                // simplified line, so the map answers the release at once.
                if let scenic = model.previewLine ?? model.response?.scenic.coordinates {
                    MapPolyline(coordinates: scenic)
                        .stroke(Color.amber, style: StrokeStyle(lineWidth: 6,
                                                                lineCap: .round,
                                                                lineJoin: .round))
                }
                if let start = model.start { endpointDot(start, tint: .startPin, label: "Start") }
                if let end = model.end {
                    Marker(model.endQuery.isEmpty ? "Destination" : model.endQuery,
                           coordinate: end).tint(Color.endPin)
                }
            case .loop:
                if let loop = model.loops.response?.loop {
                    MapPolyline(coordinates: loop.coordinates)
                        .stroke(Color.amber, style: StrokeStyle(lineWidth: 6,
                                                                lineCap: .round,
                                                                lineJoin: .round))
                }
                if let start = model.loops.start {
                    endpointDot(start, tint: .amber, label: "Start and finish")
                }
                if let turnaround = model.loops.response?.meta.turnaroundCoordinate {
                    Marker("Turnaround", systemImage: "arrow.uturn.left",
                           coordinate: turnaround).tint(BeautyType.hue(for: "hills"))
                }
            }
            UserAnnotation()
        }
        .mapControls { MapUserLocationButton() }
        // Rank search results around whatever the user is looking at. Apple's
        // search sorts by distance from this region's center, so without it
        // every search is answered from the middle of the state.
        .onMapCameraChange(frequency: .onEnd) { context in
            model.searchRegion = context.region
            model.loops.searchRegion = context.region
        }
    }

    /// A start pin, as a dot rather than a balloon. A balloon's tip points at
    /// the coordinate and its body covers the street the coordinate is on,
    /// which is the one thing this pin exists to let the driver check.
    private func endpointDot(_ coordinate: CLLocationCoordinate2D,
                             tint: Color, label: String) -> some MapContent {
        Annotation("", coordinate: coordinate, anchor: .center) {
            Circle().fill(.white)
                .frame(width: 17, height: 17)
                .overlay(Circle().fill(tint).frame(width: 12, height: 12))
                .shadow(color: .black.opacity(0.25), radius: 2, y: 1)
                .accessibilityLabel(label)
        }
    }
}

// MARK: - Framing

extension PlanningMap {
    /// A pin on the map, and how far its artwork stands above the coordinate
    /// it marks. The camera has to keep the artwork clear of the status bar,
    /// not just the coordinate.
    struct Pin {
        let coordinate: CLLocationCoordinate2D
        let reach: CGFloat

        /// `endpointDot`: 17 pt across and centred on its coordinate, plus a
        /// point of shadow.
        static func dot(_ coordinate: CLLocationCoordinate2D) -> Pin {
            Pin(coordinate: coordinate, reach: 10)
        }

        /// A `Marker` balloon stands on its coordinate: 31 × 35 pt with its tip
        /// on the point, measured on iOS 26.4.
        static func marker(_ coordinate: CLLocationCoordinate2D) -> Pin {
            Pin(coordinate: coordinate, reach: 35)
        }
    }

    /// What the camera fits on each stage: the line, and every pin the content
    /// builder above draws on it. Here rather than in `PlanningView` so that a
    /// pin added there is not missed here.
    static func framedContent(_ stage: PlanStage,
                              _ model: RouteModel) -> (line: [CLLocationCoordinate2D]?, pins: [Pin]) {
        var pins: [Pin] = []
        switch stage {
        case .home:
            return (nil, [])
        case .directions:
            if let start = model.start { pins.append(.dot(start)) }
            if let end = model.end { pins.append(.marker(end)) }
            return (model.response?.scenic.coordinates, pins)
        case .loop:
            if let start = model.loops.start { pins.append(.dot(start)) }
            if let turnaround = model.loops.response?.meta.turnaroundCoordinate {
                pins.append(.marker(turnaround))
            }
            return (model.loops.response?.loop.coordinates, pins)
        }
    }
}

extension MapCameraPosition {
    /// Fit a line, and the pins drawn on it, into the part of the map card the
    /// driver can see.
    ///
    /// **The card runs under the status bar, and MapKit cannot tell.** The page
    /// ignores the top safe area so the map can run full-bleed, and inside that
    /// region SwiftUI reports a top inset of zero. A plain `.rect` was
    /// therefore fitted to the whole card, and on the short loop card the top
    /// of the route landed under the clock and the Dynamic Island: on a loop
    /// heading south, its start pin. So the fit is done here, in
    /// points, against `topInset`. The line keeps the padding it always had
    /// (12% of its width each side, 22% of its height above and below), now
    /// fitted into the card *below* the strip. Each pin's artwork has to clear
    /// the strip as well, not just its coordinate: a `Marker` stands 35 pt tall,
    /// more than 22% of a loop's height on this card, so a turnaround at the
    /// top of a loop needs room of its own.
    ///
    /// What comes back is the whole card as a rect in map points: the strip,
    /// the route and its padding, and any slack. It has the card's shape, so
    /// MapKit shows exactly that rect, and only if the card has that `card`
    /// size when the camera is applied. That is why `PlanningView.refit` waits
    /// for the card to stop changing height before it moves the camera.
    ///
    /// No size yet (before the first layout) falls back to fitting the whole
    /// card, which is what this did before it knew about the strip.
    static func fitting(_ coordinates: [CLLocationCoordinate2D]?,
                        pins: [PlanningMap.Pin] = [],
                        card: CGSize, topInset: CGFloat) -> MapCameraPosition? {
        guard let coords = coordinates, !coords.isEmpty else { return nil }
        let line = coords.map(MKMapPoint.init)
        var rect = MKMapRect.null
        for point in line + pins.map({ MKMapPoint($0.coordinate) }) {
            rect = rect.union(MKMapRect(x: point.x, y: point.y, width: 0, height: 0))
        }
        // More headroom than sides: the card is wide and short.
        let padded = MKMapRect(x: rect.origin.x - rect.size.width * 0.12,
                               y: rect.origin.y - rect.size.height * 0.22,
                               width: rect.size.width * 1.24,
                               height: rect.size.height * 1.44)

        let width = Double(card.width), height = Double(card.height)
        let strip = min(max(Double(topInset), 0), height)
        let visible = height - strip
        guard width > 0, visible > 0 else { return .rect(padded) }

        // What has to clear the strip, as a map y and the points it needs above
        // that y. The line's own top needs half its 6 pt stroke. A card too
        // short to fit a pin at all cannot honour it, so that pin is dropped
        // rather than shrinking the route to nothing.
        let topOfLine = line.map(\.y).min() ?? padded.minY
        let reaches: [(y: Double, points: Double)] =
            (pins.map { (MKMapPoint($0.coordinate).y, Double($0.reach)) } + [(topOfLine, 3)])
            .filter { $0.points < visible }

        // Map points per screen point: the smallest scale (the closest view)
        // that fits the padded line across the card, into the height below
        // the strip, and with every pin's artwork below the strip too.
        var scale = max(padded.width / width, padded.height / visible)
        for reach in reaches {
            scale = max(scale, (padded.maxY - reach.y) / (visible - reach.points))
        }
        guard scale > 0, scale.isFinite else { return nil }

        // Where the card's top edge may sit, in map y: no lower than keeps the
        // padded bottom on the card, no higher than keeps everything out of
        // the strip. Halfway between shares any slack above and below.
        var highest = padded.minY - strip * scale
        for reach in reaches {
            highest = min(highest, reach.y - (strip + reach.points) * scale)
        }
        let lowest = padded.maxY - height * scale

        return .rect(MKMapRect(x: padded.midX - width * scale / 2,
                               y: (lowest + highest) / 2,
                               width: width * scale,
                               height: height * scale))
    }

    /// Frame a single point — a start with no destination yet, or the user's
    /// own position on the home screen. Seeing the pin land on the right street
    /// is how a bad fix gets caught before pulling away.
    static func around(_ point: CLLocationCoordinate2D, meters: Double = 1_400) -> MapCameraPosition {
        .region(MKCoordinateRegion(center: point,
                                   latitudinalMeters: meters,
                                   longitudinalMeters: meters))
    }
}
