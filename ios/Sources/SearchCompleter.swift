import MapKit
import Observation

/// Live address autocomplete, wrapping Apple's `MKLocalSearchCompleter` — the
/// same engine behind Apple Maps' search. You feed it the text as the user
/// types; it streams back suggestions (a title + subtitle, e.g. "Northeastern
/// University" / "Boston, MA") through its delegate, which we publish here for
/// SwiftUI to show in a dropdown.
///
/// A suggestion is only a *label*, not a location yet — resolving it to actual
/// coordinates is a second step (see `RouteModel.choose`).
@Observable
final class SearchCompleter: NSObject, MKLocalSearchCompleterDelegate {
    /// Suggestions for the most recent query fragment.
    var suggestions: [MKLocalSearchCompletion] = []

    private let completer = MKLocalSearchCompleter()

    override init() {
        super.init()
        completer.delegate = self
        completer.resultTypes = [.address, .pointOfInterest]
        completer.region = .coverageEnvelope
    }

    /// Refresh suggestions for the current text, ranked around `region`.
    ///
    /// The caller passes the part of the map the user is looking at (or is
    /// standing in), because the completer ranks by distance from that region's
    /// center: bias it statewide and a search from Needham surfaces places in
    /// central Massachusetts first. A region that shows none of the covered
    /// area is swapped for the coverage envelope (`rank(around:)`), so a phone
    /// in Toronto is not offered only Toronto's main streets, which the filter
    /// below would then throw away. Very short fragments are ignored
    /// so we don't show noise for one or two letters.
    func update(for fragment: String, near region: MKCoordinateRegion) {
        let query = fragment.trimmingCharacters(in: .whitespaces)
        guard query.count >= 2 else {
            suggestions = []
            return
        }
        completer.rank(around: region)
        completer.queryFragment = query
    }

    /// Hide the dropdown (after the user picks a suggestion or dismisses it).
    func clear() {
        suggestions = []
        completer.queryFragment = ""
    }

    // MARK: - MKLocalSearchCompleterDelegate (called on the main thread)

    /// Only places in the covered area (`Coverage.allowsSuggestion`), filtered
    /// here rather than at display so the field's five rows are five that can
    /// be used. Filtered after `prefix(5)`, a place in Ontario would still cost
    /// a row.
    func completerDidUpdateResults(_ completer: MKLocalSearchCompleter) {
        suggestions = completer.results.filter {
            Coverage.allowsSuggestion(title: $0.title, subtitle: $0.subtitle)
        }
    }

    func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) {
        suggestions = []
    }
}
