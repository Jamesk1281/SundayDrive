# Mid-drive recovery: lost server, lost signal, wrong way, offline rerouting — brief

**Status: diagnosed, not designed.** Nothing has been touched. Written
2026-10-05 against `main` at `191e15c`. Every code claim below was re-read
against the source that day.

This is a **design study**. The deliverable is a plan for the owner to choose
from: options, measurements, costs and a recommendation. It changes no source
code. The answer goes in `docs/mid-drive-recovery-plan.md`. This brief is
deleted when that plan merges, so nothing may cite it.

## The question

An outside review on 2026-10-05 raised two findings. Behind them is a general
question.

1. **P-04.** A drive that loses its server or its signal goes quietly stale.
2. **P-05.** Driving the wrong way along the route never reroutes, and the
   banner points behind the driver.
3. **In general:** what should Sunday Drive do mid-drive when it cannot reach
   its server? And should it be able to reroute without one?

The owner wants to know how to solve these, with the options ranked and costed.
The plan must split the work in two:
- what can go in before App Store submission (the planned launch is
  2026-10-22, per `docs/marketing-plan.md`);
- what waits until after.

## What is measured

**P-04** (outside review, simulator):
- **Setup.** On a Concord→Rockport drive, 1.8 km in, the reviewer stopped the
  backend and drove off the route onto Hawthorne Lane.
- **What the driver saw.** The banner kept "1.4 mi · Continue onto North Great
  Road", an instruction for the abandoned line. The footer said "Off your
  route". Nothing said the reroute had failed, and the voice was silent.
- **How long.** It lasted until the server came back, and the backoff retry
  succeeded 17 s after that.

**P-05** (outside review, simulator, and the repo's own end-to-end harness):
- **Setup.** On a Concord loop, the reviewer drove the route line backwards for
  about a minute.
- **What the driver saw.** The footer said "Off your route". The banner kept
  "Continue onto Concord Road", a maneuver behind the car, with its distance
  growing from 0.2 to 0.5 mi.
- **No reroute.** None was requested until the car left the line onto Route 2,
  according to the proxy log.
- **The harness fails.** The opt-in suite (`TEST_RUNNER_SUNDAYDRIVE_E2E=1`, a
  slice of 8 pairs, local server, `191e15c`) reports:
  - `test_06_missedTurn`: "parking-001@0.5 missedTurn: banner behind the car
    4x (max 68 m)";
  - `test_07_wrongWayStart`: "rural-001@0.5 … 5x (max 97 m)" and "coastal-001@0.5
    … 10x (max 174 m)";
  - `test_11_loopEarly`: "remaining rose 2x (max 18 m)".
- **Already recorded.** The banner-behind state is
  `docs/overnight-e2e-findings.md` Finding 3 (2026-09-30), seen in 169
  missed-turn and 136 wrong-way drives. **New** is the plain case: driving
  the wrong way along the route never reroutes at all.

**What a route weighs.** The production request
`from=42.1396268,-71.2613399&to=42.1311784,-72.7617144&pref=0.50&w_town=0`
(about 150 km) returned 239 KB of JSON for both arms:
- scenic: 5,874 coordinates and 98 steps;
- fastest: 3,182 coordinates and 29 steps.

**What the graph weighs.**
- 794,685 nodes, or 801,719 after turn-restriction splitting.
- 998,252 edges.
- `graph_edges.parquet` is 197 MB, with geometry and every score column, and
  `graph_nodes.parquet` is 17 MB.

**What the app promises.** The support page answers the offline question with
"No. Routes are computed on our routing server, so the app needs a data
connection." (`site/index.html:86-87`). The listing says "Needs a data
connection." (`docs/app-store-listing.md:80`).

**Hypothesis, unmeasured:** cellular dead zones are common on the back roads
the scenic preference picks in Vermont, New Hampshire and Maine.
- **Evidence:** the reviewer's assertion, and general knowledge.
- **What would kill it:** mobile coverage data showing that a negligible share
  of scenic route-km has no coverage.

Measuring this is part of the job (question 6).

## The mechanism

**What the device holds during a drive.** It has the line it is following
(coordinates) and that line's steps. On-route guidance and the voice therefore
run without a server. Everything else is a server request:
- every reroute;
- a loop's resume through its far point (`via`);
- "Switch to fastest".

### P-04

- **The failure banner only shows while a request is in flight.** The only
  banner tied to a reroute request is
  `if nav.isRerouting { … "Off route" … "Finding a way back…" }`
  (`ios/Sources/NavView.swift:253-256`).
- **A failed reroute is swallowed.** The code is
  `reply = try? await fetchRoute(…)`, and `fetchLoopResume` the same way
  (`ios/Sources/NavigationModel.swift:1380-1384`). On `nil` it bumps
  `consecutiveReroutes` and returns `.failed` (`:1386-1398`).
  `RouteService` has typed errors, `.unreachable` and `.offline`
  (`ios/Sources/RouteService.swift:62-75`), but only the planning screen shows
  them.
- **Retries run on a timer, and nothing watches connectivity.**
  - The base interval is 8 s, doubling to a 120 s cap (`:381-382`,
    `rerouteCooldown` at `:394-397`). Four failures reach the cap.
  - The backoff clears after 30 s on the line (`:388`).
  - Request timeouts are 15 s and 20 s (`RouteService.swift:94-95`).
  - There is no `NWPathMonitor` or any other connectivity check anywhere in
    `ios/Sources`.
- **Losing GPS mid-drive has no driver-facing state.**
  - `lastFixAt` only tells "no fix yet" apart, which shows "Waiting for GPS"
    (`NavView.swift:258-274`).
  - The only fix-silence check belongs to the trace recorder
    (`recordingProblem`, `NavigationModel.swift:758-776`). Recording is off in
    every build (`DriveTrace.isEnabled = false`, `ios/Sources/DriveTrace.swift:75`).
- **Off the route, the banner goes stale.** It keeps the abandoned line's next
  maneuver, and nothing is spoken.

### P-05

- **A reroute needs every one of these clauses** (`:1034-1043`):
  - armed;
  - not already rerouting;
  - not `awaitingJoin`;
  - more than 300 m remaining (`noRerouteWithinMeters`, `:434`);
  - past the cooldown;
  - moved since the last attempt;
  - `here.offRoute > offRouteMeters`, which is 60 m (`:125`);
  - a 3-fix streak. One fix past `offRouteCertainMeters` (200 m, `:142`)
    counts for the whole streak (`:1016-1022`).
- **Driving backwards along the line never qualifies.** `offRoute` is the
  distance to the nearest point at or after a floor (`notBefore`), and the
  floor follows a running maximum. A car driving backwards along its own line
  runs back past that floor. `reseatIfPinned` (`:1090-1104`) then moves the
  match onto the line behind the car. That free match must lie within
  `joinConfirmMeters` and `reseatWindowMeters`. `offRoute` falls back under
  60 m, and the reroute never qualifies.
- **The banner freezes and the voice goes silent.** `runningBackwards`
  (`:1186-1189`, `here.travelled < anchor - reverseMatchMeters`) gates
  `advanceSteps` (`:1120`) and the on-route check (`:851-852`).

## What constrains any design

These findings are all open.

**Drive simulation, 2026-10-05.** The report is uncommitted in the
`drive-simulation-testing-057db9` worktree, at
`docs/drive-simulation-2026-10-05/README.md`. It may have merged by the time you
read this. None of its findings is fixed. Real traces had 0 spikes in 29,736
fixes, but they are suburban Massachusetts only.
1. **A loop's match can jump onto its own return leg and stay there.**
   - It happens after the first outbound match.
   - On the 400 km Needham loop with σ3 m noise, 2 of 253 prompts were spoken
     over 8 h.
   - A plausibility gate fixed it in the harness, but it breaks 50 unit tests.
2. **One fix past 200 m counts as a full streak.**
   - The spike persona produced 1,468 reroutes over 79 routes.
   - Requiring two fixes cut that to 20, and missedTurn and wrongWayStart came
     out byte-identical.
   - 39 tests encode the one-fix rule.
3. **Sustained multipath ("canyon") reroutes drivers who never left the road.**

**Docs on `main`.**

| doc | what it holds |
| --- | --- |
| `docs/overnight-e2e-findings.md` | Finding 3, and the persona tables |
| `docs/loop-matching-fix.md` | the 1 m tie plus continuity rule, for roads a loop drives twice |
| `docs/reroute-audit.md` | Findings 1–5: why the backoff exists, the pinned floor, the failed "fastest" tap |
| `docs/current-street-display.md` | the three-state off-route readout |
| `docs/never-joined-drive.md` | `stalled` |
| `docs/voice-guidance-plan.md` | the time-based schedule. It is cited by section from five files, so don't renumber it |
| `docs/interface-design.md` | the banner |

On the banner, `NavView.swift:248` sets the rule: "Words only — a driving
banner is no place for a tap target."

**Licensing.**
- The drawn route is a Produced Work under ODbL §4.3.
- The parquet graph is a Derivative Database under §4.4, and distributing it
  triggers share-alike (`ios/Sources/AboutView.swift:110-119`;
  `docs/data-sources.md:41-46`).
- `docs/licensing-open-questions.md` covers what counts as "Substantial",
  from `:165`.

**Capacity.** Production is one small VM, and loops serialize on one
process-wide lock (`LOOP_LOCK` in `server/app.py`). The outside review's P-02
found that ten simultaneous loop requests left six past the app's 15 s
timeout, on a faster machine. Price any server-side option in CPU per request
against that.

## What the plan must answer

1. **Every mid-drive failure state, on a route and on a loop.** The states are:
   - server unreachable or erroring;
   - no network;
   - no GPS fixes;
   - degraded GPS;
   - off route with no reroute;
   - wrong way along the route.

   For each, give what the banner says, what the voice says and how often, what
   the map draws, and what ends the state. Include the proposed copy.
2. **Retry policy.** A network failure and "the server answered with the route
   you're ignoring" are different failures, and the backoff was built for the
   second. Should a lost connection retry when connectivity comes back instead
   of on the timer? What does each choice cost in battery?
3. **Wrong-way detection along the route (P-05).** It must survive loops that
   drive a road twice, GPS spikes, and multipath. Say what it does online
   (reroute with the heading) and offline ("turn around when possible").
4. **Tier 0, with no new data.** What can honestly be said from the cached line
   alone, and where does that go wrong?
5. **Offline rerouting tiers.** Cost each one: engineering, payload, device CPU
   and battery, server CPU, licensing, data freshness. Say what each covers:
   an outage, a dead zone, a wrong turn.
   - **T1, a corridor.** The road network within some distance of the route
     ships with it. It carries costs for the request's pref and weights, and
     enough maneuver data to speak instructions. A small on-device Dijkstra
     rejoins the line ahead, or reaches the destination.
   - **T2, a regional download.** The whole graph is on the device, with a
     router written in Swift.
   - **T3, anything else.** For example: MapKit's `MKDirections` when our server
     is down but the network is up; server-side contingency routes computed
     in advance; anything else you find.
6. **How often it matters.**
   - The share of scenic route-km and loop-km without mobile coverage, by
     state.
   - Off-route excursions per 100 km, and how far they stray, from real traces
     and the personas. This sizes T1's corridor.
7. **A recommendation**, split into before submission and after launch. Give:
   - the cost;
   - the tests that would prove it, including the personas the harness lacks:
     a server that goes down mid-drive, and a dead zone;
   - the decisions it needs from the owner.

## Traps

1. **Retrying faster is not the fix.** The backoff exists because a server that
   keeps returning the line the driver is ignoring cannot be helped by being
   asked again. On the 2026-08-22 drives that loop ran ten reroutes in 160
   seconds (`NavigationModel.swift:362-380`; `docs/reroute-audit.md` Findings
   4–5). Failed requests were folded into the same backoff as "the plainest
   case of asking not helping" (`:1389-1395`).
   - A failed request and an unhelpful success are different failures. Split
     them, but don't delete the backoff for the second.
   - Don't make a dead zone cost a radio wake every 8 s, which is the battery
     argument at `:1389-1395`.
2. **Going the wrong way along a loop can look like going forwards along its
   other pass.** Loops drive some roads twice. Stowe's default loop, for
   example, is the Smugglers' Notch out-and-back (`docs/new-england-only.md`).
   - A detector built on `travelled` falling will fire on every such stretch,
     or never, depending on which pass the match holds.
   - This is the hazard in `docs/loop-matching-fix.md` and in the drive
     simulation's Finding 1.
   - Test it on loops and on real-trace replays, not only on routes.
3. **One fix is not evidence.** Anything that triggers a wrong-way or offline
   state must survive the spike and canyon personas (drive simulation, Findings
   2–3). Don't build on the one-fix rule in `offRouteCertainMeters` as it
   stands.
4. **A polyline is not navigation.** The server builds the maneuver text, the
   names, the exits and the rotaries in `pipeline/router.py` (2,559 lines),
   from per-edge data. An on-device Dijkstra that returns a line without them
   would draw a route and say nothing. Either the corridor carries per-junction
   instruction data, or the maneuver code gets ported. Measure the bytes either
   way.
5. **Bearings mislead on a road network.** "The nearest point of the route" can
   be across a river, a railway or a limited-access highway.
   - Tier 0 must never invent a turn.
   - "Turn around when possible" is honest only when the line is behind the car
     on the road it is on.
6. **Shipping graph data means distributing a Derivative Database.** A regional
   download is Substantial and triggers share-alike. A per-route corridor might
   not be. Answer it from the "Substantial" section of
   `docs/licensing-open-questions.md` and from the OSMF guideline, with sources.
   Don't assume either way.
7. **The traces are private, and the repo is public.** `<main>/traces` records
   where someone drove, to the second. Use aggregates only. No coordinates,
   street names or towns from a trace may appear in anything committed.
8. **The simulator is not a dead zone.** Stopping the local server simulates an
   outage, not lost signal.
   - MapKit still loads tiles over the Mac's network.
   - The simulator fails open on background policy, so a locked phone or a
     backgrounded app behaves differently.

   Say which states you exercised and which you inferred.
9. **Server-side contingency routes spend the scarce resource.** Every scenic
   Dijkstra is CPU on one small VM. A design that multiplies requests per drive
   has to be priced in that CPU, not assumed to be free.

## Done looks like

1. `docs/mid-drive-recovery-plan.md` answers questions 1–7. Every claim carries
   a `file:line` or a measurement, with how to rerun it.
2. It contains a failure-state table with these columns: state, banner, voice,
   map, what ends it. The proposed copy is in the table.
3. Each tier is costed with numbers measured here where possible. For T1 that
   means:
   - payload bytes against corridor width, on a sample of routes and loops that
     includes 400 km loops;
   - the share of excursions the corridor contains;
   - on-device Dijkstra time at that size. A Swift micro-benchmark in a scratch
     package is fine.
4. Prevalence is either the coverage share by state, or a statement that the
   available data cannot determine it, with what would.
5. The recommendation is split into before submission and after launch, and
   lists the owner decisions it needs.
6. Nothing in `ios/`, `server/` or `pipeline/` is edited. Measurement scripts
   may go under `tools/` as new files only. Harness experiments run in a scratch
   copy, made with `git archive HEAD ios tools`. Nothing is pushed.

## Build and test

`<main>` is the main checkout, the first line of `git worktree list`.

- **Branch.** Work in a fresh worktree off `main`, on your own branch. This
  brief is untracked in the master session's worktree. Copy it into your
  `docs/` and commit it with the plan. Results go in the plan, never appended
  here.
- **Data.** Link `<main>/data` into your worktree and use
  `data/processed-ne`, the build production runs. `<main>/traces` holds 12
  recorded drives. Read them, never copy them out, and see Trap 7.
- **Python.** Run `<main>/.venv/bin/python -m …`. The venv's script shebangs
  are stale, so always use `-m`.
- **Local server.**
  `PORT=<free port, never 5057> SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=$PWD/data/processed-ne <main>/.venv/bin/python server/serve.py`.
  Record `$!` and stop only that PID: a broad `pkill -f serve.py` killed
  another session's server on 2026-10-05. Stopping your server is how you
  simulate an outage.
- **iOS.** Create your own simulator and use its UDID everywhere.
  - Point tests at your server with
    `TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:<port>`.
  - The end-to-end drives need `TEST_RUNNER_SUNDAYDRIVE_E2E=1`.
    `TEST_RUNNER_SUNDAYDRIVE_E2E_ONLY=<key>@<pref>` replays one drive.
  - The personas are listed in `ios/Tests/SimulatedDrive.swift:27-28`.
  - Read failures from the `.xcresult`, not the log, because test names contain
    the word "failed".
  - Don't pipe `xcodebuild` into `tail`.
- **Memory.** The router takes roughly 4–5 GB, and other sessions share this
  Mac. Run one heavy job at a time.
- **Production.** Send it a handful of requests at most. Run every sample on
  your local server.
- **No subagents.** Do the web research (coverage data, licensing guidance,
  MapKit's offline behaviour) yourself, with WebSearch and WebFetch.
