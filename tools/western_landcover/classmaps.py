"""Class groupings for the Western land-cover comparison, fixed before anything was measured.

Every grouping here was written from what the classes are, from each product's own legend,
and committed before the first sample was taken (docs/western-landcover-verdict.md gives the
commit). Nothing in this file is tuned to the byway labels or the marks. A grouping added
after measuring would have to be reported as such.

"desert" is the score's desert-and-rock idea: open arid shrubland, bare rock and soil,
snow and ice, and alpine ground. It is what WorldCover's (20, 60, 70, 100) stands for.
"grass" is natural grassland, measured only to answer whether separated prairie still
points the wrong way. The score's structure does not change for it.
"""

# ---------------------------------------------------------------- ESA WorldCover 2021 (baseline)
# As shipped in pipeline/landcover.py: shrubland, bare/sparse, snow and ice, moss and lichen.
WC_DESERT = (20, 60, 70, 100)
WC_GRASS = (30,)
WC_CROP = (40,)

# ---------------------------------------------------------------- Annual NLCD 2025 (C1V2)
# The class-for-class analog of WorldCover's set: Shrub/Scrub (52), Barren Land (31) and
# Perennial Ice/Snow (12). CONUS NLCD has no moss/lichen class (51, 72-74 are Alaska only).
# Shrub/Scrub is defined by structure, not ecology ("shrubs less than 5 m tall", including
# "young trees in an early successional stage"), so in New England it is clearcut and
# regenerating forest. That is the trap the gate below exists for.
NLCD_DESERT = (52, 31, 12)
NLCD_GRASS = (71,)            # Grassland/Herbaceous
NLCD_PASTURE = (81,)
NLCD_CROP = (82,)
NLCD_NODATA = 250

# ---------------------------------------------------------------- LANDFIRE EVT, LF2025
# From the product's own physiognomy (EVT_PHYS) and names (EVT_NAME, EVT_GP_N):
#   desert = natural Shrubland + Sparsely Vegetated + Snow-Ice + alpine herbaceous,
#   minus the transitional classes, which are disturbance states of forest, not shrubland:
#   "Recently Logged/Burned/Disturbed Other - Shrub Cover" (EVT_GP_N "Transitional Shrub
#   Vegetation"). Alpine herbaceous ground (fell-field, turf, tundra meadow) is Grassland in
#   LANDFIRE's physiognomy; it is the "alpine" part of WorldCover's moss, bare and snow, so
#   any Grassland class whose name says Alpine joins desert.
#   Exotic Herbaceous and Exotic Tree-Shrub (introduced and ruderal vegetation) are left out
#   of both groups: they are disturbed land, whatever they look like.
# grass = natural Grassland, minus the transitional herb classes and minus alpine.
LF_DESERT_PHYS = ("Shrubland", "Sparsely Vegetated", "Snow-Ice")
LF_TRANSITIONAL_GP = ("Transitional Shrub Vegetation", "Transitional Herbaceous Vegetation")
LF_GRASS_PHYS = ("Grassland",)
LF_ALPINE_WORD = "Alpine"
LF_NODATA = (-9999, 32767)


def landfire_groups(table):
    """{VALUE: 'desert' | 'grass'} from LF2025_EVT.csv (a DataFrame), by the rules above."""
    out = {}
    for r in table.itertuples():
        if r.EVT_GP_N in LF_TRANSITIONAL_GP:
            continue
        alpine = LF_ALPINE_WORD in str(r.EVT_NAME)
        if r.EVT_PHYS in LF_DESERT_PHYS or (r.EVT_PHYS in LF_GRASS_PHYS and alpine):
            out[int(r.VALUE)] = "desert"
        elif r.EVT_PHYS in LF_GRASS_PHYS:
            out[int(r.VALUE)] = "grass"
    return out


# ---------------------------------------------------------------- RCMAP 2025 (V8), fractional cover
# Percent cover per 30 m pixel, Western rangelands only; 101 is RCMAP's non-rangeland mask.
# It has no classes, so "desert" is read as the share of the ground that is shrub or bare,
# which is the literal content of WorldCover's shrub and bare classes:
#   R1: (shrub + bare ground) / 100   -- shrub includes sagebrush
#   R2: shrub / 100                   -- without bare ground, because the bare soil between
#                                        shortgrass bunches is part of prairie, not desert
# Both were written down here before measuring; both are reported.
# grass = herbaceous cover / 100. Outside RCMAP's footprint and on masked pixels, all are 0.
RCMAP_MASK = 101
RCMAP_MAX = 100

# ---------------------------------------------------------------- the gate
# NLCD's Shrub/Scrub is only desert where the land is rangeland. The gate is RCMAP's own
# footprint and mask: an NLCD desert pixel counts only where RCMAP 2025 sagebrush has a cover
# value (0-100), not its mask (101) and not outside its extent. Chosen because it is a
# land-use fact made by a different process, not a line drawn on a map. Its seam is priced
# in the verdict.

# ---------------------------------------------------------------- the candidates, all reported
# Each replaces WorldCover's desert fraction in E1's forest slot, max(c_forest, desert),
# counted in the same ~1 km ground box. Nothing else in E1 changes.
CANDIDATES = {
    "W0":   "WorldCover desert, as E1 (baseline)",
    "W0m3": "WorldCover desert on 3x3-majority ~30 m pixels (resolution control)",
    "W0r":  "WorldCover desert, gated to RCMAP rangeland",
    "N1":   "NLCD desert, ungated",
    "N1r":  "NLCD desert, gated to RCMAP rangeland",
    "L1":   "LANDFIRE desert, ungated",
    "L1r":  "LANDFIRE desert, gated to RCMAP rangeland",
    "R1":   "RCMAP shrub + bare cover",
    "R2":   "RCMAP shrub cover",
}
