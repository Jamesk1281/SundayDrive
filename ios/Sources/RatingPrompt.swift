import Foundation

/// When the app asks for an App Store rating. See `docs/rating-prompt.md`.
///
/// The rule:
/// - **What counts:** a drive that arrived — the arrival card's Done — and
///   took at least ten minutes. A drive ended early (End, or "End drive" on
///   the stalled card) never reaches this type, which is the point: the
///   ended-early drive is often the bad one.
/// - **When:** from the second counted drive on, at most once per app version.
///   Apple's own cap (three showings a year) sits on top of that, invisibly.
/// - **Where:** never on the arrival card or the driving screen. Done only
///   marks the ask as pending; the planning screen asks once it is back.
///
/// The system sheet is the only prompt there is. Guideline 5.6.1 forbids a
/// custom one, so there is no "Rate us" button and no "Enjoying it?" step.
///
/// Two values go into `UserDefaults`: a count of drives that counted, and the
/// last version asked in. Both are listed in `docs/privacy-policy.md` §1 and
/// on `site/privacy/index.html`. The pending flag lives only in memory: it is
/// set and spent within one trip from the arrival card to the planning screen.
@MainActor
final class RatingPrompt {
    static let shared = RatingPrompt()

    /// A drive shorter than this did not count.
    static let minimumMinutes = 10.0
    /// The counted drive the app first asks after.
    static let drivesBeforeAsking = 2

    static let countKey = "ratingPromptArrivedDrives"
    static let versionKey = "ratingPromptLastAskedVersion"

    /// True in the hosted test app. A Debug build shows the sheet every time
    /// it is asked, and some tests drive to arrival, so under XCTest nothing
    /// is counted and nothing is asked.
    nonisolated static var runningUnderXCTest: Bool {
        ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil
    }

    /// The marketing version (`CFBundleShortVersionString`), which is what
    /// "once per version" means.
    nonisolated static var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
    }

    private let defaults: UserDefaults
    private let isDisabled: Bool

    /// Set by a counted Done, spent by the planning screen.
    private(set) var isPending = false

    init(defaults: UserDefaults = .standard,
         disabled: Bool = RatingPrompt.runningUnderXCTest) {
        self.defaults = defaults
        self.isDisabled = disabled
    }

    var arrivedDrives: Int { defaults.integer(forKey: Self.countKey) }

    /// The arrival card's Done. Counts the drive if it was long enough, and
    /// marks an ask as pending if the count now allows one.
    func noteArrival(elapsedMinutes: Double) {
        guard !isDisabled, elapsedMinutes >= Self.minimumMinutes else { return }
        defaults.set(arrivedDrives + 1, forKey: Self.countKey)
        isPending = true
    }

    func shouldAsk(version: String) -> Bool {
        !isDisabled
            && arrivedDrives >= Self.drivesBeforeAsking
            && defaults.string(forKey: Self.versionKey) != version
    }

    func didAsk(version: String) {
        defaults.set(version, forKey: Self.versionKey)
    }

    /// The planning screen is back. Calls `ask` at most once per pending Done,
    /// and only when the policy allows it.
    func planningAppeared(version: String, ask: () -> Void) {
        guard isPending else { return }
        isPending = false
        guard shouldAsk(version: version) else { return }
        didAsk(version: version)
        ask()
    }
}
