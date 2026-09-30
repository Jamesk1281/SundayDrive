# Brief: take the coordinates out of the URL (release-plan §6e)

**Status: fixed in code 2026-09-29 on branch `claude/coordinates-out-of-url`,
not deployed.** The server change has to reach the Oracle box before a build
that sends POST reaches a phone (`server/DEPLOY-oracle.md`, "Updating the
code: server before phone"). What follows is the brief as written, unchanged.

Diagnosed and decided before the fix. Written 2026-09-29 against `main`
just after the redesign merge (`interface-redesign-from-nothing`). Nothing in
`ios/Sources`, `server/`, `tools/` or `tests/` has been touched for this. Every
`file:line` below is from that tree, and each one comes with its anchor text so
it still makes sense if the lines drift.

Answers [`release-plan.md`](release-plan.md) §6e. It is also item 1 of
[`privacy-policy.md`](privacy-policy.md) §7.

---

## 1. The goal, as measured

Every route and loop request puts the driver's start and destination in the
**URL query string**:

```
GET https://api.jameskouvlis.com/api/route?from=42.3601,-71.0589&to=44.3106,-69.7795&pref=0.50&w_coast=1.00…
GET https://api.jameskouvlis.com/api/loop?from=42.3601,-71.0589&km=40.0&pref=1.00…
```

Precision is full `Double`, not rounded. The builders interpolate
`"\(start.latitude),\(start.longitude)"` directly.

The hostname is a Cloudflare tunnel that **terminates TLS**
(`server/DEPLOY.md:8-14`). So Cloudflare's edge sees each full URL, and URLs are
what access logs record by default. `server/app.py` has no logger, no database
and no file writes. That makes "the server stores nothing" true of the code
and false of the system. The privacy policy says exactly this at
`privacy-policy.md` §2.1(a) ("**The request also passes through Cloudflare,
which can see the URL.**"). The owner decided (release-plan §8, Decision 3) that,
with no lawyer involved, **the fix is to remove the exposure, not to argue it
away**.

The goal: **no coordinate the app sends appears in any URL.** The coordinates
move into a POST body.

## 2. The mechanism: every place that has to change

**The client, which is the part that matters.**
`ios/Sources/RouteService.swift`:

- `static func route(from:to:via:pref:weights:heading:)`, about `:135-158`.
  It builds `URLComponents(string: "\(baseURL)/api/route")` with query items
  `from`, `to`, `pref`, `w_<type>…`, optional `heading`, optional `via`, then
  `return try await get(components.url!)`.
- `static func loop(from:km:sector:pref:weights:)`, about `:185-202`. Same
  shape, with `from`, `km`, `pref`, `w_<type>…`, optional `sector`.
- `private static func get<T: Decodable>(_ url: URL)`, about `:207-235`.
  It calls `try await session.data(from: url)`. This is the shared function for
  the status check and error handling, and it has to become a request-taking
  one (`session.data(for: URLRequest)`). **Keep its error handling exactly as it
  is.** The `URLError → .offline` mapping, lifting the server's `{"error": …}`
  message, and `.unreachable(status)` for HTML from a rate limiter or the tunnel
  are all load-bearing.

There are exactly three call sites, and none needs to change if the signatures
stay the same: `NavigationModel.swift:196` and `:202` (reroutes, the second with
`via:`), `RouteModel.swift:350` (planning), and `LoopModel.swift:92`.

**The server.** In `server/app.py`, `@app.get("/api/route")` (about `:222`) and
`@app.get("/api/loop")` (about `:299`) read everything from `request.args`,
directly (`request.args["from"]`, `request.args.get("pref", 0.5)`,
`request.args.get("via")`, `request.args.get("sector")`) and through
`_parse_heading(args)`, `_parse_weights(args)` and `_parse_avoid_unpaved(args)`
(about `:141-195`). All three helpers already take an `args` mapping, so they
work unchanged on `request.form`.

**Everything else that speaks this API:**

| file | what it does today |
| --- | --- |
| `tools/fake_api.py` | The redesign's stdlib dev backend (port 5099, `README.md` "fake backend" section). **Only `do_GET`.** Without a `do_POST` the app shows an error against it, and that is how every screen of the redesign is exercised without a graph |
| `ios/Tests/LiveDriveTests.swift:27` | Hand-builds its own `GET …/api/route?from=…` URL instead of going through `RouteService`. After the change it would still pass while testing a path the app no longer uses |
| `tests/test_api.py` | 46 `client.get("/api/route?…")` / `"/api/loop?…"` calls through Flask's test client |
| `README.md:82` | Documents `GET /api/route?from=LAT,LON&to=LAT,LON&pref=0..1…` as the API |
| `server/DEPLOY-oracle.md:718` | A `curl` smoke test by GET |
| `docs/privacy-policy.md` | §2.1(a) (the "which can see the URL" paragraph, about `:154-161`), §7 item 1 (about `:251-260`), and the §8 trigger "a move of coordinates out of the query string". **§8 says this change invalidates §2.1(a) and §7.1, so the edits belong in the same commit** |

## 3. The decisions, already taken so you don't reopen them

1. **Body encoding: `application/x-www-form-urlencoded`, same keys, same value
   formats.** `from=42.36,-71.05&to=…&pref=0.50&w_coast=1.00`, just moved from
   the URL into the body. Flask exposes it as `request.form`, a `MultiDict` like
   `request.args`, so every parse helper and every error message keeps working,
   and the server change is one line per endpoint (see §4, trap 3). JSON was
   considered and rejected. It changes value types (`"0.50"` becomes `0.5`, and
   `from` has to become either a two-element array or a string that is still
   parsed by hand). Either way that means a second parse path and new error
   messages, for no privacy gain. Build the body in Swift with
   `URLComponents().percentEncodedQuery` from the same `queryItems` the code
   builds today, and set `Content-Type` explicitly.
2. **The server accepts both GET and POST, and the app sends only POST.** The
   Oracle box and the owner's installed phone build both speak GET today. The
   server has to accept POST *before* any app build that sends it is installed,
   and the installed build keeps working in the meantime. The curl smoke tests in
   the deploy docs keep working too. The privacy guarantee lives in what the
   **app** sends, and that is what the policy describes. Removing GET later is a
   separate, deliberate change. Do not do it here.
3. **`/api/health` and `/` stay GET.** They carry no coordinates.

## 4. Traps

1. **Leaving the query items on the URL while also sending a body.** Flask
   reads `request.args` on a POST, so a half-converted client, one that sets
   `httpMethod = "POST"` and a body but still hands `components.url!` with
   `queryItems` attached, **works perfectly and fixes nothing**. Every test
   passes, and the coordinates stay in the URL. This is the most likely way this
   change ships wrong. It is also why §5 item 1 is a unit test on the built
   `URLRequest`, not a live call.
2. **Rewriting the 46 GET calls in `tests/test_api.py` to POST.** GET stays
   supported (decision 2), so those tests stay valid, and churning them buries
   the change. Add **parity** tests instead. Send the same parameters by GET and
   by POST (form) for `/api/route`, `/api/route` with `via`, and `/api/loop`,
   and assert the JSON bodies are identical. Also cover the 400 path by POST
   (missing `from`).
3. **`request.values` on the server.** It merges `args` and `form`, which looks
   like the neat one-liner. It is not a bug, but it makes the server silently
   accept trap 1's half-converted client, so no server-side test could ever
   notice. Use `args = request.form if request.method == "POST" else
   request.args` and read from `args` throughout, including the direct
   `request.args[...]` and `request.args.get(...)` reads in both handlers. Miss
   one of those and that parameter is silently ignored on POST: `sector` on
   loops, and `via` on routes, which is the loop-rejoin reroute.
4. **Overclaiming in the policy.** POST does **not** remove Cloudflare from the
   path. The tunnel still terminates TLS and can read the body. The honest new
   wording: coordinates travel in the request body rather than the URL, so they
   are not in the URLs that access logs record by default, *and* Cloudflare can
   still technically read them. Cloudflare stays named as a processor. **The
   privacy manifest does not change.** Precise location stays declared as
   collected (release-plan §6e, §8 Decision 3). Don't touch
   `ios/Sources/PrivacyInfo.xcprivacy`.
5. **A hypothesis, not a finding: POST loses transport-level retries.**
   CFNetwork will silently retry an idempotent GET on a reused connection that
   the peer closed. It will not retry a POST. Mid-drive on a patchy signal, that
   could turn a few invisible retries into `.offline` errors. The app already
   recovers: `NavigationModel` retries a failed reroute on its 8-second cooldown
   (comment near `:916`). So the likely cost is one extra cooldown cycle, not a
   stuck drive. Evidence for it: Apple's documented idempotency behaviour.
   What would kill it: nothing cheap. **Do not "fix" this by adding a retry
   loop to `RouteService`.** Note it in the commit message and move on.

## 5. Done looks like

1. **A unit test that the app's requests carry no coordinates in the URL.**
   Factor request construction into internal functions (for example
   `RouteService.routeRequest(...) -> URLRequest` and `loopRequest(...)`) and
   assert, for a route with `via` and `heading` and a loop with `sector`:
   `httpMethod == "POST"`, `url?.query == nil`, the URL string contains no
   digit sequence of either coordinate, `Content-Type` is form-encoded, and the
   body decodes to exactly the keys and values sent today.
2. **The server accepts POST on `/api/route` and `/api/loop`**, reading every
   parameter from the form (trap 3), with GET unchanged. Parity tests as in
   trap 2. The backend suite stays green (see below for the baseline).
3. **`tools/fake_api.py` answers POST** with the same behaviour as its GET.
4. **`LiveDriveTests` exercises the POST path**, ideally through `RouteService`
   itself rather than a hand-built URL.
5. **`privacy-policy.md` §2.1(a), §7 item 1 and §8 are updated in the same
   commit**, worded per trap 4. `README.md:82` documents POST as the app's call
   and GET as still accepted.
6. **A deployment note in the commit message and in `server/DEPLOY-oracle.md`**:
   the server change must be deployed to the Oracle box (`git pull` plus
   `systemctl restart sundaydrive-api`) **before** a POST-sending build goes
   onto a phone. You cannot deploy it yourself. The box's SSH key has a
   passphrase and needs the owner's `ssh-add`. Say so. Do not try.

Out of scope: removing GET, anything about Cloudflare's own logging
configuration, the privacy manifest, and §6d (the drive that never ends, which
lives in `NavigationModel.swift`, the file this change must **not** edit).
