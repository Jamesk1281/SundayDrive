# Pre-submission review: verdict

**Status: reviewed `6f26edf`. Verdict: PROVISIONAL (baselines done; findings in progress).**

Answer to `docs/pre-submission-review-brief.md` (committed alongside). Every
`file:line` below is at `6f26edf8cc00e8dedebd836a03a6798c34af7b19`, read with
`git show 6f26edf:<file>`. `<main>` is the main checkout.

---

## 0. Baselines

Measured 2026-09-30, 00:40–00:55 EDT, from a worktree at `6f26edf` with a clean
`git status`.

| | |
|---|---|
| SHA reviewed | `6f26edf8cc00e8dedebd836a03a6798c34af7b19` ("Merge the brand UI alignment"). `main` was still at it when this section was written |
| Backend suite | **388 passed, 0 failed, 0 skipped**, in 426 s, exit 0: `SUNDAYDRIVE_DATA=<main>/data/processed-ne <main>/.venv/bin/python -m pytest -q tests`. It took longer than the brief's 264 s because another session's `pytest tests -q -x` and my own server's graph load were running at the same time. The count matches the brief |
| iOS suite | **273 executed, 273 passed, 0 failed, 0 skipped**, `** TEST SUCCEEDED **`, on a simulator created for this review (iPhone 17 Pro, iOS 26.4), with `TEST_RUNNER_SUNDAYDRIVE_API=http://127.0.0.1:5391` |
| How I know `LiveDriveTests` reached my server | All 7 report `passed` (1.4–4.8 s each), and none report `skipped`. Nothing was listening on 5057 (`lsof -iTCP:5057` was empty), so a missed override would have shown up as 7 skips. `VoiceCatalogueTests` finished (8 cases passed) and did not hang |
| Local server | `PORT=5391 SUNDAYDRIVE_HOST=127.0.0.1 SUNDAYDRIVE_DATA=<main>/data/processed-ne … server/serve.py`: `794,685 nodes (801,719 routing slots)` |
| Live API | `GET /api/health`: HTTP 200 in 0.12 s, `{"nodes":794685,"routing_slots":801719,"status":"ok"}`. It serves the same graph as the local build. I sent it only that request and the two Pages requests. Nothing tonight probed it |
| RDAP | `jameskouvlis.com` expires **2026-10-28T18:52:52Z**, last changed 2026-08-12, **not renewed**. This is a known status item (brief §2), not a finding |
| Pages | `/SundayDrive/` and `/SundayDrive/privacy/` both returned 200 |
| What else was running | At least eight other Claude Code sessions, one running its own `pytest` over the whole suite, a booted simulator (`e2e-overnight`) belonging to another session, and an unrelated Python app. All timings below are therefore quoted as ratios or as order-of-magnitude figures |

## 1. Conceptual

Not started.

## 2. Market

Not started.

## 3. Code

Not started.

## 4. App Review

Not started.

## 5. Attacked and held

Not started.

## 6. Prior conclusions revisited

Not started.

## 7. Undetermined

Not started.

## 8. Verdict (provisional)

**PROVISIONAL.** No section is finished, so there is no verdict yet. If this
line is still here in the morning, the session ran out before any section
finished and nothing below it should be read as a result.

## Reproducing this

Not started.
