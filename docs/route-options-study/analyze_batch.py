import json, sys
from collections import defaultdict
import numpy as np

FINDABLE = 0.02          # share of the slider track a route must own
MIN_TMAX = 10.0          # minutes; below this there is no gap worth closing


def menu(spliced, full_gain):
    step = max(1.609, 0.05 * full_gain)
    kept = [spliced[0]]
    for v in spliced[1:]:
        if v["gain_km"] - kept[-1]["gain_km"] >= step:
            kept.append(v)
    if kept[-1] is not spliced[-1]:
        kept.append(spliced[-1])
    return kept


def gap(xs):
    xs = sorted(xs)
    return max(np.diff(xs)) if len(xs) > 1 else 0.0


def best_within(opts, budget):
    return max([o["gain_km"] for o in opts if o["extra"] <= budget + 1e-6] + [0.0])


rows = [json.loads(l) for l in open(sys.argv[1])]
status = defaultdict(int)
for r in rows:
    status[r["status"] if r["status"] != "ok" else ("trivial" if r.get("trivial") or r.get("t_max", 0) < MIN_TMAX else "ok")] += 1
print("status:", dict(status))

by_band = defaultdict(list)
for r in rows:
    if r["status"] != "ok" or r.get("trivial") or r["t_max"] < MIN_TMAX or r["full_gain_km"] < 1.6:
        continue
    T, G = r["t_max"], r["full_gain_km"]
    today = r["today"]
    find = [v for k, v in enumerate(today)
            if k in (0, len(today) - 1) or v["hi"] - v["lo"] >= FINDABLE]
    mid_width = sum(v["hi"] - v["lo"] for v in today if 0.25 * T <= v["extra"] <= 0.75 * T)
    m = menu(r["spliced"], G)
    d = dict(
        pair=r["pair"], T=T, G=G,
        n_today=len(today), n_find=len(find), n_menu=len(m),
        gap_all=gap([v["extra"] for v in today]) / T,
        gap_find=gap([v["extra"] for v in find]) / T,
        gap_menu=gap([v["extra"] for v in m]) / T,
        mid_width=mid_width,
        half_find=best_within(find, T / 2) / G,
        half_all=best_within(today, T / 2) / G,
        half_spl=best_within(r["spliced"], T / 2) / G,
        q_find=best_within(find, T / 4) / G,
        q_spl=best_within(r["spliced"], T / 4) / G,
        s50=min(v["lo"] for v in today if v["extra"] >= 0.5 * T),
        s90=min(v["lo"] for v in today if v["extra"] >= 0.9 * T),
        secs=r["secs"], rejected=r.get("rejected_nonsimple", 0),
    )
    by_band[r["band"]].append(d)
    by_band["ALL"].append(d)

keys = ["T", "G", "n_find", "n_menu", "gap_find", "gap_all", "gap_menu", "mid_width",
        "q_find", "q_spl", "half_find", "half_all", "half_spl", "s50", "s90", "secs"]
print(f"{'band':8}{'n':>3} " + " ".join(f"{k:>9}" for k in keys))
for band in sorted(by_band, key=lambda b: (b == "ALL", float(b.split('-')[0]) if b != "ALL" else 0)):
    ds = by_band[band]
    med = [np.median([d[k] for d in ds]) for k in keys]
    print(f"{band:8}{len(ds):>3} " + " ".join(f"{x:9.2f}" for x in med))

A = by_band["ALL"]
print()
print("trips where today's findable options leave a gap >= half the full detour:",
      sum(d["gap_find"] >= 0.5 for d in A), "/", len(A))
print("  ... same, spliced menu:", sum(d["gap_menu"] >= 0.5 for d in A), "/", len(A))
print("trips with a gap >= a third: today", sum(d["gap_find"] >= 1/3 for d in A),
      " spliced", sum(d["gap_menu"] >= 1/3 for d in A))
print("slider share giving a route in the middle half of the detour (median):",
      round(float(np.median([d["mid_width"] for d in A])), 3))
print("half-budget scenery share, spliced minus today-findable: median",
      round(float(np.median([d["half_spl"] - d["half_find"] for d in A])), 2),
      " spliced worse on", sum(d["half_spl"] < d["half_all"] - 1e-6 for d in A), "trips vs all of today's routes")
worst = sorted(A, key=lambda d: -d["gap_menu"])[:5]
print("largest remaining spliced gaps:", [(d["pair"], round(d["gap_menu"], 2), d["T"]) for d in worst])
