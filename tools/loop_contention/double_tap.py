"""One person, two loop requests overlapping: does the second come back busy?

    python double_tap.py BASE NODES_PARQUET [n]

For each of n fresh seeded starts: a cold 40 km loop, then after `gap` seconds
the same start at 50 km (the slider released twice). Also times a cold build on
its own, which is the number the wait has to cover (`LOOP_BUSY_WAIT_S`,
docs/loop-lock-contention.md).
"""
import statistics
import sys
import threading
import time

import numpy as np
import pandas as pd
import requests

base, nodes_path = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
nodes = pd.read_parquet(nodes_path, columns=["lat", "lon"])
rng = np.random.default_rng(29)
pick = rng.choice(len(nodes), 3 * n, replace=False)
starts = [f"{nodes.lat.values[i]:.6f},{nodes.lon.values[i]:.6f}" for i in pick]


def post(start, km):
    t0 = time.perf_counter()
    r = requests.post(base + "/api/loop", data={"from": start, "km": km}, timeout=60)
    return r.status_code, time.perf_counter() - t0


cold = [post(s, "40") for s in starts[:n]]
cold_t = [dt for code, dt in cold if code == 200]
print("cold build alone: median %.2f s, p90 %.2f s, n=%d" % (
    statistics.median(cold_t), float(np.percentile(cold_t, 90)), len(cold_t)))

for gap in (0.3, 1.0):
    outcomes = []
    for s in starts[n:2 * n] if gap == 0.3 else starts[2 * n:]:
        box = {}
        first = threading.Thread(target=lambda: box.setdefault("a", post(s, "40")))
        first.start()
        time.sleep(gap)
        second = post(s, "50")
        first.join()
        outcomes.append((box["a"][0], second[0], round(second[1], 2)))
    busy = sum(o[1] == 503 for o in outcomes)
    print(f"gap {gap}s: second busy {busy}/{len(outcomes)}  {outcomes}")
