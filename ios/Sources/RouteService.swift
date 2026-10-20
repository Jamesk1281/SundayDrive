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
        /// The backend answered with its own `{"error": ..., "code": ...}`.
        /// These are written for the driver and say the one thing a generic
        /// message can't, which is what to change. See `Refusal` for how the
        /// body is read and which codes get the app's own words.
        case server(Refusal)
        /// Something answered, but not with anything this app can read — a
        /// 502/503/530, or the HTML page a tunnel or a proxy serves when the
        /// backend behind it is down. The status is worth carrying for a bug
        /// report and worth nothing to the driver, so it goes in a parenthesis.
        case unreachable(Int)
        /// The backend's own 503: it was already building a loop, and refused
        /// this one rather than queue it. Its own case, never `.server`,
        /// because `.server` means "the server's answer is no": the loop
        /// page's sector fallback would turn it into a second request at once,
        /// and mid-drive it would climb the reroute backoff. Only `/api/loop`
        /// sends it. docs/loop-lock-contention.md.
        case busy(String)
        /// No answer inside the timeout. Not `.offline`, which blames the
        /// phone, and not `.busy`, which blames the server: a weak signal and
        /// a loaded server both end here, so the words take neither side.
        case timedOut
        /// The request never reached a server at all. Different advice, so a
        /// different case: nothing about the routing service will fix it.
        case offline
        /// A 200 whose body didn't decode.
        case badResponse

        var errorDescription: String? {
            switch self {
            case let .server(refusal): return refusal.sentence
            case let .busy(message): return message
            case let .unreachable(status):
                return "The routing service isn't reachable right now. "
                    + "Try again in a moment. (HTTP \(status))"
            case .timedOut:
                return "The routing service didn't answer in time. "
                    + "Try again in a moment."
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
    ///   - options: ask for the menu of in-between routes the dial turns into
    ///     detents. Planning only: never a reroute, which a driver is waiting
    ///     on. The server may still leave it out (its flag is off, or it is
    ///     busy), and the reply is then today's. docs/route-options.md.
    ///   - leave, rejoin: one menu option's switch points, which make the
    ///     reply's `scenic` that option in full: fastest to `leave`, scenic to
    ///     `rejoin`, fastest home. How an option is fetched when the driver
    ///     settles on it, and how a drive on one is rerouted by legs.
    static func route(
        from start: CLLocationCoordinate2D,
        to end: CLLocationCoordinate2D,
        via: CLLocationCoordinate2D? = nil,
        pref: Double,
        weights: [String: Double] = [:],
        heading: CLLocationDirection? = nil,
        declinedUTurn: Bool = false,
        options: Bool = false,
        leave: SwitchPoint? = nil,
        rejoin: SwitchPoint? = nil
    ) async throws -> RouteResponse {
        try await send(routeRequest(from: start, to: end, via: via, pref: pref,
                                    weights: weights, heading: heading,
                                    declinedUTurn: declinedUTurn, options: options,
                                    leave: leave, rejoin: rejoin))
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
        options: Bool = false,
        leave: SwitchPoint? = nil,
        rejoin: SwitchPoint? = nil,
        base: String = baseURL
    ) -> URLRequest {
        // The body: from=lat,lon&to=lat,lon&pref=0.50&w_coast=...
        var items = [
            URLQueryItem(name: "from", value: "\(start.latitude),\(start.longitude)"),
            URLQueryItem(name: "to", value: "\(end.latitude),\(end.longitude)"),
            URLQueryItem(name: "pref", value: String(format: "%.2f", pref)),
        ] + weights.map { type, weight in
            URLQueryItem(name: "w_\(type)", value: String(format: "%.2f", weight))
        }
        if let heading {
            items.append(URLQueryItem(name: "heading", value: headingParameter(heading)))
        }
        if let via {
            items.append(URLQueryItem(name: "via", value: "\(via.latitude),\(via.longitude)"))
        }
        if declinedUTurn { items.append(URLQueryItem(name: "declined_uturn", value: "1")) }
        if options { items.append(URLQueryItem(name: "options", value: "1")) }
        if let leave { items.append(URLQueryItem(name: "leave", value: leave.parameter)) }
        if let rejoin { items.append(URLQueryItem(name: "rejoin", value: rejoin.parameter)) }
        return formRequest("\(base)/api/route", items)
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
    /// Expect roughly 0.4 s on the server for a first 40 km loop from a given
    /// start (up to 0.8 s around Boston), about the same for a new distance, and
    /// 0.25 s for a shorter distance or another compass direction; longer loops
    /// cost more, about 2 s at 150 km and 3.5 s at 300 km (docs/loop-speed.md).
    /// The server caches two searches per start, over the area the distance can
    /// reach: a shorter distance keeps that cache, a longer one widens it, and
    /// changing `pref` starts again.
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

    /// The longest loop this start can have: `POST /api/loop/limit`.
    ///
    /// Loops are capped by how much road their disc holds, not by one
    /// distance, so the top of the slider is a property of the start. 400 km
    /// where roads are sparse, less in a dense metro. A loop asked for over it
    /// is refused with `LOOP_TOO_LONG` and the same `max_km`, so this is the
    /// slider's courtesy and not the only guard. docs/review-fixes-app.md,
    /// item 4.
    static func loopLimit(from start: CLLocationCoordinate2D) async throws -> LoopLimit {
        try await send(loopLimitRequest(from: start))
    }

    /// The request `loopLimit(from:)` sends; see `routeRequest(...)`.
    static func loopLimitRequest(from start: CLLocationCoordinate2D,
                                 base: String = baseURL) -> URLRequest {
        formRequest("\(base)/api/loop/limit", [
            URLQueryItem(name: "from", value: "\(start.latitude),\(start.longitude)"),
        ])
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
        } catch let error as URLError {
            throw failure(error)
        }

        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw failure(status: http.statusCode, body: data)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw ServiceError.badResponse
        }
    }

    /// A request that threw before any status code existed. Split out of
    /// `send` so the mapping has a test without a network call.
    static func failure(_ error: URLError) -> ServiceError {
        // Something may have answered, slowly; the phone is not the only
        // suspect, so it gets words of its own (docs/loop-lock-contention.md).
        if error.code == .timedOut { return .timedOut }
        // Anything else was thrown before reaching a server, so nothing
        // answered.
        return .offline
    }

    /// A reply that wasn't a 200. Split out of `send` so the mapping has a
    /// test without a network call.
    static func failure(status: Int, body: Data) -> ServiceError {
        // The backend's own message whenever there is one to lift. A rate
        // limiter or a tunnel answers in HTML, not our JSON shape, and that
        // is the case the status code alone used to leak into the sheet.
        guard let refusal = Refusal(body: body) else { return .unreachable(status) }
        // A 503 with our JSON, or the code BUSY at any status, is the backend
        // refusing a loop build because it is already running one — checked
        // before `.server`, which means something else entirely to both
        // callers. A 503 without it is a tunnel or a proxy, and stays
        // `.unreachable`.
        return status == 503 || refusal.kind == .busy ? .busy(refusal.sentence)
                                                      : .server(refusal)
    }

    // MARK: - The trip cap

    /// The longest point-to-point trip the server plans, in a straight line
    /// between its ends (`router.MAX_TRIP_KM`). A reroute gets more room on
    /// the server, so only planning is checked against it here.
    static let maxTripKm = 500.0

    /// The cap as the app says it. Floored, never rounded: 500 km is 310.7
    /// miles, and "up to 311 miles" would promise a trip the server refuses.
    /// docs/review-fixes-app.md, "The cap reads 310 miles".
    static func capMiles(_ km: Double) -> Int { Int(km.milesFromKm.rounded(.down)) }

    /// What the driver reads for a trip over the cap, whether the phone or the
    /// server noticed. The same sentence as the server's, in the app's miles.
    static func tripTooLong(km: Double, maxKm: Double = maxTripKm) -> String {
        "That trip is \(km.wholeMilesFromKm) miles in a straight line. "
            + "Sunday Drive plans drives of up to \(capMiles(maxKm)) miles, "
            + "so pick a stop along the way and plan it in two parts."
    }

    /// The trip's refusal, said on the phone before anything is sent, or nil
    /// when the server should be asked. Planning only; see `maxTripKm`.
    static func refusalBeforeAsking(from a: CLLocationCoordinate2D,
                                    to b: CLLocationCoordinate2D) -> String? {
        let km = CLLocation(latitude: a.latitude, longitude: a.longitude).distance(to: b) / 1000
        return km > maxTripKm ? tripTooLong(km: km) : nil
    }
}

/// The server's "no", read from `{"error": <sentence>, "code": <string>, ...}`.
///
/// Read field by field, never as `[String: String]`: the trip cap's reply
/// carries `max_km` and `km` as numbers, so a dictionary of strings failed to
/// decode, and Boston to Chicago told the driver the service was unreachable
/// (HTTP 400). Older servers send `error` alone, in lower case and with no
/// full stop, and are still read. docs/review-fixes-app.md, item 1.
struct Refusal: Equatable, ExpressibleByStringLiteral {
    /// The codes the server sends beside its sentence: the seven the units
    /// agreed, then the six the router gave the refusals that existed before
    /// codes (docs/review-fixes-router.md, "Error bodies"). A code not listed
    /// here still shows the server's sentence.
    enum Code: String {
        case tripTooLong = "TRIP_TOO_LONG"
        case legTooLong = "LEG_TOO_LONG"
        case loopTooLong = "LOOP_TOO_LONG"
        case noRouteNearby = "NO_ROUTE_NEARBY"
        case startTooFar = "START_TOO_FAR"
        case outsideCoverage = "OUTSIDE_COVERAGE"
        case badInput = "BAD_INPUT"
        case closedForSeason = "CLOSED_FOR_SEASON"
        case sameRoad = "SAME_ROAD"
        case noLoop = "NO_LOOP"
        case busy = "BUSY"
        case notFound = "NOT_FOUND"
        case serverError = "SERVER_ERROR"
    }

    /// The app's words for a road closed for the season, whatever an older
    /// or a newer server words it: the place is real, and the road to it
    /// opens again, so it must never read as a wrong pin or a broken app.
    static let closedForSeason = "The only way there is closed for the season."

    let message: String
    /// The code as sent. Kept as a string so a code this build does not know
    /// still reaches the trace; `kind` is the one the app branches on.
    var rawCode: String?
    var maxKm: Double?
    var km: Double?

    init(message: String, rawCode: String? = nil, maxKm: Double? = nil, km: Double? = nil) {
        self.message = message
        self.rawCode = rawCode
        self.maxKm = maxKm
        self.km = km
    }

    init(stringLiteral value: String) { self.init(message: value) }

    /// Nil unless `body` is a JSON object whose `error` is a string.
    init?(body: Data) {
        guard let object = try? JSONSerialization.jsonObject(with: body) as? [String: Any],
              let message = object["error"] as? String else { return nil }
        self.init(message: message, rawCode: object["code"] as? String,
                  maxKm: Self.number(object["max_km"]), km: Self.number(object["km"]))
    }

    var kind: Code? { rawCode.flatMap(Code.init(rawValue:)) }

    /// What the driver reads. The app's own words where it has numbers to
    /// say them in miles, and the server's sentence otherwise, made one if
    /// an older server sent a lower-case fragment.
    var sentence: String {
        switch kind {
        case .tripTooLong? where km != nil && maxKm != nil:
            return RouteService.tripTooLong(km: km!, maxKm: maxKm!)
        case .closedForSeason?:
            return Self.closedForSeason
        default:
            return Self.asSentence(message)
        }
    }

    /// "no route found between those points" -> "No route found between
    /// those points." Leaves a sentence that already is one alone.
    static func asSentence(_ text: String) -> String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let first = trimmed.first else { return trimmed }
        let capitalised = first.uppercased() + trimmed.dropFirst()
        guard let last = capitalised.last, !".!?”\"".contains(last) else { return capitalised }
        return capitalised + "."
    }

    /// A number, or a string holding one: the contract says numbers, and a
    /// string costs nothing to accept.
    private static func number(_ value: Any?) -> Double? {
        if let number = value as? NSNumber, !(value is Bool) { return number.doubleValue }
        if let text = value as? String { return Double(text) }
        return nil
    }
}
