# Brief: the support page (App Store Connect's Support URL)

**Status: decided, not built.** Written 2026-10-04 against `main` at
`08eea85`. Nothing under `site/` has been touched for this brief. The content
and scope below are decided. **Do not re-derive them; build them.**

## The goal

App Store Connect will not accept a submission without a **Support URL**. The
URL will be **`https://jamesk1281.github.io/SundayDrive/`**, which
`.github/workflows/pages.yml` publishes from `site/index.html`.

**Today that page is not a support page.** `site/index.html` is 14 lines: a
`<meta http-equiv="refresh" content="0; url=privacy/">`, a canonical link,
and one link to the privacy policy. A reviewer who opens the Support URL lands
on the privacy policy, with no contact address and nothing about the app.

**Why it matters.** App Review guideline 1.5 (Developer Information) asks that
"your app and its Support URL include an easy way to contact you". The
pre-submission review checked this. Its §5, "Guidelines that apply and hold",
lists 1.5 as satisfied *only if* the landing page carries the contact address,
and notes that today's `site/index.html` is "a title and one link". It is
`docs/app-store-submission.md` §8 row 12. That doc's §2 points here too.

## What to build

Replace `site/index.html` with a **self-contained support page**, in this
order.

1. **What it is**, in two or three sentences. Sunday Drive is a free iPhone
   app (iOS 17 or later). It plans the scenic way to somewhere, or a loop from
   where you are, in the six New England states: Connecticut, Maine,
   Massachusetts, New Hampshire, Rhode Island and Vermont. Every road is scored
   for scenery from open data. No account, no ads, no tracking. Open source,
   linking to `https://github.com/Jamesk1281/SundayDrive`.
2. **Contact**, prominent and near the top: a `mailto:` link to
   **`support@jameskouvlis.com`**. The owner is creating that Cloudflare Email
   Routing address (see Trap 4). The custom EULA names the same address
   (`docs/app-store-submission.md` §1).
3. **Common questions.** Keep them short, and only claim what is true on
   `main`:
   - *"It says the point is outside the covered road network."* Sunday Drive
     covers New England only. From anywhere, type a New England town as your
     start. **Loop** and **My Location** only work when you are in New
     England. This is the out-of-region screen a reviewer or a visitor meets
     (`pre-submission-review-verdict.md` AR-1 and M-2).
   - *"It asks for Precise Location."* Turn-by-turn guidance needs your
     precise position.
     - With Precise Location off, starting a drive asks to use it for that
       drive.
     - If you decline, the app cannot navigate and says so. Turn it on in
       Settings, under Sunday Drive → Location.
     - This behaviour is `09890a8`, merged in `f9f1937`.
   - *"Does it work offline, on CarPlay, or on Android?"* No. Routes are
     computed on the server, so it needs a data connection. There is no
     CarPlay or Android version.
   - *Safety.* Mount the phone and don't handle it while driving. Some roads
     close for part of the year and the app may not know, so follow posted
     signs and closures.
   - *"What does the app keep about me?"* **Link to the privacy policy and say
     nothing more** (Trap 2).
4. **Links:** the privacy policy (relative link `privacy/`, Trap 1) and the
   source code on GitHub.
5. **Data credits**, as a short list. Take the names and licences from
   `DataSources` in `ios/Sources/AboutView.swift:126-206`:
   - "Map data from OpenStreetMap", linking to
     `https://www.openstreetmap.org/copyright`.
   - ESA WorldCover (CC BY 4.0).
   - Terrain Tiles (AWS Open Data).
   - "Basemap and place search © Apple".

   Don't re-word the licences. If a credit has more than one line in the app,
   name the source here and say the full credit is on the app's Sources
   screen.
6. **App Store badge: an HTML comment placeholder only.** It is added when the
   app has an App Store ID (Trap 3).

**Look:** match `site/privacy/index.html`. Copy its `:root` palette, its
`prefers-color-scheme: dark` block, its system-font stack and its
`<meta name="referrer" content="no-referrer">`. It must read at 375 px with no
horizontal scroll. The `<title>` is "Sunday Drive · Support".

**Test:** add `tests/test_support_page.py`, in the style of
`tests/test_privacy_page.py`. Plain substring checks, parametrized where
there are several. It should assert:
- the page exists;
- no `<script src`, no `fonts.googleapis`, and no `src="http` or
  `href="http…\.css"` asset loads (links to other sites are fine);
- no `http-equiv="refresh"`;
- `mailto:support@jameskouvlis.com` is present;
- the privacy link is relative (`href="privacy/"`), and no `href="/` appears.

## Traps

1. **Absolute paths break on this host.** Pages serves the repo as a *project
   site* under `/SundayDrive/`. So `href="/privacy/"` resolves to
   `jamesk1281.github.io/privacy/`, which is a 404. Use relative links
   (`privacy/`). The in-app link (`PrivacyPolicy.url`,
   `AboutView.swift:217-218`) is absolute and correct: leave it alone.
2. **The privacy page is the one place that says what the app keeps.** It has
   just changed: `08eea85` (merged 2026-10-04) switched drive recording and
   both scenery-rating controls off in every build
   (`DriveTrace.isEnabled = false`), and rewrote `site/privacy/index.html` to
   say so.
   - **Do not touch `site/privacy/index.html` or `tests/test_privacy_page.py`.**
   - **Do not describe recording, the rating buttons or stored data on the
     support page.** Link to the privacy policy instead. A second description
     is a second thing to keep true, and recording is meant to come back one
     day.
3. **Load nothing from anywhere else, including the App Store badge later.**
   The privacy page's test enforces this rule for that page, and a support
   page that pings a third-party server contradicts the "no tracking" line on
   it. Apple's badge artwork must be downloaded from Apple's marketing
   resources and committed under `site/` when it is added. Never hotlink it.
   No web fonts and no analytics.
4. **The contact address may not route yet.** `support@jameskouvlis.com` is
   new.
   - `privacy@jameskouvlis.com` is routed and was tested on 2026-09-29.
     `support@` is not confirmed yet.
   - Build with `support@` anyway. **Do not merge to `main` and do not push.**
     The master session merges after the owner confirms a test email arrived.
   - Do not quietly swap in `privacy@`: the EULA names `support@` too.
5. **Publishing is a push, so nothing here goes live by accident.**
   `pages.yml` runs only on a push to `main` that touches `site/**`.
   - Never switch Pages to "deploy from a branch" with `/docs`. That would
     publish every internal document.
   - Do not edit `pages.yml`.
6. **Don't put the owner's name, PO box or phone on the page.** Guideline 1.5
   needs only a way to reach the developer. The postal address lives in the
   EULA because Apple's minimum terms require it there, not here.
7. **Don't over-claim.** These are true today:
   - free;
   - iPhone only;
   - New England only;
   - no account, ads or tracking (`docs/app-store-submission.md` §3);
   - open source (Apache-2.0).

   These are **not** true:
   - "nothing leaves your phone" (coordinates go to the routing server);
   - "works offline";
   - "all of the US";
   - "CarPlay".

## Done looks like

1. `site/index.html` is the support page above. It has no redirect, loads
   nothing external, reads in light and dark, and has no horizontal scroll at
   375 px.
2. `tests/test_support_page.py` exists and passes, and
   `tests/test_privacy_page.py` still passes.
3. Proof in the session's report: a screenshot of the page at phone width in
   light and in dark, opened locally (`file://…/site/index.html`, or
   `python3 -m http.server` from `site/`).
4. Committed on the session's own branch off `main`, **not merged and not
   pushed** (Trap 4).
5. A list of anything that could not be verified. At minimum, the email route,
   which only the owner can test.

**Out of scope:**
- a "Contact" or "Support" row inside the app (iOS work, kept out of a
  site-only change);
- screenshots, a press kit and the marketing landing page
  (`marketing-plan.md` §5.7), which this page can grow into later;
- any change to the privacy page.
