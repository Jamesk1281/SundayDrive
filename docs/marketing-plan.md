# Marketing plan: how Sunday Drive finds its drivers, for $0

**Status: a plan; nothing in it has been executed. Rewritten 2026-10-18 for a
national first launch, against `main` at `0fca74f`.** The New England launch
plan it replaces (L = Thursday 22 October 2026, written 2026-09-29) is
`git show 0fca74f:docs/marketing-plan.md`, last edited in `55f2288`. Web facts
were re-checked on 2026-10-18 and are listed in §14 with that date. Facts
carried over from the 2026-09-29 check and not re-read are marked
*(re-check)*. Platform features change every few months, so re-read anything
marked that way before you build on it.

**What changed on 2026-10-18, decided by the owner:**

1. **The New England-only app will never be public.** The first App Store
   release is the national app: the 48 contiguous states and DC. A private
   TestFlight for invited friends, as today, is not "public". Whether a
   *public* TestFlight link counts is not decided (§12, item 2).
2. **Scenery is scored on one national scale.** A 7 means the same everywhere.
   So the plains have almost no 7+ road (0.6% of eastern Colorado's km), and
   the mountains have plenty (29% of Colorado's mountain km under the scoring
   being built). The source is `docs/national-scenery-scoring-verdict.md` §7,
   on the `usa` branch.

**Everything else is unchanged:** $0 marketing, a completely free app, no
account, no tracking, open source, iPhone only, and one person who is also a
student.

This document sits beside [`release-plan.md`](release-plan.md). That one gets
the app onto the App Store; this one gets people to it. Where the two touch
(the domain, the server, the listing), this one points at the release plan
instead of repeating it. The release plan's national version is later work.

**The constraints it is written to:**

- **$0 marketing budget.** No ads, no paid placements, no paid tools. The only
  money in it is the Apple membership and the domain, which the release needs
  anyway (§11).
- **The app is completely free.** No price, no in-app purchase, no
  subscription, no ads. There is no funnel after the install, so success is
  installs, drives, ratings, and people telling people.
- **National from day one, iPhone only, one server, one person**, who is also
  a student.

---

## 0. The plan on one page

1. **N sets the date, and N is a hypothesis.** N ("national-ready") is the day
   the national build is ready to submit. The estimate is **summer 2027**:
   roughly 4–6 weeks of search engineering, some weeks of data-safety joins,
   and about 160 scenery marks from Western drives. The drives set the
   calendar, because the San Juans' passes open from late May to July. The
   plan dates everything relative to N, and N can slip (§7).
2. **Launch into fall 2027, on a Thursday between 9 September and 7 October.**
   That window covers New England's foliage, the Colorado aspens and canyon
   country's fall season at once. The target is **Thursday 16 September
   2027**. If N lands after about mid-September, release quietly and hold the
   seasonal one-shots for **spring 2028** (§7.2, §7.3).
3. **The product is national; the marketing is not.** One person cannot run
   48 states of local channels. The marketing focuses on two regions, where
   footage, drives and the score's strength coincide:
   - **New England**, which is home, measured, and already filmed;
   - **the Colorado Plateau and the Southern Rockies**, where the Western
     marks will be driven anyway.

   Everywhere else gets only the channels that are national by nature: App
   Store search, YouTube, the national map, Show HN and the tech press (§4.2).
4. **Measured claims stay where they were measured.** The "96% liked at 7+"
   figure is one rater (the author), 52 marks, all in New England. New England
   is also where the network was measured: 146,811 miles, 942,448 scored
   segments, six states. None of it travels. Nationally, say only what is true
   everywhere: free, no account, a score for every road on one scale, an open
   method (§3.4).
5. **The plains are a product risk that copy cannot fix.** On a national
   scale, a Kansas driver sees few 7+ roads. Worse, the router currently
   detours plains trips by a mean 41 minutes for almost nothing it can show.
   "Beautiful roads wherever you are" would earn one-star reviews. Be honest
   in the copy, and make the go/no-go depend on the product saying so too
   (§3.4, §7.3, §10).
6. **The engine is unchanged, but it only runs at home.** Short video with
   location tags, the per-state top 10 from your own data, and the one-shot
   channels (press, one launch post per subreddit, Show HN, Apple's featuring
   nomination). Run the weekly cadence in New England. Feed the Western region
   from banked footage (§5, §6).
7. **Between now and N, film and don't post.** Film every drive you make,
   starting with this October's southern foliage, and log it. Posting can start
   about 12 weeks before N (§7.4).
8. **This week:** renew `jameskouvlis.com` before it expires on 28 October,
   film the late color, and make the two decisions in §15.

**If you only do five things:** renew the domain; film every drive and log it;
never put a New England number in national copy; run the weekly loop in New
England only; and tie every one-shot to a dated season.

### Terms used below

| term | meaning |
|---|---|
| **N** | National-ready: the day the national build is ready to submit (it passes the release plan's checks). §7 dates everything relative to it. N−12w is twelve weeks before |
| **L** | Launch day: the day the app goes live on the App Store, about three weeks after N, on a Thursday in a launch window |
| **Mark** | One rating of a stretch of road, made by a driver during a test drive. The scenery model is checked against marks |
| **The national scale** | Scores mean the same everywhere: a 7 in Kansas is as good as a 7 in Vermont. The alternative, a 7 meaning "among the best in this state", was rejected on 2026-10-18 |
| **Focus region** | A region where the marketing runs its local channels. The app works everywhere either way |
| **ASO** | App Store Optimization: the name, subtitle, keywords, screenshots and video that decide whether people find you in App Store search and install |
| **One-shot channel** | Somewhere you can realistically announce once: a press story, the "I built this" post in a subreddit, Show HN, the featuring nomination |
| **Repeatable channel** | Somewhere you can post every week indefinitely: your video accounts, answers in "where should I drive?" threads |
| **Campaign link** | An App Store link with a tag (`ct=tiktok`) that lets App Store Connect tell you which channel an install came from |
| **CPP** | Custom product page: an alternative version of your App Store page, with different screenshots and text, that you can point one channel at |

---

## 1. The constraints, and what each one forces

| constraint | what it forces |
|---|---|
| $0 budget | Your time is the budget. Everything has to compound (be findable by search: YouTube, TikTok search, App Store search, Pinterest) or be a one-shot worth spending |
| The app is free | There is no launch discount, referral credit or "premium" tier to promote. In exchange, the install costs nothing, and a free, ad-free, open-source tool is welcome in places that ban commercial promotion (§3.3) |
| National from day one | Out-of-region one-star reviews ("doesn't work here") go away. They are replaced by a subtler one: "it works here, and it's boring." Copy must never promise scenery the score can't find (§3.4) |
| One national scale | The score is strongest in the mountains, canyons, coast and woods, and almost silent on the plains. So marketing goes where the score is strong, while the app serves everyone |
| One person, a student | Budget 4–6 hours a week, in batches: the same as the New England plan. Covering more ground in the same hours means fewer regional channels, not thinner ones (§4.2) |
| N is uncertain | Nothing seasonal gets spent until N is real. Every one-shot is tied to a dated season *and* to a gate (§7.3) |
| iPhone only (about 58% of US users *(re-check)*) | Roughly four in ten people who see a post can't install it. Say **"iPhone"** in the caption. Count Android requests as a signal; don't promise anything |
| One server | The national build's load has not been measured. The New England box handled about 1.5 mixed requests a second ([`load-test-oracle.md`](load-test-oracle.md)). Re-run the load test on the national build before L (§7.5, Phase 1) |
| Seasons invert nationally | There is no single peak. Winter is New England's trough but the desert Southwest's high season, and the mountain passes open in late spring and summer (§7.2) |

**Verdict:** the constraints that shaped the New England plan still hold, and
two new ones dominate: the date is uncertain, and the score is uneven by
design. The rest of the plan follows from those two.

---

## 2. The market, re-measured

Counted with Apple's App Store search API (US store) on 2026-10-18, for
"scenic drive", "scenic route", "scenic loop", "sunday drive", "aimless
drives", "wanderway", "driveloop", "roads by porsche" and "detour scenic
navigation". The search is ranked by relevance rather than exhaustive, so
these are **"at least"** figures. Ratings stand in for use; they are not
download counts.

**Scenic-driving apps launched in 2026, as of 2026-10-18:**

| app | launched | ratings | model |
|---|---|---|---|
| Vibe Drive | 2026-01-30 | 1 | |
| DriveGo: Scenic Route Planner | 2026-02-20 | 5 | subscription ("DriveGo Pro"), CarPlay, curvy roads |
| RevRoutes Find Scenic Drives | 2026-05-14 | 0 | |
| Routes – Best Driving Roads | 2026-06-06 | 0 | |
| DriveLoop: Go For A Drive | 2026-06-11 | 1 | time-budget drives, hands off to Google Maps |
| Scenra: Scenic Road Trips | 2026-07-02 | 0 | |
| Pleasant Routes | 2026-07-10 | 14 | |
| Scenic Way | 2026-07-18 | 0 | |
| Joyride: Roads & Drives | 2026-07-28 | 0 | |
| Aimless Drives | 2026-09-02 | 3 | free, no in-app purchase listed, no account, no tracking, hands off to Google Maps |
| **WanderWay Navigation** | **2026-09-16** | **5** | **"generate a Sunday Drive"**, 30 min to 5 h loops, CarPlay, no account; 14-day trial, then a $4.99 one-time unlock |
| Carve: Scenic Drive Planner | 2026-10-05 | 1 | yearly subscription ("Carve Apex"), loops, CarPlay group drives |
| MotoRidez: Scenic Routes | 2026-10-08 | 0 | |
| DriveLoop | 2026-10-14 | 0 | a second, unrelated app with the same name; account for community features |

**The apps with users are still old:** Roadtrippers (2014) has 61,536
ratings, Scenic Motorcycle Navigation (2016) 7,482, calimoto (2018) 979,
ROADS by Porsche (2018) 261 and Kurviger 250. **Detour – Scenic Navigation**
(2024) has 3 ratings. It is free to download, with "Unlimited access" in-app
purchases at $9.99 and $49.99, and a "Scenic Heatmap US" that later went
global.

**Google** launched *Ask Maps* (conversational search with Gemini) in the US
on 12 March 2026. It can be asked for scenic stops along a route. No dedicated
scenic-route mode was found *(re-check before claiming either way)*.

**What it means:**

- **The bar is still about fifteen ratings.** Fourteen 2026 entrants found,
  three of them launched since 2026-09-29, and the best still has 14. The
  2026-09-29 count found eight, because it searched fewer terms. Distribution,
  not features, separates them.
- **Not novel:** loops, a time budget, the direction compass and a
  scenery-versus-time slider. WanderWay, Carve, DriveLoop and Aimless all do
  some of it. Don't claim any of them as "the only".
- **Not unique on its own either:** "free, no account, no tracking". Aimless
  says all three, and WanderWay says no account and no tracking.
- **Defensible, and only in combination:**
  1. a published, measured validation, scoped to where it was measured;
  2. open source;
  3. scenery for cars, rather than curvature for bikes;
  4. free with no account, *and* with its own turn-by-turn navigation, where
     Aimless and DriveLoop hand off to Google Maps.
- **The name is contested.** WanderWay uses "Sunday Drive" as a feature name in
  its listing. In App Store search, "sunday drive" returns other things first.
  Until you rank first for the name, every post needs a direct link, or the
  words "Sunday Drive scenic routes". Check the rank on L.

**Verdict:** the field is more crowded than the 2026-09-29 count showed, and
still empty of users. The plan's job is unchanged: get to 15 honest ratings faster than
anyone else, by being the one with proof and no catch.

---

## 3. Positioning and message

### 3.1 Adopted, not reinvented

[`branding-brainstorm.md`](branding-brainstorm.md) §2 and §5 settled this, and
they hold nationally:

- **The thesis:** every navigation app optimizes for less time, and this is the
  only one that asks you to spend more. **Proudly anti-efficiency.**
- **The voice:** unhurried, dry, quietly confident. No exclamation marks, no
  "supercharge".
- **The subtitle (decided):** *The scenic route, on purpose*
  ([`app-store-submission.md`](app-store-submission.md)). It makes no regional
  claim, so it carries over unchanged.
- **The one-liner, national:** Every road in the contiguous US, scored for
  scenery on one scale. Move one slider to trade minutes for the view.
- **The loop hook:** Ninety minutes, nowhere to be. We'll bring you home the
  pretty way.
- **The credibility line:** Built on open data. Every road measured, not
  crowdsourced. The method is public.
- **The honesty line (new):** One scale everywhere, so some places have more
  7s than others. It says so.

**Verdict:** keep it all. The only line that changes is the one that named New
England.

### 3.2 Say what's on the screen

Captions use the app's own words, so the video and the app agree. The results
card says **"Scenic adds 49 min"** (`ios/Sources/RouteResults.swift`), and the
loop is labelled **"Loop"**, with a duration. The branding doc's "Nowhere" and
"good miles" never shipped to the UI. Ship them first, or leave them out of the
videos. Re-read the UI at N, since the national build may change labels (the
"forest/park" type is wrong for desert; `national-scenery-scoring-verdict.md`
§10, on `usa`).

### 3.3 The free-app message, and why it's worth more than it looks

- **Say it plainly:** *Free. No account, no ads, no tracking. Open source.*
  Every word is true today and is on the live
  [privacy page](https://jamesk1281.github.io/SundayDrive/privacy/).
- **Answer the catch before anyone asks.** The honest answer is the story. A
  Northeastern student built it, the code is public, the server runs on a free
  tier *(re-check at N)*, and the app itself lists what it cannot do (the "What
  it does not do" section of `ios/Sources/BeforeYouDriveView.swift`).
- **It opens doors.** Subreddits and Facebook groups that remove commercial
  promotion will often allow a free, ad-free tool from a real person,
  especially if you ask the moderators first.
- **Lead with the combination, not the words.** Since Aimless and WanderWay
  say "no account" too (§2), the line that's yours is: *free, no account, its
  own turn-by-turn, and the code is public.*
- **Keep it true.** Any analytics SDK, account system, ad, price or email list
  breaks the message and reopens the privacy decision (`release-plan.md` §8,
  Decision 3). That is why every measurement in §9 uses numbers Apple,
  Cloudflare and the platforms already give you, and why the landing page
  loads nothing from anyone else's server, by the rule
  `tests/test_privacy_page.py` enforces on the privacy page.
- **Where not to say it:** Apple rejects in-app event metadata that mentions
  price, "free" included (§5.7). The listing shows the price already, so don't
  spend keyword bytes on it either.

### 3.4 What not to claim

From [`branding-brainstorm.md`](branding-brainstorm.md) §5: no "best route", no
"most scenic", nothing that implies validated ground truth. **"Scored" and
"measured" are defensible. "Beautiful, guaranteed" is not.** Rank drives "by
our score", never as fact. Compare only against **the app's own fastest
route**. Never compare against Apple's routes (ADPLA Attachment 6 §2.3, see
[`legal-and-ip-audit.md`](legal-and-ip-audit.md)), and don't name other apps in
the listing (App Store guideline 2.3.7).

**New for a national launch: every measured claim carries its scope.**

| claim | true where | how to say it |
|---|---|---|
| Free, no account, no ads, no tracking, open source | everywhere | anywhere, plainly |
| Every road has a scenery score, on one scale | the 48 contiguous states and DC, once N ships | "every road in the contiguous US is scored" |
| The method is public | everywhere | link the repo and the method doc |
| The trade against the app's own fastest route | everywhere | "Scenic adds 12 min", in the app's words |
| **"96% liked at 7+"** | **New England only**: 52 marks, one rater (the author) | Only as "on the author's own New England test drives". Never in the listing, captions or national press. A reviewer will rightly ask who rated it |
| The 74%-against-63% separation over 79 ratings | New England only, one rater | The featuring nomination's "helpful details" only, as [`app-store-listing.md`](app-store-listing.md) §6 already does |
| 146,811 miles, 942,448 segments, six states | New England's network | Regional posts and New England press only. The national mileage is measured at N, not estimated |
| Western scores agree with a driver | **nowhere yet** | Nothing until the Western marks pass their pre-registered bar (§7.3, gate G2). Then only "on N test drives in Utah and Colorado", for those landscapes |
| "The prettiest roads near you" or "beautiful roads wherever you are" | **false** on the plains | **Never.** Under the national scale, 0.6% of eastern Colorado's km is 7+ |
| "Flat country: it tells you, and sends you the fast way" | only if the product does it | Only after a low-scenery message ships, and after the plains detour is fixed (§5.10, items 2 and 3) |

**Verdict:** the one-star review to fear is no longer "doesn't work in
Ohio". It is "promised me scenery, gave me 40 extra minutes of cornfield".
Every national sentence must survive a reader in Kansas.

---

## 4. Who it is for, and where the marketing goes

### 4.1 Audiences

| audience | when | where they are | what to show them | priority |
|---|---|---|---|---|
| **Weekend drivers in the focus regions**: suburban, 25–65, with a car and a free Sunday | all year, peaking with their region's season | state and town Facebook groups, state subreddits, Instagram, local news | The loop: an hour, nowhere to be, home the pretty way | **1, the core** |
| **Road-trippers and park visitors**, national: canyon country, the Rockies, foliage | each landscape's season (§7.2) | YouTube, TikTok search, Pinterest, r/roadtrip, travel press | The trade: "Scenic adds 20 min", and the drive between the parks | **2, national and seasonal** |
| **Car enthusiasts**: Miata, Porsche, BMW, Subaru, classic cars | April to November | clubs, Cars & Coffee meets, model subreddits, Instagram | Measured scenic roads, routing a club drive. Carve and DriveGo court them with paid features, and free is your answer | **3, amplifiers** |
| **Map, data and open-source people** | any time, especially November | r/MapPorn, r/dataisbeautiful, Hacker News, the OpenStreetMap community | The national map on one scale, the method, the open repo | **4, credibility, and national for free** |
| **Motorcyclists** | April to October | ADVrider, regional riding groups | "Every road measured", as a complement to their curated routes | **5, incumbents own this**: Scenic Motorcycle, calimoto, Kurviger, REVER. Don't lead with it |
| **Plains and flat-country drivers** | | everywhere | Nothing, as a target. Don't market to them, and don't mislead them when they find you | **not a target** |

**Verdict:** the audiences are the same people as before. What changed is that
priority 1 is defined by region, and priority 2 now spans the country.

### 4.2 The focus sequence: two regions, priced in hours

The New England engine (location-tagged short video, state subreddits, local
press, Facebook groups) works *because* it is local. Copied 48 times, it is
unexecutable. One post per state subreddit and one Facebook group per state per
season is about 48 × 3 × 1 h = **144 hours a year of posting alone**: about 3 h
a week before anything is filmed. And most of those states could never be
filmed from Boston.

So the marketing **focuses** where three things coincide:

1. **footage** you will have anyway;
2. **drives** that produce marks;
3. **a score that is strong there**, and can be shown to be.

| | region | why here | role | hours a week, in season |
|---|---|---|---|---|
| **R1** | **New England** (home) | The only region with marks. The score is validated here (one rater). You drive here every weekend, this October's footage is already being shot, and the per-state top-10 method (§6.3) and the press list (§13) are built | **The weekly engine:** drive, film, three posts a week, reply, state subs, Facebook groups, local press | **3.5–4** |
| **R2** | **The Colorado Plateau and the Southern Rockies**: canyon country (Moab, Capitol Reef), the San Juans, the Front Range | The Western marks are driven here anyway (four landscapes, about 160 marks: `national-scenery-scoring-verdict.md` §9, on `usa`). E1, the scoring being built, lifts the iconic drives over 7: Trail Ridge Road 8.9, Rim Rock Drive 8.0, SR 128 7.5, Capitol Reef Scenic Drive 7.8. 29% of Colorado's mountain km is 7+ | **Fed from banked footage:** one short and one carousel a week from the trip's footage; a monthly Colorado or Utah top-10 post; r/Colorado and r/Utah; one press pitch per state. **Active only if the marks pass** (§7.3, gate G2) | **1** |
| **National** | everywhere | These channels are national by nature, so they cost no more for 48 states than for one | App Store search and custom product pages, YouTube long-form, the national map post, Show HN, the tech press, the OSM community, and answering "does it work in X?" | **0.5–1**, with spikes at L |
| **R3** | earned, not scheduled: Southern Appalachia (the Blue Ridge in October), or the Pacific coast | Strong landscapes, but **not built or checked**. The verdict's §11 lists both as not built, and the coast component is untested anywhere | Becomes a focus only after you have driven it and marked it. Until then, it's national channels only | 0 |
| — | **the plains** | The score is nearly silent there by design | Never a focus. The product must still be honest there (§3.4) | 0 |

**Total: about 5–6 hours a week in season,** inside the same 4–6 hour budget
the New England plan used. The national plan fits by making R2 run on banked
footage and the national channels mostly one-shots, not by adding a second
weekly loop.

**Why R2 and not the Blue Ridge, which is closer:** the Blue Ridge would need a
trip made only for marketing, and its score has never been checked. R2's trip
is made for the scenery model anyway, so its footage is free and its claims
can be backed. If the Western marks fail, R2 still gets the roads shown, but
without score claims ("we drove these"), at half the hours.

**Verdict:** two focus regions and a national layer, in that order. Revisit
after L+90 with the numbers from §9. If R2's campaign links convert better
than R1's, swap the hours.

---

## 5. Channels: the playbooks

Ranked by what each returns per hour for a free app with two focus regions.
Each one has *what*, *how*, *cadence* and *the trap*. Each is also tagged
**national** (costs the same for 48 states) or **regional** (runs only in R1
and, if active, R2).

### 5.1 Short video: TikTok, Instagram Reels, YouTube Shorts (the engine; regional, on national platforms)

**Setup, once, about an hour, in Phase 0 (§7.5), not now:**

- **One handle on all three.** The bare name is probably taken. Pick one that
  is free everywhere (`sundaydrive.app`, `sundaydriveapp`,
  `takethesundaydrive`), and check all three on the same day. Whether to
  *claim* it early, to protect the name, is §12 item 4.
- **TikTok: a Business account.** It can show a clickable website link at any
  follower count, while personal accounts need 1,000 followers first. The cost
  is that you only get TikTok's Commercial Music Library, which costs less
  than it sounds: TikTok's general music licences don't cover promotional
  videos from either kind of account *(re-check)*.
- **Instagram: a Professional (Creator or Business) account.** It gives you
  Insights, and once you pass 200 followers it unlocks *Trial Reels*
  *(re-check)*.
- **YouTube: one channel**, for both Shorts and the long-form drives (§5.2).
- **Where the links point:** the landing page (§5.7) until L, then an App Store
  campaign link per region.

**The levers, and what each one costs** *(all carried from 2026-09-29;
re-check before Phase 0)*:

| lever | where | cost | why it works |
|---|---|---|---|
| **Tag the location on every post** | TikTok, Instagram | 5 s | TikTok's US Local feed (since February 2026) picks posts by location, topic and recency. Instagram's Map collects location-tagged posts. **This is what makes a national platform regional**, and why the engine runs only where you film. Viewers have to opt in to both, and TikTok publishes no audience size, so don't build everything on it |
| **Put the keyword in the first on-screen text, and say it out loud** | TikTok above all | 0 | TikTok search reads on-screen text, speech, captions and hashtags. A video that matches a seasonal search ("Moab scenic drive", "fall foliage drive Vermont") keeps collecting views. Use 3–5 hashtags, not 30 |
| **Carousels for lists** | TikTok, Instagram | 20 min | Photo carousels get about the same reach as video and more saves. "Top 5 drives in Utah, by our score" should be a carousel |
| **"Send this to whoever's driving Sunday"** | Instagram | 0 | Sends (shares by DM) are the signal Instagram says matters most for reaching non-followers |
| **Trial Reels** | Instagram | 0 | A Reel goes to non-followers first, and a flop doesn't count against you. Test two hooks for the same drive |
| **Reply to comments with a video** | TikTok, Instagram | 10 min each | "Comment your town", then reply with a loop from that town. **In R1 only**, where you can drive it. Elsewhere, reply with a screen recording, and be honest if it's flat |
| **One file on three platforms, exported clean** | all | +10 min | Export from your editor, not from TikTok. Instagram demotes Reels that carry another app's watermark |
| **Collab posts and tags** | Instagram, TikTok | 1 min | Tag the orchard, the general store, the club, the park's gateway town |
| **Link each Short to its long-form drive** | YouTube | 1 min | Point Shorts viewers at the full ambient drive |

**Cadence:** in R1, at least 3 posts a week in season, cut from one drive
(§6). R2 adds one short and one carousel a week, from the bank.

**Music:** original audio (road noise, voice-over), TikTok's Commercial Music
Library, Meta's Sound Collection or YouTube's Audio Library. Never put a
trending commercial track on a post that promotes the app.

**Editing:** iMovie or DaVinci Resolve, both free. **Skip CapCut for footage
you want to own.** Its terms changed on 12 June 2025 to take a perpetual,
irrevocable licence to whatever you upload *(re-check)*. Canva's free tier
covers the carousels.

**The trap:** chasing views. A video with 200,000 views from everywhere is
worth less than 2,000 from Worcester or Grand Junction. Watch installs per
campaign link (§9), not views. Nationally, the subtler trap is a viral clip
from a 9-rated canyon road bringing in viewers from Nebraska who then meet a
plains score. Caption the place, not the promise.

**Verdict:** still the engine, and still regional. The platforms are national,
and the location tag is what keeps the effort local.

### 5.2 YouTube long-form: the ambient drive (national, the easiest evergreen)

**What:** 30 to 90 minutes of a single drive. Mount the camera, don't talk,
edit gently, and add chapters by town. It is an established genre, with
channels that post multi-hour silent drives that people watch as background
*(re-check)*.

**Why it's the best national channel:** YouTube search is national and
long-lived, and people search the drive, not the region. "Moab to Capitol Reef
scenic drive 4K" finds a viewer in Ohio planning a trip. The banked footage
from the Western marks trip is exactly this. The description carries the
route, the app link and the credits:

```
SR 128 along the Colorado River, Moab to Cisco, picked by Sunday Drive — a
free iPhone app that scores every road in the contiguous US for scenery.
[campaign link]

0:00 Moab · 14:20 Castle Valley turnoff · …
Route data © OpenStreetMap contributors. Music: [library credit].
```

**Cadence:** one every week or two, whenever the footage is good. The bank can
run this through the winter, when R1 is in its trough.
**The trap:** a shaky or badly exposed mount. Test it on a short drive first.

**Verdict:** promoted from "efficient" to the lead national channel. It is the
only repeatable channel where the R2 footage works without you being in R2.

### 5.3 Reddit (the best free geography there is; regional plus three national subs)

**Where, by region:**

- **R1:** r/newengland, r/boston, r/massachusetts, r/vermont,
  r/newhampshire, r/maine, r/Connecticut, r/RhodeIsland, city subs like
  r/worcester.
- **R2 (when active):** r/Colorado, r/Utah, r/Moab, r/Denver, r/SaltLakeCity
  *(re-check each sub's rules)*.
- **National:** r/roadtrip (answers, not launch posts), r/MapPorn and
  r/dataisbeautiful (the national map), r/SideProject and r/iOSProgramming
  (builders). Hobbyists: r/Miata, r/subaru, r/cars.

**Three formats:**

1. **The per-state data post, repeatable:** "I scored every road in Vermont for
   scenery using open data. These are the 10 best-scoring drives." A map, the
   list, the method in one paragraph, and the credits. **Only for states you
   have driven enough of to check the list** (§6.3, step 5). That is the six
   New England states now, and Colorado and Utah after the marks trip. Eight
   states times three seasons is 24 posts a year, and no two alike.
2. **The national map, a one-shot per sub:** every road in the contiguous US,
   colored on one scale. This is the post nobody else can make, and it is
   honest by construction: the plains are visibly pale. Title it as what it
   is: "Every road in the contiguous US, scored for scenery on one scale".
   r/MapPorn and r/dataisbeautiful, days apart, at a moment you choose (§7.2).
3. **The launch post, one per sub:** "I'm a Northeastern student, and I built a
   free, open-source iPhone app that finds the scenic way. No ads, no account."
   Post it on L or L+1, in the one or two subs where the data post did best.

**How:** read every sub's rules. **Message the moderators before any launch
post**: say who you are and that the app is free, open source and ad-free, then
ask. Post in the morning, local time for the sub, and answer every comment for
two hours. Answer "scenic drive from X?" threads with a real route, whether or
not you mention the app.

**The trap:** posting the same thing to eight subs in one day, which is how
accounts get flagged. Space posts days apart. Nationally, the trap is a
"does it work in Iowa?" thread. Answer honestly: yes, and Iowa's best roads
score lower on a national scale.

**Verdict:** regional subs in the two focus regions; the national map is the
one national Reddit play, and it is worth more than any launch post.

### 5.4 Facebook groups (regional)

**Where:** R1's foliage groups (the *New England Fall Foliage* community linked
to Jeff Folger, whose jeff-foliage.com publishes the season's forecasts), state
and town groups, and car-club groups. R2 gets none: Facebook groups reward
contributing before promoting, and you can't contribute weekly to a community
two thousand miles away.

**How:** join as yourself, contribute before you promote, ask the admins, then
share the weekly drive with a photo and the route. This audience skews older
and will search the App Store by name, so the name check in §2 matters.

**Cadence:** one or two R1 groups a week, rotating, in season.
**The trap:** a post that is only a link. Lead with the photo and the drive.

**Verdict:** R1 only. It's the channel least able to scale, so don't try to.

### 5.5 Press and newsletters (one story each, tied to a season and a gate)

**The hook calendar** (dates for the target L; §7.4 moves them if N moves):

| when | the hook | to whom |
|---|---|---|
| L, September 2027 | "Local student's free app scores every road in America for scenery — here are the five best drives near [city] for the leaves" | R1 press; Northeastern |
| L to L+14 | "Every road in the contiguous US, scored on one scale: the map" | national tech and data press, MacStories, 9to5Mac |
| L+7 to L+21, if gate G2 passed | "Free app's algorithm says these are Colorado's best-scoring drives, and a test driver checked" | R2 press |
| November 2027 (off-season) | "We scored every official scenic byway in New England. Here's how they rank." **Rank them with `c_scenic_tag` left out.** That component *is* the byway designation (`pipeline/score.py`), so with it included the designation grades itself | R1 press, byway organizations |
| March–April 2028 | Canyon country's spring season: "The drives between the parks, by our score" | R2 press, travel press |
| Memorial Day 2028 (27–29 May) | "The summer drives an algorithm picked" | R1 and R2 |

**Places you can publish yourself, no pitch needed:**

- **Patch:** anyone can post an announcement to a town's Patch site for free
  *(re-check)*. Do one for every R1 town you've featured.
- **Northeastern:** Northeastern Global News, *The Huntington News* (tips at
  huntnewsnu.com/tips) and NUMedia. Your own university is the easiest pitch
  you will ever make, and its reach is national (alumni).

**R1 pitch targets:** Boston.com, Universal Hub, Axios Boston, *The Boston
Globe*; WCVB's *Chronicle*, NBC10 Boston, WBZ, NECN; WBUR and GBH; *Yankee* /
New England Today; *Seven Days* and VTDigger; NHPR and *New Hampshire
Magazine*; *Down East*, *Portland Press Herald*, *Bangor Daily News*; CT
Insider and CT Public; *The Providence Journal* and The Public's Radio.
**R2 targets** *(re-check; not researched)*: *The Colorado Sun*, *The Denver
Post*'s travel desk, *The Salt Lake Tribune*, KSL, the *Moab Sun News*.
**National tech:** MacStories and 9to5Mac (both take tips), which like
native, privacy-respecting apps.

**The pitch, under 150 words, for R1 at L:**

```
Subject: A student scored every road in America for scenery

Hi [name] — I'm a [year] at Northeastern. I built Sunday Drive, a free
iPhone app that scores every road in the contiguous US for scenery from open
map data, then routes you the pretty way instead of the fast way. Give it an
hour and it plans a loop home.

It's free, with no ads and no accounts, and the code is public. With peak
color in [region] this weekend, your readers might like the five
best-scoring drives near [city] — the list and a map are attached.

On the App Store now: [link]. Press kit: [link]. Happy to talk, or to take
you on the drive.
```

The New England numbers (146,811 miles, six states) go in R1 pitches as "in
New England alone". The national mileage goes in once it is measured at N.

**The press kit (a section of the landing page):** the icon, 5 screenshots,
the 30-second preview video, a photo of you, the one-paragraph story, the
national map, the numbers *with their scope*, the credits, and contact
details.

**The trap:** pitching before anyone can download it. A story that ends
"coming summer 2027" converts nobody, and it spends your one shot. That rules
out every pitch before L.

**Verdict:** R1 press at L, national tech press for the map, R2 press only
after gate G2. Each outlet gets one story.

### 5.6 Clubs, events, destinations and tourism (other people's audiences; R1)

- **Car clubs:** offer to route a club's next drive, then ask to film it and
  post it as a Collab: BMW CCA Boston, PCA Northeast Region, Audi Club
  Northeast, Miata and Subaru groups, VSCCA and AACA regions *(re-check)*.
  Classic-car owners literally go on Sunday drives.
- **Events:** the Larz Anderson Auto Museum in Brookline runs cars-and-coffee
  meets and scenic cruises in season *(re-check the 2027 calendar in
  Phase 0)*. Bring the TestFlight QR code on your phone during the beta.
- **Destinations:** orchards, cider mills, farm stands and general stores. End
  a drive at one and tag it, and it will usually reshare.
- **Tourism and byways:** tag state tourism offices on posts from their state.
  Give byway organizations the byway-ranking piece first.
- **R2, at a distance:** gateway-town visitor centres (Moab, Ouray, Torrey) and
  park-adjacent businesses can be tagged on banked footage. Don't promise them
  a drive you won't make.

**Verdict:** R1 only, in person. In R2, tags yes, relationships no.

### 5.7 The App Store itself (national by nature)

| tool | what to do | when |
|---|---|---|
| **Landing page** | Replace the redirect in `site/index.html` with a real page: what the app is, 3 screenshots, "contiguous US · iPhone · free", the national map, the App Store badge (or "coming 2027", with no sign-up), the press kit, credits and contact. **It doubles as the Support URL that App Store Connect requires.** It loads nothing external | Phase 0 |
| **Keywords** | **100 bytes**, no competitor names, nothing already in the name ("sunday", "drive") or the subtitle ("scenic", "route"). State names no longer earn their bytes. One national candidate, 96 bytes: `backroads,loop,byway,curvy,road,trip,foliage,fall,leaf,peeping,canyon,mountain,pass,country,park`. Apple combines terms into phrases ("canyon" + "drive"). Re-measure the bytes before pasting. The New England draft in [`app-store-listing.md`](app-store-listing.md) §3 started from the 2026-09-29 candidate and is superseded by the national listing, which is later work | before S |
| **Screenshots and preview video** | The first three screenshots decide most installs. Show the trade ("Scenic adds 12 min"), a loop, and the road itself, from R1 or R2. **No screenshot may imply every place looks like that**: caption the place | before S |
| **Featuring nomination** | App Store Connect → Featuring Nominations → *App Launch*. **At least 2 weeks before L**, and Apple suggests up to 3 months ahead for wider consideration. For L = 16 September 2027, file by mid-June if the app record allows it *(re-check)*, and by 2 September at the latest. Tell the story: a student, open data, one scale for a whole country, the season | N−8w to L−14 |
| **Manual release** | Choose "Manually release this version", so that approval doesn't mean launch | at S |
| **Pre-orders** | Only if approval lands two or more weeks before L. A pre-order works as a waitlist that collects no data and installs automatically on release day. It needs App Review first and can run 2–180 days *(re-check)* | if the gap exists |
| **Promotional text** | 170 characters above the description, **editable any time without review**. National seasons make this the most useful field in the listing: aspens in late September, color moving south in October, canyon country in spring, the passes in June | weekly in season |
| **Custom product pages** | Up to 70, and they can carry keywords and appear in organic search *(re-check)*. **This is how a national listing does regional marketing:** a *New England foliage* page, a *canyon country* page, a *loops* page. Point each region's campaign links at its page. Keywords assigned to a page come out of your 100 bytes | L+7 |
| **Campaign links** | One per channel *and region*: `…&ct=tiktok-r1`, `…&ct=reddit-r2` | before L |
| **In-app events** | Free cards in search and editorial, up to 31 days. **They need real in-app content**, and metadata that mentions "free" is rejected. A seasonal loop collection ("aspen loops", "peak color") filed as a *New Season* | foliage 2028, or earlier if the content exists |

**Verdict:** the App Store is where "national" costs nothing extra. Custom
product pages carry the regional story inside one listing.

### 5.8 Tech and open-source communities (national, credibility)

- **Show HN:** "Show HN: Sunday Drive – I scored every road in the US for
  scenery on one scale". Link the repo and a write-up of the method,
  **including why one scale and what it costs the plains**. HN rewards that
  honesty. It's a one-shot, but it isn't seasonal (§7.2).
- **The OpenStreetMap community** (weeklyOSM, OSM US): a project that routes by
  their data, and has measured how unevenly some things are mapped (green
  areas 3.3× thinner in Maine than in Rhode Island; untagged surfaces in
  Kansas), is news to them.
- **#30DayMapChallenge** runs every November. The national map fits several
  days.
- **r/MapPorn and r/dataisbeautiful:** the national map (§5.3).

**Verdict:** these were the off-season one-shots, and they still are. The
national map makes each of them stronger than the New England version would
have been.

### 5.9 Pinterest (optional, national, evergreen)

Trip planners use it as a search engine, months ahead. Pin the R1 and R2
carousels and maps, linked to the landing page. Start in Phase 0, so pins are
indexed by the fall 2027 planning season.

### 5.10 The product as a channel (engineering asks, ranked by leverage)

This is code, so it sits outside the marketing budget. Adopt items into
[`roadmap.md`](roadmap.md) one at a time; this list doesn't schedule them.

1. **The rating prompt. Built** (2026-10-08, [`rating-prompt.md`](rating-prompt.md)):
   on the second arrived drive of 10 minutes or more, once per version, asked
   from planning. Nothing to do but confirm it works on the national build.
2. **An honest low-scenery message.** When a route or loop finds little 7+
   road, the card should say so ("Not much high-scoring road near here; the
   fast way is nearly as pretty") instead of selling the scenic arm. **This is
   the plains defense, and a go/no-go item** (§7.3). Small, mostly copy.
3. **Stop paying minutes for nothing on the plains.** On six eastern-Colorado
   trips at the top of the slider, the router adds a mean 41 minutes for
   2.8 km of 7+ road in total (`national-scenery-scoring-verdict.md`, on
   `usa`). The verdict recommends the convex-cost experiment before a national
   launch. Marketing can't fix a detour that buys nothing, so this goes in the
   release gate, not the copy.
4. **Share this drive.** A `ShareLink` with an image of the map and the card
   ("72 min · Scenic adds 18 min · Sunday Drive, free on the App Store").
   **Trim the first and last kilometre, because a loop starts "From here",
   which is usually home.** Nothing like it exists today: there is no
   `ShareLink` in `ios/Sources`.
5. **"Hey Siri, take me on a Sunday drive"**, through App Intents, starting a
   loop. On-brand, easy to demo, and the kind of thing App Store editors look
   for.
6. **An opt-in weekly reminder:** "It's Sunday. Ninety minutes, nowhere to be?"
   A local notification, so no server and no data.
7. **CarPlay.** WanderWay, Carve and DriveGo have it (§2). The owner holds the
   entitlement (2026-10-08), and the code estimate then was about a day to
   mirror the phone and 3–4 days for a full CarPlay app, with real-car drives
   setting the calendar. Nationally, a road-trip audience will ask on day one.
8. **A web preview**, so Android users, desktop readers and journalists can try
   routes. A website that sends coordinates is a new privacy surface to
   document first. Later.

**Verdict:** items 2 and 3 moved to the top in substance. They are what keeps
a national launch from earning its first reviews on the plains.

---

## 6. The content system: one drive makes a week

### 6.1 The weekly loop in R1 (about 3.5–4 hours)

| when | what | time |
|---|---|---|
| Thursday | Pick the drive: a loop or route from a **public starting point**. Check the forecast and, in fall, the state foliage report | 15 min |
| Saturday or Sunday | Drive it. The phone sits in its mount, screen-recording the app. A second camera films the road. Take five stills at stops | the drive |
| Sunday | Edit 1 long-form video, 3 shorts (15–35 s each) and 1 carousel. Export clean vertical files | 2 h |
| Monday | Schedule in TikTok Studio, Meta Business Suite and YouTube Studio, all free. Captions and location tags. Queue one R2 short and carousel from the bank | 30 min |
| Every day | Reply to comments, especially in the first hour after each post | 15 min |
| Monday | Review last week's numbers (§9) | 20 min |

**What one drive yields:** 1 long-form video, 3 shorts on three platforms each,
1 carousel on two, 1 Facebook post, and stills for Reddit, press and the App
Store. About 13 posts.

### 6.2 Twelve formats, with hooks

| # | format | the first two seconds | where |
|---|---|---|---|
| 1 | **The Sunday Drive**, the weekly episode | the best frame, over "This week's drive, picked by an algorithm" | everywhere, R1 |
| 2 | **The trade** | the card, "Scenic adds 12 min", then "Worth it?" | TikTok, Reels |
| 3 | **The top 5 in a state** | "The 5 best-scoring drives in Utah" | carousel, R1 and R2 states only |
| 4 | **Comment your town** | "You said Nashua. Here's an hour, the pretty way" | reply videos, R1 |
| 5 | **The algorithm's worst pick** | "My app thought this was scenic" | TikTok |
| 6 | **Building in public** | "I scored every road in America. Here's how" | TikTok, Shorts |
| 7 | **The map** | the contiguous US animating in, on one scale; or one state | everywhere, plus Reddit |
| 8 | **The ambient drive** | no hook: it's 45 minutes of drive | YouTube |
| 9 | **Stitching a travel video** | their Moab clip, then "here's the drive between the parks, by our score" | TikTok |
| 10 | **A club or destination drive** | "We routed the Miata club's fall drive" | Collab, R1 |
| 11 | **One scale, honestly** | "On a national scale, Kansas's best road is a [score]. Here's why that's the point" | TikTok, Shorts |
| 12 | **Peak this weekend** | "Peak color in the Monadnocks this weekend" / "Aspens on the Million Dollar Highway" | in season |

Format 11 replaces the New England plan's "honest ETA". It turns the national
scale's weakness into the brand's dry honesty. **Check the number on the
national build before filming it.**

**The mix:** about 40% drives (1, 8, 12), 25% data (3, 7), 20% building in
public (5, 6, 11) and 15% community (4, 9, 10).

**The caption template:**

```
Scenic drive from Worcester, MA — a 60-minute loop through the Quabbin hills.
Picked by Sunday Drive, a free iPhone app that scores every road in the US
for scenery. iPhone · free · link in bio
#newengland #scenicdrive #fallfoliage #massachusetts #sundaydrive
```

**On every post:** a location tag, the keyword in the first on-screen text,
"iPhone" in the caption, the place named (never "roads like this near you"),
and one call to action (send, comment or save).

### 6.3 The flagship: a per-state top 10 from your own data, as a series

The New England data supports it: `scored_chunks.parquet` in
`data/processed-ne` has `name`, `ref`, `highway`, `length_m`, every beauty
component and the final `score` for all 942,448 segments. The national build
will have the same columns. The method:

1. Group segments into named stretches (by `name`, or by `ref` where there is
   no name), and keep stretches with at least about 8 km of drivable road.
2. Rank them by length-weighted mean `score`.
3. Assign each stretch to a state using the Census cartographic state
   boundaries, which are public domain.
4. **Rank within each state, never across states.** Terrain saturates
   differently by region, and green mapping is uneven (3.3× thinner in Maine
   than in Rhode Island). A cross-state top 10 is quietly biased, even on one
   scale.
5. **Check each state's top 10 against your own driving.** Cut anything
   that's obviously wrong, and say so in the post ("#7 surprised me"). If the
   list is mostly official byways, re-rank without `c_scenic_tag` and say which
   ranking you used. **A state you haven't driven doesn't get a list.**
6. **Say the scale.** On one national scale, a state's #1 can be a 5. Print
   the scores, and let the low ones be the joke and the honesty.
7. **Exclude roads the safety work hasn't cleared.** In the West, seasonal
   closures, 4WD-only and private roads are still being joined
   (`us-map-data-findings.md` §7). A top-10 road that is closed or impassable
   is the worst post you can make. Check each listed road's status in its
   season.

**The series:** the six New England states now (with the national rebuild's
scores, at N), then Colorado and Utah after the marks trip, then any R3 state
you've driven. "The ten best drives in Vermont" becomes "the ten best drives
in [state]", one state at a time.

New England miles per state, for R1 posts: MA 42,116 · ME 37,263 · CT 24,668
· NH 19,967 · VT 17,730 · RI 6,762, from the network census in
[`driving-app-features-cost.md`](driving-app-features-cost.md).

### 6.4 Rules for every piece of content

- **Never film while driving.** Most states ban holding a phone while driving
  *(re-check per state you film in)*. A passenger films, or the camera is
  mounted and started before the car moves.
- **Never show home.** Loops start "From here". Start demo loops from a town
  green, a trailhead or a parking lot, and check the first and last seconds of
  every screen recording.
- **Credit the map.** Anything drawn from the data is an ODbL *Produced Work*,
  so "© OpenStreetMap contributors" has to be visible in the image itself. Add
  the land-cover and elevation credits whenever those layers show, plus any new
  national sources (PAD-US, for example). Wording: [`data-sources.md`](data-sources.md)
  and `ios/Sources/AboutView.swift`.
- **Leave Apple's corner alone.** Don't crop or caption over the Apple Maps
  logo and the Legal link in screen recordings.
- **Use your own footage.** No Street View, no Google imagery, no other
  creators' clips outside TikTok's own stitch and duet.
- **Name the place, scope the claim.** Every clip says where it is. No clip
  implies the whole country looks like it.

### 6.5 The bank: filming for later (R2, and R1 out of season)

Every drive between now and N is footage, and the Western marks trip is the
biggest single deposit. Keep a **footage log**, a spreadsheet kept off the
public repo:

| field | why |
|---|---|
| date and season | so footage is posted in its season, not out of it |
| region, road, start and end towns | for captions and location tags |
| the road's score, at the time and after the national rebuild | so a caption never cites a score that has since moved |
| what's in frame that shouldn't be: plates, faces, home streets | so every clip is checked once, not at posting time |
| marked or not | only marked roads can carry "a test driver checked" |

**On the Western marks trip,** filming adds about 1–2 hours a day: mounting,
stills at stops, one long take per road. The drives themselves belong to the
scenery model. Film the dull roads too: "the algorithm's worst pick" and "on a
national scale, this is a 2" are honest formats.

**Verdict:** the content system carries over intact for R1. What's new is the
bank, the footage log, and the rule that a list needs a drive.

---

## 7. The timeline, relative to N

### 7.1 The milestones

| code | milestone | what it depends on | estimate |
|---|---|---|---|
| **M** | Apple Developer Program membership | **done**, accepted 2026-10-03. It **renews about 3 October 2027**, inside the launch window, so renew it before L | — |
| **G1** | **Engineering gate:** the compact graph and corridor search serve one Western region at today's latency | path C, roughly 4–6 weeks of engineering plus validation (`usa-extension-feasibility.md` §8, on `usa`) | spring 2027 *(judgment)* |
| **G2** | **Scenery gate:** the Western marks are in, and E1's promotions pass the pre-registered bar (17 of 20 liked or better) | about 160 marks from canyon country, the San Juans, the eastern plains and the Great Basin; the San Juans' passes open late May to July | July 2027 *(judgment)* |
| **N** | National-ready: the national build passes the release plan's checks | G1, G2, and the data-safety joins (closures, 4WD, private roads; "a week each", `us-map-data-findings.md` §7) | **summer 2027; likely mid-August** |
| **B** | TestFlight external testing | a build and Beta App Review | N + 2 days |
| **S** | App Store submission | the release plan's artifacts, the national listing | N + 3 days |
| **A** | Approved | App Review | N + 1 week |
| **L** | **Launch: a manual release, on a Thursday in a launch window** | A, plus the go/no-go check (§7.3) | N + about 3 weeks |

**Why Thursday:** the app is for weekends. Launch on a Thursday, and the first
weekend is when people use it.

**N's range, honestly:** the earliest is about late July 2027 (the San Juans
driven in early July, everything else on time). The likely case is mid to late
August. A late N is September or later, if a gate fails or the semester eats
the engineering. Every date below assumes the likely case, and §7.3 says what
happens in the others.

### 7.2 The seasons, nationally, and where each one-shot goes

There is no single peak. Each landscape has its own, and one-shots are spent
once, so each is tied to a season *and* to a gate.

| season | dates | strong where | what it suits |
|---|---|---|---|
| Desert high season, spring | March to May | canyon country, the Great Basin | R2's spring beat (2028); canyon-country press |
| Memorial Day | 29–31 May 2027 · 27–29 May 2028 | everywhere; the high passes start to open | not a 2027 launch (N isn't ready); 2028's spring opener |
| The passes open | late May to July (Trail Ridge typically around Memorial Day; it opened 29 May in 2026) | the Rockies, the San Juans | filming the marks trip; summer content |
| Summer | June to August | mountains, coast, northern New England | the bank; Phase 0 posting |
| **Fall, the launch window** | **Thu 9 September to Thu 7 October 2027** | northern New England (late September to early October), Colorado aspens (mid to late September *(re-check)*), canyon country's fall season (September to October) | **L**, R1 press, the featuring nomination, R1 and R2 launch posts |
| Color moves south | October | southern New England (mid to late October), the Blue Ridge (mid to late October, by elevation) | promotional text; national foliage searches on YouTube and TikTok |
| Off-season | November to February | New England's trough, the desert's mild season | Show HN, #30DayMapChallenge, the OSM community, the byway ranking, YouTube from the bank |

**Where each one-shot goes:**

| one-shot | seasonal? | spend it |
|---|---|---|
| Apple featuring nomination (*App Launch*) | yes | for L, filed by L−14 |
| R1 press, and R1 subreddit launch posts | yes | L to L+3 |
| National tech press (MacStories, 9to5Mac) | no | L to L+14 |
| R2 subreddit launch posts and press | yes, and gated on G2 | L+7 to L+21; else the spring 2028 beat |
| The national map on r/MapPorn and r/dataisbeautiful | no | L+14 to L+45, days apart, or November for #30DayMapChallenge |
| Show HN | no | a weekday after launch week, or November |
| *App Enhancements* nomination | yes | the first real update, about two months after L |

### 7.3 The gates and the go/no-go check

**G1, at about N−16 weeks (spring 2027):** is the compact graph and corridor
search working on one Western region? If not, the fall 2027 window is at risk.
Decide then whether to hold the target, not in August.

**G2, after the Western drives (July 2027):** did E1's promotions pass the
pre-registered bar?

- **If yes,** R2 becomes an active focus region, with claims scoped to those
  landscapes.
- **If no,** the scoring changes or N slips (the next candidate is tested on
  the next drive, not tuned on this one). Either way, R2 runs at half hours
  with no score claims.

**At L−7, launch on the planned Thursday only if all seven hold:**

1. The app is approved, or submitted early enough that a normal review lands
   before L−1.
2. The load test passed **on the national build**, and the rate limit is on.
3. The domain is renewed past L+12 months, and the membership renewal is done.
4. The beta has no known crash.
5. The landing page and the campaign links are live.
6. **A plains route and a plains loop say something true.** Either the
   low-scenery message (§5.10, item 2) shows, or the slider no longer buys
   minutes for nothing there (item 3).
7. **No national copy carries a New England number**: the listing,
   screenshots, press kit and drafted posts, checked against §3.4.

**If any one fails, or N is later than about mid-September 2027:** release
quietly once approved (the listing, your own channels, the beta testers), and
spend only the one-shots that aren't seasonal: Show HN, the national map, the
OSM community, #30DayMapChallenge. Hold the seasonal ones (the featuring
nomination, R1 press, the state-subreddit launch posts) for the **spring 2028
openers**: canyon country in March or April for R2, and Memorial Day weekend
(27–29 May 2028) for R1. That fallback is a good plan in its own right, not a
failure.

### 7.4 A worked example on real dates

This assumes the likely case: N = Friday 13 August 2027.

| milestone | date | why |
|---|---|---|
| Domain renewed | **by Wed 28 Oct 2026** | it expires that day |
| Southern New England color filmed | 18 Oct – early Nov 2026 | the last of this year's season, and the start of the bank |
| Off-season | Nov 2026 – Feb 2027 | no posting; footage log; R1 per-state lists drafted on the current scores |
| G1 | about mid-April 2027 | N−16 weeks |
| Canyon country, Great Basin and plains drives | spring 2027 *(the owner's calendar)* | canyon country is at its best in spring, and these landscapes don't wait on snow |
| Phase 0 starts | about Fri 21 May 2027 | N−12 weeks: handles, landing page, first posts in R1 |
| San Juans drives | late June – July 2027 | when the passes are open |
| G2 | late July 2027 | the marks scored against the pre-registered predictions |
| Featuring nomination | mid-June if possible, by Thu 2 Sep at the latest | up to 3 months ahead; at least 14 days |
| **N** | **Fri 13 Aug 2027** | |
| B, S | Mon 16 – Tue 17 Aug | |
| A | about Tue 24 Aug | |
| Membership renewed | before Fri 3 Sep | it would otherwise renew about 3 October, inside the window |
| Go/no-go | Thu 9 Sep | L−7 |
| **L** | **Thu 16 Sep 2027** | the first weekend (18–19 Sep) is northern New England's color and Colorado's aspens |
| R2 launch beat (if G2 passed) | 23 Sep – 7 Oct | |
| Domain renewal | before Thu 28 Oct 2027 | already done before L |
| L+30 | Sat 16 Oct 2027 | color moving south |
| Off-season one-shots | November 2027 | Show HN, #30DayMapChallenge |
| Spring beats | March–April and 27–29 May 2028 | R2's canyon season and Memorial Day |

**If N moves:** an early N (late July) still launches in the window, on
Thursday 9 September, and uses the gap for the beta and the 3-month
nomination lead. A late N moves L to the last Thursday that leaves a week
after approval, as late as 7 October. Past mid-September, the fallback in §7.3
takes over.

### 7.5 Phase by phase

**Phase P: pre-launch (now to N−12 weeks; about 1–2 hours a week)**

- [ ] **Renew `jameskouvlis.com` before 28 October 2026** (§15). The API
      hostname, the privacy contact and every build depend on it.
- [ ] Film every drive you make, from public starting points. Keep the footage
      log (§6.5).
- [ ] **Don't post, and don't launch the New England app.** A post now sends
      people to an app that won't exist for ten months.
- [ ] If people ask to follow along, point them at the GitHub repository's
      **Watch → Releases**. It is a waitlist that adds no data flow of yours.
      An email list would, and is §12 item 6.
- [ ] Draft the R1 per-state top 10s on today's scores, as a dry run of §6.3.
      Re-run them on the national build before posting.
- [ ] On the Western drives, film for the bank (§6.5).

**Phase 0: foundations (N−12 weeks to N; about 3–4 hours a week)**

- [ ] Claim the handle on TikTok (Business), Instagram (Professional) and
      YouTube, if not already claimed (§12, item 4).
- [ ] Build the landing page (§5.7), with a press-kit section and the national
      map. No sign-up form.
- [ ] **Start posting in R1, twice a week.** Drives, building in public, the
      map. The account needs a few weeks of history by L.
- [ ] Start YouTube long-form from the bank, and Pinterest pins.
- [ ] Draft the national listing and screenshots against §3.4.
- [ ] File the featuring nomination as early as the app record allows.

**Phase 1: beta and review (N to L−1, about three weeks)**

- [ ] TestFlight: invited testers, or the public link if §12 item 2 says it
      isn't "public". Northeastern, one R1 subreddit, one car club, and a few
      testers in R2 if the link is public.
- [ ] Watch the server and fix what breaks. Ask testers for one-line quotes,
      with their permission.
- [ ] **Run the load test on the national build** and set the Cloudflare rate
      limit (`server/DEPLOY-oracle.md`, Part 11; the method is in
      [`load-test-oracle.md`](load-test-oracle.md)).
- [ ] Renew the membership if it falls due before L+30.
- [ ] Prepare the screenshots, preview video, keywords, campaign links (per
      region) and custom product pages.
- [ ] Submit (S) with manual release selected. Draft the press lists and
      pitches.
- [ ] **L−7: the go/no-go check (§7.3).**
- [ ] The day approval (A) lands, send the R1 pitches ("available Thursday").
- [ ] L−1, pre-flight: `api/health`, the box's memory, the rate limit, the
      domain, the listing, every link, and all drafts ready.

**Phase 2: launch week (L to L+7; 15–20 hours)**

| day | what | notes |
|---|---|---|
| **L (Thursday)**, 8 am Eastern | Release in App Store Connect. Wait until the listing is live in the US store, then search "sunday drive" and note your rank | this can take hours |
| L, 11 am | Your own accounts, Northeastern's channels, then **R1 Reddit launch post #1**, then Patch | stagger them; reply to everything until 2 pm |
| L, all day | Check Cloudflare's request graph and the box every hour | stop posting if errors climb (§8) |
| L+1 (Friday) | R1 Reddit launch post #2, the Facebook groups, the national tech-press tips. Tell testers it's live and ask for an honest rating. **Never** offer anything in return, and never ask for five stars | |
| L+2 to L+3 (the weekend) | The launch-weekend Sunday Drive in R1 | |
| L+4 (Monday) | Show HN, if the week has room; otherwise November | |
| L+7 | First numbers (§9). Set the download target from this week's rate. R2 launch posts start if G2 passed | |

**Phase 3: the first month (L+8 to L+30)**

- [ ] Keep the R1 weekly loop going (§6.1).
- [ ] R2: one short and one carousel a week from the bank, the Colorado and
      Utah top-10 posts, the R2 pitches.
- [ ] The national map post, days apart on two subs.
- [ ] Ship the first update (fixes, plus the share card if it's ready), then
      file an *App Enhancements* nomination, two weeks ahead.
- [ ] Build the custom product pages and point the regional links at them.
- [ ] Two R1 club or destination collaborations.

**Phase 4: compounding (L+31 to L+90)**

- [ ] YouTube library from the season's footage.
- [ ] The byway-ranking piece (§5.5).
- [ ] The off-season one-shots: Show HN, #30DayMapChallenge, the OSM community.
- [ ] Cut the weakest channel by §9's rules. Compare R1 and R2 per hour.
- [ ] Plan the spring 2028 beats: canyon country and Memorial Day.

**Verdict:** the plan is the New England plan's shape stretched over ten
months, with the long middle spent filming, not posting. The gates make N's
uncertainty visible early, while there is still time to move the window.

---

## 8. The launch-day runbook (L)

1. **7:30 Eastern.** Hit `https://api.jameskouvlis.com/api/health`, check the
   box's memory, and confirm the Cloudflare rate-limit rule is on. Bring a
   second connector up if the release plan provides one.
2. **8:00.** Release. Refresh the US App Store until the listing is live, then
   search "sunday drive" and note your rank.
3. **Open three tabs and leave them open:** App Store Connect's analytics,
   Cloudflare's analytics, and your post queue.
4. **11:00.** Post in the order given in §7.5, **one channel at a time**, so
   each one's replies get your full attention and the load arrives in waves.
   A national app takes requests from four time zones, so expect load to
   continue into the Pacific evening.
5. **Reply to everything** for three hours. Thank everyone who tries it.
   Answer "does it work in X?" honestly: "Yes, anywhere in the contiguous US.
   It scores every road on one scale, so flat country scores lower. It'll say
   so."
6. **If the server struggles** (5xx errors, slow loops): stop posting, bring
   capacity up if you have it, and post one line wherever people are asking
   ("busy, try again in a few minutes"). Don't delete anything.
7. **In the evening,** write down the numbers: installs, ratings, requests, and
   what surprised you, including where the requests came from (the Cloudflare
   country view shows only the US; the campaign links show the region).

---

## 9. Measuring without adding tracking

The privacy page promises no analytics in the app. Drive recording is
compiled out of App Store builds (the `RECORD_DRIVES` flag;
[`privacy-policy.md`](privacy-policy.md)). You don't need either:

| source | what it tells you | cost |
|---|---|---|
| **App Store Connect → Analytics** | Impressions, product page views, conversion, and installs **by source**, including each **campaign link** and each **custom product page**. That is the only regional split you get, so tag every link by region | free |
| **TestFlight** | testers, sessions, crash reports, feedback with screenshots | free |
| **Xcode Organizer** | crashes and hangs from the App Store build | free |
| **Cloudflare analytics** | requests per day through the tunnel, a proxy for drives planned, with no new logging | free |
| **TikTok Studio, Instagram Insights, YouTube Studio** | per-post views, watch time, sends, saves, follows, traffic sources, and viewer geography | free |
| **The ratings themselves** | read every review for the plains failure ("nothing scenic", "added an hour") | free |

**Every Monday, 20 minutes:** which three posts beat your median, and why;
which campaign link converted, by region; the ratings count; any review that
mentions boredom or detours; any crashes.

**Targets (goals, not forecasts):**

- **L+30: 15 ratings**, more than any scenic-driving app launched in 2026 had
  on 2026-10-18 (§2).
- **L+90: 50 ratings.**
- **Zero reviews that quote a claim back at you.** If one does, §3.4 failed.
- **Downloads:** set a target at L+7, from launch week's rate.

**Decision rules (starting thresholds):**

1. If a channel brings under 10% of campaign-attributed installs after four
   weeks of effort, halve its time.
2. If a format scores below the account's median views four posts in a row,
   drop it.
3. If short-video installs are still negligible after six weeks of three posts
   a week, move half that time to the data posts and YouTube.
4. If R2's installs per hour beat R1's for six weeks, swap their hours.
5. If two reviews in a month report a pointless detour or "nothing scenic
   here", stop all national-reach posting until the product answers it
   (§5.10, items 2 and 3).
6. Never judge a channel on a single post.

---

## 10. Risks and guardrails

| risk | likelihood | mitigation |
|---|---|---|
| **The domain lapses on 28 October 2026**, taking the API and the privacy contact with it | certain if ignored | Renew this week (§15). Renew again before L (§11) |
| **The membership renews inside the launch window** (about 3 October 2027) | certain | Renew before L (§7.4) |
| **N slips past the fall 2027 window** | medium | Gates G1 and G2 surface it early; the fallback is spring 2028 (§7.3) |
| **The Western marks fail G2** | medium; one rater, untested landscapes | R2 runs without score claims; N may slip; don't tune the constants to the marks (`national-scenery-scoring-verdict.md` §9, on `usa`) |
| **Plains users get detours that buy nothing, and say so** | high if unfixed | Go/no-go items 6 and 7; decision rule 5; never "near you" copy |
| **A New England number leaks into national copy** | medium | §3.4's table; go/no-go item 7 |
| **A featured road is closed, 4WD-only or private** | medium in the West, where the safety joins are in progress | §6.3 step 7; check every listed road in its season |
| **A post takes off and requests pile up at the server** | low, but it's the moment that counts | Load test on the national build, the rate limit, staggered posts, the stop-posting rule (§8) |
| **The R1 audience is a small share of a national listing** | certain | That's the design: R1 is where the effort is, the listing is where everyone else lands. Custom product pages per region |
| **Android users can't install** | about 40% of viewers | "iPhone" in every caption; count the requests |
| **Your home address shows up in a video** | high by default | Public starting points; check every recording (§6.4) |
| **Filming while driving** | — | Never (§6.4) |
| **A subreddit bans or shadowbans the account** | medium | Read the rules, ask the moderators, post once per sub, space posts days apart |
| **Name confusion** (WanderWay's "Sunday Drive" feature, Google Drive, the Florida dealership) | high | Direct links everywhere; check the rank on L; "Sunday Drive scenic routes". A trademark question is [`sunday-drive-naming.md`](sunday-drive-naming.md) §4's, not this plan's |
| **Music or imagery copyright** | medium | Original audio or platform libraries, your own footage, credits |
| **Obscuring Apple's logo, or comparing against Apple's routes** | low, now that you know | §6.4 and §3.4 |
| **Burnout**: ten months of a project before launch, then a weekly loop | high | Phase P is 1–2 hours a week on purpose; skipping a week is allowed |
| **Marketing breaks the privacy promise** | medium | No email waitlist without a policy update (§12, item 6), no tracking pixels, no SDKs |

---

## 11. What it costs, through N and the launch

| item | cost | needed? |
|---|---|---|
| Apple Developer Program | $99/yr; paid 2026-10-03, **next due about 3 October 2027** | yes, for any release |
| `jameskouvlis.com` renewal | about $23/yr at GoDaddy's list renewal price (third-party snapshot, May 2026; confirm at checkout). **Renewed now, it runs to 28 October 2027**, six weeks after the target L. Renew again before L, so it doesn't lapse in launch month. **About $46 to keep it to October 2028** | yes: the API hostname and the privacy contact. A release dependency, listed here because the plan fails without it |
| Hosting | $0 assumed (Oracle Always Free); the national build's sizing is the release plan's *(re-check at N)* | yes |
| Landing page and press kit | $0 (GitHub Pages, already live) | yes |
| Editing, scheduling, design | $0 (iMovie or DaVinci Resolve; the platforms' own schedulers; Canva's free tier) | yes |
| A phone mount and a second camera mount | about $15–25 each, if you don't own them | you need one to navigate legally anyway |
| The Western marks trip | gas and lodging, **paid by the scenery work**, not marketing | the footage is a by-product |
| A brand domain (`sundaydrive.co`, `sundaydrives.app`) | optional | not before L |
| **Time** | 1–2 h/week until N−12w, 3–4 h/week to N, 15–20 h in launch week, then about 5–6 h/week in season (§4.2) | the real budget |

**There is no paid marketing line in the plan, and nothing in it needs one.**

---

## 12. Decisions for the owner

1. **Target the fall 2027 window (L = Thursday 16 September 2027), with spring
   2028 as the fallback?** Recommended (§7.2, §7.3).
2. **Does a *public* TestFlight link count as "public"?** Anyone with the URL
   can join, up to 10,000 testers. It doesn't change the marketing much,
   because the plan spends nothing before L either way. If it doesn't count,
   Phase 1's beta can reach R2 testers. If it does, the beta stays invited.
3. **On camera or not?** A face and a voice help the building-in-public posts,
   though voice-over and on-screen text work too.
4. **Claim the handles now, or at N−12 weeks?** Claiming now protects the name
   (WanderWay already uses "Sunday Drive" as a feature name), and costs an hour
   and three dormant accounts. Posting waits either way. Leaning: claim now,
   post later. Accounts are yours to create; this plan creates none.
5. **R2's activation rule:** active only if G2 passes (recommended), or always,
   without score claims?
6. **A waitlist?** An email list adds a data flow the privacy policy doesn't
   cover. It costs a policy update, a storage choice and the "no tracking"
   wording's review. **Recommended: no.** Use GitHub's Watch → Releases now,
   and pre-orders if approval leaves a gap.
7. **A second Western rater?** The scoring verdict calls a second driver on
   even one landscape the cheapest way to tell "E1 is right" from "E1 agrees
   with its author". It would also let R2 claims say "two test drivers".
8. **Ship the "Nowhere" / "good miles" copy in the app before launch, or
   not?** Captions follow the UI (§3.2).
9. **Build the share card before or after L?** After is recommended. Launch
   first.

---

## 13. The target list

These are starting points, not endorsements. Read every group's rules before
posting. Subscriber counts weren't retrieved, because Reddit blocks automated
reads.

- **R1 Reddit:** r/newengland · r/boston · r/massachusetts · r/vermont ·
  r/newhampshire · r/maine · r/Connecticut · r/RhodeIsland · city subs
- **R2 Reddit** *(re-check)*: r/Colorado · r/Utah · r/Moab · r/Denver ·
  r/SaltLakeCity
- **National Reddit:** r/roadtrip · r/MapPorn · r/dataisbeautiful ·
  r/SideProject · r/iOSProgramming · r/openstreetmap · r/Miata · r/subaru ·
  r/cars
- **Facebook (R1):** New England Fall Foliage (Jeff Folger) · state and town
  groups · club groups
- **Clubs and events (R1):** Larz Anderson Auto Museum (Brookline) · BMW CCA
  Boston · PCA Northeast Region · Audi Club Northeast · Miata and Subaru groups
  · VSCCA · AACA regions
- **Tourism and byways:** R1's state tourism offices and byway organizations
  (Mohawk Trail, Kancamagus, Connecticut River Byway, Vermont's Route 100, NH
  Scenic and Cultural Byways, Maine Scenic Byways) · R2's gateway towns · FHWA
  America's Byways
- **Press:** see §5.5
- **Northeastern:** Northeastern Global News · *The Huntington News* · NUMedia
- **Tech:** Hacker News (Show HN) · weeklyOSM · OSM US · #30DayMapChallenge ·
  MacStories · 9to5Mac

---

## 14. Sources

**From this repo:** [`release-plan.md`](release-plan.md) ·
[`branding-brainstorm.md`](branding-brainstorm.md) ·
[`sunday-drive-naming.md`](sunday-drive-naming.md) ·
[`app-store-submission.md`](app-store-submission.md) ·
[`app-store-listing.md`](app-store-listing.md) ·
[`privacy-policy.md`](privacy-policy.md) and the live
[privacy page](https://jamesk1281.github.io/SundayDrive/privacy/) ·
[`rating-prompt.md`](rating-prompt.md) ·
[`load-test-oracle.md`](load-test-oracle.md) ·
[`us-map-data-findings.md`](us-map-data-findings.md) §2, §7 ·
[`driving-app-features-cost.md`](driving-app-features-cost.md) ·
[`data-sources.md`](data-sources.md) · `server/DEPLOY-oracle.md` Part 11 ·
`pipeline/score.py` · `ios/Sources/BeforeYouDriveView.swift`,
`RouteResults.swift` · `site/index.html` · `tests/test_privacy_page.py` ·
`data/processed-ne/scored_chunks.parquet` (schema, in the main checkout only).

**On the local `usa` branch only** (read with `git show usa:docs/<file>`):
`national-scenery-scoring-verdict.md` §7 (the share of km at 7+ by landscape),
§8, §9 (the Western marks plan), §10 and §11, and the verdict's plains-detour
finding; `usa-extension-feasibility.md` §8 (path C).

**Owner decisions and estimates, not in a document:** the 2026-10-18 decisions
(no public New England app; one national scale); N's estimate; the "96% liked
at 7+" figure and its basis (52 marks, one rater, New England); the CarPlay
entitlement and estimate (2026-10-08).

**The App Store census, 2026-10-18:** Apple's search API
(`itunes.apple.com/search?entity=software&country=us`) for the nine terms in
§2, and the App Store pages for WanderWay Navigation (id6807600062), Detour –
Scenic Navigation (id6496858927), Aimless Drives (id6799342576) and ROADS by
Porsche (id1438225964), for in-app purchases, privacy labels and wording.
ROADS's listing shows Usage Data and Diagnostics as "Data Used to Track You".
It doesn't say whether sign-up is required *(re-check in the app)*.

**Web, re-checked 2026-10-18:**

- Google's Ask Maps, US launch, 12 March 2026 — [Google](https://blog.google/products-and-platforms/products/maps/ask-maps-immersive-navigation/), [Droid Life](https://www.droid-life.com/2026/03/12/google-gets-new-ai-powered-ask-maps-feature/), [Travolution](https://www.travolution.com/news/google-maps-launches-ask-maps-and-immersive-navigation-with-gemini/)
- TestFlight: up to 10,000 external testers, by email or a public link, after Beta App Review — [App Store Connect Help](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers), [TestFlight](https://developer.apple.com/testflight/)
- Trail Ridge Road: usually opens around Memorial Day; opened 29 May 2026 — [National Parks Traveler](https://www.nationalparkstraveler.org/2026/05/trail-ridge-road-has-opened-rocky-mountain-national-park), [NPS (2025)](https://www.nps.gov/romo/learn/news/trail-ridge-road-opens-for-the-2025-season-timed-entry-reservations-required-for-trail-ridge-road-9-am-to-2-pm.htm)
- Blue Ridge Parkway color, by elevation, mid to late October — [NPS](https://www.nps.gov/blri/learn/nature/fall-colors.htm)
- Moab's busy seasons, spring and fall — [Visit Utah](https://www.visitutah.com/places-to-go/cities-and-towns/moab/best-time-to-visit)
- GoDaddy .com renewal, $22.99/yr (third-party snapshot, May 2026) — [DomainOffer](https://domainoffer.net/tld/com/godaddy)

**Web, carried from 2026-09-29, not re-read** *(re-check before Phase 0)*:
TikTok's US Local feed and how posts qualify; TikTok Business vs personal
accounts, links and music; carousels vs video; TikTok search; Instagram's
sends signal, Trial Reels and Map; Apple pre-orders, featuring-nomination lead
times, keyword custom product pages and in-app events; the US iPhone share;
Patch announcements; *The Huntington News* tips; New England car events;
scenic byway counts; CapCut's terms; the GitHub Student Developer Pack; the
ambient-drive genre. The links are in the New England plan's §14,
`git show 0fca74f:docs/marketing-plan.md`.

**Not checked at all** *(re-check)*: Colorado aspen timing; the R2 subreddits'
rules; the R2 press list; per-state handheld-phone laws outside New England;
whether a featuring nomination can be filed before a build is submitted.

---

## 15. This week (18–25 October 2026)

1. **Renew `jameskouvlis.com` before Wednesday 28 October.** About $23 for a
   year, which carries it to 28 October 2027. Everything else in this plan
   assumes it. (The release plan owns it; this is the reminder.)
2. **Film the late color.** Southern New England and the coast peak from mid
   October into early November. Film any drive you're making anyway, from a
   public starting point, and start the footage log (§6.5). Northern roads are
   already closing.
3. **Check that nothing of the New England launch is still queued.** If a
   featuring nomination for 22 October 2026 was filed, withdraw it in App
   Store Connect. Don't release or submit the New England build.
4. **Decide two things** (about 10 minutes each): whether a public TestFlight
   link counts as public (§12, item 2), and whether to claim the handles now
   (§12, item 4).
5. **Read §3.4 once.** It is the rule the rest of the plan hangs on.

Total: about 2 hours plus the drive. Nothing gets posted.
