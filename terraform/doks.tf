resource "digitalocean_vpc" "llmops_vpc" {
  name     = "llmops-vpc"
  region   = var.region
  ip_range = "10.132.0.0/16"
}

resource "digitalocean_kubernetes_cluster" "doks" {
  name     = var.cluster_name
  region   = var.region
  version  = var.k8s_version
  vpc_uuid = digitalocean_vpc.llmops_vpc.id

  node_pool {
    name       = var.node_pool_name
    size       = var.node_size
    node_count = var.node_count

    tags = ["llmops", "doks", "production"]
  }

  tags = ["llmops", "doks"]
}
