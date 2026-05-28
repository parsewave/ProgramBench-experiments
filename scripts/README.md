# scripts/

Two ways to reproduce a single ProgramBench rollout against our doctrine.

## Files

- `run_claude_code.sh` — spawns a non-interactive **Claude Code** session inside the task's `:task_cleanroom` container, with `opus-experiment/CLAUDE.md` mounted as project instructions. Tars `/work/` into `submission.tar.gz`. Matches our actual setup.
- `programbench_mini.py` — bridges [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) to the access token from your local Claude Code session. Single-instance or batch; runs `DefaultAgent` with the paper's anti-cheat system prompt + (by default) our doctrine appended.
- `anthropic_oauth.py` — mini-SWE-agent model class that reads the access token from `~/.claude/.credentials.json` and talks to the Anthropic API directly.
- `setup.sh` — one-shot bootstrap (installs `uv` if missing, clones `mini-swe-agent`, installs it into the venv).

## A. Claude Code path

```bash
uv pip install programbench
bash scripts/run_claude_code.sh abishekvashok__cmatrix.5c082c6 output/my-run

uv run programbench eval output/my-run --branch-workers 4 --docker-cpus 4
uv run programbench info output/my-run
```

Prerequisites:
- `docker`
- Node.js 20+ on the host (the script bind-mounts the host's `node` binary into the container)
- `npm install -g @anthropic-ai/claude-code` on the host (bind-mounted in too)
- An active Claude Code session locally (`~/.claude/` must exist; run `claude` once if it doesn't)

Override the model with `CLAUDE_MODEL=claude-opus-4-7 bash scripts/run_claude_code.sh ...`.

## B. mini-SWE-agent path

Faster to set up if you don't have Claude Code installed but do have a session token.

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

`--doctrine` is on by default. Pass `--no-doctrine` for the plain paper baseline. Use `--config <file.yaml>` + `--workers N` for batch.

## Notes

- Session tokens expire ~every 8 hours. If a run errors with `401`, run `claude -p ok` locally to refresh and re-export the env var (path B), or just re-run the script (path A — it reads the live credentials file).
- Both paths run the agent inside `:task_cleanroom` (no source / no dev headers). Eval uses `:task` (which has the dev packages installed) so submissions that link system libraries work at scoring time.
- The network sandbox in path A is loose for simplicity; the doctrine prompt prohibits source-finding and the agent is expected to comply.
