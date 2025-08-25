terraform {
  required_providers {
    aws = {
      source        = "hashicorp/aws"
      version       = "~>6.9.0"
    }
  }
  required_version  = ">= 1.9.8"
}

provider "aws" {
  region    = var.region
  profile   = "default"
}

# Add modules here
module "acm" {
  source          = "./modules/acm"
  domain_name     = var.domain_name
  route53_zone_id = module.route53.zone_id
}

module "alb" {
  source                = "./modules/alb"
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  alb_security_group_id = module.security_groups.alb_sg_id
  certificate_arn       = module.acm.certificate_arn
}

module "ecr" {
  source              = "./modules/ecr"
  nginx_repo_name     = var.ecr_nginx_repo
  vulcan_repo_name    = var.ecr_vulcan_repo
  heimdall_repo_name  = var.ecr_heimdall_repo
}

module "ecs_cluster" {
  source              = "./modules/ecs_cluster"
  cluster_name        = "risk-sentinel-cluster"
}

module "ecs_service" {
  source                  = "./modules/ecs_service"
  cluster_id              = module.ecs_cluster.cluster_id
  task_definition_arn     = module.task_definition.task_definition_arn
  public_subnet_ids       = module.vpc.public_subnet_ids
  ecs_security_group_id   = module.security_groups.ecs_sg_id
  target_group_arn        = module.alb.target_group_arn
}

module "iam" {
  source        = "./modules/iam"
  secrets_arns  = [
    module.secrets.vulcan_okta_secret_arn,
    module.secrets.vulcan_admin_secret_arn,
    module.secrets.heimdall_okta_secret_arn,
    module.secrets.heimdall_admin_secret_arn
  ]
  kms_key_arn   = module.secrets.kms_key_arn
}

module "logs" {
  source = "./modules/logs"
}

module "rds" {
  source                = "./modules/rds"
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  ecs_security_group_id = module.security_groups.ecs_sg_id
  rds_instance_name     = "risk-sentinel-db"
  db_username           = var.db_username
  db_password           = var.db_password
  db_name               = "risksentinel"
}

module "route53" {
  source          = "./modules/route53"
  domain_name     = var.domain_name
  alb_dns_name    = module.alb.alb_dns_name
  alb_zone_id     = module.alb.alb_zone_id
}

module "secrets" {
  source                      = "./modules/secrets"
  vulcan_okta_client_id       = var.vulcan_okta_client_id
  vulcan_okta_client_secret   = var.vulcan_okta_client_secret
  vulcan_okta_api_token       = var.vulcan_okta_api_token
  vulcan_admin_password       = var.vulcan_admin_password
  heimdall_okta_client_id     = var.heimdall_okta_client_id
  heimdall_okta_client_secret = var.heimdall_okta_client_secret
  heimdall_okta_api_token     = var.heimdall_okta_api_token
  heimdall_admin_password     = var.heimdall_admin_password
}

module "security_groups" {
  source = "./modules/security_groups"
  vpc_id = module.vpc.vpc_id
}

module "task_definition" {
  source                    = "./modules/task_definition"
  region                    = var.region
  account_id                = var.account_id
  nginx_repo                = var.ecr_nginx_repo
  vulcan_repo               = var.ecr_vulcan_repo
  heimdall_repo             = var.ecr_heimdall_repo
  log_group_name            = module.logs.log_group_name
  rds_endpoint              = module.rds.rds_endpoint
  rds_db_name               = module.rds.rds_db_name
  db_username               = var.db_username
  db_password               = var.db_password
  vulcan_okta_secret_arn    = module.secrets.vulcan_okta_secret_arn
  vulcan_admin_secret_arn   = module.secrets.vulcan_admin_secret_arn
  heimdall_okta_secret_arn  = module.secrets.heimdall_okta_secret_arn
  heimdall_admin_secret_arn = module.secrets.heimdall_admin_secret_arn
  execution_role_arn        = module.iam.ecs_task_execution_role_arn
}

module "vpc" {
  source    = "./modules/vpc"
  region    = var.region
  vpc_cidr  = var.vpc_cidr
}
