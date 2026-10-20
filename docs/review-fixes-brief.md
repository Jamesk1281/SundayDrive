# Fixing what the 2026-10-20 outside review found (brief)

**Status:** diagnosed, not fixed. Written 2026-10-20 in the master session.
Nothing has been touched for this. It is one brief for **four parallel units**:
R (router and server), D (data), I (the app) and P (deploy tooling). Each unit
reads "Common" plus its own section, works on its own branch off **`usa`**
(never `main`), and writes its own answer document, named in its section.

The brief is untracked. Each unit commits an unchanged copy with its work. It is
deleted in the merge that brings back the last of the four. **Never edit it,
never append results to it, and never cite it.**

The measurements below come from **the 2026-10-20 outside review**, an
independent pre-release critique of `usa` at `4f74951`. Its write-up stays out
of the repo by the owner's decision. Never look for it or cite it by path. Cite
this work's own answer documents instead. Every headline case was re-checked in
the master session on 2026-10-20, as noted.

## Common

### Decided by the owner (don't reopen)

- **No submission dates.** The app ships when it is ready. Nothing here asks for
  or works to a date. Report what is done and what is left, not when.
- **A ford on a paved major road does not close it.** A `ford=yes` node or way on
  a motorway, trunk, primary or secondary road (or their links) that isn't
  tagged unpaved is treated as a tagging error and left open. Fords on minor
  roads, and on unpaved roads of any class, stay closed as today (unit D).
- **Loops are capped by how much road their disc holds, not by one distance.**
  The top of the loop slider becomes the most this start can afford: 400 km
  where roads are sparse, less in dense metros (units R and I).
- The earlier decisions still stand:
  - the national, absolute scenery scale;
  - 500 km straight-line point-to-point (shown as **310 miles** everywhere, units
    R and I);
  - the 48 contiguous states and DC (never mention Alaska, Hawaii or
    territories);
  - the permit rule untouched;
  - the Oracle box.

### The contract between units

Write to it exactly. It is how R, I and P avoid each other's files.

1. **Error bodies.** Every JSON error from the server is
   `{"error": <a sentence: capital first letter, full stop>, "code": <string>, ...numbers}`.
   The codes:

   | code | meaning |
   | --- | --- |
   | `TRIP_TOO_LONG` | exists today |
   | `LEG_TOO_LONG` | a `via` leg over the cap |
   | `LOOP_TOO_LONG` | a loop over this start's limit; carries `max_km`, `km` |
   | `NO_ROUTE_NEARBY` | the search ran out of room; replaces the bare "no route found" |
   | `START_TOO_FAR` | a reroute whose start would be more than 500 m from the car |
   | `OUTSIDE_COVERAGE` | a point outside the 48 states and DC |
   | `BAD_INPUT` | non-finite or out-of-range numbers |

   Numbers are numbers, never strings. R writes them. I decodes them without
   assuming every field is a string.
2. **The loop limit.** `POST /api/loop/limit` with `from=lat,lon` in the body
   returns `{"max_km": <float>, "max_mi": <int>}`. Coordinates never go in the
   URL. A loop request over that limit gets 400 `LOOP_TOO_LONG` with `max_km`.
3. **Health.** `GET /api/health` keeps `status`, `nodes` and `routing_slots`, and
   adds:
   - `region` (the string the pack names, e.g. "the contiguous United States");
   - `commit` (a short SHA from an env var or a file the deploy writes, or null);
   - `pack` (the pack's fingerprint, or null).

   R adds the fields. P makes the deploy write the commit and check all three.
4. **Data files.** D does not overwrite `data/processed-us` or `data/pack-us` in
   place. R and I run servers on them while D works, and the server refuses a
   pack whose fingerprints no longer match the parquets beside it. D writes
   `data/processed-us-next/` (symlinks to the unchanged big parquets, real files
   for the tables it regenerates) and `data/pack-us-next/`. The master session
   swaps them at merge. **R does not change the pack's format.** If it must,
   R says so in its answer document and leaves the rebuild to the master session.

### Where things are

- `data/` exists only in the main checkout,
  `/Users/james./Desktop/myapps/SundayDrive`. Worktrees reach it by symlink.
  Never write into `processed-ne`, `processed`, `processed-us` or `pack-us`.
- **Disk is tight:** about 17 GB free on 2026-10-20, and `pack-us-next` needs
  about 12 GB. Keep logs and build products small. Delete your own derived
  data and simulators when done. Never copy `data/`.
- **Tests:** `SUNDAYDRIVE_DATA=/Users/james./Desktop/myapps/SundayDrive/data/processed-ne /Users/james./Desktop/myapps/SundayDrive/.venv/bin/python -m pytest tests/`.
  `usa` was 987 passed, 13 skipped, 0 failed on 2026-10-19.
- **National server:**
  `PORT=<free> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_PACK=…/data/pack-us SUNDAYDRIVE_DATA=…/data/processed-us .venv/bin/python server/serve.py`.
  It starts in under 25 s. Kill it by its own PID, never with `pkill`, and run
  one server of yours at a time.
- **No deploying, no pushing, and no ssh to the box.** That is the master
  session's job. The repo is public: no traces or home locations in commits.

---

## R. Router and server

**Answer:** `docs/review-fixes-router.md`. **Branch:** `claude/review-fixes-router`
off `usa`. **Owns:** `pipeline/router.py`, `options.py`, `looper.py`,
`server/app.py`, `server/serve.py`, and their tests. **Doesn't touch:**
`pipeline/common.py` or `closures.py` (D), `ios/` (I), `server/deploy-oracle.sh`
or `DEPLOY*.md` (P).

**1. A reroute from a closed stretch starts miles away (Blocker).** The review
drove I-10 westbound at 35 m/s through a closed edge (1470492, 16.3 km, closed by
a ford node). The reroute started 9.5 miles ahead, and the app showed "Off route ·
route 9.5 mi away / Head back to your route" under a U-turn arrow. The mechanism
is at `pipeline/router.py:2810-2812`, verified in the master session:
```python
e = int(self._edge_tree.nearest(point))
if self._shut_at(e, point):
    e = self._nearest_open(point, e)
```
That rule exists for a car standing beside a real gate (`docs/closed-roads.md`,
"Snapping"). It must stay for planning from rest. But a **moving** car (the
request carries a heading or `declined_uturn`) on a closed edge is evidently on
it: snap it there, aligned with its heading, and let the route leave that edge
forward. Then refuse, with `START_TOO_FAR`, any reroute whose snapped start is
more than 500 m from the fix. D's ford change removes this case on I-10. The
fix here is for every other wrong closure (there are 71,617 `closed_to_cars`
rows nationally).

**2. `via` skips the cap (Major).** `server/app.py:469`: `if via is None:`. Boston,
via Los Angeles, to Miami returned 200 in 46.3 s, a 10,054 km route, with RSS
peaking at 5.8 GB. While it ran, an ordinary route took 6.5 s and a loop rejoin
30.6 s, past the app's 20 s. Cap each leg as a trip is capped (`LEG_TOO_LONG`).
Never let a request's corridor become the whole national graph.

**3. Input validation (Minor).**
- `from=nan,nan`, `to=inf,…` and `from=91,…` return Flask's HTML 500.
- `pref=nan` and `w_coast=nan` are accepted silently.

Validate every number as finite and in range before any work (`BAD_INPUT`).

**4. False "no route found" (Major).** `CORRIDOR_WIDENINGS = 2`
(`pipeline/router.py:377`) gives up on a real but long detour. Andrew Molera to
Big Sur village, 4 miles on CA-1, returned `no route found`. That one is a ford,
but the general case remains. Widen until the corridor's allowance reaches the
cap's budget, then answer `NO_ROUTE_NEARBY` with a sentence.

**5. Loops capped by density.** Today `MIN_TARGET_KM, MAX_TARGET_KM = 5.0, 400.0`
(`pipeline/looper.py:191`). The developer's Mac measured 400 km loops at 17.7 s
from Philadelphia and 14.0 s from New York, about 25 s and 20 s on the box. Set
the per-start limit from the disc's node count, measured so a first loop's p90
stays at or under about 8.5 s Mac CPU (about 12 s on the box, whose cores are
about 1.4× slower). Expose it per the contract.

**6. Instruction text (Major).** Forty random national trips produced 4,899 steps:
- **5.2% carry raw multi-values,** such as "Continue onto I 295;US 1;ME 26" and
  "Turn left onto Acquoni Road;ᎡᏆᏂ ᎦᏅᏅ". Split them and announce the first ref
  (or "I-295 / US-1").
- **2.9% are exits with no number and no destination.** "Take the exit onto
  I 64" at Waynesboro, VA has no direction, and the fallback order is at
  `router.py:4237-4246`. Use `destination:ref`, `destination`, or the
  carriageway's bearing, to say "I-64 West".
- **1.8% have no road name:** a bare "Merge", "Continue" or "Keep left".

**7. Messages and health.**
- Every refusal becomes a sentence with a code. Today "no route found between
  those points" and the rest are lower case, at `server/app.py` 460, 571, 594
  and 670.
- `_too_far` (`server/app.py:133-138`) rounds 500 km to "311 miles". Say
  **310**, as the app does.
- Add the health fields from the contract.

**Traps:**
1. **Don't drop the snap rule for parked cars.** A start from rest beside a real
   gate must still begin on its own side (Crane Road, `docs/closed-roads.md`).
   Only a moving car may snap onto a closed edge, and only to leave it.
2. **New England parity still holds.** Re-run `tools/us_scale_router/parity_run.py`
   and `parity_diff.py` against the `usa` oracle. Explain every new difference,
   which should be limited to the error bodies and the cases above.
3. **The density cap is a measurement.** Replicate it, on a quiet Mac or with
   noise stated, and record the thresholds in your answer document.

**Done:** each item fixed with tests; parity re-run; the suite green; the national
server's latency and memory re-measured with `tools/us_scale_router/load_probe.py`;
`docs/review-fixes-router.md`.

---

## D. Data: the ford rule, and an audit of what closes major roads

**Answer:** `docs/review-fixes-data.md`. **Branch:** `claude/review-fixes-data` off
`usa`. **Owns:** `pipeline/common.py`, `pipeline/closures.py`,
`tests/test_closures.py`, a new `tools/national_audit/`, and a new
`tests/test_national_routes.py`. **Doesn't touch:** `router.py`, `app.py` (R) or
`ios/` (I).

**1. The ford rule (Blocker).** Verified in the master session against
`data/processed-us` on 2026-10-20:
- 26,301 ford rows in `closed_to_cars`, on 18,957 edges.
- On motorway, trunk, primary and secondary roads: **409 edges, 1,027.6 km**.
  Among them:
  - I-10 west of Tonopah, AZ (edges 1329618 and 1470492);
  - US-95 between Vidal Junction and Needles (44.4 km);
  - US-385 north of Marathon, TX;
  - US-62/180;
  - CA-1 near Andrew Molera.
- `data/processed-ne`: 102 ford rows and **0** on major roads.

What drivers get, on the national server:

| trip | planned | instead of |
| --- | --- | --- |
| El Paso → Carlsbad Caverns | 253.7 mi | about 150 mi |
| Needles → Blythe | 132.4 mi | about 95 mi |
| Carmel → Big Sur village | 136.3 mi | about 26 mi |

The rule is at `pipeline/common.py:107-113` (nodes) and
`pipeline/closures.py:545-546` (ways). Apply the owner's decision. "Unpaved"
means `surface` in `score.UNPAVED`, or an unpaved surface on the way that carries
the ford.

**2. Audit everything else that closes a major road.** List every
`closed_to_cars` and `seasonal_closures` row on motorway through secondary roads
nationally, by `kind` and `tag`, with totals and the 30 longest examples. Don't
change anything else. Report it, because the next mis-tag is in that list.

**3. A national route-correctness check, which needs no travel.**
- Write `tools/national_audit/` and `tests/test_national_routes.py`. The tests
  skip unless `SUNDAYDRIVE_PACK` is set.
- Take points about 50 km apart along major numbered routes in every region
  (interstates and US routes). The fastest route between them must stay on that
  route, or be no longer than 1.2× the distance along it.
- Run it on the current pack, before your change, and on `pack-us-next`, after.

**4. Rebuild the tables.**
- Rerun the national sidecars with your `closures.py` (`tools/national_build/sidecars.py`, about 3,700 s), into
  `data/processed-us-next/` per the contract.
  - `SUNDAYDRIVE_FEDERAL` must point at `data/raw/federal`, because the region
    PBFs live in `data/national/pbf`.
- Build `data/pack-us-next/` with `tools/us_scale_router/pack.py`. That takes
  about 7 minutes, peaks at 9–14 GB of RAM and writes about 12 GB.
- Rerun New England's `closures.py` into a scratch copy. Its `closed_to_cars`
  should be byte-identical to `usa`'s, since New England has no major-road fords.
  If it is not, explain why.

**Traps:**
1. **Don't open fords on unpaved or minor roads.** That is the case the rule
   exists for: a consumer car app should not plan a real ford.
2. **Don't overwrite `processed-us` or `pack-us` in place** (contract 4). R and I
   are using them.

**Done:**
1. The rule changed, with tests covering both sides of it.
2. The major-road audit.
3. The continuity check, before and after.
4. `processed-us-next` and `pack-us-next` built.
5. New England confirmed unchanged.
6. The suite green.
7. `docs/review-fixes-data.md`.

---

## I. The app

**Answer:** `docs/review-fixes-app.md`. **Branch:** `claude/review-fixes-app` off
`usa`. **Owns:** `ios/` only.

**1. The cap's message is thrown away (Major).** `ios/Sources/RouteService.swift:348-349`:
```swift
guard let message = try? JSONDecoder().decode([String: String].self, from: body)["error"]
else { return .unreachable(status) }
```
The server's `TRIP_TOO_LONG` body carries numbers, so the decode fails. Boston →
Chicago showed "The routing service isn't reachable right now. Try again in a
moment. (HTTP 400)".
- Decode `error` and `code` while tolerating other fields, and branch on `code`.
- Check the straight-line distance on the phone before asking.
- Mid-drive, `NavigationModel.swift` `classify` (around line 2155) must not turn
  a refusal into "No connection. Head back to your route."

**2. Spoken road names (Major).** `ios/Sources/VoiceGuide.swift:611` rewrites only
`MA|RI|NH|VT|ME|CT|US`. Extend it to every state's and DC's prefix, plus FM, CR,
SR and BIA. Keep requiring a number after the prefix, so "YMCA Drive" can never
become "Route CA" (`docs/voice-guidance-plan.md` §4).

**3. Directions starts from nowhere (Major).**
- With an empty Start, choosing a destination does nothing. Only a Recents row
  fills Start (`ios/Sources/HomeView.swift:158-159`). Default Start to My
  Location whenever location is allowed.
- Typing into a filled field edits the old text. "Santa Cruz Beach Boardwalk"
  became "Santa Cruz Beach R…". Select all on focus.

**4. The loop slider takes the start's limit** from `POST /api/loop/limit` (contract
2). It shows "up to N mi from here", and handles `LOOP_TOO_LONG`.

**5. Smaller ones.**
- Duplicate suggestions ("Santa Cruz Beach Boardwalk" three times).
- A refused destination is saved to Recents.
- With location off, the Loop screen says "allow it in Settings" with no button
  that goes there.
- Every miles figure for the cap reads 310.

**6. The first screen.** "Before you drive" (`ios/Sources/BeforeYouDriveView.swift`)
leads with six negatives and no statement of what the app does. Its "Driven in New
England only…" line tells 96% of the country the app is untested where they are.
- Lead with one line on what the app does.
- Keep the route-guidance notice the custom EULA requires, verbatim.
- Put the limits in plain words.
- Drop the junction-approach statistic.

Record every string you change in your answer document.

**Traps:**
1. **The simulator lies.** Use `simctl location start` playback, not `set`.
   `xcodebuild test` takes `TEST_RUNNER_` variables, not `SIMCTL_CHILD_`. Use
   `-destination id=`, never `name=`, and never pipe `xcodebuild` through `tail`.
   Create your own device and delete it after.
2. **The server may not have R's codes yet.** Build to the contract, test against
   a local server on R's branch when it exists, and against `usa` meanwhile. The
   app must still read the old bodies.

**Done:** each item fixed; the iOS suite run against a local national server (`usa`
was 488 tests, 36 skipped, 0 failures); `docs/review-fixes-app.md`.

---

## P. Deploy tooling for the national server

**Answer:** `docs/review-fixes-deploy.md`. **Branch:** `claude/review-fixes-deploy`
off `usa`. **Owns:** `server/deploy-oracle.sh`, `server/DEPLOY-oracle.md`,
`server/DEPLOY.md`, `server/Dockerfile`. **Doesn't touch:** `server/app.py` (R).

**What is known.**
- `server/deploy-oracle.sh:17`: `MONITOR_KEYWORD=794685` (New England's node
  count), and `:40` defaults the data to `data/processed-ne`.
- Nothing copies a pack or sets `SUNDAYDRIVE_PACK`. The systemd unit in
  `server/DEPLOY-oracle.md` (around line 401) sets only
  `SUNDAYDRIVE_DATA=.../processed-ne`.
- A correct national deploy would fail the script's own node check.
- The box is `VM.Standard.A1.Flex`, 2 OCPU and 8 GB. The owner may resize it to
  the 12 GB Always Free ceiling.
- The boot volume is 50 GB. The pack is about 12 GB, and `processed-us` 7.3 GB.

**Make the deploy national:**
- Ship the pack and the processed directory, each verified by checksum.
- Set `SUNDAYDRIVE_PACK` and `SUNDAYDRIVE_DATA` in the unit.
- Write the commit for `/api/health` (contract 3).
- Check `region`, `nodes`, `commit` and `pack` after restart, instead of a
  hard-coded count.
- Print the UptimeRobot keyword the owner must set.
- Keep a `--dry-run` that changes nothing.
- Document a box memory check (anonymous memory, swap, the pack's page cache),
  and the 8 → 12 GB resize steps for the owner.
- The Docker path cannot start: it lacks `looper.py`, `options.py` and pack
  support, and copies `data/processed`. Remove Option B and the Dockerfile.
  Oracle is the only origin (`server/DEPLOY-oracle.md`, Part 10).

**Traps:**
1. **Never run it for real.** No ssh, no copy to the box. Exercise it with
   `--dry-run`, plus a local fake target if you build one.
2. **The New England deploy must still work** from `main`, and by flag from `usa`.
   Don't break the box's current service path.

**Done:** the script, unit and docs; a dry-run transcript; `docs/review-fixes-deploy.md`.
