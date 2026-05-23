<h1 align="center"><img src="docs/assets/fox_hero_200.png" alt="ProgramBench logo" width="120"><br/>ProgramBench-experiments</h1>

<p align="center"><em>Parsewave experiments on the ProgramBench reverse-engineering benchmark.</em></p>

<p align="center">
A fork of <a href="https://github.com/facebookresearch/programbench">facebookresearch/programbench</a> with our agent harness, prompts, and rollout traces overlaid. Upstream README continues below.
</p>

## Experiment results

The headline experiment in this repo is a **best-of-5 evaluation of Claude Opus 4.7 on the easy-10 ProgramBench subset**, using the framework-C reverse-engineering doctrine.

- **Scoreboard + methodology:** [`example-outputs/README-best-of-5.md`](example-outputs/README-best-of-5.md)
- **Per-rollout traces** (10 tasks × 5 rollouts = 50 task-traces): under [`example-outputs/cc-opus-easy10-v2-C-{1..5}/`](example-outputs/), each task dir has the full `trajectory.jsonl`, `submission.tar.gz`, and `eval.json`.
- **Harness:** [`opus-experiment/harness/`](opus-experiment/harness/) (container-CC architecture, single-task and batch launchers, eval monitor).
- **Doctrines:** [`opus-experiment/claude-configs/`](opus-experiment/claude-configs/) (`framework-A/B/C/D`; `framework-C` is the one used for the headline rollouts).
- **Standalone runner (alternative path):** [`scripts/programbench_mini.py`](scripts/) wires mini-swe-agent's `DockerEnvironment` to Anthropic OAuth so you can run a single instance without the launchpad infra.

Best-of-5 headline: average pass rate **99**, with 2 confirmed full solves (`cmatrix`, `blake3` — both from the v2-C-1 rollout). See the scoreboard linked above for the per-task breakdown.

> Internal infra references (proxy IPs, hostnames, internal repo paths) in the trace data and harness have been redacted to placeholders like `<REDACTED_PROXY_IP_1>`. The architecture remains readable; the actual endpoints are not exposed.

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
