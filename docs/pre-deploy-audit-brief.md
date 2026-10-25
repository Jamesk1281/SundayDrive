# Brief: is `usa` ready to deploy to the box, and what is left before it?

**Status: an evaluation, not a fix.** Nothing has been changed for it. Branch
off `usa` at or after `ea87a2a`. **Change no code, no config and nothing on the
box.** The only thing you write is the answer, `docs/pre-deploy-audit.md`. Every
fix you find comes back to the master session as a finding, and the master
dispatches it on its own. This brief is temporary and is deleted in the merge
that brings the work back. Never append to it.

## The question

The owner has resized the Oracle box to 12 GB. The next step is the first
national deploy: `server/deploy-oracle.sh --ref usa`. That needs `usa` pushed to
GitHub, and **the repository is public**. Is everything needed for that deploy
done, and what, if anything, has to change first?

Answer two questions separately, because they have different bars:

- **Before deploy.** The national server replaces the New England server
  that production runs today. The only users are a few private TestFlight
  testers on today's builds. The bar: it doesn't break or endanger them, it
  doesn't fall over, and it can be watched and rolled back.
- **Before submission.** App Review tests the national app against
  production. List what is left there too, but keep it out of the deploy
  verdict.

## Where things stand (2026-10-25)

- **`usa` is at `ea87a2a`.** It is 114 commits ahead of `origin/main` and has
  never been pushed. Local `main` (`4958941`) is 9 ahead of `origin/main` and is
  wholly contained in `usa`.
- **Production** runs the New England build: `/api/health` reports 794,685
  nodes, with no `region`, `commit` or `pack` fields. It is behind
  `api.jameskouvlis.com` through a Cloudflare tunnel. Box:
  `ubuntu@129.158.208.92`, key `~/.ssh/scenic_oracle` (the script's defaults,
  `server/deploy-oracle.sh:27-28`).
- **The domain `jameskouvlis.com` expires 2026-10-28 18:52 UTC**, and was not
  renewed as of 2026-10-23. Every installed build and the tunnel hostname
  depend on it. Check RDAP (`rdap.verisign.com/com/v1/domain/jameskouvlis.com`)
  and report.
- **Merged into `usa` since the last outside review (2026-10-23):**
  - the snap cap: a far-off point is refused in milliseconds, plus
    `/api/health/route` (`docs/snap-cap.md`);
  - the national copy rewrite (`docs/national-copy.md`).
- **In flight, not merged:** the low-scenery fallback. It changes
  `server/app.py`, `pipeline/options.py` and the app, so the scenic route
  falls back to the fastest when it gains under 0.5 mi of beautiful road. It
  is a server change the owner wants before submission. Judge whether the
  deploy should wait for it or ship now and redeploy (each restart costs a
  cold start, see below).
- **The deploy's own documentation:** `server/DEPLOY-oracle.md` Part 14 (*The
  national server*: disk, slow disk, memory check, the resize) and *Updating
  the box*, plus `docs/review-fixes-deploy.md`. They say none of the national
  figures has been measured on the box. Their estimates:
  - the national data is 19.7 GB on a 50 GB boot volume;
  - the copy takes about 14 min at about 24 MB/s;
  - a cold start reads 3.2 GB, about 2–3 min of 502s;
  - a full re-ship may not fit beside the live copy;
  - growing the boot volume to 100 GB is free, and "has not been done on this
    box".

## What to evaluate

Each item gets a verdict in the answer: **ready**, **blocks deploy**, **fix
before submission**, or **after**. Each comes with the evidence, labelled
*measured* (command, output) or *read* (file:line).

1. **The box, read-only.** Over ssh, run only these, and record the output:
   - `free -h`
   - `nproc`
   - `df -h ~/Scenic/data`
   - `lsblk`
   - `systemctl is-active sundaydrive-api cloudflared`
   - `cat ~/Scenic/DEPLOYED_COMMIT 2>/dev/null`
   - `curl -s 127.0.0.1:5057/api/health`

   Then run `server/deploy-oracle.sh --ref usa --dry-run`. It reads hashes and
   `df` and changes nothing. It may stop at its first check because `usa` is
   not pushed. If it does, record where, and say what the real run would need.

   Answer:
   - Is the RAM 12 GB?
   - Does the national data fit with the script's 2 GB margin, now and on the
     next re-ship?
   - Should the boot volume grow first?

   If ssh fails (a passphrase with no agent), say so and continue. Don't work
   around it.
2. **Push safety.** Pushing `usa` publishes 114 commits.
   - Search the range `origin/main..usa` (every commit's diff and message,
     not only the tip) for:
     - absolute paths (`/Users/`);
     - secrets: keys, tokens, `.p8`, `.pem`, passwords, Cloudflare or Oracle
       credentials;
     - anything derived from the private drive traces: street-level clock
       times, trace file names, `drive-2026-`;
     - large binaries;
     - anything quoting an outside review's findings file, whose findings stay
       out of the repo by the owner's decision. Briefs quoting their
       measurements are allowed.
   - Report each hit with its commit, and whether it is already public on
     `origin/main`.
   - Report the push's size.
   - Pushing over HTTPS to this origin can fail with HTTP 400 and then
     wrongly print "Everything up-to-date". The documented workaround is
     `git -c http.version=HTTP/1.1 push`. Note it, but **don't push**.
3. **The server at `usa` HEAD, on a local national server.**
   - **Routes and loops** from at least 12 states, spread over regions (the
     Northeast, Southeast, Midwest, Plains, Mountain West, Southwest, Pacific
     Northwest, California):
     - directions with and without `options=1`;
     - loops;
     - `/api/loop/limit`;
     - a reroute with a heading.
   - **Every error code** at least once: `OUTSIDE_COVERAGE`, `TRIP_TOO_LONG`,
     `LEG_TOO_LONG`, `NO_ROUTE_NEARBY`, `CLOSED_FOR_SEASON`, `BAD_INPUT`,
     `START_TOO_FAR`, `BUSY`.
   - **`/api/health` and `/api/health/route`.**
   - **A modest concurrency run**, about the plan's launch-day shape: mixed
     routes and loops, a few at a time, for a few minutes. Record:
     - latencies;
     - `503 BUSY` counts;
     - the server's `RssAnon` / RSS peak, against the box's 12 GB and Part
       14's 5.5 GB alarm line.

   Timings on this Mac are indicative only. Say how they relate to the box.
4. **Today's TestFlight builds against the national server.** The builds on
   testers' phones are `main`-era. Read `main`'s `ios/Sources/RouteService.swift`
   and models against `usa`'s server contract: error bodies with codes and
   numeric fields, the health fields, `/api/loop/limit`, and the menu
   (`options`). Will an installed build keep working, and what will a tester
   in New England see? Answer by reading, or by running `main`'s app in a
   simulator against your local national server if the reading is unclear.
5. **Operations.** For each, give its state and the owner's steps, from
   `DEPLOY-oracle.md`:
   - **Monitoring:** UptimeRobot's keyword must change to the national node
     count, and add a second monitor on `/api/health/route` (`route_ok`).
   - **The Cloudflare rate limit** (Part 11).
   - **Rollback.** Today `--region ne --allow-rewind` is a real rollback,
     because no national app is public. Should the previous pack be kept for
     a national rollback?
   - **What the deploy restarts, and for how long.**
6. **Review #4's server-side findings, as of `ea87a2a`.** For each, say whether
   it blocks the deploy, blocks submission, or comes later:
   - loop concurrency: a third concurrent loop gets `503 BUSY`, which is
     deliberate;
   - the review's island and ferry case;
   - raw TIGER road names in instructions ("CH 93", "County Highway 93" for
     CO 93);
   - ETAs fitted to New England speeds.

## Traps

1. **Deploy is not submission.** Holding the server back for an app-side or
   wording issue keeps testers on New England for no reason. Shipping a
   server that falls over, leaks something on push, or can't be rolled back
   is the real blocker. Keep the two lists apart.
2. **Read-only means read-only.** No push, no deploy, no restart, no
   `--rehash`, no edits on the box, no UptimeRobot or Cloudflare changes, no
   App Store Connect. A dry-run is allowed. If the dry-run's output says it
   would write, stop and report.
3. **One national server at a time** on this 24 GB Mac. A parallel
   low-scenery session also runs one. Check
   `ps -axo pid,rss,command | grep '[s]erve.py'`, and wait if a 2 GB+ one is
   up. Two national jobs have crashed this Mac before. Stop your server by PID
   only, never `pkill`.
4. **Production gets a handful of ordinary requests at most,** one at a time:
   health checks. It is still the New England build, and testers use it.
5. **The suite needs `processed-ne`,** not the default `data/processed`, which
   is an old one-state build and gives false failures.

## Done looks like

1. `docs/pre-deploy-audit.md` opens with a one-line verdict: **deploy now**,
   **deploy after X**, or **don't deploy**. Then two ranked lists, *before
   deploy* and *before submission*, each item with its evidence and the owner
   step or the change it needs.
2. The box's measured state (RAM, disk, services, the dry-run's result), or a
   statement that ssh was not available.
3. The push-safety scan's result, hit by hit, or "clean" with the commands
   that showed it.
4. The local national smoke and concurrency results, with the peak RSS.
5. The TestFlight-compatibility answer.
6. Whether the low-scenery fallback should land before the deploy, and why.
7. Nothing changed anywhere except that one document.
