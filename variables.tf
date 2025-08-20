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