# ABOUTME: Wrapper functions for kubectl operations with progress output.
# ABOUTME: Provides typed helpers for common kubectl commands used in tests.

from __future__ import annotations

import re
import shutil
import subprocess
import sys


def kubectl_available() -> bool:
    """Return True if kubectl is on PATH."""
    return shutil.which("kubectl") is not None


def strip_kubectl_noise(stdout: str) -> str:
    """Remove trailing 'pod "xxx" deleted' line from `kubectl run --rm` output."""
    return re.sub(r'pod "[\w-]+" deleted\s*$', "", stdout).strip()


def run_kubectl(
    args: list[str],
    namespace: str | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    """Run a kubectl command and print what is being executed.

    Args:
        args: kubectl subcommand and arguments (e.g. ["get", "pods"]).
        namespace: Kubernetes namespace to target. Omit for cluster-scoped.
        timeout: Command timeout in seconds.

    Returns:
        CompletedProcess with stdout/stderr captured as text.

    Raises:
        RuntimeError: If kubectl is not available on PATH.
        subprocess.TimeoutExpired: If the command exceeds the timeout.
        subprocess.CalledProcessError: If kubectl returns a non-zero exit code.
    """
    if not kubectl_available():
        raise RuntimeError("kubectl is not installed on PATH")

    cmd = ["kubectl", *args]
    if namespace:
        cmd.extend(["-n", namespace])

    print(f"[kubectl] Running: {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )


def get_pods(
    namespace: str,
    label_selector: str | None = None,
) -> list[dict[str, str]]:
    """Get pods in a namespace, returning name and status phase.

    Args:
        namespace: Kubernetes namespace.
        label_selector: Optional label selector (e.g. "app=argocd-server").

    Returns:
        List of dicts with "name" and "phase" keys.
    """
    args = [
        "get",
        "pods",
        "-o",
        "jsonpath={range .items[*]}{.metadata.name}|{.status.phase}\\n{end}",
    ]
    if label_selector:
        args.extend(["-l", label_selector])

    result = run_kubectl(args, namespace=namespace)
    pods: list[dict[str, str]] = []
    for line in result.stdout.strip().split("\n"):
        if "|" in line:
            name, phase = line.split("|", 1)
            pods.append({"name": name, "phase": phase})
    return pods


def apply_manifest(path: str, namespace: str | None = None) -> str:
    """Apply a Kubernetes manifest file and return stdout."""
    args = ["apply", "-f", path]
    return run_kubectl(args, namespace=namespace).stdout


def delete_manifest(
    path: str,
    namespace: str | None = None,
    ignore_not_found: bool = True,
) -> str:
    """Delete a Kubernetes manifest file and return stdout."""
    args = ["delete", "-f", path]
    if ignore_not_found:
        args.append("--ignore-not-found")
    return run_kubectl(args, namespace=namespace).stdout
