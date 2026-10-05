import SwiftUI

/// The whole screen. Two modes that cross-fade into each other:
///
/// - **planning** — `PlanningView`, a page with a bounded map at the top
/// - **driving** — `NavView`, full-bleed and glanceable
///
/// They share a map and nothing else: not a layout, not a density, not a set of
/// controls. They used to share a sheet as well, which is what made planning
/// cramped and driving crowded — and what put an opaque panel across Apple's
/// map logo at every detent. See `docs/interface-design.md`.
struct ContentView: View {
    @State private var model = RouteModel()

    /// **Dark unless the user says otherwise.** A phone in a windscreen mount
    /// is a light source pointed at the driver; MapKit's dark basemap is where
    /// amber separates best; and most driving happens at the two ends of the
    /// day, so following the system would flip the app mid-drive at dusk.
    ///
    /// The cost is real and is why the switch exists: in direct midday sun,
    /// light-on-dark is harder to read than dark-on-light. The control is on
    /// the Sources screen. See `docs/interface-design.md` §7.6.
    @AppStorage("matchSystemAppearance") private var matchSystem = false

    /// The same flag `PlanningView` presents "Before you drive" from. Read
    /// here only to know when the first launch's notice has been acknowledged.
    @AppStorage("hasSeenBeforeYouDrive") private var hasSeenNotice = false

    /// The phone is outside New England and has not yet said "Got it" this
    /// launch. See `OutsideNewEnglandView`.
    @State private var showingOutsideWarning = false
    /// Whether this launch has checked, so it checks once and warns once.
    @State private var checkedWhereabouts = false

    var body: some View {
        ZStack {
            if let nav = model.nav {
                NavView(nav: nav,
                        locationManager: model.locationManager,
                        destinationName: model.mode == .loops ? model.loops.startQuery : model.endQuery) {
                    model.endNavigation()
                }
                .transition(.opacity)
            } else {
                PlanningView(model: model)
                    .transition(.opacity)
            }

            if showingOutsideWarning {
                OutsideNewEnglandView { showingOutsideWarning = false }
                    .transition(.opacity)
                    .zIndex(1)
            }
        }
        .animation(.smooth(duration: 0.4), value: model.nav != nil)
        .animation(.smooth(duration: 0.3), value: showingOutsideWarning)
        .preferredColorScheme(matchSystem ? nil : .dark)
        .tint(Color.amberText)
        // Every launch after the first: check quietly, and only if location
        // is already allowed. A cold launch only — `.task` does not run again
        // when the app comes back from the background, so neither does the
        // warning.
        .task { if hasSeenNotice { await checkWhereabouts(askingPermission: false) } }
        // The first launch: once "Before you drive" is acknowledged, ask for
        // location, then check. The pause lets the notice finish leaving
        // before the system prompt arrives over it.
        .onChange(of: hasSeenNotice) { _, seen in
            guard seen else { return }
            Task {
                try? await Task.sleep(for: .milliseconds(600))
                await checkWhereabouts(askingPermission: true)
            }
        }
    }

    private func checkWhereabouts(askingPermission: Bool) async {
        guard !checkedWhereabouts else { return }
        checkedWhereabouts = true
        if await model.checkWhereabouts(askingPermission: askingPermission) == .outside {
            showingOutsideWarning = true
        }
    }
}
