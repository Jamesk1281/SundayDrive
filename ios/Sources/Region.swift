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
    ///
    /// **Taller than New England, and centred north of it, on purpose.** The
    /// map card runs up under the status bar, and MapKit fits the box to the
    /// whole 306 pt card without knowing that. Measured on 2026-10-04, the old
    /// box (centre 43.6, -71.3, 6.4° square) put Fort Kent 28 pt *above* the
    /// card on an iPhone SE and a 17 Pro Max alike, and northern New Hampshire
    /// under the Dynamic Island. This one puts the northern tip of Maine
    /// (Estcourt Station, 47.46) at y = 72, 10 pt below the 17 Pro Max's
    /// 62 pt status bar, and Connecticut's southern tip at y = 282, clear of
    /// Apple's logo row. The longitude span only has to be narrower than the
    /// card shows, so the fit stays height-limited on the narrowest phone.
    static let newEngland = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 45.05, longitude: -70.34),
        span: MKCoordinateSpan(latitudeDelta: 9.3, longitudeDelta: 7.6)
    )

    /// The bounding box of New England plus a tenth of a degree all round —
    /// **for search, and never for deciding what is in.**
    ///
    /// What a search falls back to once its bias has left New England (see
    /// `NewEngland.searchBias`), and the only region a typed search is ever
    /// restricted to. Built from the generated outline's own bounds, so it
    /// takes in every vertex of it, Fort Kent and Lubec included. Any box that
    /// does also takes in Montauk, Sherbrooke and Edmundston, which is why
    /// `NewEngland.contains` decides containment and this does not.
    static let newEnglandEnvelope: MKCoordinateRegion = {
        let margin = 0.1
        return MKCoordinateRegion(
            center: CLLocationCoordinate2D(
                latitude: (NewEnglandBoundary.south + NewEnglandBoundary.north) / 2,
                longitude: (NewEnglandBoundary.west + NewEnglandBoundary.east) / 2),
            span: MKCoordinateSpan(
                latitudeDelta: NewEnglandBoundary.north - NewEnglandBoundary.south + 2 * margin,
                longitudeDelta: NewEnglandBoundary.east - NewEnglandBoundary.west + 2 * margin))
    }()

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
