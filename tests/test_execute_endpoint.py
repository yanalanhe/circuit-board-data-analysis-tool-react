# tests/test_execute_endpoint.py
"""Unit tests for POST /api/execute endpoint (Story 5.2).

Tests cover:
- AC #3: POST /api/execute accepts session_id
- AC #4: Backend sets pipeline_running = True
- AC #4: Pipeline continues to code generation
- Error handling: session not found
- Error handling: no plan available
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
def mock_session():
    """Create a mock session with a plan."""
    return {
        "session_id": str(uuid.uuid4()),
        "uploaded_dfs": {},
        "csv_temp_path": None,
        "pipeline_state": {
            "user_query": "Create a chart showing voltage vs time",
            "intent": "report",
            "plan": [
                "1. Load voltage and current data from uploaded CSVs",
                "2. Calculate summary statistics",
                "3. Generate time-series plot",
                "4. Add trend line analysis"
            ],
            "generated_code": None,
            "validation_errors": [],
            "execution_output": "",
            "execution_success": False,
            "retry_count": 0,
            "replan_triggered": False,
            "error_messages": [],
            "report_charts": [],
            "report_text": "",
            "large_data_detected": False,
            "large_data_message": "",
            "recovery_applied": ""
        },
        "pipeline_running": False,
    }


class TestExecuteEndpoint:
    """Tests for POST /api/execute endpoint."""

    def test_execute_with_valid_session_and_plan(self, test_client, mock_session):
        """AC #3 & #4: Execute endpoint accepts session_id and sets pipeline_running."""
        with patch('services.session.sessions', {mock_session["session_id"]: mock_session}):
            with patch('services.api.run_pipeline') as mock_run:
                mock_run.return_value = {
                    **mock_session["pipeline_state"],
                    "generated_code": "import pandas as pd\n...",
                    "execution_success": True
                }

                response = test_client.post(
                    "/api/execute",
                    json={"session_id": mock_session["session_id"]}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["data"]["execution_status"] == "started"

                # Verify pipeline_running was set
                assert mock_session["pipeline_running"] == False  # Set back to False after execution

    def test_execute_with_invalid_session(self, test_client):
        """Error: Session not found."""
        response = test_client.post(
            "/api/execute",
            json={"session_id": "invalid-session-id"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "INVALID_SESSION"

    def test_execute_with_no_plan(self, test_client, mock_session):
        """Error: No plan available (AC #4 negative case)."""
        # Remove plan from pipeline_state
        mock_session["pipeline_state"]["plan"] = None

        with patch('services.session.sessions', {mock_session["session_id"]: mock_session}):
            response = test_client.post(
                "/api/execute",
                json={"session_id": mock_session["session_id"]}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["error"]["code"] == "NO_PLAN_AVAILABLE"

    def test_execute_with_no_pipeline_state(self, test_client, mock_session):
        """Error: No pipeline_state at all."""
        mock_session["pipeline_state"] = None

        with patch('services.session.sessions', {mock_session["session_id"]: mock_session}):
            response = test_client.post(
                "/api/execute",
                json={"session_id": mock_session["session_id"]}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["error"]["code"] == "NO_PLAN_AVAILABLE"

    def test_execute_sets_pipeline_running_flag(self, test_client, mock_session):
        """AC #4: Backend sets pipeline_running = True during execution."""
        with patch('services.session.sessions', {mock_session["session_id"]: mock_session}):
            with patch('services.api.run_pipeline') as mock_run:
                mock_run.return_value = {
                    **mock_session["pipeline_state"],
                    "generated_code": "import pandas as pd\n...",
                }

                # Before execute, flag should be False
                assert mock_session["pipeline_running"] == False

                response = test_client.post(
                    "/api/execute",
                    json={"session_id": mock_session["session_id"]}
                )

                assert response.status_code == 200

                # After execute completes, flag should be False again (execution done)
                assert mock_session["pipeline_running"] == False

    def test_execute_error_handling(self, test_client, mock_session):
        """Error: Pipeline execution fails."""
        with patch('services.session.sessions', {mock_session["session_id"]: mock_session}):
            with patch('services.api.run_pipeline') as mock_run:
                mock_run.side_effect = Exception("Pipeline execution failed")

                response = test_client.post(
                    "/api/execute",
                    json={"session_id": mock_session["session_id"]}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "error"
                assert data["error"]["code"] == "EXECUTION_FAILED"

                # Flag should be reset on error
                assert mock_session["pipeline_running"] == False

    def test_execute_stores_final_state(self, test_client, mock_session):
        """AC #4: Final pipeline state is stored back to session."""
        final_state = {
            **mock_session["pipeline_state"],
            "generated_code": "import pandas as pd\ndf = pd.read_csv(...)",
            "execution_success": True,
            "report_charts": ["base64_encoded_png_1"],
            "report_text": "Analysis shows..."
        }

        with patch('services.session.sessions', {mock_session["session_id"]: mock_session}):
            with patch('services.api.run_pipeline') as mock_run:
                mock_run.return_value = final_state

                response = test_client.post(
                    "/api/execute",
                    json={"session_id": mock_session["session_id"]}
                )

                assert response.status_code == 200

                # Verify final state was stored
                stored_state = mock_session["pipeline_state"]
                assert stored_state["generated_code"] == final_state["generated_code"]
                assert stored_state["execution_success"] == True
                assert len(stored_state["report_charts"]) > 0
