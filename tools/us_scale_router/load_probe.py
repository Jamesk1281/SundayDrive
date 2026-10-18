"""Memory under concurrent load: a real server, four clients, a mixed workload.

    python load_probe.py <pack> --port 5091 --seconds 120 --replicates 3 --out probe.json

Starts server/serve.py on the pack (its own process, on a port nothing else
uses), waits for /api/health, then runs CLIENTS threads posting a mix of plans,
plans with options, reroutes with a heading and loops of every length, drawn
across the whole map. It samples the server's RSS and macOS phys_footprint
(the memory the kernel cannot simply drop, which leaves out clean pages
mapped from the pack) every half second, and stops the server by its own PID.

Replicates start a fresh server each, because peak RSS varies run to run and
the Mac pages a big process out between them (docs/load-test-oracle.md's
probe traps). Every response's status and time is kept; nothing is piped
through `tail`.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CLIENTS = 4


def sample(pid):
    rss = int(os.popen(f"ps -o rss= -p {pid}").read() or 0) / 1e6
    fp = float("nan")
    for line in os.popen(f"footprint -p {pid} 2>/dev/null").read().splitlines():
        if "phys_footprint:" in line:
            v, unit = line.split("phys_footprint:")[1].split()[:2]
            fp = float(v) * {"KB": 1e-6, "MB": 1e-3, "GB": 1.0}[unit]
    return rss, fp


def post(port, path, params, timeout=120):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data)
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception:
        status = -1
    return status, time.perf_counter() - t


def workload(lat, lon, rng):
    """One request: a plan, a plan with options, a reroute or a loop, between
    junctions up to 500 km apart."""
    i = int(rng.integers(len(lat)))
    kind = rng.choice(["route", "options", "reroute", "loop"], p=[0.4, 0.2, 0.25, 0.15])
    if kind == "loop":
        km = float(rng.choice([20, 40, 80, 150, 300, 400]))
        return kind, "/api/loop", {"from": f"{lat[i]:.6f},{lon[i]:.6f}", "km": f"{km:g}"}
    while True:
        j = int(rng.integers(len(lat)))
        d = 111.0 * np.hypot(lat[j] - lat[i], (lon[j] - lon[i]) * np.cos(np.radians(lat[i])))
        if 5 < d < 480:
            break
    p = {"from": f"{lat[i]:.6f},{lon[i]:.6f}", "to": f"{lat[j]:.6f},{lon[j]:.6f}",
         "pref": "0.5"}
    if kind == "options":
        p["options"] = "1"
    if kind == "reroute":
        p["heading"] = f"{rng.uniform(0, 360):.1f}"
    return kind, "/api/route", p


def run(pack, port, seconds, seed):
    env = dict(os.environ, SUNDAYDRIVE_PACK=str(pack), PORT=str(port),
               SUNDAYDRIVE_HOST="127.0.0.1", SUNDAYDRIVE_ROUTE_OPTIONS="1",
               SUNDAYDRIVE_DATA=os.environ.get("SUNDAYDRIVE_DATA", "/nonexistent"))
    log = open(Path(pack).parent / f"probe-server-{port}.log", "w")
    t0 = time.perf_counter()
    proc = subprocess.Popen([sys.executable, str(ROOT / "server" / "serve.py")],
                            env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        while True:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2)
                break
            except Exception:
                if proc.poll() is not None:
                    raise RuntimeError("server exited; see its log")
                time.sleep(0.5)
        ready_s = time.perf_counter() - t0
        rss0, fp0 = sample(proc.pid)
        lat = np.load(Path(pack) / "node_lat.npy", mmap_mode="r")
        lon = np.load(Path(pack) / "node_lon.npy", mmap_mode="r")
        done, rows, peaks = threading.Event(), [], []

        def client(k):
            rng = np.random.default_rng(seed * 100 + k)
            while not done.is_set():
                kind, path, params = workload(lat, lon, rng)
                status, dt = post(port, path, params)
                rows.append((kind, status, dt))

        def sampler():
            while not done.is_set():
                peaks.append(sample(proc.pid))
                time.sleep(0.5)

        threads = [threading.Thread(target=client, args=(k,)) for k in range(CLIENTS)]
        threads.append(threading.Thread(target=sampler))
        for t in threads:
            t.start()
        time.sleep(seconds)
        done.set()
        for t in threads:
            t.join()
        rss, fp = np.array([p[0] for p in peaks]), np.array([p[1] for p in peaks])
        return {"ready_s": ready_s, "rss_after_load_gb": rss0,
                "footprint_after_load_gb": fp0, "peak_rss_gb": float(rss.max()),
                "peak_footprint_gb": float(np.nanmax(fp)),
                "requests": len(rows),
                "by_kind": {k: {"n": sum(1 for r in rows if r[0] == k),
                                "ok": sum(1 for r in rows if r[0] == k and r[1] == 200),
                                "p50_s": float(np.median([r[2] for r in rows if r[0] == k]
                                                         or [np.nan])),
                                "p90_s": float(np.percentile([r[2] for r in rows if r[0] == k]
                                                             or [np.nan], 90))}
                            for k in ("route", "options", "reroute", "loop")},
                "statuses": {str(s): sum(1 for r in rows if r[1] == s)
                             for s in sorted({r[1] for r in rows})}}
    finally:
        # Our own server, by PID: never a broad pkill (other sessions run theirs).
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pack")
    p.add_argument("--port", type=int, default=5091)
    p.add_argument("--seconds", type=int, default=120)
    p.add_argument("--replicates", type=int, default=3)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    results = []
    for rep in range(args.replicates):
        res = run(args.pack, args.port, args.seconds, rep)
        results.append(res)
        print(json.dumps(res), flush=True)
        Path(args.out).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
