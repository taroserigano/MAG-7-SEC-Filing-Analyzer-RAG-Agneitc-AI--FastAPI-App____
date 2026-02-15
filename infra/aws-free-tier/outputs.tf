output "backend_instance_id" {
  value       = aws_instance.backend.id
  description = "EC2 backend instance id"
}

output "backend_public_ip" {
  value       = aws_instance.backend.public_ip
  description = "Public IP for backend EC2"
}

output "backend_api_url" {
  value       = "http://${aws_instance.backend.public_ip}:8000"
  description = "Backend API URL"
}

output "frontend_bucket_name" {
  value       = aws_s3_bucket.frontend.bucket
  description = "S3 bucket for frontend"
}

output "frontend_website_url" {
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
  description = "S3 static website URL"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.backend.repository_url
  description = "ECR repository URL for backend image"
}

output "billing_alert_topic_arn" {
  value       = try(aws_sns_topic.billing_alerts[0].arn, null)
  description = "SNS topic ARN used for billing alerts (null if guardrails disabled or email not set)"
}

output "cost_guardrails_enabled" {
  value       = local.create_cost_alerts
  description = "Whether budget/alarm email guardrails are currently enabled"
}
