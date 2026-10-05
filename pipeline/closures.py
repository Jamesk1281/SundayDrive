"""Roads OpenStreetMap closes to cars, for the season or all year, as two tables
the router reads.

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
window covers.

The same pass finds what OSM closes to cars all year. extract.py and graph.py
drop a road only for `access=no|private`, so the graph keeps `motor_vehicle=no`
roads, `access=permit` ones and fords, and every gate, block, chain and bollard
standing on an open road; routes, loops and reroutes drove through them
(docs/closed-roads.md). It writes

  closed_to_cars.parquet      one row per graph edge and what closes it:
                              edge, u, v, rule, kind, osm_type, osm_id, tag,
                              at_m, name, length_m

`rule` is "edge" where the edge is closed both ways, by its way's tags or by a
barrier or ford standing on it, and "through" where a barrier stands on the
node at which two edges meet end to end: each side stays open up to it and only
driving through is forbidden. `at_m` is a barrier's distance from `u` along the
edge, which `Router.snap` compares with a point's own to keep a driver on their
side of it. `Router` loads it if present and closes those edges and movements
for every request.

Side tables rather than graph columns because carrying the tags through
extract.py and graph.py means a rebuild, and a rebuild moves every published
number; that belongs to the next full rebuild (docs/seasonal-closures.md,
decision 1; docs/closed-roads.md).

A way is closed for the season when, for a car:
  - `<key>:conditional = no @ <dates>`, for a key that binds a car (CAR_KEYS),
    closes it inside its own dates, including ranges that wrap the year end;
  - `<key>:conditional = yes @ <dates>` closes it outside them, which is how
    Mt Greylock's summit roads are tagged (`_open_only_windows`);
  - `no @ winter` or `no @ snow`, `winter_service=no`, and `seasonal` in
    SEASONAL close it in WINTER, Nov 1 - Apr 30.
Everything else closes nothing here; see `conditional_windows` for which
conditions those are and why.

A way is closed to cars all year when `closed_to_cars` (common.py) says so or
it is a ford (`ford=yes`), and a node closes the road it stands on when
`barrier_closes` says so. Where that node stands decides what is closed; see
`join_closed_to_cars`.

Usage: python closures.py <input.osm.pbf> <processed_dir>
"""

import re
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer

from common import (CLOSED_TO_CARS, CLOSURE_WINDOW, CRS_METERS, DRIVABLE,
                    PASSABLE_BARRIERS, PRIVATE_ACCESS, barrier_closes, car_access,
                    closed_to_cars, in_window)

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
_YEAR_DAYS = [(m, d) for m in range(1, 13) for d in range(1, _LAST_DAY[m - 1] + 1)]

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


def _open_only_windows(condition: str):
    """The windows a `yes @ <condition>` closes its way in: every day outside
    the dates it opens on.

    The inverse of `no @`, and how Mt Greylock's two summit roads, the highest
    scoring of every road here, are tagged: `motor_vehicle:conditional = yes @
    (May 20-Oct 29, sunrise-sunset)` with no base `no`. So they are closed from
    Oct 30 to May 19. Strict opening-hours grammar would read that comma as a
    second rule, open by daylight all year; the mapper meant a season with
    daylight hours. So a time or weekday narrows an opening and nothing
    more, and only the days outside every rule's dates are closed. A rule
    with no dates opens the road on every date at some hour, which closes
    nothing, and keeps the I-93 lanes tagged `yes @ (Mo-Fr 05:00-10:00)` as
    open as they were. Anything else unread closes nothing either.
    """
    opening = []
    for rule in condition.split(";"):
        rule = rule.strip()
        if not rule:
            continue
        if _SEASON.match(rule) or _VEHICLE.search(rule) or _YEAR.search(rule):
            return []
        dates = []
        for part in rule.split(","):
            words = [w for w in part.split()
                     if not (_TIME.search(w) or _WEEKDAY.search(w))]
            if not words:
                continue
            m = _RANGE.match(" ".join(words))
            window = _window(m) if m else None
            if window is None:
                return []
            dates.append(window)
        if not dates:
            return []
        opening += dates
    return _complement(opening)


def _complement(windows):
    """The windows left closed when a road is open only inside `windows`."""
    closed = [not any(in_window(w, md) for w in windows) for md in _YEAR_DAYS]
    if not any(closed) or all(closed):
        return []
    # Walked from an open day, so no closed run is split by the year end.
    first = closed.index(False)
    runs, run = [], None
    for i in list(range(first, len(_YEAR_DAYS))) + list(range(first)):
        if closed[i]:
            run = [i, i] if run is None else [run[0], i]
        elif run is not None:
            runs.append(run)
            run = None
    if run is not None:
        runs.append(run)
    return [(*_YEAR_DAYS[a], *_YEAR_DAYS[b]) for a, b in runs]


def conditional_windows(value: str):
    """The windows a `<key>:conditional` value closes its way in, plus a
    reason for each `no @` rule that closes nothing.

    `no @ ...` closes the road inside its dates and `yes @ ...` outside them
    (`_open_only_windows`); `destination`, `private` and the rest are other
    questions. A `no` condition's rules (separated by `;`) count one at a
    time, so `no @ (Nov-Dec; Feb-Mar)` closes two windows, while a condition
    that is only a time of day, such as `no @ (22:00-06:00)`, closes none
    (decision 2).
    """
    windows, skipped = [], []
    for restriction in _split_top(value):
        result, at, condition = restriction.partition("@")
        result = result.strip().lower()
        if not at or result not in ("no", "yes"):
            continue
        condition = condition.strip()
        if condition.startswith("(") and condition.endswith(")"):
            condition = condition[1:-1]
        if result == "yes":
            windows += [w for w in _open_only_windows(condition) if w not in windows]
            continue
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


# The values of a car key that are open to a driver with business there, which
# the router leaves open (docs/closed-roads.md), and the other values it knows
# to be open; anything else is open too, and counted as unrecognised.
LOCAL_ACCESS = {"destination", "customers"}
KNOWN_OPEN = {"yes", "permissive", "designated", "discouraged", "unknown"} | LOCAL_ACCESS

# The barrier values that are gates, for counting the ones whose access
# depends on the time of day.
GATES = {"gate", "lift_gate", "swing_gate"}


def scan(pbf_path: str):
    """Everything both tables are made from, in one pass over the PBF.

    Returns a SimpleNamespace of:
      drivable   the drivable ways seen, which is the control. The filter is
                 extract.py's, line for line, down to keeping a way only if
                 osmium can build its line, so this must equal
                 `roads.parquet`'s rows;
      closed     the ways closed for part of the year, and `skipped`, the car
                 conditionals with a rule that closes nothing, by reason;
      ways       every drivable way the all-year join needs: the ones closed
                 to cars (`closes` names the tags) and the ones a closing
                 barrier stands on (`closes` empty);
      barriers   {node id: (lon, lat, why, [index into `ways`])} for every node
                 a drivable way passes through that `barrier_closes` says
                 stops a car;
      record     counts of what was found and left alone on purpose, for
                 docs/closed-roads.md.

    osmium is imported here rather than at the top so that the parser above
    can be imported, and tested, on the serving box, which does not install
    the pipeline's dependencies (server/DEPLOY.md). Only nodes tagged
    `barrier` or `ford` reach Python, through a KeyFilter, so reading nodes
    costs the pass almost nothing: 71 s on the New England extract.
    """
    import osmium

    wkb = osmium.geom.WKBFactory()

    class Handler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.drivable = 0
            self.closed = []
            self.skipped = Counter()
            self.tagged = {}            # barrier/ford node id -> (lon, lat, tags)
            self.ways = []
            self.barriers = {}
            self.counted = set()
            self.record = {key: Counter() for key in (
                "dropped but open", "local access", "unrecognised",
                "left open", "timed gates")}

        def node(self, n):
            if n.location.valid():
                self.tagged[n.id] = (n.location.lon, n.location.lat,
                                     {t.k: t.v for t in n.tags})

        def way(self, w):
            tags = w.tags
            if tags.get("highway") not in DRIVABLE:
                return
            if tags.get("access") in PRIVATE_ACCESS and tags.get("motor_vehicle") != "yes":
                # Already out of the graph. Counted where the full rule would
                # let a car in, because re-admitting those takes a rebuild.
                found = car_access(tags)
                if found is not None and found[1] not in CLOSED_TO_CARS:
                    self.record["dropped but open"][f"{found[0]}={found[1]}"] += 1
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
            points = None
            windows = way_windows(tags)
            if windows:
                points = _points(w)
                self.closed.append({
                    "way_id": w.id,
                    "name": tags.get("name", ""),
                    "ref": tags.get("ref", ""),
                    "windows": windows,
                    "refs": [p[0] for p in points],
                    "coords": [(p[1], p[2]) for p in points],
                })
            self._all_year(w, tags, points)

        def _all_year(self, w, tags, points):
            closes = []
            tag = closed_to_cars(tags)
            if tag:
                closes.append(tag)
            if (tags.get("ford") or "").strip().lower() == "yes":
                closes.append("ford=yes")
            found = car_access(tags)
            if found is not None and found[1] in LOCAL_ACCESS:
                self.record["local access"][f"{found[0]}={found[1]}"] += 1
            elif (found is not None and found[1] not in CLOSED_TO_CARS
                  and found[1] not in KNOWN_OPEN):
                self.record["unrecognised"][f"{found[0]}={found[1]}"] += 1
            stops = []
            for n in w.nodes:
                hit = self.tagged.get(n.ref)
                if hit is None:
                    continue
                why = barrier_closes(hit[2])
                if why:
                    stops.append((n.ref, hit, why))
                if n.ref not in self.counted:
                    self.counted.add(n.ref)
                    self._count(hit[2], why)
            if not closes and not stops:
                return
            points = points or _points(w)
            self.ways.append({
                "way_id": w.id,
                "name": tags.get("name", ""),
                "closes": "; ".join(closes),
                # What closes the way itself, when something does.
                "kind": ("way" if tag else "ford") if closes else "",
                "refs": [p[0] for p in points],
                "coords": [(p[1], p[2]) for p in points],
            })
            for ref, (lon, lat, _), why in stops:
                self.barriers.setdefault(ref, (lon, lat, why, []))[3].append(
                    len(self.ways) - 1)

        def _count(self, tags, why):
            """One tally per node, of the ones left open and the gates whose
            access depends on the time, for the record."""
            barrier = (tags.get("barrier") or "").strip().lower()
            if barrier in GATES and ("opening_hours" in tags or any(
                    f"{key}:conditional" in tags for key in CAR_KEYS)):
                self.record["timed gates"]["closed" if why else "left open"] += 1
            if why or not barrier:
                return
            found = car_access(tags)
            if found is None:
                self.record["left open"][f"{barrier}, untagged"] += 1
            else:
                self.record["left open"][f"{barrier}, {found[0]}={found[1]}"] += 1

    h = Handler()
    tagged = osmium.filter.KeyFilter("barrier", "ford").enable_for(osmium.osm.NODE)
    h.apply_file(pbf_path, locations=True, idx="flex_mem", filters=[tagged])
    return SimpleNamespace(drivable=h.drivable, closed=h.closed, skipped=h.skipped,
                           ways=h.ways, barriers=h.barriers, record=h.record)



def _points(w):
    return [(n.ref, n.location.lon, n.location.lat)
            for n in w.nodes if n.location.valid()]


def _way_edges(ways, edges: gpd.GeoDataFrame):
    """(way, edge row) for every graph edge of each way.

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
                                       for w in ways])) if ways else []
    candidates = np.flatnonzero(np.isin(u, wanted) & np.isin(v, wanted))
    mids = shapely.line_interpolate_point(
        edges.geometry.iloc[candidates].to_crs(CRS_METERS).values,
        0.5, normalized=True)
    by_u = {}
    for i, row in enumerate(candidates):
        by_u.setdefault(int(u[row]), []).append(i)

    for way in ways:
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
                yield way, row


def join(closed, edges: gpd.GeoDataFrame) -> pd.DataFrame:
    """The seasonal table: each closed way's rows in graph_edges, one per
    window, found by `_way_edges`."""
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    rows = []
    for way, row in _way_edges(closed, edges):
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


# closed_to_cars.parquet's columns, in order; see the module docstring.
CLOSED_TO_CARS_COLUMNS = ["edge", "u", "v", "rule", "kind", "osm_type", "osm_id",
                          "tag", "at_m", "name", "length_m"]


def join_closed_to_cars(ways, barriers, edges: gpd.GeoDataFrame):
    """The all-year table, and the closing barriers it leaves alone.

    A way closes its edges, found as a seasonal way's are (`_way_edges`). A
    barrier closes by where it stands, which the graph decides
    (docs/closed-roads.md, "Where the barriers stand"):
      - inside an edge, it closes that edge both ways, and `at_m` records how
        far along it stands. The edge is found by position, not by midpoint,
        since a barrier stands anywhere along its edge: both ends among the
        way's nodes, and the barrier within MATCH_M of the edge's line;
      - on a node where exactly two edges meet, it forbids driving through:
        one "through" row per edge. Each road is open up to the barrier, so
        closing either edge would close an open road;
      - on a dead end, it closes nothing. Nothing drives through a dead end,
        and closing its edge would only stop a route reaching the road up to
        the barrier;
      - on a node where three or more edges meet, it closes nothing either.
        Which of them it bars is a guess, and both on this extract are
        mapping errors.

    Returns (table, left), `left` holding the barrier node ids left alone, by
    where they stand.
    """
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    length = edges["length_m"].to_numpy()
    names = (edges["name"].fillna("").to_numpy() if "name" in edges.columns
             else np.full(len(edges), ""))

    def row(r, rule, kind, osm_type, osm_id, tag, at_m):
        return {"edge": r, "u": int(u[r]), "v": int(v[r]), "rule": rule,
                "kind": kind, "osm_type": osm_type, "osm_id": int(osm_id),
                "tag": tag, "at_m": at_m, "name": names[r],
                "length_m": float(length[r])}

    rows = [row(r, "edge", way["kind"], "way", way["way_id"], way["closes"], np.nan)
            for way, r in _way_edges([w for w in ways if w["closes"]], edges)]

    ends, degrees = np.unique(np.concatenate([u, v]), return_counts=True)
    degree = dict(zip(ends.tolist(), degrees.tolist()))
    on_node = {}
    for r in np.flatnonzero(np.isin(u, list(barriers)) | np.isin(v, list(barriers))):
        for end in {int(u[r]), int(v[r])}:
            if end in barriers:
                on_node.setdefault(end, []).append(int(r))

    # Candidate edges for the barriers inside one, projected once.
    to_m = Transformer.from_crs(4326, CRS_METERS, always_xy=True)
    inside = [b for nid, b in barriers.items() if nid not in degree]
    wanted = (np.unique(np.concatenate([np.asarray(ways[i]["refs"], dtype=np.int64)
                                        for b in inside for i in b[3]]))
              if inside else np.empty(0, np.int64))
    candidates = np.flatnonzero(np.isin(u, wanted) & np.isin(v, wanted))
    geoms = edges.geometry.iloc[candidates].to_crs(CRS_METERS).values
    by_u = {}
    for i, r in enumerate(candidates):
        by_u.setdefault(int(u[r]), []).append(i)

    left = {"dead end": [], "junction": [], "not in the graph": []}
    for nid in sorted(barriers):
        lon, lat, why, owners = barriers[nid]
        kind = "ford" if why == "ford=yes" else "barrier"
        if nid not in degree:
            point = shapely.Point(*to_m.transform(lon, lat))
            hits = set()
            for w in owners:
                refs = set(ways[w]["refs"])
                for ref in refs:
                    for i in by_u.get(ref, ()):
                        if (int(v[candidates[i]]) in refs
                                and geoms[i].distance(point) <= MATCH_M):
                            hits.add(i)
            if not hits:
                left["not in the graph"].append(nid)
            for i in sorted(hits):
                rows.append(row(int(candidates[i]), "edge", kind, "node", nid, why,
                                float(geoms[i].project(point))))
        elif degree[nid] == 2 and len(on_node.get(nid, ())) == 2:
            for r in on_node[nid]:
                rows.append(row(r, "through", kind, "node", nid, why,
                                0.0 if int(u[r]) == nid else float(length[r])))
        elif degree[nid] == 1:
            left["dead end"].append(nid)
        else:
            left["junction"].append(nid)

    table = pd.DataFrame(rows, columns=CLOSED_TO_CARS_COLUMNS)
    # An edge two closed ways overlap on, or a barrier listed by two ways,
    # once each.
    table = (table.drop_duplicates(["edge", "rule", "osm_type", "osm_id"])
             .sort_values(["edge", "rule", "at_m", "osm_id"]).reset_index(drop=True))
    table = table.astype({"edge": "int64", "u": "int64", "v": "int64",
                          "osm_id": "int64", "at_m": "float64",
                          "length_m": "float64"})
    return table, left


def _window_label(window):
    sm, sd, em, ed = window
    return f"{_MONTHS[sm - 1].title()} {sd} - {_MONTHS[em - 1].title()} {ed}"


def main(pbf_path: str, processed_dir: str):
    d = Path(processed_dir)
    t0 = time.time()
    found = scan(pbf_path)
    drivable, closed, skipped = found.drivable, found.closed, found.skipped
    print(f"scanned in {time.time() - t0:.0f}s: {drivable:,} drivable ways, "
          f"{len(closed):,} of them closed for part of the year")
    roads = d / "roads.parquet"
    if roads.exists():
        import pyarrow.parquet as pq
        control = pq.ParquetFile(roads).metadata.num_rows
        verdict = "matches" if control == drivable else "DOES NOT MATCH"
        print(f"control: roads.parquet has {control:,} ways, which {verdict} the scan")

    edges = gpd.read_parquet(d / "graph_edges.parquet",
                             columns=["u", "v", "length_m", "score", "name", "geometry"])
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

    cars, left = join_closed_to_cars(found.ways, found.barriers, edges)
    cars.to_parquet(d / "closed_to_cars.parquet", index=False)
    _report(found, cars, left)
    print(f"wrote closed_to_cars.parquet ({len(cars):,} rows) "
          f"in {time.time() - t0:.0f}s")


LEFT_ALONE = {"dead end": "at a dead end",
              "junction": "where three or more edges meet",
              "not in the graph": "on no edge of the graph"}


def _report(found, cars, left):
    """What the all-year table holds, and what it leaves open on purpose: the
    counts docs/closed-roads.md records."""
    by_way = cars[cars["osm_type"] == "way"]
    print(f"closed to cars all year: {by_way['osm_id'].nunique():,} ways in the "
          f"graph ({by_way['edge'].nunique():,} edges, "
          f"{by_way.drop_duplicates('edge')['length_m'].sum() / 1000:.1f} km) of "
          f"{sum(1 for w in found.ways if w['closes']):,} in the PBF, by the tag "
          "that closes them:")
    for tag, group in sorted(by_way.groupby("tag"), key=lambda g: -g[1]["osm_id"].nunique()):
        print(f"  {group['osm_id'].nunique():5,} ways {group['edge'].nunique():5,} edges "
              f"{group.drop_duplicates('edge')['length_m'].sum() / 1000:7.1f} km  {tag}")
    nodes = cars[cars["osm_type"] == "node"]
    inside = nodes[nodes["rule"] == "edge"]
    through = nodes[nodes["rule"] == "through"]
    print(f"barriers and fords that stop a car: {len(found.barriers):,} on drivable "
          "ways, by where they stand:")
    print(f"  {inside['osm_id'].nunique():5,} inside an edge, which closes "
          f"{inside['edge'].nunique():,} edges "
          f"({inside.drop_duplicates('edge')['length_m'].sum() / 1000:.1f} km)")
    print(f"  {through['osm_id'].nunique():5,} where two edges meet, which forbids "
          "driving through")
    for where, ids in left.items():
        print(f"  {len(ids):5,} {LEFT_ALONE[where]}, left alone")
    kinds = Counter(why.split(",")[0] for _, _, why, _ in found.barriers.values())
    print("  by kind: " + ", ".join(f"{k} {n:,}" for k, n in kinds.most_common()))
    shut = cars[cars["rule"] == "edge"].drop_duplicates("edge")
    both = len(set(inside["edge"]) & set(by_way["edge"]))
    print(f"edges closed outright: {len(shut):,} "
          f"({shut['length_m'].sum() / 1000:.1f} km), {both:,} of them by a way "
          "and a barrier both")
    for name, counts in found.record.items():
        if counts:
            print(f"{name}: {sum(counts.values()):,}")
            for key, n in counts.most_common(12):
                print(f"  {n:5,}  {key}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
