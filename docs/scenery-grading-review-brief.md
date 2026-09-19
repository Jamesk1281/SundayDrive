# Scenery grading: twenty proposals, and a request for verdicts

> **Verdicts delivered in `docs/scenery-grading-verdict.md` (2026-09-16).**
> Nothing has been built from either document. Read the verdict before acting on
> any proposal below — it rejects a number of them.

**Status: proposed, nothing measured, nothing changed.** No source file, no
constant, no test has been touched. This document is a *hypothesis set* produced
by a brainstorm against the code, not a set of findings. Every claim in it is
either (a) read off a file at a line number given here, (b) carried over from an
existing measured doc which is cited, or (c) an inference of mine, which is
marked as such. **Category (c) is where the errors will be**, and separating the
three is most of the job being asked for.

The task: **review each proposal independently and issue a verdict.** Not
implement. Not one of them. The output is one document.

---

## Why this exists

The scenic score is calibrated against its own distribution and against two
byway names written into `pipeline/score.py`. That establishes self-consistency,
not validity. The only external evidence is **79 thumb-taps from one driver over
12 drives** (60 nice, 19 dull), which separate at **0.74 against a noise floor
of 0.63** — above chance, and not by much (`README.md:374-451`).

Two measured results bound what is worth doing next:

- **Constant-tuning does not move routes.** The 2026-08-11 recalibration fixed
  three genuine defects (curvature measured digitizing jitter; relief was scaled
  for alpine terrain; the composite only reached ~6 of 10) and afterwards routes
  at default settings were **90–100% identical** to before.
- **The scenery model is blind to road size.** Across every road class above 1%
  of New England's km, *raw* beauty runs 0.301–0.317 — a spread of 0.19 points
  of 10 (`docs/driver-preferences-study.md`). Nine components and 236,000 km
  cannot tell a residential lane from a secondary highway.

So the remaining gains are in **new signals, a different atom, or a cheaper
label supply** — not in re-sweeping `WEIGHTS` or `BETA`. The twenty proposals
below are attempts at those three. They need attacking before any of them is
built.

---

## What the model is today, in five lines

Read these first; each proposal attacks one of them.

1. **A proximity indicator vector, not a visual model.** Five of nine components
   are boolean or three-banded step functions of `dwithin`
   (`pipeline/score.py:201` `near_flags`, called at `:334-364`). Nothing knows
   whether the feature is *visible*.
2. **Memoryless and per-km.** The 9-vector is scalarized to 0–10
   (`pipeline/score.py:265` `blend`, `:276` `composite`) and the router
   multiplies by km (`pipeline/router.py:1029` `penalty = self.km * (1.0 -
   scores / 10.0)`).
3. **Static and undirected.** Scores live on undirected edges; direction enters
   only through travel time and oneway. No time, season, sun, or bearing.
4. **~15 hand-set module constants** in `score.py` alone (`:39` `CHUNK_LEN`,
   `:42` `DIST`, `:51` `MIN_AREA`, `:52` `WEIGHTS`, `:65-66`
   `RAW_BASE`/`STRETCH`, `:73-76` the `CURVE_*` family, `:81` `RELIEF_FULL`,
   `:82` `CLASS_ADJ`), plus `BETA`/`PREF_CURVE` in `router.py:75,214`.
5. **The atom is a 400 m chunk**, which is a data-structure convenience
   (`pipeline/score.py:128` `chunk_roads`). Nobody remembers a 400 m chunk.

---

## The proposals

Grouped by which foundation they attack. Each gives the mechanism, the file it
lands in, and my confidence. **Confidence is mine and is worth nothing — it is
here so you know where I think the weak points are, not so you can inherit
them.**

### Group A — proximity → visibility

**A1. Ray-cast viewshed from the DEM.** Per chunk midpoint, 32 rays to ~5 km
over the elevation mosaic, taking horizon angle per ray. Yields `c_openness`
(unobstructed hemisphere fraction), `c_viewdistance` (median distance to the
horizon-defining obstruction), and visible-feature accounting (intersect the
visible cone with water/coast/farm and weight by angular size ≈ 1/d).
*Claim:* `relief.tif` reduces the DEM to one scalar — elevation range within a
750 m window (`pipeline/elevation.py:46` `RELIEF_WINDOW_M`, `:244`
`maximum_filter`) — which **cannot distinguish a ridge road from a ravine
road**. They have identical local relief and opposite views. *Confidence in the
claim: high (it is a property of the operator). Confidence in the payoff:
untested.*
*Cost:* 6,400 raster gathers vectorized across ~1M midpoints; tileable. Not
measured.

**A2. Landcover entropy / edge density — the cheap 80%.** `pipeline/landcover.py`
already reads a ~100 m WorldCover box per chunk (`:83` `SAMPLE_BOX_M`,
`:104-112` the odd-pixel box) and collapses it to one number, the tree fraction.
Compute class entropy and class-transition (edge) density in *the same box* and
keep them. *Hypothesis:* beauty tracks **landscape heterogeneity**, not any
single class — a road on the forest/field boundary sees both; a road in the
middle of either sees one thing.
*This is the cheapest test of the whole Group A thesis and should probably be
run before A1 is costed at all.*

**A3. Canopy over the road vs canopy near it.** Same pass again: sample the
**centre pixel** separately from the box. Box-high + centre-high is a tree
tunnel; box-high + centre-low is a road running along a wood. That distinction
is currently invisible and may be a large share of what `c_forest` is
conflating. One extra column.

**A4. Directional scores.** If A1 is built, bucket the rays by bearing relative
to travel and emit left-window / right-window columns. A loop driven clockwise
is a different drive. *Note this breaks the undirected-edge assumption* — see
Trap 7.

### Group B — the per-km scalar, and the cap

**B1. `c_novelty`.** Distance between a chunk's component vector and the mean
vector of chunks within ~3 km *along the network*. The one ridge in a flat
county; the one open field in continuous forest. *Claim:* this smuggles
contrast — a sequence-level property — into a static, edge-separable column, so
Dijkstra can have it for free.

**B2. `c_reveal`.** The gradient of openness along the road: the moment the
woods open onto a view. Derivative of an A1 column. Same trick as B1.

**B3. Attack the cap doc's inference, not its measurements.**
`docs/scenery-cap-options.md` concludes that "the region where Dijkstra is valid
is precisely the region where no kilometre of road is ever worth adding." The
measurements behind it are extensive and are **not** what I am questioning. My
narrower claim: the sharper statement is *a memoryless objective cannot reward
length; rewarding length requires state* — and the two walls the doc relies on
(`s_max = 10.00` exactly, and `b*(A)`) are properties of the **score
distribution**, not of the routing mathematics. A rank-transformed score with a
long thin top tail moves both. That does not rescue option 4 (a ratio is
scale-free) and it may buy nothing at all — but it is checkable in minutes
without re-running any sweep.

### Group C — the constants and the labels

**C1. Constant-sensitivity sweep.** For every constant listed in "What the model
is today" line 4: perturb ±2× and measure **whether the chosen route changes**,
not whether the distribution looks nicer. ~20 constants × 10 routes × 2
perturbations. *Prediction: most of them never move a route*, which would make
them decoration to be deleted rather than tunables to be fitted. This is the
cheapest item in the document and the one I would run first.

**C2. Pairwise labelling instead of absolute.** "Which of these two is nicer"
carries more information per judgement than a 1–10 rating and needs no
inter-rater calibration. Bradley–Terry / TrueSkill over a few thousand
comparisons.

**C3. Label from imagery, deploy from geodata.** Mapillary (CC-BY-SA) has real
New England coverage. Sample images stratified by road class and component
vector, collect comparisons, fit the existing 9-vector to the resulting ranking.
Geodata stays the deployable model; imagery is only the yardstick. **See Trap 9
on licensing — I do not know the answer and it may kill this.**

**C4. A VLM as the rater, gated on the humans already collected.** Score images
with a vision model — but *first* check its ranking against the existing 79
marks with the noise floor printed. If it does not reach the driver's own
separation on the marks that exist, it has not earned the right to label 10,000
more. **The gate is the whole proposal.** Review the gate, not the vibe.

**C5. Geotagged-photo density as revealed preference.** The classic scenicness
proxy. Heavily confounded by tourism and population — it measures *famous*, not
*beautiful*. Usable only population-normalized, and probably only as a
validation check, never as a feature. *I think this is weak; included so it can
be rejected on the record.*

**C6. Active-learning drive planning.** Stop driving Needham→Worcester. Use
`pipeline/looper.py` to generate the loop that passes the most **model-uncertain**
chunks — where candidate models disagree most, or where adjacent chunks differ
by 5 points. Same fuel, more information per drive. *I rate this the highest-
leverage item in the document*, because the bottleneck is not compute and not
ideas: it is 79 labels and one rater.

### Group D — the atom

**D1. Grade drives, not roads.** Segment the network on feature/score
changepoints into named coherent runs of 3–20 km, score *those*, and treat the
graph as the connector between beads. Buys an explicable product, an affordable
non-additive objective (select from thousands of catalogue items, not search 1M
edges), a natural budget model, and something to show a user *before* they
drive. *Risk: curation bias, and coverage holes where nothing is catalogued.*
This is the largest change in the document and the least specified.

### Group E — signals that need no uprooting

**E1. Split `c_urban`.** It is the **only component that measured pointing the
wrong way** — 0.35 separation on the 2026-08-25 marks, and Hudson Road scores
6.42 on `c_green` 1.0 *and* `c_urban` 1.0 and was called dull. Hypothesis: it is
two things averaged into noise — a village centre (`place=village` + building
density) and a commercial strip (`landuse=retail` + parking polygon area). One
is positive, one is negative. Built at `pipeline/score.py:362-365`.

**E2. Tranquility / motorway-noise penalty.** A back road 200 m from I-95 is not
tranquil. Reuses the existing `near_flags` machinery with a negative weight.

**E3. Sun azimuth vs road bearing.** Road bearing is in the geometry; sun
position is a closed form. Gives sunset-facing coast roads at 19:00 and
separately avoids driving into low sun, which is also a safety argument.
Query-time, no rebuild — **but see Trap 7, this is where it goes wrong.**

**E4. Foliage season.** New England's biggest scenery event of the year and the
model is blind to it. WorldCover does not split deciduous from evergreen; NLCD
classes 41/42/43 do, and are free. A date-dependent modifier on `c_forest`.

**E5. Continuous distance decay.** Rasterize each feature class once, run
`scipy.ndimage.distance_transform_edt`, sample per chunk. Kills the hand-set
`DIST` bands (`pipeline/score.py:42-50`). The 0 / 0.45 / 1.0 water banding at
`:335` is an artifact of `dwithin` being a boolean predicate, not a claim about
how water looks at 130 m versus 110 m. **Sell this on model quality and
extensibility only — see Trap 5.**

### Group F — efficiency

**F1. Kill the dual representation.** `score.py` chunks ways at 400 m (942,448
chunks on the NE build); `graph.py` splits at junctions (998,252 edges) and
joins them back by `query_nearest` over ~1M sampled points
(`pipeline/graph.py:518-567`), guarded by `MAX_CHUNK_SNAP_M`
(`pipeline/graph.py:497`) against a failure the comment itself describes: *"a
residential street beside I-90 can inherit the interstate's components and its
score_adj with nothing said"* (`:549-552`). Split at junctions **first**,
sub-chunk any edge over 400 m, and the join becomes the identity — no STRtree,
no 1M-point nearest query, no guard rail, no midpoint error class, ~250 MB less
on disk. **See Trap 6: this is not free.**

**F2. Component-level rebuild cache.** The component vector is the real
artifact; `score` is a cache the router already recomputes
(`pipeline/router.py:982` `_edge_scores`). Key each `c_*` column on a hash of
its input layers and its constants. Retuning `CURVE_D` then recomputes one
column in seconds instead of a full `score.py` + `graph.py` + 364 MB redeploy.
**This is the enabling change for C1, C2, C4 and C6** — calibration is expensive
today because the loop is minutes long.

*Latent inconsistency found while writing this, worth confirming:* `WEIGHTS`
changes are already restart-only for routing, because `Router._edge_scores`
re-blends live — but the stored `score` column goes stale, and
`RouteResult.mean_score` and `looper.beautiful_km` (`pipeline/looper.py:191`)
fall back to it. The route would be picked on the new scale and reported on the
old one. **Verify this; I did not.**

**F3. A\* with time-metric landmarks — admissible, and the proof is one line.**
`pipeline/router.py:1029-1038`:

```python
penalty = self.km * (1.0 - scores / 10.0)           # km of "unscenic" road
strength = max(0.0, min(1.0, pref)) ** PREF_CURVE
w = self.d_minutes + strength * BETA * penalty[self.eidx]
```

All added terms are non-negative (`scores ≤ 10` so `penalty ≥ 0`; the unpaved
term at `:1036-1038` is a non-negative addend). So **`w ≥ d_minutes` for every
user's weight settings**, and any admissible heuristic for the time metric is
admissible for every scenic query. ALT landmarks on `d_minutes` are therefore
precomputable once, user-independent, and correct.
*Tightness is the open question, not correctness* — see Trap 4.
*A tighter universal bound may exist:* precompute per-edge `s_max` = the best
score reachable under any admissible weight vector. Renormalization
(`pipeline/router.py:982-1010`) holds the total tunable weight constant, so that
is "all user weight on the edge's strongest component", bounded further by
`server/app.py`'s 0..4 clamp. Landmarks bucketed by `pref` would then be tight
at the top of the slider too, at ~5× the preprocessing.

**F4. Customizable contraction hierarchies.** Plain CH fails on per-user metrics;
CCH was designed for exactly this — metric-independent contraction order, cheap
per-weight-vector customization. This is the known-correct answer to the
`E^1.28` latency wall and the only thing that makes the region grow past the
Northeast. Large. Probably out of scope; say so if it is.

---

## Traps

**This is the section that is worth the most. Read it before measuring
anything.**

**Trap 1 — Validating on the marks everything else was fitted on.** There are
**79 marks, one driver, 12 drives, 60 nice / 19 dull**, and at those sample
sizes *a score that knows nothing reaches 0.63 one run in twenty*
(`README.md:400-420`). The existing combined road-class + model predictor was
already **fitted on the same 76 marks it was validated on** — that caveat is
recorded and has never been cleared. A new component that reaches 0.70 on these
marks has demonstrated approximately nothing. `tools/analyze_trace.py` prints
the noise floor beside the separation for exactly this reason; any verdict that
quotes a separation without its floor is wrong on its face.

**Trap 2 — "The numbers look better" is not the test; "the routes moved" is.**
The 2026-08-11 recalibration fixed three real defects and routes came back
90–100% identical. Judge every proposal on whether chosen routes change.
`pipeline/scenery_cap_experiment.py` is the existing harness for this: it
monkeypatches `Router._weights` between calls and holds one loaded `Router` for
a whole sweep, so a full option sweep is ~15 s of load and ~0.15 s per route.
**Copy that pattern. Do not modify source to measure.**

**Trap 3 — A new component is not free, and density is the gate, not
correlation.** From `docs/driver-preferences-study.md`: a *dense* column (mean
0.841, 88% of km ≥ 0.5) added where all six existing attractions are sparse
(densest is `c_forest` at mean 0.471 / 43.9% of km) adds 0.126 to every road's
raw against the whole tunable pot's 0.246 — moving p50 from 4.50 to **5.91
before anyone touches a slider** — and breaks
`test_neutral_weights_reproduce_the_precomputed_score`, forcing a rebuild plus a
364 MB redeploy. **`c_openness` (A1) and `c_novelty` (B1) are both at risk of
being dense.** Any proposal for a new component must report its coverage
distribution on the real build before anything else about it is discussed.

**Trap 4 — F3's admissibility proof is sound; its payoff claim is not
measured.** I asserted "~40% of request time" in the brainstorm. That is an
inference from "two arms per request, tight on the fastest one, loose at
pref=1" — at pref=1 the scenery term can be ~8× the time term, so a time-only
bound prunes little on the scenic arm. It has not been measured. Related
measured facts you should use rather than re-derive: `route()` runs a
full-graph scipy Dijkstra with **no target early-exit**, so cost tracks region
size not trip length (15 km and 190 km cost the same); `dijkstra(..., limit=cost)`
cut a short route to 4 ms, but the settled set is a *cost ball* that is already
62% of Massachusetts by Boston→Worcester. NE is 2.5× MA's edges and 3.2× its
time.

**Trap 5 — E5 is not a speed win, and it is easy to re-derive it as one.**
`near_flags` `dwithin` returns **1.8 hits per chunk** — a local density ratio
that does not grow with region — so `score.py` is already O(n_chunks) and is not
a bottleneck. The case for rasterizing is continuous decay and extensibility.
A verdict that recommends E5 on performance grounds has made an error this brief
already flagged.

**Trap 6 — F1 looks like a pure win and has a hidden cost.** `score.py` runs on
`roads.parquet` from `extract.py`; junction splitting lives in
`pipeline/graph.py:307` `build_edges` and needs the PBF's node reference counts.
Moving the split earlier is a **pipeline reorder, not a function move**. Worse:
it changes the identity of `scored_chunks.parquet`, and `landcover.py`'s output
is joined to it **positionally** — `score.py:243-249` raises `SystemExit` on a
file whose midpoints do not line up. So the "free" refactor invalidates
`tree_cover.parquet` and forces a landcover re-run. Cost that before
recommending it.

**Trap 7 — query-time modifiers (E3, E4, A4) bypass the identity the tests
guard.** `test_neutral_weights_reproduce_the_precomputed_score` pins the live
re-blend to the stored column. A time-of-day or season modifier applied inside
`Router._edge_scores` breaks that identity by construction. It must go in
`_weights`, **outside** the composite — which is precisely the lesson
`UNPAVED_ADJ` taught: it used to sit inside the score, so it was scaled by
`pref**PREF_CURVE` and *wanting more beauty bought more dirt avoidance*
(`pipeline/router.py:148-170`). Any proposal that adds a term must say which
side of the composite it lands on and what that does to `pref`.

**Trap 8 — do not re-derive `docs/scenery-cap-options.md`.** It is ~600 lines of
measured work: a 64-fold `BETA` sweep, the `b*(A)` validity table, Bellman-Ford
killed at a 15-minute wall on three configurations, ten OD pairs. **Attack the
inference, not the measurements.** B3's claim is narrow and cheap: check whether
`s_max` and `b*(A)` are artifacts of the score distribution. If that check comes
back "no", B3 dies in an hour and the doc's conclusion stands unamended.

**Trap 9 — C3/C4 have a licensing question I could not answer.** Mapillary is
CC-BY-SA. Whether using it as a *label source* to fit weights creates a
share-alike obligation on the derived weights is a real question, not a
formality. This project has already been bitten by attribution obligations —
see `docs/licensing-and-attribution-brief.md` and the Apple MapKit Attachment 6
constraints. **Flag it; do not assume it away in either direction.**

**Trap 10 — scope. Twenty proposals reviewed shallowly is worth less than five
reviewed properly.** Triage explicitly: rank by *evidence obtainable without a
rebuild*, go deep on those, and return an honest "not assessed, here is what it
would take" for the rest. A verdict document that gives all twenty the same
two paragraphs has failed.

---

## Done looks like

1. **One document**, `docs/scenery-grading-verdict.md`, with a section per
   proposal (or per triage group for the ones not assessed).
2. **A verdict from a fixed vocabulary** on each: **build now** / **build after
   a named cheap test** (name it) / **reject** (say what killed it) / **cannot
   be determined from this data** (say what data would settle it). The last one
   is a real answer, not a failure.
3. **Every claim in this brief checked against the code at the line given**, with
   corrections called out explicitly. This brief is a hypothesis set. Finding it
   wrong is a result, and the "latent inconsistency" note under F2 is the first
   place to look.
4. **Coverage/density numbers on the real build for every proposed new
   component**, per Trap 3, before any other argument about it.
5. **A ranked list at the end by evidence-per-hour**, which is allowed to differ
   from mine — mine is at the bottom of the brainstorm and is not evidence.
6. **Nothing under `pipeline/`, `server/`, `ios/` or `tests/` modified.**
   Measure by monkeypatching in scratch scripts, the way
   `pipeline/scenery_cap_experiment.py` and `docs/driver-preferences-study.md`
   both did.

---

## Reproducing / running anything

The data lives **only in the main checkout**, not in worktrees:

```
SCENIC_DATA=<abs>/Scenic/data/processed-ne     # the live New England build
<abs>/Scenic/traces/                            # 12 drive traces, incl. the 79 marks
```

```bash
.venv/bin/python -m pytest tests/
```

- **Always `.venv/bin/python -m <tool>`**, never `.venv/bin/pytest`. The project
  path contains spaces, so every venv console script has a broken shebang.
- `tools/analyze_trace.py <data_dir> <trace...>` produces the separation report
  with its noise floor.
- `pipeline/scenery_cap_experiment.py data/processed` is the measurement-harness
  pattern to copy: one loaded `Router`, monkeypatched between calls.
- `data/processed` is a **Massachusetts** build; `data/processed-ne` is New
  England and is what serves. They are not interchangeable and several recorded
  numbers differ between them.
