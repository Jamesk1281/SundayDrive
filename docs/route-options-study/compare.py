import json, sys
from collections import defaultdict
import numpy as np

spl = {r["pair"]: r for r in map(json.loads, open(sys.argv[1]))}
ell = {r["pair"]: r for r in map(json.loads, open(sys.argv[2]))}


def frontier(opts):
    opts = sorted(opts, key=lambda o: (o["extra"], -o["gain_km"]))
    out, best = [], -np.inf
    for o in opts:
        if o["gain_km"] > best + 1e-9:
            out.append(o); best = o["gain_km"]
    return out


def menu(front, G):
    step = max(1.609, 0.05 * G)
    kept = [front[0]]
    for v in front[1:]:
        if v["gain_km"] - kept[-1]["gain_km"] >= step:
            kept.append(v)
    if kept[-1] is not front[-1]:
        kept.append(front[-1])
    return kept


def gap(opts, T):
    ex = sorted({o["extra"] for o in opts} | {0.0, T})
    return max(np.diff(ex)) / T


def within(opts, B, G):
    return max([o["gain_km"] for o in opts if o["extra"] <= B + 1e-6] + [0.0]) / G


mism = 0
res = defaultdict(list)
cost = []
over = [0, 0]
for p, e in ell.items():
    s = spl.get(p)
    if e["status"] != "ok" or s is None or s["status"] != "ok" or s.get("trivial"):
        continue
    if s["t_max"] < 10 or s["full_gain_km"] < 1.6:
        continue
    T, G = s["t_max"], s["full_gain_km"]
    if abs(e["t_max"] - T) > 0.2 or abs(e["full_gain_km"] - G) > 0.2:
        mism += 1
    ends = [dict(extra=0.0, gain_km=0.0), dict(extra=T, gain_km=G)]
    sets = {
        "splice": s["spliced"],
        "detour9": [o for o in e["options"] if o["extra"] <= T + 1e-6] + ends,
        "detour4": [o for o in e["options"] if o["frac"] in (0.2, 0.4, 0.6, 0.8)
                    and o["extra"] <= T + 1e-6] + ends,
    }
    sets["union"] = sets["splice"] + sets["detour9"]
    for name, opts in sets.items():
        f = frontier(opts)
        m = menu(f, G)
        res[name].append(dict(pair=p, gap=gap(m, T), half=within(f, T / 2, G),
                              quarter=within(f, T / 4, G), n_menu=len(m)))
    for o in e["options"]:
        over[0] += o["over"]; over[1] += 1
    base = e["t_scenic_search"]
    cost.append(dict(trees=e["t_trees"] / base, opts9=e["t_opts"] / base,
                     n9=e["n_search"],
                     per_opt=e["t_opts"] / max(e["n_search"], 1) / base))

print("trips compared:", len(res["splice"]), " T/G mismatches vs splice batch:", mism)
print(f"{'method':9} {'gap med':>8} {'>=1/2':>6} {'>=1/3':>6} {'quarter':>8} {'half':>6} {'menu n':>7}")
for name, ds in res.items():
    print(f"{name:9} {np.median([d['gap'] for d in ds]):8.2f} "
          f"{sum(d['gap'] >= 0.5 for d in ds):6d} {sum(d['gap'] >= 1/3 for d in ds):6d} "
          f"{np.median([d['quarter'] for d in ds]):8.2f} {np.median([d['half'] for d in ds]):6.2f} "
          f"{np.median([d['n_menu'] for d in ds]):7.1f}")
print("today (from batch60, findable): gap 0.55, 27/44 >= 1/2, 37/44 >= 1/3, quarter 0.02, half 0.15")

S = {d["pair"]: d for d in res["splice"]}
for name in ("detour9", "detour4"):
    d = res[name]
    better = sum(x["half"] > S[x["pair"]]["half"] + 0.02 for x in d)
    worse = sum(x["half"] < S[x["pair"]]["half"] - 0.02 for x in d)
    print(f"{name} vs splice at half budget: better on {better}, worse on {worse}, of {len(d)}")
print(f"options over budget by >10% after retries: {over[0]}/{over[1]}")
c = cost
print("cost in units of one full scenic search (median):",
      f"two fastest trees {np.median([x['trees'] for x in c]):.2f},",
      f"one budgeted search {np.median([x['per_opt'] for x in c]):.2f},",
      f"all 9 budgets incl. retries {np.median([x['opts9'] for x in c]):.2f} ({np.median([x['n9'] for x in c]):.0f} searches)")
