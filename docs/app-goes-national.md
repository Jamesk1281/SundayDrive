# The app goes national (unit C)

**Status:** day one, 2026-10-18. Branch `claude/app-goes-national`, cut from
local `usa` at 6fdf137. `ios/` only. The New England build on `main` keeps its
gating and is not touched.

## 1. Earliest honest date

| What | Earliest | Depends on |
|---|---|---|
| iPhone build with New England gating removed, coverage edges handled, tests rewritten, suite green against a local server on `processed-ne` | **Tue 20 Oct 2026** | nothing outside `ios/` |
| Same suite green against `processed-us` | **one day after unit A delivers `data/processed-us`** | A; and B's router, if the old one cannot load the national graph on this Mac |
| Release screenshots of drives outside New England | **one day after a server can answer for the whole country** | A and B |

The app side is not on the critical path for Thursday 29 October. A and B are.
What could move my date: the opening-camera fit for the whole country has to be
measured on the narrowest and widest phones, the way the New England box was,
and that is simulator time, not code.

What the app does in the meantime is honest: with a national build pointed at
today's New England server, a start in Colorado gets the server's own refusal
("point is outside the covered road network ..."), which the app passes
through as written (`RouteService.failure(status:body:)`).

## 2. Plan

The rest of this document is filled in as the work lands.
