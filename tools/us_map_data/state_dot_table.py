"""The state DOT survey's table: one row per state, chosen by hand from the
candidates state_dot_survey.py found.

CHOSEN names the best statewide line layer for each state, or None with the
reason. The choice reads the candidate list, not a guess: the layer must be
published by the state (its DOT, GIS office or 911 board), cover the whole
state, and be a road network rather than one county's. Fields, counts and
licence text come from the probe, so nothing here is typed in except the
choice itself. Maine's two layers are the ones pipeline/state_roads.py already
reads, which the catalogue search did not find (it returned Main Roads Western
Australia); they are probed here.

Usage: python -I state_dot_table.py <state_dot_survey_raw.json> <out.csv>
"""

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import get_json  # noqa: E402
from state_dot_survey import KINDS, STATES  # noqa: E402

# (url, scope) per state; scope says what the layer covers.
CHOSEN = {
    "AL": ("https://services.arcgis.com/LZzQi3xDiclG6XvQ/arcgis/rest/services/September_8th_2016_Highway_Functional_Classification/FeatureServer/0", "functional class only, 2016"),
    "AZ": ("https://services6.arcgis.com/clPWQMwZfdWn4MQZ/arcgis/rest/services/ADOT_Highway_Performance_Monitoring_System_(HPMS)_2022_Data/FeatureServer/5", "HPMS 2022 pavement layer, statewide"),
    "AR": ("https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Transportation/FeatureServer/18", "statewide all roads (state GIS office)"),
    "CA": ("https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/CRS_Functional_Classification/FeatureServer/0", "statewide public roads, functional class only"),
    "CO": ("https://dtdapps.codot.gov/server/rest/services/Webapps/open_data_sde/FeatureServer/11", "state highways only"),
    "CT": ("https://services1.arcgis.com/FCaUeJ5SOVtImake/arcgis/rest/services/CTDOT_Historical_State_Routes_and_Local_Roads/FeatureServer/0", "state routes and local roads (historical)"),
    "DE": ("https://enterprise.firstmap.delaware.gov/arcgis/rest/services/Transportation/DE_Roadways_Main/FeatureServer/2", "statewide road inventory"),
    "DC": ("https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Transportation_WebMercator/MapServer/48", "district-wide"),
    "FL": (None, "not found by catalogue search"),
    "GA": (None, "not found by catalogue search (city layers only)"),
    "ID": ("https://gisp.itd.idaho.gov/server/rest/services/GDWarehouse/LocalRoadInventory/FeatureServer/1", "local road inventory"),
    "IL": ("https://services2.arcgis.com/aIrBD8yn1TDTEXoz/arcgis/rest/services/Roads2017/FeatureServer/0", "statewide all roads, 2017"),
    "IN": ("https://gisdata.in.gov/server/rest/services/Hosted/Road_Centerlines_of_Indiana_Current/FeatureServer/0", "statewide centerlines"),
    "IA": ("https://gis.iowadot.gov/agshost/rest/services/RAMS/Road_Network/FeatureServer/0", "statewide road network"),
    "KS": ("https://services6.arcgis.com/7XhimSpf8B7lHIMy/arcgis/rest/services/RoadCenterline_NG911_GCS/FeatureServer/0", "statewide NG911 centerlines"),
    "KY": ("https://maps.kytc.ky.gov/arcgis/rest/services/Apps/FunctionalClass/MapServer/5", "functional class layers, one per class"),
    "LA": ("https://maps.dotd.la.gov/road/rest/services/Roads_and_Highways_OpenData/FeatureServer/49", "statewide roadways"),
    "ME": ("https://arcgisserver.maine.gov/arcgis/rest/services/mdot/MaineDOT_LRS/MapServer/1", "all public roads (plus layer 915, private roads); what state_roads.py reads"),
    "MD": ("https://services.arcgis.com/njFNhDsUCentVYJW/arcgis/rest/services/MDOT_SHA_Roadway_Functional_Classification/FeatureServer/0", "functional class only"),
    "MA": ("https://gis.massdot.state.ma.us/arcgis/rest/services/Roads/RoadInventoryYearEndFiles/FeatureServer/10", "statewide road inventory (state_roads.py reads the MassGIS copy)"),
    "MI": ("https://services2.arcgis.com/67lKNkQ2TO1I3lhR/arcgis/rest/services/MDOT_RH_2026/FeatureServer/0", "statewide roads and highways LRS"),
    "MN": ("https://webgis.dot.state.mn.us/65agsf1/rest/services/sdw_incdt/FUNCTIONAL_CLASS/FeatureServer/0", "statewide, functional class"),
    "MS": (None, "not found by catalogue search"),
    "MO": (None, "not found by catalogue search"),
    "MT": (None, "candidate found (functional class routes) but its server returned HTTP 503"),
    "NE": ("https://gis.ne.gov/Enterprise/rest/services/Street_Centerlines/FeatureServer/0", "statewide street centerlines"),
    "NV": ("https://arcgis.water.nv.gov/arcgis/rest/services/BaseLayers/NDOT_Roads/FeatureServer/2", "NDOT roads mirrored by the state water office (major, local, unimproved)"),
    "NH": ("https://nhgeodata.unh.edu/hosting/rest/services/Hosted/GV_BaseLayers/FeatureServer/18", "statewide NHDOT roads (carries winter maintenance)"),
    "NJ": ("https://services2.arcgis.com/XVOqAjTOJ5P6ngMu/arcgis/rest/services/Tran_road/FeatureServer/0", "statewide roads (state GIS office)"),
    "NM": (None, "only per-class E911 extracts found; NMDOT's NM911 centerline layer did not answer a count"),
    "NY": ("https://gisportalny.dot.ny.gov/hostingny/rest/services/Roadways/RoadwayData/FeatureServer/0", "statewide roadway inventory"),
    "NC": ("https://gis11.services.ncdot.gov/arcgis/rest/services/NCDOT_StateMaintainedRoadsQtr/MapServer/0", "state-maintained roads (most of NC's network)"),
    "ND": (None, "only a state and federal roads layer, which did not answer a count"),
    "OH": (None, "not found by catalogue search (county layers only)"),
    "OK": ("https://services6.arcgis.com/RBtoEUQ2lmN0K3GY/arcgis/rest/services/Local_Roadways/FeatureServer/0", "local roads (with a separate state roadways layer)"),
    "OR": ("https://gis.odot.state.or.us/arcgis1006/rest/services/transgis/catalog/MapServer/164", "statewide all public roads, ownership only"),
    "PA": (None, "not found by catalogue search (county layers only)"),
    "RI": ("https://services2.arcgis.com/S8zZg9pg23JUEexQ/arcgis/rest/services/RIDOT_Roads_2016/FeatureServer/0", "statewide RIDOT roads, 2016"),
    "SC": (None, "only a regional council's statewide copy with no class fields"),
    "SD": ("https://sdgis.sd.gov/dot/rest/services/TIM/DOT_Local_Roads_viewer/FeatureServer/0", "non-state-trunk (local) roads"),
    "TN": ("https://services1.arcgis.com/YuVBSS7Y1of2Qud1/arcgis/rest/services/Tennessee_NG911_Road_Centerlines/FeatureServer/1", "statewide NG911 centerlines"),
    "TX": ("https://services.arcgis.com/KTcxiTD9dsQw4r7Z/arcgis/rest/services/TxDOT_Roadway_Inventory/FeatureServer/0", "statewide roadway inventory"),
    "UT": ("https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/UtahRoads/FeatureServer/0", "statewide roads (state GIS office)"),
    "VT": ("https://maps.vtrans.vermont.gov/arcgis/rest/services/Master/General/FeatureServer/39", "statewide all roads (state_roads.py reads s1111_rds)"),
    "VA": ("https://services.arcgis.com/p5v98VHDX9Atv3l7/arcgis/rest/services/LRS_Route_Master/FeatureServer/0", "statewide LRS routes"),
    "WA": ("https://data.wsdot.wa.gov/arcgis/rest/services/Shared/WSDOTPublicRoads/MapServer/5", "statewide local public roads"),
    "WV": ("https://services2.arcgis.com/xLpB90lOmCXYDAWo/arcgis/rest/services/National_Functiononal_Classificiation/FeatureServer/23", "functional class only"),
    "WI": ("https://services5.arcgis.com/0pgGLzT0Nh7FVjon/arcgis/rest/services/WI_Local_Roads_Flood_Damage_Assessment_Snapshot/FeatureServer/1", "local road network snapshot"),
    "WY": (None, "not found by catalogue search (a TIGER copy only)"),
}


def probe(url):
    status, lm, _ = get_json(url, {"f": "json"}, timeout=30, tries=1)
    if status != 200 or not lm or "error" in lm:
        return None
    if lm.get("layers") and not lm.get("fields"):        # a service: take its first line layer
        for lay in lm["layers"]:
            got = probe(f"{url}/{lay['id']}")
            if got and got["geometry"] == "esriGeometryPolyline":
                return got
        return None
    status, cnt, _ = get_json(url + "/query", {"where": "1=1", "returnCountOnly": "true",
                                               "f": "json"}, timeout=60, tries=1)
    return {"url": url, "name": lm.get("name"), "geometry": lm.get("geometryType"),
            "fields": [f["name"] for f in lm.get("fields", [])],
            "count": (cnt or {}).get("count"),
            "copyright": (lm.get("copyrightText") or "")[:200]}


def main():
    raw = json.load(open(sys.argv[1]))
    rows = []
    for ab, (url, scope) in CHOSEN.items():
        row = {"state": ab, "scope": scope, "layer": "", "url": url or "", "count": ""}
        for k in KINDS:
            row[f"{k}_fields"] = ""
        row["licence"] = ""
        if url:
            cand = next((c for c in raw.get(ab, {}).get("candidates", [])
                         if c.get("url") == url), None)
            got = cand if cand and cand.get("count") is not None else probe(url)
            if got:
                row["layer"] = got.get("name") or ""
                row["url"] = got.get("url", url)
                row["count"] = got.get("count") or ""
                for k, rx in KINDS.items():
                    row[f"{k}_fields"] = ";".join(f for f in got.get("fields", [])
                                                  if rx.search(f))[:120]
                lic = (cand or {}).get("licence") or got.get("copyright") or ""
                row["licence"] = re.sub(r"\s+", " ", lic).strip()[:160]
            else:
                row["scope"] += "; did not answer when probed for this table"
        rows.append(row)
        print(ab, row["count"], row["layer"], flush=True)
    with open(sys.argv[2], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
