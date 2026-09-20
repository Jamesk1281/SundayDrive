# Where the Scenic API should live — findings

Answers `docs/hosting-options-brief.md`. Researched 2026-08-31/09-01 against
`main` at `efbbd28`. **Nothing was migrated, provisioned, purchased or signed
up for**, per the brief's scope. No source file was changed except
`server/DEPLOY.md`, whose §7 and sizing figures needed correcting (see below).

The brief's measured requirements were taken as given and not re-derived. Where
they were cheap to check they held: `graph_nodes.parquet` is 794,685 rows and
`graph_edges.parquet` is 998,252, exactly as stated, and the five serving files
are 364 MiB = **382 MB**, also as stated.

> **Re-checked 2026-09-19 in
> [hosting-status-2026-09.md](hosting-status-2026-09.md). The verdict, the
> runbook and the four dated provider facts all survive; one number does not.**
> Every figure below that reads **3.53 GB** is an under-read — the `Router` peak
> measures **4.39 GB** on current `main` and **4.24 GB** on `efbbd28` itself
> today, so it is the reading that moved, not A\*. Two consequences: the
> headroom claimed over the measured peak is ~3.2 GB, not 4.5 GB, and the
> "around two workers" ceiling in
> [Early-stage capacity](#early-stage-capacity-volume-is-fine-simultaneity-is-the-constraint)
> is now **one** — 8 GB does not hold two 4.4 GB processes. 8 GB remains the
> right size, with more margin against idle reclamation than this document
> claimed.

---

## Final verdict

| question | answer |
|---|---|
| **Is it free?** | **Yes. $0/mo, genuinely, indefinitely** — no card charged, no 12-month clock, no trial expiry. |
| **Free *forever*?** | **No guarantee.** The price is fixed at $0; the *allowance* is not, and Oracle halved it without notice in June 2026. Budget ~nine weeks' warning by email. |
| **Will it pass App Review?** | **Yes** — nothing about the hosting is disqualifying. Just don't migrate and submit in the same week, and fix the raw `HTTP 530` error text first. |
| **Will it carry the early stages?** | **Comfortably** — on the order of 1,000+ drives/day. But routing doesn't parallelise, so the constraint is *simultaneous* reroutes, not volume. |
| **Biggest real risk** | Not RAM, not cost: **getting an A1 instance at all.** US capacity is scarce and the home region is a permanent choice. |
| **If it goes wrong** | ~1 hour and **~€5.50/mo** at Contabo. The hostname is a tunnel, so no DNS change and no App Review. |

**Recommendation: take it.** The full setup is in the
[runbook](#setup-runbook).

---

## Recommendation, in one paragraph

**Go to Oracle Cloud Always Free** — Ampere A1, **2 OCPU / 8 GB**, home region
`us-chicago-1` (fallback `us-ashburn-1`), **$0/mo**. It is the only mainstream
free tier that fits the measured 3.53 GB, it does not sleep, and it has no
12-month clock. Keep the laptop running as the interim and the rollback until
the new box has served for a fortnight.

**But do not treat it as permanent infrastructure.** "Free forever" is not a
property Oracle sells — see
[Is it free forever?](#is-it-free-forever),
which is the most important section in this document. The reason the bet is
still worth taking is that **the downside is bounded**: the whole deployment is
three parquet files, a `git clone`, eleven pinned wheels and one systemd unit,
and the public hostname is a Cloudflare tunnel — so moving hosts again needs no
DNS change, no App Review, and about an hour. The exit price if Oracle's terms
move is **~$6/mo**, not the ~$68/mo an earlier draft of this document implied.

> **Superseded (2026-09-01):** an earlier version of this document led with
> "harden the laptop first" and diagnosed the outages as a process-supervision
> failure. The owner reports the laptop was simply **switched off** and has
> never actually misbehaved — so the 530s were the expected response to an
> absent box, not a fault. The `start-windows.bat` finding below is still true
> as a *latent* gap and is worth closing if the laptop is ever left unattended,
> but it explains nothing that happened. The migration is now the plan on its
> own merits: a laptop that gets turned off is not an always-on host.

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

**But do not conclude from this that US paid hosting is expensive.** Hetzner
specifically has stopped being the cheap answer; the market has not. **Contabo
lists 4 vCPU / 8 GB / 100 GB SSD at ~€5.50/mo with a US location** — a better
shape than CPX31 at a twelfth of the price. For Scenic in particular Contabo's
known weakness barely applies: after the 42.6 s load the workload is pure
CPU and RAM with almost no disk I/O.

So the honest paid floor is **~$6/mo, not ~$68/mo**. That does not change the
recommendation — free still beats $6 — but it matters enormously for how much
risk is worth absorbing to stay free, which is the subject of the next section.

### And a fourth correction — which then corrected itself

The brief says the API has been down "twice in three days". A third outage ran
throughout this research:

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

**It was the box.** The owner confirms the laptop had simply been switched off,
and that it has never actually misbehaved when running. So 530 was the correct
response to an absent origin, and the uptime record is not evidence of a fault —
it is evidence that **the laptop is a machine someone turns off**, which is the
real argument for moving. Two of the three "outages" may well have been the same
thing.

---

## Is it free forever?

**No — not guaranteed.** The *price* is $0 with no expiry; the *allowance* is
not contractual, and Oracle halved it three months ago without announcing it.

The offer itself has **no expiry date**. Oracle's documentation is unambiguous: Always
Free is "a set of Always Free offers that **never expire**", and "after your
trial ends, your account remains active. There is no interruption to the
availability of the Always Free Resources you have provisioned." There is no
12-month clock, no documented inactivity deletion, and no charge unless you
choose to upgrade.

**What is not guaranteed is the size of the allowance — and Oracle cut it,
without announcing it, this summer.**

The sequence, which is the single best piece of evidence anyone has about how
durable this tier is:

| date | what happened |
|---|---|
| **15 June 2026** | Allowance halved, 4 OCPU / 24 GB → 2 OCPU / 12 GB. **No blog post, no announcement.** Users found out by diffing the documentation. |
| ~22 June 2026 | Community reports begin as support clarifies. |
| **18 Aug 2026** | Enforcement. Email to affected tenancies: *"you must reduce your usage by August 18, 2026."* Instances over the entitlement **automatically terminated**. |

So the realistic model is: **the allowance can be halved again at any time, you
will get roughly nine weeks and an email, and if you do not act your instance is
deleted.** Not stopped — the June cut ended in termination for over-limit free
accounts.

Three further risks, from practitioner reports rather than documentation:

- **Idle reclamation genuinely bites.** One report: *"they are watching CPU and
  memory and if they see them idled they will take them away."* Another had a
  lightly-used instance simply *"vanished"*. See the analysis below for why
  Scenic should be exempt — and why that exemption is worth verifying rather
  than trusting.
- **A small number of accounts are terminated without explanation.** Two
  independent reports of accounts closed with support declining to give a
  reason. Set against many reports of *"several permanent Arm-VPSes running in
  OCI for almost 4 years, without paying a single cent"*. It is a tail risk, not
  a norm, but it is not zero and there is no appeal.
- **US capacity may be worse than "try another AD" suggests.** One current
  report: *"Every single availability zone in the U.S. have all been constantly
  emitting out of capacity errors for free tier resource allocation."*

### So why is this still the recommendation?

**Because the cost of being wrong is about an hour and $6/mo.** That is the
argument, and it is worth stating explicitly rather than assuming:

1. **The deployment is unusually portable.** Three parquet files, a `git clone`,
   eleven pinned wheels that all have prebuilt aarch64 *and* x86-64 wheels, and
   one systemd unit. There is no managed database, no provider-specific service,
   no vendor SDK, nothing to rewrite. Moving is a data copy and a `pip install`.
2. **The hostname does not move.** `api.jameskouvlis.com` is a Cloudflare tunnel,
   so the origin can change hosts with **no DNS change, no certificate work, and
   no App Review** — the one constraint that could have made a bad host expensive
   to leave. Run `cloudflared` on the new box, stop it on the old one, done.
3. **The exit is cheap and known.** ~€5.50/mo at Contabo for a strictly better
   shape. If Oracle halves the tier again and the box no longer fits, the
   downside is a $66/year bill, not a stranded service.

A free tier you cannot leave would be a bad bet at any price. This one you can
leave in an hour, so the expected cost of Oracle reneging is small — and in the
meantime it is genuinely $0 for a 2-core ARM box with 8 GB of RAM.

### How to make it as durable as it can be

1. **Provision 2 OCPU / 8 GB — deliberately under the 12 GB you are allowed.**
   Counter-intuitive, and it defends against both risks at once: it keeps memory
   utilization at 44% (well clear of the 20% idle threshold), and it leaves a
   margin under the allowance rather than sitting exactly on it. If you want
   maximum paranoia, **1 OCPU / 6 GB** would survive even another 50% cut
   intact — at the cost of a single core, which is defensible given routing is
   single-threaded anyway, but leaves nothing for the OS mid-route.
2. **Never exceed the entitlement, even briefly.** The trial's $300 of credits
   will happily let you provision a 4 OCPU / 24 GB A1. Don't. That is precisely
   the configuration that got terminated on 18 August.
3. **Watch for the next change.** The June cut was visible in the documentation
   nine weeks before enforcement. Check
   [the Always Free page](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
   quarterly, and **make sure Oracle has an email address you actually read** —
   the 18 August enforcement was announced by email and nowhere else.
4. **Consider Pay As You Go with a $1 budget alert — and understand the trade.**
   This is the biggest available reliability upgrade and it costs **$0 in
   actual spend**, because Always Free resources remain free after upgrading
   (Oracle's own wording: "Oracle doesn't charge for Always Free resources after
   you upgrade"). Upgrading reportedly **exempts you from idle reclamation
   entirely** — Oracle's stated scope is "Always Free customers only", and
   support has told users to convert to PAYG for exactly this reason — and PAYG
   accounts appear to have retained the older 4/24 limits.
   **The trade is a real credit card on file**, so any resource provisioned
   outside the free allowance bills you for real. If you take this route, set a
   budget alert at $1 in OCI Cost Management the same day. **This is your call to
   make, not mine — it is your payment information, and the free tier works
   without it.**

---

## The incumbent: not broken, just not always-on

The owner's account settles this: the laptop works, and the outages were it
being off. There is no reliability defect to fix and no diagnosis to perform.
**The case for migrating is simply that an always-on API cannot live on a
machine that gets switched off** — which is a property of how the machine is
used, not a bug in it.

What follows is kept because it is a real latent gap, and it matters the moment
the laptop is expected to run unattended — including in its new role as the
rollback target.

### The latent gap in `DEPLOY.md` §7

**§7 as written cannot deliver restart-on-failure, even if it was applied
exactly as specified.** §7 says to point Task Scheduler at the
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

Nothing observed here was caused by this — the box was off. But it means the
laptop would not survive a `cloudflared` crash unattended, which is the one job
it still has to do while it is the rollback target.

The circumstantial evidence that the interactive path is the one in use: the
script is written to be double-clicked, it opens titled console windows, it
prints "Started two windows" and a `curl` line for a human to run, and §7's
alternative (`Run whether user is logged on or not`) is incompatible with that
design — in a non-interactive session those windows have no desktop to appear
on.

**Verdict:** the specification is defective, so if the laptop is ever expected
to run unattended — as the rollback target, or as the interim host while the
Oracle box is being acquired — point each Task Scheduler task at the executable
itself rather than at the batch file. I have corrected §7 in `server/DEPLOY.md`.
No further diagnosis is warranted: the owner reports the machine has never
misbehaved when it is on.

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
scope. Worse, one current practitioner report claims *"every single availability
zone in the U.S. have all been constantly emitting out of capacity errors for
free tier resource allocation"* — if that is accurate, `us-chicago-1` helps with
odds but does not guarantee anything.

**So set a stopping rule before you start, rather than grinding indefinitely.**
A reasonable one:

- **Days 1–14:** retry in the chosen US home region, each availability domain,
  a few times a day. Oracle's own documented remedy is exactly this.
- **If still nothing at 14 days:** decide between three known-cost options rather
  than continuing to wait — (a) keep retrying, laptop still serving; (b) accept
  `eu-frankfurt-1`, at a measured **+81 ms** per round trip (~+243 ms on a cold
  reroute, roughly 30%); or (c) spend **~€5.50/mo** at Contabo in a US location
  and stop playing the lottery.

The point of the rule is that (c) exists at $66/year. Weeks of retrying to avoid
that is a bad trade if the retrying is costing real attention.

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

**Do not fake load to defeat this.** The common workaround is a script that
burns CPU or SSHs in every five minutes. Scenic does not need it: the memory
criterion is documented, and Scenic genuinely holds 3.53 GB of real working set
rather than pretending to. Manufacturing idle-looking work to defeat a
resource-efficiency policy is also the kind of thing that reads badly if an
account review ever happens. If Oracle reclaims the box *despite* memory being
above 20%, that is the signal to upgrade to PAYG — which exempts you outright —
not to start burning cycles.

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
| **Hugging Face Spaces free** | 2 vCPU / 16 GB is ample, but free Spaces **sleep after 48 h of inactivity**, and the 382 MB payload would have to live in the repo. Trap 2. |
| **Hetzner US (CPX31, 4 vCPU / 8 GB)** | Works technically. **~€62.49/mo** after the June 2026 increase — 10x Contabo for a worse shape. No reason to choose it. |
| **Hetzner EU (CX33, 4 vCPU / 8 GB)** | ~€6.49/mo and technically fine, but **+81 ms RTT** (+243 ms cold) for no saving over a US Contabo box. |

**Not disqualified — the paid fallback:** **Contabo Cloud VPS 4**, 4 vCPU / 8 GB /
100 GB SSD, **~€5.50/mo**, US location available. Recommended only if Oracle
capacity proves unobtainable or its terms move again. Confirm the price and the
US location in Contabo's own console before buying; the listed rate is a
24-month promotional one and the standard rate applies afterwards.

---

## Cost comparison

| option | monthly | RAM | always-on | main risk |
|---|---|---|---|---|
| **Oracle A1 Always Free** *(recommended)* | **$0** | 8 GB of 12 allowed | yes | Acquisition lottery; allowance cut again; irreversible region choice |
| Oracle A1 on Pay As You Go | **$0** spend | 8 GB (12–24 allowed) | yes | Real card on file — cap it with a $1 budget alert |
| **Contabo Cloud VPS 4** *(paid exit)* | **~€5.50** | 8 GB | yes | Oversubscribed host; slow disk (irrelevant after load) |
| Hetzner EU CX33 | ~€6.49 | 8 GB | yes | +81 ms RTT for no saving |
| Hetzner US CPX31 | ~€62.49 | 8 GB | yes | Price, for nothing extra |
| Laptop (status quo) | $0 | 8 GB | **no — it gets switched off** | Not an always-on host by use, not by fault |

---

## The plan

### Phase 0 — before signing up (10 minutes)

1. **Leave the laptop on** for the duration of the migration. It is the interim
   host and the rollback target; nothing else about it needs to change.
2. **Put a free external monitor on `/api/health` now**, pointed at the laptop.
   This is worth doing before the migration rather than after, because it gives
   you a baseline and it is the thing that has always been missing — the current
   answer to "how do you find out it is down" is "someone curls it". Details
   under [Uptime](#uptime-what-watches-it-and-what-restarts-it).
3. **Decide the Pay As You Go question** — see
   [How to make it as durable as it can be](#how-to-make-it-as-durable-as-it-can-be).
   It materially changes the reliability of the result and it is easier to decide
   before signup than after.

**Optional, and only if the laptop will ever run unattended:** close the §7 gap
by pointing two Task Scheduler tasks at `…\.venv\Scripts\python.exe` and
`cloudflared.exe` directly — never at `start-windows.bat`, which exits
immediately and so defeats restart-on-failure. Each: *At startup*, *Run whether
user is logged on or not*, and on the **Settings** tab *If the task fails,
restart every 1 minute*. Not urgent given the laptop has never actually
misbehaved.

### Phase 1 — acquire the Oracle box (no deadline, no pressure)

1. Sign up for Oracle Cloud Free Tier. **Choose `us-chicago-1` as the home
   region** (or `us-ashburn-1` if you are willing to trade capacity odds for
   12 ms). This choice is permanent — it is the single most consequential click
   in the whole plan.
2. Create **one** `VM.Standard.A1.Flex` instance: **2 OCPU, 8 GB**, Ubuntu 24.04
   (Python 3.12), 50 GB boot volume. Not 12 GB — see the reclaim table. Not more
   than 2 OCPU total, ever — see the landmine.
3. **Give Oracle a working email address** and keep it monitored. The 18 August
   enforcement was announced by email and nowhere else; that mailbox is your only
   warning if the allowance is cut again.
4. If `Out of host capacity`: try each availability domain, then retry over
   following days, against the 14-day stopping rule above. The laptop is serving
   throughout, which is the entire point of the ordering.
5. Open nothing inbound. The Cloudflare tunnel dials out, so the instance needs
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
investigation, and below 2.4 GB would re-open the reclaim question. **CPU time is
the figure that will move most** — see
[Will it survive App Review and the early stages?](#will-it-survive-app-review-and-the-early-stages).

| measure | how | expected | brief's figure |
|---|---|---|---|
| peak RSS | `systemd-cgtop` / `ps -o rss= -p $(pidof python3.12)` after first route | 3.5–4.2 GB | 3.53 GB |
| load time | time from service start to first `/api/health` 200 | **85–105 s** — the A1 core is under half an M2's | 42.6 s |
| one real route | Boston → Augusta ME, 262 km, timed server-side | **1.7–2.1 s** — same reason | 835 ms |
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

## Will it survive App Review and the early stages?

Two separate questions. Short answers: **App Review — yes, with one scheduling
rule. Early stages — yes, with a lot of room, but the ceiling is lower and
weirder than it looks.**

### The A1 core is about half the speed of the Mac these numbers came from

Every figure in the brief was measured on an **Apple M2**. Oracle's A1 is an
Ampere Altra Q80-30 — Neoverse N1 cores, documented as **less than half** the
single-core speed of an M2. This workload is a `scipy` Dijkstra: pointer-chasing
and memory-latency bound, which is where Apple's memory subsystem is strongest
and the N1's is weakest. So expect the gap to land at the bad end.

| | measured (M2) | expected (A1) |
|---|---|---|
| full API request, two Dijkstras | 835 ms | **~1.7–2.1 s** |
| `Router` load at boot | 42.6 s | **~85–105 s** |
| peak RSS | 3.53 GB | 3.5–4.2 GB (unchanged by CPU) |

**This is an estimate, not a measurement** — it is the first thing to check on
the box, and if a route comes back in ~2 s you have confirmed it. The load time
matters only at boot. The per-request figure is a real UX regression on route
*planning*, and it is the one honest cost of choosing free over paid.

It is **not** a problem for the case that matters. A mid-drive reroute at ~2 s is
fine; the disqualifying number was 42.6 s, which is why serverless was ruled out
and why an always-warm box is the whole point.

### Early-stage capacity: volume is fine, simultaneity is the constraint

The counter-intuitive part, straight from `DEPLOY.md`: **routing does not
parallelise.** `scipy.sparse.csgraph.dijkstra` holds the GIL, so four concurrent
routes measured 0.482 s against 0.519 s serial — a 1.08x speedup. waitress's four
threads keep the server *responsive*, not faster.

**So the second OCPU buys you nothing in throughput.** One route computes at a
time, whatever the core count. The ceiling is:

- **~0.5 requests/second sustained** on the A1 (one ~2 s route at a time).
- A typical 30-minute drive is roughly 1 initial route plus a handful of
  reroutes — call it **5–10 requests**.
- At a comfortable 30% utilisation that is **~500 requests/hour**, or on the
  order of **1,000+ drives a day**.

Nobody reaches that in early stages. What you *can* hit early is a **simultaneity
stall**: three people rerouting in the same second means the third waits ~6 s
behind the other two. With a handful of users that is rare and recoverable; it is
also the first thing that will break if the app gets popular.

**The scaling lever, when it comes:** more throughput means more *processes*, and
each one is another full ~3.53 GB copy of the graph. Two workers need ~7.1 GB,
which needs the full 12 GB allowance. That is the one argument for provisioning
12 GB now instead of 8 — but resizing an `A1.Flex` is an edit-and-reboot, not a
rebuild, so **start at 8 GB and resize if you ever need to.** Do not pre-buy
capacity against growth that may not happen, especially when sitting exactly on
the free allowance is its own risk.

### App Review

Hosting will not fail review on its own. Apple's reviewers are a normal client
hitting a public HTTPS endpoint; there is no auth to fumble, and Chicago is
~50–60 ms from Cupertino. Four things are worth knowing:

1. **The backend must be up *whenever* they get to it** — review can land days
   after submission, at any hour, and a backend that answers 530 gets you a
   Guideline 2.1 "App Completeness" rejection almost automatically. This is the
   single biggest hosting-shaped review risk.
2. **Do not migrate hosts and submit for review in the same week.** Obvious once
   said, easy to do by accident. Cut over, let it run a fortnight, *then* submit.
3. **Fix the raw error text first.** `docs/consumer-polish-brief.md` item 1 already
   records that an outage reaches the user as small red text reading `HTTP 530`.
   A reviewer who sees that sees a broken app. That is an app-side fix, not a
   hosting one, but it is on the critical path to a clean review.
4. **The rate limit is fine.** 60 req/min per IP at Cloudflare is far above
   anything a reviewer generates, and the ceiling above is the real constraint
   anyway.

Nothing in Oracle's Acceptable Use Policy restricts serving a public API, a
commercial app's backend, or App Store distribution. The free tier carries **no
SLA**, which is worth being clear-eyed about — but neither does a laptop.

---

## Setup runbook

Everything below runs after you have an A1 instance and its public IP. Steps 1–2
are console work; the rest is copy-paste. Nothing here was executed — **no
account exists and nothing was provisioned.**

### 1. Sign up and choose the home region — the one irreversible click

Oracle Cloud Free Tier. **Home region `us-chicago-1`** (fallback
`us-ashburn-1`). This cannot be changed afterwards and Always Free compute only
exists in it. Give Oracle an email address you actually read.

### 2. Create the instance

`VM.Standard.A1.Flex` — **2 OCPU, 8 GB**, Ubuntu 24.04 (ships Python 3.12), 50 GB
boot volume, and **add your SSH public key**. Leave the security list closed:
the tunnel dials out, so no ingress rule is needed at all.

Keep the Oracle Cloud Agent's **monitoring plugin enabled** — reported memory
utilisation is what keeps the box off the idle-reclaim list.

On `Out of host capacity`, try each availability domain, then retry over days
against the 14-day stopping rule above.

### 3. Base packages

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git rsync
```

### 4. Code — clone, never hand-copy

```bash
git clone https://github.com/Jamesk1281/Scenic.git ~/Scenic && cd ~/Scenic && git log --oneline -1
```

Compare that hash against `git log --oneline -1` on the Mac **before going
further**. `DEPLOY.md` records a real incident where old code met new parquets
and died with `KeyError: 'c_green'`.

### 5. Dependencies, from the lock file

```bash
python3 -m venv ~/Scenic/.venv && ~/Scenic/.venv/bin/python -m pip install -r ~/Scenic/server/requirements-serve.lock.txt
```

On aarch64 this downloads eleven prebuilt wheels and compiles nothing. If you see
a compiler invoked, stop — you are on the wrong Python (needs 3.10–3.13) or the
wrong libc.

### 6. Data — 382 MB, resumable, run from the Mac

```bash
rsync -avP --append-verify data/processed-ne/graph_edges.parquet data/processed-ne/graph_nodes.parquet data/processed-ne/turn_restrictions.parquet data/processed-ne/access_ways.parquet data/processed-ne/access_entries.parquet ubuntu@<INSTANCE_IP>:~/Scenic/data/processed-ne/
```

`--append-verify` is what makes a dropped home-upload connection resumable.
Re-run the same command until it completes clean.

### 7. Verify before exposing anything

```bash
cd ~/Scenic && SCENIC_DATA=~/Scenic/data/processed-ne .venv/bin/python -m pip install pytest && SCENIC_DATA=~/Scenic/data/processed-ne .venv/bin/python -m pytest tests/
```

**Expect 207 passed, 4 skipped. Count the skips, not the passes** — 4 means the
access layer loaded, 8 means it never made it across. Anything *failing* means
the code and the data disagree; do not proceed.

### 8. systemd for the API

```bash
sudo tee /etc/systemd/system/scenic-api.service >/dev/null <<'EOF'
[Unit]
Description=Scenic routing API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Scenic
Environment=SCENIC_HOST=127.0.0.1
Environment=SCENIC_DATA=/home/ubuntu/Scenic/data/processed-ne
ExecStart=/home/ubuntu/Scenic/.venv/bin/python /home/ubuntu/Scenic/server/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now scenic-api
```

The unit reports *active* as soon as the process forks, but the graph needs
~90 s before it answers. Wait, then:

```bash
curl -s http://localhost:5057/api/health
```

Expect `{"status":"ok","nodes":794685,...}`. **794685 is the check** — a wrong
number means the wrong parquets.

### 9. The tunnel

```bash
curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o /tmp/cloudflared.deb && sudo dpkg -i /tmp/cloudflared.deb && cloudflared --version
```

Authenticate and reuse the **existing** `scenic` tunnel rather than making a new
one — the DNS record already points at it:

```bash
cloudflared tunnel login
```

Copy the existing tunnel's credentials JSON from the laptop to
`/etc/cloudflared/`, write `/etc/cloudflared/config.yml` with the same
`tunnel:`/`credentials-file:` and an ingress rule for
`api.jameskouvlis.com → http://localhost:5057`, then:

```bash
sudo cloudflared service install && sudo systemctl enable --now cloudflared
```

### 10. Cut over

**Stop `cloudflared` on the laptop first.** Two connectors on one named tunnel
will load-balance, and you will get intermittent answers from whichever box is
less ready. Then from anywhere:

```bash
curl -s https://api.jameskouvlis.com/api/health
```

### 11. Monitor it

Free UptimeRobot monitor on `https://api.jameskouvlis.com/api/health`, 5-minute
interval, **keyword `794685`** — that asserts the right graph is loaded, not just
that something is listening. Alert to an address you read.

### 12. Measure, and compare against the table above

Peak RSS, load time, and one real route (Boston → Augusta ME). If RSS lands
**below 2.4 GB**, re-check the idle-reclaim maths — that is the only result that
would change the shape recommendation.

### Rollback, at any point

Start `cloudflared` on the laptop, stop it on the Oracle box. That is the whole
procedure. Keep the laptop able to do this for a fortnight after cutover.

---

## What I could not establish

Stated plainly, because a silently skipped question is the failure mode the brief
named:

1. **Whether A1 capacity is available in `us-chicago-1` or `us-ashburn-1` right
   now.** Requires an account. Out of scope. This is the recommendation's main
   open risk and the reason for the phased ordering.
2. **How much slower the A1 actually is.** The 2–2.5x estimate is inferred from
   published Neoverse N1 vs Apple M2 single-core comparisons, not measured on
   this workload. It is the first thing to check on the box, and the only
   estimate here that would change the *experience* of using the app if wrong.
3. **What Oracle actually does to a reclaimed instance** (stop vs delete). Not
   stated in Oracle's documentation; secondary sources say "stopped, volumes
   preserved". Either way it is a total outage for an always-on API.
4. **Whether the memory-utilization criterion is skipped when the Oracle Cloud
   Agent monitoring plugin is disabled.** Verify on the box once it exists — this
   is the mechanism Scenic's reclaim exemption depends on.
5. **Whether Pay As You Go really exempts you from idle reclamation.** Strongly
   and consistently reported, including by Oracle support in user accounts, but
   *not stated in Oracle's documentation*. Oracle's written scope is "Always Free
   customers only", which implies it. Do not treat it as contractual.
6. **Whether PAYG accounts genuinely retained the 4 OCPU / 24 GB limits.**
   Reported by several users via support email, and contradicted by the public
   documentation's "All tenancies get the first 1,500 OCPU hours". Irrelevant to
   the recommendation, which stays inside 2 OCPU either way.
7. **Exact current prices at Hetzner (CPX31-US, €62.49) and Contabo (€5.50).**
   Both from secondary reporting or promotional listings. Confirm in the
   provider's own console before spending anything.

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

- [Oracle quietly halves free tier A1 limits — InfoQ](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) and [Linuxiac](https://linuxiac.com/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/) — the 15 June 2026 cut, the absence of any announcement, and the fate of over-limit instances
- [HN discussion, Oracle Always Free ARM cut](https://news.ycombinator.com/item?id=49183750) — the 18 Aug 2026 enforcement email, idle-reclamation experiences, PAYG exemption reports, US capacity reports, and two accounts terminated without explanation
- [Contabo Cloud VPS](https://contabo.com/en/vps/) — 4 vCPU / 8 GB at ~€5.50/mo, US location
- [Hetzner 2026 price increases — Northflank](https://northflank.com/blog/hetzner-cloud-server-price-increases) — CPX31-US €20.99 → €62.49
- [Render free tier spin-down](https://www.srvrlss.io/provider/render/), [Fly.io billing](https://fly.io/docs/about/billing/), [Railway free tier](https://www.srvrlss.io/provider/railway/) — disqualifications
- [UptimeRobot keyword monitoring](https://uptimerobot.com/keyword-monitoring/) — free-plan monitoring
- [Ampere Altra Q80 review — Phoronix](https://www.phoronix.com/review/ampere-altra-q80) and [HN: Ampere vs M1/M2](https://news.ycombinator.com/item?id=32165554) — Neoverse N1 single-core against Apple M2, the basis for the 2–2.5x estimate

Measured here, on this Mac, 2026-09-01: OCI regional RTTs; live `api.jameskouvlis.com`
status; parquet row counts and file sizes.
