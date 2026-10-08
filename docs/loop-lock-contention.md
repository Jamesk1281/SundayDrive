# Loop planning no longer starves driving traffic (K-1)

**Status:** built 2026-10-08 on `claude/loop-lock-contention`, against `main`
at `8ad257f`, and merged into `main` the same day. Not deployed. In `server/app.py`, `REJOIN_LOCK`,
`LOOP_WAIT_SLOT` and `LOOP_BUSY_WAIT_S = 5.0` are the fix. In
`ios/Sources/RouteService.swift`, `ServiceError.busy` and `.timedOut` are the
client's half. The dispatch brief, `docs/loop-lock-contention-brief.md`, is
committed with this work and deleted when it merged
(`git show 8dbb728:docs/loop-lock-contention-brief.md`). This document is
what outlives it. Code comments and tests cite this file, and its section names.

Review finding K-1 (`pre-submission-review-verdict.md`): one `LOOP_LOCK`
wrapped every loop build and also the mid-drive loop rejoin, and queued builds
held all four of waitress's threads. Measured here before the fix, with four
clients planning loops: a driver's rejoin took **×7–8** its idle time, a
default route **×13–29**, and a fastest-only route **×70–129**. After it:
**×1.2–1.3**, **×0.9–1.8** and **×1.2–4.5**. No driving request took longer
than 2.6 s.

## What was built

### The server (`server/app.py`)

1. **The rejoin has its own planner and lock.** `REJOINER = LoopPlanner(ROUTER)`
   and `REJOIN_LOCK`, used only by the `via` branch of `_route`. A driver who
   missed a turn on a loop now waits only for another driver's rejoin. It still
   runs inside `api_route`'s `with _computing()`, so `IN_FLIGHT` counts it and
   the route options' busy guard gives way to it. `_not_alone()` also reads
   `REJOIN_LOCK.locked()`, as belt and braces, alongside `LOOP_LOCK.locked()`.
2. **A loop build is refused rather than queued.** When a build is already
   running, `/api/loop` answers **503** with
   `{"error": "Busy planning other drives. Try again in a moment."}`
   (`LOOP_BUSY`). See "The wait" for the one exception.
3. **Cached loops are never refused.** `LOOP_RESULTS` has its own
   `LOOP_RESULTS_LOCK`, and `_loop` checks it before trying the build lock. It
   checks again once it holds the lock, because the build it waited for may
   have been the same request sent twice.
4. **Nothing on `/api/route` is ever refused.** Rejoins, ordinary reroutes,
   "switch to fastest" and option fetches by switch points always compute.

### The wait

`_acquire_loop_lock()` takes the build lock at once if it is free. Otherwise
one request, and only one, may wait for it in `LOOP_WAIT_SLOT`, for up to
`LOOP_BUSY_WAIT_S = 5.0` seconds. Every other request is refused at once.

The first version waited 1.5 s and let any number of requests wait. The
double-tap measurement below refused **32 of 32** second requests from one
person. That person releases the distance slider, then releases it again
while their first loop is still building. A cold build on the New England
graph took a median **2.4–4.9 s** here (p90 up to 5.3 s), so a 1.5 s wait
expires before the first build is done. A longer wait open to everyone would
bring K-1 back: each waiter holds one of waitress's four threads. With one
waiting slot, a build and a waiter hold at most two threads, so two are left
for drivers however many people tap Loop. With the slot and 5 s, **0 of 64**
second requests were refused, and each was answered in 2.6–4.1 s.

### The client (`ios/Sources`)

- **`ServiceError.busy(String)`.** `RouteService.failure(status:body:)` maps a
  503 carrying our JSON `error` to `.busy`, checked before `.server`. A 503
  without our JSON is a tunnel or a proxy, and stays `.unreachable(503)`. Its
  words are the server's.
- **`ServiceError.timedOut`.** `RouteService.failure(_:)` maps
  `URLError.timedOut` to "The routing service didn't answer in time. Try again
  in a moment." It says neither "check your network" nor "busy", because a
  weak signal and a loaded server both end here. Every other `URLError` is
  still `.offline`.
- **The loop page's sector fallback does not fire on busy.**
  `LoopModel.fetch` catches only `.server`, so `.busy` falls through to the
  error text. The direction is kept, and no second request is sent.
- **Mid-drive, busy and timed out are requests that did not land.**
  `NavigationModel.classify` already made everything but `.server` a `.lost`.
  So neither one climbs `consecutiveReroutes`, and neither puts words under the
  trip card. The banner reads "No connection" with a path, and "No signal"
  without one, as `docs/mid-drive-recovery.md` decided. `traceDetail` writes
  `error_class` `busy` (status 503) and `timed_out`. A timeout used to be
  written as `offline`. The trace record section of `mid-drive-recovery.md`
  lists both.

**Builds already installed** see a 503 with JSON as `.server(message)`. On a
compass tap with a remembered direction, `LoopModel` then asks once more with
no sector, and that second request is most likely refused too, so the user
reads the busy words. That is one extra cheap request, and nothing mid-drive,
because only loop builds are refused.

### Tests

- `tests/test_loop_lock.py` (9 tests):
  - a rejoin is not blocked by a running build, and is never refused;
  - nor are a reroute or "fastest";
  - a second build gets 503 with the JSON error;
  - only one request waits, and the rest are refused at once;
  - a build that ends inside the wait is waited for;
  - a cached loop is served while another build runs;
  - `_not_alone()` sees a running build and a running rejoin, and a plan
    asked for while a rejoin runs gets no options.
- iOS:
  - `RouteServiceErrorTests` (5): 503+JSON is busy, 503 without JSON is
    unreachable, any other status with JSON is still `.server`, a timeout has
    the new words, and other `URLError`s are still `.offline`.
  - `LoopModelTests.test_a_busy_server_does_not_fire_the_direction_fallback`.
  - Three new rows in `MidDriveRecoveryTests`' banner table: busy, timed out
    with a path, timed out without one.

**Mutations.** Five mutants of `server/app.py`, each run against
`tests/test_loop_lock.py`. See "Mutations" under "What it measured".

## What it measured

All on this Mac, 2026-10-08, 02:19–02:59 EDT. The owner chose Mac-only
timing; see "On the box". Every row below is the ratio of a loaded median to
the idle median taken just before it, on the same server. The probe and the
raw results are in `tools/loop_contention/`.

**Conditions.**
- Replicate 1 ran while the load average fell from about 230 to 5, and
  replicate 2 ran at a load average of 4–5.
- Another session's server loaded its graph during replicate 1 of `after`
  (02:38). Swap was 9–11 GB of 10–12 GB throughout.
- Idle times moved by up to ×2.5 between replicates (rejoin 2.8 s → 1.1 s),
  which is why only ratios are quoted.

**Method.**
- Driving requests:
  - the loop rejoin: Needham, through Dover, pref 1, which is what a loop
    drive sends;
  - a default route: Boston → Worcester, pref 0.5, with `options=1` as the
    app sends it;
  - a fastest-only route: the same trip at pref 0.
- Load: 1 or 4 threads post cold 40 km loops from seeded random graph nodes
  (seeds 7, 11, 13, 17), back to back, for 45 s. After a 503 a thread waits
  1 s before asking again.
- The driving rows are timed round-robin throughout, and each server is
  fresh.
- `before` is `main` at `8ad257f`. `after` is the final code (one waiting
  slot, 5 s). The 1.5 s, any-number-of-waiters version is reported only where
  it differs.

### Four clients planning loops

| request | options | before (rep 1 / rep 2) | after (rep 1 / rep 2) |
|---|---|---|---|
| loop rejoin | off | ×7.1 / ×8.4 | ×1.30 / ×1.26 |
| route, default | off | ×29 / ×16 | ×1.84 / ×1.69 |
| route, fastest only | off | ×70 / ×129 | ×4.5 / ×1.37 |
| loop rejoin | on | ×7.0 / ×6.7 | ×1.32 / ×1.20 |
| route, default | on | ×13 / ×14 | ×1.07 / ×0.89 |
| route, fastest only | on | ×112 / ×121 | ×1.26 / ×1.17 |

The worst single driving request in the four 4-client "after" runs took
**2.6 s**. Before, they took 6–29 s, and only 1–3 of each row completed in
the 45 s window, against 19–20 after. One "before" default route took 29.0 s,
which the app would have reported as a failure at 20 s.

**The loop planners' outcomes** (4 clients, 45 s):

| | options off (rep 1 / rep 2) | options on (rep 1 / rep 2) |
|---|---|---|
| before: built | 5 / 32 | 36 / 29 |
| before: timed out (20 s) | **12** / 0 | 0 / 0 |
| after: built | 20 / 21 | 22 / 21 |
| after: busy (503) | 87 / 90 | 91 / 85 |
| after: timed out | 0 / 0 | 0 / 0 |

Fewer loops are built after the fix: about 21 against 29–36 at low load. That
is the intended trade. The driving requests now get the CPU, completing 19–20
rows per 45 s instead of 2–3. Each busy reply cost its client 1 s, by the
probe's design. At the higher load of replicate 1, the old code timed out 12 of
17 planners, so the queue failed the planners too, not only the drivers.

### One client planning loops

| request | options | before (rep 1 / rep 2) | after (rep 1 / rep 2) |
|---|---|---|---|
| loop rejoin | off | ×2.7 / ×2.7 | ×1.19 / ×1.29 |
| route, default | off | ×1.8 / ×1.7 | ×1.9 / ×1.8 |
| route, fastest only | off | ×1.2 / ×1.0 | ×1.3 / ×4.3 |
| loop rejoin | on | ×2.6 / ×2.8 | ×1.12 / ×1.26 |
| route, default | on | ×1.3 / ×1.4 | ×0.86 / ×0.97 |
| route, fastest only | on | ×1.15 / ×1.15 | ×1.14 / ×1.19 |

With one loop build at a time, ordinary routes never waited for the lock, so
their ratio is GIL sharing with that one build. The fix does not change it,
and is not meant to. The fastest-only route is the A\* arm in pure Python
(K-1's second paragraph). Its ×1.0–4.5 spread, across runs that should match,
is that GIL contention, and it is still open (see "For the owner", item 5).
With options on, the default route's ratio is at or below 1 under load. That
is the busy guard working: a plan that finds anything else running skips
options and costs less than the idle plan, which computed them.

### The rejoin's own planner: cold cost and memory

`tools/loop_contention/cold_rejoin.py` ran in-process, 5 replicates, each with
a fresh planner. A cold rejoin builds both cost models (pref 0 and pref 1), as
the first rejoin after a restart or with a new weight set does.

| | median |
|---|---|
| cold rejoin (two cost models built) | 1.20 s |
| warm rejoin | 1.12 s |
| cold / warm | **×1.07** |

A cost model costs about 40 ms to build. Before the fix, a rejoin queued
behind loop builds lost ×2.7 with one planner and ×7–8 with four. So the
brief's alternative was not needed for speed. That alternative is one
cost-model cache that both planners read, with a lock around only the dict get
and put. It was not built, because it means changing `LoopPlanner` itself. A
second planner leaves `pipeline/looper.py` untouched. The rejoin's models
also stay warm while loop builds with other weight sets churn the build
planner's two-entry cache.

The alternative would be safe: `_build` copies `w_slot` before it penalises
anything, so nothing mutates a cached model. It is the way to get the memory
below back if the box ever needs it.

**Memory.** One cost model on the New England graph holds **82.4 MB** of
arrays, not the ~30 MB that `LoopPlanner`'s docstring and the verdict assumed.
The docstring's figure was measured on the Massachusetts graph. The rejoin
planner's cache holds at most two, so the fix adds up to **165 MB**. On the box
that is 165 MB of the 3.4 GB available, beside a live process at 4.05 GB RSS
(2026-10-08, 04:52 UTC). The loop planner already holds the same two, plus its
field cache.

### Mutations

Each of five mutants of `server/app.py` was run against
`tests/test_loop_lock.py`.

All five were caught. The full backend suite, unmutated, is **777 passed**.

| mutant | what fails |
|---|---|
| the rejoin back under `LOOP_LOCK` | `test_is_not_blocked_by_a_running_loop_build`, `test_is_never_refused_as_busy` |
| the cache checked only under the build lock | `test_a_cached_loop_is_served_while_another_build_runs` |
| the `via` branch moved out of `_computing()` | `test_sees_a_running_rejoin` |
| a blocking acquire (queue, as before) | `test_is_refused_with_json_while_another_runs`, `test_only_one_waits_and_the_rest_are_refused_at_once` |
| no waiting slot (any number wait) | `test_only_one_waits_and_the_rest_are_refused_at_once` |

The iOS suite is 456 tests, 45 skipped (no server). `MidDriveRecoveryTests` 26,
`RouteOptionsTests` 10, `LoopModelTests` 20 and `RouteServiceErrorTests` 5
all pass. One test fails,
`DriveReplayTests.test_no_recorded_drive_hears_the_same_maneuver_twice`, on
the `drive-2026-10-06-122558` trace. It fails identically on unchanged `main`
at `8ad257f`, so it is not this work.

## On the box

SSH to `ubuntu@129.158.208.92` works. The box was not probed. At 04:52 UTC the
live API held 4.05 GB RSS of 7.9 GB, with 3.4 GB available. A second
graph-loaded process needs about 2.5–4 GB, enough to push the live service
into swap, and the owner chose Mac-only timing. Nothing on the box was
touched. The mechanism does not depend on the machine: the lock sharing and
thread starvation are in the code. The ratios would move, and so would the
wait (see "For the owner", item 2).

## For the owner

These are recommendations. None of them is changed here.

1. **The busy wording.** "Busy planning other drives. Try again in a moment."
   is the server's (`LOOP_BUSY`), and the app shows it as sent. It is true,
   and puts nothing on the phone. If you want it to read less like an error,
   one alternative is "Lots of people are planning drives right now. Try again
   in a moment."
2. **`LOOP_BUSY_WAIT_S` on the box.** The 5 s wait was sized to this Mac's
   cold builds (median 2.4–4.9 s, p90 up to 5.3 s). The box's cores are
   slower. After deploying, time a few cold 40 km loops on the box, then set
   the wait to about their p90. A longer wait costs only the one waiting
   thread, but the waiter's total time must stay well inside the app's 20 s.
3. **The 20 s client timeout: leave it.** After the fix, no driving request
   came within 17 s of it (the worst was 2.6 s), and no loop planner timed
   out. What reached it before was the queue, and the queue is gone.
4. **The rate limit (60/min per IP): leave it, or tighten it for `/api/loop`
   only.** A refused build costs the server almost nothing now, so the limit no
   longer has to bound loop cost. A separate, tighter rule for `/api/loop`
   would still stop one script from holding the single build slot. It would
   cost real users nothing, since a person cannot tap Loop ten times a minute.
5. **`threads=4`: leave it.** With one waiting slot, loop builds hold at most
   two threads, whatever the thread count. More threads would only let more
   requests share the GIL (`serve.py:9-15`). The remaining contention is the
   fastest-only route's pure-Python A\* against a running build (×1.0–4.5
   above). It is a separate item if it matters.
6. **Check that the tunnel passes an origin 503 through.** Cloudflare
   normally relays an origin's 5xx unchanged. If a custom 5xx page is ever
   configured, the app falls back to "The routing service isn't reachable
   right now. Try again in a moment. (HTTP 503)". That still doesn't blame the
   phone, and doesn't fire the sector fallback. One check after deploying:
   send two cold loop requests at once through the public URL, and see that
   the second comes back with the JSON body.
7. **Abandoned requests.** Waitress does not cancel a request whose client
   gave up. On the old code, a burst left the server computing loops long
   after their clients had timed out: one overloaded test server reached a
   task queue 94 deep and its connection limit, and answered `/api/health`
   in 60 s. Now at most one build and one waiter can be left behind. A
   `/api/route` whose client gave up still computes, but those are short.
