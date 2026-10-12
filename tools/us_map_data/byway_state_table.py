"""Byway census per state: what extract.py's rule admits and what it misses.

From byway_census.py's two files: the scenic-system networks (relation counts
from taginfo) and every US scenic=yes road relation (Overpass). For each state:

  networks            the scenic-system networks filed under its US:XX prefix
  relations           relations in them
  admitted_by_network those in extract.py's BYWAY_NETWORKS
  admitted_by_tag     scenic=yes relations in the state, any network or none
  missed              relations in a scenic network that neither clause admits
  numbered_flagged    scenic=yes on a numbered-highway relation (US:US, US:I,
                      US:XX), which makes the whole highway a byway

And for the sampled states, the drivable km osm_metrics.py measured for the
relations in scenic or byway networks and the share extract.py admits.

Usage: python -I byway_state_table.py <byway_networks.csv> <byway_scenic_yes.csv>
                                      <metrics_dir> <out.csv> <out_sampled.csv>
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ALLOW = {"US:MA:Scenic", "US:VT:byway", "US:AB:NSB:Connecticut River", "US:NY:Scenic",
         "CA:NB:scenic"}
STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL",
          "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE",
          "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
          "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]
# Networks that are road classes or historic trails rather than scenic
# designations, though their names match: kept out of "missed".
NOT_SCENIC = ("Parkway", "auto_trail", "Auto Trail", "Auto:Trail", "Detour", "heritage_trail",
              "WashingtonTrail", "THC")


def main():
    nets = list(csv.DictReader(open(sys.argv[1])))
    sy = list(csv.DictReader(open(sys.argv[2])))
    by = defaultdict(lambda: {"networks": [], "relations": 0, "admitted_by_network": 0,
                              "admitted_by_tag": 0, "missed": 0, "numbered_flagged": []})
    sy_by_net = defaultdict(int)
    for r in sy:
        sy_by_net[r["network"]] += 1
        if r["state"] in STATES:
            by[r["state"]]["admitted_by_tag"] += 1
            if r["numbered_highway"] == "True":
                by[r["state"]]["numbered_flagged"].append(f"{r['network']} {r['ref'] or r['name']}")
    national = []
    for n in nets:
        st, rel, net = n["state"], int(n["relations"]), n["network"]
        if any(x in net for x in NOT_SCENIC):
            continue
        if st not in STATES:
            national.append(f"{net} ({rel})")
            continue
        b = by[st]
        b["networks"].append(f"{net} ({rel})")
        b["relations"] += rel
        if net in ALLOW:
            b["admitted_by_network"] += rel
        else:
            b["missed"] += max(0, rel - sy_by_net.get(net, 0))
    with open(sys.argv[4], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state", "networks", "relations", "admitted_by_network", "admitted_by_tag",
                    "missed", "numbered_flagged"])
        for st in STATES:
            b = by[st]
            w.writerow([st, "; ".join(b["networks"]), b["relations"], b["admitted_by_network"],
                        b["admitted_by_tag"], b["missed"], "; ".join(b["numbered_flagged"])])
        w.writerow(["(no state)", "; ".join(national), "", "", "", "", ""])
    tot = {k: sum(by[s][k] for s in STATES) for k in
           ("relations", "admitted_by_network", "admitted_by_tag", "missed")}
    print("totals", tot, "states with a scenic network:",
          sum(1 for s in STATES if by[s]["relations"]))
    rows = []
    for p in sorted(Path(sys.argv[3]).glob("*.json")):
        d = json.load(open(p))
        b = d["byways"]
        km = sum(v["km"] for v in b["networks"].values())
        adm = sum(v["admitted_km"] for v in b["networks"].values())
        rows.append({"state": d["label"], "relations_named_or_tagged": len(b["relations"]),
                     "drivable_km": round(km, 1), "admitted_km": round(adm, 1),
                     "admitted_share": round(adm / km, 3) if km else "",
                     "networks": "; ".join(f"{k} ({v['relations']})"
                                           for k, v in sorted(b["networks"].items()))})
    with open(sys.argv[5], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r["state"], r["relations_named_or_tagged"], r["drivable_km"], r["admitted_km"],
              r["admitted_share"])


if __name__ == "__main__":
    main()
