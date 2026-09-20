# Discharge the ODbL obligations the public repository actually carries

> **Done 2026-09-19.** All four deliverables landed. One instruction below was
> then overtaken: "Do not add a `LICENSE` file" was correct while
> `licensing-open-questions.md` §1a was open, and §1a has since been decided —
> the repository is Apache-2.0, with `LICENSE` and `NOTICE` at the root.
> `docs/route-census/` is carved out of that licence and keeps the ODbL terms
> this brief asked for.

**Status: diagnosed 2026-09-19 against `main` at `4cf43b8`, nothing changed.**
No file was touched. **The owner has chosen the remedy** — see "The decision,
already made" — so this is implementation, not research.

The analysis is done and must not be re-derived:

```sh
docs/licensing-open-questions.md    # §1b has the whole mechanism, with file:line
docs/data-sources.md                # the established credit wording — reuse it
```

---

## The goal, as measured

`docs/route-census/census-pairs.csv` is a **Derivative Database** under ODbL 1.0
and is published without the notice or the licence offer that §4.2 and §4.4
require. Measured on the committed file today:

```
1,000 rows, 1,621 distinct place-node coordinates
bounding box  lat 41.026 … 47.355,  lon −73.628 … −67.661
columns: pair_id, band, src_lat, src_lon, dst_lat, dst_lon, gc_km, status,
         snap_src_m, snap_dst_m, in_sweep
```

Traced through the code rather than assumed:

- `pipeline/extract.py:166-167` writes `place_points` from OSM nodes tagged
  `place=city|town|village|hamlet|square`, keeping each node's own geometry.
- `tools/route_census.py:179-181` reads `place_points.parquet` and takes the raw
  latitude and longitude arrays.
- `tools/route_census.py:208-211` writes them verbatim at six decimal places:
  `src_lat=round(float(lat[i]), 6)`.

It is served anonymously right now:

```
curl https://raw.githubusercontent.com/Jamesk1281/Scenic/main/docs/route-census/census-pairs.csv
  →  200, 82,753 bytes, no credentials
```

**Why that is Substantial**, on the OSM Foundation's board-endorsed guideline
(endorsed 2014-06-06), which is the operative text because ODbL defines
"Substantial" circularly. The guideline sets the threshold by listing what is
*not* Substantial: "Less than 100 Features"; more than 100 only if "non-systematic
and clearly based on your own qualitative criteria"; "features relating to an area
of up to 1,000 inhabitants". The extraction fails all three and not marginally —
1,621 Features against a ceiling of 100, a deterministic seeded draw over the
region's entire place-point set, across six states. The guideline's own summary:
*"village map OK, town map not OK."*

**Why that makes it a Derivative Database**, ODbL §4.4(b), a
for-the-avoidance-of-doubt clause with little room to argue:

> For the avoidance of doubt, Extraction or Re-utilisation of the whole or a
> Substantial part of the Contents into a new database is a Derivative Database
> and must comply with Section 4.4.

**§4.6 is already satisfied by accident.** It allows offering "the method of
making the alterations to the Database (such as an algorithm)" in place of the
data. `tools/route_census.py` is that algorithm, it is committed, and it is
deterministic from the seed recorded in `census-summary.json`. What is missing is
only §4.2's notice and §4.4's licence offer.

## The decision, already made

The research set out two remedies and declined to choose between them, on the
grounds that offering an artifact under a licence is itself a licensing act.
**The owner picked option 1 on 2026-09-19: add the notice and keep the data.**

Do not implement option 2. Dropping `src_lat`/`src_lon`/`dst_lat`/`dst_lon` was
the rejected alternative — it was rejected because the coordinates are what make
the sample independently checkable, which is the character of this repository.
A session that "tidies" the CSV by removing them has reversed a decision the
owner made deliberately. See Trap 3.

## Three more things in the same blast radius

### 1. `docs/data-sources.md:7-8` asserts something that is no longer true

```
**This repository does not discharge the obligation** — it is private and
reaches nobody.
```

**The repository is public.** `GET https://api.github.com/repos/Jamesk1281/Scenic`
returns `private: False`, `visibility: public`, `license: None`. That sentence is
the premise that makes every unattributed artifact below defensible, and it has
been false since the repo was published. It is the load-bearing error in the
document, not a typo — correcting it is part of this task.

### 2. The most visible artifact in the repository is an unattributed Produced Work

`README.md:11` is the hero image:

```markdown
![heatmap](docs/scenic_heatmap.png)
```

`pipeline/render.py:108-109` renders it from `scored_chunks.parquet`, i.e. from
OSM road geometry. That makes it a **Produced Work** — ODbL's own definition
names "a work (such as an image …) resulting from using the whole or a
Substantial part of the Contents". §4.5(b) is explicit that creating a Produced
Work "does not create a Derivative Database", **so share-alike does not reach
it** — but the §4.3 notice does, and there is no attribution anywhere near it.

`docs/route-census/census-routes.csv` (5,192 rows, measurements only — no
coordinates, names or OSM ids) is a Produced Work on the same reasoning. The
research flags that one as a genuine judgement call, since a table of query
results is arguably itself a database; it does not change the work, because the
same §4.3 notice covers it either way.

### 3. `census-summary.json:2` publishes an absolute local path

```json
"processed_dir": "/Users/<account>/…/Scenic/data/processed-ne"
```

*(Redacted on committing this brief, to the same form
`licensing-open-questions.md:499` uses. The value quoted here in full was the
literal one, and reproducing it in a committed document would have undone the
fix below.)*

Written by `tools/route_census.py:279`, served anonymously, and it exposes the
account name and the full parent directory chain — including a folder name nobody
would choose to publish. Not a credential and not dangerous, on display for no
benefit. **Two halves, and doing only one leaves the file wrong** — see Trap 4.

---

## Traps

**1. Do not re-derive the ODbL analysis.** `docs/licensing-open-questions.md` §1b
is 120 lines with the guideline thresholds, the §4.4(b) and §4.6 quotes, and the
code trace. Re-reading ODbL from scratch to reach the same place is the single
most likely way to spend this session's budget and deliver nothing.

**2. Do not move `docs/route-census/` while you are here.** `docs/README.md:88-92`
records that the move to `tools/` is *deliberately blocked* on this task:

> it has not been moved because `licensing-open-questions.md` cites two live
> `raw.githubusercontent.com` URLs into this path and proposes adding a
> `route-census/README.md` here to discharge an ODbL obligation. Move it once
> that is settled

Adding the notice is what unblocks the move. Doing both in one change breaks two
cited URLs in a document on `main` before anyone has updated them. **Leave the
directory where it is** and, if you like, note in your commit that the move is
now unblocked.

**3. Do not drop the coordinate columns.** That was the option the owner
considered and rejected (see "The decision, already made"). It looks like the
tidier fix and it is the wrong one here.

**4. Fixing `route_census.py` does not fix the committed JSON, and regenerating
is not cheap.** `census-summary.json` is generated output. Correcting
`route_census.py:279` changes what *future* runs write; the published file still
carries the path until it is edited. And a full regeneration needs
`data/processed-ne` — 2.8 GB, gitignored, present only in the main checkout, not
in your worktree — and would rewrite every row of a 5,192-row census for a
one-field fix, changing measurements that `docs/route-distribution-study.md`
quotes. **Edit the one field in the committed file by hand, and fix the script so
it cannot recur.** Say in the commit that the rest of the file is unchanged.

**5. Use the wording already established, do not invent a variant.**
`docs/data-sources.md:13` and `ios/Sources/AboutView.swift` carry credit strings
reproduced from each licensor's own text, and `AboutView.swift`'s are asserted by
`ios/Tests/AttributionTests.swift`. The repository notice should match that
wording, not paraphrase it. ODbL §4.3 supplies an example notice; §4.2(d)
expressly allows placing it "in a location (such as a relevant directory) where
users would be likely to look for it", which is exactly what a
`route-census/README.md` is.

**6. Do not burn attribution into the PNG.** The heatmap fix is a line of
markdown next to the image, not a regenerated 2 MB raster with text rendered into
it. Regenerating it needs the gitignored build, and `README.md:13-15` documents
the refresh procedure precisely because that is awkward.

**7. Do not add a `LICENSE` file.** The repository licence is a separate open
decision belonging to the owner, with three costed options in
`docs/licensing-open-questions.md` §1a and no file committed on purpose. Offering
*one CSV* under ODbL because ODbL requires it is not the same act as licensing
the repository, and this task is only the first.

---

## Done looks like

1. **`docs/route-census/README.md`** — the §4.3 notice in the established
   wording, a statement that `census-pairs.csv` is offered under ODbL 1.0, and a
   pointer to `tools/route_census.py` plus the recorded seed as the §4.6 method.
   Short; this is a notice, not an essay.
2. **The heatmap attributed** at `README.md:11` — a caption or adjacent line
   crediting OpenStreetMap, reaching a reader who never opens a linked document.
3. **`docs/data-sources.md:7-8` corrected** — the repository is public, and what
   that changes about which artifacts carry obligations.
4. **The absolute path gone** from the committed `census-summary.json`, **and**
   `tools/route_census.py:279` changed so future runs record a repo-relative path
   or a basename.
5. **Backend tests green** — `.venv/bin/python -m pytest tests/` with
   `SCENIC_DATA` set; 348 collected at last count. Say the number. Nothing here
   should touch them, which is itself worth confirming.
6. **An honest-answer escape hatch.** If reading §1b convinces you the
   substantiality call is wrong, say so with the reasoning rather than
   implementing a notice you think is unnecessary — the research names this as
   the one item most worth a professional's eye. "The notice is cheap and correct
   either way" is also a fine conclusion; say which you reached.
