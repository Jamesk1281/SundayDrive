# Route options: in-between scenic routes on the slider — brief

**Status: diagnosed, decided, measured offline, not built.** Nothing in
`server/`, `pipeline/` or `ios/` has been touched. The study that settled the
method lives beside this file, untracked, in `docs/route-options-study/`
(scripts plus raw results); copy it into your branch with this brief. The
answer goes in a new **`docs/route-options.md`** (what was built, the
measurements, the capacity table). This brief is deleted in the merge that
brings the work back, so nothing — source comments, tests, docs — may cite
it; cite `docs/route-options.md`.

Every `file:line` below is against `main` at `f99c22e`.

---

## 1. The goal, as measured

**The owner's drive, Waitsfield VT → Needham MA, 2026-10-06.** Fastest route
181 min. With today's slider, handle position 0.05 gives **+16 min** and 30
more beautiful miles; position 0.10 gives **+112 min**. Nothing in between can
be reached. The owner's words: "its either a 5 minute increase or a two hour
increase with a tiny slide of the bar". They want in-between routes ("half on
Vermont 100 and half on I-89"), because two extra hours is usually not a
pleasant option.

**Across New England.** 60 trips drawn with `tools/route_census.py`'s
`sample_pairs` (OSM place nodes, seed `20261007`, five great-circle bands
10–25 / 25–50 / 50–100 / 100–200 / 200–350 km); 44 have a scenic detour of
at least 10 min and a gain of at least 1 beautiful mile. Today's slider was
computed **exactly**: the full lower envelope of routes over strength 0..1,
with the slider interval each route owns.

| method | largest gap in extra time (median, share of full detour) | trips with a gap ≥ half | ≥ a third | scenery bought with a quarter of the extra time | with half of it |
|---|---|---|---|---|---|
| today, routes owning ≥ 2% of the track | 0.55 | 27/44 | 37/44 | 0.02 | 0.15 |
| today, every envelope route (ceiling for any remap) | 0.34 | — | — | — | 0.32 |
| best slider remap tried (p^1.5…p^3, exponential) | 0.51 | 23/44 | — | — | 0.23 |
| 4–8 of today's routes sent together | 0.52–0.75 | 24–44/44 | — | — | 0.00–0.23 |
| detour limit (slack mask), 9 budgets | 0.66 | 36/44 | 44/44 | 0.05 | 0.13 |
| **splicing, one base (what to build)** | **0.25** | **3/44** | **10/44** | **0.28** | **0.55** |
| splicing, eight bases | 0.24 | 2/44 | 11/44 | 0.29 | 0.58 |

"Scenery" is the beautiful-km gain over the fastest route as a share of the
full scenic route's gain. A gap is measured over the **menu** (§3, step 6).
One base loses noticeably (> 0.15 of the gain at half budget) on 2 of 44
trips; a second base (pref 0.5) buys 0.02 and is not worth its search.

Waitsfield → Needham with one base: **+16 min / 30 mi** (VT-100 → VT-107 →
I-89), **+44 min / 51 mi** (VT-100 to Killington, US-4 through Woodstock,
I-89), +63, +98, +106, +117 (86 mi), +135, +142, +172, full **+181 / 109 mi**.

Residual gaps are mostly geography, and correct: trip 35 (~Freedom NH →
~Warren NH) is +6 min or +35 min for 59 km, with nothing sensible between
(probably the Kancamagus; roads not checked).

## 2. The mechanism

The router minimises, per directed edge (`pipeline/router.py:1649-1650`):

```python
strength = max(0.0, min(1.0, pref)) ** PREF_CURVE
w = self.d_minutes + strength * BETA * penalty[self.eidx]
```

so a route's cost is `c0 + s·c1`, a straight line in strength `s`, and the
slider can only ever return routes on the lower envelope of those lines. Two
facts follow, both measured:

- **The envelope's middle routes own slivers.** On the median trip only 8.6% of
  the track returns a route in the middle half of the detour; the detour has
  passed 50% of its maximum by position 0.17. Why: the break-even strength of a
  detour depends on per-km rates (min/km against penalty/km) of the road types,
  not on the detour's size, so a 5-minute swap and a 2-hour corridor flip at
  nearly the same `s`.
- **Many in-between routes are on no envelope at all.** "VT-100 then I-89" is
  never optimal at any `s`: it lies above the line joining the fastest route
  and the full scenic one. No `BETA`, `PREF_CURVE` or handle mapping reaches it.

The handle position *is* strength today: `PrefSlider.pref(atPosition:)` returns
`sqrt(position)` (`ios/Sources/PrefSlider.swift:50`), squared again by
`PREF_CURVE = 2.0` (`pipeline/router.py:225`). The route recomputes on release
(`ios/Sources/DirectionsView.swift:169`), one full request per release.

## 3. The fix, decided

**Splicing off one base.** Reference implementation: `splice()` in
`docs/route-options-study/splice_single.py` (prototype quality: Python per-hop
loops, no API).

1. `F` = fastest route, `S` = scenic route at **pref 1**, as node paths over
   the *expanded* graph (turn-restriction copies, `node_copies`,
   `pipeline/router.py:1030`). All weights from `Router._weights(...,
   avoid_unpaved, on=day)`, so closures and closed-to-cars stay infinite.
2. One forward pref-0 Dijkstra from the start and one reverse pref-0 Dijkstra
   (transposed CSR, `indices=targets, min_only=True`) into the destination,
   both with **`limit = the pref-0 cost of S`**. That cap is exact: every
   prefix and suffix of `S` is a path, so no tree distance a candidate uses can
   exceed it. It makes the trees nearly free on short trips (§5).
3. The forward tree also yields the fastest route — reuse it instead of the A\*
   arm (`pipeline/router.py:2001`).
4. Switch points on `S` every `max(0.5 km, len(S)/250)`.
5. For every pair `i < j`: `fastest(start → S[i]) + S[i:j] + fastest(S[j] →
   dest)`. Minutes, km and beautiful km per candidate are O(1) from cumulative
   arrays along `S` and per-node values along the trees.
6. Pareto frontier on (extra minutes, beautiful km), beautiful = edges scoring
   ≥ `BEAUTIFUL_SCORE` (7.0, `pipeline/router.py:308`) under the request's
   beauty weights. Check simplicity (no `real_node` repeated) on frontier points
   only, drop failures, recompute the frontier until stable. Then the **menu**:
   keep a frontier point only if it adds ≥ max(1 mi, 5% of the full gain) over
   the last kept one; always keep the fastest and the full scenic route.

**The owner's decisions (2026-10-07):**

- **Options come with every plan**, in the `/api/route` response — not lazily
  on first slider touch.
- **The route shown first** is the most scenic menu option whose extra time is
  at most **25% of the fastest time** (Waitsfield → Needham opens on +44 min).
- **Every menu option is a detent** (about 12 on a long trip), because the
  extra server cost is small (+0.06 s median, §5). Detents evenly spaced by
  index, so each one is reachable; the readout shows each one's price live
  while dragging.

**Shape of the response (suggested; refine it, keep it backward compatible).**
Old clients must keep getting `fastest` and `scenic` exactly as today. Add
`options`: one entry per menu option with minutes, km, beautiful km, extra
minutes, its switch points (`null` for the two ends), a **simplified line**
(≈20 m tolerance, ~15 KB) for drawing, and which one is the default. `scenic`
becomes the default option in full detail. Full detail for any other option is
fetched when the user settles on it, by its switch points.

**Rerouting must keep the plan.** `NavigationModel.reroute`
(`ios/Sources/NavigationModel.swift:1784`) re-asks by `pref` and takes
`response.scenic` unless `pref == 0` (`:1788`, `:1874`). A spliced plan would
be thrown away at the first missed turn. Reroute by legs instead: before the
first switch point, fastest to it, then the scenic stretch, then fastest home;
on the scenic stretch, scenic to its end, then fastest; after it, fastest. The
request carries the switch points. Read `docs/mid-drive-recovery.md` first:
that work merged on 2026-10-07 and owns this function's guards.

Record the chosen option's switch points in the `DriveTrace` header next to
`pref` (recording is on in Debug builds since `83fe53a`).

## 4. Why capacity was checked, and what was found

The owner asked whether this will become a problem on the Oracle box under any
decent traffic. The box is one waitress process (`server/serve.py:44`); routing
holds the GIL, so requests run one at a time (`server/serve.py:9-15`). On the
box, Boston → Augusta measures 0.65 s warm against ~0.47 s on the Mac
(`server/DEPLOY-oracle.md:743`), so box ≈ Mac × 1.38.

Per planning request on the box (Mac medians × 1.38, 59 trips; the 200–350 km
row ran under load):

| band | today | with options | ratio |
|---|---|---|---|
| 10–25 km | 0.38 s | 0.45 s | 1.17 |
| 25–50 km | 0.38 s | 0.53 s | 1.37 |
| 50–100 km | 0.42 s | 0.96 s | 2.00 |
| 100–200 km | 0.48 s | 1.17 s | 2.28 |
| 200–350 km | ~1.0 s | ~1.7 s (p90 2.8 s) | ~2.1 |
| all | 0.42 s | 0.94 s | 1.74 |

Components (Mac, median): the two capped trees 0.02 s (10–25 km) to 0.66 s
(200–350 km), uncapped ~0.47 s everywhere; splicing 0.04 s (p90 ≈ 0.26 s);
building one option's output 0.003–0.017 s.

- **Steady traffic: not the problem.** At 0.94 s per plan, half the box's CPU
  is ~1,900 plans in a peak hour — roughly 8,000 daily users at 1.5 plans
  each with 15% of them in the peak hour. Slider moves become free (today each
  release is a full request), so the change breaks even at about one release
  per plan.
- **Bursts are the problem, and it is an existing one.** The client gives up
  after 20 s (`ios/Sources/RouteService.swift:95`) and reports a timeout as the
  user's network (`:277`). The queue the box can absorb before that falls from
  ~47 plans to ~21. That is review finding K-1
  (`docs/pre-submission-review-verdict.md`, "K-1"), made about twice as easy to
  hit, so the guards in §6 Trap 3 are part of this change, not follow-ups.
- **Memory:** a few n-sized arrays per request (~20 MB transient) and a cached
  transposed pref-0 CSR per (closure version, `avoid_unpaved`), tens of MB each.
  The box peaks at 4.06 GB of 8 GB.

## 5. Collisions

- `pipeline/router.py` is touched by two unmerged branches
  (`claude/angry-thompson-a7c7c4`, state road classes; and
  `claude/drive-traces-access-6441d5`). Put the splicing in a **new module**
  (e.g. `pipeline/options.py`) and keep `router.py` edits to small helpers.
- `server/app.py`: the loop and `via` paths share `LOOP_LOCK`
  (`server/app.py:132`, `:328`, `:423`, `:474`). Don't change them; add beside.
- `ios/Sources/NavigationModel.swift` just took the mid-drive recovery build
  (`c97b126`). Branch from current `main`.

## 6. Traps

1. **Don't retune the cost function or remap the slider.** It looks like a
   one-line fix, and it was measured: the best curve moves the median gap
   0.55 → 0.51. Sending several of today's routes at once is *worse* (0.52–0.75).
   The in-between routes aren't on the envelope at all.
2. **Don't "improve" splicing into a detour-limit search** (mask junctions
   whose slack `df + db − F` exceeds the budget, search inside). Measured:
   worse than splicing on 41/44 trips at half budget; 225 of 396 options still
   > 10% over budget after two tightenings, because a per-junction limit
   doesn't cap the total and a pref-1 search weaves through every scenic road it
   is allowed (one 86-min budget came back +166 min). It is not cheaper either.
3. **Options must never make a driver wait.** Never compute them under
   `LOOP_LOCK`, never for a reroute or "switch to fastest", and skip them (and
   send today's response with `options` absent) whenever another plan or loop is
   already computing. Put options behind a server flag, off by default, so the
   owner can turn them on after measuring on the box (they deploy; you don't).
4. **Don't ship full geometry for every option.** One full route is 145–280 KB
   (6,863 coordinates and 43 steps for the +44 min Waitsfield option); twelve is
   ~2.5 MB per plan. Send simplified lines and fetch detail on selection.
5. **Don't make an option's detail depend on a server-side cache.** The plan is
   two tunnel connectors (laptop and Oracle), so the follow-up request can land
   on the other box. A cache is fine as an optimisation; the switch points must
   be enough to rebuild the option anywhere.
6. **Switch points are not node ids.** Ids change with every rebuild and
   deploy. And a lat/lon snapped back onto the graph can land on the wrong road
   at a junction — this project's destinations already snap behind buildings.
   Place each switch point on the scenic road just past its junction, snap it
   with the road's heading, and test that a rebuilt option equals the planned
   one.
7. **Tree distances are not minutes.** Pref-0 weights include the dirt-road
   avoidance (`UNPAVED_AVOID_MIN_PER_KM`), so `dist` overstates time on dirt.
   Accumulate `d_minutes` along the tree for the minutes you report.
8. **Keep `pref == 0` exact.** It means "fastest" in `server/app.py:330`/`:365`,
   in `NavigationModel` (`:1788`) and in `switchToFastest`; the fastest detent
   must still send exactly 0.
9. **Keep `_no_worse_than_fastest`** (`server/app.py:233`): pref 1 can return a
   route that scores lower than the fastest one. An option that adds time
   without adding beautiful km must not survive the menu.
10. **Splice on expanded indices, test simplicity on real nodes.** Joining at a
    turn-restriction copy keeps the turn legal; comparing copies instead of
    `real_node` misses U-turn loops (the prototype rejected a median of 713
    candidates per trip as non-simple).
11. **Timing on this Mac lies when other sessions run.** Report ratios to a
    plain scenic search timed in the same loop, as the study does. Use a free
    port for any local server, and stop only your own server by PID.

## 7. Done looks like

1. `/api/route` returns `options` behind a flag, backward compatible, with
   backend tests: Waitsfield → Needham includes a ~+16 and a ~+44 min option
   (or a note in `docs/route-options.md` of what a graph change moved);
   menu extra time and gain strictly increase; the default rule holds; no
   option repeats a junction; closures respected; the busy guard sends no
   options; old fields unchanged.
2. The 60-trip study re-run through the real endpoint code reproduces the
   one-base row in §1 within noise, and the capacity table in §4 is re-measured
   as ratios, both written into `docs/route-options.md`.
3. The app: detents for every option, a live price while dragging, the map
   redrawn on release, the default opening option, and a caption saying where
   the route leaves and rejoins the scenic road; today's behaviour when
   `options` is absent.
4. Rerouting keeps a spliced plan, with tests for before, on and after the
   scenic stretch; "switch to fastest" unchanged.
5. `docs/route-options.md` written; the brief left for the merge to delete
   (`docs/briefs.md` has the procedure).
6. Or, for any part that can't be done as specified, a statement in
   `docs/route-options.md` of why, with the measurement.

## 8. Reproducing the study

The graph is gitignored and lives in the main checkout:
`/Users/james./Desktop/myapps/SundayDrive/data/processed-ne`. Each script
takes `<worktree> <processed dir> <out dir> [per band]`; the graph load is
~40 s. `splice_batch.py` → today's exact envelope plus 8-base splicing;
`splice_single.py` → the one-base production shape; `ellipse_batch.py` → the
detour limit; `cost_probe.py` → per-request cost; `analyze_batch.py`,
`compare.py`, `compare_single.py` (expects `batch60/`, `single60/` in the
working directory) and `remap_eval.py` score them. Raw results are in
`results/`.
