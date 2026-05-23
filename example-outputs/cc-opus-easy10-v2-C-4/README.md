# cc-opus-easy10-v2-C-4

**Model:** claude-opus-4-7 (via claude-code, launchpad/OAuth proxy)
**Date:** 2026-05-23
**Box:** Hetzner ccx (pw box, <REDACTED_BOX_IP>)
**Doctrine:** framework-C (original / vanilla)
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Generation script:** `opus-experiment/harness/run_batch.sh`
**Config:** `opus-experiment/claude-configs/framework-C/CLAUDE.md`
**Token:** primary (`.claude-custom`)
**On-disk run name:** `cc-opus-fwc-easy10-v2-C-4-20260523-032117`

## Notes

Ran concurrently with v2-C-5 (which used the fallback token), giving 10 simultaneous CC sessions on the box (2 tokens × 5 parallel). This higher concurrency surfaced a class of transient API errors that occasionally caused `is_error=true` mid-trace; a watchdog process detected and re-queued such failures automatically (see `opus-experiment/harness/eval_monitor.sh` and the watchdog pattern logged in commit history).

One outlier: `mgdm__htmlq` scored 84 — significantly lower than the typical 98 across other runs. Root cause was an Anthropic Usage Policy refusal mid-trace (the agent constructed HTML test inputs that tripped a safety classifier false-positive), which derailed implementation of the `--remove-nodes` feature. Not a load / harness / prompt issue; would likely succeed on rerun with different probe content.

## Scores

| Task | Score |
|---|---|
| abishekvashok__cmatrix.5c082c6 | 100 |
| wfxr__csview.8ac4de0 | 99 |
| sitkevij__hex.61ae69b | 98 |
| wfxr__code-minimap.0ddeea5 | 98 |
| blake3-team__blake3.15e83a5 | 97 |
| chmln__sd.87d1ba5 | 97 |
| sheepla__pingu.926d475 | 97 |
| pier-cli__pier.5e1bde9 | 95 |
| sstadick__hck.b66c751 | 92 |
| mgdm__htmlq.6e31bc8 | 84 |
| **average** | **96** |
| **solves** | **0** |
