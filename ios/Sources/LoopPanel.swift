import MapKit
import SwiftUI

/// The loop tab's half of the bottom sheet: one start field, one distance
/// slider, and a button that keeps producing different drives.
///
/// Deliberately shorter than `RoutePanel`. There is no destination to search
/// for, no swap, and no fastest-versus-scenic comparison to read, because the
/// distance slider has already decided the trade — every loop it offers is the
/// same length, so they differ only in where they go.
struct LoopPanel: View {
    @Bindable var model: LoopModel
    /// Starts the drive. Lives with `RouteModel`, which owns the one navigation
    /// session whichever tab planned it.
    let onStart: (LoopResponse) -> Void

    @State private var completer = SearchCompleter()
    @FocusState private var startFocused: Bool
    /// Whether the scenery bars are showing, matching `RouteResults`: the
    /// sentence is what a loop gets read for, the bars are the working.
    @State private var showingBreakdown = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            startField
            distanceSlider

            if model.isLoading {
                ProgressView().frame(maxWidth: .infinity)
            }
            if let error = model.errorText {
                Text(error).font(.caption).foregroundStyle(.red)
            }
            if let response = model.response {
                results(response)
                actions(response)
            } else if model.start == nil, !model.isLoading {
                Text("Pick a starting point and a distance. There's no "
                     + "destination to choose — that's the part this does for you.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Inputs

    private var startField: some View {
        VStack(spacing: 6) {
            HStack(spacing: 8) {
                Circle().fill(Color.scenic).frame(width: 9, height: 9)
                TextField("Start and finish here", text: $model.startQuery)
                    .focused($startFocused)
                    .submitLabel(.search)
                    .autocorrectionDisabled()
                    .onChange(of: model.startQuery) { _, newValue in
                        if startFocused {
                            completer.update(for: newValue, near: model.searchRegion)
                        }
                    }
                    .onSubmit {
                        startFocused = false
                        completer.clear()
                        Task { await model.search(model.startQuery) }
                    }
                myLocationButton
                if model.start != nil {
                    Button {
                        model.clear()
                        completer.clear()
                    } label: { Image(systemName: "xmark.circle") }
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)
                        .accessibilityLabel("Clear the starting point")
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 11)
            .background(.quaternary, in: RoundedRectangle(cornerRadius: 10))

            if startFocused { suggestionList }
        }
    }

    private var myLocationButton: some View {
        Button {
            startFocused = false
            completer.clear()
            Task { await model.useMyLocation() }
        } label: {
            Group {
                if model.isLocatingUser {
                    ProgressView().controlSize(.small)
                } else {
                    Image(systemName: "location.fill")
                }
            }
            .frame(width: 30, height: 30)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(Color.scenic)
        .disabled(model.isLocatingUser)
        .accessibilityLabel("Loop from my current location")
    }

    @ViewBuilder private var suggestionList: some View {
        let rows = Array(completer.suggestions.prefix(5).enumerated())
        VStack(spacing: 0) {
            Button {
                startFocused = false
                completer.clear()
                Task { await model.useMyLocation() }
            } label: {
                Label("My Location", systemImage: "location.fill")
                    .foregroundStyle(Color.scenic)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 8).padding(.horizontal, 12)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if !rows.isEmpty { Divider() }

            ForEach(rows, id: \.offset) { index, suggestion in
                Button {
                    startFocused = false
                    completer.clear()
                    Task { await model.choose(suggestion) }
                } label: {
                    VStack(alignment: .leading, spacing: 1) {
                        Text(suggestion.title)
                        if !suggestion.subtitle.isEmpty {
                            Text(suggestion.subtitle)
                                .font(.caption2).foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 8).padding(.horizontal, 12)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                if index < rows.count - 1 { Divider() }
            }
        }
        .background(.quaternary, in: RoundedRectangle(cornerRadius: 10))
    }

    /// How far to drive. Asks for a new loop only when the user lets go —
    /// mid-drag it would be a request per tick, and each one is ~0.65 s of work
    /// on the server.
    ///
    /// Shown in miles, like everything else in the app, while the value stays in
    /// kilometers because that is what the API takes.
    private var distanceSlider: some View {
        VStack(spacing: 2) {
            HStack {
                Text("\(LoopModel.minKm.wholeMilesFromKm) mi").font(.caption2)
                Slider(value: $model.targetKm,
                       in: LoopModel.minKm...LoopModel.maxKm) { editing in
                    if !editing, model.start != nil {
                        Task { await model.generate() }
                    }
                }
                Text("\(LoopModel.maxKm.wholeMilesFromKm) mi").font(.caption2)
            }
            Text("about \(model.targetKm.wholeMilesFromKm) miles")
                .font(.caption2).foregroundStyle(.secondary)
                .accessibilityLabel("Loop distance, about \(model.targetKm.wholeMilesFromKm) miles")
        }
    }

    // MARK: - Results

    /// The same shape `RouteResults` uses, minus the price: the drive, what it
    /// buys, what it is like, then the working.
    ///
    /// A loop has no fastest arm to be compared against — the distance slider
    /// has already fixed the length — so where a route prints `+38 min · 25
    /// beautiful miles` this prints only the second half. Nothing is being
    /// traded, so nothing is being priced.
    private func results(_ response: LoopResponse) -> some View {
        let meta = response.meta
        let described = RouteDescription(response.loop.properties)
        return VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text("\(Int(meta.minutes.rounded())) min · \(meta.km.wholeMilesFromKm) mi")
                    .font(.title2.weight(.semibold))
                    // Tabular figures, so shuffling to another direction does
                    // not shift the line sideways under the reader's eye.
                    .monospacedDigit()
                Text(summary(meta))
                    .font(.subheadline)
                    .foregroundStyle(Color.scenic)
            }
            .accessibilityElement(children: .combine)

            // What the loop is like, and where it goes. `heading` rides on the
            // via line rather than taking a row of its own — and stands alone
            // when no road carries enough of the drive to be named, which is
            // exactly when a compass direction is all there is to say.
            VStack(alignment: .leading, spacing: 2) {
                if let character = described.character {
                    Text(character).font(.subheadline)
                }
                Text(described.via.map { "\($0) · heading \(meta.sector)" }
                     ?? "Heading \(meta.sector)")
                    .font(.caption).foregroundStyle(.secondary)
            }

            // Always shown, not only when bad: it is the one number that tells a
            // driver their loop is really an out-and-back.
            if meta.repeated_km >= 0.1 {
                Label("\(meta.repeated_km.milesFromKm, format: .number.precision(.fractionLength(1))) mi doubles back",
                      systemImage: "arrow.uturn.left")
                    .font(.caption2)
                    .foregroundStyle(meta.repeatedFraction > 0.15 ? .orange : .secondary)
            } else {
                Label("No road driven twice", systemImage: "checkmark.circle")
                    .font(.caption2).foregroundStyle(.secondary)
            }

            // The server's own words when the geography could not answer.
            if let note = response.note {
                Text(note).font(.caption2).foregroundStyle(.orange)
            }

            breakdown(of: response.loop.properties, beautifulScore: meta.beautiful_score)
        }
    }

    /// The per-feature mileage, folded away — and carrying the definition of
    /// "beautiful" on its label, which is where the word is finally cashed out
    /// into a number. It used to sit under a card as "scoring 7+ of 10"; it
    /// belongs with the working, not with the headline.
    @ViewBuilder private func breakdown(of props: RouteProps,
                                        beautifulScore: Double) -> some View {
        let items = props.sceneryBreakdown
        if !items.isEmpty {
            let maxKm = max(1, items.map(\.km).max() ?? 1)
            DisclosureGroup(isExpanded: $showingBreakdown) {
                VStack(alignment: .leading, spacing: 3) {
                    ForEach(items, id: \.label) { item in
                        SceneryBar(label: item.label, km: item.km, maxKm: maxKm)
                    }
                }
                .padding(.top, 6)
            } label: {
                Text("Scenery breakdown · beautiful is \(Int(beautifulScore))+ of 10")
            }
            .font(.caption)
            .tint(.secondary)
        }
    }

    /// "19 beautiful miles, back where you started."
    ///
    /// The 0–10 mean used to be the middle clause. It is gone because a second
    /// scale on the same screen asks the driver to hold two rulers at once, and
    /// the mean is the one nobody has a feel for. `mean_score` is still decoded
    /// and still what the traces are calibrated against; it is just not printed.
    ///
    /// "of your 25 mi" went with the cards. The total is now the line directly
    /// above this one, so restating it here made the same number appear twice
    /// in two adjacent rows — and this row is the only place the beautiful
    /// count appears at all, so it leads with it.
    private func summary(_ meta: LoopMeta) -> AttributedString {
        let miles = meta.beautiful_km.wholeMilesFromKm
        let markdown = "**\(miles) beautiful \(miles == 1 ? "mile" : "miles")**, "
            + "back where you started"
        return (try? AttributedString(markdown: markdown)) ?? AttributedString(markdown)
    }

    // MARK: - Actions

    private func actions(_ response: LoopResponse) -> some View {
        VStack(spacing: 8) {
            Button {
                Task { await model.regenerate() }
            } label: {
                Group {
                    if model.isRegenerating {
                        ProgressView().controlSize(.small)
                    } else {
                        // Says how many directions there really are rather than
                        // implying endless variety: from a coastal start the
                        // geography offers five or six, not eight.
                        Label(model.directionCount > 1
                              ? "Try another direction (\(model.directionCount))"
                              : "Try another loop",
                              systemImage: "arrow.triangle.2.circlepath")
                    }
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .disabled(model.isRegenerating || model.isLoading)

            Button {
                onStart(response)
            } label: {
                Label("Start this loop", systemImage: "location.north.line.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.scenic)
        }
    }
}
