"""Score endpoint_batch.py's results the way compare_single.py scored the study.

Usage: endpoint_analyze.py <results.jsonl>

Quality, over trips with a detour of at least 10 min and a gain of at least
1.6 km (1 mile), as in the study:
  gap     largest gap in extra time over the *menu* (with 0 and the full
          detour added), as a share of the full detour
  quarter, half
          the share of the full gain bought with a quarter / half of the full
          extra time, over the *frontier* the menu was thinned from
The full detour and gain are those of S, the route at pref 1, exactly as the
study took them (`base`). A spliced route can beat S on both counts, so the
frontier's own last point is the wrong denominator: on 19 of the 44 trips it
is shorter, and the same menu then scores as a bigger share.

Capacity: per band, medians of each request's time over one plain pref-1
search timed in the same loop, so that load from other work on the machine
cancels; and the ratio of a plan with options to today's plan.
"""
import json, sys
from collections import defaultdict
import numpy as np

rows = [json.loads(l) for l in open(sys.argv[1])]
status = defaultdict(int)
for r in rows:
    status[r["status"]] += 1
print("status:", dict(status))

ok = [r for r in rows if r["status"] == "ok"]
q = []
for r in ok:
    front = r["frontier"]
    if not front or not r.get("base"):
        continue
    T, G = r["base"]
    if T < 10 or G < 1.6:
        continue
    menu = r["menu"]
    ex = sorted({m[0] for m in menu} | {0.0, T})
    gap = max(np.diff(ex)) / T

    def within(B):
        return max([g for x, g in front if x <= B + 1e-6] + [0.0]) / G

    q.append(dict(pair=r["pair"], band=r["band"], T=T, G=G, gap=gap, n=len(menu),
                  quarter=within(T / 4), half=within(T / 2),
                  default_share=menu[r["default"]][0] / r["fastest_min"]))
print(f"\nquality over {len(q)} trips (study: 44)")
print(f"{'':10} {'gap med':>8} {'>=1/2':>6} {'>=1/3':>6} {'quarter':>8} {'half':>6} {'menu n':>7}")
print(f"{'endpoint':10} {np.median([d['gap'] for d in q]):8.2f} "
      f"{sum(d['gap'] >= .5 for d in q):6d} {sum(d['gap'] >= 1/3 for d in q):6d} "
      f"{np.median([d['quarter'] for d in q]):8.2f} {np.median([d['half'] for d in q]):6.2f} "
      f"{np.median([d['n'] for d in q]):7.1f}")
print(f"{'study':10} {0.25:8.2f} {3:6d} {10:6d} {0.28:8.2f} {0.55:6.2f}")
print(f"{'today':10} {0.55:8.2f} {27:6d} {37:6d} {0.02:8.2f} {0.15:6.2f}")
print("default option's extra time as a share of the fastest (max):",
      round(max(d["default_share"] for d in q), 3))

mism = [(r["pair"], r["rebuild_mismatch"]) for r in ok if r["rebuild_mismatch"]]
n_opts = sum(len(r["menu"]) - 1 for r in ok)
print(f"\nrebuilt from switch points: {n_opts} options on {len(ok)} trips, "
      f"mismatched or repeating a junction: {sum(len(m) for _, m in mism)} {mism}")

print("\ncapacity: medians, in units of one plain pref-1 search timed in the same loop")
print(f"{'band':8} {'n':>3} {'search s':>9} {'today':>6} {'options':>8} {'opt/today':>10} "
      f"{'p90':>5} {'detail':>7} {'KB today':>9} {'KB opts':>8}")
bands = defaultdict(list)
for r in ok:
    bands[r["band"]].append(r)
    bands["all"].append(r)
for band in ["10-25", "25-50", "50-100", "100-200", "200-350", "all"]:
    rs = bands[band]
    if not rs:
        continue
    s = np.array([r["t_scenic"] for r in rs])
    today = np.array([r["t_today"] for r in rs]) / s
    opts = np.array([r["t_options"] for r in rs]) / s
    ratio = np.array([r["t_options"] / r["t_today"] for r in rs])
    det = [r["t_detail"] / r["t_scenic"] for r in rs if "t_detail" in r]
    print(f"{band:8} {len(rs):3d} {np.median(s):9.3f} {np.median(today):6.2f} "
          f"{np.median(opts):8.2f} {np.median(ratio):10.2f} {np.percentile(ratio, 90):5.2f} "
          f"{(np.median(det) if det else float('nan')):7.2f} "
          f"{np.median([r['bytes_today'] for r in rs]) / 1000:9.1f} "
          f"{np.median([r['bytes_options'] for r in rs]) / 1000:8.1f}")

ph = defaultdict(list)
for r in ok:
    for k, v in r["phases"].items():
        ph[k].append(v / r["t_scenic"])
print("\nplanner phases, median in search units:",
      {k: round(float(np.median(v)), 2) for k, v in ph.items()})
