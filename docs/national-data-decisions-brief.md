# Six owner decisions on the national data, decided: carry them out

**Status:** decided, not built. Written 2026-10-21 by the master session against
`usa` at `de43cb4`. Nothing has been touched: no code, no data, and no rebuild.
The owner delegated these six calls, and each one is made below. **Your job is to
carry them out and measure them. Don't reopen them.** If a measurement shows a
decision is wrong (the escape hatch in each section), stop on that item, record
what you found and leave the code as it was. The answer goes in
**`docs/national-data-decisions.md`**, never in this brief. This brief is deleted
in the merge that brings the work back.

The six came from two documents on `usa`:
- `docs/review-fixes-data.md`, "What is left" item 2: Trail Ridge, the two
  `smoothness` mis-tags and the 259 km of `motor_vehicle=no`;
- `docs/winter-closures-national.md`, "What is still open": the MVUM licence,
  the 4,849 mi with no designation, and Pilot Creek.

---

## D1. Trail Ridge Road (US 34, RMNP) opens, subject to its season

**As measured:** `vehicle=permit` closes 57 rows, 71.8 km, all year. Almost all
of it is Trail Ridge (`review-fixes-data.md`, the closed_to_cars table, and the
continuity check's 4 US 34 legs). The permit is Rocky Mountain National Park's
timed-entry reservation. That is a reservation to enter the park, not a
restriction on the road. Closing one of the best-known scenic drives in the
country all year is wrong for this app.

**The mechanism:** `permit` is in `CLOSED_TO_CARS` (`pipeline/common.py:42`), and
`closed_to_cars` (`common.py:77`) applies it to every road class:

```python
CLOSED_TO_CARS = frozenset({"no", "private", "permit", "agricultural", "forestry",
                            "military", "emergency", "delivery", "psv", "bus"})
```

**The decision:** `permit` (from any key in `CAR_ACCESS_KEYS`) no longer closes
a way whose `highway` is motorway, trunk, primary or secondary, or a link of
one of those. On every other class it still closes. The seasonal window in
`pipeline/winter_windows.json` keeps applying, so Trail Ridge stays closed in
winter.

**Measure and record:** every way the change reopens, nationally and in New
England, with name, ref, state and km. Each one should be a park entry
reservation or a fee road. **Escape hatch:** if any reopened way is something
else (a military base road, a tribal permit road, a private estate), exclude it
by the narrowest rule that works and record why. If no class rule separates
them cleanly, fall back to reopening Trail Ridge's way IDs alone.

**Not in scope:** an in-app "needs a park reservation" notice. Record it as a
follow-up in the answer doc.

## D2. `smoothness` closes a road only when it isn't paved

**As measured:** the rough rule closes 108 rows, 103.3 km of major road. Two
of those look wrong, and the continuity check caught both:
- US 12 just east of White Pass, WA: ways 1513246614 and 1513246616, trunk,
  `smoothness=very_bad` and `horrible`;
- US 6/US 322, Superior Avenue East, Cleveland: way 102189476, 180 m,
  `smoothness=very_bad`.

Shafer Trail, and NM 4's ways that share refs with forest roads (FR 602C, FR 300H,
FR 300I), are right and must stay closed.

**The mechanism:** `too_rough` (`pipeline/closures.py:386-395`) closes on
`smoothness` with no regard to surface:

```python
smoothness = (tags.get("smoothness") or "").strip().lower()
if smoothness in ROUGH_SMOOTHNESS:
    found.append(f"smoothness={smoothness}")
```

**The decision:** `smoothness` in `ROUGH_SMOOTHNESS` closes a way unless it is
paved. Paved means `surface` is in `SEALED` (`common.py`). With no `surface`
tag, a way of class motorway, trunk or primary (or a link of one) counts as
paved. A potholed paved highway is unpleasant, but a car can drive it.
`4wd_only=yes` still closes every class, unchanged.

**Measure and record:** km reopened, nationally and in New England, and the
top ways by length. Confirm that the three wrong ways above reopen and that
Shafer Trail and the NM 4 forest-road ways stay closed. **Escape hatch:** if
the surface rule leaves either mis-tag closed or reopens Shafer or NM 4, use a
way-ID exception list for the three ways instead. Keep it beside
`ROUGH_SMOOTHNESS`, with the PBF date and a one-line reason for each ID.

**Not done here:** an OSM edit. Editing OSM is publishing and is the owner's to
do. Put the three way IDs in the answer doc so they can.

## D3. The 259 km of `motor_vehicle=no` on major roads: look, and keep closed by default

**As measured:** `motor_vehicle=no` closes 504.2 km of major road.
245.4 km of that (639 edges) is named or ref'd as HOV, express, reversible or toll
lanes, and closing those is right. The other ~259 km is mostly unnamed
carriageways and links of the same systems. Named cases are I-45's Gulf and
North Freeway in Houston (edges of about 2 km), the Verrazzano-Narrows Bridge
(2.4 km, likely its HOV level) and a US 219 Truck segment. The continuity check
found no failure, which is evidence that no whole general-purpose carriageway
is shut. `tools/national_audit/major_closures.py <processed_dir> [rows.csv]`
lists them.

**The decision:** keep a way closed when an open carriageway runs alongside it
with the same ref or name. That is a managed lane, and a solo driver can't use
it. Look at each remaining way: OSM history, its neighbours, and the agency's
own page where one exists. Reopen it only on positive evidence that it is the
general-purpose road. Reopen with a way-ID exception list, cited as in D2.
Over-closing a duplicate carriageway costs nothing. Under-closing one sends a
driver into an HOV lane.

**Measure and record:** a table of the ~259 km: way, ref, km, the verdict
(managed lane / reopened / unsure, kept closed) and the evidence for it.
"Unsure, kept closed" is an acceptable verdict.

## D4. MVUM's licence: public domain, and credit the federal sources anyway

**As measured:** `docs/data-sources.md:38` says "to confirm".
`tools/us_map_data/results/README.md` recorded CC BY 4.0, but the service states
none. NPS Public Roads, on the next line (`data-sources.md:39`), is already
recorded as "public domain (US federal government work)". MVUM is a USFS
Enterprise Data Warehouse product, a work of the same kind. `AboutView.swift`
credits OSM, WorldCover, Terrain Tiles, PAD-US and Apple. PAD-US is a public
domain USGS product and is credited anyway. Neither federal closure source is
credited.

**The decision:** read the FS Geodata Clearinghouse / EDW metadata for the MVUM
dataset once. Record its stated terms in `data-sources.md` with the date you
read them and the URL. If the metadata states no licence, record it as public
domain (US federal government work), as NPS is. Either way, add credits for
the USDA Forest Service (Motor Vehicle Use Map) and the National Park Service
(Public Roads) to `ios/Sources/AboutView.swift`, matching the existing
`DataSource` entries. If the metadata names a licence with required wording,
use that wording verbatim. `ios/Tests/AttributionTests.swift` covers this file.
Extend it.

**Escape hatch:** if the metadata names a licence that conflicts with how the
data is used (for example non-commercial or no-derivatives), stop on D4 and
report. Don't change the credits.

## D5. The 4,849 mi of MVUM road with no passenger or high-clearance designation: closed to cars

**As measured:** `winter-closures-national.md`, decision 2. 1,221 mi with no
passenger designation are read by their high-clearance dates. 4,849 mi have
neither and are left open. `mvum_windows` (`pipeline/winter_closures.py:115`)
returns `[]` for them: "no dates".

**The reasoning:** under the Travel Management Rule (36 CFR 212.51), driving a
Forest Service road is legal only for the vehicle classes the MVUM designates.
A road designated for neither passenger nor high-clearance vehicles is not
designated for a car. It is ATV, motorcycle or 4WD only, or administrative.
This is a closed-to-cars question, not a seasonal one, as the decision itself
said.

**The decision:** close those roads to cars all year, as `closed_to_cars`
rows. Use a tag such as `mvum no car designation` so they're distinguishable.
There are two exceptions. Each is a sign that the 15 m MVUM-to-OSM match
picked up a different road:
- the OSM edge is motorway, trunk or primary (or a link), or carries a US or
  state ref;
- the OSM edge is paved (`surface` in `SEALED`).

Don't close those. List them in the answer doc.

**Read the fields first.** Check the MVUM layer's other designation fields
(for example the truck, bus and 4WD-over-50-inch fields, and `symbol`) against
the service's own field list. `federal_layers.py:46-48` fetches only some of
them. If a road with neither car designation turns out to be designated for
another full-size highway-legal class, adjust the rule. The principle is to
close where no full-size highway-legal class is designated, and to treat
4WD-only as closed, consistent with `4wd_only=yes`. Record the adjustment.

**Measure and record:** km closed, nationally and per state. Re-run the
continuity check (`tools/national_audit/continuity.py`) and report any leg the
change breaks. **Escape hatch:** if a broken leg is a real public road, add it
to the exceptions with the reason.

## D6. Pilot Creek: keep the longer closure

**As measured:** `pipeline/winter_windows.json:42`. WYDOT closes US 212 from
WY 296 to Beartooth Pass. From Cooke City to Pilot Creek, 9 miles are closed
to wheeled vehicles. Pilot Creek's position is not published, so the whole of
US 212 from WY 296 to Cooke City is closed in winter.

**The decision:** keep it. Closing too much here costs a Cooke City to Cody
winter route almost nobody plans. Closing too little sends a car into a
snowmobile route. Make one attempt to find a published position for Pilot
Creek or the plowed limit: MDT, WYDOT, Park County WY, Shoshone NF or the NPS
Yellowstone road pages. If a primary source gives it, split the row there and
cite it in the `basis`. If not, change nothing and record where you looked.

---

## Traps

1. **Don't edit `data/processed-us` or `data/pack-us` in place.** They are
   live: the next deploy ships them. Build into `data/processed-us-next` and
   `data/pack-us-next` with `tools/national_audit/sidecars_next.py` and
   `pack_next.py`, exactly as `docs/review-fixes-data.md` ("The rebuilt
   tables", "The pack") did. `processed-us-next` is mostly absolute symlinks
   into `processed-us`: swapping it needs the renaming dance in that doc's
   "What is left" item 1. Leave the swap to the master session, and say in the
   answer doc that the `-next` pair is ready.
2. **Don't remove `permit` from `CLOSED_TO_CARS`** to open Trail Ridge.
   `access=permit` alone is 163 rows, 58.3 km nationally. Off major roads
   that means gated logging networks, tribal and military roads. Maine's
   checkpointed logging roads (`common.py`'s `logging_checkpoint`) show why
   that class matters. Change it by road class, as D1 says.
3. **`smoothness` with no `surface` on a track is not paved.** Only the major
   classes default to paved (D2). Defaulting every class would reopen Shafer
   Trail.
4. **After any change to `closures.py`, re-run the sidecars.** The
   national-build doc says about 22 minutes. Then re-run the continuity check
   and `tests/test_national_routes.py` against the `-next` pack. A
   `closures.py` change that only ran on New England has not been tested.
5. **The default `data/processed` is an August MA-only build.** Run the suite
   with `SUNDAYDRIVE_DATA=data/processed-ne`, or it shows phantom failures.
6. **New England moves too.** Report D1, D2 and D5's New England km
   separately. The NE suite must stay green.

## Done looks like

1. One commit (or a few) on a branch off `usa`: the rule changes in
   `pipeline/common.py` / `pipeline/closures.py` / `pipeline/winter_closures.py`
   / `pipeline/federal_layers.py` as needed, the credit in `AboutView.swift`,
   tests for each rule in `tests/test_closures.py` (and `AttributionTests` for
   D4), and the `data-sources.md` row.
2. `docs/national-data-decisions.md`: for each of D1–D6, what was done, the
   measured km (national and NE), the ways reopened or closed, and any escape
   hatch taken, with the evidence. Also the three OSM way IDs for the owner,
   and the reservation-notice follow-up.
3. `data/processed-us-next` + `data/pack-us-next` built, with
   `pack-us-next.done`. Continuity check and national route tests run against
   them, with the numbers compared with `review-fixes-data.md`'s 11,407 of
   11,414 legs.
4. The suite on `processed-ne` green. Report the passed/skipped/failed counts
   and the iOS `AttributionTests` result.
5. This brief committed with the work, and nothing appended to it.
