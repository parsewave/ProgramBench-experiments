<h1 align="center"><img src="docs/assets/fox_hero_200.png" alt="ProgramBench logo" width="120"><br/>ProgramBench-experiments</h1>

<p align="center"><em>Parsewave experiments on the ProgramBench reverse-engineering benchmark.</em></p>

<p align="center">
A fork of <a href="https://github.com/facebookresearch/programbench">facebookresearch/programbench</a> with our agent doctrine and rollout traces overlaid. Upstream README continues below.
</p>

## Experiment results

The headline experiment in this repo is a **mean-of-5 evaluation of Claude Opus 4.7 (max effort) on the easy-10 ProgramBench subset**, using a clean-room reverse-engineering doctrine.

- **Scoreboard + methodology:** [`exp-traces/README-best-of-5.md`](exp-traces/README-best-of-5.md)
- **Per-rollout traces** (10 tasks × 5 rollouts = 50 task-traces): under [`exp-traces/cc-opus-easy10-v2-C-{1..5}/`](exp-traces/), each task dir has the full `trajectory.jsonl`, `submission.tar.gz`, and `eval.json`.
- **Doctrine:** [`opus-experiment/CLAUDE.md`](opus-experiment/CLAUDE.md) — the clean-room RE prompt used for all rollouts.
- **Charts:** [`exp-traces/figures/`](exp-traces/figures/) — per-task scores, leaderboard comparison, per-rollout variance.

**Headlines** (filtered pass rate per `programbench info`):
- Mean across 5 rollouts × 10 tasks: **96.9** (vs **95.8** for Claude Opus 4.7-xhigh on the same 10 under mini-swe-agent, single rollout)
- Beats the Opus 4.7-xhigh per-task mean on **8 of 10** tasks
- Per-rollout aggregate band: 95.8 – 98.0
- **2 confirmed full ✅ solves** across 50 task-rollouts, both on `cmatrix` (v2-C-1 and v2-C-4, both 508/508)
- Best-of-5 aggregate: 98

## Reproducing a single rollout

Two paths. Both produce a `submission.tar.gz` you can score with `uv run programbench eval output/`.

### A. Via Claude Code (matches our setup)

Spawns a Claude Code session inside the task's `:task_cleanroom` container with `opus-experiment/CLAUDE.md` mounted as project instructions, runs non-interactively to completion, and tars the result.

Prerequisites: docker; Node.js 20+; `npm install -g @anthropic-ai/claude-code`; an active local Claude Code session (run `claude` once on the host).

```bash
uv pip install programbench

bash scripts/run_claude_code.sh abishekvashok__cmatrix.5c082c6 output/my-run

uv run programbench eval output/my-run --branch-workers 4 --docker-cpus 4
uv run programbench info output/my-run
```

The script bind-mounts the host's `node` binary, the host's `@anthropic-ai/claude-code` package, and `~/.claude` (your session credentials) into the task container, then runs `claude -p` with `--permission-mode bypassPermissions` and `--output-format stream-json`. The network sandbox is intentionally loose for the reproducer; the doctrine prompt prohibits source-finding and the agent is expected to comply.

### B. Via mini-SWE-agent (uses your Claude Code session token, no Claude Code CLI required)

A single-instance / batch runner that bridges [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) to the access token from `~/.claude/.credentials.json`. See [`scripts/README.md`](scripts/README.md).

```bash
bash scripts/setup.sh

export CLAUDE_CODE_OAUTH_TOKEN=$(python -c \
  'import json,os; print(json.load(open(os.path.expanduser("~/.claude/.credentials.json")))["claudeAiOauth"]["accessToken"])')

uv run python scripts/programbench_mini.py \
  --instance-id abishekvashok__cmatrix.5c082c6 \
  --output-dir output/my-run \
  --model claude-opus-4-7

uv run programbench eval output/my-run
uv run programbench info output/my-run
```

`--doctrine` is on by default and appends `opus-experiment/CLAUDE.md` to the paper's anti-cheat system prompt; pass `--no-doctrine` for the plain paper baseline.

---

<p align="center"><em>Upstream README:</em></p>

<p align="center">
Given only a compiled binary and its documentation, AI agents must architect and implement a complete codebase that reproduces the original program's behavior.
</p>

## Links

- [Website](https://programbench.com)
- [Paper](https://arxiv.org/abs/2605.03546)
- [HuggingFace](https://huggingface.co/datasets/programbench/ProgramBench-Tests)
- [Leaderboard](https://programbench.com)
- [Usage Guide](docs/README.md)

## Quickstart

We recommend [uv](https://docs.astral.sh/uv/getting-started/installation/) for managing Python environments.

```bash
# Run without installing
uvx programbench --help

# Or install into a project
uv pip install programbench

# Or with pip
pip install programbench
```

For development:

```bash
git clone https://github.com/facebookresearch/programbench.git
cd programbench
uv sync  # installs editable + dev dependencies
```

> [!NOTE]
> For more details, please refer to the [Usage Guide](docs/README.md).

## Citation

If our work was useful for you, please cite it:

```bibtex
@misc{yang2026programbenchlanguagemodelsrebuild,
    title={ProgramBench: Can Language Models Rebuild Programs From Scratch?},
    author={John Yang and Kilian Lieret and Jeffrey Ma and Parth Thakkar and Dmitrii Pedchenko and Sten Sootla and Emily McMilin and Pengcheng Yin and Rui Hou and Gabriel Synnaeve and Diyi Yang and Ofir Press},
    year={2026},
    eprint={2605.03546},
    archivePrefix={arXiv},
    primaryClass={cs.SE},
    url={https://arxiv.org/abs/2605.03546},
}
```

## License

ProgramBench is licensed under the terms of the license found in [LICENSE](LICENSE).
