import SwiftUI

/// The first screen: the two shapes a drive can have, and where you went last.
///
/// Every navigation app opens with a destination field. This one should not,
/// because one of its two products has no destination — and loop mode used to
/// sit behind a segmented control, inside a sheet, under a destination field it
/// does not use. Here it is a row, and **tapping it is one tap to a finished
/// drive**: it already has a place (here) and a length (whatever was asked for
/// last time), so there is no form between the tap and the map.
///
/// No headline above the rows. The two of them say what they are, and a
/// greeting would be the most prominent thing on a screen whose job is to get
/// out of the way.
struct HomeView: View {
    @Bindable var model: RouteModel
    @Binding var stage: PlanStage

    @State private var recents: [Recent] = []

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                intentRow(title: "Directions",
                          subtitle: "Search for a destination",
                          systemImage: "magnifyingglass",
                          tint: .slate, wash: .slateWash) {
                    stage = .directions
                }

                intentRow(title: "Loop",
                          subtitle: "From here, about \(loopEstimate)",
                          systemImage: "arrow.trianglehead.clockwise",
                          tint: .amberText, wash: .amberWash) {
                    stage = .loop
                    // Only if there is nothing to show already — coming back to
                    // a loop you were looking at should not throw it away and
                    // spend a fix and a request reproducing it.
                    if model.loops.response == nil, model.loops.start == nil {
                        Task { await model.loops.useMyLocation() }
                    }
                }

                if !recents.isEmpty {
                    Text("Recent").sectionLabel().padding(.top, 6)
                    VStack(spacing: 0) {
                        ForEach(Array(recents.enumerated()), id: \.element.id) { index, recent in
                            recentRow(recent)
                            if index < recents.count - 1 { Divider().overlay(Color.hairline) }
                        }
                    }
                }
            }
            .padding(.horizontal, Metric.margin)
            .padding(.top, 18)
            .padding(.bottom, 24)
        }
        .scrollBounceBehavior(.basedOnSize)
        .task { recents = Recents.load() }
        .onChange(of: stage) { _, new in if new == .home { recents = Recents.load() } }
    }

    private var loopEstimate: String {
        TimeText.compact(minutes: model.loops.estimatedMinutes(forKm: model.loops.targetKm))
    }

    private func intentRow(title: String, subtitle: String, systemImage: String,
                           tint: Color, wash: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 13) {
                Image(systemName: systemImage)
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(tint)
                    .frame(width: 38, height: 38)
                    .background(wash, in: RoundedRectangle(cornerRadius: 12))
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(Color.ink)
                    Text(subtitle)
                        .font(.system(size: 13.5))
                        .foregroundStyle(Color.ink2)
                }
                Spacer(minLength: 8)
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Color.ink3)
            }
            .padding(.horizontal, 17)
            .padding(.vertical, 16)
            .background(Color.card, in: RoundedRectangle(cornerRadius: Metric.cardRadius))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    /// Tapping a recent sets the destination and starts from where you are,
    /// which is the trip somebody taking it again is actually taking.
    private func recentRow(_ recent: Recent) -> some View {
        Button {
            model.end = recent.coordinate
            model.endQuery = recent.name
            stage = .directions
            if model.start == nil {
                Task { await model.useMyLocation() }
            } else {
                Task { await model.computeRoute() }
            }
        } label: {
            HStack(spacing: 12) {
                Circle().fill(Color.endPin).frame(width: 8, height: 8)
                VStack(alignment: .leading, spacing: 1) {
                    Text(recent.name)
                        .font(.system(size: 15.5, weight: .medium))
                        .foregroundStyle(Color.ink)
                        .lineLimit(1)
                    if !recent.subtitle.isEmpty {
                        Text(recent.subtitle)
                            .font(.system(size: 12.5))
                            .foregroundStyle(Color.ink2)
                            .lineLimit(1)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(.vertical, 11)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}
