# Marketing plan: how Sunday Drive finds its drivers, for $0

**Status: a plan; nothing in it has been executed. Rewritten 2026-10-18 for a
national first launch within weeks, against `main` at `0fca74f`.** The New
England launch plan it replaces (L = Thursday 22 October 2026, written
2026-09-29) is `git show 0fca74f:docs/marketing-plan.md`, last edited in
`55f2288`. Web facts were re-checked on 2026-10-18 and are listed in §14 with
that date. Facts carried over from the 2026-09-29 check and not re-read are
marked *(re-check)*.

**What changed on 2026-10-18, decided by the owner:**

1. **The New England-only app will never be public.** The first App Store
   release is the national app: the 48 contiguous states and DC, **due within
   the next couple of weeks**. A private TestFlight for invited friends is not
   "public". Whether a *public* TestFlight link counts is not decided (§12).
2. **Scenery is scored on one national scale.** A 7 means the same
   everywhere. So the plains have almost no 7+ road (0.6% of eastern
   Colorado's km), and the mountains have plenty (29% of Colorado's mountain km
   under the scoring built on the `usa` branch,
   `national-scenery-scoring-verdict.md` §7).
3. **There will be no cross-country test drives.** Every scenery rating the
   app has ever been checked against is from New England, and that will stay
   true.

**What this is:** a side project by one college freshman. The plan is sized
for that: about 3 hours a week, more in launch week, less in winter. The rest
is unchanged: $0 marketing, a completely free app, no account, no tracking,
open source, iPhone only.

It sits beside [`release-plan.md`](release-plan.md). That one gets the app onto
the App Store; this one gets people to it.

---

## 0. The plan on one page

1. **Launch on a Thursday in early November: target Thursday 5 November
   2026** (L). The app's launch doesn't depend on a season any more. Only two
   hooks are dated: #30DayMapChallenge (all of November) and Thanksgiving
   weekend (26–29 November) (§7).
2. **Spend the national, non-seasonal one-shots now; hold the New England
   seasonal ones.** At launch, use what works in any month: Northeastern's
   channels, Apple's featuring nomination, the national scenery map, Show HN,
   the OpenStreetMap community and the tech press. Hold what needs good
   weather in New England (local press, the northern state subreddits, the
   foliage groups) for **Memorial Day weekend 2027** and **foliage 2027**
   (§7.2).
3. **New England is the only region you market locally.** It's where you
   live, where you drive, and the only place the score has been checked. The
   rest of the country gets only the channels that cost the same for 48 states
   as for one: App Store search, the national map, YouTube, Reddit's data subs,
   Show HN (§4.2).
4. **Measured claims stay where they were measured, permanently.** The "96%
   liked at 7+" figure is one rater (you), 52 marks, all in New England. New
   England's network figures (146,811 miles, 942,448 scored segments, six
   states) are New England's. None of it travels. Nationally, say only what is
   true everywhere: free, no account, a score for every road on one scale, an
   open method (§3.4).
5. **The plains are the launch's biggest risk, and copy can't fix it.** On one
   national scale, a Kansas driver sees few 7+ roads, and the router currently
   adds a mean 41 minutes to plains trips for almost nothing it can show.
   "Beautiful roads wherever you are" earns one-star reviews. Say plainly that
   flat country scores low, and get the app to say it too (§3.4, §5.10).
6. **Before anything goes out:** renew `jameskouvlis.com` (it expires **28
   October**, a week before L), and load-test the national build on the box
   (§7.3).

**If you only do five things:** renew the domain; file the featuring
nomination this week; post the national map in November; answer every comment
honestly, including "it's flat here"; and keep filming New England for spring.

### Terms used below

| term | meaning |
|---|---|
| **L** | Launch day: the day the app goes live on the App Store. L−7 is a week before, L+30 a month after |
| **Mark** | One rating of a stretch of road, made by a driver during a test drive. The scenery score has only ever been checked against your own New England marks |
| **The national scale** | Scores mean the same everywhere: a 7 in Kansas is as good as a 7 in Vermont |
| **ASO** | App Store Optimization: the name, subtitle, keywords, screenshots and video that decide whether people find you in App Store search and install |
| **One-shot channel** | Somewhere you can realistically announce once: a press story, the "I built this" post in a subreddit, Show HN, the featuring nomination |
| **Repeatable channel** | Somewhere you can post every week indefinitely: your video accounts, answers in "where should I drive?" threads |
| **Campaign link** | An App Store link with a tag (`ct=reddit`) that lets App Store Connect tell you which channel an install came from |
| **CPP** | Custom product page: an alternative version of your App Store page, with different screenshots and text, that one channel can point at |

---

## 1. The constraints, and what each one forces

| constraint | what it forces |
|---|---|
| $0 budget | Your time is the budget. Favor what compounds (search on YouTube, TikTok and the App Store) and one-shots worth spending |
| A side project, a freshman | About 3 hours a week. Launch week about 10. Winter can drop to 1–2. A plan that needs daily posting is dead by December |
| The app is free | No discount or premium tier to promote. In exchange, a free, ad-free, open-source tool is welcome where commercial promotion isn't (§3.3) |
| National from day one | "Doesn't work here" reviews disappear. "Works here and it's boring" replaces them. Never promise scenery the score can't find (§3.4) |
| No drives outside New England | Nothing Western is validated by you, ever. Western content is desk work (maps, lists) labelled as unchecked, or other people's checking (§6.3, §12) |
| Launching in November | New England's off-season: color is over, and the northern roads close from mid-October. So launch on the national, data and builder story, and hold the scenic New England story for spring |
| iPhone only (about 58% of US users *(re-check)*) | Say **"iPhone"** in every caption. Count Android requests; promise nothing |
| One server | The box's capacity was measured on the New England build (about 1.5 mixed requests a second, [`load-test-oracle.md`](load-test-oracle.md)). Re-measure on the build you ship (§7.3) |

**Verdict:** the plan gets smaller, not just wider. The national app widens
the audience. The time budget and the November date shrink what you can do for
it. So the launch leans on a few national one-shots, and the weekly content
routine waits for spring.

---

## 2. The market, re-measured

Counted with Apple's App Store search API (US store) on 2026-10-18, for nine
scenic-driving search terms (§14). Search is ranked by relevance, so these are
**"at least"** figures. Ratings stand in for use.

**Scenic-driving apps launched in 2026, as of 2026-10-18:**

| app | launched | ratings | notes |
|---|---|---|---|
| Vibe Drive | 2026-01-30 | 1 | |
| DriveGo: Scenic Route Planner | 2026-02-20 | 5 | subscription, CarPlay, curvy roads |
| RevRoutes Find Scenic Drives | 2026-05-14 | 0 | |
| Routes – Best Driving Roads | 2026-06-06 | 0 | |
| DriveLoop: Go For A Drive | 2026-06-11 | 1 | time-budget drives, hands off to Google Maps |
| Scenra: Scenic Road Trips | 2026-07-02 | 0 | |
| Pleasant Routes | 2026-07-10 | 14 | |
| Scenic Way | 2026-07-18 | 0 | |
| Joyride: Roads & Drives | 2026-07-28 | 0 | |
| Aimless Drives | 2026-09-02 | 3 | free, no in-app purchase listed, no account, no tracking, hands off to Google Maps |
| **WanderWay Navigation** | **2026-09-16** | **5** | **"generate a Sunday Drive"**, loops of 30 min to 5 h, CarPlay, no account; 14-day trial, then a $4.99 unlock |
| Carve: Scenic Drive Planner | 2026-10-05 | 1 | yearly subscription, loops, CarPlay |
| MotoRidez: Scenic Routes | 2026-10-08 | 0 | |
| DriveLoop | 2026-10-14 | 0 | unrelated app, same name |

**The apps with users are old:** Roadtrippers (2014) has 61,536 ratings,
Scenic Motorcycle Navigation (2016) 7,482, calimoto 979, ROADS by Porsche
(2018) 261. **Detour – Scenic Navigation** has 3. It is free to download, with
in-app purchases at $9.99 and $49.99, and a "Scenic Heatmap US". **Google's
Ask Maps** (US, since 12 March 2026) can be asked for scenic stops along a
route. No dedicated scenic-route mode was found *(re-check)*.

**What it means:**

- **Fifteen ratings still makes you the most-used new entrant.** The best of
  fourteen 2026 entrants has 14.
- **Not novel:** loops, a time budget, the compass, the slider. Don't claim
  "the only".
- **Not unique on its own:** "free, no account, no tracking". Aimless says all
  three.
- **Yours, in combination:** free, no account, *its own* turn-by-turn
  navigation (Aimless and DriveLoop hand off to Google Maps), open source, and
  scenery for cars rather than curvature for bikes.
- **The name is contested.** WanderWay uses "Sunday Drive" as a feature name,
  and App Store search for "sunday drive" returns other apps first. Every post
  needs a direct link.

**Verdict:** a crowded, empty field. Whoever gets honest ratings first wins,
and distribution decides that.

---

## 3. Positioning and message

### 3.1 Adopted, not reinvented

From [`branding-brainstorm.md`](branding-brainstorm.md) §2 and §5:

- **The thesis:** every navigation app optimizes for less time; this one asks
  you to spend more. **Proudly anti-efficiency.**
- **The voice:** unhurried, dry, quietly confident. No exclamation marks.
- **The subtitle (decided):** *The scenic route, on purpose*
  ([`app-store-submission.md`](app-store-submission.md)). It makes no regional
  claim, so it stands.
- **The one-liner:** Every road in the contiguous US, scored for scenery on one
  scale. Move one slider to trade minutes for the view.
- **The loop hook:** Ninety minutes, nowhere to be. We'll bring you home the
  pretty way.
- **The credibility line:** Built on open data. Every road measured, not
  crowdsourced. The method is public.
- **The honesty line (new):** One scale everywhere, so some places have more
  7s than others. It says so.

Check the coverage wording against the build you ship. If the shipped build
covers less than every road in the 48 states and DC, say what it does cover.

**Verdict:** keep it. Only the line that named New England changes.

### 3.2 Say what's on the screen

Captions use the app's own words. The results card says **"Scenic adds 49
min"** (`ios/Sources/RouteResults.swift`), and the loop is labelled **"Loop"**.
"Nowhere" and "good miles" never shipped to the UI, so leave them out of
videos.

### 3.3 The free-app message

- **Say it plainly:** *Free. No account, no ads, no tracking. Open source.*
  True today, and on the live
  [privacy page](https://jamesk1281.github.io/SundayDrive/privacy/).
- **Answer the catch first.** A Northeastern freshman built it as a side
  project, the code is public, the server runs on a free tier, and the app
  lists what it can't do (`ios/Sources/BeforeYouDriveView.swift`).
- **Lead with the combination.** Aimless also says "no account" (§2). What's
  yours is *free, no account, its own turn-by-turn, open source.*
- **Keep it true.** Any analytics SDK, account, ad, price or email list breaks
  the message and reopens the privacy decision (`release-plan.md` §8, Decision
  3). That's why §9 uses only numbers Apple, Cloudflare and the platforms
  already give you.
- **Where not to say it:** Apple rejects in-app event metadata that mentions
  price, "free" included. The listing shows the price already, so don't spend
  keyword bytes on it (§5.7).

### 3.4 What not to claim

From [`branding-brainstorm.md`](branding-brainstorm.md) §5: no "best route", no
"most scenic", nothing that implies validated ground truth. **"Scored" and
"measured" are defensible. "Beautiful, guaranteed" is not.** Rank drives "by
our score", never as fact. Compare only against **the app's own fastest
route**. Never compare against Apple's routes (ADPLA Attachment 6 §2.3, see
[`legal-and-ip-audit.md`](legal-and-ip-audit.md)), and don't name other apps in
the listing (guideline 2.3.7).

**New: every measured claim carries its scope.**

| claim | true where | how to say it |
|---|---|---|
| Free, no account, no ads, no tracking, open source | everywhere | plainly, anywhere |
| Every road has a scenery score, on one scale | wherever the shipped build covers | "every road in the contiguous US is scored", if that's what ships |
| The method is public | everywhere | link the repo and the method doc |
| The trade against the app's own fastest route | everywhere | "Scenic adds 12 min", in the app's words |
| **"96% liked at 7+"** | **New England only**: 52 marks, one rater (you) | Only as "on my own New England test drives", in builder posts and Show HN. Never in the listing, captions or press. Anyone will ask who rated it, and the honest answer is "me" |
| The 74%-against-63% separation over 79 ratings | New England only, one rater | The featuring nomination's private notes only, as [`app-store-listing.md`](app-store-listing.md) §6 already does |
| 146,811 miles, 942,448 segments, six states | New England's network | New England posts and press only. State the national mileage from the shipped build, measured, not estimated |
| Western scores agree with a driver | **nowhere** | Never. No one has checked them. Western lists are "by our score, unchecked" (§6.3) |
| "Scenic roads near you", "beautiful wherever you are" | **false** on the plains | **Never** |
| "In flat country it tells you so" | only if the app does | Only after the low-scenery message ships (§5.10, item 2) |

**Verdict:** the review to fear is no longer "doesn't work in Ohio". It is
"promised scenery, gave me 40 extra minutes of cornfield". Every national
sentence has to survive a reader in Kansas.

---

## 4. Who it is for, and where the marketing goes

### 4.1 Audiences

| audience | where they are | what to show them | priority |
|---|---|---|---|
| **New England weekend drivers** | state subreddits, town Facebook groups, local news | The loop: an hour, nowhere to be, home the pretty way | **1, but mostly from spring 2027** |
| **Map, data and open-source people**, national | r/dataisbeautiful, r/MapPorn, Hacker News, OpenStreetMap, #30DayMapChallenge | The national map on one scale, the method, the repo | **2, and the launch's engine**: November is their month |
| **Road-trippers and people driving for Thanksgiving**, national | YouTube and TikTok search, r/roadtrip | The trade on a real drive; "the pretty way home for the holiday" | **3, seasonal (Thanksgiving)** |
| **Builders and Apple people** | r/SideProject, r/iOSProgramming, MacStories, 9to5Mac | A freshman's native, privacy-respecting app | **4, credibility** |
| **Car enthusiasts** | clubs, Cars & Coffee, model subreddits | Routing a club drive | **5, spring** |
| **Plains drivers** | everywhere | Nothing, as a target. Don't mislead them when they find you | not a target |

### 4.2 One home region, and a national layer

The New England plan's engine (location-tagged video, state subreddits, local
press, Facebook groups) works because it is local. Copied across 48 states it
is about 48 × 3 × 1 h = **144 hours a year of posting alone**, for states you
can't film. You can't do that, and nobody could on a side-project budget.

| | what | why | hours a week |
|---|---|---|---|
| **Home: New England** | Your drives, your footage, state subs, local press, clubs | The only region you can film, drive and check. The score is strongest where it has been validated | **~1.5** in winter, from footage you already have; **~2.5** from spring |
| **National layer** | App Store search and listing, the national map, YouTube, Reddit's data subs, Show HN, tech press, answering "does it work in X?" | These cost the same for 48 states as for one | **~1**, with spikes at launch |
| **Everywhere else** | Desk-only per-state lists, labelled "by our score, unchecked; locals, what did it miss?" (§6.3) | The only honest way to talk to a state you haven't driven: ask the people who have | **optional, ~1 h a post**, at most one a fortnight |

**Verdict:** one home region, plus a national layer that's mostly one-shots.
That fits in about 3 hours a week. If people in some other state show up in
the campaign links (§9), give that state a desk-only list, and nothing more.

---

## 5. Channels: the playbooks

Each one is tagged **national** or **home** (New England), with *what*, *how*,
*cadence*, *the trap* and a verdict.

### 5.1 Short video: TikTok, Instagram Reels, YouTube Shorts (home)

**Setup (an hour, before L):** one handle on all three, checked the same day
(`sundaydrive.app`, `sundaydriveapp`, `takethesundaydrive`). Use a TikTok
Business account, for the clickable link at any follower count. Use an
Instagram Professional account, for Insights. One YouTube channel serves both
Shorts and long-form *(re-check)*.

**The levers** *(carried from 2026-09-29; re-check)*:

- **Tag the location on every post.** TikTok's US Local feed and Instagram's
  Map surface location-tagged posts to nearby viewers. This is what keeps a
  national platform local.
- **Put the keyword in the first on-screen text, and say it aloud.** TikTok
  search reads both. Use 3–5 hashtags.
- **Use carousels for lists.** "Top 5 drives in Connecticut, by our score."
- **Ask for the send:** "Send this to whoever's driving Sunday."
- **Export clean, then post the same file to all three.** Instagram demotes
  other apps' watermarks.
- **Music:** original audio or the platforms' commercial libraries, never a
  trending track. **Editing:** iMovie or DaVinci Resolve, free. Avoid CapCut
  for footage you want to own.

**Cadence:** winter, 1–2 posts a week from this October's footage. From
spring, 3 a week cut from one drive (§6.1).

**The trap:** a clip of a 9-rated road going viral nationally, then the
viewers meeting a plains score. Caption the place, never "roads like this near
you".

**Verdict:** still the engine, but a spring engine. In November, bank footage
and post lightly.

### 5.2 YouTube long-form: the ambient drive (national, evergreen)

30 to 90 minutes of one drive, camera mounted, no talking, chapters by town.
YouTube search is national and keeps sending viewers for years, so one New
England drive reaches a viewer in Ohio planning a trip. The description carries
the route, the app link and the credits ("Route data © OpenStreetMap
contributors").

**Cadence:** whenever footage is good. This October's late color is the first
batch. **The trap:** a shaky mount. Test it on a short drive.

**Verdict:** the best repeatable national channel you can feed without
travelling.

### 5.3 Reddit (national data subs now; home subs mostly in spring)

**Three formats:**

1. **The national map, one post per sub:** "Every road in the contiguous US,
   scored for scenery on one scale". It's honest by construction: the plains
   are visibly pale, and saying why is the post. r/dataisbeautiful and
   r/MapPorn, days apart, in November (§7.2). **This is the post nobody else
   can make.**
2. **The launch post, once per sub:** "I'm a freshman at Northeastern, and I
   built a free, open-source iPhone app that finds the scenic way. No ads, no
   account." At launch in r/SideProject, r/iOSProgramming, r/boston and
   r/massachusetts. Those posts sell the builder, not the season. Hold
   r/vermont, r/newhampshire and r/maine for Memorial Day: their scenic roads
   are closed in winter.
3. **The per-state data post, repeatable:** "These are the 10 best-scoring
   drives in Connecticut" (§6.3). New England states first. Other states only
   as desk-only "unchecked" lists.

**How:** read each sub's rules and message the moderators before a launch
post. Post in the morning and answer every comment for two hours. Answer "does
it work in Iowa?" honestly: yes, and Iowa's roads score lower on one national
scale.

**The trap:** the same post in eight subs in one day. Space them days apart.

**Verdict:** the national map is the launch's best single post. Everything
else on Reddit is small and steady.

### 5.4 Facebook groups (home, spring and fall)

New England foliage groups (the *New England Fall Foliage* community linked to
Jeff Folger), town groups and car-club groups. Contribute before you promote,
and ask the admins. **Hold until spring 2027.** A November post in a foliage
group is a post about nothing.

**Verdict:** not part of the launch.

### 5.5 Press and newsletters (one story each)

| when | the hook | to whom |
|---|---|---|
| L (November 2026) | "A Northeastern freshman scored every road in America for scenery" | Northeastern Global News, *The Huntington News* (tips at huntnewsnu.com/tips), NUMedia |
| L to L+14 | The national map, and a free, private, native app | MacStories and 9to5Mac (tips) *(re-check)* |
| Thanksgiving week (23–25 Nov) | "The scenic way home for Thanksgiving, by an algorithm" | Boston.com, Universal Hub, Axios Boston: one pitch, Boston-angled |
| Winter | "We scored every official scenic byway in New England. Here's how they rank." Rank them with `c_scenic_tag` left out, since that component *is* the byway designation (`pipeline/score.py`) | New England press, byway organizations |
| Memorial Day 2027 (29–31 May) | "The summer drives an algorithm picked" | New England press: WCVB's *Chronicle*, WBUR, GBH, *Yankee*, *Seven Days*, VTDigger, NHPR, *Down East*, CT Public, *The Providence Journal* *(re-check)* |
| September 2027 | Foliage, with a season of users behind it | the same list |

**The pitch, under 150 words:**

```
Subject: A Northeastern freshman scored every road in America for scenery

Hi [name] — I'm a first-year at Northeastern. As a side project I built
Sunday Drive, a free iPhone app that scores every road in the contiguous US
for scenery from open map data, then routes you the pretty way instead of
the fast way. Give it an hour and it plans a loop home.

It's free, with no ads and no accounts, and the code is public. [One line
for the outlet: the map attached / five drives near Boston for the holiday.]

On the App Store now: [link]. Press kit: [link]. Happy to talk, or to take
you on the drive.
```

**The press kit (a section of the landing page):** the icon, five screenshots,
the national map, a photo of you, a one-paragraph story, the numbers with
their scope, credits and contact.

**The trap:** pitching before it's downloadable. Every pitch goes out on or
after L.

**Verdict:** Northeastern and the tech press at launch, one Boston pitch for
Thanksgiving, and the rest of the New England list in spring.

### 5.6 Clubs, events and destinations (home, spring)

Offer to route a club's drive and film it: BMW CCA Boston, PCA Northeast,
Miata and Subaru groups, the vintage clubs, and the Larz Anderson Auto
Museum's meets in Brookline. End drives at orchards and general stores and tag
them. **Most of this is a spring 2027 activity** *(re-check the 2027
calendars)*.

### 5.7 The App Store itself (national by nature)

| tool | what to do | when |
|---|---|---|
| **Landing page** | Replace the redirect in `site/index.html`: what it is, 3 screenshots, "iPhone · free", the national map, the App Store badge, the press kit, credits and contact. **It is also the Support URL App Store Connect requires.** It loads nothing external | before S |
| **Keywords** | **100 bytes**, nothing from the name ("sunday", "drive") or subtitle ("scenic", "route"), no competitor names. State names no longer earn their bytes. A national candidate, 96 bytes: `backroads,loop,byway,curvy,road,trip,foliage,fall,leaf,peeping,canyon,mountain,pass,country,park`. Re-measure before pasting. The New England draft in [`app-store-listing.md`](app-store-listing.md) §3 grew from the 2026-09-29 candidate and needs this national version | before S |
| **Screenshots and preview video** | The trade ("Scenic adds 12 min"), a loop, the road. Caption the place, from New England footage | before S |
| **Featuring nomination** | App Store Connect → Featuring Nominations → *App Launch*, **at least 2 weeks before L**. For L = 5 November, that's **by Thursday 22 October**. The story: a freshman, open data, one scale for a whole country *(re-check that the form accepts it before the build is submitted)* | this week |
| **Manual release** | "Manually release this version", so approval doesn't mean launch | at S |
| **Promotional text** | 170 characters, **editable any time without review**, so it's the seasonal field. November: maps and the holiday. Spring: the back roads reopening. Fall: color | at L, then seasonally |
| **Custom product pages** | Up to 70, and they can carry keywords *(re-check)*. Later: a *loops* page and a *New England foliage* page. Their keywords come out of the same 100 bytes | spring 2027 |
| **Campaign links** | One per channel: `https://apps.apple.com/app/apple-store/id<APPID>?pt=<PROVIDER_ID>&ct=reddit&mt=8` | before L |
| **In-app events** | Free cards in search, up to 31 days. They need real in-app content, and "free" in the metadata is rejected | foliage 2027 at the earliest |

**Verdict:** the listing is where "national" costs nothing extra. Get it right
once.

### 5.8 Tech and open-source communities (national, non-seasonal)

- **Show HN:** "Show HN: Sunday Drive – I scored every road in the US for
  scenery on one scale". Include why one scale, and what it costs the plains.
  HN rewards that honesty. A weekday morning, US time, after launch week.
- **The OpenStreetMap community** (weeklyOSM, OSM US): routing by their data,
  plus measured findings on uneven mapping, is news to them.
- **#30DayMapChallenge** runs every November *(re-check the 2026 themes)*.
  Post the national map on whichever day's theme fits, and a state map on
  another.

**Verdict:** these are your launch, more than any New England channel is in
November.

### 5.9 Pinterest (optional)

Pin the maps and carousels in spring, before summer trip planning. Not part of
the launch.

### 5.10 The product as a channel (engineering asks, ranked by leverage)

Code, outside the marketing budget. Adopt into [`roadmap.md`](roadmap.md) one
at a time.

1. **The rating prompt. Built** (2026-10-08, [`rating-prompt.md`](rating-prompt.md)):
   the second arrived drive of 10 minutes or more, once per version. Confirm it
   works on the national build.
2. **An honest low-scenery message.** When a route or loop finds little 7+
   road, say so ("Not much high-scoring road near here; the fast way is nearly
   as pretty") instead of selling the scenic arm. **The plains defense.**
   Mostly copy. If it can't make L, add one line to the listing's and the
   app's "what it doesn't do" lists: flat country scores low, and the scenic
   setting may add time for little to show.
3. **Stop paying minutes for nothing on the plains.** On six eastern-Colorado
   trips at the top of the slider, the router adds a mean 41 minutes for
   2.8 km of 7+ road in total (`national-scenery-scoring-verdict.md`, `usa`
   branch). The verdict recommends the convex-cost experiment before a
   national launch. It is a release question, but marketing inherits its
   reviews.
4. **Share this drive.** A `ShareLink` with the map and the card. **Trim the
   first and last kilometre, since a loop starts "From here", which is usually
   home.** There is no `ShareLink` in `ios/Sources` today.
5. **"Hey Siri, take me on a Sunday drive"**, through App Intents.
6. **An opt-in weekly reminder:** "It's Sunday. Ninety minutes, nowhere to
   be?" A local notification: no server, no data.
7. **CarPlay.** WanderWay, Carve and DriveGo have it. The entitlement is held
   (2026-10-08). Expect road-trippers to ask.

---

## 6. The content system

### 6.1 The weekly loop (spring onward, about 2.5 hours)

| when | what | time |
|---|---|---|
| Weekend | Drive a loop from a **public starting point**, phone mounted and screen-recording, a second camera on the road, five stills at stops | the drive you'd take anyway |
| Sunday | Cut 3 shorts and 1 carousel; long-form if the footage is good | 1.5 h |
| Monday | Schedule in TikTok Studio, Meta Business Suite and YouTube Studio; captions, location tags | 20 min |
| Daily | Reply to comments | 5–10 min |
| Monday | The numbers (§9) | 10 min |

**In winter,** post 1–2 a week from footage you already have, and drive when
you'd drive anyway. Skipping a week is allowed.

### 6.2 Formats, with hooks

| # | format | the first two seconds |
|---|---|---|
| 1 | **The Sunday Drive** | the best frame, over "This week's drive, picked by an algorithm" |
| 2 | **The trade** | "Scenic adds 12 min. Worth it?" |
| 3 | **The top 5 in a state** | "The 5 best-scoring drives in Connecticut" (carousel) |
| 4 | **Comment your town** | "You said Nashua. Here's an hour, the pretty way". New England only, where you can drive it |
| 5 | **The algorithm's worst pick** | "My app thought this was scenic" |
| 6 | **Building in public** | "I'm a freshman, and I scored every road in America. Here's how" |
| 7 | **The map** | the contiguous US animating in, on one scale |
| 8 | **One scale, honestly** | "On a national scale, Kansas's best road scores a [n]. Here's why that's the point" (check the number on the shipped build) |
| 9 | **Is my algorithm wrong about your state?** | a state's unchecked top 5, "locals, what did it miss?" |
| 10 | **The ambient drive** | no hook; 45 minutes of drive (YouTube) |

**The caption template:**

```
Scenic drive from Worcester, MA — a 60-minute loop through the Quabbin hills.
Picked by Sunday Drive, a free iPhone app that scores every road in the US
for scenery. iPhone · free · link in bio
#newengland #scenicdrive #massachusetts #sundaydrive
```

### 6.3 The flagship: a per-state top 10 from your own data

`scored_chunks.parquet` has `name`, `ref`, `highway`, `length_m`, every
component and the final `score` for each segment. The national build has the
same columns.

1. Group segments into named stretches (by `name`, else `ref`), and keep
   stretches with at least about 8 km of drivable road.
2. Rank by length-weighted mean `score`.
3. Assign states with the Census cartographic boundaries (public domain).
4. **Rank within a state, never across states.** Mapping density and terrain
   saturation differ by region.
5. **Check the list.** In New England, against your own driving and marks: cut
   what's obviously wrong and say so ("#7 surprised me"). If it's mostly
   byways, re-rank without `c_scenic_tag` and say which ranking you used.
   **Outside New England you can't check it**, so the post says "by our score,
   unchecked" and asks locals to correct it. Their corrections are the content.
6. **Print the scores.** On one scale a state's #1 can be a 5. Let that be the
   honesty, and sometimes the joke.
7. **Desk-check every listed road outside New England** before posting:
   seasonal closure, 4WD-only, private or gated. The national data-safety work
   is still in progress (`us-map-data-findings.md` §7), so look each road up
   with its operator (park, forest, state DOT). About 5 minutes a road. A
   closed road in a top 10 is the worst post you can make.

New England miles per state, for home posts: MA 42,116 · ME 37,263 · CT
24,668 · NH 19,967 · VT 17,730 · RI 6,762
([`driving-app-features-cost.md`](driving-app-features-cost.md)).

### 6.4 Rules for every piece of content

- **Never film while driving.** A passenger films, or the camera is mounted and
  started before the car moves.
- **Never show home.** Start demo loops from a town green or a parking lot.
  Check the first and last seconds of every recording.
- **Credit the map.** "© OpenStreetMap contributors" visible in the image
  itself; land-cover and elevation credits when those layers show
  ([`data-sources.md`](data-sources.md), `ios/Sources/AboutView.swift`).
- **Leave Apple's corner alone.** Don't crop or caption over the Apple Maps
  logo and Legal link.
- **Use your own footage.** No Street View, no other creators' clips outside
  TikTok's stitch and duet.
- **Name the place, scope the claim.** No clip implies the whole country looks
  like it.

**Verdict:** one drive still makes a week, from spring. Until then the map and
the lists carry the account, and they need no travel.

---

## 7. The timeline, relative to L

### 7.1 The milestones

| code | milestone | depends on | target |
|---|---|---|---|
| **M** | Apple Developer Program membership | **done**, 2026-10-03; renews about 3 October 2027 | — |
| **S** | App Store submission, manual release | the national build, the release plan's checklist (`app-store-submission.md` §8) | by Thu 29 Oct |
| **A** | Approved | App Review, usually a day or two *(re-check)* | about Mon 2 Nov |
| **L** | **Launch: a manual release, on a Thursday** | A, plus the go/no-go (§7.3) | **Thu 5 Nov 2026** |

**Why Thursday:** the app is for weekends. The first weekend after L is when
people use it.

### 7.2 Where each one-shot goes

| one-shot | seasonal? | spend it |
|---|---|---|
| Apple featuring nomination (*App Launch*) | no | for L; file by Thu 22 Oct |
| Northeastern's channels | no | L |
| r/SideProject, r/iOSProgramming, r/boston, r/massachusetts launch posts | no | L to L+3, days apart |
| Tech press tips | no | L+1 |
| The national map on r/dataisbeautiful and r/MapPorn | no, but November has #30DayMapChallenge | L+3 to L+20, days apart |
| Show HN | no | a weekday in L+5 to L+14 |
| OSM community (weeklyOSM, OSM US) | no | L+7 to L+21 |
| Boston press, Thanksgiving angle | yes: Thanksgiving, 26–29 Nov | pitch Mon 23 – Tue 24 Nov |
| r/vermont, r/newhampshire, r/maine, r/Connecticut, r/RhodeIsland launch posts | yes: their roads close in winter | Memorial Day 2027 |
| New England foliage Facebook groups | yes | foliage 2027 |
| New England regional press (TV, radio, magazines) | yes | Memorial Day 2027, then foliage 2027 |
| *App Enhancements* nomination | — | the first real update, filed 2 weeks ahead |

### 7.3 The go/no-go check at L−7 (Thursday 29 October)

Launch on the planned Thursday only if **all six** hold:

1. The app is submitted, early enough that a normal review lands before L−1.
2. **The load test passed on the national build**, and the rate limit is on.
   The New England numbers in [`load-test-oracle.md`](load-test-oracle.md)
   don't carry over: the graph is bigger.
3. **The domain is renewed.** It expires Wednesday 28 October, the day before
   this check.
4. No known crash on TestFlight.
5. The landing page and campaign links are live.
6. **No national copy carries a New England number** (listing, screenshots,
   press kit, drafted posts, checked against §3.4), and flat country is
   covered by the low-scenery message or the "what it doesn't do" line (§5.10,
   item 2).

**If one fails:** move L a week, to Thursday 12 November. Nothing in the
launch is seasonal except #30DayMapChallenge (all November) and Thanksgiving.
**If L slips past Thanksgiving:** launch when ready, spend the non-seasonal
one-shots (the map, Show HN, OSM, Northeastern), and drop the Thanksgiving
pitch. The spring and fall plans don't move.

### 7.4 Phase by phase

**Phase 0: this week and next (now to S)**

- [ ] **Renew `jameskouvlis.com` before 28 October.**
- [ ] **File the featuring nomination by 22 October** (§5.7).
- [ ] Claim the handles on all three platforms (§12, item 3).
- [ ] Build the landing page, with the press kit and the national map.
- [ ] Make the national map image (credits in the image).
- [ ] Draft the listing against §3.4: national keywords, screenshots and the
      flat-country line.
- [ ] Film the last color in southern New England, from public starting
      points.

**Phase 1: submission to launch (S to L−1)**

- [ ] TestFlight: invited friends, or the public link if §12 item 1 says it
      isn't "public".
- [ ] **Run the load test on the national build** and set the Cloudflare rate
      limit (`server/DEPLOY-oracle.md`, Part 11; method in
      [`load-test-oracle.md`](load-test-oracle.md)).
- [ ] Campaign links, one per channel.
- [ ] Draft every launch post and the two pitches. Message the subreddit
      moderators.
- [ ] **L−7: the go/no-go check (§7.3).**
- [ ] L−1, pre-flight: `api/health`, the box's memory, the rate limit, the
      domain, the listing, every link.

**Phase 2: launch week (L to L+7, about 10 hours)**

| day | what |
|---|---|
| **L (Thu 5 Nov)**, 8 am Eastern | Release. Wait for the listing to go live in the US store. Search "sunday drive" and note the rank |
| L, 11 am | Your accounts, Northeastern's channels, r/SideProject. Reply to everything for two hours. Check Cloudflare and the box hourly |
| L+1 (Fri) | r/boston; tech-press tips. Tell testers it's live and ask for an honest rating, never five stars, never with anything in return |
| L+2 to L+3 (weekend) | One drive, filmed |
| L+4 (Mon) | r/massachusetts or r/iOSProgramming |
| L+7 | First numbers (§9) |

**Phase 3: November (L+8 to L+30)**

- [ ] The national map on r/dataisbeautiful, then r/MapPorn days later, and in
      #30DayMapChallenge.
- [ ] Show HN, on a weekday morning.
- [ ] The OSM community.
- [ ] Thanksgiving: the Boston pitch on 23–24 November, promotional text for
      the holiday, and a "scenic way home" short.
- [ ] 1–2 posts a week from footage.

**Phase 4: winter (December to March)**

- [ ] 1–2 posts a week, or fewer. The YouTube backlog from October footage.
- [ ] The New England byway ranking (§5.5).
- [ ] Optional: a desk-only "unchecked" state list once a fortnight, for states
      that show up in the numbers.
- [ ] Plan the spring opener: the update, a list of footage to shoot, the
      press list.

**Seasonal beats after that:**

| when | beat |
|---|---|
| mid-February 2027 | Featuring nomination (*App Enhancements*) for a spring update |
| **29–31 May 2027** | **The spring opener** (Memorial Day): northern state-sub launch posts, New England press, the weekly loop resumes |
| mid-June 2027 | Featuring nomination for foliage, 3 months ahead |
| **mid-September to early November 2027** | **Foliage 2027:** foliage groups, regional press, an in-app event if seasonal content exists |

**Verdict:** a short, national launch built on the map and the builder's
story; a quiet winter; and the New England plan, mostly intact, from Memorial
Day.

---

## 8. The launch-day runbook (L)

1. **7:30 Eastern.** `https://api.jameskouvlis.com/api/health`, the box's
   memory, the Cloudflare rate-limit rule.
2. **8:00.** Release. Refresh until the listing is live, then search "sunday
   drive" and note the rank.
3. **Keep three tabs open:** App Store Connect analytics, Cloudflare
   analytics, your post queue.
4. **11:00.** Post one channel at a time, so each one's replies get your
   attention and the load arrives in waves. National posts bring requests from
   every time zone, into the Pacific evening.
5. **Reply to everything** for two hours. Answer "does it work in X?" with:
   "Yes, anywhere in the contiguous US. It scores every road on one scale, so
   flat country scores lower."
6. **If the server struggles** (5xx errors, slow loops): stop posting, and post
   one line where people are asking ("busy, try again in a few minutes").
   Don't delete anything.
7. **Evening:** write down installs, ratings, requests and what surprised you.

---

## 9. Measuring without adding tracking

No analytics in the app, and App Store builds don't record drives (the
`RECORD_DRIVES` flag; [`privacy-policy.md`](privacy-policy.md)). You don't
need either:

| source | what it tells you |
|---|---|
| **App Store Connect → Analytics** | impressions, page views, conversion, and installs by source, including each **campaign link** |
| **TestFlight, Xcode Organizer** | crashes, hangs, tester feedback |
| **Cloudflare analytics** | requests per day, a proxy for drives planned |
| **TikTok Studio, Instagram Insights, YouTube Studio** | per-post views, sends, saves, follows, and viewer geography |
| **The reviews and comments** | where people are, and whether anyone says "nothing scenic here" or "added an hour" |

**Every Monday, 10 minutes:** the best post and why; which campaign link
converted; the ratings count; any review about boredom or detours.

**Targets (goals, not forecasts):**

- **L+30: 15 ratings**, more than any 2026 scenic-driving entrant had on
  2026-10-18.
- **L+90: 50 ratings.**
- **No review that quotes a claim back at you.**

**Decision rules:**

1. If a channel brings under 10% of attributed installs after four weeks,
   halve its time.
2. If short video brings negligible installs after six weeks of real posting,
   move that time to Reddit data posts and YouTube.
3. **If two reviews in a month report a pointless detour or "nothing
   scenic"**, stop national-reach posting until the app answers it (§5.10,
   items 2–3).
4. Never judge a channel on one post.

---

## 10. Risks and guardrails

| risk | likelihood | mitigation |
|---|---|---|
| **The domain lapses on 28 October**, a week before L, taking the API and the privacy contact with it | certain if ignored | Renew this week |
| **Plains users get detours that buy nothing, and say so** | high | Go/no-go item 6; decision rule 3; never "near you" copy |
| **A New England number leaks into national copy** | medium | §3.4; go/no-go item 6 |
| **The server meets national traffic untested** | medium | Go/no-go item 2; staggered posts; the stop-posting rule (§8) |
| **A listed road is closed, 4WD-only or private** | medium outside New England | §6.3 step 7 |
| **A November launch meets an off-season audience** | certain | Launch on the map and the builder's story; hold New England's seasonal one-shots for May |
| **Name confusion** (WanderWay's "Sunday Drive" feature, Google Drive) | high | Direct links everywhere; check the rank on L. Trademark questions are [`sunday-drive-naming.md`](sunday-drive-naming.md) §4's |
| **Android users can't install** | about 40% of viewers | "iPhone" in captions; count requests |
| **Your home shows up in a video** | high by default | Public starting points; check every recording (§6.4) |
| **A subreddit bans the account** | medium | Read the rules, ask the moderators, one post per sub, days apart |
| **Burnout, or the semester wins** | high | The plan works at 1–2 hours a week in winter. Skipping weeks is allowed |
| **Marketing breaks the privacy promise** | medium | No email list, no pixels, no SDKs without a policy update (§12) |

---

## 11. What it costs

| item | cost |
|---|---|
| Apple Developer Program | $99/yr, paid 2026-10-03; next due about 3 October 2027 |
| `jameskouvlis.com` | about $23/yr at GoDaddy's list renewal price (third-party snapshot, May 2026; confirm at checkout). **Due by 28 October 2026** |
| Hosting | $0 (Oracle Always Free) *(re-check against the national build's memory)* |
| Landing page, press kit | $0 (GitHub Pages) |
| Editing, scheduling, design | $0 (iMovie or DaVinci Resolve, the platforms' schedulers, Canva's free tier) |
| A phone mount | about $15–25 if you don't have one; you need one to navigate legally |
| Gas | the drives you'd take anyway |
| **Time** | about 3 h/week; about 10 h in launch week; 1–2 h/week in winter |

**There is no paid marketing line, and nothing here needs one.**

---

## 12. Decisions for the owner

1. **Does a public TestFlight link count as "public"?** It matters only for
   the week before L. Leaning: it doesn't matter enough to use; invited
   testers are enough.
2. **L = Thursday 5 November, or 12 November?** 5 November needs the featuring
   nomination filed by 22 October and submission by 29 October.
3. **Claim the handles now?** An hour, and it protects the name. Recommended.
   You create the accounts; this plan creates none.
4. **On camera or not?** A face helps building-in-public posts. Voice-over and
   on-screen text also work.
5. **A waitlist or newsletter?** An email list adds a data flow the privacy
   policy doesn't cover. **Recommended: no.** Use GitHub's Watch → Releases
   for people who want to follow along.
6. **Other people's ratings outside New England?** TestFlight builds record
   drives (`privacy-policy.md`). A friend on TestFlight who drives elsewhere is
   the only way anyone will ever check a Western score. It's optional, and
   nothing in this plan depends on it.

---

## 13. The target list

Read every group's rules before posting.

- **National Reddit:** r/dataisbeautiful · r/MapPorn · r/SideProject ·
  r/iOSProgramming · r/roadtrip · r/openstreetmap
- **Home Reddit:** r/boston · r/massachusetts at launch; r/newengland ·
  r/vermont · r/newhampshire · r/maine · r/Connecticut · r/RhodeIsland from
  Memorial Day
- **Northeastern:** Northeastern Global News · *The Huntington News* · NUMedia
- **Tech:** Hacker News (Show HN) · weeklyOSM · OSM US · #30DayMapChallenge ·
  MacStories · 9to5Mac
- **Boston press (Thanksgiving):** Boston.com · Universal Hub · Axios Boston
- **New England press (spring, fall):** see §5.5
- **Spring:** New England Fall Foliage (Jeff Folger) and town groups on
  Facebook · Larz Anderson Auto Museum · BMW CCA Boston · PCA Northeast ·
  Miata and Subaru groups · state byway organizations

---

## 14. Sources

**From this repo:** [`release-plan.md`](release-plan.md) ·
[`branding-brainstorm.md`](branding-brainstorm.md) ·
[`sunday-drive-naming.md`](sunday-drive-naming.md) ·
[`app-store-submission.md`](app-store-submission.md) ·
[`app-store-listing.md`](app-store-listing.md) ·
[`privacy-policy.md`](privacy-policy.md) ·
[`rating-prompt.md`](rating-prompt.md) ·
[`load-test-oracle.md`](load-test-oracle.md) ·
[`us-map-data-findings.md`](us-map-data-findings.md) §7 ·
[`driving-app-features-cost.md`](driving-app-features-cost.md) ·
[`data-sources.md`](data-sources.md) · `server/DEPLOY-oracle.md` Part 11 ·
`pipeline/score.py` · `ios/Sources/BeforeYouDriveView.swift`,
`RouteResults.swift`, `AboutView.swift` · `site/index.html` ·
`data/processed-ne/scored_chunks.parquet` (schema).

**On the local `usa` branch only** (`git show usa:docs/<file>`):
`national-scenery-scoring-verdict.md` §7 (the share of km at 7+ by
landscape), §10, §11, and its plains-detour finding.

**Owner decisions, not in a document:** the 2026-10-18 decisions (no public
New England app; one national scale; release within weeks; no cross-country
drives); the "96% liked at 7+" figure and its basis (52 marks, one rater, New
England); the CarPlay entitlement (2026-10-08).

**The App Store census, 2026-10-18:** Apple's search API
(`itunes.apple.com/search?entity=software&country=us`) for "scenic drive",
"scenic route", "scenic loop", "sunday drive", "aimless drives", "wanderway",
"driveloop", "roads by porsche" and "detour scenic navigation". Plus the App
Store pages of WanderWay Navigation (id6807600062), Detour (id6496858927),
Aimless Drives (id6799342576) and ROADS by Porsche (id1438225964), for
in-app purchases, privacy labels and wording.

**Web, re-checked 2026-10-18:**

- Google's Ask Maps, US, 12 March 2026 — [Google](https://blog.google/products-and-platforms/products/maps/ask-maps-immersive-navigation/), [Droid Life](https://www.droid-life.com/2026/03/12/google-gets-new-ai-powered-ask-maps-feature/)
- TestFlight: up to 10,000 external testers, by email or public link, after Beta App Review — [App Store Connect Help](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers)
- GoDaddy .com renewal, $22.99/yr (third-party, May 2026) — [DomainOffer](https://domainoffer.net/tld/com/godaddy)

**Carried from 2026-09-29, not re-read** *(re-check)*: TikTok's Local feed and
Business accounts; Instagram's Map, sends signal and Trial Reels; carousels;
TikTok search; Apple's featuring-nomination lead times, pre-orders, custom
product pages and in-app events; the US iPhone share; *The Huntington News*
tips; CapCut's terms. The links are in the New England plan's §14
(`git show 0fca74f:docs/marketing-plan.md`).

**Not checked at all** *(re-check)*: #30DayMapChallenge's 2026 dates and
themes; App Review's current turnaround; whether a featuring nomination can be
filed before the build is submitted; the 2027 club calendars.

---

## 15. This week (18–25 October 2026)

1. **Renew `jameskouvlis.com`** before Wednesday 28 October. About $23. The
   API and every installed build depend on it. (10 minutes)
2. **File the featuring nomination** for Thursday 5 November, by Thursday 22
   October (§5.7). (30 minutes)
3. **Claim the handles** on TikTok, Instagram and YouTube, the same day
   (§12, item 3). (30 minutes)
4. **Make the national map image**, with the OpenStreetMap credit in the
   image. It is the launch's best post. (1–2 hours)
5. **Film one late-color drive** in southern New England, from a public
   starting point, if you're driving anyway.

About 3 hours. Nothing gets posted until L.
