import XCTest
@testable import SundayDrive

/// Two things App Review reads in the app's own words: the text of the location
/// prompt (Guideline 5.1.1(ii), "clearly and completely") and the way to contact
/// the developer from inside the app (Guideline 1.5).
///
/// Whether the prompt's text matches the privacy policy that quotes it is
/// `tests/test_privacy_page.py`'s job, since the policy is not in the bundle.
/// See `docs/location-text-and-contact.md`.
final class LocationTextAndContactTests: XCTestCase {

    // MARK: - The location prompt

    /// Read out of the built bundle, like the precise-location purpose in
    /// `LocationManagerTests`: the text is set in `ios/project.yml`, and a
    /// project nobody regenerated still ships the old one.
    private var purpose: String {
        Bundle.main.object(forInfoDictionaryKey: "NSLocationWhenInUseUsageDescription")
            as? String ?? ""
    }

    func test_the_location_prompt_has_text_to_show() {
        XCTAssertFalse(purpose.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                       "set NSLocationWhenInUseUsageDescription in ios/project.yml, "
                       + "then run `cd ios && xcodegen generate`")
    }

    /// iOS already titles the alert *Allow "Sunday Drive" to use your
    /// location?*, so a body that names the app says it twice. Decided
    /// 2026-09-20; see `docs/privacy-policy.md` §2.
    func test_the_location_prompt_does_not_name_the_app() {
        XCTAssertFalse(purpose.localizedCaseInsensitiveContains("Sunday Drive"), purpose)
    }

    // MARK: - Contacting the developer

    func test_help_and_support_opens_the_support_page() {
        XCTAssertEqual(Support.url.scheme, "https")
        XCTAssertEqual(Support.url.host, "jamesk1281.github.io")
        XCTAssertEqual(Support.url.absoluteString, "https://jamesk1281.github.io/SundayDrive/")
    }

    /// The simulator has no Mail, so this is the only check that the row would
    /// address a message to the inbox the support page lists. The address is
    /// the whole path of a `mailto:` URL, which has no host.
    func test_email_the_developer_writes_to_the_support_address() {
        XCTAssertEqual(Support.email.scheme, "mailto")
        XCTAssertEqual(URLComponents(url: Support.email, resolvingAgainstBaseURL: false)?.path,
                       "support@jameskouvlis.com")
    }

    /// The support page links the policy as `privacy/`, relative to itself
    /// (`tests/test_support_page.py`). So the two constants are one site, and a
    /// repo rename that updates one has to update the other.
    func test_the_support_page_and_the_privacy_policy_are_one_site() {
        XCTAssertEqual(URL(string: "privacy/", relativeTo: Support.url)?.absoluteURL,
                       PrivacyPolicy.url)
    }
}
