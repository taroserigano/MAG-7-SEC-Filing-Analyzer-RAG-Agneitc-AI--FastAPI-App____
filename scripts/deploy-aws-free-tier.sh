#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT_DIR/infra/aws-free-tier"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-mag7}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.micro}"
IMAGE_TAG="latest"
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

required_cmds=(aws docker npm)
for cmd in "${required_cmds[@]}"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd"
    exit 1
  fi
done

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "Missing backend/.env. Create it first (you can copy backend/.env.example)."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$BACKEND_DIR/.env"
set +a

if [ -z "${OPENAI_API_KEY:-}" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
  echo "OPENAI_API_KEY is missing or placeholder in backend/.env"
  exit 1
fi

if [ -z "${PINECONE_API_KEY:-}" ] || [ "$PINECONE_API_KEY" = "your_pinecone_api_key_here" ]; then
  echo "PINECONE_API_KEY is missing or placeholder in backend/.env"
  exit 1
fi

PINECONE_INDEX_NAME="${PINECONE_INDEX_NAME:-mag7-sec-filings}"
PINECONE_ENVIRONMENT="${PINECONE_ENVIRONMENT:-us-west1-gcp}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

echo "==> Terraform init/apply"
pushd "$TF_DIR" >/dev/null
"$TERRAFORM_BIN" init
"$TERRAFORM_BIN" apply -auto-approve \
  -var="aws_region=$AWS_REGION" \
  -var="project_name=$PROJECT_NAME" \
  -var="instance_type=$INSTANCE_TYPE" \
  -var="backend_image_tag=$IMAGE_TAG" \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="anthropic_api_key=$ANTHROPIC_API_KEY" \
  -var="pinecone_api_key=$PINECONE_API_KEY" \
  -var="pinecone_index_name=$PINECONE_INDEX_NAME" \
  -var="pinecone_environment=$PINECONE_ENVIRONMENT" \
  -var="enable_cost_guardrails=$ENABLE_COST_GUARDRAILS" \
  -var="budget_alert_email=$BUDGET_ALERT_EMAIL" \
  -var="monthly_budget_limit_usd=$MONTHLY_BUDGET_LIMIT_USD" \
  -var="budget_alert_threshold_percent=$BUDGET_ALERT_THRESHOLD_PERCENT" \
  -var="billing_alarm_threshold_usd=$BILLING_ALARM_THRESHOLD_USD"

ECR_REPO_URL="$("$TERRAFORM_BIN" output -raw ecr_repository_url)"
BACKEND_API_URL="$("$TERRAFORM_BIN" output -raw backend_api_url)"
FRONTEND_BUCKET="$("$TERRAFORM_BIN" output -raw frontend_bucket_name)"
FRONTEND_WEBSITE_URL="$("$TERRAFORM_BIN" output -raw frontend_website_url)"
BACKEND_INSTANCE_ID="$("$TERRAFORM_BIN" output -raw backend_instance_id)"
popd >/dev/null

echo "==> Build and push backend image to ECR"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$(echo "$ECR_REPO_URL" | cut -d'/' -f1)"
docker build -t "$ECR_REPO_URL:$IMAGE_TAG" "$BACKEND_DIR"
docker push "$ECR_REPO_URL:$IMAGE_TAG"

echo "==> Wait for SSM and restart backend service"
SSM_READY=0
for attempt in {1..30}; do
  if aws ssm describe-instance-information \
    --region "$AWS_REGION" \
    --filters "Key=InstanceIds,Values=$BACKEND_INSTANCE_ID" \
    --query 'InstanceInformationList[0].InstanceId' \
    --output text 2>/dev/null | grep -q "$BACKEND_INSTANCE_ID"; then
    SSM_READY=1
    break
  fi
  sleep 10
done

if [ "$SSM_READY" -eq 1 ]; then
  COMMAND_ID="$(aws ssm send-command \
    --region "$AWS_REGION" \
    --instance-ids "$BACKEND_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --comment "Restart MAG7 backend" \
    --parameters commands='sudo systemctl restart mag7-backend.service' \
    --query 'Command.CommandId' \
    --output text)"

  aws ssm wait command-executed \
    --region "$AWS_REGION" \
    --command-id "$COMMAND_ID" \
    --instance-id "$BACKEND_INSTANCE_ID" || true
else
  echo "SSM did not become ready in time. Backend will continue retrying image pulls in background."
fi

echo "==> Build frontend with EC2 backend URL"
pushd "$FRONTEND_DIR" >/dev/null
npm install
VITE_API_BASE_URL="$BACKEND_API_URL" npm run build
popd >/dev/null

echo "==> Upload frontend to S3 website bucket"
aws s3 sync "$FRONTEND_DIR/dist" "s3://$FRONTEND_BUCKET" --delete

echo ""
echo "Deployment complete"
echo "Frontend: $FRONTEND_WEBSITE_URL"
echo "Backend : $BACKEND_API_URL"
