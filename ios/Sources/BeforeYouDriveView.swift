import SwiftUI

/// **Before you drive** — what the app does, the route-guidance notice, and
/// its limits in plain words.
///
/// Shown once, on first launch, and permanently reachable from Sources. Two
/// ways in, **one view, one copy of the string**.
///
/// The notice is fixed by contract (ADPLA §3.3.3(F)(iii)) and pinned character
/// for character by two tests. It used to live at the bottom of the credits
/// sheet, which is correct, compliant, and read by nobody — a clause that
/// protects a driver and is filed where drivers never look protects nobody.
/// Giving it a screen at the moment it applies is the whole change, and the
/// obligation turns out to be a reasonable host for the app's honest limits:
/// stating them once, up front, is cheaper than a driver discovering them on a
/// back road in Maine.
///
/// Showing it here does **not** by itself discharge §3.3.3(F)(iii), which asks
/// for an *end user licence agreement* carrying the text. That still has to be
/// filed in App Store Connect before submission — see
/// `docs/app-store-submission.md`.
struct BeforeYouDriveView: View {
    /// Nil when the screen was reached from Sources rather than shown at first
    /// launch: then it is a page you close, not a thing you acknowledge.
    var onAcknowledge: (() -> Void)?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 17) {
                    Text("Before you drive").sectionLabel(.alert)

                    // What the app does, first. The screen used to open on
                    // six things it does not do, and one of them told most of
                    // the country it was untested where they live
                    // (docs/review-fixes-app.md, item 6).
                    Text(Self.whatItDoes)
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(Color.ink)
                        .fixedSize(horizontal: false, vertical: true)

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Route guidance").sectionLabel(.alert)
                        Text(DataSources.routeGuidanceNotice)
                            .font(.system(size: 13, weight: .medium))
                            .lineSpacing(2)
                            .foregroundStyle(Color.ink)
                            .textSelection(.enabled)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .background(Color.card, in: RoundedRectangle(cornerRadius: Metric.controlRadius))
                    .overlay {
                        RoundedRectangle(cornerRadius: Metric.controlRadius)
                            .stroke(Color.alert, lineWidth: 1.5)
                    }

                    Text("Good to know").sectionLabel()

                    ForEach(Self.limits, id: \.head) { item in limit(item.head, item.body) }

                    if onAcknowledge != nil {
                        Text("Also in Sources, any time.")
                            .font(.system(size: 12))
                            .foregroundStyle(Color.ink3)
                    }
                }
                .padding(Metric.margin)
            }
            .scrollBounceBehavior(.basedOnSize)

            PrimaryButton(title: onAcknowledge == nil ? "Done" : "Got it") {
                onAcknowledge?()
                dismiss()
            }
            .padding(.horizontal, Metric.margin)
            .padding(.bottom, 12)
        }
        .background(Color.paper)
    }

    /// The first line on the screen. docs/review-fixes-app.md lists every
    /// string here, with what it replaced.
    static let whatItDoes = "Sunday Drive finds the beautiful way: a scenic route to "
        + "where you’re going, or a loop back to where you started."

    /// The limits, in plain words. The cap is the floored figure
    /// `RouteService.capMiles` gives, so it can never read 311.
    static let limits: [(head: String, body: String)] = [
        ("Drives of up to \(RouteService.capMiles(RouteService.maxTripKm)) miles.",
         "Directions go up to \(RouteService.capMiles(RouteService.maxTripKm)) miles in a "
         + "straight line, anywhere in the 48 contiguous states and DC. Loops reach "
         + "farther in open country than in a city."),
        ("Signs come first.",
         "Some roads close for the season, and the map doesn’t know every closure. "
         + "Follow posted signs."),
        ("Times are estimates.",
         "There’s no live traffic and no lane guidance."),
        ("Beauty is an estimate.",
         "Scenery scores come from map data, so a road you love may score lower "
         + "than it deserves."),
    ]

    private func limit(_ head: String, _ body: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text("—")
                .font(.system(size: 13.5, weight: .bold))
                .foregroundStyle(Color.amberText)
            (Text(head).fontWeight(.semibold).foregroundColor(.ink)
             + Text(" ") + Text(body).foregroundColor(.ink2))
                .font(.system(size: 13.5))
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
