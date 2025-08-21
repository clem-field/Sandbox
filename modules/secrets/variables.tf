variable "vulcan_okta_client_id" {
  description = "Okta client ID for Vulcan"
  sensitive   = true
}

variable "vulcan_okta_client_secret" {
  description = "Okta client secret for Vulcan"
  sensitive   = true
}

variable "vulcan_okta_api_token" {
  description = "Okta API token for Vulcan"
  sensitive   = true
}

variable "vulcan_admin_password" {
  description = "Admin password for Vulcan"
  sensitive   = true
}

variable "heimdall_okta_client_id" {
  description = "Okta client ID for Heimdall"
  sensitive   = true
}

variable "heimdall_okta_client_secret" {
  description = "Okta client secret for Heimdall"
  sensitive   = true
}

variable "heimdall_okta_api_token" {
  description = "Okta API token for Heimdall"
  sensitive   = true
}

variable "heimdall_admin_password" {
  description = "Admin password for Heimdall"
  sensitive   = true
}