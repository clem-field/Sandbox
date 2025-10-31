variable "alert_email" {
  description = "Email address to receive AWS Health alerts (SNS subscription)"
  type        = string
}

variable "services" {
  description = "List of AWS services to monitor for Health events"
  type        = list(string)
  default = [
    "ECR",            # Amazon Elastic Container Registry
    "ECS",            # Amazon Elastic Container Service
    "IAM",            # AWS Identity and Access Management
    "CLOUDWATCH",     # Amazon CloudWatch
    "RDS",            # Amazon Relational Database Service
    "ROUTE53",        # Amazon Route 53
    "SECRETSMANAGER", # AWS Secrets Manager
    "ACM",            # AWS Certificate Manager
    "ELBV2",          # Application Load Balancer (ALB) — uses ELBV2 in AWS Health
    "ELB"             # Classic ALB  
  ]
}

variable "event_categories" {
  description = "AWS Health event categories to trigger alerts"
  type        = list(string)
  default     = ["issue", "scheduledChange"]
}

variable "region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}