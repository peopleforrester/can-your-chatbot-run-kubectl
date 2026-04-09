# ABOUTME: Secret Manager for Deinopis — placeholder secret shell for Vertex AI quota.
# ABOUTME: Actual values are written out-of-band; Terraform only creates the container.

resource "google_secret_manager_secret" "vertex_ai" {
  secret_id = var.vertex_secret_id

  replication {
    auto {}
  }

  labels = {
    "deinopis-io_layer" = "foundation"
    "deinopis-io_owner" = "burritbot"
  }
}

# Grant the workload SA access to read this secret. The actual version is
# populated via `gcloud secrets versions add` during Phase 1 rehearsal,
# not from Terraform state (keeps real credentials out of state files).
resource "google_secret_manager_secret_iam_member" "workload_can_read_vertex" {
  secret_id = google_secret_manager_secret.vertex_ai.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.workload.email}"
}
