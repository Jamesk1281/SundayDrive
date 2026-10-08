# Pre-submission review: verdict

**Status: reviewed `6f26edf`. Verdict: SUBMIT AFTER (four blockers: K-7, approximate location, AR-1, and C-1 before launch day).**

> **Where it stands, 2026-10-04 (main past `f9f1937`).**
>
> **Fixed** by round 1 ([`pre-submission-fixes-brief.md`](briefs.md)):
> - K-7 (`45b1589`)
> - §6.2, approximate location (`09890a8`)
> - K-2 (`261b3c0`)
> - K-6 (`36f5adf`)
> - K-10 (`8e3772d`)
> - AR-3, the text only (`8c56c11`)
>
> **Still open, of the blockers:**
> - AR-1: the review notes, and the out-of-region copy.
> - C-1: the winter-closure mask. It has to be live before the app is public
>   at all, not only before L, because a user who installs it after a quiet
>   release in Vermont gets the same closed roads.
>
> **Still open, of the "before L" list:**
> - ~~AR-2 and AR-4/C-2~~ **Decided 2026-10-04:** drive recording and both
>   scenery-rating controls are switched off in every build
>   (`DriveTrace.isEnabled = false`), code kept. The privacy texts say the app
>   does not record.
> - C-3.
> - K-1. **Built 2026-10-08** on `claude/loop-lock-contention`, not merged:
>   the rejoin has its own lock, and loop builds answer 503 instead of
>   queueing. With 4 clients planning loops, a rejoin went from ×7–8 to
>   ×1.2–1.3 and a default route from ×13–29 to ×0.9–1.8
>   ([loop-lock-contention.md](loop-lock-contention.md)).
> - A "Clear recent destinations" control.
>
> Everything below is as reviewed at `6f26edf`.

Answer to `docs/pre-submission-review-brief.md` (committed alongside). Every
`file:line` below is at `6f26edf8cc00e8dedebd836a03a6798c34af7b19`, read with
`git show 6f26edf:<file>`. `<main>` is the main checkout.

---

## 0. Baselines

Measured 2026-09-30, 00:40–00:55 EDT, from a worktree at `6f26edf` with a clean
`git status`.

| | |
|---|---|
| SHA reviewed | `6f26edf8cc00e8dedebd836a03a6798c34af7b19` ("Merge the brand UI alignment"). `main` was still at it when this section was written |
| Backend suite | **388 passed, 0 failed, 0 skipped**, in 426 s, exit 0: `SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python -m pytest -q tests`. It took longer than the brief's 264 s because another session's `pytest tests -q -x` and my own server's graph load were running at the same time. The count matches the brief |
| iOS suite | **273 executed, 273 passed, 0 failed, 0 skipped**, `** TEST SUCCEEDED **`, on a simulator created for this review (iPhone 17 Pro, iOS 26.4), with `TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:5391` |
| How I know `LiveDriveTests` reached my server | All 7 report `passed` (1.4–4.8 s each), and none report `skipped`. Nothing was listening on 5057 (`lsof -iTCP:5057` was empty), so a missed override would have shown up as 7 skips. `VoiceCatalogueTests` finished (8 cases passed) and did not hang |
| Local server | `PORT=5391 SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<main>/data/processed-ne … server/serve.py`: `794,685 nodes (801,719 routing slots)` |
| Live API | `GET /api/health`: HTTP 200 in 0.12 s, `{"nodes":794685,"routing_slots":801719,"status":"ok"}`. It serves the same graph as the local build. I sent it only that request and the two Pages requests. Nothing tonight probed it |
| RDAP | `jameskouvlis.com` expires **2026-10-28T18:52:52Z**, last changed 2026-08-12, **not renewed**. This is a known status item (brief §2), not a finding |
| Pages | `/SundayDrive/` and `/SundayDrive/privacy/` both returned 200 |
| What else was running | At least eight other Claude Code sessions. Among them: one running its own `pytest` over the whole suite; one running `tools/audit_directions.py` on `processed-ne` (97% CPU); a scratch server from another worktree on port 5173 (90% CPU); `mediaanalysisd` (185%); and a booted simulator (`e2e-overnight`) that is not mine. Load average reached **114** at 01:15. Another session also wrote `forbidden_movements.parquet` into `<main>/data/processed-ne/` at 01:15. The router does not read that file, and `graph_edges`, `graph_nodes` and `turn_restrictions` still carry their 2026-08-29 timestamps, so the build I served did not change during the review. All timings below are quoted as ratios or ranges |

## 1. Conceptual

### C-1. The router has no seasons, and its beauty score is drawn to the roads that close for winter — **Blocker**

**Verified.** The served graph routes and loops over roads that OpenStreetMap
itself marks closed to cars or unmaintained in winter. The scenic score rates
those roads beautiful 3.7 times as often as the network average, so the router
does not merely tolerate them, it seeks them out. Launch day is 2026-10-22,
and the first of these roads closed on 2026-10-15.

**Why it happens.** `extract.py` keeps a drivable way unless
`access ∈ {private, no}` without `motor_vehicle=yes`
(`pipeline/extract.py:175-176`, `pipeline/common.py:11-20`). Nothing in
`pipeline/` reads `*:conditional`, `seasonal`, `winter_service`,
`motor_vehicle=no` or `barrier=*`. The only `conditional` in the pipeline is a
turn restriction (`pipeline/graph.py:126-127`). The graph has one state all year.

**The scan.** I ran a pyosmium pass over `<main>/data/raw/new-england-latest.osm.pbf`
using extract.py's own filter. It matches `roads.parquet` exactly: 565,410
drivable ways. It then joined the flagged ways to `graph_edges.parquet` by
geometry.

| what OSM says about a way the router uses | ways | km |
|---|---|---|
| closed or unmaintained in winter (`*:conditional=no @ Nov–Apr`/`Oct 15–May 15`/`snow`, `winter_service=no`, `seasonal=*`) | **190** | **165.5** |
| `motor_vehicle`/`motorcar`/`vehicle` = `no`/`private` all year | 460 | 152.8 |
| passes a blocking barrier node (block, jersey barrier, bollard, chain, debris, log, rope) that no access tag lets cars through | 418 | 141.9 |

The winter-closed set is 0.071% of the 232,720 km graph, and it is the wrong
0.071%:

- **Score:** its length-weighted mean is **5.93**, against 4.56 for the whole
  network. **37.2%** of its km score 7 or more ("beautiful"), against 10.0% for
  the whole network.
- **Named roads:** VT‑108 through Smugglers' Notch scores 8.51 (tagged
  `motor_vehicle:conditional=no @ (Nov-Apr)`, `winter_service=no`). The Mt
  Washington Auto Road scores 7.86. Lincoln Gap Road scores 7.33
  (`no @ (Oct 15-May 15)`). Kearsarge Mountain Road scores 7.28. Hurricane
  Mountain Road, Jefferson Notch Road, Evans Notch (ME 113), Hazens Notch and
  Kelley Stand Road are on the list too.
- **The flagship list:** ranked the way the marketing plan's §6.3 ranks them
  (named stretches of at least 8 km, by length-weighted score), the Auto Road
  is #16 in New England and ME 113 is #34. Both are closed for their whole
  length all winter.
- **A lower bound:** OSM does not tag every seasonal road. Acadia's Park Loop
  Road, #5 on that list, closes Dec 1–Apr 14 and carries no such tag.

**It reaches drivers on every main path.** Measured on the local server
(`/api/route` and `/api/loop`, NE build):

| request | what comes back |
|---|---|
| Stowe → Jeffersonville, VT, at pref 0, 0.5 and 1 | Every arm, **the fastest included**, drives "Mountain Road" / "Vermont Route 108 South" through the Notch (27.9 km, 28 min) |
| Warren → Bristol, VT, every pref | Every arm drives Lincoln Gap Road, closed since Oct 15 |
| Jackson → Chatham, NH, pref 0.5 (the default) and 1 | "Turn left onto Hurricane Mountain Road" (`access:conditional=no @ Nov-May`) |
| Loops of 40 and 80 km from Stowe, Warren, Jackson and Jefferson, NH, every direction offered | **19 of 53 loops** carry more than 0.2 km of winter-closed road. **The loop the app offers first** does in 5 of the 8 cases. Jefferson's default 80 km loop has 25.0 of its 79 km on it. One Jackson loop says "Make a U-turn to stay on Mount Washington Auto Road", a private toll road |
| The reroute: a driver at the east end of the closed Lincoln Gap section, turned around (`heading=90`) | Both arms open with "Sharp right onto Lincoln Gap Road", back over the gap |

That last row is the stranding mechanism. At the gate, a driver in November
has three options in the app, and all three fail:
1. The off-route reroute sends them back up the closed road.
2. "Switch to fastest" sends them back up the same road, because the fastest
   arm uses it too.
3. The app has no way to say "this road is closed".

On roads tagged only `winter_service=no`, such as Jefferson Notch Road, Kelley
Stand Road or ME 113, there may be no gate at all, just an unplowed mountain
road.

**Why it is conceptual, not only a data bug.** The product scores beauty as a
fixed property of a road. The things that decide whether a scenic drive works
all run on a calendar and a clock:
- the road being open
- the leaves (the E4 point above)
- the daylight
- the plowing

The app's own "What it does not do" list (`BeforeYouDriveView.swift:51-62`)
names no live traffic and no lane guidance. It does not mention that roads
close.

**Reproduce.** Scan the PBF with the script in *Reproducing this*, then POST
`from=44.4654,-72.6874&to=44.6437,-72.8290&pref=0.5` to a local `/api/route`
and read the step names.

**Prior art.** Two partial items.
- `directions-accuracy.md` §5 lists "Node-level access. `barrier=gate`,
  `access=private` on a *node* are not read" under **known, unmeasured**. The
  barrier row above is that item, now measured: 418 ways and 141.9 km.
- `scenery-grading-verdict.md` E4 notes the score is blind to foliage season.
  That is about beauty, not access.

`git grep -iE "seasonal|winter|:conditional|road clos|closed for"` over
`docs/` and `pipeline/` finds nothing on way-level seasonal access. The
marketing plan (§1, §7) treats season as demand. What is new: roads the
router uses close for winter, the score prefers them, and every main path,
the fastest arm included, drives them.

**Cheapest fix.**
1. For launch, add a startup mask in `Router.__init__`. Load a small side
   table: the 190 flagged way geometries, with their closed months, taken from
   the PBF. Spatially join it to the edges, which takes seconds, as above.
   Then add `+inf` to those edges in `_weights` during the closed months.
   That is about 60 lines and a new parquet, with no graph rebuild. The same
   join can drop the blocking-barrier and `motor_vehicle=no` ways all year.
2. Carry the tags through `extract.py`/`graph.py` at the next rebuild.
3. Add "seasonal roads" to the "What it does not do" list, because the OSM
   tagging is incomplete.

### C-2. The one instrument that could validate the score is shipped so that it can never report back — **Major**

**Verified** (by reading the code). The premise stands on 79 marks from one
driver (`measuring-scenery.md`). The release is the first chance to get more,
and the app does collect marks from every user:
- the two in-drive buttons (`NavView.swift:313-352`)
- the arrival card's "How was the road?" (`ArrivalView.swift:44-52`)

Every mark goes into a file that never leaves the user's phone
(`DriveTrace.swift:131-134`, privacy policy §3: "no upload path anywhere in
the app").

So after launch the calibration set is still one driver, whatever happens. And
every user sees the largest controls on the driving screen (`verdictHeight`
58 pt, full width, `NavView.swift:51-53`). They are built to be tapped at
45 mph (`DriveTrace.swift:41-46`), and they do nothing for the person tapping
them. `ArrivalView.swift:5-10` describes the card as "free calibration data on
a measurement the project cannot get any other way". In the shipping
architecture, the project cannot get that data at all.

**Prior art.** `measuring-scenery.md` states the one-driver limit, and
`consumer-polish-brief.md` §5 asks for the buttons to be *more* visible. The
new point is that the release structurally cannot lift that limit, while
asking every driver to do the work.

**Cheapest fix.**
- Keep the arrival card, which is answered after parking.
- Show the in-drive pair only while stopped, or only in the owner's build.
- Before launch, decide whether to add an opt-in, anonymised upload of marks
  alone (snapped edge id and verdict, no trace). That reopens the privacy
  decision (`release-plan.md` Decision 3), so it is the owner's call. The
  legal side of the in-drive buttons is AR-4.

### C-3. The dial's headline prices the minutes against the fastest route, and the prize against nothing — **Major**

**Verified** (code, then a replay of the committed census). The line
`interface-design.md` §4.3 calls "the only number that matters", "the price
and the prize in one line", is built as follows (`DirectionsView.swift:222-225`):

```swift
cost(c.extraMinutes) + " · " + "\(miles.scenic) mi of beautiful road"
```

The price is a *difference* (scenic minus fastest). The prize is the scenic
route's *total* beautiful miles, not what the extra minutes bought. So "+17 min
· 5 mi of beautiful road" can describe a trip whose fastest route already has
5 miles of it.

I replayed that exact readout, with `isSameDrive` and the server's
`_no_worse_than_fastest` guard, over the 983 shipped-default trips in
`docs/route-census/census-routes.csv`:

| | trips |
|---|---|
| readout charges minutes ("+N min") | 846 |
| …and the extra minutes buy **no** beautiful road (printed miles ≤ the fastest route's) | **61 (7.2%)** |
| …of which the scenic route has *less* beautiful road than the fastest | 15 |
| …the printed miles are at least **twice** the real gain | **163 (19.3%)** |
| median printed vs median gain: 10–25 / 25–50 / 50–100 / 100–200 km | 3 vs 2 · **6 vs 3** · 12 vs 8 · 27 vs 21 mi |

The worst cases read "+43 min · 10 mi of beautiful road" (the fastest route
has 11), and "+16 min · 0 mi". The ledger underneath shows both numbers, so
nothing is hidden. But the headline mixes two baselines, and on the typical
25–50 km trip it states the prize at twice its size.

**This is a regression of settled design.**
- The archived `beautiful-miles-and-the-slider-brief.md` chose "adds 49 min,
  turns **1 mi** of beautiful road into **12**" because *"only the second
  phrasing says so"*.
- `RouteComparison`'s sentence (`RouteResults.swift:192-204`) still handles
  "the scenic route can come back with *less* beautiful road". The redesign
  calls it only for a backend without `beautiful_km`, so on today's server it
  never runs.

**Prior art.** `route-distribution-study.md` Q1 and Q2 (3.1% strictly worse;
12.2% gain under a mile and are told nothing) and the archived brief. The new
part is that the shipped headline reintroduces the problem, and the replay
above measures by how much.

**Fix.** Print the gain: "+17 min · +2 mi of beautiful road", or "turns 3 mi
of beautiful road into 5". When the gain is zero or negative, fall back to
`RouteComparison.attributedSummary`, which already words those cases. That is
about 10 lines.

### C-4. Maine's travel times are priced on stop-sign data four to five times sparser than its neighbours' — **Minor**

**Hypothesis.** It would be disproved by a Maine drive whose trace shows
stops the graph does not have, or by a state inventory that matches the
graph's count.

The junction charges that cut ETA error from 22% to 5.7%
(`junction-timing-plan.md`) were calibrated on Massachusetts drives. I counted
the controls baked into `graph_edges` (`n_stop_*`, `n_signal_*`) inside
interior boxes for each state, away from the borders. Stop-sign passes per
1,000 km of road:

| CT | RI | MA | VT | NH | ME |
|---|---|---|---|---|---|
| 591 | 161 | 381 | 152 | 185 | **36** |

Vermont and New Hampshire are as rural as Maine and carry 4–5 times more.
That pattern looks like mapping density, not road design. It is the pattern
`geodata-sources-findings.md` found for green areas: 3.3× thinner in Maine.

If so, Maine ETAs silently fall back towards the free-flow optimism the
junction work removed.

**Prior art.** OSM's uneven coverage is known for green areas and scores. For
traffic controls and ETAs it is not written down.

**Fix direction.** Not for launch. Put a per-state control density in the
analysis tools, and send the first Maine drive through `tools/analyze_trace.py`.

## 2. Market

The marketing plan's own market facts hold as far as I checked them:
- The empty 2026 field.
- Short video as the engine.
- The free, no-account message, apart from AR-3.

I did not re-derive any of it. The three findings below are places where the
product, measured tonight, contradicts a premise the plan relies on.

Two premise questions already have answers, and those answers still stand:
- **Would a driver notice the dial?** For everyday trips, mostly not.
  `route-distribution-study.md` Q1 found that at 10–25 km the default buys a
  median 0.33 beautiful miles, and 32.8% of those trips read "Same as the
  fastest route". At everyday distances the loop, not the dial, carries the
  product, which is how the marketing plan pitches its core audience.
- **What if nobody notices it?** Low use is itself a hosting risk, because
  memory is what keeps the Oracle box from idle reclamation
  (`DEPLOY-oracle.md` Part 12). Nothing tonight changes that.

### M-1. The launch spends its one-shot channels in the week the product's best roads start to close — **Major** (Blocker if C-1 is not fixed)

**Verified** (dates from the OSM tags in C-1).
- **The plan.** It fixes L on Thursday 2026-10-22 and spends press, one post
  per subreddit, Show HN and the featuring nomination there. None of those can
  be run again.
- **The tagged closure dates.**
  - Lincoln Gap closed Oct 15, before L.
  - Mt Greylock's summit roads are open to cars only `May 20–Oct 29`.
  - VT‑108 Smugglers' Notch, Hazens Notch and Route 58 close `Nov–Apr`.
  - Hurricane Mountain Road closes `Nov–May`.
- **Where they are.** 90% of the winter-closed km (149.7 of 165.5) is north of
  43°N, which is Vermont, New Hampshire and Maine. The loops the plan's second
  audience comes for (M-2) are in those states.
- **The flagship list.** "The ten best-scoring drives in Vermont" (§6.3),
  ranked by the plan's own method, would publish the Mt Washington Auto Road,
  ME 113 and Park Loop Road (C-1) to people who will try them in the following
  weeks, when all three are closed or about to close.

**What the tags say about spring.** In the north, the plan's spring fallback,
Memorial Day weekend (29–31 May 2027), is not a consolation. It is the first
holiday weekend after those roads reopen (`May 15`, `May 20` in their tags).
The fallback is the better date for the northern product. The October date
suits southern New England.

**Prior art.** The plan's §7 treats season as demand ("Foliage is the peak …
winter is the trough") and does not know that the roads themselves close. No
committed document mentions a seasonal road closure; see C-1's prior art.

**Fix.**
- Fix C-1 before L.
- Build the §6.3 lists with closed-in-season roads left out or labelled "open
  May–Oct".
- In October, aim the one-shot posts at southern New England and at roads
  that stay open all year, such as the Kancamagus (#4 on the list, not
  tagged). Keep the northern mountain content for the spring opener.

### M-2. The plan's second audience meets AR-1's red sentence at home, and cannot plan the trip that brings them here — **Major**

**Verified.** The plan's second priority is "Leaf-peepers and visitors, many
from New York, New Jersey and further", reached on TikTok, where "a national
audience is *useful*" (§4). On the local server:
- Times Square → Stowe returns **"point is outside the covered road network
  (currently New England)"**.
- Albany → Pittsfield returns the same.
- A loop from Times Square returns the same.

`SNAP_MAX_M = 5000` (`server/app.py:89`) rejects any endpoint more than 5 km
from a New England road. So the visitor's natural first session, on the evening
they see the video, is the screen in AR-1. That means tapping **Loop** or
**My Location**, then reading one lowercase sentence with no next step.

The captions' "New England only" warns them about the region. It does not tell
them the app works from home if they type the town they will start from, which
it does.

**Prior art.** The plan's §10 risk (one-star reviews from outside the region)
and its §5.10 ask for a friendlier message. The new point is that the plan
*targets* this audience, and that the fix AR-1 needs anyway makes the at-home
session work: "covers New England, type a town there" plus a focused start
field.

**Fix.** The AR-1 message. Captions should say "plan it from anywhere: type
the town you'll start from".

### M-3. From one home, the loop catalogue is small, fixed and blind to what you already drove — **Minor**

**Verified** (n=8 seeded random starts).
- **Setup.** I requested every offered direction at 30, 40, 50 and 60 km, and
  counted loops as distinct when they share less than half their ~100 m
  cells with any other.
- **Result.** Each start offered 24–32 loops but held only **5–12 distinct
  drives, median 8** (per start: 10, 7, 9, 6, 6, 5, 12, 9).
- **Why they never change.** The planner is deterministic, and `/api/loop`
  caches by request (`server/app.py:354-360`), so the same loops come back
  every week.
- **Why the app cannot help.** It keeps no memory of what you drove. `Recents`
  holds only destinations, and traces are never read back. So "Try another
  direction (8)" will offer last month's drive as though it were new.

At the marketing plan's weekly cadence ("It's Sunday. Ninety minutes, nowhere
to be?", §5.10), novelty from one home runs out in about two to three months.
That is roughly one season. It is a retention ceiling, not a defect, so the
rating is Minor, but it answers "why would they open it a second time" with
"about eight times".

**Prior art.** `loop-routes-design.md` measures that eight sectors share a
median 1% of roads, so they are different from each other. It does not measure
how many drives one home has across lengths, or repeats over time.

**Fix direction.** Not for launch. Later, a "roads I've driven" penalty fed
from the local traces, which never leave the phone.

The success case, one clip that takes off, is K-1: planning traffic delays
every driver's reroute, and overload is reported as the user's network failing.

## 3. Code

### K-7. On a loop, "Switch to fastest" does not take you home: it takes you to the far point — **Blocker** (3 lines)

**Verified** (by reading the code, then measured on the local server). Listed
first because it misleads drivers on a main path, loop reroutes.

**What the code does.**
- The driver taps the bolt button and confirms **"Switch to the fastest
  route? … This gives up the scenic route for the rest of the drive."**
  (`NavView.swift:149-158`).
- `switchToFastest` sets `pref = 0` and calls `reroute(…, reason: "fastest")`
  (`NavigationModel.swift:1269-1296`).
- `reroute` pins every loop request through the far point for as long as
  `loopWaypoint` is non-nil (`:1345-1349`), and that stays true until the far
  point has been passed (`:311`).

So on a loop, "fastest" means *the fastest way to finish the loop*.

**Measured.** Six 60 km loops: Stowe, Concord and four seeded random starts.
From a point 8 km in, the app's own request (`via` the turnaround, `pref=0`)
comes back as **47–73 km / 47–59 min**. The fastest way home from the same
point is **7.3–8.2 km / 8–14 min**, so the app's version is **4.4–6.3 times
longer**.

A driver who wants to go home has no way to ask for it:
- **The escape hatch keeps them on the loop.**
- **"End the drive" drops navigation.**
- **Directions needs a destination.** The loop's start is not offered as one.

**Prior art.** None. `LoopRerouteTests` covers off-route rejoins. No test and
no document covers the switch on a loop.

**Fix.** In `switchToFastest`, set `passedTurnaround = true`, or bypass
`loopWaypoint` when `reason == "fastest"`. For a loop, change the dialog to
"Head home the fastest way". That is about 3 lines and one test.

### K-1. Planning traffic starves driving traffic, and an overloaded server tells the driver their network is broken — **Major**

**Verified on a local server. The magnitudes are noisy.** One global
`LOOP_LOCK` (`server/app.py:121`) wraps every loop build (`:356`, `:407`). It
also wraps the **mid-drive loop rejoin**, the `via` reroute a driver sends
after missing a turn on a loop (`:289`). So every driver's rejoin waits in the
same queue as everyone's "Try another direction".

Separately, the new A\* fastest arm is a pure-Python heap loop
(`pipeline/router.py:1457-1513`). Waitress runs it on a thread that competes
for the GIL with the long C Dijkstras that loop builds run. That is the path
"Switch to fastest" takes.

Here is what the probe in *Reproducing this* (step 6) measured. Tonight's
load average reached 114, and the idle route alone varied 0.08–0.93 s between
runs, so read these as ranges and mechanisms, not as box numbers:

| request | idle | 1 client planning loops back to back | 4 clients |
|---|---|---|---|
| loop rejoin (`via`) | 0.95–2.9 s | **×1.9–×3.1** | **×7.5** (median 7.2 s, max 10.6 s) |
| route, default pref (two arms) | 0.34–0.93 s | ×1.1 | **×25** (8.5 s) |
| route, fastest only (A\*) | 0.08 s | **×3.6** | not run |
| `/api/health` | 0.00 s | unaffected | unaffected |
| cold 40 km loops, total server throughput | 2.0–6.2 s each | 0.16–0.40 loops/s | 0.52 loops/s |

**What follows:**
- **The rate limit does not bound cost.** It is 60 requests/min per IP
  (`server/DEPLOY-oracle.md:641-643`), so a single IP within the limit can ask
  for more cold loops than the whole server can build.
- **Success is the failure case.** The marketing plan's own success case (one
  short video that takes off) looks, to the server, like many people tapping
  **Loop** at once.
- **Timeouts look like the user's fault.** Past about 20 s of queueing, the
  client's `timeoutIntervalForResource = 20` (`RouteService.swift:95`) fires.
  `catch is URLError` then maps the timeout to `.offline`
  (`RouteService.swift:267-269`), which shows **"No connection to the routing
  service. Check your network."** (`:76`). An overloaded server is reported to
  a driver mid-reroute as their own phone's fault.

**Prior art.**
- `serve.py:9-15` and the 2026-08-14 review: routing does not parallelise,
  about 5 req/s.
- `DEPLOY-oracle.md` Part 11: "one runaway loop in a script is a denial of
  service".
- The marketing plan: "load-test the server" before L.

All of these size throughput. None notices that **the loop rejoin shares a
lock with loop planning** (planning load becomes driving latency), that the
A\* arm is GIL-starved under concurrency (it was benchmarked alone, in
`astar-fastest-arm-brief.md`), or that timeouts are misattributed.

**Cheapest fix:**
1. Give `via` requests their own `LoopPlanner` and lock, which means one more
   cost-model cache of about 30 MB.
2. Refuse rather than queue. When a loop build is already running, return 503
   `{"error": "busy, try again in a moment"}`, so the client shows the server's
   own words instead of a timeout.
3. Map `URLError.timedOut` to "The routing service is busy".
4. Load-test on the box, not on this Mac.

Items 1–3 are about 30 lines.

### K-2. `MARKETING_VERSION` and `CURRENT_PROJECT_VERSION` do nothing — **Minor**

**Verified.** XcodeGen writes literal defaults into the generated plist:
`CFBundleShortVersionString = 1.0` and `CFBundleVersion = 1`
(`ios/Generated/Info.plist` after `xcodegen generate`). The build settings at
`ios/project.yml:81-82` never reach the bundle. Two instruments agree:
- **A mutation build.** `xcodebuild build … MARKETING_VERSION=9.9
  CURRENT_PROJECT_VERSION=42` produces an app whose `Info.plist` still reads
  `1.0` / `1`.
- **The traces.** All twelve drive traces from 2026-08-14 to 08-25 record
  `"app": "1.0"` (`DriveTrace.swift:119`), while `project.yml` said `"0.1"`
  until `fbffba2` (2026-09-29).

So `release-plan.md` §10's "`MARKETING_VERSION` off `0.1`: **Done**" ticked a
no-op. The first upload is unaffected. The **second** upload, whether that is a
fixed build after a rejection or the launch-week hotfix, will carry `1.0 (1)`
again unless Xcode Organizer's automatic build-number management rewrites it.
Every future `1.0.x` will claim to be `1.0`, and the trace headers cannot tell
builds apart.

**Prior art.** None. The release plan believes it is done.

**Fix.** Add `CFBundleShortVersionString: $(MARKETING_VERSION)` and
`CFBundleVersion: $(CURRENT_PROJECT_VERSION)` under `info.properties`. That is
two lines.

### K-3. The unit tests write into the real app's settings and trace folder — **Minor**

**Verified.** After one `xcodebuild test` run, the app container on my
simulator held `lastLoopTargetKm = 5` and **five fake drive traces** in
`Documents/traces`, all timestamped during the test run.
- The first comes from `LoopModelTests.swift:162-166`, through
  `LoopModel.fetch`'s `UserDefaults.standard.set` (`LoopModel.swift:246-247`).
- The second comes from `RouteModelTests.swift:47` and
  `LocationManagerTests.swift:91` calling the real `startNavigation`, which
  opens a real `DriveTrace`.

The next launch showed "Loop · From here, about **6 min**", and the loop that
came back was 3 miles. That is exactly the failure `LoopModel.swift:44-50`
says was engineered away.

It matters in two places:
- App Store screenshots taken on a simulator that has run the tests.
- The owner's research traces, if the tests ever run on the phone.

**Prior art.** The `LoopModel.swift:44-50` comment. The fix it describes moved
the write rather than removing it.

**Fix.** Inject a `UserDefaults` suite and a trace directory into the models,
and have the tests pass throwaway ones.

### K-4. A voice that never finishes measuring leaves the picker empty on every drive — **Minor**

**Plausible.** `VoiceCatalogue.duration(of:)` resumes only when the renderer
delivers an empty end buffer (`VoiceCatalogue.swift:219-233`), and it has no
timeout. The brief records that a voice listed but not downloaded makes that
wait 13+ minutes. In the shipping app this runs in the driving screen's `.task`
(`NavView.swift:269`):
- The long-press voice menu stays empty for the whole drive.
- The measurements taken before the stuck voice are never saved, because
  `cache = durations` runs only after the loop (`:191`). So the same voice
  stalls it again next drive.
- A synthesiser and a continuation leak each time.

Guidance itself still speaks in the default voice.

**Prior art.** The test-side hang is known (brief §6 trap 4). Its production
consequence is not written down.

**Fix.** Race each measurement against a 3 s timeout and write the cache per
voice.

### K-5. No text in the app follows the user's text size — **Major**

**Verified in the code. Not reproduced at runtime.** Every font in
`ios/Sources` is fixed-size:
- 81 call sites across 13 files use `.font(.system(size:))` or `.figure(_:)`.
- `.figure` is itself `.system(size:weight:design:)` (`Theme.swift:121-123`).
- The small-caps `sectionLabel` is a fixed 11 pt (`Theme.swift:129-134`).
- Nothing uses a `Font.TextStyle` or `relativeTo:`.

SwiftUI's `.system(size:)` does not scale with Dynamic Type. Only four
`@ScaledMetric` frames do (`NavView.swift:49`, `:53`, `RouteResults.swift:281-282`).

So the promise in `interface-design.md` §7.7 cannot happen. It says "large
text lengthens [the page] and nothing is cut", and the comments at
`PlanningView.swift:25-29` and `:162-171` reason about accessibility sizes. At
the largest setting the app renders exactly as at the default. That includes
the driving screen's remaining time and distance (12.5 pt), the road name
(13.5 pt) and every section label (11 pt).

Both of my attempts to set AX5 on the simulator (the
`-UIPreferredContentSizeCategoryName` launch argument, and `simctl ui
content_size`) failed to take effect: even the `@ScaledMetric` frames stayed
34 pt. So I have no runtime screenshot. The finding rests on the font calls,
which are unambiguous.

**Who it hurts.** Drivers who set large text. The marketing plan's core
audience runs to 65, and its Facebook audience "skews older".

**Prior art.** `interface-design.md` §7.7 specifies this, and the brief notes
that accessibility was never audited.

**Fix.** Either use text styles
(`.system(.title2, design: .rounded, weight: .bold)` and so on), or keep the
design sizes and scale them with one `@ScaledMetric`-backed helper in
`Theme.swift`. It is a mechanical change at the 81 call sites, then one pass at
AX5 on a device.

### K-6. The Loop row's icon does not exist on iOS 17, the deployment target — **Minor**

**Verified** against the system's own SF Symbols availability table
(`CoreGlyphs.bundle/…/name_availability.plist`).
- `arrow.trianglehead.clockwise` (`HomeView.swift:33`) first shipped in iOS
  18.0.
- The app targets iOS 17.0 (`ios/project.yml:5`).
- Every other symbol-shaped literal in `ios/Sources` (31 checked) is
  available on iOS 17.

On iOS 17 `Image(systemName:)` renders nothing, so the first screen's Loop
row shows an empty amber square. I could not reproduce this, because only the
iOS 26.4 runtime is installed.

**Fix.** Use `arrow.clockwise`, or raise the target to 18.0. One line.

### K-8. The served graph can be rebuilt only from files on one Mac — **Minor**

**Verified.** The README builds from Geofabrik's moving
`new-england-latest.osm.pbf` (`README.md:65-67`). No committed document
records a snapshot date or checksum for the PBF, the Terrarium tiles or the
WorldCover tiles; `git grep -iE "sha256|checksum"` finds only a trace-identity
hash. The 782 MB PBF behind the served graph (downloaded 2026-08-25, graph
written 2026-08-29) exists only in `<main>/data/raw/`. The box has the
processed parquets, but not the inputs.

A rebuild from the README today would use different OSM data.
`route-distribution-study.md` already records that a rebuild moves the
published numbers ("that rebuild has already moved published separations
once"), so that part is known. The new part is its consequence for
C-1: fixing closures in `extract.py` forces exactly that rebuild, and is why I
recommend the startup mask for launch.

**Fix.** Record the input files' sha256 and download dates in
`docs/data-sources.md`, and copy `data/raw/*.pbf` somewhere other than the Mac.

### K-9. "Start driving" works while the new route is still loading, and drives the old one under the new setting — **Minor**

**Plausible** (by reading the code).
- `PrimaryButton("Start driving")` is shown whenever a `response` exists
  (`DirectionsView.swift:63-69`). It is not disabled while `isLoading`, and
  the dial's own readout knows the figures are stale (`routeIsStale`,
  `RouteModel.swift:107`).
- `startNavigation` then pairs the *previous* `response.scenic` with the
  *current* `pref` (`RouteModel.swift:271-277`).

Say the driver drags the dial to Fastest and taps Start at once. They drive the
scenic route that is still drawn on the map, and the first reroute silently
becomes a fastest one. What they see is what they drive, so this is Minor.

**Fix.** Disable the button while `routeIsStale`, or start the route with
`responsePref` rather than `pref`. One line.

### K-10. "1 miles of it beautiful" — **Minor**

**Verified** (screenshot). The loop card builds its line as
`"\(meta.beautiful_km.wholeMilesFromKm) miles of it beautiful"`
(`LoopView.swift:148`), so a short loop reads **"1 miles of it beautiful"**.
The dial's VoiceOver value has the same bug (`DirectionsView.swift:249`).
It matters only because the App Store screenshots are still to be taken.

**Fix.** Pluralise, for example with `^[\(n) mile](inflect: true)`. One line.

## 4. App Review

I read the current guidelines end to end from `developer.apple.com` ("Last
Updated: June 8, 2026") against the built app, rather than citing them piece by
piece. What survived is below. Sections that apply and hold are listed in §5.

### AR-1. The reviewer will not be in New England, and from where they sit, both of the app's front doors fail — **Blocker** (cheap)

**Verified in the simulator.** The run was a fresh install, location at Apple
Park, the app pointed at the local NE server, and driven by a scratch UI test
kept outside the repo:
- **Loop.** The home screen's Loop row is "one tap to a finished drive"
  (`HomeView.swift:5-10`, `:31-42`). Tapped from Cupertino, it gives a blank
  page with one red line: **"point is outside the covered road network
  (currently New England)"**. That is the server's own lowercase string
  (`server/app.py:261-263`), passed through verbatim (`RouteService.swift:57`,
  `:71`).
- **Directions.** From **My Location** to a searched "Coffee", Directions gives
  the same sentence.
- **Nothing on screen says what to do next.** It does not say that typing a
  New England town into the start field works, and it does.

**Why a rejection is likely.**
- **2.1(a) and Before You Submit** ask the developer to *"Provide App Review
  with full access to your app … plus any other hardware or resources that
  might be needed to review your app"*, and to *"Include detailed explanations
  of non-obvious features … in the App Review notes"*.
- **3.2.2(v)** lists *"Arbitrarily restricting who may use the app, such as by
  location"* as unacceptable.

The restriction is not arbitrary: the graph covers six states. But nothing in
the package tells the reviewer that. `release-plan.md` §10 lists the EULA,
export compliance, screenshots, description, category and the name, and **no
review notes**. `app-store-submission.md` §5 answers the background-mode
questions and nothing about region. The only places a reviewer's region comes
up are network latency to Cupertino (`hosting-options-findings.md:806-808`)
and which box Cloudflare picks (`hosting-independent-review.md:144`).

**Reproduce.**
1. `xcrun simctl location <udid> set 37.3349,-122.0090`.
2. Launch with `SIMCTL_CHILD_SUNDAYDRIVE_API=<local>`.
3. Tap **Loop**.

**Prior art.**
- The marketing plan's §10 risk (one-star reviews from out-of-region installs)
  and §5.10 ask (a friendlier out-of-region message). Both are about ratings
  after launch.
- `release-plan.md` §7, whose "most likely rejection" is the backend being
  down.

This finding is the backend being *up* and the reviewer still seeing only an
error.

**Cheapest fix.** An hour, no build:
- Write App Review notes (4,000 bytes max) naming a test route, for example
  Start *Concord, MA* → Destination *Rockport, MA*, and a loop start, for
  example *Stowe, VT*.
- Say why the region is limited.
- Attach a short screen recording of a real drive.

Change the message too, because this is also the first screen for the
marketing plan's second audience (M-2). The marketing plan's §5.10 item 2
already proposes changing this copy server-side, which takes minutes and needs
no build or App Review. But its wording ("Sunday Drive only covers New England
for now") still leaves the reader stuck. Make it say what works: "Sunday Drive
covers New England. Type a town there as your start, and plan from anywhere."
Optionally, focus the start field in the app, which is about 10 lines.

### AR-2. Every drive is recorded to a location log, with no consent step and no way to turn it off — **Major**

**Verified** (by reading the code, and against the published policy).
- **Recording is unconditional.** `startNavigation` and `startLoopDrive` open a
  `DriveTrace` every time (`RouteModel.swift:271-284`, `:294-305`). It logs
  one GPS fix per second, plus the driver's taps.
- **The privacy draft admits there is no off switch.** It says so in its own
  words: ~~"Don't record."~~ *"Not a choice the app offers"*
  (`docs/privacy-policy.md:250-251`).
- **The first-launch screen never mentions it** (`BeforeYouDriveView.swift`).
- **The purpose string does not mention it.** Location is used *"to follow
  the route, turn by turn"* (`ios/project.yml:28`).
- **The on-screen indication is an unlabelled 8 pt dot** next to the arrival
  time (`NavView.swift:421-423`), explained only to VoiceOver (`:451`).

**The guidelines this runs into.**
- **2.5.14**: *"Apps must request explicit user consent and provide a clear
  visual and/or audible indication when recording, logging, or otherwise
  making a record of user activity."*
- **5.1.1(ii)**: *"Ensure your purpose strings clearly and completely describe
  your use of the data"*, and *"provide the customer with an easily accessible
  and understandable way to withdraw consent."*
- **5.1.1(iii)** on data minimisation: the recording is not needed to
  navigate. It serves the owner's calibration, and C-2 shows it can never
  serve that either.

The privacy page states the recording plainly (*"Every drive you navigate is
recorded"*), and App Review reads privacy pages. Whether a reviewer applies
2.5.14 to a location log, as opposed to a camera or microphone, is a judgement
call, so I have not rated this a Blocker.

**Prior art.** `privacy-policy.md` §3 and §5 disclose it (corrected
2026-09-29). No committed document cites 2.5.14 or data minimisation.

**Cheapest fix.** Either choice works:
- Record only after an explicit, default-off switch on the first-launch
  screen: "Keep a record of my drives on this phone". Relabel the dot as
  "Recording".
- Or do not record in release builds at all. This also removes C-2's
  buttons from consumers.

Either way, update the purpose string and the policy. That is about 40 lines.

### AR-3. The published privacy policy says the app stores three settings; it stores a history of where you have been going — **Major**

**Verified.** The live page (`site/privacy/index.html:78-83`) says: *"Besides
drive recordings (below), the app keeps three small settings for itself"*, and
names the voice, voice durations and mute. At `6f26edf` the app also stores:
- **The last five destinations** you searched, with their names and
  coordinates (`Recents.swift:13-50`, written at `RouteModel.swift:182-189`),
  shown on the home screen.
- `lastLoopTargetKm` (`LoopModel.swift:52`).
- `hasSeenBeforeYouDrive` (`PlanningView.swift:47`).
- `matchSystemAppearance` (`ContentView.swift:23`).

Nothing in the app can clear the recent destinations. `Recents.clear()`
(`Recents.swift:52`) has no caller, so deleting the app is the only way.

How it happened: the page was built on 2026-09-29 (`b6fe06d`) from a draft
written before the redesign added `Recents` (`4b3171d`, merged 2026-09-29).
`git grep -i recent` over both policy files finds nothing. It breaches no Apple
term, but it is a specific, false statement in a public privacy policy. It also
undercuts the marketing plan's own rule for the free-app message (§3.3, "Keep
it true").

**Fix.**
- Add one bullet to the policy: "your five most recent destinations, on this
  phone only, so the home screen can offer them again".
- Add a "Clear recent destinations" row on the Sources screen.
- Have `tests/test_privacy_page.py` assert the list of keys against `ios/Sources`.

### AR-4. The in-drive rating buttons invite a tap that Massachusetts law does not allow — **Major**

**Plausible.** This is a reading of the statute; I am not a lawyer.

**The law.** M.G.L. c.90 §13B: *"No operator of a motor vehicle shall use a
mobile electronic device unless the device is being used in hands-free mode"*.
The one exception is *"view[ing] a map generated by a navigation system"* on a
mounted device (malegislature.gov, read 2026-09-30). c.90 §1 defines
"hands-free mode" as operation *"without touching or holding the device;
provided, however, that a mobile electronic device may require a single tap or
swipe to activate, deactivate or initiate the hands-free mode feature."*

**The buttons.** Tapping "Lovely road" is neither viewing a map nor starting
hands-free mode. The buttons exist to be tapped while moving:
- They are *"meant to be hit by a driver who is not looking at them"*
  (`NavView.swift:51-53`).
- The mark is *"read and answered at 45 mph"* (`DriveTrace.swift:41-46`).
- They are the biggest controls on the driving screen.

**Guideline 1.4.5**: *"Apps should not urge customers to … use their devices
in a way that risks physical harm"*. The preamble to §5: apps that *"solicit,
promote, or encourage criminal or clearly reckless behavior will be
rejected."*

A reviewer is unlikely to see the buttons, because they appear only after
joining a route, which AR-1 makes hard. The exposure is really after launch:
the marketing plan's content system screen-records drives (§6.1), and a clip
of the buttons in use is an advertisement for the tap. The marketing plan
knows all six states ban holding a phone (§6.4), but applies that only to
filming.

**Prior art.** None on the buttons. `git grep -iE "hands.free|13B|distract"`
over `docs/` is empty.

**Fix.** Show the pair only when `speed < 1 m/s` (the same `parkedSpeed` the
model already has, `NavigationModel.swift:157`). Keep the arrival card. That
is about 5 lines.

## 5. Attacked and held

What I tried to break and could not, so nobody needs to repeat it.

**The public API's input handling.** About 40 malformed requests went to a
local server. Nothing returned a 500 or hung.
- **Coordinates.** NaN, `-nan`, `inf` and `1e309` all return the out-of-region
  400. `snap` gives them an infinite offset, so `max(s_off, t_off) > SNAP_MAX_M`
  holds even for NaN.
- **Out-of-range values.** Headings of NaN, 360, `-0.0` and `abc` are dropped,
  folded or rejected with a 400. `pref`, `w_*`, `km` and `avoid_unpaved` of
  ±inf or NaN all clamp.
- **Malformed input.** Three-part coordinates and hex floats return 400. `via`
  equal to either end is fine. A lowercase sector returns 400.
- **Size.** A 2 MB form body returns **413** (Werkzeug's form limit). A
  duplicate `from` takes the first value.
- **CORS.** It is wide open (`server/app.py:99`), but tightening it would not
  help. Form-encoded POSTs are CORS "simple requests" that browsers send
  anyway, so CORS is not a lever here. The rate limit is (K-1).

**Server memory is bounded.**
- `LOOP_RESULTS` keeps 16 entries (`server/app.py:130`, `:408-410`).
- `LoopPlanner` keeps 4 field sets and 2 cost models (`looper.py:305-310`,
  `:599-601`, `:681-683`).
- Nothing grows per request.

**Loop length.** 30 seeded random New England junctions at 40 km gave 211
loops, one per direction offered.
- **The first loop:** median error +0.1%, worst +13.2%, and none off by more
  than 25%.
- **Other directions:** 4 of 181 are more than 25% long, the worst +65% (a
  rural start). The card prints the real minutes, so nothing is hidden.
- **Doubling back:** eight loops trip the "doubles back" note, and all eight
  carry it.
- **Cost:** a cold first loop took a median 2.3 s on this Mac.

**Apple's logo and Legal link are clear everywhere I could reach.** I have
screenshots at `6f26edf` of:
- home
- directions with a route
- the loop stage
- the driving screen (both route and loop, and with no GPS fix)

In every one the logo and "Legal" sit clear in the bottom-left. See §6.

**The deploy script.** `server/deploy-oracle.sh` ships every file the router
reads: `graph_edges`, `graph_nodes`, `turn_restrictions`, `access_ways` and
`access_entries` (`router.py:397-398`, `:428-439`, `:518-526`). It refuses a
dirty box or a non-ancestor, verifies by hash rather than by rsync's exit code,
and checks the node count against the file. I found nothing that ships stale
code or data.

**`LiveDriveTests` are real.** 7 of 7 passed against my server with 5057
empty.

**Traffic-control coverage spans the region** (method 10). Every state's
interior carries signal and stop counts in `graph_edges`, so no cache was built
on one state's bounding box. The density differs, as C-4 records.

**The A\* fastest arm's tests bite.** In a scratch copy I inflated
`_alt_bound` by 20%, which makes the bound inadmissible. That failed 5 of the 8
`TestFastestArm` tests, including admissibility over every node and cost
equality against Dijkstra on 25 random pairs. The mutant's Boston → Worcester
came back 46.0 min where the true fastest is 44.8, which is the silent failure
those tests exist for.

**The never-joined pause and the voice schedule are guarded.** In a scratch
copy of `ios/` I made two mutations:
- `stallSeconds` from 5 to 50 minutes
- `VoiceGuide.referenceFinalAt` from 6 to 20 s

Exactly 11 tests failed. Seven were on the pause (`NavigationModelTests` ×5,
`DriveTraceTests` ×2) and four on the voice (`VoiceGuideTests` ×3,
`VoiceGuideIntegrationTests` ×1). Nothing else failed.

**Guidelines that apply and hold:**
- **2.5.4** (location and audio background modes, used for navigation and
  spoken guidance).
- **2.5.5** (IPv6: a hostname behind Cloudflare).
- **4.2** (not a repackaged website).
- **5.1.1(i)** (policy linked in-app at `AboutView.swift:302`).
- **5.1.1(iv)** (with location refused, the user can type both ends).
- **5.1.1(v)** (no login).
- **5.1.2** (no tracking and no third-party code).
- **3.1** (free, no purchases).
- **1.5** (contact). This is satisfied only if the planned landing page
  carries the contact address (marketing plan §5.7). Today's
  `site/index.html` is a title and one link.

## 6. Prior conclusions revisited

Only the entries where I have new evidence.

1. **Apple's logo: `app-store-submission.md` §7.2 and §8 row 9 ("Blocked") are
   stale, and `release-plan.md`'s 2026-09-29 header is right.** The new
   evidence is runtime screenshots at `6f26edf` of every planning stage and
   the driving screen (§5). One caveat stays: the map card's bottom corners
   are clipped at a 22 pt radius (`PlanningView.swift:53-54`). The logo clears
   the curve today, so re-check it if that radius or the card's inset changes.

2. **Approximate location, an open gate ("untested", `release-plan.md` §10,
   `privacy-policy.md` §7 item 6), is now tested, and it fails silently.
   Blocker (§8), Verified in the simulator.**
   - **The experiment.** I made two runs of one drive, Northampton → Amherst,
     with the simulator moving along the route at 15 m/s
     (`simctl location start`).
     - **Precise on (the control):** the banner gave turn instructions, and
       the footer said "Recording this drive".
     - **Precise off** (toggled for Sunday Drive in Settings by the UI test,
       value 1 → 0): after 25 s of driving the screen still said **"50 ft
       away · Head to the start of your route"** and **"No GPS fixes yet —
       nothing is being recorded."**
   - **Why fixes are rejected.** `isUsable` rejects any fix worse than 65 m
     (`LocationManager.swift:40`, `:127-131`), and an approximate grant
     reports kilometres. So during a drive no fix ever reaches `onFix`
     (`:283-289`).
   - **Why the screen says "50 ft".** `distanceToRouteStart` stays 0, and
     `distanceText` floors at 50 ft (`NavView.swift:186`, `:515`). So a drive
     with no position claims to be 50 ft from its start, for the whole drive.
   - **Planning.** "My Location" falls back after 8 s to the coarse fix
     (`:204-210`), so a loop can start kilometres from the user.
   - **What is missing.** Nothing calls `requestTemporaryFullAccuracyAuthorization`,
     and there is no `NSLocationTemporaryUsageDescriptionDictionary`.
   - **Fix, about 25 lines.** Check `accuracyAuthorization`. Ask for temporary
     full accuracy, or say "Turn on Precise Location" in the banner. Draw
     "Waiting for GPS" instead of a distance when there is no fix.

3. **Attachment 6 §2.5 (`legal-and-ip-audit.md` item 5).** The fix
   ("record snapped coordinates, not geocoder output") never landed:
   `DriveTrace.swift:121` and `:126` still write the geocoder's point. The
   redesign then added a second store the audit never saw, the permanent,
   user-facing `Recents` list of `MKLocalSearch` coordinates
   (`Recents.swift:17-18`, `RouteModel.swift:182-189`). The enforcement risk is
   still low, but there are now two stores. The cheapest fix for both is to
   persist the route endpoint the server returned (OSM-derived) instead of the
   geocoder's coordinate.

4. **"The rate limit is fine" (`hosting-options-findings.md:819-822`).** The
   premise has moved. That sizing counted requests. A cold loop costs about 6–7× a
   two-arm route (2.0–6.2 s against 0.34–0.93 s tonight), and its rejoin shares a lock
   with planning. See K-1.

5. **`release-plan.md` §10 "`MARKETING_VERSION` … Done".** It was a no-op. See
   K-2.

6. **`LoopModel.swift:44-50`**, "the home screen came to offer a 6-minute loop
   after a test run": it still does. See K-3.

7. **`consumer-polish-brief.md`'s four "open" items no longer describe the
   tree.**
   - #3 (the compact sheet) and #4 (the pin behind the sheet) went with the
     sheet in the redesign.
   - #5's glass verdict buttons are now opaque cards (`NavView.swift:345`).
   - #6's stranded location task is fixed in `LocationManager`: waiters are
     an array (`:70-81`), and a superseded one-shot is answered
     (`:189-199`).

   Nothing there is left to dispatch.

## 7. Undetermined

| Item | Why tonight cannot settle it | What would | Which way it moves the verdict |
|---|---|---|---|
| Background and locked-phone guidance, recording and rerouting | The simulator lets background audio and location through (brief trap 5) | One real drive on the phone with the screen locked, reading the trace's `phase` records | A failure would add a Blocker: silent guidance on the main path. `voice-guidance-plan.md` measured 23/23 on the phone on 2026-08-30, so I expect it to hold |
| Whether Cloudflare's 60/min rule is live | Probing production is out of scope, and a block would land on the owner's own IP | Look at the WAF rule in the dashboard | If it is not live, K-1 gets worse: one script is a denial of service |
| K-1 on the box | Tonight's load average reached 114, and the box has slower cores and no other tenants | The capacity probe run against a second process on the box, or against a copy of it | It would only shift K-1's ratios. The lock-sharing mechanism does not depend on the machine |
| AR-1 and AR-2 in App Review's hands | Only App Review can say | Submitting | AR-1's fix costs an hour, so it is in the verdict regardless. AR-2 could turn out to be a Blocker if the reviewer reads 2.5.14 onto a location log |
| AR-4 legally | This is a statute reading, not advice | A lawyer, or simply removing the in-drive buttons (5 lines) | Removing them makes the question moot |
| Approximate location on a real phone | Settled in the simulator (§6 item 2). A phone's coarse fixes could differ in detail | Precise Location off, then one short drive | Only the wording. The 65 m gate rejects anything coarse |
| Which OSM-closed roads are gated, as against merely unplowed | OSM does not say reliably | Local knowledge, or the state DOT seasonal-closure lists | It only changes the wording of C-1's danger, from misled to stranded, not whether it is a Blocker |
| Dynamic Type at runtime | Neither method of setting AX5 took effect in this simulator | One launch at AX5 on the phone | It confirms K-5. The fixed-size font calls leave little room for doubt |

**What this review did not cover.** I read these only in passing or not at
all, so no finding about them should be inferred from their absence:
- `pipeline/score.py` (+352 since `9163cf6`) and `pipeline/landcover.py`.
  Their output was checked indirectly, through the score distribution in C-1,
  but they were not code-reviewed line by line.
- `graph.py`'s changes.
- `RouteResults.swift`, `Models.swift`, `TuneView.swift`, `BeautyType.swift`
  and `Geo.swift`.
- The rest of `DriveTrace.swift`.
- `tools/`.
- The Oracle box.
- Any real drive.

## 8. Verdict

**SUBMIT AFTER** the four blockers below, and do the "before L" list in the
same binary.

**The bar** is the brief's default, in four parts:
1. App Review is likely to pass it the first time.
2. No defect puts a driver in danger, strands them or misleads them on the
   main paths (plan, drive, reroute, arrive and end, for both a route and a
   loop).
3. There is no live breach of any term the app or its listing is bound by.
4. Nothing makes the planned launch undercut itself.

**How 6f26edf fares against it:**
- **Part 1** holds only once AR-1's review notes exist.
- **Part 2** fails three times.
  - Winter closures (C-1): as shipped, the app would send drivers over roads
    closed since Oct 15, and more close on Nov 1.
  - On loops, the escape hatch (K-7) does not go home.
  - With Precise Location off, the drive shows "50 ft away" and never
    navigates (§6.2).
- **Part 3** holds. The Apple logo is clear (§5, §6.1), and the route-guidance
  notice is in-app. The EULA field and the §2.5 stores are known, low-risk
  items.
- **Part 4** fails through M-1 and M-2, and both clear once C-1 and AR-1 are
  fixed.

### The blockers

| # | Finding | Where the fix lives | Cheapest fix | Size |
|---|---|---|---|---|
| 1 | **K-7.** On a loop, "Switch to fastest" drives to the far point: 4.4–6.3× longer than the fastest way home | **Build** | In `switchToFastest`, drop the loop waypoint and word the dialog "Head home the fastest way" | About 3 lines and one test. Under an hour |
| 2 | **§6.2, approximate location.** Precise Location off means no fix is ever accepted. The drive shows "50 ft away · Head to the start of your route" and never navigates (reproduced) | **Build** | When `accuracyAuthorization == .reducedAccuracy`, request temporary full accuracy with an `NSLocationTemporaryUsageDescriptionDictionary` purpose, or show "Turn on Precise Location to navigate" with a Settings link. Draw "Waiting for GPS" instead of a distance when there is no fix | About 25 lines. An hour |
| 3 | **AR-1.** A reviewer outside New England meets only an error on both front doors | **Package**, plus a server copy change | App Review notes with a test route and a loop start, the reason the region is limited, and a screen recording. Server copy that says what works: "Type a town there as your start" (marketing plan §5.10.2, reworded) | Notes: an hour. Copy: minutes, with no build |
| 4 | **C-1.** Routes, loops and reroutes use roads OSM marks closed for winter, and the score prefers them | **Server** (gates L, not the upload) | A startup mask in `Router.__init__`: the 190 flagged ways, joined to edges by geometry, set to `+inf` in `_weights` during their closed months. Add "seasonal roads" to "What it does not do". The ALT bound stays admissible, because closing edges only lengthens true costs | About 60 lines, a small side table, one test (for example, Stowe → Jeffersonville in January avoids VT‑108). Half a day. Deploy before L |

### Before L, in the same binary where it is a build change

These are Major, cheap and worth their cost. None blocks the upload.
- **AR-2.** Add explicit consent for recording, or record only in the owner's
  build. About 40 lines. It could become a rejection under 2.5.14.
- **AR-3.** Correct the privacy page's "three settings" and add "Clear recent
  destinations". Minutes for the page, about 15 lines for the control.
- **AR-4 and C-2.** Hide the in-drive rating buttons while moving. About 5
  lines.
- **K-1.** Give loop rejoins their own lock, answer 503 instead of queueing,
  and fix the timeout message. About 30 lines, split between server and
  client.
- **K-2.** Wire `CFBundleShortVersionString` and `CFBundleVersion` to the build
  settings. Two lines. Do it now, because the *second* upload depends on it.
- **K-6.** Swap the iOS 18-only symbol. One line.
- **K-10.** Pluralise "1 miles" before the App Store screenshots are taken.
  One line.
- **C-3.** Make the dial's headline print what the minutes buy (the gain, or
  "turns X into Y"), not the scenic route's total. About 10 lines.

**Can wait for 1.0.1:** K-5 (Dynamic Type, a mechanical change at 81 sites),
K-3, K-4, K-8, K-9, C-4 and M-3.

**The plan (marketing).** Build the §6.3 lists without closed-in-season roads.
Point October's one-shot posts at southern New England and at roads open all
year. Keep the northern mountains for the spring opener (M-1). Change the
captions to "type the town you'll start from" (M-2).

**Can this happen before L?** Yes. Blockers 1–3 are an afternoon, and
blocker 4 is a server change that can be deployed while the build is in
review. That leaves the package items `release-plan.md` §10 already lists: the
EULA field, export compliance, screenshots, description, category and the name
reservation. There is also membership, which is not code.

**Conditional on:**
- Background and locked-phone behaviour holding on the phone (§7), as it did
  on 2026-08-30.
- Nobody reading AR-2 as a 2.5.14 rejection. If a reviewer does, the fix is the
  consent switch already listed.

**Not reopened:** the name, the subtitle, the free knockout screen, no
privacy counsel, US-only, Oracle, free with a $0 budget, and Apache-2.0.

---

## Reproducing this

Commands in the order I ran them. `<main>` is the main checkout, `<wt>` this
worktree at `6f26edf`, `<scratch>` any directory outside the repository, and
`<udid>` a simulator you created. Nothing here writes to the repository.

**1. Pin, then run both suites.**
```bash
git -C <wt> rev-parse HEAD        # 6f26edf8cc00e8dedebd836a03a6798c34af7b19
cd <wt> && SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python -m pytest -q tests > <scratch>/pytest-ne.log 2>&1
PORT=5391 SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python server/serve.py   # leave 5057 empty
cd <wt>/ios && xcodegen generate
xcrun simctl create review com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-4
xcrun simctl boot <udid> && xcrun simctl bootstatus <udid> -b
TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:5391 xcodebuild test -project SundayDrive.xcodeproj -scheme SundayDrive -destination 'id=<udid>' -derivedDataPath <scratch>/dd > <scratch>/ios.log 2>&1
```

**2. K-2, the version settings.**
```bash
xcodebuild build -project SundayDrive.xcodeproj -scheme SundayDrive -destination 'id=<udid>' -derivedDataPath <scratch>/dd-ver MARKETING_VERSION=9.9 CURRENT_PROJECT_VERSION=42 > <scratch>/ver.log 2>&1
/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" -c "Print :CFBundleVersion" <scratch>/dd-ver/Build/Products/Debug-iphonesimulator/SundayDrive.app/Info.plist   # 1.0, 1
# The traces' own record. This prints only the version and start time, never a coordinate:
for f in <main>/traces/*.ndjson; do head -1 "$f" | python3 -c "import sys,json; d=json.loads(sys.stdin.readline()); print(d['started'], d['app'])"; done
```

**3. C-1, the closure scan.** pyosmium, using extract.py's own filter. It
should report 565,410 drivable ways, matching `roads.parquet`.
```python
import osmium
DRIVABLE = {...}                      # pipeline/common.py:11-16
class H(osmium.SimpleHandler):
    def node(s, n):                   # remember barrier=* nodes and their access tags
        ...
    def way(s, w):
        t = w.tags
        if t.get("highway") not in DRIVABLE: return
        if t.get("access") in {"private", "no"} and t.get("motor_vehicle") != "yes": return
        # keep motor_vehicle/motorcar/vehicle = no|private, every *:conditional,
        # seasonal, winter_service, toll, and the way's node refs
H().apply_file("<main>/data/raw/new-england-latest.osm.pbf", locations=False)
```
"Winter-closed" means one of three things:
- a `*:conditional` containing `no` and a month, `winter` or `snow`
- `winter_service=no`
- `seasonal` ∈ {yes, summer, spring;summer;autumn, no_snow}

Join to `graph_edges.parquet` by edge midpoint within 1 m of the way, in EPSG:26986, then weight `score` by `length_m`.

**4. C-1 and K-7 against the local server.**
```bash
curl -s -X POST --data "from=44.4654,-72.6874&to=44.6437,-72.8290&pref=0.5" http://127.0.0.1:5391/api/route   # Stowe -> Jeffersonville: steps name VT-108
curl -s -X POST --data "from=44.1123,-72.8565&to=44.1334,-73.0790&pref=0" http://127.0.0.1:5391/api/route      # Warren -> Bristol: Lincoln Gap Road
curl -s -X POST --data "from=44.4654,-72.6874&km=60" http://127.0.0.1:5391/api/loop                             # take meta.turnaround and a point 8 km along
curl -s -X POST --data "from=<point>&to=44.4654,-72.6874&via=<turnaround>&pref=0" http://127.0.0.1:5391/api/route   # what the app asks for
curl -s -X POST --data "from=<point>&to=44.4654,-72.6874&pref=0" http://127.0.0.1:5391/api/route                    # the fastest way home
```
For loops against closures, request every sector in `alternatives` at 40 and
80 km from Stowe, Warren, Jackson and Jefferson, and intersect each loop
line with the closed ways buffered by 3 m.

**5. Loop length and catalogue.**
- **Starts.** Seeded draws of graph junctions:
  `np.random.default_rng(20260930).choice(len(nodes), 30, replace=False)` over
  `graph_nodes.parquet`.
- **Length.** A 40 km request per start, then every sector in `alternatives`.
  Error is `(meta.km - meta.target_km) / meta.target_km`.
- **Catalogue.** For the first 8 starts, every sector at 30/40/50/60 km. A
  loop counts as distinct if it shares less than half its 3-decimal-degree
  cells with every loop kept so far.

**6. K-1, capacity.** Local only, never against the live API.
- **Idle baseline.** Time `/api/route` (Boston → Worcester, pref 0.5 and pref
  0), a `via` rejoin and `/api/health`, with nothing else running.
- **Load.** Start 1 or 4 threads posting cold 40 km loops from fresh seeded
  starts (`default_rng(7)` or `(11)`), back to back, for 45–60 s, and repeat
  the same timings.
- **Discipline.** Check `ps` and `uptime` first. Quote the ratios, and run
  each measurement twice.

**7. The UI walkthrough.** This drives the real app. Scratch only.
1. `git archive 6f26edf ios | tar -x -C <scratch>/ui`.
2. Add a `bundle.ui-testing` target, `SundayDriveUITests`, to the copied
   `project.yml`, with a test that:
   - taps "Got it"
   - taps "Directions"
   - types `Northampton, MA⏎` and `Amherst, MA⏎`
   - taps "Start driving"
   - calls `XCUIScreen.main.screenshot()` into a kept `XCTAttachment` at each
     step
3. Set the location and grant permission:
   `xcrun simctl location <udid> set 42.3251,-72.6412` (Northampton), or
   `37.3349,-122.0090` (Apple Park) for AR-1, then
   `xcrun simctl privacy <udid> grant location app.sundaydrive`.
4. Run with `xcodebuild test … -only-testing:SundayDriveUITests`.
5. Export the screenshots with
   `xcrun xcresulttool export attachments --path <result>.xcresult --output-path <dir>`.

For K-3, read the preferences afterwards:
`plutil -p "$(xcrun simctl get_app_container <udid> app.sundaydrive data)/Library/Preferences/app.sundaydrive.plist"`.

**8. The mutations.** In scratch copies only.
- **Backend.** In `pipeline/router.py`, add `h *= np.float32(1.2)` before
  `return h` in `_alt_bound`. Run
  `SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python -m pytest -q tests/test_routing.py -k TestFastestArm -p no:cacheprovider`.
  Expect 5 of 8 to fail.
- **iOS.** Change `stallSeconds` to `50 * 60` and `referenceFinalAt` to `20`.
  Run `xcodebuild test … -only-testing:SundayDriveTests`. Expect exactly the 11
  pause and voice tests to fail.

**9. K-6, symbol availability.** Read `symbols` and `year_to_release` from
`/System/Library/CoreServices/CoreGlyphs.bundle/Contents/Resources/name_availability.plist`,
then compare them with every `"a.b"` string literal under `ios/Sources`.

**10. Web sources, read 2026-09-30.**
- App Review Guidelines: `developer.apple.com/app-store/review/guidelines/`
  ("Last Updated: June 8, 2026").
- M.G.L. c.90 §13B: `malegislature.gov/Laws/GeneralLaws/PartI/TitleXIV/Chapter90/Section13B`.
- M.G.L. c.90 §1, the definition of "hands-free mode": `malegislature.gov/Laws/GeneralLaws/PartI/TitleXIV/Chapter90/Section1`.
- RDAP: `rdap.verisign.com/com/v1/domain/jameskouvlis.com`.

**11. C-3, the census replay.** From `docs/route-census/census-routes.csv`,
take the `weights == shipped` rows: the `fastest` arm, and the `scenic` arm at
pref 0.5. Then:
1. Apply the server guard: when the scenic `mean_score` is below the fastest,
   the scenic arm becomes the fastest.
2. Round minutes to whole numbers.
3. Mark `isSameDrive` when the extra minutes are ≤ 0 and both `mean_score`
   values agree at one decimal.
4. Convert beautiful miles to whole miles with `rint(km / 1.609344)`.
5. The printed figure is the scenic arm's beautiful miles. The gain is scenic
   minus fastest.

**12. §6.2, Precise Location.** A scratch UI test opens Settings with
`XCUIApplication(bundleIdentifier: "com.apple.Preferences")`, then walks
Privacy & Security → Location Services → Sunday Drive. Search does not index
the app. It turns **Precise Location** off with a coordinate tap near the
switch's right edge, because a plain `.tap()` on the element did not flip it.
It then starts Northampton → Amherst while the host plays
`xcrun simctl location <udid> start --speed=15 42.3190,-72.6310 42.3375,-72.5880 42.3490,-72.5480 42.3700,-72.5200`.
The control is the same run with Precise on.
