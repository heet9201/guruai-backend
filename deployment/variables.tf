# Terraform Variables
variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key for authentication"
  type        = string
  sensitive   = true
}

variable "encryption_key" {
  description = "Encryption key for data encryption"
  type        = string
  sensitive   = true
}

variable "pii_encryption_key" {
  description = "PII-specific encryption key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

variable "slack_channel" {
  description = "Slack channel for notifications"
  type        = string
  default     = "#alerts"
}

variable "slack_webhook_url" {
  description = "Slack webhook URL"
  type        = string
  sensitive   = true
}

variable "slack_token" {
  description = "Slack authentication token"
  type        = string
  sensitive   = true
}
