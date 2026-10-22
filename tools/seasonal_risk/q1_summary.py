"""Q1's tables, from q1_routes.csv (scenic arm, pref 0.5).

  q1_by_run.csv    per sample and run: trips answered, CLOSED_FOR_SEASON
                   and other failures, share of routes on a seasonal edge,
                   beautiful km in all and on seasonal edges, minutes
  q1_named.csv     per named road (both directions summed): all open against
                   the ban, and whether the road is driven on Jun 15, Aug 15
                   and Oct 15

  python q1_summary.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def main():
    d = pd.read_csv(HERE / "q1_routes.csv")
    first = d.drop_duplicates(["trip", "run"])
    sc = d[d.arm == "scenic"]
    by = first.groupby(["sample", "run"]).agg(
        trips=("trip", "size"), answered=("status", lambda s: int((s == 200).sum())),
        closed_for_season=("code", lambda s: int((s == "CLOSED_FOR_SEASON").sum())),
        other_failures=("status", lambda s: 0))
    by["other_failures"] = by.trips - by.answered - by.closed_for_season
    s = sc.assign(on=sc.seasonal_km > 0).groupby(["sample", "run"]).agg(
        on_seasonal_share=("on", "mean"), beautiful_km=("beautiful_km", "sum"),
        seasonal_beautiful_km=("seasonal_beautiful_km", "sum"), minutes=("minutes", "sum"))
    out = by.join(s).reset_index()
    out.to_csv(HERE / "q1_by_run.csv", index=False)

    n = sc[sc["sample"] == "named"].assign(road=lambda x: x.trip.str.split(":").str[0])
    codes = first[first["sample"] == "named"].assign(road=lambda x: x.trip.str.split(":").str[0])
    rows = []
    for road, g in n.groupby("road"):
        c = codes[codes.road == road]
        get = lambda run, col: g[g.run == run][col].sum()
        fails = lambda run: int((c[c.run == run].code == "CLOSED_FOR_SEASON").sum())
        rows.append(dict(
            road=road, trips=c.trip.nunique(),
            open_minutes=get("open", "minutes"), open_seasonal_beautiful_km=get("open", "seasonal_beautiful_km"),
            ban_minutes=get("P1", "minutes") if fails("P1") == 0 else None,
            ban_closed_for_season=fails("P1"),
            **{f"driven_{k[3:]}": int((g[g.run == k].seasonal_km > 0).sum()) for k in ("P0@06-15", "P0@08-15", "P0@10-15")},
            **{f"closed_{k[3:]}": fails(k) for k in ("P0@06-15", "P0@08-15", "P0@10-15")}))
    named = pd.DataFrame(rows)
    named["ban_extra_minutes_per_trip"] = (named.ban_minutes - named.open_minutes) / named.trips
    named.to_csv(HERE / "q1_named.csv", index=False)
    pd.set_option("display.width", 220)
    print(out.round(3).to_string(index=False))
    print(named.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
