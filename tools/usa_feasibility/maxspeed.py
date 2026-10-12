"""Length-weighted harmonic-mean posted speed by class where tagged, vs graph.py's SPEED_KMH defaults."""
import sys, math, collections
sys.path.insert(0, sys.argv[1])
import osmium
from common import DRIVABLE, PRIVATE_ACCESS
from graph import SPEED_KMH, parse_maxspeed
L = collections.Counter(); T = collections.Counter(); tagged = collections.Counter()
fp = (osmium.FileProcessor(sys.argv[2], osmium.osm.NODE | osmium.osm.WAY).with_locations()
      .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY)).with_filter(osmium.filter.KeyFilter("highway")))
for w in fp:
    t = w.tags; hw = t.get("highway")
    if hw not in DRIVABLE or (t.get("access") in PRIVATE_ACCESS and t.get("motor_vehicle") != "yes"): continue
    km = 0.0; prev = None
    for n in w.nodes:
        if not n.location.valid(): continue
        if prev:
            la1, la2 = math.radians(prev[1]), math.radians(n.location.lat); dl = math.radians(n.location.lon - prev[0])
            km += 2*6371.0088*math.asin(math.sqrt(min(1, math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dl/2)**2)))
        prev = (n.location.lon, n.location.lat)
    L[hw] += km
    v = parse_maxspeed(t.get("maxspeed", ""))
    if v and v > 5:
        tagged[hw] += km; T[hw] += km / v
print(f"{'class':14s} {'km':>8s} {'tagged%':>7s} {'tagged hm km/h':>14s} {'default':>7s}")
for hw in ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential"):
    hm = tagged[hw] / T[hw] if T[hw] else float('nan')
    print(f"{hw:14s} {L[hw]:8,.0f} {100*tagged[hw]/max(L[hw],1e-9):7.1f} {hm:14.1f} {SPEED_KMH[hw]:7d}")
