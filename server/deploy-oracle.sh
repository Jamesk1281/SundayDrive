#!/usr/bin/env bash
# deploy-oracle.sh: ship pushed `main` and the Mac's parquets to the Oracle box,
# restart the API once, and wait until it answers. Run it on the Mac, from any
# checkout. It changes nothing if the box is already current.
#
#   server/deploy-oracle.sh             deploy
#   server/deploy-oracle.sh --dry-run   say what would change, touch nothing
#   server/deploy-oracle.sh --restart   restart even if nothing changed
#
# See DEPLOY-oracle.md, "Updating the box". Overrides: SUNDAYDRIVE_BOX
# (user@host), SUNDAYDRIVE_BOX_KEY (ssh key), SUNDAYDRIVE_DATA_DIR (parquets).
set -euo pipefail

BOX=${SUNDAYDRIVE_BOX:-ubuntu@129.158.208.92}
KEY=${SUNDAYDRIVE_BOX_KEY:-$HOME/.ssh/scenic_oracle}
PUBLIC_HEALTH=https://api.jameskouvlis.com/api/health
MONITOR_KEYWORD=794685   # the UptimeRobot keyword: graph_nodes.parquet's row count
REQUIRED="graph_edges graph_nodes turn_restrictions"
OPTIONAL="access_ways access_entries"

dry_run=0 force_restart=0
for arg in "$@"; do
  case $arg in
    -n|--dry-run) dry_run=1 ;;
    --restart) force_restart=1 ;;
    *) echo "usage: $0 [--dry-run] [--restart]" >&2; exit 2 ;;
  esac
done

die() { echo "deploy: $*" >&2; exit 1; }
say() { echo "==> $*"; }

# The parquets are gitignored, so they exist only in the main checkout.
main_checkout=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
data=${SUNDAYDRIVE_DATA_DIR:-$main_checkout/data/processed-ne}
[ -d "$data" ] || die "no parquets at $data"

ctl=/tmp/sundaydrive-deploy-%C
ssh_cmd="ssh -i $KEY -o BatchMode=yes -o ControlMaster=auto -o ControlPath=$ctl -o ControlPersist=120"
box() { $ssh_cmd "$BOX" "$@"; }
trap '$ssh_cmd -O exit "$BOX" 2>/dev/null || true' EXIT

# --- 1. Code: the box clones from GitHub, so only what is pushed exists. ------
# This remote has printed "Everything up-to-date" after a failed push, so ask it.
say "checking origin/main"
local_main=$(git rev-parse main)
remote_main=$(git ls-remote origin refs/heads/main | cut -f1)
[ -n "$remote_main" ] || die "could not read origin/main"
[ "$local_main" = "$remote_main" ] || die "local main ${local_main:0:7} is not origin main ${remote_main:0:7}.
  Push it (DEPLOY-oracle.md 0.1) or pull it, then rerun."
main_head=$(git -C "$main_checkout" rev-parse HEAD)
[ "$main_head" = "$local_main" ] || echo "    warning: the main checkout, which built the parquets, is at ${main_head:0:7}, not main"

say "connecting to $BOX"
box true 2>/dev/null || die "ssh to $BOX failed. If the key has a passphrase:
  ssh-add --apple-use-keychain $KEY"

box_head=$(box 'git -C Scenic rev-parse HEAD')
[ -z "$(box 'git -C Scenic status --porcelain --untracked-files=no')" ] ||
  die "the box's checkout has local edits. Look at them before deploying over them."

# A docs-only change is pulled but does not restart anything.
RUNTIME="server/*.py pipeline/*.py server/requirements-serve.lock.txt"
code_changed=0 runtime_changed=0 deps_changed=0
if [ "$box_head" != "$local_main" ]; then
  code_changed=1
  if git cat-file -e "$box_head^{commit}" 2>/dev/null; then
    git merge-base --is-ancestor "$box_head" "$local_main" ||
      die "the box is at ${box_head:0:7}, which is not an ancestor of main"
    # shellcheck disable=SC2086
    git diff --quiet "$box_head" "$local_main" -- $RUNTIME || runtime_changed=1
    git diff --quiet "$box_head" "$local_main" -- server/requirements-serve.lock.txt || deps_changed=1
  else
    runtime_changed=1 deps_changed=1   # cannot tell; pip makes a reinstall a no-op if unchanged
  fi
fi

# --- 2. Data: hash both ends and copy only what differs. ----------------------
say "hashing parquets"
remote_hashes=$(box 'cd Scenic/data/processed-ne 2>/dev/null && sha256sum *.parquet || true')
changed=""
for p in $REQUIRED $OPTIONAL; do
  f=$data/$p.parquet
  if [ ! -f "$f" ]; then
    case " $REQUIRED " in *" $p "*) die "missing $f, which the server cannot start without" ;; esac
    echo "    warning: no $p.parquet on the Mac; destinations will snap to the wrong road"
    continue
  fi
  lh=$(shasum -a 256 "$f" | cut -d' ' -f1)
  rh=$(printf '%s\n' "$remote_hashes" | awk -v f="$p.parquet" '$2 == f { print $1 }')
  [ "$lh" = "$rh" ] || changed="$changed $p"
done

# --- 3. The plan. --------------------------------------------------------------
if [ $code_changed = 1 ]; then
  echo "    code: ${box_head:0:7} -> ${local_main:0:7}" \
    "($(git rev-list --count "$box_head..$local_main" 2>/dev/null || echo '?') commits)"
  if [ $runtime_changed = 0 ]; then
    echo "          docs only, no server code changed"
  else
    # shellcheck disable=SC2086
    git diff --stat "$box_head" "$local_main" -- $RUNTIME 2>/dev/null | sed 's/^/         /' || true
  fi
  [ $deps_changed = 1 ] && echo "    deps: requirements-serve.lock.txt changed, will reinstall"
else
  echo "    code: already at ${local_main:0:7}"
fi
if [ -n "$changed" ]; then
  for p in $changed; do echo "    data: $p.parquet ($(du -h "$data/$p.parquet" | cut -f1 | tr -d ' '))"; done
else
  echo "    data: all parquets match"
fi

restart=0
[ $runtime_changed = 1 ] || [ -n "$changed" ] || [ $force_restart = 1 ] && restart=1

if [ $code_changed = 0 ] && [ $restart = 0 ]; then
  say "nothing to deploy"; exit 0
fi
if [ $dry_run = 1 ]; then
  if [ $restart = 1 ]; then say "dry run: would restart the API (about 66 s of 502s)"
  else say "dry run: would pull, and not restart"; fi
  exit 0
fi

# --- 4. Ship. Code and data both land before the one restart: old code meeting
# new parquets is the KeyError: 'c_green' crash in DEPLOY.md. -------------------
if [ $code_changed = 1 ]; then
  say "pulling ${local_main:0:7} on the box"
  now=$(box "cd Scenic && git fetch -q origin main && git merge -q --ff-only $local_main && git rev-parse HEAD")
  [ "$now" = "$local_main" ] || die "the box ended up at ${now:0:7}, not ${local_main:0:7}"
fi
if [ $deps_changed = 1 ]; then
  say "installing the lock file"
  box 'Scenic/.venv/bin/python -m pip install -q -r Scenic/server/requirements-serve.lock.txt'
fi
if [ -n "$changed" ]; then
  say "copying parquets"
  files=""; for p in $changed; do files="$files $data/$p.parquet"; done
  box 'mkdir -p Scenic/data/processed-ne'
  # Plain -a --partial: macOS's openrsync rejects --append-verify and copies nothing.
  # shellcheck disable=SC2086
  rsync -a --partial -e "$ssh_cmd" $files "$BOX:Scenic/data/processed-ne/"
  # Verify by checksum, never by rsync's exit code.
  remote_hashes=$(box 'cd Scenic/data/processed-ne && sha256sum *.parquet')
  for p in $changed; do
    lh=$(shasum -a 256 "$data/$p.parquet" | cut -d' ' -f1)
    rh=$(printf '%s\n' "$remote_hashes" | awk -v f="$p.parquet" '$2 == f { print $1 }')
    [ "$lh" = "$rh" ] || die "$p.parquet hash mismatch after copy. The API is still running the old graph; rerun."
  done
fi

if [ $restart = 0 ]; then
  say "pulled ${local_main:0:7}; no server code or data changed, so the API was not restarted"
  exit 0
fi

# --- 5. Restart once, and wait for the graph to load. ------------------------
say "restarting sundaydrive-api (the graph takes about 66 s to load)"
started=$(date +%s)
box 'sudo systemctl restart sundaydrive-api'
if ! health=$(box 'for i in $(seq 90); do curl -sf http://127.0.0.1:5057/api/health && exit 0; sleep 2; done; exit 1'); then
  box 'systemctl status sundaydrive-api --no-pager; sudo journalctl -u sundaydrive-api -n 30 --no-pager' || true
  die "the API did not answer within 180 s of the restart"
fi
echo "    $health, after $(( $(date +%s) - started )) s"

# /api/health's node count must be the row count of the file that was loaded.
nodes=$(printf '%s' "$health" | sed -E 's/.*"nodes": *([0-9]+).*/\1/')
rows=$(box 'Scenic/.venv/bin/python -c "import pyarrow.parquet as pq; print(pq.ParquetFile(\"Scenic/data/processed-ne/graph_nodes.parquet\").metadata.num_rows)"')
[ "$nodes" = "$rows" ] || die "the API reports $nodes nodes but graph_nodes.parquet has $rows rows"
if [ "$nodes" != "$MONITOR_KEYWORD" ]; then
  echo "    warning: the graph now has $nodes nodes, not $MONITOR_KEYWORD. Update the UptimeRobot"
  echo "    keyword, DEPLOY-oracle.md, and MONITOR_KEYWORD in this script."
fi

# Idle reclaim is decided on memory alone for this box (DEPLOY-oracle.md Part 12).
mem=$(box "free | awk '/^Mem:/ { printf \"%d\", \$3 / \$2 * 100 }'")
echo "    box memory ${mem}% used"
[ "$mem" -ge 30 ] || echo "    warning: under 30%. Oracle reclaims below 20% over 7 days; see Part 12."

# --- 6. The public path. ------------------------------------------------------
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$PUBLIC_HEALTH" || true)
if [ "$code" = 200 ]; then
  say "deployed ${local_main:0:7}; $PUBLIC_HEALTH answers 200"
else
  die "the box is up, but $PUBLIC_HEALTH answered $code. Check cloudflared: systemctl status cloudflared"
fi
