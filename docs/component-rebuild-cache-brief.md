# A per-column cache for score.py, so retuning a constant is not a rebuild

> **Answered in `docs/component-rebuild-cache-findings.md` (2026-09-19).**

**Status: measured 2026-09-19, nothing built.** No file under `pipeline/`,
`server/`, `ios/` or `tests/` has been touched. The timings below were taken by
a scratch script outside the repository that loads `scored_chunks.parquet` and
re-runs `score.near_flags` against the same layers `score.py` uses, on the live
New England build.

Companion to `docs/scenery-grading-verdict.md` (proposal **F2**), which
concluded "build now" — but **not for the reason the originating brief gave.**
That brief claimed `RouteResult.mean_score` falls back to a stale `score`
column; it does not (see *The staleness that is real*, below). Build this on the
corrected argument.

---

## The goal, as measured

`pipeline/score.py` recomputes all nine component columns on every run. Nothing
is reused. `docs/unpaved-and-urban-brief.md:152` prices a full New England score
rebuild at **~11 minutes**, plus **~6 minutes** for `graph.py`.

**Almost all of the score half is two spatial queries.** Every `near_flags`
`dwithin` call in `score.py`, timed on all 942,448 chunks:

| layer | distance | hits | per chunk | **seconds** |
|---|---|---|---|---|
| `water_areas` | 350 m | 311,946 | 0.33 | **202.8** |
| `green_areas` | 80 m | 451,170 | 0.48 | **142.0** |
| `coastline` | 800 m | 313,953 | 0.33 | 3.1 |
| `place_points` | 900 m | 327,302 | 0.35 | 1.4 |
| `urban_areas` | 100 m | 103,743 | 0.11 | 1.4 |
| `farm_areas` | 80 m | 34,673 | 0.04 | 1.0 |
| `viewpoints` | 400 m | 15,513 | 0.02 | 0.6 |
| **total** | | 1,558,300 | **1.65** | **352.3** |

`water_areas` and `green_areas` are **98% of the 352 s**. Note what that is
*not* explained by: hit counts are 0.33 and 0.48 per chunk, in line with every
other layer. The cost is polygon **vertex count**, not hits — these two layers
are 88 MB and 171 MB of parquet against `farm_areas`' 16 MB.

## Why it matters

`docs/scenery-grading-verdict.md`'s C1 sweep perturbed every constant reachable
without a rebuild — `BETA`, `PREF_CURVE`, `RAW_BASE`, `STRETCH`, `WEIGHTS`,
`CLASS_ADJ` — in **199 s including the Router load**, about 5 s per
perturbation. The constants it could **not** reach are the ones that live inside
these columns:

> `DIST` (7 values), `MIN_AREA` (3), `CHUNK_LEN`, `CURVE_D`, `CURVE_CAP`,
> `CURVE_MIN_LEN`, and the *upward* direction of `CURVE_FULL` / `RELIEF_FULL`
> (a stored clipped column cannot be un-clipped).

Each of those costs **~17 minutes per perturbation** today. A ±2× sweep over
just the seven `DIST` values is 14 rebuilds — about four hours of wall clock to
answer a question the cheap half answers in a minute.

**Flagged as a hypothesis, because it is one:** this is worth building only if
that sweep is actually going to be run. If `DIST` and the `CURVE_*` family are
never going to be touched, the cache is dead code in the most load-bearing
pipeline stage. What would kill this proposal is a decision that the scoring
constants are frozen. What would confirm it is any of C1's rebuild half, or
`docs/scenery-grading-verdict.md`'s E5 (continuous distance decay), or A2/A3
(new landcover columns) — all three need repeated `score.py` runs where only one
input changed.

## The staleness that is real

The originating brief asserted that a `WEIGHTS` change leaves
`RouteResult.mean_score` reading a stale stored column. **Verified false:**
`route()` computes `scores = self._edge_scores(...)` (`pipeline/router.py:1171`)
and passes it into `RouteResult` (`:1261`); `mean_score` (`:1606`) reads the
stored column only `if self.scores is None`, which happens only for a
`RouteResult` a test built by hand.

The real asymmetry is worse and is a second reason to build this:

- **Serving** re-blends live, so a `WEIGHTS` retune is **restart-only**
  (`Router.base_score` / `pref_matrix` are snapshotted at `router.py:918-921`).
- **Validation** is not. `tools/analyze_trace.py:623-629` reads the stored
  `score` column off `graph_edges.parquet`. So today, retuning and re-validating
  against the drive marks are **different operations with different costs**, and
  nothing in the tree says so.

A per-column cache collapses that: the rebuild that re-validates becomes cheap,
because `WEIGHTS` invalidates no component column at all.

## The invalidation table — this is the design

| change | invalidates |
|---|---|
| `WEIGHTS[*]` | **no component column.** Only `raw`, `score`, and `graph_edges.parquet` |
| `RAW_BASE`, `STRETCH`, `CLASS_ADJ` | same — derived columns only |
| `CHUNK_LEN` | everything (the chunk geometry itself changes) |
| `roads.parquet` | everything |
| `DIST["water"]`, `DIST["water_mid"]`, `MIN_AREA["water"]`, `water_areas`, `water_lines` | `c_water` |
| `DIST["green"]`, `MIN_AREA["green"]`, `green_areas`, `tree_cover` | `c_forest` |
| `DIST["coast"]`, `coastline` | `c_coast` |
| `DIST["farm"]`, `MIN_AREA["farm"]`, `farm_areas` | `c_farm` |
| `DIST["view"]`, `viewpoints` | `c_views` |
| `DIST["urban"]`, `DIST["place"]`, `DIST["place_mid"]`, `urban_areas`, `place_points` | `c_urban` |
| `CURVE_D`, `CURVE_CAP`, `CURVE_MIN_LEN`, `CURVE_FULL` | `c_curves` |
| `RELIEF_FULL`, `relief.tif` | `c_relief` |
| `roads.parquet`'s `scenic` column | `c_scenic_tag` |

**That top row is the whole point of the change** and it should be asserted by a
test, not left implied. Columns are built at `pipeline/score.py:311-365`; the
derived values at `:374`, `:379`, `:405-406`.

Size, for scoping: a cached column is 942,448 float64 = **7.5 MB** (float32:
3.8 MB). All nine is **68 MB**. This Mac has 64 GB free.

---

## Traps

**Trap 1 — positional misalignment has no symptom, and this file already knows
it.** `sample_tree_cover` (`pipeline/score.py:243-256`) validates
`tree_cover.parquet` against the chunks it is about to be joined to, on **every**
midpoint, to `atol=1e-9`, and raises `SystemExit` rather than proceeding. Its
comment says why:

```
    Joined by position, so the file has to have been built from this same
    roads.parquet. ... a misaligned join has no symptom: it would credit one
    road with another's trees and still produce a plausible score.
```

A cached column is the *same hazard by the same mechanism*. **Every cache entry
must carry the chunk midpoints it was computed against, and every load must
check them the way `sample_tree_cover` does.** A hash of the midpoints is
acceptable; skipping the check is not. If this brief is only read for one thing,
read it for this.

**Trap 2 — the cache key is the chunk *sequence*, and `roads.parquet` does not
determine it.** The chunks come from `chunk_roads` (`score.py:128-150`), which
is a function of `roads.parquet`, `CHUNK_LEN`, **and the behaviour of
`shapely.ops.substring`**. A shapely upgrade can move a chunk boundary by a
float without touching any input file's hash. Trap 1's midpoint check is what
catches this; it is not redundant with the key, it is the backstop for the key
being incomplete in a way nobody anticipated.

**Trap 3 — hash content, not mtime.** The workflow this exists for is "change
one constant, re-run", where the layer files are untouched. But `git checkout`,
a re-copy, or re-running an upstream stage all change mtime without changing
bytes, and would evict exactly the two expensive entries the cache exists for.
Content-hashing the ~700 MB of input parquet with `blake2b` is ~1.5 s, against
the 352 s it protects.

**Trap 4 — cache the two that matter, not all nine.** `c_farm`, `c_views`,
`c_urban`, `c_coast` and `c_scenic_tag` together are **7.5 s**. Wrapping them in
hash-and-verify machinery adds surface area, adds a place for Trap 1 to happen,
and saves nothing. The measured win is `c_water` (203 s) and `c_forest` (142 s),
which is 98% of the cost. `c_relief` (a raster sample) and `c_curves` (pure
geometry) are worth timing before deciding — they were not measured here.

**Trap 5 — do not put the cache inside `data/processed-ne/`.** That directory is
the deploy source; `docs/hosting-options-brief.md` counts its bytes for transfer
planning, and a naive `rsync` of it would ship the cache to the serving box.
**Follow the existing precedent:** `landcover.py:267` puts its WorldCover tile
cache at `d.parent / "raw" / "worldcover"`. Do the same. (`data/` is gitignored
wholesale, so nothing needs a new ignore rule.)

**Trap 6 — the output must not move.** This is a change to the file every other
artifact is derived from, for a build-speed benefit. The acceptable bar is that
a cached rebuild produces `scored_chunks.parquet` **identical** to an uncached
one, column by column, exactly — not "within tolerance". Build the comparison
first and let it gate the change.

**Trap 7 — resist making this general.** A content-addressed DAG cache for the
whole pipeline is a bigger, more interesting piece of work and is not what the
measurement supports. Two columns, one directory, one midpoint check.

---

## Done looks like

1. `score.py` reuses a cached `c_water` and `c_forest` when their inputs and
   constants are unchanged, and recomputes them when either changes.
2. Every cache load verifies the chunk midpoints the entry was built against,
   and fails loudly — the way `sample_tree_cover` does — rather than returning
   misaligned data (Trap 1).
3. A cached rebuild of `data/processed-ne` produces a `scored_chunks.parquet`
   byte-identical to an uncached one (Trap 6). **Build into a scratch directory;
   never write to `data/processed` or `data/processed-ne`, which serve live.**
4. A test asserting the top row of the invalidation table: changing
   `WEIGHTS` invalidates no component column.
5. Measured: cold rebuild time, warm rebuild time, and warm rebuild time after
   changing `DIST["water"]` only. The expectation from the timings above is
   roughly 11 min → ~5 min warm; a warm rebuild that is not several minutes
   faster means the cost is somewhere this brief did not look, which is worth
   reporting rather than working around.
6. `.venv/bin/python -m pytest tests/` green with `SCENIC_DATA` on the New
   England build.
7. **Or** a statement that the hypothesis under *Why it matters* is wrong — that
   the constants this unlocks are not going to be swept — in which case this
   should not be built and saying so is the right answer.

## Reproducing the timings

```
SCENIC_DATA=<abs>/Scenic/data/processed-ne     # the live New England build
```

One scratch script: `gpd.read_parquet(scored_chunks.parquet)`, then for each
layer rebuild the same `STRtree` with the same `MIN_AREA` filter `score.py`
applies and time `tree.query(geoms, predicate="dwithin", distance=DIST[...])`.
No rebuild, nothing written.

The data lives **only in the main checkout**, never in a worktree. The project
path contains spaces, so every venv console script has a broken shebang: always
`.venv/bin/python -m <tool>`, never `.venv/bin/pytest`.
