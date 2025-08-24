resource "aws_ecr_repository" "nginx" {
  name                 = var.nginx_repo_name
  image_tag_mutability = "MUTABLE"
  tags = { Name = var.nginx_repo_name }
}

resource "aws_ecr_repository" "vulcan" {
  name                 = var.vulcan_repo_name
  image_tag_mutability = "MUTABLE"
  tags = { Name = var.vulcan_repo_name }
}

resource "aws_ecr_repository" "heimdall" {
  name                 = var.heimdall_repo_name
  image_tag_mutability = "MUTABLE"
  tags = { Name = var.heimdall_repo_name }
}