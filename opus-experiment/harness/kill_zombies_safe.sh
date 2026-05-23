#!/usr/bin/env bash
# Kill orphan/zombie bash-tool subprocesses INSIDE a task container while
# preserving claud and its parent chain (su -> bash -> timeout -> launchpad -> claud).
# Dynamic: discovers claud's PID via process name match, then walks up to root
# to build the keep list. Robust to PID-numbering across runs.
set -uo pipefail

# 1. Find claud (the npm-installed claude binary, NOT the launchpad wrapper)
CLAUD_PID=$(pgrep -fo '^claude --print' 2>/dev/null | head -1)
if [ -z "$CLAUD_PID" ]; then
  echo "no claude --print process found; nothing to do (claud likely already exited)"
  exit 0
fi

# 2. Walk up from claud to PID 1, collecting ancestors
KEEP="$CLAUD_PID"
P=$CLAUD_PID
for i in 1 2 3 4 5 6 7 8 9 10; do
  PP=$(ps -p "$P" -o ppid= 2>/dev/null | tr -d ' ')
  [ -z "$PP" ] && break
  [ "$PP" = "0" ] && break
  [ "$PP" = "1" ] && break
  KEEP="$KEEP $PP"
  P=$PP
done
echo "preserving (claud + ancestors): $KEEP"

# 3. Kill every agent-owned PID NOT in the keep list
killed=0
for pid in $(ps -u agent -o pid= 2>/dev/null); do
  pid=$(echo "$pid" | tr -d ' ')
  [ -z "$pid" ] && continue
  in_keep=0
  for k in $KEEP; do
    if [ "$pid" = "$k" ]; then in_keep=1; break; fi
  done
  if [ "$in_keep" = "0" ]; then
    kill -9 "$pid" 2>/dev/null && killed=$((killed+1))
  fi
done
echo "killed $killed orphan PIDs"
