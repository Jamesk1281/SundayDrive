"""The pre-registered icon and dull-control roads, bounded to the named stretch.

Written 2026-10-21 from the brief's two lists (git show d59c345:docs/national-scenery-types-brief.md), before
any candidate was computed. Do not edit after scores are seen. pin.py turns each
definition into OSM way ids (pins.csv); the bbox stays part of the pin, because a
way can run past the end of a stretch, so an edge counts only if its way is pinned
and its midpoint is inside the box.

Each road:
  regions  build regions whose owned edges are searched (data/national/build/<r>)
  refs     exact `ref` tokens (OSM splits several with ';'); any one matches
  name     a regex on `name`, matched in full
  both     True: a way needs a ref token AND the name; default: either
  bbox     (lon0, lat0, lon1, lat1), the named stretch's ends
  per_ref  optional {ref: bbox}, a tighter box for one ref of a multi-route byway
Link roads (*_link) are never pinned.
"""

ICONS = [
    dict(id="us163_monument_valley", label="US 163, Monument Valley (Kayenta to Mexican Hat)",
         regions=["ut", "az"], refs=["US 163"], bbox=(-110.30, 36.70, -109.84, 37.17)),
    dict(id="valley_of_fire", label="Valley of Fire Highway (I-15 to Northshore Road)",
         regions=["nv"], name=r"Valley of Fire Highway", bbox=(-114.90, 36.30, -114.35, 36.50)),
    dict(id="overseas_highway", label="Overseas Highway, US 1, Key Largo to Key West",
         regions=["fl"], refs=["US 1"], bbox=(-81.81, 24.50, -80.35, 25.20)),
    dict(id="tamiami_big_cypress", label="US 41 Tamiami Trail, Carnestown to Forty Mile Bend",
         regions=["fl"], refs=["US 41"], bbox=(-81.37, 25.70, -80.83, 25.95)),
    dict(id="badlands_sd240", label="Badlands Loop Road, SD 240",
         regions=["sd"], refs=["SD 240"], bbox=(-102.60, 43.60, -101.90, 44.10)),
    dict(id="needles_sd87", label="Needles Highway, SD 87",
         regions=["sd"], name=r"Needles Highway", bbox=(-103.65, 43.70, -103.40, 43.90)),
    dict(id="million_dollar_us550", label="Million Dollar Highway, US 550 Ouray to Silverton",
         regions=["co"], refs=["US 550"], bbox=(-107.80, 37.80, -107.60, 38.03)),
    dict(id="ut12", label="UT 12, Panguitch junction to Torrey",
         regions=["ut"], refs=["SR 12"], bbox=(-112.60, 37.50, -111.30, 38.35)),
    dict(id="ut128", label="UT 128 along the Colorado River, Moab to Cisco",
         regions=["ut"], refs=["SR 128"], bbox=(-109.65, 38.55, -109.20, 39.00)),
    dict(id="ut9_zion_mt_carmel", label="Zion-Mount Carmel Highway, UT 9, Canyon Junction to Mount Carmel Junction",
         regions=["ut"], refs=["SR 9"], bbox=(-112.952, 37.15, -112.665, 37.30)),
    dict(id="ca190_death_valley", label="CA 190 through Death Valley (Panamint Valley to Death Valley Junction)",
         regions=["ca-north", "ca-south"], refs=["CA 190"], bbox=(-117.55, 36.20, -116.40, 36.65)),
    dict(id="ca1_big_sur", label="CA 1 through Big Sur, Carmel River to San Carpoforo Creek",
         regions=["ca-north", "ca-south"], refs=["CA 1"], bbox=(-121.95, 35.766, -121.20, 36.535)),
    dict(id="tioga_ca120", label="Tioga Road, CA 120, Crane Flat to Tioga Pass",
         regions=["ca-north", "ca-south"], refs=["CA 120"], name=r"Tioga Road", bbox=(-119.81, 37.70, -119.255, 37.95)),
    dict(id="historic_columbia_river_hwy", label="Historic Columbia River Highway (both drivable segments)",
         regions=["or"], name=r"(East |West )?Historic Columbia River Highway", bbox=(-122.50, 45.40, -121.10, 45.75)),
    dict(id="chuckanut_drive", label="Chuckanut Drive, SR 11, Burlington to Fairhaven",
         regions=["wa"], refs=["SR 11"], bbox=(-122.55, 48.45, -122.30, 48.75)),
    dict(id="beartooth_us212", label="Beartooth Highway, US 212, Red Lodge to the Northeast Entrance",
         regions=["mt", "wy"], refs=["US 212"], bbox=(-110.01, 44.90, -109.24, 45.20)),
    dict(id="blue_ridge_parkway", label="Blue Ridge Parkway",
         regions=["nc", "va"], name=r"Blue Ridge Parkway", bbox=(-83.50, 35.40, -78.80, 38.10)),
    dict(id="skyline_drive", label="Skyline Drive, Shenandoah National Park",
         regions=["va"], name=r"Skyline Drive", bbox=(-78.90, 38.00, -78.10, 38.95)),
    dict(id="cherohala_skyway", label="Cherohala Skyway",
         regions=["nc", "tn"], name=r"Cherohala Skyway", bbox=(-84.40, 35.20, -83.80, 35.50)),
    dict(id="natchez_trace_parkway", label="Natchez Trace Parkway",
         regions=["ms", "al", "tn"], name=r"Natchez Trace Parkway", bbox=(-91.50, 31.40, -86.80, 36.10)),
    dict(id="nc12_outer_banks", label="NC 12 on the Outer Banks, Corolla to Ocracoke",
         regions=["nc"], refs=["NC 12"], bbox=(-76.05, 35.05, -75.40, 36.40)),
    dict(id="tx_hill_country_rm335_336_337", label="Texas Hill Country RM 335, 336 and 337",
         regions=["tx-west", "tx-east"], refs=["RM 335", "RM 336", "RM 337"], bbox=(-100.20, 29.50, -99.10, 30.10)),
    dict(id="flint_hills_k177", label="Flint Hills Scenic Byway, K-177 Council Grove to Cassoday",
         regions=["ks"], refs=["KS 177"], bbox=(-96.70, 38.04, -96.30, 38.67)),
    dict(id="sandhills_n2", label="Sandhills Journey, NE 2, Grand Island to Alliance",
         regions=["ne"], refs=["N-2"], bbox=(-102.88, 40.80, -98.33, 42.20)),
    # OSM carries no relation for this state byway. Its seven routes and their ends are
    # from WSDOT's designation as Wikipedia lists it (Palouse Scenic Byway, fetched 2026-10-21).
    dict(id="palouse_scenic_byway", label="Palouse Scenic Byway (SR 26, 27, 194, 271, 272, 278, US 195)",
         regions=["wa"], refs=["SR 26", "SR 27", "SR 194", "US 195", "SR 271", "SR 272", "SR 278"],
         bbox=(-118.25, 46.40, -117.03, 47.47),
         per_ref={"SR 26": (-118.25, 46.60, -117.35, 46.95),     # Adams County line to Colfax
                  "SR 27": (-117.25, 46.70, -117.03, 47.235),    # Pullman to Tekoa
                  "SR 194": (-117.46, 46.60, -117.17, 46.75),    # Almota to Pullman
                  "US 195": (-117.45, 46.40, -117.03, 47.262),   # Idaho line to the Spokane County line
                  "SR 271": (-117.40, 47.10, -117.20, 47.25),    # Oakesdale to Rosalia
                  "SR 272": (-117.40, 46.85, -117.03, 46.95),    # Colfax to Palouse
                  "SR 278": (-117.15, 47.35, -117.03, 47.47)}),  # Rockford to the Idaho line
]

CONTROLS = [
    dict(id="i15_barstow_primm", label="I-15, Barstow to Primm",
         regions=["ca-south", "nv"], refs=["I 15"], bbox=(-117.03, 34.85, -115.38, 35.62)),
    dict(id="i10_tonopah_quartzsite", label="I-10, Tonopah to Quartzsite",
         regions=["az"], refs=["I 10"], bbox=(-114.24, 33.30, -112.93, 33.75)),
    dict(id="us6_delta_eureka", label="US 6, Delta to Eureka",
         regions=["ut"], refs=["US 6"], bbox=(-112.60, 39.33, -112.10, 39.97)),
    dict(id="i40_amarillo", label="I-40 through Amarillo",
         regions=["tx-west"], refs=["I 40"], bbox=(-101.98, 35.10, -101.70, 35.30)),
    dict(id="i80_grand_island_north_platte", label="I-80, Grand Island to North Platte",
         regions=["ne"], refs=["I 80"], bbox=(-100.78, 40.55, -98.33, 41.20)),
    dict(id="i70_east_of_denver", label="I-70 east of Denver (E-470 to the Kansas line)",
         regions=["co"], refs=["I 70"], bbox=(-104.73, 38.90, -102.04, 39.85)),
    dict(id="us287_colorado_plains", label="US 287 on the Colorado plains (Limon to Oklahoma)",
         regions=["co"], refs=["US 287"], bbox=(-103.70, 36.99, -102.04, 39.30)),
    dict(id="i75_ocala_tampa", label="I-75, Ocala to Tampa",
         regions=["fl"], refs=["I 75"], bbox=(-82.60, 28.00, -82.00, 29.20)),
    dict(id="i4_orlando", label="I-4 through Orlando",
         regions=["fl"], refs=["I 4"], bbox=(-81.50, 28.40, -81.25, 28.65)),
    dict(id="bell_road_phoenix", label="Bell Road, Phoenix",
         regions=["az"], name=r"((East|West|North) )?Bell Road", bbox=(-112.45, 33.60, -111.85, 33.66)),
    dict(id="westheimer_houston", label="Westheimer Road, Houston",
         regions=["tx-east"], name=r"Westheimer Road", bbox=(-95.85, 29.70, -95.35, 29.76)),
    dict(id="i95_nj_turnpike", label="I-95 on the New Jersey Turnpike",
         regions=["nj"], refs=["I 95"], name=r"New Jersey Turnpike", both=True, bbox=(-75.00, 39.60, -73.90, 40.90)),
    dict(id="i635_lbj", label="I-635 LBJ Freeway, Dallas",
         regions=["tx-east"], refs=["I 635"], bbox=(-97.00, 32.70, -96.50, 33.00)),
]

ROADS = [dict(r, kind="icon") for r in ICONS] + [dict(r, kind="control") for r in CONTROLS]
