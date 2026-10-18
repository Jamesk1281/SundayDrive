# The router at US scale

**Status:** day one, 2026-10-18, on branch `claude/us-scale-router` off `usa`.
Nothing has been built yet. This section is the dated plan. Measurements
replace the estimates below as they land, and each section says which it is.

The design is path C of [usa-extension-feasibility.md](usa-extension-feasibility.md)
§8: one compact graph in memory, and each route searched only inside an ellipse
around the trip. Point-to-point trips are capped at 500 km straight line.

## The earliest honest date

**The router, options, loops and reroutes on the compact graph and corridor
search, with New England parity proven and US-scale numbers from a synthetic
graph: Friday 23 October.** Thursday 22 is possible if parity turns up nothing
that needs explaining. It probably will turn something up, so plan on the 23rd.

**Measured on `data/processed-us`: one day after it exists.** Most of that day
is building the compact pack from it (the pack is described below), plus one
measurement pass.

For a submission on Thursday 29 October, the server has to be on the box with
the US data by about Monday 26 October, so the app can be tested against it.
That works only if the US data arrives by about Saturday 24 October, and if the
box has been resized (next section).

### A correction to the premise: the box has 8 GB, and the ceiling is 12 GB

The feasibility review and the launch plan both size the US against a **24 GB**
box. The box in the repo's own measured records is smaller:

- `server/DEPLOY-oracle.md` (executed 2026-09-28/29): `VM.Standard.A1.Flex`,
  **2 OCPU, 8 GB**, chosen "deliberately not 12".
- `docs/hosting-status-2026-09.md` and `docs/hosting-independent-review.md`
  (C19), both checked against Oracle's page on 2026-09-28: the Always Free A1
  allowance is **2 OCPU / 12 GB**.
- `docs/load-test-oracle.md`: resizing to 12 GB "costs a stop/start, and
  Ashburn's A1 capacity is not guaranteed at the moment of the resize".

24 GB was Oracle's older A1 allowance. So the hard ceiling at $0 is 12 GB of
RAM and two A1 cores, each about three quarters the speed of the Mac's M2
cores (`DEPLOY-oracle.md`, Part 13).

What this changes:

- **The design still holds, but the margin is gone.** The review put a compact
  US graph at 4.4–5.5 GB. Add the access layer (parking lots, used to place
  destinations), each request's working set, the loop and options caches and
  Python itself, and an all-in-RAM US router would sit at or over 12 GB.
- **So the bulk of the graph will be memory-mapped from disk, not loaded.** A
  one-time *pack* step turns a processed directory into flat arrays. The server
  maps them read-only, so geometry, names and the search arrays are
  file-backed pages. The kernel can drop those pages under pressure; they do
  not count against the box the way built Python objects do. What stays truly
  in RAM is small: each request's corridor, the caches, a few dicts. The
  target is **peak anonymous memory (what the kernel cannot drop) under 6 GB
  under concurrent load**, reported beside total RSS. That works on today's
  8 GB box. The 12 GB resize then becomes headroom rather than a
  requirement. That target is a goal, not a measurement yet.
- **Someone has to decide about the resize.** It isn't mine to do, since
  deploying is the master session's job. If the 6 GB target holds, the resize
  is optional.

### What could move the date

1. **New England parity takes longer than a day to explain.** The corridor is
   empirical (the review found it exact on 80 of 80 trips, not on all trips).
   Snapping without shapely's tree may break ties differently. Every difference
   gets explained, and each one costs time.
2. **Long loops in dense places.** Loops keep their 400 km limit. A 400 km
   loop searches a disc 440 km in radius. In New England that disc already is
   the whole graph, about eight whole-graph searches, 3–4 s on the box. Around
   New York the same disc holds several times more road. If the synthetic
   measurement puts it past the app's 20 s limit, I'll report it with a
   proposed fix. The limit is not mine to change.
3. **The trip's time zone.** Seasonal closures are dated in New York time
   (`router.py:484`). Nationally the date has to come from where the trip is.
   `timezonefinder` isn't installed, and adding a dependency to the box is a
   deploy decision. The fallback is to close a road if it is closed on any US
   date at that moment. That is never more than three hours early, and it errs
   toward closed.
4. **The US data's date.** That date belongs to unit A.

## Plan, by day

| Day | Work | Done when |
|---|---|---|
| Sun 18 Oct | The fixed New England trip set and its oracle answers from today's router. A synthetic US graph builder. This document. | Oracle answers saved; the synthetic graph loads |
| Mon 19 Oct | The pack (flat arrays, memory-mapped) and a `Router` that loads it. Snapping through a grid index, without a shapely tree over every road. | Same snaps and same whole-graph routes as the oracle on the trip set |
| Tue 20 Oct | Corridor search for routes, both arms, and reroutes. Weights priced per corridor, never per graph. Corridor nodes from a spatial grid, so the cost is O(corridor). Widen the corridor when a route touches its edge. The 500 km cap. | Route parity on the trip set; US-scale latency by trip length |
| Wed 21 Oct | Options (`plan`, `spliced_route`) and loops on corridors and discs. Cost models and loop fields cut to the disc, not the graph. | Options and loop parity |
| Thu 22 Oct | Server: dates from the trip's location, national messages, the cap's error. RSS under concurrent load on the synthetic graph, with replicates. | Numbers in this document |
| Fri 23 Oct | Buffer, and explaining every parity difference. | Suite green; this document final for New England and synthetic |
| A's date + 1 | Pack `processed-us` and measure on it. | The US table filled in |

## Constraints this work keeps

- Today's router on `data/processed-ne` is the oracle. New England must route
  the same, with every difference explained, because it holds the only ground
  truth.
- No whole-graph pass per request. Corridor extraction, weights and search are
  all O(corridor).
- scipy first. numba isn't in the venv; it gets added only if measurement shows
  scipy is not enough, and it would have to install from a wheel on aarch64
  Linux under the box's Python 3.12.
- No changes to the pipeline build files, `closures.py` or `ios/`.
