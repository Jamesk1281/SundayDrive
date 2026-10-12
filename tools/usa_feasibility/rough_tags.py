"""km of drivable road by roughness tags; and the tags on the top-scoring named roads."""
import sys, collections, math
sys.path.insert(0, sys.argv[1])
import osmium
from common import DRIVABLE, PRIVATE_ACCESS
pbf = sys.argv[2]
names = set(sys.argv[3].split("|")) if len(sys.argv) > 3 else set()
km = collections.Counter(); total = 0.0
named = collections.defaultdict(collections.Counter)
ROUGH = {"bad", "very_bad", "horrible", "very_horrible", "impassable"}
def length(w):
    L = 0.0; prev = None
    for n in w.nodes:
        if not n.location.valid(): continue
        if prev:
            la1, la2 = math.radians(prev[1]), math.radians(n.location.lat)
            dl = math.radians(n.location.lon - prev[0])
            a = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dl/2)**2
            L += 2*6371.0088*math.asin(math.sqrt(min(1, a)))
        prev = (n.location.lon, n.location.lat)
    return L
fp = (osmium.FileProcessor(pbf, osmium.osm.NODE | osmium.osm.WAY).with_locations()
      .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY)).with_filter(osmium.filter.KeyFilter("highway")))
for w in fp:
    t = w.tags; hw = t.get("highway")
    if hw not in DRIVABLE: continue
    if t.get("access") in PRIVATE_ACCESS and t.get("motor_vehicle") != "yes": continue
    L = length(w); total += L
    four = t.get("4wd_only") == "yes"
    sm = t.get("smoothness", "")
    rough = sm in ROUGH
    tt = t.get("tracktype", "")
    hc = sm in ("very_bad", "horrible", "very_horrible", "impassable")
    if four: km["4wd_only=yes"] += L
    if rough: km["smoothness bad or worse"] += L
    if hc: km["smoothness very_bad or worse (high clearance)"] += L
    if four or hc: km["4wd_only OR smoothness very_bad+"] += L
    if t.get("surface") in ("unpaved","compacted","fine_gravel","gravel","dirt","ground","earth","rock","sand","mud","grass","pebblestone"): km["unpaved surface tag"] += L
    if not t.get("surface"): km["no surface tag"] += L
    if t.get("seasonal") or any(k.endswith(":conditional") for k, _ in t): km["any :conditional or seasonal tag"] += L
    nm = t.get("name", "")
    if nm in names:
        named[nm][f"hw={hw} surface={t.get('surface','-')} smooth={sm or '-'} 4wd={t.get('4wd_only','-')}"] += round(L, 1)
print(f"total drivable {total:,.0f} km")
for k, v in km.most_common():
    print(f"  {k:48s} {v:9,.0f} km  {100*v/total:5.1f}%")
for nm, c in named.items():
    print(nm); [print("    ", k, f"{v:.1f} km") for k, v in c.most_common(4)]
