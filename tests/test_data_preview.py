"""Tests for data preview endpoint (Story 3.2).

Tests verify that:
1. GET /api/data returns preview rows (first 10-20)
2. Response includes column names and data types
3. Multiple files are handled correctly
4. Data types are properly inferred and formatted
"""

import pytest
import pandas as pd
from io import BytesIO
from fastapi.testclient import TestClient
from services.api import app
from services.session import get_session


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestDataPreviewEndpoint:
    """Test data preview endpoint functionality."""

    def test_get_data_returns_preview_rows(self, client):
        """Test that /api/data returns preview rows (not just metadata)."""
        # Create session
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        # Add sample data to session
        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "temperature": [23.5, 24.1, 22.8, 25.2, 23.9],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
            "location": ["A", "B", "A", "C", "B"]
        })
        session["uploaded_dfs"]["data.csv"] = df

        response = client.get(
            "/api/data",
            headers={"session-id": session_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "files" in data["data"]
        assert len(data["data"]["files"]) == 1

        file_data = data["data"]["files"][0]
        assert file_data["name"] == "data.csv"
        assert "preview" in file_data  # Should have preview rows
        assert isinstance(file_data["preview"], list)
        assert len(file_data["preview"]) > 0

    def test_preview_includes_data_types(self, client):
        """Test that column types are included in response."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "value": [1.5, 2.5, 3.5],
            "name": ["a", "b", "c"]
        })
        session["uploaded_dfs"]["data.csv"] = df

        response = client.get(
            "/api/data",
            headers={"session-id": session_id}
        )

        file_data = response.json()["data"]["files"][0]
        assert "dtypes" in file_data or "column_types" in file_data

        # Should have type info for each column
        dtypes = file_data.get("dtypes") or file_data.get("column_types")
        assert len(dtypes) == len(file_data["columns"])

    def test_preview_limited_to_10_to_20_rows(self, client):
        """Test that only 10-20 preview rows are returned (not all data)."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        # Create DataFrame with 100 rows
        df = pd.DataFrame({
            "id": range(1, 101),
            "value": [i * 1.5 for i in range(1, 101)]
        })
        session["uploaded_dfs"]["large.csv"] = df

        response = client.get(
            "/api/data",
            headers={"session-id": session_id}
        )

        file_data = response.json()["data"]["files"][0]
        preview = file_data["preview"]

        # Should return 10-20 rows, not all 100
        assert 10 <= len(preview) <= 20
        assert len(preview) < 100

    def test_multiple_files_support(self, client):
        """Test that multiple uploaded files are all returned."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df1 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        df2 = pd.DataFrame({"x": [10, 20], "y": [30, 40]})

        session["uploaded_dfs"]["file1.csv"] = df1
        session["uploaded_dfs"]["file2.csv"] = df2

        response = client.get(
            "/api/data",
            headers={"session-id": session_id}
        )

        files = response.json()["data"]["files"]
        assert len(files) == 2

        file_names = [f["name"] for f in files]
        assert "file1.csv" in file_names
        assert "file2.csv" in file_names

    def test_data_type_formatting(self, client):
        """Test that data types are formatted for display."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.5, 2.5, 3.5],
            "str_col": ["a", "b", "c"]
        })
        session["uploaded_dfs"]["data.csv"] = df

        response = client.get(
            "/api/data",
            headers={"session-id": session_id}
        )

        file_data = response.json()["data"]["files"][0]
        dtypes = file_data.get("dtypes") or file_data.get("column_types")

        # Should format types appropriately
        assert all(isinstance(t, str) for t in dtypes)

    def test_column_metadata_included(self, client):
        """Test that column names and basic metadata are included."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        session = get_session(session_id)
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "value": [10, 20, 30, 40, 50]
        })
        session["uploaded_dfs"]["data.csv"] = df

        response = client.get(
            "/api/data",
            headers={"session-id": session_id}
        )

        file_data = response.json()["data"]["files"][0]

        assert "columns" in file_data
        assert "name" in file_data
        assert "rows" in file_data
        assert file_data["rows"] == 5  # Should still include total row count
