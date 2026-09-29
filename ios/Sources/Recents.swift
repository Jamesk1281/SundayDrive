import CoreLocation
import Foundation

/// The last handful of destinations, so the first screen has something on it.
///
/// New. The app stored nothing before this: every trip was retyped, including
/// the one you took last Sunday. `UserDefaults` rather than a file or a store,
/// for the same reason `VoiceCatalogue` uses it — this is a few hundred bytes
/// of convenience, and losing it costs the user one search.
///
/// Deliberately *destinations only*, not trips. A start point is usually where
/// you happen to be and is worth nothing tomorrow; a destination is a place.
struct Recent: Codable, Identifiable, Equatable {
    let name: String
    /// The town or region under the name, when the placemark carried one.
    let subtitle: String
    let latitude: Double
    let longitude: Double

    var id: String { "\(name)|\(latitude),\(longitude)" }
    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

@MainActor
enum Recents {
    private static let key = "recentDestinations"

    /// Five. Enough that last weekend is still there, short enough that the
    /// list never needs its own screen or a scroll.
    static let limit = 5

    static func load() -> [Recent] {
        guard let data = UserDefaults.standard.data(forKey: key),
              let rows = try? JSONDecoder().decode([Recent].self, from: data)
        else { return [] }
        return rows
    }

    /// Record a destination, most recent first, de-duplicated by name so the
    /// same place searched twice does not fill the list.
    static func remember(_ recent: Recent) {
        var rows = load().filter { $0.name != recent.name }
        rows.insert(recent, at: 0)
        if rows.count > limit { rows = Array(rows.prefix(limit)) }
        if let data = try? JSONEncoder().encode(rows) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }

    static func clear() { UserDefaults.standard.removeObject(forKey: key) }
}
