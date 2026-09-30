import SwiftUI
import UIKit

// The whole visual system, in one file, in code rather than in an asset
// catalogue. Two reasons: a colour here can carry the paragraph that explains
// why it is that value, which a `.colorset` JSON cannot; and every pair below
// is a *semantic* pair (light and dark), so keeping them adjacent is how they
// stay in step.
//
// See `docs/interface-design.md` §7.

extension Color {

    /// A colour that resolves against the view's current appearance.
    ///
    /// `UIColor`'s dynamic provider rather than two `Color`s and an
    /// `@Environment(\.colorScheme)` read, because this has to work inside
    /// `MapKit` overlays and `UIKit`-backed controls too, and because a view
    /// that has to know the appearance to pick a colour is a view that will
    /// eventually forget to.
    static func adaptiveHue(light: UInt32, dark: UInt32) -> Color {
        adaptive(light: light, dark: dark)
    }

    fileprivate static func adaptive(light: UInt32, dark: UInt32) -> Color {
        Color(uiColor: UIColor { traits in
            UIColor(rgb: traits.userInterfaceStyle == .dark ? dark : light)
        })
    }

    // MARK: - Surfaces

    /// The page. Warm off-white, warm near-black — not #FFF and not #000, so
    /// the amber has something to sit against rather than glare off.
    ///
    /// Both lean toward the app icon's cream (`#F3E7CF`) and ink (`#2B211B`),
    /// so that tapping the badge lands on the same object. Light paper stops
    /// short of the cream itself: at `#F3E7CF`, `amberText` falls to 4.41:1,
    /// and the surfaces moving is cheaper than beauty's colour moving. Dark
    /// paper takes only a trace of the brown; it must not become a light
    /// source in a windscreen mount (§7.6).
    static let paper    = adaptive(light: 0xF8F1E4, dark: 0x15120F)
    /// Anything raised off the page: the ledger, the intent rows, every card
    /// floating over the driving map.
    static let card     = adaptive(light: 0xFFFCF5, dark: 0x1F1A15)
    /// Anything sunk into it: fields, tracks, the secondary button.
    static let sunk     = adaptive(light: 0xF2EADB, dark: 0x241E18)
    static let hairline = adaptive(light: 0xE6DAC4, dark: 0x362D25)

    // MARK: - Text

    /// Every one of these clears 4.5:1 on `paper`, `card` *and* `sunk` — sunk
    /// is the hard one, because fields and secondary buttons carry text too.
    static let ink      = adaptive(light: 0x2B211B, dark: 0xF5ECDD)
    static let ink2     = adaptive(light: 0x64574A, dark: 0xADA08F)
    static let ink3     = adaptive(light: 0x716453, dark: 0x978A78)

    // MARK: - The two quantities

    /// **Beauty.** The scenic route line, every figure counting beautiful
    /// miles, the primary action.
    ///
    /// It replaced a mint green (`rgb(0.22, 0.83, 0.62)`) for one reason that
    /// is about the map rather than about taste: the scenic line has to stay
    /// legible over a basemap whose parks, forests and golf courses are green,
    /// and that is exactly the country this app routes across. Amber sits
    /// opposite the basemap's greens and blues, holds up in direct sun at mid
    /// luminance, and is not Apple's directions blue.
    ///
    /// Two values, because a 6 pt line and a 13 pt caption are different
    /// problems: `amber` is the line and the fill, `amberText` is the same hue
    /// pushed to 4.5:1 against `paper`.
    static let amber     = adaptive(light: 0xE07B2E, dark: 0xF09A4B)
    static let amberText = adaptive(light: 0xA5541A, dark: 0xF0A462)
    static let amberWash = adaptive(light: 0x22E07B2E, dark: 0x29F09A4B)
    /// Text on a filled amber button. Near-black in both appearances — amber is
    /// too light to carry white.
    static let onAmber   = adaptive(light: 0x2A1706, dark: 0x20150A)

    /// **Time.** The fastest arm, every figure counting minutes you are not
    /// choosing to spend. Deliberately unglamorous: choosing fast is not
    /// celebrated here.
    static let slate     = adaptive(light: 0x5C6771, dark: 0x9AA3AB)
    static let slateWash = adaptive(light: 0x1C5C6771, dark: 0x249AA3AB)

    /// Trouble, and only trouble. **Amber never means warning in this app** —
    /// which is why off route, a recording fault and the destructive
    /// confirmations are all this and nothing else. Before the palette change
    /// `.orange` carried three unrelated meanings at once.
    static let alert = adaptive(light: 0xB3352C, dark: 0xE5675C)

    // MARK: - Endpoints

    static let startPin = adaptive(light: 0x3E9E6B, dark: 0x4FB287)
    static let endPin   = adaptive(light: 0xC6453A, dark: 0xE06A5C)
}

extension UIColor {
    /// `0xRRGGBB`, or `0xAARRGGBB` when the top byte is set.
    fileprivate convenience init(rgb: UInt32) {
        let hasAlpha = rgb > 0xFFFFFF
        let a = hasAlpha ? CGFloat((rgb >> 24) & 0xFF) / 255 : 1
        self.init(red:   CGFloat((rgb >> 16) & 0xFF) / 255,
                  green: CGFloat((rgb >>  8) & 0xFF) / 255,
                  blue:  CGFloat( rgb        & 0xFF) / 255,
                  alpha: a)
    }
}

// MARK: - Type

extension Font {
    /// Figures, and the driving instruction. Rounded reads faster at a glance,
    /// which is the whole argument for it, and it costs nothing — it is a
    /// system face.
    ///
    /// **Nowhere else.** Everything a user reads as prose is SF Pro. Two faces
    /// with one rule between them is the whole typographic system; an earlier
    /// draft added New York for a few editorial lines, and the lines it invited
    /// were more of a problem than the face.
    static func figure(_ size: CGFloat, _ weight: Font.Weight = .semibold) -> Font {
        .system(size: size, weight: weight, design: .rounded)
    }
}

extension View {
    /// The small-caps section label used everywhere: the credit line, the
    /// ledger's column heads, "WHAT YOU'LL PASS", "BEFORE YOU DRIVE".
    func sectionLabel(_ color: Color = .ink3) -> some View {
        self.font(.system(size: 11, weight: .semibold))
            .tracking(1.1)
            .textCase(.uppercase)
            .foregroundStyle(color)
    }
}

// MARK: - Metrics

enum Metric {
    /// The page margin, unchanged from the sheet it replaces.
    static let margin: CGFloat = 20
    static let gutter: CGFloat = 12
    static let cardRadius: CGFloat = 18
    static let controlRadius: CGFloat = 14

    /// How much of the driving map's bottom edge is left alone.
    ///
    /// **This is a compliance number, not a taste one.** Apple's map logo and
    /// legal link are drawn in the bottom-left of whatever view MapKit renders
    /// into; ADPLA Attachment 6 §2.1 requires them visible and §4 names
    /// obscuring the logo as grounds for revoking MapKit access. The planning
    /// screen solves this by construction — the map is a card and the page
    /// starts below it. The driving screen is full-bleed, so it reserves this
    /// instead, *on top of* the safe-area inset the furniture already adds.
    ///
    /// On a heading-up map the bottom of the screen is the road already driven,
    /// so reserving it costs the driver nothing.
    static let appleKeep: CGFloat = 48
}
