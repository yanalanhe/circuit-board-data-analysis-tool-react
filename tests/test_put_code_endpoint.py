# tests/test_put_code_endpoint.py
"""Unit tests for PUT /api/code endpoint (Story 10.2).

Tests cover:
- AC #2/#3: PUT /api/code accepts session_id + code, validates via AST allowlist
- AC #6:    Validation failure → VALIDATION_ERROR code, plain-English inline message
- AC #4/#7: Execution failure → EXECUTION_ERROR code, translated message (no raw traceback)
- AC #4/#5: Success → returns charts, text, code; session pipeline_state updated
- Guard:    No pipeline_state → NO_PIPELINE_STATE error
- Guard:    Invalid session → INVALID_SESSION error
"""

import pytest
from unittest.mock import MagicMock, patch
import uuid


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from services.api import app
    return TestClient(app)


@pytest.fixture
def base_pipeline_state():
    """A minimal realistic pipeline_state as stored in session after a successful analysis."""
    return {
        "user_query": "plot voltage over time",
        "csv_temp_paths": {"data.csv": "/tmp/session_abc/data.csv"},
        "data_row_count": 200,
        "intent": "report",
        "plan": ["Load data", "Plot voltage vs time"],
        "generated_code": "import pandas as pd\nprint('original')",
        "validation_errors": [],
        "execution_output": "",
        "execution_success": True,
        "retry_count": 0,
        "replan_triggered": False,
        "error_messages": [],
        "report_charts": [b"old_chart_bytes"],
        "report_text": "Original trend text",
        "large_data_detected": False,
        "large_data_message": "",
        "recovery_applied": "",
    }


@pytest.fixture
def mock_session(base_pipeline_state):
    """Session fixture with a populated pipeline_state (analysis already run)."""
    sid = str(uuid.uuid4())
    return {
        "session_id": sid,
        "uploaded_dfs": {},
        "csv_temp_path": None,
        "chat_history": [],
        "pipeline_state": base_pipeline_state,
        "pipeline_running": False,
    }


# ---------------------------------------------------------------------------
# Guard conditions
# ---------------------------------------------------------------------------

class TestPutCodeGuards:
    """Guard: missing session or pipeline_state."""

    def test_invalid_session_returns_invalid_session_error(self, test_client):
        """Guard: non-existent session_id → INVALID_SESSION."""
        response = test_client.put(
            "/api/code",
            json={"session_id": "does-not-exist", "code": "print('hi')"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "INVALID_SESSION"

    def test_no_pipeline_state_returns_no_pipeline_state_error(
        self, test_client, mock_session
    ):
        """Guard: session exists but pipeline_state is None → NO_PIPELINE_STATE."""
        mock_session["pipeline_state"] = None
        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            response = test_client.put(
                "/api/code",
                json={"session_id": mock_session["session_id"], "code": "print('hi')"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "NO_PIPELINE_STATE"


# ---------------------------------------------------------------------------
# Validation failure (AC #3, #6)
# ---------------------------------------------------------------------------

class TestPutCodeValidationFailure:
    """Validation errors → VALIDATION_ERROR, plain-English message, no raw traceback."""

    def test_blocked_import_returns_validation_error_code(
        self, test_client, mock_session
    ):
        """AC #3/#6: Code with blocked import → status error, code VALIDATION_ERROR."""
        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            response = test_client.put(
                "/api/code",
                json={
                    "session_id": mock_session["session_id"],
                    "code": "import os\nos.system('ls')",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_validation_error_message_is_plain_english(
        self, test_client, mock_session
    ):
        """AC #6: Inline error message must not contain raw traceback."""
        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            response = test_client.put(
                "/api/code",
                json={
                    "session_id": mock_session["session_id"],
                    "code": "import sys\nsys.exit()",
                },
            )
        data = response.json()
        assert data["status"] == "error"
        msg = data["error"]["message"]
        assert isinstance(msg, str) and len(msg) > 0
        assert "Traceback" not in msg, "Raw traceback must not appear in validation error"

    def test_syntax_error_returns_validation_error_code(
        self, test_client, mock_session
    ):
        """AC #3/#6: Code with syntax error → VALIDATION_ERROR."""
        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            response = test_client.put(
                "/api/code",
                json={
                    "session_id": mock_session["session_id"],
                    "code": "def foo(\n    x\n# missing closing paren",
                },
            )
        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_validation_failure_does_not_execute_code(
        self, test_client, mock_session
    ):
        """AC #3: Execution must NOT occur when validation fails."""
        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("pipeline.nodes.executor.execute_code") as mock_exec:
                response = test_client.put(
                    "/api/code",
                    json={
                        "session_id": mock_session["session_id"],
                        "code": "import os",
                    },
                )
        assert response.json()["status"] == "error"
        mock_exec.assert_not_called()

    def test_validation_failure_does_not_update_session_state(
        self, test_client, mock_session
    ):
        """AC #6: Validation failure must NOT overwrite session pipeline_state."""
        original_code = mock_session["pipeline_state"]["generated_code"]
        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            test_client.put(
                "/api/code",
                json={
                    "session_id": mock_session["session_id"],
                    "code": "import subprocess",
                },
            )
        # Session's generated_code must remain unchanged
        assert mock_session["pipeline_state"]["generated_code"] == original_code


# ---------------------------------------------------------------------------
# Execution failure (AC #7)
# ---------------------------------------------------------------------------

class TestPutCodeExecutionFailure:
    """Execution errors → EXECUTION_ERROR, translated message in report panel."""

    def test_execution_failure_returns_execution_error_code(
        self, test_client, mock_session
    ):
        """AC #7: Subprocess failure → status error, code EXECUTION_ERROR."""
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": "1/0"}
        fake_exec_result = {
            "execution_success": False,
            "report_charts": [],
            "report_text": "",
            "execution_output": "",
            "retry_count": 1,
            "replan_triggered": False,
            "error_messages": ["An unexpected error occurred. Check the developer console for details."],
        }

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch("pipeline.nodes.executor.execute_code", return_value=fake_exec_result):
                    response = test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": "1/0",
                        },
                    )

        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "EXECUTION_ERROR"

    def test_execution_failure_message_no_raw_traceback(
        self, test_client, mock_session
    ):
        """AC #7: Error message must be translated, not a raw Python traceback."""
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": "1/0"}
        fake_exec_result = {
            "execution_success": False,
            "report_charts": [],
            "report_text": "",
            "execution_output": "",
            "retry_count": 1,
            "replan_triggered": False,
            "error_messages": ["An unexpected error occurred. Check the developer console for details."],
        }

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch("pipeline.nodes.executor.execute_code", return_value=fake_exec_result):
                    response = test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": "1/0",
                        },
                    )

        msg = response.json()["error"]["message"]
        assert "Traceback" not in msg, "Raw traceback must not reach API response"

    def test_execution_exception_returns_execution_error_code(
        self, test_client, mock_session
    ):
        """AC #7: Unhandled exception from execute_code → EXECUTION_ERROR with translated message."""
        fake_reexec = {**mock_session["pipeline_state"]}

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch(
                    "pipeline.nodes.executor.execute_code",
                    side_effect=RuntimeError("unexpected crash"),
                ):
                    response = test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": "print('valid')",
                        },
                    )

        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "EXECUTION_ERROR"


# ---------------------------------------------------------------------------
# Success path (AC #4, #5)
# ---------------------------------------------------------------------------

class TestPutCodeSuccess:
    """Success path: valid code → execute → return report data."""

    def _make_exec_result(self, chart_bytes=b"PNG_DATA", text="Trend up"):
        return {
            "execution_success": True,
            "report_charts": [chart_bytes],
            "report_text": text,
            "execution_output": "",
            "error_messages": [],
        }

    def test_success_returns_status_success(self, test_client, mock_session):
        """AC #4/#5: Valid code that executes → status success."""
        edited_code = "print('analysis done')"
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": edited_code}

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch(
                    "pipeline.nodes.executor.execute_code",
                    return_value=self._make_exec_result(),
                ):
                    response = test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": edited_code,
                        },
                    )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_success_response_contains_charts_text_code(self, test_client, mock_session):
        """AC #5: Success response data has charts, text, and code fields."""
        edited_code = "print('new analysis')"
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": edited_code}

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch(
                    "pipeline.nodes.executor.execute_code",
                    return_value=self._make_exec_result(text="Revenue up 12%"),
                ):
                    response = test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": edited_code,
                        },
                    )

        data = response.json()["data"]
        assert "charts" in data
        assert "text" in data
        assert "code" in data
        assert data["text"] == "Revenue up 12%"
        assert data["code"] == edited_code

    def test_success_charts_are_strings(self, test_client, mock_session):
        """AC #5: Charts in response are serialized as strings (FastAPI UTF-8-decodes bytes,
        matching the existing GET /api/report behavior)."""
        # Use ASCII-safe bytes so FastAPI's UTF-8 decode succeeds (same as test pattern
        # used in test_execute_endpoint.py and GET /api/report tests)
        raw_chart = b"FAKEPNG"
        edited_code = "import matplotlib.pyplot as plt; plt.savefig('out.png')"
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": edited_code}

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch(
                    "pipeline.nodes.executor.execute_code",
                    return_value=self._make_exec_result(chart_bytes=raw_chart),
                ):
                    response = test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": edited_code,
                        },
                    )

        charts = response.json()["data"]["charts"]
        assert len(charts) == 1
        assert isinstance(charts[0], str)
        # FastAPI serializes bytes via .decode("utf-8") — consistent with GET /api/report
        assert charts[0] == raw_chart.decode("utf-8")

    def test_success_updates_session_generated_code(self, test_client, mock_session):
        """AC #5: After success, session pipeline_state['generated_code'] is updated."""
        edited_code = "print('edited version')"
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": edited_code}

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch(
                    "pipeline.nodes.executor.execute_code",
                    return_value=self._make_exec_result(),
                ):
                    test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": edited_code,
                        },
                    )

        assert mock_session["pipeline_state"]["generated_code"] == edited_code

    def test_success_updates_session_report_charts(self, test_client, mock_session):
        """AC #5: After success, session pipeline_state['report_charts'] is updated."""
        new_chart = b"NEW_CHART_PNG"
        edited_code = "print('chart code')"
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": edited_code}

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch(
                    "pipeline.nodes.executor.execute_code",
                    return_value=self._make_exec_result(chart_bytes=new_chart),
                ):
                    test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": edited_code,
                        },
                    )

        assert mock_session["pipeline_state"]["report_charts"] == [new_chart]

    def test_success_updates_session_execution_success_flag(self, test_client, mock_session):
        """AC #5: After success, session pipeline_state['execution_success'] is True."""
        edited_code = "print('ok')"
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": edited_code}

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch("utils.reexec.build_reexec_state", return_value=fake_reexec):
                with patch(
                    "pipeline.nodes.executor.execute_code",
                    return_value=self._make_exec_result(),
                ):
                    test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": edited_code,
                        },
                    )

        assert mock_session["pipeline_state"]["execution_success"] is True

    def test_build_reexec_state_called_with_correct_args(self, test_client, mock_session):
        """Verify build_reexec_state is called with (pipeline_state, edited_code)."""
        edited_code = "print('verify args')"
        fake_reexec = {**mock_session["pipeline_state"], "generated_code": edited_code}
        original_ps = mock_session["pipeline_state"]

        with patch("services.session.sessions", {mock_session["session_id"]: mock_session}):
            with patch(
                "utils.reexec.build_reexec_state", return_value=fake_reexec
            ) as mock_build:
                with patch(
                    "pipeline.nodes.executor.execute_code",
                    return_value=self._make_exec_result(),
                ):
                    test_client.put(
                        "/api/code",
                        json={
                            "session_id": mock_session["session_id"],
                            "code": edited_code,
                        },
                    )

        mock_build.assert_called_once_with(original_ps, edited_code)
