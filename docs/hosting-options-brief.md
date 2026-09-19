# Where the Scenic API should live, and whether it can be free

> **Answered in `docs/hosting-options-findings.md` (2026-09-01). Three figures
> below were refuted there and are left in place as the record — do not quote
> them:** Oracle Always Free A1 is now **2 OCPU / 12 GB**, not 4 OCPU / 24 GB
> (halved 15 June 2026, still ample); Hetzner's CX line is **not sold in the
> US** at all, and a US Hetzner box that fits is **~€62/mo, not ~€16** — though
> Contabo does the same job for ~€5.50, so Hetzner is simply the wrong
> yardstick.
>
> **The findings read this brief's measured requirements as sound. The
> 2026-09-16 review that rewrote the body below then moved them**, so the
> findings size on a number this file no longer states: the floor is the warm
> served process at **≈4.3 GB**, not the `Router`'s 3.53 GB. Their
> recommendation survives it — 8 GB is 53.8% utilisation, still well clear of
> Oracle's 20% reclaim criterion — but the "4.5 GB of headroom over the
> measured peak" there is really ~3.7 GB.

**Status: requirements measured 2026-08-31, nothing changed.** No source file,
no config, no deploy was touched. The task is a **recommendation and a plan**,
not a migration — the migration needs account credentials nobody but the owner
has.

The goal, in the owner's words: get the API off the laptop, **prioritising free
if it is genuinely possible**. "Free" is a real constraint here, not a
preference — treat a paid recommendation as something you have to justify
against a free option that works.

---

## Why this is being asked now

The API is self-hosted on a spare Windows laptop behind a Cloudflare tunnel at
`api.jameskouvlis.com` (`server/DEPLOY.md` Option A). It has been observed down
**twice in three days**: HTTP 530 / Cloudflare 1033 on 2026-08-29
(`docs/consumer-polish-brief.md` item 1) and again on 2026-08-31. That is the
only uptime data that exists and it is two-for-two on unannounced outages.

`DEPLOY.md` §7 already specifies the full hardening — Task Scheduler entries for
both Flask and `cloudflared` at startup with restart-on-failure, `powercfg` to
disable standby/hibernate and neutralise the lid, Windows Update active hours.
**So either that was never applied or it is not holding, and which one it is
changes the answer.** Establishing that is part of this task, not a detail.

---

## The measured requirements

All measured on this Mac on 2026-08-31, against `main` at `efbbd28`, on the
**New England** build `data/processed-ne` (998,252 edges / 794,685 nodes) which
is what is actually served:

| | measured |
|---|---|
| `Router` peak RSS, access layers loaded | **3.53 GB** cold, 3.85 GB after touching them |
| access layers actually loaded? | **yes** — 691,319 access components / 850,766 entry points |
| `Router` load time | **42.6 s** |
| `route()`, **first** call after load (Boston → Augusta ME, 262 km) | **470 ms** |
| `route()`, second call (the scenic arm, and the steady state) | **365 ms** |
| a full API request (two Dijkstras) | **~835 ms**, of which ~105 ms is one-time |
| serving payload, required three parquets | **214 MB** |
| ...plus the optional access layers | **382 MB** total |
| concurrent users | **1** — assumed, not measured |

Two rows need reading carefully. **691,319 is the number of service-way
components**, which is what `len(Router._access_entries)` counts — the dict is
keyed by component; `access_entries.parquet` itself holds **850,766 rows**. Check
the box against whichever number you actually measure, or a correct copy looks
19% short. And the **470 ms is a cold call, not a property of the fastest arm**:
`route()` runs the identical sequence for both arms (`_edge_scores`, `_weights`,
CSR, `dijkstra`) with no pref-dependent shortcut, so the pref-0 arm cannot really
cost 29% more — what the first call pays for is the `cached_property` structures
(`is_roundabout`, `maneuver_context`, `_by_tail`, `_dep_bearing`) and
first-touching the parquet-backed arrays, the same effect as "3.53 GB cold,
3.85 GB after touching them". A warm request is therefore nearer **2 × 365 =
~730 ms**; ~835 ms is the conservative figure and is used as such below.

**The single most important number, and the reason this brief exists in this
form: `docs/new-england-rollout.md` Phase 6 projects 6–6.5 GB resident, and the
`Router` measurement is 3.53 GB — the projection is 1.8x the measurement.**

**The cause is the multiplier, not the method.** The rollout doc scales
Massachusetts to New England by PBF size, and the PBF ratio is
782 MB / 310 MB = **2.53x**. It used **3.53x** — in Phase 2's resource budget,
Phase 5's latency scaling and Phase 6's RAM projection, all three now corrected
in that doc — one off in the leading digit, and a factor that matches nothing
measurable: the real ratios are 2.53x on PBF, 2.49x on edges, 2.56x on nodes,
3.00x on chunks and 3.20x on road miles. So the projected edge count (1.42 M
against a built 998,252) came in **42% high**, and everything derived from it
inherited that.

Put the right factor through the same E^1.20 latency law and it gives
281 ms × 2.49^1.20 = **840 ms** against a measured ~835 ms — accurate to within
1%, so Phase 5's ~1.27 s was a bad input, not a bad method. RAM is the one place
the linearity itself fails: it grew 1.94x against 2.49x more edges. **Fix the
multiplier rather than discarding the law** — E^1.20 is still the constant the
next region gets sized from, and on this evidence it works; PBF size is still a
good proxy for edge count, to within 1.4%.

**Size the box against the whole serving process, not against `Router`.** The
3.85 GB above is a `Router` built in isolation. `server/app.py` also holds
`LoopPlanner`'s caches (`field_cache=4, cost_cache=2`), which `looper.py`
budgets at "~160 MB" — a figure written when "the process runs around 1 GB", i.e.
Massachusetts. On New England `_Field` scales with the ~804k routing slots and
`_CostModel` with the 998,252 edges, putting those same cache counts nearer
**~400 MB**, plus 16 cached loop GeoJSONs and waitress' four threads. So a warm
process is **≈4.3 GB** and the requirement is a machine with **~6 GB usable RAM**
(8 GB for comfort), one reasonable core, ~1 GB of disk, always on, never
sleeping. A 4 GB box serves fine cold and then OOM-kills once a few `/api/loop`
requests have warmed both caches — and the restart costs 42.6 s. That is still a
much cheaper machine than the rollout doc implies, and it still puts a free tier
in play.

---

## The candidates, and what has to be established about each

### The one that could actually be free: Oracle Cloud Always Free

Ampere A1 (ARM) instances, advertised as up to 4 OCPU / 24 GB RAM, always free
with no 12-month clock. On the ≈4.3 GB warm footprint this fits with enormous
margin and is the only mainstream free tier that does. **It is the option to
investigate first and hardest.** Four things must be settled before recommending
it, and none of them should be assumed:

1. **ARM64 wheels.** The serving path needs what is in
   `server/requirements-serve.txt` — check that list specifically, not the
   pipeline's. `numpy`, `scipy`, `pandas`, `pyarrow` and `geopandas` all publish
   aarch64 wheels, but *verify* rather than assume, and note anything that would
   have to build from source on a free-tier CPU. **The two entries that actually
   carry the risk are `shapely` and `pyproj`**, also in that file and omitted
   from the list above: they bundle GEOS and PROJ, so they are the ones that fall
   back to a source build, and `server/Dockerfile` already names them as the pair
   the serving path relies on for native code. Check against
   `server/requirements-serve.lock.txt` too — a wheel exists per
   (version × Python ABI × platform), so the real question is whether
   `pyarrow==24.0.0` has a wheel for *the box's* Python on aarch64, and the lock
   file's header says why: a pyarrow or geopandas major jump is the one upgrade
   that can break reading parquets you cannot regenerate. Name the target Python
   version.
2. **A1 capacity.** Ampere A1 is widely reported as "out of capacity" in popular
   regions for extended periods. A recommendation that cannot actually be
   provisioned is not a recommendation — establish current reality and name a
   region.
3. **Idle reclaim and account termination.** Oracle's free tier has provisions
   for reclaiming idle resources. Read the actual current terms. A box that
   disappears in 30 days is worse than the laptop, because it will fail silently.
4. **Terms of service** for serving a public API off it.

### Disqualify quickly, with a reason

- **AWS / GCP / Azure free tiers** — 1 GB class instances. Fails on RAM before
  anything else, which is the whole reason. Not on the clock: AWS' 750-hour
  t3.micro and Azure's B1s are 12-month trial grants, but GCP's e2-micro is
  always-free like Oracle's, so do not disqualify it for expiring.
- **Render / Railway / Fly.io free allowances** — small, and **they sleep**.
  See trap 2: a 42.6 s cold start is disqualifying on its own, independent of
  RAM.

### Already built, and the cheapest way to answer question 1

`server/Dockerfile` and `DEPLOY.md` **Option B** are an existing deploy path, and
this brief should use it rather than re-derive one. The base image is
`python:3.11-slim`, which is multi-arch, so
`docker build --platform linux/arm64 -f server/Dockerfile .` on the same Apple
Silicon Mac these measurements came from **settles the ARM64 wheel question by
resolving every wheel for real** — evidence, no account, no credentials, entirely
inside scope, instead of the "verify rather than assume" research handed off in
question 1 and trap 3. The same image then runs on A1, on Hetzner, or on the
laptop, which is what makes the "done looks like" item 5 measurements comparable
across hosts. Note it is broken today: the `COPY` lines omit
`pipeline/looper.py` and `turn_restrictions.parquet`, so the build is also the
thing that surfaces that (see trap 7).

### The incumbent, which is also free

**Keep the laptop and make it reliable.** Zero migration risk, zero cost, and
`DEPLOY.md` §7 already specifies how. This brief does **not** presume migration
is the right answer, and a recommendation to stay put — with the §7 gap closed,
a watchdog, and external monitoring — is a legitimate outcome if the evidence
supports it. What it must not be is the *default* answer arrived at by not
investigating the alternatives.

### The paid fallback, for calibration

Hetzner has US regions (Ashburn VA, Hillsboro OR), and **the line to price for
those is `CPX`** — shared-vCPU AMD, which is what the US locations actually
carry. Get the taxonomy right before pricing anything: `CCX` is the
dedicated-vCPU line and is poor value for a single-user workload, but **`CPX` is
not dedicated**, so it must not be disqualified on that basis — a ~8 GB CPX tier
in Ashburn is the likely answer to this paragraph's own question. The
cost-optimised Intel `CX` line (CX22/CX32/CX42/CX52 — the 8 vCPU / 16 GB
instance is **CX42**; "CX43" is not a Hetzner product) has historically been
EU-only, so do not price it for the US-East recommendation trap 4 asks for
without confirming per-location availability first. **And the requirement is
~6 GB, not 16** — report the cheapest tier that clears the *warm* footprint with
headroom. Take the prices from Hetzner's own page rather than from this
paragraph: the €15.99 and the "up to 176% in June 2026" increase are unsourced
here and unverified.

---

## Traps

1. **Sizing from `new-england-rollout.md` Phase 6.** Its 6–6.5 GB rests on a
   3.53x multiplier that should have been 2.53x (see above). Using the doc's
   number inflates the recommendation into a needlessly expensive tier and may
   rule out the free option entirely — which would be the wrong answer for the
   wrong reason. **Sizing from this brief's 3.53 GB is the opposite error**: that
   is `Router` alone, and the box has to hold the warm process at ≈4.3 GB.

2. **Anything that sleeps or cold-starts is disqualified.** Load time is
   **42.6 s**. That is tolerable once at boot and unacceptable mid-drive: a
   reroute that takes 43 seconds has already failed. This also rules out
   serverless (Lambda, Cloud Run) regardless of price — the working set is
   ~3.5 GB cold and ≈4.3 GB warm, and the load cost is paid per cold container.

3. **Assuming ARM "just works".** It probably does, but the free recommendation
   rests on it, so check the wheels rather than asserting them — and check them by
   building, not by reading: `docker build --platform linux/arm64` against the
   existing `server/Dockerfile` resolves them for real on the Mac.

4. **Region.** Route *planning* at ~835 ms absorbs 100 ms of extra RTT without
   anyone noticing; a **mid-drive reroute** is the case that does not. Prefer
   US-East. If you recommend a non-US region, state what it costs in latency
   rather than leaving it implicit.

5. **Code and parquets must come from the same commit.** `router.py` re-blends
   scores live using `score.py`'s `WEIGHTS`, so old code meeting new parquets
   returns subtly wrong routes *with no error at all*.
   `test_neutral_weights_reproduce_the_precomputed_score` is the tripwire.
   **Run that test on the box, not the whole suite** —
   `pytest tests/test_routing.py -k neutral_weights`. A full session loads the
   graph **twice**: `tests/conftest.py` has a session-scoped `router` fixture,
   and `tests/test_api.py` separately imports `app`, which builds its own
   `Router` at module scope. That peaks near **7.7 GB** — roughly double the
   serving footprint — so the verification step OOMs on a box that would have
   served perfectly well, and the operator cannot tell that from a bad copy. A
   full run also degrades quietly on a serve-only payload: `scored_chunks.parquet`
   is not in the copy manifest, so those tests skip and the green result will not
   match the "294 passed, 0 skipped" the other docs record. `DEPLOY.md` records a
   real instance of the mismatch this guards against costing time on 2026-08-29.

6. **382 MB over a home upload link.** Stage it as a resumable transfer, not one
   long copy. `DEPLOY.md` already flags an 80 MB copy as worth noting; this is
   nearly five times that.

7. **Do not propose building the graph on the server.** The pipeline needs the
   OSM PBF, elevation tiles and rasterio; the serving box needs the three
   parquets, `requirements-serve.txt`, **and the code** — `server/app.py` +
   `serve.py`, and `pipeline/router.py` + `common.py` + `score.py` +
   `looper.py`. That split is deliberate, but take the manifest from `DEPLOY.md`
   "What ships" rather than from this line: `app.py` imports `looper`, and
   DEPLOY.md warns that the ships-list "has been wrong before" for exactly that
   module, a missing one being an `ImportError` at startup that the tunnel
   reports as a **502** — indistinguishable from a bad data copy, and it has
   already cost a debugging session once.

8. **Free tiers that require a credit card can still bill you.** If a
   recommendation has any path to a surprise charge, say so plainly and say how
   to cap it.

9. **Losing the tunnel loses the rate limit.** The only limiter is a Cloudflare
   WAF rule (`DEPLOY.md` §6, 60 req/min by IP) — there is none in the code, and
   the API has no auth and permissive CORS. `server/serve.py` also defaults
   `SCENIC_HOST` to `0.0.0.0`, which is harmless behind a home NAT where
   `cloudflared` reaches it over loopback and fatal on a box with a public IP. At
   the measured ~835 ms per request the real ceiling is **~1.2 req/s**, not the
   5 req/s §6 quotes at the old 190 ms, so one scripted loop is a denial of
   service — and sustained CPU on a free tier is exactly what the idle-reclaim
   and termination terms in question 3 bite on. Any recommendation that drops the
   tunnel has to say what replaces the WAF rule, set `SCENIC_HOST=127.0.0.1`, and
   close every port but the reverse proxy's.

---

## Done looks like

1. **A recommendation**: named provider, plan, region, and monthly cost —
   including **$0** if that is genuinely achievable and survives the four Oracle
   questions above.
2. **Evidence for the free option**, specifically: the ARM64 wheel question
   answered against `server/requirements-serve.lock.txt` — the pinned versions
   that actually get installed, not the unpinned `requirements-serve.txt` — for a
   named target Python version, `shapely` and `pyproj` included; and a statement
   on capacity and idle-reclaim taken from the provider's current terms rather
   than from memory or a blog post.
3. **A verdict on the incumbent** — does hardening the laptop beat migrating?
   Answer it on evidence, including whether `DEPLOY.md` §7 was ever applied.
   "Stay on the laptop" is an acceptable conclusion; "we didn't look" is not.
4. **A migration plan**: what to copy, in what order, how to verify it works,
   and how to roll back. **Rollback here is host-level, and it is not an
   environment variable**: the hostname is fixed, so backing out of a new host
   means re-pointing the Cloudflare tunnel / DNS record at the laptop, which
   stays ready to serve. (`SCENIC_DATA` is the lever for rolling back *data* on
   one box — the claim in `new-england-rollout.md` Phase 6, a different
   operation — and even there it is two variables, because `server/app.py` reads
   `SCENIC_REGION` alongside it: parquets rolled back to Massachusetts without it
   leave the error messages and the index response telling a driver in Worcester
   that the covered region is New England.) The plan must also name what replaces
   the Cloudflare rate limit, and set `SCENIC_HOST=127.0.0.1` plus a firewall
   rule on any box with a public IP — see trap 9.
5. **A measurement plan for the box**: peak RSS **measured after exercising
   `/api/loop` from two different starts**, not after constructing a `Router` —
   that is the 3.85 GB figure and it misses ~400 MB of loop caches; load time;
   and one real route timed *after* a discarded warm-up call, since the 470 ms
   above is a cold one. Compare against the table in this brief. The 3.53 GB
   figure is from an Apple Silicon Mac and will not transfer exactly to ARM Linux
   or x86 — expect it to move and say by how much.
6. **Uptime**: what monitors it, and what restarts it when it dies. The current
   answer is "the owner finds out when someone curls it", and that has to change
   whatever host wins.
7. **Or a statement of why this brief is wrong**, quoting what proves it. A
   refuted assumption is a good outcome; a silently skipped question is not.

---

## Out of scope

- **Performing the migration.** It needs accounts and credentials. Produce the
  plan; the owner executes it.
- **Buying anything**, or signing up for anything that requires payment details.
- **Router performance work.** Phase 5 of the rollout doc already measured the
  candidate optimisations (`limit=`, A*, degree-2 contraction) at ~1.2x each and
  recommended deferring. Do not reopen it; ~835 ms is not the problem here.
- **The domain and tunnel.** `api.jameskouvlis.com` through Cloudflare works and
  is free. A new host may not need the tunnel at all — but **dropping it is not
  free**, because it carries the only rate limit there is (trap 9), so that cost
  is in scope even though the tunnel is not. Keeping the same hostname is a
  requirement: it is baked into the app bundle at `ios/project.yml`
  (`ScenicAPIBaseURL`), so changing it means shipping a new build through App
  Review. That does **not** mean a candidate host can only be checked with curl.
  `ios/Sources/RouteService.swift` takes `SCENIC_API` from the environment ahead
  of the baked value, so an Xcode-launched build with
  `SCENIC_API=https://<new-box>` drives real `/api/route` and `/api/loop` traffic
  against the candidate through the actual client — which is how items 4 and 5
  get verified — while production traffic stays on the laptop and rollback is
  closing a scheme rather than changing DNS.
