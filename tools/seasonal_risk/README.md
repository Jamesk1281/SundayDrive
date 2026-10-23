# Seasonal road risk study

The scripts and results behind `docs/seasonal-road-risk-verdict.md`. They
change nothing under `pipeline/`, `server/`, `ios/` or `data/`. A ban or a
margin is a modified copy of `seasonal_closures.parquet` held in memory
(`harness.set_table`). A date is `server/app.py`'s `_today()` hook replaced.
P5's "avoid this road" is extra closed slots in the router's own
`_closed_slots` (`harness.set_avoid`).

| File | What it is |
|---|---|
| `harness.py` | `server/app.py` imported in process: `route()` posts to `/api/route` through Flask's test client and returns the RouteResults `_route` built. Also `set_day`, `set_table`, `set_avoid`, and `open_to_cars` (Trail Ridge's permit rule lifted, as the brief directs). |
| `windows.py` | Window source of every table row (`osm_dated`, `osm_default`, `unknown`, `table`, `agency_dated`), 365-day closed masks, and policy tables (ban, margins). |
| `roads.py` | The named roads as table filters, with gateway-to-gateway ends. |
| `q1_routes.py` | Q1. Samples (`--make-samples`, seed 20261021) and routes: all open, P0 on Jun 15, Aug 15 and Oct 15, and P1 (ban). Writes `samples.json` and `q1_routes.csv`. |
| `q1_summary.py` | Q1's tables: `q1_by_run.csv` (per sample and run) and `q1_named.csv` (per named road). |
| `q2_published_dates.csv` | Q2's evidence: published opening and closing dates, one row per road-season, each with its URL, its read date and its quality (actual, scheduled, projected, or "by", meaning a report date). |
| `q2_windows.py` | Q2. Our windows against those dates. Writes `q2_misses.csv` and `q2_by_binding_source.csv`. |
| `q3_turnaround.py` | Q3. A driver at the closed end turns round, and the server's reroutes are replayed. `--cases named` covers the named roads on their shoulder days, `top` the most-used stretches, and `trips` every Q1 trip that uses a seasonal edge (detour only). |
| `q4_policies.py` | Q4. P0–P5 on the measured numbers, offline. Writes `q4_frontier.csv` (every policy and sample), `q4_candidates.csv` (the named policies side by side), `q4_attribution.csv` (P0's stranding by window source) and `q4_validation.csv`. `--default-curve pooled` gives the milder sensitivity for `WINTER`, as `*_pooled.csv`. |
| `q4_choose.py` | The brief's decision rule at the 80%, 90% and 95% bars: `q4_choice.csv` (and `_pooled`). |

## Running

```bash
D=/Users/james./Desktop/myapps/SundayDrive/data
export SUNDAYDRIVE_DATA=$D/processed-us SUNDAYDRIVE_PACK=$D/pack-us
PY=/Users/james./Desktop/myapps/SundayDrive/.venv/bin/python
$PY q1_routes.py                  # national pack, ~3.2 GB resident
$PY q1_summary.py
$PY q2_windows.py                 # no router; reads Q1's routes for the router's own window
$PY q3_turnaround.py --cases named
$PY q3_turnaround.py --cases top
$PY q3_turnaround.py --cases trips
$PY q4_policies.py                # no router from here on
$PY q4_policies.py --default-curve pooled
$PY q4_choose.py && $PY q4_choose.py _pooled
```

`q3_turnaround.py --real-p5` also asks each replayed reroute with the
`avoid_edges` the app would send, the built P5. Each `P5 built` row says which
closed edges it entered and whether the avoid set named them
(docs/seasonal-road-policy.md).

`built/` is the whole study re-run on the rebuilt pair of
docs/seasonal-road-policy.md (`SUNDAYDRIVE_DATA=data/processed-us-next
SUNDAYDRIVE_PACK=data/pack-us-next`, run from a copy of this directory so
the verdict's CSVs here stay as they were). In it, Q4's P0 is the build.

Run the national steps one process at a time, and check `memory_pressure`
first: the Mac is shared with sessions holding national data. Never measure
on the real date. Every run names its own.
