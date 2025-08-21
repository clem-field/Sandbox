output "vulcan_okta_secret_arn" {
  value = aws_secretsmanager_secret.vulcan_okta.arn
}

output "vulcan_admin_secret_arn" {
  value = aws_secretsmanager_secret.vulcan_admin.arn
}

output "heimdall_okta_secret_arn" {
  value = aws_secretsmanager_secret.heimdall_okta.arn
}

output "heimdall_admin_secret_arn" {
  value = aws_secretsmanager_secret.heimdall_admin.arn
}

output "kms_key_arn" {
  value = aws_kms_key.secrets.arn
}