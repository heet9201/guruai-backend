# Google Cloud Run Deployment Configuration

resource "google_cloud_run_service" "guruai_backend" {
  name     = "guruai-backend"
  location = var.region

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"        = "1"
        "autoscaling.knative.dev/maxScale"        = "1000"
        "run.googleapis.com/cpu-throttling"       = "false"
        "run.googleapis.com/execution-environment" = "gen2"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
      }
    }

    spec {
      container_concurrency = 1000
      timeout_seconds      = 300

      containers {
        image = "gcr.io/${var.project_id}/guruai-backend:latest"
        
        resources {
          limits = {
            "cpu"    = "2000m"
            "memory" = "4Gi"
          }
          requests = {
            "cpu"    = "1000m"
            "memory" = "2Gi"
          }
        }

        ports {
          container_port = 8080
        }

        env {
          name  = "FLASK_ENV"
          value = var.environment
        }

        env {
          name  = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret_version.database_url.secret
              key  = "latest"
            }
          }
        }

        env {
          name  = "REDIS_HOST"
          value = google_redis_instance.cache.host
        }

        env {
          name  = "JWT_SECRET_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret_version.jwt_secret.secret
              key  = "latest"
            }
          }
        }

        env {
          name  = "ENCRYPTION_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret_version.encryption_key.secret
              key  = "latest"
            }
          }
        }

        env {
          name  = "PII_ENCRYPTION_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret_version.pii_encryption_key.secret
              key  = "latest"
            }
          }
        }

        env {
          name  = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret_version.openai_api_key.secret
              key  = "latest"
            }
          }
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        # Health check probe
        liveness_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 30
          period_seconds       = 30
          timeout_seconds      = 10
          failure_threshold    = 3
        }

        startup_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 10
          period_seconds       = 10
          timeout_seconds      = 10
          failure_threshold    = 30
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_vpc_access_connector.connector,
    google_redis_instance.cache
  ]
}

# IAM for Cloud Run
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_service.guruai_backend.location
  project  = google_cloud_run_service.guruai_backend.project
  service  = google_cloud_run_service.guruai_backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# VPC Connector for database access
resource "google_vpc_access_connector" "connector" {
  name          = "guruai-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 10
}

# Redis Instance
resource "google_redis_instance" "cache" {
  name           = "guruai-cache"
  tier           = "STANDARD_HA"
  memory_size_gb = 5
  region         = var.region

  authorized_network = google_compute_network.vpc.id
  redis_version      = "REDIS_7_0"

  auth_enabled    = true
  transit_encryption_mode = "SERVER_CLIENT"
}

# Load Balancer with CDN
resource "google_compute_global_address" "default" {
  name = "guruai-lb-ip"
}

resource "google_compute_managed_ssl_certificate" "default" {
  name = "guruai-ssl-cert"

  managed {
    domains = [var.domain_name]
  }
}

resource "google_compute_backend_service" "default" {
  name        = "guruai-backend-service"
  description = "GuruAI Backend Service"
  
  backend {
    group = google_compute_region_network_endpoint_group.cloudrun_neg.id
  }

  port_name   = "http"
  protocol    = "HTTP"
  timeout_sec = 30

  health_checks = [google_compute_health_check.default.id]

  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    signed_url_cache_max_age_sec = 7200
    default_ttl                  = 3600
    max_ttl                      = 86400
    negative_caching             = true
    serve_while_stale            = 86400
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "guruai-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_service.guruai_backend.name
  }
}

resource "google_compute_url_map" "default" {
  name            = "guruai-urlmap"
  default_service = google_compute_backend_service.default.id

  host_rule {
    hosts        = [var.domain_name]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_service.default.id

    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.default.id
    }
  }
}

resource "google_compute_target_https_proxy" "default" {
  name             = "guruai-https-proxy"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
}

resource "google_compute_global_forwarding_rule" "default" {
  name       = "guruai-https-forwarding-rule"
  target     = google_compute_target_https_proxy.default.id
  port_range = "443"
  ip_address = google_compute_global_address.default.address
}

resource "google_compute_health_check" "default" {
  name               = "guruai-health-check"
  check_interval_sec = 30
  timeout_sec        = 10

  http_health_check {
    port         = 8080
    request_path = "/health"
  }
}
