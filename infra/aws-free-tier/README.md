# AWS Free-Tier Deploy (EC2 + S3)

This Terraform stack deploys:

- EC2 (`t3.micro` by default) for backend container
- ECR repository for backend image
- S3 static website bucket for frontend build
- IAM + SSM parameters for backend secrets
- Optional cost guardrails (AWS Budget + CloudWatch billing alarm + SNS email)

## Cost notes

- `t3.micro` can be free-tier eligible for qualifying accounts/regions.
- S3 static hosting has a small free-tier allowance, then pay-as-you-go.
- ECR also has limited free allowance.
- OpenAI/Anthropic/Pinecone usage is separate and typically billed by those providers.

## Prerequisites

- AWS CLI authenticated
- Docker installed/running
- Terraform >= 1.6
- Node.js/npm
- `backend/.env` populated with real keys

## One-command deploy

From repo root:

```bash
bash scripts/deploy-aws-free-tier.sh
```

Optional env overrides:

- `AWS_REGION` (default: `us-east-1`)
- `PROJECT_NAME` (default: `mag7`)
- `INSTANCE_TYPE` (default: `t3.micro`)

### Cost guardrails env vars

- `ENABLE_COST_GUARDRAILS` (default: `true`)
- `BUDGET_ALERT_EMAIL` (default: empty; if empty, no email alerts are created)
- `MONTHLY_BUDGET_LIMIT_USD` (default: `10`)
- `BUDGET_ALERT_THRESHOLD_PERCENT` (default: `80`)
- `BILLING_ALARM_THRESHOLD_USD` (default: `5`)

Example:

```bash
export BUDGET_ALERT_EMAIL="you@example.com"
export MONTHLY_BUDGET_LIMIT_USD=8
bash scripts/deploy-aws-free-tier.sh
```

After deploy, confirm the SNS email subscription from your inbox.

## Destroy

```bash
bash scripts/destroy-aws-free-tier.sh
```

## Terraform outputs

After deploy, these outputs are available:

- `backend_api_url`
- `frontend_website_url`
- `ecr_repository_url`
- `backend_instance_id`
- `billing_alert_topic_arn`
- `cost_guardrails_enabled`

## Notes

- Backend service on EC2 pulls image tag `latest` from ECR and restarts via SSM during deploy script.
- Frontend build is generated with `VITE_API_BASE_URL` set to `backend_api_url` and synced to S3.
- Billing alarms use the `AWS/Billing` metric in `us-east-1`.
