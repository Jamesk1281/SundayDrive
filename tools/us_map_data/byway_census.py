"""Byway census: every scenic or byway road-route network, state by state.

extract.py admits a road-route relation as a byway when its network is in
BYWAY_NETWORKS (New England's five) or it carries scenic=yes. This counts, for
the 50 states + DC, what that rule admits and what it misses:

  networks   relation `network=` values naming a scenic or byway system, from
             each state's taginfo (`key/values` on relations; one cached call
             per state). A network crossing a border appears in both extracts,
             so each is assigned to the state its `US:XX:` prefix names;
  scenic     every road-route relation tagged scenic=yes, from one Overpass
             query (overpass_queries.py), grouped by network. A scenic=yes on a
             whole numbered-highway relation (US:US, US:I, US:XX) is flagged:
             extract.py would make every km of that highway a byway, as it did
             with US 34 across Colorado's plains.

  placed     the scenic=yes relations with no network at all, which only their
             member geometry can place: Overpass's `out center` for each, put in
             a state by the Census 2023 outlines (none of them can be admitted
             or missed by network, so they are what the tag clause alone buys).

Usage: python -I byway_census.py <osm_extract_sizes.csv> <taginfo_cache> <scenic_yes.json>
                                 <no_network_centers.json> <states.zip>
                                 <out.csv> <out_scenic_yes.csv>
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taginfo_proxy import BASE, cached  # noqa: E402

# extract.py's BYWAY_NETWORKS, repeated so this needs no pipeline import.
BYWAY_NETWORKS = {"US:MA:Scenic", "US:VT:byway", "US:AB:NSB:Connecticut River",
                  "US:NY:Scenic", "CA:NB:scenic"}
WORD = re.compile(r"scenic|byway|backway|parkway|nsb|aar|tour|heritage|trail", re.IGNORECASE)
NUMBERED = re.compile(r"^US:(US|I|[A-Z]{2})$")


def main():
    sizes, cache, scenic_path, centers_path, states_zip, out, out_scenic = (
        sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6],
        sys.argv[7])
    import geopandas as gpd
    import shapely
    outlines = gpd.read_file(f"zip://{states_zip}")
    outlines = outlines[~outlines["STATEFP"].isin({"60", "66", "69", "72", "78"})]
    centers = {e["id"]: e.get("center") for e in json.load(open(centers_path))["elements"]}

    def state_of(c):
        if not c:
            return ""
        hit = outlines[outlines.contains(shapely.Point(c["lon"], c["lat"]))]
        return hit["STUSPS"].iloc[0] if len(hit) else ""
    rows = list(csv.DictReader(open(sizes)))
    slugs = [r["slug"] for r in rows if r["scope"] == "in"]
    found = defaultdict(lambda: {"relations": 0, "seen_in": set()})
    for slug in slugs:
        data = cached(cache / slug, "values_network_relations", BASE.format(slug=slug) +
                      "key/values", {"key": "network", "filter": "relations", "rp": 999,
                                     "page": 1, "sortname": "count", "sortorder": "desc"})
        for d in data["data"]:
            net = d["value"]
            if not net.upper().startswith("US") or not WORD.search(net):
                continue
            f = found[net]
            # The largest count seen is the home extract's (a border network
            # also appears, partially, in its neighbours' extracts).
            f["relations"] = max(f["relations"], d["count"])
            f["seen_in"].add(slug)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["network", "state", "relations", "admitted_by_network", "seen_in"])
        for net, f in sorted(found.items()):
            parts = net.split(":")
            st = parts[1] if len(parts) > 1 and len(parts[1]) == 2 else ""
            w.writerow([net, st, f["relations"], net in BYWAY_NETWORKS,
                        ";".join(sorted(f["seen_in"]))])
    sc = json.load(open(scenic_path))["elements"]
    with open(out_scenic, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["relation", "network", "state", "ref", "name", "numbered_highway"])
        for e in sc:
            t = e.get("tags", {})
            net = t.get("network", "")
            if net and not net.upper().startswith("US"):
                continue
            if net:
                parts = net.split(":")
                state = parts[1] if len(parts) > 1 and len(parts[1]) == 2 else ""
            else:
                state = state_of(centers.get(e["id"]))
                if not state:
                    continue                  # outside the 50 states + DC
            w.writerow([e["id"], net, state, t.get("ref", ""), t.get("name", ""),
                        bool(NUMBERED.match(net))])
    print(f"{len(found)} US networks name a scenic system; scenic=yes relations written")


if __name__ == "__main__":
    main()
