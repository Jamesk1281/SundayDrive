"""Tables for docs/us-map-data-findings.md from the measured and proxy results.

  osm_quality_measured.csv  one row per sampled state: osm_metrics.py's km-
                            weighted figures (tier 2);
  proxy_vs_measured.csv     each tier-1 taginfo proxy beside the tier-2 value it
                            stands for, per state;
  proxy_accuracy.csv        per metric, across the sampled states: Pearson r,
                            the proxy's mean absolute error as it stands, and
                            after a straight-line calibration scored leave-one-
                            out, which is what using the proxy for an unsampled
                            state would cost;
  osm_quality_all_states.csv  every state's proxies, and for the metrics where
                            the calibration helps, the calibrated estimate of
                            the km value (measured where the state was sampled).

Signals per 100 km and restrictions per 1,000 junctions have no km or
junctions in taginfo, so their proxies divide node and relation counts by FHWA
HM-20 public road km and by drivable way count respectively, the nearest
denominators that need no download.

Usage: python -I summarize.py <metrics_dir> <results_dir> <fhwa_hm20_states.csv>
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np

MAIN = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential")
KM_PER_MI = 1.609344


def measured_row(d):
    s, r, t, sea = d["surface"], d["roughness"], d["tiger"], d["seasonal"]
    km = d["graph_km"]
    row = {"state": d["label"], "graph_nodes": d["graph_nodes"], "graph_km": round(km),
           "terrarium_tiles_with_graph": d["terrarium_z11_tiles_with_graph"]}
    for h in MAIN:
        m = d["maxspeed"][h]
        row[f"maxspeed_pct_{h}"] = m["tagged_pct"]
        row[f"maxspeed_hm_{h}"] = m["tagged_hm_kmh"]
    for h in ("trunk", "primary", "secondary", "tertiary", "unclassified", "residential"):
        m = d["maxspeed"][h]
        row[f"speed_vs_default_{h}"] = (round(100 * (m["tagged_hm_kmh"] / m["default_kmh"] - 1), 1)
                                        if m["tagged_hm_kmh"] else None)
    row.update({
        "maxspeed_any_pct": d["maxspeed_any_tag_pct"],
        "surface_tagged_pct": s["tagged_pct"], "unpaved_pct": s["unpaved_pct"],
        "unpaved_pct_unclassified": s["unpaved_pct_by_class"]["unclassified"],
        "smoothness_tagged_pct": r["smoothness_tagged_pct"],
        "rough_bad_km": r["smoothness_bad_or_worse_km"],
        "4wd_only_km": r["4wd_only_km"], "4wd_or_very_bad_km": r["4wd_or_very_bad_km"],
        "4wd_or_very_bad_pct": round(100 * r["4wd_or_very_bad_km"] / km, 3),
        "4wd_only_pct": round(100 * r["4wd_only_km"] / km, 3),
        "tracktype_grade3plus_km": r["tracktype_grade3plus_km"],
        "tiger_cfcc_a5_km": r["tiger_cfcc_a5_km"],
        "tiger_cfcc_a5_unflagged_km": r["tiger_cfcc_a5_untagged_rough_km"],
        "tiger_reviewed_no_pct": t["reviewed_no_pct"], "tiger_origin_pct": t["tiger_origin_pct"],
        "signals_per_100km": d["controls"]["per_100km"].get("signal", 0.0),
        "stops_per_100km": d["controls"]["per_100km"].get("stop", 0.0),
        "giveway_per_100km": d["controls"]["per_100km"].get("giveway", 0.0),
        "restrictions_via_node_per_1000_junctions":
            d["turn_restrictions"]["via_node_per_1000_junctions"],
        "restrictions_via_way_per_1000_junctions":
            d["turn_restrictions"]["via_way_per_1000_junctions"],
        "seasonal_closed_km": sea["closures_py_closes_km"],
        "car_conditional_km": sea["car_conditional_km"],
        "conditional_unrecognized_km": sea["car_conditional_km_by_verdict"].get("unrecognized", 0.0),
        "conditional_ordinal_fixable_km": sea["car_conditional_ordinal_fixable_km"],
        "permit_closed_km": sea["permit_km"],
        "closed_all_year_km": sea["closed_to_cars_or_ford_km"],
        "timed_barriers_on_graph": d["timed_barriers_on_graph"]["count"],
    })
    return row


def main():
    mdir, rdir, fhwa_csv = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    meas = {}
    for p in sorted(mdir.glob("*.json")):
        d = json.load(open(p))
        meas[d["label"]] = measured_row(d)
    rows = [meas[k] for k in sorted(meas)]
    with open(rdir / "osm_quality_measured.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    proxy = {r["slug"]: r for r in csv.DictReader(open(rdir / "taginfo_proxy.csv"))}
    fhwa = {r["state"].lower().replace(" ", "-"): r for r in csv.DictReader(open(fhwa_csv))}
    pairs = [(f"maxspeed_pct_{h}", f"maxspeed_pct_{h}") for h in MAIN] + [
        ("surface_tagged_pct", "surface_tagged_pct"), ("unpaved_pct", "unpaved_pct"),
        ("smoothness_tagged_pct", "smoothness_tagged_pct"),
        ("tiger_reviewed_no_pct", "tiger_reviewed_no_pct"),
        ("4wd_only_pct", "4wd_only_pct"),
        ("naive_maxspeed_pct", "maxspeed_any_pct"), ("naive_surface_pct", "surface_tagged_pct"),
    ]
    table, acc = [], []
    for state, m in meas.items():
        p = proxy[state]
        public_km = (int(fhwa[state]["urban_mi"]) + int(fhwa[state]["rural_mi"])) * KM_PER_MI
        extra = {
            "signals_per_100km": 100 * int(p["signals_nodes"]) / public_km,
            "restrictions_per_1000": 1000 * int(p["restriction_relations"]) / int(p["drivable_ways"]),
        }
        for pk, mk in pairs:
            table.append({"state": state, "metric": f"{pk} -> {mk}", "proxy": float(p[pk]),
                          "measured": float(m[mk]) if m[mk] is not None else None})
        table.append({"state": state, "metric": "signal nodes / FHWA km -> signals_per_100km",
                      "proxy": round(extra["signals_per_100km"], 3),
                      "measured": m["signals_per_100km"]})
        table.append({"state": state, "metric": "restriction relations / drivable ways -> "
                      "via-node restrictions per 1000 junctions",
                      "proxy": round(extra["restrictions_per_1000"], 3),
                      "measured": m["restrictions_via_node_per_1000_junctions"]})
    with open(rdir / "proxy_vs_measured.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["state", "metric", "proxy", "measured"])
        w.writeheader()
        w.writerows(table)
    for metric in dict.fromkeys(r["metric"] for r in table):
        xs = np.array([r["proxy"] for r in table if r["metric"] == metric and r["measured"] is not None])
        ys = np.array([r["measured"] for r in table if r["metric"] == metric and r["measured"] is not None])
        n = len(xs)
        r_ = float(np.corrcoef(xs, ys)[0, 1]) if n > 2 and xs.std() > 0 and ys.std() > 0 else None
        loo = []
        for i in range(n):
            k = np.arange(n) != i
            if xs[k].std() == 0:
                continue
            a, b = np.polyfit(xs[k], ys[k], 1)
            loo.append(abs(a * xs[i] + b - ys[i]))
        acc.append({"metric": metric, "states": n,
                    "pearson_r": round(r_, 3) if r_ is not None else None,
                    "measured_mean": round(float(ys.mean()), 3),
                    "proxy_mean": round(float(xs.mean()), 3),
                    "raw_mae": round(float(np.mean(np.abs(xs - ys))), 3),
                    "calibrated_loo_mae": round(float(np.mean(loo)), 3) if loo else None,
                    "worst_raw_error": round(float(np.max(np.abs(xs - ys))), 3)})
    # Calibrated km estimates for every state, from the 16 sampled ones.
    CAL = {"unpaved_pct": "unpaved_pct", "maxspeed_pct_tertiary": "maxspeed_pct_tertiary",
           "maxspeed_pct_secondary": "maxspeed_pct_secondary",
           "tiger_reviewed_no_pct": "tiger_reviewed_no_pct",
           "surface_tagged_pct": "surface_tagged_pct"}
    fits = {}
    for pk, mk in CAL.items():
        xs = np.array([float(proxy[s_][pk]) for s_ in meas])
        ys = np.array([float(meas[s_][mk]) for s_ in meas])
        fits[pk] = np.polyfit(xs, ys, 1)
    out_rows = []
    for slug, p in proxy.items():
        row = {"state": slug, "sampled": slug in meas, "drivable_ways": p["drivable_ways"]}
        # No class combinations for the main classes (Texas): the class proxies
        # are missing, not 0. Link classes and living_street are empty nearly
        # everywhere, because taginfo only pairs tags above a usage floor.
        blind = len([h for h in p.get("class_combos_empty", "").split(";") if h in MAIN]) >= 5
        for pk, mk in CAL.items():
            a, b = fits[pk]
            est = min(100.0, max(0.0, a * float(p[pk]) + b))
            row[f"{mk}_proxy"] = "" if blind else float(p[pk])
            row[f"{mk}_km_estimate"] = (round(meas[slug][mk], 1) if slug in meas else
                                        "" if blind else round(est, 1))
        row["4wd_only_proxy_pct"] = "" if blind else float(p["4wd_only_pct"])
        row["seasonal_any_highway_ways"] = p["seasonal_any_highway_ways"]
        row["car_conditional_any_highway_ways"] = p["car_conditional_any_highway_ways"]
        row["signals_per_100km_proxy"] = round(100 * int(p["signals_nodes"]) / (
            (int(fhwa[slug]["urban_mi"]) + int(fhwa[slug]["rural_mi"])) * KM_PER_MI), 2)
        out_rows.append(row)
    with open(rdir / "osm_quality_all_states.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    with open(rdir / "proxy_accuracy.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(acc[0]))
        w.writeheader()
        w.writerows(acc)
    for a in acc:
        print(a)


if __name__ == "__main__":
    main()
