import Foundation

/// The map between the preference dial's handle and the `pref` the API takes.
///
/// They are not the same number, and that is the whole point. The router
/// squares the preference — `PREF_CURVE = 2.0` at `pipeline/router.py:152`,
/// applied at `:919` as `strength = clamp(pref) ** PREF_CURVE` — so a handle
/// moving linearly through `pref` moves *quadratically* through the quantity
/// that actually picks the route, and the bottom of the track lands in the flat
/// part of the curve. Measured over 252 pairs at five settings
/// (`docs/route-distribution-study.md`, Q3), against pref 0:
///
///     pref   strength   extra min   beautiful mi   step changes nothing
///     0.25       0.06         0.5           0.20                    33%
///     0.50       0.25        16.5           5.06                    16%
///     0.75       0.56        24.5           7.01                    22%
///     1.00       1.00        28.1           9.20                    28%
///
/// The first quarter of the travel buys 2% of what the whole slider buys, and a
/// third of trips at that setting get back the route they already had.
///
/// Mapping the handle's position `p` to `pref = sqrt(p)` makes `strength == p`,
/// so every quarter of the travel does comparable work. Read off the table, the
/// first quarter then buys about 55% of the available beautiful miles for about
/// 59% of the available minutes — still front-loaded, because the outcome
/// saturates in strength too, but no longer dead. Nothing can make the travel
/// linear in *outcome*: that curve is route-dependent. Linear in strength is
/// the honest fixed transform.
///
/// Two things this must not do.
///
/// It must not become the value anyone stores. `RouteModel.pref` is what
/// `server/app.py` is asked for, what goes into every `DriveTrace` header, what
/// `NavigationModel` reroutes with, and the quantity the census and all twelve
/// recorded drives are indexed by. Only the dial's own binding holds a position.
///
/// And it must not blur `pref == 0`, which is magic in three places:
/// `server/app.py` short-circuits (`scenic = fastest if pref == 0.0`),
/// `NavigationModel.reroute` reads it as `wantFastest`, and `switchToFastest`
/// writes it. `sqrt(0)` and `0 * 0` are both exactly 0, so the far ends survive
/// the round trip bit-for-bit — but nothing here may round, smooth or animate,
/// or the "Fastest" end of the track quietly stops being the fastest route.
///
/// Lifted out of `RoutePanel.swift` when the planning sheet was replaced by a
/// page (`docs/interface-design.md` §2). Nothing about it changed: the caption
/// above the track is what the redesign rewrote, not the mathematics under it.
enum PrefSlider {

    /// The `pref` a handle at `position` is asking for. Exact at both ends.
    static func pref(atPosition position: Double) -> Double {
        (position < 0 ? 0 : position > 1 ? 1 : position).squareRoot()
    }

    /// Where the handle sits for a given `pref` — the inverse, and the router's
    /// `strength` for that `pref`.
    static func position(forPref pref: Double) -> Double {
        let p = pref < 0 ? 0 : pref > 1 ? 1 : pref
        return p * p
    }

    /// What the dial says about itself *while the finger is down*.
    ///
    /// Not a number, on purpose. The route recomputes only on release — see
    /// the `onEditingChanged` in `PrefDial` — so mid-drag the minutes and the
    /// mile count describe the position the user just left. `0.25` was merely
    /// opaque; a stale price would be wrong. A name for the region of the track
    /// describes the handle, which is the one thing that is true at every
    /// moment of a drag.
    static func name(atPosition position: Double) -> String {
        switch position {
        case ..<0.001: return "Fastest"
        case ..<0.25:  return "Direct"
        case ..<0.55:  return "A little scenic"
        case ..<0.85:  return "Scenic"
        default:       return "Most scenic"
        }
    }
}
