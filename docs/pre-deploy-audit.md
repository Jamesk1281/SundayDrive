# Pre-deploy audit: `usa` at `ea87a2a` onto the Oracle box

**Verdict: deploy after the push.** The national server is fit to replace New
England for today's TestFlight testers. What stands between it and
`server/deploy-oracle.sh --ref usa` is the owner's to do: push `usa` (and
`main`, so the rollback works), load the box key, and run the dry-run, which
must show the disk fits. Separately, and more urgently than the deploy itself,
**renew `jameskouvlis.com` before 2026-10-28 18:52 UTC.**

This is an evaluation of `usa` at `ea87a2a` on 2026-10-25, against the brief
`docs/pre-deploy-audit-brief.md` (committed unchanged beside this file).
Nothing was pushed, deployed or changed, on the box or anywhere else. Evidence
is labelled *measured* (a command and its output) or *read* (file:line, at
`ea87a2a` unless another ref is named).

## Before deploy, ranked

1. **Renew the domain.** It is not a deploy step, but it outranks the deploy.
   Every installed build and the tunnel hostname name `api.jameskouvlis.com`.
   *Measured* (RDAP, `rdap.verisign.com/com/v1/domain/jameskouvlis.com`,
   database updated 2026-10-25 05:07 UTC): expiration **2026-10-28 18:52:52
   UTC**, unchanged. Last changed 2026-08-12. Status: client delete, renew,
   transfer and update prohibited. Nameservers: Cloudflare (anna, brett).
   *Owner:* renew it at the registrar, then re-check RDAP for a 2027 date.
   Whether "client renew prohibited" means auto-renew is handled by the
   registrar or blocked is not something RDAP says. Look in the dashboard.
2. **Push `usa`, and push `main` with it.** The push is clean (see
   [Push safety](#2-push-safety-ready)). `main` matters for rollback: the
   rollback command `--region ne --allow-rewind` deploys local `main`, and
   the script refuses any branch whose local tip is not its origin tip
   (*read* `server/deploy-oracle.sh:103-105`). Local `main` (`4958941`) is 9
   ahead of `origin/main` (`2ed3f47`), so without the push the rollback stops
   at its first check, when it is most needed. The 9 commits are all inside
   `usa`, so pushing `main` publishes nothing new.
   *Owner:* `git -c http.version=HTTP/1.1 push origin usa main`. Then
   `git ls-remote origin refs/heads/usa refs/heads/main` must print `ea87a2a…`
   and `4958941…`. This origin has printed "Everything up-to-date" after a
   failed HTTP 400 push, so trust `ls-remote`, not the push's output.
3. **Load the key and dry-run. The disk check must pass.** ssh was not
   available to this audit (the key has a passphrase and is not in the agent),
   so the box's free disk is unmeasured. The first national deploy copies
   **19.73 GB** (*measured*: the 94 pack files at 11.88 GB, the 9 parquets at
   7.85 GB) and refuses to start unless **21.73 GB** is free. The script checks
   this before it writes anything (*read* `deploy-oracle.sh:308, 337-340, 363, 368`),
   so a box without room fails safe.
   *Owner:* `ssh-add --apple-use-keychain ~/.ssh/scenic_oracle`, then
   `server/deploy-oracle.sh --ref usa --dry-run`. Proceed if it ends
   "dry run: would restart the API" and prints no `PROBLEM`.
4. **Pick a quiet time and tell the testers.** The deploy restarts the API
   once. The copy (about 14 min to write and 14 to verify at the rated
   24 MB/s) happens while New England keeps serving. The cold start that
   follows means about 2–3 min of 502 (*read* `DEPLOY-oracle.md` Part 14). A
   tester mid-drive in that window sees "The routing service isn't reachable
   right now" and the app retries at 15, 30 and 60 s (*read*
   `main:ios/Sources/NavigationModel.swift:681-683`). The copy also runs at
   the Mac's upload speed. The 2026-09-28 upload measured 24 MB/s from the
   network used then. On a slower uplink the copy is longer, but `rsync
   --partial` resumes.
5. **Right after it: switch the UptimeRobot keyword and add the route
   monitor.** Otherwise the node-count monitor alerts on a correct box (see
   [Monitoring](#monitoring)).
6. **Accept, don't fix: today's builds show four rare refusals as "isn't
   reachable".** See [TestFlight](#4-todays-testflight-builds-against-the-national-server-ready-with-four-known-regressions).
   Nothing is unsafe or lost. The fix is the next TestFlight build from
   `usa`, which reads these errors (unit I, 2026-10-20). Ship that build after
   the deploy ("server before phone", *read* `DEPLOY-oracle.md:1042-1066`).

Not on this list:

- The low-scenery fallback. The deploy should not wait for it: see
  [section 6](#6-the-low-scenery-fallback-ship-now-redeploy-after).
- Growing the boot volume. It is recommended, but not needed for the first
  deploy: see [section 1](#1-the-box-ssh-not-available-dry-run-stopped-at-step-1).

## Before submission, ranked

None of these holds the deploy.

1. **Raw TIGER names in instructions (review #4 P-7). Still present at
   `ea87a2a`.** *Measured*, Golden → Red Rocks (39.7555,-105.2211 →
   39.6654,-105.2057). The scenic arm reads "Take the exit onto CH 93 South",
   then "Continue onto CH 93", "Continue onto I 70 BUS", "Continue onto County
   Highway 93". The fastest reads "Take exit 259 toward US 40 / CH 93:
   Morrison", then "Turn left onto County Highway 93". CO 93 is a state
   highway. Same request: "Take the 2nd exit onto Heritage Road" three times
   running, one per roundabout. *Change:* normalise TIGER county-highway
   names and refs, prefer state refs, and expand `CH` in `VoiceGuide`, or drop
   it. Collapse repeated identical roundabout steps.
2. **Unbridged islands are called "outside the contiguous United States"
   (review #4's island case).** *Measured* `OUTSIDE_COVERAGE` with "Sunday
   Drive covers the contiguous United States, and that point is outside it."
   for Nantucket, Martha's Vineyard, Block Island, Washington Island (WI),
   Beaver Island (MI), Friday Harbor (WA), Isle au Haut, Vinalhaven and
   Ocracoke. Peaks Island → Portland routes (6.5 km, over the ferry). Today's
   NE server answers these islands with its own "outside the covered road
   network (currently New England)" (*read* `origin/main:server/app.py:412`),
   so testers lose nothing. App Review gets a false sentence, though, and an
   island start is an easy thing for a reviewer to try. *Change:* a
   sentence that names islands and ferries for a point that is inside the
   country but off the routable network.
3. **`NO_ROUTE_NEARBY` was not reachable on the real graph.** Every
   disconnected place tried snapped to nothing and became `OUTSIDE_COVERAGE`
   (above). The code is covered by a mocked test (*read*
   `tests/test_api.py:859-861`). Not a defect. It means the app's handling of
   that code cannot be exercised end to end before review.
4. **ETAs are fitted to New England speeds (review #4).** Not measured here,
   and not measurable without drives outside New England. The national copy
   already says "Travel times are modeled". *After* submission, unless the
   owner wants a sentence in the review notes.
5. **The concurrent-loop refusal (review #4 P-6).** *Measured*: three cold
   80 km loops sent at once gave two loops (0.61 s, 1.43 s) and **one
   `503 BUSY`**. That is the design (*read* `server/app.py:275-287`): one
   build and one waiter. The usa app shows the server's sentence. *After*
   submission.

## 1. The box: ssh not available, dry-run stopped at step 1

**ssh.** *Measured*:

```
$ ssh -i ~/.ssh/scenic_oracle -o BatchMode=yes ubuntu@129.158.208.92 ...
ubuntu@129.158.208.92: Permission denied (publickey).
```

The key is passphrase-protected (`ssh-keygen -y -P ''` fails). The agent
holds a different key (`SHA256:C0fwXN…`, not the box key's `SHA256:967azR…`).
As the brief says, this audit did not work around it. None of the seven box
commands ran, so **RAM, `df`, `lsblk`, the services and `DEPLOYED_COMMIT` are
unmeasured.**

**The dry-run.** *Measured*:

```
$ server/deploy-oracle.sh --ref usa --dry-run
==> checking origin/usa
deploy: could not read origin/usa. Push it (DEPLOY-oracle.md 0.1).
```

It stops at step 1 (`deploy-oracle.sh:103`), before any ssh. The real run
needs `usa` on origin at the same tip as local (item 2 above), and the key in
the agent (item 3).

**What could be read without ssh**, one request at a time (*measured*,
2026-10-25):

- `https://api.jameskouvlis.com/api/health` → 200 in 0.19 s,
  `{"nodes":794685,"routing_slots":801933,"status":"ok"}`. That is New
  England, on code that predates the `region`, `commit` and `pack` fields. It
  matches `origin/main`'s health handler, and `origin/main` is wholly inside
  `usa` (`git merge-base --is-ancestor origin/main usa`), so the deploy is a
  fast-forward with no `--allow-rewind`.
- `https://api.jameskouvlis.com/api/health/route` → 404 (Flask's HTML page).
  The route monitor can only be added after the deploy.

**Is the RAM 12 GB?** Unverified. The owner reports the resize. The dry-run
prints `memory: the box has … GiB`, and warns if a national deploy finds under
11 GB (`deploy-oracle.sh:345-350`).

**Does the data fit with the 2 GB margin?** It depends on `df`, which only the
dry-run can read. The thresholds, from the measured 19.73 GB (pack 11.88,
parquets 7.85):

| deploy | needs free on the box before it | fits on 50 GB? |
|---|---|---|
| the first national deploy | **21.7 GB** | almost certainly. A 50 GB volume with Ubuntu, the venv and ~1.5 GB of NE data should have about 40 GB free |
| a code-only redeploy (e.g. the low-scenery fallback) | nothing | yes |
| a later pack-only re-ship (11.88 GB beside the live pack) | 13.9 GB after the first deploy, so **33.6 GB** today | probably |
| a later full re-ship (every parquet and the pack) | 21.7 GB after the first deploy, so **41.5 GB** today | **probably not** |

**Should the boot volume grow first?** Not for this deploy, but before the
next full data re-ship. Growing to 100 GB is free under Always Free, runs
online, and doubles the Balanced rate to about 48 MB/s (*read*
`DEPLOY-oracle.md:843-881`). That halves the copy (about 7 min) and the cold
start (about 1–1.5 min of 502 instead of 2–3). That is a reason to do it
before the first deploy if the owner has the half hour. It has never been
done on this box, and the partition has to be grown by hand afterwards
(Oracle's "Extending the Partition for a Boot Volume"). Doing it in the same
sitting as the first national deploy stacks two unfamiliar steps, and the
deploy doesn't need it. **Recommendation: deploy first, grow the volume
before the next pack rebuild.**

## 2. Push safety: ready

Range `origin/main..usa`: **114 commits** (94 non-merge), 448 files,
+149,274 / −4,222 lines. *Measured* scans of every commit's diff and message
(`git log -p origin/main..usa`, 161,314 added lines indexed by commit):

| looked for | result |
|---|---|
| **Secrets**: private keys, `.p8`, `.pem`, `AuthKey_`, AWS/GitHub/Slack tokens, `password=`, `api_key=`, `secret=`, `token=`, tunnel tokens, `ocid1.`, Bearer | **clean.** The only hits are code identifiers (`PACK_FINGERPRINT`, an S3 `continuation-token` loop, "per tenancy" in prose) |
| **Absolute paths** `/Users/` | 28 added lines in 6 files at the tip: `tools/seasonal_risk/{q2_windows,q4_policies}.py`, `tools/seasonal_risk/README.md` and `docs/router-at-us-scale.md` carry `/Users/james./Desktop/myapps/SundayDrive/...`. Retired briefs in history carry the same. **Already public**: 11 commits on `origin/main` add that same path. Low. It reveals the account name and folder, nothing else. Optional cleanup: `SUNDAYDRIVE_MAIN`/relative paths in the two scripts |
| **Drive traces**: `drive-2026-`, `traces/`, clock times on streets | No trace file, no coordinates, no new trace IDs. Every `drive-2026-…` ID in the range is already on `origin/main` (`comm` of the two ID sets is empty). **One new detail**: `docs/national-copy.md:502`, `docs/app-goes-national.md:223` and `docs/review-fixes-app.md:375` quote "Sharp right onto Old North Dana Road" from the 2026-10-06 12:25 trace, a street name `origin/main` does not have. Low. It is a maneuver in a regression note, beside a trace ID that is already public. No HH:MM:SS-with-street patterns |
| **Mark-derived data** | `tools/national_scoring/results/ne_marks.csv`, `marks_ci.csv`, `tools/scenery_types/results/ne_marks_ci.csv` and `tools/western_landcover/results/ne_movement_and_marks.csv` hold only AUCs, counts and intervals, with no locations. `extract_marks.py` writes its located pickle outside the repo (its docstring says so) |
| **Outside-review findings** | No file named like a findings file in the range, and no reference to `independent-review-findings`. I compared every ≥50-character line of all four reviews' committed `docs/independent-review-findings.md` against the range. Every overlap is the app's own strings, which the reviews quoted ("outside the covered road network (currently New England)", the NE listing text), or measurements in briefs (the snap-cap brief's 100.2 s offshore request), which the brief allows |
| **The application** (memory rule) | No hits. "Northeastern" appears only as the marketing plan's school-press channel |
| **Large binaries** | none. 684 new blobs, 33.1 MB uncompressed. Largest: `app-store-screenshots/app-store-search-results-3840x2560.png` 2.3 MB, `tools/national_audit/legs.json` 1.7 MB. No `.parquet`, `.npy`, `.pickle`, `.ndjson`, `.p12`, `.mobileprovision`, `xcuserdata` or `.DS_Store`. Two screenshots opened (Bixby Creek, Moab loop) show simulated locations only |

**Push size, measured:** `git pack-objects --revs --thin` over `usa ^origin/main`
is **13.8 MB**.

**The HTTP/1.1 trap.** HTTPS pushes to this origin have failed with HTTP 400
and then printed "Everything up-to-date". Use
`git -c http.version=HTTP/1.1 push`, and confirm with `git ls-remote`.

## 3. The national server at `ea87a2a`, locally: ready

Started with the box's environment plus route options, which the box's base
unit sets (*read* `docs/route-options.md:5`):
`PORT=55641 SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_ROUTE_OPTIONS=1
SUNDAYDRIVE_PACK=data/pack-us SUNDAYDRIVE_DATA=data/processed-us`. It loaded in
seconds: `ready: 20,023,955 nodes (20,186,985 routing slots)`. It was stopped
by PID afterwards. Requests used the app's real shape: POST form, `w_*=1.00`,
`w_town=0.00`.

**Health**, *measured*:

- `/api/health` → `{"commit":"ea87a2a6ee98","nodes":20023955,"pack":"b0ba664cd701…","region":"the contiguous United States","routing_slots":20186985,"status":"ok"}`
- `/api/health/route` → 200, `route_ok`, Concord → Lexington 10.7 km in
  0.027 s. A repeat within the minute was served from the cache.

**Routes, menus, limits and loops from 18 states** (*measured*, all 200; the
latency range is over the 18):

| region | states |
|---|---|
| Northeast | VT (Stowe → Waitsfield), ME (Bar Harbor → Camden) |
| Southeast | NC (Asheville → Boone), TN (Gatlinburg → Townsend), FL (Key Largo → Islamorada) |
| Midwest | WI (Madison → Baraboo), MI (Traverse City → Leland) |
| Plains | KS (Manhattan → Council Grove), SD (Rapid City → Keystone) |
| Mountain West | CO (Denver → Estes Park), MT (Bozeman → Livingston), UT (Moab → La Sal) |
| Southwest | AZ (Sedona → Flagstaff), NM (Santa Fe → Taos), TX (Austin → Fredericksburg) |
| Pacific NW | OR (Portland → Hood River), WA (Seattle → Snoqualmie) |
| California | CA (Monterey → Big Sur) |

| request | result |
|---|---|
| route, no `options` | 18/18, 0.06–0.40 s |
| route, `options=1` | 18/18, 0.01–0.41 s, menus of 1–13 options |
| an option fetched in full (`leave`/`rejoin`, CO option 1) | 200, 0.19 s: 140.1 km, 68.1 beautiful km |
| `/api/loop/limit` | 18/18, ≤ 0.009 s. 400 km at most starts. 295–371 km in NC, TN and WI |
| 40 km loop | 18/18, 0.04–0.68 s. Two carry the retrace note (MT 6.1 km repeated, UT 11.3 km) |
| reroute with heading (Boulder, CO, heading 300) | 200, 0.06 s |
| reroute with heading and `declined_uturn` (Concord, MA) | 200, 0.10 s |
| loop rejoin with `via` (Moab) | 200, 0.02 s |
| reroute with heading, Boston → Madawaska (590 km, under the 650 km reroute cap) | 200, 1.38 s, 726 km |

**Every error code**, *measured*:

| code | status | request | time |
|---|---|---|---|
| `OUTSIDE_COVERAGE` | 400 | 400 km off the Atlantic; Toronto; a Honolulu loop; a Mexico City limit | 0.001–0.003 s |
| `TRIP_TOO_LONG` | 400 | Boston → Los Angeles (4,169.5 km). Also Greenwich, CT → Madawaska, ME (800.2 km), inside New England | 0.03–0.13 s |
| `LEG_TOO_LONG` | 400 | Boston → Worcester via Denver (`leg: 1`, 2,841.2 km) | 0.03 s |
| `NO_ROUTE_NEARBY` | — | not reachable on the real graph; see submission item 3 | — |
| `CLOSED_FOR_SEASON` | 404 | Idaho Springs → Mount Blue Sky summit; Glen House → Mt Washington summit | 1.5 s, 2.0 s |
| `BAD_INPUT` | 400 | `from=nan,nan`; missing `to`; `sector=UP` | 0.001 s |
| `START_TOO_FAR` | 400 | a reroute from 38.61,-109.57 (heading 160): `m: 782, max_m: 500` | 0.01 s |
| `BUSY` | 503 | one of three simultaneous cold loops (above) | 0.6–1.4 s |
| `LOOP_TOO_LONG` | 400 | a 400 km loop from Boston (`max_km` 398.4) and from Times Square (268.5) | ≤ 0.03 s |
| `SAME_ROAD` | 400 | two points 1 m apart | 0.03 s |
| `NOT_FOUND` | 404/405 | `/api/nothing`; GET `/api/loop/limit` | 0.001 s |

Seasonal roads routed around rather than refused, as they should be: Estes
Park → Grand Lake took 256 km around Trail Ridge Road, and Red Lodge → Cooke
City 374 km around the Beartooth.

**Concurrency**, *measured*. The 2026-10-08 Oracle probe's mix: Poisson
arrivals; 60% plans with `options=1`, 20% reroutes with a heading, 15% cold
loops (25–120 km), 5% rejoins. Starts are within 8 km of 48 cities across the
48 states. The run was 150 s at 0.5/s, then 120 s at 1.0/s, then the 3-loop
burst. 220 requests.

| phase | kind | n | p50 | p90 | max | over 20 s | answers |
|---|---|---|---|---|---|---|---|
| 0.5/s | plan | 53 | 0.43 s | 1.50 s | 2.45 s | 0 | 49 × 200, 4 × `OUTSIDE_COVERAGE` (points in water) |
| | reroute | 15 | 0.41 | 2.40 | 2.54 | 0 | 15 × 200 |
| | loop | 17 | 1.68 | 4.25 | 7.03 | 0 | 17 × 200 |
| 1.0/s | plan | 76 | 0.21 | 0.79 | 1.92 | 0 | 67 × 200, 9 × `OUTSIDE_COVERAGE` |
| | reroute | 28 | 0.19 | 0.43 | 0.72 | 0 | 26 × 200, 1 × `START_TOO_FAR`, 1 × `OUTSIDE_COVERAGE` |
| | loop | 15 | 0.47 | 3.66 | 5.09 | 0 | 15 × 200 |
| burst | loop | 3 | 0.61 | 1.43 | 1.43 | 0 | 2 × 200, **1 × `503 BUSY`** |

The rejoins in the mix were malformed by my generator (`to` = `from`, so 11 of
13 got `SAME_ROAD`). The smoke test's real rejoin answered in 0.02 s. No
`BUSY` was returned during the Poisson phases. Nothing errored with a 500, and
the server log has no traceback.

**Memory**, *measured* on the Mac (macOS has no `RssAnon`):

- Physical footprint, the closest thing to `RssAnon`: 3.28 GB idle after the
  smoke run, 3.38 GB after the load run. **Peak 3.6 GB**, against Part 14's
  5.5 GB alarm line and the box's 12 GB.
- RSS, which includes the mapped pack pages the process touched: **peak
  4.39 GiB**. So the 48-city run kept about 1 GB of the 11.9 GB pack hot.
- That leaves about 7 GB of a 12 GB box for page cache. Reclaim also stays
  safe: about 3.3–3.6 GB of 11.7 GiB is roughly 28–31% used, above the 20%
  floor (`DEPLOY-oracle.md` Part 12).

**How this relates to the box.** These are Mac numbers.

- An A1 core ran the New England graph build at about three quarters of an
  M2's speed (`DEPLOY-oracle.md:458-462`).
- On 2026-10-08 the box's single-request plan was 0.65 s p50. That was New
  England, at a time when its 1.5/s mix overloaded it (`docs/load-test-oracle.md`).
- Expect the box to be roughly 1.5–3× slower than the table above for warm
  requests.
- The difference the Mac cannot show is **cold pack pages**. On the box they
  come off a 24 MB/s disk, so the first routes in a region after a restart,
  or after the kernel drops pages, will be slower than here. By how much is
  unmeasured.
- Run Part 14's memory check (`fincore`, `/proc/pressure/memory`, `vmstat`)
  after the deploy and again after a day of traffic.
- At 1.0/s nothing here came near the app's 20 s timeout, and the Mac had
  head room. A box at 1.5–3× would still keep plans under about 5 s at that
  rate.

## 4. Today's TestFlight builds against the national server: ready, with four known regressions

The installed builds are `main`-era (`4958941` or earlier). *Measured*: I
compiled `main`'s own `ios/Sources/Models.swift` and `LoopModels.swift` (plus
a one-line stub for a display helper) into a harness. It decoded every body
captured above the way `main`'s `RouteService.send` and `failure(status:body:)`
do:

- **Every 200 decodes.** That is all 36 routes and menus, the option fetched
  in full, 18 loops, the reroutes and the rejoin. The new fields (`seasonal`,
  `turns_around`, `no_gain` later) are ignored. The `options` menu decodes into
  `main`'s `RouteOptions`, so the dial works.
- **Errors whose body is all strings are shown as written**:
  `OUTSIDE_COVERAGE`, `CLOSED_FOR_SEASON`, `BAD_INPUT`, `SAME_ROAD`,
  `NOT_FOUND`. `BUSY` reaches `.busy`.
- **Errors that carry numbers are unreadable** to `main`. It decodes error
  bodies as `[String: String]` (*read* `main:ios/Sources/RouteService.swift:348`).
  So `TRIP_TOO_LONG`, `LEG_TOO_LONG`, `LOOP_TOO_LONG` and `START_TOO_FAR`
  (and `NO_LOOP`, whose `nearest_km` is a number or null) become
  `.unreachable(status)`: "The routing service isn't reachable right now. Try
  again in a moment. (HTTP 400)". Today's NE server sends none of these codes
  or numbers (*read* `origin/main:server/app.py:390-605`), so for testers each
  one is new.

**What a tester in New England will see:**

- **Ordinary routes, menus, loops, reroutes and rejoins work.** The app's own
  New England check keeps their starts and pins in New England. The routes
  are the national graph's, which matched NE on 677 of 726 trips, the rest
  explained (`docs/router-at-us-scale.md:6`).
- **Long loops in southern New England are refused, and the refusal reads as
  an outage.** `main`'s slider runs to 400 km (*read*
  `main:ios/Sources/LoopModel.swift:59-60`). It never asks for the limit,
  because `/api/loop/limit` is new. *Measured* limits:

  | start | limit |
  |---|---|
  | Greenwich, Stamford, Danbury | 266–268 km |
  | New Haven, Hartford, Pittsfield | 291–297 km |
  | Springfield | 308 km |
  | Worcester, Brattleboro | 350–353 km |
  | Providence, Newport | 364–366 km |
  | Concord, MA | 386 km |
  | Cambridge, Boston, Lowell, Nashua | 396–398 km |
  | Manchester, Portsmouth, Portland, Burlington, Stowe, Bangor, Bar Harbor, Hyannis | 400 km |

  Above those limits a tester gets the "isn't reachable" sentence. Today's NE
  server builds them: *measured* on `main`'s code, a 400 km loop from Boston
  came back in 2.3 s on the Mac.
- **Trips over 310 mi in a straight line** (Greenwich → northern Maine) get
  the same sentence. They are rare inside New England.
- **A reroute from more than 500 m off any routable road** (`START_TOO_FAR`)
  is classified as a lost connection, not as the server's answer (*read*
  `main:ios/Sources/NavigationModel.swift:2155-2160`). It retries at 15, 30
  and 60 s, where today's server would have routed from the far road. This
  happens only on roads the graph doesn't route, such as private drives.
  *Measured*: 1 of 43 random reroutes.
- **Island starts** now read "covers the contiguous United States" instead of
  "currently New England" (submission item 2).

None of these endangers a driver or loses a drive. All of them go away with a
TestFlight build from `usa`, whose `RouteService` decodes error bodies with
numbers (`docs/review-fixes-app.md`, "Refusal"). **Verdict: not a deploy
blocker.** Push a `usa` TestFlight build soon after the deploy.

## 5. Operations

### Monitoring

**State:** unknown. UptimeRobot can't be read from here. Production answers
404 on `/api/health/route` today, so that monitor cannot exist yet.

**Owner, right after the deploy** (`DEPLOY-oracle.md:748-791`):

1. Change the node-count monitor's keyword from `794685` to **`20023955`**.
   The script prints this line itself.
2. Add the keyword monitor: name `Sunday Drive routing`, URL
   `https://api.jameskouvlis.com/api/health/route`, keyword **`route_ok`**
   (alert when it is missing), 5-minute interval, 30 s timeout, the same
   alert contact.
3. Check by hand: `curl -s https://api.jameskouvlis.com/api/health/route`
   must show `"status":"route_ok"`.

**Verdict:** ready. The steps are written, and the endpoint works (*measured*
above).

### Rate limit

**State:** unknown. The Cloudflare dashboard can't be read from here. The
rule matches the hostname, so a rule made for the laptop still applies (*read*
`DEPLOY-oracle.md:684-699`).

**Owner:** Cloudflare → `jameskouvlis.com` → Security → WAF → Rate limiting
rules. Confirm a rule on `http.host eq "api.jameskouvlis.com"`, counted by IP,
at **60 requests/minute**. Add it if there is none. The national graph doesn't
change the reasoning behind the cap: one process, four threads, and the GIL.

**Verdict:** ready to deploy without it, since the only users are a few
testers. It must be in place before submission.

### Rollback

**Today, `--region ne --allow-rewind` is a real rollback**, because no
national app is public. *Measured* that it works:

- `main`'s code (`git archive main`) on the Mac's `data/processed-ne` loads
  794,685 nodes and prints all four closure lines. It plans Stowe →
  Waitsfield with options (0.67 s), Concord → Lexington and a heading
  reroute (0.35 s each). It refuses Mt Washington as closed for the season,
  and builds a 40 km Stowe loop and a 400 km Boston loop.
- The NE parquets stay on the box through a national deploy, so the rollback
  copies nothing (*read* `DEPLOY-oracle.md:1068-1075`).

Two conditions:

1. **It needs `main` pushed** (before-deploy item 2). Otherwise it stops at
   step 1.
2. **It does not return exactly to today's production.**
   - It deploys `main` at `4958941`, whose 9 unpushed commits include the
     safety quick-fixes, never deployed.
   - It ships the Mac's NE closure tables (`seasonal_closures`,
     `closed_to_cars`, `osm_unpaved`), rebuilt 2026-10-23.
   - *Measured*: that pair reports 801,941 routing slots. Production reports
     801,933.
   - The pair works, as above, but it is a new NE build, not today's.

   If the owner wants a byte-for-byte rollback, the target is `origin/main`
   (`2ed3f47`) with the box's own `processed-ne`. The script cannot express
   that while local `main` is ahead.

**Should the previous pack be kept for a national rollback?** Not now:

- Until a national build is public, rolling back to New England is the safer
  rollback, and it costs no disk.
- The next national redeploy, the low-scenery fallback, is code only. A bad
  one rolls back with `--ref <the previous branch> --allow-rewind`, and the
  data matches.
- **Once a national app is public**, going back to New England breaks it.
  Before any pack rebuild after that, keep the previous pack beside the live
  one. That needs another 11.9 GB, which is another reason for the 100 GB
  volume.
- The script has no keep-previous mode today. The swap renames over the live
  files (*read* `deploy-oracle.sh:425-437`).

### What the deploy restarts, and for how long

- **Restarted:** `sundaydrive-api` only, once, after the data is verified and
  the code is checked out. `cloudflared` is not touched.
- **Dependencies:** no reinstall. `server/requirements-serve.lock.txt` is
  identical between `origin/main` and `usa` (*measured*,
  `git diff --stat` is empty).
- **Timing:** about 14 min to copy and 14 to verify, all while New England
  keeps serving. Then the swap and restart: 2–3 min of 502 while 3.2 GB is
  read at 24 MB/s. The script waits up to 600 s, then checks `nodes`,
  `region`, `commit`, `pack` and the public hostname
  (`deploy-oracle.sh:453-528`).
- **Base unit:** route options stay on, because the drop-in overrides only
  the data, pack, region and commit lines. Confirm afterwards with
  `systemctl show -p Environment sundaydrive-api`.

## 6. The low-scenery fallback: ship now, redeploy after

**State at the time of this audit** (*read*): branch
`claude/low-scenery-fallback-9b62f0` has one commit, `6dc157a`. It touches
`server/app.py` (+96/−18), the app, and tests. Its answer doc is still
untracked, and the session is still working. **It is not ready to merge.**

Why the deploy should not wait for it:

- **It is server-side and additive.**
  - On plans (`options=1`), a scenic arm that gains under 0.5 mi of
    beautiful road falls back to the fastest.
  - On every path, a scenic arm with fewer beautiful km than the fastest
    falls back too.
  - The scenic Feature gains an optional `"no_gain": true`.
  - `main`-era builds ignore the new key (*measured*: their models ignore
    unknown keys) and show "Same as the fastest route", which is true.
  - Nothing in it changes an error body or a field type.
- **It fixes a submission problem (review #4 P-5), not a tester-safety
  one.** The deploy bar doesn't need it.
- **Its redeploy is cheap.**
  - It is a code-only change, so no data is copied.
  - The script pulls, restarts once, and waits.
  - That costs one more 2–3 min of 502 for a handful of testers.
  - Waiting instead keeps testers on New England and leaves the national
    server unexercised on the box, while the box's real cold-page behaviour
    is the biggest unknown left.

**Exception:** if it merges into `usa` before the owner sits down to deploy,
push and deploy them together and save a restart.

## Commands this audit ran against production

There were three requests in all, one at a time: `GET /api/health`,
`GET /api/health/route` (404), and the RDAP lookup at Verisign. Nothing else
touched the box, Cloudflare, UptimeRobot or App Store Connect. Both local
servers (national on 55641, `main`'s NE on 55642) were stopped by PID. No
simulator was created.
