"""Terrarium at US scale: how many z11 tiles, how many bytes, how many corrupt.

Three steps, each writing a small CSV:

  tiles   z11 tiles per state, from the Census 2023 cartographic outlines
          (1:500k): every tile the outline touches, and every tile in the
          state's bounding box, which is what elevation.py fetches for a region
          today (its BBOX is one rectangle). The box's mosaic size is priced at
          the 37 bytes per pixel the review measured on Colorado's peak.
  head    a stratified random sample of each state's outline tiles, sized by
          HEAD Content-Length, never downloaded. The national total is the sum
          over states of tiles x sample mean, with its standard error.
  decode  a random subset of the sample, fetched into memory, decoded and
          dropped; nothing is written to disk. Each tile is classed by its own
          terrain and run through the corruption detector below.

The detector (`defects`) has two parts:
  - out of band: a pixel outside elevation.py's -11,000..9,000 m band, which
    elevation.py already masks;
  - residue: a pixel that survives the band but, on the ocean-clamped
    elevation elevation.py's relief filter reads, departs from the median of
    its valid 7x7 neighbours by more than RESIDUE_M, or by more than SPIKE_MIN_M
    and SPIKE_SPREAD times the neighbours' own robust spread. The first test is
    the fringe of mid-range values around Colorado's out-of-band blocks (-639 m
    in 2,500 m terrain) and its column of exact-0 m pixels; the second is the
    150-870 m pixels on New England's sea-level shores, which 500 m misses. It
    fires on none of 21 steep, deep-lake and below-sea-level control tiles.
Every residue is also priced in what it costs score.py: the relief it adds in
its own window, after the ocean clamp elevation.py applies, and the pixels
whose relief component (relief / RELIEF_FULL, clipped) rises by 0.1 or more,
which is the only part a mountain tile already at the cap cannot show.

A fifth step, `rates`, turns the decode sample into national estimates: each
state's sample is weighted by its share of the outline tiles, and the standard
error is the stratified binomial one. It also gives the national bytes from the
HEAD sample the same way. The full regional
censuses (the review's Colorado cache, data/raw/terrain for New England) are
reported beside it, not pooled into it, because a census of one coast is not a
sample of the country.

The committed samples (results/terrarium_head_sample.csv, _decode_sample.csv)
were drawn from a wider frame, and the rows outside scope.py's states were
dropped afterwards, which leaves every in-scope state's sample exactly as drawn.
A re-run now draws a different sample of the same design.

Usage: python -I terrarium_survey.py tiles  <states.zip> <out_dir>
       python -I terrarium_survey.py head   <out_dir> [per_state]
       python -I terrarium_survey.py decode <out_dir> [per_state] [extra_tiles.csv] [tile_cache]
       python -I terrarium_survey.py local  <tile_dir> <label> <out_dir>
       python -I terrarium_survey.py rates  <out_dir> <out.csv> [census.csv ...]
"""

import csv
import io
from collections import defaultdict
import math
import random
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netutil  # noqa: E402
from netutil import head, request  # noqa: E402

# S3 serves these, not a government host: a short pause is polite enough.
netutil.PAUSE_S = 0.05

Z = 11
N = 2 ** Z
TILE_URL = "https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"
BYTES_PER_PX = 37          # the review's Colorado peak, elevation.py's mosaic
ELEV_MAX_M, ELEV_MIN_M = 9000.0, -11000.0
NEIGH_PX = 7               # 7x7 neighbourhood, about 400 m at mid-latitudes
RESIDUE_M = 500.0          # no real slope at 60 m pixels departs this far
SPIKE_MIN_M = 150.0        # ... and none departs this far from flat neighbours
SPIKE_SPREAD = 10.0        # times the neighbours' robust spread (1.4826 x MAD)
SPREAD_FLOOR_M = 5.0
SEED = 20261011
# Everything in the outline file outside the contiguous 48 + DC (scope.py).
from scope import OUT_ABBR, OUT_FIPS as NOT_IN_SCOPE  # noqa: E402


def lon2x(lon):
    return (lon + 180.0) / 360.0 * N


def lat2y(lat):
    lat = max(min(lat, 85.0511), -85.0511)
    r = math.radians(lat)
    return (1.0 - math.asinh(math.tan(r)) / math.pi) / 2.0 * N


def x2lon(x):
    return x / N * 360.0 - 180.0


def y2lat(y):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / N))))


def state_tiles(geom):
    """{(x, y)} of every z11 tile the geometry touches, part by part, so that
    a state in several parts is never one box spanning the gaps between them."""
    import shapely
    parts = list(getattr(geom, "geoms", [geom]))
    out = set()
    for p in parts:
        w, s, e, n = p.bounds
        xs = range(int(math.floor(lon2x(w))), int(math.floor(lon2x(e))) + 1)
        ys = range(int(math.floor(lat2y(n))), int(math.floor(lat2y(s))) + 1)
        cand = [(x, y) for x in xs for y in ys]
        boxes = shapely.box([x2lon(x) for x, _ in cand], [y2lat(y + 1) for _, y in cand],
                            [x2lon(x + 1) for x, _ in cand], [y2lat(y) for _, y in cand])
        hit = shapely.intersects(boxes, p)
        out.update(c for c, h in zip(cand, hit) if h)
    return out


def bbox_tiles(geom):
    w, s, e, n = geom.bounds
    nx = int(math.floor(lon2x(e))) - int(math.floor(lon2x(w))) + 1
    ny = int(math.floor(lat2y(s))) - int(math.floor(lat2y(n))) + 1
    return nx * ny


def cmd_tiles(states_zip, out):
    import geopandas as gpd
    st = gpd.read_file(f"zip://{states_zip}")
    st = st[~st["STATEFP"].isin(NOT_IN_SCOPE)].sort_values("NAME")
    rows, union = [], {}
    for _, r in st.iterrows():
        t = state_tiles(r.geometry)
        for c in t:
            union.setdefault(c, r["STUSPS"])
        bb = bbox_tiles(r.geometry)
        rows.append({"state": r["STUSPS"], "name": r["NAME"], "outline_tiles": len(t),
                     "bbox_tiles": bb,
                     "bbox_mosaic_gb": round(bb * 256 * 256 * BYTES_PER_PX / 1e9, 1)
                     if bb != "" else ""})
        print(f"{r['STUSPS']} {len(t):6d} outline tiles, bbox {bb}", flush=True)
    with open(out / "terrarium_tiles_by_state.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    # The union, each tile assigned to the first state (alphabetically) that
    # touches it, so a border tile is counted once. Kept in scratch only.
    with open(out / "terrarium_union_tiles.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state", "x", "y"])
        for (x, y), s in sorted(union.items()):
            w.writerow([s, x, y])
    xs = [c[0] for c in union]
    ys = [c[1] for c in union]
    print(f"union {len(union):,} tiles; their bounding box "
          f"{(max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1):,}")


def load_union(out):
    by = {}
    with open(out / "terrarium_union_tiles.csv") as f:
        for r in csv.DictReader(f):
            by.setdefault(r["state"], []).append((int(r["x"]), int(r["y"])))
    return by


def sample(by, per_state):
    rnd = random.Random(SEED)
    return {s: rnd.sample(t, min(per_state, len(t))) for s, t in sorted(by.items())}


def cmd_head(out, per_state=100):
    by = load_union(out)
    smp = sample(by, per_state)
    rows = []
    for s, tiles in smp.items():
        for x, y in tiles:
            status, size, _ = head(TILE_URL.format(z=Z, x=x, y=y))
            rows.append({"state": s, "x": x, "y": y, "status": status, "bytes": size or ""})
        print(s, len(tiles), flush=True)
    with open(out / "terrarium_head_sample.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    # Stratified estimate of the national total.
    tot, var = 0.0, 0.0
    for s, tiles in by.items():
        b = np.array([float(r["bytes"]) for r in rows if r["state"] == s and r["bytes"] != ""])
        n, Nn = len(b), len(tiles)
        tot += Nn * b.mean()
        if n > 1:
            var += Nn ** 2 * b.var(ddof=1) / n * (1 - n / Nn)
    print(f"US outline tiles {sum(len(t) for t in by.values()):,}: "
          f"{tot / 1e9:.2f} GB +/- {math.sqrt(var) / 1e9:.2f} GB (1 s.e.)")


def decode(png_bytes):
    from PIL import Image
    a = np.asarray(Image.open(io.BytesIO(png_bytes)).convert("RGB")).astype(np.float64)
    return a[..., 0] * 256.0 + a[..., 1] + a[..., 2] / 256.0 - 32768.0


def _windows(v, idx):
    """The 7x7 windows (centre included) around pixels `idx`, NaN beyond the
    tile's edge, as an (n, 49) array."""
    r = NEIGH_PX // 2
    pad = np.pad(v, r, mode="constant", constant_values=np.nan)
    off = np.arange(-r, r + 1)
    rows = idx[:, 0][:, None, None] + r + off[None, :, None]
    cols = idx[:, 1][:, None, None] + r + off[None, None, :]
    return pad[rows, cols].reshape(len(idx), -1)


def residue_mask(v):
    """(strong, residue) boolean masks for an elevation array whose band
    failures are already NaN. See `defects` for the two tests.

    The tests run on the ocean-clamped elevation, the array elevation.py's
    relief filter actually sees. Unclamped, a 30 m sea stack beside -135 m of
    bathymetry reads as a 165 m spike (Maui, tile 133/904), and garbage
    bathymetry, which the clamp makes harmless, counts as residue.

    The neighbourhood median is the 7x7 window's, centre included, from
    scipy's median filter; where the window holds a masked pixel or runs off
    the tile it is recomputed exactly, NaN-aware. The robust spread is only
    needed where a pixel already departs by more than SPIKE_MIN_M, so it is
    computed for those few."""
    from scipy import ndimage
    v = np.clip(v, 0.0, None)
    nan = np.isnan(v)
    r = NEIGH_PX // 2
    med = ndimage.median_filter(np.where(nan, 0.0, v), size=NEIGH_PX, mode="nearest")
    edge = np.zeros_like(nan)
    edge[:r, :], edge[-r:, :], edge[:, :r], edge[:, -r:] = True, True, True, True
    exact = (ndimage.binary_dilation(nan, structure=np.ones((NEIGH_PX, NEIGH_PX)))
             | edge) & ~nan
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)   # all-NaN windows
        if exact.any():
            idx = np.argwhere(exact)
            med[exact] = np.nanmedian(_windows(v, idx), axis=1)
        med[nan] = np.nan
        dev = np.abs(v - med)
        cand = ~nan & ~np.isnan(med) & (dev > SPIKE_MIN_M)
        strong = cand & (dev > RESIDUE_M)
        resid = strong.copy()
        weak = cand & ~strong
        if weak.any():
            idx = np.argwhere(weak)
            win = _windows(v, idx)
            spread = 1.4826 * np.nanmedian(np.abs(win - med[weak][:, None]), axis=1)
            resid[weak] = dev[weak] > SPIKE_SPREAD * np.maximum(spread, SPREAD_FLOOR_M)
    return strong, resid


def defects(e):
    """Out-of-band pixels, residue pixels, and what the residue does to relief.

    Returns (out-of-band px, strong residue px, residue px, relief added m,
    px whose relief component rises by 0.1 or more). A strong residue sits
    more than RESIDUE_M from the median of its valid 7x7 neighbours; a residue
    is that, or more than SPIKE_MIN_M away and more than SPIKE_SPREAD times
    the neighbours' own robust spread. The second test is what finds a 400 m
    pixel on a sea-level shore, where 500 m is far too blunt, without firing
    on a cliff, whose neighbours spread as much as the pixel departs.
    """
    from scipy import ndimage
    oob = (e > ELEV_MAX_M) | (e < ELEV_MIN_M)
    v = np.where(oob, np.nan, e)
    strong, resid = residue_mask(v)
    # What those pixels do downstream: elevation.py clamps at 0 and takes
    # max - min over a 13 px window; compare with and without them.
    added, raised = 0.0, 0
    if resid.any():
        land = np.clip(v, 0.0, None)
        lo = np.where(np.isnan(land), np.inf, land)
        hi = np.where(np.isnan(land), -np.inf, land)
        rel = ndimage.maximum_filter(hi, 13) - ndimage.minimum_filter(lo, 13)
        lo2, hi2 = lo.copy(), hi.copy()
        lo2[resid], hi2[resid] = np.inf, -np.inf
        rel2 = ndimage.maximum_filter(hi2, 13) - ndimage.minimum_filter(lo2, 13)
        with np.errstate(invalid="ignore"):
            fin = np.isfinite(rel) & np.isfinite(rel2)
            d = np.where(fin, rel - rel2, 0.0)
            comp = np.where(fin, np.clip(rel / 100.0, 0, 1) - np.clip(rel2 / 100.0, 0, 1), 0.0)
        added = float(d.max())
        raised = int((comp >= 0.1).sum())
    return int(oob.sum()), int(strong.sum()), int(resid.sum()), added, raised


def terrain_class(e):
    v = e[(e <= ELEV_MAX_M) & (e >= ELEV_MIN_M)]
    if v.size == 0:
        return "no data"
    sea = float((v <= 0).mean())
    if sea > 0.98:
        return "ocean"
    if sea > 0.02:
        return "coast"
    p1, p99 = np.percentile(v, [1, 99])
    rng = p99 - p1
    if rng > 1000:
        return "mountain"
    if rng > 250:
        return "hills"
    return "plains"


def tile_row(state, x, y, body, status):
    row = {"state": state, "x": x, "y": y, "status": status, "bytes": len(body)}
    if status != 200:
        return row
    e = decode(body)
    oob, strong, resid, added, raised = defects(e)
    v = e[(e <= ELEV_MAX_M) & (e >= ELEV_MIN_M)]
    row.update({"terrain": terrain_class(e), "min_m": round(float(v.min()), 1) if v.size else "",
                "max_m": round(float(v.max()), 1) if v.size else "", "oob_px": oob,
                "strong_residue_px": strong, "residue_px": resid,
                "residue_relief_added_m": round(added, 1),
                "relief_component_raised_px": raised})
    return row


def cmd_decode(out, per_state=40, extra=None, cache=None):
    by = load_union(out)
    smp = sample(by, 100)                      # the HEAD sample, of which a subset
    rnd = random.Random(SEED + 1)
    jobs = [(s, x, y) for s, t in smp.items() for x, y in rnd.sample(t, min(per_state, len(t)))]
    if extra:
        with open(extra) as f:
            jobs += [(r["state"], int(r["x"]), int(r["y"])) for r in csv.DictReader(f)]
    rows = []
    for i, (s, x, y) in enumerate(jobs):
        p = Path(cache) / f"{Z}_{x}_{y}.png" if cache else None
        if p is not None and p.exists():
            status, body = 200, p.read_bytes()
        else:
            status, _, body = request(TILE_URL.format(z=Z, x=x, y=y))
            if p is not None and status == 200:
                p.write_bytes(body)
        rows.append(tile_row(s, x, y, body, status))
        if (i + 1) % 100 == 0:
            print(f"{i + 1}/{len(jobs)}", flush=True)
    write_decode(rows, out / "terrarium_decode_sample.csv")


def cmd_local(tile_dir, label, out):
    """The same per-tile row for a directory of cached z_x_y.png tiles, such as
    the review's Colorado cache and data/raw/terrain (New England)."""
    rows = []
    for p in sorted(Path(tile_dir).glob("*.png")):
        z, x, y = (int(v) for v in p.stem.split("_"))
        rows.append(tile_row(label, x, y, p.read_bytes(), 200))
    write_decode(rows, out / f"terrarium_decode_{label}.csv")


def write_decode(rows, path):
    keys = ["state", "x", "y", "status", "bytes", "terrain", "min_m", "max_m", "oob_px",
            "strong_residue_px", "residue_px", "residue_relief_added_m",
            "relief_component_raised_px"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    ok = [r for r in rows if r["status"] == 200]
    bad_oob = sum(1 for r in ok if r["oob_px"])
    bad_res = sum(1 for r in ok if r["residue_px"])
    harm = sum(1 for r in ok if r.get("relief_component_raised_px"))
    print(f"{len(ok)} tiles decoded: {bad_oob} with out-of-band pixels, "
          f"{bad_res} with residue the band misses, {harm} where it raises the relief "
          f"component -> {path.name}")


def cmd_rates(out, out_csv, censuses):
    by = load_union(out)
    rows = list(csv.DictReader(open(out / "terrarium_decode_sample.csv")))
    rnd = [r for r in rows if ":" not in r["state"] and r["status"] == "200"
           and r["state"] not in OUT_ABBR]
    tests = {"out of band": lambda r: int(r["oob_px"]) > 0,
             "residue": lambda r: int(r["residue_px"]) > 0,
             "raises the relief component": lambda r: int(r["relief_component_raised_px"]) > 0}
    result = []
    regions = {"contiguous 48 + DC": lambda st: st not in OUT_ABBR}
    for region, keep in regions.items():
        states = [st for st in by if keep(st)]
        total = sum(len(by[st]) for st in states)
        for name, hit in tests.items():
            est, var, k, n_all = 0.0, 0.0, 0, 0
            for st in states:
                tiles = by[st]
                sample = [r for r in rnd if r["state"] == st]
                if not sample:
                    continue
                n, Nn = len(sample), len(tiles)
                ks = sum(1 for r in sample if hit(r))
                k += ks
                n_all += n
                p = ks / n
                est += Nn * p
                var += Nn ** 2 * p * (1 - p) / max(n - 1, 1) * (1 - n / Nn)
            result.append({"set": f"national sample, {region}", "test": name,
                           "tiles": n_all, "hits": k,
                           "rate_pct": round(100 * k / n_all, 3) if n_all else "",
                           "us_tiles_estimate": round(est),
                           "us_tiles_se": round(math.sqrt(var)), "us_tiles_total": total})
    heads = defaultdict(list)
    hp = out / "terrarium_head_sample.csv"
    if hp.exists():
        for r in csv.DictReader(open(hp)):
            if r["bytes"] and r["state"] not in OUT_ABBR:
                heads[r["state"]].append(int(r["bytes"]))
        est, var, n_all = 0.0, 0.0, 0
        for st, tiles in by.items():
            b = np.array(heads.get(st, []), dtype=float)
            if st in OUT_ABBR or not len(b):
                continue
            n, Nn = len(b), len(tiles)
            n_all += n
            est += Nn * b.mean()
            if n > 1:
                var += Nn ** 2 * b.var(ddof=1) / n * (1 - n / Nn)
        result.append({"set": "HEAD sample, contiguous 48 + DC", "test": "bytes",
                       "tiles": n_all, "hits": "", "rate_pct": "",
                       "us_tiles_estimate": round(est), "us_tiles_se": round(math.sqrt(var)),
                       "us_tiles_total": sum(len(t) for st, t in by.items()
                                             if st not in OUT_ABBR)})
    for path in censuses:
        crow = [r for r in csv.DictReader(open(path)) if r["status"] == "200"]
        for name, hit in tests.items():
            k = sum(1 for r in crow if hit(r))
            result.append({"set": Path(path).stem.replace("terrarium_decode_", ""), "test": name,
                           "tiles": len(crow), "hits": k,
                           "rate_pct": round(100 * k / len(crow), 3), "us_tiles_estimate": "",
                           "us_tiles_se": "", "us_tiles_total": ""})
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(result[0]))
        w.writeheader()
        w.writerows(result)
    for r in result:
        print(r)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "tiles":
        cmd_tiles(sys.argv[2], Path(sys.argv[3]))
    elif cmd == "head":
        cmd_head(Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 100)
    elif cmd == "decode":
        cmd_decode(Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 40,
                   sys.argv[4] if len(sys.argv) > 4 else None,
                   sys.argv[5] if len(sys.argv) > 5 else None)
    elif cmd == "local":
        cmd_local(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
    elif cmd == "rates":
        cmd_rates(Path(sys.argv[2]), sys.argv[3], sys.argv[4:])
