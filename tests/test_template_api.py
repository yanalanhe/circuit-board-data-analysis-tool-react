"""Tests for Template Persistence API endpoints (Story 11.1).

Tests cover:
- GET /api/templates — returns in-memory cache (empty and populated)
- POST /api/templates — success: writes file, updates cache, returns confirmation
- POST /api/templates — invalid session → INVALID_SESSION error
- POST /api/templates — empty name → VALIDATION_ERROR error
- POST /api/templates — in-memory cache updated after save (subsequent GET includes it)
- Startup loading — load_templates() called during startup_event
- AC #7 sandbox security — open() blocked by AST allowlist validator
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import uuid


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from services.api import app
    return TestClient(app)


@pytest.fixture
def mock_session_id():
    """Register a real session and return its ID."""
    from services.session import create_session
    session = create_session()
    return session["session_id"]


@pytest.fixture(autouse=True)
def reset_templates_cache(monkeypatch):
    """Reset _templates cache to empty list before each test to prevent cross-test pollution."""
    import services.api as api_module
    monkeypatch.setattr(api_module, "_templates", [])


# ---------------------------------------------------------------------------
# Task 9.1 — GET /api/templates tests
# ---------------------------------------------------------------------------


def test_list_templates_empty(test_client):
    """GET /api/templates returns success with empty list when cache is empty."""
    response = test_client.get("/api/templates")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "data" in body
    assert body["data"]["templates"] == []


def test_list_templates_returns_cache_contents(test_client, monkeypatch):
    """GET /api/templates returns current in-memory cache contents."""
    import services.api as api_module
    pre_loaded = [
        {"name": "Sales Analysis", "plan": ["Load data", "Plot sales"], "code": "import pandas as pd"},
    ]
    monkeypatch.setattr(api_module, "_templates", list(pre_loaded))

    response = test_client.get("/api/templates")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]["templates"]) == 1
    assert body["data"]["templates"][0]["name"] == "Sales Analysis"
    assert body["data"]["templates"][0]["plan"] == ["Load data", "Plot sales"]


# ---------------------------------------------------------------------------
# Task 9.2 — POST /api/templates success case
# ---------------------------------------------------------------------------


def test_save_template_success(test_client, mock_session_id, tmp_path, monkeypatch):
    """POST /api/templates saves template file and returns saved=True with name."""
    monkeypatch.setattr("utils.templates.TEMPLATES_FILE", str(tmp_path / "templates.json"))

    response = test_client.post("/api/templates", json={
        "session_id": mock_session_id,
        "name": "My Analysis",
        "plan": ["step 1", "step 2"],
        "code": "import pandas as pd\ndf.describe()"
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["saved"] is True
    assert body["data"]["name"] == "My Analysis"


def test_save_template_writes_file(test_client, mock_session_id, tmp_path, monkeypatch):
    """POST /api/templates actually writes templates.json to disk."""
    templates_file = str(tmp_path / "templates.json")
    monkeypatch.setattr("utils.templates.TEMPLATES_FILE", templates_file)

    test_client.post("/api/templates", json={
        "session_id": mock_session_id,
        "name": "Disk Write Test",
        "plan": ["step A"],
        "code": "x = 1"
    })

    assert (tmp_path / "templates.json").exists()
    with open(templates_file, encoding="utf-8") as f:
        saved = json.load(f)
    assert len(saved) == 1
    assert saved[0]["name"] == "Disk Write Test"


def test_save_template_strips_whitespace_from_name(test_client, mock_session_id, tmp_path, monkeypatch):
    """POST /api/templates strips leading/trailing whitespace from template name."""
    monkeypatch.setattr("utils.templates.TEMPLATES_FILE", str(tmp_path / "templates.json"))

    response = test_client.post("/api/templates", json={
        "session_id": mock_session_id,
        "name": "  Padded Name  ",
        "plan": [],
        "code": ""
    })

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["name"] == "Padded Name"


# ---------------------------------------------------------------------------
# Task 9.3 — POST /api/templates — invalid session
# ---------------------------------------------------------------------------


def test_save_template_invalid_session(test_client):
    """POST /api/templates with unknown session_id returns INVALID_SESSION error."""
    response = test_client.post("/api/templates", json={
        "session_id": str(uuid.uuid4()),  # random, not registered
        "name": "Test",
        "plan": [],
        "code": ""
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_SESSION"


# ---------------------------------------------------------------------------
# Task 9.4 — POST /api/templates — empty name
# ---------------------------------------------------------------------------


def test_save_template_empty_name(test_client, mock_session_id):
    """POST /api/templates with empty name returns VALIDATION_ERROR."""
    response = test_client.post("/api/templates", json={
        "session_id": mock_session_id,
        "name": "",
        "plan": ["step 1"],
        "code": "x = 1"
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "empty" in body["error"]["message"].lower()


def test_save_template_whitespace_only_name(test_client, mock_session_id):
    """POST /api/templates with whitespace-only name returns VALIDATION_ERROR."""
    response = test_client.post("/api/templates", json={
        "session_id": mock_session_id,
        "name": "   ",
        "plan": [],
        "code": ""
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# Task 9.5 — In-memory cache updated after save
# ---------------------------------------------------------------------------


def test_save_then_list_includes_new_template(test_client, mock_session_id, tmp_path, monkeypatch):
    """After POST /api/templates, subsequent GET /api/templates includes the new entry."""
    monkeypatch.setattr("utils.templates.TEMPLATES_FILE", str(tmp_path / "templates.json"))

    # Save a template
    post_resp = test_client.post("/api/templates", json={
        "session_id": mock_session_id,
        "name": "Cache Consistency Check",
        "plan": ["step X"],
        "code": "df.head()"
    })
    assert post_resp.json()["status"] == "success"

    # Immediately GET — should include the saved template from cache
    get_resp = test_client.get("/api/templates")
    assert get_resp.status_code == 200
    templates = get_resp.json()["data"]["templates"]
    assert len(templates) == 1
    assert templates[0]["name"] == "Cache Consistency Check"
    assert templates[0]["plan"] == ["step X"]
    assert templates[0]["code"] == "df.head()"


def test_save_multiple_templates_cache_order(test_client, mock_session_id, tmp_path, monkeypatch):
    """Multiple saves append to cache in insertion order."""
    monkeypatch.setattr("utils.templates.TEMPLATES_FILE", str(tmp_path / "templates.json"))

    for name in ["First", "Second", "Third"]:
        test_client.post("/api/templates", json={
            "session_id": mock_session_id,
            "name": name,
            "plan": [],
            "code": ""
        })

    get_resp = test_client.get("/api/templates")
    names = [t["name"] for t in get_resp.json()["data"]["templates"]]
    assert names == ["First", "Second", "Third"]


# ---------------------------------------------------------------------------
# Task 9.6 — Startup loads templates from file
# ---------------------------------------------------------------------------


def test_startup_calls_load_templates(monkeypatch):
    """startup_event() calls load_templates() and extends _templates cache.

    Patch services.api.load_templates (the bound name in the api module) because
    api.py uses `from utils.templates import load_templates` — patching the
    source module has no effect on the already-bound reference.
    """
    import asyncio
    import services.api as api_module

    fake_templates = [{"name": "Loaded on Boot", "plan": ["x"], "code": "y = 1"}]
    # Reset the module-level list in-place (extend the existing list instead of replacing it)
    api_module._templates.clear()
    # Patch the name as bound in services.api, not in utils.templates
    monkeypatch.setattr(api_module, "load_templates", lambda: fake_templates)
    monkeypatch.setattr(api_module, "validate_startup_config", lambda: None)

    asyncio.get_event_loop().run_until_complete(api_module.startup_event())

    assert api_module._templates == fake_templates


def test_startup_handles_empty_templates_file(monkeypatch):
    """startup_event() works correctly when templates.json is absent (load_templates returns [])."""
    import asyncio
    import services.api as api_module

    api_module._templates.clear()
    monkeypatch.setattr(api_module, "load_templates", lambda: [])
    monkeypatch.setattr(api_module, "validate_startup_config", lambda: None)

    asyncio.get_event_loop().run_until_complete(api_module.startup_event())

    assert api_module._templates == []


# ---------------------------------------------------------------------------
# Task 9.7 / Task 8.2 — AC #7 sandbox security: open() blocked by validator
# ---------------------------------------------------------------------------


def test_sandbox_cannot_write_templates_json():
    """open() is in BLOCKED_CALLS — code attempting open('templates.json', 'w') fails validation."""
    from pipeline.nodes.validator import validate_code

    malicious_code = "open('templates.json', 'w').write('hacked')"
    is_valid, errors = validate_code(malicious_code)

    assert is_valid is False
    assert any("open" in err.lower() or "blocked" in err.lower() for err in errors)


def test_sandbox_cannot_write_any_file():
    """open() blocked regardless of target file path."""
    from pipeline.nodes.validator import validate_code

    code = "with open('/etc/passwd', 'r') as f: data = f.read()"
    is_valid, errors = validate_code(code)

    assert is_valid is False


def test_sandbox_open_not_in_allowed_imports():
    """open is blocked at the BLOCKED_CALLS level, not import level (it's a builtin)."""
    from pipeline.nodes.validator import BLOCKED_CALLS

    assert "open" in BLOCKED_CALLS
