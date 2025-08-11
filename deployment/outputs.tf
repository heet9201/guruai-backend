# Terraform Outputs
output "service_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_service.guruai_backend.status[0].url
}

output "load_balancer_ip" {
  description = "IP address of the load balancer"
  value       = google_compute_global_address.default.address
}

output "redis_host" {
  description = "Redis instance host"
  value       = google_redis_instance.cache.host
  sensitive   = true
}

output "service_account_email" {
  description = "Service account email for Cloud Run"
  value       = google_service_account.cloud_run_sa.email
}

output "monitoring_dashboard_url" {
  description = "URL to the monitoring dashboard"
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.guruai_dashboard.id}?project=${var.project_id}"
}
