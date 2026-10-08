# State road classes: closed, private and dirt roads from state DOT data

**Status (2026-10-07): built, tested and measured; not merged and not deployed.**
Code is in `pipeline/state_roads.py`, `pipeline/router.py`, `pipeline/looper.py`,
`pipeline/common.py` and `pipeline/closures.py`. Tests are in
`tests/test_state_roads.py`, and the census tool is `tools/state_road_census.py`.
The side table, `state_road_class.parquet`, is in `data/processed-ne`.
The Maine checkpoint rule changes `closed_to_cars.parquet`. That table has
**not** been rewritten in `data/processed-ne`; see "Rebuild and deploy".

## What happened

On 2026-10-06 a test drive's scenic route turned onto a road in southwest New
Hampshire that turned to dirt and ended at a blockade. OSM has it as plain
`highway=residential` with `tiger:reviewed=no`: an unchecked 2013 TIGER import
with no surface, access or barrier tag, so nothing in the pipeline could see a
problem. NHDOT's legislative-class layer can. It has a Class VI ("not
maintained") section, 0.298 mi long, lying in graph edge 497893, and a Private
section nearby.

Where the drive went is left out on purpose. The drive traces are private, and
this repository is public, so this doc, its tests and its tools name no street
from the drive, no coordinate from a trace and no clock time. The brief that
dispatched the work quoted the trace, so it is kept out of history
([briefs.md](briefs.md)).

## The decisions

The user made these decisions; the master session added MA and ME on 2026-10-06.

| State | Closed to cars (like a locked gate) | Private: start or end only | Counts as unpaved |
| --- | --- | --- | --- |
| NH | `LEGIS_CLASS='VI'` | `LEGIS_CLASS='0'` | none (Class V dirt is a follow-up) |
| VT | `AOTCLASS=4` with `SURFACETYPE=6`; trails `AOTCLASS` 7, 70, 71; discontinued 96, 97 | `AOTCLASS` 8, 9, 89 | other `AOTCLASS=4` |
| MA | none | `JURISDICTN='H'` or `FACILITY=14` | `SURFACE_TP` 1 (earth) and 2 (gravel) |
| ME | the North Maine Woods / KI Jo-Mary checkpoints (in `closed_to_cars`, below) | every road in MaineDOT's Private Roads layer, **only north of 45° N** | none |

Two things are deliberately left alone. MA `JURISDICTN='0'` ("Unaccepted by city
or town") is 15.7% of the MA graph and mostly ordinary subdivision streets.
Maine graph roads in neither MaineDOT layer (9.4%) are not acted on.

**Decided in this session (2026-10-07).** The user left four open questions to
this session:

1. **Toll roads open to all are public.** The Mount Washington Auto Road (NHDOT
   class 0) and Mount Equinox's Skyline Drive (VTrans private) are privately
   owned, but anyone may drive them in season. They are listed in
   `OPEN_TO_ALL` and carry no label, so loops may turn round at the summit
   again; seasonal closures still govern their seasons.
2. **OSM's explicit sealed surface beats a state surface code.** This applies to
   MassDOT's earth and gravel codes only. It fixes Mt Greylock's Rockwell Road,
   which MassDOT codes gravel and OSM has as asphalt. Vermont Class 4 stays dirt
   as decided, because it is a legal class, not a surface reading. See
   "Overrides".
3. **Maine's data is kept, and MaineDOT gets asked before release.** Only a
   derived side table is used, it never leaves the author's own server, nothing
   from the layers is shown in the app, and MaineDOT publishes both layers on an
   open endpoint with no terms attached. A draft inquiry is under "Follow-ups".
4. **Remote Maine destinations keep the rule as it is.** The Daaquam detour
   turned out to be the checkpoint ban, not the private rule: the old route
   went through the Six Mile Checkpoint. A trial that cut Maine's entry charge
   to an hour changed no trip in the census, so it was reverted rather than
   weaken "never the middle" for nothing.

A private road is priced, not banned. Private is a tenth of NH and VT and is
where people live. A ban would also stop `snap` starting a car on its own
driveway, and would move a destination pin to the nearest public road, which
for a long private drive can be over a hill. None of this goes through the
scenery score or BETA, because it is about access, not beauty.

## How it works

1. **Fetch.** `python pipeline/state_roads.py fetch data/raw` snapshots every
   layer whole, public roads included, into
   `data/raw/state-roads/<state>-<layer>-<YYYYMMDD>.geojson`, along with each
   state's Census TIGERweb outline. Pages are 2000 features, ordered by OID, and
   checked against the layer's own count. The 2026-10-06 snapshots hold NH
   112,827 features, VT 78,195, MA 409,586, ME private 60,212 and ME ALLPUBRDS
   77,654. MA takes about 100 minutes; the rest take minutes.
2. **Build.** `python pipeline/state_roads.py build data/raw data/processed-ne`
   labels every graph edge, applies the overrides, and writes
   `state_road_class.parquet`: 49,801 rows. It takes about 5 to 8 minutes and
   8 GB peak.
3. **Load.** `Router` reads the table if it is present and validates its rows
   against `graph_edges.parquet`, as `ClosedToCars` does. A stale table is
   refused loudly. Then:
   - **closed** rows become `closed_to_cars` rows (`kind="state_class"`,
     `osm_type="state"`). Everything that handles a gate handles them: the
     +inf weight, the snap refusal, and `_ways_round` for what lies behind.
   - **unpaved** rows set `unpaved_frac` to 1 in `_load_unpaved`, after the
     score is settled in either graph vintage.
   - **private** rows are priced in `_weights` (see "The private rule").

   It prints `state road classes: ...` at load, flushed, and
   `server/deploy-oracle.sh` greps the journal for that line.
4. **Without the table** the router behaves exactly as before. The test
   `test_without_the_table_nothing_changes` checks the weights term by term.

## Parameters

| | Value | Why |
| --- | --- | --- |
| `SAMPLE_M` | 25 m | Samples along each edge; short enough that a 100 m run is four samples. |
| `TOLERANCE_M` | 12 m | The two datasets digitise one road independently and agree to a few metres; a parallel road is rarely nearer than 15 m. Same as the brief's measurement. |
| `MAX_BEARING_DEG` | 30° | A sample counts only for a line running the same way, so a drive crossing or leaving a road is not that road. |
| `MIN_COVERAGE` | 0.5 | An edge takes a rule carried by half its samples. |
| `MIN_RUN_M` | 100 m | A closed or private run this long labels the edge whatever its share. A route through an edge drives every metre of it, the way one barrier inside an edge closes it. The Class VI section that started this is 481 m of a 912 m edge, 53%, so it passes the share by a hair and the run rule makes it robust. |
| `THROUGH_RUN_SAMPLES` | 2 (about 50 m) | The same, on an edge that meets a public road at both ends, a connector; see "Short runs". |
| `PRIVATE_ENTRY_MIN` | 10,000 min | Charged once per turn onto private road from the main public network. A week; no detour costs that. |
| `PRIVATE_MIN_PER_KM` | 10 min/km | Once on private road, leave it by the shortest way. |
| `WHOLE_SLACK_M` | 25 m | A closed span this close to both ends closes the edge whole. |

**Nearest line, not any line.** Each sample takes the class of the *nearest*
aligned state line, and every layer is fetched with its public roads. A private
drive 8 m from a highway therefore loses the highway's samples to the
highway's own line. The brief's measurement matched only the in-scope classes,
which is how it labelled 7 km of NH motorway private.

## What it labels

After the overrides. Graph km per state are edges any state line matched. "Run only" counts edges
labelled by `MIN_RUN_M` or `THROUGH_RUN_SAMPLES` below a 50% share. Scenic means
score ≥ 7.

| State, rule, class | Edges | Graph km | Share of state | Scenic km lost | Run only |
| --- | ---: | ---: | ---: | ---: | ---: |
| **NH** (30,087 km matched; 3,724 scenic) | | | | | |
| closed: Class VI | 1,237 | 624.5 | 2.1% | 25.1 (0.7%) | 214 edges, 222.5 km |
| private: class 0 | 13,614 | 3,053.6 | 10.1% | 399.5 (10.7%) | 248 edges, 172.4 km |
| **VT** (27,207 km; 3,273 scenic) | | | | | |
| closed: Class 4 impassable | 356 | 270.2 | 1.0% | 4.1 | 133 edges, 161.6 km |
| closed: legal trail (7) | 293 | 213.2 | 0.8% | 4.0 | 73, 101.9 |
| closed: unconfirmed trail (70) | 1 | 0.5 | 0.0% | 0.0 | 1, 0.5 |
| closed: discontinued (96) | 214 | 94.4 | 0.3% | 9.6 | 47, 40.7 |
| closed: discontinued, now private (97) | 85 | 34.9 | 0.1% | 3.1 | 13, 16.5 |
| private (8) | 10,920 | 2,992.1 | 11.0% | 261.0 (8.0%) | 347, 277.3 |
| private (9) | 23 | 8.3 | 0.0% | 1.5 | 5, 3.1 |
| unpaved: other Class 4 | 1,100 | 674.3 | 2.5% | 13.6 | none |
| **MA** (65,162 km; 6,135 scenic) | | | | | |
| private: jurisdiction H | 631 | 97.5 | 0.1% | 10.2 | 2, 0.8 |
| private: private way | 2 | 0.2 | 0.0% | 0.0 | none |
| unpaved: earth | 1,208 | 298.1 | 0.5% | 5.2 | none |
| unpaved: gravel | 13,669 | 3,432.4 | 5.3% | 75.9 | none |
| **ME** (53,431 km; 3,974 scenic; private labels north of 45° N only) | | | | | |
| private: RDCLASS Local | 4,258 | 4,635.5 | 8.7% | 205.1 | 272, 485.2 |
| private: RDCLASS Private | 2,190 | 2,535.1 | 4.7% | 120.1 | 57, 148.0 |
| private: RDCLASS Gated | 2 | 1.0 | 0.0% | 0.4 | none |
| private: RDCLASS Primary | 1 | 1.1 | 0.0% | 0.0 | none |

**By road class:**
- NH closed: residential 455.7 km, unclassified 168.1, tertiary 0.7.
- NH private: residential 2,654.5, unclassified 384.5, tertiary 8.3, secondary
  5.3, living_street 1.1, primary 0.04 (South River Road, 43 m, names agree).
- VT closed: residential 531.5, unclassified 81.6.
- VT private: residential 2,908.8, unclassified 87.0, secondary 2.5, tertiary
  1.9.
- VT unpaved: residential 498.5, unclassified 175.8.
- MA private: residential 93.1, unclassified 4.6.
- MA unpaved: residential 3,495.2, unclassified 159.4, tertiary 69.3,
  secondary 6.5.
- ME private: unclassified 3,389.0, residential 2,971.9, tertiary 784.0 (the
  logging roads: Golden 154.7 km, Realty 109.7, Pinkham 75.0, Rocky Brook
  68.3, Telos 54.0 and others, all names agreeing), secondary 27.7 (Northern
  Road, ME).
- **No motorway or trunk edge is labelled in any state.**

**The ban costs about 1% of scenic km.** That is 0.7% in NH and 0.6% in VT.
Private is the large category, which is why it isn't banned.

**Unpaved adds less than it labels.** OSM already marks most of these roads
unpaved:

| | Labelled | Already unpaved in OSM | Newly unpaved |
| --- | ---: | ---: | ---: |
| VT Class 4 | 674 km | 589 km (87%) | **86 km** |
| MA gravel | 3,432 km | 2,931 km (85%) | **501 km** |
| MA earth | 298 km | 268 km (90%) | **30 km** |

So VT Class 4 is a small change, not a big one. MA added 1,334 km before the
sealed-surface override and 531 km after it.

**Maine's private layer by RDCLASS.** The layer totals, with the part north of
45° N in brackets, are:

| RDCLASS | km (north of 45° N) |
| --- | ---: |
| Private | 15,630 (5,362) |
| Local | 12,683 (6,323) |
| Gated | 42.0 (14.0) |
| Vehicular Trail | 9.1 (3.7) |
| Walkway | 7.5 (0.1) |
| Service | 5.0 (4.4) |
| Trail | 3.3 (0.9) |
| Primary | 2.8 (2.3) |
| Paper Street | 1.5 (0.0) |

Only Local, Private, Gated (1.0 km) and Primary match graph edges. The
undecided classes (Gated, Vehicular Trail, Paper Street, Trail, Walkway) are
treated as private, start or end only; Gated is the only one with graph km,
1.0. No Maine edge south of 45° N is labelled (checked: 0).

## Overrides

`apply_overrides` runs after labelling. Each override has a test, and each test
fails without its line.

| Override | Edges | km | What |
| --- | ---: | ---: | --- |
| OSM surface is sealed | 3,334 | 745.0 | MA gravel that OSM tags asphalt, paved, concrete, chipseal, sett, paving stones or cobblestone |
| OSM surface is sealed | 240 | 57.6 | MA earth, likewise |
| Open to all | 16 | 12.4 | Mount Washington Auto Road (NH) |
| Open to all | 7 | 8.6 | Skyline Drive, Mount Equinox (VT) |

- **Rockwell Road** is 10.83 km of the sealed override. Its last 0.53 km, where
  OSM itself says `unpaved`, keeps its label.
- **The sealed match** takes an edge's midpoint within 1 m of an OSM way
  carrying the surface, as `closures.py` matches ways to edges.
- **The toll roads** match by state, OSM name and a bounding box, because
  "Skyline Drive" is a common name. A same-named road elsewhere keeps its label
  (tested).
- **Stowe's Mount Mansfield toll road** is not in the graph, so it needs no
  entry.

## The false-positive guard

Matching by proximity puts private labels on public highways (Trap 1). Five
things stop it, all tested:

1. **Nearest aligned line wins** (above), within 30° of the edge's bearing.
2. **Every layer is clipped to its state's outline.** NHDOT's layer carries
   class-0 stubs that physically stand in MA, VT and ME: "MA Turn Around" on
   I-95, "Vermont Route 12", "Vermont I89 Turn Around". Unclipped, they labelled
   I-95 in Massachusetts private. In total 107 NH, 96 VT, 241 MA and 65 ME lines
   reach outside their state.
3. **Names must agree on motorway, trunk, primary, secondary and tertiary**
   (and links), by `same_name`.
   - It normalises spelling: "Brook Rd" is "Brook Road" and "Ste Aurelie" is
     "Saint Aurelie".
   - Off the major classes, one name's road-naming words may be a subset of the
     other's: "Realty Road" is "American Realty Rd".
   - On motorway, trunk and primary the words must match exactly.

   The brief asked for this on motorway, trunk and primary only. Secondary and
   tertiary were added because every false label there looked the same: a
   private stub drawn over a public road. Examples: Daniel Webster Highway vs
   "TURN LANE B755", Neponset Valley Parkway vs "WESTINGHOUSE PLAZA", VT-140
   vs "ELFIN LAKE RD".
4. **No run rule on a major road.** A motorway, trunk or primary edge is
   labelled only by its share. Before this, the connector rule labelled 1 km of
   I-93 at the Hooksett rest area (edge 800720) private. That came from 76 m of
   a ramp line named "Hooksett Rest Area Interstate 93 N", whose "93" matched
   OSM's ref "I 93".
5. **A name made only of numbers or generic words must match exactly.** "I 93"
   is not "Hooksett Rest Area Interstate 93 N", "Vermont" names no road, and
   "South Street" is "SOUTH ST" but not "North Street".

**Refused by the names: 143 edges, 65.3 km.** All but 10.5 km are in Maine.
They are logging roads whose two names differ: Blanchette Road vs "Blanchet
Rd" (26.6 km), Edmond Roy Road vs "Grande Marche Rd" (12.3), Realty Road vs
"Daaquam Rd" (9.1) and Boulevard Road vs "Thibodeau Rd" (5.8). These stay
unlabelled, which errs toward routing on them. The rest are NH interstate ramps
and turn lanes (5.8 km), MA unpaved with differing names (4.6) and slivers.

**Accepted on a named class: 417 edges, 830 km.** Nearly all are Maine logging
roads with agreeing names. The two worth knowing about are resort access roads
the state codes private: Killington Road's top stretch by the base lodge (VT 9,
2.5 km) and Burke Mountain's Mountain Road (VT 8, 1.3 km). Both are dead ends,
so start-or-end-only costs no route anything.

## Short runs

Short runs were the master session's question: a short private or Class VI
connector is exactly the shortcut a router loves. The 100 m minimum only ever
*adds* labels to the 50% share. A short private link that is its own graph
edge has about 100% share and is labelled (test
`test_a_short_private_edge_is_labelled_by_its_share`). What escapes is a
short run *inside* a longer edge.

**Runs under 100 m that still label nothing** are runs on an edge left
unlabelled or given a weaker rule. "Public both sides" means the run sits
mid-edge with public samples on either side:

| | Closed runs | Closed km | Private runs | Private km | Public both sides |
| --- | ---: | ---: | ---: | ---: | --- |
| NH | 245 | 10.8 | 500 | 20.1 | 8 closed (0.2 km), 18 private (0.6 km) |
| VT | 328 | 14.2 | 414 | 17.6 | 23 closed (0.6 km), 2 private (0.0 km) |
| MA | 1 | 0.03 | 23 | 0.6 | none |
| ME | none | | 399 | 15.9 | 15 private (0.5 km) |

**Connectors do exist, so they are exempted.** Before the exemption, 141
runs (8.9 km) were at least two samples long, on unlabelled edges that meet
another public edge at both ends. So a closed or private run of
`THROUGH_RUN_SAMPLES` (two samples, about 50 m) now labels such an edge.

**One sample is not enough.** Of the mid-edge one-sample runs, 62 of 73 were a
single 25 m sample. The longest of them lie on I-93, the Blue Star Turnpike
(I-95) and Loudon Road, where a private stub brushes a public road at a shallow
angle. Exempting those would label through roads.

## Partly closed edges

A road maintained up to the last house and Class VI beyond is often one OSM edge
for both. That covers 460 NH edges (388 km) and 525 VT edges (486 km). These
are closed with two positions, where the closed span starts and ends, which is
exactly how a barrier inside an edge is represented.

So `snap` keeps a car or a pin on the maintained part on its own side, as it
does for a gate, instead of moving it to another road. `ClosedToCars` now
tells a point closure from a whole one by `at_m` rather than by `osm_type`. For
the existing rows the two are identical; that is checked by
`TestTheTableIsRefusedWhenStale.test_a_current_table_loads` in
`tests/test_closed_roads.py`.

A destination *on* a closed stretch goes to the nearest reachable end, through
`_ways_round`, as one behind a locked gate does. Someone who lives on a Class
VI road and starts a trip there is snapped to the nearest open road.

## The private rule

The mechanism is a positive penalty in `Router._weights`, as the brief
recommended. Each private slot adds `PRIVATE_MIN_PER_KM × km`, plus
`PRIVATE_ENTRY_MIN` when the slot leaves a node on the **main public network**.
That network is the largest connected set of edges that are neither private
nor closed. The consequences:

- **A trip starting on a private road** drives out of it without paying the
  entry.
- **A trip ending on one** pays the entry once, whichever way it comes in, so
  the choice of route is unchanged.
- **A trip that could go round** pays it for going through. A week of minutes
  is never worth saving.
- **Every weight stays positive**, so Dijkstra is valid, the ALT bounds stay
  admissible (`w ≥ d_minutes` still holds), and there is no per-request graph
  surgery. `/api/loop`, the `via` resume path and every cost cache get it for
  free.
- **The ETA is real.** `_collect` reports `d_minutes`, not `w`; the test
  `test_the_eta_is_real_minutes` pins it.

**Why entries are counted from the main network.** The first version charged
an entry at any junction a public road meets. The North Maine Woods are
private road broken up by short stretches nothing labels: OSM-only roads, and
names the guard refused. Each counted as a public road, so driving past one
was a fresh entry, and Dijkstra minimised the *number* of entries before
anything else. A census trip from Aroostook to Daaquam (`100-200:041`) went
from 291 km to 636 km.

Counting from the main public network treats those pockets as private land. A
public stretch reachable only through private roads is inside the estate. The
same trip is now +132 to +150 km instead of +345. What remains is the checkpoint
ban: the old route went through the Six Mile Checkpoint on the Realty Road (see
"Route census"). The test
`test_a_public_pocket_inside_private_land_is_not_a_second_entry` pins this:
reverting to the first rule fails four tests.

**Per entry, not per edge,** so a private road's price does not depend on how
many junctions OSM gives it.

**Why not "allow only the private component touching src or dst"?** It is a
weight copy per request, and `/api/loop`, the `via` resume, the reroute path
and both looper caches would each need it. The penalty gives the same routes
whenever a public way round exists, and costs nothing per request beyond one
indexed add.

## Loops

Two changes in `looper.py`:

1. A loop never turns round at a node in `private_inside`: private road off the
   main network, pockets included. A turnaround there is a private road in the
   middle of the drive.
2. The retrace penalty is not applied to private slots. Scaling
   `PRIVATE_ENTRY_MIN` by the penalty made any other way back onto a
   home's private road worth thousands of minutes of detour.

## Maine checkpoints

`common.logging_checkpoint` closes a `barrier=toll_booth` whose operator is
"North Maine Woods" (any case), or whose name says "Checkpoint" or "Electronic
Gate". Generic `barrier=gate` nodes keep the existing rules. Ordinary toll
booths stay open (tested).

On the 2026-08-25 NE extract there are 20 such nodes. KIW and Hedgehog already
closed, through `motor_vehicle=permit`. With the rule, 19 close something:
- 14 stand inside an edge and close it;
- 5 stand between two edges, where driving through is forbidden.

Caribou Checkpoint (9590438638) closes nothing: it stands where
`join_closed_to_cars` leaves a barrier alone. The rule adds 20 rows to `closed_to_cars.parquet`, and changes
nothing else in that table.

**The networks leak.** Measured by reachability from the main network, with all
closures and the state table:

| Road | In graph | Newly unreachable | Still reachable |
| --- | ---: | ---: | ---: |
| Golden Road | 154.7 km | 0 | 154.7 |
| Telos Road | 54.0 | 0 | 54.0 |
| Katahdin Iron Works Road | 43.7 | 0 (20.3 already cut off by `permit`) | 23.3 |
| Jo Mary Road | 32.2 | 23.2 | 9.0 |
| Realty Road | 125.8 | 0 | 125.8 |
| Pinkham Road | 85.2 | 0 | 85.2 |
| Rocky Brook Road | 68.4 | 0 | 68.4 |

The ungated ways in, from routing to them:
- Millinocket to the Golden Road via Baxter Park Road. This is real: there is
  no checkpoint on the Golden Road's east end.
- Greenville via Lily Bay Road and Sias Hill Road.
- Rockwood via the Northern Road and South Branch Access Road.
- Aroostook to the Realty Road via Rocky Brook Road and Carr Pond Road.

In all, the checkpoints and Class VI cut off 1,221 km that a route could reach
before. 1,086 km of that is the closed roads themselves, and only 70.3 km is
north of 45° N.

**So the checkpoints do not seal the networks, and nothing here silently relies
on that.** Routes are kept out of the woods by the private rule: north of
45° N, MaineDOT calls the logging roads private, so a route only goes there to
start or end there. A destination inside the woods still routes, by an ungated
way, which is the honest answer when the map has one.

## The case that started this

Replayed between two points the suite already uses (Warren village in
`tests/test_closures.py`, `NEEDHAM_KERB` in `tests/test_routing.py`), at pref
0.5 with the app's weights. That trip drives edge 497893 without the table, as
the test drive did.

| | km | Edge 497893 (Class VI) |
| --- | ---: | --- |
| Before | 298.4 | driven |
| After | 298.7 | not driven; no closed or private road anywhere |

The test drive's own request, replayed from its trace, came out the same way:
307.3 to 307.6 km, +0.5 min, with no closed or private edge.
`TestTheRealGraph.test_the_case_no_longer_drives_the_class_vi_road` asserts it
from the public points.

## Route census

`tools/state_road_census.py` routed 831 trips on today's `data/processed-ne`
and on it with the new tables:
- every pair in `tools/e2e_od_pairs.json` at pref 0 and 0.5;
- its 20 loops;
- 400 town-to-town trips drawn as `tools/route_census.py` draws them (50 per
  band, seed 20261007, prefs 0 and 0.5);
- the Class VI case. The census in this doc ran it from the test drive's own
  request; the committed tool replays it from the public points above.

All trips used the app's weights, on a July day. Every trip routed both times:
none lost, none gained.

| | Trips | Changed | Median change | Max change |
| --- | ---: | ---: | --- | --- |
| all | 831 | 30 (3.6%) | +0.04 km, +0.10 min | +150.1 km, +192.5 min |
| e2e | 410 | 5 (1.2%) | +0.05 km, +0.06 min | +0.4 km, +0.8 min |
| census | 400 | 18 (4.5%) | +0.04 km, +0.10 min | +150.1 km, +192.5 min |
| loops | 20 | 6 | -0.15 km | +11.5 km, +14.7 min |
| the case | 1 | 1 | +0.29 km, +0.5 min | |

Of the 30 changed trips, the 90th percentile is +11.1 km and +10.3 min, with
the two Daaquam trips and the Stowe loop at the top. 16 of them drove a closed
road or private road mid-route before, and 12 drove a newly unpaved road.

| Exposure over all 831 | Before | After |
| --- | --- | --- |
| Closed roads driven | 7 trips, 6.55 km | **0** |
| Private road in the middle | 10 trips, 113.65 km | 2 trips, 130.0 km (one trip, both prefs) |
| Newly-unpaved roads driven | 49 trips, 37.9 km | 42 trips, 30.5 km |

**The two outliers, both looked at:**

- **`100-200:041`, Aroostook to Daaquam on the Quebec border, 291 → 424 km
  (+132 km at pref 0, +150 at 0.5).** The destination is deep in the North
  Maine Woods. The old route went through the Six Mile Checkpoint on the Realty
  Road, which is now closed. The new route goes round to an ungated way in at
  Rockwood and the Northern Road. In practice a driver pays at the checkpoint
  and drives through, which the ban was decided against. "Private in the
  middle" still reads 65 km for it, because the metric counts the woods'
  unlabelled pockets as public.
- **`loop-015`, 40 km from Stowe: 38.9 → 50.4 km.** Neither loop drives a
  labelled road. Excluding the 103 turnarounds on private road (of 373
  candidates near Stowe) changed which candidates the planner samples, and
  this sample builds a worse loop; without the filter it is 38.9 again. It is a
  sampling regression in one loop of 20, worth fixing in the planner rather
  than here.

The other five changed loops each drove a private or closed road before and
none after: Northampton (Bayon Drive), Concord (West Joppa Road, closed),
Hanover (Tuck Drive), Brattleboro (Old Northfield Road, closed) and North
Conway.

## Tests

`tests/test_state_roads.py` holds 83 tests. The whole backend suite is 708
passed and 3 skipped on today's `data/processed-ne` without the table (main's
630 plus 78 new; the 3 skips are the real-graph tests below). With the table
and the checkpoint closures loaded, every test passes, after four existing
tests were taught about the table:
- `test_the_router_loaded_all_of_it` counts the state-closed edges too;
- `test_pref_curve_shapes_the_scenery_cost` leaves out the private slots,
  whose charge is flat in pref like the surface cost's;
- `test_a_modern_graph_is_taken_as_given` runs without the overlay. It also
  caught a real bug: the overlay indexed by position, not row label, on a
  slice of the edges;
- `test_a_loop_cached_in_july_is_not_served_in_january` now uses a 60 km
  loop. Its 80 km Jefferson loop stopped crossing a seasonal road once private
  turnarounds were excluded, the same sampling effect as Stowe's.

**Synthetic, run anywhere:**
- the rules, class by class;
- the names;
- the labelling: the motorway beside a private drive, the major-road name
  check, the crossing road, the 53% closed edge and its span, the short
  run, the connector, the one-sample connector, I-93 at Hooksett, and Maine's
  45° N limit;
- the overrides: the toll roads by name and place, and a sealed OSM surface
  beating MassDOT but not VT Class 4;
- the loader's stale-table refusal, and whole versus two-barrier closed rows;
- the checkpoints;
- a toy graph Router: through-traffic avoids private, a trip ending or starting
  on private routes, a public pocket is not a second entry, the ETA is real,
  the entry is charged once per entry, a closed road is never routed, VT
  Class 4 counts as dirt, loops don't turn inside, and without the table
  nothing changes.

**Against the built graph:** no tertiary-or-above label without agreeing names,
the Class VI edge closed, the case replayed, and the deploy script.

Every router mechanism was mutation-checked:
- entry M set to 0: 5 tests fail;
- the private add removed: 6;
- the unpaved override removed: 1;
- the closed union removed: 4;
- the main-network rule reverted: 4;
- the run rule allowed on majors: 1;
- the exact-name flag dropped: 1;
- either override removed: 1 each.

## Rebuild and deploy

For the master session:

1. **Merge, then rerun closures.py** into `data/processed-ne`, so the 20
   checkpoint rows go into the shipped `closed_to_cars.parquet`. That table was
   deliberately rebuilt only in a scratch copy:
   `python pipeline/closures.py data/raw/new-england-latest.osm.pbf data/processed-ne`.
2. **`state_road_class.parquet` is already in `data/processed-ne`,** built from
   the 2026-10-06 snapshots against today's graph. It needs no other change.
3. **Deploy.** `server/deploy-oracle.sh` now ships `state_road_class` (it is in
   `OPTIONAL`, with a cost line) and reports the `state road classes` line from
   the journal. Expect, at load:
   `state road classes: 31,638 private edges (13324.3 km), start or end only; 2,186 closed (1237.7 km); 15,977 unpaved (4404.8 km)`.
   `closed to cars:` then reports 3,271 edges, 2,186 of them by state road class.
4. **The phone needs no build.** Everything is server-side.
5. **A graph rebuild now also needs `state_roads.py build` rerun,** as it
   already needs `closures.py`. The table names edges by row and is refused if
   it was built against another graph.

The router loads in 51 s with everything (99 s without, measured while another
job ran, so neither number is a benchmark).

## Follow-ups and open questions

- **NH Class V unpaved, not decided.** `LEGIS_CLASS='V'` with
  `SURF_TYPE='Unpaved'` is 9,502 edges and 4,615 km of graph, 248 km of it
  scenic. Of that, 1,737 km is not already unpaved in OSM; that is what feeding
  it to `unpaved_frac` would change.
- **NH Class VII (federal)**, 122 km in the brief's measurement, is not in
  scope.
- **Ask MaineDOT before release** (decision 3). Neither layer states terms; the
  GeoLibrary catalog entry for MaineDOT's public roads called its data "the
  property of MEDOT and its use is thereby restricted" (`docs/data-sources.md`).
  If the answer is no, delete the two ME entries in `SOURCES`, rebuild, and
  Maine reverts to OSM alone. A draft, to send through MaineDOT's contact page
  for its GIS or mapping office:

  > I develop Sunday Drive, a free iPhone app for scenic drives in New England.
  > To keep its routes off private logging roads, its server reads two layers
  > from arcgisserver.maine.gov (MaineDOT_Dynamic/MapServer/915, Private Roads,
  > and MaineDOT_LRS/MapServer/1, ALLPUBRDS) and derives one flag per road
  > segment: private or not. Nothing from the layers is displayed or
  > redistributed; the flag only steers routes. May I use the layers this way,
  > and is there a credit line you would like shown?
- **Crediting the four agencies in the app** isn't required by NH, VT or MA.
  That leaves it open: `AboutView.swift` was not touched.
- **Maine logging roads the name guard refused** (Blanchette, Edmond Roy, part
  of the Realty Road and Boulevard Road, about 54 km) stay unlabelled. A
  Maine-specific alias table would label them.
- **Remote Maine destinations** (decision 4). A destination behind the
  checkpoints routes round to an ungated way in (Daaquam, +150 km). That is the
  ban as decided. If it should instead route through a checkpoint as a paying
  driver would, the fix is in `common.logging_checkpoint`, not the private
  rule.
- **Loop sampling.** Stowe's 40 km loop is now 50.4 km (see above). Excluding
  private turnarounds changes which candidates the planner samples, and here the
  sample builds a worse loop. The fix belongs in `looper.py`'s spread, not here.
- **More toll roads.** `OPEN_TO_ALL` holds the two found in the graph. Any other
  private road that its owner opens to everyone goes there, with its box.
- **Snap on a Class VI road.** A resident starting on one is snapped to the
  nearest open road, as on a gated road.
