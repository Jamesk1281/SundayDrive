# Deploying the Sunday Drive API to Oracle Cloud Always Free — end to end

**Status: written 2026-09-19 against `main` at `2d6fbc0`. Nothing here has been
executed — no Oracle account exists and nothing was provisioned.** Every command
below was checked against the code it runs (`server/serve.py`, `server/app.py`,
`server/requirements-serve.lock.txt`) and against the figures re-measured in
[`docs/hosting-status-2026-09.md`](../docs/hosting-status-2026-09.md), but the
box itself is hypothetical until you build it.

This is the follow-along version of the runbook in
[`docs/hosting-options-findings.md`](../docs/hosting-options-findings.md#setup-runbook).
That document argues *why* Oracle; this one is what you type. Read
[Before you start](#before-you-start) in full — two of the five prerequisites
have bitten this project before.

**Time:** about an hour of hands-on work, spread over ~2 hours with the waiting.
**Plus** an unbounded amount if A1 capacity is not available — see
[Part 2](#part-2--create-the-instance).
**Difficulty:** the Linux half is copy-paste. The three fiddly parts are the
sign-up, the capacity lottery, and moving the tunnel credentials off the laptop.
**Risk:** low. The laptop keeps serving the whole time, and rollback is one
command.

---

## Before you start

| you need | why | check it now |
|---|---|---|
| **~1 hour, uninterrupted-ish** | The long waits are the 382 MB upload and a ~2 min graph load | |
| **A payment card** | Oracle verifies identity with it. Always Free is not charged, but you cannot sign up without one | |
| **An email address you actually read** | The 18 Aug 2026 entitlement enforcement was announced **by email and nowhere else**. That mailbox is your only warning if the allowance is cut again | |
| **The Windows laptop switched ON** | Part 9 copies the existing Cloudflare tunnel's credentials off it. Without them you would have to create a *new* tunnel and repoint DNS | |
| **`main` pushed to GitHub** | The box installs by `git clone`. As of 2026-09-19 `origin/main` is **36 commits behind** local `main` — a clone today gets code from before A\* landed | `git rev-list --count origin/main..main` |

**Do Part 0 on the Mac before you open Oracle's site at all.** Two of those five
are Mac-side work, and discovering them halfway through a migration is how this
project lost an afternoon in August.

### The one irreversible decision

**The home region.** Always Free compute exists *only* in your account's home
region, and it cannot be changed afterwards — a new region means a new account.
The recommendation is **`us-chicago-1`**, measured at +12 ms RTT from Boston
against +81 ms for Frankfurt. Everything else in this document is reversible.

---

## Part 0 — On the Mac, before you touch Oracle

### 0.1 Push `main`, and verify it actually pushed

The serving box clones from GitHub, so anything unpushed does not exist as far
as the deployment is concerned. **This remote fails in a way that lies to you:**
the push dies with `HTTP 400` and then prints `Everything up-to-date`.

```bash
git -c http.version=HTTP/1.1 -c http.postBuffer=524288000 push origin main
```

Then verify, because the success message is not trustworthy:

```bash
git ls-remote origin refs/heads/main && git rev-parse main
```

**Those two hashes must match.** If they do not, the push failed regardless of
what it printed. (The repo is public, so the box can clone it with no
credentials and no deploy key.)

### 0.2 Make an SSH key, if you do not have one

Oracle asks for a public key while creating the instance, and there is no
password login to fall back on.

```bash
ssh-keygen -t ed25519 -C "scenic-oracle" -f ~/.ssh/scenic_oracle
```

Then have the **public** half ready to paste — this is the one you upload:

```bash
cat ~/.ssh/scenic_oracle.pub
```

Never paste the file *without* `.pub`; that one is the private key and it never
leaves the Mac.

### 0.3 Record what a good box looks like

Run the suite locally now, so you have a baseline to compare the box against
rather than a number from a document:

```bash
SUNDAYDRIVE_DATA="$PWD/data/processed-ne" .venv/bin/python -m pytest tests/ -q
```

Write down the pass/skip/fail counts. **379 tests collect** as of 2026-09-19.
The important figure is the **skip count**, not the passes — see
[Part 7](#part-7--verify-before-exposing-anything).

---

## Part 1 — Account and home region

1. Go to Oracle Cloud Free Tier and sign up. Use the email from the table above.
2. When asked for **Home Region**, choose **US Midwest (Chicago)** =
   `us-chicago-1`. Fallback: **US East (Ashburn)** = `us-ashburn-1`.
   **This is the irreversible click.** Do not accept whatever it defaults to.
3. Finish verification. Sign-ups are sometimes rejected outright; if yours is,
   that is an Oracle decision and not something the rest of this document can
   route around.

> **I cannot do this part for you, and neither can any agent** — it involves
> entering personal and card details, which is yours to do.

---

## Part 2 — Create the instance

Console → **Compute → Instances → Create instance**.

| field | value | why |
|---|---|---|
| Image | **Ubuntu 24.04** | Ships Python 3.12; the lock file needs 3.10–3.13 |
| Shape | **`VM.Standard.A1.Flex`** | The Ampere ARM shape. *Not* the E2.1.Micro |
| OCPUs | **2** | The whole entitlement. Never more — see [the landmine](#the-landmine-never-exceed-the-entitlement) |
| Memory | **8 GB** | **Deliberately not 12.** See [idle reclaim](#part-12--the-two-things-that-keep-the-box-alive) |
| Boot volume | **50 GB** | Well inside the 200 GB allowance; leaves room for the 382 MB of data and logs |
| SSH key | paste `~/.ssh/scenic_oracle.pub` | The only way in |
| Networking | default VCN, **assign a public IPv4** | |
| Security list | **leave closed** | The tunnel dials *out*. Nothing needs to reach the box inbound except your SSH |
| Oracle Cloud Agent → Monitoring | **leave enabled** | Reported memory utilisation is what keeps the box off the reclaim list |

Note the **public IP** when it finishes provisioning.

### If you get `Out of host capacity`

This is the expected failure and it is not your fault — A1 is scarce in exactly
the US regions. Oracle's own documented remedy is to wait and retry.

- Try **each availability domain** in the region.
- Then retry a few times a day, for up to **14 days**.
- At 14 days, stop grinding and pick deliberately: keep retrying (the laptop is
  still serving), accept `eu-frankfurt-1` at a measured +81 ms per round trip,
  or take the paid exit (Contabo, ~€5.50/mo).

The laptop serving throughout is the entire point of this ordering. Nothing is
broken while you wait.

---

## Part 3 — First login and base packages

```bash
ssh -i ~/.ssh/scenic_oracle ubuntu@<INSTANCE_IP>
```

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git rsync
```

### Optional but recommended: a swap file

The working set is **~4.4 GB peak, ~4.8 GB once the loop caches warm** on an
8 GB box. That fits, but with less air than the original 3.53 GB figure
suggested, and an OOM kill costs a ~2 minute reload. 4 GB of swap on a 50 GB
boot volume is cheap insurance:

```bash
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

> **Do not** use swap to justify a smaller instance. Routing is numpy over
> ~800k-node tables; if it swaps during a route, the route takes seconds.

---

## Part 4 — The code

```bash
git clone https://github.com/Jamesk1281/Scenic.git ~/Scenic && cd ~/Scenic && git log --oneline -1
```

**Compare that hash against `git log --oneline -1` on the Mac before going any
further.** `DEPLOY.md` records a real incident where old code met new parquets
and died with `KeyError: 'c_green'` — a 502 that looks exactly like a bad file
copy. If the hashes differ, go back to [0.1](#01-push-main-and-verify-it-actually-pushed).

---

## Part 5 — Dependencies, from the lock file

```bash
python3 -m venv ~/Scenic/.venv && ~/Scenic/.venv/bin/python -m pip install -r ~/Scenic/server/requirements-serve.lock.txt
```

Eleven pinned packages — geopandas, pandas, shapely, pyarrow, numpy, scipy,
pyproj, Flask, flask-cors, Flask-Compress, waitress. On `aarch64` all eleven
have prebuilt wheels and **nothing compiles**.

> **If you see a compiler invoked, stop.** It means the wrong Python (needs
> 3.10–3.13) or the wrong libc. Building scipy from source on 2 OCPUs is an
> hour you do not need to spend, and the result would be unpinned anyway.

---

## Part 6 — The data, 382 MB, from the Mac

The parquets are not in git. Create the directory first — `rsync` will not make
a nested path for you:

```bash
ssh -i ~/.ssh/scenic_oracle ubuntu@<INSTANCE_IP> 'mkdir -p ~/Scenic/data/processed-ne'
```

Then, **from the Mac**, in the repo root:

```bash
rsync -avP --append-verify -e "ssh -i ~/.ssh/scenic_oracle" data/processed-ne/graph_edges.parquet data/processed-ne/graph_nodes.parquet data/processed-ne/turn_restrictions.parquet data/processed-ne/access_ways.parquet data/processed-ne/access_entries.parquet ubuntu@<INSTANCE_IP>:~/Scenic/data/processed-ne/
```

| file | size | required? |
|---|---|---|
| `graph_edges.parquet` | 197.1 MB | **yes** |
| `graph_nodes.parquet` | 16.9 MB | **yes** |
| `turn_restrictions.parquet` | 0.2 MB | **yes** — the server refuses to start without it |
| `access_ways.parquet` | 136.0 MB | optional, but destinations snap to the wrong road without it |
| `access_entries.parquet` | 31.9 MB | optional, same |

`--append-verify` is what makes a dropped home-upload connection resumable:
re-run the identical command until it completes clean.

---

## Part 7 — Verify before exposing anything

```bash
cd ~/Scenic && .venv/bin/python -m pip install pytest && SUNDAYDRIVE_DATA=~/Scenic/data/processed-ne .venv/bin/python -m pytest tests/ -q
```

**Compare against the baseline you took in [0.3](#03-record-what-a-good-box-looks-like), not against a number in a document.**
The suite has grown from 207 tests to 379 since the original runbook was
written, and at least one test is currently red against `data/processed-ne` on
the Mac too — so a hard-coded expectation would either stop you for nothing or
miss a real problem.

What each outcome means:

- **Skips: 4** — the access layer loaded. **8 skips** means the two optional
  parquets never made it across; go back to Part 6.
- **A failure that also fails on the Mac** — pre-existing, not your migration.
- **A failure that passes on the Mac** — the code and the data disagree. **Stop.**
  Check the commit hashes at both ends before debugging anything else.

Then load the graph by hand once, to see the startup cost with your own eyes:

```bash
cd ~/Scenic && SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=~/Scenic/data/processed-ne .venv/bin/python server/serve.py
```

In a second SSH session:

```bash
curl -s http://localhost:5057/api/health
```

Expect exactly:

```json
{"status":"ok","nodes":794685,"routing_slots":801719}
```

**`794685` is the check.** It is the row count of `graph_nodes.parquet`; a
different number means the wrong parquets. (`routing_slots` is higher because
the router splits junctions that carry turn restrictions.) Then `Ctrl-C` it —
systemd takes over next.

---

## Part 8 — systemd

```bash
sudo tee /etc/systemd/system/sundaydrive-api.service >/dev/null <<'EOF'
[Unit]
Description=Sunday Drive routing API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Scenic
Environment=SUNDAYDRIVE_HOST=127.0.0.1
Environment=SUNDAYDRIVE_DATA=/home/ubuntu/Scenic/data/processed-ne
ExecStart=/home/ubuntu/Scenic/.venv/bin/python /home/ubuntu/Scenic/server/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now sundaydrive-api
```

Three things about this unit:

- **`SUNDAYDRIVE_HOST=127.0.0.1`** — `serve.py` defaults to `0.0.0.0` so a phone can
  reach a dev server. On a deployed box, `cloudflared` reaches it over loopback
  and nothing else should.
- **`Restart=always`** is the thing the Windows setup never actually had. This
  is the concrete reliability difference between the two options.
- **The unit reports `active` the moment the process forks, but the graph needs
  ~100–125 s before it answers.** (It is 49.9 s on an M2; an A1 core is under
  half that.) Do not let a monitor page you during a restart, and do not assume
  a failure because `curl` refuses for the first two minutes.

```bash
systemctl status sundaydrive-api --no-pager
journalctl -u sundaydrive-api -f
```

---

## Part 9 — The tunnel

**This is the fiddly part, and it needs the Windows laptop switched on.** You
are moving an *existing* named tunnel (`scenic`), not making a new one — the DNS
record at Cloudflare already points at it, which is why no DNS change and no new
app build are needed.

Install `cloudflared` on the box (ARM64 build):

```bash
curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o /tmp/cloudflared.deb && sudo dpkg -i /tmp/cloudflared.deb && cloudflared --version
```

### 9.1 Find the tunnel's credentials on the laptop

On **Windows**, in PowerShell:

```powershell
cloudflared tunnel list
```

Note the tunnel's **UUID**. Its credentials file is
`C:\Users\<you>\.cloudflared\<UUID>.json`.

### 9.2 Copy it to the box

That file is a **secret** — it is the tunnel's identity. Move it directly from
the laptop to the box; do not paste its contents anywhere, including into a chat
with me.

```powershell
scp -i <key> C:\Users\<you>\.cloudflared\<UUID>.json ubuntu@<INSTANCE_IP>:/tmp/
```

Then on the box:

```bash
sudo mkdir -p /etc/cloudflared && sudo mv /tmp/<UUID>.json /etc/cloudflared/ && sudo chmod 600 /etc/cloudflared/<UUID>.json
```

### 9.3 Write the config

```bash
sudo tee /etc/cloudflared/config.yml >/dev/null <<'EOF'
tunnel: <UUID>
credentials-file: /etc/cloudflared/<UUID>.json

ingress:
  - hostname: api.jameskouvlis.com
    service: http://localhost:5057
  - service: http_status:404
EOF
```

### 9.4 Do not start it yet

Starting it now gives the named tunnel **two** connectors, and Cloudflare will
load-balance between the laptop and a box that may not be warm. Go to Part 10.

---

## Part 10 — Cut over

**Order matters.** On the **laptop** first, stop the tunnel (close the
`Sunday Drive Tunnel` window, or stop its service/scheduled task).

Confirm the old connector is gone — from anywhere:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.jameskouvlis.com/api/health
```

`530` is what you want to see at this moment: tunnel with no origin. Then on the
**box**:

```bash
sudo cloudflared service install && sudo systemctl enable --now cloudflared
```

And verify the whole path, from anywhere:

```bash
curl -s https://api.jameskouvlis.com/api/health
```

`{"status":"ok","nodes":794685,...}` through the public hostname means you are
done. The iOS app needs **no new build** — `SundayDriveAPIBaseURL` names the
hostname, and the tunnel is the switch.

---

## Part 11 — Rate limit

The API has no auth and permissive CORS, and each request is CPU that the four
threads do **not** parallelise — the real ceiling is nearer **5 req/s**, so one
runaway loop in a script is a denial of service.

`dash.cloudflare.com` → your domain → **Security → WAF → Rate limiting rules**.
Match `http.host eq "api.jameskouvlis.com"`, count by IP, cap at **60
requests/minute**. The rate goes in the "When rate exceeds" fields, *not* in the
match expression. 60 rather than 30 because the app legitimately bursts: seven
sliders that each re-route on release, plus off-route reroutes every 8 s.

---

## Part 12 — The two things that keep the box alive

### Idle reclamation

Oracle reclaims an Always Free instance if, over 7 days, **all three** hold:
CPU 95th percentile < 20%, network < 20%, **and** memory < 20% (A1 only). A
single-user routing API is unambiguously idle on the first two, so **memory is
the only thing keeping the box alive.**

| instance memory | Sunday Drive at ~4.4 GB | verdict |
|---|---|---|
| 12 GB (the full entitlement) | 37% | safe |
| **8 GB (what you built)** | **55%**, 60% warm | **safe, with margin** |

This is why you provisioned 8 GB rather than the 12 you are entitled to: **more
RAM lowers the percentage and moves the box towards reclamation.** Keep the
Oracle Cloud Agent monitoring plugin enabled — an instance that reports no
memory metric is not one that reports high memory.

**Do not fake load to defeat this.** Sunday Drive genuinely holds the working set; a
cron job burning CPU to look busy is both unnecessary and the sort of thing that
reads badly in an account review.

### The mailbox

The June 2026 halving had **no announcement** and the August enforcement was
**email only**. Read that mailbox. It is the entire early-warning system.

### Monitoring

A free UptimeRobot monitor on `https://api.jameskouvlis.com/api/health`, 5-minute
interval, **keyword `794685`** — asserting the keyword rather than just a 200
catches a box serving the *wrong graph*, which a liveness check cannot see.
Alert to an address you read.

---

## Part 13 — Measure it, and write the numbers down

```bash
systemctl status sundaydrive-api --no-pager | grep Memory
ps -o rss= -p $(pgrep -f 'serve.py') | awk '{printf "%.2f GB\n", $1/1048576}'
time curl -s "https://api.jameskouvlis.com/api/route?from=42.3601,-71.0589&to=44.3106,-69.7795&pref=0.5" -o /dev/null
```

| measure | expected on A1 | measured on the Mac, 2026-09-19 |
|---|---|---|
| peak RSS | **4.2–5.0 GB** | 4.39 GB |
| load time | **100–125 s** | 49.9 s |
| one API request (two arms) | **~1.0–1.3 s** | ~470 ms warm |

The A1 column is scaled from the Mac by the same factor
`hosting-options-findings.md` used, **not** measured — replace it with real
numbers once the box exists. Two results deserve investigation rather than a
shrug: **above 5.5 GB** (something is holding more than the graph) and **below
2.4 GB** (the idle-reclaim maths needs redoing, because you are approaching the
20% floor).

---

## Rollback

At any point, including after cutover:

1. Stop the tunnel on the box: `sudo systemctl stop cloudflared`.
2. Start `cloudflared` on the laptop again.

That is the whole rollback. No DNS change, no App Review, no new build. The
Oracle box can sit there stopped while you decide.

---

## Troubleshooting

| symptom | almost certainly | fix |
|---|---|---|
| `HTTP 530` from the public hostname | Tunnel up, **no origin** — the service is down or still loading | Wait 2 min for the graph, then `journalctl -u sundaydrive-api -n 50` |
| `HTTP 502` | `cloudflared` reached the box but the app is not on `:5057` | `systemctl status sundaydrive-api`; an `ImportError` at startup looks exactly like this |
| `KeyError: 'c_green'` or similar at startup | **Old code, new parquets** | Compare `git log --oneline -1` at both ends |
| `/api/health` reports a node count that is not 794685 | Wrong or partial parquets | Re-run Part 6; `--append-verify` makes it safe to repeat |
| 8 skips in the test suite | The two optional access parquets did not arrive | Re-run Part 6 |
| `curl localhost:5057` refused, but the service is `active` | The graph is still loading | It is ~100–125 s. `active` ≠ answering |
| Intermittent answers, some stale | **Two connectors on one tunnel** | Stop `cloudflared` on the laptop — Part 10, in order |
| `Out of host capacity` | A1 scarcity, not your account | Part 2's 14-day rule |
| Route requests time out under load | You are at the ~5 req/s ceiling | That is the documented ceiling, not a bug. Part 11 |

### The landmine: never exceed the entitlement

The Always Free A1 allowance is **2 OCPU and 12 GB total, per tenancy** — and
2 OCPU running continuously is 1,488 hours in a 31-day month against an
allowance of 1,500. It fits with about six hours of slack, which means:

- **You cannot run two 2-OCPU instances side by side**, not even briefly for a
  parallel-run window. If you want an overlap, make each instance 1 OCPU.
- **Never resize above 2 OCPU.** On 18 Aug 2026 Oracle terminated instances that
  exceeded the (silently halved) entitlement, with an email as the only warning,
  and its own FAQ says reclaimed resources "can't be restored". At least one
  user reports the boot volume went with the instance.

Which is the real reason to keep this box reproducible from the repo: everything
on it is a `git clone`, eleven pinned wheels, 382 MB of parquet you can re-copy,
and the two unit files above.

---

## What this does not cover

- **Rebuilding the graph.** The pipeline never runs on this box — you build
  parquets on the Mac and `rsync` them. See the top-level README.
- **A second worker.** At ~4.4 GB each, two processes need ~8.8 GB and **do not
  fit in 8 GB** — a correction to the old "around two workers" figure, which was
  derived from a 3.53 GB measurement that
  [`docs/hosting-status-2026-09.md`](../docs/hosting-status-2026-09.md) shows was
  an under-read. Routing does not parallelise anyway.
- **Whether to do this at all.** `docs/release-plan.md` §7 rates keeping the
  laptop up and migrating as *both* acceptable for launch. This document is what
  the second option costs, not an argument for it.
