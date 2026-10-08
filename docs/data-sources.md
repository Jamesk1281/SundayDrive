# Data sources and licences

All three sources are open, and all three require attribution in anything put in
front of a user. The app carries that attribution: a credit line pinned in the
planning sheet at every height, tapping through to a "Data sources" screen
(`ios/Sources/AboutView.swift`, asserted by `ios/Tests/AttributionTests.swift`).
The credit strings in `AboutView.swift` are reproduced from each licensor's own
wording; change them there, not here.

**This repository is public, so it carries obligations of its own.** An earlier
version of this page said the opposite — that the repo was private and reached
nobody — and that stopped being true when it was published. What the repository
owes is recorded in [`NOTICE`](../NOTICE), and the one directory whose contents
are themselves an OpenStreetMap extraction carries ODbL terms separately: see
[`route-census/README.md`](route-census/README.md). The reasoning behind both is
in [Licensing: the open questions, answered](licensing-open-questions.md).

| Source | Used for | Licence |
| --- | --- | --- |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) (Geofabrik extracts) | every road, street name and turn restriction | Open Database License (ODbL) 1.0 |
| [ESA WorldCover](https://esa-worldcover.org) 10 m 2021 v200 | half of `c_forest`, so present in every score | CC BY 4.0 |
| [Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) (Terrarium, AWS Open Data) | `c_relief` | an **aggregate** — see below |

The basemap the routes are drawn on is Apple's, via MapKit, which renders its own
attribution.

## State road classes

Since 2026-10-07 the router also reads what four state DOTs say about their
roads, to keep routes off unmaintained, private and trail roads
(`pipeline/state_roads.py`, [`state-road-class.md`](state-road-class.md)). Only
the derived side table, `data/processed-ne/state_road_class.parquet`, reaches the
serving box; nothing from these layers is drawn or shown in the app, and the raw
snapshots stay in `data/raw/state-roads/` on the author's Mac. All were fetched
whole through each agency's ArcGIS REST endpoint on 2026-10-06.

| Source | Layer | Used for | Terms, as the agency states them |
| --- | --- | --- | --- |
| NHDOT | [Roads by Legislative Class](https://maps.dot.nh.gov/arcgis_server/rest/services/Highways/NHDOT_HIGHWAYS_Legislative_Class/MapServer/1) (`LEGIS_CLASS`), metadata created 2024-12-23 | Class VI closed, class 0 private | "provided by the State of New Hampshire and is available for public use under the State's Right-to-Know laws ... intended to be used for planning purposes only" (the layer's own metadata). No attribution requirement stated; credit "NHDOT". |
| VTrans | [Trans_RDS road centerline](https://maps.vtrans.vermont.gov/arcgis/rest/services/Layers/s1111_rds/MapServer/2) (`AOTCLASS`, `SURFACETYPE`) | Class 4 impassable, trails and discontinued roads closed; private roads; other Class 4 unpaved | No licence stated. The FGDC metadata ([TransRoad_RDS_20210531](https://vtransmaps.vermont.gov/Maps/Publications/TransRoad_RDS_20210531_metadata_FGDC.xml)) gives a warranty disclaimer only: "VCGI, VTrans and the State of Vermont make no representations of any kind ... VCGI and VTrans are not accountable for any errors or misuse of the data." Credit "Vermont Agency of Transportation". |
| MassDOT / MassGIS | [MassDOT Roads](https://services1.arcgis.com/hGdibHYSPO59RG1h/ArcGIS/rest/services/MassDOTRoads_gdb/FeatureServer/0) (`JURISDICTN`, `FACILITY`, `SURFACE_TP`) | Private roads; earth and gravel unpaved | Public domain: MassGIS states its data "can be used by anyone for any purpose", with the credit "MassGIS (Bureau of Geographic Information), Commonwealth of Massachusetts EOTSS" appreciated but not required ([About MassGIS](https://www.mass.gov/service-details/about-massgis)). |
| MaineDOT | [Private Roads](https://arcgisserver.maine.gov/arcgis/rest/services/mdot/MaineDOT_Dynamic/MapServer/915) and [ALLPUBRDS](https://arcgisserver.maine.gov/arcgis/rest/services/mdot/MaineDOT_LRS/MapServer/1) | Private roads north of 45 N; public roads only as the matching competitor | **Unresolved.** Neither layer states terms. The Maine GeoLibrary's catalog entry for MaineDOT's public roads (now offline; [medotpubrds](https://www1.maine.gov/geolib/catalog/metadata/medotpubrds.html)) said the product "is the property of MEDOT and its use is thereby restricted", and that a dataset's presence in the GeoLibrary does not by itself make it a public record. Ask MaineDOT before a release relies on it. |
| US Census Bureau | [TIGERweb States](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/0) | clipping each layer to its own state | Public domain (US federal government work). |

None of the four requires a credit in the app the way OSM, WorldCover and
Terrain Tiles do, so `AboutView.swift` is unchanged. Whether to credit them
anyway, and the Maine question, are open decisions, recorded in
[`state-road-class.md`](state-road-class.md).

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
[`licensing-and-attribution.md`](licensing-and-attribution.md). The
three questions it left open — and the finding that ODbL is already engaged —
are answered in [`licensing-open-questions.md`](licensing-open-questions.md).
