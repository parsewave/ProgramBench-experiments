#!/usr/bin/env bash
# ============================================================================
# container_entrypoint.sh
# ----------------------------------------------------------------------------
# Runs INSIDE the task container as PID 1 (root). Responsibilities:
#
#   1. Install an iptables egress allowlist that ONLY permits TCP traffic to
#      the Parsewave Claude proxy (<REDACTED_PROXY_IP_1>:8080). All other outbound
#      traffic (incl. DNS) is dropped. Container must be launched with
#      --cap-add=NET_ADMIN for this to take effect.
#   2. Ensure a non-root user exists (prefer one baked into the task image:
#      'agent', 'worker', 'user'; otherwise create 'agent' with uid 1000).
#   3. Wire launchpad + claud into the non-root user's $HOME by copying
#      bind-mounted host files (/host/launchpad, /host/token,
#      /host/launchpad-bin).
#   4. Verify the proxy works: `launchpad doctor claud` must PASS.
#   5. Run `claud --print --output-format=stream-json` as the non-root user
#      with cwd=/work and the harness-supplied initial prompt. Wrapped in
#      `timeout` so it cannot exceed the configured wall clock.
#   6. Tar /work/ -> /out/submission.tar.gz (excluding bind-mounted .claude/
#      and CLAUDE.md which belong to the harness, not the agent's submission).
#   7. Write /out/meta.json with timing, exit code, model, etc.
#
# Inputs (env vars):
#   CC_MODEL, CC_TIMEOUT_SECONDS, CC_INITIAL_PROMPT,
#   TASK_ID, TRACE_ID
#
# Bind-mounts expected (read-only unless noted):
#   /work/.claude              -- CC project config (ro)
#   /work/CLAUDE.md            -- project rules (ro)
#   /opt/cc-harness            -- this script + helpers (ro)
#   /host/launchpad            -- ~/.local/share/<REDACTED_LAUNCHPAD_NAME> (ro)
#   /host/parsewave            -- ~/.local/share/parsewave -- holds
#                                 mitmproxy-ca.pem + ca-bundle.pem; required
#                                 for the agent's TLS to the proxy (ro)
#   /host/token                -- ~/.claude-custom OAuth token (ro)
#   /host/launchpad-bin        -- dir containing `launchpad` and `claud` bins (ro)
#   /out                       -- where trajectory.jsonl, submission.tar.gz,
#                                 run.log, meta.json land (rw)
#
# Note: `set -uo pipefail` (not -e) so we can capture claud's exit code.
# ============================================================================
set -uo pipefail

# Default proxy address; we override below by parsing launchpad's
# env/prod/client.json (the authoritative source). Parsewave rotates the
# proxy IP from time to time, so hardcoding here is just a fallback.
PROXY_IP="<REDACTED_PROXY_IP_1>"
PROXY_PORT="8080"

log() { printf '[entrypoint] %s\n' "$*"; }

# Parse the currently-active proxy from launchpad's client.json. Falls back
# to the hardcoded defaults if the file is missing or unparseable. Reads
# from the bind-mounted host copy so we get the latest without going through
# the iptables-blocked <REDACTED_PARSEWAVE_HOST>.
resolve_proxy_from_client_json() {
  local cj=/host/launchpad/env/prod/client.json
  [[ -f "$cj" ]] || return 1
  command -v python3 >/dev/null 2>&1 || return 1
  local url
  url=$(python3 -c "
import json, sys
try:
    d = json.load(open('$cj'))
    print(d.get('active_proxy_url',''))
except Exception:
    pass
" 2>/dev/null)
  [[ -n "$url" ]] || return 1
  # url looks like http://<REDACTED_PROXY_IP_2>:8080 or https://host:port
  local host_port="${url#*://}"
  PROXY_IP="${host_port%:*}"
  PROXY_PORT="${host_port##*:}"
  return 0
}

if resolve_proxy_from_client_json; then
  log "proxy resolved from client.json: ${PROXY_IP}:${PROXY_PORT}"
else
  log "WARN: could not parse client.json; falling back to ${PROXY_IP}:${PROXY_PORT}"
fi

# ---- 0. sanity: required env vars ------------------------------------------
: "${CC_MODEL:?CC_MODEL required}"
: "${CC_TIMEOUT_SECONDS:?CC_TIMEOUT_SECONDS required}"
: "${CC_INITIAL_PROMPT:?CC_INITIAL_PROMPT required}"
: "${TASK_ID:?TASK_ID required}"
: "${TRACE_ID:?TRACE_ID required}"

mkdir -p /out
chmod 0777 /out 2>/dev/null || true

# ---- 0.5. wire Node + claude binary (bind-mounted from host) ---------------
# The launchpad wrapper execs `claude` (npm-installed) at runtime. The host
# has node + the @anthropic-ai/claude-code module bind-mounted in at
# /usr/bin/node and /usr/lib/node_modules/@anthropic-ai/. Create the symlink
# the npm install would have made.
if [[ -x /usr/bin/node && -f /usr/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe ]]; then
  ln -sf /usr/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe /usr/local/bin/claude
  log "wired claude: $(claude --version 2>&1 | head -1)"
else
  log "FATAL: node or claude-code bind-mount missing"
  ls -la /usr/bin/node 2>&1 | sed 's/^/  /'
  ls -la /usr/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe 2>&1 | sed 's/^/  /'
  exit 88
fi

# ---- 1. iptables egress allowlist ------------------------------------------
log "installing iptables egress allowlist (proxy=${PROXY_IP}:${PROXY_PORT})"
if ! command -v iptables >/dev/null 2>&1; then
  log "iptables not present; attempting apt-get install"
  if command -v apt-get >/dev/null 2>&1; then
    DEBIAN_FRONTEND=noninteractive apt-get update -qq 2>/dev/null || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iptables 2>/dev/null || true
  fi
fi

if ! command -v iptables >/dev/null 2>&1; then
  log "FATAL: iptables unavailable; cannot enforce egress allowlist"
  exit 90
fi

# Order matters: ACCEPT rules first, then default-DROP.
iptables -A OUTPUT -d "${PROXY_IP}" -p tcp --dport "${PROXY_PORT}" -j ACCEPT \
  || { log "FATAL: iptables ACCEPT failed (missing NET_ADMIN?)"; exit 91; }
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -P OUTPUT DROP

# Inbound is irrelevant for an agent, but mirror the policy for hygiene.
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -P INPUT DROP

log "iptables rules installed:"
iptables -L OUTPUT -n -v | sed 's/^/[entrypoint]   /'

# ---- 2. resolve / create non-root user -------------------------------------
AGENT_USER=""
for candidate in agent worker user ubuntu; do
  if id "$candidate" >/dev/null 2>&1; then
    AGENT_USER="$candidate"
    break
  fi
done

if [[ -z "$AGENT_USER" ]]; then
  AGENT_USER="agent"
  log "no existing non-root user found; creating ${AGENT_USER} (uid 1000)"
  # If uid 1000 is taken, useradd will pick the next free one -- fine.
  useradd -m -s /bin/bash -u 1000 "$AGENT_USER" 2>/dev/null \
    || useradd -m -s /bin/bash "$AGENT_USER"
fi

AGENT_HOME="$(getent passwd "$AGENT_USER" | cut -d: -f6)"
log "agent user: ${AGENT_USER}  home: ${AGENT_HOME}"
# The launchpad wrapper scripts on the host hard-code /home/ubuntu/.local/share/<REDACTED_LAUNCHPAD_NAME>/
# in their `exec` lines. When the agent user inside the task container is `agent` (the task images
# ship it), those paths do not resolve. Bridge with a symlink so the same scripts work without edits.
if [[ "$AGENT_USER" != "ubuntu" && ! -e /home/ubuntu ]]; then
  ln -s "$AGENT_HOME" /home/ubuntu
  log "linked /home/ubuntu -> $AGENT_HOME (launchpad wrapper compat)"
fi


# ---- 3. give agent write access to /work + read access to /workspace -------
# /work is part of the task image; it's owned by root by default. The agent
# needs to write under /work/work/ for the submission, and read the (ro)
# bind-mounted /work/.claude and /work/CLAUDE.md.
if [[ -d /work ]]; then
  chown -R "${AGENT_USER}:${AGENT_USER}" /work 2>/dev/null || true
  mkdir -p /work/work
  chown "${AGENT_USER}:${AGENT_USER}" /work/work 2>/dev/null || true
else
  log "WARN: /work does not exist in image; creating"
  mkdir -p /work/work
  chown -R "${AGENT_USER}:${AGENT_USER}" /work
fi

# Task images ship /workspace/executable as `--x--x--x` (executable, no
# read). `strings` needs read access; add it so the session-start hook can
# extract symbols.
if [[ -e /workspace/executable ]]; then
  chmod a+r /workspace/executable 2>/dev/null || true
fi
# Same for the rest of /workspace (READMEs, configs, docs)
chmod -R a+rX /workspace 2>/dev/null || true

# ---- 4. lay down launchpad + claud for agent --------------------------------
log "installing launchpad into ${AGENT_HOME} from bind-mounted host copy"

install -d -o "$AGENT_USER" -g "$AGENT_USER" \
  "${AGENT_HOME}/.local" \
  "${AGENT_HOME}/.local/share" \
  "${AGENT_HOME}/.local/share/<REDACTED_LAUNCHPAD_NAME>" \
  "${AGENT_HOME}/.local/share/parsewave" \
  "${AGENT_HOME}/.local/bin"

if [[ -d /host/launchpad ]]; then
  # Copy (not symlink) so launchpad's own state writes don't try to mutate
  # the ro bind-mount.
  cp -a /host/launchpad/. "${AGENT_HOME}/.local/share/<REDACTED_LAUNCHPAD_NAME>/"
  chown -R "${AGENT_USER}:${AGENT_USER}" "${AGENT_HOME}/.local/share/<REDACTED_LAUNCHPAD_NAME>"
else
  log "FATAL: /host/launchpad bind-mount missing"
  exit 92
fi

# parsewave/ holds mitmproxy-ca.pem + ca-bundle.pem. Without these, launchpad
# inside the container tries to download the CA from <REDACTED_PARSEWAVE_HOST>
# (blocked by iptables), writes a 0-byte cert, and every Anthropic call
# fails TLS -> api_retry loop -> zero progress. Copy from host bind-mount.
if [[ -d /host/parsewave ]]; then
  cp -a /host/parsewave/. "${AGENT_HOME}/.local/share/parsewave/"
  chown -R "${AGENT_USER}:${AGENT_USER}" "${AGENT_HOME}/.local/share/parsewave"
  chmod 0700 "${AGENT_HOME}/.local/share/parsewave"
  log "parsewave CA dir installed (mitmproxy-ca.pem $(wc -c <${AGENT_HOME}/.local/share/parsewave/mitmproxy-ca.pem) bytes, ca-bundle.pem $(wc -c <${AGENT_HOME}/.local/share/parsewave/ca-bundle.pem) bytes)"
else
  log "FATAL: /host/parsewave bind-mount missing (mitmproxy CA cert)"
  exit 96
fi

if [[ -f /host/token ]]; then
  cp /host/token "${AGENT_HOME}/.claude-custom"
  chown "${AGENT_USER}:${AGENT_USER}" "${AGENT_HOME}/.claude-custom"
  chmod 0600 "${AGENT_HOME}/.claude-custom"
else
  log "FATAL: /host/token bind-mount missing"
  exit 93
fi

# The launchpad binary and the claud wrapper live in /host/launchpad-bin/ on
# the host. We symlink them into the agent's ~/.local/bin so they're on PATH
# under a login shell. They're scripts that just invoke launchpad's own
# state under ~/.local/share/<REDACTED_LAUNCHPAD_NAME>, so symlinking is fine.
if [[ -d /host/launchpad-bin ]]; then
  for bin in launchpad claud; do
    if [[ -e "/host/launchpad-bin/${bin}" ]]; then
      ln -sf "/host/launchpad-bin/${bin}" "${AGENT_HOME}/.local/bin/${bin}"
    else
      log "WARN: /host/launchpad-bin/${bin} not found"
    fi
  done
  chown -h "${AGENT_USER}:${AGENT_USER}" "${AGENT_HOME}/.local/bin/launchpad" 2>/dev/null || true
  chown -h "${AGENT_USER}:${AGENT_USER}" "${AGENT_HOME}/.local/bin/claud" 2>/dev/null || true
else
  log "FATAL: /host/launchpad-bin bind-mount missing"
  exit 94
fi

# ---- 4.5. config audit (visible to claud) ----------------------------------
log "config audit (what claud will see at cwd=/work):"
log "  CLAUDE.md:       $([ -f /work/CLAUDE.md ] && echo OK || echo MISSING)"
log "  settings.json:   $([ -f /work/.claude/settings.json ] && echo OK || echo MISSING)"
log "  skills count:    $(ls -d /work/.claude/skills/*/ 2>/dev/null | wc -l) (each should have SKILL.md)"
log "  agents count:    $(ls /work/.claude/agents/*.md 2>/dev/null | wc -l)"
log "  hook scripts:    $(ls /work/.claude/hooks/*.sh /work/.claude/hooks/*.py 2>/dev/null | wc -l)"

# Show settings.json contents (truncated) so we know which hooks are wired
if [[ -f /work/.claude/settings.json ]]; then
  log "settings.json (first 30 lines):"
  head -30 /work/.claude/settings.json | sed 's/^/[entrypoint]   /'
fi

# ---- 5. verify proxy connectivity ------------------------------------------
log "running 'launchpad doctor claud' as ${AGENT_USER}"
DOCTOR_LOG="/out/doctor.log"
if ! su - "$AGENT_USER" -c "HOME='$AGENT_HOME' PATH=\"$AGENT_HOME/.local/bin:\$PATH\" launchpad doctor claud" \
      > "$DOCTOR_LOG" 2>&1; then
  log "FATAL: launchpad doctor claud FAILED. See ${DOCTOR_LOG}:"
  sed 's/^/[entrypoint]   /' "$DOCTOR_LOG" >&2 || true
  exit 95
fi
log "launchpad doctor claud: PASS"

# ---- 6. run claud as agent -------------------------------------------------
log "starting claud (model=${CC_MODEL} no max-turns timeout=${CC_TIMEOUT_SECONDS}s)"
log "  task=${TASK_ID}  trace=${TRACE_ID}  cwd=/work"

START_TS=$(date +%s)

# Run claud as the agent user. The HEREDOC-as-shell-script pattern is the
# cleanest way to thread env vars + the multi-line prompt through `su -`
# without quoting hell.
#
# We export the prompt into the agent shell so it isn't re-expanded by su's
# parsing of -c. `timeout` ensures hard wall-clock cutoff.
#
# RETRY with session preservation: launchpad's subscription pool occasionally
# returns transient errors -- "organization has been disabled" routing flake,
# "Server is temporarily limiting" rate limit, "socket connection was closed
# unexpectedly" drops. claud-code does NOT retry these internally so the run
# dies on the offending turn.
#
# We retry up to 4 times. To avoid losing in-context history across retries,
# a session UUID is generated up front and claud uses --session-id on attempt
# 1 + --resume on attempts 2-4. This preserves the agent's prior turns,
# probing history, and behavior_map state instead of starting from a blank
# context (which previously wasted hours of work on failed-then-resumed tasks).
# Stage the initial prompt in a file the agent can read, so we never pass it
# as a positional argv to claud. Two reasons: (1) claud's process argv would
# otherwise contain any path the prompt mentions (e.g. /workspace/...), making
# the agent vulnerable to its own `pkill -f /workspace/...` cleanup commands
# matching the parent process. (2) Smaller argv = cleaner ps output.
PROMPT_FILE=/tmp/claud-prompt.txt
printf '%s' "$CC_INITIAL_PROMPT" > "$PROMPT_FILE"
chown "${AGENT_USER}:${AGENT_USER}" "$PROMPT_FILE"
chmod 0600 "$PROMPT_FILE"

MAX_ATTEMPTS=4
SESSION_ID=$(cat /proc/sys/kernel/random/uuid)
log "claud session id: ${SESSION_ID}"

for ATTEMPT in $(seq 1 "$MAX_ATTEMPTS"); do
  log "claud attempt ${ATTEMPT}/${MAX_ATTEMPTS}"
  # NOTE: do NOT pre-truncate /out/trajectory.jsonl or /out/run.log here as
  # root -- that creates root-owned files agent can't write to, and claud
  # exits silently with rc=1. claud's own `>` redirect (attempt 1) truncates
  # the file when it opens it as agent. Attempts 2+ use `>>` to append so
  # the resumed session's events concatenate with the prior attempt's.

  # Capture file sizes before this attempt so the retry-trigger grep below
  # only inspects events written BY THIS ATTEMPT -- not prior attempts'
  # flake text, which would otherwise infinite-loop retries.
  TRAJ_OFFSET=$(stat -c%s /out/trajectory.jsonl 2>/dev/null || echo 0)
  LOG_OFFSET=$(stat -c%s /out/run.log 2>/dev/null || echo 0)

  HOME="$AGENT_HOME" \
  CC_INITIAL_PROMPT="$CC_INITIAL_PROMPT" \
  CC_MODEL="$CC_MODEL" \
  CC_TIMEOUT_SECONDS="$CC_TIMEOUT_SECONDS" \
  ATTEMPT="$ATTEMPT" \
  SESSION_ID="$SESSION_ID" \
  REF_BIN=/workspace/executable \
  su -p "$AGENT_USER" -c "
    set -uo pipefail
    export HOME='$AGENT_HOME'
    export PATH=\"\$HOME/.local/bin:\$PATH\"
    cd /work
    if [[ \"\$ATTEMPT\" -eq 1 ]]; then
      timeout \"\$CC_TIMEOUT_SECONDS\" claud \
        --print \
        --input-format=text \
        --output-format=stream-json \
        --verbose \
        --model \"\$CC_MODEL\" \
        --effort max \
        --permission-mode bypassPermissions \
        --disallowedTools \"WebSearch,WebFetch\" \
        --session-id \"\$SESSION_ID\" \
        < /tmp/claud-prompt.txt \
        > /out/trajectory.jsonl 2> /out/run.log
    else
      timeout \"\$CC_TIMEOUT_SECONDS\" claud \
        --print \
        --input-format=text \
        --output-format=stream-json \
        --verbose \
        --model \"\$CC_MODEL\" \
        --effort max \
        --permission-mode bypassPermissions \
        --disallowedTools \"WebSearch,WebFetch\" \
        --resume \"\$SESSION_ID\" \
        'The previous turn was interrupted by an API error. Review what you have done so far in /work/work/ (behavior_map.md, goldens/, source files, diff_probe.sh if present) and continue the task from where you left off. Do not start over.' \
        >> /out/trajectory.jsonl 2>> /out/run.log
    fi
  " < /dev/null
  CC_RC=$?

  # Broadened retry trigger: routing flake + rate limit + socket drop.
  # ONLY inspect content written BY THIS ATTEMPT (offsets captured above) --
  # without this, prior attempts' flake text matches on retries and produces
  # an infinite-retry doom loop on what is actually a successful attempt.
  if tail -c +$((TRAJ_OFFSET + 1)) /out/trajectory.jsonl 2>/dev/null \
       | grep -qE "organization has been disabled|Server is temporarily limiting|socket connection was closed unexpectedly|Rate limited" \
     || tail -c +$((LOG_OFFSET + 1)) /out/run.log 2>/dev/null \
       | grep -qE "organization has been disabled|Server is temporarily limiting|socket connection was closed unexpectedly|Rate limited"; then
    log "attempt ${ATTEMPT}: API flake detected -- retrying same session ${SESSION_ID}"
    if [[ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]]; then
      log "  sleeping 60s before retry..."
      sleep 60
      continue
    else
      log "  out of retries; failing run"
    fi
  fi

  # Either success, or a non-retryable failure (timeout, real model error, etc.)
  break
done

END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))
log "claud exited rc=${CC_RC} after ${DURATION}s"

# ---- 7. package submission -------------------------------------------------
# Defensive mirror: agents sometimes interpret "./work/" from the initial
# prompt as the *current* /work dir rather than the /work/work/ subdir,
# and write sd.py/compile.sh/etc directly under /work. Without this mirror
# we'd tar an empty /work/work/ and ship a 45-byte tarball.
log "mirroring /work/* -> /work/work/* (in case agent wrote to the wrong place)..."
mkdir -p /work/work
chown "${AGENT_USER}:${AGENT_USER}" /work/work 2>/dev/null || true
(
  cd /work
  for item in *; do
    [[ "$item" == "work" || "$item" == "CLAUDE.md" || "$item" == ".claude" || "$item" == "executable" ]] && continue
    # Only copy if /work/work doesn't already have it (don't clobber the
    # agent's intended /work/work/ files with a duplicate from /work/)
    if [[ ! -e "/work/work/$item" ]]; then
      cp -a "$item" /work/work/ 2>/dev/null && log "  mirrored: $item"
    fi
  done
) 2>/dev/null

log "packaging submission..."
if [[ -d /work/work ]]; then
  tar czf /out/submission.tar.gz \
    --exclude='node_modules' \
    --exclude='target' \
    --exclude='.git' \
    -C /work/work . 2>/dev/null \
    || log "WARN: tar exited non-zero (work/work/ may be empty)"
else
  log "WARN: /work/work not found; creating empty submission.tar.gz"
  tar czf /out/submission.tar.gz --files-from=/dev/null
fi

# Belt-and-suspenders: also save a raw tar of /work (excl. harness bits + binary)
# so we have full source recovery even if the path mirror misses something.
tar czf /out/source-backup.tar.gz \
  --exclude='work' --exclude='.claude' --exclude='CLAUDE.md' --exclude='executable' \
  --exclude='target' --exclude='node_modules' --exclude='.git' \
  -C /work . 2>/dev/null || log "WARN: source-backup tar non-zero"
log "  source-backup: $(stat -c%s /out/source-backup.tar.gz 2>/dev/null || echo '?') bytes"

# ---- 8. meta.json ----------------------------------------------------------
# Prefer python3 (cleaner JSON encoding); fall back to a hand-rolled heredoc
# if python3 isn't in the image.
if command -v python3 >/dev/null 2>&1; then
  DURATION="$DURATION" CC_RC="$CC_RC" START_TS="$START_TS" END_TS="$END_TS" \
  PROXY_IP="$PROXY_IP" PROXY_PORT="$PROXY_PORT" \
  python3 - > /out/meta.json <<'PYEOF'
import json, os
meta = {
    "task_id":          os.environ["TASK_ID"],
    "trace_id":         os.environ["TRACE_ID"],
    "model":            os.environ["CC_MODEL"],
    "max_turns":        None,
    "timeout_seconds":  int(os.environ["CC_TIMEOUT_SECONDS"]),
    "duration_seconds": int(os.environ["DURATION"]),
    "exit_code":        int(os.environ["CC_RC"]),
    "start_ts":         int(os.environ["START_TS"]),
    "end_ts":           int(os.environ["END_TS"]),
    "container_run":    True,
    "proxy":            os.environ["PROXY_IP"] + ":" + os.environ["PROXY_PORT"],
}
print(json.dumps(meta, indent=2))
PYEOF
else
  cat > /out/meta.json <<JSON
{
  "task_id": "${TASK_ID}",
  "trace_id": "${TRACE_ID}",
  "model": "${CC_MODEL}",
  "max_turns": null,
  "timeout_seconds": ${CC_TIMEOUT_SECONDS},
  "duration_seconds": ${DURATION},
  "exit_code": ${CC_RC},
  "start_ts": ${START_TS},
  "end_ts": ${END_TS},
  "container_run": true,
  "proxy": "${PROXY_IP}:${PROXY_PORT}"
}
JSON
fi

# Make /out files readable from host (uid mapping varies)
chmod -R a+rX /out 2>/dev/null || true

log "outputs:"
ls -lh /out | sed 's/^/[entrypoint]   /'

log "done. rc=${CC_RC}"
exit "$CC_RC"
