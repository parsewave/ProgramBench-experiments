# cc-opus-easy10 best-of-5 results

Five independent rollouts of Claude Opus 4.7 (via Claude Code / launchpad) on the easy-10 ProgramBench subset, using the framework-C reverse-engineering doctrine. Each rollout is one full pass over all 10 tasks. The best-of-5 column takes the per-task max across all five rollouts — this is the headline result.

## Best-of-5 scoreboard

Scores are **filtered pass rates** computed via `programbench info` / the pb_score.py helper. Per-task winner is bolded; ties are bolded in every tied cell. ✅ marks a full programbench-confirmed solve (all scored tests pass).

| Task | v2-C-1 | v2-C-2 | v2-C-3 | v2-C-4 | v2-C-5 | **best-of-5** |
|---|---|---|---|---|---|---|
| abishekvashok__cmatrix | **100 ✅** | **100** | **100** | **100** | 99 | **100 ✅** |
| wfxr__csview | **99** | **99** | **99** | **99** | **99** | **99** |
| wfxr__code-minimap | 93 | **99** | 95 | 98 | 96 | **99** |
| blake3-team__blake3 | **100 ✅** | 98 | 97 | 97 | 99 | **100 ✅** |
| sitkevij__hex | 98 | 99 | **100** | 98 | 98 | **100** |
| sstadick__hck | 96 | **98** | 97 | 92 | 95 | **98** |
| mgdm__htmlq | 98 | **99** | 98 | 84 | 98 | **99** |
| pier-cli__pier | 89 | 95 | 94 | 95 | **96** | **96** |
| sheepla__pingu | **97** | **97** | **97** | **97** | 94 | **97** |
| chmln__sd | 93 | 97 | **98** | 97 | 95 | **98** |
| **avg** | 96 | 98 | 98 | 96 | 97 | **99** |
| **solves** | **2** | 0 | 0 | 0 | 0 | **2** |

## Per-rollout contribution to best-of-5

| Rollout | Tasks where it's the (sole or tied) best |
|---|---|
| v2-C-1 | **cmatrix ✅, blake3 ✅** (only source of full solves) + tied csview, pingu |
| v2-C-2 | code-minimap, hck, htmlq + tied cmatrix, csview, pingu |
| v2-C-3 | hex (sole 100), sd + tied cmatrix, csview, pingu |
| v2-C-4 | nothing exclusive; tied on cmatrix, csview, pingu |
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

| Rollout | Box | Token | Concurrency | Doctrine | Notes |
|---|---|---|---|---|---|
| v2-C-1 | Hetzner | single | 5 | framework-C original | Cobbled from 3 source dirs; produced both solves |
| v2-C-2 | Hetzner (different box) | single | 5 | framework-C original | Peer run; 0 compile_failed |
| v2-C-3 | pw | single | 5 | framework-C + framework-C-tmt for hex/blake3/hck | tmt variant later retired (see v2-C-4/5) |
| v2-C-4 | pw | primary | 5 | framework-C original | Concurrent with v2-C-5 (10 total CC sessions) |
| v2-C-5 | pw | fallback | 5 | framework-C original | Concurrent with v2-C-4 (10 total CC sessions) |

## Methodology takeaways

- **Solves are rare** (~8% expected probability per attempt given typical 99.5% per-test pass rate × ~500 tests). v2-C-1's 2 solves on cmatrix + blake3 were the only ones we got across 50 task-rollouts.
- **Best-of-N at the box level** (rather than `traces_per_task` in run_batch.sh) was used to spread rollouts across different physical boxes with different launchpad tokens. This both diversifies design-choice variance AND avoids per-token rate-limit contention.
- **Higher concurrency on a single box surfaces transient API errors** (~10% of traces in the 10-concurrent v2-C-4/v2-C-5 setup vs 0% in v2-C-1's 5-concurrent setup). A watchdog process catches and re-queues these.
- **Pass rate, not raw test counts**: scored-test denominators can vary per submission because programbench's pytest parametrize generates more cases when the submission exposes more surface area (e.g., extra CLI options → extra test cases). Always compare via pass rate.
