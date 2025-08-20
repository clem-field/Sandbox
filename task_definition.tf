resource "aws_ecs_task_definition" "task" {
  family                   = "multi-container-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  tags = { Name = "ecs-task-def" }

  container_definitions = jsonencode([
    {
      name      = "nginx"
      image     = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_nginx_repo}:latest"
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_log_group.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "nginx"
        }
      }
    },
    {
      name      = "vulcan"
      image     = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_vulcan_repo}:latest"
      cpu       = 384
      memory    = 768
      essential = true
      environment = [
        {
          name  = "PORT"
          value = "3000"
        }
      ]
      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_log_group.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "vulcan"
        }
      }
    },
    {
      name      = "heimdall"
      image     = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_heimdall_repo}:latest"
      cpu       = 384
      memory    = 768
      essential = true
      environment = [
        {
          name  = "PORT"
          value = "3001"
        }
      ]
      portMappings = [
        {
          containerPort = 3001
          hostPort      = 3001
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_log_group.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "heimdall"
        }
      }
    }
  ])
}