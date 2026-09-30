import XCTest
@testable import SundayDrive

/// The in-app privacy-policy link (Guideline 5.1.1(i)) goes to the page
/// `.github/workflows/pages.yml` publishes, and not to the routing server.
final class PrivacyPolicyLinkTests: XCTestCase {

    func test_the_link_is_the_published_policy_page() {
        XCTAssertEqual(PrivacyPolicy.url.absoluteString,
                       "https://jamesk1281.github.io/SundayDrive/privacy/")
    }

    func test_the_link_is_not_built_from_the_api_host() {
        let api = Bundle.main.object(forInfoDictionaryKey: "SundayDriveAPIBaseURL") as? String
        if let api, let apiHost = URL(string: api)?.host {
            XCTAssertNotEqual(PrivacyPolicy.url.host, apiHost)
        }
    }
}
