# Seven driving-app features: what each would cost, and in what order

**Status: measured 2026-09-19, nothing changed.** No file in `pipeline/`,
`server/` or `ios/Sources/` was touched, no constant moved, no test edited. The
suite is exactly as it was found — **1 failed, 347 passed** against
`data/processed-ne`, with that one failure pre-existing and described in §3b.
**This document exists to be chosen from; it does not choose.**

Answers `docs/driving-app-features-brief.md`, which lands in the same commit.
Reading order: that file first. Its survey is taken as given and is not
re-derived here — every `file:line` in it was read off `main` at `378aaee`, and
the handful this study had to open for costing all held.

Four things were measured rather than estimated, and each of them changed an
answer this document would otherwise have guessed:

| measurement | what it settled |
|---|---|
| `turn:lanes` per-state census over the six-state extract | §5 — and the obvious denominator turned out to be the wrong one |
| Wire cost of a per-segment series on six real routes | §2 — the wire-format question the brief posed |
| Re-routing 30 saved requests across the one rebuild that actually happened | §3 — how much of a "saved route" survives |
| The share of served road-km inside `Region.massachusetts`, and where a six-state box centres | §7 — both halves, separately |

---

## The answer in seven sentences

1. **Lane guidance is not a feature that works in some states and not others —
   it fails in all six.** Best state, best denominator: **23.8%**. Worst:
   **4.6%**. The spread is **5.1×**, wider than `surface`'s, and the *level* is
   the finding, not the spread.
2. **The scenery profile is nearly free and the elevation profile is a
   rebuild.** They are not one feature: `c_relief` is normalised ruggedness, not
   altitude, and the serving box has no raster library to read one with.
3. **A per-edge series costs 4–9% of the already-gzipped response, or 8–17%
   with all six beauty components** — so the coarse-bucket compromise the brief
   asked to be priced is not worth its own code.
4. **Re-running a saved request reproduces the drive two times in three, and
   changes the displayed numbers three times in three.** Storing the parameters
   is storing a suggestion.
5. **The cheapest item on the list is the one nobody asked for**: `reroute()`
   throws its error away with `try?`, so "the server is gone" and "the route you
   have is still the best one" reach the driver identically — as silence.
6. **CarPlay is blocked, not expensive**, and the blockers are the four already
   in someone else's risk register.
7. **The app does not open on Massachusetts.** `Region.massachusetts` is a 2.6°
   box that already contains **52.9%** of the served network; what it hides is
   **109,502 km**, nearly all of it Maine and the north.

---

## Three decisions this document does not make

`docs/consumer-polish-brief.md` holds seven product decisions out of scope and
decides them separately. Three of the seven features below touch three of them.
**These are the owner's to make, and this document deliberately does not answer
any of them.** Each is named again in its own section.

| feature | the held-out decision | why it cannot be settled here |
|---|---|---|
| §2 | **How the scenery breakdown is presented** | The mechanism is costed below and is cheap either way. What the driver *sees* — a strip, a coloured overlay on the map line, a list of named stretches — changes only the iOS half, and the wire format measured here supports all of them. |
| §3 | **The drive-trace privacy story** | The traces already exist on disk and are already exported over a cable (`ios/project.yml:46-51`). Surfacing them *in-app* is a different promise from surfacing them *in Files.app*, and which promise the app makes is not an engineering question. |
| §7 | **The `SCENIC_REGION` / opening-region default** | Three defensible answers, and they differ in the case that matters — before location permission is granted. The measurement below prices the *consequences* of each; it does not pick. |

---

# Part 1 — the `turn:lanes` census

The brief is right that this has to come first, and right about why: `surface`
runs 90.1% in Vermont to 35.9% in Maine
(`docs/unpaved-and-urban-verdict.md` Finding 3), which made the unpaved penalty
a measurement of mapping diligence; green polygons are 3.3× thinner in Maine
than Rhode Island (`docs/geodata-sources-findings.md` §1).

## The obvious denominator is the wrong one, and it is wrong in the usual way

The natural question is "of the road where lane guidance could apply, how much
carries the tag?" — which means *multi-lane* road, which means reading OSM's
`lanes=`. Measured that way:

| | multi-lane junction approaches | with `turn:lanes` | cover |
|---|---|---|---|
| NH | 5,842 | 3,040 | **52.0%** |
| CT | 9,298 | 4,330 | 46.6% |
| RI | 3,634 | 1,275 | 35.1% |
| ME | 2,964 | 948 | 32.0% |
| VT | 1,382 | 293 | 21.2% |
| **MA** | 34,965 | 7,306 | **20.9%** |

Massachusetts last, at 21%, and by a distance. That is the wrong answer, and
the reason is the same trap one level down: **`lanes=` is itself an unevenly
mapped tag**, and it runs 14.0% of ways in Maine to **80.4%** in Massachusetts
— a **5.7× spread, wider than `surface`'s.** Massachusetts knows about 34,965
multi-lane approaches because Massachusetts is diligently mapped; New Hampshire
knows about 5,842. Dividing by a number that is itself a diligence measurement
measures diligence twice and cancels nothing.

So the headline below uses a denominator that **does not depend on `lanes=`**:
every junction approach on road of a given class. A junction is a node with
three or more road arms; an approach is a drivable way that *ends* at one. Road
class is not perfectly mapped either, but it is the axis this pipeline already
trusts everywhere (`SPEED_FACTOR`, `CLASS_ADJ`, `DRIVABLE`), which is the right
standard to hold a new measurement to.

## The census

Population is the pipeline's own notion of a road: `highway in DRIVABLE`
(`pipeline/common.py:11-16`) minus private access
(`pipeline/common.py:20`, applied as `pipeline/extract.py:175-176` applies it).
Per state, over the same Geofabrik extracts the six-state build was cut from.

"Exit cover" is the case the README names in its own words — the approach to a
grade-separated exit: a `motorway` or `trunk` way ending at a node where a
`motorway_link` or `trunk_link` begins.

| state | network km | exit approaches | **exit cover** | primary+ approaches | **primary+ cover** | secondary cover | multi-lane cover | `lanes=` tagged |
|---|---|---|---|---|---|---|---|---|
| NH | 32,133 | 931 | **22.9%** | 8,670 | **23.8%** | 16.7% | 52.0% | 35.4% |
| CT | 39,700 | 2,632 | **35.3%** | 15,000 | **20.9%** | 10.8% | 46.6% | 19.2% |
| RI | 10,882 | 838 | **35.8%** | 7,265 | **17.1%** | 7.3% | 35.1% | 18.9% |
| MA | 67,779 | 3,399 | **32.1%** | 34,854 | **15.9%** | 7.5% | 20.9% | 80.4% |
| ME | 59,969 | 623 | **17.0%** | 8,475 | **8.8%** | 4.1% | 32.0% | 14.0% |
| VT | 28,533 | 283 | **7.8%** | 4,328 | **4.6%** | 4.0% | 21.2% | 24.6% |
| **all six** | **236,270** | **8,696** | **30.6%** | **78,426** | **16.5%** | **8.6%** | **29.6%** | **45.3%** |

Spread across the six, max/min: exit **4.6×**, primary-or-better **5.1×**,
secondary **4.2×**, `lanes=` **5.7×**.

**Integrity.** The six per-state files and the single six-state extract are the
same vintage (all 2026-08-25), and the per-state sums reconcile to the merged
file to within Geofabrik's border overlap:

| | six-state sum | `new-england-latest` | ratio |
|---|---|---|---|
| network km | 238,996 | 236,270 | 1.0115 |
| drivable ways | 568,691 | 565,410 | 1.0058 |
| ways with `turn:lanes` | 17,890 | 17,858 | 1.0018 |
| exit approaches | 8,706 | 8,696 | 1.0011 |

236,270 km also matches what the README claims the build serves, independently.

**One thing the census can see and no design can fix.** `turn:lanes` is a
property of a whole way, so it can only be mapped where the way is *split* at
the junction. Across the six states, **37.6%** of multi-lane junction
incidences are a road passing *through* an unsplit junction — 34,938 of 92,947.
Those cannot carry lane guidance for that junction no matter how diligent a
mapper is, short of re-cutting the way.

## What the census means

**Three denominators give three different state rankings and one identical
verdict.** Rhode Island is best on exits and fourth on primary-or-better; New
Hampshire is the reverse; Massachusetts moves from last to mid-table depending
on which you read. The ranking is not robust. The level is:

- In the **best** state on the **most favourable** denominator, **64%** of
  motorway and trunk exit approaches have no lane data.
- In Vermont it is **92%**.
- On secondary road — where a multi-lane turn lane is common in a New England
  town centre — the six-state figure is **8.6%**.

This is not the `surface` shape, where a defensible feature was being applied
unevenly. `surface` was 36–90%: bad in Maine, genuinely usable in Vermont.
`turn:lanes` has no state where it is usable. **The honest finding is not "lane
guidance works in some states and silently does not in others" — it is that
lane guidance does not work anywhere in New England yet, and the per-state
variation is a second defect on top of the first.**

That converts §5 from an engineering question into a product one, which is
where §5 leaves it.

---

# Part 2 — the seven

Each section: what exists, what would change, cost, and what would kill it.
Costs are labelled as measured or estimated. Where a line count appears it is
an estimate and says so; where a millisecond or a kilobyte appears it was
measured on this machine against `data/processed-ne` (998,252 edges).

---

## 1. GPX export

**What exists.** Nothing, and slightly less than the brief says: the brief's own
grep (`gpx\|GPX\|ShareLink\|UIActivity` over `ios/ server/ pipeline/`) returns
**zero** matches here, not one. There is no export path, no share affordance,
and no file-writing code outside `DriveTrace`.

Everything a GPX `<trk>` needs is already decoded on the phone.
`Geometry.coordinates` (`ios/Sources/Models.swift:30-31`) is the full LineString
as `[[Double]]`, and `RouteProps.steps` (`:180`) is the maneuver list with
`lat`, `lon` and `instruction` on each (`ios/Sources/Models.swift:71-89`).

**What would change.** The brief asks server-side against client-side. The
measurement settles it.

*Server-side* (`/api/route.gpx`, or `format=gpx`) costs a second round trip and
a second pair of Dijkstras for a route the client already holds — ~196 ms per
served request, on a box that does about 5 req/s
(`server/serve.py` docstring; `docs/hosting-options-brief.md`). It also needs an
arm parameter, and it delivers a `Content-Disposition` download into an app that
has no download story.

*Client-side* costs one string builder over data already in memory, and
`ShareLink` takes it from there. No request, no server change, no new test
fixture — and it works when the network does not, which is §4's whole subject.

**Recommend client-side.** The only argument for the server is a future non-iOS
client, and there isn't one.

**Cost.** One new Swift file, no server change, no pipeline change, no rebuild.
Estimated ~80–120 lines including the XML escaping and a round-trip test. The
placement is the only non-trivial part, and it is a collision: §1 and §2 both
reach for `ios/Sources/RoutePanel.swift`, which `claude/data-attribution` owns.

**What would kill it — and it is not a technical problem.** The response is two
routes and a GPX file is one track. Exporting "the route" without saying which
is a silent wrong answer, and silent wrong answers are the failure mode this
project spends most of its comments on. The cheap fix is placement rather than
UI: put the export where an arm has *already* been chosen — beside the arm's own
summary, or on the nav screen where a route is live — rather than on the
comparison sheet where both are on screen and neither is selected.

**One limitation worth stating, because it recurs in §2.** The payload carries
no elevation, so the GPX has no `<ele>`. Some consumers (Garmin, RideWithGPS)
expect it. Fixing that is the rebuild described in §2, not a GPX change.

---

## 2. A strip showing where the good parts are

**What exists.** Aggregates only, exactly as the brief says. `Route.geojson`
(`pipeline/router.py:2047-2064`) carries `km`, `minutes`, `mean_score`,
`beautiful_km`, `beautiful_score`, `scenery_km` and `steps`. `scenery_km` is a
total per beauty type (`pipeline/router.py:1634-1641`).

The per-segment numbers are not "already on the server" in the abstract — they
are already **in the object that serialises itself**. `_collect`
(`pipeline/router.py:1204-1264`) returns a `RouteResult` holding `rows` (the
edge table in travel order), `scores[edge_rows]` (the user-weighted 0–10 score
per edge, in the same order) and `edge_minutes`. A per-segment series is
`zip(edges.length_m, scores)`. No new computation, no second walk, no second
instrument — which matters, because `_edge_scores` exists precisely to stop two
instruments disagreeing (`pipeline/router.py:976`).

**What would change, and the brief's open question answered.** The brief asks
whether to send a coarse fixed-bucket series or a per-edge array, worrying that
"an 80 km scenic route can carry several hundred edges". Measured, on six real
routes at pref 1.0 against `data/processed-ne`. Responses are gzipped in
production (`server/app.py:88-91`), so the gzip column is the wire cost:

| route | km | edges | coords | response gz | **+3 per-edge series** | **as % of gz** | +64-bucket |
|---|---|---|---|---|---|---|---|
| Harvard→Needham | 17.2 | 237 | 1,211 | 10.1 KB | **+1.0 KB** | **10.0%** | +0.1 KB |
| Needham→Wachusett | 80.2 | 411 | 3,904 | 29.8 KB | **+1.9 KB** | **6.3%** | +0.1 KB |
| Needham→Worcester | 56.7 | 401 | 3,211 | 23.9 KB | +1.9 KB | 8.1% | +0.1 KB |
| Needham→Wellesley | 5.4 | 69 | 290 | 2.6 KB | +0.3 KB | 12.8% | +0.1 KB |
| Boston→Gloucester | 53.0 | 491 | 2,677 | 21.2 KB | +2.0 KB | 9.5% | +0.1 KB |
| Needham→Burlington VT | 394.5 | 1,369 | 13,584 | 98.0 KB | **+6.1 KB** | **6.2%** | +0.1 KB |

The three series are per-edge length in metres, score to 1 dp, and `c_relief` to
3 dp — i.e. *more* than the feature needs. **The brief's worry is inverted by
the geometry it names:** Needham→Wachusett carries 3,904 coordinates against 411
edges, so the per-edge array is an order of magnitude smaller than the line it
annotates and rides along in the same gzip stream.

**So send the per-edge array.** The bucketed version saves about 1.8 KB
gzipped on a 30 KB response, and costs a resampling step on the server, a
different contract, and a permanent inability to answer "which road was that?".

The cost does not change the answer at either end of the plausible range, which
was measured rather than extrapolated — a *minimal* series (`seg_m` plus the
composite score) against a *per-beauty-type* series (`seg_m`, score, and all six
`SCENERY_BREAKDOWN` components at 2 dp), the most any presentation decision
could reasonably want:

| route | response gz | minimal | per-type (6 components) |
|---|---|---|---|
| Harvard→Needham | 10.1 KB | +0.7 KB (**6.8%**) | +1.3 KB (**13.0%**) |
| Needham→Wachusett | 29.8 KB | +1.2 KB (4.2%) | +2.5 KB (8.3%) |
| Needham→Wellesley | 2.6 KB | +0.2 KB (8.6%) | +0.4 KB (**16.9%**) |
| Needham→Burlington VT | 98.0 KB | +4.0 KB (4.1%) | +8.1 KB (8.3%) |

**4.1–8.6% minimal, 8.3–16.9% for all six components.** The worst case is the
5 km trip, where the response is small enough that anything added looks large in
percentage terms and is 0.4 KB in bytes. Nothing here is a reason to bucket.

`seg_m` is sufficient for the client to locate each segment on the line: the
route's geometry is the per-edge coordinates stitched with joins de-duplicated
(`pipeline/router.py:1267-1273`), so walking the LineString by cumulative
distance lands in the right segment without an index array.

**Cost.** Server: an estimated ~10–15 lines in `geojson()` reading arrays the
`RouteResult` already holds, plus a decode field in `ios/Sources/Models.swift`.
No pipeline change, **no rebuild, no restart** — `geojson()` is pure
serialisation. iOS: a new view, and that is the bulk of the work.

**What the elevation half actually costs, which is not the same thing.** The
brief asks "whether the same series answers elevation, since `c_relief` is
already on the edge". **It does not.** `c_relief` is *local relief* — the metres
of height variation within about 1 km of the chunk midpoint — divided by
`RELIEF_FULL = 100.0` and clipped to 0–1 (`pipeline/score.py:78-81`,
`pipeline/score.py:209-232`). It answers "is this hilly country", not "how high
am I". A driver's elevation profile needs altitude per node, and:

- it is not on the graph — `graph_nodes.parquet` is `node_id, lon, lat,
  exit_ref`, and no edge column carries it either;
- the serving box **cannot** sample `elevation.tif` at request time, by design:
  `server/requirements-serve.txt:1` and `server/DEPLOY.md:155` both say rasterio
  is deliberately not installed there.

So an elevation profile is a new pipeline column and a **full graph rebuild**
(`docs/new-england-rollout.md` Phase 2: ~5.2 GB peak, ~1.5 GB of new artifacts,
and a redeploy), against a scenery profile that is a serialisation change. They
should be costed and decided separately and this document treats them as two
items, not one.

**What would kill it.** Nothing technical. **Product decision (owner's): how the
scenery breakdown is presented.** The measurement above is deliberately
presentation-neutral — a per-edge series supports a strip, a coloured map
overlay, or a list of named stretches equally — so the server half can be built
before the decision lands without betting on it. Do not compute a second score
client-side (`pipeline/router.py:976`).

---

## 3. Saved routes and history

**What exists.** No route persistence. `UserDefaults` holds exactly three
things, all voice: the selected voice and its duration cache
(`ios/Sources/VoiceCatalogue.swift:118-119,148-149`) and the mute flag
(`ios/Sources/VoiceGuide.swift:351-352`).

Half of it is on disk already. Every drive writes an NDJSON trace to
`Documents/traces` (`ios/Sources/DriveTrace.swift:131-135`), and the header line
is deliberately self-describing: `from`, `dest`, `pref`, `weights`, `started`,
app version and API base (`ios/Sources/DriveTrace.swift:114-128`) — written so
"the exact request that produced this drive can be replayed against a rebuilt
graph months later".

**These are two features and the brief is right to insist they not be merged.**
They have different costs and, as it turns out, different degrees of honesty
available to them.

### 3a. Drive history from the traces that already exist

**Cost.** No server change, no pipeline change, no new data. A list view over
`Documents/traces` reading each file's first line, and a detail view drawing the
recorded fixes. Estimated ~200–300 lines, most of it view code, and the trace
format is already parsed once in `tests/test_trace.py` (55 tests) so the shape
is pinned.

**What would kill it. Product decision (owner's): the drive-trace privacy
story.** Today the traces are reachable only by someone holding the phone or a
cable (`ios/project.yml:46-51`). An in-app history is a different promise and
the app currently makes no privacy promise at all — there is no privacy policy
and no `PrivacyInfo.xcprivacy` (`docs/legal-and-ip-audit.md` items 4 and 6, on
`claude/data-attribution`). This is not blocked on *engineering*.

### 3b. Saved routes — and how much of one survives

The brief's trap is that re-running a saved request does not reproduce a saved
route. **That is measurable right now**, because the rebuild already happened:
`data/processed` (Massachusetts) and `data/processed-ne` (six states) both exist
in the main checkout, built 87 minutes apart on 2026-08-29 with the constants
frozen. Ten Massachusetts pairs × three `pref` settings, routed against both:

| outcome | count |
|---|---|
| Same road end to end (nothing >20 m off the other line) | **20 / 30** |
| Minor divergence (0.5–5% of length on different road) | 6 / 30 |
| **Materially different drive (≥5% on different road)** | **4 / 30** |
| **Changed `km`, `minutes` or `mean_score`** | **30 / 30** |
| Byte-identical polyline | 3 / 30 |

The worst case is not marginal. Needham→Groton at pref 0 came back **67.9 km →
70.6 km** with **36%** of the route on different roads and `mean_score` 1.95 →
1.61. Boston→Gloucester at pref 1.0 moved 13%.

**So the honest shape of the promise:**

- Storing the **request** gives back the same drive about **two times in
  three**, a recognisably different one about **one time in seven**, and
  different headline numbers **every single time**.
- Storing the **answer** (the polyline) is stable by construction, but its
  `steps` go stale against a rebuilt graph, and the moment the driver leaves it
  the reroute returns the new graph's route anyway — so a stored answer is
  reliable exactly until the first reroute.

Neither is wrong. They are different products: "take me on that drive again" and
"here is the drive I did". The first is a request; the second is already §3a.

**The suite contains a live instance of this.**
`tests/test_api.py::test_the_route_that_found_this_defect_no_longer_returns_it`
passes against `data/processed` and **fails against `data/processed-ne`** — the
build the API actually serves. It is a *benign* failure and it is not a
regression in the guard: line 170's real property (`scenic >= fastest`) holds,
and so does the parametrised property test directly below it. What broke is line
172's proxy for it, `scenic["mean_score"] == fast["mean_score"]`, which encodes
"on this pair the guard fires and the fastest route comes back". On the
six-state graph the router finds a genuinely better scenic route here — 6.79
against the fastest arm's 6.28, with 30.0 beautiful km against 21.4 — so the
guard has nothing to do. **A test pinned to a Massachusetts build's exact answer
was broken by the rebuild**, which is the same mechanism as the table above, on
the same graph, costing nothing to observe. It is pre-existing, unrelated to
this document, and out of its scope.

**One caveat, stated because it bounds the number.** These two builds differ in
*extent*, not only in vintage — `docs/new-england-rollout.md` Phase 3 predicted
scoring changes near state lines from cross-border features, and some of the
drift above is that. It is still the right experiment, because it is the rebuild
that actually happened and the one a saved route would have had to survive. A
same-extent rebuild would drift less; by how much is not measured, and
`docs/new-england-rollout.md` Phase 3 is where that comparison already lives.

**Cost (3b).** A store keyed on endpoints + `pref` + weights + `avoid_unpaved`,
plus whichever of request/answer the promise turns out to be. No server change.
Estimated ~150–250 lines. It also supplies §4's gap 2 for free — see below.

---

## 4. Offline continuation

**Offline *routing* is not on the table.** Shipping a routable subset of a
998,252-edge graph to the phone — the graph the server holds in 3.53 GB of RSS
(`docs/hosting-options-brief.md`) — is a different project by an order of
magnitude, and it is not what this feature is. That is the whole of what this
document says about it.

**What exists — the brief is right and it understates the case.** Navigation
already survives a dropped connection: the in-memory route keeps guiding, voice
keeps speaking, and the reroute cooldown was written for exactly this
(`ios/Sources/NavigationModel.swift:260-264`). `ServiceError` already
distinguishes `.offline` from `.unreachable(status)` from `.server(message)`,
with the driver-facing wording already written
(`ios/Sources/RouteService.swift:42-73`).

**And then it is thrown away.** `reroute()` calls
`ios/Sources/NavigationModel.swift:1238` and `:1241`:

```swift
reply = try? await fetchRoute(origin.coordinate, destination,
                              askedPref, weights, askedHeading)
```

`try?` discards the error. Every failure — no network, tunnel down, server
saying "no route found between those points" — collapses into `nil`, and
`RerouteOutcome.failed` (`:1208-1210`) carries no reason. So the three cases
`RouteService` went to the trouble of telling apart reach `NavigationModel` as
one case, and reach the driver as nothing at all. **This is the gap, and it is
one keyword wide.**

### Gap 1 — the driver is never told

**What would change.** A `do`/`catch` in place of the two `try?`s, carrying the
`ServiceError` into `RerouteOutcome.failed`, and a standing condition on the
model that the nav screen renders.

**Every piece of this already has a precedent in the same two files**, which is
what makes it the cheapest item on the list:

- `recordingProblem` (`ios/Sources/NavigationModel.swift:666`) is already a
  *standing condition* — "true until the trace starts working again" — which is
  exactly the shape a "no connection" indicator needs, as against
  `actionProblem` (`:638`), which is a 6-second reply to a tap. The file already
  argues, at `:630-637`, why those two must not be merged; a connection state is
  a third of the first kind.
- `NavView.swift:261` and `:272` already render both, in the one place the file
  insists on ("never above the maneuver the driver is about to miss").
- `report(_:)` (`ios/Sources/NavigationModel.swift:647-655`) is the transient
  helper, and `switchToFastest` already uses it for a refused action
  (`:1163`).

**Cost.** Two files, no server change, no pipeline change, no rebuild, no new
endpoint. Estimated ~40–60 lines including doc comments in the house style, plus
tests alongside the existing reroute tests — an estimate, like every line count
here. **This is the smallest change on the list and the only one that is a
correctness defect rather than a missing feature.**

**What would kill it.** Nothing. The one thing that would spoil it is scope
creep into the reroute logic itself — the cooldown, the movement guard, the
`awaitingJoin` latch and the backoff (`ios/Sources/NavigationModel.swift:266-310,
398-431`) are each the measured answer to a specific defect from the 2026-08-22
drives. Reading the error is orthogonal to all of them: it changes what
`.failed` *says*, not when it fires.

### Gap 2 — a cold start with no network has no route

**This is §3 wearing a different hat.** A cached last route is a saved answer,
and the store that provides one is the store in §3b. Costing it separately would
double-count. If §3b ships in its "store the answer" form, gap 2 is a launch-time
read and an empty-state; if it ships as "store the request", gap 2 is not
answered at all, because a request needs a server.

**That is a real dependency and it points at the store's design**: the offline
case is the argument for storing the answer, and §3b's drift table is the
argument against trusting it after the first reroute. Both are true at once.

### Gap 3 — MapKit tiles

Apple's, cached by Apple, blank when the cache misses. Nothing in this project
changes that, and an offline indicator that promises more than the tiles can
deliver is worse than none. This is a constraint on the *wording* of gap 1, not
a task.

---

## 5. Lane guidance

**What exists.** Nothing, anywhere: `turn:lanes` is not extracted
(`pipeline/extract.py:170-192` reads `highway`, `name`, `ref`, `scenic`,
`surface` and nothing else), not carried onto edges (the 29 columns of
`graph_edges.parquet` contain no lane field), and not in `steps()`
(`pipeline/router.py:1782-1830`). The README lists it as an open item.

**The census comes first and it is Part 1 of this document.** The number, again,
on the denominator that does not measure `lanes=` twice: **23.8% in the best
state, 4.6% in the worst, 16.5% across the six.** On the exit case the README
itself names: **35.8% best, 7.8% worst.**

**What would change, if it were built anyway.** This is the item whose
engineering cost is *also* the largest, which is worth stating so the two
arguments are not confused:

1. **`extract.py`** reads the tag onto the roads layer — small.
2. **`graph.py`** carries it through way→chunk→edge, and it is **directional**
   (`turn:lanes:forward` / `:backward`) and **ordered per lane**
   (`left|through|through;right`), so it cannot ride the same path as `surface`,
   which is a single scalar. It also has to survive the chunking that turns a
   way into edges.
3. **A full rebuild.** Unlike the unpaved work — which
   `docs/unpaved-and-urban-verdict.md` found was recoverable exactly from the
   shipped graph, "no rebuild, no 364 MB redeploy" — `turn:lanes` is not in the
   graph in any form, so it is `extract.py` + `graph.py` over the 782 MB PBF and
   a redeploy: ~5.2 GB peak RAM, ~1.5 GB of artifacts
   (`docs/new-england-rollout.md` Phase 2).
4. **`steps()`** is the subtle one. `_legs()` merges consecutive edges into one
   instruction (`pipeline/router.py:1643-1730`), so the lane hint belongs to the
   *last edge before the maneuver*, not to the leg — a leg that merges twenty
   edges must not average their lane tags or take the first one's.
5. **iOS** renders lane chevrons in the banner.

**What would kill it, and this is the finding.** The census. At 16.5%
six-state coverage, a lane strip is present on fewer than one approach in five
and absent on the rest — and **absent is indistinguishable from "no lane
restriction"** to a driver who has seen it work once. That is the failure mode
this project already has a name for: a feature that is silently wrong is worse
than one that is missing, which is the argument `switchToFastest` makes in its
own comment (`ios/Sources/NavigationModel.swift:1156-1160`).

**So the honest answer is not a cost, it is a precondition.** Lane guidance
needs either (a) a presentation that is *correct when absent* — showing lanes
only where the data exists and never implying its absence means anything — or
(b) data this project does not have. (a) is a product decision, and it is a
harder one than it sounds, because "sometimes there are chevrons" is exactly
the design that teaches a driver to trust them.

**What would change the answer.** A re-run of Part 1 against a later extract.
The recipe is at the end of this document and the run is minutes, not hours, so
this is cheap to re-ask in a year. OSM lane mapping is improving; 16.5% is a
2026-08-25 number, not a law.

---

## 6. CarPlay

**What exists.** Nothing. `ios/project.yml` declares `UIBackgroundModes:
location, audio` (`:43-45`) and no entitlements; deployment target is iOS 17
(`:4-5`).

**The brief asks for the ordering with evidence, not an engineering estimate,
and that is the right ask.** Two things were checked against primary sources:

- Apple's own CarPlay developer page offers, among its resources, a link to
  "Request CarPlay app entitlement" (developer.apple.com/carplay, read
  2026-09-19). It is **requested and granted, not enabled** — there is no
  checkbox for it in Xcode.
- The App Review Guidelines' introduction says entitlements of this kind are
  offered "for limited use cases", and names CarPlay among its examples
  (developer.apple.com/app-store/review/guidelines, read 2026-09-19).

**The request form itself could not be read**: developer.apple.com/contact
redirects to an Apple ID sign-in, and this session did not authenticate. So the
form's exact criteria are not established here — see "what could not be costed".

**The finding: CarPlay is blocked, and not by anything in this list.** A CarPlay
navigation app is an App Store app first. `docs/legal-and-ip-audit.md` (on
`claude/data-attribution`) is the live record, and its risk register has four
items that gate submission at all:

| # | item | status in that audit |
|---|---|---|
| 1 | **"Scenic" is taken by a senior direct competitor**, and is descriptive | rename before spending anything on brand |
| 2 | Apple's map attribution **obscured** by the planning sheet | confirmed breach, unfixed |
| 3 | No EULA carrying the ADPLA §3.3.15 route-guidance notice | confirmed gap |
| 4 | No privacy policy URL | confirmed missing — a hard submission gate |

Plus no `PrivacyInfo.xcprivacy` (item 6) and no LICENSE. Item 2 is the one that
compounds: **a second screen is a second place to clip the Apple logo**, so
CarPlay makes an existing unfixed breach worse rather than being independent of
it.

**So the ordering, which is what this section owes:**

1. Resolve the name (`docs/…name-must-change`, and it is a rename, not a
   decision that can be deferred past any brand spend).
2. Close audit items 2, 3, 4 and 6.
3. Ship to the App Store as a phone app and let it be reviewed once.
4. *Then* request the entitlement, with a shipped app to point at.

**Estimating the CarPlay scene itself is the least useful thing this document
could produce**, and it is not produced. The scene is ordinary UIKit template
work against `CPMapTemplate`; the reason it is not on the near list is that
steps 1–3 are not done, and `docs/scenic-never-scoped-for-public-release` is the
record of how far from done they are.

---

## 7. The app opens on Massachusetts

**What exists.** `MKCoordinateRegion.massachusetts`
(`ios/Sources/Region.swift:9-12`) — centre 42.15, −71.8, span 2.6° — used in
four places:

| use | file |
|---|---|
| initial map camera | `ios/Sources/ContentView.swift:16` |
| address-search bias, route tab | `ios/Sources/RouteModel.swift:58` |
| address-search bias, loop tab | `ios/Sources/LoopModel.swift:94` |
| `MKLocalSearchCompleter.region` | `ios/Sources/SearchCompleter.swift:23` |

Both models already replace it with `.around(fix.coordinate)` once a fix arrives
(`ios/Sources/RouteModel.swift:183`, `ios/Sources/LoopModel.swift:132`).
**`SearchCompleter` does not** — its region is set once at `:23` and never
updated, which is a separate small defect this document only notes.

**First, a correction to the framing.** "The app opens on Massachusetts and
hides five states" is not quite what the code does. A 2.6° box centred on 42.15,
−71.8 spans lat 40.85–43.45 and lon −73.10 to −70.50, which already reaches into
Connecticut, Rhode Island, and southern New Hampshire and Vermont. Measured
against the served graph:

| | |
|---|---|
| graph nodes inside the opening camera | 517,405 / 794,685 = **65.1%** |
| served road-km inside it (both ends) | 123,219 / 232,720 km = **52.9%** |
| **served road-km it omits** | **109,502 km** |

(232,720 km is the graph's own edge total, against the census's 236,270 km of
raw OSM way length in Part 1 — the graph drops disconnected components and
measures in `CRS_METERS` after chunking. The two are 1.5% apart and are not
interchangeable; each figure above uses the one it was computed from.)

So the camera shows just over half the network and hides just under half — and
what it hides is coherent rather than arbitrary: Maine, northern New Hampshire
and Vermont, and the western edge of Connecticut. That is a smaller defect than
"five states hidden" and a real one.

**The two halves cost differently, and the brief is right that they must be
separated.**

### 7a. The camera

One value in one file, which documents itself as "the single place to widen".
**Product decision (owner's): the `SCENIC_REGION` / opening-region default.**
Three defensible answers, and they differ in the pre-permission case:

- **Open on the six-state box.** Correct, and shows the driver a lot of ocean
  and forest — the box is 6.49° × 6.76° and its centre is in the Maine woods.
- **Open on the user's location.** Best when there is one; before permission is
  granted there is not, so this needs one of the other two as a fallback anyway.
- **Remember the last region.** Best on the second launch, undefined on the
  first.

Costed, not chosen: all three are a small change to `Region.swift` plus, for the
last two, a `UserDefaults` key — which is the same mechanism
`VoiceCatalogue.swift:118-119` already uses. Estimated under 50 lines for any of
them. **The engineering cost does not discriminate between the three; the
decision is entirely about behaviour.**

### 7b. The search bias — and here the measurement does discriminate

`MKCoordinateRegion.around` exists (`ios/Sources/Region.swift:20-23`) because
ranking by distance from a statewide box's centre offers "main street" four
towns away. A six-state box makes that strictly worse, and by how much is
measurable. The six-state bounding box of the served graph is lon
−73.717 to −66.953, lat 40.994 to 47.488; its centre is **44.241, −70.335**, in
inland Maine.

| destination | km from today's MA-box centre | km from a six-state box centre |
|---|---|---|
| Needham | **48** | **230** |
| Providence | 48 | 283 |
| Boston | 65 | 217 |
| Hartford | 84 | 335 |
| Concord NH | 120 | 150 |
| Portland ME | 210 | **65** |
| Burlington VT | 283 | 230 |

**Widening the search bias to the six-state box moves the ranking anchor from
48 km to 230 km away from the place the app is actually used — 4.8× worse —
and improves it only for Portland.** A box that covers six states is mostly
Maine and the Atlantic, because Maine is nearly half of New England by area
(91,633 km² of 186,447) while carrying a quarter of its road-km (59,969 of
236,270, from the census above).

**So the recommendation for 7b is: do not widen it.** Widen the camera; fix the
bias by pointing it at the user, which the two models already do and
`SearchCompleter.swift:23` does not. That is the cheaper change *and* the better
one, and it is independent of the held-out decision in 7a.

**What would kill it.** Nothing kills 7a; it is gated on a decision, not a cost.
The thing that would kill 7b is doing it the obvious way: a naive widen ships a
measurable regression to every search the app's actual user makes.

---

# The ordering recommendation

**This is a recommendation with its reasoning, and the reasoning is more useful
than the order.** Two orderings are given because two defensible readings exist,
and choosing between them is a judgement about what the app is *for* right now,
which is the owner's.

## Ordering A — by cost and by what unblocks what

**Tier 1 — buildable today, no decision needed, no collision:**

1. **§4 gap 1 — tell the driver the connection is gone.** Smallest change on
   the list, every mechanism already precedented in the same two files, and the
   only item that is a correctness defect rather than a missing feature.
2. **§1 GPX, client-side.** No server change, no new request, works offline. The
   measurement in §2 is what proves the client already holds every byte the file
   needs.
3. **§2 server half — the per-edge series on the wire.** Measured at 4–9% of
   the gzipped response (8–17% with all six beauty components), no rebuild, no
   restart. Worth doing *before* the
   presentation decision precisely because it does not bet on it, and because
   it is the one item whose cost falls when it ships early: the field can be
   live while the view is designed.
4. **§7b — point the search bias at the user, don't widen it.** Measured as a
   4.8× improvement over the naive alternative, and independent of 7a's
   decision.

**Tier 2 — one decision each, cheap once it lands:**

5. **§7a — the opening camera.** Under 50 lines once the default is chosen.
6. **§3a — drive history from the traces already on disk.** No new data, no
   server change; gated on the privacy story.
7. **§2 iOS half.** Gated on the presentation decision; unblocked by item 3.
8. **§3b — saved routes**, with the promise worded against the drift table.
   Carries §4 gap 2 with it if it stores the answer.

**Tier 3 — not an engineering decision:**

9. **§5 lane guidance.** The census says the data is not there in any state. Ask
   again against a later extract.
10. **§6 CarPlay.** Blocked behind rename → audit items 2/3/4/6 → an App Store
    release.

## Ordering B — by what the driver gets

The counter-reading, and it is not weak. **§2 is the app's entire thesis.** It
tells the driver "31 of your 50 miles are beautiful" and gives them no way to
see *which* 31 — and the engine has had the per-edge numbers the whole time.
Under this reading §2 goes first, entire, and the presentation decision becomes
the thing to unblock rather than the thing to wait for. §4 gap 1 is invisible
until something breaks, and §1 serves a smaller set of people than either.

**What the two orderings agree on**, which is the part worth trusting: §5 and §6
are last, for reasons that are not about effort; §2's server half is cheap and
should not wait for its client half; and §7b should not be done the obvious way.

---

# What could not be costed from the code alone

1. **Engineer-hours for anything.** Every line count above is an estimate and is
   labelled as one. What *is* measured is the kind of change: whether it needs a
   server round trip, a new endpoint, a restart, or a full rebuild — and those
   are the distinctions that actually separate a day from a week here.
2. **The CarPlay entitlement's criteria.** developer.apple.com/contact redirects
   to an Apple ID sign-in and this session did not authenticate. What Apple asks
   for — a shipped app, a demo build, a category justification — is therefore
   not established. **The measurement that would settle it:** open the request
   form while signed in to the developer account and read it. That is a
   five-minute check and it is the owner's to run, since it needs their account.
3. **Whether a same-extent rebuild drifts less than §3b's 4/30.** The two builds
   that exist differ in extent as well as vintage.
   **The measurement that would settle it:** re-run `extract.py` → `graph.py`
   over the *same* PBF and re-run §3b's harness. That is ~1.5 GB of disk and a
   few hours of pipeline, which is why it was not done here.
4. **What a lane strip does to driver trust when it is absent 83% of the time.**
   This is the crux of §5 and it is not a code question.
   **The measurement that would settle it:** the drives. This project's other
   hard answers came from `xcrun simctl location` replays and real drives
   (`docs/consumer-polish-brief.md`, the 2026-08-22 traces), and this one would
   too.
5. **Whether OSM's `turn:lanes` is improving fast enough to change §5.** One
   extract is a snapshot. **The measurement:** re-run Part 1 against a
   `new-england-latest` from a year earlier and compare. The script takes a file
   list; the only obstacle is having an older PBF, which this machine does not.
6. **The iOS half of §2, §3 and §7 was costed by reading, not by building.** No
   Swift was written and no build was run, so every iOS estimate is softer than
   the server and pipeline ones. The measured wire format is firm; the view
   work around it is not.

---

# Reproducing this

All three harnesses are scratch scripts kept **outside** the repo, as the
geodata studies were. They are reproduced here in full recipe so the numbers can
be re-taken rather than re-believed. `data/` lives only in the main checkout,
never in a worktree — run these from the main checkout with absolute paths.

**The `turn:lanes` census (Part 1).** Two passes per PBF with pyosmium: pass 1
counts road *arms* per node over `DRIVABLE` ways only — a node with ≥3 arms is a
junction, and counting distinct *ways* instead misses every T-junction, where a
side street ends on an unsplit through way and only two ways touch the node.
Pass 2 walks the same ways with node locations (`idx="flex_mem"`), measuring
length with `osmium.geom.haversine_distance`, and records for each way its
class, whether any of `turn:lanes{,:forward,:backward,:both_ways}` is present,
its directional lane count, and which of its endpoints are junctions.

"Directional lane count" needs stating because OSM's `lanes=` counts **both**
directions: take `lanes:forward`/`lanes:backward` when either is present,
otherwise `lanes` if the way is oneway (or a roundabout, or a motorway), and
otherwise `lanes // 2`. A plain `lanes=2` residential street is one lane each
way and no `turn:lanes` could apply to it. This is the definition behind the
"multi-lane" column — and, per Part 1, the reason that column is not the
headline.

```bash
.venv/bin/python turn_lanes_census.py \
  data/raw/{rhode-island,vermont,new-hampshire,maine,connecticut}-latest.osm.pbf \
  data/raw/massachusetts-20260825.osm.pbf \
  data/raw/new-england-latest.osm.pbf
```

Under three minutes for the six state files; about twelve for the merged
extract, which is run only as the integrity check.

**The payload measurement (§2).** Loads one `Router` against
`data/processed-ne`, routes six pairs at pref 1.0, and compares
`json.dumps(..., separators=(",",":"))` and `gzip.compress(..., 6)` of
`geojson()` against the same object with extra per-edge arrays — three variants
were run (minimal, the three-series version in the first table, and all six
`SCENERY_BREAKDOWN` components). ~30 s each including the graph load.

**The rebuild-drift measurement (§3b).** Loads both builds in one process,
routes ten Massachusetts pairs at pref 0.0 / 0.5 / 1.0 against each, and
compares the answers three ways: byte-identical WKB, changed `km`/`minutes`/
`mean_score`, and — the one that matters — the length of each line falling
outside a 20 m buffer of the other, projected to `CRS_METERS`. The 20 m
tolerance is what separates "the same road, re-chunked" from "a different road",
and it is the reason the byte test (3/30) and the ground test (20/30) disagree
so sharply. ~45 s.

```bash
.venv/bin/python rebuild_drift2.py data/processed data/processed-ne
```

**Tests.** `SCENIC_DATA=<abs>/data/processed-ne .venv/bin/python -m pytest tests/`
from the repo root, with an absolute path to the main checkout's `data/`.

This change is documents only and leaves the suite exactly as it found it, which
on 2026-09-19 against `data/processed-ne` is **1 failed, 347 passed** in 282 s.
The one failure is
`tests/test_api.py::test_the_route_that_found_this_defect_no_longer_returns_it`,
it is pre-existing, and it is described in §3b — the same test passes against
`data/processed`. Nothing here touches it.
