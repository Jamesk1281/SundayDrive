# Loop speed: stop searching all of New England for a 40 km loop — brief

**Status: diagnosed, not fixed.** Nothing in `pipeline/`, `server/` or `ios/`
has been touched. The answer goes in a new **`docs/loop-speed.md`** (what was
built, the before/after measurements, the exactness check). This brief is
deleted in the merge that brings the work back, so nothing — source comments,
tests, docs — may cite it; cite `docs/loop-speed.md`.

Every `file:line` is against `main` at `722132b`. The timing script used below
is beside this brief at `docs/loop-speed-study/loop_time.py`.

---

## 1. The goal, as measured

The owner noticed loops are slow. Measured on the live box (2026-10-08, public
URL, warm server):

| request | time on the box |
|---|---|
| first 40 km loop from a new start (Needham, Stowe, Woodstock VT) | 3.8–4.2 s |
| same start, 60 km | 2.5–2.6 s |
| exact repeat | 0.1–0.2 s (whole-response cache) |
| a point-to-point route, Boston → Worcester, for comparison | 0.77 s |

**Nothing recent made them slower.** The same three loops were timed in units of
one plain pref-1 full-graph Dijkstra (same process, so machine load cancels) at
`121f1a5`, `0315918` (state road classes), `012a5f3` (route options) and
`eba9564` (K-1): every commit gives **~9.3 units for a first loop and ~5.6 for
a new distance**. The box recorded 3.9 s for the first 40 km loop on the day it
went live (`server/DEPLOY-oracle.md:745`). The "1.2 s / 0.65 s" in
`ios/Sources/RouteService.swift:241` is from 2026-08-28, on the
Massachusetts-only graph.

**Where the time goes** (cProfile, Mac, Needham 40 km then 60 km; one unit =
0.22 s):

- `_fields` → two `_pass` calls (`pipeline/looper.py:623`, `:646`): out and
  back over **the whole graph**, plus `_accumulate` over all ~800k nodes.
  0.40 s each, **~3.6 units together**, once per (start, pref, weights,
  avoid, closures); cached across distance changes.
- `_build` (`:535`), called `SPAN_PICKS = 5` times per `plan` (`:411-414`):
  each is a full-graph Dijkstra **home** from the candidate turnaround, under
  weights with the outbound roads penalised ×3. 0.225 s each, **~1 unit each,
  ~5 units per loop**. Four of the five built loops are thrown away
  (`:422`, kept on distance error).

So a 40 km loop pays for 7 searches of all of New England. A route menu
(`pipeline/options.py`) pays for ~2.3 units because its two extra trees are
capped (`limit=`) at the scenic route's cost, which on trips under 50 km
settles ~1–5% of the graph (0.47 s → 0.02 s).

## 2. The mechanism, and the two caps

### 2a. The home leg in `_build` — exact, do this first

`pipeline/looper.py:566-568`:

```python
g = csr_matrix((pair_w, (r.u_tail, r.u_head)), shape=(r.n, r.n))
dist, pred = dijkstra(g, directed=True, indices=turnaround,
                      return_predecessors=True)
```

No `limit`. But an upper bound on the answer is already in hand: the back
field's tree path from the turnaround home (`fields.back.pred`, built in
`_pass(reverse=True)`) is a legal path to one of `_arrival_indices(start)`. Its
cost **under the penalised `pair_w` of this build** bounds the cheapest
penalised way home, so `limit = that cost (+ a hair)` cannot change the result.
Same argument as `options.py`'s capped trees. The home leg of a 40 km loop is
~20 km, so this search should settle a small fraction of the graph.

Compute the bound by summing the penalised per-pair weights along the back
tree path (`_tree_path` on `fields.back.pred` gives turnaround → home on the
original direction; check the direction carefully — the back pass runs on the
transposed graph, `:658-663`, and its `pred[v]` is the next node *after* v on
the way home).

Second-order, once the search is cheap: the per-build fixed cost
(`w_slot.copy()` `:554`, `np.isin` over all slots `:559`, `np.minimum.at` over
all slots `:564`, a fresh `csr_matrix` `:566`) will start to dominate. Copying
`pair_w` and recomputing only the pairs the outbound path touches is the
obvious reduction. Measure before and after.

### 2b. The two field passes — exact with a fallback

`:660-667`: forward and reverse full-graph passes, no `limit`. What the loop
actually needs from them is every **candidate turnaround**: a node whose
`loop_km` (`fields.out.km + fields.back.km`, `:290`) is within
`CANDIDATE_TOLERANCE` (10 %) of the target (`candidates`, `:356`). Let
`K = target × 1.1`. A candidate's out and back tree paths each have length
≤ K, so **both lie within a disc of radius K around the start** (a path of
length ≤ K cannot leave it).

Proposed exact method (prove it, or replace it with one you can prove):

1. Run each pass on the subgraph induced by nodes within Euclidean distance
   `K` (+ a small margin) of the start.
2. Inside the subgraph, a node's distance is exact whenever it is no larger
   than `D_b`: the cheapest cost of leaving the disc (min over edges from a
   settled inside node to an outside node of `dist(inside) + w(edge)`). Any
   path through the outside costs at least `D_b`, so it cannot beat an inside
   distance ≤ `D_b`.
3. If every node that would be a candidate has distance ≤ `D_b` in both
   passes, the candidates (and their tree paths) are exactly today's. If any
   does not, **fall back to today's full pass** for that start. Measure how
   often the fallback fires.

The cheaper `limit`-on-cost formulation does **not** work on its own (Trap 2).

## 3. Collisions

- **`pipeline/looper.py` is also targeted by the neighbourhood-streets work**
  (chip task_b0cc6add, brief untracked in worktree
  `residential-side-streets-rating-9086b9`): it extends the private-road guards
  at `:365-371` (`candidates`) and `:554-562` (`retraced` in `_build`). It had
  no commits when this was written. **Do not edit those lines.** Confine your
  edits to the Dijkstra calls in `_pass`, `_build` and (if you get there)
  `_leg`, plus new helpers, so whichever lands second merges cleanly.
- `server/app.py`'s loop path (`LOOP_LOCK` `:155`, `LOOP_BUSY_WAIT_S = 5.0`
  `:176`, the K-1 busy guard `:226`, `:652-658`) — do not change it. Note in
  `docs/loop-speed.md` that `LOOP_BUSY_WAIT_S = 5.0` was sized for a cold loop
  p90 of ~4.3 s on the box, so the owner can revisit it once loops are fast.

## 4. Traps

1. **Loops must come out identical.** Same turnaround, same node path, same km
   and score, for every start, target and sector you test. This is a speed
   change, not a quality change: do not touch `PENALTY`, `SPAN_PICKS`,
   `CANDIDATE_TOLERANCE`, the candidate ranking, `_spread` or `_miss`, and do
   not "save" builds by building fewer than `SPAN_PICKS` (measured in the
   module docstring: 1 pick is +21 % distance error).
2. **A cost `limit` on the field passes is not exact.** Candidates are filtered
   on *km*, the search is ordered by *cost*, and cost per km is unbounded per
   edge (control seconds on a 10 m edge, dirt-road avoidance, closures). A
   node 15 km out by a slow scenic road can cost more than one 80 km out by
   motorway. Any field cap must be justified in km and space (§2b), or fall
   back.
3. **The field cache is reused across distance changes** (`_fields` key, `:630`,
   has no target), and the app relies on that: moving the distance slider must
   not re-run the two passes. If the disc depends on the target, key or reuse
   accordingly (a field built for radius K serves any target with
   `target × 1.1 ≤ K`), and measure the slider-move case separately.
4. **Unreached nodes.** With `limit=` or a subgraph, unsettled nodes come back
   `inf` / pred `-9999`. `_pass` treats `pred < 0` as unseen (`:670`) and
   `_accumulate` leaves them at 0 km — make sure that can never make an
   unreached node look like a candidate (`loop_km` 0 is outside every band
   today, but check it stays so), and that `sectors()` (`:330`) counts are
   unchanged.
5. **`nearest_length`** (`:490`) scans every reachable length to suggest one
   when a request has no loop. With capped fields it can only see inside the
   disc. It runs only on the failure path; give it the full pass there rather
   than a wrong hint.
6. **Turn-restriction copies and split junctions.** The back pass is
   multi-sourced over `_arrival_indices(start)` (`:661`); the home leg arrives
   at any of them (`:576-580`). Subgraph construction must keep every copy of
   every inside junction (copies share coordinates with their real node,
   `router.real_node`), or the copies vanish and turns change.
7. **Timing on this Mac lies when other sessions run.** Report times as ratios
   to a plain pref-1 full-graph Dijkstra timed in the same process, as
   `docs/loop-speed-study/loop_time.py` does. Never pipe a probe through `tail`.
   Use a free port other than 5057 for any local server and stop only your own
   server by PID.

## 5. Done looks like

1. The home-leg cap (§2a), with a test that its loops equal today's.
2. The field-pass cap (§2b) with its fallback, or a measured statement in
   `docs/loop-speed.md` of why it isn't exact or isn't worth it.
3. An exactness check over a stratified sample: at least 30 starts (town,
   rural, coast, dead end, Maine woods, a private-road start, island/peninsula)
   × targets 10, 25, 40, 80, 150 and 300 km × default sector plus two compass
   sectors, comparing old and new `LoopPlanner.plan` output node for node, plus
   `sectors()` counts and `nearest_length` on a failing request. Zero
   differences, or each one explained.
4. Before/after in search units for: first loop from a start, new distance,
   compass change, rejoin (`resume`, if touched), and the share of fields that
   took the fallback. Converted to box seconds with the box's measured
   3.9 s ≈ 9.3 units for a first loop.
5. Backend suite green (record the count at your base commit first); the docs'
   stale numbers updated where you measured new ones (the looper module
   docstring, `ios/Sources/RouteService.swift:241`).
6. `docs/loop-speed.md` written; this brief left for the merge to delete.
