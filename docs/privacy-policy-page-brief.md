# Brief: publish the privacy policy as a public page (release-plan §10)

**Status: decided, not built.** Written 2026-09-29 against `main` after
`9d99638`. Nothing has been touched for this: no `site/`, no `.github/`, and no
GitHub Pages setting. The repo has no `.github/` directory at all. GitHub Pages
is **not enabled**, and enabling it is the owner's job (§5), not this session's.

Answers the "Privacy policy **URL**" row of `docs/release-plan.md` §10, which is
a **hard submission gate**. App Store Connect will not accept a submission
without a policy URL.

---

## 1. The goal

A user-facing privacy policy at a stable public URL, and a link to it inside the
app.

- **Superseded 2026-09-29:** the repo has since been renamed to
  `Jamesk1281/SundayDrive`, and Pages does not redirect a renamed project
  site, so the URL is `https://jamesk1281.github.io/SundayDrive/privacy/`.
  The paragraph below is as briefed.
- **The URL (as briefed):** `https://jamesk1281.github.io/Scenic/privacy/`. The repo is
  `Jamesk1281/Scenic` and is public (it has been since 2026-09-19), so a
  project Pages site is free. The `/Scenic/` in the path is the old name. It
  stays **on purpose**: the repo keeps its old name, and renaming the repo to
  change a URL is out of scope. The privacy-policy URL in App Store Connect can
  be edited later, so this does not lock anything in.
- **The in-app link.** App Store Review Guideline 5.1.1(i) asks for the policy
  link in App Store Connect **and inside the app**, somewhere easy to find. The
  app has no link today: `ios/Sources/AboutView.swift` has no privacy entry.
  The About screen is where it goes, next to the data-sources credits.

## 2. The source, and why the page is a rewrite, not a copy

`docs/privacy-policy.md` is the source of truth, but it is a **developer
document**:

- Every claim cites `file:line`, for example `RouteService.swift:150-170`.
- §7 is addressed to a lawyer. That is moot now: `release-plan.md` §8
  Decision 3 is "no lawyer; US-only at launch".
- §8 is a list of re-check triggers for the developer.
- The banner says "DRAFT, NOT PUBLISHED".

The public page is **§§0–6 rewritten for a driver**: plain sentences, no file
paths, no §7 and no §8. Every claim on the page must still be one that
`privacy-policy.md` makes. The job is to translate the document, not extend it.

## 3. What the page must say (each item is in the draft already)

1. No account, no identifiers, no analytics, no ads, no third-party code (§1).
2. The three settings kept on the phone (§1).
3. Location: when-in-use only, the blue bar in the background, and precise
   accuracy while driving (§2).
4. Where location goes (§2.1): the routing server, as a POST body, stored
   nowhere. **Cloudflare is named** as the network in the path, and it can read
   requests. **Oracle Cloud (US East, Ashburn) is named** as the host. Apple
   handles map, search and place names under its own policy.
5. Drive recordings stay on the phone. You can see and delete them in the Files
   app. They are removed when the app is deleted, and they are **included in
   iPhone backups** (§3).
6. Not directed at children (§4). Your choices (§5).
7. Contact (§6). **The owner has not picked an address yet.** Write the literal
   `CONTACT_ADDRESS_TBD` and add a test (§6, item 4) that fails while it is still
   there, so the page cannot be published without one.
8. An "Effective date" line.

## 4. Traps

- **Do not serve Pages from the `/docs` folder.** That is the obvious setting,
  and it is wrong here: it would turn all 70-odd internal documents into
  rendered public pages under the policy's domain, including the legal audit
  and the trademark findings. Put the page in a new `site/` directory, and
  deploy **only `site/`** with a GitHub Actions workflow
  (`.github/workflows/pages.yml` using `actions/upload-pages-artifact` and
  `actions/deploy-pages`, triggered on pushes to `main` that touch `site/**`,
  plus `workflow_dispatch`). The repo still being public is no reason to
  publish the whole folder as a website.
- **Do not overclaim.** "We never store or share your location" is false:
  Cloudflare terminates TLS and can read request bodies (`privacy-policy.md`
  §2.1(a)). Keep the draft's exact claim, which is that the server writes
  nothing and the network in between can read it. The same goes for
  approximate location. §2.2 says that path is **untested**, so the page may
  say only that turn-by-turn guidance needs precise location. It must not say
  what happens without it.
- **Two copies will drift.** Add a line to `privacy-policy.md` §8, "A change to
  anything in §§0–6 must also change `site/privacy/index.html`", and replace the
  "NOT PUBLISHED" banner with a pointer to the page and its URL. Do not delete
  the draft: its citations are what make the page checkable.
- **The About-screen link has test neighbours.** `ios/Tests/AttributionTests.swift`
  asserts the About screen's route-guidance notice character for character, and
  asserts that exactly one exists. Add the link without disturbing that text.
  Use SwiftUI `Link` with the URL as one constant. It must not be built from
  `SundayDriveAPIBaseURL`, which is the API host, not the policy host.
- **Plain HTML, no Jekyll theme, no external assets.** One self-contained
  `index.html` with inline CSS that reads well on a phone, plus a
  `site/index.html` that redirects to `privacy/`. No trackers, fonts or CDN
  scripts: a privacy page that loads Google Fonts contradicts itself.

## 5. What the owner does (not this session)

This session must **not** change repository settings or merge to `main`.

1. Pick the contact address (a monitored alias) and replace
   `CONTACT_ADDRESS_TBD`.
2. GitHub → `Jamesk1281/Scenic` → Settings → Pages → Source: **GitHub Actions**.
3. Merge, then check the workflow run and open the URL.
4. Paste the URL into App Store Connect → App Privacy → Privacy Policy URL.

## 6. Done looks like

1. On a branch off `main`: `site/privacy/index.html`, `site/index.html` and
   `.github/workflows/pages.yml`, following §§2–4.
2. `privacy-policy.md` has its banner and §8 updated as §4 says.
   `release-plan.md` §10's policy-URL row reads "built, awaiting contact
   address and Pages enablement".
3. An About-screen link to the URL, with the iOS suite still green.
4. A backend test in `tests/` (run as `.venv/bin/python -m pytest tests/` from the main checkout's venv) that
   checks three things. `site/privacy/index.html` exists. It contains no
   `<script src` and no `fonts.googleapis`. And it contains no
   `CONTACT_ADDRESS_TBD`. That last check is **expected to fail until the
   owner supplies the address**. Mark it `xfail(strict=True)` with that reason,
   so replacing the placeholder turns it into an XPASS failure, which prompts
   removing the marker.
5. A short report back: the branch name, the test counts, and anything in the
   draft that could not be put in plain words without changing what it claims.
