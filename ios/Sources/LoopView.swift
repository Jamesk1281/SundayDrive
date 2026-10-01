import SwiftUI

/// The loop: one place, one length, one drive back to where you started.
///
/// **The dial reads in time, not distance.** The request still goes to
/// `/api/loop` in kilometres because that is what it takes; the label converts,
/// and the factor is measured rather than assumed — every response re-fits
/// `LoopModel.minutesPerKm` from its own `minutes` and `km`, so the estimate
/// calibrates itself on this driver's roads with no backend change, and the
/// loop's real time replaces it the moment one lands.
struct LoopView: View {
    @Bindable var model: RouteModel
    @Binding var stage: PlanStage
    @Binding var isSearching: Bool
    @Binding var showingTaste: Bool

    @FocusState private var focused: Endpoint?

    private var loops: LoopModel { model.loops }

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 13) {
                    StageHeader(title: "Loop") {
                        focused = nil
                        stage = .home
                    }

                    PlaceField(prompt: "Start and finish here",
                               text: Binding(get: { loops.startQuery },
                                             set: { loops.startQuery = $0 }),
                               dot: .amber, role: .start, focused: $focused,
                               region: loops.searchRegion,
                               isLocating: loops.isLocatingUser,
                               onSubmit: { q in Task { await loops.search(q) } },
                               onChoose: { s in Task { await loops.choose(s) } },
                               onMyLocation: { Task { await loops.useMyLocation() } },
                               onClear: loops.start == nil ? nil : { loops.clear() })

                    distanceDial

                    if let error = loops.errorText {
                        Text(error).font(.system(size: 13)).foregroundStyle(Color.alert)
                    }
                    if loops.isLoading {
                        ProgressView().frame(maxWidth: .infinity).padding(.vertical, 18)
                    }

                    if let response = loops.response {
                        loopCard(response)
                        breakdown(response)
                    } else if loops.start == nil, !loops.isLoading {
                        Text("Pick a starting point and how long you have. There’s no "
                             + "destination to choose — that’s the part this does for you.")
                            .font(.system(size: 13.5))
                            .foregroundStyle(Color.ink2)
                    }
                }
                .padding(.horizontal, Metric.margin)
                .padding(.top, 14)
                .padding(.bottom, 18)
            }
            .scrollBounceBehavior(.basedOnSize)
            .scrollDismissesKeyboard(.interactively)

            if let response = loops.response {
                VStack(spacing: 9) {
                    SecondaryButton(title: loops.directionCount > 1
                                    ? "Try another direction (\(loops.directionCount))"
                                    : "Try another loop",
                                    systemImage: "arrow.triangle.2.circlepath",
                                    isBusy: loops.isRegenerating) {
                        Task { await loops.regenerate() }
                    }
                    PrimaryButton(title: "Start driving", systemImage: "location.north.fill") {
                        model.startLoopDrive(response)
                    }
                }
                .padding(.horizontal, Metric.margin)
                .padding(.bottom, 10)
            }
        }
        .onChange(of: focused) { _, value in isSearching = value != nil }
        .onDisappear { isSearching = false }
    }

    // MARK: - How long

    private var distanceDial: some View {
        VStack(alignment: .leading, spacing: 2) {
            // Asks for a new loop only when the user lets go — mid-drag it
            // would be a request per tick, and each one is ~0.65 s of work on
            // the server.
            Slider(value: Binding(get: { loops.targetKm }, set: { loops.targetKm = $0 }),
                   in: LoopModel.minKm...LoopModel.maxKm) { editing in
                if !editing, loops.start != nil { Task { await loops.generate() } }
            }
            .tint(Color.amber)
            .accessibilityLabel("How long the loop should take")
            .accessibilityValue("about \(TimeText.compact(minutes: estimate)), "
                                + "\(loops.targetKm.wholeMilesFromKm) miles")

            // Not the small-caps label style the rest of the design uses for
            // ends: "3 HR 50" is a duration shouted, and these two move as the
            // estimate re-fits.
            HStack {
                Text(TimeText.compact(minutes: loops.estimatedMinutes(forKm: LoopModel.minKm)))
                Spacer()
                Text(TimeText.compact(minutes: loops.estimatedMinutes(forKm: LoopModel.maxKm)))
            }
            .font(.system(size: 12, weight: .medium))
            .foregroundStyle(Color.slate)
            .monospacedDigit()

            HStack(spacing: 5) {
                Text("about")
                Text(TimeText.compact(minutes: estimate))
                    .fontWeight(.semibold)
                    .foregroundStyle(Color.ink)
                    .monospacedDigit()
                Text("· \(loops.targetKm.wholeMilesFromKm) mi")
            }
            .font(.system(size: 14))
            .foregroundStyle(Color.ink2)
            .padding(.top, 7)
            .accessibilityHidden(true)
        }
    }

    private var estimate: Double { loops.estimatedMinutes(forKm: loops.targetKm) }

    // MARK: - The loop

    private func loopCard(_ response: LoopResponse) -> some View {
        let meta = response.meta
        return VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .firstTextBaseline, spacing: 7) {
                Text(TimeText.compact(minutes: meta.minutes))
                    .font(.figure(27))
                    .foregroundStyle(Color.ink)
                    .monospacedDigit()
                Text("· \(meta.km.wholeMilesFromKm) mi")
                    .font(.figure(20, .medium))
                    .foregroundStyle(Color.ink2)
                    .monospacedDigit()
            }
            Text("\(CountText.of(meta.beautiful_km.wholeMilesFromKm, "mile")) of it beautiful")
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(Color.amberText)
                .padding(.top, 6)

            HStack(spacing: 14) {
                Label("heading \(headingName(meta.sector))", systemImage: "location.north")
                // Always shown, not only when bad: it is the one number that
                // tells a driver their loop is really an out-and-back. It is no
                // longer orange, because in this palette amber is the brand and
                // only red means trouble.
                if meta.repeated_km >= 0.1 {
                    Label("\(meta.repeated_km.milesFromKm, format: .number.precision(.fractionLength(1))) mi doubles back",
                          systemImage: "arrow.uturn.left")
                        .foregroundStyle(meta.repeatedFraction > 0.15 ? Color.alert : Color.ink2)
                } else {
                    Label("no road driven twice", systemImage: "checkmark.circle")
                }
            }
            .font(.system(size: 12))
            .foregroundStyle(Color.ink2)
            .padding(.top, 9)

            // The server's own words when the geography could not answer.
            if let note = response.note {
                Text(note)
                    .font(.system(size: 12.5))
                    .foregroundStyle(Color.ink2)
                    .padding(.top, 8)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 16)
        .padding(.vertical, 15)
        .background(Color.card, in: RoundedRectangle(cornerRadius: Metric.cardRadius))
    }

    private func headingName(_ sector: String) -> String {
        LoopAlternative(sector: sector, candidates: 0).name.lowercased()
    }

    private func breakdown(_ response: LoopResponse) -> some View {
        let rows = response.loop.properties.sceneryBreakdown
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
