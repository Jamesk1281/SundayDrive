# How much traffic the Oracle box can take

**Status:** measured 2026-10-08, 14:55–15:25 UTC, against the live box
(Ashburn, A1.Flex 2 OCPU / 8 GB, running `012a5f3` with route options on). This
is the "load test" item in `marketing-plan.md`'s phase 1 checklist and go/no-go
item 2. The probe and every raw result are in `tools/load_test/`.

**Verdict: good enough for the beta and an ordinary launch, not for a post
that takes off, until K-1 is deployed.** On ordinary routes the box degrades
gracefully and never fell over. Memory is not the limit. What breaks it is a
handful of people tapping **Loop** at the same moment. Four at once slow every
driver's reroute from 0.7 s to 17 s. The fix for that is already built
(`claude/loop-lock-contention`, `docs/loop-lock-contention.md`) and has not
been merged or deployed.

## The numbers

### One request at a time

The box with nothing else running. The SSH tunnel used for the test adds
about 0.04 s.

| request | p50 | p95 |
|---|---|---|
| plan (pref 0.5, options on) over all 194 routable OD pairs | 0.65 s | 1.07 s at p90, 1.57 s max |
| mid-drive reroute (no options) | 0.68 s | 0.76 s |
| loop rejoin (`via`) | 1.97 s | 2.21 s |
| cold loop, 25–80 km | 3.89 s | 4.24 s |
| cached loop | 0.07 s | 0.08 s |
| `/api/health` | 0.04–0.07 s | |

By trip type, plans range from 0.61 s (urban, parking lots) to 0.98 s
(cross-state).

**Through the public hostname**, a plan's p50 is 0.75 s against 0.72 s for
the same requests sent to the box directly, and health is 0.13 s against
0.04 s. The Cloudflare tunnel costs well under 0.1 s, which is nothing next to
routing.

### Plans only: the throughput ceiling

C clients, each sending plan requests back to back for 60 s, with random trips
from the OD set.

| clients | plans/s | p50 | p95 | max |
|---|---|---|---|---|
| 1 | 1.32 | 0.64 s | 1.37 s | 2.75 s |
| 2 | 1.72 | 1.12 s | 1.61 s | 1.96 s |
| 4 | 1.79 | 2.15 s | 2.71 s | 5.39 s |
| 8 | 1.72 | 4.37 s | 5.81 s | 7.26 s |
| 16 | 1.74 | 8.85 s | 10.85 s | 13.15 s |

- **The ceiling is about 1.75 plans per second.** Past two clients, extra
  clients only queue: latency grows linearly with load and throughput stays
  flat.
- Nothing failed at any level, and none of the 527 plans came near the app's
  20 s timeout.
- Under load, the box's CPU peaked at 68–70% of its two cores. That is the GIL
  and waitress's four threads (`serve.py:9-15`), not the hardware.
- The ceiling is a little flattering, because the busy guard skips route
  options once a second request is in flight. Under load, a plan does less
  work than an idle one.

### Loops beside drivers: K-1, on the box

L clients build cold loops back to back. Beside them, three clients drive:
one planning, one rerouting and one rejoining a loop.

| loop builders | loop p50 | rejoin p50 | plan p50 | reroute p50 |
|---|---|---|---|---|
| 0 (idle, above) | 3.9 s | 2.0 s | 0.65 s | 0.68 s |
| 1 | 10.8 s | 10.9 s | 1.65 s | 1.57 s |
| 2 | 17.4 s | 12.9 s | 1.83 s | 1.74 s |
| 4 | 17.0 s | 17.0 s | **16.2 s** | **17.4 s** |

- **One person building a loop** makes every rejoin wait about 11 s. The
  rejoin queues on `LOOP_LOCK` behind the build.
- **Two at once** push loops to 17–20 s, the edge of the app's timeout.
- **Four at once** fill all four waitress threads with queued loop builds.
  Plans and reroutes then wait about 17 s, 25 times their idle time, and only
  7 plans completed in 60 s. That is K-1 exactly as the pre-submission review
  described it, measured on production rather than on the Mac.

### A realistic mix, arriving at random

Poisson arrivals, 90 s at each rate. The mix is 60% plans, 20% reroutes, 15%
cold loops and 5% rejoins. The probe stops a rate once 40 requests are in
flight.

| rate | in flight (peak) | plan p50 / p95 | reroute p50 | loop p50 | over 20 s |
|---|---|---|---|---|---|
| 0.5/s (30/min) | 3 | 1.21 / 2.01 s | 0.69 s | 3.3 s | 0 of 43 |
| 1.0/s (60/min) | 12 | 2.08 / 9.66 s | 1.88 s | 11.2 s | 0 of 80 |
| 1.5/s (90/min) | 22 | 5.17 / 19.2 s | 3.69 s | 22.8 s | **13 of 132** (7 of 11 loops) |
| 2.0/s (120/min) | 40, capped after 30 s | 27.6 / 35.6 s | 26.8 s | 28.0 s | **41 of 60** |

- **0.5/s is comfortable.**
- **1/s works but is slow:** one plan in twenty waits about 10 s.
- **1.5/s overloads it,** and **2/s collapses it.**
- With loops in the mix, the real capacity is about **1 request/s**, not the
  1.75 that plans alone reach.

### What did not move

- **Memory.**
  - `MemAvailable` never fell below 2.69 GB, and swap stayed at 12 MB.
  - The service's cgroup grew from 4.25 to 4.70 GB, with a peak of 4.87 GB.
    That is the loop and cost-model caches filling. They are bounded
    (`LOOP_RESULTS_MAX = 16`, two cost models of 82 MB each), but worth one
    look after a busy week.
- **Stability.**
  - `NRestarts=0`, and nothing matching error, traceback, killed or OOM
    appeared in the journal during the test.
  - After the 2/s collapse, health was back at 0.03 s within seconds.

## In people

A person planning a trip sends about 4 requests over 2 minutes: the plan,
one or two option fetches as they turn the dial, and a re-plan if they touch a
slider or swap the ends. A loop user sends one or two cold loops, and a drive
adds a reroute or two. On those assumptions:

| load | requests/s | people planning at the same moment | planning sessions per hour |
|---|---|---|---|
| comfortable | 0.5 | about 15 | about 450 |
| slow but working | 1.0 | about 30 | about 900 |
| overloaded | 1.5+ | 45+ | |

The tighter limit, until K-1 ships, is people tapping **Loop** at once, not
total traffic. **Three or four loop builds in the same ten seconds** are
enough to stall every driver.

The marketing plan expects a beta of 50–200 people and a $0 launch. Six of
the eight scenic apps launched in 2026 have no ratings at all. At that scale,
the box has a wide margin. The case it cannot take today is the one the plan
calls a success: one short video that sends hundreds of people into the app
within an hour, most of whom try Loop first.

## The rate limit

The Cloudflare rule **is live**. It is tighter than `DEPLOY-oracle.md` Part
11 says.

- **It allows about 10 requests per IP in 10 s, then blocks that IP for about
  10 s.** In the first burst, the 8th request in 2.6 s got a 429. In a clean
  repeat, it was the 10th in 1.7 s. A steady 40/min (one request every 1.5 s)
  passed 18 of 18. The free plan only offers a 10-second period, so "60 per
  minute" was entered as 10 per 10 s. That is burstier than 60/min reads.
- **Can a real person hit it?** Probably not, but it is closer than it looks.
  A plan, five option fetches from turning the dial through every detent, and
  a few slider releases add up to about 10 in 10 s. A blocked phone gets
  Cloudflare's HTML 429, which the app shows as "isn't reachable (HTTP 429)".
  Phones behind carrier-grade NAT share one IPv4 address. Most US carriers give
  iPhones IPv6, which avoids that, but this was not measured.
- **It does not protect the box from one script.** Ten requests every 10 s
  from one IP is 1 request/s, the box's whole mixed capacity. Ten cold loops
  per 10 s is about 40 s of build work arriving every 10 s. With K-1 deployed,
  that stops mattering: a refused loop costs almost nothing, and one client
  can hold at most one build and one waiting slot.
- **Separately, Cloudflare answers 403 to the user agent `Python-urllib/3.x`.**
  A bot rule or Browser Integrity Check does this. The app's `CFNetwork`
  agent, `curl` and `python-requests` all get 200. It is harmless, but it
  explains a 403 if you ever probe the API from a stock Python script.

## What to do before launch

1. **Merge and deploy K-1** (`claude/loop-lock-contention`). This is the
   change that matters. It turns "the fifth person to tap Loop slows every
   driver to 17 s" into "the second person gets a polite busy, and drivers
   stay at about 1.2–1.8 times idle". Deploy the server before the phone build,
   as usual. Installed builds see the 503 as a server error, so they ask once
   more without a sector and then show the busy words. After deploying, do two
   things:
   - time a few cold 40 km loops on the box and set `LOOP_BUSY_WAIT_S` near
     their p90 (`loop-lock-contention.md`, item 2). The cold loops measured
     here took 3.9–4.2 s with nothing else running and 11–17 s beside other
     work, so 5 s is about right;
   - rerun `tools/load_test/run.sh after-k1 loops open --rates 0.5 1.0 1.5`
     to confirm the drivers' rows.
2. **Leave the rate limit as it is.** 10 per 10 s with a 10 s block is about
   right for a phone. If the dial or the sliders ever start sending more,
   raise it to about 20 per 10 s rather than lowering it. Once K-1 is out, the
   rule is not what bounds cost.
3. **Watch the Cloudflare request graph during launch week**, as the plan
   already says. As a guide: under about 30 requests/min the box is
   comfortable, 60/min is slow but working, and past 90/min people start
   seeing timeouts. The stop-posting rule (§8) should key on that.
4. **If more capacity is ever needed,** the lever is a second worker
   process, not more threads. CPU sat at 68–70% under full load, so two
   processes would buy perhaps 1.3–1.5× (unmeasured). Each process needs about
   4.7 GB, so it means resizing the instance to the 12 GB you are entitled to.
   That costs a stop/start, and Ashburn's A1 capacity is not guaranteed at the
   moment of the resize. At 9.4 of 12 GB, the memory share stays far above the
   20% idle-reclaim floor. Not needed for anything the marketing plan
   forecasts.

## Caveats

- **The probe waits up to 120 s; the app gives up at 20 s.** Waitress keeps
  computing a request whose client gave up, and a person who sees an error
  taps again. So under a real overload, abandoned work and retries make it
  last longer than it did here. The recovery measured here is the best case.
- **Each loop here was cold:** a new length from one of 115 starts. Real
  users asking the same loop twice get the 0.07 s cache hit, so this is
  pessimistic for loops.
- The client ran on a busy Mac (load average about 5). It only waits on
  sockets, so this does not move the server's timings, but it is why the box
  was reached over SSH and not over the LAN.
- **One replicate per row.** The throughput plateau repeats across four
  levels (1.72–1.79/s), so that figure is solid. Single p95s from 10–20
  samples are not.

## Reproduce

```bash
ssh -N -L 15957:127.0.0.1:5057 -i ~/.ssh/scenic_oracle ubuntu@129.158.208.92 &
tools/load_test/run.sh idle idle
tools/load_test/run.sh sweep sweep
tools/load_test/run.sh mixed loops open --rates 0.5 1.0 1.5 2.0 --duration 90
SSL_CERT_FILE=/etc/ssl/cert.pem tools/load_test/run.sh public public --public-n 12
```

- `watch.sh` samples the box every 2 s into `results/<label>-box.tsv`, and
  stops the probe if `MemAvailable` falls under 700 MB. It never came close.
- The python.org Python on this Mac has no CA bundle, hence `SSL_CERT_FILE`
  for the public phase.
- A full run costs the live service about 15 minutes of degraded answers.
  Don't run it while people are driving.
