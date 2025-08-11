# Cloud SQL Database Instance
resource "google_sql_database_instance" "guruai_db" {
  name             = "guruai-db-${var.environment}"
  database_version = "POSTGRES_15"
  region          = var.region
  
  settings {
    tier = var.database_tier
    
    disk_type    = "PD_SSD"
    disk_size    = var.database_disk_size
    disk_autoresize = true
    disk_autoresize_limit = 500
    
    backup_configuration {
      enabled                        = var.enable_backup
      start_time                    = "03:00"
      location                      = var.region
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = var.backup_retention_days
        retention_unit   = "COUNT"
      }
      transaction_log_retention_days = 7
    }
    
    maintenance_window {
      day          = 7  # Sunday
      hour         = 4  # 4 AM
      update_track = "stable"
    }
    
    database_flags {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"
    }
    
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"  # Log queries taking more than 1 second
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.guruai_vpc.id
      require_ssl     = true
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }
  
  deletion_protection = true
  
  depends_on = [
    google_service_networking_connection.private_vpc_connection
  ]
}

# Database
resource "google_sql_database" "guruai_database" {
  name     = "guruai"
  instance = google_sql_database_instance.guruai_db.name
}

# Database User
resource "google_sql_user" "guruai_user" {
  name     = "guruai"
  instance = google_sql_database_instance.guruai_db.name
  password = random_password.db_password.result
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store database password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "database-password"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Private Service Networking for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "guruai-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.guruai_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.guruai_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Database monitoring
resource "google_monitoring_alert_policy" "database_cpu" {
  display_name = "Database High CPU Usage"
  combiner     = "OR"
  
  conditions {
    display_name = "Database CPU > 80%"
    
    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.guruai_db.name}\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.8
      duration        = "300s"
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]
  
  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_monitoring_alert_policy" "database_memory" {
  display_name = "Database High Memory Usage"
  combiner     = "OR"
  
  conditions {
    display_name = "Database Memory > 85%"
    
    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.guruai_db.name}\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.85
      duration        = "300s"
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]
}

resource "google_monitoring_alert_policy" "database_connections" {
  display_name = "Database High Connection Count"
  combiner     = "OR"
  
  conditions {
    display_name = "Database Connections > 80% of max"
    
    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.guruai_db.name}\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 80
      duration        = "300s"
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]
}
