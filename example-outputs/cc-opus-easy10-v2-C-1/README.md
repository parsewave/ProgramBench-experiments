# cc-opus-easy10-v2-C-1

**Model:** claude-opus-4-7 (via claude-code, launchpad/OAuth proxy)
**Date:** 2026-05-20 / 2026-05-21
**Box:** Hetzner ccx (single CC-Opus eval box)
**Doctrine:** framework-C (original, pre-tmt)
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Generation script:** `opus-experiment/harness/run_batch.sh`
**Config:** `opus-experiment/claude-configs/framework-C/CLAUDE.md`

## Purpose

The original v2-C baseline run, pieced together from three contributing on-disk runs
(some tasks needed a second attempt due to the stdin-blocking pattern):

- **cmatrix** → from `cc-opus-fwc-v2b-cmatrix-20260521-075551` (single-task retry; produced the only ✅ cmatrix solve)
- **blake3 / csview / hex / sd / pingu / code-minimap** → from `cc-opus-fwc-v2-easy10-20260521-063532` (6 tasks; blake3 ✅ solved)
- **pier / hck / htmlq** → from `cc-opus-fwc-easy10-20260520-195157` (earlier framework-C run; the v2-easy10 retry batch had not covered these three)

## Scores (filtered, per pb_score.py / `programbench info`)

| Task | Score | Notes |
|---|---|---|
| abishekvashok__cmatrix.5c082c6 | 100 (508/508) | ✅ solved |
| blake3-team__blake3.15e83a5 | 100 (647/647) | ✅ solved |
| wfxr__csview.8ac4de0 | 99 | |
| sitkevij__hex.61ae69b | 98 | |
| mgdm__htmlq.6e31bc8 | 98 | |
| sheepla__pingu.926d475 | 97 | |
| sstadick__hck.b66c751 | 96 | |
| chmln__sd.87d1ba5 | 93 | |
| wfxr__code-minimap.0ddeea5 | 93 | |
| pier-cli__pier.5e1bde9 | 89 | |
| **average** | **96** | |
| **solves** | **2** | cmatrix, blake3 |

**Solves:** 2 — cmatrix (508/508) and blake3 (647/647). Both required the pre-tmt vanilla framework-C prompt to hit; later runs (v2-C-2 through v2-C-5) reproduced 100 on cmatrix but only at 507/508 max, and blake3 at 99 (644/647) max.
