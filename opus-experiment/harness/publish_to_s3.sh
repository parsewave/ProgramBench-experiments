#!/usr/bin/env bash
# Upload a completed CC-Opus run to S3.
#   ./publish_to_s3.sh <run_name>
# Reads from /tmp/cc-runs/<run_name>/<task>/<trace>/ and uploads to
#   s3://parsewave-program-bench/traces/<run_name>/<task>/<trace>/
#
# NOTE on the prefix: we deliberately upload directly under traces/ (NOT
# traces/cc-opus/<run_name>/) so that trace-gen/grade_traces.sh's
# `--run-name <X>` mode -- which pulls from s3://.../traces/<X>/ -- works
# unchanged for our runs. The "cc-opus-" prefix is already encoded in
# every RUN_NAME (see run_task.sh's default of cc-opus-<utc-stamp>), so the
# layout is still disambiguated from kimi-k2.6-* runs sharing the same
# parent prefix.

set -euo pipefail

RUN_NAME="${1:?usage: $0 <run_name>}"
LOCAL_DIR="/tmp/cc-runs/$RUN_NAME"
S3_PREFIX="s3://parsewave-program-bench/traces/$RUN_NAME"

[[ -d "$LOCAL_DIR" ]] || { echo "[publish] ERR: $LOCAL_DIR not found"; exit 1; }

# Source AWS creds
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]]; then
  CRED_FILE="$REPO_ROOT/../credentials.yaml"
  if [[ -f "$CRED_FILE" ]]; then
    export AWS_ACCESS_KEY_ID="$(python3 -c "import yaml; print(yaml.safe_load(open('$CRED_FILE'))['aws']['access_key_id'])")"
    export AWS_SECRET_ACCESS_KEY="$(python3 -c "import yaml; print(yaml.safe_load(open('$CRED_FILE'))['aws']['secret_access_key'])")"
    export AWS_DEFAULT_REGION=us-east-1
  fi
fi

echo "[publish] syncing $LOCAL_DIR -> $S3_PREFIX"
aws s3 sync "$LOCAL_DIR" "$S3_PREFIX" \
  --exclude '*.log' \
  --exclude '.log' \
  --only-show-errors

echo "[publish] done"
aws s3 ls "$S3_PREFIX/" 2>/dev/null | head -5
