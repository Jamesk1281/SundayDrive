# A\* on the fastest arm: ALT landmarks over the time metric

**Status: built 2026-09-19 — see "Built" at the foot of this file, which
records what this plan got wrong.** Everything above it is the brief as it was
written, before any of it was implemented: the numbers in it come from scratch
scripts outside the repository that load one `Router` and work on its arrays,
the `pipeline/scenery_cap_experiment.py` pattern. They held up. Four of the
inferences drawn from them did not, and one of those returned a wrong route.

Companion to `docs/scenery-grading-verdict.md` (proposal **F3**), which
concluded "build now, fastest arm only". **This brief supersedes that document's
payoff estimate**: the verdict quoted ~36% of request latency from the *perfect*
heuristic, and a real 16-landmark ALT delivers ~25%. Everything else in the F3
section still holds.

---

## The goal, as measured

`/api/route` answers every request with **two** Dijkstra searches
(`server/app.py:276-280`):

```python
fastest = ROUTER.route(s, t, 0.0, weights, heading=heading, avoid_unpaved=avoid_unpaved)
scenic  = (fastest if pref == 0.0
           else ROUTER.route(s, t, pref, weights, heading=heading, avoid_unpaved=avoid_unpaved))
```

Both run a **full-graph scipy Dijkstra with no target early-exit**
(`pipeline/router.py:1178`), so cost tracks region size, not trip length. On
`data/processed-ne` (801,719 routing nodes) every search settles all of them and
takes **220–265 ms**, whether the trip is 5.6 km or 314 minutes.
`docs/hosting-options-brief.md:44` measures a full API request at **~835 ms**.

Replacing the **`pref = 0` arm only** with A\* takes that arm from ~227 ms to
~20 ms. **~25% off every request with `pref > 0`.**

## Why it is safe: the admissibility proof, which is one line

`Router._weights` (`pipeline/router.py:1027-1038`):

```python
penalty = self.km * (1.0 - scores / 10.0)           # km of "unscenic" road
strength = max(0.0, min(1.0, pref)) ** PREF_CURVE
w = self.d_minutes + strength * BETA * penalty[self.eidx]
```

`score.composite()` clips to `[0, 10]`, so `penalty ≥ 0`. `strength`, `BETA`,
`avoid` and `dirt_km` (`:1035-1038`) are all non-negative. `self.d_minutes` is
built once at load (`:889`) from no user parameter. Therefore

> **`w ≥ d_minutes` pointwise, for every `pref`, every beauty-weight vector and
> every `avoid_unpaved`.**

`route()` collapses parallel edges by `np.minimum` (`:1175-1176`), and
`min_e w_e ≥ min_e d_minutes_e` follows from the pointwise bound, so the
collapse preserves it. **Any admissible heuristic for the time metric is
admissible for every query this router can be asked**, which is what makes one
user-independent landmark set correct for all of them.

## What to build, and the numbers that chose it

Three candidate heuristics, measured at `pref = 0` over 12 OD pairs spanning
5.6 km to 314 minutes. "Settled" is nodes of 801,719; lower is better. "Perfect"
is the true time-to-go from a backward Dijkstra — not implementable per request,
but it is the bound no heuristic can beat, so it is the yardstick.

| pair | scipy ms | perfect | **ALT-16** | ALT-8 | Euclidean | Python A\* (ALT-16) |
|---|---|---|---|---|---|---|
| Harvard→Needham | 241 | 0.0% | **1.5%** | 1.5% | 3.8% | 15.0 ms |
| Needham→Wachusett | 225 | 0.0% | **5.9%** | 6.4% | 16.5% | 72.7 ms |
| Needham→Worcester | 238 | 0.0% | **2.0%** | 3.9% | 4.2% | 18.5 ms |
| Needham→Wellesley | 227 | 0.0% | **0.0%** | 0.0% | 0.2% | 0.2 ms |
| Needham→Foxborough | 225 | 0.0% | **0.9%** | 1.2% | 2.0% | 8.2 ms |
| Needham→Groton | 227 | 0.0% | **3.8%** | 3.8% | 8.1% | 40.2 ms |
| BostonHarvSq→Providence | 227 | 0.0% | **4.2%** | 5.5% | 8.2% | 23.6 ms |
| Needham→Brattleboro | 229 | 0.1% | **5.4%** | 5.4% | 37.8% | 57.3 ms |
| Providence→Portland | 220 | 0.1% | **1.6%** | 1.7% | 34.7% | 17.1 ms |
| Concord NH→NorthConway | 235 | 0.0% | **1.5%** | 1.5% | 9.8% | 15.0 ms |
| Burlington→Bangor | 225 | 0.1% | **1.8%** | 1.8% | 31.0% | 22.0 ms |
| Needham→NorthConway | 265 | 0.1% | **11.3%** | 18.6% | 48.1% | 136.0 ms |
| **median** | **227** | 0.0% | **2.9%** | 3.8% | 9.0% | **20.3 ms** |

Three readings, each of which decides something:

**Euclidean is out.** A straight-line bound divided by the graph's fastest edge
(measured: 140.0 km/h) settles 31–48% on long routes. At those counts a Python
heap loses to scipy's C outright. Do not implement it as "the cheap version
first" — it is the version that does not work.

**ALT-16 over ALT-8.** Mostly a tie, but ALT-8 is 1.6× worse on the two hardest
pairs (Needham→NorthConway 18.6% vs 11.3%, Needham→Worcester 3.9% vs 2.0%). The
extra 8 landmarks cost 51 MB and 3.5 s of preprocessing.

**The perfect heuristic is 50–100× tighter than ALT-16, and it does not matter.**
ALT-16 already reaches 20 ms against scipy's 227 ms. Do not chase the gap.

Measured preprocessing: **32 Dijkstra runs in 7 s** at load. Tables are
`16 × 2 × 801,719`: **205 MB as float64, 103 MB as float32.** Use float32 —
rounding a lower bound *down* keeps it admissible; see Trap 7.

The scratch A\* used Python dicts and a `heapq`, so 20.3 ms is an **upper
bound** on what a numpy-array implementation costs.

## Correctness, already demonstrated

The scratch A\*, run with `h = ALT-16` and the target-set rule in Trap 1,
**reproduced scipy's path cost to 1e-6 on all 12 pairs**, and no admissibility
violation was found on any node of any pair (each heuristic was checked against
the true time-to-go from a backward Dijkstra). The algorithm is not the risk
here. The integration is.

---

## Traps

**Trap 1 — the destination is a *set*, and missing this returns a wrong route
silently.** `route()` does this at `pipeline/router.py:1187-1189`:

```python
targets = self.node_copies.get(dst_idx)
if targets is not None:
    dst_idx = int(targets[np.argmin(dist[targets])])
```

A junction split for turn restrictions stands at several node indices, and any
of them is a legitimate place to arrive. A full Dijkstra can pick the cheapest
afterwards because it settled all of them; **A\* cannot**. The rule that works,
and is what the measured run used: `h(n) = min over targets t of h(n, t)`, then
stop when the **first** target is popped. That is correct because the min of
lower bounds is a lower bound on reaching the nearest target.

**Trap 2 — build the landmark tables *after* `_apply_turn_restrictions`.**
`self.n` is set to 794,685 at `router.py:331` from `graph_nodes.parquet`, and
`_build_directed` → `_apply_turn_restrictions` (`:897`) then grows it to
**801,719**. Tables built against the pre-split node set are the wrong length
and, worse, the wrong *indexing* — they would load, run, and return plausible
routes. Precompute inside or after `_build_directed`, never before.

**Trap 3 — at `pref = 0` the weight is not `d_minutes`.** It is
`d_minutes + avoid * UNPAVED_AVOID_MIN_PER_KM * dirt_km` (`router.py:1035-1038`).
The heuristic stays admissible (the extra term is non-negative), but A\* must
search on the **actual `w` array `_weights` returns**. Caching one time-only
Dijkstra and reusing it as "the fastest route" returns the wrong road whenever
`avoid_unpaved != 0`, which is the default (1.0).

**Trap 4 — do not put the scenic arm on this, however tempting.** Measured at
`pref = 1`, even the *perfect* heuristic still settles 77.9% (Providence→Portland)
and 92.5% (Burlington→Bangor) of the graph; ALT will be worse. Leaving scipy's C
for a Python heap costs **3.6×** on this project's own measurement
(`docs/traffic-schedule-plan.md:232-234`: scipy static 88.6 ms vs Python static
319.9 ms). A Python A\* settling 90% of 801,719 nodes is several times *slower*
than what ships today. Gate strictly on `pref == 0.0` and let everything else
take the existing path unchanged.

**Trap 5 — search the collapsed pair graph, not the directed slot array.**
`route()` builds its matrix from one entry per `(tail, head)`, taking the
cheapest parallel edge (`router.py:1175-1177`). A\* must traverse the same
collapsed graph. If it walks `self.tail/self.head` directly it can settle a
parallel edge the cost matrix never offered, and `_collect` — which re-picks
`argmin(w[slots])` per hop at `:1230` — will then disagree with the path A\*
found.

**Trap 6 — node copies have no coordinates.** `self._nx` / `self._ny`
(`router.py:332-334`) are projected from `graph_nodes.parquet` and have 794,685
entries, not 801,719. Anything geometric must index through `self.real_node`.
(This matters only if the Euclidean bound is attempted; Trap 5's graph and the
ALT tables are both full-length. It is recorded because it cost time in the
scratch work.)

**Trap 7 — float32 rounding must go down, not to nearest.** The ALT bound is
`max(d(n,L) − d(t,L), d(L,t) − d(L,n))`, a difference of two stored values.
Rounding either to nearest can make the bound exceed the true distance by an ulp
and break admissibility. Either store float32 and subtract a small epsilon from
`h`, or clamp `h = max(h, 0)` *and* accept the path only if its cost matches a
verification pass. The simplest safe answer: store float32, compute `h` in
float64, and subtract `1e-6` minutes. Nobody notices a microsecond; an
inadmissible heuristic returns a wrong route with no symptom.

**Trap 8 — "same cost" is the assertion; "same edges" is a measurement, not an
assertion.** Road networks have genuine ties, so A\* and scipy can return
different equal-cost paths, and the driver would see a different road with the
same ETA. Assert cost equality to 1e-9. **Report** the share of OD pairs whose
edge list differs rather than asserting it is zero — if that share is large
enough to matter, that is a finding worth reporting back, not a bug to suppress
by tie-breaking until the test passes.

**Trap 9 — RAM.** `docs/hosting-options-brief.md` puts a warm `app.py` at
**≈4.3 GB** and recommends sizing the box at ~6 GB. float32 tables add 103 MB
(2.4%). That is fine on the chosen 24 GB target, but the 7 s of preprocessing
lands on **every process start**, on top of a 40 s load. If that is unacceptable,
the tables are a deterministic function of `graph_edges.parquet` and can be
written beside it — but do not add a new required file without saying so in
`Router.REQUIRED_EDGE_COLUMNS`'s neighbourhood, and keep the in-process
computation as the fallback.

---

## Done looks like

1. `Router` precomputes 16 ALT landmark tables over `d_minutes` at load, after
   turn restrictions are applied, as float32, in ≤10 s.
2. `route()` uses a numpy A\* when `pref == 0.0` and the existing scipy path
   otherwise. The scipy path is unchanged for every other input.
3. On a sample of at least 200 OD pairs spanning New England, the A\* arm's path
   **cost** matches today's to 1e-9 on every one; the share whose **edge list**
   differs is measured and reported (Trap 8).
4. Measured median latency of the `pref = 0` arm, before and after, on the same
   machine. The expectation from the scratch work is ~227 ms → ~20 ms; a result
   worse than ~80 ms means the implementation, not the idea, and is worth
   reporting rather than shipping.
5. `.venv/bin/python -m pytest tests/` green, with `SCENIC_DATA` pointed at the
   New England build.
6. A test that would catch Trap 1: an OD pair whose destination junction carries
   turn-restriction copies, asserted to route identically on both paths.
7. **Or** an honest statement that one of the traps above makes this not worth
   doing, with the measurement that shows it. That is a real answer.

## Reproducing the numbers above

One scratch script, outside the repo, ~120 lines: load `Router`, build the
collapsed time CSR and its transpose, pick 16 landmarks by farthest-point
selection over backward Dijkstra, run `2k` Dijkstras for the tables, then per OD
pair count `|{n : dist_w[n] + h(n) ≤ dist_w[dst]}|` for each candidate `h` and
time a `heapq` A\*. One `Router` load (23–40 s, ~4 GB RSS) serves the whole
sweep.

```
SCENIC_DATA=<abs>/Scenic/data/processed-ne     # the live New England build
```

The data lives **only in the main checkout**, never in a worktree. The project
path contains spaces, so every venv console script has a broken shebang: always
`.venv/bin/python -m <tool>`, never `.venv/bin/pytest`.

---

# Built, 2026-09-19

(`docs/scenery-grading-verdict.md`, referenced above, was not on the branch
this was built on — it was copied across on its own so that the plan and the
thing built from it travelled together. Both are on `main` now, merged from
`claude/funny-elbakyan-93c75f` alongside the component-cache brief.)

`pipeline/router.py` and `tests/test_routing.py`. `Router._build_alt_tables`
precomputes the tables at the end of `_build_directed`; `_alt_bound` turns them
into a per-node bound; `_astar` searches; `route` picks between it and
`_dijkstra_path`, which is the old body moved out whole so the scenic arm is
byte-for-byte the search it always was. Measured on `data/processed-ne`
(801,719 nodes), Apple M2, with another job holding a core throughout — so the
absolute figures are a little high, and the two arms were timed interleaved,
pair by pair, in one process, which is what makes the ratios fair.

**What it costs at load**, measured against the same load without it:
22.6 s -> 32.1 s and peak RSS 4.56 GB -> 4.66 GB. The tables are 103 MB and the
CSR row index another 6 MB, so +2.2% — Trap 9 estimated 2.4%.

**The arm, end to end** — `_edge_scores` through `_collect`, not just the
search:

| sample | old | new | |
|---|---|---|---|
| the 12 pairs above, best of 3 | 254.8 ms | **45.8 ms** | 5.6x |
| 250 OD pairs ≤ 60 km apart (median 43 min) | 303.6 ms | **38.0 ms** | 8.0x |
| 250 uniformly random OD pairs (median 125 min) | 276.6 ms | **76.4 ms** | 3.6x |

Against `hosting-options-brief.md`'s 835 ms request, the realistic sample is
**~32% off every request with `pref > 0`**, against the ~25% estimated here.

**Correctness.** 500 OD pairs over the two samples and all 5,897 split
junctions as destinations: **0 cost differences** above 1e-9 (worst 4.55e-13),
**0 edge-list differences** — Trap 8's tie-breaking worry is real in principle
and did not happen once. Admissibility checked by backward Dijkstra on the real
`w` for five targets: 0 violations over 801,717 nodes each. `avoid_unpaved` at
0.0, 1.0 and 2.0 all agree (Trap 3).

## Four things this brief had wrong or missing

**1. The bound is negative at the targets, and that alone returns wrong
routes.** The brief's rule — `h = min` over targets, stop at the first target
popped — is not sufficient, and neither is the variant used here. A* orders by
`g + h`, so two copies of one junction are compared on `g + h` and not on `g`;
their bounds differ, so the costlier copy can pop first. Measured before the
fix: junction 669074 returned a copy costing 111.1124 min ahead of one costing
111.0289, on a 3e-5 min lead in `f`. **Clamp the bound at zero.** It restores
`h(t) = 0` for every target, which is the actual precondition for stopping at
the first pop, and it changes nothing else — 7 nodes of 801,719 had a negative
bound. This is the one defect that reached a route; nothing else did.

**2. Trap 7's slack of 1e-6 minutes is ~60x too small.** The error is two
float32 roundings of an 813-minute quantity plus one of the subtraction: about
1.5e-4 min. Measured worst overshoot before clamping, over five full-graph
passes: 6e-5 min. `ALT_SLACK_MIN` is 1e-3.

**3. The min over a target set does not cost a pass per target.** Trap 1 asks
for `min_t max_L b_L(n,t)`; `max_L min_t b_L(n,t)` is smaller, is still a bound
on the distance to the nearest target, and folds both mins into per-landmark
constants — so any number of targets costs one pass. The copies of a junction
stand in the same place, so the weakening is not measurable.

**4. The tail regresses, and needs a stop-loss.** The brief costs the win and
not the loss. On a destination in the far corner of the region the A* settles
most of the graph through a Python heap and finishes *slower* than scipy's C;
on a destination no road reaches it settles all of it. Over uniformly random OD
pairs, 24 of 250 came out slower, the worst at 2x. `ALT_SETTLE_FRACTION` caps
it: A* gives up at 20% of the graph — measured break-even is 16-23% — and hands
the query to the Dijkstra. It fired on 22 of 250 random pairs and on 0 of 250
realistic ones, the budget counter costs nothing measurable, and the slowest
new arm (630 ms) is below the slowest old one (787 ms).

## What the search is not

45.8 ms of arm is ~24 ms of search and bound and ~22 ms of array work that both
arms pay: `_edge_scores` 4.3 ms, `_weights` 10.1 ms, the parallel-edge collapse
7.6 ms. At `pref = 0` the scenery term is multiplied by zero and the collapse
depends only on `avoid_unpaved`, so most of that 22 ms is recomputing a
constant. Not touched here — it is a different change, and it is now the
larger half of the arm.
