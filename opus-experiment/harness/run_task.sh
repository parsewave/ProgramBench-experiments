#!/usr/bin/env bash
# ============================================================================
# run_task.sh
# ----------------------------------------------------------------------------
# Run a single ProgramBench task through Claude Code -- CONTAINER architecture.
#
# CC now runs INSIDE the task container, with an iptables egress allowlist
# that only permits traffic to the Parsewave proxy. This sandboxes the
# agent's Bash tool from the open internet (no `git clone` of the upstream
# repo, no `curl github.com`) while letting CC itself reach the Anthropic
# API via the proxy.
#
# Flow:
#   1. Resolve the task image (programbench/<task_with_1776>:task).
#   2. Verify the image is present locally.
#   3. `docker run --rm --cap-add=NET_ADMIN ...` mounting:
#        - claude-config/ -> /work/.claude  (ro)
#        - CLAUDE.md      -> /work/CLAUDE.md (ro)
#        - this harness   -> /opt/cc-harness (ro)
#        - launchpad bits -> /host/launchpad, /host/token, /host/launchpad-bin (ro)
#        - out dir        -> /out (rw)
#      and invoking bash /opt/cc-harness/container_entrypoint.sh.
#   4. The entrypoint handles iptables, user setup, claud invocation, tarring
#      the submission, and writing meta.json. All outputs land in /out which
#      maps to the host OUT_DIR.
#
# Usage:
#   ./run_task.sh <task_instance_id> [<trace_id>]
#
# Reads model + budget from environment OR these defaults:
#   CC_MODEL                    (default: claude-opus-4-7)
#   CC_TIMEOUT_SECONDS          (default: 5400)
#   RUN_NAME                    (default: cc-opus-<utc-stamp>)
#   OUT_DIR_BASE                (default: /tmp/cc-runs)
#   PROGRAMBENCH_DOCKER_CPUS    (default: 4)
#   LAUNCHPAD_DIR               (default: /home/agent/.local/share/<REDACTED_LAUNCHPAD_NAME>)
#   LAUNCHPAD_TOKEN             (default: /home/agent/.claude-custom)
#   LAUNCHPAD_BIN_DIR           (default: /home/agent/.local/bin)
#
# Outputs to:
#   <OUT_DIR_BASE>/<RUN_NAME>/<task>/<trace>/{trajectory.jsonl,submission.tar.gz,run.log,meta.json,doctor.log}
# ============================================================================
set -uo pipefail

TASK="${1:?usage: $0 <task_instance_id> [<trace_id>]}"
TRACE="${2:-trace1}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
HARNESS_DIR="$REPO_ROOT/opus-experiment/harness"

log() { printf '[run_task] %s\n' "$*"; }

# Which claude-config variant to bind-mount as the agent's /work/.claude.
# Overridable via env var CC_CONFIG_DIR (absolute path) or CC_CONFIG_NAME
# (subdir name under claude-configs/, e.g. "base", "framework-A").
# Default: claude-configs/base (minimal task-contract only, no doctrine).
if [[ -n "${CC_CONFIG_DIR:-}" ]]; then
  CONFIG_DIR="$CC_CONFIG_DIR"
elif [[ -n "${CC_CONFIG_NAME:-}" ]]; then
  CONFIG_DIR="$REPO_ROOT/opus-experiment/claude-configs/$CC_CONFIG_NAME"
else
  CONFIG_DIR="$REPO_ROOT/opus-experiment/claude-configs/base"
fi
if [[ ! -f "$CONFIG_DIR/CLAUDE.md" ]]; then
  log "FATAL: CLAUDE.md not found at $CONFIG_DIR/CLAUDE.md"
  exit 1
fi
log "using claude-config: $CONFIG_DIR"

# ---- preflight: docker available -------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "FATAL: docker not on PATH"
  exit 1
fi

CC_MODEL="${CC_MODEL:-claude-opus-4-7}"
CC_TIMEOUT_SECONDS="${CC_TIMEOUT_SECONDS:-21600}"   # 6hr per task
RUN_NAME="${RUN_NAME:-cc-opus-4.7-$(date -u +%Y%m%d-%H%M%S)}"
OUT_DIR_BASE="${OUT_DIR_BASE:-/tmp/cc-runs}"
DOCKER_CPUS="${PROGRAMBENCH_DOCKER_CPUS:-4}"

LAUNCHPAD_DIR="${LAUNCHPAD_DIR:-/home/agent/.local/share/<REDACTED_LAUNCHPAD_NAME>}"
LAUNCHPAD_TOKEN="${LAUNCHPAD_TOKEN:-/home/agent/.claude-custom}"
LAUNCHPAD_BIN_DIR="${LAUNCHPAD_BIN_DIR:-/home/agent/.local/bin}"
# Holds mitmproxy-ca.pem + ca-bundle.pem -- proxy TLS verification needs these.
# Without them, launchpad inside the container tries to download from
# <REDACTED_PARSEWAVE_HOST> (blocked by iptables), writes an empty 0-byte CA,
# and every Anthropic request fails TLS -> api_retry loop -> no progress.
PARSEWAVE_DIR="${PARSEWAVE_DIR:-/home/agent/.local/share/parsewave}"

OUT_DIR="${OUT_DIR_BASE}/${RUN_NAME}/${TASK}/${TRACE}"
mkdir -p "$OUT_DIR"
# Container writes /out as root (then chmods a+rX); make the host dir at
# least group-writable so a non-root host user can clean it up later.
chmod 0777 "$OUT_DIR" 2>/dev/null || true

# ---- resolve task image ----------------------------------------------------
TASK_IMG_NAME="$(echo "$TASK" | sed 's/__/_1776_/g')"
TASK_IMG="programbench/${TASK_IMG_NAME}:task"

if ! docker image inspect "$TASK_IMG" >/dev/null 2>&1; then
  log "ERR: image $TASK_IMG not found locally. Build it via 'uv run programbench build --instance-id $TASK'."
  exit 1
fi

# ---- preflight: launchpad bind-mount sources exist -------------------------
for p in "$LAUNCHPAD_DIR" "$LAUNCHPAD_TOKEN" "$LAUNCHPAD_BIN_DIR/launchpad" "$LAUNCHPAD_BIN_DIR/claud" \
         "$PARSEWAVE_DIR/mitmproxy-ca.pem" "$PARSEWAVE_DIR/ca-bundle.pem"; do
  if [[ ! -e "$p" ]]; then
    log "FATAL: required launchpad path missing on host: $p"
    log "       run install-cc.sh first"
    exit 1
  fi
done

# ---- initial prompt --------------------------------------------------------
# Minimal. We deliberately do NOT name the reference path or source path in
# this prompt: claud passes the prompt as its own argv, and agents have been
# observed running `pkill -f <path>` against literal paths in the prompt --
# which matches claud and SIGKILLs it. Path info lives on disk in CLAUDE.md
# where pkill can't reach it.
INITIAL_PROMPT='Read /work/CLAUDE.md and follow it strictly. You have a 4-hour budget. Ultrathink before every major decision.'

# Make sure entrypoint + hooks are executable on the host side; the
# bind-mount carries the mode bit into the container.
chmod +x "$HARNESS_DIR/container_entrypoint.sh" 2>/dev/null || true
chmod +x "$CONFIG_DIR/hooks/"*.sh "$CONFIG_DIR/hooks/"*.py 2>/dev/null || true

# ---- run container ---------------------------------------------------------
CONTAINER_NAME="cc-$(echo "${TASK}-${TRACE}-$$" | tr '/:.' '___')"

log "starting container ${CONTAINER_NAME}"
log "  image=${TASK_IMG}"
log "  model=${CC_MODEL}  timeout=${CC_TIMEOUT_SECONDS}s"
log "  out=${OUT_DIR}"

START_TS=$(date +%s)

docker run --rm \
  --name "$CONTAINER_NAME" \
  --cap-add=NET_ADMIN \
  --cpus="$DOCKER_CPUS" \
  -v "$CONFIG_DIR:/work/.claude:ro" \
  -v "$CONFIG_DIR/CLAUDE.md:/work/CLAUDE.md:ro" \
  -v "$HARNESS_DIR:/opt/cc-harness:ro" \
  -v "$LAUNCHPAD_DIR:/host/launchpad:ro" \
  -v "$PARSEWAVE_DIR:/host/parsewave:ro" \
  -v "$LAUNCHPAD_TOKEN:/host/token:ro" \
  -v "$LAUNCHPAD_BIN_DIR:/host/launchpad-bin:ro" \
  -v /usr/bin/node:/usr/bin/node:ro \
  -v /usr/lib/node_modules/@anthropic-ai:/usr/lib/node_modules/@anthropic-ai:ro \
  -v "$OUT_DIR:/out:rw" \
  -e CC_MODEL="$CC_MODEL" \
  -e CC_TIMEOUT_SECONDS="$CC_TIMEOUT_SECONDS" \
  -e CC_INITIAL_PROMPT="$INITIAL_PROMPT" \
  -e TASK_ID="$TASK" \
  -e TRACE_ID="$TRACE" \
  --entrypoint /bin/bash \
  "$TASK_IMG" \
  /opt/cc-harness/container_entrypoint.sh
CC_RC=$?

END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))
log "container exited rc=${CC_RC} after ${DURATION}s"

# ---- trajectory -> trajectory.json (lossy adapter) -------------------------
# Downstream analysis tools (filter_traces.py, behavior_flags.py) expect a
# mini-swe-agent-shaped trajectory.json. Best-effort; failures non-fatal.
if [[ -s "$OUT_DIR/trajectory.jsonl" ]]; then
  log "converting trajectory.jsonl -> trajectory.json (lossy adapter)"
  python3 "$HARNESS_DIR/convert_trajectory.py" \
    "$OUT_DIR/trajectory.jsonl" \
    "$OUT_DIR/trajectory.json" \
    || log "WARN: trajectory converter exited non-zero; continuing"
else
  log "WARN: trajectory.jsonl empty or missing; skipping converter"
fi

log "outputs:"
ls -lh "$OUT_DIR" 2>/dev/null || true

log "done. rc=${CC_RC}  out=${OUT_DIR}"
exit "$CC_RC"
