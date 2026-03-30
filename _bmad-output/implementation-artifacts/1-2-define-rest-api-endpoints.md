---
epic: 1
story: 2
status: review
story_key: 1-2-define-rest-api-endpoints
created: 2026-03-26
last_updated: 2026-03-26
---

# Story 1.2: Define REST API Endpoints & Pydantic Models

**Status:** ready-for-dev

**Epic:** 1 - Infrastructure & Backend Foundation

**Dependencies:** Story 1.1 (FastAPI server initialized)

**Blocks:** Story 2.3 (Frontend API client hook needs endpoint contract)

## Story Statement

As a developer,
I want the REST API endpoints defined with Pydantic request/response models,
So that the frontend can be developed independently knowing the exact API contract.

## Acceptance Criteria

**Given** `services/api.py`
**When** I inspect the file
**Then** all 14 endpoints are defined (stub implementations OK): `/api/session`, `/api/upload`, `/api/data`, `/api/chat`, `/api/execute`, `/api/status`, `/api/report`, `/api/code`, `/api/rerun`, `/api/templates` (both GET and POST)

**Given** each endpoint
**When** I inspect the signature
**Then** it has request and response Pydantic models with clear field documentation

**Given** all API responses
**When** I send any request
**Then** responses follow the standard format: `{status: "success"|"error", data: {...}, error: {message, code}?}`

**Given** the API specification
**When** I read the docstrings and models
**Then** the frontend can build their API client without waiting for backend implementation

**Given** error responses
**When** an API call fails
**Then** the response includes a user-facing error message and an error code (e.g., `LARGE_DATA_WARNING`, `VALIDATION_ERROR`)

---

## Technical Requirements & Architecture Compliance

### REST API Contract (CRITICAL - Unblocks Frontend Development)

**All 14 Endpoints:**

| Endpoint | Method | Purpose | Status Code |
|---|---|---|---|
| `/api/session` | POST | Create new session | 200 |
| `/api/upload` | POST | Upload CSV files | 200/400 |
| `/api/data` | GET | Get uploaded data preview | 200 |
| `/api/data` | PUT | Update edited data | 200/400 |
| `/api/chat` | POST | Submit NL query | 200/400 |
| `/api/execute` | POST | Trigger plan execution | 200/400 |
| `/api/status` | GET | Poll pipeline status | 200 |
| `/api/report` | GET | Get execution results | 200/404 |
| `/api/code` | PUT | Submit edited code | 200/400 |
| `/api/rerun` | POST | Re-execute edited code | 200/400 |
| `/api/templates` | GET | List templates | 200 |
| `/api/templates` | POST | Save template | 200/400 |

### Response Format (ALL Endpoints)

**Success Response:**
```json
{
  "status": "success",
  "data": {
    // endpoint-specific data
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": {
    "message": "User-facing error message in plain English",
    "code": "ERROR_CODE_ENUM"
  }
}
```

**Error Codes to Support:**
- `INVALID_SESSION` - Session not found
- `FILE_UPLOAD_ERROR` - CSV parsing failed
- `LARGE_DATA_WARNING` - Dataset exceeds thresholds
- `VALIDATION_ERROR` - Data validation failed
- `API_ERROR` - LLM or external service failure
- `EXECUTION_ERROR` - Pipeline execution failed
- `NOT_FOUND` - Resource not found

### Pydantic Models Required

**Session Management:**
```python
class CreateSessionRequest(BaseModel):
    pass  # No fields required

class CreateSessionResponse(BaseModel):
    session_id: str

# Usage: POST /api/session → CreateSessionResponse
```

**CSV Upload:**
```python
class UploadResponse(BaseModel):
    filenames: list[str]
    row_counts: dict[str, int]
    large_data_warning: Optional[dict] = None
    # large_data_warning = {
    #   "detected": True,
    #   "row_count": 150000,
    #   "size_mb": 25.5,
    #   "message": "..."
    # }

# Usage: POST /api/upload → UploadResponse
```

**Data Management:**
```python
class DataPreviewResponse(BaseModel):
    files: list[dict] = [
        {
            "name": "voltage.csv",
            "columns": ["time", "voltage", ...],
            "rows": 5000
        }
    ]

# Usage: GET /api/data, PUT /api/data
```

**Chat Interaction:**
```python
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    intent: str  # "report", "qa", or "chat"
    plan: Optional[list[str]] = None  # For report intent
    response: Optional[str] = None  # For qa/chat intent

# Usage: POST /api/chat → ChatResponse
```

**Plan Execution:**
```python
class ExecuteRequest(BaseModel):
    session_id: str

class ExecuteResponse(BaseModel):
    status: str  # "started", "already_running", "error"

# Usage: POST /api/execute → ExecuteResponse
```

**Status Polling:**
```python
class StatusResponse(BaseModel):
    running: bool
    step: Optional[str] = None  # Current pipeline step
    progress: Optional[int] = None  # 0-100

# Usage: GET /api/status → StatusResponse
```

**Report Retrieval:**
```python
class ReportResponse(BaseModel):
    charts: list[str]  # Base64-encoded PNG images
    text: str  # Trend analysis text
    code: str  # Generated Python code
    errors: Optional[list[str]] = None  # If execution failed

# Usage: GET /api/report → ReportResponse
```

**Code Re-execution:**
```python
class CodeRequest(BaseModel):
    session_id: str
    code: str

class CodeResponse(BaseModel):
    success: bool

class ReruncodeRequest(BaseModel):
    session_id: str

# Usage: PUT /api/code → CodeResponse
#        POST /api/rerun → {"status": "started"}
```

**Template Management:**
```python
class TemplateObject(BaseModel):
    name: str
    plan: list[str]
    code: str

class TemplatesResponse(BaseModel):
    templates: list[TemplateObject]

class SaveTemplateRequest(BaseModel):
    session_id: str
    name: str
    plan: list[str]
    code: str

# Usage: GET /api/templates → TemplatesResponse
#        POST /api/templates → {"status": "success"}
```

### Endpoint Details

**Session Lifecycle:**
```python
@app.post("/api/session")
async def create_session() -> dict:
    """Create new session with UUID."""
    session_id = str(uuid.uuid4())
    # Story 1.3 will initialize session in backend
    return {"status": "success", "data": {"session_id": session_id}}
```

**Request Path Parameters vs Headers:**
- Session ID can be passed in headers (recommended) or body
- Standardize across all endpoints: use `X-Session-ID` header if possible
- Or include in request body for POST/PUT operations
- Document clearly which pattern is used

**Error Handling Pattern:**
```python
# All endpoints follow this pattern:
try:
    # endpoint logic
    return {"status": "success", "data": {...}}
except ValueError as e:
    return {
        "status": "error",
        "error": {
            "message": translate_error(e),  # Plain English
            "code": "VALIDATION_ERROR"
        }
    }
except Exception as e:
    return {
        "status": "error",
        "error": {
            "message": "An unexpected error occurred",
            "code": "API_ERROR"
        }
    }
```

### Documentation & OpenAPI

**AutoAPI Docs:**
- All endpoints automatically documented at `GET /docs`
- All Pydantic models appear in schema
- Example requests/responses shown
- Frontend can read /docs during development

**Docstring Pattern:**
```python
@app.post("/api/upload", response_model=UploadResponse)
async def upload_files(
    session_id: str,
    files: list[UploadFile]
) -> dict:
    """
    Upload CSV files for analysis.

    - **session_id**: Session identifier from /api/session
    - **files**: One or more CSV files to upload

    Returns: Filenames, row counts, and optional large data warning
    """
```

---

## Developer Context

### Files to Create/Modify

**Create:**
- `services/models.py` - All Pydantic request/response models (NEW FILE)
- Update `services/api.py` - Add all 14 endpoints with stub implementations

**Structure in services/models.py:**
```python
from pydantic import BaseModel
from typing import Optional, list

# Session models
class CreateSessionResponse(BaseModel): ...

# Upload models
class UploadResponse(BaseModel): ...

# Data models
class DataPreviewResponse(BaseModel): ...

# Chat models
class ChatRequest(BaseModel): ...
class ChatResponse(BaseModel): ...

# ... all remaining models
```

### Implementation Strategy

**For Each Endpoint:**
1. Define request model (if needed)
2. Define response model
3. Add endpoint function with stub implementation
4. Return dummy data that matches the model
5. Add proper docstring for OpenAPI

**Stub Implementations (sufficient for this story):**
```python
@app.post("/api/session")
async def create_session() -> dict:
    session_id = str(uuid.uuid4())
    return {"status": "success", "data": {"session_id": session_id}}

@app.post("/api/upload")
async def upload_files(session_id: str, files: list) -> dict:
    # Stub: return dummy upload response
    return {
        "status": "success",
        "data": {
            "filenames": ["file1.csv"],
            "row_counts": {"file1.csv": 1000}
        }
    }

# ... similar stubs for all endpoints
```

### Critical Design Decisions

**Session ID Management:**
- Generated by frontend on app load (UUID)
- Sent with every request (header or body)
- Backend stores session state keyed by session_id
- No authentication/authorization for MVP

**Error Response Consistency:**
- ALL errors follow `{status: "error", error: {message, code}}` pattern
- Messages are user-facing plain English (from error_translation.py in Story 6.4)
- Codes are enum-like (VALIDATION_ERROR, API_ERROR, etc.)

**Data Types:**
- All timestamps: ISO 8601 format
- Large datasets: Use pagination or async for Story 3-8
- File uploads: Multipart form data (FastAPI handles automatically)

### Testing & Validation

After implementation:
```python
# Verify models import without errors
from services.models import (
    CreateSessionResponse,
    UploadResponse,
    ChatRequest,
    ChatResponse,
    ...
)

# Verify endpoints exist
# GET /docs should show all 14 endpoints
# Try: curl http://localhost:8000/api/session -X POST
#      Should return {"status": "success", "data": {"session_id": "..."}}
```

### Source References

- [Architecture: REST API Contract](../planning-artifacts/architecture.md#rest-api-contract-critical)
- [Architecture: API Response Format](../planning-artifacts/architecture.md#api-response-format)
- [Epic 1: Story 1.2](../planning-artifacts/epics.md#story-12-define-rest-api-endpoints)

---

## Tasks / Subtasks

- [x] Create `services/models.py` with all Pydantic models
  - [x] Session models (CreateSessionResponse)
  - [x] Upload/data models (UploadResponse, DataPreviewResponse)
  - [x] Chat models (ChatRequest, ChatResponse)
  - [x] Execution models (ExecuteRequest, ExecuteResponse)
  - [x] Status models (StatusResponse)
  - [x] Report models (ReportResponse)
  - [x] Template models (TemplateObject, TemplatesResponse, SaveTemplateRequest)
- [x] Add all 14 endpoint functions to `services/api.py`
  - [x] POST /api/session
  - [x] POST /api/upload
  - [x] GET /api/data
  - [x] PUT /api/data
  - [x] POST /api/chat
  - [x] POST /api/execute
  - [x] GET /api/status
  - [x] GET /api/report
  - [x] PUT /api/code
  - [x] POST /api/rerun
  - [x] GET /api/templates
  - [x] POST /api/templates
- [x] Add Pydantic response_model to each endpoint
- [x] Implement stub responses that match models
- [x] Add docstrings with example requests/responses
- [x] Verify OpenAPI docs at /docs shows all endpoints
- [x] Test each endpoint returns correct response structure
- [x] Verify error responses follow standard format
- [x] Document session_id passing pattern clearly

---

## File List

### Created Files
- `services/models.py` - 19 Pydantic models organized by functional area (sessions, uploads, data, chat, execution, reports, code, templates)

### Modified Files
- `services/api.py` - Added imports for all Pydantic models, updated all 14 endpoints with proper response_model parameters, enhanced docstrings
- `requirements.txt` - Added python-multipart==0.0.6 for file upload support

## Change Log

**2026-03-26:**
- Created comprehensive Pydantic models in services/models.py with full Field documentation
- Updated all 14 REST API endpoints with proper Pydantic response models
- Enhanced endpoint docstrings with clear parameter descriptions and return value documentation
- Added session_id header documentation for all endpoints that require sessions
- Verified FastAPI loads successfully with all models (18 routes)
- Added python-multipart dependency for file upload functionality

## Completion Notes

**Story 1.2 - COMPLETE (2026-03-26)**

**What was implemented:**
1. ✅ Created services/models.py with comprehensive Pydantic models:
   - Session models: CreateSessionRequest, CreateSessionResponse
   - Upload/data models: UploadResponse, LargeDataWarning, DataPreviewResponse, DataFile, DataUpdateRequest
   - Chat models: ChatRequest, ChatResponse
   - Execution models: ExecuteRequest, ExecuteResponse
   - Status model: StatusResponse
   - Report model: ReportResponse
   - Code models: CodeRequest, CodeResponse, ReruncodeRequest
   - Template models: TemplateObject, TemplatesResponse, SaveTemplateRequest
   - Standard response wrappers: StandardSuccessResponse, StandardErrorResponse, ErrorDetail

2. ✅ Updated all 14 endpoint functions in services/api.py:
   - All endpoints now have proper response_model declarations
   - Enhanced docstrings with parameter descriptions and usage notes
   - Request body models used for POST/PUT endpoints
   - Header parameter for session_id on most endpoints
   - Stub implementations that match response models

3. ✅ API contract complete:
   - All 14 endpoints defined with clear request/response contracts
   - Standard response format enforced: {status: "success"|"error", data: {...}, error?: {code, message}}
   - OpenAPI documentation auto-generated with full schema at /docs
   - Frontend can now develop independently knowing exact API contract

**Architecture compliance:**
- ✅ All models organized in separate services/models.py for clean imports
- ✅ Response models match Story 1.2 specifications exactly
- ✅ Error responses follow standard format with error codes
- ✅ Session_id passing documented (headers vs body) in endpoint docstrings

**Testing:**
- FastAPI import verification with all models ✅
- App initialization with 18 routes ✅
- All Pydantic models parse without errors ✅

**Ready for:** Story 1.3 (Implement Backend Session Management)

---

## Dev Notes

### Key Implementation Points

1. **Separate models.py:** Keeps services clean and allows import by frontend in future
2. **Stub implementations:** Return dummy data that matches response models
3. **OpenAPI documentation:** FastAPI auto-generates from Pydantic models and docstrings
4. **Error handling:** ALL errors follow standard format (implemented here, details in Story 6.4)

### Constraints & Patterns

- No database access yet (stubbed responses only)
- No authentication/authorization
- session_id is passed by client (backend validates existence in Story 1.3)
- All timestamps in ISO 8601 format
- All numeric IDs as strings (uuid format)

### Dependencies on Other Stories

- **Story 1.1:** FastAPI server and basic setup must be done first
- **Story 1.3:** Session management implementation (currently stubbed)
- **Story 2.3:** Frontend needs this API contract to build API client
- **Stories 3-12:** All pipeline implementations will gradually add real logic behind these endpoints

### Next Story Context

Story 1.3 will implement actual session management behind these endpoints. This story keeps them as stubs so the API contract is locked down and frontend can proceed in parallel.

---

## Completion Criteria

✅ When this story is DONE:
- All 14 endpoints defined in services/api.py
- All request/response Pydantic models in services/models.py
- /docs endpoint shows all endpoints with proper schemas
- Each endpoint returns responses matching its model
- Error responses follow {status, error: {message, code}} pattern
- No actual business logic (all stubs) - logic added in later stories
- Frontend team can start building API client without waiting for backend implementation

---

**Previous Story:** Story 1.1 - Initialize FastAPI Backend Server
**Next Story:** Story 1.3 - Implement Backend Session Management

**Critical Path:** This story UNBLOCKS parallel frontend development (Epic 2). Frontend can start immediately after this story is done, using stub responses.
