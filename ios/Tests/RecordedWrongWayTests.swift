import XCTest
@testable import SundayDrive

/// The drive that P-05 came from, replayed: `drive-2026-10-06-192759`, where
/// about 2.6 h in the car drove its own route backwards for about 1.9 km and
/// nothing noticed (docs/mid-drive-recovery.md).
///
/// Replayed `asRecorded`, because the ordinary replay cannot reach that
/// stretch: the car leaves its line just before it, the replay's request is
/// answered with the next recorded route — one the drive was given 40 minutes
/// later, somewhere else — and from there it follows the wrong line. On the
/// road nothing landed until then, so every request in between failed (P-04),
/// and that is what `asRecorded` reproduces.
///
/// Skips where the trace is not on disk, like the rest of the replays.
@MainActor
final class RecordedWrongWayTests: XCTestCase {

    private static let name = "drive-2026-10-06-192759.ndjson"

    /// Seconds from the drive's first fix to the first fix of the run against
    /// the line, and the run's last fix on the line, measured from the trace
    /// (211 fixes in a row within 30 m of the line, with a course 120 degrees
    /// or more against every pass of it there and none within 60, at a stated
    /// 5 m; the first few at a crawl, which the detector does not read).
    private static let runStarts: TimeInterval = 9_274
    private static let runEnds: TimeInterval = 9_484

    func test_the_recorded_wrong_way_run_is_caught_within_20_s() async throws {
        guard let drive = DriveReplay.recordings().first(where: { $0.name == Self.name })
        else { throw XCTSkip("\(Self.name) is not on this machine") }
        let outcome = await DriveReplay.run(drive, speaker: VoiceGuideTests.FakeSpeaker(),
                                            mode: .asRecorded)
        let during = outcome.wrongWayAt.filter { $0 >= Self.runStarts && $0 <= Self.runEnds }
        XCTAssertEqual(during.count, 1, "said \(outcome.wrongWayAt)")
        XCTAssertLessThanOrEqual((during.first ?? .infinity) - Self.runStarts, 20,
                                 "caught late, or not at all")
        XCTAssertEqual(outcome.wrongWayAt.count, 1, "fired elsewhere on the drive too")
        // And the failed requests around it were said, once per episode,
        // rather than swallowed.
        XCTAssertGreaterThan(outcome.failedRequests, 0)
        XCTAssertTrue(outcome.said.contains("No connection. Head back to your route."))
    }
}
