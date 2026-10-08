"""Replay the exact slider envelopes from batch60 under other handle->strength
curves, and under a fixed grid of sample positions (option 4: N routes in one
response). No routing: each envelope route owns a known strength interval."""
import json, sys
import numpy as np

rows = [json.loads(l) for l in open(sys.argv[1])]
trips = [r for r in rows if r["status"] == "ok" and not r.get("trivial")
         and r["t_max"] >= 10 and r["full_gain_km"] >= 1.6]

CURVES = {
    "today s=p": lambda p: p,
    "s=p^1.5": lambda p: p ** 1.5,
    "s=p^2": lambda p: p ** 2,
    "s=p^2.5": lambda p: p ** 2.5,
    "s=p^3": lambda p: p ** 3,
    "exp a=4": lambda p: (np.exp(4 * p) - 1) / (np.exp(4) - 1),
    "exp a=6": lambda p: (np.exp(6 * p) - 1) / (np.exp(6) - 1),
}


def route_at(today, s):
    for v in today:
        if v["lo"] - 1e-9 <= s <= v["hi"] + 1e-9:
            return v
    return today[-1]


def score(picked, T, G):
    ex = sorted({v["extra"] for v in picked} | {0.0, T})
    gap = max(np.diff(ex)) / T
    half = max([v["gain_km"] for v in picked if v["extra"] <= T / 2] + [0]) / G
    return gap, half


print("continuous slider (a route is findable if it owns >=2% of the track)")
print(f"{'curve':12} {'gap med':>8} {'gap>=1/2':>9} {'half med':>9} {'mid share':>10}")
for name, f in CURVES.items():
    gaps, halfs, mids, big = [], [], [], 0
    grid = np.linspace(0, 1, 2001)
    for r in trips:
        T, G, today = r["t_max"], r["full_gain_km"], r["today"]
        s = f(grid)
        own = {}
        for p, si in zip(grid, s):
            v = route_at(today, si)
            own.setdefault(id(v), [v, 0])[1] += 1
        share = {k: c / len(grid) for k, (v, c) in own.items()}
        find = [v for k, (v, c) in own.items() if share[k] >= 0.02] + [today[0], today[-1]]
        g, h = score(find, T, G)
        gaps.append(g); halfs.append(h); big += g >= 0.5
        mids.append(sum(share[k] for k, (v, c) in own.items() if 0.25 * T <= v["extra"] <= 0.75 * T))
    print(f"{name:12} {np.median(gaps):8.2f} {big:5d}/{len(trips)} {np.median(halfs):9.2f} {np.median(mids):10.3f}")

print()
print("option 4: N routes at fixed positions, returned together")
print(f"{'curve':12} {'N':>2} {'distinct':>8} {'gap med':>8} {'gap>=1/2':>9} {'half med':>9}")
for name in ["today s=p", "s=p^2", "s=p^2.5", "s=p^3", "exp a=4", "exp a=6"]:
    f = CURVES[name]
    for N in (4, 5, 6, 8):
        pos = np.linspace(1 / N, 1, N)
        gaps, halfs, dis, big = [], [], [], 0
        for r in trips:
            T, G, today = r["t_max"], r["full_gain_km"], r["today"]
            picked = [route_at(today, f(p)) for p in pos] + [today[0]]
            dis.append(len({id(v) for v in picked}))
            g, h = score(picked, T, G)
            gaps.append(g); halfs.append(h); big += g >= 0.5
        print(f"{name:12} {N:2d} {np.median(dis):8.1f} {np.median(gaps):8.2f} {big:5d}/{len(trips)} {np.median(halfs):9.2f}")
print()
print("for reference, spliced menu from the batch: gap med 0.23, 2/44 >= 1/2, half med 0.58")
