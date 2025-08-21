terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~>6.9.0"
    }
  }
  required_version = ">= 1.13.0"
}

provider "aws" {
  region = var.region
  profile = "default"
}

# Add modules here
module "rds" {
  source               = "./modules/rds"
  vpc_id               = aws_vpc.main.id
  private_subnet_ids   = [aws_subnet.private1.id, aws_subnet.private2.id]
  ecs_security_group_id = aws_security_group.ecs_sg.id
  rds_instance_name    = "risk-sentinel-db"
  db_username          = var.db_username
  db_password          = var.db_password
  db_name              = "risksentinel"
}

module "secrets" {
  source                    = "./modules/secrets"
  vulcan_okta_client_id     = var.vulcan_okta_client_id
  vulcan_okta_client_secret = var.vulcan_okta_client_secret
  vulcan_okta_api_token     = var.vulcan_okta_api_token
  vulcan_admin_password     = var.vulcan_admin_password
  heimdall_okta_client_id   = var.heimdall_okta_client_id
  heimdall_okta_client_secret = var.heimdall_okta_client_secret
  heimdall_okta_api_token   = var.heimdall_okta_api_token
  heimdall_admin_password   = var.heimdall_admin_password
}