"""Member way ids of every road-route relation in a byway network, one per line.

Used to label chunks for byway_auc.py with a state's whole designated set
(e.g. all 26 `US:CO:Scenic` byways), not only the ones extract.py admits.

Usage: python byway_ways.py <file.osm.pbf> <network> > way_ids.txt
"""
import sys

import osmium

pbf, network = sys.argv[1], sys.argv[2]
ways, rels = set(), 0
for r in osmium.FileProcessor(pbf, osmium.osm.RELATION):
    if r.tags.get("route") == "road" and r.tags.get("network") == network:
        rels += 1
        ways.update(m.ref for m in r.members if m.type == "w")
print("\n".join(str(w) for w in sorted(ways)))
print(f"{rels} relations, {len(ways)} member ways", file=sys.stderr)
