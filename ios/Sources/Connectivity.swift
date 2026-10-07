import Foundation
import Network

/// Whether the phone has a network path at all, and a callback for when one
/// comes back.
///
/// Two jobs and only two (docs/mid-drive-recovery-plan.md, section 3.1): to
/// tell a failed reroute with no path ("No signal") from one with a path that
/// carried nothing ("No connection"), and to trigger a retry the moment a path
/// returns. It never gates a request. A path can be "satisfied" while nothing
/// gets through — a weak signal, a captive portal, our server down — and only
/// the request finds that out, which is why `NavigationModel` keeps a timer
/// for the satisfied case.
///
/// One for the app's lifetime, owned by `RouteModel` and handed to each drive.
/// `waitsForConnectivity` stays off in `RouteService` either way: a request
/// parked until the network returned would plan from where the car used to be,
/// and the callback here is what replaces the waiting, with a fresh request
/// from the newest fix.
@MainActor
final class Connectivity {
    /// True until the monitor has said otherwise. The first update lands
    /// within milliseconds of `start`, and assuming a path until then means a
    /// failure in that window reads as "No connection" rather than "No
    /// signal" — the milder of the two claims.
    private(set) var hasPath = true

    /// Called on the main actor when the path goes from unsatisfied to
    /// satisfied. Not on every update: an interface change on a path that
    /// never went away is not a signal coming back.
    var onRestored: (() -> Void)?

    private let monitor = NWPathMonitor()

    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            let satisfied = path.status == .satisfied
            Task { @MainActor [weak self] in self?.update(satisfied) }
        }
        monitor.start(queue: DispatchQueue(label: "app.sundaydrive.connectivity"))
    }

    deinit { monitor.cancel() }

    private func update(_ satisfied: Bool) {
        let restored = satisfied && !hasPath
        hasPath = satisfied
        if restored { onRestored?() }
    }
}
