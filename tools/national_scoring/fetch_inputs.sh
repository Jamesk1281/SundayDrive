#!/bin/zsh
# Fetch the national inputs into $NS_WORK. Each source goes in its own directory, and nothing
# here is executed: the downloads are data. Sizes as of 2026-10-12.
#   FHWA America's Byways, eight states, with geometry (2.2 MB; no licence stated, used as a check only)
#   EPA Level III ecoregions (28 MB zip; public domain)
#   PAD-US 4.1 national geodatabase (1.52 GB zip, 2.0 GB unpacked; public domain)
# WorldCover is fetched tile by tile by wc_grids.py.
set -e
: ${NS_WORK:?set NS_WORK}
mkdir -p $NS_WORK/fhwa $NS_WORK/eco_dl/x $NS_WORK/padus_dl $NS_WORK/padus_x
U="https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/FHWA_ScenicByways_08042026_gdb/FeatureServer/0"
curl -sS -f "$U/query?where=STATE+IN+%28%27CO%27%2C%27UT%27%2C%27MA%27%2C%27CT%27%2C%27RI%27%2C%27VT%27%2C%27NH%27%2C%27ME%27%29&outFields=*&returnGeometry=true&outSR=4326&f=geojson" -o $NS_WORK/fhwa/byways.geojson
curl -sS -f -o $NS_WORK/eco_dl/us_eco_l3.zip https://dmap-prod-oms-edc.s3.us-east-1.amazonaws.com/ORD/Ecoregions/us/us_eco_l3.zip
(cd $NS_WORK/eco_dl/x && unzip -o -q ../us_eco_l3.zip)
# ScienceBase's catalog file endpoint serves the zip directly; the item's "manager" links are web pages.
curl -sS -L -f -o $NS_WORK/padus_dl/PADUS4_1Geodatabase.zip "https://www.sciencebase.gov/catalog/file/get/652d4fc5d34e44db0e2ee45e?name=PADUS4_1Geodatabase.zip"
(cd $NS_WORK/padus_x && unzip -o -q ../padus_dl/PADUS4_1Geodatabase.zip)
