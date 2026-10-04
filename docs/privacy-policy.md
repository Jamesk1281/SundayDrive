# Privacy policy — the developer's source copy

> **The user-facing version is `site/privacy/index.html`, live at
> <https://jamesk1281.github.io/SundayDrive/privacy/>.** It is published by
> `.github/workflows/pages.yml` and linked from the app's Sources screen
> (`PrivacyPolicy.url`, `AboutView.swift`). It is §§0–6 below rewritten for a
> driver. This file stays because its citations are what make the page
> checkable. A change to §§0–6 here must change the page too (§8).

**Status, 2026-10-04: published, and current as of main past `f9f1937`.**
- Written 2026-09-19 against `3fb75d6`.
- Name and identifier brought up to date 2026-09-21.
- Hosting brought up to date 2026-09-29, when the routing server moved from
  the developer's laptop to an Oracle Cloud virtual machine (§2.1(a)).
- Coordinates moved out of the request URL the same day (§2.1(a)).
- Approximate-location behaviour tested and described 2026-10-01 (§2.2).
- The stored-settings list corrected the same day (§3, §5).

**It goes out without a lawyer, by owner decision** (`release-plan.md` §8,
decision 3, 2026-09-19). What makes a privacy policy dangerous is asserting
something untrue, so every factual claim in §§1–5 cites the file that makes it
true. Re-check those claims against the code rather than trusting them, and
use §8 for what would make them wrong.

The app is `PRODUCT_BUNDLE_IDENTIFIER: app.sundaydrive`. The identifier locks
at the first build upload, TestFlight included (`docs/app-store-submission.md`
§6), and nothing has been uploaded yet.

---

## 0. What this app is

Sunday Drive plans and narrates driving routes that prefer scenic roads over
fast ones. It runs on iPhone, it talks to one routing server the developer
operates on a virtual machine rented from Oracle Cloud Infrastructure in the
United States, and it uses Apple's Maps services for the map, for address
search and for place names. There is no account, no sign-in, and no way to
create one.

**The app is not published.** At the time of writing it is a single-user
research instrument (`docs/legal-and-ip-audit.md`; the bundle identifier is
`app.sundaydrive` and the marketing version `1.0`, raised from `0.1` on
2026-09-29 for submission). This document is
written as the policy it would need if it were published, which is the only way
to find out what would have to change first.

---

## 1. What the app collects, and what it does not

**No account, no identity.** The app never asks for a name, an email address, a
phone number or a password, and it has no server-side user record to attach one
to. `server/app.py` exposes two endpoints, `/api/route` and `/api/loop`
(`server/app.py:211`, `:288`); neither takes or issues an identifier.

**No tracking, no analytics, no advertising.** The shipped binary contains **no
third-party code at all** — no analytics SDK, no crash reporter, no ad network.
`ios/project.yml` declares no Swift Package, no CocoaPods and no Carthage, and
the only `import`s across `ios/Sources` are Apple's own: `SwiftUI`, `MapKit`,
`CoreLocation`, `AVFoundation`, `UIKit`, `Foundation`, `Observation`. There is
no IDFA, no App Tracking Transparency prompt, and nothing to put in a tracking
domains list.

**No device identifiers.** Nothing in `ios/Sources` reads an advertising
identifier, a vendor identifier, or the device name.

**What is stored on your phone**, besides drive recordings (§3), is kept in
`UserDefaults`. All of it is the app reading back its own data, and one item is
a short history of where you have been going: the destinations you last
searched for.

| What | Where |
| --- | --- |
| **Your five most recent destinations**, each with its name, the town under it and its coordinates, so the home screen can offer them again | `ios/Sources/Recents.swift:13-50`, written by `RouteModel.swift:182-189` |
| The length of the last loop you asked for | `ios/Sources/LoopModel.swift:51-52`, `:247` |
| The chosen guidance voice | `ios/Sources/VoiceCatalogue.swift:118-119` |
| A cache of how long each voice takes to speak | `ios/Sources/VoiceCatalogue.swift:148-149` |
| Whether voice guidance is muted | `ios/Sources/VoiceGuide.swift:351-352` |
| Whether the one-time "Before you drive" notice has been shown | `ios/Sources/PlanningView.swift:47` |
| Whether the app follows the phone's light or dark appearance | `ios/Sources/AboutView.swift:240`, read by `ContentView.swift:23` |

---

## 2. Location

**The app uses your location for one thing: following the route you asked for.**
It requests *when in use* authorization only (`LocationManager.swift:182`,
`:287`) — never "always" — and the purpose string the system shows you is the
one at `ios/project.yml:21`: "Your location is used to follow the route, turn
by turn, while you drive."

**That string does not name the app, deliberately** — iOS already titles the
alert *Allow "Sunday Drive" to use your location?*, so naming the app in the
body said it twice. The name was removed on 2026-09-20 and this quotation was
re-read against `ios/project.yml` at `5aff398` on 2026-09-21. Do not "restore"
a product name to it: neither *"Victory Lap uses your location…"* (what this
document quoted until 2026-09-21) nor a Sunday Drive equivalent exists anywhere
in the project.

**Location continues while the app is in the background, and the blue bar shows
whenever it does.** `UIBackgroundModes` includes `location`
(`ios/project.yml:43-44`), and the app opts into
`showsBackgroundLocationIndicator` (`LocationManager.swift:195-196`), so
background location is always visible in the status bar. Without this, a
locked phone or an incoming call silently ends a drive; the reasoning is written
out at `ios/project.yml:22-42`. Background updates are switched off again when
navigation stops (`LocationManager.swift:208`).

**Accuracy is set to `kCLLocationAccuracyBestForNavigation`**
(`LocationManager.swift:141`) with no distance filter (`:153`) — about one fix
per second while driving. This is the accuracy turn-by-turn guidance needs; it
is also the most precise location iOS will give an app.

### 2.1 Where location goes

Three destinations, and no others.

**(a) To the routing server, to compute a route.** Your start and destination
coordinates are sent in the body of a POST request to `/api/route`
(`RouteService.swift:150-170`), and your start point to `/api/loop`
(`RouteService.swift:211-225`), never in the URL (`formRequest`,
`RouteService.swift:241`, and `RouteServiceRequestTests`, which checks the
built request). While you are driving, a reroute sends your current position
and heading the same way. Nothing else goes with them: no identifier, no
timestamp, no trace, no history.

**The server stores nothing.** `server/app.py` has no database, no log file and
no request logging — it prints two startup lines and nothing per request
(`server/app.py:93`, `:120`), and `serve.py` runs it under `waitress`, which
does not write an access log by default. **Checked on the live machine
on 2026-09-29.** After real route requests had passed through it, a search for
a request coordinate found nothing. The search covered the routing server's
system log, the tunnel client's system log and `/var/log`. The tunnel client
(`cloudflared`) runs at its default log level, which records connections, not
requests.

**The server runs on Oracle's infrastructure.** Since 2026-09-29 the routing
server has run on a virtual machine that the developer rents from Oracle Cloud
Infrastructure, on its free tier, in the US East region (Ashburn, Virginia)
(`server/DEPLOY.md:8-14`, `server/DEPLOY-oracle.md`). Before that it ran on a
laptop the developer owns. The coordinates in each request are processed in
that machine's memory to compute the route, and the server software writes
them nowhere. The machine does have a swap file, so the operating system can
page memory to disk under pressure, and that could briefly include a request
in progress. On 2026-09-29, 14.6 MB of the 4 GB swap file was in use.

But Oracle operates the hardware, the virtualisation layer and the network, so
a third party now runs the machine that handles every coordinate. Oracle's own
management agent also runs inside the virtual machine. The components actually
running on 2026-09-29 were:

- **A monitoring component** that reports CPU and memory use to Oracle. It is
  kept on deliberately. Oracle reclaims free-tier instances that look idle, and
  this component is what reports the memory use that shows this one is not.
- **A log collector whose configuration is empty.** It collects nothing unless
  someone configures it in Oracle's console, and no one has.
- **Oracle's workload-protection scanner (Cloud Guard).**
- **A remote-command component.**

None of these is directed at route requests. Which of them this policy has to
name is a §7 question.

**The request also passes through Cloudflare, which can still read it.** The
deployed backend is reached through a Cloudflare tunnel that terminates TLS
(`server/DEPLOY.md:8-14`, `:118-123`). The coordinates travel in the request
body, not the URL, so they are not in the URLs that access logs record by
default. That narrows the exposure; it does not remove Cloudflare from the
path. Terminating TLS means Cloudflare's edge can technically read the body as
well as the URL, and what it does with either is subject to Cloudflare's own
logging and retention. **Cloudflare's edge is still the one place where
location passes through a third party in transit, outside the developer's
control**, and this policy still names Cloudflare for that reason. Oracle is the
other third party, because it hosts the machine. See §7.

App builds made before 2026-09-29 sent the coordinates in the URL query string.
The server still accepts that form so those builds keep working, but the app
described here does not send it.

**(b) To Apple, for the map, search and place names.** The map is Apple's
(`MapKit`). Typing an address sends it to Apple's search service
(`MKLocalSearchCompleter` in `SearchCompleter.swift:17`, `MKLocalSearch` in
`RouteModel.swift:125` and `LoopModel.swift:78`), and naming the place you are
starting from sends a coordinate to Apple's reverse geocoder
(`PlaceNaming.swift:46`). Apple handles that data under Apple's own privacy
policy, not this one. **Addresses you type are never sent to the routing
server** — only the coordinates Apple resolves them to.

**(c) To a file on your own phone, if a drive is recorded.** See §3.

### 2.2 Precise location and iOS's "approximate" setting

Turn-by-turn guidance needs precise location, and the app does not navigate on
approximate location. It acts only on fixes with a stated error of 65 m or less
(`usableAccuracy`, `LocationManager.swift:76`), and an approximate fix is
kilometres wide: the one measured below was 11,920 m.

**If location is allowed but Precise Location is off, the app asks for precise
location.** It asks when a drive starts and when "My Location" is tapped while
planning (`requestTemporaryFullAccuracyAuthorization`,
`LocationManager.swift:188-190` and `:237-239`). iOS shows its own prompt,
*Allow "Sunday Drive" to use your precise location once?*, with the purpose
string from the `NSLocationTemporaryUsageDescriptionDictionary` entry in
`ios/project.yml`: "Turn-by-turn guidance needs your precise location to follow
the route." The two answers are **Allow Once** and **Don't Allow**. Allow Once
does not change the setting. The next launch started with Precise Location off
again, and asked again. Apple's documentation (`CLLocationManager.h`) says the
grant lasts while the app is in use, and through a drive for as long as the
blue location indicator shows.

**If you decline, the app says so and does not navigate.** The drive's banner
reads "Precise Location is off · Turn it on in Settings to navigate". Every
approximate fix is discarded, so no position is recorded (§3). Until a usable
fix arrives, the banner says "Waiting for GPS" rather than a distance. Declined
from "My Location", planning goes ahead from the approximate fix, so the start
of a planned route can be kilometres out.

*Observed 2026-10-01 in the simulator (iPhone 17 Pro, iOS 26.4), with Precise
Location switched off in Settings and a drive played along Northampton →
Amherst. Before the change, no fix was ever accepted and the screen said "50 ft
away · Head to the start of your route". After it, starting a drive raised the
prompt. **Allow Once** switched the grant to full accuracy, and from then on 5 m
fixes were accepted once a second and the drive navigated. **Don't Allow** left
the banner above, with the one approximate fix that arrived (11,920 m)
discarded.*

---

## 3. Drive recordings

**Every navigated drive is recorded** — `RouteModel.startNavigation` and
`startLoopDrive` open a `DriveTrace` unconditionally (`RouteModel.swift:267-273`,
`:296`), and there is no setting to turn it off. *(Corrected 2026-09-29. Until
then this section said the app "can" record and §5 called recording "a
deliberate act, not a default"; both were wrong from the day the draft was
written.)* A recording contains, once per second, the
raw GPS fix and where it fell on the route: latitude, longitude, horizontal
accuracy, altitude, speed and a timestamp; plus the route being followed, any
"nice"/"dull" verdicts tapped during the drive, when the app went to the
background, and how the drive ended (`DriveTrace.swift:115`, `:199`, `:258-267`,
`:326-337`, `:360`, `:368`). **Taken together that is a detailed record of where
you drove and when.**

- **It stays on your phone.** Recordings are written to the app's own
  `Documents/traces` directory (`DriveTrace.swift:131-134`) and there is no
  upload path anywhere in the app — no `URLSession` call sends them, no share
  sheet, no mail composer. The only network code in the app is the two route
  requests in §2.1(a).
- **You can read and delete them yourself.** `UIFileSharingEnabled` and
  `LSSupportsOpeningDocumentsInPlace` (`ios/project.yml:51-52`) expose that
  folder to the Files app and to a Mac over a cable. Deleting a file there
  deletes the recording; the app keeps no copy.
- **Deleting the app deletes them.** They live in the app container.
- **They are included in an iPhone backup.** Nothing in `ios/Sources` marks the
  traces directory as excluded from backup, so if you back up your phone to
  iCloud or to a computer, your drive recordings are in that backup, under
  whatever protection you have given it.

There is no retention limit and no automatic deletion: a recording stays until
you remove it.

---

## 4. Children

The app is not directed at children, has no social features, no user-generated
content that anyone else can see, and no advertising. It is a driving
application. *(Whether that is enough to answer COPPA and the App Store's Kids
Category rules is a §7 item.)*

---

## 5. Your choices

- **Refuse location.** The app cannot route without it, but nothing else about
  the phone is read.
- ~~**Don't record.**~~ Not a choice the app offers: every navigated drive
  is recorded (§3). Deleting recordings is the control there is.
- **Delete recordings** at any time, from the Files app or a Mac (§3).
- **Reset the stored destinations and settings** by deleting the app.

There is no server-side data about you to request, correct or delete, because
none is kept.

---

## 6. Contact

**privacy@jameskouvlis.com** — chosen 2026-09-29. It is a Cloudflare Email
Routing alias on the same domain as the API, forwarding to the owner's inbox,
and a test message was received through it the same day. An alias rather than
a personal address because it is published. It dies with the domain, which
also carries `api.jameskouvlis.com`, so renewing the domain keeps both alive.

---

## 7. The open questions, and how each was settled

This section once listed what "a lawyer has to clear". On 2026-09-19 the owner
decided to publish without one (`release-plan.md` §8, decision 3), and each
question was settled in another way:
- by an engineering change,
- by a conservative declaration,
- by a threshold test,
- or by a choice of territory.

The numbering is kept because `release-plan.md` decision 3 maps these items by
number. The decision has an expiry. Revisit it if money changes hands, an
account system appears, a third-party SDK is added, or EU/UK territories are
switched on.

1. **The Cloudflare edge disclosure (§2.1(a)).** Settled 2026-09-29.
   - The app sends coordinates in a POST body, so they are no longer in the
     URLs that access logs record by default
     (`docs/coordinates-out-of-the-url-brief.md`).
   - §2.1(a) names Cloudflare as the service that carries them, because
     Cloudflare terminates TLS and can technically read the body.
2. **Whether precise location counts as "collected".** Settled: **yes**, which
   is the conservative answer. The privacy manifest and the nutrition label
   both say so. See `docs/app-store-submission.md` §3 for why, and for what
   would have to change for the answer to change.
3. **CPRA.** Settled by its own thresholds. It applies to businesses with more
   than $25M in revenue, or 100,000+ consumers, or revenue from selling
   personal data. The app meets none of these, and it sells nothing.
4. **GDPR.** Settled by shipping in the **United States only**. The territory
   is a checkbox in App Store Connect (`docs/app-store-submission.md` §6).
   Switching on an EU or UK territory reopens this item.
5. **Children (§4).** Settled at submission. App Store Connect's age-rating
   questionnaire decides the rating; answer it honestly.
6. **Reduced-accuracy behaviour (§2.2).** Settled 2026-10-01. It was tested in
   the simulator and found broken: no fix was ever accepted, and the screen
   said "50 ft away · Head to the start of your route". It was then fixed and
   tested again, and §2.2 describes what was observed.
7. **The contact address (§6).** Settled 2026-09-29: privacy@jameskouvlis.com.
8. **The app's name.** Settled 2026-09-21: **Sunday Drive**
   (`docs/sunday-drive-naming.md`), renamed from Victory Lap
   (`docs/victory-lap-naming.md`).
9. **Oracle as the host (§2.1(a)).** Settled 2026-09-29. §2.1(a) names Oracle
   as the host, in the same breath as Cloudflare.
   - The region is `us-ashburn-1`, so shipping US-only still keeps GDPR out
     of scope. A host established in the EU, such as Contabo GmbH, the
     planned paid fallback, would reopen item 4.
   - Optional: three of the four Oracle agent components in §2.1(a) (the log
     collector, the workload scanner and the remote-command component) can be
     switched off in Oracle's console. The monitoring component cannot be
     switched off without risking reclamation.

## 8. What would make this document wrong

Re-check it if any of these change, because each one is load-bearing above:

- **Any new `URLSession` call in `ios/Sources`.** Today there are two route
  requests and nothing else; §1 and §3 both depend on that.
- **Any logging, database or analytics added to `server/`.** §2.1(a) asserts
  the server persists nothing.
- **Any third-party package added to `ios/project.yml`.** §1's "no third-party
  code at all" is the strongest claim here and the easiest to invalidate.
  (Note that the `dependencies:` entry at `ios/project.yml:97` is *not* a
  package — it is the test target depending on the app target.)
- **Any upload, share or sync feature for drive traces.** §3 rests on there
  being none.
- **A move off the Cloudflare tunnel, or any coordinate put back into a
  request URL.** Either one changes §2.1(a) and §7.1. The move of coordinates
  out of the query string into a POST body happened on 2026-09-29, and those
  two sections were rewritten with it; `RouteServiceRequestTests` fails if
  one comes back. Removing the server's GET support, kept for older builds,
  would not change this document.
- **A change of the machine behind the tunnel.** This includes a new hosting
  provider, a new region, or a second origin such as the developer's laptop
  rejoining as a second connector, which `server/DEPLOY-oracle.md` Part 10
  describes. The tunnel and the hostname stay the same, so the trigger above
  does not fire, but §0, §2.1(a) and §7 item 9 all change. **This line was
  missing until 2026-09-29, and the move to Oracle is what exposed the gap.**
- **Enabling request logging anywhere on the serving machine.** That covers
  `cloudflared` at debug level, and an Oracle log-collection rule pointed at a
  file that holds requests. §2.1(a)'s "writes them nowhere" was checked
  against the defaults.
- **`requestAlwaysAuthorization`, or dropping the background location
  indicator.** §2 describes when-in-use with a visible blue bar.
- **An off switch for drive recording.** §3 and §5 say there is none.
- **A change to anything in §§0–6 must also change `site/privacy/index.html`.**
  That page is the published copy, and nothing checks the two against each
  other except this line.
