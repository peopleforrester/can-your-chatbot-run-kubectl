# ABOUTME: Phase 2 GitOps tests for ArgoCD install and app-of-apps bootstrap.
# ABOUTME: Static manifest checks plus live ArgoCD app sync/health assertions.

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import PROJECT_ROOT


pytestmark = pytest.mark.phase2

GITOPS_DIR = PROJECT_ROOT / "gitops"
BOOTSTRAP_DIR = GITOPS_DIR / "bootstrap"
ARGOCD_DIR = GITOPS_DIR / "argocd"
NAMESPACES_DIR = GITOPS_DIR / "namespaces"


@pytest.mark.static
def test_gitops_tree_exists() -> None:
    assert GITOPS_DIR.is_dir(), "gitops/ is missing"
    assert BOOTSTRAP_DIR.is_dir(), "gitops/bootstrap/ is missing"
    assert ARGOCD_DIR.is_dir(), "gitops/argocd/ is missing"
    assert NAMESPACES_DIR.is_dir(), "gitops/namespaces/ is missing"


@pytest.mark.static
def test_app_of_apps_manifest_valid() -> None:
    """gitops/bootstrap/app-of-apps.yaml is a valid ArgoCD Application."""
    path = BOOTSTRAP_DIR / "app-of-apps.yaml"
    assert path.exists(), "app-of-apps.yaml is missing"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["apiVersion"].startswith("argoproj.io/"), "apiVersion is not argoproj.io"
    assert doc["kind"] == "Application", "kind is not Application"
    assert "spec" in doc and "source" in doc["spec"]


@pytest.mark.static
def test_namespaces_manifest_includes_deinopis_net() -> None:
    """gitops/namespaces/namespaces.yaml creates the deinopis-net namespace."""
    path = NAMESPACES_DIR / "namespaces.yaml"
    assert path.exists(), "namespaces.yaml is missing"
    docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    ns_names = {d["metadata"]["name"] for d in docs if d and d.get("kind") == "Namespace"}
    required = {
        "argocd",
        "monitoring",
        "security",
        "deinopis-net",
        "burritbot-unguarded",
        "burritbot-guarded",
        "audience",
    }
    missing = required - ns_names
    assert not missing, f"Missing namespaces in manifest: {sorted(missing)}"


@pytest.mark.static
def test_sync_wave_annotations_present() -> None:
    """At least one Application declares a sync-wave annotation."""
    count = 0
    for path in (GITOPS_DIR / "apps").rglob("*.yaml") if (GITOPS_DIR / "apps").exists() else []:
        text = Path(path).read_text(encoding="utf-8")
        if "argocd.argoproj.io/sync-wave" in text:
            count += 1
    assert count >= 1, "No sync-wave annotations found in gitops/apps/**"


# --- Live ArgoCD assertions -------------------------------------------------


@pytest.mark.live
def test_argocd_server_running(k8s_core_v1) -> None:
    pods = k8s_core_v1.list_namespaced_pod(
        namespace="argocd",
        label_selector="app.kubernetes.io/name=argocd-server",
    )
    running = [p for p in pods.items if p.status and p.status.phase == "Running"]
    assert running, "No argocd-server pods Running"


@pytest.mark.live
def test_root_app_of_apps_synced(k8s_custom_objects) -> None:
    app = k8s_custom_objects.get_namespaced_custom_object(
        group="argoproj.io",
        version="v1alpha1",
        namespace="argocd",
        plural="applications",
        name="root",
    )
    status = app.get("status", {})
    assert status.get("sync", {}).get("status") == "Synced", f"root app sync status: {status}"
    assert status.get("health", {}).get("status") == "Healthy", f"root app health: {status}"
