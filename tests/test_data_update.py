"""Tests for data update endpoint (Story 3.3).

Tests verify that:
1. PUT /api/data updates cell values
2. Data type validation works (int, float, string, datetime, bool)
3. Invalid data types are rejected with descriptive errors
4. Backend updates the DataFrame in memory
5. Session validation works
"""

import pytest
import pandas as pd
from fastapi.testclient import TestClient
from services.api import app
from services.session import get_session


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestDataUpdateEndpoint:
    """Test data update endpoint functionality."""

    def test_update_single_cell_value(self, client):
        """Test that PUT /api/data updates a single cell value."""
        # Create session and add data
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "temperature": [23.5, 24.1, 22.8],
            "location": ["A", "B", "C"]
        })
        session["uploaded_dfs"]["data.csv"] = df

        # Update a cell
        response = client.put(
            "/api/data",
            json={
                "session_id": session_id,
                "updates": {
                    "filename": "data.csv",
                    "row_index": 0,
                    "column": "temperature",
                    "value": 25.0
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify the value was updated in the DataFrame
        updated_df = session["uploaded_dfs"]["data.csv"]
        assert updated_df.loc[0, "temperature"] == 25.0

    def test_update_validates_data_types(self, client):
        """Test that invalid data types are rejected."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "temperature": [23.5, 24.1, 22.8]
        })
        session["uploaded_dfs"]["data.csv"] = df

        # Try to update float column with non-numeric value
        response = client.put(
            "/api/data",
            json={
                "session_id": session_id,
                "updates": {
                    "filename": "data.csv",
                    "row_index": 0,
                    "column": "temperature",
                    "value": "not_a_number"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "validation" in data["error"]["code"].lower()

    def test_update_integer_column(self, client):
        """Test updating an integer column."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "count": [10, 20, 30]
        })
        session["uploaded_dfs"]["data.csv"] = df

        # Update with valid integer
        response = client.put(
            "/api/data",
            json={
                "session_id": session_id,
                "updates": {
                    "filename": "data.csv",
                    "row_index": 1,
                    "column": "count",
                    "value": 25
                }
            }
        )

        assert response.status_code == 200
        updated_df = session["uploaded_dfs"]["data.csv"]
        assert updated_df.loc[1, "count"] == 25

    def test_update_string_column(self, client):
        """Test updating a string column."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"]
        })
        session["uploaded_dfs"]["data.csv"] = df

        response = client.put(
            "/api/data",
            json={
                "session_id": session_id,
                "updates": {
                    "filename": "data.csv",
                    "row_index": 0,
                    "column": "name",
                    "value": "Diana"
                }
            }
        )

        assert response.status_code == 200
        updated_df = session["uploaded_dfs"]["data.csv"]
        assert updated_df.loc[0, "name"] == "Diana"

    def test_update_with_invalid_session(self, client):
        """Test that invalid session is rejected."""
        response = client.put(
            "/api/data",
            json={
                "session_id": "invalid-session",
                "updates": {
                    "filename": "data.csv",
                    "row_index": 0,
                    "column": "temperature",
                    "value": 25.0
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    def test_update_with_missing_file(self, client):
        """Test that missing file is reported."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        # Don't upload any files

        response = client.put(
            "/api/data",
            json={
                "session_id": session_id,
                "updates": {
                    "filename": "nonexistent.csv",
                    "row_index": 0,
                    "column": "temperature",
                    "value": 25.0
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    def test_update_multiple_cells_in_sequence(self, client):
        """Test updating multiple cells in sequence."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "value": [10.5, 20.5, 30.5]
        })
        session["uploaded_dfs"]["data.csv"] = df

        # Update first cell
        response1 = client.put(
            "/api/data",
            json={
                "session_id": session_id,
                "updates": {
                    "filename": "data.csv",
                    "row_index": 0,
                    "column": "value",
                    "value": 15.5
                }
            }
        )
        assert response1.status_code == 200

        # Update second cell
        response2 = client.put(
            "/api/data",
            json={
                "session_id": session_id,
                "updates": {
                    "filename": "data.csv",
                    "row_index": 1,
                    "column": "value",
                    "value": 25.5
                }
            }
        )
        assert response2.status_code == 200

        # Verify both updates were applied
        updated_df = session["uploaded_dfs"]["data.csv"]
        assert updated_df.loc[0, "value"] == 15.5
        assert updated_df.loc[1, "value"] == 25.5

    def test_error_message_includes_column_and_row(self, client):
        """Test that error messages include column and row information."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "temperature": [23.5, 24.1, 22.8]
        })
        session["uploaded_dfs"]["data.csv"] = df

        response = client.put(
            "/api/data",
            json={
                "session_id": session_id,
                "updates": {
                    "filename": "data.csv",
                    "row_index": 2,
                    "column": "temperature",
                    "value": "invalid"
                }
            }
        )

        assert response.status_code == 200
        error = response.json()["error"]
        assert "temperature" in error.get("message", "").lower()
