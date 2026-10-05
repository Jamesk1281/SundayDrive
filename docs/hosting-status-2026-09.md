# Hosting re-check, 2026-09-19 — the verdict stands

**Status: checked 2026-09-19 against `main` at `2d6fbc0`. Nothing was migrated,
provisioned, purchased or signed up for, and no file outside `docs/` was
touched.** Answers [hosting-refresh-brief.md](briefs.md). The
1,028 lines of [hosting-options-findings.md](hosting-options-findings.md) were
**not** redone — only the four dated provider facts it turns on, and the one
measurement that predated A\*.

> **Verdict: unchanged. Oracle Always Free, `us-chicago-1`, 8 GB still stands.**
> Nothing in the entitlement, the enforcement practice or the exit price has
> moved since 2026-09-01, and the re-measured working set moves the sizing
> argument in the safe direction.

Two things did change underneath it, neither fatal:

1. **The 3.53 GB that sized the box does not reproduce — and A\* is not why.**
   The pre-A\* commit measures **4.24 GB on this machine today**. Size on
   **4.4 GB** for the `Router`, ~4.8 GB warm.
2. **Two worker processes no longer fit in 8 GB.** At 4.4 GB each that is
   8.8 GB. `release-plan.md` §7 and the findings' throughput section both say
   "around two workers" on the old figure; on the new one the 8 GB box is a
   **one-worker box**. It changes nothing for a single user — routing does not
   parallelise anyway — but the sentence is now wrong.

---

## 1. The sizing number, re-measured

Same method as 2026-08-31: a `Router` built directly on `data/processed-ne`
(998,252 edges / 801,719 nodes after the turn-restriction split), peak read from
`ru_maxrss`, on this Mac. **Three replicates per arm, interleaved**, because the
first two runs of the same commit disagreed by 0.57 GB.

| | 2026-08-31 (`efbbd28`) | today, `2d6fbc0` | today, `efbbd28` |
|---|---|---|---|
| peak RSS, median of 3 | **3.53 GB** (cold) / 3.85 GB | **4.39 GB** (4.30–4.41) | **4.24 GB** (4.23–4.25) |
| load time, median of 3 | 42.6 s | **49.9 s** (48.8–50.6) | 38.5 s (38.2–39.3) |
| Boston→Augusta, first call | 470 ms | **153 ms** (152–176) | 475 ms (466–476) |
| fastest arm, warm | — | **104 ms** (99–104) | 420 ms (414–423) |
| scenic arm (`pref=1`) | 365 ms | **367 ms** (366–381) | 368 ms (367–369) |

**Latency reproduces the 2026-08-31 record exactly; RSS does not.** The pre-A\*
commit still answers in 475 ms cold and 368 ms on the scenic arm — within 2% of
the numbers recorded against it — while its peak RSS reads 0.71 GB higher than
it did eighteen days ago. The workload did not change, so what moved is the
reading, not the process: one first-of-session load measured 3.69 GB before the
file cache was warm, and every repeat load settled at 4.2–4.4 GB. `DEPLOY.md`
already warns that macOS compresses much of this footprint out of plain RSS.
**Treat 3.53 GB as an under-read and size on the high end.**

### What the ALT tables actually cost

**The brief's 205 MB was arithmetic on the wrong dtype.** `scipy`'s `dijkstra`
does return float64, but `_build_alt_tables` casts before storing
(`pipeline/router.py:1103-1104`), which `router.py:326` already documents:

| | measured |
|---|---|
| dtype and shape | **float32**, 2 × (16 × 801,719) |
| stored | **102.6 MB** (51.3 MB each), not 205 MB |
| peak RSS cost | **+0.19 GB** median (0.07–0.28 across replicates) |
| load time cost | **+11.9 s** (docstring says 9.5 s for the 32 Dijkstras) |
| fastest arm, warm | **420 ms → 104 ms**, a 4.0x cut |
| scenic arm | 367 ms → 367 ms, untouched, as designed |

Measured by neutralising `_build_alt_tables` on the same commit, not by
differencing against the old record. Peak costs roughly twice what it stores
because construction holds both float64 originals — `np.empty((16, n))` plus
`dijkstra`'s return — before the cast; the ranges of the two arms do not
overlap, so the cost is real but it is the same order as this instrument's own
run-to-run spread.

### What it does to the reclaim argument

The argument is unchanged and now has more margin. At **4.4 GB**, or ~4.8 GB
once `LoopPlanner`'s caches warm:

| instance memory | utilisation | idle? |
|---|---|---|
| 12 GB (the full entitlement) | 37% | no — safe |
| **8 GB (recommended)** | **55%**, 60% warm | **no — safe, with margin** |

Provisioning 8 GB rather than the full 12 GB is still the right call for the
reason the findings give: more RAM lowers the percentage and moves the box
*towards* reclamation. Headroom over the measured peak is now ~3.2 GB rather
than the 4.5 GB that document claims.

## 2. The four dated facts

| fact, as of 2026-09-01 | today | source, read 2026-09-19 |
|---|---|---|
| Always Free A1 = **2 OCPU / 12 GB** | **confirmed, unchanged** — as are the three idle-reclaim criteria, memory still A1-only | [docs.oracle.com, Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) |
| Oracle **terminated** over-entitlement instances 18 Aug 2026, email-only warning | **confirmed; no second wave found.** One detail is worse than the record — see below | [InfoQ, 3 Jul 2026](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/); [Oracle's own Free Tier FAQ](https://www.oracle.com/cloud/free/faq/) |
| Exit is **Contabo ~€5.50/mo**; Hetzner US CPX31 ~€62/mo | **both confirmed to the euro.** Contabo Cloud VPS 4 (4 vCPU / 8 GB) **€5.50/mo**, `$6.60` list on the US page (`$5.28` for the first 24 months); Hetzner CPX31 at ASH1/HIL1 **€62.49 / $73.49** | [contabo.com](https://contabo.com/en-us/vps/); hetzner.com's own price matrix |
| **A1 capacity in `us-chicago-1`** | **not retrievable** — unchanged in kind, and still the open question the findings flagged | see below |

**On the termination practice.** Oracle's FAQ states plainly that reclaimed
resources "can't be restored", and the 18 Aug enforcement is well documented.
Search results also surface a Cloud Customer Connect thread titled *"URGENT:
Always Free automated termination, instance and boot volume disappeared; need
data recovery"* — i.e. **data loss, not just instance loss**, which the
2026-09-01 record did not anticipate. **I could not verify that at source:**
`community.oracle.com` serves the page title but no post body to either
`WebFetch` or the browser pane, so the claim is reported, not confirmed. Treat
it as a reason to keep the deployment reproducible from the repo — which, per
the findings' runbook, it already is.

**On capacity.** Oracle publishes no unauthenticated capacity API and checking
requires an account, which this task must not create — so this is **explicitly
unretrievable from here**, exactly as `hosting-options-findings.md` recorded it
as open question 1. What is available: Oracle's FAQ still describes
`out of host capacity` as "a temporary lack of Always Free shapes in your home
region" that "might take several days", and the most recent specific report for
this region is a LowEndTalk thread of **1–2 April 2026** — scripted retries
failing persistently in US-Chicago, and an upgrade to PAYG obtaining the same
shape on the first try two to three days later. Five months old, and the only
thing it establishes is that the risk is real at sign-up. **This is the
irreversible half: the home region is permanent per account.**

### A note on retrieval, for whoever checks next

The brief's warning was half right and the workarounds are worth recording:

- `oracle.com` 403s `WebFetch` but **serves normally in the browser pane** —
  that is how the FAQ above was read. `docs.oracle.com` serves to both.
- Hetzner's per-line pages **no longer render prices at all**: every plan shows
  an empty `from /month` and "This product is currently unavailable", in both
  `WebFetch` and the browser, before and after dismissing the cookie banner.
  The prices are live in the JSON the page itself fetches,
  `/_resources/app/data/bench/cloud_data.json`, which is where the CPX31 figure
  above came from.
- `community.oracle.com` and `lowendtalk.com` 403 `WebFetch`; LowEndTalk renders
  in the browser pane, `community.oracle.com` does not render post bodies.

## 3. The status half

**The API is down.** `https://api.jameskouvlis.com/api/health` → **HTTP 530**,
checked twice, 20:36 and 20:43 EDT on 2026-09-19. Not diagnosed, per the brief:
530 with an absent origin is the expected response to the laptop being off, and
the machine is not reachable from here.

**The cheapest thing that makes it reliable through an App Review window** is to
apply `server/DEPLOY.md` §7 as it is now written — two Task Scheduler tasks
pointed at `python.exe` and `cloudflared.exe` **directly**, never at
`start-windows.bat`, plus the three `powercfg` calls and Windows Update active
hours — and then reboot and confirm `/api/health` answers untouched. That is
$0, needs no account, and is the only test that proves anything. Whether §7 was
ever applied is unknown and unknowable from this session; the `530`s tell you
nothing either way, because a switched-off laptop produces them whether or not
the hardening is in place.

**The alternative is the migration**, whose runbook is written end to end, costs
$0/mo, and whose rollback is starting `cloudflared` on the laptop again. Its
risk is the one fact above that could not be checked: A1 capacity at sign-up,
behind a permanent region choice.

**This is the owner's call and both are acceptable** — `release-plan.md` §7
(unmerged, on `claude/release-plan-sequence`) rates them so, and hosting is
decoupled from submission because `ScenicAPIBaseURL` names a hostname and the
tunnel is the switch. The only hard requirement is that the API answers
*during* review. Worth weighing: the laptop option is free and available today
but its reliability is unverified from here; the Oracle option is verified on
paper end to end but cannot be started at all if Chicago has no A1 capacity, and
finding that out is itself the irreversible step.

## 4. What this re-check did not touch

The verdict, the runbook, the ARM64 wheel analysis, the throughput ceiling, the
region latency measurements and the Oracle-vs-Hetzner comparison in
`hosting-options-findings.md` all stand as written. The only sentences in it
that this document supersedes are the ones quoting **3.53 GB** and the headroom
derived from it, and the "around two workers" ceiling that figure implied.
