# Brief: K-1, loop planning starves driving traffic

**Status: diagnosed and decided, not fixed.** Written 2026-10-08 against
`main` at `012a5f3`, which includes the route options and their busy guard.
Nothing has been touched. **This brief is temporary, and the merge that brings
the work back deletes it** (`docs/briefs.md`).

The answer goes in a new `docs/loop-lock-contention.md`, plus the code and
tests. Update K-1's line in the status block at the top of
`docs/pre-submission-review-verdict.md`. Never append results to this file,
and never cite it from code or tests.

## 1. The finding, as measured

K-1 is in `docs/pre-submission-review-verdict.md`, under "K-1". It was
measured on a local server on 2026-09-30, at a load average of up to 114, so
the figures are ranges:

| request | idle | 1 client planning loops back to back | 4 clients |
|---|---|---|---|
| loop rejoin (`via`, a driver mid-drive who missed a turn on a loop) | 0.95–2.9 s | ×1.9–×3.1 | **×7.5** (median 7.2 s, max 10.6 s) |
| route, default pref | 0.34–0.93 s | ×1.1 | **×25** (8.5 s) |
| route, fastest only | 0.08 s | ×3.6 | not run |

The app gives up after 20 s (`ios/Sources/RouteService.swift:95`,
`timeoutIntervalForResource = 20`). The marketing plan's success case, one
clip that takes off, looks to the server like many people tapping **Loop** at
once. It is a launch-day problem, not an App Review one.

## 2. The mechanism

All references are to `main` at `012a5f3`.

- **One lock for three jobs.** `LOOP_LOCK = threading.Lock()` is at
  `server/app.py:151`. It is held across:
  - every loop build, including the cache lookup (`_loop`, `:544`),
  - the cache store (`:595`), and
  - **the mid-drive loop rejoin**, the `via` branch of `_route` (`:406`):

    ```python
    with LOOP_LOCK:
        fastest = LOOPER.resume(s, w, t, 0.0, weights, avoid_unpaved, on=day)
    ```

  So a driver's rejoin queues behind everyone's "Try another direction". The
  lock exists because `LoopPlanner`'s cost-model and field caches are plain
  dicts (`pipeline/looper.py:319-320`). `resume` (`:422-462`) reads the same
  `_cost(...)` cache that `plan` fills.
- **Queued loops hold waitress threads.** `serve.py:44` runs
  `serve(app, ..., threads=4)`. Four loop requests waiting on the lock occupy
  all four threads. An ordinary `/api/route`, which never takes the lock,
  then waits for a thread. That is the ×25 for routes: thread starvation,
  not lock contention.
- **The client blames the driver.** In `RouteService.send` (`:277-279`),
  `catch is URLError` → `.offline` → "No connection to the routing service.
  Check your network." (`:75-76`). A server that took 20 s is reported as
  the phone's fault in planning.

  Mid-drive this does not apply: `NavigationModel.classify` turns a timeout
  with a network path into `.lost(.serverUnreachable)`, "No connection"
  (`docs/mid-drive-recovery.md`). That was decided, so leave it alone.
- **The route options already have a busy guard.** It is `IN_FLIGHT` /
  `_computing()` / `_not_alone()` at `server/app.py:164-193`
  (`docs/route-options.md`, "The busy guard"). Options compute only when
  nothing else is running, and abort between phases when anything arrives.
  `_not_alone()` reads `IN_FLIGHT > 1 or LOOP_LOCK.locked()`.

## 3. What to build

This is the verdict's "cheapest fix", items 1–4, made concrete. The verdict
estimates about 30 lines for 1–3.

1. **Give the rejoin its own planner and lock.**
   - Add a second `LoopPlanner(ROUTER)` with its own lock, used only by the
     `via` branch.
   - It costs one more cost-model cache. The verdict estimates about 30 MB;
     measure it on the box's graph.
   - A driver's rejoin then waits only for another driver's rejoin.
   - **Measure the cold-cache cost.** The first rejoin for a given
     (pref, weights, avoid_unpaved, day) now builds its own cost model,
     where it used to find the one the loop build left behind. Report cold
     against warm.
   - If cold is much worse than today's queueing, the alternative is to make
     the cost-model cache safe to read concurrently (a small lock around
     the dict get/put only, never around the search). Say which you chose
     and why.
2. **Refuse rather than queue, for loop *builds* only.**
   - When a loop build is already running, `/api/loop` returns **HTTP 503**
     with `{"error": "Busy planning other drives. Try again in a moment."}`
     (or similar words), instead of holding a thread on the lock.
   - Use a non-blocking or short-timeout acquire. The common case is one
     user tapping the compass twice: if they hit busy noticeably often, a
     short wait (about one loop's time) is the fix. Measure it.
   - **Cache hits must never be refused** (§4 trap 3).
3. **Have the client recognise busy and say so.**
   - In `RouteService.send`, add a case such as `ServiceError.busy(String)`
     for HTTP 503 carrying a JSON `error`, checked before the generic
     `.server` mapping.
   - `LoopModel.fetch`'s sector fallback (`ios/Sources/LoopModel.swift:277`)
     must **not** fire on it (§4 trap 2).
   - `NavigationModel.classify` must treat it as a request that did not
     land (`.lost(...)`), never as `.server`. Nothing mid-drive should
     receive it (item 2 is loops only, and `via` has its own lock). This is
     belt and braces.
   - Add the new case to `traceDetail`'s switch (an exhaustive switch, so
     the compiler will insist). If it adds an `error_class` value, list it in
     `docs/mid-drive-recovery.md`'s trace record section.
4. **Tell timeouts apart from no connection, in planning.**
   - `URLError.timedOut` gets its own case and words, such as
     "The routing service didn't answer in time. Try again in a moment."
   - **Not "busy".** A weak signal times out too, and blaming the server for
     the phone's signal is the same misattribution in reverse.
   - The other `URLError`s stay `.offline`.
5. **Measure.**
   - Rerun the verdict's probe (its "Reproducing this", step 6) before and
     after, as **ratios to idle**, never absolute times. Other sessions load
     this Mac.
   - Rows: the loop rejoin, a default-pref route, and a fastest-only route,
     each under 1 and 4 clients planning loops. Also count the 4-client loop
     planners' outcomes: built, busy, timed out.
   - Run it with `SUNDAYDRIVE_ROUTE_OPTIONS=1` too, because options are on
     in production.
   - **On the box:** if `ssh -i ~/.ssh/scenic_oracle ubuntu@129.158.208.92`
     works, run the probe against a **second** process there on a free
     localhost port, never the live service and never the public URL. If SSH
     does not work, say so. Do not deploy or restart the live service; the
     owner deploys.
6. **Tests.**
   - Backend, in `tests/`: a rejoin is not blocked while a loop build holds
     the loop lock; a second loop build gets 503 with a JSON error while one
     runs; a cached loop is served while another build runs; `_not_alone()`
     still sees a running loop build and a running rejoin, so options still
     abort for a driver.
   - iOS: 503+JSON → `.busy` with the server's words; a timeout → the new
     words; the loop page's sector fallback does not fire on busy; `classify`
     maps busy to `.lost`.

## 4. Traps

1. **A mid-drive request must never get a refusal.** Since `c97b126`, any
   JSON `{"error"}` is `.server(message)`, which `NavigationModel.noteFailure`
   books as an *unhelpful success*:
   - `consecutiveReroutes += 1`, which climbs the 8 s → 120 s backoff, and
   - the message is shown under the trip card.

   So a "busy" sent to a driver's reroute makes them wait up to two minutes
   for the next try, with "Busy planning other drives" on the screen.
   Refusal is for `/api/loop` builds only. Rejoins (`via`), ordinary
   reroutes, "switch to fastest" and option fetches by switch points always
   compute.
2. **The loop page's sector fallback turns busy into a second request.**
   `LoopModel.fetch` catches any `.server(_)` on a compass tap and at once
   re-asks with no sector (`LoopModel.swift:277-283`). Mapped as `.server`, a
   busy reply would instantly fire another loop request into the same busy
   server, and if that one got through, show a loop in a direction the user
   didn't ask for. That is why busy needs its own case.
3. **Don't refuse cache hits.** `_loop` does its cache lookup under the same
   lock as the build (`:544-548`). The cache exists for the common case:
   going back to the direction you liked costs nothing. Refusing the whole
   function when the lock is held throws that away for every user whenever
   anyone builds. Put the result cache under its own small lock (or check it
   before trying the build lock), so only a real build can be busy.
4. **Keep the rejoin inside `_computing()`, and keep `_not_alone()` honest.**
   The options' busy guard is what stops options delaying a driver. It counts
   requests through `IN_FLIGHT` and also reads `LOOP_LOCK.locked()`. Once the
   rejoin has its own lock, `_not_alone()` must still be true while a rejoin
   runs: it already is through `IN_FLIGHT`, as long as the `via` branch stays
   inside `api_route`'s `with _computing()`. Don't move the rejoin out of it,
   and don't make `_not_alone()` read only the new lock.
5. **More threads is not the fix.** Raising `threads=4` lets more requests
   start, but routing holds the GIL, so they all finish later. It also lets
   more loop builds queue. The verdict and `serve.py:9-15` both say routing
   does not parallelise.
6. **Don't change the 20 s client timeout, or the rate limit, here.** Both
   are levers on the same symptom with their own costs (the timeout was
   chosen for mid-drive recovery, `RouteService.swift:85-91`). If the
   measurements say one should move, write it in the answer document as a
   recommendation for the owner.

## 5. Build and test

- Work on a branch off current `main` (`012a5f3` or later), never on `main`.
  This brief may be untracked in the master worktree
  (`release-readiness-check-a285aa`). Copy it into yours and commit it with
  the work.
- **Parallel sessions.**
  - A wrong-way time-out session is editing `NavigationModel.swift` (the
    wrong-way section, `noteFailure`'s voice guard, and the banner).
    Touch only `classify` and `traceDetail` there.
  - A recent-destinations session may be in the planning views.
  - After merging, rerun `MidDriveRecoveryTests` and `RouteOptionsTests`. A
    conflict-free merge proves nothing here.
- Data lives in the main checkout:
  - Backend suite:
    `SUNDAYDRIVE_DATA=/Users/james./Desktop/myapps/SundayDrive/data/processed-ne /Users/james./Desktop/myapps/SundayDrive/.venv/bin/python -m pytest -q tests`.
    The NE baseline is green, so a red there is yours.
  - A local server:
    `PORT=<free port> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<same> <same python> server/serve.py`.
    It takes a while to load the graph. Kill it by its own PID only, never
    with a broad `pkill`, because other sessions run servers too.
- iOS: `cd ios && xcodegen generate`, then
  `xcodebuild test -project SundayDrive.xcodeproj -scheme SundayDrive -destination 'id=<a simulator you created>'`.
  Use `id=`, not `name=`, and never pipe it through `tail`. About 33 tests
  skip with no server.

## 6. Done looks like

1. Items 1–4 of §3 built, with item 6's tests. Backend and iOS suites green
   apart from the usual skips.
2. The probe before and after, as ratios, with and without options, written
   into `docs/loop-lock-contention.md`, plus the box run, or why there isn't
   one.
3. The cold-rejoin cost and the extra memory, measured.
4. K-1's line in the verdict's status block updated.
5. Anything the measurements say the owner should decide (busy wording, the
   client timeout, the rate limit, the box's thread count) listed in the
   answer document as a recommendation, not changed.
6. Or, if a part can't be done as specified, a statement in the answer
   document of why, with the measurement.
