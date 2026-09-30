# Hosting — one last independent review before anything is provisioned

**Status: question, not answer. Written 2026-09-28 against `main` at `3402298`.
Nothing has been provisioned, signed up for or purchased. No Oracle account
exists. No hosting file has been edited.** The answer goes in a new file,
`docs/hosting-independent-review.md`.

## What is being asked

Every hosting document in this repo came from sessions inside this project, and
each built on the one before it:

- `docs/hosting-options-brief.md`: the original question
- `docs/hosting-options-findings.md` (2026-09-01, 1,048 lines): the verdict and the research
- `docs/hosting-status-2026-09.md` (2026-09-19): a re-check that said the verdict stands
- `server/DEPLOY-oracle.md` (2026-09-19, 547 lines): the step-by-step runbook

They agree with each other because each one started from the previous one's
conclusion. The owner wants **one review from outside that chain** before the
irreversible step (choosing an Oracle home region at sign-up) is taken:

1. **Is moving off the laptop the right move at all?**
2. **Is the Oracle plan everything it appears to be?** What is overstated,
   understated or missing?
3. **Is there a better option?** That includes options the earlier documents
   never considered.

Treat the four documents above as **the plan under review, not as evidence.**
Read them to learn what is claimed, then decide for yourself which claims hold.

## The plan, as it stands

Move the routing API from a Windows laptop to **Oracle Cloud Always Free**, as
one `VM.Standard.A1.Flex` (Ampere ARM) instance with **2 OCPU and 8 GB**,
Ubuntu 24.04, home region **`us-chicago-1`**, at **$0/mo**. It runs one
`waitress` process under systemd, with `cloudflared` under systemd, and reuses
the existing named Cloudflare tunnel `scenic`. The documented fallback is
**Contabo Cloud VPS 4 at ~€5.50/mo**. Rollback: start `cloudflared` on the
laptop again.

The four arguments the plan rests on (findings, "So why is this still the
recommendation?"):

- **Portable:** three parquets, a `git clone`, eleven pinned wheels, one unit file.
- **The hostname never moves:** it is a tunnel, so there is no DNS change and no App Review.
- **Exit price is cheap:** Contabo.
- **Oracle's idle reclaim can't fire:** reclaim needs CPU, network **and** memory
  all under 20% for 7 days, and 4.4 GB is 55% of 8 GB. This is also why the plan
  deliberately provisions *less* than the 12 GB allowed.

## Facts you can rely on (measured, don't re-measure)

These were measured with replicates. They describe the workload, not a verdict.

| fact | value | source |
|---|---|---|
| Peak RSS of the serving process, New England graph | **4.39 GB** (range 4.30–4.41), ~4.8 GB once loop caches warm | `docs/hosting-status-2026-09.md` §1, on an Apple M2 |
| Earlier reading of the same figure | 3.53 GB, now known to be an under-read | same |
| Graph load time at startup | **49.9 s** on the M2 | same |
| One route, Boston → Augusta ME, 262 km | 153 ms first call; fastest arm 104 ms warm; scenic arm 367 ms | same |
| Graph size | 794,685 nodes (801,719 routing slots), 998,252 edges | `/api/health`, `server/app.py:397` |
| Data to ship | ~382 MB across five parquets from `data/processed-ne/` (gitignored) | `server/DEPLOY-oracle.md` Part 6 |
| Concurrency | `waitress` with `threads=4` (`server/serve.py:44`), but scipy's Dijkstra holds the GIL: 4 concurrent routes took 0.482 s against 0.519 s serial | `docs/hosting-options-findings.md`, "Early-stage capacity" |
| The app's API URL | `SundayDriveAPIBaseURL: https://api.jameskouvlis.com` is baked into the iOS build (`ios/project.yml:63`) | code |
| Current state | `https://api.jameskouvlis.com/api/health` returned **HTTP 530** on 2026-09-28: the tunnel answers with no origin behind it, because the laptop is off | curl |

## Claims that are *inferred*, and are the ones to attack

- **"A1 is about 2–2.5x slower than an M2."** Taken from published single-core
  comparisons, never measured on this workload. It sets every A1 latency and
  load-time figure in the runbook.
- **"Idle reclaim can't fire because memory is 55%."** This depends on the Oracle
  Cloud Agent actually reporting memory, and on Oracle applying the three-way AND
  as written. The findings list both as unverified ("What I could not
  establish", items 3–5).
- **"Pay As You Go exempts you from reclaim and costs $0."** Reported by users;
  Oracle's documentation does not say it.
- **"A1 capacity is obtainable in `us-chicago-1`."** Can't be checked without an
  account. The newest public report is from April 2026. The home region is
  permanent.
- **"Contabo is a fine exit."** A promotional 24-month price, on hosts that are
  widely reported as oversubscribed. Does that matter for a memory-resident,
  single-threaded workload?
- **"The laptop is not an always-on host."** The owner says it was simply
  switched off and has never misbehaved. Hardening it (`server/DEPLOY.md` §7:
  Task Scheduler pointed at `python.exe` / `cloudflared.exe` directly, not at
  `server/start-windows.bat`, which detaches and exits 0) was rated an
  acceptable launch option by `docs/release-plan.md` §7 and never chosen or
  rejected.
- **The "Disqualified" table** (findings, "Disqualified, with reasons"). It
  looked at mainstream free tiers and two paid providers. It did **not** look at
  owned hardware (a mini PC or a Raspberry Pi 5 8 GB at home, run behind the same
  tunnel), other budget US VPS providers, or changing the workload so it fits a
  smaller or cheaper box (4.4 GB is a property of the current code, not a law).
  Whether any of those beats the plan is for you to find out. They are examples,
  not a whitelist.

## What actually has to be true (the requirement)

The project's goal since 2026-09-19 is **App Store release** of a single-region
(New England) iOS driving app with a handful of users at first. The hosting
requirements that follow from that:

- **The API answers whenever an App Review reviewer tries it.** That can be days
  after submission, at any hour. A 530 is close to an automatic Guideline 2.1
  rejection.
- **Reroutes mid-drive answer in a few seconds.**
- **Cost as close to $0 as is sensible.** The owner is a student; $99/yr Apple
  membership is already the main spend.
- **The hostname cannot change** without a new build and a new App Review.
- Route requests carry **coordinates in the query string** through Cloudflare,
  which may affect which hosts or tunnels are acceptable for privacy.

If you think one of these requirements is wrong or missing, say so. That is in
scope.

## Traps

1. **Anchoring on the earlier documents.** This whole review exists because they
   agree with each other. Do the reverse of what they did: form the option set
   and the criteria first, *then* read what they claimed. But **don't re-measure
   the workload numbers** above. Those were measured carefully (three
   interleaved replicates), and redoing them is a day spent confirming what is
   known. Attack the inferences, not the measurements.
2. **Capping the answer to "which cloud host".** Valid verdicts include "don't
   move, harden the laptop", "buy a $100 box", "pay €5/mo and skip the Oracle
   lottery", and "shrink the working set first". A review that only compares
   VPS providers has already accepted the plan's framing.
3. **Blog and aggregator prices.** Provider prices moved in June 2026 (Oracle
   halved its allowance on 15 June and then terminated over-limit instances on
   18 Aug; Hetzner US roughly tripled). Every price or allowance in your
   verdict needs a primary source and the date you read it. Retrieval quirks:
   `oracle.com` pages and PDFs return 403 to WebFetch but load in the browser
   pane; `docs.oracle.com` serves both. Hetzner's plan pages show no prices; the
   live data is in `hetzner.com/_resources/app/data/bench/cloud_data.json`.
   `lowendtalk.com` 403s WebFetch but renders in the browser;
   `community.oracle.com` renders no post bodies at all.
4. **Signing up, entering a card, or buying anything.** Don't. That includes
   free trials to "check capacity". If a question can only be answered with an
   account, say so and leave it to the owner.
5. **Diagnosing the laptop.** The 530 is the laptop being off. The owner
   confirmed it has never faulted. Don't spend time on it.
6. **Naming.** The app is **Sunday Drive** now (renamed twice in September), and
   env vars are `SUNDAYDRIVE_*`. The repo, the GitHub URL and the tunnel keep
   the old name **Scenic** on purpose. Don't "fix" that.

## Done looks like

1. `docs/hosting-independent-review.md`, opening with a **verdict** in a few
   lines: proceed with the Oracle plan as written, proceed with named changes,
   or replace it with something specific.
2. A **ranked option table** covering at least: Oracle as planned, laptop
   hardened, one owned-hardware option, and the best paid option you found. For
   each, give monthly and one-off cost (with source and date), the risk that
   would actually bite, and how it meets the App Review requirement.
3. **A claim-by-claim list** of the plan's inferred claims above (and any others
   you find): held, broken, or unverifiable, with the evidence.
4. **Anything the plan is missing:** a failure mode, cost or obligation none of
   the four documents mention.
5. **What can't be determined without an account, a purchase or the hardware,**
   stated plainly rather than guessed. If the honest answer to a question is "it
   cannot be known from here", that counts as an answer.

Don't edit `server/DEPLOY-oracle.md` or the findings. If your verdict changes
them, list the edits in your document and the owner will decide.
