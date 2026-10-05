import MapKit
import SwiftUI

/// Which of the three planning screens is showing.
///
/// A stage rather than a `NavigationStack`, for two reasons. The map is
/// continuous across all three and only changes height — pushing a new screen
/// would tear it down and rebuild it, which reads as a flicker and refits the
/// camera for no reason. And a navigation bar is chrome this design does not
/// want: the back affordance is one chevron in the page header.
enum PlanStage: Equatable {
    case home
    case directions
    case loop
}

/// **A page, not a drawer.**
///
/// The planning half of the app: a bounded map at the top, a scrolling page
/// underneath it, the primary action pinned above the fold, and the data credit
/// pinned below everything. Replaces `RoutePanel` in a permanent `.sheet`.
///
/// What that buys beyond the Attachment 6 fix in `PlanningMap`:
///
/// - `PlanningCompactDetent` is gone. Eighty-seven lines of custom detent whose
///   two constants were *solved* from the block measured on a booted iPhone at
///   two text sizes, because no literal height can follow Dynamic Type — and at
///   AX5 the same block measured 884 pt on an 852 pt screen, which no detent
///   could ever show. A page just gets longer.
/// - The keyboard no longer fights the container, so the stale hit-test frame
///   that silently swallowed taps on the first suggestion row cannot recur, and
///   neither can the panel that appeared to close itself the instant an address
///   was set.
struct PlanningView: View {
    @Bindable var model: RouteModel

    @State private var stage: PlanStage = .home
    @State private var camera: MapCameraPosition = .region(.newEngland)
    @State private var showingTaste = false
    @State private var showingSources = false
    /// True while any address field on the current stage has the keyboard.
    @State private var isSearching = false
    /// The card's width, and how much of its top runs under the status bar
    /// and the Dynamic Island. `refit` frames routes against both.
    @State private var cardWidth: CGFloat = 0
    @State private var topInset: CGFloat = 0
    /// The height the card last changed to, and when. See `refit`.
    @State private var cardChange = (height: CGFloat(0), at: Date.distantPast)
    /// Ticks whenever the camera is told to go somewhere, so a fit still
    /// waiting for the card to stop moving cannot land on top of a newer one.
    @State private var fitGeneration = 0

    /// Shown once, on the first launch that ever reaches this screen. It is
    /// also permanently reachable from Sources — two ways in, one view, one
    /// copy of the fixed notice.
    @AppStorage("hasSeenBeforeYouDrive") private var hasSeenNotice = false

    var body: some View {
        VStack(spacing: 0) {
            PlanningMap(model: model, stage: stage, camera: $camera)
                .frame(height: mapHeight)
                .clipShape(UnevenRoundedRectangle(bottomLeadingRadius: 22,
                                                  bottomTrailingRadius: 22))
                .animation(.smooth(duration: 0.34), value: mapHeight)

            Group {
                switch stage {
                case .home:
                    HomeView(model: model, stage: $stage)
                case .directions:
                    DirectionsView(model: model, stage: $stage,
                                   isSearching: $isSearching,
                                   showingTaste: $showingTaste)
                case .loop:
                    LoopView(model: model, stage: $stage,
                             isSearching: $isSearching,
                             showingTaste: $showingTaste)
                }
            }
            .transition(.opacity)

            creditLine
        }
        .background(Color.paper)
        // The map card runs under the status bar; everything below it sits in
        // the safe area, including the credit line above the home indicator.
        .ignoresSafeArea(edges: .top)
        // Read here, outside `ignoresSafeArea`. Inside it the top inset reads
        // as zero, and that is how routes came to be framed under the clock.
        .onGeometryChange(for: CGFloat.self) { $0.safeAreaInsets.top } action: { topInset = $0 }
        .onGeometryChange(for: CGFloat.self) { $0.size.width } action: { cardWidth = $0 }
        .onChange(of: mapHeight, initial: true) { _, height in cardChange = (height, .now) }
        .animation(.smooth(duration: 0.28), value: stage)
        .sheet(isPresented: $showingTaste) { TuneView(model: model) }
        .sheet(isPresented: $showingSources) { AboutView() }
        .sheet(isPresented: .constant(!hasSeenNotice)) {
            BeforeYouDriveView { hasSeenNotice = true }
                .interactiveDismissDisabled()
        }
        // The tune screen edits one set of beauty weights for the whole app, so
        // the loop stage has to be routing under them too. Pushed rather than
        // read through a back-reference, which would be a retain cycle.
        .onChange(of: model.weights) { _, weights in model.loops.weights = weights }
        .task { model.loops.weights = model.weights }
        .onChange(of: model.response?.scenic.coordinates.count) { refit() }
        .onChange(of: model.loops.response?.loop.coordinates.count) { refit() }
        .onChange(of: stage) { _, new in
            // `PlanningMode` still exists and still means what it meant: which
            // kind of drive is being planned. Nothing in the interface picks it
            // any more — the stage does — but `RouteModel` and the drive that
            // starts from it both read it.
            model.mode = (new == .loop) ? .loops : .directions
            refit()
        }
        .onChange(of: model.start?.latitude) {
            guard model.response == nil, let start = model.start else { return }
            fitGeneration += 1
            withAnimation { camera = .around(start) }
        }
        .onChange(of: model.loops.start?.latitude) {
            guard model.loops.response == nil, let start = model.loops.start else { return }
            fitGeneration += 1
            withAnimation { camera = .around(start) }
        }
    }

    /// How tall the map is, by what the user is doing.
    ///
    /// Three sizes and one rule: the map is as big as it is useful. On the home
    /// screen it answers "where am I"; with a route on it, it answers "does
    /// that go where I think it goes" and shares the screen with the numbers;
    /// while the keyboard is up it gets out of the way, which a sheet could
    /// only do by fighting the keyboard for the same space.
    private var mapHeight: CGFloat {
        if isSearching { return 132 }
        switch stage {
        case .home:       return 306
        case .directions: return model.response == nil ? 300 : 218
        case .loop:       return model.loops.response == nil ? 300 : 200
        }
    }

    /// Frame the stage's line, for the height the card is heading to.
    ///
    /// **After the card has stopped moving.** The change that brings a route
    /// usually resizes the card as well (300 pt to 200 for the first loop), and
    /// MapKit works out where an animated camera will end from the card's
    /// height *when the animation starts*. It keeps that region, not that
    /// scale, as the card goes on moving. So a fit started together with the
    /// resize could come out wrong by as much as the ratio of the two heights.
    /// On main the first Concord loop put its start pin 31 pt down the card in
    /// one run and 18 pt in the next. A fit applied just as the card began to
    /// shrink came out 1.5× too far out. Setting the camera without
    /// animation did not save it either: MapKit's scale drifted about 4% as the
    /// card shrank underneath it. So the fit waits out the card's own 0.34 s
    /// animation. At 0.4 s the spring still left it 0.4% out; at 0.5 s it
    /// measured exact. A fit with no resize in flight, such as another
    /// direction or a new pref, moves at once as before.
    private func refit() {
        fitGeneration += 1
        let generation = fitGeneration
        let (line, pins) = PlanningMap.framedContent(stage, model)
        guard let fitted = MapCameraPosition.fitting(line, pins: pins,
                                                     card: CGSize(width: cardWidth, height: mapHeight),
                                                     topInset: topInset) else { return }
        // The height's own `onChange` may not have run yet in this update.
        let sinceResize = cardChange.height == mapHeight ? Date.now.timeIntervalSince(cardChange.at) : 0
        let wait = 0.5 - sinceResize
        guard wait > 0 else {
            withAnimation { camera = fitted }
            return
        }
        Task { @MainActor in
            try? await Task.sleep(for: .seconds(wait))
            guard generation == fitGeneration else { return }
            withAnimation { camera = fitted }
        }
    }

    /// The data credit, and the way in to the full list of sources.
    ///
    /// **Pinned outside the scroll view, deliberately, and not moved by the
    /// redesign.** The OSMF attribution guideline's base requirement is that
    /// attribution "must be presented to anyone who uses, views, accesses,
    /// interacts with, or is otherwise exposed to the map or produced work",
    /// and that the format "should not require individuals to interact with the
    /// map or produced work to see the attribution". A credits screen one tap
    /// away is the guideline's own example of where the *detail* may live — the
    /// supplement to a visible credit, not a substitute for one.
    ///
    /// So it is on screen at every stage, at every scroll position. What
    /// changed is only how it is set: the small-caps label style the rest of
    /// the design uses for section heads, above a hairline, so it reads as a
    /// colophon rather than as fine print somebody was made to add.
    ///
    /// The driving screen carries no credit of its own, and that is unchanged
    /// too: a route has to be planned here before a drive can start, so this
    /// has necessarily been on screen first, and the guideline is explicit that
    /// attribution shown at startup "does not need to be presented to the user
    /// every time the user looks at or interacts with the application".
    private var creditLine: some View {
        Button { showingSources = true } label: {
            // One concatenated `Text`, not an `HStack` of two. Side by side,
            // the credit and the link are separate wrapping contexts, and at
            // the accessibility text sizes they each wrap inside their own
            // column — "Map data from OpenStreet-/Map" stacked beside a
            // two-line "Sources", four lines to say one thing. Joined, it
            // reflows as a single paragraph.
            //
            // Truncating instead is not the alternative: this is a licence
            // credit, and the OSMF guideline asks that it stay legible and that
            // accessibility guidance be followed. It is allowed to grow.
            (Text(DataSources.shortCredit.uppercased())
             + Text("   ")
             + Text("Sources ›").foregroundColor(.amberText))
                .font(.system(size: 11, weight: .semibold))
                .tracking(1.0)
                .foregroundStyle(Color.ink3)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, Metric.margin)
                .padding(.vertical, 11)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .overlay(alignment: .top) { Divider().overlay(Color.hairline) }
        .accessibilityLabel("\(DataSources.shortCredit). Data sources and licences.")
    }
}
