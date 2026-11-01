# Cloudflare R2 backend for persistent Terraform state.
#
# Bucket name and endpoint are NOT secret — keep them in this file.
# Access credentials are supplied via GitHub Secrets:
#   R2_ACCESS_KEY   -> AWS_ACCESS_KEY_ID
#   R2_SECRET_KEY   -> AWS_SECRET_ACCESS_KEY
# No AWS account is required; R2 speaks the S3 API so Terraform's S3
# backend treats R2 credentials as standard S3 access/secret keys.
#
# After editing the values below, run locally once:
#   cd terraform && terraform init -migrate-state
# This moves any existing local state into R2.

terraform {
  backend "s3" {
    bucket                      = "monitoring-terraform"
    key                         = "serverless-ai-platform/terraform.tfstate"
    region                      = "auto"
    endpoint                    = "https://895f68af8d118214b33f446537d86361.r2.cloudflarestorage.com"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    use_path_style              = true
  }
}
