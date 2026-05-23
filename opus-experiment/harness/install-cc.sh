#!/usr/bin/env bash
# ============================================================================
# install-cc.sh
# ----------------------------------------------------------------------------
# One-time host setup for the container-CC harness on a Hetzner Ubuntu box.
#
# Architecture: CC runs INSIDE each task container with an iptables egress
# allowlist permitting only the Parsewave proxy. The host's job is just to:
#   1. Ensure `docker` is installed and the daemon is reachable.
#   2. Install Parsewave's `launchpad` as the non-root `agent` user (which
#      sets up `claud` on PATH and writes the OAuth token to ~/.claude-custom).
#   3. Verify `launchpad doctor claud` passes (i.e., the proxy is healthy).
#   4. Pre-pull the 5 smoke-test task images so the first run isn't waiting
#      on a download.
#
# Idempotent -- safe to re-run.
#
# Run as root (the script will sudo where needed and `su - agent` for the
# launchpad install).
# ============================================================================
set -euo pipefail

log() { printf '[install-cc] %s\n' "$*"; }

AGENT_USER="${AGENT_USER:-agent}"
PROXY_HOST="<REDACTED_PROXY_IP_1>"
PROXY_PORT="8080"

SMOKE_IMAGES=(
  "programbench/mgdm_1776_htmlq.6e31bc8:task"
  "programbench/chmln_1776_sd.87d1ba5:task"
  "programbench/pemistahl_1776_grex.fa3e8ed:task"
  "programbench/bootandy_1776_dust.62bf1e1:task"
  "programbench/nikoladucak_1776_caps-log.2cf2d1e:task"
)

# ---- root check ------------------------------------------------------------
if [[ "$(id -u)" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    log "FATAL: must run as root (no sudo found)"
    exit 1
  fi
else
  SUDO=""
fi

# Run a command as $AGENT_USER. The earlier pattern of `$SUDO -u $AGENT_USER`
# breaks silently when $SUDO is empty (i.e. invoked as root): bash sees `-u`
# as a command name. Use this helper instead.
run_as_agent() {
  if [[ "$(id -u)" -eq 0 ]]; then
    su - "$AGENT_USER" -c "$*"
  else
    sudo -u "$AGENT_USER" bash -lc "$*"
  fi
}

# ---- 1. ensure docker ------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "installing docker..."
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq docker.io
  $SUDO systemctl enable --now docker
else
  log "docker present: $(docker --version)"
fi

if ! $SUDO docker info >/dev/null 2>&1; then
  log "FATAL: docker daemon not reachable"
  exit 1
fi

# ---- 2. ensure agent user (BEFORE docker-group add so the check works) ----
if ! id "$AGENT_USER" >/dev/null 2>&1; then
  log "creating ${AGENT_USER} user"
  $SUDO useradd -m -s /bin/bash "$AGENT_USER"
fi
AGENT_HOME="$(getent passwd "$AGENT_USER" | cut -d: -f6)"
log "agent user: ${AGENT_USER}  home: ${AGENT_HOME}"

# Make sure the agent user can talk to docker (needs to be in `docker` group
# if run_batch.sh / run_task.sh are invoked as agent rather than root).
if ! id -nG "$AGENT_USER" | grep -qw docker; then
  log "adding ${AGENT_USER} to docker group"
  $SUDO usermod -aG docker "$AGENT_USER"
  log "NOTE: ${AGENT_USER} must log out and back in for docker group membership to apply"
fi

# ---- 2.5. install Node.js + @anthropic-ai/claude-code ---------------------
# container_entrypoint.sh bind-mounts /usr/bin/node and
# /usr/lib/node_modules/@anthropic-ai/ into each task container, then
# symlinks `claude` into /usr/local/bin so launchpad's `claud` wrapper can
# exec it. Without these, every container exits at the "wired claude" step.
if ! command -v node >/dev/null 2>&1; then
  log "installing Node.js 20.x..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO bash - >/dev/null 2>&1
  $SUDO apt-get install -y -qq nodejs
fi
log "node: $(node --version)"

if [[ ! -f /usr/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe ]]; then
  log "installing @anthropic-ai/claude-code globally..."
  $SUDO npm install -g @anthropic-ai/claude-code 2>&1 | tail -3
fi
log "claude-code: $(ls /usr/lib/node_modules/@anthropic-ai/claude-code/bin/ 2>/dev/null | head -1) present"

# ---- 3. install launchpad as agent -----------------------------------------
# launchpad's install script lives at https://<REDACTED_PARSEWAVE_HOST>/launchpad/install.sh
# and bootstraps ~/.local/share/<REDACTED_LAUNCHPAD_NAME>/ + symlinks for `launchpad`
# and `claud` into ~/.local/bin/.
if [[ -d "${AGENT_HOME}/.local/share/<REDACTED_LAUNCHPAD_NAME>" ]] \
   && [[ -x "${AGENT_HOME}/.local/bin/claud" ]] \
   && [[ -x "${AGENT_HOME}/.local/bin/launchpad" ]]; then
  log "launchpad already installed for ${AGENT_USER}"
else
  log "installing launchpad as ${AGENT_USER}..."
  run_as_agent 'set -euo pipefail; curl -fsSL https://<REDACTED_PARSEWAVE_HOST>/launchpad/install.sh | bash'
fi

# ---- 4. token check + doctor -----------------------------------------------
if [[ ! -f "${AGENT_HOME}/.claude-custom" ]]; then
  cat <<EOF

[install-cc] ============================================================
[install-cc] ONE-TIME LOGIN REQUIRED
[install-cc] ============================================================
[install-cc] No ${AGENT_HOME}/.claude-custom found. Run as ${AGENT_USER}:
[install-cc]
[install-cc]     sudo -iu ${AGENT_USER}
[install-cc]     launchpad login
[install-cc]
[install-cc] Then re-run this script to verify and pre-pull images.
[install-cc] ============================================================
EOF
  exit 0
fi

log "running 'launchpad update' as ${AGENT_USER} to cache the prod bundle + CA"
run_as_agent 'launchpad update' >/dev/null 2>&1 || true

log "running 'launchpad doctor claud' as ${AGENT_USER}"
if ! run_as_agent 'launchpad doctor claud'; then
  log "FATAL: launchpad doctor claud failed."
  log "  Try: sudo -iu ${AGENT_USER} launchpad login"
  log "  Or check that the proxy at ${PROXY_HOST}:${PROXY_PORT} is reachable."
  exit 1
fi
log "launchpad doctor claud: PASS"

# ---- 4.5. build ca-bundle.pem for the container entrypoint -----------------
# container_entrypoint.sh requires both mitmproxy-ca.pem AND ca-bundle.pem
# under ~/.local/share/parsewave/. Launchpad only lays down mitmproxy-ca.pem;
# build the combined bundle (system CAs + mitmproxy CA) here so the agent's
# TLS inside the container can verify both regular HTTPS and the proxy.
PARSEWAVE_DIR="${AGENT_HOME}/.local/share/parsewave"
if [[ -f "${PARSEWAVE_DIR}/mitmproxy-ca.pem" && ! -s "${PARSEWAVE_DIR}/ca-bundle.pem" ]]; then
  log "building ca-bundle.pem (system roots + mitmproxy CA)"
  cat /etc/ssl/certs/ca-certificates.crt "${PARSEWAVE_DIR}/mitmproxy-ca.pem" \
    | $SUDO tee "${PARSEWAVE_DIR}/ca-bundle.pem" >/dev/null
  $SUDO chown "${AGENT_USER}:${AGENT_USER}" "${PARSEWAVE_DIR}/ca-bundle.pem"
  $SUDO chmod 0644 "${PARSEWAVE_DIR}/ca-bundle.pem"
  log "  ca-bundle.pem: $(stat -c%s "${PARSEWAVE_DIR}/ca-bundle.pem") bytes"
elif [[ ! -f "${PARSEWAVE_DIR}/mitmproxy-ca.pem" ]]; then
  log "WARN: ${PARSEWAVE_DIR}/mitmproxy-ca.pem missing -- launchpad install didn't lay it down"
fi

# ---- 5. pre-pull smoke images ----------------------------------------------
log "pre-pulling ${#SMOKE_IMAGES[@]} smoke task images..."
for img in "${SMOKE_IMAGES[@]}"; do
  if $SUDO docker image inspect "$img" >/dev/null 2>&1; then
    log "  already present: $img"
  else
    log "  pulling: $img"
    if ! $SUDO docker pull "$img"; then
      log "  WARN: failed to pull $img (may not be in registry; build locally)"
    fi
  fi
done

log "done. Host is ready. Next:"
log "  bash run_batch.sh --smoke"
