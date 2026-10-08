#!/bin/bash
# One sequential run: box watcher on, probe phases, watcher off.
#
#     tools/load_test/run.sh LABEL PHASE [PHASE ...] [-- probe options]
#
# Needs the SSH tunnel up first:
#     ssh -N -L 15957:127.0.0.1:5057 -i ~/.ssh/scenic_oracle ubuntu@129.158.208.92 &
HERE="$(cd "$(dirname "$0")" && pwd)"
LABEL="$1"; shift
mkdir -p "$HERE/results"
rm -f "$HERE/STOP"
"$HERE/watch.sh" "$HERE/results/$LABEL-box.tsv" &
WATCH=$!
python3 -u "$HERE/probe.py" http://127.0.0.1:15957 "$@" --out "$HERE/results/$LABEL.jsonl"
STATUS=$?
pkill -P "$WATCH"; kill "$WATCH" 2>/dev/null
exit $STATUS
