import MapKit
import SwiftUI

/// One address row: a coloured dot, a field that drives live autocomplete as
/// the user types, and — while it holds the keyboard — suggestions beneath it.
///
/// Shared by the directions stage and the loop stage, which used to keep two
/// diverging copies of it. Nothing about how it *works* is new; what the
/// redesign changed is where the row's own controls live. Swap and clear sit in
/// the field they act on now, rather than in a header beside the hint text.
struct PlaceField: View {
    let prompt: String
    @Binding var text: String
    let dot: Color
    let role: Endpoint
    @FocusState.Binding var focused: Endpoint?
    let region: MKCoordinateRegion

    var isLocating = false
    var showsMyLocation = true
    var onSubmit: (String) -> Void
    var onChoose: (MKLocalSearchCompletion) -> Void
    var onMyLocation: () -> Void
    var onClear: (() -> Void)?

    @State private var completer = SearchCompleter()

    var body: some View {
        VStack(spacing: 6) {
            HStack(spacing: 10) {
                Circle().fill(dot).frame(width: 9, height: 9)
                TextField(prompt, text: $text)
                    .focused($focused, equals: role)
                    .submitLabel(.search)
                    .autocorrectionDisabled()
                    .foregroundStyle(Color.ink)
                    // Feed each keystroke to the completer — only for the field
                    // actually being typed in, not for programmatic label
                    // updates — ranked around whatever the map is showing.
                    .onChange(of: text) { _, newValue in
                        if focused == role { completer.update(for: newValue, near: region) }
                    }
                    .onSubmit {
                        focused = nil
                        completer.clear()
                        onSubmit(text)
                    }
                if showsMyLocation { myLocationButton }
                if let onClear, !text.isEmpty {
                    Button {
                        onClear()
                        completer.clear()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(Color.ink3)
                            .frame(width: 26, height: 26)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Clear")
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(Color.sunk, in: RoundedRectangle(cornerRadius: 13))
            .overlay {
                RoundedRectangle(cornerRadius: 13)
                    .stroke(Color.amber, lineWidth: focused == role ? 2 : 0)
            }

            if focused == role { suggestionList }
        }
    }

    /// Fill the field with wherever the driver is standing. It sits in the row
    /// itself, not only in the dropdown, because "route me from here" is the
    /// common case and shouldn't need a tap to discover.
    private var myLocationButton: some View {
        Button {
            focused = nil
            completer.clear()
            onMyLocation()
        } label: {
            Group {
                if isLocating { ProgressView().controlSize(.small) }
                else { Image(systemName: "location.fill") }
            }
            .frame(width: 28, height: 28)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(Color.amberText)
        .disabled(isLocating)
        .accessibilityLabel("Use my current location")
    }

    @ViewBuilder private var suggestionList: some View {
        let rows = Array(completer.suggestions.prefix(5).enumerated())
        if showsMyLocation || !rows.isEmpty {
            VStack(spacing: 0) {
                if showsMyLocation {
                    Button {
                        focused = nil
                        completer.clear()
                        onMyLocation()
                    } label: {
                        Label("My Location", systemImage: "location.fill")
                            .font(.system(size: 15, weight: .medium))
                            .foregroundStyle(Color.amberText)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, 11)
                            .padding(.horizontal, 14)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    if !rows.isEmpty { Divider().overlay(Color.hairline) }
                }

                ForEach(rows, id: \.offset) { index, suggestion in
                    Button {
                        focused = nil
                        completer.clear()
                        onChoose(suggestion)
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(suggestion.title)
                                .font(.system(size: 15))
                                .foregroundStyle(Color.ink)
                            if !suggestion.subtitle.isEmpty {
                                Text(suggestion.subtitle)
                                    .font(.system(size: 12))
                                    .foregroundStyle(Color.ink2)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 10)
                        .padding(.horizontal, 14)
                        // Without an explicit shape, only the *text* is
                        // tappable — the empty space to the right of a short
                        // name like "Rockport, MA" isn't part of the button, so
                        // half the row silently ignores taps.
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    if index < rows.count - 1 { Divider().overlay(Color.hairline) }
                }
            }
            .background(Color.sunk, in: RoundedRectangle(cornerRadius: 13))
        }
    }
}

// MARK: - Shared page furniture

/// The page's back chevron and title row.
struct StageHeader: View {
    let title: String
    var onBack: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onBack) {
                Image(systemName: "chevron.left")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(Color.ink2)
                    .frame(width: 30, height: 30)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Back")
            Text(title)
                .font(.system(size: 19, weight: .semibold))
                .foregroundStyle(Color.ink)
            Spacer(minLength: 0)
        }
        .padding(.leading, -4)
    }
}

/// The filled amber action at the foot of a page. One per screen, never two.
struct PrimaryButton: View {
    let title: String
    var systemImage: String?
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 9) {
                if let systemImage { Image(systemName: systemImage).font(.system(size: 16, weight: .semibold)) }
                Text(title).font(.system(size: 17, weight: .semibold))
            }
            .foregroundStyle(Color.onAmber)
            .frame(maxWidth: .infinity)
            .frame(height: 52)
            .background(Color.amber, in: RoundedRectangle(cornerRadius: 15))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}

struct SecondaryButton: View {
    let title: String
    var systemImage: String?
    var isBusy = false
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if isBusy { ProgressView().controlSize(.small) }
                else if let systemImage { Image(systemName: systemImage).font(.system(size: 15, weight: .medium)) }
                Text(title).font(.system(size: 15.5, weight: .semibold))
            }
            .foregroundStyle(Color.ink)
            .frame(maxWidth: .infinity)
            .frame(height: 48)
            .background(Color.sunk, in: RoundedRectangle(cornerRadius: 15))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(isBusy)
    }
}

/// The chip that opens *What you like*, showing what is actually set.
///
/// A control that states its own value. The old `Tune` button tinted itself
/// when a preference was active, which told you that *something* was set but
/// not what — so the only way to find out was to open the sheet the tint was
/// there to save you opening.
struct TasteChip: View {
    let weights: [String: Double]
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 7) {
                if !raised.isEmpty {
                    HStack(spacing: 3) {
                        ForEach(raised.prefix(2), id: \.apiName) { type in
                            Circle().fill(type.hue).frame(width: 7, height: 7)
                        }
                    }
                }
                Text(summary)
                    .font(.system(size: 12.5, weight: .medium))
                    .foregroundStyle(Color.ink)
                    .lineLimit(1)
                Image(systemName: "chevron.right")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(Color.ink3)
            }
            .padding(.horizontal, 11)
            .padding(.vertical, 6)
            .background(Color.sunk, in: Capsule())
            .contentShape(Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Scenery preferences: \(summary)")
    }

    /// Types raised above neutral, strongest first.
    private var raised: [BeautyType] {
        BeautyType.all
            .map { ($0, weights[$0.apiName] ?? $0.defaultWeight) }
            .filter { $0.1 > BeautyType.neutralWeight + 0.05 }
            .sorted { $0.1 > $1.1 }
            .map(\.0)
    }

    /// Named in the user's terms, not as a count. "Coast & water" is a thing
    /// you asked for; "2 preferences" is a thing the app is keeping score of.
    private var summary: String {
        let names = raised.prefix(2).map { $0.label.components(separatedBy: " &").first ?? $0.label }
        if names.isEmpty { return "No preference" }
        return names.joined(separator: " & ")
    }
}
