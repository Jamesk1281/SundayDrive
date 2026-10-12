"""Exact size of every US state extract on Geofabrik, by HEAD, never by download.

Reads the north-america/us.html index for the list of sub-regions and the
rounded size it prints, then sends one HEAD per state of the contiguous 48 and
DC (scope.py) for the exact Content-Length and Last-Modified. Also records the
history of Geofabrik's US file that the index lists, which gives the growth rate
a rebuild cadence has to plan for.

Usage: python -I geofabrik_sizes.py <us.html> <out_dir>
Writes osm_extract_sizes.csv and osm_us_history.csv.
"""

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import head  # noqa: E402
from scope import OUT_SLUGS  # noqa: E402

BASE = "https://download.geofabrik.de/north-america/"

html = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

subs = re.findall(
    r'<a href="us/([a-z-]+)\.html">([^<]+)</a>.*?\(([\d.]+)&nbsp;(MB|GB|KB)\)', html, re.S)
history = re.findall(
    r'<a href="(us-(\d{6})\.osm\.pbf)">[^<]+</a></td><td class="subright">([^<]+)</td>'
    r'<td class="subright">(\d+)</td>', html)

rows = []
for slug, name, size, unit in subs:
    if slug in OUT_SLUGS:
        continue
    url = f"{BASE}us/{slug}-latest.osm.pbf"
    status, length, hdrs = head(url)
    rows.append({
        "slug": slug, "name": name.strip(),
        "scope": "in",
        "index_size": f"{size} {unit}",
        "head_status": status,
        "bytes": length if length is not None else "",
        "last_modified": hdrs.get("Last-Modified", ""),
    })
    print(f"{name:24s} {status} {length}", flush=True)

with open(out / "osm_extract_sizes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
with open(out / "osm_us_history.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file", "yymmdd", "timestamp", "bytes"])
    w.writerows(history)

inside = [r for r in rows if r["scope"] == "in"]
total = sum(int(r["bytes"]) for r in inside if r["bytes"] != "")
print(f"{len(inside)} extracts (the contiguous 48 + DC), {total:,} bytes in all")
