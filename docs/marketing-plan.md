# Marketing plan: how Sunday Drive finds its drivers, for $0

**Status: a plan; nothing in it has been executed. Written 2026-09-29 against
`main` at `717c5bb`.** Every web fact was checked on 2026-09-29 and is listed
in §14. Platform features change every few months, so anything marked
*(re-check)* should be re-read before you build on it.

> **Committed 2026-10-04, unchanged from 2026-09-29 apart from this note.**
> Since then, two things have moved:
> - **The membership (M) arrived on 2026-10-03,** not on the 2026-09-30 that
>   §7.4's worked example assumes. Every date after M in that table is three
>   days early.
> - **The pre-submission review (2026-09-30) found two premises that do not
>   hold.** See [`pre-submission-review-verdict.md`](pre-submission-review-verdict.md)
>   §2.
>   - M-1: the northern roads this plan would showcase close for winter from
>     October 15.
>   - M-2: a viewer outside New England meets only an error.
>
> The launch-date decision (§12, item 1) is still open.

This document sits beside [`release-plan.md`](release-plan.md). That one gets
the app onto the App Store; this one gets people to it. Where the two touch
(the domain, the server, the listing), this one points at the release plan
instead of repeating it.

**The constraints it was written to:**

- **$0 marketing budget.** No ads, no paid placements, no paid tools. The only
  money anywhere in it is the $99 Apple membership and the domain renewal that
  the release needs anyway (§11).
- **The app is completely free.** No price, no in-app purchase, no
  subscription, no ads. There is no funnel after the install, so success is
  installs, drives, ratings, and people telling people.
- **New England only, iPhone only, one server, one person** — who is also a
  student.

---

## 0. The plan on one page

1. **Getting onto the store gets you nothing by itself.** At least eight
   scenic-driving apps launched in 2026. Six have zero ratings, and the best
   has 14 (§2). What separates you from them has to be distribution.
2. **Short video is the engine, and the TikTok instinct was right.** Post the
   same clips to TikTok, Instagram Reels and YouTube Shorts, cut from one drive
   a week. Since February 2026 TikTok has had a US *Local* feed, and Instagram
   has a Map, so a location-tagged New England post can reach New Englanders
   specifically (§5.1).
3. **One-shot channels are the ignition.** A press story, one launch post per
   subreddit, Show HN, and Apple's featuring nomination. You get roughly one of
   each, so spend them when the app is on the store and in season (§7).
4. **The advantage nobody can copy is the data.** Nobody else has a scenery
   score for 146,811 miles of road. "The ten best-scoring drives in Vermont"
   is a post no competitor can make (§6.3).
5. **"Free, no account, no ads, no tracking, open source"** opens doors that
   stay shut to commercial self-promotion. Say it, and keep it true (§3.3).
6. **The earliest realistic launch is Thursday 22 October 2026**, which catches
   the last peak weekend in southern New England. If it slips past about 27
   October, release quietly and save the seasonal one-shots for a **spring
   opener (Memorial Day weekend, 29–31 May 2027)** and **foliage 2027** (§7).
7. **Before posting anything that could take off:** renew the domain (it
   expires 28 October), load-test the server, and never film a loop that
   starts at your house (§10).

**If you only do five things:** renew the domain; film every drive this
October; make one data post; post three times a week from one drive; and tag
the location on every post.

### Terms used below

| term | meaning |
|---|---|
| **L** | Launch day: the day the app goes live on the App Store. §7 dates everything relative to it (L-14 is two weeks before) |
| **ASO** | App Store Optimization: the name, subtitle, keywords, screenshots and video that decide whether people find you in App Store search and install |
| **One-shot channel** | Somewhere you can realistically announce once: a press story, the "I built this" post in a subreddit, Show HN |
| **Repeatable channel** | Somewhere you can post every week indefinitely: your video accounts, answers in "where should I drive?" threads |
| **Campaign link** | An App Store link with a tag (`ct=tiktok`) that lets App Store Connect tell you which channel an install came from |
| **CPP** | Custom product page: an alternative version of your App Store page, with different screenshots and text, that you can point one channel at |

---

## 1. The constraints, and what each one forces

| constraint | what it forces |
|---|---|
| $0 budget | Your time is the budget. Everything has to compound (be findable by search: YouTube, TikTok search, App Store search, Pinterest) or be a one-shot worth spending |
| The app is free | There is no launch discount, referral credit or "premium" tier to promote. In exchange, the install costs nothing, and a free, ad-free, open-source tool is welcome in places that ban commercial promotion (§3.3) |
| New England only (about 4.5% of the US) | Every post has to be anchored somewhere real: a town, a road, a landmark, a location tag. That is exactly what TikTok's Local feed and Instagram's Map reward. Say **"New England only"** in every caption, or people elsewhere will install it and leave one-star "doesn't work" reviews |
| iPhone only (about 58% of US users) | Roughly four in ten people who see a post can't install it. Say **"iPhone"** in the caption. Count Android requests as a signal; don't promise anything |
| One server: one process, 4 threads, 2 cores (`server/serve.py:44`) | A route takes about 0.8 s and a loop about 3.9 s on its first call. Stagger launch posts across days, and load-test before L (§10) |
| One person, a student | Budget 4–6 hours a week, in batches. A plan that needs daily posting will be dead by November |
| Seasonal demand | Foliage is the peak, and it is happening now. Winter is the trough, spring and summer are a second season, and foliage 2027 is the main event |

---

## 2. The market, measured

Counted with Apple's App Store search API (US store) on 2026-09-29. The search
is ranked by relevance rather than exhaustive, so these are **"at least"**
figures. Ratings stand in for use; they are not download counts.

**Scenic-driving apps launched in 2026:**

| app | launched | ratings |
|---|---|---|
| Vibe Drive | 2026-01-30 | 0 |
| RevRoutes Find Scenic Drives | 2026-05-14 | 0 |
| Routes – Best Driving Roads | 2026-06-06 | 0 |
| Scenra: Scenic Road Trips | 2026-07-02 | 0 |
| Pleasant Routes | 2026-07-10 | 14 |
| Scenic Way | 2026-07-18 | 0 |
| Joyride: Roads & Drives | 2026-07-28 | 0 |
| **Aimless Drives** (loops of 30/60/90/120 min) | **2026-09-02** | **2** |

**The apps that have users are old:** Roadtrippers (2014) has 61,501 ratings,
Scenic Motorcycle Navigation (2016) 7,450, and ROADS by Porsche (2018) 261.
**This season's foliage apps are empty too:** Fallcast (launched 2026-09-17)
has 0, Explore Fall 7, and FoliageBeat 5.

**What it means:**

- A scenic-route app was apparently a common idea this year, and shipping one
  has bought nobody anything yet. **Fifteen ratings would make you the most-used
  new entrant.**
- Aimless Drives is your loop mode, shipped a month before you, and it has two
  ratings. The loop space is not taken. It is empty.
- The differentiator, per [`branding-brainstorm.md`](branding-brainstorm.md)
  §2: **every road measured, not submitted**, and **the dial plus the loop**.
  The established competitors either sell community-submitted routes to
  motorcyclists or just avoid highways. The 2026 entrants' listings were not
  read for this plan, so read the three nearest before claiming to be "the
  only" anything.
- **Searching for the name is noisy.** Today, `sunday drive` in the App Store
  returns Google Drive, Garmin Drive and driving games, and `sundaydrive.com`
  is a Florida car dealership
  ([`sunday-drive-naming.md`](sunday-drive-naming.md) §3). On L, check where
  you rank for "sunday drive". Until you rank first, every post needs a direct
  link, or the words "Sunday Drive scenic routes".

---

## 3. Positioning and message

### 3.1 Adopted, not reinvented

[`branding-brainstorm.md`](branding-brainstorm.md) §2 and §5 settled this, and
they hold:

- **The thesis:** every navigation app optimizes for less time, and this is the
  only one that asks you to spend more. **Proudly anti-efficiency.**
- **The voice:** unhurried, dry, quietly confident. No exclamation marks, no
  "supercharge". That happens to suit the slow content that does well on every
  platform: cozy fall, slow living, the drive with no destination.
- **The subtitle (decided):** *The scenic route, on purpose*
  ([`app-store-submission.md`](app-store-submission.md)).
- **The one-liner:** Every road in New England, scored for beauty. Move one
  slider to trade minutes for the view.
- **The loop hook:** Ninety minutes, nowhere to be. We'll bring you home the
  pretty way.
- **The credibility line:** Built on open data. Every road measured, not
  crowdsourced.

### 3.2 Say what's on the screen

Captions should use the app's own words, so the video and the app agree. The
results card says **"Scenic adds 49 min"** (`ios/Sources/RouteResults.swift`),
and the loop is labelled **"Loop"**, with a duration. The branding doc's
"Nowhere" and "good miles" never shipped to the UI. Ship them first, or leave
them out of the videos.

### 3.3 The free-app message, and why it's worth more than it looks

- **Say it plainly:** *Free. No account, no ads, no tracking. Open source.*
  Every word is true today and is on the live
  [privacy page](https://jamesk1281.github.io/SundayDrive/privacy/).
- **Answer the catch before anyone asks.** Free apps get "what's the catch?"
  The honest answer is the story. A Northeastern student built it, the code is
  public, the server runs on a free tier, and the app itself lists what it
  cannot do (the "What it does not do" section of
  `ios/Sources/BeforeYouDriveView.swift`).
- **It opens doors.** Local subreddits and Facebook groups that remove
  commercial promotion will often allow a free, ad-free local tool from a real
  community member, especially if you ask the moderators first. A startup can't
  make that request, and you can.
- **Keep it true.** Any analytics SDK, account system, ad or price breaks the
  message and reopens the privacy decision (`release-plan.md` §8, Decision 3).
  That is why every measurement in §9 uses numbers that Apple, Cloudflare and
  the platforms already give you. It is also why the landing page follows the
  rule that `tests/test_privacy_page.py` enforces on the privacy page: it loads
  nothing from anyone else's server.
- **Where not to say it:** Apple rejects in-app event metadata that mentions
  price, "free" included (§5.7). The listing already shows the price, so don't
  spend keyword bytes on it either.

### 3.4 What not to claim

From [`branding-brainstorm.md`](branding-brainstorm.md) §5: no "best route", no
"most scenic", nothing that implies validated ground truth. **"Scored" and
"measured" are defensible. "Beautiful, guaranteed" is not.** Rank drives "by
our score", never as fact. Compare only against **the app's own fastest
route**. Never compare against Apple's routes (ADPLA Attachment 6 §2.3, see
[`legal-and-ip-audit.md`](legal-and-ip-audit.md)), and don't name other apps in
the listing (App Store guideline 2.3.7).

---

## 4. Who it is for

| audience | when | where they are | what to show them | priority |
|---|---|---|---|---|
| **New England weekend drivers**: suburban, 25–65, with a car and a free Sunday | all year, peaking spring to fall | Facebook town and state groups, state subreddits, Instagram, local news | The loop: an hour, nowhere to be, home the pretty way | **1, the core** |
| **Leaf-peepers and visitors**, many from New York, New Jersey and further | mid-September to early November | Facebook foliage groups, Instagram, Pinterest, TikTok (a national audience is *useful* here), travel press | The trade: "Scenic adds 20 min", and you skip I-93 between foliage spots | **2, seasonal and national** |
| **Car enthusiasts**: Miata, Porsche, BMW, Subaru, classic cars | April to November | clubs, Cars & Coffee meets, model subreddits, Instagram | Measured curvy roads, and routing a club drive | **3, amplifiers** |
| **Map and data people** | any time, especially November | r/MapPorn, r/dataisbeautiful, Hacker News, the OpenStreetMap community | The instrument: the heatmap, the method, the open repo | **4, credibility rather than users** |
| **Motorcyclists** | April to October | New England Riders, ADVrider, motorcycle Facebook groups | "Every road measured", as a complement to their curated routes | **5, incumbents own this**: Scenic Motorcycle, calimoto, Kurviger, REVER, and NER's own BONE routes. Don't lead with it |

---

## 5. Channels: the playbooks

Ranked by what each returns per hour for a free, New England-only app. Each one
has *what*, *how*, *cadence* and *the trap*.

### 5.1 Short video: TikTok, Instagram Reels, YouTube Shorts (the engine)

**Setup, once, about an hour:**

- **One handle on all three.** The bare name is probably taken. Pick one that
  is free everywhere (`sundaydrive.app`, `sundaydriveapp`,
  `takethesundaydrive`), and check all three on the same day.
- **TikTok: a Business account.** It can show a clickable website link at any
  follower count, while personal accounts need 1,000 followers first. The cost
  is that you only get TikTok's Commercial Music Library. That costs you less
  than it sounds: TikTok's general music licences don't cover promotional
  videos from either kind of account.
- **Instagram: a Professional (Creator or Business) account.** It gives you
  Insights, and once you pass 200 followers it unlocks *Trial Reels*
  (described below).
- **YouTube: one channel**, for both Shorts and the long-form drives (§5.2).
- **Where the links point:** the landing page (§5.7) until L, then an App Store
  campaign link.

**The levers, and what each one costs:**

| lever | where | cost | why it works |
|---|---|---|---|
| **Tag the location on every post** | TikTok, Instagram | 5 s | TikTok's US Local feed (live since February 2026) picks posts by location, topic and recency, and a creator who tags a location becomes eligible for it. Instagram's Map (US, since August 2025) collects location-tagged posts. This is how a national platform finds New Englanders. *(Re-check: viewers have to opt in to both, and TikTok publishes no audience size, so don't build the strategy around it.)* |
| **Put the keyword in the first on-screen text, and say it out loud** | TikTok above all | 0 | TikTok search reads on-screen text, speech, captions and hashtags. Foliage searches spike every fall, and a video that matches a search keeps collecting views long after its first run. Use 3–5 hashtags, not 30 |
| **Carousels for lists** | TikTok, Instagram | 20 min | Photo carousels get about the same reach as video but many more likes, comments and saves. Five or six slides is the reported sweet spot. "Top 5 drives in Connecticut" should be a carousel, not a video |
| **"Send this to whoever's driving Sunday"** | Instagram | 0 | The head of Instagram says sends (shares by DM) are the strongest signal for reaching people who don't follow you. Ask for the send, not the like |
| **Trial Reels** | Instagram | 0 | Once you have 200 followers, a Reel can go to non-followers first, and a flop doesn't count against your account. Test two hooks for the same drive |
| **Reply to comments with a video** | TikTok, Instagram | 10 min each | "Comment your town", then reply with a video of a loop from that town. Every reply is a demo, it's personal, and it turns into a series your audience directs |
| **One file on three platforms, exported clean** | all | +10 min | Export from your editor, not from TikTok. Instagram's recommendation guidelines demote Reels that visibly carry another app's watermark |
| **Collab posts and tags** | Instagram, TikTok | 1 min | Tag the orchard, the cider mill, the general store or the club. They reshare to a local audience that is already in the market |
| **Link each Short to its long-form drive** | YouTube | 1 min | A Short can link one related video, so point Shorts viewers at the full ambient drive |

**Cadence:** at least 3 posts a week, cut from one drive (§6). For a one-person
account, consistency beats volume.

**Music:** original audio (road noise, voice-over), TikTok's Commercial Music
Library, Meta's Sound Collection or YouTube's Audio Library. Never put a
trending commercial track on a post that promotes the app.

**Editing:** iMovie or DaVinci Resolve, both free. **Skip CapCut for footage
you want to own.** Its terms of service changed on 12 June 2025 to take a
perpetual, irrevocable licence to whatever you upload. Canva's free tier covers
the carousels, and the GitHub Student Developer Pack lists 12 months of Canva
Pro *(re-check at education.github.com)*.

**The trap:** chasing views. A video with 200,000 views from Texas is worth
less than one with 2,000 views from Worcester. Watch installs per campaign link
(§9), not views.

### 5.2 YouTube long-form: the ambient drive (the easiest evergreen)

**What:** 30 to 90 minutes of a single drive. Mount the camera, don't talk,
edit gently, and add chapters by town. It is an established genre: channels
such as World Driving Tours and the 4K Relaxation Channel post multi-hour
silent drives, some with millions of views, that people watch as background.

**Why it's efficient:** you already shot the footage for the shorts, YouTube
search keeps sending viewers for years, and the description can carry the
route, the app link and the credits:

```
A 72-minute loop from Concord, MA through Carlisle and Harvard, picked by
Sunday Drive — a free iPhone app that scored every road in New England for
scenery. New England only. [campaign link]

0:00 Concord · 12:40 Carlisle · …
Route data © OpenStreetMap contributors. Music: [library credit].
```

**Cadence:** one every week or two, whenever the footage is good.
**The trap:** a shaky or badly exposed mount. Test it on a short drive first.

### 5.3 Reddit (the best free geography there is)

**Where:** r/newengland, r/boston, r/massachusetts, r/vermont,
r/newhampshire, r/maine, r/Connecticut, r/RhodeIsland, and city subs like
r/worcester. For hobbyists: r/Miata, r/subaru, r/cars. For data: r/MapPorn and
r/dataisbeautiful. For builders: r/SideProject and r/iOSProgramming.

**Two formats:**

1. **The data post, which you can repeat:** "I scored every road in Vermont for
   scenery using open data. These are the 10 best-scoring drives." A map, the
   list, the method in one paragraph, and the credits. Do one per state per
   season: six states times three seasons is 18 posts a year, and no two are
   alike. Put the app in a comment, and only where the sub allows it (§6.3).
2. **The launch post, one per sub:** "I'm a Northeastern student, and I built a
   free, open-source iPhone app that finds the scenic way. No ads, no account."
   Post it on L or L+1, in the one or two subs where the data post did best.

**How:** read every sub's rules. **Message the moderators before the launch
post**: say who you are and that the app is free, open source and ad-free, then
ask. Post in the morning, US Eastern time, and answer every comment for the
next two hours. Answer "scenic drive from X?" threads with a real route,
whether or not you mention the app.

**The trap:** posting the same thing to eight subs in one day, which is how
accounts get flagged. Space posts days apart.

### 5.4 Facebook groups (where the leaf-peepers actually are)

**Where:** the New England foliage groups; the obvious one is the *New England
Fall Foliage* community linked to Jeff Folger, whose jeff-foliage.com publishes
the season's forecasts. Also state and town groups, and car-club and motorcycle
groups.

**How:** join as yourself, contribute before you promote, ask the admins, then
share the weekly drive with a photo and the route. This audience skews older
and will search the App Store by name, which is why the name check in §2
matters.

**Cadence:** one or two groups a week, rotating.
**The trap:** a post that is only a link. Lead with the photo and the drive.

### 5.5 Press and newsletters (one story each, tied to a season)

**The hook calendar:**

| when | the hook |
|---|---|
| October 2026 | "Local student's free app finds the prettiest way to see the leaves" |
| November 2026 (off-season) | "We scored every official scenic byway in New England. Here's how they rank." Vermont has 1 national and 9 state byways, New Hampshire 20, and Massachusetts 3 national ones. **Rank them with `c_scenic_tag` left out.** That component *is* the byway designation (`pipeline/score.py:12`, from OSM route relations), so with it included the designation grades itself, and "this byway scores below the road next to it" would be understated |
| Memorial Day 2027 | "The summer drives an algorithm picked" |
| September 2027 | Foliage, now with a year of data and users behind it |

**Places you can publish yourself, no pitch needed:**

- **Patch:** anyone can post an announcement or a press release to a town's
  Patch site for free. Do one for every town you've featured.
- **Northeastern:** Northeastern Global News (the university's newsroom), *The
  Huntington News* (the student paper; tips go to huntnewsnu.com/tips) and
  NUMedia. Your own university is the easiest pitch you will ever make.

**Pitch targets:** Boston.com, Universal Hub, Axios Boston and *The Boston
Globe*; on TV, WCVB (its *Chronicle* covers New England travel), NBC10 Boston,
WBZ and NECN; on radio, WBUR and GBH. Regional magazines: *Yankee* / New
England Today (which runs a peak-foliage map and scenic-drive lists every
year). Vermont: *Seven Days*, VTDigger. New Hampshire: NHPR, *New Hampshire
Magazine*. Maine: *Down East*, *Portland Press Herald*, *Bangor Daily News*.
Connecticut: CT Insider, CT Public. Rhode Island: *The Providence Journal*,
The Public's Radio. Tech press: MacStories and 9to5Mac (both take tips), which
like native, privacy-respecting apps.

**The pitch, under 150 words:**

```
Subject: A student scored every road in New England for scenery

Hi [name] — I'm a [year] at Northeastern. I built Sunday Drive, a free
iPhone app that scores all 146,811 miles of road in New England for scenery
from open map data, then routes you the pretty way instead of the fast
way. Give it an hour and it plans a loop home.

It's free, with no ads and no accounts, and the code is public. With peak
color in [region] this weekend, your readers might like the five
best-scoring drives near [city] — the list and a map are attached.

On the App Store now: [link]. Press kit: [link]. Happy to talk, or to take
you on the drive.
```

**The press kit (a section of the landing page):** the icon, 5 screenshots,
the 30-second preview video, a photo of you, the one-paragraph story, the
numbers (146,811 miles; 942,448 scored road segments; six states), the credits,
and contact details.

**The trap:** pitching before anyone can download it. A story that ends
"coming soon" converts nobody, and it spends your one shot.

### 5.6 Clubs, events, destinations and tourism (other people's audiences)

- **Car clubs:** offer to route a club's next drive, then ask to film it and
  post it as a Collab. Try BMW CCA Boston, PCA Northeast Region, Audi Club
  Northeast (it ran a "Skyline Drive" through the mountains in June), Miata and
  Subaru groups, and the vintage clubs (VSCCA, AACA regions). Classic-car
  owners literally go on Sunday drives.
- **Events:** the Larz Anderson Auto Museum in Brookline, a short trip from
  campus, runs cars-and-coffee meets and scenic cruises in season. **Southern
  New Hampshire Cars and Coffee meets on Sunday 18 October 2026** in
  Manchester, NH, inside the beta window (§7) *(re-check)*. Bring the TestFlight
  QR code on your phone; you don't need printed flyers.
- **Motorcycles:** New England Riders (newenglandriders.org) publishes its own
  curated BONE routes. Approach it as a complement, not a competitor.
- **Destinations:** orchards, cider mills, farm stands and general stores. End
  a drive at one and tag it, and it will usually reshare.
- **Tourism and byways:** state tourism offices publish foliage reports, so tag
  them on posts from their state. Give byway organizations (the Mohawk Trail,
  the Kancamagus, the Connecticut River Byway, Vermont's Route 100) the
  byway-ranking piece first.
- **Foliage forecasters:** Jeff Folger and New England Today's foliage map.
  "Their forecast, our routes" is a natural collaboration.

### 5.7 The App Store itself (free tools most indie apps never touch)

| tool | what to do | when |
|---|---|---|
| **Landing page** | Replace the redirect in `site/index.html` with a real page: what the app is, 3 screenshots, "New England · iPhone · free", the App Store badge (the TestFlight link before L), the press kit, credits and contact. **It doubles as the Support URL that App Store Connect requires.** It loads nothing external, by the same rule the privacy page's test enforces | before B |
| **Keywords** | **100 bytes**, no competitor names, and nothing already in the name ("sunday", "drive") or the subtitle ("scenic", "route"), since both are indexed. One candidate at 95 bytes: `foliage,fall,leaf,peeping,loop,backroads,byway,autumn,curvy,road,trip,new,england,vermont,maine`. Apple combines separate terms into phrases, so "new,england" reaches "new england". Re-measure the bytes before pasting | before S |
| **Screenshots and preview video** | The first three screenshots decide most installs. Show the trade ("Scenic adds 12 min"), a loop, and the road itself. The preview video can run up to 30 s, cut from your footage | before S |
| **Featuring nomination** | App Store Connect → Featuring Nominations → *App Launch*. **At least 2 weeks before L**, and Apple suggests up to 3 months ahead for wider consideration. Tell the story: a student, open data, New England, the season | L-14 at the latest |
| **Manual release** | Choose "Manually release this version", so that approval doesn't mean launch and you pick the moment | at S |
| **Pre-orders** (only if there's a gap) | Only if approval lands two or more weeks before L. A pre-order works as a waitlist that collects no data and installs automatically on release day. It needs App Review first and can run 2–180 days | if the gap exists |
| **Promotional text** | 170 characters above the description, **editable any time without review**. Change it with the season: "Peak color in the Berkshires this weekend. Try a 90-minute loop" | weekly in season |
| **Custom product pages** | Up to 70 of them, and since July 2025 they can carry keywords and show up in organic search. Build three (*foliage*, *loops*, *curvy roads*) and point each channel at the one that matches. Keywords assigned to a page come out of your 100 bytes; they don't add to them | L+7 |
| **Campaign links** | One per channel: `https://apps.apple.com/app/apple-store/id<APPID>?pt=<PROVIDER_ID>&ct=tiktok&mt=8` | before L |
| **In-app events** | Free cards that show up in search and editorial, lasting up to 31 days. **They need real in-app content**, and metadata that mentions "free" gets rejected. They become possible once the app has something seasonal, such as a "peak foliage" loop collection filed as a *New Season* | foliage 2027 |

### 5.8 Tech and open-source communities (credibility, not installs)

- **Show HN** (Hacker News): "Show HN: Sunday Drive – I scored every road in
  New England for scenery". Link the repo and a short write-up of the method.
  It's a one-shot, but it isn't seasonal, so it can wait for the off-season.
- **The OpenStreetMap community** (weeklyOSM, OSM US): a project built on their
  data, and routing by it, is news to them. It even closes a loop: green areas
  are mapped 3.3× more thinly in Maine than in Rhode Island, so better mapping
  there directly improves Maine's scores.
- **#30DayMapChallenge** runs every November, one map a day on a set theme. The
  heatmap and the route maps fit several of the days.
- **r/MapPorn and r/dataisbeautiful:** the per-state maps, with credits (§6.4).

### 5.9 Pinterest (optional, evergreen)

Trip planners use it as a search engine, and fall trips get planned in August
and September. Pin the same carousels and maps, linked to the landing page.
Once the carousels exist, it takes little effort. Start before foliage 2027,
not now.

### 5.10 The product as a channel (engineering asks, ranked by leverage)

This is code, so it sits outside the marketing budget. Adopt items into
[`roadmap.md`](roadmap.md) one at a time; this list doesn't schedule them.

1. **A rating prompt at the right moment.** Call SwiftUI's `requestReview`
   after a completed drive, **once parked**, never during navigation. The
   system shows it at most three times a year. Ratings drive both ranking and
   conversion, and the bar in §2 is 15. A few hours of work.
2. **A friendlier out-of-region message.** Today the server says "point is
   outside the covered road network (currently New England)"
   (`server/app.py:262`), and the app shows that text word for word
   (`RouteService.swift`, `ServiceError.server`). Something like "Sunday Drive
   only covers New England for now" would do. It's server copy, so it ships
   with a deploy and no App Review. Minutes.
3. **Share this drive.** A `ShareLink` with an image of the map and the card
   ("72 min · Scenic adds 18 min · Sunday Drive, free on the App Store").
   **Trim the first and last kilometre, because a loop starts "From here",
   which is usually home.** Nothing like it exists today: there is no
   `ShareLink` in `ios/Sources`.
4. **"Hey Siri, take me on a Sunday drive"**, through App Intents, starting a
   loop. It's on-brand and easy to demo, and adopting Apple's own frameworks is
   the kind of thing App Store editors look for.
5. **An opt-in weekly reminder:** "It's Sunday. Ninety minutes, nowhere to be?"
   It's a local notification, so no server and no data.
6. **A web preview**, so Android users, desktop readers and journalists can try
   routes. The API already allows cross-origin requests (`CORS(app)`), but a
   website that sends coordinates is a new privacy surface to document before
   anything else. Later.
7. **CarPlay.** Expect people to ask for it. It is blocked rather than
   expensive ([`driving-app-features-cost.md`](driving-app-features-cost.md),
   sentence 6).

---

## 6. The content system: one drive makes a week

### 6.1 The weekly loop (about 4–6 hours)

| when | what | time |
|---|---|---|
| Thursday | Pick the drive: a loop or route from a **public starting point**. Check the forecast and the state foliage report | 15 min |
| Saturday or Sunday | Drive it. The phone sits in its mount, screen-recording the app. A second camera films the road (a passenger, an old phone, a second mount). Take five stills at stops | the drive |
| Sunday | Edit 1 long-form video, 3 shorts (15–35 s each) and 1 carousel (5–6 slides). Export clean vertical files | 2 h |
| Monday | Schedule everything in TikTok Studio, Meta Business Suite (Instagram and Facebook) and YouTube Studio, which are all free. Write captions and add location tags | 30 min |
| Every day | Reply to comments, especially in the first hour after each post | 15 min |
| Monday | Review last week's numbers (§9) | 20 min |

**What one drive yields:** 1 long-form YouTube video, 3 shorts posted on three
platforms each, 1 carousel posted on two, 1 Facebook post, and stills for
Reddit, press and the App Store. That is about 13 posts.

### 6.2 Twelve formats, with hooks

| # | format | the first two seconds | where |
|---|---|---|---|
| 1 | **The Sunday Drive**, the weekly episode | the best frame, over "This week's drive, picked by an algorithm" | everywhere |
| 2 | **The trade** | the card, "Scenic adds 12 min", then "Worth it?" | TikTok, Reels |
| 3 | **The top 5 in a state** | "The 5 best-scoring drives in Connecticut" | carousel |
| 4 | **Comment your town** | "You said Nashua. Here's an hour, the pretty way" | reply videos |
| 5 | **The algorithm's worst pick** | "My app thought this was scenic" (an industrial park) | TikTok |
| 6 | **Building in public** | "I scored 146,811 miles of road. Here's how" | TikTok, Shorts |
| 7 | **The map** | every road in Vermont animating in, colored by score | everywhere, plus Reddit |
| 8 | **The ambient drive** | no hook: it's 45 minutes of drive | YouTube |
| 9 | **Stitching a foliage video** | their Vermont clip, then "here's the pretty way there from Boston" | TikTok |
| 10 | **A club or destination drive** | "We routed the Miata club's fall drive" | Collab |
| 11 | **The honest ETA** | "Is the scenic route really slower? Here's the math" | TikTok, Shorts |
| 12 | **Peak this weekend** | "Peak color in the Monadnocks this weekend. Here's a loop through it" | everywhere, in season |

**The mix:** about 40% drives (formats 1, 8 and 12), 25% data (3 and 7), 20%
building in public (5, 6 and 11) and 15% community (4, 9 and 10).

**The caption template:**

```
Scenic drive from Worcester, MA — a 60-minute loop through the Quabbin hills.
Picked by Sunday Drive, a free app that scored every road in New England.
iPhone · New England only · link in bio
#newengland #scenicdrive #fallfoliage #massachusetts #sundaydrive
```

**On every post:** a location tag, the keyword in the first on-screen text,
"New England only" and "iPhone" in the caption, and one call to action (send,
comment or save).

### 6.3 The flagship: a per-state top 10 from your own data

The data supports it. `scored_chunks.parquet` in `data/processed-ne` has
`name`, `ref`, `highway`, `length_m`, every beauty component and the final
`score` for all 942,448 segments. The method, in outline:

1. Group segments into named stretches (by `name`, or by `ref` where there is
   no name), and keep stretches with at least about 8 km of drivable road.
2. Rank them by length-weighted mean `score`.
3. Assign each stretch to a state using the Census cartographic state
   boundaries, which are public domain.
4. **Rank within each state, never across states.** The app's own "What it
   does not do" section says the terrain component saturates north of
   Massachusetts, and green areas are mapped 3.3× more thinly in Maine. A
   New England-wide top 10 would be quietly biased.
5. Check each state's top 10 against your own driving marks. Cut anything
   that's obviously wrong, and say so in the post ("#7 surprised me"). If the
   list is mostly official byways, re-rank without `c_scenic_tag` to see
   whether those roads earn their place on their own, and say which ranking
   you used.

Miles per state, for the posts: MA 42,116 · ME 37,263 · CT 24,668 · NH 19,967
· VT 17,730 · RI 6,762. They come from the network census in
[`driving-app-features-cost.md`](driving-app-features-cost.md), converted from
kilometres.

### 6.4 Rules for every piece of content

- **Never film while driving.** All six New England states ban holding a phone
  while driving. A passenger films, or the camera is mounted and started before
  the car moves. You need a mount to use a navigation app legally anyway.
- **Never show home.** Loops start "From here". Start demo loops from a town
  green or a parking lot, and check the first and last seconds of every screen
  recording.
- **Credit the map.** Anything drawn from the data is an ODbL *Produced Work*,
  so "© OpenStreetMap contributors" has to be visible in the image itself, not
  just in the caption. Add the ESA WorldCover and elevation credits whenever
  those layers show. The exact wording is in
  [`data-sources.md`](data-sources.md) and `ios/Sources/AboutView.swift`.
- **Leave Apple's corner alone.** Don't crop or put captions over the Apple
  Maps logo and the Legal link in screen recordings.
- **Use your own footage.** No Street View, no Google imagery, and no other
  creators' clips outside TikTok's own stitch and duet.

---

## 7. The timeline, relative to deployment

### 7.1 The milestones

| code | milestone | what it depends on |
|---|---|---|
| **M** | Apple Developer Program membership active | $99; usually the same day (`release-plan.md` §11) |
| **B** | TestFlight public link live (up to 10,000 testers) | a build and Beta App Review |
| **S** | App Store submission | the §10 artifacts in `release-plan.md` |
| **A** | Approved | App Review |
| **L** | **Launch: a manual release, on a Thursday** | A, plus the go/no-go check in §7.3 |

**Why Thursday:** the app is for weekends. Launch on a Thursday, and the first
weekend is when people use it.

### 7.2 Phase by phase

**Phase 0: foundations (M to B, about L-28 to L-15)**

- [ ] **Renew `jameskouvlis.com`. It expires 28 October.** The API hostname,
      the privacy contact (`privacy@jameskouvlis.com`) and every build depend
      on it.
- [ ] Buy the membership, and reserve the name in App Store Connect.
- [ ] Claim the handle on TikTok (Business), Instagram (Professional) and
      YouTube.
- [ ] Build the landing page (§5.7), with the TestFlight link and a press-kit
      section.
- [ ] Get a mount, and film the first two drives.
- [ ] **Start posting before launch**: drives, building in public, the map. The
      account needs a few weeks of history by L.
- [ ] Make the first data post, for one state (§6.3). It doesn't need the app,
      and it tests whether anyone cares.

**Phase 1: beta (B to L-1, about L-14 to L-1)**

- [ ] Share the TestFlight public link with about 50–200 people: Northeastern,
      one or two subreddits ("free beta for foliage season"), one car club.
- [ ] Show the QR code on your phone at a Cars & Coffee meet.
- [ ] Watch the server and fix what breaks. Ask testers for one-line quotes you
      can use, with their permission.
- [ ] **Submit the featuring nomination by L-14.**
- [ ] Run the load test and set the Cloudflare rate limit
      (`server/DEPLOY-oracle.md`, Part 11). Decide whether the laptop runs as a
      warm, gated second connector during launch week
      ([`hosting-independent-review.md`](hosting-independent-review.md)).
- [ ] Prepare the screenshots, preview video, keywords and campaign links, and
      ship the out-of-region copy (§5.10, item 2).
- [ ] Submit (S) with manual release selected. Draft the press list and the
      pitch.
- [ ] **L-7: the go/no-go check (§7.3).**
- [ ] The day approval (A) lands, send the pitches ("available Thursday").
- [ ] L-1, pre-flight: `api/health`, the box's memory, the rate limit, the
      domain, the listing, every link, and all drafts ready.

**Phase 2: launch week (L to L+7)**

| day | what | notes |
|---|---|---|
| **L (Thursday)**, 8 am | Release in App Store Connect. Wait until the listing is actually live in the US store, then search "sunday drive" and note your rank | this can take hours |
| L, 11 am | Your own accounts, then Northeastern's channels, then **Reddit launch post #1** (in the sub where the data post did best), then Patch announcements | stagger them, and reply to everything until 2 pm |
| L, all day | Check Cloudflare's request graph and the box every hour | stop posting if errors climb (§8) |
| L+1 (Friday) | Reddit launch post #2 (a second state), the Facebook groups. Tell testers it's live and ask for an honest rating. **Never** offer anything in return, and never ask for five stars | |
| L+2 to L+3 (the weekend) | The launch-weekend Sunday Drive, while people are actually out driving | |
| L+4 (Monday) | Show HN, on a weekday morning US time | it isn't seasonal, so it can move to the off-season if the week is full |
| L+7 | First numbers (§9): which link converted and which post worked. Set the download target from this week's rate | |

**Phase 3: the first month (L+8 to L+30)**

- [ ] Keep the weekly loop going (§6.1): 3 or more posts a week, every week.
- [ ] Do the data posts for the other states, one a week.
- [ ] Ship the first update (fixes and the rating prompt, plus the share card
      if it's ready), then file a featuring nomination for *App Enhancements*,
      two weeks ahead.
- [ ] Build custom product pages for the three audiences and point the links at
      them.
- [ ] Do two club or destination collaborations.

**Phase 4: compounding (L+31 to L+90)**

- [ ] Build the YouTube library from the season's footage.
- [ ] Publish the byway-ranking piece (§5.5).
- [ ] Spend the off-season one-shots: Show HN, #30DayMapChallenge, the OSM
      community.
- [ ] Cut the weakest channel, using the decision rules in §9.
- [ ] Plan the spring opener: the feature, a list of footage to shoot, the
      press list.

**Seasonal beats after L+90:**

| when | beat |
|---|---|
| mid-February 2027 | Featuring nomination for the spring update, 3 months ahead of Memorial Day |
| **29–31 May 2027** | **The spring opener** (Memorial Day weekend): a second press moment, "summer drives", an update |
| mid-June 2027 | Featuring nomination for foliage 2027, 3 months ahead |
| **mid-September to early November 2027** | **Foliage 2027, the main event.** A year of footage and ratings behind you, plus a seasonal in-app event if the app has seasonal content by then |

### 7.3 The go/no-go check at L-7

Launch on the planned Thursday only if **all five** hold:

1. The app is approved, or submitted early enough that a normal review lands
   before L-1.
2. The load test passed, and the rate limit is on.
3. The domain is renewed.
4. The beta has no known crash.
5. The landing page and the campaign links are live.

**If any one fails:** release quietly once approved (the listing, your own
channels, the beta testers), and this year **spend only the one-shots that
aren't seasonal**: Show HN, the OSM community, #30DayMapChallenge. Hold the
seasonal ones (local press, the state-subreddit launch posts, the foliage
groups) for the spring opener. That fallback is a good plan in its own right,
not a failure. Most of what this document builds pays off in 2027.

### 7.4 A worked example on real dates

This assumes the membership is bought on 30 September 2026.

| milestone | date | why |
|---|---|---|
| M | Wed 30 Sep | |
| First drives filmed | Sat 3 – Sun 4 Oct | northern New England at or near peak |
| B | around Wed 7 Oct | beta review usually takes about a day |
| Featuring nomination | by Thu 8 Oct | 14 days before L |
| First data post | around Sat 10 Oct | before the southern peak |
| S | around Tue 13 Oct | |
| Go/no-go | Thu 15 Oct | |
| A | around Thu 15 – Mon 19 Oct | |
| Southern NH Cars and Coffee | Sun 18 Oct | show the beta QR code |
| **L** | **Thu 22 Oct** | MA peaks around 14 Oct and CT around 18 Oct, with coastal CT and RI in late October to early November, so launch weekend (24–25 Oct) is the last good peak weekend in the south |
| **Domain expiry** | **Wed 28 Oct** | renewed back in Phase 0, not on this date |
| L+30 | Sat 21 Nov | off-season; #30DayMapChallenge runs through November |

This is tight. The week of engineering in the release plan has to fit into the
first two weeks of October. If it doesn't, the fallback in §7.3 takes over.

---

## 8. The launch-day runbook (L)

1. **7:30.** Hit `https://api.jameskouvlis.com/api/health`, check the box's
   memory, and confirm the Cloudflare rate-limit rule is on. Bring the laptop
   connector up if you decided to use it.
2. **8:00.** Release. Refresh the US App Store until the listing is live, then
   search "sunday drive" and note your rank.
3. **Open three tabs and leave them open:** App Store Connect's analytics,
   Cloudflare's analytics, and your post queue.
4. **11:00.** Post in the order given in §7.2, **one channel at a time**, so
   each one's replies get your full attention and the load arrives in waves.
5. **Reply to everything** for three hours. Thank everyone who tries it. Answer
   every "does it work in X?" with "New England only for now. Which state
   should be next?"
6. **If the server struggles** (5xx errors, slow loops): stop posting new
   things, bring the second connector up, and post one line wherever people
   are asking ("busy, try again in a few minutes"). Don't delete anything.
7. **In the evening,** write down the numbers: installs, ratings, requests, and
   what surprised you.

---

## 9. Measuring without adding tracking

The privacy page promises no analytics in the app, and you don't need any:

| source | what it tells you | cost |
|---|---|---|
| **App Store Connect → Analytics** | Impressions, product page views, conversion, and installs **by source** (search, browse, web referrer, app referrer, and each **campaign link**). Sessions and retention for users who opted in to share data with developers | free |
| **TestFlight** | testers, sessions, crash reports, feedback with screenshots | free |
| **Xcode Organizer** | crashes and hangs from the App Store build | free |
| **Cloudflare analytics** | requests per day through the tunnel, a proxy for drives planned, with no new logging | free |
| **TikTok Studio, Instagram Insights, YouTube Studio** | per-post views, watch time, sends and shares, saves, follows, traffic sources | free |

**Every Monday, 20 minutes:** which three posts beat your median, and why;
which campaign link converted; the ratings count; any crashes.

**Targets (these are goals, not forecasts):**

- **L+30: 15 ratings**, more than any scenic-driving app launched this year
  (§2).
- **L+90: 50 ratings.**
- **Downloads:** set a target at L+7, from launch week's rate. Before then there
  is no honest basis for a number.

**Decision rules (starting thresholds, to adjust as you learn):**

1. If a channel brings under 10% of campaign-attributed installs after four
   weeks of effort, cut the time you give it in half.
2. If a format scores below the account's median views four posts in a row,
   drop it.
3. If short-video installs are still negligible after six weeks of three posts
   a week, move half that time to Reddit data posts and YouTube.
4. Never judge a channel on a single post.

---

## 10. Risks and guardrails

| risk | likelihood | mitigation |
|---|---|---|
| **The domain lapses on 28 October**, taking the API and the privacy contact with it | certain if ignored | Renew in Phase 0 (about $23 a year at GoDaddy's list price) |
| **A post takes off and requests pile up at the server** | low, but it's the moment that counts | The load test, the Cloudflare rate limit, the laptop as a gated second connector, staggered posts, and the stop-posting rule (§8) |
| **Out-of-region installs lead to one-star reviews** | high, given national reach | "New England only" in every caption and the first line of the description; the friendlier server message (§5.10, item 2) |
| **Android users can't install** | about 40% of viewers | "iPhone" in every caption; count the requests |
| **Your home address shows up in a video** | high by default | Public starting points, and check every recording (§6.4) |
| **Filming while driving** | — | Never (§6.4) |
| **A subreddit bans or shadowbans the account** | medium | Read the rules, get moderator permission, post once per sub, space posts days apart |
| **Overclaiming leads to bad reviews** | medium | "Scored" and "measured", never "best"; point to the app's own limits screen (§3.4) |
| **Music or imagery copyright** | medium | Original audio or platform libraries, your own footage, credits |
| **Obscuring Apple's logo, or comparing against Apple's routes** | low, now that you know | §6.4 and §3.4 |
| **Confusion over the name** (Google Drive, the dealership) | high | Direct links everywhere, check the rank on L, use "Sunday Drive scenic routes" |
| **Burnout** | high by November | The weekly loop is the floor, and skipping a week is allowed |
| **A trademark complaint** | low | Per [`sunday-drive-naming.md`](sunday-drive-naming.md) §4, get clearance before spending money on the brand |
| **Marketing breaks the privacy promise** | medium | No email waitlist (use TestFlight or a pre-order instead), no tracking pixels on the landing page, no SDKs. Update the policy before adding any new data flow |

---

## 11. What it costs

| item | cost | needed? |
|---|---|---|
| Apple Developer Program | $99/yr | yes, for any release |
| `jameskouvlis.com` renewal | about $23/yr (GoDaddy list) | yes: the API hostname is baked into every build |
| Hosting | $0 (Oracle Always Free) | yes |
| Landing page and press kit | $0 (GitHub Pages, already live) | yes |
| Editing, scheduling, design | $0 (iMovie or DaVinci Resolve; the platforms' own schedulers; Canva's free tier) | yes |
| A phone mount | about $15–25, if you don't own one | you need one to navigate legally anyway |
| Gas | your weekly drive | the drive you'd take anyway |
| A brand domain (`sundaydrive.co`, `sundaydrives.app`) | optional | not now. The GitHub Student Developer Pack lists free `.me` and `.tech` domains for a year *(re-check)* |
| **Time** | about 4–6 h a week, and 15–20 h in launch week | the real budget |

**There is no paid line in the plan, and nothing in it needs one.**

---

## 12. Decisions for the owner

1. **Target L = Thursday 22 October 2026, or a quiet release and the spring
   opener?** (§7.3)
2. **On camera or not?** A face and a voice help the building-in-public posts,
   though voice-over and on-screen text work too.
3. **The handle.** Check it on all three platforms on the same day.
4. **Ship the "Nowhere" / "good miles" copy in the app before launch, or
   not?** Captions follow the UI (§3.2).
5. **Build the rating prompt before L?** Recommended: it's small, and ratings
   are the target.
6. **Build the share card before or after L?** After is recommended. Launch
   first.
7. **A newsletter, later?** A free weekly "this weekend's drive" email is a
   strong idea, but it adds a data flow to the privacy page. Not before spring.

---

## 13. The target list

These are starting points, not endorsements. Read every group's rules before
posting. Subscriber counts weren't retrieved, because Reddit blocks automated
reads.

- **Reddit:** r/newengland · r/boston · r/massachusetts · r/vermont ·
  r/newhampshire · r/maine · r/Connecticut · r/RhodeIsland · city subs ·
  r/Miata · r/subaru · r/cars · r/MapPorn · r/dataisbeautiful · r/SideProject ·
  r/iOSProgramming · r/openstreetmap
- **Facebook:** New England Fall Foliage (Jeff Folger) · state and town groups ·
  club groups
- **Clubs and events:** Larz Anderson Auto Museum (Brookline) · Southern NH
  Cars and Coffee (Manchester, 18 October) · BMW CCA Boston · PCA Northeast
  Region · Audi Club Northeast · Miata and Subaru groups · VSCCA · AACA regions
  · New England Riders
- **Tourism and byways:** state tourism offices and their foliage reports ·
  Mohawk Trail · Kancamagus Scenic Byway · Connecticut River Byway · Vermont
  Byways (Route 100) · NH Scenic and Cultural Byways · Maine Scenic Byways ·
  FHWA America's Byways
- **Press:** see §5.5
- **Northeastern:** Northeastern Global News · *The Huntington News* · NUMedia
- **Tech:** Hacker News (Show HN) · weeklyOSM · OSM US · #30DayMapChallenge ·
  MacStories · 9to5Mac

---

## 14. Sources (all read 2026-09-29)

**From this repo:** [`release-plan.md`](release-plan.md) ·
[`branding-brainstorm.md`](branding-brainstorm.md) ·
[`sunday-drive-naming.md`](sunday-drive-naming.md) ·
[`app-store-submission.md`](app-store-submission.md) ·
[`privacy-policy.md`](privacy-policy.md) and the live
[privacy page](https://jamesk1281.github.io/SundayDrive/privacy/) ·
[`privacy-policy-page-brief.md`](briefs.md) ·
[`driving-app-features-cost.md`](driving-app-features-cost.md) ·
[`data-sources.md`](data-sources.md) ·
[`hosting-independent-review.md`](hosting-independent-review.md) ·
`server/serve.py:44` · `server/app.py:262` · `server/DEPLOY-oracle.md` Part 11
· `ios/Sources/BeforeYouDriveView.swift`, `RouteResults.swift`,
`RouteService.swift` · `site/index.html` · `tests/test_privacy_page.py` ·
`data/processed-ne/scored_chunks.parquet` (schema, in the main checkout only).

**The App Store census:** Apple's search API
(`itunes.apple.com/search?entity=software&country=us`) for "scenic drive",
"aimless drives", "sunday drive" and "fall foliage".

**Web:**

- TikTok's US joint venture closed in January 2026 — [The Hacker News](https://thehackernews.com/2026/01/tiktok-forms-us-joint-venture-to.html)
- TikTok's US Local feed, February 2026 — [MacRumors](https://www.macrumors.com/2026/02/11/tiktok-us-local-feed); how posts qualify — [Storrito](https://storrito.com/resources/how-tiktoks-local-feeds-work-and-what-location-based-discovery-changes-for-content-teams/)
- TikTok Business vs personal accounts, links and music — [unil.ink](https://unil.ink/blog/tiktok-link-in-bio-without-1000-followers), [Soundstripe](https://www.soundstripe.com/blogs/why-can-i-only-use-commercial-sounds-on-tiktok)
- Carousels vs video — [Fanpage Karma](https://www.fanpagekarma.com/insights/carousel-vs-video-performance-tiktok-instagram/)
- TikTok search — [Metricool](https://metricool.com/tiktok-seo/)
- Instagram's sends-per-reach signal — [Search Engine Journal](https://searchenginejournal.com/instagram-algorithm-shift-why-sends-matter-more-than-ever/521389)
- Instagram Trial Reels — [inro](https://www.inro.social/blog/what-is-a-reel-trial)
- Instagram Map — [TechCrunch](https://techcrunch.com/2025/08/06/instagram-takes-on-snapchat-with-new-instagram-map)
- Apple pre-orders — [developer.apple.com](https://developer.apple.com/app-store/pre-orders/)
- Featuring nominations — [TechCrunch](https://techcrunch.com/2024/11/13/apple-now-lets-app-developers-apply-to-be-featured-on-the-app-store); lead time — [aso.dev](https://aso.dev/metadata/nominations/)
- Custom product pages in organic search — [Phiture](https://phiture.com/blog/keyword-based-custom-product-pages-cpps-arrive-in-app-store-connect/), [Adapty](https://adapty.io/blog/custom-product-pages-app-store/)
- In-app events — [MobileAction](https://www.mobileaction.co/guide/in-app-events-promotional-content-guide)
- US iPhone share — [Digital Silk](https://www.digitalsilk.com/digital-trends/iphone-vs-android-user-stats/)
- 2026 foliage timing — More Than Just Parks trackers for [Massachusetts](https://morethanjustparks.com/foliage-tracker/massachusetts) and [Connecticut](https://morethanjustparks.com/foliage-tracker/connecticut)
- Patch announcements — [patch.com](https://patch.com/info/posting-instructions)
- *The Huntington News* tips — [huntnewsnu.com](https://huntnewsnu.com/tips/)
- Car events — [Larz Anderson Auto Museum](https://www.larzanderson.org/rally), [Southern NH Cars and Coffee](https://americancollectors.com/event/southern-new-hampshire-cars-and-coffee/)
- New England Riders — [Rider Magazine](https://ridermagazine.com/2023/06/01/ed-conde-ep-62-rider-magazine-insider-podcast/)
- Scenic byways — [Scenic America (NH)](https://www.scenic.org/state/new-hampshire/), [FHWA (MA)](https://fhwaapps.fhwa.dot.gov/bywaysp/States/Show/MA)
- CapCut's terms — [Larry Jordan](https://larryjordan.com/articles/caution-capcut-changed-their-license-and-may-own-your-content/)
- GitHub Student Developer Pack — [Capital & Compute](https://capitalandcompute.net/blog/github-student-developer-pack-2026/)
- The ambient-drive genre — a web search on 2026-09-29 (channel listings for World Driving Tours and the 4K Relaxation Channel)
