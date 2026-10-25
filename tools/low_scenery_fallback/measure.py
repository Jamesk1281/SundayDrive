"""Send each trip to a local server the way the app does, one request at a
time, and write what came back. docs/low-scenery-fallback.md.

    python tools/low_scenery_fallback/measure.py http://127.0.0.1:55631 \
        trips.json out.jsonl menu plain

Modes, each one request per trip, in the order given:
  menu   options=1. The menu, when the server runs with
         SUNDAYDRIVE_ROUTE_OPTIONS=1 and nothing else is computing, which is
         why nothing here is ever sent concurrently.
  plain  no options: a reroute without a heading, or an app build that
         predates the menu. On code before the change, also the busy fallback.

On a server started with SUNDAYDRIVE_ROUTE_OPTIONS unset, `menu` is the busy
fallback as the current app gets it: options=1 sent, the menu not run.

The body is RouteService.routeRequest's: a form POST, pref 0.50, and the app's
default weights (BeautyType.all: every type 1.00, town 0.00).
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

WEIGHTS = {"coast": 1.0, "forest": 1.0, "town": 0.0, "water": 1.0,
           "hills": 1.0, "farm": 1.0}


def body(trip, mode):
    items = [("from", f"{trip['from'][0]},{trip['from'][1]}"),
             ("to", f"{trip['to'][0]},{trip['to'][1]}"),
             ("pref", "0.50")]
    items += [(f"w_{k}", f"{v:.2f}") for k, v in WEIGHTS.items()]
    if mode == "menu":
        items.append(("options", "1"))
    return urllib.parse.urlencode(items).encode()


def arm(feature):
    p = feature["properties"]
    return {k: p.get(k) for k in ("minutes", "km", "beautiful_km", "mean_score",
                                  "no_gain")} | {"switch": "switch" in p}


def ask(base, trip, mode):
    req = urllib.request.Request(f"{base}/api/route", data=body(trip, mode),
                                 method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            j = json.load(r)
            status = r.status
    except urllib.error.HTTPError as e:
        j, status = json.load(e), e.code
    out = {"id": trip["id"], "mode": mode, "status": status,
           "s": round(time.perf_counter() - t0, 2)}
    if status != 200:
        out["code"] = j.get("code")
        return out
    out["fastest"], out["scenic"] = arm(j["fastest"]), arm(j["scenic"])
    out["same"] = j["fastest"]["geometry"] == j["scenic"]["geometry"]
    if "options" in j:
        menu = j["options"]["menu"]
        out["options"] = {"default": j["options"]["default"],
                          "menu": [{"extra_minutes": o["extra_minutes"],
                                    "minutes": o["minutes"],
                                    "beautiful_km": o["beautiful_km"]}
                                   for o in menu]}
    return out


def main(base, trips_path, out_path, *modes):
    trips = json.load(open(trips_path))["trips"]
    done = set()
    try:
        for line in open(out_path):
            r = json.loads(line)
            done.add((r["id"], r["mode"]))
    except FileNotFoundError:
        pass
    with open(out_path, "a") as out:
        for n, trip in enumerate(trips):
            for mode in modes:
                if (trip["id"], mode) in done:
                    continue
                r = ask(base, trip, mode)
                out.write(json.dumps(r) + "\n")
                out.flush()
                print(n, trip["id"], mode, r["status"], r["s"], flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
