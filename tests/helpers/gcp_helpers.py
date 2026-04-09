# ABOUTME: GCP helper functions for GKE / Workload Identity / Secret Manager checks.
# ABOUTME: Used by Phase 1 tests and any test that needs to inspect GCP state.

from __future__ import annotations

from typing import Any


def gke_cluster_parent(project_id: str, region: str) -> str:
    """Return the 'projects/.../locations/...' parent string for GKE APIs."""
    return f"projects/{project_id}/locations/{region}"


def gke_cluster_name(project_id: str, region: str, cluster: str) -> str:
    """Return the fully-qualified GKE cluster resource name."""
    return f"{gke_cluster_parent(project_id, region)}/clusters/{cluster}"


def cluster_has_workload_identity(cluster: Any) -> bool:
    """Return True if the GKE cluster has Workload Identity enabled.

    Args:
        cluster: A google.cloud.container_v1.types.Cluster instance.
    """
    wi = getattr(cluster, "workload_identity_config", None)
    if wi is None:
        return False
    return bool(getattr(wi, "workload_pool", ""))


def cluster_has_node_auto_provisioning(cluster: Any) -> bool:
    """Return True if the GKE cluster has node auto-provisioning enabled."""
    autoscaling = getattr(cluster, "autoscaling", None)
    if autoscaling is None:
        return False
    return bool(getattr(autoscaling, "enable_node_autoprovisioning", False))


def cluster_is_standard(cluster: Any) -> bool:
    """Return True if the GKE cluster is Standard (not Autopilot).

    Autopilot clusters set `cluster.autopilot.enabled = True`.
    """
    autopilot = getattr(cluster, "autopilot", None)
    if autopilot is None:
        return True
    return not bool(getattr(autopilot, "enabled", False))


def secret_resource_name(project_id: str, secret_id: str) -> str:
    """Return the fully-qualified Secret Manager secret resource name."""
    return f"projects/{project_id}/secrets/{secret_id}"
