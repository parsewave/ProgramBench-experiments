# cc-opus-easy10-v2-C-5

**Model:** claude-opus-4-7 (via claude-code, launchpad/OAuth proxy)
**Date:** 2026-05-23
**Box:** Hetzner ccx (pw box, <REDACTED_BOX_IP>)
**Doctrine:** framework-C (original / vanilla)
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Generation script:** `opus-experiment/harness/run_batch.sh`
**Config:** `opus-experiment/claude-configs/framework-C/CLAUDE.md`
**Token:** fallback (`.claude-custom-fallback`)
**On-disk run name:** `cc-opus-fwc-easy10-v2-C-5-20260523-032120`

## Notes

Ran concurrently with v2-C-4 on the same box, sharing CPU/memory but using a different launchpad token. Same harness, prompt, and concurrency as v2-C-4. The cmatrix task here came in at 99 (505/508) on the watchdog-triggered rerun after the initial trace hit an early-exit-error class (agent terminated abnormally mid-Discovery, no compile.sh written).

## Scores

| Task | Score |
|---|---|
| blake3-team__blake3.15e83a5 | 99 |
| wfxr__csview.8ac4de0 | 99 |
| abishekvashok__cmatrix.5c082c6 | 99 |
| sitkevij__hex.61ae69b | 98 |
| mgdm__htmlq.6e31bc8 | 98 |
| pier-cli__pier.5e1bde9 | 96 |
| sstadick__hck.b66c751 | 95 |
| chmln__sd.87d1ba5 | 95 |
| wfxr__code-minimap.0ddeea5 | 96 |
| sheepla__pingu.926d475 | 94 |
| **average** | **97** |
| **solves** | **0** |
