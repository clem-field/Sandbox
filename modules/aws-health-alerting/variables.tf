variable "alert_email" {
  description = "Email address to receive AWS Health alerts (SNS subscription)"
  type        = string
}

variable "services" {
  description = "List of AWS services to monitor for Health events (e.g., EC2, RDS)"
  type        = list(string)
  default     = ["EC2", "RDS", "S3", "LAMBDA"]
}

variable "event_categories" {
  description = "AWS Health event categories to trigger alerts"
  type        = list(string)
  default     = ["issue", "scheduledChange"]
}

variable "region" {
  description = "AWS region to deploy resources in (required for multi-region setup)"
  type        = string
  default     = "us-east-1"
}