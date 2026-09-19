# A\* on the fastest arm: ALT landmarks over the time metric

**Status: measured 2026-09-19, nothing built.** No file under `pipeline/`,
`server/`, `ios/` or `tests/` has been touched. Every number below comes from
scratch scripts outside the repository that load one `Router` and work on its
arrays — the `pipeline/scenery_cap_experiment.py` pattern. A working Python A\*
exists only in that scratch script; it is not in the tree.

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
