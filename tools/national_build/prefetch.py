"""Download every WorldCover tile the regions will read, before any region runs.

Usage: prefetch.py <config.json> [region ...]

landcover.py downloads a missing tile to `<tile>.tif.part` and renames it. Two
regions built at once that both need a tile would write that same .part file
together. So build.py's regions only ever read tiles this has already put in the
cache, <work>/raw/worldcover, each written under its own temporary name.

A 404 is a cell WorldCover leaves out because it is all ocean, which landcover.py
handles itself (`tile_absent`); anything else is retried and then fails.
"""
import math
import os
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pipeline"))
sys.path.insert(0, str(HERE))
import regions  # noqa: E402
from build import load_config  # noqa: E402
from landcover import TILE_DEG, TILE_URL, tile_name  # noqa: E402

PAD_DEG = 0.05  # more than landcover.py's ~1 km desert box reaches


def cells(region: regions.Region) -> set[str]:
    w, s, e, n = region.bbox
    rows = range(math.floor((90 - (n + PAD_DEG)) / TILE_DEG), math.floor((90 - (s - PAD_DEG)) / TILE_DEG) + 1)
    cols = range(math.floor((w - PAD_DEG + 180) / TILE_DEG), math.floor((e + PAD_DEG + 180) / TILE_DEG) + 1)
    return {tile_name(r, c) for r in rows for c in cols}


def fetch(tile: str, cache: Path) -> str:
    p = cache / f"{tile}.tif"
    if p.exists() and p.stat().st_size > 0:
        return "cached"
    tmp = cache / f".{tile}.{os.getpid()}.prefetch"
    for attempt in range(4):
        try:
            with requests.get(TILE_URL.format(tile=tile), timeout=120, stream=True) as r:
                if r.status_code == 404:
                    return "absent"
                if r.status_code == 200:
                    with open(tmp, "wb") as f:
                        for block in r.iter_content(1 << 20):
                            f.write(block)
                    os.replace(tmp, p)
                    return "fetched"
        except requests.RequestException:
            pass
        time.sleep(2 * 2 ** attempt)
    tmp.unlink(missing_ok=True)
    raise SystemExit(f"could not fetch {tile}")


def main(config: str, only: list[str]):
    c = load_config(config)
    cache = Path(c["work"]) / "raw" / "worldcover"
    cache.mkdir(parents=True, exist_ok=True)
    wanted = sorted(set().union(*(cells(r) for r in regions.load(c["states"], only or None))))
    t0 = time.time()
    status = {}
    for i, tile in enumerate(wanted):
        status[tile] = fetch(tile, cache)
        print(f"  {i + 1}/{len(wanted)} {tile} {status[tile]} ({time.time() - t0:.0f}s)", flush=True)
    by = {s: sum(v == s for v in status.values()) for s in ("cached", "fetched", "absent")}
    print(f"{len(wanted)} cells: {by}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
