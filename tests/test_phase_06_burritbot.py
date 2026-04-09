# ABOUTME: Phase 6 BurritBot application tests — FastAPI app, Vertex AI, K8s manifests.
# ABOUTME: Validates gemini-2.5-flash pin, unguarded/guarded deployment manifests, labels.

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import GEMINI_MODEL, PROJECT_ROOT


pytestmark = pytest.mark.phase6

APP_DIR = PROJECT_ROOT / "apps" / "burritbot"
APP_SOURCE = APP_DIR / "app.py"
APP_DOCKERFILE = APP_DIR / "Dockerfile"
APP_MANIFESTS_DIR = APP_DIR / "k8s"

REQUIRED_MANIFESTS = {
    "deployment-unguarded.yaml",
    "deployment-guarded.yaml",
    "service-unguarded.yaml",
    "service-guarded.yaml",
}


@pytest.mark.static
def test_burritbot_tree_exists() -> None:
    assert APP_DIR.is_dir(), "apps/burritbot/ is missing"
    assert APP_SOURCE.exists(), "apps/burritbot/app.py is missing"
    assert APP_DOCKERFILE.exists(), "apps/burritbot/Dockerfile is missing"
    assert APP_MANIFESTS_DIR.is_dir(), "apps/burritbot/k8s/ is missing"


@pytest.mark.static
def test_burritbot_app_pins_gemini_2_5_flash() -> None:
    """BurritBot app.py pins MODEL_NAME to gemini-2.5-flash (the one GA model)."""
    text = APP_SOURCE.read_text(encoding="utf-8")
    assert GEMINI_MODEL in text, (
        f"app.py does not reference {GEMINI_MODEL}"
    )
    # The two bad pins from the spec draft and from training data:
    assert "gemini-1.5-flash" not in text, (
        "app.py still references gemini-1.5-flash (unsupported)"
    )
    assert "gemini-2.0-flash" not in text, (
        "app.py still references gemini-2.0-flash (deprecated 2026-06-01)"
    )


@pytest.mark.static
def test_burritbot_app_uses_vertex_ai_sdk() -> None:
    """BurritBot app.py imports the Vertex AI SDK (google-cloud-aiplatform)."""
    text = APP_SOURCE.read_text(encoding="utf-8")
    assert "vertexai" in text or "google.cloud.aiplatform" in text, (
        "app.py does not import the Vertex AI SDK"
    )


@pytest.mark.static
def test_burritbot_manifests_present() -> None:
    """The four named BurritBot manifests exist under apps/burritbot/k8s/."""
    present = {p.name for p in APP_MANIFESTS_DIR.glob("*.yaml")}
    missing = REQUIRED_MANIFESTS - present
    assert not missing, f"Missing BurritBot manifests: {sorted(missing)}"


@pytest.mark.static
def test_burritbot_unguarded_deployment_valid() -> None:
    """The unguarded Deployment targets the burritbot-unguarded namespace."""
    path = APP_MANIFESTS_DIR / "deployment-unguarded.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["kind"] == "Deployment", "deployment-unguarded.yaml is not a Deployment"
    assert doc["metadata"]["namespace"] == "burritbot-unguarded", (
        "unguarded deployment is not in the burritbot-unguarded namespace"
    )


@pytest.mark.static
def test_burritbot_guarded_deployment_has_deinopis_labels() -> None:
    """The guarded Deployment carries the full deinopis.io label set."""
    path = APP_MANIFESTS_DIR / "deployment-guarded.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["kind"] == "Deployment", "deployment-guarded.yaml is not a Deployment"
    assert doc["metadata"]["namespace"] == "burritbot-guarded", (
        "guarded deployment is not in the burritbot-guarded namespace"
    )
    labels = doc["metadata"].get("labels", {}) or {}
    required = {
        "deinopis.io/layer",
        "deinopis.io/model-source",
        "deinopis.io/model-hash",
    }
    missing = required - set(labels)
    assert not missing, f"guarded deployment missing deinopis.io labels: {sorted(missing)}"


@pytest.mark.static
def test_burritbot_dockerfile_has_aboutme() -> None:
    """Dockerfile begins with the ABOUTME convention."""
    text = APP_DOCKERFILE.read_text(encoding="utf-8")
    first_lines = text.splitlines()[:4]
    aboutme_count = sum(1 for ln in first_lines if "ABOUTME:" in ln)
    assert aboutme_count >= 2, "Dockerfile missing two ABOUTME lines at top"


# --- Live BurritBot checks --------------------------------------------------


@pytest.mark.live
def test_unguarded_burritbot_running(k8s_core_v1) -> None:
    pods = k8s_core_v1.list_namespaced_pod(
        namespace="burritbot-unguarded",
        label_selector="app.kubernetes.io/name=burritbot",
    )
    running = [p for p in pods.items if p.status and p.status.phase == "Running"]
    assert running, "No unguarded BurritBot pods Running"


@pytest.mark.live
def test_guarded_burritbot_running(k8s_core_v1) -> None:
    pods = k8s_core_v1.list_namespaced_pod(
        namespace="burritbot-guarded",
        label_selector="app.kubernetes.io/name=burritbot",
    )
    running = [p for p in pods.items if p.status and p.status.phase == "Running"]
    assert running, "No guarded BurritBot pods Running"
