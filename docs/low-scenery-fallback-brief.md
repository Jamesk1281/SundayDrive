# Brief: when the scenic route isn't worth it, the server says so on every path

**Status: diagnosed and decided, not built.** Nothing has been changed.
Branch off `usa` at or after `ea87a2a`, which has the snap-cap merge. Line numbers
below are at `ea87a2a`. This brief is temporary and is deleted in the merge that
brings the work back. **Your answer goes in `docs/low-scenery-fallback.md`**,
plus the code and tests. Never append to this brief, and cite
`docs/low-scenery-fallback.md` from code and tests.

## The goal

The owner decided on 2026-10-23:

1. **The busy fallback gets the menu's existing minimum.** When the plain
   route path plans a trip, a scenic route that gains less than 0.5 mi
   (`MENU_FIRST_MIN_KM = 0.805`, `pipeline/options.py:60`) of beautiful road
   over the fastest is replaced by the fastest. That is the minimum the menu
   already applies to its first option.
2. **A beautiful-km guard.** No scenic route is ever handed back with *fewer*
   beautiful km than the fastest.
3. **The app says why.** When the server fell back for lack of gain, the card
   reads "No beautiful road worth the detour on this trip" instead of "Same as
   the fastest route at this setting".
4. **Measure** the app's real request on a random national sample, before and
   after.

The minimum stays 0.5 mi. The owner chose the existing number over a new 2 km
one, and the measurement decides whether it should rise later. Don't add a
time budget to the plain path. It wasn't decided, so measure it instead (see
*Measure*).

## What was measured, and why the plain path is the one that matters

The 2026-10-23 outside review measured the plain request (`POST /api/route`,
`pref=0.5`, no `options`) on a local national server:

| trip | fastest | scenic | beautiful km, fastest → scenic |
| --- | --- | --- | --- |
| Wichita → Salina | 69 min | 106 (+54%) | 0.0 → 0.1 |
| New Orleans → Baton Rouge | 69 | 119 (+73%) | 0.0 → 0.0 |
| Chicago → Milwaukee | 81 | 138 (+70%) | 0.0 → 1.6 |
| Atlanta → Chattanooga | 94 | 181 (+93%) | 0.0 → 7.6 |

- Of 16 seeded random trips of 40–160 km, 12 gained ≤ 1 km of beautiful road
  for 0–26% more time.
- In 3 of them, scenic had **fewer** beautiful km than the fastest, and took
  longer:
  - near 40.58,-119.30 (NV): +32%, 10 → 1 km;
  - near 45.87,-121.56 (WA): +18%, 11 → 8 km;
  - near 43.21,-115.36 (ID): +2%, 3 → 2 km.
- In the app's simulator, Denver → Estes Park read "Scenic adds 9 min and
  leaves beautiful road at 11 mi". Unit national-copy re-measured it as
  17.2 → 17.8 km for +10 min.

**The app normally asks for the menu, not that route.**
- `RouteModel.swift:197` sends `options: true`.
- The menu's default (`pipeline/options.py:490-493`) is the most scenic option
  costing at most 25% extra time (`DEFAULT_MAX_EXTRA_SHARE`).
- Its first option must gain at least `MENU_FIRST_MIN_KM`, and each later one
  at least `max(1 mi, 5% of the whole gain)` more.

**But the menu is computed only when the server is alone.**
`server/app.py:643`: `want_options and ROUTE_OPTIONS and alone`. The plan
also gives up between phases when another request arrives
(`docs/route-options.md`, "The busy guard"). Any overlapping request therefore
gets the plain path, which is `server/app.py:825-846`: one search at the
driver's `pref`, no budget, no minimum. On a busy launch day that is a large
share of plans. Older backends and app builds take the plain path too. The
review's numbers describe that path.

## The mechanism

The plain path's only check is `_no_worse_than_fastest`
(`server/app.py:580-602`):

```python
return fastest if scenic.mean_score < fastest.mean_score else scenic
```

- That is the mean score, length-weighted. A route can raise the mean
  slightly while losing most of its beautiful km, which is the Nevada case.
- `RouteResult.beautiful_km` (`pipeline/router.py:4403`) is the count the card
  prints.
- The menu's own gain is computed from hop stats (`options.py`, `_hop_stats`)
  on the same `BEAUTIFUL_SCORE` line.

The guard is called from three places:

| line | path | gets |
| --- | --- | --- |
| `app.py:844` | plain, the busy fallback and reroutes without switch points | **guard + minimum, when planning** (no heading, not moving); **guard only, when moving** |
| `app.py:811` | one menu option fetched by switch points (the driver chose it, or a reroute on it) | guard only |
| `app.py:770` | loop rejoin, mid-drive | guard only |

The menu path (`app.py:778-787`) doesn't call the guard. Its options gain
> 0 by construction. It still needs the *reason* (see *The contract*).

## What to build

1. **One constant.** The minimum is `MENU_FIRST_MIN_KM`, imported, not copied.
2. **The guard** falls back to the fastest when the scenic route has fewer
   `beautiful_km` than the fastest, *or* (as today) a lower `mean_score`.
   Keeping the old half means a reroute changes only in the fewer-beautiful-km
   case.
3. **The minimum, on plans only:** on the plain path with no heading, no
   declined U-turn and not moving, fall back to the fastest when
   `scenic.beautiful_km - fastest.beautiful_km < MENU_FIRST_MIN_KM`.
   - Pref 0 is unchanged. Scenic is already the fastest there.
   - Never apply the minimum mid-drive (Trap 2).
4. **The contract.** When the scenic arm *is* the fastest because nothing
   gained the minimum, the reply says so.
   - Do this on the plain path, and on the menu path when no frontier option
     reached `MENU_FIRST_MIN_KM` (`t_max <= 0`, an empty front, or nothing
     chosen).
   - One field on the scenic feature's properties, for example
     `"no_gain": true`. The name is yours; document it.
   - It is absent in every other case, including a menu whose default is the
     fastest only because every option is over the 25% budget (Trap 3).
   - Older app builds ignore unknown properties. Check that the decoder
     tolerates it.
5. **The app.**
   - Decode the field.
   - When it is present and the comparison is the same drive, the summary
     reads "No beautiful road worth the detour on this trip." (in
     `RouteComparison.summary`, `ios/Sources/RouteResults.swift:241`, and
     wherever `DirectionsView.swift:229` branches on `isSameDrive`).
   - Otherwise keep "Same as the fastest route at this setting".
   - "Start driving" already drives the scenic arm, which is now the fastest.
     Confirm that, don't assume it.
6. **Tests.**
   - Python: each path in the table, the reason present and absent (including
     the over-budget menu), mid-drive untouched by the minimum, and a
     fewer-beautiful-km case.
   - iOS: the new sentence, and the old one when the field is absent.

## Measure

Run all of this on a local national server, before and after:

- **A seeded random sample** of at least 100 trips, 40–160 km apart, with both
  ends on roads anywhere in the 48 states. Record the seed.
- **The review's named trips:** Wichita → Salina, New Orleans → Baton Rouge,
  Chicago → Milwaukee, Atlanta → Chattanooga, Denver → Estes Park, and the
  three fewer-km points above as starts.

For each trip, two requests the way the app sends them (`RouteService`: POST,
form body, the app's default weights, `pref` 0.5):

1. **with** `options=1` and the server otherwise idle: the menu path;
2. **without** it: the busy fallback.

Report, before and after:
- the share where the scenic arm gains less than 0.5 mi;
- the share where it costs more than 10% extra time for under 2 km gained,
  which is the review's metric;
- the share that falls back to the fastest;
- the extra-minutes distribution;
- **for the fallback after the change:** how many still cost more than 25%
  extra time, which is the menu's budget. That number is the case for or
  against a time budget, an owner decision for later.

## Traps

1. **"The app's default is the review's table" is wrong.** The menu already
   has a budget and a minimum. Changing the menu's constants is out of scope.
   The plain path is where the gap is, so measure both paths, or the
   before/after describes the wrong one.
2. **The minimum must not touch a moving car.** Near the end of a scenic
   drive the remaining gain is naturally under 0.5 mi. Applying the minimum to
   a reroute would switch the driver to the fastest roads for the last stretch
   and change the route under them. Plans only: no heading, no declined
   U-turn, no switch points.
3. **"Fastest because over budget" is not "no gain".** A menu whose options
   all cost more than 25% extra still offers them on the dial. Saying "No
   beautiful road worth the detour" there is false, because there is
   beautiful road, at a price the driver can choose.
4. **Two beautiful counts exist:** `RouteResult.beautiful_km` and the menu's
   hop-stat gain. Use each path's own count, and check on the named trips that
   the two agree to within rounding.
5. **One national server at a time** on this 24 GB Mac. Check
   `ps -axo pid,rss,command | grep '[s]erve.py'` first, and stop yours by PID
   only, never `pkill`. The menu path runs only when the server is alone, so
   send the `options=1` requests one at a time, or they silently become
   fallback requests and the measurement is wrong.

## Out of scope

- The menu's constants.
- A time budget on the plain path (measure it only).
- Loops.
- The cost function and `BETA` / `PREF_CURVE`.
- Deploying.

## Done looks like

1. On a plan, the plain path never returns a scenic route that gains less
   than 0.5 mi, or that has fewer beautiful km than the fastest.
2. A moving car's routes change only in the fewer-beautiful-km case.
3. The reply carries the no-gain reason exactly when nothing gained the
   minimum, and the app shows the new sentence then and only then.
4. The Python suite on `processed-ne` and the iOS tests pass, apart from known
   failures, which are named. `tests/test_national_routes.py` passes with
   `SUNDAYDRIVE_PACK` set.
5. `docs/low-scenery-fallback.md` holds the before/after measurement on both
   paths, the contract, and the over-budget count for the owner. Or, for any
   item that cannot be done, a statement saying why.
