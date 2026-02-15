variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for AWS resource names"
  type        = string
  default     = "mag7"
}

variable "instance_type" {
  description = "EC2 instance type (t3.micro is commonly free-tier eligible in many accounts/regions)"
  type        = string
  default     = "t3.micro"
}

variable "backend_image_tag" {
  description = "Container image tag that EC2 will pull from ECR"
  type        = string
  default     = "latest"
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "pinecone_api_key" {
  description = "Pinecone API key"
  type        = string
  sensitive   = true
}

variable "pinecone_index_name" {
  description = "Pinecone index name"
  type        = string
  default     = "mag7-sec-filings"
}

variable "pinecone_environment" {
  description = "Pinecone environment"
  type        = string
  default     = "us-west1-gcp"
}

variable "enable_cost_guardrails" {
  description = "Enable monthly budget and CloudWatch billing alarms"
  type        = bool
  default     = true
}

variable "budget_alert_email" {
  description = "Email to receive AWS Budget and billing alarm notifications (leave empty to disable email notifications)"
  type        = string
  default     = ""
}

variable "monthly_budget_limit_usd" {
  description = "Monthly cost budget limit in USD"
  type        = number
  default     = 10
}

variable "budget_alert_threshold_percent" {
  description = "Budget threshold percentage for notifications"
  type        = number
  default     = 80
}

variable "billing_alarm_threshold_usd" {
  description = "CloudWatch billing alarm threshold in USD"
  type        = number
  default     = 5
}
