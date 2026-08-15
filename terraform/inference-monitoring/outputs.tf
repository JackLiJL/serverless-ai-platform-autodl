output "folder_uid" {
  description = "Inference Service Monitoring Folder UID"
  value       = grafana_folder.inference.uid
}

output "dashboard_uid" {
  description = "Dashboard UID"
  value       = grafana_dashboard.inference_monitoring.uid
}

output "dashboard_url" {
  description = "Dashboard URL"
  value       = "${var.grafana_url}/d/${grafana_dashboard.inference_monitoring.uid}"
}
