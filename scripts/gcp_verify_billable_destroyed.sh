#!/usr/bin/env bash
# Verify GCP teardown: no billable compute left; static IP + Secret Manager preserved.
#
# Usage:
#   ./scripts/gcp_verify_billable_destroyed.sh \
#     --project my-project \
#     --region asia-south1 \
#     --static-ip-name my-static-ip \
#     --secret-id swingbot-balancewheel-env \
#     [--name-prefix balancewheel]
#
# Requires: gcloud CLI authenticated with permission to list compute + secrets.
# Exit 0 = OK. Exit 1 = billable resources remain OR required keepers missing.

set -euo pipefail

PROJECT=""
REGION=""
STATIC_IP_NAME="${STATIC_IP_NAME:-my-static-ip}"
SECRET_ID="${SECRET_ID:-swingbot-balancewheel-env}"
NAME_PREFIX="${NAME_PREFIX:-balancewheel}"

log() { echo "[verify] $*"; }
fail() { echo "[verify] FAIL: $*" >&2; FAILED=1; }

FAILED=0

usage() {
  sed -n '2,12p' "$0"
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --static-ip-name) STATIC_IP_NAME="$2"; shift 2 ;;
    --secret-id) SECRET_ID="$2"; shift 2 ;;
    --name-prefix) NAME_PREFIX="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown arg: $1"; usage ;;
  esac
done

[[ -n "$PROJECT" ]] || { echo "Missing --project"; usage; }
[[ -n "$REGION" ]] || { echo "Missing --region"; usage; }
[[ -n "$STATIC_IP_NAME" ]] || { echo "Missing --static-ip-name"; usage; }
[[ -n "$SECRET_ID" ]] || { echo "Missing --secret-id"; usage; }

if ! command -v gcloud &>/dev/null; then
  echo "gcloud not found" >&2
  exit 1
fi

export CLOUDSDK_CORE_DISABLE_PROMPTS=1
gcloud config set project "$PROJECT" --quiet 2>/dev/null || true

filter_name() {
  local resource="$1"
  gcloud compute "$resource" list --project="$PROJECT" \
    --filter="name~^${NAME_PREFIX}" \
    --format="value(name)" 2>/dev/null || true
}

# --- Billable: must be empty ---
INSTANCES=$(filter_name instances)
if [[ -n "$INSTANCES" ]]; then
  fail "Compute instances still exist: $(echo "$INSTANCES" | tr '\n' ' ')"
else
  log "OK: no matching compute instances"
fi

DISKS=$(filter_name disks)
if [[ -n "$DISKS" ]]; then
  fail "Disks still exist: $(echo "$DISKS" | tr '\n' ' ')"
else
  log "OK: no matching disks"
fi

SNAPSHOTS=$(gcloud compute snapshots list --project="$PROJECT" \
  --filter="name~^${NAME_PREFIX}" --format="value(name)" 2>/dev/null || true)
if [[ -n "$SNAPSHOTS" ]]; then
  fail "Snapshots still exist: $(echo "$SNAPSHOTS" | tr '\n' ' ')"
else
  log "OK: no matching snapshots"
fi

IMAGES=$(gcloud compute images list --project="$PROJECT" \
  --filter="name~^${NAME_PREFIX}" --format="value(name)" 2>/dev/null || true)
if [[ -n "$IMAGES" ]]; then
  fail "Custom images still exist: $(echo "$IMAGES" | tr '\n' ' ')"
else
  log "OK: no matching custom images"
fi

# Optional: forwarding rules / addresses created for LB (not static IP keeper)
FWD=$(gcloud compute forwarding-rules list --project="$PROJECT" \
  --filter="name~^${NAME_PREFIX}" --format="value(name)" 2>/dev/null || true)
if [[ -n "$FWD" ]]; then
  fail "Forwarding rules still exist: $(echo "$FWD" | tr '\n' ' ')"
else
  log "OK: no matching forwarding rules"
fi

# --- Keepers: must exist ---
if gcloud compute addresses describe "$STATIC_IP_NAME" \
    --region="$REGION" --project="$PROJECT" &>/dev/null; then
  ADDR=$(gcloud compute addresses describe "$STATIC_IP_NAME" \
    --region="$REGION" --project="$PROJECT" --format="value(address)")
  log "OK: static IP preserved: $STATIC_IP_NAME ($ADDR)"
else
  fail "Static IP missing (should be kept): $STATIC_IP_NAME in $REGION"
fi

if gcloud secrets describe "$SECRET_ID" --project="$PROJECT" &>/dev/null; then
  log "OK: Secret Manager secret preserved: $SECRET_ID"
else
  fail "Secret missing (should be kept): $SECRET_ID"
fi

echo ""
if [[ "$FAILED" -eq 1 ]]; then
  echo "[verify] RESULT: FAILED — fix items above before considering teardown complete."
  exit 1
fi

echo "[verify] RESULT: PASSED — billable BalanceWheel resources destroyed; secrets and static IP retained."
exit 0
