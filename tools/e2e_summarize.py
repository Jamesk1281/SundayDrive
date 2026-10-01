"""Summarise an overnight simulated-drive run into the tables the brief asks for.

    python3 tools/e2e_summarize.py <out-dir>        # the SUNDAYDRIVE_E2E_OUT directory

Reads `drives.ndjson` (one line per drive, from `SimulatedDriveTests`) and prints
Markdown: per persona, then per category for the hard failures. Reports drives
*run* — a persona that could not be staged on a route is counted apart as
"unstaged" with its reason, never as a pass.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def fmt(x, nd=1):
    return "—" if x is None else f"{x:.{nd}f}"


def main(argv):
    out = Path(argv[1])
    rows = [json.loads(line) for line in (out / "drives.ndjson").open()]
    by = defaultdict(list)
    for r in rows:
        by[r["persona"]].append(r)
    order = ["perfect", "noisy", "dropout", "stopAndGo", "missedTurn", "wrongWayStart",
             "earlyStop", "loopPerfect", "loopLate", "loopEarly"]
    summaries = {p: json.loads((out / f"summary-{p}.json").read_text())
                 for p in order if (out / f"summary-{p}.json").exists()}

    print("| persona | drives run | unstaged | arrived | driven km | reroutes/km | "
          "same-road adoptions | banner behind (drives) | banner skipped | "
          "dist err p50/p95 m (≤1 km) | prompt lead p5/p50 s | missing prompts | "
          "reroute openings unspoken | street mismatches / checked | hard-fail drives |")
    print("|" + "---|" * 15)
    for p in order:
        rs = by.get(p, [])
        if not rs:
            continue
        ran = [r for r in rs if r["ran"]]
        s = summaries.get(p, {})
        km = sum(r["drivenKm"] for r in ran)
        rr = sum(r["rerouteRequests"] for r in ran)
        leads = [x for r in ran for x in r["finalLeadS"]]
        print(f"| {p} | {len(ran)} | {len(rs) - len(ran)} | {sum(r['arrived'] for r in ran)} | "
              f"{km:,.0f} | {rr / km if km else 0:.3f} | "
              f"{sum(r['suffixAdoptions'] for r in ran)} | "
              f"{sum(r['bannerBehind'] for r in ran)} ({sum(r['bannerBehind'] > 0 for r in ran)}) | "
              f"{sum(r['bannerSkipped'] for r in ran)} | "
              f"{fmt(s.get('distErrP50'))}/{fmt(s.get('distErrP95'))} | "
              f"{fmt(pct(leads, 5))}/{fmt(pct(leads, 50))} | "
              f"{sum(r['missingPrompts'] for r in ran)} of {sum(r['maneuversPassed'] for r in ran)} | "
              f"{sum(r.get('openingsUnspoken', 0) for r in ran)} of {sum(r.get('openingsDriven', 0) for r in ran)} | "
              f"{sum(r['streetMismatch'] for r in ran)} / {sum(r['streetChecked'] for r in ran):,} | "
              f"{sum(bool(r['violations']) for r in ran)} |")

    print("\nTotals:", sum(r["ran"] for r in rows), "drives run,",
          len({r['key'] for r in rows if r['ran']}), "distinct routes,",
          f"{sum(r['drivenKm'] for r in rows if r['ran']):,.0f} km driven.")

    print("\n**Hard failures by kind** (drive count, digits normalised):\n")
    kinds = Counter()
    examples = defaultdict(list)
    for r in rows:
        for v in r["violations"]:
            k = "".join("N" if c.isdigit() else c for c in v)
            while "NN" in k:
                k = k.replace("NN", "N")
            kinds[(r["persona"], k)] += 1
            examples[(r["persona"], k)].append(r["key"])
    for (p, k), n in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"- {p}: {k} — {n} (e.g. {', '.join(examples[(p, k)][:3])})")

    print("\n**Unstaged, by reason** (first clause):\n")
    why = Counter((r["persona"], (r.get("setup") or "").split(":")[0]) for r in rows if not r["ran"])
    for (p, w), n in why.most_common():
        print(f"- {p}: {w} — {n}")

    print("\n**Other UX counters** (all personas):\n")
    for field in ("flicker", "falseOffRoute", "namedWhileOff", "stalls", "bridges",
                  "uTurnJoins", "latePrompts", "passedInGap", "stepBackwards",
                  "remainingRises", "failedReroutes"):
        print(f"- {field}: {sum(r.get(field, 0) for r in rows)} "
              f"({sum(bool(r.get(field, 0)) for r in rows)} drives)")
    lat = [x for r in rows for x in r["rerouteLatencyS"]]
    print(f"- deviation → reroute adopted, s: p50 {fmt(pct(lat, 50))}, p95 {fmt(pct(lat, 95))}, "
          f"n={len(lat)}")
    early = [r for r in rows if r["persona"] == "earlyStop" and r["ran"]]
    after = [r["arrivalAfterParkS"] for r in early if r.get("arrivalAfterParkS") is not None]
    print(f"- earlyStop: arrival after parking 150 m short, s: p50 {fmt(pct(after, 50))}, "
          f"max {fmt(max(after) if after else None)}; {len(early) - len(after)} never arrived while parked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
