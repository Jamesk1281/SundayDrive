import SwiftUI

/// **This won't work from here** — what a phone outside New England is shown,
/// once a launch.
///
/// The ask was "a big warning if they are outside of NE that THIS WONT WORK".
/// Big, then: the whole screen, opaque, under the largest type in the app. Not
/// in capitals, though. All-caps text is slower to read and can trip VoiceOver
/// into reading words as letters, so the shout is in the headline's size and
/// weight instead.
///
/// **It informs and never blocks.** Guideline 3.2.2(v) counts "arbitrarily
/// restricting who may use the app, such as by location" as unacceptable, and
/// someone planning next month's trip to Vermont is part of the audience: a
/// typed New England start works from anywhere. So "Got it" always dismisses
/// it, and the copy ends on what does work.
///
/// Shown from `ContentView` as an overlay in its stack, not as a sheet or a
/// cover. On first launch it arrives just after "Before you drive", which is a
/// sheet, and SwiftUI drops a second presentation made while the first is up
/// or still leaving. An overlay cannot be dropped. At worst it waits under a
/// sheet the user opened and is there when the sheet closes.
struct OutsideNewEnglandView: View {
    var onDismiss: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 44, weight: .semibold))
                        .foregroundStyle(Color.alert)
                        .accessibilityHidden(true)

                    Text("This won’t work from here")
                        .font(.system(size: 40, weight: .heavy))
                        .foregroundStyle(Color.ink)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityAddTraits(.isHeader)

                    Text("Sunday Drive only covers the six New England states: Connecticut, "
                         + "Maine, Massachusetts, New Hampshire, Rhode Island and Vermont. "
                         + "You’re outside them, so Loop and My Location can’t plan a drive "
                         + "from where you are.")
                        .font(.system(size: 17))
                        .foregroundStyle(Color.ink)

                    Text("You can still plan a drive there: type a New England town, like "
                         + "Stowe, VT, as your start.")
                        .font(.system(size: 17))
                        .foregroundStyle(Color.ink2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, Metric.margin)
                .padding(.top, 48)
                .padding(.bottom, 18)
            }
            .scrollBounceBehavior(.basedOnSize)

            PrimaryButton(title: "Got it", action: onDismiss)
                .padding(.horizontal, Metric.margin)
                .padding(.bottom, 12)
        }
        .background(Color.paper.ignoresSafeArea())
        // The screen underneath is still there; VoiceOver must not wander
        // into it, and should start reading here.
        .accessibilityElement(children: .contain)
        .accessibilityAddTraits(.isModal)
        .onAppear { UIAccessibility.post(notification: .screenChanged, argument: nil) }
    }
}
