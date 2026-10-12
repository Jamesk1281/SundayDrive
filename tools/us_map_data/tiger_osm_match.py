"""TIGER/Line 2026 roads in sample counties against OSM, by MTFCC class.

TIGER's MTFCC says what the Census thinks a road is. Two classes bear on a car
app and on nothing OSM-derived the pipeline reads:
  S1500  vehicular trail (4WD): "an unpaved dirt trail where a four-wheel
         drive vehicle is required";
  S1740  private road for service vehicles: logging, oil fields, ranches.
S1400 (local neighbourhood road) is matched too, as the control.

Each county's ROADS file (a few hundred KB) is fetched into its own directory,
and its lines are matched to OSM by osm_match.py's sampling rule. The result
says, per class and per county, how many TIGER km OSM has as a road graph.py
keeps, as a track it leaves out, or not at all, and for the km it keeps, which
access and roughness tags OSM carries there.

Usage: python -I tiger_osm_match.py <repo_pipeline_dir> <state.osm.pbf> <dl_dir>
                                    <out.json> <county_fips> [<county_fips> ...]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import request  # noqa: E402
from osm_match import SAMPLE_M, TOLERANCE_M, matcher, osm_ways  # noqa: E402

URL = "https://www2.census.gov/geo/tiger/TIGER2026/ROADS/tl_2026_{fips}_roads.zip"
CLASSES = {"S1500": "S1500 4WD trail", "S1740": "S1740 private service road",
           "S1400": "S1400 local road (control)"}


def main():
    import geopandas as gpd
    pbf, dl, out = sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
    counties = sys.argv[5:]
    frames = []
    for fips in counties:
        d = dl / f"tiger_{fips}"
        d.mkdir(parents=True, exist_ok=True)
        z = d / f"tl_2026_{fips}_roads.zip"
        if not z.exists():
            status, _, body = request(URL.format(fips=fips), timeout=120)
            if status != 200:
                raise SystemExit(f"{fips}: HTTP {status}")
            z.write_bytes(body)
        g = gpd.read_file(f"zip://{z}")
        g["county"] = fips
        frames.append(g[g["MTFCC"].isin(CLASSES)])
        print(fips, len(g), "segments,", int(g["MTFCC"].isin(CLASSES).sum()), "in the classes",
              flush=True)
    import pandas as pd
    t = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs).to_crs(4326)
    w, s, e, n = t.total_bounds
    ways = osm_ways(pbf, (w - 0.02, s - 0.02, e + 0.02, n + 0.02))
    print(f"{len(ways)} OSM highway ways in the box", flush=True)
    match = matcher(ways)
    tab = defaultdict(float)
    for geom, cls, fips in zip(t.geometry, t["MTFCC"], t["county"]):
        for part in getattr(geom, "geoms", [geom]):
            km_each, hit = match(list(part.coords))
            label = CLASSES[cls]
            for h in hit:
                wy = ways[h] if h >= 0 else None
                kind = wy["kind"] if wy else f"no OSM way within {TOLERANCE_M:.0f} m"
                tab[(label, "total")] += km_each
                tab[(label, "coverage", kind)] += km_each
                tab[(label, "by county", fips)] += km_each
                if kind.startswith("in graph ("):
                    tab[(label, "graph access", wy["access"])] += km_each
                    tab[(label, "graph roughness", wy["rough"])] += km_each
                    if wy["cfcc"]:
                        tab[(label, "graph tiger:cfcc", wy["cfcc"][:2] + "x")] += km_each
    res = {"counties": counties, "sample_m": SAMPLE_M, "tolerance_m": TOLERANCE_M,
           "tables": {}}
    for k, v in sorted(tab.items()):
        res["tables"].setdefault(k[0], {}).setdefault(k[1], {})
        if len(k) == 2:
            res["tables"][k[0]][k[1]] = round(v, 1)
        else:
            res["tables"][k[0]][k[1]][k[2]] = round(v, 1)
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
