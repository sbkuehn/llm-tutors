resource "azurerm_resource_group" "rg" {
  name     = "${var.prefix}-rg"
  location = var.location
}

# ---------------------------------------------------------------------------
# IDENTITIES & SECURITY
# ---------------------------------------------------------------------------

resource "azurerm_user_assigned_identity" "app_identity" {
  name                = "${var.prefix}-app-identity"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_user_assigned_identity" "gh_identity" {
  name                = "${var.prefix}-gh-actions-identity"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_federated_identity_credential" "gh_oidc" {
  name                = "${var.prefix}-gh-federated-cred"
  resource_group_name = azurerm_resource_group.rg.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  parent_id           = azurerm_user_assigned_identity.gh_identity.id
  subject             = "repo:${var.github_organization_and_repo}:ref:refs/heads/main"
}

# ---------------------------------------------------------------------------
# AZURE OPENAI (COGNITIVE ACCOUNT + DEPLOYMENTS)
# ---------------------------------------------------------------------------

resource "azurerm_cognitive_account" "openai" {
  name                = "${var.prefix}-openai"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "OpenAI"
  sku_name            = "S0"
}

# RAI (Responsible AI) policy is now mandatory for some deployments in new regions.
# For simplicity, we use the built-in "default" policy if supported; if it errors,
# you can remove the rai_policy block after the first plan.
resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }

  rai_policy_name = "Default" # if this causes an error, remove this line

  scale {
    type     = "Standard"
    capacity = 10
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = "text-embedding-3-small"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-small"
    version = "1"
  }

  rai_policy_name = "Default" # if this causes an error, remove this line

  scale {
    type     = "Standard"
    capacity = 10
  }
}

# ---------------------------------------------------------------------------
# AZURE AI SEARCH (VECTOR DB)
# ---------------------------------------------------------------------------

resource "azurerm_search_service" "search" {
  name                = "${var.prefix}-search"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "basic"
  semantic_search_sku = "standard"
}

# ---------------------------------------------------------------------------
# HOSTING: ACR & CONTAINER APPS
# ---------------------------------------------------------------------------

resource "azurerm_container_registry" "acr" {
  name                = "${var.prefix}acr"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_log_analytics_workspace" "law" {
  name                = "${var.prefix}-law"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
}

resource "azurerm_container_app_environment" "cae" {
  name                       = "${var.prefix}-env"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
}

resource "azurerm_container_app" "app" {
  name                         = "${var.prefix}-app"
  container_app_environment_id = azurerm_container_app_environment.cae.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app_identity.id]
  }

  template {
    container {
      name   = "chainlit-app"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      cpu    = 0.5
      memory = "1.0Gi"

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.openai.endpoint
      }

      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = "https://${azurerm_search_service.search.name}.search.windows.net"
      }

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.app_identity.client_id
      }
    }

    min_replicas = 0
    max_replicas = 5
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# ---------------------------------------------------------------------------
# ROLE ASSIGNMENTS
# ---------------------------------------------------------------------------

# App runtime -> OpenAI, Search, ACR
resource "azurerm_role_assignment" "app_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

resource "azurerm_role_assignment" "app_search" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

resource "azurerm_role_assignment" "app_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

# GitHub identity -> ACR push + RG contributor
resource "azurerm_role_assignment" "gh_acr_push" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.gh_identity.principal_id
}

resource "azurerm_role_assignment" "gh_rg_contributor" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.gh_identity.principal_id
}
