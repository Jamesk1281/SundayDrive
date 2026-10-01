import CoreLocation

extension Double {
    /// The backend speaks metric; the app is Massachusetts-only, so every
    /// distance the user sees is in miles. Converted at the view layer so the
    /// numbers coming off the API stay in their original units.
    var milesFromKm: Double { self * 0.621371 }

    /// Kilometers as the whole number of miles the UI puts on screen.
    ///
    /// Rounded rather than truncated, and — the point of it existing — shared
    /// with the filter that decides whether a scenery row appears at all. Those
    /// two used to measure different things: `sceneryBreakdown` dropped a
    /// feature at `km > 0` while the label truncated `Int(km.milesFromKm)`, so
    /// anything under 1.6 km survived the filter and then rendered as "0 mi".
    /// Seen on a real loop as a "farmland  0 mi" row beside a dot-sized bar,
    /// claiming a feature the drive did not have. One rule, read from both
    /// sides, cannot drift like that again.
    ///
    /// Truncation was also just wrong on its own terms: a 24.9 km route reads
    /// 15 mi truncated and 16 mi at 15.5.
    var wholeMilesFromKm: Int { Int(milesFromKm.rounded()) }
}

extension CLLocation {
    /// Straight-line distance in meters from this location to a coordinate.
    func distance(to coordinate: CLLocationCoordinate2D) -> Double {
        distance(from: CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude))
    }
}

extension CLLocationCoordinate2D {
    /// `CLLocationCoordinate2D` isn't `Equatable`; this covers the one thing we
    /// ask of it — "is this still the same pin I set earlier?".
    func matches(_ other: CLLocationCoordinate2D) -> Bool {
        latitude == other.latitude && longitude == other.longitude
    }
}

/// Where a driver sits relative to a route line. All values in meters.
struct RouteProgress {
    /// Perpendicular distance to the nearest point of the line — how far off
    /// route we are.
    let offRoute: Double
    /// Distance still to drive, measured *along* the line from that nearest
    /// point to the end. This is what the remaining-distance and ETA readouts
    /// are built from, so it has to follow the road rather than fly straight to
    /// the destination.
    let remaining: Double
    /// How far along the line the driver has been matched to. Feed this back in
    /// as `notBefore` on the next fix to keep the match moving forwards.
    let travelled: Double
}

/// How much further off a segment may be than the nearest one and still be a
/// candidate, for `progress`'s continuity rule.
///
/// Only a genuine tie. Two passes over one OSM way are the same coordinates,
/// so the offsets to them agree to nanometres, and a maneuver's coordinate is
/// rounded 3-6 cm off its vertex; a metre covers both. It is deliberately not
/// wide enough to reach the other carriageway of a divided road. Measured on
/// a real trace (2026-08-25, a U-turn on Southwest Cutoff), a 10 m window let
/// a match that had run 88 m ahead on the return carriageway hold the car
/// there, parked 1.9 m from the outbound one and 8.9 m from the return —
/// the nearest road is the right answer there, and strict nearest finds it.
let progressTieMeters: Double = 1

/// Metres of offset that one metre along the line is worth, between the
/// candidates `progressTieMeters` lets through.
///
/// Decisive between passes, which are hundreds of metres apart along the line
/// with offsets equal to nanometres. Not decisive within one: at a bend, a fix
/// a few metres off has a nearest point on each of two adjacent segments, 5 m
/// apart along the line and up to a metre apart in offset, and ranking those
/// by along-line distance alone took the one behind — measured on the
/// 2026-08-14 evening trace, where it held the banner on "Turn left to stay on
/// Washington Street" one fix too long and lost the Pearl Street prepare.
let progressContinuityWeight: Double = 0.05

/// Project a point onto a polyline: how far off it is, and how much line is
/// left ahead of it.
///
/// We check every *segment* (not just the shape points), so a long straight
/// stretch with far-apart vertices doesn't make a driver on the line look "off
/// route". Each segment is measured in its own local east/north meter frame —
/// per-segment rather than one frame for the whole route, because a 60 km route
/// spans enough latitude that a single east-west scale factor would misjudge
/// lengths at the far end by a couple of percent.
///
/// `notBefore` is how far along the driver is already known to be. Segments that
/// end before it are not considered, which is what makes the match work on a
/// route that comes back on itself — and scenic routes do that constantly, since
/// an out-and-back detour is often the prettiest way to spend ten extra minutes.
/// Without it, a driver on the return leg matches the outbound one they drove
/// twenty minutes ago, and the distance remaining jumps back up. Pass a little
/// less than the last known value so GPS jitter can nudge backwards; pass 0
/// before the driver has joined the route, when nothing is known yet.
///
/// `notBefore` alone does not separate two passes that are both ahead of it,
/// and on a road a route drives twice the two passes are the *same
/// coordinates*: the car is equidistant from both to within floating-point
/// noise, so "strictly nearest" picks a pass at random. Measured on the
/// simulated loops (2026-09-30), the first fix matched the closing leg 45 km
/// on, a maneuver at the start was placed at the end, and a car mid-loop
/// jumped 10 km to the return pass.
///
/// So the nearest segment does not win outright. Every segment within
/// `progressTieMeters` of the nearest is a candidate, and the one nearest
/// along the line to `near` — where the driver already is — is taken, with
/// ground behind it counting double and the offset still weighed in
/// (`progressContinuityWeight`). That is continuity, not a tie-break:
/// with real GPS the offsets to two identical passes still agree exactly,
/// while which one gets "strictly nearer" is decided by float noise, and only
/// "which one were we on" is stable from fix to fix. Anything further off
/// than the tolerance is a different road, and the nearest road wins as it
/// always did.
///
/// A gap in the fixes does not trip this up. After a tunnel the driver is
/// legitimately kilometres on, and the road where they were is not within the
/// tolerance of where they are now unless the route really does come back to
/// it — so no forward ceiling is needed, and none is applied.
///
/// `near` defaults to `notBefore`, which is right for a caller with a floor
/// just behind the driver; one asking the unconstrained question passes the
/// driver's position explicitly.
func progress(of point: CLLocationCoordinate2D,
              along line: [CLLocationCoordinate2D],
              notBefore: Double = 0,
              near: Double? = nil) -> RouteProgress {
    guard line.count >= 2 else {
        let here = CLLocation(latitude: point.latitude, longitude: point.longitude)
        let only = line.first.map { here.distance(to: $0) } ?? .infinity
        return RouteProgress(offRoute: only, remaining: 0, travelled: 0)
    }

    let metersPerDegLat = 111_320.0
    var best = Double.infinity
    var travelled = 0.0        // length of the line before the current segment
    // Per segment: how far off it the point is, and how far along the line its
    // nearest point sits. Infinity for a segment wholly behind `notBefore`.
    var distances = [Double](repeating: .infinity, count: line.count - 1)
    var alongs = [Double](repeating: 0, count: line.count - 1)
    var ends = [Double](repeating: 0.5, count: line.count - 1)    // the clamped t

    for i in 0 ..< line.count - 1 {
        let p = line[i], q = line[i + 1]
        // East-west scale at this segment's own latitude.
        let metersPerDegLon = 111_320.0 * cos((p.latitude + q.latitude) / 2 * .pi / 180)
        func offset(_ c: CLLocationCoordinate2D) -> (x: Double, y: Double) {
            ((c.longitude - point.longitude) * metersPerDegLon,
             (c.latitude - point.latitude) * metersPerDegLat)
        }

        let a = offset(p), b = offset(q)
        let dx = b.x - a.x, dy = b.y - a.y
        let lengthSquared = dx * dx + dy * dy
        let length = lengthSquared.squareRoot()

        // Project the origin (our point) onto segment AB, clamped to its ends.
        let t = lengthSquared == 0 ? 0 : max(0, min(1, -(a.x * dx + a.y * dy) / lengthSquared))
        let cx = a.x + t * dx, cy = a.y + t * dy
        let distance = (cx * cx + cy * cy).squareRoot()

        // Segments wholly behind us belong to an earlier pass along the same
        // road, not to where the driver is now.
        if travelled + length >= notBefore {
            distances[i] = distance
            alongs[i] = travelled + t * length
            ends[i] = t
            best = min(best, distance)
        }
        travelled += length
    }

    // Of the segments that tie for nearest, the one nearest along the line to
    // where the driver already is — with the offset still counted, so that
    // within one pass the nearer of two segments a few metres apart wins.
    // Ground behind the anchor counts double: the driver's position is a
    // running maximum, so through a U-turn it waits at the turn while the car
    // drives away from it, and the two legs sit exactly as far either side.
    let limit = best + progressTieMeters
    let anchor = near ?? notBefore
    var chosen = -1            // the matched segment
    var chosenCost = Double.infinity

    // A segment matched at its far end is matched at the vertex the next
    // segment starts from, and if that one is at least as near, it is the same
    // place on the same road and not another pass. Kept as a candidate, it is
    // the one nearer the anchor, and pins a car just past a maneuver's vertex
    // to the vertex itself — which `firstStepAhead` reads as not yet past
    // (measured on the 2026-08-14 traces: a fix late at four maneuvers, and
    // two prepares lost). Likewise a near end with the previous segment
    // strictly nearer. Equal on both sides is a car outside a corner, whose
    // nearest point really is the vertex, so one of the two survives.
    let last = distances.count - 1
    for i in distances.indices where distances[i] <= limit {
        if ends[i] == 1, i < last, distances[i + 1] <= distances[i] { continue }
        if ends[i] == 0, i > 0, distances[i - 1] < distances[i] { continue }
        let gap = alongs[i] >= anchor ? alongs[i] - anchor : 2 * (anchor - alongs[i])
        let cost = distances[i] + progressContinuityWeight * gap
        if cost < chosenCost { chosen = i; chosenCost = cost }
    }

    // `notBefore` ran past the end of the line: there is nothing ahead to match
    // against, so the driver is at the end of it.
    guard chosen >= 0 else {
        let here = CLLocation(latitude: point.latitude, longitude: point.longitude)
        return RouteProgress(offRoute: line.last.map { here.distance(to: $0) } ?? .infinity,
                             remaining: 0, travelled: travelled)
    }
    let along = alongs[chosen]
    return RouteProgress(offRoute: distances[chosen],
                         remaining: max(0, travelled - along),
                         travelled: along)
}

enum TimeText {
    /// "48 min", or "1 hr 30" once it is worth splitting. Used by the loop
    /// dial's estimate, the loop card and the arrival card, so the three cannot
    /// print the same duration three ways.
    static func compact(minutes: Double) -> String {
        let total = max(0, Int(minutes.rounded()))
        guard total >= 60 else { return "\(total) min" }
        let h = total / 60, m = total % 60
        return m == 0 ? "\(h) hr" : "\(h) hr \(m)"
    }
}

enum CountText {
    /// "1 mile", "3 miles". For the few places a count is spelled out in
    /// full, which need the plural that the "mi" and "min" abbreviations
    /// everywhere else do not: a short loop read "1 miles of it beautiful".
    static func of(_ count: Int, _ unit: String) -> String {
        "\(count) \(unit)\(count == 1 ? "" : "s")"
    }
}
