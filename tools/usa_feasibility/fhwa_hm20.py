"""Fetch FHWA Highway Statistics table HM-20 (public road length by state, rural
and urban) and write it as CSV.

Usage: python fhwa_hm20.py [year] [out.csv]
"""
import csv
import html
import re
import sys
import urllib.request

year = sys.argv[1] if len(sys.argv) > 1 else "2023"
out = sys.argv[2] if len(sys.argv) > 2 else f"fhwa_hm20_{year}_states.csv"
url = f"https://www.fhwa.dot.gov/policyinformation/statistics/{year}/hm20.cfm"
page = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                              timeout=60).read().decode("utf-8", "replace")
table = re.findall(r"<table.*?</table>", page, re.S)[0]


def cells(row):
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
            for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]


def num(s):
    return 0 if s in ("-", "") else int(s.replace(",", ""))


rows = []
# Columns: state, 8 rural (interstate ... local, total), 8 urban, grand total.
for row in re.findall(r"<tr.*?</tr>", table, re.S)[2:]:
    c = cells(row)
    if len(c) != 18 or c[0] in ("U.S. Total", "Grand Total", "Puerto Rico"):
        continue
    rows.append({"state": c[0], "rural_mi": num(c[8]), "urban_mi": num(c[16]),
                 "total_mi": num(c[17]), "rural_local_mi": num(c[7]),
                 "urban_local_mi": num(c[15])})
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} states + DC -> {out}; US total {sum(r['total_mi'] for r in rows):,} mi")
