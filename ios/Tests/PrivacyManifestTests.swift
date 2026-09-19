import XCTest

/// `PrivacyInfo.xcprivacy`, asserted from inside the built app bundle.
///
/// These are not tests of behaviour either — like `AttributionTests`, they are
/// tests of a file somebody else specifies the contents of. The failure mode
/// they guard against is specific and silent: `ios/Scenic.xcodeproj` is a
/// gitignored build output, so a manifest that is plainly on disk can be absent
/// from the product simply because nobody ran `xcodegen generate`. Nothing
/// warns you. App Store Connect does, weeks later, at submission.
///
/// So the first test deliberately reads `Bundle.main` — which, because
/// `ScenicTests` is app-hosted (`TEST_HOST` is set in the generated project),
/// is the **app** bundle at run time — rather than reading the source file. A
/// manifest that only exists in the repository fails here.
///
/// Declarations checked against Apple's "Describing use of required reason API"
/// and "Describing data use in privacy manifests", and against the code that
/// justifies each one. The reasoning is in `docs/app-store-submission.md`.
final class PrivacyManifestTests: XCTestCase {

    /// The manifest, as the App Store will see it: parsed out of the product.
    private func manifest(file: StaticString = #filePath, line: UInt = #line) throws -> [String: Any] {
        let url = try XCTUnwrap(
            Bundle.main.url(forResource: "PrivacyInfo", withExtension: "xcprivacy"),
            "PrivacyInfo.xcprivacy is not in the built app bundle. It exists at "
            + "ios/Sources/PrivacyInfo.xcprivacy; if that file is there, the "
            + "project is stale — run `cd ios && xcodegen generate`.",
            file: file, line: line)
        let parsed = try PropertyListSerialization.propertyList(
            from: try Data(contentsOf: url), format: nil)
        return try XCTUnwrap(parsed as? [String: Any], "manifest is not a dictionary",
                             file: file, line: line)
    }

    func test_the_privacy_manifest_ships_in_the_app_bundle() throws {
        XCTAssertFalse(try manifest().isEmpty)
    }

    // MARK: - Required reason APIs

    /// Six live `UserDefaults` call sites — `VoiceCatalogue.swift:118,119,148,149`
    /// and `VoiceGuide.swift:351,352` — put the app in
    /// `NSPrivacyAccessedAPICategoryUserDefaults`. Reason `CA92.1` is "access
    /// info from same app, per documentation", which is what all three keys do:
    /// the chosen voice, a speech-length cache, and the mute flag.
    func test_userdefaults_access_is_declared_with_reason_CA92_1() throws {
        let types = try XCTUnwrap(
            manifest()["NSPrivacyAccessedAPITypes"] as? [[String: Any]])
        let userDefaults = types.first {
            $0["NSPrivacyAccessedAPIType"] as? String
                == "NSPrivacyAccessedAPICategoryUserDefaults"
        }
        let entry = try XCTUnwrap(userDefaults, "UserDefaults category not declared")
        XCTAssertEqual(entry["NSPrivacyAccessedAPITypeReasons"] as? [String], ["CA92.1"])
    }

    /// The other four categories are absent from `ios/Sources` and must stay
    /// undeclared — an unused declaration is as wrong as a missing one, and
    /// this is the assertion that notices if one is pasted in from a template.
    func test_no_other_required_reason_category_is_declared() throws {
        let types = try XCTUnwrap(
            manifest()["NSPrivacyAccessedAPITypes"] as? [[String: Any]])
        XCTAssertEqual(types.compactMap { $0["NSPrivacyAccessedAPIType"] as? String },
                       ["NSPrivacyAccessedAPICategoryUserDefaults"],
                       "Only UserDefaults is used. Verified by grep over ios/Sources: "
                       + "no file-timestamp, disk-space, active-keyboard or "
                       + "systemUptime call exists.")
    }

    // MARK: - Collected data

    /// No tracking, and nothing to put in `NSPrivacyTrackingDomains`: the binary
    /// contains no third-party code at all (`docs/legal-and-ip-audit.md` §1), so
    /// there is no ad SDK, no analytics SDK, no IDFA and no ATT prompt.
    func test_the_app_declares_no_tracking() throws {
        let manifest = try manifest()
        XCTAssertEqual(manifest["NSPrivacyTracking"] as? Bool, false)
        XCTAssertEqual(manifest["NSPrivacyTrackingDomains"] as? [String], [])
    }

    /// Precise location is declared collected because route requests carry
    /// coordinates off the device (`RouteService.route`, `RouteService.loop`).
    /// It is *not* declared because of `DriveTrace` — writing to the app's own
    /// Documents directory is not collection under Apple's definition.
    ///
    /// Not linked (no account, no identifier is ever sent), not used for
    /// tracking, app functionality only. These three answers must stay equal to
    /// the App Store Connect nutrition label; `docs/app-store-submission.md`
    /// holds the console copy.
    func test_precise_location_is_declared_unlinked_and_untracked() throws {
        let collected = try XCTUnwrap(
            manifest()["NSPrivacyCollectedDataTypes"] as? [[String: Any]])
        let location = collected.first {
            $0["NSPrivacyCollectedDataType"] as? String
                == "NSPrivacyCollectedDataTypePreciseLocation"
        }
        let entry = try XCTUnwrap(location, "precise location not declared")
        XCTAssertEqual(entry["NSPrivacyCollectedDataTypeLinked"] as? Bool, false)
        XCTAssertEqual(entry["NSPrivacyCollectedDataTypeTracking"] as? Bool, false)
        XCTAssertEqual(entry["NSPrivacyCollectedDataTypePurposes"] as? [String],
                       ["NSPrivacyCollectedDataTypePurposeAppFunctionality"])
    }

    /// Nothing else is collected, and the omissions are deliberate. The typed
    /// address never reaches the backend — `MKLocalSearchCompleter` and
    /// `MKLocalSearch` resolve it against *Apple's* service and only the
    /// resulting coordinates are sent on — so there is no search history, no
    /// contact info, no identifiers and no diagnostics to declare.
    func test_nothing_else_is_declared_collected() throws {
        let collected = try XCTUnwrap(
            manifest()["NSPrivacyCollectedDataTypes"] as? [[String: Any]])
        XCTAssertEqual(collected.compactMap { $0["NSPrivacyCollectedDataType"] as? String },
                       ["NSPrivacyCollectedDataTypePreciseLocation"])
    }
}
