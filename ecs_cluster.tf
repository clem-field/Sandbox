resource "aws_ecs_cluster" "main" {
  name = "mitre-ecs-cluster"
  tags = { Name = "ecs-cluster" }
}