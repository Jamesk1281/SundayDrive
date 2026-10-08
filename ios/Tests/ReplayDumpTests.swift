import XCTest
@testable import SundayDrive

/// Replay every recorded drive and dump what it did, one NDJSON line per
/// drive: every utterance, every reroute request and when, every wrong-way
/// detection, the arrival. Diff the dump from a base build against a branch
/// and explain every difference — the check that caught what the personas
/// missed on 2026-10-01 (docs/loop-matching-fix.md, and
/// docs/mid-drive-recovery.md for how it was used there).
///
/// Off unless `SUNDAYDRIVE_REPLAY_OUT` names the file to write, which on the
/// command line is `TEST_RUNNER_SUNDAYDRIVE_REPLAY_OUT=<path>`.
/// `SUNDAYDRIVE_REPLAY_MODE=asRecorded` replays with `DriveReplay.Mode.asRecorded`.
@MainActor
final class ReplayDumpTests: XCTestCase {
    func test_dump_replays() async throws {
        guard let out = ProcessInfo.processInfo.environment["SUNDAYDRIVE_REPLAY_OUT"] else {
            throw XCTSkip("set SUNDAYDRIVE_REPLAY_OUT (TEST_RUNNER_SUNDAYDRIVE_REPLAY_OUT) to dump")
        }
        let drives = DriveReplay.recordings()
        guard !drives.isEmpty else { throw XCTSkip("no traces") }
        var text = ""
        for (i, drive) in drives.enumerated() {
            let speaker = VoiceGuideTests.FakeSpeaker()
            let mode: DriveReplay.Mode =
                ProcessInfo.processInfo.environment["SUNDAYDRIVE_REPLAY_MODE"] == "asRecorded"
                ? .asRecorded : .inOrder
            let o = await DriveReplay.run(drive, speaker: speaker, mode: mode)
            let row: [String: Any] = [
                "i": i, "name": o.name, "arrived": o.arrived, "fixes": o.fixesFed,
                "stalledAfter": o.stalledAfter ?? -1,
                "replies": o.repliesGiven, "same": o.sameLineReplies, "failed": o.failedRequests,
                "requestsAt": o.requestsAt, "wrongWayAt": o.wrongWayAt,
                "wrongWayTimeoutsAt": o.wrongWayTimeoutsAt,
                "describable": o.describableFixes,
                "repeats": o.repeatsWithoutARouteChange.count, "said": o.said, "saidAt": o.saidAt,
            ]
            let data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
            text += String(decoding: data, as: UTF8.self) + "\n"
        }
        try text.write(toFile: out, atomically: true, encoding: .utf8)
    }
}
