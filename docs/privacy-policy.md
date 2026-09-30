# Privacy policy — DRAFT, NOT PUBLISHED

**Status: drafted 2026-09-19, published nowhere; name and identifier brought
up to date 2026-09-21; hosting brought up to date 2026-09-29, when the routing
server moved from the developer's laptop to an Oracle Cloud virtual machine
(§2.1(a), §7 item 9); coordinates moved out of the request URL 2026-09-29
(§2.1(a), §7 item 1).** Checkable: `git grep -l 'privacy polic'` finds no URL
in `ios/`, and App Store Connect has never been given one. The app itself is
`PRODUCT_BUNDLE_IDENTIFIER: app.sundaydrive` at `MARKETING_VERSION: "1.0"`
(`ios/project.yml:66`, `:74`) — the identifier changed with the 2026-09-20
rename and **again** with the 2026-09-21 rename to Sunday Drive
(`docs/sunday-drive-naming.md`), and is **not** final — it locks at the
first build upload, TestFlight included, not at submission
(`docs/app-store-submission.md` §6). Nothing has been uploaded.

> **This is a draft for review. It is not published anywhere, it is not linked
> from the app, and it is not the policy URL that App Store Connect asks for.**
>
> **It has not been reviewed by a lawyer, and it must be before it is
> published.** `docs/licensing-open-questions.md` puts the reason plainly: being
> wrong in a published privacy policy is worse than not having one, because a
> published policy is a representation to users and to regulators, and an
> inaccurate one is actionable in a way that silence is not. §7 below lists
> exactly which claims need clearing and why.
>
> Written 2026-09-19 against `main` at `3fb75d6`. Every factual claim in §§1–5
> cites the file that makes it true, so the draft can be re-checked against the
> code rather than trusted.

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

**What is stored on your phone** — three small settings in `UserDefaults`, all
of them the app reading back its own preferences:

| What | Where |
| --- | --- |
| The chosen guidance voice | `ios/Sources/VoiceCatalogue.swift:118-119` |
| A cache of how long each voice takes to speak | `ios/Sources/VoiceCatalogue.swift:148-149` |
| Whether voice guidance is muted | `ios/Sources/VoiceGuide.swift:351-352` |

---

## 2. Location

**The app uses your location for one thing: following the route you asked for.**
It requests *when in use* authorization only (`LocationManager.swift:145`,
`:218`) — never "always" — and the purpose string the system shows you is the
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
`showsBackgroundLocationIndicator` (`LocationManager.swift:150-151`), so
background location is always visible in the status bar. Without this, a
locked phone or an incoming call silently ends a drive; the reasoning is written
out at `ios/project.yml:22-42`. Background updates are switched off again when
navigation stops (`LocationManager.swift:163`).

**Accuracy is set to `kCLLocationAccuracyBestForNavigation`**
(`LocationManager.swift:104`) with no distance filter (`:116`) — about one fix
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

The app does not currently handle reduced accuracy: there is no
`requestTemporaryFullAccuracyAuthorization` call anywhere in `ios/Sources`.
Turn-by-turn guidance needs precise location to work at all. *(Behaviour under
an approximate-location grant is untested — see §7.)*

---

## 3. Drive recordings

The app can record a drive to a file. A recording contains, once per second, the
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
- **Don't record.** Recording is a deliberate act, not a default of using the
  app.
- **Delete recordings** at any time, from the Files app or a Mac (§3).
- **Reset the three stored settings** by deleting the app.

There is no server-side data about you to request, correct or delete, because
none is kept.

---

## 6. Contact

*Placeholder — an email address has to go here, and it has to be one that is
monitored.* App Store Connect requires a contact route for privacy requests, and
CPRA and GDPR both assume a way to reach the controller. **This is an owner
decision:** which address, and whether it should be an alias rather than a
personal one, given that it will be published.

---

## 7. What a lawyer has to clear before this is published

The engineering facts above are verifiable and I have verified them. The legal
characterisations are not mine to make. In order of how much turns on them:

1. **The Cloudflare edge disclosure (§2.1(a)).** The claim "the server stores
   nothing" is true of the code and false of the *system*, because coordinates
   still pass through a third party that terminates TLS. **The
   engineering half is done (2026-09-29):** the app now sends coordinates in a
   POST body rather than the URL query string
   (`docs/coordinates-out-of-the-url-brief.md`), so they are no longer in the
   URLs that access logs record by default. What is left is the legal half.
   Cloudflare can still technically read the body, so a lawyer still needs to
   decide whether Cloudflare is a processor to be named (this draft names it)
   and whether the §2.1(a) wording discloses it adequately. The privacy
   manifest is unchanged by this: precise location stays declared as
   collected (item 2).
2. **Whether precise location counts as "collected".** Apple's definition turns
   on retention beyond servicing the request in real time. On the code alone the
   answer is no; with Cloudflare in the path it is arguably yes. The privacy
   manifest and the nutrition label both currently answer **yes**, which is the
   conservative choice — see `docs/app-store-submission.md` §3 for the full
   reasoning and for what would have to be true to change it.
3. **CPRA.** Precise geolocation is "sensitive personal information" under
   California law, which brings its own notice and limit-use obligations. Does a
   free single-purpose app with no sale of data and no business-size threshold
   met actually fall in scope? Probably not on thresholds — but "probably not"
   is not a thing to publish.
4. **GDPR.** If the app is downloadable in the EU/UK, there is a controller
   (the owner), a lawful basis to name, and a set of data-subject rights to
   describe. Location data is not formally "special category", but regulators
   treat routine location history as high-risk. The territory list in App Store
   Connect is an owner decision that changes this answer.
5. **Children (§4).** Whether the assertion is sufficient, and what age rating
   the listing should carry.
6. **Reduced-accuracy behaviour (§2.2).** Not a legal question but a factual gap
   in this draft: nobody has tested what the app does when iOS grants
   approximate location. The policy should not describe behaviour that has not
   been observed. **Test it, then write what happens.**
7. **The contact address (§6).**
8. ~~**The app's name.**~~ **Resolved 2026-09-20, and again 2026-09-21.** The
   app is **Sunday Drive** (`docs/sunday-drive-naming.md`), renamed from Victory
   Lap (`docs/victory-lap-naming.md`), and this document was updated with it.
   The audit's item 1 — "Scenic" being taken by a senior direct competitor, and
   descriptive — is what the first rename answered; the second was a change of
   fit, not of risk.
9. **Oracle as the host (§2.1(a)).** *Numbered last so that
   `docs/release-plan.md` Decision 3, which maps these items by number, keeps
   its numbering. By weight it belongs beside item 1.* Since 2026-09-29 the
   routing server has run on an Oracle Cloud Infrastructure virtual machine,
   not on hardware the developer owns. A lawyer needs to decide three things.
   First, whether Oracle is a processor or service provider that the policy
   must name. Second, how
   Oracle's own terms for its free tier bear on that. Third, whether §2.1(a)'s
   description of Oracle's in-VM agents is enough. Two facts bear on the
   answer. The region is in the US, which keeps `docs/release-plan.md`
   decision 3's "US-only at launch" premise intact. (A host established in the
   EU, such as Contabo GmbH, the planned paid fallback, would reopen it.) And
   the draft's own §8 trigger ("a move off the Cloudflare tunnel") did not
   catch this change, because the tunnel stayed the same and only the machine
   behind it changed. §8 now lists a change of host too. **Engineering can
   shrink this one as well.** Three of the four agent components in §2.1(a)
   (the log collector, the workload scanner and the remote-command component)
   are optional plugins that can be switched off in Oracle's console. The
   monitoring component cannot be switched off without risking reclamation.

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
