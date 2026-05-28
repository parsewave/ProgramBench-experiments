#!/usr/bin/env bash
# Batch orchestrator for the CC-Opus harness.
# Reads tasks_*.yaml and runs each (task × trace) via run_task.sh,
# with a bounded parallel queue. Modeled after trace-gen/run_sample16.sh.
#
# Flags:
#   --config <path>    yaml to read (default: tasks_smoke.yaml)
#   --run-name <name>  resume an existing run; skips (task,trace) with trajectory.jsonl already present
#   --parallel N       max concurrent containers (default 1)
#   --smoke            stop after first (task,trace), validate output, exit
#
# Pre-reqs (container-CC architecture):
#   - docker daemon reachable; agent user in `docker` group (see install-cc.sh)
#   - launchpad installed for the agent user with a valid token at
#     ~/.claude-custom; `launchpad doctor claud` PASSes
#   - programbench task images already built / pulled for the listed
#     instance_ids
#
# The agent's Bash tool is sandboxed inside each task container by an
# iptables egress allowlist (proxy IP only). See container_entrypoint.sh.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

CONFIG="$SCRIPT_DIR/tasks_smoke.yaml"
RUN_NAME=""
PARALLEL=1
SMOKE=0
CLAUDE_CONFIG=""    # subdir name under claude-configs/ (e.g. base, framework-A)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --run-name) RUN_NAME="$2"; shift 2 ;;
    --parallel) PARALLEL="$2"; shift 2 ;;
    --smoke) SMOKE=1; shift ;;
    --claude-config) CLAUDE_CONFIG="$2"; shift 2 ;;
    *) echo "[run_batch] unknown arg: $1"; exit 1 ;;
  esac
done

# Resolve + validate claude-config variant; propagates to run_task.sh via env.
if [[ -n "$CLAUDE_CONFIG" ]]; then
  CC_CONFIG_DIR_RESOLVED="$REPO_ROOT/opus-experiment/claude-configs/$CLAUDE_CONFIG"
  if [[ ! -f "$CC_CONFIG_DIR_RESOLVED/CLAUDE.md" ]]; then
    echo "[run_batch] FATAL: --claude-config $CLAUDE_CONFIG not found at $CC_CONFIG_DIR_RESOLVED"
    exit 1
  fi
  export CC_CONFIG_DIR="$CC_CONFIG_DIR_RESOLVED"
  echo "[run_batch] claude-config: $CLAUDE_CONFIG ($CC_CONFIG_DIR)"
else
  echo "[run_batch] claude-config: (default — claude-configs/base)"
fi

[[ -f "$CONFIG" ]] || { echo "[run_batch] ERR: $CONFIG not found"; exit 1; }

# Parse yaml via python
read CC_MODEL CC_TIMEOUT_SECONDS TRACES_PER_TASK < <(python3 -c "
import yaml
d = yaml.safe_load(open('$CONFIG'))
print(
  d.get('model','claude-opus-4-7'),
  d.get('timeout_seconds',21600),
  d.get('traces_per_task',1),
)")
export CC_MODEL CC_TIMEOUT_SECONDS

INSTANCE_IDS=( $(python3 -c "
import yaml
for inst in yaml.safe_load(open('$CONFIG')).get('instance_ids', []): print(inst)
") )

if [[ -z "$RUN_NAME" ]]; then
  RUN_NAME="cc-opus-$(date -u +%Y%m%d-%H%M%S)"
fi
export RUN_NAME
# /tmp/cc-runs lives under the agent user's writable space; make sure the
# per-run dir is world-writable so the container (which writes /out as root)
# and the host (which reads results back) can both touch it.
OUT_DIR_BASE="${OUT_DIR_BASE:-/tmp/cc-runs}"
export OUT_DIR_BASE
OUT_BASE="${OUT_DIR_BASE}/${RUN_NAME}"
mkdir -p "$OUT_BASE"
chmod 0777 "$OUT_DIR_BASE" "$OUT_BASE" 2>/dev/null || true

echo "[run_batch] run: $RUN_NAME  model: $CC_MODEL  timeout: ${CC_TIMEOUT_SECONDS}s  parallel: $PARALLEL"
echo "[run_batch] tasks: ${#INSTANCE_IDS[@]}  traces/task: $TRACES_PER_TASK"
echo "[run_batch] outputs under $OUT_BASE"

# Build the work queue: (task, trace) tuples, skipping any with trajectory.jsonl already
QUEUE=()
for task in "${INSTANCE_IDS[@]}"; do
  for i in $(seq 1 "$TRACES_PER_TASK"); do
    trace="trace$i"
    out_dir="$OUT_BASE/$task/$trace"
    if [[ -f "$out_dir/trajectory.jsonl" ]]; then
      echo "[run_batch] SKIP (already have trajectory): $task/$trace"
      continue
    fi
    QUEUE+=("$task|$trace")
  done
done
echo "[run_batch] queue: ${#QUEUE[@]} jobs"

# Smoke mode: just first job
if [[ "$SMOKE" -eq 1 ]]; then
  QUEUE=("${QUEUE[0]}")
fi

# Bounded-parallel loop
run_one() {
  local pair="$1"
  local task="${pair%|*}"
  local trace="${pair#*|}"
  echo "[run_batch] START $task/$trace"
  bash "$SCRIPT_DIR/run_task.sh" "$task" "$trace" >"$OUT_BASE/$task/$trace/.log" 2>&1 \
    && echo "[run_batch] DONE  $task/$trace" \
    || echo "[run_batch] FAIL  $task/$trace (see $OUT_BASE/$task/$trace/.log)"
}

declare -a PIDS=()
for pair in "${QUEUE[@]}"; do
  task="${pair%|*}"; trace="${pair#*|}"
  mkdir -p "$OUT_BASE/$task/$trace"
  chmod 0777 "$OUT_BASE/$task" "$OUT_BASE/$task/$trace" 2>/dev/null || true
  # wait for a slot
  while (( ${#PIDS[@]} >= PARALLEL )); do
    NEW_PIDS=()
    for pid in "${PIDS[@]}"; do
      kill -0 "$pid" 2>/dev/null && NEW_PIDS+=("$pid")
    done
    PIDS=("${NEW_PIDS[@]}")
    sleep 5
  done
  run_one "$pair" &
  PIDS+=($!)
done
wait

echo "[run_batch] all done. Run name: $RUN_NAME"
echo "  results: $OUT_BASE"
