#!/usr/bin/env bash
# Generic eval monitor. Watches a run dir; for each new (task,trace) with
# rc=0 + non-empty submission.tar.gz, runs programbench eval in its own
# tmux session. Skips already-graded tasks.
#
# Usage:
#   RUN=<run-name> bash eval_monitor.sh        # uses /tmp/cc-runs/$RUN
#   RUN_DIR=/path/to/run bash eval_monitor.sh
#
# Env:
#   PROGRAMBENCH  path to programbench CLI (default: ~/work/program-bench/.venv/bin/programbench)
#   EVAL_IN       staging dir for submissions (default: /tmp/eval-input-<run>)
#   EVAL_OUT      eval output dir (default: /tmp/eval-out-<run>)
#   POLL          seconds between polls (default: 60)
set -uo pipefail

if [[ -z "${RUN_DIR:-}" ]]; then
  : "${RUN:?need RUN or RUN_DIR}"
  RUN_DIR="/tmp/cc-runs/$RUN"
fi
RUN="${RUN:-$(basename "$RUN_DIR")}"
PROGRAMBENCH="${PROGRAMBENCH:-$HOME/work/program-bench/.venv/bin/programbench}"
EVAL_IN="${EVAL_IN:-/tmp/eval-input-$RUN}"
EVAL_OUT="${EVAL_OUT:-/tmp/eval-out-$RUN}"
POLL="${POLL:-60}"

mkdir -p "$EVAL_IN" "$EVAL_OUT"
echo "[monitor] watching $RUN_DIR  (poll=${POLL}s)"
echo "[monitor] eval-in  $EVAL_IN"
echo "[monitor] eval-out $EVAL_OUT"
echo "[monitor] programbench $PROGRAMBENCH"

while true; do
  for d in "$RUN_DIR"/*/trace1; do
    [ -d "$d" ] || continue
    TASK=$(basename "$(dirname "$d")")
    META="$d/meta.json"
    SUB="$d/submission.tar.gz"
    [ -s "$META" ] || continue
    [ -s "$SUB" ] || continue
    RC=$(jq -r .exit_code "$META" 2>/dev/null)
    [ "$RC" = "0" ] || continue

    SHORT=${TASK#*__}; SHORT=${SHORT%.*}
    SESSION="eval-${SHORT}"
    if tmux has-session -t "$SESSION" 2>/dev/null; then continue; fi
    EVAL_FILE="$EVAL_OUT/$(basename "$EVAL_IN")/$TASK/${TASK}.eval.json"
    [ -f "$EVAL_FILE" ] && continue

    mkdir -p "$EVAL_IN/$TASK"
    cp -n "$SUB" "$EVAL_IN/$TASK/submission.tar.gz" 2>/dev/null || true
    FILTER=$(printf "%s" "$TASK" | sed "s/[.]/\\./g")
    echo "[$(date -u +%H:%M:%S)] eval $TASK  (session=$SESSION)"
    tmux new -d -s "$SESSION" "cd $(dirname "$PROGRAMBENCH" | sed "s|/.venv/bin||") && $PROGRAMBENCH eval $EVAL_IN --filter \"^${FILTER}\\$\" -w 1 -b 4 --docker-cpus 4 -o $EVAL_OUT 2>&1 | tee /tmp/${SESSION}.log"
  done
  sleep "$POLL"
done
