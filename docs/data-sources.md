# Data sources and licences

All three sources are open, and all three require attribution in anything put in
front of a user. The app carries that attribution: a credit line pinned in the
planning sheet at every height, tapping through to a "Data sources" screen
(`ios/Sources/AboutView.swift`, asserted by `ios/Tests/AttributionTests.swift`).
**This repository is public, so it carries obligations of its own** — the app's
attribution does not reach a reader of GitHub. Two committed artifacts are
derived from OpenStreetMap and are credited where they are seen: the README's
heatmap, a Produced Work rendered by `pipeline/render.py`, carries its notice
beside the image; and `docs/route-census/census-pairs.csv`, which extracts 1,621
OSM place-node coordinates and is therefore a Derivative Database, is offered
under ODbL by [its own notice](route-census/README.md). Nothing else committed
here is derived from the data — `data/` is gitignored, and source code that
computes over a database is neither a Derivative Database nor a Produced Work
(the reasoning is in [licensing-open-questions.md](licensing-open-questions.md)
§1b). The credit strings in `AboutView.swift` are reproduced from each
licensor's own wording; change them there, not here.

| Source | Used for | Licence |
| --- | --- | --- |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) (Geofabrik extracts) | every road, street name and turn restriction | Open Database License (ODbL) 1.0 |
| [ESA WorldCover](https://esa-worldcover.org) 10 m 2021 v200 | half of `c_forest`, so present in every score | CC BY 4.0 |
| [Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) (Terrarium, AWS Open Data) | `c_relief` | an **aggregate** — see below |

The basemap the routes are drawn on is Apple's, via MapKit, which renders its own
attribution.

Two things worth knowing before touching any of this:

- **Terrain Tiles is not one dataset under one licence.** It is a mosaic of
  national elevation products, each with its own attribution, and its largest US
  upstream being public domain does *not* make the tile set public domain. The
  registry entry names
  [`tilezen/joerd`'s attribution doc](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)
  as its licence. At zoom 11 over `pipeline/elevation.py`'s `BBOX` the upstreams
  are 3DEP and SRTM (USGS), ETOPO1 (NOAA) over water, and — because the box
  reaches past the Maine border — CDEM under the **Open Government Licence –
  Canada**, which is not US-government public domain. Widening `BBOX` can pull in
  another upstream with another licence; re-read that doc's per-zoom source table
  when you do.
- **ODbL share-alike does not apply to the routes on screen, but it would apply
  to the parquets.** The drawn route is a Produced Work (ODbL §4.3): attribution
  only. `data/processed-ne/{scored_chunks,graph_edges,graph_nodes,turn_restrictions}.parquet`
  are a Derivative Database (§4.4), and *distributing those files* obliges
  offering them under ODbL. Today they only move from the author's Mac to the
  author's own serving box, which is not distribution — but an
  offline-download-this-region feature would be, and has to be designed for it.

The full reasoning, and what was checked against each licence's own text, is in
[`licensing-and-attribution-brief.md`](licensing-and-attribution-brief.md). The
three questions it left open — and the finding that ODbL is already engaged —
are answered in [`licensing-open-questions.md`](licensing-open-questions.md).
