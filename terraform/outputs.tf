output "folder_uid" {
  description = "Inference Service Monitoring Folder UID"
  value       = module.inference_monitoring.folder_uid
}

output "dashboard_url" {
  description = "Dashboard URL"
  value       = module.inference_monitoring.dashboard_url
}
