import XCTest
@testable import SundayDrive

/// The rating prompt's rule, from `docs/rating-prompt.md`: a drive counts when
/// it arrived and took ten minutes or more; the app asks from the second such
/// drive on, at most once per version, from the planning screen; and never
/// under XCTest.
@MainActor
final class RatingPromptTests: XCTestCase {

    private var suite: String!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        suite = "RatingPromptTests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suite)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suite)
        super.tearDown()
    }

    private func prompt() -> RatingPrompt {
        RatingPrompt(defaults: defaults, disabled: false)
    }

    /// Done, then the planning screen comes back. Returns how many times it asked.
    private func arriveAndReturn(_ p: RatingPrompt, minutes: Double = 25,
                                 version: String = "1.0") -> Int {
        var asks = 0
        p.noteArrival(elapsedMinutes: minutes)
        p.planningAppeared(version: version) { asks += 1 }
        return asks
    }

    func test_the_first_counted_drive_does_not_ask_and_the_second_does() {
        let p = prompt()
        XCTAssertEqual(arriveAndReturn(p), 0)
        XCTAssertEqual(p.arrivedDrives, 1)
        XCTAssertEqual(arriveAndReturn(p), 1)
        XCTAssertEqual(p.arrivedDrives, 2)
    }

    func test_a_nine_minute_drive_does_not_count() {
        let p = prompt()
        XCTAssertEqual(arriveAndReturn(p), 0)
        XCTAssertEqual(arriveAndReturn(p, minutes: 9.9), 0)
        XCTAssertEqual(p.arrivedDrives, 1)
        XCTAssertFalse(p.isPending)
        XCTAssertFalse(p.shouldAsk(version: "1.0"))
    }

    func test_exactly_ten_minutes_counts() {
        let p = prompt()
        p.noteArrival(elapsedMinutes: 10)
        XCTAssertEqual(p.arrivedDrives, 1)
    }

    func test_once_asked_the_same_version_does_not_ask_again_and_a_new_one_may() {
        let p = prompt()
        _ = arriveAndReturn(p)
        XCTAssertEqual(arriveAndReturn(p, version: "1.0"), 1)
        XCTAssertEqual(arriveAndReturn(p, version: "1.0"), 0)
        XCTAssertEqual(arriveAndReturn(p, version: "1.0"), 0)
        XCTAssertEqual(arriveAndReturn(p, version: "1.1"), 1)
        XCTAssertEqual(arriveAndReturn(p, version: "1.1"), 0)
    }

    /// The count and the version asked in survive a relaunch; the pending
    /// flag does not, by design.
    func test_the_count_and_the_version_persist_across_instances() {
        _ = arriveAndReturn(prompt())
        XCTAssertEqual(arriveAndReturn(prompt()), 1)
        XCTAssertEqual(arriveAndReturn(prompt()), 0)
        XCTAssertFalse(prompt().isPending)
    }

    /// One Done asks at most once, however many times the planning screen
    /// appears after it.
    func test_one_done_asks_exactly_once() {
        let p = prompt()
        _ = arriveAndReturn(p)
        p.noteArrival(elapsedMinutes: 30)
        var asks = 0
        p.planningAppeared(version: "1.0") { asks += 1 }
        p.planningAppeared(version: "1.0") { asks += 1 }
        p.planningAppeared(version: "1.0") { asks += 1 }
        XCTAssertEqual(asks, 1)
    }

    /// The planning screen coming back without a counted Done — a drive
    /// ended early, or the app's first appearance — never asks, even when
    /// the count would allow it.
    func test_the_planning_screen_alone_never_asks() {
        defaults.set(5, forKey: RatingPrompt.countKey)
        let p = prompt()
        XCTAssertTrue(p.shouldAsk(version: "1.0"))
        var asks = 0
        p.planningAppeared(version: "1.0") { asks += 1 }
        XCTAssertEqual(asks, 0)
    }

    func test_nothing_counts_or_asks_when_disabled() {
        let p = RatingPrompt(defaults: defaults, disabled: true)
        XCTAssertEqual(arriveAndReturn(p), 0)
        XCTAssertEqual(arriveAndReturn(p), 0)
        XCTAssertEqual(arriveAndReturn(p), 0)
        XCTAssertEqual(p.arrivedDrives, 0)
        XCTAssertNil(defaults.object(forKey: RatingPrompt.countKey))
        XCTAssertNil(defaults.object(forKey: RatingPrompt.versionKey))
    }

    /// The suite runs in a hosted Debug app, where the sheet shows every time
    /// it is asked. The shared instance the app uses must be off here, so a
    /// test that drives to arrival and taps Done neither counts nor asks.
    func test_the_app_never_asks_under_xctest() {
        XCTAssertTrue(RatingPrompt.runningUnderXCTest)
        let before = UserDefaults.standard.object(forKey: RatingPrompt.countKey)
        RatingPrompt.shared.noteArrival(elapsedMinutes: 60)
        RatingPrompt.shared.noteArrival(elapsedMinutes: 60)
        XCTAssertFalse(RatingPrompt.shared.isPending)
        XCTAssertFalse(RatingPrompt.shared.shouldAsk(version: RatingPrompt.appVersion))
        var asks = 0
        RatingPrompt.shared.planningAppeared(version: RatingPrompt.appVersion) { asks += 1 }
        XCTAssertEqual(asks, 0)
        XCTAssertEqual(UserDefaults.standard.object(forKey: RatingPrompt.countKey) as? Int,
                       before as? Int)
    }

    func test_the_version_is_the_marketing_version() {
        XCTAssertFalse(RatingPrompt.appVersion.isEmpty)
        XCTAssertEqual(RatingPrompt.appVersion,
                       Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String)
    }
}
