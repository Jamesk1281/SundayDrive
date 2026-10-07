import CoreLocation
import Foundation

/// The network layer: turns a (start, end, preference) into routes, or a (start,
/// distance) into a scenic loop, by calling the backend. It's an `enum` with only
/// static members because it holds no state — it's just a namespace.
enum RouteService {

    /// Where the backend lives, in order of precedence:
    ///
    ///   1. `SUNDAYDRIVE_API` in the environment — for developing against a
    ///      local server. Add it to the Run action in Xcode's scheme editor.
    ///      The older `VICTORYLAP_API` and `SCENIC_API` are still read as
    ///      fallbacks; see below.
    ///   2. `SundayDriveAPIBaseURL` from Info.plist — the deployed backend,
    ///      baked into the bundle at build time (set in `ios/project.yml`).
    ///   3. localhost, as a last resort.
    ///
    /// The Info.plist entry is what makes the app usable away from a Mac. An
    /// environment variable only exists when *Xcode* launches the process, so
    /// tapping the icon — or iOS relaunching the app after jettisoning it
    /// mid-drive — starts it with no environment at all. With only the env var,
    /// that silently fell back to localhost, i.e. the phone itself, and every
    /// request failed at the worst possible moment.
    ///
    /// `VICTORYLAP_API` and `SCENIC_API` are still honoured after
    /// `SUNDAYDRIVE_API`, for one release: the variable is set by hand in
    /// scheme editors and in every documented command written before the
    /// renames, and the failure it would otherwise cause is silent — the app
    /// quietly talks to localhost instead of saying the variable was ignored.
    static let baseURL: String = {
        let env = ProcessInfo.processInfo.environment
        if let override = env["SUNDAYDRIVE_API"] ?? env["VICTORYLAP_API"]
                            ?? env["SCENIC_API"],
           !override.isEmpty {
            return override
        }
        if let baked = Bundle.main.object(forInfoDictionaryKey: "SundayDriveAPIBaseURL") as? String,
           !baked.isEmpty {
            return baked
        }
        return "http://127.0.0.1:5057"
    }()

    /// Why a request didn't produce a route, in the words the driver sees.
    ///
    /// Four cases because they call for four different things from whoever is
    /// reading them, and telling them apart is the whole point: retry, wait,
    /// check the phone, or move the pin. A driver who was shown `HTTP 530` —
    /// which is what a Cloudflare tunnel with nothing behind it answers, and
    /// what this used to surface verbatim — could act on none of them.
    enum ServiceError: LocalizedError {
        /// The backend answered with its own `{"error": ...}`. Passed through
        /// untouched: these are written for the driver ("point is outside the
        /// covered road network", "no route found between those points") and
        /// say the one thing a generic message can't, which is what to change.
        case server(String)
        /// Something answered, but not with anything this app can read — a
        /// 502/503/530, or the HTML page a tunnel or a proxy serves when the
        /// backend behind it is down. The status is worth carrying for a bug
        /// report and worth nothing to the driver, so it goes in a parenthesis.
        case unreachable(Int)
        /// The request never reached a server at all. Different advice, so a
        /// different case: nothing about the routing service will fix it.
        case offline
        /// A 200 whose body didn't decode.
        case badResponse

        var errorDescription: String? {
            switch self {
            case let .server(message): return message
            case let .unreachable(status):
                return "The routing service isn't reachable right now. "
                    + "Try again in a moment. (HTTP \(status))"
            case .offline:
                return "No connection to the routing service. Check your network."
            // A decode failure otherwise surfaces as Foundation's "The data
            // couldn't be read because it isn't in the correct format", which
            // tells a driver nothing about what to do.
            case .badResponse: return "The routing server sent something unreadable."
            }
        }
    }

    /// Requests time out well inside a drive's patience.
    ///
    /// `URLSession.shared` waits 60 seconds, and mid-drive that is the worst of
    /// both worlds: `NavigationModel` holds `isRerouting` for the whole minute,
    /// which both pins "Rerouting…" on the banner and blocks every retry — the
    /// 8-second reroute cooldown cannot fire while a request is still in flight.
    /// Failing fast and retrying is what recovers a drive on a patchy signal.
    private static let session: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 20
        // Never park a request waiting for the network to come back: the driver
        // has moved on and the answer would be for where they used to be.
        configuration.waitsForConnectivity = false
        return URLSession(configuration: configuration)
    }()

    /// The `heading` query value: one decimal place, folded into [0, 360).
    ///
    /// Rounded first and folded second, because it is the *rounding* that leaves
    /// the range. `CLLocation.course` is [0, 360), so a driver headed due north
    /// can report 359.97 — which `%.1f` renders as "360.0", and both
    /// `_parse_heading` and `Router.snap` take a half-open 0..<360 and drop it.
    /// The reroute then fell back to the nearer graph node, which mid-drive is
    /// as often as not the junction just passed: the turn-the-car-around failure
    /// the `heading` parameter exists to prevent, firing only when heading north.
    ///
    /// Folding before rounding would fix nothing, since 359.97 is already in
    /// range. Extracted so the wrap has a test without a network call.
    static func headingParameter(_ heading: CLLocationDirection) -> String {
        let rounded = (heading * 10).rounded() / 10
        return String(format: "%.1f", rounded.truncatingRemainder(dividingBy: 360))
    }

    /// Request the fastest and scenic routes between two points.
    /// - Parameters:
    ///   - pref: 0 = fastest, 1 = most scenic (overall scenery strength).
    ///   - weights: per-beauty-type weights keyed by `BeautyType.apiName`
    ///     (1.0 = neutral). Sent as `w_<type>` params; omitted types default to
    ///     neutral on the server, so an empty dictionary is the plain behavior.
    ///   - heading: the driver's course over ground, for a reroute taken while
    ///     moving. It decides which end of the current road the route starts
    ///     from, so a replacement doesn't open by turning the car around. Leave
    ///     it nil when planning from a standstill — the server then falls back
    ///     to the nearer end, which is the right answer for a parked car.
    ///   - via: a waypoint the route must pass through. One caller: a driver who
    ///     has come off a *loop*. A loop's destination is its own origin, so a
    ///     plain replacement is the short way home and throws the rest of the
    ///     drive away; pinning through the loop's far point makes it a rejoin.
    ///     Note the server ignores `heading` when `via` is set.
    ///   - declinedUTurn: the driver has just left a route that turned them
    ///     around without taking it. The server then keeps the replacement
    ///     going on ahead where there is a reasonable way to, so a driver is
    ///     told to turn around at most once per departure. It needs `heading`
    ///     to know which way "ahead" is, and is ignored with `via`.
    ///     docs/reroute-uturn.md.
    static func route(
        from start: CLLocationCoordinate2D,
        to end: CLLocationCoordinate2D,
        via: CLLocationCoordinate2D? = nil,
        pref: Double,
        weights: [String: Double] = [:],
        heading: CLLocationDirection? = nil,
        declinedUTurn: Bool = false
    ) async throws -> RouteResponse {
        try await send(routeRequest(from: start, to: end, via: via, pref: pref,
                                    weights: weights, heading: heading,
                                    declinedUTurn: declinedUTurn))
    }

    /// The request `route(...)` sends, built without sending it so the one
    /// property this app promises about it — no coordinate in the URL — has a
    /// test. `base` is only for tests and must otherwise stay the default.
    static func routeRequest(
        from start: CLLocationCoordinate2D,
        to end: CLLocationCoordinate2D,
        via: CLLocationCoordinate2D? = nil,
        pref: Double,
        weights: [String: Double] = [:],
        heading: CLLocationDirection? = nil,
        declinedUTurn: Bool = false,
        base: String = baseURL
    ) -> URLRequest {
        // The body: from=lat,lon&to=lat,lon&pref=0.50&w_coast=...
        formRequest("\(base)/api/route", [
            URLQueryItem(name: "from", value: "\(start.latitude),\(start.longitude)"),
            URLQueryItem(name: "to", value: "\(end.latitude),\(end.longitude)"),
            URLQueryItem(name: "pref", value: String(format: "%.2f", pref)),
        ] + weights.map { type, weight in
            URLQueryItem(name: "w_\(type)", value: String(format: "%.2f", weight))
        } + (heading.map {
            [URLQueryItem(name: "heading", value: headingParameter($0))]
        } ?? []) + (via.map {
            [URLQueryItem(name: "via", value: "\($0.latitude),\($0.longitude)")]
        } ?? []) + (declinedUTurn
            ? [URLQueryItem(name: "declined_uturn", value: "1")] : []))
    }

    /// Request one scenic loop from a start point, of about `km`.
    ///
    /// The loop feature's whole job is choosing where to go, so there is no
    /// destination to pass — only a length. See docs/loop-routes-design.md.
    ///
    /// - Parameters:
    ///   - km: the distance slider, in kilometers. The server clamps it to its
    ///     own range and reports what it settled on in `meta.target_km`, so the
    ///     UI should read the target back rather than assume it was honoured.
    ///   - sector: which compass direction to head off in — what the compass
    ///     on the loop panel sets. Pass nil and the server picks the
    ///     best-scoring direction. Only the sectors named in a previous
    ///     response's `alternatives` are worth asking for; the others have no
    ///     loop in them and would be rejected.
    ///   - pref: overall scenery strength. Defaults to full, and the loop tab
    ///     should leave it there: with the length already pinned by the slider,
    ///     pref has little left to trade, its middle range is measurably not
    ///     monotone for loops, and it is the one parameter that throws away the
    ///     server's cached work — 1,125 ms against 650 ms.
    ///   - weights: per-beauty-type weights, exactly as `route(...)` takes them,
    ///     so the tune screen shapes a loop the same way it shapes a route.
    ///
    /// Expect roughly 1.2 s for the first loop from a given start and 0.65 s for
    /// each one after that, because the server caches two full-graph searches per
    /// start. Changing only the distance keeps that cache; changing `pref` does
    /// not.
    static func loop(
        from start: CLLocationCoordinate2D,
        km: Double,
        sector: String? = nil,
        pref: Double = 1.0,
        weights: [String: Double] = [:]
    ) async throws -> LoopResponse {
        try await send(loopRequest(from: start, km: km, sector: sector,
                                   pref: pref, weights: weights))
    }

    /// The request `loop(...)` sends; see `routeRequest(...)`.
    static func loopRequest(
        from start: CLLocationCoordinate2D,
        km: Double,
        sector: String? = nil,
        pref: Double = 1.0,
        weights: [String: Double] = [:],
        base: String = baseURL
    ) -> URLRequest {
        formRequest("\(base)/api/loop", [
            URLQueryItem(name: "from", value: "\(start.latitude),\(start.longitude)"),
            URLQueryItem(name: "km", value: String(format: "%.1f", km)),
            URLQueryItem(name: "pref", value: String(format: "%.2f", pref)),
        ] + weights.map { type, weight in
            URLQueryItem(name: "w_\(type)", value: String(format: "%.2f", weight))
        } + (sector.map { [URLQueryItem(name: "sector", value: $0)] } ?? []))
    }

    /// A POST carrying `items` as a form body, and nothing on the URL.
    ///
    /// The parameters are the driver's position and destination, and the API
    /// sits behind a proxy that terminates TLS: whatever is in a URL is in that
    /// proxy's access log by default, so they travel in the body instead.
    /// Same keys and value formats the query string carried, which is why the
    /// server's parsing did not change. See
    /// docs/coordinates-out-of-the-url.md.
    ///
    /// Setting POST is not the fix; leaving the query off the URL is. The server
    /// reads only the body on a POST, so a request that kept both would fail
    /// there rather than quietly working, and `RouteServiceRequestTests` checks
    /// the URL directly.
    static func formRequest(_ endpoint: String, _ items: [URLQueryItem]) -> URLRequest {
        var request = URLRequest(url: URL(string: endpoint)!)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded",
                         forHTTPHeaderField: "Content-Type")
        var body = URLComponents()
        body.queryItems = items
        // `URLComponents` leaves "+" alone, which is right in a query and wrong
        // in a form body, where it decodes as a space. Nothing sent today holds
        // one, so this only keeps that true if something ever does.
        request.httpBody = body.percentEncodedQuery?
            .replacingOccurrences(of: "+", with: "%2B")
            .data(using: .utf8)
        return request
    }

    /// One request, decoded — with every way it can fail turned into a
    /// `ServiceError` whose text is worth showing a driver.
    ///
    /// Shared because `route` and `loop` carried the same status-check block
    /// verbatim, and it was wrong in both.
    private static func send<T: Decodable>(_ request: URLRequest) async throws -> T {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch is URLError {
            // Thrown before any status code exists, so nothing answered.
            throw ServiceError.offline
        }

        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            // The backend's own message whenever there is one to lift. A rate
            // limiter or a tunnel answers in HTML, not our JSON shape, and that
            // is the case the status code alone used to leak into the sheet.
            if let message = try? JSONDecoder().decode([String: String].self, from: data)["error"] {
                throw ServiceError.server(message)
            }
            throw ServiceError.unreachable(http.statusCode)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw ServiceError.badResponse
        }
    }
}
