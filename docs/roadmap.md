# Roadmap

**Status:** current. Split out of the README 2026-09-16. `[x]` is built and
measured; `[ ]` is open, with what it is waiting on.

- [x] Scoring pipeline: per-road-segment "beauty vector" (water, coastline,
      forest/parks, curvature, terrain relief, farmland, viewpoints, scenic tags,
      town/urban)
- [x] Terrain relief from the Terrarium elevation tiles (AWS Open Data; an
      aggregate of national elevation products — see
      [data sources and licences](data-sources.md))
- [x] Routable graph (998k edges, 795k nodes) split at intersections,
      scenic-scored
- [x] Scenic router: Dijkstra with a time-vs-scenery preference knob
- [x] Per-beauty-type preferences — weight scenery types live per request
- [x] iOS app (SwiftUI + MapKit): route planning from an address or your own
      location, tunable scenery, turn-by-turn live navigation with arrival
      time / distance remaining and a switch-to-fastest escape hatch
- [x] Scenic byways read from OSM route relations rather than hardcoded names,
      with the Mohawk Trail and Jacob's Ladder kept as calibration benchmarks
- [x] Scoring calibrated against the score distribution, with tests that guard
      it (`tests/`) — see [How scoring works](scoring.md)
- [x] Hosted API: self-hosted on a spare laptop behind a Cloudflare tunnel, so
      the app works off-device on a real phone — see
      [`server/DEPLOY.md`](../server/DEPLOY.md)
- [x] Land cover: ESA WorldCover tree cover, blended half and half with OSM's
      mapped green, because OSM's polygons record land *designation* rather
      than vegetation and are three times more complete in Rhode Island than
      in Maine
- [x] Drive traces: every drive records itself, so a test drive produces
      measurements instead of impressions — see
      [Measuring travel times](measuring-travel-times.md)
- [x] More accurate travel times: routes are priced at the speed each road class
      is really driven, plus the mapped traffic signals and stop signs on them,
      in the direction those face. Measured against two recorded drives, error
      falls from 22% to 5.7% pooled, and the ETA the app showed for one of
      them goes from 13.3% out to 2.2%. What is left is congestion, which no static graph
      predicts — see [Measuring travel times](measuring-travel-times.md). Those two
      drives are the sample; the constants are due a re-fit, below
- [ ] **Re-fit `CONTROL_SECONDS`.** The costs the router charges (9.5 s per
      signal, 9.3 s per stop sign) were fitted while `analyze_trace.py` was
      caching the *alphabetically first* extract in `data/raw` — Connecticut,
      once the six New England states sat next to the merged build. So drives
      taken in Massachusetts were explained with Connecticut's signals, every
      real stop fell into "unexplained — traffic", and the denominator the fit
      divides by said these roads had almost nothing on them. The picker now
      takes the largest extract and says which one it used. Re-read with the
      right cache, the share of stopped time that OSM can already account for
      goes from 18% to 35%, and ten drives put a signal at **11.9 s** and a
      stop sign at **8.5 s** — so signals are currently under-charged by about
      a quarter. Re-fitting changes ETAs, so it is a deliberate step, not a
      drive-by
- [ ] Time of day. A static cost is an average over a quiet hour and a busy one:
      the two drives met almost the same number of signals — 26 and 27 — and
      stopped at 4 and 12 of them. That variance, not the model, is what now
      caps per-drive accuracy
- [x] Directions a driver can follow. Two measurable ways a route misleads
      someone, both now audited by `tools/audit_directions.py` over 120 random
      routes: turns OSM forbids (18% of routes → 1%, by splitting the 3,078
      junctions that carry a restriction into one node per approach), and
      junctions where holding the wheel takes you off route with no instruction
      (78% of routes → 0%). See
      [`docs/directions-accuracy.md`](directions-accuracy.md)
- [ ] Lane guidance. Nothing reads `turn:lanes`, so nothing ever says "use the
      right two lanes" — and at a multi-lane exit the wrong lane is a missed
      exit however good the maneuver is
- [ ] `via`-way turn restrictions, where the forbidden movement spans a whole
      road rather than a junction. They are counted and skipped at build time;
      honouring them needs the search to remember more than one junction back
- [ ] Start from the exact point, not the nearest corner. `snap()` finds the
      road you're on and then routes from that road's *nearer end* — right
      street, but a median 99 m up it (p90 217 m), because graph nodes are
      junctions. Splitting the snapped edge into two virtual nodes per request
      would take that to zero
- [x] An instrument for route quality. Two buttons on the nav screen record what
      the driver thinks of the road they are on, and `analyze_trace.py` compares
      each verdict against what the score claimed for that stretch — so "is this
      actually a nice road?" produces a number instead of an impression. See
      [Measuring whether the roads are nice](measuring-scenery.md)
- [x] **Drive the routes and judge them.** 79 marks over 12 drives say the score
      ranks a road the driver liked above one they didn't **74% of the time**,
      against a **63%** noise floor computed from those same sample sizes — and
      the answer holds at every window width tried (0.75 / 0.74 / 0.74 over
      200 / 400 / 800 m). That is the first thing in this repo that says the
      score tracks a human rather than only itself.
- [ ] **More drivers.** Those 79 marks are one person, in one part of one state.
      A second driver is worth more than a second drive: it is the only way to
      tell a scenic score from one person's taste.
- [ ] The app still opens on Massachusetts. The API serves all six states, but
      `Region.massachusetts` is the iOS map's starting camera and its address
      search bias (`ios/Sources/Region.swift`), so a Vermont trip is harder to
      search for than it should be.
- [ ] **A drive that never joins its route can never end.** All three arrival
      tests are gated on `hasJoinedRoute`
      (`ios/Sources/NavigationModel.swift:849-857`), so a car that is snapped
      onto the wrong road, or parked beside a line it never reached, stays in
      navigation indefinitely — holding GPS at 1 Hz with the screen awake. Found
      on the 2026-08-25 drives and flagged as out of scope by three documents
      since (`reroute-audit.md`, `reroute-step-offset.md`,
      `docs/archive/stale-plan-after-arrival.md`); it belongs to none of them. The fix is not
      to clear `hasJoinedRoute` — it also gates the backtrack floor and
      off-route recovery — so it needs an arrival path that does not depend on
      having joined
- [ ] **Remaining distance and ETA credit route the driver has not driven.** The
      banner half of this was fixed 2026-08-25; the odometer half was not. A
      driver matched 229.6 m along a line they have not started still has
      229.6 m knocked off `remainingMeters`. 0.5% on a 42 km trip, and it
      corrects itself on joining — see `docs/reroute-step-offset.md`
- [ ] **`RELIEF_FULL` has no range left north of Massachusetts.** It is 100.0
      (`score.py`), fitted to Massachusetts. Measured over the New England
      build, **13.4% of chunks north of MA already saturate it**, so a 1,453 m
      ravine in the White Mountains scores the same as a 100 m rise outside
      Worcester. Re-fitting is rollout Phase 4 and changes every score, so it is
      a deliberate step — `docs/new-england-terrain-findings.md`, Finding 3
- [ ] **The 500 m reroute re-seat window is argued, not fitted.** Bounded by one
      measured case (282 m). A drive deliberately routed over a road the route
      uses twice would calibrate it — `docs/reroute-audit.md`

> The early MapLibre web demo was retired to focus on iOS; it lives in git
> history (`git show 82044e2`) and is cheap to revive on the same API if needed.
