# Measuring whether the roads are nice

**Status:** current. Split out of the README 2026-09-16. This is the only
instrument in the repo that tests the product rather than the car.

The travel-time work measures the car. None of it measures the product.

The scenic score is calibrated against its own distribution and against two
byways whose names are written into `score.py`. That establishes it is
self-consistent and correctly scaled; it does not establish that it is right.
No open geodata answers "is this road beautiful", and the person driving it is
the only instrument that can — while they are there, because the answer does not
survive the trip home.

So the nav screen carries two buttons, above the trip bar: **lovely road** and
**nothing to see**. One tap each, distinct haptics so you can feel which one you
hit without looking, and a `mark` record in the trace. Two options rather than a
five-point scale because this is answered at 45 mph — a scale needs aiming, and
aiming needs looking at the phone. The calibration wants a rank statistic over
many marks anyway, so precision on any single one buys nothing.

`analyze_trace.py` then resolves each verdict to a stretch of road and compares
it against what the score claimed there:

    SCENERY  79 marks over 12 drive(s) — 60 nice, 19 dull
      model score on the roads you liked   5.24 (median 5.47, n=60)
      model score on the roads you didn't  3.53 (median 3.63, n=19)

      SEPARATION  0.74    above chance
      0.50 is a coin — but with 60 nice and 19 dull, a score
      that knows nothing still reaches 0.63 one run in twenty.

      same number over other windows —  200 m: 0.75   400 m: 0.74   800 m: 0.74

That is the whole exercise in one number: the chance the score ranks a road you
liked above one you didn't. Three things about it are load-bearing.

**It is a rank statistic, not a difference of means.** It assumes only that
higher should mean nicer, which is the entire claim the score makes, and one
marked stretch that happened to snap to a 9.6 cannot carry it.

**The noise floor is printed beside it, computed from your own sample sizes.**
Off five marks each way a score that knows nothing reaches 0.82, so an
impressive-looking 0.75 from a first drive is worth nothing — and read against
0.50 it looks like the premise confirmed. That is much the likeliest way this
exercise talks itself into a wrong answer, so the number it has to beat is
always on screen next to it.

**A mark is about a stretch, and a late one.** A driver taps *after* seeing
something, so the tap is downstream of what prompted it; the anchor is walked
back by the distance covered during `MARK_REACTION_S`, converted at the speed the
car was doing rather than at a guessed number of metres — three seconds is 40 m
through a village and 110 m on a highway. From there the verdict is charged to the
preceding `MARK_WINDOW_M` (400 m, one `score.py` chunk's worth of road, sampled
along the route line rather than per GPS fix so a minute at a red light doesn't
weight that junction sixty times over). Because the window is a judgement call,
the report re-runs its own headline at 200 m and 800 m and says so if the answer
moves — a conclusion that only holds at one window size is not one.

Two things worth knowing before reading a report:

- **Every exclusion is counted, and "you didn't tap" is never confused with "your
  taps were unusable."** They call for opposite responses. A mark carries the
  *last* GPS fix, not the instant of the tap, so a stalled location stream
  produces verdicts anchored wherever the car was when it stopped reporting —
  dropped past 5 s of staleness, and reported as that rather than blamed on the
  road. The marks stay in the trace either way: fix the cause and re-read, no
  re-driving.
- **The report ends with the disagreements, worst few in each direction**, with
  road names and coordinates, because those are the addresses worth going back
  to. The two directions cost different things. A road you called dull that
  scored high is scenery the model claims and the road doesn't have — the
  expensive kind, since that claim is what the router spends your extra minutes
  buying. A road you liked that scored low costs nothing but is where the score
  is blind, and it will route around it.

Tap often; there is no cost to it, and the noise floor falls as the marks
accumulate. Two drives at different hours are still worth more than one — but for
this, unlike for the clock, a second driver would be worth more than either.
