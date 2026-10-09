"""Old vs new LoopPlanner, node for node, over a stratified sample of starts.

argv: <old looper.py> <data dir> [out.csv]
Get the old module with `git show 722132b:pipeline/looper.py > looper_old.py`.
Run from the checkout whose pipeline/ holds the new looper.

For every start x target x (default sector + two compass sectors) it compares
`plan` output (turnaround, node path, km, minutes, score, repeated and
beautiful km, sector), `sectors()` counts, the candidate set and each
candidate's out/back cost, km, scenic-km and tree path, and `nearest_length`
wherever the old planner returned no loop. Targets run in the order an app
user might take them (40 first, then shorter and longer), so cached discs are
reused as well as built. Prints one line per (start, target) and a summary.
"""
import csv, importlib.util, sys, time
from datetime import date
import numpy as np

OLD_PATH, DATA = sys.argv[1], sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else None
sys.path.insert(0, "pipeline")
import router as RT, looper as NEW                                  # noqa: E402
spec = importlib.util.spec_from_file_location("looper_old", OLD_PATH)
OLD = importlib.util.module_from_spec(spec); spec.loader.exec_module(OLD)

ON = date(2026, 10, 8)
R = RT.Router(DATA)

STARTS = {
    # towns
    "Needham": (42.2809, -71.2378), "Boston": (42.3601, -71.0589),
    "Worcester": (42.2626, -71.8023), "Burlington VT": (44.4759, -73.2121),
    "Portland ME": (43.6591, -70.2568), "Hartford": (41.7658, -72.6734),
    "Providence": (41.8240, -71.4128), "Concord NH": (43.2081, -71.5376),
    "Springfield": (42.1015, -72.5898),
    # rural
    "Petersham": (42.4890, -72.1890), "Stowe": (44.4654, -72.6874),
    "Woodstock VT": (43.6235, -72.5185), "Litchfield CT": (41.7473, -73.1887),
    "Peterborough": (42.8706, -71.9518), "Jackson NH": (44.1464, -71.1856),
    "Island Pond": (44.8137, -71.8801), "Pittsburg NH": (45.0512, -71.3915),
    # coast
    "Gloucester": (42.6159, -70.6620), "Chatham": (41.6821, -69.9598),
    "Camden": (44.2098, -69.0648), "Westerly": (41.3776, -71.8273),
    # Maine woods
    "Greenville ME": (45.4595, -69.5906), "Rangeley": (44.9659, -70.6428),
    "Millinocket": (45.6573, -68.7098), "Jackman": (45.6278, -70.2556),
    "Fort Kent": (47.2587, -68.5895),
    # islands and peninsulas
    "Bar Harbor": (44.3876, -68.2039), "Edgartown": (41.3890, -70.5134),
    "Nantucket": (41.2835, -70.0995), "Deer Isle": (44.2237, -68.6775),
    "Grand Isle VT": (44.7187, -73.2943), "Newport RI": (41.4901, -71.3128),
    "Provincetown": (42.0584, -70.1786), "Nahant": (42.4265, -70.9195),
    "Cape Elizabeth": (43.5637, -70.2000),
}
TARGETS = (40.0, 10.0, 80.0, 25.0, 150.0, 300.0)


def picked_nodes():
    """Two dead ends and two private-road junctions, chosen by a fixed seed."""
    rng = np.random.default_rng(20261008)
    out_deg = np.bincount(R.u_tail, minlength=R.n)
    in_deg = np.bincount(R.u_head, minlength=R.n)
    dead = np.flatnonzero((out_deg == 1) & (in_deg == 1)
                          & (R.real_node == np.arange(R.n)))
    private = np.flatnonzero(R.private_inside)
    out = {}
    for i, v in enumerate(rng.choice(dead, 2, replace=False)):
        out[f"dead end {i + 1}"] = int(v)
    for i, v in enumerate(rng.choice(private, 2, replace=False)):
        out[f"private road {i + 1}"] = int(v)
    return out


def sig(loop):
    if loop is None:
        return None
    r = loop.route
    return (loop.turnaround_idx, tuple(r.nodes), tuple(r.edges.index), r.km,
            r.minutes, r.mean_score, loop.repeated_km, loop.beautiful_km,
            loop.sector, loop.target_km)


def field_diff(fo, fn, idx):
    """Differences between old and new fields on the candidate nodes."""
    bad = 0
    for a, b in ((fo.out, fn.out), (fo.back, fn.back)):
        for name in ("cost", "km", "scen", "pred"):
            bad += int((getattr(a, name)[idx] != getattr(b, name)[idx]).sum())
    return bad


starts = {name: R.snap(*ll)[0] for name, ll in STARTS.items()}
starts.update(picked_nodes())
old, new = OLD.LoopPlanner(R), NEW.LoopPlanner(R)
for p in (old, new):
    p._cost(1.0, (), 1.0, ON)
rows, diffs = [], 0
t_old = t_new = 0.0
for name, s in starts.items():
    for km in TARGETS:
        t = time.perf_counter()
        so = old.sectors(s, km, on=ON)
        fo = old._fields(s, 1.0, {}, 1.0, ON)
        co = old.candidates(fo, km)
        t_old += time.perf_counter() - t
        t = time.perf_counter()
        sn = new.sectors(s, km, on=ON)
        fn = new._fields(s, 1.0, {}, 1.0, ON, target_km=km)
        cn = new.candidates(fn, km)
        t_new += time.perf_counter() - t
        same_cands = np.array_equal(co, cn)
        fd = field_diff(fo, fn, co) if same_cands else -1
        offered = sorted(so, key=lambda k: (-so[k], k))
        compass = ([offered[0], offered[-1]] if len(offered) >= 2
                   else (offered + ["N", "S"])[:2])
        if len(compass) == 2 and compass[0] == compass[1]:
            compass[1] = "S" if compass[0] != "S" else "N"
        plans = []
        for sector in [None] + compass:
            t = time.perf_counter(); lo = old.plan(s, km, sector=sector, on=ON)
            t_old += time.perf_counter() - t
            t = time.perf_counter(); ln = new.plan(s, km, sector=sector, on=ON)
            t_new += time.perf_counter() - t
            nearest = None
            if lo is None:
                nearest = (old.nearest_length(s, km, on=ON),
                           new.nearest_length(s, km, on=ON))
            ok = sig(lo) == sig(ln) and (nearest is None
                                         or nearest[0] == nearest[1])
            plans.append((sector or "-", ok, lo is None, nearest))
        bad = (so != sn) + (not same_cands) + (fd != 0) + \
            sum(not ok for _, ok, _, _ in plans)
        diffs += bad
        row = dict(start=name, node=s, target=km, sectors_same=so == sn,
                   n_sectors=len(so), candidates=len(co),
                   candidates_same=same_cands, field_diffs=fd,
                   plans=" ".join(f"{sec}:{'ok' if ok else 'DIFF'}"
                                  f"{'(none)' if none else ''}"
                                  for sec, ok, none, _ in plans),
                   nearest=";".join(f"{a}/{b}" for *_, nr in plans
                                    if nr is not None for a, b in [nr]),
                   reach=fn.reach_km)
        rows.append(row)
        print(f"{name:15s} {km:5.0f} cands {len(co):6d} same={same_cands} "
              f"fielddiff={fd} sectors={'same' if so == sn else 'DIFF'} "
              f"{row['plans']} {row['nearest']} reach={fn.reach_km:.0f}",
              flush=True)
    # A fresh new-planner cache per start, so each start's first target is a
    # first loop; the old planner's cache is trimmed by its own LRU.
    new._fields_by_key.clear()

print(f"\n{len(rows)} (start, target) cells, {3 * len(rows)} plans; "
      f"differences: {diffs}")
print(f"disc field sets {new.disc_passes}, refined {new.disc_refines}, "
      f"fell back {new.disc_fallbacks}, whole-graph field sets "
      f"{new.full_passes} (includes nearest_length)")
print(f"wall time old {t_old:.0f} s, new {t_new:.0f} s")
if OUT:
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
