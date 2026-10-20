# Deploying the national server (review fixes, unit P)

**Status:** built and exercised against a local fake box on 2026-10-20. **Never
run against the real box.** Nothing here connected to the box, copied to it or
restarted it. The box still serves New England from `main`, as before.

This covers `server/deploy-oracle.sh`, `server/DEPLOY-oracle.md` (Part 8's
drop-in, the new Part 14, "Updating the box", Rollback, Troubleshooting) and
`server/DEPLOY.md`. `server/Dockerfile` is removed.

## What was wrong

- The script could deploy only New England. The data defaulted to
  `data/processed-ne`, and nothing copied a pack or set `SUNDAYDRIVE_PACK`.
  The UptimeRobot keyword was hard-coded as `794685`, New England's node count.
- The systemd unit set only `SUNDAYDRIVE_DATA=…/processed-ne`.
- The script checked `/api/health`'s node count against `graph_nodes.parquet`
  on the box. A correct national deploy would have tripped its own check, and
  it would have done so only after the restart.
- The Docker path could not start the current server. It left out `looper.py`
  and `options.py`, had no pack, and copied `data/processed`.

## What the script does now

`server/deploy-oracle.sh [--region us|ne] [--ref BRANCH] [--pack DIR] [--data DIR] [--dry-run] [--restart] [--rehash] [--allow-rewind]`

| | national (`--region us`, the default) | New England (`--region ne`) |
|---|---|---|
| Mac source | `--pack` / `SUNDAYDRIVE_PACK_DIR` (default `data/pack-us`), `--data` / `SUNDAYDRIVE_DATA_DIR` (default `data/processed-us`) | `--data` (default `data/processed-ne`) |
| files | every file the manifest lists (94 for the real pack), plus the nine `PACK_SOURCES` parquets | the same nine parquets, by the old `REQUIRED` and `OPTIONAL` lists |
| box destination | always `~/Scenic/data/pack-us` and `~/Scenic/data/processed-us`, so a `-next` build ships with no unit change | `~/Scenic/data/processed-ne` |
| unit drop-in | `SUNDAYDRIVE_DATA=…/processed-us`, `SUNDAYDRIVE_PACK=…/pack-us` | `SUNDAYDRIVE_DATA=…/processed-ne`, `SUNDAYDRIVE_PACK=` (empty means none) |
| checked after the restart | nodes = manifest, region = manifest's, commit, pack = sha256(manifest.json) | nodes = parquet rows (box and Mac), region "New England", commit, pack null; the journal's closure lines as before |
| UptimeRobot keyword printed | `20023955` | `794685` |
| wait for the restart | 600 s | 180 s |

**`--ref`** defaults to `main`. For the national server the script refuses a
ref whose `server/app.py` does not read `SUNDAYDRIVE_PACK`, which `main` does
not until `usa` is merged into it. So the national deploy is `--ref usa` today,
and the bare command after that merge.

**Before the box is touched,** the Mac checks:
- that the ref is on origin (`git ls-remote`);
- the pack's manifest (every listed file exists, and its version is the one
  the ref's router reads);
- that the manifest's fingerprints match the parquets being shipped. This uses
  the router's own rule, `pipeline/router.py` `_sources`: size and sha1 of the
  last 64 KB.

  That last check catches `pack-us-next` shipped with the old `processed-us`
  (transcript, step 4). Without it the server would find the mismatch only at
  startup, and refuse to start.

**What differs** is decided by SHA-256 at both ends. The Mac hashes everything
(22 s for the real 19.7 GB, with openssl). The box uses the record
`.deploy-sha256` that the script writes after each verified copy. Any file
whose size disagrees with the record is hashed again, and `--rehash` hashes
them all. Rehashing is worth avoiding: at the boot volume's rated 24 MB/s, the
national data takes about 13 minutes to hash.

**The order** is:
1. Copy to `<dir>.incoming`, and verify there by SHA-256. A mismatch deletes
   that file and stops, with nothing swapped in (step 5).
2. Check out the commit, detached.
3. Run pip if the lock file changed.
4. Rename the verified files over the live ones. The old `manifest.json` comes
   out first and the new one goes in last, so a server that restarted
   mid-swap would refuse to start rather than map a mixed pack. Remove files
   the pack no longer lists.
5. Write the drop-in, reload systemd, and restart once.

The live service is unaffected until that one restart.

**The unit** keeps the file Part 8 wrote and gains
`/etc/systemd/system/sundaydrive-api.service.d/deploy.conf`. Every restart
rewrites it with the data and pack paths, an empty `SUNDAYDRIVE_REGION`, and
`SUNDAYDRIVE_COMMIT=<12-char sha>`. A change to the paths alone forces a
restart. A changed commit forces one only when server code changed. A
docs-only pull leaves the running process and its commit alone. The same sha
also goes to `~/Scenic/DEPLOYED_COMMIT`. That file is untracked on the box and
ignored by the script's dirty-checkout test.

**The plan** also shows:
- the box's free disk. The script refuses a copy that would leave under 2 GB
  free, in a dry run too.
- the box's memory. A national deploy on under 11 GB gets a resize warning.
- a copy-time estimate at 24 MB/s.

### What /api/health must say

This was agreed with unit R on 2026-10-20, and R is building to it:

- **`commit`.** `SUNDAYDRIVE_COMMIT`, else the first line of
  `<checkout>/DEPLOYED_COMMIT`, else null, reported as given. The deploy
  accepts any prefix of 7 characters or more of the sha it shipped.
- **`pack`.** The full hex sha256 of the pack's `manifest.json`, or null with no
  pack. An empty `SUNDAYDRIVE_PACK` counts as no pack (`or None` in `app.py`).
- **`region`.** `SUNDAYDRIVE_REGION` if set, else the manifest's `region`, else
  "New England". The drop-in sets it empty so the pack names it.

A field the server does not yet report is a **warning**, so the script works
before and after R's change. A wrong value **stops** the deploy (step 7).

## The New England path

- **From `main`:** `main`'s own script is untouched. It ran clean against the
  box state this script leaves (step 9). It ignores the drop-in, which by then
  names New England's paths.
- **By flag from `usa`:** `--region ne` ships the same files, runs the same
  journal and row-count checks, and uses the same port and service. Going back
  from a national box needs `--allow-rewind`, because `main` does not contain
  the box's `usa` commit (step 8).
- **`main`'s script on a national box refuses,** with "not an ancestor of main"
  (step 10). So it cannot restart a box whose drop-in names the national data
  into code that would try to build the US graph from parquets. After `usa` is
  merged into `main`, `main`'s script is this one.

## The fake box

All runs used a fake box built in the session's scratch directory, which is
now deleted:

- **The box's checkout.** A clone of the repo at `2ed3f47`, the commit the box
  served after 2026-10-08. Its `data/processed-ne` held New England's real
  parquets as APFS clones, without `osm_unpaved`, which was never deployed.
  Its `.venv/bin/python` was a shim that turns `pip` into a no-op.
- **The base unit.** Part 8's text, verbatim, with only the paths changed.
- **The "Mac".** A second clone, whose `origin` is the repo itself, so
  `ls-remote` answered without GitHub.
- **`ssh` on `PATH`.** A shim that runs the remote command locally, in the
  fake home. **It ignores the host**, which is why the transcript says
  "connecting to ubuntu@129.158.208.92". All 179 ssh invocations in the
  session went through the shim, and its log has every one. rsync used it too
  (`-e`).
- **Other shims.** `sudo` runs its command. `systemctl restart` starts a fake
  API. `journalctl` prints fake closure lines. `sha256sum` can be told to
  corrupt one file's hash.
- **The fake API.** It serves `/api/health` to R's contract above. Like the real
  server, it refuses a pack whose sources don't match the parquets beside it.
- **The fake `/proc`.** **The memory figures in the transcript are values I
  wrote into it** (an 8 GB box, 3.16 GiB anonymous), not measurements.
- **The national data.** Nine small random "parquets" and a pack whose
  manifest was written with `router._sources` itself. The `-next` pair
  symlinks eight unchanged parquets, regenerates `closed_to_cars`, changes one
  array, drops one and adds one. Step 11 runs a dry run on the **real**
  `pack-us` and `processed-us`.

The script reads four overrides that exist only for this:
`SUNDAYDRIVE_UNIT_DIR`, `SUNDAYDRIVE_BOX_PORT` and `SUNDAYDRIVE_PUBLIC_HEALTH`
on the Mac, and `SUNDAYDRIVE_PROC` in the commands it sends to the box. Unset,
they are `/etc/systemd/system`, 5057, the real hostname and `/proc`.

## What it showed

| step | what | result |
|---|---|---|
| 1 | national from `main` | refused: `main` cannot load a pack |
| 2 | first national deploy, `--ref usa` | 17 files copied and verified, unit written, every health field `ok`, keyword 20023955 |
| 3 | rerun | nothing to deploy |
| 4 | `pack-us-next` with the old `processed-us` | refused on the Mac: `closed_to_cars.parquet` differs |
| 5 | the `-next` pair, `objects.pickle` corrupted in transit | stopped at verification; staged file deleted, live pack untouched, old API still answering |
| 6 | the same, rerun | 5 files copied, `lines.xy.npy` removed, new pack fingerprint served |
| 7 | server reports the wrong commit | `PROBLEM`, exit 1 |
| 8 | back to New England by flag | refused without `--allow-rewind`; with it, `main` checked out, 794685 nodes, pack null; rerun is a no-op |
| 9 | `main`'s own script afterwards | restarted and passed. Its `free` and memory-% errors are the macOS fake lacking `free`. Its public check reached the fake API through a `curl` shim, not the real hostname |
| 10 | national again, then `main`'s script | `main`'s script refuses the box |
| 11 | real `pack-us` + `processed-us`, dry run | manifest, version and fingerprints pass on all 94 + 9 files, 19.7 GB to copy. Refused at the disk check, correctly, because the fake box's disk is this Mac's, with 11.4 GB free |

`bash -n` passes. shellcheck is not installed here. The suite
(`SUNDAYDRIVE_DATA=…/processed-ne pytest tests/`) is **987 passed, 13
skipped, 0 failed**, the same as `usa`. The four tests that read the script's
`OPTIONAL=` line and journal strings still pass.

## What the owner must do on the box (not done)

These steps are also in `server/DEPLOY-oracle.md`, Part 14:

1. **Resize 8 → 12 GB first.**
   - Console → the instance → Edit → Edit shape → 2 OCPU, 12 GB.
   - It costs a stop/start, and capacity is not guaranteed at that moment.
   - Then check `free -h`, both services `active`, and `/api/health`.
2. **Look at the disk:** `df -h ~/Scenic/data`.
   - The first national deploy needs 19.7 GB plus 2 GB.
   - Once it is live, a whole new graph needs another 19.7 GB beside it until
     the restart. That may not fit on 50 GB.
   - Always Free covers 200 GB of block storage, so growing the boot volume to
     100 GB is free. It also doubles its rated throughput. Not done; follow
     Oracle's "Resizing a Volume" pages.
3. **Push `usa`.** Then `server/deploy-oracle.sh --ref usa --dry-run`, then the
   real run.
4. **Set the UptimeRobot keyword** to what the script prints (`20023955`)
   straight after the deploy.
5. **Run the memory check** (Part 14) after a day of traffic.

## Left open

- **Nothing here is measured on the box.**
  - The 24 MB/s figure is Oracle's published Balanced rate for a 50 GB volume
    (480 KB/s per GB), not a measurement. It matches the first run's
    382 MB in 16 s.
  - From it, the box's cold national start is estimated at 2–3 minutes, which
    is why the script waits 600 s. Measure it on the first deploy.
  - The memory thresholds in Part 14 come from the Mac's figures in
    `docs/router-at-us-scale.md`.
  - The `fincore -b -n -o RES` line in Part 14 was not run here, because the
    Mac has no `fincore`.
- **The health checks stay warnings until R's fields are merged.** The values
  were agreed, not tested against R's code.
- **`data/processed-ne` on the Mac has no `osm_unpaved.parquet`.** Both
  scripts warn about it. Building it is `pipeline/closures.py`'s job, not this
  unit's.
- **`server/serve.py`'s docstring still mentions Docker.** That file is R's.
- **Two connectors (Part 10):** the rolling deploy is still unwritten. This
  script covers one box.

## Dry-run transcript

All of this ran against the fake box. `$SCRATCH` is the session's scratch
directory and `$REPO` the main checkout.

```text
### 1. The default is main, which cannot serve the national graph yet
$ server/deploy-oracle.sh --dry-run --pack $SCRATCH/fakedata/pack-us --data $SCRATCH/fakedata/processed-us
==> checking origin/main
deploy: main (4958941) cannot load a pack, so it cannot serve the national graph.
  Deploy --ref usa, or --region ne.
[exit 1]
### 2. The first national deploy, from usa: dry run, then real
$ server/deploy-oracle.sh --dry-run --ref usa --pack $SCRATCH/fakedata/pack-us --data $SCRATCH/fakedata/processed-us
==> checking origin/usa
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: the contiguous United States, 20023955 nodes, pack 1ab70ee117ba
    code: 2ed3f47 -> 4f74951 (usa, 55 commits)
          10 files changed, 3135 insertions(+), 1030 deletions(-)
    data: Scenic/data/processed-us: 9 of 9 files to copy, 1 MB (graph_edges.parquet graph_nodes.parquet turn_restrictions.parquet access_ways.parquet access_entries.parquet seasonal_closures.parquet ... and 3 more)
    data: Scenic/data/pack-us: 8 of 8 files to copy, 0 MB (_score.npy base_score.npy km.npy lines.xy.npy node_lat.npy node_lon.npy ... and 2 more)
    unit: $SCRATCH/fakebox/etc/systemd/system/sundaydrive-api.service.d/deploy.conf becomes
            SUNDAYDRIVE_DATA=$SCRATCH/fakebox/home/Scenic/data/processed-us
            SUNDAYDRIVE_PACK=$SCRATCH/fakebox/home/Scenic/data/pack-us
            SUNDAYDRIVE_REGION=
    disk: 2 MB to copy, 12.5 GB free on the box
          under a minute to write at the boot volume's rated 24 MB/s, and as long again to verify
    memory: the box has 7.5 GiB
    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving
    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14).
    monitor: UptimeRobot keyword must be 20023955 (New England's was 794685)
==> dry run: would restart the API
[exit 0]
$ server/deploy-oracle.sh --ref usa --pack $SCRATCH/fakedata/pack-us --data $SCRATCH/fakedata/processed-us
==> checking origin/usa
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: the contiguous United States, 20023955 nodes, pack 1ab70ee117ba
    code: 2ed3f47 -> 4f74951 (usa, 55 commits)
          10 files changed, 3135 insertions(+), 1030 deletions(-)
    data: Scenic/data/processed-us: 9 of 9 files to copy, 1 MB (graph_edges.parquet graph_nodes.parquet turn_restrictions.parquet access_ways.parquet access_entries.parquet seasonal_closures.parquet ... and 3 more)
    data: Scenic/data/pack-us: 8 of 8 files to copy, 0 MB (_score.npy base_score.npy km.npy lines.xy.npy node_lat.npy node_lon.npy ... and 2 more)
    unit: $SCRATCH/fakebox/etc/systemd/system/sundaydrive-api.service.d/deploy.conf becomes
            SUNDAYDRIVE_DATA=$SCRATCH/fakebox/home/Scenic/data/processed-us
            SUNDAYDRIVE_PACK=$SCRATCH/fakebox/home/Scenic/data/pack-us
            SUNDAYDRIVE_REGION=
    disk: 2 MB to copy, 12.5 GB free on the box
          under a minute to write at the boot volume's rated 24 MB/s, and as long again to verify
    memory: the box has 7.5 GiB
    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving
    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14).
    monitor: UptimeRobot keyword must be 20023955 (New England's was 794685)
==> copying 9 files to Scenic/data/processed-us.incoming
==> verifying the copy
==> copying 8 files to Scenic/data/pack-us.incoming
==> verifying the copy
==> checking out 4f74951 on the box
==> swapping in the new data
==> writing the unit's environment (commit 4f749514e7df)
==> restarting sundaydrive-api (waiting up to 600 s for it to answer)
    {"commit":"4f749514e7df","nodes":20023955,"pack":"1ab70ee117ba7d6004b9ab406a32f81349d4e63f8ff1b8f6a5a2485ab35cc7e6","region":"the contiguous United States","routing_slots":20186995,"status":"ok"}, after 3 s
    the pack was built from: graph_edges.parquet graph_nodes.parquet turn_restrictions.parquet access_ways.parquet access_entries.parquet seasonal_closures.parquet closed_to_cars.parquet state_road_class.parquet osm_unpaved.parquet
    ok: nodes 20023955, shipped 20023955
    ok: region 'the contiguous United States', shipped 'the contiguous United States'
    ok: commit 4f749514e7df, shipped 4f749514e7df
    ok: pack 1ab70ee117ba, shipped 1ab70ee117ba
    box memory: 56% used (4.2 of 7.5 GiB), swap 0.00 GiB used
    server: RssAnon: 3.16 GiB  RssFile: 2.00 GiB  VmSwap: 0.00 GiB  
==> deployed 4f74951 (usa, the contiguous United States); http://127.0.0.1:5091/api/health answers 200
    UptimeRobot keyword must be 20023955 (New England's was 794685)
[exit 0]
### 3. Nothing left to do
$ server/deploy-oracle.sh --dry-run --ref usa --pack $SCRATCH/fakedata/pack-us --data $SCRATCH/fakedata/processed-us
==> checking origin/usa
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: the contiguous United States, 20023955 nodes, pack 1ab70ee117ba
    code: already at 4f74951 (usa)
    data: Scenic/data/processed-us matches (9 files)
    data: Scenic/data/pack-us matches (8 files)
    unit: already serves these paths
    disk: 0 MB to copy, 12.5 GB free on the box
    memory: the box has 7.5 GiB
    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving
    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14).
    monitor: UptimeRobot keyword must be 20023955 (New England's was 794685)
==> nothing to deploy
[exit 0]
### 4. A pack built from other parquets than the ones it is shipped with
$ server/deploy-oracle.sh --dry-run --ref usa --pack $SCRATCH/fakedata/pack-us-next --data $SCRATCH/fakedata/processed-us-next/../processed-us
==> checking origin/usa
deploy: the pack at $SCRATCH/fakedata/pack-us-next was not built from the parquets at $SCRATCH/fakedata/processed-us-next/../processed-us.
  These differ: closed_to_cars.parquet.
  The server would refuse it at startup. Ship the processed directory the pack was built from.
[exit 1]
### 5. The -next pair (symlinked parquets, one table rebuilt, one array dropped), with a copy that arrives corrupted
$ server/deploy-oracle.sh --ref usa --pack $SCRATCH/fakedata/pack-us-next --data $SCRATCH/fakedata/processed-us-next
==> checking origin/usa
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: the contiguous United States, 20023955 nodes, pack 8e109760317b
    code: already at 4f74951 (usa)
    data: Scenic/data/processed-us: 1 of 9 files to copy, 0 MB (closed_to_cars.parquet )
    data: Scenic/data/pack-us: 4 of 8 files to copy, 0 MB (_score.npy _snap_closed.npy objects.pickle manifest.json )
          and remove lines.xy.npy, which the pack no longer lists
    unit: already serves these paths
    disk: 0 MB to copy, 12.5 GB free on the box
          under a minute to write at the boot volume's rated 24 MB/s, and as long again to verify
    memory: the box has 7.5 GiB
    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving
    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14).
    monitor: UptimeRobot keyword must be 20023955 (New England's was 794685)
==> copying 1 files to Scenic/data/processed-us.incoming
==> verifying the copy
==> copying 4 files to Scenic/data/pack-us.incoming
==> verifying the copy
deploy: objects.pickle hash mismatch after copy. Nothing was swapped in, and the API is still serving the old graph; rerun.
[exit 1]
### 6. The same, rerun
$ server/deploy-oracle.sh --ref usa --pack $SCRATCH/fakedata/pack-us-next --data $SCRATCH/fakedata/processed-us-next
==> checking origin/usa
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: the contiguous United States, 20023955 nodes, pack 8e109760317b
    code: already at 4f74951 (usa)
    data: Scenic/data/processed-us: 1 of 9 files to copy, 0 MB (closed_to_cars.parquet )
    data: Scenic/data/pack-us: 4 of 8 files to copy, 0 MB (_score.npy _snap_closed.npy objects.pickle manifest.json )
          and remove lines.xy.npy, which the pack no longer lists
    unit: already serves these paths
    disk: 0 MB to copy, 12.5 GB free on the box
          under a minute to write at the boot volume's rated 24 MB/s, and as long again to verify
    memory: the box has 7.5 GiB
    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving
    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14).
    monitor: UptimeRobot keyword must be 20023955 (New England's was 794685)
==> copying 1 files to Scenic/data/processed-us.incoming
==> verifying the copy
==> copying 4 files to Scenic/data/pack-us.incoming
==> verifying the copy
==> swapping in the new data
==> writing the unit's environment (commit 4f749514e7df)
==> restarting sundaydrive-api (waiting up to 600 s for it to answer)
    {"commit":"4f749514e7df","nodes":20023955,"pack":"8e109760317bfc4e5b6a2b2814d09de0e2c97740fee97f077fd9e5b61c016902","region":"the contiguous United States","routing_slots":20186995,"status":"ok"}, after 1 s
    the pack was built from: graph_edges.parquet graph_nodes.parquet turn_restrictions.parquet access_ways.parquet access_entries.parquet seasonal_closures.parquet closed_to_cars.parquet state_road_class.parquet osm_unpaved.parquet
    ok: nodes 20023955, shipped 20023955
    ok: region 'the contiguous United States', shipped 'the contiguous United States'
    ok: commit 4f749514e7df, shipped 4f749514e7df
    ok: pack 8e109760317b, shipped 8e109760317b
    box memory: 56% used (4.2 of 7.5 GiB), swap 0.00 GiB used
    server: RssAnon: 3.16 GiB  RssFile: 2.00 GiB  VmSwap: 0.00 GiB  
==> deployed 4f74951 (usa, the contiguous United States); http://127.0.0.1:5091/api/health answers 200
    UptimeRobot keyword must be 20023955 (New England's was 794685)
[exit 0]
### 7. A server that reports a commit other than the one shipped
$ server/deploy-oracle.sh --restart --ref usa --pack $SCRATCH/fakedata/pack-us-next --data $SCRATCH/fakedata/processed-us-next
==> checking origin/usa
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: the contiguous United States, 20023955 nodes, pack 8e109760317b
    code: already at 4f74951 (usa)
    data: Scenic/data/processed-us matches (9 files)
    data: Scenic/data/pack-us matches (8 files)
    unit: already serves these paths
    disk: 0 MB to copy, 12.5 GB free on the box
    memory: the box has 7.5 GiB
    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving
    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14).
    monitor: UptimeRobot keyword must be 20023955 (New England's was 794685)
==> recording what the box holds
==> writing the unit's environment (commit 4f749514e7df)
==> restarting sundaydrive-api (waiting up to 600 s for it to answer)
    {"commit":"deadbeef0000","nodes":20023955,"pack":"8e109760317bfc4e5b6a2b2814d09de0e2c97740fee97f077fd9e5b61c016902","region":"the contiguous United States","routing_slots":20186995,"status":"ok"}, after 2 s
    the pack was built from: graph_edges.parquet graph_nodes.parquet turn_restrictions.parquet access_ways.parquet access_entries.parquet seasonal_closures.parquet closed_to_cars.parquet state_road_class.parquet osm_unpaved.parquet
    ok: nodes 20023955, shipped 20023955
    ok: region 'the contiguous United States', shipped 'the contiguous United States'
    PROBLEM: commit deadbeef0000, shipped 4f749514e7df
    ok: pack 8e109760317b, shipped 8e109760317b
deploy: the API is up, but not serving what was shipped (above)
[exit 1]
### 8. Back to New England, by flag
$ server/deploy-oracle.sh --dry-run --region ne --data $REPO/data/processed-ne
==> checking origin/main
    warning: no osm_unpaved.parquet on the Mac; routes will take TIGER's 4WD trails as paved (pipeline/closures.py builds it)
==> connecting to ubuntu@129.158.208.92
deploy: the box is at 4f74951, which main does not contain.
  Deploying would drop those commits from the box. If that is the point (a
  rollback, or going from usa back to main), rerun with --allow-rewind.
[exit 1]
$ server/deploy-oracle.sh --region ne --allow-rewind --data $REPO/data/processed-ne
==> checking origin/main
    warning: no osm_unpaved.parquet on the Mac; routes will take TIGER's 4WD trails as paved (pipeline/closures.py builds it)
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: New England, 794685 nodes
    code: 4f74951 -> 4958941 (main, a rewind: 4f74951 is not in main)
          8 files changed, 938 insertions(+), 2625 deletions(-)
    data: Scenic/data/processed-ne matches (8 files)
    unit: $SCRATCH/fakebox/etc/systemd/system/sundaydrive-api.service.d/deploy.conf becomes
            SUNDAYDRIVE_DATA=$SCRATCH/fakebox/home/Scenic/data/processed-ne
            SUNDAYDRIVE_PACK=
            SUNDAYDRIVE_REGION=
    disk: 0 MB to copy, 12.5 GB free on the box
    memory: the box has 7.5 GiB
    monitor: UptimeRobot keyword must be 794685
==> checking out 4958941 on the box
==> recording what the box holds
==> writing the unit's environment (commit 49589414a6d6)
==> restarting sundaydrive-api (waiting up to 180 s for it to answer)
    {"commit":"49589414a6d6","nodes":794685,"pack":null,"region":"New England","routing_slots":801719,"status":"ok"}, after 2 s
    seasonal closures: 64 edges (fake)
    closed to cars: 1,024 edges (fake)
    state road classes: 9 private edges (fake)
    unpaved by TIGER's 4WD class: 3 edges (fake)
    ok: nodes 794685, shipped 794685
    ok: region 'New England', shipped 'New England'
    ok: commit 49589414a6d6, shipped 49589414a6d6
    ok: pack None, shipped None
    box memory: 56% used (4.2 of 7.5 GiB), swap 0.00 GiB used
    server: RssAnon: 3.16 GiB  RssFile: 2.00 GiB  VmSwap: 0.00 GiB  
==> deployed 4958941 (main, New England); http://127.0.0.1:5091/api/health answers 200
    UptimeRobot keyword must be 794685
[exit 0]
$ server/deploy-oracle.sh --dry-run --region ne --data $REPO/data/processed-ne
==> checking origin/main
    warning: no osm_unpaved.parquet on the Mac; routes will take TIGER's 4WD trails as paved (pipeline/closures.py builds it)
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: New England, 794685 nodes
    code: already at 4958941 (main)
    data: Scenic/data/processed-ne matches (8 files)
    unit: already serves these paths
    disk: 0 MB to copy, 12.5 GB free on the box
    memory: the box has 7.5 GiB
    monitor: UptimeRobot keyword must be 794685
==> nothing to deploy
[exit 0]
### 9. main's own script on the box this one left serving New England (curl and ssh shimmed)
$ (main's) server/deploy-oracle.sh --restart
==> checking origin/main
==> connecting to ubuntu@129.158.208.92
==> hashing parquets
    warning: no osm_unpaved.parquet on the Mac; routes will take TIGER's 4WD trails as paved (pipeline/closures.py builds it)
    code: already at 4958941
    data: all parquets match
==> restarting sundaydrive-api (the graph takes about 66 s to load)
    {"commit":"49589414a6d6","nodes":794685,"pack":null,"region":"New England","routing_slots":801719,"status":"ok"}, after 1 s
    seasonal closures: 64 edges (fake)
    closed to cars: 1,024 edges (fake)
    state road classes: 9 private edges (fake)
    unpaved by TIGER's 4WD class: 3 edges (fake)
bash: free: command not found
    box memory % used
$SCRATCH/tools/deploy-oracle-main.sh: line 199: [: : integer expression expected
    warning: under 30%. Oracle reclaims below 20% over 7 days; see Part 12.
==> deployed 4958941; https://api.jameskouvlis.com/api/health answers 200
[exit 0]
### 10. National again, then main's script
$ server/deploy-oracle.sh --ref usa --pack $SCRATCH/fakedata/pack-us-next --data $SCRATCH/fakedata/processed-us-next
==> checking origin/usa
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: the contiguous United States, 20023955 nodes, pack 8e109760317b
    code: 4958941 -> 4f74951 (usa, 46 commits)
          8 files changed, 2625 insertions(+), 938 deletions(-)
    data: Scenic/data/processed-us matches (9 files)
    data: Scenic/data/pack-us matches (8 files)
    unit: $SCRATCH/fakebox/etc/systemd/system/sundaydrive-api.service.d/deploy.conf becomes
            SUNDAYDRIVE_DATA=$SCRATCH/fakebox/home/Scenic/data/processed-us
            SUNDAYDRIVE_PACK=$SCRATCH/fakebox/home/Scenic/data/pack-us
            SUNDAYDRIVE_REGION=
    disk: 0 MB to copy, 11.4 GB free on the box
    memory: the box has 7.5 GiB
    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving
    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14).
    monitor: UptimeRobot keyword must be 20023955 (New England's was 794685)
==> checking out 4f74951 on the box
==> recording what the box holds
==> writing the unit's environment (commit 4f749514e7df)
==> restarting sundaydrive-api (waiting up to 600 s for it to answer)
    {"commit":"4f749514e7df","nodes":20023955,"pack":"8e109760317bfc4e5b6a2b2814d09de0e2c97740fee97f077fd9e5b61c016902","region":"the contiguous United States","routing_slots":20186995,"status":"ok"}, after 3 s
    the pack was built from: graph_edges.parquet graph_nodes.parquet turn_restrictions.parquet access_ways.parquet access_entries.parquet seasonal_closures.parquet closed_to_cars.parquet state_road_class.parquet osm_unpaved.parquet
    ok: nodes 20023955, shipped 20023955
    ok: region 'the contiguous United States', shipped 'the contiguous United States'
    ok: commit 4f749514e7df, shipped 4f749514e7df
    ok: pack 8e109760317b, shipped 8e109760317b
    box memory: 56% used (4.2 of 7.5 GiB), swap 0.00 GiB used
    server: RssAnon: 3.16 GiB  RssFile: 2.00 GiB  VmSwap: 0.00 GiB  
==> deployed 4f74951 (usa, the contiguous United States); http://127.0.0.1:5091/api/health answers 200
    UptimeRobot keyword must be 20023955 (New England's was 794685)
[exit 0]
$ (main's) server/deploy-oracle.sh --dry-run
==> checking origin/main
==> connecting to ubuntu@129.158.208.92
deploy: the box is at 4f74951, which is not an ancestor of main
[exit 1]
### 11. The real pack-us and processed-us, dry run (the fake box's disk is the Mac's)
$ server/deploy-oracle.sh --dry-run --ref usa --pack $REPO/data/pack-us --data $REPO/data/processed-us
==> checking origin/usa
==> connecting to ubuntu@129.158.208.92
==> comparing the data at both ends
    serving: the contiguous United States, 20023955 nodes, pack 04e86dace4c7
    code: already at 4f74951 (usa)
    data: Scenic/data/processed-us: 9 of 9 files to copy, 7.8 GB (graph_edges.parquet graph_nodes.parquet turn_restrictions.parquet access_ways.parquet access_entries.parquet seasonal_closures.parquet ... and 3 more)
    data: Scenic/data/pack-us: 94 of 94 files to copy, 11.9 GB (_breakdown.npy _car_closed_slots.npy _edge_order.npy _edge_start.npy _pair_indptr.npy _pair_slots.npy ... and 88 more)
    unit: already serves these paths
    disk: 19.7 GB to copy, 11.4 GB free on the box
    PROBLEM: that leaves less than 2 GB free. See DEPLOY-oracle.md Part 14, "Disk".
          about 13 min to write at the boot volume's rated 24 MB/s, and as long again to verify
    memory: the box has 7.5 GiB
    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving
    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14).
    monitor: UptimeRobot keyword must be 20023955 (New England's was 794685)
deploy: dry run: this deploy would stop at the disk check
[exit 1]
```
