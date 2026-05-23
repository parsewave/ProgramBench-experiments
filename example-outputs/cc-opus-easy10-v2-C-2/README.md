# cc-opus-cv3-v2-C-2-20260522

**Model:** claude-opus-4-7 (via claude-code, launchpad/OAuth proxy)
**Date:** 2026-05-22
**Box:** Hetzner ccx53 (32-core, 128 GB) — same box as v3-1, destroyed after run
**Doctrine:** framework-C v2-C (pre-twin, restored from git `faee535`)
**Git commit:** cb77498 (harness); doctrine = git show faee535:opus-experiment/claude-configs/framework-C/CLAUDE.md
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Generation script:** opus-experiment/harness/run_batch.sh
**Config:** opus-experiment/claude-configs/framework-C-v2c/CLAUDE.md

## Purpose

A/B against v3-1 (twin doctrine) using the original v2-C doctrine that
produced the historic v2-C-1 baseline (cmatrix 100 ✅, blake3 100 ✅).

## Scores (filtered)

| Task | Score (passed/total) | v2-C-1 baseline | Δ tests |
|---|---:|---:|---:|
| abishekvashok__cmatrix.5c082c6 | 100 (507/508) | 508/508 ✅ | −1 |
| wfxr__csview.8ac4de0 | 99 (333/335) | 332/335 | +1 |
| sitkevij__hex.61ae69b | 99 (811/823) | 809/823 | +2 |
| mgdm__htmlq.6e31bc8 | 99 (1437/1455) | 1424/1455† | +13 |
| wfxr__code-minimap.0ddeea5 | 99 (309/313) | 292/313 | +17 |
| blake3-team__blake3.15e83a5 | 98 (632/647) | 647/647 ✅ | −15 |
| sstadick__hck.b66c751 | 98 (834/855) | 820/855† | +14 |
| sheepla__pingu.926d475 | 97 (373/383) | 373/383 | 0 |
| chmln__sd.87d1ba5 | 97 (787/810) | 757/810 | +30 |
| pier-cli__pier.5e1bde9 | 95 (659/692) | 615/692† | +44 |
| **Aggregate** | **6682/6821 (98.0%)** | **6577/6821 (96.4%)** | **+105 tests, +1.5pp** |
| **Mean per-task pct** | **98.1** | **96.4** | **+1.8pp** |

† pier/hck/htmlq v2-C-1 baselines from cc-opus-fwc-easy10-20260520-195157
(earlier framework-C run; canonical v2-easy10 only covered the other 6 tasks).

**Solves:** 0 (vs v2-C-1's 2 solves on cmatrix & blake3 — both lost by 1 and 15 tests).

## Read

Beats v2-C-1 in aggregate test-pass rate (+1.5pp, +105 tests across 10 tasks)
but loses both ✅ solves. Single-trace stochastic variance: the agent's
probe-tree walked a different subset of canonical surfaces this conversation
than it did when v2-C-1 was run. Doctrine identical to v2-C-1; result is
broader-but-shallower test coverage.

## Co-located v3-1 run

Same box, same harness; only doctrine differs. See
`cc-opus-cv3-v3-1-twin-20260522/` for the twin-doctrine sibling run.
