"""Project the US routing graph from the states that were counted.

Fits graph nodes ~ a * urban_km + b * rural_km (FHWA HM-20 public road length,
least squares on relative error) over the measured states in
results/graph_counts.jsonl, then predicts the rest and sums by Census division.

Usage: python fit_us.py [results_dir]
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

RES = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results"
KM = 1.609344

meas = {}
for line in open(RES / "graph_counts.jsonl"):
    r = json.loads(line)
    if "error" not in r:
        meas[r["label"]] = r
fhwa = {r["state"].lower().replace(" ", "-"): r
        for r in csv.DictReader(open(RES / "fhwa_hm20_2023_states.csv"))}


def x_of(state):
    s = fhwa[state]
    return np.array([int(s["urban_mi"]) * KM, int(s["rural_mi"]) * KM])


names = sorted(meas)
X = np.array([x_of(k) for k in names])
y = np.array([meas[k]["graph_nodes"] for k in names], dtype=float)
ye = np.array([meas[k]["graph_edges"] for k in names], dtype=float)
coef = np.linalg.lstsq(X / y[:, None], np.ones(len(y)), rcond=None)[0]
coef_e = np.linalg.lstsq(X / ye[:, None], np.ones(len(ye)), rcond=None)[0]
print(f"nodes per urban km {coef[0]:.2f}, per rural km {coef[1]:.2f} (n={len(y)} states)")
loo = []
for i in range(len(y)):
    m = np.arange(len(y)) != i
    c = np.linalg.lstsq(X[m] / y[m, None], np.ones(m.sum()), rcond=None)[0]
    loo.append(X[i] @ c / y[i] - 1)
    print(f"  {names[i]:16s} measured {int(y[i]):>10,}  leave-one-out {100 * loo[-1]:+6.1f}%")
print(f"leave-one-out error: mean |e| {100 * np.mean(np.abs(loo)):.1f}%, worst {100 * np.max(np.abs(loo)):.1f}%")

per = {}
for k in fhwa:
    if k in meas:
        per[k] = (meas[k]["graph_nodes"], meas[k]["graph_edges"], True)
    else:
        per[k] = (float(x_of(k) @ coef), float(x_of(k) @ coef_e), False)
total = sum(v[0] for v in per.values())
print(f"\nUS (50 states + DC): {total / 1e6:.1f} M nodes, {sum(v[1] for v in per.values()) / 1e6:.1f} M edges "
      f"= {total / 794685:.1f} x New England; measured share {sum(v[0] for v in per.values() if v[2]) / total:.1%}")

DIVISIONS = {
    "New England": "connecticut maine massachusetts new-hampshire rhode-island vermont",
    "Middle Atlantic": "new-jersey new-york pennsylvania",
    "East North Central": "illinois indiana michigan ohio wisconsin",
    "West North Central": "iowa kansas minnesota missouri nebraska north-dakota south-dakota",
    "South Atlantic": "delaware district-of-columbia florida georgia maryland north-carolina "
                      "south-carolina virginia west-virginia",
    "East South Central": "alabama kentucky mississippi tennessee",
    "West South Central": "arkansas louisiana oklahoma texas",
    "Mountain": "arizona colorado idaho montana nevada new-mexico utah wyoming",
    "Pacific (CA OR WA)": "california oregon washington",
    "Alaska": "alaska",
    "Hawaii": "hawaii",
}
# Router RSS fitted on the two loads measured (NE 3.68 GB, CO 2.21 GB) and the
# whole-graph Dijkstra measured on linked copies of the NE graph (M2, scipy).
DIJ = (np.log([0.8e6, 3.2e6, 9.6e6, 23.3e6]), np.log([0.38, 3.6, 12.5, 25.0]))
print(f"\n{'division':22s} {'nodes':>7s} {'x NE':>5s} {'RSS today':>9s} {'scenic search':>13s}")
for name, states in DIVISIONS.items():
    n = sum(per[s][0] for s in states.split())
    t = float(np.exp(np.interp(np.log(n), *DIJ))) if n >= 0.8e6 else 0.38 * n / 0.8e6
    print(f"{name:22s} {n / 1e6:6.2f}M {n / 794685:5.1f} {0.73 + 3.71e-6 * n:7.1f} GB {t:11.1f} s")
top = sorted(per.items(), key=lambda kv: -kv[1][0])[:10]
print("\nlargest states:", ", ".join(f"{k} {v[0] / 1e6:.2f}M{'' if v[2] else ' (fit)'}" for k, v in top))
