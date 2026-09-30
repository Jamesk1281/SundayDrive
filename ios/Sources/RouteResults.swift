import SwiftUI

/// What the route comes back as, in the bottom sheet: the drive itself, what
/// choosing it costs, what it is like, and — for whoever wants them — the
/// numbers behind that.
///
/// It used to be two summary cards side by side (FASTEST 58 min / SCENIC 96
/// min), a sentence about the difference, and six scenery bars always open.
/// Three readouts of the same trip, none of which said what the drive was
/// *like*. What replaced them:
///
///   96 min · 61 mi                              the trip, once
///   +38 min · 25 beautiful miles                the price of taking it
///   Mostly forest, with 8 miles along the water what it is
///   via Route 2 and the Mohawk Trail
///   ▸ Scenery breakdown                          the instrument, folded away
///
/// The fastest arm is no longer given a card of its own. It has not gone
/// anywhere — it is the `+38 min`, which is the only thing about it anyone was
/// reading, and the slider above already has "Fastest" written at the end of
/// the track that produces it.
struct RouteResults: View {
    let response: RouteResponse

    /// Whether the scenery bars are showing. Closed on arrival: the bars are
    /// the instrument, and the sentence above them is what most drives get
    /// read for.
    @State private var showingBreakdown = false

    var body: some View {
        let scenic = response.scenic.properties
        let comparison = RouteComparison(fastest: response.fastest.properties,
                                         scenic: scenic)
        VStack(alignment: .leading, spacing: 12) {
            headline(comparison)
            description(of: scenic)
            breakdown(of: scenic)
        }
    }

    /// The trip, then its price. Both built from `RouteComparison`'s rounded
    /// integers, so the two lines cannot disagree with each other or with the
    /// bars below.
    private func headline(_ comparison: RouteComparison) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(comparison.totalLine)
                .font(.title2.weight(.semibold))
                // Tabular figures: the slider re-routes under this label, and
                // proportional digits make the whole line jump sideways every
                // time a minute count changes width.
                .monospacedDigit()
            Text(comparison.attributedTradeLine)
                .font(.subheadline)
                .foregroundStyle(comparison.tradeTint)
        }
        .accessibilityElement(children: .combine)
    }

    /// What the drive is like, and which roads it goes down. Absent rather than
    /// blank when the route has nothing to say — see `RouteDescription`.
    @ViewBuilder private func description(of props: RouteProps) -> some View {
        let described = RouteDescription(props)
        if !described.isEmpty {
            VStack(alignment: .leading, spacing: 2) {
                if let character = described.character {
                    Text(character).font(.subheadline)
                }
                if let via = described.via {
                    Text(via).font(.caption).foregroundStyle(.secondary)
                }
            }
        }
    }

    /// The per-feature mileage, behind a disclosure.
    ///
    /// Kept, not deleted: it is the only place the app shows its own working,
    /// and the sentence above it is a summary of exactly these numbers. Hidden
    /// entirely — rather than shown as an empty disclosure — when the route
    /// passes nothing that clears the one-mile floor.
    @ViewBuilder private func breakdown(of props: RouteProps) -> some View {
        let items = props.sceneryBreakdown
        if !items.isEmpty {
            let maxKm = max(1, items.map(\.km).max() ?? 1)
            DisclosureGroup("Scenery breakdown", isExpanded: $showingBreakdown) {
                VStack(alignment: .leading, spacing: 3) {
                    ForEach(items, id: \.label) { item in
                        SceneryBar(label: item.label, km: item.km, maxKm: maxKm)
                    }
                }
                .padding(.top, 6)
            }
            .font(.caption)
            .tint(.secondary)
        }
    }
}

/// The arithmetic behind every number on the results panel.
///
/// It exists so they cannot disagree, which they did: back when the panel was
/// two summary cards, each card rounded its own minutes while the delta was
/// rounded from the raw values, so 57.6 and 106.4 rendered as "58 min",
/// "106 min" and "Scenic adds 49 min" — three individually correct roundings
/// that cannot all be true at once, over a subtraction the reader can do in
/// their head. Everything below is derived from the same rounded integers, so
/// what is printed is arithmetic that checks out against what is beside it.
///
/// The cards are gone (see `RouteResults`); this is not. `totalLine` and
/// `tradeLine` are two readings of the same trip sitting one above the other,
/// which is exactly the arrangement that produced the original bug.
struct RouteComparison {
    let fastestMinutes: Int
    let scenicMinutes: Int
    /// How far the scenic route actually is, in the whole miles `totalLine`
    /// prints. Rounded once here for the same reason the minutes are.
    let scenicMiles: Int
    let fastestScore: Double
    let scenicScore: Double
    /// Whole miles of road scoring 7+ on each arm, rounded once here so the
    /// cards and the sentence cannot print different integers — nil when the
    /// backend predates `beautiful_km`. See `RouteProps.beautiful_km`.
    let fastestBeautifulMiles: Int?
    let scenicBeautifulMiles: Int?

    init(fastest: RouteProps, scenic: RouteProps) {
        fastestMinutes = Int(fastest.minutes.rounded())
        scenicMinutes = Int(scenic.minutes.rounded())
        scenicMiles = scenic.km.wholeMilesFromKm
        fastestScore = fastest.mean_score
        scenicScore = scenic.mean_score
        fastestBeautifulMiles = fastest.beautiful_km?.wholeMilesFromKm
        scenicBeautifulMiles = scenic.beautiful_km?.wholeMilesFromKm
    }

    /// What the scenic route costs, in the minutes the cards are showing.
    var extraMinutes: Int { scenicMinutes - fastestMinutes }

    /// The two mile counts, but only when *both* arms carry one.
    ///
    /// Taken as a pair rather than one at a time so the screen can never end up
    /// with a mile count on one card and a 0–10 score on the other. In practice
    /// both arms come from one response and one backend, so this is nil or
    /// whole; the pair makes that structural rather than assumed.
    var beautifulMiles: (fastest: Int, scenic: Int)? {
        guard let fastest = fastestBeautifulMiles, let scenic = scenicBeautifulMiles
        else { return nil }
        return (fastest, scenic)
    }

    /// The two scores as the cards used to print them, and still the ruler
    /// `scoreMoves` and the fallback sentence measure with.
    var printedFastestScore: String { String(format: "%.1f", fastestScore) }
    var printedScenicScore: String { String(format: "%.1f", scenicScore) }

    /// The drive as it will be driven: "96 min · 61 mi".
    ///
    /// The scenic arm's own totals, not a difference — the first thing anyone
    /// needs off this screen is how long they will be in the car and how far
    /// they are going. The fastest arm's totals are not here because nobody is
    /// driving them; what is worth knowing about that route is what it would
    /// have saved, and that is `tradeLine`.
    var totalLine: String { "\(scenicMinutes) min · \(scenicMiles) mi" }

    /// The price tag: "+38 min · 25 beautiful miles".
    ///
    /// This replaces the caption that used to sit under the slider, "scenery
    /// strength 0.50". A strength is a *parameter* — it says what the router
    /// was asked for, in units belonging to `PrefSlider` and `router.py`, and
    /// there is no action a driver can take on the number 0.50. The same fact
    /// stated as a cost and a thing bought is the whole of what the slider is
    /// for, and it is legible without knowing anything about the app.
    ///
    /// Built from the same rounded integers as `totalLine` and the scenery
    /// bars, for the reason this type exists at all: two numbers on one screen
    /// that disagree by a minute are worse than either of them alone.
    ///
    /// Three cases it must not sell:
    ///
    /// - **The same drive.** At `pref` 0 the server answers with the same route
    ///   twice, and "+0 min · 25 beautiful miles" would price a choice nobody
    ///   made.
    /// - **A route that costs nothing.** The best news this screen ever has is
    ///   scenery for free, and "+0 min" is the wrong way to deliver it.
    /// - **A scenic arm carrying *less* beautiful road than the fastest one** —
    ///   3.1% of 983 sampled trips, the case `summary` documents at length. It
    ///   is not a purchase and must not be phrased as one, so the line states
    ///   what was lost and `tradeTint` stops colouring it like a gain.
    ///
    /// Falls back to `summary` when the backend sends no `beautiful_km`: there
    /// is nothing to price then, and the sentence already says everything a
    /// 0–10 mean supports. See `RouteProps.beautiful_km` — the deployed backend
    /// predates the field, and an app in the store talks to whichever backend
    /// is deployed.
    var tradeLine: String {
        if isSameDrive { return "Same as the fastest route" }
        guard let miles = beautifulMiles else { return summary }

        let cost = extraMinutes > 0 ? "+\(extraMinutes) min" : "No extra time"
        if isWorseThanFastest {
            let lost = miles.fastest - miles.scenic
            return "\(cost) · **\(lost) fewer** beautiful "
                + "\(lost == 1 ? "mile" : "miles") than the fastest route"
        }
        return "\(cost) · **\(miles.scenic) beautiful "
            + "\(miles.scenic == 1 ? "mile" : "miles")**"
    }

    /// Whether the scenic arm comes back with less beautiful road than the
    /// fastest one — the one outcome on this screen that is bad news.
    ///
    /// On the whole-mile counts the cards and the sentence print, not the raw
    /// kilometres: a fall too small to change the printed integers is a fall
    /// nobody can see, and warning about one would contradict the numbers next
    /// to it.
    var isWorseThanFastest: Bool {
        guard let miles = beautifulMiles else { return false }
        return miles.scenic < miles.fastest
    }

    /// `tradeLine` with its markdown bold resolved, for display.
    var attributedTradeLine: AttributedString {
        (try? AttributedString(markdown: tradeLine)) ?? AttributedString(tradeLine)
    }

    /// What colour the price tag is. The accent is the app saying "this is what
    /// you came for", so it is spent only where the trade is one — never on a
    /// route that lost beautiful road, and never on one that is not a choice.
    var tradeTint: Color {
        if isSameDrive { return .secondary }
        return isWorseThanFastest ? .orange : .scenic
    }

    /// Whether the mean score moves at all, at the precision it *would* be
    /// shown to.
    ///
    /// The printed strings, not a tolerance on the raw values — which is what
    /// `abs(difference) < 0.05` was reaching for and missed in both directions.
    /// 4.851 and 4.949 are 0.098 apart and both print "4.9", so the old test
    /// called them different and the sentence claimed a rise the cards
    /// contradicted; 4.949 and 4.951 are 0.002 apart and print "4.9" and "5.0",
    /// so it called them the same while the cards visibly disagreed.
    ///
    /// Since the panel moved to miles this no longer describes what is on
    /// screen — it rounds a number the driver is not shown. That is deliberate
    /// and it is the *only* thing left reading the score: `isSameDrive` is
    /// defined on it, and that definition is measured (see below), so rebuilding
    /// this on the mile counts would silently throw the measurement away. It
    /// stays a question about `mean_score` at one decimal place, which is a
    /// well-defined question whether or not the answer is printed.
    var scoreMoves: Bool { printedFastestScore != printedScenicScore }

    /// Whether the printed mile counts differ — the on-screen question the
    /// sentence is actually built from. Compares the rounded integers the panel
    /// shows, so "turns 3 mi into 4 mi" can never appear above a breakdown
    /// summing to the same number.
    var beautifulMilesMove: Bool {
        guard let miles = beautifulMiles else { return false }
        return miles.fastest != miles.scenic
    }

    /// Whether the two routes read as the same drive. At `pref` 0 the server
    /// answers with the same route twice, and two routes both labelled 4.4 have
    /// nothing to say to each other about scenery whatever their raw scores are.
    ///
    /// Still `mean_score`-based after the panel moved to miles, on purpose. The
    /// 983-pair census replayed *this exact definition*: it fires on 11.5% of
    /// trips, catches 105 of the 106 where the scenic arm genuinely is the
    /// fastest arm, and across all 113 it fires on the largest gain is **0.22
    /// beautiful miles** — which rounds to the same whole mile on both cards
    /// anyway, so it never hides a difference the driver could have seen.
    /// Redefining it on the mile counts would need a new census.
    var isSameDrive: Bool { extraMinutes <= 0 && !scoreMoves }

    /// The trade as a sentence, in markdown.
    ///
    /// No longer the primary readout — `tradeLine` is — but still what the
    /// screen falls back to for a backend that sends no `beautiful_km`, which
    /// is the deployed one. Every case below is therefore still reachable, and
    /// the fall it handles is the same fall `tradeLine` handles in its own
    /// phrasing.
    ///
    /// Four shapes past "same drive". "Scenic adds 0 min and turns 3 mi of
    /// beautiful road into 3 mi" is a sentence about nothing; a scenic route
    /// that costs no extra time is the best news this screen ever has to
    /// deliver and must not be phrased as a charge of zero; a route that costs
    /// time and moves the number nowhere should say so rather than claim a
    /// gain; and the scenic route can come back with *less* beautiful road than
    /// the fastest one.
    ///
    /// That last case is the point of counting miles rather than averaging a
    /// score. On 3.1% of 983 sampled trips the scenic arm is slower and has
    /// less beautiful road, and `mean_score` *rose* on 27 of those 30 — a
    /// shorter route with a better per-kilometre average genuinely scores
    /// higher — so the old sentence read "adds 2 min and raises scenery 4.1 →
    /// 4.7" about a trip where the good road went down. `_no_worse_than_fastest`
    /// in `server/app.py` now catches the six that were worse on the score too;
    /// the other 24 still ship and the sentence has to describe them honestly.
    /// So the fall is a plain statement, not clamped to zero and not an error.
    ///
    /// Falls back to the 0–10 sentence when the backend did not send
    /// `beautiful_km`, which is the same reasoning as `_no_worse_than_fastest`
    /// above: an app in the store talks to whichever backend is deployed,
    /// including an older one.
    var summary: String {
        if isSameDrive {
            return "**Same as the fastest route** at this setting."
        }
        guard let miles = beautifulMiles else { return scoreSummary }

        let from = "**\(miles.fastest) mi**", to = "**\(miles.scenic) mi**"
        if !beautifulMilesMove {
            // Past `isSameDrive` this is either time spent for no more good
            // road, or — when the mean moved but the whole miles did not — a
            // genuinely different route that happens to tie on the count.
            return extraMinutes > 0
                ? "Scenic adds **\(extraMinutes) min** and leaves beautiful road at \(to)"
                : "A different route with the same \(to) of beautiful road, at no extra time"
        }
        // "turns A into B" reads in both directions, and the fall gets a word
        // of its own so it cannot be skimmed past as a gain.
        let change = miles.scenic > miles.fastest
            ? "turns \(from) of beautiful road into \(to)"
            : "**cuts** beautiful road from \(from) to \(to)"
        if extraMinutes <= 0 {
            return "Scenic \(change) **at no extra time**"
        }
        return "Scenic adds **\(extraMinutes) min** and \(change)"
    }

    /// The sentence as it shipped before the cards counted miles, kept whole
    /// for backends that predate `beautiful_km`. Reached only through
    /// `summary`, and past its `isSameDrive` check.
    var scoreSummary: String {
        let scores = "**\(printedFastestScore)** → **\(printedScenicScore)**"
        // Past `isSameDrive`, a score that has not moved implies added minutes.
        if !scoreMoves {
            return "Scenic adds **\(extraMinutes) min** and leaves scenery "
                + "at **\(printedScenicScore)**"
        }
        let verb = scenicScore > fastestScore ? "raises" : "**lowers**"
        if extraMinutes <= 0 {
            return "Scenic \(verb) scenery \(scores) **at no extra time**"
        }
        return "Scenic adds **\(extraMinutes) min** and \(verb) scenery \(scores)"
    }

    /// `summary` with its markdown bold resolved, for display.
    var attributedSummary: AttributedString {
        (try? AttributedString(markdown: summary)) ?? AttributedString(summary)
    }
}

/// One labeled bar in the scenery breakdown ("forest  22 mi"), filled in
/// proportion to the longest feature so lengths are easy to compare.
struct SceneryBar: View {
    let label: String
    let km: Double
    let maxKm: Double

    // The label and value columns line the bars up, but a width in fixed points
    // clips its own text as soon as the user raises the system text size.
    // @ScaledMetric grows them with it, so the column survives and the bars stay
    // aligned.
    @ScaledMetric(relativeTo: .caption2) private var labelWidth: CGFloat = 74
    @ScaledMetric(relativeTo: .caption2) private var valueWidth: CGFloat = 40

    var body: some View {
        HStack(spacing: 8) {
            Text(label).font(.caption2).foregroundStyle(.secondary)
                .frame(width: labelWidth, alignment: .leading)
            GeometryReader { geo in
                Capsule().fill(Color.scenic)
                    .frame(width: geo.size.width * (km / maxKm), height: 6)
                    .frame(maxHeight: .infinity, alignment: .center)
            }
            .frame(height: 10)
            Text("\(km.wholeMilesFromKm) mi").font(.caption2)
                .frame(width: valueWidth, alignment: .trailing)
        }
        // Read as one fact. Left to itself VoiceOver announces the label, then a
        // decorative bar, then the number, as three separate stops.
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(label), \(km.wholeMilesFromKm) miles")
    }
}
