"""Roads a state DOT says a car should not drive, or not drive through, as a
side table the router reads (docs/state-road-class.md).

OpenStreetMap cannot see them. Much of rural New England is an unreviewed
TIGER import, `highway=residential` with no surface, access or barrier tag, and
on 2026-10-06 a scenic route followed one such road in New Hampshire to a
blockade: NHDOT classes it Class VI, "not maintained". Each state DOT publishes
its road classes as an ArcGIS layer; this snapshots those layers and labels the
graph's edges from them, writing

  state_road_class.parquet    one row per labelled graph edge:
                              edge, u, v, state, rule, cls, tag, name,
                              state_name, highway, coverage, run_m, from_m,
                              to_m, length_m

`rule` is what the router does with the edge (docs/state-road-class.md,
"The decisions"):
  "closed"    never driven, like a locked gate: NH Class VI, VT Class 4 with an
              impassable surface, VT legal trails and discontinued roads;
  "private"   may be the start or the end of a route and never the middle: NH
              class 0 and VT private roads;
  "unpaved"   counted as dirt by the `avoid_unpaved` setting: the rest of VT
              Class 4.

Two overrides follow (`apply_overrides`): the toll roads in OPEN_TO_ALL are
public whatever the state says, and a state surface code of dirt gives way to
OSM's own explicit sealed surface (SURFACE_CLASSES, SEALED).

`Router` loads it if present. The rules live in `SOURCES`, one entry per state,
and nothing below them knows a state's name, so Maine or Massachusetts is a new
entry and a fetch.

**How an edge is labelled.** Each layer is fetched whole, public roads
included, and every graph edge is sampled every SAMPLE_M. A sample takes the
class of the *nearest* state line within TOLERANCE_M, so a private drive
running beside a highway loses the highway's samples to the highway's own
line. An edge takes a rule when at least MIN_COVERAGE of its samples carry it,
or, for "closed" and "private", when a run of them is MIN_RUN_M long, or
THROUGH_RUN_SAMPLES long on an edge that meets a public road at both ends; the
strictest rule that qualifies wins. Then two guards, because a wrong label on a major road is far
worse than the bug being fixed (docs/state-road-class.md, Trap 1):
  - a sample only counts for a line running the same way as the edge there,
    within MAX_BEARING_DEG, so a drive crossing or leaving a road is not it;
  - on motorway, trunk, primary, secondary and tertiary (and their links) a
    label stands only when the state's name for the road agrees with OSM's
    (`same_name`).

Side table rather than graph column for the reason closures.py gives: a column
means a rebuild, and a rebuild moves every published number. And for the same
reason it must be rerun after every graph rebuild, since it names edges by
their row in graph_edges.parquet.

Usage:
  python state_roads.py fetch <raw_dir> [STATE ...]
  python state_roads.py build <raw_dir> <processed_dir> [<out_dir>]
"""

import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

# The rules, by state: a list of layers each, every layer an ArcGIS feature
# layer fetched whole. `classify` maps a feature's attributes to a (rule, cls)
# pair, `cls` being a short label for the record, or None for a road a car may
# drive like any other; those are fetched too, since they are what keeps a
# private drive's label off the highway beside it. `names` are the attributes
# holding the road's name, compared with OSM's by `same_name`. `min_lat`, where
# set, keeps the layer's labels to edges whose midpoint is at or north of it.
#
# NH: LEGIS_CLASS is I-V (state and town highways), VI (town, not maintained),
# VII (federal) and 0 (private). Class V `SURF_TYPE='Unpaved'` is not in scope
# (docs/state-road-class.md, "Follow-ups").
#
# VT: AOTCLASS is a coded domain (the layer's ?f=pjson): 4 Town Highway Class
# 4, 7 Legal Trail, 70 Unconfirmed Legal Trail, 71 Unidentified Corridor, 96
# Discontinued Road, 97 Discontinued Now Private, 8 Private Road - No Show, 9
# Private Road, 89 Proposed Private Road. SURFACETYPE 6 is "Impassable or
# untravelled".
#
# MA: JURISDICTN 'H' is Private and FACILITY 14 a Private Way; SURFACE_TP 1 is
# unimproved or graded earth and 2 gravel or stone. JURISDICTN '0',
# "Unaccepted by city or town", is left alone on purpose: it is 15.7% of the
# MA graph and mostly ordinary subdivision streets (docs/state-road-class.md,
# "Massachusetts").
#
# ME: two layers. MaineDOT's Private Roads layer is private throughout, every
# RDCLASS of it, but only north of 45 N, where the user decided it: statewide
# it is 27% of the ME graph. ALLPUBRDS is every public road, fetched only as
# the competitor that keeps private labels off the roads beside them; a graph
# road in neither layer is left alone.


def _nh(a):
    cls = (a.get("LEGIS_CLASS") or "").strip()
    if cls == "VI":
        return "closed", "NH VI"
    if cls == "0":
        return "private", "NH 0"
    return None


def _vt(a):
    cls, surface = a.get("AOTCLASS"), a.get("SURFACETYPE")
    if cls == 4:
        return ("closed", "VT 4 impassable") if surface == 6 else ("unpaved", "VT 4")
    if cls in (7, 70, 71):
        return "closed", f"VT {cls} trail"
    if cls in (96, 97):
        return "closed", f"VT {cls} discontinued"
    if cls in (8, 9, 89):
        return "private", f"VT {cls} private"
    return None


def _ma(a):
    if (a.get("JURISDICTN") or "").strip() == "H":
        return "private", "MA jurisdiction H"
    if a.get("FACILITY") == 14:
        return "private", "MA private way"
    if a.get("SURFACE_TP") == 1:
        return "unpaved", "MA earth"
    if a.get("SURFACE_TP") == 2:
        return "unpaved", "MA gravel"
    return None


def _me_private(a):
    return "private", f"ME {(a.get('RDCLASS') or 'unclassed').strip()}"


def _layer(**kw):
    kw.setdefault("oid", "OBJECTID")
    kw.setdefault("min_lat", None)
    return SimpleNamespace(**kw)


SOURCES = {
    "NH": [_layer(
        layer="nhdot-legislative-class",
        url=("https://maps.dot.nh.gov/arcgis_server/rest/services/Highways/"
             "NHDOT_HIGHWAYS_Legislative_Class/MapServer/1"),
        fields=["OBJECTID", "STREET", "TOWN_NAME", "LEGIS_CLASS", "LC_LEGEND",
                "SURF_TYPE", "SECT_LENGTH"],
        names=("STREET",),
        tag=lambda a: f"LEGIS_CLASS={a.get('LEGIS_CLASS')} ({a.get('LC_LEGEND')})",
        classify=_nh)],
    "VT": [_layer(
        layer="vtrans-trans-rds",
        url=("https://maps.vtrans.vermont.gov/arcgis/rest/services/Layers/"
             "s1111_rds/MapServer/2"),
        fields=["OBJECTID", "PRIMARYNAME", "RDFLNAME", "ALIAS1", "TOWN",
                "AOTCLASS", "SURFACETYPE", "ARCMILES"],
        names=("PRIMARYNAME", "RDFLNAME", "ALIAS1"),
        tag=lambda a: f"AOTCLASS={a.get('AOTCLASS')} SURFACETYPE={a.get('SURFACETYPE')}",
        classify=_vt)],
    "MA": [_layer(
        layer="massdot-roads",
        url=("https://services1.arcgis.com/hGdibHYSPO59RG1h/ArcGIS/rest/services/"
             "MassDOTRoads_gdb/FeatureServer/0"),
        fields=["OBJECTID", "STREETNAME", "RT_NUMBER", "MGIS_TOWN", "JURISDICTN",
                "FACILITY", "SURFACE_TP", "LENGTH_MI"],
        names=("STREETNAME", "RT_NUMBER"),
        tag=lambda a: (f"JURISDICTN={a.get('JURISDICTN')} FACILITY={a.get('FACILITY')} "
                       f"SURFACE_TP={a.get('SURFACE_TP')}"),
        classify=_ma)],
    "ME": [_layer(
        layer="mainedot-private-roads",
        url=("https://arcgisserver.maine.gov/arcgis/rest/services/mdot/"
             "MaineDOT_Dynamic/MapServer/915"),
        fields=["OBJECTID", "RDNAME", "STREETNAME", "TOWN", "RDCLASS", "FEET"],
        names=("RDNAME",),
        tag=lambda a: f"Private Roads RDCLASS={a.get('RDCLASS')}",
        classify=_me_private, min_lat=45.0), _layer(
        layer="mainedot-allpubrds",
        url=("https://arcgisserver.maine.gov/arcgis/rest/services/mdot/"
             "MaineDOT_LRS/MapServer/1"),
        fields=["objectid", "townname", "tlength"], oid="objectid",
        names=(), tag=lambda a: "ALLPUBRDS",
        classify=lambda a: None)],
}

RULES = ("closed", "private", "unpaved")

# Each state's own outline, which every layer is clipped to before matching.
# The NH layer carries stubs that stand in Massachusetts, Vermont and Maine
# ("MA Turn Around", "Vermont Route 12", I-89's turnaround), coded class 0, so
# without the clip a private label lands on I-95 in Massachusetts. Census
# TIGERweb, current vintage, at full resolution; public domain.
BOUNDARY_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "State_County/MapServer/0")

# --- Matching parameters (docs/state-road-class.md, "Parameters") -------------
# Metres between samples along an edge; an edge shorter than this gets one, at
# its midpoint.
SAMPLE_M = 25.0
# How far a state line may sit from a sample and still be the same road, in
# metres. The two datasets digitise one road independently, so they disagree
# by a few metres; a parallel road is rarely nearer than 15.
TOLERANCE_M = 12.0
# Share of an edge's samples that must carry a rule for the edge to take it.
MIN_COVERAGE = 0.5
# A run of consecutive samples this long, in metres, carrying "closed" or
# "private" also labels the edge, whatever its share. A road is closed if any
# stretch of it is (closures.py closes an edge for one barrier inside it), and
# a route through an edge drives every metre of it; the Class VI section that
# started this is 53% of the OSM edge it lies in (docs/state-road-class.md).
MIN_RUN_M = 100.0
RUN_RULES = ("closed", "private")
# ...and a run of at least this many samples, about 50 m, does too when its
# edge meets a public road at both ends. That edge is a connector, the one
# shortcut a router reaches for, so a short closed or private stretch on it
# matters more than anywhere else. One sample is not enough: of the 62
# single-sample runs on such edges, the longest lie on I-93 and I-95, a
# private stub brushing a public road (docs/state-road-class.md, "Short runs").
THROUGH_RUN_SAMPLES = 2
# Largest angle between the edge and the state line at a sample, in degrees,
# for the sample to count. Lines are undirected, so the angle is folded to
# 0-90.
MAX_BEARING_DEG = 30.0
# The OSM classes reported as major roads, and those on which a label also
# needs the names to agree: secondary and tertiary too, because a private stub
# drawn over a public road is how every false label on them looked
# (docs/state-road-class.md, "The false-positive guard").
MAJOR = {"motorway", "motorway_link", "trunk", "trunk_link",
         "primary", "primary_link"}
NAMED = MAJOR | {"secondary", "secondary_link", "tertiary", "tertiary_link"}

PAGE = 2000

# --- Overrides (docs/state-road-class.md, "Overrides") ------------------------
# Roads a state codes private that their owner opens to every driver, as
# (state, OSM name, (south, west, north, east)). Toll roads up a mountain,
# priced and seasonal, but public in every sense a route cares about; their
# seasons are seasonal_closures.parquet's job. Matched by name inside a box,
# because "Skyline Drive" is a common name.
OPEN_TO_ALL = [
    ("NH", "Mount Washington Auto Road", (44.25, -71.32, 44.30, -71.20)),
    ("VT", "Skyline Drive", (43.10, -73.16, 43.18, -73.09)),       # Mt Equinox
]

# The classes that come from a state's *surface* code, where OSM's own
# explicit surface wins when it says the road is sealed: a road gets paved and
# an inventory code goes stale. MassDOT codes Mt Greylock's Rockwell Road
# gravel; OSM has 10.8 km of it as asphalt. Not VT Class 4, which is a legal
# class the user decided counts as dirt (decision 3).
SURFACE_CLASSES = {"MA earth", "MA gravel"}
# The OSM surfaces that are sealed: everything score.py's UNPAVED leaves out
# that a road is actually laid with.
SEALED = {"asphalt", "paved", "concrete", "concrete:plates", "concrete:lanes",
          "paving_stones", "chipseal", "sett", "cobblestone"}
# How near an edge's midpoint must lie to an OSM way to be one of its edges, in
# metres, as closures.py matches them.
WAY_MATCH_M = 1.0

# state_road_class.parquet's columns, in order; see the module docstring.
COLUMNS = ["edge", "u", "v", "state", "rule", "cls", "tag", "name", "state_name",
           "highway", "coverage", "run_m", "from_m", "to_m", "length_m"]


# ------------------------------------------------------------------- fetching

def _get(url: str, params: dict, tries: int = 5):
    # certifi's bundle where it is installed: python.org's macOS build ships
    # with no CA certificates and refuses both hosts without it.
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = None
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(full, timeout=120, context=context) as r:
                return json.loads(r.read())
        except Exception as e:                      # noqa: BLE001 - retried
            if attempt == tries - 1:
                raise
            print(f"  retrying after {e!r}", flush=True)
            time.sleep(5 * (attempt + 1))


def fetch(raw_dir: str, states=None):
    """Snapshot each state's layer, whole, into <raw_dir>/state-roads/ as
    <state>-<layer>-<YYYYMMDD>.geojson, and its outline (BOUNDARY_URL) as
    <state>-tigerweb-state-<YYYYMMDD>.geojson.

    Paged by OBJECTID order with `resultOffset`, PAGE features at a time, and
    checked against the layer's own count, so a short page cannot pass for the
    end of the layer. A layer already snapshotted today is not fetched again.
    """
    out_dir = Path(raw_dir) / "state-roads"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    for state in states or SOURCES:
        for src in SOURCES[state]:
            path = out_dir / f"{state.lower()}-{src.layer}-{stamp}.geojson"
            if not path.exists():
                _fetch_layer(state, src, path)
        outline = _get(BOUNDARY_URL + "/query", {
            "where": f"STUSAB='{state}'", "outFields": "STUSAB,NAME,GEOID",
            "outSR": 4326, "f": "geojson"})
        if len(outline.get("features", [])) != 1:
            raise RuntimeError(f"{state}: TIGERweb returned "
                               f"{len(outline.get('features', []))} outlines, not 1")
        path = out_dir / f"{state.lower()}-tigerweb-state-{stamp}.geojson"
        with open(path, "w") as f:
            json.dump(outline, f)
        print(f"wrote {path}", flush=True)


def _fetch_layer(state, src, path):
    query = src.url + "/query"
    count = _get(query, {"where": "1=1", "returnCountOnly": "true",
                         "f": "json"})["count"]
    features = []
    while len(features) < count:
        page = _get(query, {
            "where": "1=1", "outFields": ",".join(src.fields),
            "orderByFields": src.oid, "resultOffset": len(features),
            "resultRecordCount": PAGE, "outSR": 4326, "f": "geojson"})
        got = page.get("features", [])
        if not got:
            break
        features += got
        print(f"  {state}: {len(features):,} of {count:,}", flush=True)
    ids = {f["properties"][src.oid] for f in features}
    if len(features) != count or len(ids) != count:
        raise RuntimeError(f"{state}: fetched {len(features):,} features "
                           f"({len(ids):,} distinct) of {count:,}")
    with open(path, "w") as f:
        json.dump({"type": "FeatureCollection", "source": src.url,
                   "fetched": date.today().isoformat(),
                   "features": features}, f)
    print(f"wrote {path} ({count:,} features)", flush=True)


def latest_snapshot(raw_dir: str, state: str, layer: str) -> Path:
    found = sorted((Path(raw_dir) / "state-roads").glob(
        f"{state.lower()}-{layer}-*.geojson"))
    if not found:
        raise FileNotFoundError(f"no {state} snapshot in {raw_dir}/state-roads; "
                                f"run `python state_roads.py fetch {raw_dir}`")
    return found[-1]


# -------------------------------------------------------------------- names

# Spellings that mean the same word, to one form. Both datasets abbreviate
# freely and differently: NH writes "BROOK RD", OSM "Brook Road".
_WORDS = {
    "ROAD": "RD", "STREET": "ST", "AVENUE": "AVE", "AV": "AVE", "DRIVE": "DR",
    "LANE": "LN", "HIGHWAY": "HWY", "HGWY": "HWY", "TURNPIKE": "TPKE",
    "TPK": "TPKE", "PARKWAY": "PKWY", "BOULEVARD": "BLVD", "PLACE": "PL",
    "COURT": "CT", "CIRCLE": "CIR", "TERRACE": "TER", "EXTENSION": "EXT",
    "MOUNTAIN": "MTN", "MOUNT": "MT", "SAINT": "ST", "SAINTE": "ST", "STE": "ST",
    "TRAIL": "TRL", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "ROUTE": "RTE", "RT": "RTE", "INTERSTATE": "I", "HILL": "HL", "POND": "PD",
}
# Words that say what kind of road it is, or whose road, and not which one. A
# name made only of these names nothing: the NH layer's stub on Vermont Route
# 12 is called "Vermont", and its unnamed segments "No Name".
_GENERIC = {
    "RD", "ST", "AVE", "DR", "LN", "HWY", "TPKE", "PKWY", "BLVD", "PL", "CT",
    "CIR", "TER", "EXT", "N", "S", "E", "W", "RTE", "I", "US", "SR", "TH",
    "NH", "VT", "ME", "MA", "MASS", "VERMONT", "MAINE", "MASSACHUSETTS", "NEW",
    "HAMPSHIRE", "NO", "NAME", "THE",
}
# The generic words that cannot name a road even spelled out in full.
_NAMES_NOTHING = {"NO", "NAME", "NH", "VT", "ME", "MA", "MASS", "VERMONT", "MAINE",
                  "MASSACHUSETTS", "NEW", "HAMPSHIRE", "THE"}
_SPLIT = re.compile(r"[^A-Z0-9]+")


def _tokens(name: str) -> tuple:
    words = [w for w in _SPLIT.split((name or "").upper()) if w]
    return tuple(_WORDS.get(w, w) for w in words)


def same_name(osm_names, state_names, exact: bool = False) -> bool:
    """Whether any OSM name (name or ref) is the same road as any state name.

    Spelled alike first ("Brook Rd" is "Brook Road", "Ste Aurelie" is
    "Saint Aurelie"), then the same when the words naming the road, the ones
    not `_GENERIC`, of one are all among the other's: "Realty Road" is
    "American Realty Rd" and "NH 12A" is "NH ROUTE 12A", but "Vermont Route
    12" is not "Vermont", which names no road at all. A name made only of
    generic words must match exactly: "South Street" is "SOUTH ST" and is not
    "North Street". So must one whose naming words are only numbers, and so
    must every name when `exact`: OSM's "I 93" is not the state's "Hooksett
    Rest Area Interstate 93 N", a private stub that once labelled I-93 private.
    """
    for o in filter(None, osm_names):
        for t in filter(None, state_names):
            a, b = _tokens(o), _tokens(t)
            sig_a, sig_b = set(a) - _GENERIC, set(b) - _GENERIC
            if sig_a and sig_b:
                if sig_a == sig_b:
                    return True
                small = sig_a if len(sig_a) <= len(sig_b) else sig_b
                worded = any(not w.isdigit() for w in small)
                if not exact and worded and (sig_a <= sig_b or sig_b <= sig_a):
                    return True
            elif a == b and not set(a) <= _NAMES_NOTHING:
                # "South Street" is "SOUTH ST" though every word is generic.
                return True
    return False


# ------------------------------------------------------------------ labelling

def read_lines(raw_dir: str, states=None):
    """Every state's latest snapshots as one GeoDataFrame of line parts in
    EPSG:CRS_METERS, clipped to the state's outline, with columns state,
    layer, rule (None for a road a car may drive like any other), cls, tag,
    names (a tuple), objectid and min_lat (NaN where the layer has none)."""
    import geopandas as gpd
    import shapely
    import shapely.geometry
    from common import CRS_METERS

    frames = []
    for state in states or SOURCES:
        outline_path = latest_snapshot(raw_dir, state, "tigerweb-state")
        with open(outline_path) as f:
            outline = shapely.geometry.shape(json.load(f)["features"][0]["geometry"])
        shapely.prepare(outline)
        for src in SOURCES[state]:
            path = latest_snapshot(raw_dir, state, src.layer)
            with open(path) as f:
                features = json.load(f)["features"]
            rows, geoms = [], []
            for feat in features:
                if not feat.get("geometry"):
                    continue
                a = feat["properties"]
                found = src.classify(a)
                rows.append({
                    "state": state,
                    "layer": src.layer,
                    "rule": found[0] if found else None,
                    "cls": found[1] if found else "",
                    "tag": src.tag(a),
                    "names": tuple(a.get(k) or "" for k in src.names),
                    "objectid": int(a[src.oid]),
                    "min_lat": np.nan if src.min_lat is None else float(src.min_lat),
                })
                geoms.append(feat["geometry"])
            frame = gpd.GeoDataFrame(
                rows, geometry=[shapely.geometry.shape(g) for g in geoms], crs=4326)
            inside = shapely.contains(outline, frame.geometry.values)
            cut = ~inside & shapely.intersects(outline, frame.geometry.values)
            frame.loc[cut, "geometry"] = shapely.intersection(
                frame.geometry.values[cut], outline)
            before = len(frame)
            frame = frame[inside | cut]
            frame = frame[~frame.geometry.is_empty]
            print(f"{state}: {len(frame):,} lines from {path.name}, clipped to "
                  f"{outline_path.name} ({before - int(inside.sum()):,} reach "
                  f"outside it, {before - len(frame):,} of them wholly)", flush=True)
            frames.append(frame)
    lines = pd.concat(frames, ignore_index=True)
    lines = lines.explode(index_parts=False).reset_index(drop=True)
    lines = lines[lines.geometry.geom_type == "LineString"].to_crs(CRS_METERS)
    return lines[lines.geometry.length > 0].reset_index(drop=True)


def _bearing_at(lines, along, step=2.0):
    """Bearing in degrees of each line at `along` metres, from points `step`
    either side, clipped to the line."""
    import shapely
    length = shapely.length(lines)
    a = shapely.line_interpolate_point(lines, np.clip(along - step, 0, length))
    b = shapely.line_interpolate_point(lines, np.clip(along + step, 0, length))
    return np.degrees(np.arctan2(shapely.get_x(b) - shapely.get_x(a),
                                 shapely.get_y(b) - shapely.get_y(a)))


def _fold(delta):
    """An angle between two undirected lines, folded to 0-90 degrees."""
    d = np.abs(delta) % 180.0
    return np.minimum(d, 180.0 - d)


def sample_matches(edge_geoms, lines):
    """For every sample along every edge, the nearest state line that runs the
    same way, or -1.

    `edge_geoms` and `lines.geometry` are in metres. Returns (edge, along,
    line), one entry per sample in order along each edge: `edge` its position
    in `edge_geoms`, `along` its metres from the edge's start.
    """
    import shapely

    line_geoms = lines.geometry.values
    length = shapely.length(edge_geoms)
    n = np.maximum(1, np.round(length / SAMPLE_M).astype(np.int64))
    edge = np.repeat(np.arange(len(edge_geoms)), n)
    first = np.repeat(np.cumsum(n) - n, n)
    k = np.arange(len(edge)) - first
    along = (k + 0.5) * (length[edge] / n[edge])
    points = shapely.line_interpolate_point(edge_geoms[edge], along)
    edge_bearing = _bearing_at(edge_geoms[edge], along)

    tree = shapely.STRtree(line_geoms)
    s, l = tree.query(points, predicate="dwithin", distance=TOLERANCE_M)
    dist = shapely.distance(points[s], line_geoms[l])
    at = shapely.line_locate_point(line_geoms[l], points[s])
    aligned = _fold(edge_bearing[s] - _bearing_at(line_geoms[l], at)) <= MAX_BEARING_DEG
    s, l, dist = s[aligned], l[aligned], dist[aligned]

    # The nearest aligned line per sample: sort by sample, then distance, and
    # keep the first of each sample.
    order = np.lexsort((dist, s))
    s, l = s[order], l[order]
    keep = np.ones(len(s), bool)
    keep[1:] = s[1:] != s[:-1]
    line = np.full(len(edge), -1, np.int64)
    line[s[keep]] = l[keep]
    return edge, along, line


def runs(sample_edge, sample_rule, along):
    """Every run of consecutive samples along one edge with one rule, as a
    DataFrame: edge, rule (index into RULES plus one; 0 a public road, -1 no
    line), n samples, from_m and to_m (the first and last sample's position),
    and the rules of the samples just before and after it on the same edge
    (-2 where the run reaches the edge's end)."""
    if not len(sample_edge):
        return pd.DataFrame(columns=["edge", "rule", "n", "from_m", "to_m",
                                     "before", "after"])
    new = np.ones(len(sample_edge), bool)
    new[1:] = (sample_edge[1:] != sample_edge[:-1]) | (sample_rule[1:] != sample_rule[:-1])
    starts = np.flatnonzero(new)
    ends = np.append(starts[1:], len(sample_edge)) - 1
    edge = sample_edge[starts]
    before = np.full(len(starts), -2)
    after = np.full(len(starts), -2)
    same_prev = np.zeros(len(starts), bool)
    same_prev[1:] = edge[1:] == edge[:-1]
    before[same_prev] = sample_rule[starts[same_prev] - 1]
    same_next = np.zeros(len(starts), bool)
    same_next[:-1] = edge[:-1] == edge[1:]
    after[same_next] = sample_rule[ends[same_next] + 1]
    return pd.DataFrame({"edge": edge, "rule": sample_rule[starts],
                         "n": ends - starts + 1, "from_m": along[starts],
                         "to_m": along[ends], "before": before, "after": after})


def label(edges, lines):
    """Label `edges` (a GeoDataFrame of graph_edges.parquet's rows, in any
    CRS, with u, v, length_m, name, ref and highway) from `lines`
    (`read_lines`).

    Returns a SimpleNamespace of:
      table     the side table (module docstring), plus from_m and to_m, the
                stretch of a closed edge the closed samples span;
      refused   the same columns, for the labels on NAMED roads the names did
                not confirm (Trap 1);
      matched   {edge: state} for every edge any state line matched, for the
                share-of-state record;
      short     the closed and private runs too short (MIN_RUN_M) to label an
                edge their rule does not otherwise cover, from `runs`.
    """
    import shapely
    from common import CRS_METERS

    geoms_m = edges.geometry.to_crs(CRS_METERS).values
    n_edges = len(edges)
    # Only the edges with some state line near them are worth sampling.
    tree = shapely.STRtree(lines.geometry.values)
    near_any = np.unique(tree.query(geoms_m, predicate="dwithin",
                                    distance=TOLERANCE_M)[0])
    sample_edge, along, sample_line = sample_matches(geoms_m[near_any], lines)
    sample_edge = near_any[sample_edge]

    rule_of_line = lines["rule"].map({r: i + 1 for i, r in enumerate(RULES)})
    rule_of_line = rule_of_line.fillna(0).astype(np.int64).to_numpy()
    sample_rule = np.where(sample_line >= 0, rule_of_line[np.maximum(sample_line, 0)], -1)
    # A layer limited to a latitude still claims its samples south of it, so
    # no other line takes them, but as a road a car may drive.
    min_lat = lines["min_lat"].to_numpy()
    lat = shapely.get_y(shapely.line_interpolate_point(
        edges.geometry.to_crs(4326).values, 0.5, normalized=True))
    limited = (sample_line >= 0) & ~np.isnan(min_lat[np.maximum(sample_line, 0)])
    south = limited & (lat[sample_edge] < min_lat[np.maximum(sample_line, 0)])
    sample_rule[south] = 0

    samples = np.bincount(sample_edge, minlength=n_edges)
    # counts[e, r]: samples of edge e whose nearest aligned line carries rule
    # r (0 = a road a car may drive like any other).
    counts = np.zeros((n_edges, len(RULES) + 1), np.int64)
    hit = sample_rule >= 0
    np.add.at(counts, (sample_edge[hit], sample_rule[hit]), 1)
    shares = counts[:, 1:] / np.maximum(samples, 1)[:, None]
    spacing = np.zeros(n_edges)
    lengths = shapely.length(geoms_m)
    spacing[samples > 0] = lengths[samples > 0] / samples[samples > 0]

    every = runs(sample_edge, sample_rule, along)
    longest = np.zeros((n_edges, len(RULES) + 1), np.int64)
    ruled = every[every["rule"] >= 0]
    np.maximum.at(longest, (ruled["edge"].to_numpy(), ruled["rule"].to_numpy()),
                  ruled["n"].to_numpy())
    # On a major road a label rests on its share alone: no run of samples
    # makes I-93 private (docs/state-road-class.md, "The false-positive guard").
    major = edges["highway"].isin(MAJOR).to_numpy() if "highway" in edges.columns \
        else np.zeros(n_edges, bool)
    qualifies = shares >= MIN_COVERAGE
    for r in RUN_RULES:
        i = RULES.index(r)
        qualifies[:, i] |= ~major & (longest[:, i + 1] * spacing >= MIN_RUN_M)
    # The connectors: an edge meeting, at both ends, another edge no run rule
    # took, i.e. a public road.
    taken = qualifies[:, [RULES.index(r) for r in RUN_RULES]].any(axis=1)
    u, v = edges["u"].to_numpy(), edges["v"].to_numpy()
    ends, inverse = np.unique(np.concatenate([u, v]), return_inverse=True)
    public_at = np.bincount(inverse, weights=np.tile(~taken, 2), minlength=len(ends))
    others = public_at[inverse] - np.tile(~taken, 2)
    connector = (others[:n_edges] > 0) & (others[n_edges:] > 0)
    for r in RUN_RULES:
        i = RULES.index(r)
        qualifies[:, i] |= ~major & connector & (longest[:, i + 1] >= THROUGH_RUN_SAMPLES)
    # The strictest rule that qualifies (RULES is in that order, and argmax
    # takes the first True).
    best = np.argmax(qualifies, axis=1)
    labelled = np.flatnonzero(qualifies.any(axis=1))
    share = shares[np.arange(n_edges), best]
    run_m = longest[np.arange(n_edges), best + 1] * spacing

    # The runs of a run rule that labelled nothing: shorter than MIN_RUN_M,
    # on an edge left unlabelled or given a weaker rule (RULES is strictest
    # first, so a larger code is weaker).
    code = every["rule"].to_numpy()
    e = every["edge"].to_numpy()
    want = np.full(n_edges, -1)
    want[labelled] = best[labelled] + 1
    run_rule = np.isin(code, [RULES.index(r) + 1 for r in RUN_RULES])
    short = every[run_rule & ((want[e] == -1) | (want[e] > code))].copy()
    short["run_m"] = short["n"] * spacing[short["edge"].to_numpy()]
    short["rule"] = [RULES[c - 1] for c in short["rule"]]

    # The closed samples' span on each closed edge, for `Router.snap`.
    closed_code = RULES.index("closed") + 1
    spans = every[(code == closed_code)].groupby("edge").agg(
        from_m=("from_m", "min"), to_m=("to_m", "max"))
    half = spacing / 2.0

    # The line most of each labelled edge's winning samples came from, for
    # its tag and names.
    mine = hit & (sample_rule == want[sample_edge])
    pairs = pd.DataFrame({"edge": sample_edge[mine], "line": sample_line[mine]})
    top = (pairs.groupby(["edge", "line"]).size().rename("n").reset_index()
           .sort_values(["edge", "n"], ascending=[True, False])
           .drop_duplicates("edge").set_index("edge")["line"])
    # Every name any winning line gives the road, for the name check.
    names = (pairs.drop_duplicates().assign(
        names=lambda p: lines["names"].to_numpy()[p["line"].to_numpy()])
        .groupby("edge")["names"].agg(lambda s: {n for t in s for n in t if n}))

    rows = []
    col = {c: (edges[c].fillna("").to_numpy() if c in edges.columns
               else np.full(n_edges, "")) for c in ("name", "ref", "highway")}
    for e in labelled:
        line = int(top[e])
        state_names = names[e]
        rule = RULES[best[e]]
        span = (max(0.0, spans.at[e, "from_m"] - half[e]),
                min(lengths[e], spans.at[e, "to_m"] + half[e])) \
            if rule == "closed" else (np.nan, np.nan)
        rows.append({
            "edge": int(e), "u": int(edges["u"].iat[e]), "v": int(edges["v"].iat[e]),
            "state": lines["state"].iat[line],
            "rule": rule,
            "cls": lines["cls"].iat[line],
            "tag": lines["tag"].iat[line],
            "name": col["name"][e],
            "state_name": "; ".join(sorted(state_names)),
            "highway": col["highway"][e],
            "coverage": float(share[e]),
            "run_m": float(run_m[e]),
            "from_m": float(span[0]), "to_m": float(span[1]),
            "length_m": float(edges["length_m"].iat[e]),
            "named": same_name([col["name"][e], *str(col["ref"][e]).split(";")],
                               state_names, exact=col["highway"][e] in MAJOR),
        })
    table = pd.DataFrame(rows, columns=COLUMNS + ["named"])
    refuse = table["highway"].isin(NAMED) & ~table["named"]
    refused = table[refuse].drop(columns="named").reset_index(drop=True)
    table = table[~refuse].drop(columns="named").reset_index(drop=True)
    table = table.astype({"edge": "int64", "u": "int64", "v": "int64",
                          **{c: "float64" for c in ("coverage", "run_m", "from_m",
                                                    "to_m", "length_m")}})
    state_of_line = lines["state"].to_numpy()
    matched = pd.DataFrame({"edge": sample_edge[hit],
                            "state": state_of_line[sample_line[hit]]})
    matched = matched.groupby("edge")["state"].agg(lambda s: s.mode().iat[0])
    short["state"] = matched.reindex(short["edge"].to_numpy()).to_numpy()
    return SimpleNamespace(table=table, refused=refused, matched=matched,
                           short=short.reset_index(drop=True))


def _km(frame):
    return frame["length_m"].sum() / 1000.0


def main(raw_dir: str, processed_dir: str, out_dir: str = None):
    """Label processed_dir's graph from raw_dir's latest snapshots and write
    the table into `out_dir` (processed_dir unless given)."""
    import geopandas as gpd

    d = Path(processed_dir)
    t0 = time.time()
    lines = read_lines(raw_dir)
    edges = gpd.read_parquet(d / "graph_edges.parquet",
                             columns=["u", "v", "length_m", "name", "ref",
                                      "highway", "score", "geometry"])
    found = label(edges, lines)
    roads = gpd.read_parquet(d / "roads.parquet", columns=["surface", "geometry"])
    found.table, found.overridden = apply_overrides(found.table, edges, roads)
    out = Path(out_dir or processed_dir)
    found.table.to_parquet(out / "state_road_class.parquet", index=False)
    print(f"labelled in {time.time() - t0:.0f}s", flush=True)
    report(edges, found)
    print(f"wrote {out / 'state_road_class.parquet'} ({len(found.table):,} rows)",
          flush=True)
    return found


def apply_overrides(table, edges, roads):
    """`table` without the labels OPEN_TO_ALL and SEALED overrule, and those
    labels, with a `why` column.

    `edges` is graph_edges.parquet's frame (u, v, name, geometry) and `roads`
    roads.parquet's (surface, geometry), each in any CRS.
    """
    import shapely
    from common import CRS_METERS

    rows = table["edge"].to_numpy()
    names = edges["name"].fillna("").to_numpy()[rows]
    mid = shapely.line_interpolate_point(edges.geometry.to_crs(4326).values[rows],
                                         0.5, normalized=True)
    lat, lon = shapely.get_y(mid), shapely.get_x(mid)
    why = np.full(len(table), "", dtype=object)
    private = (table["rule"] == "private").to_numpy()
    for state, name, (s, w, n, e) in OPEN_TO_ALL:
        hit = (private & (table["state"].to_numpy() == state) & (names == name)
               & (lat >= s) & (lat <= n) & (lon >= w) & (lon <= e))
        why[hit] = f"open to all: {name}"

    surface = table["cls"].isin(SURFACE_CLASSES).to_numpy() & (why == "")
    if surface.any():
        sealed = roads[roads["surface"].fillna("").str.lower().isin(SEALED)]
        geoms = sealed.geometry.to_crs(CRS_METERS).values
        pts = shapely.line_interpolate_point(
            edges.geometry.to_crs(CRS_METERS).values[rows[surface]], 0.5,
            normalized=True)
        near = np.unique(shapely.STRtree(geoms).query(
            pts, predicate="dwithin", distance=WAY_MATCH_M)[0])
        at = np.flatnonzero(surface)[near]
        why[at] = "OSM surface is sealed"
    drop = why != ""
    overridden = table[drop].assign(why=why[drop]).reset_index(drop=True)
    return table[~drop].reset_index(drop=True), overridden


def report(edges, found):
    """What the table holds, by state, class and road class, what the guards
    refused, and what the run rule left alone: the numbers
    docs/state-road-class.md records."""
    table, refused, matched, short = found.table, found.refused, found.matched, found.short
    km = edges["length_m"].to_numpy() / 1000.0
    scenic = edges["score"].to_numpy() >= 7.0
    for state in sorted(set(matched.unique())):
        mine = matched.index[matched == state].to_numpy()
        total, scen = km[mine].sum(), km[mine][scenic[mine]].sum()
        print(f"{state}: {total:,.0f} km of graph matched a state line, "
              f"{scen:,.0f} of them scenic (score >= 7)")
        rows = table[table["state"] == state]
        for (rule, cls), g in rows.groupby(["rule", "cls"]):
            e = g["edge"].to_numpy()
            by_run = g["coverage"] < MIN_COVERAGE
            print(f"  {rule:8} {cls:24} {len(g):6,} edges {km[e].sum():8.1f} km "
                  f"({km[e].sum() / total:.1%}), scenic {km[e][scenic[e]].sum():6.1f} km "
                  f"({km[e][scenic[e]].sum() / scen:.1%}); by the run rule alone "
                  f"{by_run.sum():,} edges, {g.loc[by_run, 'length_m'].sum() / 1000:.1f} km")
        for rule, g in rows.groupby("rule"):
            by = g.groupby("highway")["length_m"].sum().div(1000).sort_values(ascending=False)
            print(f"  {rule} by highway: " + ", ".join(f"{h} {v:.1f}" for h, v in by.items()))
        closed = rows[rows["rule"] == "closed"]
        partial = closed[(closed["from_m"] > 0) | (closed["to_m"] < closed["length_m"] - 1)]
        print(f"  closed edges a car may still be on part of: {len(partial):,} "
              f"({partial['length_m'].sum() / 1000:.1f} km)")
        s = short[short["state"] == state]
        for rule, g in s.groupby("rule"):
            through = (g["before"] == 0) & (g["after"] == 0)
            print(f"  {rule} runs under {MIN_RUN_M:.0f} m labelling nothing: {len(g):,} runs, "
                  f"{g['run_m'].sum() / 1000:.1f} km; with a public road on both sides "
                  f"{through.sum():,}, {g.loc[through, 'run_m'].sum() / 1000:.1f} km")
    over = getattr(found, "overridden", None)
    if over is not None and len(over):
        print("overridden:")
        for (why, state, cls), g in over.groupby(["why", "state", "cls"]):
            print(f"  {state} {cls:22} {len(g):6,} edges {_km(g):8.1f} km  {why}")
    for name, frame in (("accepted on a named class", table[table["highway"].isin(NAMED)
                                                            & (table["rule"] != "unpaved")]),
                        ("refused on a named class (names disagree)", refused)):
        print(f"{name}: {len(frame):,} edges, {_km(frame):.1f} km")
        for _, r in frame.sort_values("length_m", ascending=False).iterrows():
            print(f"  {r['state']} {r['rule']:8} {r['highway']:14} {r['length_m']:7.0f} m "
                  f"cov {r['coverage']:.2f}  osm '{r['name']}'  state '{r['state_name']}'")


if __name__ == "__main__":
    if sys.argv[1] == "fetch":
        fetch(sys.argv[2], sys.argv[3:] or None)
    elif sys.argv[1] == "build":
        main(*sys.argv[2:5])
    else:
        sys.exit(__doc__)
