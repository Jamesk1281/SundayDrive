# US map data survey: result files

What `docs/us-map-data-findings.md` reports. Every file here was written by a
script in `tools/us_map_data/`, named in that document's §10, on 2026-10-11.

The figures derived from OpenStreetMap are © OpenStreetMap contributors and
available under the Open Database License (https://opendatacommons.org/licenses/odbl/).
That covers the km-weighted tag measurements, the taginfo proxies (taginfo is computed
from OSM), the seasonal-road and byway tables, and the OSM side of the MVUM and TIGER
comparisons. The other sources' figures carry those sources' terms:
- US federal data (TIGER, 3DEP, PAD-US, BLM, NPS, HPMS): public domain.
- MVUM and WorldCover: CC BY 4.0.
- State DOT layers: the terms recorded in `state_dot_layers.csv`.

Nothing here is input to the pipeline; `data/` is untouched.
