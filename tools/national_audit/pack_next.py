"""tools/us_scale_router/pack.py, writing only the arrays that changed.

    python pack_next.py <processed_dir> <pack_dir> <old_pack_dir> [--region "..."]

A closures change leaves most of a pack's arrays byte-identical: the geometry,
grids, text and scores. It rewrites the slot-indexed ones only when a through
barrier comes or goes, since that changes the turn-restriction expansion
(26 of 92 arrays, about 8.5 GB, for the ford change of 2026-10-20;
docs/review-fixes-data.md, "The pack"). The disk had about 12 GB
free on 2026-10-20 and a national pack is about 12 GB, so this runs pack.py's
own `main` with `np.save` wrapped: an array equal (dtype, shape and every
element) to the one of the same name in <old_pack_dir> is written as an APFS
clone of that file (`cp -c`), which takes no space until either copy is
written to and is otherwise an ordinary, independent file. Every other array,
objects.pickle and manifest.json are written as pack.py writes them. The pack
that results is the one pack.py would write, file for file.

Nothing in <old_pack_dir> is written. Prints which arrays were written new.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "us_scale_router"))
sys.path.insert(0, str(ROOT / "pipeline"))

_save = np.save
written, cloned = [], []


def main():
    args = sys.argv[1:]
    old = Path(args.pop(2))
    out = Path(args[1]).resolve()
    if out == old.resolve():
        raise SystemExit("the new pack must not be the old one")

    def save(file, arr, *a, **kw):
        path = Path(file)
        before = old / path.name
        arr = np.asanyarray(arr)
        if before.exists() and path.resolve().parent == out:
            prev = np.load(before, mmap_mode="r")
            if prev.dtype == arr.dtype and prev.shape == arr.shape and np.array_equal(prev, arr):
                if path.exists():
                    path.unlink()
                subprocess.run(["cp", "-c", str(before), str(path)], check=True)
                cloned.append(path.name)
                return
        written.append(path.name)
        _save(file, arr, *a, **kw)

    np.save = save
    import pack
    sys.argv = ["pack.py", *args]
    pack.main()
    print(f"written new ({len(written)}): {', '.join(sorted(written))}")
    print(f"cloned from {old} ({len(cloned)})")


if __name__ == "__main__":
    main()
