# tests/test_story_4_2.py
"""Tests for Story 4.2 — Intent Classification & Chat Responses (Backend API).

Tests verify the POST /api/chat endpoint with Story 4.2 enhancements:
- Intent classification (report, qa, chat)
- Direct responses for qa and chat intents
- Plan generation for report intents
- Chat history with both user and bot messages

Story 4.2 Acceptance Criteria:
- AC #1: classify_intent node runs on POST /api/chat
- AC #2: Intent classified into "report", "qa", or "chat"
- AC #3: "report" intent returns plan
- AC #4: "qa" intent returns direct response
- AC #5: "chat" intent returns conversational response
- AC #6: Bot message appended to chat_history
"""

import pytest
from unittest.mock import patch, MagicMock

from services.session import (
    create_session,
    clear_all_sessions_for_testing,
)
from services.api import app
from fastapi.testclient import TestClient

client = TestClient(app)


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


class TestIntentClassificationViaAPI:
    """Tests for intent classification through POST /api/chat endpoint."""

    def test_chat_endpoint_runs_intent_classification(self, session_id):
        """AC #1: classify_intent node runs on POST /api/chat."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            # Mock pipeline to return a simple state
            mock_pipeline.return_value = {
                "intent": "chat",
                "response": "Hello there!",
            }

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "hello"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            # Verify pipeline was called
            assert mock_pipeline.called

    def test_chat_endpoint_classifies_report_intent(self, session_id):
        """AC #2 & #3: Intent classified as 'report' and plan returned."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "intent": "report",
                "response": "",
                "plan": [
                    "1. Load voltage and current data",
                    "2. Calculate statistics",
                    "3. Create visualization"
                ],
            }

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "create a chart showing voltage vs time"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["intent"] == "report"
            assert "plan" in data["data"]
            assert len(data["data"]["plan"]) > 0

    def test_chat_endpoint_classifies_qa_intent(self, session_id):
        """AC #2 & #4: Intent classified as 'qa' and direct response returned."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "intent": "qa",
                "response": "The maximum value in column A is 847.3",
                "plan": [],
            }

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "what is the maximum value in column A?"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["intent"] == "qa"
            assert "response" in data["data"]
            assert data["data"]["response"] != ""
            # QA intent should not have plan
            assert "plan" not in data["data"]

    def test_chat_endpoint_classifies_chat_intent(self, session_id):
        """AC #2 & #5: Intent classified as 'chat' and conversational response returned."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "intent": "chat",
                "response": "Hello! I'm here to help with your data analysis.",
                "plan": [],
            }

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "hello"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["intent"] == "chat"
            assert "response" in data["data"]
            assert data["data"]["response"] != ""


class TestChatHistoryWithBotMessages:
    """Tests for AC #6: Bot message appended to chat_history."""

    def test_bot_message_appended_to_chat_history(self, session_id):
        """AC #6: Bot message appended to chat_history with role 'bot'."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "intent": "chat",
                "response": "Hello there!",
                "plan": [],
            }

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "hello"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

            chat_history = data["data"]["chat_history"]
            assert len(chat_history) == 2

            # First message is user
            assert chat_history[0]["role"] == "user"
            assert chat_history[0]["content"] == "hello"

            # Second message is bot
            assert chat_history[1]["role"] == "bot"
            assert chat_history[1]["content"] != ""
            assert "hello" in chat_history[1]["content"].lower() or "help" in chat_history[1]["content"].lower()

    def test_multiple_messages_build_chat_history(self, session_id):
        """Test that multiple messages build full conversation history."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "intent": "chat",
                "response": "Response to message",
                "plan": [],
            }

            # Send first message
            response1 = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "first message"}
            )
            assert response1.status_code == 200
            history1 = response1.json()["data"]["chat_history"]
            assert len(history1) == 2

            # Send second message
            response2 = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "second message"}
            )
            assert response2.status_code == 200
            history2 = response2.json()["data"]["chat_history"]
            # Should have 4 messages: user1, bot1, user2, bot2
            assert len(history2) == 4
            assert history2[0]["content"] == "first message"
            assert history2[1]["role"] == "bot"
            assert history2[2]["content"] == "second message"
            assert history2[3]["role"] == "bot"


class TestResponseFormatByIntent:
    """Tests for response structure based on intent type."""

    def test_report_intent_response_format(self, session_id):
        """Report intent should include plan, no response field."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "intent": "report",
                "response": "",
                "plan": ["step 1", "step 2"],
            }

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "analyze data"}
            )

            data = response.json()["data"]
            assert "plan" in data
            assert data["plan"] == ["step 1", "step 2"]
            assert "response" not in data  # No response field for report

    def test_qa_intent_response_format(self, session_id):
        """QA intent should include response, no plan field."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "intent": "qa",
                "response": "The answer is 42",
                "plan": [],  # Empty plan for QA
            }

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "what is the answer?"}
            )

            data = response.json()["data"]
            assert "response" in data
            assert data["response"] == "The answer is 42"
            assert "plan" not in data  # No plan field for QA

    def test_chat_intent_response_format(self, session_id):
        """Chat intent should include response, no plan field."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "intent": "chat",
                "response": "Nice to meet you!",
                "plan": [],
            }

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "hi"}
            )

            data = response.json()["data"]
            assert "response" in data
            assert data["response"] == "Nice to meet you!"
            assert "plan" not in data


class TestErrorHandling:
    """Tests for error handling in Story 4.2 API."""

    def test_pipeline_error_returns_error_response(self, session_id):
        """If pipeline fails, endpoint returns error response."""
        with patch("pipeline.graph.run_pipeline") as mock_pipeline:
            mock_pipeline.side_effect = RuntimeError("Pipeline error")

            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "test"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "PIPELINE_ERROR" in data["error"]["code"]

    def test_empty_message_still_rejected(self, session_id):
        """Empty messages should be rejected before pipeline execution."""
        response = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": ""}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "EMPTY_MESSAGE"

    def test_invalid_session_still_rejected(self, session_id):
        """Invalid sessions should be rejected before pipeline execution."""
        response = client.post(
            "/api/chat",
            json={"session_id": "invalid-session", "message": "test"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "INVALID_SESSION"
