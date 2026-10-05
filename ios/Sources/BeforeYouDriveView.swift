import SwiftUI

/// **Before you drive** — the route-guidance notice, and what this app is not.
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

                    Text("What it does not do").sectionLabel()

                    limit("New England only.",
                          "Six states, 236,000 km of road, all of it measured.")
                    limit("No lane guidance.",
                          "The data covers between 4.6% and 23.8% of junction approaches "
                          + "depending on the state, which is not enough to tell you which "
                          + "lane to be in.")
                    limit("No live traffic.",
                          "Every time shown is a model, not a measurement.")
                    limit("Beauty is not measured evenly.",
                          "The terrain component saturates north of Massachusetts, so a "
                          + "Maine road and a Connecticut road are not scored on quite the "
                          + "same ruler.")
                    limit("Seasonal roads.",
                          "Some mountain roads close for winter. The app avoids the "
                          + "closures OpenStreetMap records, but not every closure is "
                          + "recorded, so follow posted signs.")

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
