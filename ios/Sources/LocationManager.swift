import CoreLocation
import Observation

/// Thin wrapper around `CLLocationManager` — the one place the app touches the
/// user's location.
///
/// Three ways in. `start()`/`stop()` bracket a live navigation session and
/// stream fixes into `location`; `currentLocation()` takes a single fix so the
/// planning screen can offer "My Location" as a start point without leaving the
/// GPS on; `roughLocation()` takes a fix of any accuracy for the one question
/// that needs no more, whether the phone is in New England.
///
/// The first two reject junk fixes (see `isUsable`). That matters more than it
/// looks: `startUpdatingLocation` hands back a *cached* fix immediately, often
/// minutes old and derived from Wi-Fi rather than GPS, so the first location the
/// app ever sees is the least trustworthy one it will get. Routing from it puts
/// the driver a street or two from where they actually are.
@Observable
final class LocationManager: NSObject, CLLocationManagerDelegate {
    /// The most recent usable fix, or nil until the first one arrives.
    var location: CLLocation?

    /// Called with every usable fix, as it lands. Set for the duration of a
    /// drive by `RouteModel`, cleared when the drive ends.
    ///
    /// This exists because `location` alone is not enough. Reading it from a
    /// SwiftUI `onChange` works only while the app is on screen: backgrounded,
    /// the scene stops rendering, body evaluation is suspended, and observed
    /// changes coalesce — so a locked phone delivers *one* callback carrying the
    /// latest fix when it wakes, and every fix in between is gone. Steps would
    /// stop advancing, arrival would never fire, and the drive trace would hold
    /// a hole exactly the length of the drive that wasn't watched.
    ///
    /// A closure called straight from the delegate has no view in the path, so
    /// the drive runs whether or not anything is drawing it.
    var onFix: (@MainActor (CLLocation) -> Void)?
    /// Current permission state, so the UI can prompt or explain if denied.
    var authorization: CLAuthorizationStatus

    /// Whether that permission includes Precise Location.
    ///
    /// iOS lets someone allow location with Precise switched off, and then
    /// hands out fixes "on the order of about 5km" (`CLLocationManager.h`) —
    /// every one of which `isUsable` rejects. So nothing reached the drive at
    /// all. Reproduced in the simulator, the banner said "50 ft away · Head to
    /// the start of your route" for as long as the car kept moving. Published
    /// so the banner can say what is actually wrong.
    private(set) var accuracyAuthorization: CLAccuracyAuthorization

    /// Location allowed, Precise Location off: the one grant this app can be
    /// given and still not navigate on.
    ///
    /// Read together with the status, as the header says accuracy should be:
    /// before anyone has answered the permission prompt, it means nothing.
    var isPreciseLocationOff: Bool {
        Self.isPreciseLocationOff(authorization, accuracyAuthorization)
    }

    private static func isPreciseLocationOff(_ status: CLAuthorizationStatus,
                                             _ accuracy: CLAccuracyAuthorization) -> Bool {
        (status == .authorizedWhenInUse || status == .authorizedAlways)
            && accuracy == .reducedAccuracy
    }

    /// Whether the app may use location at all, Precise or not.
    var isAuthorized: Bool {
        manager.authorizationStatus == .authorizedWhenInUse
            || manager.authorizationStatus == .authorizedAlways
    }

    /// Whether the phone was in New England at the last fix the app planned
    /// with. See `RegionStatus`.
    ///
    /// Here because both planning models share this object, so the check at
    /// launch, Directions' My Location and the Loop row all write the one
    /// answer, and Home reads it.
    var regionStatus: RegionStatus = .unknown

    /// Record which side of the line a fix is on, and return it.
    @discardableResult
    func noteRegion(of fix: CLLocation) -> RegionStatus {
        regionStatus = RegionStatus(fix.coordinate)
        return regionStatus
    }

    /// The entry in `NSLocationTemporaryUsageDescriptionDictionary`
    /// (`ios/project.yml`) that the precise-location prompt shows. A key that
    /// is not in that dictionary fails silently: CoreLocation shows nothing.
    static let precisePurposeKey = "Navigation"

    /// Worst horizontal accuracy we'll act on, in meters. Roughly "we know which
    /// road you're on"; a good GPS fix in the open is 5–10 m.
    ///
    /// Not to be loosened to let approximate location in. A fix kilometres
    /// wide sits far past `NavigationModel.offRouteCertainMeters` and would
    /// read as off route, and reroute, on every update — the storms this gate
    /// ended. With Precise Location off the answer is to ask for it, or say
    /// so (`isPreciseLocationOff`), never to accept the coarse fix.
    private static let usableAccuracy: Double = 65
    /// Oldest fix we'll act on. Only ever excludes the cached fix delivered at
    /// startup — during a drive, fixes arrive sub-second fresh.
    private static let usableAge: TimeInterval = 15

    private let manager = CLLocationManager()

    /// Whether this *build* declares the background location mode.
    ///
    /// `allowsBackgroundLocationUpdates = true` raises `NSInvalidArgumentException`
    /// when the bundle lacks `UIBackgroundModes: location` — an Objective-C
    /// exception, so no Swift `catch` can reach it and the app simply dies. That
    /// is not a hypothetical: `ios/Generated/Info.plist` is a *gitignored build
    /// output* of `project.yml`, regenerated only by `xcodegen generate`, so a
    /// checkout whose plist predates the entry crashes the instant the driver
    /// taps Start — with a clean `git status` and nothing to suggest why.
    /// Reading the bundle turns that into a degraded drive (foreground-only
    /// updates) instead of a crash, and `recordingProblem` will notice if fixes
    /// then stop while backgrounded.
    private static let backgroundLocationDeclared: Bool = {
        let modes = Bundle.main.object(forInfoDictionaryKey: "UIBackgroundModes") as? [String]
        return modes?.contains("location") ?? false
    }()

    /// True between `start()` and `stop()`, so a one-shot request knows whether
    /// it may switch the GPS back off when it's done.
    private var navigating = false

    /// A `currentLocation()` call waiting for a fix good enough to answer with.
    private var pendingFix: PendingFix?
    /// A `roughLocation()` call waiting for any fix at all.
    private var pendingRoughFix: PendingFix?
    /// How old a fix `roughLocation()` will still answer with.
    private var roughMaxAge: TimeInterval = 0
    /// Every `currentLocation()` call waiting for the permission prompt to
    /// resolve — an array, because there can be more than one.
    ///
    /// This used to be a single continuation, overwritten by the second caller
    /// with no attempt to resume the first, which left that first task
    /// suspended for the life of the process (`SWIFT TASK CONTINUATION MISUSE`)
    /// and its spinner turning in the start field. Two callers is not exotic:
    /// `RoutePanel` offers "My Location" as both a button in the field and a row
    /// in the suggestion list, and `isLocatingUser` — which drives the button's
    /// `.disabled` — is set inside the `Task` body rather than at tap time, so
    /// two quick taps both get through.
    private var pendingAuth: [CheckedContinuation<CLAuthorizationStatus, Never>] = []

    /// One in-flight one-shot request: who to answer, and the best fix seen so
    /// far in case we time out before an accurate one arrives.
    private final class PendingFix {
        var continuation: CheckedContinuation<CLLocation?, Never>?
        var best: CLLocation?

        init(_ continuation: CheckedContinuation<CLLocation?, Never>) {
            self.continuation = continuation
        }

        /// Answer at most once — the fix and the timeout race each other.
        func finish(with location: CLLocation?) {
            continuation?.resume(returning: location)
            continuation = nil
        }
    }

    override init() {
        authorization = manager.authorizationStatus
        accuracyAuthorization = manager.accuracyAuthorization
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBestForNavigation
        // No distance filter, deliberately. A filter cannot make fixes arrive
        // faster — GPS produces them at about 1 Hz and the filter only
        // *suppresses* the ones that moved too little. So at driving speed a 5 m
        // filter changed nothing (1 Hz is already ~29 m apart at 65 mph, which is
        // what `advanceSteps` is written around), while a stopped car moved less
        // than 5 m per second and its updates were dropped almost entirely.
        //
        // That silence is invisible to navigation and fatal to `DriveTrace`:
        // time spent stopped at lights and stop signs is exactly the cost the
        // router charges nothing for, and with the filter on, a 40-second red
        // light left no evidence it had happened.
        manager.distanceFilter = kCLDistanceFilterNone
        // Tell CoreLocation this is a car, so it filters the fix stream for
        // road travel instead of walking.
        manager.activityType = .automotiveNavigation
        // iOS otherwise decides on its own that we've stopped moving and pauses
        // updates — which, mid-drive, silently freezes the whole nav screen.
        manager.pausesLocationUpdatesAutomatically = false
    }

    /// Whether a fix is fresh and accurate enough to act on. Invalid fixes carry
    /// a negative accuracy, which would otherwise sail through a `<` comparison.
    private static func isUsable(_ location: CLLocation) -> Bool {
        location.horizontalAccuracy > 0
            && location.horizontalAccuracy <= usableAccuracy
            && -location.timestamp.timeIntervalSinceNow <= usableAge
    }

    // MARK: - Live navigation

    /// Ask permission (if needed) and start receiving location updates.
    ///
    /// Background updates are switched on here rather than in `init` because
    /// they are only legal while the app is actually navigating, and iOS raises
    /// if the capability isn't declared — so the setting stays paired with the
    /// `UIBackgroundModes` entry in `project.yml` and with the drive it's for.
    /// `showsBackgroundLocationIndicator` puts the blue bar up: this app follows
    /// you from your pocket only while a drive is running, and says so.
    func start() {
        navigating = true
        manager.requestWhenInUseAuthorization()
        // Precise Location off: ask for it for this drive, rather than drive on
        // fixes `isUsable` will reject. Not waited for — fixes start flowing
        // once it is allowed, and the banner says so if it is not. One answer
        // covers the drive: iOS keeps a temporary grant for as long as the
        // background location indicator below is showing.
        if Self.isPreciseLocationOff(manager.authorizationStatus, manager.accuracyAuthorization) {
            manager.requestTemporaryFullAccuracyAuthorization(withPurposeKey: Self.precisePurposeKey)
        }
        // Only if this build actually declares the capability — see
        // `backgroundLocationDeclared`. Setting it without the entry raises an
        // Objective-C exception that no Swift `catch` can reach.
        if Self.backgroundLocationDeclared {
            manager.allowsBackgroundLocationUpdates = true
            manager.showsBackgroundLocationIndicator = true
        }
        manager.startUpdatingLocation()
    }

    /// Stop updates when leaving navigation, to save battery.
    func stop() {
        navigating = false
        // Surrendered as soon as the drive is over. Left on, a one-shot "My
        // Location" from the planning screen would quietly hold a background
        // location grant the user only ever agreed to for a drive. (Clearing it
        // is always safe; only setting it true needs the capability.)
        manager.allowsBackgroundLocationUpdates = false
        // A one-shot still needs them.
        guard pendingFix == nil, pendingRoughFix == nil else { return }
        manager.stopUpdatingLocation()
    }

    // MARK: - One-shot fix, for "My Location" while planning

    /// Wait for a single accurate fix, or give up after `timeout` and return the
    /// best we saw (nil if we saw nothing, or permission was refused).
    ///
    /// Pinned to the main actor deliberately. A `nonisolated` async method runs
    /// on the concurrent executor, not on its caller's actor, so without this
    /// the `CLLocationManager` calls below would be made from a background
    /// thread with no run loop — while its delegate callbacks still arrive on
    /// main, leaving `pendingFix` touched from two threads.
    @MainActor
    func currentLocation(timeout: TimeInterval = 8) async -> CLLocation? {
        if manager.authorizationStatus == .notDetermined {
            _ = await requestAuthorization()
        }
        guard manager.authorizationStatus == .authorizedWhenInUse
                || manager.authorizationStatus == .authorizedAlways else { return nil }

        // Precise Location off, and the timeout below would answer with the
        // best coarse fix it saw: a loop planned from kilometres away. Ask
        // first and wait for the answer, so the timeout cannot run out under
        // the prompt — the same reason `requestAuthorization` waits. Declined,
        // it still answers with that coarse fix; whether planning should
        // refuse it instead has not been decided.
        if Self.isPreciseLocationOff(manager.authorizationStatus, manager.accuracyAuthorization) {
            await preciseLocationDecision()
        }

        // A fix we already have in hand, if it's still good, saves the wait.
        if let known = location, Self.isUsable(known) { return known }

        let fix = await withCheckedContinuation { (continuation: CheckedContinuation<CLLocation?, Never>) in
            // A second request supersedes the first, and the first has to be
            // answered on its way out. Replacing `pendingFix` while its
            // continuation was unresumed left that caller suspended forever —
            // its timeout task bails out on seeing itself superseded — so
            // `useMyLocation` never returned, and the spinner in the field
            // never stopped. Two taps could do it: the button and the
            // "My Location" row in the suggestion list are separate controls.
            if let superseded = pendingFix {
                superseded.finish(with: superseded.best)
            }
            let pending = PendingFix(continuation)
            pendingFix = pending
            manager.startUpdatingLocation()

            Task { @MainActor in
                try? await Task.sleep(for: .seconds(timeout))
                guard self.pendingFix === pending else { return }
                self.pendingFix = nil
                self.settleAfterOneShot()
                pending.finish(with: pending.best)
            }
        }
        return fix
    }

    /// Ask for Precise Location and wait for the answer.
    ///
    /// The completion form inside a continuation rather than the imported
    /// `async` one, so the request is made here on the main actor, like every
    /// other call on `manager`. CoreLocation always calls it once: with an error
    /// when it declines to show the prompt, otherwise after the answer.
    @MainActor
    private func preciseLocationDecision() async {
        await withCheckedContinuation { (answered: CheckedContinuation<Void, Never>) in
            manager.requestTemporaryFullAccuracyAuthorization(
                withPurposeKey: Self.precisePurposeKey) { _ in answered.resume() }
        }
    }

    /// Ask for permission and wait for the user to answer the system prompt.
    @MainActor
    private func requestAuthorization() async -> CLAuthorizationStatus {
        manager.requestWhenInUseAuthorization()
        // If there was nothing to prompt for, no callback is coming and parking
        // below would never end.
        guard manager.authorizationStatus == .notDetermined else {
            return manager.authorizationStatus
        }
        return await authorizationDecision()
    }

    /// Park until the prompt is answered, however many callers are parked.
    ///
    /// Note what this deliberately does *not* do: resume the caller it joins,
    /// the way `PendingFix.finish` resumes the request it supersedes. At this
    /// instant the status is still `.notDetermined`, so an early resume sends
    /// the first caller straight into the guard in `currentLocation()`, out
    /// with nil, and up to the driver as "Couldn't get a location fix" —
    /// printed over the system prompt they are still being asked to answer.
    /// There is one answer coming and it belongs to all of them, so they all
    /// wait for it.
    ///
    /// Split from `requestAuthorization` so the overlap has a test: registering
    /// two waiters is the whole defect, and going through
    /// `requestWhenInUseAuthorization` would put the simulator's process-wide
    /// grant in the middle of it.
    @MainActor
    func authorizationDecision() async -> CLAuthorizationStatus {
        await withCheckedContinuation { pendingAuth.append($0) }
    }

    /// How many callers are parked on the prompt. For the overlap test, which
    /// has to know both have registered before it answers.
    var waitingOnAuthorization: Int { pendingAuth.count }

    /// Ask for permission if nobody has been asked yet, and wait for the
    /// answer. Once, at first launch, so the New England check can run; every
    /// other path asks when it needs a fix, through `currentLocation()`.
    @MainActor
    @discardableResult
    func requestPermissionIfUndetermined() async -> CLAuthorizationStatus {
        guard manager.authorizationStatus == .notDetermined else { return manager.authorizationStatus }
        return await requestAuthorization()
    }

    // MARK: - Any recent fix, for the New England check

    /// The first fix of any accuracy, or nil if there is no permission or
    /// nothing arrives within `timeout`.
    ///
    /// **Not `currentLocation()`, on purpose.** That holds out for a fix good
    /// enough to drive on (`isUsable`, 65 m), and with Precise Location off it
    /// first raises the temporary full-accuracy prompt — "Turn-by-turn guidance
    /// needs your precise location" — which at launch, with no drive in sight,
    /// would make no sense. Which side of the New England line the phone is on
    /// needs kilometres, not metres, so this takes the first real fix to
    /// arrive, an approximate one included, and asks for nothing: not
    /// precision, and not permission either.
    ///
    /// A fix up to `maxAge` old will do. The phone cannot have left the region
    /// since, and a cached fix answers without turning the GPS on.
    @MainActor
    func roughLocation(maxAge: TimeInterval = 600, timeout: TimeInterval = 10) async -> CLLocation? {
        guard isAuthorized else { return nil }
        if let cached = manager.location, Self.isRough(cached, maxAge: maxAge) { return cached }

        return await withCheckedContinuation { (continuation: CheckedContinuation<CLLocation?, Never>) in
            // Superseding answers the earlier caller rather than stranding it,
            // as `currentLocation()` does.
            pendingRoughFix?.finish(with: nil)
            let pending = PendingFix(continuation)
            pendingRoughFix = pending
            roughMaxAge = maxAge
            manager.startUpdatingLocation()

            Task { @MainActor in
                try? await Task.sleep(for: .seconds(timeout))
                guard self.pendingRoughFix === pending else { return }
                self.pendingRoughFix = nil
                self.settleAfterOneShot()
                pending.finish(with: nil)
            }
        }
    }

    /// Real, and recent enough to say which state the phone is in. Any
    /// accuracy; an invalid fix carries a negative one.
    private static func isRough(_ location: CLLocation, maxAge: TimeInterval) -> Bool {
        location.horizontalAccuracy > 0 && -location.timestamp.timeIntervalSinceNow <= maxAge
    }

    /// Switch the GPS back off if a one-shot turned it on outside navigation,
    /// once no other one-shot is still waiting on it.
    private func settleAfterOneShot() {
        if !navigating, pendingFix == nil, pendingRoughFix == nil { manager.stopUpdatingLocation() }
    }

    // MARK: - CLLocationManagerDelegate

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let newest = locations.last else { return }

        // A one-shot holds out for an accurate fix, but keeps the best it has
        // seen so a timeout can still answer with something.
        if let pending = pendingFix {
            // Valid first, then better. An invalid fix carries a *negative*
            // accuracy — the case `isUsable` was written for — so on a bare `<`
            // it outranks every real fix and `?? true` accepts it outright when
            // nothing is held yet. The timeout below then answers with a
            // coordinate CoreLocation has already called meaningless, in
            // practice (0, 0), which `useMyLocation` plans a trip from without
            // complaint. Coarse-but-real fixes are still kept: they are what
            // this fallback exists to provide.
            if newest.horizontalAccuracy > 0,
               pending.best.map({ newest.horizontalAccuracy < $0.horizontalAccuracy }) ?? true {
                pending.best = newest
            }
            if Self.isUsable(newest) {
                pendingFix = nil
                settleAfterOneShot()
                pending.finish(with: newest)
            }
        }

        // The New England check takes the first real fix, however coarse.
        if let rough = pendingRoughFix, Self.isRough(newest, maxAge: roughMaxAge) {
            pendingRoughFix = nil
            settleAfterOneShot()
            rough.finish(with: newest)
        }

        guard Self.isUsable(newest) else { return }
        location = newest
        // Delivered here rather than observed from a view — see `onFix`. Core
        // Location calls its delegate on the run loop the manager was created
        // on, which for this app is main, so the isolation is real rather than
        // assumed away.
        MainActor.assumeIsolated { onFix?(newest) }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        // Same isolation as `didUpdateLocations` above, and for the same reason:
        // CoreLocation calls its delegate on the run loop the manager was
        // created on, which for this app is main.
        //
        // Accuracy first, so whoever `authorizationResolved` wakes reads the
        // grant whole. This callback fires on a change to either.
        MainActor.assumeIsolated {
            accuracyResolved(manager.accuracyAuthorization)
            authorizationResolved(manager.authorizationStatus)
        }
    }

    /// Publish whether Precise Location is on. Separate from the delegate
    /// callback for the reason `authorizationResolved` is: a test can neither
    /// set nor predict the simulator's real grant.
    @MainActor
    func accuracyResolved(_ accuracy: CLAccuracyAuthorization) {
        accuracyAuthorization = accuracy
    }

    /// The prompt has an answer: publish it and release everyone waiting.
    ///
    /// Separate from the delegate callback so a test can supply a status. The
    /// callback reads the process-wide grant, which a unit test can neither set
    /// nor predict — and this is the one place a stranded waiter is fixed, so it
    /// is the one place worth being able to drive directly.
    @MainActor
    func authorizationResolved(_ status: CLAuthorizationStatus) {
        authorization = status
        // `.notDetermined` is the state *before* the prompt is answered, so it
        // isn't an answer — keep waiting.
        guard status != .notDetermined else { return }
        let waiting = pendingAuth
        pendingAuth = []
        for continuation in waiting { continuation.resume(returning: status) }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // A refusal is terminal for a one-shot; transient errors just mean the
        // next fix hasn't landed yet, and the timeout will cover us.
        guard (error as? CLError)?.code == .denied else { return }
        let waiting = [pendingFix, pendingRoughFix].compactMap { $0 }
        guard !waiting.isEmpty else { return }
        pendingFix = nil
        pendingRoughFix = nil
        settleAfterOneShot()
        for pending in waiting { pending.finish(with: nil) }
    }
}
