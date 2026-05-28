# cc-opus-easy10-v2-C-3

**Model:** claude-opus-4-7 (via Claude Code)
**Date:** 2026-05-22 (blake3 trace replaced 2026-05-28 — see note below)
**Doctrine:** clean-room RE (vanilla) for 7/10 tasks; an experimental variant for hex / blake3 / hck (rerun targets)
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Config:** `opus-experiment/CLAUDE.md` (an experimental variant was used for the three rerun targets — that variant has since been retired due to a separate regression on other tasks; see v2-C-4/v2-C-5 README for context)

## Per-task source attribution

Each task's trace was selected as the highest-scoring submission across three contributing on-disk runs:

| Task | Source | Score |
|---|---|---|
| abishekvashok__cmatrix.5c082c6 | main run | 100 |
| wfxr__csview.8ac4de0 | main run | 99 |
| wfxr__code-minimap.0ddeea5 | main run | 95 |
| blake3-team__blake3.15e83a5 | clean-image rerun (trace3) | 98 |
| sitkevij__hex.61ae69b | tmt-hexblake3 rerun | 100 |
| sstadick__hck.b66c751 | tmt-hck rerun | 97 |
| mgdm__htmlq.6e31bc8 | main run | 98 |
| pier-cli__pier.5e1bde9 | main run | 94 |
| sheepla__pingu.926d475 | main run | 97 |
| chmln__sd.87d1ba5 | main run | 98 |

Both reruns ran on the same date as the main session with the experimental variant. The blake3 replacement comes from trace3 of the clean-image blake3 rerun (2026-05-27).

## Scores (filtered, per `programbench info`)

| Task | Score |
|---|---|
| abishekvashok__cmatrix.5c082c6 | 100 |
| sitkevij__hex.61ae69b | 100 |
| wfxr__csview.8ac4de0 | 99 |
| chmln__sd.87d1ba5 | 98 |
| mgdm__htmlq.6e31bc8 | 98 |
| blake3-team__blake3.15e83a5 | 98 |
| sheepla__pingu.926d475 | 97 |
| sstadick__hck.b66c751 | 97 |
| wfxr__code-minimap.0ddeea5 | 95 |
| pier-cli__pier.5e1bde9 | 94 |
| **average** | **98** |
| **solves** | **0** |

No full ✅ solves; cmatrix and hex both at 100 are rounded from 506/508 and 821/823 respectively.

## blake3 contamination note (2026-05-28)

The blake3 trace originally in this directory ran on the contaminated `:task` image variant (see v2-C-1 README for full root cause). A trajectory audit confirmed it did NOT exploit the leaked reference binary, but it was still on the wrong image. Replaced with trace3 of the clean-image blake3 rerun (98, 632/647 filtered). Pre-cleanroom artifact preserved at `s3://parsewave-program-bench/traces/blake3-v2-C-2thru5-wrong-image-20260528/v2-C-3/`.
