import MapKit
import SwiftUI
import UIKit

/// The drive. Five things, floating, clear of the bottom-left.
///
/// In priority order: the next maneuver, am I nearly there, this road is
/// lovely / this road is dull, where am I now, and get me out of this.
/// Everything else is a diagnostic and sits below the fold of attention.
///
/// Two things changed structurally from the screen this replaces.
///
/// **The banner is opaque.** It was `.ultraThinMaterial`, and the codebase had
/// already learned this lesson one control down: the verdict buttons were moved
/// to `.regularMaterial` because glass over a `Map` is a tint, not a
/// background, and the POI labels underneath read straight through it. The
/// maneuver is the one thing on this screen a driver reads at 50 mph in direct
/// sun, so it gets ink. The basemap also drops its points of interest for the
/// duration, so nothing competes with the route line for the brightest thing
/// on screen.
///
/// **Nothing opaque enters the bottom-left.** All the furniture sits in the
/// bottom safe-area inset, which means MapKit lays its own attribution out
/// *above* it rather than behind it, and a further `Metric.appleKeep` of clear
/// space sits under everything as a second, independent guarantee. On a
/// heading-up map that strip is the road already driven, so it costs the driver
/// nothing. See `docs/interface-design.md` §2.2.
struct NavView: View {
    @Bindable var nav: NavigationModel
    let locationManager: LocationManager
    /// What to call the place at the end, for the arrival card. The drive does
    /// not know it; the plan does.
    var destinationName: String
    var onEnd: () -> Void

    /// Follows the user's location and turns with their heading, like any
    /// turn-by-turn map. Falls back to a sensible frame before the first fix.
    @State private var camera: MapCameraPosition =
        .userLocation(followsHeading: true, fallback: .automatic)

    /// Whether the "switch to fastest?" confirmation is up.
    @State private var confirmingFastest = false
    /// English voices that can keep up with the schedule — see
    /// `VoiceCatalogue`. Empty until the first measurement pass finishes.
    @State private var voices: [VoiceCatalogue.Measured] = []

    /// Tap target for the two corner buttons. Scaled, so the glyph inside still
    /// fits when the driver runs a larger system text size.
    @ScaledMetric(relativeTo: .body) private var controlSize: CGFloat = 34

    /// Height of the scenery-verdict buttons. Well over the 44 pt minimum,
    /// because these are meant to be hit by a driver who is not looking at them.
    @ScaledMetric(relativeTo: .body) private var verdictHeight: CGFloat = 58

    /// Watched so the drive trace can mark where the app went away and came
    /// back, and flush on the way out — a hole in the fixes otherwise looks the
    /// same as a tunnel.
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        Map(position: $camera) {
            MapPolyline(coordinates: nav.coordinates)
                .stroke(nav.followingFastest ? Color.slate : Color.amber,
                        style: StrokeStyle(lineWidth: 8, lineCap: .round, lineJoin: .round))
            Marker("Destination", coordinate: nav.destination).tint(Color.endPin)
            UserAnnotation()
        }
        // Nothing on a driving basemap should compete with the route line. The
        // POI pins are the only thing on it with comparable contrast, and a
        // driver has no use for a coffee shop they are passing at 50 mph.
        .mapStyle(.standard(pointsOfInterest: .excludingAll))
        // North stops being obvious the moment the map turns with the car, and
        // on a scenic drive "which way am I actually pointing" is a question
        // worth answering without leaving the app. MapKit's own compass hides
        // itself at north-up and appears as soon as the map rotates, which in
        // a heading-up drive means it is simply always there.
        .mapControls { MapCompass() }
        .ignoresSafeArea()
        .safeAreaInset(edge: .top) { banner }
        .safeAreaInset(edge: .bottom) { furniture }
        .overlay(alignment: .bottom) {
            if nav.arrived {
                ArrivalView(nav: nav, destinationName: destinationName, onDone: onEnd)
                    .padding(.horizontal, 14)
                    .padding(.bottom, Metric.appleKeep + 10)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            } else if nav.stalled {
                // The same place and the same keep as the arrival card: this
                // overlay ignores the furniture's inset, so the clear strip
                // under Apple's logo is reserved here again, by hand.
                StalledView(onKeepNavigating: { nav.resumeAfterStall() }, onEnd: onEnd)
                    .padding(.horizontal, 14)
                    .padding(.bottom, Metric.appleKeep + 10)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(.smooth(duration: 0.4), value: nav.arrived)
        .animation(.smooth(duration: 0.4), value: nav.stalled)
        .onAppear {
            locationManager.start()
            // Keep the screen awake for the whole drive, so the map stays
            // visible without the driver reaching for the phone.
            UIApplication.shared.isIdleTimerDisabled = true
        }
        .onDisappear {
            locationManager.stop()
            UIApplication.shared.isIdleTimerDisabled = false
        }
        // Arrival ends the drive, so release the hardware then rather than
        // waiting for a tap. `nav.update` early-returns once `arrived` latches,
        // so nothing is being recorded or displayed — but the session would
        // otherwise keep running at 1 Hz, in the background, with the screen
        // held awake, until the driver happened to come back to the phone.
        .onChange(of: nav.arrived) { _, arrived in
            guard arrived else { return }
            locationManager.stop()
            UIApplication.shared.isIdleTimerDisabled = false
        }
        // A drive that never reached its route and has stood still is paused,
        // and released for the same reason as arrival: otherwise a car parked
        // back from the road it was routed along runs GPS with the screen awake
        // forever. Unlike arrival it can be undone, so the resume is here too
        // and puts back exactly what `onAppear` set up.
        .onChange(of: nav.stalled) { _, stalled in
            if stalled {
                locationManager.stop()
                UIApplication.shared.isIdleTimerDisabled = false
            } else {
                locationManager.start()
                UIApplication.shared.isIdleTimerDisabled = true
            }
        }
        // No `onChange` feeding `nav.update` here on purpose. The drive is wired
        // straight to CoreLocation in `RouteModel.startNavigation`, because a
        // view modifier stops firing the moment the phone locks — see
        // `LocationManager.onFix`. This view only draws what the drive decides.
        //
        // `scenePhase` is different, and is the right tool for exactly this: the
        // transition *into* the background is delivered, which is what the trace
        // needs to distinguish a suspended app from a tunnel.
        .onChange(of: scenePhase) { _, phase in
            switch phase {
            case .background: nav.recordPhase("background")
            case .inactive:   nav.recordPhase("inactive")
            case .active:     nav.recordPhase("active")
            @unknown default: break
            }
        }
        .confirmationDialog(fastestPrompt.title,
                            isPresented: $confirmingFastest,
                            titleVisibility: .visible) {
            Button(fastestPrompt.confirm, role: .destructive) {
                Task { await nav.switchToFastest(from: locationManager.location) }
            }
            Button("Keep the scenic route", role: .cancel) {}
        } message: {
            Text(fastestPrompt.message)
        }
    }

    // MARK: - The escape hatch

    /// What the fastest-route escape says, which depends on what it will do.
    ///
    /// On a loop short of its far point the fastest route is the way *home*:
    /// `switchToFastest` gives up the far point with the scenery. Offering a
    /// "fastest route" there promised a quicker version of the same drive, and
    /// the driver who took it was sent to the far point by fast roads. Past the
    /// far point a loop is heading home anyway, so it keeps the ordinary words,
    /// as does every other drive.
    struct FastestPrompt: Equatable {
        let title: String
        let message: String
        let confirm: String
        /// The bolt button's VoiceOver label.
        let label: String

        init(loopBeforeFarPoint: Bool) {
            if loopBeforeFarPoint {
                title = "Head home the fastest way?"
                message = "This ends the loop and takes the fastest route back to where you started."
                confirm = "Head home"
                label = "Head home the fastest way"
            } else {
                title = "Switch to the fastest route?"
                message = "This gives up the scenic route for the rest of the drive."
                confirm = "Switch to fastest"
                label = "Switch to the fastest route"
            }
        }
    }

    private var fastestPrompt: FastestPrompt {
        FastestPrompt(loopBeforeFarPoint: nav.isLoopBeforeFarPoint)
    }

    // MARK: - The maneuver

    /// Whether the drive is still being followed. The banner and the controls
    /// describe a live drive, and neither an ended nor a paused one is.
    private var isLive: Bool { !nav.arrived && !nav.stalled }

    @ViewBuilder private var banner: some View {
        if isLive {
            HStack(spacing: 13) {
                Group {
                    if locationManager.authorization == .denied
                        || locationManager.authorization == .restricted {
                        // Without location we can't follow the drive at all — say
                        // so instead of sitting silently on the first instruction.
                        bannerBody(symbol: "location.slash", tint: .alert,
                                   over: "Location is off",
                                   main: "Allow it in Settings to navigate")
                    } else if nav.isRerouting {
                        bannerBody(symbol: "arrow.triangle.2.circlepath", tint: .alert,
                                   over: "Off route", main: "Finding a way back…")
                    } else if !nav.hasJoinedRoute {
                        // The trip was planned from somewhere the driver isn't
                        // yet. Say so plainly rather than reading out a first
                        // instruction that belongs to a road miles away.
                        bannerBody(symbol: "location.north.fill", tint: .amber,
                                   over: "\(distanceText(nav.distanceToRouteStart)) away",
                                   main: "Head to the start of your route")
                    } else {
                        bannerBody(symbol: nav.currentSymbol, tint: .amber,
                                   over: distanceText(nav.distanceToNext),
                                   main: nav.currentInstruction)
                    }
                }
                muteButton
            }
            .padding(.horizontal, 15)
            .padding(.vertical, 14)
            .background(Color.card, in: RoundedRectangle(cornerRadius: 19))
            .shadow(color: .black.opacity(0.22), radius: 12, y: 4)
            .padding(.horizontal, 14)
        }
    }

    private func bannerBody(symbol: String, tint: Color, over: String, main: String) -> some View {
        HStack(spacing: 13) {
            Image(systemName: symbol)
                .font(.system(size: 27, weight: .semibold))
                .foregroundStyle(tint)
                .frame(width: 34)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 1) {
                Text(over)
                    .font(.figure(17, .medium))
                    .foregroundStyle(tint == .alert ? Color.alert : Color.ink2)
                    .monospacedDigit()
                Text(main)
                    .font(.figure(25, .bold))
                    .foregroundStyle(Color.ink)
                    .lineLimit(3)
                    .minimumScaleFactor(0.75)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .accessibilityElement(children: .combine)
    }

    /// Silence the spoken directions — and, held down, choose the voice.
    ///
    /// In the banner, and deliberately not in the trip card. The banner is the
    /// only thing on this screen that is always on it; a control that moves
    /// mid-drive is one the driver has to hunt for. It is also, plainly, next
    /// to the words it governs.
    ///
    /// Voice selection hides behind a long press rather than taking a control
    /// of its own, because it is a once-ever choice sharing the one affordance
    /// that already means "the voice". It lives here rather than on the
    /// planning screen for a reason that outweighs the awkwardness of choosing
    /// one while driving: a voice is picked by ear, and `useVoice` speaks a
    /// real instruction in it. A list of names on a settings screen is not a
    /// choice anyone can make.
    @ViewBuilder private var muteButton: some View {
        if nav.canSpeak {
            Menu {
                Section("Voice") {
                    ForEach(voices) { option in
                        Button {
                            nav.useVoice(option)
                        } label: {
                            Label(option.label,
                                  systemImage: option.identifier == nav.selectedVoiceIdentifier
                                  ? "checkmark" : "speaker.wave.1")
                        }
                    }
                }
            } label: {
                Image(systemName: nav.voiceMuted ? "speaker.slash.fill" : "speaker.wave.2.fill")
                    .font(.system(size: 19, weight: .medium))
                    .foregroundStyle(nav.voiceMuted ? Color.ink3 : Color.amberText)
                    .frame(width: controlSize, height: controlSize)
                    .contentShape(Rectangle())
            } primaryAction: {
                nav.voiceMuted.toggle()
            }
            .accessibilityLabel(nav.voiceMuted
                                ? "Turn spoken directions on"
                                : "Turn spoken directions off")
            .accessibilityHint("Press and hold to change the voice")
            .task { voices = await VoiceCatalogue.usable() }
        }
    }

    // MARK: - The bottom

    private var furniture: some View {
        VStack(spacing: 10) {
            if camera.positionedByUser {
                HStack {
                    Spacer()
                    recenterButton
                }
            }
            if isLive {
                sceneryVerdict
                tripCard
            }
            // The keep. Nothing opaque below this line, ever.
            Color.clear.frame(height: Metric.appleKeep)
        }
        .padding(.horizontal, 14)
    }

    /// The two buttons that make a drive worth taking twice.
    ///
    /// Everything else on this screen measures the car. These measure the road,
    /// and they are the only instrument in the project that can: the scenic
    /// score has been calibrated against its own distribution and against two
    /// byways named in `score.py`, which tests that it is self-consistent, not
    /// that it is right. Whether these roads are actually beautiful is a
    /// question only the person driving them can answer, and only while they
    /// are there.
    ///
    /// Two targets, no scale: a five-point rating needs aiming and aiming needs
    /// looking, and the calibration wants a rank statistic over many marks
    /// anyway. The haptics differ — `success` for nice, `warning` for dull — so
    /// the driver feels *which* one they hit without looking up to check.
    ///
    /// **They stop short of the bottom-left corner**, which is the one place on
    /// this screen where the licence costs the driver something real: in a
    /// centre windscreen mount a US driver's hand comes at the phone from the
    /// lower left, so the most reachable corner is the one Apple reserves. It
    /// is worth about 15 mm of reach.
    @ViewBuilder private var sceneryVerdict: some View {
        if nav.hasJoinedRoute && nav.canRecordMarks {
            HStack(spacing: 11) {
                verdictButton(.nice, symbol: "hand.thumbsup.fill",
                              tint: .amberText, border: .amber, label: "Lovely road")
                verdictButton(.dull, symbol: "hand.thumbsdown.fill",
                              tint: .ink2, border: .hairline, label: "Nothing to see")
            }
        }
    }

    private func verdictButton(_ verdict: SceneryVerdict, symbol: String,
                               tint: Color, border: Color, label: String) -> some View {
        Button {
            nav.mark(verdict)
            // Distinct patterns per verdict — the point is to be told apart by
            // feel. Generated fresh rather than kept around: a driver taps a
            // handful of times in an hour, so there is nothing to warm up for.
            UINotificationFeedbackGenerator()
                .notificationOccurred(verdict == .nice ? .success : .warning)
        } label: {
            // The words, not only the glyph. A thumbs-down on a map is as
            // easily read as "hide this" or "worse route" as "dull road".
            Label(label, systemImage: symbol)
                .font(.system(size: 15.5, weight: .semibold))
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .foregroundStyle(tint)
                // The generous frame *is* the feature: this has to be hittable
                // without aiming.
                .frame(maxWidth: .infinity)
                .frame(height: verdictHeight)
                .background(Color.card, in: RoundedRectangle(cornerRadius: 17))
                .overlay(RoundedRectangle(cornerRadius: 17).stroke(border, lineWidth: 1))
                .shadow(color: .black.opacity(0.18), radius: 10, y: 3)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
        .accessibilityHint("Records how this stretch of road looks, for calibrating the scenic score")
    }

    /// Arrival time, time left, distance left, and the road under the car —
    /// with End and the fastest-route escape tucked into the corners.
    ///
    /// The stats take the middle on purpose. That's where a thumb lands, and
    /// the numbers aren't tappable, so resting a hand on the phone mid-drive
    /// can't trigger anything.
    private var tripCard: some View {
        VStack(spacing: 0) {
            HStack(alignment: .center, spacing: 10) {
                cornerButton(systemImage: "xmark", label: "End the drive",
                             tint: .ink2, action: onEnd)
                Spacer(minLength: 6)
                tripStats
                Spacer(minLength: 6)
                // Hidden once taken: there's no second fastest route to switch
                // to. The clear spacer keeps the stats centred when it goes.
                if !nav.followingFastest {
                    cornerButton(systemImage: "bolt.fill",
                                 label: fastestPrompt.label,
                                 tint: .ink2) { confirmingFastest = true }
                } else {
                    Color.clear.frame(width: controlSize, height: controlSize)
                }
            }

            currentRoadLabel

            // Under the controls, not in the banner: the banner is where the
            // next maneuver goes, and no diagnostic outranks the turn you are
            // about to miss. Unmissable, but never in the way.
            if let problem = nav.recordingProblem ?? nav.actionProblem {
                Label(problem, systemImage: "exclamationmark.triangle.fill")
                    .font(.system(size: 12))
                    .foregroundStyle(Color.alert)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 7)
                    .transition(.opacity)
            }
        }
        .padding(.horizontal, 13)
        .padding(.vertical, 10)
        .background(Color.card, in: RoundedRectangle(cornerRadius: 19))
        .shadow(color: .black.opacity(0.22), radius: 12, y: 4)
        .animation(.snappy, value: nav.actionProblem)
    }

    private func cornerButton(systemImage: String, label: String, tint: Color,
                              action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(tint)
                .frame(width: controlSize, height: controlSize)
                .background(Color.sunk, in: RoundedRectangle(cornerRadius: 11))
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }

    private var tripStats: some View {
        VStack(spacing: 1) {
            HStack(spacing: 6) {
                // A drive is unrepeatable — that light was that colour, that
                // traffic was that thick, once — so whether it is being recorded
                // has to be answerable at a glance. Silence would look identical
                // to working.
                Circle()
                    .fill(nav.recordingProblem == nil ? Color.endPin : Color.alert)
                    .frame(width: 8, height: 8)
                Text(nav.eta, format: .dateTime.hour().minute())
                    .font(.figure(23, .bold))
                    .foregroundStyle(Color.ink)
                    .monospacedDigit()
                // How many verdicts have been logged. The haptic is the primary
                // confirmation, but a driver with haptics off system-wide gets
                // nothing back from a tap at all. Small, and outside the tap
                // targets, because it is a receipt rather than a number anybody
                // drives by.
                if nav.marksRecorded > 0 {
                    Text("\(nav.marksRecorded)")
                        .font(.system(size: 12, weight: .bold))
                        .monospacedDigit()
                        .foregroundStyle(Color.amberText)
                        .contentTransition(.numericText())
                }
            }
            .animation(.snappy, value: nav.marksRecorded)
            Text("\(timeText(nav.remainingMinutes)) · \(milesText(nav.remainingMeters))")
                .font(.system(size: 12.5))
                .foregroundStyle(Color.ink2)
                .monospacedDigit()
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "Arriving at \(nav.eta.formatted(date: .omitted, time: .shortened)), "
            + "\(timeText(nav.remainingMinutes)) and \(milesText(nav.remainingMeters)) to go. "
            + (nav.recordingProblem ?? "Recording this drive.")
            + (nav.marksRecorded > 0 ? " \(nav.marksRecorded) scenery marks logged." : "")
        )
    }

    /// The road under the car.
    ///
    /// Here rather than in the banner because the banner is for the maneuver
    /// ahead, and this is the opposite question — where am I *now*. It reads as
    /// a caption to the trip stats above it, which is about the attention it
    /// deserves: useful continuously, urgent never.
    @ViewBuilder private var currentRoadLabel: some View {
        switch nav.currentRoad {
        case .named(let road):
            // One line, truncated rather than wrapped: a long road name must
            // not reflow the controls underneath it mid-drive.
            Text(road)
                .font(.system(size: 13.5, weight: .semibold))
                .foregroundStyle(Color.ink2)
                .lineLimit(1)
                .truncationMode(.tail)
                .frame(maxWidth: .infinity)
                .padding(.top, 7)
                .accessibilityLabel("On \(road)")
        case .offRoute:
            Text("Off your route")
                .font(.system(size: 13.5, weight: .semibold))
                .foregroundStyle(Color.alert)
                .frame(maxWidth: .infinity)
                .padding(.top, 7)
        case .unknown:
            EmptyView()
        }
    }

    /// Puts the camera back on the driver, heading-up.
    ///
    /// Without it, panning the map is a one-way door: `MapCameraPosition` stops
    /// following the moment the user drags it, so a driver who nudged the map
    /// to see what was coming would spend the rest of the drive with a map that
    /// no longer tracked them.
    private var recenterButton: some View {
        Button {
            withAnimation {
                camera = .userLocation(followsHeading: true, fallback: .automatic)
            }
        } label: {
            Image(systemName: "location.fill")
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Color.amberText)
                .frame(width: 44, height: 44)
                .background(Color.card, in: Circle())
                .shadow(color: .black.opacity(0.22), radius: 10, y: 3)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Recenter the map on your location")
    }

    // MARK: - Units

    /// Distance in friendly US units: feet (rounded to 50) up close, miles after.
    private func distanceText(_ meters: Double) -> String {
        let feet = meters * 3.28084
        if feet < 1000 {
            return "\(max(50, Int((feet / 50).rounded()) * 50)) ft"
        }
        return milesText(meters)
    }

    /// "0.4 mi" up close, "23 mi" once the decimal stops meaning anything.
    private func milesText(_ meters: Double) -> String {
        let miles = meters / 1609.34
        return miles < 10 ? String(format: "%.1f mi", miles) : "\(Int(miles.rounded())) mi"
    }

    /// "8 min", or "1 hr 12 min" once it's worth splitting.
    private func timeText(_ minutes: Double) -> String {
        let total = max(0, Int(minutes.rounded()))
        return total >= 60 ? "\(total / 60) hr \(total % 60) min" : "\(total) min"
    }
}
