# Licensing: the three open questions, answered

**Researched 2026-09-19 against `main` at `378aaee`. Nothing was changed.** No
file under `ios/`, `server/`, `pipeline/` or `tests/` was touched, no `LICENSE`
was added, and no licensing decision was made on anyone's behalf.

This document answers the three questions left open by
[`licensing-open-questions-brief.md`](licensing-open-questions-brief.md). It is
the *residue* of the legal and IP audit, not a replacement for it — that audit
registers ten items against primary sources and is right about every claim
re-checked today. Read it first if you are starting cold.

**I am not a lawyer and this is not legal advice.** It is a set of documented
options with their consequences. Three items below are marked as genuinely
needing a professional, and one is marked as not retrievable from this machine.
Those labels are used sparingly and mean what they say.

**The headline.** Two of the three questions came back differently than expected:

1. **The ODbL hypothesis was half wrong, and the half that was wrong has already
   fired.** ODbL does not reach the Python. But `docs/route-census/census-pairs.csv`
   contains **1,621 distinct OpenStreetMap place nodes** covering all of New
   England, it is served anonymously from `raw.githubusercontent.com` today, and
   by the OSM Foundation's own board-endorsed guideline that extraction is
   Substantial. Share-alike is not a future risk here. It is live.
2. **Apple's §3.3.15 no longer exists.** The agreement was restructured; the
   route-guidance clause is now §3.3.3(F)(iii). The required notice string is
   byte-for-byte identical, so the audit's quoted text is safe — but its
   *citation* is stale, and §2.5 has been materially rewritten since 2021 in a
   way that makes the drive-trace item harder, not easier, to dismiss.

---

## Gap 1 — the repository is public and carries no licence

### What is true today

Measured 2026-09-19, anonymously, with no credentials presented:

```
curl https://api.github.com/repos/Jamesk1281/Scenic
  →  private: False   visibility: public   license: None   forks_count: 0

git ls-tree -r main --name-only | grep -iE '^(LICENSE|COPYING|NOTICE|COPYRIGHT)'
  →  (nothing)
```

125 tracked files, 133 commits across 16 published branches, no licence file of
any kind. Under the Berne Convention and US copyright law the default for a
published work with no licence grant is **all rights reserved**. GitHub's Terms
of Service §D.5 ("License Grant to Other Users") carve out exactly one
exception: by making a repository public you "agree to allow others to view and
'fork'" it, granting other users "a nonexclusive, worldwide license to use,
display, perform and reproduce (by forking) Your Content **through the
Service**." That grant stops at GitHub's edge. Nobody acquires any right to
copy, modify or redistribute the work outside it. §D.5 then says the quiet part
plainly: "You may grant additional rights by adopting a license."

**So the current terms are not a choice. They are a default inherited by not
acting.** That default may be exactly right — but it should be the answer to a
question somebody asked.

`forks_count: 0` is worth recording, because it means the practical cost of the
decision is still near zero. Un-licensing a public repository does not reach
copies already taken; today there are none on GitHub.

### 1a — Intent: three options, and what each costs

The choice turns on intent, and intent is not a research question. What research
can do is price each option.

| | **Leave it all-rights-reserved, and say so** | **MIT** | **Apache-2.0** |
| --- | --- | --- | --- |
| Satisfies "readable so people can see the work" | yes | yes | yes |
| Satisfies "reusable by others" | no | yes | yes |
| Express patent grant | no | **no** | **yes** |
| Reserves the project name | n/a (everything reserved) | **no** | **yes** (§6) |
| Blocks a later paid App Store binary | no | no | no |
| Blocks a later relicence | no | effectively yes, for released versions | effectively yes, for released versions |
| Effort | one README sentence | one file | one file + NOTICE discipline |

Three things to know before choosing:

- **The choice is close to irreversible in one direction only.** You can always
  move from all-rights-reserved to a permissive licence. Moving back does not
  reach copies already distributed under the permissive terms. If you are
  undecided, undecided-and-explicit is a real option, not a failure to decide.
- **Apache-2.0 §6 reserves the name**, verbatim: "This License does not grant
  permission to use the trade names, trademarks, service marks, or product names
  of the Licensor, except as required for reasonable and customary use in
  describing the origin of the Work and reproducing the content of the NOTICE
  file." That matters here specifically, because the audit's largest item is that
  the working title is already taken by a senior direct competitor and has to
  change. MIT reserves nothing; a permissive licence with no trademark clause
  makes the eventual name harder to hold, not easier.
- **Whatever you pick, it cannot honestly be a blanket statement**, because of
  1b: one directory in this repo already carries someone else's licence terms.

**Recommendation: Apache-2.0 for the code, if the goal is for others to be able
to use it.** It is the only option here that carries both a patent grant and a
name reservation, it costs one file, and it does not close any door the project
has open — including a paid App Store release (see 1d). **If the goal is only
that the work be readable, then the honest answer is to keep all rights reserved
and add one sentence to the README saying so**, which is strictly better than
today's silence and preserves every option.

**This is the owner's decision and it is deliberately not made here.** No
`LICENSE` file has been committed.

### 1b — Does ODbL reach this repository?

**The brief's hypothesis was: it does not, because `pipeline/*.py` is
independently authored software that *processes* OSM, and is neither a database
nor a Produced Work. The brief also named what would kill the hypothesis: "any
committed artifact that is itself substantially derived from OSM content."**

**That artifact exists. The hypothesis survives for the code and fails for the
data.** Both halves matter, so both are set out.

#### The half that survives: ODbL does not reach `pipeline/`, `server/` or `ios/`

ODbL 1.0 licenses rights *in a database*. Its copyleft (§4.4) attaches to
Derivative Databases; its notice duty (§4.3) attaches to Produced Works. Source
code that reads OSM and computes over it is neither. Nothing in ODbL obliges a
program that consumes a database to adopt the database's licence, and the
existing attribution brief reaches the same conclusion by the same route. **No
change: the application's own source may be licensed however the owner likes.**

#### The half that fails: `docs/route-census/census-pairs.csv`

What the file is, traced through the code rather than assumed:

- `pipeline/extract.py:166-167` writes `place_points` from OSM nodes tagged
  `place=city|town|village|hamlet|square`, keeping the node's own point geometry.
- `tools/route_census.py:179-181` reads `place_points.parquet` and takes the raw
  latitude and longitude arrays.
- `tools/route_census.py:208-211` writes them straight into the CSV:
  `src_lat=round(float(lat[i]), 6)` — six decimal places, roughly 11 cm, i.e.
  verbatim.

Measured on the committed file: **1,000 rows, 1,621 distinct place-node
coordinates**, bounding box `lat 41.026 … 47.355`, `lon −73.628 … −67.661` — the
Connecticut shoreline to northern Maine. And it is public right now:

```
curl https://raw.githubusercontent.com/Jamesk1281/Scenic/main/docs/route-census/census-pairs.csv
  →  200, 82,753 bytes, no credentials
```

Now the two tests that decide it, quoted from the sources rather than
paraphrased.

**Is the extraction Substantial?** ODbL defines "Substantial" circularly
("substantial in terms of quantity or quality or a combination of both"), so the
operative text is the OSM Foundation's **board-endorsed** community guideline
(endorsed 2014-06-06). It defines a "Feature" as "a Way … or an independent node
such as a Point Of Interest" — an OSM `place=town` node is one Feature — and
then sets the threshold by listing what is **not** Substantial:

> Less than 100 Features.
>
> More that 100 Features only if the extraction is non-systematic and clearly
> based on your own qualitative criteria […] The systematic extraction of all
> eating places within an area or at all castles within an area would be
> considered to be systematic.
>
> The features relating to an area of up to 1,000 inhabitants […]

The census extraction fails all three limbs, and not marginally: 1,621 Features
against a ceiling of 100; a deterministic seeded draw over the region's entire
place-point set, which is systematic in exactly the sense the guideline
describes; and a footprint of six states rather than one village. The guideline's
own summary of where it drew the line is "village map OK, town map not OK."

**Does that make the CSV a Derivative Database?** ODbL §4.4(b) answers directly,
and it is a for-the-avoidance-of-doubt clause, so there is little room to argue:

> For the avoidance of doubt, Extraction or Re-utilisation of the whole or a
> Substantial part of the Contents into a new database is a Derivative Database
> and must comply with Section 4.4.

Serving it from a public URL is Re-utilisation ("making available to the public
… by online or other forms of transmission") and is Publicly Used ("to Persons
other than You"). **So §4.4 share-alike and §4.2 notices are engaged today.**

#### Two other artifacts, and why they are easier

- **`docs/scenic_heatmap.png`** is rendered by `pipeline/render.py:108-109` from
  `scored_chunks.parquet` — OSM road geometry. That is a **Produced Work** ("a
  work (such as an image …) resulting from using the whole or a Substantial part
  of the Contents"). §4.5(b) is explicit that creating a Produced Work "does not
  create a Derivative Database", so **share-alike does not reach it** — but the
  §4.3 notice does, and this image is the first thing in `README.md:13`, with no
  attribution near it. The most visible artifact in the repository is an
  unattributed Produced Work. It is also the cheapest thing on this page to fix.
- **`docs/route-census/census-routes.csv`** holds measurements only — distances,
  minutes, scores — with no coordinates, names or OSM identifiers. It is output
  computed *from* the database rather than Contents extracted *out of* it, which
  makes it a Produced Work on the same reasoning. *This one is a judgement call
  and is flagged as such*: a table of query results is arguably itself a
  database. It does not change what needs doing, because the §4.3 notice that
  covers the heatmap covers it too.

#### What discharging this actually takes

Smaller than it sounds, and §4.6 is already satisfied by accident:

> **4.6** … You must also offer to recipients … a copy in a machine readable form
> of: a. The entire Derivative Database; or b. A file containing all of the
> alterations made to the Database **or the method of making the alterations to
> the Database (such as an algorithm)** …

`tools/route_census.py` **is** that algorithm, it is committed, and it is
deterministic from a seed recorded in `census-summary.json`. So §4.6 is met.

What is missing is §4.2 (the notice and the licence URI, carried with the
Derivative Database — §4.2(d) expressly allows putting it "in a location (such as
a relevant directory) where users would be likely to look for it") and §4.4 (the
Derivative Database offered under ODbL or a compatible licence). Three ways out,
in ascending order of effort:

1. **A `docs/route-census/README.md`** carrying the §4.3 example notice and
   stating that `census-pairs.csv` is offered under ODbL 1.0. Ten minutes, keeps
   the data, and is the resolution the OSMF itself recommends: *"just attribute
   us and contribute back any data improvements … then everyone is happy!"*
2. **Drop the four coordinate columns** from the committed CSV. `pair_id` and the
   seed already make the sample reproducible from `route_census.py`, so the
   analysis survives intact and the extraction disappears. This is the option
   that makes the question go away rather than answering it.
3. **Leave it and accept the position.** Recorded for completeness, not
   recommended — not because anyone is likely to complain, but because the
   project depends on this licence upstream and there is no version of "we rely
   on ODbL but do not comply with it" that reads well in a public repository.

**Calibration, honestly.** This is not litigation exposure. The OSMF's posture is
attribution-first, the project is precisely the kind of non-commercial local work
the guideline says it wants to encourage, and the remedy is a notice file. But
the threshold test is objective, the numbers are not close to it, and the fix is
ten minutes. **Option 1 or 2 — the owner's pick.** Neither was done here, because
offering an artifact under a licence is itself a licensing decision.

**This is the item most worth a professional's eye** if any of them are, because
it is the one where the repository is out of step with a licence it actually
depends on.

### 1c — Do the fitted constants carry anything?

**No.** Short answer, as the brief predicted.

The constants are `WEIGHTS` (9 scalars) plus `RAW_BASE` and `STRETCH` in
`pipeline/score.py:52-66`, and `SPEED_KMH` (13), `SPEED_FACTOR` (1),
`SURFACE_SPEED_FACTOR` (1) and `CONTROL_SECONDS` (3) in `pipeline/graph.py:64`
and `pipeline/router.py:140-199`. Twenty-nine scalars in total.

Two independent reasons nothing carries:

- **They are not copyrightable subject matter.** *Feist Publications v. Rural
  Telephone Service* (499 U.S. 340) holds that facts are not copyrightable
  however much effort went into collecting them. A number fitted to observed data
  — "signals cost 11.5 seconds", "p50 lands near 4.5" — is a measurement, and
  §102(b) separately excludes the method it parameterises.
- **They are not a database, so ODbL cannot attach.** Twenty-nine scalars are not
  "a collection of material arranged in a systematic or methodical way and
  individually accessible", and they contain no OSM Contents. They are a summary
  *about* the data, not an extraction *from* it — the same reasoning that makes
  `census-summary.json`'s aggregate counts unproblematic.

The expressive work here is the commentary around the constants, which is
ordinary copyrightable prose owned by its author and governed by whatever licence
1a settles on.

### 1d — Does a licence choice constrain a later App Store release?

**Only if the licence is copyleft. MIT, Apache-2.0 and all-rights-reserved are
all clear.** This is answerable from the agreement's own text rather than by
analogy, because the current ADPLA defines the term:

> "**FOSS**" (Free and Open Source Software) means any software that is subject
> to terms that, as a condition of use, copying, modification or redistribution,
> require such software and/or derivative works thereof to be disclosed or
> distributed in source code form, to be licensed for the purpose of making
> derivative works, or to be redistributed free of charge, including without
> limitation software distributed under the GNU General Public License or GNU
> Lesser/Library GPL.

MIT and Apache-2.0 impose none of those three conditions and fall outside the
definition. GPL and LGPL are named inside it.

Two operative clauses follow from it. **§3.3.4 "Content Rights and Licensing" →
A. "Content and Materials" → (v)**:

> If Your Application or Your Corresponding Product includes any FOSS, You agree
> to comply with all applicable FOSS licensing terms. You also agree not to use
> any FOSS in the development of Your Application … in such a way that would
> cause the non-FOSS portions of the Apple Software to be subject to any FOSS
> licensing terms or obligations.

and a representation and warranty in **§5.1, "Certificate Requirements"** — which
is where it sits because the conflict it guards against is with code signing:

> You further represent and warrant to Apple that the licensing terms governing
> Your Application … will be consistent with and not conflict with the digital
> signing or content protection aspects of the Program or any of the terms,
> conditions or requirements of the Program or this Agreement.

That second clause is the mechanism behind the well-known conflict between
GPL-licensed applications and App Store distribution: a licence forbidding
"further restrictions" collides with the restrictions the Program imposes.
**Publishing the source permissively and selling a binary are compatible, and
many shipped apps do exactly that.** The constraint is real but narrow, and it
does not touch either option recommended in 1a.

---

## Gap 2 — the four Apple clauses, checked against the current agreement

### What was retrieved, and its provenance

The full current Apple Developer Program License Agreement was retrieved
successfully as HTML on 2026-09-19 from
<https://developer.apple.com/support/terms/apple-developer-program-license-agreement/>
— 838 KB of source, 637 KB of text. **It did not have to be treated as
unretrievable.** All four clauses were read from it directly.

**One caveat, in Apple's own words, and it is not a small one.** That page says:

> Please note that the version of the Apple Developer Program License Agreement
> you accept in your developer account is binding and the most up to date. This
> version is provided for your convenience.
>
> * Developer Program License Agreement, including its Schedule 1 last updated
>   **August 18, 2026**.

So this is Apple's published convenience copy dated 2026-08-18, not the executed
copy in the account. **Before relying on any of this commercially, check the
copy in App Store Connect.** That is the one honest gap in this section, and it
cannot be closed from this machine — the binding copy is behind authentication
that belongs to the account holder.

### Clause by clause

| Clause | Audit's citation | Current agreement | Verdict |
| --- | --- | --- | --- |
| Obscuring Apple's notices | Att. 6 §2.1 | Att. 6 §2.1 | **Confirmed; text broadened** |
| No benchmarking against Apple | Att. 6 §2.3 | Att. 6 §2.3 | **Confirmed unchanged** |
| No storing Map Data | Att. 6 §2.5 | Att. 6 §2.5 | **Confirmed, but materially rewritten** |
| Route-guidance EULA notice | §3.3.15 | **§3.3.3(F)(iii)** | **String confirmed; citation stale** |
| "Map Data" includes coordinates | Definitions | Definitions | **Confirmed verbatim** |
| Fleet/asset limits scoped to MapKit JS | Att. 6 §1.2 | Att. 6 §1.2 | **Confirmed** |

#### §3.3.15 → §3.3.3(F)(iii) — the citation moved, the string did not

**`3.3.15` does not appear anywhere in the current agreement.** §3.3 has been
restructured into eleven thematic subsections (§3.3.1 "APIs and Functionality"
through §3.3.11 "AI & Machine Learning Technologies"), each with lettered parts.
The route-guidance obligation now sits at **§3.3.3 "Data and Privacy" → F.
"Location and Maps; User Consents" → (iii)**, and reads:

> (iii) If You choose to provide Your own location-based service, data and/or
> information in conjunction with the Apple maps provided through the Apple Maps
> Service (e.g., overlaying a map or route You have created on top of an Apple
> map), You are solely responsible for ensuring that Your service, data and/or
> information correctly aligns with any Apple maps used. For Applications that
> use location-based APIs for real-time navigation (including, but not limited
> to, turn-by-turn route guidance and other routing that is enabled through the
> use of a sensor), You must have an end user license agreement that includes the
> following notice: YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT
> YOUR SOLE RISK. LOCATION DATA MAY NOT BE ACCURATE.

**The notice string is byte-for-byte identical to the audit's.** Compared
programmatically after whitespace normalisation: identical, pure ASCII, no smart
quotes, no changed capitalisation. This was the brief's central worry — that the
app would ship the wrong string and silently fail to discharge the clause — and
it can be retired. **Use the audit's string as written.**

Two smaller notes. The current text reads "an end user license agreement"
(unhyphenated) where the audit wrote "an end-user license agreement"; that is in
the lead-in, not the notice, so nothing turns on it. And the audit's separate
observation still holds: the same clause's opening sentence names overlaying
"a map or route You have created on top of an Apple map" as a contemplated use,
so the architecture is expressly permitted.

#### Att. 6 §2.1 — confirmed, and slightly broader than quoted

> 2.1 Neither You nor Your Application, website or web application may remove,
> obscure or alter Apple's **or its partners' or** licensors' copyright notices,
> trademarks, logos, or any other proprietary rights or legal notices, documents
> or hyperlinks that may appear in or be provided through the Apple Maps Service.

"or its partners'" has been added since the 2021 text. It widens the clause and
leaves the audit's conclusion — that a clipped Apple ornament is within "obscure"
— untouched.

#### Att. 6 §2.3 — confirmed unchanged

The two sentences the audit relies on are present word for word:

> Further, You may not use or compare the data provided by the Apple Maps Service
> for the purpose of improving or creating another mapping service. You agree not
> to create or attempt to create a substitute or similar service through use of
> or access to the Apple Maps Service.

**The standing rule stands: never evaluate this project's routes or ETAs against
Apple's.** Benchmark against recorded drives and a clock.

#### Att. 6 §2.5 — confirmed, and the 2021 quote is now misleading

This is the one clause where quoting the old text would have led somewhere wrong.
Current, with the differences marked:

> 2.5 Unless otherwise expressly permitted **in writing by Apple**, Map Data may
> not be cached, pre-fetched, or stored by You or Your Application, website, or
> web application other than on a temporary and limited basis solely as necessary
> **(a) for Your use of the Apple Maps Service as permitted herein or in the
> MapKit or MapKit JS Documentation, and/or (b)** to improve the performance of
> the Apple Maps Service with Your Application, website, or web application,
> **after which, in all cases, You must delete any such Map Data.**

Three changes, pulling in different directions:

1. The permission gate narrowed from "in the MapKit Documentation" to "**in
   writing by Apple**".
2. A new limb (a) was added, which on its face permits storage for ordinary
   permitted use and is *broader* than the 2021 text.
3. **A new affirmative duty: "after which, in all cases, You must delete any such
   Map Data."** There was no deletion obligation in the quoted 2021 text.

Change 3 is the one that matters. The audit rated this item "technically engaged,
low enforcement risk" — fair on the old text. On the current text the clause
contains an express, unqualified duty to delete, and a permanent NDJSON file in
`Documents/traces/` that `UIFileSharingEnabled` exposes for copying off does not
satisfy it. The audit's recommended fix — record the router's *snapped* node
instead of the geocoder's output, which is a graph node from this project's own
OSM-derived data and not Map Data at all — discharges the clause completely and
improves the instrument. **That recommendation gets stronger, not weaker.**

The definition it depends on is also confirmed verbatim:

> "Map Data" means any content, data or information provided through the Apple
> Maps Service including, but not limited to, imagery, terrain data, **latitude
> and longitude coordinates**, transit data, points of interest and traffic data.

#### One thing the audit did not have: Attachment 6 §4

The audit covers §§2.1–2.6 and the route-guidance clause. It does not mention
Attachment 6 §4, "Apple's Right to Review Your MapKit and/or MapKit JS
Implementation", which ends:

> Apple reserves the right to revoke Your access to MapKit … at any time in its
> sole discretion, even if Your use of MapKit … meets the Documentation and
> Program Requirements and terms of this Attachment. By way of example only,
> Apple may do so if Your MapKit … implementation places an excessive and undue
> burden on the Apple Maps Service, **obscures or removes the Apple Maps logo or
> embedded links when displaying a map**, or uses the Apple Maps Service with
> corresponding offensive or illegal map content.

**Obscuring the logo is named, by example, as grounds for revoking MapKit
access.** That raises the consequence of the audit's item 2 from "a term is
breached" to "the remedy Apple reserves is withdrawal of the API the app is built
on". It does not change the fix, which is still the `MKMapView` +
`layoutMargins` refactor the audit describes — but it changes how easy the item
is to defer.

---

## Gap 3 — what the public repository exposes

Checked independently rather than by restating the brief. Two of its numbers came
out differently and two findings are new.

### Credentials: clean, and checked across all published history

A repository's tip is not its exposure — anything reachable from any pushed ref
is public. So the scan covered **all 133 commits across all 16 branches published
to `origin`**, not just `main`:

- **Key and token patterns** (`AKIA…`/`ASIA…`, `ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`,
  `github_pat_`, `sk-…`, `xox[baprs]-…`, `AIza…`, `-----BEGIN … PRIVATE KEY`):
  **zero matches.**
- **Assignment-shaped secrets** (`api_key=`, `secret=`, `password=`, `token=`,
  `private_key=` followed by a literal of 8+ characters), excluding prose and
  false friends like `UserDefaults` and `tokenize`: **zero matches.**
- **`server/start-windows.bat`** runs `cloudflared.exe tunnel run scenic` — a
  *named* tunnel, whose credentials live in a local file on the host. No tunnel
  token, no connector secret in the repo. **Correct by construction.**

**The brief's "no API keys, tokens or passwords" holds, independently
reproduced, and it holds across history rather than only at `main`.**

### Two things worth fixing

**1. `docs/route-census/census-summary.json:2` publishes an absolute local
filesystem path.** It is the `processed_dir` recorded by `route_census.py:279`,
and it exposes the machine's account name and the full parent directory chain of
the project. It is served anonymously:

```
curl https://raw.githubusercontent.com/Jamesk1281/Scenic/main/docs/route-census/census-summary.json
  →  200, "processed_dir": "/Users/<account>/…/Scenic/data/processed-ne"
```

Not a credential, and not dangerous. But it is the author's machine layout on
display for no benefit, and one of the directory names in that chain is not one
you would choose to publish. **Fix: have `route_census.py` record
`processed_dir` relative to the repository root, or record only its basename.**
That is a one-line change in a file this document is not permitted to touch;
it is recorded here for whoever does.

**2. All 131 commits on `main` carry a personal email address in the author
field**, rather than a GitHub `users.noreply.github.com` address. On a public
repository that address is readable by anyone, permanently, through the commit
metadata and the API — and it is not an address that reads like a project
contact. The address is deliberately not reproduced here.

This is conventional and it is not a security problem. It is, however, a thing
most people would change if asked. **Fix, for future commits:** enable "Keep my
email address private" in GitHub account settings and set the `noreply` address
as `user.email` for this repository. Rewriting the 131 existing commits is
possible but rewrites every SHA in the published history, which is a real cost
for a modest benefit — **recommended against unless the owner feels strongly.**

### Two counts corrected

- **`api.jameskouvlis.com` appears 7 times across 5 files, not 8.** Exact
  occurrences, `git grep -o`: `ios/project.yml:63`, `server/DEPLOY.md:9,367`,
  `server/start-windows.bat:23`, `docs/hosting-options-brief.md:18,191`,
  `docs/consumer-polish-brief.md:33`. The brief's extra hit in `DEPLOY.md` around
  `:366` is an `api/…` path, not the hostname.

  **On whether it should be there at all:** it is the owner's own domain, it
  resolves through Cloudflare rather than to a home IP, and `DEPLOY.md`
  deliberately proposes a public demo on it. Publishing the hostname is a
  decision already made, and the tunnel is what makes it safe — the origin's
  address is never exposed. The one thing worth knowing is that it advertises a
  home-hosted service as a target; the mitigation is Cloudflare Access on
  anything that is not `/api/health` or `/api/route`, not redaction of a name
  that is already in DNS.

- **`DEVELOPMENT_TEAM: 28ZU5P5GC3` appears 4 times across 2 files**, not 2 —
  `ios/project.yml:73` and `spike/voice-audio/project.yml:31,75,88`. The brief's
  substantive point is right and is confirmed: **a Team ID is not a credential.**
  It is embedded in every signed app's receipt, it is visible to anyone who
  inspects a distributed binary, and it cannot be used to sign anything without
  the private key and certificate that live in the developer's Keychain.
  **No action.**

### Two things that are already right

- **No drive traces anywhere in published history.** `*.ndjson` and `traces/`
  return zero files across all 16 published branches, not just `main`, and
  `.gitignore` explains why. Confirmed independently.
- **The spike measurement files contain no location data.** Their keys are
  audio-session and lifecycle fields (`category`, `route`, `outVolume`,
  `appState`, `spokenSeconds`, `acc`, `speed`); a full key scan of both files
  returns no latitude, longitude or coordinate field. `acc` and `speed` are
  sensor accuracy and speed, not position. **Clean.**

  One small note for completeness: `spike/voice-audio/measurements/instruction-durations.tsv`
  lists real street names from a test route through Cambridge, MA. They are OSM
  street names in a public city and reveal nothing about a person, but they do
  record roughly where the app was tested. Recorded, not flagged.

---

## The audit's ten items, carried forward

What this pass did to each — not a re-derivation. Every "confirmed" below means
checked against a primary source today.

| # | Audit item | This pass |
| --- | --- | --- |
| 1 | "Scenic" is taken and descriptive | **Not re-examined** — settled in `branding-brainstorm.md`. Noted only that Apache-2.0 §6 would reserve the eventual name and MIT would not (1a). |
| 2 | Apple attribution obscured (Att. 6 §2.1) | **Confirmed, and escalated.** Clause text broadened; Att. 6 §4 names this conduct as grounds to revoke MapKit access. |
| 3 | No EULA carrying the route-guidance notice | **Confirmed. Citation corrected** to §3.3.3(F)(iii); the required string is byte-identical and safe to use as quoted. |
| 4 | No privacy policy URL | **Unchanged, not re-examined.** Still a hard App Store gate. |
| 5 | Traces persist Apple-derived coordinates (§2.5) | **Confirmed, and harder than recorded.** Current §2.5 adds an express duty to delete. The audit's snapped-coordinate fix now discharges more than it did. |
| 6 | No `PrivacyInfo.xcprivacy` | **Unchanged, not re-examined.** Live on `main` since the voice merge. |
| 7 | Geofabrik credit line | **Unchanged, not re-examined.** |
| 8 | Generated app icon may not be ownable | **Unchanged, not re-examined.** Interacts with 1a: Apache-2.0 §6 reserves names and marks, not the icon's underlying authorship. |
| 9 | Third-party code licences clean | **Confirmed.** `ios/project.yml` declares no package manager; the `dependencies:` line at `:97` is the test target depending on the app target, not a package. |
| 10 | OSM / WorldCover / Terrain Tiles attribution | **Confirmed for the shipped app** (on the unmerged attribution branch). **Newly open for the repository**: the heatmap and census CSVs carry no notice — see 1b. |

**Plus one item the audit's scope excluded, now open:** the repository itself is
published with no licence (Gap 1), and one directory in it carries live ODbL
obligations (1b).

---

## What needs a professional, and what could not be retrieved

Used sparingly, and meant literally.

**Needs a lawyer:**

- **The ODbL position on `census-pairs.csv` (1b)**, if the owner wants to keep
  the file as it stands rather than take option 1 or 2. The guideline is
  board-endorsed but it is a guideline, not the licence, and the substantiality
  question in a specific case is exactly what the OSMF says to take to counsel:
  *"If you intended use is obviously larger than our guideline, well, you'll have
  to consult your lawyer."* If either cheap option is taken, the question does
  not arise.
- **The name (audit item 1)**, unchanged from the audit's own assessment.
- **Any privacy policy that will actually be published**, because it has to be
  accurate about GDPR and CCPA/CPRA treatment of precise location, and being
  wrong in a published policy is worse than not having one.

**Could not be retrieved from this machine:**

- **The binding copy of the ADPLA in the developer account.** Apple's public page
  states plainly that the account copy governs and the published one is "for your
  convenience". Everything in Gap 2 is verified against the convenience copy
  dated **2026-08-18** and should be re-checked against the account copy before
  anything commercial depends on it. This is the only unretrieved item, it is
  named rather than papered over, and nothing here silently substitutes the 2021
  text for the current one.

**Answerable without either, and answered above:** the licence options and their
consequences (1a), the fitted constants (1c), the App Store compatibility
question (1d), all four clause verifications (Gap 2), and the whole of Gap 3.

---

## Sources

Every claim above traces to one of these, all retrieved 2026-09-19 unless noted.

- Apple Developer Program License Agreement, published copy last updated
  2026-08-18 —
  <https://developer.apple.com/support/terms/apple-developer-program-license-agreement/>
- ODbL 1.0 full text —
  <https://opendatacommons.org/licenses/odbl/1-0/>
- OSM Foundation, *Licence/Community Guidelines/Substantial — Guideline*,
  endorsed by the OSMF board 2014-06-06 —
  <https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines/Substantial_-_Guideline>
- Apache License 2.0 — <https://www.apache.org/licenses/LICENSE-2.0.txt>
- GitHub Terms of Service §D.5, "License Grant to Other Users" —
  <https://docs.github.com/en/site-policy/github-terms/github-terms-of-service>
- *Feist Publications, Inc. v. Rural Telephone Service Co.*, 499 U.S. 340 (1991)
- The repository itself, at `378aaee`, and the GitHub REST API for its public
  metadata.
