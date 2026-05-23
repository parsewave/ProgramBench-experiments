# scripts/

A self-contained way to run ProgramBench tasks through the same agent harness
the paper baselines use ([mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent),
per paper §3 and `docs/README.md`), without needing a metered Anthropic API key.

Behaviorally equivalent to upstream `mini-extra programbench` (bash-only tool
surface, no extra plumbing) — the only delta is the model class, which is
swapped out for `AnthropicOAuthModel` so a Claude Code subscription token can
be used in place of a metered API key.

## Files

- **`setup.sh`** — one-shot bootstrap. Installs `uv` if missing, clones
  `mini-swe-agent` next to this repo, and `uv pip install -e`'s it into
  programbench's venv.
- **`programbench_mini.py`** — runner. Pulls
  `programbench/<inst>:task_cleanroom`, spawns a `--network none` container via
  mini-swe-agent's `DockerEnvironment`, runs `DefaultAgent` with the **paper §A.2.3
  system prompt verbatim**, and tarballs `/work/` into `submission.tar.gz` for
  `programbench eval`. Supports `--instance-id` (single) or `--config` (batch).
- **`anthropic_oauth.py`** — drop-in mini-swe-agent model class. Authenticates
  with `$CLAUDE_CODE_OAUTH_TOKEN` (the `accessToken` from
  `~/.claude/.credentials.json`), sends `Authorization: Bearer <token>` plus the
  `anthropic-beta: oauth-2025-04-20` header, prepends the
  `"You are Claude Code..."` identity system block (without it the OAuth-only
  beta returns 429), and bridges Anthropic ↔ OpenAI message shapes so the rest
  of mini-swe-agent's tool-call loop works unchanged.

## Setup (once)

```bash
bash scripts/setup.sh
```

This is idempotent — re-runs only fix what's missing. It clones
`mini-swe-agent` into a sibling directory of this repo.

## Run a single instance

Requires you to be logged in via Claude Code locally so
`~/.claude/.credentials.json` contains a fresh access token. If a run fails with
`401 from Anthropic`, refresh by running `claude -p ok` once locally and
re-export the token.

```bash
export CLAUDE_CODE_OAUTH_TOKEN=$(python -c \
  'import json,os; print(json.load(open(os.path.expanduser("~/.claude/.credentials.json")))["claudeAiOauth"]["accessToken"])')

uv run python scripts/programbench_mini.py \
  --instance-id abishekvashok__cmatrix.5c082c6 \
  --output-dir output/my-run \
  --model claude-opus-4-7
```

## Score the result

The benchmark already ships an evaluator — there's no separate eval script
here. Run it directly:

```bash
uv run programbench eval output/my-run --branch-workers 4 --docker-cpus 4
```

Outputs land in `output/my-run/<instance_id>/<instance_id>.eval.json`.
`programbench info output/my-run` prints the score table.

## Notes & gotchas

- **OAuth tokens expire ~every 8 hours.** If a run errors mid-way with
  `AnthropicOAuthAuthError: 401`, run `claude -p ok` once locally to refresh,
  then re-export `$CLAUDE_CODE_OAUTH_TOKEN`.
- **OAuth has no per-call cost.** Cost tracking is forcibly set to
  `ignore_errors`; trajectories record `cost: 0.0` regardless of usage.
- **The agent operates inside `:task_cleanroom`**, which has the runtime
  shared libraries the gold binary links against (e.g., `libncursesw.so.6`)
  but NOT the dev/header packages. The eval container uses the `:task` tag
  which DOES have the dev packages installed, so submissions that rely on
  system libraries work at scoring time even without internet access. Bear
  this in mind when reasoning about why your submission did or didn't compile.
