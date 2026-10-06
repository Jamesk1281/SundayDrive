import CoreLocation
import MapKit
import Observation

/// How loops are fetched. Tests substitute a stub, the same seam and for the
/// same reason as `RouteFetcher`: every interesting behaviour here — which
/// direction is asked for, which of two overlapping requests wins, what survives
/// a failed compass tap — is a sequence of requests, and a test that needs a live
/// backend and a real Massachusetts graph to see it does not get written.
typealias LoopFetcher = (CLLocationCoordinate2D, Double, String?,
                         [String: Double]) async throws -> LoopResponse

/// State for the loop tab: one start point, one distance, and the loop that came
/// back. The driver picks the compass direction; the server picks the first.
///
/// Separate from `RouteModel` because it shares almost nothing with it — no
/// destination, no swap, no fastest-versus-scenic comparison — but it does *not*
/// own a `LocationManager`. It takes `RouteModel`'s, so location permission is
/// asked for once for the whole app and there is only ever one stream of fixes.
/// Live navigation stays with `RouteModel` for the same reason: there is one
/// drive at a time whichever tab planned it.
@Observable
@MainActor
final class LoopModel {
    private let locationManager: LocationManager

    /// How "My Location" gets its fix. Tests substitute one, the way they
    /// substitute `fetchLoop`.
    var locate: () async -> CLLocation?

    init(locationManager: LocationManager) {
        self.locationManager = locationManager
        locate = { await locationManager.currentLocation() }
    }

    var start: CLLocationCoordinate2D?
    /// Text in the start field, kept in sync with the resolved place.
    var startQuery = ""

    /// The distance slider, in kilometers. 40 km is a bit over an hour's drive,
    /// which is what most people mean by "go for a drive".
    ///
    /// The bounds match the server's clamp (`MAX_TARGET_KM` in
    /// `pipeline/looper.py`). They are not graph limits — the longest available
    /// loop from a Massachusetts start is over 500 km — they are the range where
    /// the answer is a drive rather than an expedition: 400 km is a full day.
    /// Restored from the last session, so "Loop" on the home screen is one tap
    /// to a finished drive rather than one tap to a form.
    ///
    /// Written back in `fetch`, when a loop has actually come back at this
    /// length — not from a `didSet`. Two reasons: what is worth remembering is
    /// the length the driver *drove*, not every position the slider passed
    /// through under a thumb; and a `didSet` would make every unit test that
    /// touches this property write to the app's real `UserDefaults`, which is
    /// exactly how the home screen came to offer a 6-minute loop after a test
    /// run left `targetKm` at the 5 km minimum.
    var targetKm: Double = UserDefaults.standard.object(forKey: LoopModel.targetKey) as? Double ?? 40
    private static let targetKey = "lastLoopTargetKm"
    static let minKm: Double = 5
    static let maxKm: Double = 400

    /// Minutes per kilometre, for labelling the distance dial in time.
    ///
    /// **Nobody has 48 kilometres; they have an afternoon.** The request still
    /// goes to `/api/loop` in kilometres, because that is what it takes — this
    /// only changes what the dial *says*. What keeps the label honest is that
    /// the factor is measured rather than assumed: every response carries its
    /// real `minutes` and `km`, so each loop that comes back re-fits the
    /// estimate for the next one, on this driver's roads rather than on an
    /// average of everybody's.
    ///
    /// 1.2 is the seed, from a 40 km loop taking a little under 50 minutes. It
    /// is replaced by a measurement the first time a loop lands.
    private(set) var minutesPerKm: Double = 1.2

    /// What a given distance is likely to take, in minutes. An estimate, and
    /// labelled as one ("about 1 hr 30") — the loop's own `minutes` replaces it
    /// the moment there is a real answer.
    func estimatedMinutes(forKm km: Double) -> Double { km * minutesPerKm }

    var response: LoopResponse?
    var isLoading = false
    var errorText: String?

    /// The direction the driver just tapped, while its loop is on the way, so
    /// the compass can show which point is working without the whole panel
    /// flashing its loading state.
    var pendingSector: String?

    /// The last direction the driver chose on the compass, or tapped while it
    /// was on screen. Set only once a loop that way has come back, so it never
    /// names a direction the map is not showing. Carried into every later
    /// request — a new length or a new start — so dragging the
    /// slider does not swing a westward drive round to whatever the server
    /// would have picked. Nil until they choose, which leaves it to the server.
    private(set) var preferredSector: String?

    /// Ticks up per request so a slow response that lands after a newer one has
    /// started can be recognised as stale and dropped. Same reason
    /// `RouteModel.requestGeneration` exists: dragging the distance slider and
    /// then tapping the compass is two requests in flight, and the older one
    /// must not win.
    private var requestGeneration = 0

    /// How loops are fetched. Tests substitute a stub.
    var fetchLoop: LoopFetcher = { start, km, sector, weights in
        try await RouteService.loop(from: start, km: km, sector: sector,
                                    weights: weights)
    }

    /// True once there is something on screen to drive.
    var hasLoop: Bool { response != nil }

    /// True while the user is standing still waiting for a location fix.
    var isLocatingUser = false

    // MARK: - Choosing where to start

    /// Resolve a free-text query to a place and set it as the start.
    func search(_ query: String) async {
        let trimmed = query.trimmingCharacters(in: .whitespaces)
        guard trimmed.count >= 3 else { return }
        let request = MKLocalSearch.Request()
        request.naturalLanguageQuery = trimmed
        request.rank(around: searchRegion)
        await resolve(request, label: trimmed)
    }

    /// Resolve a tapped autocomplete suggestion. The suggestion is only a label,
    /// so it still needs a search to get a coordinate.
    func choose(_ completion: MKLocalSearchCompletion) async {
        await resolve(MKLocalSearch.Request(completion: completion),
                      label: completion.title)
    }

    /// Where autocomplete results are ranked around — the map's camera, same as
    /// the directions tab. Without it every search is answered from the middle of
    /// the state.
    var searchRegion: MKCoordinateRegion = .massachusetts

    /// The first result in New England, never simply the first — see
    /// `RouteModel.resolve`.
    private func resolve(_ request: MKLocalSearch.Request, label: String) async {
        do {
            let result = try await MKLocalSearch(request: request).start()
            guard !result.mapItems.isEmpty else {
                errorText = "No match for “\(label)”"
                return
            }
            guard let match = NewEngland.firstInside(result.mapItems) else {
                errorText = NewEngland.notInNewEngland(label)
                return
            }
            start = match.placemark.coordinate
            startQuery = PlaceNaming.displayName(for: match, fallback: label)
            errorText = nil
            await generate()
        } catch {
            errorText = "Couldn’t find “\(label)”"
        }
    }

    /// Start the loop from wherever the user is standing — the common case for
    /// this tab, since a loop starts and ends at home.
    ///
    /// Takes a fresh fix rather than the cached one for the same reason
    /// `RouteModel.useMyLocation` does: a Wi-Fi-derived location is often a
    /// street or two out, and here that error decides which roads are within
    /// reach. And, as there, a fix outside New England stops here with a
    /// message, and no request is made.
    func useMyLocation() async {
        isLocatingUser = true
        defer { isLocatingUser = false }

        guard let fix = await locate() else {
            errorText = locationManager.authorization == .denied
                    || locationManager.authorization == .restricted
                ? "Location access is off — allow it in Settings to start from here."
                : "Couldn’t get a location fix. Try again in a moment."
            return
        }
        guard locationManager.noteRegion(of: fix) == .inside else {
            errorText = NewEngland.outsideHere
            return
        }
        start = fix.coordinate
        startQuery = PlaceNaming.myLocation
        searchRegion = .around(fix.coordinate)
        errorText = nil
        await generate()
        // After the loop, not before: the geocode is a courtesy and the drive
        // is the point, so it must not stand between the tap and the map.
        await nameCurrentLocation(fix)
    }

    /// Put a street name on the "My Location" start once reverse geocoding
    /// answers, the way the directions tab does — see `PlaceNaming`.
    ///
    /// The guards are not optional. This suspends for as long as the geocoder
    /// takes, and in that time the user can have typed an address, tapped
    /// "My Location" again from somewhere else, or cleared the field; writing
    /// the answer back unconditionally would label whatever is there now with
    /// where they used to be.
    private func nameCurrentLocation(_ fix: CLLocation) async {
        guard let label = await PlaceNaming.currentLocationLabel(for: fix) else { return }
        guard startQuery == PlaceNaming.myLocation,
              start?.matches(fix.coordinate) == true else { return }
        startQuery = label
    }

    func clear() {
        // A request still in flight must not put a loop back under an empty
        // start, so it is made stale; and since a stale request returns
        // without resetting anything, its busy flags are reset here.
        requestGeneration += 1
        start = nil
        startQuery = ""
        response = nil
        errorText = nil
        preferredSector = nil
        pendingSector = nil
        isLoading = false
    }

    // MARK: - Asking for loops

    /// Ask for a loop in the direction the driver last chose, or the server's
    /// choice if they have not. Used for the first loop and after the distance
    /// or start changes.
    func generate() async {
        await fetch(sector: preferredSector, regenerating: false)
    }

    /// Ask for a loop heading off in `sector`, as tapped on the compass.
    ///
    /// Only a direction the last response listed in `alternatives` is asked
    /// for: those are the ones that actually hold a loop of this length, and
    /// the compass greys out the rest — a coastal start has fewer than eight,
    /// and some of the missing ones are the ocean. Tapping the direction already
    /// on screen asks for nothing, but keeps it as the choice.
    ///
    /// Ignored while any loop is on its way: the directions on the compass
    /// belong to the loop on screen, and a new length or start being fetched
    /// may not have them.
    func head(_ sector: String) async {
        guard let response, start != nil, !isLoading, pendingSector == nil
        else { return }
        if sector == response.meta.sector {
            preferredSector = sector
            return
        }
        guard availableSectors.contains(sector) else { return }
        pendingSector = sector
        await fetch(sector: sector, regenerating: true)
        if self.response?.meta.sector == sector { preferredSector = sector }
    }

    /// The directions that hold a loop of this length from this start.
    var availableSectors: Set<String> { Set(response?.alternatives.map(\.sector) ?? []) }

    /// How many directions the driver can choose between from here. Shown so
    /// the compass does not imply eight choices when the geography offers five.
    var directionCount: Int { response?.alternatives.count ?? 0 }

    private func fetch(sector: String?, regenerating: Bool) async {
        guard let origin = start else { return }

        requestGeneration += 1
        let generation = requestGeneration
        if !regenerating { isLoading = true }
        errorText = nil

        do {
            let result: LoopResponse
            do {
                result = try await fetchLoop(origin, targetKm, sector, weights)
            } catch RouteService.ServiceError.server(_) where sector != nil && !regenerating {
                // The remembered direction has nothing at this length or from
                // this start — the server's own refusal, not a dead network,
                // which a second request would only wait on twice. Better the server's choice than an error and an
                // empty map for a preference the driver set at another length.
                guard generation == requestGeneration else { return }
                result = try await fetchLoop(origin, targetKm, nil, weights)
            }
            guard generation == requestGeneration else { return }
            response = result
            // Re-fit the time estimate on what the router actually returned.
            // Guarded against a degenerate loop so one odd answer cannot make
            // the dial's label nonsense for the rest of the session.
            if result.meta.km > 1, result.meta.minutes > 1 {
                minutesPerKm = min(3.0, max(0.6, result.meta.minutes / result.meta.km))
            }
            // The server clamps the distance to its own range; show what it
            // actually used rather than what was asked for, so the slider and
            // the result never disagree.
            targetKm = result.meta.target_km
            UserDefaults.standard.set(targetKm, forKey: Self.targetKey)
        } catch {
            guard generation == requestGeneration else { return }
            // A failed compass tap leaves the loop that is already on screen
            // alone. Blanking the map because one direction had nothing in it
            // would throw away a perfectly good drive.
            if !regenerating { response = nil }
            errorText = error.localizedDescription
        }
        isLoading = false
        pendingSector = nil
    }

    /// Per-beauty-type weights, so the tune screen shapes a loop the same way it
    /// shapes a route. Set by whoever owns this model from the shared value —
    /// `pref` is deliberately absent, because the loop tab pins it at full
    /// scenery (see `RouteService.loop`).
    var weights: [String: Double] = [:]
}
