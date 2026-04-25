# ABOUTME: Phase A1 test — every ArgoCD Application path: must resolve to a real dir.
# ABOUTME: Caught only by behavior validation; static "yaml exists" tests would miss this.

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import PROJECT_ROOT


GITOPS_APPS_DIR = PROJECT_ROOT / "gitops" / "apps"


def _load_applications() -> list[tuple[Path, dict]]:
    """Yield (file_path, manifest_dict) for every ArgoCD Application."""
    apps: list[tuple[Path, dict]] = []
    for yaml_file in sorted(GITOPS_APPS_DIR.glob("*.yaml")):
        with yaml_file.open() as fp:
            for doc in yaml.safe_load_all(fp):
                if not doc:
                    continue
                if doc.get("kind") == "Application":
                    apps.append((yaml_file, doc))
    return apps


@pytest.mark.static
@pytest.mark.parametrize(
    "yaml_file,app",
    _load_applications(),
    ids=lambda x: x.name if isinstance(x, Path) else x.get("metadata", {}).get("name", "?"),
)
def test_argocd_application_path_resolves(yaml_file: Path, app: dict) -> None:
    """Every Git-source Application must point to an existing populated dir."""
    source = app["spec"]["source"]

    if "chart" in source:
        # Helm-source apps (e.g. kyverno) target a chart, not a repo path.
        return

    path = source.get("path")
    assert path, f"{yaml_file.name}: spec.source.path is missing"

    target = PROJECT_ROOT / path
    assert target.is_dir(), (
        f"{yaml_file.name}: path '{path}' does not exist at {target}"
    )

    yaml_files = list(target.rglob("*.yaml")) + list(target.rglob("*.yml"))
    assert yaml_files, (
        f"{yaml_file.name}: path '{path}' contains no yaml files"
    )
