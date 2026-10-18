"""Build a router pack: the graph in a processed directory, as flat arrays.

    python pack.py <processed_dir> <pack_dir> [--region "the contiguous United States"]

The server maps a pack instead of building the graph at startup
(SUNDAYDRIVE_PACK, server/app.py), which is what lets the US graph run on the
box at all: built in place, the router would need far more memory than the box
has (docs/router-at-us-scale.md, "The pack").

Rebuild the pack whenever any file the router reads changes: the graph, the
restrictions, the access layer, or any closures.py table. A pack records a
fingerprint of each, and the server refuses a pack that no longer matches the
directory beside it.

Prints the build's time and peak memory, and the pack's size on disk.
"""

import argparse
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from router import Router  # noqa: E402


def peak_gb():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Bytes on macOS, kilobytes on Linux.
    return rss / 1e9 if sys.platform == "darwin" else rss / 1e6


def main():
    p = argparse.ArgumentParser()
    p.add_argument("processed_dir")
    p.add_argument("pack_dir")
    p.add_argument("--region", help="what the graph covers, for the server's messages")
    args = p.parse_args()
    t = time.perf_counter()
    router = Router(args.processed_dir)
    built = time.perf_counter() - t
    print(f"built in {built:.0f} s, peak {peak_gb():.2f} GB", flush=True)
    t = time.perf_counter()
    router.save_pack(args.pack_dir, region=args.region)
    size = sum(f.stat().st_size for f in Path(args.pack_dir).iterdir())
    print(f"wrote {args.pack_dir} in {time.perf_counter() - t:.0f} s: "
          f"{size / 1e9:.2f} GB, {router.n_real:,} nodes, {router.m:,} edges, "
          f"{router.n:,} routing nodes; peak {peak_gb():.2f} GB", flush=True)


if __name__ == "__main__":
    main()
