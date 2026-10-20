#!/usr/bin/env bash
# deploy-oracle.sh: ship a pushed branch and the Mac's graph to the Oracle box,
# restart the API once, and check that it serves what was shipped. Run it on
# the Mac, from any checkout. It changes nothing if the box is already current.
#
#   server/deploy-oracle.sh                      the national server, from main
#   server/deploy-oracle.sh --ref usa            the national server, from usa
#   server/deploy-oracle.sh --region ne          New England, from main, as before
#   server/deploy-oracle.sh --dry-run ...        say what would change, touch nothing
#
# Options:
#   --region us|ne    which graph to serve (default us). us ships the pack and
#                     processed-us; ne ships processed-ne's parquets, with no pack
#   --ref BRANCH      the branch to deploy (default main). It must be pushed
#   --pack DIR        the pack to ship (us; default data/pack-us in the main checkout)
#   --data DIR        the parquets to ship (default data/processed-us or -ne)
#   --restart         restart even if nothing changed
#   --rehash          hash every file on the box instead of trusting its record
#   --allow-rewind    allow moving the box to a commit that does not contain
#                     its current one (a rollback, or usa back to main)
#
# See DEPLOY-oracle.md, "Updating the box", and docs/review-fixes-deploy.md.
# Overrides: SUNDAYDRIVE_BOX (user@host), SUNDAYDRIVE_BOX_KEY (ssh key),
# SUNDAYDRIVE_DATA_DIR and SUNDAYDRIVE_PACK_DIR (as --data and --pack).
set -euo pipefail

BOX=${SUNDAYDRIVE_BOX:-ubuntu@129.158.208.92}
KEY=${SUNDAYDRIVE_BOX_KEY:-$HOME/.ssh/scenic_oracle}
PUBLIC_HEALTH=${SUNDAYDRIVE_PUBLIC_HEALTH:-https://api.jameskouvlis.com/api/health}
NE_KEYWORD=794685   # New England's UptimeRobot keyword: its graph_nodes.parquet row count
REQUIRED="graph_edges graph_nodes turn_restrictions"
# Optional to the server, which starts without them. Not optional to a driver:
# without seasonal_closures the box routes over roads closed for the winter, and
# without closed_to_cars through locked gates and onto roads closed to cars, and
# without state_road_class onto Class VI and private roads (docs/state-road-class.md),
# and without osm_unpaved onto 4WD trails as if paved (docs/safety-quick-fixes.md).
# The same nine files are the ones a pack is fingerprinted against
# (pipeline/router.py, PACK_SOURCES), so they are what ships beside the pack.
OPTIONAL="access_ways access_entries seasonal_closures closed_to_cars state_road_class osm_unpaved"

# Only for exercising the script against a local fake box
# (docs/review-fixes-deploy.md, "The fake box"). Never set them for a real deploy.
UNIT_DIR=${SUNDAYDRIVE_UNIT_DIR:-/etc/systemd/system}
BOX_PORT=${SUNDAYDRIVE_BOX_PORT:-5057}

region=us ref=main pack_src=${SUNDAYDRIVE_PACK_DIR:-} data_src=${SUNDAYDRIVE_DATA_DIR:-}
dry_run=0 force_restart=0 rehash=0 allow_rewind=0
usage() { sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }
while [ $# -gt 0 ]; do
  case $1 in
    -n|--dry-run) dry_run=1 ;;
    --restart) force_restart=1 ;;
    --rehash) rehash=1 ;;
    --allow-rewind) allow_rewind=1 ;;
    --region) region=${2:?--region needs us or ne}; shift ;;
    --ref) ref=${2:?--ref needs a branch}; shift ;;
    --pack) pack_src=${2:?--pack needs a directory}; shift ;;
    --data) data_src=${2:?--data needs a directory}; shift ;;
    -h|--help) usage 0 ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
  shift
done

die() { echo "deploy: $*" >&2; exit 1; }
say() { echo "==> $*"; }
gb() { awk -v b="$1" 'BEGIN { if (b < 1e9) printf "%.0f MB", b / 1e6; else printf "%.1f GB", b / 1e9 }'; }

# The data is gitignored, so it exists only in the main checkout.
main_checkout=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
PY=$main_checkout/.venv/bin/python
[ -x "$PY" ] || PY=python3

# One layout on the box per region. The box's directory names never change,
# whatever the Mac's are called (data/pack-us-next ships to data/pack-us), so
# the unit only ever names these.
case $region in
  ne)
    data_src=${data_src:-$main_checkout/data/processed-ne}
    pack_src=""
    box_data=Scenic/data/processed-ne box_pack="" ;;
  us)
    data_src=${data_src:-$main_checkout/data/processed-us}
    pack_src=${pack_src:-$main_checkout/data/pack-us}
    box_data=Scenic/data/processed-us box_pack=Scenic/data/pack-us ;;
  *) die "--region is us or ne, not $region" ;;
esac
[ -d "$data_src" ] || die "no parquets at $data_src"

# A local sha256 at about 2 GB/s (openssl), or shasum's 0.3 GB/s without it.
if openssl dgst -sha256 -r /dev/null >/dev/null 2>&1; then
  lhash() { openssl dgst -sha256 -r "$1" | cut -d' ' -f1; }
else
  lhash() { shasum -a 256 "$1" | cut -d' ' -f1; }
fi
fsize() { wc -c < "$1" | tr -d ' '; }

# --- 1. Code: the box clones from GitHub, so only what is pushed exists. ------
# This remote has printed "Everything up-to-date" after a failed push, so ask it.
say "checking origin/$ref"
local_ref=$(git rev-parse --verify -q "refs/heads/$ref") || die "no local branch $ref"
remote_ref=$(git ls-remote origin "refs/heads/$ref" | cut -f1)
[ -n "$remote_ref" ] || die "could not read origin/$ref. Push it (DEPLOY-oracle.md 0.1)."
[ "$local_ref" = "$remote_ref" ] || die "local $ref ${local_ref:0:7} is not origin $ref ${remote_ref:0:7}.
  Push it (DEPLOY-oracle.md 0.1) or pull it, then rerun."
commit=$(git rev-parse --short=12 "$local_ref")
if [ $region = us ]; then
  # main can only serve New England until usa is merged into it.
  git grep -q SUNDAYDRIVE_PACK "$local_ref" -- server/app.py ||
    die "$ref (${commit:0:7}) cannot load a pack, so it cannot serve the national graph.
  Deploy --ref usa, or --region ne."
  code_pack_version=$(git show "$local_ref:pipeline/router.py" |
    sed -n 's/^ *PACK_VERSION *= *\([0-9][0-9]*\).*/\1/p' | head -1)
else
  main_head=$(git -C "$main_checkout" rev-parse HEAD)
  [ "$main_head" = "$local_ref" ] || echo "    warning: the main checkout, which built the parquets, is at ${main_head:0:7}, not $ref"
fi

# --- 2. The data on the Mac, checked before anything touches the box. ----------
# Each entry: "<box dir>|<local dir>|<file names>".
data_files=""
for p in $REQUIRED $OPTIONAL; do
  f=$data_src/$p.parquet
  if [ ! -f "$f" ]; then
    case " $REQUIRED " in *" $p "*) die "missing $f, which the server cannot start without" ;; esac
    case $p in
      seasonal_closures) cost="routes will use roads closed for the season (pipeline/closures.py builds it)" ;;
      closed_to_cars) cost="routes will drive through locked gates and roads closed to cars (pipeline/closures.py builds it)" ;;
      state_road_class) cost="routes will drive NH Class VI, VT trails and through private roads (pipeline/state_roads.py builds it)" ;;
      osm_unpaved) cost="routes will take TIGER's 4WD trails as paved (pipeline/closures.py builds it)" ;;
      *) cost="destinations will snap to the wrong road" ;;
    esac
    echo "    warning: no $p.parquet on the Mac; $cost"
    continue
  fi
  data_files="$data_files $p.parquet"
done
sets="$box_data|$data_src|$data_files"

pack_fp="" region_want="New England"
if [ $region = us ]; then
  [ -f "$pack_src/manifest.json" ] || die "no pack at $pack_src (tools/us_scale_router/pack.py builds one)"
  # The server refuses a pack whose sources no longer match the parquets beside
  # it (pipeline/router.py, _load_pack). Check that here, with the same
  # fingerprint, so a pack-us-next shipped beside the old processed-us fails on
  # the Mac and not on the box after a restart.
  pack_info=$("$PY" - "$pack_src" "$data_src" $REQUIRED $OPTIONAL <<'EOF'
import hashlib, json, os, sys
pack, data, names = sys.argv[1], sys.argv[2], sys.argv[3:]
m = json.load(open(os.path.join(pack, "manifest.json")))
here = {}
for p in names:
    f = os.path.join(data, p + ".parquet")
    if os.path.exists(f):
        size = os.path.getsize(f)
        with open(f, "rb") as fh:
            fh.seek(max(0, size - 65536))
            here[f"{p}.parquet"] = [size, hashlib.sha1(fh.read()).hexdigest()]
files = [a + ".npy" for a in m["arrays"]] + ["objects.pickle", "manifest.json"]
missing = [f for f in files if not os.path.isfile(os.path.join(pack, f))]
print("version", m["version"])
print("nodes", m["nodes"])
print("region", m.get("region") or "")
print("files", " ".join(files))
print("missing", " ".join(missing))
print("sources_match", int(here == m["sources"]))
print("sources_differ", " ".join(sorted(k for k in set(here) | set(m["sources"])
                                        if here.get(k) != m["sources"].get(k))))
EOF
)
  field() { printf '%s\n' "$pack_info" | sed -n "s/^$1 //p"; }
  [ -z "$(field missing)" ] || die "the pack at $pack_src is missing $(field missing)"
  [ "$(field version)" = "$code_pack_version" ] ||
    die "the pack is version $(field version), and $ref's router reads version ${code_pack_version:-?}.
  Rebuild it with tools/us_scale_router/pack.py."
  [ "$(field sources_match)" = 1 ] || die "the pack at $pack_src was not built from the parquets at $data_src.
  These differ: $(field sources_differ).
  The server would refuse it at startup. Ship the processed directory the pack was built from."
  region_want=$(field region)
  [ -n "$region_want" ] || die "the pack names no region (pack.py --region)"
  nodes_want=$(field nodes)
  pack_fp=$(lhash "$pack_src/manifest.json")
  sets="$sets
$box_pack|$pack_src|$(field files)"
else
  nodes_want=$("$PY" -c "import pyarrow.parquet as pq, sys; print(pq.ParquetFile(sys.argv[1]).metadata.num_rows)" \
    "$data_src/graph_nodes.parquet" 2>/dev/null || true)
fi

# --- 3. The box. -----------------------------------------------------------------
ctl=/tmp/sundaydrive-deploy-%C
ssh_cmd="ssh -i $KEY -o BatchMode=yes -o ControlMaster=auto -o ControlPath=$ctl -o ControlPersist=120"
box() { $ssh_cmd "$BOX" "$@"; }
# A script on stdin, its arguments after it. No argument may contain a space.
box_sh() { $ssh_cmd "$BOX" bash -s -- "$@"; }
trap '$ssh_cmd -O exit "$BOX" 2>/dev/null || true' EXIT

say "connecting to $BOX"
box true 2>/dev/null || die "ssh to $BOX failed. If the key has a passphrase:
  ssh-add --apple-use-keychain $KEY"
box_home=$(box 'printf %s "$HOME"')
box_head=$(box 'git -C Scenic rev-parse HEAD')
[ -z "$(box 'git -C Scenic status --porcelain --untracked-files=no')" ] ||
  die "the box's checkout has local edits. Look at them before deploying over them."

# A docs-only change is pulled but does not restart anything.
RUNTIME="server/*.py pipeline/*.py server/requirements-serve.lock.txt"
code_changed=0 runtime_changed=0 deps_changed=0 rewind=0
if [ "$box_head" != "$local_ref" ]; then
  code_changed=1
  if git cat-file -e "$box_head^{commit}" 2>/dev/null; then
    if ! git merge-base --is-ancestor "$box_head" "$local_ref"; then
      [ $allow_rewind = 1 ] || die "the box is at ${box_head:0:7}, which $ref does not contain.
  Deploying would drop those commits from the box. If that is the point (a
  rollback, or going from usa back to main), rerun with --allow-rewind."
      rewind=1
    fi
    # shellcheck disable=SC2086
    git diff --quiet "$box_head" "$local_ref" -- $RUNTIME || runtime_changed=1
    git diff --quiet "$box_head" "$local_ref" -- server/requirements-serve.lock.txt || deps_changed=1
  else
    runtime_changed=1 deps_changed=1   # cannot tell; pip makes a reinstall a no-op if unchanged
  fi
fi

# What the box holds: "<name> <sha256>" per file. A file is hashed on the box
# unless the record this script wrote after its last verified copy has the
# same size for it. Hashing reads the disk, and the boot volume is rated for
# about 24 MB/s (DEPLOY-oracle.md Part 14), so 19 GB of national data takes
# about 13 minutes; --rehash does it anyway.
REMOTE_STATE='
rehash=$1 d=$2; shift 2
cd "$d" 2>/dev/null || exit 0
for f in "$@"; do
  [ -f "$f" ] || continue
  s=$(wc -c < "$f" | tr -d " ")
  h=""
  [ "$rehash" = 1 ] || h=$(awk -v f="$f" -v s="$s" "\$3 == f && \$2 == s { print \$1 }" .deploy-sha256 2>/dev/null)
  [ -n "$h" ] || h=$(sha256sum "$f" | cut -d" " -f1)
  echo "$f $h"
done'

say "comparing the data at both ends"
plan_lines="" ship_bytes=0 changed_sets=""
records=""   # "<box dir>|<record text>", one per set, written after the copy
local_hashes=""   # "<local path> <sha256>", so nothing is hashed twice
while IFS='|' read -r -u 3 bdir ldir names; do
  [ -n "$bdir" ] || continue
  # shellcheck disable=SC2086
  remote=$(printf '%s\n' "$REMOTE_STATE" | box_sh "$rehash" "$bdir" $names)
  changed="" bytes=0 record=""
  for n in $names; do
    lh=$(lhash "$ldir/$n"); sz=$(fsize "$ldir/$n")
    local_hashes="$local_hashes$ldir/$n $lh
"
    record="$record$lh $sz $n
"
    rh=$(printf '%s\n' "$remote" | awk -v f="$n" '$1 == f { print $2 }')
    if [ "$lh" != "$rh" ]; then changed="$changed $n"; bytes=$((bytes + sz)); fi
  done
  # Files in the pack's directory that the pack no longer lists. The processed
  # directory holds other things, so nothing is removed from it.
  stale=""
  if [ "$bdir" = "$box_pack" ]; then
    for f in $(box "ls -A $bdir 2>/dev/null" || true); do
      case " $names .deploy-sha256 " in *" $f "*) ;; *) stale="$stale $f" ;; esac
    done
  fi
  count=$(echo $changed | wc -w | tr -d ' ')
  if [ "$count" = 0 ] && [ -z "$stale" ]; then
    plan_lines="$plan_lines    data: $bdir matches ($(echo $names | wc -w | tr -d ' ') files)
"
  else
    shown=$(echo $changed | tr ' ' '\n' | head -6 | tr '\n' ' ')
    [ "$count" -le 6 ] || shown="$shown... and $((count - 6)) more"
    plan_lines="$plan_lines    data: $bdir: $count of $(echo $names | wc -w | tr -d ' ') files to copy, $(gb $bytes)${shown:+ ($shown)}
"
    [ -z "$stale" ] || plan_lines="$plan_lines          and remove$stale, which the pack no longer lists
"
    changed_sets="$changed_sets$bdir|$ldir|$changed|$stale
"
  fi
  ship_bytes=$((ship_bytes + bytes))
  records="$records$bdir|$(printf '%s' "$record" | base64 | tr -d '\n')
"
done 3<<< "$sets"

# The unit. A drop-in overrides the Environment lines of the unit Part 8 of
# DEPLOY-oracle.md wrote, which stays as it is. An empty SUNDAYDRIVE_PACK means
# no pack (server/app.py), and an empty SUNDAYDRIVE_REGION lets the pack name it.
dropin=$UNIT_DIR/sundaydrive-api.service.d/deploy.conf
unit_body="[Service]
Environment=SUNDAYDRIVE_DATA=$box_home/$box_data
Environment=SUNDAYDRIVE_PACK=${box_pack:+$box_home/$box_pack}
Environment=SUNDAYDRIVE_REGION="
unit_now=$(box "cat $dropin 2>/dev/null" | grep -v -e '^#' -e 'SUNDAYDRIVE_COMMIT=' || true)
unit_changed=0
[ "$unit_now" = "$unit_body" ] || unit_changed=1
new_unit="# Written by server/deploy-oracle.sh on each restart. It overrides the
# Environment lines of sundaydrive-api.service; delete it to fall back to them.
$unit_body
Environment=SUNDAYDRIVE_COMMIT=$commit"

# Room on the box. The copy lands beside the live files, which the running
# server still holds until the restart, so it needs its own space.
free_kb=$(box "df -Pk Scenic/data 2>/dev/null || df -Pk Scenic" | awk 'NR == 2 { print $4 }')
free_bytes=$((free_kb * 1024))
headroom=$((2 * 1000 * 1000 * 1000))
mem_kb=$(box "awk '/^MemTotal:/ { print \$2 }' \${SUNDAYDRIVE_PROC:-/proc}/meminfo 2>/dev/null" || true)

# --- 4. The plan. --------------------------------------------------------------
echo "    serving: $region_want, ${nodes_want:-?} nodes${pack_fp:+, pack ${pack_fp:0:12}}"
if [ $code_changed = 1 ]; then
  if [ $rewind = 1 ]; then
    echo "    code: ${box_head:0:7} -> ${local_ref:0:7} ($ref, a rewind: ${box_head:0:7} is not in $ref)"
  else
    echo "    code: ${box_head:0:7} -> ${local_ref:0:7} ($ref," \
      "$(git rev-list --count "$box_head..$local_ref" 2>/dev/null || echo '?') commits)"
  fi
  if [ $runtime_changed = 0 ]; then
    echo "          docs only, no server code changed"
  else
    # shellcheck disable=SC2086
    git diff --stat "$box_head" "$local_ref" -- $RUNTIME 2>/dev/null | tail -1 | sed 's/^/         /' || true
  fi
  [ $deps_changed = 1 ] && echo "    deps: requirements-serve.lock.txt changed, will reinstall"
else
  echo "    code: already at ${local_ref:0:7} ($ref)"
fi
printf '%s' "$plan_lines"
if [ $unit_changed = 1 ]; then
  echo "    unit: $dropin becomes"
  printf '%s\n' "$unit_body" | sed -n 's/^Environment=/            /p'
else
  echo "    unit: already serves these paths"
fi
echo "    disk: $(gb $ship_bytes) to copy, $(gb $free_bytes) free on the box"
fits=1
[ $((ship_bytes + headroom)) -le $free_bytes ] || fits=0
[ $fits = 1 ] || echo "    PROBLEM: that leaves less than 2 GB free. See DEPLOY-oracle.md Part 14, \"Disk\"."
if [ $ship_bytes -gt 0 ]; then
  mins=$(( ship_bytes / 24000000 / 60 ))
  echo "          $([ $mins = 0 ] && echo 'under a minute' || echo "about $mins min") to write at the boot volume's rated 24 MB/s, and as long again to verify"
fi
if [ -n "$mem_kb" ]; then
  echo "    memory: the box has $(awk -v k="$mem_kb" 'BEGIN { printf "%.1f GiB", k / 1048576 }')"
  if [ $region = us ] && [ "$mem_kb" -lt 11000000 ]; then
    echo "    warning: the national server peaked at 4.1-4.8 GB under load, plus the OS, leaving"
    echo "    about 2.5 GB to cache an 11.9 GB pack. Resize to 12 GB first (DEPLOY-oracle.md Part 14)."
  fi
fi
monitor_line="UptimeRobot keyword must be ${nodes_want:-the node count /api/health reports}"
[ "$nodes_want" = "$NE_KEYWORD" ] || monitor_line="$monitor_line (New England's was $NE_KEYWORD)"
echo "    monitor: $monitor_line"

restart=0
[ $runtime_changed = 1 ] || [ -n "$changed_sets" ] || [ $unit_changed = 1 ] || [ $force_restart = 1 ] && restart=1

if [ $code_changed = 0 ] && [ $restart = 0 ]; then
  say "nothing to deploy"; exit 0
fi
if [ $dry_run = 1 ]; then
  [ $fits = 1 ] || die "dry run: this deploy would stop at the disk check"
  if [ $restart = 1 ]; then say "dry run: would restart the API"
  else say "dry run: would pull, and not restart"; fi
  exit 0
fi
[ $fits = 1 ] || die "not enough room on the box for the copy"

# --- 5. Ship. Data first, into a directory beside the live one, verified there;
# then the code; then one swap and one restart. Old code meeting new data is
# the KeyError: 'c_green' crash in DEPLOY.md, and a pack meeting parquets it was
# not built from is a server that refuses to start. ---------------------------
while IFS='|' read -r -u 3 bdir ldir changed stale; do
  [ -n "$bdir" ] || continue
  [ -n "$changed" ] || continue
  inc=$bdir.incoming
  say "copying $(echo $changed | wc -w | tr -d ' ') files to $inc"
  # Keep only what this copy will verify: a file left from an abandoned copy
  # would otherwise be swapped in unverified.
  # shellcheck disable=SC2086
  printf '%s\n' 'inc=$1; shift; mkdir -p "$inc"; cd "$inc"; for f in * .[!.]*; do [ -e "$f" ] || continue; case " $* " in *" $f "*) ;; *) rm -rf -- "$f" ;; esac; done' |
    box_sh "$inc" $changed
  files=""; for n in $changed; do files="$files $ldir/$n"; done
  # Plain -a --partial: macOS's openrsync rejects --append-verify and copies
  # nothing. -L because data/processed-us-next links the unchanged parquets.
  # shellcheck disable=SC2086
  rsync -a -L --partial -e "$ssh_cmd" $files "$BOX:$inc/"
  # Verify by checksum, never by rsync's exit code.
  say "verifying the copy"
  # shellcheck disable=SC2086
  remote=$(box "cd $inc && sha256sum $changed")
  for n in $changed; do
    lh=$(printf '%s' "$local_hashes" | awk -v f="$ldir/$n" '$1 == f { print $2 }')
    rh=$(printf '%s\n' "$remote" | awk -v f="$n" '$2 == f || $2 == "*" f { print $1 }')
    if [ "$lh" != "$rh" ]; then
      box "rm -f $inc/$n"
      die "$n hash mismatch after copy. Nothing was swapped in, and the API is still serving the old graph; rerun."
    fi
  done
done 3<<< "$changed_sets"

if [ $code_changed = 1 ]; then
  say "checking out ${local_ref:0:7} on the box"
  # Detached, so a deploy of usa does not move the box's main, and a deploy
  # of main can come back to it.
  now=$(box "cd Scenic && git fetch -q origin $ref && git checkout -q --detach $local_ref && git rev-parse HEAD")
  [ "$now" = "$local_ref" ] || die "the box ended up at ${now:0:7}, not ${local_ref:0:7}"
fi
if [ $deps_changed = 1 ]; then
  say "installing the lock file"
  box 'Scenic/.venv/bin/python -m pip install -q -r Scenic/server/requirements-serve.lock.txt'
fi

if [ $restart = 0 ]; then
  say "checked out ${local_ref:0:7}; no server code or data changed, so the API was not restarted"
  exit 0
fi

# The swap: each verified file is renamed over the live one, which the running
# server keeps open until the restart below. Then the record of what is there.
# A new manifest.json goes in last, and the old one comes out first: if the
# server restarted on its own in between, it would find no manifest and fail,
# rather than map half of one pack and half of another.
SWAP='
d=$1 rec=$2; shift 2
mkdir -p "$d"
if [ -d "$d.incoming" ]; then
  [ -e "$d.incoming/manifest.json" ] && rm -f "$d/manifest.json"
  for f in "$d.incoming"/*; do
    [ -e "$f" ] && [ "${f##*/}" != manifest.json ] && mv -f "$f" "$d/"
  done
  [ -e "$d.incoming/manifest.json" ] && mv -f "$d.incoming/manifest.json" "$d/"
  rm -rf "$d.incoming"
fi
for s in "$@"; do rm -f -- "$d/$s"; done
printf %s "$rec" | base64 -d > "$d/.deploy-sha256.new" && mv -f "$d/.deploy-sha256.new" "$d/.deploy-sha256"'
if [ -n "$changed_sets" ]; then say "swapping in the new data"; else say "recording what the box holds"; fi
while IFS='|' read -r -u 3 bdir rec; do
  [ -n "$bdir" ] || continue
  stale=$(printf '%s' "$changed_sets" | awk -F'|' -v d="$bdir" '$1 == d { print $4 }')
  # shellcheck disable=SC2086
  printf '%s\n' "$SWAP" | box_sh "$bdir" "$rec" $stale
done 3<<< "$records"

say "writing the unit's environment (commit $commit)"
printf '%s\n' "$new_unit" | box "sudo mkdir -p $(dirname "$dropin") && sudo tee $dropin >/dev/null && sudo systemctl daemon-reload"
printf '%s\n' "$commit" | box 'cat > Scenic/DEPLOYED_COMMIT'

# --- 6. Restart once, and wait for the graph to load. ------------------------
# New England builds its graph in about 66 s. The national server maps its pack,
# but reads 3.2 GB of it in at start, from a disk rated for about 24 MB/s.
wait_s=180; [ $region = us ] && wait_s=600
say "restarting sundaydrive-api (waiting up to $wait_s s for it to answer)"
started=$(date +%s)
box 'sudo systemctl restart sundaydrive-api'
if ! health=$(box "for i in \$(seq $((wait_s / 2))); do curl -sf http://127.0.0.1:$BOX_PORT/api/health && exit 0; sleep 2; done; exit 1"); then
  box 'systemctl status sundaydrive-api --no-pager; sudo journalctl -u sundaydrive-api -n 30 --no-pager' || true
  die "the API did not answer within $wait_s s of the restart"
fi
echo "    $health, after $(( $(date +%s) - started )) s"

if [ $region = ne ]; then
  # The router logs the closure and road-class counts as it builds the graph,
  # flushed so the journal keeps them. "none" or no line at all means the box
  # is routing over closed roads.
  for what in 'seasonal closures' 'closed to cars' 'state road classes' "unpaved by TIGER"; do
    line=$(box "sudo journalctl -u sundaydrive-api --since @$started --no-pager -o cat | grep '$what' | tail -1" || true)
    echo "    ${line:-warning: no '$what' line in the journal since the restart}"
  done
  # /api/health's node count must be the row count of the file that was loaded.
  rows=$(box "Scenic/.venv/bin/python -c \"import pyarrow.parquet as pq; print(pq.ParquetFile('$box_data/graph_nodes.parquet').metadata.num_rows)\"")
  [ -n "$nodes_want" ] || nodes_want=$rows
  [ "$rows" = "$nodes_want" ] || die "the box's graph_nodes.parquet has $rows rows, and the Mac's has $nodes_want"
else
  # A pack logs nothing as it loads: the closure tables are inside it, and
  # step 2 checked that it was built from all of them.
  echo "    the pack was built from:$data_files"
fi

# What the server says it serves, against what was shipped (/api/health,
# docs/review-fixes-deploy.md, "What /api/health must say").
"$PY" - "$health" "$region_want" "$nodes_want" "$commit" "$pack_fp" <<'EOF' || die "the API is up, but not serving what was shipped (above)"
import json, sys
health, region, nodes, commit, pack = sys.argv[1:6]
h = json.loads(health)
bad = []
def say(level, text):
    print(f"    {level}: {text}")
    if level == "PROBLEM":
        bad.append(text)
say("ok" if str(h.get("nodes")) == nodes else "PROBLEM", f"nodes {h.get('nodes')}, shipped {nodes}")
for key in ("region", "commit", "pack"):
    if key not in h:
        say("warning", f"/api/health has no '{key}' yet, so it cannot be checked")
if "region" in h:
    say("ok" if h["region"] == region else "PROBLEM", f"region {h['region']!r}, shipped {region!r}")
if "commit" in h:
    c = h["commit"] or ""
    ok = len(c) >= 7 and (c.startswith(commit) or commit.startswith(c))
    say("ok" if ok else "PROBLEM", f"commit {h['commit']}, shipped {commit}")
if "pack" in h:
    p = h["pack"]
    ok = p is None if not pack else (isinstance(p, str) and len(p) >= 8 and pack.startswith(p))
    say("ok" if ok else "PROBLEM", f"pack {p if p is None else p[:12]}, shipped {pack[:12] or None}")
sys.exit(1 if bad else 0)
EOF

# Memory, for idle reclaim (DEPLOY-oracle.md Part 12) and for whether the pack
# is being read from disk again and again (Part 14, "Memory check").
box_sh <<'EOF' || true
P=${SUNDAYDRIVE_PROC:-/proc}
pid=$(systemctl show -p MainPID --value sundaydrive-api)
awk '/^(MemTotal|MemAvailable|SwapTotal|SwapFree):/ { m[$1] = $2 }
  END { printf "    box memory: %.0f%% used (%.1f of %.1f GiB), swap %.2f GiB used\n",
        (m["MemTotal:"] - m["MemAvailable:"]) / m["MemTotal:"] * 100,
        (m["MemTotal:"] - m["MemAvailable:"]) / 1048576, m["MemTotal:"] / 1048576,
        (m["SwapTotal:"] - m["SwapFree:"]) / 1048576 }' "$P/meminfo"
awk '/^(RssAnon|RssFile|VmSwap):/ { printf "%s %.2f GiB  ", $1, $2 / 1048576 } END { print "" }' "$P/$pid/status" | sed 's/^/    server: /'
EOF
mem=$(box "awk '/^MemTotal:/ { t = \$2 } /^MemAvailable:/ { a = \$2 } END { printf \"%d\", (t - a) / t * 100 }' \${SUNDAYDRIVE_PROC:-/proc}/meminfo" || true)
mem=${mem:-100}
[ "$mem" -ge 30 ] || echo "    warning: under 30%. Oracle reclaims below 20% over 7 days; see Part 12."

# --- 7. The public path. ------------------------------------------------------
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$PUBLIC_HEALTH" || true)
[ "$code" = 200 ] || die "the box is up, but $PUBLIC_HEALTH answered $code. Check cloudflared: systemctl status cloudflared"
say "deployed ${local_ref:0:7} ($ref, $region_want); $PUBLIC_HEALTH answers 200"
echo "    $monitor_line"
