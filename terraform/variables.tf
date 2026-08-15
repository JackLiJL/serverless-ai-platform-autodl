variable "grafana_url" {
  description = "Grafana Cloud Instance URL"
  type        = string
}

variable "grafana_token" {
  description = "Grafana Cloud Service Account Token"
  type        = string
  sensitive   = true
}

variable "prometheus_datasource_uid" {
  description = "Prometheus datasource uid inside Grafa"
  type        = string
}
