output "resource_group_name" {
  value       = azurerm_resource_group.rg.name
  description = "Resource Group Name"
}

output "storage_account_name" {
  value       = azurerm_storage_account.lake.name
  description = "ADLS Gen2 Storage Account Name"
}

output "storage_account_key" {
  value       = azurerm_storage_account.lake.primary_access_key
  sensitive   = true
  description = "Storage Account Primary Access Key"
}

output "eventhub_namespace" {
  value       = azurerm_eventhub_namespace.ehns.name
  description = "Event Hubs Namespace Name"
}

output "eventhub_name" {
  value       = azurerm_eventhub.eh.name
  description = "Event Hub Name"
}

output "eventhub_connection_string" {
  value       = azurerm_eventhub_namespace.ehns.default_primary_connection_string
  sensitive   = true
  description = "Event Hub Namespace Connection String"
}

output "eventhub_topic_connection_string" {
  value       = azurerm_eventhub_authorization_rule.policy.primary_connection_string
  sensitive   = true
  description = "Event Hub Topic Connection String (FraudPolicy)"
}

output "eventhub_bootstrap_server" {
  value       = "${azurerm_eventhub_namespace.ehns.name}.servicebus.windows.net:9093"
  description = "Kafka Bootstrap Server endpoint"
}

output "key_vault_name" {
  value       = azurerm_key_vault.kv.name
  description = "Azure Key Vault Name"
}

output "key_vault_uri" {
  value       = azurerm_key_vault.kv.vault_uri
  description = "Azure Key Vault URI"
}

output "databricks_workspace_name" {
  value       = azurerm_databricks_workspace.dbw.name
  description = "Azure Databricks Workspace Name"
}

output "databricks_workspace_url" {
  value       = "https://${azurerm_databricks_workspace.dbw.workspace_url}"
  description = "Azure Databricks Workspace URL"
}

output "databricks_workspace_id" {
  value       = azurerm_databricks_workspace.dbw.id
  description = "Azure Databricks Workspace Resource ID"
}

output "log_analytics_workspace_name" {
  value       = azurerm_log_analytics_workspace.law.name
  description = "Log Analytics Workspace Name"
}

output "logic_app_name" {
  value       = azurerm_logic_app_workflow.logic_app.name
  description = "Logic App Workflow Name"
}

output "logic_app_id" {
  value       = azurerm_logic_app_workflow.logic_app.id
  description = "Logic App Workflow Resource ID (use Azure Portal or az rest to get trigger callback URL)"
}
