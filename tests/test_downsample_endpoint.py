"""Tests for POST /api/downsample endpoint.

Story 9.2: Implement Auto-Downsample Recovery Path.

Tests verify:
- AC #2: frontend triggers backend call (endpoint exists and responds)
- AC #3: apply_uniform_stride() reduces dataset to ≤10,000 rows
- AC #4: session["uploaded_dfs"] updated; /api/data returns reduced row count
- AC #5: session["csv_temp_paths"] populated with valid temp files for pipeline use
- Error case: no uploaded data → structured error response
- Small dataset: apply_uniform_stride passthrough (≤10k rows unchanged)
"""
import io
import csv
import os
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from services.api import app
from services.session import get_all_sessions_for_testing, clear_all_sessions_for_testing


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Clean up sessions after each test to prevent cross-test contamination."""
    yield
    clear_all_sessions_for_testing()


def make_csv_bytes(rows: list[dict]) -> bytes:
    """Serialise a list of dicts to CSV bytes."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def make_large_csv_bytes(num_rows: int) -> bytes:
    """Create CSV bytes with num_rows rows (two columns)."""
    rows = [{"col": i, "value": i * 2.5} for i in range(num_rows)]
    return make_csv_bytes(rows)


def create_session(client) -> str:
    """Create a new session and return session_id."""
    resp = client.post("/api/session")
    return resp.json()["data"]["session_id"]


def upload_csv(client, session_id: str, filename: str, content: bytes) -> dict:
    """Upload a single CSV file via /api/upload."""
    resp = client.post(
        "/api/upload",
        headers={"session-id": session_id},
        files=[("files", (filename, io.BytesIO(content), "text/csv"))],
    )
    return resp.json()


def call_downsample(client, session_id: str) -> dict:
    """Call POST /api/downsample and return parsed JSON."""
    resp = client.post(
        "/api/downsample",
        headers={"session-id": session_id},
    )
    return resp.json()


# ============================================================================
# Happy Path — Large Dataset Downsampled
# ============================================================================

class TestDownsampleHappyPath:
    """Core downsample functionality on a large dataset (AC #2, #3, #4, #5)."""

    def test_returns_success_status(self, client):
        """POST /api/downsample returns status=success for valid session with data."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        result = call_downsample(client, session_id)

        assert result["status"] == "success"

    def test_response_contains_downsampled_flag(self, client):
        """Response data.downsampled is True."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        result = call_downsample(client, session_id)

        assert result["data"]["downsampled"] is True

    def test_row_counts_reduced_to_at_most_10000(self, client):
        """Response row_counts value is ≤10,000 after downsampling 150k rows."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        result = call_downsample(client, session_id)

        assert result["data"]["row_counts"]["big.csv"] <= 10_000

    def test_row_counts_equals_exactly_10000_for_large_file(self, client):
        """150k rows → exactly 10,000 rows after apply_uniform_stride (DOWNSAMPLE_TARGET_ROWS)."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        result = call_downsample(client, session_id)

        assert result["data"]["row_counts"]["big.csv"] == 10_000

    def test_response_filenames_contains_uploaded_file(self, client):
        """Response data.filenames lists the uploaded file."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        result = call_downsample(client, session_id)

        assert "big.csv" in result["data"]["filenames"]


# ============================================================================
# Session State After Downsampling
# ============================================================================

class TestSessionStateAfterDownsample:
    """Verify session state is correctly updated (AC #4, #5)."""

    def test_uploaded_dfs_updated_in_session(self, client):
        """session["uploaded_dfs"]["big.csv"] has ≤10,000 rows after downsample."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        call_downsample(client, session_id)

        sessions = get_all_sessions_for_testing()
        session = sessions[session_id]
        assert len(session["uploaded_dfs"]["big.csv"]) <= 10_000

    def test_recovery_applied_set_in_session(self, client):
        """session["recovery_applied"] == "uniform_stride_10k" after downsample."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        call_downsample(client, session_id)

        sessions = get_all_sessions_for_testing()
        session = sessions[session_id]
        assert session["recovery_applied"] == "uniform_stride_10k"

    def test_csv_temp_paths_populated(self, client):
        """session["csv_temp_paths"] has an entry for each uploaded file after downsample."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        call_downsample(client, session_id)

        sessions = get_all_sessions_for_testing()
        session = sessions[session_id]
        assert "big.csv" in session["csv_temp_paths"]

    def test_csv_temp_paths_point_to_real_files(self, client):
        """Temp CSV file paths in session["csv_temp_paths"] exist on disk."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        call_downsample(client, session_id)

        sessions = get_all_sessions_for_testing()
        session = sessions[session_id]
        temp_path = session["csv_temp_paths"]["big.csv"]
        assert os.path.exists(temp_path)

    def test_csv_temp_file_contains_downsampled_data(self, client):
        """Temp CSV file contains exactly the downsampled rows (readable by pandas)."""
        session_id = create_session(client)
        upload_csv(client, session_id, "big.csv", make_large_csv_bytes(150_000))

        call_downsample(client, session_id)

        sessions = get_all_sessions_for_testing()
        session = sessions[session_id]
        temp_path = session["csv_temp_paths"]["big.csv"]
        df_from_file = pd.read_csv(temp_path)
        assert len(df_from_file) == 10_000


# ============================================================================
# Error Cases
# ============================================================================

class TestDownsampleErrors:
    """Error handling for /api/downsample (AC: error case)."""

    def test_no_uploaded_data_returns_error(self, client):
        """Calling /api/downsample before any upload returns status=error."""
        session_id = create_session(client)

        result = call_downsample(client, session_id)

        assert result["status"] == "error"

    def test_no_uploaded_data_error_code(self, client):
        """Error response includes code=NO_DATA when no files uploaded."""
        session_id = create_session(client)

        result = call_downsample(client, session_id)

        assert result["error"]["code"] == "NO_DATA"

    def test_no_uploaded_data_error_message(self, client):
        """Error message mentions uploading a CSV file."""
        session_id = create_session(client)

        result = call_downsample(client, session_id)

        assert "upload" in result["error"]["message"].lower()

    def test_invalid_session_returns_error(self, client):
        """Calling /api/downsample with unknown session_id returns error."""
        result = call_downsample(client, "nonexistent-session-id")

        assert result["status"] == "error"


# ============================================================================
# Small Dataset Passthrough
# ============================================================================

class TestSmallDatasetPassthrough:
    """Small datasets (≤10k rows) are returned unchanged by apply_uniform_stride."""

    def test_small_dataset_row_count_unchanged(self, client):
        """500-row dataset returns 500 rows after downsample (no reduction needed)."""
        session_id = create_session(client)
        small_content = make_csv_bytes([{"x": i, "y": i * 2} for i in range(500)])
        upload_csv(client, session_id, "small.csv", small_content)

        result = call_downsample(client, session_id)

        assert result["status"] == "success"
        assert result["data"]["row_counts"]["small.csv"] == 500

    def test_exactly_10000_rows_passthrough(self, client):
        """Exactly 10,000-row dataset returns 10,000 rows (at boundary, no reduction)."""
        session_id = create_session(client)
        content = make_large_csv_bytes(10_000)
        upload_csv(client, session_id, "boundary.csv", content)

        result = call_downsample(client, session_id)

        assert result["data"]["row_counts"]["boundary.csv"] == 10_000
        assert result["data"]["downsampled"] is True

    def test_recovery_applied_set_even_for_small_dataset(self, client):
        """session["recovery_applied"] is set regardless of whether data was reduced."""
        session_id = create_session(client)
        small_content = make_csv_bytes([{"x": i} for i in range(100)])
        upload_csv(client, session_id, "tiny.csv", small_content)

        call_downsample(client, session_id)

        sessions = get_all_sessions_for_testing()
        assert sessions[session_id]["recovery_applied"] == "uniform_stride_10k"


# ============================================================================
# Multiple Files
# ============================================================================

class TestMultipleFilesDownsample:
    """Verify all uploaded files are downsampled when multiple files exist."""

    def test_all_files_in_response(self, client):
        """Response filenames contains all uploaded files."""
        session_id = create_session(client)
        content1 = make_large_csv_bytes(150_000)
        content2 = make_large_csv_bytes(120_000)

        # Upload both files (separate calls — each call adds to session)
        upload_csv(client, session_id, "file1.csv", content1)
        upload_csv(client, session_id, "file2.csv", content2)

        result = call_downsample(client, session_id)

        assert result["status"] == "success"
        assert "file1.csv" in result["data"]["filenames"]
        assert "file2.csv" in result["data"]["filenames"]

    def test_all_files_row_counts_reduced(self, client):
        """Both files have row counts ≤10,000 after downsample."""
        session_id = create_session(client)
        content1 = make_large_csv_bytes(150_000)
        content2 = make_large_csv_bytes(120_000)

        upload_csv(client, session_id, "file1.csv", content1)
        upload_csv(client, session_id, "file2.csv", content2)

        result = call_downsample(client, session_id)

        assert result["data"]["row_counts"]["file1.csv"] <= 10_000
        assert result["data"]["row_counts"]["file2.csv"] <= 10_000
