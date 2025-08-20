resource "aws_ecr_repository" "nginx" {
  name                 = var.ecr_nginx_repo
  image_tag_mutability = "MUTABLE"
  tags = { Name = "ecr-nginx" }
}

resource "aws_ecr_repository" "vulcan" {
  name                 = var.ecr_vulcan_repo
  image_tag_mutability = "MUTABLE"
  tags = { Name = "ecr-vulcan" }
}

resource "aws_ecr_repository" "heimdall" {
  name                 = var.ecr_heimdall_repo
  image_tag_mutability = "MUTABLE"
  tags = { Name = "ecr-heimdall" }
}