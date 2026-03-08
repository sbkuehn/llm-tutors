variable "location" {
  description = "The Azure region to deploy resources"
  type        = string
  default     = "eastus"
}

variable "prefix" {
  description = "A prefix for all resource names"
  type        = string
  default     = "llmtutor"
}

variable "github_organization_and_repo" {
  description = "Your GitHub org and repo for OIDC (e.g., 'username/azure-tutor')"
  type        = string
  default     = "sbkuehn/llm-tutor"
}
