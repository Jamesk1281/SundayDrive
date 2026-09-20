import SwiftUI

extension Color {
    /// The app's accent green — the scenic route line, the Tune highlight, the
    /// scenery bars. Defined once so every view uses exactly the same color.
    ///
    /// Named for the app rather than for the scenic arm on purpose: it tints
    /// the About sheet, the Tune button and the mute control too, none of
    /// which are about the route.
    static let brand = Color(red: 0.22, green: 0.83, blue: 0.62)
}
