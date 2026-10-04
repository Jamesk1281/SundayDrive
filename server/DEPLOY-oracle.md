# Deploying the Sunday Drive API to Oracle Cloud Always Free — end to end

**Status: written 2026-09-19 against `main` at `2d6fbc0`. Executed end to end
on 2026-09-28/29 against `main` at `3402298`. The box exists, and
`api.jameskouvlis.com` has been served from it since 2026-09-29 04:15 UTC.**
It runs in `us-ashburn-1`, AD-3, on `VM.Standard.A1.Flex` with 2 OCPU and
8 GB, on a VCN named `sundaydrive`. The first run found five things this
document had wrong. Each one is corrected where it bites, and all of them are
listed under [What the first run changed](#what-the-first-run-changed). The
figures under [Part 13](#part-13--measure-it-and-write-the-numbers-down) are
now measured on the box, not scaled from the Mac.

The 2026-09-28 independent review (`docs/hosting-independent-review.md`, on
branch `claude/sunday-drive-hosting-review-c9c122`) recommends running this box
*beside* a hardened laptop, as a second health-gated connector, rather than as
a replacement. Everything below is still step one of that plan. Only
[Part 10](#part-10--cut-over) and [Rollback](#rollback) change under it.

This is the follow-along version of the runbook in
[`docs/hosting-options-findings.md`](../docs/hosting-options-findings.md#setup-runbook).
That document argues *why* Oracle; this one is what you type. Read
[Before you start](#before-you-start) in full. One of its rows has a hard
deadline, and another used to be wrong.

**Time:** on the first run, about 40 minutes passed from opening the instance
form to going live. The console's generated names put that at 23:38 and 00:15
EDT. Sign-up came before that and was not timed. The test suite (8 min) and
the graph load (66 s) were the only real waits. The 382 MB upload took 16 s.
**Plus** an unbounded amount if A1 capacity is not available — see
[Part 2](#part-2--create-the-instance). On the first run it was available on
the day.
**Difficulty:** the Linux half is copy-paste. The fiddly parts are the sign-up,
the console's networking form ([Part 2](#part-2--create-the-instance)), and a
browser click with a timeout ([Part 9](#part-9--the-tunnel)).
**Risk:** low, and rollback is two commands. **But do not assume the laptop is
serving while you work.** On 2026-09-28 it was off, and the API was returning
530 before the migration started.

---

## Before you start

| you need | why | check it now |
|---|---|---|
| **~1 hour, uninterrupted-ish** | The long waits are the 8-minute test suite and the ~1 minute graph load | |
| **`jameskouvlis.com` registered for longer than the box will live** | It **expires 2026-10-28** (RDAP, read 2026-09-28; registrar GoDaddy). The app has `api.jameskouvlis.com` built in, so a lapsed domain breaks every installed copy until a new build passes App Review. No host can fix that | GoDaddy → auto-renew **on** |
| **A credit card, or a debit card that works like one** | Oracle verifies identity with it. Always Free is not charged, but you cannot sign up without one. Oracle refuses PIN-debit, prepaid and virtual single-use cards, and it may re-check the card for as long as the account exists | |
| **An email address you actually read** | The 18 Aug 2026 entitlement enforcement was announced **by email and nowhere else**, about **13 days** ahead. That mailbox is your only warning if the allowance is cut again | |
| **A Cloudflare login in your browser** | [Part 9](#part-9--the-tunnel) re-issues the tunnel's credentials from your account. **The Windows laptop does not need to be on.** The 2026-09-19 version of this table said it did | |
| **`main` pushed to GitHub** | The box installs by `git clone`, so anything unpushed does not exist on it. On 2026-09-19 `origin/main` was 36 commits behind. On 2026-09-28 it matched | `git rev-list --count origin/main..main` |

**Do Part 0 on the Mac before you open Oracle's site at all.** Discovering Mac-side
work halfway through a migration is how this project lost an afternoon in August.

### The one irreversible decision

**The home region.** Always Free compute exists *only* in your account's home
region, and it cannot be changed afterwards. It is permanent **for you, not for
an email address**: Oracle allows one Free Tier account per person, and trying
to create a second is prohibited. So "sign up again somewhere else" is not an
escape.

**Choose by capacity, not latency.** Cloudflare terminates the phone's TCP and
TLS at its own edge, and `cloudflared` holds the tunnel open. So the origin's
distance costs about **one** round trip per request, not three. That makes
Frankfurt about +81 ms, and every US region is within about 50 ms of any other.
Stay in the US for jurisdiction (the privacy policy's premise), and prefer a
region with **three availability domains** (Chicago, Ashburn or Phoenix),
because Oracle's only remedy for a capacity shortage is to try another AD. The
one public capacity report for Chicago (April 2026) was negative. **The first
run chose `us-ashburn-1` and got A1 capacity in AD-3 on 2026-09-28.** Whether
other ADs were tried first was not recorded.
Everything else in this document is reversible.

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

Then put the **public** half on the clipboard. This is the one you upload:

```bash
pbcopy < ~/.ssh/scenic_oracle.pub
```

Never upload the file *without* `.pub`. That one is the private key, and it
never leaves the Mac.

**If you gave the key a passphrase** (the 2026-09-28 key has one), load it into
the agent once per login. Otherwise every non-interactive `ssh`, including an
agent's, fails *after* the server has accepted the key, with a bare
`Permission denied (publickey)`:

```bash
ssh-add --apple-use-keychain ~/.ssh/scenic_oracle
```

`ssh -v` tells the two failures apart. `Server accepts key` followed by
`Permission denied` means a passphrase problem, not a wrong key.

### 0.3 Know what a good box looks like

**Do not compare the box against a Mac run.** The Mac's venv has the pipeline
dependencies and all nineteen parquets. The box has neither, so its counts are
supposed to differ. The expected result on the box, measured on the first run
with exactly the files [Part 6](#part-6--the-data-382-mb-from-the-mac) copies,
is:

**341 passed, 6 skipped, 0 failed**

The six skips are expected. `tests/test_graph.py` skips as a whole module
("graph build tests need the pipeline deps"), and that one skip stands for its
33 tests. The other five name `scored_chunks.parquet`, which the server never
reads. The 2026-09-19 version said 4 skips and told you to diff against the
Mac. Both were wrong.

---

## Part 1 — Account and home region

1. Go to Oracle Cloud Free Tier and sign up. Use the email from the table above.
2. When asked for **Home Region**, choose a three-AD US region. The live box is
   in **US East (Ashburn)** = `us-ashburn-1`. Chicago and Phoenix are the
   others (see [the one irreversible decision](#the-one-irreversible-decision)).
   **This is the irreversible click.** Do not accept whatever it defaults to.
3. Finish verification. Sign-ups are sometimes rejected outright. If yours is,
   that is an Oracle decision and not something the rest of this document can
   route around. **Do not retry under another email:** one account per person.
4. **Do not upgrade to Pay As You Go on a whim.** People report it getting A1
   capacity where Always Free could not, and Oracle does not charge for Always
   Free resources after an upgrade. But it **cannot be downgraded**, its budgets
   are soft limits evaluated every 24 hours (they alert, they do not cap), and
   it turns a future allowance cut into a bill (about $23.81/mo for this box at
   list price) rather than a termination.

> **I cannot do this part for you, and neither can any agent** — it involves
> entering personal and card details, which is yours to do.

---

## Part 2 — Create the instance

### 2.1 Make the network first, in a second tab

**A new account has no VCN, and the instance form cannot make a usable one.**
If you choose "Create new virtual cloud network" and "Create new public subnet"
inside the instance form, its *Automatically assign public IPv4 address* toggle
stays greyed out, with a warning that you must select a public subnet. The
subnet you just asked for does not exist yet. Without a public IP you cannot
SSH in, and without an internet gateway the box cannot reach Cloudflare,
GitHub or `apt`.

So open a second tab, keep the instance form in the first, and go to
☰ → **Networking → Virtual cloud networks → Actions → Start VCN Wizard →
Create VCN with Internet Connectivity**. Name it `sundaydrive`, keep every
other default, and create it. It builds the VCN, a public and a private subnet,
the internet gateway, the routes, and a default security list that admits SSH
only.

### 2.2 The instance

Console → **Compute → Instances → Create instance**.

| field | value | why |
|---|---|---|
| Image | **Canonical Ubuntu 24.04** | Ships Python 3.12. The lock file needs 3.10–3.13. Once you pick an Ampere shape the console gives you the `aarch64` build, which is what you want |
| Shape | **Change shape → Shape series: Ampere → `VM.Standard.A1.Flex`** | "Browse all shapes" opens on the x86 list, and A1 is not in it. The only *Always Free-eligible* shape on that first list is E2.1.Micro, with **1 GB**, which cannot hold the graph. Everything else on it is paid, and on a trial account a paid shape quietly spends the trial credit |
| OCPUs | **2** | **It defaults to 1.** Expand the shape with ▸ and set 2, which is the whole entitlement. Never more — see [the landmine](#the-landmine-never-exceed-the-entitlement) |
| Memory | **8 GB** | **Deliberately not 12.** See [idle reclaim](#part-12--what-keeps-the-box-alive) |
| Networking | **Select existing VCN `sundaydrive` → Select existing subnet → `public subnet-sundaydrive`** | Now the public-IPv4 toggle works. Turn it **on**. Pick the *public* subnet, not the private one |
| Public IPv4 | **on** | |
| IPv6 | off | |
| SSH key | **Paste public keys**, one box, one line | Check the Review page. On the first run it showed the key pasted twice into one field (`…scenic-oraclessh-ed2551…`) |
| Boot volume | **Specify a custom size → 50 GB**, 10 VPU | Well inside the 200 GB allowance. The default is about 47 GB and would also do |
| Security list | **leave it as the wizard made it** | SSH in, nothing else. The tunnel dials *out*, so nothing needs to reach the box inbound except your SSH |
| Oracle Cloud Agent → **Compute Instance Monitoring** | **leave enabled** (it is by default) | Reported memory utilisation is what keeps the box off the reclaim list |

The Review page should say **VM.Standard.A1.Flex, 2 core OCPU, 8 GB memory**,
subnet `public subnet-sundaydrive`, and **Public IPv4 address: Yes**. Renaming
the instance from the generated `instance-YYYYMMDD-HHMM` is cosmetic. The live
box kept its generated name.

Note the **public IP** when it finishes provisioning.

### If you get `Out of host capacity`

This is the expected failure and it is not your fault — A1 is scarce in exactly
the US regions. Oracle's own documented remedy is to wait and retry.

- Try **each availability domain** in the region.
- Then try **1 OCPU / 8 GB**. Memory decides whether the graph fits, and the
  second core only buys speed. Resize to 2 later.
- Then retry a few times a day, for up to **14 days**.
- At 14 days, stop grinding and pick deliberately. You can keep retrying. You
  can take the paid exit, Contabo Cloud VPS 4 in US-Central at **$6.58/mo**
  (24-month prepaid) or **$7.90/mo** month to month. The 2026-09-19 figure of
  "~€5.50" left out the US region surcharge. Or you can settle for the laptop
  alone for now. An EU region is not the answer. Its latency cost is only about
  +81 ms, but it reopens the privacy policy's US-only premise.

Nothing about the live service changes while you wait. **That only helps if
something is serving.** Check the public hostname before assuming it is.

---

## Part 3 — First login and base packages

```bash
ssh -i ~/.ssh/scenic_oracle ubuntu@<INSTANCE_IP>
```

Check you got the box you asked for. You want `aarch64`, `2`, about 7.7 Gi
total, and `status: done`:

```bash
uname -m; nproc; free -h | head -2; cloud-init status
```

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git rsync
```

`git` and `rsync` are already on the 2026.09.18 image (`/var/log/dpkg.log`
shows only the two Python packages being installed), so what this really adds
is `python3-venv` and `python3-pip`. It also pulls in a compiler toolchain as
recommended packages. That is harmless, but it is not a sign that anything
will be built: [Part 5](#part-5--dependencies-from-the-lock-file) compiles
nothing.

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
have prebuilt wheels and **nothing compiles**. That was confirmed on the first
run: every package came from a wheel under Python 3.12.3.

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

Then, **from the Mac**, in the **main checkout's** root. The parquets are
gitignored and exist only there, not in any worktree:

```bash
rsync -a --partial -e "ssh -i ~/.ssh/scenic_oracle" data/processed-ne/graph_edges.parquet data/processed-ne/graph_nodes.parquet data/processed-ne/turn_restrictions.parquet data/processed-ne/access_ways.parquet data/processed-ne/access_entries.parquet ubuntu@<INSTANCE_IP>:~/Scenic/data/processed-ne/
```

> **The 2026-09-19 command used `--append-verify`, and on this Mac it uploads
> nothing.** macOS now ships `openrsync` as `/usr/bin/rsync`
> (`rsync --version` prints `openrsync: protocol version 29`). It does not
> know that flag, so it prints its usage text and exits. Behind a `| tail` the
> exit status is 0 and it looks like success. `--partial` is the part that
> makes a dropped connection resumable, and `openrsync` supports it.

**Verify the copy by checksum, not by the exit code.** Run this on the Mac, in
the same directory:

```bash
shasum -a 256 data/processed-ne/{graph_edges,graph_nodes,turn_restrictions,access_ways,access_entries}.parquet
```

Then run this on the box. The five hashes must match:

```bash
cd ~/Scenic/data/processed-ne && sha256sum *.parquet
```

| file | size | required? |
|---|---|---|
| `graph_edges.parquet` | 197.1 MB | **yes** |
| `graph_nodes.parquet` | 16.9 MB | **yes** |
| `turn_restrictions.parquet` | 0.2 MB | **yes** — the server refuses to start without it |
| `access_ways.parquet` | 136.0 MB | optional, but destinations snap to the wrong road without it |
| `access_entries.parquet` | 31.9 MB | optional, same |

On the first run all 382 MB crossed in 16 s. If yours drops, re-run the
identical command until the checksums match.

---

## Part 7 — Verify before exposing anything

Run it under `nohup`, so a dropped SSH session does not kill an 8-minute run:

```bash
cd ~/Scenic && .venv/bin/python -m pip install pytest && nohup env SUNDAYDRIVE_DATA=$HOME/Scenic/data/processed-ne .venv/bin/python -m pytest tests/ -q -rs -p no:cacheprovider > ~/pytest.log 2>&1 < /dev/null &
```

```bash
tail -8 ~/pytest.log
```

**Expect 341 passed, 6 skipped, 0 failed**, in about 8 minutes (7m50s on the
first run). Compare against that, **not against a Mac run** (see
[0.3](#03-know-what-a-good-box-looks-like)).

What each outcome means:

- **6 skips, all of them either `test_graph.py` ("need the pipeline deps") or
  `scored_chunks.parquet`.** Correct.
- **Any other skip reason** (say, an access-layer test). A parquet did not
  arrive. Go back to Part 6 and check the hashes.
- **Any failure.** The code and the data disagree. **Stop.** Check the commit
  hashes at both ends before debugging anything else.

Don't run the tests and the service at the same time. Each loads the graph at
about 4 GB, and two of them do not fit in 8 GB.

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
  about 66 s before it answers** (measured on the box, against 49.9 s on an M2).
  The 2026-09-19 guess was 100–125 s, because it assumed an A1 core runs at
  under half an M2's speed. On this workload it runs at about three quarters.
  Do not let a monitor page you during a restart, and do not assume a failure
  because `curl` refuses for the first minute.
- **`journalctl -u sundaydrive-api` shows almost nothing, and that is normal.**
  Python block-buffers stdout when it is not a terminal, so `serve.py`'s two
  startup lines may never appear. Tracebacks go to stderr, which is unbuffered,
  so a crash *does* show up. If you want the startup lines, add
  `Environment=PYTHONUNBUFFERED=1` to the unit. The live box does not have it.

Now wait for it to answer:

```bash
until curl -sf http://127.0.0.1:5057/api/health; do sleep 3; done; echo
```

Expect:

```json
{"nodes":794685,"routing_slots":801719,"status":"ok"}
```

**`794685` is the check.** It is the row count of `graph_nodes.parquet`, and a
different number means the wrong parquets. (`routing_slots` is higher because
the router splits junctions that carry turn restrictions.)

```bash
systemctl status sundaydrive-api --no-pager
```

---

## Part 9 — The tunnel

You are moving an *existing* named tunnel (`scenic`), not making a new one. The
DNS record at Cloudflare already points at it, which is why no DNS change and
no new app build are needed.

**The Windows laptop does not need to be on.** The 2026-09-19 version of this
part copied the credentials file off the laptop. Cloudflare will re-issue that
file to anyone logged into the account, and the first run did exactly that.

Install `cloudflared` on the box (ARM64 build):

```bash
curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o /tmp/cloudflared.deb && sudo dpkg -i /tmp/cloudflared.deb && cloudflared --version
```

### 9.1 Log the box into Cloudflare, once

```bash
cloudflared tunnel login
```

It prints a `https://dash.cloudflare.com/argotunnel?…` URL and waits. Open the
URL on the Mac, pick **jameskouvlis.com**, and click **Authorize**.
`~/.cloudflared/cert.pem` then appears on the box.

**It waits about nine minutes and then gives up.** On the first run the click
landed after the wait had run out. The box logged
`Failed to write the certificate`, Cloudflare offered the certificate as a
browser download instead, and nothing arrived in `~/Downloads`. If that
happens, run the command again and click straight away.

### 9.2 Re-issue the tunnel's credentials

```bash
cloudflared tunnel list
```

Note the ID of the tunnel named `scenic`. It was created 2026-08-12, and it
should be the only tunnel on the account.

```bash
cloudflared tunnel token --cred-file ~/<UUID>.json scenic
```

This writes the same credentials JSON that `tunnel create` wrote on the laptop
in August: `AccountTag`, `TunnelID`, `TunnelSecret`, `Endpoint`. According to
cloudflared's own help text it works for any tunnel created with cloudflared
2022.3.0 or later. **The file is a secret**, because it is the tunnel's
identity. Do not print it, paste it anywhere, or commit it.

```bash
sudo mkdir -p /etc/cloudflared && sudo mv ~/<UUID>.json /etc/cloudflared/ && sudo chown root:root /etc/cloudflared/<UUID>.json && sudo chmod 600 /etc/cloudflared/<UUID>.json
```

**If `tunnel token` fails,** fall back to the laptop's copy at
`C:\Users\<you>\.cloudflared\<UUID>.json`. `scp` it to `/tmp/` on the box and
run the `mv` above from there.

### 9.3 Delete the account certificate

```bash
rm ~/.cloudflared/cert.pem
```

`cert.pem` is not the tunnel's key. It belongs to the *account*, and it can
create, delete and re-route every tunnel on it. Running a tunnel needs only the
credentials file from 9.2, and a box on someone else's hardware should not
hold more than that.

### 9.4 Write the config

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

```bash
sudo cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
```

Expect `OK`.

### 9.5 Do not start it yet

Once it starts, this box is a connector on the live tunnel. Cloudflare sends
each request to the **geographically closest** connector and retries the
others if that one fails. It does not load-balance, which is what the
2026-09-19 text said. So if the API here is not answering yet, the requests
routed to this box get 502s. Go to Part 10.

---

## Part 10 — Cut over

**1. Find out what is attached now.** From anywhere:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.jameskouvlis.com/api/health
```

- **`530`**: no connector is attached at all, so nothing else is serving. That
  is what the first run found, because the laptop was off.
- **`200`**: something else, presumably the laptop, is serving. If you are
  *replacing* it, stop its tunnel first (close the `Sunday Drive Tunnel`
  window, or stop its scheduled task) and wait for `530`. If you want both,
  read [Two connectors on one tunnel](#two-connectors-on-one-tunnel) before
  going further.

**2. Confirm this box's API answers.** On the box:

```bash
curl -s http://127.0.0.1:5057/api/health
```

**3. Start the connector:**

```bash
sudo cloudflared service install && sudo systemctl enable --now cloudflared
```

```bash
sudo journalctl -u cloudflared -n 30 --no-pager | grep "Registered tunnel connection"
```

You should see four lines. The first run registered to `iad08` and `iad09`,
Cloudflare's Ashburn data centres.

**4. Verify the whole path.** From the Mac:

```bash
curl -s https://api.jameskouvlis.com/api/health
```

`{"nodes":794685,…,"status":"ok"}` through the public hostname means you are
done. The iOS app needs **no new build**: `SundayDriveAPIBaseURL` names the
hostname, and the tunnel is the switch.

### Before the laptop is next switched on

> **2026-10-04: the owner expects the laptop never to be switched on again**,
> so Oracle is the only origin and there is no rollback box. The warning below
> still holds if it ever boots.

If the Task Scheduler entries from [`DEPLOY.md`](DEPLOY.md) §7 exist, booting
the laptop starts `cloudflared tunnel run scenic` and attaches it as a
**second, ungated** connector. Cloudflare sends each request to the closest
connector, so Boston-area users would reach the laptop, running whatever code
and data it holds. Nobody has confirmed it ever held the New England build.
**Disable its tunnel task before it boots,** or make it a gated connector as
described next.

### Two connectors on one tunnel

This is the independent review's recommendation. The laptop fails through a
person, the house or Windows; this box fails through capacity, policy or the
account. With both attached, the API is down only when both are down at once.
Two connectors are safe only if **each one attaches only while its own API
answers**. The review's sketch for the Linux side is **untested**:

```sh
#!/bin/sh
# run-connector.sh: hold the tunnel only while this box's API answers.
while :; do
  until curl -sf --max-time 10 http://127.0.0.1:5057/api/health >/dev/null; do sleep 5; done
  cloudflared tunnel run scenic & pid=$!
  while kill -0 "$pid" 2>/dev/null && curl -sf --max-time 20 http://127.0.0.1:5057/api/health >/dev/null; do sleep 15; done
  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
done
```

On this box, it replaces the `ExecStart` of `cloudflared.service`. On the
laptop, the same loop becomes a PowerShell script run by the §7 task. Deploys
then roll: detach one box, restart its API, let the gate reattach it, then do
the other. Two costs come with it. Every deploy goes to both boxes. And the
public monitor only sees whichever replica answered, so each box needs its own
local check. `/api/health` should also report a commit and a data fingerprint
(`server/app.py`, proposed in the review, not made), because users near each
box see a different one.

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

**Check before adding one.** The rule matches the hostname, not the origin, so
a rule made during the laptop setup still applies to this box.

---

## Part 12 — What keeps the box alive

### Idle reclamation

Oracle's text says an idle Always Free instance "may" be reclaimed. It counts
as idle if, over 7 days, **all three** of these hold: CPU 95th percentile under
20%, network under 20%, **and** memory under 20% (the memory test applies to A1
only). A single-user routing API is clearly idle on the first two, so **memory
is the only thing keeping the box alive.**

| instance memory | measured on the box, 2026-09-29 | verdict |
|---|---|---|
| 12 GB (the full entitlement) | would be about 35% | safe |
| **8 GB (what you built)** | **4.2 GiB of 7.7 GiB used, 55%** (`free -h`, after routing) | **safe, with margin** |

This is why you provisioned 8 GB rather than the 12 you are entitled to: **more
RAM lowers the percentage and moves the box towards reclamation.** Keep the
Oracle Cloud Agent's *Compute Instance Monitoring* plugin enabled. The metric
needs it, and an instance that reports no memory metric is not one that
reports high memory.

This couples hosting to the code. **A future optimisation that takes the
server's memory under about 1.6 GB re-arms reclaim, and nothing will warn
you.** And reclaim is only one of four ways to lose the box. The others are
the next two subsections and termination without a stated reason.

**Do not fake load to defeat this.** Sunday Drive genuinely holds the working set; a
cron job burning CPU to look busy is both unnecessary and the sort of thing that
reads badly in an account review.

### The account can go idle too

Oracle's Free Tier FAQ: accounts "left idle for 30 days or more may be deemed
abandoned and become eligible for suspension or termination". It does not say
what makes an *account* idle, as opposed to an instance, and a box nobody logs
into could plausibly qualify. **Sign into the console at least once a month.**
Always-Free-only accounts get no Oracle Support, so there is no one to ask
afterwards.

### The mailbox

The June 2026 halving had **no announcement**. The August enforcement came
**by email only**, about **13 days** before it began, not the nine weeks the
2026-09-19 text implied. Read that mailbox. It is the entire early-warning
system.

### Monitoring

A free UptimeRobot monitor on `https://api.jameskouvlis.com/api/health`, 5-minute
interval, **keyword `794685`** — asserting the keyword rather than just a 200
catches a box serving the *wrong graph*, which a liveness check cannot see.
Alert to an address you read.

---

## Part 13 — Measure it, and write the numbers down

```bash
systemctl show -p MemoryPeak --value sundaydrive-api | awk '{printf "peak %.2f GB\n", $1/1073741824}'
```

```bash
ps -o rss= -p $(systemctl show -p MainPID --value sundaydrive-api) | awk '{printf "RSS %.2f GB\n", $1/1048576}'
```

```bash
curl -s -o /dev/null -w "%{time_total}s\n" "https://api.jameskouvlis.com/api/route?from=42.3601,-71.0589&to=44.3106,-69.7795&pref=0.5"
```

That is a GET, which the server still accepts. The app sends the same
parameters as a POST form body (see
[Updating the code](#updating-the-code-server-before-phone)), and this is the
check that the box speaks it:

```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" -d "from=42.3601,-71.0589&to=44.3106,-69.7795&pref=0.5" https://api.jameskouvlis.com/api/route
```

| measure | **measured on the box, 2026-09-29** | measured on the Mac, 2026-09-19 | guessed for A1 on 2026-09-19 |
|---|---|---|---|
| peak memory | **4.06 GB** (cgroup `MemoryPeak`); RSS 3.49 GB cold, 3.65 GB after routing | 4.39 GB peak RSS | 4.2–5.0 GB |
| graph load, start to first answer | **66 s** | 49.9 s | 100–125 s |
| Boston → Augusta, on the box | **0.65 s** warm, 0.91 s first request | ~470 ms warm | ~1.0–1.3 s |
| the same, through the public hostname from Boston | **0.79 s** | — | — |
| `/api/loop`, default 40 km, first call | **3.9 s** | never timed | — |
| test suite (341 tests) | **7m50s** | 6m54s (374 tests) | — |

The guesses assumed an A1 core runs at under half an M2's speed. On this
workload it runs at about three quarters. The tunnel adds about 0.14 s per
request from Boston to Ashburn. Two results deserve investigation rather than a
shrug: **above 5.5 GB** (something is holding more than the graph) and **below
2.4 GB** (the idle-reclaim maths needs redoing, because you are approaching the
20% floor).

---

## Updating the box

Nothing on the box pulls code or data by itself, and the server reads the
graph once at startup. So every change goes through one script, run on the
Mac from any checkout:

```bash
server/deploy-oracle.sh --dry-run
```

```bash
server/deploy-oracle.sh
```

The dry run says what would change and touches nothing. The real run does the
following, and stops at the first step that fails:

1. Checks with `git ls-remote` that local `main` is on GitHub (Part 0.1).
2. Hashes the five parquets at both ends. It copies only the ones that differ,
   from the main checkout, then checks the hashes again (Part 6).
3. Fast-forwards the box to `main`. If the lock file changed, it reinstalls
   the dependencies.
4. Restarts `sundaydrive-api` once, **only if** server code or data changed.
   A docs-only change is pulled and nothing restarts. `--restart` forces one.
5. Waits up to 180 s for `/api/health`. Then it checks that the node count
   equals `graph_nodes.parquet`'s row count, reports memory against the
   reclaim floor, and checks the public hostname.

Code and data both arrive before the single restart. That is what prevents
the `KeyError: 'c_green'` crash. A restart still means about 66 s of `502`
while the graph loads, because only one box is serving. If a rebuild changes
the node count, the script tells you to update the UptimeRobot keyword.

The ssh key must be in the agent (Part 0.2). Once there are two gated
connectors (Part 10), this script covers one box, and the rolling deploy
described there is still unwritten.

---

## Updating the code: server before phone

**Added 2026-09-29 with the move of coordinates out of the URL
(`docs/coordinates-out-of-the-url-brief.md`).** From that commit on, the app
sends `/api/route` and `/api/loop` as `POST` with the parameters in a form
body. The server accepts both `POST` and `GET`, but a box running older code
answers only `GET`, and a `POST` to it gets a `405` that the app shows as "the
routing service isn't reachable". So the order is fixed:

1. **The box first.** On the Mac, `ssh-add --apple-use-keychain
   ~/.ssh/scenic_oracle` (the key has a passphrase, and only the owner can
   type it). Then run `server/deploy-oracle.sh`, as in
   [Updating the box](#updating-the-box). It pulls, restarts and waits for
   the graph. Then run the `POST` check in
   [Part 13](#part-13--measure-it-and-write-the-numbers-down). It must print
   `200`. A `405` means the box is still on the old code.
2. **Then the phone.** Only after step 1 answers `200` does a build containing
   the change go onto a phone or TestFlight. A build installed before the change
   keeps sending `GET` and keeps working throughout, so the box can go first
   with nothing to coordinate.

Getting the order wrong breaks every route and loop request from the new build
until the box is updated. It does not break the old build.

---

## Rollback

At any point, including after cutover:

1. Stop the tunnel on the box: `sudo systemctl stop cloudflared`.
2. Start `cloudflared` on the laptop again.

No DNS change, no App Review, no new build. **But step 2 only works if the
laptop is on, on the same commit as `main`, and holding the New England
parquets.** None of that was true on 2026-09-28: it was off, and nobody has
confirmed it ever held the NE build. Until it is true, rollback means fixing
this box, not leaving it. If you want the laptop to stay a real rollback, run
it as a gated second connector (Part 10).

---

## Troubleshooting

| symptom | almost certainly | fix |
|---|---|---|
| `HTTP 530` from the public hostname | **No connector attached at all.** `cloudflared` is down on every origin | `systemctl status cloudflared`, then `sudo journalctl -u cloudflared -n 50`. (The 2026-09-19 row blamed the API here. That was wrong) |
| `HTTP 502` | `cloudflared` is connected, but the API is not answering on `:5057`: it is down, or still loading (about 66 s after a restart) | Wait a minute, then `systemctl status sundaydrive-api`. An `ImportError` at startup looks exactly like this |
| `KeyError: 'c_green'` or similar at startup | **Old code, new parquets** | Compare `git log --oneline -1` at both ends |
| `/api/health` reports a node count that is not 794685 | Wrong or partial parquets | Re-run Part 6, then compare the hashes |
| A test skipped for a reason other than `test_graph.py` or `scored_chunks.parquet` | A parquet did not arrive | Re-run Part 6, then compare the hashes |
| `rsync` prints a usage summary and copies nothing | macOS's `openrsync` rejects `--append-verify` | Use Part 6's command as written now |
| `ssh -v` says `Server accepts key`, then `Permission denied (publickey)` | The key has a passphrase and no agent holds it | `ssh-add` (Part 0.2) |
| The instance form's public-IPv4 toggle is greyed out | The "new public subnet" it offered does not exist yet | Part 2.1: make the VCN with the wizard first |
| A1 missing from "Browse all shapes" | That list opens on the x86 series | Shape series → **Ampere** (Part 2.2) |
| `cloudflared tunnel login` ends in `Failed to write the certificate` | Its roughly nine-minute wait ran out before the click | Run it again and click straight away |
| `curl localhost:5057` refused, but the service is `active` | The graph is still loading | It takes about 66 s. `active` ≠ answering |
| `journalctl -u sundaydrive-api` shows only `Started…` | Python buffers stdout under systemd | Normal (Part 8). Tracebacks still appear |
| Intermittent answers, some stale | **A second, ungated connector**, most likely the laptop booting with its §7 task | Part 10, "Before the laptop is next switched on" |
| `Out of host capacity` | A1 scarcity, not your account | Other ADs, then 1 OCPU, then Part 2's 14-day rule |
| Route requests time out under load | You are at the ~5 req/s ceiling | That is the documented ceiling, not a bug. Part 11 |

### The landmine: never exceed the entitlement

The Always Free A1 allowance is **2 OCPU and 12 GB total, per tenancy** — and
2 OCPU running continuously is 1,488 hours in a 31-day month against an
allowance of 1,500. It fits with about six hours of slack, which means:

- **You cannot run two 2-OCPU instances side by side**, not even briefly for a
  parallel-run window. If you want an overlap, make each instance 1 OCPU.
- **Never resize above 2 OCPU.** On 18 Aug 2026 Oracle terminated instances
  that exceeded the (silently halved) entitlement, with an email as the only
  warning. Oracle's Free Tier overview says A1 instances over the limit are
  "disabled and then deleted after 30 days". (The 2026-09-19 text quoted the
  FAQ's "can't be restored", but that sentence is about paid resources when a
  trial ends.) At least one user reports the boot volume went with the
  instance, so assume deletion.

Which is the real reason to keep this box reproducible from the repo: everything
on it is a `git clone`, eleven pinned wheels, 382 MB of parquet you can re-copy,
and the two unit files above.

---

## What this does not cover

- **Rebuilding the graph.** The pipeline never runs on this box — you build
  parquets on the Mac and ship them with `deploy-oracle.sh` ([Updating the box](#updating-the-box)). See the top-level README.
- **A second worker.** The box peaked at 4.06 GB with one process, so two need
  about 8 GB and **do not fit in 8 GB** alongside the OS. That corrects the old
  "around two workers" figure, which came from a 3.53 GB measurement that
  [`docs/hosting-status-2026-09.md`](../docs/hosting-status-2026-09.md) shows was
  an under-read. Routing does not parallelise anyway.
- **Whether to keep the laptop.** `docs/release-plan.md` §7 rated keeping the
  laptop up and migrating as *both* acceptable for launch. The independent
  review's answer is both at once, gated (Part 10). This document covers the
  Oracle half.

---

## What the first run changed

Executing the 2026-09-19 version on 2026-09-28/29 found five things it had
wrong:

1. **The laptop was never needed.** `cloudflared tunnel token --cred-file`
   re-issues the credentials from the account (Part 9). The old version made a
   switched-on laptop a prerequisite, and it was off.
2. **The test expectation.** It is **341 passed, 6 skipped, 0 failed**, not
   "4 skips", and comparing against a Mac run cannot work, because the Mac has
   the pipeline deps and every parquet (Part 0.3).
3. **The upload command did nothing.** macOS's `openrsync` rejects
   `--append-verify` (Part 6). Now verified by checksum.
4. **The console does not work the way the table implied.** The instance form
   cannot make a subnet it can put a public IP on. A1 is not on the shape list
   it opens with. OCPUs default to 1 (Part 2).
5. **The A1 figures were guesses, and pessimistic ones.** Load 66 s, not
   100–125 s. A route 0.65 s, not 1.0–1.3 s (Part 13).

It also folds in what the 2026-09-28 independent review found by reading
Oracle's and Cloudflare's own pages:

- the domain expiry
- the accepted card types
- one account per person
- choosing the region by capacity rather than latency
- PAYG being one-way
- the ~13-day warning
- the account-level idle rule
- the US Contabo price
- 530 versus 502
- "closest replica" rather than load-balancing
- the correct citation for over-limit deletion
