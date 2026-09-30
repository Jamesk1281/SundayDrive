import SwiftUI

/// What the screen says when a drive that never reached its route has been
/// paused for standing still — see `NavigationModel.stalled`.
///
/// Deliberately not the arrival card, and nothing like it: there is no
/// receipt, because nothing was driven, and no verdict on the road, because
/// no road was. The one thing a driver coming back to the phone needs is to
/// know the app has stopped following them and why, and the two ways on.
///
/// "Keep navigating" is the filled action because the likeliest reason for a
/// car sitting still before its route is a driver who has not left yet — the
/// kids, the coffee — and the tap that costs them nothing should be the easy
/// one. Ending is one tap too, and not hidden: the other likely reason is a
/// drive that was never going to happen.
struct StalledView: View {
    var onKeepNavigating: () -> Void
    var onEnd: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Navigation paused").sectionLabel()
            Text("You haven't reached the route yet")
                .font(.figure(26, .bold))
                .foregroundStyle(Color.ink)
                .lineLimit(2)
                .minimumScaleFactor(0.7)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 3)
            // Says what was switched off, so a paused screen is not mistaken
            // for a frozen one.
            Text("You've been in one place for five minutes, so location is off to save your battery.")
                .font(.system(size: 14.5))
                .foregroundStyle(Color.ink2)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 8)

            PrimaryButton(title: "Keep navigating", systemImage: "location.north.fill",
                          action: onKeepNavigating)
                .padding(.top, 16)
            SecondaryButton(title: "End drive", action: onEnd)
                .padding(.top, 10)
        }
        .padding(20)
        .background(Color.card, in: RoundedRectangle(cornerRadius: 22))
        .shadow(color: .black.opacity(0.28), radius: 20, y: 6)
    }
}
