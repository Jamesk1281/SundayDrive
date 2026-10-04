# Sunday Drive — the screen, and the rename

**Status: screened and renamed 2026-09-21, against `main` at `3c35b4f`. Nothing
was filed, bought or reserved. The app is now **Sunday Drive** and the bundle
identifier is **`app.sundaydrive`**, changed deliberately while it is still
free to change — it becomes permanent at the first build upload, TestFlight
included, and nothing has been uploaded.**

This reverses the **"blocked, drop it"** verdict in
[`trademark-knockout-findings.md`](trademark-knockout-findings.md) §14. That
section invited it in its own text — *"Stated so it can be overruled, because
the register alone would not support it"* — and three of the four facts it
rested on did not survive re-checking.

**Nobody here is a lawyer and nothing below is legal advice.** This is a
knockout screen, not a clearance search; the distinction is in
`trademark-knockout-findings.md`.

---

## 1. Why §14 was overruled

### 1a. The prior class 9 application died procedurally, over a blocker that is now dead

§14's strongest line was that *"a prior application for this precise product
[was] abandoned for reasons nobody here can determine."* It can be determined.
TSDR's web interface gives both the status and the file.

**Application 77812622** — `SUNDAY DRIVE`, Sunday Drive (LLC, California),
correspondent **Jason Scott, Ventura CA**, filed **2009-08-25** on a **§1(b)
intent-to-use** basis, IC 009, *"App which details iconic 'Sunday Drives'
throughout America."*

> **Status: Abandoned due to incomplete response. The response did not satisfy
> all issues in the Office action.** Status date 2010-08-03; date abandoned
> 2010-06-03.

The prosecution history is a self-represented applicant losing a procedural
exchange: non-final action 2009-12-02 → response 2009-12-03 → **Notice of
Unresponsive Amendment** 2010-01-05 → abandonment 2010-08-03. Not a ruling that
the name is unusable.

**And the mark it was refused over is gone.** The office action's cited
registration, read off the file:

| Cited mark | Owner | Reg. | Class | Goods | Status |
| --- | --- | --- | --- | --- | --- |
| **`SUNDAY DRIVES`** | Make Memories, Inc. (Jacksonville FL) | **3410292** | **042** | *"Providing information in the field of geography and map images via the Internet; customized mapping services for any series of destinations"* | **CANCELLED 2014-11-14** |

That description is very nearly this product. It was live in 2009 and it has
been dead for twelve years. `sundaydrives.com` (registered 2004-03-31) returns
**HTTP 402 — "Store unavailable"**, a shut Shopify store, so the business
behind it appears wound up too. Per Trap 4 of the original screen, cancellation
removes the registration and not whatever rights use created — but there is no
visible use left to create them.

*(The same Jason Scott had an earlier `SUNDAY DRIVE`, app 77191226, IC 016,
newsletters in automobile customer retention, abandoned 2008-08-06. One
individual, two attempts, both procedural failures.)*

### 1b. There is no descriptiveness problem on the record — and this is the contrast that matters

This is the sharpest difference from "Scenic", whose whole case collapsed on
§2(e)(1) (see
[`scenic-name-viability-findings.md`](scenic-name-viability-findings.md) §3).

- **No `SUNDAY DRIVE` mark has ever been refused as merely descriptive.**
- **No `SUNDAY DRIVE` mark disclaims the phrase**, and none sits on the
  Supplemental Register.
- The USPTO has registered it as **inherently distinctive** for beer, a musical
  band, an automobile dealership and trading cards.

Where `SCENIC` is disclaimed 82 times over and refused twice for the applicant
now trying to own it, `SUNDAY DRIVE` is a phrase the register treats as a mark.
**Unlike Scenic, this is a name that could actually be owned** in class 9 —
arbitrary-to-suggestive for routing software rather than descriptive of it.

### 1c. The App Store is empty where it counts — checked with the corrected method

§14 said *"App Store: zero."* Strictly that is wrong, and the correction is
worth recording because it comes from the method fix in
`scenic-name-viability-findings.md` §6: a single `itunes.apple.com/search`
query is relevance-ranked, not an index scan, so it undercounts.

Union over **seven** query terms (`sunday drive`, `sundaydrive`, `sunday
drives`, `sunday driver`, `sunday`, `the sunday drive`, `scenic drive sunday`):

| App | Category | Seller | Released |
| --- | --- | --- | --- |
| Sunday Drive VT | **Lifestyle** | Clover VT LLC | 2025-08-18 |
| Sunday Drive 3D | **Games** | steven schenk | 2025-06-24 |

**Two, not zero — and zero in Navigation or Travel.** Neither is a routing
product. For comparison the same method finds **29** Navigation/Travel apps
carrying "scenic". The category this app ships into is empty of the name.

*(Clover VT LLC's own `S SUNDAY DRIVE` clothing application, 99438887, was
abandoned 2026-06-03.)*

---

## 2. The register, in full

Controls first: `*drive*` → **18,434**, so the machinery was returning results
when these numbers were recorded.

| Query | Hits |
| --- | --- |
| `wordmark:*sundaydrive*` — one word, substring | 1 |
| `wordmark:"SUNDAY DRIVE"` — all classes, all statuses | 11 |
| `wordmark:"SUNDAY DRIVE" AND alive:true` | 6 |
| `wordmark:"SUNDAY DRIVER"` | 11 |
| `wordmark:"SUNDAY DRIVES"` | 1 (cancelled — §1a) |
| `wordmarkPseudoText:"SUNDAY DRIVE"` | **0** |
| `wordmark:(SUNDAY AND DRIVE)` in 9/39/42, any status | **1** *(the 2009 abandonment)* |
| **`wordmark:(SUNDAY AND DRIVE)` live in 9/39/42** | **0** |

**Zero live marks in classes 9, 39 or 42.**

The six live marks, none in this product's classes:

| Mark | Owner | Reg./App | Class | Goods |
| --- | --- | --- | --- | --- |
| `SUNDAY DRIVE` | **Tomlinson, Jr., John D.** | **6979596** | **041** | **Providing entertainment information in the field of automobiles via a global computer network and through online social media platforms; blogs featuring commentary in the fields of automobiles** |
| `SUNDAY DRIVE` | Tomlinson, Jr., John D. | 7214321 | 035, 037 | Automobile dealerships; information about vehicles for sale via the internet; repair and maintenance |
| `SUNDAY DRIVE` | SIRIUS XM RADIO LLC | app 50004613 | 041 | Continuing programs featuring sports, namely football — **filed 2026-07-21** |
| `SUNDAY DRIVE` | Mother Road Brewing | 5998225 | 032 | Beer |
| `SUNDAY DRIVE` | Jeffrey Treece | 3817920 | 041 | Live performances by a musical band |
| `SUNDAY DRIVE CAR CARE` | Sunday Drive, LLC | app 99870115 | 003, 007, 021, 024 | Car washing mitts, microfibre towels |

**One method note worth carrying forward:** `wordmark:(SUNDAY AND DRIVE)` does
**not** match `SUNDAY DRIVES` — the index does not stem, so the plural is a
different token. The cancelled class 42 registration in §1a was invisible to
the query shape §14 used, and only surfaced by reading the cited evidence in
the office action. **Run the plural as its own query.**

---

## 3. Common law and domains

- **`sundaydrive.com` is an operating car dealership** — *"Used Cars, Trucks,
  Vans & SUVs in St. Augustine, FL | Sunday Drive"*, registered 2001-11-26.
  This is Tomlinson, matching the two registrations above.
- `sundaydrives.com` — 2004-03-31, **HTTP 402**, shut Shopify store (§1a).
- `sundaydrive.app` — **registered 2025-01-25**, no nameservers configured,
  serving nothing.
- `thesundaydrive.com` — 2014-09-09, does not resolve.
- `sundaydriveapp.com` — 2025-08-11, does not resolve.
- **Free: `sundaydrive.co` and `sundaydrives.app`.**

**This is the worst domain position of any candidate screened**, and §14 was
right about that. It is the real cost of the name and it does not improve.

---

## 4. The honest weaknesses

1. **Tomlinson reg. 6979596 is the nearest live thing and belongs in front of an
   attorney.** Class 41, *automotive information delivered over a global
   computer network*. It does not cover software, mapping, navigation or
   transport — but a driving app is arguably automotive information delivered
   over a network, and he holds the exact-match `.com` with a live business on
   it.
2. **No exact-match domain, now or plausibly ever.** Shipping on
   `sundaydrive.co` means the dealership outranks the app on searches for its
   own name, permanently.
3. **It is a common phrase.** A brewery, a band, a dealership, SiriusXM, a
   film, a New Zealand car dealer. Crowded fields cut both ways: coexistence is
   already normal, so nobody is likely to come after you — and whatever
   registers would be narrow.
4. **The §2(e)(1) question is untested for *these* goods.** "Sunday drive" is
   the plain English phrase for driving with no destination for pleasure, which
   is precisely what loop mode does. Not descriptive for beer or a band; closer
   to the line for an app whose function it names. Milder than Scenic's case —
   and Scenic died of exactly this.

---

## 5. Verdict

**No knockout blocker found — proceed to professional clearance.**

> **Not taken, 2026-10-04.** The name was adopted without paid clearance, as
> `release-plan.md` §8 decision 2 decided for the free knockout screen. The two
> questions below are what an attorney would be asked if clearance is ever
> bought. Revisit that before money is spent on the brand.

Nothing on the register in classes 9, 39 or 42. Nothing in Navigation or Travel
on the App Store. No descriptiveness refusal on record, and a register that
treats the phrase as inherently distinctive. The one on-the-nose prior
conflict — a class 42 registration for internet map and geography information —
has been cancelled since 2014.

**Two questions for an attorney, if one is ever engaged**, in order: whether reg. 6979596's
"automotive information via a global computer network" reaches a navigation
app, and whether "Sunday drive" is too descriptive of *these* goods to
register on the Principal Register without a fight.

---

## 6. What the rename touched

Applied to code, configuration and the currently-descriptive documents only;
historical documents keep their original wording per `docs/README.md`.

- **Bundle identifier `app.victorylap` → `app.sundaydrive`** (tests
  `app.sundaydrive.tests`). Changed on purpose: nothing has been uploaded, and
  the identifier locks permanently at the first build upload, TestFlight
  included — a burned identifier cannot even be reused on another account.
- Target, scheme, module and generated project `VictoryLap` → `SundayDrive`;
  `CFBundleDisplayName` "Sunday Drive"; Info.plist key
  `VictoryLapAPIBaseURL` → `SundayDriveAPIBaseURL`.
- `ios/Sources/VictoryLapApp.swift` → `SundayDriveApp.swift`, struct renamed.
- Env prefix `VICTORYLAP_*` → `SUNDAYDRIVE_*`, **with both older spellings
  still read after it** at all ten read sites — see below.
- Docker tag and `/health` service id `victorylap-api` → `sundaydrive-api`;
  systemd unit `scenic-api` → `sundaydrive-api`.

**`Color.brand` needed no change.** The previous rename deliberately chose
`.brand` over `.victoryLap` precisely so the next rename would not have to
touch it. That decision paid off here, one day later.

### Three env layers, on purpose

Every read site now takes `SUNDAYDRIVE_*` first, then `VICTORYLAP_*`, then
`SCENIC_*`. Three is ugly. The alternative is worse: dropping a name that is
still set by hand on the deployed box fails **silently** — the server comes up
on the default region and the default data directory and answers every request
as though that were correct. **Delete both legacy layers at the first release,
not before.** Ten sites: `server/app.py` (×2), `server/serve.py`,
`pipeline/render.py`, `tools/analyze_trace.py`, `tools/audit_directions.py`,
`tests/conftest.py`, `ios/Sources/RouteService.swift`,
`ios/Sources/RouteModel.swift`, `ios/Tests/DriveReplay.swift`,
`ios/Tests/LiveDriveTests.swift`.

### One defect fixed in passing

**`server/DEPLOY-oracle.md` was missed entirely by the Victory Lap rename.** It
still instructed setting `SCENIC_HOST` and `SCENIC_DATA` — which worked only
through the legacy fallback the same document elsewhere calls temporary — and
it named the Info.plist key `ScenicAPIBaseURL`, which has not been correct
since 2026-09-20. Both corrected.

### What still says "scenic", on purpose

Unchanged from the previous rename: the GitHub repository `Jamesk1281/Scenic`
and the `~/Scenic` paths that follow from it, the Cloudflare tunnel named
`scenic`, the `~/.ssh/scenic_oracle` key, `docs/scenic_heatmap.png`, and the
routing-arm vocabulary — *scenic route*, *scenic score*, *scenic km*, *scenic
arm*. The word is the right English for the feature, which is simultaneously
why it fails as a mark and why it belongs in the domain language.
