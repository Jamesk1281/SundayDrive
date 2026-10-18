"""Compare a replay (parity_run.py --replay) with the oracle's answers.

    python parity_diff.py oracle.json new.json [--show 20]

Each request is classed by the first thing that differs:

  same        the whole JSON answer is identical
  wording     same status and same routes, only an error message reworded
  capped      the oracle answered a trip over the cap and the new server
              refused it with TRIP_TOO_LONG, as it must
  numbers     the same lines drawn, some reported number differs
  route       a different line drawn for some route, option or loop
  status      a different HTTP status, otherwise

and the snaps are compared node for node. Latency is reported beside it, by
request kind, for the same requests on the same machine.
"""

import argparse
import json
from collections import Counter, defaultdict

import numpy as np


def kind(r):
    p = r["params"]
    if r["path"] == "/api/loop":
        return "loop" + (" sector" if "sector" in p else "")
    if "via" in p:
        return "loop rejoin"
    if "options" in p:
        return "options plan"
    if "leave" in p or "rejoin" in p:
        return "option reroute" if "heading" in p else "option fetch"
    if "declined_uturn" in p:
        return "declined U-turn"
    if "heading" in p:
        return "reroute"
    return f"route pref {p.get('pref')}"


def lines(body):
    """Every drawn line in an answer, by where it sits."""
    out = {}
    if not isinstance(body, dict):
        return out
    for key in ("fastest", "scenic", "loop"):
        f = body.get(key)
        if isinstance(f, dict) and f.get("geometry"):
            out[key] = f["geometry"]["coordinates"]
    for i, o in enumerate(((body.get("options") or {}).get("menu")) or []):
        out[f"option {i}"] = o.get("line")
    return out


def classify(a, b):
    if a == b:
        return "same", ""
    sa, sb = a["status"], b["status"]
    ba, bb = a["body"] or {}, b["body"] or {}
    if sb == 400 and bb.get("code") == "TRIP_TOO_LONG":
        return "capped", f"{bb.get('km')} km"
    if sa != sb:
        return "status", f"{sa} -> {sb}: {bb.get('error') or ''}"
    if "error" in ba and "error" in bb and set(ba) == set(bb) - {"code"}:
        return "wording", f"{ba['error']!r} -> {bb['error']!r}"
    la, lb = lines(ba), lines(bb)
    if la != lb:
        where = sorted(k for k in set(la) | set(lb) if la.get(k) != lb.get(k))
        return "route", ", ".join(where)
    return "numbers", first_difference(ba, bb)


def first_difference(a, b, path=""):
    if type(a) != type(b):
        return f"{path}: {a!r} -> {b!r}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                return first_difference(a.get(k), b.get(k), f"{path}.{k}")
        return ""
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: {len(a)} items -> {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return first_difference(x, y, f"{path}[{i}]")
        return ""
    return f"{path}: {a!r} -> {b!r}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("oracle")
    p.add_argument("new")
    p.add_argument("--show", type=int, default=30)
    args = p.parse_args()
    old = json.load(open(args.oracle))
    new = json.load(open(args.new))
    assert len(old["requests"]) == len(new["requests"])
    counts = Counter()
    by_kind = defaultdict(Counter)
    times = defaultdict(lambda: ([], []))
    shown = []
    for n, (ra, rb) in enumerate(zip(old["requests"], new["requests"])):
        assert ra["params"] == rb["params"]
        cls, detail = classify(ra["answer"], rb["answer"])
        k = kind(ra)
        counts[cls] += 1
        by_kind[k][cls] += 1
        if cls not in ("capped",):
            # CPU seconds where both runs kept them, wall seconds otherwise.
            key = "cpu" if "cpu" in ra["answer"] and "cpu" in rb["answer"] else "seconds"
            times[k][0].append(ra["answer"][key])
            times[k][1].append(rb["answer"][key])
        if cls not in ("same", "capped", "wording"):
            shown.append((n, k, cls, detail, ra["params"]))
    print(f"{len(old['requests'])} requests: " +
          ", ".join(f"{c} {v}" for c, v in counts.most_common()))
    print()
    print(f"{'kind':18s} {'classes':44s} {'oracle p50/p90 s':>17s} {'new p50/p90 s':>15s}")
    for k in sorted(by_kind):
        ta, tb = (np.array(t) for t in times[k])
        cl = ", ".join(f"{c} {v}" for c, v in by_kind[k].most_common())
        if len(ta):
            print(f"{k:18s} {cl:44s} {np.median(ta):7.3f}/{np.percentile(ta, 90):6.3f}"
                  f"   {np.median(tb):6.3f}/{np.percentile(tb, 90):6.3f}")
        else:
            print(f"{k:18s} {cl:44s}")
    print()
    for n, k, cls, detail, params in shown[:args.show]:
        print(f"#{n} {k}: {cls}: {detail[:160]}")
    sa, sb = old["snaps"], new["snaps"]
    diff = [i for i, (x, y) in enumerate(zip(sa, sb)) if x != y]
    print(f"\nsnaps: {len(sa) - len(diff)} of {len(sa)} identical")
    for i in diff[:10]:
        print(f"  snap {i}: {sa[i]} -> {sb[i]}")
    print(f"\nload {old['load_s']:.1f} s -> {new['load_s']:.1f} s; "
          f"all requests {old['serve_s']:.0f} s -> {new['serve_s']:.0f} s")


if __name__ == "__main__":
    main()
