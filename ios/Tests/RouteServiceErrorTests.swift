import XCTest
@testable import SundayDrive

/// How a failed request becomes the words a driver reads.
///
/// The cases decide what happens next as well as what is said: `.server` is
/// the server's "no", which the loop page answers with a second request and a
/// drive books against the reroute backoff, so a busy server or a slow answer
/// must never land there. docs/loop-lock-contention.md.
final class RouteServiceErrorTests: XCTestCase {

    private func json(_ object: [String: String]) -> Data {
        try! JSONSerialization.data(withJSONObject: object)
    }

    func test_a_503_with_the_servers_json_is_busy_in_its_words() {
        let error = RouteService.failure(
            status: 503, body: json(["error": "Busy planning other drives. Try again in a moment."]))
        guard case .busy(let message) = error else {
            return XCTFail("expected .busy, got \(error)")
        }
        XCTAssertEqual(message, "Busy planning other drives. Try again in a moment.")
        XCTAssertEqual(error.errorDescription, message)
    }

    func test_a_503_without_json_is_a_tunnel_or_proxy_and_stays_unreachable() {
        let error = RouteService.failure(status: 503,
                                         body: Data("<html>Service Unavailable</html>".utf8))
        guard case .unreachable(503) = error else {
            return XCTFail("expected .unreachable(503), got \(error)")
        }
    }

    func test_any_other_status_with_json_is_still_the_servers_no() {
        let error = RouteService.failure(status: 404,
                                         body: json(["error": "no route found between those points"]))
        guard case .server("no route found between those points") = error else {
            return XCTFail("expected .server, got \(error)")
        }
    }

    func test_a_timeout_has_neutral_words_of_its_own() {
        let error = RouteService.failure(URLError(.timedOut))
        guard case .timedOut = error else { return XCTFail("expected .timedOut, got \(error)") }
        XCTAssertEqual(error.errorDescription,
                       "The routing service didn't answer in time. Try again in a moment.")
        // Neither the phone's fault nor the server's.
        XCTAssertFalse(error.errorDescription!.contains("network"))
        XCTAssertFalse(error.errorDescription!.contains("Busy"))
    }

    func test_every_other_url_error_is_still_offline() {
        for code in [URLError.Code.notConnectedToInternet, .cannotConnectToHost,
                     .networkConnectionLost, .cannotFindHost, .dnsLookupFailed] {
            guard case .offline = RouteService.failure(URLError(code)) else {
                return XCTFail("\(code) is no longer .offline")
            }
        }
    }
}
