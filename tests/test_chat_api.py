# tests/test_chat_api.py
"""Tests for Story 4.1 — Chat Interface Component (Backend API).

Tests verify the POST /api/chat endpoint:
- AC #1-#3: Message submission, storage, and session validation
- AC #6: Chat history persistence across requests

Story 4.1 Acceptance Criteria:
- AC #3: Chat submission includes session_id in request, returns success response
- AC #1: Chat interface (frontend) renders message history and input field
- AC #2: User messages appear in history with role "user" after submission
- AC #5: Chat history persists when switching panels (backend stores messages)
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch

# Import session management and models
from services.session import (
    create_session,
    get_session,
    clear_all_sessions_for_testing,
    sessions,
)
from services.models import ChatRequest
from services.api import app

# Use TestClient for FastAPI testing
from fastapi.testclient import TestClient

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Clear all sessions before and after each test."""
    clear_all_sessions_for_testing()
    yield
    clear_all_sessions_for_testing()


@pytest.fixture
def session_id():
    """Create a test session and return its session_id."""
    session = create_session()
    return session["session_id"]


# ---------------------------------------------------------------------------
# AC #3 — Endpoint validation and request handling
# ---------------------------------------------------------------------------

def test_chat_endpoint_requires_session(session_id):
    """Test POST /api/chat with invalid session returns 400 error."""
    invalid_session_id = "invalid-session-uuid"

    response = client.post(
        "/api/chat",
        json={"session_id": invalid_session_id, "message": "Test message"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "INVALID_SESSION"


def test_chat_endpoint_requires_non_empty_message(session_id):
    """Test POST /api/chat with empty message returns error."""
    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": ""}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "EMPTY_MESSAGE"


def test_chat_endpoint_trims_whitespace(session_id):
    """Test POST /api/chat trims whitespace from message."""
    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "   Test message   "}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["content"] == "Test message"


# ---------------------------------------------------------------------------
# AC #2 — Message storage with role "user"
# ---------------------------------------------------------------------------

def test_chat_endpoint_stores_message_with_user_role(session_id):
    """Test POST /api/chat stores message with role 'user' in session chat history."""
    message_text = "What is the maximum value in column A?"

    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": message_text}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify response contains message details
    message = data["data"]
    assert message["role"] == "user"
    assert message["content"] == message_text
    assert "id" in message
    assert "timestamp" in message

    # Verify message is stored in session chat history
    session = get_session(session_id)
    assert len(session["chat_history"]) == 1
    stored_message = session["chat_history"][0]
    assert stored_message["role"] == "user"
    assert stored_message["content"] == message_text
    assert stored_message["id"] == message["id"]
    assert stored_message["timestamp"] == message["timestamp"]


def test_chat_endpoint_generates_unique_message_ids(session_id):
    """Test POST /api/chat generates unique IDs for each message."""
    messages = ["First message", "Second message", "Third message"]
    ids = set()

    for msg_text in messages:
        response = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": msg_text}
        )

        assert response.status_code == 200
        message_id = response.json()["data"]["id"]
        ids.add(message_id)

    # All IDs should be unique
    assert len(ids) == 3


def test_chat_endpoint_generates_iso_timestamps(session_id):
    """Test POST /api/chat generates valid ISO 8601 timestamps."""
    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Test message"}
    )

    assert response.status_code == 200
    timestamp = response.json()["data"]["timestamp"]

    # Should be ISO 8601 format with Z suffix
    assert timestamp.endswith("Z")
    # Should be parseable as ISO datetime
    datetime.fromisoformat(timestamp.rstrip("Z"))


# ---------------------------------------------------------------------------
# AC #5 — Chat history persistence
# ---------------------------------------------------------------------------

def test_chat_history_persists_across_requests(session_id):
    """Test that chat history persists across multiple POST /api/chat requests."""
    messages = [
        "First question",
        "Second question",
        "Third question"
    ]

    for msg_text in messages:
        response = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": msg_text}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    # Verify all messages are in session history
    session = get_session(session_id)
    assert len(session["chat_history"]) == 3

    for i, msg_text in enumerate(messages):
        assert session["chat_history"][i]["content"] == msg_text
        assert session["chat_history"][i]["role"] == "user"


def test_chat_history_independent_per_session():
    """Test that each session has independent chat history."""
    session1 = create_session()
    session2 = create_session()

    # Send message to session1
    response1 = client.post(
        "/api/chat",
        json={"session_id": session1["session_id"], "message": "Message for session 1"}
    )
    assert response1.status_code == 200

    # Send message to session2
    response2 = client.post(
        "/api/chat",
        json={"session_id": session2["session_id"], "message": "Message for session 2"}
    )
    assert response2.status_code == 200

    # Verify histories are independent
    assert len(session1["chat_history"]) == 1
    assert len(session2["chat_history"]) == 1
    assert session1["chat_history"][0]["content"] == "Message for session 1"
    assert session2["chat_history"][0]["content"] == "Message for session 2"


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

def test_chat_endpoint_handles_long_messages(session_id):
    """Test POST /api/chat handles very long messages."""
    long_message = "X" * 5000

    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": long_message}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["content"] == long_message


def test_chat_endpoint_handles_special_characters(session_id):
    """Test POST /api/chat handles special characters."""
    special_message = 'What is max(voltage)? Also, print "hello" with backslash'

    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": special_message}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["content"] == special_message


def test_chat_endpoint_handles_unicode(session_id):
    """Test POST /api/chat handles unicode characters."""
    unicode_message = "Analysez les données: 日本語 中文 العربية"

    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": unicode_message}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["content"] == unicode_message


def test_chat_endpoint_returns_correct_response_structure(session_id):
    """Test POST /api/chat returns the correct response structure."""
    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Test message"}
    )

    assert response.status_code == 200

    # Verify response structure
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "data" in data

    message = data["data"]
    assert isinstance(message, dict)
    assert "id" in message
    assert "role" in message
    assert "content" in message
    assert "timestamp" in message

    # Verify field types
    assert isinstance(message["id"], str)
    assert message["role"] == "user"
    assert isinstance(message["content"], str)
    assert isinstance(message["timestamp"], str)
