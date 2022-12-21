locals {
  main_tags = {
    env = "synapse"
  }
  tags = "${merge(local.common_tags, local.main_tags)}"
}

resource "azurerm_storage_account" "storage_acct" {
  name                     = "${local.prefix_minus}${local.environment}lake"
  resource_group_name      = local.resource_group 
  location                 = local.location 
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = "true"
}

resource "azurerm_storage_data_lake_gen2_filesystem" "data_lake_fs" {
  name                    = "${local.prefix}dlfs"
  storage_account_id      = azurerm_storage_account.storage_acct.id
}

resource "azurerm_synapse_workspace" "synapse_ws" {
  name                                 = "${local.prefix}-${local.environment}-ws"
  resource_group_name                  = local.resource_group 
  location                             = local.location 
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.data_lake_fs.id
  sql_administrator_login              = "sqladminuser"
  sql_administrator_login_password     = "H@Sh1CoR3!"

  lifecycle {
    ignore_changes = [
      azure_devops_repo,
    ]
  }
  
  aad_admin {
    login     = "AzureAD Admin"
    object_id = data.azurerm_client_config.current.object_id
    tenant_id = data.azurerm_client_config.current.tenant_id
  }

  identity {
    type = "SystemAssigned"
  } 

  tags = local.tags
}

resource "azurerm_cosmosdb_account" "db" {
  name                = "${local.prefix_minus}cosmos"
  location            = local.location
  resource_group_name = local.resource_group
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  enable_automatic_failover = false 
  enable_free_tier          = true

  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 300
    max_staleness_prefix    = 100000
  }

  geo_location {
    location          = local.location 
    failover_priority = 0
  }
}

resource "azurerm_synapse_spark_pool" "spark" {
  name                 = "${local.prefix_minus}sk"
  synapse_workspace_id = azurerm_synapse_workspace.synapse_ws.id
  node_size_family     = "MemoryOptimized"
  node_size            = "Small"

  auto_scale {
    max_node_count = 3
    min_node_count = 3
  }

  auto_pause {
    delay_in_minutes = 15
  }

  tags = local.tags
}

resource "azurerm_synapse_firewall_rule" "allow" {
  name                 = "AllowAll"
  synapse_workspace_id = azurerm_synapse_workspace.synapse_ws.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "255.255.255.255"
}

resource "azurerm_synapse_firewall_rule" "allowall" {
  name                 = "AllowAllWindowsAzureIps"
  synapse_workspace_id = azurerm_synapse_workspace.synapse_ws.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "0.0.0.0"
}

resource "azurerm_synapse_firewall_rule" "home" {
  name                 = "Home"
  synapse_workspace_id = azurerm_synapse_workspace.synapse_ws.id
  start_ip_address     = "24.91.87.90"
  end_ip_address       = "24.91.87.90"
}

resource "azurerm_synapse_role_assignment" "example" {
  synapse_workspace_id = azurerm_synapse_workspace.synapse.id
  role_name            = "Synapse SQL Administrator"
  principal_id         = data.azurerm_client_config.current.object_id

  depends_on           = [azurerm_synapse_firewall_rule.allowall, azurerm_synapse_firewall_rule.allowall,azurerm_synapse_firewall_rule.home]
}

# resource "azurerm_synapse_sql_pool" "example" {
#   name                 = "${local.prefix}_sql"
#   synapse_workspace_id = azurerm_synapse_workspace.synapse_ws.id
#   sku_name             = "DW100c"
#   create_mode          = "Default"
# }
