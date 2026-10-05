# Roads closed to cars all year: what was built, and the decisions behind it

**Status:** built 2026-10-05 on `claude/heuristic-poincare-bc2422`, against
`main` at `191e15c`. Not merged, not deployed. The dispatch brief,
`docs/closed-roads-brief.md`, is committed with this work and deleted when it
merges (`git log --all -- docs/closed-roads-brief.md` finds it). This document is
what outlives it: the decisions as built, the measurements, and what is still
open. Code comments and tests cite this file, and section names here are cited
by them.

**The snap rule (the brief's Trap 2) is built**, not left open. Nothing here
starts a driver on the far side of a barrier, or ends a route past one.

## Result

**What is closed.** 1,093 edges and 423.5 km, both ways and for every request:
0.11% of the graph's 998,252 edges and 0.18% of its 232,720 km.
- 530 ways are closed by their own tags: 665 edges, 201.6 km.
- 508 barriers and fords stand inside an edge, closing 456 edges and 233.5 km.
- 28 edges are counted in both.
- On top of those, nobody may drive *through* the 105 barriers that stand where
  two edges meet.

The router prints:

```
closed to cars: 1,093 edges (423.5 km, 530 ways, 508 barriers and fords), and no driving through 105 more barriers; 916 junctions cut off behind them
```

**Before and after**, on the same sample:
- **The sample.** 160 random origin-destination pairs and 160 random loop starts
  (seed 20261005), drawn from `graph_nodes.parquet`.
- **The settings.** The server's defaults: a route at pref 0.5 with every weight
  1.0; a loop at 40 km and pref 1.0.
- **The servers.** Every request was POSTed to a local server: "before" is
  `main` at `191e15c`, "after" is this branch. Both ran on the New England build
  on 2026-10-05, when no seasonal closure is in force.

| | before | after |
|---|---|---|
| **loops** crossing an element this branch closes | 9 of 160 (5.6%) | **0** |
| **scenic routes** crossing one | 13 of 160 (8.1%) | **0** |
| **fastest routes** crossing one | 2 of 160 (1.2%) | **0** |
| the review's narrower set, loops / scenic / fastest | 4.4% / 6.2% / 0% | 0.6% / 0 / 0 (see below) |
| requests answered | 320 of 320 | 320 of 320: **none now fails** |
| responses that changed | | 10 loops (6.2%), 13 scenic (8.1%), 2 fastest (1.2%) |
| median on the changed | | loops −0.1 min, +0.0 km, beautiful km ±0.0; scenic +0.1 min, +0.1 km, ±0.0; fastest: the 2 routes below |
| untagged gates crossed: loops / scenic / fastest | 9 / 5 / 0 | 6 / 6 / 0 |

**What counts as crossing.** A response crosses an element when all three hold:
- its line passes within 1 m of the element;
- that point is not within 1 m of the line's start or end;
- the line runs along the element. At least half of a closed edge, or of the
  30 m of road around a barrier, up to 20 m, lies within 1 m of the line.

The third condition was added after the first pass. Without it, two routes
"crossed" the Southeast Expressway HOV lane where they pass over or under it,
covering 2-4 m of edges 32-117 m long, before and after alike.

**The review's set.** It counted gates and chains tagged `no`/`private`, blocks,
bollards, and `motor_vehicle=no|private|permit` ways. Its 5.4% of loops, 6.0% of
scenic routes and 1.3% of fastest routes compare with this sample's
4.4% / 6.2% / 0% on that set, or 5.6% / 8.1% / 1.2% on the full closed set.

The one loop still in the review's set after, loop046, drives up a dead end on
Old Town Hall Road to an `access=no` gate and turns back. It does the same
before and after. A dead-end gate closes nothing, because nothing lies beyond
it in the graph (decisions, "Built beyond the brief").

**Every change, explained.** In each case the before-route crossed what the
after-route avoids, except for one loop at the end of the list:
- **route006 (both arms, −8.3 min).** Its start is up Bull Branch Road in Maine,
  behind a `motor_vehicle=permit` gate and a run of fords. It now leaves from the
  pocket's way out, and the route is 4.9 km shorter; before, it drove out
  through them.
- **route140 (fastest +6.0 min, scenic +3.1 min):** a ford on Center Road.
- **loop059 (+6.4 min, +2.9 km, +1.4 beautiful km):** the private gate on
  Creeper Hill Road, one of the brief's loop cases.
- **loop071 (−10.3 min) and loop003 (−4.0 min):** a ford on Masons Bay Road and
  a permit gate on South Peak Road, each standing between two edges.
- **route074 (+1.5 min) and loop114 (+1.3 min):** the `access=no` lift gate on
  Tracy Wood Road and a `motor_vehicle=no` gate on Lanesville Road, each between
  two edges.
- **The other 15, all within ±1.1 min:**
  - Holman Street's blocks, the brief's case 2 again (route157, route159);
  - R Street's `motor_vehicle=no` stretch and its blocks (route033, route048,
    route154);
  - the Stanley Street chain (route052, route095);
  - Porter Street, which is `motor_vehicle=private` with a gate (route149);
  - a block on Westford Street (route108);
  - a `barrier=yes` at Hartford Square (route086);
  - Cove Street's `motor_vehicle=no` stretch and gate (loop016, loop150);
  - a ford on Wakefield Street (loop015);
  - a block on Highland Avenue Extension (loop037);
  - jersey barriers on Main Street (loop124).
- **loop040 (+1.0 min) crossed nothing.** Its turnaround moved 0.7 km, in the
  same direction and with the same beautiful km. The planner's length estimates
  for other candidate turnarounds changed where their paths ran through closed
  elements.

A scenic route or a loop can come back with *fewer* minutes. The scenic arm
minimises a blend of time and scenery, and a loop aims at a length, not a time.
Only route006, whose start moved, is faster on the fastest arm.

**The brief's cases**, run on the local "before" server (production's code and
data) and on this branch, each with the app's parameters:

| case | before | after |
|---|---|---|
| 1, Crane Road | both arms "Turn left onto Crane Road", through the gate | neither; +0.3 min |
| 2, Holman Street | scenic arm "Turn right onto Holman Street", through both blocks | not on it; +0.8 km, −0.4 min |
| 3, Stanley Street | both arms "Turn left onto Stanley Street", through the chain | neither; +0.1 min |
| 5, reroute 57 m short of the Crane Road gate, heading away from it | both arms open "Sharp left onto Crane Road", back through the gate | "Head north on Clear Pond Drive"; +1.6 min |
| 5, the same, heading toward the gate | starts beyond the gate: "Turn right onto Norfolk Street" | starts on the car's own side: "Sharp right onto Clear Pond Drive" |

**What it costs.** The two routers were loaded back to back on the same build,
with nothing else running:
- **Load time:** 50.4 s and 50.5 s on `main`, against 49.8 s and 50.6 s here.
  The ways round a closure take one strong-components pass, two breadth-first
  passes and two multi-source Dijkstras. Together they are inside that noise.
- **Peak RSS:** 4.02 GiB on `main` and 4.05 GiB here when measured back to
  back. Across runs it ranged from 3.1 to 4.1 GiB for both, so the difference
  is noise.
- **Graph size:** the 208 barrier copies take `n` from 801,719 to 801,927, which
  `/api/health` reports as `routing_slots`.
- **Per request:** `_weights` does one more numpy assignment, of +inf into the
  2,291 closed slots out of 1,891,793, on top of the work it already does.

## The decisions, as built

The brief's six decisions were made before the work started. They were built as
written, with one exception, the kerb.

1. **A side table and a router mask, not a rebuild.**
   - `pipeline/closures.py` already scanned the PBF for seasonal closures. The
     same single pass now also writes `closed_to_cars.parquet`. The whole run
     takes 68 s and peaks at 2.6 GB.
   - The control still holds: the scan sees 565,410 drivable ways, equal to
     `roads.parquet`. The seasonal table it rewrites is **byte-identical** to the
     one built on 2026-10-04.
   - `Router` loads the new table at startup. It refuses one whose `u`/`v` do
     not match `graph_edges.parquet`, as `SeasonalClosures` does, and prints
     `closed to cars: ...`, flushed, either way.
   - The rebuild-time version is still for the next full rebuild: see "What is
     still open".
2. **Server-side only.** No iOS change.
3. **The car-access rule is OSM's transport-mode hierarchy.**
   - It lives in `pipeline/common.py` as `car_access` and `closed_to_cars`, so
     that `extract.py` and `graph.py` can apply it at the next rebuild.
   - The most specific key present wins: `motorcar`, then `motor_vehicle`, then
     `vehicle`, then `access`.
   - Closed: `no`, `private`, `permit`, `agricultural`, `forestry`, `military`,
     `emergency`, `delivery`, `psv`, `bus`.
   - Everything else is open, including `destination`, `customers` and any value
     it does not recognise. Subkeys such as `access:delivery` are not read.
4. **Barriers on a drivable way** (`barrier_closes` in `common.py`).
   - A gate (`gate`, `lift_gate`, `swing_gate`, `cattle_grid`, `toll_booth`,
     `border_control`, `entrance`, `height_restrictor`, `sally_port`, `arch`,
     `no`) passes unless its own tags close it, by the hierarchy or
     `locked=yes`. An untagged gate passes.
   - Every other `barrier=` value blocks unless its own tags open it.
   - **The exception: `kerb` passes.** There are 19 kerbs on drivable ways in
     this extract, and they are pedestrian crossings' kerbs dropped onto the
     road's centreline:
     - 16 are tagged `kerb=lowered|flush` or `highway=crossing`. They stand on
       Broadway in Cambridge (primary), on Reverend Dr Martin Luther King Jr
       Boulevard and South Frontage Road in New Haven (trunk), on Park Street
       there (secondary), and on seven smaller roads.
     - The other three are bare, or `kerb=yes`. One of them is on no edge of
       the graph. The Abbot Street one in Andover was added by an Every Door edit
       whose comment reads "Updated 13 crossings" (changeset 171825990).

     Blocking them would have closed those roads. OSRM's car profile, which
     decision 4 follows, passes the lowered, flush and crossing kerbs for the
     same reason. So `kerb` passes outright, and still closes when its own tags
     close it.

     This is the one place the build departs from the brief. Reverting it is a
     one-word change to `PASSABLE_BARRIERS`.
5. **Fords are closed.** A `ford=yes` way, or a `ford=yes` node on a drivable way,
   whatever else it is tagged.
6. **Closed for every caller**, `on=None` included. The table is loaded once
   and never changes, so no cache needed a new key.

### Built beyond the brief

**Where a barrier stands decides what it closes.** See "Where the barriers
stand" for the counts.

| where it stands | what is closed |
|---|---|
| inside one edge | the edge, both ways; the barrier's distance from `u` is stored as `at_m` |
| a node where exactly two edges meet | driving *through* the node, and neither edge |
| a dead end (one edge) | nothing |
| a node where three or more edges meet | nothing; recorded |

- **Dead ends close nothing**, and the brief allowed closing them. Nothing
  drives through a dead end, so closing the edge buys nothing. It does cost
  something: every destination on that road would then snap back to the road's
  mouth instead of driving up to the gate. 459 of the 533 dead-end edges are
  residential streets.
- **A barrier between two edges is the turn-restriction machinery, with one
  change.**
  - Each approach gets its own copy of the junction, as
    `_apply_turn_restrictions` does (`Router._split_through_barriers`).
  - Unlike a restriction's copy, each copy keeps *every* exit. The exit onto the
    far side is priced at +inf in `_weights` instead of being left out.
  - Leaving it out is the obvious version, and it breaks. Behind many of these
    barriers is a dead-end pocket. Removing the movement disconnects the pocket,
    and `_keep_network_reachable` then gives the movement back to reconnect it,
    which reopens exactly the gate that was being closed.
  - Kept and priced, the graph stays as connected as it was. The ALT tables,
    built on the graph with nothing closed, stay admissible.
  - The 105 barriers became 208 copies: `n` goes from 801,719 to 801,927.
  - None of these nodes already carries a turn restriction. The code skips one
    that does, rather than copying a copy.
- **The way round what a closure cuts off** (`Router._ways_round`).
  - Closing a gate cuts off what lies behind it: 916 junctions as destinations,
    926 as starts.
  - A destination there ends at the nearest junction on the road in that a
    route can reach. That is the near side of the gate, so it is never beyond
    it and never "no route found".
  - A start there leaves from the nearest junction on the road out.
  - Each comes from one multi-source Dijkstra at load, over the graph with
    nothing closed, measured in kilometres.
  - Examples:
    - a pin up Watatic Mountain Road, past its `locked=yes` gate, ends at the
      gate's near end;
    - a pin up HMS Halsted Drive, past a `motor_vehicle=no` gate between two
      edges, ends at the gate itself, on the open side.

### Snapping (the brief's Trap 2)

`Router.snap` serves the start, a reroute, a `via` and a loop.
`Router.snap_destination` serves the destination. Both now obey these rules:

- **A point on an edge with a barrier inside it** takes the end on its own side
  of the barrier, whatever distance or heading say. The point's projection
  along the edge is compared with `at_m`.
  - At Crane Road the gate stands 21.1 m from one end of a 230 m edge. A car
    57 m short of it, coming from the other end, is 78 m from the near end and
    152 m from the far one, so the nearer end is past the gate.
  - On `main` today, a car 57 m short of the gate and facing it is started from
    beyond the gate ("Turn right onto Norfolk Street"). Facing away from it, the
    car is sent back through it ("Sharp left onto Crane Road").
- **A point at a barrier between two edges** takes the copy of the junction on
  its own side. From that copy the only way on is back.
- **A point between two barriers on one edge** has no end of its own edge that
  a car can reach. It snaps to the nearest part of a road a car can use, which
  is usually the stretch beyond the nearer barrier. On Turner Road, 4 m past
  either of its two barriers, which stand 18 m apart, a point takes the end
  beyond that barrier.
- **A point on a road closed by its tags** (`motor_vehicle=no` and the rest)
  snaps to the nearest road a car can use. The search doubles outward from the
  closed edge's distance. A point in the middle of Blunt Park Road, in
  Springfield, snaps to the road 86 m away.
- **A node no route can leave or reach**, behind a gate, gives way to the
  nearest one on the road in or out (above).
- **A heading never carries the snap through a barrier.** `_aligned_edge` no
  longer considers an edge that is closed where the driver stands.

## Where the barriers stand

The brief's Trap 1, measured first. These are the 1,183 barrier and ford nodes
on drivable ways that stop a car, placed on the New England graph:

| kind | inside an edge | two edges meet | dead end | three or more | on no edge | total |
|---|---|---|---|---|---|---|
| gate (any tag that closes it) | 131 | 40 | 276 | 1 | 9 | 457 |
| block | 88 | 10 | 95 | 0 | 13 | 206 |
| `barrier=yes` | 74 | 12 | 44 | 0 | 7 | 137 |
| ford | 83 | 3 | 1 | 0 | 3 | 90 |
| bollard | 31 | 7 | 42 | 0 | 0 | 80 |
| chain | 41 | 7 | 17 | 0 | 0 | 65 |
| jersey barrier | 20 | 16 | 20 | 0 | 2 | 58 |
| swing gate | 22 | 3 | 15 | 0 | 0 | 40 |
| lift gate | 6 | 2 | 4 | 0 | 0 | 12 |
| other (fence, debris, ditch, log, rope, wall, ...) | 12 | 5 | 19 | 0 | 2 | 38 |
| **total** | **508** | **105** | **533** | **1** | **36** | **1,183** |

- **Inside an edge: 508**, closing 456 edges and 233.5 km. 418 of those edges
  carry one barrier, 34 carry two, and one each carries three, four, five and
  ten. The ten are fords, all on one edge of Bull Branch Road in Maine.
- **Where two edges meet: 105.** All 105 sit where two different ways meet end
  to end. None is a node where one way is split. Examples:
  - a gate (`access=no`) between Eagle Avenue and Arthur Paquin Way;
  - a `barrier=yes` across Rockford Street in Boston;
  - jersey barriers on Mellen Street and Yarmouth Street.

  At 45 of the 105, both sides are connected to the network. At 58, one side is
  reached only through the barrier, a pocket behind it. At the last 2, one side
  is a one-way road leading away from it, which needs no copy.
- **Three or more: 1.** A private gate on Whitney Lane at a fork, node 62209736,
  `access=private`, with edges of 242 m, 26 m and 28 m. Which of the three it
  bars is a guess, so it is left open. The other node of degree 3 or more was a
  crossing kerb on Water Street, now open under the kerb exception.
- **Dead ends: 533**, left alone (see "Built beyond the brief").
- **On no edge of the graph: 36.** No graph edge of their way passes them, so
  they close nothing.

Gates by the tag that closes them: `access=private` 146, `access=no` 134,
`motor_vehicle=no` 130, `motor_vehicle=private` 38, `locked=yes` 36,
`motor_vehicle=permit` 8, `access=permit` 7, `motorcar=no` 4, `vehicle=no` 4,
`vehicle=private` 1, `access=delivery` 1.

## The counts

**Ways closed to cars by their tags**: 549 drivable ways in the PBF, 530 of them
in the graph. They cover 665 edges and 201.6 km.

| deciding tag | ways in the PBF | ways in the graph | edges | km |
|---|---|---|---|---|
| `motor_vehicle=no` | 260 | 253 | 292 | 82.3 |
| `motor_vehicle=private` | 194 | 193 | 271 | 63.7 |
| `access=permit` | 43 | 40 | 47 | 9.5 |
| `motor_vehicle=permit` | 15 | 15 | 19 | 28.6 |
| `ford=yes`, and no access tag that closes it | 12 | 10 | 12 | 4.9 |
| `access=forestry` | 6 | 6 | 7 | 4.5 |
| `access=military` | 5 | 0 | 0 | 0 |
| `vehicle=no` | 5 | 5 | 5 | 5.4 |
| `access=delivery` | 3 | 2 | 5 | 0.5 |
| `access=emergency` | 2 | 2 | 2 | 0.3 |
| `motor_vehicle=emergency` | 2 | 2 | 2 | 0.1 |
| `access=agricultural` | 1 | 1 | 2 | 1.7 |
| `vehicle=private` | 1 | 1 | 1 | 0.2 |

Thirteen ways are fords. The one that is also `motor_vehicle=no` is counted
under `motor_vehicle=no`. These agree with the brief's counts (260, 194, 43, 15,
6, 5, 5, 13).

**Barrier and ford nodes on drivable ways**: 3,212 carry a `barrier` or `ford`
tag. 1,183 of them stop a car (above), and 2,029 are left open:

| left open | nodes |
|---|---|
| untagged `gate` | 1,437 |
| untagged `border_control` | 125 |
| untagged `lift_gate` | 115 |
| untagged `swing_gate` | 83 |
| untagged `toll_booth` | 72 |
| untagged `height_restrictor` (every one 9 ft or more) | 28 |
| crossing `kerb` | 19 |
| untagged `entrance` and `cattle_grid` | 5 |
| opened by their own tags: gates 80, swing gates 33, lift gates 21, toll booths 5, and 6 others (`access=permissive`, `access=yes`, `motor_vehicle=permissive`, ...) | 145 |

The untagged gate, lift gate and swing gate add up to **1,635 untagged gates**,
open as decided. How often routes still cross them is under "Result".

### Recorded, not acted on

| what | count | why it is left |
|---|---|---|
| drivable ways the old filter drops that the hierarchy would admit (`access=private` or `no`, with `motorcar=yes` or `motor_vehicle=destination|designated|unknown`) | 9 | re-admitting them needs a rebuild |
| ways open for local access only (`access=destination` 445, `motor_vehicle=destination` 197, `access=customers` 111, `vehicle=destination` 3, `motor_vehicle=customers` 1) | 757 | legal for a driver with business there; through-traffic handling is out of scope |
| ways with a car value the hierarchy does not recognise (`access=residents` 5, `hov` 1, `restricted` 1) | 7 | open, as decided |
| gates whose access depends on the time (`opening_hours` or a car key's `:conditional`) | 36: 28 left open, 8 closed | time of day is out of scope |
| ways closed by `motor_vehicle=no` that a `:conditional=yes @ (hours)` opens part of the day | 62 | closed all day here |
| rising bollards | 4 | they block, as decision 4 says; OSRM passes them |

All 62 part-time ways are **the Southeast Expressway HOV lane**:
`motor_vehicle=no`, with `motor_vehicle:conditional=yes @ (Mo-Fr 05:00-10:00)`
on 32 of them and `yes @ (Mo-Th 15:00-19:00; Fr 14:00-19:00)` on the other 30,
and `hov:minimum=2`. Outside those hours the lane is not there at all
(`lanes:conditional=0`). Before this change a route could use it at any hour.
Now none can, which is right for a driver alone in the car.

## What is still open

- **Closures OSM does not record.** A gate mapped without `access` or `locked`
  is open here. 1,635 untagged gates stand on these roads, and some will be
  locked.
- **Through-traffic on `destination` and `customers` roads.** 757 ways stay
  fully open.
- **Time of day.** Park gates shut at dusk, and the HOV lane. The router has no
  clock (docs/seasonal-closures.md, decision 2).
- **The rebuild-time rule.** At the next full rebuild:
  - apply `car_access` in `extract.py` and `graph.py`, in place of the
    `PRIVATE_ACCESS` test they copy (`extract.py:176`, `graph.py:202`, and the
    same line in `closures.py`'s scan);
  - read barrier and ford nodes in `graph.py`'s node handler.

  That re-admits the 9 dropped-but-open ways and drops the 549 closed ones.
  The barrier logic here still has to run on the result, because a barrier
  inside an edge or between two edges is not a way-level fact. Until then this
  table is the rule.
- **An in-drive "road closed" control** for a closure OSM does not know about.
  It is new UI and an API change, and is not decided.
- **The kerb exception and degree 1** are the two judgement calls the owner may
  want to revisit (decision 4 is theirs to overrule).
- **Permit roads.** `access=permit` and `motor_vehicle=permit` close roads such
  as Katahdin Iron Works Road in Maine, a fee road the public may drive. That
  is decision 3 as written.

## The brief's traps, as handled

The brief numbered nine traps, and the code and tests cite them by number. This
is what each one became.

| trap | the warning | how it is handled |
|---|---|---|
| 1 | A barrier on a graph node is on no one edge; closing every edge there closes a public road | Measured first ("Where the barriers stand"). Between two edges it forbids driving through (`Router._split_through_barriers`); at a dead end or a junction of three or more it closes nothing |
| 2 | Snapping can start the drive past the barrier | The snap rules ("Snapping") and the way round a closure (`Router._ways_round`) |
| 3 | Join barriers by position, not by midpoint | `join_closed_to_cars`: the barrier lies within `MATCH_M` of the edge's line, and the edge's ends are among the way's nodes |
| 4 | Mask in `_weights`, not in `d_minutes` | The mask is in `_weights`. `d_minutes`, the ETA and the ALT tables are untouched |
| 5 | The filter is in three places, and the scan must match the graph's | The scan is `closures.py`'s, with extract.py's filter: 565,410 ways, equal to `roads.parquet`. `extract.py` and `graph.py` are untouched |
| 6 | The deploy list, and refusing a stale table | `deploy-oracle.sh` ships the table and echoes its line; `ClosedToCars` refuses a stale table; the README build list says `closures.py` writes it |
| 7 | A test that now fails may be encoding the bug | 10 failures in 4 tests of `test_routing.py`. All were `inf - inf` arithmetic over every slot; none routed anywhere or crossed anything. They now compare open slots only |
| 8 | A green suite proved nothing | 13 deliberate breakages, each caught ("Tests") |
| 9 | The overrides must stay open | Unit-tested: `access=no` with `motor_vehicle=yes`, `vehicle=no` with `motorcar=yes`, `motor_vehicle=no` with `motorcar=yes` |

## Tests

**The suite**, against the New England build, with the same data directory:
**497 passed** on `main` at `191e15c` and **630 passed** on this branch, with
none failing. `tests/test_closed_roads.py` adds 133 tests. Without the build,
its 102 pure tests run and the other 31 skip, saying which file is missing.

What `tests/test_closed_roads.py` covers:
- **The access rule.** Every closed value under every car key, and the open
  values. Trap 9's three overrides, and the reverse cases where the specific
  key closes what the general one opens.
- **The barrier rule.** Untagged gates pass. A gate its own tags close is
  closed. Everything else blocks unless its own tags open it. Fords block. The
  crossing kerb passes.
- **The join, on synthetic edges.**
  - A barrier a quarter of the way along closes its edge and records `at_m`.
  - An open parallel road stays open.
  - A barrier between two edges gives two "through" rows.
  - A barrier at a dead end, at a junction of three, or on no edge closes
    nothing.
  - A closed way closes only its own edges.
- **The loader.** A stale table is refused, and a missing one prints
  `closed to cars: none`.
- **On the New England build.** Each test below has a control that fails
  without the change:
  - cases 1-3 on both arms;
  - the Crane Road reroute 57 m short of the gate, facing away, toward it, and
    with no heading, on both arms;
  - a point whose nearer end is past the gate, and a heading toward the gate;
  - a point between Turner Road's two barriers, and a point on Blunt Park Road;
  - the Eagle Avenue gate between two roads: neither road is closed, nobody
    drives through, both sides are reachable, and a point beside it starts on
    its own side;
  - destinations past Watatic Mountain Road's locked gate and past HMS Halsted
    Drive's gate, and a start past Watatic's. With the way round removed, each
    is "no route";
  - the mask with no date, the loop planner's costs, and the Creeper Hill loop
    from the sample.
- **Through the API.** Case 1 and the reroute.
- **The deploy script** ships the table and echoes its line.

**Tests changed.** Four tests in `test_routing.py` produced 10 parametrised
failures: the squared-curve ratio, the surface-cost ratio, and the
surface-charge tests. Each subtracted two `_weights` arrays over every slot,
or summed one, and met `inf - inf` on the closed slots. None routes anywhere,
so none could have encoded a crossing (Trap 7). They now compare only finite
slots, and their claims are unchanged.

**The breakages (Trap 8).** Each rule was broken once, and each breakage made
at least one test fail:

| breakage | tests that failed |
|---|---|
| drop `vehicle` from the hierarchy | 2 |
| gates always passable | 6 |
| gates always blocking | 10 |
| fords open | 1 |
| kerbs block | 1 |
| join barriers by midpoint | 2 |
| skip the snap side rule | 7 |
| hand out the junction instead of its side's copy | 1 |
| close both edges at a barrier between them | 2 |
| leave driving through it open | 2 |
| close only when a date is given | 8 |
| no way round a gate | 4 |
| snap onto a road closed to cars | 1 |

## Deploy steps

Nothing here has been deployed. The steps:

1. **Merge to `main`**, deleting `docs/closed-roads-brief.md` in the merge, and
   push. The origin needs HTTP/1.1:
   `git -c http.version=HTTP/1.1 push origin main`.
2. **Build the table in the main checkout**, against the graph the box serves:

   ```bash
   .venv/bin/python pipeline/closures.py data/raw/new-england-latest.osm.pbf data/processed-ne
   ```

   Expect, among its lines:
   - `control: roads.parquet has 565,410 ways, which matches the scan`;
   - `wrote seasonal_closures.parquet (235 rows)`, a file byte-identical to the
     one already deployed;
   - `wrote closed_to_cars.parquet (1,383 rows)`.

   It takes about 70 s and 2.6 GB.
3. **Ship it.** Run `server/deploy-oracle.sh --dry-run`, then
   `server/deploy-oracle.sh`.
   - It ships the code and `closed_to_cars.parquet`, which is now on its
     `OPTIONAL` list, then restarts once.
   - After the restart it prints both router lines from the journal. Expect:

     ```
     seasonal closures: 223 edges (182.2 km, 197 ways) in 7 windows
     closed to cars: 1,093 edges (423.5 km, 530 ways, 508 barriers and fords), and no driving through 105 more barriers; 916 junctions cut off behind them
     ```

   - A line reading `closed to cars: none`, or no line at all, means the box is
     driving through gates.
   - `/api/health` keeps `"nodes": 794685`. Its `routing_slots` goes from
     801,719 to **801,927**, which is the 208 barrier copies.
4. **Smoke it on production with one request**, case 1 with the app's
   parameters. Neither arm may say "Crane Road":

   ```bash
   curl -s https://api.jameskouvlis.com/api/route -d from=42.1396268,-71.2613399 -d to=42.1311784,-72.7617144 -d pref=0.50 -d w_town=0
   ```

5. **The box's test count** rises by the 133 tests in
   `tests/test_closed_roads.py`, once the table is on the box.

The Windows laptop is not expected to serve again
(server/DEPLOY-oracle.md, "Before the laptop is next switched on"). If it ever
does, it needs `closed_to_cars.parquet` too (server/DEPLOY.md).
