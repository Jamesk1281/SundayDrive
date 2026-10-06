import SwiftUI

/// Which way the loop heads off: eight points on a dial, tap one to go there.
///
/// It replaced a "Try another direction (5)" button that stepped through the
/// directions in a fixed order. That asked a driver who wanted the coast to
/// press it until the coast came up, with no way to tell how many presses away
/// it was. The server already answered the real question — `alternatives` is
/// the list of directions that hold a loop this long — so the dial shows all
/// eight and greys out the ones it did not list, rather than hiding them: a
/// missing west is information ("that's the ocean"), not clutter.
struct LoopCompass: View {
    /// The octant the loop on screen heads off in.
    let current: String
    /// The octants that hold a loop of this length from this start.
    let available: Set<String>
    /// The octant whose loop is on its way, if any.
    let pending: String?
    var choose: (String) -> Void

    /// Wide enough that neighbouring points sit just over 44 pt apart centre to
    /// centre, so each 44 pt target is its own. That is the chord, not the arc:
    /// 2 × 58 × sin 22.5° ≈ 44.4, so any smaller radius makes them overlap.
    static let diameter: CGFloat = 160
    private static let radius: CGFloat = 58
    private static let point: CGFloat = 40

    /// Cumulative rather than `index × 45`, so NW to N turns 45° clockwise
    /// instead of 315° the long way round.
    @State private var needleAngle: Double?

    var body: some View {
        ZStack {
            Circle().fill(Color.sunk)
            Circle()
                .strokeBorder(Color.hairline, lineWidth: 1)
                .padding(Self.diameter / 2 - Self.radius + Self.point / 2 + 4)

            Needle()
                .fill(Color.amber)
                .frame(width: 10, height: 2 * (Self.radius - Self.point / 2 - 4))
                .rotationEffect(.degrees(needleAngle ?? Self.angle(of: current)))
                .animation(.spring(duration: 0.45, bounce: 0.25), value: needleAngle)
                .accessibilityHidden(true)
            Circle().fill(Color.ink2).frame(width: 7, height: 7)

            ForEach(LoopAlternative.allSectors, id: \.self) { sector in
                pointButton(sector)
                    .offset(Self.offset(of: sector))
            }
        }
        .frame(width: Self.diameter, height: Self.diameter)
        // Seeded on appear, so the first change has an angle to turn from.
        // Left nil, that change renders at the new angle unanimated and the
        // needle jumps.
        .onAppear { needleAngle = Self.angle(of: current) }
        .onChange(of: current) { _, new in
            let from = needleAngle ?? Self.angle(of: new)
            let delta = (Self.angle(of: new) - from).truncatingRemainder(dividingBy: 360)
            needleAngle = from + (delta > 180 ? delta - 360 : delta < -180 ? delta + 360 : delta)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Which way the loop heads")
    }

    private func pointButton(_ sector: String) -> some View {
        let isCurrent = sector == current
        let isAvailable = available.contains(sector)
        let name = LoopAlternative(sector: sector, candidates: 0).name
        return Button { choose(sector) } label: {
            ZStack {
                if pending == sector {
                    ProgressView().controlSize(.small)
                } else {
                    Text(sector)
                        .font(.system(size: sector.count == 1 ? 15 : 12.5,
                                      weight: .semibold, design: .rounded))
                }
            }
            .frame(width: Self.point, height: Self.point)
            .foregroundStyle(isCurrent ? Color.onAmber
                             : isAvailable ? Color.ink : Color.ink3.opacity(0.4))
            .background(Circle().fill(isCurrent ? Color.amber
                                      : isAvailable ? Color.card : Color.clear))
            .frame(width: 44, height: 44)
            .contentShape(Circle())
        }
        .buttonStyle(.plain)
        // Not disabled when current: a disabled button is drawn faded, and the
        // one point that must read clearest is the one you are on. Tapping it
        // is a no-op in `LoopModel.head` instead. The server can serve a loop in
        // a direction it does not list as an alternative, so `current` is
        // checked here rather than assumed to be in `available`.
        .disabled(!isAvailable && !isCurrent)
        .accessibilityLabel(name)
        .accessibilityAddTraits(isCurrent ? .isSelected : [])
        .accessibilityHint(isAvailable || isCurrent ? "" : "No loop this long that way")
    }

    private static func angle(of sector: String) -> Double {
        Double(LoopAlternative.allSectors.firstIndex(of: sector) ?? 0) * 45
    }

    private static func offset(of sector: String) -> CGSize {
        let a = angle(of: sector) * .pi / 180
        return CGSize(width: radius * sin(a), height: -radius * cos(a))
    }
}

/// A slim diamond pointing up, its long half towards the direction.
private struct Needle: Shape {
    func path(in rect: CGRect) -> Path {
        let c = CGPoint(x: rect.midX, y: rect.midY)
        var p = Path()
        p.move(to: CGPoint(x: c.x, y: rect.minY))
        p.addLine(to: CGPoint(x: rect.maxX, y: c.y))
        p.addLine(to: CGPoint(x: c.x, y: c.y + rect.height * 0.18))
        p.addLine(to: CGPoint(x: rect.minX, y: c.y))
        p.closeSubpath()
        return p
    }
}
