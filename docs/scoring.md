# How the scenic score works

**Status:** current. Split out of the README 2026-09-16; the numbers are
`score.py`'s calibration report on the live `data/processed-ne` build.

Each ~400 m road chunk gets component scores in `[0,1]` for proximity to water,
coastline, forest/parks, farmland and viewpoints, plus road curvature and local
terrain relief. The forest component is half OSM's mapped woods/parks and half
measured tree cover from ESA WorldCover (`landcover.py`), because OSM's polygons
record land *designation* rather than vegetation and are three times more
complete in Rhode Island than in Maine — see
[`docs/geodata-sources-findings.md`](geodata-sources-findings.md). A weighted blend (tunable constants at the top of `score.py`)
produces a 0–10 composite, with a penalty for highways.
The router charges a minutes-equivalent penalty per km of *unscenic* road, so the
preference knob trades extra time for scenery.

Road *surface* is deliberately not part of that composite. A flat -0.25 for
unpaved used to be, and it measured mapping diligence rather than beauty —
surface tagging runs from Vermont's 90% down to Maine's 36%, so Vermont's dirt
roads were nearly all found and penalised while most of Maine's escaped, and the
model's own components rate unpaved roads *above* paved ones in all six states.
Worse, sitting in the score put it inside the router's `pref` term, so asking
for more scenery bought more dirt-avoidance. It is now a separate preference
priced in minutes — `avoid_unpaved=0..2` on both endpoints, defaulting to the
calibrated 1.0 min/km, which preserves the old average behaviour without the
coupling. See
[`docs/unpaved-and-urban-verdict.md`](unpaved-and-urban-verdict.md).

Every constant in that blend is fitted to the *distribution* it produces, not
guessed, because a single number silently reshapes 236,000 km of road. `score.py`
prints a calibration report on each run — scale percentiles, per-component
coverage, and benchmark roads — and the current numbers are: median road 4.4,
p90 6.9, p99 9.1, with Greylock's Notch Road at 6.6 and the Mass Pike at 0.6.
Three things that report is specifically there to catch, all of which were live
at some point:

- **a component pinned at its ceiling** — curvature is measured between chords
  60 m apart rather than between raw ~20 m OSM vertices, because summing
  vertex-to-vertex heading change measures digitizing jitter (it reached 3,500
  deg/km, ten rotations per kilometre) and rated cul-de-sacs above the Mohawk
  Trail;
- **a component with no range left** — relief is scaled to Massachusetts
  terrain, not alpine, or the Hills slider has nothing to grab;
- **a compressed scale** — no real road collects every component, so the blend
  needs an explicit stretch or "8/10" is unreachable.
