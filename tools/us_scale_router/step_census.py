"""Count the instruction defects in random national trips, for one checkout.

The census behind docs/review-fixes-router.md, "Instruction text": what share
of steps read a raw multi-value ("Continue onto I 295;US 1;ME 26"), take an
exit with no number, no destination and no direction ("Take the exit onto
I 64"), or name no road ("Merge", "Continue", "Keep left").

    SUNDAYDRIVE_PACK=data/pack-us python step_census.py data/processed-us \
        --root <checkout> [--trips 40] [--out steps.json]

`--root` is a directory holding `pipeline/`, so the same trips can be asked of
two checkouts. Trips are random graph nodes 20 to 400 km apart, seeded.
"""

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

SEED = 20261020
SUMMER = date(2026, 7, 1)
BARE = re.compile(r"^(Merge|Continue|Keep (left|right)|Turn (left|right)|"
                  r"Slight (left|right)|Sharp (left|right)|Make a U-turn)$")
EXIT_ONTO = re.compile(r"^Take the exit onto (.+)$")
DIRECTED = re.compile(r" (North|South|East|West)$")


def classify(step):
    text = step["instruction"]
    out = []
    if ";" in text:
        out.append("multi-value")
    m = EXIT_ONTO.match(text)
    if m and not DIRECTED.search(m.group(1)):
        out.append("exit without direction")
    if step["type"] == "exit" and text in ("Take the exit", "Take the exit on the left",
                                          "Take the exit on the right"):
        out.append("exit with nothing")
    if BARE.match(text):
        out.append("no road name")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("processed")
    p.add_argument("--root", required=True)
    p.add_argument("--trips", type=int, default=40)
    p.add_argument("--out")
    args = p.parse_args()
    sys.path.insert(0, str(Path(args.root).resolve() / "pipeline"))
    from router import Router
    router = Router(args.processed, pack=os.environ.get("SUNDAYDRIVE_PACK"))
    rng = np.random.default_rng(SEED)
    lat, lon = np.asarray(router.node_lat), np.asarray(router.node_lon)
    counts, total, examples, trips = Counter(), 0, {}, 0
    t = time.perf_counter()
    while trips < args.trips:
        i, j = (int(x) for x in rng.integers(0, len(lat), 2))
        d = 6371.0088 * 2 * math.asin(math.sqrt(
            math.sin(math.radians(lat[j] - lat[i]) / 2) ** 2
            + math.cos(math.radians(lat[i])) * math.cos(math.radians(lat[j]))
            * math.sin(math.radians(lon[j] - lon[i]) / 2) ** 2))
        if not 20.0 <= d <= 400.0:
            continue
        s, _ = router.snap(float(lat[i]), float(lon[i]))
        e, _ = router.snap_destination(float(lat[j]), float(lon[j]))
        if s == e:
            continue
        trips += 1
        for pref in (0.0, 0.5):
            route = router.route(s, e, pref, on=SUMMER)
            if route is None:
                continue
            for step in route.steps():
                total += 1
                for c in classify(step):
                    counts[c] += 1
                    examples.setdefault(c, []).append(step["instruction"])
        print(f"trip {trips}: {d:.0f} km, {total} steps so far", flush=True)
    print(f"{trips} trips, {total} steps, {time.perf_counter() - t:.0f} s")
    for c in ("multi-value", "exit without direction", "exit with nothing",
              "no road name"):
        print(f"  {c:24s} {counts[c]:5d}  {100.0 * counts[c] / max(total, 1):4.1f}%"
              f"  e.g. {examples.get(c, [''])[:3]}")
    if args.out:
        Path(args.out).write_text(json.dumps({"steps": total, "counts": counts,
                                              "examples": {k: v[:20] for k, v
                                                           in examples.items()}}))


if __name__ == "__main__":
    main()
