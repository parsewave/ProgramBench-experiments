#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv sync --quiet

MINI_DIR="$(cd .. && pwd)/mini-swe-agent"
if [ ! -d "$MINI_DIR/.git" ]; then
    git clone --depth 1 https://github.com/SWE-agent/mini-swe-agent.git "$MINI_DIR"
fi

uv pip install --quiet -e "$MINI_DIR"

uv run python -c "from minisweagent.agents.default import DefaultAgent; from minisweagent.environments.docker import DockerEnvironment; print('mini-swe-agent ready (version', __import__('minisweagent').__version__, ')')"
