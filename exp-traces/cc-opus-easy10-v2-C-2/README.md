# cc-opus-cv3-v2-C-2-20260522

**Model:** claude-opus-4-7 (via Claude Code)
**Date:** 2026-05-22 (blake3 trace replaced 2026-05-28 — see note below)
**Doctrine:** clean-room RE (early variant, restored from git `faee535`)
**Git commit:** doctrine = git show faee535:opus-experiment/CLAUDE.md
**Tasks:** 10 (full easy-10)
**Per-task budget:** 14400 s (4 h), --effort max
**Parallel:** 5
**Config:** opus-experiment/CLAUDE.md (early-variant snapshot)

## Purpose

A/B against v3-1 (twin doctrine) using the original v2-C doctrine that produced the historic v2-C-1 baseline (cmatrix 100 ✅).

## Scores (filtered, per `programbench info`)

| Task | Score (passed/total) | v2-C-1 baseline | Δ tests |
|---|---:|---:|---:|
| abishekvashok__cmatrix.5c082c6 | 100 (507/508) | 508/508 ✅ | −1 |
| wfxr__csview.8ac4de0 | 99 (333/335) | 332/335 | +1 |
| sitkevij__hex.61ae69b | 99 (811/823) | 809/823 | +2 |
| mgdm__htmlq.6e31bc8 | 99 (1437/1455) | 1424/1455† | +13 |
| blake3-team__blake3.15e83a5 | 99 (641/647) | 641/647 | 0 |
| sstadick__hck.b66c751 | 98 (834/855) | 820/855† | +14 |
| sheepla__pingu.926d475 | 97 (373/383) | 373/383 | 0 |
| chmln__sd.87d1ba5 | 97 (787/810) | 757/810 | +30 |
| wfxr__code-minimap.0ddeea5 | 97 (309/319) | 292/313 | +17* |
| pier-cli__pier.5e1bde9 | 95 (659/692) | 615/692† | +44 |
| **Aggregate** | **6691/6837 (97.9%)** | **6586/6821 (96.6%)** | **+105 tests, +1.3pp** |
| **Mean per-task pct** | **98.0** | **96.2** | **+1.8pp** |

† pier/hck/htmlq v2-C-1 baselines come from an earlier easy-10 session that covered those three tasks.
\* code-minimap denominators differ (319 vs 313) because v2-C-2's submission exposed more CLI surface → more parametrized test cases.

**Solves:** 0 (vs v2-C-1's 1 solve on cmatrix — missed by 1 test here).

## Read

Beats v2-C-1 in aggregate test-pass rate (+1.3pp) but missed the cmatrix solve by 1 test. Single-trace stochastic variance: the agent's probe-tree walked a different subset of canonical surfaces this conversation than it did when v2-C-1 was run. Doctrine identical to v2-C-1; result is broader-but-shallower test coverage.

## blake3 contamination note (2026-05-28)

The blake3 trace originally in this directory ran on the contaminated `:task` image variant. A trajectory audit confirmed it did NOT exploit the leaked reference binary — the agent wrote a genuine reimplementation with a distinct executable md5 from the reference — but it was still on the wrong image. We replaced the trace with trace2 of the clean-image blake3 rerun (score 99/641/647 filtered). The pre-cleanroom honest-but-wrong-image trace is preserved at `s3://parsewave-program-bench/traces/blake3-v2-C-2thru5-wrong-image-20260528/v2-C-2/`.

## Co-located v3-1 run

Same box, same harness; only doctrine differs. See `cc-opus-cv3-v3-1-twin-20260522/` for the twin-doctrine sibling run.
