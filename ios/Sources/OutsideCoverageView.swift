import SwiftUI

/// **This won't work from here** — what a phone outside the covered area is
/// shown, once a launch.
///
/// The ask was "a big warning if they are outside of NE that THIS WONT WORK",
/// and it carries over unchanged to the national edge: Canada, Mexico, the
/// sea, and everywhere else outside the 48 contiguous states and DC.
/// Big, then: the whole screen, opaque, under the largest type in the app. Not
/// in capitals, though. All-caps text is slower to read and can trip VoiceOver
/// into reading words as letters, so the shout is in the headline's size and
/// weight instead.
///
/// **It informs and never blocks.** Guideline 3.2.2(v) counts "arbitrarily
/// restricting who may use the app, such as by location" as unacceptable, and
/// someone planning next month's trip to Vermont is part of the audience: a
/// typed start inside the covered area works from anywhere. So "Got it" always dismisses
/// it, and the copy ends on what does work.
///
/// Shown from `ContentView` as an overlay in its stack, not as a sheet or a
/// cover. On first launch it arrives just after "Before you drive", which is a
/// sheet, and SwiftUI drops a second presentation made while the first is up
/// or still leaving. An overlay cannot be dropped. At worst it waits under a
/// sheet the user opened and is there when the sheet closes.
struct OutsideCoverageView: View {
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

                    Text("Sunday Drive only covers \(Coverage.areaName). You’re outside "
                         + "them, so Loop and My Location can’t plan a drive from where "
                         + "you are.")
                        .font(.system(size: 17))
                        .foregroundStyle(Color.ink)

                    Text("You can still plan a drive there: type a town in the 48 states, "
                         + "like Stowe, VT, as your start.")
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
