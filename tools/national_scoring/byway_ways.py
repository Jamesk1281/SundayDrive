"""Way ids of every route relation in one OSM byway network, for attrs.py's byway_osm label.

Usage: byway_ways.py <region.osm.pbf> <network> <out.txt>
  e.g. byway_ways.py co/pbf/region.osm.pbf US:CO:Scenic $NS_WORK/co_byway_ways.txt

Colorado's label is its whole state scenic network (the 26 US:CO:Scenic byways), not
extract.py's own scenic flag. The 2026-10-12 way list was the feasibility review's and is
gone with its scratch; this regenerates it from the region's own extract.
"""
import sys
import osmium

pbf, network, out = sys.argv[1], sys.argv[2], sys.argv[3]


class Rels(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.ways, self.names = set(), []

    def relation(self, r):
        if r.tags.get("type") == "route" and r.tags.get("network") == network:
            self.names.append(r.tags.get("name", r.tags.get("ref", str(r.id))))
            self.ways.update(m.ref for m in r.members if m.type == "w")


h = Rels()
h.apply_file(pbf)
with open(out, "w") as f:
    f.write("\n".join(str(w) for w in sorted(h.ways)))
print(len(h.names), "relations,", len(h.ways), "ways:", "; ".join(sorted(h.names)))
