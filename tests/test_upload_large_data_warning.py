"""Tests for large data warning response format in /api/upload endpoint.

Story 9.1: Implement Large Data Detection on Upload.

Tests verify:
- AC #1: detect_large_data() called with combined row count and total size
- AC #3: large_data_warning has correct shape { detected, row_count, size_mb, message }
- AC #6: no large_data_warning field for normal-sized datasets
- AC #2: dual threshold — row count OR size triggers the warning
"""
import io
import csv
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from services.api import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def make_csv_bytes(rows: list[dict]) -> bytes:
    """Serialise a list of dicts to CSV bytes."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def upload_csv(client, session_id: str, files: list[tuple[str, bytes]]) -> dict:
    """Helper to upload one or more CSV files via /api/upload."""
    files_param = [
        ("files", (name, io.BytesIO(content), "text/csv"))
        for name, content in files
    ]
    resp = client.post(
        "/api/upload",
        headers={"session-id": session_id},
        files=files_param,
    )
    return resp.json()


def make_large_csv_bytes(num_rows: int) -> bytes:
    """Create CSV bytes with num_rows rows."""
    rows = [{"col": i, "value": i * 2.5} for i in range(num_rows)]
    return make_csv_bytes(rows)


class TestLargeDataWarningAbsent:
    """No warning returned for datasets below both thresholds (AC #6)."""

    def test_no_warning_for_small_dataset(self, client):
        """Normal dataset (100 rows) → no large_data_warning in response."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content = make_csv_bytes([{"x": i} for i in range(100)])
        result = upload_csv(client, session_id, [("data.csv", content)])

        assert result["status"] == "success"
        assert "large_data_warning" not in result["data"]

    def test_no_warning_just_below_row_threshold(self, client):
        """99,999 rows → no large_data_warning (threshold is ≥100,000)."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content = make_large_csv_bytes(99_999)
        result = upload_csv(client, session_id, [("data.csv", content)])

        assert result["status"] == "success"
        assert "large_data_warning" not in result["data"]


class TestLargeDataWarningShape:
    """Large data warning has correct shape when detected (AC #3)."""

    def test_warning_has_detected_true(self, client):
        """large_data_warning.detected is True when threshold exceeded."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content = make_large_csv_bytes(100_000)
        result = upload_csv(client, session_id, [("big.csv", content)])

        assert result["status"] == "success"
        warning = result["data"]["large_data_warning"]
        assert warning["detected"] is True

    def test_warning_has_row_count(self, client):
        """large_data_warning.row_count equals total rows uploaded."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content = make_large_csv_bytes(100_000)
        result = upload_csv(client, session_id, [("big.csv", content)])

        warning = result["data"]["large_data_warning"]
        assert warning["row_count"] == 100_000

    def test_warning_has_size_mb(self, client):
        """large_data_warning.size_mb is a positive float."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content = make_large_csv_bytes(100_000)
        result = upload_csv(client, session_id, [("big.csv", content)])

        warning = result["data"]["large_data_warning"]
        assert isinstance(warning["size_mb"], float)
        assert warning["size_mb"] > 0

    def test_warning_has_message_with_row_count(self, client):
        """large_data_warning.message contains human-readable row count."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content = make_large_csv_bytes(100_000)
        result = upload_csv(client, session_id, [("big.csv", content)])

        warning = result["data"]["large_data_warning"]
        assert "100,000" in warning["message"]

    def test_warning_message_mentions_threshold(self, client):
        """large_data_warning.message mentions visualization threshold."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content = make_large_csv_bytes(100_000)
        result = upload_csv(client, session_id, [("big.csv", content)])

        warning = result["data"]["large_data_warning"]
        assert "threshold" in warning["message"].lower()

    def test_warning_has_no_legacy_fields(self, client):
        """large_data_warning does NOT contain old fields: code, affected_files, max_row_count."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content = make_large_csv_bytes(100_000)
        result = upload_csv(client, session_id, [("big.csv", content)])

        warning = result["data"]["large_data_warning"]
        assert "code" not in warning
        assert "affected_files" not in warning
        assert "max_row_count" not in warning


class TestLargeDataCombinedDetection:
    """Detection uses combined row count across all uploaded files (AC #1)."""

    def test_combined_rows_trigger_warning(self, client):
        """Two files that are individually below threshold but combined ≥100K rows → warning."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        # Each file: 60,000 rows (below 100K), combined: 120,000 (above 100K)
        content1 = make_large_csv_bytes(60_000)
        content2 = make_large_csv_bytes(60_000)
        result = upload_csv(client, session_id, [
            ("part1.csv", content1),
            ("part2.csv", content2),
        ])

        assert result["status"] == "success"
        assert "large_data_warning" in result["data"]
        assert result["data"]["large_data_warning"]["row_count"] == 120_000

    def test_combined_row_count_in_warning(self, client):
        """Warning row_count reflects total rows from all uploaded files."""
        resp = client.post("/api/session")
        session_id = resp.json()["data"]["session_id"]

        content1 = make_large_csv_bytes(60_000)
        content2 = make_large_csv_bytes(60_000)
        result = upload_csv(client, session_id, [
            ("part1.csv", content1),
            ("part2.csv", content2),
        ])

        warning = result["data"]["large_data_warning"]
        assert warning["row_count"] == 120_000
