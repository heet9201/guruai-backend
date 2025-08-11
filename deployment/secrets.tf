# Secret Manager for sensitive configuration
resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "jwt-secret-key"
  
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = var.jwt_secret_key
}

resource "google_secret_manager_secret" "encryption_key" {
  secret_id = "encryption-key"
  
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "encryption_key" {
  secret      = google_secret_manager_secret.encryption_key.id
  secret_data = var.encryption_key
}

resource "google_secret_manager_secret" "pii_encryption_key" {
  secret_id = "pii-encryption-key"
  
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "pii_encryption_key" {
  secret      = google_secret_manager_secret.pii_encryption_key.id
  secret_data = var.pii_encryption_key
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"
  
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "openai_api_key" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = var.openai_api_key
}

# IAM for secret access
resource "google_secret_manager_secret_iam_member" "database_url_access" {
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "jwt_secret_access" {
  secret_id = google_secret_manager_secret.jwt_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "encryption_key_access" {
  secret_id = google_secret_manager_secret.encryption_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "pii_encryption_key_access" {
  secret_id = google_secret_manager_secret.pii_encryption_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "openai_api_key_access" {
  secret_id = google_secret_manager_secret.openai_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Service Account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "guruai-cloud-run"
  display_name = "GuruAI Cloud Run Service Account"
  description  = "Service account for GuruAI Cloud Run service"
}

# IAM roles for Cloud Run service account
resource "google_project_iam_member" "cloud_run_sa_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectViewer",
    "roles/storage.objectCreator",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent"
  ])

  role   = each.value
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}
