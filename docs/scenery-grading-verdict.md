# Verdicts on the twenty scenery-grading proposals

**Status: reviewed 2026-09-16. Nothing built, nothing changed.** No file under
`pipeline/`, `server/`, `ios/` or `tests/` was touched. Every measurement below
was made by scratch scripts outside the repository that load one `Router` and
monkeypatch it between calls, the way `pipeline/scenery_cap_experiment.py` and
`docs/driver-preferences-study.md` both do — see *Reproducing this* at the end.

This is the verdict on `docs/scenery-grading-review-brief.md`, which is
committed alongside it. That brief is a hypothesis set; this is what survived.

**Everything here is measured on the live New England build**
(`data/processed-ne`, 942,448 chunks / 236,477 km / 998,252 graph edges /
**801,719 routing nodes** — 794,685 junctions in `graph_nodes.parquet` plus the
per-approach copies `_apply_turn_restrictions` makes; the routing figure is the
one the node counts below are shares of), except where it says otherwise. `data/processed` is
Massachusetts and several numbers differ.

---

## The verdicts, in one table

| | proposal | verdict |
|---|---|---|
| **F3** | A\* with time-metric landmarks | **build now**, for the *fastest* arm only. Measured: the perfect time heuristic settles **0.0–0.1%** of the graph at `pref=0` and **7.7–92.5%** at `pref=1`. |
| **B3** | the cap doc's wall is an artifact of the score distribution | **reject.** Rank-transforming the score moves `b*(8)` from 0.902 to 0.906. The doc's conclusion stands unamended. |
| **C1** | constant-sensitivity sweep | **build after a named cheap test** — and the test is already run, below. Its stated *prediction* is wrong and its stated *cost* is wrong by about half. |
| **A1** | ray-cast viewshed → `c_openness` | **build after a named cheap test: pick the threshold first.** The signal is real and orthogonal (`corr(openness, c_relief) = −0.005`) and the compute is ~50 s, not a project. Density swings from 3.0% to 99.4% of km on the threshold alone. |
| **A2** | landcover entropy / edge density | **build after a named cheap test** — the cheapest density gate in the document, and it runs in one streamed WorldCover window. |
| **A3** | canopy over the road vs near it | **build now**, folded into A2's pass. One `uint8` compare in a box already read. |
| **A4** | directional scores | **reject as scoped** (it doubles the component table and breaks the undirected-edge assumption for a payoff nothing has measured); the *bearing* half is free and belongs in E3's bucket. |
| **B1** | `c_novelty` | **reject.** Measured density: mean **0.512**, 34.5% of km ≥ 0.5 — denser than every attraction in the pot, and `corr(novelty, score) = +0.390`. A contrast measure has a floor; there is no un-novel road. |
| **B2** | `c_reveal` | **cannot be determined**; strictly downstream of A1, and it inherits A1's threshold problem in a worse form. |
| **C2** | pairwise labelling | **build now.** It is the only proposal that raises the ceiling on every other one, and it is client work with no rebuild. |
| **C3** | label from imagery, deploy from geodata | **cannot be determined** — and the blocker is not the licence, it is that the gate in C4 cannot be run. |
| **C4** | a VLM as the rater, gated on the 79 marks | **reject the gate as specified**, which the brief asked me to review. The bar it sets is inside the noise it is meant to exclude. The idea survives with a different gate. |
| **C5** | geotagged-photo density | **reject**, on the brief's own reasoning, which is correct. |
| **C6** | active-learning drive planning | **build after a named cheap test.** Highest-leverage item in the document, as the brief says — but the first version should target *disagreement with the marks already collected*, not model uncertainty. |
| **D1** | grade drives, not roads | **cannot be determined.** One number narrows it: OSM's own catalogue of named scenic routes already covers **4,026 km of 236,477 — 1.7%**. The proposal is really about the other 98.3%. |
| **E1** | split `c_urban` | **reject as motivated.** Measured: the two halves are 8.1% and 3.9% of network km, nearly disjoint, and **both score above the non-urban baseline**. Its headline example no longer holds on this build. |
| **E2** | tranquility / motorway-noise penalty | **build after a named cheap test.** Density is in the sparse regime (10.4% of km within 200 m) — but it is a *negative* term and 2.2% of km is already floored at zero. |
| **E3** | sun azimuth vs road bearing | **cannot be determined**, and Trap 7 is right about where it lands. The safety half is a different product decision from the scenery half and should not be bundled. |
| **E4** | foliage season | **cannot be determined.** No New England drive mark exists in foliage season; every mark in `traces/` is from 14–25 August. |
| **E5** | continuous distance decay | **build after a named cheap test**, on model quality — never on speed. Measured: the coast band gives the same 1.0 to a road 33 m from the Atlantic and one 652 m inland, and everything past 350 m from water gets the same 0.0 at a p50 of 1,127 m. |
| **F1** | kill the dual representation | **reject as scoped.** None of its four stated payoffs survive contact with the code: the midpoint error it removes was fixed in 2026-08, the join is 2.8M points not ~1M, the 250 MB never leaves the build machine, and the join it calls lossy is **exact** — 0 strays and 0 class mismatches over 2.8M samples. |
| **F2** | component-level rebuild cache | **build now** — but not for the reason given, and its "latent inconsistency" is **wrong**. The real staleness is in `tools/analyze_trace.py`, which is worse, because that is the instrument. |
| **F4** | customizable contraction hierarchies | **cannot be determined, and out of scope today.** Say so and move on; F3 buys the next 2× and nothing needs the one after it yet. |

Ranked by evidence-per-hour at the end.

### Triage: what is measured and what is only argued

Trap 10 asks for this explicitly, so it is stated rather than implied.

**Measured on the live build** (numbers in the body, scripts in the appendix):
**F3, B3, C1, A1, B1, E1, F1, F2, E2, E5**, plus the bar itself. Ten of twenty,
chosen because their evidence was obtainable without a rebuild — which is the
brief's own triage rule.

**Argued from the code and the existing measured docs, not measured here:**
**A4, B2, C3, C4, C5, D1, E3, E4, F4**. For each of these the verdict says what
would settle it. None of them could be settled without either a rebuild, a new
data source, or a human rater, and all three were out of scope for a review.

**Measured only partially: A2 and A3.** Their density gate needs WorldCover, and
there is no tile cache on this machine — `landcover.py` streams over
`/vsicurl/`. I did not download tiles. What it would take is in A2's entry: one
streamed window over a few thousand clustered chunks, an afternoon.

---

## Read this first: what the brief got wrong

The brief asked to be attacked and marked its own claims (a) read off a line,
(b) carried from a measured doc, (c) inference. **Every (a) claim I checked held
up**, to within two lines in two places. The errors are in (b) and (c). Seven
are below; **five of them change a verdict.**

### 1. F2's "latent inconsistency" does not exist

> *the stored `score` column goes stale, and `RouteResult.mean_score` and
> `looper.beautiful_km` fall back to it. The route would be picked on the new
> scale and reported on the old one.* **Verify this; I did not.**

Verified: **false in production.** `Router.route` computes
`scores = self._edge_scores(...)` at `pipeline/router.py:1171` and hands the
array to `_collect`, which passes it into `RouteResult` at `:1261`.
`mean_score` (`:1606`) and `beautiful_km` (`:1630`) read the stored column only
`if self.scores is None`, which happens only for a `RouteResult` a test built by
hand. Measured on Needham→Gloucester at `pref=0.6`:

| weights | `res.scores is None` | `mean_score` reported | mean of the **stored** column on the same edges |
|---|---|---|---|
| neutral | False | 6.177 | 6.177 |
| `coast=4, water=0` | False | **7.557** | 6.287 |

The comment at `router.py:1165-1170` says this was a real bug and says it was
fixed; it was.

**But there is a real staleness, and it is worse.** The stored `score` column
has exactly two production readers left — `tools/analyze_trace.py:623-629` and
`pipeline/render.py`. So a `WEIGHTS` retune is **restart-only for serving and
rebuild-only for validation**: the router would route on the new scale while the
only instrument that checks the score against a human would still be reading the
old one, silently. That asymmetry is F2's actual argument and it is a better one.

A second asymmetry the brief does not have, measured the same way: `WEIGHTS` is
snapshotted into `Router.base_score` / `pref_matrix` at load
(`router.py:918-921`), so it needs a restart — but `RAW_BASE` and `STRETCH` are
read by `score.composite()` at *call* time, so patching them changes live
routing with **no restart at all**. Two constants in the same file, twelve lines
apart, with different deployment semantics and nothing saying so.

### 2. E1's headline example is stale

> *Hudson Road scores 6.42 on `c_green` 1.0 and `c_urban` 1.0 and was called dull.*

That is `docs/geodata-sources-review.md:81`, written against a Massachusetts
build with a `c_green` column. `c_green` no longer exists — it became half of
`c_forest` in the 2026-08-29 landcover merge. On the current New England build,
length-weighted over every way named Hudson Road (184 chunks, 63.2 km):

```
score 4.088   c_forest 0.492   c_urban 0.165   c_water 0.159   c_relief 0.338
```

Not 6.42, not 1.0, not 1.0. The road now scores *below* the network p50 of 4.50.
Whatever that example was evidence of, `c_forest` already fixed it. (Caveat: this
pools every Hudson Road in six states; the original was one stretch in eastern
Massachusetts. The point stands — the column it names is gone.)

### 3. C1's prediction is wrong, and its cost is understated by about half

The brief calls C1 "the cheapest item in the document" and predicts "most of
them never move a route." Both are wrong. Full table below; the summary is that
**the routing constants move nearly every route** (`PREF_CURVE ×2` leaves 17% of
the baseline route standing and moves 13 of 13 pairs) and that **about half the
constants cannot be perturbed without re-running `score.py`** — `DIST` (seven
values), `MIN_AREA` (three), `CHUNK_LEN`, `CURVE_D`, `CURVE_CAP`,
`CURVE_MIN_LEN`, and the *upward* direction of `CURVE_FULL` and `RELIEF_FULL`,
because a stored clipped column cannot be un-clipped. That is ~11 minutes of
`score.py` plus ~6 of `graph.py` per perturbation, against ~5 seconds for the
live half.

### 4. A1's compute is a minute, not a project

> *Cost: 6,400 raster gathers vectorized across ~1M midpoints; tileable. Not measured.*

Measured. `data/processed-ne/elevation.tif` is 10240×13568 float32 — **0.56 GB,
it fits in memory whole**. 40,000 midpoints × 16 rays × 22 range steps took
**1.0 s**. Extrapolated to all 942,448 chunks at the brief's 32 rays: **~50 s**.
There is no tiling problem and no cost question. A1's open question is entirely
about whether the number means anything, which is a different and harder one.

### 5. F1 costs more and buys less than stated

- *"the join becomes the identity — no ... midpoint error class"*: there is no
  midpoint error class. `graph.py` stopped reading a single midpoint before this
  brief was written; `attach_scores` samples every 100 m and length-weight
  averages (`graph.py:518-536`, and the docstring says why). The 0.65-point mean
  / 3.9-point worst error on edges over 800 m that the docstring records is the
  error that change *removed*, not one F1 would remove.
- *"~1M sampled points"*: measured **2,841,347** samples over 998,252 edges (2.8
  per edge). Nearly triple.
- *"~250 MB less on disk"*: `scored_chunks.parquet` is 208.7 MB and **the server
  never loads it** — `Router.__init__` reads `graph_edges`, `graph_nodes`,
  `access_ways`, `access_entries`, `turn_restrictions` and `traffic_control`
  (`router.py:324-453`). The saving is on the build Mac — worth something when
  that machine was at 4.7 GB free, worth little at today's 64 GB — and it is not
  part of the 364 MB redeploy, so it should not be sold as if it were.

### 6. Trap 5 is right about the hit rate and wrong about what follows

`dwithin` really does return few hits per chunk — I measure **1.65** across all
seven layers, against the brief's 1.8, which is close enough that the trap's
point stands. It does not follow that `score.py`'s feature stage is cheap: those
seven queries took **352 s** on this build, 203 s of it `water_areas` alone,
because the cost of `dwithin` against large multipolygons is driven by vertex
count, not hit count. See E5 — this changes E5's argument, though not its
verdict.

### 7. Two line numbers

`score.py:243-249` is the *missing-file* branch; the `SystemExit` on misaligned
midpoints is at `:250-256`. `router.py:1029` should be `:1027` (the quoted code
is correct). Neither changes anything.

---

## The bar: Trap 1, with numbers

Every verdict below is calibrated against this section, so it comes first.

Running the project's own instrument on the live build:

```
SCENERY  79 marks over 12 drive(s) — 60 nice, 19 dull
  SEPARATION  0.74    above chance      (null ceiling 0.63)
  same number over other windows —  200 m: 0.75   400 m: 0.74   800 m: 0.74
```

Capturing the per-mark scores `tools/analyze_trace.py` computes, without
changing it, and jackknifing the 400 m headline window:

| statistic | value |
|---|---|
| separation (400 m window; 200 m gives 0.747, 800 m 0.738) | 0.7395 |
| null ceiling, one-in-twenty (Hanley–McNeil, `analyze_trace.py:1272`) | 0.6258 |
| **bootstrap 90% CI (4,000 draws)** | **[0.646, 0.832]** |
| bootstrap draws at or below the null ceiling | 2.7% |
| **most one single mark moves the headline** | **0.0216** |
| mean absolute influence of one mark | 0.0052 |
| dropping the two *nice* marks that scored ≤ 0.01 | 0.739 → **0.764** |

Three things follow, and they are the frame for the whole document.

**One mark is worth a fifth of the margin.** The gap between the shipped model
and a score that knows nothing is 0.7395 − 0.6258 = 0.114. A single mark moves
the headline by up to 0.0216 — 19% of it. **Five or six marks going the other
way would erase the entire external validation of this project.**

**The family bar is 0.715, not 0.63.** The printed ceiling is the one-in-twenty
level for *one pre-specified* score. This brief proposes twenty. Holding the
family error at one in twenty needs `z = 2.807`, which on 60 nice / 19 dull puts
the ceiling at **0.715** — and the shipped model reaches 0.7395, with a
bootstrap lower bound of 0.646. *The existing model would not clear the bar its own
twenty successors have to clear.* Any proposal whose evidence is "it separated
at 0.7x on the marks" has not cleared it either. `docs/unpaved-and-urban-verdict.md:356`
already made this argument for nine components at 24%; twenty is worse.

**Buying the bar down is expensive and buying it out is cheap.** Holding the
76/24 nice:dull ratio, pushing the *single-test* ceiling to:

| target ceiling | marks needed |
|---|---|
| 0.60 | ~125 |
| 0.58 | ~195 |
| **0.55** | **~499** |
| 0.53 | ~1,376 |

That is 6.3× the current label supply to get to 0.55, from one driver whose
drives are all eastern Massachusetts and all between 14 and 25 August. Against
that, a **second driver replicating on the same roads** costs one afternoon and
answers the multiple-comparisons worry directly, which no number of marks from
the first driver can. `docs/unpaved-and-urban-verdict.md:409-412` reached the
same conclusion for `c_urban`; it generalises to everything here.

---

## Deep verdicts

### F3 — A\* with time-metric landmarks · **build now, fastest arm only**

**The admissibility proof is correct.** `_weights` (`router.py:1027-1038`)
builds `w = d_minutes + strength·BETA·penalty + avoid·UNPAVED_AVOID·dirt_km`.
`composite` clips to `[0, 10]` so `penalty = km·(1 − score/10) ≥ 0`; `strength`,
`BETA`, `avoid` and `dirt_km` are all non-negative; `d_minutes` is built once at
load (`:889`) from no user parameter. So `w ≥ d_minutes` pointwise, for every
`pref`, every weight vector and every `avoid_unpaved`. `route()` collapses
parallel edges by `np.minimum`, and `min_e w_e ≥ min_e d_minutes_e` follows from
the pointwise bound, so the collapse does not break it. **Any admissible
heuristic for the time metric is admissible for every scenic query.** Nothing to
add.

**The payoff is not what the brief guessed, and Trap 4 is right to flag it.** I
measured the *upper bound* on the whole family: instead of ALT landmarks, the
**perfect** time-to-go heuristic, from a backward Dijkstra on `d_minutes`. No
ALT preprocessing can beat it. Nodes settled, of 801,719:

| pair | `pref=0` ball / A\* | `pref=0.5` ball / A\* | `pref=1.0` ball / A\* |
|---|---|---|---|
| Needham→Wellesley (5.6 km) | 0.3% / **0.0%** | 0.3% / 0.1% | 0.3% / 0.2% |
| Harvard→Needham (49 km) | 12.6% / **0.0%** | 11.6% / 4.9% | 11.0% / 7.7% |
| Needham→Foxborough | 7.1% / **0.0%** | 9.4% / 3.1% | 10.1% / 7.1% |
| BostonHarvSq→Providence | 26.4% / **0.0%** | 29.3% / 19.7% | 28.6% / 24.1% |
| Needham→Worcester | 22.0% / **0.0%** | 20.6% / 10.3% | 21.8% / 17.2% |
| Needham→Groton | 24.1% / **0.0%** | 17.4% / 8.8% | 16.8% / 12.9% |
| Needham→Wachusett | 37.3% / **0.0%** | 27.7% / 14.5% | 26.5% / 20.3% |
| Needham→Brattleboro | 67.0% / **0.1%** | 51.9% / 33.2% | 49.1% / 41.4% |
| Hartford→Concord NH | 68.7% / **0.1%** | 67.6% / 55.8% | 66.9% / 62.5% |
| Providence→Portland | 73.1% / **0.1%** | 80.3% / 66.7% | 81.7% / 77.9% |
| Needham→NorthConway | 85.2% / **0.1%** | 76.1% / 50.0% | 77.3% / 67.3% |
| Burlington→Bangor (314 min) | 94.7% / **0.1%** | 92.6% / 57.4% | 95.8% / 92.5% |

("ball" is plain Dijkstra with a target early-exit; "A\*" is the perfect time
heuristic. Today's `route()` settles **100%** in every row — confirming Trap 4's
"no target early-exit, cost tracks region size": every one of those Dijkstras
took 0.30–0.37 s regardless of trip length.)

Read the table two ways.

**At `pref=0` the heuristic is the metric**, up to the surface term
(`w = d_minutes + avoid·UNPAVED_AVOID·dirt_km`, which is why the count is 64–782
nodes rather than exactly the path). A\* settles **0.0–0.1%** even on a
314-minute Vermont-to-Maine trip. And
`server/app.py:276-280` runs **two arms per request** — `ROUTER.route(s, t, 0.0, ...)`
and then the requested `pref` — so the first is always `pref=0.0`. `route()`
measured end to end is 0.37 s of which the scipy Dijkstra is 0.30 s, against
`docs/hosting-options-brief.md:44`'s measured **~835 ms** for a full two-Dijkstra
request. So removing the fastest arm's search is **~36%** of a request. **The
brief's unmeasured "~40% of request time" lands about right — but for the
fastest arm alone, not for ALT in general.**

**At `pref=1` the time bound is nearly worthless.** On Providence→Portland the
perfect heuristic trims the cost ball from 81.7% to 77.9% — under four
percentage points, on the arm that costs the most. Since A\* means leaving scipy's C for a Python heap —
which this project has already measured at **3.6×** (scipy static 88.6 ms
against Python static 319.9 ms on a Massachusetts-sized graph,
`docs/traffic-schedule-plan.md:232-234`) — a scenic arm settling 78% of the
graph in Python would be **≈2.8× slower than today**.

So: **build it for the fastest arm and leave the scenic arm on scipy.** It is
correct by the proof above, and the fallback is the code that already exists.

> **Superseded 2026-09-19, in the proposal's own favour but with a smaller
> number.** The table above is the *perfect* heuristic, which bounds the family
> and is not implementable per request. A real 16-landmark ALT was since
> measured: it settles **2.9% of the graph at the median** rather than 0.0%, and
> a `heapq` A\* on it runs in **20.3 ms against scipy's 227 ms** — 11× at the
> median, matching scipy's cost to 1e-6 on all 12 pairs. That is **~25%** of an
> 835 ms request, not the ~36% estimated here. A Euclidean bound settles 31–48%
> on long routes and is not viable. Full table and nine traps in
> `docs/astar-fastest-arm-brief.md`. Preprocessing for 16
landmarks is 32 Dijkstra runs (~10 s) and 103 MB of RAM on a process already at
4.0 GB.

**"Build now" is not "build first."** This is an engineering win with no product
evidence behind it: nothing in `traces/` or in any doc says a user has waited
too long. It is third in the ranking below, behind two label-supply items that
cost an afternoon each, because the bottleneck this project actually has is 79
marks and one rater — not 0.3 s.

Two things this is *not*. It is not a fix for the `E^1.28` wall — halving a
constant does not change an exponent, and the scenic arm, which is the one that
grows, is the one A\* cannot help. And the cheap alternative is much weaker than
it looks: the "ball" column is what `dijkstra(..., limit=...)` would achieve, and
at `pref=0` it settles 12.6–94.7% against A\*'s 0.0–0.1%. **The heuristic does
the work, not the early exit.**

*Named test before building, if one is wanted:* implement the heuristic as
`h = 0` first and confirm the Python A\* reproduces scipy's route on all 13 pairs
to the metre. The correctness risk here is the implementation, not the theory.

### B3 — the validity wall · **reject**

B3's claim is narrow and cheap, as advertised, and Trap 8 predicted the outcome.
Checked without re-running one measurement from `docs/scenery-cap-options.md`:

| A | 1 | 2 | 4 | **8** | 16 | 32 | 64 | 128 | 512 |
|---|---|---|---|---|---|---|---|---|---|
| `b*(A)` shipped scores | 0.251 | 0.608 | 0.804 | **0.902** | 0.951 | 0.975 | 0.988 | 0.994 | 0.998 |
| `b*(A)` rank-transformed | 0.325 | 0.653 | 0.817 | **0.906** | 0.951 | 0.975 | 0.988 | 0.994 | 0.998 |

**A rank transform moves the wall at the shipped `A = BETA = 8.0` by 0.004, and
in the wrong direction.** At `A ≥ 16` it is identical to three decimals. (The
cap doc's 0.911 at A=8 is Massachusetts on the 2026-08-24 graph; 0.902 is New
England today. Its own caveat 7 predicted exactly that.)

The brief's two sub-claims, separately:

**"`s_max = 10.00` exactly is a property of the score distribution."** Half
right, and it cuts the other way. `s_max` is 10.000000 because
`score.composite()` clips there; the *unclipped* composite reaches **13.189**,
and 0.237% of network km is pinned. So removing the clip does not lower `s_max`,
it raises it to 1.32 — and `b*` with it. The clip is the thing holding the wall
*down*.

**"a long thin top tail moves `b*`."** It cannot, because of what `b*` is. The
argmax at A=8 is a single edge: **Crawford Notch Road, 1,007 m, 0.79 min,
score 10.00** — a genuinely beautiful and genuinely fast primary through the
Notch. `b*(A) = max_e [s_e/10 − t_e/(A·L_e)]` is set by the best road in New
England, and every monotone transform keeps the best road at the top. Thinning
the tail moves the roads *below* it, which the max does not see.

And the deeper point the brief concedes but does not follow through: **the valid
region is `{b ≥ b*(A)}` and in that region every edge cost is non-negative, so
no edge ever lowers the total, for any score scale whatsoever.** That is a
theorem about non-negative weights. It is scale-invariant by construction, so no
re-scaling of the score can touch it. The brief's own sharper statement — *a
memoryless objective cannot reward length; rewarding length requires state* — is
correct, and it is precisely why the cap doc's conclusion is not vulnerable to
the attack aimed at it.

**B3 dies in an hour, as Trap 8 said it would. `docs/scenery-cap-options.md`
stands unamended.**

### C1 — constant sensitivity · **run it; here it is; its prediction is wrong**

13 OD pairs across New England, `pref=0.5` (the app default), each constant
perturbed ×0.5 and ×2. "overlap" is the share of the baseline route's km that
survives; "moved" counts pairs where overlap < 0.99.

| constant | ×  | median overlap | **worst** | moved | median abs Δscore |
|---|---|---|---|---|---|
| `PREF_CURVE` | 2.0 | **0.172** | 0.009 | 13/13 | 2.04 |
| `BETA` | 0.5 | **0.556** | 0.010 | 12/13 | 0.39 |
| `CLASS_ADJ` (family) | 2.0 | 0.689 | 0.094 | 11/13 | 0.23 |
| `STRETCH` | 2.0 | 0.705 | 0.491 | 12/13 | 3.95 |
| `BETA` / `PREF_CURVE` | 2.0 / 0.5 | 0.732 | 0.096 | 11/13 | 0.36 |
| `STRETCH` | 0.5 | 0.796 | 0.094 | 12/13 | 3.07 |
| `CLASS_ADJ` (family) | 0.5 | 0.888 | 0.106 | 9/13 | 0.37 |
| `WEIGHTS[water]` | 0.5 / 2.0 | 0.919 / 0.932 | 0.106 / 0.094 | 8/13 | 0.52 / 0.80 |
| `WEIGHTS[forest]` | 0.5 / 2.0 | 0.967 / 0.996 | 0.668 / 0.086 | 7/13, 6/13 | 0.63 / 1.40 |
| `WEIGHTS[curves]` | 2.0 | 0.986 | 0.572 | 10/13 | 0.52 |
| `CURVE_FULL` | 0.5 | 0.997 | 0.568 | 5/13 | 0.34 |
| `RELIEF_FULL` | 0.5 | 0.998 | 0.674 | 4/13 | 0.56 |
| `WEIGHTS[urban]` | 0.5 | 0.997 | 0.636 | 5/13 | 0.35 |
| `RAW_BASE` | 0.5 / 2.0 | 0.997 / 0.996 | 0.723 / 0.568 | 4/13, 6/13 | **0.86 / 1.69** |
| `WEIGHTS[relief]` | 0.5 / 2.0 | 1.000 / 0.997 | 0.770 / 0.674 | 3/13, 5/13 | 0.30 / 0.65 |
| `WEIGHTS[coast]` | 0.5 / 2.0 | 1.000 | 0.666 / 0.731 | 1/13, 2/13 | 0.00 |
| `WEIGHTS[scenic_tag]` | 2.0 | 1.000 | **0.072** | 2/13 | 0.00 |
| `WEIGHTS[farm]` | 0.5 / 2.0 | 1.000 | 0.971 | 1/13 | 0.00 |
| `WEIGHTS[views]` | 0.5 / 2.0 | 1.000 | 0.996 | 0/13 | 0.01–0.02 |
| `UNPAVED_AVOID_MIN_PER_KM` | 0.5 / 2.0 | 1.000 | 0.996 | 0/13 | 0.00 |

Sanity: `PREF_CURVE ×0.5` reproduces `BETA ×2.0` to every digit, which it must
at `pref=0.5` — the harness is measuring what it says it is.

**The prediction "most of them never move a route" is wrong, and the median is
the wrong statistic.** Look at `WEIGHTS[scenic_tag] ×2`: median overlap **1.000**
over 13 pairs, and on one pair **92.8% of the route changes**. A constant that
is inert on twelve routes and rewrites the thirteenth is not decoration. The
same shape appears on `coast` (1.000 median, 0.666 worst), `relief`, `urban` and
both halved range constants.

The honest reading of those worst cases is *a near-tie broken the other way*,
not a secretly powerful constant — a route with two nearly equal-cost
alternatives will flip on any perturbation. That is the point. **C1's inference
— "decoration to be deleted rather than tunables to be fitted" — does not follow
from this data**, because a constant that only matters where the answer is close
is a constant that decides the close calls, and the close calls are most of what
a scenic router does. If C1 is run for real, report the *worst* case per
constant, not the median, over many more than thirteen pairs, and report how
often a flip lands on a route the driver would notice.

**Two constants are provably invisible to the only external validation the
project has.** `RAW_BASE` moves the reported score by up to 1.69 points while
leaving the median route 99.6% intact — and the separation statistic is a *rank*
statistic (`analyze_trace.py:1243-1261`), so a monotone rescale of every score
cannot move it at all. `RAW_BASE` and `STRETCH` are display calibration with a
mild side effect on routing (they act as a flat per-km distance toll through
`km·(1 − score/10)`), and nothing in the repo says so. That is worth one comment
in `score.py` and is the most actionable thing C1 produced.

**Verdict: build after a named cheap test — and the cheap half is done.** The
remaining half needs a rebuild per perturbation and should be scoped as such,
not as "the cheapest item in the document". If the goal is to delete constants,
the rebuild half is where the candidates are (`CURVE_CAP`, `CURVE_MIN_LEN`,
`MIN_AREA`), and F2 is the thing that makes it affordable.

### A1 — the viewshed · **build after a named cheap test: fix the threshold first**

The brief's central claim is that `relief.tif` reduces the DEM to one scalar and
so cannot tell a ridge road from a ravine road. **Measured, and it is stronger
than claimed.** Ray-casting 16 rays to 5 km over
`data/processed-ne/elevation.tif` at 40,000 sampled chunk midpoints:

```
corr(openness, c_relief) = -0.005
corr(openness, score)    = -0.102
among chunks with c_relief > 0.6 (n = 7,230): openness p10 0.00  p50 0.06  p90 0.31
```

`c_relief` carries **no** information about the view — not "little", none. And
openness is near-orthogonal to the entire nine-component composite. Whatever it
is measuring, the model does not have it.

**The density gate (Trap 3) has no answer until the definition is fixed**, and
that is the finding:

| candidate `c_openness` | mean | km-wtd | % km ≥ 0.5 |
|---|---|---|---|
| fraction of rays with horizon ≤ 0° | **0.101** | 0.105 | **3.0%** |
| fraction of rays with horizon < 2° | 0.656 | 0.637 | 71.6% |
| `1 − mean horizon / 20°` | 0.895 | 0.889 | 99.4% |
| `1 − mean horizon / 10°` | 0.791 | 0.779 | 91.2% |
| *for scale:* `c_coast` (sparsest usable today) | 0.084 | 0.070 | 7.0% |
| *for scale:* `c_forest` (densest today) | 0.471 | 0.505 | 43.9% |
| *for scale:* the road-class column the study rejected as too dense | 0.841 | — | 88.0% |

The same terrain gives a column sparser than `c_coast` or denser than the column
`docs/driver-preferences-study.md` rejected, depending on one threshold nobody
has justified. **So the named cheap test is: pick and defend the threshold
before measuring anything else about A1**, because the density argument is
downstream of it and so is everything the brief says about which slider it goes
on. The `horizon ≤ 0` definition lands in the regime the weight pot is
calibrated for and is the one to start from.

**Two things the brief should know before anyone writes this.**

*The DEM is in Web Mercator and the vertical is not.* `elevation.tif` is
EPSG:3857 at 76.44 "metres" per pixel, which at latitude 43° is **56 ground
metres**. An implementation that treats the pixel size as ground distance gets
every horizon angle too small by `cos(lat)` — 27% at 43°N — and, worse,
*latitude-dependent*, so Maine would read as systematically more open than
Connecticut. That is the same shape as the `c_green` designation gradient and
the WorldCover `floor`-not-`ceil` bug: a plausible-looking number, wrong by
region. My measurement corrects for it; a first implementation will not.

*Relief and openness disagreeing is not evidence either is right.* Both are
geometry. The claim that openness predicts *beauty* is untested and — per the
bar section — cannot be tested on the 79 marks. A1 is a good candidate for the
first thing C6/C2 collect labels about.

### B1 — `c_novelty` · **reject**

Trap 3 asks for the density before any other argument, so: distance from each
edge's 9-vector to the length-weighted mean vector of a 3.5 km neighbourhood
(a grid box blur, which is generous to the proposal — a network ball is a subset
of a Euclidean one).

| | p10 | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| raw L2 distance to local mean | **0.340** | 0.613 | 0.944 | 1.229 | 1.764 |

| normalisation | mean | km-wtd | % km ≥ 0.5 |
|---|---|---|---|
| ÷ p99 | **0.512** | 0.428 | **34.5%** |
| ÷ max | 0.357 | 0.298 | 9.0% |

On the p99 normalisation — the one anybody would actually write — `c_novelty`
has **the highest mean of any component in the model** (`c_forest` is 0.434 at
the edge level) and would be the second densest. On the max normalisation it
still beats `c_relief`.

**This is structural, not a tuning problem.** The p10 is 0.340: *the least
novel decile of New England road is still 0.34 from its neighbourhood mean.*
A contrast measure has a floor, because no road exactly equals the average of
its surroundings. There is no "not novel" road to be 0, which is exactly the
property every existing attraction has and the property `RAW_BASE` and `STRETCH`
were fitted against. Adding it as a seventh `BEAUTY_TYPES` entry reproduces the
failure `docs/driver-preferences-study.md` §6a measured and rejected.

And it is not even new information: **`corr(novelty, score) = +0.390`**. Most of
what it flags is what the score already flags.

The escape hatch is real but does not save the proposal. A *centred* term
outside the renormalised pot — the study's variant A, which moved p50 by 0.05
against variant B's 1.41 — is density-neutral by construction. But a centred
novelty term rewards above-local-average road and penalises below-local-average
road, and at ρ = +0.39 with the composite that mostly amplifies the existing
ranking while adding a term nobody can explain to a driver. **Reject.** If the
underlying wish is "take me somewhere different from where I am", that is a
routing objective, not a column, and it needs state — see B3.

### E1 — split `c_urban` · **reject as motivated**

Decomposing the column exactly as `score.py:361-365` builds it:

| | % of network km | length-wtd composite score |
|---|---|---|
| `c_urban = 1.0`, retail/commercial polygon only | 3.9% (9,312 km) | 5.15 |
| `c_urban = 1.0`, town-centre node only | 8.1% (19,188 km) | 6.24 |
| `c_urban = 1.0`, both | 0.8% (1,945 km) | 5.75 |
| `c_urban = 0.5`, the wider orbit | 14.0% (33,009 km) | 5.20 |
| `c_urban = 0.0` | 73.2% (173,024 km) | **4.22** |

Overlap: P(retail | town node) = 9.2%, P(town node | retail) = 17.3%.

**The two halves are nearly disjoint, as the brief guessed — and they do not
have opposite signs.** Both sit well above the non-urban baseline of 4.22, and
the town-centre half carries **twice** the km of the retail half. The
hypothesis "two things averaged into noise" needs the two things to roughly
cancel; a 2:1 mass ratio with both terms positive does not produce noise, it
produces the town-centre half's answer. (These are composite scores and
`c_urban` is *in* the composite at the same value for both groups, so the 1.09
gap between them is the *other* components — town-centre roads are in prettier
places on water, forest and relief. That is a fact about where villages are, not
about urban-ness, and it argues against the split rather than for it.)

**And the evidence that started this has already been ruled insufficient by the
project.** `c_urban`'s 0.35 separation sits 0.018 below the null band's floor,
clears a one-tailed test and fails a two-tailed one, and
`docs/unpaved-and-urban-verdict.md:354-357` records that with nine components
examined, one reaching p=0.030 by luck alone has probability ~24%. E1 proposes
to *subdivide* that signal — testing two sub-columns on the same 76 marks, which
adds two more tests to a family that is already the problem, without adding one
observation.

**Reject as motivated.** What would revive it is what the verdict doc already
specified and nothing has done: a **second driver** replicating on the same
eastern-Massachusetts roads. If something has to move sooner, `town` is already
a `BEAUTY_TYPES` entry (`router.py:232`) — the lever is the *client's default
slider*, which is reversible and needs no rebuild, and the existing doc says so.

---

## Shallow verdicts, with what would settle each

### A2 — landcover entropy / edge density · **build after a named cheap test**

Correct that this is the cheapest test of the Group A thesis, and the brief is
right that it should be run before A1 is costed. Two facts it does not have.

`landcover.py` **streams** the WorldCover tile over `/vsicurl/` by default and
there is no tile cache on this Mac (`data/raw/` holds PBFs and Terrarium only).
So A2 is not "the same pass again" on data already local — it is a re-read of
three 36000×36000 tiles. (Disk is less of an obstacle than the docs assume: this
Mac has **64 GB free** today against the 4.7 GB `docs/unpaved-and-urban-brief.md:152`
recorded on 2026-08-29.) The cheap version is to stream one modest window over a
few thousand geographically clustered chunks and report the density
distribution: an afternoon, and nothing written to disk.

The hypothesis is the good part. "Beauty tracks heterogeneity, not any single
class" is a real, testable, and — unlike novelty — *plausibly sparse* claim,
because most road is in the interior of one class. **Named test: entropy and
transition density over ~5,000 clustered chunks, reported as the density table
in this document's A1 section, before any correlation is quoted.**

### A3 — canopy over the road vs near it · **build now** (inside A2's pass)

One `uint8` comparison on a pixel the box already reads. It costs nothing, it is
a distinction `c_forest` genuinely cannot express, and unlike everything else in
Group A it needs no new threshold: centre-pixel tree/not-tree is the same
predicate `landcover.py:246` already uses. The only caveat is that the centre
pixel is ~9 m × 7 m and a road corridor is wider than that, so "tree tunnel"
will read as noisy on any road with a mapped verge — worth a 3×3 centre rather
than one pixel. Build it as a column and *do not weight it* until there is a
label to fit against.

### A4 — directional scores · **reject as scoped**

It doubles the component table (18 columns), doubles the `pref_matrix`, breaks
the undirected-edge assumption that `graph.py` and `Router` are built on, and is
gated on A1, whose payoff is unmeasured. Nothing in this document justifies that
order of change. The genuinely cheap half — *road bearing*, which is already in
the geometry — is free and belongs with E3, where the bearing is the input
anyway.

### B2 — `c_reveal` · **cannot be determined**

Strictly downstream of A1 and it inherits A1's threshold problem in a worse
form: a derivative of a quantity whose absolute scale is unjustified has an
unjustified scale *and* an unjustified length scale (over how many metres is a
reveal a reveal?). It also has B1's shape — a gradient, like a contrast, has no
natural zero — so it should be density-gated before it is built, on the same
table. *What would settle it:* A1's threshold, then the same density table.

### C2 — pairwise labelling · **build now**

The one proposal that raises the ceiling on every other proposal in the
document, and the only one whose cost is client work with no rebuild, no
redeploy and no new data source.

The argument for it here is not the usual information-theoretic one, it is the
bar section. **The binding constraint is 19 dull marks**, because the
Mann-Whitney null SE is `sqrt((n1+n2+1)/(12·n1·n2))` and that is governed by the
smaller class: the 499 marks needed to reach a 0.55 ceiling are 499 *because*
only 24% of taps are dull. A pairwise design has no thin side — every judgement
is itself a comparison, so there is no class to run short of, and the estimator
is a fit over comparisons rather than a two-sample rank test. That is the whole
argument, and it does not depend on any claim about bits per judgement.

The design risk is that a pairwise judgement made at 45 mph is not available —
you cannot compare a road you are on to one you drove 20 minutes ago. Either it
is a post-drive screen over the trace's own stretches (which loses the
"does not survive the trip home" property the README is built on) or it is over
imagery (which is C3). **Say which before building.** The post-drive version is
the cheap one and is worth doing even at a discount, because its output is
comparisons against the *same* driver's in-drive marks, which is a calibration
nothing currently has.

### C3 — label from imagery, deploy from geodata · **cannot be determined**

Structurally the right idea — the geodata stays deployable and imagery is only
the yardstick — and the blocker is not the one the brief flags.

*On Trap 9.* The licensing question is real and I am not resolving it. Two
things narrow it. First, this project has already reasoned the analogous
question correctly for ODbL (`docs/licensing-and-attribution-brief.md:58,71`):
share-alike attaches to a derivative *database*, not to a produced work, and
nine fitted floats are much further from the source than a rendered polyline is.
The CC-BY-SA analogue turns on whether fitted weights are "Adapted Material",
which is a facts-versus-expression question with real authority on both sides
and different answers in the US and the EU. Second, and more practically:
**Mapillary's image licence and Mapillary's API terms of use are different
instruments**, and the terms have changed since the Meta acquisition. A verdict
that reads the CC-BY-SA badge and stops has answered the easier question. *What
would settle it:* the current API terms read end to end, and — because the
answer may be "it depends on whether you redistribute" — a design note saying
explicitly that no image is stored, cached or shipped.

*The reason it is undetermined is C4.* C3's whole value is that imagery scales
the label supply, and it only scales it if a machine does the rating. A human
rating 10,000 Mapillary images is not obviously cheaper than a second driver,
and it is worse evidence — a still frame is not a drive.

### C4 — a VLM as the rater · **reject the gate as specified**

The brief says "the gate is the whole proposal. Review the gate, not the vibe."
So: **the gate cannot be run, and if it could be run it would not discriminate.**

1. **The bar is inside the noise.** The gate is "reach the driver's own
   separation on the marks that exist" — 0.7395, with a bootstrap 90% CI of
   [0.646, 0.832]. A VLM scoring 0.70 is statistically indistinguishable from
   the model *and* from the 0.626 floor. The gate has no resolution at n=79.
2. **Running it adds a test to the family.** Per the bar section, the
   twenty-proposal ceiling is already 0.715. The gate is not free to attempt.
3. **It has an unstated prerequisite.** The 79 marks are anchored to road
   stretches; a VLM rates images. To run the gate at all you need imagery at
   those 79 locations, facing the right way, in August. Mapillary coverage there
   is an empirical question the proposal does not raise, and it comes before
   everything else.
4. **Passing it would prove the wrong thing.** A VLM that reproduces one
   driver's 79 taps has been validated as a clone of the sample the project is
   trying to escape. The failure mode of one rater is not fixed by automating
   that rater.

**The idea survives with a different gate:** agreement with a *second human*, on
imagery, on roads where the two humans also disagree with each other — which
measures the VLM against the inter-rater spread rather than against one person.
That gate needs the second rater first, which is C2/C6's dependency too. Until
then, C4 is blocked on the same thing everything else is.

### C5 — geotagged-photo density · **reject**

The brief's own reasoning is correct and complete: it measures *famous*, not
*beautiful*, and population-normalising a tourism confound does not remove it —
the Kancamagus is photographed because it is a destination, and so is Quincy
Market. Recorded as rejected, as asked. One salvage worth a line: as a
*negative* control it is genuinely useful — a candidate scenery signal that
correlates with photo density no better than road class does is probably
measuring popularity too.

### C6 — active-learning drive planning · **build after a named cheap test**

Agreed that this is the highest-leverage item, for the reason the brief gives:
the bottleneck is 79 labels and one rater, not compute and not ideas. One
correction to the design.

**Do not target model uncertainty first; target the disagreements you already
have.** `analyze_trace.py` already prints them, and on the current build they are
specific:

```
dull  6.4  primary    High Street Extension   42.44381,-71.66654
dull  6.2  secondary  Main Street             42.34857,-71.73930
dull  5.6  primary    Old Sudbury Road        42.36804,-71.36657
nice  0.0  motorway   Massachusetts Turnpike  42.22745,-71.64064
nice  0.0  motorway   Massachusetts Turnpike  42.24160,-71.59546
nice  0.0  motorway   Massachusetts Turnpike  42.30079,-71.46954
```

Those three Turnpike marks are 5% of every nice mark in the project, on road the
model floors at or near 0.0 (two are ≤ 0.01 exactly; the third rounds to 0.0 in
the table). The two at ≤ 0.01 are the two most influential *nice* marks in the
jackknife above.

Either the road-class penalty is wrong for this driver on those
stretches, or the marks are misfires — and which it is changes
`CLASS_ADJ`, which C1 shows moves 11 of 13 routes. A loop through those six
addresses is one afternoon and resolves a live ambiguity. Model-disagreement
sampling is the right second version; **replication of known disagreements is
the right first one**, because it is the only design where the answer is
interpretable at n=6.

The named cheap test before building any of it into `looper.py`: check that a
loop constrained to pass N specified chunks is even feasible at reasonable length
— `looper.py` optimises for sector coverage, not for waypoint sets, and
"maximise uncertain chunks visited subject to a 40 km budget" is an orienteering
problem, not a loop-shape problem.

### D1 — grade drives, not roads · **cannot be determined**

The largest change in the document and the least specified, as it says. One
measurement narrows it usefully: **OSM's own catalogue of named scenic routes
already exists and is already extracted.** `docs/byway-relations-brief.md`
(built and measured 2026-08-29) found 54 relations across 13 networks, 53
distinct named routes, 5,550 drivable member ways, **4,026 km** — which is
**1.7% of the network's 236,477 km** — consistent with, and a little above,
`c_scenic_tag`'s measured 1.4% of scored km at ≥ 0.5 (3,311 km), the gap being
byway members that `extract.py` drops as non-drivable.

So the coverage-hole risk is not a risk, it is the proposal: 98.3% of the
network has no catalogue entry and D1 is a plan to manufacture one by
changepoint segmentation. That is the part to specify. Three questions that
would settle whether it is worth specifying:

1. **Does changepoint segmentation on the existing components produce runs a
   person would name?** Cheap to test: segment one county, print the top 20 runs
   by length-weighted score with their road names, and look at them. If they are
   not recognisable drives, the atom is not the problem.
2. **What is the selection problem's size?** "Select from thousands of catalogue
   items" is only affordable if it is thousands. 236,477 km in 3–20 km runs is
   ~20,000–70,000 items before any filtering.
3. **Does it survive the connector?** A route is beads plus graph. The graph part
   is the same Dijkstra and the same `E^1.28`; D1 moves the hard part, it does
   not remove it.

### E2 — tranquility / motorway-noise penalty · **build after a named cheap test**

Density, on the real build (distance from each edge midpoint to the nearest
motorway / motorway_link / trunk / trunk_link midpoint):

| within | % of network km |
|---|---|
| 200 m | 10.4% |
| 400 m | 14.7% |
| 800 m | 22.8% |

(p10 distance 140 m, p50 1,707 m, p90 8,680 m. Midpoint-to-midpoint understates
proximity on long edges, so these are floors.)

10.4% is squarely in the sparse regime and the mechanism already exists —
`near_flags` with a negative weight. But **it is a negative term, and the floor
has a guard with less headroom than it looks**. 2.204% of network km is clipped
at score 0.00 today, and `tests/test_calibration.py:73` asserts
`share(km, s <= 0.01) < 0.12`. A penalty applied to 10.4% of km can plausibly
put a large part of it through the floor — where `km·(1 − score/10)` stops
discriminating between roads in exactly the way `_edge_scores`' docstring
describes for the ceiling, and where a further penalty buys nothing because the
road is already maximally unattractive.

Named cheap test: apply the candidate penalty live through `score_adj`, measure
the share of km at 0.00 before and after, and only then look at routes. If 2.2%
goes past about 5%, the term belongs in the routing cost rather than in the
score — which is where `UNPAVED_AVOID_MIN_PER_KM` ended up, for the same class
of reason.

### E3 — sun azimuth vs road bearing · **cannot be determined**

Trap 7 is correct and is the whole verdict: a time-of-day modifier applied
inside `Router._edge_scores` breaks
`test_neutral_weights_reproduce_the_precomputed_score` by construction, so it
must go in `_weights`, outside the composite — which is the `UNPAVED_ADJ` lesson
(`router.py:148-167`) exactly. That much is settled and the brief settled it.

What is not determined is whether anyone wants it. It bundles two different
products: "route me toward the sunset" is a scenery preference, and "do not point
me into low sun" is a safety constraint. They have opposite signs on the same
geometry, they want different defaults, and one of them is a claim about hazard
that this project has no evidence for. *What would settle it:* separate them,
and price only the safety one — it is a hard constraint on a handful of
minutes-per-day and does not need the scenery machinery at all.

### E4 — foliage season · **cannot be determined**

Correct that this is New England's biggest scenery event and the model is blind
to it. Correct that NLCD 41/42/43 splits deciduous from evergreen and WorldCover
does not.

It cannot be evaluated because **there is not one drive mark in foliage season**:
every trace in `traces/` is 14–25 August 2026. A date-dependent modifier on
`c_forest` would be the only part of the model that cannot be checked against a
single observation, in either direction, and the effect it claims is large. It
also lands on the wrong side of Trap 7 — a seasonal multiplier inside the
composite breaks the precomputed-score identity, and outside it, it is a routing
term whose strength nothing calibrates.

*What would settle it:* drives in the first three weeks of October, on the same
roads as the August drives, by the same driver. That is the cheapest
high-information data collection available to this project and the window is
three weeks away. It is worth planning now even though the feature is not.

### E5 — continuous distance decay · **build after a named cheap test**

Trap 5 is right that this must not be sold on speed, and I will add that the
trap's own supporting number needs care. `dwithin` returns few hits — but the
`water_areas` query alone took **203 s** on this build, because the cost is
driven by polygon vertex count, not by hit count. So "score.py is already
O(n_chunks)" is true and "score.py's feature stage is cheap" is not. That still
does not make E5 a speed proposal: the cost is on the build Mac, once, and
`docs/unpaved-and-urban-brief.md:152` already prices a full score rebuild at 11
minutes. **A verdict recommending E5 on performance grounds is still wrong; it
is just wrong about a smaller number than the trap implies.**

The model-quality case is real and measurable, and the numbers are worse than
"a factor of three". Measured over 60,000 sampled chunks, true distance to the
nearest feature *inside each band*:

| band | share of chunks | p10 | p50 | p90 |
|---|---|---|---|---|
| water, `c_water = 1.0` — `[0, 120)` m | 12.3% | 8 m | 47 m | 102 m |
| water, `c_water = 0.45` — `[120, 350)` m | 14.5% | 141 m | 232 m | 326 m |
| water, `c_water = 0.0` — `≥ 350` m | 73.2% | 480 m | **1,127 m** | 2,844 m |
| green, `1.0` — `[0, 80)` m | 30.9% | 0 m | 8 m | 56 m |
| green, `0.0` — `≥ 80` m | 69.1% | 145 m | 535 m | 2,273 m |
| **coast, `c_coast = 1.0` — `[0, 800)` m** | 8.4% | **33 m** | 244 m | **652 m** |

The strongest case is the coast band and it is not the one the brief makes. A
road 33 m from the Atlantic and a road 652 m inland get **the same 1.0**, a 20×
spread inside one boolean. And the sharpest discontinuity is at the *outer*
edge: a chunk 360 m from water scores 0.00, identically to one 3 km away, while
the p50 of that whole group is 1,127 m. The brief's framing — "the 0.45 is not a
claim about how water looks at 130 m versus 110 m" — is right but points at the
mildest of the three defects.

The case against is that it turns three tunable distances into an unbounded
family of decay shapes with nothing to fit them against, which is the same
problem A1's threshold has. **Named cheap test: before rasterising anything,
re-derive the existing bands as a continuous function and check whether any
route changes.** If the 0/0.45/1.0 step and a smooth decay through the same
distances give the same routes, E5 is a code-quality change and should be
scheduled as one.

### F1 — kill the dual representation · **reject as scoped**

Three of the four stated payoffs do not survive (corrections §5 above): the
midpoint error class was fixed in August, the join is 2.8M points rather than
~1M, and the 208.7 MB never reaches the serving box.

**The fourth does not survive either, and this is the measurement that settles
it.** I re-ran `attach_scores`' join exactly as `graph.py:538-545` performs it,
over all 2,841,347 sample points:

| | |
|---|---|
| samples more than `MAX_CHUNK_SNAP_M` (150 m) from a chunk | **0** |
| worst gap, and every percentile up to p99.99 | **0.0 m** |
| samples whose nearest chunk has a different `highway` class | **0** |
| samples whose nearest chunk has a different name (both named) | 1 of 2.8M |
| the comment's own example — a non-motorway edge taking a **motorway** chunk | **0 samples, 0 edges** |

The join is not approximate on this build; it is **exact**. Chunks are cut from
the same way geometries the edges are cut from, so every sample point lies on
its own chunk at distance zero. The failure the comment at `graph.py:548-554`
describes is real as a *class* and has never fired — the guard rail exists to
catch an operator running `score.py` and `graph.py` against different PBFs, which
is a different problem and one F1 would not fix either. The whole join, STRtree
build included, takes **30 s** of a ~17-minute build.

So the correctness payoff is zero, the disk payoff is on the wrong machine, and
the performance payoff is 30 seconds.

Against that, Trap 6 is correct and, if anything, understates it. The reorder
invalidates `tree_cover.parquet`, whose join to `scored_chunks.parquet` is
positional and checked to `atol=1e-9` on every midpoint (`score.py:250-256`), so
it forces a landcover re-run — three streamed WorldCover tiles. And junction
splitting needs the PBF's node reference counts
(`graph.py:307`), which `score.py` never sees, so it is a pipeline reorder
rather than a function move.

**Reject as scoped.** The one part worth keeping: if F2 is built, the component
cache will need a stable chunk identity anyway, and *that* is the moment to
revisit the atom — as a consequence of a change with an independent payoff,
not as a refactor justified by four payoffs that are not there.

### F2 — component-level rebuild cache · **build now**

The proposal is right and its own supporting claim is wrong; see corrections §1.
Build it on the corrected argument, which is stronger:

- **`WEIGHTS` retuning is restart-only for routing and rebuild-only for
  validation.** The router re-blends live; `analyze_trace.py` reads the stored
  column. So today, retuning and re-validating are not the same operation and
  nothing says so. That is the bug F2 removes.
- **It is the enabling change for C1, C2, C4 and C6**, and C1's own results say
  why with a number: the half of C1 that is cheap took 199 s including load, and
  the half that needs `score.py` costs ~17 minutes *per perturbation*. Caching
  per-column on a hash of its inputs and constants collapses the expensive half
  to the cheap half for every constant that touches one column — which is
  `CURVE_D`, `CURVE_CAP`, `CURVE_MIN_LEN`, `CURVE_FULL`, `RELIEF_FULL`, and each
  `DIST` entry separately.
- Key each `c_*` column on (input layer hashes, the constants that column reads,
  `CHUNK_LEN`). Note that `CHUNK_LEN` and `MIN_AREA` invalidate everything, and
  that `WEIGHTS` invalidates **no** component column — only the derived `raw`,
  `score` and `graph_edges`. That asymmetry is the cache's whole value and it
  should be written down in the cache, not just implied by it.

### F4 — customizable contraction hierarchies · **cannot be determined; out of scope**

Correct on the theory: plain CH cannot serve per-user metrics and CCH was
designed for exactly this. The brief asks to be told if it is out of scope, so:
**it is, today.** F3's measurement is the reason. The fastest arm is already
solvable to 0.0–0.1% of the graph with a heuristic that takes 10 s to precompute, and
the scenic arm's problem is not the algorithm but that `pref=1` genuinely
explores a large cost ball. Before CCH, the cheaper question is whether the
scenic arm needs the whole region at all — Burlington→Bangor at `pref=1` settles
95.8% of New England, and a driver asking for a scenic Vermont-to-Maine route is
not going to be routed through Rhode Island. A geometric corridor restriction is
a tenth of CCH's work and is untested.

*What would settle F4:* the region growing past the Northeast, which
`docs/new-england-expansion.md` prices independently, or a measured
requests-per-second requirement that today's single serving laptop cannot meet.
Neither exists.

---

## Ranked by evidence obtainable per hour

Differs from the brief's ranking, as invited.

| # | item | why here | cost |
|---|---|---|---|
| 1 | **C6 first version — drive the six known disagreements** | resolves a live ambiguity in `CLASS_ADJ`, which C1 shows moves 11/13 routes; the addresses are already printed | one afternoon, no code |
| 2 | **Plan October foliage drives (E4's prerequisite)** | the window is three weeks away and closes for a year; it is also the only way to test E4 ever | zero now, one drive later |
| 3 | **F3 on the fastest arm** | proved admissible; ALT-16 measured at 2.9% of the graph and 11x faster than scipy, ~25% of request latency | days |
| 4 | **C2 post-drive pairwise screen** | the only thing that lifts the bar every other proposal has to clear | client work, no rebuild |
| 5 | **F2 component cache** | makes C1's expensive half cheap and removes a real staleness | days |
| 6 | **A2 + A3 on ~5,000 clustered chunks** | cheapest test of the whole Group A thesis; must report density first | an afternoon |
| 7 | **A1 threshold decision, then its density table** | the signal is orthogonal and free to compute; the definition is the open question | hours |
| 8 | **A second driver on the same eastern-MA roads** | the only thing that answers the multiple-comparisons worry at all | one afternoon, not mine to schedule |
| 9 | **E2 floor check** | cheap, and tells you whether it is a score term or a routing term | hours |
| 10 | **E5 same-bands-continuous route check** | decides whether E5 is a model change or a tidy-up | hours |
| — | *done in this document* | B3, C1's live half, E1, B1, F2's premise, F1's premise | — |
| — | *blocked on a rater, in this order* | C4 gate redesign, C3, then D1 | — |
| — | *out of scope* | F4, A4 | — |


---

## Measurement appendix

### Component density, both atoms

Trap 3 asks for coverage before any other argument, so here is the reference
scale a new column has to be read against. `docs/driver-preferences-study.md`
§6a measured on **chunks**; the router sees **edges**. Both, on
`data/processed-ne`:

| component | chunk mean | chunk % km ≥ 0.5 | edge mean | edge % km ≥ 0.5 |
|---|---|---|---|---|
| `c_views` | 0.012 | 1.0% | 0.014 | 1.0% |
| `c_scenic_tag` | 0.012 | 1.4% | 0.010 | 1.4% |
| `c_farm` | 0.027 | 3.2% | 0.020 | 3.1% |
| `c_coast` | 0.084 | 7.0% | 0.104 | 6.6% |
| `c_water` | 0.244 | 15.6% | 0.252 | 17.6% |
| `c_urban` | 0.242 | 26.8% | 0.305 | 24.4% |
| `c_relief` | 0.383 | 29.6% | 0.339 | 30.0% |
| `c_curves` | 0.395 | 44.0% | 0.385 | 44.6% |
| `c_forest` | 0.471 | 43.9% | 0.434 | 39.3% |
| *proposed* `c_novelty` (÷ p99) | — | — | **0.512** | **34.5%** |
| *proposed* `c_openness` (horizon ≤ 0°) | 0.101 | 3.0% | — | — |
| *proposed* `c_openness` (horizon < 2°) | 0.656 | 71.6% | — | — |
| *rejected* road-class column, for scale | 0.841 | 88.0% | — | — |

The chunk column reproduces the study's table exactly, which confirms both the
study's atom and that this build is the one it measured.

### The `dwithin` hit rate (Trap 5)

Every `near_flags` call in `score.py`, on all 942,448 chunks:

| layer | distance | hits | per chunk | seconds |
|---|---|---|---|---|
| `water_areas` | 350 m | 311,946 | 0.33 | **202.8** |
| `coastline` | 800 m | 313,953 | 0.33 | 3.1 |
| `green_areas` | 80 m | 451,170 | 0.48 | **142.0** |
| `farm_areas` | 80 m | 34,673 | 0.04 | 1.0 |
| `viewpoints` | 400 m | 15,513 | 0.02 | 0.6 |
| `urban_areas` | 100 m | 103,743 | 0.11 | 1.4 |
| `place_points` | 900 m | 327,302 | 0.35 | 1.4 |
| **total** | | **1,558,300** | **1.65** | **352.3** |

1.65, against the trap's 1.8. The hit rate is low and the time is not, for the
reason in corrections §6.

### Which constants can be reached without a rebuild

| reachable live | how |
|---|---|
| `BETA`, `PREF_CURVE`, `UNPAVED_AVOID_MIN_PER_KM`, `MAX_AVOID_UNPAVED` | module globals in `router.py`, read inside `_weights` at call time |
| `RAW_BASE`, `STRETCH` | `score.composite()` reads them at call time — **no restart needed** |
| `WEIGHTS` | rebuild `Router.base_score` / `pref_matrix`; needs a **restart** in production |
| `CLASS_ADJ` | `Router.score_adj` is exactly `highway.map(CLASS_ADJ)` — verified to 3.4e-15 |
| `CURVE_FULL`, `RELIEF_FULL` | **downward only**; the stored column is clipped at 1.0 and cannot be un-clipped (14.0% of chunks pinned on curves, 2.1% on relief) |

| needs `score.py` re-run (~11 min) + `graph.py` (~6 min) |
|---|
| `DIST` (7 values), `MIN_AREA` (3), `CHUNK_LEN`, `CURVE_D`, `CURVE_CAP`, `CURVE_MIN_LEN`, and `CURVE_FULL`/`RELIEF_FULL` upward |

---

## Reproducing this

Five scratch scripts, none of them in the repository, all run against the main
checkout's data from a worktree holding `main` plus these two documents:

```bash
SCENIC_DATA=<abs>/Scenic/data/processed-ne
.venv/bin/python <scratch>/router_probe.py    # F2 · F3/Trap 4 A* bound
.venv/bin/python <scratch>/round2.py          # edge densities · B3 wall · B1 · E2
.venv/bin/python <scratch>/round3_c1.py       # C1 constant sweep
.venv/bin/python <scratch>/round4_chunks.py   # chunk densities · Hudson Rd · E1 · A1
.venv/bin/python <scratch>/round5.py          # Trap 5 · E5 banding · F1 join
.venv/bin/python <scratch>/jackknife.py       # the bar: jackknife + bootstrap
```

Each holds one loaded `Router` (39–40 s, 4.0 GB peak RSS) or one loaded
`scored_chunks.parquet`, and patches module globals and the Router's cached
derivatives in memory between calls — `pipeline/scenery_cap_experiment.py`'s
pattern. `jackknife.py` monkeypatches `analyze_trace.separation` to capture the
per-mark score arrays it already computes and calls `analyze_trace.main`
unchanged.

Costs worth knowing before repeating any of this: a full-graph scipy Dijkstra on
New England is 0.30–0.37 s; `route()` end to end is 0.37 s; the 13-pair × 32-perturbation
C1 sweep is 199 s including load; the A1 viewshed is 1.0 s for 40,000 midpoints
× 16 rays × 22 range steps; the F1 join re-run is 30 s over 2.8M points; the
`dwithin` battery is 352 s. Nothing here writes a raster or rebuilds anything.

**Always `.venv/bin/python -m <tool>`** — the project path contains spaces and
every venv console script has a broken shebang.
