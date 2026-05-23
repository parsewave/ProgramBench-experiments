# cc-opus-easy10-v2-C-3

**Model:** claude-opus-4-7 (via claude-code, launchpad/OAuth proxy)
**Date:** 2026-05-22
**Box:** Hetzner ccx (pw box, <REDACTED_BOX_IP>)
**Doctrine:** framework-C (original) for 7/10 tasks; framework-C-tmt for hex / blake3 / hck (rerun targets)
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Generation script:** `opus-experiment/harness/run_batch.sh`
**Config:** `opus-experiment/claude-configs/framework-C/CLAUDE.md` (and `framework-C-tmt` for the three rerun targets — note framework-C-tmt has since been retired due to a separate regression on other tasks; see v2-C-4/v2-C-5 README for context)

## Per-task source attribution

Each task's trace was selected as the highest-scoring submission across three contributing on-disk runs:

| Task | Source | Score |
|---|---|---|
| abishekvashok__cmatrix.5c082c6 | main run | 100 |
| wfxr__csview.8ac4de0 | main run | 99 |
| wfxr__code-minimap.0ddeea5 | main run | 95 |
| blake3-team__blake3.15e83a5 | tmt-hexblake3 rerun | 97 |
| sitkevij__hex.61ae69b | tmt-hexblake3 rerun | 100 |
| sstadick__hck.b66c751 | tmt-hck rerun | 97 |
| mgdm__htmlq.6e31bc8 | main run | 98 |
| pier-cli__pier.5e1bde9 | main run | 94 |
| sheepla__pingu.926d475 | main run | 97 |
| chmln__sd.87d1ba5 | main run | 98 |

The main run was `cc-opus-fwc-v3-3-easy10-20260522-110218`; reruns were `cc-opus-fwc-tmt-hexblake3-20260522-130232` and `cc-opus-fwc-tmt-hck-20260522-134856`.

## Scores

| Task | Score |
|---|---|
| abishekvashok__cmatrix.5c082c6 | 100 |
| sitkevij__hex.61ae69b | 100 |
| wfxr__csview.8ac4de0 | 99 |
| chmln__sd.87d1ba5 | 98 |
| mgdm__htmlq.6e31bc8 | 98 |
| sheepla__pingu.926d475 | 97 |
| sstadick__hck.b66c751 | 97 |
| blake3-team__blake3.15e83a5 | 97 |
| wfxr__code-minimap.0ddeea5 | 95 |
| pier-cli__pier.5e1bde9 | 94 |
| **average** | **98** |
| **solves** | **0** |

No full ✅ solves; cmatrix and hex both at 100 are rounded from 506/508 and 820/823 respectively.
