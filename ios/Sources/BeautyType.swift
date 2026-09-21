import SwiftUI

/// One user-tunable scenery type, mirroring the server's `BEAUTY_TYPES`
/// (pipeline/router.py).
///
/// `apiName` is the key the backend expects — it's sent as the query parameter
/// `w_<apiName>` (e.g. `w_coast`). `label` is the friendly name shown on the
/// tune screen. A weight of 1.0 is neutral (the calibrated default); higher
/// leans into that type, 0 ignores it.
struct BeautyType: Identifiable {
    let apiName: String
    let label: String

    /// Where this type's slider starts before the user touches it.
    ///
    /// Usually `neutralWeight` — the calibrated blend, which is what "no
    /// preference" means. `town` is the exception and the reason this is a
    /// per-type value rather than one constant; see `note`.
    var defaultWeight: Double = BeautyType.neutralWeight

    /// Why this type does not start where the others do, shown under its
    /// slider. Nil for the types that start neutral, which need no explaining.
    var note: String?

    var id: String { apiName }

    /// The six tunable types, in the order they appear on the tune screen.
    /// Keep this list in sync with BEAUTY_TYPES in pipeline/router.py — the
    /// `apiName`s must match the server's, or its weights are ignored.
    static let all: [BeautyType] = [
        BeautyType(apiName: "coast",  label: "Coast"),
        BeautyType(apiName: "forest", label: "Forest & parks"),
        // Off by default, alone among the six. `c_urban` is the one component
        // the 2026-08-25 drive marks scored *below* chance — 0.35 separation
        // against a 0.50 coin, the only one of nine pointing the wrong way —
        // while carrying weight 0.14 in score.py's blend. Measured on the
        // Massachusetts graph, sending w_town=0 costs nothing to buy back:
        // Needham→Wachusett at pref 1.0 sheds 12.1 km of built-up road, gains
        // 5.0 km of forest, and arrives 5.1 minutes *earlier*;
        // Boston→Northampton at pref 0.5 sheds 12.4 km and is 1.0 min faster.
        // Coastal trips are unaffected (Needham→Rockport: no change at all),
        // because there the towns are on the coast and the coast is what buys
        // them.
        //
        // Left tunable rather than deleted: the component conflates a village
        // green with a retail park (score.py gives both 1.0), so the signal is
        // miscast rather than worthless, and a driver who wants town centres
        // can still ask for them.
        BeautyType(apiName: "town",   label: "Town centers",
                   defaultWeight: 0.0,
                   note: "Off by default — drivers rated built-up stretches "
                       + "worse than the score predicted."),
        BeautyType(apiName: "water",  label: "Lakes & rivers"),
        BeautyType(apiName: "hills",  label: "Hills"),
        BeautyType(apiName: "farm",   label: "Farmland"),
    ]

    /// Neutral weight — the calibrated blend, and what the middle of the slider
    /// means. Most types start here; see `defaultWeight` for the one that
    /// doesn't.
    static let neutralWeight = 1.0

    /// The slider's range. The midpoint is `neutralWeight`, so "centered" reads
    /// as "no preference"; left ignores the type, right leans into it.
    static let weightRange = 0.0...2.0

    /// This type's colour, used in three places that have to agree: the slider
    /// on the *What you like* sheet, its bar in the route breakdown, and the
    /// swatches on the chip that opens the sheet. One language, so the bars
    /// read as a key rather than as an unrelated chart.
    var hue: Color { BeautyType.hue(for: apiName) }

    /// Mid-chroma so six of them can sit together without any one shouting,
    /// and lifted in dark mode so they still separate against `#121110`.
    ///
    /// `forest` is the old `Color.brand` — `rgb(0.22, 0.83, 0.62)` — deepened
    /// until it works as text. The green did not survive as the app's accent
    /// (see `Color.amber`), but it was the only visual equity the project had,
    /// and the honest place for it is the one thing it literally names.
    static func hue(for apiName: String) -> Color {
        switch apiName {
        case "coast":  return .adaptiveHue(light: 0x2F7E8C, dark: 0x4FA8B8)
        case "forest": return .adaptiveHue(light: 0x2F8A63, dark: 0x4FB287)
        case "water":  return .adaptiveHue(light: 0x3D6BA8, dark: 0x6E9AD6)
        case "hills":  return .adaptiveHue(light: 0x7A6A9E, dark: 0xA091C4)
        case "farm":   return .adaptiveHue(light: 0xA8903C, dark: 0xC9B057)
        case "town":   return .adaptiveHue(light: 0x8A7F74, dark: 0xAFA396)
        default:       return .slate
        }
    }

    /// The backend names the breakdown buckets `forest/park`, `farmland`,
    /// `town`; the tune sheet calls the same things *Forest & parks*,
    /// *Farmland*, *Town centers*. Two vocabularies for one set of six was a
    /// small thing on separate screens and is a visible one now that the bars
    /// carry the sheet's colours. The backend's key stays the key; this is only
    /// what a reader sees.
    ///
    /// Keep in sync with `SCENERY_BREAKDOWN` in `pipeline/router.py` and with
    /// `RouteProps.sceneryBreakdown`.
    static func forBreakdown(_ key: String) -> (label: String, hue: Color) {
        let apiName: String
        switch key {
        case "forest/park": apiName = "forest"
        case "farmland":    apiName = "farm"
        default:            apiName = key
        }
        let label = all.first { $0.apiName == apiName }?.label ?? key.capitalized
        return (label, hue(for: apiName))
    }
}
