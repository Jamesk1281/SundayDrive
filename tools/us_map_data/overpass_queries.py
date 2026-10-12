"""The few small Overpass queries this survey makes, one at a time.

  seasonal  the ground-truth roads of states whose extracts were not sampled
            (California's is 1.3 GB): their ways with geometry and node lists,
            and the barrier nodes on them, for seasonal_check.py;
  byways    every road-route relation, worldwide, whose network names a scenic
            or byway system or that carries scenic=yes, tags only;
  bywaynames  US road-route relations named for scenery whatever their network,
            tags only, so a byway extract.py cannot see by network or tag is
            still counted.

Usage: python -I overpass_queries.py <seasonal_roads.json> <state> <out.json>   (seasonal)
       python -I overpass_queries.py byways <out.json>
       python -I overpass_queries.py bywaynames <out.json>
"""

import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import request  # noqa: E402

API = "https://overpass-api.de/api/interpreter"


def run(query, timeout=400):
    status, _, body = request(API, method="POST",
                              data=urllib.parse.urlencode({"data": query}).encode(),
                              timeout=timeout, tries=2)
    if status != 200:
        raise SystemExit(f"Overpass HTTP {status}: {body[:400]!r}")
    return json.loads(body)


def seasonal_query(roads):
    parts = []
    for r in roads:
        w, s, e, n = r["bbox"]
        bb = f"({s},{w},{n},{e})"
        if r.get("name"):
            parts.append(f'way["highway"]["name"~"{r["name"]}",i]{bb};')
        if r.get("ref"):
            parts.append(f'way["highway"]["ref"~"{r["ref"]}"]{bb};')
    return ("[out:json][timeout:180];(" + "".join(parts) + ")->.w;"
            ".w out body geom;node(w.w)[\"barrier\"];out body;")


BYWAYS = """[out:json][timeout:300];
(
  rel["route"="road"]["network"~"scenic|byway|backway|parkway|NSB|AAR|tour",i];
  rel["route"="road"]["scenic"="yes"];
);
out tags;"""

BYWAY_NAMES = """[out:json][timeout:600];
area["ISO3166-1"="US"][admin_level=2]->.us;
rel(area.us)["route"="road"]["name"~"scenic|byway|backway|skyway|parkway",i];
out tags;"""


if __name__ == "__main__":
    if sys.argv[1] == "byways":
        Path(sys.argv[2]).write_text(json.dumps(run(BYWAYS)))
    elif sys.argv[1] == "bywaynames":
        Path(sys.argv[2]).write_text(json.dumps(run(BYWAY_NAMES, timeout=700)))
    else:
        roads = [r for r in json.load(open(sys.argv[1])) if r["state"] == sys.argv[2]]
        Path(sys.argv[3]).write_text(json.dumps(run(seasonal_query(roads))))
