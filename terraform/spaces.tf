resource "digitalocean_spaces_bucket" "model_artifacts" {
  name   = var.spaces_bucket_name
  region = var.region
  acl    = "private"

  versioning {
    enabled = true
  }
}
