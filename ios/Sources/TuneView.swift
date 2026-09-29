import SwiftUI

/// *What you like* — one slider per beauty type, saying what kind of scenery
/// the router should chase.
///
/// The main dial still sets the overall strength; these only shape *what kind*.
/// Editing one re-routes in the background, so the updated route is already
/// waiting when the sheet closes.
///
/// Two changes from the sheet it replaces, both small. Each slider carries its
/// type's colour, so this screen, the breakdown bars and the map speak one
/// language. And the way in is `TasteChip`, which states what is set rather
/// than only that something is.
struct TuneView: View {
    @Bindable var model: RouteModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Drag toward what you’d rather drive past. Centred means no preference.")
                        .font(.system(size: 13.5))
                        .foregroundStyle(Color.ink2)

                    ForEach(BeautyType.all) { type in
                        slider(for: type)
                    }

                    Text("Routes update in the background as you drag, so the new one is "
                         + "waiting when you close this.")
                        .font(.system(size: 12))
                        .foregroundStyle(Color.ink3)
                        .padding(.top, 2)
                }
                .padding(Metric.margin)
            }
            .background(Color.paper)
            .navigationTitle("What you like")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Reset") { model.resetWeights() }
                        .disabled(!model.isTuned)
                        .tint(Color.amberText)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }.tint(Color.amberText)
                }
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }

    /// One labelled slider bound to a beauty type's weight. Re-routes when the
    /// user lets go (not on every pixel of the drag), so we don't spam the
    /// backend mid-gesture.
    private func slider(for type: BeautyType) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 8) {
                RoundedRectangle(cornerRadius: 3)
                    .fill(type.hue)
                    .frame(width: 10, height: 10)
                Text(type.label)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(Color.ink)
                Spacer(minLength: 6)
                Text(emphasis(for: type))
                    .font(.system(size: 12))
                    .foregroundStyle(Color.ink2)
            }
            Slider(value: binding(for: type), in: BeautyType.weightRange) { editing in
                if !editing { Task { await model.computeRoute() } }
            }
            .tint(type.hue)
            .accessibilityLabel(type.label)
            .accessibilityValue(emphasis(for: type).isEmpty ? "no preference" : emphasis(for: type))
            // Only `town` carries one. A slider that starts pinned to the left
            // with no explanation reads as a bug, not as a decision.
            if let note = type.note {
                Text(note)
                    .font(.system(size: 12))
                    .foregroundStyle(Color.ink3)
            }
        }
    }

    private func binding(for type: BeautyType) -> Binding<Double> {
        Binding(get: { model.weights[type.apiName] ?? type.defaultWeight },
                set: { model.weights[type.apiName] = $0 })
    }

    /// A one-word hint of where a slider sits relative to neutral.
    ///
    /// Against `neutralWeight` and not against the type's own default, because
    /// this describes the slider the user is looking at — town parked at zero
    /// really does mean "less", and saying nothing there would be a worse
    /// answer than saying so.
    private func emphasis(for type: BeautyType) -> String {
        let weight = model.weights[type.apiName] ?? type.defaultWeight
        if weight > BeautyType.neutralWeight + 0.05 { return "more" }
        if weight < BeautyType.neutralWeight - 0.05 { return "less" }
        return ""
    }
}
