output "alb_dns_name" {
  description     = "DNS name of the Application Load Balancer"
  value           = module.alb.alb_dns_name
}

output "ecs_cluster_name" {
  description     = "Name of the ECS cluster"
  value           = module.ecs_cluster.cluster_name
}

output "rds_endpoint" {
  description     = "Endpoint of the RDS instance"
  value           = module.rds.rds_endpoint
}