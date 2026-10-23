"""Each seasonal edge's window, where it came from, and the policies as tables.

A seasonal_closures row carries one window and a `tag` that says which source
wrote it. An edge can carry several rows, and the router closes it on any day
any of them closes it (`SeasonalClosures`), so what the router does is the
union. This module reads the table into:

  source(tag)        which of the window sources wrote a row;
  closed_mask(...)   a 366-day closed mask, per row or per edge;
  policy_table(...)  a modified copy of the table for a policy (ban, margins),
                     handed to harness.set_table; never written under data/.

The sources, from pipeline/closures.py and pipeline/winter_closures.py (read
only):

  osm_dated     an OSM *:conditional with dates, used as tagged
  osm_default   an undated OSM winter/snow, winter_service=no or seasonal=*,
                given WINTER = Nov 1 - Apr 30
  unknown       UNKNOWN_SEASON = Oct 1 - Jun 30: MVUM `seasonal` with no
                readable dates, or NPS SEASONAL=Yes in a park the table lacks
  table         winter_windows.json: a road's window (the ten-season longest
                rule), or a park's window applied to its NPS segments
  agency_dated  dates the agency itself publishes per segment: MVUM
                passengervehicle_datesopen, an NPS SEASDESC the table maps
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

COLS = ["start_month", "start_day", "end_month", "end_day"]
SOURCES = ["osm_dated", "osm_default", "unknown", "table", "agency_dated"]
UNKNOWN_SEASON = (10, 1, 6, 30)
WINTER = (11, 1, 4, 30)
# WINTER as closures.py writes it since docs/seasonal-road-policy.md: with its
# 45-day spring margin. Either is the undated default.
WINTER_WIDENED = (11, 1, 6, 14)
YEAR = 2026                      # a non-leap year: day-of-year 0..364
DAYS = 365


def source(tag: str, window) -> str:
    tag = tag or ""
    w = tuple(int(x) for x in window)
    if tag.startswith("table "):
        return "table"
    if tag.startswith("nps park"):
        # `nps_windows`: a park's window from the table's _parks.
        return "table"
    if tag.startswith("nps seasonal, no dates") or tag.startswith("mvum seasonal, no readable"):
        return "unknown"
    if tag.startswith("mvum") or tag.startswith("nps description"):
        return "agency_dated"
    # OSM. A conditional with dates is dated; the WINTER default is what an
    # undated winter/snow conditional, winter_service=no or seasonal=* get.
    if w in (WINTER, WINTER_WIDENED) and not _has_dates(tag):
        return "osm_default"
    return "osm_dated"


def _has_dates(tag: str) -> bool:
    import re
    months = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    return bool(re.search(r"@\s*\(?[^)]*" + months, tag, re.I))


def doy(month: int, day: int) -> int:
    day = min(day, 28) if month == 2 and day == 29 else day
    return (date(YEAR, month, day) - date(YEAR, 1, 1)).days


def day_of(i: int) -> date:
    return date(YEAR, 1, 1) + timedelta(days=int(i) % DAYS)


def window_mask(window, before: int = 0, after: int = 0) -> np.ndarray:
    """Closed days of `window` (both ends closed, wrapping the new year),
    widened `before` days ahead of its start and `after` days past its end."""
    sm, sd, em, ed = (int(x) for x in window)
    if (sm, sd, em, ed) == (1, 1, 12, 31):
        return np.ones(DAYS, bool)
    s, e = doy(sm, sd) - before, doy(em, ed) + after
    m = np.zeros(DAYS, bool)
    if e - s + 1 >= DAYS:
        return np.ones(DAYS, bool)
    idx = np.arange(s, e + 1) % DAYS if s <= e else \
        np.r_[np.arange(s, DAYS + e + 1)] % DAYS
    m[idx] = True
    return m


def annotate(table: pd.DataFrame) -> pd.DataFrame:
    t = table.copy()
    if "rule" not in t.columns:
        t["rule"] = "edge"
    t["source"] = [source(tag, w) for tag, w in zip(t["tag"], t[COLS].to_numpy())]
    return t


def edge_masks(t: pd.DataFrame, margins: dict | None = None) -> dict:
    """{edge: closed mask} under per-source margins {source: (before, after)}.
    Gates ("through" rows) count against both their edges."""
    out = {}
    margins = margins or {}
    for e, w, src in zip(t["edge"].to_numpy(), t[COLS].to_numpy(), t["source"]):
        b, a = margins.get(src, (0, 0))
        m = window_mask(w, b, a)
        prev = out.get(int(e))
        out[int(e)] = m if prev is None else (prev | m)
    return out


def policy_table(t: pd.DataFrame, ban: bool = False, margins: dict | None = None) -> pd.DataFrame:
    """A copy of the table that closes what the policy closes, in the
    router's own (start, end) form. A margin moves each row's start earlier
    and its end later; a window widened past a whole year becomes all year."""
    out = t.copy()
    if ban:
        out[COLS] = (1, 1, 12, 31)
        return out[[c for c in t.columns if c != "source"]]
    margins = margins or {}
    rows = []
    for w, src in zip(t[COLS].to_numpy(), t["source"]):
        b, a = margins.get(src, (0, 0))
        sm, sd, em, ed = (int(x) for x in w)
        if (sm, sd, em, ed) == (1, 1, 12, 31) or (b == 0 and a == 0):
            rows.append((sm, sd, em, ed))
            continue
        s, e = doy(sm, sd), doy(em, ed)
        span = (e - s) % DAYS + 1
        if span + b + a >= DAYS:
            rows.append((1, 1, 12, 31))
            continue
        s0, e0 = day_of(s - b), day_of(e + a)
        rows.append((s0.month, s0.day, e0.month, e0.day))
    out[COLS] = np.array(rows, dtype=np.int8)
    return out[[c for c in t.columns if c != "source"]]
