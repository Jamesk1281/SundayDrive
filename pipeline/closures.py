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
                              end_month, end_day, length_m, rule, node_id,
                              at_m

which `Router` loads if present, pricing each edge at +inf on the days its
window covers. A row is a closed way's (`rule` "edge", `node_id` -1) or a
gate's closed for the season (`node_id` its OSM id), which is placed as a
barrier closed all year is: `rule` "edge" for one inside an edge, which
closes the edge, and "through" for one where two edges meet, which forbids
only driving through (`join_gates`; docs/safety-quick-fixes.md).

The same pass finds what OSM closes to cars all year. extract.py and graph.py
drop a road only for `access=no|private`, so the graph keeps `motor_vehicle=no`
roads, `access=permit` ones and fords, and every gate, block, chain and bollard
standing on an open road; routes, loops and reroutes drove through them
(docs/closed-roads.md). It writes

  closed_to_cars.parquet      one row per graph edge and what closes it:
                              edge, u, v, rule, kind, osm_type, osm_id, tag,
                              at_m, name, length_m

`rule` is "edge" where the edge is closed both ways, by its way's tags or by a
barrier or ford standing on it, or by MVUM (`kind` says which: way, ford, rough,
barrier, mvum), and "through" where a barrier stands on the
node at which two edges meet end to end: each side stays open up to it and only
driving through is forbidden. `at_m` is a barrier's distance from `u` along the
edge, which `Router.snap` compares with a point's own to keep a driver on their
side of it. `Router` loads it if present and closes those edges and movements
for every request.

And the roads TIGER's import classed as 4WD trails, which count as unpaved
unless OSM's own surface says they are sealed (`tiger_unpaved`):

  osm_unpaved.parquet         one row per graph edge: edge, u, v, way_id, tag,
                              name, length_m

which `Router` loads if present and counts as dirt for `avoid_unpaved`
(docs/safety-quick-fixes.md).

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
    SEASONAL close it in WINTER: Nov 1 - Apr 30, with the spring margin
    WINTER_SPRING_MARGIN_DAYS, so Nov 1 - Jun 14.
Everything else closes nothing here; see `conditional_windows` for which
conditions those are and why. A gate closes for the season by the same car
conditionals, on the node (`gate_windows`).

A way is closed to cars all year when `closed_to_cars` (common.py) says so,
except Rocky Mountain National Park's timed-entry roads (`permit_reopened`), it
is a ford (`ford=yes`) that `ford_closes` closes, which is every ford but one
on a paved major road (docs/review-fixes-data.md), or it is too rough for a car (`too_rough`:
`4wd_only=yes`, or `smoothness` of `very_bad` or worse on an unpaved way), and a node closes the road it stands on when
`barrier_closes` says so for that way. Where that node stands decides what is closed; see
`join_closed_to_cars`. And a forest road closes to cars all year when the
Forest Service's MVUM designates it for no full-size highway-legal vehicle,
unless the OSM edge is major, ref'd as a US or state route, or paved
(`join_no_car`; docs/national-data-decisions.md, D5). Those rows are `kind`
and `osm_type` "mvum".

Usage: python closures.py <input.osm.pbf> <processed_dir> [<out_dir> [<federal_dir>]]
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
                    PASSABLE_BARRIERS, PRIVATE_ACCESS, SEALED, barrier_closes,
                    car_access, closed_to_cars, ford_closes, in_window)

# The keys whose conditional can close a road to a car. `access` binds every
# road user, `vehicle` everything on wheels, `motor_vehicle` everything with an
# engine and `motorcar` cars. Anything narrower restricts someone else's
# vehicle, and the rest of the `*:conditional` family is not access at all. That
# matters on this extract: two New Hampshire ways carry a winter parking ban,
# `parking:both:restriction:conditional = no_stopping @ (Nov 1-Apr 30)`, dated
# exactly like a closure and containing "no".
CAR_KEYS = ("access", "vehicle", "motor_vehicle", "motorcar")

# The winter a tag means when it says winter without saying when, as (start
# month, start day, end month, end day), both ends included.
WINTER_TAGGED = (11, 1, 4, 30)

# How many days longer than WINTER_TAGGED an undated winter tag keeps its road
# closed in spring. On the high passes that carry one, Nov 1 - Apr 30 said
# "open" while the road was still shut in 83% of springs, a median 24 days
# early (docs/seasonal-road-risk-verdict.md, Q2), so its spring end moves to
# Jun 14. Autumn is unchanged. A margin by source, written here, where the
# row is, and never in the router: the windows are the closure version every
# cache keys on (docs/seasonal-road-policy.md).
WINTER_SPRING_MARGIN_DAYS = 45

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
# A whole year, the window a margin can widen one to.
_ALL_YEAR = (1, 1, 12, 31)


def widen(windows, before: int = 0, after: int = 0):
    """`windows` each closed `before` days earlier and `after` days later,
    and merged where they then meet. A margin wide enough to close every day
    closes the whole year.

    Days are counted on `_YEAR_DAYS`, a year with Feb 29 in it, as
    `_complement` counts them.
    """
    n = len(_YEAR_DAYS)
    at = {md: i for i, md in enumerate(_YEAR_DAYS)}
    closed = np.zeros(n, bool)
    for w in windows:
        start, end = at[tuple(w[:2])], at[tuple(w[2:])]
        span = (end - start) % n + 1
        if tuple(w) == _ALL_YEAR or span + before + after >= n:
            return [_ALL_YEAR]
        closed[np.arange(start - before, start + span + after) % n] = True
    if closed.all():
        return [_ALL_YEAR]
    return _runs(list(closed))


def _runs(closed):
    """The closed runs of a mask over `_YEAR_DAYS`, which has an open day, as
    windows. Walked from an open day, so no run is split by the year end."""
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


# The window an undated winter tag closes its road in: WINTER_TAGGED with the
# spring margin, Nov 1 - Jun 14. Read only where a tag says winter without
# dates: `no @ winter` or `no @ snow` on a way or a gate (`_rule_windows`),
# `winter_service=no` and `seasonal` (`way_windows`).
WINTER = widen([WINTER_TAGGED], after=WINTER_SPRING_MARGIN_DAYS)[0]

_MONTH = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
# "Nov", "Nov 1", "Nov-Apr", "Nov 1-Apr 30", "December - May", "Nov 1-15".
_RANGE = re.compile(
    rf"^{_MONTH}(?:\s+(\d{{1,2}}))?"
    rf"(?:\s*-\s*(?:{_MONTH}(?:\s+(\d{{1,2}}))?|(\d{{1,2}})))?$",
    re.IGNORECASE)
# "8 Dec - 1 May", "15 Dec-30 Apr": the same range written day first, both ends.
_RANGE_DAY_FIRST = re.compile(
    rf"^(\d{{1,2}})\s+{_MONTH}(?:\s*-\s*(\d{{1,2}})\s+{_MONTH})?$", re.IGNORECASE)
# An ordinal suffix directly after a one- or two-digit day: "Oct 14th". Only
# there, because `_WEEKDAY` reads a `th` standing alone as Thursday.
_ORDINAL = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b", re.IGNORECASE)
# The one German month name seen on a car conditional whose first three
# letters `_window` cannot map: `no@(Dec 1 - Mai 1)`. As a whole word only, so
# that nothing else beginning "mai" becomes May.
_MAI = re.compile(r"\bmai\b", re.IGNORECASE)
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


def _dates(text: str):
    """One range of dates as (start month, start day, end month, end day), or
    None if it is not one.

    Month first is the form `_RANGE` reads. Three other spellings of it are
    rewritten into that form first, each as narrowly as it was seen
    (docs/safety-quick-fixes.md, "Dates"): an ordinal day (`Oct 14th - May
    31st`, Trail Ridge Road), the German `Mai`, and a range written day first
    at both ends (`8 Dec - 1 May`).
    """
    text = _MAI.sub("May", _ORDINAL.sub(r"\1", text.strip()))
    m = _RANGE_DAY_FIRST.match(text)
    if m:
        text = f"{m.group(2)} {m.group(1)}"
        if m.group(3):
            text += f" - {m.group(4)} {m.group(3)}"
    m = _RANGE.match(text)
    return _window(m) if m else None


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
        window = _dates(part)
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
            window = _dates(" ".join(words))
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
    return _runs(closed)


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
    found = _car_windows(tags)

    def close(window, tag):
        found.setdefault(window, [])
        if tag not in found[window]:
            found[window].append(tag)

    if (tags.get("winter_service") or "").strip().lower() == "no":
        close(WINTER, "winter_service=no")
    seasonal = (tags.get("seasonal") or "").strip().lower()
    if seasonal in SEASONAL:
        close(WINTER, f"seasonal={seasonal}")
    return found


def _car_windows(tags) -> dict:
    """{window: [the car conditionals that close in it]}, through
    `conditional_windows` and every refusal it makes."""
    found = {}
    for key in CAR_KEYS:
        value = tags.get(f"{key}:conditional")
        if value:
            for window in conditional_windows(value)[0]:
                found.setdefault(window, []).append(f"{key}:conditional={value}")
    return found


def gate_windows(tags, way=None) -> dict:
    """{window: [the tags that close it]} for a barrier node that closes the
    road it stands on for part of the year, and empty for any other node.

    A seasonal gate is often tagged on the gate and not on the road behind it
    (docs/us-map-data-findings.md, section 4, cause 4): New England's include
    `no @ (Nov-Apr)`, `no @ winter` and `yes@(Jun-Aug)`. Its car conditionals
    are read exactly as a way's are (`conditional_windows`), refusals and
    all. That matters more here than on ways: most gate conditionals are
    times of day, `no @ (Mo-Fr 17:00-07:00; Sa-Su)` and the like, and read by
    their months alone they would shut a park gate all summer for its
    evenings. `yes @` closes outside its dates, as on a way.

    A conditional only ever adds closed days to a barrier, never removes
    them. A node `barrier_closes` already closes all year gets nothing here,
    so a chain that is `access=private` with `access=permissive @ (winter)`
    stays closed all year; it is closed_to_cars' row, not this table's.
    `way` is the tags of the road the node stands on, as `barrier_closes`
    takes them.
    """
    if not (tags.get("barrier") or "").strip() or barrier_closes(tags, way):
        return {}
    found = _car_windows(tags)
    barrier = tags["barrier"].strip().lower()
    return {w: [f"barrier={barrier}, {t}" for t in found[w]] for w in found}


# Rocky Mountain National Park's timed-entry roads, which `vehicle=permit`
# closed all year: Trail Ridge Road (US 34; 31 ways) and Park Entrance Road
# (US 36; 16 ways), by their ids in Geofabrik's US extract of 2026-10-17. The
# permit is a reservation to enter the park, not a closed road, so these
# stay open, and their winter windows (OSM's own `access:conditional`, and
# the NPS layer's dated description) still close them for the season. A list rather than a
# class rule, because `permit` on the same major classes is also Camp
# Pendleton, Fort Benning, Fort Sill and the Air Force Academy
# (docs/national-data-decisions.md, D1). A way OSM later splits or renumbers
# falls out of the list and closes again, which is the safe side.
PERMIT_REOPENED = frozenset({
    # Trail Ridge Road, US 34
    6147016, 6170582, 6170584, 174615105, 174615106, 301545131, 308279184,
    328388445, 328471511, 328471514, 328885633, 328885645, 329057774, 329057775,
    329057776, 329057777, 329057779, 329058494, 329058497, 329059071, 456529757,
    727646558, 727646559, 834038569, 834038570, 977025414, 977025415, 977025418,
    1105411383, 1105411384, 1409641713,
    # Park Entrance Road, US 36 (Beaver Meadows)
    6165156, 6168904, 328388424, 328388428, 328388429, 328388431, 328388433,
    328388437, 328388438, 328388439, 328388442, 328388443, 328388446, 977025416,
    977025417, 1483799057,
})


def permit_reopened(way_id, tag) -> bool:
    """Whether `closed_to_cars`' `tag` on way `way_id` is a park's entry
    reservation that leaves the road open (PERMIT_REOPENED)."""
    return bool(tag) and tag.endswith("=permit") and way_id in PERMIT_REOPENED


# `smoothness` values at which a road is closed to cars, as fords are: a
# consumer car app should not plan one (decided 2026-10-18; `bad` stays
# open). docs/safety-quick-fixes.md has what they close.
ROUGH_SMOOTHNESS = frozenset({"very_bad", "horrible", "very_horrible", "impassable"})

# The classes a way with no `surface` counts as paved on, for the smoothness
# rule. A track or an unclassified road with no surface is not paved: Shafer
# Trail would reopen (docs/national-data-decisions.md, D2).
PAVED_BY_DEFAULT = frozenset({"motorway", "motorway_link", "trunk", "trunk_link",
                              "primary", "primary_link"})


def paved(tags) -> bool:
    """Whether a way with these tags is paved, for the smoothness rule: its
    `surface` is SEALED, or it has none and its class is PAVED_BY_DEFAULT."""
    surface = (tags.get("surface") or "").strip().lower()
    if surface:
        return surface in SEALED
    return (tags.get("highway") or "").strip().lower() in PAVED_BY_DEFAULT


def too_rough(tags) -> list:
    """The tags that close a way with these tags to cars as too rough for
    one: `4wd_only=yes`, or `smoothness` of `very_bad` or worse on a way that
    is not `paved`. A potholed paved highway is unpleasant, but a car can
    drive it: US 12 by White Pass and Superior Avenue in Cleveland were shut
    by it (decided 2026-10-21; docs/national-data-decisions.md, D2)."""
    found = []
    if (tags.get("4wd_only") or "").strip().lower() == "yes":
        found.append("4wd_only=yes")
    smoothness = (tags.get("smoothness") or "").strip().lower()
    if smoothness in ROUGH_SMOOTHNESS and not paved(tags):
        found.append(f"smoothness={smoothness}")
    return found


# TIGER's census feature class for a vehicular trail, passable only by
# four-wheel drive: A51, A52, A53.
_TIGER_4WD = re.compile(r"^A5\d$", re.IGNORECASE)


def tiger_unpaved(tags):
    """`tiger:cfcc=<value>` when a way with these tags counts as unpaved by
    TIGER's 4WD class, or None.

    Unpaved, not closed (decided 2026-10-18). The class came in with the 2007
    TIGER import and has rarely been reviewed since, and 61.9 of New
    England's 711.6 km of it carry a sealed `surface`: closing it would cut
    real paved roads. So OSM's own sealed surface wins, as it does over a
    state's surface code (`SEALED`). Only a way every one of whose codes is
    A5x counts; a way joined from an A5x and a road of another class is left
    as OSM's surface says.
    """
    value = (tags.get("tiger:cfcc") or "").strip()
    codes = [c.strip() for c in value.split(";") if c.strip()]
    if not codes or not all(_TIGER_4WD.match(c) for c in codes):
        return None
    if (tags.get("surface") or "").strip().lower() in SEALED:
        return None
    return f"tiger:cfcc={value}"


# The values of a car key that are open to a driver with business there, which
# the router leaves open (docs/closed-roads.md), and the other values it knows
# to be open; anything else is open too, and counted as unrecognised.
LOCAL_ACCESS = {"destination", "customers"}
KNOWN_OPEN = {"yes", "permissive", "designated", "discouraged", "unknown"} | LOCAL_ACCESS

# The barrier values that are gates, for counting the ones whose access
# depends on the time of day.
GATES = {"gate", "lift_gate", "swing_gate"}


def scan(pbf_path: str, watch=None):
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
      gates      {node id: (lon, lat, {window: [tags]}, [index into `ways`])}
                 for every node on one that `gate_windows` says closes for
                 the season;
      unpaved    the drivable ways `tiger_unpaved` counts as unpaved;
      sealed     the drivable ways with a SEALED `surface` that pass through
                 a node in `watch`, a set of OSM node ids: the ends of the
                 edges an MVUM road with no car designation would close,
                 which stay open where OSM says they are paved
                 (docs/national-data-decisions.md, D5);
      record     counts of what was found and left alone on purpose, for
                 docs/closed-roads.md and docs/safety-quick-fixes.md.

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
            self.gates = {}
            self.unpaved = []
            self.sealed = []
            self.counted = set()
            self.record = {key: Counter() for key in (
                "dropped but open", "local access", "unrecognised",
                "left open", "timed gates", "barrier car conditionals",
                "tiger:cfcc A5x left paved",
                "fords left open on paved major roads",
                "permits left open, park entry", "rough left open, paved")}

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
            self._unpaved(w, tags)
            if (watch and (tags.get("surface") or "").strip().lower() in SEALED
                    and any(n.ref in watch for n in w.nodes)):
                points = points or _points(w)
                self.sealed.append({"way_id": w.id, "name": tags.get("name", ""),
                                    "refs": [p[0] for p in points],
                                    "coords": [(p[1], p[2]) for p in points]})

        def _unpaved(self, w, tags):
            found = tiger_unpaved(tags)
            cfcc = (tags.get("tiger:cfcc") or "").strip()
            if found is None:
                if "A5" in cfcc.upper():
                    sealed = (tags.get("surface") or "").strip().lower() in SEALED
                    self.record["tiger:cfcc A5x left paved"][
                        f"surface={tags.get('surface')}" if sealed
                        else f"tiger:cfcc={cfcc}"] += 1
                return
            points = _points(w)
            self.unpaved.append({
                "way_id": w.id, "name": tags.get("name", ""), "tag": found,
                "refs": [p[0] for p in points],
                "coords": [(p[1], p[2]) for p in points],
            })

        def _all_year(self, w, tags, points):
            closes = []
            tag = closed_to_cars(tags)
            if permit_reopened(w.id, tag):
                self.record["permits left open, park entry"][
                    f"{tags.get('name', '')} {tags.get('ref', '')}".strip()] += 1
                tag = None
            if tag:
                closes.append(tag)
            if (tags.get("ford") or "").strip().lower() == "yes":
                if ford_closes(tags):
                    closes.append("ford=yes")
                else:
                    self.record["fords left open on paved major roads"][
                        f"way, highway={tags.get('highway')}"] += 1
            rough = too_rough(tags)
            closes += rough
            smoothness = (tags.get("smoothness") or "").strip().lower()
            if smoothness in ROUGH_SMOOTHNESS and paved(tags):
                self.record["rough left open, paved"][
                    f"highway={tags.get('highway')}, surface={tags.get('surface')}"] += 1
            found = car_access(tags)
            if found is not None and found[1] in LOCAL_ACCESS:
                self.record["local access"][f"{found[0]}={found[1]}"] += 1
            elif (found is not None and found[1] not in CLOSED_TO_CARS
                  and found[1] not in KNOWN_OPEN):
                self.record["unrecognised"][f"{found[0]}={found[1]}"] += 1
            stops, seasonal = [], []
            for n in w.nodes:
                hit = self.tagged.get(n.ref)
                if hit is None:
                    continue
                why = barrier_closes(hit[2], tags)
                if why:
                    stops.append((n.ref, hit, why))
                else:
                    if (hit[2].get("ford") or "").strip().lower() == "yes":
                        self.record["fords left open on paved major roads"][
                            f"node, highway={tags.get('highway')}"] += 1
                    windows = gate_windows(hit[2], tags)
                    if windows:
                        seasonal.append((n.ref, hit, windows))
                if n.ref not in self.counted:
                    self.counted.add(n.ref)
                    self._count(hit[2], why, tags)
            if not closes and not stops and not seasonal:
                return
            points = points or _points(w)
            self.ways.append({
                "way_id": w.id,
                "name": tags.get("name", ""),
                "closes": "; ".join(closes),
                # What closes the way itself, when something does.
                "kind": (("way" if tag else "ford" if "ford=yes" in closes
                          else "rough") if closes else ""),
                "refs": [p[0] for p in points],
                "coords": [(p[1], p[2]) for p in points],
            })
            for ref, (lon, lat, _), why in stops:
                self.barriers.setdefault(ref, (lon, lat, why, []))[3].append(
                    len(self.ways) - 1)
            for ref, (lon, lat, _), windows in seasonal:
                self.gates.setdefault(ref, (lon, lat, windows, []))[3].append(
                    len(self.ways) - 1)

        @staticmethod
        def _conditional(tags, why, way):
            """What a barrier's car conditional came to, for the record."""
            if why:
                return "already closed all year, left closed"
            if gate_windows(tags, way):
                return "closed for the season"
            reasons = set()
            for key in CAR_KEYS:
                value = tags.get(f"{key}:conditional")
                if value:
                    reasons |= set(conditional_windows(value)[1])
            return ("closes nothing: " + ", ".join(sorted(reasons)) if reasons
                    else "closes nothing: not `no @` or `yes @` with dates")

        def _count(self, tags, why, way):
            """One tally per node, of the ones left open and the gates whose
            access depends on the time, for the record."""
            barrier = (tags.get("barrier") or "").strip().lower()
            if barrier in GATES and ("opening_hours" in tags or any(
                    f"{key}:conditional" in tags for key in CAR_KEYS)):
                self.record["timed gates"]["closed" if why else "left open"] += 1
            if barrier and any(f"{key}:conditional" in tags for key in CAR_KEYS):
                self.record["barrier car conditionals"][self._conditional(tags, why, way)] += 1
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
                           ways=h.ways, barriers=h.barriers, gates=h.gates,
                           unpaved=h.unpaved, sealed=h.sealed, record=h.record)



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


# seasonal_closures.parquet's columns, in order; see the module docstring.
SEASONAL_COLUMNS = ["edge", "u", "v", "way_id", "name", "ref", "tag",
                    *CLOSURE_WINDOW, "length_m", "rule", "node_id", "at_m"]


def join(closed, edges: gpd.GeoDataFrame) -> pd.DataFrame:
    """The seasonal table's way rows: each closed way's rows in graph_edges,
    one per window, found by `_way_edges`."""
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
                "rule": "edge", "node_id": -1, "at_m": np.nan,
            })
    return _seasonal_table(rows)


def join_gates(ways, gates, edges: gpd.GeoDataFrame):
    """The seasonal table's gate rows, and the gates that close nothing.

    Each gate is placed as a barrier closed all year is (`_place_barriers`),
    with a row per window: inside an edge it closes the edge, and between two
    edges it forbids driving through, for the season. The second is how
    VT-108 is gated at Smugglers' Notch: closing both edges would close the
    open road below the gate too.

    Returns (table, left), `left` holding the gate node ids that close
    nothing, by where they stand.
    """
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    length = edges["length_m"].to_numpy()
    names = (edges["name"].fillna("").to_numpy() if "name" in edges.columns
             else np.full(len(edges), ""))
    placed, left = _place_barriers(
        {nid: (lon, lat, owners) for nid, (lon, lat, _, owners) in gates.items()},
        ways, edges)
    rows = []
    for nid, rule, r, at_m in placed:
        windows, owners = gates[nid][2], gates[nid][3]
        for window, tags in windows.items():
            rows.append({
                "edge": r, "u": int(u[r]), "v": int(v[r]),
                "way_id": ways[owners[0]]["way_id"], "name": names[r], "ref": "",
                "tag": "; ".join(tags), **dict(zip(CLOSURE_WINDOW, window)),
                "length_m": float(length[r]),
                "rule": rule, "node_id": nid, "at_m": at_m,
            })
    return _seasonal_table(rows), left


# The prefixes `tag` carries on the agencies' rows (winter_closures.federal_rows):
# a table window, an unknown season, and the agencies' own dates.
_TABLE_TAGS = ("table ", "nps park")
_UNKNOWN_TAGS = ("nps seasonal, no dates", "mvum seasonal, no readable")
_AGENCY_TAGS = ("mvum", "nps description")
_DATED_IN_TAG = re.compile(rf"@\s*\(?[^)]*\b{_MONTH}", re.IGNORECASE)


def row_source(tag: str, window) -> str:
    """Which source wrote a seasonal row, by its `tag` and window: "table",
    "unknown", "agency_dated", or OSM's "osm_default" (the undated winter,
    WINTER) or "osm_dated" (a conditional with its own dates). The same
    classes as tools/seasonal_risk/windows.py."""
    tag = tag or ""
    if tag.startswith(_TABLE_TAGS):
        return "table"
    if tag.startswith(_UNKNOWN_TAGS):
        return "unknown"
    if tag.startswith(_AGENCY_TAGS):
        return "agency_dated"
    if tuple(int(x) for x in window) == WINTER and not _DATED_IN_TAG.search(tag):
        return "osm_default"
    return "osm_dated"


def seasonal_rows(*parts) -> pd.DataFrame:
    """The seasonal table from its parts (way, gate and agency rows), with
    the undated default giving way to a dated window on its own edge.

    On an edge with any dated window, an OSM-dated conditional, a table row
    or an agency's own dates, the edge's `osm_default` rows are dropped: the
    specific beats the general, as a table road replaces its park's window on
    its own edges (docs/winter-closures-national.md, decision 4). Before
    WINTER's spring margin the default ended Apr 30, before every dated
    window, so it never decided; with the margin it would, and the dated and
    table windows take no margin (docs/seasonal-road-policy.md, "The default
    gives way"). Where an edge has only guesses, the default and
    UNKNOWN_SEASON, every row stands. A gate between two edges ("through")
    gives way as a whole when either of its edges has a dated window: the
    Ross Dam gate at the North Cascades Highway's west end, `no @ winter`
    between the table's last edge and the next, would otherwise hold the
    crossing to Jun 14 against the table's May 15. Its rows only ever go
    together, since the router reads a gate as the two edges it joins.

    Returns (table, the rows that gave way).
    """
    table = _seasonal_table(pd.concat([p for p in parts if len(p)], ignore_index=True)
                            if any(len(p) for p in parts) else parts[0])
    if not len(table):
        return table, table
    source = np.array([row_source(t, w) for t, w in
                       zip(table["tag"], table[list(CLOSURE_WINDOW)].to_numpy())])
    edge_rule = (table["rule"] == "edge").to_numpy()
    dated = np.isin(source, ("osm_dated", "table", "agency_dated")) & edge_rule
    on_dated = table["edge"].isin(table.loc[dated, "edge"]).to_numpy()
    default = source == "osm_default"
    gate = (table["rule"] == "through").to_numpy() & default
    gates = table.loc[gate & on_dated, "node_id"].unique()
    drop = (default & edge_rule & on_dated) | (gate & table["node_id"].isin(gates).to_numpy())
    return table[~drop].reset_index(drop=True), table[drop].reset_index(drop=True)


def _seasonal_table(rows) -> pd.DataFrame:
    """Seasonal rows as the table, sorted, with each row once."""
    table = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(
        rows, columns=SEASONAL_COLUMNS)
    # Two ways can share an edge only where they overlap, which is a mapping
    # error; keep the edge once per window either way. A gate keeps its own
    # rows, since one between two edges closes neither.
    table = (table.drop_duplicates(["edge", "rule", "node_id", *CLOSURE_WINDOW])
             .sort_values(["edge", *CLOSURE_WINDOW, "rule", "node_id"])
             .reset_index(drop=True))
    for col in CLOSURE_WINDOW:
        table[col] = table[col].astype("int8")
    return table.astype({"edge": "int64", "u": "int64", "v": "int64",
                         "way_id": "int64", "node_id": "int64",
                         "at_m": "float64", "length_m": "float64"})


def _place_barriers(barriers, ways, edges: gpd.GeoDataFrame):
    """Where each barrier stands in the graph, which decides what it closes
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

    `barriers` is {node id: (lon, lat, [index into `ways`])}. Returns
    (placed, left): `placed` a list of (node id, "edge" or "through", edge
    row, at_m), and `left` the node ids that close nothing, by where they
    stand.
    """
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    length = edges["length_m"].to_numpy()
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
                                        for b in inside for i in b[2]]))
              if inside else np.empty(0, np.int64))
    candidates = np.flatnonzero(np.isin(u, wanted) & np.isin(v, wanted))
    geoms = edges.geometry.iloc[candidates].to_crs(CRS_METERS).values
    by_u = {}
    for i, r in enumerate(candidates):
        by_u.setdefault(int(u[r]), []).append(i)

    placed = []
    left = {"dead end": [], "junction": [], "not in the graph": []}
    for nid in sorted(barriers):
        lon, lat, owners = barriers[nid]
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
                placed.append((nid, "edge", int(candidates[i]),
                               float(geoms[i].project(point))))
        elif degree[nid] == 2 and len(on_node.get(nid, ())) == 2:
            for r in on_node[nid]:
                placed.append((nid, "through", r,
                               0.0 if int(u[r]) == nid else float(length[r])))
        elif degree[nid] == 1:
            left["dead end"].append(nid)
        else:
            left["junction"].append(nid)
    return placed, left


# closed_to_cars.parquet's columns, in order; see the module docstring.
CLOSED_TO_CARS_COLUMNS = ["edge", "u", "v", "rule", "kind", "osm_type", "osm_id",
                          "tag", "at_m", "name", "length_m"]


def join_closed_to_cars(ways, barriers, edges: gpd.GeoDataFrame):
    """The all-year table, and the closing barriers it leaves alone.

    A way closes its edges, found as a seasonal way's are (`_way_edges`). A
    barrier closes by where it stands (`_place_barriers`).

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
    placed, left = _place_barriers(
        {nid: (lon, lat, owners) for nid, (lon, lat, _, owners) in barriers.items()},
        ways, edges)
    for nid, rule, r, at_m in placed:
        why = barriers[nid][2]
        rows.append(row(r, rule, "ford" if why == "ford=yes" else "barrier",
                        "node", nid, why, at_m))

    table = pd.DataFrame(rows, columns=CLOSED_TO_CARS_COLUMNS)
    # An edge two closed ways overlap on, or a barrier listed by two ways,
    # once each.
    table = (table.drop_duplicates(["edge", "rule", "osm_type", "osm_id"])
             .sort_values(["edge", "rule", "at_m", "osm_id"]).reset_index(drop=True))
    table = table.astype({"edge": "int64", "u": "int64", "v": "int64",
                          "osm_id": "int64", "at_m": "float64",
                          "length_m": "float64"})
    return table, left


# osm_unpaved.parquet's columns, in order; see the module docstring.
UNPAVED_COLUMNS = ["edge", "u", "v", "way_id", "tag", "name", "length_m"]


def join_unpaved(unpaved, edges: gpd.GeoDataFrame) -> pd.DataFrame:
    """The unpaved table: each way `tiger_unpaved` counts, as its rows in
    graph_edges (`_way_edges`)."""
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    length = edges["length_m"].to_numpy()
    rows = [{"edge": r, "u": int(u[r]), "v": int(v[r]), "way_id": way["way_id"],
             "tag": way["tag"], "name": way["name"], "length_m": float(length[r])}
            for way, r in _way_edges(unpaved, edges)]
    table = pd.DataFrame(rows, columns=UNPAVED_COLUMNS)
    table = table.drop_duplicates("edge").sort_values("edge").reset_index(drop=True)
    return table.astype({"edge": "int64", "u": "int64", "v": "int64",
                         "way_id": "int64", "length_m": "float64"})


def _window_label(window):
    sm, sd, em, ed = window
    return f"{_MONTHS[sm - 1].title()} {sd} - {_MONTHS[em - 1].title()} {ed}"


# Where federal_layers.py writes the agencies' road layers by default.
FEDERAL_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "federal"


def federal_dir_for(pbf_path: str, given: str = None) -> Path:
    """Where to read the agencies' layers: `given`, else $SUNDAYDRIVE_FEDERAL,
    else `federal/` beside the PBF (data/raw/federal for data/raw's
    extracts, which also serves a worktree whose data/ is elsewhere), else
    FEDERAL_DIR."""
    import os
    if given:
        return Path(given)
    if os.environ.get("SUNDAYDRIVE_FEDERAL"):
        return Path(os.environ["SUNDAYDRIVE_FEDERAL"])
    beside = Path(pbf_path).resolve().parent / "federal"
    return beside if beside.exists() else FEDERAL_DIR


def join_federal(edges: gpd.GeoDataFrame, federal_dir=None):
    """The seasonal rows from the agencies that run the roads, and the table
    of windows for the high passes and parks (winter_closures.py), and the
    MVUM roads with no car designation: (seasonal table, (candidates, MVUM
    frame)), the candidates as `winter_closures.no_car_edges` gives them.

    Reads mvum_roads.parquet and nps_roads.parquet from `federal_dir`
    (FEDERAL_DIR unless given; `main` passes `federal_dir_for`). A missing
    file is said loudly, never silently: without them a national build
    closes only what OSM tags, which leaves Yellowstone, Teton Park Road and
    809 of 813 km of one Colorado forest's seasonal roads open
    (docs/winter-closures-national.md).
    """
    from winter_closures import federal_rows

    t0 = time.time()
    d = Path(federal_dir or FEDERAL_DIR)
    frames = {}
    for name in ("mvum_roads", "nps_roads"):
        path = d / f"{name}.parquet"
        if path.exists():
            frames[name] = gpd.read_parquet(path)
        else:
            frames[name] = None
            print(f"WARNING: {path} is missing, so no {name.split('_')[0].upper()} "
                  "closures: run pipeline/federal_layers.py first", flush=True)
    rows, report = federal_rows(edges, frames["mvum_roads"], frames["nps_roads"])
    print(f"agencies' layers joined in {time.time() - t0:.0f}s", flush=True)
    for source in ("mvum", "nps"):
        if report[source] is not None:
            n, km = report[source]
            print(f"{source.upper()} closes {n:,} edges ({km:.1f} km) for part of the year")
    for kind, label in (("roads", "table road"), ("exceptions", "kept open")):
        placed = {k: r for k, r in report[kind].items() if r[1] is None}
        print(f"{label}s: {len(placed)} of {len(report[kind])} in this graph")
        for key, (km, why) in sorted(report[kind].items()):
            print(f"  {key:28s} {km:7.1f} km" if why is None
                  else f"  {key:28s} not placed: {why}")
    # Closes nothing: unknown seasons a step off a table road, for a person
    # to judge (winter_closures.unknown_beside).
    beside = report.get("unknown_beside_table", [])
    print(f"unknown seasons beside a table road: {len(beside)}")
    for hit in beside:
        print(f"  {hit['road']:28s} edge {hit['edge']} {hit['name'] or '(no name)'} "
              f"{hit['km'] * 1000:.0f} m: {hit['tag']}")
    return (_seasonal_table(pd.DataFrame(rows, columns=SEASONAL_COLUMNS)),
            (report["no_car"], frames["mvum_roads"]))


def join_no_car(candidates, mvum, sealed, edges: gpd.GeoDataFrame):
    """closed_to_cars rows for the MVUM roads with no full-size highway-legal
    designation, and the edges left open, with why.

    A candidate stays open when its class or ref says so (its `exception`)
    or when a way with a SEALED surface runs along it (`sealed`, from the
    scan, matched as `_way_edges` matches). Either is a sign the 15 m match
    picked up a different road. Rows are `kind` and `osm_type` "mvum", with
    the MVUM layer's objectid as `osm_id` (docs/national-data-decisions.md, D5).
    """
    paved = {r for _, r in _way_edges(sealed, edges)} if sealed else set()
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    length = edges["length_m"].to_numpy()
    names = (edges["name"].fillna("").to_numpy() if "name" in edges.columns
             else np.full(len(edges), ""))
    rows, kept = [], []
    for c in candidates:
        r = c["edge"]
        m = mvum.iloc[c["line"]]
        why = c["exception"] or ("surface sealed in OSM" if r in paved else "")
        tag = (f"mvum no car designation ({m.get('forestname') or ''}, "
               f"MVUM id {m.get('id') or ''})")
        if why:
            kept.append({"edge": r, "why": why, "tag": tag, "name": names[r],
                         "length_m": float(length[r])})
            continue
        rows.append({"edge": r, "u": int(u[r]), "v": int(v[r]), "rule": "edge",
                     "kind": "mvum", "osm_type": "mvum", "osm_id": int(m["objectid"]),
                     "tag": tag, "at_m": np.nan, "name": names[r],
                     "length_m": float(length[r])})
    return (pd.DataFrame(rows, columns=CLOSED_TO_CARS_COLUMNS),
            pd.DataFrame(kept, columns=["edge", "why", "tag", "name", "length_m"]))


def main(pbf_path: str, processed_dir: str, out_dir: str = None,
         federal_dir: str = None):
    """Read processed_dir's graph, and write both tables into `out_dir`
    (processed_dir unless given, which is how to try a rule change without
    touching the tables a deploy ships). The agencies' layers come from
    `federal_dir_for`."""
    d = Path(processed_dir)
    out = Path(out_dir or processed_dir)
    t0 = time.time()

    import pyarrow.parquet as pq
    columns = ["u", "v", "length_m", "score", "name", "geometry"]
    names = pq.ParquetFile(d / "graph_edges.parquet").schema_arrow.names
    columns += [c for c in ("unpaved_frac", "highway", "ref") if c in names]
    edges = gpd.read_parquet(d / "graph_edges.parquet", columns=columns)
    # The agencies' layers first, so the scan can look for paved OSM ways
    # along the edges MVUM would close to cars.
    by_agency, (no_car, mvum) = join_federal(edges, federal_dir_for(pbf_path, federal_dir))
    watch = {int(x) for c in no_car if not c["exception"]
             for x in (edges["u"].iat[c["edge"]], edges["v"].iat[c["edge"]])}
    found = scan(pbf_path, watch)
    drivable, closed, skipped = found.drivable, found.closed, found.skipped
    print(f"scanned in {time.time() - t0:.0f}s: {drivable:,} drivable ways, "
          f"{len(closed):,} of them closed for part of the year")
    roads = d / "roads.parquet"
    if roads.exists():
        import pyarrow.parquet as pq
        control = pq.ParquetFile(roads).metadata.num_rows
        verdict = "matches" if control == drivable else "DOES NOT MATCH"
        print(f"control: roads.parquet has {control:,} ways, which {verdict} the scan")

    by_way = join(closed, edges)
    by_gate, gates_left = join_gates(found.ways, found.gates, edges)
    table, dropped = seasonal_rows(by_way, by_gate, by_agency)
    table.to_parquet(out / "seasonal_closures.parquet", index=False)
    print(f"undated winter giving way to a dated window on its edge: {len(dropped):,} rows, "
          f"{dropped['edge'].nunique():,} edges, "
          f"{dropped.drop_duplicates('edge')['length_m'].sum() / 1000:.1f} km")

    unique = by_way.drop_duplicates("edge")
    km = unique["length_m"].sum() / 1000.0
    score = edges["score"].to_numpy()[unique["edge"].to_numpy()]
    lengths = unique["length_m"].to_numpy()
    if lengths.sum() > 0:
        print(f"in the graph: {by_way['way_id'].nunique():,} ways, {len(unique):,} edges, "
              f"{km:.1f} km; length-weighted score {np.average(score, weights=lengths):.2f}, "
              f"{lengths[score >= 7.0].sum() / lengths.sum():.1%} of km at 7 or more")
    else:
        # A region with no seasonally tagged way (Rhode Island, as a national
        # build's region) has nothing to average; docs/national-build.md §8.
        print("in the graph: no seasonally closed ways")
    absent = len(closed) - by_way["way_id"].nunique()
    print(f"not in the graph: {absent:,} closed ways have no edge in it "
          "(outside the largest component, or under 1 m)")
    for window, group in by_way.groupby(list(CLOSURE_WINDOW)):
        print(f"  closed {_window_label(window):>17}: {group['way_id'].nunique():4,} ways, "
              f"{group.drop_duplicates('edge')['length_m'].sum() / 1000:6.1f} km")
    _report_gates(found.gates, by_gate, gates_left)
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
    by_mvum, kept = (join_no_car(no_car, mvum, found.sealed, edges) if no_car
                     else (pd.DataFrame(columns=CLOSED_TO_CARS_COLUMNS), None))
    if len(by_mvum):
        cars = (pd.concat([cars, by_mvum.astype(cars.dtypes.to_dict())], ignore_index=True)
                .sort_values(["edge", "rule", "at_m", "osm_id"]).reset_index(drop=True))
    cars.to_parquet(out / "closed_to_cars.parquet", index=False)
    _report(found, cars, left)
    _report_no_car(by_mvum, kept)
    print(f"wrote closed_to_cars.parquet ({len(cars):,} rows) "
          f"in {time.time() - t0:.0f}s")

    unpaved = join_unpaved(found.unpaved, edges)
    unpaved.to_parquet(out / "osm_unpaved.parquet", index=False)
    km = unpaved["length_m"].sum() / 1000.0
    already = ""
    if "unpaved_frac" in edges.columns:
        dirt = (edges["unpaved_frac"].to_numpy()[unpaved["edge"].to_numpy()]
                * unpaved["length_m"].to_numpy()).sum() / 1000.0
        already = f"; {dirt:.1f} km of it already unpaved by its surface"
    print(f"unpaved by TIGER's 4WD class: {unpaved['way_id'].nunique():,} ways in the "
          f"graph ({len(unpaved):,} edges, {km:.1f} km) of {len(found.unpaved):,} "
          f"in the PBF{already}")
    print(f"wrote osm_unpaved.parquet ({len(unpaved):,} rows) "
          f"in {time.time() - t0:.0f}s")


LEFT_ALONE = {"dead end": "at a dead end",
              "junction": "where three or more edges meet",
              "not in the graph": "on no edge of the graph"}


def _report_gates(gates, table, left):
    """What the seasonal gates close: docs/safety-quick-fixes.md's counts."""
    inside = table[table["rule"] == "edge"]
    through = table[table["rule"] == "through"]
    print(f"gates closed for the season: {len(gates):,} on drivable ways, by where "
          "they stand:")
    print(f"  {inside['node_id'].nunique():5,} inside an edge, which closes "
          f"{inside['edge'].nunique():,} edges "
          f"({inside.drop_duplicates('edge')['length_m'].sum() / 1000:.1f} km) in season")
    print(f"  {through['node_id'].nunique():5,} where two edges meet, which forbids "
          "driving through in season")
    for where, ids in left.items():
        print(f"  {len(ids):5,} {LEFT_ALONE[where]}, left alone")
    for window, group in table.groupby(list(CLOSURE_WINDOW)):
        print(f"  closed {_window_label(window):>17}: {group['node_id'].nunique():4,} gates")


def _report_no_car(rows, kept):
    """What the MVUM no-car rule closes and leaves open: D5's counts."""
    shut = rows.drop_duplicates("edge")
    print(f"closed to cars by MVUM, no full-size highway-legal designation: "
          f"{len(shut):,} edges ({shut['length_m'].sum() / 1000:.1f} km)")
    if kept is not None and len(kept):
        print(f"  left open as a different road: {kept['edge'].nunique():,} edges "
              f"({kept.drop_duplicates('edge')['length_m'].sum() / 1000:.1f} km)")
        for why, group in kept.groupby(kept["why"].str.split("=").str[0]):
            print(f"    {why:24s} {len(group):5,} edges "
                  f"{group['length_m'].sum() / 1000:7.1f} km")


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
    main(*sys.argv[1:5])
