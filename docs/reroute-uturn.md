# At most one U-turn per departure

**Status: built and replayed against every recorded reroute; not yet driven.**
Server: `pipeline/router.py` (`turnaround_at`, `Router.route(keep_ahead=)`),
`server/app.py` (`declined_uturn`). App: `NavigationModel.declinedUTurn`.
Replay: `tools/replay_uturn.py`. One number is a decision for you, not a
measurement: the 15-minute cap (see "What going on ahead costs").

## The goal

When a driver leaves the route, the first reroute may tell them to turn
around. That is often right. **If they ignore it and keep going, the next
reroute goes on ahead.** At most one U-turn per departure, and a "switch to
fastest" does not reset that.

## Why it happened

A reroute is computed from the junction ahead of the car (the heading is used
correctly; `Router._snap`, `_forward_end`), but nothing constrained the
search's first move. When the best way to the destination was back down the
road, the route said so: "Make a U-turn". The driver kept going, went off the
new line, and the app asked again from a few hundred metres further on. That
is the same question, and it usually got the same answer. Nothing recorded
that the last answer was a U-turn the driver had refused, and the server is
stateless, so only the app can know that.

Backing off would not have helped: `rerouteCooldown` only changes *when* the
next request goes. Across the five U-turns of `drive-2026-10-06-122558` seq
15–19, the cooldown grew and every answer was still a U-turn.

## The design

**The server says when a route turns the driver around, and where.** Every
`/api/route` reply that was asked with a heading now carries
`turns_around` (bool) and `turnaround_m`: how far along the route it starts
to turn them back, or null. It is judged by geometry and not by the wording
(next section).

**The app keeps a declined-U-turn state** (`NavigationModel.declinedUTurn`):

- **Set** when a reroute, for any reason, leaves a route whose `turnaround_m`
  the driver never drove `declinedUTurnProgressMeters` (100 m) past.
  "Past the turnaround" and not "along the route", because a route can lead
  the driver ahead for hundreds of metres before it turns them around (the
  step-1 form below). Counting progress from where they joined would have
  forgiven a driver who followed those metres and then carried on.
- **Sent** as `declined_uturn=1` on every reroute while set, through its own
  fetcher seam (`fetchRouteKeepingAhead`), so no existing stub changed.
- **Kept across "switch to fastest".** `switchToFastest` resets the backoff
  but leaves this state alone, and does not restore it when the switch
  fails. Declining the U-turn was not staked on that request.
- **Cleared** in `trackFollowing` once the driver is on a route (within
  `joinConfirmMeters`, not running backwards) and has driven 100 m past its
  turnaround. For a route that goes on ahead, that means 100 m past where
  they joined it. From there a new departure starts fresh, and its first
  U-turn is offered again.

**The server, asked with `declined_uturn=1`, keeps the route ahead.**
`Router.route(keep_ahead=True)` first finds the cheapest route as always. Only
if that route turns the driver around does it search again, with every road
through the strip behind the driver closed in the direction that leads back
over it (`_turn_back_slots`). That is the same test `turns_around` applies,
so the route it finds cannot turn the driver around: not at the start, not
one junction on, and not by going round the block. It hands back the
turnaround anyway in two cases, and that route still says `turns_around`, so
the app keeps the driver's refusal:

- there is no way ahead (a dead end or a cul-de-sac), or
- going on would cost more than `TURN_BACK_CAP_MIN` (15) extra minutes.

The change is at the start of the search only. Snapping, the unpaved
penalty and the closures are untouched. `route()`'s A*/Dijkstra choice moved
into `_cheapest` so both searches use it.

**Compatibility.** The server deploys separately from the app.

- An old client never sends `declined_uturn`, so every route it gets is
  today's route. The reply gains two properties, which it ignores
  (`test_a_client_that_never_sends_the_flag_gets_todays_route`).
- A new app against the old server never gets `turnaround_m`, so it never
  declines anything and sends exactly what it sends today
  (`test_a_backend_that_never_says_a_route_turns_around_changes_nothing`).
- **The loop rejoin (`via`) does not honour it.** That path already drops the
  heading (`server/app.py`), so it has no "behind" to keep the route out of. It
  accepts the parameter and ignores it without error. The app never sends it
  there anyway, because a rejoin reply carries no `turnaround_m`, so nothing on
  that path can be declined.

The trace records both halves for the next drive: `req_declined_uturn` on a
route record whose request carried the flag, and `turnaround_m` on any route
that turns the driver around.

## "Turns you around", measured

A route turns the driver around if, **within its first 1,000 m, it drives
through the strip behind them, 1,000 m deep and 40 m either side of the line
they are travelling on, heading at least 120° from their course**
(`TURN_BACK_WITHIN_M`, `TURN_BACK_STRIP_M`, `TURN_BACK_DEGREES`;
`router._behind_strip`, `_turning_back`, `turnaround_at`).

Why geometry and not the words, nor the first step only (the brief's Trap 1).
The recorded drives express the same move three ways:

| Wording | Where it turns you around |
|---|---|
| "Make a U-turn on X" | at the start, back past the car |
| "Head west on X", then "Make a U-turn to stay on X" | 300–600 m on, back down the other carriageway |
| "Sharp right onto Y" (`drive-2026-10-06-122558` seq 11) | 213 m on, onto a road that runs back past the car |

A rule that read the words would miss the third. A rule that read only step 0
would miss the second. A rule that only banned reversing the start edge would
move the U-turn to the next junction or round the block. The strip catches
all of these, and the search ban closes all of them, because both are the
same test.

Why *behind* and not *near*. A plain "comes back within D m of the request
point" fails on a road that simply curves through 180° ahead. Seq 4 of the
same trace does that 95 m to the side of a car doing nothing but driving on.
A turnaround comes back over the road already driven.

The numbers, over the 26 reroutes of the 2026-10-06 drives that sent a
heading:

- **The 13 turnarounds** came back within **0–13 m** of the line behind the
  car, first entering the strip **16–632 m** along. 632 m is the step-1 form,
  in `drive-2026-10-06-164801` seq 1. Two rebuilt 2026-08 requests of the
  same form came back 602 and 727 m along.
- **Of the other 13**, the nearest that line any came while heading back was
  **95 m**.
- So **40 m** sits in a gap from 13 to 95 m. It covers GPS error and a divided
  road's other carriageway (10–30 m), and **1,000 m** covers the latest
  return with room to spare.
- **120°** means "going back". A road crossing behind the car at a right angle
  does not count. At 90° the same 13 are caught plus one more:
  `drive-2026-10-06-185940` seq 1, which opens with an ordinary right turn.

The strip is 1,000 m deep, not just a few hundred, because a shallower one let
the search find a way round it. With a 300 m strip, seq 12's "ahead" route
looped 1.3 km round three roads and came back down the car's road 775 m behind
it, which is the same instruction in different words. The 1,000 m strip
closes that for +1.1 min instead of +0.6.

## Replay

Every request asked again of a local router built from `data/processed-ne`,
from its recorded `req_lat`/`req_lon`/`req_heading`/`req_pref` and the drive's
`dest`/`weights`, on the drive's own date. Requests without the flag reproduce
the route that was actually sent to 0.1 km and 0.1 min in every row, so the
replay is faithful.

The flag column is the app's rule, simulated from the recorded fixes: was
there a reroute away from a turnaround the driver had not driven 100 m past?
The replay can only ask each request from where the car really was. Under the
rule the driver would have been sent different routes, and the replay cannot
know where they would then have driven.

**sent / now**: whether the route sent then, and the route the new rule
returns, turn the driver around (U), by the definition above. **Δ** is the
new route against the route that was actually sent.

| Trace | Seq | Reason | Sent | Flag | Now | Δ km | Δ min | Note |
|---|---|---|---|---|---|---|---|---|
| `drive-2026-10-06-122558` | 1 | offroute | U | | U | 0.0 | 0.0 | first of its departure: allowed |
| | 2 | offroute | – | set | – | 0.0 | 0.0 | was already ahead |
| | 11 | offroute | U | | U | 0.0 | 0.0 | the "Sharp right" form; first: allowed |
| | 12 | offroute | U | set | – | +0.8 | +1.1 | |
| | 13 | offroute | U | set | **U** | 0.0 | 0.0 | **no way ahead**: the road is a dead end |
| | 15 | offroute | U | | U | 0.0 | 0.0 | first of its departure: allowed |
| | 16 | offroute | U | set | – | +1.2 | +1.7 | |
| | 17 | **fastest** | U | set | – | +0.6 | +0.9 | the driver's own switch |
| | 18 | offroute | U | set | – | +0.3 | +0.5 | |
| | 19 | offroute | U | set | – | +3.3 | +0.5 | faster roads |
| | 20 | offroute | – | set | – | 0.0 | 0.0 | was already ahead |
| `drive-2026-10-06-192759` | 4 | offroute | U | | U | 0.0 | 0.0 | first: allowed |
| | 5 | offroute | U | set | – | 0.0 | +0.2 | |
| | 6 | offroute | – | | | | | sent no heading; not replayable (it went on ahead) |
| `drive-2026-10-06-161415` | 1 | offroute | U | | U | 0.0 | 0.0 | single: allowed |
| `drive-2026-10-06-164801` | 1 | offroute | U | | U | 0.0 | 0.0 | single, step-1 form: allowed |

Before, counting by geometry, the 2026-10-06 runs of consecutive turnarounds
were 1, 3 (seq 11–13, where 11 is the "Sharp right"), 5, 1, 1 and 2. After,
no two replies in a row turn the driver around. Every departure gets one
U-turn, except 11–13, which gets two (11 and 13), because 13 is on a dead end
and the only way out is back. Every other declined U-turn now gets a route
ahead, for +0.2 to +1.7 min.

Indicative only: the step-1 form in the August traces. These requests were
rebuilt from the last fix, and the server they went to may not have used a
heading, so Δ is against a different router and is omitted.

| Trace | Seq | Sent | Flag | Now |
|---|---|---|---|---|
| `drive-2026-08-25-202122` | 4 | U | | U (first: allowed) |
| | 5 | U | set | – |
| `drive-2026-08-22-222623` | 3 | U | | – (the replayed route is already ahead) |
| | 4, 5, 6 | U | set | – |

## What going on ahead costs

The trade-off the brief's Trap 6 asks for. "Ahead" is measured against the
turnaround it replaces, for the same request.

**Every traced turnaround, if it had been declined:**

| Request | Ahead: Δ km | Δ min |
|---|---|---|
| `122558` 1 | +0.4 | +0.6 |
| `122558` 11 | +1.3 | +1.7 |
| `122558` 12 | +0.9 | +1.1 |
| `122558` 13 | no way ahead | |
| `122558` 15 | +1.5 | +2.0 |
| `122558` 16 | +1.2 | +1.7 |
| `122558` 17 | +0.6 | +0.9 |
| `122558` 18 | +0.3 | +0.5 |
| `122558` 19 | +3.2 | +0.5 |
| `161415` 1 | +0.5 | +1.0 |
| `164801` 1 | +8.0 | **+11.2** |
| `192759` 4 | +0.2 | +0.4 |
| `192759` 5 | 0.0 | +0.2 |

`164801` seq 1 is a divided road, where the U-turn is 300 m on, and is the one
expensive case. It was a single U-turn, so the rule leaves it alone. It would
only cost +11.2 min if the driver declined it.

**Random departures** (`tools/replay_uturn.py --sample 400`, seed 20261006):
400 points on primary-to-residential roads, heading along the road, each
with a random destination 3–60 km away, on the fastest arm.

- The cheapest route turned the driver around on **133**.
- **46** had **no way ahead**, so they get the U-turn, which is right: any way
  out goes back down the road the car is on. In an earlier run of the same
  sample (335 departures), all 37 such cases were on residential streets.
- **87** had a way ahead, at:

| | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| extra minutes | 1.5 | 3.9 | 7.8 | 8.9 | 22.5 | 42.7 |
| extra km | 0.7 | 3.7 | 6.4 | 9.9 | 17.0 | 28.7 |

Over 5 min: 18. Over 10: 3. Over 15: 2. Over 20: 1. Over 30: 1.

**The cap is your call.** Without one, the worst random case sends a driver
on for 43 extra minutes rather than offer the U-turn again. `TURN_BACK_CAP_MIN`
is set to **15**: it leaves every traced case alone, and it catches 2 of the
87. At **10** it would also catch `164801`'s +11.2, if that were ever
declined, and 3 of the 87. A cap that is too low gives the storm back on
divided roads, which are exactly where the U-turn often can't be made at
once. The cap is one constant, and `--sample` re-measures it.

## Limits

- **The strip is straight.** Behind a car on a curving road, it leaves the
  road after a few hundred metres. That does not matter for what was measured:
  every turnaround came back within 13 m, at or near the car. But a long
  round-the-block that rejoins a curving road far behind would be missed.
- **A hairpin ahead.** If the road the car is on doubles back through the
  strip within 1,000 m, the search ban closes the road's own continuation. The
  cap or the no-way-ahead fallback then hands back the cheapest route, and
  that route is right, though it says it turns around. No recorded drive
  has met this.
- **Latency.** A flagged request whose cheapest route turns around runs each
  arm's search twice. The prototype measured the constrained pair at
  0.4–0.6 s at pref 0.77, and under 0.1 s on the fastest arm. Requests whose
  cheapest route goes on ahead cost nothing extra, and nor does any unflagged
  request.
- **Not driven yet.** The replay shows what the server would have answered.
  Whether a driver who has declined a U-turn takes the route ahead is the
  next drive's question. The trace now carries `req_declined_uturn` and
  `turnaround_m` to answer it.

## Tests

- `tests/test_uturn.py`. The definition, on synthetic geometry: a U-turn at
  the junction ahead, the step-1 form on a divided road, round the block, a
  road bending back 95 m to the side, a right-angle crossing behind, a return
  past the window, and `turnaround_m`. On the real graph: keep-ahead on both
  arms, a route already ahead left byte-identical, no heading means no
  change, the cap.
- `tests/test_api.py` (`declined_uturn` section): the reply properties, an old
  client gets today's route, a declined U-turn is not offered again (also at
  pref 0), and the loop rejoin accepts the flag and ignores it.
- `ios/Tests/DeclinedUTurnTests.swift`. Set by leaving a U-turn untaken;
  the first U-turn still offered; the step-1 form (following the route ahead
  to its turnaround is not taking it); an old backend changes nothing; set by
  "fastest" instead of the U-turn; kept across a switch to fastest, and
  across a failed one; cleared by driving 100 m of the route ahead, after
  which a new departure asks plainly; a U-turn the driver takes is not
  declined.
- `ios/Tests/RouteServiceRequestTests.swift`. `declined_uturn=1` in the body
  only when set.

## Reproduce

```sh
.venv/bin/python tools/replay_uturn.py data/processed-ne traces/*.ndjson
.venv/bin/python tools/replay_uturn.py data/processed-ne --sample 400
```

The first prints the replay table, the second the random-departure costs.
Both print trace names, sequence numbers, distances and durations only. The
traces are private, and nothing here places them.
