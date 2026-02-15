#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT_DIR/infra/aws-free-tier"
BACKEND_DIR="$ROOT_DIR/backend"

AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-mag7}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.micro}"
ENABLE_COST_GUARDRAILS="${ENABLE_COST_GUARDRAILS:-true}"
BUDGET_ALERT_EMAIL="${BUDGET_ALERT_EMAIL:-}"
MONTHLY_BUDGET_LIMIT_USD="${MONTHLY_BUDGET_LIMIT_USD:-10}"
BUDGET_ALERT_THRESHOLD_PERCENT="${BUDGET_ALERT_THRESHOLD_PERCENT:-80}"
BILLING_ALARM_THRESHOLD_USD="${BILLING_ALARM_THRESHOLD_USD:-5}"

LOCAL_USER="${USER:-${USERNAME:-$(whoami 2>/dev/null || echo taro)}}"

find_terraform() {
  if command -v terraform >/dev/null 2>&1; then
    command -v terraform
    return
  fi

  local candidates=(
    "/c/Users/$LOCAL_USER/Downloads/terraform_1.14.5_windows_amd64/terraform.exe"
    "/c/Users/$LOCAL_USER/bin/terraform.exe"
    "/c/terraform/terraform.exe"
  )

  for candidate in "${candidates[@]}"; do
    if [ -x "$candidate" ] || [ -f "$candidate" ]; then
      echo "$candidate"
      return
    fi
  done

  return 1
}

TERRAFORM_BIN="$(find_terraform || true)"
if [ -z "$TERRAFORM_BIN" ]; then
  echo "Missing required command: terraform (not found on PATH or common Windows locations)"
  exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "Missing backend/.env. Terraform still needs var values to destroy managed SSM params."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$BACKEND_DIR/.env"
set +a

PINECONE_INDEX_NAME="${PINECONE_INDEX_NAME:-mag7-sec-filings}"
PINECONE_ENVIRONMENT="${PINECONE_ENVIRONMENT:-us-west1-gcp}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

pushd "$TF_DIR" >/dev/null
"$TERRAFORM_BIN" destroy -auto-approve \
  -var="aws_region=$AWS_REGION" \
  -var="project_name=$PROJECT_NAME" \
  -var="instance_type=$INSTANCE_TYPE" \
  -var="backend_image_tag=latest" \
  -var="openai_api_key=${OPENAI_API_KEY:-}" \
  -var="anthropic_api_key=$ANTHROPIC_API_KEY" \
  -var="pinecone_api_key=${PINECONE_API_KEY:-}" \
  -var="pinecone_index_name=$PINECONE_INDEX_NAME" \
  -var="pinecone_environment=$PINECONE_ENVIRONMENT" \
  -var="enable_cost_guardrails=$ENABLE_COST_GUARDRAILS" \
  -var="budget_alert_email=$BUDGET_ALERT_EMAIL" \
  -var="monthly_budget_limit_usd=$MONTHLY_BUDGET_LIMIT_USD" \
  -var="budget_alert_threshold_percent=$BUDGET_ALERT_THRESHOLD_PERCENT" \
  -var="billing_alarm_threshold_usd=$BILLING_ALARM_THRESHOLD_USD"
popd >/dev/null

echo "Destroyed AWS free-tier stack resources managed by Terraform."
