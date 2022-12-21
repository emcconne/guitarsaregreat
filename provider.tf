terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.36.0"
    }
  }
  backend azurerm {
    storage_account_name  = "tfstguitarssa"
    container_name        = "tfstguitars"
    key                   = "terraform.state.main"
  }
}
provider azurerm {
  skip_provider_registration = true
  features {}
}
