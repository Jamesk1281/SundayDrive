"""State DOT road-class layers, the contiguous 48 + DC: a survey, not an integration.

state_roads.py needed one bespoke ArcGIS integration per New England state
(SOURCES, line 148). This asks, for every state, whether a public layer like
those exists at all, and what it would offer, in three steps:

  search   ArcGIS Online's catalogue, once or twice per state, for feature and
           map services titled like a statewide road network (road inventory,
           centerline, all roads, LRS, functional class, surface). Catalogue
           search finds what a DOT has registered there; a state that hosts
           only on its own server and never registers it is missed, so a miss
           is recorded as "not found by catalogue search", never "not public";
  probe    each candidate service's line layers: name, field list, licence
           text, and `returnCountOnly`, one request at a time;
  flag     the fields that carry what the pipeline would read: road class,
           maintenance or legal status, surface, ownership or jurisdiction,
           and seasonal restrictions.

The output is candidates, ranked by how many of those field kinds a layer has
and how many features it holds; the findings table is chosen from it by hand.

Usage: python -I state_dot_survey.py <out.json>
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import get_json  # noqa: E402

STATES = {
    "AL": "Alabama", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
SEARCH = "https://www.arcgis.com/sharing/rest/search"
TITLE = re.compile(r"road ?inventory|roadway inventory|all ?roads|centerline|center line|"
                   r"road network|roadway network|\bLRS\b|linear referenc|functional class|"
                   r"surface type|public roads|local roads|county roads|roadways?\b|"
                   r"\broads\b|road class|legislative class", re.IGNORECASE)
KINDS = {
    "class": re.compile(r"func|f_?system|fclass|road_?class|rd_?class|legis|aot_?class|"
                        r"highway_?class|hwy_?class|route_?type|rte_?type|class", re.I),
    "maintenance": re.compile(r"maint|status|accept|legis|aot_?class", re.I),
    "surface": re.compile(r"surf|pave", re.I),
    "ownership": re.compile(r"owner|juris|govt|agency|admin", re.I),
    "seasonal": re.compile(r"season|winter|closure", re.I),
    "speed": re.compile(r"speed|mph", re.I),
}


def search(q):
    status, data, _ = get_json(SEARCH, {"q": q, "num": 25, "f": "json",
                                        "sortField": "numViews", "sortOrder": "desc"})
    return data.get("results", []) if data else []


def statewide(cand, ab, name):
    """Whether a catalogue hit could be a statewide layer: a DOT or state
    agency's account or host, or the state's name in the title. City and
    county servers are skipped; several never answer, and none is statewide."""
    text = f"{cand['owner']} {cand['url']} {cand['title']}".lower()
    if re.search(r"county|city|town|village|borough|parish|\bco\.", text):
        return False
    return bool(re.search(r"dot|transport|highway|\bstate\b|gov|" + ab.lower() + r"\b|"
                          + re.escape(name.lower()), text))


def probe_service(url):
    """Line layers of one service: name, fields, kinds, count, licence."""
    out = []
    status, meta, _ = get_json(url, {"f": "json"}, timeout=20, tries=1)
    if status != 200 or not meta or "error" in meta:
        return [{"url": url, "error": f"HTTP {status}"}]
    layers = meta.get("layers") or ([{"id": None}] if meta.get("geometryType") else [])
    for lay in layers[:6]:
        lurl = url if lay["id"] is None else f"{url}/{lay['id']}"
        status, lm, _ = get_json(lurl, {"f": "json"}, timeout=20, tries=1)
        if status != 200 or not lm or "error" in lm:
            continue
        if lm.get("geometryType") != "esriGeometryPolyline":
            continue
        fields = [f["name"] for f in lm.get("fields", [])]
        kinds = sorted(k for k, rx in KINDS.items() if any(rx.search(f) for f in fields))
        cnt = None
        if kinds:
            status, cnt, _ = get_json(lurl + "/query", {"where": "1=1",
                                                        "returnCountOnly": "true",
                                                        "f": "json"}, timeout=30, tries=1)
        out.append({"url": lurl, "name": lm.get("name"), "fields": fields, "kinds": kinds,
                    "count": (cnt or {}).get("count"),
                    "copyright": (lm.get("copyrightText") or "")[:300]})
    return out


def main():
    out_path = Path(sys.argv[1])
    res = json.loads(out_path.read_text()) if out_path.exists() else {}
    for ab, name in STATES.items():
        if ab in res:
            continue
        seen, cands = set(), []
        for q in (f'"{name}" (DOT OR "Department of Transportation") (roads OR roadway OR '
                  f'centerline OR inventory OR LRS) (type:"Feature Service" OR '
                  f'type:"Map Service")',
                  f'"{name}" ("road inventory" OR "roadway inventory" OR "all roads" OR '
                  f'"road centerline" OR "functional class") (type:"Feature Service" OR '
                  f'type:"Map Service")'):
            for r in search(q):
                url = (r.get("url") or "").rstrip("/")
                if not url or url in seen or not TITLE.search(r.get("title", "")):
                    continue
                seen.add(url)
                c = {"title": r["title"], "owner": r.get("owner"), "url": url,
                     "licence": re.sub(r"<[^>]+>", " ", r.get("licenseInfo") or "")[:300],
                     "access": r.get("accessInformation")}
                if statewide(c, ab, name):
                    cands.append(c)
        probed = []
        for c in cands[:4]:
            for lay in probe_service(c["url"]):
                probed.append({**c, **lay})
        probed.sort(key=lambda p: (-len(p.get("kinds", [])), -(p.get("count") or 0)))
        res[ab] = {"state": name, "candidates": probed[:8]}
        best = probed[0] if probed else {}
        print(ab, len(cands), "services;", best.get("name"), best.get("count"),
              best.get("kinds"), flush=True)
        out_path.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
