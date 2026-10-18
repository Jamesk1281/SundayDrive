# Routing safety: the quick fixes (brief)

**Status:** diagnosed, not fixed. Written 2026-10-18 in the master session. Nothing
in `pipeline/`, `server/`, `ios/`, `tests/` or `data/` has been touched for this.
Work on a branch off **`main`** (these are generic fixes that also bite in New
England). The master session merges `main` into `usa` afterwards. The answer
lives in the code and tests, plus `docs/safety-quick-fixes.md`. This brief is
deleted in the merge that brings the work back, so nothing permanent may cite it.

**Decided in the master session, so don't reopen these:**

- A road tagged `4wd_only=yes`, or `smoothness` of `very_bad` or worse
  (`very_bad`, `horrible`, `very_horrible`, `impassable`), is **closed to cars**.
  This is the same principle as the existing ford rule: a consumer car app should
  not plan one.
- A road carrying `tiger:cfcc` A5x (TIGER's 4WD-trail class) counts as
  **unpaved**, not closed, unless OSM's own `surface` says it is sealed. Unpaved is
  avoided by default (`avoid_unpaved` defaults to 1.0, `server/app.py:302`).
- `smoothness=bad` stays open.
- **Out of scope, waiting on the owner:** the permit rule (`permit` in
  `CLOSED_TO_CARS`). Don't touch it.

## The goal, as measured

The US map-data inventory (`docs/us-map-data-findings.md` §4, §6.4–6.5, and gaps
S1–S2 in §7) found that the router plans roads that are closed or not passable
in a car. These are the parts fixable in days, from tags already in the OSM
extract:

**1. Closure dates that closures.py can't parse** (§4, cause 1). These strings
fail `_RANGE` and are skipped as "unrecognized", so the road stays open all year:

| tag value | where | km |
|---|---|---:|
| `no @ Oct 14th - May 31st` | Trail Ridge Road, CO | 66 |
| `no @ Nov 19th - May 30th` | CO | 18 |
| `no@(Dec 1 - Mai 1)` | (German month) | 13 |
| `no @ (8 Dec - 1 May)` | WA (day before month) | 7.5 |

Dropping the ordinal suffix alone would close 84.7 km in Colorado. **New England
has none of these today.** A scan of `data/raw/new-england-latest.osm.pbf` on
2026-10-18 found 0 km of drivable way with an unrecognized or ordinal car-key
conditional. So this fix changes nothing in New England, and it is still the
right place for it.

**2. Gates whose seasonal closure is tagged on the gate node, not the way** (§4,
cause 4). closures.py reads conditionals on ways only. For gates it counts the
timed ones and moves on. The New England extract has **57 barrier nodes with a
conditional**, seasonal ones among them:
`gate no @ (Nov-Apr)`, `gate no @ (Nov-Mar)`, `gate no @ winter`,
`gate yes@(Jun-Aug)`, and `chain permissive @ (winter)`. Many others are times of
day (`gate no @ (Mo-Fr 17:00-07:00; Sa-Su)`). In the West, Mirror Lake's and the
North Cascades' winter gates carry them. Those two are redundant with their
ways' tags, but elsewhere a gate can be the only tag a closure has.

**3. 4WD and very rough roads in the graph, unflagged** (§6.4–6.5, S2). New
England drivable ways, measured on the same scan:

| tag | km |
|---|---:|
| `tiger:cfcc` A51 | 711.6 (61.9 of it with a sealed `surface`) |
| `smoothness=very_bad` | 17.1 |
| `smoothness=horrible` | 11.1 |
| `smoothness=very_horrible` | 1.2 |
| `smoothness=impassable` | 0.2 |
| `4wd_only=yes` | 1.2 |
| `smoothness=bad` (stays open) | 265.6 |

Nationally, A5x is unflagged on 3,296 km in South Dakota, 1,499 in Montana, 927
in Colorado and 914 in Kansas. **None of `4wd_only`, `smoothness`, `tracktype` or
`tiger:cfcc` is read anywhere in `pipeline/` today.** Some New England A51 km will
already be covered by `state_road_class.parquet` (Vermont Class 4 and the rest).
Measure the overlap and report it.

## The mechanism

**Dates.** `pipeline/closures.py:105-110`:
```python
_MONTH = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
_RANGE = re.compile(
    rf"^{_MONTH}(?:\s+(\d{{1,2}}))?"
    rf"(?:\s*-\s*(?:{_MONTH}(?:\s+(\d{{1,2}}))?|(\d{{1,2}})))?$",
```
It accepts month-then-day only, with a bare number for the day. `_rule_windows`
(`closures.py:152-180`) returns `"unrecognized"` on any part `_RANGE` rejects,
and `_window` (`closures.py:135-149`) maps month names to numbers through the
first three letters, so `Mai` can't map.

**Gates.** `closures.py:435-446`, `_count`, tallies a gate with a conditional
into `record["timed gates"]` and nothing else. `barrier_closes`
(`pipeline/common.py:104`) decides only the all-year case. Way conditionals become
per-edge windows through `way_windows` (`closures.py:275`) and
`conditional_windows` (`closures.py:241`) into `seasonal_closures.parquet`. The
router masks those windows by date (`pipeline/router.py:462` onward).

**Rough roads.** All-year closures are written by `_all_year` (`closures.py:395`)
into `closed_to_cars.parquet`. It appends `closed_to_cars(tags)` and `ford=yes`:
```python
if (tags.get("ford") or "").strip().lower() == "yes":
    closes.append("ford=yes")
```
That is where `4wd_only` and `smoothness` belong. The router reads the file at
startup (`router.py:798-818`), so the deploy is restart-only.

**Unpaved.** The router's unpaved set is the graph's surface-derived
`unpaved_frac` plus the `"unpaved"` rows of `state_road_class.parquet`
(`router.py:1738` `_load_unpaved`, `1793-1798`). The state rules and their
validation are at `router.py:591-620`.

## Traps

1. **Gate conditionals must go through the existing grammar.** Pass them through
   `conditional_windows` and its refusals (`dated`, `part-time`, `time of day`,
   `vehicle`). Never write a second parser. Most of New England's 57 are times of
   day. Read by their months alone they would shut a park gate all summer for its
   evening hours, which is exactly the Baxter Boulevard trap
   `_rule_windows`' docstring describes. `yes @ (Jun-Aug)` closes *outside* the
   window (the complement, as ways already do). Values like `customers @ ...` and
   `permissive @ ...` close nothing. And a conditional must never *open* a barrier
   that `barrier_closes` already closes all year (the chain).
2. **A51 is an unreviewed TIGER import class, not ground truth.** 61.9 of New
   England's 711.6 A51 km carry a sealed `surface`. Closing A51 outright would cut
   real roads. That is why the decision is unpaved, with OSM's sealed surface
   winning, the same precedent as `SURFACE_CLASSES`/`SEALED` in
   `pipeline/state_roads.py:255-263`. Don't write A51 rows into
   `state_road_class.parquet`: `state_roads.py` regenerates that file from state
   DOT data, and its `state`/`cls` columns mean something else. Give the router
   an OSM-derived unpaved input of its own (written by closures.py beside
   `closed_to_cars.parquet`), with the same u/v check against
   `graph_edges.parquet` that the other sidecars have.
3. **Strip ordinals narrowly.** Only an `st|nd|rd|th` suffix directly after a
   1–2 digit day. `_WEEKDAY` (`closures.py:115`) already matches `th` as Thursday
   when it stands alone. Add day-first (`8 Dec - 1 May`) and the one German month
   seen (`Mai`) as explicit cases, with a test for each exact string in the table
   above. Don't loosen the year, time or weekday refusals: every one of them was
   added to stop a real New England road being closed for good.
4. **Don't claim a New England win for the date fix.** It moves 0 km there. Gates
   and rough roads do move New England. Measure them.
5. **Closing a road can strand a start or destination.** Re-run the exposure
   measurement `docs/closed-roads.md` used (loops and scenic routes crossing a
   closed element, before and after), and check that snap still keeps drivers off
   the newly closed roads.
6. **Never write into `data/processed-ne` in the main checkout.** That is the
   deployed build's source. Run closures.py into a scratch copy. Deploying
   (rerunning closures.py into `processed-ne`, shipping with
   `server/deploy-oracle.sh`) is the master session's return leg, not yours.

## Done looks like

1. closures.py parses the four strings above. Gate-node seasonal conditionals
   become `seasonal_closures` windows. `4wd_only=yes` and `smoothness` of
   `very_bad` or worse land in `closed_to_cars`. A5x without a sealed surface
   reaches the router as unpaved. The permit rule is untouched.
2. Tests in `tests/test_closures.py` (and `test_closed_roads.py` for the router
   side) for each case and each refusal kept. The full suite is green
   (`.venv/bin/python -m pytest tests/`).
3. `docs/safety-quick-fixes.md`, covering:
   - New England before and after: km closed by each new rule, A51 km newly
     unpaved and how much `state_road_class` already covered, gates that now
     close and in which windows, and the exposure change on loops and routes;
   - the exact closures.py output line counts the deploy should expect;
   - the deploy steps.
4. If a Colorado PBF is at hand, the same counts there. Trail Ridge's window
   must parse as Oct 14–May 31. It will still be closed every day by the
   untouched permit rule, so check the window in `seasonal_closures`, not in
   routing. Otherwise, say it wasn't measured.
