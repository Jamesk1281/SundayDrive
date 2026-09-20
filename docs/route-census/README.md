# Route census — data, and the licence it carries

Contains information from [OpenStreetMap](https://www.openstreetmap.org/copyright),
which is made available here under the
[Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

- © OpenStreetMap contributors
- Extracts processed by Geofabrik GmbH

Those two lines are OpenStreetMap's and Geofabrik's own wording. They are
maintained in `ios/Sources/AboutView.swift`, asserted by
`ios/Tests/AttributionTests.swift`, and reproduced here and in
[`NOTICE`](../../NOTICE) so that each file is complete on its own. Change them
there, not here.

**These files are not covered by the repository's Apache-2.0 licence.** The
`LICENSE` at the repository root covers the source code. This directory carries
ODbL terms instead, for the reason set out below.

## What is here

| File | What it is | Terms |
| --- | --- | --- |
| `census-pairs.csv` | 1,000 origin/destination pairs — 1,621 distinct OpenStreetMap `place` nodes, with their coordinates | **ODbL 1.0** — a Derivative Database |
| `census-routes.csv` | the measurements for each routed arm: distance, minutes, scores. No coordinates, names or OSM identifiers | Produced Work — ODbL §4.3 notice only |
| `census-summary.json` | run parameters and aggregate counts | aggregate facts |

## Why `census-pairs.csv` carries ODbL rather than Apache-2.0

The endpoints in that file are not synthetic. `pipeline/extract.py` collects
OpenStreetMap nodes tagged `place=city|town|village|hamlet|square`, and
`tools/route_census.py` writes their latitude and longitude straight out at six
decimal places — so the file contains 1,621 OpenStreetMap features verbatim,
spanning Connecticut to northern Maine.

The OSM Foundation's
[Substantial guideline](https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines/Substantial_-_Guideline)
(endorsed by the OSMF board, 2014-06-06) treats an extraction as *not*
Substantial only if it is under 100 features, or non-systematic, or confined to
an area of up to 1,000 inhabitants. This extraction is none of those. ODbL
§4.4(b) is then explicit: "Extraction or Re-utilisation of the whole or a
Substantial part of the Contents into a new database is a Derivative Database."

So it is one, and because this repository is public, it is Publicly Used.

## Reproducing it — the §4.6 offer

ODbL §4.6 requires that recipients be offered either the whole Derivative
Database or "the method of making the alterations to the Database (such as an
algorithm)". The method is `tools/route_census.py`, which is in this repository
and is deterministic: the seed is recorded as `seed` in `census-summary.json`,
alongside the build date of the graph it ran against.

```sh
python3 tools/route_census.py --processed <path>/data/processed-ne --out-dir docs/route-census
```

`--processed` is required, and the seed defaults to the value recorded in
`census-summary.json`, so that command reproduces the same sample.

## If you reuse these files

Keep this notice with them, and keep them under ODbL 1.0 or a compatible
licence. The full reasoning, including what was measured and the options
considered, is in [`../licensing-open-questions.md`](../licensing-open-questions.md).
