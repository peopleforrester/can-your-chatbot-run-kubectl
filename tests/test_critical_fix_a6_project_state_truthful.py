# ABOUTME: Phase A6 test — PROJECT_STATE.md's stated static-test total must equal reality.
# ABOUTME: Drift here violates the state-persistence rule ("never green-wash the scorecard").

from __future__ import annotations

import re
import subprocess
import sys

import pytest

from conftest import PROJECT_ROOT


PROJECT_STATE = PROJECT_ROOT / "PROJECT_STATE.md"
TOTAL_PATTERN = re.compile(r"Total:\s*(\d+)\s*static\s*tests")


def _collected_static_count() -> int:
    """Run pytest --collect-only -m static and parse the count."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", "static"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"(\d+)\s*/\s*\d+\s*tests collected", result.stdout)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s*tests collected", result.stdout)
    assert match, f"could not parse pytest collect output:\n{result.stdout}"
    return int(match.group(1))


@pytest.mark.static
def test_project_state_static_test_count_is_current() -> None:
    """The number stated in PROJECT_STATE.md must match what pytest collects today."""
    text = PROJECT_STATE.read_text()
    match = TOTAL_PATTERN.search(text)
    assert match, "PROJECT_STATE.md has no 'Total: N static tests' line"
    stated = int(match.group(1))
    actual = _collected_static_count()
    assert stated == actual, (
        f"PROJECT_STATE.md says {stated} static tests; pytest collects "
        f"{actual}. Refresh the state file — see "
        f"~/.claude/rules/state-persistence.md (no green-washing)."
    )
