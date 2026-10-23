"""Winter closures OpenStreetMap leaves out, from the agencies that run the roads.

closures.py reads OSM's own tags, and most park and forest roads that close for
winter carry none. Teton Park Road, Glacier Point Road, Yellowstone's Grand
Loop, Kuwohi Road and Crater Lake's Rim Drive are untagged or free text. MVUM
marks 821 km of one Colorado forest's graph road seasonal, and OSM tags 1.6 km
of it. And the generic winter, Nov 1 - Apr 30, leaves high passes routed open
for weeks of real closure (docs/us-map-data-findings.md, §4 and §6.4). This
adds three sources, each as seasonal_closures rows in closures.py's format:

  mvum    the Forest Service's Motor Vehicle Use Map: each road's dates open
          to passenger vehicles, `passengervehicle_datesopen`, closed outside
          them (`mvum_windows`);
  nps     NPS Public Roads: segments marked SEASONAL, with dates where the
          description gives them (`nps_windows`), else the park's window;
  table   winter_windows.json: a window for each high pass and park road in
          §4, and for the parks, each with its operator's source and the
          date it was read.

**Joined by geometry, never by name** (`match_lines`). Clingmans Dome Road
became Kuwohi Road in 2024, and a name join finds nothing. A table road is
the graph's shortest path through waypoints along it (`path_edges`).

**Uncertain resolves toward closed.** A seasonal road with no readable dates
gets UNKNOWN_SEASON. A prose date is read at its longer end. A table window is
the longest the operator has published in its last ten seasons, or, with no
record, the longer ends of its stated range. Rows from every source are kept
side by side, so an edge is closed whenever any of them closes it. The one
exception is precedence among the table's own windows: a road's window
replaces its park's on the edges they share, because it is the more specific
of two sourced statements (`federal_rows`).

**The guesses get a margin.** UNKNOWN_SEASON and the agencies' own dates close
7 days longer at each end as their rows are written (UNKNOWN_MARGIN_DAYS,
AGENCY_MARGIN_DAYS); the table's windows take none (docs/seasonal-road-policy.md).

docs/winter-closures-national.md has the decisions, the sources and what each
one closes.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import shapely

TABLE = Path(__file__).with_name("winter_windows.json")

# The matcher: walk each edge in SAMPLE_M steps and give each step the nearest
# federal line within TOLERANCE_M, as tools/us_map_data/osm_match.py does (25 m
# and 15 m, the tolerance for forest roads digitised more loosely than state
# highways). A step counts only where the two run the same way, within
# ALIGN_DEG, so a road crossing a closed one, or ending at it, does not pick
# up its closure.
SAMPLE_M = 25.0
TOLERANCE_M = 15.0
ALIGN_DEG = 30.0
# How much of an edge must lie along seasonal lines for the edge to close.
# Half, so an edge closes when it is mostly the closed road. See "The join" in
# docs/winter-closures-national.md for what lower shares would add.
MIN_SHARE = 0.5
# A line that covers less of an edge than this contributes no window to it.
WINDOW_SHARE = 0.2
# Metres anywhere in the lower 48, for the matcher; graph.py's CRS_METERS is
# Massachusetts' state plane.
CRS_M = 5070
# How far a table waypoint may sit from the nearest graph node.
SNAP_M = 150.0

# The season of a road known to close for one but with no dates anyone
# publishes: an MVUM road marked `seasonal` with no readable passenger dates,
# or an NPS road marked seasonal in a park the table has no window for. Oct 1
# to Jun 30 contains the closed window of every dated NPS winter description
# in the 48 states, and 95.7% of the closed days of MVUM's dated seasonal
# roads, weighted by miles (docs/winter-closures-national.md, "Unknown
# seasons").
UNKNOWN_SEASON = (10, 1, 6, 30)

# Days each source's windows are widened by, (before its start, after its
# end), as their rows are written (`federal_rows`). The two that guess or
# report without a record behind them close 7 days longer at each end:
# UNKNOWN_SEASON, and the dates MVUM and NPS descriptions give, which no
# published actual date was found to check (docs/seasonal-road-risk-verdict.md,
# "Recommended policy"). The table's own windows take none: the longest of ten
# seasons already stays shut a median 20-30 days after the road opens, and a
# margin on top would count that bias twice. docs/seasonal-road-policy.md.
UNKNOWN_MARGIN_DAYS = (7, 7)
AGENCY_MARGIN_DAYS = (7, 7)

# A whole year, for a road its agency says is closed to cars all year.
ALL_YEAR = (1, 1, 12, 31)

_MD = re.compile(r"(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})")
_LAST_DAY = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def load_table(path: Path = TABLE) -> dict:
    """winter_windows.json, its windows as tuples."""
    table = json.loads(Path(path).read_text())
    for entry in table["roads"] + table["parks"]:
        entry["window"] = tuple(entry["window"]) if entry["window"] else None
    for entry in table["nps_descriptions"]:
        entry["windows"] = [tuple(w) for w in entry["windows"]]
    return table


# ------------------------------------------------------------------- MVUM

def mvum_open_ranges(text):
    """The ranges in an MVUM `*_datesopen` value, as (start month, start day,
    end month, end day), or None if it holds anything else or a day that does
    not exist. `01/01-10/11    10/22-12/31` is two ranges: closed for a
    hunting season in between."""
    text = (text or "").strip()
    if not text:
        return None
    ranges = []
    for m in _MD.finditer(text):
        m1, d1, m2, d2 = map(int, m.groups())
        if not (1 <= m1 <= 12 and 1 <= m2 <= 12 and 1 <= d1 <= _LAST_DAY[m1 - 1]
                and 1 <= d2 <= _LAST_DAY[m2 - 1]):
            return None
        ranges.append((m1, d1, m2, d2))
    if not ranges or _MD.sub("", text).strip(" ,;&"):
        return None
    return ranges


def mvum_windows(row):
    """(windows closed to a passenger car, how they were found) for one MVUM
    road, a mapping with the layer's field names.

    The passenger-vehicle dates are the specific field, so they decide:
    closed outside them, and open all year when they say `01/01-12/31`, even
    on a road marked `seasonal` for other vehicles. A road with no passenger
    designation is read by its high-clearance dates, since a car's season is
    no longer than a high-clearance vehicle's. A road marked `seasonal` with
    neither readable gets UNKNOWN_SEASON.
    """
    from closures import _complement

    def flag(key):
        return (row.get(key) or "").strip().lower()

    for vehicle in ("passengervehicle", "highclearancevehicle"):
        if flag(vehicle) != "open":
            continue
        ranges = mvum_open_ranges(row.get(f"{vehicle}_datesopen"))
        if ranges is not None:
            return _complement(ranges), f"{vehicle}_datesopen"
    if flag("seasonal") == "seasonal":
        return [UNKNOWN_SEASON], "seasonal, no readable dates"
    return [], "no dates"


# The MVUM vehicle classes that are full-size and highway legal: a car, an
# SUV or light truck, a truck over 10,000 lb, a bus and a motorhome, each
# "licensed to operate on public roads" in the layer's own metadata. Under
# the Travel Management Rule (36 CFR 212.51) a Forest Service road may be
# driven only by the classes its MVUM designates, so a road designated for
# none of these is not a road for a car: ATV, motorcycle, OHV or 4WD only.
# Four-wheel drive over 50 inches is not one, as `4wd_only=yes` closes a
# road; nor is two-wheel drive over 50 inches, which the metadata does not
# call highway legal (docs/national-data-decisions.md, D5).
MVUM_CAR_CLASSES = ("passengervehicle", "highclearancevehicle", "truck", "bus",
                    "motorhome")

# MVUM's symbols for a road open to every vehicle or to highway-legal
# vehicles, yearlong or seasonal: the map's own legend designates a car on
# these whatever the class fields hold, and some forests fill only the
# symbol. 11 and 12 are "special designation", where the classes decide.
MVUM_CAR_SYMBOLS = frozenset({"1", "2", "3", "4"})


def mvum_car_designated(row) -> bool:
    """Whether one MVUM road is designated for a full-size highway-legal
    vehicle: its symbol says so (MVUM_CAR_SYMBOLS) or one of
    MVUM_CAR_CLASSES is `open`."""
    if (row.get("symbol") or "").strip() in MVUM_CAR_SYMBOLS:
        return True
    return any((row.get(c) or "").strip().lower() == "open" for c in MVUM_CAR_CLASSES)


# The classes on which an MVUM road with no car designation is taken for a
# different road the 15 m match picked up, and left open, as is an edge with
# a US or state ref or a paved one (`no_car_exception`).
MAJOR_CLASSES = frozenset({"motorway", "motorway_link", "trunk", "trunk_link",
                           "primary", "primary_link"})

_STATES = ("AL AZ AR CA CO CT DE DC FL GA ID IL IN IA KS KY LA ME MD MA MI MN MS MO "
           "MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY")
# A ref naming an interstate, a US route or a state route: "I 70", "US 34",
# "CO 14", "SR 410", "State Highway 310". "FR 602C", "CR 142" and "NF 37"
# are not, and no state's postal code is FR, FS, NF or CR.
STATE_REF = re.compile(rf"^(?:I|US|SR|SH|STATE(?: (?:ROUTE|HIGHWAY|ROAD))?|"
                       rf"{'|'.join(_STATES.split())})[ -]?\d", re.IGNORECASE)


def state_ref(ref) -> bool:
    """Whether any part of a `;`-separated ref is an interstate, US or state
    route (STATE_REF)."""
    return any(STATE_REF.match(part.strip()) for part in (ref or "").split(";"))


def no_car_exception(highway, ref) -> str:
    """Why an edge an MVUM road with no car designation runs along stays
    open, by its own class and ref, or "" when it closes."""
    highway = (highway or "").strip().lower()
    if highway in MAJOR_CLASSES:
        return f"highway={highway}"
    if state_ref(ref):
        return f"ref={ref}"
    return ""


# -------------------------------------------------------------------- NPS

def _norm(text) -> str:
    return " ".join((text or "").split()).rstrip(".").strip().lower()


def nps_windows(row, table):
    """(windows, how) for one NPS Public Roads segment, a mapping with the
    layer's field names, and the window table.

    A description the table maps (`nps_descriptions`, every one seen in the
    48 states) closes in its windows, or closes nothing when the table says
    it is not a closure. Any other segment marked SEASONAL=Yes takes its
    park's window, or UNKNOWN_SEASON where the park is not in the table. A
    park in the table that `applies` to nothing is one that does not close
    for winter, Golden Gate: its flag closes nothing. A park in the
    table with `applies` naming other SEASONAL values takes those segments
    too: Yellowstone is Unknown on 1,979 of its 2,007.
    """
    seasonal = (row.get("SEASONAL") or "").strip()
    unit = (row.get("UNITCODE") or "").strip()
    desc = _norm(row.get("SEASDESC"))
    park = table["_parks"].get(unit)
    if seasonal == "Yes" and desc:
        entry = table["_descriptions"].get(desc)
        if entry is not None and entry["closes"] == "dates":
            return entry["windows"], "description"
        if entry is not None and entry["closes"] == "no":
            return [], "not a closure"
    if park is not None and seasonal in park["applies"]:
        return [park["window"]], f"park {unit}"
    if park is not None and seasonal == "Yes":
        return [], f"park {unit} does not close for the season"
    if seasonal == "Yes":
        return [UNKNOWN_SEASON], "seasonal, no dates"
    return [], "not seasonal"


# ---------------------------------------------------------------- the join

def _bearings(lines, at):
    """The direction of each line at distance `at` along it, as unit vectors."""
    lo = shapely.line_interpolate_point(lines, np.maximum(at - 2.0, 0.0))
    hi = shapely.line_interpolate_point(lines, np.minimum(at + 2.0, shapely.length(lines)))
    d = shapely.get_coordinates(hi) - shapely.get_coordinates(lo)
    n = np.hypot(d[:, 0], d[:, 1])
    n[n == 0] = 1.0
    return d / n[:, None]


def match_lines(edge_geoms, lines):
    """Which lines each edge runs along, by geometry.

    `edge_geoms` and `lines` are GeoSeries in WGS84. Returns a DataFrame of
    (edge, line, share): `edge` a position in `edge_geoms`, `line` one in
    `lines`, and `share` the fraction of the edge's SAMPLE_M steps whose
    nearest line within TOLERANCE_M is that one and runs within ALIGN_DEG of
    the edge there.
    """
    empty = pd.DataFrame({"edge": np.empty(0, np.int64), "line": np.empty(0, np.int64),
                          "share": np.empty(0)})
    if len(edge_geoms) == 0 or len(lines) == 0:
        return empty
    # Candidates in degrees first, generously (15 m is under 0.0002 degrees
    # of longitude at 49 N), so only edges near a line are projected.
    tree = shapely.STRtree(lines.values)
    pairs = tree.query(edge_geoms.values, predicate="dwithin", distance=0.0004)
    cand = np.unique(pairs[0])
    if len(cand) == 0:
        return empty
    near = np.unique(pairs[1])
    edges_m = edge_geoms.iloc[cand].to_crs(CRS_M).values
    lines_m = lines.iloc[near].to_crs(CRS_M).values

    length = shapely.length(edges_m)
    n = np.maximum(1, np.round(length / SAMPLE_M).astype(np.int64))
    owner = np.repeat(np.arange(len(cand)), n)
    k = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
    at = (k + 0.5) * (length[owner] / n[owner])
    points = shapely.line_interpolate_point(edges_m[owner], at)
    found = shapely.STRtree(lines_m).query_nearest(
        points, max_distance=TOLERANCE_M, all_matches=False)
    sample, line = found
    keep = np.zeros(len(sample), bool)
    if len(sample):
        edge_dir = _bearings(edges_m[owner[sample]], at[sample])
        line_at = shapely.line_locate_point(lines_m[line], points[sample])
        line_dir = _bearings(lines_m[line], line_at)
        cos = np.abs((edge_dir * line_dir).sum(axis=1))
        keep = cos >= np.cos(np.radians(ALIGN_DEG))
    frame = pd.DataFrame({"edge": owner[sample[keep]], "line": line[keep]})
    frame = frame.groupby(["edge", "line"]).size().rename("hits").reset_index()
    frame["share"] = frame["hits"] / n[frame["edge"].to_numpy()]
    frame["edge"] = cand[frame["edge"].to_numpy()]
    frame["line"] = near[frame["line"].to_numpy()]
    return frame[["edge", "line", "share"]]


def closed_by_lines(match, windows_of):
    """{edge: {window: [line, ...]}} for the edges seasonal lines close.

    `windows_of` is the windows each line closes in, by line position. An
    edge closes when the lines that close at all cover MIN_SHARE of it, and
    then in every window of each of those lines covering WINDOW_SHARE of it:
    two seasonal roads meeting inside one edge close it for both seasons,
    which is the longer reading.
    """
    out = {}
    seasonal = match[np.array([bool(windows_of[i]) for i in match["line"]], bool)]
    for edge, group in seasonal.groupby("edge"):
        if group["share"].sum() < MIN_SHARE:
            continue
        found = defaultdict(list)
        for line, share in zip(group["line"], group["share"]):
            if share >= WINDOW_SHARE:
                for w in windows_of[line]:
                    found[w].append(int(line))
        if not found:
            # Every line is a sliver; the edge is still mostly closed road.
            for line in group["line"]:
                for w in windows_of[line]:
                    found[w].append(int(line))
        out[int(edge)] = dict(found)
    return out


def path_edges(edges, waypoints):
    """The graph edges along a road given as waypoints, and why not if none.

    Each waypoint snaps to the nearest edge within SNAP_M, which is part of
    the road, so a waypoint at a gate inside an edge closes that edge whole,
    as a seasonal gate inside an edge does (docs/safety-quick-fixes.md,
    decision 2). Consecutive waypoints are joined by the shortest path by
    length between their edges' nearer ends, over the edges near the
    waypoints and both ways (a closure closes both). Returns (edge rows,
    None) or ([], the reason).
    """
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    from pyproj import Transformer

    pts = np.asarray(waypoints, float)
    w, s = pts.min(axis=0) - 0.15
    e, n = pts.max(axis=0) + 0.15
    bounds = shapely.bounds(edges.geometry.values)
    rows = np.flatnonzero((bounds[:, 2] >= w) & (bounds[:, 0] <= e)
                          & (bounds[:, 3] >= s) & (bounds[:, 1] <= n))
    if len(rows) == 0:
        return [], "no graph near it"
    u = edges["u"].to_numpy()[rows]
    v = edges["v"].to_numpy()[rows]
    length = edges["length_m"].to_numpy()[rows]
    ids, inv = np.unique(np.concatenate([u, v]), return_inverse=True)
    ui, vi = inv[:len(rows)], inv[len(rows):]
    to_m = Transformer.from_crs(4326, CRS_M, always_xy=True)
    geoms = shapely.transform(edges.geometry.values[rows],
                              lambda xy: np.column_stack(to_m.transform(xy[:, 0], xy[:, 1])))
    tree = shapely.STRtree(geoms)
    px, py = to_m.transform(pts[:, 0], pts[:, 1])
    snapped = []
    for k, (x, y) in enumerate(zip(px, py)):
        i, d = tree.query_nearest(shapely.Point(x, y), return_distance=True)
        if len(i) == 0 or d[0] > SNAP_M:
            far = shapely.Point(x, y).distance(geoms[tree.nearest(shapely.Point(x, y))])
            return [], f"waypoint {k + 1} is {far:,.0f} m from the graph"
        snapped.append(int(i[0]))
    # The cheapest of parallel edges, which is the one a route would take.
    best = {}
    for j, (a, b, L) in enumerate(zip(ui, vi, length)):
        key = (min(a, b), max(a, b))
        if key not in best or L < best[key][1]:
            best[key] = (j, L)
    keys = np.array(list(best))
    lens = np.array([best[k][1] for k in best])
    g = csr_matrix((np.r_[lens, lens], (np.r_[keys[:, 0], keys[:, 1]],
                                        np.r_[keys[:, 1], keys[:, 0]])),
                   shape=(len(ids), len(ids)))
    out = [snapped[0]]
    for a, b in zip(snapped, snapped[1:]):
        if a != b:
            starts = [ui[a], vi[a]]
            dist, pred = dijkstra(g, indices=starts, return_predecessors=True)
            k, end = min(((k, t) for k in (0, 1) for t in (ui[b], vi[b])),
                         key=lambda kt: dist[kt[0], kt[1]])
            if not np.isfinite(dist[k, end]):
                return [], "two waypoints are not connected in the graph"
            node, steps = end, []
            while node != starts[k]:
                p = pred[k, node]
                steps.append(best[(min(p, node), max(p, node))][0])
                node = p
            out += steps[::-1]
        out.append(b)
    return [int(rows[j]) for j in dict.fromkeys(out)], None


# ------------------------------------------------------------- the rows

def federal_rows(edges, mvum=None, nps=None, table=None):
    """The seasonal rows these sources add for the graph `edges`, and a
    report of what each did.

    `edges` is graph_edges with u, v, length_m and geometry (WGS84); `mvum`
    and `nps` are federal_layers.py's frames, or None when the file is
    missing. Returns (rows, report): rows are dicts with closures.py's
    SEASONAL_COLUMNS, `rule` "edge", `node_id` and `way_id` -1, and `tag`
    naming the source.
    """
    from common import CLOSURE_WINDOW

    table = table or load_table()
    table["_parks"] = {p["unit"]: p for p in table["parks"]}
    table["_descriptions"] = {_norm(d["text"]): d for d in table["nps_descriptions"]}
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    length = edges["length_m"].to_numpy()
    names = (edges["name"].fillna("").to_numpy() if "name" in edges.columns
             else np.full(len(edges), ""))
    report = {}
    # (edge, window) -> (level, tag). Level 0 is a source that always stands
    # (MVUM, a dated NPS description); 1 a table road, which overrides 2, a
    # park's window or UNKNOWN_SEASON on its edges.
    found = defaultdict(dict)

    def put(edge, window, level, tag):
        have = found[edge].get(window)
        if have is None or level < have[0]:
            found[edge][window] = (level, tag)

    report["no_car"] = []
    if mvum is not None and len(mvum):
        records = mvum.to_dict("records")
        windows, how = zip(*(mvum_windows(r) for r in records))
        windows = [_with_margin(w, h, "seasonal, no readable dates")
                   for w, h in zip(windows, how)]
        match = match_lines(edges.geometry, mvum.geometry)
        closed = closed_by_lines(match, windows)
        report["no_car"] = no_car_edges(edges, records, match)
        for edge, by_window in closed.items():
            for window, lines in by_window.items():
                r = mvum.iloc[lines[0]]
                put(edge, window, 0, f"mvum {how[lines[0]]}="
                    f"{r.get('passengervehicle_datesopen') or r.get('highclearancevehicle_datesopen') or ''}"
                    f" ({r.get('forestname', '')}, MVUM id {r.get('id', '')})".strip())
        report["mvum"] = _km(closed, length)
    else:
        report["mvum"] = None

    if nps is not None and len(nps):
        records = nps.to_dict("records")
        windows, how = zip(*(nps_windows(r, table) for r in records))
        # A park's window is the table's and keeps it as it is.
        windows = [w if h.startswith("park ") else _with_margin(w, h, "seasonal, no dates")
                   for w, h in zip(windows, how)]
        closed = closed_by_lines(match_lines(edges.geometry, nps.geometry), windows)
        for edge, by_window in closed.items():
            for window, lines in by_window.items():
                levels = [0 if how[i] == "description" else 2 for i in lines]
                i = lines[int(np.argmin(levels))]
                r = records[i]
                put(edge, window, min(levels),
                    f"nps {how[i]}: {r.get('UNITCODE', '')} SEASONAL={r.get('SEASONAL', '')}"
                    + (f", {r['SEASDESC'].strip()}" if (r.get('SEASDESC') or '').strip() else ""))
        report["nps"] = _km(closed, length)
    else:
        report["nps"] = None

    # The table's roads, and its parks' open roads, by waypoints.
    report["roads"], report["exceptions"] = {}, {}
    paths = {}
    for road in table["roads"]:
        on, why = path_edges(edges, road["waypoints"])
        paths[road["id"]] = on
        report["roads"][road["id"]] = (length[on].sum() / 1000.0, why)
        for edge in on:
            # A table road replaces its park's window on its edges.
            for w in [w for w, (lvl, _) in found[edge].items() if lvl == 2]:
                del found[edge][w]
            put(edge, road["window"], 1, f"table {road['id']}: {road['source']}")
    for park in table["parks"]:
        for keep in park.get("except", []):
            on, why = path_edges(edges, keep["waypoints"])
            report["exceptions"][keep["id"]] = (length[on].sum() / 1000.0, why)
            for edge in on:
                for w in [w for w, (lvl, _) in found[edge].items() if lvl == 2]:
                    del found[edge][w]

    report["unknown_beside_table"] = unknown_beside(paths, found, u, v, length, names)

    rows = []
    for edge, by_window in found.items():
        for window, (_, tag) in by_window.items():
            rows.append({
                "edge": edge, "u": int(u[edge]), "v": int(v[edge]), "way_id": -1,
                "name": names[edge], "ref": "", "tag": tag,
                **dict(zip(CLOSURE_WINDOW, window)),
                "length_m": float(length[edge]),
                "rule": "edge", "node_id": -1, "at_m": np.nan,
            })
    return rows, report


def unknown_beside(paths, found, u, v, length, names):
    """Every UNKNOWN_SEASON row on an edge that meets a table road's path
    without being on it: where a stray seasonal flag a step off the table's
    waypoints can close a road the table dates, as one 30 m edge closed the
    North Cascades Highway to July 1 (docs/seasonal-road-risk-verdict.md,
    "Defects found", 1). A report: it closes and opens nothing, and its hits
    are listed in docs/seasonal-road-policy.md for a person to judge.

    Returns dicts of road, edge, name, km and tag.
    """
    unknown = {e: tag for e, by_window in found.items()
               for _, tag in by_window.values()
               if tag.startswith(("nps seasonal, no dates", "mvum seasonal, no readable"))}
    out = []
    for road, on in paths.items():
        on = set(on)
        ends = {int(x) for e in on for x in (u[e], v[e])}
        for e, tag in unknown.items():
            if e not in on and (int(u[e]) in ends or int(v[e]) in ends):
                out.append({"road": road, "edge": int(e), "name": names[e],
                            "km": float(length[e]) / 1000.0, "tag": tag})
    return out


def _with_margin(windows, how, unknown_how):
    """An agency line's `windows` with its source's margin: UNKNOWN_SEASON's
    when `how` is `unknown_how`, the agency's own dates' otherwise."""
    from closures import widen
    if not windows:
        return windows
    before, after = UNKNOWN_MARGIN_DAYS if how == unknown_how else AGENCY_MARGIN_DAYS
    return widen(windows, before, after)


def no_car_edges(edges, records, match):
    """The edges MVUM roads with no full-size highway-legal designation
    close to cars all year, before the paved check closures.py makes.

    `records` are the MVUM rows and `match` their `match_lines` with
    `edges`. An edge closes when such roads cover MIN_SHARE of it, as a
    seasonal edge does, and each line is given the share of it the line
    covers. Returns dicts of edge, line (the longest share), and
    `exception`, `no_car_exception`'s reason or "" (D5,
    docs/national-data-decisions.md).
    """
    if not len(match):
        return []
    no_car = [() if mvum_car_designated(r) else (ALL_YEAR,) for r in records]
    highway = (edges["highway"].to_numpy() if "highway" in edges.columns
               else np.full(len(edges), ""))
    ref = edges["ref"].to_numpy() if "ref" in edges.columns else np.full(len(edges), "")
    share = dict(zip(zip(match["edge"], match["line"]), match["share"]))
    out = []
    for edge, by_window in closed_by_lines(match, no_car).items():
        line = max(by_window[ALL_YEAR], key=lambda i: share[(edge, i)])
        out.append({"edge": edge, "line": line,
                    "exception": no_car_exception(highway[edge], ref[edge])})
    return out


def _km(closed, length):
    edges = np.fromiter(closed, np.int64, len(closed))
    return (len(edges), float(length[edges].sum() / 1000.0) if len(edges) else 0.0)
