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
        let kept = completer.results.filter {
            Coverage.allowsSuggestion(title: $0.title, subtitle: $0.subtitle)
        }
        let rows = Self.distinct(kept.map { (title: $0.title, subtitle: $0.subtitle) })
        suggestions = rows.map { kept[$0] }
    }

    /// The indices of the rows worth showing: the first of each place, in
    /// order. The completer can answer one place several times, as a point of
    /// interest and as addresses. On 2026-10-20 "Santa Cruz Beach Boardwalk"
    /// filled three of the five rows, under "Santa Cruz, CA, United States",
    /// "400 Beach St, Santa Cruz, CA 95060, United States" and the same
    /// address with two spaces before the ZIP (docs/review-fixes-app.md,
    /// item 5).
    ///
    /// Two rows are one place when their titles match and one subtitle is the
    /// other, or ends with it: the town is the tail of the address. Compared
    /// without case, accents, ZIP codes or runs of spaces, which are not what
    /// a driver reads. Two Main Streets in two towns stay two rows.
    static func distinct(_ rows: [(title: String, subtitle: String)]) -> [Int] {
        var seen: [String: [String]] = [:]   // title -> subtitles already shown
        var kept: [Int] = []
        for (index, row) in rows.enumerated() {
            let title = normalised(row.title), subtitle = normalised(row.subtitle, dropZIP: true)
            let shown = seen[title, default: []]
            if shown.contains(where: { samePlace($0, subtitle) }) { continue }
            seen[title, default: []].append(subtitle)
            kept.append(index)
        }
        return kept
    }

    private static func normalised(_ text: String, dropZIP: Bool = false) -> String {
        var out = text.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: nil)
        if dropZIP { out = out.replacing(#/\b\d{5}(?:-\d{4})?\b/#, with: "") }
        out = out.replacing(#/\s+/#, with: " ").replacing(" ,", with: ",")
        return out.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func samePlace(_ a: String, _ b: String) -> Bool {
        a == b || a.isEmpty || b.isEmpty || a.hasSuffix(", " + b) || b.hasSuffix(", " + a)
    }

    func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) {
        suggestions = []
    }
}
