data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "random_id" "suffix" {
  byte_length = 3
}

resource "aws_s3_bucket" "frontend" {
  bucket        = "${var.project_name}-frontend-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend_public_read" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject"]
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role-${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy" "ssm_parameters" {
  name = "${var.project_name}-ssm-parameters"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.openai_key.arn,
          aws_ssm_parameter.anthropic_key.arn,
          aws_ssm_parameter.pinecone_key.arn,
          aws_ssm_parameter.pinecone_index_name.arn,
          aws_ssm_parameter.pinecone_environment.arn,
          aws_ssm_parameter.cors_origins.arn
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-instance-profile-${random_id.suffix.hex}"
  role = aws_iam_role.ec2_role.name
}

resource "aws_security_group" "backend" {
  name        = "${var.project_name}-backend-sg-${random_id.suffix.hex}"
  description = "Allow inbound backend API traffic"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Backend API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ssm_parameter" "openai_key" {
  name  = "/${var.project_name}/OPENAI_API_KEY"
  type  = "SecureString"
  value = var.openai_api_key
}

resource "aws_ssm_parameter" "anthropic_key" {
  name  = "/${var.project_name}/ANTHROPIC_API_KEY"
  type  = "SecureString"
  value = var.anthropic_api_key
}

resource "aws_ssm_parameter" "pinecone_key" {
  name  = "/${var.project_name}/PINECONE_API_KEY"
  type  = "SecureString"
  value = var.pinecone_api_key
}

resource "aws_ssm_parameter" "pinecone_index_name" {
  name  = "/${var.project_name}/PINECONE_INDEX_NAME"
  type  = "String"
  value = var.pinecone_index_name
}

resource "aws_ssm_parameter" "pinecone_environment" {
  name  = "/${var.project_name}/PINECONE_ENVIRONMENT"
  type  = "String"
  value = var.pinecone_environment
}

resource "aws_ssm_parameter" "cors_origins" {
  name = "/${var.project_name}/CORS_ORIGINS"
  type = "String"
  value = join(",", [
    "http://localhost:5173",
    "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
  ])
}

resource "aws_instance" "backend" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.backend.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  associate_public_ip_address = true

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    aws_region              = var.aws_region
    aws_account_id          = data.aws_caller_identity.current.account_id
    ecr_repo_name           = aws_ecr_repository.backend.name
    backend_image_tag       = var.backend_image_tag
    openai_param_name       = aws_ssm_parameter.openai_key.name
    anthropic_param_name    = aws_ssm_parameter.anthropic_key.name
    pinecone_param_name     = aws_ssm_parameter.pinecone_key.name
    pinecone_index_param    = aws_ssm_parameter.pinecone_index_name.name
    pinecone_env_param      = aws_ssm_parameter.pinecone_environment.name
    cors_origins_param_name = aws_ssm_parameter.cors_origins.name
  })

  tags = {
    Name = "${var.project_name}-backend"
  }

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    delete_on_termination = true
  }
}

locals {
  create_cost_alerts = var.enable_cost_guardrails && var.budget_alert_email != ""
}

resource "aws_sns_topic" "billing_alerts" {
  count    = local.create_cost_alerts ? 1 : 0
  provider = aws.us_east_1
  name     = "${var.project_name}-billing-alerts"
}

resource "aws_sns_topic_subscription" "billing_alert_email" {
  count     = local.create_cost_alerts ? 1 : 0
  provider  = aws.us_east_1
  topic_arn = aws_sns_topic.billing_alerts[0].arn
  protocol  = "email"
  endpoint  = var.budget_alert_email
}

resource "aws_cloudwatch_metric_alarm" "monthly_billing_alarm" {
  count    = local.create_cost_alerts ? 1 : 0
  provider = aws.us_east_1

  alarm_name          = "${var.project_name}-estimated-charges"
  alarm_description   = "Alerts when AWS estimated monthly charges exceed threshold"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600
  statistic           = "Maximum"
  threshold           = var.billing_alarm_threshold_usd
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.billing_alerts[0].arn]

  dimensions = {
    Currency = "USD"
  }
}

resource "aws_budgets_budget" "monthly_cost" {
  count        = local.create_cost_alerts ? 1 : 0
  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.budget_alert_threshold_percent
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.budget_alert_threshold_percent
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}
