"""TIGER/Line 2026 road files at national scale, from the Census directory listings.

The ROADS directory holds one zip per county (all road classes, MTFCC
included); PRISECROADS one per state (primary and secondary only). Sizes come
from the Apache index pages, which round to K or M, so the sum carries up to
half a unit of rounding per file; no file is downloaded.

Usage: python -I tiger_sizes.py <ROADS.html> <PRISECROADS.html> <out.csv>
"""

import csv
import re
import sys

UNIT = {"K": 1e3, "M": 1e6, "G": 1e9, "": 1.0}
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from scope import OUT_FIPS as NOT_IN_SCOPE  # noqa: E402


def files(path, pattern):
    html = open(path).read()
    rx = re.compile(pattern + r'">[^<]+</a></td><td align="right">([^<]+?)\s*</td>'
                    r'<td align="right">\s*([\d.]+)([KMG]?)</td>')
    return [(m.group(1), m.group(2).strip(), float(m.group(3)) * UNIT[m.group(4)])
            for m in rx.finditer(html)]


roads = files(sys.argv[1], r'href="(tl_2026_(?:\d{5})_roads\.zip)')
prisec = files(sys.argv[2], r'href="(tl_2026_(?:\d{2})_prisecroads\.zip)')
rows = []
for name, date, size in roads:
    fips = re.search(r"_(\d{5})_", name).group(1)
    if fips[:2] not in NOT_IN_SCOPE:
        rows.append({"file": name, "state_fips": fips[:2], "date": date,
                     "bytes_approx": int(size)})
for name, date, size in prisec:
    fips = re.search(r"_(\d{2})_", name).group(1)
    if fips not in NOT_IN_SCOPE:
        rows.append({"file": name, "state_fips": fips, "date": date, "bytes_approx": int(size)})
with open(sys.argv[3], "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
inr = [r for r in rows if r["file"].endswith("_roads.zip") and r["state_fips"] not in NOT_IN_SCOPE]
inp = [r for r in rows if r["file"].endswith("prisecroads.zip") and r["state_fips"] not in NOT_IN_SCOPE]
print(f"ROADS: {len(inr)} county files in the contiguous 48 + DC, "
      f"{sum(r['bytes_approx'] for r in inr) / 1e9:.2f} GB (rounded sizes); "
      f"PRISECROADS: {len(inp)} files, {sum(r['bytes_approx'] for r in inp) / 1e9:.3f} GB")
