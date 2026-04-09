# ABOUTME: VPC network and subnet for the Deinopis GKE cluster.
# ABOUTME: Private nodes with secondary ranges for pods and services.

resource "google_compute_network" "deinopis" {
  name                            = var.network_name
  auto_create_subnetworks         = false
  routing_mode                    = "REGIONAL"
  delete_default_routes_on_create = false
}

resource "google_compute_subnetwork" "deinopis" {
  name                     = var.subnet_name
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.deinopis.id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }
}

resource "google_compute_router" "deinopis" {
  name    = "${var.network_name}-router"
  network = google_compute_network.deinopis.id
  region  = var.region
}

resource "google_compute_router_nat" "deinopis" {
  name                               = "${var.network_name}-nat"
  router                             = google_compute_router.deinopis.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
