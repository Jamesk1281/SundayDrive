# New kinds of scenery for a national score: verdict

**Status:** measured 2026-10-21/22 against `usa` at `de43cb4`, on branch
`claude/national-scenery-types`. Nothing under `pipeline/`, `server/`, `ios/` or `data/`
changed. Every figure comes from a script in [`tools/scenery_types/`](../tools/scenery_types/README.md)
and its output in `tools/scenery_types/results/`, unless the text says otherwise. It answers
`docs/national-scenery-types-brief.md`, "the brief" below, which is deleted when this merges.
What ships is the owner's call. This recommends and builds nothing.

## The verdict

**Three small terms pass every check. None of them fixes the West's flat, dry ceiling.
Nothing that passes can.**

Ranked:

1. **Ship V + S2 + L together, in one rebuild.** It passes all three checks:
   - **New England is unharmed:**
     - 2.52% of its km move by more than 0.25 (the limit is 3%);
     - the Oct holdout goes 0.773 → 0.780, with a paired 90% interval of −0.003 to +0.017;
     - all 151 marks: 0.721 → 0.721.
   - **The icons rise and the controls don't:**
     - icon km at 7 or more go from 37.6% to 42.4%;
     - control km at 7 or more stay at 0.04%;
     - the worst control mean is US 6 Delta–Eureka, at 3.66.
   - **The byway proxy within ecoregion improves:** pooled +0.010; Florida +0.016,
     Utah +0.008, Colorado +0.002, New England +0.001.

   The three terms:
   - **V, distant relief.** Open land credits mountains up to 10 km away, in the
     mountain-scale terrain slot (`c_grand`) via `max()`, with `c_grand`'s own 300 m start
     and 900 m full. Death Valley's CA 190 goes from 34% to 78% of its km at 7 or more,
     UT 12 from 37% to 47%, UT 128 from 65% to 72%, and Valley of Fire from 22% to 36%.
   - **S2, the sea as water where the road is on it.** It uses water's own 120 m / 350 m
     curve, and applies only where at least half the ~1 km box is water. The Overseas
     Highway goes from 16% to 32% of its km at 7 or more, and NC 12 from 53% to 58%.
   - **L, landmark credit within 80 m.** This repairs a PAD-US defect (§5). With V,
     CA 190 reaches 96%. The Tamiami Trail moves 3.9 → 4.7.
2. **Of the three, S2 is the safest alone.** It moves 0.23% of New England's km, changes no
   mark, passes at every threshold swept (35%, 50% and 65% water), and costs seconds.
   **V is the most valuable alone, with the least headroom.** Every more generous setting
   fails New England (§4).
3. **S1, the sea as water everywhere within 350 m, passes but is not recommended over S2.**
   It turns every shore road into a double credit (coast 0.13 plus water 0.22, about +2
   points):
   - 2.28% of New England's km move;
   - in Florida, 50% of the km it moves are urban or motorway, against 23% for S2.
4. **W (wetland and mangrove), R (rock texture) and P (prairie and pastoral) should not
   ship.**
   - **W and R pass the letter of the checks and buy nothing.** Icon km at 7 or more rise
     by 0.05 points. The Tamiami Trail, W's target, rises 3.9 → 4.5 (4.6 under W2) and
     gains no km at 7 or more. The Badlands, R's target, stays at 0%.
   - **P fails.** Its holdout interval falls to −0.007, it lowers the Colorado and Utah
     byway proxies, and none of the three prairie icons moves. This confirms the national
     scoring verdict's §8.
5. **The composites fail New England.** All three move too much of it: C-slots 4.19%,
   C-max 3.19%, C-add 5.19%.

**The escape hatch, stated plainly:** five pinned icons stay below 7 under every passing
candidate:

- Monument Valley (5.5 at best);
- the Tamiami Trail through Big Cypress (4.7);
- the Badlands Loop (4.9);
- the Natchez Trace (5.2);
- the Hill Country RMs (5.3).

The three prairie byways also stay below 7: Flint Hills 3.9, the Sandhills 1.9, the
Palouse 3.2.

These roads lack the raw score for 7 by +0.09 to +0.43. The dull controls lack similar
amounts: US 6 +0.32, Bell Road +0.29, Westheimer +0.30. No land-cover or terrain term
can tell them apart (§6). What could is designation data, or Western marks.

## 1. The pinned roads under S0

Every road in the brief's two lists is pinned to OSM way ids and bounded to its named
stretch (`results/pins.csv`, 8,420 ways). The pins were committed in `3db69d5` before any
candidate was computed, and the candidates in `87451e9` before any feature was. Two
changes came after those commits, both before any score was produced:

- the Tioga Road's ref fix (its ways inside Yosemite carry the name, not `CA 120`);
- P's sweep range, which had to fit inside capped `c_relief`.

Candidate L and the combinations were added in `a9f48d9`, after the S0 breakdown and before
they were scored. S2's threshold sweep was added after the first run (§4).

The brief's substring table was contaminated, as it warned:

- The Tamiami Trail's 579 km (4.92) included urban US 41. Its Big Cypress stretch is 59 km
  at **3.92**, with 4% of km at 7 or more.
- US 163 is 5.18 on the pinned 74 km, against 5.24 on 104 km.

S0 below is the shipped E1 score. Contributions are weight × component, length-weighted;
"raw for 7" is the raw score that road's class adjustment needs to reach 7.

| road | km | score | km ≥ 7 | forest/desert | water | coast | relief | grand | curves | protected | byway | raw | raw for 7 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **icons** | | | | | | | | | | | | | |
| US 163 Monument Valley | 74 | 5.18 | 5% | 0.176 | 0.021 | 0 | 0.058 | 0.003 | 0.014 | 0 | 0.036 | 0.322 | 0.474 |
| Valley of Fire | 38 | 5.93 | 22% | 0.178 | 0 | 0 | 0.086 | 0.007 | 0.042 | 0.034 | 0 | 0.351 | 0.440 |
| Overseas Highway | 224 | 5.53 | 16% | 0.080 | 0.059 | 0.127 | 0.013 | 0 | 0.007 | 0.004 | 0.070 | 0.399 | 0.522 |
| Tamiami, Big Cypress | 59 | 3.92 | 4% | 0.106 | 0.038 | 0 | 0.002 | 0 | 0.001 | 0.005 | 0 | 0.217 | 0.474 |
| Badlands Loop SD 240 | 59 | 4.88 | 0% | 0.093 | 0 | 0 | 0.078 | 0 | 0.053 | 0.053 | 0 | 0.297 | 0.474 |
| Needles Highway | 22 | 8.76 | 100% | 0.160 | 0.006 | 0 | 0.143 | 0.004 | 0.118 | 0.070 | 0.070 | 0.590 | 0.440 |
| Million Dollar Hwy | 41 | 8.42 | 90% | 0.125 | 0.158 | 0 | 0.159 | 0.093 | 0.085 | 0 | 0 | 0.644 | 0.524 |
| UT 12 | 199 | 6.23 | 37% | 0.102 | 0.021 | 0 | 0.124 | 0.009 | 0.047 | 0.021 | 0.070 | 0.409 | 0.474 |
| UT 128 | 72 | 7.49 | 65% | 0.116 | 0.130 | 0 | 0.110 | 0.012 | 0.038 | 0 | 0.070 | 0.481 | 0.440 |
| Zion–Mt Carmel UT 9 | 32 | 5.62 | 31% | 0.084 | 0.003 | 0 | 0.128 | 0.020 | 0.050 | 0.028 | 0 | 0.326 | 0.440 |
| CA 190 Death Valley | 156 | 6.64 | 34% | 0.165 | 0 | 0 | 0.084 | 0.012 | 0.030 | 0.058 | 0.070 | 0.428 | 0.457 |
| CA 1 Big Sur | 121 | 9.10 | 98% | 0.113 | 0.020 | 0.116 | 0.159 | 0.059 | 0.074 | 0.006 | 0.070 | 0.661 | 0.474 |
| Tioga Road | 78 | 8.68 | 100% | 0.163 | 0.022 | 0 | 0.149 | 0.030 | 0.066 | 0.067 | 0.070 | 0.586 | 0.440 |
| Historic Columbia River Hwy | 38 | 8.64 | 84% | 0.157 | 0.088 | 0 | 0.138 | 0.026 | 0.072 | 0.055 | 0.003 | 0.589 | 0.440 |
| Chuckanut Drive | 34 | 6.83 | 49% | 0.104 | 0.088 | 0.074 | 0.081 | 0.014 | 0.037 | 0 | 0 | 0.473 | 0.440 |
| Beartooth US 212 | 110 | 8.20 | 87% | 0.129 | 0.079 | 0 | 0.144 | 0.045 | 0.069 | 0 | 0.070 | 0.547 | 0.441 |
| Blue Ridge Parkway | 682 | 7.99 | 83% | 0.170 | 0.004 | 0 | 0.145 | 0.029 | 0.083 | 0 | 0.070 | 0.523 | 0.440 |
| Skyline Drive | 170 | 9.33 | 100% | 0.178 | 0 | 0 | 0.159 | 0.038 | 0.093 | 0.070 | 0.070 | 0.635 | 0.440 |
| Cherohala Skyway | 67 | 8.66 | 99% | 0.171 | 0.028 | 0 | 0.156 | 0.033 | 0.105 | 0 | 0.068 | 0.584 | 0.440 |
| Natchez Trace Parkway | 718 | 5.18 | 4% | 0.160 | 0.016 | 0 | 0.044 | 0 | 0.020 | 0 | 0.070 | 0.322 | 0.474 |
| NC 12 Outer Banks | 176 | 6.91 | 53% | 0.074 | 0.113 | 0.129 | 0.011 | 0 | 0.019 | 0.026 | 0.047 | 0.462 | 0.469 |
| Hill Country RM 335/336/337 | 181 | 5.28 | 13% | 0.053 | 0.071 | 0 | 0.116 | 0 | 0.051 | 0 | 0 | 0.297 | 0.440 |
| Flint Hills K-177 | 78 | 3.88 | 2% | 0.040 | 0.020 | 0 | 0.038 | 0 | 0.012 | 0 | 0 | 0.180 | 0.440 |
| Sandhills NE 2 | 455 | 1.89 | 0% | 0.007 | 0.027 | 0 | 0.037 | 0 | 0.009 | 0 | 0 | 0.097 | 0.523 |
| Palouse Scenic Byway | 341 | 3.21 | 2% | 0.009 | 0.012 | 0 | 0.071 | 0 | 0.029 | 0 | 0 | 0.158 | 0.474 |
| **dull controls** | | | | | | | | | | | | | |
| I-15 Barstow–Primm | 366 | 0.28 | 0% | 0.160 | 0.003 | 0 | 0.056 | 0.003 | 0.003 | 0 | 0 | 0.239 | 0.815 |
| I-10 Tonopah–Quartzsite | 247 | 0.14 | 0% | 0.156 | 0.015 | 0 | 0.027 | 0.001 | 0.002 | 0 | 0 | 0.207 | 0.815 |
| US 6 Delta–Eureka | 87 | 3.11 | 1% | 0.052 | 0.006 | 0 | 0.045 | 0.003 | 0.005 | 0 | 0 | 0.127 | 0.451 |
| I-40 Amarillo | 51 | 0.07 | 0% | 0.016 | 0.020 | 0 | 0.012 | 0 | 0.007 | 0 | 0 | 0.147 | 0.815 |
| I-80 Grand Island–N. Platte | 444 | 0.11 | 0% | 0.039 | 0.122 | 0 | 0.007 | 0 | 0.003 | 0 | 0 | 0.196 | 0.815 |
| I-70 east of Denver | 519 | 0.00 | 0% | 0.002 | 0.004 | 0 | 0.025 | 0 | 0.003 | 0 | 0 | 0.071 | 0.815 |
| US 287 Colorado plains | 335 | 1.60 | 0% | 0.008 | 0.015 | 0 | 0.020 | 0 | 0.004 | 0 | 0 | 0.072 | 0.522 |
| I-75 Ocala–Tampa | 294 | 0.17 | 0% | 0.082 | 0.037 | 0 | 0.017 | 0 | 0.005 | 0 | 0 | 0.196 | 0.815 |
| I-4 Orlando | 67 | 0.19 | 0% | 0.013 | 0.096 | 0 | 0.010 | 0 | 0.009 | 0 | 0 | 0.193 | 0.815 |
| Bell Road, Phoenix | 109 | 3.52 | 0% | 0.036 | 0.012 | 0 | 0.013 | 0 | 0.001 | 0 | 0 | 0.180 | 0.470 |
| Westheimer, Houston | 57 | 3.42 | 0% | 0.011 | 0.039 | 0 | 0.006 | 0 | 0.005 | 0 | 0 | 0.176 | 0.474 |
| I-95 NJ Turnpike | 353 | 0.18 | 0% | 0.052 | 0.048 | 0.011 | 0.020 | 0 | 0.004 | 0 | 0 | 0.183 | 0.815 |
| I-635 LBJ | 109 | 0.15 | 0% | 0.017 | 0.034 | 0 | 0.024 | 0 | 0.006 | 0 | 0 | 0.167 | 0.815 |

Pooled, 37.6% of icon km and 0.04% of control km are at 7 or more under S0. Every control
mean is under 4 already. **The interstates are protected by the motorway class adjustment,
not by scenery.** I-15 has more distant relief than US 163 (§3). A motorway needs raw 0.815
for 7, so a scenery term would have to add about +0.6 to promote one. The controls that
test a candidate are the non-motorway ones: US 6, US 287, Bell Road and Westheimer.

## 2. What each mechanism turned out to be

The brief's five mechanisms, checked:

1. **Distant relief is real, but it does not separate Monument Valley from the dull
   desert.** Mean prominence within 10 km is:
   - US 163: 504 m;
   - I-15: 727 m;
   - I-10: 578 m;
   - US 6: 571 m.

   V adds +0.35 to US 163, and +0.55 to US 6. The brief's kill test was an open-land
   prominence term that "doesn't lift US 163 above the dull desert controls". On
   Monument Valley, that is what happened. US 163 stays above US 6 (5.5 against 3.7),
   but because of its desert land cover (0.176 against 0.052) and its byway tag, not
   because of V. V works where the relief is bigger:
   Death Valley's 1,376 m, Valley of Fire's 623 m, and UT 12 and UT 128's 760–770 m.
2. **The ceiling is binding**, and it is measured in the "raw for 7" column above. A road
   with no water and no curves sits 0.09–0.43 short of 7. The best a passing candidate
   adds to such a road is about 0.07 (V's 0.10 slot, times its openness and prominence).
3. **The open sea is not a water polygon. Confirmed.** Within 350 m of the Overseas
   Highway, OSM's water polygons are:
   - unnamed ponds and lagoons: 68 of 224 km;
   - canals: 24 km;
   - lakes: 4 km;
   - bays: 1.5 km.

   The sea itself never appears, though 1,202 of the road's 1,337 pieces (90%) lie
   within 350 m of the coastline.
4. **Wetland and mangrove are unread, and reading them changes nothing.** The Tamiami's
   1 km box is 79% wetland. Its forest slot already holds 0.59 of 1, so `max()` adds
   about 0.04 of raw (+0.5 points, to 4.5), and the road needs +0.26.
5. **The breakdown types are New England's:** §8.

## 3. V: a prominence proxy, checked against a true viewshed

V is a **prominence proxy**: the highest despiked elevation within a 10 km half-side
square, minus the road's own. It is credited by open land: everything WorldCover shows
that is not tree, built or mangrove, within ~1 km.

`viewshed.py` checked the proxy against a true viewshed on all 26,325 icon and control
pieces: 72 rays, an eye 1.5 m up, out to the same radius.

- **The two agree:** piece-level r = 0.92.
- **The viewshed is slightly less generous:**
  - icon km at 7 or more: 39.6% under the viewshed, 40.1% under the proxy;
  - Monument Valley: 7.3% under the viewshed, 9.4% under the proxy;
  - controls: 0.04% under both.
- **Cost:** the viewshed took 10.2 ms a piece. The national network is about 52 million
  pieces (Florida's 6.6 a km, times 7.80 million km), so about **146 CPU-hours**. The
  proxy's 10 km maximum filter took **2.8 s** on Colorado's 83-megapixel mosaic, against
  4.9 s for `terrain.py`'s existing 3 km range: about two minutes nationally.

The viewshed buys nothing the proxy misses. Use the proxy.

## 4. The three checks, and the sweeps

Check 1 is New England: the holdout's paired 90% lower bound at least −0.005, and at most
3% of km moving by more than 0.25. Check 2 is the icons and controls. Check 3 is the
pooled byway proxy within ecoregion, no worse than −0.005. The byway columns are each
region's FHWA scenic/natural AUC within ecoregion on trunk–tertiary, with the byway term
removed (`results/byway_proxy.csv`). S0's are New England 0.574, Colorado 0.595,
Utah 0.489, Florida 0.614, pooled 0.558.

| candidate | NE km moved | marks moved | Oct holdout (Δ, 90% low) | icons km ≥ 7 | controls km ≥ 7 | worst control mean | proxy pooled Δ | FL | UT | CO | 1 | 2 | 3 |
|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|:-:|:-:|:-:|
| S0 shipped E1 | — | — | 0.773 | 37.6% | 0.04% | 3.52 Bell Rd | — | — | — | — | | | |
| V (R10, 300–900 m, grand slot) | 1.85% | 3 | 0.775 (+0.002, −0.003) | 40.1% | 0.04% | 3.66 US 6 | +0.003 | +0.000 | +0.009 | −0.002 | ✓ | ✓ | ✓ |
| V-add (own term, 0.10) | 2.04% | 4 | 0.776 (+0.003, +0.000) | 40.3% | 0.05% | 3.69 US 6 | +0.006 | +0.000 | +0.013 | +0.006 | ✓ | ✓ | ✓ |
| S1 sea as water | 2.28% | 0 | 0.773 (+0.000, +0.000) | 39.8% | 0.04% | 3.52 Bell Rd | +0.013 | +0.035 | 0 | 0 | ✓ | ✓ | ✓ |
| S2 sea as water, on the sea | 0.23% | 0 | 0.773 (+0.000, +0.000) | 38.7% | 0.04% | 3.52 Bell Rd | +0.002 | +0.006 | 0 | 0 | ✓ | ✓ | ✓ |
| W1 wetland, forest slot | 0.08% | 0 | 0.773 (+0.000, +0.000) | 37.6% | 0.04% | 3.52 Bell Rd | −0.000 | −0.001 | 0 | 0 | ✓ | (✓) | ✓ |
| W2 wetland, mid water | 0.06% | 0 | 0.773 (+0.000, +0.000) | 37.6% | 0.04% | 3.52 Bell Rd | +0.000 | +0.001 | 0 | 0 | ✓ | (✓) | ✓ |
| R rock texture | 0.00% | 0 | 0.773 (+0.000, +0.000) | 37.6% | 0.04% | 3.52 Bell Rd | −0.000 | 0 | −0.001 | 0 | ✓ | (✓) | ✓ |
| P pastoral | 1.90% | 1 | 0.774 (+0.001, **−0.007**) | 37.7% | 0.04% | 3.52 Bell Rd | −0.004 | 0 | −0.006 | −0.009 | ✗ | (✓) | ✓ |
| L landmark within 80 m | 0.45% | 5 | 0.778 (+0.005, +0.000) | 37.9% | 0.04% | 3.52 Bell Rd | +0.005 | +0.011 | 0 | +0.004 | ✓ | ✓ | ✓ |
| C-slots S1+W1+V+R | **4.19%** | 3 | 0.775 (+0.002, −0.003) | 43.0% | 0.04% | 3.67 US 6 | +0.016 | +0.035 | +0.008 | −0.002 | ✗ | ✓ | ✓ |
| C-max one landscape slot + S1 | **3.19%** | 1 | 0.776 (+0.003, +0.000) | 40.4% | 0.04% | 3.83 US 6 | +0.009 | +0.035 | −0.006 | −0.005 | ✗ | ✓ | ✓ |
| C-add separate terms + S1 | **5.19%** | 8 | 0.776 (+0.003, +0.002) | 44.9% | 0.05% | 3.71 US 6 | +0.021 | +0.038 | +0.015 | +0.007 | ✗ | ✓ | ✓ |
| V+S1 | **4.12%** | 3 | 0.775 (+0.002, −0.003) | 42.3% | 0.04% | 3.66 US 6 | +0.016 | +0.035 | +0.009 | −0.002 | ✗ | ✓ | ✓ |
| V+S2 | 2.08% | 3 | 0.775 (+0.002, −0.003) | 41.2% | 0.04% | 3.66 US 6 | +0.005 | +0.006 | +0.009 | −0.002 | ✓ | ✓ | ✓ |
| **V+S2+L** | 2.52% | 8 | 0.780 (+0.008, −0.003) | 42.4% | 0.04% | 3.66 US 6 | +0.010 | +0.016 | +0.009 | +0.002 | ✓ | ✓ | ✓ |
| V+S1+L | **4.55%** | 8 | 0.780 (+0.008, −0.003) | 43.7% | 0.04% | 3.66 US 6 | +0.020 | +0.044 | +0.009 | +0.002 | ✗ | ✓ | ✓ |

(✓) means the candidate passes the letter of check 2 on a rise of 0.2 points or less.

**The marks check is weak evidence for most of these.** Of the 151 marks, S1, S2, W and
R move none by more than 0.25; V moves 3, L 5 and V+S2+L 8. For S, W and R, New England's
check rests on km moved alone. All 151 marks stay at 0.720–0.722 under every candidate.
The share of marks at 7 or more that were liked moves from 96.2% (53 marks) to 94.6%
(56) under V+S2+L.

**Sweeps.** Each constant was moved around its hand-set value, with the others held.

| sweep | NE km moved | Oct 90% low | icons km ≥ 7 | worst control | proxy pooled Δ | passes |
|---|---:|---:|---:|---|---:|:-:|
| V R5, 150–450 m | 3.66% | +0.004 | 39.9% | 3.72 | +0.003 | ✗ |
| V R5, 300–900 m | 0.36% | +0.000 | 38.7% | 3.54 | +0.001 | ✓ |
| V R5, 450–1350 m | 0.01% | +0.000 | 38.4% | 3.53 | +0.000 | ✓ |
| V R10, 150–450 m | 7.63% | −0.006 | 40.7% | 3.95 | +0.002 | ✗ |
| **V R10, 300–900 m** | 1.85% | −0.003 | 40.1% | 3.66 | +0.003 | ✓ |
| V R10, 450–1350 m | 0.25% | +0.000 | 39.7% | 3.54 | +0.001 | ✓ |
| V R15, 150–450 m | 10.36% | −0.014 | 40.8% | **4.12** | −0.001 | ✗ |
| V R15, 300–900 m | 3.46% | −0.004 | 40.5% | 3.94 | +0.004 | ✗ |
| V R15, 450–1350 m | 0.83% | −0.004 | 40.0% | 3.57 | +0.003 | ✓ |
| V-add 0.05 / **0.10** / 0.15 / 0.20 | 0.26 / 2.04 / 3.93 / 5.51% | +0.000 each | 38.9 / 40.3 / 41.8 / 42.7% | 3.56 / 3.69 / 3.98 / **4.27** | +0.003 / +0.006 / +0.009 / +0.012 | ✓ ✓ ✗ ✗ |
| S1 distances ×0.5 / **×1** / ×2 | 1.15 / 2.28 / 4.26% | +0.000 | 38.6 / 39.8 / 41.1% | 3.52 | +0.010 / +0.013 / +0.015 | ✓ ✓ ✗ |
| S2 at 35% / **50%** / 65% water | 0.71 / 0.23 / 0.06% | +0.000 | 39.2 / 38.7 / 38.2% | 3.52 | +0.011 / +0.002 / +0.001 | ✓ ✓ ✓ |
| L within 40 / **80** / 200 m | 0.31 / 0.45 / 0.95% | +0.000 | 37.8 / 37.9 / 38.3% | 3.52 | +0.004 / +0.005 / +0.006 | ✓ ✓ ✓ |
| W1 full at 50% / **100%** wet | 0.28 / 0.08% | +0.000 | 37.9 / 37.6% | 3.52 | −0.000 | ✓ ✓ |
| W2 level **0.45** / 1.0 | 0.06 / 0.32% | +0.000 | 37.6 / 37.9% | 3.52 | +0.000 / +0.001 | ✓ ✓ |
| R full at 25 / **38** / 60 m | 0.00% | +0.000 | 37.9 / 37.6 / 37.6% | 3.52 | −0.001 / −0.000 / −0.000 | ✓ ✓ ✗ |
| P rolling at 33 / 50 / **100** m | 5.12 / 4.00 / 1.90% | +0.000 / +0.000 / −0.007 | 38.0 / 37.9 / 37.7% | 3.73 / 3.52 / 3.52 | −0.012 / −0.008 / −0.004 | ✗ ✗ ✗ |

- **None of the recommended terms is a knife-edge at its hand-set value.**
  - S2 and L pass across their whole sweeps.
  - V passes at every setting from its hand-set value to stricter ones.
- **V has no headroom in the generous direction.** Every setting that buys more icon km
  fails New England: a 15 km window, a 150 m start, or a weight of 0.15. At 0.20, or a
  15 km window with a 150 m start, it also takes US 6 over 4.
- **What V moves in New England is open valley road under mountains.** VT 100, VT 30,
  VT 102, US 5 and the Daniel Webster Highway gain +0.36 to +0.52 (`results/movers.csv`).
  The owner can drive those (§9).

## 5. L, this study's own candidate: PAD-US cuts the road out of the park

The S0 breakdown showed the Tamiami Trail with `c_protected` 0.005 of 0.07, though it runs
through Big Cypress National Preserve, which is a landmark. PAD-US's fee polygons exclude
the road right-of-way:

| road | inside a landmark polygon | within 80 m | within 200 m |
|---|---:|---:|---:|
| Tamiami Trail, Big Cypress | 9% | **98%** | 99% |
| Overseas Highway | 20% | 72% | 80% |
| CA 1 Big Sur | 9% | 26% | 58% |
| Badlands Loop | 75% | 75% | 76% |

L credits a landmark within `DIST["green"]`, 80 m: the reach `score.py` already gives
"next to a park". It keeps E1's 30% built-land gate.

- **It passes all three checks, and gives the best holdout of any single term:** +0.005,
  with a 90% interval of +0.000 to +0.011.
- **Its cost is boundary roads.** It credits a road running *along* a park as well as
  through it. In New England that includes 19 km of Route 128 (Yankee Division Highway,
  +0.75) and 6 km of the Mass Pike (+0.84), each starting below 2. In Florida it includes
  Alligator Alley. 9% of the km it moves in New England are motorway or built-up. Nothing
  it moves crosses 7, and the shipped term already credits motorways that run inside a
  park.

## 6. Why the ceiling cannot be raised within these rules

Mechanism 2 is the binding one, and the measurement makes the trade explicit:

- **To reach 7 the low icons need more raw score:**
  - Monument Valley +0.15;
  - the Tamiami Trail +0.26;
  - the Badlands +0.18;
  - the Natchez Trace +0.15;
  - the Hill Country +0.14;
  - Flint Hills +0.26;
  - the Palouse +0.32;
  - the Sandhills +0.43.
- **The non-motorway controls need about as much:** US 6 +0.32, Bell Road +0.29,
  Westheimer +0.30, US 287 +0.45.
- **Any term that adds +0.15 or more to open, dry, flat-ish land also lifts US 6, US 287
  and New England's farm valleys.** That is what C-add does. It is the only candidate that
  lifts the Badlands past a few percent (19%), and it moves 5.19% of New England.
- **A `max()` slot cannot raise the ceiling at all.** C-max moves New England 3.19% and
  adds 2.8 points of icon km, most of them S1's.

What would separate these icons from the controls is not land cover or terrain:

- **Designation the landmark set does not read.** PAD-US files the Blue Ridge and Natchez
  Trace Parkways as `SDA` (Special Designation Area), a type outside `protected.py`'s
  `LANDMARK` set, so both score `c_protected` 0. Monument Valley Navajo Tribal Park is
  not in PAD-US at all (queried 2026-10-22). Adding `SDA` is a candidate for its own
  test. It is not measured here: the brief allowed one own candidate, and `SDA` covers
  far more than parkways.
- **Western marks.** They are the only evidence that could justify more weight mass in
  open land (§9).

## 7. Build cost

V, S2 and L change existing columns (`c_grand`, `c_water`, `c_protected`). They add none,
so `graph_edges.parquet`'s schema and the pack's size do not change. Per stage:

| term | stage | added cost |
|---|---|---|
| V | `terrain.py`: one 10 km maximum filter on the despiked mosaic it already holds; `score.py` samples one more raster | 2.8 s on Colorado (83 Mpx), about 2 min nationally (2.8 Gpx over all rings). A float32 raster on the elevation grid: 0.33 GB uncompressed for Colorado, about 11 GB summed over every ring. It is a per-region intermediate, like `range3k.tif`, so it is deleted at harvest. Peak memory rises by one mosaic-sized float32 array (about 3.6 GB at Montana, the largest), unless the range and the prominence are computed in turn |
| S2 | `landcover.py`: the water share of the ~1 km box it already reads; `score.py`: two more queries on the coastline tree it already builds | seconds a region |
| L | `protected.py`: `dwithin` 80 m instead of `within` | seconds a region |

**The rebuild is the expensive part.** The national build deleted its region
intermediates at harvest, so any score change re-runs every region stage. From the 51
regions' `stages.json`, in process-hours:

| stage | process-hours |
|---|---:|
| extract | 1.99 |
| elevation | 1.00 |
| terrain | 0.77 |
| landcover | 1.52 |
| protected | 0.66 |
| score | 1.54 |
| graph | 3.24 |
| **total** | **10.7** |

The stitch, the sidecars and the pack come on top. On this Mac that is the national
build's own wall time again, roughly a night at two or three regions at once
(`docs/national-build.md`).

A cheaper path exists. Compute the three columns offline at edge level, as this study did,
then re-composite `score` and rebuild only the pack: Florida's 1.76 million pieces took
322 s, so the country would take about 3 hours single-stream. It is not identical to a
pipeline build, because `max()` would apply to edge-averaged components. So the pipeline
remains the clean route, and it should be timed with the next planned rebuild rather than
run on its own.

## 8. Proposed app scenery types

**Keep the six sliders as they are.** Change the breakdown.

| breakdown row | maps to | cut | slider |
|---|---|---|---|
| Forest & parks | the woods half of `c_forest`: 0.5 green + 0.5 tree | 0.25, as now | **Forest, parks & desert** (already the slider's label) |
| Desert & rock | `landcover.py`'s `desert` share | 0.25 | the same slider |
| Water | `c_water`, which with S2 includes the sea under bridges and causeways | 0.4 | Lakes & rivers |
| Coast | `c_coast` | 0.4 | Coast |
| Hills | `c_relief` | 0.4 | Hills |
| Mountains | `c_grand`, which with V includes distant mountains across open land | 0.25 | none: baseline |
| Farmland | `c_farm` | 0.4 | Farmland |
| Town | `c_urban` | 0.4 | Town centers |
| Parks & landmarks | `c_protected` | 0.5 | none: baseline |

Two rows are deliberately left out:

- **Wetland:** W does nothing to the score, and a row for scenery the score does not value
  would mislead.
- **Prairie:** the data points the wrong way (§4, P).

**Why desert stays on forest's slider.** Desert shares forest's slot through `max()`, and
`Router._edge_scores` is linear in its components. A separate desert slider would have to
make desert a term of its own, which adds weight mass to desert land. That is a score
change, the C-add trap, not an app change. Splitting only the breakdown keeps the score
exactly as it is.

**Why Mountains and Parks have no slider.** Moving `c_grand` into `BEAUTY_TYPES` raises
`DEFAULT_WEIGHTS`' mass from 0.89 to 0.99. All-1.0 stays a fixed point, so the stored
`score` column is untouched, but every other slider setting renormalises slightly
differently. That is a small, owner-visible change for a type most km do not have. If the
owner wants a Mountains slider anyway, it is that one move.

What the change touches:

- **`score.py` and `graph.py`:** store the woods and desert halves as two extra chunk and
  edge columns, for the breakdown only. They must not carry a `c_` prefix. `score.py`'s
  blend raises a KeyError on any `c_` column with no `WEIGHTS` entry, and `graph.py`
  re-derives the same blend. Name them `bd_woods` and `bd_desert`, say. The pack grows by
  two coded columns over 25.8 million edges, an estimated 50–100 MB.
- **`router.py`:**
  - `SCENERY_BREAKDOWN` is derived today from `BEAUTY_TYPES`. It would come from its own
    list, with `BREAKDOWN_OVERRIDE` cuts for desert, mountains and parks.
  - `BEAUTY_TYPES`, `DEFAULT_WEIGHTS`, the pack's `comp.{k}` columns and the slider
    renormalisation in `Router._edge_scores` are unchanged.
  - The loader's `_breakdown` stack picks up the new columns from `SCENERY_BREAKDOWN`.
  - `TestBreakdownThreshold` gains the new rows.
- **The API:** `scenery_km` gains the keys `desert & rock`, `mountains` and
  `parks & landmarks`, and `forest/park` stops counting desert. No public app depends on
  the old meaning (the New England app never shipped), so the key can change meaning;
  TestFlight builds simply won't show the new rows.
- **`ios/Sources/Models.swift`:** `RouteProps.sceneryBreakdown`'s `displayOrder` gains the
  three keys.
- **`ios/Sources/BeautyType.swift`:** `forBreakdown` maps them to labels, and `hue(for:)`
  needs three new hues (they would fall back to `.slate`).

## 9. What Western marks would need to test

The marks are New England's, and they see almost none of this: 8 of 151 move under
V+S2+L. What would test each term:

- **V.** Marks on open roads where V moves the score: basin-and-range valleys like US 6
  Delta–Eureka, and Plateau roads like UT 12 and CA 190. Liked and disliked marks are both
  needed inside V's band (prominence above 300 m, open land). About 40 marks where V moves
  the score by more than 0.25 would show whether distant mountains are what a driver
  rates. **Part of it can be tested in New England.** V's largest movers there are
  Vermont valley roads: VT 100, VT 30, VT 102 and US 5. Marks on those, with and without a
  mountain wall in view, would test the term without travel.
- **S2.** Marks on bridges and causeways over the sea (the Keys, the Outer Banks, Tampa
  Bay's causeways). New England has few: Lighthouse Road, Ocean Avenue, Nahant Road,
  Gurnet Road and Hull's Nantasket Avenue are its largest S2 movers.
- **L.** Its risk is testable in New England: marks on the boundary roads it credits
  (its largest movers include Route 128 and the Mass Pike), against roads that run
  through a park.
- **The ceiling.** Marks on Monument Valley-like flat dry roads, and on prairie. If drivers
  like those at the rate they like roads already at 7 or more (96%), the case for more
  weight mass in open land (C-add) is made by marks rather than by the icon list, which
  is the only way it can be made without repeating D1.

Western drives are unlikely at this project's scale, so the New England-testable parts
of V and L are the realistic ones.

## 10. Method notes

- **S0 reproduces the shipped score exactly.** Icon and Florida edges match
  `part_edges.parquet`'s stored `score` to 1e-9. New England's chunk tables reproduce
  E1's built figures: 0.721 / 0.773, 53 marks at 7 or more, 1.28% of km moved.
- **The DEM is the national build's own Terrarium cache,** despiked with
  `terrain.despike`. The despike counts match `terrain.py`'s documented ones: 463 px in
  Colorado, 2 in Utah. Windows are sized at `RELIEF_REF_LAT`, as every pipeline window
  is.
- **Pieces stand in for chunks** where no chunk table survives (icons and Florida): 400 m
  pieces, each piece's raw averaged along the edge, as `graph.py` does. The base
  components are known only per edge, so `max()` there applies to edge averages. That
  slightly understates any `max()` candidate on edges whose components vary along them.
- **The Florida proxy has eight FHWA national byways, five of them scenic or natural,**
  and one of those is the Florida Keys Scenic Highway, which is also an icon. S1 and S2's
  Florida gains are partly that overlap.
- **Region slices only.** The national `graph_edges.parquet` and the pack were never read.
  One region was processed at a time. Peaks: Florida 6.0 GB, New England 4.4 GB, the
  evaluation 1.9 GB.
