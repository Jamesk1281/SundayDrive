# Loop speed: searching the part of New England a loop can reach

**Status: merged into `main` 2026-10-08 (`_home_bound`, `_disc`, `_refine`
and `_serves` in `pipeline/looper.py`), built off `722132b`, and deployed the
same day (box at `1c55ead`; measured there in §4).** Loops come out identical, node for node,
to `722132b`'s on every request checked (§3).

A loop from a new start used to cost ~9.3 searches of the whole New England
graph (about 4 s on the Oracle box), and a new distance ~5.6 (2.5 s). Nothing
had regressed: it was 3.9 s the day the box went live. The time was two
uncapped field passes in `pipeline/looper.py` `_pass` (~3.6 searches between
them) and five uncapped Dijkstras home in `_build`, one per candidate loop.
Both are now capped, exactly:

| | before | after |
|---|---|---|
| first 40 km loop from a new start | 9.5 | **0.89** |
| new distance, 40 → 60 km | 5.9 | **1.01** |
| new distance, 60 → 25 km | 5.7 | **0.62** |
| compass change | 5.1 | **0.57** |
| rejoin (`resume`) | 2.2 | 2.1 |

Medians over twelve starts, in units of one plain pref-1 whole-graph Dijkstra
timed in the same process (§4 has the full table, the method and box seconds).

## 1. What was built

### 1a. The home leg: `limit=` at a cost already in hand

`_build`'s search home from a turnaround now passes `limit=` the cost, under
this build's penalised weights, of the back field's own tree path from the
turnaround home (`_home_bound`). That path is a legal drive to one of the
start's arrival indices, so the cheapest penalised way home costs no more,
and every node on the way to it is settled. The answer cannot change. The
bound is summed in a different order from Dijkstra's running total, so it is
padded by 1e-9 relative, far more than either sum's rounding.

In every build inspected (Needham at 40 km, Boston at 150 km) the bound was
the back field's own cost: the retrace penalty rarely touches the back
field's way home. A 40 km loop's search home then settles ~5% of the graph
instead of all of it, ~0.25 of a whole-graph search per build against ~1.1. At 150 km and up the home leg is long enough that the
bound covers most of the graph and the cap buys little.

All three matrices the module builds from per-pair weights for a forward
search (`_build`, `_leg`, the forward pass) now come from `_graph`, which hands
scipy the pairs' existing CSR order (`Router._pair_indptr`) instead of a COO
sort: 0.013 of a search against 0.062, and the same matrix, neighbour order
included (tested: `tests/test_loop_speed.py`).

### 1b. The field passes: a disc, a proof, and a fallback

**The disc.** A candidate turnaround has `out.km + back.km` within 10% of the
target, so each leg is at most `K = target x 1.1` km of road. No road is
shorter than the great circle between its ends by more than 0.09% (measured
over all 1,891,805 directed slots; the test allows `DISC_SLACK / 2` = 0.5%),
so both of a candidate's tree paths lie within `K x 1.01` of the start. `_disc`
cuts out every node within that radius (copies of a split junction share
their real node's coordinates, so they are in or out together) and builds the
forward and transposed matrices over the pairs with both ends inside, in the
whole graph's neighbour order. `_pass` searches that, accumulates km and
scenic-km over the disc only, and spreads the result back over the whole
graph's indices: unreached outside, `pred = -9999`, cost infinite.

**Why the disc gets every real candidate.** A whole-graph candidate's out and
back paths lie inside the disc, so the disc search finds them at the same cost.
That is one direction of exactness. The other is the trap: a node inside the
disc whose cheapest *whole-graph* path leaves the disc gets a dearer path
inside it, with different km, and could look like a candidate when it is not.
A cost `limit=` cannot rule that out, because candidates are chosen on km and
the search runs on cost.

**The proof (`_Field.exact`).** Let `leave` be the cheapest way out of the disc:
the minimum over arcs from a reached inside node to an outside node of
`cost(inside) + w(arc)` (for the back pass, over arcs entering the disc). Any
path that leaves costs at least `leave`, so a node costing less inside the
disc has the whole graph's cost and the whole graph's shortest paths. That is
`exact = cost < leave`, free.

It is not enough on its own. **A few candidates cost 10,000 minutes or more**,
because their way out turns onto a private road from the main network
(`router.PRIVATE_ENTRY_MIN`): at Stowe 10 km, 2 of 63 candidates (the
dearer at 10,026 against a median of 17); at Needham 80 km, 5 of 25,762. One such node
outprices every way out of any disc, and the simple test then fails for
almost every start (3 of the first 4 tried fell back). `_refine` adds the
second half of the argument: a path that leaves and comes back also has to
re-enter, so it costs at least `leave` plus the cheapest way, inside the disc,
from an arc entering it to the node. That second term for every node is one
multi-source search over the disc, seeded through a virtual node at the
entering arcs (on the back pass, the arcs leaving it, on the transpose). A
node costing less than the sum is proved. It runs only when a candidate is
left unproved, on both passes, since the disc is not kept for later targets.

**`_serves`.** A cut field set answers a target when the target fits its
reach (`target x 1.1 <= reach_km`) and every candidate it reports is proved in
both passes. Then its candidate set, each candidate's cost, km, scenic-km and
tree path, `sectors()` counts and every loop built from it are the whole
graph's. Otherwise `_fields` falls back to two whole-graph passes.

**The cache (brief trap 3).** The target is still not in the field cache key.
A cut field set serves every shorter target it can prove, so moving the slider
down reuses it; a longer target cuts a wider disc and replaces it. A whole-graph
set serves everything. `nearest_length`, which looks for any length that
works and so cannot be answered from inside a disc, asks for the whole graph.
It runs only after `plan` returned None.

**Two measured settings.**
- *No headroom.* A disc cut wider than the target (×1.25, ×1.5) would let the
  next notch up the slider reuse it, but over twelve starts it cost every first
  loop more than it saved the next distance (median first loop 0.87 → 0.96
  searches at ×1.5, 40 → 60 km 1.00 → 0.78). First loops are the slow case the
  owner noticed, so the disc is cut for exactly the target.
- *`DISC_MAX_SHARE = 0.6`.* A disc holding more than 60% of the graph is not
  cut: with `_refine`, it costs more than the whole graph. At 300 km the
  twelve starts' median was 4.8 searches with the cap at 0.6, 8.0 at 0.8 and
  10.0 with none.

## 2. What was not changed

- `PENALTY`, `SPAN_PICKS`, `CANDIDATE_TOLERANCE`, the candidate ranking,
  `_spread`, `_miss`: untouched. Every request still builds `SPAN_PICKS` loops.
- The private-road guard in `candidates` and the `retraced` lines in `_build`,
  which the neighbourhood-streets work (chip task_b0cc6add) edits. The edits
  here are three unchanged lines away from them, so either can merge first.
- **The per-build fixed costs.** Once the search home is capped, each build
  still pays `w_slot.copy()`, `np.isin` over every slot and `np.minimum.at`
  over every slot (together ~0.05 of a search) plus scipy's own O(n) setup
  (~0.025 of a search, measured with `limit=0`). Copying `pair_w` and
  re-collapsing only the pairs the outbound path touches would remove the
  first three, but it rewrites the `retraced` lines. Worth doing after the
  neighbourhood-streets work lands: ~0.25 searches a loop.
- **A\* home** (the router's ALT tables bound the penalised weights too) would
  settle less than a capped Dijkstra, but it breaks ties between equal-cost
  paths differently, so loops would not come out identical. Not tried.
- `server/app.py`'s loop lock and busy wait. **`LOOP_BUSY_WAIT_S = 5.0` was
  sized for a cold loop p90 of ~4.3 s on the box** (docs/loop-lock-contention.md);
  with first loops now ~0.4 (0.8 at worst around Boston) s there, the owner may want to revisit it.
- `resume` (rejoin) keeps its two whole-graph searches. It only gains the
  cheaper matrix build (§4). Neither leg has a bound in hand: the driver is
  off the route.

## 3. Exactness check

`docs/loop-speed-study/exactness.py` runs `722132b`'s `looper.py` and this one
side by side over one `Router`, and compares, for every start x target x
sector:

- `plan`: turnaround, node path, edge ids, km, minutes, mean score, repeated
  and beautiful km, sector and target, compared with `==` (no tolerance);
- `sectors()` counts;
- the candidate set, and each candidate's out and back cost, km, scenic-km and
  predecessor;
- `nearest_length` wherever the old planner returned no loop.

Sample: 39 starts — nine towns, eight rural, four coastal, five in the
Maine woods, nine islands and peninsulas (Bar Harbor, Edgartown, Nantucket,
Deer Isle, Grand Isle, Newport, Provincetown, Nahant, Cape Elizabeth), two
dead ends and two junctions on private road chosen by a fixed seed — x
targets 40, 10, 80, 25, 150 and 300 km in that order (so cached discs are
reused down the slider as well as cut fresh) x the default sector and two
compass sectors (the most and least populated offered, or N and S where fewer
than two are offered, which exercises refusals). The new planner's cache is
cleared between starts, so each start's first target is a first loop.

**Result: zero differences.** 234 (start, target) cells, 702 plans, 3.27
million candidate turnarounds compared field by field, every `sectors()`
dict, and 17 refused requests (all of them compass directions too thin to
offer, since no unsectored request in the sample fails) whose
`nearest_length` hints matched. The run cut 90 field sets to a disc; 52 of
them needed `_refine` and 3 still fell back to the whole graph. An earlier
run with 300 km before 150 km (so every 150 km cell reused the 300 km
whole-graph set, and no 150 km disc was tested) also gave zero differences
over its 234 cells, with 72 discs, 36 refined and 3 fallbacks.

Wall time for the same 702 plans and 234 `sectors()` calls: 830 s old, 266 s
new.

**What "identical" rests on.** The proof in §1b makes every candidate's cost,
and its set of shortest paths, the whole graph's. Which of two exactly
equal-cost paths a search keeps depends on scipy's heap order, and a smaller
graph or a `limit=` could in principle keep the other. The matrices are built
in the whole graph's neighbour order to keep that as close as it can be, and
the check above found no case where it differed.

## 4. Before and after

Searches per request; median (worst) over the twelve starts.

| request | `722132b` | this change |
|---|---|---|
| first loop, 40 km | 9.54 (10.05) | **0.89** (1.91) |
| new distance up, 40 → 60 km | 5.90 (6.34) | **1.01** (3.78) |
| new distance down, 60 → 25 km | 5.71 (6.12) | **0.62** (1.01) |
| compass change, 25 km | 5.05 (5.99) | **0.57** (0.91) |
| rejoin (`resume`) | 2.18 (2.40) | 2.10 (2.26) |
| first loop, 10 km | 9.58 (10.19) | **0.69** (0.87) |
| first loop, 80 km | 9.79 (10.09) | **1.74** (5.03) |
| first loop, 150 km | 9.76 (10.85) | **4.71** (7.36) |
| first loop, 300 km | 10.12 (10.35) | **8.40** (8.72) |

The slow end of each row is the dense south: Needham, Boston, Providence and
Hartford have the most junctions inside any given radius. Long loops gain
least, for two reasons. At 150 km and up, a disc around a southern start
holds more than 60% of the graph, so the passes run over all of it
(`DISC_MAX_SHARE`); northern starts like Stowe and Bar Harbor still get a disc
(1.6 and 1.1 searches at 150 km). And a 150 km
home leg is long enough that its bound settles most of the graph anyway:
builds at 300 km cost ~0.9 of a search each, against ~0.25 at 40 km.
"Longer" is the one move that cuts a new disc and pays `_refine` on it, which
is why it costs more than a first loop at the dense starts.

**Method.** `docs/loop-speed-study/units.py`, run at `722132b` (a `git archive`
of `pipeline/`) and at this change, on the same Mac in one sitting. Each
figure is a request's wall time divided by a plain pref-1 whole-graph Dijkstra
timed just before it in the same process, so load from other sessions cancels.
One planner for the whole run, warmed first, the way the server holds one.
"first" is `plan` + `sectors` at 40 km from a cleared field cache; "longer"
60 km after it; "shorter" 25 km after that; "compass" the same 25 km in the
least populated offered sector; "rejoin" `resume` from a tenth of the way
round, through the turnaround, home. Twelve starts: Needham, Boston, Stowe,
Woodstock, Petersham, Bar Harbor, Greenville, Hartford, Chatham, Jackson,
Providence, Portland.

**Through the app.** The brief's own probe, `docs/loop-speed-study/loop_time.py`
(Needham, Stowe and Woodstock through `/api/loop`, 40 km then 60 km):

| start | km | `722132b` | this change |
|---|---|---|---|
| Needham | 40 | 10.3 | 4.0 (one-time costs, below) |
| Needham | 60 | 5.6 | 3.5 |
| Stowe | 40 | 9.6 | **0.7** |
| Stowe | 60 | 5.7 | **0.8** |
| Woodstock | 40 | 9.2 | **0.7** |
| Woodstock | 60 | 5.8 | **0.9** |

Needham's first request through a fresh app also pays the process's one-time
costs: the cost model (~0.7 searches, in both columns) and, new here, the
pair order `_disc` sorts once per process (~0.6 searches, 7 MB, `_by_head`).

**Box seconds.** The box measured 3.9 s for a first 40 km loop the day it went
live, which is 9.3 units: ~0.42 s a unit. On that scale:

| request | `722132b` | this change |
|---|---|---|
| first 40 km loop | 4.0 s | **0.4 s** (0.8 s at worst) |
| new distance, 40 → 60 km | 2.5 s | **0.4 s** (1.6 s) |
| new distance down, or compass | 2.1–2.4 s | **0.25 s** |
| first 150 km loop | 4.1 s | 2.0 s |
| first 300 km loop | 4.3 s | 3.5 s |
| rejoin | 0.9 s | 0.9 s |

These are a scale, not a measurement on the box. **Measured on the box** after
deploying `1c55ead` (2026-10-08, `curl` POSTs to the public URL, so each time
includes ~0.2-0.3 s through Cloudflare; the brief's "before" was measured the
same way):

| request | before | after |
|---|---|---|
| first 40 km loop | 3.8-4.2 s | 0.48 s (Bar Harbor), 0.51 s (Woodstock), 1.0 s (Boston), 1.1 s (Needham; Stowe, the first request after the restart, also 1.1 s) |
| 40 → 60 km | 2.5-2.6 s | 0.55 s (Stowe), 0.62 s (Woodstock), 1.7 s (Needham) |
| 60 → 25 km | | 0.61 s (Needham) |
| first 150 km loop | | 3.3 s (Boston) |

**Fallback rate.** A disc that `_serves` cannot prove even after `_refine`
falls back to the whole graph: 3 of 90 disc field sets in the exactness run
(3.3%), 3 of 72 in its first run (4.2%), 2 of 58 in the units run (3.4%).
Separately from
fallbacks, a request is answered from the whole graph when its disc would hold
over 60% of it (most southern starts at 150 km and up) or after a refused
request has asked `nearest_length`.

**Memory.** Unchanged in shape: a cut field set is stored over the whole
graph's indices like a whole one, plus a boolean `exact` per pass (1.6 MB a
set). The disc itself is built per field set and dropped. The pair order is
7 MB, once.

## 5. Found along the way

**Some candidate turnarounds are reached by turning onto a private road.**
Their out cost carries `PRIVATE_ENTRY_MIN` (10,000 minutes): 2 of 63
candidates at Stowe 10 km, 4 of 779 at Woodstock 40 km, 5 of 25,762 at
Needham 80 km; none of them costs that on the way back. They are public-network junctions (so `private_inside` lets
them through) whose cheapest way *out* from the start enters private road,
while their way back is public. If `_spread` picks one, the loop's outbound
leg drives that private road. This change keeps them exactly as they were,
since it must not change loops; it is a question for the private-road guard
in `candidates`, which the neighbourhood-streets work is editing. A filter
such as `fields.out.cost < PRIVATE_ENTRY_MIN` would drop them, and would also
let `_serves` prove most discs without `_refine`.

## 6. Where the numbers in the code came from

- `looper.py` module docstring, `SPAN_PICKS`, `MAX_TARGET_KM`'s comment and
  `plan`'s docstring: the medians in §4.
- `DISC_SLACK`, `DISC_MAX_SHARE`, no headroom: §1b.
- `ios/Sources/RouteService.swift`, `loop(...)`'s doc comment: box seconds
  from §4.

## 7. Reproducing

```
git show 722132b:pipeline/looper.py > /tmp/looper_old.py
SUNDAYDRIVE_DATA=…/data/processed-ne python docs/loop-speed-study/exactness.py /tmp/looper_old.py …/data/processed-ne
git archive 722132b pipeline | tar -x -C /tmp/base
python docs/loop-speed-study/units.py /tmp/base …/data/processed-ne
python docs/loop-speed-study/units.py . …/data/processed-ne
python docs/loop-speed-study/loop_time.py <checkout> …/data/processed-ne
python docs/loop-speed-study/loop_profile.py      # cProfile of one start
SUNDAYDRIVE_DATA=…/data/processed-ne python -m pytest tests/test_loop_speed.py
```

`loop_time.py` and `loop_profile.py` are the diagnosis's scripts, unchanged.
