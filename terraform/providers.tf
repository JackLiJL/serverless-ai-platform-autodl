terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = ">= 2.9.0"
    }
  }
}

provider "grafana" {
  url  = var.grafana_url
  auth = var.grafana_token
}

module "inference_monitoring" {
  source = "./modules/inference-monitoring"

  grafana_url               = var.grafana_url
  grafana_token             = var.grafana_token
  prometheus_datasource_uid = var.prometheus_datasource_uid
}
