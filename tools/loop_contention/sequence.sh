#!/bin/zsh
# Probe each server in turn: start it, wait for it, probe it, stop it by PID.
#
#   PY=<venv>/bin/python SUNDAYDRIVE_DATA=<main>/data/processed-ne \
#     tools/loop_contention/sequence.sh <work> before:0:1 after:0:1 before:1:1 after:1:1
#
# <work>/<name> is a copy of server/ and pipeline/ at the commit being measured
# (`git archive <rev> server pipeline | tar -x -C <work>/<name>`). The middle
# field is SUNDAYDRIVE_ROUTE_OPTIONS, the last a replicate number. Results land
# in <work>. One server at a time, on port 5391, and a fresh one per run: a
# server the old code overloaded is still computing abandoned loop builds
# long after its clients gave up, and would poison the next run.
# docs/loop-lock-contention.md.
here=${0:a:h}; work=$1; shift
nodes=$SUNDAYDRIVE_DATA/graph_nodes.parquet
for spec in $@; do
  code=${spec%%:*}; rest=${spec#*:}; opts=${rest%%:*}; rep=${rest#*:}
  label=$code-opt$opts-$rep
  (cd $work/$code && PORT=5391 SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_ROUTE_OPTIONS=$opts \
     exec $PY -u server/serve.py > $work/srv-$label.log 2>&1) &
  pid=$!
  until curl -s -m 5 http://127.0.0.1:5391/api/health >/dev/null; do sleep 5; done
  echo "$(date +%T) $label server up; $(uptime)" >> $work/sequence.log
  $PY -u $here/probe.py http://127.0.0.1:5391 $nodes --clients 0 1 0 4 --duration 45 \
      --reps 5 --label $label --out $work/$label.json >> $work/probe-$label.log 2>&1
  $PY -u $here/double_tap.py http://127.0.0.1:5391 $nodes 8 >> $work/double-$label.log 2>&1
  echo "$(date +%T) $label done; $(uptime)" >> $work/sequence.log
  kill $pid; wait $pid 2>/dev/null
done
