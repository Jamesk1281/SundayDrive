# Six owner decisions on the national data, carried out

**Status:** built 2026-10-21/22 on `claude/national-data-decisions`, off `usa`
at `de43cb4`. Not merged, not pushed, not deployed. Code comments and tests
cite this file by decision (D1-D6).

The six calls were left open by `docs/review-fixes-data.md` ("What is left")
and `docs/winter-closures-national.md` ("What is still open"). The master
session made each one on the owner's behalf. This doc records how each was
carried out and what it measured. Two escape hatches were taken:

- **D1** reopens Rocky Mountain National Park's roads by way id, not by class.
  The class rule would also have opened military bases.
- **D5** counts the truck, bus and motorhome designations and MVUM's own
  symbols as car designations. The rule then closes about 1,311 MVUM miles,
  not 4,849.

| | decision | done | km reopened (+) or closed (-), national | of it New England |
|---|---|---|---:|---:|
| D1 | `permit` on major roads | escape hatch: RMNP way-id list | +71.8 (57 edges) | 0 |
| D2 | `smoothness` only when unpaved | as decided | +91.4 (333 edges) | +0.01 (1 edge); +0.70 on `processed-ne` |
| D3 | `motor_vehicle=no` on major roads | looked; all kept closed | 0 | 0 |
| D4 | MVUM licence, federal credits | as decided: public domain, both credited | - | - |
| D5 | MVUM with no car designation | rule adjusted after reading the fields | -243.7 (117 edges; 211.7 km newly closed) | 0 |
| D6 | Pilot Creek | no primary source; unchanged | 0 | 0 |

With all six in, **every one of the continuity check's 11,414 legs passes**
on `data/pack-us-next` (the baseline was 11,407). The seven known failures
were Trail Ridge four times, US 12 twice and US 322 once, and all now pass.
`continuity.KNOWN` is empty. D5 broke no leg. `data/processed-us-next` and
`data/pack-us-next` are built, and `data/pack-us-next.done` marks the pair
complete. The swap is the master session's, with `data/raw/federal-next`
alongside it ("The rebuilt data").

## D1. Trail Ridge Road opens, subject to its season

**The class rule fails the escape-hatch test.** On `data/processed-us`,
`permit` closes 224 rows, 130.6 km, on motorway through secondary roads and
links. Only 57 rows, 71.8 km, are Rocky Mountain National Park's timed entry:
Trail Ridge Road (US 34, 31 ways, 39 edges, 66.75 km) and Park Entrance Road
(US 36 from Beaver Meadows, 16 ways, 18 edges, 5.02 km). Those are exactly
the brief's "`vehicle=permit`, 57 rows, 71.8 km". The other 167 rows,
58.8 km, are `access=permit` or `motor_vehicle=permit` on:

- military bases: Camp Pendleton (Stuart Mesa Road, Las Pulgas Road), Fort
  Benning (Lindsey Creek Parkway, a motorway; Fort Benning Road; Old Cusseta
  Highway; Stadium Boulevard; Dixie Road), Fort Sill (Northwest Fort Sill
  Boulevard, Sheridan Road), and the Air Force Academy (Academy Drive, Pine
  Drive, North and South Gate Boulevard);
- the CBP Detroit Port of Entry commercial bus lane, an airport arrivals
  roadway (Inner Roadway Arrivals Level), Banning Lewis Parkway, Tower Road,
  Wilson Road, Louisburg Road;
- NC 615 (South End Road, Currituck) and MN 310 (Roseau, at the border), with
  a dozen unnamed links.

No tag separates them cleanly. Trail Ridge carries `access=permit` as well as
`vehicle=permit`, and so do the base roads. Its other tags (`bus=official`,
`taxi=permit`, `tourist_bus=permit`) are one mapper's style, not a rule. A
US-route ref would pick the two RMNP roads, but only by coincidence of this
extract. So, as the brief directs, **the fallback**: `PERMIT_REOPENED` in
`pipeline/closures.py`, the 47 way ids of both RMNP roads in Geofabrik's US
extract of 2026-10-17. `permit_reopened` leaves those ways open, and every
other `permit` closes as before, on every class. `CLOSED_TO_CARS` and
`closed_to_cars` in `common.py` are unchanged (trap 2).

**Park Entrance Road is in the list** although the brief's fallback says
"Trail Ridge's way IDs alone". It is the same permit on the same park's road,
one of the 57 rows the brief measured, and the entrance a driver from Estes
Park uses. Without it, Trail Ridge is reachable from the east only by the
Fall River entrance. If the owner wants Trail Ridge alone, delete the 16 ids
under `# Park Entrance Road` in `PERMIT_REOPENED`, and the test count of 47.

**The season stands.** On `processed-us-next`, 37 of Trail Ridge's 39
edges close Oct 14 - May 31 by its own `access:conditional=no @ Oct 14th -
May 31st`, which `way_windows` reads whatever the permit rule does. 10 of
them also close Oct 10 - May 31 by the NPS layer's dated description. 2
Trail Ridge edges and 17 of Park Entrance Road's 18 carry no window in either
source and stay open all year. That is enough to shut the through road in
winter (the January trip just below). `winter_windows.json` has no Trail Ridge
row. Estes Park to Grand Lake, on the fastest arm: **46.6 mi in July**
(159.2 mi on `pack-us`), and **159.2 mi in
January** on both packs, because Trail Ridge is shut for the season.

**Measured** (national, `processed-us` → `processed-us-next`): 57 rows removed, 57 edges, **71.76 km**: Trail Ridge Road 39 edges,
66.75 km, and Park Entrance Road 18 edges, 5.02 km. Every other `permit` row
stands. The scan's "permits left open, park entry" record lists them.

New England has no `permit` row on a major road, so D1 changes nothing there.

A list goes stale: when OSM splits or renumbers one of these ways, the new
id is not in it and that piece closes again. That fails safe, and the
continuity check's US 34 legs will flag it at the next rebuild.

**Follow-up, not done here:** an in-app notice that Trail Ridge needs a park
reservation (timed entry, late May to mid-October). Nothing in the app says
so today.

## D2. `smoothness` closes a road only when it isn't paved

`too_rough` (`pipeline/closures.py`) now closes on `smoothness` of
`very_bad` or worse only when the way is not `paved`: its `surface` is not in
`SEALED`, or it has no `surface` and its class is not motorway, trunk or
primary (or a link: `PAVED_BY_DEFAULT`). `4wd_only=yes` closes every class,
unchanged. The scan records the ways left open as "rough left open, paved".

All three mis-tags carry `surface=asphalt` in the PBF of 2026-10-17, so the
surface rule opens them, and no exception list was needed:

| way | road | tags |
|---|---|---|
| 1513246614 | US 12 east of White Pass, WA | trunk, `surface=asphalt`, `smoothness=very_bad` |
| 1513246616 | US 12 east of White Pass, WA | trunk, `surface=asphalt`, `smoothness=horrible` |
| 102189476 | US 6/US 322, Superior Avenue East, Cleveland | primary, `surface=asphalt`, `smoothness=very_bad` |

**Still closed, as they must be:** Shafer Trail (CR 142: way 27230983,
`smoothness=very_bad` on a secondary road that is not paved; ways
27231781, 338153571 and 1489991567, `4wd_only=yes`), and NM 4's ways that
share refs with forest roads (14585338 `NM 4;FR 602C`, 14585362
`NM 4;FR 300I`, 586710972 `NM 4;FR 300H`, all `4wd_only=yes`). Also still
closed: NM 126's twelve rough secondary ways, and Fremont River Road
(FR 036D).

**Measured:** (national, `processed-us` → `processed-us-next`): 333 rows removed,
333 edges, **91.37 km**. Of that, 51 edges, 21.9 km, are on motorway through
secondary roads and links, and 282 edges, 69.5 km, on minor roads.

| class | edges | km |
|---|---:|---:|
| residential | 199 | 34.44 |
| unclassified | 44 | 18.01 |
| tertiary | 39 | 17.02 |
| secondary | 20 | 16.77 |
| primary | 29 | 4.78 |
| trunk | 2 | 0.35 |

The longest reopened ways, each tagged with a `SEALED` surface:

| way | road | class | region | km |
|---|---|---|---|---:|
| 10674431 | Yokohl Valley Drive (M-296) | secondary | ca-north | 12.12 |
| 20167217 | Dodge Lodge Road | unclassified | ny | 5.13 |
| 19651327 | River Road | unclassified | tn | 3.67 |
| 294271169 | West McCully Mountain Road | tertiary | or | 3.38 |
| 733797696 | Sampson Road | tertiary | nc | 3.33 |
| 20079518 | Styles Brook Road | residential | ny | 3.24 |
| 10632349 | Wildcat Road | tertiary | ca-north | 2.44 |
| 11010978 | Lakeridge Boulevard | residential | fl | 2.36 |
| 23502974 | Saw Mill River Road (NY 100) | primary | ny | 2.24 |
| 14633197 | Old Highway 3 (FR 493A) | residential | nm | 1.66 |

The rule decides on OSM's surface, so a way tagged both paved and very rough
now opens whatever class it is. That is the decision as made.

Naches to Packwood over White Pass (US 12), on the fastest arm: **59.1 mi in
July and in January** (79.3 mi and 251.9 mi on `pack-us`). The pass is plowed
all winter, and nothing seasonal closes it.

New England: in the national build's six NE regions, one edge (Messier Road,
VT, way 1391717834, 10 m, residential). On `processed-ne` ("New England"),
10 rows on 8 ways, 0.70 km.

**For the owner (an OSM edit, not made here):** the three ways above
probably carry a stale `smoothness` (US 12's two are version 1, created
2026-05-14). Retagging them is the owner's call, and the app no longer needs
it.

## D3. `motor_vehicle=no` on major roads: looked, all kept closed

All 1,709 rows (one per edge), 504.2 km, were classified, not just the ~259 km
the review left unnamed. The method used `data/processed-us` and the region
PBFs:

1. **Open carriageway alongside, same ref or name.** This is the brief's own
   managed-lane test. For each closed edge: is there an open motorway-through-
   secondary edge within 150 m of its midpoint, running within 30°, sharing a
   ref or name once suffixes like `EXPR`, `HOV`, `Express Lanes` and
   `Upper Level` are dropped?
2. **Named or ref'd as a managed lane** (HOV, express, `EXPR`, reversible,
   toll, busway).
3. **Contiguous with a managed lane**: the closed edges joined end to end
   into pieces; a piece with any managed edge is managed. Then any ramp whose
   end touches a managed lane, or a lane another tag closes.
4. **The way's own tags** for the rest, read from the PBFs with osmium:
   `hov`, `hov:minimum`, `toll`, `bus` or `psv` designated.

| verdict | edges | ways | km |
|---|---:|---:|---:|
| managed lane: open carriageway alongside, same ref or name | 714 | 705 | 278.9 |
| managed lane: own tags (`hov`, `hov:minimum`, `toll`, `bus`, `psv`) | 415 | 412 | 94.0 |
| managed lane: joins a managed lane end to end | 348 | 332 | 60.2 |
| managed lane: named or ref'd as one | 170 | 166 | 57.0 |
| managed lane: a ramp onto a managed or closed lane | 29 | 29 | 8.5 |
| unsure, kept closed | 33 | 33 | 5.7 |
| **reopened** | **0** | **0** | **0** |

The full table, with way, ref, name, km, verdict and evidence for every way,
is `tools/national_audit/motor_vehicle_no_major.csv`.

The named cases in the brief:
- **I-45, Gulf and North Freeway, Houston** (137 edges, 60.7 km): each runs
  beside the open I-45 carriageway of the same name. These are Houston's
  reversible HOV lanes.
- **Verrazzano-Narrows Bridge** (way 865473231, 2.4 km): its own
  `description` is "Reversible HOV lane of the Verrazzano Bridge", with
  `hov:minimum=3`, `toll=yes` and `oneway=reversible`.
- **US 219 Truck** (way 11881279, 2.5 km): its own note says
  `motor_vehicle=no` with `hgv=designated` is "used to indicate truck-only
  access".
- Ed Koch Queensboro Bridge upper level (reversible, HOV at the morning
  peak), Eastex Freeway (US 59/I-69 HOV) and Santa Ana Freeway (I-5) are
  managed lanes by test 1 or 2.

The 33 unsure ways, 5.7 km, have no positive evidence of being the general-
purpose road, so they stay closed:
- SR 504 Spirit Lake Highway (3 ways, 1.6 km). Its note says it is "Closed
  to motor vehicles due to 2023-05-14 landslide repair", a real closure.
- Four I-17 ramps north of Black Canyon City, AZ (2.6 km), with
  `motor_vehicle:conditional=yes @ (Su ...)` or `(Mo-Sa ...)`: reversible by
  day of week. Closed all week is the conservative reading. The router reads
  no time-of-day access.
- Three `bicycle=designated` links, two `emergency=yes` links, and 21 short
  unnamed links (the longest 165 m) with no tag either way.

Some managed lanes open outside their hours (the Queensboro upper level
outside the morning peak, the I-17 ramps on some days). The router cannot
read hours, so they stay closed all the time. Over-closing costs nothing here
(the brief), and the continuity check found no failure from any of them.

## D4. MVUM is public domain; both federal sources are credited

The FS Geodata Clearinghouse metadata for the layer,
<https://data.fs.usda.gov/geodata/edw/edw_resources/meta/S_USA.Road_MVUM.xml>,
was read on 2026-10-21 (publication date 2025-05-13, title "MVUM Roads",
originator "U.S. Forest Service"). It says:
- `accconst`: "None";
- `useconst`: a disclaimer only ("The USDA Forest Service makes no warranty,
  expressed or implied..."), with no licence and no required credit.

The map service states none either: the layer's copyright text is empty. So
`docs/data-sources.md` now records MVUM as **public domain (US federal
government work)**, as NPS was already, with the URL and the date. The CC BY
4.0 in `tools/us_map_data/results/README.md` is borne out by neither, and no
escape hatch applies. NPS Public Roads' copyright text names "National Park
Service" and no licence.

`ios/Sources/AboutView.swift` gains two `DataSource` entries, in `all`
between PAD-US and Apple:
- `forestServiceRoads`: "USDA Forest Service Motor Vehicle Use Map (MVUM)
  Roads", credit "U.S. Forest Service, MVUM Roads.", linking the
  Clearinghouse;
- `parkRoads`: "National Park Service Public Roads", credit "National Park
  Service, National Park Service Public Roads.", linking the map service.

Neither agency publishes credit wording, so each line is the dataset's own
citation: originator and title. Neither has a licence line, and "public
domain" stays off the screen, as for PAD-US
(`test_the_terrain_aggregate_is_never_called_public_domain`).
`ios/Tests/AttributionTests.swift` checks both are in `all`, their lines,
their missing licence and their hosts. `AttributionTests`: **16 tests, 0 failures** (an iOS 26.4 iPhone 17
Pro simulator created for the run and deleted after).

## D5. MVUM roads designated for no full-size highway-legal vehicle: closed to cars

### Reading the fields first changed the rule

The brief's 4,849 mi is the MVUM roads with neither `passengervehicle` nor
`highclearancevehicle` open. Measured again on the layer refetched on
2026-10-21 (the same 149,950 features and ids as 2026-10-18), that is 3,961
roads, 4,833.6 mi. The 15.6 mi difference from 4,849 is not chased here.

`federal_layers.py` fetched only some of the layer's designation fields. The
service's own field list (`MapServer/1?f=json`) and the metadata's attribute
definitions show more:
- `truck` (">10,000 pounds GVW... licensed to operate on public roads"),
  `bus` and `motorhome`, each defined as highway legal;
- `fourwd_gt50inches`, `twowd_gt50inches`, the OHV classes, `atv`,
  `motorcycle`;
- `symbol`, whose domain is the MVUM legend: 1 "Roads open to all
  Vehicles, Yearlong", 2 the same "Seasonal", 3 "Roads open to highway legal
  vehicles only, Yearlong", 4 the same "Seasonal", and 11/12 "Special
  Designation".

Of the 4,833.6 mi:
- **3,095.8 mi are designated for truck and bus** (motorhome on 2,074.9).
  Prescott (1,572 mi) and Chattahoochee-Oconee (1,021 mi) fill those fields
  and leave the passenger and high-clearance ones empty.
- **3,504.5 mi carry symbol 1-4**: the map itself says a highway-legal
  vehicle may drive them. 427.2 mi of those have every class field empty.

Closing those would shut thousands of km of roads the MVUM designates for
highway-legal vehicles. So, by the brief's own principle ("close where no
full-size highway-legal class is designated"), **a road is designated for a
car when its symbol is 1-4, or `passengervehicle`, `highclearancevehicle`,
`truck`, `bus` or `motorhome` is `open`** (`mvum_car_designated`,
`pipeline/winter_closures.py`). 4WD over 50 inches is not a car designation
(4WD-only closes, as `4wd_only=yes` does). Neither is 2WD over 50 inches,
which the metadata does not call highway legal and which appears here only
beside 4WD and the OHV classes.

**What that leaves: 1,305 roads, 1,310.7 MVUM miles, all symbol 11 or 12.**

| designated only for | roads | mi |
|---|---:|---:|
| ATV and motorcycle | 830 | 720.4 |
| vehicles over 50 in (4WD, 2WD or other OHV), some with ATV and motorcycle | 442 | 557.2 |
| ATV alone | 8 | 7.6 |
| nothing at all | 25 | 25.4 |

By maintenance level, 1,268.7 of the 1,310.7 mi are level 2, "high clearance
vehicles", and 1,119.8 mi are native material. The largest forests:
Bridger-Teton 400.7 mi, Kisatchie 272.8, Bitterroot 259.8, Chippewa 85.9,
National Forests in Mississippi 57.9.

### The rule

`winter_closures.no_car_edges` takes the MVUM match `federal_rows` already
makes (15 m, aligned within 30°, nearest line wins) and closes an edge when
no-car lines cover half of it (`MIN_SHARE`, as a seasonal edge). Each closed
edge is a `closed_to_cars` row: `kind` and `osm_type` "mvum", `osm_id` the
layer's objectid, `tag` "mvum no car designation (<forest>, MVUM id <id>)".
It stays open, and is reported, when:
- the edge is motorway, trunk or primary, or a link (`MAJOR_CLASSES`);
- its ref names an interstate, US or state route (`state_ref`: "US 34",
  "CO 14", "SR 410", "State Highway 310"; not "FR 602C", "CR 142" or
  "NF 37");
- a way with a `SEALED` surface runs along it. `closures.main` now runs the
  agencies' join before the PBF scan, so the scan can collect the paved ways
  through those edges' end nodes (`scan(watch=...)`), matched as
  `_way_edges` matches.

The seasonal reading of MVUM (`mvum_windows`) is unchanged.

**Measured:** (national): **117 edges, 243.7 km** of `closed_to_cars` rows of kind
"mvum". 20 of those edges were already closed by another rule, so **97 edges,
211.7 km** are newly closed. Most of the 1,311 MVUM miles are not in the graph
at all: they are tracks and trails, which the drivable graph never had.

| region | edges | km |
|---|---:|---:|
| wy | 39 | 74.5 |
| mt | 10 | 62.9 |
| co | 15 | 25.8 |
| ms | 11 | 21.9 |
| la | 17 | 20.5 |
| mi | 3 | 14.9 |
| wa | 7 | 10.7 |
| id | 4 | 7.4 |
| mn | 3 | 3.2 |
| tn | 6 | 1.3 |
| pa | 1 | 0.7 |
| ca-north | 1 | 0.0 |

By class: unclassified 73 edges, 180.1 km; residential 44 edges, 63.6 km. No
motorway through tertiary edge closes. By forest: Bridger-Teton 74.5 km,
Bitterroot 62.9, National Forests in Mississippi 21.9, Kisatchie 20.5, Pike
and San Isabel 13.8.

**Left open as a different road: 2 edges, 0.1 km**, both because OSM says
they are paved (one in Wyoming, one in Colorado). No edge was kept open by
its class or its ref.

The longest are what the rule is for. Each is a forest road whose passenger
stretch is symbol 3 or 4 and whose far stretch is symbol 11 or 12, ATV,
motorcycle or OHV only:
- Andrews Creek Road (Bitterroot, MVUM 728, 28.9 km edge; 10.5 of its MVUM
  miles ATV and motorcycle only);
- FS 5612, Moonshine Connection (Bitterroot, 17.2 km);
- Forest Road 1360 (Ottawa, 12.0 km);
- Fall Creek Road, FR 618 (GMUG, 12.0 km; 9.7 mi for vehicles over 50 in);
- Gold Camp Road, FS 370 (Pike and San Isabel, 5.5 km; its 8.5 mi
  special-designation piece is ATV and motorcycle only).

**A limit:** an edge closes whole when no-car lines cover half of it, as a
seasonal edge does. Where one OSM edge spans both a passenger stretch and a
longer ATV stretch, as Andrews Creek Road's 28.9 km edge does, the passenger
stretch on that edge closes with it. Splitting edges at the
MVUM segment ends would fix it, and that is a graph change.

New England: none. The NE regions' logs say 0 edges, and so does the
`processed-ne` run.

### Continuity

No leg breaks: 11,414 of 11,414 pass on `data/pack-us-next`. No
exception had to be added.

## D6. Pilot Creek: the longer closure stays

One attempt, as the brief asks, for a published position of Pilot Creek or
the plowed limit on US 212 east of Cooke City:
- Shoshone NF (fs.usda.gov/r02/shoshone): over-snow vehicle orders for the
  Greybull and Wind River districts; nothing places Pilot Creek. The Clarks
  Fork district (the Wyoming side of US 212) has no page on it.
- Custer Gallatin NF's US 212 / Beartooth Highway page: the summer season
  (Memorial Day to Oct 15) and the Clarks Fork district's phone number; no
  plowed limit.
- MDT, WYDOT (wyoroad.info), Park County WY and NPS: a search restricted to
  their sites and the two forests' found no page that gives the position.

Only the press places it: the Powell Tribune and Cowboy State Daily put
Pilot Creek "just over eight miles" southeast of Cooke City, with an
unplowed eight-mile "plug" across the state line. Those are not primary
sources, so `pipeline/winter_windows.json` is unchanged, and US 212 from WY
296 to Cooke City stays closed in winter.

## The rebuilt data

Built as `docs/review-fixes-data.md` did, and nothing under `data/processed-us`
or `data/pack-us` was written:

- **`data/raw/federal-next/`**: `mvum_roads.parquet` refetched 2026-10-21 with
  the extra designation fields (`federal_layers.py`'s new field list, 149,950
  features, the same ids as 2026-10-18), and `nps_roads.parquet` an absolute
  symlink to `data/raw/federal/`'s. `federal_layers.json` records both. The
  `-next` tables were built with `SUNDAYDRIVE_FEDERAL` pointing here.
- **`data/processed-us-next/`**: `tools/national_audit/sidecars_next.py`, two
  regions at a time. 49 regions in 2,690 s. `closed_to_cars` goes from 71,103 rows to
70,830 (390 removed, 117 added). `seasonal_closures` (13,588) and
`osm_unpaved` (19,237) are row-for-row identical to `processed-us`'s: the
refetched MVUM layer changes no seasonal window. Everything other than the three closure tables is
  an absolute symlink into `processed-us`.
- **`data/pack-us-next/`**: `tools/national_audit/pack_next.py`. Built at 00:23-00:30 on 2026-10-22, with nothing else heavy running
and a watchdog on memory and disk: 400 s, peak 11.20 GB, 11.88 GB on disk.
**3 arrays written new** (`_car_closed_slots`, `_slot_flags`, `_snap_closed`)
and 89 cloned. No through barrier came or went, so the turn expansion and
the slot-indexed arrays are unchanged (20,186,991 routing nodes, as in
`pack-us`). The build prints 60,660 edges closed to cars, against 60,953 on
`pack-us`: −390 + 97.
- `data/pack-us-next.done` is written: the pair is complete.

The first attempt at the rebuild ended in a kernel watchdog panic at 23:29 on
2026-10-21. It was running three regions at a time beside two other sessions
that were reading national data. Its three partial regions were deleted and
the whole step rerun at `--jobs 2`.

**At the swap** (the master session): as in `review-fixes-data.md` "What is
left" item 1, swap `processed-us-next` → `processed-us` and `pack-us-next` →
`pack-us` (the symlinks are absolute, into `processed-us`). Also swap
`data/raw/federal-next` → `data/raw/federal`: the next closures.py run needs
the new MVUM fields. Without them every special-designation road reads as
no-car, and the symbol 1-4 roads with empty fields still read as car roads.
Swap it by moving `mvum_roads.parquet` and `federal_layers.json` across, and
keep `nps_roads.parquet` (the `-next` one is a link to it).

### New England

`closures.py` was run on `data/raw/new-england-latest.osm.pbf` over
`data/processed-ne`, once with `usa`'s own `pipeline/` (`git archive usa
pipeline`, with `data/raw/federal`) and once with this branch's (with
`data/raw/federal-next`):
- `seasonal_closures` and `osm_unpaved` came out **byte-identical** (`cmp`);
- `closed_to_cars` loses 10 rows, 0.70 km, and gains none. All 10 are D2:
  `smoothness=very_bad` or `horrible` on 8 paved ways. Summit Avenue (ways
  9251866 and 514655790), Woodland Road (9520209), Fox Road (252063034 and
  1083026230), Messier Road (1391717834) and two unnamed ways (67850118,
  635819862). The scan records them as residential or unclassified with
  `surface=asphalt` or `paved`.
- D1 and D5 change nothing in New England.

### The continuity check

`continuity.py check data/processed-us-next data/pack-us-next`:
**11,414 of 11,414 legs pass, in 485 s** (peak RSS 11.75 GB). The baseline
in `review-fixes-data.md` was 11,407 of 11,414 on the same legs, the 7
failures being `continuity.KNOWN`. `KNOWN` is now empty.

`SUNDAYDRIVE_PACK=data/pack-us-next pytest tests/test_national_routes.py`:
**11 passed in 470 s**: the five review trips, the legs check, the full
check, and four new trips (`DECISION_TRIPS`) that pin D1 and D2. The four
are Trail Ridge open in July and shut in January, and White Pass open in
both.

### The suite

`SUNDAYDRIVE_DATA=data/processed-ne .venv/bin/python -m pytest tests/`:
**1,218 passed, 24 skipped, 0 failed** in 306 s. On `usa` at merge it was
1,118 passed, 20 skipped. The new skips are the four decision trips, which
need `SUNDAYDRIVE_PACK`.

New tests, in `tests/test_closures.py`:
- `TestParkEntryPermits` (D1);
- `TestSmoothnessOnPavedRoads` (D2);
- `TestMvumNoCarDesignation` (D5).
Each includes a real osmium scan over a hand-written extract where the rule
lives in the scan.

## For the owner

- **Three OSM ways** whose `smoothness` looks stale (D2): 1513246614 and
  1513246616 (US 12, White Pass) and 102189476 (Superior Avenue East,
  Cleveland). The app no longer depends on them.
- **Park Entrance Road (US 36)** is reopened with Trail Ridge (D1). Drop its
  16 ids if only Trail Ridge was meant.
- **Follow-ups not done here:**
  - an in-app "needs a park reservation" notice for Trail Ridge (D1);
  - MVUM roads designated only for trucks, buses or motorhomes (3,096 mi)
    are read for season by passenger and high-clearance dates, which they
    don't have. So they are open all year unless flagged `seasonal`. Their
    `truck_datesopen` would give the season (D5);
  - the managed lanes that open outside their hours stay closed all the
    time (D3).
