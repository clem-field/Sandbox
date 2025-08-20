resource "aws_ecr_repository" "nginx" {
  name                 = locals.ecr_nginx_repo
  image_tag_mutability = "MUTABLE"
  tags = { Name = "ecr-nginx" }
}

resource "aws_ecr_repository" "vulcan" {
  name                 = locals.ecr_vulcan_repo
  image_tag_mutability = "MUTABLE"
  tags = { Name = "ecr-vulcan" }
}

resource "aws_ecr_repository" "heimdall" {
  name                 = locals.ecr_heimdall_repo
  image_tag_mutability = "MUTABLE"
  tags = { Name = "ecr-heimdall" }
}