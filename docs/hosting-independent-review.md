# Hosting: an independent review before the home region is chosen

**Status: written 2026-09-28 against `main` at `3402298`. It answers
[hosting-independent-review-brief.md](hosting-independent-review-brief.md).
Nothing was signed up for, trialled or bought. No hosting file was edited.
Every price and allowance below was read at its primary source on 2026-09-28,
unless the row says otherwise.** No workload figure was re-measured. The RSS,
load-time and latency numbers are the brief's own.

---

## Verdict

**Proceed with the Oracle plan, with named changes. The most important changes
are not about Oracle.**

1. **Renew `jameskouvlis.com` first. It expires on 2026-10-28, 30 days from
   now** (RDAP, read 2026-09-28). The app has `api.jameskouvlis.com` baked in
   (`ios/project.yml:63`), so if the domain lapses, every installed copy stops
   working until a new build passes App Review. None of the four hosting
   documents mention this.
2. **Harden the laptop today, and keep it as a serving origin rather than a
   rollback.** It is the only step that can fix today's 530 on any timescale.
   It costs nothing, it has 16 GB or more (twice the planned Oracle box), and
   every other branch of this plan needs it anyway.
3. **Add Oracle as a second connector on the same `scenic` tunnel, not as a
   replacement. Gate each connector on `/api/health`.** A Cloudflare tunnel
   supports this natively: requests go to the nearest connector, and fail over
   when a connector disappears. The Oracle-specific risks (the capacity
   lottery, idle reclaim, account termination, another cut to the allowance)
   and the laptop-specific ones (switched off, rebooted, moved) stop being
   outages. The API goes down only when both fail at once. The cost is $0.
4. **Choose the home region by capacity, not latency.** Behind a tunnel, the
   origin's distance costs about one round trip per request, not three. The
   plan's "+243 ms" for Frankfurt is really about +81 ms, and every US region
   is within about 50 ms of Chicago. Stay in the US. The only public report
   specific to `us-chicago-1` (1 Apr 2026) is negative.
5. **The paid fallback costs more than the plan says.** Contabo in a US region
   is **$6.58/mo on a prepaid 24-month term, or $7.90/mo month to month**, not
   "~€5.50". The plan left out the US location surcharge.
6. **Don't buy hardware, and don't shrink the working set to save on hosting.**
   After the 2026 DRAM price spike, no suitable box costs $100 new. The cheapest
   paid VPS tiers already come with 8 GB. A smaller working set would also
   weaken the one defence the Oracle box has against idle reclaim.

**Is moving right at all?** Moving *off* the laptop is not. Adding an origin in
a datacentre is. **Is the Oracle plan what it seems?** Mostly, on Oracle's
written terms. It overstates how much warning you get and how cheap the exit
is, and it misses an account-level idle rule, that PAYG is one-way, and that
PAYG budgets don't cap anything. **Is there a better option?** Not a better
host. A better topology, built from hardware the owner already has.

---

## How this was done

The criteria and option set were written down *before* the four hosting
documents were read. Those documents were then read as the plan under review.
Their claims were checked against Oracle's, Cloudflare's, Apple's and the
providers' own pages, not against each other.

**Criteria, in order of weight:**

1. The chance that the API is down when a reviewer or user tries it, and how
   long it stays down (who notices, and how recovery happens).
2. Reroute latency, and outage length after any restart.
3. Cash cost, monthly and one-off.
4. How durable the offer is.
5. Irreversibility.
6. Ops burden for one student.
7. Privacy and legal obligations.
8. Exit cost.

**Options:**

- The laptop, hardened
- Owned hardware at home, behind the same tunnel
- Oracle as planned
- Budget paid VPSes
- Shrinking the working set
- Two connectors on one tunnel

---

## 1. Ranked options

The ranking is against the brief's requirement: answers whenever tried, at a
cost as close to $0 as is sensible. Laptop electricity is unmeasured. It is
priced at Massachusetts' **30.49 ¢/kWh** (EIA *Electric Power Monthly* Table
5.6.A, July 2026, released 2026-09-24). At that rate **every 10 W left on
around the clock costs about $2.23/mo**, so a laptop idling at 8–20 W costs
$1.78–4.45/mo. That is $0 if electricity comes with the rent.

| # | option | monthly | one-off | the risk that would actually bite | App Review |
|---|---|---|---|---|---|
| **1** | **Laptop hardened + Oracle A1 (2 OCPU / 8 GB) as a second, health-gated connector** | **$0** hosting, plus laptop electricity ($1.78–4.45) | $0. Needs a credit card, or a debit card that works like one | Both down at once (the laptop off while Oracle reclaims or terminates). Code or data skew between the two boxes. Gating the Windows side is the fiddly part | **Meets it.** Each box covers the other's outages. Deploys can be rolling, with no downtime during a review |
| 2 | Laptop hardened + **Contabo Cloud VPS 4, US-Central** as the second connector, if Oracle capacity never comes | **$6.58** on a 24-month prepaid term, or **$7.90** month to month (Contabo configurator) | **$0 setup.** The 24-month rate is prepaid: $126.72 was "due today" before the region fee; about $158 with it | Contabo's "Core" tier is shared. Contabo itself pitches its *Performance* line, not Core, at "API services". Expect latency to vary, but stay well inside "a few seconds". The promo rate ends at 24 months | Meets it. Provisioning takes minutes, with no lottery |
| 3 | Oracle A1 as planned, on its own, with the laptop as a manual rollback | $0 | $0, card as above | **The recovery path fails with the thing it recovers from.** A reclaimed or terminated A1 comes back only if A1 capacity exists. The laptop rollback decays once the fortnight is up. Account-level idle rule (§2, C10). About 13 days' email warning of a cut | Meets it once it's running. **Nothing works until capacity is won** |
| 4 | Contabo on its own (US-Central) | $6.58 / $7.90 | $0 setup; prepay as above | Shared-tier latency variance. One provider with no second origin. Contabo GmbH is a German company (§3, M6) | Meets it |
| 5 | Laptop hardened, on its own | $0 plus electricity | $0 | **It gets switched off.** Every public check since the NE build found it off (§2, C6). Forced Windows reboots cost 1–2 minutes each. Home power and ISP outages. The residential ISP's or university's acceptable-use policy (§3, M5) | Meets it **if it is left on**. Apple reviews 90% of submissions within 24 hours, so the exposure window is usually one day |
| 6 | Owned hardware: **Raspberry Pi 5 8 GB** at home, same tunnel | Electricity, a few watts (unmeasured) | **$200 board only** (Adafruit, in stock), plus PSU, case and storage. The official 16 GB board is $305 | Same site risks as the laptop, and no battery to ride through power blips. Costs about 30 months of Contabo up front | Same as the laptop |
| 7 | Owned hardware: a new N150 mini PC, 16 GB | Electricity | **$385** on sale ($469 regular), pre-order (Beelink EQ14) | As #6. Buys nothing the 16 GB laptop doesn't already have | Same as the laptop |
| 8 | Other paid: OVHcloud VPS-2 (4 vCores / 8 GB) | from **$8.50** | — | More expensive than Contabo for the same memory | Meets it |
| 9 | Other paid: Hetzner US CPX31 (4 vCPU / 8 GB) | **$73.49** (€62.49) | $0 | Price | Meets it |
| 10 | Shrink the working set | Engineering days | — | Saves no money at today's prices (§2, C7) and weakens Oracle's reclaim defence | n/a |

**Why #1 beats #3, and why the plan missed it.** The plan treats the laptop
and Oracle as either/or: the laptop is the interim host, then the rollback.
It says outright not to run two connectors (`hosting-options-findings.md:684-686`,
`server/DEPLOY-oracle.md:380-383`). That rule is right about *ungated*
connectors and wrong as a general rule (C12 below).

The two machines fail for unrelated reasons. The laptop fails through a
person, the house or Windows. Oracle fails through capacity, policy or the
account. So the chance that both are down at the moment a reviewer taps
"Route" is roughly the product of two small numbers, not the larger of them.

**The one real cost of #1** is operating two origins:

- Every deploy has to go to both boxes.
- Each connector must attach only once its own API answers.

A sketch of the Linux side (untested; verify it on the box):

```sh
#!/bin/sh
# run-connector.sh: hold the tunnel only while this box's API answers.
while :; do
  until curl -sf --max-time 10 http://127.0.0.1:5057/api/health >/dev/null; do sleep 5; done
  cloudflared tunnel run scenic & pid=$!
  while kill -0 "$pid" 2>/dev/null && curl -sf --max-time 20 http://127.0.0.1:5057/api/health >/dev/null; do sleep 15; done
  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
done
```

Run it from the `cloudflared` unit in place of `cloudflared tunnel run`. On
the laptop, the same loop becomes one PowerShell script run by the §7 Task
Scheduler task. A deploy then works like this: stop the connector on box A,
restart its API, let the gate reattach it, then repeat on box B. Neither
restart becomes a public outage.

**One consequence to expect.** Cloudflare sends each request "to the
geographically closest replica", and there is no way to steer traffic on the
free plan. New England users will mostly reach the Boston laptop. A reviewer
in Cupertino will probably reach Chicago. Both boxes therefore have to be
right, not just up. That is the reason for M13 below.

---

## 2. The plan's claims, one by one

The brief lists seven inferred claims. The rest were found while reading.

| # | claim | status | evidence |
|---|---|---|---|
| C1 | **"A1 is about 2–2.5x slower than an M2."** | **Unverifiable, and not load-bearing** | Checking it needs the box. It doesn't matter much, because the scenic arm settles the whole graph "whatever the trip" (`pipeline/router.py:1370-1380`; `docs/route-distribution-study.md:78`). So the 367 ms Boston–Augusta figure is close to that arm's ceiling, not a typical case. Even at **4x**, a request is about 2 s: inside "a few seconds", and far inside the app's 15 s request timeout (`ios/Sources/RouteService.swift:94`). The only thing the ratio really moves is restart downtime, about 100–200 s. Two requests arriving together queue behind the GIL, so the second waits about one extra route time. `/api/loop` was never timed at all, on any box |
| C2 | **"Idle reclaim can't fire, because memory is 55%."** | **Holds narrowly; "can't" is broader than the evidence** | Oracle's text: instances are idle if 95th-percentile CPU, network *and* memory ("applies to A1 shapes only") are all under 20% for 7 days. The memory metric is "space currently in use… percentage of used pages", and it needs the Compute Instance Monitoring plugin enabled and running. So 4.4 GB of anonymous memory on 8 GB counts. But Oracle says idle instances "**may** be reclaimed". It never says busy ones are safe. Reclaim is only one of four ways to lose the box (the others are C9, C10 and termination without reason, below). And the defence couples hosting to code: any future memory optimisation that takes RSS under 1.6 GB re-arms reclaim, silently |
| C3 | **"Pay As You Go exempts you from reclaim and costs $0."** | **$0 holds. The exemption is unverifiable. "Capped by a $1 alert" is broken** | Oracle confirms the $0: it "doesn't charge for Always Free resources after you upgrade, and will only charge you for resource usage above the Always Free limits". The docs are silent on any reclaim exemption; the reclaim clause covers "Idle Always Free compute instances". Three things the plan doesn't say. **PAYG is one-way**: "There is no option to downgrade your account." **Budgets are "soft limits"**, evaluated "every 24 hours", so `hosting-options-findings.md:547-549`'s "How to cap it… budget alert at $1" caps nothing. **A future allowance cut becomes a bill instead of a termination**: A1 lists at $0.01/OCPU-hr and $0.0015/GB-hr, so this box would cost **$23.81/mo** if the free allowance went to zero (Oracle price list). That is 3.6 times Contabo |
| C4 | **"A1 capacity is obtainable in `us-chicago-1`."** | **Unverifiable without an account, and the one piece of evidence points the other way** | Oracle publishes no capacity figures before sign-up. The only report specific to this region is a LowEndTalk thread of 1 Apr 2026 ("Oracle Free Tier 'Out of Capacity' in Chicago region"): scripted retries failed, and an upgrade to PAYG got the shape. Chicago was chosen for latency (`hosting-options-findings.md:388-392`), which doesn't matter behind a tunnel (C8). It does have 3 availability domains, and that matters because Oracle's only remedy is "try… a different availability domain". Phoenix and Ashburn also have 3. San Jose has 1 |
| C5 | **"Contabo is a fine exit at ~€5.50/mo."** | **Holds as an exit. The price is broken for a US box. "Oversubscription barely matters" is doubtful** | Contabo's US configurator: Cloud VPS 4 costs $6.60 month to month, $5.61 over 12 months, $5.28 over 24 months, with no setup fee. The 24-month rate is prepaid. A US region adds **$1.30 (Central), $1.60 (West) or $1.90 (East) per month**, and only the EU region is free. So a US box is **$6.58–7.90/mo**. On quality, Contabo itself says Core VPS is for "lighter workloads" and Performance VPS for "API services". Its Performance tier (Cloud VPS Plus 4, 8 GB) is $13.00/mo on a 24-month promo, $16.25 list. This workload is memory-bandwidth-bound: this repo recorded **6–17x** timing inflation from a co-tenant on a shared machine (`docs/component-rebuild-cache-findings.md:147-151`). Latency on a shared host will vary. Whether it ever leaves "a few seconds" can't be known without a box |
| C6 | **"The laptop is not an always-on host."** | **Holds as a statement about how it is used. The hardening is untested, not rejected. The plan undersells the machine** | It was off at every public check on record: 2026-08-29, 08-31, 09-01, 09-19 and 09-28. That is about use, not fault (brief trap 5). Nobody has recorded applying `server/DEPLOY.md` §7 and then doing its reboot test. The findings' cost table gives the laptop **8 GB** (`hosting-options-findings.md:583`), but `docs/new-england-rollout.md:399-400` records **16 GB or more** (confirmed 2026-08-26). Not established: whether it has ever served the New England build. Every check since that build landed found it off |
| C7 | **The "Disqualified" table** | **Incomplete in scope. One entry's reasoning is broken** | Owned hardware: a Pi 5 8 GB is **$200** board-only at Adafruit. The official 16 GB is **$305**. Raspberry Pi's own post of 2026-02-02 added $30 to the 8 GB price, on top of earlier rises. A new N150 16 GB mini PC is **$385** (Beelink). So "buy a $100 box" doesn't exist new in September 2026. Other budget VPSes: OVHcloud VPS-2 (8 GB) from $8.50. Shrinking the working set pays nothing at these prices. Contabo's smallest plan is already 8 GB. OVH's 4 GB VPS-1 ($4.54) saves about $4/mo. Free 1 GB tiers would need about a 6x cut. And it weakens C2. The Hetzner EU / Frankfurt rows rest on the broken +243 ms (C8) |
| C8 | "Frankfurt costs **+243 ms on a cold connection** (TCP + TLS 1.3 + request ≈ 3 RTTs), about 30%" (`hosting-options-findings.md:396-398`, `:415`, `:564`) | **Broken** | Cloudflare terminates the phone's TCP and TLS at the nearest Cloudflare data centre, whichever region the origin is in. `cloudflared` holds the tunnel open ("once the connection is established, traffic flows in both directions over the tunnel"), so no handshake happens per request. The origin's distance is paid about **once per request**: roughly +81 ms for Frankfurt, which is about 10% of the 835 ms request the doc used and 6–8% of an A1 request. There was never a capacity-versus-latency conflict to resolve. Stay in the US for jurisdiction (M6), not speed |
| C9 | "Budget **~nine weeks'** warning by email" (`hosting-options-findings.md:33`, `:182`, `:236`) | **Broken** | Nine weeks is how long ago Oracle *edited its documentation* (15 June), before enforcement on 18 Aug. The email came the week of **5 Aug**: "Beginning on August 18, 2026, Oracle will begin enforcing the updated Always Free compute limits. Compute instances that exceed the Always Free entitlement will be automatically terminated." That is about **13 days**, from an article of 2026-08-05 quoting the email (secondary). Someone who only reads the mailbox gets two weeks, not nine |
| C10 | "No documented inactivity deletion" (`hosting-options-findings.md:166`, `:535`) | **Broken** | Oracle's Free Tier FAQ, under eligibility: "**Accounts left idle for 30 days or more may be deemed abandoned and become eligible for suspension or termination.**" It doesn't define what makes an *account* idle, as opposed to an instance. A box nobody logs into could plausibly qualify. Signing into the console monthly costs nothing |
| C11 | "Its own FAQ says reclaimed resources 'can't be restored'" (`server/DEPLOY-oracle.md:527`; `docs/hosting-status-2026-09.md:98-99`) | **Misapplied** | In the FAQ, that sentence is about *paid* resources reclaimed when a trial ends. The applicable text is that over-limit A1 instances are "disabled and then deleted after 30 days". Assuming deletion is still the right posture |
| C12 | "Only one `cloudflared` should run the named tunnel… two connectors will load-balance" (`hosting-options-findings.md:684-686`; `server/DEPLOY-oracle.md:380-383`, `:513`) | **Half right** | Cloudflare doesn't load-balance replicas. A request goes "to the geographically closest replica. If that connection fails, Cloudflare retries with other replicas", and "replicas do not support traffic steering". The harm the plan describes is real, but it comes from a connector attached to a box that isn't ready. The fix is gating, and the gain is redundancy (§1) |
| C13 | Rollback is "start `cloudflared` on the laptop again" | **Holds mechanically. Decays in practice** | It needs a person to read an alert, and a laptop that is switched on, on the same commit, holding the New England parquets and the tunnel credentials. The plan keeps that true for "a fortnight after cutover" and no longer |
| C14 | "If it goes wrong: ~1 hour and ~€5.50/mo" (`hosting-options-findings.md:37`) | **Understated** | The hour is setup only. Add noticing the outage (5-minute monitor), opening a provider account and paying, and the Mac being present to push 382 MB, since the parquets exist only in its gitignored `data/processed-ne/` and on any box already given a copy. The price is C5's. Under #1 in §1, neither applies: the other box is already serving and already holds a copy of the data |
| C15 | "A payment card" (`server/DEPLOY-oracle.md:31`) | **Incomplete** | Oracle accepts "credit cards and debit cards that function like credit cards", not "debit cards with a PIN or virtual, single-use, or prepaid cards". It "may periodically check the validity of your card", and billing details must stay valid "for the duration of the account". So a card that expires is a compliance question, not only a billing one |
| C16 | "If it refuses you indefinitely, the remedy is a new tenancy under a different email" (`hosting-options-findings.md:373-374`) | **Broken, and risky** | The FAQ: "One Oracle Cloud Free Trial or Always Free account is permitted per person. Creating or attempting to create multiple free accounts is prohibited." The home region is permanent *for the person*, not for an email address |
| C17 | 530 means "Tunnel up, **no origin**, the service is down or still loading" (`server/DEPLOY-oracle.md:507`) | **Broken** | It contradicts `server/DEPLOY.md:364-365`. With `cloudflared` connected and the API down or still loading, the answer is **502**. A **530** means no connector at all. Misreading this sends someone to `journalctl` for the wrong process |
| C18 | "No SLA, but neither does a laptop" | **Holds. One point is missing** | "Customers using only Always Free resources are not eligible for Oracle Support." There is no channel to query a termination |
| C19 | Always Free A1 = 2 OCPU / 12 GB, with the three idle criteria | **Holds** | docs.oracle.com, *Always Free Resources*, read 2026-09-28, unchanged |
| C20 | Hetzner US CPX31 = €62.49 | **Holds** | `hetzner.com/_resources/app/data/bench/cloud_data.json` (last-modified 2026-09-22): ASH1/HIL1 €62.49 / $73.49 |
| C21 | "`TimeoutStartSec` must exceed the load time" (`hosting-options-findings.md:678`) | **Irrelevant** | With `Type=simple`, systemd counts the unit as started the moment it forks. The runbook's unit correctly omits it |

---

## 3. What none of the four documents mention

- **M1. The domain expires in 30 days.** RDAP for `jameskouvlis.com`:
  registered 2025-10-28, **expires 2026-10-28**, registrar GoDaddy. This is the
  only hosting item with a hard deadline, and the only one that can't be
  undone after the fact. Everything else in the stack can move without a new
  build *because* the hostname stays fixed, and the hostname stays fixed only
  while the domain is registered.
  - Check auto-renew today. RDAP doesn't show it publicly.
  - GoDaddy lists .com at **$22.99/yr** ("Additional year(s) $22.99").
  - Cloudflare Registrar "does not mark up domain prices at all", and the
    zone's DNS is already there. A transfer also adds a year, but it takes
    days. With 30 days left, renewing where it is registered is the safe move.
- **M2. The availability requirement never ends.** The brief frames it around
  review, and review is usually short: "90% of submissions are reviewed in less
  than 24 hours" (Apple, *App Review*). The harder requirement is the one
  after: "Apps that stop working or offer a degraded experience may be removed
  from the App Store at any time" (App Review Guidelines, introduction). Every
  update is reviewed again. And guideline 2.1 asks you to "turn on your
  back-end service!". So uptime is a standing obligation, and each update's
  review is a fresh exposure. That is the case for rolling deploys (§1).
- **M3. The Oracle recovery path fails together with the thing it recovers.**
  If A1 capacity is short, you can't re-create a reclaimed or terminated
  instance. And when an allowance cut prompts people to rebuild, everyone
  rebuilds at once.
- **M4. Electricity.** An owned box isn't $0 in Massachusetts. At 30.49 ¢/kWh,
  a 20 W laptop costs about $4.45/mo, two-thirds of Contabo US. Nobody has
  measured the laptop's draw.
- **M5. Acceptable-use terms for serving from home.** Comcast's residential
  AUP (updated 2021-02-01) prohibits "dedicated, stand-alone equipment or
  servers from the Premises that provide network content or any other services
  to anyone outside of your Premises local area network". It also prohibits
  programs that do so "except for your personal and non-commercial residential
  use". If the laptop is on campus, Northeastern's Policy 700 (revised
  2026-06-22) requires "explicit written authorization of the Office of the
  Provost or its designee" for "hosting non-university activities". Which of
  these applies depends on where the laptop is, and that is unknown from here.
  A tunnel hides the traffic pattern, not the obligation. This is a real point
  for moving to a datacentre, and the plan never used it.
- **M6. A cloud host is a new processor for the privacy policy.**
  `docs/privacy-policy.md` §2.1(a) names Cloudflare and says the server stores
  nothing. Today the origin is the developer's own machine. On Oracle or
  Contabo, a third party runs the process that handles every coordinate. The
  policy's own §8 lists "a move off the Cloudflare tunnel" as a trigger for
  rewriting it, but not a change of host behind the tunnel, and that is the
  gap.
  **Contabo is Contabo GmbH, Munich** (its legal notice), wherever the server
  sits. `docs/release-plan.md` decision 3 rests on "US-only at launch removes
  GDPR from scope", so an EU-established processor, or an EU region, reopens
  that premise. This is not legal advice, only a flag that the decision was
  made without this fact.
- **M7. PAYG is a second irreversible decision.** It is one-way, its budgets
  don't cap spending, and it turns future cuts into bills (C3). The findings
  present it as a free upgrade to "consider".
- **M8. An account-level idle rule exists** (C10).
- **M9. No support for Always-Free-only accounts** (C18).
- **M10. The serving data has one real copy.** The five parquets are
  gitignored and live on the Mac. Two origins make two more copies as a side
  effect.
- **M11. On one box, every deploy is an outage.** A restart costs the graph
  load: 49.9 s on the M2, and more on A1. That is harmless on an ordinary day
  and bad during the review of an update. Two gated connectors remove it.
- **M12. The monitor only sees the replica that answers.** With two origins,
  the public health check tells you *a* box is up. Keep one per-box check
  (for example, a cron job on each box that emails if its local
  `/api/health` fails). UptimeRobot's free plan is described as "Good for
  hobby and non-profit projects". That fits a free app, but note it.
- **M13. `/api/health` reports no build identity.** It returns `status`,
  `nodes` and `routing_slots` only (`server/app.py:397-399`). With two origins
  serving different users, it should also report the git commit and a data
  fingerprint, so a keyword monitor can catch a box that is live but stale.
  This is a small code change, proposed and not made.
- **M14. A laptop that is always on is always charging.** If the vendor's
  utility offers a charge limit, turn it on. Batteries held at 100% around the
  clock are the usual way an always-on laptop fails physically.

---

## 4. What can't be known from here

Each of these needs an account, a purchase, the hardware, or the owner. None
is guessed at above.

| question | what it needs |
|---|---|
| Is A1 capacity available now in any US region? | An Oracle account, and creating one fixes the region permanently for the person (C16) |
| Does PAYG exempt an A1 instance from idle reclaim? | Oracle saying so in writing. Always-Free-only accounts can't open a support request to ask |
| What makes an *account* idle under the 30-day rule? | Oracle. It isn't defined anywhere public |
| If the monitoring plugin reports nothing, is the memory criterion skipped? | The box, plus Oracle |
| Real A1 figures for this workload: RSS, load time, route latency, and `/api/loop` | The box. C1 argues it doesn't change the verdict |
| Contabo noisy-neighbour effect on route latency | A box. A month-to-month $7.90 test, with 4 weeks' cancellation notice on post-paid, is the cheapest way to find out |
| Pi 5 or mini PC performance on this workload | The hardware. Moot, because §1 ranks both below the laptop the owner already has |
| Is auto-renew on for `jameskouvlis.com`? | The owner's GoDaddy account. Minutes |
| Where does the laptop sit (which ISP or campus network), what does it draw, and has it ever served the NE build? | The owner. Minutes |
| Will Oracle accept the owner's card? | Sign-up |

---

## 5. Proposed edits, not made

Per the brief, `server/DEPLOY-oracle.md` and the findings doc are untouched.
The owner decides.

**`server/DEPLOY-oracle.md`**

- **Before you start (line 31):** add the domain-expiry check (M1). Replace
  "A payment card" with Oracle's accepted card types (C15).
- **The one irreversible decision (lines 40-45) and Part 1:** drop the latency
  rationale (C8). Say that the choice is permanent per person (C16). Recommend
  a 3-AD US region, and note the April 2026 Chicago report (C4).
- **Part 2, capacity (lines 144-146):** give Frankfurt as about +81 ms per
  request, and Contabo as $6.58/mo (24-month prepaid) or $7.90/mo in
  US-Central (C5, C8).
- **Parts 9.4 and 10, and troubleshooting line 513:** replace "never two
  connectors" with a gated second connector (§1), and add the rolling-deploy
  order.
- **Troubleshooting line 507:** 530 means no connector. Add a separate 502 row
  for "API down or still loading" (C17).
- **Part 12:** add the account idle rule (C10). Change the mailbox's warning
  window to about 13 days (C9). Note that memory optimisation can re-arm
  reclaim (C2).
- **Line 527:** cite the A1 over-limit rule ("disabled and then deleted after
  30 days") instead of the trial-resources sentence (C11).
- **Rollback (lines 491-499):** keep the laptop on the same commit and data
  indefinitely, or better, run it as the second connector (C13).

**`docs/hosting-options-findings.md`**

- Lines 33, 182 and 236: about 13 days of email warning (C9).
- Lines 166 and 535: the account idle rule (C10).
- Lines 373-374: remove the multiple-tenancy remedy (C16).
- Lines 388-398, 415 and 564: the tunnel latency correction (C8).
- Lines 240-252, 547-549 and 579: PAYG is one-way, and budgets don't cap (C3).
- Lines 37, 566-570 and 580: the US Contabo price (C5).
- Line 583: the laptop has 16 GB or more (C6).
- Lines 684-686: gated connectors (C12).
- Line 678: drop `TimeoutStartSec` (C21).

**Elsewhere**

- `server/DEPLOY.md` §7: the connector task should wait for `/api/health`
  before attaching.
- `docs/privacy-policy.md` §2.1(a): name the hosting provider(s) (M6).
- `docs/release-plan.md` §7: the Contabo price (C5), and the domain (M1).
- `server/app.py:397`: commit and data fingerprint in `/api/health` (M13).

(`docs/README.md` now indexes this file. That is the only existing file this
review changed.)

**Order of work, if accepted**

1. Renew the domain (today).
2. Apply `DEPLOY.md` §7 with the connector gate. Do the reboot test and a
   `kill` test. Point a monitor at `/api/health`.
3. Push `main`, and put the NE parquets on the laptop.
4. Sign up with Oracle whenever convenient. Per `docs/release-plan.md` §4, it
   gates nothing.
5. Add the Oracle box as the second connector.
6. If the 14-day stopping rule runs out, decide whether the second connector
   is worth $6.58–7.90/mo at Contabo, or whether the laptop alone is enough
   for now.

---

## Sources

All read 2026-09-28 unless marked.

**Oracle**

- [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm): allowance, idle criteria, capacity guidance, the "doesn't charge… after you upgrade" wording.
- [Free Tier overview](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm): card requirement, the A1 over-limit "disabled and then deleted after 30 days" rule.
- [Free Tier FAQ](https://www.oracle.com/cloud/free/faq/) (browser pane): one account per person, the 30-day account idle rule, card types, no support, no downgrade from paid, capacity.
- [Budgets overview](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm): "soft limits", evaluated every 24 hours.
- [Compute metrics](https://docs.oracle.com/en-us/iaas/Content/Compute/References/computemetrics.htm): `MemoryUtilization` definition and plugin requirement.
- [Regions](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm): availability domains per region.
- [Price list](https://www.oracle.com/cloud/price-list/) (browser pane): A1 at $0.01/OCPU-hr and $0.0015/GB-hr.

**Cloudflare**

- [Tunnel availability and replicas](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-availability/)
- [Cloudflare Tunnel overview](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)
- [Registrar](https://www.cloudflare.com/products/registrar/)

**Providers**

- Contabo: [Core VPS](https://contabo.com/en-us/vps/), the [Cloud VPS 4 configurator](https://contabo.com/en-us/vps/cloud-vps-core-4) (term prices, setup fee, region surcharges, prepaid "due today"), [Performance VPS](https://contabo.com/en-us/vps-performance), and the [legal notice](https://contabo.com/en/legal/impressum/). All in the browser pane, non-essential cookies denied.
- [OVHcloud US VPS](https://us.ovhcloud.com/vps/)
- [Hetzner price JSON](https://www.hetzner.com/_resources/app/data/bench/cloud_data.json)

**Hardware**

- [Raspberry Pi 5 product page](https://www.raspberrypi.com/products/raspberry-pi-5/) (16 GB at $305)
- [Raspberry Pi, "More memory-driven price rises"](https://www.raspberrypi.com/news/more-memory-driven-price-rises/) (2026-02-02)
- [Adafruit, Pi 5 8 GB](https://www.adafruit.com/product/5813) ($200)
- [Beelink EQ14](https://www.bee-link.com/products/beelink-eq14-n150) ($385)

**Apple**

- [App Review](https://developer.apple.com/distribute/app-review/) (90% within 24 hours)
- [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) (2.1, and the removal sentence)

**Other**

- [EIA Electric Power Monthly, Table 5.6.A](https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_6_a) (July 2026 data)
- [Verisign RDAP, jameskouvlis.com](https://rdap.verisign.com/com/v1/domain/jameskouvlis.com)
- [GoDaddy .com pricing](https://www.godaddy.com/tlds/com-domain) (browser pane)
- [Comcast AUP](https://www.xfinity.com/corporate/customers/policies/highspeedinternetaup)
- [Northeastern Policy 700](https://policies.northeastern.edu/policy700)
- [UptimeRobot pricing](https://uptimerobot.com/pricing/)

**Secondary, used only where marked**

- [CNELECAR, 2026-08-05](https://www.cnelecar.com/blog/oracle-always-free-arm-limits-cut-2026/): the enforcement email's text and timing.
- [LowEndTalk 218183](https://lowendtalk.com/discussion/218183/oracle-free-tier-being-reduced) (June 2026): PAYG tenancies expecting bills for the excess.
- [LowEndTalk 215831](https://lowendtalk.com/discussion/215831/oracle-free-tier-out-of-capacity-in-chicago-region-any-success-stories-with-scripts-lately) (2026-04-01): Chicago capacity. Read through a search summary, not in full.
- [Electronics Weekly, 2026-04-06](https://www.electronicsweekly.com/news/products/raspberry-pi-development/raspberrypi-price-hikes-2026-04/): the April Pi rise.
