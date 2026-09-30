# Pre-submission review: verdict

**Status: reviewed `6f26edf`. Verdict: PROVISIONAL (baselines, conceptual and code drafted; App Review and market in progress).**

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
| What else was running | At least eight other Claude Code sessions, one running its own `pytest` over the whole suite, a booted simulator (`e2e-overnight`) belonging to another session, and an unrelated Python app. All timings below are therefore quoted as ratios or as order-of-magnitude figures |

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
- the leaves
- the daylight
- the plowing

The app's own "What it does not do" list (`BeforeYouDriveView.swift:51-62`)
names no live traffic and no lane guidance. It does not mention that roads
close.

**Reproduce.** Scan the PBF with the script in *Reproducing this*, then POST
`from=44.4654,-72.6874&to=44.6437,-72.8290&pref=0.5` to a local `/api/route`
and read the step names.

**Prior art.** None. `git grep -iE "seasonal|winter|conditional|barrier"` over
`docs/` and `pipeline/` finds only the turn-restriction comment. The marketing
plan (§1, §7) treats seasonality as demand, not as road access.

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

### C-3. The one instrument that could validate the score is shipped so that it can never report back — **Major**

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

## 2. Market

Not started.

## 3. Code

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

Here is what one probe (`capacity.py` in *Reproducing this*) measured. Tonight's
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

## 4. App Review

Not started.

## 5. Attacked and held

Not started.

## 6. Prior conclusions revisited

Not started.

## 7. Undetermined

Not started.

## 8. Verdict (provisional)

**PROVISIONAL.** No section is finished, so there is no verdict yet. If this
line is still here in the morning, the session ran out before any section
finished and nothing below it should be read as a result.

## Reproducing this

Not started.
