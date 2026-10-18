#!/bin/zsh
# Build one region with the unmodified pipeline into $NS_WORK/<name>/processed, then the
# evaluation's feature tables into $NS_WORK/reg/<name>. Utah, 2026-10-12: 170 MB PBF, about
# 15 minutes for the pipeline, 837 MB on disk.
#   build_region.sh ut https://download.geofabrik.de/north-america/us/utah-latest.osm.pbf -114.1,36.95,-109.0,42.05 650 4130 UT,ID,NV,AZ,WY,CO,NM
# Colorado, 2026-10-18 (docs/western-landcover-verdict.md): Geofabrik's extract of 2026-10-17.
#   byway_ways.py $NS_WORK/co/pbf/region.osm.pbf US:CO:Scenic $NS_WORK/co_byway_ways.txt   (26 relations)
#   BYWAY_WAYS=$NS_WORK/co_byway_ways.txt PADUS_FILE=$NS_WORK/padus_rest/co.parquet \
#   build_region.sh co https://download.geofabrik.de/north-america/us/colorado-latest.osm.pbf -109.1,36.95,-102.0,41.05 1000 4420 CO,UT,WY,NE,KS,OK,NM,AZ
# The last three arguments are the physical elevation band (m) for terrain.py and the PAD-US
# states to read (the region and its neighbours; at least two, see padus.py).
#
# The evaluation's S0 is the score without the national terms; candidates.py adds them from the
# feature tables. On a branch where landcover.py already writes the desert and built-up columns
# (usa, since 5219744), they are dropped before score.py so S0 stays S0 and E1 is not desert twice.
# PADUS_FILE=<padus_rest.py output> reads PAD-US from that file instead of the geodatabase.
# PART=pipeline or PART=features runs one half (the feature steps need fetch_inputs.sh and wc_grids.py done).
set -e
PART=${PART:-all}
: ${NS_WORK:?set NS_WORK}
NAME=$1; URL=$2; BBOX=$3; LO=$4; HI=$5; STATES=$6
PY=${PY:-python}
HERE=${0:A:h}; P=$HERE/../../pipeline
U=$NS_WORK/$NAME; mkdir -p $U/pbf $U/processed $U/logs
[ -s $U/pbf/region.osm.pbf ] || curl -sS -L -f -o $U/pbf/region.osm.pbf $URL
if [ $PART != features ]; then
cd $P
$PY extract.py $U/pbf/region.osm.pbf $U/processed > $U/logs/extract.log 2>&1
$PY -c "import sys, elevation; elevation.BBOX = tuple(float(x) for x in sys.argv[2].split(',')); elevation.main(sys.argv[1], 11)" $U/processed $BBOX > $U/logs/elevation.log 2>&1
$PY landcover.py $U/processed --stream > $U/logs/landcover.log 2>&1
$PY -c "import sys, pandas as pd; p = sys.argv[1]; t = pd.read_parquet(p); t.to_parquet(p.replace('.parquet', '_national.parquet')); t.drop(columns=[c for c in ('desert', 'built') if c in t]).to_parquet(p)" $U/processed/tree_cover.parquet
$PY score.py $U/processed --no-cache > $U/logs/score.log 2>&1
$PY graph.py $U/pbf/region.osm.pbf $U/processed > $U/logs/graph.log 2>&1
$PY closures.py $U/pbf/region.osm.pbf $U/processed > $U/logs/closures.log 2>&1
fi
[ $PART = pipeline ] && exit 0
cd $HERE
$PY prep_region.py $U/processed $NS_WORK/reg/$NAME
$PY terrain.py $U/processed $NS_WORK/reg/$NAME $LO $HI
$PY relief_raw.py $U/processed $NS_WORK/reg/$NAME
$PY wc_sample.py $NS_WORK/wc_grid $NS_WORK/reg/$NAME
$PY padus.py $NS_WORK/reg/$NAME $STATES ${PADUS_FILE:-}
$PY attrs.py $NS_WORK/reg/$NAME $NAME $U/processed ${BYWAY_WAYS:-}
