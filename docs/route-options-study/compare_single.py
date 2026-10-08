import json, sys
import numpy as np
sys.argv = [sys.argv[0]]
_src = open('compare.py').read(); exec(_src[_src.index('def frontier'):_src.index('mism = 0')])   # frontier, menu, gap, within
spl = {r["pair"]: r for r in map(json.loads, open('batch60/results.jsonl'))}
one = {r["pair"]: r for r in map(json.loads, open('single60/results.jsonl'))}
res = {k: [] for k in ("8 bases", "full", "full+quarter")}
mism, cost = 0, []
for p, s in spl.items():
    if s["status"] != "ok" or s.get("trivial") or s["t_max"] < 10 or s["full_gain_km"] < 1.6:
        continue
    o = one[p]; T, G = s["t_max"], s["full_gain_km"]
    mism += abs(o["t_max"] - T) > 0.2 or abs(o["full_gain_km"] - G) > 0.2
    sets = {"8 bases": s["spliced"], **{k: v["spliced"] for k, v in o["configs"].items()}}
    for k, opts in sets.items():
        f = frontier(opts); m = menu(f, G)
        res[k].append(dict(pair=p, gap=gap(m, T), half=within(f, T/2, G), quarter=within(f, T/4, G), n=len(m)))
    b = o["t_scenic_search"]
    cost.append(dict(trees=o["t_trees"]/b, full=o["configs"]["full"]["t_splice"]/b,
                     fq=o["configs"]["full+quarter"]["t_splice"]/b, abs_s=b,
                     abs_trees=o["t_trees"], abs_full=o["configs"]["full"]["t_splice"]))
print("trips:", len(res["full"]), " T/G mismatches vs batch60:", mism)
print(f"{'bases':13} {'gap med':>8} {'>=1/2':>6} {'>=1/3':>6} {'quarter':>8} {'half':>6} {'menu n':>7}")
for k, ds in res.items():
    print(f"{k:13} {np.median([d['gap'] for d in ds]):8.2f} {sum(d['gap']>=.5 for d in ds):6d} "
          f"{sum(d['gap']>=1/3 for d in ds):6d} {np.median([d['quarter'] for d in ds]):8.2f} "
          f"{np.median([d['half'] for d in ds]):6.2f} {np.median([d['n'] for d in ds]):7.1f}")
print("today: gap 0.55, 27 >= 1/2, 37 >= 1/3, quarter 0.02, half 0.15")
E = {d["pair"]: d for d in res["8 bases"]}
for k in ("full", "full+quarter"):
    d = res[k]
    print(f"{k} vs 8 bases at half budget: worse by >0.05 on {sum(x['half'] < E[x['pair']]['half'] - .05 for x in d)},"
          f" by >0.15 on {sum(x['half'] < E[x['pair']]['half'] - .15 for x in d)}; gap worse by >0.1 on {sum(x['gap'] > E[x['pair']]['gap'] + .1 for x in d)}")
med = lambda k: np.median([c[k] for c in cost])
p90 = lambda k: np.percentile([c[k] for c in cost], 90)
print(f"cost vs one scenic search (median / p90): two fastest trees {med('trees'):.2f}/{p90('trees'):.2f}, "
      f"splice full {med('full'):.2f}/{p90('full'):.2f}, splice full+quarter {med('fq'):.2f}/{p90('fq'):.2f}")
print(f"absolute (s, median, busy machine, nice 19): scenic search {med('abs_s'):.3f}, trees {med('abs_trees'):.3f}, splice full {med('abs_full'):.3f}")
