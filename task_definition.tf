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
        },
        {
          name = "HTTPS_PROXY"
          value = ""
        },
        {
          name = "HTTP_PROXY"
          value = ""
        },
        {
          name = "RAILS_SERVE_STATIC_FILES"
          value = "true"
        },
        {
          name = "RAILS_ENV"
          value = "production"
        },
        {
          name = "VULCAN_CONTACT_EMAIL"
          value = "kc8yhe@me.com"
        },
        {
          name = "VULCAN_APP_URL"
          value = "vulcan.risk-sentinel.info"
        },
        {
          name = "VULCAN_ENABLE_LOCAL_LOGIN"
          value = "true"
        },
        {
          name = "VULCAN_ENABLE_EMAIL_CONFIRMATION"
          value = "false"
        },
        {
          name = "VULCAN_SESSION_TIMEOUT"
          value = "60"
        },
        {
          name = "VULCAN_ENABLE_USER_REGISTRATION"
          value = "false"
        },
        {
          name = "ADMINUSER"
          value = var.db_username
        },
        {
          name = "ADMINEMAIL"
          value = "kc8yhe@me.com"
        },
        {
          name = "VULCAN_PROJECT_CREATE_PERMISSION"
          value = "false"
        },
        {
          name = "VULCAN_ENABLE_LDAP"
          value = "false"
        },
        {
          name = "VULCAN_ENABLE_OIDC"
          value = "false"
        },
        {
          name = "VULCAN_OIDC_PROVIDER"
          value = ""
        },
        {
          name = "VULCAN_OIDC_PROMPT"
          value = "login"
        },
        {
          name = "VULCAN_OIDC_ISSUER_URL"
          value = ""
        },
        {
          name = "VULCAN_OIDC_CLIENT_SIGNING_ALG"
          value = "RS256"
        },
        {
          name = "VULCAN_OIDC_PORT"
          value = "443"
        },
        {
          name = "RAILS_LOG_TO_STDOUT"
          value = "true"
        },
        {
          name = "FORCE_SSL"
          value = "true"
        },
        {
          name = "VULCAN_OIDC_SCHEME"
          value = "https"
        },
        {
          name = "VULCAN_OIDC_HOST"
          value = ""
        },
        {
          name = "VULCAN_OIDC_REDIRECT_URI"
          value = ""
        },
        {
          name = "VULCAN_OIDC_AUTHORIZATION_URL"
          value = ""
        },
        {
          name = "VULCAN_OIDC_TOKEN_URL"
          value = ""
        },
        {
          name = "VULCAN_OIDC_USERINFO_URL"
          value = ""
        },
        {
          name = "VULCAN_OIDC_JWKS_URI"
          value = ""
        },
        {
          name = "VULCAN_ENABLE_SMTP"
          value = ""
        },
        {
          name = "VULCAN_SMTP_ADDRESS"
          value = ""
        },
        {
          name = "VULCAN_SMTP_PORT"
          value = ""
        },
        {
          name = "VULCAN_SMTP_DOMAIN"
          value = ""
        },
        {
          name = "VULCAN_SMTP_TLS"
          value = "false"
        },
        {
          name = "VULCAN_SMTP_ENABLE_STARTTLS_AUTO"
          value = "false"
        },
        {
          name = "CIPHER_PASSWORD"
          value = var.db_password
        },
        {
          name = "CIPHER_SALT"
          value = ""
        },
        {
          name = "DATABASE_URL"
          value = module.rds.rds_endpoint
        },
        {
          name = "SECRET_KEY_BASE"
          value = ""
        },
        {
          name = "OKTA_DOMAIN"
          value = ""
        }
        ]
      secrets = [
        {
          name      = "OKTA_CLIENT_ID"
          valueFrom = module.secrets.vulcan_okta_secret_arn
        },
        {
          name      = "OKTA_CLIENT_SECRET"
          valueFrom = module.secrets.vulcan_okta_secret_arn
        },
        {
          name      = "OKTA_API_TOKEN"
          valueFrom = module.secrets.vulcan_okta_secret_arn
        },
        {
          name      = "ADMIN_PASSWORD"
          valueFrom = module.secrets.vulcan_admin_secret_arn
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
      privileged = false
      task_container_assign_public_ip = false
      environment = [
        {
          name  = "PORT"
          value = "3001"
        },
        {
          name = "HTTPS_PROXY"
          value = ""
        },
        {
          name = "CLASSIFICATION_BANNER_TEXT"
          value = "PUT SOMETHING HERE"
        },
        {
          name = "CLASSIFICATION_BANNER_COLOR"
          value = "red"
        },
        {
          name = "NODE_ENV"
          value = "production"
        },
        {
          name = "ADMIN_EMAIL"
          value = "kc8yhe@me.com"
        },
        {
          name = "ADMIN_USES_EXTERNAL_AUTH"
          value = "false"
        },
        {
          name = "LOCAL_LOGIN_DISABLED"
          value = "false"
        },
        {
          name = "REGISTRATION_DISABLED"
          value = "true"
        },
        {
          name = "OKTA_TENANT"
          value = ""
        },
        {
          name = "ONE_SESSION_PER_USER"
          value = "true"
        },
        {
          name = "JWT_EXPIRE_TIME"
          value = "600s"
        },
        {
          name = "MAX_FILE_UPLOAD_SIZE"
          value = "50"
        },
        {
          name = "DATABASE_HOST"
          value = module.rds.rds_endpoint
        },
        {
          name = "DATABASE_PORT"
          value = ""
        },
        {
          name = "DATABASE_USERNAME"
          value = var.db_username
        },
        {
          name = "DATABASE_NAME"
          value = module.rds.rds_db_name
        },
        {
          name = "DATABASE_SSL"
          value = "true"
        },
        {
          name = "DATABASE_SSL_INSECURE"
          value = "false"
        },
        {
          name = "DATABASE_SSL_CA"
          value = "/opt/app-root/src/rds-bundle.pem"
        },
        {
          name = "NODE_EXTRA_CERTS"
          value = "/opt/app-root/src/aws-bundle.pem"
        },
        {
          name = "NGINX_HOST"
          value = ""
        },
        {
          name = "EXTERNAL_URL"
          value = "heimdall.risk-sentinel.info"
        },
        {
          name = "OKTA_ISSUER_URL"
          value = ""
        },
        {
          name = "OKTA_AUTHORIZATION_URL"
          value = ""
        },
        {
          name = "OKTA_TOKEN_URL"
          value = ""
        },
        {
          name = "OKTA_USER_INFO_URL"
          value = ""
        },
        {
          name = "OKTA_USE_HTTPS_PROXY"
          value = "true"
        },
        {
          name = "DATABASE_PASSWORD"
          value = var.db_password
        }
      ]
      secrets = [
        {
          name      = "OKTA_CLIENT_ID"
          valueFrom = module.secrets.heimdall_okta_secret_arn
        },
        {
          name      = "OKTA_CLIENT_SECRET"
          valueFrom = module.secrets.heimdall_okta_secret_arn
        },
        {
          name      = "OKTA_API_TOKEN"
          valueFrom = module.secrets.heimdall_okta_secret_arn
        },
        {
          name      = "ADMIN_PASSWORD"
          valueFrom = module.secrets.heimdall_admin_secret_arn
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