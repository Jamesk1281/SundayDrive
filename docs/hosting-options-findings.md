# Where the Scenic API should live — findings

Answers `docs/hosting-options-brief.md`. Researched 2026-08-31/09-01 against
`main` at `efbbd28`. **Nothing was migrated, provisioned, purchased or signed
up for**, per the brief's scope. No source file was changed except
`server/DEPLOY.md`, where §7 is wrong in a way that matters (see below).

The brief's measured requirements were taken as given and not re-derived. Where
they were cheap to check they held: `graph_nodes.parquet` is 794,685 rows and
`graph_edges.parquet` is 998,252, exactly as stated, and the five serving files
are 364 MiB = **382 MB**, also as stated.

---

## Recommendation, in one paragraph

**Do not pay for anything, and do not migrate this week.** Do two things in
order. **First, tonight: fix process supervision on the laptop and put a free
external monitor on `/api/health`.** That is free, takes about an hour, carries
no migration risk, and addresses the actual cause of the outages — which is not
RAM, not CPU, and not the hardware. **Then, without time pressure: acquire an
Oracle Cloud Always Free Ampere A1 instance** (2 OCPU / 8 GB, home region
`us-ashburn-1`, fallback `us-chicago-1`), migrate onto it, and keep the laptop
as the documented rollback. Oracle is genuinely free, genuinely always-on, and
fits the measured 3.53 GB with large margin — but acquiring an A1 instance
involves an **irreversible region choice made before you know whether capacity
exists**, so it must not be attempted under pressure from a downed API.

The single most important finding is the ordering, and the reason for it is in
[The outage is a supervision defect](#the-outage-is-a-supervision-defect-not-a-hosting-one):
**migrating without fixing supervision reproduces the outage on the new box.**

---

## Three things in the brief are wrong

The brief invited this ("a refuted assumption is a good outcome"). All three
corrections came from provider primary sources, not blogs.

### 1. Oracle Always Free A1 is 2 OCPU / 12 GB, not 4 OCPU / 24 GB

Oracle halved it, effective **15 June 2026**. Oracle's own documentation now
reads:

> the first 1,500 OCPU hours and 9,000 GB hours per month for free for VM
> instances using the VM.Standard.A1.Flex shape, which has an Arm processor.
> For Always Free tenancies, this is equivalent to 2 OCPUs and 12 GB of memory.

— [Always Free Resources, docs.oracle.com](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)

**This does not change the recommendation.** 12 GB against a measured 3.53 GB is
still 3.4x headroom. It changes one number in the plan and, as it turns out,
*improves* the reclaim picture — see
[idle reclaim](#3-idle-reclaim-the-halving-accidentally-protects-scenic).

### 2. Hetzner's CX line is not available in the US

The brief says "Hetzner's cost-optimised CX line, US regions available (Ashburn
VA, Hillsboro OR)" and prices CX43 at €15.99/mo. Hetzner's own cost-optimized
page lists CX23/CX33/CX43/CX53 as available in **`eu-central FSN NBG HEL`** —
Falkenstein, Nuremberg, Helsinki. Not Ashburn, not Hillsboro. The US locations
get the older CPX*1* generation (CPX11/21/31/41/51); the newer CPX*2* generation
is EU and Singapore only.

This matters a great deal, because of the third correction.

### 3. US paid hosting is now roughly ten times the brief's figure

Hetzner's **15 June 2026** price adjustment raised CPX and CCX by 2.1x–3x, and
it applied to the US locations. The plan that actually clears the measured
footprint in Ashburn is **CPX31 (4 vCPU / 8 GB)**, and its US price went from
**€20.99 to €62.49/mo**. The brief's mental model of "the paid fallback is about
€16" is out of date by about 4x for a US box and about 10x against the €6.49
EU CX33 it was implicitly imagining.

Hetzner's own price-adjustment notice confirms the pattern and that the USA
(ASH/HIL) locations were included; the specific CPX31-US figure is from
secondary reporting and **should be confirmed in the Hetzner console before
anyone spends money**. Directionally it is not in doubt — the same notice shows
CCX13 €15.99 → €42.99 and CPX52 €36.49 → €100.49.

**Consequence: "just pay for a small VPS in the US" is no longer a $5–16/mo
answer. It is a ~$68/mo answer.** That strengthens the case for both free
options and is the main reason the recommendation does not hedge toward paying.

### And a fourth correction, to the premise

The brief says the API has been down "twice in three days". **It is three
times.** It was down while this was being researched — continuously, for the
entire session:

```
utc,http_code,time_total_s
2026-09-01T02:55:13Z,530,0.085382
2026-09-01T03:02:07Z,530,0.046588
2026-09-01T03:05:08Z,530,0.042640
...
```

HTTP 530 / Cloudflare 1033, which `DEPLOY.md`'s own decoder table defines as
**"DNS points at the tunnel, no `cloudflared` connected"**. Not a 502 (app dead,
tunnel alive). Not a DNS failure. The tunnel process is gone, or the box is.

---

## The outage is a supervision defect, not a hosting one

This is the part that changes what to do first.

### What the evidence says

Three observed outages, and the one I could observe directly presented as
**530/1033 with a fast TCP connect** (~45 ms — Cloudflare's edge answers
immediately and reports no origin). So Cloudflare is healthy, DNS is healthy,
and nothing is connected from the laptop side.

### Was `DEPLOY.md` §7 ever applied?

**I cannot prove it either way from this Mac** — the laptop is a separate
Windows machine and nothing in the repo records its runtime state. But there is
strong circumstantial evidence, and one hard finding that makes the question
partly moot.

The hard finding: **§7 as written cannot deliver restart-on-failure, even if it
was applied exactly as specified.** §7 says to point Task Scheduler at the
Python and `cloudflared` executables directly, but the repo also ships
`server/start-windows.bat`, whose own header says:

> Double-click this, or point a Task Scheduler task at it to run at startup.
> Two console windows open and must stay open — closing one stops that half.

and whose body is:

```bat
start "Scenic API" "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\server\serve.py"
start "Scenic Tunnel" cloudflared.exe tunnel run scenic
```

`start` launches each child **detached** and returns immediately. The batch file
then echoes three lines and exits **0**. So a Task Scheduler task pointed at this
script — which the script itself invites — reports success within milliseconds
and has no further relationship with either process. "Restart on failure" never
fires, because from Task Scheduler's point of view nothing ever failed. The task
gives you start-at-boot and nothing else.

That is *exactly* consistent with the observed symptom: an API that comes back
after a reboot but stays down for hours once `cloudflared` dies on its own.

The circumstantial evidence that the interactive path is the one in use: the
script is written to be double-clicked, it opens titled console windows, it
prints "Started two windows" and a `curl` line for a human to run, and §7's
alternative (`Run whether user is logged on or not`) is incompatible with that
design — in a non-interactive session those windows have no desktop to appear
on.

**Verdict on the incumbent: the hardening was specified but the specification is
defective, so "was it applied?" is the second question, not the first.** Fix the
supervision model and the answer to the original question stops mattering.

I have corrected §7 in `server/DEPLOY.md` as part of this work.

### What the owner should check on the laptop, to confirm

Five commands, in an **Administrator** PowerShell on the laptop. This is the
missing evidence; it takes two minutes:

```powershell
schtasks /query /tn "*Scenic*" /v /fo LIST
```

```powershell
powercfg /q SCHEME_CURRENT SUB_SLEEP
```

```powershell
powercfg /lastwake
```

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; Id=41,1074,6008} -MaxEvents 20 | Format-Table TimeCreated,Id,Message -AutoSize
```

```powershell
Get-Process python,cloudflared -ErrorAction SilentlyContinue | Format-Table Name,Id,StartTime,WS -AutoSize
```

In order: whether the tasks exist at all and how they are configured; whether
standby is actually disabled; what last woke the box; unexpected shutdowns and
Windows-Update-initiated reboots (event 1074 names the initiator); and whether
both processes are alive right now and since when. If `StartTime` on those two
processes is recent and the box has not rebooted, something is killing and not
restarting them. If event 1074 shows Windows Update reboots, active hours were
never set.

---

## Oracle Cloud Always Free — the four questions

### 1. ARM64 wheels: settled, and the answer is clean

Checked against **`server/requirements-serve.lock.txt`** (the pinned set, which
is what a reproducible box should install) by querying the PyPI JSON API for each
pinned version and inspecting the actual wheel filenames. Not from memory.

| package | version | kind | aarch64 manylinux wheel | builds from source? |
|---|---|---|---|---|
| geopandas | 1.1.3 | pure Python | n/a (`py3-none-any`) | no |
| pandas | 2.3.3 | compiled | cp39–cp314 | **no** |
| shapely | 2.1.2 | compiled | cp310–cp314 | **no** |
| pyarrow | 24.0.0 | compiled | cp310–cp314 | **no** |
| numpy | 2.2.6 | compiled | cp310–cp313 | **no** |
| scipy | 1.15.3 | compiled | cp310–cp313 | **no** |
| pyproj | 3.7.1 | compiled | cp310–cp313 | **no** |
| Flask | 3.1.3 | pure Python | n/a | no |
| flask-cors | 6.0.5 | pure Python | n/a | no |
| Flask-Compress | 1.24 | pure Python | n/a | no |
| waitress | 3.0.2 | pure Python | n/a | no |

**Nothing in the serving path compiles on the box.** Every compiled dependency
ships a prebuilt `manylinux` aarch64 wheel; the rest are architecture
independent. The free-tier CPU never has to build numpy or scipy, which was the
brief's specific worry.

Two constraints fall out of the table, and both are real deployment traps:

- **Python must be 3.10, 3.11, 3.12 or 3.13.** The intersection of cp-tags
  across all six compiled packages is cp310–cp313. numpy 2.2.6, scipy 1.15.3
  and pyproj 3.7.1 publish **no cp314 wheel**, so a box with Python 3.14 falls
  back to source builds for exactly the three heaviest packages. Equally,
  **Python 3.9 does not work** — shapely 2.1.2 and numpy 2.2.6 have no cp39
  wheel. This matters because **Oracle Linux 9's default `python3` is 3.9**. Use
  Ubuntu 22.04/24.04 (Python 3.10/3.12) or explicitly install `python3.12` on
  Oracle Linux.
- **glibc ≥ 2.28**, set by pyarrow 24.0.0's `manylinux_2_28_aarch64`. Oracle
  Linux 8 (2.28), Oracle Linux 9 (2.34), Ubuntu 22.04 (2.35) and 24.04 (2.39)
  all clear it. A musl distro (Alpine) would not — the aarch64 musllinux
  coverage is not complete across this set. Don't use Alpine.

`cloudflared` also ships a `linux-arm64` binary and `.deb`, confirmed against
the current GitHub release assets, so the tunnel survives the architecture
change if you keep it.

### 2. A1 capacity: obtainable, but the region choice is an irreversible bet

This is the real risk in the Oracle option, and it is larger than the brief
anticipated. It is a chain of three facts, each individually documented:

1. **Always Free compute can only be created in your tenancy's home region.**
2. **The home region is chosen at signup and cannot be changed afterwards.**
3. **`Out of host capacity` on A1 is common and concentrated in exactly the
   popular US regions** — Oracle's own docs acknowledge the condition and offer
   only "try a different availability domain, or wait a while, then try again"
   ([Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)).
   `us-ashburn-1` is repeatedly named in secondary reporting as among the worst.

So you must commit permanently to a region **before** you can find out whether
you will ever get an instance in it, and the region the latency budget wants is
the one most likely to refuse you. If it refuses you indefinitely, the remedy is
a new tenancy under a different email — not a setting.

**Mitigation, and this is why the latency measurement matters.** Measured TCP
connect RTT from this Mac (Boston) to OCI regional endpoints, 5 samples each:

| region | median RTT | vs Ashburn |
|---|---|---|
| `us-ashburn-1` | **23 ms** | — |
| `us-chicago-1` | **35 ms** | +12 ms |
| `us-phoenix-1` | 76 ms | +53 ms |
| `us-sanjose-1` | 76 ms | +53 ms |
| `eu-frankfurt-1` | 104 ms | +81 ms |
| `ap-singapore-1` | 242 ms | +219 ms |

**`us-chicago-1` is the answer to the capacity/latency conflict.** It costs
+12 ms over Ashburn — irrelevant against an ~835 ms request, and roughly a
1.4% increase in a warm reroute — while being a much less contended region than
Ashburn for free-tier A1. If you want to reduce the chance of being permanently
stuck, **choose `us-chicago-1` as the home region.**

The commonly recommended regions (Frankfurt, Singapore) are the ones with
capacity precisely because they are far away. Frankfurt costs +81 ms per round
trip, which is **+243 ms on a cold connection** (TCP + TLS 1.3 + request ≈ 3
RTTs) — about a 30% increase in mid-drive reroute latency. That is the case the
brief's trap 4 says not to leave implicit. Singapore is disqualifying on its own.

**What I could not establish:** whether A1 capacity is available in
`us-ashburn-1` or `us-chicago-1` *at this moment*. Oracle publishes no
unauthenticated capacity API, and checking requires an account, which is out of
scope. Treat acquisition as a task with an unbounded tail — possibly minutes,
possibly repeated attempts over days. **This is the whole reason the laptop must
be hardened first.**

### 3. Idle reclaim: the halving accidentally protects Scenic

The policy is real, and Scenic would have tripped it under the *old* free tier.
Oracle's exact wording:

> Oracle will deem virtual machine and bare metal compute instances as idle if,
> during a 7-day period, the following are true:
> - CPU utilization for the 95th percentile is less than 20%
> - Network utilization is less than 20%
> - Memory utilization is less than 20% *(applies to A1 shapes only)*

All three must hold. A single-user routing API is unambiguously idle on CPU and
network — it does nothing at all between requests. **Memory is the only
criterion Scenic can fail, and therefore the only thing standing between the box
and reclamation.** Running the numbers on the measured 3.53 GB:

| instance memory | Scenic memory utilization | idle? |
|---|---|---|
| 24 GB (old free tier) | 14.7% | **yes — would be reclaimed** |
| 12 GB (current max) | 29.4% | no — safe |
| **8 GB (recommended)** | **44.1%** | **no — safe, with margin** |
| 6 GB | 58.8% | no — safe |

Under the old 4 OCPU / 24 GB allowance, Scenic would have sat below all three
thresholds and been a reclamation candidate. The June 2026 halving removes that
risk for free.

**This is why the recommendation is 8 GB and not the full 12 GB.** More RAM is
actively worse here. The brief notes the 3.53 GB figure is from an Apple Silicon
Mac and will move on ARM Linux; at 12 GB, a working set that came in below
2.4 GB would drop under the threshold and re-arm the reclaim risk, whereas at
8 GB it would have to fall below 1.6 GB. 8 GB still leaves 4.5 GB of headroom
over the measured peak, which is comfortably inside the brief's "6–8 GB for
comfort" target.

Two caveats I could not close:

- **Oracle's docs do not state what reclamation actually does** — whether the
  instance is stopped (restartable, volumes intact) or deleted. Secondary
  sources consistently say "stopped, volumes preserved, restartable if the shape
  is available", but I could not confirm that from Oracle. It does not change the
  plan: for an always-on API, "stopped" is a total outage anyway, and the
  external monitor is what catches it.
- **Memory utilization is reported by the Oracle Cloud Agent's monitoring
  plugin.** If that plugin is disabled, it is unclear whether the memory
  criterion is evaluated as "not met" or simply skipped — and skipped would mean
  CPU and network alone decide, which Scenic fails. **Leave the monitoring plugin
  enabled** and confirm `MemoryUtilization` is actually appearing in OCI
  Monitoring after setup. This is a genuine unknown, cheap to verify once the box
  exists, and expensive to get wrong.

### 4. Terms of service: serving a public API is permitted

Oracle's Acceptable Use Policy prohibits vulnerability/penetration testing of
the services without approval, network discovery and port scanning, password
cracking, and cryptocurrency mining. **Nothing in it restricts hosting a
publicly reachable web service or API**, and nothing restricts production use.
Always Free is explicitly positioned for exactly this kind of workload.

Two real constraints, neither a prohibition:

- **No SLA.** Always Free carries no uptime commitment. This is fine — the
  laptop has no SLA either, and the honest comparison is "a datacentre with no
  SLA" against "a laptop in a flat with no SLA".
- **Non-compliance can mean suspension or termination of the account.** Standard,
  and not triggered by anything Scenic does.

I read Oracle's AUP and Cloud Services Agreement via search summaries of the
primary PDFs; `oracle.com` itself returns HTTP 403 to automated fetches, while
`docs.oracle.com` serves normally — which is why the technical policies above
are quoted directly and the legal ones are characterised rather than quoted.
**Anyone relying on the ToS conclusion should read
[the CSA PDF](https://www.oracle.com/contracts/docs/cloud_csa_online_v062223_us_eng.pdf)
in a browser.**

### The landmine the brief did not anticipate

From Oracle's Free Tier overview, and this is the one that could silently destroy
the deployment:

> If you have more OCI Ampere A1 Compute instances provisioned than are
> available for an Always Free tenancy, all existing OCI Ampere A1 Compute
> instances are **disabled and then deleted after 30 days**, unless you upgrade
> to a paid account.

— [Oracle Cloud Infrastructure Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)

Read that against correction 1. During the 30-day trial you have $300 of credits
and can provision A1 shapes larger than the Always Free allowance. When the trial
ends, or if the allowance is reduced again as it was in June 2026, an
over-allowance A1 footprint is **disabled and deleted, not merely billed**.

**Operational rule: never let total provisioned A1 exceed 2 OCPU. Ever.** Do not
provision a bigger shape "because the trial allows it" and plan to shrink later.

The good news, from the same documentation:

> After your trial ends, your account remains active. There is no interruption to
> the availability of the Always Free Resources you have provisioned.

and

> a set of Always Free offers that **never expire**

So there is no 12-month clock, and no inactivity-based account deletion is
documented anywhere I could find.

### Can it surprise you with a bill? (brief trap 8)

A credit card is required at signup for identity verification. Oracle's
documentation states:

> Your credit card will not be charged unless you upgrade your account.

Always Free resources stay free even after a voluntary upgrade to Pay As You Go.
The exposure is therefore: **you cannot be billed unless you actively click
upgrade.** How to cap it: stay on the Always Free account type, and if you ever
do upgrade (the only documented way to escape idle reclaim, incidentally), set a
**budget alert at $1** in OCI Cost Management immediately.

---

## Disqualified, with reasons

| option | why not |
|---|---|
| **AWS / GCP / Azure free tiers** | 1 GB instance class (t3.micro, e2-micro, B1s) — fails on RAM against 3.53 GB before anything else. AWS and Azure are 12-month only. |
| **Render free** | Free web services **spin down after 15 minutes of inactivity** (reduced from 30 in Sept 2025) and take ~1 minute to spin up. Brief trap 2 disqualifies this outright — and a single-user API is idle nearly all the time, so it would be cold for essentially every drive. |
| **Fly.io free** | No true permanent free tier any more; legacy allowances honoured only for accounts created before 7 Oct 2024. Current model auto-stops machines on low traffic. Sleeps, and the old allowance was 256 MB anyway. |
| **Railway free** | Free tier removed July 2023. Current free plan is **$1/month of credit, 0.5 GB RAM**. Fails on RAM by 7x. |
| **Lambda / Cloud Run / any serverless** | 42.6 s load time paid per cold container against a ~3.5 GB working set. Brief trap 2. Not a pricing question. |
| **Hetzner US (CPX31, 4 vCPU / 8 GB)** | Works technically. **~€62.49/mo** after the June 2026 increase. Not disqualified — just poor value against two free options that work. |
| **Hetzner EU (CX33, 4 vCPU / 8 GB)** | ~€6.49/mo and technically fine, but **+81 ms RTT** (+243 ms cold). Only worth it if Oracle capacity proves unobtainable *and* the laptop is unacceptable. |

---

## Cost comparison

| option | monthly | RAM | always-on | migration risk | notes |
|---|---|---|---|---|---|
| **Laptop, hardened** | **$0** | 8 GB (assumed) | yes, once §7 is fixed properly | **none** | Home ISP and power are the residual risk |
| **Oracle A1 Always Free** | **$0** | 8 GB provisioned / 12 GB max | yes | low (rollback = one env var) | Acquisition risk; irreversible region choice |
| Hetzner EU CX33 | ~€6.49 | 8 GB | yes | low | +81 ms RTT |
| Hetzner US CPX31 | ~€62.49 | 8 GB | yes | low | 3x price increase June 2026 |

---

## The plan

### Phase 0 — tonight, on the laptop (free, ~1 hour, no migration risk)

This is required whatever host wins, because it is also the rollback target.

1. **Stop using `start-windows.bat` as a Task Scheduler target.** Create **two
   separate tasks**, each pointing at an executable directly — never at a batch
   file that spawns and exits:
   - `…\.venv\Scripts\python.exe` with argument `…\server\serve.py`
   - `cloudflared.exe` with arguments `tunnel run scenic`

   Each: trigger *At startup*, *Run whether user is logged on or not*, and on the
   **Settings** tab, *If the task fails, restart every 1 minute*, up to 3 times,
   with *If the running task does not end when requested, force it to stop*. The
   critical detail is that the task's action must be the **long-lived process
   itself**, so that when it dies the task is seen to fail.
   `start-windows.bat` stays useful for manual double-click starts.
2. Set `SCENIC_HOST=127.0.0.1` for the API task (System environment variable, or
   a one-line wrapper that is `cmd /c set ... && python.exe …` — not `start`).
3. Apply the `powercfg` lines in §7 if they were never applied, and **verify**
   with `powercfg /q SCHEME_CURRENT SUB_SLEEP` rather than assuming.
4. Set Windows Update **active hours**.
5. **Reboot and touch nothing.** Confirm `https://api.jameskouvlis.com/api/health`
   answers on its own. §7 already says this is the only real test; it is, and it
   is worth doing twice.
6. **External monitoring** (see below). This is the item that has been missing
   entirely, and it is the difference between "down for six hours" and "down for
   five minutes".

### Phase 1 — acquire the Oracle box (no deadline, no pressure)

1. Sign up for Oracle Cloud Free Tier. **Choose `us-chicago-1` as the home
   region** (or `us-ashburn-1` if you are willing to trade capacity odds for
   12 ms). This choice is permanent — it is the single most consequential click
   in the whole plan.
2. Create **one** `VM.Standard.A1.Flex` instance: **2 OCPU, 8 GB**, Ubuntu 24.04
   (Python 3.12), 50 GB boot volume. Not 12 GB — see the reclaim table. Not more
   than 2 OCPU total, ever — see the landmine.
3. If `Out of host capacity`: try each availability domain, then retry over
   following days. Oracle's documented remedy is exactly this. The laptop is
   serving throughout, which is the entire point of the ordering.
4. Open nothing inbound. The Cloudflare tunnel dials out, so the instance needs
   **no ingress rule at all** — leave the default security list closed. This is
   strictly better than the laptop's position and removes the firewall question.

Note on the OCPU budget: 1,500 OCPU-hours/month against 2 OCPU running
continuously is 1,488 hours in a 31-day month. It fits, with about 6 hours of
slack. **You cannot run two 2-OCPU instances side by side for a parallel-run
window.** If you want an overlap, make each instance 1 OCPU, or accept a short
cutover.

### Phase 2 — migrate

What ships is already specified in `DEPLOY.md`, and it is worth re-reading rather
than re-deriving. In order:

1. **Code first, via `git clone`, not by hand.** `DEPLOY.md` records that the
   hand-copied file list has been wrong before and that a missing module is an
   `ImportError` presenting as a 502.
2. **Confirm the commits match.** `git log --oneline -1` on both ends. `DEPLOY.md`
   records a real 2026-08-29 incident where local merges were never pushed, so
   the serving box pulled old code, met new parquets, and died with
   `KeyError: 'c_green'`.
3. **Then the data — 382 MB, staged and resumable.** Brief trap 6. Five files
   from `data/processed-ne/`:

   | file | size | required? |
   |---|---|---|
   | `graph_edges.parquet` | 187.9 MiB | yes |
   | `graph_nodes.parquet` | 16.2 MiB | yes |
   | `turn_restrictions.parquet` | 0.2 MiB | yes — server refuses to start without it |
   | `access_ways.parquet` | 129.7 MiB | optional |
   | `access_entries.parquet` | 30.4 MiB | optional |

   Use `rsync --partial --progress --append-verify` over SSH, or `scp` per file
   with the two large ones split out. Do not start one 382 MB copy over a home
   upload link and hope.
4. **Install from the lock file**, not the loose requirements:
   `python3.12 -m pip install -r server/requirements-serve.lock.txt`. On ARM this
   is the difference between downloading eleven wheels and compiling scipy.
5. **Run the test suite on the box** — `DEPLOY.md` §3. **Count the skips, not the
   passes**: 4 skips means the access layer loaded, 8 means it did not. This is
   also the tripwire for brief trap 5:
   `test_neutral_weights_reproduce_the_precomputed_score` is what catches code
   and parquets from different commits, which otherwise returns subtly wrong
   routes with no error at all.
6. **Do not build the graph on the server** (brief trap 7). The pipeline needs
   the PBF, elevation tiles and rasterio; the serving box needs parquets and
   `requirements-serve.lock.txt`.
7. **systemd, not a batch file.** Two units, `scenic-api.service` and
   `cloudflared.service`, each with `Restart=always`, `RestartSec=5`, and
   `After=network-online.target`. This is the thing the Windows box cannot do
   cleanly, and it is a real reason to prefer the migration once it is safe.
   Note `TimeoutStartSec` must exceed the **42.6 s** load time — set it to 180.
   Do **not** use `Type=notify`; the app does not notify readiness.
8. **Cut over.** The tunnel is the switch: run `cloudflared tunnel run scenic` on
   the new box and stop it on the laptop. The hostname `api.jameskouvlis.com`
   does not change, which is mandatory — it is baked into the app bundle at
   `ios/project.yml` (`ScenicAPIBaseURL`) and changing it means App Review.
   Only one `cloudflared` should run the named tunnel at a time; two connectors
   will load-balance and you will get intermittent results from whichever box is
   less ready.

### Rollback

**Start `cloudflared` on the laptop again and stop it on the Oracle box.** That
is the whole procedure, and it is why the deploy risk is low. Keep the laptop
fully working for at least two weeks after cutover — it costs nothing.

Separately, `SCENIC_DATA` (`server/app.py:84`) selects the data directory, so
rolling back a *data* change on either box is one environment variable and a
restart, with `data/processed` and `data/processed-ne` side by side.

### Measurement plan for the new box

Compare against the brief's table. The brief is right that 3.53 GB will move —
`DEPLOY.md` already notes macOS compresses much of the footprint out of plain
RSS, so **expect ARM Linux to report the same or somewhat more**, not less. My
estimate is 3.5–4.2 GB; anything above 5 GB or below 2.5 GB deserves
investigation, and below 2.4 GB would re-open the reclaim question.

| measure | how | expected | brief's figure |
|---|---|---|---|
| peak RSS | `systemd-cgtop` / `ps -o rss= -p $(pidof python3.12)` after first route | 3.5–4.2 GB | 3.53 GB |
| load time | time from service start to first `/api/health` 200 | 40–70 s (A1 core is slower than an M-series) | 42.6 s |
| one real route | Boston → Augusta ME, 262 km, timed server-side | 0.5–1.2 s | 835 ms |
| test suite | `pytest tests/` | 207 passed, **4 skipped** | — |
| memory utilization | OCI Monitoring, `MemoryUtilization` | **must be > 20%** | — |

That last row is not a performance check — it is the reclaim check, and it is the
one that has no equivalent on the laptop. Confirm it is being reported at all.

### Uptime: what watches it, and what restarts it

Today the answer is "the owner finds out when someone curls it", which is how
three outages became three outages. Whatever host wins:

- **Restart** is the local supervisor: fixed Task Scheduler tasks on Windows,
  `Restart=always` on systemd. Both must supervise the *actual long-lived
  process*.
- **Alerting** is a free external monitor. **UptimeRobot's free plan** (50
  monitors, 5-minute interval, email alerts) is sufficient and includes
  **keyword monitoring**, which matters here: point it at
  `https://api.jameskouvlis.com/api/health` and assert the body contains
  **`794685`** — the New England node count, confirmed from
  `graph_nodes.parquet`. A plain 200-check proves the process is listening; the
  keyword check additionally proves it loaded the *right graph*, which is the
  silent-disagreement failure `DEPLOY.md` warns about repeatedly. **Better Stack's
  free tier** (10 monitors, 3-minute interval, one phone-call alert) is worth
  considering instead if you want to be woken up rather than emailed.
- **Note the health endpoint returns live values**, not constants:
  `jsonify(status="ok", nodes=len(ROUTER.nodes), routing_slots=ROUTER.n)`
  (`server/app.py:384`). So the keyword assertion has to be updated whenever the
  served region changes — a Massachusetts build answers `310807`. That is a
  feature: a stale assertion fails loudly instead of a stale graph serving
  quietly.

---

## What I could not establish

Stated plainly, because a silently skipped question is the failure mode the brief
named:

1. **Whether A1 capacity is available in `us-chicago-1` or `us-ashburn-1` right
   now.** Requires an account. Out of scope. This is the recommendation's main
   open risk and the reason for the phased ordering.
2. **Whether `DEPLOY.md` §7 was ever applied to the laptop.** Requires access to
   the Windows box. The five diagnostic commands above close it in two minutes.
   The finding that §7 is *defective as specified* partly moots the question.
3. **What Oracle actually does to a reclaimed instance** (stop vs delete). Not
   stated in Oracle's documentation; secondary sources say "stopped, volumes
   preserved".
4. **Whether the memory-utilization criterion is skipped when the Oracle Cloud
   Agent monitoring plugin is disabled.** Verify on the box once it exists.
5. **The exact current Hetzner CPX31-US price.** €62.49 is secondary reporting;
   the ~3x direction is confirmed by Hetzner's own price-adjustment notice.
   Irrelevant unless the free options both fail.

---

## Sources

Provider primary sources:

- [Always Free Resources — docs.oracle.com](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) — 2 OCPU/12 GB allowance, idle criteria, out-of-host-capacity guidance
- [Oracle Cloud Infrastructure Free Tier — docs.oracle.com](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm) — never expires, trial-end behaviour, the A1 over-allowance deletion rule
- [Oracle Cloud Services Agreement (PDF)](https://www.oracle.com/contracts/docs/cloud_csa_online_v062223_us_eng.pdf) — AUP
- [Hetzner price adjustment, 15 June 2026](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/) — affected families and regions
- [Hetzner cost-optimized (CX) plans](https://www.hetzner.com/cloud/cost-optimized/) — `eu-central FSN NBG HEL` only
- [Hetzner regular performance (CPX) plans](https://www.hetzner.com/cloud/regular-performance/) — CPX*1* generation in ASH1/HIL1
- PyPI JSON API, per pinned version — wheel filenames for the ARM64 table
- GitHub releases API, `cloudflare/cloudflared` — `linux-arm64` assets

Secondary reporting, used only where marked:

- [Oracle quietly halves free tier A1 limits — InfoQ](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) and [Linuxiac](https://linuxiac.com/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/) — the 15 June 2026 date
- [Hetzner 2026 price increases — Northflank](https://northflank.com/blog/hetzner-cloud-server-price-increases) — CPX31-US €20.99 → €62.49
- [Render free tier spin-down](https://www.srvrlss.io/provider/render/), [Fly.io billing](https://fly.io/docs/about/billing/), [Railway free tier](https://www.srvrlss.io/provider/railway/) — disqualifications
- [UptimeRobot keyword monitoring](https://uptimerobot.com/keyword-monitoring/) — free-plan monitoring

Measured here, on this Mac, 2026-09-01: OCI regional RTTs; live `api.jameskouvlis.com`
status; parquet row counts and file sizes.
