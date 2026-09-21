#!/usr/bin/env python3
"""A fake backend, so the app can be driven without a graph.

**This is a fixture, not a router.** Every number it returns is invented from a
straight line between two points. Nothing here is measured, nothing here came
out of `pipeline/`, and no figure it prints is evidence of anything. It exists
for one reason: to make the interface usable — the dial, the ledger, the
breakdown, the loop card, the driving screen and the arrival card all need a
`RouteResponse` to have anything to say, and standing up the real server needs
the New England graph, several gigabytes of RAM and a rebuild.

Use it to look at the app. Never quote it.

What it does get right, because otherwise the dial would be a lie about a lie:

* **The preference curve.** `strength = pref ** 2` (`PREF_CURVE` at
  `pipeline/router.py:152`), so dragging the dial moves the numbers the way the
  real router moves them — flat at the bottom, biting in the upper half.
* **The ceiling.** The scenic arm tops out at 1.61x the fastest arm's travel
  time, which is the measured cap.
* **`pref == 0` is the fastest route, exactly**, the same short-circuit
  `server/app.py` takes — so the left end of the dial behaves as the interface
  claims it does.
* **The per-type weights do something.** `w_coast=2.0` really does move coastal
  kilometres into the breakdown, so the *What you like* sheet is testable.

Run it:

    python3 tools/fake_api.py                  # 127.0.0.1:5099
    python3 tools/fake_api.py --port 5057      # or stand in for the dev server

Point the app at it: see the "Running the app without a backend" section of the
README.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# `pipeline/router.py:152`. The one number here that is not invented.
PREF_CURVE = 2.0

# The measured ceiling on what the dial can spend. It is a *ceiling*, not a
# typical value — over 252 sampled pairs the top of the dial averaged +28.1 min
# (`docs/route-distribution-study.md`, Q3), so this fixture climbs to
# TOP_TIME_MULTIPLE and leaves the cap above it where it belongs.
MAX_TIME_MULTIPLE = 1.61
TOP_TIME_MULTIPLE = 1.45

# Roughly the share of a fast route that scores 7+, and the share the scenic arm
# reaches at full strength. Shaped to look like the real distribution's ends;
# not fitted to it.
BEAUTIFUL_SHARE_FAST = 0.09
BEAUTIFUL_SHARE_SCENIC = 0.34

# Keep in sync with SCENERY_BREAKDOWN in pipeline/router.py and with
# `RouteProps.sceneryBreakdown`. The second number is the share of a *scenic*
# route this type takes when every weight is neutral.
BUCKETS = {
    "forest/park": ("forest", 0.34),
    "water": ("water", 0.16),
    "coast": ("coast", 0.14),
    "hills": ("hills", 0.12),
    "farmland": ("farm", 0.16),
    "town": ("town", 0.08),
}

ROADS = ["Great Plain Ave", "Route 127", "Eastern Ave", "Essex Ave", "Old Bay Rd",
         "River Rd", "Meetinghouse Hill Rd", "Route 2A", "Mill Brook Rd", "Ridge Rd"]

SECTORS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
SECTOR_BEARING = {s: i * 45 for i, s in enumerate(SECTORS)}


def haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0088 * 2 * math.asin(math.sqrt(h))


def wander(a, b, bulge, wiggle, n=180):
    """A line from a to b that bows sideways and twitches, so the two arms are
    visibly different shapes on the map rather than one drawn over the other."""
    dlat, dlon = b[0] - a[0], b[1] - a[1]
    # Unit normal, so the bow is perpendicular to the trip whichever way it runs.
    length = math.hypot(dlat, dlon) or 1e-9
    nlat, nlon = -dlon / length, dlat / length
    pts = []
    for i in range(n + 1):
        t = i / n
        arc = math.sin(t * math.pi)
        lat = a[0] + dlat * t + nlat * bulge * arc
        lon = a[1] + dlon * t + nlon * bulge * arc
        lat += math.sin(t * 17) * wiggle * arc
        lon += math.cos(t * 23) * wiggle * arc
        pts.append([round(lon, 6), round(lat, 6)])
    return pts


def steps_along(coords, km):
    """Four to eight maneuvers, so the driving screen has something to say and
    `currentRoad` has a name to show."""
    names = random.sample(ROADS, k=min(len(ROADS), max(4, min(8, int(km / 9)))))
    out = [{"instruction": f"Head out on {names[0]}", "type": "depart",
            "modifier": None, "name": names[0],
            "lat": coords[0][1], "lon": coords[0][0],
            "distance_m": km * 1000 / (len(names) + 1)}]
    for i, name in enumerate(names[1:], start=1):
        at = coords[int(len(coords) * i / (len(names) + 1))]
        side = "left" if i % 2 else "right"
        out.append({"instruction": f"Turn {side} onto {name}", "type": "turn",
                    "modifier": side, "name": name,
                    "lat": at[1], "lon": at[0],
                    "distance_m": km * 1000 / (len(names) + 1)})
    out.append({"instruction": "Arrive at your destination", "type": "arrive",
                "modifier": None, "name": "",
                "lat": coords[-1][1], "lon": coords[-1][0], "distance_m": 0.0})
    return out


def scenery(km, weights, scenic_share):
    """Kilometres per bucket, tilted by the caller's `w_*`.

    Neutral is 1.0, so a type dragged to 2.0 roughly doubles its share and one
    dragged to 0 disappears — which is what makes the *What you like* sheet
    worth opening.
    """
    shares = {}
    for key, (api_name, base) in BUCKETS.items():
        w = weights.get(api_name, 1.0)
        shares[key] = base * w
    total = sum(shares.values()) or 1.0
    # A fast route passes less of everything except towns.
    covered = km * (0.35 + 0.55 * scenic_share)
    out = {}
    for key, share in shares.items():
        value = covered * share / total
        if key == "town":
            value = km * (0.19 - 0.12 * scenic_share) * max(0.0, weights.get("town", 1.0))
        if value >= 0.9:                    # under a mile the app drops the row anyway
            out[key] = round(value, 2)
    return out


def feature(coords, km, minutes, mean, beautiful, scenery_km):
    return {
        "geometry": {"coordinates": coords},
        "properties": {
            "km": round(km, 2),
            "minutes": round(minutes, 1),
            "mean_score": round(mean, 2),
            "beautiful_km": round(beautiful, 2),
            "beautiful_score": 7.0,
            "scenery_km": scenery_km,
            "steps": steps_along(coords, km),
        },
    }


def route(start, end, pref, weights):
    strength = min(1.0, max(0.0, pref)) ** PREF_CURVE
    direct = max(0.6, haversine_km(start, end))
    fast_km = direct * 1.15                 # roads are not straight lines
    fast_min = fast_km / 76.0 * 60.0        # ~76 km/h door to door

    fast = feature(wander(start, end, 0.012, 0.0009),
                   fast_km, fast_min, 4.1,
                   fast_km * BEAUTIFUL_SHARE_FAST,
                   scenery(fast_km, weights, 0.0))
    if pref <= 0.0:
        # `server/app.py` short-circuits here: at pref 0 the scenic arm *is* the
        # fastest arm, and the dial's left end depends on that being exact.
        return {"fastest": fast, "scenic": fast}

    scenic_km = fast_km * (1 + 0.24 * strength)
    scenic_min = min(fast_min * MAX_TIME_MULTIPLE,
                     fast_min * (1 + (TOP_TIME_MULTIPLE - 1) * strength))
    share = BEAUTIFUL_SHARE_FAST + (BEAUTIFUL_SHARE_SCENIC - BEAUTIFUL_SHARE_FAST) * strength
    scenic = feature(wander(start, end, 0.012 + 0.26 * strength, 0.0016 + 0.002 * strength),
                     scenic_km, scenic_min, 4.1 + 1.9 * strength,
                     scenic_km * share,
                     scenery(scenic_km, weights, strength))
    return {"fastest": fast, "scenic": scenic}


def loop(start, km, sector, weights):
    sector = sector or random.choice(SECTORS)
    bearing = math.radians(SECTOR_BEARING.get(sector, 0))
    radius = km / (2 * math.pi) / 111.0     # degrees, near enough at this latitude
    centre = (start[0] + math.cos(bearing) * radius * 1.05,
              start[1] + math.sin(bearing) * radius * 1.05 / math.cos(math.radians(start[0])))
    coords, n = [], 190
    for i in range(n + 1):
        t = i / n * 2 * math.pi
        r = radius * (1 + 0.16 * math.sin(t * 3) + 0.08 * math.cos(t * 5))
        coords.append([
            round(centre[1] + r * math.sin(t) / math.cos(math.radians(start[0])), 6),
            round(centre[0] + r * math.cos(t) - radius * 1.05, 6),
        ])
    coords[0] = coords[-1] = [round(start[1], 6), round(start[0], 6)]

    actual = km * random.uniform(0.98, 1.07)
    minutes = actual / 52.0 * 60.0          # loops use smaller roads than a trip does
    beautiful = actual * random.uniform(0.55, 0.68)
    # Short loops from one point genuinely have to reuse road; long ones do not.
    repeated = 0.0 if km > 24 else actual * random.uniform(0.12, 0.3)
    turnaround = [centre[0] + radius, centre[1]]

    return {
        "loop": feature(coords, actual, minutes, 6.3, beautiful,
                        scenery(actual, weights, 0.9)),
        "meta": {
            "target_km": km, "km": round(actual, 2), "minutes": round(minutes, 1),
            "mean_score": 6.3, "beautiful_km": round(beautiful, 2),
            "beautiful_score": 7.0, "repeated_km": round(repeated, 2),
            "turnaround": [round(turnaround[0], 6), round(turnaround[1], 6)],
            "sector": sector,
        },
        # Five of eight, which is what a real start with water or a state line
        # near it offers — the regenerate button should not imply eight.
        "alternatives": [{"sector": s, "candidates": random.randint(2, 9)}
                         for s in random.sample(SECTORS, 5)],
        "note": None,
    }


def latlon(raw):
    lat, lon = raw.split(",")
    return float(lat), float(lon)


def weights_from(query):
    out = {}
    for key, values in query.items():
        if key.startswith("w_"):
            try:
                out[key[2:]] = float(values[0])
            except ValueError:
                pass
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "VictoryLapFakeAPI/1"

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    def _send(self, payload, status=200):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/":
                self._send({"service": "victory-lap fake api",
                            "warning": "every number here is invented; see tools/fake_api.py"})
            elif url.path == "/api/route":
                self._send(route(latlon(q["from"][0]), latlon(q["to"][0]),
                                 float(q.get("pref", ["0.5"])[0]), weights_from(q)))
            elif url.path == "/api/loop":
                self._send(loop(latlon(q["from"][0]),
                                float(q.get("km", ["40"])[0]),
                                (q.get("sector") or [None])[0],
                                weights_from(q)))
            else:
                self._send({"error": f"no such endpoint: {url.path}"}, status=404)
        except (KeyError, ValueError) as exc:
            # The app renders a backend's own `error` verbatim, so say something
            # a person could act on.
            self._send({"error": f"fake api couldn't read that request ({exc})"}, status=400)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=5099)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--seed", type=int, default=None,
                        help="fix the randomness, for a reproducible screenshot")
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    print(f"fake api on http://{args.host}:{args.port}  —  every number is invented")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
