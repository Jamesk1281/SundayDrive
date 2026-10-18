# Winter closures for park and forest roads, national

**Status:** in progress on `claude/winter-closures`, off `usa` at `6fdf137`.
Started 2026-10-18.

## Earliest honest date

**Wednesday 2026-10-21** for this branch to be ready to merge into `usa`. That
means the code, the tests and the sourced window table, with the §4 roads re-run
and the New England diff explained. It is not deployed and not pushed.

What the date rests on, measured on day one (2026-10-18):
- **Both federal sources answer and can be read by machine.** The MVUM roads
  layer (`apps.fs.usda.gov/.../EDW_MVUM_01/MapServer/1`) and NPS Public Roads
  (`mapservices.nps.gov/.../NPS_Public_Roads/MapServer/0`) both return 200 with
  their fields, and a bogus layer or service beside each returns 404. Both page
  at 2,000 records. That is about 75 pages for MVUM's 150,022 segments and 16
  for NPS's 30,374.
- **MVUM's dates are clean.** 728 of the 729 distinct
  `passengervehicle_datesopen` strings are one or more `mm/dd-mm/dd` ranges.
  Some have two ranges with a hunting-season gap (`01/01-10/11 10/22-12/31`).
  The one exception is the literal `open`, on 2 segments and 1.2 mi.
- **NPS's dates are prose,** in 95 distinct (park, description) pairs among
  the `SEASONAL = Yes` segments. They are few enough to map one by one, and each
  mapping cites the layer.
- **The work is a sourced table plus a join,** not new routing. The router
  already reads any number of windows from `seasonal_closures.parquet`.

What could move it:
1. **Operator sources for the window table.** There are about 15 roads and 10
   parks, each needing a page and an access date. If an operator page is down
   or vague, the road gets the longer window, and the doc says so.
2. **The §4 re-run needs Western graphs.** None are on this Mac, and building
   them is unit A's job. I will build small clipped graphs around each §4 road
   from Geofabrik extracts, in scratch. If `graph.py` can't run without the full
   scoring chain, the fallback is to check the join on the road's own OSM ways.
3. **The data has to be in the national build.** Unit A runs `closures.py`.
   This branch adds an input stage that fetches the two federal layers into
   `data/raw/federal/`. A national `seasonal_closures` without that directory
   is only as good as today's. `closures.py` will say so loudly; it won't fail
   silently.

Not affected by the date: the router (unit B) keeps reading the same table
format.

## Day-one findings worth knowing now

- **New England will change, with a source.** NPS marks seasonal roads in
  Acadia. Acadia has 33 segments of "winter seasonal closure December 1 -
  April 15", plus Columbus Day and Nov 15 variants. OSM leaves Acadia untagged.
  MVUM covers the White Mountain and Green Mountain National Forests. Every New
  England change will be listed with its source, as the Auto Road's will.
- **MVUM has 4,101 mi marked `seasonal` whose passenger-vehicle dates are
  `01/01-12/31`.** The passenger-vehicle field is the specific one, so those
  roads stay open to cars. The season applies to other vehicle classes.
- **MVUM has 6,070 mi with no passenger-vehicle designation.** 1,221 mi of
  it is open to high-clearance vehicles. The other 4,849 mi has no
  high-clearance designation either: 2,973 mi yearlong, 1,430 mi seasonal and
  446 mi blank. A car on such a road is a legal question, not a seasonal
  one. It is reported here, not decided here.
