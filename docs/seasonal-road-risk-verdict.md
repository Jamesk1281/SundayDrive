# Verdict: how much risk to take on roads that are sometimes closed

This study answers the owner's question: should roads that are open only some of
the year (seasonal passes, gated park and forest roads) be banned outright, or is
it worth the risk of sending someone to a shut one? Measured 2026-10-21/22 on
`claude/seasonal-road-risk`, off `usa` at `de43cb4`. The numbers come from the
**pre-decisions data**, `data/processed-us` and `data/pack-us` as they stood
before the six-decisions swap; see "What the data swap could move". **Nothing
under `pipeline/`, `server/`, `ios/` or `data/` was changed.** Bans, margins and
the mid-drive avoid were simulated in memory, through the server's own
`_route`. The scripts, CSVs and how to rerun them are in
`tools/seasonal_risk/README.md`.

---

## The answer

**Don't ban them. Keep routing them, widen the guessed windows where the
evidence says they open early, and teach the reroute to remember the road the
driver turned away from.**

1. **A ban costs far more than it saves.** On random US trips, a ban saves
   37.6 expected stranded minutes per 1,000 trips. It costs 108.5 certain
   minutes per 1,000 trips, makes 3.2 more trips per 1,000 impossible, and
   loses all of the scenery on these roads. In seasonal-road country a further
   145 trips per 1,000 become impossible over the year. Nine of the 24 named
   roads can no longer be crossed at all, and a tenth only one way. Those nine
   include Beartooth, Chinook, Sonora and Dunraven. Tioga becomes a
   380-minute drive instead of 118, and North Cascades 375 instead of 117. The
   ban beats even P5 alone only in seasonal-road country, and only if a
   stranded minute counts as four ordinary ones and the failed trips are
   ignored. It never beats the recommended policy.
2. **The risk is real, and it sits in the guessed windows.** The hand-table
   windows (published dates, ten-season longest) are almost never dangerously
   open: 1.3 dangerous days per season out of sample. OSM's undated default,
   `WINTER` = Nov 1–Apr 30, is the one that sends drivers to shut roads. On the
   high passes that carry it, it says "open" while the road is still shut in 83%
   of springs, a median 24 days early. Across the samples it causes most of the
   expected stranding.
3. **The hypothesis in mechanism item 5 is true, and it is worse than stated.**
   A driver turned back at a closed gate is sent back to it by 93% of reroutes.
   92% still do so just past the junction where the right way out leaves the
   road they came in by. In 39% of cases the app never stops pointing back
   within 80 km of driving the right way. `declined_uturn` does not rescue them:
   replies asked with it still send them back 89% of the time.

### Recommended policy

| Part | What | Why |
|---|---|---|
| **P2, by source** | `WINTER` default (`osm_default`): **close 45 days longer in spring**, autumn unchanged. `UNKNOWN_SEASON` and MVUM/NPS agency dates (`unknown`, `agency_dated`): **±7 days**. Hand table and OSM-dated windows: **no margin**. | These are the ends that miss (Q2). A margin on the hand table double-counts its ten-season bias (trap 5): it stays shut a median 20–30 days after the road opens. |
| **P5, remember the road** | The reroute rules out the seasonal stretch the driver turned away from. | Cuts stranded minutes by a further 25–30% in seasonal country and 70% on random trips. That beats the 20% tie band, so it earns its app change (Q4). |
| **P3, risk price** | Not worth building. | Detours are so long that pricing the risk barely moves the routes, even at 10× risk aversion (Q4). |
| **P4, planning notice** | Optional copy, not needed for the decision. | It would show on about 0.1% of all trips and 9% of trip-days on seasonal roads. The model gives it no stranding benefit. |
| **Three data fixes** | Outside the P0–P5 framing. | North Cascades, Crater Lake and Glacier's Logan Pass windows are wrong by weeks; see "Defects found". |

Under the brief's rule (expected stranded minutes, at least 90% of P0's
seasonal-road scenery kept in **every** sample), this combination keeps
**91–100%** of the scenery. Against today it cuts expected stranding:

| sample | P0 (today) | recommended + P5 | cut |
|---|---:|---:|---:|
| random US trips (`us`, 273) | 37.6 | 6.5 | −83% |
| seasonal-road country (`near`, 220) | 1,474 | 489 | −67% |
| New England random (`ne`, 100) | 7.3 | 3.4 | −53% |
| the named roads, gateway to gateway (`named`, 48) | 3,842 | 1,582 | −59% |

All figures are stranded minutes per 1,000 trips. Trips are spread evenly over
the year, and only answered trips are counted.

**At the 80% bar:** default 14/45, OSM-dated 14, table 7, unknown and agency 14,
plus P5. Stranding falls to 320 (`near`) and 928 (`named`). **At the 95% bar:**
default 0/30, nothing else, plus P5. Stranding falls to 699 (`near`) and 1,982
(`named`). See "The frontier".

### What a build would touch (for the separate build that follows)

- **Margins** belong where windows are written, not in the router.
  `pipeline/closures.py` `WINTER` (spring end only) and
  `pipeline/winter_closures.py` `UNKNOWN_SEASON` and the MVUM/NPS-description
  rows, as a per-source margin before rows are written. The router stays as it
  is (`router.py:2775-2779`), and the closure version still keys every cache.
  Both files belong to the parallel six-decisions unit today, so build after it
  merges.
- **P5** is a new reroute parameter on `/api/route`: the edge rows, or the route
  id plus stretch, to close for this request. It joins
  `_parse_declined_uturn` (`server/app.py:448`) and is added to
  `_slot_weights`' `blocked` set the way `_keep_ahead` already blocks slots
  (`router.py:2786`). The route's GeoJSON should list its seasonal stretches, so
  the app knows what it is driving onto. The app needs one rule: a driver who
  reverses within some distance of a seasonal stretch on the active route has
  turned away from it, so send it with every reroute until arrival. A visible
  "Road closed" button is optional, and nothing here needs one.
- **No UI is required.** P4's notice is the only visible element, and it is
  optional.

---

## Q1: what a ban costs

Sample (`tools/seasonal_risk/samples.json`, seed 20261021):
- **`ne`**: `tools/national_build/ne_trip_pairs.json`, 100 pairs.
- **`us`**: 300 pairs, the origin uniform over road km, the destination at a
  random bearing 20–150 km away.
- **`near`**: 300 pairs in seasonal-road country: a seasonal edge drawn by
  length, the origin 5–60 km from it, and the destination across it. Biased
  toward seasonal roads on purpose.
- **`named`**: 24 roads, gateway to gateway, both ways.

Every trip was asked of `/api/route` in process at pref 0.5, the app's default,
in five runs: with nothing closed; under P0 on 2026-06-15, 2026-08-15 and
2026-10-15; and under P1 (every row closed all year, an in-memory copy of the
table). 27 `us` and 80 `near` pairs fall outside coverage in every run and are
dropped. Trail Ridge's all-year permit closure is lifted in every run, as the
brief directs.

| sample | run | share of routes on a seasonal edge | beautiful km on seasonal edges | CLOSED_FOR_SEASON |
|---|---|---:|---:|---:|
| us | Jun 15 | 2.2% | 131 | 1 |
| us | Aug 15 | 2.6% | 92 | 1 |
| us | Oct 15 | 2.2% | 92 | 1 |
| us | ban | 0 | 0 | 3 |
| near | Jun 15 | 41.1% | 1,769 | 6 |
| near | Aug 15 | 43.6% | 1,984 | 2 |
| near | Oct 15 | 41.7% | 1,957 | 2 |
| near | ban | 0 | 0 | **61 of 220** |
| ne | all three dates | 1.0% | 6 | 0 |
| named | Jun / Aug / Oct | 82% / 100% / 77% | 967 / 1,468 / 982 | 3 / 0 / 5 |
| named | ban | 0 | 0 | **19 of 48** |

Trap 3 shows in the table. A ban changes 2.6% of random routes in August, yet it
removes every beautiful km those roads carry. The roads it removes are the ones
the app is for:

| road | all open, both ways (min) | banned (min) | beautiful km lost | note |
|---|---:|---:|---:|---|
| Beartooth (US 212) | 140 | — | 155 | the crossing is impossible |
| Going-to-the-Sun | 190 | 187 | 126 | US 2 is as fast; the scenery is what goes |
| Tioga (CA 120) | 236 | 760 | 178 | +262 min per trip |
| Trail Ridge (US 34) | 167 | 447 | 132 | +140 min per trip |
| VT 108 Smugglers' Notch | 57 | 90 | 12 | +17 min per trip |
| Lincoln Gap | 34 | 80 | 7 | +23 min per trip |
| Mt Washington Auto Road | 59 | — | 25 | impossible (summit) |
| Independence Pass (CO 82) | 135 | 451 | 55 | +158 min per trip |
| North Cascades (SR 20) | 234 | 751 | 119 | +259 min per trip |
| Crater Lake Rim Drive | 59 | 116 | 20 | +28 min per trip |
| Sonora, Chinook, Dunraven, Greylock, Kelley Stand, Mt Blue Sky, Sunrise | — | — | 338 in all | all impossible under a ban; Stevens Canyon one way |

Per road and month: `tools/seasonal_risk/q1_named.csv`. Per run:
`q1_by_run.csv`.

---

## Q2: how often our windows are wrong

**Evidence:** 176 road-seasons on 17 roads from agency tables and releases (NPS,
WSDOT, CDOT, Caltrans, VTrans and the press), read 2026-10-21. Every date has
its URL in `tools/seasonal_risk/q2_published_dates.csv`. Each date also has a
quality: actual, scheduled, projected, or "by", meaning a report date the road
was open by.

**Method:** a miss is in days and signed so that **positive is dangerous**,
meaning the router says open while the road is shut. The open-end miss is the
actual opening minus our first open day. The close-end miss is our first closed
day minus the actual closing.

**The window compared is the router's own.** It is the union of the windows on
the seasonal edges the server's route across the road actually drives, so one
short edge counts if it is on the route. The source that sets each end is
recorded. Crater Lake's two halves and Old Fall River Road, which have no
through trip, use the window covering most of their km. The hand table's own
ten seasons are flagged in-sample: a ten-season-longest window cannot miss on
the seasons it was chosen from (trap 5).

| road | our window opens / closes | set by | seasons (open / close) | dangerous seasons at the open end: worst | at the close end: worst | median days shut while actually open (open / close end) |
|---|---|---|---|---|---|---|
| Tioga | Jun 11 / Nov 1 | table / OSM+table | 16 / 16 | **5: +41 d** (2023) | 2: +11 d (2021) | 15 / 12.5 |
| Going-to-the-Sun (Logan Pass) | Jul 1 / Oct 1 | OSM dated | 13 / 13 | **4: +12 d** | **7: +28 d** (Sep closings) | 7 / — |
| Lassen | Jul 26 / Oct 21 | table | 17 / 16 | 0 | 0 | **53 / 26** |
| Trail Ridge | Jun 1 / Oct 1 | OSM+NPS / OSM | 10 / 10 | 0 | 0 | 9 / 22 |
| Old Fall River | Jul 11 / Oct 1 | table (park) | 9 / 9 | 0 | 2: +5 d | 9 / 17 |
| Crater Lake, West Rim | Aug 1 / Oct 15 | table (park) | 20 / 13 | 0 | 1: +1 d | **53** / 13 |
| Crater Lake, East Rim | Aug 1 / Oct 15 | table (park) | 19 / 13 | 0 | **4: +14 d** (2013) | 23 / 8 |
| Chinook (SR 410) | Jun 11 / Oct 24 | table | 16 / 16 | 1: +12 d (2011, out of sample) | 1: +5 d | 16 / 18.5 |
| North Cascades (SR 20) | **Jul 1 / Oct 1** | **unknown** (a 30 m edge) | 17 / 16 | 0 | 0 | **57 / 50.5** |
| Independence Pass | May 28 / Oct 25 | table | 6 / 11 | 2: +4 d (2020, 2024) | 0 | 1.5 / 11 |
| Beartooth | May 28 / Oct 12 | table | 5 / 2 | 2: +4 d (2018, 2024) | 1: +2 d (2023) | 1 / 0.5 |
| Sonora Pass | Jun 13 / Nov 1 | table / WINTER+table | 4 / 2 | 0 | 0 | 36 / 58.5 |
| VT 108 | May 1 / Nov 1 | OSM dated | 4 / 2 | **3: +14 d** (2024) | 0 | — / 18 |
| Lincoln Gap | May 16 / Oct 15 | OSM dated | 1 / 0 | 0 | — | 1 / — |
| Greylock | May 20 / Oct 30 | OSM dated | 3 / 1 | 0 | 0 | 2 / 0 |
| Stevens Canyon (Rainier) | Jul 1 / Oct 1 | unknown | 2 / 1 | 0 | 0 | 35.5 / 16 |
| Sunrise Road (Rainier) | Jul 1 / Oct 1 | unknown | 1 / 1 | 0 | 0 | 9 / 4 |

**Sources:**
- **Tioga:** [nps.gov/yose seasonal.htm](https://www.nps.gov/yose/planyourvisit/seasonal.htm), Roads CSV, 2010–2025.
- **Going-to-the-Sun:** [Logan Pass dates](https://www.nps.gov/glac/learn/news/logan-pass-opening-and-closing-dates.htm), 2010–2022.
- **Lassen:** [spring clearing](https://www.nps.gov/lavo/planyourvisit/winter-road-closures-and-spring-clearing-update.htm), 2010–2026.
- **Trail Ridge and Old Fall River:** [ROMO table](https://www.nps.gov/romo/learn/photosmultimedia/opening_closing_trr_ofr.htm), 2000–2009, and the [2016 closing](https://www.nps.gov/romo/learn/news/pr_trail-ridge-road-closes-on-november-18-to-through-travel-for-the-season.htm).
- **Crater Lake:** [hours](https://www.nps.gov/crla/planyourvisit/hours.htm), 2004–2023.
- **Chinook and North Cascades:** [WSDOT](https://wsdot.wa.gov/travel/roads-bridges/mountain-pass-closure-and-opening-dates), 2010–2026.
- **Independence Pass:** CDOT [closings](https://www.codot.gov/news/2024/october/seasonal-closure-co82-independence-pass-through-spring-2025), [openings](https://www.codot.gov/news/2025/may/independence-pass-open-for-2025-season) and [2025](https://www.codot.gov/news/2025/november/co82-independence-pass-closed-nov17).
- **Beartooth, Sonora, VT 108, Lincoln Gap, Greylock and Rainier:** NPS and agency releases and local press, one URL per date in the CSV.

**By the source that sets each end** (`q2_by_binding_source.csv`):

| source | end | road-seasons (roads) | dangerous seasons | dangerous days per season | days shut while open, per season |
|---|---|---:|---:|---:|---:|
| hand table | spring, out of sample | 82 (8) | 9.8% | 1.3 | 30.2 |
| hand table | spring, in sample | 30 (5) | 6.7% | 0.2 | 21.6 |
| hand table | autumn, out of sample | 50 (7) | 16.0% | 0.6 | 15.0 |
| OSM dated | spring | 21 (4) | 33.3% | 2.7 | 4.9 |
| OSM dated | autumn | 26 (4) | 26.9% | 3.2 | 13.2 |
| unknown | both | 38 (3) | 0% | 0 | 47–56 |

**Each source's own window, wherever it is written** (the standalone test; it
answers "if this were the only window"):
- **`WINTER` default:** n = 47 springs on 4 roads (Tioga, Going-to-the-Sun,
  North Cascades, Lassen). Dangerous in **83%**, median **+24 days**, p90 +61.
  In autumn, dangerous in 33%.
- **OSM dated:** 43% of springs and 38% of autumns, median −4 days.
- **Hand table:** 8.5% / 9.6%, median −21 / −16 days.

**The escape hatch, labelled where it applies:**
- **`WINTER`** sets few published ends. Its risk curve in Q4 is its own window
  on the high passes. That is a worst case for the low New England gravel roads
  that carry it most. Jefferson Notch, Evans Notch and Kelley Stand have no
  published history; only forum reports exist ("usually open by Memorial Day"),
  and those are not used. Q4 repeats with the pooled curve as a sensitivity.
- **`UNKNOWN_SEASON`'s** zero misses come from three Washington roads. **MVUM's
  dated and undated windows have no published actual dates at all.** Both take
  the pooled curve in Q4, labelled as a proxy, and their recommendation rests
  mostly on the stranding cost.
- **Mid-season closures are not in these dates:** Beartooth's 2022 floods and
  2023 opening-day storm, Glacier's September fire closures, and Chinook's 2019
  temporary closing. No margin removes them. They are a floor under P0–P2 that
  only P5 shortens.

---

## Q3: what a wrong "open" costs the driver

**Method:** for each named road, both ways, on its two shoulder days (the first
and last day our effective window calls open), the trip was planned through
`_route`. The driver is put at the first edge of the closed road on the planned
scenic route, the way the route arrived (trap 4: the window's first edge, not
the nearest junction). They turn round, 30 m back, facing away. Then:

- **The truth, and P5:** the road is closed for the reroute
  (`harness.set_avoid`). The reply is what they must drive.
- **P0 replay:** the reroutes the app gets today, asked along that way out at
  30 m and 1, 2, 5, 10, 20, 40 and 80 km, and just past the junction where it
  leaves the approach. Each is asked plain, and again with `declined_uturn` when
  the reply turns them round.

The same was run for the 8 most-used seasonal stretches from Q1, and for every
one of Q1's 155 trips that uses a seasonal edge (detour only).
Files: `q3_cases*.csv` and `q3_reroutes*.csv`.

| road | (b) detour, min / km | (c) backtrack, km | (a) P0 still sends them back past the junction | P0 stops pointing back after |
|---|---:|---:|---|---|
| Baxter Tote Road | 308 / 232 | 1.3 | always | never (>80 km) |
| Beartooth | 228 / 246 | 8.0 | always | never (>80 km) |
| Tioga | 210 / 271 | 9.7 | always | never (>80 km) |
| Chinook | 184 / 175 | **52.0** | always | never (>80 km) |
| Independence Pass | 178 / 174 | 9.5 | always | never (>80 km) |
| Trail Ridge | 151 / 151 | 3.9 | always | never (>80 km) |
| Ebbetts | 144 / 141 | 4.0 | always | never (>80 km) |
| Stevens Canyon | 66 / 57 | 3.6 | always | 40 km |
| Evans Notch | 50 / 49 | 3.8 | always | 40 km |
| Dunraven | 48 / 56 | 2.1 | always | 20 km |
| VT 108 | 39 / 33 | 11.1 | always | 20 km |
| Lincoln Gap | 36 / 39 | 5.4 | always | 20 km |
| Crater Lake | 33 / 51 | 2.2 | always | never (>80 km) |
| Jefferson Notch | 20 / 24 | 3.3 | no | 5 km |
| Going-to-the-Sun | 18 / 74 | 8.1 | half the cases | 20 km |
| Hurricane Mtn Road | 14 / 25 | 2.4 | always | 20 km |
| Lassen | 11 / −8 | 7.0 | always | 20 km |
| Sunrise, Mt Blue Sky, Mt Washington, Kelley Stand, Sonora (one way) | the round trip to the gate: 5–128 min | 4–53 | dead end: no way on | — |

The per-trip detours (Q4's D) sit under the table:

| sample | trips | median detour | p90 detour | median backtrack | p90 backtrack | no way on |
|---|---:|---:|---:|---:|---:|---:|
| `near` | 97 | 46 min | 187 min | 1.9 km | **64.8 km** | 41 |
| `us` | 9 | 18 min | 134 min | 0.4 km | 9.2 km | 0 |

**The hypothesis in mechanism item 5 holds.** Of 728 P0 reroutes, 81% send the
driver back into the closed road:

| distance from the gate | share sending them back |
|---|---:|
| 0–7 km | 93–95% |
| 7–15 km | 84% |
| 15–30 km | 63% |
| 30–60 km | 53% |
| 60–100 km | 48% |

**What would kill it** (the brief's test) is a reroute from just past the
turnaround that already avoids the road. That happens in 7% of cases.
`declined_uturn` cannot help. Its keep-ahead closes only the 40 m strip behind
the driver for a kilometre (`TURN_BACK_WITHIN_M`), and past the 15-minute cap
(`TURN_BACK_CAP_MIN`) it hands back the U-turn. In 89% of the replies asked
with it, the route loops back to the closed road.

**P0's extra cost.** Turning back costs nothing extra until the junction where
the way out leaves the approach, because the driver has to drive there anyway.
Past it, a driver who follows the app misses the turn. I charge them the drive
out to where the app stops pointing back, and back again, capped at the 80 km
asked. The median across the 89 replayed cases is **34.7 minutes**. This is a
model of a driver who trusts the app, and it is the part P5 removes. A driver
who ignores the app pays nothing extra, but is still told for up to 80 km to go
back to a shut road.

---

## Q4: the policies

`tools/seasonal_risk/q4_policies.py` works offline on the measured CSVs.

**Driving a seasonal road.** Each trip drives its all-open route on any day
every seasonal edge on it is open under the policy. Otherwise it takes its ban
route. This agrees with the server's own P0 routes on 155 of 155 seasonal trips
on all three dates (`q4_validation.csv`).

**The chance a road is shut although we say open.** Per edge and day, this is
the share of Q2 road-seasons whose miss exceeds that day's distance from our P0
window end. The curve is the one for the source that sets that end, and the
highest edge on the trip counts. A margin moves the days we call open. A
narrowed window opens days before our P0 end, which carry the higher
P(miss > −k).

**What being stranded costs.** It is the trip's measured Q3 detour, plus P0's
34.7 pointed-back minutes unless P5 is on.

**The two measures.** Stranded minutes are the expectation per 1,000 trips,
spread over the year. Scenery kept is the beautiful km driven on seasonal
edges, over P0's.

| policy | stranded `us` | `near` | `ne` | `named` | scenery kept, worst sample | certain minutes added, `near` |
|---|---:|---:|---:|---:|---:|---:|
| **P0** today | 37.6 | 1,474 | 7.3 | 3,842 | 100% | 0 |
| P0 + P5 | 10.1 | 1,051 | 3.4 | 2,864 | 100% | 0 |
| **P1** ban | 0 | 0 | 0 | 0 | **0%** | **+4,048, and 145 failed trips** |
| P2 all ±7 d | 26.0 | 1,101 | 3.1 | 2,850 | 88.6% | +297 |
| P2 all ±14 d | 17.6 | 811 | 0.6 | 2,079 | 77.2% | — |
| P2 all ±30 d | 7.4 | 397 | 0 | 1,005 | 51.2% | +1,273 |
| P2 guessed-only ±7 d, + P5 | 5.8 | 809 | 1.5 | 2,236 | 92.4% | — |
| P3 price ×10, + P5 | 9.7 | 674 | 0.5 | 2,415 | 87.5% | — |
| **recommended, no P5** | 22.0 | 684 | 7.3 | 2,123 | 91.2% | +502 |
| **recommended + P5** | **6.5** | **489** | **3.4** | **1,582** | **91.2%** | +502 |

All 166 policies, each with and without P5, are in `q4_frontier.csv`. The table
above is drawn from `q4_candidates.csv`.

**P5** cuts stranding by more than the 20% tie band in every sample with
seasonal trips (−29% `near`, −25% `named`, −70% `us`), so the no-UI tie rule
does not drop it. **P3** changes little, because the alternative costs far more
than the expected stranding. That is the quantitative answer to "is it worth
the risk": on expectation, nearly always. **P4**'s notice, within 14 days of a
window under the recommended policy, would show on 1.1 trips per 1,000 (`us`)
and 17.9 per 1,000 (`near`).

**Which windows strand drivers today** (`q4_attribution.csv`): most of P0's
stranding comes from `WINTER`-default ends (1,343 of 1,474 in `near`). MVUM
dates come second (159), then the hand table (19) and OSM dated (9).

### The frontier

The best combination at each scenery bar: the lowest `near` stranding among
policies that clear the bar in all four samples (`q4_choose.py`,
`q4_choice.csv`). The bar is the owner's to move.

| bar | without P5 | with P5 | stranded `near` / `named` (with P5) |
|---|---|---|---:|
| 80% | default 14/45, dated ±14, table ±7, unknown+agency ±14 | the same + P5 | 320 / 928 |
| **90%** | default 0/45, unknown+agency ±7 | **the same + P5** | **489 / 1,582** |
| 95% | default 0/30 | the same + P5 | 699 / 1,982 |

The default margin is written as autumn/spring days. **I would choose the 90%
row**. At 80% the hand table takes a margin it does not need, and North Cascades
and Crater Lake lose more weeks. At 95% `WINTER`'s spring end stays 15 days too
optimistic for the passes it covers.

### Sensitivities

**With the milder pooled curve for `WINTER`** (`--default-curve pooled`,
`q4_*_pooled.csv`), every number falls three- to five-fold: P0 is 290 (`near`),
13.3 (`us`) and 761 (`named`). The best at 90% becomes default 0/14, dated ±7, unknown+agency ±14,
plus P5, at 75 (`near`). The recommendation scores 103 there, 37% behind. That
best scores 720 on the high-pass curve, 47% behind the recommendation's 489. So
the recommendation has the smaller worst case of the two. The shape, margins on
the guessed ends only plus P5, is the same under both curves. Only the size of
`WINTER`'s spring margin depends on which curve is right, and Q2 cannot settle
that for low roads.

**Counting the certain minutes too.** The brief's rule counts only stranded
minutes. Margins also add certain minutes, sending drivers round on days the
road was open. Weighing a stranded minute as w ordinary minutes, the total per
1,000 trips is:

| w | P0 + P5 (`near` / `named`) | recommended + P5 (`near` / `named`) | ban |
|---:|---|---|---|
| 1 | 1,051 / 2,864 | 991 / 4,244 | 4,048 / 22,625 + failed trips |
| 2 | 2,102 / 5,728 | 1,480 / 5,825 | unchanged |
| 4 | 4,204 / 11,456 | 2,458 / 8,988 | unchanged |

Once a stranded minute in the middle of nowhere counts at least twice an
ordinary minute, the recommendation is best or tied in every sample. If the
owner counts all minutes alike, P5 alone (P0 + P5) is the pick on the named
roads.

---

## Defects found (data, not policy)

These are outside P0–P5. Each one is a window wrong by weeks on a famous road,
and each would be its own small fix in the build.

1. **North Cascades is shut from October 1 to June 30.** One 30 m edge of
   "Highway 20" carries an NPS `USFS SEASONAL=Yes` row, so `UNKNOWN_SEASON`
   applies. The table's path (`north_cascades`) does not cover it. The road
   really opens mid-April to May and closes in November or December (WSDOT,
   2010–2026). That loses a median 57 days each spring and 50 each autumn. It is
   safe, but it costs one of the country's best drives about a third of its
   season. **Fix:** let a table road's window take the unknown rows on its own
   path's neighbours, or extend the waypoints.
2. **Crater Lake's park window (Oct 15–Jul 31) shuts the West Rim to August 1.**
   It opened a median 53 days earlier, by Jun 9. It also closes East Rim later
   than it shut in 4 of 13 autumns, by up to 14 days (Oct 1, 2013). The
   description is read at its longer ends, which is wrong in both directions.
   The two halves need their own windows.
3. **Going-to-the-Sun's OSM `Oct-Jun` closes Logan Pass on October 1.** It was
   shut earlier in 7 of 13 years (Sep 3–29), from fire, construction and early
   snow. It opened after July 1 in 4 of 13 years. A table row from the NPS
   Logan Pass record would replace a guess with a measurement.
4. **Lassen's ten-season-longest rule keeps the road shut to July 26.** It
   opened a median 53 days earlier. This is the bias trap 5 names, measured. The
   hand table's spring ends could be narrowed to its median: −7/−14 days costs
   +20% stranding on the named roads and buys back 1–6 points of scenery
   (`P2 tuned` rows in `q4_frontier.csv`). It is a judgement for the owner, and
   not part of the recommendation.

---

## What the data swap could move

All numbers are on the pre-decisions `processed-us` and `pack-us`.
- **Trail Ridge:** today the permit rule closes it all year. This study lifted
  that rule in memory, as the brief directs, so Trail Ridge is already measured
  open in season. Nothing moves when D-decisions open it.
- **D5's 243.7 km of forest road that no car may use:** it is open here. It is
  MVUM forest road, so after the swap some `near` trips lose a seasonal forest
  road they use now. MVUM's share of stranding (159 of 1,474 in `near`) and
  `near`'s usage can only fall. Neither the named-road results nor the choice of
  margins depends on it.
- **Any window the six-decisions unit rewrote** in `closures.py` or
  `winter_closures.py` changes Q2's "set by" column for that road. Q2's
  published dates and Q3's detours do not change.

To refresh: rerun `q1_routes.py`, `q3_turnaround.py --cases named|top|trips`,
`q2_windows.py` and `q4_policies.py` (both curves) on the swapped data. The
national steps take about 40 minutes.

## Limits

- **The `us` sample is thin:** 9 of 273 trips touch a seasonal road. The rule is
  decided on `near` and checked on all four samples.
- **The model is simple.** A trip whose seasonal edge closes takes its ban route
  for the day, and its risk is its highest edge, not the edges combined. Risk is
  per day of year with trips spread evenly. Real traffic peaks in summer, when
  the risk is lowest, so the absolute stranding is likely overstated. The
  comparison between policies is not.
- **P0's extra minutes model a driver who follows the app.** With a driver who
  ignores it, P5's minutes benefit is zero, but the app's wrong guidance for up
  to 80 km is not.
- **Two P5 reroutes of 99 still entered a closed edge.** Both are one
  most-used stretch (`top:3852782`) asked on two days, and its trip starts on
  the closed stretch itself (0 km approach). A moving car is routed off the road
  under it forward (`Router.snap`), so it drives the start of that road
  whatever is closed. 20 of the 99 found no way on (404): the dead ends.
