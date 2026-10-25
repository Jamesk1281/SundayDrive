"""The tables in docs/low-scenery-fallback.md, from measure.py's output.

    python tools/low_scenery_fallback/analyze.py results/

Reads before.jsonl (code at ea87a2a, menu on: modes menu, plain),
after.jsonl (this change, menu on: menu, plain) and after-busy.jsonl (this
change, menu off: menu, which is then the busy fallback).
"""

import json
import sys
from pathlib import Path

import numpy as np

MIN_KM = 0.805      # options.MENU_FIRST_MIN_KM
BUDGET = 0.25       # options.DEFAULT_MAX_EXTRA_SHARE


def load(path):
    rows = {}
    for line in open(path):
        r = json.loads(line)
        rows[(r["id"], r["mode"])] = r
    return rows


def describe(name, rows):
    ok = [r for r in rows if r["status"] == 200]
    fails = [r for r in rows if r["status"] != 200]
    n = len(ok)
    f_min = np.array([r["fastest"]["minutes"] for r in ok])
    extra = np.array([r["scenic"]["minutes"] for r in ok]) - f_min
    share = extra / f_min
    gain = np.array([r["scenic"]["beautiful_km"] - r["fastest"]["beautiful_km"]
                     for r in ok])
    same = np.array([r["same"] for r in ok])
    no_gain = np.array([bool(r["scenic"].get("no_gain")) for r in ok])
    offered = ~same
    pct = lambda m: f"{m.sum()} ({100 * m.sum() / n:.0f}%)"  # noqa: E731
    q = lambda a: ("-" if not len(a) else  # noqa: E731
                   f"{np.percentile(a, 50):.1f} / {np.percentile(a, 90):.1f} / {a.max():.1f}")
    print(f"\n### {name}: {n} trips answered"
          + (f", {len(fails)} refused ({', '.join(sorted({str(r.get('code')) for r in fails}))})"
             if fails else ""))
    print(f"- scenic arm is the fastest: {pct(same)}; with no_gain: {pct(no_gain)}")
    print(f"- offered, gaining < 0.5 mi: {pct(offered & (gain < MIN_KM))}")
    print(f"- offered, > 10% extra time for < 2 km gained: "
          f"{pct(offered & (share > 0.10) & (gain < 2.0))}")
    print(f"- offered, fewer beautiful km than the fastest: {pct(offered & (gain < 0))}")
    print(f"- offered, > 25% extra time: {pct(offered & (share > BUDGET))}")
    print(f"- extra minutes p50 / p90 / max, all trips: {q(extra)}")
    print(f"- extra minutes p50 / p90 / max, where offered: {q(extra[offered])}")
    print(f"- extra share p50 / p90 / max, where offered: "
          f"{q(100 * share[offered])} %")
    print(f"- beautiful km gained p50 / p90 / max, where offered: {q(gain[offered])}")
    menus = [r for r in ok if "options" in r]
    if menus:
        print(f"- menus: {len(menus)} of {n}")
        d0 = [r for r in menus if r["options"]["default"] == 0]
        over = [r for r in d0 if len(r["options"]["menu"]) > 1
                and max(o["beautiful_km"] for o in r["options"]["menu"])
                - r["options"]["menu"][0]["beautiful_km"] >= MIN_KM]
        print(f"  - default is the fastest: {len(d0)}; of those, over budget with "
              f"an option gaining >= 0.5 mi on the dial: {len(over)}")
        sub = [r for r in menus if r["options"]["default"] > 0 and
               r["options"]["menu"][r["options"]["default"]]["beautiful_km"]
               - r["options"]["menu"][0]["beautiful_km"] < MIN_KM]
        print(f"  - default is an option gaining < 0.5 mi (the menu keeps its "
              f"most scenic frontier point whatever it adds): {len(sub)}")
        df = max(abs(r["options"]["menu"][0]["beautiful_km"] - r["fastest"]["beautiful_km"])
                 for r in menus)
        ds = max(abs(r["options"]["menu"][r["options"]["default"]]["beautiful_km"]
                     - r["scenic"]["beautiful_km"]) for r in menus)
        print(f"  - Trap 4, menu hop-stat km against RouteResult.beautiful_km: "
              f"fastest max |diff| {df:.2f} km, default {ds:.2f} km")
    return ok


def main(d):
    d = Path(d)
    before, after = load(d / "before.jsonl"), load(d / "after.jsonl")
    busy = load(d / "after-busy.jsonl")
    sets = [("before, menu (options=1, alone)", before, "menu"),
            ("before, plain (the busy fallback, and reroutes)", before, "plain"),
            ("after, menu (options=1, alone)", after, "menu"),
            ("after, busy fallback (options=1, menu not run)", busy, "menu"),
            ("after, plain without options (reroutes, older builds)", after, "plain")]
    for name, rows, mode in sets:
        describe(name, [r for (i, m), r in rows.items() if m == mode])
    # Per-trip changes on the plain path: what the fallback now does.
    print("\n### trips the change moved")
    for (i, m), b in before.items():
        if m != "plain" or b["status"] != 200:
            continue
        a = busy.get((i, "menu"))
        p = after.get((i, "plain"))
        am = after.get((i, "menu"))
        bm = before.get((i, "menu"))
        if a is None or a["status"] != 200:
            continue
        moved = a["same"] != b["same"] or (p and p["status"] == 200 and p["same"] != b["same"])
        menu_moved = (am and bm and am["status"] == bm["status"] == 200
                      and (am["scenic"]["minutes"] != bm["scenic"]["minutes"]))
        if moved or menu_moved or i[0] != "r":
            fb, sb = b["fastest"], b["scenic"]
            print(f"- {i}: fastest {fb['minutes']:.0f} min {fb['beautiful_km']} km; "
                  f"before plain {sb['minutes']:.0f} min {sb['beautiful_km']} km; "
                  f"after fallback {'fastest' if a['same'] else str(round(a['scenic']['minutes'])) + ' min ' + str(a['scenic']['beautiful_km']) + ' km'}"
                  f"{' no_gain' if a['scenic'].get('no_gain') else ''}; "
                  f"after plain {'fastest' if p and p.get('same') else (str(round(p['scenic']['minutes'])) + ' min ' + str(p['scenic']['beautiful_km']) + ' km') if p and p['status'] == 200 else '?'}; "
                  f"menu default before/after "
                  f"{bm['options']['default'] if bm and 'options' in bm else '-'}/"
                  f"{am['options']['default'] if am and 'options' in am else '-'}"
                  f"{' no_gain' if am and am.get('scenic', {}).get('no_gain') else ''}")


if __name__ == "__main__":
    main(sys.argv[1])
