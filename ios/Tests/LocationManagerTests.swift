import CoreLocation
import XCTest
@testable import SundayDrive

/// The settings that decide whether a drive is recorded at all.
///
/// These are pairings between Swift and `project.yml`, and every one of them
/// fails at the worst possible moment: `start()` is called when the driver taps
/// Start, which is the first thing that happens on a test drive and the last
/// place you want to find out.
@MainActor
final class LocationManagerTests: XCTestCase {

    func test_the_app_declares_the_background_modes_it_asks_for() {
        // `allowsBackgroundLocationUpdates = true` raises an exception if
        // UIBackgroundModes doesn't contain "location" — a pairing across two
        // files with nothing but this to hold it together.
        let modes = Bundle.main.object(forInfoDictionaryKey: "UIBackgroundModes") as? [String]
        XCTAssertEqual(modes.map(Set.init), ["location", "audio"],
                       "set in ios/project.yml; LocationManager.start() and "
                       + "VoiceGuide both depend on it")
        // `audio` is not decoration. Measured on an iPhone 17 on 2026-08-30:
        // without it, `AVAudioSession.setActive(true)` threw `'!pla'` on all 19
        // attempts made from the background and nothing was ever spoken, while
        // the same binary with it declared spoke 23 of 23, 16 of those with the
        // screen off. Every drive on this app runs with the phone in a pocket,
        // so dropping this key does not degrade the voice, it removes it — and
        // a simulator will insist everything is fine. See
        // `docs/voice-guidance-plan.md` §1.
        XCTAssertTrue(modes?.contains("audio") ?? false,
                      "spoken guidance is silent in the background without this")
    }

    func test_starting_navigation_does_not_raise() {
        // The exception above is a hard crash, not a Swift error, so nothing
        // catches it. Exercising the real call is the only thing that proves
        // the pairing holds.
        let manager = LocationManager()
        manager.start()
        manager.stop()
    }

    // MARK: - The drive must not depend on being watched

    func test_a_fix_reaches_the_drive_with_no_view_in_the_path() {
        // The defect this guards. `nav.update` used to hang off a SwiftUI
        // `onChange`, and SwiftUI suspends body evaluation when the scene stops
        // rendering — so a locked phone delivered one coalesced callback on
        // wake and dropped every fix in between. Steps stopped advancing,
        // arrival never fired, and the trace held a hole the length of the
        // drive nobody was looking at.
        //
        // No view is constructed anywhere in this test. That is the point.
        let manager = LocationManager()
        var seen: [CLLocation] = []
        manager.onFix = { seen.append($0) }

        manager.locationManager(CLLocationManager(),
                                didUpdateLocations: [Fixture.fixAt(100)])
        manager.locationManager(CLLocationManager(),
                                didUpdateLocations: [Fixture.fixAt(200)])

        XCTAssertEqual(seen.count, 2, "every fix should reach the drive, not just the last")
    }

    func test_a_junk_fix_still_never_reaches_the_drive() {
        // Delivering straight from the delegate must not smuggle past the
        // accuracy and staleness checks the drive relies on.
        let manager = LocationManager()
        var seen = 0
        manager.onFix = { _ in seen += 1 }

        let stale = CLLocation(
            coordinate: Fixture.origin, altitude: 0,
            horizontalAccuracy: 5, verticalAccuracy: 5,
            timestamp: Date(timeIntervalSinceNow: -600))
        let vague = CLLocation(
            coordinate: Fixture.origin, altitude: 0,
            horizontalAccuracy: 500, verticalAccuracy: 5, timestamp: Date())

        manager.locationManager(CLLocationManager(), didUpdateLocations: [stale])
        manager.locationManager(CLLocationManager(), didUpdateLocations: [vague])
        XCTAssertEqual(seen, 0)
    }

    func test_ending_a_drive_unhooks_it() {
        // Otherwise the next "My Location" tap on the planning screen would
        // still be feeding a drive that finished hours ago.
        let model = RouteModel()
        model.end = Fixture.north(5000)
        model.startNavigation(Fixture.straightRoute())
        XCTAssertNotNil(model.locationManager.onFix)

        model.endNavigation()
        XCTAssertNil(model.locationManager.onFix)
    }

    // MARK: - Two taps must not strand a task

    func test_two_callers_waiting_on_the_permission_prompt_both_resume() async {
        // The defect. `pendingAuth` was one continuation, and a second caller
        // overwrote it without resuming the first — so that first task hung for
        // the life of the process (`SWIFT TASK CONTINUATION MISUSE`) with its
        // spinner still turning in the start field. Two callers is ordinary:
        // "My Location" is both a button in the field and a row in the
        // suggestion list, and `isLocatingUser` is set inside the `Task` body
        // rather than at tap time, so two quick taps both get through.
        let manager = LocationManager()
        // CoreLocation delivers one authorization callback of its own when a
        // manager is created. Let it land before the waiters register, so this
        // test answers the prompt rather than racing that callback.
        try? await Task.sleep(for: .milliseconds(100))

        let answered = expectation(description: "both callers resume")
        answered.expectedFulfillmentCount = 2
        let statuses = Answers()
        for _ in 0..<2 {
            Task { @MainActor in
                statuses.received.append(await manager.authorizationDecision())
                answered.fulfill()
            }
        }

        // Both have to be parked before the prompt is answered — that overlap
        // is the whole bug, and a test that answered first would pass on the
        // broken code too.
        var spins = 0
        while manager.waitingOnAuthorization < 2 && spins < 1_000 {
            await Task.yield()
            spins += 1
        }
        XCTAssertEqual(manager.waitingOnAuthorization, 2, "both should be waiting")

        manager.authorizationResolved(.authorizedWhenInUse)

        await fulfillment(of: [answered], timeout: 2)
        XCTAssertEqual(statuses.received, [.authorizedWhenInUse, .authorizedWhenInUse])
        XCTAssertEqual(manager.waitingOnAuthorization, 0)
    }

    func test_nobody_is_released_on_notDetermined() async {
        // `.notDetermined` is the state *before* the prompt is answered, so it
        // is not an answer. Waking a caller on it is the tempting wrong fix: it
        // resumes, fails the authorization guard in `currentLocation()`, and
        // puts "Couldn't get a location fix. Try again in a moment." on screen
        // over the system prompt the driver is still being asked to answer.
        let manager = LocationManager()
        try? await Task.sleep(for: .milliseconds(100))

        let answered = expectation(description: "the caller resumes")
        Task { @MainActor in
            _ = await manager.authorizationDecision()
            answered.fulfill()
        }
        var spins = 0
        while manager.waitingOnAuthorization < 1 && spins < 1_000 {
            await Task.yield()
            spins += 1
        }

        manager.authorizationResolved(.notDetermined)
        XCTAssertEqual(manager.waitingOnAuthorization, 1, "still waiting for a real answer")

        // Released properly, so the task doesn't outlive the test.
        manager.authorizationResolved(.denied)
        await fulfillment(of: [answered], timeout: 2)
    }

    /// A box for what the concurrent waiters came back with. `Task` closures are
    /// `@Sendable`, so they cannot write to a local `var`.
    @MainActor private final class Answers {
        var received: [CLAuthorizationStatus] = []
    }

    // MARK: - Precise Location off

    // With Precise Location off, iOS hands out fixes kilometres wide, and
    // `isUsable` rejects every one, so the drive never receives a position.
    // Reproduced in the simulator: "50 ft away · Head to the start of your
    // route" and "No GPS fixes yet" for as long as the car kept moving. The fix
    // is to ask for precise location or say it is off, never to accept the
    // coarse fix. These are synchronous on purpose: CoreLocation's own
    // authorization callback lands on the main run loop, so it cannot overwrite
    // the state a test sets until the test is over.

    func test_the_precise_location_prompt_has_a_purpose_to_show() {
        // A purpose key missing from this dictionary shows no prompt and
        // reports nothing, so a typo here, or the entry added to the generated
        // plist instead of project.yml, fails exactly as silently as the bug.
        let purposes = Bundle.main.object(
            forInfoDictionaryKey: "NSLocationTemporaryUsageDescriptionDictionary") as? [String: String]
        XCTAssertFalse((purposes?[LocationManager.precisePurposeKey] ?? "").isEmpty,
                       "set in ios/project.yml; LocationManager asks with this key")
    }

    func test_the_accuracy_gate_is_not_loosened_for_approximate_fixes() {
        // A kilometre-wide fix reads as off route on every update, and the
        // reroute storms this gate ended would come straight back.
        let manager = LocationManager()
        var seen: [Double] = []
        manager.onFix = { seen.append($0.horizontalAccuracy) }
        for accuracy in [65.0, 66.0, 5_000.0] {
            manager.locationManager(CLLocationManager(), didUpdateLocations: [CLLocation(
                coordinate: Fixture.origin, altitude: 0, horizontalAccuracy: accuracy,
                verticalAccuracy: 5, timestamp: Date())])
        }
        XCTAssertEqual(seen, [65.0])
    }

    func test_a_drive_with_no_fix_says_waiting_for_gps_rather_than_a_distance() {
        // `distanceToRouteStart` starts at 0 and `distanceText` never prints
        // less than 50 ft, which is how a drive with no position at all came
        // to say "50 ft away".
        let manager = granted(.fullAccuracy)
        let nav = drive()
        XCTAssertNil(nav.lastFixAt)
        XCTAssertEqual(NavView.bannerText(nav: nav, location: manager),
                       NavView.BannerText(symbol: "location.north.fill", alert: false,
                                          over: "Waiting for GPS",
                                          main: "Head to the start of your route"))

        // The distance comes back with the first fix that has one to give.
        nav.update(Fixture.fix(Fixture.offset(east: 2_000, north: 0)))
        XCTAssertFalse(nav.hasJoinedRoute)
        XCTAssertEqual(NavView.bannerText(nav: nav, location: manager).over, "1.2 mi away")
    }

    func test_precise_location_off_is_what_the_banner_says() {
        // Accuracy reaches the banner through the same kind of seam the status
        // does. No approximate fix is ever accepted, so nothing about the drive
        // itself changes: the banner has to be told why.
        let manager = granted(.reducedAccuracy)
        let nav = drive()
        XCTAssertTrue(manager.isPreciseLocationOff)
        XCTAssertEqual(NavView.bannerText(nav: nav, location: manager),
                       NavView.BannerText(symbol: "location.slash", alert: true,
                                          over: "Precise Location is off",
                                          main: "Turn it on in Settings to navigate"))

        // Allowed for the drive, and the banner is the drive's again.
        manager.accuracyResolved(.fullAccuracy)
        XCTAssertFalse(manager.isPreciseLocationOff)
        XCTAssertEqual(NavView.bannerText(nav: nav, location: manager).over, "Waiting for GPS")
    }

    func test_accuracy_means_nothing_until_location_is_allowed() {
        // `CLLocationManager.h`: accuracy is to be read "in the context of the
        // authorizationStatus". Before the prompt is answered there is no grant
        // to be approximate, and a refusal has a banner of its own.
        let manager = LocationManager()
        manager.accuracyResolved(.reducedAccuracy)
        manager.authorizationResolved(.notDetermined)
        XCTAssertFalse(manager.isPreciseLocationOff)

        manager.authorizationResolved(.denied)
        XCTAssertFalse(manager.isPreciseLocationOff)
        XCTAssertEqual(NavView.bannerText(nav: drive(), location: manager).over, "Location is off")

        manager.authorizationResolved(.authorizedAlways)
        XCTAssertTrue(manager.isPreciseLocationOff)
    }

    /// A manager whose grant is location allowed, at the given accuracy.
    private func granted(_ accuracy: CLAccuracyAuthorization) -> LocationManager {
        let manager = LocationManager()
        manager.authorizationResolved(.authorizedWhenInUse)
        manager.accuracyResolved(accuracy)
        return manager
    }

    /// A drive that has received no fix.
    private func drive() -> NavigationModel {
        NavigationModel(route: Fixture.straightRoute(), destination: Fixture.north(5000),
                        pref: 1.0, weights: [:])
    }

    func test_traces_can_be_taken_off_the_phone() {
        // The whole export path. Without this key the traces are real, correct,
        // and unreachable behind the app sandbox — every drive recorded and no
        // way to read one.
        XCTAssertEqual(
            Bundle.main.object(forInfoDictionaryKey: "UIFileSharingEnabled") as? Bool, true,
            "set in ios/project.yml; Documents/traces is only reachable with it")
    }
}
