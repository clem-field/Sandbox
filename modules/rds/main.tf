resource "aws_db_subnet_group" "rds" {
  name       = "${var.rds_instance_name}-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags = { Name = "${var.rds_instance_name}-subnet-group" }
}

resource "aws_db_instance" "main" {
  identifier              = var.rds_instance_name
  engine                  = "postgres"
  engine_version          = "15.5"
  instance_class          = "db.t3.micro"  # Adjust based on needs
  allocated_storage       = 20
  storage_type            = "gp2"
  username                = var.db_username
  password                = var.db_password
  db_name                 = var.db_name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  db_subnet_group_name    = aws_db_subnet_group.rds.name
  skip_final_snapshot     = true
  publicly_accessible     = false
  multi_az                = false  # Enable for production
  backup_retention_period = 7
  tags = { Name = "${var.rds_instance_name}-db" }
}

resource "aws_security_group" "rds" {
  vpc_id = var.vpc_id
  tags = { Name = "${var.rds_instance_name}-rds-sg" }

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]  # Allow ECS tasks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}