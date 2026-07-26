output "cluster_id" {
  value       = digitalocean_kubernetes_cluster.doks.id
  description = "DigitalOcean Kubernetes cluster ID"
}

output "cluster_endpoint" {
  value       = digitalocean_kubernetes_cluster.doks.endpoint
  description = "Kubernetes API server endpoint"
}

output "cluster_status" {
  value       = digitalocean_kubernetes_cluster.doks.status
  description = "Kubernetes cluster status"
}

output "spaces_bucket_domain" {
  value       = digitalocean_spaces_bucket.model_artifacts.bucket_domain_name
  description = "Spaces S3 bucket domain endpoint"
}

output "container_registry_server_url" {
  value       = data.digitalocean_container_registry.docr.server_url
  description = "DigitalOcean Container Registry server URL"
}
