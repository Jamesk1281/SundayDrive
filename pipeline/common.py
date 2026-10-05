"""Shared vocabulary for the scoring + routing pipeline.

These constants describe *what counts as a road* and *which map projection we
measure distances in*. They were duplicated across extract.py, graph.py,
score.py and router.py; keeping them here means there's one place to change when
(say) a new road class should be considered drivable.
"""

# OSM highway= values we treat as drivable roads. Everything else (footways,
# cycleways, service alleys, etc.) is ignored when extracting and graph-building.
DRIVABLE = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "unclassified", "residential",
    "living_street",
}

# access= values that mean "not open to the public". A road tagged this way is
# skipped unless it also carries motor_vehicle=yes (a common override).
#
# That is the whole of what extract.py and graph.py read, and it misses most of
# what closes a road to a car: `motor_vehicle=no`, `access=permit`, a locked gate.
# `car_access` below is the full rule. Until the next rebuild applies it there,
# closures.py uses it to write closed_to_cars.parquet beside the graph, and the
# router masks those roads (docs/closed-roads.md).
PRIVATE_ACCESS = {"private", "no"}

# The keys that decide whether a car may use a road or pass a barrier, most
# specific first: OSM's transport-mode hierarchy, in which `motorcar` binds cars
# alone, `motor_vehicle` everything with an engine, `vehicle` everything on
# wheels and `access` everyone. The most specific one present wins, so
# `access=no` + `motor_vehicle=yes` and `vehicle=no` + `motorcar=yes` are open.
# Subkeys such as `access:delivery` are not transport modes and are not read.
CAR_ACCESS_KEYS = ("motorcar", "motor_vehicle", "vehicle", "access")

# The values of those keys that shut a car out. Every other value is open:
# `yes`, `permissive`, `designated`, `discouraged`, `unknown`, anything not
# recognised, and `destination` and `customers`, which are legal for a driver
# with business there.
CLOSED_TO_CARS = frozenset({"no", "private", "permit", "agricultural", "forestry",
                            "military", "emergency", "delivery", "psv", "bus"})

# Barriers a car drives through unless the node's own tags close them, by
# `car_access` or `locked=yes`. As in OSRM's car profile, an untagged gate is
# open: most are farm and park gates standing open. Every other `barrier=` value
# (block, bollard, chain, jersey_barrier, ...) stops a car unless the node's own
# tags open it.
#
# `kerb` is here although the rule as decided would block it. The 19 kerbs on
# drivable ways in this extract are pedestrian crossings' kerbs dropped onto the
# road's centreline, Broadway in Cambridge and two New Haven trunk roads among
# them, and blocking them closes those roads. 16 are tagged lowered, flush or
# `highway=crossing`, which OSRM's car profile passes for the same reason
# (docs/closed-roads.md, decision 4).
PASSABLE_BARRIERS = frozenset({"gate", "lift_gate", "swing_gate", "cattle_grid",
                               "toll_booth", "border_control", "entrance",
                               "height_restrictor", "sally_port", "arch", "no",
                               "kerb"})


def car_access(tags):
    """The (key, value) that decides whether a car may pass, or None when no
    key in CAR_ACCESS_KEYS is set. `tags` is a dict or an osmium TagList.

    The value is lower-cased and stripped. A car is shut out when it is in
    CLOSED_TO_CARS; `closed_to_cars` says so in one call.
    """
    for key in CAR_ACCESS_KEYS:
        value = (tags.get(key) or "").strip().lower()
        if value:
            return key, value
    return None


def closed_to_cars(tags):
    """The tag that closes a way with these tags to a car, as "key=value", or
    None if a car may drive it."""
    found = car_access(tags)
    if found is not None and found[1] in CLOSED_TO_CARS:
        return f"{found[0]}={found[1]}"
    return None


def barrier_closes(tags):
    """Why a node with these tags stops a car on the road it sits on, or None.

    A ford stops it whatever else is tagged: a consumer car app should not plan
    one. A PASSABLE_BARRIERS gate stops it only when its own tags close it. Any
    other `barrier=` stops it unless its own tags open it.
    """
    if (tags.get("ford") or "").strip().lower() == "yes":
        return "ford=yes"
    barrier = (tags.get("barrier") or "").strip().lower()
    if not barrier:
        return None
    found = car_access(tags)
    says = f"{found[0]}={found[1]}" if found else None
    if barrier in PASSABLE_BARRIERS:
        if found is not None and found[1] in CLOSED_TO_CARS:
            return f"barrier={barrier}, {says}"
        if (tags.get("locked") or "").strip().lower() == "yes":
            return f"barrier={barrier}, locked=yes"
        return None
    if found is not None and found[1] not in CLOSED_TO_CARS:
        return None
    return f"barrier={barrier}" + (f", {says}" if says else "")

# The traffic controls a car has to stop at, mapped to the three kinds worth
# telling apart. Massachusetts has 29,772 of them — 11,348 signals, 17,567 stop
# signs, 839 give-ways and 18 mini-roundabouts — and the graph charged nothing
# for any of them until 2026-08-15, which is most of why its travel times ran
# 22% optimistic (see docs/junction-timing-plan.md).
#
# Mini-roundabouts join the give-ways: there are 18 in the state and only 7 sit
# on a drivable way, so a column of their own would be a column of zeroes.
CONTROL_KINDS = {
    "traffic_signals": "signal",
    "stop": "stop",
    "give_way": "giveway",
    "mini_roundabout": "giveway",
}

# One count per kind per direction of travel, written by graph.py and priced by
# router.py. Here rather than in graph.py because the serving box deliberately
# does not install the pipeline's dependencies (osmium, rasterio — see
# server/DEPLOY.md), so router.py cannot import graph.py to learn the names of
# the columns it has to read.
CONTROL_COLUMNS = [f"n_{kind}_{d}" for kind in ("signal", "stop", "giveway")
                   for d in ("fwd", "rev")]

# The closed window on each row of seasonal_closures.parquet, both ends
# included: written by closures.py and read by router.py, here for the same
# reason as CONTROL_COLUMNS. A window whose start falls after its end wraps the
# year end, as Nov 1 - Apr 30 does.
CLOSURE_WINDOW = ("start_month", "start_day", "end_month", "end_day")


def in_window(window, month_day) -> bool:
    """Whether (month, day) falls inside a CLOSURE_WINDOW, both ends included."""
    start, end = tuple(window[:2]), tuple(window[2:])
    if start <= end:
        return start <= month_day <= end
    return month_day >= start or month_day <= end


# oneway= values, and which direction they permit. Shared because graph.py and
# router.py have to agree exactly: graph.py decides which nodes are mutually
# reachable and router.py decides which edges may be traversed, so a road that
# one treats as two-way and the other as one-way produces a node the API accepts
# and then cannot route out of.
ONEWAY_FWD = {"yes", "true", "1"}      # forward only
ONEWAY_REV = {"-1", "reverse"}         # reverse only

# The projected coordinate system we do all metric work in: NAD83 / Massachusetts
# Mainland, whose units are meters. Lengths, buffers and nearest-feature
# distances are only meaningful in a projected CRS like this — raw lon/lat
# (EPSG:4326) degrees are not a constant distance apart. State data starts in
# 4326 and is reprojected to this before any distance math.
CRS_METERS = 26986
