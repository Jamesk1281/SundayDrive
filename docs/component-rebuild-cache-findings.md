# What the component cache turned out to be

**Status: built and measured 2026-09-19 on the live New England build**
(`data/processed-ne`, 565,410 ways / 942,448 chunks). Changed: `pipeline/score.py`,
`tests/test_cache.py` (new), `README.md`. Every rebuild below was written to a
scratch directory of symlinked inputs; `data/processed` and `data/processed-ne`
were not written to.

This is what came of [`docs/component-rebuild-cache-brief.md`](component-rebuild-cache-brief.md),
committed alongside it, which is in turn F2 of `docs/scenery-grading-verdict.md`.
**The brief's measurements hold and its design is sound. Two of its framings are
wrong in the same direction — it undersells the change — and one of its
prescriptions is worth deviating from.**

---

## The headline

| rebuild | total | the three cached queries |
|---|---|---|
| uncached (`--no-cache`) | **454.7 s** | 129 + 153 + 107 = **389 s** |
| cold (cache on, empty) | **459.3 s** | 139 + 142 + 100 = **381 s** |
| warm, nothing changed | **62.7 s** / **77.9 s** | all three cached |
| warm, `WEIGHTS["water"]` doubled | **73.4 s** | all three cached |
| warm, `DIST["water"]` 120 → 150 | **223.8 s** | water@150 recomputed (143 s) |

**About 6–7× on a full rebuild, and the `WEIGHTS` row is the one that
matters** — a scenery retune that has to be re-validated against the drive
marks now costs 73 s of `score.py` instead of 455 s. The brief predicted
"roughly 11 min → ~5 min warm"; the real figure is better than that on both
ends, for reasons in *Where the brief is wrong*, below. The two warm figures
are the same build run twice, an hour apart, at different machine loads; see
the same section for why that spread is reported rather than averaged away.

Cold costs 5 s more than uncached, which is the three `.npz` writes and
run-to-run noise. The cache does not pay for itself on the first build and is
not meant to.

**Five independent builds — uncached, two cold, two warm — produced the same
`scored_chunks.parquet`**: blake2b `2a439bc92f502a56c97c00caf22b0706` for all
of them. That is stronger than Trap 6's bar, which was column-for-column
equality.

The two runs that *should* move the output do, and only where they should:

| | columns that changed | chunks affected |
|---|---|---|
| `WEIGHTS["water"]` ×2 | `raw`, `score` — **no component column** | 321,212 / 318,316 |
| `DIST["water"]` 120 → 150 | `c_water`, and `raw`/`score` downstream | 24,215 |

## What is cached, and two deviations from the brief

The brief says to cache the `c_water` and `c_forest` **columns**. This caches
the **`dwithin` queries** underneath them instead. Same two layers, same
directory, same midpoint hazard — but the key is narrower, in two ways that
both matter for the sweeps this exists to enable:

- **`c_forest` is half OSM green and half `tree_cover.parquet`, and only the
  green half is expensive.** A column key would throw the green query away
  every time `landcover.py` re-ran — which is exactly what A2/A3 of the
  grading verdict propose doing repeatedly. A query key does not.
- **`c_water` is two queries against one tree.** Re-tuning `DIST["water_mid"]`
  leaves the 120 m answer cached, which halves the cost of the `DIST` sweep the
  brief is built for. That is not hypothetical: the `DIST["water"]` run above
  cost 223.8 s rather than ~370 s because the 350 m answer survived.

The second deviation: **the trees are built lazily**. `CachedQuery` takes a
callable, not a tree, so a warm rebuild never opens the 88 MB + 171 MB of
water and green polygons at all. Part of the gap between the brief's predicted
5 minutes and the measured 63–78 s is that the brief's design still pays to
read and reproject a quarter of a gigabyte on every run.

### Trap 1, handled harder than asked

The brief asks that every entry carry the chunk midpoints it was computed
against, hashed if convenient. `chunk_digest` hashes **every coordinate of
every chunk plus the per-chunk vertex counts** instead. This is strictly
stronger — identical coordinate bytes imply identical midpoints — and it is
*cheaper*: 0.35 s over 9.8M coordinates, against 0.41 s to compute the
midpoints alone.

It is stronger in a way that matters, not just formally. `dwithin` reads the
whole line, not the midpoint, so two chunks can agree on their midpoint to
`sample_tree_cover`'s `atol=1e-9` and still have different answers — a chunk
that dips 4 m towards the water is the test case in
`tests/test_cache.py::test_two_roads_can_share_a_midpoint_and_not_a_geometry`.
Hashing the geometry also subsumes `roads.parquet`, `CHUNK_LEN`, and Trap 2's
shapely-moved-a-boundary case in one value.

A mismatch is a `SystemExit`, not a silent recompute: the filename *is* the
digest of the key, so an entry whose recorded key disagrees is a collision or a
hand-edit, and the cost of guessing wrong is the misaligned join that has no
symptom.

## The invalidation table, as implemented and as tested

`tests/test_cache.py` runs `score.main()` against a synthetic six-road region
and asserts on **which layer files were opened**, because a cache hit is
exactly the case where the expensive layer is never read.

| change | recomputes | test |
|---|---|---|
| `WEIGHTS`, `RAW_BASE`, `STRETCH`, `CLASS_ADJ` | **nothing** | `test_weights_invalidates_no_component_column` |
| `DIST["water"]` or `DIST["water_mid"]` | water only | parametrized |
| `DIST["green"]`, `MIN_AREA["green"]` | green only | parametrized |
| `MIN_AREA["water"]` | water only | parametrized |
| `water_areas` or `water_lines` content | water only | parametrized |
| `green_areas` content | green only | parametrized |
| `tree_cover.parquet` | **nothing** (`c_forest` moves anyway) | `test_tree_cover_moves_c_forest_without_re_running_the_green_query` |
| any layer's mtime, content unchanged | **nothing** (Trap 3) | `test_touching_a_layer_without_changing_it...` |
| `DIST["farm"]` (shares 80 m with green) | nothing cached | `test_a_cheap_layers_distance_invalidates_nothing_cached` |
| `CHUNK_LEN`, `roads.parquet` | everything | two tests |

Note that the grading verdict's F2 prose says "`CHUNK_LEN` and `MIN_AREA`
invalidate everything". The brief's own table is the correct one: each
`MIN_AREA` entry feeds exactly one tree, so it invalidates exactly one query.

**The tests were mutation-checked, and the first cut was not good enough.**
Eleven deliberate breakages of the key and the verification — dropping each
layer digest, the chunk digest, `min_area`, the distance; keying on mtime;
hashing midpoints instead of geometry; skipping the load-time check; making
`--no-cache` read the cache. Three survived the first version of the tests
(the water layer digests were droppable because only `green_areas` was ever
rewritten, and the midpoint-versus-geometry claim was asserted nowhere). All
eleven fail the tests now.

## Where the brief is wrong

**1. `score.py` issues nine `dwithin` queries, and the brief's table has seven
rows.** It carries one row per *layer*. Missing: `water` at `DIST["water"]`
(120 m) and `place_points` at `DIST["place"]` (400 m).

This is not a rounding error on the expensive side. Measured back to back on
this build, **`water@120 m` costs essentially as much as `water@350 m`** —
123.4 s against 125.3 s standalone, 129 s against 153 s inside the build. So
the water *layer* is about twice what the brief's table prices it at, the
"352.3 s total" is nearer 550 s on the brief's own scale, and the cacheable
share is ~99% rather than 98%. The missing cheap query, `place@400 m`, is 0.5 s
and changes nothing about Trap 4.

**2. The absolute seconds are softer than they look, but the ratios hold.**
Re-measuring the brief's own rows on the same data came in at a consistent
~0.62× its numbers (`water@350` 125.3 s against 202.8 s; `green@80` 86.0 s
against 142.0 s; `place@900` 0.9 s against 1.4 s). That is machine state, not
method — the relative picture is identical.

**This Mac is shared with other Claude sessions, and that deserves more than a
footnote.** One cold rebuild here overlapped another session's job and recorded
**938 s and 1,697 s** for the same two queries that took 142 s and 100 s in a
clean run forty minutes later — a 6–17× inflation with no other cause, on
identical code and identical inputs. It was caught only because the number was
absurd. The cold build was therefore run twice (454.7 s and 459.3 s, agreeing
to 1%) with `uptime` and a count of competing processes sampled every 60 s
throughout. **Anything timed on this box needs the load recorded beside it**,
and a single unreplicated timing here is not evidence. That applies to the
brief's table, to this document, and to `docs/unpaved-and-urban-brief.md:152`'s
eleven minutes.

**3. `docs/unpaved-and-urban-brief.md:152`'s "~11 minutes" is stale.** A full
uncached score rebuild is 454.7 s and a cold one 459.3 s — 7.6 minutes, twice,
at an ordinary load average of about 3.

## What was not built, and why

- **`c_relief` and `c_curves`**, which Trap 4 leaves open. They needed no
  separate timing to settle. Subtracting the printed stage boundaries: the
  uncached feature stage is 416 s of which the three cached queries are 389 s,
  leaving **27 s** for curvature, the relief raster sample, the tree-cover join
  and all five cheap layers *put together* — and the three other builds
  reproduce it at 31 s, 24 s and 30 s. Neither is a candidate, and neither is
  anything else in there.
- **The other five layers.** 7.5 s between them, as the brief says.
- **Anything general.** Trap 7 asked for two layers, one directory, one
  alignment check, and that is what this is. `score.py` grew one class.

## Cost, and the floor this leaves

The cache is **460 KB for four entries** — ~110–130 KB each, not the 7.5 MB per
column the brief scoped for, because the stored thing is a boolean flag array
rather than a float column and it compresses. A ±2× sweep over all seven `DIST`
values would leave about 2 MB behind. Nothing evicts; delete the directory.

It lives at `data/raw/component-cache`, following `landcover.py:267`, so an
rsync of `data/processed-ne` to the serving box does not ship it. Builds of
different regions share the directory safely — their chunk digests differ.

What the cache cannot touch is a **60–78 s floor** on any `score.py` run: 29–37 s
to re-chunk 565,410 ways, 5 s to digest the chunks and the layer files, 24–31 s
of cheap components, 2 s to write 208 MB, and 4 s of calibration report.

Caching the chunking itself is the obvious next increment and it is *not*
recommended on this evidence — 29 s of a 63 s warm run is a far worse ratio
than the 389 s of 455 s this change was built on, and it would put the chunk
geometry behind a cache that depends on that geometry for its identity.

## The hypothesis, answered

The brief flags its own justification as a hypothesis: this is worth building
only if the constants it unlocks are actually going to be swept, and "if you
conclude the scoring constants are frozen, saying so and not building it is the
right answer."

**They are not frozen.** `docs/scenery-grading-verdict.md` ranks F2 fifth of
ten by evidence-per-hour, and three separate items above or near it need
repeated `score.py` runs where exactly one input changed: C1's rebuild half
(explicitly deferred *because* it costs ~17 minutes per perturbation, with
`CURVE_CAP`, `CURVE_MIN_LEN` and `MIN_AREA` named as the deletion candidates),
E5's continuous distance decay, and A2/A3's new landcover columns. The drive
marks are also still accumulating — 79 as of 2026-09-16 — and each new batch is
a reason to re-fit and re-validate.

The second argument, which the verdict added and the brief carries, survives
contact with the build: a `WEIGHTS` retune is restart-only for serving but
rebuild-only for validation, because `tools/analyze_trace.py:623-629` reads the
stored `score` column off `graph_edges.parquet`. That asymmetry is now 73 s
wide instead of 455 s.
