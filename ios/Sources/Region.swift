import MapKit

extension MKCoordinateRegion {
    /// The 48 contiguous states — **the opening map camera, and nothing
    /// else.**
    ///
    /// The camera answers "where am I, and does this app cover me?". Before
    /// the phone has a fix, the honest answer is the whole covered area; once
    /// the launch check finds the phone inside it, the camera moves to
    /// `home(around:)` (`PlanningView`). The search bias wants a different
    /// box, for the reason `around(_:)` records below.
    ///
    /// **Width-limited on every phone, so the centre's latitude is what places
    /// it.** On the map the 48 states are about twice as wide as they are
    /// tall, and the 306 pt home card is wider than that on no phone. MapKit
    /// therefore fits the longitude span edge to edge, and the latitude span
    /// only has to be no taller than the card shows. Centred on the states'
    /// own middle (37.6), the first try put Mexico City in the bottom of the
    /// card and the 49th parallel under the 17 Pro Max's 62 pt status bar.
    /// Centred at 40.95, measured on the simulator on 2026-10-18: on the
    /// 17 Pro Max the 49th parallel is at y = 69 and Key West at about 296 of
    /// 305, right of Apple's logo; on an iPhone SE the parallel is at y = 80.
    /// The 60.4° width leaves Cape Flattery and Lubec just inside the edges.
    static let coverage = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 40.95, longitude: -95.86),
        span: MKCoordinateSpan(latitudeDelta: 24.0, longitudeDelta: 60.4)
    )

    /// The bounding box of the covered area plus a tenth of a degree all
    /// round — **for search, and never for deciding what is in.**
    ///
    /// What a search falls back to once its bias has left the covered area
    /// (see `Coverage.searchBias`), the only region a typed search is ever
    /// restricted to, and the bias before the map has reported a camera. Built
    /// from the generated outline's own bounds, so it takes in every vertex of
    /// it, Key West and the Northwest Angle included. It also takes in Toronto,
    /// Vancouver and Tijuana, which is why `Coverage.contains` decides
    /// containment and this does not.
    static let coverageEnvelope: MKCoordinateRegion = {
        let margin = 0.1
        return MKCoordinateRegion(
            center: CLLocationCoordinate2D(
                latitude: (CoverageBoundary.south + CoverageBoundary.north) / 2,
                longitude: (CoverageBoundary.west + CoverageBoundary.east) / 2),
            span: MKCoordinateSpan(
                latitudeDelta: CoverageBoundary.north - CoverageBoundary.south + 2 * margin,
                longitudeDelta: CoverageBoundary.east - CoverageBoundary.west + 2 * margin))
    }()

    /// Where the home map goes once the launch check has a fix inside the
    /// covered area: a box about 300 km across, centred on the phone.
    ///
    /// Big enough that an approximate fix, which can be kilometres out, still
    /// lands the phone well inside it, and that a day's drive from home is on
    /// the map; small enough that the search bias, which follows the camera,
    /// ranks around the user rather than from the middle of the country.
    static func home(around center: CLLocationCoordinate2D) -> MKCoordinateRegion {
        around(center, meters: 300_000)
    }

    /// A box roughly `meters` across, centered on a point.
    ///
    /// Search results are ranked by distance from the bias region's center,
    /// and a box much bigger than the user's surroundings centres somewhere
    /// they are not. Biasing to where the user actually is (or is looking on
    /// the map) is what stops "main street" offering a main street four towns
    /// away.
    static func around(_ center: CLLocationCoordinate2D,
                       meters: CLLocationDistance = 30_000) -> MKCoordinateRegion {
        MKCoordinateRegion(center: center, latitudinalMeters: meters, longitudinalMeters: meters)
    }
}
