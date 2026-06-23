import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
import pytest


class _FakeStaticFiles:
    """Stand-in for StaticFiles — skips the directory existence check at import time."""
    def __init__(self, *args, **kwargs):
        pass


# These patches must be active when app.py is first imported.
# app.py executes two things at module level that fail without real infrastructure:
#   1. `rag_system = RAGSystem(config)` — needs ChromaDB, embedding model, Anthropic key
#   2. `app.mount("/", StaticFiles(directory="../frontend"))` — directory doesn't exist in CI
_static_patcher = patch("fastapi.staticfiles.StaticFiles", _FakeStaticFiles)
_rag_patcher = patch("rag_system.RAGSystem")
_static_patcher.start()
_mock_rag_class = _rag_patcher.start()

from app import app  # noqa: E402 — must follow the patches above

# Stop the RAGSystem patcher immediately after import.
# app.rag_system already holds the mock instance, so it's unaffected.
# Stopping here restores rag_system.RAGSystem to the real class so that
# test_rag_system.py can import and instantiate it normally.
_rag_patcher.stop()

from fastapi.testclient import TestClient


@pytest.fixture
def mock_rag():
    """
    The module-level rag_system instance from app.py, reset and pre-configured per test.

    Returns the same MagicMock object every time (app only imports once), but
    reset_mock() clears call history so each test starts clean.
    """
    import app as app_module
    instance = app_module.rag_system
    instance.reset_mock()
    instance.session_manager.create_session.return_value = "test-session-123"
    instance.query.return_value = ("Test answer", [])
    instance.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": [],
    }
    return instance


@pytest.fixture
def client(mock_rag):
    """TestClient wrapping the FastAPI app with a fresh mock_rag pre-configured."""
    with TestClient(app) as c:
        yield c
