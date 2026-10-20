# Fords on major roads, and an audit of what else closes one

**Status:** built 2026-10-20 on `claude/review-fixes-data`, off `usa` at
`4f74951`. Not merged, not deployed. Code comments and tests cite this file by
its section names.

**Done:**
- the ford rule, with tests on both sides of it;
- the major-road audit;
- `data/processed-us-next/`, rebuilt and diffed against `data/processed-us`;
- `data/pack-us-next/`, built; `data/pack-us-next.done` marks it ready;
- the continuity check and the review trips, run on both packs;
- New England confirmed byte-identical;
- the suite (see "The suite").

**Left:** the swap at merge, and the owner's calls ("What is left").

## The rule

A ford on a paved motorway, trunk, primary or secondary road, or on one of their
links, is a tagging error, and it stays open. A ford on any other road, or on an
unpaved road of any class, stays closed, as before. Decided by the owner on
2026-10-20.

- `common.FORD_OPEN_CLASSES` holds the eight classes.
- `common.ford_closes(way, node)` decides. A ford closes unless the way's
  `highway` is in that set and neither the way's `surface` nor the ford node's
  own `surface` is in `score.UNPAVED`. With no way given, it closes, which is
  the old rule, so every existing caller of `barrier_closes(tags)` is unchanged.
- `barrier_closes(tags, way)` asks it for a ford node. A ford that is left open
  is then read as whatever barrier it also is: a `ford=yes` + `barrier=gate` +
  `access=no` node still closes as a gate.
- `gate_windows(tags, way)` passes the way on, so an open ford that is also a
  seasonal gate keeps its season.
- In `closures.scan`, a ford node is judged once per way it lies on, with that
  way's tags. A ford node where a primary road meets an unclassified one closes
  the unclassified way only. A `ford=yes` way is judged by its own tags.
- The scan's report gains "fords left open on paved major roads", by node or
  way and class.

What "unpaved" covers is exactly `score.UNPAVED`, the set the router avoids. A
road with no `surface` tag is not tagged unpaved, so a ford on it opens.
`tiger:cfcc` A5x does not count. None of the national opened rows has any
unpaved fraction (below), so leaving it out opened nothing unpaved.

Tests (`tests/test_closures.py`, `TestFordsOnMajorRoads`):
- every major class, paved or untagged, opens;
- every minor class, paved, untagged or gravel, closes;
- every `UNPAVED` surface on a major road closes, on the way or on the node;
- no way given closes;
- an open ford is still its barrier, and keeps its seasonal gate;
- the real osmium scan, over a hand-written extract, opens exactly the paved
  major fords. That extract has ford nodes on paved and gravel primaries, a
  residential road, a secondary with a dirt ford node, three ford ways, and a
  ford node shared by a primary and an unclassified road.

## What it changes nationally

Measured on `data/processed-us` (before) and `data/processed-us-next` (after).

**Before.** 26,292 rows of `kind` ford in `closed_to_cars`, on 18,952 edges.
Counting the 9 more rows whose tag combines `ford=yes` with another closing tag,
that is 26,301 rows on 18,957 edges. On major roads there were 525 ford rows:
- 407 edges closed outright, 1,025.6 km;
- 5 "through" rows on 2 further edges, for **409 edges and 1,027.6 km** in all.

**After.** 514 rows are removed. All of them are fords on major roads, and no row
is added:
- 402 edges, **1,001.8 km**, open outright;
- 4 through rows are gone: North Wickenburg Road (AZ) and Del Venturi Road (CA),
  2 each;
- by class, the removed rows are on secondary 328, primary 133, trunk 42,
  motorway_link 8, motorway 2 and primary_link 1;
- none of the edges they were on has any unpaved fraction.

`closed_to_cars` goes from 71,617 rows to 71,103. `seasonal_closures` (13,588
rows) and `osm_unpaved` (19,237) are frame-equal to before.

Among those opened: I-10 west of Tonopah (edges 1329618 and 1470492), US-95
(including the 44.4 km edge 3113251), US-385 north of Marathon (32.7 km),
US-62/180, CA-1, US-84 in New Mexico, US-93 and TX-163.

**Still closed on major roads: 11 ford rows.**
- 5 edges, 23.8 km, every one fully unpaved by its surface: Shafer Trail
  (CR 142, Canyonlands, 7 rows on 2 edges), NM 52, CR 75, and edge 1166414. These
  are the fords the rule exists for.
- One through row, at node 171597071 in North Carolina ("Manchester Road &
  Raefordvass Road"). The ford stands where a paved secondary edge meets a
  tertiary one. It stays closed on the tertiary way, so driving through stays
  forbidden. That is the rule as decided.

**New England has none.** `closures.py` was run on
`data/raw/new-england-latest.osm.pbf` over `data/processed-ne`, once with
`usa`'s own `pipeline/` (`git archive usa pipeline`) and once with this branch.
All three tables came out **byte-identical** (`cmp`), and the scan records no
ford left open.

`data/processed-ne`'s own `closed_to_cars.parquet` (2026-10-07) is smaller than
either run's, because it predates the safety quick-fixes of 2026-10-18. That
rerun is the safety fixes' return leg, not this change.

## What else closes a major road

`tools/national_audit/major_closures.py <processed_dir> [rows.csv]` prints this.
It covers every `closed_to_cars` and `seasonal_closures` row on a motorway through
secondary road (and their links), by kind and tag, with the 30 longest edges. It
is a report only: nothing else was changed. The figures below are from
`processed-us-next`.

### closed_to_cars: 2,459 rows, 2,378 edges, 863.0 km, and 45 through rows

| kind | rows | edges | km | through |
|---|---:|---:|---:|---:|
| way | 2,144 | 2,144 | 706.1 | 0 |
| rough | 108 | 108 | 103.3 | 0 |
| barrier | 196 | 137 | 49.7 | 44 |
| ford | 11 | 5 | 23.8 | 1 |

| tag | rows | km |
|---|---:|---:|
| `motor_vehicle=no` | 1,709 | 504.2 |
| `vehicle=permit` | 57 | 71.8 |
| `smoothness=very_bad` | 78 | 60.3 |
| `motorcar=private` | 122 | 58.9 |
| `access=permit` | 163 | 58.3 |
| `4wd_only=yes` | 29 | 42.9 |
| `ford=yes` | 11 | 23.8 |
| `barrier=gate, access=no` | 15 | 19.1 |
| `barrier=yes` | 32 | 9.7 |
| `motorcar=no` | 24 | 5.5 |
| 36 other tags | 183 | 58.6 |

Where the next mis-tag is likely to be:

- **`motor_vehicle=no`, 504.2 km.**
  - 245.4 km of it (639 edges) is named or ref'd as HOV, express, reversible or
    toll lanes. A solo driver can't use those, so closing them is right.
  - The rest is mostly unnamed carriageways and links of the same systems. Among
    them are I-45's Gulf and North Freeway in Houston (about 2 km edges), the
    Verrazzano-Narrows Bridge (2.4 km, likely its HOV level) and a US 219 Truck
    segment.
  - Worth one look, Houston first: a whole freeway carriageway with
    `motor_vehicle=no` would show as a continuity failure, and none did.
- **`vehicle=permit` on Trail Ridge Road (US 34), 71.8 km.** It is closed all year
  by the permit rule (Rocky Mountain National Park's timed entry). The owner's
  decisions leave the permit rule as it is, so it stands. The continuity check
  flags it four times. For a scenic-drive app it is one of the best-known
  drives in the country.
- **`smoothness` and `4wd_only` on major roads, 103.3 km.**
  - Some are right: Shafer Trail, and NM 4's shared refs with forest roads
    (FR 602C, FR 300H, FR 300I), which are the forest roads.
  - Two look wrong, and the continuity check found both:
    - US 12 just east of White Pass, WA: ways 1513246614 and 1513246616, a trunk
      road tagged `smoothness=very_bad` and `horrible`;
    - US 6/US 322, Superior Avenue East in Cleveland: way 102189476, 180 m,
      `smoothness=very_bad`.
- **`barrier=gate, access=no` on NM 81, 16.6 km**, is the single longest barrier
  closure. Not checked further.

### seasonal_closures: 1,765 rows, 1,290 edges, 1,902.5 km, and 28 through rows

| source | rows | edges | km | through |
|---|---:|---:|---:|---:|
| OSM way | 872 | 683 | 1,118.6 | 0 |
| NPS layer | 528 | 528 | 741.9 | 0 |
| hand table | 281 | 281 | 359.2 | 0 |
| MVUM | 39 | 37 | 87.4 | 0 |
| OSM gate | 45 | 15 | 63.4 | 28 |

The largest tags:

| tag | rows | km |
|---|---:|---:|
| `winter_service=no` | 307 | 401.9 |
| `nps park YELL` | 340 | 397.1 |
| `access:conditional` | 214 | 368.9 |
| `motor_vehicle:conditional` | 177 | 283.1 |
| `nps description` | 106 | 170.0 |
| `seasonal=summer` | 60 | 150.2 |

Then the passes table: Sonora, North Cascades, Beartooth, Ebbetts, Independence.
The longest edges are what a winter closure should be:
- Lassen Peak Highway, CA-120 Mono Mills Road, Trail Ridge Road, Tioga Road,
  CA-108, CA-180 and SR-150 Mirror Lake;
- Yellowstone's Grand Loop and entrance roads;
- Angeles Crest Highway (CA-2): two edges, 17.5 and 13.9 km, closed by a winter
  swing gate.

Nothing here closes a road in summer, which is when the continuity check runs.
So this table cannot be checked by it, and is reported only.

## The continuity check

`tools/national_audit/continuity.py` checks that every interstate and US route,
end to end and in both directions, routes along itself.

**The legs.** `legs` walks each connected piece of a ref's own edges, on the
directed graph (`oneway` as the router reads it). It takes a leg every 40-60 km
(aimed at 50) of driving along the ref, so a leg on a divided highway starts
and ends on the carriageway it drives. A walk that finds nothing ahead tries the
ref's nodes within 300 m, which is the other carriageway; where none drives on,
it steps over a gap.

- On `processed-us`: **11,414 legs on 480 refs**, with 496 gaps stepped over, in
  `tools/national_audit/legs.json`.
- Only `graph_edges.parquet` decides the legs, so one file serves before and
  after. `test_the_legs_are_the_graphs` regenerates it to prove that.

**The rule.** `check` routes each leg on the fastest arm, on 2027-07-15, so no
pass is shut for winter. A leg passes when any one of these holds:
- at least 90% of the route's km carry the ref;
- the route is at most 1.2× the leg's distance along the ref;
- the route costs no more, under the router's own prices for that request, than
  driving the ref's own path. Each of the path's edges is priced at its
  cheapest directed slot that way, and a closed edge costs infinity.

The third condition was added after the first run. The first two alone failed
345 legs that had no closure anywhere on the ref. All were US routes that the
fastest arm rightly leaves for a parallel interstate, longer and faster: US 1 in
Florida beside I-95, US 130 in New Jersey and so on. With it, a leg fails only
when the highway was cheaper but could not be driven.

`explain` lists the `closed_to_cars` rows on each failed leg's own path.

**Before, on `data/pack-us`: 11,392 of 11,414 legs pass, in 460 s.** Every one of
the 22 failures has a closure on the ref's own path:

| ref | legs | what closes it |
|---|---:|---|
| I 10, AZ | 2 | ford nodes 9525661253, 9525661254 (Tonopah) |
| US 62/180, TX | 6 | ford nodes on edges 23124501 and 23212092 |
| US 385, TX | 2 | ford nodes on edge 23306323 (32.7 km) |
| US 84, NM | 2 | ford way 219169636 |
| US 93, AZ | 2 | ford nodes 882187130, 13706626629 |
| US 95, AZ | 1 | ford nodes on edges 1205436, 1568382 |
| US 34, CO | 4 | `vehicle=permit`, Trail Ridge Road |
| US 12, WA | 2 | `smoothness` ways 1513246614, 1513246616 |
| US 322, OH | 1 | `smoothness=very_bad` way 102189476 |

That makes 15 failures from fords on paved major roads, and all of them are rows
this change removes. The other 7 are listed in `continuity.KNOWN`, with these
reasons, and `test_numbered_highways_route_along_themselves` allows those and
no others.

Eleven of the 22 found no route at all (`route_km` None): US 62/180 west of
the Guadalupes, US 93 and US 95 in Arizona, and all of Trail Ridge. Unit R's
corridor widening (its item 4) is the general fix for that.

**After, on `data/pack-us-next`: 11,407 of 11,414 legs pass, in 367 s.** The
7 that fail are exactly `continuity.KNOWN`: Trail Ridge four times, US 12
twice and US 322 once, each with its closure on the ref's own path. Every
ford failure is gone.

`tests/test_national_routes.py` is skipped unless `SUNDAYDRIVE_PACK` is set:
- the processed directory is `SUNDAYDRIVE_PACK_DATA`, or the pack's sibling with
  "processed" for "pack";
- it checks the five trips in "The trips", each at about a tenth over the
  drive along the highway;
- it checks that `legs.json` is the graph's;
- it runs the full check.

Measured on 2026-10-20:
- on `pack-us-next`, **7 passed in 418 s**;
- on `pack-us`, 6 failed: all five trips and the continuity test. Only the
  `legs.json` check passed, as it should, since the graph is the same.

## The trips

These are the fastest arm on 2027-07-15, snapped with `Router.snap` at both
ends. "Mostly" is the leading refs by miles.

| trip | `pack-us` | `pack-us-next` | mostly, after | test bound |
|---|---:|---:|---|---:|
| El Paso → Carlsbad Caverns | 308.7 mi, 276 min | **152.1 mi, 150 min** | US 62/180 | 165 |
| Needles → Blythe | 132.3 mi, 200 min | **97.2 mi, 125 min** | US 95 | 105 |
| Fort Stockton → Marathon | 80.8 mi, 105 min | **58.2 mi, 52 min** | US 385 | 64 |
| Carmel → Big Sur village | 137.1 mi, 193 min | **26.1 mi, 43 min** | CA 1 | 29 |
| Andrew Molera → Big Sur village | no route | **3.9 mi, 5 min** | CA 1 | 5 |

Before, the routes went round by I-10, US-285 and I-20 (El Paso), AZ-95 and
I-40 (Needles), US-67 and US-90 (Fort Stockton), and US-101 with a forest road
(Carmel). The review measured El Paso → Carlsbad Caverns at 253.7 mi. The
308.7 here is from these endpoints, on this date.

Andrew Molera now drives the 4-mile CA-1 road. Its start snaps 66 m from the
point given, the park entrance road.

## The rebuilt tables

`data/processed-us-next/` holds real `closed_to_cars`, `seasonal_closures` and
`osm_unpaved` parquets, plus `sidecars_report.json`, and per-region outputs and
logs under `sidecars/`. Everything else in it is an absolute symlink into
`data/processed-us`, including `state_road_class.parquet`. `state_roads.py` reads
no ford or barrier rule. Nothing under `data/processed-us` was written.

The tables come from `tools/national_audit/sidecars_next.py`, not from
`tools/national_build/sidecars.py` writing into a new directory:
- `sidecars.py` would write each region's slice of the national graph again,
  3.9 GB on a disk with about 12 GB free;
- the slices depend only on `graph_edges.parquet`, which is unchanged, so this
  reads `processed-us`'s slices and has `closures.py` write its tables to its
  own `out_dir`;
- the rows are mapped and deduplicated with `sidecars.py`'s own `remap` and its
  dedupe keys;
- 49 regions, three at a time, took 1,843 s.

That the shortcut reproduces the served build is shown two ways:
- Arizona alone, first: only its 173 major-road ford rows differ, and nothing is
  added;
- nationally: the whole difference is the 514 rows above, and the two other
  tables are frame-equal.

## The pack

**Built 2026-10-20 at about 17:15, alone on the machine:**
- 382 s, peak 11.36 GB RAM;
- 11.88 GB as `pack.py` counts it, 20,023,955 nodes and 25,849,861 edges;
- free disk went from 15 GB to 6.5 GB, and was never below 3.95 GB.

26 of its 92 arrays were written new and 66 cloned. More arrays moved than
the closures alone. Removing the four through barriers takes one routing-node
copy each out of the turn-restriction expansion (20,186,995 routing nodes in
`pack-us`, 20,186,991 here), and that shifts every slot-indexed array. That is
about 8.5 GB written.

The build printed 60,953 edges closed to cars. The router loads the pack
against `processed-us-next` (the server refuses a pack whose fingerprints
don't match), which the continuity check and the test run did.

`tools/national_audit/pack_next.py` runs `pack.py`'s own `main` with `np.save`
wrapped:
- an array equal to the one of the same name in `data/pack-us` (dtype, shape and
  every element) is written as an APFS clone of that file (`cp -c`). That takes
  no space until one copy is written to, and is otherwise an ordinary,
  independent file;
- every other array, `objects.pickle` and `manifest.json` are written as
  `pack.py` writes them.

The result is the pack `pack.py` would write, file for file. It needs only the
changed arrays' space, not about 12 GB.

The first attempt, earlier the same day, failed on memory. Unit R's national
server and its loop-limit measurement were running (about 6.6 GB), and swap
grew to 18.4 GB, which on APFS comes out of the same free space. Free disk fell
from 8.9 GB to 0.9 GB, and the watchdog stopped the build by its PID. The pack
needs the machine to itself: its 11.4 GB peak, and about 9 GB of disk for the
arrays it writes.

## What is left

1. The swap, at merge: `processed-us-next` → `processed-us`, and `pack-us-next`
   → `pack-us`. The symlinks are absolute and point into `processed-us`. Swap by
   renaming the new directory's real files into the old one, or replace the
   links with the files, before the old directory goes. `pack-us-next`'s
   clones are independent files, so deleting `pack-us` does not touch them.
2. Owner's calls, not made here:
   - Trail Ridge Road's `vehicle=permit`;
   - the two `smoothness` mis-tags (the fix is an OSM edit, or a local
     exception);
   - one look at the 259 km of `motor_vehicle=no` on major roads that isn't
     named as a managed lane.

## The suite

`SUNDAYDRIVE_DATA=data/processed-ne .venv/bin/python -m pytest tests/`: **1,046
passed, 18 skipped, 0 failed** in 254 s (`usa` was 987 passed, 13 skipped). The
five new skips are `tests/test_national_routes.py`, with no `SUNDAYDRIVE_PACK`.
