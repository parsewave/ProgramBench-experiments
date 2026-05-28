# cc-opus-easy10-v2-C-1

**Model:** claude-opus-4-7 (via Claude Code)
**Date:** 2026-05-20 / 2026-05-21 (blake3 trace replaced 2026-05-28 — see note below)
**Doctrine:** clean-room RE (vanilla)
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Config:** `opus-experiment/CLAUDE.md`

## Purpose

The original v2-C baseline rollout, pieced together from three contributing earlier sessions (some tasks needed a second attempt due to the stdin-blocking pattern):

- **cmatrix** → single-task retry session (produced the ✅ cmatrix solve)
- **csview / hex / sd / pingu / code-minimap** → original easy-10 session (5 tasks)
- **pier / hck / htmlq** → earlier easy-10 session that hadn't been superseded for these three
- **blake3** → trace1 of the clean-image blake3 rerun (5 traces, 2026-05-27 — see contamination note below)

## Scores (filtered, per `programbench info`)

| Task | Score | Notes |
|---|---|---|
| abishekvashok__cmatrix.5c082c6 | 100 (508/508) | ✅ solved |
| wfxr__csview.8ac4de0 | 99 | |
| blake3-team__blake3.15e83a5 | 99 (641/647) | clean-image rerun |
| sitkevij__hex.61ae69b | 98 | |
| mgdm__htmlq.6e31bc8 | 98 | |
| sheepla__pingu.926d475 | 97 | |
| sstadick__hck.b66c751 | 96 | |
| chmln__sd.87d1ba5 | 93 | |
| wfxr__code-minimap.0ddeea5 | 93 | |
| pier-cli__pier.5e1bde9 | 89 | |
| **average** | **96** | |
| **solves** | **1** | cmatrix |

**Solves:** 1 — cmatrix (508/508). The companion best-of-5 run v2-C-4 also achieved a cmatrix solve.

## blake3 contamination note (2026-05-28)

The original blake3 trace in this directory was retired. It scored 647/647 = 100 ✅ on the upstream-contaminated `:task` image variant by `cp`-ing the leaked reference binary at `/workspace/b3sum/target/release/b3sum` into the submission. Root cause was twofold: (1) ProgramBench's `:task` image for blake3 retained the `target/release/` build tree (other 9 easy tasks are identical between `:task` and `:task_cleanroom`), and (2) the cc-opus harness `run_task.sh` hardcoded `:task` instead of the documented `:task_cleanroom`. Caught during a post-hoc audit; we reran blake3 5× on `:task_cleanroom` and replaced the trace with the cleanroom rerun's trace1 (99, 641/647). Pre-cleanroom artifacts + full post-mortem are preserved at `s3://parsewave-program-bench/traces/blake3-v2-C-1-contamination-20260528/`.
