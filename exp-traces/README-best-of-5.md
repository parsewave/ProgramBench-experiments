# cc-opus-easy10 best-of-5 results

Five independent rollouts of Claude Opus 4.7 (via Claude Code) on the easy-10 ProgramBench subset, using a clean-room reverse-engineering doctrine. Each rollout is one full pass over all 10 tasks. The best-of-5 column takes the per-task max across all five rollouts.

## Best-of-5 scoreboard

Scores are **filtered pass rates** computed via the official `programbench info` CLI (mirrored locally by pb_score.py). Per-task winner is bolded; ties are bolded in every tied cell. ✅ marks a full programbench-confirmed solve (`passed == total` after filtering active branches / ignored tests — programbench's own verdict, not a 100-rounded display).

| Task | v2-C-1 | v2-C-2 | v2-C-3 | v2-C-4 | v2-C-5 | **best-of-5** |
|---|---|---|---|---|---|---|
| abishekvashok__cmatrix | **100 ✅** | 100 | 100 | **100 ✅** | 99 | **100 ✅** |
| wfxr__csview | **99** | **99** | **99** | **99** | **99** | **99** |
| wfxr__code-minimap | 93 | 97 | 95 | **98** | 96 | **98** |
| blake3-team__blake3 | **99** | **99** | 98 | 98 | 97 | **99** |
| sitkevij__hex | 98 | 99 | **100** | 98 | 98 | **100** |
| sstadick__hck | 96 | **98** | 97 | 92 | 95 | **98** |
| mgdm__htmlq | 98 | **99** | 98 | 84 | 98 | **99** |
| pier-cli__pier | 89 | 95 | 94 | 95 | **96** | **96** |
| sheepla__pingu | **97** | **97** | **97** | **97** | 94 | **97** |
| chmln__sd | 93 | 97 | **98** | 97 | 95 | **98** |
| **avg** | 96 | 98 | 98 | 96 | 97 | **98** |
| **solves** | **1** | 0 | 0 | **1** | 0 | **1** |

Two genuine ✅ solves landed across 50 task-rollouts, both on cmatrix (v2-C-1 and v2-C-4 — both 508/508). The other cmatrix 100s and hex v2-C-3 100 are 1–2 tests short of a full solve and display as 100 due to rounding only — `programbench info` explicitly notes: *"A score of 100 does not mean solved (due to rounding). Only ✅ indicates a solved task."*

## Per-rollout contribution to best-of-5

| Rollout | Tasks where it's the (sole or tied) best |
|---|---|
| v2-C-1 | **cmatrix ✅** + tied csview, blake3, pingu |
| v2-C-2 | hck, htmlq + tied csview, blake3, pingu |
| v2-C-3 | hex (sole 100), sd + tied csview, pingu |
| v2-C-4 | **cmatrix ✅**, code-minimap + tied csview, pingu |
| v2-C-5 | pier (sole 96) |

## Layout

Each `cc-opus-easy10-v2-C-N/` dir contains:
- 10 task subdirectories (`<instance_id>/trace1/`), each with:
  - `trajectory.jsonl` — full Claude Code stream-json trace
  - `trajectory.json` — converted form (lossy adapter)
  - `submission.tar.gz` — the agent's `/work/work/` packaged for `programbench eval`
  - `source-backup.tar.gz` — full `/work/` snapshot
  - `meta.json`, `run.log`, `doctor.log` — harness metadata
  - `<instance_id>.eval.json` — per-task eval result
- `README.md` — per-rollout setup notes + score table

## How the runs differ

| Rollout | Concurrency | Doctrine | Notes |
|---|---|---|---|
| v2-C-1 | 5 | clean-room RE (vanilla) | Cobbled from 3 source dirs; cmatrix solve |
| v2-C-2 | 5 | clean-room RE (vanilla) | Peer run; 0 compile_failed |
| v2-C-3 | 5 | clean-room RE + an experimental variant for hex/blake3/hck | Experimental variant later retired (see v2-C-4/5) |
| v2-C-4 | 5 | clean-room RE (vanilla) | Concurrent with v2-C-5 (10 total CC sessions); cmatrix solve |
| v2-C-5 | 5 | clean-room RE (vanilla) | Concurrent with v2-C-4 (10 total CC sessions) |

## Methodology takeaways

- **Solves are rare** (~8% expected probability per attempt given typical 99.5% per-test pass rate × ~500 tests). We landed 2 across 50 task-rollouts, both on cmatrix (v2-C-1 and v2-C-4) — consistent with expectation.
- **Best-of-N across separate sessions** (rather than `traces_per_task` within a single batch) was used to diversify rollout-level design-choice variance and avoid per-session rate-limit contention.
- **Higher in-session concurrency surfaces transient API errors** (~10% of traces in the 10-concurrent v2-C-4/v2-C-5 setup vs 0% in v2-C-1's 5-concurrent setup). Failed traces were detected and re-queued.
- **Pass rate, not raw test counts**: scored-test denominators can vary per submission because programbench's pytest parametrize generates more cases when the submission exposes more surface area (e.g., extra CLI options → extra test cases). Always compare via filtered pass rate.
- **blake3 trace was clean-image rerun**: the original v2-C-N blake3 traces ran on the contaminated `:task` image variant (v2-C-1 was an outright cp-cheat on the leaked reference binary; v2-C-2..5 were genuine but on the wrong image). All 5 were replaced with traces from a clean-image rerun on `:task_cleanroom` (2026-05-27); pre-cleanroom evidence preserved at `s3://parsewave-program-bench/traces/blake3-v2-C-1-contamination-20260528/` and `…/blake3-v2-C-2thru5-wrong-image-20260528/`.
