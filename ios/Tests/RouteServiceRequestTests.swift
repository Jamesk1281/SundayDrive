import CoreLocation
import XCTest
@testable import SundayDrive

/// The requests the app sends carry no coordinate in their URL.
///
/// The API sits behind a Cloudflare tunnel that terminates TLS, and a URL is
/// what an access log records by default, so the driver's start, destination
/// and waypoint travel in a POST body instead. See
/// docs/coordinates-out-of-the-url-brief.md.
///
/// These check the built `URLRequest`, not a live call, on purpose. The server
/// would answer a POST that left its parameters on the URL too, so a
/// half-converted client passes every end-to-end test while fixing nothing. The
/// URL itself is the only place that mistake can be seen.
final class RouteServiceRequestTests: XCTestCase {

    // Five decimal places, and digits that appear nowhere else in the request,
    // so a coordinate that leaks into the URL can be found by its digits.
    private let start = CLLocationCoordinate2D(latitude: 42.35512, longitude: -71.06573)
    private let end = CLLocationCoordinate2D(latitude: 42.26261, longitude: -71.80237)
    private let via = CLLocationCoordinate2D(latitude: 42.48793, longitude: -72.18891)
    private let base = "https://api.example.test"

    /// The body's parameters, decoded the way a form decoder reads them.
    private func form(_ request: URLRequest,
                      file: StaticString = #filePath, line: UInt = #line) -> [String: String] {
        guard let data = request.httpBody, let body = String(data: data, encoding: .utf8)
        else {
            XCTFail("no body", file: file, line: line)
            return [:]
        }
        var components = URLComponents()
        components.percentEncodedQuery = body
        let items = components.queryItems ?? []
        let pairs = items.map { ($0.name, $0.value ?? "") }
        XCTAssertEqual(Set(items.map(\.name)).count, items.count,
                       "a key sent twice", file: file, line: line)
        return Dictionary(pairs, uniquingKeysWith: { first, _ in first })
    }

    private func assertNoCoordinateInURL(_ request: URLRequest,
                                         _ points: [CLLocationCoordinate2D],
                                         file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertEqual(request.httpMethod, "POST", file: file, line: line)
        XCTAssertNil(request.url?.query, "parameters left on the URL", file: file, line: line)
        let url = request.url?.absoluteString ?? ""
        for point in points {
            for value in [point.latitude, point.longitude] {
                // The fractional digits alone: "35512" of 42.35512. The integer
                // part is too short to mean anything on its own.
                let digits = String(format: "%.5f", abs(value)).split(separator: ".")[1]
                XCTAssertFalse(url.contains(digits),
                               "\(value) is in the URL \(url)", file: file, line: line)
            }
        }
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"),
                       "application/x-www-form-urlencoded", file: file, line: line)
    }

    func test_a_route_request_carries_its_coordinates_in_the_body() {
        let request = RouteService.routeRequest(
            from: start, to: end, via: via, pref: 0.5,
            weights: ["coast": 2.0, "town": 0.25], heading: 182.44, base: base)

        XCTAssertEqual(request.url?.absoluteString, "\(base)/api/route")
        assertNoCoordinateInURL(request, [start, end, via])
        // Exactly the keys and value formats the query string used to carry,
        // which is what lets the server parse a POST with the code it already
        // had for a GET.
        XCTAssertEqual(form(request), [
            "from": "42.35512,-71.06573",
            "to": "42.26261,-71.80237",
            "via": "42.48793,-72.18891",
            "pref": "0.50",
            "w_coast": "2.00",
            "w_town": "0.25",
            "heading": "182.4",
        ])
    }

    func test_a_plain_route_request_sends_only_what_it_was_given() {
        let request = RouteService.routeRequest(from: start, to: end, pref: 1.0, base: base)
        assertNoCoordinateInURL(request, [start, end])
        XCTAssertEqual(form(request), [
            "from": "42.35512,-71.06573",
            "to": "42.26261,-71.80237",
            "pref": "1.00",
        ])
    }

    func test_a_loop_request_carries_its_start_in_the_body() {
        let request = RouteService.loopRequest(
            from: start, km: 40, sector: "NE", weights: ["water": 2.5], base: base)

        XCTAssertEqual(request.url?.absoluteString, "\(base)/api/loop")
        assertNoCoordinateInURL(request, [start])
        XCTAssertEqual(form(request), [
            "from": "42.35512,-71.06573",
            "km": "40.0",
            "pref": "1.00",
            "w_water": "2.50",
            "sector": "NE",
        ])
    }

    func test_the_app_posts_to_its_configured_backend() {
        // No `base`: what `route(...)` and `loop(...)` actually send.
        let route = RouteService.routeRequest(from: start, to: end, pref: 0.5)
        let loop = RouteService.loopRequest(from: start, km: 40)
        XCTAssertEqual(route.url?.absoluteString, "\(RouteService.baseURL)/api/route")
        XCTAssertEqual(loop.url?.absoluteString, "\(RouteService.baseURL)/api/loop")
        assertNoCoordinateInURL(route, [start, end])
        assertNoCoordinateInURL(loop, [start])
    }

    func test_a_plus_sign_survives_form_decoding() {
        // In a form body "+" means a space. `URLComponents` leaves it bare,
        // which is right for a query and wrong here.
        let request = RouteService.formRequest("\(base)/api/route",
                                               [URLQueryItem(name: "x", value: "a+b c")])
        XCTAssertEqual(request.httpBody.flatMap { String(data: $0, encoding: .utf8) },
                       "x=a%2Bb%20c")
    }
}
