variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "nginx_repo" {
  type = string
}

variable "vulcan_repo" {
  type = string
}

variable "heimdall_repo" {
  type = string
}

variable "log_group_name" {
  type = string
}

variable "rds_endpoint" {
  type = string
}

variable "rds_db_name" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type = string
  sensitive = true
}

variable "vulcan_okta_secret_arn" {
  type = string
}

variable "vulcan_admin_secret_arn" {
  type = string
}

variable "heimdall_okta_secret_arn" {
  type = string
}

variable "heimdall_admin_secret_arn" {
  type = string
}

variable "execution_role_arn" {
  type = string
}