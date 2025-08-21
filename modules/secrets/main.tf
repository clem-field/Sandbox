resource "aws_kms_key" "secrets" {
  description         = "KMS key for Secrets Manager encryption"
  enable_key_rotation = true
  tags = { Name = "risk-sentinel-secrets-key" }
}

resource "aws_kms_alias" "secrets_alias" {
  name          = "alias/risk-sentinel-secrets"
  target_key_id = aws_kms_key.secrets.id
}

resource "aws_secretsmanager_secret" "vulcan_okta" {
  name                    = "vulcan-okta-credentials"
  kms_key_id              = aws_kms_key.secrets.id
  description             = "Okta credentials for Vulcan"
  recovery_window_in_days = 7
  tags = { Name = "vulcan-okta-credentials" }
}

resource "aws_secretsmanager_secret_version" "vulcan_okta" {
  secret_id = aws_secretsmanager_secret.vulcan_okta.id
  secret_string = jsonencode({
    client_id     = var.vulcan_okta_client_id
    client_secret = var.vulcan_okta_client_secret
    api_token     = var.vulcan_okta_api_token
  })
}

resource "aws_secretsmanager_secret" "vulcan_admin" {
  name                    = "vulcan-admin-password"
  kms_key_id              = aws_kms_key.secrets.id
  description             = "Admin password for Vulcan"
  recovery_window_in_days = 7
  tags = { Name = "vulcan-admin-password" }
}

resource "aws_secretsmanager_secret_version" "vulcan_admin" {
  secret_id = aws_secretsmanager_secret.vulcan_admin.id
  secret_string = jsonencode({
    password = var.vulcan_admin_password
  })
}

resource "aws_secretsmanager_secret" "heimdall_okta" {
  name                    = "heimdall-okta-credentials"
  kms_key_id              = aws_kms_key.secrets.id
  description             = "Okta credentials for Heimdall"
  recovery_window_in_days = 7
  tags = { Name = "heimdall-okta-credentials" }
}

resource "aws_secretsmanager_secret_version" "heimdall_okta" {
  secret_id = aws_secretsmanager_secret.heimdall_okta.id
  secret_string = jsonencode({
    client_id     = var.heimdall_okta_client_id
    client_secret = var.heimdall_okta_client_secret
    api_token     = var.heimdall_okta_api_token
  })
}

resource "aws_secretsmanager_secret" "heimdall_admin" {
  name                    = "heimdall-admin-password"
  kms_key_id              = aws_kms_key.secrets.id
  description             = "Admin password for Heimdall"
  recovery_window_in_days = 7
  tags = { Name = "heimdall-admin-password" }
}

resource "aws_secretsmanager_secret_version" "heimdall_admin" {
  secret_id = aws_secretsmanager_secret.heimdall_admin.id
  secret_string = jsonencode({
    password = var.heimdall_admin_password
  })
}