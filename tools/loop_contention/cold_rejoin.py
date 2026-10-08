"""Cold against warm rejoin, and what a rejoin planner's cost models weigh.

    SUNDAYDRIVE_DATA=<main>/data/processed-ne python cold_rejoin.py <checkout>

In-process, so HTTP and waitress are out of it. Each replicate gets a fresh
planner, so "cold" builds both cost models (pref 0 and pref 1) the way the
first rejoin after a restart, or after a new weight set, does.
"""
import statistics
import sys
import time
from datetime import date

import numpy as np

sys.path.insert(0, sys.argv[1] + "/server")
sys.path.insert(0, sys.argv[1] + "/pipeline")
import app  # noqa: E402
from looper import LoopPlanner  # noqa: E402

R = app.ROUTER
day = date(2027, 7, 15)
s, _ = R.snap(42.2900, -71.2200)
w, _ = R.snap(42.2457, -71.2828)
t, _ = R.snap(42.2810, -71.2370)


def rejoin(p):
    a = p.resume(s, w, t, 0.0, {}, 1.0, on=day)
    b = p.resume(s, w, t, 1.0, {}, 1.0, on=day)
    assert a is not None and b is not None


cold, warm = [], []
for _ in range(5):
    p = LoopPlanner(R)
    t0 = time.perf_counter(); rejoin(p); cold.append(time.perf_counter() - t0)
    t0 = time.perf_counter(); rejoin(p); warm.append(time.perf_counter() - t0)

# Size of one cost model, from the arrays it holds.
from looper import _weights_key  # noqa: E402
p = LoopPlanner(R)
model = p._cost(1.0, _weights_key({}), 1.0, day)
nbytes = sum(v.nbytes for v in vars(model).values() if isinstance(v, np.ndarray))
print(f"cold rejoin median {statistics.median(cold):.3f}s  {[round(x,3) for x in cold]}")
print(f"warm rejoin median {statistics.median(warm):.3f}s  {[round(x,3) for x in warm]}")
print(f"cold/warm {statistics.median(cold)/statistics.median(warm):.2f}")
print(f"one cost model {nbytes/1e6:.1f} MB; a rejoin planner holds two: {2*nbytes/1e6:.1f} MB")
