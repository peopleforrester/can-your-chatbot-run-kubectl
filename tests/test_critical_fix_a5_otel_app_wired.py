# ABOUTME: Phase A5 test — burritbot FastAPI app must register the OTel auto-instrumentor.
# ABOUTME: Without this call, no spans reach the collector and the comparison dashboard is dead.

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.static
def test_create_app_invokes_fastapi_instrumentor() -> None:
    """create_app() must call FastAPIInstrumentor.instrument_app(app)."""
    sys.path.insert(0, str(__import__("conftest").PROJECT_ROOT / "apps" / "burritbot"))
    try:
        if "app" in sys.modules:
            importlib.reload(sys.modules["app"])
        app_module = importlib.import_module("app")
        fastapi_app = app_module.create_app()
    finally:
        sys.path.pop(0)

    instrumented = getattr(fastapi_app, "_is_instrumented_by_opentelemetry", False)
    assert instrumented, (
        "FastAPIInstrumentor.instrument_app(app) was not called inside "
        "create_app(); without it, no traces will reach the OTel collector"
    )
