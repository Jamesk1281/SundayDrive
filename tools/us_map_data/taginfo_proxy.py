"""Tier 1: tag coverage for all 50 states + DC from Geofabrik's per-state taginfo.

These are OBJECT COUNTS, a proxy only. Taginfo counts OSM objects, not
kilometres, and a short residential stub counts the same as a 20 km pass. Two
proxies are built so the findings can say how much the choice matters:

  class proxy   restricted to ways whose `highway=` is in pipeline/common.py's
                DRIVABLE, summed over the 13 classes from one
                `tag/combinations` call per class (the access rule and the
                connected component cannot be applied: taginfo cannot see them);
  naive proxy   the key's share of every `highway=*` way, footways and service
                roads included, which is what a quick look at taginfo gives.

Per state it also records node counts for signals, stops and give-ways, and
relation counts for turn restrictions, both over the whole file rather than on
the graph. osm_metrics.py measures the same things by km on the sampled states,
and summarize.py reports how well each proxy predicts them.

Raw answers are cached in <cache_dir> so a rerun costs no requests.

Usage: python -I taginfo_proxy.py <osm_extract_sizes.csv> <cache_dir> <out.csv>
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import get_json  # noqa: E402

BASE = "https://taginfo.geofabrik.de/north-america:us:{slug}/api/4/"
DRIVABLE = ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
            "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified",
            "residential", "living_street"]
MAIN = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential"]
# score.py's UNPAVED, repeated here so the proxy does not import the pipeline.
UNPAVED = {"unpaved", "compacted", "fine_gravel", "gravel", "shells", "rock", "pebblestone",
           "ground", "dirt", "earth", "grass", "grass_paver", "mud", "sand", "woodchips",
           "snow", "ice", "salt"}
VBAD = {"very_bad", "horrible", "very_horrible", "impassable"}
COND_KEYS = ["access:conditional", "vehicle:conditional", "motor_vehicle:conditional",
             "motorcar:conditional"]


def cached(cache, name, url, params):
    p = cache / f"{name}.json"
    if p.exists():
        return json.loads(p.read_text())
    status, data, body = get_json(url, params)
    if status != 200 or data is None:
        raise SystemExit(f"{url} {params}: HTTP {status} {body[:200]!r}")
    p.write_text(json.dumps(data))
    return data


def state_proxy(slug, cache):
    base = BASE.format(slug=slug)
    cache = cache / slug
    cache.mkdir(parents=True, exist_ok=True)

    def get(name, path, **params):
        return cached(cache, name, base + path, params)

    def all_rows(name, path, **params):
        params.update(rp=999, page=1, sortname="count" if "values" in path else
                      "together_count", sortorder="desc")
        return get(name, path, **params)["data"]

    hv = {d["value"]: d["count"] for d in all_rows("values_highway_ways", "key/values",
                                                   key="highway", filter="ways")}
    count = {hw: hv.get(hw, 0) for hw in DRIVABLE}
    combos = {hw: get(f"comb_highway_{hw}", "tag/combinations", key="highway", value=hw,
                      filter="ways", rp=999, page=1, sortname="together_count",
                      sortorder="desc") for hw in DRIVABLE}
    hw_ways = sum(hv.values())
    # The naive ratio: ways carrying the key and any highway= over all highway
    # ways, footways and service roads included.
    kc = all_rows("comb_key_highway", "key/combinations", key="highway", filter="ways")
    naive = {k: round(100 * next((d["together_count"] for d in kc if d["other_key"] == k), 0)
                      / hw_ways, 2) for k in ("maxspeed", "surface")}
    hn = {d["value"]: d["count"] for d in all_rows("values_highway_nodes", "key/values",
                                                   key="highway", filter="nodes")}
    rs = get("stats_type_restriction", "tag/stats", key="type", value="restriction")
    restr = next(d["count"] for d in rs["data"] if d["type"] == "relations")

    def together(hw, key, value=""):
        return next((x["together_count"] for x in combos[hw]["data"]
                     if x["other_key"] == key and x["other_value"] == value), 0)

    def rare_tag(key, value):
        # A rare tag is absent from the class lists (taginfo only pairs
        # frequent keys), so count it from its own side: the drivable
        # highway values among its combinations.
        rows = all_rows(f"comb_{key}_{value}".replace(":", "_").replace(";", "_"),
                        "tag/combinations", key=key, value=value, filter="ways")
        return sum(d["together_count"] for d in rows
                   if d["other_key"] == "highway" and d["other_value"] in DRIVABLE)

    def rare_key_any_highway(key):
        # Key level only: the count is over every highway= way, tracks and
        # paths included, so it overstates the drivable share.
        rows = all_rows(f"comb_key_{key}".replace(":", "_"), "key/combinations",
                        key=key, filter="ways")
        return next((d["together_count"] for d in rows if d["other_key"] == "highway"), 0)

    total = sum(count.values())
    pct = lambda n: round(100 * n / total, 3) if total else None
    row = {"slug": slug, "drivable_ways": total, "highway_ways": hw_ways,
           "data_until": combos["residential"].get("data_until", "")}
    for hw in MAIN:
        row[f"maxspeed_pct_{hw}"] = round(100 * together(hw, "maxspeed") / count[hw], 2) \
            if count[hw] else None
    row["surface_tagged_pct"] = pct(sum(together(hw, "surface") for hw in DRIVABLE))
    row["unpaved_pct"] = pct(sum(together(hw, "surface", v) for hw in DRIVABLE for v in UNPAVED))
    row["smoothness_tagged_pct"] = pct(sum(together(hw, "smoothness") for hw in DRIVABLE))
    row["smoothness_vbad_pct"] = pct(sum(together(hw, "smoothness", v)
                                         for hw in DRIVABLE for v in VBAD))
    row["tracktype_pct"] = pct(sum(together(hw, "tracktype") for hw in DRIVABLE))
    row["tiger_reviewed_no_pct"] = pct(sum(together(hw, "tiger:reviewed", "no")
                                           for hw in DRIVABLE))
    row["tiger_cfcc_pct"] = pct(sum(together(hw, "tiger:cfcc") for hw in DRIVABLE))
    row["4wd_only_pct"] = pct(rare_tag("4wd_only", "yes"))
    # Too rare for taginfo to pair with anything by value (Colorado's 35
    # `seasonal=summer` ways have no combinations at all), so key level, any
    # value including `no`, any highway.
    row["seasonal_any_highway_ways"] = rare_key_any_highway("seasonal")
    row["winter_service_any_highway_ways"] = rare_key_any_highway("winter_service")
    row["car_conditional_any_highway_ways"] = sum(rare_key_any_highway(k) for k in COND_KEYS)
    row["naive_maxspeed_pct"] = naive["maxspeed"]
    row["naive_surface_pct"] = naive["surface"]
    row["signals_nodes"] = hn.get("traffic_signals", 0)
    row["stops_nodes"] = hn.get("stop", 0)
    row["giveway_nodes"] = hn.get("give_way", 0)
    row["restriction_relations"] = restr
    row["class_combos_truncated"] = ";".join(
        hw for hw in DRIVABLE if combos[hw]["total"] > len(combos[hw]["data"]))
    # Geofabrik's Texas instance has no combination statistics at all (every
    # class returns total 0 on 2026-10-08), which would read as 0% of
    # everything; listed so summarize.py can leave those proxies blank.
    row["class_combos_empty"] = ";".join(
        hw for hw in DRIVABLE if count[hw] and combos[hw]["total"] == 0)
    return row


if __name__ == "__main__":
    sizes, cache, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    slugs = [r["slug"] for r in csv.DictReader(open(sizes)) if r["scope"] == "in"]
    rows = []
    for slug in slugs:
        rows.append(state_proxy(slug, cache))
        print(slug, rows[-1]["drivable_ways"], flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
