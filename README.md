# Sunday Drive

Scenic-route navigation: pick a destination, get a route that's beautiful
instead of fast. Every road in the six New England states is scored for beauty
from **open geodata only** ([no Google or Apple data](docs/data-sources.md)),
a Dijkstra router trades
travel time for scenery on a single preference knob, and a native iOS app
(SwiftUI + MapKit) rides on the routing API. 236,000 km of road on a 998k-edge
graph, with live turn-by-turn navigation on a real phone.

![heatmap](docs/scenic_heatmap.png)

<sub>Contains information from [OpenStreetMap](https://www.openstreetmap.org/copyright),
which is made available under the
[Open Database License](https://opendatacommons.org/licenses/odbl/1-0/).</sub>

<!-- docs/ holds committed showcase images (out/ is gitignored build output;
     referencing it here would render a broken image on GitHub). Refresh with:
     sips -Z 1800 out/scenic_heatmap.png --out docs/scenic_heatmap.png
     The credit line above is required: the image is a Produced Work rendered
     from OSM geometry by pipeline/render.py, and ODbL §4.3 wants the notice
     where a reader sees it, not one link away. Keep it with the image. -->

## Both claims are measured

Every test drive recorded itself, so it produced numbers rather than
impressions. Recording and the scenery buttons are switched off for launch
(`DriveTrace.isEnabled` in `ios/Sources/DriveTrace.swift`); flip it to record
again.

- **The ETA.** 5.7% error pooled over two recorded drives, down from 22%, once
  routes were priced at the speed each road class is really driven plus the
  signals and stop signs facing them —
  [measuring travel times](docs/measuring-travel-times.md).
- **The scenery.** Two buttons on the nav screen record what the driver thinks
  of the road they are on. Over 79 marks the score ranks a road they liked above
  one they didn't **74%** of the time, against a **63%** noise floor computed
  from those same sample sizes —
  [measuring scenery](docs/measuring-scenery.md).

## Architecture

```
OSM PBF ─┐
Terrarium tiles ─┼─> score.py ──> scored_chunks.parquet ─┐
                 │                                         ├─> graph.py ─> graph_*.parquet
                 │                                         │                     │
                 └─> elevation.py ─> relief.tif ──────────┘            router.py (Dijkstra)
                                                                               │
                                                          server/app.py (Flask API) ─> ios/ (SwiftUI app)
```

`pipeline/common.py` holds the constants shared across these stages.

## Build the data

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r pipeline/requirements.txt

# six free Geofabrik extracts, merged into one; extract.py takes a single PBF
for s in connecticut maine massachusetts new-hampshire rhode-island vermont; do
  curl -L -o "data/raw/$s-latest.osm.pbf" \
    "https://download.geofabrik.de/north-america/us/$s-latest.osm.pbf"
done
osmium merge data/raw/{connecticut,maine,massachusetts,new-hampshire,rhode-island,vermont}-latest.osm.pbf \
  -o data/raw/new-england-latest.osm.pbf

R=data/raw/new-england-latest.osm.pbf; D=data/processed-ne
.venv/bin/python pipeline/extract.py   "$R" "$D"
.venv/bin/python pipeline/elevation.py "$D" 11   # terrain relief raster
.venv/bin/python pipeline/landcover.py "$D"      # WorldCover tree cover
.venv/bin/python pipeline/score.py     "$D"      # scenic score per chunk (cached; --no-cache forces)
.venv/bin/python pipeline/render.py    "$D" out  # heatmap + regional maps
.venv/bin/python pipeline/graph.py     "$R" "$D" # routable graph
```

## Run the API

```sh
.venv/bin/python server/app.py        # dev server on http://127.0.0.1:5057
```

`/api/route` with `from=LAT,LON&to=LAT,LON&pref=0..1[&avoid_unpaved=0..2]` is
the one endpoint that matters (`/api/loop` takes `from`, `km` and `sector`).
The app sends those parameters as `POST` with an
`application/x-www-form-urlencoded` body, so a driver's coordinates never
appear in a URL
([`docs/coordinates-out-of-the-url-brief.md`](docs/coordinates-out-of-the-url-brief.md)).
`GET` with the same parameters in the query string is still accepted, for older
builds and for curl. `GET /` describes the service and doubles as a liveness
check. Hosting it behind a tunnel: [`server/DEPLOY.md`](server/DEPLOY.md).
Command-line equivalent:

```sh
.venv/bin/python pipeline/router.py data/processed-ne "42.2626,-71.8023" "42.3551,-71.0657" 0.6
```

The iOS app (`ios/`, open in Xcode) reads its backend URL from the
`SundayDriveAPIBaseURL` Info.plist key in `ios/project.yml`, overridable at
runtime with a `SUNDAYDRIVE_API` environment variable.

### Running the app on sample data

The real server needs the New England graph, several gigabytes of RAM and a
build. To *look at the app* — drag the dial, watch the ledger move, open the
scenery weights, take a drive — there is a fixture that needs none of that:

```sh
python3 tools/fake_api.py            # 127.0.0.1:5099, stdlib only, no venv
```

**Every number it returns is invented.** It is not a router and nothing it
prints is evidence of anything; see its docstring. What it does reproduce is the
behaviour the interface depends on: `strength = pref ** 2`, so the dial bites
where the real one bites; `pref == 0` returning the fastest route exactly; the
1.61x ceiling on travel time; and `w_*` actually moving kilometres between
scenery types, so the *What you like* sheet is testable.

Point the app at it one of two ways.

**In Xcode** — Product ▸ Scheme ▸ Edit Scheme ▸ Run ▸ Arguments, add an
environment variable `SUNDAYDRIVE_API` = `http://127.0.0.1:5099`, then run. This
is the one to use day to day, because the value survives every
`xcodegen generate` (the scheme is regenerated, but Xcode keeps user scheme
settings in `xcuserdata`).

**From the command line**, which needs no Xcode window:

```sh
cd ios && xcodegen generate
xcodebuild build -project SundayDrive.xcodeproj -scheme SundayDrive \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath build CODE_SIGNING_ALLOWED=NO

xcrun simctl boot 'iPhone 17 Pro'        # `simctl create` one first if there is none
xcrun simctl install booted build/Build/Products/Debug-iphonesimulator/SundayDrive.app
SIMCTL_CHILD_SUNDAYDRIVE_API=http://127.0.0.1:5099 \
  xcrun simctl launch booted app.sundaydrive
```

`SIMCTL_CHILD_` is the prefix that passes a variable *through* `simctl` into the
app; plain `--setenv` does not reach it.

**Give the simulator a location**, or *Loop*, *My Location* and the whole
driving screen have nothing to work with:

```sh
xcrun simctl location booted set 42.2809,-71.2378      # Needham, MA
```

Setting it again mid-drive is how to walk the car along a route: the arrival
card and (with `DriveTrace.isEnabled` on) the two scenery marks need the drive
to actually progress.

## Tests

```sh
.venv/bin/python -m pytest tests/       # backend: 379 tests
cd ios && xcodegen generate && xcodebuild test -project SundayDrive.xcodeproj \
  -scheme SundayDrive -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

Geometry and scoring maths run anywhere; the calibration, routing and API tests
need a built graph and skip cleanly without one — point them elsewhere with
`SUNDAYDRIVE_DATA=/path/to/processed`. The iOS suite covers what a simulator can't
exercise and a drive only tests once: where the driver is on the route, when a
maneuver has been passed, which of two overlapping reroutes wins.

## The detail

- [Roadmap](docs/roadmap.md) — what is built, and what the open items wait on
- [How the scenic score works](docs/scoring.md) — the components, the weights,
  and the three failure modes `score.py`'s calibration report exists to catch
- [Measuring travel times](docs/measuring-travel-times.md) — the speed and
  junction model, how to take a drive worth analysing, how to read the report
- [Measuring whether the roads are nice](docs/measuring-scenery.md) — the two
  buttons, the separation statistic, and the noise floor printed beside it
- [Directions accuracy](docs/directions-accuracy.md) — forbidden turns and
  missing instructions, audited over 120 random routes
- [Where the next features plug in](docs/extending.md) — a new scenery
  component, retuning the timing constants, or another region
- [Data sources and licences](docs/data-sources.md) — the three open
  sources, what each one is used for, and how the attribution the app
  carries is derived from each licensor's own wording
- [Licensing: the open questions, answered](docs/licensing-open-questions.md) —
  what the public repository owes, and what it does not

Behind those sit the measurements the constants were fitted against — the
studies, verdicts and audits that say why each number is what it is.
[`docs/README.md`](docs/README.md) indexes all of them.

## Licence

The source in this repository is licensed under the
[Apache License 2.0](LICENSE). See [`NOTICE`](NOTICE) for the attribution that
travels with it.

Two things the Apache licence does **not** cover:

- **`docs/route-census/`** is a Derivative Database under
  [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) and carries its own
  terms — see [`docs/route-census/README.md`](docs/route-census/README.md).
- **The name.** Apache-2.0 §6 grants no rights to the project's names or marks.
  The app was named **Victory Lap** on 2026-09-20 and renamed **Sunday Drive**
  on 2026-09-21 ([`docs/victory-lap-naming.md`](docs/victory-lap-naming.md),
  [`docs/sunday-drive-naming.md`](docs/sunday-drive-naming.md)); the repository,
  the Cloudflare tunnel and `docs/scenic_heatmap.png` still carry the original
  working title, and the word "scenic" remains the right one for the routing
  arm, the score and the roads themselves.
