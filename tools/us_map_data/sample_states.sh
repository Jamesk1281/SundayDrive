#!/bin/sh
# Download, measure and delete the sampled state extracts, one at a time.
#
# Each extract goes into a new empty directory of its own, is measured by
# osm_metrics.py and seasonal_check.py, and is deleted before the next one is
# fetched, so at most one sits on disk. Geofabrik is asked for one file at a
# time, never in parallel (docs/us-map-data-findings.md, "Method").
#
# Usage: sh sample_states.sh <scratch_dir> <repo_dir> <python> <state> [<state> ...]
set -u
scratch=$1; repo=$2; py=$3; shift 3
here=$repo/tools/us_map_data
mkdir -p "$scratch/out/metrics" "$scratch/out/seasonal"
for state in "$@"; do
  dir="$scratch/dl/pbf_$state"
  mkdir -p "$dir"
  pbf="$dir/$state.osm.pbf"
  if [ ! -s "$scratch/out/metrics/$state.json" ]; then
    echo "== $state: download $(date +%H:%M:%S)"
    curl -sS -L --fail -C - -A "SundayDrive-us-map-data-survey/1.0" -o "$pbf" \
      -w "   %{http_code} %{size_download} bytes in %{time_total}s (%{speed_download} B/s)\n" \
      "https://download.geofabrik.de/north-america/us/$state-latest.osm.pbf" || {
        echo "   download failed"; continue; }
    echo "== $state: measure $(date +%H:%M:%S)"
    "$py" -I "$here/osm_metrics.py" "$repo/pipeline" "$pbf" "$state" \
      "$scratch/out/metrics/$state.json"
    "$py" -I "$here/seasonal_check.py" "$repo/pipeline" "$pbf" "$state" \
      "$here/seasonal_roads.json" "$scratch/out/seasonal/$state.json"
  fi
  rm -f "$pbf"
  echo "== $state: deleted $(date +%H:%M:%S)"
done
echo "== all done $(date +%H:%M:%S)"
