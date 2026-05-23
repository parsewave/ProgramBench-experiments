#!/usr/bin/env bash
# Eval monitor for the cc-opus-top9 run. Reads RUN env var to know which
# /tmp/cc-runs/<name>/ to watch; per-task auto-eval as submissions land.
set -uo pipefail
export HF_TOKEN="${HF_TOKEN:?HF_TOKEN env var required}"

RUN="${RUN:?RUN env var required (e.g. cc-opus-top9-20260520-...)}"
RUN_DIR=/tmp/cc-runs/${RUN}
EVAL_IN=/tmp/eval-input-top9
EVAL_OUT=/tmp/eval-out-top9
mkdir -p "$EVAL_IN" "$EVAL_OUT"

echo "[monitor] watching $RUN_DIR"
echo "[monitor] eval input dir $EVAL_IN, output $EVAL_OUT"

while true; do
  for d in "$RUN_DIR"/*/trace1; do
    [ -d "$d" ] || continue
    TASK=$(basename "$(dirname "$d")")
    META=$d/meta.json
    SUB=$d/submission.tar.gz
    [ -s "$META" ] || continue
    [ -s "$SUB" ] || continue
    RC=$(jq -r .exit_code "$META" 2>/dev/null)
    # Submission tarball is the source of truth — accept any rc as long as a non-stub
    # submission exists. rc=0 clean exit, rc=1 api-error-after-work, rc=137 sigkilled
    # mid-cleanup. claud emits its result message regardless.
    SUB_SIZE=$(stat -c %s "$SUB" 2>/dev/null || echo 0)
    [ "$SUB_SIZE" -gt 1000 ] || continue

    AFTER_US=${TASK#*__}
    SHORT=${AFTER_US%.*}
    SESSION="eval-${SHORT}"

    if tmux has-session -t "$SESSION" 2>/dev/null; then continue; fi
    EVAL_FILE="$EVAL_OUT/eval-input-top9/$TASK/${TASK}.eval.json"
    if [ -f "$EVAL_FILE" ]; then continue; fi

    mkdir -p "$EVAL_IN/$TASK"
    cp "$SUB" "$EVAL_IN/$TASK/submission.tar.gz"
    # Escape dots in TASK name for regex
    FILTER=$(printf '%s' "$TASK" | sed 's/[.]/\\./g')
    echo "[$(date -u +%H:%M:%S)] starting $SESSION for $TASK (filter=$FILTER)"
    tmux new -d -s "$SESSION" "cd /opt/programbench && .venv/bin/programbench eval $EVAL_IN --filter '^${FILTER}\$' -w 1 -b 4 --docker-cpus 4 -o $EVAL_OUT 2>&1 | tee /root/eval-${SHORT}.log"
  done
  sleep 60
done
