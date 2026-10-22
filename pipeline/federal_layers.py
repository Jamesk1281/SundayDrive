"""Fetch the two federal road layers that date winter closures OSM leaves out.

OpenStreetMap leaves most park and forest roads that close for winter untagged:
Teton Park Road, Glacier Point Road, Yellowstone's Grand Loop, Kuwohi Road, and
819 of the 821 km of seasonal forest road in the graph in one Colorado forest
(docs/us-map-data-findings.md, §4 and §6.4). Two agencies publish what OSM is
missing:

  mvum_roads.parquet   the Forest Service's Motor Vehicle Use Map roads, with
                       the dates each is open to passenger vehicles
                       (`passengervehicle_datesopen`, e.g. `04/01-11/30`) and
                       to high-clearance vehicles, and which other vehicle
                       classes each is designated for (truck, bus, motorhome,
                       4WD and 2WD over 50 inches, OHVs), which decide
                       whether a car may use it at all
                       (docs/national-data-decisions.md, D5);
  nps_roads.parquet    NPS Public Roads, with `SEASONAL` (Yes, No, Unknown)
                       and the free-text `SEASDESC`.

Both are written as GeoParquet in WGS84, with the attributes closures.py reads
(winter_closures.py) and the names, kept for reports only: the join is by
geometry, never by name. Beside them, `federal_layers.json` records each
layer's URL, the date it was fetched, and the count the server reported, which
the fetch checks it received in full.

The contiguous 48 states and DC only, by envelope; a few Canadian park roads
inside the envelope come along and match nothing.

Network only here, so closures.py can run anywhere the files are. Run it once
per national build, before closures.py; docs/winter-closures-national.md says
when the data was last fetched.

Usage: python federal_layers.py [<out_dir>]     (default: data/raw/federal)
"""

import json
import sys
import time
from datetime import date
from pathlib import Path

import geopandas as gpd

MVUM = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MVUM_01/MapServer/1"
NPS = ("https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/"
       "NPS_Public_Roads/MapServer/0")

LAYERS = {
    "mvum_roads": (MVUM, "objectid", (
        "objectid,id,name,forestname,districtname,jurisdiction,symbol,mvum_symbol_name,"
        "seasonal,passengervehicle,passengervehicle_datesopen,highclearancevehicle,"
        "highclearancevehicle_datesopen,truck,truck_datesopen,bus,bus_datesopen,"
        "motorhome,motorhome_datesopen,fourwd_gt50inches,fourwd_gt50_datesopen,"
        "twowd_gt50inches,twowd_gt50_datesopen,other_ohv_gt50inches,atv,motorcycle,"
        "operationalmaintlevel,surfacetype,gis_miles")),
    "nps_roads": (NPS, "OBJECTID", (
        "OBJECTID,UNITCODE,UNITNAME,RDNAME,RDSTATUS,RDCLASS,RDSURFACE,SEASONAL,"
        "SEASDESC,OPENTOPUBLIC,PUBLICDISPLAY")),
}

# The contiguous 48 and DC, as tools/us_map_data/scope.py draws it.
LOWER48_BBOX = (-125.0, 24.4, -66.9, 49.5)
PAGE = 2000
PAUSE_S = 0.25
UA = "SundayDrive-pipeline/1.0 (federal_layers.py)"


def _session():
    import certifi
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = UA
    # The venv's interpreter ships no CA store of its own.
    s.verify = certifi.where()
    return s


def _get(session, url, params, tries=4):
    for attempt in range(tries):
        time.sleep(PAUSE_S)
        try:
            r = session.get(url, params=params, timeout=300)
            if r.status_code == 200:
                data = r.json()
                if "error" not in data:
                    return data
                err = data["error"]
            else:
                err = f"HTTP {r.status_code}"
        except Exception as e:      # timeouts, resets, a truncated body
            err = f"{type(e).__name__}: {e}"
        if attempt < tries - 1:
            time.sleep(2 * 2 ** attempt)
    raise SystemExit(f"{url}: {err}")


def fetch(url: str, order: str, fields: str) -> tuple[gpd.GeoDataFrame, int]:
    """Every feature of one layer inside LOWER48_BBOX, and the count the server
    said there were."""
    session = _session()
    where = {"where": "1=1", "geometry": ",".join(map(str, LOWER48_BBOX)),
             "geometryType": "esriGeometryEnvelope", "inSR": 4326,
             "spatialRel": "esriSpatialRelIntersects"}
    expected = _get(session, url + "/query",
                    {**where, "returnCountOnly": "true", "f": "json"})["count"]
    frames, offset = [], 0
    while offset < expected:
        data = _get(session, url + "/query", {
            **where, "outFields": fields, "outSR": 4326, "f": "geojson",
            "orderByFields": order, "resultOffset": offset,
            "resultRecordCount": PAGE})
        feats = data.get("features", [])
        if not feats:
            break
        frames.append(gpd.GeoDataFrame.from_features(feats, crs=4326))
        offset += len(feats)
        print(f"  {offset:,} of {expected:,}", flush=True)
    import pandas as pd
    frame = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=4326)
    frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty]
    return frame.drop_duplicates(order).reset_index(drop=True), expected


def main(out_dir: str = None):
    out = Path(out_dir or Path(__file__).resolve().parent.parent / "data/raw/federal")
    out.mkdir(parents=True, exist_ok=True)
    record = {}
    for name, (url, order, fields) in LAYERS.items():
        t0 = time.time()
        print(f"{name}: {url}", flush=True)
        frame, expected = fetch(url, order, fields)
        got = frame[order].nunique()
        # A short read is a layer half-fetched, which would leave roads open
        # with nothing to say so; better no file than that one.
        if got < expected:
            raise SystemExit(f"{name}: received {got:,} of the {expected:,} features "
                             "the server reported; not writing it")
        frame.to_parquet(out / f"{name}.parquet", index=False)
        record[name] = {"url": url, "fetched": date.today().isoformat(),
                        "features": int(got), "server_count": int(expected),
                        "envelope": LOWER48_BBOX}
        print(f"{name}: {got:,} features in {time.time() - t0:.0f}s", flush=True)
    (out / "federal_layers.json").write_text(json.dumps(record, indent=1) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:2])
