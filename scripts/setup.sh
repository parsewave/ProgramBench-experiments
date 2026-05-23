#!/usr/bin/env bash
# One-shot bootstrap: install uv if missing, clone mini-swe-agent next to this
# repo, and install it editable into programbench's venv. Idempotent — re-runs
# only fix what's missing.

set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
    echo "[setup] installing uv..." >&2
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "[setup] uv sync (programbench deps)..." >&2
uv sync --quiet

MINI_DIR="$(cd .. && pwd)/mini-swe-agent"
if [ ! -d "$MINI_DIR/.git" ]; then
    echo "[setup] cloning mini-swe-agent into $MINI_DIR ..." >&2
    git clone --depth 1 https://github.com/SWE-agent/mini-swe-agent.git "$MINI_DIR"
else
    echo "[setup] mini-swe-agent already cloned at $MINI_DIR" >&2
fi

echo "[setup] uv pip install -e $MINI_DIR ..." >&2
uv pip install --quiet -e "$MINI_DIR"

uv run python -c "from minisweagent.agents.default import DefaultAgent; from minisweagent.environments.docker import DockerEnvironment; print('[setup] mini-swe-agent ready (version', __import__('minisweagent').__version__, ')')"

cat <<'DONE'

[setup] complete. Run a single task:

  CLAUDE_CODE_OAUTH_TOKEN=$(python -c 'import json,os; print(json.load(open(os.path.expanduser("~/.claude/.credentials.json")))["claudeAiOauth"]["accessToken"])') \
    uv run python scripts/programbench_mini.py \
      --instance-id abishekvashok__cmatrix.5c082c6 \
      --output-dir output/my-run \
      --model claude-opus-4-7

Score it:

  uv run programbench eval output/my-run

DONE
