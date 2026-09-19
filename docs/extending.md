# Where the next features plug in

**Status:** current. Split out of the README 2026-09-16.

The component pipeline is deliberately open-ended: `score.py` writes every
`c_<component>` column it computes, `graph.py` auto-detects those columns and
carries them onto edges, and `router.py` re-blends them live per request. So:

- **A new scenery signal** (e.g. land cover from NLCD/ESA WorldCover) is one new
  `c_...` column plus a `WEIGHTS` entry in `score.py`, then a score + graph
  rebuild. Add it to `BEAUTY_TYPES` in `router.py` only if users should be able
  to tune it (otherwise list it in `BASELINE`).
- **Retuning travel time** is `SPEED_FACTOR` and `CONTROL_SECONDS` in
  `router.py` — constants and a restart, deliberately not a graph rebuild, so
  re-fitting them as drives accumulate costs nothing. Drive first and fit them
  to the trace with `tools/fit_junction_cost.py` rather than picking numbers.
  This section used to warn against charging a junction penalty *per edge*,
  because edges are also split where a way merely ends and a flat per-edge cost
  would price OSM's editing history instead of the road — the same trap
  curvature fell into. The warning stands; what dodges it is that the cost is
  per *control node found in the way's node list*, so a split with no signal on
  it costs nothing. Do not replace that with a per-edge or a nearest-edge
  charge: 81.7% of MA's controls have more than one road within 15 m of them.
- **Retuning the scenery blend against real verdicts** is `WEIGHTS` in
  `score.py`, then a score + graph rebuild. That rebuild is cheap on purpose:
  `WEIGHTS` feeds no component column, only the derived `raw` and `score`, so
  every cached spatial query survives it and the score half runs in about a
  minute instead of eight (`component-rebuild-cache-findings.md`). Drive first:
  the marks are what say which component is lying, and the disagreement table
  names the roads to check.
  Read the separation number against the noise floor printed beside it, never
  against 0.50 — and change one weight at a time, since `score.py`'s calibration
  report is what catches a component pinned at its ceiling.
- **A second region** is the same pipeline run on another Geofabrik extract,
  or several merged with `osmium merge` as New England was. Most of what used
  to be Massachusetts-specific is already gone: `elevation.py`'s BBOX covers
  all six states, and the byways come from OSM route relations rather than
  hardcoded names. What is left to generalize when the region leaves New
  England: the projection in `common.py` (`CRS_METERS`, fine at these
  latitudes), `RELIEF_FULL` in `score.py` (fitted so Massachusetts' hills have
  range — 4.7% of New England chunks already sit at its ceiling, against 1.6%
  of Massachusetts'), and the `Region.massachusetts` camera and search bias in
  the iOS app.

The user-facing scenery labels live in one place per language: `SCENERY_BREAKDOWN`
in `router.py` (server) and `RouteProps.sceneryBreakdown` in `Models.swift`
(client), with the tunable type names in `BEAUTY_TYPES` and `BeautyType.all`.
Both suites assert the same lists from their own side, so renaming a type on one
end fails a test rather than quietly dropping a bar from the app.
