"""Q4: the policies on Q1-Q3's numbers, and the frontier.

Offline arithmetic over the measured CSVs; no router. For every sample trip
and every day of a year (trips spread evenly over the year):

  uses(i, d, X)   trip i's all-open scenic route is driven on day d under
                  policy X if every seasonal edge on it is open under X that
                  day; otherwise the trip takes its ban route (Q1's P1 run).
                  An approximation, checked against the P0 runs on Jun 15,
                  Aug 15 and Oct 15 (`validate`).
  p(i, d)         the chance the road is actually shut that day though we
                  say open: per edge, the empirical share of Q2 road-seasons
                  whose miss exceeds the day's distance from our P0 window
                  end, for the source that sets that end; the max over the
                  trip's edges.
  D(i)            the detour minutes when it is (Q3, per trip, the road
                  closed for the reroute), plus under P0 the minutes the
                  app spends pointing the driver back (Q3's replay), which
                  P5 removes.

  stranded(X)  = 1000 * mean over trips and days of uses * p * D
  scenery(X)   = beautiful km driven on seasonal edges under X / under P0

  python q4_policies.py  ->  q4_frontier.csv, q4_validation.csv
"""

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import windows as W   # noqa: E402

DATA = Path("/Users/james./Desktop/myapps/SundayDrive/data/processed-us")
DAYS = W.DAYS
# The miss curves are indexed by a signed distance from our P0 window's end,
# k = -HALF..HALF: negative is a day the P0 window keeps shut, which only a
# narrowed window opens.
HALF = DAYS // 2


def idx(k):
    """A signed day distance -HALF..HALF as an index into a miss curve."""
    return np.clip(np.asarray(k), -HALF, DAYS - HALF - 1) + HALF


def day_risk(o, c, so_curve, sc_curve):
    """p[d] for one edge whose P0 window opens on `o` and closes on `c`.

    An open-season day is k days after opening and j before closing, both
    from 0, and is at risk from either end. A day the P0 window keeps shut,
    which only a narrowed window opens, is measured from the nearer end, as
    a negative distance: the road is still shut with P(miss > -k)."""
    d = np.arange(DAYS)
    L = (c - o) % DAYS
    t = (d - o) % DAYS
    p = np.empty(DAYS)
    inside = t < L
    p[inside] = np.maximum(so_curve[idx(t[inside])], sc_curve[idx(L - 1 - t[inside])])
    back = DAYS - t[~inside]                 # days before opening
    fwd = t[~inside] - L + 1                  # days after the last open day
    p[~inside] = np.where(back <= fwd, so_curve[idx(-back)], sc_curve[idx(-fwd)])
    return p


# ------------------------------------------------------------- the risk model
def miss_curves(proxy_default="standalone"):
    # A source needs at least ten published road-seasons from three roads at
    # each end to stand on its own; with fewer it takes the pooled curve and
    # is labelled a proxy (the brief's escape hatch).
    """{source: (S_open, S_close)}, each S[k] = P(miss > k) for k = 0..364,
    from Q2's effective misses by the source that sets each end. The table's
    in-sample seasons are dropped: its windows cannot miss on them."""
    d = pd.read_csv(HERE / "q2_misses.csv")
    import q2_windows as Q2
    b = Q2.binding(d).set_index("road")
    eff = d[d.window_source == "effective"]
    own = d[d.window_source != "effective"]
    curves, counts = {}, {}

    def surv(x):
        x = np.asarray(x, float)
        x = x[~np.isnan(x)]
        k = np.arange(-HALF, DAYS - HALF)
        return (x[None, :] > k[:, None]).mean(axis=1) if len(x) else np.zeros(DAYS)

    pooled = {}
    for end, col in (("open", "open_bound_by"), ("close", "close_bound_by")):
        x = eff.assign(src=eff.road.map(b[col]).fillna(""))
        # The table's own in-sample seasons cannot test it: dropped where the
        # table sets this end.
        x = x[~(x.in_sample.astype(bool) & x.src.str.contains("table"))]
        pooled[end] = x[f"{end}_miss"].to_numpy()
        for src in W.SOURCES:
            g = x[x.src.str.split("+").apply(lambda s: src in s)].dropna(subset=[f"{end}_miss"])
            counts[(src, end)] = (len(g), g.road.nunique())
            curves.setdefault(src, {})[end] = g[f"{end}_miss"].to_numpy()
            curves[src][end + "_roads"] = g.road.nunique()
    out, how = {}, {}
    for src in W.SOURCES:
        o, c = curves[src]["open"], curves[src]["close"]
        label = "Q2, binding"
        if src == "osm_default" and proxy_default == "standalone":
            # WINTER sets few published ends; its own window on the roads
            # that carry it is the evidence (high passes: a worst case).
            o = own[own.window_source == src]["open_miss"].to_numpy()
            c = own[own.window_source == src]["close_miss"].to_numpy()
            label = "Q2, its own window on high passes (proxy)"
        elif min(len(o), len(c)) < 10 or min(curves[src]["open_roads"], curves[src]["close_roads"]) < 3:
            o, c = pooled["open"], pooled["close"]
            label = "pooled proxy (too few published dates)"
        out[src] = (surv(o), surv(c))
        how[src] = label
    return out, how, counts


def edge_ends(table: pd.DataFrame):
    """{edge: (first open day, first closed day, open source, close source)}
    under P0, the longest closed run taken as the edge's winter."""
    out = {}
    for e, g in table.groupby("edge"):
        masks = [(W.window_mask(w), s) for w, s in zip(g[W.COLS].to_numpy(), g["source"])]
        m = np.logical_or.reduce([x for x, _ in masks])
        if m.all() or not m.any():
            continue
        # Rotate so the array starts on an open day, then find the closed runs.
        start = int(np.flatnonzero(~m)[0])
        r = np.roll(m, -start)
        idx = np.flatnonzero(r)
        runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
        run = max(runs, key=len)
        c, o = (run[0] + start) % DAYS, (run[-1] + 1 + start) % DAYS
        osrc = [s for x, s in masks if x[(o - 1) % DAYS] and not x[o]] or [masks[0][1]]
        csrc = [s for x, s in masks if x[c] and not x[(c - 1) % DAYS]] or [masks[0][1]]
        out[int(e)] = (o, c, osrc[0], csrc[0])
    return out


def edge_risk(ends, curves):
    """{edge: p[d]}: the chance it is shut on day d though P0 says open."""
    return {e: day_risk(o, c, curves[so][0], curves[sc][1]) for e, (o, c, so, sc) in ends.items()}


def attribution(trips, masks, ends, curves, p5=False):
    """P0's stranded minutes split by the window source, and the end, that
    set the risk on each trip-day: the edge and end with the highest p."""
    d = np.arange(DAYS)
    out = {}
    for t in trips:
        E = [e for e in t["edges"] if e in ends]
        if not E:
            continue
        open_ = np.logical_and.reduce([~masks.get(e, np.zeros(DAYS, bool)) for e in E])
        # Each end's own share, to say which one set the day's risk.
        zero = np.zeros(DAYS)
        po = np.array([day_risk(ends[e][0], ends[e][1], curves[ends[e][2]][0], zero) for e in E])
        pc = np.array([day_risk(ends[e][0], ends[e][1], zero, curves[ends[e][3]][1]) for e in E])
        both = np.concatenate([po, pc])
        k = both.argmax(axis=0)
        p = both.max(axis=0)
        D = t["detour"] + (0.0 if p5 else t["p0_extra"])
        for day in np.flatnonzero(open_ & (p > 0)):
            i = k[day]
            e = E[i % len(E)]
            key = (ends[e][2], "spring") if i < len(E) else (ends[e][3], "autumn")
            out[key] = out.get(key, 0.0) + p[day] * D
    return out


# ------------------------------------------------------------------ policies
def policy_masks(table, margins=None, ban=False):
    if ban:
        return {int(e): np.ones(DAYS, bool) for e in table["edge"].unique()}
    return W.edge_masks(table, margins or {})


def evaluate(trips, masks, risk, extra_p0, p5, price=None, notice_days=None, p0_masks=None):
    """Totals for one policy over all trip-days."""
    strand = scen = scen_p0 = beaut = beaut_p0 = notices = added = fails = 0.0
    used_days = 0
    for t in trips:
        E = t["edges"]
        if not E:
            continue
        open_X = np.logical_and.reduce([~masks.get(e, np.zeros(DAYS, bool)) for e in E])
        open_0 = np.logical_and.reduce([~p0_masks.get(e, np.zeros(DAYS, bool)) for e in E])
        p = np.max([risk.get(e, np.zeros(DAYS)) for e in E], axis=0)
        D = t["detour"] + (0.0 if p5 else t["p0_extra"])
        use = open_X.copy()
        if price is not None:
            # P3: drive it only when it beats the ban route by more than
            # `price` times the expected stranding cost.
            use &= t["advantage"] > price * p * t["detour"]
        strand += float((use * p * D).sum())
        scen += float(use.sum() * t["seasonal_bkm"])
        scen_p0 += float(open_0.sum() * t["seasonal_bkm"])
        beaut += float((use * t["bkm_open"] + ~use * t["bkm_ban"]).sum())
        beaut_p0 += float((open_0 * t["bkm_open"] + ~open_0 * t["bkm_ban"]).sum())
        used_days += int(use.sum())
        # Days the trip cannot use its seasonal road: the ban route's extra
        # minutes, or no trip at all where the ban route does not exist.
        off = ~use
        if t["ban_fails"]:
            fails += float(off.sum())
        else:
            added += float(off.sum() * max(0.0, t["min_ban"] - t["min_open"]))
        if notice_days is not None:
            near = np.zeros(DAYS, bool)
            for e in E:
                m = p0_masks.get(e)
                if m is None:
                    continue
                # Within `notice_days` of a closed day, either side.
                near |= np.convolve(m.astype(int), np.ones(2 * notice_days + 1, int), "same") > 0
            notices += float((use & near).sum())
    return dict(stranded=strand, added_min=added, failed_trip_days=fails, seasonal_bkm=scen, seasonal_bkm_p0=scen_p0,
                trip_bkm=beaut, trip_bkm_p0=beaut_p0, used_trip_days=used_days, notice_trip_days=notices)


def load_trips(table):
    q1 = pd.read_csv(HERE / "q1_routes.csv")
    sc = q1[q1.arm == "scenic"]
    op = sc[sc.run == "open"].set_index("trip")
    ban = sc[sc.run == "P1"].set_index("trip")
    status = q1.drop_duplicates(["trip", "run"]).set_index(["trip", "run"])["status"]
    q3 = {}
    for name in ("q3_cases_trips.csv",):
        f = HERE / name
        if f.exists():
            c = pd.read_csv(f)
            c = c[c.status == "ok"]
            # Against the planned scenic route, a reroute can come out
            # faster; a detour is never counted as a saving.
            q3 = dict(zip(c.case.str.replace("trip:", "", regex=False), c.detour_min.clip(lower=0)))
    # P0's "pointed back" minutes, from the replayed cases (named roads and
    # the most-used stretches). A trip that starts inside the closure has no
    # approach and nothing to replay, and is left out.
    replayed = pd.concat([pd.read_csv(HERE / f) for f in ("q3_cases.csv", "q3_cases_top.csv")
                          if (HERE / f).exists()])
    replayed = replayed[(replayed.status == "ok") & (replayed.p0_reroutes_asked > 0)]
    extra = float(replayed["p0_extra_min"].median()) if len(replayed) else 0.0
    fallback = float(np.nanmedian(list(q3.values()))) if q3 else 30.0
    trips = []
    samples = {t["name"]: t for t in json.load(open(HERE / "samples.json"))}
    for name in samples:
        if name not in op.index:
            continue
        r = op.loc[name]
        edges = [int(x) for x in str(r.seasonal_edges).split()] if isinstance(r.seasonal_edges, str) else []
        b = ban.loc[name] if name in ban.index else None
        trips.append(dict(
            name=name, sample=samples[name]["sample"], edges=edges,
            seasonal_bkm=float(r.seasonal_beautiful_km), bkm_open=float(r.beautiful_km),
            bkm_ban=float(b.beautiful_km) if b is not None else 0.0,
            min_open=float(r.minutes), min_ban=float(b.minutes) if b is not None else np.nan,
            ban_fails=b is None or status.get((name, "P1")) != 200,
            advantage=(float(b.cost) - float(r.cost)) if b is not None else np.inf,
            detour=float(q3.get(name, fallback)), measured_detour=name in q3,
            p0_extra=extra))
    return trips


def validate(trips, p0):
    """The `uses` approximation against the P0 runs: predicted to drive its
    all-open route's seasonal edges on the day, against whether the server's
    route that day did."""
    q1 = pd.read_csv(HERE / "q1_routes.csv")
    sc = q1[q1.arm == "scenic"].set_index(["trip", "run"])
    rows = []
    for run, day in (("P0@06-15", (6, 15)), ("P0@08-15", (8, 15)), ("P0@10-15", (10, 15))):
        k = W.doy(*day)
        for t in trips:
            if not t["edges"]:
                continue
            pred = all(not p0[e][k] for e in t["edges"] if e in p0)
            got = (t["name"], run) in sc.index and isinstance(sc.loc[(t["name"], run)].seasonal_edges, str) \
                and set(t["edges"]) <= set(int(x) for x in sc.loc[(t["name"], run)].seasonal_edges.split())
            rows.append(dict(run=run, sample=t["sample"], trip=t["name"], predicted=pred, actual=bool(got)))
    v = pd.DataFrame(rows)
    v.to_csv(HERE / "q4_validation.csv", index=False)
    return v.groupby("run").apply(lambda g: pd.Series({
        "trips": len(g), "agree": float((g.predicted == g.actual).mean()),
        "predicted_uses": int(g.predicted.sum()), "actual_uses": int(g.actual.sum())}), include_groups=False)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--default-curve", default="standalone", choices=("standalone", "pooled"),
                    help="WINTER's risk: its own window on the high passes (the default), "
                         "or the pooled curve of every published end, a milder sensitivity")
    args = ap.parse_args()
    suffix = "" if args.default_curve == "standalone" else "_pooled"
    table = W.annotate(pd.read_parquet(DATA / "seasonal_closures.parquet"))
    curves, how, counts = miss_curves(args.default_curve)
    ends = edge_ends(table)
    risk = edge_risk(ends, curves)
    trips = load_trips(table)
    p0 = policy_masks(table)
    print(validate(trips, p0))
    policies = [("P0", {}, False, False, None)]
    policies += [("P1 ban", None, True, False, None)]
    for n in (7, 14, 21, 30):
        policies.append((f"P2 all {n}d", {s: (n, n) for s in W.SOURCES}, False, False, None))
    for n in (7, 14, 21, 30):
        policies.append((f"P2 guessed {n}d", {s: (n, n) for s in ("osm_default", "osm_dated", "unknown", "agency_dated")},
                         False, False, None))
    for n in (14, 21, 30):
        policies.append((f"P2 spring-only {n}d", {s: (0, n) for s in W.SOURCES}, False, False, None))
    for lam in (1, 3, 10):
        policies.append((f"P3 price x{lam}", {}, False, False, lam))
    # Per-source margins, (autumn days before the window, spring days after
    # it), on a grid chosen from Q2: WINTER's spring end is the one that
    # misses most, the hand table's the least.
    grid = product((0, 14, 30, 45), (0, 14), (0, 7, 14), (0, 7), (0, 7, 14))
    for dsp, dau, od, tb, uk in grid:
        m = {"osm_default": (dau, dsp), "osm_dated": (od, od), "table": (tb, tb),
             "unknown": (uk, uk), "agency_dated": (uk, uk)}
        policies.append((f"P2 by source: default {dau}/{dsp}, dated {od}, table {tb}, unknown+agency {uk}",
                         m, False, False, None))
    # The hand table narrowed toward its measured bias (Q2: it stays shut a
    # median 20-30 days after opening), with WINTER's spring end widened.
    for tb_au, tb_sp in ((0, 0), (-7, -14), (-14, -21)):
        for dsp in (30, 45):
            m = {"osm_default": (14, dsp), "osm_dated": (7, 7), "table": (tb_au, tb_sp),
                 "unknown": (0, 0), "agency_dated": (0, 0)}
            policies.append((f"P2 tuned: default 14/{dsp}, dated 7, table {tb_au}/{tb_sp}",
                             m, False, False, None))
    rows = []
    for (name, margins, ban, _, price), p5 in product(policies, (False, True)):
        masks = policy_masks(table, margins, ban)
        for sample in ("us", "near", "ne", "named"):
            sub = [t for t in trips if sample == "all" or t["sample"] == sample]
            r = evaluate(sub, masks, risk, None, p5, price=price, notice_days=14, p0_masks=p0)
            n = max(1, len(sub)) * DAYS
            rows.append(dict(policy=name + (" + P5" if p5 else ""), sample=sample, trips=len(sub),
                             stranded_min_per_1000=1000 * r["stranded"] / n,
                             seasonal_scenery_kept=r["seasonal_bkm"] / max(r["seasonal_bkm_p0"], 1e-9),
                             trip_scenery_kept=r["trip_bkm"] / max(r["trip_bkm_p0"], 1e-9),
                             added_min_per_1000=1000 * r["added_min"] / n,
                             failed_trips_per_1000=1000 * r["failed_trip_days"] / n,
                             seasonal_trip_days_per_1000=1000 * r["used_trip_days"] / n,
                             notice_trip_days_per_1000=1000 * r["notice_trip_days"] / n))
    out = pd.DataFrame(rows)
    out.to_csv(HERE / f"q4_frontier{suffix}.csv", index=False)
    cand = out[~out.policy.str.startswith("P2 by source")].pivot_table(
        index="policy", columns="sample",
        values=["stranded_min_per_1000", "seasonal_scenery_kept"], sort=False)
    cand.to_csv(HERE / f"q4_candidates{suffix}.csv")
    att = []
    for sample in ("us", "near", "ne", "named"):
        sub = [t for t in trips if t["sample"] == sample]
        for (src, end), v in attribution(sub, p0, ends, curves).items():
            att.append(dict(sample=sample, source=src, end=end,
                            stranded_min_per_1000=1000 * v / (max(1, len(sub)) * DAYS)))
    att = pd.DataFrame(att)
    att.to_csv(HERE / f"q4_attribution{suffix}.csv", index=False)
    print(att.pivot_table(index=["source", "end"], columns="sample", values="stranded_min_per_1000").round(1))
    pd.set_option("display.width", 220)
    print("risk curves:", how)
    print({k: v for k, v in counts.items()})
    print(out[(out["sample"] == "us") & ~out.policy.str.startswith("P2 by source")].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
