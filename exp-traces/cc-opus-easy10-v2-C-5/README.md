# cc-opus-easy10-v2-C-5

**Model:** claude-opus-4-7 (via Claude Code)
**Date:** 2026-05-23 (blake3 trace replaced 2026-05-28 — see note below)
**Doctrine:** clean-room RE (vanilla)
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Config:** `opus-experiment/CLAUDE.md`

## Notes

Ran concurrently with v2-C-4 from a separate Claude Code session. Same prompt and concurrency as v2-C-4. The cmatrix task here came in at 99 (505/508) on a re-queued rerun after the initial trace hit an early-exit-error class (agent terminated abnormally mid-Discovery, no compile.sh written).

## Scores (filtered, per `programbench info`)

| Task | Score |
|---|---|
| wfxr__csview.8ac4de0 | 99 |
| abishekvashok__cmatrix.5c082c6 | 99 |
| sitkevij__hex.61ae69b | 98 |
| mgdm__htmlq.6e31bc8 | 98 |
| blake3-team__blake3.15e83a5 | 97 (628/647) |
| pier-cli__pier.5e1bde9 | 96 |
| wfxr__code-minimap.0ddeea5 | 96 |
| sstadick__hck.b66c751 | 95 |
| chmln__sd.87d1ba5 | 95 |
| sheepla__pingu.926d475 | 94 |
| **average** | **97** |
| **solves** | **0** |

## blake3 contamination note (2026-05-28)

The blake3 trace originally in this directory ran on the contaminated `:task` image variant. A trajectory audit confirmed it did NOT exploit the leaked reference binary, but it was still on the wrong image. Replaced with trace5 of the clean-image blake3 rerun (97, 628/647 filtered). Pre-cleanroom artifact preserved at `s3://parsewave-program-bench/traces/blake3-v2-C-2thru5-wrong-image-20260528/v2-C-5/`.
