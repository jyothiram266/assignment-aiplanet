variable "do_token" {
  type        = string
  description = "DigitalOcean API Personal Access Token"
  sensitive   = true
}

variable "spaces_access_id" {
  type        = string
  description = "DigitalOcean Spaces Access Key ID"
  default     = ""
}

variable "spaces_secret_key" {
  type        = string
  description = "DigitalOcean Spaces Secret Access Key"
  default     = ""
  sensitive   = true
}

variable "region" {
  type        = string
  description = "DigitalOcean datacenter region"
  default     = "nyc3"
}

variable "cluster_name" {
  type        = string
  description = "DigitalOcean Kubernetes cluster name"
  default     = "llmops-doks-cluster"
}

variable "k8s_version" {
  type        = string
  description = "Kubernetes version for DOKS"
  default     = "1.34.8-do.3"
}

variable "node_pool_name" {
  type        = string
  description = "Name of worker node pool"
  default     = "worker-pool"
}

variable "node_size" {
  type        = string
  description = "Droplet size for DOKS worker nodes (2 vCPU / 8 GB RAM)"
  default     = "s-2vcpu-8gb-160gb-intel"
}

variable "node_count" {
  type        = number
  description = "Fixed node count matching budget (3 nodes)"
  default     = 3
}

variable "spaces_bucket_name" {
  type        = string
  description = "Spaces S3 bucket name for model artifacts"
  default     = "llmops-model-artifacts-nyc3"
}

variable "container_registry_name" {
  type        = string
  description = "DigitalOcean Container Registry name"
  default     = "jyothiram"
}
