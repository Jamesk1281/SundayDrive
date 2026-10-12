"""What "the US" means in this survey: the contiguous 48 states and DC.

Alaska, Hawaii and the territories are out of scope (decided 2026-10-11). Every
script that enumerates states reads these sets, so a re-run cannot bring them
back by accident.
"""

# Geofabrik sub-region slugs.
OUT_SLUGS = {"alaska", "hawaii", "puerto-rico", "us-virgin-islands"}
# USPS abbreviations, and Census state FIPS codes.
OUT_ABBR = {"AK", "HI", "PR", "VI", "GU", "AS", "MP"}
OUT_FIPS = {"02", "15", "60", "66", "69", "72", "78"}
# A box around the contiguous 48 and DC (lon/lat), for services that filter
# by envelope rather than by state. It also takes in slivers of Canada and
# Mexico, which carry no US agency data.
LOWER48_BBOX = (-125.0, 24.4, -66.9, 49.5)
