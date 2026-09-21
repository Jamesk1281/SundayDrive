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
        }
        .animation(.smooth(duration: 0.4), value: model.nav != nil)
        .preferredColorScheme(matchSystem ? nil : .dark)
        .tint(Color.amberText)
    }
}
