"""Loading and the candidate scores for the Western land-cover comparison, shared by evaluate.py
and breakdowns.py. Importing it loads all three regions and scores every candidate (about 20 s).
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "national_scoring")); sys.path.insert(0, str(HERE))
from core import *  # noqa
import candidates as KC
import classmaps as CM

REGIONS = ["ne", "co", "ut"]
t0 = time.time()
chunks = {r: load_chunks(r) for r in REGIONS}
edges = {r: load_edges(r, chunks[r]) for r in REGIONS}
D = load_marks()
print("loaded", f"{time.time() - t0:.0f}s", flush=True)


def wc_desert(F, suf=""):
    return np.clip(sum(F[f"{k}_1k{suf}"].to_numpy() for k in ("shrub", "bare", "moss", "snow")), 0, 1)


# Each candidate's desert fraction, from a frame of chunk or edge features.
DESERT = {
    "W0":   lambda F: wc_desert(F),
    "W0m3": lambda F: wc_desert(F, "_m3"),
    # Approximate: WorldCover's box share times the box's rangeland share (the two grids differ,
    # so the pixel-level product cannot be formed from the block counts).
    "W0r":  lambda F: wc_desert(F) * F["rc_range"].to_numpy(),
    "N1":   lambda F: F["nlcd_desert"].to_numpy(),
    "N1r":  lambda F: F["nlcd_desert_r"].to_numpy(),
    "L1":   lambda F: F["lf_desert"].to_numpy(),
    "L1r":  lambda F: F["lf_desert_r"].to_numpy(),
    "R1":   lambda F: np.clip(F["rc_shrub"].to_numpy() + F["rc_bare"].to_numpy(), 0, 1),
    "R2":   lambda F: F["rc_shrub"].to_numpy(),
}
assert set(DESERT) == set(CM.CANDIDATES)
# Grass for the prairie question: each source's natural-grassland share (net of nothing).
GRASS = {
    "WorldCover grassland (30)": lambda F: F["grass_1k"].to_numpy(),
    "NLCD Grassland/Herbaceous (71)": lambda F: F["nlcd_grass"].to_numpy(),
    "NLCD 71, rangeland only": lambda F: F["nlcd_grass_r"].to_numpy(),
    "LANDFIRE natural grassland": lambda F: F["lf_grass"].to_numpy(),
    "LANDFIRE natural grassland, rangeland only": lambda F: F["lf_grass_r"].to_numpy(),
    "RCMAP herbaceous cover": lambda F: F["rc_herb"].to_numpy(),
}
GRASS_FOR = {"W0": "WorldCover grassland (30)", "N1r": "NLCD 71, rangeland only",
             "L1": "LANDFIRE natural grassland", "L1r": "LANDFIRE natural grassland, rangeland only",
             "R1": "RCMAP herbaceous cover"}


def raw_e1(F, desert, grass=None, drop_byway=False):
    """E1 exactly as candidates.py builds it, with this desert (and optionally grass) in the forest slot."""
    base = KC._cols(F, grand=True, prot=True, drop_byway=drop_byway)
    forest = F["c_forest"].to_numpy().astype(float)
    slot = np.maximum(forest, desert)
    if grass is not None:   # E1g's form: grass net of built land
        slot = np.maximum(slot, np.clip(grass * (1 - F["built_1k"].to_numpy()), 0, 1))
    return base + W["c_forest"] * (slot - forest)


def scores(desert_fn, grass_fn=None):
    out = {}
    for r in REGIONS:
        C, E = chunks[r], edges[r]
        gc = grass_fn(C) if grass_fn else None
        ge = grass_fn(E) if grass_fn else None
        out[r] = dict(chunk=composite(raw_e1(C, desert_fn(C), gc), C.score_adj.to_numpy()),
                      chunk_nb=composite(raw_e1(C, desert_fn(C), gc, drop_byway=True), C.score_adj.to_numpy()),
                      edge=composite(raw_e1(E, desert_fn(E), ge), E.score_adj.to_numpy()))
    return out


S = {k: scores(f) for k, f in DESERT.items()}
S0 = {r: dict(chunk=chunks[r].score.to_numpy(),
              chunk_nb=composite(raw_shipped(chunks[r], drop_byway=True), chunks[r].score_adj.to_numpy()),
              edge=edges[r].score.to_numpy()) for r in REGIONS}
SG = {k: scores(DESERT[k], GRASS[g]) for k, g in GRASS_FOR.items()}
print("scored", f"{time.time() - t0:.0f}s", flush=True)
GROUPS = {"High Plains": "plains", "Southwestern Tablelands": "plains", "Southern Rockies": "mountains",
          "Wasatch and Uinta Mountains": "mountains", "Colorado Plateaus": "plateau/canyon",
          "Arizona/New Mexico Plateau": "plateau/canyon", "Wyoming Basin": "basin", "Central Basin and Range": "basin",
          "Mojave Basin and Range": "basin", "Northern Basin and Range": "basin"}
