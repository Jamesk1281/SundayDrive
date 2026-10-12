"""USGS 3DEP seamless DEMs at US scale, by metadata only.

Two instruments, because the first disagreed with itself:
  api      the National Map's product API: every product of the 1 and 1/3
           arc-second DEMs and Alaska's 2 arc-second, summing `sizeInBytes`.
           It lists superseded versions of a cell beside the current one, and
           its paging repeats items, so cells are de-duplicated by name;
  s3       the bucket listing itself (prd-tnm, public, ListObjectsV2), under
           StagedProducts/Elevation/<res>/TIFF/current/: one GeoTIFF per
           current 1x1 degree cell, with its exact size. This is the number
           the findings use; the API's is kept to show the gap.

Usage: python -I dem3dep_survey.py <out.json>
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netutil import get_json  # noqa: E402

API = "https://tnmaccess.nationalmap.gov/api/v1/products"
DATASETS = ["National Elevation Dataset (NED) 1 arc-second",
            "National Elevation Dataset (NED) 1/3 arc-second",
            "National Elevation Dataset (NED) Alaska 2 arc-second"]
CELL = re.compile(r"([ns]\d{2}[ew]\d{3})", re.IGNORECASE)


def products(dataset):
    items, offset = [], 0
    while True:
        status, data, body = get_json(API, {"datasets": dataset, "prodFormats": "GeoTIFF",
                                            "max": 1000, "offset": offset,
                                            "outputFormat": "JSON"}, timeout=180)
        if status != 200 or not data:
            raise SystemExit(f"{dataset}: HTTP {status} {body[:200]!r}")
        items += data.get("items", [])
        total = data.get("total", 0)
        print(f"  {dataset}: {len(items)}/{total}", flush=True)
        if not data.get("items") or len(items) >= total:
            return items, total
        offset += 1000


def s3_listing(prefix):
    import xml.etree.ElementTree as ET
    from netutil import request
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    token, n, size, tifs = None, 0, 0, 0
    while True:
        url = ("https://prd-tnm.s3.amazonaws.com/?list-type=2&prefix=" + prefix
               + (f"&continuation-token={urllib.parse.quote(token)}" if token else ""))
        status, _, body = request(url, timeout=120)
        if status != 200:
            raise SystemExit(f"S3 listing {prefix}: HTTP {status}")
        root = ET.fromstring(body)
        for c in root.findall("s3:Contents", ns):
            key = c.find("s3:Key", ns).text
            n += 1
            if key.endswith(".tif"):
                tifs += 1
                size += int(c.find("s3:Size", ns).text)
        if root.find("s3:IsTruncated", ns).text != "true":
            return {"objects": n, "tifs": tifs, "tif_bytes": size}
        token = root.find("s3:NextContinuationToken", ns).text


if __name__ == "__main__":
    import urllib.parse
    out = {"s3_current": {}}
    for res in ("1", "13", "2"):
        out["s3_current"][res] = s3_listing(f"StagedProducts/Elevation/{res}/TIFF/current/")
        print("s3", res, out["s3_current"][res], flush=True)
    for ds in DATASETS:
        items, total = products(ds)
        cells = {}
        for it in items:
            m = CELL.search(it.get("downloadURL", "") or it.get("title", ""))
            key = m.group(1).lower() if m else it.get("title")
            prev = cells.get(key)
            if prev is None or (it.get("publicationDate") or "") > (prev.get("publicationDate") or ""):
                cells[key] = it
        size = sum(int(c.get("sizeInBytes") or 0) for c in cells.values())
        out[ds] = {"products_listed": total, "cells": len(cells), "bytes_current": size,
                   "bytes_all_listed": sum(int(i.get("sizeInBytes") or 0) for i in items),
                   "example": next(iter(cells.values())).get("downloadURL") if cells else None}
        print(ds, out[ds], flush=True)
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
