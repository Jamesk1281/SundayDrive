"""Roads OpenStreetMap marks closed for the season, as a table the router reads.

The graph has one state all year, and the scenery score is drawn to exactly the
roads that close for winter: VT-108 through Smugglers' Notch, the Mt Washington
Auto Road, Lincoln Gap Road. Every route, loop and reroute drove them, the
fastest arm included (docs/pre-submission-review-verdict.md, C-1). This finds
them and writes

  seasonal_closures.parquet   one row per graph edge and closed window:
                              edge (its row in graph_edges.parquet), u, v,
                              way_id, name, ref, tag, start_month, start_day,
                              end_month, end_day, length_m

which `Router` loads if present, pricing each edge at +inf on the days its
window covers. A side table rather than a graph column because carrying the
tags through extract.py and graph.py means a rebuild, and a rebuild moves every
published number; that belongs to the next full rebuild
(docs/seasonal-closures-brief.md, decision 1).

A way is closed for the season when, for a car:
  - `<key>:conditional = no @ <dates>`, for a key that binds a car (CAR_KEYS),
    closes it inside its own dates, including ranges that wrap the year end;
  - `no @ winter` or `no @ snow`, `winter_service=no`, and `seasonal` in
    SEASONAL close it in WINTER, Nov 1 - Apr 30.
Everything else closes nothing here; see `conditional_windows` for which
conditions those are and why.

Usage: python closures.py <input.osm.pbf> <processed_dir>
"""

import re
import sys
import time
from collections import Counter
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer

from common import CLOSURE_WINDOW, CRS_METERS, DRIVABLE, PRIVATE_ACCESS

# The keys whose conditional can close a road to a car. `access` binds every
# road user, `vehicle` everything on wheels, `motor_vehicle` everything with an
# engine and `motorcar` cars. Anything narrower restricts someone else's
# vehicle, and the rest of the `*:conditional` family is not access at all. That
# matters on this extract: two New Hampshire ways carry a winter parking ban,
# `parking:both:restriction:conditional = no_stopping @ (Nov 1-Apr 30)`, dated
# exactly like a closure and containing "no".
CAR_KEYS = ("access", "vehicle", "motor_vehicle", "motorcar")

# The closed window for a tag that says winter without saying when, as
# (start month, start day, end month, end day), both ends included.
WINTER = (11, 1, 4, 30)

# `seasonal=` values meaning the road is only there outside winter. `winter`
# says the reverse and `no` says nothing, so neither is here.
SEASONAL = {"yes", "summer", "spring;summer;autumn", "no_snow"}

# How far an edge's midpoint may sit from a closed way's line and still be one
# of its edges, in metres (EPSG:26986). An edge of the way lies on it, so the
# true distance is zero to rounding; a different road between the same two
# junctions runs metres away at least.
MATCH_M = 1.0

_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun",
           "jul", "aug", "sep", "oct", "nov", "dec")
# 29 for February so that a window ending in it keeps a leap day.
_LAST_DAY = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

_MONTH = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
# "Nov", "Nov 1", "Nov-Apr", "Nov 1-Apr 30", "December - May", "Nov 1-15".
_RANGE = re.compile(
    rf"^{_MONTH}(?:\s+(\d{{1,2}}))?"
    rf"(?:\s*-\s*(?:{_MONTH}(?:\s+(\d{{1,2}}))?|(\d{{1,2}})))?$",
    re.IGNORECASE)
_SEASON = re.compile(r"^(winter|snow)$", re.IGNORECASE)
_NAMES_A_MONTH = re.compile(rf"\b{_MONTH}", re.IGNORECASE)
_YEAR = re.compile(r"\b\d{4}\b")
_TIME = re.compile(r"\d{1,2}:\d{2}|\b(dusk|dawn|sunrise|sunset)\b", re.IGNORECASE)
_WEEKDAY = re.compile(r"\b(mo|mon|tu|tue|we|wed|th|thu|fr|fri|sa|sat|su|sun|ph|sh)\b",
                      re.IGNORECASE)
_VEHICLE = re.compile(r"[<>=]|\band\b", re.IGNORECASE)


def _split_top(value: str, sep: str = ";"):
    """`value` split on `sep` wherever it is not inside parentheses."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(value):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == sep and depth == 0:
            parts.append(value[start:i])
            start = i + 1
    parts.append(value[start:])
    return parts


def _window(m):
    """A `_RANGE` match as (start month, start day, end month, end day), or
    None if one of its days does not exist."""
    m1 = _MONTHS.index(m.group(1)[:3].lower()) + 1
    d1 = int(m.group(2)) if m.group(2) else 1
    if m.group(3):                                  # Nov[ 1]-Apr[ 30]
        m2 = _MONTHS.index(m.group(3)[:3].lower()) + 1
        d2 = int(m.group(4)) if m.group(4) else _LAST_DAY[m2 - 1]
    elif m.group(5):                                # Nov 1-15
        m2, d2 = m1, int(m.group(5))
    else:                                           # Nov, or Nov 1
        m2, d2 = m1, (d1 if m.group(2) else _LAST_DAY[m1 - 1])
    if not (1 <= d1 <= _LAST_DAY[m1 - 1] and 1 <= d2 <= _LAST_DAY[m2 - 1]):
        return None
    return (m1, d1, m2, d2)


def _rule_windows(rule: str):
    """The windows one opening-hours rule closes a road in, and if none, why.

    Checked in this order, and the order is the decision. A comparison or an
    AND restricts some vehicles and not others. A rule naming a year is a
    one-off closure, not a season: `no @ (2022 Apr 04-2022 Oct 28)` read as an
    annual window would close four Manchester, NH ramps every summer for good.
    A rule naming a weekday or a time closes the road only part of the time,
    and the router has no clock to price that with: `no @ May-Sep Su
    09:00-16:00` read as its months alone would close Portland's Baxter
    Boulevard all summer for its Sunday mornings. Such a rule is "part-time"
    when it names a month and "time of day" when it does not.
    """
    if _SEASON.match(rule):
        return [WINTER], None
    if _VEHICLE.search(rule):
        return [], "vehicle"
    if _YEAR.search(rule):
        return [], "dated"
    if _TIME.search(rule) or _WEEKDAY.search(rule):
        return [], "part-time" if _NAMES_A_MONTH.search(rule) else "time of day"
    windows = []
    for part in rule.split(","):
        m = _RANGE.match(part.strip())
        window = _window(m) if m else None
        if window is None:
            return [], "unrecognized"
        windows.append(window)
    return windows, None


def conditional_windows(value: str):
    """The windows a `<key>:conditional` value closes its way in, plus a
    reason for each `no @` rule that closes nothing.

    Only `no @ ...` restrictions close anything; `yes`, `destination` and the
    rest are other questions. The condition's rules (separated by `;`) count
    one at a time, so `no @ (Nov-Dec; Feb-Mar)` closes two windows, while a
    condition that is only a time of day, such as `no @ (22:00-06:00)`, closes
    none (decision 2).
    """
    windows, skipped = [], []
    for restriction in _split_top(value):
        result, at, condition = restriction.partition("@")
        if not at or result.strip().lower() != "no":
            continue
        condition = condition.strip()
        if condition.startswith("(") and condition.endswith(")"):
            condition = condition[1:-1]
        for rule in condition.split(";"):
            rule = rule.strip()
            if not rule:
                continue
            found, reason = _rule_windows(rule)
            windows += [w for w in found if w not in windows]
            if reason:
                skipped.append(reason)
    return windows, skipped


def way_windows(tags) -> dict:
    """{window: [the tags that close the way in it]} for one way's tags.

    `tags` is a mapping, an osmium TagList or a dict. Empty for a way that is
    open all year.
    """
    found = {}

    def close(window, tag):
        found.setdefault(window, [])
        if tag not in found[window]:
            found[window].append(tag)

    for key in CAR_KEYS:
        value = tags.get(f"{key}:conditional")
        if value:
            for window in conditional_windows(value)[0]:
                close(window, f"{key}:conditional={value}")
    if (tags.get("winter_service") or "").strip().lower() == "no":
        close(WINTER, "winter_service=no")
    seasonal = (tags.get("seasonal") or "").strip().lower()
    if seasonal in SEASONAL:
        close(WINTER, f"seasonal={seasonal}")
    return found


def scan(pbf_path: str):
    """Every drivable way the tags close for part of the year, and the count
    of drivable ways seen, which is the control.

    The filter is extract.py's, line for line, down to keeping a way only if
    osmium can build its line, so the count must equal `roads.parquet`'s rows.
    osmium is imported here rather than at the top so that the parser above
    can be imported, and tested, on the serving box, which does not install
    the pipeline's dependencies (server/DEPLOY.md).
    """
    import osmium

    wkb = osmium.geom.WKBFactory()

    class Handler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.drivable = 0
            self.closed = []
            self.skipped = Counter()

        def way(self, w):
            tags = w.tags
            if tags.get("highway") not in DRIVABLE:
                return
            if tags.get("access") in PRIVATE_ACCESS and tags.get("motor_vehicle") != "yes":
                return
            try:
                wkb.create_linestring(w)
            except Exception:
                return
            self.drivable += 1
            for key in CAR_KEYS:
                value = tags.get(f"{key}:conditional")
                if value:
                    for reason in set(conditional_windows(value)[1]):
                        self.skipped[(reason, f"{key}:conditional={value}")] += 1
            windows = way_windows(tags)
            if not windows:
                return
            points = [(n.ref, n.location.lon, n.location.lat)
                      for n in w.nodes if n.location.valid()]
            self.closed.append({
                "way_id": w.id,
                "name": tags.get("name", ""),
                "ref": tags.get("ref", ""),
                "windows": windows,
                "refs": [p[0] for p in points],
                "coords": [(p[1], p[2]) for p in points],
            })

    h = Handler()
    h.apply_file(pbf_path, locations=True, idx="flex_mem")
    return h.drivable, h.closed, h.skipped


def join(closed, edges: gpd.GeoDataFrame) -> pd.DataFrame:
    """The table: each closed way's rows in graph_edges, one per window.

    Two tests, because the first alone closes open roads. graph.py splits a
    way at its junctions, so every edge of a way has both ends among the way's
    nodes, and taking those is the candidate set. But a different road between
    the same two junctions has both ends there too, and `Router.route` keeps
    only the cheapest of parallel edges, so closing both would close the open
    one. Each candidate must also lie along the way: its midpoint within
    MATCH_M of the way's line, in EPSG:26986.
    """
    to_m = Transformer.from_crs(4326, CRS_METERS, always_xy=True)
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    wanted = np.unique(np.concatenate([np.asarray(w["refs"], dtype=np.int64)
                                       for w in closed])) if closed else []
    candidates = np.flatnonzero(np.isin(u, wanted) & np.isin(v, wanted))
    mids = shapely.line_interpolate_point(
        edges.geometry.iloc[candidates].to_crs(CRS_METERS).values,
        0.5, normalized=True)
    by_u = {}
    for i, row in enumerate(candidates):
        by_u.setdefault(int(u[row]), []).append(i)

    rows = []
    for way in closed:
        if len(way["coords"]) < 2:
            continue
        xs, ys = to_m.transform(*zip(*way["coords"]))
        line = shapely.LineString(np.column_stack([xs, ys]))
        refs = set(way["refs"])
        for ref in refs:
            for i in by_u.get(ref, ()):
                row = int(candidates[i])
                if int(v[row]) not in refs or mids[i].distance(line) > MATCH_M:
                    continue
                for window, tags in way["windows"].items():
                    rows.append({
                        "edge": row, "u": int(u[row]), "v": int(v[row]),
                        "way_id": way["way_id"], "name": way["name"],
                        "ref": way.get("ref", ""), "tag": "; ".join(tags),
                        **dict(zip(CLOSURE_WINDOW, window)),
                        "length_m": float(edges["length_m"].iat[row]),
                    })
    table = pd.DataFrame(rows, columns=["edge", "u", "v", "way_id", "name", "ref",
                                        "tag", *CLOSURE_WINDOW, "length_m"])
    # Two ways can share an edge only where they overlap, which is a mapping
    # error; keep the edge once per window either way.
    table = table.drop_duplicates(["edge", *CLOSURE_WINDOW]).sort_values(
        ["edge", *CLOSURE_WINDOW]).reset_index(drop=True)
    for col in CLOSURE_WINDOW:
        table[col] = table[col].astype("int8")
    return table


def _window_label(window):
    sm, sd, em, ed = window
    return f"{_MONTHS[sm - 1].title()} {sd} - {_MONTHS[em - 1].title()} {ed}"


def main(pbf_path: str, processed_dir: str):
    d = Path(processed_dir)
    t0 = time.time()
    drivable, closed, skipped = scan(pbf_path)
    print(f"scanned in {time.time() - t0:.0f}s: {drivable:,} drivable ways, "
          f"{len(closed):,} of them closed for part of the year")
    roads = d / "roads.parquet"
    if roads.exists():
        import pyarrow.parquet as pq
        control = pq.ParquetFile(roads).metadata.num_rows
        verdict = "matches" if control == drivable else "DOES NOT MATCH"
        print(f"control: roads.parquet has {control:,} ways, which {verdict} the scan")

    edges = gpd.read_parquet(d / "graph_edges.parquet",
                             columns=["u", "v", "length_m", "score", "geometry"])
    table = join(closed, edges)
    table.to_parquet(d / "seasonal_closures.parquet", index=False)

    unique = table.drop_duplicates("edge")
    km = unique["length_m"].sum() / 1000.0
    score = edges["score"].to_numpy()[unique["edge"].to_numpy()]
    lengths = unique["length_m"].to_numpy()
    print(f"in the graph: {table['way_id'].nunique():,} ways, {len(unique):,} edges, "
          f"{km:.1f} km; length-weighted score {np.average(score, weights=lengths):.2f}, "
          f"{lengths[score >= 7.0].sum() / lengths.sum():.1%} of km at 7 or more")
    absent = len(closed) - table["way_id"].nunique()
    print(f"not in the graph: {absent:,} closed ways have no edge in it "
          "(outside the largest component, or under 1 m)")
    for window, group in table.groupby(list(CLOSURE_WINDOW)):
        print(f"  closed {_window_label(window):>17}: {group['way_id'].nunique():4,} ways, "
              f"{group.drop_duplicates('edge')['length_m'].sum() / 1000:6.1f} km")
    if skipped:
        # Ways, not rules, and every tag but the time-of-day bulk spelled out:
        # those are the judgement calls a reader may want to overrule.
        print("car conditionals with a rule that closes nothing, by reason (ways):")
        for reason in sorted({r for r, _ in skipped}):
            tags = {t: n for (r, t), n in skipped.items() if r == reason}
            print(f"  {reason}: {sum(tags.values()):,}")
            if reason != "time of day":
                for tag, n in sorted(tags.items()):
                    print(f"    {n:3,}  {tag}")
    print(f"wrote seasonal_closures.parquet ({len(table):,} rows) "
          f"in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
