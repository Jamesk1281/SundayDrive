# Route census — attribution and licence notice

The committed output of [`tools/route_census.py`](../../tools/route_census.py),
kept in the repository so that the numbers in
[route-distribution-study.md](../route-distribution-study.md) can be checked
without rebuilding a 2.8 GB graph.

| File | What it holds |
| --- | --- |
| `census-pairs.csv` | The 1,000 sampled origin–destination pairs, each endpoint carrying the coordinate of the OpenStreetMap place node it was drawn from |
| `census-routes.csv` | 5,192 routed results — distances, times, scores. No coordinates, names or OSM identifiers |
| `census-summary.json` | The run's parameters: seed, band sizes, weight sets, status counts |

## Attribution

Contains information from
[OpenStreetMap](https://www.openstreetmap.org/copyright), which is made
available here under the
[Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

- © OpenStreetMap contributors
- Extracts processed by Geofabrik GmbH

That is the wording the app carries; it is maintained in
`ios/Sources/AboutView.swift` (asserted by `ios/Tests/AttributionTests.swift`)
and summarised in [data-sources.md](../data-sources.md). Change it there, not
here.

## `census-pairs.csv` is offered under ODbL 1.0

The file carries the coordinates of **1,621 distinct OSM `place=*` nodes**,
copied verbatim from the source data at six decimal places, across six states.
That is a Substantial extraction on the OSM Foundation's
[substantiality guideline](https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines/Substantial_-_Guideline)
— which is the operative text, because ODbL defines "Substantial" circularly —
and ODbL §4.4(b) makes a Substantial extraction into a new database a
**Derivative Database**. So the file is hereby offered under the
[Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/),
whose URI is the notice §4.2(b) asks for. The reasoning, with the thresholds and
the code trace, is in [licensing-open-questions.md](../licensing-open-questions.md) §1b.

`census-routes.csv` and `census-summary.json` are measurements computed *from*
the database rather than Contents extracted *out of* it — Produced Works under
§4.3, which the attribution above covers. Share-alike does not reach them
(§4.5(b)).

### The alterations, in machine-readable form (§4.6)

§4.6 accepts "the method of making the alterations to the Database (such as an
algorithm)" in place of a diff. `tools/route_census.py` is that method: it is
committed, and it is deterministic from the seed recorded in
`census-summary.json` (`"seed": 20260829`) over the `place_points.parquet` that
`pipeline/extract.py` builds from a Geofabrik extract. Re-running it against the
same extract reproduces this sample.

---

This notice covers the three files in this directory. It says nothing about the
licence of the rest of the repository, which is a separate open question —
[licensing-open-questions.md](../licensing-open-questions.md) §1a.
