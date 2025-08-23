variable "region" {
  default = "us-east-1"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "ecr_nginx_repo" {
  default = "custom-nginx"
}

variable "ecr_vulcan_repo" {
  default = "vulcan"
}

variable "ecr_heimdall_repo" {
  default = "heimdall2"
}

variable "account_id" {
  description = "AWS Account ID for ECR URIs"
  default = 1234567890
  # Set this to your account ID
}

variable "domain_name" {
  description = "Domain name for Route 53"
  default     = "risk-sentinel.info"
}

variable "db_username" {
  description = "RDS admin username"
  default     = "admin"
  sensitive   = true
}

variable "db_password" {
  description = "RDS admin password"
  sensitive   = true
}

variable "vulcan_okta_client_id" {
  description = "Okta client ID for Vulcan"
  sensitive   = true
}

variable "vulcan_okta_client_secret" {
  description = "Okta client secret for Vulcan"
  sensitive   = true
}

variable "vulcan_okta_api_token" {
  description = "Okta API token for Vulcan"
  sensitive   = true
}

variable "vulcan_admin_password" {
  description = "Admin password for Vulcan"
  sensitive   = true
}

variable "heimdall_okta_client_id" {
  description = "Okta client ID for Heimdall"
  sensitive   = true
}

variable "heimdall_okta_client_secret" {
  description = "Okta client secret for Heimdall"
  sensitive   = true
}

variable "heimdall_okta_api_token" {
  description = "Okta API token for Heimdall"
  sensitive   = true
}

variable "heimdall_admin_password" {
  description = "Admin password for Heimdall"
  sensitive   = true
}