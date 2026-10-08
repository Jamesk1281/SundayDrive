import SwiftUI

/// What the drive was, at the end of it.
///
/// New, and it earns its place three ways: it closes the promise the trade
/// screen made — you were told this would buy nineteen miles of beautiful road,
/// and here is the receipt; it gives a driver who marked nothing a single
/// chance to mark the whole drive, which is free calibration data on a
/// measurement the project cannot get any other way; and it is the moment the
/// app's name is about, without the name appearing anywhere.
///
/// It replaces `Text("You've arrived 🎉")`, which was the last thing the app
/// said on every drive and said nothing.
struct ArrivalView: View {
    @Bindable var nav: NavigationModel
    let destinationName: String
    var onDone: () -> Void

    /// Nil until the driver answers, then locked — this is one verdict on the
    /// whole drive, not a toggle.
    @State private var verdict: SceneryVerdict?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Arrived").sectionLabel()
            Text(destinationName.isEmpty ? "Back where you started" : destinationName)
                .font(.figure(30, .bold))
                .foregroundStyle(Color.ink)
                .lineLimit(2)
                .minimumScaleFactor(0.7)
                .padding(.top, 3)

            HStack(alignment: .top, spacing: 22) {
                stat("Drove", "\(nav.route.properties.km.wholeMilesFromKm) mi", tint: .ink)
                stat("Took", TimeText.compact(minutes: nav.elapsedMinutes), tint: .ink)
                if let beautiful = nav.route.properties.beautiful_km {
                    stat("Beautiful", "\(beautiful.wholeMilesFromKm) mi", tint: .amberText)
                }
            }
            .padding(.top, 15)

            // Only asked when there is a recording to put the answer in. Asking
            // and then dropping the answer would be worse than not asking.
            if nav.canRecordMarks {
                Divider().overlay(Color.hairline).padding(.vertical, 15)

                Text("How was the road?").sectionLabel()
                    .padding(.bottom, 10)

                HStack(spacing: 10) {
                    answer(.nice, "Lovely", symbol: "hand.thumbsup.fill",
                           tint: .amberText, border: .amber)
                    answer(.dull, "Not really", symbol: "hand.thumbsdown.fill",
                           tint: .ink2, border: .hairline)
                }
            }

            // Done is the one way out of a drive that arrived, so it is where a
            // drive counts towards the rating prompt. The ask itself waits for
            // the planning screen (`ContentView`; `docs/rating-prompt.md`).
            PrimaryButton(title: "Done") {
                RatingPrompt.shared.noteArrival(elapsedMinutes: nav.elapsedMinutes)
                onDone()
            }
            .padding(.top, nav.canRecordMarks ? 12 : 18)
        }
        .padding(20)
        .background(Color.card, in: RoundedRectangle(cornerRadius: 22))
        .shadow(color: .black.opacity(0.28), radius: 20, y: 6)
    }

    private func stat(_ head: String, _ value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(head).sectionLabel()
            Text(value)
                .font(.figure(25))
                .foregroundStyle(tint)
                .monospacedDigit()
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(head) \(value)")
    }

    private func answer(_ which: SceneryVerdict, _ title: String, symbol: String,
                        tint: Color, border: Color) -> some View {
        let chosen = verdict == which
        return Button {
            guard verdict == nil else { return }
            verdict = which
            nav.mark(which)
            UINotificationFeedbackGenerator()
                .notificationOccurred(which == .nice ? .success : .warning)
        } label: {
            Label(title, systemImage: chosen ? "checkmark" : symbol)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(chosen ? Color.onAmber : tint)
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(chosen ? Color.amber : Color.card,
                            in: RoundedRectangle(cornerRadius: 15))
                .overlay(RoundedRectangle(cornerRadius: 15)
                    .stroke(chosen ? Color.clear : border, lineWidth: 1))
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(verdict != nil && !chosen)
        .accessibilityLabel(title)
        .accessibilityAddTraits(chosen ? [.isSelected] : [])
    }
}
