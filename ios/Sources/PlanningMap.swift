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
                if let scenic = model.response?.scenic {
                    MapPolyline(coordinates: scenic.coordinates)
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

extension MapCameraPosition {
    /// Fit a line into the map card.
    ///
    /// Plain padding on all four sides, which it could not be before: the old
    /// `ContentView.frame(_:)` extended the rect *downwards* by
    /// `max(h × 1.4, w × 0.9)` so that MapKit centring the taller rect left the
    /// route in the upper half, clear of the sheet. With the map bounded, there
    /// is nothing to dodge.
    static func fitting(_ coordinates: [CLLocationCoordinate2D]?) -> MapCameraPosition? {
        guard let coords = coordinates, !coords.isEmpty else { return nil }
        var rect = MKMapRect.null
        for coord in coords {
            let point = MKMapPoint(coord)
            rect = rect.union(MKMapRect(x: point.x, y: point.y, width: 0, height: 0))
        }
        // More headroom than sides: the card is wide and short, and the top of
        // a loop is where its turnaround marker sits.
        let padded = MKMapRect(x: rect.origin.x - rect.size.width * 0.12,
                               y: rect.origin.y - rect.size.height * 0.22,
                               width: rect.size.width * 1.24,
                               height: rect.size.height * 1.44)
        return .rect(padded)
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
