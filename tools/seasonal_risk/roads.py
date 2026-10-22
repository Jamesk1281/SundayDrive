"""The named seasonal roads this study follows, as filters on the table, with a
through trip across each (gateway to gateway) for Q1's named sample and Q3.

`ten` are the brief's best-known roads, plus Independence Pass, the North
Cascades Highway and Crater Lake's Rim Drive to make ten. The rest are Q2's
sample, chosen to cover every window source. A `bbox` (lon0, lat0, lon1, lat1)
keeps a name match on the road meant: there are other Trail Ridge and Mountain
Roads in the country.

`ends` are two points a driver crosses the road between. `dead_end` roads
(an auto road to a summit) have the summit as the second end: when they are
shut the trip cannot be made at all.
"""

import pandas as pd

ROADS = {
    # --- the ten
    "beartooth": dict(label="Beartooth Highway (US 212)", ten=True,
                      match=lambda t: t.tag.str.startswith("table beartooth") | t.name.str.contains("Beartooth"),
                      bbox=(-110.1, 44.85, -109.2, 45.25),
                      ends=((45.0204, -109.9334), (45.1850, -109.2470))),        # Cooke City, Red Lodge
    "gtsr": dict(label="Going-to-the-Sun Road", ten=True,
                 match=lambda t: t.name == "Going-to-the-Sun Road",
                 bbox=(-114.1, 48.4, -113.3, 48.85),
                 ends=((48.4955, -113.9822), (48.7458, -113.4269))),             # West Glacier, St. Mary
    "tioga": dict(label="Tioga Road (CA 120, Yosemite)", ten=True,
                  match=lambda t: t.name.isin(["Tioga Road", "Tioga Pass Road"]),
                  bbox=(-119.9, 37.7, -119.1, 38.0),
                  ends=((37.9577, -119.1199), (37.7489, -119.5885))),            # Lee Vining, Yosemite Village
    "trail_ridge": dict(label="Trail Ridge Road (US 34, RMNP)", ten=True,
                        match=lambda t: (t.name == "Trail Ridge Road") & ~t.tag.str.startswith("mvum"),
                        bbox=(-105.95, 40.15, -105.5, 40.5),
                        ends=((40.3772, -105.5217), (40.2522, -105.8233))),     # Estes Park, Grand Lake
    "vt108": dict(label="VT 108 Smugglers' Notch", ten=True,
                  match=lambda t: (t.ref == "VT 108") | (t.name == "Vermont Route 108 South"),
                  bbox=(-72.9, 44.45, -72.65, 44.65),
                  ends=((44.4654, -72.6874), (44.6434, -72.8287))),              # Stowe, Jeffersonville
    "lincoln_gap": dict(label="Lincoln Gap Road", ten=True,
                        match=lambda t: t.name == "Lincoln Gap Road",
                        bbox=(-73.05, 44.05, -72.85, 44.15),
                        ends=((44.1120, -72.8565), (44.1056, -72.9976))),       # Warren, Lincoln
    "mwar": dict(label="Mount Washington Auto Road", ten=True, dead_end=True,
                 match=lambda t: t.name == "Mount Washington Auto Road",
                 bbox=(-71.35, 44.25, -71.2, 44.32),
                 ends=((44.3878, -71.1734), (44.2706, -71.3033))),               # Gorham, summit
    "independence": dict(label="Independence Pass (CO 82)", ten=True,
                         match=lambda t: t.tag.str.startswith("table independence_pass") | (t.ref == "CO 82"),
                         bbox=(-106.85, 39.0, -106.35, 39.2),
                         ends=((39.1911, -106.8175), (39.0828, -106.3825))),    # Aspen, Twin Lakes
    "north_cascades": dict(label="North Cascades Highway (SR 20)", ten=True,
                           match=lambda t: t.tag.str.startswith("table north_cascades") | (t.name == "North Cascades Highway"),
                           bbox=(-121.3, 48.4, -120.4, 48.8),
                           ends=((48.5290, -121.4410), (48.4779, -120.1862)),  # Marblemount, Winthrop
                           ),
    "crater_lake": dict(label="Crater Lake Rim Drive", ten=True,
                        match=lambda t: t.tag.str.contains("CRLA"),
                        bbox=(-122.3, 42.8, -121.95, 43.1),
                        ends=((42.8966, -122.1336), (43.0870, -122.1150))),     # park HQ, north entrance
    # --- Q2's wider sample
    "sonora": dict(label="Sonora Pass (CA 108)", match=lambda t: t.tag.str.startswith("table sonora_pass"),
                   bbox=(-120.1, 38.2, -119.4, 38.45),
                   ends=((38.3317, -119.9310), (38.3830, -119.4570))),           # Dardanelle, US 395 jct
    "ebbetts": dict(label="Ebbetts Pass (CA 4)", match=lambda t: t.tag.str.startswith("table ebbetts_pass"),
                    bbox=(-120.2, 38.4, -119.7, 38.7),
                    ends=((38.4770, -120.0400), (38.6900, -119.7800))),          # Lake Alpine area, Markleeville
    "chinook": dict(label="Chinook Pass (SR 410)", match=lambda t: t.tag.str.startswith("table chinook_pass"),
                    bbox=(-121.7, 46.8, -121.3, 47.0),
                    ends=((47.0450, -121.5390), (46.7290, -120.6981))),          # Crystal Mtn Blvd jct, Naches
    "dunraven": dict(label="Dunraven Pass (Yellowstone)", match=lambda t: t.tag.str.startswith("table dunraven_pass"),
                     bbox=(-110.6, 44.7, -110.3, 44.95),
                     ends=((44.7353, -110.4892), (44.9157, -110.4161))),         # Canyon Village, Tower Jct
    "lassen": dict(label="Lassen Park Highway (CA 89)", match=lambda t: t.tag.str.contains("LAVO"),
                   bbox=(-121.7, 40.35, -121.4, 40.6),
                   ends=((40.3474, -121.6011), (40.6735, -121.4277))),           # Mineral, Old Station
    "stevens_canyon": dict(label="Stevens Canyon Road (Mt Rainier)", match=lambda t: t.name == "Stevens Canyon Road",
                           bbox=(-121.8, 46.7, -121.5, 46.8),
                           ends=((46.7860, -121.7350), (46.7330, -121.5670))),  # Paradise, Ohanapecosh
    "sunrise": dict(label="Sunrise Road (Mt Rainier)", dead_end=True,
                    match=lambda t: t.name == "Sunrise Park Road",
                    bbox=(-121.7, 46.85, -121.5, 47.0),
                    ends=((47.0450, -121.5390), (46.9146, -121.6430))),          # SR 410, Sunrise
    "mt_blue_sky": dict(label="Mount Blue Sky Road (CO 5)", dead_end=True,
                        match=lambda t: t.name == "Mount Blue Sky Road",
                        bbox=(-105.7, 39.55, -105.55, 39.7),
                        ends=((39.7420, -105.5136), (39.5883, -105.6438))),     # Idaho Springs, summit
    "greylock": dict(label="Mount Greylock roads (Rockwell/Notch)", dead_end=True,
                     match=lambda t: t.name.isin(["Rockwell Road", "Notch Road", "Summit Road"])
                     & t.tag.str.contains("May 20-Oct 29"),
                     bbox=(-73.25, 42.55, -73.1, 42.7),
                     ends=((42.5960, -73.2010), (42.6370, -73.1660))),           # Lanesborough side, summit
    "jefferson_notch": dict(label="Jefferson Notch Road", match=lambda t: t.name == "Jefferson Notch Road",
                            bbox=(-71.45, 44.25, -71.3, 44.4),
                            ends=((44.3600, -71.4100), (44.2580, -71.3530))),   # US 2 side, Crawford/Base Rd
    "evans_notch": dict(label="Evans Notch (ME 113)", match=lambda t: t.ref == "ME 113",
                        bbox=(-71.1, 44.15, -70.9, 44.45),
                        ends=((44.3940, -70.9930), (44.1660, -70.9900))),       # Gilead, Chatham
    "hurricane_mtn": dict(label="Hurricane Mountain Road", match=lambda t: t.name == "Hurricane Mountain Road",
                          bbox=(-71.15, 44.05, -71.0, 44.12),
                          ends=((44.0780, -71.1270), (44.0960, -71.0110))),     # Intervale, South Chatham
    "kelley_stand": dict(label="Kelley Stand Road", match=lambda t: t.name == "Kelley Stand Road",
                         bbox=(-73.1, 43.0, -72.85, 43.1),
                         ends=((43.0700, -73.0790), (43.0760, -72.8650))),      # East Arlington, West Wardsboro
    "baxter": dict(label="Baxter State Park Tote Road", match=lambda t: t.name == "Baxter Park Road",
                   bbox=(-69.1, 45.8, -68.7, 46.3),
                   ends=((45.9400, -68.8650), (46.2020, -68.9970))),             # Togue Pond, Matagamon
}


def edges_of(table: pd.DataFrame, key: str, lonlat=None) -> pd.DataFrame:
    """The table rows of one road, kept to its bbox when `lonlat` (a function
    edge -> (lon, lat)) is given."""
    spec = ROADS[key]
    t = table.fillna({"name": "", "ref": "", "tag": ""})
    rows = t[spec["match"](t)]
    if lonlat is not None and len(rows):
        x0, y0, x1, y1 = spec["bbox"]
        keep = [x0 <= lon <= x1 and y0 <= lat <= y1
                for lon, lat in (lonlat(e) for e in rows["edge"])]
        rows = rows[keep]
    return rows
