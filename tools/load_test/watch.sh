#!/bin/bash
# Samples the box every 2 s while a probe runs, and creates tools/load_test/STOP
# when MemAvailable falls under 700 MB, which ends the probe between requests.
#
#     tools/load_test/watch.sh results/run-box.tsv &
#
# Columns: time, MemAvailable MB, service cgroup MB, swap used MB, CPU busy %
# over the interval (both cores), 1-min load.
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$1"
KEY="${KEY:-$HOME/.ssh/scenic_oracle}"
BOX="${BOX:-ubuntu@129.158.208.92}"
ssh -o BatchMode=yes -i "$KEY" "$BOX" 'bash -s' <<'EOF' | while IFS=$'\t' read -r line; do
cg=/sys/fs/cgroup/system.slice/sundaydrive-api.service
read -r _ u n s i rest < /proc/stat; prev_busy=$((u+n+s)); prev_all=$((u+n+s+i))
while true; do
  sleep 2
  read -r _ u n s i w q sq rest < /proc/stat
  busy=$((u+n+s+q+sq)); all=$((u+n+s+i+w+q+sq))
  cpu=$(( 100 * (busy - prev_busy) / (all - prev_all) )); prev_busy=$busy; prev_all=$all
  avail=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
  swap=$(awk '/SwapTotal/ {t=$2} /SwapFree/ {f=$2} END {print int((t-f)/1024)}' /proc/meminfo)
  svc=$(( $(cat $cg/memory.current) / 1048576 ))
  load=$(cut -d" " -f1 /proc/loadavg)
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%H:%M:%S)" "$avail" "$svc" "$swap" "$cpu" "$load"
done
EOF
  echo "$line" >> "$OUT"
  avail=$(echo "$line" | cut -f2)
  if [ -n "$avail" ] && [ "$avail" -lt 700 ]; then
    touch "$HERE/STOP"
    echo "LOW MEMORY: $line" >&2
  fi
done
