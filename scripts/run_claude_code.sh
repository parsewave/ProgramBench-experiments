#!/usr/bin/env bash
set -euo pipefail

TASK="${1:?usage: $0 <task_instance_id> [<output_root>]}"
OUTPUT_DIR="${2:-output}/${TASK}"
mkdir -p "$OUTPUT_DIR"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCTRINE="$REPO_ROOT/opus-experiment/CLAUDE.md"
[ -f "$DOCTRINE" ] || { echo "missing doctrine: $DOCTRINE" >&2; exit 1; }

NPM_GLOBAL="$(npm root -g 2>/dev/null || true)"
CLAUDE_PKG="${NPM_GLOBAL}/@anthropic-ai/claude-code"
CLAUDE_NATIVE="${CLAUDE_PKG}/bin/claude.exe"
[ -f "$CLAUDE_NATIVE" ] || { echo "claude-code native binary missing at ${CLAUDE_NATIVE} — run: npm install -g @anthropic-ai/claude-code" >&2; exit 1; }
[ "$(uname -s)" = "Linux" ] || echo "[warn] host is not Linux ($(uname -s)); the bind-mounted claude.exe is platform-specific and may not run inside a Linux container" >&2

[ -f "$HOME/.claude/.credentials.json" ] || { echo "no ~/.claude/.credentials.json — start a session with 'claude' once on the host" >&2; exit 1; }
[ -f "$HOME/.claude.json" ] || { echo "no ~/.claude.json — start a session with 'claude' once on the host" >&2; exit 1; }

TASK_IMG="programbench/$(echo "$TASK" | sed 's/__/_1776_/g'):task_cleanroom"
docker pull "$TASK_IMG"

MODEL="${CLAUDE_MODEL:-claude-opus-4-7}"
EFFORT="${CLAUDE_EFFORT:-max}"
MAX_TURNS="${CLAUDE_MAX_TURNS:-1000}"
STRICT_NETWORK="${STRICT_NETWORK:-1}"

DOCKER_FLAGS=()
[ "$STRICT_NETWORK" = "1" ] && DOCKER_FLAGS+=(--cap-add=NET_ADMIN)

CONTAINER_NAME="cc-$(echo "${TASK}-$$" | tr '/:.' '___')"

echo "[run] task=${TASK} model=${MODEL} effort=${EFFORT} max-turns=${MAX_TURNS} strict-network=${STRICT_NETWORK}"

docker run --rm \
    "${DOCKER_FLAGS[@]}" \
    --name "$CONTAINER_NAME" \
    -v "${CLAUDE_PKG}:/opt/claude-code:ro" \
    -v "${DOCTRINE}:/work/CLAUDE.md:ro" \
    -v "${HOME}/.claude:/home/agent/.claude:rw" \
    -v "${HOME}/.claude.json:/home/agent/.claude.json:rw" \
    -v "${OUTPUT_DIR}:/out:rw" \
    -e STRICT_NETWORK="$STRICT_NETWORK" \
    -e CLAUDE_MODEL="$MODEL" \
    -e CLAUDE_EFFORT="$EFFORT" \
    -e CLAUDE_MAX_TURNS="$MAX_TURNS" \
    --workdir /work \
    --entrypoint /bin/bash \
    "$TASK_IMG" \
    -c '
        set -o pipefail
        if [ "$STRICT_NETWORK" = "1" ]; then
            if ! command -v iptables >/dev/null 2>&1; then
                apt-get update -qq 2>/dev/null && \
                    apt-get install -y -qq --no-install-recommends iptables 2>/dev/null \
                    || { echo "[warn] iptables install failed; continuing with open network" >&2; STRICT_NETWORK=0; }
            fi
            if [ "$STRICT_NETWORK" = "1" ]; then
                IPS=$(getent ahostsv4 api.anthropic.com 2>/dev/null | awk "/STREAM/{print \$1}" | sort -u)
                if [ -n "$IPS" ]; then
                    iptables -P OUTPUT DROP
                    iptables -A OUTPUT -o lo -j ACCEPT
                    iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
                    iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
                    for ip in $IPS; do
                        iptables -A OUTPUT -p tcp -d "$ip" --dport 443 -j ACCEPT
                    done
                    echo "[sandbox] egress allowlist active: api.anthropic.com -> $IPS"
                else
                    echo "[warn] could not resolve api.anthropic.com; continuing with open network" >&2
                fi
            fi
        fi

        id agent >/dev/null 2>&1 || useradd -m -u 1000 -d /home/agent -s /bin/bash agent
        chown agent /work
        chown -R agent /out
        chmod 1777 /work

        su agent -s /bin/bash -c "
            cd /work
            HOME=/home/agent /opt/claude-code/bin/claude.exe \
                -p \"Read /work/CLAUDE.md and follow it strictly. Ultrathink before every major decision.\" \
                --model \"$CLAUDE_MODEL\" \
                --effort \"$CLAUDE_EFFORT\" \
                --max-turns \"$CLAUDE_MAX_TURNS\" \
                --permission-mode bypassPermissions \
                --output-format stream-json \
                --verbose
        " > /out/trajectory.jsonl 2> /out/run.log \
            || echo "[warn] claude exited $?" >> /out/run.log

        tar -czf /out/submission.tar.gz -C /work \
            --exclude="./CLAUDE.md" --exclude="./executable" .
    '

echo "[done] ${OUTPUT_DIR}/{trajectory.jsonl,submission.tar.gz,run.log}"
