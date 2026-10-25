# When the scenic route isn't worth it, the server says so

**Status: built on `claude/low-scenery-fallback-9b62f0`, off `usa` at `ea87a2a`.
Not merged, pushed or deployed.** The brief is
`docs/low-scenery-fallback-brief.md`.

## The answer

On a seeded national sample of 134 trips (120 random, 40-160 km apart, plus
the review's named trips), at the app's request (pref 0.50, its default
weights, a form POST):

| the scenic arm, busy fallback (`options=1`, menu not run) | before | after |
| --- | --- | --- |
| offered while gaining < 0.5 mi of beautiful road | 55 (41%) | 1 (1%), a rounding artefact |
| offered at > 10% extra time for < 2 km gained (the review's metric) | 29 (22%) | 9 (7%) |
| offered with **fewer** beautiful km than the fastest | 5 (4%) | 0 |
| the fastest route, so the card reads "same" | 8 (6%) | 62 (46%), all with `no_gain` |
| extra minutes p50 / p90, all trips | 15.9 / 65.1 | 3.4 / 65.1 |
| **offered at > 25% extra time (the menu's budget)** | 49 (37%) | **41 (31%)** |

- **The menu path is unchanged** except for the reason. `no_gain` is on 27 of
  its 134 plans, and absent on the 10 whose default is the fastest only
  because every option gaining 0.5 mi or more is over budget (Trap 3).
- **For the owner: a time budget on the fallback.** After the change, 41 of
  the 72 scenic routes the fallback still offers cost more than 25% extra
  time. The median is +52 min (+49%) for 22 km of beautiful road. On the same
  41 trips the menu's default costs a median +21 min for 7.3 km. That gap is
  the case for a budget, and it is not decided here.
- **For the owner: the menu has a hole the brief did not know about.** The
  brief says the menu's first option must gain at least 0.5 mi. It doesn't
  always: when no frontier point reaches the minimum, the menu still keeps
  its most scenic point (`pipeline/options.py:461-462`, "the most scenic
  frontier point always stays"), and defaults to it when it is within budget.
  That happened on **13 of 134 plans (10%)**: two-entry menus whose default
  gains 0.1-0.7 km, for up to +22 min (r112: 106 -> 128 min for 0.2 km). No
  `no_gain` is sent there, because the scenic arm is not the fastest. This
  is the app's *normal* path. Closing it is one line, dropping that point
  when it is under `MENU_FIRST_MIN_KM`, and it changes the menu, so it is
  left for the owner.
- **The 0.5 mi minimum stays.** The review's metric still catches 9 fallback
  plans and 17 menu plans: routes gaining 0.5 mi to 2 km for over 10% extra
  time. Raising the minimum to 2 km would move those. That is the owner's
  call, and both paths would need it.

## What changed

### The server (`server/app.py`)

1. **The guard counts beautiful km.** `_no_worse_than_fastest` falls back to
   the fastest route when the scenic one has a lower `mean_score` (as before)
   **or fewer `beautiful_km`**. It runs on every path that has a scenic search:
   the plain path, a menu option fetched by switch points, and the loop
   rejoin. A moving car's route changes only in the fewer-beautiful-km case.
2. **A plan needs the menu's minimum.** On the plain path, a plan whose scenic
   route gains less than `options.MENU_FIRST_MIN_KM` (0.805 km, half a mile)
   of beautiful road over the fastest gets the fastest. The constant is
   imported, not copied (`_worth_the_detour`).
3. **"A plan" is `options=1`, not "no heading".** This departs from the
   brief, which defined a plan as "no heading, no declined U-turn, not
   moving". That definition lets the minimum reach a moving car: the app
   sends a reroute **without** a heading whenever the fix has no course or
   the car is below 2 m/s (`NavigationModel.usableHeading`,
   `minSpeedForHeading = 2.0`), which is a car crawling out of a wrong turn or
   stopped at a light. The app's plans always send `options=1`
   (`RouteModel.fetchRoute`), its reroutes never do (`NavigationModel`'s four
   fetchers), and the server reads it whether or not the menu then runs, so
   it marks exactly the busy fallback. A heading or a declined U-turn still
   rules the minimum out, belt and braces.
   - Cost: an app build that predates `options=1` (before the menu, 2026-10-07
     builds and earlier) gets the guard but not the minimum on its plans.
     None of those are public.
4. **The contract: `"no_gain": true`** on the scenic Feature's properties,
   present only when the scenic arm **is** the fastest route because nothing
   gained the minimum, and absent otherwise.
   - Plain path: whenever the plan's fallback, or the guard on any path, put
     the fastest route in the scenic arm and the scenic search had gained
     less than 0.805 km. A guard fallback for a lower mean on a route that did
     gain the minimum carries no `no_gain`: the old sentence is still true
     there.
   - Menu path: when the default is the fastest and no frontier point gained
     0.805 km (`t_max <= 0`, an empty front, or a front whose best gain is
     under the minimum). Computed from `Plan.frontier`, the menu's own
     hop-stat gains (Trap 4); `pipeline/options.py` is unchanged.
   - Never at pref 0 (the driver asked for the fastest), and never for a menu
     whose default is the fastest only because every option is over the 25%
     budget: those options are still on the dial (Trap 3).
   - Never on the fastest Feature.

### The app

- `RouteProps.no_gain: Bool?`, optional like every field added since the app
  first shipped. An older build's `RouteProps` has no such property, and
  synthesised `Decodable` skips keys it does not declare; a test decodes a
  route carrying both `no_gain` and a key no build knows.
- `RouteComparison.noGain`, and `summary` for the same drive reads
  "**No beautiful road** worth the detour on this trip." when it is set,
  "**Same as the fastest route** at this setting." otherwise. `summary` is
  what VoiceOver reads for the same drive.
- The headline under the continuous slider (`DirectionsView.readout`, the one
  place that branches on `isSameDrive`) reads "No beautiful road worth the
  detour" when it is set, "Same as the fastest route" otherwise. With a menu
  of more than one option the dial shows instead and neither is reached; a
  menu carrying `no_gain` has only the fastest on it unless its one option
  gains under half a mile (see the measurement).
- **"Start driving" drives the scenic arm**, `model.startNavigation(response.scenic)`
  (`DirectionsView.swift:65`), which is now the fastest route. Confirmed by
  reading, not by a drive. Its `pref` is `drivePref`: 0 on a menu's fastest
  detent, but the slider's own pref (0.5 by default) on the plain path, so a
  plain-path plan with `no_gain` is driven at 0.5 and its reroutes search
  scenic roads at 0.5, held to the guard only, as before.

## Tests

- `tests/test_low_scenery_fallback.py`, 45 cases on `processed-ne`: the
  decision on stand-ins (fewer km on every path, the lower mean, the minimum
  on a plan, never on a moving car, pref 0), the busy fallback on the real
  graph (Hancock -> Shutesbury at pref 0.25 gains 21.4 -> 21.9 km for no
  extra time, and now gets the fastest with `no_gain`), the same request
  without `options=1` keeping its small gain, `options=1` with a heading
  identical to without, no route anywhere with fewer beautiful km than the
  fastest, and the menu's three cases (gain, over budget, nothing reaching
  the minimum).
- Mutations, each re-run alone: removing the minimum fails 15 tests; removing
  the beautiful-km half of the guard fails 1 (the stand-in: no New England
  trip in the set has fewer km); planning on "no heading" instead of
  `options=1` fails 1 (`test_a_reroute_keeps_a_small_gain`); dropping the
  menu's frontier check fails 1 (`test_over_budget_is_not_no_gain`).
- `tests/test_api.py`'s stand-in `Arm` gained a `beautiful_km`.
- iOS `RouteComparisonTests`: the new sentence, the old one without the
  field, the field ignored on a different drive, and decoding.

Results on this branch, 2026-10-25:

- `pytest tests/` on `processed-ne`: **1454 passed, 14 skipped**.
- `tests/test_national_routes.py` with `SUNDAYDRIVE_PACK=data/pack-us`:
  **11 passed**.
- iOS (`xcodebuild test`, iPhone 17 Pro, iOS 26.4, no local API so the live
  tests skip): **541 run, 47 skipped**. The only failing test is the known
  `DriveReplayTests.test_no_recorded_drive_hears_the_same_maneuver_twice`,
  with two assertions.

## The measurement

`tools/low_scenery_fallback/`: `sample.py` draws the trips (seed
**20261025**, in `trips.json`), `measure.py` sends them one at a time,
`analyze.py` writes `results/analysis.txt` from the three JSONL files in
`results/`. Run 2026-10-25 on this Mac, one national server at a time on
`data/pack-us` + `data/processed-us`, each stopped by its PID. **The
measurement waited for the slot.** The pre-deploy audit's national server
(PID 1996, port 55641) was running when the code was ready, so the runner
waited for it to exit before starting its own, and sent it no requests. The
code and tests were committed first (6dc157a). The three phases then ran from
01:29 to 01:32, with nothing else on the Mac computing routes:

| file | code | `SUNDAYDRIVE_ROUTE_OPTIONS` | modes |
| --- | --- | --- | --- |
| `before.jsonl` | `ea87a2a` | 1 | `menu` (options=1), `plain` (none) |
| `after.jsonl` | this branch | 1 | `menu`, `plain` |
| `after-busy.jsonl` | this branch | unset | `menu`: options=1 sent, the menu not run |

- **The busy fallback is measured directly.** It is `options=1` on a server
  whose menu doesn't run, which is what an overlapping plan gets. With the
  flag unset that happens on every request, deterministically, with no
  concurrency to arrange. Before the change it is the same code as `plain`.
- **Every menu request ran alone.** Requests were strictly sequential, and
  all 134 `menu` replies in `before` and `after` carry `options`.
- **The trips.** Both ends of a random trip are routing-slot tails drawn by
  road length, 40-160 km apart in a straight line. The named trips use city
  centres. The review recorded no destinations for its three fewer-km starts
  (NV 40.58,-119.30; WA 45.87,-121.56; ID 43.21,-115.36), so each got three
  seeded random destinations. None of those nine reproduced a fewer-km
  route. Five random trips did, and all five now get the fastest route on
  both plain paths. Four show it at the reply's rounding (r000: +19 min for
  0.8 -> 0.6 km, with the mean score up from 0.54 to 2.63; r002, r003,
  r118). r047 has fewer km unrounded and reads 0.8 -> 0.8.
- **No request failed**, on any path.
- **Trap 4 holds.** On all 268 menu replies, the menu's hop-stat
  `beautiful_km` and `RouteResult.beautiful_km` agree exactly at the 0.1 km
  the reply rounds to, for the fastest arm and for the default.
- **The one "under 0.5 mi" fallback after the change** is r061, which reads
  0.4 -> 1.2 km. Both values are rounded to 0.1 km in the reply. The server
  compares unrounded values, so the real gain is at least 0.805.

### All five paths

| | before menu | before plain | after menu | after busy fallback | after plain (no options) |
| --- | --- | --- | --- | --- | --- |
| scenic arm is the fastest | 37 | 8 | 37 | 62 | 13 |
| ... with `no_gain` | - | - | 27 | 62 | 6 |
| offered, gaining < 0.5 mi | 16 | 55 | 16 | 1* | 50 |
| offered, > 10% time for < 2 km | 17 | 29 | 17 | 9 | 27 |
| offered, fewer beautiful km (at 0.1 km) | 0 | 4 | 0 | 0 | 0 |
| offered, > 25% extra time | 0 | 49 | 0 | 41 | 49 |
| extra min p50 / p90 / max, all | 10.6 / 30.5 / 54.9 | 15.9 / 65.1 / 163.5 | same as before | 3.4 / 65.1 / 163.5 | 15.3 / 65.1 / 163.5 |
| extra min p50 / p90, where offered | 16.1 / 32.7 | 17.7 / 65.5 | same | 35.2 / 80.5 | 18.4 / 65.8 |
| beautiful km gained p50 / p90, where offered | 4.8 / 40.2 | 1.7 / 47.6 | same | 9.5 / 80.1 | 1.9 / 48.1 |

\* r061, rounding (above). "Offered" means the scenic arm is a different
route from the fastest.

- **After plain (no options)** is what reroutes without a heading, and app
  builds older than the menu, get: the guard only. It moved on the 5
  fewer-km trips, which now fall back to the fastest with `no_gain`. The
  sixth `no_gain`, r089, was already the fastest under the old mean guard
  and now carries the reason.
  Reroutes *with* a heading were not sampled: the guard is the only change
  there, and the tests cover it.
- **The menu's 37 fastest defaults** split into 27 `no_gain` (nothing on the
  frontier reached 0.5 mi) and 10 over budget, with an option gaining 0.5 mi
  or more on the dial. That is Trap 3, and those 10 correctly carry nothing.

### The review's named trips (pref 0.50, the app's weights)

| trip | fastest | before: plain | after: busy fallback | menu default |
| --- | --- | --- | --- | --- |
| Wichita -> Salina | 69 min, 0.0 km | 77 min, 0.0 km | fastest, `no_gain` | option 1 |
| New Orleans -> Baton Rouge | 69, 0.0 | 110, 0.0 | fastest, `no_gain` | option 1 |
| Chicago -> Milwaukee | 81, 0.0 | 99, 0.0 | fastest, `no_gain` | option 2 |
| Atlanta -> Chattanooga | 94, 0.0 | 179, 9.7 | unchanged: 179, 9.7 | option 3 |
| Denver -> Estes Park | 82, 17.2 | 92, 17.8 | fastest, `no_gain` | fastest, over budget |

- The review's own minutes differ: Wichita -> Salina was +54% there and is
  +12% here. The review probed without the app's weights, which the
  national-copy unit found moves these numbers. Every figure here uses the
  app's weights.
- Atlanta -> Chattanooga still costs +85 min for 9.7 km. It clears the
  minimum, so only a time budget would change it.

### The fallback's over-budget routes (the owner's number)

On the 41 trips where the busy fallback still offers a route costing more
than 25% extra time:

| | p10 | p50 | p90 |
| --- | --- | --- | --- |
| extra minutes | 29.5 | 51.6 | 85.0 |
| extra share | 29% | 49% | 94% |
| beautiful km gained | 1.9 | 22.0 | 98.0 |
| the menu's default on the same trip, extra minutes | 7.1 | 20.7 | 31.4 |
| the menu's default on the same trip, km gained | 0.9 | 7.3 | 38.6 |

- 5 of the 41 gain under 2 km, and 10 gain under 5 km.
- The median rate is 24 beautiful km per extra hour.
- The menu would default to the fastest on 3 of them.
- So most of these are real scenic drives at a price the menu won't open on,
  not empty detours. A budget would turn them into the menu's
  cheaper option only if the fallback had a menu, which it doesn't. A budget
  on the fallback would return the fastest route on all 41.

## Follow-ups, not done here

- **The menu's sub-minimum default** (13 of 134 plans, above). An owner
  decision; the fix is in `pipeline/options.py`'s `chosen` loop.
- **A time budget on the fallback** (41 of 134). An owner decision.
- **`server/DEPLOY-oracle.md` Part 8's unit has no
  `SUNDAYDRIVE_ROUTE_OPTIONS=1`.** The box has it (`docs/route-options.md`),
  and `deploy-oracle.sh`'s drop-in keeps it. A box rebuilt from the guide
  would run every plan through the fallback, which is now the safer of the
  two but has no budget.
- **The 2026-10-23 fewer-km trips were not reproduced exactly**: their
  destinations were not recorded. Four other random trips had the defect,
  and none do now.
