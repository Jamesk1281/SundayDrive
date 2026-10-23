# Dispatch briefs: where they went

**Status:** every brief written before 2026-10-05 was deleted on that date.
`a2ddddc` is the last commit that has them all. From now on a brief is
deleted in the same merge that brings its work back. Rule 5 in
[README.md](README.md#adding-a-document) says how.

A brief is the hand-off to a dispatched session: what to do, the traps, and
what done looks like. Once the work merges, that job is finished. The answer
lives in code, in a findings or verdict document, or in a record kept from the
brief. What a brief *asked* is still worth reading when you're checking a
result against its question, so every one stays in history:

```sh
git show a2ddddc:docs/<name>-brief.md          # or docs/archive/<name>-brief.md
```

Where a brief held a measurement, a decision or a result that nothing else
recorded, that part was kept as `<topic>.md` with its section headings intact.
Traps, done-lists and build steps were not kept. A source comment that cites
a brief by name or trap number means the copy at `a2ddddc`.

| brief (`git show a2ddddc:<path>`) | its answer lives in |
| --- | --- |
| `docs/astar-fastest-arm-brief.md` | [astar-fastest-arm.md](astar-fastest-arm.md) |
| `docs/brand-ui-alignment-brief.md` | [brand-ui-alignment.md](brand-ui-alignment.md) |
| `docs/byway-relations-brief.md` | [byway-relations.md](byway-relations.md) |
| `docs/component-rebuild-cache-brief.md` | [component-rebuild-cache-findings.md](component-rebuild-cache-findings.md) |
| `docs/consumer-polish-brief.md` | [consumer-polish-defects.md](consumer-polish-defects.md) — four still open |
| `docs/coordinates-out-of-the-url-brief.md` | [coordinates-out-of-the-url.md](coordinates-out-of-the-url.md) |
| `docs/dial-headline-gain-brief.md` | [pre-submission-review-verdict.md](pre-submission-review-verdict.md) C-3, and `RouteComparison` |
| `docs/driving-app-features-brief.md` | [driving-app-features-cost.md](driving-app-features-cost.md) |
| `docs/hosting-independent-review-brief.md` | [hosting-independent-review.md](hosting-independent-review.md) |
| `docs/hosting-options-brief.md` | [hosting-options-findings.md](hosting-options-findings.md) |
| `docs/hosting-refresh-brief.md` | [hosting-status-2026-09.md](hosting-status-2026-09.md) |
| `docs/interface-design-brief.md` | [interface-design.md](interface-design.md) |
| `docs/licensing-and-attribution-brief.md` | [licensing-and-attribution.md](licensing-and-attribution.md), [data-sources.md](data-sources.md) |
| `docs/licensing-open-questions-brief.md` | [licensing-open-questions.md](licensing-open-questions.md) |
| `docs/location-text-and-contact-brief.md` | [location-text-and-contact.md](location-text-and-contact.md) |
| `docs/loop-matching-fix-brief.md` | [loop-matching-fix.md](loop-matching-fix.md) |
| `docs/never-joined-drive-brief.md` | [never-joined-drive.md](never-joined-drive.md) |
| `docs/new-england-only-brief.md` | [new-england-only.md](new-england-only.md) |
| `docs/odbl-repository-compliance-brief.md` | [licensing-open-questions.md](licensing-open-questions.md) §1b, `NOTICE` |
| `docs/overnight-e2e-drives-brief.md` | [overnight-e2e-findings.md](overnight-e2e-findings.md) |
| `docs/pre-submission-fixes-brief.md` | [pre-submission-review-verdict.md](pre-submission-review-verdict.md), merged as `f9f1937` |
| `docs/pre-submission-review-brief.md` | [pre-submission-review-verdict.md](pre-submission-review-verdict.md) |
| `docs/privacy-and-submission-brief.md` | [app-store-submission.md](app-store-submission.md) |
| `docs/privacy-policy-page-brief.md` | [privacy-policy.md](privacy-policy.md), `site/privacy/`, `.github/workflows/pages.yml` |
| `docs/release-plan-brief.md` | [release-plan.md](release-plan.md) |
| `docs/rename-to-victory-lap-brief.md` | Superseded by the Sunday Drive rename: [sunday-drive-rename-audit.md](sunday-drive-rename-audit.md) |
| `docs/scenery-grading-review-brief.md` | [scenery-grading-verdict.md](scenery-grading-verdict.md) |
| `docs/scenic-name-viability-brief.md` | [scenic-name-viability-findings.md](scenic-name-viability-findings.md) |
| `docs/seasonal-closures-brief.md` | [seasonal-closures.md](seasonal-closures.md) |
| `docs/sunday-drive-rename-audit-brief.md` | [sunday-drive-rename-audit.md](sunday-drive-rename-audit.md) |
| `docs/support-page-brief.md` | `site/index.html`, `tests/test_support_page.py` |
| `docs/trademark-knockout-brief.md` | [trademark-knockout-findings.md](trademark-knockout-findings.md) |
| `docs/unpaved-and-urban-brief.md` | [unpaved-and-urban-verdict.md](unpaved-and-urban-verdict.md) |
| `docs/victory-lap-naming-brief.md` | [victory-lap-naming.md](victory-lap-naming.md), itself superseded by [sunday-drive-naming.md](sunday-drive-naming.md) |
| `docs/voice-status-refresh-brief.md` | [voice-guidance-plan.md](voice-guidance-plan.md) |
| `docs/archive/beautiful-miles-and-the-slider-brief.md` | `ios/Sources/RoutePanel.swift:24-51` — the sweep table and all three traps |
| `docs/archive/documentation-structure-brief.md` | [documentation-structure-proposal.md](documentation-structure-proposal.md) |
| `docs/archive/geodata-peer-review-brief.md` | [geodata-peer-review-verdict.md](geodata-peer-review-verdict.md) |
| `docs/archive/landcover-implementation-brief.md` | [geodata-sources-findings.md](geodata-sources-findings.md), [geodata-peer-review-verdict.md](geodata-peer-review-verdict.md) |
| `docs/archive/new-england-terrain-brief.md` | `pipeline/elevation.py:50-58`, [new-england-terrain-findings.md](new-england-terrain-findings.md) |
| `docs/archive/voice-guidance-plan-brief.md` | `VoiceGuide.swift:12-20`, [voice-guidance-plan.md](voice-guidance-plan.md) §3 |

## Briefs deleted after 2026-10-05

These were committed with their answer and deleted later, so they are not
at `a2ddddc`. Read each at the commit named.

| brief | read it with | its answer lives in |
| --- | --- | --- |
| `docs/us-data-evaluation-brief.md` | `git show 88b1314:docs/us-data-evaluation-brief.md` | [us-map-data-findings.md](us-map-data-findings.md), with the scripts and results in `tools/us_map_data/` |
| `docs/loop-speed-brief.md` | `git show 7a7ea65:docs/loop-speed-brief.md` | [loop-speed.md](loop-speed.md), with the probes in `loop-speed-study/` |
| `docs/loop-lock-contention-brief.md` | `git show 8dbb728:docs/loop-lock-contention-brief.md` | [loop-lock-contention.md](loop-lock-contention.md), with the probe in `tools/loop_contention/` |
| `docs/mid-drive-recovery-brief.md` | `git show fe5cab0:docs/mid-drive-recovery-brief.md` | [mid-drive-recovery-plan.md](mid-drive-recovery-plan.md) |
| `docs/rating-prompt-brief.md` | `git show e5b2be8:docs/rating-prompt-brief.md` | [rating-prompt.md](rating-prompt.md) |
| `docs/route-options-brief.md` | `git show e26766a:docs/route-options-brief.md` | [route-options.md](route-options.md), with the study in `route-options-study/` |
| `docs/wrong-way-timeout-brief.md` | `git show 1be0691:docs/wrong-way-timeout-brief.md` | [mid-drive-recovery.md](mid-drive-recovery.md), "The wrong-way time-out"; D9 in [mid-drive-recovery-plan.md](mid-drive-recovery-plan.md) §8.3 |
| `docs/national-scenery-types-brief.md` | `git show d59c345:docs/national-scenery-types-brief.md` | [national-scenery-types-verdict.md](national-scenery-types-verdict.md), with the scripts and results in `tools/scenery_types/` |
| `docs/national-data-decisions-brief.md` | `git show 6f3a275:docs/national-data-decisions-brief.md` | [national-data-decisions.md](national-data-decisions.md) |
| `docs/seasonal-road-risk-brief.md` | `git show 8ed1082:docs/seasonal-road-risk-brief.md` | [seasonal-road-risk-verdict.md](seasonal-road-risk-verdict.md), with the scripts and results in `tools/seasonal_risk/` |
| `docs/scenery-additions-build-brief.md` | `git show 7e9d763:docs/scenery-additions-build-brief.md` | [national-scenery-additions.md](national-scenery-additions.md), with the checks in `tools/scenery_additions/` |
| `docs/seasonal-road-policy-brief.md` | `git show f8e4a83:docs/seasonal-road-policy-brief.md` | [seasonal-road-policy.md](seasonal-road-policy.md), with the re-measured study in `tools/seasonal_risk/built/` |
| `docs/safety-quick-fixes-brief.md` | `git show 93cf704:docs/safety-quick-fixes-brief.md` | [safety-quick-fixes.md](safety-quick-fixes.md) |
| `docs/national-marketing-brief.md` | `git show 426c2e5:docs/national-marketing-brief.md` | [marketing-plan.md](marketing-plan.md), rewritten for a national first launch |
| `docs/western-landcover-brief.md` | `git show 06ae07f:docs/western-landcover-brief.md` | [western-landcover-verdict.md](western-landcover-verdict.md), with the scripts and results in `tools/western_landcover/` (on `usa`) |
| `docs/national-launch-brief.md` | `git show cfeb688:docs/national-launch-brief.md` | four units, on `usa`: [national-build.md](national-build.md), [router-at-us-scale.md](router-at-us-scale.md), [app-goes-national.md](app-goes-national.md), [winter-closures-national.md](winter-closures-national.md) |
| `docs/review-fixes-brief.md` | `git show 042a470:docs/review-fixes-brief.md` | four units, on `usa`: [review-fixes-router.md](review-fixes-router.md), [review-fixes-data.md](review-fixes-data.md), [review-fixes-app.md](review-fixes-app.md), [review-fixes-deploy.md](review-fixes-deploy.md). The 2026-10-20 outside review it quotes stayed out of the repo by the owner's decision |
| `docs/national-copy-brief.md` | `git show 42e4808:docs/national-copy-brief.md` | on `usa`: [national-copy.md](national-copy.md). The 2026-10-23 outside review it quotes stayed out of the repo by the owner's decision |

## Briefs kept out of history

A brief that quoted the private drive traces (street names, clock times) is
never committed to `main`, so it does not exist in the public history at all.
Its answer document is self-contained.

| brief | its answer lives in |
| --- | --- |
| `docs/reroute-uturn-brief.md` | [reroute-uturn.md](reroute-uturn.md) |
| `docs/mid-drive-recovery-build-brief.md` | [mid-drive-recovery.md](mid-drive-recovery.md), designed in [mid-drive-recovery-plan.md](mid-drive-recovery-plan.md) |
| `docs/state-road-class-brief.md` | [state-road-class.md](state-road-class.md) |
| `docs/side-loops-brief.md` | [side-loops-verdict.md](side-loops-verdict.md) |
