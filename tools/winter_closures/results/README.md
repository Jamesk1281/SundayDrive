# Winter closures: acceptance results

Written by `tools/winter_closures/acceptance.py` on 2026-10-18, for
`docs/winter-closures-national.md`:

- `acceptance_west.csv`: the §4 roads on the test graph from `test_graph.py`
  (Geofabrik extracts of 2026-10-17);
- `acceptance_ne.csv`: the Auto Road and the Kancamagus on `data/processed-ne`'s
  graph.

Each row is a road, a date, whether its operator has it closed or open then, and
the km of it closed by OSM's tags alone, by every row, and all year.

The road km are derived from OpenStreetMap, © OpenStreetMap contributors, under
the Open Database License (https://opendatacommons.org/licenses/odbl/). The
closures also come from MVUM (licence to confirm: docs/data-sources.md) and NPS
Public Roads (public domain).
