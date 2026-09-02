# ── Data sources ─────────────────────────────────────────────────────────────
data "azurerm_client_config" "current" {}

# Get the AzureDatabricks enterprise app object ID (app ID is fixed across all tenants)
# but the object ID varies per tenant - must look up via service principal
data "azuread_service_principal" "databricks" {
  client_id = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
}

resource "random_string" "suffix" {
  length  = 5
  special = false
  upper   = false
}

locals {
  suffix = random_string.suffix.result
  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ── 1. Resource Group ────────────────────────────────────────────────────────
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# ── 2. ADLS Gen2 Storage Account ─────────────────────────────────────────────
resource "azurerm_storage_account" "lake" {
  name                     = "stfraudlake${local.suffix}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true

  tags = local.tags
}

resource "azurerm_storage_container" "containers" {
  for_each = toset([
    "bronze",
    "silver",
    "gold",
    "checkpoints",
    "unity-catalog-metastore",
    "training-data"
  ])

  name                  = each.key
  storage_account_name  = azurerm_storage_account.lake.name
  container_access_type = "private"
}

# ── 3. Azure Event Hubs (Kafka Compatible) ───────────────────────────────────
resource "azurerm_eventhub_namespace" "ehns" {
  name                = "ehns-frauddetect${local.suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Standard"
  capacity            = 1

  tags = local.tags
}

resource "azurerm_eventhub" "eh" {
  name                = "eh-trade-events"
  namespace_name      = azurerm_eventhub_namespace.ehns.name
  resource_group_name = azurerm_resource_group.rg.name
  partition_count     = var.eventhub_partition_count
  message_retention   = var.eventhub_retention_days
}

resource "azurerm_eventhub_authorization_rule" "policy" {
  name                = "FraudPolicy"
  namespace_name      = azurerm_eventhub_namespace.ehns.name
  eventhub_name       = azurerm_eventhub.eh.name
  resource_group_name = azurerm_resource_group.rg.name
  listen              = true
  send                = true
  manage              = true
}

# ── 4. Azure Key Vault (RBAC Mode) ───────────────────────────────────────────
resource "azurerm_key_vault" "kv" {
  name                       = "kv-fraud${local.suffix}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization = true
  purge_protection_enabled   = false

  tags = local.tags
}

# Assign Key Vault Administrator to deploying user
resource "azurerm_role_assignment" "kv_admin" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Assign Key Vault Secrets User to Microsoft AzureDatabricks enterprise app
resource "azurerm_role_assignment" "databricks_kv_user" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = data.azuread_service_principal.databricks.object_id
}

# Key Vault Secrets
resource "azurerm_key_vault_secret" "eh_conn_string" {
  name         = "eventhub-conn-string"
  value        = azurerm_eventhub_namespace.ehns.default_primary_connection_string
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "eh_topic_conn_string" {
  name         = "eventhub-topic-conn-string"
  value        = azurerm_eventhub_authorization_rule.policy.primary_connection_string
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "eh_namespace_name" {
  name         = "eventhub-namespace"
  value        = azurerm_eventhub_namespace.ehns.name
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "eh_name" {
  name         = "eventhub-name"
  value        = azurerm_eventhub.eh.name
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "storage_account_name" {
  name         = "storage-account-name"
  value        = azurerm_storage_account.lake.name
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "storage_account_key" {
  name         = "storage-account-key"
  value        = azurerm_storage_account.lake.primary_access_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "cmc_api_key" {
  name         = "cmc-api-key"
  value        = "public-coingecko-fallback"
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

# ── 5. Databricks Access Connector + Storage RBAC ───────────────────────────
resource "azurerm_databricks_access_connector" "connector" {
  name                = "dbw-access-connector3"
  resource_group_name = azurerm_resource_group.rg.name
  location            = "eastus2"  # separate region from eastus to avoid capacity issues

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.connector.identity[0].principal_id
}

# ── 6. Azure Databricks Workspace (Premium) ─────────────────────────────────
resource "azurerm_databricks_workspace" "dbw" {
  name                          = "dbw-frauddetect-final"
  resource_group_name           = azurerm_resource_group.rg.name
  managed_resource_group_name   = "databricks-managed-fraud-final"  # explicit name avoids orphaned RG conflict
  location                      = "eastus2"
  sku                           = "premium"
  public_network_access_enabled = true

  custom_parameters {
    no_public_ip = false
  }

  tags = merge(local.tags, { Environment = "dev" })

  timeouts {
    create = "60m"
    update = "60m"
  }
}



# ── 7. Log Analytics Workspace + Diagnostic Settings ────────────────────────
resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-fraud-detection"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.tags
}

resource "azurerm_monitor_diagnostic_setting" "eh_diag" {
  name                       = "diag-eh-to-law"
  target_resource_id         = azurerm_eventhub_namespace.ehns.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log {
    category = "OperationalLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

# ── 8. Azure Logic App (Fraud Alert Webhook) ─────────────────────────────────
resource "azurerm_logic_app_workflow" "logic_app" {
  name                = "logic-fraud-alerts"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = local.tags
}

resource "azurerm_logic_app_trigger_http_request" "http_trigger" {
  name         = "manual"
  logic_app_id = azurerm_logic_app_workflow.logic_app.id

  schema = jsonencode({
    type = "object"
    properties = {
      order_id   = { type = "string" }
      trader_id  = { type = "string" }
      symbol     = { type = "string" }
      risk_score = { type = "number" }
      decision   = { type = "string" }
      fraud_type = { type = "string" }
      price      = { type = "number" }
      volume     = { type = "number" }
      timestamp  = { type = "string" }
    }
  })
}

resource "azurerm_logic_app_action_custom" "compose_alert" {
  name         = "Compose_Alert"
  logic_app_id = azurerm_logic_app_workflow.logic_app.id

  body = jsonencode({
    type = "Compose"
    inputs = {
      alert       = "FRAUD DETECTED"
      order_id    = "@triggerBody()?['order_id']"
      trader_id   = "@triggerBody()?['trader_id']"
      symbol      = "@triggerBody()?['symbol']"
      risk_score  = "@triggerBody()?['risk_score']"
      fraud_type  = "@triggerBody()?['fraud_type']"
      timestamp   = "@triggerBody()?['timestamp']"
    }
  })
}
