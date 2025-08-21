variable "vpc_id" {
  description = "VPC ID for RDS"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for RDS"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID of ECS tasks"
  type        = string
}

variable "rds_instance_name" {
  description = "Name of the RDS instance"
  default     = "risk-sentinel-db"
}

variable "db_username" {
  description = "Database admin username"
  default     = "admin"
}

variable "db_password" {
  description = "Database admin password"
  sensitive   = true
}

variable "db_name" {
  description = "Default database name"
  default     = "risksentinel"
}