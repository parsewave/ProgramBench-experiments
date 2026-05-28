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
# Agent runs with cwd=/work. Be EXPLICIT about paths -- earlier wording
# ("./work/ with compile.sh") was ambiguous when cwd was already /work,
# and every agent in run-5tasks-20260519-151748 wrote source to /work/*
# instead of /work/work/*. We salvaged it via a mirror step in the
# entrypoint, but the prompt should not need that crutch.
INITIAL_PROMPT='This is a reverse-engineering benchmark. Any approach that shortcuts behavioral observation - finding existing source code, wrapping the binary, or installing the original tool - does not count as a solution. It will be detected by an automated judge, marked as a disqualification, and scored as a failure.

<RULES>
## What is not allowed

### 1. Obtaining source code

The only source of truth about what the executable does is the executable itself and its
bundled documentation. You must not search the internet, package registries, or any external
source for information about the source code of this project. Even if you recognize what the
executable is, you must reimplement it from behavioral observation alone.

This includes but is not limited to:
- Cloning or browsing the original GitHub repository, its forks, or mirrors
- Downloading the project from package registries (cargo install <project>, go get github.com slash <org> slash <project>,
  pip install <project>, apt-get source <project>, npm install <project>, etc.)
- Fetching source tarballs from project websites
- Using a package manager to download the project as a dependency and then reading its cached source
  (e.g. navigating into the cargo registry src directory or the Go module cache directory)
- Searching the web for source code or implementation details of this project

### 2. Wrapping or reusing the original binary

Your submission must be a genuine reimplementation. The provided reference binary at REF_BIN
is for observation only. Your final solution must not depend on it or any other pre-built
version of the same tool at runtime.

This includes but is not limited to:
- Writing a wrapper script that delegates to the original binary
- Installing the tool from a package manager and shimming to it
- Writing a compile.sh that simply makes the provided binary executable or copies it
- Building a binary whose main function shells out to an external tool
- Re-linking prebuilt object files found in the workspace without writing new source code

### 3. Binary analysis of the provided executable

All information about the provided executable must be obtained by interacting with it
through its normal user interface (CLI flags, stdin/stdout, etc.).
- You MUST NOT decompile REF_BIN or use disassemblers (objdump, Ghidra, etc.) on it
- You MUST NOT use strace, ltrace, or similar tracing/instrumentation tools on REF_BIN

This restriction applies ONLY to the provided reference binary. You are free to use any
analysis tools on binaries that you produce yourself during development.

## What IS allowed

- Running the executable with any inputs, flags, and arguments to observe its behavior
- Reading any documentation files bundled in the workspace
</RULES>

You are running a ProgramBench task.

Paths (absolute, no ambiguity):
  - Reference binary:    $REF_BIN   (read/exec only)
  - Your cwd:            /work                   (CLAUDE.md lives here)
  - Write source HERE:   /work/work/             (THIS is what gets tarred for grading)
  - Build script:        /work/work/compile.sh   (must produce ./executable inside /work/work/)

ANYTHING you write outside /work/work/ is NOT submitted. Do not write source
files to /work/ directly -- only /work/work/ is packaged.

You have a 4-hour wall-clock budget. Use it for thorough probing and the
differential loop. Once your reimplementation matches the reference on a
clean statistical top-up (CLAUDE.md step 6), submit -- continued
verification beyond that does not raise certified reliability.

Before doing anything else: read /work/CLAUDE.md and follow it strictly. It
contains the rules and the phase-by-phase workflow (Discovery -> Language
selection -> Implementation -> Verification -> Submission gate).

Begin with Phase 1 (Discovery). Do not write any source until you have
produced /work/work/behavior_map.md and populated /work/work/goldens/.

Ultrathink before every major decision.'

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
