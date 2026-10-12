"""Route effect of each candidate: the shipped Router, its _edge_scores monkeypatched to a candidate.

Usage: routes.py <region> <out_csv> <cand name> [<cand name> ...]
Trips are between public town centres (never trace points). pref 0 is the fastest route and the
same for every candidate; pref 0.5 and 1 are priced on the candidate's own scale.
"""
import sys, time, pickle
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *  # noqa
import router as R  # noqa: E402

TOWNS = {
    "ne": {"Concord MA": (42.4604, -71.3489), "Amherst MA": (42.3732, -72.5199), "Northampton MA": (42.3251, -72.6412),
           "Pittsfield MA": (42.4501, -73.2454), "Great Barrington MA": (42.1959, -73.3620), "Worcester MA": (42.2626, -71.8023),
           "Plymouth MA": (41.9584, -70.6673), "Brattleboro VT": (42.8509, -72.5579), "Woodstock VT": (43.6243, -72.5185),
           "Stowe VT": (44.4654, -72.6874), "Montpelier VT": (44.2601, -72.5754), "Manchester VT": (43.1637, -73.0723),
           "Rutland VT": (43.6106, -72.9726), "Burlington VT": (44.4759, -73.2121), "Keene NH": (42.9337, -72.2781),
           "Concord NH": (43.2081, -71.5376), "North Conway NH": (44.0537, -71.1284), "Lincoln NH": (44.0453, -71.6703),
           "Hanover NH": (43.7022, -72.2896), "Portsmouth NH": (43.0718, -70.7626), "Portland ME": (43.6591, -70.2568),
           "Camden ME": (44.2098, -69.0648), "Bethel ME": (44.4045, -70.7909), "Augusta ME": (44.3106, -69.7795),
           "Litchfield CT": (41.7470, -73.1887), "Hartford CT": (41.7658, -72.6734), "Mystic CT": (41.3543, -71.9665),
           "Newport RI": (41.4901, -71.3128), "Providence RI": (41.8240, -71.4128)},
    "co": {"Denver": (39.7392, -104.9903), "Boulder": (40.0150, -105.2705), "Estes Park": (40.3772, -105.5217),
           "Grand Lake": (40.2522, -105.8231), "Fort Collins": (40.5853, -105.0844), "Colorado Springs": (38.8339, -104.8214),
           "Canon City": (38.4409, -105.2425), "Salida": (38.5347, -105.9989), "Buena Vista": (38.8422, -106.1311),
           "Leadville": (39.2508, -106.2925), "Aspen": (39.1911, -106.8175), "Glenwood Springs": (39.5505, -107.3248),
           "Grand Junction": (39.0639, -108.5506), "Montrose": (38.4783, -107.8762), "Ouray": (38.0228, -107.6714),
           "Durango": (37.2753, -107.8801), "Telluride": (37.9375, -107.8123), "Gunnison": (38.5458, -106.9253),
           "Crested Butte": (38.8697, -106.9878), "Pagosa Springs": (37.2694, -107.0098), "Alamosa": (37.4695, -105.8700),
           "Trinidad": (37.1695, -104.5005), "Pueblo": (38.2544, -104.6091), "Lamar": (38.0872, -102.6208),
           "La Junta": (37.9850, -103.5438), "Limon": (39.2639, -103.6922), "Burlington": (39.3061, -102.2694),
           "Sterling": (40.6255, -103.2077), "Steamboat Springs": (40.4850, -106.8317), "Craig": (40.5153, -107.5464),
           "Kremmling": (40.0589, -106.3889), "Walden": (40.7311, -106.2836)},
    "ut": {"Moab": (38.5733, -109.5498), "Torrey": (38.2997, -111.4199), "Escalante": (37.7703, -111.6021),
           "Panguitch": (37.8225, -112.4358), "Springdale": (37.1889, -112.9986), "Kanab": (37.0475, -112.5263),
           "Cedar City": (37.6775, -113.0619), "Green River": (38.9950, -110.1593), "Price": (39.5994, -110.8107),
           "Logan": (41.7370, -111.8338), "Garden City": (41.9461, -111.3938), "Kamas": (40.6430, -111.2805),
           "Heber": (40.5069, -111.4132), "Delta": (39.3522, -112.5772), "Vernal": (40.4555, -109.5287),
           "Monticello": (37.8714, -109.3429), "Blanding": (37.6244, -109.4785), "Bluff": (37.2847, -109.5521),
           "Nephi": (39.7102, -111.8363), "Hanksville": (38.3725, -110.7137)},
}
PAIRS = {
    "ne": [("Concord MA", "Amherst MA"), ("Amherst MA", "Pittsfield MA"), ("Northampton MA", "Brattleboro VT"),
           ("Great Barrington MA", "Litchfield CT"), ("Worcester MA", "Keene NH"), ("Brattleboro VT", "Woodstock VT"),
           ("Woodstock VT", "Stowe VT"), ("Montpelier VT", "Burlington VT"), ("Manchester VT", "Rutland VT"),
           ("Rutland VT", "Hanover NH"), ("Hanover NH", "Lincoln NH"), ("Lincoln NH", "North Conway NH"),
           ("North Conway NH", "Bethel ME"), ("Portland ME", "Camden ME"), ("Augusta ME", "Camden ME"),
           ("Concord NH", "Portsmouth NH"), ("Keene NH", "Concord NH"), ("Hartford CT", "Litchfield CT"),
           ("Mystic CT", "Newport RI"), ("Providence RI", "Plymouth MA"), ("Pittsfield MA", "Manchester VT"),
           ("Stowe VT", "Burlington VT"), ("Worcester MA", "Northampton MA"), ("Portsmouth NH", "Portland ME")],
    "co": [("Denver", "Estes Park"), ("Estes Park", "Grand Lake"), ("Boulder", "Estes Park"), ("Glenwood Springs", "Aspen"),
           ("Montrose", "Ouray"), ("Ouray", "Durango"), ("Telluride", "Durango"), ("Gunnison", "Crested Butte"),
           ("Grand Junction", "Montrose"), ("Salida", "Gunnison"), ("Buena Vista", "Leadville"), ("Leadville", "Aspen"),
           ("Canon City", "Salida"), ("Pueblo", "Trinidad"), ("Alamosa", "Pagosa Springs"), ("Colorado Springs", "Canon City"),
           ("Steamboat Springs", "Craig"), ("Kremmling", "Walden"), ("Limon", "Lamar"), ("La Junta", "Lamar"),
           ("Sterling", "Burlington"), ("Limon", "Burlington"), ("Pueblo", "La Junta"), ("Fort Collins", "Sterling")],
    "ut": [("Torrey", "Escalante"), ("Panguitch", "Escalante"), ("Springdale", "Kanab"), ("Moab", "Green River"),
           ("Moab", "Monticello"), ("Logan", "Garden City"), ("Price", "Green River"), ("Cedar City", "Panguitch"),
           ("Blanding", "Bluff"), ("Vernal", "Price"), ("Kamas", "Heber"), ("Nephi", "Delta"), ("Hanksville", "Torrey"),
           ("Hanksville", "Green River")],
}
PLAINS = {"Limon", "Lamar", "La Junta", "Sterling", "Burlington", "Pueblo", "Fort Collins"}

region, out_csv, names = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
with open(SP / "cands.pkl", "rb") as f:
    CAND = pickle.load(f)
t0 = time.time()
rt = R.Router(str(PROC[region]))
print("router loaded", f"{time.time() - t0:.0f}s", flush=True)
ship = CAND["S0 shipped"][region]
assert (rt.edges.index.to_numpy() == np.arange(len(rt.edges))).all(), "edges not positionally indexed"
assert len(rt.edges) == len(ship) and np.allclose(rt.edges.score.to_numpy(), ship), "edge order differs"
assert np.allclose(rt._edge_scores({}), ship, atol=1e-9), "router's live blend differs from graph score"

current = {"s": ship}
R.Router._edge_scores = lambda self, weights: current["s"]
row_of = None
rows = []
for a, b in PAIRS[region]:
    sa, _ = rt.snap(*TOWNS[region][a]); sb, _ = rt.snap(*TOWNS[region][b])
    current["s"] = ship
    fast = rt.route(sa, sb, 0.0)
    if fast is None:
        print("no route", a, b); continue
    base = {}
    for name in names:
        s = CAND[name][region]
        current["s"] = s
        for pref in (0.5, 1.0):
            res = rt.route(sa, sb, pref)
            rows_idx = res.edges.index.to_numpy()   # graph_edges row labels == positions (RangeIndex)
            L = res.edges["length_m"].to_numpy()
            key = (pref,)
            if name == "S0 shipped":
                base[key] = set(rows_idx.tolist())
            shared = L[np.isin(rows_idx, list(base.get(key, set())))].sum() / L.sum() if key in base else np.nan
            rows.append(dict(region=region, trip=f"{a} - {b}", plains=(a in PLAINS and b in PLAINS), cand=name, pref=pref,
                             km=L.sum() / 1000, minutes=res.minutes, fast_km=fast.km, fast_min=fast.minutes,
                             extra_min=res.minutes - fast.minutes,
                             beaut_km_own=L[s[rows_idx] >= 7].sum() / 1000,
                             beaut_km_shipped=L[ship[rows_idx] >= 7].sum() / 1000,
                             mean_shipped=np.average(ship[rows_idx], weights=L),
                             fast_beaut_km_own=fast.edges["length_m"].to_numpy()[s[fast.edges.index.to_numpy()] >= 7].sum() / 1000,
                             shared_with_shipped=shared))
    print(a, "-", b, f"{time.time() - t0:.0f}s", flush=True)
D = pd.DataFrame(rows)
D.to_csv(out_csv, index=False)
g = D.groupby(["cand", "pref"], sort=False).agg(trips=("trip", "size"), extra_min=("extra_min", "median"),
        extra_min_mean=("extra_min", "mean"), beaut_own=("beaut_km_own", "sum"), beaut_shipped=("beaut_km_shipped", "sum"),
        km=("km", "sum"), shared=("shared_with_shipped", "mean"))
pd.set_option("display.width", 200)
print(g.round(2).to_string())
