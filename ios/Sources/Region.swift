import MapKit

extension MKCoordinateRegion {
    /// The whole state of Massachusetts.
    ///
    /// The fallback "roughly where the user is" box, used for the initial map
    /// camera and as the search bias until we have something better. When the
    /// app expands beyond MA, this is the single place to widen.
    static let massachusetts = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 42.15, longitude: -71.8),
        span: MKCoordinateSpan(latitudeDelta: 2.6, longitudeDelta: 2.6)
    )

    /// All six states the app serves — **the opening map camera, and nothing
    /// else.**
    ///
    /// The camera and the search bias want different boxes, and conflating them
    /// is why this was a single constant. The camera answers "where am I, and
    /// does this app cover me?", and the honest answer is New England, not one
    /// state of six (`roadmap.md`). The *bias* must stay tight for the reason
    /// `around(_:)` records below: completions rank by distance from the box's
    /// centre, so widening it is how "main street" starts offering a main
    /// street four towns away.
    static let newEngland = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 43.6, longitude: -71.3),
        span: MKCoordinateSpan(latitudeDelta: 6.4, longitudeDelta: 6.4)
    )

    /// A box roughly `meters` across, centered on a point.
    ///
    /// Search results are ranked by distance from the bias region's center, and
    /// the statewide box centers on Oxford — 40 miles from Boston. Biasing to
    /// where the user actually is (or is looking on the map) is what stops
    /// "main street" offering a main street four towns away.
    static func around(_ center: CLLocationCoordinate2D,
                       meters: CLLocationDistance = 30_000) -> MKCoordinateRegion {
        MKCoordinateRegion(center: center, latitudinalMeters: meters, longitudinalMeters: meters)
    }
}
