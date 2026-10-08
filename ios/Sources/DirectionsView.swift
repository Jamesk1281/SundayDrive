import SwiftUI

/// The trade — the screen the app is for.
///
/// One dial between the fastest route and the scenic one, and beneath it the
/// only number that matters: **what this setting costs, and what it buys.** It
/// replaces `Text("scenery strength 0.25")`, which printed the router's own
/// internal parameter to the person paying for it.
///
/// The handle's position is still the router's `strength` under `PrefSlider`'s
/// measured `sqrt` mapping. That mathematics is not up for redesign — it is
/// fitted over 252 pairs and it is right. What changed is only the caption.
struct DirectionsView: View {
    @Bindable var model: RouteModel
    @Binding var stage: PlanStage
    @Binding var isSearching: Bool
    @Binding var showingTaste: Bool

    @FocusState private var focused: Endpoint?
    /// Whether the two address fields are showing. Once a route exists they
    /// collapse to one line, because the ledger and the breakdown need the
    /// room more than a resolved address does.
    @State private var editingTrip = false

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 13) {
                    StageHeader(title: "Directions") {
                        focused = nil
                        stage = .home
                    }

                    if model.response == nil || editingTrip {
                        fields
                    } else {
                        tripLine
                    }

                    if let error = model.errorText {
                        Text(error)
                            .font(.system(size: 13))
                            .foregroundStyle(Color.alert)
                    }

                    if model.isLoading && model.response == nil {
                        ProgressView().frame(maxWidth: .infinity).padding(.vertical, 20)
                    }

                    if let response = model.response {
                        PrefDial(model: model, response: response)
                        RouteLedger(response: response)
                        breakdown(response)
                    }
                }
                .padding(.horizontal, Metric.margin)
                .padding(.top, 14)
                .padding(.bottom, 18)
            }
            .scrollBounceBehavior(.basedOnSize)
            .scrollDismissesKeyboard(.interactively)

            if let response = model.response {
                PrimaryButton(title: "Start driving", systemImage: "location.north.fill") {
                    model.startNavigation(response.scenic)
                }
                // Not while a menu option is on its way: `response.scenic` is
                // still the one before it, and that is not what was chosen.
                .disabled(model.pendingOption != nil)
                .padding(.horizontal, Metric.margin)
                .padding(.bottom, 10)
            }
        }
        .onChange(of: focused) { _, value in isSearching = value != nil }
        .onDisappear { isSearching = false }
        // A route arriving closes the editor, the way choosing a suggestion in
        // a maps app puts the keyboard away.
        .onChange(of: model.response == nil) { _, noRoute in
            if !noRoute { editingTrip = false }
        }
        .task { if model.response == nil && model.end == nil { focused = .end } }
    }

    // MARK: - The two ends

    private var fields: some View {
        VStack(spacing: 9) {
            PlaceField(prompt: "Start", text: $model.startQuery, dot: .startPin,
                       role: .start, focused: $focused, region: model.searchRegion,
                       isLocating: model.isLocatingUser,
                       onSubmit: { q in Task { await model.search(q, into: .start) } },
                       onChoose: { s in Task { await model.choose(s, into: .start) } },
                       onMyLocation: { Task { await model.useMyLocation() } },
                       onClear: model.start == nil ? nil : {
                           model.start = nil; model.startQuery = ""; model.response = nil
                       })

            PlaceField(prompt: "Destination", text: $model.endQuery, dot: .endPin,
                       role: .end, focused: $focused, region: model.searchRegion,
                       showsMyLocation: false,
                       onSubmit: { q in Task { await model.search(q, into: .end) } },
                       onChoose: { s in Task { await model.choose(s, into: .end) } },
                       onMyLocation: {},
                       onClear: model.end == nil ? nil : {
                           model.end = nil; model.endQuery = ""; model.response = nil
                       })

            if model.start != nil, model.end != nil {
                Button { model.swapEnds() } label: {
                    Label("Swap", systemImage: "arrow.up.arrow.down")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(Color.ink2)
                }
                .buttonStyle(.plain)
                .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
    }

    /// The collapsed trip, once there is a route to look at.
    private var tripLine: some View {
        HStack(spacing: 9) {
            Circle().fill(Color.startPin).frame(width: 8, height: 8)
            Text(model.startQuery)
                .font(.system(size: 15.5, weight: .semibold))
                .foregroundStyle(Color.ink)
                .lineLimit(1)
            Image(systemName: "arrow.right")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Color.ink3)
            Text(model.endQuery)
                .font(.system(size: 15.5, weight: .semibold))
                .foregroundStyle(Color.ink)
                .lineLimit(1)
            Spacer(minLength: 6)
            Button("Edit") { editingTrip = true }
                .font(.system(size: 13.5, weight: .medium))
                .foregroundStyle(Color.amberText)
        }
    }

    // MARK: - What you'll pass

    private func breakdown(_ response: RouteResponse) -> some View {
        let rows = response.scenic.properties.sceneryBreakdown
        let maxKm = max(1, rows.map(\.km).max() ?? 1)
        return VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 10) {
                Text("What you’ll pass").sectionLabel()
                Spacer(minLength: 6)
                TasteChip(weights: model.weights) { showingTaste = true }
            }
            VStack(spacing: 7) {
                ForEach(rows, id: \.label) { row in
                    SceneryBar(key: row.label, km: row.km, maxKm: maxKm)
                }
            }
        }
    }
}

// MARK: - The dial

/// Fastest ←→ Scenic, and the price of where the handle is.
struct PrefDial: View {
    @Bindable var model: RouteModel
    let response: RouteResponse

    var body: some View {
        if let menu = model.options?.menu, menu.count > 1 {
            OptionDial(model: model, menu: menu)
        } else {
            continuous
        }
    }

    private var continuous: some View {
        VStack(alignment: .leading, spacing: 2) {
            Slider(value: position, in: 0...1) { editing in
                if !editing { Task { await model.computeRoute() } }
            }
            .tint(Color.amber)
            .accessibilityLabel("Trade travel time for scenery")
            .accessibilityValue(spokenValue)

            HStack {
                Text("Fastest").sectionLabel(.slate)
                Spacer()
                Text("Scenic").sectionLabel(.amberText)
            }

            readout
                .padding(.top, 9)
                .animation(.smooth(duration: 0.2), value: model.routeIsStale)
        }
    }

    /// Where the handle sits, which is deliberately *not* `model.pref`.
    /// See `PrefSlider`. `model.pref` is the API's number and stays it; this
    /// binding is the only place the handle's own coordinate exists.
    private var position: Binding<Double> {
        Binding(get: { PrefSlider.position(forPref: model.pref) },
                set: { model.pref = PrefSlider.pref(atPosition: $0) })
    }

    /// **While the figures are stale this shows a name, not a number.**
    ///
    /// The route recomputes only on release — mid-drag is a request per tick at
    /// roughly 0.65 s of server work each — so while the handle is moving, and
    /// again while the new request is in flight, the minutes and the mile count
    /// describe the position the user has left. `0.25` was merely opaque; a
    /// stale price would be wrong. The name describes the handle, which is the
    /// one thing that is true at every moment of a drag. On arrival the real
    /// figures roll in.
    ///
    /// Keyed on `RouteModel.routeIsStale` rather than on the slider's own
    /// `onEditingChanged`: the gesture callback covers the drag but not the
    /// request after it, and it left the caption latched on the name when the
    /// end-of-drag edit never arrived.
    @ViewBuilder private var readout: some View {
        if model.routeIsStale {
            Text(PrefSlider.name(atPosition: position.wrappedValue))
                .font(.figure(26))
                .foregroundStyle(Color.ink)
                .transition(.opacity)
        } else {
            let c = RouteComparison(fastest: response.fastest.properties,
                                    scenic: response.scenic.properties)
            if c.isSameDrive {
                Text("Same as the fastest route")
                    .font(.figure(24))
                    .foregroundStyle(Color.ink2)
            } else if let gain = c.headlineGain {
                (cost(c.extraMinutes)
                 + Text(" · ").foregroundColor(.ink3)
                 + Text("+\(gain) mi of beautiful road").foregroundColor(.amberText))
                    .font(.figure(26))
                    .contentTransition(.numericText())
            } else {
                // No gain to print: the same beautiful miles or fewer, which the
                // sentence words honestly rather than as "+0 mi". Or an older
                // backend, no `beautiful_km`, which the sentence that shipped
                // before the cards counted miles still describes exactly.
                Text(c.attributedSummary)
                    .font(.system(size: 15))
                    .foregroundStyle(Color.ink)
            }
        }
    }

    private func cost(_ minutes: Int) -> Text {
        minutes <= 0
            ? Text("No extra time").foregroundColor(.slate)
            : Text("+\(minutes) min").foregroundColor(.slate)
    }

    /// The readout, in words. Wherever there is no gain to print, the same
    /// drive included, it reads the sentence's plain text: `summary` is
    /// markdown, and its `**` are not something to read aloud.
    private var spokenValue: String {
        let c = RouteComparison(fastest: response.fastest.properties,
                                scenic: response.scenic.properties)
        guard let gain = c.headlineGain else { return String(c.attributedSummary.characters) }
        let cost = c.extraMinutes <= 0
            ? "no extra time" : "plus \(CountText.of(c.extraMinutes, "minute"))"
        return "\(cost), \(CountText.of(gain, "more mile")) of beautiful road"
    }
}

// MARK: - The menu's dial

/// The dial when the plan came with a menu of in-between routes
/// (docs/route-options.md): one detent per option, evenly spaced by index so
/// every one is reachable, the fastest at the left and the full scenic route at
/// the right.
///
/// Unlike the continuous dial this prints a **price while dragging**: every
/// option's minutes and beautiful miles came with the plan, so the figure under
/// the handle is true at every moment of the drag rather than the stale price
/// of a setting just left. The map is redrawn on release, from the option's
/// simplified line until its full route arrives.
struct OptionDial: View {
    @Bindable var model: RouteModel
    let menu: [RouteOption]

    var body: some View {
        let option = menu[min(max(model.optionIndex, 0), menu.count - 1)]
        VStack(alignment: .leading, spacing: 2) {
            Slider(value: detent, in: 0...Double(menu.count - 1), step: 1) { editing in
                if !editing { Task { await model.chooseOption() } }
            }
            .tint(Color.amber)
            .accessibilityLabel("Trade travel time for scenery")
            .accessibilityValue(OptionCaption.spoken(option, fastest: menu[0]))

            HStack {
                Text("Fastest").sectionLabel(.slate)
                Spacer()
                Text("Scenic").sectionLabel(.amberText)
            }

            price(option)
                .font(.figure(26))
                .contentTransition(.numericText())
                .padding(.top, 9)
            if let caption = OptionCaption.route(option) {
                Text(caption)
                    .font(.system(size: 13.5))
                    .foregroundStyle(Color.ink2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var detent: Binding<Double> {
        Binding(get: { Double(model.optionIndex) },
                set: { model.optionIndex = min(max(Int($0.rounded()), 0), menu.count - 1) })
    }

    private func price(_ option: RouteOption) -> Text {
        let minutes = Int(option.extra_minutes.rounded())
        let gain = OptionCaption.gainMiles(option, fastest: menu[0])
        if minutes <= 0 && gain <= 0 {
            return Text("Fastest route").foregroundColor(.slate)
        }
        return Text(minutes <= 0 ? "No extra time" : "+\(minutes) min").foregroundColor(.slate)
            + Text(" · ").foregroundColor(.ink3)
            + Text("+\(gain) mi of beautiful road").foregroundColor(.amberText)
    }
}

/// The words for one menu option. Pure, so the wording has tests.
enum OptionCaption {
    /// Beautiful miles over the fastest route, in the whole miles the ledger
    /// prints, so the dial and the ledger cannot disagree by a rounding.
    static func gainMiles(_ option: RouteOption, fastest: RouteOption) -> Int {
        option.beautiful_km.wholeMilesFromKm - fastest.beautiful_km.wholeMilesFromKm
    }

    /// Where the route leaves and rejoins the scenic road, and the roads it
    /// takes between; nil for the fastest route, which does neither.
    static func route(_ option: RouteOption) -> String? {
        guard option.extra_minutes > 0 else { return nil }
        let via = option.roads.isEmpty ? "" : " on " + list(option.roads)
        switch (option.leave, option.rejoin) {
        case (nil, nil):
            return "Scenic all the way\(via)."
        case (nil, let rejoin?):
            return "Scenic from the start\(via), then fast roads from \(name(rejoin))."
        case (let leave?, nil):
            return "Fast roads to \(name(leave)), then scenic\(via) to the end."
        case (let leave?, let rejoin?):
            return "Fast roads to \(name(leave)), scenic\(via), "
                + "back on fast roads after \(name(rejoin))."
        }
    }

    static func spoken(_ option: RouteOption, fastest: RouteOption) -> String {
        let minutes = Int(option.extra_minutes.rounded())
        let gain = gainMiles(option, fastest: fastest)
        if minutes <= 0 && gain <= 0 { return "Fastest route" }
        let cost = minutes <= 0 ? "no extra time" : "plus \(CountText.of(minutes, "minute"))"
        return "\(cost), \(CountText.of(gain, "more mile")) of beautiful road"
    }

    private static func name(_ point: SwitchPoint) -> String {
        point.road.isEmpty ? "the scenic road" : point.road
    }

    private static func list(_ roads: [String]) -> String {
        switch roads.count {
        case 0: return ""
        case 1: return roads[0]
        default: return roads.dropLast().joined(separator: ", ") + " and " + roads.last!
        }
    }
}
