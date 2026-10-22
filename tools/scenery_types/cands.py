"""Every candidate, hand-set by analogy and written down before any feature was computed.

A candidate maps one unit table F (chunks or edges) to a raw score on the shipped
composite. F carries the shipped components, with S0's c_forest (forest or desert,
whichever is larger), c_grand and c_protected already as built on `usa`, plus the
feature columns below. Nothing here is fitted to marks, icons or byways.

Features (features_*.py):
  <class>_1k   WorldCover class share of the ~1 km box (wc_sample.py's 9x11 blocks of ~100 m)
  relief250    elevation range in a 5 px (~280 m at RELIEF_REF_LAT) window, despiked DEM
  prom5k, prom10k, prom15k
               highest despiked elevation within a square of half-side R, minus the road's
  d_coast      metres to the nearest OSM natural=coastline line (inf where none)

The constants, and what each is set by analogy with:
  V  vista = open * clip((prom_R - V0) / (V1 - V0)). V0 = 300 m, V1 = 900 m are
     c_grand's own start and full (GRAND_START, GRAND_FULL): the same scale of landform,
     seen from further off. R = 10 km, the middle of the brief's 5-15 km. open is the
     brief's open land: everything WorldCover has that is not tree, built or mangrove.
     It enters grand's slot by max() (no new weight mass), or as its own term at
     grand's 0.10 (V-add).
  S  the sea scores as water with c_water's own distance curve: 1 within DIST["water"]
     (120 m) of the coastline, 0.45 within DIST["water_mid"] (350 m). S2 credits it only
     where at least half the ~1 km box is water, which is the geometry of a road with
     water on both sides (a bridge or causeway); a shore road has at most about half.
  W  wetland + mangrove share of the ~1 km box, full when the box is all wetland,
     like desert's. W1: forest's slot by max(), as desert entered. W2: water's slot at
     DIST's mid-distance credit 0.45, since marsh is water you see but do not reach.
  R  rock = bare_1k * clip(relief250 / RF), RF = RELIEF_FULL scaled by the window
     ratio: 100 m * 280 / 738 = 38 m. Relief's slot by max().
  P  pastoral = (grass + crop) * (1 - built) * c_relief: open farmland, credited only
     as far as it rolls, at relief's own scale. Forest's slot by max().
  C  C-max: forest's slot takes max(forest/desert, wetland, rock, vista), plus S.
     C-add: S, plus vista, wetland and rock as terms of their own at the weight of the
     slot each would otherwise share (grand 0.10, forest 0.18, relief 0.16).
     C-slots: S + W1 + V + R, each in its natural slot.
  L  (this study's own candidate, added 2026-10-22 after the S0 icon breakdown and before
     it was scored.) Landmark credit within DIST["green"] (80 m) of a PAD-US landmark
     polygon, the reach score.py already gives "next to a park", with the same built-land
     gate. Why: PAD-US cuts road rights-of-way out of its fee polygons, so US 41 through
     Big Cypress National Preserve is inside the preserve for 9% of its length and within
     80 m of it for 98%, and scores c_protected 0.07 of 1. No other candidate touches it.
     Feature d_landmark: metres to the nearest landmark polygon (landmarks.py).
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline"))
import score as S  # noqa: E402

BASE = ["c_curves", "c_water", "c_coast", "c_forest", "c_farm", "c_views", "c_scenic_tag",
        "c_relief", "c_urban", "c_grand", "c_protected"]
WT = {c: S.WEIGHTS[c[2:]] for c in BASE}

V0, V1, V_R = S.GRAND_START, S.GRAND_FULL, 10
RF_ROCK = S.RELIEF_FULL * 280.0 / 738.0
WET_MID = 0.45                         # score.py: c_water at DIST["water_mid"]
ON_SEA_WATER_SHARE = 0.5


def f(F, c):
    return F[c].to_numpy().astype(float)


def open_land(F):
    return np.clip(1 - f(F, "tree_1k") - f(F, "built_1k") - f(F, "mangrove_1k"), 0, 1)


def vista(F, R=V_R, v0=V0, v1=V1):
    p = np.nan_to_num(f(F, f"prom{R}k"), nan=0.0)
    return open_land(F) * np.clip((p - v0) / (v1 - v0), 0, 1)


def sea(F, near=S.DIST["water"], mid=S.DIST["water_mid"], on_sea=False):
    d = f(F, "d_coast")
    s = np.where(d <= near, 1.0, np.where(d <= mid, WET_MID, 0.0))
    if on_sea:
        s = s * (f(F, "water_1k") >= ON_SEA_WATER_SHARE)
    return s


def wet(F, sat=1.0):
    return np.clip((f(F, "wetland_1k") + f(F, "mangrove_1k")) / sat, 0, 1)


def rock(F, full=RF_ROCK):
    return f(F, "bare_1k") * np.clip(np.nan_to_num(f(F, "relief250")) / full, 0, 1)


def pastoral(F, relief_full=S.RELIEF_FULL):
    # Exact from the capped c_relief for any relief_full <= RELIEF_FULL, which is all pieces carry.
    assert relief_full <= S.RELIEF_FULL
    rel = np.clip(f(F, "c_relief") * S.RELIEF_FULL / relief_full, 0, 1)
    return np.clip(f(F, "grass_1k") + f(F, "crop_1k"), 0, 1) * (1 - f(F, "built_1k")) * rel


def landmark(F, dist=S.DIST["green"]):
    return ((f(F, "d_landmark") <= dist) & (f(F, "built_1k") <= S.PROTECTED_BUILT_MAX)).astype(float)


def raw(F, spec):
    """spec: a dict of switches (see CANDIDATES). Returns the raw score."""
    c = {k: f(F, k) for k in BASE}
    extra = np.zeros(len(F))
    if "sea" in spec:
        c["c_water"] = np.maximum(c["c_water"], sea(F, **spec["sea"]))
    if "wet" in spec:
        o = dict(spec["wet"]); mode = o.pop("mode")
        if mode == "forest":
            c["c_forest"] = np.maximum(c["c_forest"], wet(F, **o))
        else:
            lvl = o.pop("level", WET_MID)
            c["c_water"] = np.maximum(c["c_water"], lvl * wet(F, **o))
    if "vista" in spec:
        o = dict(spec["vista"]); mode = o.pop("mode", "slot"); w = o.pop("w", WT["c_grand"])
        v = vista(F, **o)
        if mode == "slot":
            c["c_grand"] = np.maximum(c["c_grand"], v)
        else:
            extra += w * v
    if "rock" in spec:
        c["c_relief"] = np.maximum(c["c_relief"], rock(F, **spec["rock"]))
    if "pastoral" in spec:
        c["c_forest"] = np.maximum(c["c_forest"], pastoral(F, **spec["pastoral"]))
    if "landmark" in spec:
        c["c_protected"] = np.maximum(c["c_protected"], landmark(F, **spec["landmark"]))
    if spec.get("cmax"):
        c["c_forest"] = np.maximum.reduce([c["c_forest"], wet(F), rock(F), vista(F)])
    if spec.get("cadd"):
        extra += WT["c_grand"] * vista(F) + WT["c_forest"] * wet(F) + WT["c_relief"] * rock(F)
    r = sum(WT[k] * c[k] for k in BASE) + extra
    if spec.get("drop_byway"):
        r = r - WT["c_scenic_tag"] * c["c_scenic_tag"]
    return r


def score(F, spec):
    return 10.0 * np.clip((raw(F, spec) + S.RAW_BASE) * S.STRETCH + f(F, "score_adj"), 0.0, 1.0)


S1 = dict(sea={})
CANDIDATES = {
    "S0 shipped E1": {},
    "V slot (R10, 300-900 m)": dict(vista={}),
    "V-add (R10, +0.10)": dict(vista=dict(mode="add")),
    "S1 sea as water": S1,
    "S2 sea as water, on the sea only": dict(sea=dict(on_sea=True)),
    "W1 wetland in forest slot": dict(wet=dict(mode="forest")),
    "W2 wetland as mid water": dict(wet=dict(mode="water")),
    "R rock texture": dict(rock={}),
    "P pastoral (priced only)": dict(pastoral={}),
    "C-slots S1+W1+V+R": dict(sea={}, wet=dict(mode="forest"), vista={}, rock={}),
    "C-max one landscape slot + S1": dict(sea={}, cmax=True),
    "C-add separate terms + S1": dict(sea={}, cadd=True),
    "S1+W1": dict(sea={}, wet=dict(mode="forest")),
    # combinations of the passing terms, and L (no new constants)
    "V+S1": dict(vista={}, sea={}),
    "V+S2": dict(vista={}, sea=dict(on_sea=True)),
    "L landmark within 80 m": dict(landmark={}),
    "V+S2+L": dict(vista={}, sea=dict(on_sea=True), landmark={}),
    "V+S1+L": dict(vista={}, sea={}, landmark={}),
}

# Sweeps: each constant moved around its hand-set value, the others held.
SWEEPS = {}
for R in (5, 10, 15):
    for v0 in (150, 300, 450):
        SWEEPS[f"V slot R{R} {v0}-{3 * v0} m"] = dict(vista=dict(R=R, v0=v0, v1=3 * v0))
for w in (0.05, 0.10, 0.15, 0.20):
    SWEEPS[f"V-add w{w:.2f}"] = dict(vista=dict(mode="add", w=w))
for k in (0.5, 1.0, 2.0):
    SWEEPS[f"S1 distances x{k}"] = dict(sea=dict(near=S.DIST["water"] * k, mid=S.DIST["water_mid"] * k))
for sat in (0.5, 1.0):
    SWEEPS[f"W1 full at {sat:.0%} wet"] = dict(wet=dict(mode="forest", sat=sat))
for lvl in (0.45, 1.0):
    SWEEPS[f"W2 level {lvl}"] = dict(wet=dict(mode="water", level=lvl))
for full in (25.0, RF_ROCK, 60.0):
    SWEEPS[f"R full at {full:.0f} m"] = dict(rock=dict(full=full))
for d in (40.0, 80.0, 200.0):
    SWEEPS[f"L within {d:.0f} m"] = dict(landmark=dict(dist=d))
for rf in (33.0, 50.0, 100.0):
    SWEEPS[f"P relief full {rf:.0f} m"] = dict(pastoral=dict(relief_full=rf))
