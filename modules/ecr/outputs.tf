output "nginx_repository_url" {
  description = "URL of the nginx ECR repository"
  value       = aws_ecr_repository.nginx.repository_url
}

output "vulcan_repository_url" {
  description = "URL of the vulcan ECR repository"
  value       = aws_ecr_repository.vulcan.repository_url
}

output "heimdall_repository_url" {
  description = "URL of the heimdall2 ECR repository"
  value       = aws_ecr_repository.heimdall.repository_url
}