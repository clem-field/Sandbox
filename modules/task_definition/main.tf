resource "aws_ecs_task_definition" "task" {
  family                   = "multi-container-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = var.execution_role_arn
  tags = { Name = "ecs-task-def" }

  container_definitions = jsonencode([
    {
      name      = "nginx"
      image     = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.nginx_repo}:latest"
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
          awslogs-group         = var.log_group_name
          awslogs-region        = var.region
          awslogs-stream-prefix = "nginx"
        }
      }
    },
    {
      name      = "vulcan"
      image     = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.vulcan_repo}:latest"
      cpu       = 384
      memory    = 768
      essential = true
      environment = [
        {
          name  = "PORT"
          value = "3000"
        },
        {
          name  = "DB_HOST"
          value = var.rds_endpoint
        },
        {
          name  = "DB_NAME"
          value = var.rds_db_name
        },
        {
          name  = "DB_USER"
          value = var.db_username
        },
        {
          name  = "DB_PASSWORD"
          value = var.db_password
        }
      ]
      secrets = [
        {
          name      = "OKTA_CLIENT_ID"
          valueFrom = var.vulcan_okta_secret_arn
        },
        {
          name      = "OKTA_CLIENT_SECRET"
          valueFrom = var.vulcan_okta_secret_arn
        },
        {
          name      = "OKTA_API_TOKEN"
          valueFrom = var.vulcan_okta_secret_arn
        },
        {
          name      = "ADMIN_PASSWORD"
          valueFrom = var.vulcan_admin_secret_arn
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
          awslogs-group         = var.log_group_name
          awslogs-region        = var.region
          awslogs-stream-prefix = "vulcan"
        }
      }
    },
    {
      name      = "heimdall"
      image     = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.heimdall_repo}:latest"
      cpu       = 384
      memory    = 768
      essential = true
      environment = [
        {
          name  = "PORT"
          value = "3001"
        },
        {
          name  = "DB_HOST"
          value = var.rds_endpoint
        },
        {
          name  = "DB_NAME"
          value = var.rds_db_name
        },
        {
          name  = "DB_USER"
          value = var.db_username
        },
        {
          name  = "DB_PASSWORD"
          value = var.db_password
        }
      ]
      secrets = [
        {
          name      = "OKTA_CLIENT_ID"
          valueFrom = var.heimdall_okta_secret_arn
        },
        {
          name      = "OKTA_CLIENT_SECRET"
          valueFrom = var.heimdall_okta_secret_arn
        },
        {
          name      = "OKTA_API_TOKEN"
          valueFrom = var.heimdall_okta_secret_arn
        },
        {
          name      = "ADMIN_PASSWORD"
          valueFrom = var.heimdall_admin_secret_arn
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
          awslogs-group         = var.log_group_name
          awslogs-region        = var.region
          awslogs-stream-prefix = "heimdall"
        }
      }
    }
  ])
}