# Re-verify the hosting decision — the box was sized before A\* landed

**Status: scoped 2026-09-19 against `main` at `2d6fbc0`, nothing changed and
nothing may be migrated.** No config, no deploy, no account. The deliverable is
a short status document — see Trap 1.

The research is done and is **not** to be redone:

```sh
docs/hosting-options-findings.md   # 1,028 lines: Oracle Always Free, with a runbook
docs/hosting-options-brief.md      # the measured requirements it answers
server/DEPLOY.md                   # the incumbent topology
```

That document's verdict — **move to Oracle Always Free, `us-chicago-1`, 8 GB** —
is not being reopened. What this task does is check the three things under it
that are known to move, plus one measurement that has certainly gone stale.

---

## Why now: the number that sized the box predates the code

`hosting-options-findings.md` sizes the instance on a **measured 3.53 GB peak
RSS** (3.85 GB after touching the access layers), taken 2026-08-31 against `main`
at `efbbd28`, on the New England build.

**A\* landed on 2026-09-19** (`403675c`, "Stop settling all of New England to
answer the fastest arm") and it allocates memory the measurement never saw.
`pipeline/router.py`:

- `ALT_LANDMARKS = 16` (`:323`).
- `_build_alt_tables()` is called from `_build_directed` (`:1030`), **at load
  time, every process**.
- Its docstring (`:1033-1053`) states what it builds and what it costs:

  > Travel time from and to `ALT_LANDMARKS` landmarks … **After
  > `_apply_turn_restrictions`, never before.** That call grows `self.n` from
  > 794,685 to 801,719 … **32 Dijkstras, measured at 9.5 s on New England.**

So two tables, each 16 × 801,719, built per process at start-up. **If they are
float64 — which is what `scipy.sparse.csgraph.dijkstra` returns — that is about
205 MB**, and the start-up cost rises by ~9.5 s.

*Flagged as arithmetic, not a measurement.* The dtype was not confirmed and the
tables may be stored narrower. **What would settle it: load a `Router` on
`data/processed-ne` and read the peak RSS, the way the original measurement did.**
That is the first job here.

**Why it matters more than 205 MB sounds.** The findings document's core argument
is counter-intuitive and turns on a *percentage*:

> idle reclaim requires CPU, network **and** memory all under 20% over 7 days,
> and a single-user API is idle on the first two — so **memory is the only thing
> keeping the box alive**.

3.53 GB is 44% of a deliberately-small 8 GB, comfortably above the 20% floor;
3.53 GB would have been 14.7% of the old 24 GB and **would have been reclaimed**.
Adding ~205 MB moves the number the right way. **But the recommendation to
provision *less* RAM than Oracle allows is derived from this figure, so the
figure should be current before anyone acts on it.**

## The three dated facts, and why they are the task

`scenic-hosting-decision` in the project memory carries an explicit instruction:
*don't redo this research; do check the dated provider facts, because both moved
in June 2026 and could move again.* All three are now **eighteen days old**:

| Fact, as of 2026-09-01 | Why it could have moved |
| --- | --- |
| Always Free A1 is **2 OCPU / 12 GB**, halved on 15 June 2026 **with no announcement** | It was halved once, silently. The entitlement is not contractual |
| Oracle **terminated** over-entitlement instances on 18 Aug 2026, warning by email only | Enforcement practice, not policy — the kind of thing that changes without a document changing |
| The paid exit is **Contabo ~€5.50/mo** (4 vCPU / 8 GB, US); Hetzner US CPX31 went ~€21 → ~€62/mo in June 2026 | Hetzner moved 3× in one month. The exit price is what bounds the downside of the whole bet |

A fourth is worth confirming because it is the **irreversible** part:
**A1 capacity in `us-chicago-1`**. The home region is permanent per account and
A1 is scarce in exactly the US regions. The findings document picked Chicago on a
measured **+12 ms RTT from Boston** (against +81 ms for Frankfurt) and called the
region choice "an irreversible bet".

## The operational state, for the status half

- **The API is down.** `https://api.jameskouvlis.com/api/health` → **HTTP 530**,
  checked again while writing this. 530 with Cloudflare 1033 means the tunnel is
  answering and the origin is absent.
- **This is almost certainly the laptop being off, and it must not be
  re-diagnosed.** The owner has said the machine had simply been switched off and
  has never actually misbehaved, so 530 is the correct response to an absent
  origin. It is also unreachable from here. See Trap 4.
- **`DEPLOY.md` §7's hardening cannot deliver what it promises, and that *is*
  settled** — `hosting-options-findings.md:255-273` shows why:
  `server/start-windows.bat` launches both halves with `start`, which detaches
  them and returns **0** immediately, so a Task Scheduler task pointed at it sees
  success and its restart-on-failure never fires. **Whether the hardening was
  ever applied to the actual machine is unknown and unknowable from here.**
- **Release relevance, from `docs/release-plan.md` §7** (unmerged, on
  `claude/release-plan-sequence`): hosting is **decoupled** from submission —
  `ScenicAPIBaseURL` names a hostname and the Cloudflare tunnel is the switch, so
  migrating needs no new build and no App Review. What *is* on the critical path
  is that a reviewer who opens the app while the API is down gets an error, which
  is a **guideline 2.1 rejection**. The requirement is reliability *during
  review*, not migration.

---

## Traps

**1. Do not migrate anything, and do not create an account.** No credentials
exist here, and the home region is a permanent choice. This task writes one
document.

**2. Do not redo the 1,028-line research.** Its verdict, its runbook, its ARM64
wheel analysis and its throughput ceiling all stand and are not in question.
Re-verify the four dated facts above, re-measure the one stale number, and say
whether the verdict still holds. A session that re-derives why Oracle beat
Hetzner has spent its budget on a settled question.

**3. Two hosts block automated fetches, and the workarounds are known.**
`oracle.com` and its policy PDFs return **403** to programmatic fetches while
`docs.oracle.com` serves normally. Hetzner's plan tables render on the per-line
pages (`/cloud/cost-optimized/`, `/cloud/regular-performance/`) but **not** on
`/cloud/`. Budget for this rather than concluding a fact is unobtainable — and
if something genuinely cannot be retrieved, **say so rather than carrying the
2026-09-01 figure forward as current.** That substitution is the one failure that
would make the refresh worthless.

**4. Do not diagnose the laptop.** It is a Windows machine at the owner's home,
not reachable from this session, and the 530 has a known and boring cause. The
one thing worth reporting is whether the API is up or down at the moment you
check, and what that implies for a review window.

**5. Re-measuring RSS needs the main checkout, and may fight another session.**
`data/` is gitignored and exists **only** in the main checkout, never in a
worktree — set `SCENIC_DATA` explicitly. `server/app.py` hard-codes port 5057 and
another session on this machine may already hold it; you do not need to serve to
measure, so load a `Router` directly rather than starting the server.

**6. Provisioning *less* RAM than allowed is deliberate, not a mistake.** If the
re-measurement tempts a "we should take all 12 GB" conclusion, re-read the idle
reclaim argument first — more RAM lowers the utilisation percentage and moves the
box *towards* reclamation.

---

## Done looks like

1. **One short document** — `docs/hosting-status-2026-09.md` or similar,
   deliberately not this brief's filename — indexed in `docs/README.md`.
2. **Peak RSS and load time re-measured** on current `main` against
   `data/processed-ne`, stated beside the 3.53 GB / 2026-08-31 figures so the
   delta is visible, with the ALT tables' actual contribution and dtype named.
3. **The four dated facts re-checked** — A1 entitlement, termination practice,
   the Contabo/Hetzner exit price, and `us-chicago-1` capacity — each either
   confirmed with its source and date, corrected, or **explicitly marked
   unretrievable**.
4. **A one-line verdict**: does "move to Oracle Always Free, `us-chicago-1`,
   8 GB" still stand, and if not, what changed.
5. **The status half answered plainly** — is the API up right now, and what is
   the cheapest thing that makes it reliable through an App Review window.
   Note that the two options (keep the laptop up, or migrate) are the owner's
   call and `release-plan.md` §7 rates both acceptable; **recommend, do not
   choose.**
6. **An honest-answer escape hatch.** "Nothing has moved and the verdict stands"
   is a complete and welcome answer — say it in one line rather than padding it.
   So is "this could not be retrieved from this machine", for any individual
   fact.
