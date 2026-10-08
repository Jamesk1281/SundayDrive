"""Load test for the deployed API: how much traffic the Oracle box can take.

    python -u tools/load_test/probe.py http://127.0.0.1:15957 PHASE [...] \
        --out tools/load_test/results/run.jsonl

BASE is normally an SSH tunnel to the box's loopback port (ssh -N -L
15957:127.0.0.1:5057 ubuntu@box), which measures the server and not
Cloudflare's 60/min per-IP rule, and puts no client CPU on the box's two cores.
Standard library only, so it runs from any Python 3.

Phases:
  idle     serial latency of each request type, nothing else running
  sweep    closed loop: C clients posting plan requests back to back
  loops    loop builders beside route clients (the LOOP_LOCK queue)
  open     Poisson arrivals at fixed rates, with the request mix below
  public   a few requests through the public hostname, for the tunnel's cost

Trips are the 194 routable pairs of tools/e2e_od_pairs.json (urban, suburban,
rural, cross-state, coastal, parking lots), so lengths look like real trips
rather than random node pairs across New England. Every request is cold: the
server caches no routes, and each loop asks a length nobody asked before.

The client waits 120 s, never 20 s like the app. Waitress keeps computing a
request whose client gave up (docs/loop-lock-contention.md, item 7), so an
impatient probe would leave a queue behind and poison the next phase. Anything
over 20 s is counted as a failure the app would have shown.

A file named STOP next to this script ends the run between requests. The
memory watcher creates it when the box's MemAvailable falls under 700 MB.
"""
import argparse
import json
import os
import random
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STOP = os.path.join(HERE, "STOP")
# Cloudflare answers 403 to urllib's own "Python-urllib/3.x" (2026-10-08); the
# app's CFNetwork agent and curl's pass.
HEADERS = {"User-Agent": "SundayDrive-loadtest/1"}
APP_TIMEOUT = 20.0              # RouteService.timeoutIntervalForResource
CLIENT_TIMEOUT = 120.0

# Two pairs answer 400 on the box (2026-10-08), so they would only time a refusal.
UNROUTABLE = {"suburban-005", "island-001"}
PAIRS = [p for p in json.load(open(os.path.join(HERE, "..", "e2e_od_pairs.json")))["pairs"]
         if p["expect"] == "route" and "destination" in p and p["id"] not in UNROUTABLE]
LOOP_STARTS = [p["origin"] for p in json.load(open(os.path.join(HERE, "..", "e2e_od_pairs.json")))["pairs"]
               if p["category"] in ("loop", "rural", "suburban", "coastal")]
# What a loop drive sends when the driver misses a turn (the K-1 probe's row).
REJOIN = {"from": "42.2900,-71.2200", "to": "42.2810,-71.2370",
          "via": "42.2457,-71.2828", "pref": "1.0"}


def ll(p):
    return f"{p[0]:.6f},{p[1]:.6f}"


def post(base, path, params, timeout=CLIENT_TIMEOUT):
    data = urllib.parse.urlencode(params).encode()
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(base + path, data=data, headers=HEADERS),
                                    timeout=timeout) as r:
            r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        e.read()
        status = e.code
    except Exception as e:  # noqa: BLE001 — timeouts, resets, refused
        status = type(e).__name__
    return time.perf_counter() - t0, status


def get(base, path, timeout=CLIENT_TIMEOUT):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(base + path, headers=HEADERS),
                                    timeout=timeout) as r:
            r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:  # noqa: BLE001
        status = type(e).__name__
    return time.perf_counter() - t0, status


class Requests:
    """Request makers. Each call returns (kind, path, params)."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.loop_n = 0

    def plan(self):
        # What the app sends when you tap Go: default pref, options asked for.
        p = self.rng.choice(PAIRS)
        return "plan", "/api/route", {"from": ll(p["origin"]), "to": ll(p["destination"]),
                                      "pref": "0.5", "options": "1"}

    def reroute(self):
        # Mid-drive off-route reroute: the slider's pref, no options, a heading.
        p = self.rng.choice(PAIRS)
        return "reroute", "/api/route", {"from": ll(p["origin"]), "to": ll(p["destination"]),
                                         "pref": f"{self.rng.choice([0.0, 0.5, 1.0])}",
                                         "heading": str(self.rng.randrange(360))}

    def loop(self):
        # A cold loop: a length (to 0.1 km) nobody has asked for from this start.
        self.loop_n += 1
        start = self.rng.choice(LOOP_STARTS)
        km = round(self.rng.uniform(25, 80), 1)
        return "loop", "/api/loop", {"from": ll(start), "km": f"{km}"}

    def rejoin(self):
        return "rejoin", "/api/route", dict(REJOIN)


def summarise(samples):
    """samples: list of (kind, seconds, status). Per kind: n, ok, p50/p95/max."""
    out = {}
    for kind in sorted({k for k, _, _ in samples}):
        ts = sorted(t for k, t, s in samples if k == kind and s == 200)
        bad = [s for k, _, s in samples if k == kind and s != 200]
        row = {"n": sum(1 for k, *_ in samples if k == kind), "ok": len(ts),
               "errors": {str(s): bad.count(s) for s in set(bad)}}
        if ts:
            row.update(p50=round(statistics.median(ts), 2),
                       p95=round(ts[min(len(ts) - 1, int(0.95 * len(ts)))], 2),
                       max=round(ts[-1], 2),
                       over_20s=sum(t > APP_TIMEOUT for t in ts))
        out[kind] = row
    return out


def stopped():
    return os.path.exists(STOP)


def wait_drained(base, label):
    """Health answers in under 0.5 s once nothing is queued ahead of it."""
    for _ in range(120):
        dt, st = get(base, "/api/health", timeout=60)
        if st == 200 and dt < 0.5:
            return
        print(f"[{label}] draining: health {st} in {dt:.1f}s", flush=True)
        time.sleep(2)


def emit(out, record):
    record["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = json.dumps(record)
    print(line, flush=True)
    if out:
        with open(out, "a") as f:
            f.write(line + "\n")


# ---------------------------------------------------------------- phases

def phase_idle(base, out, n):
    reqs = Requests(1)
    samples = []
    for _ in range(5):
        dt, st = get(base, "/api/health")
        samples.append(("health", dt, st))
    makers = [reqs.plan, reqs.reroute] * n + [reqs.loop] * max(4, n // 3) + [reqs.rejoin] * 4
    reqs.rng.shuffle(makers)
    for make in makers:
        if stopped():
            break
        kind, path, params = make()
        dt, st = post(base, path, params)
        samples.append((kind, dt, st))
    # A loop asked twice is a cache hit the second time.
    kind, path, params = reqs.loop()
    post(base, path, params)
    for _ in range(3):
        dt, st = post(base, path, params)
        samples.append(("loop_cached", dt, st))
    emit(out, {"phase": "idle", "summary": summarise(samples)})


def closed_loop(base, makers, clients, duration, seed):
    stop = threading.Event()
    samples, lock = [], threading.Lock()
    t_start = time.perf_counter()

    def worker(i):
        reqs = Requests(seed * 100 + i)
        make = getattr(reqs, makers[i % len(makers)])
        while not stop.is_set() and not stopped():
            kind, path, params = make()
            dt, st = post(base, path, params)
            with lock:
                samples.append((kind, dt, st))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(clients)]
    for t in threads:
        t.start()
    stop.wait(duration)
    stop.set()
    for t in threads:
        t.join()
    return samples, time.perf_counter() - t_start


def phase_sweep(base, out, levels, duration):
    for c in levels:
        if stopped():
            break
        wait_drained(base, f"sweep c={c}")
        samples, wall = closed_loop(base, ["plan"], c, duration, seed=c)
        ok = sum(1 for _, _, s in samples if s == 200)
        emit(out, {"phase": "sweep", "clients": c, "wall_s": round(wall, 1),
                   "throughput_rps": round(ok / wall, 2),
                   "summary": summarise(samples)})


def phase_loops(base, out, loop_clients, route_clients, duration):
    for lc in loop_clients:
        if stopped():
            break
        wait_drained(base, f"loops lc={lc}")
        makers = ["loop"] * lc + ["plan", "reroute", "rejoin"][:route_clients]
        samples, wall = closed_loop(base, makers, lc + route_clients, duration, seed=50 + lc)
        emit(out, {"phase": "loops", "loop_clients": lc, "route_clients": route_clients,
                   "wall_s": round(wall, 1), "summary": summarise(samples)})


# The mix an open-loop arrival draws from. Planning dominates: a person plans
# once or a few times (the slider re-plans on release) and reroutes rarely.
MIX = [("plan", 0.60), ("reroute", 0.20), ("loop", 0.15), ("rejoin", 0.05)]


def phase_open(base, out, rates, duration, max_in_flight):
    for rate in rates:
        if stopped():
            break
        wait_drained(base, f"open {rate}/s")
        reqs = Requests(int(rate * 1000))
        samples, lock = [], threading.Lock()
        in_flight = [0]
        peak = [0]
        threads = []
        aborted = False

        def fire(kind, path, params):
            dt, st = post(base, path, params)
            with lock:
                samples.append((kind, dt, st))
                in_flight[0] -= 1

        t_end = time.perf_counter() + duration
        nxt = time.perf_counter()
        while time.perf_counter() < t_end and not stopped():
            nxt += reqs.rng.expovariate(rate)
            time.sleep(max(0.0, nxt - time.perf_counter()))
            with lock:
                if in_flight[0] >= max_in_flight:
                    aborted = True
                    break
                in_flight[0] += 1
                peak[0] = max(peak[0], in_flight[0])
            r = reqs.rng.random()
            for name, w in MIX:
                r -= w
                if r <= 0:
                    break
            kind, path, params = getattr(reqs, name)()
            t = threading.Thread(target=fire, args=(kind, path, params))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        emit(out, {"phase": "open", "rate_rps": rate, "duration_s": duration,
                   "sent": len(threads), "peak_in_flight": peak[0],
                   "aborted_at_in_flight_cap": aborted,
                   "summary": summarise(samples)})
        if aborted:
            break


def phase_public(base, out, public, n):
    """Same requests on both paths, interleaved, to price the tunnel.

    Paced to two public requests per 2.5 s or slower: the Cloudflare rule
    blocks an IP for ~10 s after ~10 requests in 10 s.
    """
    reqs = Requests(7)
    samples = []
    for _ in range(n):
        dt, st = get(public, "/api/health")
        samples.append(("public_health", dt, st))
        dt, st = get(base, "/api/health")
        samples.append(("box_health", dt, st))
        kind, path, params = reqs.plan()
        dt, st = post(public, path, params)
        samples.append(("public_plan", dt, st))
        dt, st = post(base, path, params)
        samples.append(("box_plan", dt, st))
        time.sleep(2.5)
    emit(out, {"phase": "public", "summary": summarise(samples)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("phases", nargs="+")
    ap.add_argument("--out")
    ap.add_argument("--idle-n", type=int, default=20)
    ap.add_argument("--sweep", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    ap.add_argument("--duration", type=float, default=60)
    ap.add_argument("--loop-clients", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--route-clients", type=int, default=3)
    ap.add_argument("--rates", type=float, nargs="+", default=[0.5, 1, 2, 3])
    ap.add_argument("--max-in-flight", type=int, default=40)
    ap.add_argument("--public", default="https://api.jameskouvlis.com")
    ap.add_argument("--public-n", type=int, default=10)
    a = ap.parse_args()
    for ph in a.phases:
        if stopped():
            print("STOP file present; ending", flush=True)
            break
        if ph == "idle":
            phase_idle(a.base, a.out, a.idle_n)
        elif ph == "sweep":
            phase_sweep(a.base, a.out, a.sweep, a.duration)
        elif ph == "loops":
            phase_loops(a.base, a.out, a.loop_clients, a.route_clients, a.duration)
        elif ph == "open":
            phase_open(a.base, a.out, a.rates, a.duration, a.max_in_flight)
        elif ph == "public":
            phase_public(a.base, a.out, a.public, a.public_n)
        else:
            raise SystemExit(f"unknown phase {ph}")


if __name__ == "__main__":
    main()
