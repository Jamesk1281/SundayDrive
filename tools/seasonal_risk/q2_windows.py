"""Q2: how far our windows miss the published opening and closing dates.

Reads q2_published_dates.csv (one row per road and season, each date with
its URL) and the deployed seasonal_closures.parquet, read only. For each road
it takes, per window source, the window that covers most of the road's km
(`road_windows`), and the router's effective window, the union of those (a
day is closed if any source closes it, as `SeasonalClosures` does).

Two misses per road-season and window, in days, signed so that positive is
the dangerous side, the router saying open while the road is shut:

  open_miss   = actual opening - our first open day
  close_miss  = our first closed day - actual closing

`in_sample` marks a season the hand table's own window was chosen from (its
`basis` in pipeline/winter_windows.json names them): a ten-season-longest
window cannot miss on its own ten seasons, so only the other seasons test it.

  python q2_windows.py      ->  q2_misses.csv, and a summary on stdout
"""

import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import roads as R            # noqa: E402
import windows as W          # noqa: E402

# The served table unless SUNDAYDRIVE_DATA names another (the rebuilt one,
# docs/seasonal-road-policy.md).
DATA = Path(os.environ.get("SUNDAYDRIVE_DATA",
                           "/Users/james./Desktop/myapps/SundayDrive/data/processed-us"))

# Q2 road -> (roads.py key, extra row filter). Crater Lake's two halves and
# Old Fall River Road are Q2-only.
Q2_ROADS = {
    "tioga": ("tioga", None), "gtsr": ("gtsr", None), "lassen": ("lassen", None),
    "trail_ridge": ("trail_ridge", None),
    "old_fall_river": (None, lambda t: t["name"] == "Old Fall River Road"),
    # By the rims' own table rows where they exist (docs/seasonal-road-policy.md,
    # fix 2): in the graph "Rim Drive" is part of the East rim's path.
    "crater_lake_west": ("crater_lake", lambda t: t["tag"].str.startswith("table crater_lake_west")
                         | t["name"].isin(["West Rim Drive", "North Entrance Road"])),
    "crater_lake_east": ("crater_lake", lambda t: t["tag"].str.startswith("table crater_lake_east")
                         | (t["name"] == "East Rim Drive")),
    "chinook": ("chinook", None), "north_cascades": ("north_cascades", None),
    "independence": ("independence", None), "vt108": ("vt108", None),
    "lincoln_gap": ("lincoln_gap", None), "greylock": ("greylock", None),
    "beartooth": ("beartooth", None), "sonora": ("sonora", None),
    "stevens_canyon": ("stevens_canyon", None), "sunrise": ("sunrise", None),
}

# The seasons each hand-table window was fitted on (winter_windows.json
# `basis`), by road. A park window written from prose has none.
IN_SAMPLE = {
    "lassen": range(2016, 2027), "chinook": range(2016, 2026),
    "north_cascades": range(2016, 2026), "independence": range(2015, 2026),
    "sonora": range(2016, 2026), "beartooth": range(2026, 2027),
}


def road_windows(table: pd.DataFrame, road: str) -> dict:
    """{source: window} for the window covering most of the road's km per
    source, plus "effective", the union of their closed days."""
    key, extra = Q2_ROADS[road]
    t = table.fillna({"name": "", "ref": "", "tag": ""})
    rows = R.edges_of(t, key) if key else t
    if extra is not None:
        rows = rows[extra(rows)]
    out = {}
    for src, g in rows.groupby("source"):
        g = g.assign(w=list(map(tuple, g[W.COLS].to_numpy())))
        out[src] = max(g.groupby("w")["length_m"].sum().items(), key=lambda kv: kv[1])[0]
    return out


def route_rows(table: pd.DataFrame, road: str):
    """The table rows on the seasonal edges the server's all-open scenic
    route across the road drives (Q1's named trips, both ways), or None.
    The router closes a through trip on any of them, however short: one
    30 m edge sets North Cascades' window."""
    key = Q2_ROADS[road][0]
    f = HERE / "q1_routes.csv"
    if key is None or Q2_ROADS[road][1] is not None or not f.exists():
        return None
    q1 = pd.read_csv(f)
    q1 = q1[(q1["sample"] == "named") & (q1.run == "open") & (q1.arm == "scenic")
            & q1.trip.str.startswith(key + ":") & q1.seasonal_edges.notna()]
    edges = {int(e) for x in q1.seasonal_edges for e in str(x).split()}
    return table[table.edge.isin(edges)] if edges else None


def bound_by(rows: pd.DataFrame, o: int, c: int):
    """The sources of the rows whose own window ends the day before `o`, and
    that start on `c`: the ones that set the effective window's ends."""
    so, sc = set(), set()
    for w, src in zip(rows[W.COLS].to_numpy(), rows["source"]):
        m = W.window_mask(w)
        if m[(o - 1) % W.DAYS] and not m[o % W.DAYS]:
            so.add(src)
        if m[c % W.DAYS] and not m[(c - 1) % W.DAYS]:
            sc.add(src)
    return "+".join(sorted(so)), "+".join(sorted(sc))


def first_open_and_closed(mask: np.ndarray):
    """(first open day after the winter closure, first closed day of the next
    one) as day-of-year, for a mask closed over one winter."""
    if mask.all() or not mask.any():
        return None, None
    open_days = np.flatnonzero(~mask)
    # The open season is one run of days in a winter window; find its ends.
    runs = np.split(open_days, np.flatnonzero(np.diff(open_days) > 1) + 1)
    season = max(runs, key=len)
    return int(season[0]), int(season[-1]) + 1


def doy(s: str):
    if not isinstance(s, str) or not s:
        return None
    d = date.fromisoformat(s)
    return (d - date(d.year, 1, 1)).days - (1 if (d.year % 4 == 0 and d.month > 2) else 0)


def main():
    table = W.annotate(pd.read_parquet(DATA / "seasonal_closures.parquet"))
    pub = pd.read_csv(HERE / "q2_published_dates.csv")
    out = []
    for road, g in pub.groupby("road"):
        wins = road_windows(table, road)
        masks = {s: W.window_mask(w) for s, w in wins.items()}
        on_route = route_rows(table, road)
        if on_route is not None:
            masks["effective"] = np.logical_or.reduce([W.window_mask(w) for w in on_route[W.COLS].to_numpy()])
            how = "route"
        elif masks:
            masks["effective"] = np.logical_or.reduce(list(masks.values()))
            how = "km-majority"
        for which, m in masks.items():
            o, c = first_open_and_closed(m)
            ob = cb = ""
            if which == "effective":
                rows = on_route if on_route is not None else None
                if rows is None:
                    own = {s: W.window_mask(w) for s, w in wins.items()}
                    ob = "+".join(sorted(s for s, x in own.items() if first_open_and_closed(x)[0] == o))
                    cb = "+".join(sorted(s for s, x in own.items() if first_open_and_closed(x)[1] == c))
                else:
                    ob, cb = bound_by(rows, o, c)
            for _, r in g.iterrows():
                ao, ac = doy(r["opened"]), doy(r["closed"])
                # A closing in January belongs to the season before it.
                if ac is not None and ac < 120:
                    ac += 365
                out.append(dict(
                    road=road, season=r["season"], window_source=which,
                    window="" if which == "effective" else "%d/%d-%d/%d" % wins[which],
                    our_open=W.day_of(o).isoformat()[5:] if o is not None else "",
                    our_close=W.day_of(c).isoformat()[5:] if c is not None else "",
                    opened=r["opened"], closed=r["closed"],
                    open_quality=r["open_quality"], close_quality=r["close_quality"],
                    open_miss=(ao - o) if ao is not None and o is not None else None,
                    close_miss=(c - ac) if ac is not None and c is not None else None,
                    in_sample=int(r["season"]) in IN_SAMPLE.get(road, ()) and which in ("table", "effective"),
                    effective_from=how if which == "effective" else "",
                    open_bound_by=ob, close_bound_by=cb,
                    source_url=r["source_url"]))
    df = pd.DataFrame(out)
    df.to_csv(HERE / "q2_misses.csv", index=False)

    pd.set_option("display.width", 200)
    print("Per road, effective window (what the router does):")
    eff = df[df.window_source == "effective"]
    print(eff.groupby("road").agg(
        our_open=("our_open", "first"), our_close=("our_close", "first"),
        n_open=("open_miss", "count"), open_danger_seasons=("open_miss", lambda x: int((x > 0).sum())),
        open_danger_days=("open_miss", lambda x: int(x.clip(lower=0).sum())),
        open_lost_median=("open_miss", lambda x: float(np.nanmedian((-x).clip(lower=0))) if x.notna().any() else np.nan),
        n_close=("close_miss", "count"), close_danger_seasons=("close_miss", lambda x: int((x > 0).sum())),
        close_danger_days=("close_miss", lambda x: int(x.clip(lower=0).sum())),
        close_lost_median=("close_miss", lambda x: float(np.nanmedian((-x).clip(lower=0))) if x.notna().any() else np.nan),
    ).to_string())
    print("\nPer window source, each source's own window on the roads that carry it:")
    own = df[df.window_source != "effective"]
    for src, g in own.groupby("window_source"):
        for end in ("open_miss", "close_miss"):
            x = g[end].dropna()
            if not len(x):
                continue
            print(f"{src:13s} {end:10s} n={len(x):3d} roads={g.loc[x.index, 'road'].nunique():2d} "
                  f"danger={int((x > 0).sum()):3d} ({(x > 0).mean():5.1%}) "
                  f"p50={np.percentile(x, 50):+6.0f} p90={np.percentile(x, 90):+6.0f} max={x.max():+5.0f}")



def binding(df: pd.DataFrame) -> pd.DataFrame:
    """Each road's effective window ends with the source(s) that set them:
    the rows' sources whose own window ends where the effective one does
    (recorded by `main`)."""
    eff = df[df.window_source == "effective"].drop_duplicates("road")
    return eff[["road", "effective_from", "our_open", "our_close", "open_bound_by", "close_bound_by"]].reset_index(drop=True)


def by_binding(df: pd.DataFrame) -> pd.DataFrame:
    """The effective misses, grouped by the source that sets each end."""
    b = binding(df).set_index("road")
    eff = df[df.window_source == "effective"].copy()
    out = []
    for end, col in (("open", "open_bound_by"), ("close", "close_bound_by")):
        x = eff.assign(bound_by=eff.road.map(b[col]), miss=eff[f"{end}_miss"]).dropna(subset=["miss"])
        # A season is in sample only for an end the hand table sets.
        x = x.assign(in_sample=x.in_sample.astype(bool) & x.bound_by.str.contains("table"))
        for (src, ins), g in x.groupby(["bound_by", "in_sample"]):
            out.append(dict(end=end, bound_by=src, in_sample=ins, road_seasons=len(g),
                            roads=g.road.nunique(), danger_seasons=int((g.miss > 0).sum()),
                            danger_share=round(float((g.miss > 0).mean()), 3),
                            danger_days_per_season=round(float(g.miss.clip(lower=0).mean()), 1),
                            lost_days_per_season=round(float((-g.miss).clip(lower=0).mean()), 1),
                            worst=int(g.miss.max())))
    return pd.DataFrame(out)


if __name__ == "__main__":
    main()
    d = pd.read_csv(HERE / "q2_misses.csv")
    s = by_binding(d)
    s.to_csv(HERE / "q2_by_binding_source.csv", index=False)
    print("\nEffective window, by the source that sets each end:")
    print(binding(d).to_string(index=False))
    print(s.to_string(index=False))
