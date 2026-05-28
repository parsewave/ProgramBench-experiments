# cc-opus-easy10-v2-C-4

**Model:** claude-opus-4-7 (via Claude Code)
**Date:** 2026-05-23 (blake3 trace replaced 2026-05-28 — see note below)
**Doctrine:** clean-room RE (vanilla)
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Config:** `opus-experiment/CLAUDE.md`

## Notes

Ran concurrently with v2-C-5 from a separate Claude Code session, giving 10 simultaneous sessions in flight. This higher concurrency surfaced a class of transient API errors that occasionally caused `is_error=true` mid-trace; failed traces were detected and re-queued.

One outlier: `mgdm__htmlq` scored 84 — significantly lower than the typical 98 across other runs. Root cause was an Anthropic Usage Policy refusal mid-trace (the agent constructed HTML test inputs that tripped a safety classifier false-positive), which derailed implementation of the `--remove-nodes` feature. Not a load / harness / prompt issue; would likely succeed on rerun with different probe content.

## Scores (filtered, per `programbench info`)

| Task | Score | Notes |
|---|---|---|
| abishekvashok__cmatrix.5c082c6 | 100 (508/508) | ✅ solved |
| wfxr__csview.8ac4de0 | 99 | |
| sitkevij__hex.61ae69b | 98 | |
| wfxr__code-minimap.0ddeea5 | 98 | |
| blake3-team__blake3.15e83a5 | 98 (632/647) | clean-image rerun |
| chmln__sd.87d1ba5 | 97 | |
| sheepla__pingu.926d475 | 97 | |
| pier-cli__pier.5e1bde9 | 95 | |
| sstadick__hck.b66c751 | 92 | |
| mgdm__htmlq.6e31bc8 | 84 | Usage-Policy refusal mid-trace |
| **average** | **96** | |
| **solves** | **1** | cmatrix |

**Solves:** 1 — cmatrix (508/508). Same task as v2-C-1's solve — this rollout independently arrived at the same fully-resolved implementation.

## blake3 contamination note (2026-05-28)

The blake3 trace originally in this directory ran on the contaminated `:task` image variant. A trajectory audit confirmed it did NOT exploit the leaked reference binary, but it was still on the wrong image. Replaced with trace4 of the clean-image blake3 rerun (98, 632/647 filtered). Pre-cleanroom artifact preserved at `s3://parsewave-program-bench/traces/blake3-v2-C-2thru5-wrong-image-20260528/v2-C-4/`.
