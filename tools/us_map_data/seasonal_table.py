"""The seasonal ground-truth table: official closures beside how OSM tags them.

Joins seasonal_truth.json (each road's official closure, its source and the
verdict reached by reading both) to seasonal_check.py's per-state output, and
adds what closures.py does: the km it closes, the windows, and every closure-
type tag on the road it does not read. Closure-type means the car keys'
`*:conditional`, `seasonal`, `winter_service` and free-text `note` or
`description`; `maxspeed:conditional` and the like are not closures.

Usage: python -I seasonal_table.py <seasonal_truth.json> <seasonal_dir> <out.csv>
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

CAR = ("access", "vehicle", "motor_vehicle", "motorcar")


def main():
    truth = {t["id"]: t for t in json.load(open(sys.argv[1]))}
    found = {}
    for p in sorted(Path(sys.argv[2]).glob("*.json")):
        for r in json.load(open(p)):
            # A later Overpass re-check (e.g. a renamed road) replaces a PBF miss.
            if r["id"] not in found or r["km_in_graph"] > found[r["id"]]["km_in_graph"]:
                found[r["id"]] = r
    rows = []
    for rid, t in truth.items():
        r = found.get(rid)
        tags, windows = Counter(), Counter()
        if r:
            for w in r["ways"]:
                if w["status"] != "in graph":
                    continue
                for k, v in w["tags"].items():
                    if (k in [f"{c}:conditional" for c in CAR] or k in ("seasonal", "winter_service")
                            or k in ("note", "description") and "winter" in v.lower()
                            or k in ("note", "description") and "season" in v.lower()):
                        tags[f"{k}={v}"] += w["km"]
                for win in w["closures_py_windows"]:
                    windows["{}/{}-{}/{}".format(*win)] += w["km"]
        rows.append({
            "road": r["road"] if r else rid, "state": r["state"] if r else "",
            "official_closure": t["official"], "source": t["source"],
            "km_in_graph": r["km_in_graph"] if r else "",
            "km_closures_py_closes": r["km_closures_py_closes"] if r else "",
            "closures_py_windows": "; ".join(f"{w} ({km:.1f} km)" for w, km in windows.most_common()),
            "closure_tags_on_graph_ways": "; ".join(f"{k} ({km:.1f} km)"
                                                     for k, km in tags.most_common(4)),
            "timed_gates": len(r["timed_barriers"]) if r else "",
            "verdict": t["verdict"], "note": t["note"],
        })
    with open(sys.argv[3], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['road'][:44]:44s} {r['verdict']:24s} graph {r['km_in_graph']} "
              f"closed {r['km_closures_py_closes']}")


if __name__ == "__main__":
    main()
