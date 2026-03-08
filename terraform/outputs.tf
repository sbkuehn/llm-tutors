output "github_variable_AZURE_CLIENT_ID" {
  value       = azurerm_user_assigned_identity.gh_identity.client_id
  description = "Add this as AZURE_CLIENT_ID in GitHub Repo Variables"
}

output "github_variable_AZURE_TENANT_ID" {
  value       = data.azurerm_client_config.current.tenant_id
  description = "Add this as AZURE_TENANT_ID in GitHub Repo Variables"
}

output "github_variable_AZURE_SUBSCRIPTION_ID" {
  value       = data.azurerm_client_config.current.subscription_id
  description = "Add this as AZURE_SUBSCRIPTION_ID in GitHub Repo Variables"
}

output "github_variable_ACR_NAME" {
  value       = azurerm_container_registry.acr.name
  description = "Add this as ACR_NAME in GitHub Repo Variables"
}

output "github_variable_CONTAINER_APP_NAME" {
  value       = azurerm_container_app.app.name
  description = "Add this as CONTAINER_APP_NAME in GitHub Repo Variables"
}

output "github_variable_RESOURCE_GROUP" {
  value       = azurerm_resource_group.rg.name
  description = "Add this as RESOURCE_GROUP in GitHub Repo Variables"
}

output "app_url" {
  value       = "https://${azurerm_container_app.app.latest_revision_fqdn}"
  description = "The public URL where your Azure Tutor will live"
}
