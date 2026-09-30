import Foundation

/// What a route is *like*, in the words someone would use telling a friend
/// where they went: "Mostly forest, with 8 miles along the water", "via Route 2
/// and the Mohawk Trail".
///
/// This is the half of the results the six scenery bars never covered. A bar
/// chart of forest/water/hills is an instrument reading — it answers "how much
/// of each" for a reader who already knows what the rows mean. It does not
/// answer "what is this drive", which is the question actually being asked by
/// someone deciding whether to spend 38 extra minutes on it. The bars are still
/// there, one disclosure away, for whoever wants the numbers.
///
/// Everything here comes from fields the route already carries — `scenery_km`
/// and `steps` — so it costs no extra request and cannot disagree with the
/// breakdown underneath it.
struct RouteDescription {

    /// "Mostly forest, with 8 miles along the water." Nil when the route passes
    /// nothing that survives `sceneryBreakdown`'s one-mile floor.
    let character: String?

    /// "via Route 2 and the Mohawk Trail". Nil when no single road carries
    /// enough of the drive to be worth naming.
    let via: String?

    var isEmpty: Bool { character == nil && via == nil }

    init(_ props: RouteProps) {
        character = Self.character(of: props)
        via = Self.via(of: props)
    }

    // MARK: - What the drive passes

    /// How each scenery feature is spoken about, in the two grammatical shapes
    /// the sentence needs: as a subject ("Mostly **forest**") and as a
    /// prepositional phrase ("8 miles **along the water**").
    ///
    /// Keyed by the labels `RouteProps.sceneryBreakdown` emits, which are the
    /// server's `SCENERY_BREAKDOWN` keys. A key missing here falls back to the
    /// raw label rather than dropping the clause: a scenery type the server
    /// learns before the app does should read a little flat, not vanish.
    private static let vocabulary: [String: (subject: String, phrase: String)] = [
        "forest/park": ("forest",           "through forest"),
        "water":       ("lakes and rivers", "along the water"),
        "coast":       ("coast",            "along the coast"),
        "hills":       ("hills",            "over hills"),
        "farmland":    ("farmland",         "past farmland"),
        "town":        ("town centers",     "through town centers"),
    ]

    /// The share of the route a feature has to cover before the sentence will
    /// call the drive "mostly" that.
    private static let majorityShare = 0.5

    /// The sentence.
    ///
    /// "Mostly" is a claim, so it is only made when it is true: the leading
    /// feature has to cover at least half the route's length, and otherwise the
    /// clause states its mileage instead. That guard is not pedantry — the
    /// `scenery_km` values *overlap* (a lakeside road through woods counts in
    /// both `water` and `forest/park`), so they can sum past the route's own
    /// length, and the leading value's share of `km` is the only reading of one
    /// that means anything on its own.
    ///
    /// Two clauses at most. A third is where this stops being a sentence and
    /// starts being the bar chart again, in prose, which is worse than the bar
    /// chart.
    private static func character(of props: RouteProps) -> String? {
        // Ties fall back to the order `sceneryBreakdown` hands them over in,
        // which is the server's display order. `sorted(by:)` is not documented
        // as stable, so two features on the same mileage — which is common once
        // the values are rounded to whole miles for printing — could otherwise
        // swap clauses between one launch and the next on the same route.
        let ranked = props.sceneryBreakdown.enumerated()
            .sorted { $0.element.km != $1.element.km
                        ? $0.element.km > $1.element.km
                        : $0.offset < $1.offset }
            .map(\.element)
        guard let top = ranked.first else { return nil }

        let lead: String
        if props.km > 0, top.km / props.km >= majorityShare {
            lead = "Mostly \(vocabulary[top.label]?.subject ?? top.label)"
        } else {
            lead = milesClause(top)
        }
        guard let second = ranked.dropFirst().first else { return lead + "." }
        return "\(lead), with \(milesClause(second))."
    }

    /// "8 miles along the water" — a feature's mileage and where it takes you.
    ///
    /// Never "0 miles" and never "1 miles": `sceneryBreakdown` has already
    /// dropped everything that would round to zero, which is the same rule
    /// `SceneryBar` labels itself by, so this and the bars cannot print
    /// different numbers for the same feature.
    private static func milesClause(_ item: (label: String, km: Double)) -> String {
        let miles = item.km.wholeMilesFromKm
        return "\(miles) \(miles == 1 ? "mile" : "miles") "
            + (vocabulary[item.label]?.phrase ?? item.label)
    }

    // MARK: - Which roads it goes down

    /// The share of the drive a road has to carry before it is named.
    ///
    /// Without a floor the line fills with the quarter-mile connectors at each
    /// end — the roads a route touches and nobody would mention — which is the
    /// opposite of what it is for. With it, a trip made entirely of short hops
    /// names nothing and says nothing, which is the right answer for a trip
    /// that has no road to speak of.
    private static let minimumShare = 0.08

    /// "via Route 2 and the Mohawk Trail".
    ///
    /// Built from the maneuver list, where each step carries the road it puts
    /// you *onto* together with how far that instruction carries you — so
    /// summing `distance_m` under `name` is the distance spent on each road,
    /// and a road the route leaves and rejoins adds up across both passes.
    /// (`NavigationModel.currentRoad` reads the same pairing from the other
    /// end, one step back.)
    private static func via(of props: RouteProps) -> String? {
        var metersByRoad: [String: Double] = [:]
        for step in props.steps {
            guard let name = step.name, !name.isEmpty else { continue }
            metersByRoad[name, default: 0] += step.distance_m
        }
        let total = metersByRoad.values.reduce(0, +)
        guard total > 0 else { return nil }

        // Ordered by distance, and by name where two roads tie: a dictionary
        // has no order of its own, and the same route must not name its roads
        // in a different order from one launch to the next.
        let named = metersByRoad
            .filter { $0.value >= total * minimumShare }
            .sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }
            .prefix(2)
            .map(\.key)

        switch named.count {
        case 0:  return nil
        case 1:  return "via \(named[0])"
        default: return "via \(named[0]) and \(named[1])"
        }
    }
}
