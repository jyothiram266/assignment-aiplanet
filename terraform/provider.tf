terraform {
  required_version = ">= 1.3.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.34.0"
    }
  }
}

provider "digitalocean" {
  token             = var.do_token
  spaces_access_id  = var.spaces_access_id != "" ? var.spaces_access_id : null
  spaces_secret_key = var.spaces_secret_key != "" ? var.spaces_secret_key : null
}
