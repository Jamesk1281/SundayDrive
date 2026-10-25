# Brief: cap the nearest-road search, so one request can't stall the API

**Status: diagnosed, not fixed.** Nothing has been changed. Branch off `usa`
(at or after `936dfcf`). This brief is temporary and is deleted in the merge
that brings the work back. **Your answer goes in `docs/snap-cap.md`**, along
with the code and tests. Never append to this brief, and have source comments
and tests cite `docs/snap-cap.md`, never this file.

## The symptom, as measured

The 2026-10-23 outside review, on a local national server
(`data/pack-us` + `data/processed-us`, 20,023,955 nodes):

- `POST /api/route from=36.46994,-70.93004 to=36.48985,-70.08488` (about 400 km
  off the Atlantic coast) returned the correct `400 OUTSIDE_COVERAGE`, but
  only after **100.2 s**. A repeat took 94.2 s.
- Points about 10 km offshore took **9.2 s and 10.9 s**.
- During four such requests at once, an ordinary Denver → Estes Park route
  took **176.8 s** instead of 0.5 s. The app's timeout is 20 s.
- `/api/health` answered in 0.02 s the whole time, so the only monitor stays
  green while drivers time out.

Re-measured by the master session on 2026-10-23, with the national server
alone on the Mac and freshly started: Denver → Estes Park took 0.56 s. The
same 400 km-offshore request took **618 s**, and RSS went from 2.7 GB to
8.1 GB while it ran. That figure is the cold page cache: the search touches
most of the memory-mapped pack. On the box's disk (about 24 MB/s) it would be
worse.

The API has no authentication, the URL is public, waitress runs 4 threads
(`server/serve.py:44`), and the Cloudflare rule is 60 requests a minute per
IP. Four requests are enough.

## The mechanism

`LineIndex.nearest` (`pipeline/router.py:887-911`) widens its square fourfold
until the nearest line it finds lies inside it, with no upper bound short of
20,000 km:

```python
reach = max(reach * 4.0, float(d[k]))
...
if reach > 2e7:
```

Every candidate in the square is then measured with `shapely.distance`. From
400 km offshore the square reaches about 1,000 km half-width, which is
millions of segments.

Only after that does the server apply its 5 km limit:
`server/app.py:213` `SNAP_MAX_M = 5000.0`, then `:669`
`if max(s_off, t_off) > SNAP_MAX_M: return _outside("that point")`.

Every public endpoint reaches the unbounded search:

| endpoint | call | `app.py` |
| --- | --- | --- |
| `/api/route` `from` | `ROUTER.snap_lead` → `_snap` → `_edge_tree.nearest` (`router.py:3059`) | 651 |
| `/api/route` `to` | `ROUTER.snap_destination` (`router.py:1764`): `_snap`, then `access_point` (`router.py:1749-1751`), which searches `_access_tree.nearest` **and** `_edge_tree.nearest` again. That is three unbounded searches for one destination | 668 |
| `/api/route` `via` | `ROUTER.snap` | 711 |
| `/api/loop` | `ROUTER.snap` | 890 |
| `/api/loop/limit` | `ROUTER.snap` | 923 |

`_nearest_open` (`router.py:3146`) is already bounded by `SNAP_OPEN_MAX_M`, so
leave it alone.

## What to build

1. **Bound the search inside `LineIndex.nearest`.** Give it a maximum
   distance. Once the square's half-width reaches that limit and nothing lies
   within it, report "nothing in reach" instead of widening. Thread the limit
   through `_snap`, `snap`, `snap_lead`, `snap_destination` and `access_point`,
   so a point beyond 5 km comes back as "outside" without a continental
   search. Where `SNAP_MAX_M` lives (router or app) is your call. There must
   be one constant, not two.
2. **Keep in-range behaviour identical.** For any point with a road within
   5 km, the chosen line, the tie rule ("the lowest index on a tie") and the
   returned offset must not change. Prove it with a parity check: sample many
   points (NE and national, on-road, mid-block, 1–4.9 km from roads, in car
   parks), compare old against new `nearest` and snaps, and report the count.
   It must be all of them.
3. **Fuzz every endpoint with hostile input, as a test and as a measurement.**
   - Points: 10 km and 400 km offshore in the Atlantic, the Gulf and the
     Pacific; mid-Lake Michigan; a Nevada or Utah point more than 5 km from
     any road; Hudson Bay; central Mexico; `0,0`; near the poles; the
     antimeridian; out-of-range latitudes; `nan`, `inf`.
   - Each one goes into `from`, `to` and `via` on `/api/route`, plus
     `/api/loop` and `/api/loop/limit`.
   - **Done means** each one answers its correct error in well under 1 s on
     the national server. Then send four offshore requests at once alongside
     Denver → Estes Park, and that route still answers in about its normal
     time.
   - Python test: write it against the regional fixture or `processed-ne`.
     Assert the **work** (candidates measured, or loop iterations), not wall
     time. Wall-clock asserts are flaky on this shared Mac.
4. **A health check that plans a route.** Add an endpoint that plans one
   fixed short route and reports its time. It returns a failure status, and
   not the success keyword, when planning fails or takes more than a few
   seconds.
   - Pick a pair that exists in both the New England and the national
     builds, such as two Massachusetts towns. The server still runs
     `--region ne` today.
   - Anyone can call it, so it must not amplify load. Cache the result for
     about a minute, and never run two at once. It must not take the loop
     lock.
   - Update the monitoring section of `server/DEPLOY-oracle.md`: a second
     UptimeRobot keyword monitor on this endpoint, beside the existing
     node-count one. Setting it up is the owner's job, so write the steps.
5. **`docs/snap-cap.md`**: what changed, before/after timings (the 10 km
   offshore point and the fuzz set, old code against new), the parity count,
   and the health endpoint's contract.

## Traps

1. **A pre-check in `app.py` alone does not fix it.** A bounding box or
   coverage polygon still lets through points inside it that are far from
   roads: the Gulf, the Great Lakes, Chesapeake Bay, the desert. The 10 km
   offshore case took about 10 s. The bound has to be inside
   `LineIndex.nearest`. A coarse polygon is optional on top. Don't build one
   unless the fuzz shows you need it.
2. **Changing the stop rule for in-range points changes routes.** The current
   rule ("accept once `d[k] <= reach`") is what makes the result exact. Add
   only a cut-off for when `reach` has passed the limit and the best distance
   is still beyond it. Run the parity check of item 2 before anything else
   counts as done.
3. **Destinations search three times.** `access_point` searches the access
   tree and then the edge tree. Bounding only `_snap` leaves two unbounded
   searches per destination.
4. **Other callers of `snap` exist.** `pipeline/options.py`, `looper.py`,
   `tools/` and tests may call `snap`, `_snap` or `nearest` and expect an
   index back. Grep for all of them before you choose how "outside" is
   represented. A `None` where an `int` was expected crashes the loop builder
   mid-request.
5. **Don't re-run the 400 km offshore case on the old code.** It is settled,
   at 100–618 s. Use the 10 km point (about 10 s) as the old-code baseline.
6. **The health endpoint is a public endpoint.** Without a cache, it hands a
   scraper a cheap way to make the server plan routes.

## Out of scope

- A per-request CPU deadline. If the fuzz turns up another slow path, report
  it in `docs/snap-cap.md` and don't fix it here.
- Island and ferry destinations.
- Error wording.
- Loop concurrency.
- Deploying. The owner deploys.

## Done looks like

1. Every endpoint answers every fuzz point in well under 1 s on the national
   server, and four concurrent offshore requests no longer delay an ordinary
   route.
2. The in-range parity check passes on every sampled point, with the count
   reported.
3. The Python suite on `processed-ne` is green apart from known failures,
   which are named. `tests/test_national_routes.py` passes with
   `SUNDAYDRIVE_PACK` set.
4. A health endpoint that plans a route exists, is cached, and is documented
   in `DEPLOY-oracle.md`.
5. `docs/snap-cap.md` records all of the above. Or, for any item that cannot
   be done, a statement saying why.
