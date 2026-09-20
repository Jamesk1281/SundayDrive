import SwiftUI

/// The app entry point. `@main` marks this as where the app starts; the
/// `WindowGroup` hosts our single screen, `ContentView`.
@main
struct VictoryLapApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
