"""Pydantic request/response models for REST API endpoints.

These models define the data contract for all API requests and responses.
Organized by functional area: sessions, uploads, data, chat, execution, templates.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


# ============================================================================
# Session Management Models
# ============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new session (no fields required)."""
    pass


class CreateSessionResponse(BaseModel):
    """Response from session creation endpoint."""
    session_id: str = Field(..., description="UUID of the newly created session")


# ============================================================================
# CSV Upload & Data Models
# ============================================================================

class LargeDataWarning(BaseModel):
    """Warning details for large dataset detection."""
    detected: bool = Field(..., description="Whether large data was detected")
    row_count: int = Field(..., description="Number of rows in dataset")
    size_mb: float = Field(..., description="Dataset size in MB")
    message: str = Field(..., description="User-facing message about large data")


class UploadResponse(BaseModel):
    """Response from CSV file upload endpoint."""
    filenames: List[str] = Field(..., description="Names of uploaded files")
    row_counts: Dict[str, int] = Field(..., description="Row count per file")
    large_data_warning: Optional[LargeDataWarning] = Field(
        None,
        description="Warning if dataset exceeds size/row thresholds"
    )


class DataFile(BaseModel):
    """Metadata for a single uploaded data file."""
    name: str = Field(..., description="Filename")
    columns: List[str] = Field(..., description="Column names")
    rows: int = Field(..., description="Number of rows")


class DataPreviewResponse(BaseModel):
    """Response from data preview/retrieval endpoint."""
    files: List[DataFile] = Field(..., description="List of uploaded files with metadata")


class DataUpdateRequest(BaseModel):
    """Request to update data (manual edits)."""
    session_id: str = Field(..., description="Session identifier")
    updates: Dict = Field(..., description="Data updates to apply")


# ============================================================================
# Chat & Intent Classification Models
# ============================================================================

class ChatRequest(BaseModel):
    """Request to submit a natural language query."""
    session_id: str = Field(..., description="Session identifier from /api/session")
    message: str = Field(..., description="Natural language query from user")


class ChatResponse(BaseModel):
    """Response from chat/query endpoint."""
    intent: str = Field(..., description="Classified intent: 'report', 'qa', or 'chat'")
    plan: Optional[List[str]] = Field(
        None,
        description="Execution plan steps (populated for 'report' intent)"
    )
    response: Optional[str] = Field(
        None,
        description="Direct response text (populated for 'qa' or 'chat' intent)"
    )


# ============================================================================
# Plan Execution Models
# ============================================================================

class ExecuteRequest(BaseModel):
    """Request to execute a generated plan."""
    session_id: str = Field(..., description="Session identifier")


class ExecuteResponse(BaseModel):
    """Response from plan execution trigger endpoint."""
    status: str = Field(
        ...,
        description="Execution status: 'started', 'already_running', or 'error'"
    )


class StatusResponse(BaseModel):
    """Response from pipeline status polling endpoint."""
    running: bool = Field(..., description="Whether pipeline is currently executing")
    step: Optional[str] = Field(None, description="Current pipeline step name")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")


# ============================================================================
# Report & Results Models
# ============================================================================

class ReportResponse(BaseModel):
    """Response from report retrieval endpoint."""
    charts: List[str] = Field(..., description="Base64-encoded PNG chart images")
    text: str = Field(..., description="Trend analysis and interpretation text")
    code: str = Field(..., description="Python code that generated the report")
    errors: Optional[List[str]] = Field(None, description="Errors if execution failed")


# ============================================================================
# Code Review & Editing Models
# ============================================================================

class CodeRequest(BaseModel):
    """Request to submit edited code."""
    session_id: str = Field(..., description="Session identifier")
    code: str = Field(..., description="Modified Python code")


class CodeResponse(BaseModel):
    """Response from code submission endpoint."""
    success: bool = Field(..., description="Whether validation succeeded")
    errors: Optional[List[str]] = Field(None, description="Validation errors if any")


class ReruncodeRequest(BaseModel):
    """Request to re-execute edited code."""
    session_id: str = Field(..., description="Session identifier")


# ============================================================================
# Template Management Models
# ============================================================================

class TemplateObject(BaseModel):
    """A saved analysis template."""
    name: str = Field(..., description="Template name")
    plan: List[str] = Field(..., description="Execution plan steps")
    code: str = Field(..., description="Python code template")


class TemplatesResponse(BaseModel):
    """Response from template listing endpoint."""
    templates: List[TemplateObject] = Field(..., description="Available templates")


class SaveTemplateRequest(BaseModel):
    """Request to save current analysis as template."""
    session_id: str = Field(..., description="Session identifier")
    name: str = Field(..., description="Template name")
    plan: List[str] = Field(..., description="Execution plan to save")
    code: str = Field(..., description="Code to save")


# ============================================================================
# Standard Response Wrapper Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Error response detail."""
    message: str = Field(..., description="User-facing error message in plain English")
    code: str = Field(
        ...,
        description="Error code enum: INVALID_SESSION, FILE_UPLOAD_ERROR, LARGE_DATA_WARNING, VALIDATION_ERROR, API_ERROR, EXECUTION_ERROR, NOT_FOUND"
    )


class StandardSuccessResponse(BaseModel):
    """Standard successful response wrapper."""
    status: str = Field(default="success", description="Always 'success' for successful responses")
    data: Dict = Field(..., description="Response data specific to endpoint")


class StandardErrorResponse(BaseModel):
    """Standard error response wrapper."""
    status: str = Field(default="error", description="Always 'error' for error responses")
    error: ErrorDetail = Field(..., description="Error details with message and code")
